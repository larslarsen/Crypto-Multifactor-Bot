# CURRENT_TASK

Ticket: PAPER-006
State: READY
Next required actor: Sr Dev (Strong Model) — risk-compliant real paper gate
Next ticket authorized: PAPER-006

**Reviewer Decision (Architecture & Ticket Selection):**

PAPER-005 ACCEPTED (REVIEW-0189). Real as-of session +1.37% net, but **`meets_risk_limits: false`** (max weight 0.5 > 0.15). **`live_gate_satisfied: true` overstated.** LIVE still blocked.

Authorizing **PAPER-006**:
1. Enforce max single weight 0.15 + gross lev 1.0 on paper targets
2. Honest `live_gate_satisfied` = real_asof ∧ return>0 ∧ risk ∧ complete
3. Re-run evidence → `14_RISK_COMPLIANT_PAPER_SESSION.json`; `live_eligible: false`

**Policy:** No LIVE promotion in this ticket.

## Governing documents

- tickets/PAPER-006.md (READY)
- tickets/PAPER-005.md (ACCEPTED)
- docs/reviews/REVIEW-0189_PAPER-005_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution
4. 14_RISK_COMPLIANT_PAPER_SESSION.json + live_eligible false
5. python3 scripts/check_repo_control.py
