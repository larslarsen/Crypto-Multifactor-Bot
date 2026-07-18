# Validation Protocol

## 1. Contamination declaration

Historical data through 2026-07-17 has been exposed to extensive prior experimentation in the legacy project. Even when the new definitions differ, it cannot serve as a pristine final holdout.

Therefore:

- historical walk-forward results are **developmental/pseudo-OOS**;
- the first production-strength claim requires prospective data after the research freeze;
- prior tried variants count toward qualitative skepticism and the experiment census.

## 2. Research epochs

### Epoch A — Historical reconstruction

All audited data ending on or before 2026-07-17.

Purpose:

- repair data;
- test factor construction;
- estimate costs;
- reject weak hypotheses;
- compare simple baselines.

It may generate research conclusions, but not an untouched-final-test claim.

### Epoch B — Prospective sealed holdout

Begins 2026-07-18 00:00 UTC.

Before opening it, freeze:

- universe rules;
- factor formulas;
- rebalance schedule;
- cost model;
- portfolio construction;
- model class and hyperparameters;
- all acceptance metrics.

The holdout remains sealed for a minimum declared duration and number of independent rebalances.

## 3. Historical nested evaluation

Use anchored or rolling chronological folds.

For each outer fold:

1. training window;
2. inner validation window for permitted choices;
3. outer test window;
4. no test feedback into the current research version.

All preprocessing, imputation, scaling, neutralization, and hyperparameter selection is fitted inside training.

## 4. Correct event-time purging

Each sample has `[event_start, event_end]`.

Before evaluating a later partition, remove any earlier sample whose `event_end` overlaps the start of the later partition.

For a split boundary `T`:

- training samples require `event_end < T_validation_start`;
- validation samples require `event_end < T_test_start`;
- optional embargo begins after each test event to prevent immediate reuse when features or labels overlap.

Deleting rows from the beginning of the test set is not a substitute.

## 5. Cross-sectional dependence

Cryptoasset observations on the same date share market shocks. Asset-level rows are not independent.

Use:

- date-level block or stationary bootstrap for portfolio metrics;
- HAC/Newey-West errors for factor-return time series;
- two-way clustering by date and asset for suitable panel regressions;
- date-level permutation only where exchangeability is defensible.

Per-asset sign tests may be reported as diagnostics, not as the sole inference.

## 6. Multiple testing

Every tried factor definition, lookback, threshold, universe, model, and portfolio rule is logged.

### Confirmatory family

Primary hypotheses declared in the registry receive family-wise control using Holm or a prespecified joint procedure.

### Model search

When comparing many strategy variants, use a Superior Predictive Ability/reality-check style test or an equivalent bootstrap procedure.

### Research hurdle

A production candidate should generally clear:

- economically material net performance;
- a dependence-aware confidence interval excluding a nonpositive effect;
- a t-statistic near or above the stricter factor-research hurdle, where applicable;
- the prospective holdout without retuning.

The hurdle is not reduced because crypto observations are numerous.

## 7. Primary metrics

### Prediction diagnostics

- Spearman information coefficient;
- IC mean and stability;
- cross-sectional \(R^2\);
- quantile monotonicity;
- calibration, when probabilistic.

### Portfolio outcomes

- net arithmetic and geometric return;
- annualized volatility;
- Sharpe and Sortino;
- maximum drawdown;
- Calmar;
- turnover;
- gross and net exposure;
- beta;
- funding and fee contribution;
- capacity;
- tail loss and expected shortfall;
- number of assets and concentration.

Accuracy and ROC-AUC are secondary diagnostics only.

## 8. Primary comparisons

Each candidate is compared with:

- equal-weight eligible universe;
- market-only benchmark;
- its own single-factor baseline;
- equal-factor composite;
- regularized linear composite;
- no-trade/cash where appropriate.

## 9. Robustness matrix

Report, without selecting only favorable cells:

- U25/U50/U100;
- single-venue/multi-venue;
- long-only/market-neutral;
- 0.5x/1x/2x baseline costs;
- equal weight/liquidity capped;
- major subperiods;
- bull/bear/high-volatility periods;
- exclusion of the largest assets;
- exclusion of the smallest eligible tier;
- alternative but prespecified bar source.

## 10. Advancement gate

A factor advances to the composite when:

- primary sign is correct;
- net effect is positive and economically material;
- at least three major subperiods do not contradict it;
- no single asset contributes more than a declared fraction of cumulative P&L;
- capacity is adequate for the target capital;
- it is incremental to accepted factors;
- its multiple-testing-adjusted evidence passes;
- results and code reproduce from an immutable manifest.

## 11. Model advancement

ML advances only if, net of all costs:

- it beats equal-factor and regularized-linear baselines;
- improvement is stable across outer folds;
- complexity-adjusted evidence is positive;
- feature ablations are coherent;
- the prospective holdout passes without model redesign.

## 12. Reporting failures

A failed candidate remains in the registry with:

- exact configuration;
- metrics;
- rejection reason;
- plots/tables;
- dataset hashes;
- links to logs.

No failed row is deleted or renamed to hide the trial count.
