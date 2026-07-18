"""Focused tests for the semantic repo control validator.

These exercise the GOV-001 field format in `CURRENT_TASK.md`:

    Ticket: GOV-001
    State: AWAITING_REVIEW
    Governing documents:
    - docs/adr/0011-repo-governance-and-agent-instructions.md
    - docs/reviews/REVIEW-0003_GOV-001.md
    Authorized scope: Complete GOV-001 only.
    Required outcome: GOV-001 acceptance checks pass.
    Stop condition: Commit and stop for review.
    Next ticket authorized: NONE
"""

from __future__ import annotations

from pathlib import Path

import importlib.util

spec = importlib.util.spec_from_file_location("crc", "scripts/check_repo_control.py")
crc = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(crc)  # type: ignore[union-attr]
validate = crc.validate
VALID_STATES = crc.VALID_STATES


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


GOV_001_TICKET = """# GOV-001

**Status:** AWAITING_REVIEW

# GOV-001
"""

GOV_001_REVIEW = "# REVIEW-0003_GOV-001\n"
ADR_0011 = "# ADR 0011\n"

VALID_CURRENT_TASK = """# Current developer task

Ticket: GOV-001
State: AWAITING_REVIEW
Governing documents:
- docs/adr/0011-repo-governance-and-agent-instructions.md
- docs/reviews/REVIEW-0003_GOV-001.md
Authorized scope: Complete GOV-001 only.
Required outcome: GOV-001 acceptance checks pass.
Stop condition: Commit and stop for review.
Next ticket authorized: NONE
"""


def make_valid_structure(tmp_path: Path) -> None:
    root = tmp_path
    write(root / "AGENTS.md", "# AGENTS.md\nFollow CURRENT_TASK.md.\n")
    write(root / "docs/handoff/CURRENT_TASK.md", VALID_CURRENT_TASK)
    write(root / "tickets/GOV-001.md", GOV_001_TICKET)
    write(root / "docs/adr/0011-repo-governance-and-agent-instructions.md", ADR_0011)
    write(root / "docs/reviews/REVIEW-0003_GOV-001.md", GOV_001_REVIEW)
    write(root / "docs/handoff/HERMES_START_HERE.md", "# Hermes\nFollow the CURRENT_TASK.md only.\n")


def test_valid_repository(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    ok, errors = validate(tmp_path)
    assert ok, errors


def test_missing_ticket_file(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    (tmp_path / "tickets/GOV-001.md").unlink()
    ok, errors = validate(tmp_path)
    assert not ok
    assert any("does not exist" in e for e in errors)


def test_invalid_state(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    ct = (tmp_path / "docs/handoff/CURRENT_TASK.md").read_text()
    ct = ct.replace("State: AWAITING_REVIEW", "State: FOO_STATE")
    (tmp_path / "docs/handoff/CURRENT_TASK.md").write_text(ct)
    ok, errors = validate(tmp_path)
    assert not ok
    assert any("Invalid task state" in e for e in errors)


def test_mismatched_ticket_status(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    t = (tmp_path / "tickets/GOV-001.md").read_text()
    t = t.replace("AWAITING_REVIEW", "BLOCKED")
    (tmp_path / "tickets/GOV-001.md").write_text(t)
    ok, errors = validate(tmp_path)
    assert not ok
    assert any("does not match task state" in e for e in errors)


def test_missing_governing_document(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    (tmp_path / "docs/reviews/REVIEW-0003_GOV-001.md").unlink()
    ok, errors = validate(tmp_path)
    assert not ok
    assert any("Referenced governing document missing" in e for e in errors)


def test_multiple_ticket_declarations(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    ct = (tmp_path / "docs/handoff/CURRENT_TASK.md").read_text()
    ct = ct.replace(
        "Ticket: GOV-001",
        "Ticket: GOV-001\nTicket: CAT-001A",
    )
    (tmp_path / "docs/handoff/CURRENT_TASK.md").write_text(ct)
    ok, errors = validate(tmp_path)
    assert not ok
    assert any("exactly one `Ticket:`" in e for e in errors)


def test_unauthorized_next_ticket_when_awaiting_review(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    ct = (tmp_path / "docs/handoff/CURRENT_TASK.md").read_text()
    ct = ct.replace("Next ticket authorized: NONE", "Next ticket authorized: GOV-002")
    (tmp_path / "docs/handoff/CURRENT_TASK.md").write_text(ct)
    ok, errors = validate(tmp_path)
    assert not ok
    assert any("Next ticket authorized must be NONE" in e for e in errors)


def test_explicit_next_ticket_id_allowed_when_in_progress(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    ct = (tmp_path / "docs/handoff/CURRENT_TASK.md").read_text()
    ct = ct.replace("State: AWAITING_REVIEW", "State: IN_PROGRESS")
    ct = ct.replace("Next ticket authorized: NONE", "Next ticket authorized: CAT-001A")
    (tmp_path / "docs/handoff/CURRENT_TASK.md").write_text(ct)
    t = (tmp_path / "tickets/GOV-001.md").read_text()
    t = t.replace("**Status:** AWAITING_REVIEW", "**Status:** IN_PROGRESS")
    (tmp_path / "tickets/GOV-001.md").write_text(t)
    ok, errors = validate(tmp_path)
    assert ok, errors


def test_all_valid_states_accepted(tmp_path: Path) -> None:
    for state in VALID_STATES:
        make_valid_structure(tmp_path)
        ct = (tmp_path / "docs/handoff/CURRENT_TASK.md").read_text()
        ct = ct.replace("State: AWAITING_REVIEW", f"State: {state}")
        if state in {"BLOCKED", "AWAITING_REVIEW"}:
            next_val = "NONE"
        else:
            next_val = "CAT-001A"
        ct = ct.replace("Next ticket authorized: NONE", f"Next ticket authorized: {next_val}")
        (tmp_path / "docs/handoff/CURRENT_TASK.md").write_text(ct)
        t = (tmp_path / "tickets/GOV-001.md").read_text()
        t = t.replace("**Status:** AWAITING_REVIEW", f"**Status:** {state}")
        (tmp_path / "tickets/GOV-001.md").write_text(t)
        ok, errors = validate(tmp_path)
        assert ok, (state, errors)


def test_no_push_or_remote_requirement_in_gov_docs(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    # Inject a prohibited requirement into AGENTS.md.
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS.md\nAgents must run `git push origin main` and verify public origin/main.\n"
    )
    ok, errors = validate(tmp_path)
    assert not ok
    assert any("push or verify remotes" in e for e in errors)


def test_no_hard_coded_ticket_in_hermes(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    (tmp_path / "docs/handoff/HERMES_START_HERE.md").write_text(
        "# Hermes\nImplement `tickets/CAT-001.md` first.\n"
    )
    ok, errors = validate(tmp_path)
    assert not ok
    assert any("hard-coded ticket assignment" in e for e in errors)
