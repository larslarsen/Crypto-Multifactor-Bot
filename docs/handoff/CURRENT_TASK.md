# CURRENT_TASK

Ticket: COMP-001
State: IN_PROGRESS
Next required actor: Sr Dev (Grok 0.1)
Next ticket authorized: NONE

COMP-001 round 2 rejected (REVIEW-0163). Production fixes correct. One test fix remaining.

## Sr Dev Prompt

```
COMP-001 round 3 fixup (1 item):

Fix tautological rank assertion in test_composite_factors.py:244-247

The current assertion uses max(scores) both to pick top_iid and to
assert. Instead, identify the best instrument by lowest raw_value:

    scores = {v.instrument_id: v.score for v in frame.values}
    raws = {v.instrument_id: v.raw_value for v in frame.values}
    best = min(raws, key=raws.__getitem__)
    assert scores[best] == max(scores.values())

After: run tests, stop for reviewer.
```

Governing documents:
- docs/reviews/REVIEW-0163_COMP-001_REJECTED.md
- tickets/COMP-001.md (IN_PROGRESS)

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/test_composite_factors.py -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/factors tests/test_composite_factors.py
3. python3 scripts/check_repo_control.py
