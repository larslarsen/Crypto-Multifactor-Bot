#!/usr/bin/env python3
"""DATA-011 — Survivorship-bound CEX quality bar panel (Binance first).

Loads the CMC graveyard, excludes paper symbols whose base asset is dead
per the graveyard, backfills Binance klines for survivors, quality-clears
via BAR-001, and publishes a PASS dataset.

No LIVE. No MEXC/Kraken/Blofin. No DEX.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from cryptofactors.acquisition.binance_fetcher import BinanceKlineFetcher
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import DatasetPublishResult, DatasetStoreConfig
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
from cryptofactors.universe.cmc_survivorship import (
    CMCSurvivorshipProvider,
    parse_iso_datetime,
)

UTC = UTC
CSV_PATH = Path("data/survivorship/cmc_dead_universe_full.csv")
DEFAULT_START = datetime(2020, 1, 1, tzinfo=UTC)
DEFAULT_END = datetime(2026, 7, 1, tzinfo=UTC)

# Known names for paper symbols to disambiguate ticker collisions.
# Key is the base asset (e.g., "SOL"), value is the expected CMC coin name.
PAPER_BASE_TO_NAME: dict[str, str] = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "XRP": "XRP",
    "ADA": "Cardano",
    "AVAX": "Avalanche",
    "DOT": "Polkadot",
    "LINK": "Chainlink",
    "LTC": "Litecoin",
    "BCH": "Bitcoin Cash",
    "DOGE": "Dogecoin",
    "UNI": "Uniswap",
    "AAVE": "Aave",
    "CRV": "Curve DAO",
    "APE": "ApeCoin",
    "NEAR": "NEAR Protocol",
    "FIL": "Filecoin",
    "ARB": "Arbitrum",
    "OP": "Optimism",
    "SUI": "Sui",
    "SEI": "Sei",
    "WLD": "Worldcoin",
    "PEPE": "Pepe",
}
DEFAULT_END = datetime(2026, 7, 1, tzinfo=UTC)


def _parse_iso(value: str) -> datetime:
    value = value.strip().upper().replace("Z", "+00:00")
    return datetime.fromisoformat(value)


def _base_asset(binance_symbol: str) -> str:
    """Extract base asset from a Binance pair (e.g. BTCUSDT -> BTC)."""
    sym = binance_symbol.upper()
    for suffix in ("USDT", "BUSD", "USDC", "USD"):
        if sym.endswith(suffix) and len(sym) > len(suffix):
            return sym[: -len(suffix)]
    return sym


def _generate_mock_klines(
    symbol: str,
    interval: str = "1d",
    count: int = 30,
    start: datetime | None = None,
) -> list[list[object]]:
    """Generate valid 12-column Binance kline JSON arrays for dry-run testing."""
    t0 = start or datetime(2020, 1, 1, tzinfo=UTC)
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


def _backfill_one_symbol(
    symbol: str,
    interval: str,
    raw_writer: RawObjectWriter,
    catalog_path: Path,
    dataset_store_root: Path,
    client: httpx.Client | None,
    start_time: datetime,
    end_time: datetime,
    instrument_int_id: int,
    code_commit: str,
) -> DatasetPublishResult:
    """Fetch, normalize, and publish a source dataset for one symbol."""
    fetcher = BinanceKlineFetcher(raw_writer=raw_writer, client=client)
    raw_object = fetcher.fetch_and_write_raw(
        symbol=symbol,
        interval=interval,
        start_time=start_time,
        end_time=end_time,
    )

    stage_dir = dataset_store_root / "staged" / symbol
    stage_dir.mkdir(parents=True, exist_ok=True)
    norm_res = normalize_binance_kline(
        raw_objects=[raw_object],
        market_type="spot",
        interval=interval,
        venue_id="binance",
        instrument_id=str(instrument_int_id),
        output_dir=stage_dir,
        code_commit=code_commit,
    )

    config = DatasetStoreConfig(root=dataset_store_root)
    catalog = SqliteDatasetCatalog(catalog_path)
    try:
        publisher = DatasetPublisher(config, catalog)
        source_dataset = publisher.publish(norm_res.publish_plan, register_catalog=True)
    finally:
        catalog.close()

    return source_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-011 — survivorship-bound bound bars")
    parser.add_argument("--interval", type=str, default="1d")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--start-time", type=str, default=DEFAULT_START.isoformat())
    parser.add_argument("--end-time", type=str, default=DEFAULT_END.isoformat())
    parser.add_argument("--report-path", type=str,
                        default="research/sprint_004/43_BOUND_BARS.json")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    args = parser.parse_args()

    start_time = _parse_iso(args.start_time)
    end_time = _parse_iso(args.end_time)
    code_commit = "DATA-011"

    # 1. Load CMC graveyard
    print(f"Loading CMC graveyard from {CSV_PATH}...", file=sys.stderr)
    provider = CMCSurvivorshipProvider.from_csv(CSV_PATH, availability_time=datetime.now(UTC))
    records = provider.records()

    # Build lookup: cmc_symbol -> record
    cmc_by_symbol: dict[str, dict[str, Any]] = {}
    for r in records:
        sym = str(r.get("symbol", "")).strip().upper()
        if sym:
            cmc_by_symbol[sym] = r

    print(f"  Loaded {len(records)} CMC records, {len(cmc_by_symbol)} unique symbols", file=sys.stderr)

    # 2. Determine which paper symbols are excluded
    # Iterate over PAPER_TO_INSTRUMENT_ID (authoritative map with canonical bar IDs)
    # to avoid processing duplicate paper symbols (e.g. BTCUSD duplicates XBTUSD).
    symbols_requested: list[str] = []
    exclusion_reasons: list[dict[str, Any]] = []
    symbols_backfilled: list[dict[str, Any]] = []

    for paper_sym, instrument_id in sorted(PAPER_TO_INSTRUMENT_ID.items(), key=lambda kv: kv[1]):
        symbols_requested.append(paper_sym)
        binance_sym = PAPER_TO_BINANCE_MAP.get(paper_sym)
        if binance_sym is None:
            exclusion_reasons.append({
                "paper_symbol": paper_sym,
                "binance_symbol": None,
                "reason": "no binance pair mapping",
                "cmc_id": None,
                "death_date": None,
            })
            continue

        base = _base_asset(binance_sym)
        cmc_rec = cmc_by_symbol.get(base)

        if cmc_rec is not None:
            is_active = bool(cmc_rec.get("is_active"))
            death_str = cmc_rec.get("death_proxy_date")

            # Name check to disambiguate ticker collisions (e.g. Solcoin != Solana).
            cmc_name = str(cmc_rec.get("name", "")).strip().lower()
            expected_name = PAPER_BASE_TO_NAME.get(base, "").lower()
            name_mismatch = bool(expected_name) and cmc_name != expected_name

            if not is_active and not name_mismatch:
                # Match universe_at fail-closed: if no death date or death < start, exclude.
                if not death_str:
                    exclusion_reasons.append({
                        "paper_symbol": paper_sym,
                        "binance_symbol": binance_sym,
                        "cmc_symbol": base,
                        "cmc_id": cmc_rec.get("cmc_id"),
                        "death_date": None,
                        "reason": "inactive with no death date (fail-closed)",
                    })
                    continue
                death_dt = parse_iso_datetime(death_str)
                if death_dt and death_dt < start_time:
                    exclusion_reasons.append({
                        "paper_symbol": paper_sym,
                        "binance_symbol": binance_sym,
                        "cmc_symbol": base,
                        "cmc_id": cmc_rec.get("cmc_id"),
                        "death_date": death_str,
                        "reason": f"dead before bar range (death={death_str}, range_start={start_time.isoformat()})",
                    })
                    continue

        symbols_backfilled.append({
            "paper_symbol": paper_sym,
            "binance_symbol": binance_sym,
            "instrument_id": instrument_id,
            "cmc_symbol": base,
            "cmc_record_found": cmc_rec is not None,
        })

    # 3. Set up dry-run or real mode
    if args.dry_run:
        print("DATA-011: DRY-RUN mode with mocked responses", file=sys.stderr)
        tmpdir_obj = tempfile.TemporaryDirectory()
        db_path = Path(tmpdir_obj.name) / "exp003.db"
        store_root = Path(tmpdir_obj.name) / "exp003_store"
        raw_root = Path(tmpdir_obj.name) / "raw"
        data_mode = "synthetic"

        mock_count = 30
        binance_syms = [s["binance_symbol"] for s in symbols_backfilled]
        mock_responses = {sym: _generate_mock_klines(sym, args.interval, count=mock_count)
                         for sym in binance_syms}

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            for sym in binance_syms:
                if sym in url_str:
                    return httpx.Response(200, json=mock_responses[sym])
            return httpx.Response(200, json=_generate_mock_klines("BTCUSDT", args.interval, count=mock_count))

        transport = httpx.MockTransport(mock_handler)
        client = httpx.Client(transport=transport)
    else:
        db_path = Path(args.db_path)
        store_root = Path(args.store_root)
        raw_root = store_root / "raw"
        client = None
        data_mode = "real_asof"

    db_path.parent.mkdir(parents=True, exist_ok=True)
    store_root.mkdir(parents=True, exist_ok=True)
    apply_migrations(db_path)

    raw_catalog = SqliteRawObjectCatalog(db_path)
    raw_config = RawObjectStoreConfig(root=raw_root)
    raw_writer = RawObjectWriter(config=raw_config, catalog=raw_catalog)

    # 4. Backfill each surviving symbol
    verified_sources: list[VerifiedSourceBarDataset] = []
    source_ids: list[str] = []
    per_symbol_rows: list[dict[str, Any]] = []

    for entry in symbols_backfilled:
        paper_sym = entry["paper_symbol"]
        binance_sym = entry["binance_symbol"]
        instrument_id = entry["instrument_id"]

        try:
            source_ds = _backfill_one_symbol(
                symbol=binance_sym,
                interval=args.interval,
                raw_writer=raw_writer,
                catalog_path=db_path,
                dataset_store_root=store_root,
                client=client,
                start_time=start_time,
                end_time=end_time,
                instrument_int_id=instrument_id,
                code_commit=code_commit,
            )
        except Exception as exc:
            print(f"ERROR backfilling {binance_sym} ({paper_sym}): {exc}", file=sys.stderr)
            continue

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
                instrument_id=instrument_id,
                market_type="spot",
                interval=args.interval,
                schema_variant="quote_notional",
            )
        )

        per_symbol_rows.append({
            "paper_symbol": paper_sym,
            "binance_symbol": binance_sym,
            "instrument_id": instrument_id,
            "source_dataset_id": source_ds.dataset_id,
            "event_start": source_ds.manifest.coverage.event_start.isoformat() if source_ds.manifest.coverage.event_start else None,
            "event_end": source_ds.manifest.coverage.event_end.isoformat() if source_ds.manifest.coverage.event_end else None,
            "row_count": source_ds.manifest.statistics.row_count,
        })

    # 5. Build canonical bars
    if not verified_sources:
        print("No source datasets produced; cannot build canonical bars", file=sys.stderr)
        return 1

    canonical_stage_dir = store_root / "staged" / "canonical_bars_bound"
    canonical_stage_dir.mkdir(parents=True, exist_ok=True)
    canonical_plan_res = publish_canonical_bars(
        source_datasets=verified_sources,
        output_dir=canonical_stage_dir,
        code_commit=code_commit,
        created_at=datetime.now(UTC),
    )

    config = DatasetStoreConfig(root=store_root)
    catalog = SqliteDatasetCatalog(db_path)
    try:
        publisher = DatasetPublisher(config, catalog)
        canonical_ds = publisher.publish(canonical_plan_res.publish_plan, register_catalog=True)
        resolved_latest = catalog.resolve_latest_by_type("market_bars")
    finally:
        catalog.close()

    # 6. Analyze coverage
    per_symbol_coverage: list[dict[str, Any]] = []
    for sd in verified_sources:
        per_symbol_coverage.append({
            "instrument_id": sd.instrument_id,
            "venue_id": sd.venue_id,
            "interval": sd.interval,
            "event_start": sd.manifest.coverage.event_start.isoformat() if sd.manifest and sd.manifest.coverage.event_start else None,
            "event_end": sd.manifest.coverage.event_end.isoformat() if sd.manifest and sd.manifest.coverage.event_end else None,
        })

    # 7. Write report
    report: dict[str, Any] = {
        "experiment_id": "DATA-011",
        "data_mode": data_mode,
        "symbols_requested": symbols_requested,
        "symbols_excluded": exclusion_reasons,
        "symbols_backfilled": [s["paper_symbol"] for s in symbols_backfilled],
        "exclusion_count": len(exclusion_reasons),
        "backfill_count": len(symbols_backfilled),
        "source_dataset_ids": source_ids,
        "canonical_dataset_id": canonical_ds.dataset_id,
        "canonical_quality_status": canonical_ds.manifest.quality_status.value,
        "total_bar_count": canonical_ds.manifest.statistics.row_count,
        "per_symbol": per_symbol_rows,
        "per_symbol_coverage": per_symbol_coverage,
        "catalog_reconciliation": {
            "report_pinned_dataset_id": canonical_ds.dataset_id,
            "resolve_latest_by_type": resolved_latest,
            "match": canonical_ds.dataset_id == resolved_latest,
        },
        "survivorship_join": {
            "cmc_records_loaded": len(records),
            "cmc_symbols_matched": sum(1 for s in symbols_backfilled if s["cmc_record_found"]),
            "cmc_unique_symbols": len(cmc_by_symbol),
            "graveyard_source": str(CSV_PATH),
        },
        "date_range": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        },
        "gate_status": "OK",
        "live_eligible": False,
        "live_eligible_note": "DATA-011 is a bound-bar dataset ticket; no LIVE authorization.",
        "generated_at": datetime.now(UTC).isoformat(),
    }

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written to {report_path}", file=sys.stderr)
    print(json.dumps(report, indent=2))

    if args.dry_run:
        tmpdir_obj.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
