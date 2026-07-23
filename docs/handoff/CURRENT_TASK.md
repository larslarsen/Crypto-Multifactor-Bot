# CURRENT_TASK

Ticket: EXP-006
State: AWAITING_REVIEW
Next required actor: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

DATA-004 ACCEPTED (REVIEW-0195). Bars **2024-01-01→2026-07-23** (~30.7m). Quality REJECTED is structural for native 1d BAR-001 path (same as prior research set). **No LIVE.**

Authorizing **EXP-006**: frozen TSMOM multi-fold/long OOS on DATA-004 dataset; artifact `21_TSMOM_EXTENDED_OOS.json`; `live_eligible: false`. Do not mutate 08–20.

**Policy:** No LIVE.

## Governing documents

- tickets/EXP-006.md (AWAITING_REVIEW)
- tickets/DATA-004.md (ACCEPTED)
- docs/reviews/REVIEW-0195_DATA-004_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. 21_TSMOM_EXTENDED_OOS.json present
4. python3 scripts/check_repo_control.py
