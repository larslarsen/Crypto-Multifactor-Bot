# Validation, Capacity, and Regime Protocol Addendum

## Estimand-specific inference

Every experiment preregistration names one primary estimand and one primary inference path.

| Estimand | Primary inference | Required disclosure |
|---|---|---|
| Costed portfolio path | Date-level stationary/block bootstrap | Decision dates, independent rebalances, block algorithm/length, repetitions, seed policy |
| Factor-return time series | HAC/Newey-West | Lag fixed from label/rebalance overlap before results; sensitivity lags reported |
| Panel slope or incremental IC | Two-way date x asset clustering where cluster counts are adequate | Date clusters, asset clusters, coefficient definition, fallback declared before execution |
| Strategy/model family | SPA/reality-check style bootstrap | Complete variant census and benchmark |

The bootstrap block rule is fitted or fixed using training/development data only and stored in
the experiment config. Politis-White is permitted after a tested implementation exists; it is
not a magic default. Applying several estimators to the same outcome does not create
independent replications.

Confirmatory hypotheses retain Holm family-wise control unless a reviewed preregistration
names another validated procedure. All lookbacks, exposure variants, universes, thresholds,
and regime cells count in the trial census.

## Economic threshold

Before execution, each experiment freezes:

- target capital;
- primary net economic estimand;
- minimum economically material effect;
- confidence level and interval construction;
- rejection and advancement rule.

Advancement requires the dependence-aware lower confidence bound to exceed the preregistered
minimum effect after base costs at target capital. A lower bound merely above zero is not, by
itself, economically material. No universal target Sharpe is introduced.

## Capacity

After the cost model is calibrated, report:

- 0.25x, 0.5x, 1x, and 2x preregistered target capital;
- participation, depth usage, liquidation days, and venue/asset concentration;
- gross and net performance at each cell;
- break-even capacity under the approved impact model;
- the existing 0.5x/1x/2x cost sensitivities.

Dollar AUM examples may be shown but do not replace target-relative curves. Square-root impact
is a sensitivity model until calibrated to approved crypto observations.

## Regime reporting

The existing major-subperiod and bull/bear/high-volatility matrix remains governing. Sprint
004 adds the following optional-but-preregistered cells for confirmatory experiments:

- high/low broad-market realized volatility;
- high/low aggregate funding for derivative strategies;
- high/low market beta exposure;
- externally dated structural breaks known before outcome inspection.

State variables use only information available at the decision time. Quantile thresholds are
estimated fold-locally or frozen from a prior period. Regime cells initially diagnose
stability; they do not select models, signs, thresholds, or leverage. Ex-post worst periods
remain stress descriptions, not confirmatory regimes.

## Prospective holdout

Epoch B remains one sealed prospective holdout per declared research version. It is not
replaced by rolling opened windows. A new version after opening requires a new decision event,
counts prior exposure as contamination, and cannot reuse the opened period as pristine data.

## Record placement

Performance paths, confidence intervals, capacity curves, regime cells, cluster counts, and
block parameters belong in immutable experiment bundles. The Evidence Registry links to and
interprets those bundles; it does not duplicate them as a leaderboard.
