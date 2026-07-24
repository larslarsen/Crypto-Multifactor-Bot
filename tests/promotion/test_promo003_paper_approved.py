"""PROMO-003 regression: frozen tsmom_14_3 reaches PAPER_APPROVED with PASS dataset."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cryptofactors.promotion import (
    PromotionError,
    PromotionGateError,
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)

PASS_DATASET_ID = "ds_0cb6415fa79119bf5317c124e9da2f0d4953b9a8d119aae45e2589ba716c5aaa"
MODEL_ARTIFACT_ID = "mod_tsmom_14_3_v1"


def _payload(
    target_stage: PromotionTarget,
    evidence_reference: str,
    effective_time: datetime | None = None,
    approving_authority: str = "Lead Quantitative Researcher",
) -> PromotionIdentityPayload:
    return PromotionIdentityPayload(
        model_artifact_id=MODEL_ARTIFACT_ID,
        experiment_fingerprint="PROMO-003:tsmom_14_3:frozen:v1",
        dataset_ids=(PASS_DATASET_ID, "coingecko_universe"),
        universe_ids=("cmc_survivorship_universe",),
        code_commit="MOMTS-001",
        config_version="cfg_tsmom_14_3_v1",
        feature_version="feat_tsmom_14_3_v1",
        representation_version="rep_time_bar_1d",
        portfolio_version="perp_ls_v1",
        cost_model_version="cost_v1_binance_spot",
        risk_policy_version="risk_lev1.0_w0.15_v1",
        target_stage=target_stage,
        effective_time=effective_time or datetime.now(timezone.utc),
        approving_authority=approving_authority,
        evidence_reference=evidence_reference,
        paper_observation_reference=None,
        kill_switch_procedure=None,
    )


def test_promo003_frozen_tsmom_14_3_reaches_paper_approved() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        eff = datetime(2024, 4, 1, tzinfo=timezone.utc)

        # RESEARCH_CANDIDATE
        registry.register_candidate(
            _payload(PromotionTarget.RESEARCH, "REVIEW-0200", eff),
            reason="PROMO-003: register frozen tsmom_14_3 candidate",
        )
        assert registry.get_current_state(MODEL_ARTIFACT_ID) == PromotionState.RESEARCH_CANDIDATE

        # RESEARCH_ACCEPTED
        registry.transition_state(
            _payload(PromotionTarget.RESEARCH, "REVIEW-0200 / REVIEW-0202", eff),
            target_state=PromotionState.RESEARCH_ACCEPTED,
            reason="PROMO-003: scientific review accepted",
        )
        assert registry.get_current_state(MODEL_ARTIFACT_ID) == PromotionState.RESEARCH_ACCEPTED

        # PAPER_APPROVED
        registry.transition_state(
            _payload(PromotionTarget.PAPER, "PAPER-009 / REVIEW-0202", eff),
            target_state=PromotionState.PAPER_APPROVED,
            reason="PROMO-003: PAPER_APPROVED on PASS canonical bars",
        )
        assert registry.get_current_state(MODEL_ARTIFACT_ID) == PromotionState.PAPER_APPROVED

        history = registry.list_history(MODEL_ARTIFACT_ID)
        assert len(history) == 3
        assert [e.promotion_state for e in history] == [
            PromotionState.RESEARCH_CANDIDATE,
            PromotionState.RESEARCH_ACCEPTED,
            PromotionState.PAPER_APPROVED,
        ]

        # Fail closed: LIVE_APPROVED is rejected without owner authority
        with pytest.raises(PromotionGateError, match="requires owner authority"):
            registry.transition_state(
                _payload(
                    PromotionTarget.LIVE,
                    "PAPER-009 / REVIEW-0202",
                    eff,
                    approving_authority="Lead Quantitative Researcher",
                ),
                target_state=PromotionState.LIVE_APPROVED,
                reason="PROMO-003: must not reach LIVE",
            )

        # Serving discovery returns PAPER_APPROVED
        active = registry.get_active_promoted_artifact(MODEL_ARTIFACT_ID, PromotionTarget.PAPER)
        assert active.promotion_state == PromotionState.PAPER_APPROVED

        # LIVE serving discovery fails closed
        with pytest.raises(PromotionError, match="is not LIVE_APPROVED"):
            registry.get_active_promoted_artifact(MODEL_ARTIFACT_ID, PromotionTarget.LIVE)


def test_promo003_pinned_pass_dataset_is_identity_field() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        eff = datetime(2024, 4, 1, tzinfo=timezone.utc)
        payload = _payload(PromotionTarget.RESEARCH, "REVIEW-0200", eff)
        registry.register_candidate(payload)

        latest = registry.get_latest_event(MODEL_ARTIFACT_ID)
        assert latest is not None
        assert PASS_DATASET_ID in latest.payload.dataset_ids
