#!/usr/bin/env python3
"""PROMO-003 — PAPER_APPROVED promotion for frozen tsmom_14_3.

Registers model artifact `mod_tsmom_14_3_v1` (tsmom_14_3, lookback=14, skip=3)
in the Promotion Registry and advances it through the ADR-0008 lifecycle:

    RESEARCH_CANDIDATE → RESEARCH_ACCEPTED → PAPER_APPROVED

The script is idempotent: if the artifact is already at or beyond PAPER_APPROVED,
it records the final state and writes the promotion artifact without making
further transitions. It explicitly fails closed and does NOT transition to
LIVE_APPROVED.

Pins the DATA-005 PASS canonical dataset. Produces
research/sprint_004/27_TSMOM_14_3_PAPER_PROMOTION.json.

live_eligible: false. No LIVE. No parameter changes.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptofactors.promotion import (
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)

UTC = timezone.utc

MODEL_ARTIFACT_ID = "mod_tsmom_14_3_v1"
FACTOR_ID = "tsmom_14_3"
LOOKBACK_DAYS = 14
SKIP_DAYS = 3

PASS_DATASET_ID = "ds_0cb6415fa79119bf5317c124e9da2f0d4953b9a8d119aae45e2589ba716c5aaa"
PAPER_008_ARTIFACT = "research/sprint_004/24_TSMOM_14_3_PAPER_SESSION.json"
PAPER_009_ARTIFACT = "research/sprint_004/26_TSMOM_14_3_PASS_BARS_PAPER.json"

EXPERIMENT_REGISTRY = Path("research/sprint_004/experiment_registry.csv")


def _base_payload(
    target_stage: PromotionTarget,
    evidence_reference: str,
    effective_time: datetime,
    approving_authority: str = "Lead Quantitative Researcher",
) -> PromotionIdentityPayload:
    """Build the immutable identity payload for mod_tsmom_14_3_v1."""
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
        effective_time=effective_time,
        approving_authority=approving_authority,
        evidence_reference=evidence_reference,
        paper_observation_reference=None,
        kill_switch_procedure=None,
    )


def _advance_to_paper_approved(
    registry: PromotionRegistry,
    effective_time: datetime,
) -> PromotionState:
    """Advance the artifact through the required states, idempotently."""
    current = registry.get_current_state(MODEL_ARTIFACT_ID)

    if current is None:
        candidate = _base_payload(
            PromotionTarget.RESEARCH,
            evidence_reference="REVIEW-0200",
            effective_time=effective_time,
        )
        registry.register_candidate(
            candidate,
            reason="PROMO-003: register frozen tsmom_14_3 candidate",
        )
        current = PromotionState.RESEARCH_CANDIDATE
        print("PROMO-003: registered RESEARCH_CANDIDATE", file=sys.stderr)

    if current == PromotionState.RESEARCH_CANDIDATE:
        accepted = _base_payload(
            PromotionTarget.RESEARCH,
            evidence_reference="REVIEW-0200 / REVIEW-0202",
            effective_time=effective_time,
        )
        registry.transition_state(
            accepted,
            target_state=PromotionState.RESEARCH_ACCEPTED,
            reason="PROMO-003: scientific review accepted for frozen tsmom_14_3",
        )
        current = PromotionState.RESEARCH_ACCEPTED
        print("PROMO-003: advanced to RESEARCH_ACCEPTED", file=sys.stderr)

    if current == PromotionState.RESEARCH_ACCEPTED:
        paper = _base_payload(
            PromotionTarget.PAPER,
            evidence_reference="PAPER-009 / REVIEW-0202",
            effective_time=effective_time,
        )
        registry.transition_state(
            paper,
            target_state=PromotionState.PAPER_APPROVED,
            reason="PROMO-003: PAPER_APPROVED on PASS canonical bars",
        )
        current = PromotionState.PAPER_APPROVED
        print("PROMO-003: advanced to PAPER_APPROVED", file=sys.stderr)

    if current == PromotionState.PAPER_APPROVED:
        print("PROMO-003: already at PAPER_APPROVED", file=sys.stderr)
    elif current in (PromotionState.LIVE_APPROVED, PromotionState.LIVE_SUSPENDED):
        raise RuntimeError(
            f"PROMO-003: forbidden pre-existing state {current.value}; "
            "this ticket must not promote to LIVE."
        )
    else:
        raise RuntimeError(
            f"PROMO-003: unexpected current state {current.value}; "
            "expected to reach PAPER_APPROVED."
        )

    return current


def _load_paper_009_session() -> dict[str, Any]:
    path = Path(PAPER_009_ARTIFACT)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "total_net_return": data.get("session", {}).get("total_net_return"),
        "final_equity": data.get("session", {}).get("final_equity"),
        "canonical_dataset_id": data.get("canonical_dataset_id"),
        "canonical_dataset_quality_status": data.get("canonical_dataset_quality_status"),
    }


def _build_trail(registry: PromotionRegistry) -> list[dict[str, Any]]:
    """Serialize the append-only promotion history for the artifact."""
    events = registry.list_history(MODEL_ARTIFACT_ID)
    return [
        {
            "event_index": idx,
            "promotion_event_id": e.promotion_event_id,
            "promotion_state": e.promotion_state.value,
            "target_stage": e.payload.target_stage.value,
            "event_at": e.event_at.isoformat(),
            "reason": e.reason,
            "effective_time": e.payload.effective_time.isoformat(),
            "approving_authority": e.payload.approving_authority,
            "evidence_reference": e.payload.evidence_reference,
            "dataset_ids": list(e.payload.dataset_ids),
        }
        for idx, e in enumerate(events)
    ]


def _append_registry_row(artifact_path: Path) -> None:
    """Append a PROMO-003 row to experiment_registry.csv (idempotent)."""
    if not EXPERIMENT_REGISTRY.exists():
        return

    artifacts_json = json.dumps(
        {"promotion_artifact": str(artifact_path)},
        separators=(",", ":"),
        sort_keys=True,
    )
    new_row = {
        "experiment_id": "PROMO-003",
        "status": "EXECUTED",
        "artifacts_json": artifacts_json,
        "generated_at": datetime.now(UTC).isoformat(),
    }

    rows: list[dict[str, str]] = []
    if EXPERIMENT_REGISTRY.exists():
        with EXPERIMENT_REGISTRY.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

    rows = [r for r in rows if r.get("experiment_id") != "PROMO-003"]
    rows.append(new_row)

    with EXPERIMENT_REGISTRY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["experiment_id", "status", "artifacts_json", "generated_at"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"PROMO-003 row written to {EXPERIMENT_REGISTRY}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="PROMO-003 PAPER_APPROVED promotion")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--output-dir", type=str, default="research/sprint_004")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    effective_time = datetime.now(UTC)
    registry = PromotionRegistry(db_path)

    final_state = _advance_to_paper_approved(registry, effective_time)
    assert final_state == PromotionState.PAPER_APPROVED, f"final state must be PAPER_APPROVED, got {final_state}"

    latest_event = registry.get_latest_event(MODEL_ARTIFACT_ID)
    if latest_event is None:
        raise RuntimeError("PROMO-003: latest promotion event missing")

    trail = _build_trail(registry)
    paper_009 = _load_paper_009_session()

    artifact: dict[str, Any] = {
        "experiment_id": "PROMO-003",
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "factor_id": FACTOR_ID,
        "lookback_days": LOOKBACK_DAYS,
        "skip_days": SKIP_DAYS,
        "canonical_dataset_id": PASS_DATASET_ID,
        "canonical_dataset_quality_status": "PASS",
        "canonical_dataset_quality_note": (
            "Pinned PASS canonical dataset from DATA-005 (BAR-001 native 1d daily promotion)."
        ),
        "promotion_state": {
            "final_state": final_state.value,
            "final_event_id": latest_event.promotion_event_id,
            "final_event_at": latest_event.event_at.isoformat(),
        },
        "promotion_trail": trail,
        "paper_009_session": {
            "artifact_path": PAPER_009_ARTIFACT,
            "total_net_return": paper_009.get("total_net_return"),
            "final_equity": paper_009.get("final_equity"),
        },
        "candidate_frozen": True,
        "candidate_frozen_note": (
            "tsmom_14_3 lookback=14/skip=3 remains frozen. No further lookback/skip "
            "optimization or re-selection on this path is permitted without a new ticket "
            "and reviewer authorization."
        ),
        "live_eligible": False,
        "live_eligible_note": (
            "PROMO-003 is PAPER_APPROVED only. LIVE_APPROVED is explicitly out of scope; "
            "multiple-testing / selection-path risk and owner policy still block live promotion."
        ),
        "cross_references": [
            "research/sprint_004/24_TSMOM_14_3_PAPER_SESSION.json",
            "research/sprint_004/25_QUALITY_CLEARED_BARS_REPORT.json",
            "research/sprint_004/26_TSMOM_14_3_PASS_BARS_PAPER.json",
        ],
        "prior_artifacts": [
            "research/sprint_004/13_REAL_PAPER_SESSION.json",
            "research/sprint_004/14_RISK_COMPLIANT_PAPER_SESSION.json",
            "research/sprint_004/15_MOMTS_RISK_DIAGNOSIS.json",
            "research/sprint_004/16_MOMTS_LONG_SESSION.json",
            "research/sprint_004/17_NEUTRAL_RISK_SESSION.json",
            "research/sprint_004/18_TSMOM_GRID_RESULTS.json",
            "research/sprint_004/19_TSMOM_OOS_VALIDATION.json",
            "research/sprint_004/20_EXTENDED_HISTORY_REPORT.json",
            "research/sprint_004/21_TSMOM_EXTENDED_OOS.json",
            "research/sprint_004/22_TSMOM_14_0_PAPER_SESSION.json",
            "research/sprint_004/23_TSMOM_FULLWINDOW_SCREEN.json",
            "research/sprint_004/24_TSMOM_14_3_PAPER_SESSION.json",
            "research/sprint_004/25_QUALITY_CLEARED_BARS_REPORT.json",
            "research/sprint_004/26_TSMOM_14_3_PASS_BARS_PAPER.json",
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }

    out_path = output_dir / "27_TSMOM_14_3_PAPER_PROMOTION.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Promotion artifact written to {out_path}", file=sys.stderr)

    _append_registry_row(out_path)

    print(json.dumps(artifact, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
