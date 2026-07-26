"""DEX-002 — Multi-provider free DEX OHLCV fan-out.

Provider interface + token-bucket rate limiters + sharded watermarks +
merge/dedupe policy + screening gate + pragmatic DEX death.

Provider ranking (from DATA-007 recommended_fanout):
  1. geckoterminal (primary)
  2. dexscreener (secondary, gap-fill)
  3. defillama (tertiary, liquidity/volume context)

No Birdeye OHLCV. No LIVE.
"""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final

import httpx

from cryptofactors.ingest.dex_ohlcv import (
    GeckoTerminalClient,
)

UTC: Final = timezone.utc

DEFAULT_PRIMARY_RATE: Final[float] = 6.0 / 60.0  # 6 req/min
DEFAULT_SECONDARY_RATE: Final[float] = 60.0 / 60.0  # 60 req/min polite
DEFAULT_TERTIARY_RATE: Final[float] = 2.0  # 2 req/sec


class DexFanOutError(RuntimeError):
    """Base error for DEX fan-out operations."""


# ---------------------------------------------------------------------------
# Token-bucket rate limiter
# ---------------------------------------------------------------------------


@dataclass
class RateLimitIncident:
    timestamp: str
    provider: str
    chain: str
    pool_address: str
    status_code: int
    backoff_seconds: float
    note: str


class TokenBucketRateLimiter:
    """Simple token-bucket / min-interval rate limiter."""

    def __init__(self, *, tokens_per_second: float, burst: int = 1) -> None:
        if tokens_per_second <= 0:
            raise DexFanOutError("tokens_per_second must be positive")
        self._tokens_per_second: float = tokens_per_second
        self._burst: int = max(1, burst)
        self._tokens: float = float(self._burst)
        self._last_update: float = time.monotonic()
        self._incidents: list[RateLimitIncident] = []
        self._total_requests: int = 0

    def acquire(self, *, provider: str, chain: str, pool_address: str) -> None:
        """Block until one token is available."""
        while True:
            now = time.monotonic()
            elapsed = now - self._last_update
            self._tokens = min(self._burst, self._tokens + elapsed * self._tokens_per_second)
            self._last_update = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                self._total_requests += 1
                return
            # Sleep until the next token is available.
            sleep_s = (1.0 - self._tokens) / self._tokens_per_second
            time.sleep(max(0.001, sleep_s))

    def record_incident(self, incident: RateLimitIncident) -> None:
        self._incidents.append(incident)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tokens_per_second": self._tokens_per_second,
            "burst": self._burst,
            "total_requests": self._total_requests,
            "incidents": [
                {
                    "timestamp": inc.timestamp,
                    "provider": inc.provider,
                    "chain": inc.chain,
                    "pool_address": inc.pool_address,
                    "status_code": inc.status_code,
                    "backoff_seconds": inc.backoff_seconds,
                    "note": inc.note,
                }
                for inc in self._incidents
            ],
        }


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoolOhlcvRecord:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    provider: str
    chain: str
    pool_address: str
    fee_tier: str | None
    liquidity: float | None
    volume_24h: float | None


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    chain: str
    pool_address: str
    records: list[PoolOhlcvRecord]
    incident: RateLimitIncident | None = None


class DexOHLCVProvider(ABC):
    """Abstract DEX OHLCV provider."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Short identifier matching DATA-007 source_id."""

    @property
    @abstractmethod
    def role(self) -> str:
        """primary | secondary | tertiary."""

    @property
    def produces_ohlcv(self) -> bool:
        """Whether this provider contributes OHLCV records for gap-fill/merge.

        Tertiary providers (e.g., DefiLlama) may only provide screening context
        and do not produce time-series data. They are excluded from work items.
        """
        return True

    @abstractmethod
    def fetch_pool_ohlcv(
        self,
        *,
        chain: str,
        pool_address: str,
        fee_tier: str | None = None,
        start_time: datetime,
        end_time: datetime,
    ) -> ProviderResult:
        """Fetch OHLCV records for a single pool."""

    def screen_pool(
        self,
        *,
        chain: str,
        pool_address: str,
        min_liquidity_usd: float,
        min_volume_24h_usd: float,
        base_token_address: str | None = None,
        quote_token_address: str | None = None,
    ) -> dict[str, Any]:
        """Return pool metadata for screening.

        Fail-closed (DEX-002 rework): a provider with no screening evidence cannot
        admit a pool. The previous default returned ``passed=True``, which let pools
        through on no evidence at all.
        """
        return {
            "provider": self.provider_id,
            "chain": chain,
            "pool_address": pool_address,
            "liquidity_usd": None,
            "volume_24h_usd": None,
            "passed": False,
            "note": "no screening data available",
        }


