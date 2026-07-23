"""SERV-001 — artifact / representation parity tests."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest

from cryptofactors.catalog.as_of import CatalogAsOfStore
from cryptofactors.factors.baseline import (
    MeanReversionFactor,
    MomentumFactor,
    VolumeFactor,
)
from cryptofactors.factors.composite import EqualWeightRankComposite
from cryptofactors.factors.contract import Factor, FactorFrame, FactorValue
from cryptofactors.factors.ml import RidgeFactor
from cryptofactors.serving.parity import (
    ParityError,
    ParityHarness,
    ServingFactorEvaluator,
    TruncatedAsOfStoreAdapter,
    compare_factor_frames,
)
from cryptofactors.validation.labels import AsOfLabelEngine, LabelConfig, LabelType
from tests.test_baseline_factors import (
    _DATASET,
    _INSTRUMENT_DATASET_ID,
    _build_catalog_asof,
)

UTC = timezone.utc


def _ts(day: int) -> datetime:
    return datetime(2020, 1, 1, tzinfo=UTC) + timedelta(days=day)


def _us(dt: datetime) -> int:
    return int(dt.astimezone(UTC).timestamp() * 1_000_000)


class _FakeAsOf:
    """Minimal fake as-of store matching production BAR-001 timestamp model."""

    def __init__(
        self,
        prices: dict[str, list[tuple[datetime, float]]],
        volumes: dict[str, list[tuple[datetime, float]]] | None = None,
    ) -> None:
        self._prices = {
            k: sorted(((t.astimezone(UTC), float(p)) for t, p in v), key=lambda x: x[0])
            for k, v in prices.items()
        }
        vols = volumes if volumes is not None else {}
        self._volumes = {
            k: sorted(((t.astimezone(UTC), float(p)) for t, p in v), key=lambda x: x[0])
            for k, v in vols.items()
        }

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> pa.Table:
        del dataset_id, max_age
        empty = pa.table(
            {
                "instrument_id": pa.array([], pa.string()),
                "close": pa.array([], pa.float64()),
                "base_volume": pa.array([], pa.float64()),
                "availability_time": pa.array([], pa.int64()),
                "period_start": pa.array([], pa.int64()),
            }
        )
        if not keys:
            return empty
        inst = str(keys[0])
        d = decision_time.astimezone(UTC)
        close_hit = self._pick_available(self._prices.get(inst, []), d)
        vol_hit = self._pick_available(self._volumes.get(inst, []), d)

        if close_hit is None and ("close" in fields):
            return empty

        if close_hit is not None:
            period_start, close_v = close_hit
        else:
            assert vol_hit is not None
            period_start, _ = vol_hit
            close_v = None
        vol_v = self._value_at(self._volumes.get(inst, []), period_start)
        period_end = period_start + timedelta(days=1)
        avail_us = _us(period_end)
        pstart_us = _us(period_start)
        data: dict[str, object] = {
            "instrument_id": pa.array([inst], pa.string()),
            "availability_time": pa.array([avail_us], pa.int64()),
            "period_start": pa.array([pstart_us], pa.int64()),
        }
        if close_v is not None:
            data["close"] = pa.array([close_v], pa.float64())
        if vol_v is not None:
            data["base_volume"] = pa.array([vol_v], pa.float64())
        names = [f for f in fields if f in data] or list(data.keys())
        return pa.table({n: data[n] for n in names})

    @staticmethod
    def _pick_available(
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

    @staticmethod
    def _value_at(
        series: list[tuple[datetime, float]], period_start: datetime
    ) -> float | None:
        for tt, v in series:
            if tt == period_start:
                return v
        return None

    def as_of(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        instant: datetime,
        knowledge_time: datetime | None = None,
    ) -> pa.Table:
        del dataset_id, instant, knowledge_time
        return pa.table(
            {
                "instrument_id": pa.array([str(k) for k in keys], pa.string()),
            }
        )


def _fake_synthetic_store(n_inst: int = 4, n_days: int = 40) -> _FakeAsOf:
    prices: dict[str, list[tuple[datetime, float]]] = {}
    volumes: dict[str, list[tuple[datetime, float]]] = {}
    for i in range(1, n_inst + 1):
        iid = str(i)
        prices[iid] = [(_ts(d), 100.0 + i * 5.0 + d * 0.5) for d in range(n_days)]
        volumes[iid] = [(_ts(d), 1000.0 + i * 100.0 + d * 10.0) for d in range(n_days)]
    return _FakeAsOf(prices, volumes)


class _BuggyLookaheadFactor:
    """Intentionally flawed factor that leaks future data in batch mode."""

    factor_id = "buggy_lookahead"
    factor_version = "1"

    def __init__(self, store: _FakeAsOf) -> None:
        self.store = store

    def compute(self, universe: Sequence[str], as_of: datetime) -> FactorFrame:
        dt = as_of.astimezone(UTC)
        values: list[FactorValue] = []
        for iid in universe:
            # Buggy: queries 5 days in the future if available in batch store!
            future_dt = dt + timedelta(days=5)
            table = self.store.latest_available(
                _DATASET, [iid], ["close"], future_dt
            )
            val = (
                table.column("close")[0].as_py()
                if table.num_rows > 0
                else 0.0
            )
            values.append(
                FactorValue(
                    instrument_id=iid,
                    decision_time=dt,
                    raw_value=float(val),
                    score=float(val),
                    availability_time=dt,
                    factor_id=self.factor_id,
                    factor_version=self.factor_version,
                )
            )
        return FactorFrame(
            values=tuple(values),
            factor_id=self.factor_id,
            factor_version=self.factor_version,
            decision_time=dt,
        )


def test_baseline_factor_serving_parity() -> None:
    store = _fake_synthetic_store(n_inst=4, n_days=40)
    universe = ("1", "2", "3", "4")
    decision_times = [_ts(d) for d in (25, 26, 27, 28, 29, 30)]

    def factor_factory(st: _FakeAsOf) -> Factor:
        return MomentumFactor(st, market_dataset_id=_DATASET, window=10)

    harness = ParityHarness()
    result = harness.verify_parity(
        factor_factory=factor_factory,
        store=store,
        universe=universe,
        decision_times=decision_times,
    )

    assert result.is_parity_satisfied
    assert len(result.comparisons) == len(decision_times)


def test_composite_factor_serving_parity() -> None:
    store = _fake_synthetic_store(n_inst=4, n_days=40)
    universe = ("1", "2", "3", "4")
    decision_times = [_ts(d) for d in (25, 26, 27, 28, 29, 30)]

    def factor_factory(st: _FakeAsOf) -> Factor:
        children: list[Factor] = [
            MomentumFactor(st, market_dataset_id=_DATASET, window=10),
            MeanReversionFactor(st, market_dataset_id=_DATASET, window=10),
            VolumeFactor(st, market_dataset_id=_DATASET, window=10),
        ]
        return EqualWeightRankComposite(children)

    harness = ParityHarness()
    result = harness.verify_parity(
        factor_factory=factor_factory,
        store=store,
        universe=universe,
        decision_times=decision_times,
    )

    assert result.is_parity_satisfied
    assert len(result.comparisons) == len(decision_times)


def test_ml_factor_serving_parity() -> None:
    store = _fake_synthetic_store(n_inst=4, n_days=40)
    universe = ("1", "2", "3", "4")
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=False,
    )
    schedule = [_ts(d) for d in (7, 14, 21)]
    decision_times = [_ts(d) for d in (25, 26, 27, 28, 29, 30)]

    def factor_factory(st: _FakeAsOf) -> Factor:
        features: list[Factor] = [
            MomentumFactor(st, market_dataset_id=_DATASET, window=5),
            VolumeFactor(st, market_dataset_id=_DATASET, window=5),
        ]
        return RidgeFactor(
            features,
            label_engine,
            label_config,
            schedule,
            alpha=1.0,
        )

    harness = ParityHarness()
    result = harness.verify_parity(
        factor_factory=factor_factory,
        store=store,
        universe=universe,
        decision_times=decision_times,
    )

    assert result.is_parity_satisfied
    assert len(result.comparisons) == len(decision_times)


def test_parity_harness_detects_lookahead_mismatch() -> None:
    store = _fake_synthetic_store(n_inst=4, n_days=40)
    universe = ("1", "2", "3", "4")
    decision_times = [_ts(d) for d in (20, 21, 22)]

    def factor_factory(st: _FakeAsOf) -> Factor:
        return _BuggyLookaheadFactor(st)

    harness = ParityHarness()
    # Adapter blocks future decision_time queries
    with pytest.raises(ParityError, match="decision_time exceeds max_availability_time"):
        harness.verify_parity(
            factor_factory=factor_factory,
            store=store,
            universe=universe,
            decision_times=decision_times,
        )


class _BuggyServingMismatchFactor:
    """Factor that computes differently in batch vs serving context."""

    factor_id = "buggy_serving_mismatch"
    factor_version = "1"

    def __init__(self, store: Any) -> None:
        self.store = store

    def compute(self, universe: Sequence[str], as_of: datetime) -> FactorFrame:
        dt = as_of.astimezone(UTC)
        values: list[FactorValue] = []
        is_serving = isinstance(self.store, TruncatedAsOfStoreAdapter)
        for iid in universe:
            val = 99.0 if is_serving else 1.0
            values.append(
                FactorValue(
                    instrument_id=iid,
                    decision_time=dt,
                    raw_value=val,
                    score=val,
                    availability_time=dt,
                    factor_id=self.factor_id,
                    factor_version=self.factor_version,
                )
            )
        return FactorFrame(
            values=tuple(values),
            factor_id=self.factor_id,
            factor_version=self.factor_version,
            decision_time=dt,
        )


def test_compare_factor_frames_direct() -> None:
    dt = _ts(10)
    v1 = FactorValue("1", dt, 1.0, 1.0, dt, "f1", "1")
    v2 = FactorValue("2", dt, 2.0, 2.0, dt, "f1", "1")
    f_batch = FactorFrame((v1, v2), "f1", "1", dt)
    f_serving = FactorFrame((v1, v2), "f1", "1", dt)

    is_eq, diffs = compare_factor_frames(f_batch, f_serving)
    assert is_eq
    assert not diffs

    # Factor ID mismatch
    f_other_id = FactorFrame((v1, v2), "f2", "1", dt)
    is_eq2, diffs2 = compare_factor_frames(f_batch, f_other_id)
    assert not is_eq2
    assert any("factor_id mismatch" in d for d in diffs2)

    # Score mismatch
    v2_bad = FactorValue("2", dt, 2.0, 9.0, dt, "f1", "1")
    f_bad_score = FactorFrame((v1, v2_bad), "f1", "1", dt)
    is_eq3, diffs3 = compare_factor_frames(f_batch, f_bad_score)
    assert not is_eq3
    assert any("score mismatch" in d for d in diffs3)


def test_parity_harness_detects_frame_mismatch() -> None:
    store = _fake_synthetic_store(n_inst=4, n_days=40)
    universe = ("1", "2", "3", "4")
    decision_times = [_ts(d) for d in (20, 21, 22)]

    def factor_factory(st: Any) -> Factor:
        return _BuggyServingMismatchFactor(st)

    harness = ParityHarness()
    with pytest.raises(ParityError, match="Parity mismatch detected"):
        harness.verify_parity(
            factor_factory=factor_factory,
            store=store,
            universe=universe,
            decision_times=decision_times,
        )



def test_serving_evaluator_enforces_chronological_order() -> None:
    store = _fake_synthetic_store(n_inst=2, n_days=30)
    factor = MomentumFactor(store, market_dataset_id=_DATASET, window=5)
    evaluator = ServingFactorEvaluator(factor)

    evaluator.evaluate_daily(("1", "2"), _ts(20))
    with pytest.raises(
        ParityError, match="serving decision_time must strictly advance"
    ):
        evaluator.evaluate_daily(("1", "2"), _ts(19))


def test_substrate_catalog_asof_parity_integration(tmp_path: Path) -> None:
    """CatalogAsOfStore substrate parity check across baseline, composite, ML factors."""
    n_assets = 6
    n_days = 45
    window = 5
    instruments = list(range(1, n_assets + 1))
    start = datetime(2020, 1, 1, tzinfo=UTC)
    root = tmp_path / "serving_substrate"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    store = _build_catalog_asof(
        root,
        instruments=instruments,
        start=start,
        n_days=n_days,
        price_seed=12,
    )
    assert isinstance(store, CatalogAsOfStore)

    universe = [str(i) for i in instruments]
    decision_times = [start + timedelta(days=d) for d in (30, 31, 32, 33)]

    # 1. Baseline Factor Parity
    def baseline_factory(st: CatalogAsOfStore) -> Factor:
        return MomentumFactor(st, market_dataset_id=_DATASET, window=window)

    harness = ParityHarness()
    base_res = harness.verify_parity(
        factor_factory=baseline_factory,
        store=store,
        universe=universe,
        decision_times=decision_times,
    )
    assert base_res.is_parity_satisfied

    # 2. Composite Factor Parity
    def composite_factory(st: CatalogAsOfStore) -> Factor:
        children: list[Factor] = [
            MomentumFactor(st, market_dataset_id=_DATASET, window=window),
            MeanReversionFactor(st, market_dataset_id=_DATASET, window=window),
            VolumeFactor(st, market_dataset_id=_DATASET, window=window),
        ]
        return EqualWeightRankComposite(children)

    comp_res = harness.verify_parity(
        factor_factory=composite_factory,
        store=store,
        universe=universe,
        decision_times=decision_times,
    )
    assert comp_res.is_parity_satisfied

    # 3. ML Factor Parity
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=True,
    )
    train_schedule = [start + timedelta(days=d) for d in (10, 15, 20, 25)]

    def ml_factory(st: CatalogAsOfStore) -> Factor:
        feats: list[Factor] = [
            MomentumFactor(st, market_dataset_id=_DATASET, window=window),
            VolumeFactor(st, market_dataset_id=_DATASET, window=window),
        ]
        return RidgeFactor(
            feats,
            label_engine,
            label_config,
            train_schedule,
            alpha=1.0,
        )

    ml_res = harness.verify_parity(
        factor_factory=ml_factory,
        store=store,
        universe=universe,
        decision_times=decision_times,
    )
    assert ml_res.is_parity_satisfied
