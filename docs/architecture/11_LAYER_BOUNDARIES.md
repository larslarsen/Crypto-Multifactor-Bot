# 11 — Data, Research, and Execution Boundaries

## 1. Purpose

The three logical layers prevent two common failures:

1. research that depends on live exchange behavior and cannot be reproduced;
2. serving code that silently implements a different feature, data, or portfolio pipeline from research.

They are logical boundaries inside a modular monolith, not network services.

## 2. Data Platform

### Responsibilities

- source discovery and acquisition;
- immutable raw-object storage;
- source-specific parsing and normalization;
- asset, instrument, venue, alias, and listing reference data;
- timestamp, unit, coverage, and cross-source quality checks;
- quarantine;
- canonical market, funding, fee, FX, and metadata datasets;
- historical universe inputs and snapshots;
- manifests, lineage, watermarks, and quality records.

### May access

- official exchange archives and public APIs;
- local files explicitly registered as source objects;
- the SQLite control catalog;
- configured raw/canonical storage roots.

### Must not contain

- factor hypotheses;
- labels or forward returns;
- model fitting;
- portfolio optimization decisions;
- broker order placement.

## 3. Research Platform

### Responsibilities

- point-in-time dataset access by immutable ID;
- factor materialization;
- labels and event intervals;
- chronological split generation, purge, and embargo;
- portfolio and cost simulation;
- experiments and immutable result bundles;
- inference and robustness;
- Evidence Registry;
- artifact candidacy and promotion recommendations.

### Inputs

Only immutable, accepted datasets and universe snapshots from the Data Platform.

### Must not

- call exchange APIs;
- load API credentials;
- use a broker SDK;
- mutate canonical datasets;
- use current exchange metadata as historical truth;
- read execution fills as research data until they have been ingested and published by the Data Platform.

## 4. Execution Platform

### Responsibilities

- load explicitly promoted artifacts;
- verify representation and feature parity;
- obtain current accepted data through the Data Platform update path;
- calculate signed decision snapshots;
- enforce operational risk controls;
- paper simulation and, only after later approval, broker order placement;
- persist orders, fills, rejects, positions, and reconciliation events.

### Must not

- retrain models;
- select factors;
- tune thresholds;
- bypass the promotion registry;
- write observations directly into research datasets;
- load an artifact by filename convention.

## 5. Allowed dependency direction

```text
shared/core
   ↑
Data Platform
   ↑
Research Platform
   ↑
Execution Platform
```

The arrow means “may depend on.” A lower layer must never import a higher layer.

Within the Python package, the allowed direct dependencies are specified in `docs/engineering/LAYER_DEPENDENCY_MATRIX.yaml` and checked by `scripts/check_layer_imports.py`.

## 6. Data exchange between layers

Layers exchange typed artifacts:

- Data → Research: dataset manifests, reference snapshots, universe snapshots;
- Research → Execution: promoted artifact manifests and portfolio policy manifests;
- Execution → Data: raw operational events for later immutable ingestion;
- Data → Research: published execution datasets, only after quality acceptance.

No layer communicates through undocumented directories or “latest” symlinks.

## 7. Same-process use is allowed

A modular monolith may call another layer's Python function in the same process if the dependency is allowed. The boundary is about ownership, interfaces, and direction—not process isolation.

## 8. Boundary-change rule

Any new direct dependency, alternate data path, or live-network call requires an ADR before implementation.
