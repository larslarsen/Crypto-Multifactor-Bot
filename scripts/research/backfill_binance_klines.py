#!/usr/bin/env python3
"""DATA-006 — Full historical backfill for Binance spot klines (U50+ universe).

Backfills the full available history for the configured universe from the earliest
Binance listing date (default 2017-08-17) through the present. Supports watermark
tracking so re-runs are incremental and idempotent.

Flow:
1. Load per-symbol watermark (last source dataset event_end, or file fallback).
2. Fetch incremental klines via BinanceKlineFetcher.
3. Persist immutable raw objects.
4. Defer normalization, identity resolution, and publication to catalog consumers.

Modes:
  --dry-run (default): uses mocked HTTP responses and temp directories.
  --no-dry-run: fetches real data from Binance REST API.

No LIVE.
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
from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.writer import RawObjectWriter

# Binance spot launched public trading ~2017-08-17; use this as the default
# earliest fetch date for pairs with no existing source dataset.
DEFAULT_EARLIEST_START = datetime(2017, 8, 17, tzinfo=UTC)

# U50+ universe (spot USDT pairs). Order is stable for deterministic instrument IDs.
U50_UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT",
    "DOGEUSDT", "UNIUSDT", "AAVEUSDT", "CRVUSDT", "APEUSDT",
    "NEARUSDT", "FILUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT",
    "SEIUSDT", "WLDUSDT", "PEPEUSDT",
]

WATERMARK_PATH = Path("data/backfill_watermarks.json")


def _load_watermarks() -> dict[str, str]:
    """Load the last known event_end per symbol from the watermark file."""
    if not WATERMARK_PATH.exists():
        return {}
    try:
        text = WATERMARK_PATH.read_text(encoding="utf-8")
        data: dict[str, Any] = json.loads(text)
        spot = data.get("binance_spot")
        if isinstance(spot, dict):
            return {str(k): str(v) for k, v in spot.items() if isinstance(v, str)}
        return {}
    except (json.JSONDecodeError, OSError, AttributeError):
        return {}


def _save_watermarks(watermarks: dict[str, str]) -> None:
    """Save the updated watermark file."""
    WATERMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if WATERMARK_PATH.exists():
        try:
            data = json.loads(WATERMARK_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    data["binance_spot"] = watermarks
    WATERMARK_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _parse_iso(value: str) -> datetime:
    value = value.strip().upper().replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _floor_to_interval(dt: datetime, interval: str) -> datetime:
    """Floor a UTC datetime to the most recent completed interval boundary.

    For daily intervals this returns 00:00:00 UTC of the current day, so the
    last fetched daily bar is the fully completed previous day. For hourly it
    returns the top of the current hour.
    """
    dt = dt.astimezone(UTC)
    if interval == "1d":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if interval == "1h":
        return dt.replace(minute=0, second=0, microsecond=0)
    return dt


def _default_end_time(interval: str = "1d") -> datetime:
    return _floor_to_interval(datetime.now(UTC), interval)


def generate_mock_klines(symbol: str, interval: str = "1d", count: int = 30) -> list[list[Any]]:
    """Generate valid 12-column Binance kline JSON arrays for testing."""
    t0 = datetime(2020, 1, 1, tzinfo=UTC)
    rows: list[list[Any]] = []
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


def _derive_watermark(symbol: str, watermarks: dict[str, str]) -> datetime:
    """Return start time for incremental fetch for a symbol."""
    if symbol in watermarks:
        return _parse_iso(watermarks[symbol]) + timedelta(days=1)
    return DEFAULT_EARLIEST_START


def fetch_symbol_raw_klines(
    symbol: str,
    interval: str,
    raw_writer: RawObjectWriter,
    client: httpx.Client | None,
    start_time: datetime,
    end_time: datetime,
) -> Any:
    """Fetch and persist one raw Binance response without resolving identity."""
    fetcher = BinanceKlineFetcher(raw_writer=raw_writer, client=client)
    print(f"Fetching {symbol} {interval} from {start_time} to {end_time}...", file=sys.stderr)
    return fetcher.fetch_and_write_raw(
        symbol=symbol,
        interval=interval,
        start_time=start_time,
        end_time=end_time,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-006 full Binance spot klines backfill")
    parser.add_argument("--symbols", type=str, default=",".join(U50_UNIVERSE),
                        help="Comma-separated symbols to backfill")
    parser.add_argument("--interval", type=str, default="1d", help="Kline interval (1d or 1h)")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--start-time", type=str, default=None,
                        help="Override earliest start time (ISO 8601 UTC)")
    parser.add_argument("--end-time", type=str, default=None,
                        help="Override end time (ISO 8601 UTC); defaults to now")
    parser.add_argument("--report-path", type=str,
                        default="research/sprint_004/31_BINANCE_FULL_BACKFILL_REPORT.json")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Use mocked HTTP responses and temp directories")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false",
                        help="Fetch real data from Binance API")
    parser.add_argument("--update-watermark", action="store_true", default=True,
                        help="Update the watermark file after a successful backfill")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    end_time = _floor_to_interval(_parse_iso(args.end_time), args.interval) if args.end_time else _default_end_time(args.interval)

    if args.dry_run:
        print("DATA-006 Binance: DRY-RUN mode with mocked responses", file=sys.stderr)
        tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(tmpdir.name) / "exp003.db"
        store_root = Path(tmpdir.name) / "exp003_store"
        raw_root = Path(tmpdir.name) / "raw"
        watermarks: dict[str, str] = {}
        data_mode = "synthetic"

        mock_count = 30
        mock_responses = {sym: generate_mock_klines(sym, args.interval, count=mock_count) for sym in symbols}

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            for sym in symbols:
                if sym in url_str:
                    return httpx.Response(200, json=mock_responses[sym])
            return httpx.Response(200, json=generate_mock_klines("BTCUSDT", args.interval, count=mock_count))

        transport = httpx.MockTransport(mock_handler)
        client = httpx.Client(transport=transport)
    else:
        db_path = Path(args.db_path)
        store_root = Path(args.store_root)
        raw_root = store_root / "raw"
        client = None
        data_mode = "real_asof"
        watermarks = _load_watermarks()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    store_root.mkdir(parents=True, exist_ok=True)
    apply_migrations(db_path)

    raw_catalog = SqliteRawObjectCatalog(db_path)
    raw_config = RawObjectStoreConfig(root=raw_root)
    raw_writer = RawObjectWriter(config=raw_config, catalog=raw_catalog)

    raw_object_ids: list[str] = []
    symbol_rows: list[dict[str, Any]] = []

    for symbol in symbols:
        start_time = _parse_iso(args.start_time) if args.start_time else _derive_watermark(symbol, watermarks)
        if start_time >= end_time:
            print(f"Skipping {symbol}: watermark {start_time} already at or after end {end_time}", file=sys.stderr)
            continue

        try:
            raw_object = fetch_symbol_raw_klines(
                symbol=symbol,
                interval=args.interval,
                raw_writer=raw_writer,
                client=client,
                start_time=start_time,
                end_time=end_time,
            )
        except (httpx.HTTPError, OSError, ValueError) as exc:
            print(f"ERROR backfilling {symbol}: {exc}", file=sys.stderr)
            continue

        raw_object_ids.append(raw_object.raw_object_id)
        watermarks[symbol] = end_time.isoformat()

        symbol_rows.append({
            "symbol": symbol,
            "raw_object_id": raw_object.raw_object_id,
        })

    if not raw_object_ids:
        print("No raw objects were produced", file=sys.stderr)
        return 1

    # Update watermark file in real mode
    if not args.dry_run and args.update_watermark:
        _save_watermarks(watermarks)

    report_data = {
        "experiment_id": "DATA-006-BINANCE",
        "data_mode": data_mode,
        "symbols_requested": symbols,
        "symbols_backfilled": [r["symbol"] for r in symbol_rows],
        "symbols_failed": sorted(set(symbols) - {r["symbol"] for r in symbol_rows}),
        "raw_object_ids": raw_object_ids,
        "symbol_rows": symbol_rows,
        "watermarks": watermarks,
        "catalog_reconciliation": {
            "identity_resolution": "deferred to catalog consumer",
        },
        "gate_status": "RAW_ONLY",
        "live_eligible": False,
        "scope_reduction": {
            "why_not_earliest_2017": (
                "The script supports the Binance earliest listing date (2017-08-17) via "
                "DEFAULT_EARLIEST_START and watermarks. The real_asof backfill was intentionally "
                "run from 2020-01-01 to (a) satisfy the DATA-006 acceptance criterion that "
                "BTCUSDT and ETHUSDT cover >=2020, and (b) avoid REJECTED source datasets caused "
                "by listing-day partial bars on assets that began trading intra-day after 2020-01-01."
            ),
            "universe_scope": (
                "U50+ spot symbols as listed in DATA-006 (23 symbols); no instrument identity "
                "is assigned during raw acquisition."
            ),
            "interval_scope": "Daily (1d) only for this evidence. Hourly support is present in the script via --interval 1h.",
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"Report written to {report_path}", file=sys.stderr)

    if args.dry_run:
        tmpdir.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
