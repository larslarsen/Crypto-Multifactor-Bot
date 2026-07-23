# CURRENT_TASK

Ticket: BASE-001
State: BLOCKED
Next required actor: Sr Dev (corrections required)
Next ticket authorized: NONE

BASE-001 source rejected again (REVIEW-0157). P1: history walk incompatible with production BAR-001 timestamps (availability_time = period_end). P1: integration tests use noncanonical timestamps. P2: smoke test uses cached store.

Governing documents:
- tickets/BASE-001.md (BLOCKED)
- docs/reviews/REVIEW-0157_BASE-001_REJECTED.md
- docs/reviews/REVIEW-0156_BASE-001_REJECTED.md

## Sr Dev Correction Prompt

```
Correct BASE-001 source per REVIEW-0157 findings.

P1 — History walk incompatible with production BAR-001 timestamps:
- baseline.py:296-325 rewinds cursor to period_start - 1µs.
- Production bars set availability_time = period_end (market/bars.py:1133-1143).
- This makes the preceding bar unavailable; skips valid observations.
- Fix: use availability_time instead of period_start for cursor rewinding.
- The cursor should be set to availability_time - 1µs (i.e., period_end - 1µs).

P1 — Integration tests use noncanonical timestamps:
- test_baseline_factors.py:532-544 sets availability_time = period_start.
- Must use production-like availability_time = period_end.

P2 — Smoke test uses cached store:
- test_baseline_factors.py:613-614,691-705 uses _CachedCatalogAsOf.
- Either use raw CatalogAsOfStore or rename to reflect what it tests.

Files to modify:
- src/cryptofactors/factors/baseline.py (history walk fix)
- tests/test_baseline_factors.py (timestamps + smoke test)

Reference: market/bars.py:1133-1143 (production bar timestamps).

After completion: set status to AWAITING_REVIEW.
```

## Stop condition

Sr Dev produces corrected source, stops for Reviewer. No commits until Reviewer accepts.
