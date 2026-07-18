#!/usr/bin/env python3
"""check_repo_control.py

Dependency-free semantic repository-control validator for GOV-001.

The active ticket is declared in `docs/handoff/CURRENT_TASK.md` using a small
fixed field format. This script checks that:

- exactly one `Ticket:` field is present (the active ticket);
- the active ticket file exists under `tickets/`;
- the task state is one of the valid ticket states;
- the ticket's own status matches the current-task state;
- every document referenced under `Governing documents:` exists;
- `Next ticket authorized` is `NONE` or a complete ticket ID containing digits;
- blocked or awaiting-review work requires `NONE`;
- governance docs do not hard-code ticket assignments or require development
  agents to push / inspect remotes / verify public GitHub state.

It is a routine integration of GOV-001. It adds no dependencies and does not
redesign validation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Valid ticket lifecycle states for GOV-001.
VALID_STATES = {
    "DRAFT",
    "READY",
    "IN_PROGRESS",
    "BLOCKED",
    "AWAITING_REVIEW",
    "ACCEPTED",
    "SUPERSEDED",
}

# A complete ticket ID contains one or more digits (e.g. GOV-001, CAT-001A).
TICKET_ID_RE = re.compile(r"^[A-Z]{2,}-\d")

# A hard-coded assignment in a doc looks like "Implement tickets/GOV-001.md"
# or "do tickets/CAT-001.md". The control plane must not hard-code tickets in
# durable docs other than CURRENT_TASK.md.
HARD_CODED_RE = re.compile(r"(?:implement|do|complete)\s+`?tickets/[A-Z]{2,}-\d+", re.IGNORECASE)

# Development-agent push / remote-verification requirements are rejected. The
# owner publishes commits; development agents commit locally and stop. We match
# requirement phrases only (e.g. "git push", "push origin", "rev-parse origin",
# "verify ... remote/origin", "visible on public ... main"), not statements that
# prohibit those actions.
REMOTE_REQ_RE = re.compile(
    r"(?:git push|push origin|rev-parse origin|visible on public .*?main|"
    r"verify.*(?:remote|origin))",
    re.IGNORECASE,
)


def extract_ticket_fields(text: str) -> List[str]:
    """Return all `Ticket:` field values (case-insensitive field name)."""
    return re.findall(r"^\s*Ticket:\s*(\S+)\s*$", text, re.IGNORECASE | re.MULTILINE)


def extract_state(text: str) -> Optional[str]:
    m = re.search(r"^\s*State:\s*(\S+)\s*$", text, re.IGNORECASE | re.MULTILINE)
    if m:
        return m.group(1).upper()
    return None


def extract_next_auth(text: str) -> Optional[str]:
    m = re.search(
        r"^\s*Next ticket authorized:\s*(\S+)\s*$", text, re.IGNORECASE | re.MULTILINE
    )
    return m.group(1).upper() if m else None


def find_referenced_docs(text: str) -> List[str]:
    """Find documents listed in a `Governing documents:` block (one path per line)."""
    refs: List[str] = []
    lines = text.splitlines()
    in_block = False
    for line in lines:
        if re.match(r"^\s*Governing documents:\s*$", line, re.IGNORECASE):
            in_block = True
            continue
        if in_block:
            # A new top-level field terminates the block.
            if re.match(r"^\s*[A-Z][A-Za-z ]+:\s*", line) and not line.lstrip().startswith("-"):
                break
            m = re.match(r"^\s*-\s+(\S+\.md)\s*$", line)
            if m:
                refs.append(m.group(1).strip().lstrip("./"))
            elif line.strip() == "":
                continue
            else:
                break
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

    # Exactly one active ticket.
    ticket_fields = extract_ticket_fields(ct_text)
    if len(ticket_fields) == 0:
        errors.append("CURRENT_TASK.md must declare exactly one `Ticket:` field")
    elif len(ticket_fields) > 1:
        errors.append("CURRENT_TASK.md must declare exactly one `Ticket:` field (multiple found)")

    ticket_id = ticket_fields[0] if ticket_fields else None
    if ticket_id and not TICKET_ID_RE.match(ticket_id):
        errors.append(f"Ticket '{ticket_id}' is not a valid ticket ID")

    if ticket_id:
        ticket_p = root / "tickets" / f"{ticket_id}.md"
        if not ticket_p.exists():
            errors.append(f"Ticket file tickets/{ticket_id}.md does not exist")
            ticket_p = None
    else:
        ticket_p = None

    # Task state.
    task_state = extract_state(ct_text)
    if task_state is None:
        errors.append("CURRENT_TASK.md must declare a `State:` field")
    elif task_state not in VALID_STATES:
        errors.append(f"Invalid task state '{task_state}'")

    # Ticket status must match the current-task state.
    if ticket_p is not None and task_state in VALID_STATES:
        ticket_text = ticket_p.read_text()
        sm = re.search(r"\*\*Status:\*\*\s*(\S+)", ticket_text, re.IGNORECASE)
        ticket_status = sm.group(1).upper() if sm else None
        if ticket_status is None:
            errors.append(f"Ticket {ticket_id} must declare a `**Status:**` field")
        elif ticket_status not in VALID_STATES:
            errors.append(f"Invalid ticket status '{ticket_status}'")
        elif ticket_status != task_state:
            errors.append(
                f"Ticket status ({ticket_status}) does not match task state ({task_state})"
            )
    else:
        ticket_text = ""

    # Referenced governing documents must exist.
    for ref in find_referenced_docs(ct_text):
        if not check_file_exists(root, ref):
            errors.append(f"Referenced governing document missing: {ref}")

    # Next ticket authorized.
    next_auth = extract_next_auth(ct_text)
    if next_auth is None:
        errors.append("CURRENT_TASK.md must declare a `Next ticket authorized:` field")
    elif next_auth == "NONE":
        pass
    elif TICKET_ID_RE.match(next_auth):
        pass
    else:
        errors.append(
            f"Next ticket authorized must be NONE or a complete ticket ID (got {next_auth})"
        )

    # Blocked / awaiting-review work cannot authorize a next ticket.
    if task_state in {"BLOCKED", "AWAITING_REVIEW"} and next_auth not in (None, "NONE"):
        errors.append(
            f"Next ticket authorized must be NONE when state is {task_state} (got {next_auth})"
        )

    # HERMES_START_HERE must not hard-code a ticket assignment.
    hermes = root / "docs/handoff/HERMES_START_HERE.md"
    if hermes.exists():
        if HARD_CODED_RE.search(hermes.read_text()):
            errors.append("HERMES_START_HERE.md contains a hard-coded ticket assignment")
    else:
        errors.append("HERMES_START_HERE.md missing")

    # No governance doc may require development agents to push or verify remotes.
    for doc in [root / "AGENTS.md", current_task_p, hermes, ticket_p] if ticket_p else [
        root / "AGENTS.md",
        current_task_p,
        hermes,
    ]:
        if doc is not None and doc.exists() and REMOTE_REQ_RE.search(doc.read_text()):
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
