# Point-in-Time Data Contract

## 1. Design principle

A value is usable only when the system can answer:

1. what economic period did it describe?
2. when did it become observable?
3. when was it ingested?
4. which raw object produced it?
5. which transform version created it?

## 2. Required temporal fields

Every research table has:

- `event_time`: time the market/network event occurred;
- `period_start`: beginning of the summarized interval;
- `period_end`: end of the summarized interval;
- `source_publish_time`: provider publication time, when applicable;
- `availability_time`: earliest time the strategy may use the value;
- `ingested_at`: local collection time;
- `valid_from` and `valid_to`: validity range for slowly changing metadata.

For ordinary closed OHLCV bars, `availability_time` cannot precede `period_end`.

## 3. Canonical identifiers

Never join by ticker alone.

Required keys:

- `asset_id`
- `instrument_id`
- `venue_id`
- `market_type`
- `base_asset_id`
- `quote_asset_id`
- `contract_id`, if derivatives
- `chain_id` and `token_contract`, if on-chain/DEX

## 4. Price-bar schema

Minimum fields:

- `instrument_id`
- `venue_id`
- `period_start`
- `period_end`
- `availability_time`
- `open`, `high`, `low`, `close`
- `base_volume`
- `quote_volume`
- `trade_count`, nullable
- `vwap`, nullable
- `source_dataset_id`
- `quality_flags`

Constraints:

- `low <= min(open, close)`;
- `high >= max(open, close)`;
- `low <= high`;
- prices positive;
- volumes nonnegative;
- primary key unique;
- gaps and outages represented explicitly.

## 5. Derivatives schema

In addition to market prices:

- mark price;
- index price;
- funding rate;
- funding cash-flow timestamp;
- open interest;
- contract multiplier;
- margin asset;
- settlement asset;
- fee tier;
- maintenance-margin schedule version.

## 6. Feature table

Each feature row includes:

- `decision_time`
- `asset_id`
- `feature_id`
- `value`
- `availability_time`
- `lookback_start`
- `lookback_end`
- `source_dataset_ids`
- `transform_version`
- `missing_reason`

Allowed missing reasons include:

- `NOT_LISTED`
- `NOT_APPLICABLE`
- `SOURCE_UNAVAILABLE`
- `INSUFFICIENT_HISTORY`
- `PUBLICATION_LAG`
- `QUALITY_REJECTED`

A missing value is never encoded as a numeric zero.

## 7. Labels and returns

Each target row includes:

- `event_start`
- `event_end`
- `entry_price_time`
- `exit_price_time`
- gross return;
- fees;
- spread/impact;
- funding/borrow;
- net return;
- censoring flag;
- delisting/default treatment;
- ambiguity flag.

Forward labels are never written into the feature store.

## 8. Imputation

Imputation is fitted only on the training window.

Baseline rules:

- cross-sectional median for suitable continuous characteristics;
- explicit missingness indicator;
- no forward fill beyond a factor-specific maximum age;
- no backfill from future observations;
- no global full-sample normalization.

## 9. Normalization

Cross-sectional transforms are computed independently at each decision date:

1. apply preregistered clipping/winsorization;
2. rank or robust-standardize across eligible assets;
3. optionally neutralize controls using only that date;
4. preserve the raw characteristic alongside the transformed score.

## 10. Raw-data immutability

Raw objects are content-addressed and never overwritten. Corrections create a new dataset ID and a supersession record.

Research runs reference exact dataset hashes, not mutable paths such as `*_max.csv`.

## 11. Consolidation

Venue consolidation must be reproducible.

A consolidated observation records:

- all contributing venue rows;
- venue reliability weights;
- staleness filters;
- outlier rule;
- volume rule;
- price rule;
- transform version.

A single “best exchange” may be used for execution, but not silently substituted for the consolidated research market.

## 12. Minimum manifest record

```json
{
  "dataset_id": "sha256:...",
  "source": "provider",
  "venue_id": "venue",
  "instrument_id": "venue:market:symbol",
  "schema_version": "1.0.0",
  "collector_commit": "git-sha",
  "acquired_at": "UTC timestamp",
  "event_start": "UTC timestamp",
  "event_end": "UTC timestamp",
  "rows": 0,
  "bytes": 0,
  "sha256": "...",
  "license_class": "internal-research"
}
```
