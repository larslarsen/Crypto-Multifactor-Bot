# AUD-004 — Change Report: native headerless support for Binance precision comparator

**Ticket:** AUD-004
**State:** AWAITING_REVIEW
**Next ticket authorized:** NONE
**Next required actor:** Reviewer

## Source/behavior contract
Integrated reviewer-approved local behavior under `docs/reviews/REVIEW-0059_AUD-004_SOURCE_APPROVED_JR_AUTHORIZED.md`. The committed production source already uses max observed width across sampled rows in headerless mode, so short first rows reach `_analyze` and are governed by `max_malformed_rate`. This submission adds integration regressions and records truthful gate evidence.

## Files changed in this submission
- `src/source_audit/binance_precision.py` — no change
- `src/source_audit/archives.py` — no change
- `src/source_audit/__init__.py` — no change
- `tests/test_binance_precision.py`
- `docs/reviews/AUD-004_CHANGE_REPORT.md`
- `docs/reviews/REVIEW-0060_AUD-004_INTEGRATION_EVIDENCE_REQUIRED.md`
- `docs/reviews/AUD-004_JR_INTEGRATION_TASK.md`
- `docs/reviews/AUD-004_JR_FINAL_EVIDENCE_TASK.md`
- `tickets/AUD-004.md`
- `docs/handoff/CURRENT_TASK.md`
- `README.md`
- `docs/engineering/IMPLEMENTATION_BACKLOG.csv`

## Mechanism
Final Jr integration layer only; no production-source changes in this commit.
1. Strengthened `test_headerless_short_first_row_counts_malformed` to assert that within `max_malformed_rate=0.2` the comparison supports the timestamp-precision transition, and that under `max_malformed_rate=0.05` the comparison rejects with `max_malformed_rate` in `transition_rationale`. Malformed counts and sampled-row counts are asserted for both archives.
2. Retained the real-kline-layout regression confirming `timestamp_column=0` and `6` both return valid unit inference in 12-column kline fixtures.
3. Corrected kline test fixtures so both openTime and closeTime contain parseable timestamps; an earlier literal at index 6 produced zero valid inferences.

## Regression tests added
- `test_headerless_short_first_row_counts_malformed` — malformed rate governs transition decision at two limits.
- `test_headerless_real_kline_layout_valid_index_selection` — real 12-column kline layout for index 0 and 6.

## Acceptance gates
```bash
PYTHONPATH=src uv run pytest tests/test_binance_precision.py -q --tb=short
# 12 passed
PYTHONPATH=src uv run pytest -q --tb=short
# 117 passed, 3 xfailed, 5 errored, 1 xpassed in 84.98s
PYTHONPATH=src uv run ruff check src/source_audit tests/test_binance_precision.py
# All checks passed!
PYTHONPATH=src uv run mypy --no-incremental src/source_audit tests/test_binance_precision.py
# Success: no issues found in 13 source files
python3 scripts/check_repo_control.py
# Repo control check: PASS
```

## Blocker — sprint003 runner
`PYTHONPATH=src uv run pytest -q --tb=short` has 5 errors in `tests/test_audit_runner_sprint003.py`. Each is a setup failure when `pytest` invokes `scripts/audit/run_sprint003_audit.py` in a subprocess. Direct runner invocation fails with:
```
source_audit.errors.SerializationError: float is not supported; use Decimal for numeric values | context={'value': '0.1'}
```
This is a distinct production-source defect in `source_audit/serialization.py`: the runner emits `float('0.1')` data where the normalizer now requires `Decimal`. `/tmp/crypto_source_audit` is present. Running full suite in the supported test environment completes setup but fails at this runtime defect; requirement to run the complete suite without weakening tests is therefore blocked by a production-source defect unrelated to AUD-004. ticket and handoff are set to `AWAITING_REVIEW`; reviewer may choose to authorize a source defect task against `serialization.py` independently.
