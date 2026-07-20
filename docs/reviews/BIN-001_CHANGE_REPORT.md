# BIN-001 — Change Report: Binance archive kline normalizer

**Ticket:** BIN-001
**State:** IN_PROGRESS
**Next ticket authorized:** NONE

## Accepted Sr Dev drops — v4 RETURNED -> v4 ACCEPTED

- First drop: transform/schema validators, `_require_code_commit`, `_canonical_config_bytes`, `_resolve_config_sha256`, empty-string defect fixed in `src/cryptofactors/ingest/binance.py`.
- Second drop: identical functionally, accepted and integrated.
- Transform: `BINANCE_KLINE_TRANSFORM_VERSION = "4"`
- Schema: `BINANCE_KLINE_SCHEMA_VERSION = "2"`

## Integration

- No additional production changes beyond Sr drop acceptance.
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
| Count claims not authoritative | File contains exactly 29 `test_*` functions |
| Test function count in file | 30 |
| Review-0024 gate commit | `7f4163b` |
| Control-plane command | `python3 scripts/check_repo_control.py` |
