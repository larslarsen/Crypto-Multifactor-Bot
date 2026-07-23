"""SERV-001 — artifact/representation parity harness and serving wrappers.

Bridge between research and serving: proves that factors (baselines, composites, ML)
compute identically in an incremental serving context as in historical batch context.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from cryptofactors.factors.contract import Factor, FactorFrame


class ParityError(RuntimeError):
    """Raised when parity verification fails or inputs are invalid."""

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


def _require_utc(dt: datetime, *, field: str) -> datetime:
    if not isinstance(dt, datetime):
        raise ParityError(
            f"{field} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise ParityError(
            f"{field} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


@runtime_checkable
class AsOfStore(Protocol):
    """As-of store interface used by serving parity harness."""

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: Any = None,
    ) -> Any: ...

    def as_of(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        knowledge_time: datetime | None = None,
    ) -> Any: ...


class TruncatedAsOfStoreAdapter:
    """Store wrapper enforcing point-in-time boundary for incremental serving.

    Prevents queries beyond ``max_availability_time`` and filters returned tables
    to simulate a production store where data past ``max_availability_time`` does
    not exist yet.
    """

    def __init__(self, inner_store: Any, max_availability_time: datetime) -> None:
        if inner_store is None:
            raise ParityError("inner_store must not be None")
        self._inner = inner_store
        self._max_time = _require_utc(
            max_availability_time, field="max_availability_time"
        )

    @property
    def max_availability_time(self) -> datetime:
        return self._max_time

    def _filter_table(self, table: Any) -> Any:
        if table is None or getattr(table, "num_rows", 0) == 0:
            return table
        names = getattr(table, "column_names", [])
        if "availability_time" in names:
            import pyarrow as pa
            import pyarrow.compute as pc

            max_us = int(self._max_time.timestamp() * 1_000_000)
            col = table.column("availability_time")
            mask = pc.less_equal(col, pa.scalar(max_us, type=col.type))
            return table.filter(mask)
        return table

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: Any = None,
    ) -> Any:
        dt = _require_utc(decision_time, field="decision_time")
        if dt > self._max_time:
            raise ParityError(
                "decision_time exceeds max_availability_time of serving store",
                context={
                    "decision_time": dt.isoformat(),
                    "max_availability_time": self._max_time.isoformat(),
                },
            )
        table = self._inner.latest_available(dataset_id, keys, fields, dt, max_age)
        return self._filter_table(table)

    def as_of(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        knowledge_time: datetime | None = None,
    ) -> Any:
        dt = _require_utc(decision_time, field="decision_time")
        kt = (
            _require_utc(knowledge_time, field="knowledge_time")
            if knowledge_time
            else dt
        )
        if dt > self._max_time or kt > self._max_time:
            raise ParityError(
                "decision_time or knowledge_time exceeds max_availability_time of serving store",
                context={
                    "decision_time": dt.isoformat(),
                    "knowledge_time": kt.isoformat(),
                    "max_availability_time": self._max_time.isoformat(),
                },
            )
        table = self._inner.as_of(dataset_id, keys, fields, dt, knowledge_time=kt)
        return self._filter_table(table)


class ServingFactorEvaluator:
    """Incremental daily serving wrapper for factor evaluation."""

    def __init__(
        self,
        factor: Factor,
        *,
        strict_chronological: bool = True,
    ) -> None:
        if factor is None or not isinstance(factor, Factor):
            raise ParityError("factor must implement Factor protocol")
        self._factor = factor
        self._strict_chronological = strict_chronological
        self._last_decision_time: datetime | None = None

    @property
    def factor(self) -> Factor:
        return self._factor

    def evaluate_daily(
        self,
        universe: Sequence[str],
        decision_time: datetime,
    ) -> FactorFrame:
        dt = _require_utc(decision_time, field="decision_time")
        if self._strict_chronological and self._last_decision_time is not None:
            if dt <= self._last_decision_time:
                raise ParityError(
                    "serving decision_time must strictly advance chronologically",
                    context={
                        "previous": self._last_decision_time.isoformat(),
                        "current": dt.isoformat(),
                    },
                )
        frame = self._factor.compute(universe, dt)
        self._last_decision_time = dt
        return frame


@dataclass(frozen=True, slots=True)
class ParityComparison:
    decision_time: datetime
    batch_frame: FactorFrame
    serving_frame: FactorFrame
    is_equal: bool
    diffs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ParityResult:
    factor_id: str
    factor_version: str
    decision_times: tuple[datetime, ...]
    comparisons: tuple[ParityComparison, ...]

    @property
    def is_parity_satisfied(self) -> bool:
        return all(c.is_equal for c in self.comparisons)


def _values_close(a: float, b: float, *, rel_tol: float, abs_tol: float) -> bool:
    if math.isnan(a) and math.isnan(b):
        return True
    if math.isinf(a) and math.isinf(b):
        return (a > 0) == (b > 0)
    if math.isnan(a) or math.isnan(b) or math.isinf(a) or math.isinf(b):
        return False
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


def compare_factor_frames(
    batch_frame: FactorFrame,
    serving_frame: FactorFrame,
    *,
    rel_tol: float = 1e-7,
    abs_tol: float = 1e-7,
) -> tuple[bool, tuple[str, ...]]:
    """Compare two FactorFrames for exact/near-exact value and score parity."""
    diffs: list[str] = []

    if batch_frame.factor_id != serving_frame.factor_id:
        diffs.append(
            f"factor_id mismatch: batch={batch_frame.factor_id!r} vs serving={serving_frame.factor_id!r}"
        )

    if batch_frame.factor_version != serving_frame.factor_version:
        diffs.append(
            f"factor_version mismatch: batch={batch_frame.factor_version!r} vs serving={serving_frame.factor_version!r}"
        )

    if batch_frame.decision_time != serving_frame.decision_time:
        diffs.append(
            f"decision_time mismatch: batch={batch_frame.decision_time.isoformat()} vs serving={serving_frame.decision_time.isoformat()}"
        )

    b_map = {v.instrument_id: v for v in batch_frame.values}
    s_map = {v.instrument_id: v for v in serving_frame.values}

    b_iids = set(b_map.keys())
    s_iids = set(s_map.keys())

    if b_iids != s_iids:
        missing_in_serving = b_iids - s_iids
        extra_in_serving = s_iids - b_iids
        diffs.append(
            f"instrument set mismatch: missing_in_serving={sorted(missing_in_serving)}, extra_in_serving={sorted(extra_in_serving)}"
        )

    for iid in sorted(b_iids & s_iids):
        bv = b_map[iid]
        sv = s_map[iid]

        if bv.availability_time != sv.availability_time:
            diffs.append(
                f"[{iid}] availability_time mismatch: batch={bv.availability_time.isoformat()} vs serving={sv.availability_time.isoformat()}"
            )

        if not _values_close(
            bv.raw_value, sv.raw_value, rel_tol=rel_tol, abs_tol=abs_tol
        ):
            diffs.append(
                f"[{iid}] raw_value mismatch: batch={bv.raw_value} vs serving={sv.raw_value}"
            )

        if not _values_close(bv.score, sv.score, rel_tol=rel_tol, abs_tol=abs_tol):
            diffs.append(
                f"[{iid}] score mismatch: batch={bv.score} vs serving={sv.score}"
            )

    return len(diffs) == 0, tuple(diffs)


class ParityHarness:
    """Test harness comparing batch research vs incremental serving factor frames."""

    def __init__(
        self,
        *,
        rel_tol: float = 1e-7,
        abs_tol: float = 1e-7,
    ) -> None:
        self.rel_tol = float(rel_tol)
        self.abs_tol = float(abs_tol)

    def verify_parity(
        self,
        *,
        factor_factory: Callable[[Any], Factor],
        store: Any,
        universe: Sequence[str],
        decision_times: Sequence[datetime],
        truncated_store_factory: Callable[[Any, datetime], Any] | None = None,
        raise_on_mismatch: bool = True,
    ) -> ParityResult:
        if not decision_times:
            raise ParityError("decision_times must be non-empty")
        d_times = tuple(_require_utc(t, field="decision_time") for t in decision_times)

        for i in range(1, len(d_times)):
            if d_times[i] <= d_times[i - 1]:
                raise ParityError(
                    "decision_times must be strictly increasing UTC datetimes",
                    context={
                        "index": i,
                        "prev": d_times[i - 1].isoformat(),
                        "curr": d_times[i].isoformat(),
                    },
                )

        batch_factor = factor_factory(store)
        factor_id = batch_factor.factor_id
        factor_version = batch_factor.factor_version

        comparisons: list[ParityComparison] = []

        for dt in d_times:
            batch_frame = batch_factor.compute(universe, dt)

            if truncated_store_factory is not None:
                serving_store = truncated_store_factory(store, dt)
            else:
                serving_store = TruncatedAsOfStoreAdapter(
                    store, max_availability_time=dt
                )

            serving_factor = factor_factory(serving_store)
            evaluator = ServingFactorEvaluator(serving_factor)
            serving_frame = evaluator.evaluate_daily(universe, dt)

            is_eq, diffs = compare_factor_frames(
                batch_frame,
                serving_frame,
                rel_tol=self.rel_tol,
                abs_tol=self.abs_tol,
            )

            comparison = ParityComparison(
                decision_time=dt,
                batch_frame=batch_frame,
                serving_frame=serving_frame,
                is_equal=is_eq,
                diffs=diffs,
            )
            comparisons.append(comparison)

        result = ParityResult(
            factor_id=factor_id,
            factor_version=factor_version,
            decision_times=d_times,
            comparisons=tuple(comparisons),
        )

        if raise_on_mismatch and not result.is_parity_satisfied:
            mismatches = [c for c in result.comparisons if not c.is_equal]
            err_msg = (
                f"Parity mismatch detected for factor {factor_id!r} "
                f"at {len(mismatches)}/{len(d_times)} decision times: "
                f"{mismatches[0].diffs}"
            )
            raise ParityError(err_msg, context={"factor_id": factor_id})

        return result
