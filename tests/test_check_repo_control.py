"""Focused tests for the semantic repo control validator."""

from __future__ import annotations

from pathlib import Path

import importlib.util
spec = importlib.util.spec_from_file_location("crc", "scripts/check_repo_control.py")
crc = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(crc)  # type: ignore[union-attr]
validate = crc.validate


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def make_valid_structure(tmp_path: Path) -> None:
    root = tmp_path
    write(root / "AGENTS.md", "# AGENTS.md\n")
    write(root / "docs/handoff/CURRENT_TASK.md", """# Current task

## Task State
AWAITING_REVIEW

## Next ticket authorized
NONE

Complete [`GOV-001`](../../tickets/GOV-001.md) and stop for review.

Read [ADR-0011](../adr/0011-foo.md) and [AGENTS.md](../../AGENTS.md).
""")
    write(root / "tickets/GOV-001.md", "**Status:** AWAITING_REVIEW\n\n# GOV-001\n")
    write(root / "docs/adr/0011-foo.md", "# ADR 0011\n")
    write(root / "docs/handoff/HERMES_START_HERE.md", "# Hermes\nFollow the CURRENT_TASK.md only.\n")


def test_valid_repository(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    ok, errors = validate(tmp_path)
    assert ok, errors


def test_missing_ticket(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    (tmp_path / "tickets/GOV-001.md").unlink()
    ok, errors = validate(tmp_path)
    assert not ok
    assert any("does not exist" in e for e in errors)


def test_invalid_state(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    ct = (tmp_path / "docs/handoff/CURRENT_TASK.md").read_text()
    ct = ct.replace("AWAITING_REVIEW", "FOO_STATE")
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
    (tmp_path / "docs/adr/0011-foo.md").unlink()
    ok, errors = validate(tmp_path)
    assert not ok
    assert any("Referenced governing document missing" in e for e in errors)


def test_multiple_ticket_declarations(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    ct = (tmp_path / "docs/handoff/CURRENT_TASK.md").read_text()
    ct = ct + "\nComplete [`CAT-001A`](../../tickets/CAT-001A.md) too."
    (tmp_path / "docs/handoff/CURRENT_TASK.md").write_text(ct)
    ok, errors = validate(tmp_path)
    assert not ok
    assert any("exactly one ticket" in e.lower() for e in errors)


def test_unauthorized_next_ticket_progression(tmp_path: Path) -> None:
    make_valid_structure(tmp_path)
    ct = (tmp_path / "docs/handoff/CURRENT_TASK.md").read_text()
    ct = ct.replace("Next ticket authorized\nNONE", "Next ticket authorized\nGOV-002")
    (tmp_path / "docs/handoff/CURRENT_TASK.md").write_text(ct)
    ok, errors = validate(tmp_path)
    assert not ok
    assert any("Next ticket authorized must be NONE" in e for e in errors)
