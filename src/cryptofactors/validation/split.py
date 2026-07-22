"""SPLIT-001 — purged chronological split engine.

Produces deterministic walk-forward / expanding / purged K-fold splits with
event-time purging and optional embargo so training never sees future labels.

Temporal data access uses the reviewed AsOfStore contract via a structural
protocol (validation may not import ``catalog``; callers inject
``CatalogAsOfStore`` or a compatible implementation).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class SplitError(RuntimeError):
    """Fail-closed split construction error."""

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


class SplitMode(StrEnum):
    """Supported chronological split geometries."""

    WALK_FORWARD = "walk_forward"
    EXPANDING = "expanding"
    PURGED_KFOLD = "purged_kfold"


def _require_utc(dt: datetime, *, field: str) -> datetime:
    if not isinstance(dt, datetime):
        raise SplitError(f"{field} must be a datetime", context={"type": type(dt).__name__})
    if dt.tzinfo is None:
        raise SplitError(f"{field} must be timezone-aware UTC", context={"value": str(dt)})
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class EventInterval:
    """One decision event with its label/event-time interval.

    ``decision_time`` is when the strategy decides. ``event_start`` / ``event_end``
    bound the economic event or label horizon (half-open ``[event_start, event_end)``
    when used for overlap). Features for the decision may only use observations with
    ``availability_time <= decision_time`` (enforced via AsOfStore by callers).
    """

    instrument_id: str | int
    decision_time: datetime
    event_start: datetime
    event_end: datetime
    event_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_time", _require_utc(self.decision_time, field="decision_time"))
        object.__setattr__(self, "event_start", _require_utc(self.event_start, field="event_start"))
        object.__setattr__(self, "event_end", _require_utc(self.event_end, field="event_end"))
        if self.event_end <= self.event_start:
            raise SplitError(
                "event_end must be > event_start",
                context={
                    "event_start": self.event_start.isoformat(),
                    "event_end": self.event_end.isoformat(),
                },
            )
        if self.decision_time > self.event_end:
            raise SplitError(
                "decision_time must be <= event_end",
                context={
                    "decision_time": self.decision_time.isoformat(),
                    "event_end": self.event_end.isoformat(),
                },
            )


@dataclass(frozen=True, slots=True)
class SplitConfig:
    """Configuration for purged chronological split generation.

    ``seed`` is reserved for deterministic tie-breaking; pure chronological modes
    do not randomize fold membership.
    """

    mode: SplitMode
    n_folds: int | None = None
    train_span: timedelta | None = None
    test_span: timedelta | None = None
    embargo: timedelta = field(default_factory=lambda: timedelta(0))
    min_train_events: int = 1
    min_test_events: int = 1
    seed: int = 0
    # Optional AsOf dataset id for instrument eligibility checks (REF-001).
    instrument_dataset_id: str = "ref_instrument_version"

    def __post_init__(self) -> None:
        if not isinstance(self.mode, SplitMode):
            object.__setattr__(self, "mode", SplitMode(str(self.mode)))
        if self.embargo.total_seconds() < 0:
            raise SplitError("embargo must be non-negative")
        if self.min_train_events < 1 or self.min_test_events < 1:
            raise SplitError("min_train_events and min_test_events must be >= 1")
        if self.mode is SplitMode.PURGED_KFOLD:
            if self.n_folds is None or self.n_folds < 2:
                raise SplitError(
                    "purged_kfold requires n_folds >= 2",
                    context={"n_folds": self.n_folds},
                )
        if self.mode in (SplitMode.WALK_FORWARD, SplitMode.EXPANDING):
            if self.train_span is None or self.test_span is None:
                raise SplitError(
                    f"{self.mode.value} requires train_span and test_span",
                )
            if self.train_span.total_seconds() <= 0 or self.test_span.total_seconds() <= 0:
                raise SplitError("train_span and test_span must be positive")


@dataclass(frozen=True, slots=True)
class SplitPartition:
    """One named segment of a fold (train or test)."""

    name: str
    start: datetime
    end: datetime
    events: tuple[EventInterval, ...]


@dataclass(frozen=True, slots=True)
class OuterFold:
    """One outer chronological fold with purged train and test partitions."""

    fold_id: int
    train: SplitPartition
    test: SplitPartition
    purge_gap_start: datetime
    purge_gap_end: datetime
    embargo: timedelta
    split_version: str


@runtime_checkable
class AsOfDataAccess(Protocol):
    """Structural AsOfStore surface (no catalog import from validation)."""

    def as_of(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        knowledge_time: datetime | None = None,
    ) -> Any: ...

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> Any: ...


@runtime_checkable
class ChronologicalSplitter(Protocol):
    """Architecture chronological splitter (``03_DOMAIN_INTERFACES`` §10)."""

    split_version: str

    def split(
        self,
        events: Sequence[EventInterval],
        config: SplitConfig,
    ) -> list[OuterFold]: ...


def _events_overlap(a: EventInterval, b: EventInterval) -> bool:
    """Half-open interval overlap on [event_start, event_end)."""
    return a.event_start < b.event_end and b.event_start < a.event_end


def _interval_overlaps_window(
    event: EventInterval, *, window_start: datetime, window_end: datetime
) -> bool:
    """True if event [start, end) overlaps [window_start, window_end)."""
    return event.event_start < window_end and window_start < event.event_end


def _sort_key(event: EventInterval) -> tuple[datetime, datetime, str, str]:
    return (
        event.decision_time,
        event.event_end,
        str(event.instrument_id),
        event.event_id or "",
    )


def purge_train_events(
    train_candidates: Sequence[EventInterval],
    test_events: Sequence[EventInterval],
    *,
    embargo: timedelta,
) -> tuple[EventInterval, ...]:
    """Remove train events that leak into the test event-time window.

    A train event is purged when:
    - its ``event_end`` is after the earliest test decision minus embargo, or
    - its event interval overlaps any test event interval for the same instrument.
    """
    if not test_events:
        return tuple(sorted(train_candidates, key=_sort_key))
    test_by_instr: dict[str, list[EventInterval]] = {}
    earliest_test_decision = min(e.decision_time for e in test_events)
    purge_horizon = earliest_test_decision - embargo
    for te in test_events:
        test_by_instr.setdefault(str(te.instrument_id), []).append(te)

    kept: list[EventInterval] = []
    for tr in train_candidates:
        if tr.event_end > purge_horizon:
            continue
        if tr.decision_time >= earliest_test_decision - embargo:
            continue
        peers = test_by_instr.get(str(tr.instrument_id), [])
        if any(_events_overlap(tr, te) for te in peers):
            continue
        # Also purge if train event interval overlaps the test decision window
        # [earliest_test_decision - embargo, latest_test_event_end).
        latest_test_end = max(e.event_end for e in test_events)
        if _interval_overlaps_window(
            tr,
            window_start=earliest_test_decision - embargo,
            window_end=latest_test_end,
        ):
            continue
        kept.append(tr)
    return tuple(sorted(kept, key=_sort_key))


class PurgedChronologicalSplitter:
    """Deterministic purged chronological splitter (SPLIT-001).

    Parameters
    ----------
    as_of_store:
        Reviewed as-of access implementation. Required for instrument eligibility
        checks against REF-001 via ``config.instrument_dataset_id``.
    """

    split_version: str = "1"

    def __init__(self, as_of_store: AsOfDataAccess) -> None:
        if as_of_store is None:
            raise SplitError("as_of_store is required")
        self._asof = as_of_store

    def split(
        self,
        events: Sequence[EventInterval],
        config: SplitConfig,
    ) -> list[OuterFold]:
        if not events:
            raise SplitError("events must be non-empty")
        cfg = config if isinstance(config, SplitConfig) else SplitConfig(**dict(config))  # type: ignore[arg-type]
        ordered = tuple(sorted(events, key=_sort_key))
        self._validate_instruments(ordered, cfg)

        if cfg.mode is SplitMode.PURGED_KFOLD:
            folds = self._purged_kfold(ordered, cfg)
        elif cfg.mode is SplitMode.WALK_FORWARD:
            folds = self._walk_forward(ordered, cfg, expanding=False)
        elif cfg.mode is SplitMode.EXPANDING:
            folds = self._walk_forward(ordered, cfg, expanding=True)
        else:
            raise SplitError(f"unsupported mode: {cfg.mode!r}")

        if not folds:
            raise SplitError(
                "insufficient history to form any valid fold",
                context={
                    "mode": cfg.mode.value,
                    "event_count": len(ordered),
                    "min_train_events": cfg.min_train_events,
                    "min_test_events": cfg.min_test_events,
                },
            )
        return folds

    def _validate_instruments(
        self, events: Sequence[EventInterval], config: SplitConfig
    ) -> None:
        """Fail closed if AsOfStore cannot resolve instruments at decision times."""
        # Group decision times → instruments for batch as_of calls.
        by_decision: dict[datetime, set[str]] = {}
        for e in events:
            by_decision.setdefault(e.decision_time, set()).add(str(e.instrument_id))
        for decision_time, instruments in sorted(by_decision.items(), key=lambda x: x[0]):
            keys = sorted(instruments)
            try:
                table = self._asof.as_of(
                    config.instrument_dataset_id,
                    keys,
                    ["instrument_id"],
                    decision_time,
                    knowledge_time=decision_time,
                )
            except Exception as exc:  # noqa: BLE001 — surface as split failure
                raise SplitError(
                    "as-of instrument eligibility check failed",
                    context={
                        "dataset_id": config.instrument_dataset_id,
                        "decision_time": decision_time.isoformat(),
                        "error": str(exc),
                    },
                ) from exc
            found: set[str] = set()
            if table is not None and getattr(table, "num_rows", 0) > 0:
                col = table.column("instrument_id")
                found = {str(v.as_py()) for v in col}
            missing = [k for k in keys if k not in found]
            if missing:
                raise SplitError(
                    "instrument not eligible under AsOfStore at decision_time",
                    context={
                        "dataset_id": config.instrument_dataset_id,
                        "decision_time": decision_time.isoformat(),
                        "missing_instrument_ids": missing,
                    },
                )

    def _walk_forward(
        self,
        events: Sequence[EventInterval],
        config: SplitConfig,
        *,
        expanding: bool,
    ) -> list[OuterFold]:
        assert config.train_span is not None and config.test_span is not None
        t0 = min(e.decision_time for e in events)
        t1 = max(e.decision_time for e in events)
        folds: list[OuterFold] = []
        fold_id = 0
        # First test window starts after initial train_span (+ embargo).
        cursor = t0 + config.train_span + config.embargo
        while cursor + config.test_span <= t1 + timedelta(microseconds=1):
            test_start = cursor
            test_end = cursor + config.test_span
            if expanding:
                train_start = t0
            else:
                train_start = test_start - config.embargo - config.train_span
            train_end = test_start - config.embargo
            if train_end <= train_start:
                cursor = cursor + config.test_span
                continue

            test_events = tuple(
                e
                for e in events
                if test_start <= e.decision_time < test_end
            )
            train_pool = tuple(
                e
                for e in events
                if train_start <= e.decision_time < train_end
            )
            train_events = purge_train_events(
                train_pool, test_events, embargo=config.embargo
            )
            if (
                len(train_events) < config.min_train_events
                or len(test_events) < config.min_test_events
            ):
                cursor = cursor + config.test_span
                continue

            folds.append(
                OuterFold(
                    fold_id=fold_id,
                    train=SplitPartition(
                        name="train",
                        start=train_start,
                        end=train_end,
                        events=train_events,
                    ),
                    test=SplitPartition(
                        name="test",
                        start=test_start,
                        end=test_end,
                        events=test_events,
                    ),
                    purge_gap_start=train_end,
                    purge_gap_end=test_start,
                    embargo=config.embargo,
                    split_version=self.split_version,
                )
            )
            fold_id += 1
            cursor = cursor + config.test_span
        return folds

    def _purged_kfold(
        self,
        events: Sequence[EventInterval],
        config: SplitConfig,
    ) -> list[OuterFold]:
        assert config.n_folds is not None
        n = config.n_folds
        # Contiguous time folds on decision_time order.
        times = sorted({e.decision_time for e in events})
        if len(times) < n:
            raise SplitError(
                "not enough distinct decision_times for purged_kfold",
                context={"distinct_decision_times": len(times), "n_folds": n},
            )
        # Partition sorted events into n contiguous blocks by decision_time rank.
        sorted_events = list(events)
        block_size = len(sorted_events) // n
        if block_size < 1:
            raise SplitError("insufficient events for purged_kfold")

        folds: list[OuterFold] = []
        for fold_id in range(n):
            start_idx = fold_id * block_size
            end_idx = (fold_id + 1) * block_size if fold_id < n - 1 else len(sorted_events)
            test_events = tuple(sorted_events[start_idx:end_idx])
            if not test_events:
                continue
            test_start = test_events[0].decision_time
            test_end = max(e.decision_time for e in test_events) + timedelta(microseconds=1)
            # Train: all events strictly before the purge boundary.
            train_end = test_start - config.embargo
            train_pool = tuple(
                e for e in sorted_events if e.decision_time < train_end
            )
            train_events = purge_train_events(
                train_pool, test_events, embargo=config.embargo
            )
            if (
                len(train_events) < config.min_train_events
                or len(test_events) < config.min_test_events
            ):
                # Skip empty/insufficient folds fail-closed only if ALL folds fail later.
                continue
            train_start = (
                min(e.decision_time for e in train_events)
                if train_events
                else train_end
            )
            folds.append(
                OuterFold(
                    fold_id=fold_id,
                    train=SplitPartition(
                        name="train",
                        start=train_start,
                        end=train_end,
                        events=train_events,
                    ),
                    test=SplitPartition(
                        name="test",
                        start=test_start,
                        end=test_end,
                        events=test_events,
                    ),
                    purge_gap_start=train_end,
                    purge_gap_end=test_start,
                    embargo=config.embargo,
                    split_version=self.split_version,
                )
            )
        return folds
