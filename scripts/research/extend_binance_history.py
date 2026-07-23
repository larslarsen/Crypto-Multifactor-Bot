#!/usr/bin/env python3
"""DATA-004 — Extend real market bar history to ≥24 months for credible OOS.

Backfills the 10-symbol paper universe via the existing Binance spot klines
acquisition pipeline (RAW-001 -> MAN-001 -> BAR-001 canonical market_bars),
records the resulting content-addressed dataset IDs, and writes a report
artifact with per-symbol row counts, date spans, and gap counts.

No LIVE. No risk-limit changes. Does not mutate artifacts 08-19.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.acquisition.binance_fetcher import BinanceKlineFetcher
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import (
    DatasetPublishResult,
    DatasetStoreConfig,
)
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.execution.symbols import (
    PAPER_TO_BINANCE_MAP,
    PAPER_TO_INSTRUMENT_ID,
)
from cryptofactors.ingest.binance import normalize_binance_kline
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.writer import RawObjectWriter
from cryptofactors.market.bars import VerifiedSourceBarDataset, publish_canonical_bars

UTC = timezone.utc

DEFAULT_START = datetime(2024, 1, 1, tzinfo=UTC)


def _today_utc() -> datetime:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_iso(value: str) -> datetime:
    value = value.strip().upper().replace("Z", "+00:00")
    return datetime.fromisoformat(value)


def _generate_mock_klines(
    symbol: str,
    interval: str = "1d",
    count: int = 30,
    start: datetime | None = None,
) -> list[list[object]]:
    """Generate valid 12-column Binance kline JSON arrays for testing."""
    t0 = start or datetime(2026, 1, 1, tzinfo=UTC)
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


def _backfill_symbol(
    symbol: str,
    instrument_id: int,
    interval: str,
    raw_writer: RawObjectWriter,
    catalog_path: Path,
    dataset_store_root: Path,
    client: httpx.Client | None,
    start_time: datetime,
    end_time: datetime,
) -> tuple[int, DatasetPublishResult]:
    """Fetch one symbol through RAW-001 -> MAN-001 source dataset."""
    fetcher = BinanceKlineFetcher(raw_writer=raw_writer, client=client)

    print(f"Fetching {symbol} {interval} klines...", file=sys.stderr)
    raw_object = fetcher.fetch_and_write_raw(
        symbol=symbol,
        interval=interval,
        start_time=start_time,
        end_time=end_time,
    )
    print(
        f"RAW-001 object created: {raw_object.raw_object_id} ({raw_object.bytes} bytes)",
        file=sys.stderr,
    )

    stage_dir = dataset_store_root / "staged" / symbol
    stage_dir.mkdir(parents=True, exist_ok=True)

    norm_res = normalize_binance_kline(
        raw_objects=[raw_object],
        market_type="spot",
        interval=interval,
        venue_id="binance",
        instrument_id=str(instrument_id),
        output_dir=stage_dir,
        code_commit="DATA-004",
    )

    config = DatasetStoreConfig(root=dataset_store_root)
    catalog = SqliteDatasetCatalog(catalog_path)
    publisher = DatasetPublisher(config, catalog)
    source_dataset = publisher.publish(norm_res.publish_plan, register_catalog=True)
    print(
        f"MAN-001 source dataset published: {source_dataset.dataset_id}",
        file=sys.stderr,
    )

    return instrument_id, source_dataset


def _build_canonical_bars(
    source_datasets: list[tuple[int, DatasetPublishResult]],
    dataset_store_root: Path,
    catalog_path: Path,
) -> DatasetPublishResult:
    """Build and publish BAR-001 canonical market_bars from source datasets."""
    verified_sources: list[VerifiedSourceBarDataset] = []
    for instrument_id, source_ds in source_datasets:
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
                instrument_id=instrument_id,
                market_type="spot",
                interval="1d",
                schema_variant="quote_notional",
            )
        )

    canonical_stage_dir = dataset_store_root / "staged" / "canonical_bars_extended"
    canonical_stage_dir.mkdir(parents=True, exist_ok=True)

    canonical_plan_res = publish_canonical_bars(
        source_datasets=verified_sources,
        output_dir=canonical_stage_dir,
        code_commit="DATA-004",
    )

    config = DatasetStoreConfig(root=dataset_store_root)
    catalog = SqliteDatasetCatalog(catalog_path)
    publisher = DatasetPublisher(config, catalog)
    canonical_ds = publisher.publish(canonical_plan_res.publish_plan, register_catalog=True)
    print(
        f"BAR-001 canonical market_bars published: {canonical_ds.dataset_id}",
        file=sys.stderr,
    )

    return canonical_ds


def _us_to_datetime(us: int) -> datetime:
    return datetime.fromtimestamp(us / 1_000_000, tz=UTC)


def _analyze_canonical_dataset(
    canonical_ds: DatasetPublishResult,
    dataset_store_root: Path,
    paper_symbols: list[str],
) -> dict[str, Any]:
    """Compute per-symbol row counts, bar spans, and daily gap counts."""
    dataset_base = dataset_store_root
    if canonical_ds.manifest_uri:
        dataset_base = dataset_store_root / Path(canonical_ds.manifest_uri).parent

    # Find all intraday bars.parquet files.
    bar_paths = list(
        (dataset_base / "market_bars" / "intraday").rglob("bars.parquet")
    )
    if not bar_paths:
        bar_paths = list(
            (dataset_base / "market_bars" / "quarantine").rglob("bars.parquet")
        )

    tables = [pq.read_table(str(p)) for p in bar_paths if p.is_file()]
    if not tables:
        return {
            "total_bar_count": 0,
            "bar_start": None,
            "bar_end": None,
            "symbols": [],
            "gaps": {},
        }

    table = pa.concat_tables(tables, promote_options="default")

    instrument_ids = table.column("instrument_id").to_pylist()
    period_starts = table.column("period_start").to_pylist()

    by_instrument: dict[int, list[datetime]] = defaultdict(list)
    for iid, ps in zip(instrument_ids, period_starts):
        if iid is None or ps is None:
            continue
        by_instrument[int(iid)].append(_us_to_datetime(int(ps)))

    symbol_stats: list[dict[str, Any]] = []
    gaps_by_symbol: dict[str, int] = {}

    all_starts: list[datetime] = []
    all_ends: list[datetime] = []

    for symbol in paper_symbols:
        iid = PAPER_TO_INSTRUMENT_ID[symbol]
        dates = sorted(by_instrument.get(iid, []))
        if not dates:
            symbol_stats.append(
                {
                    "paper_symbol": symbol,
                    "instrument_id": iid,
                    "row_count": 0,
                    "bar_start": None,
                    "bar_end": None,
                    "gap_count": 0,
                }
            )
            gaps_by_symbol[symbol] = 0
            continue

        expected_days = {
            dates[0].date() + timedelta(days=i)
            for i in range((dates[-1].date() - dates[0].date()).days + 1)
        }
        observed_days = {d.date() for d in dates}
        gap_count = len(expected_days - observed_days)

        symbol_stats.append(
            {
                "paper_symbol": symbol,
                "instrument_id": iid,
                "row_count": len(dates),
                "bar_start": dates[0].isoformat(),
                "bar_end": dates[-1].isoformat(),
                "gap_count": gap_count,
            }
        )
        gaps_by_symbol[symbol] = gap_count
        all_starts.append(dates[0])
        all_ends.append(dates[-1])

    return {
        "total_bar_count": int(table.num_rows),
        "bar_start": min(all_starts).isoformat() if all_starts else None,
        "bar_end": max(all_ends).isoformat() if all_ends else None,
        "symbols": symbol_stats,
        "gaps": gaps_by_symbol,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-004 — extend real market bar history.")
    parser.add_argument(
        "--start-time",
        type=str,
        default="2024-01-01T00:00:00Z",
        help="Start time ISO 8601 (UTC)",
    )
    parser.add_argument(
        "--end-time",
        type=str,
        default=None,
        help="End time ISO 8601 (UTC); defaults to today UTC",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="exp003.db",
        help="Path to control SQLite DB",
    )
    parser.add_argument(
        "--store-root",
        type=str,
        default="data/exp003_store",
        help="Path to dataset store root",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default="research/sprint_004/20_EXTENDED_HISTORY_REPORT.json",
        help="Path to write the extended history report",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run with mocked HTTP responses")
    args = parser.parse_args()

    start_time = _parse_iso(args.start_time)
    end_time = _parse_iso(args.end_time) if args.end_time else _today_utc()

    paper_symbols = sorted(PAPER_TO_INSTRUMENT_ID.keys())

    if args.dry_run:
        print("Running in DRY-RUN mode with mocked responses...", file=sys.stderr)
        tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(tmpdir.name) / "control.db"
        store_root = Path(tmpdir.name) / "store"
        raw_root = Path(tmpdir.name) / "raw"

        mock_responses = {
            PAPER_TO_BINANCE_MAP[sym]: _generate_mock_klines(
                PAPER_TO_BINANCE_MAP[sym],
                "1d",
                count=30,
                start=start_time,
            )
            for sym in paper_symbols
        }

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            for sym in mock_responses:
                if sym in url_str:
                    return httpx.Response(200, json=mock_responses[sym])
            return httpx.Response(200, json=[])

        transport = httpx.MockTransport(mock_handler)
        client: httpx.Client | None = httpx.Client(transport=transport)
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

    source_datasets: list[tuple[int, DatasetPublishResult]] = []
    for paper_symbol in paper_symbols:
        binance_symbol = PAPER_TO_BINANCE_MAP[paper_symbol]
        instrument_id = PAPER_TO_INSTRUMENT_ID[paper_symbol]
        source_ds = _backfill_symbol(
            symbol=binance_symbol,
            instrument_id=instrument_id,
            interval="1d",
            raw_writer=raw_writer,
            catalog_path=db_path,
            dataset_store_root=store_root,
            client=client,
            start_time=start_time,
            end_time=end_time,
        )
        source_datasets.append(source_ds)

    canonical_ds = _build_canonical_bars(
        source_datasets=source_datasets,
        dataset_store_root=store_root,
        catalog_path=db_path,
    )

    analysis = _analyze_canonical_dataset(
        canonical_ds=canonical_ds,
        dataset_store_root=store_root,
        paper_symbols=paper_symbols,
    )

    # Determine overall span in months.
    if analysis["bar_start"] and analysis["bar_end"]:
        start_dt = datetime.fromisoformat(analysis["bar_start"])
        end_dt = datetime.fromisoformat(analysis["bar_end"])
        span_days = (end_dt - start_dt).days
        span_months = round(span_days / 30.4375, 2)
    else:
        span_days = 0
        span_months = 0.0

    # Catalog quality status.
    catalog = SqliteDatasetCatalog(db_path)
    try:
        ds_row = catalog.get_dataset(canonical_ds.dataset_id)
        canonical_quality = str(ds_row["quality_status"]) if ds_row else "UNKNOWN"
    finally:
        catalog.close()

    # Detect whether any symbol did not reach the requested end (venue max).
    venue_max_reached = False
    short_symbols: list[str] = []
    for sym_info in analysis["symbols"]:
        if sym_info["bar_end"] is None:
            short_symbols.append(sym_info["paper_symbol"])
            continue
        sym_end = datetime.fromisoformat(sym_info["bar_end"])
        if sym_end < end_time - timedelta(days=1):
            short_symbols.append(sym_info["paper_symbol"])
    if short_symbols:
        venue_max_reached = True

    report_data = {
        "experiment_id": "DATA-004",
        "data_mode": data_mode,
        "source_dataset_ids": [ds.dataset_id for _, ds in source_datasets],
        "canonical_dataset_id": canonical_ds.dataset_id,
        "canonical_dataset_quality_status": canonical_quality,
        "store_root": str(store_root),
        "db_path": str(db_path),
        "requested_start": start_time.isoformat(),
        "requested_end": end_time.isoformat(),
        "bar_start": analysis["bar_start"],
        "bar_end": analysis["bar_end"],
        "span_days": span_days,
        "span_months": span_months,
        "total_bar_count": analysis["total_bar_count"],
        "symbols_covered": paper_symbols,
        "venue_symbols": sorted(set(PAPER_TO_BINANCE_MAP.values())),
        "per_symbol": analysis["symbols"],
        "gaps": analysis["gaps"],
        "venue_max_reached": venue_max_reached,
        "short_symbols": short_symbols,
        "live_eligible": False,
        "live_eligible_note": "DATA-004 is a data-acquisition report only; no LIVE path.",
        "generated_at": datetime.now(UTC).isoformat(),
    }

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"Extended history report written to {report_path}", file=sys.stderr)

    if args.dry_run:
        tmpdir.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