class GeckoTerminalProvider(DexOHLCVProvider):
    """Primary provider using the existing GeckoTerminal client.

    The GeckoTerminal public API only permits data within the most recent
    180 days. We clip the request window to that range so pagination never
    asks the API for a ``before_timestamp`` beyond the free tier.

    Supports multi-chain backfill by lazily creating a chain-specific client.
    """

    _MAX_FREE_LOOKBACK_DAYS: int = 180

    def __init__(
        self,
        *,
        gecko_client: GeckoTerminalClient | None = None,
        http_client: httpx.Client | None = None,
        rate_limiter: TokenBucketRateLimiter | None = None,
        requests_per_minute: int | None = None,
    ) -> None:
        self._clients: dict[str, GeckoTerminalClient] = {}
        if gecko_client is not None:
            # Backward compatibility: single injected client defaults to the
            # legacy network, but we still allow multi-chain lookups by using
            # the client's configured network.
            self._clients[gecko_client._network] = gecko_client
        self._http_client: httpx.Client | None = http_client
        self._requests_per_minute: int | None = requests_per_minute
        self._rate_limiter: TokenBucketRateLimiter = rate_limiter or TokenBucketRateLimiter(
            tokens_per_second=DEFAULT_PRIMARY_RATE,
        )

    def _client_for_chain(self, chain: str) -> GeckoTerminalClient:
        chain = chain.strip()
        if chain not in self._clients:
            kwargs: dict[str, Any] = {"network": chain, "client": self._http_client}
            if self._requests_per_minute is not None:
                kwargs["requests_per_minute"] = self._requests_per_minute
            self._clients[chain] = GeckoTerminalClient(**kwargs)
        return self._clients[chain]

    @property
    def provider_id(self) -> str:
        return "geckoterminal"

    @property
    def role(self) -> str:
        return "primary"

    def fetch_pool_ohlcv(
        self,
        *,
        chain: str,
        pool_address: str,
        fee_tier: str | None = None,
        start_time: datetime,
        end_time: datetime,
    ) -> ProviderResult:
        # Clip the request window to the free-tier lookback.
        clipped_start = max(
            start_time,
            end_time - timedelta(days=self._MAX_FREE_LOOKBACK_DAYS),
        )
        self._rate_limiter.acquire(provider=self.provider_id, chain=chain, pool_address=pool_address)
        client = self._client_for_chain(chain)
        try:
            records = client.fetch_pool_ohlcv(
                pool_address=pool_address,
                fee_tier=fee_tier or "0.05%",
                start_time=clipped_start,
                end_time=end_time,
            )
        except Exception as exc:  # noqa: BLE001
            note = str(exc)
            incident = RateLimitIncident(
                timestamp=datetime.now(UTC).isoformat(),
                provider=self.provider_id,
                chain=chain,
                pool_address=pool_address,
                status_code=0,
                backoff_seconds=0.0,
                note=note,
            )
            self._rate_limiter.record_incident(incident)
            return ProviderResult(
                provider=self.provider_id,
                chain=chain,
                pool_address=pool_address,
                records=[],
                incident=incident,
            )

        out: list[PoolOhlcvRecord] = []
        for r in records:
            ts = datetime.fromisoformat(r["timestamp"])
            out.append(
                PoolOhlcvRecord(
                    timestamp=ts,
                    open=r["open"],
                    high=r["high"],
                    low=r["low"],
                    close=r["close"],
                    volume=r["volume"],
                    provider=self.provider_id,
                    chain=chain,
                    pool_address=pool_address,
                    fee_tier=fee_tier,
                    liquidity=None,
                    volume_24h=None,
                )
            )

        return ProviderResult(
            provider=self.provider_id,
            chain=chain,
            pool_address=pool_address,
            records=out,
        )


