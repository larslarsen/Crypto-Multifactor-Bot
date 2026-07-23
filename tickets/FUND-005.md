# FUND-005 — BitMEX Funding Cashflow Provider

**Priority:** P0
**Status:** ACCEPTED
**Dependencies:** FUND-004 (PASSED - BitMEX approved as pragmatic primary)
**Layer:** ingest / market / execution
**Architecture:** Implements the BitMEX REST paginator for funding and the internal provider for executing funding cashflows on perpetual positions.

## Objective

Implement the ingestion and standardization of BitMEX perpetual funding rates to enable cashflow accounting in our simulation and execution layers. This addresses Step #10 of the implementation sequence. 

## Scope

- **Ingestion:** A client (`src/cryptofactors/ingest/bitmex_funding.py`) to query the `GET /funding` REST endpoint, paginating over `startTime`/`endTime` to build a complete historical funding rate dataset.
- **Normalization:** Standardize to 8-hour intervals and handle the 2016-05-14 to 2016-06-04 daily interval transition cleanly.
- **Data Model:** PyArrow schema mapping `(timestamp, symbol, fundingRate, fundingRateDaily)`.
- **FX Assumption:** Per the accepted FUND-004 findings, USDT is assumed pegged 1:1 with USD for quote resolution. XBT inverse contracts must use the point-in-time BTC/USD price to convert the BTC cashflow to USD equivalent.
- **Provider Interface:** A provider that, given an open quantity and decision time, can compute the cumulative funding cost/proceeds over a holding period.

## Required Contract

- Pluggable into the `PortfolioSimulator` (or a dedicated `FundingSimulator`) so that perpetual long/short cells can deduct funding costs at exact 8h settlement times.
- Deterministic, fail-closed on missing data.
- API requests must respect 180 req/min limits.

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/ingest/ tests/market/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/ingest/bitmex_funding.py`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/ingest/bitmex_funding.py`
4. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Strong Model): production source only. Stop for reviewer.
- Jr Engineer (Weak Model): tests, gates, records, Git, commit, push after approval.

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
