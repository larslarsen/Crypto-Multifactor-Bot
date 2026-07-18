# Coding standards

## General

- Python 3.12, type-checked in strict mode.
- Public functions have typed signatures and concise docstrings.
- Domain IDs use dedicated types or validated strings, not arbitrary filenames.
- UTC-aware datetimes only at boundaries.
- Decimal or integer minor units for fees/cash where binary float error matters.
- Pure transformations are preferred over stateful objects.
- Side effects are isolated behind narrow interfaces.
- Explicit errors beat sentinel values.

## Data

- Polars/PyArrow/DuckDB for tabular workloads.
- Parquet schemas and timestamp units are explicit.
- Sorting requirements are declared and validated.
- Partition keys are low-cardinality and query-relevant.
- No unbounded `collect()` on historical intraday data.
- No dataframe index semantics as business identity.

## SQL

- migrations are ordered and forward-only;
- foreign keys enabled;
- constraints encode invariants where practical;
- JSON fields are for extensibility, not a substitute for core relational keys;
- large observation tables do not live in SQLite.

## Tests

- unit tests for deterministic IDs and canonicalization;
- property tests for invariants;
- synthetic point-in-time and leakage fixtures;
- golden files only when semantic review is possible;
- network tests are separated and opt-in;
- tests do not depend on current exchange state.
