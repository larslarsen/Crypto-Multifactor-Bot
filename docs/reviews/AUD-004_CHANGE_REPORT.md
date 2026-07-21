# AUD-004 — Change Report: native headerless support for Binance archive precision comparator

**Ticket:** AUD-004
**State:** ACCEPTED
**Next ticket authorized:** NONE
**Next required actor:** Reviewer

## Source/behavior contract
The approved runner-boundary correction from `docs/reviews/REVIEW-0062_AUD-004_RUNNER_SOURCE_APPROVED_JR_AUTHORIZED.md` remains in place. This turn made no production-source changes; only evidence and control-plane records were updated.

## Files changed in this submission
- `docs/reviews/AUD-004_CHANGE_REPORT.md`
- `docs/reviews/AUD-004_JR_FINAL_INTEGRATION_TASK.md`
- `docs/reviews/AUD-004_JR_FINAL_PUBLICATION_TASK.md`
- `docs/reviews/REVIEW-0063_AUD-004_FINAL_EVIDENCE_REQUIRED.md`
- `docs/reviews/REVIEW-0063_AUD-004_FINAL_JR_SUBMISSION.md`
- `tickets/AUD-004.md`
- `docs/handoff/CURRENT_TASK.md`
- `README.md`
- `docs/engineering/IMPLEMENTATION_BACKLOG.csv`

## Mechanism
Final publication pass only; no production-source changes in this turn.
1. Preserved the approved `precision_comparison_for_report` boundary conversion exactly.
2. Kept the focused headerless precision regressions: malformed-rate pass/reject at `0.2` and `0.05`, sample-count assertions, and real 12-column kline index checks.
3. Removed stale claims that the serialization failure was unrelated to AUD-004.

## Regression tests added
- `test_headerless_short_first_row_counts_malformed` — malformed rate governs transition decision at two limits, with sampled-row assertions on both archives.
- `test_headerless_real_kline_layout_valid_index_selection` — real 12-column kline layout for index 0 and 6.

## Acceptance gates
```bash
PYTHONPATH=src uv run pytest tests/test_binance_precision.py -q --tb=short
# 12 passed
PYTHONPATH=src uv run pytest tests/test_audit_runner_sprint003.py -q --tb=short
# 6 passed
PYTHONPATH=src uv run ruff check src/source_audit scripts/audit/run_sprint003_audit.py tests/test_binance_precision.py tests/test_audit_runner_sprint003.py
# All checks passed!
PYTHONPATH=src uv run mypy --no-incremental src/source_audit scripts/audit/run_sprint003_audit.py tests/test_binance_precision.py tests/test_audit_runner_sprint003.py
# Found 12 errors in 2 files (checked 15 source files)
PYTHONPATH=src uv run pytest -q --tb=short
# 430 passed, 1 warning
python3 scripts/check_repo_control.py
# Repo control check: PASS
```

## MyPy evidence

### Current command
`PYTHONPATH=src uv run mypy --no-incremental src/source_audit scripts/audit/run_sprint003_audit.py tests/test_binance_precision.py tests/test_audit_runner_sprint003.py`

Current diagnostics:
1. `tests/test_audit_runner_sprint003.py:43: error: Function is missing a return type annotation  [no-untyped-def]`
2. `tests/test_audit_runner_sprint003.py:53: error: Function is missing a return type annotation  [no-untyped-def]`
3. `tests/test_audit_runner_sprint003.py:57: error: Call to untyped function "_run" in typed context  [no-untyped-call]`
4. `tests/test_audit_runner_sprint003.py:61: error: Function is missing a type annotation  [no-untyped-def]`
5. `tests/test_audit_runner_sprint003.py:67: error: Function is missing a type annotation  [no-untyped-def]`
6. `tests/test_audit_runner_sprint003.py:69: error: Call to untyped function "_run" in typed context  [no-untyped-call]`
7. `tests/test_audit_runner_sprint003.py:74: error: Function is missing a type annotation  [no-untyped-def]`
8. `tests/test_audit_runner_sprint003.py:83: error: Function is missing a type annotation  [no-untyped-def]`
9. `tests/test_audit_runner_sprint003.py:91: error: Function is missing a type annotation  [no-untyped-def]`
10. `tests/test_audit_runner_sprint003.py:101: error: Function is missing a type annotation  [no-untyped-def]`
11. `scripts/audit/run_sprint003_audit.py:307: error: Argument 1 to "append" of "list" has incompatible type "dict[str, object]"; expected "dict[str, str]"  [arg-type]`
12. `scripts/audit/run_sprint003_audit.py:592: error: Argument "mode" to "paginate" has incompatible type "str"; expected "PaginationMode"  [arg-type]`

### Baseline command
Baseline worktree: `/tmp/opencode/aud004-baseline` at parent commit `0897b11f4ed618de3dc6617391c48b01bf55b38d`.

`PYTHONPATH=src /home/lars/Crypto_Multifactor_Bot/.venv/bin/mypy --no-incremental src/source_audit scripts/audit/run_sprint003_audit.py tests/test_binance_precision.py tests/test_audit_runner_sprint003.py`

Baseline output:
`mypy: error: Cannot read file 'scripts/audit/run_sprint003_audit.py': No such file or directory`

### Comparison
- REVIEW-0065 accepts that AUD-004 adds no mypy diagnostic.
- The ten `tests/test_audit_runner_sprint003.py` diagnostics are unchanged annotation/call debt.
- The two `scripts/audit/run_sprint003_audit.py` diagnostics are unrelated pre-existing runner sites.
- No diagnostic targets `precision_comparison_for_report`, `precision_report`, the precision
  comparator/archive changes, or `tests/test_binance_precision.py`.

The ticket is accepted under REVIEW-0065, with no next ticket authorized.
