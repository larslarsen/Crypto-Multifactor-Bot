#!/usr/bin/env python3
"""DATA-008 — Expand Binance spot universe using screen-prioritized symbols.

Usage:
    python scripts/research/expand_binance_universe.py --dry-run
    python scripts/research/expand_binance_universe.py --no-dry-run

Default is dry-run. Real mode backfills additional symbols beyond the DATA-006
23-symbol universe and publishes a new canonical market_bars dataset.

No LIVE. Multi-day safe default budget: 20k symbols/day.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ops"))
from daily_refresh import _load_existing_source_datasets

from cryptofactors.acquisition.binance_fetcher import BinanceKlineFetcher
from cryptofactors.acquisition.binance_universe_expansion import (
    BinanceSymbolScreener,
    BinanceUniverseExpander,
    DailySymbolBudget,
    IncrementalWatermarkStore,
    InstrumentIdAllocator,
    RateLimitIncident,
    load_watermark_as_datetime,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import DatasetPublishResult, DatasetStoreConfig
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.execution.symbols import PAPER_TO_BINANCE_MAP, PAPER_TO_INSTRUMENT_ID
from cryptofactors.ingest.binance import normalize_binance_kline
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.writer import RawObjectWriter
from cryptofactors.market.bars import VerifiedSourceBarDataset, publish_canonical_bars

UTC = timezone.utc

DEFAULT_BASE_SYMBOLS = sorted(set(PAPER_TO_BINANCE_MAP.values()))
DEFAULT_START = datetime(2020, 1, 1, tzinfo=UTC)
WATERMARK_PATH = Path("data/backfill_watermarks.json")


def _today_utc() -> datetime:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.strip().upper().replace("Z", "+00:00"))


def _generate_mock_klines(
    symbol: str,
    start_ms: int,
    end_ms: int,
    limit: int = 1000,
) -> list[list[Any]]:
    """Generate a paginated slice of valid Binance 1d kline arrays for dry-run.

    Aligns to the next day boundary so that the fetcher's pagination
    (start_ms = last_open_ms + 1) does not create intra-day gaps.
    """
    rows: list[list[Any]] = []
    # Align to the next UTC day boundary.
    day_ms = ((start_ms // 86_400_000) + 1) * 86_400_000
    if day_ms < start_ms:
        day_ms += 86_400_000
    i = 0
    while day_ms < end_ms and len(rows) < limit:
        open_ms = day_ms
        close_ms = day_ms + 86_400_000 - 1
        base = 1.0 + (hash(symbol) % 1000)
        p_open = base + i * 0.1
        p_high = p_open + 0.05
        p_low = p_open - 0.05
        p_close = p_open + 0.01
        volume = 1000.0 + i
        rows.append([
            open_ms,
            f"{p_open:.4f}",
            f"{p_high:.4f}",
            f"{p_low:.4f}",
            f"{p_close:.4f}",
            f"{volume:.4f}",
            close_ms,
            f"{volume * p_close:.4f}",
            100,
            f"{volume * 0.5:.4f}",
            f"{volume * 0.5 * p_close:.4f}",
            "0",
        ])
        day_ms += 86_400_000
        i += 1
    return rows


def _fetch_symbol_priority_mock(new_symbols: list[str]) -> list[dict[str, Any]]:
    """Return synthetic ticker/24hr data for dry-run symbol prioritization."""
    return [
        {
            "symbol": sym,
            "status": "TRADING",
            "quoteVolume": 10_000_000.0 - idx * 100_000.0,
            "lastPrice": "100.0",
            "count": 10000,
        }
        for idx, sym in enumerate(new_symbols)
    ]


def _backfill_new_symbol(
    symbol: str,
    instrument_id: int,
    start_time: datetime,
    end_time: datetime,
    raw_writer: RawObjectWriter,
    db_path: Path,
    client: httpx.Client | None,
    budget: DailySymbolBudget,
) -> DatasetPublishResult:
    """Fetch and publish a single source dataset for a new symbol."""
    fetcher = BinanceKlineFetcher(raw_writer=raw_writer, client=client)
    try:
        raw_object = fetcher.fetch_and_write_raw(
            symbol=symbol,
            interval="1d",
            start_time=start_time,
            end_time=end_time,
        )
    except Exception as exc:
        # Record rate-limit incidents if they are HTTP errors.
        if hasattr(exc, "context") and isinstance(getattr(exc, "context", None), dict):
            ctx = exc.context
            status = ctx.get("status_code", 0)
            if status == 429:
                budget.record_incident(
                    RateLimitIncident(
                        timestamp=datetime.now(UTC).isoformat(),
                        symbol=symbol,
                        status_code=429,
                        backoff_seconds=10.0,
                        note="Binance 429 during kline fetch",
                    )
                )
        raise

    stage_dir = raw_writer._config.root / "staged" / "universe_expansion" / symbol
    stage_dir.mkdir(parents=True, exist_ok=True)
    norm_res = normalize_binance_kline(
        raw_objects=[raw_object],
        market_type="spot",
        interval="1d",
        venue_id="binance",
        instrument_id=str(instrument_id),
        output_dir=stage_dir,
        code_commit="DATA-008",
    )

    config = DatasetStoreConfig(root=raw_writer._config.root)
    catalog = SqliteDatasetCatalog(db_path)
    try:
        publisher = DatasetPublisher(config, catalog)
        result = publisher.publish(norm_res.publish_plan, register_catalog=True)
    finally:
        catalog.close()

    return result


def _build_canonical_bars(
    all_sources: list[VerifiedSourceBarDataset],
    store_root: Path,
    db_path: Path,
) -> DatasetPublishResult:
    """Build and publish canonical market_bars from all source datasets."""
    canonical_stage_dir = store_root / "staged" / "canonical_universe_expansion"
    canonical_stage_dir.mkdir(parents=True, exist_ok=True)

    canonical_plan_res = publish_canonical_bars(
        source_datasets=all_sources,
        output_dir=canonical_stage_dir,
        code_commit="DATA-008",
        created_at=datetime.now(UTC),
    )

    config = DatasetStoreConfig(root=store_root)
    catalog = SqliteDatasetCatalog(db_path)
    try:
        publisher = DatasetPublisher(config, catalog)
        result = publisher.publish(canonical_plan_res.publish_plan, register_catalog=True)
        resolved_latest = catalog.resolve_latest_by_type("market_bars")
    finally:
        catalog.close()

    print(f"DATA-008 canonical market_bars published: {result.dataset_id}", file=sys.stderr)
    print(f"DATA-008 resolve_latest_by_type market_bars: {resolved_latest}", file=sys.stderr)
    return result


def _analyze_canonical_dataset(
    canonical_ds: DatasetPublishResult,
    store_root: Path,
    symbol_to_iid: dict[str, int],
) -> dict[str, Any]:
    """Compute total bars, span, and per-symbol row counts."""
    import pyarrow.parquet as pq
    from pyarrow import concat_tables

    dataset_base = Path(canonical_ds.manifest_uri).parent
    if not dataset_base.is_absolute():
        dataset_base = store_root / dataset_base

    daily_paths = list((dataset_base / "market_bars" / "daily").rglob("bars.parquet"))
    intraday_paths = list((dataset_base / "market_bars" / "intraday").rglob("bars.parquet"))
    paths = daily_paths or intraday_paths

    if not paths:
        return {
            "total_bar_count": 0,
            "bar_start": None,
            "bar_end": None,
            "symbol_rows": [],
        }

    tables = [pq.read_table(str(p)) for p in paths if p.is_file()]
    table = concat_tables(tables, promote_options="default")
    period_starts = table.column("period_start").to_pylist()
    instrument_ids = table.column("instrument_id").to_pylist()

    dt_values = [datetime.fromtimestamp(ps / 1_000_000, tz=UTC) for ps in period_starts]
    by_iid: dict[int, list[datetime]] = {}
    for iid, ps in zip(instrument_ids, period_starts):
        by_iid.setdefault(int(iid), []).append(datetime.fromtimestamp(ps / 1_000_000, tz=UTC))

    symbol_rows: list[dict[str, Any]] = []
    for symbol, iid in symbol_to_iid.items():
        dates = sorted(by_iid.get(iid, []))
        symbol_rows.append({
            "symbol": symbol,
            "instrument_id": iid,
            "row_count": len(dates),
            "bar_start": dates[0].isoformat() if dates else None,
            "bar_end": dates[-1].isoformat() if dates else None,
        })

    return {
        "total_bar_count": len(period_starts),
        "bar_start": min(dt_values).isoformat(),
        "bar_end": max(dt_values).isoformat(),
        "symbol_rows": symbol_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-008 — expand Binance spot universe")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--start-time", type=str, default="2020-01-01T00:00:00Z")
    parser.add_argument("--end-time", type=str, default=None)
    parser.add_argument("--top-n", type=int, default=100, help="Maximum additional symbols to backfill")
    parser.add_argument("--symbols-per-day", type=int, default=20_000, help="Daily symbol budget")
    parser.add_argument("--report-path", type=str, default="research/sprint_004/36_BINANCE_UNIVERSE_EXPANSION.json")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    args = parser.parse_args()

    end_time = _parse_iso(args.end_time) if args.end_time else _today_utc()
    start_time = _parse_iso(args.start_time)

    data_mode: str
    if args.dry_run:
        print("DATA-008: DRY-RUN mode with mocked responses", file=sys.stderr)
        tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(tmpdir.name) / "exp003.db"
        store_root = Path(tmpdir.name) / "exp003_store"
        raw_root = store_root / "raw"
        data_mode = "synthetic"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        store_root.mkdir(parents=True, exist_ok=True)

        # Seed the temp DB/store from the real ones so we can resolve the existing
        # canonical dataset and source datasets in dry-run mode.
        real_db = Path(args.db_path)
        real_store = Path(args.store_root)
        if real_db.exists() and real_store.exists():
            import shutil
            shutil.copy2(real_db, db_path)
            shutil.copytree(real_store, store_root, dirs_exist_ok=True)
        else:
            apply_migrations(db_path)

        # Mock screener: produce deterministic top symbols.
        extra_symbols = [f"SYM{i:02d}USDT" for i in range(1, 11)]
        mock_tickers = _fetch_symbol_priority_mock(extra_symbols)

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "/api/v3/ticker/24hr" in url:
                return httpx.Response(200, json=mock_tickers)
            if "/api/v3/klines" in url:
                symbol = _extract_symbol_from_url(url)
                params = dict(request.url.params)
                start_ms = int(params.get("startTime", 0))
                end_ms = int(params.get("endTime", 0))
                limit = int(params.get("limit", 1000))
                if start_ms == 0:
                    start_ms = int(start_time.timestamp() * 1000)
                if end_ms == 0:
                    end_ms = int(end_time.timestamp() * 1000)
                return httpx.Response(200, json=_generate_mock_klines(symbol, start_ms, end_ms, limit))
            return httpx.Response(200, json=[])

        client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        screener = BinanceSymbolScreener(client=client)
    else:
        print("DATA-008: real mode — fetching live priority screen", file=sys.stderr)
        data_mode = "real_asof"
        db_path = Path(args.db_path)
        store_root = Path(args.store_root)
        raw_root = store_root / "raw"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        store_root.mkdir(parents=True, exist_ok=True)
        apply_migrations(db_path)
        client = None
        screener = BinanceSymbolScreener()

    # Prepare expansion helpers.
    watermark_store = IncrementalWatermarkStore(WATERMARK_PATH)
    watermarks = watermark_store.load()
    budget = DailySymbolBudget(symbols_per_day=args.symbols_per_day)
    allocator = InstrumentIdAllocator(PAPER_TO_INSTRUMENT_ID)

    expander = BinanceUniverseExpander(
        screener=screener,
        watermark_store=watermark_store,
        budget=budget,
        instrument_allocator=allocator,
        base_symbols=DEFAULT_BASE_SYMBOLS,
        target_start=start_time,
        target_end=end_time,
        top_n=args.top_n,
    )

    new_symbols = expander.select_new_symbols()

    # Resolve latest canonical dataset from DATA-006.
    catalog = SqliteDatasetCatalog(db_path)
    try:
        canonical_dataset_id = catalog.resolve_latest_by_type("market_bars")
    finally:
        catalog.close()

    if canonical_dataset_id is None:
        raise RuntimeError("No existing canonical market_bars dataset found (run DATA-006 first)")

    print(f"DATA-008: base canonical dataset {canonical_dataset_id}", file=sys.stderr)

    # Load existing source datasets.
    existing_sources = _load_existing_source_datasets(db_path, store_root, canonical_dataset_id)
    print(f"DATA-008: loaded {len(existing_sources)} existing source datasets", file=sys.stderr)

    planned_symbols = expander.plan_backfill(new_symbols)
    print(f"DATA-008: {len(new_symbols)} screened; {len(planned_symbols)} planned for this run", file=sys.stderr)

    if not planned_symbols:
        print("DATA-008: no new symbols to backfill", file=sys.stderr)
        return 0

    # Allocate instrument ids for all planned symbols.
    symbol_to_iid = expander.allocate_instrument_ids(planned_symbols)

    # Backfill new symbols.
    raw_catalog = SqliteRawObjectCatalog(db_path)
    raw_config = RawObjectStoreConfig(root=raw_root)
    raw_writer = RawObjectWriter(config=raw_config, catalog=raw_catalog)

    symbol_to_source: dict[str, DatasetPublishResult] = {}
    symbol_rows: list[dict[str, Any]] = []
    for symbol in planned_symbols:
        if not budget.can_process():
            print(f"DATA-008: daily symbol budget reached; stopping at {symbol}", file=sys.stderr)
            break

        instrument_id = symbol_to_iid[symbol]
        symbol_start = load_watermark_as_datetime(watermarks, symbol)
        # Clamp to target window.
        symbol_start = max(symbol_start, start_time)
        symbol_end = min(end_time, _today_utc())
        if symbol_start >= symbol_end:
            print(f"DATA-008: skipping {symbol} (watermark already at end)", file=sys.stderr)
            continue

        try:
            source_ds = _backfill_new_symbol(
                symbol=symbol,
                instrument_id=instrument_id,
                start_time=symbol_start,
                end_time=symbol_end,
                raw_writer=raw_writer,
                db_path=db_path,
                client=client,
                budget=budget,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"DATA-008: ERROR backfilling {symbol}: {exc}", file=sys.stderr)
            continue

        if source_ds.manifest.quality_status.value not in ("PASS", "PASS_WITH_WARNINGS"):
            print(f"DATA-008: skipping {symbol} source dataset {source_ds.dataset_id} quality={source_ds.manifest.quality_status.value}", file=sys.stderr)
            continue

        symbol_to_source[symbol] = source_ds
        budget.record_processed()
        if source_ds.manifest.coverage.event_end:
            watermarks[symbol] = source_ds.manifest.coverage.event_end.isoformat()

        symbol_rows.append({
            "symbol": symbol,
            "instrument_id": instrument_id,
            "source_dataset_id": source_ds.dataset_id,
            "row_count": source_ds.manifest.statistics.row_count,
            "event_start": source_ds.manifest.coverage.event_start.isoformat() if source_ds.manifest.coverage.event_start else None,
            "event_end": source_ds.manifest.coverage.event_end.isoformat() if source_ds.manifest.coverage.event_end else None,
        })
        print(f"DATA-008: backfilled {symbol} -> {source_ds.dataset_id}", file=sys.stderr)

    if not symbol_to_source:
        print("DATA-008: no new source datasets produced; cannot expand canonical bars", file=sys.stderr)
        return 0

    # Load new source datasets as VerifiedSourceBarDataset.
    new_sources: list[VerifiedSourceBarDataset] = []
    for symbol, source_ds in symbol_to_source.items():
        local_files = {
            f.relative_path: source_ds.dataset_path / f.relative_path
            for f in source_ds.manifest.files
            if f.relative_path.endswith("bars.parquet")
        }
        instrument_id = symbol_to_iid[symbol]
        new_sources.append(VerifiedSourceBarDataset(
            local_files=local_files,
            manifest=source_ds.manifest,
            receipt=source_ds.receipt,
            venue_id="binance",
            instrument_id=instrument_id,
            market_type="spot",
            interval="1d",
            schema_variant="quote_notional",
        ))

    # Combine existing and new sources.
    all_sources = existing_sources + new_sources

    # Build canonical bars.
    canonical_ds = _build_canonical_bars(all_sources, store_root, db_path)

    # Update watermarks in real mode.
    if not args.dry_run:
        watermark_store.save(watermarks)

    # Analyze canonical dataset.
    analysis = _analyze_canonical_dataset(canonical_ds, store_root, symbol_to_iid)

    # Build report.
    catalog = SqliteDatasetCatalog(db_path)
    try:
        resolved_latest = catalog.resolve_latest_by_type("market_bars")
    finally:
        catalog.close()

    report = {
        "experiment_id": "DATA-008-BINANCE-UNIVERSE-EXPANSION",
        "data_mode": data_mode,
        "base_canonical_dataset_id": canonical_dataset_id,
        "expanded_canonical_dataset_id": canonical_ds.dataset_id,
        "canonical_dataset_quality_status": canonical_ds.manifest.quality_status.value,
        "catalog_reconciliation": {
            "report_pinned_dataset_id": canonical_ds.dataset_id,
            "resolve_latest_by_type": resolved_latest,
            "match": canonical_ds.dataset_id == resolved_latest,
        },
        "base_symbol_count": len(DEFAULT_BASE_SYMBOLS),
        "added_symbols": sorted(symbol_to_source.keys()),
        "added_symbol_count": len(symbol_to_source),
        "total_symbols": len(DEFAULT_BASE_SYMBOLS) + len(symbol_to_source),
        "total_bar_count": analysis["total_bar_count"],
        "bar_start": analysis["bar_start"],
        "bar_end": analysis["bar_end"],
        "symbol_rows": symbol_rows,
        "rate_limit": budget.to_dict(),
        "incident_count": len(budget.to_dict()["incidents"]),
        "watermarks": dict(watermarks),
        "live_eligible": False,
        "live_eligible_note": "DATA-008 is a data acquisition report; no LIVE authorization.",
        "generated_at": datetime.now(UTC).isoformat(),
    }

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"DATA-008 report written to {report_path}", file=sys.stderr)

    if args.dry_run:
        tmpdir.cleanup()

    return 0


def _extract_symbol_from_url(url: str) -> str:
    """Parse symbol from a Binance klines URL query string."""
    if "symbol=" not in url:
        return "UNKNOWN"
    rest = url.split("symbol=")[1]
    return rest.split("&")[0].upper()


if __name__ == "__main__":
    sys.exit(main())
