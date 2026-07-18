# 04 — Point-in-Time Reference Reconstruction Plan

**Sprint:** 003
**Research cutoff:** 2026-07-18

This plan defines how to reconstruct listing, delisting, and delivery events as
point-in-time references, using the audited sources. Each event records: announcement
time, effective time, first trade, last trade, delivery/settlement time, source evidence,
and a confidence classification.

## Confidence classes

- `CONFIRMED_OFFICIAL` — exchange announcement / official docs state the time.
- `CONFIRMED_MARKET_DATA` — first/last trade or launchTime field directly observed from
  market data with no ambiguity.
- `INFERRED` — derived from market-data edges (e.g. first trade timestamp) without an
  official announcement.
- `CONFLICTED` — sources disagree on the time.
- `UNKNOWN` — no reachable evidence.

## Event types and preferred sources

| Event | Preferred source | Fallback | Confidence target |
|-------|-----------------|----------|-------------------|
| Listing (spot) | exchange announcement + first-trade | Kraken/OKX/Binance first aggTrade | CONFIRMED_OFFICIAL or CONFIRMED_MARKET_DATA |
| Listing (perp) | instruments-info launchTime | first perp aggTrade | CONFIRMED_MARKET_DATA |
| Delisting (spot) | exchange announcement + last-trade | last aggTrade before gap | CONFIRMED_OFFICIAL or CONFIRMED_MARKET_DATA |
| Delivery (perp) | instruments-info deliveryTime / funding interval | settlement timestamp | CONFIRMED_MARKET_DATA |
| Unlock (token) | on-chain vesting + project docs + governance | Tokenomist/Messari/DefiLlama emissions | CONFLICTED until cross-checked |

## Reconstructed exemplars from this audit (evidence only)

- **Binance BTCUSDT first trade of 2025** — `aggTrades` sample first `T` = 1735689600010 ms
  (2025-01-01T00:00:00.010Z). Classification: `CONFIRMED_MARKET_DATA` for the first-trade
  edge; this is an active pair, not a listing event, so announcement time = `UNKNOWN`
  (pair predates the sample window). Use only to demonstrate the timestamp-precision
  boundary (no T shift).
- **Bybit BTCUSDT linear perp launch** — `instruments-info.launchTime` = 1584230400000 ms
  (2020-03-15T00:00:00Z), `deliveryTime` = 0 (perpetual), `contractType` =
  LinearPerpetual. Classification: `CONFIRMED_MARKET_DATA` (launchTime field).
- **Bybit BTCUSD inverse perp** — `contractType` = InversePerpetual; volume in contracts.
  Classification: `CONFIRMED_MARKET_DATA` for instrument type; launch time via same field.
- **OKX BTC-USDT-SWAP** — `instruments.ctType` = linear, `ctVal` = 0.01 BTC. First funding
  in sample `fundingTime` = 1784246400000 ms (2026-07-16). Classification:
  `CONFIRMED_MARKET_DATA` for instrument + funding cadence.

## Delisting / delivery reconstruction procedure (per asset, per venue)

1. Pull `instruments-info` / catalog once per asset; record `launchTime`, `deliveryTime`,
   `state`. If `state` = delisted/settled, the effective time is the last observed
   `state` change or `deliveryTime`.
2. Scan `aggTrades` (or trades) for the first and last trade timestamps around the window;
   the last trade before a permanent gap is the `last_trade` edge (`CONFIRMED_MARKET_DATA`
   if gap is durable across subsequent polls).
3. Cross-check against the exchange announcement archive (official notice board) for the
   announcement time; if found, upgrade to `CONFIRMED_OFFICIAL`.
4. If market-data edges exist but no announcement, classify `INFERRED` and record the
   discrepancy.
5. If two venues disagree on the same asset's last trade, classify `CONFLICTED`.

## Token-unlock point-in-time requirement (DIL-01 gate)

For `DIL-01`, an unlock event must carry: announcement time, revision history, and actual
on-chain execution time. Per this audit, **Tokenomist was unreachable** and we **cannot
confirm that current public unlock charts preserve historical schedule vintages**. Until a
reachable source demonstrates vintage preservation (or on-chain vesting contracts are
queried directly), unlock events are `UNKNOWN`/`CONFLICTED` for point-in-time use. This is
the binding gap blocking `DIL-01` (see `06`/`09`).

## Net

Point-in-time reconstruction is feasible for exchange listing/launch/delivery via
instruments-info + market-data edges (`CONFIRMED_MARKET_DATA` achievable). Delisting edges
require polling + announcement cross-check. Token-unlock point-in-time remains blocked by
source-access and vintage-preservation uncertainty.
