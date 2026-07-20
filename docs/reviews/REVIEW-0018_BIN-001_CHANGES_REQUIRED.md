# REVIEW-0018 — BIN-001 INTEGRATION: CHANGES_REQUIRED

**Ticket:** BIN-001 — Binance archive kline normalizer
**Integrated drop:** `src/cryptofactors/ingest/binance.py` (Sr Dev — Hermes, in-tree edit; no commit by Sr)
**Integrated by:** Hermes (Jr Dev) per control-plane governance
**Status:** CHANGES_REQUIRED (Sr-source defect; integration landed, 2 required cases unmet)
**Date:** 2026-07-19

## Scope integrated

- `src/cryptofactors/ingest/binance.py` (new, ~536 lines): `normalize_binance_kline`
  normalizer consuming registered `RawObject` ZIP/CSV kline archives; Decimal prices,
  per-object timestamp-unit inference (ms/us), typed `QualityIssue` surfacing, MAN-001
  `PublishPlan` construction with raw-object lineage.
- `tests/ingest/market/test_binance_kline.py` (new): 12 focused regressions.
- `pyproject.toml`: mypy override for untyped `pyarrow` (env has no `py.typed` marker).
- Jr integration fixes to the Sr drop (see Defects).

## Validation (acceptance commands)

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/ingest/market -q` | 10 passed, 2 xfailed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/ingest tests/ingest` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/ingest tests/ingest` | Success (14 files) |
| `PYTHONPATH=src uv run pytest -q` (full suite) | passed |
| `python3 scripts/check_repo_control.py` | PASS |

## Defects found (Sr-source)

**D1 — `pa.table([], schema=...)` empty-array bug (fixed by Jr).** In
`_write_parquet_bars` and `_write_quality_parquet`, the empty-path built a 12-/5-field
schema but passed **zero arrays** → `ValueError: Schema and number of arrays unequal`.
Fired on any archive yielding zero parsed bars (empty CSV, header-only, all-malformed).
Jr fix: `pa.table([[] for _ in range(len(schema))], schema=schema)`.

**D2 — missing `import` lint (fixed by Jr).** Unused `dataclasses.field`,
`typing.Mapping`; ambiguous variable `l` (E741) in `_infer_ts_unit`, `_ohlc_violation`,
`_parse_kline_row`. Jr renamed to `length`/`low` and dropped unused imports.

**D3 — duplicate-open-time detection NOT implemented (required case unmet).** BIN-001
requires "duplicate and gap handling through quality issues." The integr... no code path
emits a duplicate-open_time `QualityIssue`. `test_duplicate_open_time_surfaces_issue` is
`xfail(strict=True)` pending Sr implementation of `binance_kline_duplicate_open_time`.

**D4 — gap detection NOT implemented (required case unmet).** No code compares
consecutive `open_time` deltas against the declared interval to surface a gap
`QualityIssue`. `test_gap_between_rows_surfaces_issue` is `xfail(strict=True)` pending Sr
implementation of `binance_kline_gap`.

## Accepted invariants (verified)

- No network: normalizer reads only local `RawObject.storage_path` bytes.
- Explicit params required (market_type/interval/venue_id/instrument_id) — empty raises.
- Timestamp unit inferred per-object from data length (ms 13-digit, us 16-digit), not
  filename/date.
- UTC interval semantics validated (close_time == open_time + interval).
- OHLC invariants validated; quote/base volumes preserved as Decimal (no float).
- Source-object lineage present on every output partition (bar + quality).
- Malformed/header rows handled; issues surfaced, never silently dropped/repaird.

## Disposition

Integration complete; 10/12 required-case regressions pass. D3/D4 are genuine Sr-source
gaps in BIN-001's required cases. Relay to Sr Dev — Hermes (or Sr Dev — Grok Build) to
implement duplicate/gap detection; on completion, remove the two `xfail` markers and
re-run the acceptance commands. BIN-001 remains `IN_PROGRESS`; `Next ticket authorized:
NONE`.
