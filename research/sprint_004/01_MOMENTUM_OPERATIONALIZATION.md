# Momentum Operationalization

## Existing cross-sectional baseline

MOM-01 and H-001 remain unchanged. The canonical cross-sectional characteristics are
`mom_30_7` and `mom_90_7`, ranked across the eligible universe for a seven-day holding
horizon. EXP-2026-003 and EXP-2026-004 remain the primary cross-sectional experiments.

No Sprint 004 record renames MOM-01, silently replaces its formulas, or treats time-series
and cross-sectional momentum as one result.

## MOM-TS-01

MOM-TS-01 asks whether an asset's own lagged trend predicts its own next-period realizable
return. It is registered as H-012 and remains `UNTESTED`.

### Signals

- `tsmom_30_7 = log(P[t-7d] / P[t-30d])`
- `tsmom_90_7 = log(P[t-7d] / P[t-90d])`

These matched lookbacks isolate implementation style from lookback selection. Zero maps to a
flat position. Missing history remains missing, not flat.

### Mandatory implementation cells

- Spot long/cash: long positive trend, otherwise cash.
- Perpetual long/short: sign of trend only where point-in-time contract availability,
  shortability, funding, margin, and liquidation terms are known.
- Raw notional exposure.
- Volatility-managed exposure using only lagged, fold-local estimates.

All cells and both lookbacks count in the multiplicity family. No favorable cell may be
renamed the primary result after observation.

### Wealth path

- Weekly decisions at the charter's fixed UTC timestamp and seven-day primary horizon.
- Daily mark-to-market within each holding period.
- Actual funding cash flows at their event timestamps.
- Fees, spread, impact, borrow, and quote conversion recorded separately.
- Point-in-time margin rules and maintenance thresholds for derivative cells.
- Liquidation is an absorbing forced-exit event for that position until the next scheduled
  decision; terminal backtest return cannot revive a liquidated path.
- Long and short legs, liquidations, and asset-level concentration are reported separately.

### Advancement

MOM-TS-01 must beat the eligible-universe and matched simple-trend baselines net of costs,
remain positive under the preregistered economic threshold and dependence-aware interval,
and survive the prospective process without retuning. Literature alone cannot advance it.

## Joint momentum/carry

No joint experiment is registered. It becomes eligible for design only after a standalone
momentum implementation and the relevant CARRY-01 mechanism independently pass their data,
cost, and evidence gates. The later joint test must report standalone and incremental
attribution; a favorable combination cannot rescue a rejected component.
