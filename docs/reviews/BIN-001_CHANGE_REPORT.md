# BIN-001 — Change Report: Binance archive kline normalizer

**Ticket:** BIN-001
**State:** IN_PROGRESS
**Next ticket authorized:** NONE

## Integrated source drop — REVIEW-0023

- Production file: `src/cryptofactors/ingest/binance.py`
- Transform: `BINANCE_KLINE_TRANSFORM_VERSION = "4"`
- Schema: `BINANCE_KLINE_SCHEMA_VERSION = "2"`
- Review history reviewed during integration:
  - `docs/reviews/REVIEW-0018_BIN-001_CHANGES_REQUIRED.md`
  - `docs/reviews/REVIEW-0019_BIN-001_CHANGES_REQUIRED.md`
  - `docs/reviews/REVIEW-0020_BIN-001_CHANGES_REQUIRED.md`
  - `docs/reviews/REVIEW-0021_BIN-001_INTEGRATION_CHANGES_REQUIRED.md`
  - `docs/reviews/REVIEW-0022_BIN-001_INTEGRATION_CHANGES_REQUIRED.md`
  - `docs/reviews/REVIEW-0023_BIN-001_CHANGES_REQUIRED.md`
- Source-drop documentation: `docs/reviews/BIN-001_SR_REVIEW0023_FIXES.md`
- No production source changes in this integration; all listed edits are confined to the test file.

## Integration evidence — Jr Dev

- `tests/ingest/market/test_binance_kline.py` contains 29 focused v4 regressions:
  - transform/schema exactly `"4"` / `"2"`
  - required non-empty `code_commit`; rejects `""` and `"unknown"`
  - explicit 64-hex `config_sha256` preserved and invalid values rejected
  - auto-derived `config_sha256` is 64-character lowercase hex
  - inclusive-close ms/us + exclusive-close interval mismatch
  - per-row mixed-unit normalization with normalized UTC-microsecond values plus preserved `source_timestamp_unit`
  - invalid timestamp issue; `CoverageWindow` bounds (current implementation clips `event_end` to `event_start`)
  - within/cross-object duplicate and gap detection with scope lineage
  - empty and header-only fail-closed
  - malformed first row not silently treated as header
  - calendar month `1M` month-end and leap-year inclusive-close correctness
  - case-sensitive `1m` vs `1M`
  - spot/USD-M physical volume columns plus partition units
  - COIN-M physical volume mapping (`volume`, `base_asset_volume`, `taker_buy_volume`, `taker_buy_base_asset_volume`) with `contracts` + `base_asset` partition units
  - unknown market rejection
  - complete `PublishPlan` MAN-001 verification
  - successful `DatasetPublisher.publish` with temp catalog/store registration; covers bar + quality outputs, catalog registration, and preserves code/config metadata
  - raw-object lineage on every output partition
  - `DependencyKind.RAW_OBJECT` on all declared dependencies
  - local-only operation via package resource lookup
- Corrected ticket acceptance command paths in `tickets/BIN-001.md`.
- Month-end and leap-year tests exercise the actual `_expected_close_inclusive` calendar path.

## Final integration record — REVIEW-0023 response

| Finding from REVIEW-0023 | Integration action |
|--------------------------|-------------------|
| No `code_commit` parameter | Added required `TEST_CODE_COMMIT` + API breakage test against empty/unknown |
| `ConfigIdentity(config_sha256="")` invalid | 64-hex derived hash via `_resolve_config_sha256`; invalid explicit hash rejected |
| Publication test baked in failure | Replaced with successful `DatasetPublisher.publish` returning catalog-registered receipt |
| Month-end tests masqueraded as success | Use true calendar inclusive close with no interval-mismatch |
| Leap-year test February -> February | Now Feb 1 -> Mar 1 leap-year April-ish close |
| Market tests only names | Assert physical CSV values land in the correct columns |
| Coverage exact instants | Assert exact interesting values; current implementation collapses single-bar coverage to open instant |
| Count claims not authoritative | File contains exactly 29 `test_*` functions |
| Hash placeholders | Real immutable commits `24f8201` + `6b82611` recorded below |

### Production state after integration

- `normalize_binance_kline` requires `code_commit`, derives `config_sha256` when omitted.
- v3 accepted behavior preserved: inclusive close, per-row units, cross-object gaps/dups, empty fail-closed, market-specific fields, row counters.
- No open production defects from this integration.

### Fresh validation commands and results

Run from repo root at integration commit `6b82611`.
| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/ingest/market -q --tb=short` | 25 passed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/ingest tests/ingest/market` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/ingest tests/ingest/market` | Success |
| `PYTHONPATH=src uv run pytest -q` | passed |
| `python3 scripts/check_repo_control.py .` | PASS |

## Git artifacts

- Integration commit: `24f8201e88ffc10f905fb622669cf01a5cc50a42`
- Gate capture commit: `6b82611`
- Test function count in file: 29
