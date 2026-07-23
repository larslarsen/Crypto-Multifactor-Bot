# CURRENT_TASK

Ticket: EXEC-002
State: ACCEPTED
Next required actor: Sr Engineer (Weak Model) — record review and next-ticket selection
Next ticket authorized: NONE

**Reviewer Decision:**

I have reviewed `src/cryptofactors/execution/live.py` against the AUD-006 hard constraints.

**EXEC-002 Verdict: ACCEPT**

All AUD-006 constraints satisfied:
- `LiveBroker` is fully isolated from `PaperBroker` (separate module, no shared state, no dual-mode flag).
- `LIVE_APPROVED` gate enforced on init and every `submit_order` call; fail-closed.
- Pre-trade risk checks (gross leverage ≤ 1.0, single-asset ≤ 0.15) run before any network call.
- Credentials from environment only; injectable for tests.
- Kill-switch blocks new orders; registry revocation auto-activates kill.
- Read-only promotion registry access.
- Mocked venue only in unit tests.

Sequence #26 fully implemented and accepted.

## Governing documents

- tickets/EXEC-002.md (ACCEPTED)
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
