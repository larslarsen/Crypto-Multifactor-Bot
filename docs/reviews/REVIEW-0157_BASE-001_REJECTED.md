# REVIEW-0157 — BASE-001 SOURCE REJECTED (Round 2)

**Ticket:** BASE-001 — Transparent Factor Baselines (Experiment #19)
**Status:** REJECTED
**Date:** 2026-07-22
**Reviewer:** GPT-5.6 sol
**Next required actor:** Sr Dev (corrections required)
**Next ticket authorized:** NONE

## Corrected from REVIEW-0156

- P1: Substrate integration added (CatalogAsOfStore → labels → split → experiment bundle).
- P1: `_history_series()` rewritten to collect distinct observations by rewinding cursor.
- P2: Negative price/volume validation added.

## Remaining findings

### P1 — Production BAR-001 timestamps incompatible with history walk

`baseline.py:296-325` — `_history_series()` rewinds to `period_start - 1µs` after each observation. Production BAR-001 bars set `availability_time = period_end` (`market/bars.py:1133-1143`). This means the preceding bar's `availability_time` is after the cursor and becomes unavailable, skipping valid observations.

The history walk assumes `availability_time = period_start` (the model's synthetic bars), but production bars use `availability_time = period_end` (the next interval's open time).

### P1 — Integration tests conceal the incompatibility

`test_baseline_factors.py:532-544` — Synthetic bars set `availability_time = period_start` and `period_end = far_end_us` (distant future). This matches the model's assumption but not production BAR-001 semantics. The integration test passes on noncanonical timestamps.

### P2 — Smoke test uses cached store, not raw CatalogAsOfStore

`test_baseline_factors.py:613-614,691-705` — `_build_catalog_asof()` returns `_CachedCatalogAsOf`, not raw `CatalogAsOfStore`. The smoke test claims to exercise the raw store but uses the cached wrapper.

## Decision

REJECT source. P1 findings require correction. The history walk must work with production BAR-001 timestamps (`availability_time = period_end`).

## Corrected source must

1. Fix `_history_series()` to work with production `availability_time = period_end` semantics.
2. Update integration tests to use production-like timestamps.
3. Fix or rename the smoke test.

No next ticket authorized. Stop after push.
