# BYB-001 — Change Report

**Ticket:** BYB-001 - Bybit Public Trade-Archive Normalizer
**Source drop reviewed:** REVIEW-0048 (SOURCE APPROVED / JR AUTHORIZED)
**Date:** 2026-07-20
**Actor:** Jr Dev - Hermes (Phase B integration)

## Scope

Integrate the reviewer-approved Sr source drop (`src/cryptofactors/ingest/bybit.py`)
and add the required Jr test suite. No production-behavior changes were intended;
only the two behavior-preserving strict-typing fixes noted below.

## Source integration fixes (behavior-preserving, strict typing only)

- Removed two unused `# type: ignore[override]` comments on
  `_BoundedRawReader.readinto` / `.read` (bybit.py:214, 243). The override
  signatures are compatible with `RawIOBase`; the ignores were dead. No runtime
  effect. (Authorized by REVIEW-0048 "formatting or strict typing" fixes.)

## Test suite added

`tests/ingest/market/test_bybit_trade.py` — **29 tests** covering the ticket's
required Jr integration cases plus the REVIEW-0046/0047 regression behavior:

- Audited-shape linear (`usdm`/`base_asset`/`linear_base_size`) and inverse
  (`coinm`/`contracts`/`inverse_contract_size`) rows; PASS with correct partition
  evidence and no invented inverse base/quote volume.
- Exact timestamp conversion: six fractional digits, fewer digits, excess
  sub-microsecond rejection (`bybit_trade_invalid_timestamp`), and tiny nonzero
  sub-microsecond (`0.0000000000001`) rejection.
- Descending and mixed-order archives: source row order preserved, ordering
  diagnostic (`descending` / `mixed`), correct min/max coverage independent of
  row order; mixed order emits `bybit_trade_nonmonotonic_timestamp` (warning,
  not rejection).
- Strict validation: header mismatch, row width, symbol mismatch, invalid side,
  invalid tick direction, nonpositive size, empty/header-only (`bybit_trade_empty_observations`).
- Bad gzip (`bybit_archive_bad_gzip`), strict malformed-quoted CSV
  (`bybit_trade_parse_failure`), over-scale decimal rejection (decimal128 bound).
- Duplicate / conflicting trade IDs within and across objects, with no hidden row
  deletion (exact-duplicate `bybit_trade_duplicate_id`; content-differing
  `bybit_trade_conflicting_duplicate_id`).
- Source row / raw-object lineage preserved (`source_row_number`, `raw_object_id`).
- Deterministic config and schema identities (config_sha256, schema fingerprint,
  transform version `1`, schema version `1`, code commit).
- Storage-root-independent quality identity (quality.parquet hash equal across
  roots).
- Safe logical output paths (`bybit/{market_type}/trades/raw_{id}/...`).
- `verify_outputs` passes; full MAN-001 `DatasetPublisher.publish` through a
  temporary registered catalog succeeds (RAW_OBJECT dependency, role
  `bybit_trade_archive`).
- Explicit no-network behavior (local-only, `CONDITIONAL - CROSSCHECK`).
- Bounded row-limit exceedance (`bybit_archive_limit_exceeded`).

## Exact acceptance commands (from tickets/BYB-001.md)

1. `PYTHONPATH=src uv run pytest tests/ingest/market/test_bybit_trade.py -q --tb=short`
   -> 29 passed
2. `PYTHONPATH=src uv run ruff check src/cryptofactors/ingest/bybit.py tests/ingest/market/test_bybit_trade.py`
   -> All checks passed
3. `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/ingest/bybit.py tests/ingest/market/test_bybit_trade.py`
   -> Success: no issues found in 2 source files
4. `PYTHONPATH=src uv run pytest -q --tb=short`
   -> 396 passed (1 pre-existing archive warning)
5. `python3 scripts/check_layer_imports.py`
   -> layer import check passed
6. `python3 scripts/check_repo_control.py`
   -> Repo control check: PASS

## Publication correction (REVIEW-0049)

Commit `f667c6d` integrated the source and 29-test suite and passed all six
acceptance gates, but it omitted the governing BYB review records referenced by
`CURRENT_TASK.md`; those files remained untracked. This corrective, records-only
commit (no source/test changes) adds them:

- `docs/reviews/BYB-001_SR_SOURCE_TASK.md`
- `docs/reviews/REVIEW-0044_BYB-001_SOURCE_CHANGES_REQUIRED.md`
- `docs/reviews/REVIEW-0045_BYB-001_SOURCE_FINAL_CHANGES_REQUIRED.md`
- `docs/reviews/REVIEW-0046_BYB-001_SOURCE_CORRECTNESS_CHANGES_REQUIRED.md`
- `docs/reviews/REVIEW-0047_BYB-001_SOURCE_FINAL_CORRECTIONS_REQUIRED.md`
- `docs/reviews/REVIEW-0048_BYB-001_SOURCE_APPROVED_JR_AUTHORIZED.md`
- `docs/reviews/REVIEW-0049_BYB-001_INTEGRATION_PUBLICATION_REQUIRED.md`

Integration commit (unchanged, gates still green): `f667c6d`
Corrective commit (this records-only publish): `f00c3d8`
Push/remote evidence: `git fetch` + `git rev-parse origin/main` == local after push.
`git status --short` after push contains only the unrelated `.stale/` entry.
Repo control after corrective commit: PASS.

## Stop condition

Integrated, gated, reported, committed, and pushed. Ticket accepted under
REVIEW-0050 (commit `f667c6d`, corrective `f00c3d8`); set to `ACCEPTED`. Next
ticket remains unauthorized.
