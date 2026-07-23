# NULL-001 — Null Factor Test (Experiment #18)

**Priority:** P0
**Status:** BLOCKED
**Dependencies:** EXP-001 (accepted), LABEL-001 (accepted), ASOF-001 (accepted), UNIVERSE-001 (accepted)
**Layer:** validation
**Architecture:** implements experiment #18 (null/noise factor test); no ADR required

## Objective

Test that a random/unpredictable factor has no edge. This is the first experiment to validate the research substrate.

## Required Contract

- `NullFactor` implements factor protocol (if it exists)
- Factor values are random noise (uniform or normal)
- No signal, no edge
- Test: null factor Sharpe ratio should be ~0 (within noise)
- Test: null factor should not consistently outperform random

## Test Strategy

- Generate null factor values for 100 random coins over 365 days
- Run simple portfolio simulation (long top decile, short bottom decile)
- Check Sharpe ratio is within ±0.5 of zero
- Check win rate is within 45-55%
- Run 10 trials, check consistency

## Deliverables

- `src/cryptofactors/factors/null.py`
- `tests/test_null_factor.py`
- Ticket + governance
- Tests + gates (Jr)

## Out of Scope

- Factor protocol definition (if not exists, create minimal one)
- Full portfolio simulation (use simple long/short)
- Real data (use synthetic BAR-001 data)

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/test_null_factor.py -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/factors tests/test_null_factor.py`
3. `.venv/bin/python -m mypy --no-incremental src/cryptofactors/factors tests/test_null_factor.py`
4. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Grok): production source only. Stop for reviewer.
- Jr Dev (Hermes): tests, gates, records, Git, commit, push after approval.

## Stop Condition

After Jr: AWAITING_REVIEW, Reviewer next, NONE.
