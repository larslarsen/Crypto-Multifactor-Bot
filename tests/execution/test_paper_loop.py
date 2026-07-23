"""Tests for PAPER-001 Factor-Driven Paper Trading Loop."""

import tempfile
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cryptofactors.execution import (
    FactorDrivenPaperLoop,
    UnapprovedArtifactError,
)
from cryptofactors.factors.tsmom import TimeSeriesMomentumFactor
from cryptofactors.promotion import (
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)

UTC = timezone.utc
MODEL_ARTIFACT_ID = "mod_tsmom_30_7_v1"
FINGERPRINT = "87469a44a18449bee23de76b1312413fd3e5a649a6677e3509a8c270caea3318"


class _StubPriceStore:
    def __init__(self, universe: list[str]) -> None:
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        self.prices: dict[str, list[tuple[datetime, float]]] = {}
        for i, inst in enumerate(universe):
            start = 100.0 * (1.0 + i * 0.2)
            growth = 0.001 * (1 if i % 2 == 0 else -1)
            inst_prices = []
            for d in range(160):
                dt = t0 + timedelta(days=d)
                p = start * ((1.0 + growth) ** d)
                inst_prices.append((dt, p))
            self.prices[inst] = inst_prices

    def latest_available(
        self,
        dataset_id: str,
        keys: list[object],
        fields: list[str],
        decision_time: datetime,
        max_age: object = None,
    ) -> object:
        import pyarrow as pa

        if "ref_instrument" in dataset_id:
            return pa.table({"instrument_id": pa.array([str(k) for k in keys], pa.string())})

        if not keys:
            return pa.table({"instrument_id": pa.array([], pa.string()), "close": pa.array([], pa.float64())})

        inst = str(keys[0])
        series = self.prices.get(inst, [])
        d = decision_time.astimezone(UTC)

        chosen: tuple[datetime, float] | None = None
        for period_start, v in series:
            avail = period_start + timedelta(days=1)
            if avail <= d:
                chosen = (period_start, v)
            else:
                break

        if chosen is None:
            return pa.table({"instrument_id": pa.array([], pa.string()), "close": pa.array([], pa.float64())})

        period_start, price = chosen
        pstart_us = int(period_start.timestamp() * 1_000_000)
        avail_us = int((period_start + timedelta(days=1)).timestamp() * 1_000_000)

        return pa.table(
            {
                "instrument_id": pa.array([inst], pa.string()),
                "close": pa.array([price], pa.float64()),
                "availability_time": pa.array([avail_us], pa.int64()),
                "period_start": pa.array([pstart_us], pa.int64()),
            }
        )

    def get_prices_at(self, dt: datetime, universe: Sequence[str]) -> dict[str, float]:
        res: dict[str, float] = {}
        for inst in universe:
            series = self.prices.get(inst, [])
            for p_time, p_val in series:
                if p_time <= dt:
                    res[inst] = p_val
                else:
                    break
        return res


def promote_to_paper(registry: PromotionRegistry, artifact_id: str = MODEL_ARTIFACT_ID) -> None:
    payload_cand = PromotionIdentityPayload(
        model_artifact_id=artifact_id,
        experiment_fingerprint=FINGERPRINT,
        dataset_ids=("ds_1h",),
        universe_ids=("cmc_univ",),
        code_commit="commit123",
        config_version="cfg1",
        feature_version="feat1",
        representation_version="rep1",
        portfolio_version="port1",
        cost_model_version="cost1",
        risk_policy_version="risk1",
        target_stage=PromotionTarget.RESEARCH,
        effective_time=datetime.now(UTC),
        approving_authority="Lead Quant",
        evidence_reference="rev_001",
    )
    registry.register_candidate(payload_cand)

    payload_paper = PromotionIdentityPayload(
        model_artifact_id=artifact_id,
        experiment_fingerprint=FINGERPRINT,
        dataset_ids=("ds_1h",),
        universe_ids=("cmc_univ",),
        code_commit="commit123",
        config_version="cfg1",
        feature_version="feat1",
        representation_version="rep1",
        portfolio_version="port1",
        cost_model_version="cost1",
        risk_policy_version="risk1",
        target_stage=PromotionTarget.PAPER,
        effective_time=datetime.now(UTC) - timedelta(days=20),
        approving_authority="Lead Quant",
        evidence_reference="rev_001",
    )
    registry.transition_state(
        payload_paper,
        target_state=PromotionState.PAPER_APPROVED,
        reason="Approved for paper evaluation",
    )


def test_paper_loop_fails_closed_for_unapproved_artifact() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)
        universe = ["XBTUSD", "ETHUSD"]
        store = _StubPriceStore(universe)
        factor = TimeSeriesMomentumFactor(store, lookback_days=30, skip_days=7, market_dataset_id="ds_1h")

        with pytest.raises(UnapprovedArtifactError, match="failed paper promotion gate"):
            FactorDrivenPaperLoop(
                model_artifact_id="unapproved_model",
                promotion_registry=registry,
                factor=factor,
            )


def test_paper_loop_execution_and_metrics() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)
        promote_to_paper(registry, MODEL_ARTIFACT_ID)

        universe = ["XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD"]
        store = _StubPriceStore(universe)
        factor = TimeSeriesMomentumFactor(store, lookback_days=30, skip_days=7, market_dataset_id="ds_1h")

        loop = FactorDrivenPaperLoop(
            model_artifact_id=MODEL_ARTIFACT_ID,
            promotion_registry=registry,
            factor=factor,
            initial_cash=100_000.0,
        )

        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        decision_times = [t0 + timedelta(days=d) for d in range(100, 150, 7)]

        res = loop.run_loop(
            universe=universe,
            decision_times=decision_times,
            get_prices_at=store.get_prices_at,
            min_observation_days=14,
        )

        assert res.model_artifact_id == MODEL_ARTIFACT_ID
        assert res.factor_id == "tsmom_30_7"
        assert res.initial_cash == 100_000.0
        assert res.total_trades_executed > 0
        assert len(res.period_logs) == len(decision_times)
