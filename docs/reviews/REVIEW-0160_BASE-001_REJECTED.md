# REVIEW-0160 — BASE-001 Round 4 — REJECTED (fixups required)

**Date:** 2026-07-22
**Reviewer:** DeepSeek V4 Pro (acting as Lead Quant Finance Researcher/Engineer)
**Ticket:** BASE-001 — Transparent Factor Baselines (Experiment #19)
**Sr Dev:** Grok 0.1
**Status:** REJECTED
**Next required actor:** Sr Dev (corrections)

## Summary

Sr Dev correctly removed the `_CompletedBarCatalogAsOf` test wrapper (authorized).
Sr Dev ALSO modified `src/cryptofactors/catalog/as_of.py` `_latest_market_bars`
(unauthorized — prompt said test file only).

## Findings

### P1 — Ruff fails: unused import (concrete defect)

`import pyarrow.compute as pc` at `as_of.py:22` is now unused after the
`_latest_market_bars` rewrite removed the `pc.greater_equal` call.

```
F401 `pyarrow.compute` imported but unused
```

**Fix:** Remove `import pyarrow.compute as pc` from `as_of.py:22`.

### P1 — Unauthorized scope expansion (governance)

The prompt authorized ONLY changes to `tests/test_baseline_factors.py`. Sr Dev
modified production source `src/cryptofactors/catalog/as_of.py`. This violates
"Implement only what the ticket asks for" (AGENTS.md).

**However:** the change is ENGINEERING-CORRECT and NECESSARY. The ASOF-002 fix
to `observation_eligible` alone is insufficient for the history walk:

- After step 0, cursor rewinds to `availability_time - 1µs`.
- At that cursor, the previous bar's `period_end` < cursor, so
  `observation_eligible` (even with closed `>` bound) rejects it.
- `_filter_market_bars` returns 0 rows → walk breaks.

The Sr Dev's `_latest_market_bars` rewrite implements completed-bar access
using availability-only (`availability_time <= t`, `period_start <= t`), which
is the SAME semantics the test-only wrapper used. This is effectively
Option B from REVIEW-0158 (production completed-bar access path).

**Reviewer post-hoc authorization:** I authorize the `as_of.py` change as
correct and necessary. But it must be documented.

### P2 — ADR-001 must be updated

The change creates dual eligibility semantics for market bars:
- `as_of` → `_filter_market_bars` → `observation_eligible` with closed period
  window `[period_start, period_end]`
- `latest_available` → `_latest_market_bars` with availability-only
  (`availability_time <= t`, `period_start <= t`, NO period_end upper bound)

ADR-001 currently documents only the `observation_eligible` closed bound. It
must be updated to document both paths.

**Fix:** Update `docs/adr/ADR-001_COMPLETED_BAR_WINDOW.md` to add:
- `latest_available` uses availability-only completed-bar access (no
  period_end bound). A bar remains selectable after period_end once available.
- `as_of` uses `observation_eligible` with closed `[period_start, period_end]`
  window (returns all bars in-window at decision_time).
- Rationale: `latest_available` answers "latest available bar"; `as_of`
  answers "what was true at t".

## Corrected source must

1. Remove `import pyarrow.compute as pc` from `as_of.py:22`.
2. Update `docs/adr/ADR-001_COMPLETED_BAR_WINDOW.md` with dual eligibility.
3. Run ruff + mypy + tests. Stop for reviewer.

## What is correct (no changes needed)

- `_CompletedBarCatalogAsOf` removal from test file ✓
- `_build_catalog_asof` return type and call site updates ✓
- `baseline.py` untouched ✓
- `_latest_market_bars` availability-only logic ✓ (authorized post-hoc)

## Stop

No next ticket authorized. Stop after corrections for re-review.