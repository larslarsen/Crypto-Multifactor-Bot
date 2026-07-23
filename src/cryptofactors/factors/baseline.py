"""BASE-001 — transparent factor baselines (experiment #19).

Preregistered order: momentum, mean-reversion, volume. Each factor is a fixed
formula over as-of market history (no tuning). Scores are deterministic given
``(universe, as_of, window, dataset bindings)``.

History windows are built from **N distinct as-of observations** (keyed by
``period_start``), not calendar-day offsets, so missing bars do not duplicate
stale rows.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

from cryptofactors.factors.contract import FactorFrame, FactorValue

DEFAULT_WINDOW: int = 20
DEFAULT_PRICE_FIELD: str = "close"
DEFAULT_VOLUME_FIELD: str = "base_volume"
BASELINE_FACTOR_ORDER: tuple[str, ...] = (
    "momentum",
    "mean_reversion",
    "volume",
)

MOMENTUM_FACTOR_ID: str = "momentum"
MEAN_REVERSION_FACTOR_ID: str = "mean_reversion"
VOLUME_FACTOR_ID: str = "volume"
BASELINE_FACTOR_VERSION: str = "1"

_US_PER_SECOND: int = 1_000_000


class BaselineFactorError(RuntimeError):
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
    """Structural as-of surface used by baseline factors (catalog AsOfStore)."""

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
        raise BaselineFactorError(
            f"{field} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise BaselineFactorError(
            f"{field} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


def _require_window(window: int) -> int:
    if not isinstance(window, int) or isinstance(window, bool):
        raise BaselineFactorError(
            "window must be int",
            context={"type": type(window).__name__},
        )
    if window < 2:
        raise BaselineFactorError(
            "window must be >= 2",
            context={"window": window},
        )
    return window


def _normalize_universe(universe: Sequence[str]) -> tuple[str, ...]:
    if universe is None:
        raise BaselineFactorError("universe must not be None")
    if isinstance(universe, (str, bytes, bytearray)):
        raise BaselineFactorError(
            "universe must be a sequence of instrument ids, not str/bytes",
            context={"type": type(universe).__name__},
        )
    ids: list[str] = []
    for item in universe:
        if not isinstance(item, str):
            raise BaselineFactorError(
                "universe entries must be str",
                context={"type": type(item).__name__},
            )
        text = item.strip()
        if not text:
            raise BaselineFactorError("universe entries must be non-empty strings")
        ids.append(text)
    if not ids:
        raise BaselineFactorError("universe must be non-empty")
    return tuple(sorted(set(ids)))


def _asof_key(instrument_id: str) -> int | str:
    try:
        return int(instrument_id)
    except ValueError:
        return instrument_id


def _us_to_dt(us: int) -> datetime:
    return datetime.fromtimestamp(us / _US_PER_SECOND, tz=timezone.utc)


def _parse_us(raw: object, *, field: str, instrument_id: str) -> int:
    if raw is None:
        raise BaselineFactorError(
            f"as-of {field} is null",
            context={"instrument_id": instrument_id},
        )
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        raise BaselineFactorError(
            f"as-of {field} is not an integer timestamp",
            context={"instrument_id": instrument_id, "value": repr(raw)},
        )
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BaselineFactorError(
            f"as-of {field} is not an integer timestamp",
            context={"instrument_id": instrument_id, "value": repr(raw)},
        ) from exc


def _validate_numeric(
    value: float,
    *,
    field: str,
    instrument_id: str,
    role: str,
) -> float:
    if not math.isfinite(value):
        raise BaselineFactorError(
            f"as-of field {field!r} is non-finite",
            context={"instrument_id": instrument_id, "value": value},
        )
    if role == "price":
        if value <= 0.0:
            raise BaselineFactorError(
                f"price field {field!r} must be > 0",
                context={"instrument_id": instrument_id, "value": value},
            )
    elif role == "volume":
        if value < 0.0:
            raise BaselineFactorError(
                f"volume field {field!r} must be >= 0",
                context={"instrument_id": instrument_id, "value": value},
            )
    else:
        raise BaselineFactorError(
            "unknown field role",
            context={"role": role},
        )
    return value


def _field_float(
    table: object,
    field: str,
    *,
    instrument_id: str,
) -> float:
    num_rows = getattr(table, "num_rows", None)
    if num_rows is None:
        raise BaselineFactorError(
            "as-of result is not a table",
            context={"type": type(table).__name__},
        )
    if int(num_rows) == 0:
        raise BaselineFactorError(
            "insufficient as-of market data",
            context={"instrument_id": instrument_id, "field": field},
        )
    names = list(getattr(table, "column_names", []))
    if field not in names:
        raise BaselineFactorError(
            f"as-of table missing field {field!r}",
            context={"columns": names, "instrument_id": instrument_id},
        )
    raw = table.column(field)[0].as_py()  # type: ignore[attr-defined]
    if raw is None:
        raise BaselineFactorError(
            f"as-of field {field!r} is null",
            context={"instrument_id": instrument_id},
        )
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise BaselineFactorError(
            f"as-of field {field!r} is not numeric",
            context={"instrument_id": instrument_id, "value": repr(raw)},
        ) from exc


def _latest_observation(
    store: AsOfMarketAccess,
    *,
    dataset_id: str,
    instrument_id: str,
    field: str,
    as_of: datetime,
    role: str,
) -> tuple[float, int, int]:
    """Return ``(value, availability_time_us, period_start_us)`` at ``as_of``."""
    fields = ["instrument_id", field, "availability_time", "period_start"]
    try:
        table = store.latest_available(
            dataset_id,
            [_asof_key(instrument_id)],
            fields,
            as_of,
            None,
        )
    except BaselineFactorError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise BaselineFactorError(
            "as-of latest_available failed",
            context={
                "instrument_id": instrument_id,
                "dataset_id": dataset_id,
                "as_of": as_of.isoformat(),
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        ) from exc

    value = _validate_numeric(
        _field_float(table, field, instrument_id=instrument_id),
        field=field,
        instrument_id=instrument_id,
        role=role,
    )
    names = list(getattr(table, "column_names", []))
    if "availability_time" not in names:
        raise BaselineFactorError(
            "as-of table missing availability_time",
            context={"columns": names, "instrument_id": instrument_id},
        )
    if "period_start" not in names:
        raise BaselineFactorError(
            "as-of table missing period_start",
            context={"columns": names, "instrument_id": instrument_id},
        )
    avail_us = _parse_us(
        table.column("availability_time")[0].as_py(),  # type: ignore[attr-defined]
        field="availability_time",
        instrument_id=instrument_id,
    )
    period_start_us = _parse_us(
        table.column("period_start")[0].as_py(),  # type: ignore[attr-defined]
        field="period_start",
        instrument_id=instrument_id,
    )
    return value, avail_us, period_start_us


def _history_series(
    store: AsOfMarketAccess,
    *,
    dataset_id: str,
    instrument_id: str,
    field: str,
    as_of: datetime,
    window: int,
    role: str,
) -> list[float]:
    """Collect ``window`` distinct observations ending at ``as_of`` (oldest first).

    After each hit, rewinds to ``availability_time - 1µs`` so the same bar cannot
    be re-selected. Production BAR-001 sets ``availability_time = period_end``
    (next interval open); rewinding on ``period_start`` would place the cursor
    before the preceding bar's availability and skip valid observations.
    Distinctness is still enforced via ``period_start``.
    """
    newest_first: list[float] = []
    seen_period_starts: set[int] = set()
    cursor = as_of
    for _ in range(window):
        value, avail_us, period_start_us = _latest_observation(
            store,
            dataset_id=dataset_id,
            instrument_id=instrument_id,
            field=field,
            as_of=cursor,
            role=role,
        )
        if period_start_us in seen_period_starts:
            raise BaselineFactorError(
                "duplicate observation period_start in history walk",
                context={
                    "instrument_id": instrument_id,
                    "period_start_us": period_start_us,
                    "availability_time_us": avail_us,
                    "as_of": cursor.isoformat(),
                },
            )
        seen_period_starts.add(period_start_us)
        newest_first.append(value)
        cursor = _us_to_dt(avail_us - 1)
    newest_first.reverse()
    return newest_first


class _BaselineBase:
    factor_version: str = BASELINE_FACTOR_VERSION

    def __init__(
        self,
        as_of_store: AsOfMarketAccess,
        *,
        window: int = DEFAULT_WINDOW,
        market_dataset_id: str,
        price_field: str = DEFAULT_PRICE_FIELD,
        volume_field: str = DEFAULT_VOLUME_FIELD,
    ) -> None:
        if as_of_store is None:
            raise BaselineFactorError("as_of_store must not be None")
        ds = market_dataset_id.strip()
        if not ds:
            raise BaselineFactorError("market_dataset_id must be non-empty")
        pf = price_field.strip()
        if not pf:
            raise BaselineFactorError("price_field must be non-empty")
        vf = volume_field.strip()
        if not vf:
            raise BaselineFactorError("volume_field must be non-empty")
        self._store: AsOfMarketAccess = as_of_store
        self._window: int = _require_window(window)
        self._market_dataset_id: str = ds
        self._price_field: str = pf
        self._volume_field: str = vf

    @property
    def window(self) -> int:
        return self._window

    @property
    def market_dataset_id(self) -> str:
        return self._market_dataset_id


class MomentumFactor(_BaselineBase):
    """Trailing return over ``window`` observation steps: ``P_last / P_first - 1``."""

    factor_id: str = MOMENTUM_FACTOR_ID

    def compute(
        self,
        universe: Sequence[str],
        as_of: datetime,
    ) -> FactorFrame:
        decision_time = _require_utc(as_of, field="as_of")
        ordered = _normalize_universe(universe)
        values: list[FactorValue] = []
        # window steps ⇒ window+1 distinct prices (first → last).
        n_obs = self._window + 1
        for instrument_id in ordered:
            series = _history_series(
                self._store,
                dataset_id=self._market_dataset_id,
                instrument_id=instrument_id,
                field=self._price_field,
                as_of=decision_time,
                window=n_obs,
                role="price",
            )
            p_then = series[0]
            p_now = series[-1]
            raw = (p_now / p_then) - 1.0
            values.append(
                FactorValue(
                    instrument_id=instrument_id,
                    decision_time=decision_time,
                    raw_value=raw,
                    score=raw,
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


class MeanReversionFactor(_BaselineBase):
    """Z-score of price vs rolling N distinct obs mean/std; score = ``-z``."""

    factor_id: str = MEAN_REVERSION_FACTOR_ID

    def compute(
        self,
        universe: Sequence[str],
        as_of: datetime,
    ) -> FactorFrame:
        decision_time = _require_utc(as_of, field="as_of")
        ordered = _normalize_universe(universe)
        values: list[FactorValue] = []
        for instrument_id in ordered:
            series = _history_series(
                self._store,
                dataset_id=self._market_dataset_id,
                instrument_id=instrument_id,
                field=self._price_field,
                as_of=decision_time,
                window=self._window,
                role="price",
            )
            mean = statistics.fmean(series)
            stdev = statistics.pstdev(series)
            if stdev == 0.0:
                raise BaselineFactorError(
                    "rolling price stdev is zero",
                    context={"instrument_id": instrument_id, "window": self._window},
                )
            z = (series[-1] - mean) / stdev
            score = -z
            values.append(
                FactorValue(
                    instrument_id=instrument_id,
                    decision_time=decision_time,
                    raw_value=z,
                    score=score,
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


class VolumeFactor(_BaselineBase):
    """Volume ratio over N distinct obs: ``V_last / mean(V)``."""

    factor_id: str = VOLUME_FACTOR_ID

    def compute(
        self,
        universe: Sequence[str],
        as_of: datetime,
    ) -> FactorFrame:
        decision_time = _require_utc(as_of, field="as_of")
        ordered = _normalize_universe(universe)
        values: list[FactorValue] = []
        for instrument_id in ordered:
            series = _history_series(
                self._store,
                dataset_id=self._market_dataset_id,
                instrument_id=instrument_id,
                field=self._volume_field,
                as_of=decision_time,
                window=self._window,
                role="volume",
            )
            mean_vol = statistics.fmean(series)
            if mean_vol <= 0.0:
                raise BaselineFactorError(
                    "rolling mean volume must be > 0",
                    context={"instrument_id": instrument_id, "mean_volume": mean_vol},
                )
            raw = series[-1] / mean_vol
            values.append(
                FactorValue(
                    instrument_id=instrument_id,
                    decision_time=decision_time,
                    raw_value=raw,
                    score=raw,
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
