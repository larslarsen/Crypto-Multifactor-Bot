# CURRENT_TASK

Ticket: ALLOC-001
State: AWAITING_REVIEW
Next required actor: Lead Quantitative Finance Researcher/Engineer (reviewer)
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

EXP-003 ACCEPTED (REVIEW-0191). Longer real window: unconstrained **−5.28%**, risk-enforced **−15.36%**. LIVE blocked. Clip-and-renormalize causes large **net exposure drift** (up to ±0.35).

Authorizing **ALLOC-001**:
1. Neutrality-preserving enforce_risk_limits (long/short leg rescale)
2. Tests for net≈0 after clip under caps
3. Evidence `17_NEUTRAL_RISK_SESSION.json`; `live_eligible: false`

**Policy:** No LIVE.

## Implemented

- Replaced clip-and-renormalize with **neutrality-preserving leg rescale** in `src/cryptofactors/execution/risk_limits.py`:
  - Clip each weight to `[-0.15, 0.15]`.
  - For L/S books, rescale the long and short legs independently so `sum(long) == sum(|short|)` and `|net| ≈ 0` while respecting `max_gross_leverage / 2` per leg.
  - Directional books (only one leg) are scaled to fit the gross cap; residual net is documented as irreducible.
  - Updated module docstring to describe the new policy.
- Added unit tests in `tests/execution/test_paper_loop.py` covering:
  - Neutral L/S book with one leg clipped → post net ≈ 0, max |w| ≤ 0.15, gross ≤ 1.0
  - Both legs clipped → net ≈ 0
  - Gross cap enforced symmetrically
  - Directional book scaled to gross cap
- Updated existing `test_risk_limits_enforced_even_with_small_universe` and `test_drawdown_alert_callback_triggers` to remain valid under the new policy.
- Added `scripts/research/run_neutral_risk_session.py` to produce the evidence artifact.
- Re-ran the same 50-week real window (2025-08-08 → 2026-07-23) used by EXP-003:
  - **−6.52%** net return
  - max |single weight| = 0.15, gross = 1.0
  - Net exposure ≈ 0 when both L/S legs present; documented directional residual |net| = 0.5 when factor frame is one-sided.
  - `meets_risk_limits: true`, `live_gate_satisfied: false`, `live_eligible: false`.
- Produced `research/sprint_004/17_NEUTRAL_RISK_SESSION.json`.
- No LIVE. No live orders.

## Governing documents

- tickets/ALLOC-001.md (AWAITING_REVIEW)
- tickets/EXP-003.md (ACCEPTED)
- docs/reviews/REVIEW-0191_EXP-003_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution
4. 17_NEUTRAL_RISK_SESSION.json + live_eligible false
5. python3 scripts/check_repo_control.py
