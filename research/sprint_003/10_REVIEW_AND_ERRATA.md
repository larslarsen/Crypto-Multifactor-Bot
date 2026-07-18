# 10 — Review and Errata (Sprint 003 correction)

**Sprint:** 003 (correction pass)
**Supersedes:** the original Sprint 003 audit (commit 318bfa6) for historical-source conclusions
**Created:** 2026-07-18
**Research cutoff:** 2026-07-18

## What the original pass actually tested

The first audit (318bfa6) **primarily tested live REST connectivity**, not the required
historical backfill sources. It acquired bounded live REST samples (Binance/OKX/Bybit
market REST, Kraken REST OHLC/Trades, Coin Metrics catalog) and one malformed Binance bulk
placeholder. Several conclusions overstated historical-source readiness. This document
preserves the original records, classifies each, and supersedes the unsupported parts.

Original acquisition records are retained in `02_SOURCE_OBJECT_INVENTORY.csv` (first-pass
rows) and the per-source notes, with new columns `sample_status`, `limitation`, and
`superseded_by` added. No original row was deleted.

## Classification of original (first-pass) samples

| Original sample | sample_status | limitation | superseded_by |
|---|---|---|---|
| Binance malformed bulk placeholder (`data-api.binance.vision/.../<SYM>/...zip`, 404) | INVALID / NON-QUALIFYING | wrong host (`data-api` vs `data.binance.vision`); not a real object; path pattern unverified | Real Binance archive objects below (Sec. 2) |
| Kraken REST OHLC `XBTUSD` presented as historical | NON-QUALIFYING FOR HISTORICAL | REST OHLC is incremental/current, capped at 720 entries; not the bulk historical file | Kraken bulk file audit (Sec. 3) — HOST UNREACHABLE, recorded as gap |
| OKX live `/market/trades` + `/market/books` presented as historical-source qualification | NON-QUALIFYING FOR HISTORICAL | live snapshots, not historical files; no coverage dates | OKX historical files (Sec. 4) — HOST UNREACHABLE, recorded as gap |
| Binance live REST klines/aggTrades/funding | VALID AS INCREMENTAL SAMPLE | proves incremental capture only; does NOT prove backfill | Real archive objects below |
| Kraken REST Trades | VALID AS INCREMENTAL SAMPLE | incremental source audit; 720-entry OHLC limit noted | retained as incremental only |
| Coin Metrics catalog (no params) | VALID | catalog only, not timeseries observations | Real timeseries (Sec. 7) |
| DefiLlama APIs + SDK commit | VALID | SDK adapter path moved (404); recomputation noted | current emissions repo (Sec. 8) |
| Bybit REST instruments/funding/tickers | VALID AS INCREMENTAL SAMPLE | incremental; pagination not demonstrated | real pagination + archive files (Sec. 5) |

## Corrected conclusions vs original

1. **Binance backfill is feasible** — original said bulk zip 404 (CONDITIONAL). The error
   was the wrong host. Real archive objects at `data.binance.vision/data/.../daily/...`
   download HTTP 200, with provider CHECKSUM sidecars that **match** locally computed
   SHA-256. Binance is now `BACKFILL_PRIMARY` (historical) + `INCREMENTAL_PRIMARY` (REST).
2. **Timestamp precision boundary confirmed on real archive data** — spot aggTrades
   `transact_time` is **13-digit milliseconds** on 2024-12-31 and **16-digit microseconds**
   on 2025-01-01. This is an archive-file fact, not a REST inference (original used REST,
   which is also ms — did not isolate the µs boundary).
3. **Coin Metrics issued-supply metric is `SplyCur`, not `SplyIssued`** — original cited
   `SplyIssued` (which is unsupported in v4 timeseries). Confirmed via real timeseries:
   `btc` `SplyCur` ≈ 19.80M, `sushi` `SplyCur` ≈ 279.15M on 2025-01-01.
4. **Coin Metrics timeseries returns a FLAT `data` array** (`{asset,time,metric...}`), not
   the nested `{asset,series:[{metric,values}]}` shape the first pass assumed. Parsing was
   wrong, not the data.
5. **Kraken and OKX historical bulk hosts are unreachable from this environment** (DNS
   failure: `data.kraken.com`, `bulk-data-download.okx.com` do not resolve). This is a real
   access gap, not a code error. Their live REST remains reachable (incremental). Historical
   backfill for Kraken/OKX is `CONDITIONAL` pending host access.
6. **Bybit funding history is capped at the most-recent ≤100 events** (cursor `None` even
   with older windows) — true multi-page pagination demonstrated on `instruments-info`
   instead (cursor returns distinct page). Documented honestly.
7. **Methodological corrections** (Sec. 11): trades are canonical; REST reachability ≠
   backfill feasibility; current metadata ≠ security master; actual funding settlements
   determine cash flows; no factor becomes research-ready from this audit.

## Real historical-source acquisitions completed in this correction

- Binance archive: `BTCUSDT` spot aggTrades 2024-12-31 (1,218,370 rows), 2025-01-01
  (653,485 rows); spot klines 1m 2025-01-01 (1,440 rows); USD-M perp aggTrades 2025-01-01
  (726,612 rows); USD-M perp trades 2025-01-01 (1,804,361 rows); funding monthly 2025-01
  (94 rows). Provider CHECKSUM verified for 2025-01-01.
- Binance replacement register: `updates/2022-10-04_aggregate_trade_updates.csv` audited
  (old→new checksum per file).
- Bybit archive: `BTCUSD` inverse perp 2019-10-01 (4.0 MB gz), `BTCUSDT` linear perp
  2020-03-25 (121 KB gz) with real schemas.
- Coin Metrics timeseries: `btc`/`sushi`/`bonk` observations (3 assets, flat format, status
  via presence/absence; `community:true` flag).
- Bybit pagination: `instruments-info` cursor returns distinct second page.

## What remains a genuine gap (not an error)

- Kraken historical bulk files (host unreachable).
- OKX historical files (host unreachable).
- Tokenomist (TLS unreachable) — DIL-01 still blocked.
- DefiLlama emissions adapter current path (old SDK path 404; new repo located, Sec. 8).
