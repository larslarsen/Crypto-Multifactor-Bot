# LABEL-001 — Label / Event Interval Separation Engine

**Priority:** P0
**Status:** AWAITING_REVIEW
**Dependencies:** ASOF-001, SPLIT-001 (accepted)
**Layer:** validation / labels
**Architecture:** implements architecture requirement for label / event-interval separation; no ADR required

## Objective

Produce deterministic labeled decision events with explicit event-start/event-end intervals strictly separated from feature windows, so labels never leak.

## Required contract

- Input: list of instruments, decision cadence (e.g. daily), label horizon (timedelta), label type.
- Output: ordered `DecisionEvent` objects with instrument_id, decision_time, event_start, event_end, label_direction, label_value.
- Label types: forward_return, sign (up/down), binary.
- **Separation rule:** label window [event_start, event_end) must begin at or after decision_time + min_gap (default 0). Feature data may only use observations with availability_time <= decision_time.
- All instrument/price access via reviewed AsOfStore.
- Deterministic from same inputs.
- Insufficient data → fail closed.

## Deliverables

- `src/cryptofactors/validation/labels.py` (or labels.py in separate module)
- Public exports
- Ticket + governance
- Tests + gates (Jr)

## Out of scope

- Factor materialization, portfolio, experiments
- Universe (blocked by DF-08)
- New data sources

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/validation/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/validation tests/validation`
3. `.venv/bin/python -m mypy --no-incremental src/cryptofactors/validation tests/validation`
4. `python3 scripts/check_repo_control.py`

## Phased ownership

- Sr Dev (Grok): production source only. Stop for reviewer.
- Jr Dev (Hermes): tests, gates, records, Git, commit, push after approval.

## Stop condition

After Jr: AWAITING_REVIEW, Reviewer next, NONE.