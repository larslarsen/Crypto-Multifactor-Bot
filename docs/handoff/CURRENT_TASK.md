# CURRENT_TASK

Ticket: PAPER-004
State: AWAITING_REVIEW
Next required actor: Lead Quant (Reviewer) — review paper ops equity and resume fixes
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

Paper path: 3 (ops fixes) → 4 (hardening toward LIVE). LIVE blocked until paper trading is profitable on real data.

Authorizing **PAPER-004** to close the two REVIEW-0181 caveats:
1. Fix `PaperOpsMonitor` to use MTM equity not cash.
2. Add broker resume-from-store.

Next ticket after this (HARDEN-001 or LIVE-PREP) will wire exchange API stubs and run on real as-of store data.

## Governing documents

- tickets/PAPER-004.md (READY)
- tickets/PAPER-003.md (ACCEPTED)
- docs/reviews/REVIEW-0181_PAPER-003_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution
4. python3 scripts/check_repo_control.py
