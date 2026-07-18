# Factor Card MOM-01 — Medium-Term Momentum

**Status:** Preregistered  
**Family:** Price trend  
**Primary horizon:** 7 days  
**Expected sign:** Positive

## Economic hypothesis

Cryptoassets with stronger recent medium-term performance continue to outperform over the next week, after excluding the most recent short-reversal window.

## Canonical characteristics

- `mom_30_7 = log(P[t-7d] / P[t-30d])`
- `mom_90_7 = log(P[t-7d] / P[t-90d])`

Primary factor score:

1. robust cross-sectional z-score each characteristic;
2. average the two scores;
3. optionally residualize against market beta and log market cap when audited.

No indicator-derived substitutes are part of the primary test.

## Data

Audited consolidated close prices with availability at or before decision time.

## Portfolio test

Weekly top-minus-bottom quintile and long-only top quintile. Equal-weight is primary; liquidity-capped weighting is secondary.

## Diagnostics

- cross-sectional Spearman IC;
- quintile monotonicity;
- subperiod and venue stability;
- turnover;
- overlap with size and liquidity;
- crash behavior.

## Reject when

- net spread is nonpositive under baseline costs;
- result is concentrated in a few assets or one era;
- it vanishes after point-in-time universe reconstruction;
- sign is unstable without a prespecified explanation.
