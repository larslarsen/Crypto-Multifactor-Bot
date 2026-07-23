# CURRENT_TASK

Ticket: ML-001
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

ML-001 (experiment #21 — ML challengers) production source and tests complete.
Three ML factors (Ridge, ElasticNet, XGBoost) with expanding-window training
over baseline features. 39 total tests (17 ML, 10 composite, 18 baseline, 11 null) pass. ruff, mypy, governance all clean.

## Governing documents

- tickets/ML-001.md (IN_PROGRESS)
- src/cryptofactors/factors/ml.py
- tests/test_ml_factors.py
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr) — last pass

1. .venv/bin/python -m pytest tests/test_ml_factors.py -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/factors tests/test_ml_factors.py
3. .venv/bin/python -m mypy --no-incremental src/cryptofactors/factors tests/test_ml_factors.py
4. python3 scripts/check_repo_control.py
