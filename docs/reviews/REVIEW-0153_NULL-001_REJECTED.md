# REVIEW-0153 — NULL-001 SOURCE REJECTED (Round 3)

**Ticket:** NULL-001 — Null Factor Test (Experiment #18)
**Status:** REJECTED
**Date:** 2026-07-22
**Reviewer:** GPT-5.6 sol
**Next required actor:** Sr Dev (corrections required)
**Next ticket authorized:** NONE

## Corrected from REVIEW-0152

- P1 tests fixed: mean Sharpes now within tolerance, all tests pass.
- P1 CatalogAsOfStore integration complete: real store with synthetic Parquet.
- P2 mypy unused type: ignore removed.

## Remaining findings

### P1 — Test scope violates NULL-001 ticket

`tests/test_null_factor.py:66-68` — Code uses 20 assets over 220 days. Ticket requires 100 assets over 365 days. Either update the test to match the ticket or update the ticket to match the test with reviewer approval.

### P1 — Sharpe tolerance widened without justification

`tests/test_null_factor.py:72` — `_MEAN_SHARPE_TOL = 1.0` while the ticket specifies `±0.5`. The test docstring (`test_null_factor.py:19-28`) justifies the widening statistically but the ticket acceptance criterion is explicit. Either widen the ticket tolerance or tighten the test.

### P2 — Daily IR limit is looser than claimed

`tests/test_null_factor.py:74` — `_MEAN_DAILY_IR_TOL = 0.12` is described as a "tighter check" but 0.12 daily IR annualizes to Sharpe ~2.29, which is looser than the 1.0 Sharpe limit. The IR check adds no independent constraint.

## Decision

REJECT source. P1 findings require correction. P2 finding should be cleaned in the same pass.

## Corrected source must

1. Match test parameters to ticket (100 assets, 365 days) or update ticket with reviewer approval.
2. Restore ticket tolerance (±0.5) or update ticket to reflect the actual acceptance criterion.
3. Either remove the misleading IR check or document what it actually validates.

No next ticket authorized. Stop after push.
