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
from enum import Enum
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
_BASE58_ADDRESS = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

EVM_FAMILY = "evm"
SOLANA_FAMILY = "solana"

# Which address grammar each chain uses. A chain that is not registered here is
# refused rather than guessed: accepting an unknown chain would mean accepting an
# unvalidated address, which is how a malformed EVM address became a "non-EVM"
# identity under the previous implementation.
CHAIN_FAMILIES: dict[str, str] = {
    "arbitrum": EVM_FAMILY,
    "avalanche": EVM_FAMILY,
    "base": EVM_FAMILY,
    "bsc": EVM_FAMILY,
    "ethereum": EVM_FAMILY,
    "linea": EVM_FAMILY,
    "optimism": EVM_FAMILY,
    "polygon": EVM_FAMILY,
    "scroll": EVM_FAMILY,
    "zksync": EVM_FAMILY,
    "solana": SOLANA_FAMILY,
}


class DexSnapshotError(RuntimeError):
    """Raised for invalid bars, identity violations, or unresolved gaps."""


class AcquisitionState(str, Enum):
    """Terminal state of one pool's acquisition.

    Every state except ``PUBLISHABLE`` and ``ALREADY_CURRENT`` means the pool has no
    complete, trustworthy coverage for the requested window. For a pool that passed
    screening, that must block the whole publication: dropping it while publishing a
    clean sibling would silently narrow the snapshot.
    """

    PUBLISHABLE = "PUBLISHABLE"
    ALREADY_CURRENT = "ALREADY_CURRENT"
    SCREENED_OUT = "SCREENED_OUT"
    FAILED = "FAILED"
    EMPTY = "EMPTY"
    INVALID = "INVALID"
    GAPPED = "GAPPED"


#: States that block publication when the pool passed screening.
BLOCKING_STATES = frozenset({
    AcquisitionState.FAILED,
    AcquisitionState.EMPTY,
    AcquisitionState.INVALID,
    AcquisitionState.GAPPED,
})


# ---------------------------------------------------------------------------
# Pool identity
# ---------------------------------------------------------------------------

def chain_family(chain: str) -> str:
    """The address grammar a chain uses, or a typed refusal."""
    normalized = canonical_chain(chain)
    family = CHAIN_FAMILIES.get(normalized)
    if family is None:
        raise DexSnapshotError(
            f"chain {normalized!r} has no registered address family; register it in "
            "CHAIN_FAMILIES before ingesting it"
        )
    return family


def canonical_pool_address(address: str, *, chain: str) -> str:
    """Canonicalise a pool address against its chain's address grammar.

    EVM addresses are case-insensitive, so they lowercase. Solana base58 is
    case-sensitive and is preserved exactly -- lowercasing would merge genuinely
    different pools. Validation is chain-driven: a malformed ``0x...`` value on an
    EVM chain is refused rather than silently accepted as a non-EVM identity.
    """
    if not isinstance(address, str):
        raise DexSnapshotError("pool address must be a string")
    stripped = address.strip()
    if not stripped:
        raise DexSnapshotError("pool address must not be empty")

    family = chain_family(chain)
    if family == EVM_FAMILY:
        if not _EVM_ADDRESS.match(stripped):
            raise DexSnapshotError(
                f"{stripped!r} is not a valid 20-byte EVM address for chain {chain!r}"
            )
        return stripped.lower()
    if family == SOLANA_FAMILY:
        if not _BASE58_ADDRESS.match(stripped):
            raise DexSnapshotError(
                f"{stripped!r} is not a valid base58 address for chain {chain!r}"
            )
        return stripped
    raise DexSnapshotError(f"unsupported address family {family!r}")


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
        normalized_chain = canonical_chain(chain)
        return cls(
            chain=normalized_chain,
            pool_address=canonical_pool_address(pool_address, chain=normalized_chain),
        )

    @property
    def key(self) -> str:
        return f"{self.chain}:{self.pool_address}"


def validate_token_addresses(
    tokens: Iterable[str] | None, *, chain: str
) -> tuple[str, ...]:
    """Validate optional base/quote token identities against the chain family."""
    if not tokens:
        return ()
    return tuple(canonical_pool_address(str(token), chain=chain) for token in tokens)


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


