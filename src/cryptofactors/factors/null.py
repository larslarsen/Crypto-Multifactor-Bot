"""NULL-001 — null / noise factor for experiment #18.

Produces pure random noise scores with no predictive content so the research
substrate can be validated against a known zero-edge baseline.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from random import Random

from cryptofactors.factors.contract import FactorFrame, FactorValue

NULL_FACTOR_ID: str = "null"
NULL_FACTOR_VERSION: str = "1"


class NullFactorError(RuntimeError):
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
        raise NullFactorError(
            f"{field} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise NullFactorError(
            f"{field} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


def _unit_normal(*, seed: int, instrument_id: str, as_of_key: str) -> float:
    rng = Random()
    rng.seed(f"{seed}|{instrument_id}|{as_of_key}", version=2)
    return rng.gauss(0.0, 1.0)


class NullFactor:
    """Pure-noise factor: scores are i.i.d. unit normal, independent of returns.

    Scores are seeded per ``(seed, instrument_id, as_of)`` so values are stable
    under universe membership changes (universe-stable point-in-time scores).
    """

    factor_id: str = NULL_FACTOR_ID
    factor_version: str = NULL_FACTOR_VERSION

    def __init__(self, *, seed: int = 0) -> None:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise NullFactorError(
                "seed must be int",
                context={"type": type(seed).__name__},
            )
        self._seed: int = seed

    @property
    def seed(self) -> int:
        return self._seed

    def compute(
        self,
        universe: Sequence[str],
        as_of: datetime,
    ) -> FactorFrame:
        decision_time = _require_utc(as_of, field="as_of")
        if universe is None:
            raise NullFactorError("universe must not be None")
        if isinstance(universe, (str, bytes, bytearray)):
            raise NullFactorError(
                "universe must be a sequence of instrument ids, not str/bytes",
                context={"type": type(universe).__name__},
            )
        ids: list[str] = []
        for item in universe:
            if not isinstance(item, str):
                raise NullFactorError(
                    "universe entries must be str",
                    context={"type": type(item).__name__},
                )
            text = item.strip()
            if not text:
                raise NullFactorError("universe entries must be non-empty strings")
            ids.append(text)
        if not ids:
            raise NullFactorError("universe must be non-empty")
        ordered = tuple(sorted(set(ids)))
        as_of_key = decision_time.isoformat()
        values: list[FactorValue] = []
        for instrument_id in ordered:
            noise = _unit_normal(
                seed=self._seed,
                instrument_id=instrument_id,
                as_of_key=as_of_key,
            )
            values.append(
                FactorValue(
                    instrument_id=instrument_id,
                    decision_time=decision_time,
                    raw_value=noise,
                    score=noise,
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
