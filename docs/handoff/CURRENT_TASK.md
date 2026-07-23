# CURRENT_TASK

Ticket: PAPER-002
State: AWAITING_REVIEW
Next required actor: Lead Quant (Reviewer) — review paper holdout observation hardening
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

PAPER-001 delivered a real factor-driven paper loop, but REVIEW-0179 left a LIVE blocker: `paper_observation_reference` is null and holdout inputs used placeholder period metrics.

I am authorizing **PAPER-002** (Paper Holdout Observation Hardening) to:
1. Fix period PnL and observed risk metrics in `FactorDrivenPaperLoop`.
2. Integrate `ProspectiveEvaluator` without silent failure.
3. Emit a non-null observation reference suitable for a future LIVE gate payload.

No LIVE ticket until this observation path is accepted.

## Governing documents

- tickets/PAPER-002.md (READY)
- tickets/PAPER-001.md (ACCEPTED)
- docs/reviews/REVIEW-0179_PAPER-001_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/serving/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution src/cryptofactors/serving scripts/run_paper_momts.py
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution src/cryptofactors/serving scripts/run_paper_momts.py
4. .venv/bin/python scripts/run_paper_momts.py --dry-run
5. python3 scripts/check_repo_control.py
