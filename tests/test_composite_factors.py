"""COMP-001 — equal-weight rank composite factor tests."""

from __future__ import annotations

import math
import shutil
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cryptofactors.catalog.as_of import CatalogAsOfStore
from cryptofactors.factors.baseline import (
    MeanReversionFactor,
    MomentumFactor,
    VolumeFactor,
)
from cryptofactors.factors.composite import (
    COMPOSITE_EQUAL_RANK_FACTOR_ID,
    COMPOSITE_FACTOR_VERSION,
    CompositeFactorError,
    EqualWeightRankComposite,
)
from cryptofactors.factors.contract import Factor, FactorFrame, FactorValue
from cryptofactors.validation.experiment import (
    ExperimentBundle,
    InMemoryExperimentRegistry,
)
from cryptofactors.validation.labels import (
    AsOfLabelEngine,
    LabelConfig,
    LabelType,
)
from cryptofactors.validation.split import (
    PurgedChronologicalSplitter,
    SplitConfig,
    SplitMode,
)
from tests.test_baseline_factors import (
    _DATASET,
    _INSTRUMENT_DATASET_ID,
    _build_catalog_asof,
)

UTC = timezone.utc


class _ConstFactor:
    """Deterministic child factor returning fixed scores for a subset of ids."""

    factor_version: str = "1"

    def __init__(self, scores: dict[str, float], *, factor_id: str = "const") -> None:
        self.factor_id = factor_id
        self._scores = dict(scores)

    def compute(
        self,
        universe: Sequence[str],
        as_of: datetime,
    ) -> FactorFrame:
        decision_time = as_of.astimezone(UTC)
        values: list[FactorValue] = []
        for iid in sorted(set(universe)):
            if iid not in self._scores:
                continue
            score = self._scores[iid]
            values.append(
                FactorValue(
                    instrument_id=iid,
                    decision_time=decision_time,
                    raw_value=score,
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


def test_composite_implements_factor_protocol() -> None:
    child = _ConstFactor({"1": 1.0, "2": 2.0})
    comp = EqualWeightRankComposite([child])
    assert isinstance(comp, Factor)
    assert comp.factor_id == COMPOSITE_EQUAL_RANK_FACTOR_ID
    assert comp.factor_version == COMPOSITE_FACTOR_VERSION


def test_composite_rejects_empty_factors() -> None:
    with pytest.raises(CompositeFactorError):
        EqualWeightRankComposite([])


def test_composite_two_assets_ranks_correct() -> None:
    """Higher child score → better (lower) rank; average across factors."""
    # Factor A: a=10, b=20 → ranks a=2, b=1
    # Factor B: a=5,  b=1  → ranks a=1, b=2
    # Average: a=1.5, b=1.5
    fa = _ConstFactor({"a": 10.0, "b": 20.0}, factor_id="A")
    fb = _ConstFactor({"a": 5.0, "b": 1.0}, factor_id="B")
    comp = EqualWeightRankComposite([fa, fb])
    as_of = datetime(2020, 6, 1, tzinfo=UTC)
    frame = comp.compute(("b", "a"), as_of)
    assert [v.instrument_id for v in frame.values] == ["a", "b"]
    by_id = {v.instrument_id: v for v in frame.values}
    assert by_id["a"].score == pytest.approx(1.5)
    assert by_id["b"].score == pytest.approx(1.5)
    assert by_id["a"].raw_value == by_id["a"].score
    assert frame.factor_id == COMPOSITE_EQUAL_RANK_FACTOR_ID


def test_composite_three_assets_rank_order() -> None:
    # scores 30, 10, 20 → ranks 1, 3, 2
    child = _ConstFactor({"x": 30.0, "y": 10.0, "z": 20.0})
    frame = EqualWeightRankComposite([child]).compute(
        ("y", "z", "x"), datetime(2020, 1, 1, tzinfo=UTC)
    )
    by_id = {v.instrument_id: v.score for v in frame.values}
    assert by_id == {"x": 1.0, "z": 2.0, "y": 3.0}


def test_composite_single_asset_rank_one() -> None:
    child = _ConstFactor({"solo": 42.0})
    frame = EqualWeightRankComposite([child]).compute(
        ("solo",), datetime(2020, 1, 1, tzinfo=UTC)
    )
    assert len(frame.values) == 1
    assert frame.values[0].score == pytest.approx(1.0)


def test_composite_ties_get_average_rank() -> None:
    # scores: a=10, b=10, c=5 → a and b tie for 1st/2nd → avg 1.5; c=3
    child = _ConstFactor({"a": 10.0, "b": 10.0, "c": 5.0})
    frame = EqualWeightRankComposite([child]).compute(
        ("a", "b", "c"), datetime(2020, 1, 1, tzinfo=UTC)
    )
    by_id = {v.instrument_id: v.score for v in frame.values}
    assert by_id["a"] == pytest.approx(1.5)
    assert by_id["b"] == pytest.approx(1.5)
    assert by_id["c"] == pytest.approx(3.0)


def test_composite_missing_instrument_skipped_in_average() -> None:
    # Factor A covers a,b ranks a=2,b=1
    # Factor B covers only a → rank a=1
    # a avg = (2+1)/2 = 1.5; b avg = 1.0 only from A
    fa = _ConstFactor({"a": 1.0, "b": 9.0}, factor_id="A")
    fb = _ConstFactor({"a": 100.0}, factor_id="B")
    frame = EqualWeightRankComposite([fa, fb]).compute(
        ("a", "b"), datetime(2020, 1, 1, tzinfo=UTC)
    )
    by_id = {v.instrument_id: v.score for v in frame.values}
    assert by_id["a"] == pytest.approx(1.5)
    assert by_id["b"] == pytest.approx(1.0)


def test_composite_deterministic_universe_order_independent() -> None:
    fa = _ConstFactor({"1": 3.0, "2": 1.0, "3": 2.0}, factor_id="A")
    fb = _ConstFactor({"1": 1.0, "2": 2.0, "3": 3.0}, factor_id="B")
    comp = EqualWeightRankComposite([fa, fb])
    as_of = datetime(2021, 3, 15, tzinfo=UTC)
    a = comp.compute(("3", "1", "2"), as_of)
    b = comp.compute(("2", "3", "1"), as_of)
    assert [v.instrument_id for v in a.values] == [v.instrument_id for v in b.values]
    assert [v.score for v in a.values] == [v.score for v in b.values]


def test_composite_substrate_integration(tmp_path: Path) -> None:
    """CatalogAsOfStore → composite(baselines) → Label → Split → ExperimentBundle."""
    n_assets = 8
    n_days = 50
    window = 5
    instruments = list(range(1, n_assets + 1))
    start = datetime(2020, 1, 1, tzinfo=UTC)
    root = tmp_path / "composite"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    store = _build_catalog_asof(
        root,
        instruments=instruments,
        start=start,
        n_days=n_days,
        price_seed=11,
    )
    assert isinstance(store, CatalogAsOfStore)

    children: list[Factor] = [
        MomentumFactor(store, market_dataset_id=_DATASET, window=window),
        MeanReversionFactor(store, market_dataset_id=_DATASET, window=window),
        VolumeFactor(store, market_dataset_id=_DATASET, window=window),
    ]
    factor = EqualWeightRankComposite(children)
    assert isinstance(factor, Factor)

    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=True,
    )
    split_config = SplitConfig(
        mode=SplitMode.WALK_FORWARD,
        train_span=timedelta(days=15),
        test_span=timedelta(days=10),
        embargo=timedelta(days=1),
        min_train_events=n_assets,
        min_test_events=max(2, n_assets // 2),
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
    )
    bundle = ExperimentBundle(
        label_config=label_config,
        split_config=split_config,
        factor_defs=(factor.factor_id,),
        metadata={"name": "composite_equal_rank"},
    )
    reg = InMemoryExperimentRegistry()
    fp = reg.register(bundle)
    assert reg.has(fp)

    as_of = start + timedelta(days=31)
    universe = [str(i) for i in instruments]
    frame = factor.compute(universe, as_of)
    assert len(frame.values) == n_assets
    assert all(math.isfinite(v.score) for v in frame.values)
    assert frame.factor_id == COMPOSITE_EQUAL_RANK_FACTOR_ID

    decision_times = [
        start + timedelta(days=d) for d in range(window + 2, n_days + 1)
    ]
    events = AsOfLabelEngine(store).compute(instruments, decision_times, label_config)
    assert events
    folds = PurgedChronologicalSplitter(store).split(
        [e.to_event_interval() for e in events],
        split_config,
    )
    assert folds
    test_dt = folds[0].test.events[0].decision_time
    frame2 = factor.compute(universe, test_dt)
    assert len(frame2.values) == n_assets
