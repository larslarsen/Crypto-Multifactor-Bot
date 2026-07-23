# CURRENT_TASK

Ticket: BASE-001
State: READY
Next required actor: Sr Dev (Grok Build)
Next ticket authorized: NONE

Transparent factor baselines (experiment #19): momentum, mean reversion, volume. Each implements Factor protocol. Deterministic, no tuning.

Governing documents:
- tickets/BASE-001.md (READY)
- tickets/NULL-001.md (ACCEPTED)
- docs/reviews/REVIEW-0154_NULL-001_ACCEPTED.md

## Sr Dev Prompt

```
Implement BASE-001: Transparent factor baselines for experiment #19.

Goal: Implement simple, transparent factor baselines using the Factor protocol.

Factors (in order):
1. MomentumFactor — N-day forward return (configurable window, default 20)
2. MeanReversionFactor — z-score vs rolling N-day mean/std (default 20)
3. VolumeFactor — N-day volume ratio vs rolling mean (default 20)

Requirements:
- Each factor implements Factor protocol from cryptofactors.factors.contract
- Deterministic given universe + as_of
- No hyperparameter optimization, just fixed defaults
- Use as-of access (AsOfDataAccess) for price/volume data

Reference implementations:
- NULL-001: src/cryptofactors/factors/null.py (Factor protocol usage)
- NULL-001: tests/test_null_factor.py (substrate integration pattern)
- ASOF-001: src/cryptofactors/catalog/as_of.py (CatalogAsOfStore API)

Files to create:
- src/cryptofactors/factors/baseline.py
- tests/test_baseline_factors.py

Acceptance:
1. All tests pass
2. ruff clean
3. mypy clean
4. check_repo_control.py PASS

After completion: set status to AWAITING_REVIEW.
```

## Stop condition

Sr Dev produces source, stops for Reviewer. No commits until Reviewer accepts.
