# CURRENT_TASK

Ticket: PAPER-006
State: AWAITING_REVIEW
Next required actor: Lead Quantitative Finance Researcher/Engineer (reviewer)
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

PAPER-005 ACCEPTED (REVIEW-0189). Real as-of session +1.37% net, but **`meets_risk_limits: false`** (max weight 0.5 > 0.15). **`live_gate_satisfied: true` overstated.** LIVE still blocked.

Authorizing **PAPER-006**:
1. Enforce max single weight 0.15 + gross lev 1.0 on paper targets
2. Honest `live_gate_satisfied` = real_asof ∧ return>0 ∧ risk ∧ complete
3. Re-run evidence → `14_RISK_COMPLIANT_PAPER_SESSION.json`; `live_eligible: false`

**Policy:** No LIVE promotion in this ticket.

## Implemented

- Added `src/cryptofactors/execution/risk_limits.py` with deterministic `enforce_risk_limits` (clip each weight to 0.15, then scale gross to 1.0) and `compute_live_gate_satisfied` (real_asof ∧ return>0 ∧ risk ∧ complete).
- Wired enforcement into `FactorDrivenPaperLoop` before `PaperBroker.rebalance`; observed max weight / leverage now reflect post-enforcement weights.
- Updated existing tests: `test_risk_limits_enforced_even_with_small_universe` verifies risk compliance with 4 assets; `test_drawdown_alert_callback_triggers` adjusted to the smaller position sizes under the 0.15 cap.
- Added unit tests for `enforce_risk_limits` and `compute_live_gate_satisfied`.
- Re-ran non-dry-run paper on existing real bars. Result: risk-compliant (`meets_risk_limits: true`) but net return **-3.31%**; `live_gate_satisfied: false`; `live_eligible: false`.
- Created `research/sprint_004/14_RISK_COMPLIANT_PAPER_SESSION.json` and corrected/superseded `13_REAL_PAPER_SESSION.json` (fixed `live_gate_satisfied` to `false` and added `superseded_by` pointer).
- No LIVE. No live orders.

## Governing documents

- tickets/PAPER-006.md (AWAITING_REVIEW)
- tickets/PAPER-005.md (ACCEPTED)
- docs/reviews/REVIEW-0189_PAPER-005_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution
4. 14_RISK_COMPLIANT_PAPER_SESSION.json + live_eligible false
5. python3 scripts/check_repo_control.py
