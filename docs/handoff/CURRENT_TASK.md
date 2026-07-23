# CURRENT_TASK

Ticket: PAPER-009
State: READY
Next required actor: Sr Dev (Strong Model) — re-validate frozen 14_3 on PASS bars
Next ticket authorized: PAPER-009

**Reviewer Decision (Architecture & Ticket Selection):**

DATA-005 ACCEPTED (REVIEW-0201). New bars **PASS** (`ds_0cb6415f…`) but `resolve_latest` still returns REJECTED (epoch created_at). **No LIVE.**

Authorizing **PAPER-009**: pin PASS dataset; re-run frozen `tsmom_14_3` paper; optional/required catalog resolve fix; artifact `26_TSMOM_14_3_PASS_BARS_PAPER.json`; `live_eligible: false`.

**Policy:** No LIVE.

## Governing documents

- tickets/PAPER-009.md (READY)
- tickets/DATA-005.md (ACCEPTED)
- docs/reviews/REVIEW-0201_DATA-005_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ tests/market/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors scripts/
3. 26_TSMOM_14_3_PASS_BARS_PAPER.json present
4. python3 scripts/check_repo_control.py
