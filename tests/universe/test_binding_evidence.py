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
    BINDING_EVIDENCE_SERIES_KEY,
    REQUIRED_BINDING_EVIDENCE_FIELDS,
    UniverseBindingError,
    binding_evidence,
    binding_evidence_series,
    validate_binding_evidence,
    validate_binding_evidence_series,
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

    def test_the_complete_series_covers_every_executed_decision(self, tmp_path: Path) -> None:
        """REVIEW-0251: a first-decision summary alone is insufficient."""
        loop = FactorDrivenPaperLoop(
            model_artifact_id="mod_series",
            promotion_registry=_promoted_registry(tmp_path, "mod_series"),
            factor=_Factor(),
        )
        decisions = [
            datetime(2026, 3, 1, tzinfo=UTC),
            datetime(2026, 3, 8, tzinfo=UTC),
            datetime(2026, 3, 15, tzinfo=UTC),
            datetime(2026, 3, 22, tzinfo=UTC),
        ]
        res = loop.run_loop(
            universe_binding=_Binding(),
            decision_times=decisions,
            get_prices_at=lambda dt, univ: dict.fromkeys(univ, 100.0),
        )
        series = binding_evidence_series(res.period_logs)
        assert len(series) == len(decisions)
        validate_binding_evidence_series(
            series, decision_count=len(res.period_logs), decision_times=decisions
        )

    def test_binding_evidence_rejects_an_incomplete_binding(self) -> None:
        """binding_evidence validates at build time, not at review time."""
        class Incomplete(_Binding):
            def binding_fingerprint(self, decision_time: datetime) -> dict[str, Any]:
                return {"universe_dataset_id": "ds_universe"}

        with pytest.raises(UniverseBindingError, match="missing required fields"):
            binding_evidence(Incomplete(), datetime(2026, 1, 1, tzinfo=UTC))


# --------------------------------------------------------------------------- #
# REVIEW-0251 — the complete series contract
# --------------------------------------------------------------------------- #

def _entry(when: str) -> dict[str, Any]:
    payload = dict.fromkeys(REQUIRED_BINDING_EVIDENCE_FIELDS, 1)
    payload["decision_time"] = when
    return payload


class TestSeriesContract:
    def test_a_truncated_series_is_refused(self) -> None:
        """Dropping decisions is exactly the REVIEW-0251 defect."""
        series = [_entry("2026-01-01T00:00:00+00:00")]
        with pytest.raises(UniverseBindingError, match="1 entries for 3 decisions"):
            validate_binding_evidence_series(series, decision_count=3)

    def test_an_over_long_series_is_refused(self) -> None:
        series = [_entry(f"2026-01-0{i}T00:00:00+00:00") for i in (1, 2, 3)]
        with pytest.raises(UniverseBindingError, match="3 entries for 2 decisions"):
            validate_binding_evidence_series(series, decision_count=2)

    def test_timestamps_must_match_the_executed_decisions(self) -> None:
        decisions = [
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 8, tzinfo=UTC),
        ]
        wrong = [
            _entry("2026-01-01T00:00:00+00:00"),
            _entry("2026-02-99".replace("99", "15") + "T00:00:00+00:00"),
        ]
        with pytest.raises(UniverseBindingError, match="do not match the executed"):
            validate_binding_evidence_series(wrong, decision_times=decisions)

    def test_a_duplicated_timestamp_is_refused(self) -> None:
        """A series that repeats the first decision is the summary in disguise."""
        decisions = [
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 8, tzinfo=UTC),
        ]
        repeated = [_entry("2026-01-01T00:00:00+00:00")] * 2
        with pytest.raises(UniverseBindingError, match="do not match the executed"):
            validate_binding_evidence_series(repeated, decision_times=decisions)

    def test_out_of_order_entries_are_refused(self) -> None:
        decisions = [
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 8, tzinfo=UTC),
        ]
        reversed_series = [
            _entry("2026-01-08T00:00:00+00:00"),
            _entry("2026-01-01T00:00:00+00:00"),
        ]
        with pytest.raises(UniverseBindingError, match="do not match the executed"):
            validate_binding_evidence_series(reversed_series, decision_times=decisions)

    def test_an_empty_series_is_refused(self) -> None:
        with pytest.raises(UniverseBindingError, match="empty"):
            validate_binding_evidence_series([])

    def test_an_incomplete_entry_inside_the_series_is_refused(self) -> None:
        good = _entry("2026-01-01T00:00:00+00:00")
        bad = _entry("2026-01-08T00:00:00+00:00")
        del bad["bar_panel_dataset_id"]
        with pytest.raises(UniverseBindingError, match="missing required fields"):
            validate_binding_evidence_series([good, bad])

    def test_a_period_log_without_a_fingerprint_is_refused(self) -> None:
        class _Bare:
            binding_fingerprint: dict[str, Any] = {}

        with pytest.raises(UniverseBindingError, match="carries no binding fingerprint"):
            binding_evidence_series([_Bare()])

    def test_a_matching_series_passes(self) -> None:
        decisions = [
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 8, tzinfo=UTC),
        ]
        series = [_entry(t.isoformat()) for t in decisions]
        validate_binding_evidence_series(
            series, decision_count=2, decision_times=decisions
        )


