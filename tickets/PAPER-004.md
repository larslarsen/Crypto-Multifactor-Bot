# PAPER-004 — Paper Ops Equity and Resume Fixes

**Priority:** P1
**Status:** AWAITING_REVIEW
**Dependencies:** PAPER-003 (ACCEPTED)
**Layer:** execution
**Architecture:** Fixes two REVIEW-0181 caveats.

## Objective

Close the two non-blocking caveats from REVIEW-0181 before the hardening phase.

## Scope

1. **`PaperOpsMonitor.inspect_session` equity fix:**
   - Replace `broker.get_cash()` with `broker.get_equity(prices)` so status reports mark-to-market equity.
   - Requires the caller to supply current prices (add optional `current_prices` param).

2. **Broker resume from store:**
   - `PaperSessionStore.load_latest_snapshot` exists but `FactorDrivenPaperLoop.__init__` (or a factory method) does not restore broker state from it.
   - Add a `restore_from_store(store, model_artifact_id)` method or constructor path that loads the last snapshot and sets `PaperBroker._cash` and `PaperBroker._positions`.

## Deliverables

- Updated `src/cryptofactors/execution/paper_monitor.py`
- Updated `src/cryptofactors/execution/paper_loop.py` (or `PaperBroker`)
- Updated tests in `tests/execution/test_paper_ops.py`
- Updated `scripts/run_paper_momts.py` (optional: demo resume path)

## Out of Scope

- Exchange connectivity / API stubs (next phase).
- Running on real as-of store data (next phase).

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution`
4. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Strong Model): production source. Stop for reviewer.
- Jr Dev (Weak Model): tests, gates, Git after approval.

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
