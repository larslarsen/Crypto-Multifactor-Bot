"""UNIVERSE-004 — Birdeye listings → screen → OHLCV request queue + liquidity death.

Uses Birdeye new-listing events (free key) as the top-of-funnel. Applies
configurable screening (liquidity, volume, chain allowlist). Enqueues survivors
for DEX-002 OHLCV providers. Marks pools pragmatically dead when liquidity and
volume stay below configured thresholds for N consecutive days (from DEX-002
pool stats or any supplied pool statistics).

Hard constraints:
- Birdeye is used only for /defi/v2/tokens/new_listing (listing events).
- No Birdeye OHLCV or bar endpoints.
- All membership is as-of and non-survivorship-free.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from cryptofactors.universe.birdeye_listings import (
    BirdeyeListingsProvider,
    normalize_listing_event,
    parse_iso_datetime,
)

DEFAULT_MIN_LIQUIDITY_USD: float = 10_000.0
DEFAULT_MIN_VOLUME_24H_USD: float = 1_000.0
DEFAULT_DEATH_CONSECUTIVE_DAYS: int = 7
DEFAULT_CHAIN_ALLOWLIST: set[str] = {"solana", "arbitrum", "ethereum"}
# Birdeye free tier is conservative; public docs suggest ~5-10 req/min.
DEFAULT_BIRDEYE_RATE_PER_MIN: float = 6.0


class BirdeyeScreenQueueError(RuntimeError):
    """Base error for UNIVERSE-004 operations."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


# ---------------------------------------------------------------------------
# Generic token-bucket rate limiter (deliberately self-contained in universe layer)
# ---------------------------------------------------------------------------


@dataclass
class RateLimitIncident:
    timestamp: str
    provider: str
    chain: str
    note: str


class TokenBucketRateLimiter:
    """Simple token-bucket / min-interval rate limiter."""

    def __init__(self, *, tokens_per_second: float, burst: int = 1) -> None:
        if tokens_per_second <= 0:
            raise BirdeyeScreenQueueError("tokens_per_second must be positive")
        self._tokens_per_second = tokens_per_second
        self._burst = max(1, burst)
        self._tokens = float(self._burst)
        self._last_update = time.monotonic()
        self._incidents: list[RateLimitIncident] = []
        self._total_requests = 0

    def acquire(self, *, provider: str, chain: str) -> None:
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
                    "note": inc.note,
                }
                for inc in self._incidents
            ],
        }


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScreeningConfig:
    """Deterministic, versioned screening criteria."""

    min_liquidity_usd: float = DEFAULT_MIN_LIQUIDITY_USD
    min_volume_24h_usd: float = DEFAULT_MIN_VOLUME_24H_USD
    chain_allowlist: set[str] | None = None
    death_consecutive_days: int = DEFAULT_DEATH_CONSECUTIVE_DAYS
    as_of: datetime | None = None


@dataclass(frozen=True)
class PoolStats:
    """Daily-ish pool statistics used for pragmatic death detection."""

    timestamp: datetime
    chain: str
    pool_address: str
    liquidity: float
    volume_24h: float


@dataclass(frozen=True)
class OHLCVQueueItem:
    """Request for DEX-002 to backfill OHLCV for this pool."""

    chain: str
    address: str
    fee_tier: str | None
    reason: str
    enqueued_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "address": self.address,
            "fee_tier": self.fee_tier,
            "reason": self.reason,
            "enqueued_at": self.enqueued_at.isoformat(),
        }


@dataclass(frozen=True)
class UniverseMember:
    """As-of membership decision: listed and not dead."""

    chain: str
    address: str
    listed_at: datetime
    is_dead: bool
    death_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "address": self.address,
            "listed_at": self.listed_at.isoformat(),
            "is_dead": self.is_dead,
            "death_reason": self.death_reason,
            "member": not self.is_dead,
        }


# ---------------------------------------------------------------------------
# Screening / queue / death logic
# ---------------------------------------------------------------------------


