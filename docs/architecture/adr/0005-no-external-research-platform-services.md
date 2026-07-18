# ADR-0005 — No external feature store, MLflow server, DVC, or lakehouse framework

**Status:** Accepted for v1

## Decision

Use versioned Parquet, manifests, SQLite records, and immutable experiment directories instead of operating research-platform services.

## Rationale

The project has one machine, one primary researcher, and a small daily panel. Service infrastructure would add complexity, hidden state, and maintenance cost without improving scientific validity.

## Revisit trigger

Measured collaboration, scale, or artifact-management requirements that cannot be met by the local manifest design.
