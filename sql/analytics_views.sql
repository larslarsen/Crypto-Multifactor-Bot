-- Template: replace ${DATA_ROOT} when generating a local DuckDB catalog.

CREATE OR REPLACE VIEW market_bars AS
SELECT *
FROM read_parquet('${DATA_ROOT}/canonical/market_bars/**/*.parquet', hive_partitioning = true);

CREATE OR REPLACE VIEW funding_cashflows AS
SELECT *
FROM read_parquet('${DATA_ROOT}/canonical/funding_cashflows/**/*.parquet', hive_partitioning = true);

CREATE OR REPLACE VIEW reference_assets AS
SELECT *
FROM read_parquet('${DATA_ROOT}/canonical/reference_assets/**/*.parquet', hive_partitioning = true);

CREATE OR REPLACE VIEW reference_instruments AS
SELECT *
FROM read_parquet('${DATA_ROOT}/canonical/reference_instruments/**/*.parquet', hive_partitioning = true);

CREATE OR REPLACE VIEW universe_snapshot AS
SELECT *
FROM read_parquet('${DATA_ROOT}/derived/universe_snapshot/**/*.parquet', hive_partitioning = true);

CREATE OR REPLACE VIEW factor_value AS
SELECT *
FROM read_parquet('${DATA_ROOT}/derived/factor_value/**/*.parquet', hive_partitioning = true);

CREATE OR REPLACE VIEW label_return AS
SELECT *
FROM read_parquet('${DATA_ROOT}/derived/label_return/**/*.parquet', hive_partitioning = true);