class BirdeyeScreenQueue:
    """Fetch Birdeye listings, screen them, and build an OHLCV request queue."""

    def __init__(
        self,
        provider: BirdeyeListingsProvider,
        config: ScreeningConfig,
        *,
        rate_limiter: TokenBucketRateLimiter | None = None,
    ) -> None:
        self._provider = provider
        self._config = config
        self._rate_limiter = rate_limiter or TokenBucketRateLimiter(
            tokens_per_second=DEFAULT_BIRDEYE_RATE_PER_MIN / 60.0,
        )

    def fetch_and_screen(
        self,
        chain: str,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch raw listings, split into survivors and rejected.

        Returns (raw, survivors, rejected) in normalized form.
        """
        self._rate_limiter.acquire(provider="birdeye_listings", chain=chain)
        try:
            raw_items = self._provider.fetch_new_listings(chain=chain, limit=limit)
        except Exception as exc:  # noqa: BLE001
            self._rate_limiter.record_incident(
                RateLimitIncident(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="birdeye_listings",
                    chain=chain,
                    note=str(exc),
                )
            )
            return [], [], []

        normalized = [normalize_listing_event(item, chain=chain) for item in raw_items]
        survivors = []
        rejected = []
        for n in normalized:
            reason = self._screen_reason(n)
            if reason is None:
                survivors.append(n)
            else:
                n["_reject_reason"] = reason
                rejected.append(n)
        return normalized, survivors, rejected

    def _screen(self, record: Mapping[str, Any]) -> bool:
        """Apply deterministic screening criteria.

        Liquidity and chain are available from Birdeye new-listing events; the
        volume_24h threshold is not applied here because the listing endpoint does
        not return volume. The same threshold is used for pragmatic death once
        DEX-002 pool stats are available.
        """
        return self._screen_reason(record) is None

    def _screen_reason(self, record: Mapping[str, Any]) -> str | None:
        """Return the rejection reason, or None if the record passes."""
        cfg = self._config
        if cfg.chain_allowlist and record["chain"] not in cfg.chain_allowlist:
            return f"chain_not_allowed:{record['chain']}"
        if float(record.get("liquidity") or 0.0) < cfg.min_liquidity_usd:
            return "low_liquidity"
        return None

    def build_queue(self, survivors: Sequence[Mapping[str, Any]]) -> list[OHLCVQueueItem]:
        """Convert survivors to OHLCV request queue items."""
        as_of = self._config.as_of or datetime.now(timezone.utc)
        items: list[OHLCVQueueItem] = []
        for r in survivors:
            volume_note = "n/a" if r.get("volume_24h") is None else f"{float(r['volume_24h']):.2f}"
            reason = (
                f"screen_pass:liquidity={float(r.get('liquidity') or 0.0):.2f},"
                f"volume_24h={volume_note},"
                f"chain={r['chain']}"
            )
            items.append(
                OHLCVQueueItem(
                    chain=r["chain"],
                    address=r["address"],
                    fee_tier=None,
                    reason=reason,
                    enqueued_at=as_of,
                )
            )
        return items

    def apply_death_rule(
        self,
        listed: Sequence[Mapping[str, Any]],
        stats: Sequence[PoolStats],
    ) -> list[UniverseMember]:
        """Mark members dead when liquidity and volume are below thresholds for N days.

        If no pool stats are supplied for a listed address, the pool is assumed
        alive (death cannot be proven). This is intentional: death must come from
        DEX-002 derived activity, not from the listing event itself.
        """
        cfg = self._config
        as_of = cfg.as_of or datetime.now(timezone.utc)
        members: list[UniverseMember] = []
        for r in listed:
            chain = r["chain"]
            address = r["address"]
            listed_at = parse_iso_datetime(r.get("liquidity_added_at"))
            if listed_at is None:
                listed_at = as_of

            pool_stats = [
                s for s in stats if s.chain == chain and s.pool_address.lower() == address.lower()
            ]
            is_dead = _is_dead_by_liquidity(pool_stats, cfg, as_of)
            members.append(
                UniverseMember(
                    chain=chain,
                    address=address,
                    listed_at=listed_at,
                    is_dead=is_dead,
                    death_reason="liquidity_volume_death" if is_dead else None,
                )
            )
        return members

    def screen_all_chains(
        self,
        chains: Sequence[str],
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """Run fetch_and_screen across multiple chains and aggregate results."""
        all_raw: list[dict[str, Any]] = []
        all_survivors: list[dict[str, Any]] = []
        all_rejected: list[dict[str, Any]] = []
        for chain in chains:
            raw, survivors, rejected = self.fetch_and_screen(chain=chain, limit=limit)
            all_raw.extend(raw)
            all_survivors.extend(survivors)
            all_rejected.extend(rejected)
        return all_raw, all_survivors, all_rejected


def _is_dead_by_liquidity(
    stats: Sequence[PoolStats],
    config: ScreeningConfig,
    as_of: datetime,
) -> bool:
    """Return True if the pool failed liquidity+volume thresholds for N consecutive days."""
    if not stats:
        return False

    by_day: dict[datetime, list[PoolStats]] = {}
    for s in stats:
        day = s.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        by_day.setdefault(day, []).append(s)

    daily: list[tuple[datetime, float, float]] = []
    for day in sorted(by_day.keys()):
        liquidity = max((s.liquidity for s in by_day[day]), default=0.0)
        volume_24h = max((s.volume_24h for s in by_day[day]), default=0.0)
        daily.append((day, liquidity, volume_24h))

    end_day = as_of.replace(hour=0, minute=0, second=0, microsecond=0)
    window = [d for d in daily if d[0] <= end_day][-config.death_consecutive_days :]
    if len(window) < config.death_consecutive_days:
        return False
    return all(
        liquidity < config.min_liquidity_usd and volume_24h < config.min_volume_24h_usd
        for _, liquidity, volume_24h in window
    )


def read_api_key_from_env(key_name: str = "BIRDEYE_API_KEY") -> str | None:
    """Read a Birdeye API key from the environment without hard-coding it."""
    import os

    return os.environ.get(key_name)


def build_birdeye_screening_provider(
    *,
    api_key: str | None = None,
    client: httpx.Client | None = None,
    config: ScreeningConfig | None = None,
) -> BirdeyeScreenQueue:
    """Factory: build a BirdeyeScreenQueue from an API key or injected client."""
    key = api_key or read_api_key_from_env()
    provider = BirdeyeListingsProvider(api_key=key, client=client)
    return BirdeyeScreenQueue(provider=provider, config=config or ScreeningConfig())
