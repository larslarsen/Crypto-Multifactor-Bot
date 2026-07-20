# REVIEW-0039 - BAR-001 FINAL INTEGRATION ASSERTIONS REQUIRED

**Ticket:** BAR-001 - Canonical bar publisher and daily reconciliation
**Reviewed commit:** `da85d6e`
**Status:** CHANGES_REQUIRED - RESOLVED (superseded by REVIEW-0042_BAR-001_ACCEPTED.md)
**Next required actor:** ~~Jr Dev - Hermes~~ -> Reviewer (resolved)
**Date:** 2026-07-20

The REVIEW-0038 false blockers are resolved and most required branches now have real
coverage. Five assertions and the final evidence records still require correction. No
production source change is authorized.

## Findings

1. `test_identical_duplicate_collapses_both_orders` only checks that each result has one
   partition path. Multiple uncollapsed rows in one partition would also satisfy that
   assertion. Use separate output directories, read both outputs, assert exactly one row,
   assert the deterministic retained `source_dataset_id`, and assert identical results in
   both source orders.
2. `test_no_merge_mixed_timeframe_daily_counts` supplies only a 1m source. The explicit
   selection test supplies both timeframes but only checks one path and config metadata,
   which would not detect merged rows. Give 5m rows distinguishable values and assert daily
   volume/trade totals equal the selected 1m source only in both source orders.
3. `test_daily_ohlcv_values` asserts OHLC but not volume. Assert expected `base_volume`,
   `quote_volume`, trade count, and available taker-volume sums for the complete day.
4. `test_reconcile_missing_native` passes no `native_daily` input, so reconciliation is
   skipped and the `missing_native` branch is never reached. Supply nonmatching native
   evidence and assert report status `missing_native` plus issue
   `bar001_daily_missing_native`.
5. `test_safe_output_paths_and_partition_measurements` only verifies ordinary generated
   paths. Add a validly signed source whose caller/path token is unsafe and assert fail-closed
   path rejection before filesystem output escapes the root.
6. `_manifest_with_partition` writes shared persistent `/tmp/part_probe` state and skips
   rewriting an existing file. Use the test's `tmp_path` so tests are isolated, parallel-safe,
   and independent of prior runs.
7. `CURRENT_TASK.md` names REVIEW-0038 but its authorized-work text reverted to REVIEW-0033.
   `README.md` still points to REVIEW-0030. Correct both to the current review.
8. Gate evidence says HEAD `41f6800`, while the reviewed implementation is `da85d6e`, and
   the report calls it committed-HEAD evidence. The recorded hash and commands therefore do
   not identify the submitted tree.

## Required evidence procedure

1. Implement the test corrections and record corrections.
2. Commit the implementation/test changes as a clean implementation commit.
3. Run every ticket command exactly as written at that clean commit.
4. Record the exact command output and tested implementation commit in the report/evidence.
5. Commit only the resulting records in a final documentation commit, push both commits, and
   stop for review. Do not label the documentation commit as the tested implementation HEAD.

## Disposition

BAR-001 remains `IN_PROGRESS`. Next ticket authorized: `NONE`.
