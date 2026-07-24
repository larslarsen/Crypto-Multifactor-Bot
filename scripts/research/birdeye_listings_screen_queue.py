#!/usr/bin/env python3
"""UNIVERSE-004 — Birdeye listings → screen → OHLCV queue + liquidity death.

Usage:
    python scripts/research/birdeye_listings_screen_queue.py --dry-run
    python scripts/research/birdeye_listings_screen_queue.py --no-dry-run

Default is dry-run. Real mode requires BIRDEYE_API_KEY in the environment.
Birdeye is used ONLY for /defi/v2/tokens/new_listing (listing events). No OHLCV.
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

from cryptofactors.universe.birdeye_listings import (
    BirdeyeListingsProvider,
)
from cryptofactors.universe.birdeye_screen_queue import (
    DEFAULT_CHAIN_ALLOWLIST,
    DEFAULT_DEATH_CONSECUTIVE_DAYS,
    DEFAULT_MIN_LIQUIDITY_USD,
    DEFAULT_MIN_VOLUME_24H_USD,
    PoolStats,
    ScreeningConfig,
    BirdeyeScreenQueue,
    build_birdeye_screening_provider,
)

UTC = timezone.utc
REPORT_PATH = "research/sprint_004/38_BIRDEYE_LISTINGS_SCREEN_QUEUE.json"


def _mock_handler_factory() -> httpx.HTTPTransport:
    """Return a mock transport that returns synthetic Birdeye listings."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/defi/v2/tokens/new_listing" not in url.lower():
            return httpx.Response(404, text="only new_listing endpoint is mocked")
        chain = request.headers.get("X-Chain", "solana")
        items = [
            {
                "address": "So11111111111111111111111111111111111111112",
                "symbol": "SOL",
                "name": "Wrapped Solana",
                "decimals": 9,
                "liquidityAddedAt": "2026-07-20T00:00:00.000Z",
                "liquidity": 50000.0,
                "volume_24h": 5000.0,
            },
            {
                "address": "DezXAZ8z7PnrnRJjz3wXBoRgixCaADxTk2v2rA4bY71M",
                "symbol": "BONK",
                "name": "Bonk",
                "decimals": 5,
                "liquidityAddedAt": "2026-07-21T00:00:00.000Z",
                "liquidity": 80.0,  # fails liquidity screen
                "volume_24h": 5000.0,
            },
            {
                "address": "7i5KKfX7fTVxnS7v7K7a9R1X3n2X6Z8q1Q2w3e4r5t6y",
                "symbol": "ARB",
                "name": "Arbitrum Token",
                "decimals": 18,
                "liquidityAddedAt": "2026-07-22T00:00:00.000Z",
                "liquidity": 25000.0,
                "volume_24h": 2500.0,
            },
        ]
        # Only return items that match the requested chain for realism.
        filtered = [i for i in items if chain.lower() in i["name"].lower() or chain.lower() == "solana"]
        return httpx.Response(
            200,
            json={"success": True, "data": {"items": filtered}},
        )

    return httpx.MockTransport(handler)


def _build_mock_provider() -> BirdeyeListingsProvider:
    client = httpx.Client(transport=_mock_handler_factory())
    return BirdeyeListingsProvider(api_key="mock_key", client=client)


