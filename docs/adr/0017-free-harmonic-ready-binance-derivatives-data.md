# ADR 0017 — Free Harmonic-Ready Binance Derivatives Data

- **Status:** Accepted
- **Date:** 2026-08-18
- **Supersedes:** ADR-0016 delivery scope and platform decision
- **Evidence:** `research/sprint_004/60_CEX_DATA_DESTINATION_DECISION.md`

## Context

ADR-0016 correctly stopped DEX work and rejected the invalid BitMEX funding products,
but it expanded the data objective into an institutional full-market reconstruction that
the Harmonic Trader design does not require. In particular, complete historical L2/BBO
and event-complete Binance liquidations became blocking prerequisites for all research.
That made an unaffordable commercial capture product appear mandatory.

The actual target model uses scale-invariant price geometry plus terminal-leg open-interest
change, funding state, and long/short liquidation imbalance. Its executable research
context additionally needs perpetual prices/trades, basis, fees, and honest cost evidence.
The example outcome horizon is expressed in daily bars; the design does not require an
incremental historical order book as an input feature.

Binance publishes free official USD-M archives for trades, klines, mark/index/premium
klines, five-minute metrics, and derived depth products, with checksums. Realized funding
history is available from the official USD-M API. Coinalyze's free API supplies
venue-specific daily open-interest, funding, OHLCV, and long/short liquidation histories
without deleting old daily observations. Binance's public liquidation stream has exposed
at most the latest liquidation per symbol per one-second interval since 2021-04-27, so a
publicly captured Binance liquidation series is an observed/censored flow, not an
event-complete liquidation tape. Buying a recorder of that public stream cannot restore
events the venue never published.

## Decision

### 1. Destination and work order

CEX-002 is the sole active ticket. It delivers a full-history, full-historical-membership,
Harmonic-ready Binance USD-M perpetual data release before any model development. It does
not run a price-only preliminary study and does not use the accepted 22-name DATA-011 panel
as its universe.

DEX-003 and CEX-001 remain preserved as `SUPERSEDED`. No DEX, factor, harmonic-model,
payoff, PAPER, or LIVE work begins before CEX-002 acceptance.

### 2. Required historical products

The release contains separate immutable products for:

1. historical USD-M perpetual membership and native identity;
2. source-granular trades and causally aggregated trade flow;
3. one-minute perpetual bars plus declared higher-timeframe views;
4. five-minute open interest and available positioning/taker metrics;
5. realized funding events, with indicative/premium data kept separate;
6. mark, index, premium, and basis observations;
7. observed Binance long/short liquidation aggregates, including the source's censorship
   semantics and an independent Coinalyze daily series;
8. effective fee schedules and all freely available Binance book/depth evidence used to
   calibrate spread/impact assumptions;
9. typed per-product gaps and a pinned cross-product bundle descriptor.

Acquisition covers every historically observed Binance USD-M perpetual contract in the
declared source interval, including delisted contracts. It may not use a fixed-N or current-
listing filter. The source-native products retain their available granularity. The first
full-history model-ready intersection is daily because the free third-party liquidation
history is retained indefinitely only at daily granularity. This matches the original
multi-day geometric design; it is not represented as event-complete liquidation history.

### 3. Prospective capture

The same ticket starts a resumable forward collector for official Binance trades, BBO/depth,
mark/funding, liquidation snapshots, and OI polling. Forward data never backfills a past
gap. The retained stream limitations remain part of the schema and quality state.

### 4. Platform boundary

This repository owns acquisition, raw provenance, normalization, reconciliation, gaps, and
immutable data releases. It does not build another trading engine. CEX-002 must prove that
its pinned release can be loaded into a clean NautilusTrader catalog, but strategy,
backtest, paper, and live development belongs to the Harmonic Trader project after data
acceptance. No Tardis integration or purchase is required.

### 5. Source and cost policy

No paid data purchase is authorized. Official Binance sources are primary authority.
Coinalyze is an explicitly attributed secondary aggregation source and must reconcile on
overlapping OI/funding/price fields before its liquidation aggregate is accepted. Its API
key is supplied only through `COINALYZE_API_KEY` and never stored in URLs, logs, receipts,
exceptions, reports, or repository evidence.

If a required free source is inaccessible or fails qualification, the precise product and
coverage become typed blocking evidence. The implementation must not silently substitute a
smaller universe, zeros, synthetic rows, or a different venue.

## Consequences

- The project acquires the complete data needed by the original geometric-plus-derivatives
  hypothesis before modeling.
- Historical full L2 and an impossible claim of uncensored Binance liquidation history no
  longer block the model-ready release.
- Real raw trades, OI, funding, basis, liquidation aggregates, costs, provenance, gaps,
  reconciliation, and resumability remain mandatory.
- The direct Nautilus boundary avoids further custom backtest/paper/live-engine work while
  leaving the data release usable outside Nautilus.
