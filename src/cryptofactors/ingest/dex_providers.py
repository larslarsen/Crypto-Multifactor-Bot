"""DEX-002 provider capability contracts, screening, and raw acquisition lineage.

Provider capabilities are separated and enforced. A provider may supply interval
OHLCV bars, authoritative screening metrics, or context; those are independent and a
provider may never exceed what DATA-007 evidenced for it:

* GeckoTerminal  -- interval OHLCV only (the sole current OHLCV authority)
* DexScreener    -- authoritative screening metrics only (current price/24h stats)
* DefiLlama      -- context only; it can never make a pool pass

Screening is fail-closed. A pool passes only from an authoritative observation that
actually carries finite liquidity and 24h volume at or above both thresholds. Missing
metrics, provider errors, and context-only responses cannot pass; they are
``UNAVAILABLE`` and stay retryable rather than becoming a death observation.

Every controlling HTTP response is preserved byte-for-byte through ``RawObjectWriter``
before it is decoded, including error bodies. Transport failures that produce no body
still leave failed-acquisition evidence, so a gap in coverage is always explainable.
"""

from __future__ import annotations

import hashlib
import json
import math
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import httpx

from cryptofactors.ingest.raw.models import AcquisitionMetadata
from cryptofactors.ingest.raw.writer import RawObjectWriter

GECKOTERMINAL_PROVIDER = "geckoterminal"
DEXSCREENER_PROVIDER = "dexscreener"
DEFILLAMA_PROVIDER = "defillama"

DEFAULT_MIN_LIQUIDITY_USD = 50_000.0
DEFAULT_MIN_VOLUME_24H_USD = 10_000.0


class DexProviderError(RuntimeError):
    """Raised for malformed provider responses or capability violations."""


class ProviderCapability(str, Enum):
    """What a provider is actually evidenced to supply."""

    INTERVAL_OHLCV = "interval_ohlcv"
    AUTHORITATIVE_SCREENING = "authoritative_screening"
    CONTEXT = "context"


class ScreeningStatus(str, Enum):
    """Outcome of a screening observation or decision.

    ``UNAVAILABLE`` is deliberately distinct from ``REJECT``: a pool we could not
    observe is retryable and is not evidence of death, while a pool we did observe
    below threshold is a real rejection.
    """

    PASS = "PASS"
    REJECT = "REJECT"
    UNAVAILABLE = "UNAVAILABLE"
    CONTEXT_ONLY = "CONTEXT_ONLY"


