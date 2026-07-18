# Post-Sprint Commit Review

## Review scope

This addendum reviews the legacy repository through:

- `581aed2` — information/volume-bar retraining support, Paper #2 v2 evaluator, and related research artifacts;
- `fb737ae` — committed information-bar model artifacts for 27 pairs.

Review date: 2026-07-18.  The review covers versioned source and artifacts, not the omitted raw training observations.

## Executive verdict

The junior engineer's three handoff caveats are accurate, but they understate the validation risk.

The commits are useful because they preserve implementation evidence and trained artifacts. They do **not** establish that information bars are a validated edge, and the committed information-bar models must not be deployed by merely changing the loaded filename.

The greenfield multifactor research direction remains unchanged. Information bars remain an isolated representation experiment governed by `08_VOLUME_BAR_REPLICATION_PROTOCOL.md`.

## Review of the handoff caveats

### 1. Research/serving mismatch — confirmed

`model_trainer.py` can now build information bars and writes `_info` model artifacts. The serving bot still constructs the ordinary five-minute feature stream and is configured around the standard time-bar model path.

This is more than a missing wiring step. A production information-bar model requires a causal streaming bar builder with:

- a threshold estimated only from past data;
- deterministic partial-bar state;
- exact close-time semantics;
- restart/recovery behavior;
- training/serving feature parity;
- explicit handling of delayed or corrected volume;
- a model-to-representation compatibility check.

Loading `latest_info_xgb.json` while retaining time-bar features would be invalid. Reconstructing historical bars with a full-sample threshold would also be invalid.

**Disposition:** quarantine all `_info` artifacts from serving discovery until EXP-2026-015 passes and a representation contract is frozen.

### 2. Small training folds — confirmed and material

The committed latest information model reports:

- 496 training bars;
- 5,000 validation bars;
- 14,976 test bars;
- 113 features;
- 200 trees;
- directional accuracy about 0.5664.

Other pairs have much larger training sets, so model estimation conditions vary substantially across assets. A large test set does not repair an unstable high-dimensional fit trained on 496 observations, nor does accuracy alone establish economic value.

Minimum diagnostics before any artifact is considered research-grade:

- exact train/validation/test date ranges;
- class counts and base rates;
- prediction coverage, including the omitted-flat share;
- probability calibration;
- per-fold predictions and returns;
- dataset and feature hashes;
- threshold provenance;
- turnover and costed portfolio outcomes;
- seed and software environment.

**Disposition:** model files are forensic artifacts, not promotion evidence.

### 3. Literature classification — confirmed

Karassavidis, Kateris, and Ioannidis propose a volatility-adaptive trend-following framework that is implementable with available OHLCV-style inputs. It is a recent working paper and should be treated as an exploratory challenger after the transparent momentum and defensive baselines—not as validation of the primary factor program.

Nguyen and Chan is a systematic mapping study. It is useful for taxonomy, literature coverage, and prioritizing replication candidates. It does not define a tradable strategy and must not receive an experiment row as though it were a model.

## Additional critical findings

### A. The Paper #2 v2 evaluator is not fold-specific walk-forward

The evaluator trains one XGBoost model on the first 80% of the complete sample. It then obtains nominal walk-forward test indices and evaluates that same model on every test slice.

For ordinary sample sizes, one or more nominal test slices can fall inside the data already used to fit the model. Even where a slice occurs later, the procedure is not a fold-by-fold walk-forward retraining design.

**Impact:** the reported values cannot be called out-of-sample walk-forward evidence.

### B. Information-bar thresholds use future sample volume

Both the evaluator and the artifact trainer derive the volume threshold from cumulative volume over the complete available sample, targeting approximately 60,000 bars.

That allows future total volume to determine historical bar boundaries. Adding later observations can revise the representation of earlier history.

**Impact:** the representation is non-causal and historically unstable.

### C. Evaluation and artifact training use different feature semantics

The evaluator first computes canonical features on time bars and then aggregates those existing feature columns into information bars using their last values. The artifact trainer constructs information bars first and then computes the canonical features on the resulting information-bar series.

These are different experiments. A result from the evaluator does not directly validate the committed artifact pipeline.

### D. The claimed second-venue treatment does not build bars from second-venue volume

The evaluator computes the alternate threshold from `blofin_volume`, but its information-bar grouping function always accumulates the column named `volume`. In the merged frame that remains the Binance volume column. The source also retains Binance OHLC and previously computed features.

**Impact:** this is not a true second-venue representation replication.

### E. Accuracy is conditional on non-flat predictions

The evaluator excludes predictions assigned to class 2 before computing directional accuracy. It does not jointly report prediction coverage, trade count, turnover, payoff magnitude, fees, spread, impact, or funding.

**Impact:** reported accuracies cannot establish a costed trading edge.

### F. Artifact auto-discovery has a namespace hazard

The serving model discovery glob matches all `*_xgb.json` files. The current explicit screener list prevents `_info` artifacts from being selected, but fallback auto-discovery can interpret filenames containing `_info` as symbols.

**Impact:** representation-incompatible models could enter discovery after a configuration failure or deployment change.

## Promotion decision

| Item | Decision |
|---|---|
| Commit source code | Preserve as legacy evidence |
| Committed `_info` artifacts | Preserve; do not deploy |
| “Edge holds universe-wide” claim | Rejected as unvalidated |
| Existing Paper #2 v2 metrics | Contaminated by evaluator defects |
| Volume/information-bar hypothesis | Retain for clean replication |
| Karassavidis trend model | Add as low-priority exploratory challenger |
| Nguyen mapping study | Add to literature taxonomy only |

## Required remediation before replication

1. Build bars causally inside each fold using thresholds learned only from the training history.
2. Train a fresh model for every fold.
3. Compute features after constructing the representation being tested.
4. Use true venue-specific raw observations for venue robustness.
5. Match decision timestamps, target horizon, capacity, turnover, and costs.
6. Report all predictions, including flat coverage and economic payoff.
7. Version dataset hashes, thresholds, dates, classes, predictions, and environment.
8. Keep serving disabled until streaming parity tests pass.

## Effect on Sprint 1

No binding factor, universe, validation, cost, or architecture decision is reversed. The addendum raises the priority of causal event-bar infrastructure and reinforces the decision not to let the legacy volume-bar claim shape the primary architecture.
