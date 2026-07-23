# ARCH-001 — Archive False Discovery, Pre-Registered Single-Test Framework

**Priority:** P0  
**Status:** ACCEPTED  
**Dependencies:** EXP-008 (ACCEPTED)  
**Layer:** research / meta  
**Architecture:** New factor research uses pre-registered single-hypothesis framework with reserved holdout. **No LIVE.**

## Objective

tsmom_14_3 is a false discovery (EXP-008). Archive the candidate and establish a methodological reset that prevents multiple-testing risk in future research.

## Scope

1. **Archive** the false-discovery candidate:
   - Mark `mod_tsmom_14_3_v1` in the Promotion Registry as superseded (REJECTED or RETIRED per ADR-0008).
   - Add `archived: true` note to existing artifacts (do not delete them).
   - Note: PAPER_APPROVED was granted before the multiple-testing analysis; the promotion was correct at the time but the underlying evidence is now refuted.
2. **Reserve a holdout period** from the current dataset:
   - Select a contiguous out-of-sample window at the end of `ds_0cb6415f…` that has **never been used in any grid, selection, or tuning decision** (all prior analysis used the full window, so the entire dataset is contaminated. A fresh dataset or a new data stream may be needed).
   - If using the existing bars, the holdout must be set aside **before any new analysis begins**.
   - Record the holdout boundaries in `29_HOLDOUT_RESERVATION.json`.
3. **Establish a pre-registration template** for single-hypothesis factor tests:
   - Template in `tickets/templates/PRE_REGISTERED_TEST.md`.
   - Must include: factor_id, parameters, universe, risk policy, data window (exploration + holdout), significance level, and minimum acceptable return.
   - Must be filled in and committed **before** any exploration code is written or run.
4. **Do not** change bars, risk limits, or existing promotion records. Do not create new factors or run backtests.

## Out of Scope

- LIVE_APPROVED or any live broker/order path  
- New factor design or backtesting  
- Deleting or altering prior artifacts  

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors scripts/`
3. `29_HOLDOUT_RESERVATION.json` present; holdout boundaries documented
4. `tickets/templates/PRE_REGISTERED_TEST.md` present
5. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