def validate_bar_values(
    *,
    open_: Any,
    high: Any,
    low: Any,
    close: Any,
    volume: Any,
) -> tuple[float, float, float, float, float]:
    """The OHLC/volume invariants every bar must satisfy, however it was obtained."""
    values = (
        _finite_number(open_, label="open"),
        _finite_number(high, label="high"),
        _finite_number(low, label="low"),
        _finite_number(close, label="close"),
        _finite_number(volume, label="volume"),
    )
    open_v, high_v, low_v, close_v, volume_v = values
    if volume_v < 0:
        raise DexSnapshotError(f"volume must be non-negative, got {volume_v}")
    if low_v > high_v:
        raise DexSnapshotError(f"low {low_v} exceeds high {high_v}")
    for name, value in (("open", open_v), ("close", close_v)):
        if not low_v <= value <= high_v:
            raise DexSnapshotError(f"{name} {value} outside [low {low_v}, high {high_v}]")
    return values


def validate_bar_timestamp(
    timestamp: datetime, *, interval_seconds: int = DAY_SECONDS
) -> datetime:
    """Timestamps must be timezone-aware UTC and aligned to the interval."""
    if timestamp.tzinfo is None:
        raise DexSnapshotError(f"bar timestamp {timestamp!r} must be timezone-aware")
    moment = timestamp.astimezone(UTC)
    if int(moment.timestamp()) % interval_seconds:
        raise DexSnapshotError(
            f"bar timestamp {moment.isoformat()} is not aligned to a "
            f"{interval_seconds}s interval"
        )
    return moment


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
            # GeckoTerminal's before_timestamp+limit pagination legitimately returns
            # bars older than the requested window. Extra history is normal API
            # behaviour, not corruption, so it is excluded rather than fatal -- and
            # coverage validation still catches anything missing *inside* the range.
            continue
        if epoch in seen:
            raise DexSnapshotError(f"duplicate bar timestamp {timestamp.isoformat()}")
        seen.add(epoch)

        open_, high, low, close, volume = validate_bar_values(
            open_=raw_open, high=raw_high, low=raw_low, close=raw_close, volume=raw_volume
        )

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


def expected_interval_starts(
    *, start_time: datetime, end_time: datetime, interval_seconds: int = DAY_SECONDS
) -> list[datetime]:
    """Every interval the request was supposed to cover, inclusive."""
    if start_time > end_time:
        return []
    first = int(start_time.timestamp())
    last = int(end_time.timestamp())
    if first % interval_seconds or last % interval_seconds:
        raise DexSnapshotError("requested range must align to the interval")
    return [
        datetime.fromtimestamp(epoch, UTC)
        for epoch in range(first, last + 1, interval_seconds)
    ]


