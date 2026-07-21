# AUD-004 - JR FINAL INTEGRATION TASK

**Ticket:** `tickets/AUD-004.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETE - REVIEW-0063 BLOCKED RECORDS RECORDED
**Next ticket:** `NONE`

## Assignment

Integrate the local runner correction approved by
`docs/reviews/REVIEW-0062_AUD-004_RUNNER_SOURCE_APPROVED_JR_AUTHORIZED.md` and produce final,
truthful AUD-004 acceptance evidence.

## Required Work

- Preserve the approved `precision_comparison_for_report` boundary conversion exactly.
- Extend `test_headerless_short_first_row_counts_malformed` with archive-B malformed and
  sampled-row assertions.
- Exercise the Sprint-003 runner path that serializes a successful native precision comparison.
- Remove stale claims that the serialization failure is unrelated or that failed gates passed.

## Acceptance Gates

Run and record:

1. `PYTHONPATH=src uv run pytest tests/test_binance_precision.py -q --tb=short`
2. `PYTHONPATH=src uv run pytest tests/test_audit_runner_sprint003.py -q --tb=short`
3. `PYTHONPATH=src uv run ruff check src/source_audit scripts/audit/run_sprint003_audit.py tests/test_binance_precision.py tests/test_audit_runner_sprint003.py`
4. `PYTHONPATH=src uv run mypy --no-incremental src/source_audit scripts/audit/run_sprint003_audit.py tests/test_binance_precision.py tests/test_audit_runner_sprint003.py`
5. `PYTHONPATH=src uv run pytest -q --tb=short`
6. `python3 scripts/check_repo_control.py`

## Records And Publication

The exact command outputs were recorded in `docs/reviews/AUD-004_CHANGE_REPORT.md`. Because the
full-suite mypy gate still reports pre-existing typing errors, the published repository remains
`BLOCKED`; the ticket and handoff were aligned to Reviewer with `Next ticket authorized: NONE`.

## Completion Condition

The published repository contains the approved runner correction, complete regressions, truthful
records, and a `BLOCKED` handoff for final reviewer decision.
