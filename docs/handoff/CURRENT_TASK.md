# CURRENT_TASK

Ticket: NULL-001
State: READY
Next required actor: Sr Dev (Grok Build)
Next ticket authorized: NONE

Reviewer decision recorded: UNIVERSE-001 accepted with Option C (bounded non-survivorship-free universe with current BAR-001 instruments). CoinGecko doesn't provide listing/delisting dates. CoinMarketCap needed for true survivorship-free.

Governing documents:
- tickets/NULL-001.md (READY)
- tickets/UNIVERSE-001.md (ACCEPTED, Option C)
- docs/reviews/REVIEW-0150_UNIVERSE-001_REJECTED.md
- docs/reviews/REVIEW-0148_EXP-001_ACCEPTED.md

## Sr Dev Prompt

```
Implement NULL-001: Null factor test for experiment #18.

Goal: Test that a random/unpredictable factor has no edge.

Requirements:
1. `NullFactor` class implementing minimal factor protocol
2. `NullFactor.compute(universe, as_of)` returns random noise values
3. No signal, no edge
4. Test: null factor Sharpe ratio should be ~0 (within ±0.5)
5. Test: null factor win rate should be within 45-55%
6. Run 10 trials, check consistency

Reference implementations:
- EXP-001: src/cryptofactors/validation/experiment.py (ExperimentBundle, fingerprinting)
- LABEL-001: src/cryptofactors/validation/labels.py (AsOfLabelEngine)
- ASOF-001: src/cryptofactors/catalog/as_of.py (CatalogAsOfStore)

Files to create:
- src/cryptofactors/factors/null.py
- tests/test_null_factor.py

Acceptance:
1. All tests pass
2. ruff clean
3. mypy clean
4. check_repo_control.py PASS

After completion: set status to AWAITING_REVIEW.
```

## Stop condition

Sr Dev produces source, stops for Reviewer. No commits until Reviewer accepts.
