# REVIEW-0176 - PORT-002 Perpetual Long/Short Portfolio Simulator

**Status:** ACCEPTED
**Reviewer:** Lead Quant
**Ticket:** PORT-002

## Findings

1. **Allocator Logic:** `LongShortRankAllocator` correctly divides target leverage equally among positive-scoring (long) and negative-scoring (short) assets. Edge cases like single assets are gracefully handled.
2. **Simulation Mechanics:** `PerpetualSimulator` correctly separates long and short return attribution, accurately computes turnover-based trading costs, and interfaces properly with the optional `funding_provider` to deduct/credit funding cashflows.
3. **Liquidation Check:** The maintenance margin breach logic (`loss >= max_allowed_loss`) is sound. When triggered, the portfolio is correctly marked as liquidated, `net_return` is floored at -1.0 (-100%), and active weights are zeroed out.
4. **Runner Integration:** `momts_runner.py` was successfully updated with `run_perpetual_experiment`, leveraging the new simulator to finally support the `EXP-2026-019/020` realistic mechanical requirements. 
5. **Gates:** 11 tests pass, types and linter are perfectly clean. 

## Decision

**ACCEPT.** `PORT-002` bridges the final mechanical gap required for the `MOM-TS-01` confirmatory experiments. The codebase is now fully capable of running realistic backtests simulating perpetual swaps with funding and liquidation mechanics.
