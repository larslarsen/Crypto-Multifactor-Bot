#!/usr/bin/env python3
"""Seed ARCH-003 reference identities and compatibility surrogates.

Listing start times are explicitly labeled first-bar proxies. They are not
claims about exchange listing time and must be replaced by source evidence when
that evidence becomes available.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.reference.models import dt_to_iso

BINANCE_VENUE_ID = "venue:binance"
ARBITRUM_VENUE_ID = "venue:arbitrum"
FIRST_BAR_PROXY_AT = "2020-01-01T00:00:00.000000Z"
BINANCE_SYMBOLS = (
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT",
    "DOTUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT", "DOGEUSDT", "UNIUSDT",
    "AAVEUSDT", "CRVUSDT", "APEUSDT", "NEARUSDT", "FILUSDT", "ARBUSDT",
    "OPUSDT", "SUIUSDT", "SEIUSDT", "WLDUSDT", "PEPEUSDT",
)
ASSETS = (
    "BTC", "ETH", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "LTC",
    "BCH", "DOGE", "UNI", "AAVE", "CRV", "APE", "NEAR", "FIL", "ARB",
    "OP", "SUI", "SEI", "WLD", "PEPE", "USDT", "USDC",
)
WETH_CONTRACT = "contract:arbitrum:0x82af49447d8a07e3bd95bd0d56f35241523fbab1"
USDC_CONTRACT = "contract:arbitrum:0xff970a61a04b1ca14834a43f5de4533ebddb5cc8"
DEX_POOLS = (
    (20001, "0xbe3ad6a5669dc0b8b12febc03608860c31e2eef6", "0.01%"),
    (20002, "0xbce73c2e5a623054b0e8e2428e956f4b9d0412a5", "0.05%"),
)


def _parse_known_at(value: str | None) -> str:
    if value is None:
        return dt_to_iso(datetime.now(UTC))
    text = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("--known-at must be timezone-aware")
    return dt_to_iso(parsed.astimezone(UTC))


def _asset_id(symbol: str) -> str:
    return f"asset:{symbol.lower()}"


def _upsert_surrogate(
    conn: sqlite3.Connection,
    *,
    table: str,
    surrogate_column: str,
    surrogate_id: int,
    reference_column: str,
    reference_id: str,
    known_at: str,
) -> None:
    conn.execute(
        f"INSERT INTO {table}({surrogate_column}, {reference_column}, created_at, evidence_json) "
        f"VALUES (?, ?, ?, ?) ON CONFLICT({surrogate_column}) DO UPDATE SET "
        f"{reference_column}=excluded.{reference_column}, evidence_json=excluded.evidence_json",
        (surrogate_id, reference_id, known_at, '{"source":"ARCH-003-static-seed"}'),
    )


def _seed(conn: sqlite3.Connection, known_at: str) -> None:
    conn.execute(
        "INSERT INTO ref_venue(venue_id, venue_code, display_name, venue_type, created_at) "
        "VALUES (?, 'BINANCE', 'Binance', 'CEX', ?) "
        "ON CONFLICT(venue_id) DO UPDATE SET display_name=excluded.display_name",
        (BINANCE_VENUE_ID, known_at),
    )
    conn.execute(
        "INSERT INTO ref_venue(venue_id, venue_code, display_name, venue_type, created_at) "
        "VALUES (?, 'ARBITRUM', 'Arbitrum', 'DEX', ?) "
        "ON CONFLICT(venue_id) DO UPDATE SET display_name=excluded.display_name",
        (ARBITRUM_VENUE_ID, known_at),
    )
    for canonical_asset_id, symbol in enumerate(ASSETS, 1):
        asset_id = _asset_id(symbol)
        asset_class = "STABLE" if symbol in {"USDT", "USDC"} else "CRYPTO"
        conn.execute(
            "INSERT INTO ref_asset(asset_id, asset_class, display_name, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(asset_id) DO UPDATE SET display_name=excluded.display_name",
            (asset_id, asset_class, symbol, known_at),
        )
        _upsert_surrogate(
            conn,
            table="ref_asset_surrogate",
            surrogate_column="canonical_asset_id",
            surrogate_id=canonical_asset_id,
            reference_column="asset_id",
            reference_id=asset_id,
            known_at=known_at,
        )

    contracts = ((10001, WETH_CONTRACT, "ETH"), (10002, USDC_CONTRACT, "USDC"))
    for canonical_id, contract_id, symbol in contracts:
        _, chain, address = contract_id.split(":", 2)
        conn.execute(
            "INSERT INTO ref_instrument(instrument_id, asset_id, venue_id, instrument_type, "
            "base_asset_id, quote_asset_id, created_at, identity_kind, chain, address, fee_tier) "
            "VALUES (?, ?, ?, 'OTHER', ?, NULL, ?, 'token_contract', ?, ?, NULL) "
            "ON CONFLICT(instrument_id) DO UPDATE SET asset_id=excluded.asset_id, "
            "identity_kind=excluded.identity_kind, chain=excluded.chain, address=excluded.address",
            (contract_id, _asset_id(symbol), ARBITRUM_VENUE_ID, _asset_id(symbol), known_at, chain, address),
        )
        _upsert_surrogate(
            conn,
            table="ref_instrument_surrogate",
            surrogate_column="canonical_instrument_id",
            surrogate_id=canonical_id,
            reference_column="instrument_id",
            reference_id=contract_id,
            known_at=known_at,
        )

    for canonical_id, address, fee_tier in DEX_POOLS:
        pool_id = f"pool:arbitrum:{address}:{fee_tier}"
        conn.execute(
            "INSERT INTO ref_instrument(instrument_id, asset_id, venue_id, instrument_type, "
            "base_asset_id, quote_asset_id, created_at, identity_kind, chain, address, fee_tier, "
            "base_instrument_id, quote_instrument_id) "
            "VALUES (?, ?, ?, 'OTHER', ?, ?, ?, 'dex_pool', 'arbitrum', ?, ?, ?, ?) "
            "ON CONFLICT(instrument_id) DO UPDATE SET asset_id=excluded.asset_id, "
            "identity_kind=excluded.identity_kind, chain=excluded.chain, address=excluded.address, "
            "fee_tier=excluded.fee_tier, base_instrument_id=excluded.base_instrument_id, "
            "quote_instrument_id=excluded.quote_instrument_id",
            (pool_id, _asset_id("ETH"), ARBITRUM_VENUE_ID, _asset_id("ETH"), _asset_id("USDC"),
             known_at, address, fee_tier, WETH_CONTRACT, USDC_CONTRACT),
        )
        _upsert_surrogate(
            conn,
            table="ref_instrument_surrogate",
            surrogate_column="canonical_instrument_id",
            surrogate_id=canonical_id,
            reference_column="instrument_id",
            reference_id=pool_id,
            known_at=known_at,
        )

    for canonical_id, symbol in enumerate(BINANCE_SYMBOLS, 1):
        base = symbol.removesuffix("USDT")
        pair_id = f"venue_pair:binance:{symbol}"
        listing_id = f"listing:binance:{symbol}"
        conn.execute(
            "INSERT INTO ref_instrument(instrument_id, asset_id, venue_id, instrument_type, "
            "base_asset_id, quote_asset_id, created_at, identity_kind, chain, address, fee_tier) "
            "VALUES (?, ?, ?, 'SPOT', ?, ?, ?, 'venue_pair', NULL, NULL, NULL) "
            "ON CONFLICT(instrument_id) DO UPDATE SET asset_id=excluded.asset_id, "
            "base_asset_id=excluded.base_asset_id, quote_asset_id=excluded.quote_asset_id, "
            "identity_kind=excluded.identity_kind",
            (pair_id, _asset_id(base), BINANCE_VENUE_ID, _asset_id(base), _asset_id("USDT"), known_at),
        )
        _upsert_surrogate(
            conn,
            table="ref_instrument_surrogate",
            surrogate_column="canonical_instrument_id",
            surrogate_id=canonical_id,
            reference_column="instrument_id",
            reference_id=pair_id,
            known_at=known_at,
        )
        evidence = json.dumps(
            {
                "source": "ARCH-003-static-seed",
                "listing_time_kind": "first_bar_proxy",
                "listing_time_note": "not an exchange listing-time claim",
            },
            sort_keys=True,
        )
        conn.execute(
            "INSERT INTO ref_listing_event(listing_event_id, instrument_id, venue_id, event_type, "
            "valid_from, valid_to, known_from, known_to, evidence_json, venue_symbol) "
            "VALUES (?, ?, ?, 'LIST', ?, NULL, ?, NULL, ?, ?) "
            "ON CONFLICT(listing_event_id) DO UPDATE SET instrument_id=excluded.instrument_id, "
            "valid_from=excluded.valid_from, known_from=excluded.known_from, "
            "evidence_json=excluded.evidence_json, venue_symbol=excluded.venue_symbol",
            (listing_id, pair_id, BINANCE_VENUE_ID, FIRST_BAR_PROXY_AT, known_at, evidence, symbol),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed ARCH-003 reference identity catalog")
    parser.add_argument("--db-path", type=Path, default=Path("exp003.db"))
    parser.add_argument("--known-at", default=None, help="UTC observation time for seed evidence")
    args = parser.parse_args()
    known_at = _parse_known_at(args.known_at)
    args.db_path.parent.mkdir(parents=True, exist_ok=True)
    apply_migrations(args.db_path)
    conn = sqlite3.connect(args.db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        _seed(conn, known_at)
        conn.commit()
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
