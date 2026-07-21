# AUD-004 — Change Report: native headerless support for Binance archive precision comparator

**Ticket:** AUD-004
**State:** BLOCKED
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

## Blocker — mypy typing debt
`PYTHONPATH=src uv run mypy --no-incremental src/source_audit scripts/audit/run_sprint003_audit.py tests/test_binance_precision.py tests/test_audit_runner_sprint003.py` reports 12 existing errors in 2 files, with 15 source files checked. The errors are the pre-existing `no-untyped-def` / `no-untyped-call` test annotations and the two runner-side type mismatches already visible in the approval history. The repository is therefore published in `BLOCKED` state for Reviewer review, with no next ticket authorized.