class TestEveryBuilderSerializesTheCompleteSeries:
    @pytest.mark.parametrize(
        "script", affected_entrypoints(), ids=lambda p: p.name
    )
    def test_every_entrypoint_emits_the_complete_series(self, script: Path) -> None:
        """A summary-only artifact loses coverage for every later decision."""
        source = script.read_text(encoding="utf-8")
        assert BINDING_EVIDENCE_SERIES_KEY in source, (
            f"{script.name} serializes no {BINDING_EVIDENCE_SERIES_KEY}"
        )
        assert "binding_evidence_series(" in source, (
            f"{script.name} must build its series with the shared serializer"
        )

    @pytest.mark.parametrize(
        "script", affected_entrypoints(), ids=lambda p: p.name
    )
    def test_the_series_is_sourced_from_executed_period_logs(self, script: Path) -> None:
        """Sourcing from period_logs is what guarantees one entry per decision."""
        source = script.read_text(encoding="utf-8")
        assert "binding_evidence_series(result.period_logs)" in source or (
            "binding_evidence_series(res.period_logs)" in source
        ), f"{script.name} must source its series from the loop's period logs"

    def test_no_builder_keeps_only_the_first_decision(self) -> None:
        """Regression for REVIEW-0251: summary present implies series present."""
        offenders = []
        for script in affected_entrypoints():
            source = script.read_text(encoding="utf-8")
            if BINDING_EVIDENCE_KEY in source and BINDING_EVIDENCE_SERIES_KEY not in source:
                offenders.append(script.name)
        assert not offenders, f"summary-only artifacts remain: {offenders}"


