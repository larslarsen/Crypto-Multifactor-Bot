"""ML-001 — ML challenger factor tests."""

from __future__ import annotations

import math
import shutil
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyarrow as pa
import pytest

from cryptofactors.catalog.as_of import CatalogAsOfStore
from cryptofactors.factors.baseline import (
    MeanReversionFactor,
    MomentumFactor,
    VolumeFactor,
)
from cryptofactors.factors.contract import Factor, FactorFrame
from cryptofactors.factors.ml import (
    ElasticNetFactor,
    MLFactorError,
    RidgeFactor,
    XGBoostFactor,
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
    """Minimal fake as-of store matching production BAR-001 timestamp model.

    Bars have ``availability_time = period_start + 1d``.  The store returns
    the latest bar whose availability <= decision_time.
    """

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


def _fake_store(
    *,
    n_inst: int = 3,
    n_days: int = 30,
) -> tuple[dict[str, list[tuple[datetime, float]]], dict[str, list[tuple[datetime, float]]]]:
    prices: dict[str, list[tuple[datetime, float]]] = {}
    volumes: dict[str, list[tuple[datetime, float]]] = {}
    for i in range(1, n_inst + 1):
        iid = str(i)
        prices[iid] = [(_ts(d), 100.0 + i + d * 0.5) for d in range(n_days)]
        volumes[iid] = [(_ts(d), 1000.0 + i * 100 + d) for d in range(n_days)]
    return prices, volumes


def _baseline_features(store: _FakeAsOf, window: int = 5) -> list[Factor]:
    return [
        MomentumFactor(store, market_dataset_id=_DATASET, window=window),
        MeanReversionFactor(store, market_dataset_id=_DATASET, window=window),
        VolumeFactor(store, market_dataset_id=_DATASET, window=window),
    ]


_ML_FACTOR_CLS = [RidgeFactor, ElasticNetFactor, XGBoostFactor]


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_ridge_implements_factor_protocol() -> None:
    prices, vols = _fake_store(n_inst=2, n_days=30)
    store = _FakeAsOf(prices, vols)
    features = _baseline_features(store)
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=False,
    )
    schedule = [_ts(d) for d in (7, 14, 21)]
    factor = RidgeFactor(features, label_engine, label_config, schedule, alpha=1.0)
    assert isinstance(factor, Factor)
    assert factor.factor_id == "ml_ridge"
    assert factor.factor_version == "1"


def test_elasticnet_implements_factor_protocol() -> None:
    prices, vols = _fake_store(n_inst=2, n_days=30)
    store = _FakeAsOf(prices, vols)
    features = _baseline_features(store)
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=False,
    )
    schedule = [_ts(d) for d in (7, 14, 21)]
    factor = ElasticNetFactor(features, label_engine, label_config, schedule, alpha=1.0)
    assert isinstance(factor, Factor)
    assert factor.factor_id == "ml_elasticnet"


def test_xgboost_implements_factor_protocol() -> None:
    prices, vols = _fake_store(n_inst=2, n_days=30)
    store = _FakeAsOf(prices, vols)
    features = _baseline_features(store)
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=False,
    )
    schedule = [_ts(d) for d in (7, 14, 21)]
    factor = XGBoostFactor(features, label_engine, label_config, schedule)
    assert isinstance(factor, Factor)
    assert factor.factor_id == "ml_xgboost"


@pytest.mark.parametrize("cls", _ML_FACTOR_CLS)
def test_ml_factor_deterministic(cls: type) -> None:
    prices, vols = _fake_store(n_inst=3, n_days=30)
    store = _FakeAsOf(prices, vols)
    features = _baseline_features(store)
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=False,
    )
    schedule = [_ts(d) for d in (7, 14, 21)]
    factor = cls(features, label_engine, label_config, schedule)
    as_of = _ts(28)
    universe = ("1", "2", "3")
    a = factor.compute(universe, as_of)
    b = factor.compute(universe, as_of)
    assert isinstance(a, FactorFrame)
    assert isinstance(b, FactorFrame)
    assert [v.score for v in a.values] == [v.score for v in b.values]


@pytest.mark.parametrize("cls", _ML_FACTOR_CLS)
def test_ml_factor_universe_order_independent(cls: type) -> None:
    prices, vols = _fake_store(n_inst=3, n_days=30)
    store = _FakeAsOf(prices, vols)
    features = _baseline_features(store)
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=False,
    )
    schedule = [_ts(d) for d in (7, 14, 21)]
    factor = cls(features, label_engine, label_config, schedule)
    as_of = _ts(28)
    a = factor.compute(("3", "1", "2"), as_of)
    b = factor.compute(("2", "3", "1"), as_of)
    assert [v.instrument_id for v in a.values] == [v.instrument_id for v in b.values]
    assert [v.score for v in a.values] == [v.score for v in b.values]


