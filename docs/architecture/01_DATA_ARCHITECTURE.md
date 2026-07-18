# 01 — Data Architecture

## 1. Data is the product

The project should be understood as a point-in-time data platform that happens to run factor research. Models are downstream consumers and are replaceable. Data identity, timestamp meaning, universe history, and execution semantics are not replaceable.

## 2. Storage zones

Use four simple zones. Avoid mutable “latest” datasets.

```text
$CRYPTO_FACTOR_HOME/
├── raw/              # exact source bytes; content-addressed; immutable
├── canonical/        # validated source-specific and canonical Parquet
├── derived/          # universe, factors, labels, costs, portfolios
├── experiments/      # immutable experiment bundles
├── catalog/          # control.sqlite, generated DuckDB catalog, manifests
├── state/            # watermarks, locks, prospective collection state
├── quarantine/       # failed objects/partitions plus issue records
├── cache/            # disposable downloads and query cache
└── tmp/              # DuckDB spill and atomic-write staging
```

### Raw

Preserve exact downloaded bytes and request metadata. A raw object path is based on SHA-256, not on a mutable human filename.

Example:

```text
raw/source=binance_public/object_type=monthly_klines/sha256=ab/cd/abcdef....zip
```

### Canonical

Canonical data is immutable, typed, and partitioned Parquet. A new correction creates a new dataset version and supersession relation.

### Derived

Derived datasets are rebuildable from canonical dataset IDs and code/config versions. They are still immutable because research runs reference them by ID.

### Experiments

Each run is a directory identified by experiment ID and fingerprint. Results are append-only.

## 3. Control versus analytical storage

### SQLite control catalog

Use SQLite for small transactional state:

- raw object registration;
- dataset manifests;
- lineage edges;
- watermarks and jobs;
- quality issues;
- experiment and model promotion status.

SQLite is durable, dependency-light, and appropriate for a single-writer workstation.

### Parquet observation store

Use Parquet for observations and derived panels. Do not load all Parquet into a DuckDB database file. Query it in place.

### DuckDB query engine

DuckDB provides SQL, joins, windows, and out-of-core spilling over Parquet. The DuckDB file should contain views, small reference caches, and report tables—not a second complete copy of the observation lake.

## 4. Dataset identity

A dataset is not “the files in this folder.” It is an immutable manifest containing:

- dataset ID;
- dataset type and schema version;
- source dataset/object IDs;
- transform name/version and code commit;
- canonical config hash;
- list of output object hashes;
- row count, bytes, and temporal coverage;
- quality summary;
- superseded dataset ID, if any;
- created-at time.

Recommended identity:

```text
dataset_id = "ds_" + sha256(canonical_json(manifest_without_dataset_id))
```

File paths are locators. Dataset IDs are identities.

## 5. Canonical identifiers

### Asset

The economic asset independent of venue and quote currency.

Example conceptual key: `asset_id = 1001` for Bitcoin.

### Instrument

A tradable listing or contract.

An instrument includes:

- venue;
- market type;
- base asset;
- quote asset;
- contract type/multiplier;
- settlement/margin asset;
- listing/delisting validity;
- source symbol aliases.

Use compact integer surrogate IDs in fact Parquet for speed. Human-readable stable strings remain in reference tables.

### Never join by ticker

`BTC`, `XBT`, wrapped tokens, bridged assets, redenominations, and reused symbols make ticker-only joins invalid.

## 6. Temporal model

Every table uses timezone-aware UTC semantics. Store high-volume fact timestamps as signed 64-bit UTC microseconds or Arrow timestamps with UTC metadata. Preserve source timestamp unit in raw metadata.

### Required concepts

- `event_time`: event occurred.
- `period_start`, `period_end`: aggregation interval.
- `source_publish_time`: provider says it published the value, if available.
- `availability_time`: earliest point the strategy may consume it.
- `ingested_at`: local acquisition time.
- `valid_from`, `valid_to`: when reference metadata is economically valid.
- `known_from`, `known_to`: when the system knew that reference fact.

Reference data is therefore effectively bitemporal. A historical backtest uses both economic validity and knowledge availability.

## 7. Core canonical datasets

### `reference_assets`

Canonical assets and classification flags.

### `reference_instruments`

Venue instruments/contracts and validity windows.

### `reference_aliases`

Source-specific symbol-to-instrument mappings with knowledge windows and confidence.

### `listing_events`

List, delist, suspend, resume, migrate, redenominate, contract launch/expiry, and announced-delisting events.

### `market_bars`

Per-venue, per-instrument bars. Never destroy venue identity.

Minimum fields:

- instrument ID, venue ID, timeframe;
- period start/end and availability;
- OHLC;
- base and quote volume;
- trade count and taker volume when available;
- source dataset ID;
- quality flags.

