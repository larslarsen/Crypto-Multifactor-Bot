"""HARDEN-001 — Paper Path Hardening & Verification Report Generator.

Generates structured hardening reports capturing data mode (synthetic vs real_asof),
paper session equity metrics, ops gate status, venue connectivity probe results,
and explicit live eligibility status (always live_eligible=False per policy).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from cryptofactors.execution.models import PaperOpsStatus

UTC: Final[timezone] = timezone.utc
DEFAULT_HARDEN_REPORT_PATH = Path("research/sprint_004/10_PAPER_HARDEN_REPORT.json")


@dataclass(frozen=True, slots=True)
class PaperHardenReport:
    """Paper trading hardening and verification report artifact (HARDEN-001)."""

    model_artifact_id: str
    data_mode: str  # "synthetic" or "real_asof"
    promotion_state: str
    gate_status: str  # "OK" or "FAIL"
    initial_cash: float
    final_equity: float
    total_net_return: float
    paper_observation_reference: str | None
    venue_probe_result: dict[str, Any] | None
    live_eligible: bool = False  # ALWAYS False per HARDEN-001 policy
    report_generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def build_harden_report(
    ops_status: PaperOpsStatus,
    *,
    data_mode: str = "synthetic",
    venue_probe_result: dict[str, Any] | None = None,
) -> PaperHardenReport:
    """Build PaperHardenReport from PaperOpsStatus and probe results."""
    mode_clean = str(data_mode).strip().lower()
    if mode_clean not in ("synthetic", "real_asof"):
        mode_clean = "synthetic"

    return PaperHardenReport(
        model_artifact_id=ops_status.model_artifact_id,
        data_mode=mode_clean,
        promotion_state=ops_status.promotion_state,
        gate_status=ops_status.gate_status,
        initial_cash=ops_status.initial_cash,
        final_equity=ops_status.last_equity,
        total_net_return=ops_status.total_net_return,
        paper_observation_reference=ops_status.paper_observation_reference,
        venue_probe_result=venue_probe_result,
        live_eligible=False,  # HARDEN-001 policy: LIVE is strictly blocked
        report_generated_at=datetime.now(UTC),
    )


def write_harden_report_artifact(
    report: PaperHardenReport,
    output_path: Path | str = DEFAULT_HARDEN_REPORT_PATH,
) -> Path:
    """Write PaperHardenReport to JSON file artifact."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {
        "model_artifact_id": report.model_artifact_id,
        "data_mode": report.data_mode,
        "promotion_state": report.promotion_state,
        "gate_status": report.gate_status,
        "initial_cash": report.initial_cash,
        "final_equity": report.final_equity,
        "total_net_return": report.total_net_return,
        "paper_observation_reference": report.paper_observation_reference,
        "venue_probe_result": report.venue_probe_result,
        "live_eligible": report.live_eligible,  # false
        "report_generated_at": report.report_generated_at.isoformat(),
    }

    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p