def missing_intervals(
    bars: Sequence[OhlcvBar],
    *,
    start_time: datetime,
    end_time: datetime,
    interval_seconds: int = DAY_SECONDS,
) -> list[datetime]:
    """Requested intervals with no bar, including leading and trailing ones.

    `find_interval_gaps` only sees holes *between* returned bars, so a response
    that simply starts late or stops early looks complete to it. Coverage has to be
    judged against the range that was requested, not against what came back.
    """
    present = {int(bar.timestamp.timestamp()) for bar in bars}
    return [
        moment
        for moment in expected_interval_starts(
            start_time=start_time, end_time=end_time, interval_seconds=interval_seconds
        )
        if int(moment.timestamp()) not in present
    ]


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
    missing_intervals: tuple[datetime, ...] = ()
    requested_start: datetime | None = None
    requested_end: datetime | None = None
    state: AcquisitionState = AcquisitionState.PUBLISHABLE

    @property
    def has_unresolved_coverage(self) -> bool:
        """Any hole -- internal, leading or trailing -- makes this pool unpublishable."""
        return bool(self.missing_intervals) or bool(self.gaps)

    @property
    def usable(self) -> bool:
        """Publishable only with exact requested coverage."""
        return self.state is AcquisitionState.PUBLISHABLE

    @property
    def blocks_publication(self) -> bool:
        """A screened-PASS pool in a blocking state stops the entire run.

        Coverage gaps are not the only way a passed pool can be incomplete: an HTTP
        failure, a transport failure, an invalid payload and a zero-row response all
        leave no gaps to find, yet each means the pool is missing from the snapshot.
        """
        return self.decision.passed and self.state in BLOCKING_STATES

    def coverage_report(self) -> dict[str, Any]:
        return {
            "requested_start": None if self.requested_start is None else self.requested_start.isoformat(),
            "requested_end": None if self.requested_end is None else self.requested_end.isoformat(),
            "row_count": len(self.bars),
            "internal_gaps": [
                {"after": start.isoformat(), "before": end.isoformat()}
                for start, end in self.gaps
            ],
            "missing_intervals": [moment.isoformat() for moment in self.missing_intervals],
            "unresolved": self.has_unresolved_coverage,
            "state": self.state.value,
        }


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

    def screen(
        self, identity: PoolIdentity, *, token_addresses: Sequence[str] | None = None
    ) -> ScreeningDecision:
        """Call every configured provider for auditable context, then decide."""
        observations = [
            provider.observe(
                chain=identity.chain,
                pool_address=identity.pool_address,
                thresholds=self._thresholds,
                acquirer=self._acquirer,
                token_addresses=token_addresses,
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
        token_addresses: Sequence[str] | None = None,
    ) -> PoolAcquisition:
        decision = self.screen(identity, token_addresses=token_addresses)
        if not decision.passed:
            return PoolAcquisition(
                identity=identity, decision=decision, bars=(), gaps=(), outcomes=(),
                watermark_candidate=None,
                error=f"screening {decision.status.value}: {decision.reason}",
                state=AcquisitionState.SCREENED_OUT,
            )

        start_time = resume_start(
            watermarks,
            provider=self._ohlcv_source.provider_id,
            identity=identity,
            default_start=default_start,
            interval_seconds=self._interval_seconds,
        )
        if start_time > end_time:
            # Provisional: the runner promotes this only when prior canonical rows
            # prove the pool is complete through the pinned end.
            return PoolAcquisition(
                identity=identity, decision=decision, bars=(), gaps=(), outcomes=(),
                watermark_candidate=None, error=None,
                state=AcquisitionState.ALREADY_CURRENT,
                requested_start=start_time, requested_end=end_time,
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
                state=AcquisitionState.INVALID,
                requested_start=start_time, requested_end=end_time,
            )

        if not outcome.ok:
            return PoolAcquisition(
                identity=identity, decision=decision, bars=(), gaps=(),
                outcomes=(outcome,), watermark_candidate=None,
                error=f"OHLCV {outcome.failure_kind}: {outcome.detail}",
                state=AcquisitionState.FAILED,
                requested_start=start_time, requested_end=end_time,
            )
        if not bars:
            return PoolAcquisition(
                identity=identity, decision=decision, bars=(), gaps=(),
                outcomes=(outcome,), watermark_candidate=None, error="no rows returned",
                state=AcquisitionState.EMPTY,
                requested_start=start_time, requested_end=end_time,
            )

        gaps = find_interval_gaps(bars, interval_seconds=self._interval_seconds)
        missing = missing_intervals(
            bars, start_time=start_time, end_time=end_time,
            interval_seconds=self._interval_seconds,
        )
        unresolved = bool(gaps) or bool(missing)
        return PoolAcquisition(
            identity=identity,
            decision=decision,
            bars=tuple(bars),
            gaps=tuple(gaps),
            outcomes=(outcome,),
            # Unresolved coverage yields no watermark at all: advancing over a hole
            # would permanently skip the missing intervals.
            watermark_candidate=(
                None if unresolved
                else contiguous_prefix_end(bars, interval_seconds=self._interval_seconds)
            ),
            error="unresolved coverage" if unresolved else None,
            state=AcquisitionState.GAPPED if unresolved else AcquisitionState.PUBLISHABLE,
            missing_intervals=tuple(missing),
            requested_start=start_time,
            requested_end=end_time,
        )


def config_fingerprint(config: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(dict(config)).encode()).hexdigest()


def bars_from_records(
    records: Iterable[Mapping[str, Any]],
    *,
    allowed_raw_object_ids: Iterable[str] | None = None,
    interval_seconds: int = DAY_SECONDS,
) -> list[OhlcvBar]:
    """Rebuild and fully revalidate bars from a previously published snapshot.

    A prior snapshot is untrusted input at merge time: the file may reconcile on hash
    and row count and still contain rows that no longer satisfy the invariants, or
    rows attributed to a provider with no OHLCV capability. Every restored row is put
    through the same checks as a freshly decoded one, and its raw-object id must be
    declared by the prior dataset's own lineage.
    """
    permitted = None if allowed_raw_object_ids is None else {
        str(raw_id) for raw_id in allowed_raw_object_ids
    }
    restored: list[OhlcvBar] = []
    seen: set[tuple[str, str, int]] = set()

    for record in records:
        if not isinstance(record, Mapping):
            raise DexSnapshotError("prior snapshot row must be an object")
        for column in (
            "chain", "pool_address", "timestamp", "open", "high", "low", "close",
            "volume", "provider", "raw_object_id",
        ):
            if column not in record:
                raise DexSnapshotError(f"prior snapshot row is missing {column!r}")

        chain = canonical_chain(str(record["chain"]))
        pool_address = canonical_pool_address(str(record["pool_address"]), chain=chain)
        if pool_address != str(record["pool_address"]):
            raise DexSnapshotError(
                f"prior snapshot row address {record['pool_address']!r} is not canonical "
                f"for chain {chain!r}"
            )

        provider = str(record["provider"])
        if provider != GECKOTERMINAL_PROVIDER:
            raise DexSnapshotError(
                f"prior snapshot row claims provider {provider!r}, which has no OHLCV "
                "capability"
            )

        raw_object_id = str(record["raw_object_id"])
        if not raw_object_id.startswith("raw_"):
            raise DexSnapshotError(f"prior snapshot row has invalid raw object id {raw_object_id!r}")
        if permitted is not None and raw_object_id not in permitted:
            raise DexSnapshotError(
                f"prior snapshot row cites raw object {raw_object_id} which the prior "
                "dataset lineage does not declare"
            )

        try:
            parsed = datetime.fromisoformat(str(record["timestamp"]))
        except ValueError as exc:
            raise DexSnapshotError(
                f"prior snapshot timestamp {record['timestamp']!r} is not ISO-8601"
            ) from exc
        timestamp = validate_bar_timestamp(parsed, interval_seconds=interval_seconds)

        open_, high, low, close, volume = validate_bar_values(
            open_=record["open"], high=record["high"], low=record["low"],
            close=record["close"], volume=record["volume"],
        )

        bar = OhlcvBar(
            chain=chain, pool_address=pool_address, timestamp=timestamp, open=open_,
            high=high, low=low, close=close, volume=volume, provider=provider,
            raw_object_id=raw_object_id,
        )
        if bar.dedupe_key in seen:
            raise DexSnapshotError(
                f"prior snapshot contains duplicate identity {bar.dedupe_key}"
            )
        seen.add(bar.dedupe_key)
        restored.append(bar)

    return restored


def pool_covers_range(
    bars: Iterable[OhlcvBar],
    *,
    identity: PoolIdentity,
    start_time: datetime,
    end_time: datetime,
    interval_seconds: int = DAY_SECONDS,
) -> tuple[bool, list[datetime]]:
    """Whether prior canonical rows cover *every* interval in the requested range.

    Returns the verdict and the missing intervals. An end-point-only check is not
    proof: a prior snapshot with leading or internal holes can still carry the final
    bar, and accepting that as ALREADY_CURRENT would freeze the holes in place -- the
    watermark says the pool is done, so nothing ever re-fetches them.
    """
    present = {
        int(bar.timestamp.timestamp())
        for bar in bars
        if bar.chain == identity.chain and bar.pool_address == identity.pool_address
    }
    expected = expected_interval_starts(
        start_time=start_time, end_time=end_time, interval_seconds=interval_seconds
    )
    missing = [moment for moment in expected if int(moment.timestamp()) not in present]
    return (not missing and bool(expected)), missing


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
    "AcquisitionState",
    "BLOCKING_STATES",
    "bars_from_records",
    "canonical_chain",
    "canonical_pool_address",
    "config_fingerprint",
    "chain_family",
    "contiguous_prefix_end",
    "expected_interval_starts",
    "find_interval_gaps",
    "missing_intervals",
    "merge_canonical_bars",
    "pool_covers_range",
    "validate_bar_timestamp",
    "validate_token_addresses",
    "validate_bar_values",
    "parse_geckoterminal_bars",
    "resume_start",
    "watermark_key",
]
