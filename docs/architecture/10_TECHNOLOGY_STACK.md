# 10 — Technology Stack

## Core language

- Python 3.12 as the conservative initial runtime.
- `pyproject.toml` and a committed `uv.lock` for exact environments.

## Data

- PyArrow: schemas and Parquet interoperability.
- Polars: lazy/streaming ETL and vectorized transformations.
- DuckDB: local SQL over Parquet and larger-than-memory operations.
- SQLite: control catalog and job state.

## Research

- NumPy/SciPy.
- scikit-learn for regularized models and preprocessing.
- statsmodels for inference where appropriate.
- XGBoost only as an optional shallow challenger after baselines.
- Matplotlib for deterministic static reports.

## Application

- Typer or argparse for CLI.
- HTTPX for public HTTP collection.
- Tenacity or a small explicit retry policy.
- Pydantic for configuration/metadata boundary validation.
- Standard-library logging or structured JSON logging; no logging service.

## Quality

- pytest.
- Hypothesis for temporal/leakage properties.
- Ruff for lint/format.
- mypy or pyright for type checking.
- JSON Schema and Arrow schema checks.

## Why Polars and DuckDB both

- DuckDB is strongest for SQL joins, windows, audits, and ad hoc scans.
- Polars is useful for source parsing, lazy transformation pipelines, and streaming writes.
- PyArrow is the interchange/schema layer.

Do not wrap all three in an internal dataframe abstraction. Use the right engine at domain boundaries and exchange Arrow tables/Parquet.

## Dependency discipline

- Keep the base install small.
- Put ML, plotting, and development tools in optional groups.
- Commit the lockfile.
- Record lock hash in experiment bundles.
- Upgrade deliberately with a compatibility/reproduction run.
