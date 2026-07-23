# CURRENT_TASK

Ticket: BASE-001
State: AWAITING_REVIEW
Next required actor: Reviewer (strong model)
Next ticket authorized: NONE

Round 4 rejected (REVIEW-0160). Two fixups required. The `_latest_market_bars`
change in `as_of.py` is authorized post-hoc (correct and necessary).

## Sr Dev Prompt

```
BASE-001 round 4 fixups (2 items):

1. Remove unused import in src/cryptofactors/catalog/as_of.py:22
   Delete the line: import pyarrow.compute as pc
   (ruff F401 — it's no longer used after the _latest_market_bars rewrite)

2. Update docs/adr/ADR-001_COMPLETED_BAR_WINDOW.md to document dual eligibility.
   Add a section explaining:
   - latest_available uses availability-only completed-bar access:
     availability_time <= t AND period_start <= t (NO period_end upper bound).
     A bar remains selectable after period_end once available.
   - as_of uses observation_eligible with closed [period_start, period_end]
     window (returns all bars in-window at decision_time).
   - Rationale: latest_available answers "latest available bar";
     as_of answers "what was true at t".

After: run ruff + mypy + tests. Stop for reviewer.
```

Governing documents:
- docs/reviews/REVIEW-0160_BASE-001_REJECTED.md
- docs/adr/ADR-001_COMPLETED_BAR_WINDOW.md (needs update)

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/test_baseline_factors.py tests/catalog/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/catalog/as_of.py
3. .venv/bin/python -m mypy --no-incremental src/cryptofactors/catalog/as_of.py
4. python3 scripts/check_repo_control.py