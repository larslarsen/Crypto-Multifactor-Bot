#!/usr/bin/env python3
"""ARCH-001 — Archive false-discovery candidate and reserve holdout.

1. Marks mod_tsmom_14_3_v1 as REJECTED in the Promotion Registry (terminal state).
2. Adds an `archived` note to the candidate-supporting artifacts without deleting them.
3. Writes 29_HOLDOUT_RESERVATION.json documenting that the entire existing PASS
   dataset is contaminated by grid selection and that the only valid holdout is
   fresh data after 2026-07-23.

Does not create new factors or run backtests. No LIVE.
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
PASS_DATASET_ID = "ds_0cb6415fa79119bf5317c124e9da2f0d4953b9a8d119aae45e2589ba716c5aaa"

ARTIFACTS_TO_ARCHIVE = [
    Path("research/sprint_004/24_TSMOM_14_3_PAPER_SESSION.json"),
    Path("research/sprint_004/26_TSMOM_14_3_PASS_BARS_PAPER.json"),
    Path("research/sprint_004/27_TSMOM_14_3_PAPER_PROMOTION.json"),
    Path("research/sprint_004/28_MULTIPLE_TESTING_ANALYSIS.json"),
]

EXPERIMENT_REGISTRY = Path("research/sprint_004/experiment_registry.csv")


def _archive_artifacts() -> None:
    """Add additive archived metadata to candidate-supporting artifacts."""
    archive_note = (
        "ARCH-001: mod_tsmom_14_3_v1 has been rejected as a false discovery "
        "following EXP-008 multiple-testing analysis. This artifact is preserved "
        "for audit and reproducibility but is no longer valid evidence for LIVE promotion."
    )
    for path in ARTIFACTS_TO_ARCHIVE:
        if not path.exists():
            print(f"Warning: artifact not found, skipping {path}", file=sys.stderr)
            continue

        data = json.loads(path.read_text(encoding="utf-8"))
        data["archived"] = True
        data["archive_note"] = archive_note
        data["archived_at"] = datetime.now(UTC).isoformat()
        data["archived_by_ticket"] = "ARCH-001"
        data["cross_references"] = sorted(
            set(data.get("cross_references", []) + ["research/sprint_004/29_HOLDOUT_RESERVATION.json"])
        )
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Archived note added to {path}", file=sys.stderr)


def _reject_candidate(db_path: Path) -> None:
    """Transition mod_tsmom_14_3_v1 to REJECTED (terminal) in the Promotion Registry."""
    registry = PromotionRegistry(db_path)
    current = registry.get_current_state(MODEL_ARTIFACT_ID)
    if current is None:
        raise RuntimeError(f"{MODEL_ARTIFACT_ID} is not registered in the Promotion Registry")
    if current in (PromotionState.REJECTED, PromotionState.RETIRED):
        print(f"PROMO-003: already in terminal state {current.value}", file=sys.stderr)
        return

    payload = PromotionIdentityPayload(
        model_artifact_id=MODEL_ARTIFACT_ID,
        experiment_fingerprint="ARCH-001:archive:false_discovery",
        dataset_ids=(PASS_DATASET_ID, "coingecko_universe"),
        universe_ids=("cmc_survivorship_universe",),
        code_commit="MOMTS-001",
        config_version="cfg_tsmom_14_3_v1",
        feature_version="feat_tsmom_14_3_v1",
        representation_version="rep_time_bar_1d",
        portfolio_version="perp_ls_v1",
        cost_model_version="cost_v1_binance_spot",
        risk_policy_version="risk_lev1.0_w0.15_v1",
        target_stage=PromotionTarget.RESEARCH,
        effective_time=datetime.now(UTC),
        approving_authority="Lead Quantitative Researcher",
        evidence_reference="EXP-008 / REVIEW-0204",
        paper_observation_reference=None,
        kill_switch_procedure=None,
    )
    registry.transition_state(
        payload,
        target_state=PromotionState.REJECTED,
        reason="ARCH-001: false discovery rejected after multiple-testing analysis",
    )
    print(f"ARCH-001: transitioned {MODEL_ARTIFACT_ID} to REJECTED", file=sys.stderr)


def _write_holdout_reservation(output_dir: Path) -> Path:
    """Write the holdout reservation artifact."""
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact: dict[str, Any] = {
        "experiment_id": "ARCH-001",
        "data_mode": "real_asof",
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "canonical_dataset_id": PASS_DATASET_ID,
        "dataset_quality_status": "PASS",
        "holdout": {
            "start": "2026-07-24T00:00:00+00:00",
            "end": None,
            "end_note": "Open-ended: holdout consists of all future bars after the last contaminated date.",
        },
        "contamination": {
            "contaminated_start": "2024-01-01T00:00:00+00:00",
            "contaminated_end": "2026-07-23T00:00:00+00:00",
            "contamination_note": (
                "Every bar through 2026-07-23 was used in one or more of: grid search "
                "(EXP-004/EXP-008), full-window selection (EXP-007), formal paper sessions "
                "(PAPER-008/PAPER-009), promotion evidence (PROMO-003), and the multiple-testing "
                "analysis (EXP-008). The dataset is therefore fully contaminated for the purpose "
                "of selecting or validating a TSMOM-style candidate. Any future single-hypothesis "
                "test must use data from 2026-07-24 onward, or a fresh data stream."
            ),
            "fresh_data_required": True,
        },
        "policy": {
            "no_exploration_before_holdout": True,
            "policy_note": (
                "No new factor exploration, grid search, or parameter tuning may be performed on "
                "the contaminated window (2024-01-01 -> 2026-07-23). A pre-registered single-hypothesis "
                "test (see tickets/templates/PRE_REGISTERED_TEST.md) must be filed and accepted before "
                "any code touches the holdout data."
            ),
            "pre_registration_required": True,
        },
        "live_eligible": False,
        "live_eligible_note": (
            "ARCH-001 establishes the methodological reset. LIVE is not authorized; the prior candidate "
            "is rejected and any future candidate must pass a pre-registered holdout test."
        ),
        "cross_references": [
            "research/sprint_004/24_TSMOM_14_3_PAPER_SESSION.json",
            "research/sprint_004/26_TSMOM_14_3_PASS_BARS_PAPER.json",
            "research/sprint_004/27_TSMOM_14_3_PAPER_PROMOTION.json",
            "research/sprint_004/28_MULTIPLE_TESTING_ANALYSIS.json",
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
            "research/sprint_004/27_TSMOM_14_3_PAPER_PROMOTION.json",
            "research/sprint_004/28_MULTIPLE_TESTING_ANALYSIS.json",
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }

    out_path = output_dir / "29_HOLDOUT_RESERVATION.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Holdout reservation written to {out_path}", file=sys.stderr)
    return out_path


def _append_registry_row(artifact_path: Path) -> None:
    """Append an ARCH-001 row to experiment_registry.csv (idempotent)."""
    if not EXPERIMENT_REGISTRY.exists():
        return

    artifacts_json = json.dumps(
        {"archive_artifact": str(artifact_path)},
        separators=(",", ":"),
        sort_keys=True,
    )
    new_row = {
        "experiment_id": "ARCH-001",
        "status": "EXECUTED",
        "artifacts_json": artifacts_json,
        "generated_at": datetime.now(UTC).isoformat(),
    }

    rows: list[dict[str, str]] = []
    if EXPERIMENT_REGISTRY.exists():
        with EXPERIMENT_REGISTRY.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

    rows = [r for r in rows if r.get("experiment_id") != "ARCH-001"]
    rows.append(new_row)

    with EXPERIMENT_REGISTRY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["experiment_id", "status", "artifacts_json", "generated_at"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"ARCH-001 row written to {EXPERIMENT_REGISTRY}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="ARCH-001 archive false discovery and reserve holdout")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--output-dir", type=str, default="research/sprint_004")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    output_dir = Path(args.output_dir)

    _archive_artifacts()
    _reject_candidate(db_path)
    holdout_path = _write_holdout_reservation(output_dir)
    _append_registry_row(holdout_path)

    print(json.dumps({
        "ticket": "ARCH-001",
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "final_state": PromotionState.REJECTED.value,
        "holdout_artifact": str(holdout_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
