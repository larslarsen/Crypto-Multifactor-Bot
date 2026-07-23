# CURRENT_TASK

Ticket: EXEC-002
State: AWAITING_REVIEW
Next required actor: Lead Quant (Reviewer) — review live execution routing
Next ticket authorized: NONE

**Reviewer Decision (AUD-006 + Ticket Selection):**

I have reviewed `docs/reviews/AUD-006_RISK_REPORT.md` against the live codebase.

**AUD-006 Verdict: ACCEPT / PASS**

Confirmed:
- `PaperBroker` has no live credentials or exchange HTTP paths.
- `LIVE_APPROVED` requires owner authority + paper observation reference; discovery fails closed.
- Terminal states are sealed.
- Gross leverage ≤ 1.0 is enforced in paper rebalance; single-asset ≤ 0.15 remains a mandatory pre-trade check for live.

No blocking FX tickets. Sequence #26 is authorized under the hard constraints recorded in `tickets/EXEC-002.md`.

I am authorizing **EXEC-002** (Live Execution Routing, Sequence #26).

## Governing documents

- tickets/EXEC-002.md (AWAITING_REVIEW)
- tickets/AUD-006.md (ACCEPTED)
- docs/reviews/AUD-006_RISK_REPORT.md
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution tests/execution
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution tests/execution
4. python3 scripts/check_repo_control.py
5. Unapproved artifact fails before any HTTP call
6. Leverage / single-asset pre-trade limits enforced
7. Mocked HTTP only in unit tests
