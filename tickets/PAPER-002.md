# PAPER-002 — Paper Holdout Observation Hardening

**Priority:** P0
**Status:** AWAITING_REVIEW
**Dependencies:** PAPER-001 (ACCEPTED), HOLDOUT-001 (ACCEPTED)
**Layer:** execution / serving
**Architecture:** Fixes ProspectiveEvaluator integration so paper sessions emit a real `paper_observation_reference`.

## Objective

Close the REVIEW-0179 caveat: dry-run paper loops currently emit `paper_observation_reference: null`. Produce a complete, non-null `PaperObservationResult` with true period PnL, observed leverage/weight from actual allocations, and fail-visible errors (no silent swallow).

## Scope

1. **`FactorDrivenPaperLoop` fixes** (`src/cryptofactors/execution/paper_loop.py`):
   - Compute **period-over-period** equity returns (not cumulative return from `initial_cash` each period).
   - Track `max_gross_leverage` and `max_single_asset_weight` from each period’s `target_weights`.
   - Pass real period metrics into holdout evaluation (extend `SimulationPeriod` usage or feed a dedicated observation builder).
   - Do **not** bare-`except` the holdout path; catch only expected domain errors and surface others.
   - Ensure when `evaluation_time - effective_time >= min_observation_days` and periods exist, `observation_result` is non-null and `is_complete` reflects the window.

2. **`ProspectiveEvaluator` (minimal if needed):**
   - Accept observed leverage/weight from the paper loop (constructor args or new optional fields on periods / a small DTO) instead of stubbing `0.10` / `1.0` only.
   - Keep fail-closed if event is not `PAPER_APPROVED`.

3. **Script + artifact:**
   - Update `scripts/run_paper_momts.py` so dry-run writes non-null `paper_observation_reference` in `research/sprint_004/08_PAPER_FACTOR_LOOP_RESULTS.json` (or `09_PAPER_OBSERVATION_RESULTS.json` if preferred).
   - Align promotion `effective_time` with decision window so the observation window is valid.

4. **Tests:**
   - Observation non-null when window ≥ 14 days.
   - Incomplete observation when window &lt; 14 days.
   - Risk breach when single weight / leverage exceeds limits.
   - Gate still fails closed without `PAPER_APPROVED`.

## Out of Scope

- LIVE promotion or exchange routing.
- New factor families.

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ tests/serving/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution src/cryptofactors/serving scripts/run_paper_momts.py`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution src/cryptofactors/serving scripts/run_paper_momts.py`
4. `.venv/bin/python scripts/run_paper_momts.py --dry-run` (assert non-null observation in output JSON)
5. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Strong Model): production source. Stop for reviewer.
- Jr Dev (Weak Model): tests, gates, Git after approval.

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