class DexScreenerProvider(DexOHLCVProvider):
    """Secondary provider: limited OHLCV via pair endpoints."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        rate_limiter: TokenBucketRateLimiter | None = None,
    ) -> None:
        self._client: httpx.Client | None = client
        self._rate_limiter: TokenBucketRateLimiter = rate_limiter or TokenBucketRateLimiter(
            tokens_per_second=DEFAULT_SECONDARY_RATE,
        )

    @property
    def provider_id(self) -> str:
        return "dexscreener"

    @property
    def role(self) -> str:
        return "secondary"

    def _get(self, url: str) -> httpx.Response:
        if self._client:
            return self._client.get(url)
        with httpx.Client(timeout=30.0) as c:
            return c.get(url)

    def fetch_pool_ohlcv(
        self,
        *,
        chain: str,
        pool_address: str,
        fee_tier: str | None = None,
        start_time: datetime,
        end_time: datetime,
    ) -> ProviderResult:
        self._rate_limiter.acquire(provider=self.provider_id, chain=chain, pool_address=pool_address)
        url = f"https://api.dexscreener.com/latest/dex/pairs/{chain}/{pool_address}"
        try:
            r = self._get(url)
            if r.status_code != 200:
                incident = RateLimitIncident(
                    timestamp=datetime.now(UTC).isoformat(),
                    provider=self.provider_id,
                    chain=chain,
                    pool_address=pool_address,
                    status_code=r.status_code,
                    backoff_seconds=0.0,
                    note="DexScreener non-200 response",
                )
                self._rate_limiter.record_incident(incident)
                return ProviderResult(
                    provider=self.provider_id,
                    chain=chain,
                    pool_address=pool_address,
                    records=[],
                    incident=incident,
                )
            data = r.json()
        except Exception as exc:  # noqa: BLE001
            incident = RateLimitIncident(
                timestamp=datetime.now(UTC).isoformat(),
                provider=self.provider_id,
                chain=chain,
                pool_address=pool_address,
                status_code=0,
                backoff_seconds=0.0,
                note=str(exc),
            )
            self._rate_limiter.record_incident(incident)
            return ProviderResult(
                provider=self.provider_id,
                chain=chain,
                pool_address=pool_address,
                records=[],
                incident=incident,
            )

        # DEX-002 rework: DexScreener returns a current-price snapshot, not interval
        # bars. Turning one into a candle with open=high=low=close and 24h volume
        # attached to a single timestamp fabricates a bar that is indistinguishable
        # downstream from an observed one. DATA-007 classifies this provider as pool
        # statistics only, so it contributes no OHLCV rows.
        del data
        return ProviderResult(
            provider=self.provider_id,
            chain=chain,
            pool_address=pool_address,
            records=[],
        )

    def screen_pool(
        self,
        *,
        chain: str,
        pool_address: str,
        min_liquidity_usd: float,
        min_volume_24h_usd: float,
        base_token_address: str | None = None,
        quote_token_address: str | None = None,
    ) -> dict[str, Any]:
        url = f"https://api.dexscreener.com/latest/dex/pairs/{chain}/{pool_address}"
        try:
            r = self._get(url)
            if r.status_code != 200:
                return {
                    "provider": self.provider_id,
                    "chain": chain,
                    "pool_address": pool_address,
                    "liquidity_usd": None,
                    "volume_24h_usd": None,
                    "passed": False,
                    "note": f"HTTP {r.status_code}",
                }
            data = r.json()
            pairs = data.get("pairs") or []
            if not pairs:
                return {
                    "provider": self.provider_id,
                    "chain": chain,
                    "pool_address": pool_address,
                    "liquidity_usd": None,
                    "volume_24h_usd": None,
                    "passed": False,
                    "note": "no pairs",
                }
            pair = pairs[0]
            liquidity = float(pair.get("liquidity", {}).get("usd") or 0.0)
            volume_24h = float(pair.get("volume", {}).get("h24") or 0.0)
            passed = liquidity >= min_liquidity_usd and volume_24h >= min_volume_24h_usd
            return {
                "provider": self.provider_id,
                "chain": chain,
                "pool_address": pool_address,
                "liquidity_usd": liquidity,
                "volume_24h_usd": volume_24h,
                "passed": passed,
                "note": "DexScreener screen",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "provider": self.provider_id,
                "chain": chain,
                "pool_address": pool_address,
                "liquidity_usd": None,
                "volume_24h_usd": None,
                "passed": False,
                "note": str(exc),
            }


class DefiLlamaProvider(DexOHLCVProvider):
    """Tertiary provider: liquidity/volume context only. Does not produce OHLCV."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        rate_limiter: TokenBucketRateLimiter | None = None,
    ) -> None:
        self._client: httpx.Client | None = client
        self._rate_limiter: TokenBucketRateLimiter = rate_limiter or TokenBucketRateLimiter(
            tokens_per_second=DEFAULT_TERTIARY_RATE,
        )

    @property
    def provider_id(self) -> str:
        return "defillama"

    @property
    def role(self) -> str:
        return "tertiary"

    @property
    def produces_ohlcv(self) -> bool:
        return False

    def _get(self, url: str) -> httpx.Response:
        if self._client:
            return self._client.get(url)
        with httpx.Client(timeout=30.0) as c:
            return c.get(url)

    def fetch_pool_ohlcv(
        self,
        *,
        chain: str,
        pool_address: str,
        fee_tier: str | None = None,
        start_time: datetime,
        end_time: datetime,
    ) -> ProviderResult:
        # DefiLlama does not provide native OHLCV; return empty for gap-fill.
        return ProviderResult(
            provider=self.provider_id,
            chain=chain,
            pool_address=pool_address,
            records=[],
        )

    def screen_pool(
        self,
        *,
        chain: str,
        pool_address: str,
        min_liquidity_usd: float,
        min_volume_24h_usd: float,
        base_token_address: str | None = None,
        quote_token_address: str | None = None,
    ) -> dict[str, Any]:
        """Validate token prices via DefiLlama Coins as tertiary context.

        When token addresses are available, the coins endpoint is a real,
        pool-agnostic request that exercises the DefiLlama tier without
        fetching OHLCV.
        """
        if not base_token_address or not quote_token_address:
            return {
                "provider": self.provider_id,
                "chain": chain,
                "pool_address": pool_address,
                "liquidity_usd": None,
                "volume_24h_usd": None,
                "passed": True,
                "note": "tertiary provider defers screening (no token addresses)",
            }

        coins = [f"{chain}:{base_token_address}", f"{chain}:{quote_token_address}"]
        url = f"https://coins.llama.fi/prices/current/{','.join(coins)}"
        self._rate_limiter.acquire(provider=self.provider_id, chain=chain, pool_address=pool_address)
        try:
            r = self._get(url)
            if r.status_code != 200:
                return {
                    "provider": self.provider_id,
                    "chain": chain,
                    "pool_address": pool_address,
                    "liquidity_usd": None,
                    "volume_24h_usd": None,
                    "passed": False,
                    "note": f"HTTP {r.status_code}",
                }
            data = r.json()
            prices = data.get("coins") or {}
            matched = [c for c in coins if c in prices and float(prices[c].get("price") or 0.0) > 0.0]
            # Context only (DEX-002 rework): token prices are not liquidity/volume
            # evidence and can never make a pool pass.
            passed = False
            return {
                "provider": self.provider_id,
                "chain": chain,
                "pool_address": pool_address,
                "liquidity_usd": None,
                "volume_24h_usd": None,
                "passed": passed,
                "note": f"DefiLlama coins matched {len(matched)}/{len(coins)} tokens",
                "matched_coins": matched,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "provider": self.provider_id,
                "chain": chain,
                "pool_address": pool_address,
                "liquidity_usd": None,
                "volume_24h_usd": None,
                "passed": False,
                "note": str(exc),
            }


