# AUD-005 — Change Report: provider-candle comparison by explicit comparable dimensions

**Ticket:** AUD-005
**State:** AWAITING_REVIEW
**Next ticket authorized:** NONE
**Next required actor:** Reviewer

## Summary

Integrated the approved AUD-005 source contract and corrected the Sprint-003 research records so
provider raw-trade count is documented as semantically distinct from aggTrades record count. The
runner now emits the structured comparison result with explicit comparable dimensions and excludes
trade_count from the completed comparison.

## Files changed in this submission
- `src/source_audit/bars.py`
- `src/source_audit/models.py`
- `src/source_audit/__init__.py`
- `scripts/audit/run_sprint003_audit.py`
- `tests/test_bars.py`
- `tests/test_audit_runner_sprint003.py`
- `research/sprint_003/12_AUDIT_EXECUTION.md`
- `research/sprint_003/13_RESEARCH_LEAD_DECISIONS.md`
- `research/sprint_003/audit_results/bar_reconstruction_comparison.json`
- `research/sprint_003/audit_results/csv_schema_timestamp.json`
- `research/sprint_003/audit_results/execution_manifest.json`
- `docs/reviews/REVIEW-0067_AUD-005_SOURCE_TYPE_CORRECTION_REQUIRED.md`
- `docs/reviews/REVIEW-0068_AUD-005_SOURCE_APPROVED_JR_AUTHORIZED.md`
- `docs/reviews/AUD-005_SR_SOURCE_TASK.md`
- `docs/reviews/AUD-005_JR_INTEGRATION_TASK.md`
- `docs/reviews/AUD-005_CHANGE_REPORT.md`
- `tickets/AUD-005.md`
- `docs/handoff/CURRENT_TASK.md`
- `README.md`
- `docs/engineering/IMPLEMENTATION_BACKLOG.csv`

## Regenerated evidence

The runner fixture regenerated these deterministic outputs:

- `research/sprint_003/audit_results/bar_reconstruction_comparison.json`
- `research/sprint_003/audit_results/csv_schema_timestamp.json`
- `research/sprint_003/audit_results/execution_manifest.json`

## Acceptance gates
```bash
PYTHONPATH=src uv run pytest tests/test_bars.py -q --tb=short
# ....................... [100%]
# 23 passed
PYTHONPATH=src uv run pytest tests/test_audit_runner_sprint003.py -q --tb=short
# ...... [100%]
# 6 passed
PYTHONPATH=src uv run ruff check src/source_audit scripts/audit/run_sprint003_audit.py tests/test_bars.py tests/test_audit_runner_sprint003.py
# All checks passed!
PYTHONPATH=src uv run mypy --no-incremental src/source_audit tests/test_bars.py
# Success: no issues found in 13 source files
PYTHONPATH=src uv run pytest -q --tb=short
# 430 passed, 1 warning
python3 scripts/check_repo_control.py
# Repo control check: PASS
```

## Notes

- `compare_bars` now accepts explicit comparable dimensions and preserves historical all-fields
  behavior when omitted.
- The Sprint-003 runner now compares Binance kline quote volume from column 7 and retains column-8
  provider trade count as non-comparable to aggTrades record counts.