def _finite(value: Any) -> float | None:
    """Return a finite float, or None for anything that cannot screen a pool."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def canonical_json(payload: Any) -> str:
    """Stable encoding so a recorded request compares byte-for-byte."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class ScreeningThresholds:
    """Configured screening thresholds, fingerprinted into published lineage."""

    min_liquidity_usd: float = DEFAULT_MIN_LIQUIDITY_USD
    min_volume_24h_usd: float = DEFAULT_MIN_VOLUME_24H_USD

    def __post_init__(self) -> None:
        for name in ("min_liquidity_usd", "min_volume_24h_usd"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise DexProviderError(f"{name} must be a finite, non-negative number")

    def as_dict(self) -> dict[str, float]:
        return {
            "min_liquidity_usd": float(self.min_liquidity_usd),
            "min_volume_24h_usd": float(self.min_volume_24h_usd),
        }

    def fingerprint(self) -> str:
        return hashlib.sha256(canonical_json(self.as_dict()).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ScreeningObservation:
    """One provider's screening evidence for one pool.

    Replaces the previous untyped dict: the metrics that drove the outcome are part
    of the record, so a decision can always be re-derived from its own evidence.
    """

    provider: str
    capability: ProviderCapability
    observed_at: datetime
    liquidity_usd: float | None
    volume_24h_usd: float | None
    status: ScreeningStatus
    reason: str
    raw_object_id: str | None = None
    acquisition_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "capability": self.capability.value,
            "observed_at": self.observed_at.isoformat(),
            "liquidity_usd": self.liquidity_usd,
            "volume_24h_usd": self.volume_24h_usd,
            "status": self.status.value,
            "reason": self.reason,
            "raw_object_id": self.raw_object_id,
            "acquisition_id": self.acquisition_id,
        }

    @property
    def is_authoritative(self) -> bool:
        return self.capability is ProviderCapability.AUTHORITATIVE_SCREENING


@dataclass(frozen=True, slots=True)
class ScreeningDecision:
    """The single verdict for a pool, plus every observation behind it."""

    chain: str
    pool_address: str
    status: ScreeningStatus
    reason: str
    thresholds: ScreeningThresholds
    authoritative: ScreeningObservation | None
    observations: tuple[ScreeningObservation, ...]

    @property
    def passed(self) -> bool:
        return self.status is ScreeningStatus.PASS

    @property
    def raw_object_ids(self) -> frozenset[str]:
        return frozenset(
            obs.raw_object_id for obs in self.observations if obs.raw_object_id is not None
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "pool_address": self.pool_address,
            "status": self.status.value,
            "reason": self.reason,
            "thresholds": self.thresholds.as_dict(),
            "liquidity_usd": None if self.authoritative is None else self.authoritative.liquidity_usd,
            "volume_24h_usd": (
                None if self.authoritative is None else self.authoritative.volume_24h_usd
            ),
            "authoritative_provider": None if self.authoritative is None else self.authoritative.provider,
            "observations": [obs.as_dict() for obs in self.observations],
        }


def decide_screening(
    *,
    chain: str,
    pool_address: str,
    observations: Sequence[ScreeningObservation],
    thresholds: ScreeningThresholds,
) -> ScreeningDecision:
    """Fail-closed screening decision.

    Only an authoritative observation can decide a pool. Context-only evidence is
    recorded for audit but is structurally incapable of passing anything, which is
    what stopped DefiLlama from admitting pools under the previous design.
    """
    ordered = tuple(observations)
    authoritative = [obs for obs in ordered if obs.is_authoritative]

    decided = next(
        (obs for obs in authoritative if obs.status in (ScreeningStatus.PASS, ScreeningStatus.REJECT)),
        None,
    )
    if decided is not None:
        return ScreeningDecision(
            chain=chain,
            pool_address=pool_address,
            status=decided.status,
            reason=decided.reason,
            thresholds=thresholds,
            authoritative=decided,
            observations=ordered,
        )

    if authoritative:
        unavailable = authoritative[0]
        return ScreeningDecision(
            chain=chain,
            pool_address=pool_address,
            status=ScreeningStatus.UNAVAILABLE,
            reason=unavailable.reason,
            thresholds=thresholds,
            authoritative=None,
            observations=ordered,
        )

    return ScreeningDecision(
        chain=chain,
        pool_address=pool_address,
        status=ScreeningStatus.UNAVAILABLE,
        reason="no authoritative screening observation",
        thresholds=thresholds,
        authoritative=None,
        observations=ordered,
    )


def evaluate_metrics(
    *,
    provider: str,
    observed_at: datetime,
    liquidity_usd: Any,
    volume_24h_usd: Any,
    thresholds: ScreeningThresholds,
    raw_object_id: str | None,
    acquisition_id: str | None,
) -> ScreeningObservation:
    """Turn raw authoritative metrics into a typed observation, fail-closed."""
    liquidity = _finite(liquidity_usd)
    volume = _finite(volume_24h_usd)

    if liquidity is None or volume is None:
        missing = [
            name
            for name, value in (("liquidity_usd", liquidity), ("volume_24h_usd", volume))
            if value is None
        ]
        return ScreeningObservation(
            provider=provider,
            capability=ProviderCapability.AUTHORITATIVE_SCREENING,
            observed_at=observed_at,
            liquidity_usd=liquidity,
            volume_24h_usd=volume,
            status=ScreeningStatus.UNAVAILABLE,
            reason=f"missing or non-finite {', '.join(missing)}",
            raw_object_id=raw_object_id,
            acquisition_id=acquisition_id,
        )

    passed = liquidity >= thresholds.min_liquidity_usd and volume >= thresholds.min_volume_24h_usd
    if passed:
        reason = (
            f"liquidity {liquidity:.2f} >= {thresholds.min_liquidity_usd:.2f} and "
            f"volume_24h {volume:.2f} >= {thresholds.min_volume_24h_usd:.2f}"
        )
    else:
        failed = []
        if liquidity < thresholds.min_liquidity_usd:
            failed.append(f"liquidity {liquidity:.2f} < {thresholds.min_liquidity_usd:.2f}")
        if volume < thresholds.min_volume_24h_usd:
            failed.append(f"volume_24h {volume:.2f} < {thresholds.min_volume_24h_usd:.2f}")
        reason = "; ".join(failed)

    return ScreeningObservation(
        provider=provider,
        capability=ProviderCapability.AUTHORITATIVE_SCREENING,
        observed_at=observed_at,
        liquidity_usd=liquidity,
        volume_24h_usd=volume,
        status=ScreeningStatus.PASS if passed else ScreeningStatus.REJECT,
        reason=reason,
        raw_object_id=raw_object_id,
        acquisition_id=acquisition_id,
    )


# ---------------------------------------------------------------------------
# Raw acquisition
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AcquisitionOutcome:
    """One HTTP attempt, whether or not it produced usable data.

    ``payload`` is None whenever the attempt failed; ``raw_object_id`` is None only
    when the transport produced no body at all.
    """

    provider: str
    request: dict[str, Any]
    acquired_at: datetime
    ok: bool
    payload: Any = None
    status_code: int | None = None
    raw_object_id: str | None = None
    acquisition_id: str | None = None
    failure_kind: str | None = None
    detail: str | None = None

    @property
    def request_json(self) -> str:
        return canonical_json(self.request)

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "request_json": self.request_json,
            "acquired_at": self.acquired_at.isoformat(),
            "ok": self.ok,
            "status_code": self.status_code,
            "raw_object_id": self.raw_object_id,
            "acquisition_id": self.acquisition_id,
            "failure_kind": self.failure_kind,
            "detail": self.detail,
        }


