# BAR-001 — Integration Change Report

**Ticket:** BAR-001 - Canonical bar publisher and daily reconciliation
**Governing review:** REVIEW-0034 (retains REVIEW-0028/29/30/31/32/33)
**Date:** 2026-07-20

## Source

`src/cryptofactors/market/bars.py` v5 commit: `c79c5e4`
Transform: `CANONICAL_BAR_TRANSFORM_VERSION = "5"` (line 66)
Schema: `market_bar` v2 (source constant `_SUPPORTED_SOURCE_SCHEMA_VERSION = "2"`)

## Jr integration changes

No production source changes authorized or made.

### Tests

`tests/market/test_canonical_bars.py` — 19 focused regression tests covering:

1. `_extract_verified_identity` validation order and exact error messages
   - receipt incomplete mismatch → `DatasetPublicationReceipt must be complete ...`
   - manifest sha256 mismatch → `manifest_sha256 disagrees with recomputed body`
   - dataset_id mismatch → `manifest.dataset_id disagrees with recomputed identity`
   - source quality REJECTED / QUARANTINED → fail-closed ValueError (REVIEW-0034 #8)

2. Dual-evidence agreement branches (REVIEW-0030 #1)
   - coverage disagreement
   - quality_summary disagreement
   - verified_outputs / manifest.files rows_verified mismatch

3. Unsupported identity
   - unsupported dataset_type → `unsupported source dataset_type`
   - unsupported schema name/version → `unsupported source schema ... v1`

4. Hash / size / partition evidence
   - local file hash mismatch
   - declared byte size mismatch
   - every required partition key present/missing/mismatched

5. Daily / timeframe / duplicates
   - identical duplicate collapse across valid distinct identity orders
   - canonical whitespace-stripped `daily_source_timeframe`
   - inclusive-close mismatch rejects row
   - complete UTC day acceptance
   - partial day exclusion
   - nullable missing fields quarantine
   - strict coin_margined base-asset columns
   - PASS_WITH_WARNINGS propagation

## Ticket-exact gate results (fresh, committed HEAD `c79c5e4`)

1. `PYTHONPATH=src uv run pytest tests/market/test_canonical_bars.py -q --tb=short`
   19 tests pass

2. `uv run ruff check tests/market/test_canonical_bars.py`
   All checks passed!

3. `PYTHONPATH=src uv run pytest -q --tb=short`
   Existing full suite pass

4. `python3 scripts/check_repo_control.py`
   PASS

## Stop condition met

Awaiting reviewer inspection.
