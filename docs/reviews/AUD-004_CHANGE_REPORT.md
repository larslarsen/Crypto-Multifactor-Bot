# AUD-004 — Change Report: native headerless support for Binance precision comparator

**Ticket:** AUD-004
**State:** IN_PROGRESS
**Next ticket authorized:** NONE
**Next required actor:** Sr Dev - Sandbox

## Source/behavior contract
Integrated reviewer-approved local source under `docs/reviews/REVIEW-0059_AUD-004_SOURCE_APPROVED_JR_AUTHORIZED.md`.
- `src/source_audit/binance_precision.py`: `_max_row_width` computes max field count across the sample, not `rows[0]` only.
- Short first rows reach `_analyze` and are governed by `max_malformed_rate`.

## Files changed in this control-plane update
- `src/source_audit/binance_precision.py` — REVIEW-0059 source correction (committed)
- `tests/test_binance_precision.py` — headerless regressions (committed)
- `docs/reviews/AUD-004_CHANGE_REPORT.md`
- `docs/handoff/CURRENT_TASK.md`
- `tickets/AUD-004.md`
- `README.md`
- `docs/engineering/IMPLEMENTATION_BACKLOG.csv`
- Review docs: REVIEW-0060→RESOLVED, REVIEW-0061 + tasks (committed)

## Gates passed
```bash
PYTHONPATH=src uv run pytest tests/test_binance_precision.py -q --tb=short
# 12 passed
PYTHONPATH=src uv run ruff check src/source_audit tests/test_binance_precision.py
# All checks passed!
PYTHONPATH=src uv run mypy --no-incremental src/source_audit tests/test_binance_precision.py
# Success: no issues found in 13 source files
python3 scripts/check_repo_control.py
# Repo control check: PASS
```

## Blocker
Full-suite gate (`PYTHONPATH=src uv run pytest -q --tb=short`) blocked by production-source defect in `src/source_audit/serialization.py`:
```
source_audit.errors.SerializationError: float is not supported; use Decimal for numeric values | context={'value': '0.1'}
```
Runner invokes `run_sprint003_audit.py` which serializes float threshold values. This is the exact issue REVIEW-0061 escalates.

## Ownership sequence
Sr Dev - Sandbox owns `scripts/audit/run_sprint003_audit.py` source correction per REVIEW-0061. After reviewer source approval, Jr Dev - Hermes integrates and publishes full-suite evidence.