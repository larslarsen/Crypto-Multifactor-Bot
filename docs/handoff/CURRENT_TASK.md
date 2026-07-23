# CURRENT_TASK

Ticket: EXP-004
State: AWAITING_REVIEW
Next required actor: Lead Quantitative Finance Researcher/Engineer (reviewer)
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

ALLOC-001 ACCEPTED (REVIEW-0192). Neutrality-preserving enforcement works (−6.52% vs old −15.36%). LIVE still blocked.

Authorizing **EXP-004**: grid search TSMOM lookback/skip under ALLOC-001 risk; artifact `18_TSMOM_GRID_RESULTS.json`; `live_eligible: false`.

**Policy:** No LIVE.

## Implemented

- Added `scripts/research/run_tsmom_grid.py` (EXP-004) that:
  - Reuses the EXP-003/ALLOC-001 real backfill (`exp003.db` / `data/exp003_store`).
  - Loads the canonical `market_bars` dataset into an in-memory `_InMemoryMarketBarStore` for fast grid evaluation.
  - Runs risk-enforced paper sessions for lookbacks `{7, 14, 30, 60, 90}` and skips `{0, 3, 7}` (skipping invalid `lookback <= skip` pairs).
  - Records per-cell: net return, max weight, gross, max/avg |net|, meets_risk, live_gate_satisfied, and `live_eligible: false`.
- Produced `research/sprint_004/18_TSMOM_GRID_RESULTS.json`:
  - 14 valid configurations evaluated over 50 weekly decisions (2025-08-08 → 2026-07-23).
  - Best cell: **tsmom_14_0** (lookback 14, skip 0) with **+31.12%** net return, risk-compliant, `live_gate_satisfied: true`.
  - 11 of 14 cells are risk-compliant and profitable (`live_gate_satisfied: true`).
  - `recommend_live_path: true` because at least one cell passed the gate, with note that LIVE promotion still requires a separate ticket and owner policy.
  - `live_eligible: false` globally and per row.
- No LIVE. No live orders.

## Governing documents

- tickets/EXP-004.md (AWAITING_REVIEW)
- tickets/ALLOC-001.md (ACCEPTED)
- docs/reviews/REVIEW-0192_ALLOC-001_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. 18_TSMOM_GRID_RESULTS.json present
4. python3 scripts/check_repo_control.py
