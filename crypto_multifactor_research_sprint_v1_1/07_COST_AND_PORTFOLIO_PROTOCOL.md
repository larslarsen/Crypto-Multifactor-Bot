# Cost and Portfolio Protocol

## 1. Economic objective

Research optimizes and evaluates **net** portfolio outcomes, not label accuracy.

A simple utility diagnostic is:

\[
U = \bar r_{net} - \frac{\gamma}{2}\sigma^2_{net}
\]

This is reported alongside return, drawdown, turnover, and capacity rather than used to conceal them in one score.

## 2. Cost components

For each order, estimate:

- exchange fee;
- half-spread;
- market impact;
- latency/staleness;
- funding or borrow;
- conversion/quote-currency cost;
- liquidation or forced-exit cost;
- venue/default haircut, where modeled.

All components are recorded separately.

## 3. Cost hierarchy

1. observed trade/order-book estimate aligned to the order time;
2. venue- and liquidity-tier empirical model;
3. conservative fallback floor.

The fallback is not evidence that costs are known.

## 4. Baseline sensitivity schedule

Until empirical calibration is complete, report every strategy under:

- low: 0.5x baseline estimated cost;
- base: 1.0x;
- high: 2.0x.

A candidate that succeeds only under the low-cost case does not advance.

## 5. Execution timing

Signals formed from a closed bar cannot trade at that bar's pre-close price.

Primary assumptions:

- signal at the fixed decision timestamp;
- order begins after all features are available;
- fill uses the next executable quote/bar with slippage;
- no same-bar high/low clairvoyance;
- dual-touch stops/targets use conservative or higher-frequency resolution.

## 6. Capacity

For every position, calculate:

- order notional;
- fraction of trailing median daily quote volume;
- fraction of observed depth, if available;
- liquidation days;
- concentration by venue and asset.

Primary portfolio caps are set before results and tightened for lower-liquidity universes.

## 7. Portfolio baselines

### P0 — Equal-weight universe

Long all eligible assets equally. This separates selection value from broad crypto beta.

### P1 — Single-factor sort

Top and bottom quantile portfolios as defined in the factor specification.

### P2 — Equal-factor composite

Equal family scores; equal-weight or rank-proportional positions.

### P3 — Volatility-scaled factor composite

Scale accepted factor-family contributions by lagged volatility.

### P4 — Regularized prediction

Use regularized expected-return forecasts with transparent constraints.

## 8. Market-neutral constraints

- dollar-neutral target;
- bounded crypto-market beta;
- balanced long and short gross;
- per-asset cap;
- per-venue cap;
- liquidity participation cap;
- shortability required at the decision time;
- funding booked explicitly.

Exact neutrality may be relaxed only through a documented solver tolerance.

## 9. Long-only constraints

- no implicit cash redistribution into ineligible names;
- per-asset and per-venue caps;
- optional cash position;
- turnover buffer;
- benchmark-relative exposure reported.

## 10. Turnover mitigation

The first cost-control method is a no-trade/buffer region:

- an incumbent holding remains until its rank crosses a wider exit threshold;
- a new asset enters only after crossing a stricter entry threshold.

Buffer widths are preregistered or chosen inside training. They are not tuned on final results.

## 11. Risk estimation

Start with:

- sample volatility with sensible rolling windows;
- shrinkage covariance;
- market-beta constraints;
- simple factor exposure limits.

Do not begin with a highly parameterized optimizer. Equal weight is a required benchmark because estimation error can overwhelm theoretical optimization gains.

## 12. Stress tests

- doubled spread/impact;
- delayed execution;
- missing venue;
- top asset unavailable;
- funding spike;
- forced delisting;
- exchange price dislocation;
- market gap;
- stale or zero volume;
- partial fill.

## 13. Rejection rules

Reject an implementation when:

- net return is nonpositive at base costs;
- performance collapses at 2x costs;
- capacity is trivial;
- P&L depends on unshortable assets;
- funding accounting reverses the result;
- a same-bar fill assumption is necessary;
- one venue or asset dominates.