@dataclass
class AcquisitionLog:
    """Every attempt made during a run, successful or not."""

    outcomes: list[AcquisitionOutcome] = field(default_factory=list)

    def record(self, outcome: AcquisitionOutcome) -> AcquisitionOutcome:
        self.outcomes.append(outcome)
        return outcome

    @property
    def raw_object_ids(self) -> frozenset[str]:
        return frozenset(o.raw_object_id for o in self.outcomes if o.raw_object_id is not None)

    @property
    def failures(self) -> list[AcquisitionOutcome]:
        return [o for o in self.outcomes if not o.ok]

    def as_dicts(self) -> list[dict[str, Any]]:
        return [o.as_dict() for o in self.outcomes]


class RawHttpAcquirer:
    """Performs HTTP requests, preserving the exact response bytes before decoding."""

    def __init__(
        self,
        *,
        raw_writer: RawObjectWriter,
        client: httpx.Client,
        log: AcquisitionLog | None = None,
    ) -> None:
        self._raw_writer = raw_writer
        self._client = client
        self.log = log if log is not None else AcquisitionLog()

    def get_json(
        self,
        *,
        provider: str,
        url: str,
        params: Mapping[str, Any] | None = None,
        source_id: str,
        original_name: str,
    ) -> AcquisitionOutcome:
        request = {"method": "GET", "url": url, "params": dict(params or {})}
        acquired_at = datetime.now(UTC)

        try:
            response = self._client.get(url, params=dict(params or {}))
        except httpx.HTTPError as exc:
            detail = f"transport failure: {exc}"
            # No bytes to preserve, but the attempt must still be evidence.
            self._raw_writer.record_failed_acquisition(
                AcquisitionMetadata(source_id=source_id, request=request, acquired_at=acquired_at),
                detail,
            )
            return self.log.record(AcquisitionOutcome(
                provider=provider, request=request, acquired_at=acquired_at, ok=False,
                failure_kind="transport", detail=detail,
            ))

        body = response.content
        acquired_at = datetime.now(UTC)
        raw = self._raw_writer.write_stream(
            [body],
            AcquisitionMetadata(
                source_id=source_id,
                request=request,
                response_metadata={"status_code": response.status_code, "provider": provider},
                original_name=original_name,
                acquired_at=acquired_at,
            ),
        )
        common = {
            "provider": provider,
            "request": request,
            "acquired_at": acquired_at,
            "status_code": response.status_code,
            "raw_object_id": raw.raw_object_id,
            "acquisition_id": raw.acquisition_id,
        }

        if response.is_error:
            return self.log.record(AcquisitionOutcome(
                ok=False, failure_kind="http_status",
                detail=f"HTTP {response.status_code}", **common,
            ))
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            return self.log.record(AcquisitionOutcome(
                ok=False, failure_kind="invalid_json",
                detail=f"invalid JSON body: {exc}", **common,
            ))
        return self.log.record(AcquisitionOutcome(ok=True, payload=payload, **common))


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class ScreeningProvider(ABC):
    """A provider that contributes screening evidence.

    The default path is fail-closed and context-only: a subclass must explicitly
    declare authoritative capability to be able to decide anything.
    """

    provider_id: str = "unknown"
    capability: ProviderCapability = ProviderCapability.CONTEXT

    @abstractmethod
    def observe(
        self,
        *,
        chain: str,
        pool_address: str,
        thresholds: ScreeningThresholds,
        acquirer: RawHttpAcquirer,
    ) -> ScreeningObservation:
        """Return this provider's screening evidence for one pool."""

    def _context_only(
        self, *, reason: str, outcome: AcquisitionOutcome | None = None
    ) -> ScreeningObservation:
        return ScreeningObservation(
            provider=self.provider_id,
            capability=ProviderCapability.CONTEXT,
            observed_at=datetime.now(UTC) if outcome is None else outcome.acquired_at,
            liquidity_usd=None,
            volume_24h_usd=None,
            status=ScreeningStatus.CONTEXT_ONLY,
            reason=reason,
            raw_object_id=None if outcome is None else outcome.raw_object_id,
            acquisition_id=None if outcome is None else outcome.acquisition_id,
        )


