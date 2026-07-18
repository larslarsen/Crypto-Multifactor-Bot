# 00 — Audit Scope and Method

**Sprint:** 003 (data-source feasibility audit)
**Research cutoff:** 2026-07-18
**Prepared:** 2026-07-18

## Objective

Determine, from real bounded samples, whether the official/public data sources needed to
test the Sprint 002 factor families are **feasible, point-in-time correct, and licensed
for research use** — before any implementation ticket is opened.

## Environment

Normal project network environment (outbound HTTPS). No VPN, no API keys, no commercial
subscriptions were used. All fetches used official English-language endpoints. A bounded
fixture (Binance 1m kline, 5 rows) was stored only at `/tmp/s3audit/fixtures` and is NOT
committed.

## Vendors and datasets audited

- **Exchanges (market data):** Binance (spot + USD-M perp), Kraken (spot), OKX (spot +
  SWAP), Bybit (linear + inverse perp).
- **On-chain / metrics:** Coin Metrics Community API v4 (catalog + timeseries).
- **DeFi / TVL / emissions:** DefiLlama (chains, stablecoins, SDK adapters).
- **Token unlocks:** Tokenomist public API (attempted; see gap), DefiLlama emissions
  adapters, Messari (attempted; rate-limited).
- **Cross-source reconstruction:** listing/delisting/delivery events from market-data
  evidence plus official announcement references where reachable.

## Per-object record schema

For every downloaded/queried object: provider; source role; endpoint/path; request
parameters; retrieval UTC timestamp; HTTP status + relevant headers; provider checksum
(when available); locally computed SHA-256; compressed + decompressed byte size; row
count; earliest/latest event time; timestamp precision; field names/types; compression and
encoding; duplicate/ordering behavior; missing-interval semantics; licensing/terms location;
whether the object may be corrected/replaced later.

## Acquisition approach

Each vendor was queried with the minimal parameters needed for a bounded sample
(`limit` small, short date windows around 2025-01-01). The Binance **bulk daily-zip**
historical endpoint (`data-api.binance.vision`) returned HTTP 404 from this environment;
live REST was used instead and the bulk path is recorded as a `CONDITIONAL` backfill source
with the access limitation noted. All 40 acquisition records (with SHA-256) are persisted at
`/tmp/s3audit/ALL_ACQ.json` and summarized in `02_SOURCE_OBJECT_INVENTORY.csv`.

## What "feasible" means here

A source is feasible if: (a) a bounded official sample was retrievable; (b) its schema and
timestamp semantics are documented; (c) point-in-time availability/revision behavior is
understood or bounded by a stated condition; and (d) its terms permit non-redistributing
research use. Sources failing (a) are recorded as access gaps, not assumed usable.

## Limitations

- No historical bulk archives were downloaded (size/terms); only bounded live samples.
- TLS to `api.tokenomist.com` failed in this environment (recorded as an access gap).
- Messari returned HTTP 429 (no key); treated as `EXPLORATORY_PHASE2` conditional.
- Point-in-time listing/delisting reconstruction relies on market-data first/last-trade
  evidence plus announcement references; confidence is classified per event.
- No provider was paid; commercial tiers (Coin Metrics Pro, Kaiko, Amberdata, Messari Pro)
  were not evaluated beyond reachability.
