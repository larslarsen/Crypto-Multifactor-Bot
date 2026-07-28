"""REVIEW-0250 — every affected run artifact must persist its binding fingerprint.

A run artifact that omits the binding evidence cannot prove which universe, which
bar panel, or which as-of coverage controlled the decision. These are structural
regressions over the 11 paper/experiment entrypoints plus the paper loop, so a new
output builder cannot quietly ship without evidence.
"""

import ast
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from cryptofactors.execution import FactorDrivenPaperLoop
from cryptofactors.promotion import (
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)
from cryptofactors.universe.binding import (
    BINDING_EVIDENCE_KEY,
    REQUIRED_BINDING_EVIDENCE_FIELDS,
    UniverseBindingError,
    binding_evidence,
    validate_binding_evidence,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def affected_entrypoints() -> list[Path]:
    """Every script that resolves membership through the binding."""
    return sorted(
        p for p in SCRIPTS_DIR.rglob("*.py")
        if "load_paper_universe_binding" in p.read_text(encoding="utf-8")
    )


# --------------------------------------------------------------------------- #
# the evidence contract itself
# --------------------------------------------------------------------------- #

class TestEvidenceContract:
    def test_the_required_field_set_is_complete(self) -> None:
        """REVIEW-0250 names universe id, bar-panel id, policy, code version,
        decision time, and coverage."""
        assert {
            "universe_dataset_id",
            "bar_panel_dataset_id",
            "survivorship_policy",
            "universe_code_version",
            "decision_time",
        } <= REQUIRED_BINDING_EVIDENCE_FIELDS
        coverage = {"eligible_count", "with_bars_count", "excluded_dead_count", "panel_count"}
        assert coverage <= REQUIRED_BINDING_EVIDENCE_FIELDS

    @pytest.mark.parametrize("dropped", sorted(REQUIRED_BINDING_EVIDENCE_FIELDS))
    def test_dropping_any_required_field_is_refused(self, dropped: str) -> None:
        payload = dict.fromkeys(REQUIRED_BINDING_EVIDENCE_FIELDS, "x")
        del payload[dropped]
        with pytest.raises(UniverseBindingError, match="missing required fields"):
            validate_binding_evidence(payload)

    @pytest.mark.parametrize("nulled", sorted(REQUIRED_BINDING_EVIDENCE_FIELDS))
    def test_a_null_required_field_is_refused(self, nulled: str) -> None:
        payload: dict[str, Any] = dict.fromkeys(REQUIRED_BINDING_EVIDENCE_FIELDS, "x")
        payload[nulled] = None
        with pytest.raises(UniverseBindingError, match="null required fields"):
            validate_binding_evidence(payload)

    def test_a_complete_payload_passes(self) -> None:
        validate_binding_evidence(dict.fromkeys(REQUIRED_BINDING_EVIDENCE_FIELDS, "x"))


# --------------------------------------------------------------------------- #
# the 11 entrypoints
# --------------------------------------------------------------------------- #

class TestEntrypointCoverage:
    def test_all_eleven_entrypoints_are_discovered(self) -> None:
        assert len(affected_entrypoints()) == 11

    @pytest.mark.parametrize(
        "script", affected_entrypoints(), ids=lambda p: p.name
    )
    def test_every_entrypoint_emits_binding_evidence(self, script: Path) -> None:
        """Each output builder must write the evidence key somewhere."""
        source = script.read_text(encoding="utf-8")
        assert BINDING_EVIDENCE_KEY in source, (
            f"{script.name} builds a run artifact without {BINDING_EVIDENCE_KEY}"
        )

    @pytest.mark.parametrize(
        "script", affected_entrypoints(), ids=lambda p: p.name
    )
    def test_every_entrypoint_parses(self, script: Path) -> None:
        """The injected evidence must not have broken any builder."""
        ast.parse(script.read_text(encoding="utf-8"), filename=str(script))

    def test_grid_and_fold_builders_emit_per_cell_evidence(self) -> None:
        """Grid cells and train/test folds each need their own decision-time evidence."""
        expected = {
            "run_tsmom_grid.py",
            "run_tsmom_extended_oos.py",
            "run_tsmom_oos_validation.py",
            "run_tsmom_fullwindow_screen.py",
            "run_multiple_testing_analysis.py",
        }
        found = {
            p.name for p in affected_entrypoints()
            if 'cell["universe_binding"]' in p.read_text(encoding="utf-8")
        }
        assert expected <= found, f"missing per-cell evidence: {sorted(expected - found)}"


# --------------------------------------------------------------------------- #
# paper loop persistence
# --------------------------------------------------------------------------- #

class _Binding:
    universe_dataset_id = "ds_universe"
    bar_panel_dataset_id = "ds_bars"
    survivorship_policy = "test_policy"
    universe_code_version = "v3"

    def __init__(self, symbols: tuple[str, ...] = ("XBTUSD", "ETHUSD")) -> None:
        self.symbols = symbols

    def universe_at(self, decision_time: datetime) -> frozenset[str]:
        return frozenset(self.symbols)

    def coverage_report(self, decision_time: datetime) -> dict[str, Any]:
        return {}

    def binding_fingerprint(self, decision_time: datetime) -> dict[str, Any]:
        return {
            "universe_dataset_id": self.universe_dataset_id,
            "bar_panel_dataset_id": self.bar_panel_dataset_id,
            "survivorship_policy": self.survivorship_policy,
            "universe_code_version": self.universe_code_version,
            "decision_time": decision_time.isoformat(),
            "eligible_count": len(self.symbols),
            "with_bars_count": len(self.symbols),
            "excluded_dead_count": 0,
            "panel_count": len(self.symbols),
        }


class _Factor:
    factor_id = "static"

    def compute(self, universe: Any, decision_time: datetime) -> Any:
        class Frame:
            def __init__(self) -> None:
                self.values = [
                    type("FV", (), {"instrument_id": s, "score": 1.0})() for s in universe
                ]
        return Frame()


def _promoted_registry(tmp_path: Path, artifact_id: str) -> PromotionRegistry:
    registry = PromotionRegistry(tmp_path / "registry.db")
    payload = PromotionIdentityPayload(
        model_artifact_id=artifact_id,
        experiment_fingerprint="fp",
        dataset_ids=("ds1",),
        universe_ids=("cmc_survivorship_universe",),
        code_commit="c1",
        config_version="cfg1",
        feature_version="f1",
        representation_version="r1",
        portfolio_version="p1",
        cost_model_version="cost1",
        risk_policy_version="risk1",
        target_stage=PromotionTarget.PAPER,
        effective_time=datetime(2026, 1, 1, tzinfo=UTC),
        approving_authority="Lead Quant",
        evidence_reference="ref",
    )
    registry.register_candidate(payload)
    registry.transition_state(payload, PromotionState.PAPER_APPROVED, reason="ok")
    return registry


class TestPaperLoopPersistsPerDecisionEvidence:
    def test_every_period_log_carries_a_complete_fingerprint(self, tmp_path: Path) -> None:
        loop = FactorDrivenPaperLoop(
            model_artifact_id="mod_ev",
            promotion_registry=_promoted_registry(tmp_path, "mod_ev"),
            factor=_Factor(),
        )
        decisions = [
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 8, tzinfo=UTC),
            datetime(2026, 1, 15, tzinfo=UTC),
        ]
        res = loop.run_loop(
            universe_binding=_Binding(),
            decision_times=decisions,
            get_prices_at=lambda dt, univ: dict.fromkeys(univ, 100.0),
        )
        assert len(res.period_logs) == len(decisions)
        for log, dt in zip(res.period_logs, decisions, strict=True):
            validate_binding_evidence(log.binding_fingerprint)
            assert log.binding_fingerprint["decision_time"] == dt.isoformat(), (
                "each decision must record its own decision time, not the session's"
            )

    def test_the_fingerprint_is_not_shared_between_decisions(self, tmp_path: Path) -> None:
        """A single session-level identity cannot prove per-decision membership."""
        loop = FactorDrivenPaperLoop(
            model_artifact_id="mod_ev2",
            promotion_registry=_promoted_registry(tmp_path, "mod_ev2"),
            factor=_Factor(),
        )
        res = loop.run_loop(
            universe_binding=_Binding(),
            decision_times=[
                datetime(2026, 2, 1, tzinfo=UTC),
                datetime(2026, 2, 8, tzinfo=UTC),
            ],
            get_prices_at=lambda dt, univ: dict.fromkeys(univ, 100.0),
        )
        stamps = {log.binding_fingerprint["decision_time"] for log in res.period_logs}
        assert len(stamps) == 2

    def test_binding_evidence_rejects_an_incomplete_binding(self) -> None:
        """binding_evidence validates at build time, not at review time."""
        class Incomplete(_Binding):
            def binding_fingerprint(self, decision_time: datetime) -> dict[str, Any]:
                return {"universe_dataset_id": "ds_universe"}

        with pytest.raises(UniverseBindingError, match="missing required fields"):
            binding_evidence(Incomplete(), datetime(2026, 1, 1, tzinfo=UTC))
