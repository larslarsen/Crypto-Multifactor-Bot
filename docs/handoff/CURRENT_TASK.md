# CURRENT_TASK

Ticket: EXP-007
State: READY
Next required actor: Sr Dev (Strong Model) — full-window screen of remaining TSMOM candidates
Next ticket authorized: EXP-007

**Reviewer Decision (Architecture & Ticket Selection):**

PAPER-007 ACCEPTED (REVIEW-0198). Full-window `tsmom_14_0` **−0.63%**, risk OK, gate false. Multi-fold ≠ continuous path. **No LIVE.**

Authorizing **EXP-007**: full-window paper screen for `tsmom_14_3` and `tsmom_60_0` (same protocol as PAPER-007); artifact `23_TSMOM_FULLWINDOW_SCREEN.json`; `live_eligible: false`.

**Policy:** No LIVE.

## Governing documents

- tickets/EXP-007.md (READY)
- tickets/PAPER-007.md (ACCEPTED)
- docs/reviews/REVIEW-0198_PAPER-007_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. 23_TSMOM_FULLWINDOW_SCREEN.json present
4. python3 scripts/check_repo_control.py
