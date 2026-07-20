# REVIEW-0033 - BAR-001 INTEGRATION: CHANGES_REQUIRED

**Ticket:** BAR-001 - Canonical bar publisher and daily reconciliation
**Status:** CHANGES_REQUIRED (Jr integration only)
**Next required actor:** Jr Dev - Hermes
**Date:** 2026-07-19

The v5 source remains approved. The current 16-test integration adds only part of the
REVIEW-0032 contract and contains tests that do not reach the behavior their names claim.

## Findings

1. The module docstring still identifies transform v3 although production is v5.
2. `test_reject_legacy_v1_identity` supplies an invalid dataset ID, so it fails during
   recomputed-ID validation before reaching unsupported dataset/schema rejection.
3. `test_identical_duplicate_collapses` constructs both inputs from the same path and
   same dataset identity. It does not prove identical economics across distinct verified
   dataset IDs. Conflict behavior is not tested under reversed source order.
4. No tests cover forged manifest hash, local file hash/size mismatch, missing/mismatched
   required partition metadata, dependency/file-partition dual disagreement, or bar-only
   output selection.
5. REJECTED and QUARANTINED source quality are untested.
6. Shifted normalized timestamps are untested; only raw inclusive-close mismatch is
   covered.
7. Complete daily OHLCV values, simultaneous complete 1m/5m ambiguity, explicit
   timeframe selection, and selected-timeframe output are not established.
8. Reconciliation match, mismatch quarantine, and both missing-side cases are absent;
   `VerifiedDailySource` is imported but unused.
9. Safe partition paths, partition sizing/lineage details, full-plan `verify_outputs`,
   and successful `DatasetPublisher.publish` remain absent.
10. The report is explicitly work-in-progress, points to REVIEW-0030 rather than the
    integration reviews, and records pytest commands that differ from the ticket-exact
    directory/full-suite commands.

## Authorized integration task - Jr Dev - Hermes

Do not modify production source. Correct the existing weak fixtures so each test reaches
the intended branch, then implement every missing case above and REVIEW-0032. Use distinct
valid manifests/dataset IDs for cross-dataset duplicate tests; recompute valid identity
before testing unsupported source type/schema; and use real complete-day fixtures for
daily/reconciliation behavior. Add complete-plan `verify_outputs` and successful
catalog-registered `DatasetPublisher.publish`.

After the final test edit, run every command in `tickets/BAR-001.md` exactly as written.
Replace the work-in-progress report with demonstrated behavior only, transform v5,
actual count, exact results, and the real BAR commit. Keep `AWAITING_REVIEW`, commit/push,
and stop for reviewer inspection. If a regression exposes a source defect, record it and
stop without editing production.

## Disposition

BAR-001 remains `AWAITING_REVIEW`. Sr Dev attention is not required. Next ticket authorized:
`NONE`.