# ---------------------------------------------------------------------------
# Screening gate
# ---------------------------------------------------------------------------


@dataclass
class ScreeningGate:
    min_liquidity_usd: float = 10_000.0
    min_volume_24h_usd: float = 1_000.0
    death_consecutive_days: int = 7

    def screen(
        self,
        *,
        chain: str,
        pool_address: str,
        providers: Sequence[DexOHLCVProvider],
        base_token_address: str | None = None,
        quote_token_address: str | None = None,
    ) -> dict[str, Any]:
        """Screen a pool against all providers and return a single verdict.

        Every provider is called so that the tertiary provider (DefiLlama)
        contributes real context even when the primary provider already passes.
        """
        results = []
        passed = False
        first_passed_provider: str | None = None
        first_passed_liquidity: float | None = None
        first_passed_volume: float | None = None
        for provider in providers:
            res = provider.screen_pool(
                chain=chain,
                pool_address=pool_address,
                min_liquidity_usd=self.min_liquidity_usd,
                min_volume_24h_usd=self.min_volume_24h_usd,
                base_token_address=base_token_address,
                quote_token_address=quote_token_address,
            )
            results.append(res)
            if res.get("passed") and not passed:
                passed = True
                first_passed_provider = provider.provider_id
                first_passed_liquidity = res.get("liquidity_usd")
                first_passed_volume = res.get("volume_24h_usd")
        return {
            "chain": chain,
            "pool_address": pool_address,
            "passed": passed,
            "provider": first_passed_provider,
            "liquidity_usd": first_passed_liquidity,
            "volume_24h_usd": first_passed_volume,
            "screen_results": results,
        }


