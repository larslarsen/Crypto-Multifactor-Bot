# CURRENT_TASK

Ticket: BASE-001
State: READY
Next required actor: Sr Dev (Grok 4.5)
Next ticket authorized: NONE

ASOF-002 accepted (completed-bar window fix). BASE-001 unblocked. Remove test-only wrapper, all tests now use raw CatalogAsOfStore.

## Sr Dev Prompt

```
BASE-001 — remove _CompletedBarCatalogAsOf wrapper (ASOF-002 makes it redundant).

Raw CatalogAsOfStore now handles completed bars correctly. Delete the test-only
wrapper and update all call sites in tests/test_baseline_factors.py.

Changes (tests/test_baseline_factors.py only):

1. DELETE class _CompletedBarCatalogAsOf (lines 348-463, ~115 lines)

2. UPDATE _build_catalog_asof return type (line 474):
   Before: -> tuple[CatalogAsOfStore, _CompletedBarCatalogAsOf]:
   After:  -> CatalogAsOfStore:

3. UPDATE _build_catalog_asof return (line 617):
   Before: return raw, _CompletedBarCatalogAsOf(raw, market_dataset_id)
   After:  return raw

4. UPDATE test_baseline_substrate_integration (line 638):
   Before: _raw, store = _build_catalog_asof(
   After:  store = _build_catalog_asof(

5. UPDATE test_catalog_asof_raw_store_ref_and_completed_bar_access (line 695-731):
   Before: raw, completed = _build_catalog_asof(...)
   After:  store = _build_catalog_asof(...)
   Then: replace all uses of `completed` with `store` in that test body.
   The test already asserts raw store returns 1 row (line 725); the completed
   assertion should also use `store.latest_available`.

After: run tests, stop.

Source file src/cryptofactors/factors/baseline.py needs NO changes — it uses
the protocol, already production-ready.
```

## Model Note

Sr Dev Grok 4.5 credits available. Use Grok 4.5.

Governing documents:
- tickets/BASE-001.md (READY)
- docs/reviews/REVIEW-0158_BASE-001_REJECTED.md (third rejection)
- docs/reviews/REVIEW-0159_ASF002_ACCEPTED.md (unblocker)
- src/cryptofactors/factors/baseline.py (515 lines, NO changes needed)
- tests/test_baseline_factors.py (731 lines, wrapper removal)

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/test_baseline_factors.py -q --tb=short
2. .venv/bin/python -m ruff check tests/test_baseline_factors.py
3. .venv/bin/python -m mypy --no-incremental tests/test_baseline_factors.py
4. python3 scripts/check_repo_control.py

## Stop condition

After Sr Dev: stop for Reviewer. After acceptance: Jr commits.
