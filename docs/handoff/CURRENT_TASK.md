# CURRENT_TASK

Ticket: COMP-001
State: READY
Next required actor: Sr Dev (Grok 0.1)
Next ticket authorized: NONE

BASE-001 accepted. Experiment #20 (simple composites) authorized.

## Sr Dev Prompt

```
Create COMP-001: Simple equal-weight rank composite factor.

File: src/cryptofactors/factors/composite.py

Implement EqualWeightRankComposite that combines multiple baseline factors
(momentum, mean_reversion, volume) into a single composite score.

Requirements:
- Implements Factor protocol from cryptofactors.factors.contract
- factor_id = "composite_equal_rank"
- factor_version = "1"
- Constructor takes a list of Factor implementations (the baseline factors)
- compute(universe, as_of):
  1. Call each factor's compute(universe, as_of) to get FactorFrames
  2. For each instrument, rank its score cross-sectionally within each factor
     (rank 1 = best, N = worst; higher score = better rank)
  3. Average the ranks across all factors
  4. score = average rank (lower = better)
  5. raw_value = average rank
  6. Return FactorFrame with factor_id="composite_equal_rank"
- Deterministic given (universe, as_of)
- No hyperparameter tuning
- Handle edge cases: single asset (rank=1), ties (use average rank),
  missing instrument in a factor (skip that factor in the average)

Use the same patterns as baseline.py:
- _require_utc for as_of validation
- _normalize_universe for universe validation
- FactorValue/FactorFrame from contract.py
- BaselineFactorError for errors (reuse or create CompositeFactorError)

Create tests/test_composite_factors.py:
- Unit tests with _FakeAsOf (same as baseline tests) for deterministic computation
- Test with 2+ assets: verify ranks are correct
- Test single asset: rank = 1
- Test ties: average rank assigned
- Test missing instrument in one factor: skipped in average
- Integration test: CatalogAsOfStore → composite → Label → Split → ExperimentBundle
  (same pattern as test_baseline_substrate_integration)

Imports: follow existing patterns in baseline.py. No new dependencies.

After: run tests, stop for reviewer.
```

Governing documents:
- tickets/COMP-001.md (READY)
- tickets/BASE-001.md (ACCEPTED)
- src/cryptofactors/factors/contract.py (39 lines, Factor protocol)
- src/cryptofactors/factors/baseline.py (515 lines, reference implementation)
- tests/test_baseline_factors.py (reference test patterns)

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/test_composite_factors.py -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/factors tests/test_composite_factors.py
3. .venv/bin/python -m mypy --no-incremental src/cryptofactors/factors tests/test_composite_factors.py
4. python3 scripts/check_repo_control.py