"""ARCH-001 regression: false-discovery candidate is archived and holdout is reserved."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "research"))
from archive_tsmom_14_3_false_discovery import (
    MODEL_ARTIFACT_ID,
    PASS_DATASET_ID,
    _reject_candidate,
    _write_holdout_reservation,
)

from cryptofactors.promotion import (
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)


def _paper_payload(effective_time: datetime) -> PromotionIdentityPayload:
    return PromotionIdentityPayload(
        model_artifact_id=MODEL_ARTIFACT_ID,
        experiment_fingerprint="ARCH-001:test",
        dataset_ids=(PASS_DATASET_ID, "coingecko_universe"),
        universe_ids=("cmc_survivorship_universe",),
        code_commit="MOMTS-001",
        config_version="cfg_tsmom_14_3_v1",
        feature_version="feat_tsmom_14_3_v1",
        representation_version="rep_time_bar_1d",
        portfolio_version="perp_ls_v1",
        cost_model_version="cost_v1_binance_spot",
        risk_policy_version="risk_lev1.0_w0.15_v1",
        target_stage=PromotionTarget.PAPER,
        effective_time=effective_time,
        approving_authority="Lead Quantitative Researcher",
        evidence_reference="TEST",
        paper_observation_reference=None,
        kill_switch_procedure=None,
    )


def test_reject_candidate_transitions_to_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        # Seed registry with PAPER_APPROVED state
        cand = _paper_payload(datetime(2024, 4, 1, tzinfo=timezone.utc))
        registry.register_candidate(cand, reason="test candidate")
        registry.transition_state(
            _paper_payload(datetime(2024, 4, 1, tzinfo=timezone.utc)),
            target_state=PromotionState.RESEARCH_ACCEPTED,
            reason="test accepted",
        )
        registry.transition_state(
            _paper_payload(datetime(2024, 4, 1, tzinfo=timezone.utc)),
            target_state=PromotionState.PAPER_APPROVED,
            reason="test paper approved",
        )
        assert registry.get_current_state(MODEL_ARTIFACT_ID) == PromotionState.PAPER_APPROVED

        # Reject via ARCH-001
        _reject_candidate(db_path)
        assert registry.get_current_state(MODEL_ARTIFACT_ID) == PromotionState.REJECTED

        history = registry.list_history(MODEL_ARTIFACT_ID)
        states = [e.promotion_state for e in history]
        assert states == [
            PromotionState.RESEARCH_CANDIDATE,
            PromotionState.RESEARCH_ACCEPTED,
            PromotionState.PAPER_APPROVED,
            PromotionState.REJECTED,
        ]


def test_reject_candidate_is_idempotent() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)
        cand = _paper_payload(datetime(2024, 4, 1, tzinfo=timezone.utc))
        registry.register_candidate(cand, reason="test candidate")
        registry.transition_state(
            _paper_payload(datetime(2024, 4, 1, tzinfo=timezone.utc)),
            target_state=PromotionState.REJECTED,
            reason="test rejected",
        )
        assert registry.get_current_state(MODEL_ARTIFACT_ID) == PromotionState.REJECTED

        _reject_candidate(db_path)
        assert registry.get_current_state(MODEL_ARTIFACT_ID) == PromotionState.REJECTED


def test_write_holdout_reservation() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "research"
        path = _write_holdout_reservation(output_dir)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["experiment_id"] == "ARCH-001"
        assert data["model_artifact_id"] == MODEL_ARTIFACT_ID
        assert data["canonical_dataset_id"] == PASS_DATASET_ID
        assert data["holdout"]["start"] == "2026-07-24T00:00:00+00:00"
        assert data["holdout"]["end"] is None
        assert data["contamination"]["fresh_data_required"] is True
        assert data["policy"]["pre_registration_required"] is True
        assert data["live_eligible"] is False


def test_rejected_terminal_state_forbids_further_transitions() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)
        cand = _paper_payload(datetime(2024, 4, 1, tzinfo=timezone.utc))
        registry.register_candidate(cand, reason="test candidate")
        registry.transition_state(
            _paper_payload(datetime(2024, 4, 1, tzinfo=timezone.utc)),
            target_state=PromotionState.REJECTED,
            reason="test rejected",
        )
        with pytest.raises(Exception):
            registry.transition_state(
                _paper_payload(datetime(2024, 4, 1, tzinfo=timezone.utc)),
                target_state=PromotionState.PAPER_APPROVED,
                reason="must not revive rejected artifact",
            )
