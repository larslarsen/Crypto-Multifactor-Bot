"""Tests for DEX-002 multi-provider DEX OHLCV fan-out.

All tests use mocked providers so no live network calls are made.
"""

from datetime import datetime, timezone
from typing import Any

from cryptofactors.ingest.dex_fanout import (
    DEXFanOutEngine,
    DexOHLCVProvider,
    PoolOhlcvRecord,
    ProviderResult,
    ScreeningGate,
    ShardedWatermarkStore,
    TokenBucketRateLimiter,
    merge_records,
)

UTC = timezone.utc


class _StaticProvider(DexOHLCVProvider):
    """Provider that returns a fixed list of records."""

    def __init__(self, provider_id: str, records: list[PoolOhlcvRecord], role: str = "primary") -> None:
        self._provider_id = provider_id
        self._records = records
        self._role = role
        self._rate_limiter = TokenBucketRateLimiter(tokens_per_second=1_000)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def role(self) -> str:
        return self._role

    def fetch_pool_ohlcv(
        self,
        *,
        chain: str,
        pool_address: str,
        fee_tier: str | None = None,
        start_time: datetime,
        end_time: datetime,
    ) -> ProviderResult:
        self._rate_limiter.acquire(provider=self._provider_id, chain=chain, pool_address=pool_address)
        filtered = [
            r
            for r in self._records
            if r.chain == chain
            and r.pool_address.lower() == pool_address.lower()
            and start_time <= r.timestamp <= end_time
        ]
        return ProviderResult(
            provider=self._provider_id,
            chain=chain,
            pool_address=pool_address,
            records=filtered,
        )

    def screen_pool(
        self,
        *,
        chain: str,
        pool_address: str,
        min_liquidity_usd: float,
        min_volume_24h_usd: float,
    ) -> dict[str, Any]:
        return {
            "provider": self._provider_id,
            "chain": chain,
            "pool_address": pool_address,
            "liquidity_usd": 50_000.0,
            "volume_24h_usd": 5_000.0,
            "passed": True,
            "note": "mock",
        }

    def get_pool_metadata(self, *, chain: str, pool_address: str) -> dict[str, Any]:
        return {
            "provider": self._provider_id,
            "chain": chain,
            "pool_address": pool_address,
            "liquidity_usd": 50_000.0,
            "volume_24h_usd": 5_000.0,
            "passed": True,
            "note": "mock",
        }


def _day(ts_str: str) -> datetime:
    return datetime.strptime(ts_str, "%Y-%m-%d").replace(tzinfo=UTC)


def _record(
    provider: str,
    chain: str,
    pool_address: str,
    ts_str: str,
    close: float,
    volume: float = 1_000.0,
) -> PoolOhlcvRecord:
    dt = _day(ts_str)
    return PoolOhlcvRecord(
        timestamp=dt,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=volume,
        provider=provider,
        chain=chain,
        pool_address=pool_address,
        fee_tier=None,
        liquidity=None,
        volume_24h=None,
    )


def test_merge_records_prefers_primary():
    chain = "arbitrum"
    pool = "0xaaa"
    primary = ProviderResult(
        provider="geckoterminal",
        chain=chain,
        pool_address=pool,
        records=[_record("geckoterminal", chain, pool, "2026-07-20", 1.0)],
    )
    secondary = ProviderResult(
        provider="dexscreener",
        chain=chain,
        pool_address=pool,
        records=[
            _record("dexscreener", chain, pool, "2026-07-20", 99.0),
            _record("dexscreener", chain, pool, "2026-07-19", 2.0),
        ],
    )
    merged = merge_records([primary, secondary])
    assert len(merged) == 2
    by_ts = {m.timestamp: m for m in merged}
    # Primary value wins on overlap.
    assert by_ts[_day("2026-07-20")].close == 1.0
    assert by_ts[_day("2026-07-20")].provider == "geckoterminal"
    # Gap filled by secondary.
    assert by_ts[_day("2026-07-19")].close == 2.0
    assert by_ts[_day("2026-07-19")].provider == "dexscreener"


def test_merge_records_preserves_provenance():
    chain = "arbitrum"
    pool = "0xbbb"
    primary = ProviderResult(
        provider="geckoterminal",
        chain=chain,
        pool_address=pool,
        records=[_record("geckoterminal", chain, pool, "2026-07-20", 1.0)],
    )
    merged = merge_records([primary])
    assert merged[0].provider == "geckoterminal"
    assert merged[0].pool_address == pool


