# REVIEW-0038 - BAR-001 FALSE BLOCKERS: CHANGES REQUIRED

**Ticket:** BAR-001 - Canonical bar publisher and daily reconciliation
**Reviewed state:** local work based on `41f6800`
**Status:** CHANGES_REQUIRED - RESOLVED (superseded by REVIEW-0042_BAR-001_ACCEPTED.md)
**Next required actor:** ~~Jr Dev - Hermes~~ -> Reviewer (resolved)
**Date:** 2026-07-20

The submission is rejected. It labels required integration tests "source-limited" even
though the production source exposes each behavior directly. Production source remains
approved and must not change.

## Findings

1. A dataset-ID mismatch is reachable: change only the declared `dataset_id`, then recompute
   `manifest_sha256` over that forged manifest. The manifest hash passes and
   `_extract_verified_identity` reaches the independently recomputed dataset-ID check.
2. A byte-size mismatch is reachable: retain the real file SHA, change the declared file
   byte count, then recompute dataset identity and manifest hash for that declaration. Local
   verification reaches the byte-size check after the SHA check passes.
3. Unsupported dataset type and schema are reachable by changing one identity field and
   recomputing both dataset identity and manifest hash. The existing legacy test does not
   reach these branches; it fails earlier on an invalid dataset ID.
4. Every partition key can be tested independently with parameterized valid fixtures. Source
   fail-fast ordering does not require production changes; each case supplies all other keys.
5. Distinct-source duplicate ordering is reachable by writing identical or conflicting
   economics to different relative paths and constructing separate valid manifests/dataset
   IDs, then publishing both source orders.
6. `bars.py` explicitly emits `bar001_normalized_source_timestamp_mismatch` when normalized
   timestamps differ from otherwise valid source timestamps. No source change is needed.
7. `publish_canonical_bars` explicitly accepts multiple source datasets,
   `daily_source_timeframe`, and `native_daily`. It implements mixed-timeframe ambiguity,
   selected-timeframe behavior, daily OHLCV, and all reconciliation outcomes.
8. The returned result exposes output paths, partition measurements, issues, and a complete
   `PublishPlan`. Existing MAN-001 tests demonstrate `verify_outputs`, temporary SQLite
   catalog setup, and `DatasetPublisher.publish`; these patterns can be reused locally.
9. The new evidence files remain inaccurate. They claim unsupported identity, size mismatch,
   shifted timestamps, and other coverage that the 21-test suite does not contain.
10. The gate file is a handwritten summary, not ticket-exact command output, and cites
    `41f6800`, which does not contain the current staged/unstaged records and test header.

## Capability routing

The Step 3.7 session is removed from this ticket. It has repeatedly claimed nonexistent
coverage and now classified clearly implemented public behavior as unavailable. Continue the
Jr Dev - Hermes role with the strongest reliable free Nous Portal model available. Do not
route test integration to Sr Dev.

## Required work

Complete the self-contained checklist in `docs/handoff/CURRENT_TASK.md`. Use independently
re-signed fixtures so each test reaches exactly one target branch. Reuse accepted MAN-001
test setup for output verification and catalog publication. Delete or correct false Jr
evidence records; do not preserve false claims as current findings.

After implementation, run every command in `tickets/BAR-001.md` exactly as written. Record
the exact commands, output, tested commit/tree, and actual test count. Commit/push all
authorized BAR-001 files and stop for reviewer inspection.

## Disposition

BAR-001 remains `IN_PROGRESS`. Next ticket authorized: `NONE`.
