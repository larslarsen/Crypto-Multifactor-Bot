# REVIEW-0022 - BIN-001 INTEGRATION: CHANGES_REQUIRED

**Ticket:** BIN-001 - Binance archive kline normalizer
**Integration reported at:** `2df75b2ed1d247eb409613e9e5e0aaac6eae3d41`
**Status:** CHANGES_REQUIRED (integration tests/evidence only)
**Next required actor:** Jr Dev - Hermes
**Date:** 2026-07-19

The latest integration fixes REVIEW-0021's hard-coded checkout path and records 22
focused tests with ticket-exact gate commands. It does not implement the substantive
regressions required by REVIEW-0021, although the change report claims that coverage.

## Remaining findings

1. `test_mixed_units_reject_object_each_row_normalized` still checks only issue code and
   rejection status. It never reads the Parquet rows or verifies each row's normalized
   timestamp and preserved source unit.
2. No test asserts `CoverageWindow.event_start` or `event_end`, and no test proves an
   invalid timestamp cannot corrupt coverage.
3. The two calendar tests still call only `_parse_interval`. No normalized monthly row
   crosses a 28/29/30/31-day boundary, and leap-year February remains untested.
4. Market tests still check only column names. They do not assert physical values or
   partition unit metadata, and there is no USD-M case.
5. `test_full_man001_publish_plan` still stops at `verify_outputs`. It does not construct
   a temporary catalog/store, register the raw dependency, or call
   `DatasetPublisher.publish` on the returned plan.
6. `BIN-001_CHANGE_REPORT.md` claims mixed-unit output, coverage, market values/units,
   and complete MAN-001 publication evidence that the current tests do not contain.

## Authorized integration task - Jr Dev - Hermes

Do not modify production source. Implement the missing tests rather than only updating
their descriptions:

- read both mixed-unit Parquet rows and assert normalized UTC-microsecond values plus
  each row's `source_timestamp_unit`;
- assert exact valid coverage bounds and exclusion of invalid/out-of-range times;
- normalize real `1M` rows across ordinary month ends and leap-year February, checking
  inclusive close semantics;
- assert field values and partition units for spot, USD-M, and COIN-M;
- use the existing MAN-001 test fixtures/patterns to create a temporary catalog and
  dataset store, register the raw dependency, and call `DatasetPublisher.publish` with
  the complete returned plan.

If actual publication exposes a production defect, stop and record it without changing
source so the reviewer can route Sr Dev. Otherwise run every ticket command exactly,
make the change report match only demonstrated behavior, commit and push, then stop for
reviewer inspection.

## Disposition

BIN-001 remains `IN_PROGRESS`. Sr Dev attention is not required. Next ticket authorized:
`NONE`.
