# Literature Addendum — LIQ-01 (Liquidity)

**Card:** LIQ-01 (Sprint 001, unchanged dual role)
**Sprint:** 002 refresh
**Status:** retained as eligibility/cost input AND candidate predictor

## What Sprint 1 already specified

Liquidity as both a point-in-time eligibility/cost/capacity input and a separately evaluated
candidate return predictor; predictive role must survive after separating eligibility/cost
effects from alpha.

## What the new literature changes

- LIT-028 shows liquidity/risk/past-return interactions dominate; equal-weighted OOS Sharpe
  >1 but low liquidity dampens trading.
- LIT-029 shows liquidity proxies (turnover volatility, bid-ask spread) dominate factor
  selection and that costs narrow the exploitable set.

## What remains unchanged

Dual role retained. Liquidity is not demoted to a pure cost input; it remains a candidate
predictor to be tested on its own.

## Additional diagnostics (new)

Explicit decomposition: liquidity-alpha vs mechanical universe-selection vs cost effects.
Report under multiple cost levels (LIT-028, LIT-029).

## New data requirements

Point-in-time spreads/depth/impact per venue (DF-09); consistent liquidity definitions
across the sample (LIT-029 warns liquidity variables dominate and are unstable).

## Why it remains untested (in this project)

Literature refresh only. LIQ-01 stays `UNTESTED` (H-005) until a preregistered experiment
runs the alpha-vs-cost decomposition under Research→Paper gates.
