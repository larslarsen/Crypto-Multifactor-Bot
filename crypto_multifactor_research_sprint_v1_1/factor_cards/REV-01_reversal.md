# Factor Card REV-01 — Short-Term Reversal

**Status:** Preregistered  
**Family:** Price pressure/reversal  
**Primary horizon:** 1 day  
**Expected sign:** Negative relation between recent return and next return

## Canonical characteristics

- `rev_1 = -log(P[t] / P[t-1d])`
- `rev_3 = -log(P[t] / P[t-3d])`

Primary score is the equal average of date-wise robust z-scores.

## Conditional diagnostic

Test whether reversal is stronger after an abnormal-volume or price-impact shock. This interaction is secondary and counts as a separate experiment.

## Implementation concern

This is expected to have high turnover. It cannot advance on gross returns.

## Reject when

- the signal does not survive two-times baseline cost;
- profitability comes only from illiquid assets;
- entries require unavailable within-bar prices;
- capacity is negligible.
