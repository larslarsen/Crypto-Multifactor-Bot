"""Tests for DATA-003 Real As-Of Path Correctness & Fail-Closed Guards (REVIEW-0186 rework)."""

from __future__ import annotations

import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from cryptofactors.acquisition.binance_fetcher import BinanceKlineFetcher
from cryptofactors.catalog.as_of import CatalogAsOfStore
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import DatasetStoreConfig
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.execution import (
    INSTRUMENT_ID_TO_PAPER,
    PAPER_TO_INSTRUMENT_ID,
    PaperSymbolAsOfAdapter,
    to_binance_symbol,
    to_instrument_id,
    to_paper_symbol,
)
from cryptofactors.ingest.binance import normalize_binance_kline
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.writer import RawObjectWriter
from cryptofactors.market.bars import VerifiedSourceBarDataset, publish_canonical_bars

UTC = timezone.utc


# ---------------------------------------------------------------------------
# B1 — Int instrument_id map
# ---------------------------------------------------------------------------


def test_int_instrument_id_map_consistency() -> None:
    """Paper symbol → int id must be stable and match backfill instrument_int_id assignments."""
    assert PAPER_TO_INSTRUMENT_ID["XBTUSD"] == 1
    assert PAPER_TO_INSTRUMENT_ID["ETHUSD"] == 2
    assert INSTRUMENT_ID_TO_PAPER[1] == "XBTUSD"
    assert INSTRUMENT_ID_TO_PAPER[2] == "ETHUSD"


def test_to_instrument_id_fail_closed_on_unmapped() -> None:
    """to_instrument_id must raise KeyError for symbols not in the map."""
    with pytest.raises(KeyError, match="not in PAPER_TO_INSTRUMENT_ID"):
        to_instrument_id("UNKNOWN")


def test_symbol_mapping_bidirectional() -> None:
    assert to_binance_symbol("XBTUSD") == "BTCUSDT"
    assert to_paper_symbol("BTCUSDT") == "XBTUSD"


# ---------------------------------------------------------------------------
# B2 — Dataset id resolution
# ---------------------------------------------------------------------------