def test_token_bucket_rate_limiter_tracks_usage():
    limiter = TokenBucketRateLimiter(tokens_per_second=1_000)
    limiter.acquire(provider="a", chain="c", pool_address="0x1")
    state = limiter.to_dict()
    assert state["tokens_per_second"] == 1_000
    assert state["total_requests"] == 1


class _FailingProvider(DexOHLCVProvider):
    def __init__(self, provider_id: str = "bad") -> None:
        self._provider_id = provider_id

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def role(self) -> str:
        return "secondary"

    def fetch_pool_ohlcv(
        self, *, chain: str, pool_address: str, fee_tier: str | None = None, start_time: datetime, end_time: datetime
    ) -> ProviderResult:
        return ProviderResult(provider=self._provider_id, chain=chain, pool_address=pool_address, records=[])

    def screen_pool(
        self, *, chain: str, pool_address: str, min_liquidity_usd: float, min_volume_24h_usd: float
    ) -> dict[str, Any]:
        return {
            "provider": self._provider_id,
            "chain": chain,
            "pool_address": pool_address,
            "liquidity_usd": 100,
            "volume_24h_usd": 50,
            "passed": False,
            "note": "low",
        }


def test_screening_gate_passes_and_fails():
    gate = ScreeningGate(min_liquidity_usd=10_000, min_volume_24h_usd=1_000)
    good = _StaticProvider("good", [])
    bad = _FailingProvider("bad")
    assert gate.screen(chain="c", pool_address="0x1", providers=[good])["passed"]
    assert not gate.screen(chain="c", pool_address="0x2", providers=[bad])["passed"]


def test_engine_merges_and_updates_watermarks(tmp_path):
    chain = "arbitrum"
    pool = "0xccc"
    end = _day("2026-07-20")
    primary = _StaticProvider(
        "geckoterminal",
        [_record("geckoterminal", chain, pool, "2026-07-20", 1.0)],
    )
    secondary = _StaticProvider(
        "dexscreener",
        [_record("dexscreener", chain, pool, "2026-07-19", 2.0)],
        role="secondary",
    )
    watermark_path = tmp_path / "watermarks.json"
    store = ShardedWatermarkStore(watermark_path)
    gate = ScreeningGate(min_liquidity_usd=10_000, min_volume_24h_usd=1_000)
    engine = DEXFanOutEngine(
        providers={"geckoterminal": primary, "dexscreener": secondary},
        screening_gate=gate,
        watermark_store=store,
    )
    work = engine.screen_and_enqueue([{"chain": chain, "address": pool}], end_time=end)
    results = engine.run_work_items(work)
    engine.update_watermarks(results)

    assert len(results) == 1
    assert len(results[0].records) == 2
    assert results[0].providers_used == ["dexscreener", "geckoterminal"]
    key = f"geckoterminal:{chain}:{pool.lower()}"
    assert engine._watermarks[key] == end.isoformat()


def test_engine_marks_dead_pools():
    chain = "arbitrum"
    pool = "0xddd"
    end = _day("2026-07-20")
    primary = _StaticProvider(
        "geckoterminal",
        [_record("geckoterminal", chain, pool, "2026-07-10", 1.0)],
    )
    gate = ScreeningGate(min_liquidity_usd=10_000, min_volume_24h_usd=1_000)
    engine = DEXFanOutEngine(
        providers={"geckoterminal": primary},
        screening_gate=gate,
        watermark_store=ShardedWatermarkStore("/tmp/" + pool),
    )
    work = engine.screen_and_enqueue([{"chain": chain, "address": pool}], end_time=end)
    results = engine.run_work_items(work)
    dead = engine.mark_dead_pools(results, threshold_days=7, as_of=end)
    assert len(dead) == 1
    assert dead[0]["pool_address"] == pool
    assert dead[0]["days_inactive"] == 10


def test_engine_skips_watermark_at_end_time():
    chain = "arbitrum"
    pool = "0xeee"
    end = _day("2026-07-20")
    primary = _StaticProvider(
        "geckoterminal",
        [_record("geckoterminal", chain, pool, "2026-07-20", 1.0)],
    )
    gate = ScreeningGate(min_liquidity_usd=10_000, min_volume_24h_usd=1_000)
    engine = DEXFanOutEngine(
        providers={"geckoterminal": primary},
        screening_gate=gate,
        watermark_store=ShardedWatermarkStore("/tmp/" + pool),
    )
    engine._watermarks = {f"geckoterminal:{chain}:{pool.lower()}": end.isoformat()}
    work = engine.screen_and_enqueue([{"chain": chain, "address": pool}], end_time=end)
    assert work == []


def test_merge_records_empty():
    assert merge_records([]) == []
