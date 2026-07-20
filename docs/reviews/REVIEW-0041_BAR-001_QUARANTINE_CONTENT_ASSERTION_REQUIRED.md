# REVIEW-0041 - BAR-001 QUARANTINE CONTENT ASSERTION REQUIRED

**Ticket:** BAR-001 - Canonical bar publisher and daily reconciliation
**Reviewed implementation:** `3a6ed1a`
**Reviewed records:** `490c12e`
**Status:** CHANGES_REQUIRED (single Jr test correction)
**Next required actor:** Jr Dev - Hermes (Tencent HY3)
**Date:** 2026-07-20

Mixed-timeframe and source-order isolation are correct. One REVIEW-0040 assertion remains.

`test_conflict_duplicate_quarantines_both_orders` asserts one quarantine path, not the
contents of that partition. One file may contain zero, one, or both conflicting rows. Read
each order's independent quarantine Parquet and assert:

1. exactly two rows are quarantined;
2. both conflicting close values/source dataset IDs are present;
3. the two order results are semantically equal;
4. neither order promotes an intraday row.

Correct the change report wording: one quarantine partition contains both conflicting rows;
it is not "exactly one quarantined conflicting row."

Commit the test correction, run every ticket-exact gate at the clean implementation commit,
then commit/push exact evidence and all outstanding reviewer/control records. No production
source changes are authorized.

## Disposition

BAR-001 remains `IN_PROGRESS`. Next ticket authorized: `NONE`.
