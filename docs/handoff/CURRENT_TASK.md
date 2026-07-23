# CURRENT_TASK

Ticket: EXP-004
State: READY
Next required actor: Sr Dev (Strong Model) — TSMOM lookback grid under neutral risk
Next ticket authorized: EXP-004

**Reviewer Decision (Architecture & Ticket Selection):**

ALLOC-001 ACCEPTED (REVIEW-0192). Neutrality-preserving enforcement works (−6.52% vs old −15.36%). LIVE still blocked.

Authorizing **EXP-004**: grid search TSMOM lookback/skip under ALLOC-001 risk; artifact `18_TSMOM_GRID_RESULTS.json`; `live_eligible: false`.

**Policy:** No LIVE.

## Governing documents

- tickets/EXP-004.md (READY)
- tickets/ALLOC-001.md (ACCEPTED)
- docs/reviews/REVIEW-0192_ALLOC-001_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. 18_TSMOM_GRID_RESULTS.json present
4. python3 scripts/check_repo_control.py
