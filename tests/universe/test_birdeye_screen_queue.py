"""Tests for UNIVERSE-004 Birdeye listings → screen → OHLCV queue + death rule.

All tests use mocked Birdeye HTTP responses; no live network calls.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from cryptofactors.universe.birdeye_listings import BirdeyeListingsProvider
from cryptofactors.universe.birdeye_screen_queue import (
    BirdeyeScreenQueue,
    PoolStats,
    ScreeningConfig,
)

UTC = timezone.utc


def _sample_listing(address: str, symbol: str, liquidity: float, chain: str = "solana") -> dict[str, Any]:
    return {
        "address": address,
        "symbol": symbol,
        "name": symbol,
        "decimals": 6,
        "liquidityAddedAt": "2026-07-20T00:00:00.000Z",
        "liquidity": liquidity,
        "chain": chain,
    }


def _mock_handler(items: list[dict[str, Any]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/defi/v2/tokens/new_listing" not in url.lower():
            return httpx.Response(404, text="only new_listing is mocked")
        chain = request.headers.get("X-Chain", "solana")
        filtered = [i for i in items if str(i.get("chain", "solana")).lower() == chain.lower()]
        return httpx.Response(200, json={"success": True, "data": {"items": filtered}})

    return httpx.MockTransport(handler)


def _screener(items: list[dict[str, Any]], config: ScreeningConfig) -> BirdeyeScreenQueue:
    client = httpx.Client(transport=_mock_handler(items))
    provider = BirdeyeListingsProvider(api_key="test_key", client=client)
    return BirdeyeScreenQueue(provider=provider, config=config)


def test_screen_passes_on_liquidity_and_chain():
    items = [_sample_listing("0xgood", "GOOD", 50_000.0)]
    config = ScreeningConfig(min_liquidity_usd=10_000, chain_allowlist={"solana"})
    screener = _screener(items, config)
    raw, survivors, rejected = screener.fetch_and_screen("solana")
    assert len(survivors) == 1
    assert rejected == []


def test_screen_rejects_low_liquidity():
    items = [_sample_listing("0xlow", "LOW", 100.0)]
    config = ScreeningConfig(min_liquidity_usd=10_000)
    screener = _screener(items, config)
    raw, survivors, rejected = screener.fetch_and_screen("solana")
    assert len(survivors) == 0
    assert len(rejected) == 1
    assert "low_liquidity" in rejected[0].get("_reject_reason", "")


def test_screen_rejects_chain_not_allowed():
    items = [_sample_listing("0xother", "OTHER", 50_000.0, chain="ethereum")]
    config = ScreeningConfig(min_liquidity_usd=10_000, chain_allowlist={"solana"})
    screener = _screener(items, config)
    raw, survivors, rejected = screener.fetch_and_screen("ethereum")
    assert len(survivors) == 0
    assert len(rejected) == 1


def test_volume_threshold_not_applied_to_listing_screen():
    # volume_24h is missing from Birdeye listings; screen should not reject.
    items = [{"address": "0xnovol", "symbol": "NOVOL", "liquidity": 50_000.0}]
    config = ScreeningConfig(min_liquidity_usd=10_000, min_volume_24h_usd=1_000)
    screener = _screener(items, config)
    raw, survivors, rejected = screener.fetch_and_screen("solana")
    assert len(survivors) == 1


def test_build_queue_has_correct_fields():
    items = [_sample_listing("0xgood", "GOOD", 50_000.0)]
    config = ScreeningConfig(min_liquidity_usd=10_000, as_of=datetime(2026, 7, 20, tzinfo=UTC))
    screener = _screener(items, config)
    raw, survivors, rejected = screener.fetch_and_screen("solana")
    queue = screener.build_queue(survivors)
    assert len(queue) == 1
    item = queue[0]
    assert item.chain == "solana"
    assert item.address == "0xgood"
    assert item.fee_tier is None
    assert "screen_pass" in item.reason
    assert item.enqueued_at == config.as_of


def test_death_rule_marks_dead_after_n_consecutive_days():
    as_of = datetime(2026, 7, 24, tzinfo=UTC)
    listed = [
        {
            "address": "0xdead",
            "chain": "solana",
            "liquidity_added_at": "2026-07-10T00:00:00Z",
        }
    ]
    stats = []
    for i in range(10):
        stats.append(
            PoolStats(
                timestamp=datetime(2026, 7, 14, tzinfo=UTC) + timedelta(days=i),
                chain="solana",
                pool_address="0xdead",
                liquidity=100.0,
                volume_24h=50.0,
            )
        )
    config = ScreeningConfig(
        min_liquidity_usd=10_000,
        min_volume_24h_usd=1_000,
        death_consecutive_days=7,
        as_of=as_of,
    )
    screener = _screener([], config)
    members = screener.apply_death_rule(listed, stats)
    assert len(members) == 1
    assert members[0].is_dead is True
    assert members[0].death_reason == "liquidity_volume_death"


def test_death_rule_does_not_mark_alive_pool_dead():
    as_of = datetime(2026, 7, 24, tzinfo=UTC)
    listed = [
        {
            "address": "0xalive",
            "chain": "solana",
            "liquidity_added_at": "2026-07-10T00:00:00Z",
        }
    ]
    stats = []
    for i in range(10):
        stats.append(
            PoolStats(
                timestamp=datetime(2026, 7, 14, tzinfo=UTC) + timedelta(days=i),
                chain="solana",
                pool_address="0xalive",
                liquidity=100_000.0,
                volume_24h=10_000.0,
            )
        )
    config = ScreeningConfig(
        min_liquidity_usd=10_000,
        min_volume_24h_usd=1_000,
        death_consecutive_days=7,
        as_of=as_of,
    )
    screener = _screener([], config)
    members = screener.apply_death_rule(listed, stats)
    assert members[0].is_dead is False
    assert members[0].death_reason is None


def test_death_rule_not_dead_without_stats():
    as_of = datetime(2026, 7, 24, tzinfo=UTC)
    listed = [
        {
            "address": "0xunknown",
            "chain": "solana",
            "liquidity_added_at": "2026-07-10T00:00:00Z",
        }
    ]
    config = ScreeningConfig(
        min_liquidity_usd=10_000,
        min_volume_24h_usd=1_000,
        death_consecutive_days=7,
        as_of=as_of,
    )
    screener = _screener([], config)
    members = screener.apply_death_rule(listed, [])
    assert members[0].is_dead is False


def test_screen_all_chains_aggregates():
    items = [
        _sample_listing("0xa", "A", 50_000.0, "solana"),
        _sample_listing("0xb", "B", 50_000.0, "arbitrum"),
    ]
    config = ScreeningConfig(min_liquidity_usd=10_000, chain_allowlist={"solana", "arbitrum"})
    screener = _screener(items, config)
    raw, survivors, rejected = screener.screen_all_chains(["solana", "arbitrum"])
    assert len(survivors) == 2
    assert len(rejected) == 0


def test_queue_items_are_serializable():
    as_of = datetime(2026, 7, 20, tzinfo=UTC)
    items = [_sample_listing("0xgood", "GOOD", 50_000.0)]
    config = ScreeningConfig(min_liquidity_usd=10_000, as_of=as_of)
    screener = _screener(items, config)
    raw, survivors, rejected = screener.fetch_and_screen("solana")
    queue = screener.build_queue(survivors)
    d = queue[0].to_dict()
    assert d["chain"] == "solana"
    assert d["address"] == "0xgood"
    assert d["enqueued_at"] == as_of.isoformat()
