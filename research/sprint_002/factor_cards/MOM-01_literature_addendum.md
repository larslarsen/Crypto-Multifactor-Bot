# Literature Addendum — MOM-01 (Medium-Term Momentum)

**Card:** MOM-01 (Sprint 001, unchanged primary test)
**Sprint:** 002 refresh
**Status:** retained; reporting expanded; CTREND/vol-managed are later challengers

## What Sprint 1 already specified

Weekly medium-term cross-sectional momentum (`mom_30_7`, `mom_90_7`), equal-weight primary,
liquidity-capped secondary, with diagnostics for IC, monotonicity, subperiod/venue
stability, turnover, overlap, and crash behavior. Long-only and winner-minus-loser.

## What the new literature changes

- Crypto momentum is short-horizon and leg/liquidity dependent (LIT-025, LIT-028).
- CTREND (LIT-024) is a validated price-volume trend factor but is ML-aggregated — a later
  challenger, not the baseline.
- Volatility-managed momentum raises Sharpe in crypto, but LIT-026 (no extended crashes,
  gains from returns) and LIT-027 (severe crashes in large-cap equal-weighted) disagree on
  crash risk.

## What remains unchanged

Primary simple momentum test and its canonical characteristics are retained. No substitution
by CTREND or volatility scaling as the primary.

## Additional diagnostics (new)

Require separate reporting for: time-series vs cross-sectional; long-leg vs short-leg;
large/liquid vs smaller; spot long-only vs realistically shortable perpetual; raw vs
volatility-managed exposure; ordinary vs margin/liquidation-aware wealth paths; asset-level
concentration and crash attribution (RD-01).

## New data requirements

Realistically shortable perpetual implementations need point-in-time margin/liquidation terms
(DF-06). Crash attribution needs per-asset return paths, not just portfolio series.

## Why it remains untested (in this project)

Sprint 002 is a literature refresh; no empirical run was performed. MOM-01 stays
`UNTESTED` in the Evidence Registry (H-001) until a preregistered experiment on audited data
is run under the Research→Paper gates (ADR-0008).
