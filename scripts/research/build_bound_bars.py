#!/usr/bin/env python3
"""DATA-011 raw Binance acquisition stage.

This stage fetches and stores immutable raw exchange responses only. Catalog
identity resolution, survivorship binding, normalization, and bar publication
are downstream consumer responsibilities.
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

DEFAULT_SYMBOLS = (
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT",
    "DOTUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT", "DOGEUSDT", "UNIUSDT",
    "AAVEUSDT", "CRVUSDT", "APEUSDT", "NEARUSDT", "FILUSDT", "ARBUSDT",
    "OPUSDT", "SUIUSDT", "SEIUSDT", "WLDUSDT", "PEPEUSDT",
)
DEFAULT_START = datetime(2020, 1, 1, tzinfo=UTC)
DEFAULT_END = datetime(2026, 7, 1, tzinfo=UTC)

# Compatibility metadata retained for legacy CMC-validation consumers. It is
# not used to select acquisition symbols or resolve catalog identity.
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


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.strip().upper())
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _base_asset(venue_symbol: str) -> str:
    """Return a legacy base-symbol view for CMC validation compatibility."""
    symbol = venue_symbol.upper()
    for quote in ("USDT", "BUSD", "USDC", "USD"):
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return symbol[: -len(quote)]
    return symbol


def _mock_klines(count: int = 30) -> list[list[Any]]:
    rows: list[list[Any]] = []
    start = datetime(2020, 1, 1, tzinfo=UTC)
    for i in range(count):
        opening = start + timedelta(days=i)
        closing = opening + timedelta(days=1) - timedelta(milliseconds=1)
        open_price = 50_000.0 + i * 10.0
        volume = 100.0 + i
        rows.append([
            int(opening.timestamp() * 1000), f"{open_price:.2f}",
            f"{open_price + 500:.2f}", f"{open_price - 500:.2f}",
            f"{open_price + 50:.2f}", f"{volume:.4f}",
            int(closing.timestamp() * 1000), f"{volume * open_price:.2f}",
            100 + i, f"{volume / 2:.4f}", f"{volume * open_price / 2:.2f}", "0",
        ])
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-011 raw Binance acquisition")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--db-path", type=Path, default=Path("exp003.db"))
    parser.add_argument("--store-root", type=Path, default=Path("data/exp003_store"))
    parser.add_argument("--start-time", default=DEFAULT_START.isoformat())
    parser.add_argument("--end-time", default=DEFAULT_END.isoformat())
    parser.add_argument("--report-path", type=Path, default=Path("research/sprint_004/43_BOUND_BARS.json"))
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    start_time = _parse_iso(args.start_time)
    end_time = _parse_iso(args.end_time)

    if args.dry_run:
        print("DATA-011: DRY-RUN raw acquisition", file=sys.stderr)
        tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(tmpdir.name) / "exp003.db"
        store_root = Path(tmpdir.name) / "exp003_store"
        raw_root = Path(tmpdir.name) / "raw"
        responses = {symbol: _mock_klines() for symbol in symbols}

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            for symbol in symbols:
                if symbol in url:
                    return httpx.Response(200, json=responses[symbol])
            return httpx.Response(404, text="symbol not found")

        client: httpx.Client | None = httpx.Client(transport=httpx.MockTransport(handler))
    else:
        db_path = args.db_path
        store_root = args.store_root
        raw_root = store_root / "raw"
        client = None

    db_path.parent.mkdir(parents=True, exist_ok=True)
    store_root.mkdir(parents=True, exist_ok=True)
    apply_migrations(db_path)
    raw_catalog = SqliteRawObjectCatalog(db_path)
    writer = RawObjectWriter(config=RawObjectStoreConfig(root=raw_root), catalog=raw_catalog)
    raw_objects: list[dict[str, str]] = []

    try:
        fetcher = BinanceKlineFetcher(raw_writer=writer, client=client)
        for symbol in symbols:
            try:
                raw = fetcher.fetch_and_write_raw(
                    symbol=symbol,
                    interval=args.interval,
                    start_time=start_time,
                    end_time=end_time,
                )
                raw_objects.append({
                    "symbol": symbol,
                    "raw_object_id": raw.raw_object_id,
                })
            except (httpx.HTTPError, OSError, ValueError) as exc:
                print(f"ERROR acquiring {symbol}: {exc}", file=sys.stderr)
    finally:
        raw_catalog.close()
        if client is not None:
            client.close()

    if not raw_objects:
        return 1
    report = {
        "experiment_id": "DATA-011",
        "data_mode": "synthetic" if args.dry_run else "real_asof",
        "symbols_requested": symbols,
        "raw_objects": raw_objects,
        "identity_resolution": "deferred to catalog consumer",
        "canonical_publication": "deferred",
        "live_eligible": False,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.dry_run:
        tmpdir.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
