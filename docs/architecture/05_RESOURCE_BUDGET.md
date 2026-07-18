# 05 — Resource Budget and Performance Plan

## 1. Hardware assumptions

- CPU: Ryzen 5 5600X, 6 cores / 12 threads
- RAM: 32 GB
- Storage: local SSD/NVMe strongly preferred
- No required GPU
- No required cloud service

This is sufficient for the Phase 1 daily/weekly program. The main risk is poorly structured I/O, not model compute.

## 2. Memory budget

Default operating budget:

| Component | Budget |
|---|---:|
| OS, filesystem cache, desktop | 6–8 GB |
| DuckDB query memory limit | 18–20 GB |
| Python/controller overhead | 2–4 GB |
| Safety margin | 2–4 GB |

Recommended DuckDB defaults:

```sql
SET threads = 6;
SET memory_limit = '20GB';
SET temp_directory = '/fast-ssd/crypto-factor/tmp/duckdb';
```

Do not let DuckDB, Polars, BLAS, XGBoost, and a process pool all use every thread simultaneously.

## 3. CPU policy

- Data parsing/transform: up to 4 worker processes or 6 engine threads.
- HTTP collection: 2–6 concurrent requests, further limited by source policy.
- XGBoost/linear algebra: one training job at a time, 6 threads maximum.
- Chronological outer folds: run serially by default.
- Set BLAS/OpenMP threads to 1 inside multi-process jobs.

Parallelize independent I/O and partitions, not every layer at once.

## 4. Data-frame policy

### Use Polars/DuckDB for large tables

- lazy Parquet scans;
- projection/predicate pushdown;
- streaming sinks;
- SQL windows and joins;
- incremental partition processing.

### Use pandas only at the modeling/report edge

Convert only the fold-specific matrix needed by scikit-learn/statsmodels when it comfortably fits memory.

### Never

- concatenate all historical 5-minute CSVs into one pandas DataFrame;
- materialize all venue/timeframe combinations in RAM;
- run one process per asset with full data copies;
- cache large duplicate wide feature matrices without manifesting them.

## 5. Disk sizing

Exact sizing must come from the Tier-0 manifest. Use this planning formula:

```text
working_disk ~= raw_bytes
             + canonical_parquet_bytes
             + derived_parquet_bytes
             + max(2 × largest active partition, 20 GB) for spill/staging
             + experiment artifacts
             + backup overhead
```

A practical starting target is:

- **250 GB free**: likely workable for curated 5-minute bars/funding and Phase 1 research;
- **500 GB–1 TB SSD**: comfortable when retaining raw archives, multiple venues, and temporary rebuilds;
- full-market L2/tick history: intentionally excluded because it can dominate storage by orders of magnitude.

Do not buy storage based on guessed row counts. Generate the manifest first.

## 6. Parquet tuning defaults

- Zstandard compression, modest level.
- 128–256 MB target file size.
- monthly partitions for 5-minute bars/funding.
- yearly partitions for daily/weekly derived panels.
- sort within file by instrument/time.
- write statistics.
- avoid per-symbol files in canonical storage.

These defaults are revisited after measuring file sizes and query profiles.

## 7. Model complexity budget

Phase 1 model ladder:

1. factor quantiles;
2. equal-factor composite;
3. volatility-scaled composite;
4. ridge/elastic-net cross-sectional model;
5. shallow CPU histogram tree model.

Constraints for initial ML:

- low hundreds of features are not allowed by default;
- no deep neural networks;
- no Bayesian/global hyperparameter optimizer;
- small preregistered grid or fixed hyperparameters;
- maximum tree depth and number of trials explicitly bounded;
- predictions and costed portfolios persisted for every trial.

The daily U50/U100 panel is small enough that rigorous validation, not compute, will be the bottleneck.

## 8. Scheduling

Use OS scheduling:

- Linux: `systemd` timers preferred; cron acceptable.
- Windows: Task Scheduler.

A job acquires a filesystem/SQLite lock, writes structured logs, and exits. No long-running orchestration service is required.

Suggested cadence:

- daily: incremental bars/funding/reference snapshots;
- daily after ingest: quality report;
- weekly: compaction, universe/factor snapshot, paper decision;
- monthly: archive reconciliation and checksum scan;
- quarterly: Kraken incremental archive refresh and broader source audit.

## 9. Performance acceptance tests

Before optimizing, record:

- rows/second parse and publish;
- peak RSS;
- Parquet compression ratio;
- scan time for one asset, U50 one year, and full daily panel;
- U50 universe build time;
- one complete single-factor experiment time;
- temporary disk peak.

Architecture changes require measured evidence from these benchmarks.
