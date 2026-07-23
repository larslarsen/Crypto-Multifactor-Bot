# CURRENT_TASK

Ticket: ALLOC-001
State: READY
Next required actor: Sr Dev (Strong Model) — neutrality-preserving risk enforcement
Next ticket authorized: ALLOC-001

**Reviewer Decision (Architecture & Ticket Selection):**

EXP-003 ACCEPTED (REVIEW-0191). Longer real window: unconstrained **−5.28%**, risk-enforced **−15.36%**. LIVE blocked. Clip-and-renormalize causes large **net exposure drift** (up to ±0.35).

Authorizing **ALLOC-001**:
1. Neutrality-preserving enforce_risk_limits (long/short leg rescale)
2. Tests for net≈0 after clip under caps
3. Evidence `17_NEUTRAL_RISK_SESSION.json`; `live_eligible: false`

**Policy:** No LIVE.

## Governing documents

- tickets/ALLOC-001.md (READY)
- tickets/EXP-003.md (ACCEPTED)
- docs/reviews/REVIEW-0191_EXP-003_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution
4. 17_NEUTRAL_RISK_SESSION.json + live_eligible false
5. python3 scripts/check_repo_control.py