class DexScreenerScreeningProvider(ScreeningProvider):
    """Authoritative screening metrics. Structurally cannot emit OHLCV."""

    provider_id = DEXSCREENER_PROVIDER
    capability = ProviderCapability.AUTHORITATIVE_SCREENING

    BASE_URL = "https://api.dexscreener.com/latest/dex/pairs"
    SOURCE_ID = "dexscreener_pairs"

    def observe(
        self,
        *,
        chain: str,
        pool_address: str,
        thresholds: ScreeningThresholds,
        acquirer: RawHttpAcquirer,
    ) -> ScreeningObservation:
        outcome = acquirer.get_json(
            provider=self.provider_id,
            url=f"{self.BASE_URL}/{chain}/{pool_address}",
            source_id=self.SOURCE_ID,
            original_name=f"dexscreener_{chain}_{pool_address}.json",
        )
        if not outcome.ok:
            return self._unavailable(outcome, outcome.detail or "acquisition failed")

        payload = outcome.payload
        if not isinstance(payload, Mapping):
            return self._unavailable(outcome, "response is not a JSON object")
        pairs = payload.get("pairs")
        if not isinstance(pairs, list) or not pairs:
            return self._unavailable(outcome, "no pairs in screening response")
        pair = pairs[0]
        if not isinstance(pair, Mapping):
            return self._unavailable(outcome, "pair entry is not an object")

        liquidity = pair.get("liquidity")
        volume = pair.get("volume")
        return evaluate_metrics(
            provider=self.provider_id,
            observed_at=outcome.acquired_at,
            liquidity_usd=liquidity.get("usd") if isinstance(liquidity, Mapping) else None,
            volume_24h_usd=volume.get("h24") if isinstance(volume, Mapping) else None,
            thresholds=thresholds,
            raw_object_id=outcome.raw_object_id,
            acquisition_id=outcome.acquisition_id,
        )

    def _unavailable(self, outcome: AcquisitionOutcome, reason: str) -> ScreeningObservation:
        return ScreeningObservation(
            provider=self.provider_id,
            capability=ProviderCapability.AUTHORITATIVE_SCREENING,
            observed_at=outcome.acquired_at,
            liquidity_usd=None,
            volume_24h_usd=None,
            status=ScreeningStatus.UNAVAILABLE,
            reason=reason,
            raw_object_id=outcome.raw_object_id,
            acquisition_id=outcome.acquisition_id,
        )


class DefiLlamaContextProvider(ScreeningProvider):
    """Context only. Called for auditable context; can never make a pool pass."""

    provider_id = DEFILLAMA_PROVIDER
    capability = ProviderCapability.CONTEXT

    BASE_URL = "https://coins.llama.fi/prices/current"
    SOURCE_ID = "defillama_coins"

    def observe(
        self,
        *,
        chain: str,
        pool_address: str,
        thresholds: ScreeningThresholds,
        acquirer: RawHttpAcquirer,
    ) -> ScreeningObservation:
        outcome = acquirer.get_json(
            provider=self.provider_id,
            url=f"{self.BASE_URL}/{chain}:{pool_address}",
            source_id=self.SOURCE_ID,
            original_name=f"defillama_{chain}_{pool_address}.json",
        )
        if not outcome.ok:
            return self._context_only(
                reason=outcome.detail or "acquisition failed", outcome=outcome
            )
        coins = outcome.payload.get("coins") if isinstance(outcome.payload, Mapping) else None
        count = len(coins) if isinstance(coins, Mapping) else 0
        return self._context_only(reason=f"context only; {count} coin price(s)", outcome=outcome)
