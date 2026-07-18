# ADR-0001 — Local Parquet + DuckDB + SQLite

**Status:** Accepted provisionally pending local size audit

## Decision

Use Parquet files as the observation system of record, DuckDB as the local analytical query engine, and SQLite as the transactional control catalog.

## Rationale

- Fits one workstation and batch workloads.
- Parquet is compressed, columnar, portable, and directly queryable.
- DuckDB supports projection/filter pushdown and larger-than-memory operations with disk spill.
- SQLite is simple and reliable for small single-writer metadata/state.
- Avoids duplicating the entire Parquet lake into a database or operating a server.

## Consequences

- One canonical writer per dataset publication.
- Applications use manifests rather than database table mutation.
- A generated DuckDB catalog/view layer may be rebuilt.
- Cross-machine multi-writer operation is out of scope.
