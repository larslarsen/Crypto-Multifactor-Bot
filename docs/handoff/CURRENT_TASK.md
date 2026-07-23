# CURRENT_TASK

Ticket: EXEC-001
State: AWAITING_REVIEW
Next required actor: Lead Quant (Reviewer) — review Sr Dev implementation
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**
With the completion of UNIVERSE-002, the data and research foundations are sealed. We are now officially entering the **Execution** phase defined in `IMPLEMENTATION_SEQUENCE.md`.

I am drafting and authorizing **EXEC-001** (Paper Execution Runtime, Sequence #25). 
This transitions our evaluation capability from purely historical backtesting (`PORT-001`) into a stateful, forward-walking paper trading environment. Crucially, this execution layer must be strongly coupled to `PROMO-001`: it may only execute artifacts verified to be in the `PAPER_APPROVED` state by the Promotion Registry.

## Governing documents

- tickets/EXEC-001.md (AWAITING_REVIEW)
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution tests/execution
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution tests/execution
4. python3 scripts/check_repo_control.py
5. Test asserting PaperBroker raises explicit error if artifact is not PAPER_APPROVED.
