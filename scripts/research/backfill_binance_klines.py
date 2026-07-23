#!/usr/bin/env python3
"""DATA-001 — Backfill script for Binance spot klines through RAW-001 -> MAN-001 -> Canonical Bars.

Flow:
1. Fetch Binance klines via REST API GET /api/v3/klines using BinanceKlineFetcher.
2. Store raw zip file in content-addressed store (RAW-001).
3. Normalize raw object via ingest/binance.py (BIN-001).
4. Publish source dataset via DatasetPublisher (MAN-001).
5. Build and publish canonical market bars via market/bars.py (BAR-001).

Usage:
  python3 scripts/research/backfill_binance_klines.py --dry-run
  python3 scripts/research/backfill_binance_klines.py --symbol BTCUSDT --interval 1d --db-path control.db
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

import json
from cryptofactors.acquisition.binance_fetcher import BinanceKlineFetcher
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import DatasetPublishResult, DatasetStoreConfig
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.ingest.binance import normalize_binance_kline
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.writer import RawObjectWriter
from cryptofactors.market.bars import VerifiedSourceBarDataset, publish_canonical_bars

UTC = timezone.utc


def generate_mock_klines(
    symbol: str,
    interval: str = "1d",
    count: int = 30,
) -> list[list[object]]:
    """Generate valid 12-column Binance kline JSON arrays for testing."""
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    rows: list[list[object]] = []

    for i in range(count):
        open_time = t0 + timedelta(days=i)
        close_time = open_time + timedelta(days=1) - timedelta(milliseconds=1)
        open_ms = int(open_time.timestamp() * 1000)
        close_ms = int(close_time.timestamp() * 1000)

        p_open = 50000.0 + i * 10.0
        p_high = p_open + 500.0
        p_low = p_open - 500.0
        p_close = p_open + 50.0
        volume = 100.0 + i

        rows.append([
            open_ms,
            f"{p_open:.2f}",
            f"{p_high:.2f}",
            f"{p_low:.2f}",
            f"{p_close:.2f}",
            f"{volume:.4f}",
            close_ms,
            f"{volume * p_close:.2f}",
            100 + i,
            f"{volume * 0.5:.4f}",
            f"{volume * 0.5 * p_close:.2f}",
            "0",
        ])

    return rows


def backfill_symbol_klines(
    symbol: str,
    interval: str,
    raw_writer: RawObjectWriter,
    catalog_path: Path,
    dataset_store_root: Path,
    client: httpx.Client | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    instrument_int_id: int = 1,
) -> DatasetPublishResult:
    """Run backfill pipeline for one symbol from REST fetch -> RAW-001 -> MAN-001 source dataset."""
    fetcher = BinanceKlineFetcher(raw_writer=raw_writer, client=client)

    st = start_time or datetime(2026, 1, 1, tzinfo=UTC)
    et = end_time or datetime(2026, 2, 1, tzinfo=UTC)

    print(f"Fetching {symbol} {interval} klines...", file=sys.stderr)
    raw_object = fetcher.fetch_and_write_raw(
        symbol=symbol,
        interval=interval,
        start_time=st,
        end_time=et,
    )
    print(f"RAW-001 object created: {raw_object.raw_object_id} ({raw_object.bytes} bytes)", file=sys.stderr)

    # 3. Normalize raw object via ingest/binance.py
    stage_dir = dataset_store_root / "staged" / symbol
    stage_dir.mkdir(parents=True, exist_ok=True)

    norm_res = normalize_binance_kline(
        raw_objects=[raw_object],
        market_type="spot",
        interval=interval,
        venue_id="binance",
        instrument_id=str(instrument_int_id),
        output_dir=stage_dir,
        code_commit="DATA-002",
    )

    # 4. Publish source dataset via MAN-001 DatasetPublisher
    config = DatasetStoreConfig(root=dataset_store_root)
    catalog = SqliteDatasetCatalog(catalog_path)
    publisher = DatasetPublisher(config, catalog)
    source_dataset = publisher.publish(norm_res.publish_plan, register_catalog=True)
    print(f"MAN-001 source dataset published: {source_dataset.dataset_id}", file=sys.stderr)

    return source_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-002 Binance klines backfill & canonical bar pipeline.")
    parser.add_argument("--symbols", type=str, default="BTCUSDT,ETHUSDT", help="Comma-separated symbols to backfill")
    parser.add_argument("--interval", type=str, default="1d", help="Kline interval (e.g. 1d, 1h)")
    parser.add_argument("--db-path", type=str, default="control.db", help="Path to control SQLite DB")
    parser.add_argument("--store-root", type=str, default="data/store", help="Path to dataset store root")
    parser.add_argument("--dry-run", action="store_true", help="Run with mocked HTTP response and temp directories")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    if args.dry_run:
        print("Running backfill in DRY-RUN mode with mocked responses...", file=sys.stderr)
        tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(tmpdir.name) / "control.db"
        store_root = Path(tmpdir.name) / "store"
        raw_root = Path(tmpdir.name) / "raw"

        mock_responses = {sym: generate_mock_klines(sym, args.interval, count=30) for sym in symbols}

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            for sym in symbols:
                if sym in url_str:
                    return httpx.Response(200, json=mock_responses[sym])
            return httpx.Response(200, json=generate_mock_klines("BTCUSDT", args.interval, count=30))

        transport = httpx.MockTransport(mock_handler)
        client = httpx.Client(transport=transport)
        data_mode = "synthetic"
    else:
        db_path = Path(args.db_path)
        store_root = Path(args.store_root)
        raw_root = store_root / "raw"
        client = None
        data_mode = "real_asof"

    db_path.parent.mkdir(parents=True, exist_ok=True)
    apply_migrations(db_path)

    raw_catalog = SqliteRawObjectCatalog(db_path)
    raw_config = RawObjectStoreConfig(root=raw_root)
    raw_writer = RawObjectWriter(config=raw_config, catalog=raw_catalog)

    verified_sources: list[VerifiedSourceBarDataset] = []
    source_ids: list[str] = []

    for idx, sym in enumerate(symbols):
        source_ds = backfill_symbol_klines(
            symbol=sym,
            interval=args.interval,
            raw_writer=raw_writer,
            catalog_path=db_path,
            dataset_store_root=store_root,
            client=client,
            instrument_int_id=idx + 1,
        )
        source_ids.append(source_ds.dataset_id)
        local_files = {
            f.relative_path: source_ds.dataset_path / f.relative_path
            for f in source_ds.manifest.files
        }
        verified_sources.append(
            VerifiedSourceBarDataset(
                local_files=local_files,
                manifest=source_ds.manifest,
                receipt=source_ds.receipt,
                venue_id="binance",
                instrument_id=idx + 1,  # Matches partition instrument_id ("1", "2")
                market_type="spot",
                interval=args.interval,
                schema_variant="quote_notional",
            )
        )

    # Build & publish canonical market bars via BAR-001 publish_canonical_bars
    canonical_stage_dir = store_root / "staged" / "canonical_bars"
    canonical_stage_dir.mkdir(parents=True, exist_ok=True)

    canonical_plan_res = publish_canonical_bars(
        source_datasets=verified_sources,
        output_dir=canonical_stage_dir,
        code_commit="DATA-002",
    )

    config = DatasetStoreConfig(root=store_root)
    catalog = SqliteDatasetCatalog(db_path)
    publisher = DatasetPublisher(config, catalog)
    canonical_ds = publisher.publish(canonical_plan_res.publish_plan, register_catalog=True)
    print(f"BAR-001 canonical market_bars published: {canonical_ds.dataset_id}", file=sys.stderr)

    # Verify published canonical dataset in DatasetCatalog
    ds_row = catalog.get_dataset(canonical_ds.dataset_id)
    assert ds_row is not None, f"Canonical dataset {canonical_ds.dataset_id} not found in catalog!"
    assert ds_row["dataset_type"] == "market_bars", f"Expected dataset_type 'market_bars', got {ds_row['dataset_type']}"
    print(f"SUCCESS: Verified canonical dataset {canonical_ds.dataset_id} in catalog", file=sys.stderr)

    # Write report artifact: research/sprint_004/11_REAL_DATA_PATH_REPORT.json
    report_data = {
        "data_mode": data_mode,
        "source_dataset_ids": source_ids,
        "canonical_dataset_id": canonical_ds.dataset_id,
        "total_bar_count": canonical_ds.manifest.statistics.row_count,
        "symbols_covered": symbols,
        "gate_status": "OK",
        "live_eligible": False,  # ALWAYS false per policy
        "generated_at": datetime.now(UTC).isoformat(),
    }

    report_path = Path("research/sprint_004/11_REAL_DATA_PATH_REPORT.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"Real data path report written to {report_path}", file=sys.stderr)

    if args.dry_run:
        tmpdir.cleanup()

    return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
