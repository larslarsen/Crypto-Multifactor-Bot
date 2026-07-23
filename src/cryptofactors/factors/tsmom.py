"""MOMTS-001 — Time-series momentum factor (MOM-TS-01).

Skip-window log-return signals over calendar-day lookbacks:
- ``tsmom_30_7 = log(P[t-7d] / P[t-30d])``
- ``tsmom_90_7 = log(P[t-7d] / P[t-90d])``

The signal uses prices ending 7 days before the decision time (skip window),
so the most recent 7 days of price action are excluded from the signal. This is
distinct from the cross-sectional ``MomentumFactor`` (MOM-01) in ``baseline.py``:
MOM-TS-01 is an own-asset log-return with an explicit gap, not a cross-sectional
rank over a trailing window of distinct bars.

Missing history → missing (the instrument is omitted from the frame). An exactly
zero signal is flat (score 0.0 = cash), never imputed.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

from cryptofactors.factors.contract import FactorFrame, FactorValue

DEFAULT_PRICE_FIELD: str = "close"
TSMOM_FACTOR_VERSION: str = "1"
TSMOM_30_7_FACTOR_ID: str = "tsmom_30_7"
TSMOM_90_7_FACTOR_ID: str = "tsmom_90_7"

_US_PER_SECOND: int = 1_000_000


class TSMOMError(RuntimeError):
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


@runtime_checkable
class AsOfMarketAccess(Protocol):
    """Structural as-of surface used by TSMOM factors (catalog AsOfStore)."""

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> object: ...


def _require_utc(dt: datetime, *, field: str) -> datetime:
    if not isinstance(dt, datetime):
        raise TSMOMError(
            f"{field} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise TSMOMError(
            f"{field} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


def _normalize_universe(universe: Sequence[str]) -> tuple[str, ...]:
    if universe is None:
        raise TSMOMError("universe must not be None")
    if isinstance(universe, (str, bytes, bytearray)):
        raise TSMOMError(
            "universe must be a sequence of instrument ids, not str/bytes",
            context={"type": type(universe).__name__},
        )
    ids: list[str] = []
    for item in universe:
        if not isinstance(item, str):
            raise TSMOMError(
                "universe entries must be str",
                context={"type": type(item).__name__},
            )
        text = item.strip()
        if not text:
            raise TSMOMError("universe entries must be non-empty strings")
        ids.append(text)
    if not ids:
        raise TSMOMError("universe must be non-empty")
    return tuple(sorted(set(ids)))


def _asof_key(instrument_id: str) -> int | str:
    try:
        return int(instrument_id)
    except ValueError:
        return instrument_id


def _parse_us(raw: object, *, field: str, instrument_id: str) -> int:
    if raw is None:
        raise TSMOMError(
            f"as-of {field} is null",
            context={"instrument_id": instrument_id},
        )
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        raise TSMOMError(
            f"as-of {field} is not an integer timestamp",
            context={"instrument_id": instrument_id, "value": repr(raw)},
        )
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise TSMOMError(
            f"as-of {field} is not an integer timestamp",
            context={"instrument_id": instrument_id, "value": repr(raw)},
        ) from exc


def _field_float(
    table: object,
    field: str,
    *,
    instrument_id: str,
) -> float:
    num_rows = getattr(table, "num_rows", None)
    if num_rows is None:
        raise TSMOMError(
            "as-of result is not a table",
            context={"type": type(table).__name__},
        )
    if int(num_rows) == 0:
        raise TSMOMError(
            "insufficient as-of market data",
            context={"instrument_id": instrument_id, "field": field},
        )
    names = list(getattr(table, "column_names", []))
    if field not in names:
        raise TSMOMError(
            f"as-of table missing field {field!r}",
            context={"columns": names, "instrument_id": instrument_id},
        )
    raw = table.column(field)[0].as_py()  # type: ignore[attr-defined]
    if raw is None:
        raise TSMOMError(
            f"as-of field {field!r} is null",
            context={"instrument_id": instrument_id},
        )
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise TSMOMError(
            f"as-of field {field!r} is not numeric",
            context={"instrument_id": instrument_id, "value": repr(raw)},
        ) from exc


def _price_at(
    store: AsOfMarketAccess,
    *,
    dataset_id: str,
    instrument_id: str,
    field: str,
    as_of: datetime,
) -> float:
    """Return the latest available price at ``as_of`` for ``instrument_id``.

    Raises ``TSMOMError`` if the as-of store returns malformed/empty data so the
    caller can treat it as missing history rather than silently imputing a value.
    """
    fields = ["instrument_id", field, "availability_time", "period_start"]
    try:
        table = store.latest_available(
            dataset_id,
            [_asof_key(instrument_id)],
            fields,
            as_of,
            None,
        )
    except TSMOMError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TSMOMError(
            "as-of latest_available failed",
            context={
                "instrument_id": instrument_id,
                "dataset_id": dataset_id,
                "as_of": as_of.isoformat(),
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        ) from exc

    value = _field_float(table, field, instrument_id=instrument_id)
    if not math.isfinite(value) or value <= 0.0:
        raise TSMOMError(
            f"price field {field!r} must be finite and > 0",
            context={"instrument_id": instrument_id, "value": value},
        )
    return value


def _try_price_at(
    store: AsOfMarketAccess,
    *,
    dataset_id: str,
    instrument_id: str,
    field: str,
    as_of: datetime,
) -> float | None:
    """Like ``_price_at`` but returns ``None`` on missing/insufficient history."""
    try:
        return _price_at(
            store,
            dataset_id=dataset_id,
            instrument_id=instrument_id,
            field=field,
            as_of=as_of,
        )
    except TSMOMError:
        return None


class TimeSeriesMomentumFactor:
    """Skip-window log-return time-series momentum factor (MOM-TS-01).

    Signal: ``log(P[t - skip] / P[t - lookback])`` where ``lookback > skip`` and
    both are calendar-day offsets. The skip window excludes the most recent
    ``skip`` days of price action from the signal.

    Missing history for either endpoint omits the instrument from the frame
    (never imputed). An exactly zero signal yields a flat score (0.0 = cash).
    """

    factor_version: str = TSMOM_FACTOR_VERSION

    def __init__(
        self,
        as_of_store: AsOfMarketAccess,
        *,
        lookback_days: int,
        skip_days: int,
        market_dataset_id: str,
        price_field: str = DEFAULT_PRICE_FIELD,
        factor_id: str | None = None,
    ) -> None:
        if as_of_store is None:
            raise TSMOMError("as_of_store must not be None")
        if not isinstance(lookback_days, int) or isinstance(lookback_days, bool):
            raise TSMOMError("lookback_days must be int")
        if not isinstance(skip_days, int) or isinstance(skip_days, bool):
            raise TSMOMError("skip_days must be int")
        if skip_days < 0:
            raise TSMOMError("skip_days must be >= 0", context={"skip_days": skip_days})
        if lookback_days <= skip_days:
            raise TSMOMError(
                "lookback_days must be > skip_days",
                context={"lookback_days": lookback_days, "skip_days": skip_days},
            )
        ds = market_dataset_id.strip()
        if not ds:
            raise TSMOMError("market_dataset_id must be non-empty")
        pf = price_field.strip()
        if not pf:
            raise TSMOMError("price_field must be non-empty")

        if factor_id is not None:
            fid = factor_id.strip()
            if not fid:
                raise TSMOMError("factor_id must be non-empty when provided")
        else:
            fid = f"tsmom_{lookback_days}_{skip_days}"

        self._store: AsOfMarketAccess = as_of_store
        self._lookback_days: int = lookback_days
        self._skip_days: int = skip_days
        self._market_dataset_id: str = ds
        self._price_field: str = pf
        self._factor_id: str = fid

    @property
    def factor_id(self) -> str:
        return self._factor_id

    @property
    def lookback_days(self) -> int:
        return self._lookback_days

    @property
    def skip_days(self) -> int:
        return self._skip_days

    @property
    def market_dataset_id(self) -> str:
        return self._market_dataset_id

    def compute(
        self,
        universe: Sequence[str],
        as_of: datetime,
    ) -> FactorFrame:
        decision_time = _require_utc(as_of, field="as_of")
        ordered = _normalize_universe(universe)

        recent_time = decision_time - timedelta(days=self._skip_days)
        far_time = decision_time - timedelta(days=self._lookback_days)

        values: list[FactorValue] = []
        for instrument_id in ordered:
            p_recent = _try_price_at(
                self._store,
                dataset_id=self._market_dataset_id,
                instrument_id=instrument_id,
                field=self._price_field,
                as_of=recent_time,
            )
            p_far = _try_price_at(
                self._store,
                dataset_id=self._market_dataset_id,
                instrument_id=instrument_id,
                field=self._price_field,
                as_of=far_time,
            )

            if p_recent is None or p_far is None:
                continue

            raw = math.log(p_recent / p_far)
            score = raw if raw != 0.0 else 0.0
            values.append(
                FactorValue(
                    instrument_id=instrument_id,
                    decision_time=decision_time,
                    raw_value=raw,
                    score=score,
                    availability_time=decision_time,
                    factor_id=self._factor_id,
                    factor_version=self.factor_version,
                )
            )

        return FactorFrame(
            values=tuple(values),
            factor_id=self._factor_id,
            factor_version=self.factor_version,
            decision_time=decision_time,
        )


def make_tsmom_30_7(
    as_of_store: AsOfMarketAccess,
    *,
    market_dataset_id: str,
    price_field: str = DEFAULT_PRICE_FIELD,
) -> TimeSeriesMomentumFactor:
    """Construct the registered ``tsmom_30_7`` factor (EXP-2026-019)."""
    return TimeSeriesMomentumFactor(
        as_of_store,
        lookback_days=30,
        skip_days=7,
        market_dataset_id=market_dataset_id,
        price_field=price_field,
        factor_id=TSMOM_30_7_FACTOR_ID,
    )


def make_tsmom_90_7(
    as_of_store: AsOfMarketAccess,
    *,
    market_dataset_id: str,
    price_field: str = DEFAULT_PRICE_FIELD,
) -> TimeSeriesMomentumFactor:
    """Construct the registered ``tsmom_90_7`` factor (EXP-2026-020)."""
    return TimeSeriesMomentumFactor(
        as_of_store,
        lookback_days=90,
        skip_days=7,
        market_dataset_id=market_dataset_id,
        price_field=price_field,
        factor_id=TSMOM_90_7_FACTOR_ID,
    )