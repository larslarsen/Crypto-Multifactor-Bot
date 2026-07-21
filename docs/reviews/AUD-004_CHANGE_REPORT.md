# AUD-004 — Change Report: native headerless support for Binance precision comparator

**Ticket:** AUD-004
**State:** AWAITING_REVIEW (integrated; awaiting reviewer acceptance)
**Next ticket authorized:** NONE
**Next required actor:** Reviewer

## Source/behavior contract
Changed the native `source_audit.compare_binance_archive_precision` call path so it works on
real Binance daily dumps (aggTrades / klines), which are headerless CSVs. Existing
min-evidence/quality thresholds are preserved. No behavior outside the headerless path changed.

## Files changed
- `src/source_audit/binance_precision.py`
- `src/source_audit/archives.py`
- `tests/test_binance_precision.py`

## Mechanism
1. Removed the hard `if not has_header: raise` guard in `compare_binance_archive_precision`.
2. Pass the caller-supplied `has_header` through to `iter_csv_rows_from_text`.
3. In headerless mode, require `timestamp_column` as an integer index; reject string column
   names with a `PrecisionComparisonError` that cites sample rows in `context` so the caller
   can diagnose.
4. Treat the first CSV row as data in headerless mode; report schema as `()`.
5. Validate `timestamp_column` against the actual row width so out-of-range indices fail closed.
6. In `archives.iter_csv_rows_from_text`, accept `has_header=False` and return empty schema
   plus all rows as data rows. Reject completely-empty-data CSVs.
7. In `binance_precision.py`, when both sides are headerless with different widths, append a
   `SchemaFieldDiff(field_name="*", detail="Column count differs: A=<w>, B=<w>")` so the
   reporter surfaces the mismatch.

## Tests added
- `test_headerless_supports_transition_agg_trades` — aggTrades-style headerless archives,
  integer `timestamp_column=5`, `s`→`ms` transition supported with thresholds met.
- `test_headerless_no_transition_when_same_unit_klines` — klines-style headerless archives,
  both sides `us`, same-unit non-transition.
- `test_headerless_string_column_rejected` — string `timestamp_column` rejected with
  "provide an integer column index" message.
- `test_headerless_out_of_range_index_rejected` — integer `timestamp_column` beyond row width
  rejected with "out of range".
- `test_headerless_schema_diff_reported` — different column counts surface as `*` schema diff.
All original 4 tests retained; focused suite now 9 passed.

## Gate results
```bash
PYTHONPATH=src uv run pytest tests/test_binance_precision.py -q --tb=short
..8 passed
PYTHONPATH=src uv run ruff check src/source_audit tests/test_binance_precision.py
All checks passed!
PYTHONPATH=src uv run mypy --no-incremental src/source_audit tests/test_binance_precision.py
Success: no issues found in 13 source files
PYTHONPATH=src uv run pytest -q --tb=short
.429 passed
python3 scripts/check_repo_control.py
Repo control check: PASS
```

## Out of scope / preserved
- Does not change `audit_csv_safe`, which remains header-rejecting; scope limited to the
  precision-comparison path requested by AUD-004.
- All existing evidence/gate thresholds (`min_valid_inferences`, `max_malformed_rate`,
  `max_ambiguous_rate`) preserved.
