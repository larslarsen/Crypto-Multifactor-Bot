# PAPER-001 — Factor-Driven Paper Trading Loop for MOM-TS-01

**Priority:** P0
**Status:** ACCEPTED
**Dependencies:** PROMO-002 (ACCEPTED), PORT-002 (ACCEPTED), MOMTS-001 (ACCEPTED), HOLDOUT-001 (ACCEPTED)
**Layer:** execution / serving / experiments
**Architecture:** Wires promoted artifact → factor scores → allocator → PaperBroker; optional holdout observation snapshot.

## Objective

Replace the hardcoded weight demo in PROMO-002 with a real paper loop: at each decision time, compute `tsmom_30_7` scores, allocate via `LongShortRankAllocator`, rebalance via `PaperBroker` under `PAPER_APPROVED` gate, and emit paper + holdout observation artifacts suitable as `paper_observation_reference` for a future LIVE gate.

## Scope

1. **Paper loop module or script** (`scripts/run_paper_momts.py` and/or `src/cryptofactors/execution/paper_loop.py`):
   - Require `model_artifact_id=mod_tsmom_30_7_v1` in `PAPER_APPROVED` (fail closed otherwise).
   - For each decision time: factor compute → L/S allocate (leverage ≤ 1.0) → `PaperBroker.rebalance`.
   - Support `--dry-run` synthetic as-of store (same pattern as `run_momts_experiments.py`).
   - Emit equity curve, trades, turnover, and period returns.

2. **Holdout snapshot (lightweight):**
   - Call or mirror `ProspectiveEvaluator` over the paper session window when available.
   - Write `research/sprint_004/08_PAPER_FACTOR_LOOP_RESULTS.json` including observation reference id/path.

3. **Tests:** unit tests for the loop with mocked store + temp PromotionRegistry (promote once, run loop, assert trades and gate failure without approval).

## Out of Scope

- LIVE routing / real exchange keys.
- New factor families.
- Changing promotion state machine rules.

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ tests/promotion/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution scripts/run_paper_momts.py`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution scripts/run_paper_momts.py`
4. `.venv/bin/python scripts/run_paper_momts.py --dry-run`
5. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Strong Model): production loop source + script. Stop for reviewer.
- Jr Dev (Weak Model): tests, gates, Git, commit, push after approval.

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
