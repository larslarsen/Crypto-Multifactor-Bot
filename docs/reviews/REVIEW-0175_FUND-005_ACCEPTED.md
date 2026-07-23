# REVIEW-0175 - FUND-005 BitMEX Funding Cashflow Provider

**Status:** ACCEPTED
**Reviewer:** Lead Quant
**Ticket:** FUND-005

## Findings

1. **Ingestion Logic:** The `BitMEXFundingClient` correctly implements the `GET /funding` pagination protocol. It respects the 180 requests/min rate limit and normalizes the payload into the expected `BITMEX_FUNDING_SCHEMA`.
2. **Interval Transition:** The daily (pre-June 2016) to 8-hour transition is handled transparently as the provider simply applies rates at whatever timestamps they occur.
3. **Cashflow Semantics:** The `BitMEXFundingProvider` correctly computes the USD funding cashflow impact for both linear and inverse contracts. The inverse contract math correctly reflects that position size in contracts equals USD notional, yielding a BTC cashflow that is then converted back to USD at the point-in-time price. This aligns perfectly with the USD-denominated `PortfolioSimulator`.
4. **Gates:** `pytest` (6 tests), `ruff`, `mypy`, and `check_repo_control.py` all pass.

## Decision

**ACCEPT.** The funding provider resolves Step #10 of the implementation sequence for funding/fees/FX.

The BitMEX funding data is now ready for use in simulation. The next logical step is to integrate this `BitMEXFundingProvider` into our `PortfolioSimulator` so that perpetual long/short strategies (like the follow-on to MOM-TS-01) properly incur funding costs.
