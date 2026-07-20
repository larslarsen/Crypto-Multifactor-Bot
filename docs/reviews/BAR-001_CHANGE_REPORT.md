# BAR-001 — Integration Change Report

**Ticket:** BAR-001 - Canonical bar publisher and daily reconciliation
**Governing review:** REVIEW-0039 (final integration assertions required; CHANGES_REQUIRED, Jr only)
**Date:** 2026-07-20

## Source

`src/cryptofactors/market/bars.py` v5 (committed at `c79c5e4`). Transform
`CANONICAL_BAR_TRANSFORM_VERSION = "5"`. Schema `market_bar` v2
(`_SUPPORTED_SOURCE_SCHEMA_VERSION = "2"`). No production source changes made.

## Jr integration changes

`tests/market/test_canonical_bars.py` — 40 focused regression tests. Each
CURRENT_TASK checklist item is covered by a dedicated test that independently
reaches and asserts the target branch.

### REVIEW-0039 corrections (tested implementation HEAD `d12caff`)

1. `test_identical_duplicate_collapses_both_orders` — uses separate output
   directories, reads both outputs, asserts exactly one retained row, asserts the
   deterministic retained `source_dataset_id` (order-independent), and asserts
   semantically identical output tables in both source orders.
2. `test_explicit_1m_selection_no_merge` / `test_no_merge_mixed_timeframe_daily_counts`
   — 5m rows now carry distinguishable open/close/volume/trade values; daily
   base_volume / trade_count / open / close are asserted equal to the selected 1m
   totals only, in both source orders (a merge would be detected).
3. `test_daily_ohlcv_values` — asserts `base_volume`, `quote_volume`,
   `trade_count`, and the taker-volume sums for the complete day.
4. `test_reconcile_missing_native` — supplies native evidence for a different
   period so the `missing_native` branch is reached; asserts report status
   `missing_native` and issue `bar001_daily_missing_native`.
5. `test_unsafe_path_token_rejected_fail_closed` (new) — a validly signed source
   with an unsafe caller/path token (`../escape`) is rejected before any
   filesystem write escapes the root.
6. `_manifest_with_partition` — no longer writes shared `/tmp/part_probe`; uses the
   test's `tmp_path` so fixtures are isolated, parallel-safe, and independent of
   prior runs.

### REVIEW-0040 corrections (tested implementation HEAD `3a6ed1a`)

1. `test_no_merge_mixed_timeframe_daily_counts` — both source orders published
   under separate output parents (`out_ab` / `out_ba`) and read independently, so
   neither publication overwrites the other; selected-1m OHLC/volume/trade totals
   asserted for both.
2. `test_conflict_duplicate_quarantines_both_orders` — both orders published under
   separate output parents; each asserts no intraday promotion, a single
   quarantine partition containing **both** conflicting rows (both close values and
   both source dataset IDs present), and the `bar001_duplicate_conflict` issue.
3. Change-report wording corrected: the duplicate-collapse test proves *semantic*
   table equality, not byte identity.

### REVIEW-0041 corrections (tested implementation HEAD `c10dd3a`)

1. `test_conflict_duplicate_quarantines_both_orders` — reads each order's
   independent quarantine Parquet and asserts exactly two rows, both conflicting
   close values (105 and 200) and both source dataset IDs present, both orders
   semantically equal, and no intraday promotion in either order.

### Checklist coverage (items 1-10)

| # | Requirement | Test(s) |
|---|---|---|
| 1 | Module header transform v3→v5 | file docstring + `test_transform_version_constant_is_v5` |
| 2a | Dataset-ID mismatch after valid hash | `test_dataset_id_mismatch_rejected` |
| 2b | Byte-size mismatch after valid file hash | `test_byte_size_mismatch_rejected` |
| 2c | Unsupported dataset type | `test_unsupported_dataset_type_rejected` |
| 2d | Unsupported schema version | `test_unsupported_schema_version_rejected` |
| 3 | Every partition key missing & mismatched | `test_partition_key_missing_rejected`, `test_partition_key_mismatched_rejected` (all 5 keys) |
| 4 | Incomplete-receipt evidence beyond `publication_verified=False` | `test_reject_unverified_receipt`, `test_reject_receipt_missing_manifest_sha256`, `test_reject_receipt_bad_dataset_id_prefix` |
| 5 | Duplicate collapse/conflict, distinct IDs, both orders | `test_identical_duplicate_collapses_both_orders`, `test_conflict_duplicate_quarantines_both_orders` |
| 6 | Shifted normalized timestamps | `test_shifted_normalized_timestamp_mismatch_quarantines` |
| 7 | Simultaneous 1m/5m, ambiguity, explicit 1m, no merge | `test_mixed_timeframe_ambiguity_fails_closed`, `test_explicit_1m_selection_no_merge`, `test_no_merge_mixed_timeframe_daily_counts` |
| 8 | Daily OHLCV values | `test_daily_ohlcv_values` |
| 9 | Reconciliation match/mismatch/missing-native/missing-resampled | `test_reconcile_match`, `test_reconcile_mismatch_quarantine`, `test_reconcile_missing_native`, `test_reconcile_missing_resampled` |
| 10 | Safe paths, partition measurements, lineage, `verify_outputs`, catalog `DatasetPublisher.publish` | `test_safe_output_paths_and_partition_measurements`, `test_unsafe_path_token_rejected_fail_closed`, `test_row_and_dependency_lineage`, `test_verify_outputs_passes`, `test_catalog_registered_publish` |

Retained regression coverage: empty sources, PASS_WITH_WARNINGS propagation,
nullable missing fields, strict COIN-M schema rejection, inclusive-close
match/mismatch, partial-day exclusion, forged manifest hash, local file hash
mismatch, REJECTED/QUARANTINED fail-closed, legacy v1 identity, daily-source-
timeframe canonical identity, whitespace-equivalent timeframe identity.

## Fixture method

Each forged case re-signs identity independently so exactly one branch is reached:
- Dataset-ID mismatch: forge `dataset_id`, re-sign `manifest_sha256` over the forged body.
- Byte-size mismatch: preserve real file SHA, change declared `OutputFileSpec.bytes`
  and `statistics.byte_size`, re-sign `dataset_id` + `manifest_sha256`, propagate
  the new `verified_outputs`/dataset_id to the receipt so dual-evidence agrees and
  the file byte-size check fires at runtime.
- Unsupported identity / partition variants: change one identity field, re-sign both
  `dataset_id` and `manifest_sha256`.

## Ticket-exact gate results (tested implementation HEAD `c10dd3a`)
See docs/reviews/bar001_gates_exact_HEAD.txt for exact command output:
1. `PYTHONPATH=src uv run pytest tests/market/test_canonical_bars.py -q --tb=short`
   40 tests pass
2. `uv run ruff check tests/market/test_canonical_bars.py`
   All checks passed!
3. `PYTHONPATH=src uv run pytest -q --tb=short`
   367 passed (pre-existing benign archive warning only)
4. `python3 scripts/check_repo_control.py`
   PASS

## Stop condition

Complete current suite and every ticket-exact gate pass; change report updated;
committed (implementation + records); pushed; stopped for reviewer inspection.
