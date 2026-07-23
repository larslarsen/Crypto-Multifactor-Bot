# REVIEW-0165 — ML-001 Accepted

**Ticket:** ML-001 (ML challengers, experiment #21)
**Previous:** (new ticket)
**Status:** ACCEPTED

## Review Outcome

Three ML factors (Ridge, ElasticNet, XGBoost) with expanding-window training
over baseline features. 17 tests. Gates: pytest, ruff, mypy, governance all clean.

### Integrity Checks

- **Lookahead bias:** PASS — `event_end <= decision_time` filter
- **Determinism:** PASS — fixed seeds, pinned `n_jobs=1` on XGBoost
- **Fail-soft:** PASS — `< 5` training samples returns empty FactorFrame
- **Contract:** PASS — all factors implement `Factor` protocol

## Gates

| Gate | Result |
|------|--------|
| pytest (17 tests) | PASS |
| ruff | PASS |
| mypy | PASS |
| check_repo_control.py | PASS |

## Next

Experiments #18–21 (null → baselines → composites → ML) complete.
Next requires architecture decision — serving phase (#22–24) or additional
research iteration. Stronger model needed for ticket selection.
