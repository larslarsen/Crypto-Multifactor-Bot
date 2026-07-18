# 07 — Implementation Roadmap

The sequence is designed to prevent downstream code from forming around unaudited data.

## Phase 0 — Repository normalization

Deliverables:

- move sprint documents under `research/sprint_001/`;
- add root README and architecture documents;
- create `pyproject.toml`, dependency lock, package skeleton, tests, and CI;
- define local data-root configuration; no hard-coded paths.

Exit criteria:

- clean install;
- lint/unit tests pass;
- no production/research code imports from the legacy Trading-Bot repository.

## Phase 1 — Control catalog and raw registration (P0)

Implement:

- SQLite schema;
- raw content-addressed storage;
- hashing and atomic writes;
- dataset manifest publisher;
- legacy local-file registrar;
- source/request/watermark/run records.

Deliverables:

- immutable manifest of all legacy local observations;
- schema fingerprint and coverage export;
- source confidence/evidence report.

Exit criteria:

- every candidate input has a hash and source record;
- repeated registration is idempotent;
- raw objects cannot be overwritten.

## Phase 2 — Reference data and canonical bars (P0)

Implement:

- asset/instrument/alias/listing event schemas;
- Binance/Kraken/OKX/Bybit normalizers as required by the audited inventory;
- timestamp/unit normalization;
- canonical 5-minute and daily bars;
- stablecoin FX;
- data quality/quarantine rules;
- cross-source comparison report.

Exit criteria:

- canonical daily bars rebuild from raw IDs;
- ambiguous instruments are excluded or manually resolved;
- native and resampled daily bars reconcile within documented tolerances.

## Phase 3 — Funding, fees, costs, and execution routes (P0)

Implement:

- funding event normalization and cash-flow tests;
- dated fee schedules/assumption classes;
- historical cost tiers and sensitivity parameters;
- point-in-time execution route snapshots.

Exit criteria:

- fee/funding cash reconciliation passes golden fixtures;
- long-only route is valid;
- market-neutral route remains disabled until shortability inputs pass.

## Phase 4 — Point-in-time universe (P0)

Implement U25/U50/U100 snapshots exactly from the research contract.

Exit criteria:

- all gates/rejection reasons persisted;
- delisted assets retained;
- current metadata changes cannot alter frozen historical snapshots;
- survivor-biased diagnostic quantifies, but never replaces, primary universe.

## Phase 5 — Research substrate (P1)

Implement:

- as-of access layer;
- factor output schema;
- labels/net returns;
- event-interval purged nested splits;
- experiment fingerprints/bundles;
- reporting and inference foundation.

Exit criteria:

- synthetic end-to-end pipeline passes;
- no feature/label leakage;
- one null/noise factor correctly fails.

## Phase 6 — Transparent factor baselines (P1)

Implement and run in order:

- momentum;
- reversal;
- defensive;
- liquidity;
- carry after derivatives gate;
- equal-factor and volatility-scaled composites.

Exit criteria:

- preregistered tear sheets;
- all net costs and robustness cells reported;
- failed factors archived.

## Phase 7 — Regularized and shallow ML challengers (P2)

Only after accepted transparent baselines:

- ridge/elastic net;
- shallow histogram tree model;
- limited, preregistered hyperparameter choices;
- ablations and stable outer-fold improvement.

Exit criteria:

- challenger beats simple composites net of costs;
- complexity-adjusted evidence and prospective plan accepted.

## Phase 8 — Prospective paper serving (P2)

- freeze research version;
- collect clean prospective observations;
- daily/weekly fail-closed paper decisions;
- no retuning inside sealed period;
- monitor data and portfolio drift.

## Separate branch — Information-bar replication (P2)

Do not block the primary factor platform.

- causal fold-local threshold builder;
- true venue-specific raw inputs;
- features computed after representation;
- matched decisions/horizon/cost/capacity;
- streaming replay/parity only after empirical promotion.

## Work-unit sizing for the junior engineer

Each implementation ticket should contain:

- one domain and one observable output;
- explicit input/output schema;
- invariants and failure policy;
- tests before integration;
- no architecture expansion unless an ADR is approved;
- no “helper framework” created for a single use case.

## Immediate next eight tickets

1. `CAT-001`: initialize SQLite control schema and migrations.
2. `RAW-001`: content-addressed raw object writer with atomic rename/hash test.
3. `MAN-001`: canonical dataset-manifest fingerprint and publisher.
4. `LEG-001`: recursively register legacy local files without reading all content into RAM.
5. `AUD-001`: schema/coverage profiler writing Parquet/JSON reports.
6. `REF-001`: asset/instrument/alias schemas and manual resolution workflow.
7. `BIN-001`: Binance kline normalizer with pre/post-2025 timestamp unit tests.
8. `BAR-001`: canonical bar publisher and daily resampling reconciliation test.

Do not assign factor implementation until these tickets pass.
