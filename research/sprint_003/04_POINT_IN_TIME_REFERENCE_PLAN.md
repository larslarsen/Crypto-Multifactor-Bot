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

The exemplars below use real data acquired in this correction pass. Confidence classes:
`CONFIRMED_OFFICIAL` (announcement), `CONFIRMED_MARKET_DATA` (instrument field / first-last
trade), `INFERRED` (derived edge, no announcement), `CONFLICTED` (sources disagree on same
instrument+event), `UNKNOWN` (no reachable evidence). Different venues having naturally
different listing dates is NOT a conflict.

### Real reconstructed exemplars

| Venue | Instrument | Event | Announcement | Effective | First trade | Last trade | Delivery/settle | Source evidence | Confidence |
|-------|-----------|-------|-------------|-----------|-------------|------------|-----------------|-----------------|------------|
| Binance | BTCUSDT (spot) | first/last trade edges (active) | UNKNOWN | n/a | 1735689600010866 (2025-01-01T00:00:00.010Z, archive) | 1735775999658370 (archive 2025-01-01) | n/a | `data.binance.vision` spot aggTrades 2024-12-31 / 2025-01-01 | CONFIRMED_MARKET_DATA (active pair; not a listing event) |
| Kraken | XBTUSD (spot) | active (no listing edge in sample) | UNKNOWN | n/a | 1735689600.0975654 (REST Trades 2025-01-01) | 1735691765.8469803 | n/a | Kraken REST Trades XBTUSD | CONFIRMED_MARKET_DATA (active; listing predates sample) |
| OKX | BTC-USDT-SWAP | instrument active | UNKNOWN | n/a | first funding 1784246400000 (2026-07-16, funding history) | n/a | n/a | OKX `/public/instruments` ctType=linear, ctVal=0.01 BTC | CONFIRMED_MARKET_DATA (instrument metadata) |
| Bybit | BTCUSDT (linear perp) | LISTING | UNKNOWN | 1584230400000 (2020-03-15T00:00:00Z, launchTime) | 2020-03-25 (archive CSV.gz first file) | n/a | 0 (perpetual) | `instruments-info.launchTime` + `public.bybit.com/trading/BTCUSDT/` | CONFIRMED_MARKET_DATA (launchTime field; archive start corroborates) |
| Bybit | BTCUSD (inverse perp) | LISTING | UNKNOWN | ~2019-10-01 (first archive file) | 1569974394.557895 (2019-10-01T23:59:54Z, archive) | n/a | 0 (perpetual) | `public.bybit.com/trading/BTCUSD/BTCUSD2019-10-01.csv.gz` | INFERRED (first observed trade = earliest available; no launchTime pulled for this symbol) |
| Bybit | BTCUSDU26 (inverse futures) | DELIVERY/SETTLEMENT | UNKNOWN | 1790323200000 (deliveryTime) | n/a | n/a | 1790323200000 (contractType InverseFutures, deliveryTime>0) | `instruments-info` inverse BTCUSDU26 | CONFIRMED_MARKET_DATA (deliveryTime field; differs from perpetual deliveryTime=0) |

### Notes

- Binance BTCUSDT is an active pair; the archive first/last-trade edges confirm
  timestamp-precision behavior and continuous trading, not a listing. Announcement time is
  `UNKNOWN` (pair predates the audit window).
- Bybit BTCUSDT `launchTime` = 2020-03-15 is a genuine LISTING event recorded from the
  instrument field (`CONFIRMED_MARKET_DATA`); the 2020-03-25 archive file independently
  corroborates the pair existed by then.
- Bybit BTCUSDU26 is a delivered forward contract: `contractType=InverseFutures` with
  `deliveryTime=1790323200000` (>0), explicitly contrasting the perpetual `deliveryTime=0`.
  This is a real DELIVERY exemplar.
- No `CONFLICTED` classification was required: all venues agree on their own instrument's
  events; cross-venue listing-date differences are expected, not conflicts.
- Kraken/OKX historical bulk files were unreachable (DNS), so their listing events could
  not be reconstructed from archive; only active-pair REST edges are available
  (`CONFIRMED_MARKET_DATA` for active status only).

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
