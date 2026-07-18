# Matched Replication Protocol — Volume / Information Bars

## 1. Legacy claim under test

The legacy repository reports substantially higher classification accuracy for information/volume bars than time bars across many assets.

This sprint does not accept or reject that empirical result because the local data and result artifacts were unavailable. It specifies a test that isolates the bar representation.

## 2. Scientific question

Does a volume-clock representation add out-of-sample net economic information beyond a time-clock representation when both models:

- decide at matched timestamps;
- receive equivalent historical information;
- predict the same future economic outcome;
- have the same decision budget;
- trade under the same cost and portfolio rules?

## 3. Null

After matching timestamps, targets, model capacity, decisions, and costs, volume-clock features do not improve net portfolio performance over time-clock features.

## 4. Test A — Matched timestamp representation test

1. Build volume bars using only trades available before each bar close.
2. For every completed volume bar, record its close timestamp.
3. At that exact timestamp, construct:
   - features from the volume-bar history;
   - features from time bars using only data available by the same timestamp.
4. Assign an identical wall-clock target, such as next 24-hour or 7-day return.
5. Use the same universe and samples.
6. Fit models with the same capacity and nested splits.
7. Compare IC, calibration, and costed portfolio returns on paired timestamps.

This isolates representation from sample count and target horizon.

## 5. Test B — Equal decision-budget strategy test

Compare event-driven strategies with:

- the same maximum decisions per asset per day;
- the same maximum turnover;
- the same position duration policy;
- the same gross exposure;
- identical execution and cost model.

If the volume strategy naturally creates more events, subsample or budget decisions according to a rule fixed before results.

## 6. Test C — Null timing controls

Repeat volume-bar construction with controls:

- shuffled historical volume sequence within suitable blocks;
- alternative volume thresholds fixed from training;
- equal-dollar versus equal-trade-count bars;
- venue-specific and consolidated bars.

The goal is to determine whether any gain comes from information timing, volatility conditioning, or merely changing the sample distribution.

## 7. Label controls

- use forward returns defined in wall-clock time;
- separately report event-clock targets;
- do not compare accuracies across different class balances as the primary statistic;
- resolve intrabar barrier ambiguity conservatively;
- purge by event end time.

## 8. Portfolio controls

Report:

- gross and net return;
- turnover;
- number of decisions;
- average wall-clock holding period;
- spread/impact at event times;
- exposure by volatility and volume regime;
- capacity.

## 9. Inference

Use date-block bootstrap of paired strategy-return differences. Asset-level sign tests are supplementary because assets share market shocks.

All thresholds and model variants enter the experiment census.

## 10. Promotion rule

Volume bars advance only if:

- paired net portfolio improvement is positive;
- confidence intervals are dependence-aware;
- the result survives base and 2x costs;
- it persists across venues and major periods;
- it is not explained solely by more decisions or a different target;
- a prospective holdout passes.

Until then, “volume bars are the edge” is replaced with “volume bars are an unconfirmed representation hypothesis.”

## 11. Corrections required after the post-sprint code review

The legacy evaluator and artifact trainer may not be reused as the validation engine. The replacement must satisfy all of the following.

### Fold-local representation construction

For each outer fold:

1. estimate the volume threshold from the outer-training interval only;
2. freeze that threshold for validation and test, or apply a separately preregistered causal rolling update using only past observations;
3. rebuild bars sequentially without consulting total future volume;
4. preserve the actual close timestamp and wall-clock duration of every bar;
5. train a new model only on that fold's training representation.

No full-history target such as `total_volume / desired_bar_count` may determine historical bar boundaries.

### Transformation-order parity

Raw observations → information bars → features → imputation/model pipeline must be identical in evaluation, artifact training, and serving. Aggregating precomputed time-bar technical indicators is a different treatment and must not stand in for the artifact pipeline.

### True venue replication

A venue-robustness treatment must use that venue's own raw timestamps, prices, and volume. Using one venue's OHLC/features with another venue's threshold is not an independent venue test.

### Streaming state contract

A deployable event-bar builder must persist and test:

- cumulative volume since the last close;
- partial OHLCV state;
- threshold version and effective time;
- duplicate/out-of-order trade handling;
- late corrections;
- restart determinism;
- maximum wall-clock bar age;
- exact model/representation compatibility.

### Complete outcome reporting

Report total observations, class rates, prediction rates for every class, flat coverage, IC/calibration, gross and net P&L, turnover, holding times, and capacity. Conditional accuracy after removing flat predictions is diagnostic only.

### Sample-size gate

The minimum training requirement must be justified against feature dimension and model capacity. A 113-feature, 200-tree model trained on hundreds of observations is not eligible for promotion without strong regularization and independent stability evidence.
