# PORT-001 — Costed Portfolio Simulation (Sequence #15)

**Priority:** P0
**Status:** ACCEPTED
**Dependencies:** SPLIT-001 (accepted), EXP-001 (accepted), DF-08 (universe survivorship authority)
**Layer:** portfolio
**Architecture:** implements step #15 (costed portfolio simulation); no ADR required

## Objective

Implement the `portfolio` domain. The portfolio domain consumes factor scores and explicit label events (or event intervals) and runs a costed portfolio simulation to evaluate net factor performance. This fills the missing Sequence #15 implementation gap necessary for full research evaluation and to unblock Explicit Paper Promotion (Sequence #23).

## Required Contract

- **Input:** Factor frame/scores, decision times, purged chronological split folds, and cost configuration (slippage, fee rate).
- **Behavior:**
  - Evaluates cross-sectional factor scores at each decision time.
  - Generates target positions (e.g., long top decile, short bottom decile, or proportional).
  - Simulates portfolio returns over the target label horizons.
  - Applies transaction costs based on turnover and the cost model.
- **Output:**
  - Portfolio performance metrics (e.g., net return, Sharpe ratio, turnover).
  - Explicit portfolio and cost-model versions for lineage tracking.

## Deliverables

- `src/cryptofactors/portfolio/simulation.py` (or similar location)
- `tests/portfolio/test_simulation.py`
- Ticket + governance
- Tests + gates (Jr)

## Out of Scope

- Live execution routing or paper trading execution.
- Complex nonlinear optimization (keep the allocator simple: equal weight top/bottom or rank-weighted).
- Market depth / order book impact modeling (use flat basis point cost for now).

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/portfolio/ -q --tb=short` 
2. `.venv/bin/python -m ruff check src/cryptofactors/portfolio tests/portfolio`
3. `.venv/bin/python -m mypy --no-incremental src/cryptofactors/portfolio tests/portfolio`
4. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Grok): portfolio simulation logic and production source. Stop for reviewer.
- Jr Dev (Hermes): tests, gates, records, Git, commit, push after approval.

## Stop Condition

After Sr: AWAITING_REVIEW, Reviewer next, NONE.
