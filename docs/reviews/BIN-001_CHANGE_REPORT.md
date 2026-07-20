# BIN-001 — Change Report: Binance archive kline normalizer (v3)

**Ticket:** BIN-001
**Source of change:** Sr Dev — Grok Build source-only drop
(`docs/reviews/BIN-001_SR_REVIEW0020_FIXES.md`); no zip, no Sr commit.
**Integrated as:** current HEAD `ced2436` (this commit).
**Migration:** none.

## Source drop summary

`src/cryptofactors/ingest/binance.py` was rewritten as v3
(`BINANCE_KLINE_TRANSFORM_VERSION = "3"`, `BINANCE_KLINE_SCHEMA_VERSION = "2"`)
addressing REVIEW-0019 and REVIEW-0020 blocking findings:

1. Cross-object duplicate/gap assessment on the complete multi-object sequence.
2. Empty/header-only archives fail closed with `binance_kline_empty_observations`.
3. Per-row timestamp unit normalization; mixed units reject the object.
4. Market-specific physical volume fields for spot/usdm vs coinm.
5. Stable schema identity/fingerprint for the changed Parquet schema.
6. MAN-001 row counters (`REQUIRE_VERIFIER`) on bars + quality outputs.
7. Explicit header skip only for `open_time`/`opentime`; no silent header heuristics.

## Jr integration notes

- Wrote/rewrote `tests/ingest/market/test_binance_kline.py` with 21 focused
  regressions covering:
  - inclusive-close ms/us + exclusive-close mismatch
  - normalized UTC-microsecond timestamps with source timestamp columns
  - within/cross-object duplicate and gap detection with `scope` lineage
  - empty and header-only fail-closed
  - mixed-unit rows + object rejection + invalid timestamp coverage
  - market physical volume fields (spot/usdm/coinm) and unknown market rejection
  - calendar month `1M`/`1mo` and case-sensitive `1m` vs `1M`
  - `PublishPlan` identity (schema version/fingerprint, transform version)
  - `verify_outputs` MAN-001 verification for the complete returned plan
  - local-only operation; no network imports
- Corrected ticket acceptance command paths in `tickets/BIN-001.md`
  (`src/cryptofactors/ingest/market` → actual `src/cryptofactors/ingest` /
  `tests/ingest/market`).
- No independent production source changes beyond Sr drop integration.

## Validation evidence

| Command | Result |
|---------|--------|
| `pytest tests/ingest/market -q --tb=short` | 21 passed |
| `ruff check src/cryptofactors/ingest tests/ingest` | All checks passed |
| `mypy --no-incremental src/cryptofactors/ingest tests/ingest` | Success (14 files) |
| `pytest -q` (full suite) | passed |
| `python3 scripts/check_repo_control.py` | PASS |

## Status

Integrated and validated. BIN-001 remains `IN_PROGRESS`.
`Next ticket authorized: NONE`.
