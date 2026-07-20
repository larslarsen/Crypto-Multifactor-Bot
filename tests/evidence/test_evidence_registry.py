"""Focused EVD-001 regressions for the Operational Evidence Registry.

Covers the REVIEW-0052/0053/0054 regression checklist authorized under
REVIEW-0055 (Jr integration): verified evidence hashes, immutable idempotence,
point-in-time ordering, snapshot/supersession ownership, promotion guards,
deterministic exports, atomic/idempotent real-seed import, registry-version
rejection, seed snapshot validation, typed SQLite failures, clean CLI failures,
and explicit experiment-link exclusion.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.evidence.canonical import content_sha256
from cryptofactors.evidence.models import (
    EvidenceDirection,
    EvidenceIntegrity,
    EvidenceItem,
    EvidenceKind,
    EvidenceRelevance,
    EvidenceSnapshot,
    HypothesisDecision,
    HypothesisEvidenceLink,
    HypothesisLifecycle,
    HypothesisVerdict,
    HypothesisVersion,
    IndependenceClass,
    IntegrityGrade,
    ReproductionGrade,
)
from cryptofactors.evidence.repository import (
    EvidenceRegistryError,
    EvidenceRepository,
    _evidence_canonical_body,
    seed_import_hypotheses,
)

SEED_PATH = Path("research/evidence/hypotheses.yaml")
HYP_CREATED = datetime(2026, 7, 20, 0, 0, 0, tzinfo=timezone.utc)


def _hyp(hid: str = "H-001", slug: str = "medium-term-momentum") -> HypothesisVersion:
    return HypothesisVersion(
        hypothesis_id=hid,
        version=1,
        slug=slug,
        title="Medium-term momentum title long enough",
        statement=(
            "Among point-in-time eligible liquid cryptoassets, higher medium-term "
            "residual returns predict higher subsequent net returns over the declared "
            "weekly horizon, excluding the most recent reversal window."
        ),
        mechanism=(
            "Slow information diffusion and trend-following demand may create "
            "persistent cross-sectional continuation after controlling for exposure."
        ),
        expected_sign="POSITIVE",
        phase="PHASE_1",
        primary_metric="net_return",
        advancement_rule="Positive net performance under preregistered costs.",
        rejection_rule="Reject if net performance is non-positive.",
    )


def _evidence(
    eid: str,
    kind: EvidenceKind = EvidenceKind.EXPERIMENT_RESULT,
    registered_at: datetime = HYP_CREATED,
) -> EvidenceItem:
    """Build an EvidenceItem with a VERIFIED canonical content_sha256."""
    raw = EvidenceItem(
        evidence_id=eid,
        kind=kind,
        title="Evidence title long enough",
        summary="Evidence summary long enough",
        source_ref="src://ref",
        registered_at=registered_at,
        registered_by="tester",
        metadata={"k": "v"},
        content_sha256="0" * 64,
    )
    verified = content_sha256(_evidence_canonical_body(raw))
    return raw.model_copy(update={"content_sha256": verified})


def _link(evid: str, hid: str = "H-001") -> HypothesisEvidenceLink:
    return HypothesisEvidenceLink(
        hypothesis_id=hid,
        hypothesis_version=1,
        evidence_id=evid,
        direction=EvidenceDirection.SUPPORTS,
        relevance=EvidenceRelevance.PRIMARY,
        rationale="rationale text long enough",
        integrity=EvidenceIntegrity(
            point_in_time=IntegrityGrade.PASS,
            causal_split=IntegrityGrade.PASS,
            reproduction=ReproductionGrade.FULL,
            costs=IntegrityGrade.PASS,
            universe=IntegrityGrade.PASS,
            independence=IndependenceClass.INTERNAL_INDEPENDENT,
        ),
        registered_at=HYP_CREATED,
        registered_by="tester",
    )


@pytest.fixture()
def repo(tmp_path: Path) -> EvidenceRepository:
    db = tmp_path / "ev.db"
    apply_migrations(db)
    return EvidenceRepository(db)


def _snapshot(repo: EvidenceRepository, hid: str = "H-001") -> EvidenceSnapshot:
    # Deterministic: pass generated_at explicitly so tests do not depend on the
    # system clock (the repository requires generated_at >= as_of).
    return repo.build_snapshot(
        hid, 1, as_of=HYP_CREATED, generated_at=HYP_CREATED
    )


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cryptofactors.cli", *args],
        capture_output=True,
        text=True,
    )


# ----------------------------------------------------------------------
# 1. Verified evidence hashes (REVIEW-0052 #1)
# ----------------------------------------------------------------------


def test_evidence_rejects_caller_supplied_mismatched_hash(repo: EvidenceRepository) -> None:
    ev = _evidence("EV-AAA")
    with pytest.raises(EvidenceRegistryError, match="content_sha256 does not match"):
        repo.add_evidence(ev.model_copy(update={"content_sha256": "0" * 64}))


def test_evidence_accepts_verified_hash(repo: EvidenceRepository) -> None:
    repo.add_evidence(_evidence("EV-AAA"))
    assert len(repo.list_evidence()) == 1


# ----------------------------------------------------------------------
# 2. Immutable idempotence (REVIEW-0052 #1)
# ----------------------------------------------------------------------


def test_evidence_idempotent_on_identical_content(repo: EvidenceRepository) -> None:
    repo.add_evidence(_evidence("EV-AAA"))
    repo.add_evidence(_evidence("EV-AAA"))  # same id, same verified content
    assert len(repo.list_evidence()) == 1


def test_evidence_id_clash_with_different_content_rejected(repo: EvidenceRepository) -> None:
    repo.add_evidence(_evidence("EV-AAA"))
    changed = _evidence("EV-AAA").model_copy(
        update={"summary": "changed summary long enough"}
    )
    changed = changed.model_copy(
        update={"content_sha256": content_sha256(_evidence_canonical_body(changed))}
    )
    with pytest.raises(EvidenceRegistryError, match="different content"):
        repo.add_evidence(changed)


# ----------------------------------------------------------------------
# 3. Point-in-time ordering (REVIEW-0052 #3, REVIEW-0053 #1)
# ----------------------------------------------------------------------


def test_snapshot_as_of_cannot_predate_hypothesis_created(repo: EvidenceRepository) -> None:
    repo.register_hypothesis(_hyp(), actor="tester", created_at="2026-07-20T00:00:00.000000Z")
    with pytest.raises(EvidenceRegistryError, match="cannot predate hypothesis version"):
        repo.build_snapshot("H-001", 1, as_of=datetime(2026, 7, 19, tzinfo=timezone.utc))


def test_link_cannot_predate_evidence_registration(repo: EvidenceRepository) -> None:
    repo.register_hypothesis(_hyp(), actor="tester", created_at="2026-07-20T00:00:00.000000Z")
    # Evidence registered AFTER the hypothesis, link predates only the evidence.
    repo.add_evidence(_evidence("EV-AAA", registered_at=datetime(2026, 7, 21, tzinfo=timezone.utc)))
    late_link = _link("EV-AAA").model_copy(
        update={"registered_at": datetime(2026, 7, 20, tzinfo=timezone.utc)}
    )
    with pytest.raises(EvidenceRegistryError, match="cannot predate evidence registered"):
        repo.link_evidence(late_link)


def test_snapshot_includes_only_links_registered_by_as_of(repo: EvidenceRepository) -> None:
    repo.register_hypothesis(_hyp(), actor="tester", created_at="2026-07-20T00:00:00.000000Z")
    repo.add_evidence(_evidence("EV-AAA"))
    # Link registered one hour after the hypothesis/evidence creation.
    repo.link_evidence(
        _link("EV-AAA").model_copy(
            update={"registered_at": HYP_CREATED + timedelta(hours=1)}
        )
    )
    # Snapshot strictly before the link registration time exposes no links.
    early = repo.build_snapshot(
        "H-001", 1, as_of=HYP_CREATED + timedelta(minutes=30), generated_at=HYP_CREATED + timedelta(minutes=30)
    )
    assert len(early.links) == 0
    # Snapshot after the link registration time includes it.
    late = repo.build_snapshot(
        "H-001", 1, as_of=HYP_CREATED + timedelta(hours=2), generated_at=HYP_CREATED + timedelta(hours=2)
    )
    assert len(late.links) == 1


# ----------------------------------------------------------------------
# 4. Snapshot + supersession ownership (REVIEW-0052 #2)
# ----------------------------------------------------------------------


def test_snapshot_idempotent_same_state(repo: EvidenceRepository) -> None:
    repo.register_hypothesis(_hyp(), actor="tester", created_at="2026-07-20T00:00:00.000000Z")
    repo.add_evidence(_evidence("EV-AAA"))
    repo.link_evidence(_link("EV-AAA"))
    s1 = _snapshot(repo)
    s2 = _snapshot(repo)
    assert s1.snapshot_id == s2.snapshot_id
    assert s1.content_sha256 == s2.content_sha256


def test_decision_requires_exact_snapshot_ownership(repo: EvidenceRepository) -> None:
    repo.register_hypothesis(_hyp(), actor="tester", created_at="2026-07-20T00:00:00.000000Z")
    repo.register_hypothesis(
        _hyp("H-002", "short-term-reversal"),
        actor="tester",
        created_at="2026-07-20T00:00:00.000000Z",
    )
    repo.add_evidence(_evidence("EV-AAA"))
    repo.link_evidence(_link("EV-AAA"))
    snap = _snapshot(repo)
    wrong = HypothesisDecision(
        decision_id="dec-x",
        hypothesis_id="H-002",
        hypothesis_version=1,
        action="SET_VERDICT",
        lifecycle=HypothesisLifecycle.DRAFT,
        verdict=HypothesisVerdict.UNTESTED,
        evidence_snapshot_id=snap.snapshot_id,
        reason="reason long enough",
        actor="tester",
        event_at=HYP_CREATED + timedelta(hours=1),
    )
    with pytest.raises(EvidenceRegistryError, match="does not belong to the decision"):
        repo.append_decision(wrong)


def test_correct_requires_supersedes_and_strictly_after(repo: EvidenceRepository) -> None:
    repo.register_hypothesis(_hyp(), actor="tester", created_at="2026-07-20T00:00:00.000000Z")
    repo.add_evidence(_evidence("EV-AAA"))
    repo.link_evidence(_link("EV-AAA"))
    snap = _snapshot(repo)
    base: dict[str, Any] = dict(
        hypothesis_id="H-001",
        hypothesis_version=1,
        lifecycle=HypothesisLifecycle.ACTIVE,
        verdict=HypothesisVerdict.SUPPORTED,
        evidence_snapshot_id=snap.snapshot_id,
        reason="reason long enough",
        actor="tester",
    )
    # CORRECT without supersedes -> rejected.
    with pytest.raises(EvidenceRegistryError, match="requires supersedes_decision_id"):
        repo.append_decision(
            HypothesisDecision(
                decision_id="dec-c1",
                action="CORRECT",
                event_at=HYP_CREATED + timedelta(hours=2),
                **base,
            )
        )
    repo.append_decision(
        HypothesisDecision(
            decision_id="dec-1",
            action="SET_VERDICT",
            event_at=HYP_CREATED + timedelta(hours=1),
            **base,
        )
    )
    # CORRECT must occur strictly after the superseded event.
    with pytest.raises(EvidenceRegistryError, match="strictly after the superseded"):
        repo.append_decision(
            HypothesisDecision(
                decision_id="dec-c2",
                action="CORRECT",
                event_at=HYP_CREATED + timedelta(hours=1),
                supersedes_decision_id="dec-1",
                **base,
            )
        )
    repo.append_decision(
        HypothesisDecision(
            decision_id="dec-c3",
            action="CORRECT",
            event_at=HYP_CREATED + timedelta(hours=3),
            supersedes_decision_id="dec-1",
            **base,
        )
    )


# ----------------------------------------------------------------------
# 5. Promotion guards (ticket invariants / REVIEW-0052 #2)
# ----------------------------------------------------------------------


def test_promotion_rejected_for_literature_only_snapshot(repo: EvidenceRepository) -> None:
    repo.register_hypothesis(_hyp(), actor="tester", created_at="2026-07-20T00:00:00.000000Z")
    repo.add_evidence(_evidence("EV-LIT", EvidenceKind.LITERATURE_PUBLISHED))
    repo.link_evidence(_link("EV-LIT"))
    snap = _snapshot(repo)
    with pytest.raises(EvidenceRegistryError, match="only literature or legacy"):
        repo.append_decision(
            HypothesisDecision(
                decision_id="dec-p1",
                hypothesis_id="H-001",
                hypothesis_version=1,
                action="SET_VERDICT",
                lifecycle=HypothesisLifecycle.ACTIVE,
                verdict=HypothesisVerdict.SUPPORTED,
                evidence_snapshot_id=snap.snapshot_id,
                reason="reason long enough",
                actor="tester",
                event_at=HYP_CREATED + timedelta(hours=1),
            )
        )


@pytest.mark.parametrize("grade", ["point_in_time", "causal_split"])
def test_promotion_rejected_for_integrity_fail(
    repo: EvidenceRepository, grade: str
) -> None:
    repo.register_hypothesis(_hyp(), actor="tester", created_at="2026-07-20T00:00:00.000000Z")
    repo.add_evidence(_evidence("EV-EXP"))
    pass_integrity = EvidenceIntegrity(
        point_in_time=IntegrityGrade.PASS,
        causal_split=IntegrityGrade.PASS,
        reproduction=ReproductionGrade.FULL,
        costs=IntegrityGrade.PASS,
        universe=IntegrityGrade.PASS,
        independence=IndependenceClass.INTERNAL_INDEPENDENT,
    )
    fail_integrity = pass_integrity.model_copy(update={grade: IntegrityGrade.FAIL})
    bad = _link("EV-EXP").model_copy(update={"integrity": fail_integrity})
    repo.link_evidence(bad)
    snap = _snapshot(repo)
    with pytest.raises(EvidenceRegistryError, match="integrity FAIL"):
        repo.append_decision(
            HypothesisDecision(
                decision_id="dec-p2",
                hypothesis_id="H-001",
                hypothesis_version=1,
                action="SET_VERDICT",
                lifecycle=HypothesisLifecycle.ACTIVE,
                verdict=HypothesisVerdict.SUPPORTED,
                evidence_snapshot_id=snap.snapshot_id,
                reason="reason long enough",
                actor="tester",
                event_at=HYP_CREATED + timedelta(hours=1),
            )
        )


# ----------------------------------------------------------------------
# 6. Complete deterministic exports (REVIEW-0052 #5)
# ----------------------------------------------------------------------


def test_export_json_byte_stable_and_complete(repo: EvidenceRepository) -> None:
    repo.register_hypothesis(_hyp(), actor="tester", created_at="2026-07-20T00:00:00.000000Z")
    repo.add_evidence(_evidence("EV-AAA"))  # unlinked evidence must appear
    repo.add_evidence(_evidence("EV-BBB"))
    repo.link_evidence(_link("EV-AAA"))
    snap = _snapshot(repo)
    repo.append_decision(
        HypothesisDecision(
            decision_id="dec-1",
            hypothesis_id="H-001",
            hypothesis_version=1,
            action="SET_VERDICT",
            lifecycle=HypothesisLifecycle.ACTIVE,
            verdict=HypothesisVerdict.SUPPORTED,
            evidence_snapshot_id=snap.snapshot_id,
            reason="reason long enough",
            actor="tester",
            event_at=HYP_CREATED + timedelta(hours=1),
        )
    )
    e1 = repo.export_current_state("json")
    e2 = repo.export_current_state("json")
    assert isinstance(e1, (bytes, str))
    b1 = e1 if isinstance(e1, bytes) else e1.encode()
    b2 = e2 if isinstance(e2, bytes) else e2.encode()
    assert b1 == b2  # byte-stable
    state = json.loads(b1.decode() if isinstance(b1, bytes) else b1)
    assert len(state["evidence"]) == 2  # unlinked EV-BBB included
    hyp = state["hypotheses"][0]
    assert hyp["versions"][0]["content_sha256"]
    assert hyp["current"]["verdict"] == "SUPPORTED"
    assert len(hyp["links"]) == 1
    assert len(hyp["decisions"]) == 1


def test_export_markdown_deterministic(repo: EvidenceRepository) -> None:
    repo.register_hypothesis(_hyp(), actor="tester", created_at="2026-07-20T00:00:00.000000Z")
    m1 = repo.export_current_state("markdown")
    m2 = repo.export_current_state("markdown")
    assert m1 == m2
    assert "Evidence Registry Current State" in m1


# ----------------------------------------------------------------------
# 7. Atomic / idempotent real-seed import (REVIEW-0052 #4, REVIEW-0053 #2)
# ----------------------------------------------------------------------


def test_seed_import_real_yaml_idempotent(repo: EvidenceRepository) -> None:
    n1 = repo.seed_import(SEED_PATH, actor="seed", created_at="2026-07-20T00:00:00.000000Z")
    assert n1 > 0
    n2 = repo.seed_import(SEED_PATH, actor="seed", created_at="2026-07-20T00:00:00.000000Z")
    assert n2 == 0  # fully idempotent
    assert len(repo.list_hypotheses()) == n1


def test_seed_import_atomic_on_bad_entry(tmp_path: Path) -> None:
    db = tmp_path / "ev.db"
    apply_migrations(db)
    r = EvidenceRepository(db)
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        json.dumps(
            {
                "registry_version": 2,
                "as_of": "2026-07-20T00:00:00Z",
                "hypotheses": [
                    {
                        "hypothesis_id": "H-001",
                        "version": 1,
                        "slug": "ok-slug",
                        "title": "ok title long enough",
                        "statement": "ok statement long enough to pass validation here.",
                        "mechanism": "ok mechanism long enough to pass validation here.",
                        "expected_sign": "POSITIVE",
                        "phase": "PHASE_1",
                        "primary_metric": "net_return",
                        "advancement_rule": "advance when positive.",
                        "rejection_rule": "reject when nonpositive.",
                        "lifecycle": "REGISTERED",
                        "verdict": "UNTESTED",
                    },
                    {
                        "hypothesis_id": "H-002",
                        "version": 1,
                        "slug": "bad-slug",
                        "title": "x",
                        "statement": "too short",
                    },
                ],
            }
        )
    )
    with pytest.raises(EvidenceRegistryError):
        r.seed_import(bad, actor="seed", created_at="2026-07-20T00:00:00.000000Z")
    # Atomic: no partial hypotheses landed.
    assert len(r.list_hypotheses()) == 0


# ----------------------------------------------------------------------
# 8. Registry-version rejection (REVIEW-0053 #2)
# ----------------------------------------------------------------------


def test_seed_rejects_unsupported_registry_version(tmp_path: Path) -> None:
    db = tmp_path / "ev.db"
    apply_migrations(db)
    r = EvidenceRepository(db)
    bad = tmp_path / "v3.yaml"
    bad.write_text(json.dumps({"registry_version": 3, "hypotheses": []}))
    with pytest.raises(EvidenceRegistryError, match="unsupported registry_version"):
        r.seed_import(bad, actor="seed", created_at="2026-07-20T00:00:00.000000Z")


def test_seed_rejects_unknown_top_level_field(tmp_path: Path) -> None:
    db = tmp_path / "ev.db"
    apply_migrations(db)
    r = EvidenceRepository(db)
    bad = tmp_path / "extra.yaml"
    bad.write_text(
        json.dumps(
            {
                "registry_version": 2,
                "as_of": "2026-07-20T00:00:00Z",
                "unknown_top_field": True,
                "hypotheses": [],
            }
        )
    )
    with pytest.raises(EvidenceRegistryError, match="unsupported top-level"):
        r.seed_import(bad, actor="seed", created_at="2026-07-20T00:00:00.000000Z")


# ----------------------------------------------------------------------
# 9. Seed snapshot validation (REVIEW-0054 #2)
# ----------------------------------------------------------------------


def test_seed_rejects_when_linked_evidence_exists_at_seed_clock(tmp_path: Path) -> None:
    db = tmp_path / "ev.db"
    apply_migrations(db)
    r = EvidenceRepository(db)
    # Register H-001 with the EXACT seed content so seed_import's register step is a
    # no-op, then add linked evidence before seeding. The first-time seed path must
    # then fail closed (linked evidence already exists at the seed clock).
    import yaml  # type: ignore[import-untyped]

    seed = yaml.safe_load(Path(SEED_PATH).read_text(encoding="utf-8"))
    h1 = next(h for h in seed["hypotheses"] if h["hypothesis_id"] == "H-001")
    h1.pop("lifecycle", None)
    h1.pop("verdict", None)
    if "known_confounders" in h1:
        h1["known_confounders"] = tuple(h1["known_confounders"])
    if "required_dataset_types" in h1:
        h1["required_dataset_types"] = tuple(h1["required_dataset_types"])
    r.register_hypothesis(HypothesisVersion.model_validate(h1), actor="seed", created_at="2026-07-20T00:00:00.000000Z")
    r.add_evidence(_evidence("EV-PRE"))
    r.link_evidence(_link("EV-PRE"))
    with pytest.raises(EvidenceRegistryError, match="linked evidence already exists"):
        r.seed_import(SEED_PATH, actor="seed", created_at="2026-07-20T00:00:00.000000Z")


# ----------------------------------------------------------------------
# 10. Typed SQLite failures (REVIEW-0053 #3, REVIEW-0054 #1)
# ----------------------------------------------------------------------


def test_uninitialized_database_raises_typed_error(tmp_path: Path) -> None:
    # Database file exists but migrations never applied.
    db = tmp_path / "empty.db"
    db.write_bytes(b"")
    r = EvidenceRepository(db)
    with pytest.raises(EvidenceRegistryError):
        r.list_hypotheses()


def test_uninitialized_database_cli_exits_nonzero(tmp_path: Path) -> None:
    db = tmp_path / "empty.db"
    db.write_bytes(b"")
    result = _cli("evidence", "list-hypotheses", "--database", str(db))
    assert result.returncode == 1
    assert "no such table" in result.stderr or "sqlite error" in result.stderr
    assert "Traceback" not in result.stderr


# ----------------------------------------------------------------------
# 11. Clean CLI failures (REVIEW-0052 #6)
# ----------------------------------------------------------------------


def test_cli_register_rejects_invalid_model(tmp_path: Path) -> None:
    db = tmp_path / "ev.db"
    apply_migrations(db)
    payload = tmp_path / "bad.json"
    payload.write_text(json.dumps({"hypothesis_id": "H-001"}))  # missing required fields
    result = _cli(
        "evidence",
        "register-hypothesis",
        "--payload",
        str(payload),
        "--database",
        str(db),
        "--actor",
        "tester",
    )
    assert result.returncode == 1
    assert "Traceback" not in result.stderr


def test_cli_register_rejects_missing_payload_file(tmp_path: Path) -> None:
    db = tmp_path / "ev.db"
    apply_migrations(db)
    result = _cli(
        "evidence",
        "register-hypothesis",
        "--payload",
        str(tmp_path / "nope.json"),
        "--database",
        str(db),
        "--actor",
        "tester",
    )
    assert result.returncode == 1
    assert "Traceback" not in result.stderr


def test_cli_seed_end_to_end_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "ev.db"
    apply_migrations(db)
    out1 = _cli("evidence", "seed", "--database", str(db), "--yaml", str(SEED_PATH))
    assert out1.returncode == 0
    out2 = _cli("evidence", "seed", "--database", str(db), "--yaml", str(SEED_PATH))
    assert out2.returncode == 0
    # Second run reports 0 newly registered versions.
    assert "newly registered versions: 0" in out2.stdout


# ----------------------------------------------------------------------
# 12. Explicit experiment-link exclusion (ticket scope)
# ----------------------------------------------------------------------


def test_experiment_link_is_not_exposed() -> None:
    # Contract: EVD-001 must not implement or expose hypothesis_experiment_link.
    assert not hasattr(EvidenceRepository, "link_experiment")
    assert not hasattr(EvidenceRepository, "add_experiment_link")
    # The schema table exists but the repository provides no mutation path.
    import inspect

    source = inspect.getsource(EvidenceRepository)
    assert "hypothesis_experiment_link" not in source


def test_seed_import_hypotheses_module_entrypoint(tmp_path: Path) -> None:
    db = tmp_path / "ev.db"
    apply_migrations(db)
    r = EvidenceRepository(db)
    n = seed_import_hypotheses(r, SEED_PATH, actor="seed", created_at="2026-07-20T00:00:00.000000Z")
    assert n > 0