### `funding_cashflows`

Funding rate, timestamp, interval, sign convention, mark/index references, and realized cash-flow rule.

### `stablecoin_fx`

Observed quote-to-USD conversion. Never assume USDT/USDC equals exactly one dollar in historical calculations.

### `venue_fee_schedule`

Dated maker/taker and relevant derivative fees. When historical schedules are unavailable, store an explicit conservative assumption with evidence class.

### `universe_snapshot`

One row per decision time and asset, including all gate values and rejection reasons.

### `execution_route_snapshot`

The deterministic venue/instrument selected for simulated entry/exit at a decision time. Data venues and execution venues are separate concepts.

### `factor_value`

Long-form factor characteristics and scores with lineage and missing reason.

### `label_return`

Gross/net returns with event start/end and cost attribution. Physically separate from factor values.

## 8. Venue consolidation rules

“Consolidated” must never mean “average everything and throw away source rows.”

### Liquidity consolidation

For universe gating:

1. retain venue quote volume separately;
2. convert quote volume to USD using point-in-time quote FX;
3. exclude or haircut venues failing reliability policy;
4. prevent duplicate economic instruments from double counting;
5. sum or robustly aggregate approved venue volume using a versioned policy;
6. retain each component and weight.

### Price/return routing

For portfolio returns, use a point-in-time execution route rather than a hindsight consolidated close.

A route may be chosen from eligible venues using only trailing:

- availability;
- reliable volume/depth;
- fees;
- spread/cost estimate;
- jurisdiction/operational approval.

The route used for labels is stored. Robustness tests can compare single-venue and multi-venue routing.

## 9. Partition and file strategy

Do not partition by every instrument; that creates thousands of tiny files.

### Initial policy

- `market_bars`: venue / market_type / timeframe / year / month
- `funding_cashflows`: venue / year / month
- `reference_*`: dataset version only; usually one compact file each
- `universe_snapshot`: universe version / year
- `factor_value`: factor version / year
- `label_return`: target version / year
- `portfolio`: experiment/fingerprint

Within files, sort by `(instrument_id, period_start)` or `(decision_time, asset_id)`.

### File sizing

Target approximately 128–256 MB compressed files. Compact small files into a new immutable dataset version. If a monthly partition becomes too large, add a stable hash bucket on `instrument_id`; do not introduce it before the local audit proves it is needed.

### Compression

Use Parquet Zstandard with a modest level. Store statistics and dictionary encoding where useful. Raw source archives remain in their original compression format plus local hash.

## 10. Incremental updates and corrections

Each source has a watermark and an overlap policy.

- Fetch from `last_complete_event_time - overlap_window`.
- Store exact raw response.
- Deduplicate by canonical primary key.
- Compare overlapping rows with the previous dataset.
- Register changed values as corrections.
- Publish a new dataset version when corrections are accepted.
- Never mutate a dataset referenced by an experiment.

The overlap window is source-specific and documented.

## 11. Data quality and quarantine

Quality checks produce rows, not just log messages.

Issue fields include:

- issue ID;
- dataset/object ID;
- severity;
- rule ID/version;
- affected time/instruments;
- observed/expected values;
- status and resolution;
- superseding transform/dataset.

Severity policy:

- `INFO`: documented anomaly, usable.
- `WARN`: usable only with flag/sensitivity.
- `ERROR`: partition quarantined.
- `FATAL`: dataset publication blocked.

No generic `fillna(0)` or silent row drop is permitted.

## 12. Availability and as-of joins

All as-of data access goes through one reviewed implementation.

For a decision time `t`, a row is eligible only when:

```text
valid_from <= t < valid_to
and availability_time <= t
and known_from <= t < known_to   # for reference facts
```

The interface returns the selected row plus lineage. Direct ad hoc joins on date columns are prohibited in factor code.

## 13. Data retention and backup

### Re-downloadable data

Official bulk archives can be reconstructed, but manifests and checksums should still be backed up.

### Irreplaceable data

Prospectively collected API snapshots, venue metadata history, announcements, and paper/live decisions require a second local copy.

Recommended minimum:

- working copy on SSD/NVMe;
- automated nightly incremental backup to an external drive;
- periodic checksum verification;
- no secrets in backup manifests committed to Git.

## 14. Data architecture gate before models

Do not run EXP-2026 factor experiments until:

1. legacy observations have immutable raw registrations;
2. timestamp units and bar-close conventions are documented;
3. instrument aliases and listing validity are resolved to an acceptable confidence;
4. canonical daily bars are reproducible;
5. U50 snapshots are point-in-time and deterministic;
6. execution route and cost inputs are defined;
7. dataset hashes and lineage reproduce on a clean checkout plus local data root.
