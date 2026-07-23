# ASOF-002 — Fix CatalogAsOfStore Half-Open Window for Completed Bars

**Priority:** P0
**Status:** ACCEPTED
**Dependencies:** ASOF-001 (accepted), BAR-001 (accepted)
**Layer:** catalog
**Architecture:** fixes production bug; ADR required (docs/adr/ADR-001_COMPLETED_BAR_WINDOW.md)

## Objective

Fix `observation_eligible` in `CatalogAsOfStore` so completed market bars are selectable. Production BAR-001 bars set `availability_time = period_end`, but the current half-open window check (`decision_time_us >= valid_to_us`) excludes bars at their exact availability time.

## Bug

`src/cryptofactors/catalog/as_of.py:131`:
```python
if decision_time_us >= valid_to_us:
    return False
```

When `availability_time = period_end` and `decision_time = period_end`:
- Bar IS available: `availability_time <= decision_time`
- Bar SHOULD be in period window: `period_start <= decision_time <= period_end`
- Bar IS NOT in period window: `decision_time >= period_end` → False

## Fix

Change `>=` to `>` at line 131:
```python
if decision_time_us > valid_to_us:
    return False
```

This makes the period window `[period_start, period_end]` inclusive, consistent with `availability_time = period_end` semantics. The change only affects the boundary case at `t == period_end`. On-disk data is unchanged.

## Verification

- Raw `CatalogAsOfStore.latest_available` must return completed bars at `decision_time = period_end`
- Existing tests must still pass (fee schedules, instrument versions use NULL valid_to or far-future)
- `test_catalog_asof_raw_store_ref_and_completed_bar_access` in `tests/test_baseline_factors.py` must flip from 0 rows to 1 row

## Deliverables

- `src/cryptofactors/catalog/as_of.py` (one-line fix)
- `docs/adr/ADR-001_COMPLETED_BAR_WINDOW.md`
- Ticket + governance
- Tests + gates (Jr)

## Out of Scope

- Changes to market_bars canonicalization
- Changes to dataset file format
- Performance optimization

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/catalog/ tests/test_baseline_factors.py -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/catalog/as_of.py`
3. `.venv/bin/python -m mypy --no-incremental src/cryptofactors/catalog/as_of.py`
4. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Grok): production source only. Stop for reviewer.
- Jr Dev (Hermes): tests, gates, records, Git, commit, push after approval.

## Stop Condition

After Jr: AWAITING_REVIEW, Reviewer next, NONE.
