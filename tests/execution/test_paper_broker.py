"""Tests for EXEC-001 Paper Execution Runtime and PaperBroker."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cryptofactors.execution import (
    PaperBroker,
    PaperExecutionError,
    UnapprovedArtifactError,
)
from cryptofactors.promotion import (
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)


def create_approved_artifact(
    registry: PromotionRegistry,
    model_artifact_id: str = "art_approved_v1",
) -> None:
    payload_cand = PromotionIdentityPayload(
        model_artifact_id=model_artifact_id,
        experiment_fingerprint="exp_fp_123",
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
        effective_time=datetime.now(timezone.utc),
        approving_authority="Lead Quant",
        evidence_reference="rev_001",
    )
    registry.register_candidate(payload_cand)

    payload_paper = PromotionIdentityPayload(
        model_artifact_id=model_artifact_id,
        experiment_fingerprint="exp_fp_123",
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
        effective_time=datetime.now(timezone.utc),
        approving_authority="Lead Quant",
        evidence_reference="rev_001",
    )
    registry.transition_state(
        payload_paper,
        target_state=PromotionState.PAPER_APPROVED,
        reason="Approved for paper testing",
    )


def test_paper_broker_raises_error_for_unapproved_artifact() -> None:
    """Acceptance item #5: Assert PaperBroker raises UnapprovedArtifactError if artifact is not PAPER_APPROVED."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        # 1. Unregistered artifact -> raises UnapprovedArtifactError
        with pytest.raises(UnapprovedArtifactError, match="failed paper promotion gate"):
            PaperBroker("unregistered_art", registry)

        # 2. Registered only as RESEARCH_CANDIDATE -> raises UnapprovedArtifactError
        payload = PromotionIdentityPayload(
            model_artifact_id="art_cand_only",
            experiment_fingerprint="fp1",
            dataset_ids=("ds1",),
            universe_ids=("u1",),
            code_commit="c1",
            config_version="cfg1",
            feature_version="f1",
            representation_version="r1",
            portfolio_version="p1",
            cost_model_version="cm1",
            risk_policy_version="rp1",
            target_stage=PromotionTarget.RESEARCH,
            effective_time=datetime.now(timezone.utc),
            approving_authority="Quant",
            evidence_reference="ev1",
        )
        registry.register_candidate(payload)

        with pytest.raises(UnapprovedArtifactError, match="failed paper promotion gate"):
            PaperBroker("art_cand_only", registry)


def test_paper_broker_initialization_and_rebalance() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)
        create_approved_artifact(registry, "art_approved_v1")

        broker = PaperBroker(
            "art_approved_v1",
            registry,
            initial_cash=100_000.0,
            fee_rate=0.0005,  # 5 bps
            slippage_rate=0.0005,  # 5 bps
        )

        assert broker.get_cash() == 100_000.0
        assert broker.get_positions() == {}

        prices = {"BTC": 50_000.0, "ETH": 3_000.0}
        t0 = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)

        # Rebalance: 50% BTC, 30% ETH
        target_weights = {"BTC": 0.5, "ETH": 0.3}
        trades = broker.rebalance(target_weights, prices, t0)

        assert len(trades) == 2
        positions = broker.get_positions()
        assert "BTC" in positions
        assert "ETH" in positions
        assert positions["BTC"] > 0
        assert positions["ETH"] > 0

        # Equity after cost deduction should be slightly less than 100,000
        eq = broker.get_equity(prices)
        assert 99_800.0 < eq < 100_000.0


def test_leverage_limit_enforced() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)
        create_approved_artifact(registry, "art_approved_v1")

        broker = PaperBroker("art_approved_v1", registry)
        prices = {"BTC": 50_000.0, "ETH": 3_000.0}
        t0 = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)

        # Leverage > 1.0 (0.8 + 0.5 = 1.3)
        invalid_weights = {"BTC": 0.8, "ETH": 0.5}
        with pytest.raises(PaperExecutionError, match="exceeds 1.0 limit"):
            broker.rebalance(invalid_weights, prices, t0)
