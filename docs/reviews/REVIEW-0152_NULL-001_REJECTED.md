# REVIEW-0152 — NULL-001 SOURCE REJECTED (Round 2)

**Ticket:** NULL-001 — Null Factor Test (Experiment #18)
**Status:** REJECTED
**Date:** 2026-07-22
**Reviewer:** Big Pickle
**Next required actor:** Sr Dev (corrections required)
**Next ticket authorized:** NONE

## Corrected from REVIEW-0151

- P2 contracts moved to `src/cryptofactors/factors/contract.py`.
- P2 string/bytes universe inputs rejected.
- P2 per-instrument seeding for universe-stable scores.

## Remaining findings

### P1 — Tests fail

`tests/test_null_factor.py:358,373` — Mean Sharpe ratios exceed ±0.5 threshold:
- `test_null_factor_sharpe_near_zero_ten_trials`: mean_sharpe=0.861
- `test_null_factor_ten_trials_consistent`: mean_sharpe=0.554

Null factor through the substrate produces mean Sharpes of 0.86 and 0.55 across 10 trials. Either the tolerance is too tight for this substrate path, or the synthetic price/label construction introduces systematic bias. Investigate which and correct: widen tolerance with documented justification, or fix the synthetic pipeline to remove the bias source.

### P1 — Substrate stand-in, not real CatalogAsOfStore

`tests/test_null_factor.py:53-131` — `_SubstrateAsOf` is an in-memory hand-rolled stand-in. It does not exercise the real `CatalogAsOfStore` contract (Arrow serialization, timestamp microsecond encoding, max-age filtering). The P1 finding from REVIEW-0151 is not fully closed: the test proves LABEL/SPLIT/EXP interfaces connect, not that the production ASOf store path works.

Recommended fix: inject `CatalogAsOfStore` with synthetic Parquet files (as done in `tests/catalog/test_asof001_integration.py`) or explicitly document the stand-in as the accepted approach for this specific null-baseline validation step and move the integration proof to a dedicated integration test.

### P2 — Mypy unused type: ignore

`tests/test_null_factor.py:339` — `# type: ignore[arg-type]` is no longer needed. Mypy reports `unused-ignore`. Remove it.

## Decision

REJECT source. P1 findings require correction. P2 finding should be cleaned in the same pass.

## Corrected source must

1. Fix test failures: widen tolerance with justification or fix synthetic pipeline bias.
2. Either inject real `CatalogAsOfStore` or document why the stand-in is accepted for this validation step.
3. Remove unused `# type: ignore` at line 339.

No next ticket authorized. Stop after push.
