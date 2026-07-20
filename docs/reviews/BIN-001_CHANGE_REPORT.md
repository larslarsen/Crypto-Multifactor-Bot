# BIN-001 — Change Report: Binance archive kline normalizer

**Ticket:** BIN-001
**State:** ACCEPTED by REVIEW-0025
**Next ticket authorized:** BAR-001

## Integrated Sr Dev drop — REVIEW-0023 v4 source-reviewed

- Production file: `src/cryptofactors/ingest/binance.py`
- Source-review status: reviewed and integrated; no additional production changes in this integration.
- Transform: `BINANCE_KLINE_TRANSFORM_VERSION = "4"`
- Schema: `BINANCE_KLINE_SCHEMA_VERSION = "2"`

## Integration

- `tests/ingest/market/test_binance_kline.py`: 30 focused v4 regressions covering:
  - required non-empty `code_commit`; rejects `""` and `"unknown"`
  - explicit 64-hex `config_sha256` preserved and invalid values rejected
  - auto-derived `config_sha256` is 64-character lowercase hex
  - inclusive-close ms/us, exclusive-close interval mismatch
  - per-row mixed-unit normalization with normalized UTC-microsecond values plus `source_timestamp_unit`
  - invalid timestamp issue; `CoverageWindow` bounds
  - within/cross-object duplicate and gap detection
  - empty and header-only fail-closed
  - malformed first row not silently treated as header
  - calendar month `1M` month-end and leap-year inclusive-close correctness
  - case-sensitive `1m` vs `1M`
  - spot/USD-M/COIN-M physical volume columns plus partition units
  - unknown market rejection
  - complete `PublishPlan` MAN-001 verification
  - successful `DatasetPublisher.publish` with temp catalog/store registration
  - raw-object lineage on every output partition
  - `DependencyKind.RAW_OBJECT` on all declared dependencies
  - local-only operation via package resource lookup

## Final integration record

| Finding | Integration action |
|---------|-------------------|
| Empty `config_sha256` invalid | Derive deterministic 64-hex when omitted |
| Empty/unknown `code_commit` | Require non-empty caller-supplied non-placeholder |
| Publication test baked in failure | Replaced with successful publish returning catalog-registered receipt |
| Month-end/leap tests only parser-level | Added calendar `_expected_close_inclusive` normalization |
| Coverage not asserted | Assert exact values; current single-bar bounds both equal open instant |
| Market tests only names | Assert physical CSV values map to correct columns |
| Deterministic-config hash not proven | Added `test_derived_config_sha256_is_deterministic_and_normalization_sensitive` |
| Month-end test name false | Renamed `_jan31_to_feb28` → `_jan31_to_feb29` |
| Review-policy `config_sha256` constant constraint | No new constants added; derivation + validation implemented in `binance.py` |

## Fresh gate evidence on `b881335817e9390011a37afb73b522d985746416`

Full gate output: `docs/reviews/bin001_gates_review24.txt`

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/ingest/market -q --tb=short` | 30 passed |
| `PYTHONPATH=src uv run pytest -q` | passed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/ingest tests/ingest/market` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/ingest tests/ingest/market` | Success |
| `python3 scripts/check_repo_control.py` | PASS |

## Git artifacts

- Integration commit: `b881335817e9390011a37afb73b522d985746416`
- Test function count in file: 30
