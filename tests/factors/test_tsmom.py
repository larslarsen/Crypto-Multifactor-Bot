"""MOMTS-001 — Time-series momentum factor (MOM-TS-01) unit tests.

Tests assert the exact 30-7 / 90-7 skip-window log-return formulas on a fixed
synthetic price series, missing-history omission (never imputed to zero), and
exactly-zero signal yielding a flat score.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

import pyarrow as pa
import pytest

from cryptofactors.factors.contract import Factor
from cryptofactors.factors.tsmom import (
    TSMOM_30_7_FACTOR_ID,
    TSMOM_90_7_FACTOR_ID,
    TSMOMError,
    TimeSeriesMomentumFactor,
    make_tsmom_30_7,
    make_tsmom_90_7,
)

UTC = timezone.utc
_DATASET = "ds_tsmom_bars"
_US = 1_000_000


def _ts(day: int) -> datetime:
    return datetime(2020, 1, 1, tzinfo=UTC) + timedelta(days=day)


def _us(dt: datetime) -> int:
    return int(dt.astimezone(UTC).timestamp() * _US)


class _FakeAsOf:
    """As-of fake mimicking BAR-001 timestamps (availability = period_start + 1d)."""

    def __init__(
        self,
        prices: dict[str, list[tuple[datetime, float]]],
    ) -> None:
        self._prices = {
            k: sorted(((t.astimezone(UTC), float(p)) for t, p in v), key=lambda x: x[0])
            for k, v in prices.items()
        }

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> pa.Table:
        empty = pa.table(
            {
                "instrument_id": pa.array([], pa.string()),
                "close": pa.array([], pa.float64()),
                "availability_time": pa.array([], pa.int64()),
                "period_start": pa.array([], pa.int64()),
            }
        )
        if not keys:
            return empty
        inst = str(keys[0])
        d = decision_time.astimezone(UTC)
        hit = self._pick(self._prices.get(inst, []), d)
        if hit is None:
            return empty
        period_start, price = hit
        avail_us = _us(period_start + timedelta(days=1))
        pstart_us = _us(period_start)
        return pa.table(
            {
                "instrument_id": pa.array([inst], pa.string()),
                "close": pa.array([price], pa.float64()),
                "availability_time": pa.array([avail_us], pa.int64()),
                "period_start": pa.array([pstart_us], pa.int64()),
            }
        )

    @staticmethod
    def _pick(
        series: list[tuple[datetime, float]], as_of: datetime
    ) -> tuple[datetime, float] | None:
        chosen: tuple[datetime, float] | None = None
        for period_start, v in series:
            availability = period_start + timedelta(days=1)
            if availability <= as_of:
                chosen = (period_start, v)
            else:
                break
        return chosen


def _flat_prices(
    instrument_id: str, days: int, start_price: float = 100.0, growth: float = 0.0
) -> dict[str, list[tuple[datetime, float]]]:
    if growth != 0.0:
        prices = [(_ts(d), start_price * (1.0 + growth) ** d) for d in range(days)]
    else:
        prices = [(_ts(d), start_price) for d in range(days)]
    return {instrument_id: prices}


# ---------------------------------------------------------------------------
# Acceptance item 5: 30-7 and 90-7 formulas match the factor card
# ---------------------------------------------------------------------------


def test_tsmom_30_7_formula_matches_card() -> None:
    """tsmom_30_7 = log(P[t-7d] / P[t-30d]) on a fixed synthetic series."""
    prices = _flat_prices("1", days=120, start_price=100.0, growth=0.01)
    store = _FakeAsOf(prices)
    factor = make_tsmom_30_7(store, market_dataset_id=_DATASET)

    assert factor.factor_id == TSMOM_30_7_FACTOR_ID
    assert factor.lookback_days == 30
    assert factor.skip_days == 7
    assert isinstance(factor, Factor)

    decision = _ts(100)
    frame = factor.compute(("1",), decision)

    # t-7d = day 93, latest avail bar period_start <= 92. P at day 92.
    p_recent = 100.0 * (1.01 ** 92)
    # t-30d = day 70, latest avail bar has period_start <= 69. P at day 69.
    p_far = 100.0 * (1.01 ** 69)
    expected = math.log(p_recent / p_far)

    assert len(frame.values) == 1
    assert frame.values[0].raw_value == pytest.approx(expected, rel=1e-9)
    assert frame.values[0].score == pytest.approx(expected, rel=1e-9)
    assert frame.values[0].factor_id == TSMOM_30_7_FACTOR_ID


def test_tsmom_90_7_formula_matches_card() -> None:
    """tsmom_90_7 = log(P[t-7d] / P[t-90d]) on a fixed synthetic series."""
    prices = _flat_prices("1", days=120, start_price=100.0, growth=0.01)
    store = _FakeAsOf(prices)
    factor = make_tsmom_90_7(store, market_dataset_id=_DATASET)

    assert factor.factor_id == TSMOM_90_7_FACTOR_ID
    assert factor.lookback_days == 90
    assert factor.skip_days == 7

    decision = _ts(100)
    frame = factor.compute(("1",), decision)

    # t-7d = day 93, latest avail bar period_start <= 92. P at day 92.
    p_recent = 100.0 * (1.01 ** 92)
    # t-90d = day 10, latest avail bar period_start <= 9. P at day 9.
    p_far = 100.0 * (1.01 ** 9)
    expected = math.log(p_recent / p_far)

    assert len(frame.values) == 1
    assert frame.values[0].raw_value == pytest.approx(expected, rel=1e-9)
    assert frame.values[0].score == pytest.approx(expected, rel=1e-9)
    assert frame.values[0].factor_id == TSMOM_90_7_FACTOR_ID


def test_30_7_and_90_7_produce_different_signals() -> None:
    prices = _flat_prices("1", days=120, start_price=100.0, growth=0.01)
    store = _FakeAsOf(prices)
    f30 = make_tsmom_30_7(store, market_dataset_id=_DATASET)
    f90 = make_tsmom_90_7(store, market_dataset_id=_DATASET)

    decision = _ts(100)
    r30 = f30.compute(("1",), decision)
    r90 = f90.compute(("1",), decision)

    assert r30.values[0].raw_value != pytest.approx(r90.values[0].raw_value, rel=1e-6)


# ---------------------------------------------------------------------------
# Acceptance item 6: missing history → missing (omit instrument); zero → flat
# ---------------------------------------------------------------------------


def test_missing_history_omits_instrument_not_zero() -> None:
    """An instrument without enough history is omitted, never imputed to zero."""
    # "long" has 120 days of history; "nohist" has no bars at all
    prices = {
        "long": _flat_prices("long", days=120, start_price=100.0, growth=0.01)["long"],
    }
    store = _FakeAsOf(prices)
    factor = make_tsmom_30_7(store, market_dataset_id=_DATASET)

    decision = _ts(100)
    frame = factor.compute(("long", "nohist"), decision)

    assert len(frame.values) == 1
    assert frame.values[0].instrument_id == "long"
    # "nohist" is missing — not present, not zero


def test_zero_signal_is_flat_score() -> None:
    """An exactly zero log-return signal yields a flat score (0.0 = cash)."""
    # Flat price → log(P_recent / P_far) = log(1.0) = 0.0
    prices = _flat_prices("1", days=120, start_price=100.0, growth=0.0)
    store = _FakeAsOf(prices)
    factor = make_tsmom_30_7(store, market_dataset_id=_DATASET)

    decision = _ts(100)
    frame = factor.compute(("1",), decision)

    assert len(frame.values) == 1
    assert frame.values[0].raw_value == 0.0
    assert frame.values[0].score == 0.0  # flat / cash, not imputed


# ---------------------------------------------------------------------------
# Validation / fail-closed
# ---------------------------------------------------------------------------


def test_non_utc_decision_time_fails_closed() -> None:
    prices = _flat_prices("1", days=120)
    store = _FakeAsOf(prices)
    factor = make_tsmom_30_7(store, market_dataset_id=_DATASET)

    naive = datetime(2020, 4, 10)  # no tzinfo
    with pytest.raises(TSMOMError, match="timezone-aware UTC"):
        factor.compute(("1",), naive)


def test_invalid_lookback_skip_rejected() -> None:
    prices = _flat_prices("1", days=120)
    store = _FakeAsOf(prices)
    with pytest.raises(TSMOMError, match="lookback_days must be > skip_days"):
        TimeSeriesMomentumFactor(
            store,
            lookback_days=7,
            skip_days=7,
            market_dataset_id=_DATASET,
        )


def test_deterministic_output() -> None:
    """Same inputs produce identical frames on repeated calls."""
    prices = _flat_prices("1", days=120, start_price=100.0, growth=0.01)
    store = _FakeAsOf(prices)
    factor = make_tsmom_30_7(store, market_dataset_id=_DATASET)

    decision = _ts(100)
    a = factor.compute(("1",), decision)
    b = factor.compute(("1",), decision)

    assert a.values[0].raw_value == b.values[0].raw_value
    assert a.values[0].score == b.values[0].score


def test_universe_sorted_and_deduped() -> None:
    prices = {k: v for k, v in {**_flat_prices("b", 120), **_flat_prices("a", 120)}.items()}
    store = _FakeAsOf(prices)
    factor = make_tsmom_30_7(store, market_dataset_id=_DATASET)

    decision = _ts(100)
    frame = factor.compute(("b", "a", "a"), decision)
    ids = [v.instrument_id for v in frame.values]
    assert ids == ["a", "b"]