# ---------------------------------------------------------------------------
# Watermark store
# ---------------------------------------------------------------------------


class ShardedWatermarkStore:
    """Per-(provider, chain, pool) watermarks stored as JSON."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def load(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise DexFanOutError(f"Failed to load watermarks from {self._path}") from exc
        return dict(data.get("dex_fanout", {}))

    def save(self, watermarks: Mapping[str, str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {}
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
        data["dex_fanout"] = dict(watermarks)
        self._path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _watermark_key(provider: str, chain: str, pool_address: str) -> str:
    return f"{provider}:{chain}:{pool_address.lower()}"


def load_watermark(watermarks: Mapping[str, str], provider: str, chain: str, pool_address: str) -> datetime:
    key = _watermark_key(provider, chain, pool_address)
    if key in watermarks:
        end = datetime.fromisoformat(watermarks[key])
        return (end + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return datetime(2020, 1, 1, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Merge / dedupe policy
# ---------------------------------------------------------------------------


PRIORITY: Final[dict[str, int]] = {
    "geckoterminal": 1,
    "dexscreener": 2,
    "defillama": 3,
}


def merge_records(results: Sequence[ProviderResult]) -> list[PoolOhlcvRecord]:
    """Merge records by timestamp, preferring lower-priority provider.

    Provenance is preserved on every row (record.provider). Secondary/tertiary
    records are only used when primary has no record for that timestamp.
    """
    by_key: dict[tuple[str, int], PoolOhlcvRecord] = {}
    for result in sorted(results, key=lambda r: PRIORITY.get(r.provider, 99)):
        for rec in result.records:
            key = (rec.pool_address.lower(), int(rec.timestamp.timestamp()))
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = rec
            # Lower priority number wins; do not overwrite.
    return [by_key[k] for k in sorted(by_key.keys())]


# ---------------------------------------------------------------------------
# Fan-out engine
# ---------------------------------------------------------------------------


@dataclass
class WorkItem:
    provider: str
    chain: str
    pool_address: str
    fee_tier: str | None
    start_time: datetime
    end_time: datetime
    gecko_network: str | None = None


@dataclass
class PoolBackfillResult:
    chain: str
    pool_address: str
    fee_tier: str | None
    records: list[PoolOhlcvRecord]
    providers_used: list[str]
    incidents: list[RateLimitIncident]
    last_timestamp: datetime | None
    gecko_network: str | None = None


class DEXFanOutEngine:
    """Run multi-provider DEX OHLCV backfill with screening and watermarks."""

    def __init__(
        self,
        *,
        providers: Mapping[str, DexOHLCVProvider],
        screening_gate: ScreeningGate,
        watermark_store: ShardedWatermarkStore,
        watermarks: Mapping[str, str] | None = None,
    ) -> None:
        self._providers: dict[str, DexOHLCVProvider] = dict(providers)
        self._screening_gate = screening_gate
        self._watermark_store = watermark_store
        self._watermarks: dict[str, str] = dict(watermarks) if watermarks else watermark_store.load()
        self._screen_results: list[dict[str, Any]] = []
        self._dead_pools: list[dict[str, Any]] = []
        self._last_work_items: list[WorkItem] = []

    def screen_and_enqueue(
        self,
        candidate_pools: Sequence[dict[str, Any]],
        *,
        end_time: datetime,
        max_pools_per_run: int | None = None,
    ) -> list[WorkItem]:
        """Screen candidate pools and produce work items for active ones.

        Candidate pools are assumed to be supplied in priority order. When
        ``max_pools_per_run`` is set, only the top N active pools (those that
        still have work to do) are scheduled; the rest are left for the next run
        via the watermark store.
        """
        work: list[WorkItem] = []
        active_pools: list[tuple[dict[str, Any], list[WorkItem]]] = []
        for pool in candidate_pools:
            chain = str(pool.get("chain") or "arbitrum").strip().lower()
            gecko_network = str(pool.get("gecko_network") or chain).strip().lower()
            # Preserve original casing for Solana addresses; they are case-sensitive.
            address = str(pool.get("address") or "").strip()
            fee_tier = str(pool.get("fee_tier") or "").strip() or None
            if not address:
                continue

            screen = self._screening_gate.screen(
                chain=chain,
                pool_address=address,
                providers=list(self._providers.values()),
                base_token_address=pool.get("base_token_address"),
                quote_token_address=pool.get("quote_token_address"),
            )
            self._screen_results.append(screen)

            if not screen["passed"]:
                self._dead_pools.append({
                    "chain": chain,
                    "pool_address": address,
                    "reason": "screen_failed",
                    "screen": screen,
                })
                continue

            # Only providers that actually produce OHLCV time-series are
            # scheduled. Tertiary providers contribute during screening.
            provider_order = sorted(
                self._providers.values(),
                key=lambda p: PRIORITY.get(p.provider_id, 99),
            )
            pending_items: list[WorkItem] = []
            for provider in provider_order:
                if not provider.produces_ohlcv:
                    continue
                start = load_watermark(self._watermarks, provider.provider_id, chain, address)
                if start >= end_time:
                    continue
                pending_items.append(
                    WorkItem(
                        provider=provider.provider_id,
                        chain=chain,
                        pool_address=address,
                        fee_tier=fee_tier,
                        start_time=start,
                        end_time=end_time,
                        gecko_network=gecko_network,
                    )
                )
            # A pool is considered active for this run if it has at least one
            # OHLCV provider with work remaining.
            if pending_items:
                active_pools.append((pool, pending_items))

        if max_pools_per_run is not None:
            active_pools = active_pools[:max_pools_per_run]

        for _pool, pending_items in active_pools:
            work.extend(pending_items)
        return work

    def run_work_items(self, work_items: Sequence[WorkItem]) -> list[PoolBackfillResult]:
        """Fetch OHLCV for all work items and merge per pool."""
        self._last_work_items = list(work_items)
        by_pool: dict[tuple[str, str], list[ProviderResult]] = {}
        gecko_network_by_key: dict[tuple[str, str], str] = {}
        for item in work_items:
            provider = self._providers.get(item.provider)
            if provider is None:
                continue
            key = (item.chain, item.pool_address)
            gecko_network_by_key[key] = item.gecko_network or item.chain
            result = provider.fetch_pool_ohlcv(
                chain=item.gecko_network or item.chain,
                pool_address=item.pool_address,
                fee_tier=item.fee_tier,
                start_time=item.start_time,
                end_time=item.end_time,
            )
            by_pool.setdefault(key, []).append(result)

        pool_results: list[PoolBackfillResult] = []
        for (chain, pool_address), results in by_pool.items():
            merged = merge_records(results)
            providers_used = sorted({r.provider for r in results if r.records})
            incidents = [r.incident for r in results if r.incident is not None]
            last_ts = max((r.timestamp for r in merged), default=None)
            pool_results.append(
                PoolBackfillResult(
                    chain=chain,
                    pool_address=pool_address,
                    fee_tier=None,
                    records=merged,
                    providers_used=providers_used,
                    incidents=incidents,
                    last_timestamp=last_ts,
                    gecko_network=gecko_network_by_key.get((chain, pool_address)),
                )
            )
        return pool_results

    def update_watermarks(self, pool_results: Sequence[PoolBackfillResult]) -> None:
        """Advance watermarks for every provider that was scheduled.

        Providers that returned records advance to the last timestamp. Providers
        that returned empty records (e.g., failures or no data) advance to the
        end_time of the work item so the next run does not waste rate-limit
        budget on them.
        """
        last_timestamp_by_key: dict[tuple[str, str, str], datetime] = {}
        for res in pool_results:
            if res.last_timestamp is not None:
                for provider_id in res.providers_used:
                    key = (provider_id, res.chain, res.pool_address)
                    last_timestamp_by_key[key] = res.last_timestamp

        for item in self._last_work_items:
            key = (item.provider, item.chain, item.pool_address)
            ts = last_timestamp_by_key.get(key)
            if ts is None:
                ts = item.end_time
            self._watermarks[_watermark_key(*key)] = ts.isoformat()

    def mark_dead_pools(
        self,
        pool_results: Sequence[PoolBackfillResult],
        *,
        threshold_days: int = 7,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        now = as_of or datetime.now(UTC)
        newly_dead: list[dict[str, Any]] = []
        for res in pool_results:
            if res.last_timestamp is None:
                continue
            if (now - res.last_timestamp).days > threshold_days:
                death_record = {
                    "chain": res.chain,
                    "pool_address": res.pool_address,
                    "last_timestamp": res.last_timestamp.isoformat(),
                    "days_inactive": (now - res.last_timestamp).days,
                    "reason": "pragmatic_dex_death",
                }
                self._dead_pools.append(death_record)
                newly_dead.append(death_record)
        return newly_dead

    def save_watermarks(self) -> None:
        self._watermark_store.save(self._watermarks)

    def get_screen_results(self) -> list[dict[str, Any]]:
        return list(self._screen_results)

    def get_dead_pools(self) -> list[dict[str, Any]]:
        return list(self._dead_pools)


# ---------------------------------------------------------------------------
# Table builder
# ---------------------------------------------------------------------------


def build_dex_fanout_table(records: Sequence[PoolOhlcvRecord]) -> dict[str, list[Any]]:
    """Return a column dict ready for PyArrow from merged records."""
    ordered = sorted(records, key=lambda r: (r.chain, r.pool_address, r.timestamp))
    return {
        "timestamp": [r.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") for r in ordered],
        "timestamp_us": [int(r.timestamp.timestamp() * 1_000_000) for r in ordered],
        "chain": [r.chain for r in ordered],
        "pool_address": [r.pool_address.lower() for r in ordered],
        "fee_tier": [r.fee_tier or "" for r in ordered],
        "open": [r.open for r in ordered],
        "high": [r.high for r in ordered],
        "low": [r.low for r in ordered],
        "close": [r.close for r in ordered],
        "volume": [r.volume for r in ordered],
        "provider": [r.provider for r in ordered],
        "liquidity": [r.liquidity for r in ordered],
        "volume_24h": [r.volume_24h for r in ordered],
    }


def read_api_key_from_env(key_name: str) -> str | None:
    return os.environ.get(key_name)
