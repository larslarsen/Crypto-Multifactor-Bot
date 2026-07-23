# CURRENT_TASK

Ticket: NULL-001
State: BLOCKED
Next required actor: Sr Dev (corrections required)
Next ticket authorized: NONE

NULL-001 source rejected again (REVIEW-0152). P1: tests fail (mean Sharpes 0.86 and 0.55 exceed ±0.5). P1: _SubstrateAsOf stand-in, not real CatalogAsOfStore. P2: unused type: ignore.

Governing documents:
- tickets/NULL-001.md (BLOCKED)
- docs/reviews/REVIEW-0152_NULL-001_REJECTED.md
- docs/reviews/REVIEW-0151_NULL-001_REJECTED.md
- docs/reviews/REVIEW-0150_UNIVERSE-001_REJECTED.md
- docs/reviews/REVIEW-0148_EXP-001_ACCEPTED.md

## Sr Dev Correction Prompt

```
Correct NULL-001 source per REVIEW-0152 findings.

P1 — Tests fail:
- test_null_factor_sharpe_near_zero_ten_trials: mean_sharpe=0.861 (exceeds ±0.5)
- test_null_factor_ten_trials_consistent: mean_sharpe=0.554 (exceeds ±0.5)
- Either widen tolerance with documented justification or fix synthetic pipeline bias.

P1 — Substrate stand-in:
- tests/test_null_factor.py:53-131 uses hand-rolled _SubstrateAsOf, not real CatalogAsOfStore.
- Option A: inject CatalogAsOfStore with synthetic Parquet (see tests/catalog/test_asof001_integration.py for pattern).
- Option B: document why stand-in is accepted for null-baseline validation and add separate integration test.

P2 — Mypy unused type: ignore:
- tests/test_null_factor.py:339 — remove unused # type: ignore[arg-type].

Files to modify:
- tests/test_null_factor.py (primary)

Acceptance:
1. All tests pass (pytest, ruff, mypy)
2. check_repo_control.py PASS

After completion: set status to AWAITING_REVIEW.
```

## Stop condition

Sr Dev produces corrected source, stops for Reviewer. No commits until Reviewer accepts.
