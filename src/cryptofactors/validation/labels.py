"""LABEL-001 — label / event-interval separation engine.

Produces deterministic labeled decision events with explicit
``[event_start, event_end)`` windows strictly separated from feature time.
Entry prices use AsOfStore observations with ``availability_time <= decision_time``.
Exit prices use as-of access at ``event_end`` for label realization only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from cryptofactors.validation.split import AsOfDataAccess, EventInterval


def _require_utc(dt: datetime, *, field: str) -> datetime:
    if not isinstance(dt, datetime):
        raise LabelError(f"{field} must be a datetime", context={"type": type(dt).__name__})
    if dt.tzinfo is None:
        raise LabelError(
            f"{field} must be timezone-aware UTC", context={"value": str(dt)}
        )
    return dt.astimezone(timezone.utc)


class LabelError(RuntimeError):
    """Fail-closed label construction error."""

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


class LabelType(StrEnum):
    """Supported label constructions (LABEL-001)."""

    FORWARD_RETURN = "forward_return"
    SIGN = "sign"
    BINARY = "binary"


@dataclass(frozen=True, slots=True)
class DecisionEvent:
    """One labeled decision with explicit event interval (SPLIT-001 compatible).

    Separation: ``event_start >= decision_time + min_gap`` so the label window does
    not overlap the feature observation window ending at ``decision_time``.
    """

    instrument_id: str | int
    decision_time: datetime
    event_start: datetime
    event_end: datetime
    label_type: LabelType
    label_value: Decimal
    label_direction: int
    entry_price: Decimal
    exit_price: Decimal
    event_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "decision_time", _require_utc(self.decision_time, field="decision_time")
        )
        object.__setattr__(
            self, "event_start", _require_utc(self.event_start, field="event_start")
        )
        object.__setattr__(
            self, "event_end", _require_utc(self.event_end, field="event_end")
        )
        if self.event_end <= self.event_start:
            raise LabelError(
                "event_end must be > event_start",
                context={
                    "event_start": self.event_start.isoformat(),
                    "event_end": self.event_end.isoformat(),
                },
            )
        if self.event_start < self.decision_time:
            raise LabelError(
                "event_start must be >= decision_time (label/feature separation)",
                context={
                    "decision_time": self.decision_time.isoformat(),
                    "event_start": self.event_start.isoformat(),
                },
            )
        if self.label_direction not in (-1, 0, 1):
            raise LabelError(
                "label_direction must be -1, 0, or 1",
                context={"label_direction": self.label_direction},
            )

    def to_event_interval(self) -> EventInterval:
        """Convert to SPLIT-001 ``EventInterval`` for purged split construction."""
        return EventInterval(
            instrument_id=self.instrument_id,
            decision_time=self.decision_time,
            event_start=self.event_start,
            event_end=self.event_end,
            event_id=self.event_id,
        )


@dataclass(frozen=True, slots=True)
class LabelConfig:
    """Configuration for label generation."""

    horizon: timedelta
    label_type: LabelType
    min_gap: timedelta = timedelta(0)
    binary_threshold: Decimal = Decimal("0")
    price_field: str = "close"
    market_dataset_id: str = ""
    # Optional REF eligibility dataset (same as SPLIT-001 defaults).
    instrument_dataset_id: str = "ref_instrument_version"
    require_instrument_eligibility: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.label_type, LabelType):
            object.__setattr__(self, "label_type", LabelType(str(self.label_type)))
        if self.horizon.total_seconds() <= 0:
            raise LabelError("horizon must be positive")
        if self.min_gap.total_seconds() < 0:
            raise LabelError("min_gap must be non-negative")
        if not isinstance(self.binary_threshold, Decimal):
            raise LabelError(
                "binary_threshold must be Decimal",
                context={"type": type(self.binary_threshold).__name__},
            )
        if not self.price_field.strip():
            raise LabelError("price_field must be non-empty")
        if not self.market_dataset_id.strip():
            raise LabelError("market_dataset_id must be non-empty")


@runtime_checkable
class LabelEngine(Protocol):
    """LABEL-001 label / event-interval separation engine."""

    label_version: str

    def compute(
        self,
        instruments: Sequence[str | int],
        decision_times: Sequence[datetime],
        config: LabelConfig,
    ) -> list[DecisionEvent]: ...


def _to_decimal(value: Any, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise LabelError(f"{field}: boolean is not a price", context={"value": repr(value)})
    if isinstance(value, Decimal):
        dec = value
    elif isinstance(value, int):
        dec = Decimal(value)
    elif isinstance(value, float):
        # Arrow may yield float64; convert via str for stability (fail on non-finite).
        if value != value or value in (float("inf"), float("-inf")):
            raise LabelError(f"{field}: non-finite float price", context={"value": value})
        dec = Decimal(str(value))
    elif isinstance(value, str):
        try:
            dec = Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise LabelError(
                f"{field}: invalid Decimal string",
                context={"value": value},
            ) from exc
    else:
        raise LabelError(
            f"{field}: unsupported price type {type(value).__name__}",
            context={"value": repr(value)},
        )
    if not dec.is_finite() or dec <= 0:
        raise LabelError(
            f"{field}: price must be finite and > 0",
            context={"value": str(dec)},
        )
    return dec


class AsOfLabelEngine:
    """Concrete label engine using reviewed as-of access (LABEL-001).

    Parameters
    ----------
    as_of_store:
        Structural AsOfStore (e.g. ``CatalogAsOfStore``).
    """

    label_version: str = "1"

    def __init__(self, as_of_store: AsOfDataAccess) -> None:
        if as_of_store is None:
            raise LabelError("as_of_store is required")
        self._asof = as_of_store

    def compute(
        self,
        instruments: Sequence[str | int],
        decision_times: Sequence[datetime],
        config: LabelConfig,
    ) -> list[DecisionEvent]:
        if not instruments:
            raise LabelError("instruments must be non-empty")
        if not decision_times:
            raise LabelError("decision_times must be non-empty")
        cfg = config if isinstance(config, LabelConfig) else LabelConfig(**dict(config))  # type: ignore[arg-type]

        instruments_u = list(dict.fromkeys(instruments))  # stable unique order
        decisions_u = sorted(
            {_require_utc(d, field="decision_time") for d in decision_times}
        )

        out: list[DecisionEvent] = []
        for decision_time in decisions_u:
            if cfg.require_instrument_eligibility:
                self._assert_instruments_eligible(
                    instruments_u, decision_time, cfg.instrument_dataset_id
                )
            for instrument_id in instruments_u:
                event = self._label_one(instrument_id, decision_time, cfg)
                out.append(event)
        # Deterministic order: decision_time, instrument_id, event_id
        out.sort(
            key=lambda e: (
                e.decision_time,
                str(e.instrument_id),
                e.event_id or "",
            )
        )
        return out

    def _assert_instruments_eligible(
        self,
        instruments: Sequence[str | int],
        decision_time: datetime,
        dataset_id: str,
    ) -> None:
        keys = [str(i) for i in instruments]
        try:
            table = self._asof.as_of(
                dataset_id,
                keys,
                ["instrument_id"],
                decision_time,
                knowledge_time=decision_time,
            )
        except Exception as exc:  # noqa: BLE001
            raise LabelError(
                "as-of instrument eligibility check failed",
                context={
                    "dataset_id": dataset_id,
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
            raise LabelError(
                "instrument not eligible under AsOfStore at decision_time",
                context={
                    "dataset_id": dataset_id,
                    "decision_time": decision_time.isoformat(),
                    "missing_instrument_ids": missing,
                },
            )

    def _price_at(
        self,
        instrument_id: str | int,
        as_of_time: datetime,
        *,
        dataset_id: str,
        price_field: str,
        role: str,
    ) -> Decimal:
        """Latest price available at ``as_of_time`` (availability_time <= as_of_time)."""
        try:
            table = self._asof.latest_available(
                dataset_id,
                [instrument_id],
                ["instrument_id", price_field, "availability_time", "period_start"],
                as_of_time,
                max_age=None,
            )
        except Exception as exc:  # noqa: BLE001
            raise LabelError(
                f"as-of price lookup failed ({role})",
                context={
                    "instrument_id": str(instrument_id),
                    "as_of_time": as_of_time.isoformat(),
                    "dataset_id": dataset_id,
                    "error": str(exc),
                },
            ) from exc
        if table is None or getattr(table, "num_rows", 0) == 0:
            raise LabelError(
                f"insufficient price data for {role}",
                context={
                    "instrument_id": str(instrument_id),
                    "as_of_time": as_of_time.isoformat(),
                    "dataset_id": dataset_id,
                    "price_field": price_field,
                },
            )
        if price_field not in table.column_names:
            raise LabelError(
                f"price field {price_field!r} missing from as-of result",
                context={"columns": list(table.column_names)},
            )
        raw = table.column(price_field)[0].as_py()
        return _to_decimal(raw, field=f"{role}_{price_field}")

    def _label_one(
        self,
        instrument_id: str | int,
        decision_time: datetime,
        cfg: LabelConfig,
    ) -> DecisionEvent:
        event_start = decision_time + cfg.min_gap
        event_end = event_start + cfg.horizon
        # Entry: last price available at decision (feature-safe).
        entry = self._price_at(
            instrument_id,
            decision_time,
            dataset_id=cfg.market_dataset_id,
            price_field=cfg.price_field,
            role="entry",
        )
        # Exit: last price available at event_end (label realization only).
        exit_px = self._price_at(
            instrument_id,
            event_end,
            dataset_id=cfg.market_dataset_id,
            price_field=cfg.price_field,
            role="exit",
        )
        ret = (exit_px / entry) - Decimal("1")
        direction, value = self._encode_label(ret, cfg)
        event_id = (
            f"{instrument_id}|{decision_time.isoformat()}|"
            f"{cfg.label_type.value}|{cfg.horizon.total_seconds():.0f}"
        )
        return DecisionEvent(
            instrument_id=instrument_id,
            decision_time=decision_time,
            event_start=event_start,
            event_end=event_end,
            label_type=cfg.label_type,
            label_value=value,
            label_direction=direction,
            entry_price=entry,
            exit_price=exit_px,
            event_id=event_id,
        )

    @staticmethod
    def _encode_label(
        ret: Decimal, cfg: LabelConfig
    ) -> tuple[int, Decimal]:
        if cfg.label_type is LabelType.FORWARD_RETURN:
            if ret > 0:
                direction = 1
            elif ret < 0:
                direction = -1
            else:
                direction = 0
            return direction, ret
        if cfg.label_type is LabelType.SIGN:
            if ret > 0:
                return 1, Decimal("1")
            if ret < 0:
                return -1, Decimal("-1")
            return 0, Decimal("0")
        if cfg.label_type is LabelType.BINARY:
            if ret > cfg.binary_threshold:
                return 1, Decimal("1")
            return 0, Decimal("0")
        raise LabelError(f"unsupported label_type: {cfg.label_type!r}")
