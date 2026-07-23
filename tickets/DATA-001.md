# DATA-001 — Live Market Data Acquisition Pipeline

**Priority:** P0
**Status:** ACCEPTED
**Dependencies:** HARDEN-001 (ACCEPTED), PAPER-004 (accepted), RAW-001 (accepted), MAN-001 (accepted), UNIVERSE-001 (accepted)
**Layer:** data platform / acquisition
**Architecture:** must use existing RAW-001 content-addressed store and MAN-001 publisher; no new storage layer

## Objective

Wire up live market data from exchange APIs through the existing RAW-001 / MAN-001 pipeline, replacing synthetic data in the factor → experiment → paper execution path.

## Current State

The pipeline from normalized Parquet → published datasets → factors → experiments → paper execution is built and tested, but all data is synthetic. No exchange fetcher calls any live API and writes through the catalog. The only real network calls in the codebase are BitMEX funding REST client (bypasses RAW-001) and CoinGecko universe list (one-shot).

## Scope

### In scope

1. **Binance spot klines fetcher** — download historical and recent daily/hourly OHLCV for the active U50 universe via `GET /api/v3/klines`. Write raw JSON responses through `RawObjectWriter` and `SqliteRawObjectCatalog` (RAW-001).
2. **Binance kline normalizer** — `ingest/binance.py` already exists; wire it to consume RAW-001 objects and produce source-specific bars Parquet. Publish via `DatasetPublisher` (MAN-001).
3. **Canonical bar pipeline** — `market/bars.py` already exists; run on published Binance source bars to produce unified market bars. Publish as canonical dataset.
4. **AsOf eligibility** — `CatalogAsOfStore` queries against real published bars; factor/experiment/paper paths consume real data.
5. **Backfill support** — one-time historical fetch for all U50 assets back to 2020 (or earliest available).
6. **Incremental update** — subsequent runs fetch only new bars since last watermark.

### Out of scope

- Real-time WebSocket streaming (REST polling is sufficient for daily/hourly signals)
- Other exchange fetchers (Binance spot first; Kraken, Bybit, OKX follow-on tickets)
- LIVE order placement or paper execution on live data (governed by HARDEN-001 policy)
- Trade/orderbook data (klines only)

## Deliverables

1. `src/cryptofactors/acquisition/binance_fetcher.py` (or similar) — Binance kline REST client implementing the `SourceAdapter` protocol, with rate limiting, retry, and content-addressed publication
2. Wiring of `ingest/binance.py` normalizer to consume RAW-001 objects
3. `scripts/research/backfill_binance_klines.py` — one-shot backfill runner
4. Tests with Binance sandbox or mocked responses
5. A dry-run producing a real non-empty dataset in the catalog

## Acceptance (Jr)

1. `python3 -m pytest tests/acquisition/ -q --tb=short`
2. `python3 -m ruff check src/cryptofactors/acquisition/`
3. `python3 -m mypy --no-error-summary src/cryptofactors/acquisition/`
4. Backfill script fetches ≥1 asset's daily klines, verifies published dataset exists in catalog
5. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
