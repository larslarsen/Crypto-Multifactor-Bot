# Factor Card MOM-TS-01 - Time-Series Momentum

**Status:** Registered / untested / blocked by research substrate and execution realism
**Hypothesis:** H-012
**Family:** Own-asset price trend
**Primary horizon:** 7 days
**Expected sign:** Positive to own lagged trend

## Canonical characteristics

- `tsmom_30_7 = log(P[t-7d] / P[t-30d])`
- `tsmom_90_7 = log(P[t-7d] / P[t-90d])`

MOM-TS-01 is not a cross-sectional rank and does not replace MOM-01. Lookbacks are separate
registered experiments. Missing history is missing; an exactly zero signal is flat.

## Portfolio cells

- spot long/cash;
- point-in-time shortable perpetual long/short;
- raw exposure;
- lagged fold-local volatility-managed exposure.

Equal notional with approved liquidity, asset, and venue caps is the initial portfolio. No
cell is selected after observing results.

## Required accounting

Daily mark-to-market, actual funding events, fees, spread/impact, borrow, margin terms,
liquidation thresholds, forced-exit costs, and quote conversion. Liquidated positions cannot
receive terminal returns they could not realize.

## Required reports

- spot/perpetual and long/short legs;
- raw/volatility-managed paths;
- liquidation count and loss attribution;
- large/liquid and full eligible subsets;
- asset and venue concentration;
- turnover, capacity curve, break-even capacity, and cost sensitivities;
- comparison with cross-sectional MOM-01 without combining verdicts.

## Rejection

Reject if net realizable performance is nonpositive at the preregistered threshold, depends
on terminal-only accounting, vanishes with actual funding/liquidation mechanics, is confined
to one asset/venue/era, or fails incrementality and multiplicity controls.
