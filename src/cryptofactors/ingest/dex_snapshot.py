"""DEX-002 screened DEX OHLCV acquisition and canonical snapshot publication.

Every published row comes from a genuine interval-bar response. Nothing here
synthesises a candle from a current-price snapshot, and no provider outside its
evidenced OHLCV capability can contribute a row.

Resume is retry-safe: a watermark advances only to the last contiguous validated row
that was actually published. Empty results, provider errors, unresolved gaps and
publication failures all leave the watermark where it was, so a pool that failed once
is retried rather than silently abandoned.

Publication is always a complete canonical snapshot. An incremental run merges the
prior canonical rows with newly acquired rows and republishes the union, so a delta
can never become the latest dataset.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptofactors.ingest.dex_providers import (
    GECKOTERMINAL_PROVIDER,
    AcquisitionLog,
    AcquisitionOutcome,
    DexProviderError,
    ProviderCapability,
    RawHttpAcquirer,
    ScreeningDecision,
    ScreeningProvider,
    ScreeningStatus,
    ScreeningThresholds,
    canonical_json,
    decide_screening,
)

DAY_SECONDS = 86_400
_EVM_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")


class DexSnapshotError(RuntimeError):
    """Raised for invalid bars, identity violations, or unresolved gaps."""


# ---------------------------------------------------------------------------
# Pool identity
# ---------------------------------------------------------------------------

def canonical_pool_address(address: str) -> str:
    """Canonicalise a pool address for identity and dedupe.

    EVM addresses are case-insensitive, so they lowercase. Non-EVM addresses (Solana
    base58, for example) are case-sensitive and are preserved exactly -- lowercasing
    them would merge genuinely different pools.
    """
    if not isinstance(address, str):
        raise DexSnapshotError("pool address must be a string")
    stripped = address.strip()
    if not stripped:
        raise DexSnapshotError("pool address must not be empty")
    if _EVM_ADDRESS.match(stripped):
        return stripped.lower()
    return stripped


def canonical_chain(chain: str) -> str:
    if not isinstance(chain, str) or not chain.strip():
        raise DexSnapshotError("chain must be a non-empty string")
    return chain.strip().lower()


@dataclass(frozen=True, slots=True)
class PoolIdentity:
    """`(chain, canonical_pool_address)` -- the key for dedupe and watermarks."""

    chain: str
    pool_address: str

    @classmethod
    def create(cls, chain: str, pool_address: str) -> PoolIdentity:
        return cls(chain=canonical_chain(chain), pool_address=canonical_pool_address(pool_address))

    @property
    def key(self) -> str:
        return f"{self.chain}:{self.pool_address}"


# ---------------------------------------------------------------------------
# Bars
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OhlcvBar:
    """One validated interval bar from a genuine OHLCV response."""

    chain: str
    pool_address: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    provider: str
    raw_object_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "pool_address": self.pool_address,
            "timestamp": self.timestamp.isoformat(),
            "timestamp_us": int(self.timestamp.timestamp() * 1_000_000),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "provider": self.provider,
            "raw_object_id": self.raw_object_id,
        }

    @property
    def dedupe_key(self) -> tuple[str, str, int]:
        return (self.chain, self.pool_address, int(self.timestamp.timestamp()))


def _finite_number(value: Any, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise DexSnapshotError(f"{label} must be numeric, got {value!r}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise DexSnapshotError(f"{label} must be numeric, got {value!r}") from exc
    if not math.isfinite(number):
        raise DexSnapshotError(f"{label} must be finite, got {value!r}")
    return number


def parse_geckoterminal_bars(
    payload: Any,
    *,
    identity: PoolIdentity,
    start_time: datetime,
    end_time: datetime,
    raw_object_id: str,
    interval_seconds: int = DAY_SECONDS,
) -> list[OhlcvBar]:
    """Decode and validate GeckoTerminal interval OHLCV.

    Validation is fail-closed on every axis the ticket names: UTC timestamps, the
    requested range, interval alignment, finite values, `low <= open/close <= high`,
    non-negative volume, uniqueness and deterministic order.
    """
    if not isinstance(payload, Mapping):
        raise DexSnapshotError("OHLCV response must be a JSON object")
    data = payload.get("data")
    attributes = data.get("attributes") if isinstance(data, Mapping) else None
    if not isinstance(attributes, Mapping):
        raise DexSnapshotError("OHLCV response has no data.attributes")
    items = attributes.get("ohlcv_list")
    if not isinstance(items, list):
        raise DexSnapshotError("ohlcv_list must be a list")

    seen: set[int] = set()
    bars: list[OhlcvBar] = []
    for item in items:
        if not isinstance(item, Sequence) or isinstance(item, (str, bytes)) or len(item) < 6:
            raise DexSnapshotError("each OHLCV item must be a sequence of at least 6 fields")
        raw_ts, raw_open, raw_high, raw_low, raw_close, raw_volume = item[:6]

        if isinstance(raw_ts, bool) or not isinstance(raw_ts, (int, float)):
            raise DexSnapshotError(f"bar timestamp must be a unix number, got {raw_ts!r}")
        epoch = int(raw_ts)
        if epoch != raw_ts:
            raise DexSnapshotError(f"bar timestamp must be a whole second, got {raw_ts!r}")
        if epoch % interval_seconds != 0:
            raise DexSnapshotError(
                f"bar timestamp {epoch} is not aligned to a {interval_seconds}s interval"
            )
        timestamp = datetime.fromtimestamp(epoch, UTC)
        if not start_time <= timestamp <= end_time:
            raise DexSnapshotError(
                f"bar {timestamp.isoformat()} is outside the requested range "
                f"[{start_time.isoformat()}, {end_time.isoformat()}]"
            )
        if epoch in seen:
            raise DexSnapshotError(f"duplicate bar timestamp {timestamp.isoformat()}")
        seen.add(epoch)

        open_ = _finite_number(raw_open, label="open")
        high = _finite_number(raw_high, label="high")
        low = _finite_number(raw_low, label="low")
        close = _finite_number(raw_close, label="close")
        volume = _finite_number(raw_volume, label="volume")
        if volume < 0:
            raise DexSnapshotError(f"volume must be non-negative, got {volume}")
        if low > high:
            raise DexSnapshotError(f"low {low} exceeds high {high}")
        for name, value in (("open", open_), ("close", close)):
            if not low <= value <= high:
                raise DexSnapshotError(f"{name} {value} outside [low {low}, high {high}]")

        bars.append(OhlcvBar(
            chain=identity.chain,
            pool_address=identity.pool_address,
            timestamp=timestamp,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
            provider=GECKOTERMINAL_PROVIDER,
            raw_object_id=raw_object_id,
        ))

    return sorted(bars, key=lambda bar: bar.timestamp)


def find_interval_gaps(
    bars: Sequence[OhlcvBar], *, interval_seconds: int = DAY_SECONDS
) -> list[tuple[datetime, datetime]]:
    """Return the open intervals missing between consecutive bars.

    Gaps are reported, never filled: a synthesised bar would be indistinguishable
    from an observed one downstream.
    """
    gaps: list[tuple[datetime, datetime]] = []
    ordered = sorted(bars, key=lambda bar: bar.timestamp)
    for previous, following in zip(ordered, ordered[1:], strict=False):
        delta = int((following.timestamp - previous.timestamp).total_seconds())
        if delta > interval_seconds:
            gaps.append((previous.timestamp, following.timestamp))
    return gaps


def contiguous_prefix_end(
    bars: Sequence[OhlcvBar], *, interval_seconds: int = DAY_SECONDS
) -> datetime | None:
    """Timestamp of the last bar before the first gap.

    This is the only value a watermark may advance to: everything after the first
    gap is not contiguous and must be re-acquired.
    """
    ordered = sorted(bars, key=lambda bar: bar.timestamp)
    if not ordered:
        return None
    last = ordered[0].timestamp
    for previous, following in zip(ordered, ordered[1:], strict=False):
        if int((following.timestamp - previous.timestamp).total_seconds()) > interval_seconds:
            return last
        last = following.timestamp
    return last


def merge_canonical_bars(
    prior: Iterable[OhlcvBar], acquired: Iterable[OhlcvBar]
) -> list[OhlcvBar]:
    """Merge prior canonical rows with newly acquired rows.

    Newly acquired rows win on collision, and the result is deterministically ordered
    by `(chain, pool_address, timestamp)`. The output is a full snapshot, never a delta.
    """
    merged: dict[tuple[str, str, int], OhlcvBar] = {}
    for bar in prior:
        merged[bar.dedupe_key] = bar
    for bar in acquired:
        merged[bar.dedupe_key] = bar
    return [merged[key] for key in sorted(merged)]


# ---------------------------------------------------------------------------
# Watermarks
# ---------------------------------------------------------------------------

def watermark_key(*, provider: str, identity: PoolIdentity) -> str:
    return f"{provider}:{identity.chain}:{identity.pool_address}"


class WatermarkStore:
    """Per-(provider, chain, pool) watermarks persisted atomically.

    Unrelated shards are always retained: the file is re-read and merged on save, so
    a run covering one provider cannot drop another provider's progress.
    """

    SECTION = "dex002_snapshot"

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def load(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            document = _read_json(self._path)
        except DexSnapshotError:
            raise
        section = document.get(self.SECTION, {})
        if not isinstance(section, Mapping):
            raise DexSnapshotError(f"{self.SECTION} watermark section must be an object")
        return {str(k): str(v) for k, v in section.items()}

    def save(self, watermarks: Mapping[str, str]) -> None:
        document: dict[str, Any] = {}
        if self._path.exists():
            document = _read_json(self._path)
        document[self.SECTION] = dict(sorted(watermarks.items()))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        temporary.write_text(canonical_json(document) + "\n", encoding="utf-8")
        temporary.replace(self._path)


def _read_json(path: Path) -> dict[str, Any]:
    import json

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DexSnapshotError(f"cannot read watermark file {path}") from exc
    if not isinstance(document, dict):
        raise DexSnapshotError(f"watermark file {path} must contain an object")
    return document


def resume_start(
    watermarks: Mapping[str, str],
    *,
    provider: str,
    identity: PoolIdentity,
    default_start: datetime,
    interval_seconds: int = DAY_SECONDS,
) -> datetime:
    """Next interval to request, or the configured default on first sight."""
    recorded = watermarks.get(watermark_key(provider=provider, identity=identity))
    if not recorded:
        return default_start
    try:
        last = datetime.fromisoformat(recorded)
    except ValueError as exc:
        raise DexSnapshotError(f"watermark {recorded!r} is not an ISO-8601 timestamp") from exc
    if last.tzinfo is None:
        raise DexSnapshotError(f"watermark {recorded!r} must be timezone-aware")
    return last + timedelta(seconds=interval_seconds)


# ---------------------------------------------------------------------------
# Acquisition
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PoolAcquisition:
    """Everything one pool contributed to a run."""

    identity: PoolIdentity
    decision: ScreeningDecision
    bars: tuple[OhlcvBar, ...]
    gaps: tuple[tuple[datetime, datetime], ...]
    outcomes: tuple[AcquisitionOutcome, ...]
    watermark_candidate: datetime | None
    error: str | None = None

    @property
    def usable(self) -> bool:
        return self.error is None and bool(self.bars)


class GeckoTerminalOhlcvSource:
    """The only current OHLCV authority. Screening providers cannot reach this path."""

    provider_id = GECKOTERMINAL_PROVIDER
    capability = ProviderCapability.INTERVAL_OHLCV
    BASE_URL = "https://api.geckoterminal.com/api/v2/networks"
    SOURCE_ID = "geckoterminal_ohlcv"

    def __init__(self, *, timeframe: str = "day", aggregate: int = 1) -> None:
        self._timeframe = timeframe
        self._aggregate = aggregate

    def fetch(
        self,
        *,
        identity: PoolIdentity,
        start_time: datetime,
        end_time: datetime,
        acquirer: RawHttpAcquirer,
        interval_seconds: int = DAY_SECONDS,
    ) -> tuple[list[OhlcvBar], AcquisitionOutcome]:
        outcome = acquirer.get_json(
            provider=self.provider_id,
            url=(
                f"{self.BASE_URL}/{identity.chain}/pools/{identity.pool_address}"
                f"/ohlcv/{self._timeframe}"
            ),
            params={
                "aggregate": self._aggregate,
                "before_timestamp": int(end_time.timestamp()),
                "limit": 1000,
                "currency": "usd",
            },
            source_id=self.SOURCE_ID,
            original_name=f"geckoterminal_{identity.chain}_{identity.pool_address}.json",
        )
        if not outcome.ok:
            return [], outcome
        bars = parse_geckoterminal_bars(
            outcome.payload,
            identity=identity,
            start_time=start_time,
            end_time=end_time,
            raw_object_id=str(outcome.raw_object_id),
            interval_seconds=interval_seconds,
        )
        return bars, outcome


class DexSnapshotEngine:
    """Screen pools, acquire genuine bars, and report what may be published."""

    def __init__(
        self,
        *,
        acquirer: RawHttpAcquirer,
        screening_providers: Sequence[ScreeningProvider],
        ohlcv_source: GeckoTerminalOhlcvSource | None = None,
        thresholds: ScreeningThresholds | None = None,
        interval_seconds: int = DAY_SECONDS,
    ) -> None:
        self._acquirer = acquirer
        self._screening_providers = list(screening_providers)
        self._ohlcv_source = ohlcv_source or GeckoTerminalOhlcvSource()
        self._thresholds = thresholds or ScreeningThresholds()
        self._interval_seconds = interval_seconds

    @property
    def thresholds(self) -> ScreeningThresholds:
        return self._thresholds

    @property
    def log(self) -> AcquisitionLog:
        return self._acquirer.log

    def screen(self, identity: PoolIdentity) -> ScreeningDecision:
        """Call every configured provider for auditable context, then decide."""
        observations = [
            provider.observe(
                chain=identity.chain,
                pool_address=identity.pool_address,
                thresholds=self._thresholds,
                acquirer=self._acquirer,
            )
            for provider in self._screening_providers
        ]
        return decide_screening(
            chain=identity.chain,
            pool_address=identity.pool_address,
            observations=observations,
            thresholds=self._thresholds,
        )

    def acquire_pool(
        self,
        *,
        identity: PoolIdentity,
        watermarks: Mapping[str, str],
        default_start: datetime,
        end_time: datetime,
    ) -> PoolAcquisition:
        decision = self.screen(identity)
        if not decision.passed:
            return PoolAcquisition(
                identity=identity, decision=decision, bars=(), gaps=(), outcomes=(),
                watermark_candidate=None,
                error=f"screening {decision.status.value}: {decision.reason}",
            )

        start_time = resume_start(
            watermarks,
            provider=self._ohlcv_source.provider_id,
            identity=identity,
            default_start=default_start,
            interval_seconds=self._interval_seconds,
        )
        if start_time > end_time:
            return PoolAcquisition(
                identity=identity, decision=decision, bars=(), gaps=(), outcomes=(),
                watermark_candidate=None, error="already current",
            )

        try:
            bars, outcome = self._ohlcv_source.fetch(
                identity=identity, start_time=start_time, end_time=end_time,
                acquirer=self._acquirer, interval_seconds=self._interval_seconds,
            )
        except DexSnapshotError as exc:
            return PoolAcquisition(
                identity=identity, decision=decision, bars=(), gaps=(), outcomes=(),
                watermark_candidate=None, error=f"invalid OHLCV response: {exc}",
            )

        if not outcome.ok:
            return PoolAcquisition(
                identity=identity, decision=decision, bars=(), gaps=(),
                outcomes=(outcome,), watermark_candidate=None,
                error=f"OHLCV {outcome.failure_kind}: {outcome.detail}",
            )
        if not bars:
            return PoolAcquisition(
                identity=identity, decision=decision, bars=(), gaps=(),
                outcomes=(outcome,), watermark_candidate=None, error="no rows returned",
            )

        gaps = find_interval_gaps(bars, interval_seconds=self._interval_seconds)
        return PoolAcquisition(
            identity=identity,
            decision=decision,
            bars=tuple(bars),
            gaps=tuple(gaps),
            outcomes=(outcome,),
            # Only the contiguous prefix is publishable progress.
            watermark_candidate=contiguous_prefix_end(
                bars, interval_seconds=self._interval_seconds
            ),
        )


def config_fingerprint(config: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(dict(config)).encode()).hexdigest()


def bars_from_records(records: Iterable[Mapping[str, Any]]) -> list[OhlcvBar]:
    """Rebuild bars from a previously published canonical snapshot."""
    restored: list[OhlcvBar] = []
    for record in records:
        timestamp = datetime.fromisoformat(str(record["timestamp"]))
        if timestamp.tzinfo is None:
            raise DexSnapshotError("prior snapshot timestamps must be timezone-aware")
        restored.append(OhlcvBar(
            chain=str(record["chain"]),
            pool_address=str(record["pool_address"]),
            timestamp=timestamp,
            open=float(record["open"]),
            high=float(record["high"]),
            low=float(record["low"]),
            close=float(record["close"]),
            volume=float(record["volume"]),
            provider=str(record["provider"]),
            raw_object_id=str(record["raw_object_id"]),
        ))
    return restored


__all__ = [
    "DAY_SECONDS",
    "DexProviderError",
    "DexSnapshotEngine",
    "DexSnapshotError",
    "GeckoTerminalOhlcvSource",
    "OhlcvBar",
    "PoolAcquisition",
    "PoolIdentity",
    "ScreeningStatus",
    "WatermarkStore",
    "bars_from_records",
    "canonical_chain",
    "canonical_pool_address",
    "config_fingerprint",
    "contiguous_prefix_end",
    "find_interval_gaps",
    "merge_canonical_bars",
    "parse_geckoterminal_bars",
    "resume_start",
    "watermark_key",
]
