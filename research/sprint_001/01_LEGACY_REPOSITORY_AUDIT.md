# Legacy Repository Audit

## Scope

Repository: https://github.com/larslarsen/Trading-Bot  
Initial snapshot inspected: 2026-07-17  
Post-sprint review: 2026-07-18, through commits `581aed2` and `fb737ae`  
Audit type: public-code, documentation, and committed-model-artifact review; no access to omitted raw training observations.

## Executive conclusion

The repository contains substantial collection, reliability, and simulation work, but it does not yet provide a trustworthy research lineage for a new multifactor model.

It currently mixes at least three different identities:

1. a five-minute per-pair XGBoost paper trader described in the README;
2. a pooled daily XGBoost effort described in `RESEARCH_SUMMARY.md`;
3. a daily regime-based long-only rule system described as the production focus in `ROADMAP.md`.

This ambiguity is not cosmetic. It prevents a reader from knowing which research question, universe, target, cost model, and validation standard govern the current system.

The new initiative should not refactor this design in place. It should transplant only audited components.

## Evidence boundary

### Verified from the public repository

- The README describes a 5-minute multi-pair XGBoost system and a frozen 113-feature contract.
- `ROADMAP.md` describes a daily regime-rule system as the production focus.
- `RESEARCH_SUMMARY.md` reports a daily pooled XGBoost model and numerous newer experiments.
- Raw data, generated CSV/Parquet files, and broad classes of experiment outputs are ignored by Git. Commit `fb737ae` now versions information-bar model artifacts, but not their raw training observations or complete prediction lineage.
- `pipeline.py` implements triple-barrier labels and a walk-forward split.
- `quality_gate.py` computes eligibility from full-file history and liquidity.
- `canonical_features.py` enforces a fixed feature contract and zero-fills absent columns.
- The repository includes many one-off indicator, regime, and comparison scripts.
- The repository acknowledges that an earlier order-flow result was void because the relevant columns contained no observations.
- The repository reports a large volume-bar advantage, but the underlying local results were not available for independent reproduction.

### Not verified

- the reported count, row count, date span, and integrity of local data files;
- the reproducibility of any performance table;
- independent reproduction of the committed information-bar model artifacts from raw inputs;
- exchange fee schedules and realized fills;
- point-in-time market-cap, listing, delisting, or shortability histories;
- whether all live features are identical to research features for every path;
- whether experiments omitted from Git materially changed the selection process.

## Findings

### L-001 — Incorrect split-boundary purge  
**Severity: Critical**

The walk-forward function leaves training directly adjacent to validation and validation directly adjacent to test. Its variable called `purge` instead removes observations from the beginning of the test set.

For forward-looking or overlapping labels, correct purging removes training/validation observations whose label intervals overlap the next partition. The current placement does not establish that separation.

**Consequence:** reported validation statistics must be re-established.

**Action:** split using each sample's `event_start` and `event_end`; purge any earlier sample whose `event_end` reaches the next partition.

### L-002 — Intrabar triple-barrier ambiguity  
**Severity: Critical**

The OHLC label routine checks the profit barrier before the loss barrier. If both are touched inside the same bar, the within-bar path is unknown, yet the favorable barrier receives precedence.

**Consequence:** labels can be optimistically biased, particularly on coarse or volatility-scaled bars.

**Action:** mark dual-touch bars ambiguous and drop them, use conservative loss-first resolution, or label from higher-frequency paths. The choice must be preregistered.

### L-003 — Universe selection is not point in time  
**Severity: Critical**

The CEX quality gate uses:

- the complete file's first and last timestamps;
- average quote volume over the complete history;
- liquidity measured relative to the file's latest timestamp;
- a manually maintained current delisting list.

That may be suitable for selecting assets today, but not for reconstructing what was investable on each historical date.

**Consequence:** historical backtests can inherit look-ahead and survivorship bias.

**Action:** generate dated membership snapshots using only trailing data available at each decision date.

### L-004 — Public research provenance is incomplete  
**Severity: High**

The `.gitignore` excludes raw data, tabular results, model objects, broad experiment-script patterns, sweeps, comparisons, and sensitivity files.

**Consequence:** the public repository cannot reproduce the claimed empirical path or count all tried configurations.

**Action:** keep raw data external, but version immutable manifests, schemas, checksums, environment locks, experiment configs, metrics, and result hashes.

### L-005 — Missingness is conflated with a numeric zero  
**Severity: High**

The canonical feature contract fills absent columns with zero. For optional funding, order flow, DEX, macro, and cross-asset inputs, zero can be a genuine observation.

**Consequence:** a model cannot distinguish “no data,” “not applicable,” “source failed,” and “observed zero.”

**Action:** preserve nulls through the research layer and add explicit availability/missingness indicators. Imputation belongs inside the fitted pipeline.

### L-006 — Researcher degrees of freedom are large  
**Severity: High**

The repository contains many indicator, regime, threshold, sizing, slicing, and feature experiments. Its own notes show that a result reversed after changing slice granularity.

**Consequence:** isolated p-values and paired sign tests understate selection risk.

**Action:** reconstruct an experiment census, classify previous results as contaminated, and use a locked prospective holdout.

