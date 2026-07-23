# PAPER-006 — Risk-Compliant Real Paper Gate

**Priority:** P0  
**Status:** AWAITING_REVIEW  
**Dependencies:** PAPER-005 (ACCEPTED), DATA-003 (ACCEPTED)  
**Layer:** execution / portfolio allocation / research evidence  
**Architecture:** tighten paper path risk; **no LIVE orders; live_eligible stays false** unless all gate prongs met (still no LIVE promotion without separate LIVE ticket).

## Objective

Close the PAPER-005 gap: session showed +PnL on real as-of but **failed** `meets_risk_limits` (max single weight 0.5 > 0.15). Make allocation risk-compliant and report an honest LIVE *readiness* flag (not LIVE enablement).

## Scope

1. **Allocator / paper loop**
   - Enforce `max_single_weight` (default 0.15) and `max_gross_leverage` (default 1.0) on target weights before `PaperBroker.rebalance` (fail closed or clip-with-renormalize — pick one, document, test).
   - Ensure observed leverage/weight passed into `ProspectiveEvaluator` match post-enforcement weights.

2. **Session gate definition** (artifact field)
   - `live_gate_satisfied` := `data_mode==real_asof` AND `net_return>0` AND `meets_risk_limits` AND `is_complete`
   - `live_eligible` remains **false** in this ticket (no LIVE promotion)

3. **Re-run evidence**
   - Re-run non-dry-run paper on existing or refreshed real bars
   - Write/update `research/sprint_004/14_RISK_COMPLIANT_PAPER_SESSION.json` (and refresh 13 or supersede with clear pointer)

4. **Tests**
   - Unit: weights exceeding 0.15 are rejected or clipped per chosen policy
   - Unit: `live_gate_satisfied` false when risk fails even if return > 0
   - Existing acquisition/execution suite still green

## Out of Scope

- LIVE_APPROVED / funded trading  
- Changing TSMOM factor math (allocation only)  
- Full multi-year backtest redesign (optional stretch)

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution scripts/`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution`
4. Artifact `14_RISK_COMPLIANT_PAPER_SESSION.json` present; `live_eligible: false`
5. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
