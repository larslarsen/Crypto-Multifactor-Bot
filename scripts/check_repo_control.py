#!/usr/bin/env python3
"""check_repo_control.py

Dependency-free semantic repository-control validator.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

VALID_STATES = {"BLOCKED", "IN_PROGRESS", "AWAITING_REVIEW", "ACCEPTED"}

TICKET_RE = re.compile(r"\[`([A-Z]{2,}-\d+)`\]")
HARD_CODED_RE = re.compile(r"Implement `?tickets/[A-Z]{2,}-\d+\.md`?", re.IGNORECASE)
REMOTE_REQ_RE = re.compile(r"(?:git push|push origin|verify.*(?:remote|origin)|rev-parse origin|visible on public .*?main)", re.IGNORECASE)


def extract_primary_ticket_id(text: str) -> Optional[str]:
    m = re.search(r"Complete \[`([A-Z]{2,}-\d+)`\]", text, re.IGNORECASE)
    if m:
        return m.group(1)
    ids = TICKET_RE.findall(text)
    return ids[0] if len(ids) == 1 else None


def extract_state(text: str) -> str:
    m = re.search(r"State[:\s]+(\w+)", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    if "stop for review" in text.lower() or "awaiting_review" in text.lower():
        return "AWAITING_REVIEW"
    if "blocked" in text.lower():
        return "BLOCKED"
    return "UNKNOWN"


def extract_next_auth(text: str) -> str:
    m = re.search(r"Next ticket authorized[:\s]*([A-Z-]+|NONE)", text, re.IGNORECASE)
    return m.group(1).upper() if m else "UNKNOWN"


def find_referenced_docs(text: str) -> List[str]:
    refs = []
    for m in re.finditer(r"\[[^\]]+\]\(([^)]+?\.md)\)", text, re.IGNORECASE):
        ref = m.group(1).strip().lstrip("./")
        refs.append(ref)
    return refs


def check_file_exists(root: Path, rel: str) -> bool:
    p = root / rel
    if p.exists():
        return True
    for base in (root, root / "docs", root / "docs/handoff"):
        if (base / rel).exists():
            return True
    return False


def validate(root: Path) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if not (root / "AGENTS.md").exists():
        errors.append("root AGENTS.md does not exist")

    current_task_p = root / "docs/handoff/CURRENT_TASK.md"
    if not current_task_p.exists():
        errors.append("CURRENT_TASK.md does not exist")
        return False, errors

    ct_text = current_task_p.read_text()
    ticket_id = extract_primary_ticket_id(ct_text)
    if ct_text.lower().count("complete [`") > 1:
        errors.append("CURRENT_TASK.md must identify exactly one ticket (multiple declarations)")

    completes = re.findall(r"Complete \[`[A-Z]{2,}-\d+`\]", ct_text, re.IGNORECASE)
    all_ticket_ids = TICKET_RE.findall(ct_text) if TICKET_RE else []
    if not ticket_id:
        errors.append("CURRENT_TASK.md must identify exactly one ticket using Complete [`ID`]")
        return False, errors
    if len(completes) > 1 or len(all_ticket_ids) > 1:
        errors.append("CURRENT_TASK.md must identify exactly one ticket (multiple declarations)")

    ticket_p = root / "tickets" / f"{ticket_id}.md"
    if not ticket_p.exists():
        errors.append(f"Ticket file tickets/{ticket_id}.md does not exist")
        return False, errors

    ticket_text = ticket_p.read_text()

    task_state = extract_state(ct_text)
    if task_state not in VALID_STATES:
        errors.append(f"Invalid task state '{task_state}'")

    ticket_status = extract_state(ticket_text)
    sm = re.search(r"\*\*Status:\*\*\s*(\S+)", ticket_text, re.IGNORECASE)
    if sm:
        ticket_status = sm.group(1).upper()
    if ticket_status not in VALID_STATES or ticket_status != task_state:
        errors.append(f"Ticket status ({ticket_status}) does not match task state ({task_state})")

    for ref in set(find_referenced_docs(ct_text) + find_referenced_docs(ticket_text)):
        if not check_file_exists(root, ref):
            errors.append(f"Referenced governing document missing: {ref}")

    next_auth = extract_next_auth(ct_text)
    if task_state in {"BLOCKED", "AWAITING_REVIEW"} and next_auth != "NONE":
        errors.append(f"Next ticket authorized must be NONE when state is {task_state} (got {next_auth})")

    hermes = root / "docs/handoff/HERMES_START_HERE.md"
    if hermes.exists():
        if HARD_CODED_RE.search(hermes.read_text()):
            errors.append("HERMES_START_HERE.md contains hard-coded ticket assignment")
    else:
        errors.append("HERMES_START_HERE.md missing")

    for doc in [root / "AGENTS.md", current_task_p, hermes, ticket_p]:
        if doc.exists() and REMOTE_REQ_RE.search(doc.read_text()):
            errors.append(f"{doc.name} requires development agents to push or verify remotes")

    return len(errors) == 0, errors


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    ok, errors = validate(root)
    if ok:
        print("Repo control check: PASS")
        sys.exit(0)
    else:
        print("Repo control check: FAIL")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
