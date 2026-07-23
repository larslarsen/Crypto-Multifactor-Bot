# REVIEW-0158 — BASE-001 SOURCE REJECTED (Round 3)

**Ticket:** BASE-001 — Transparent Factor Baselines (Experiment #19)
**Status:** REJECTED
**Date:** 2026-07-22
**Reviewer:** GPT-5.6 sol
**Next required actor:** Sr Dev (corrections required)
**Next ticket authorized:** NONE

## Corrected from REVIEW-0157

- P1: History walk rewinds cursor to `availability_time - 1µs` (production-compatible).
- P1: Integration tests now use production-like `availability_time = period_end`.
- P2: Smoke test explicitly shows raw `CatalogAsOfStore` returns zero completed bars, then uses `_CompletedBarCatalogAsOf`.

## Remaining findings

### P1 — No production completed-bar access

`test_baseline_factors.py:695-725` confirms raw `CatalogAsOfStore.latest_available` returns zero rows for completed bars when `availability_time = period_end`. The test substitutes a test-only `_CompletedBarCatalogAsOf` wrapper.

No production equivalent exists. Baseline factors cannot run on the accepted BAR-001/ASOF-001 substrate.

**Options:**
A) Implement completed-bar access in `CatalogAsOfStore` (production fix).
B) Create a production `CompletedBarAsOf` adapter in `src/cryptofactors/`.
C) Explicitly document the limitation and accept the test-only wrapper for now.

## Decision

REJECT source. P1 finding requires decision on production completed-bar access.

## Corrected source must

1. Resolve production completed-bar access (option A, B, or C with reviewer approval).
2. If option C: document the limitation clearly in `baseline.py` docstring.

No next ticket authorized. Stop after push.
