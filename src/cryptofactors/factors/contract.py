"""Factor layer contracts (neutral; shared by all factor implementations)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class FactorValue:
    instrument_id: str
    decision_time: datetime
    raw_value: float
    score: float
    availability_time: datetime
    factor_id: str
    factor_version: str


@dataclass(frozen=True, slots=True)
class FactorFrame:
    values: tuple[FactorValue, ...]
    factor_id: str
    factor_version: str
    decision_time: datetime


@runtime_checkable
class Factor(Protocol):
    factor_id: str
    factor_version: str

    def compute(
        self,
        universe: Sequence[str],
        as_of: datetime,
    ) -> FactorFrame: ...
