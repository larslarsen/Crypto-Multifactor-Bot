# Crypto Multifactor Platform — Architecture v1

**Status:** Proposed and implementation-ready, subject to the local Tier-0/Tier-1 data audit  
**Architecture date:** 2026-07-17  
**Target machine:** Ryzen 5 5600X, 32 GB RAM, local SSD/NVMe  
**Primary workload:** Daily/weekly cross-sectional crypto factor research  
**Design posture:** Local-first, batch-first, data-first, fail-closed

## Decision summary

The platform should be a **modular monolith**, not a distributed system.

- Immutable raw source objects on the local filesystem.
- Canonical and derived observations in partitioned Parquet.
- DuckDB for analytical queries over Parquet, without duplicating the entire lake into a database.
- SQLite for small transactional control-plane state: manifests, watermarks, runs, issues, and promotions.
- Polars/PyArrow for streaming transforms and Parquet publication.
- Python package boundaries that enforce point-in-time data, research/serving parity, and typed model artifacts.
- CLI-driven batch jobs scheduled with the operating system; no Airflow, Spark, Kafka, Kubernetes, feature-store service, or MLflow server.
- Daily/weekly factors first. Intraday event bars and live execution remain quarantined extensions.

This architecture is intentionally boring. On one workstation, boring is an advantage: fewer moving parts, less hidden state, easier reproduction, and more CPU/RAM available for the research itself.

## Read in this order

1. `docs/architecture/00_SYSTEM_ARCHITECTURE.md`
2. `docs/architecture/01_DATA_ARCHITECTURE.md`
3. `docs/architecture/02_DATA_SOURCE_PLAN.md`
4. `docs/architecture/03_DOMAIN_INTERFACES.md`
5. `docs/architecture/04_REPOSITORY_LAYOUT.md`
6. `docs/architecture/05_RESOURCE_BUDGET.md`
7. `docs/architecture/06_TEST_AND_VALIDATION_STRATEGY.md`
8. `docs/architecture/07_IMPLEMENTATION_ROADMAP.md`
9. `docs/architecture/08_LEGACY_MIGRATION_PLAN.md`
10. `docs/architecture/09_RISK_REGISTER.md`

The `schemas/`, `configs/`, and `sql/` directories contain implementation contracts. `scaffold/` is a deliberately small starter overlay, not a finished application.

## Binding architecture decisions

- The raw-data store is append-only and content-addressed.
- Every usable value has explicit event and availability time.
- Ticker strings are aliases, never primary identifiers.
- Source-specific data remains source-specific until a documented canonical transform.
- Venue observations are preserved; “consolidated” data never destroys provenance.
- Features and labels are physically separate datasets.
- Historical universe membership is materialized and versioned.
- An experiment cannot run without frozen dataset IDs, config, code commit, and environment lock hash.
- Serving never discovers models by filename glob. It loads only promoted artifacts with a typed representation manifest.
- No information-bar model may enter serving until the causal/parity experiment passes.

## First implementation objective

Do **not** implement factors first. Implement the local manifest/audit pipeline and import the legacy observations into immutable raw objects. Architecture acceptance begins when the platform can prove what data exists, where it came from, what each timestamp means, and whether the same dataset can be rebuilt from hashes.