@pytest.mark.parametrize("cls", _ML_FACTOR_CLS)
def test_ml_factor_all_scores_finite(cls: type) -> None:
    prices, vols = _fake_store(n_inst=4, n_days=35)
    store = _FakeAsOf(prices, vols)
    features = _baseline_features(store)
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=False,
    )
    schedule = [_ts(d) for d in (7, 14, 21, 28)]
    factor = cls(features, label_engine, label_config, schedule)
    as_of = _ts(30)
    frame = factor.compute(("1", "2", "3", "4"), as_of)
    assert len(frame.values) == 4
    assert all(math.isfinite(v.score) for v in frame.values)
    assert frame.factor_id == factor.factor_id


def test_insufficient_training_data_returns_empty() -> None:
    prices, vols = _fake_store(n_inst=2, n_days=20)
    store = _FakeAsOf(prices, vols)
    features = _baseline_features(store)
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=False,
    )
    # Schedule date has label window closing after prediction time → no valid dates.
    schedule = [_ts(15)]
    factor = RidgeFactor(features, label_engine, label_config, schedule)
    as_of = _ts(10)
    frame = factor.compute(("1", "2"), as_of)
    assert len(frame.values) == 0


def test_empty_features_raises() -> None:
    prices, vols = _fake_store(n_inst=2, n_days=10)
    store = _FakeAsOf(prices, vols)
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=False,
    )
    with pytest.raises(MLFactorError, match="features must be non-empty"):
        RidgeFactor([], label_engine, label_config, [_ts(7)])


def test_ml_factor_returns_correct_instruments() -> None:
    prices, vols = _fake_store(n_inst=3, n_days=30)
    store = _FakeAsOf(prices, vols)
    features = _baseline_features(store)
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=False,
    )
    schedule = [_ts(d) for d in (7, 14, 21)]
    factor = RidgeFactor(features, label_engine, label_config, schedule)
    as_of = _ts(28)
    frame = factor.compute(("1", "2", "3"), as_of)
    assert len(frame.values) == 3
    assert {v.instrument_id for v in frame.values} == {"1", "2", "3"}


# ---------------------------------------------------------------------------
# Substrate integration (CatalogAsOfStore → LABEL → SPLIT → EXP)
# ---------------------------------------------------------------------------


def test_ml_substrate_integration_ridge(tmp_path: Path) -> None:
    """Run RidgeFactor through full research substrate."""
    n_assets = 6
    n_days = 60
    window = 5
    instruments = list(range(1, n_assets + 1))
    start = datetime(2020, 1, 1, tzinfo=UTC)
    root = tmp_path / "ml_ridge"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    store = _build_catalog_asof(
        root,
        instruments=instruments,
        start=start,
        n_days=n_days,
        price_seed=17,
    )
    assert isinstance(store, CatalogAsOfStore)

    features: list[Factor] = [
        MomentumFactor(store, market_dataset_id=_DATASET, window=window),
        MeanReversionFactor(store, market_dataset_id=_DATASET, window=window),
        VolumeFactor(store, market_dataset_id=_DATASET, window=window),
    ]
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=True,
    )
    schedule = [start + timedelta(days=d) for d in range(10, 50, 5)]
    factor = RidgeFactor(features, label_engine, label_config, schedule)
    assert isinstance(factor, Factor)

    as_of = start + timedelta(days=50)
    universe = [str(i) for i in instruments]
    frame = factor.compute(universe, as_of)
    assert len(frame.values) == n_assets
    assert all(math.isfinite(v.score) for v in frame.values)
    assert frame.factor_id == "ml_ridge"


def test_ml_substrate_integration_xgboost(tmp_path: Path) -> None:
    """Run XGBoostFactor through full research substrate."""
    n_assets = 6
    n_days = 60
    window = 5
    instruments = list(range(1, n_assets + 1))
    start = datetime(2020, 1, 1, tzinfo=UTC)
    root = tmp_path / "ml_xgb"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    store = _build_catalog_asof(
        root,
        instruments=instruments,
        start=start,
        n_days=n_days,
        price_seed=19,
    )
    assert isinstance(store, CatalogAsOfStore)

    features: list[Factor] = [
        MomentumFactor(store, market_dataset_id=_DATASET, window=window),
        MeanReversionFactor(store, market_dataset_id=_DATASET, window=window),
        VolumeFactor(store, market_dataset_id=_DATASET, window=window),
    ]
    label_engine = AsOfLabelEngine(store)
    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=True,
    )
    schedule = [start + timedelta(days=d) for d in range(10, 50, 5)]
    factor = XGBoostFactor(features, label_engine, label_config, schedule)
    assert isinstance(factor, Factor)

    as_of = start + timedelta(days=50)
    universe = [str(i) for i in instruments]
    frame = factor.compute(universe, as_of)
    assert len(frame.values) == n_assets
    assert all(math.isfinite(v.score) for v in frame.values)
    assert frame.factor_id == "ml_xgboost"
