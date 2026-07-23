from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from cryptofactors.portfolio.simulation import SimulationResult, SimulationPeriod
from cryptofactors.promotion.models import PromotionEvent, PromotionState, PromotionIdentityPayload, PromotionTarget
from cryptofactors.serving.holdout import ProspectiveEvaluator, ProspectiveHoldoutError

def dummy_payload(effective_time: datetime) -> PromotionIdentityPayload:
    return PromotionIdentityPayload(
        model_artifact_id="test_artifact",
        experiment_fingerprint="fp1",
        dataset_ids=("ds1",),
        universe_ids=("uv1",),
        code_commit="commit1",
        config_version="v1",
        feature_version="v1",
        representation_version="v1",
        portfolio_version="v1",
        cost_model_version="v1",
        risk_policy_version="v1",
        target_stage=PromotionTarget.PAPER,
        effective_time=effective_time,
        approving_authority="test_auth",
        evidence_reference="ref1",
    )

def dummy_event(state: PromotionState, effective_time: datetime) -> PromotionEvent:
    return PromotionEvent(
        promotion_event_id="evt1",
        payload=dummy_payload(effective_time),
        promotion_state=state,
        event_at=effective_time,
        reason="test"
    )

def test_evaluator_requires_paper_approved() -> None:
    evaluator = ProspectiveEvaluator()
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    evt = dummy_event(PromotionState.RESEARCH_ACCEPTED, t0)
    sim = SimulationResult(portfolio_version="v1", cost_version="v1", periods=())
    
    with pytest.raises(ProspectiveHoldoutError, match="non-PAPER_APPROVED"):
        evaluator.evaluate(evt, sim, t0)

def test_evaluator_checks_duration() -> None:
    evaluator = ProspectiveEvaluator(min_observation_days=14)
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    evt = dummy_event(PromotionState.PAPER_APPROVED, t0)
    sim = SimulationResult(portfolio_version="v1", cost_version="v1", periods=())
    
    # 10 days later -> incomplete
    t10 = t0 + timedelta(days=10)
    res = evaluator.evaluate(evt, sim, t10)
    assert not res.is_complete
    
    # 15 days later -> complete
    t15 = t0 + timedelta(days=15)
    res2 = evaluator.evaluate(evt, sim, t15)
    assert res2.is_complete

def test_evaluator_computes_returns_in_window() -> None:
    evaluator = ProspectiveEvaluator()
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    evt = dummy_event(PromotionState.PAPER_APPROVED, t0)
    
    # Periods at t0+1d, t0+5d, t0+20d
    p1 = SimulationPeriod(t0 + timedelta(days=1), Decimal("0.05"), Decimal("0.04"), Decimal("0.1"), Decimal("0.01"))
    p2 = SimulationPeriod(t0 + timedelta(days=5), Decimal("0.02"), Decimal("0.01"), Decimal("0.1"), Decimal("0.01"))
    p3 = SimulationPeriod(t0 + timedelta(days=20), Decimal("0.10"), Decimal("0.09"), Decimal("0.1"), Decimal("0.01"))
    
    sim = SimulationResult(portfolio_version="v1", cost_version="v1", periods=(p1, p2, p3))
    
    # Eval at t0+10d -> should only include p1, p2
    t10 = t0 + timedelta(days=10)
    res = evaluator.evaluate(evt, sim, t10)
    
    assert res.net_return == (Decimal("1.04") * Decimal("1.01")) - Decimal("1.0")
    assert not res.is_complete # 10 days < 14
