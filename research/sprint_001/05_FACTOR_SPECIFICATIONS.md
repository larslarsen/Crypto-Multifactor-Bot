# Factor Specifications

This file defines the factor ontology. The detailed cards are in `factor_cards/`.

## 1. Factor families and canonical IDs

| ID | Family | Phase | Main horizon | Initial role |
|---|---|---:|---:|---|
| MOM-01 | Medium-term momentum | 1 | 7d | Alpha |
| REV-01 | Short-term reversal | 1 | 1d | Alpha |
| DEF-01 | Defensive risk | 1 | 7d | Alpha + risk |
| CARRY-01 | Perpetual carry | 1 | 1d/7d | Alpha |
| LIQ-01 | Liquidity | 1 | 7d | Gate + candidate alpha |
| SIZE-01 | Market capitalization | 1 conditional | 7d | Alpha/control |
| NET-01 | Network/protocol activity | 2 | 7d–30d | Alpha |

The crypto market factor is a benchmark and risk exposure, not an alpha score.

## 2. What counts as a factor

A factor is an economically distinct characteristic family. Multiple lookbacks or technical transformations of the same price history are variants, not independent factors.

Examples:

- RSI, ROC, moving-average distance, and oscillator variants are not automatically four factors.
- Funding, basis, and staking yield may all be “carry,” but their cash-flow mechanisms differ and remain separate until spanning tests justify combination.
- Volume, spread, and price impact belong to liquidity/tradability, not independent factor counts by default.

## 3. Standard transformation

At each decision date:

1. enforce universe eligibility;
2. require the factor-specific minimum history;
3. winsorize at prespecified cross-sectional limits or use ranks;
4. robust-standardize within the date;
5. orient the score so larger means higher expected return;
6. retain a missing indicator;
7. neutralize only prespecified controls;
8. store raw and transformed values.

Primary implementation uses percentile ranks mapped to `[-1, 1]`, reducing sensitivity to crypto outliers.

## 4. Single-factor portfolio

For U50:

- top 20% long;
- bottom 20% short where eligible;
- equal weight within legs;
- dollar neutral for the market-neutral test;
- separate long-only top-quintile test;
- rebalance at the factor's declared horizon;
- apply position and liquidity caps before normalization.

When fewer than 20 assets are eligible, use terciles and label the result as a sparse-universe period.

## 5. Factor combination

### Baseline composite

Equal-weight the available canonical family scores:

\[
S_{i,t} = \frac{1}{K_{i,t}}\sum_k z_{i,t,k}
\]

A factor missing for an asset is not zero. The number of available families is recorded. A minimum family count is required.

### Volatility-scaled composite

Scale factor-family contributions by trailing factor-return volatility, estimated on the training window. No expected-return optimization.

### Regularized linear model

Predict cross-sectional future net return using elastic net or ridge. Hyperparameters are selected inside nested training/validation periods.

### Nonlinear model

A shallow tree ensemble may enter only after the linear and equal-factor baselines are frozen. Depth, estimators, and feature set are tightly bounded.

## 6. Incrementality tests

A factor advances only if it adds value beyond:

- the crypto market;
- momentum;
- size, when available;
- liquidity;
- the current accepted composite.

Report:

- cross-sectional regression slope;
- incremental IC;
- long-short alpha;
- change in net portfolio utility;
- correlation and spanning;
- turnover and capacity impact.

## 7. Prohibited practices

- selecting a factor's sign from the final holdout;
- treating zero-filled missing inputs as observations;
- retaining only the best lookback without counting all variants;
- using current market cap or listing status historically;
- declaring success from feature importance;
- promoting on gross accuracy;
- optimizing factor weights on the prospective holdout.
