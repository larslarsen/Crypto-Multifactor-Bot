# BIN-001 — Change Report: Binance archive kline normalizer

**Ticket:** BIN-001
**State:** IN_PROGRESS
**Next ticket authorized:** NONE

## Integrated source drop

- Source drop from Sr Dev — Grok Build local filesystem edit (no zip, no Sr commit).
- Integrated production file: `src/cryptofactors/ingest/binance.py`
- Transform: `BINANCE_KLINE_TRANSFORM_VERSION = "3"`
- Schema: `BINANCE_KLINE_SCHEMA_VERSION = "2"`
- Review history reviewed during integration:
  - `docs/reviews/REVIEW-0018_BIN-001_CHANGES_REQUIRED.md`
  - `docs/reviews/REVIEW-0019_BIN-001_CHANGES_REQUIRED.md`
  - `docs/reviews/REVIEW-0020_BIN-001_CHANGES_REQUIRED.md`
  - `docs/reviews/REVIEW-0021_BIN-001_INTEGRATION_CHANGES_REQUIRED.md`

## Behavioral claims from v3

1. Cross-object duplicate/gap assessment on the complete multi-object sequence.
2. Empty/header-only archives fail closed with `binance_kline_empty_observations`.
3. Per-row timestamp unit normalization; mixed units reject the object.
4. Market-specific physical volume fields for spot/usdm vs coinm.
5. Stable schema identity/fingerprint for the changed Parquet schema.
6. MAN-001 row counters (`REQUIRE_VERIFIER`) on bars + quality outputs.
7. Explicit header skip only for `open_time`/`opentime`; no silent header heuristic.
8. Local-only operation; no network imports used by the normalizer.

## Integration evidence from Jr Dev

- Wrote/rewrote `tests/ingest/market/test_binance_kline.py` with 22 focused
  regressions covering:
  - inclusive-close ms/us + exclusive-close mismatch
  - normalized UTC-microsecond timestamps with source timestamp columns
  - per-row unit inference; mixed-unit object rejection with issue/surface check
  - invalid timestamp issue coverage
  - within/cross-object duplicate and gap detection with scope lineage
  - empty and header-only fail-closed
  - malformed first row not silently treated as header
  - calendar month `1M`/`1mo` and case-sensitive `1m` vs `1M`
  - market physical volume fields spot/USD-M/COIN-M plus partition unit metadata
  - unknown market type rejection
  - complete `PublishPlan` MAN-001 verification against the returned plan
  - raw-object lineage on every output partition
  - local-only operation; no network imports in source
- Corrected ticket acceptance command paths in `tickets/BIN-001.md`
  (`src/cryptofactors/ingest/market` → actual `src/cryptofactors/ingest` /
  `tests/ingest/market`).
- Removed brittle hard-coded checkout path from `test_no_network_used`.
- No independent production source changes beyond Sr drop integration.

## Fresh validation commands and results

Run from repo root at integration commit `2df75b2`.

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/ingest/market -q --tb=short` | 22 passed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/ingest tests/ingest/market` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/ingest tests/ingest/market` | Success (13 files) |
| `PYTHONPATH=src uv run pytest -q` | passed |
| `python3 scripts/check_repo_control.py` | PASS |

## Git artifacts

- Integration commit: `2df75b2ed1d247eb409613e9e5e0aaac6eae3d41` (origin/main)
