"""Tests for PROMO-001 Promotion Registry and state machine."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cryptofactors.promotion import (
    InvalidPromotionPayloadError,
    PromotionError,
    PromotionGateError,
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)


def valid_payload(
    model_artifact_id: str = "art_model_v1",
    target_stage: PromotionTarget = PromotionTarget.RESEARCH,
    evidence_reference: str = "rev_evidence_001",
    approving_authority: str = "Lead Quantitative Researcher",
    paper_observation_reference: str | None = None,
) -> PromotionIdentityPayload:
    return PromotionIdentityPayload(
        model_artifact_id=model_artifact_id,
        experiment_fingerprint="exp_fp_sha256_001",
        dataset_ids=("ds_market_bars_1h", "coingecko_universe"),
        universe_ids=("cmc_survivorship_universe",),
        code_commit="git_commit_sha_12345",
        config_version="cfg_v1.0.0",
        feature_version="feat_v2.1",
        representation_version="rep_time_bar_1h",
        portfolio_version="port_v1_costed",
        cost_model_version="cost_v1_binance",
        risk_policy_version="risk_lev1.0_w0.15_v1",
        target_stage=target_stage,
        effective_time=datetime.now(timezone.utc),
        approving_authority=approving_authority,
        evidence_reference=evidence_reference,
        paper_observation_reference=paper_observation_reference,
    )


def test_candidate_registration_starts_in_research_candidate() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        payload = valid_payload("art_v1")
        event = registry.register_candidate(payload, reason="New research model")

        assert event.promotion_state == PromotionState.RESEARCH_CANDIDATE
        assert registry.get_current_state("art_v1") == PromotionState.RESEARCH_CANDIDATE

        # New artifact version starts in RESEARCH_CANDIDATE and does not inherit prior state
        payload_v2 = valid_payload("art_v2")
        event_v2 = registry.register_candidate(payload_v2, reason="New research model version 2")
        assert event_v2.promotion_state == PromotionState.RESEARCH_CANDIDATE
        assert registry.get_current_state("art_v2") == PromotionState.RESEARCH_CANDIDATE


def test_missing_identity_field_is_rejected() -> None:
    with pytest.raises(InvalidPromotionPayloadError, match="code_commit must be a non-empty string"):
        PromotionIdentityPayload(
            model_artifact_id="art_v1",
            experiment_fingerprint="fp123",
            dataset_ids=("ds1",),
            universe_ids=("univ1",),
            code_commit="",  # Missing / empty
            config_version="cfg1",
            feature_version="f1",
            representation_version="r1",
            portfolio_version="p1",
            cost_model_version="c1",
            risk_policy_version="rp1",
            target_stage=PromotionTarget.RESEARCH,
            effective_time=datetime.now(timezone.utc),
            approving_authority="owner",
            evidence_reference="ev1",
        ).validate()


def test_paper_approved_without_review_reference_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        payload = valid_payload("art_v1", target_stage=PromotionTarget.RESEARCH)
        registry.register_candidate(payload)

        # Attempt transition to PAPER_APPROVED with empty evidence reference
        payload_invalid = valid_payload(
            "art_v1",
            target_stage=PromotionTarget.PAPER,
            evidence_reference=" ",
        )
        with pytest.raises(
            (PromotionGateError, InvalidPromotionPayloadError),
        ):
            registry.transition_state(
                payload_invalid,
                target_state=PromotionState.PAPER_APPROVED,
                reason="Promote to paper",
            )


def test_live_approved_without_owner_authority_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        # 1. Candidate
        payload_res = valid_payload("art_v1", target_stage=PromotionTarget.RESEARCH)
        registry.register_candidate(payload_res)

        # 2. Paper Approved
        payload_paper = valid_payload("art_v1", target_stage=PromotionTarget.PAPER)
        registry.transition_state(
            payload_paper,
            target_state=PromotionState.PAPER_APPROVED,
            reason="Approved for paper evaluation",
        )

        # 3. Live Approved without owner authority -> rejected
        payload_live_unauth = valid_payload(
            "art_v1",
            target_stage=PromotionTarget.LIVE,
            approving_authority="Jr Dev Hermes",
            paper_observation_reference="obs_14day_pass",
        )
        with pytest.raises(PromotionGateError, match="requires owner authority"):
            registry.transition_state(
                payload_live_unauth,
                target_state=PromotionState.LIVE_APPROVED,
                reason="Attempt live promotion",
            )

        # 4. Live Approved with owner authority and paper observation -> succeeds
        payload_live_ok = valid_payload(
            "art_v1",
            target_stage=PromotionTarget.LIVE,
            approving_authority="Owner Relay / Lead Engineer",
            paper_observation_reference="obs_14day_pass_verified",
        )
        event_live = registry.transition_state(
            payload_live_ok,
            target_state=PromotionState.LIVE_APPROVED,
            reason="Authorized for live deployment",
        )
        assert event_live.promotion_state == PromotionState.LIVE_APPROVED
        assert registry.get_current_state("art_v1") == PromotionState.LIVE_APPROVED


def test_append_only_history_and_terminal_states() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        payload = valid_payload("art_v1", target_stage=PromotionTarget.RESEARCH)
        registry.register_candidate(payload)

        # Transition to RESEARCH_ACCEPTED then REJECTED
        payload_acc = valid_payload("art_v1", target_stage=PromotionTarget.RESEARCH)
        registry.transition_state(
            payload_acc,
            target_state=PromotionState.RESEARCH_ACCEPTED,
            reason="Accepted scientific review",
        )

        payload_rej = valid_payload("art_v1", target_stage=PromotionTarget.RESEARCH)
        registry.transition_state(
            payload_rej,
            target_state=PromotionState.REJECTED,
            reason="Rejected due to high cost slippage",
        )

        assert registry.get_current_state("art_v1") == PromotionState.REJECTED

        # Attempt to transition out of terminal state REJECTED -> forbidden
        payload_promo = valid_payload("art_v1", target_stage=PromotionTarget.PAPER)
        with pytest.raises(PromotionGateError, match="Cannot transition from terminal state"):
            registry.transition_state(
                payload_promo,
                target_state=PromotionState.PAPER_APPROVED,
                reason="Try to revive rejected artifact",
            )

        # History is append-only and contains 3 events
        history = registry.list_history("art_v1")
        assert len(history) == 3
        states = [e.promotion_state for e in history]
        assert states == [
            PromotionState.RESEARCH_CANDIDATE,
            PromotionState.RESEARCH_ACCEPTED,
            PromotionState.REJECTED,
        ]


def test_serving_discovery_accessor() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        payload = valid_payload("art_v1")
        registry.register_candidate(payload)

        # Before paper approval -> get_active_promoted_artifact for PAPER fails closed
        with pytest.raises(PromotionError, match="is not PAPER_APPROVED"):
            registry.get_active_promoted_artifact("art_v1", PromotionTarget.PAPER)

        # Approve for paper
        payload_paper = valid_payload("art_v1", target_stage=PromotionTarget.PAPER)
        registry.transition_state(
            payload_paper,
            target_state=PromotionState.PAPER_APPROVED,
            reason="Paper approved",
        )

        # Now get_active_promoted_artifact for PAPER succeeds
        event = registry.get_active_promoted_artifact("art_v1", PromotionTarget.PAPER)
        assert event.promotion_state == PromotionState.PAPER_APPROVED

        # Get active for LIVE still fails closed
        with pytest.raises(PromotionError, match="is not LIVE_APPROVED"):
            registry.get_active_promoted_artifact("art_v1", PromotionTarget.LIVE)
