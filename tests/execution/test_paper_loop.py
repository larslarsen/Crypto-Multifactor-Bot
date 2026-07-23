"""Tests for PAPER-001 & PAPER-002 Factor-Driven Paper Trading Loop & Holdout Observation."""

import tempfile
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from cryptofactors.execution import (
    FactorDrivenPaperLoop,
    UnapprovedArtifactError,
)
from cryptofactors.execution.risk_limits import (
    compute_live_gate_satisfied,
    enforce_risk_limits,
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


def promote_to_paper(
    registry: PromotionRegistry,
    artifact_id: str = MODEL_ARTIFACT_ID,
    effective_time: datetime | None = None,
) -> None:
    eff_time = effective_time or datetime(2026, 4, 1, tzinfo=UTC)

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
        effective_time=eff_time,
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
        effective_time=eff_time,
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


def test_observation_non_null_when_window_complete() -> None:
    """PAPER-002: Observation result is non-null and complete when duration >= min_observation_days."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        eff_time = datetime(2026, 4, 1, tzinfo=UTC)
        promote_to_paper(registry, MODEL_ARTIFACT_ID, effective_time=eff_time)

        # 10 assets so single asset weight is 0.10 <= 0.15
        universe = [
            "XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD",
            "AVAXUSD", "DOTUSD", "LINKUSD", "LTCUSD", "BCHUSD",
        ]
        store = _StubPriceStore(universe)
        factor = TimeSeriesMomentumFactor(store, lookback_days=30, skip_days=7, market_dataset_id="ds_1h")

        loop = FactorDrivenPaperLoop(
            model_artifact_id=MODEL_ARTIFACT_ID,
            promotion_registry=registry,
            factor=factor,
            initial_cash=100_000.0,
        )

        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        decision_times = [t0 + timedelta(days=d) for d in range(100, 150, 7)]  # 2026-04-11 to 2026-05-30 (59 days)

        res = loop.run_loop(
            universe=universe,
            decision_times=decision_times,
            get_prices_at=store.get_prices_at,
            min_observation_days=14,
        )

        assert res.observation_result is not None
        obs = res.observation_result
        assert obs.is_complete is True
        assert obs.meets_risk_limits is True
        assert obs.duration_days >= 14.0
        assert obs.reference_id.startswith("obs_mod_tsmom_30_7_v1_")


def test_observation_incomplete_when_window_short() -> None:
    """PAPER-002: Observation is marked incomplete (is_complete=False) when duration < min_observation_days."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        eff_time = datetime(2026, 5, 20, tzinfo=UTC)  # Only 10 days before evaluation at May 30
        promote_to_paper(registry, MODEL_ARTIFACT_ID, effective_time=eff_time)

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
        decision_times = [t0 + timedelta(days=d) for d in range(140, 150, 7)]  # May 20 to May 30

        res = loop.run_loop(
            universe=universe,
            decision_times=decision_times,
            get_prices_at=store.get_prices_at,
            min_observation_days=14,
        )

        assert res.observation_result is not None
        assert res.observation_result.is_complete is False


def test_risk_limits_enforced_even_with_small_universe() -> None:
    """PAPER-006: With 4 assets raw weights are 0.25, but enforcement clips to 0.15 and scales."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        eff_time = datetime(2026, 4, 1, tzinfo=UTC)
        promote_to_paper(registry, MODEL_ARTIFACT_ID, effective_time=eff_time)

        # 4 assets -> raw single asset weight is 0.25, but enforcement should cap it.
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

        assert res.observation_result is not None
        assert res.observation_result.meets_risk_limits is True
        assert res.observation_result.max_single_asset_weight <= Decimal("0.15")
        assert res.observation_result.max_leverage_observed <= Decimal("1.0")


# ---------------------------------------------------------------------------
# PAPER-006 — Risk enforcement helpers
# ---------------------------------------------------------------------------


class TestRiskLimitEnforcement:
    """Unit tests for neutrality-preserving risk enforcement (ALLOC-001)."""

    def test_single_weight_clipped_to_cap(self) -> None:
        weights = {"BTC": 0.5}
        out = enforce_risk_limits(weights)
        assert abs(out["BTC"]) == pytest.approx(0.15)

    def test_gross_scaled_after_clipping(self) -> None:
        # Two weights at 0.5 -> gross 1.0, after clip each at 0.15 -> gross 0.3
        weights = {"BTC": 0.5, "ETH": 0.5}
        out = enforce_risk_limits(weights)
        assert abs(out["BTC"]) == pytest.approx(0.15)
        assert abs(out["ETH"]) == pytest.approx(0.15)
        assert sum(abs(w) for w in out.values()) == pytest.approx(0.3)

    def test_long_short_balanced_unchanged_when_compliant(self) -> None:
        weights = {"BTC": 0.1, "ETH": 0.1, "SOL": -0.1, "XRP": -0.1}
        out = enforce_risk_limits(weights)
        assert out == pytest.approx(weights)

    def test_excess_gross_scaled_uniformly(self) -> None:
        # 10 assets at 0.15 -> gross 1.5, scale to 1.0 -> each 0.10
        weights = {f"A{i}": 0.15 for i in range(10)}
        out = enforce_risk_limits(weights)
        assert sum(abs(w) for w in out.values()) == pytest.approx(1.0)
        for w in out.values():
            assert w == pytest.approx(0.1)

    def test_negative_weights_clipped(self) -> None:
        weights = {"BTC": -0.4, "ETH": -0.6}
        out = enforce_risk_limits(weights)
        assert out["BTC"] == pytest.approx(-0.15)
        assert out["ETH"] == pytest.approx(-0.15)
        assert sum(abs(w) for w in out.values()) == pytest.approx(0.3)

    def test_zero_weights_dropped(self) -> None:
        weights = {"BTC": 0.0, "ETH": 0.1}
        out = enforce_risk_limits(weights)
        assert "BTC" not in out
        assert out["ETH"] == pytest.approx(0.1)

    def test_neutral_ls_preserved_when_one_leg_clipped(self) -> None:
        """ALLOC-001: concentrated long leg clipped; short leg scaled down to match."""
        # Long: 2 names -> raw 0.25 each -> clipped 0.15 each -> gross 0.30
        # Short: 8 names -> raw 0.0625 each -> not clipped -> gross 0.50
        # Expected: short leg scaled to 0.30 gross, net ≈ 0.
        weights = {
            "A1": 0.25,
            "A2": 0.25,
            "B1": -0.0625,
            "B2": -0.0625,
            "B3": -0.0625,
            "B4": -0.0625,
            "B5": -0.0625,
            "B6": -0.0625,
            "B7": -0.0625,
            "B8": -0.0625,
        }
        out = enforce_risk_limits(weights)
        assert max(abs(w) for w in out.values()) == pytest.approx(0.15)
        assert sum(abs(w) for w in out.values()) <= 1.0 + 1e-9
        long_gross = sum(w for w in out.values() if w > 0)
        short_gross = sum(abs(w) for w in out.values() if w < 0)
        assert long_gross == pytest.approx(short_gross)
        assert sum(out.values()) == pytest.approx(0.0, abs=1e-6)
        assert out["A1"] == pytest.approx(0.15)
        assert out["A2"] == pytest.approx(0.15)
        assert out["B1"] == pytest.approx(-0.0375)

    def test_neutral_ls_preserved_when_both_legs_clipped(self) -> None:
        """ALLOC-001: both legs concentrated; post-enforcement net ≈ 0."""
        weights = {"A1": 0.5, "A2": 0.5, "B1": -0.5, "B2": -0.5}
        out = enforce_risk_limits(weights)
        assert max(abs(w) for w in out.values()) == pytest.approx(0.15)
        assert sum(out.values()) == pytest.approx(0.0, abs=1e-6)
        long_gross = sum(w for w in out.values() if w > 0)
        short_gross = sum(abs(w) for w in out.values() if w < 0)
        assert long_gross == pytest.approx(short_gross)
        assert sum(abs(w) for w in out.values()) == pytest.approx(0.6)

    def test_neutral_ls_maximizes_gross_within_caps(self) -> None:
        """ALLOC-001: when legs are unequal, target is the smaller clipped gross."""
        weights = {"A1": 0.5, "A2": 0.1, "B1": -0.5, "B2": -0.1, "B3": -0.1}
        out = enforce_risk_limits(weights)
        long_gross = sum(w for w in out.values() if w > 0)
        short_gross = sum(abs(w) for w in out.values() if w < 0)
        assert long_gross == pytest.approx(short_gross)
        assert long_gross <= 0.5 + 1e-9
        assert sum(abs(w) for w in out.values()) <= 1.0 + 1e-9

    def test_directional_book_scaled_to_gross_cap(self) -> None:
        """ALLOC-001: single-leg book cannot be neutral; scaled to gross cap."""
        weights = {"A1": 0.2, "A2": 0.2, "A3": 0.2, "A4": 0.2, "A5": 0.2, "A6": 0.2, "A7": 0.2}
        out = enforce_risk_limits(weights)
        assert sum(abs(w) for w in out.values()) == pytest.approx(1.0)
        assert sum(out.values()) == pytest.approx(1.0)
        assert max(abs(w) for w in out.values()) == pytest.approx(1.0 / 7)

    def test_neutral_book_gross_cap_enforced(self) -> None:
        """ALLOC-001: if both legs exceed half gross, each leg scaled to max_gross/2."""
        weights = {"A1": 0.5, "A2": 0.5, "A3": 0.5, "A4": 0.5, "B1": -0.5, "B2": -0.5, "B3": -0.5, "B4": -0.5}
        out = enforce_risk_limits(weights)
        long_gross = sum(w for w in out.values() if w > 0)
        short_gross = sum(abs(w) for w in out.values() if w < 0)
        assert long_gross == pytest.approx(0.5)
        assert short_gross == pytest.approx(0.5)
        assert sum(abs(w) for w in out.values()) == pytest.approx(1.0)
        assert sum(out.values()) == pytest.approx(0.0, abs=1e-6)


class TestComputeLiveGateSatisfied:
    """Unit tests for honest live_gate_satisfied predicate."""

    def test_all_prongs_true(self) -> None:
        assert compute_live_gate_satisfied("real_asof", 0.01, True, True) is True

    def test_fails_when_synthetic(self) -> None:
        assert compute_live_gate_satisfied("synthetic", 0.01, True, True) is False

    def test_fails_when_return_negative(self) -> None:
        assert compute_live_gate_satisfied("real_asof", -0.01, True, True) is False

    def test_fails_when_risk_not_met(self) -> None:
        assert compute_live_gate_satisfied("real_asof", 0.01, False, True) is False

    def test_fails_when_incomplete(self) -> None:
        assert compute_live_gate_satisfied("real_asof", 0.01, True, False) is False
