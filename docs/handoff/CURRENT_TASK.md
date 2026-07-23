# CURRENT_TASK

Ticket: HOLDOUT-001
State: ACCEPTED
Next required actor: Jr Engineer (Weak Model) — gates, records, commit, push
Next ticket authorized: NONE

**Reviewer Decision (Authorization):**
With PROMO-001 accepted, the Promotion Registry enforces the state machine up to `PAPER_APPROVED`. To satisfy the `LIVE_APPROVED` gate, we must fulfill the prospective paper observation requirement (Sequence #24).

I have drafted and authorized **HOLDOUT-001** (Prospective Holdout Evaluation, Sequence #24). This will implement the evaluation harness for out-of-sample paper trading validation.

## Governing documents

- tickets/HOLDOUT-001.md (ACCEPTED)
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/serving/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/serving tests/serving
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/serving tests/serving
4. python3 scripts/check_repo_control.py
