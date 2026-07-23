# CURRENT_TASK

Ticket: EXP-003
State: READY
Next required actor: Sr Dev (Strong Model) — risk-compliant MOM-TS real-data diagnosis
Next ticket authorized: EXP-003

**Reviewer Decision (Architecture & Ticket Selection):**

PAPER-006 ACCEPTED (REVIEW-0190). Risk enforcement + honest gate land. Risk-compliant real paper **−3.31%** → LIVE still blocked. Unconstrained +1.37% was concentration, not policy-valid edge.

Authorizing **EXP-003**:
1. Diagnose unconstrained vs enforced return gap
2. Longer real-window risk-enforced session if data allows
3. Artifacts under research/sprint_004/; `live_eligible: false`

**Policy:** No LIVE.

## Governing documents

- tickets/EXP-003.md (READY)
- tickets/PAPER-006.md (ACCEPTED)
- docs/reviews/REVIEW-0190_PAPER-006_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. 15_MOMTS_RISK_DIAGNOSIS.json present
4. python3 scripts/check_repo_control.py
