# Source note — Binance (CORRECTION: real archive audit)

**Role:** BACKFILL_PRIMARY (historical archive) + INCREMENTAL_PRIMARY (live REST)
**Audit date:** 2026-07-18 (correction pass)

## Real archive objects acquired (data.binance.vision — NOT the data-api host used in error before)

- Spot aggTrades `BTCUSDT` 2024-12-31: 1,218,370 rows, 16.85 MB zip, sha 31bf57b5…
- Spot aggTrades `BTCUSDT` 2025-01-01: 653,485 rows, 9.82 MB zip, sha 1a8361e4…
- Spot klines 1m `BTCUSDT` 2025-01-01: 1,440 rows, 69 KB zip, sha 10a12909…
- USD-M perp aggTrades `BTCUSDT` 2025-01-01: 726,612 rows, 9.36 MB zip, sha b0e75563…
- USD-M perp trades `BTCUSDT` 2025-01-01: 1,804,361 rows, 15.1 MB zip, sha 0b82a0c8…
- Funding monthly `BTCUSDT` 2025-01: 94 rows, 825 B zip, sha df725010… (schema:
  `calc_time,funding_interval_hours,last_funding_rate`; 8h interval; ms calc_time).

## Timestamp-precision boundary — VERIFIED ON ARCHIVE FILES
- 2024-12-31 spot aggTrades `transact_time` = **13-digit milliseconds** (e.g. 1735689599951).
- 2025-01-01 spot aggTrades `transact_time` = **16-digit microseconds** (e.g. 1735689600010866).
- This flips exactly on 2025-01-01. (The first pass used live REST, which is ms-only, and
  could not isolate the µs boundary. This correction uses the archive directly.)
- Klines `open_time` = 16-digit µs throughout (e.g. 1735689600000000).
- Perp files keep **ms** transact_time (do not assume µs for perp).

## Checksum / replacement
- Provider `.CHECKSUM` sidecar for 2025-01-01 matches locally computed SHA-256 **exactly**
  (provider 1a8361e40b3a… = local 1a8361e40b3a…). Verified.
- Real replacement register: `binance/binance-public-data` → `updates/2022-10-04_aggregate_trade_updates.csv`
  audited; format `File, Original File Checksum, New File Checksum` (e.g. BNBBTC-aggTrades-2018-01
  old→new). Confirms Binance does replace historical files and publishes both checksums.
- Implication: backfill MUST validate provider CHECKSUM at acquisition; never assume
  immutability; record both old and new checksums on replacement.

## Schema
- Spot aggTrades CSV: `agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker`.
- Klines CSV (12 fields): open_time,open,high,low,close,volume,close_time,quote_volume,trades,taker_base,taker_quote,ignore.
- Perp aggTrades: header row + `agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker` (ms).

## Live REST (incremental, retained)
- api.binance.com klines/aggTrades + fapi.binance.com fundingRate remain valid incremental
  sources. REST `fundingRate` is current; the archive field is `last_funding_rate`.

## Units / licensing
- Price quote USDT; volume base BTC for spot; perp in USDT notional. Public market data
  usable for research; confirm redistribution terms before committing raw data.

## Gaps closed
- Bulk backfill now CONFIRMED feasible (wrong host was the original error).
- Provider checksum verified; real replacement example audited.
