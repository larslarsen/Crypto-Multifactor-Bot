# Source note — Binance

**Role:** BACKFILL_PRIMARY (spot + USD-M perp) / COST_CALIBRATION (funding)
**Audit date:** 2026-07-18

## Samples acquired (hashes in 02_SOURCE_OBJECT_INVENTORY.csv)
- Spot 1m klines `BTCUSDT` 2025-01-01: 60 rows, sha 179f7d6e…, first open 1735689600000 ms UTC (no T-boundary shift confirmed).
- Spot aggTrades `BTCUSDT`: 50 rows, sha 7554baf2…; fields a,p,q,nq,f,l,T,m.
- USD-M perp aggTrades `BTCUSDT`: 50 rows, sha 0c78dc69…; same schema.
- Perp fundingRate `BTCUSDT`: 4 rows, sha e33988d9…; 8h interval implied.

## Schema
- Klines: 12-field arrays [open_time,open,high,low,close,volume,close_time,quote_volume,trades,taker_base,taker_quote,ignore]; ms-epoch UTC; bucket = [start, start+59999].
- aggTrades: a=aggId, p=price, q=qty, nq=quoteQty, f/l=first/last tradeId, T=tradeTime ms, m=isBuyerMaker.
- fundingRate: symbol, fundingIntervalHours, fundingRate, fundingTime, markPrice.

## Timestamp precision
Millisecond epoch UTC. Verified the 2025-01-01 boundary: open_time exactly 1735689600000 (no shift). Confirms LIT-038-style daily mark-to-market paths are reconstructable at 1m resolution.

## Correction / replacement
Live REST is current-only. Bulk daily zip (`data-api.binance.vision`) returned HTTP 404 from this environment → recorded as CONDITIONAL (SRC-002). The provider-replacement checksum register (github binance-public-data) was also unreachable, so a known replacement exemplar could NOT be verified this audit. Backfill via REST pagination is the working path.

## Units / licensing
Price in quote (USDT), volume in base. Public market data usable for research; confirm redistribution terms before committing raw data (registries/hashes are publishable).

## Gaps
- Bulk historical zip unreachable here.
- No provider-replacement checksum exemplar verified.