### L-007 — Prediction metrics dominate the research frame  
**Severity: High**

Several research paths promote models using accuracy, ROC-AUC, and sign tests over per-asset accuracy differences.

**Consequence:** the system can prefer a statistically predictable label that is untradeable, asymmetric, too costly, or economically small.

**Action:** promote only on net portfolio utility and risk, with predictive metrics retained as diagnostics.

### L-008 — Volume-bar comparison is not economically matched  
**Severity: High**

The reported comparison changes the sampling clock and may therefore change event count, event duration, class balance, horizon, overlap, volatility, and turnover.

**Consequence:** a large accuracy difference does not isolate a representation effect.

**Action:** run the matched-timestamp replication in `08_VOLUME_BAR_REPLICATION_PROTOCOL.md`.

### L-009 — Data manifest is inventory-level, not provenance-level  
**Severity: Medium**

The manifest records source, venue, timeframe, symbol, rows, dates, and path. It does not appear to record checksums, schema versions, fetch windows, duplicate rates, gaps, corrections, or first-availability semantics.

**Action:** replace it with the contract in `03_POINT_IN_TIME_DATA_CONTRACT.md`.

### L-010 — Root-level experiment sprawl  
**Severity: Medium**

Collection, features, labels, models, live trading, simulation, and one-off research scripts coexist at the root.

**Consequence:** accidental imports and inconsistent research paths become more likely.

**Action:** do not reorganize the old repository. Establish clear domains in a new repository.

### L-011 — Research and live operation share assumptions too early  
**Severity: Medium**

The same feature and engine concepts are reused across training and serving, which is good operationally, but research claims can become tied to live-oriented defaults and compatibility behavior.

**Action:** separate raw research semantics from serving transformations. A production contract is generated only after a research version is frozen.

## Positive assets

The following are worth preserving conceptually or after audit:

- broad data-source collection experience;
- explicit recognition of forward-fill and leakage risks;
- shared execution/accounting intent;
- reliability helpers such as atomic writes and retry logic;
- tests around execution and state;
- negative findings, including weak five-minute models and the void order-flow experiment;
- feature-contract discipline, while replacing zero-fill semantics;
- willingness to revise a result when finer validation contradicted it.

## Disposition

The old repository becomes:

- an immutable evidence archive;
- a source of candidate collectors and execution tests;
- a graveyard of failed hypotheses;
- a source of regression fixtures.

It does **not** supply the new model architecture, factor ontology, universe, validation splits, or performance priors.

## Post-sprint findings from commits `581aed2` and `fb737ae`

The detailed review is in `15_POST_SPRINT_COMMIT_REVIEW.md`.

### L-012 — Pseudo-out-of-sample information-bar evaluator  
**Severity: Critical**

The evaluator fits one model on the first 80% of the complete sample and reuses it across nominal walk-forward test slices. This is not fold-specific walk-forward retraining and can evaluate on observations already used for fitting.

**Action:** invalidate the Paper #2 v2 OOS label and rebuild with one fresh model per purged fold.

### L-013 — Future-dependent information-bar boundaries  
**Severity: Critical**

The volume threshold is calculated from total volume over the complete sample. Future observations therefore determine historical bar boundaries, and extending the dataset can revise prior bars.

**Action:** estimate and freeze thresholds from the training period only, or use a preregistered causal rolling rule.

### L-014 — Evaluator/trainer representation mismatch  
**Severity: Critical**

The evaluator aggregates already-computed time-bar features into information bars. The artifact trainer constructs information bars first and computes features afterward.

**Action:** evaluate the exact transformation order used by the trained artifact.

### L-015 — Second-venue robustness implementation defect  
**Severity: Critical**

The alternate threshold is computed from BloFin volume, but bar grouping still accumulates the frame's Binance `volume` column and retains Binance price/features.

**Action:** rebuild the treatment from true venue-specific raw observations.

### L-016 — Information-bar training/serving skew  
**Severity: High**

The serving bot still constructs time-bar inputs. Deploying the information model requires a causal streaming representation, not a filename change.

**Action:** quarantine `_info` artifacts until a serving contract and parity tests exist.

### L-017 — Unstable small-sample fits  
**Severity: High**

The latest committed information model reports only 496 training bars for 113 features and 200 trees, while other assets have materially different training counts.

**Action:** enforce minimum effective sample, stability, and provenance gates before fitting or comparing assets.

### L-018 — Artifact metadata is insufficient for promotion  
**Severity: High**

The committed metadata reports headline split sizes and accuracy but not complete date ranges, class composition, flat coverage, predictions, net returns, data hashes, threshold lineage, or environment.

**Action:** adopt the experiment and artifact schemas in this package.

### L-019 — Model discovery namespace hazard  
**Severity: Medium**

The generic model glob also matches `_info` artifacts. The explicit screener currently blocks selection, but fallback discovery can parse representation suffixes as symbols.

**Action:** require typed manifests and representation compatibility rather than filename inference.

### L-020 — Literature role conflation  
**Severity: Medium**

A recent volatility-adaptive trend working paper is implementable but exploratory; a systematic mapping study is a review, not a trading rule.

**Action:** classify sources by evidence type before creating experiments.