def test_resolve_latest_by_type_returns_none_when_empty() -> None:
    """resolve_latest_by_type must return None when no datasets exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        apply_migrations(db_path)
        cat = SqliteDatasetCatalog(db_path)
        try:
            assert cat.resolve_latest_by_type("market_bars") is None
        finally:
            cat.close()


# ---------------------------------------------------------------------------
# B3 — Mocked E2E: fetch → RAW → normalize → MAN source → canonical → catalog assert market_bars
# ---------------------------------------------------------------------------


def _mock_kline_rows(symbol: str = "BTCUSDT") -> list[list[object]]:
    """Generate valid 12-column Binance kline JSON arrays."""
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    rows: list[list[object]] = []
    for i in range(30):
        open_dt = t0 + timedelta(days=i)
        close_dt = open_dt + timedelta(days=1) - timedelta(milliseconds=1)
        p_open = 50000.0 + i * 10.0
        rows.append([
            int(open_dt.timestamp() * 1000),
            f"{p_open:.2f}",
            f"{p_open + 500:.2f}",
            f"{p_open - 500:.2f}",
            f"{p_open + 50:.2f}",
            f"{100.0 + i:.4f}",
            int(close_dt.timestamp() * 1000),
            f"{(100.0 + i) * (p_open + 50):.2f}",
            100 + i,
            f"{(100.0 + i) * 0.5:.4f}",
            f"{(100.0 + i) * 0.5 * (p_open + 50):.2f}",
            "0",
        ])
    return rows


def test_e2e_mocked_canonical_market_bars_in_catalog() -> None:
    """B3: fetch → RAW → normalize → MAN source → canonical → catalog assert dataset_type == market_bars."""
    rows = _mock_kline_rows()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=rows)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        store_root = Path(tmpdir) / "store"
        raw_root = store_root / "raw"

        apply_migrations(db_path)

        raw_catalog = SqliteRawObjectCatalog(db_path)
        raw_writer = RawObjectWriter(RawObjectStoreConfig(root=raw_root), raw_catalog)

        fetcher = BinanceKlineFetcher(raw_writer, client=client)
        raw_obj = fetcher.fetch_and_write_raw("BTCUSDT", "1d")

        # Normalize
        stage_dir = store_root / "staged" / "BTCUSDT"
        stage_dir.mkdir(parents=True, exist_ok=True)
        norm_res = normalize_binance_kline(
            raw_objects=[raw_obj],
            market_type="spot",
            interval="1d",
            venue_id="binance",
            instrument_id="1",
            output_dir=stage_dir,
            code_commit="DATA-003",
        )

        # Publish source dataset
        config = DatasetStoreConfig(root=store_root)
        ds_cat = SqliteDatasetCatalog(db_path)
        publisher = DatasetPublisher(config, ds_cat)
        source_ds = publisher.publish(norm_res.publish_plan, register_catalog=True)

        # Build VerifiedSourceBarDataset
        local_files = {
            f.relative_path: source_ds.dataset_path / f.relative_path
            for f in source_ds.manifest.files
        }
        verified_src = VerifiedSourceBarDataset(
            local_files=local_files,
            manifest=source_ds.manifest,
            receipt=source_ds.receipt,
            venue_id="binance",
            instrument_id=1,
            market_type="spot",
            interval="1d",
            schema_variant="quote_notional",
        )

        # Publish canonical bars
        canonical_stage = store_root / "staged" / "canonical"
        canonical_stage.mkdir(parents=True, exist_ok=True)
        canonical_res = publish_canonical_bars(
            source_datasets=[verified_src],
            output_dir=canonical_stage,
            code_commit="DATA-003",
        )

        publisher2 = DatasetPublisher(config, SqliteDatasetCatalog(db_path))
        canonical_ds = publisher2.publish(canonical_res.publish_plan, register_catalog=True)

        # Assert market_bars in catalog
        cat = SqliteDatasetCatalog(db_path)
        try:
            row = cat.get_dataset(canonical_ds.dataset_id)
            assert row is not None
            assert row["dataset_type"] == "market_bars"

            # B2: resolve_latest_by_type works
            resolved = cat.resolve_latest_by_type("market_bars")
            assert resolved == canonical_ds.dataset_id
        finally:
            cat.close()


# ---------------------------------------------------------------------------
# B4 — Mini real-asof price hit: publish bars, query latest_available with int keys, assert close
# ---------------------------------------------------------------------------


def test_asof_price_hit_with_int_instrument_id() -> None:
    """B4: After publishing canonical bars, latest_available with int keys returns close price."""
    rows = _mock_kline_rows()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=rows)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        store_root = Path(tmpdir) / "store"
        raw_root = store_root / "raw"

        apply_migrations(db_path)

        raw_catalog = SqliteRawObjectCatalog(db_path)
        raw_writer = RawObjectWriter(RawObjectStoreConfig(root=raw_root), raw_catalog)

        fetcher = BinanceKlineFetcher(raw_writer, client=client)
        raw_obj = fetcher.fetch_and_write_raw("BTCUSDT", "1d")

        stage_dir = store_root / "staged" / "BTCUSDT"
        stage_dir.mkdir(parents=True, exist_ok=True)
        norm_res = normalize_binance_kline(
            raw_objects=[raw_obj],
            market_type="spot",
            interval="1d",
            venue_id="binance",
            instrument_id="1",
            output_dir=stage_dir,
            code_commit="DATA-003",
        )

        config = DatasetStoreConfig(root=store_root)
        ds_cat = SqliteDatasetCatalog(db_path)
        publisher = DatasetPublisher(config, ds_cat)
        source_ds = publisher.publish(norm_res.publish_plan, register_catalog=True)

        local_files = {
            f.relative_path: source_ds.dataset_path / f.relative_path
            for f in source_ds.manifest.files
        }
        verified_src = VerifiedSourceBarDataset(
            local_files=local_files,
            manifest=source_ds.manifest,
            receipt=source_ds.receipt,
            venue_id="binance",
            instrument_id=1,
            market_type="spot",
            interval="1d",
            schema_variant="quote_notional",
        )

        canonical_stage = store_root / "staged" / "canonical"
        canonical_stage.mkdir(parents=True, exist_ok=True)
        canonical_res = publish_canonical_bars(
            source_datasets=[verified_src],
            output_dir=canonical_stage,
            code_commit="DATA-003",
        )

        publisher2 = DatasetPublisher(config, SqliteDatasetCatalog(db_path))
        canonical_ds = publisher2.publish(canonical_res.publish_plan, register_catalog=True)

        # Query latest_available with int key 1 (instrument_id for BTCUSDT/XBTUSD)
        as_of_store = CatalogAsOfStore(control_database=db_path, dataset_store_root=store_root)
        decision_time = datetime(2026, 1, 30, tzinfo=UTC)
        tbl = as_of_store.latest_available(
            canonical_ds.dataset_id,
            [1],  # int instrument_id
            ["close"],
            decision_time,
        )

        assert tbl is not None
        assert tbl.num_rows > 0
        close_val = float(tbl.column("close")[0].as_py())
        assert close_val > 0

        # Test PaperSymbolAsOfAdapter translates paper symbol → int key
        adapter = PaperSymbolAsOfAdapter(as_of_store)
        tbl2 = adapter.latest_available(
            canonical_ds.dataset_id,
            ["XBTUSD"],  # paper symbol
            ["close"],
            decision_time,
        )
        assert tbl2 is not None
        assert tbl2.num_rows > 0
        assert float(tbl2.column("close")[0].as_py()) == close_val


# ---------------------------------------------------------------------------
# B5 — Factor field list hits instrument_id column translation
# ---------------------------------------------------------------------------


def test_adapter_translates_instrument_id_with_factor_field_list() -> None:
    """B5: PaperSymbolAsOfAdapter returns instrument_id + close; factor field list works."""
    rows = _mock_kline_rows()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=rows)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        store_root = Path(tmpdir) / "store"
        raw_root = store_root / "raw"

        apply_migrations(db_path)

        raw_catalog = SqliteRawObjectCatalog(db_path)
        raw_writer = RawObjectWriter(RawObjectStoreConfig(root=raw_root), raw_catalog)

        fetcher = BinanceKlineFetcher(raw_writer, client=client)
        raw_obj = fetcher.fetch_and_write_raw("BTCUSDT", "1d")

        stage_dir = store_root / "staged" / "BTCUSDT"
        stage_dir.mkdir(parents=True, exist_ok=True)
        norm_res = normalize_binance_kline(
            raw_objects=[raw_obj],
            market_type="spot",
            interval="1d",
            venue_id="binance",
            instrument_id="1",
            output_dir=stage_dir,
            code_commit="DATA-003",
        )

        config = DatasetStoreConfig(root=store_root)
        ds_cat = SqliteDatasetCatalog(db_path)
        publisher = DatasetPublisher(config, ds_cat)
        source_ds = publisher.publish(norm_res.publish_plan, register_catalog=True)

        local_files = {
            f.relative_path: source_ds.dataset_path / f.relative_path
            for f in source_ds.manifest.files
        }
        verified_src = VerifiedSourceBarDataset(
            local_files=local_files,
            manifest=source_ds.manifest,
            receipt=source_ds.receipt,
            venue_id="binance",
            instrument_id=1,
            market_type="spot",
            interval="1d",
            schema_variant="quote_notional",
        )

        canonical_stage = store_root / "staged" / "canonical"
        canonical_stage.mkdir(parents=True, exist_ok=True)
        canonical_res = publish_canonical_bars(
            source_datasets=[verified_src],
            output_dir=canonical_stage,
            code_commit="DATA-003",
        )

        publisher2 = DatasetPublisher(config, SqliteDatasetCatalog(db_path))
        canonical_ds = publisher2.publish(canonical_res.publish_plan, register_catalog=True)

        adapter = PaperSymbolAsOfAdapter(
            CatalogAsOfStore(control_database=db_path, dataset_store_root=store_root)
        )
        decision_time = datetime(2026, 1, 30, tzinfo=UTC)
        tbl = adapter.latest_available(
            canonical_ds.dataset_id,
            ["XBTUSD"],
            ["instrument_id", "close"],
            decision_time,
        )

        assert tbl is not None
        assert tbl.num_rows > 0
        assert "instrument_id" in tbl.column_names
        assert "close" in tbl.column_names

        instrument_ids = tbl.column("instrument_id").to_pylist()
        assert all(isinstance(v, str) for v in instrument_ids)
        assert instrument_ids[0] == "XBTUSD"

        close_val = float(tbl.column("close")[0].as_py())
        assert close_val > 0 and close_val == pytest.approx(close_val)


# ---------------------------------------------------------------------------
# Fail-closed subprocess tests
# ---------------------------------------------------------------------------


def test_paper_path_fails_closed_without_control_db() -> None:
    """Non-dry-run path must fail closed if control database is missing."""
    cmd = [
        ".venv/bin/python",
        "scripts/run_paper_momts.py",
        "--db-path",
        "/nonexistent/path/control.db",
        "--store-root",
        "/nonexistent/store",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    assert "Control database missing" in res.stderr or "PaperExecutionError" in res.stderr


def test_paper_path_fails_closed_without_store_root() -> None:
    """Non-dry-run path must fail closed if dataset_store_root does not exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        apply_migrations(db_path)

        cmd = [
            ".venv/bin/python",
            "scripts/run_paper_momts.py",
            "--db-path",
            str(db_path),
            "--store-root",
            "/nonexistent/store/root",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode != 0
        assert "Dataset store root missing" in res.stderr or "PaperExecutionError" in res.stderr


def test_paper_path_fails_closed_without_market_bars_dataset() -> None:
    """Non-dry-run path must fail closed if no market_bars dataset exists in catalog."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        store_root = Path(tmpdir) / "store"
        store_root.mkdir(parents=True, exist_ok=True)
        apply_migrations(db_path)

        cmd = [
            ".venv/bin/python",
            "scripts/run_paper_momts.py",
            "--db-path",
            str(db_path),
            "--store-root",
            str(store_root),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode != 0
        assert "market_bars" in res.stderr or "PaperExecutionError" in res.stderr
