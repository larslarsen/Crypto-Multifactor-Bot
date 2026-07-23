# CURRENT_TASK

Ticket: COMP-001
State: IN_PROGRESS
Next required actor: Sr Dev (Grok 0.1)
Next ticket authorized: NONE

COMP-001 rejected (REVIEW-0162). Two P1 corrections required.

## Sr Dev Prompt

```
COMP-001 round 2 fixups (3 items):

1. Invert score direction in src/cryptofactors/factors/composite.py:170-176
   score must be higher-is-better (descending-sort convention for portfolio).
   Example: score = -avg_rank. raw_value can stay avg_rank.

2. Reject duplicate child factor_ids in constructor
   composite.py:102-120. Raise CompositeFactorError if any two children
   have the same factor_id.

3. Add assertion in test_composite_substrate_integration
   After factor.compute(), verify the instrument with the strongest baseline
   performance gets the highest composite score (assert scores are
   descending-sort-orderable).

After: run tests, stop for reviewer.
```

Governing documents:
- docs/reviews/REVIEW-0162_COMP-001_REJECTED.md
- tickets/COMP-001.md (IN_PROGRESS)

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/test_composite_factors.py -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/factors tests/test_composite_factors.py
3. .venv/bin/python -m mypy --no-incremental src/cryptofactors/factors tests/test_composite_factors.py
4. python3 scripts/check_repo_control.py
