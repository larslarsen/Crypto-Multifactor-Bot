"""COMP-001 — equal-weight cross-sectional rank composite factor.

Combines multiple child factors into one score by averaging per-instrument
cross-sectional ranks (rank 1 = best / highest child score).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from datetime import datetime, timezone

from cryptofactors.factors.contract import Factor, FactorFrame, FactorValue

COMPOSITE_EQUAL_RANK_FACTOR_ID: str = "composite_equal_rank"
COMPOSITE_FACTOR_VERSION: str = "1"


class CompositeFactorError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.context: dict[str, object] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


def _require_utc(dt: datetime, *, field: str) -> datetime:
    if not isinstance(dt, datetime):
        raise CompositeFactorError(
            f"{field} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise CompositeFactorError(
            f"{field} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


def _normalize_universe(universe: Sequence[str]) -> tuple[str, ...]:
    if universe is None:
        raise CompositeFactorError("universe must not be None")
    if isinstance(universe, (str, bytes, bytearray)):
        raise CompositeFactorError(
            "universe must be a sequence of instrument ids, not str/bytes",
            context={"type": type(universe).__name__},
        )
    ids: list[str] = []
    for item in universe:
        if not isinstance(item, str):
            raise CompositeFactorError(
                "universe entries must be str",
                context={"type": type(item).__name__},
            )
        text = item.strip()
        if not text:
            raise CompositeFactorError("universe entries must be non-empty strings")
        ids.append(text)
    if not ids:
        raise CompositeFactorError("universe must be non-empty")
    return tuple(sorted(set(ids)))


def _cross_sectional_ranks(scores: dict[str, float]) -> dict[str, float]:
    """Rank instruments by score descending (1 = best). Ties get average rank."""
    if not scores:
        return {}
    # Sort by score desc, then instrument_id for deterministic tie grouping order.
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    ranks: dict[str, float] = {}
    i = 0
    n = len(ordered)
    while i < n:
        j = i + 1
        while j < n and ordered[j][1] == ordered[i][1]:
            j += 1
        # 1-based positions i+1 .. j
        avg_rank = statistics.fmean(range(i + 1, j + 1))
        for k in range(i, j):
            ranks[ordered[k][0]] = float(avg_rank)
        i = j
    return ranks


class EqualWeightRankComposite:
    """Average cross-sectional ranks across child factors (higher score = better).

    ``score = -avg_rank`` so the best instrument (rank 1) gets the highest
    score (``-1``), consistent with the descending-sort portfolio convention.
    ``raw_value`` remains the plain average rank.
    """

    factor_id: str = COMPOSITE_EQUAL_RANK_FACTOR_ID
    factor_version: str = COMPOSITE_FACTOR_VERSION

    def __init__(self, factors: Sequence[Factor]) -> None:
        if factors is None:
            raise CompositeFactorError("factors must not be None")
        if isinstance(factors, (str, bytes, bytearray)):
            raise CompositeFactorError(
                "factors must be a sequence of Factor implementations",
                context={"type": type(factors).__name__},
            )
        children: list[Factor] = []
        seen_ids: set[str] = set()
        for item in factors:
            if not isinstance(item, Factor):
                raise CompositeFactorError(
                    "each child must implement Factor",
                    context={"type": type(item).__name__},
                )
            fid = item.factor_id
            if fid in seen_ids:
                raise CompositeFactorError(
                    "duplicate child factor_id",
                    context={"factor_id": fid},
                )
            seen_ids.add(fid)
            children.append(item)
        if not children:
            raise CompositeFactorError("factors must be non-empty")
        self._factors: tuple[Factor, ...] = tuple(children)

    @property
    def factors(self) -> tuple[Factor, ...]:
        return self._factors

    def compute(
        self,
        universe: Sequence[str],
        as_of: datetime,
    ) -> FactorFrame:
        decision_time = _require_utc(as_of, field="as_of")
        ordered = _normalize_universe(universe)

        # instrument_id -> list of ranks from child factors that covered it
        rank_lists: dict[str, list[float]] = {iid: [] for iid in ordered}

        for child in self._factors:
            frame = child.compute(ordered, decision_time)
            if frame is None:
                raise CompositeFactorError(
                    "child factor returned None",
                    context={"factor_id": getattr(child, "factor_id", None)},
                )
            scores: dict[str, float] = {}
            for value in frame.values:
                iid = value.instrument_id
                if iid not in rank_lists:
                    continue
                score = float(value.score)
                if not math.isfinite(score):
                    raise CompositeFactorError(
                        "child factor score is non-finite",
                        context={
                            "factor_id": frame.factor_id,
                            "instrument_id": iid,
                            "score": score,
                        },
                    )
                scores[iid] = score
            ranks = _cross_sectional_ranks(scores)
            for iid, rank in ranks.items():
                rank_lists[iid].append(rank)

        values: list[FactorValue] = []
        for instrument_id in ordered:
            parts = rank_lists[instrument_id]
            if not parts:
                # Missing from every child factor — omit (fail-soft per instrument).
                continue
            avg_rank = float(statistics.fmean(parts))
            values.append(
                FactorValue(
                    instrument_id=instrument_id,
                    decision_time=decision_time,
                    raw_value=avg_rank,
                    score=-avg_rank,
                    availability_time=decision_time,
                    factor_id=self.factor_id,
                    factor_version=self.factor_version,
                )
            )

        return FactorFrame(
            values=tuple(values),
            factor_id=self.factor_id,
            factor_version=self.factor_version,
            decision_time=decision_time,
        )