class TestWrittenArtifactsCarryTheSeries:
    """Per-artifact, not per-file.

    A file-level string check passes when the series exists only inside a helper
    while the artifact actually written to disk keeps a first-decision summary --
    which is how diagnose_momts_risk.py's long_session slipped through.
    """

    @staticmethod
    def _written_artifact_names(tree: ast.AST) -> set[str]:
        """Names passed to json.dumps(...) whose result is written to disk."""
        names: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_dumps = (
                isinstance(func, ast.Attribute)
                and func.attr == "dumps"
                and isinstance(func.value, ast.Name)
                and func.value.id == "json"
            )
            if is_dumps and node.args and isinstance(node.args[0], ast.Name):
                names.add(node.args[0].id)
        return names

    @staticmethod
    def _artifact_node(tree: ast.AST, target: str) -> ast.Dict | None:
        """The dict literal assigned to ``target``, if it is one."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                assigned: list[ast.expr] = list(node.targets)
            elif isinstance(node, ast.AnnAssign):
                assigned = [node.target]
            else:
                continue
            if any(isinstance(t, ast.Name) and t.id == target for t in assigned) and (
                isinstance(node.value, ast.Dict)
            ):
                return node.value
        return None

    @staticmethod
    def _mentions(node: ast.AST, *needles: str) -> bool:
        """True if any string constant or name in the subtree matches."""
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and sub.value in needles:
                return True
            if isinstance(sub, ast.Name) and sub.id in needles:
                return True
        return False

    def test_long_session_artifact_carries_the_full_series(self) -> None:
        """Exact regression for the gap found in self-review."""
        source = (SCRIPTS_DIR / "research" / "diagnose_momts_risk.py").read_text(
            encoding="utf-8"
        )
        node = self._artifact_node(ast.parse(source), "long_session")
        assert node is not None, "long_session artifact not found"
        assert self._mentions(node, BINDING_EVIDENCE_SERIES_KEY), (
            "long_session cherry-picks scalars and would drop the series"
        )

    @pytest.mark.parametrize(
        "script", affected_entrypoints(), ids=lambda p: p.name
    )
    def test_each_written_artifact_carries_series_or_embedded_cells(
        self, script: Path
    ) -> None:
        """Every artifact written to disk must reach the series somehow.

        Session artifacts carry it directly. Aggregate artifacts (grids, folds)
        carry it inside each embedded cell/summary collection, since a single
        series is meaningless across many configurations.
        """
        tree = ast.parse(script.read_text(encoding="utf-8"))
        embedded_collections = {
            "grid_results", "config_results", "folds",
            "train_fold", "test_fold", "enforced_summary",
            "unconstrained_summary", "period_logs",
        }
        for name in sorted(self._written_artifact_names(tree)):
            node = self._artifact_node(tree, name)
            if node is None:
                continue  # built by a helper, covered by that helper's own checks
            # Only run artifacts are in scope; a harden/correctness report is not
            # a binding artifact and legitimately carries no membership evidence.
            if not self._mentions(node, BINDING_EVIDENCE_KEY, "decision_count"):
                continue
            assert self._mentions(
                node, BINDING_EVIDENCE_SERIES_KEY, *embedded_collections
            ), (
                f"{script.name}: run artifact {name!r} records binding evidence but "
                f"neither {BINDING_EVIDENCE_SERIES_KEY} nor an embedded collection"
            )


class TestStaleTimestampsAreRefused:
    """A fingerprint must describe the decision it is attached to.

    Without this, an artifact can attribute as-of coverage to a decision that
    never produced it -- the evidence looks complete but is wrong.
    """

    def test_binding_evidence_refuses_a_stale_fingerprint(self) -> None:
        class _Stale(_Binding):
            def binding_fingerprint(self, decision_time: datetime) -> dict[str, Any]:
                payload = super().binding_fingerprint(decision_time)
                payload["decision_time"] = "2020-01-01T00:00:00+00:00"
                return payload

        with pytest.raises(UniverseBindingError, match="refusing stale binding evidence"):
            binding_evidence(_Stale(), datetime(2026, 5, 1, tzinfo=UTC))

    def test_binding_evidence_accepts_the_matching_instant(self) -> None:
        when = datetime(2026, 5, 1, tzinfo=UTC)
        assert binding_evidence(_Binding(), when)["decision_time"] == when.isoformat()

    def test_the_series_refuses_a_log_whose_fingerprint_is_stale(self) -> None:
        class _Log:
            def __init__(self, when: datetime, stamped: str) -> None:
                self.decision_time = when
                self.binding_fingerprint = dict.fromkeys(
                    REQUIRED_BINDING_EVIDENCE_FIELDS, 1
                )
                self.binding_fingerprint["decision_time"] = stamped

        good = _Log(
            datetime(2026, 5, 1, tzinfo=UTC), "2026-05-01T00:00:00+00:00"
        )
        stale = _Log(
            datetime(2026, 5, 8, tzinfo=UTC), "2026-05-01T00:00:00+00:00"
        )
        with pytest.raises(UniverseBindingError, match="period log 1"):
            binding_evidence_series([good, stale])

    def test_the_series_accepts_matching_logs(self) -> None:
        class _Log:
            def __init__(self, when: datetime) -> None:
                self.decision_time = when
                self.binding_fingerprint = dict.fromkeys(
                    REQUIRED_BINDING_EVIDENCE_FIELDS, 1
                )
                self.binding_fingerprint["decision_time"] = when.isoformat()

        logs = [_Log(datetime(2026, 5, d, tzinfo=UTC)) for d in (1, 8, 15)]
        assert len(binding_evidence_series(logs)) == 3

    def test_a_log_without_a_decision_time_is_refused(self) -> None:
        class _Bare:
            binding_fingerprint = dict.fromkeys(REQUIRED_BINDING_EVIDENCE_FIELDS, 1)

        with pytest.raises(UniverseBindingError, match="no decision_time"):
            binding_evidence_series([_Bare()])
