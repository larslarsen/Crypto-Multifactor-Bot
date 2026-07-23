# CURRENT_TASK

Ticket: PORT-002
State: AWAITING_REVIEW
Next required actor: Lead Quant (Reviewer) — review Perpetual Long/Short Portfolio Simulator
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

The user requested: "Do whatever gets experiments happening the fastest". 
`EXP-2026-019` and `020` are in `READY_TO_RUN` state, but they require "shortable perpetual cells" and "liquidations" which are not yet supported by our basic `PortfolioSimulator` (PORT-001). We now have BitMEX funding (FUND-005).

I am authorizing **PORT-002** (Perpetual Long/Short Portfolio Simulator) to bridge this final mechanical gap. Once this is implemented, the Sr Dev will update the `momts_runner.py` to run the true perpetual L/S experiment, fulfilling the registration requirements.

## Governing documents

- tickets/PORT-002.md (READY)
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/portfolio/ tests/experiments/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/portfolio src/cryptofactors/experiments
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/portfolio src/cryptofactors/experiments
4. python3 scripts/check_repo_control.py
