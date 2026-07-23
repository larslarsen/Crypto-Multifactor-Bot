# PORT-002 — Perpetual Long/Short Portfolio Simulator

**Priority:** P0
**Status:** READY
**Dependencies:** PORT-001 (ACCEPTED), FUND-005 (ACCEPTED)
**Layer:** portfolio
**Architecture:** Extends the portfolio domain to support perpetual contracts, funding costs, and liquidations.

## Objective

Extend the historical backtest portfolio simulator to support perpetual long/short allocations with realistic mechanics. This is required to execute `EXP-2026-019` and `EXP-2026-020` strictly according to their preregistered metrics: "liquidations; long/short attribution" and "point-in-time shortable perpetual cells".

## Scope

- **Perpetual Simulation Engine (`PerpetualSimulator`):** A simulator that maintains a margin account (in USD).
- **Funding Costs:** Integrate `BitMEXFundingProvider` (FUND-005) to deduct or credit funding cashflows to the margin account at each decision interval.
- **Liquidations:** Implement a margin fraction check. If the portfolio leverage exceeds a specified threshold (e.g., initial margin requirement), force a liquidation (wipeout or partial close).
- **L/S Allocator:** Implement a `LongShortRankAllocator` that allocates a percentage of capital to the top N (long) and bottom N (short).
- **Runner Update:** Update `momts_runner.py` to use the `PerpetualSimulator` with long/short allocation and BitMEX funding for `EXP-2026-019/020`.

## Deliverables

- `src/cryptofactors/portfolio/perpetual_simulation.py` (or update `simulation.py`)
- `tests/portfolio/test_perpetual_simulation.py`
- Updates to `momts_runner.py`

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/portfolio/ tests/experiments/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/portfolio src/cryptofactors/experiments`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/portfolio src/cryptofactors/experiments`
4. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Strong Model): production source and runner update.
- Jr Dev (Weak Model): tests, git commit.

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