def _build_live_provider() -> BirdeyeListingsProvider:
    api_key = build_birdeye_screening_provider()._provider._api_key
    return BirdeyeListingsProvider(api_key=api_key)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UNIVERSE-004 — Birdeye listings → screen → OHLCV queue + liquidity death"
    )
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.add_argument("--chains", type=str, default=None,
                        help="Comma-separated chain allowlist (default: solana,arbitrum,ethereum)")
    parser.add_argument("--min-liquidity", type=float, default=DEFAULT_MIN_LIQUIDITY_USD)
    parser.add_argument("--min-volume", type=float, default=DEFAULT_MIN_VOLUME_24H_USD)
    parser.add_argument("--death-days", type=int, default=DEFAULT_DEATH_CONSECUTIVE_DAYS)
    parser.add_argument("--report-path", type=str, default=None)
    args = parser.parse_args()

    as_of = datetime.now(UTC)
    chains = [c.strip() for c in args.chains.split(",")] if args.chains else sorted(DEFAULT_CHAIN_ALLOWLIST)

    if args.report_path:
        report_path = Path(args.report_path)
    elif args.dry_run:
        report_path = Path(tempfile.gettempdir()) / "38_BIRDEYE_LISTINGS_SCREEN_QUEUE.json"
    else:
        report_path = Path(REPORT_PATH)

    data_mode: str
    if args.dry_run:
        print("UNIVERSE-004: DRY-RUN mode with mocked Birdeye responses", file=sys.stderr)
        data_mode = "synthetic"
        provider = _build_mock_provider()
    else:
        print("UNIVERSE-004: real mode — fetching live Birdeye listings", file=sys.stderr)
        data_mode = "real_asof"
        provider = _build_live_provider()
        if not provider._api_key:
            print("UNIVERSE-004: BIRDEYE_API_KEY not set; cannot run real mode", file=sys.stderr)
            return 1

    config = ScreeningConfig(
        min_liquidity_usd=args.min_liquidity,
        min_volume_24h_usd=args.min_volume,
        chain_allowlist=set(chains),
        death_consecutive_days=args.death_days,
        as_of=as_of,
    )

    screener = BirdeyeScreenQueue(provider=provider, config=config)
    raw, survivors, rejected = screener.screen_all_chains(chains=chains)

    queue = screener.build_queue(survivors)

    # For this ticket we have no prior DEX-002 pool stats for newly listed pools.
    # The death rule still runs, and the artifact documents how it would consume
    # DEX-002 pool stats when available. We pass an empty stats list here.
    stats: list[PoolStats] = []
    members = screener.apply_death_rule(survivors, stats)
    alive_members = [m for m in members if not m.is_dead]

    # Build report.
    report: dict[str, Any] = {
        "experiment_id": "UNIVERSE-004-BIRDEYE-LISTINGS-SCREEN-QUEUE",
        "data_mode": data_mode,
        "real_asof": as_of.isoformat() if data_mode == "real_asof" else None,
        "screening_config": {
            "min_liquidity_usd": config.min_liquidity_usd,
            "min_volume_24h_usd": config.min_volume_24h_usd,
            "chain_allowlist": sorted(config.chain_allowlist) if config.chain_allowlist else [],
            "death_consecutive_days": config.death_consecutive_days,
        },
        "listed_count": len(raw),
        "screened_count": len(survivors),
        "rejected_count": len(rejected),
        "dead_count": len(members) - len(alive_members),
        "survivor_count": len(alive_members),
        "ohlcv_request_queue": [q.to_dict() for q in queue],
        "universe_membership": [m.to_dict() for m in members],
        "rejected_listings": [
            {
                "chain": r["chain"],
                "address": r["address"],
                "symbol": r["symbol"],
                "liquidity": r["liquidity"],
                "volume_24h": r.get("volume_24h") or 0.0,
                "reason": _reject_reason(r, config),
            }
            for r in rejected
        ],
        "rate_limit": screener._rate_limiter.to_dict(),
        "death_rule": (
            "Pragmatic DEX death: pool marked inactive when both liquidity "
            f"and volume_24h are below thresholds for {config.death_consecutive_days} "
            "consecutive days, derived from DEX-002 pool stats."
        ),
        "live_eligible": False,
        "live_eligible_note": "UNIVERSE-004 is a research screening queue; no LIVE authorization.",
        "generated_at": datetime.now(UTC).isoformat(),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"UNIVERSE-004 report written to {report_path}", file=sys.stderr)
    return 0


def _reject_reason(record: dict[str, Any], config: ScreeningConfig) -> str:
    reasons: list[str] = []
    if config.chain_allowlist and record["chain"] not in config.chain_allowlist:
        reasons.append(f"chain_not_allowed:{record['chain']}")
    if float(record.get("liquidity") or 0.0) < config.min_liquidity_usd:
        reasons.append("low_liquidity")
    return ",".join(reasons) if reasons else "screen_failed"


if __name__ == "__main__":
    sys.exit(main())
