"""MOMTS-001 — Confirmatory runner tests for MOM-TS-01.

Tests assert:
- Distinct EXP-001 fingerprints for EXP-2026-019 vs EXP-2026-020.
- Runner end-to-end produces structured artifacts with proper bundle metadata.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

import pyarrow as pa
import pytest

from cryptofactors.experiments.momts_runner import (
    EXP_2026_019_ID,
    EXP_2026_020_ID,
    MOMTSRunner,
    build_momts_30_7_bundle,
    build_momts_90_7_bundle,
)
from cryptofactors.factors.tsmom import (
    TSMOM_30_7_FACTOR_ID,
    TSMOM_90_7_FACTOR_ID,
)

UTC = timezone.utc
_DATASET = "ds_momts_bars"
_US = 1_000_000


def _ts(day: int) -> datetime:
    return datetime(2020, 1, 1, tzinfo=UTC) + timedelta(days=day)


def _us(dt: datetime) -> int:
    return int(dt.astimezone(UTC).timestamp() * _US)


class _FakeAsOf:
    """As-of fake supporting both market_bars and ref_instrument_version datasets."""

    def __init__(
        self,
        prices: dict[str, list[tuple[datetime, float]]],
        instruments: set[str] | None = None,
    ) -> None:
        self._prices = {
            k: sorted(((t.astimezone(UTC), float(p)) for t, p in v), key=lambda x: x[0])
            for k, v in prices.items()
        }
        self._instruments = instruments or set(self._prices.keys())

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> pa.Table:
        return self._query(dataset_id, keys, fields, decision_time)

    def as_of(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        knowledge_time: datetime | None = None,
    ) -> pa.Table:
        return self._query(dataset_id, keys, fields, decision_time)

    def _query(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
    ) -> pa.Table:
        if "ref_instrument" in dataset_id:
            inst_ids = [str(k) for k in keys if str(k) in self._instruments]
            return pa.table(
                {"instrument_id": pa.array(inst_ids, pa.string())}
            )
        if not keys:
            return self._empty()
        inst = str(keys[0])
        d = decision_time.astimezone(UTC)
        hit = self._pick(self._prices.get(inst, []), d)
        if hit is None:
            return self._empty()
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
    def _empty() -> pa.Table:
        return pa.table(
            {
                "instrument_id": pa.array([], pa.string()),
                "close": pa.array([], pa.float64()),
                "availability_time": pa.array([], pa.int64()),
                "period_start": pa.array([], pa.int64()),
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


def _make_prices(instruments: list[str], days: int = 120, growth: float = 0.01) -> dict[str, list[tuple[datetime, float]]]:
    prices: dict[str, list[tuple[datetime, float]]] = {}
    for i, inst in enumerate(instruments):
        start = 100.0 * (1.0 + i * 0.1)
        prices[inst] = [(_ts(d), start * (1.0 + growth) ** d) for d in range(days)]
    return prices


# ---------------------------------------------------------------------------
# Acceptance item 7: distinct EXP-001 fingerprints for 019 vs 020
# ---------------------------------------------------------------------------


def test_bundles_have_distinct_fingerprints() -> None:
    """EXP-2026-019 and EXP-2026-020 must produce different fingerprints."""
    bundle_30 = build_momts_30_7_bundle(_DATASET)
    bundle_90 = build_momts_90_7_bundle(_DATASET)

    assert bundle_30.fingerprint != bundle_90.fingerprint
    assert bundle_30.factor_defs == ("tsmom_30_7",)
    assert bundle_90.factor_defs == ("tsmom_90_7",)


def test_bundle_metadata_documents_experiment_id_and_formula() -> None:
    bundle = build_momts_30_7_bundle(_DATASET)
    meta = dict(bundle.metadata)

    assert meta["experiment_id"] == EXP_2026_019_ID
    assert meta["signal"] == "tsmom_30_7"
    assert meta["formula"] == "log(P[t-7d] / P[t-30d])"
    assert meta["lookback_days"] == 30
    assert meta["skip_days"] == 7
    assert meta["horizon_days"] == 7
    assert meta["portfolio_cell"] == "perp_ls"
    assert meta["survivorship_source"] == "cmc_data_api_unofficial_proxy"


def test_bundle_90_7_metadata() -> None:
    bundle = build_momts_90_7_bundle(_DATASET)
    meta = dict(bundle.metadata)

    assert meta["experiment_id"] == EXP_2026_020_ID
    assert meta["signal"] == "tsmom_90_7"
    assert meta["formula"] == "log(P[t-7d] / P[t-90d])"
    assert meta["lookback_days"] == 90
    assert meta["skip_days"] == 7


def test_registered_fingerprints_match_recomputed() -> None:
    """Fingerprints stored in the bundle must match recomputation."""
    from cryptofactors.validation.experiment import InMemoryExperimentRegistry

    bundle = build_momts_30_7_bundle(_DATASET)
    registry = InMemoryExperimentRegistry()
    fp = registry.register(bundle)
    assert fp == bundle.fingerprint
    assert registry.has(bundle.fingerprint)


# ---------------------------------------------------------------------------
# Runner end-to-end (synthetic as-of)
# ---------------------------------------------------------------------------


def test_runner_produces_distinct_results_for_both_experiments() -> None:
    instruments = ["a", "b", "c"]
    prices = _make_prices(instruments, days=120)
    store = _FakeAsOf(prices, instruments=set(instruments))

    runner = MOMTSRunner(store, market_dataset_id=_DATASET)
    decision_times = [_ts(d) for d in range(100, 150, 7)]

    result_019 = runner.run_30_7(instruments, decision_times)
    result_020 = runner.run_90_7(instruments, decision_times)

    assert result_019.experiment_id == EXP_2026_019_ID
    assert result_020.experiment_id == EXP_2026_020_ID
    assert result_019.factor_id == TSMOM_30_7_FACTOR_ID
    assert result_020.factor_id == TSMOM_90_7_FACTOR_ID
    assert result_019.fingerprint != result_020.fingerprint
    assert result_019.n_periods > 0
    assert result_020.n_periods > 0
    assert hasattr(result_019, "liquidation_count")
    assert hasattr(result_019, "long_return")
    assert hasattr(result_019, "short_return")
    assert hasattr(result_019, "total_funding_cost")


def test_runner_rejects_unknown_experiment_id() -> None:
    instruments = ["a"]
    prices = _make_prices(instruments, days=120)
    store = _FakeAsOf(prices, instruments=set(instruments))

    runner = MOMTSRunner(store, market_dataset_id=_DATASET)

    from cryptofactors.factors.tsmom import TimeSeriesMomentumFactor
    from cryptofactors.experiments.momts_runner import build_momts_30_7_bundle

    factor = TimeSeriesMomentumFactor(
        store, lookback_days=30, skip_days=7, market_dataset_id=_DATASET,
        factor_id=TSMOM_30_7_FACTOR_ID,
    )
    bundle = build_momts_30_7_bundle(_DATASET)
    with pytest.raises(ValueError, match="experiment_id must be"):
        runner.run_experiment(
            experiment_id="EXP-FAKE-999",
            factor=factor,
            bundle=bundle,
            universe=instruments,
            decision_times=[_ts(100), _ts(107)],
        )