# Source note — Kraken (CORRECTION: bulk host unreachable)

**Role:** BACKFILL_PRIMARY (CONDITIONAL — host unreachable) + INCREMENTAL_PRIMARY (REST OK)
**Audit date:** 2026-07-18 (correction pass)

## Historical bulk files — ACCESS GAP
- The official Kraken historical download host (`data.kraken.com`) does **NOT resolve** from
  this environment (DNS failure, 2026-07-18). Historical trade/OHLCVT bulk backfill is
  therefore `CONDITIONAL` pending access from a host where the domain resolves.
- The first pass presented Kraken REST OHLC as a historical source. That was wrong: REST
  OHLC is an **incremental/current** endpoint capped at **720 entries** and is not the bulk
  historical file. It is retained only as an incremental source (SRC-003b).

## Live REST (incremental, retained, valid)
- Trades `XBTUSD` since 2025-01-01: 1000 rows, sha a0d9c878…; fields price,volume,time,side,ordertype,misc.
- OHLC `XBTUSD` 1h: 721 rows, sha ed2b3dba…; fields time,open,high,low,close,vwap,volume,count.

## Expected bulk schema (NOT verified — host unreachable)
- Per-pair daily CSV; OHLCVT cols time,open,high,low,close,vwap,volume,count; Trades cols
  price,volume,time,side,ordertype,misc.
- Pairs prefixed (`XXBTZUSD`); volume in base (XBT), price in quote (USD).
- **No-trade OHLCVT omission**: UNVERIFIED — must confirm whether Kraken emits a
  zero-volume bar or omits the interval, then reconcile reconstructed bars from trades
  against provider candles once the bulk host is reachable.

## Required before promotion (CONDITIONAL)
1. Acquire from a host where `data.kraken.com` resolves.
2. Verify ZIP/CSV layout, timestamp precision (unix seconds), pair identifiers, units.
3. Confirm no-trade interval handling; diff reconstructed vs provider OHLCVT.
4. Confirm quarterly update behavior.

## Licensing
- Public data usable for research; confirm redistribution clause.
