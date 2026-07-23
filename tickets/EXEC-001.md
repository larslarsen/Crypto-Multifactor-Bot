# EXEC-001 — Paper Execution Runtime (Sequence #25)

**Priority:** P1
**Status:** AWAITING_REVIEW
**Dependencies:** PROMO-001 (Promotion Registry), PORT-001 (Costed Simulation)
**Layer:** execution
**Architecture:** Implements step #25 (Paper Execution Runtime). No ADR required as it follows the existing execution architecture separation.

## Objective

Implement the Paper Execution Runtime. This component acts as a simulated broker for models that have reached the `PAPER_APPROVED` state. While `PORT-001` provides historical backtest simulation, `EXEC-001` provides a forward-walking position manager that tracks paper trading equity, fills orders with applied slippage/fees, and ensures strict gating (only running models officially approved for paper).

## Scope

- **PaperBroker:** Maintain account state (cash balance, open positions) and track paper equity.
- **Order Routing:** Accept target weight vectors (or market orders) from an active allocator and compute required trades.
- **Fill Simulation:** Execute simulated fills using point-in-time price data, applying `CostConfig` (fee_bps, slippage_bps).
- **Promotion Gate:** The runtime *must* query the `PromotionRegistry` (from PROMO-001) and strictly refuse to execute or track paper positions for any `model_artifact_id` that is not currently in the `PAPER_APPROVED` state.

## Required Contract

- The runtime consumes a `PAPER_APPROVED` artifact and a live/forward data stream (or out-of-sample holdout stream).
- It maintains state across sequential ticks (unlike the cross-sectional simulator).
- `get_positions()` and `get_equity()` methods accurately reflect simulated costs.

## Out of Scope

- Live exchange API connections, real keys, or live routing (reserved for Sequence #26).
- Intraday order book microstructure matching (use simple slippage models).
- Complex order types (Limit, Stop, TWAP/VWAP) - Market orders for flat rebalancing are sufficient for MVP.

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution tests/execution`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution tests/execution`
4. `python3 scripts/check_repo_control.py`
5. Test asserting `PaperBroker` raises an explicit error if asked to run an artifact not in `PAPER_APPROVED` state.

## Phased Ownership

- Sr Dev (Strong Model): logic and production source. Stop for reviewer.
- Jr Dev (Weak Model): tests, gates, records, Git, commit, push after approval.

## Stop Condition

After Sr Dev implementation: Set state to AWAITING_REVIEW, wait for Lead Quant review, Next ticket authorized: NONE.
