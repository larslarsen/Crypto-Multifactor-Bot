# BAR-001 — Integration Change Report

**Ticket:** BAR-001 - Canonical bar publisher and daily reconciliation
**Governing review:** REVIEW-0038 (false-blocker remediation; retains REVIEW-0028/29/30/31/32/33/34/35/36/37)
**Date:** 2026-07-20

## Source

`src/cryptofactors/market/bars.py` v5 (committed at `c79c5e4`). Transform
`CANONICAL_BAR_TRANSFORM_VERSION = "5"`. Schema `market_bar` v2
(`_SUPPORTED_SOURCE_SCHEMA_VERSION = "2"`). No production source changes made.

## Jr integration changes

`tests/market/test_canonical_bars.py` — 39 focused regression tests. Each
CURRENT_TASK checklist item is covered by a dedicated test that independently
reaches and asserts the target branch:

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
| 10 | Safe paths, partition measurements, lineage, `verify_outputs`, catalog `DatasetPublisher.publish` | `test_safe_output_paths_and_partition_measurements`, `test_row_and_dependency_lineage`, `test_verify_outputs_passes`, `test_catalog_registered_publish` |

Also retained regression coverage: empty sources, PASS_WITH_WARNINGS propagation,
nullable missing fields, strict COIN-M schema rejection, inclusive-close match/mismatch,
partial-day exclusion, forged manifest hash, local file hash mismatch, REJECTED/
QUARANTINED fail-closed, legacy v1 identity, daily-source-timeframe canonical identity,
whitespace-equivalent timeframe identity.

## Fixture method (REVIEW-0038 requirement)

Each forged case re-signs identity independently so exactly one branch is reached:
- Dataset-ID mismatch: forge `dataset_id`, re-sign `manifest_sha256` over the forged body.
- Byte-size mismatch: preserve real file SHA, change declared `OutputFileSpec.bytes`
  and `statistics.byte_size`, re-sign `dataset_id` + `manifest_sha256`, and propagate
  the new `verified_outputs`/dataset_id to the receipt so dual-evidence agrees and the
  file byte-size check fires at runtime.
- Unsupported identity / partition variants: change one identity field, re-sign both
  `dataset_id` and `manifest_sha256`.

## Ticket-exact gate results (committed HEAD — see docs/reviews/bar001_gates_exact_HEAD.txt)

1. `PYTHONPATH=src uv run pytest tests/market/test_canonical_bars.py -q --tb=short`
   39 tests pass
2. `uv run ruff check tests/market/test_canonical_bars.py`
   All checks passed!
3. `PYTHONPATH=src uv run pytest -q --tb=short`
   Full suite pass (pre-existing benign archive warning only)
4. `python3 scripts/check_repo_control.py`
   PASS

## Stop condition

Complete current suite and every ticket-exact gate pass; change report updated;
committed/pushed; stopped for reviewer inspection.
