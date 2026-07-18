# Research-to-Architecture Handoff

## Purpose

This document defines what the future architecture must support. It does not prescribe frameworks, databases, cloud vendors, or class hierarchies.

Architecture should begin from these research invariants, not from the legacy module tree.

## 1. Required domain boundaries

### Raw data

Immutable, content-addressed source objects.

### Reference data

Point-in-time assets, instruments, venues, contracts, listings, delistings, migrations, and fee schedules.

### Curated market data

Validated bars, trades, funding, depth, and consolidated observations.

### Feature research

Factor characteristics with availability metadata and versioned transforms.

### Universe

Dated eligibility and shortability snapshots.

### Labels/returns

Gross and net future outcomes with event intervals.

### Experiments

Immutable configuration, dataset hashes, code commit, metrics, and artifacts.

### Portfolio

Signal-to-weight logic, constraints, costs, and risk.

### Simulation

Execution, funding, delisting, and accounting.

### Serving

Frozen production features and decisions generated from an approved research version.

## 2. Non-negotiable interfaces

### Dataset manifest interface

Given a dataset ID, return its schema, source, hash, acquisition, and time coverage.

### As-of query interface

Given `(field, asset, decision_time)`, return only values with `availability_time <= decision_time`.

### Universe interface

Given `decision_time`, return eligibility, rejection reasons, and execution/shortability metadata.

### Factor interface

Given a decision time and universe snapshot, return raw values, transformed scores, missing reasons, and lineage.

### Return interface

Given a decision and horizon, return gross and net outcomes with an event-end time.

### Experiment interface

An experiment cannot run without a frozen config, dataset IDs, and code version.

### Portfolio interface

Weights are a pure function of signals, current holdings, constraints, and cost estimates.

## 3. Architecture acceptance tests

The system must prove:

- no future-availability join;
- exact reproduction from dataset hashes;
- current symbol lists do not alter historical universes;
- missing values remain distinguishable from zero;
- purging uses label event intervals;
- training transformations cannot inspect validation/test;
- fees and funding reconcile to cash;
- dual-touch OHLC events follow the declared policy;
- changing a dataset or config changes the experiment fingerprint;
- failed experiments remain discoverable.

## 4. Legacy migration categories

### Candidate transplant after audit

- collectors/backfills;
- retry and atomic-write utilities;
- execution/accounting concepts;
- selected tests and fixtures;
- symbol-resolution knowledge;
- known failure cases.

### Rewrite

- data manifest;
- universe selection;
- feature store;
- label/split pipeline;
- model-selection logic;
- research reporting;
- cost calibration;
- experiment tracking.

### Archive only

- frozen 113-feature research ontology;
- legacy model weights;
- tuned indicator/regime variants;
- claimed Sharpe expectations;
- unmatched volume-bar verdict;
- old p-values used as promotion evidence.

## 5. Suggested build order

1. manifests and instrument master;
2. curated daily market/funding tables;
3. as-of query tests;
4. point-in-time universe;
5. transparent factor library;
6. return/cost engine;
7. experiment registry;
8. single-factor reports;
9. composite portfolios;
10. ML research;
11. serving adapter.

## 6. Definition of architecture readiness

Architecture is ready to design when:

- Tier-0/1 data audit passes;
- canonical identifiers are known;
- event and availability timestamps are specified for every source;
- U50 can be generated historically;
- cost inputs are identified;
- factor and experiment schemas are accepted.

This sprint supplies the contracts. The local audit supplies the remaining empirical facts.

## 7. Conditional information-bar serving contract

This domain is **not** part of the initial architecture. It becomes eligible only if EXP-2026-015 passes the clean replication protocol.

If promoted, architecture must provide:

- an immutable bar-definition/version object;
- fold-frozen or causal threshold history;
- venue-specific raw event inputs;
- durable partial-bar state;
- deterministic replay and restart tests;
- event-time feature generation after bar close;
- strict model metadata declaring `representation_type` and `representation_version`;
- loader rejection when representation and model do not match;
- explicit separation between time-bar and information-bar artifact namespaces.

The existing `_info` filename suffix is not a sufficient serving contract.
