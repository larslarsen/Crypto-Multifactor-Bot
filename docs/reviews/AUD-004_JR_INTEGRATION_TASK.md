# AUD-004 - JR INTEGRATION TASK

**Ticket:** `tickets/AUD-004.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED - REVIEW-0060 REQUIRES FINAL TEST/EVIDENCE CORRECTION
**Next ticket:** `NONE`

## Assignment

Integrate the reviewer-approved local Sr correction governed by
`docs/reviews/REVIEW-0059_AUD-004_SOURCE_APPROVED_JR_AUTHORIZED.md`.

## Required Tests

- Add a headerless regression whose first row is shorter than `timestamp_column` and whose
  remaining rows provide enough valid inferences. Assert that the short row is counted malformed
  and the configured malformed-rate threshold determines the result.
- Correct the kline fixture to use the real 12-column Binance kline order and select timestamp
  index 0 or 6.
- Retain aggTrades, headed-path, prefix-bound, string-index, out-of-range, schema-difference, and
  evidence-threshold coverage.

## Acceptance Gates

Run and record:

1. `PYTHONPATH=src uv run pytest tests/test_binance_precision.py -q --tb=short`
2. `PYTHONPATH=src uv run ruff check src/source_audit tests/test_binance_precision.py`
3. `PYTHONPATH=src uv run mypy --no-incremental src/source_audit tests/test_binance_precision.py`
4. `PYTHONPATH=src uv run pytest -q --tb=short`
5. `python3 scripts/check_repo_control.py`

## Records And Publication

Update `docs/reviews/AUD-004_CHANGE_REPORT.md` with exact test counts and gate output. Update the
ticket and handoff to `AWAITING_REVIEW`, name Reviewer as next actor, retain
`Next ticket authorized: NONE`, commit the approved source/tests/records, and push them.

## Completion Condition

The published repository contains the approved source, regression tests, exact gate evidence, and
an `AWAITING_REVIEW` handoff for final reviewer decision.
