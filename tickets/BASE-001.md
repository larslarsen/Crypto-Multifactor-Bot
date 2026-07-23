# BASE-001 — Transparent Factor Baselines (Experiment #19)

**Priority:** P0
**Status:** BLOCKED
**Dependencies:** ASOF-002 (READY), NULL-001 (accepted), EXP-001 (accepted), LABEL-001 (accepted), ASOF-001 (accepted)
**Blocked by:** ASOF-002 — CatalogAsOfStore half-open window excludes completed bars at availability_time
**Layer:** factors
**Architecture:** implements experiment #19 (transparent factor baselines in preregistered order); no ADR required

## Objective

Implement simple, transparent factor baselines that produce explainable factor scores with known economic rationale. These baselines serve as the foundation against which ML challengers will be compared.

## Required Contract

- Each factor implements `Factor` protocol from `cryptofactors.factors.contract`
- Factors are deterministic given universe + as_of
- Simple, transparent formulas with no hyperparameter tuning
- Pre-registered order: momentum first, then mean-reversion, then volume-based

## Factors (in order)

1. **Momentum** — N-day forward return (e.g. 20d, 60d)
2. **Mean Reversion** — N-day z-score vs rolling mean/std
3. **Volume** — N-day volume ratio vs rolling mean

## Test Strategy

- Each factor: unit tests for deterministic computation, edge cases
- Integration: run each through research substrate (same as NULL-001)
- No single factor expected to produce edge; baselines only

## Deliverables

- `src/cryptofactors/factors/baseline.py` (momentum, mean_reversion, volume)
- `tests/test_baseline_factors.py`
- Ticket + governance
- Tests + gates (Jr)

## Out of Scope

- Hyperparameter optimization
- Composite/combined factors (experiment #20)
- ML factors (experiment #21)

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/test_baseline_factors.py -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/factors tests/test_baseline_factors.py`
3. `.venv/bin/python -m mypy --no-incremental src/cryptofactors/factors tests/test_baseline_factors.py`
4. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Grok): production source only. Stop for reviewer.
- Jr Dev (Hermes): tests, gates, records, Git, commit, push after approval.

## Stop Condition

After Jr: AWAITING_REVIEW, Reviewer next, NONE.
