# 06 — Test and Validation Strategy

## 1. Test pyramid

### Unit tests

- timestamp/unit conversion;
- canonical IDs and alias resolution;
- primary-key construction;
- cost/funding signs;
- factor formulas;
- weight constraints;
- fingerprint determinism.

### Property-based tests

Use generated data to prove invariants:

- an as-of query never returns future availability;
- adding future rows cannot change past causal features or event bars;
- current symbol changes cannot alter a frozen historical universe;
- duplicate/reordered raw rows normalize deterministically;
- purged partitions have no event overlap;
- fees/funding reconcile to net return;
- weights satisfy gross/net/capacity constraints.

### Integration tests

- raw object → canonical Parquet → universe → factor → label → portfolio → experiment bundle;
- source adapter pagination and retries using recorded fixtures;
- correction/supersession workflow;
- rebuild from a dataset manifest.

### Golden tests

A tiny synthetic market with known listings, delistings, missing bars, stablecoin depeg, funding events, and dual-touch ambiguity. Expected outputs are versioned.

### Leakage tests

Dedicated tests deliberately inject future values and ensure the pipeline rejects or cannot access them.

## 2. Data contract tests

Every published partition validates:

- Arrow/JSON schema version;
- primary-key uniqueness;
- sortedness or declared sort order;
- OHLC inequalities;
- positive prices and nonnegative volumes;
- time interval and timezone;
- closed-bar availability;
- instrument validity at event time;
- source/canonical unit compatibility;
- nullability and missing-reason consistency;
- source dataset lineage.

## 3. Cross-source checks

For overlapping venue/instrument periods:

- synchronized return correlation;
- median and tail close-price dispersion;
- quote-volume scale ratios;
- stale run detection;
- impossible constant-price/volume patterns;
- symbol/unit mismatch flags.

These are diagnostics and quarantine rules, not automatic averaging.

## 4. Research validation tests

The experiment runner must test that:

- all preprocessing objects are fit inside training scope;
- every fold trains a fresh model when a model is used;
- train/validation/test event intervals do not overlap;
- test data cannot affect bar thresholds or representation;
- flat/no-trade predictions are retained;
- predictions map to realizable route/timestamps;
- costs/funding are included before promotion metrics;
- multiple trials are counted.

## 5. Serving parity tests

Before paper serving:

- research and serving produce identical factor values from the same snapshot;
- feature names, order, types, and versions match the model manifest;
- stale/missing data causes no decision;
- rerunning after restart is deterministic;
- decision snapshots are immutable;
- model promotion is explicit and reversible.

For any future event/information-bar representation:

- append-invariance of closed historical bars;
- deterministic replay;
- durable partial-bar state;
- late/out-of-order event policy;
- exact research/streaming parity.

## 6. CI policy

GitHub CI runs only:

- formatting/linting/type checks;
- unit/property tests;
- JSON/Arrow schema validation;
- synthetic/golden integration tests;
- dependency lock consistency.

CI never downloads the full private dataset. Local commands run data-dependent integration and experiment tests.

## 7. Required gates

### Gate D0 — Raw provenance

No modeling. All local source objects registered with hashes and source evidence.

### Gate D1 — Canonical data

Timestamp, schema, primary-key, and unit checks pass; exceptions are explicit.

### Gate D2 — Reference/universe

Point-in-time instruments and U50 snapshots reproduce.

### Gate R0 — Research pipeline

Factors/labels/splits/costs pass synthetic leakage and accounting tests.

### Gate R1 — Baselines

Single-factor and transparent composites complete before ML.

### Gate S0 — Paper serving

Promoted artifact, parity, freshness, and fail-closed tests pass.

### Gate L0 — Live capital

Not part of architecture v1. Requires separate operational/security review and prospective evidence.
