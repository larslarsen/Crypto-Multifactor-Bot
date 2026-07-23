# COMP-001 — Simple Composites (Experiment #20)

**Priority:** P0
**Status:** READY
**Dependencies:** BASE-001 (accepted), EXP-001 (accepted), LABEL-001 (accepted), SPLIT-001 (accepted), ASOF-001 (accepted)
**Layer:** factors
**Architecture:** implements experiment #20 (simple composites); no ADR required

## Objective

Combine the three baseline factors (momentum, mean reversion, volume) into simple
composite scores. Composites are transparent, fixed-weight combinations — no
optimization, no learning. These establish whether diversification across
baseline factors improves on any single factor.

## Required Contract

- Composite implements `Factor` protocol from `cryptofactors.factors.contract`
- Deterministic given universe + as_of
- Fixed combination method (no hyperparameter tuning)
- Pre-registered: equal-weight rank average

## Composite Methods (in order)

1. **Equal-Weight Rank Composite** — rank each factor cross-sectionally, average
   ranks across factors, score = average rank

## Test Strategy

- Unit tests: deterministic computation, edge cases (single asset, ties, missing)
- Integration: run through research substrate (same as BASE-001)
- No expectation of edge; composites only

## Deliverables

- `src/cryptofactors/factors/composite.py`
- `tests/test_composite_factors.py`
- Ticket + governance
- Tests + gates (Jr)

## Out of Scope

- Optimized weights (experiment #21+)
- ML-based composites
- Non-equal weighting schemes

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/test_composite_factors.py -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/factors tests/test_composite_factors.py`
3. `.venv/bin/python -m mypy --no-incremental src/cryptofactors/factors tests/test_composite_factors.py`
4. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Grok): production source only. Stop for reviewer.
- Jr Dev (Hermes): tests, gates, records, Git, commit, push after approval.

## Stop Condition

After Sr: AWAITING_REVIEW, Reviewer next, NONE.