# CURRENT_TASK

Ticket: PAPER-008
State: AWAITING_REVIEW
Next required actor: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

EXP-007 ACCEPTED (REVIEW-0199). Full-window winner **tsmom_14_3 +16.70%** (gate true). Selection-path + quality caveats. **No LIVE.**

Authorizing **PAPER-008**: dedicated paper package for `tsmom_14_3`; artifact `24_TSMOM_14_3_PAPER_SESSION.json`; `candidate_frozen: true`; `live_eligible: false`.

**Policy:** No LIVE.

## Governing documents

- tickets/PAPER-008.md (AWAITING_REVIEW)
- tickets/EXP-007.md (ACCEPTED)
- docs/reviews/REVIEW-0199_EXP-007_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. 24_TSMOM_14_3_PAPER_SESSION.json present
4. python3 scripts/check_repo_control.py
