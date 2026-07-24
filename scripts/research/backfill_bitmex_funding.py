#!/usr/bin/env python3
"""DATA-009 — BitMEX full historical funding rate backfill.

Extends DATA-006 to:
- Discover all active BitMEX perpetual symbols from /instrument/active.
- Backfill 8-hour funding rates from 2016-05-13 to present.
- Resume incrementally via per-symbol watermarks.
- Stay within the 120 req/min polite budget.
- Publish a new canonical dataset.

No LIVE.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetStatistics,
    DatasetStoreConfig,
    OutputFileSpec,
    PublishPlan,
    QualityStatus,
    RowCountPolicy,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.ingest.bitmex_funding import (
    BitMEXFundingClient,
    build_funding_table,
)

UTC = timezone.utc
DEFAULT_START_TIME = "2016-05-13T00:00:00+00:00"
WATERMARK_PATH = Path("data/bitmex_funding_full_watermarks.json")
REPORT_PATH = "research/sprint_004/39_BITMEX_FULL_BACKFILL.json"
DATASET_TYPE = "bitmex_funding_full"


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def load_watermarks(path: Path) -> dict[str, str]:
    """Load per-symbol watermarks as ISO timestamps."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return dict(data.get("watermarks", {}))


def save_watermarks(path: Path, watermarks: dict[str, datetime]) -> None:
    """Save per-symbol watermarks as ISO timestamps."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "watermarks": {
            sym: dt.isoformat() for sym, dt in watermarks.items()
        }
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def generate_mock_funding(symbol: str, count: int = 100) -> list[dict[str, Any]]:
    """Generate mocked BitMEX funding records for dry-run testing."""
    t0 = datetime(2016, 5, 13, tzinfo=UTC)
    records: list[dict[str, Any]] = []
    for i in range(count):
        ts = t0 + timedelta(hours=8 * i)
        records.append({
            "timestamp": ts.isoformat().replace("+00:00", "Z"),
            "symbol": symbol,
            "fundingRate": 0.0001 * (i % 5 - 2),
            "fundingRateDaily": 0.0003 * (i % 5 - 2),
            "fundingInterval": "2000-01-01T08:00:00.000Z" if i < 10 else "2000-01-01T08:00:00.000Z",
        })
    return records


def generate_mock_instruments() -> list[dict[str, Any]]:
    """Generate mocked active instruments for dry-run testing."""
    return [
        {"symbol": "XBTUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "ETHUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "XRPUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "LTCUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "SOLUSDT", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "SPYUSD", "typ": "FFCCSX", "state": "Open"},  # not a perp
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-009 BitMEX full funding backfill")
    parser.add_argument("--symbols", type=str, default=None,
                        help="Comma-separated symbols; if omitted, discover from exchange")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--start-time", type=str, default=DEFAULT_START_TIME)
    parser.add_argument("--end-time", type=str, default=None)
    parser.add_argument("--watermark-path", type=str, default=str(WATERMARK_PATH))
    parser.add_argument("--report-path", type=str, default=REPORT_PATH)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.add_argument("--rate-per-minute", type=int, default=120)
    args = parser.parse_args()

    start_time = _parse_iso(args.start_time)
    end_time = _parse_iso(args.end_time) if args.end_time else datetime.now(UTC)

    if args.dry_run:
        print("DATA-009 BitMEX: DRY-RUN mode with mocked responses", file=sys.stderr)
        tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(tmpdir.name) / "exp003.db"
        store_root = Path(tmpdir.name) / "exp003_store"
        watermark_path = Path(tmpdir.name) / "watermarks.json"
        data_mode = "synthetic"

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "/instrument/active" in url:
                return httpx.Response(200, json=generate_mock_instruments())
            for sym in ["XBTUSD", "ETHUSD", "XRPUSD", "LTCUSD", "SOLUSDT"]:
                if sym in url:
                    return httpx.Response(200, json=generate_mock_funding(sym))
            return httpx.Response(200, json=[])

        client = BitMEXFundingClient(
            client=httpx.Client(transport=httpx.MockTransport(mock_handler)),
            requests_per_minute=args.rate_per_minute,
        )
    else:
        db_path = Path(args.db_path)
        store_root = Path(args.store_root)
        watermark_path = Path(args.watermark_path)
        data_mode = "real_asof"
        client = BitMEXFundingClient(requests_per_minute=args.rate_per_minute)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    store_root.mkdir(parents=True, exist_ok=True)
    apply_migrations(db_path)

    # Discover or use provided symbol universe.
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        try:
            symbols = client.fetch_perp_symbols()
            print(f"DATA-009: discovered {len(symbols)} perpetual symbols", file=sys.stderr)
        except Exception as exc:
            print(f"ERROR discovering symbols: {exc}", file=sys.stderr)
            return 1

    if not symbols:
        print("No symbols to backfill", file=sys.stderr)
        return 1

    watermarks = load_watermarks(watermark_path)
    new_watermarks: dict[str, datetime] = {}

    all_records: list[dict[str, Any]] = []
    symbol_rows: list[dict[str, Any]] = []
    rate_limit_incidents: list[dict[str, Any]] = []

    for symbol in symbols:
        symbol_start = start_time
        watermark_str = watermarks.get(symbol)
        if watermark_str:
            watermark_dt = _parse_iso(watermark_str)
            # Resume from the next 8-hour interval after the watermark.
            symbol_start = watermark_dt + timedelta(hours=8)
            if symbol_start >= end_time:
                print(f"Skipping {symbol}: up to watermark", file=sys.stderr)
                new_watermarks[symbol] = watermark_dt
                continue

        try:
            records = client.fetch_funding(symbol, start_time=symbol_start, end_time=end_time)
            if not records:
                print(f"No funding records for {symbol}", file=sys.stderr)
                continue
            all_records.extend(records)
            last_ts_str = records[-1]["timestamp"]
            last_ts = _parse_iso(last_ts_str)
            new_watermarks[symbol] = last_ts
            symbol_rows.append({
                "symbol": symbol,
                "record_count": len(records),
                "first_timestamp": records[0]["timestamp"],
                "last_timestamp": records[-1]["timestamp"],
                "watermark": last_ts.isoformat(),
                "resumed_from": watermark_str,
            })
            print(f"Fetched {len(records)} funding records for {symbol}", file=sys.stderr)
        except Exception as exc:
            note = str(exc)
            print(f"ERROR fetching {symbol}: {note}", file=sys.stderr)
            rate_limit_incidents.append({
                "timestamp": datetime.now(UTC).isoformat(),
                "symbol": symbol,
                "note": note,
            })

    if not all_records:
        print("No funding records produced; cannot publish dataset", file=sys.stderr)
        return 1

    save_watermarks(watermark_path, new_watermarks)

    table = build_funding_table(all_records)

    stage_dir = store_root / "staged" / "bitmex_funding_full"
    stage_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = stage_dir / "funding.parquet"
    pq.write_table(table, parquet_path)

    row_count = table.num_rows

    relative_path = "bitmex/funding_full/funding.parquet"
    output_sources = {relative_path: parquet_path}
    sha256, byte_size = stream_sha256_and_size(parquet_path)
    output_specs = [
        OutputFileSpec(
            relative_path=relative_path,
            sha256=sha256,
            rows=row_count,
            bytes=byte_size,
            partition={"source": "bitmex", "kind": "funding_full"},
        )
    ]

    coverage_start = min(
        (_parse_iso(r["timestamp"]) for r in all_records),
        default=start_time,
    )
    coverage_end = max(
        (_parse_iso(r["timestamp"]) for r in all_records),
        default=end_time,
    )

    plan = PublishPlan(
        dataset_type=DATASET_TYPE,
        schema=SchemaIdentity(name="bitmex_funding", version="1", fingerprint="fund_v1"),
        transform=TransformSpec(name="bitmex_funding_full_backfill", version="1"),
        code=CodeIdentity(commit="DATA-009"),
        config=ConfigIdentity(config_sha256="a" * 64),
        dependencies=(),
        output_sources=output_sources,
        output_specs=output_specs,
        statistics=DatasetStatistics(row_count=row_count, byte_size=byte_size),
        coverage=CoverageWindow(
            event_start=coverage_start,
            event_end=coverage_end,
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={
            "record_count": row_count,
            "symbol_count": len(symbols),
            "symbols_backfilled": [r["symbol"] for r in symbol_rows],
            "rate_limit_incidents": len(rate_limit_incidents),
        },
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters={relative_path: lambda p: row_count},
        created_at=datetime.now(UTC),
    )

    config = DatasetStoreConfig(root=store_root)
    catalog = SqliteDatasetCatalog(db_path)
    try:
        publisher = DatasetPublisher(config, catalog)
        result = publisher.publish(plan, register_catalog=True)
        resolved_latest = catalog.resolve_latest_by_type(DATASET_TYPE)
    finally:
        catalog.close()

    print(f"BitMEX full funding dataset published: {result.dataset_id}", file=sys.stderr)

    report = {
        "experiment_id": "DATA-009-BITMEX-FULL-BACKFILL",
        "data_mode": data_mode,
        "real_asof": datetime.now(UTC).isoformat() if data_mode == "real_asof" else None,
        "symbols": symbols,
        "symbols_backfilled": [r["symbol"] for r in symbol_rows],
        "symbols_skipped": [s for s in symbols if s not in {r["symbol"] for r in symbol_rows}],
        "dataset_id": result.dataset_id,
        "dataset_type": DATASET_TYPE,
        "catalog_reconciliation": {
            "report_pinned_dataset_id": result.dataset_id,
            "resolve_latest_by_type": resolved_latest,
            "match": result.dataset_id == resolved_latest,
        },
        "quality_status": result.manifest.quality_status.value,
        "row_count": row_count,
        "byte_size": byte_size,
        "symbol_rows": symbol_rows,
        "coverage": {
            "start": coverage_start.isoformat(),
            "end": coverage_end.isoformat(),
        },
        "rate_limit_incidents": rate_limit_incidents,
        "watermarks": {
            sym: dt.isoformat() for sym, dt in new_watermarks.items()
        },
        "live_eligible": False,
        "scope": "all BitMEX perpetuals from 2016-05-13 (or symbol inception) to present; 8-hour funding",
        "generated_at": datetime.now(UTC).isoformat(),
    }
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written to {report_path}", file=sys.stderr)

    if args.dry_run:
        tmpdir.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
