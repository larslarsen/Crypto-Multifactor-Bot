"""Tests for DATA-001 Binance Kline Fetcher, RAW-001 publication, and End-to-End Backfill."""

import tempfile
import zipfile
from datetime import timezone
from pathlib import Path

import httpx

from cryptofactors.acquisition.binance_fetcher import (
    BinanceKlineFetcher,
    klines_to_csv_zip_bytes,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import DatasetStoreConfig
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.ingest.binance import normalize_binance_kline
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.writer import RawObjectWriter

UTC = timezone.utc


def sample_mock_kline_rows() -> list[list[object]]:
    return [
        [
            1767225600000,
            "50000.00",
            "50500.00",
            "49500.00",
            "50050.00",
            "100.0000",
            1767311999999,
            "5005000.00",
            100,
            "50.0000",
            "2502500.00",
            "0",
        ],
        [
            1767312000000,
            "50050.00",
            "51000.00",
            "49800.00",
            "50800.00",
            "150.0000",
            1767398399999,
            "7620000.00",
            150,
            "75.0000",
            "3810000.00",
            "0",
        ],
    ]


def test_klines_to_csv_zip_bytes() -> None:
    rows = sample_mock_kline_rows()
    zip_bytes = klines_to_csv_zip_bytes("BTCUSDT", "1d", rows)

    assert len(zip_bytes) > 0

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "test.zip"
        zip_path.write_bytes(zip_bytes)

        with zipfile.ZipFile(zip_path, "r") as zf:
            files = zf.namelist()
            assert len(files) == 1
            assert files[0] == "BTCUSDT-1d.csv"

            content = zf.read(files[0]).decode("utf-8")
            lines = [line for line in content.split("\n") if line.strip()]
            assert len(lines) == 2
            assert lines[0].startswith("1767225600000,50000.00")


def test_binance_fetcher_discover() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        apply_migrations(db_path)
        catalog = SqliteRawObjectCatalog(db_path)
        writer = RawObjectWriter(RawObjectStoreConfig(root=Path(tmpdir) / "raw"), catalog)
        fetcher = BinanceKlineFetcher(writer)

        refs = fetcher.discover({"symbol": "BTCUSDT", "interval": "1d"})
        assert len(refs) == 1
        assert refs[0].source_id == "binance_spot"
        assert refs[0].request["symbol"] == "BTCUSDT"


def test_fetch_and_write_raw_with_mock_http() -> None:
    rows = sample_mock_kline_rows()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=rows)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        apply_migrations(db_path)
        catalog = SqliteRawObjectCatalog(db_path)
        writer = RawObjectWriter(RawObjectStoreConfig(root=Path(tmpdir) / "raw"), catalog)

        fetcher = BinanceKlineFetcher(writer, client=client)
        raw_obj = fetcher.fetch_and_write_raw("BTCUSDT", "1d")

        assert raw_obj.raw_object_id.startswith("raw_")
        assert raw_obj.source_id == "binance_spot"
        assert raw_obj.bytes > 0
        assert raw_obj.storage_path.exists()


def test_end_to_end_backfill_pipeline() -> None:
    """Acceptance test: Fetch klines -> RAW-001 -> MAN-001 -> Canonical Bars -> Catalog Verification."""
    rows = sample_mock_kline_rows()

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

        # Normalize via ingest/binance.py
        stage_dir = store_root / "staged" / "BTCUSDT"
        stage_dir.mkdir(parents=True, exist_ok=True)
        norm_res = normalize_binance_kline(
            raw_objects=[raw_obj],
            market_type="spot",
            interval="1d",
            venue_id="binance",
            instrument_id="BTCUSDT",
            output_dir=stage_dir,
            code_commit="DATA-001",
        )

        # Publish source dataset via MAN-001
        config = DatasetStoreConfig(root=store_root)
        catalog = SqliteDatasetCatalog(db_path)
        publisher = DatasetPublisher(config, catalog)
        source_ds = publisher.publish(norm_res.publish_plan, register_catalog=True)

        # Verify source dataset registered in SqliteDatasetCatalog
        ds_cat = SqliteDatasetCatalog(db_path)
        try:
            row = ds_cat.get_dataset(source_ds.dataset_id)
            assert row is not None
            assert row["dataset_type"] == "binance_kline_source"
        finally:
            ds_cat.close()
