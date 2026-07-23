# PROMO-002 — Paper Promotion and Paper Execution for MOM-TS-01

**Priority:** P0
**Status:** AWAITING_REVIEW
**Dependencies:** PROMO-001 (ACCEPTED), EXEC-001 (ACCEPTED), EXP-002 (ACCEPTED)
**Layer:** promotion / execution
**Architecture:** Model artifact promotion to PAPER_APPROVED and forward-walking paper broker session.

## Objective

Promote the executed MOM-TS-01 model artifact (`mod_tsmom_30_7_v1`) through the `PromotionRegistry` to `PAPER_APPROVED` using the accepted evidence reference (`REVIEW-0177`), and execute a stateful paper trading session using `PaperBroker` (EXEC-001) to demonstrate paper execution working end-to-end.

## Scope

1. **Promotion Registration Script / Task:**
   - Create a script or utility (`scripts/promote_and_run_paper.py`) that initializes `PromotionRegistry` with `control.db`.
   - Register model artifact `mod_tsmom_30_7_v1` in `RESEARCH_CANDIDATE` state with full `PromotionIdentityPayload` matching `EXP-2026-019` fingerprint (`87469a44a184...`), commit hash, and cost versions.
   - Transition state to `RESEARCH_ACCEPTED` with evidence reference `REVIEW-0174`.
   - Transition state to `PAPER_APPROVED` with evidence reference `REVIEW-0177`.

2. **Paper Execution Session:**
   - Instantiate `PaperBroker` for `mod_tsmom_30_7_v1` with `strict_promotion_gate=True` (confirming `PaperBroker.verify_promotion_gate()` passes).
   - Simulate sequential forward-walking paper rebalances across 8 decision periods using factor weights from `tsmom_30_7`.
   - Track paper equity, trades, cash, and open positions.
   - Emit a clean JSON summary of paper trading results (Initial Cash, Final Equity, Total Trades, Win Rate, Final Account State).

## Deliverables

- `scripts/promote_and_run_paper.py`
- Paper promotion event records in control database
- `research/sprint_004/07_PAPER_TRADING_RESULTS.json`

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/promotion/ tests/execution/ -q --tb=short`
2. `.venv/bin/python -m ruff check scripts/promote_and_run_paper.py`
3. `.venv/bin/python -m mypy --no-error-summary scripts/promote_and_run_paper.py`
4. `.venv/bin/python scripts/promote_and_run_paper.py --dry-run`
5. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Strong Model): implementation of promotion and paper session script. Stop for reviewer.
- Jr Dev (Weak Model): tests, gates, records, Git, commit, push after approval.

## Stop Condition

After Sr Dev implementation: Set state to AWAITING_REVIEW, wait for Lead Quant review, Next ticket authorized: NONE.
