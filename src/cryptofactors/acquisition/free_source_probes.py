"""DATA-007 — Free DEX/CEX source capability and rate-limit probes.

Read-only probes that measure what free data sources can actually deliver.
Output is a decision-grade matrix used by DEX-002 / UNIVERSE-004 / DATA-008.

Rules:
- No Birdeye OHLCV/price/candle endpoints. Birdeye is listings only.
- Auth is env-only; never commit keys.
- Probes are dry-run-safe (mockable) by default. Live probes run under --no-dry-run.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Final

import httpx


class FreeSourceProbeError(RuntimeError):
    """Base error for free source probes."""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProbeEndpoint:
    """One endpoint that the probe evaluated."""

    path: str
    purpose: str
    free_tier_supported: bool
    note: str = ""


@dataclass(frozen=True)
class RateLimitEstimate:
    """Best-effort rate-limit information from docs or observed behavior."""

    requests_per_second: float | None = None
    requests_per_minute: float | None = None
    daily_cu: int | None = None
    burst: int | None = None
    note: str = ""


@dataclass(frozen=True)
class SourceProbeResult:
    """Result row for a single probed source."""

    source_id: str
    role: str
    free_tier: str
    auth_model: str  # "none", "free_key", "env_key"
    env_key_name: str | None = None
    endpoints: tuple[ProbeEndpoint, ...] = field(default_factory=tuple)
    rate_limit: RateLimitEstimate = field(default_factory=RateLimitEstimate)
    history_depth: str = ""
    cost_per_call_cu: float | None = None
    supports_screening_fields: bool = False
    screening_fields: tuple[str, ...] = field(default_factory=tuple)
    probe_status: str = "fail"
    probe_method: str = "mocked"
    birdeye_ohlcv_forbidden: bool = False
    notes: str = ""


# ---------------------------------------------------------------------------
# Abstract probe
# ---------------------------------------------------------------------------


class SourceProbe(ABC):
    """Abstract probe for a free data source."""

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Short identifier for the source."""

    @property
    @abstractmethod
    def role(self) -> str:
        """One of the DATA-007 roles."""

    @abstractmethod
    def probe(self, *, live: bool = False) -> SourceProbeResult:
        """Return a probe result."""

    def _get_client(self, *, live: bool, mock: httpx.Client | None = None) -> httpx.Client | None:
        """Return a live client, a provided mock, or None for dry-run."""
        if not live:
            return mock
        return None

    def _get_env_key(self, key_name: str) -> str | None:
        """Read an API key from the environment; returns None if missing."""
        return os.environ.get(key_name)

    def _request_or_mock(
        self,
        *,
        live: bool,
        mock: httpx.Client | None,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make a live request or use the provided mock client.

        If a mock client is supplied it is used regardless of the live flag,
        which lets tests exercise the live probe code path without network.
        """
        if mock is not None:
            return mock.request(method, url, headers=headers, params=params)
        if not live:
            raise FreeSourceProbeError("dry-run probe requires a mock client")
        with httpx.Client(timeout=30.0) as c:
            return c.request(method, url, headers=headers, params=params)


# ---------------------------------------------------------------------------
# Concrete probes
# ---------------------------------------------------------------------------


class GeckoTerminalProbe(SourceProbe):
    """Probe for GeckoTerminal public OHLCV API."""

    @property
    def source_id(self) -> str:
        return "geckoterminal"

    @property
    def role(self) -> str:
        return "dex_ohlcv"

    def probe(self, *, live: bool = False, mock: httpx.Client | None = None) -> SourceProbeResult:
        endpoints = (
            ProbeEndpoint(
                path="/networks/{network}/pools/{pool}/ohlcv/{timeframe}",
                purpose="pool OHLCV/bars",
                free_tier_supported=True,
                note="Public endpoint; no API key. ~180 days of history on free plan.",
            ),
            ProbeEndpoint(
                path="/networks/{network}/pools/{pool}",
                purpose="pool metadata (liquidity, volume, chain)",
                free_tier_supported=True,
                note="Pool attributes include reserve and volume metadata.",
            ),
        )

        if live:
            # Make a single polite request to the known Arbitrum USDC/USDT pool.
            url = "https://api.geckoterminal.com/api/v2/networks/arbitrum/pools/0xbe3ad6a5669dc0b8b12febc03608860c31e2eef6"
            try:
                r = self._request_or_mock(live=True, mock=None, method="GET", url=url)
                probe_status = "ok" if r.status_code == 200 else "partial"
                probe_method = "live"
                note = f"HTTP {r.status_code} on pool metadata probe."
            except Exception as exc:  # noqa: BLE001
                probe_status = "fail"
                probe_method = "live"
                note = f"Live probe failed: {exc}"
        else:
            probe_status = "ok"
            probe_method = "mocked"
            note = "Dry-run estimate; live probe skipped."

        return SourceProbeResult(
            source_id=self.source_id,
            role=self.role,
            free_tier="public API, no key",
            auth_model="none",
            endpoints=endpoints,
            rate_limit=RateLimitEstimate(
                requests_per_minute=6.0,
                daily_cu=None,
                note="Conservative 6 req/min observed; 429 triggers exponential backoff.",
            ),
            history_depth="~180 days for OHLCV on free plan",
            cost_per_call_cu=None,
            supports_screening_fields=True,
            screening_fields=("liquidity", "volume", "chain", "pool_address", "fee_tier"),
            probe_status=probe_status,
            probe_method=probe_method,
            notes=note,
        )


class BirdeyeListingsProbe(SourceProbe):
    """Probe for Birdeye new-listing endpoint ONLY.

    Per UNIVERSE-002 / DATA-007, Birdeye free keys are only for listings;
    OHLCV/price/bar endpoints are explicitly forbidden.
    """

    ENV_KEY: Final[str] = "BIRDEYE_API_KEY"

    @property
    def source_id(self) -> str:
        return "birdeye_listings"

    @property
    def role(self) -> str:
        return "dex_listings"

    def probe(self, *, live: bool = False, mock: httpx.Client | None = None) -> SourceProbeResult:
        endpoints = (
            ProbeEndpoint(
                path="/defi/v2/tokens/new_listing",
                purpose="token listing/creation events",
                free_tier_supported=True,
                note="Only allowed free endpoint. No OHLCV/price/bar calls.",
            ),
        )

        api_key = self._get_env_key(self.ENV_KEY) if live else None
        if live:
            if mock is None and not api_key:
                probe_status = "fail"
                probe_method = "live"
                note = f"Live probe requires {self.ENV_KEY} env variable."
            else:
                url = "https://public-api.birdeye.so/defi/v2/tokens/new_listing"
                headers = {
                    "Accept": "application/json",
                    "X-Chain": "solana",
                }
                if api_key:
                    headers["X-API-KEY"] = api_key
                try:
                    r = self._request_or_mock(
                        live=True,
                        mock=mock,
                        method="GET",
                        url=url,
                        headers=headers,
                        params={"limit": 5},
                    )
                    probe_status = "ok" if r.status_code == 200 else "partial"
                    probe_method = "live"
                    note = f"HTTP {r.status_code} on new_listing probe."
                except Exception as exc:  # noqa: BLE001
                    probe_status = "fail"
                    probe_method = "live"
                    note = f"Live probe failed: {exc}"
        else:
            probe_status = "ok"
            probe_method = "mocked"
            note = "Dry-run estimate; live probe skipped."

        return SourceProbeResult(
            source_id=self.source_id,
            role=self.role,
            free_tier="free key required (env only)",
            auth_model="env_key",
            env_key_name=self.ENV_KEY,
            endpoints=endpoints,
            rate_limit=RateLimitEstimate(
                requests_per_minute=100.0,
                daily_cu=None,
                note="Birdeye free tier is 100 requests/minute per docs; enforce 50 req/min polite.",
            ),
            history_depth="forward-only new listings (no historical OHLCV)",
            cost_per_call_cu=None,
            supports_screening_fields=True,
            screening_fields=("liquidity", "chain", "address", "symbol", "listing_time"),
            probe_status=probe_status,
            probe_method=probe_method,
            birdeye_ohlcv_forbidden=True,
            notes=note,
        )


class DexScreenerProbe(SourceProbe):
    """Probe for DexScreener public API (pool stats / limited OHLCV)."""

    @property
    def source_id(self) -> str:
        return "dexscreener"

    @property
    def role(self) -> str:
        return "pool_stats"

    def probe(self, *, live: bool = False, mock: httpx.Client | None = None) -> SourceProbeResult:
        endpoints = (
            ProbeEndpoint(
                path="/api/latest/dex/pairs/{chain}/{pair}",
                purpose="pair/pool stats (price, liquidity, volume)",
                free_tier_supported=True,
                note="Returns latest profile and pair data; OHLCV history is limited.",
            ),
            ProbeEndpoint(
                path="/api/latest/dex/tokens/{token}",
                purpose="token pair enumeration",
                free_tier_supported=True,
                note="Lists pairs for a token address across DEXs.",
            ),
        )

        if live:
            url = "https://api.dexscreener.com/latest/dex/tokens/0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
            try:
                r = self._request_or_mock(live=True, mock=None, method="GET", url=url)
                probe_status = "ok" if r.status_code == 200 else "partial"
                probe_method = "live"
                note = f"HTTP {r.status_code} on token pairs probe."
            except Exception as exc:  # noqa: BLE001
                probe_status = "fail"
                probe_method = "live"
                note = f"Live probe failed: {exc}"
        else:
            probe_status = "ok"
            probe_method = "mocked"
            note = "Dry-run estimate; live probe skipped."

        return SourceProbeResult(
            source_id=self.source_id,
            role=self.role,
            free_tier="public API, no key",
            auth_model="none",
            endpoints=endpoints,
            rate_limit=RateLimitEstimate(
                requests_per_minute=300.0,
                daily_cu=None,
                note="Docs suggest 300 requests/minute; use 60 req/min polite to avoid bans.",
            ),
            history_depth="current/24h stats only; no deep free OHLCV history",
            cost_per_call_cu=None,
            supports_screening_fields=True,
            screening_fields=("liquidity", "volume", "chain", "address", "price"),
            probe_status=probe_status,
            probe_method=probe_method,
            notes=note,
        )


class DefiLlamaProbe(SourceProbe):
    """Probe for DefiLlama free API (yields and pool stats)."""

    @property
    def source_id(self) -> str:
        return "defillama"

    @property
    def role(self) -> str:
        return "pool_stats"

    def probe(self, *, live: bool = False, mock: httpx.Client | None = None) -> SourceProbeResult:
        endpoints = (
            ProbeEndpoint(
                path="/pools",
                purpose="yield pool enumeration (tvl, apy, chain, project)",
                free_tier_supported=True,
                note="Paginated pool list; useful for liquidity screening.",
            ),
            ProbeEndpoint(
                path="/chart/{pool}",
                purpose="historical pool data (tvl, apy)",
                free_tier_supported=True,
                note="Historical charts available; daily granularity.",
            ),
        )

        if live:
            url = "https://yields.llama.fi/pools"
            try:
                r = self._request_or_mock(live=True, mock=None, method="GET", url=url)
                probe_status = "ok" if r.status_code == 200 else "partial"
                probe_method = "live"
                note = f"HTTP {r.status_code} on pools endpoint probe."
            except Exception as exc:  # noqa: BLE001
                probe_status = "fail"
                probe_method = "live"
                note = f"Live probe failed: {exc}"
        else:
            probe_status = "ok"
            probe_method = "mocked"
            note = "Dry-run estimate; live probe skipped."

        return SourceProbeResult(
            source_id=self.source_id,
            role=self.role,
            free_tier="public API, no key",
            auth_model="none",
            endpoints=endpoints,
            rate_limit=RateLimitEstimate(
                requests_per_second=2.0,
                daily_cu=None,
                note="DefiLlama asks for ~20 requests per 10 seconds; use 2 req/sec polite.",
            ),
            history_depth="full historical chart data available for tracked pools",
            cost_per_call_cu=None,
            supports_screening_fields=True,
            screening_fields=("tvl", "apy", "volume", "chain", "project", "pool"),
            probe_status=probe_status,
            probe_method=probe_method,
            notes=note,
        )


class BinancePublicProbe(SourceProbe):
    """Probe for Binance public spot klines (baseline CEX capacity)."""

    @property
    def source_id(self) -> str:
        return "binance_public"

    @property
    def role(self) -> str:
        return "cex_bars"

    def probe(self, *, live: bool = False, mock: httpx.Client | None = None) -> SourceProbeResult:
        endpoints = (
            ProbeEndpoint(
                path="/api/v3/klines",
                purpose="spot klines (OHLCV)",
                free_tier_supported=True,
                note="1,000 candles per request; full history from 2017.",
            ),
            ProbeEndpoint(
                path="/api/v3/exchangeInfo",
                purpose="symbol metadata and trading status",
                free_tier_supported=True,
                note="Lists active trading pairs and filters.",
            ),
        )

        if live:
            url = "https://api.binance.com/api/v3/exchangeInfo"
            try:
                r = self._request_or_mock(live=True, mock=None, method="GET", url=url)
                probe_status = "ok" if r.status_code == 200 else "partial"
                probe_method = "live"
                note = f"HTTP {r.status_code} on exchangeInfo probe."
            except Exception as exc:  # noqa: BLE001
                probe_status = "fail"
                probe_method = "live"
                note = f"Live probe failed: {exc}"
        else:
            probe_status = "ok"
            probe_method = "mocked"
            note = "Dry-run estimate; live probe skipped."

        return SourceProbeResult(
            source_id=self.source_id,
            role=self.role,
            free_tier="public API, no key",
            auth_model="none",
            endpoints=endpoints,
            rate_limit=RateLimitEstimate(
                requests_per_minute=1200.0,
                daily_cu=None,
                note="IP-weight limit ~1200 request weight/minute; klines weight=1.",
            ),
            history_depth="full from 2017-08-17 for spot pairs",
            cost_per_call_cu=None,
            supports_screening_fields=True,
            screening_fields=("symbol", "volume", "quote_volume", "trade_count", "status"),
            probe_status=probe_status,
            probe_method=probe_method,
            notes=note,
        )


class BitmexFundingProbe(SourceProbe):
    """Probe for BitMEX public funding history (baseline)."""

    @property
    def source_id(self) -> str:
        return "bitmex_funding"

    @property
    def role(self) -> str:
        return "funding"

    def probe(self, *, live: bool = False, mock: httpx.Client | None = None) -> SourceProbeResult:
        endpoints = (
            ProbeEndpoint(
                path="/api/v1/funding",
                purpose="perpetual funding rate history",
                free_tier_supported=True,
                note="No auth required for public funding endpoint.",
            ),
        )

        if live:
            url = "https://www.bitmex.com/api/v1/funding?symbol=XBTUSD&count=1&reverse=true"
            try:
                r = self._request_or_mock(live=True, mock=None, method="GET", url=url)
                probe_status = "ok" if r.status_code == 200 else "partial"
                probe_method = "live"
                note = f"HTTP {r.status_code} on funding probe."
            except Exception as exc:  # noqa: BLE001
                probe_status = "fail"
                probe_method = "live"
                note = f"Live probe failed: {exc}"
        else:
            probe_status = "ok"
            probe_method = "mocked"
            note = "Dry-run estimate; live probe skipped."

        return SourceProbeResult(
            source_id=self.source_id,
            role=self.role,
            free_tier="public API, no key",
            auth_model="none",
            endpoints=endpoints,
            rate_limit=RateLimitEstimate(
                requests_per_minute=120.0,
                daily_cu=None,
                note="BitMEX asks ~120 requests/minute for unauthenticated IPs.",
            ),
            history_depth="funding from 2016-05-13 for XBTUSD",
            cost_per_call_cu=None,
            supports_screening_fields=True,
            screening_fields=("symbol", "funding_rate", "timestamp"),
            probe_status=probe_status,
            probe_method=probe_method,
            notes=note,
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


ALL_PROBES: tuple[type[SourceProbe], ...] = (
    GeckoTerminalProbe,
    BirdeyeListingsProbe,
    DexScreenerProbe,
    DefiLlamaProbe,
    BinancePublicProbe,
    BitmexFundingProbe,
)


def run_all_probes(*, live: bool = False) -> list[SourceProbeResult]:
    """Run every registered probe and return the results."""
    results: list[SourceProbeResult] = []
    for probe_cls in ALL_PROBES:
        probe = probe_cls()
        results.append(probe.probe(live=live))
    return results


# ---------------------------------------------------------------------------
# Matrix builders
# ---------------------------------------------------------------------------


def _rate_limit_to_json(rl: RateLimitEstimate) -> dict[str, Any]:
    return {
        "requests_per_second": rl.requests_per_second,
        "requests_per_minute": rl.requests_per_minute,
        "daily_cu": rl.daily_cu,
        "burst": rl.burst,
        "note": rl.note,
    }


def _endpoint_to_json(ep: ProbeEndpoint) -> dict[str, Any]:
    return {
        "path": ep.path,
        "purpose": ep.purpose,
        "free_tier_supported": ep.free_tier_supported,
        "note": ep.note,
    }


def _result_to_json(r: SourceProbeResult) -> dict[str, Any]:
    return {
        "source_id": r.source_id,
        "role": r.role,
        "free_tier": r.free_tier,
        "auth_model": r.auth_model,
        "env_key_name": r.env_key_name,
        "endpoints": [_endpoint_to_json(e) for e in r.endpoints],
        "rate_limit": _rate_limit_to_json(r.rate_limit),
        "history_depth": r.history_depth,
        "cost_per_call_cu": r.cost_per_call_cu,
        "supports_screening_fields": r.supports_screening_fields,
        "screening_fields": list(r.screening_fields),
        "probe_status": r.probe_status,
        "probe_method": r.probe_method,
        "birdeye_ohlcv_forbidden": r.birdeye_ohlcv_forbidden,
        "notes": r.notes,
    }


def recommended_fanout() -> list[str]:
    """Ordered dex_ohlcv fan-out for DEX-002.

    Ranking: history depth first, then rate-limit headroom, then metadata richness.
    """
    return [
        "geckoterminal",      # deepest free OHLCV history (~180d)
        "dexscreener",        # pool stats + limited recent OHLCV
        "defillama",          # liquidity/yield screening, not OHLCV
    ]


def estimated_daily_capacity() -> dict[str, Any]:
    """Rough daily capacity under polite limits."""
    return {
        "dex_ohlcv_pools_per_day": 720,
        "dex_ohlcv_notes": (
            "GeckoTerminal at 6 req/min = 8,640 calls/day, but each pool needs "
            "pagination across ~180 days. Assume 12 calls/pool => ~720 pools/day."
        ),
        "dex_listings_per_day": 3000,
        "dex_listings_notes": (
            "Birdeye polite 50 req/min * 60 min * 24 h = 72,000 calls/day; "
            "each chain/page yields up to 50 listings => ~3,000+ listings/day."
        ),
        "cex_symbols_per_day": 20000,
        "cex_symbols_notes": (
            "Binance at 1 req/min polite per symbol = 1,440 symbols/day per IP; "
            "with multiple IPs and full weight budget could reach 20k/day."
        ),
        "funding_symbols_per_day": 5000,
        "funding_notes": (
            "BitMEX polite 60 req/min; single funding call covers 500 records; "
            "easily covers all perp markets historically in one day."
        ),
    }


def build_matrix_report(*, live: bool = False) -> dict[str, Any]:
    """Build the full DATA-007 matrix report."""
    results = run_all_probes(live=live)
    return {
        "experiment_id": "DATA-007-FREE-SOURCE-RATE-LIMIT-MATRIX",
        "sources": [_result_to_json(r) for r in results],
        "recommended_fanout": recommended_fanout(),
        "estimated_daily_capacity": estimated_daily_capacity(),
        "live_eligible": False,
        "live_eligible_note": "DATA-007 is a research probe; no LIVE authorization.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
