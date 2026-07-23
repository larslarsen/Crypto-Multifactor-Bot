# CURRENT_TASK

Ticket: PAPER-005
State: READY
Next required actor: Sr Dev (Strong Model) — real as-of paper session evidence
Next ticket authorized: PAPER-005

**Reviewer Decision (Architecture & Ticket Selection):**

DATA-003 ACCEPTED (REVIEW-0188). B5 fixed; factor compute works on adapter + real bars.

Authorizing **PAPER-005**: non-dry-run paper session on published real (or durable real-published) as-of bars; artifact `13_REAL_PAPER_SESSION.json`; `live_eligible: false` always in this ticket.

**Policy:** LIVE blocked until profitable real paper — this ticket only measures; does not promote LIVE.

## Governing documents

- tickets/PAPER-005.md (READY)
- tickets/DATA-003.md (ACCEPTED)
- docs/reviews/REVIEW-0188_DATA-003_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/acquisition/ tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. research/sprint_004/13_REAL_PAPER_SESSION.json present
4. python3 scripts/check_repo_control.py
