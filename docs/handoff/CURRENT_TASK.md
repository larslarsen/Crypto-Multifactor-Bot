# CURRENT_TASK

Ticket: PROMO-002
State: READY
Next required actor: Sr Dev (Strong Model) — implement paper promotion and paper execution session script
Next ticket authorized: PROMO-002

**Reviewer Decision (Architecture & Ticket Selection):**

The user instructed: "we should get paper trading working if experiments have promoted to that level, if not, we should add new families until we get something that promotes".

`MOM-TS-01` (`EXP-2026-019` / `tsmom_30_7`) has passed all confirmatory experiment gates with positive net return (+4.9%), zero liquidations, and clean L/S attribution under BitMEX funding and PORT-002 perpetual simulation mechanics. It has an accepted scientific review (`REVIEW-0177`).

Therefore, `MOM-TS-01` qualifies for promotion to `PAPER_APPROVED`. 

I am authorizing **PROMO-002** (Paper Promotion and Paper Execution for MOM-TS-01) to:
1. Register and promote model artifact `mod_tsmom_30_7_v1` to `PAPER_APPROVED` via `PromotionRegistry`.
2. Run a stateful forward-walking paper trading session via `PaperBroker` (EXEC-001) with strict gate verification enabled.
3. Emit `research/sprint_004/07_PAPER_TRADING_RESULTS.json`.

## Governing documents

- tickets/PROMO-002.md (READY)
- docs/reviews/REVIEW-0177_EXP-002_ACCEPTED.md
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/promotion/ tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check scripts/promote_and_run_paper.py
3. .venv/bin/python -m mypy --no-error-summary scripts/promote_and_run_paper.py
4. .venv/bin/python scripts/promote_and_run_paper.py --dry-run
5. python3 scripts/check_repo_control.py
