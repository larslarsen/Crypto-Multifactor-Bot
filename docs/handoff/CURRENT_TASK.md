# CURRENT_TASK

Ticket: DATA-005
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

PAPER-008 ACCEPTED (REVIEW-0200). `tsmom_14_3` frozen, gate true, **live_eligible false**. LIVE blocked on **REJECTED** bar quality + selection caveats.

Authorizing **DATA-005**: quality-cleared `market_bars` (PASS/PASS_WITH_WARNINGS) for same universe/span; artifact `25_QUALITY_CLEARED_BARS_REPORT.json`; no LIVE; no TSMOM re-tune.

**Policy:** No LIVE.

## Governing documents

- tickets/DATA-005.md (READY)
- tickets/PAPER-008.md (ACCEPTED)
- docs/reviews/REVIEW-0200_PAPER-008_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors scripts/
3. 25_QUALITY_CLEARED_BARS_REPORT.json present with PASS or PASS_WITH_WARNINGS
4. python3 scripts/check_repo_control.py
