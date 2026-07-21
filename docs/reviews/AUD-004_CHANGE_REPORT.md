# AUD-004 — Change Report: native headerless support for Binance precision comparator

**Ticket:** AUD-004
**State:** AWAITING_REVIEW
**Next ticket authorized:** NONE
**Next required actor:** Reviewer

## Source/behavior contract
Integrated Sr Dev's AUD-004 source drop. Changed the native `source_audit.compare_binance_archive_precision`
call path so it works on real Binance daily dumps (aggTrades / klines), which are headerless CSVs.
Existing min-evidence/quality thresholds are preserved. Headed-path contracts from AUD-002 are preserved.
No behavior outside the headerless path changed.

## Files changed
- `src/source_audit/binance_precision.py`
- `src/source_audit/archives.py`
- `src/source_audit/__init__.py`
- `tests/test_binance_precision.py`

## Mechanism
1. Added `read_zip_member_text_prefix` to `archives.py` — bounded-prefix streaming that does not
   require the full declared member size to fit under `max_extracted_bytes`; rejects empty prefix.
2. In headerless mode, `compare_binance_archive_precision` streams only a bounded prefix, then
   keeps at most `max_sample_rows` data rows. Full-member extract is not required, so real daily
   dumps larger than the default bound remain usable.
3. Headed mode keeps the historical full-member `read_zip_member_text` path and schema-length bounds.
4. In headerless mode, require `timestamp_column` as an integer index; reject string column names with
   a `PrecisionComparisonError` citing sample rows in `context`.
5. Treat the first CSV row as data in headerless mode; report schema as `()`.
6. Headerless index validation uses observed data-row width; headed index validation uses schema length.
7. `iter_csv_rows_from_text` accepts `has_header=False` and rejects empty headerless data only.
   Headed header-only CSVs still return an empty data list (historical contract preserved).

## Blocking defects corrected (reviewer)
1. **Headed-path regression:** integer `timestamp_column` bounds and empty-data handling no longer
   diverge from AUD-002 headed behavior.
2. **Real-dump unusability:** headerless path no longer full-extracts the member (`UnsafeArchiveError`
   when declared size > `max_extracted_bytes`); it streams a bounded prefix sample instead.

## Tests added
- `test_headerless_supports_transition_agg_trades`
- `test_headerless_no_transition_when_same_unit_klines`
- `test_headerless_string_column_rejected`
- `test_headerless_out_of_range_index_rejected`
- `test_headerless_schema_diff_reported`
- `test_headerless_prefix_sample_when_full_member_exceeds_bound`
- `test_headed_integer_index_uses_schema_length`
Focused suite: 10 passed.

## Gate results
```bash
PYTHONPATH=src uv run pytest tests/test_binance_precision.py -q --tb=short
# 10 passed
PYTHONPATH=src uv run pytest tests/test_binance_precision.py tests/test_archives.py tests/test_timestamps.py tests/test_pagination.py tests/test_bars.py tests/test_download_atomicity.py -q --tb=short
# focused audit-focused suite passes
PYTHONPATH=src uv run ruff check src/source_audit/binance_precision.py src/source_audit/archives.py tests/test_binance_precision.py
# All checks passed!
PYTHONPATH=src uv run mypy --no-incremental src/source_audit/binance_precision.py src/source_audit/archives.py tests/test_binance_precision.py
# Success: no issues found in 3 source files
python3 scripts/check_repo_control.py
# Repo control check: PASS
```

## Out of scope / preserved
- Does not change `audit_csv_safe`, which remains header-rejecting.
- Headed full-member extract bound behavior unchanged.
- All existing evidence/gate thresholds preserved.
