# ADR 0017 — Free Harmonic-Ready Binance Derivatives Data

- **Status:** Accepted
- **Date:** 2026-08-18
- **Amended:** 2026-08-20
- **Supersedes:** ADR-0016 delivery scope and platform decision
- **Evidence:** `research/sprint_004/60_CEX_DATA_DESTINATION_DECISION.md` and
  `research/sprint_004/98_CEX002_RESOLUTION_AND_STORAGE_ARCHITECTURE_REVIEW.md`

## Context

ADR-0016 correctly stopped DEX work and rejected the invalid BitMEX funding products,
but it expanded the data objective into an institutional full-market reconstruction that
the Harmonic Trader design does not require. In particular, complete historical L2/BBO
and event-complete Binance liquidations became blocking prerequisites for all research.
That made an unaffordable commercial capture product appear mandatory.

The actual target model uses scale-invariant price geometry plus terminal-leg open-interest
change, funding state, and long/short liquidation imbalance. Its executable research
context additionally needs hourly perpetual OHLCV, basis, fees, and honest cost evidence.
The example outcome horizon is expressed in daily bars. Neither individual trades nor an
incremental historical order book is an input to the declared model vector.

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
2. native one-hour perpetual bars;
3. one-hour volume and taker flow derived from the bar source's total and taker-buy
   base/quote volume fields;
4. five-minute open interest and available positioning/taker metrics;
5. realized funding events, with indicative/premium data kept separate;
6. mark, index, premium, and basis observations;
7. observed Binance long/short liquidation aggregates, including the source's censorship
   semantics and an independent Coinalyze daily series;
8. effective fee schedules and a frozen, outcome-blind Binance book-ticker/depth sample
   used to calibrate spread/impact assumptions;
9. typed per-product gaps and a pinned cross-product bundle descriptor.

Acquisition covers every historically observed Binance USD-M perpetual contract in the
declared source interval, including delisted contracts. It may not use a fixed-N or current-
listing filter. The first full-history model-ready intersection is daily because the free
third-party liquidation history is retained indefinitely only at daily granularity. This
matches the original multi-day geometric design; it is not represented as event-complete
liquidation history.

Individual `trades` and `aggTrades` archives are not historical release inputs. A complete
tick tape is not needed to calculate the declared feature vector, and native Binance klines
already contain the total and taker-buy volumes required for hourly taker imbalance. Full
historical `bookTicker` and `bookDepth` archives are also not release inputs. Discovery may
list any official archive family to find candidate contract names without thereby making
every listed object an acquisition requirement.

For klines and every other family offered in both monthly and daily packaging, the release
selects one raw representation for each economic interval. A checksum-valid monthly object
is canonical for a completed month. Daily objects are selected only for days not represented
by an accepted monthly object, including the current tail or an explicit monthly gap. The
plan, manifest, storage report, and normalizer must reject overlapping selected coverage.
If a monthly object later fails integrity or economic validation, it remains quarantined
evidence and an explicit daily fallback may replace it; it never becomes a second consumable
copy of the same interval.

Cost calibration is a separate bounded evidence product, not a historical book feature.
Before outcomes are inspected, its immutable sample plan selects the first, chronological
midpoint, and last available whole-day object from each of `daily/bookTicker` and
`daily/bookDepth` for each accepted contract wherever those families exist. Missing objects
become typed gaps. Gate 1 reports the exact sample bytes before download; if the complete
declared sample does not fit the accepted resource envelope, it blocks for reviewer redesign
rather than silently shrinking. The resulting product supports cost sensitivities, not a
claim of exact historical fills.

### 3. Prospective holdout

CEX-002 records and pins a prospective holdout boundary before model outcomes are inspected.
It does not build a live trade, BBO, depth, liquidation, or OI streaming collector. That
operational work is premature until the historical research establishes tradability and
requires a later ticket. Data retrieved after the boundary retains its real retrieval and
source-availability semantics and never masquerades as an earlier vintage.

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

Explicit source gaps do not erase a contract from historical membership. They exclude only
the affected contract/interval from a product intersection. In particular, an affirmative
Coinalyze non-mapping is a typed liquidation-coverage gap, not a failure of the qualified
source and not permission to invent zero liquidations.

### 6. Storage and acquisition planning

Gate 1 storage is calculated from the selected, non-overlapping acquisition manifest, not
from every object discovered in every archive family. The preflight must separately report:

1. selected compressed raw bytes, including the complete frozen cost sample;
2. a conservative normalized/catalog bound derived from retained real samples;
3. temporary high-water space for the largest atomic download and normalization unit; and
4. an operating reserve that remains free throughout acquisition.

No bulk acquisition begins unless their sum fits the measured destination. Listing bytes,
unselected cadence copies, unselected trades, and unselected book archives are reported as
inventory facts but are not counted as required release storage.

The revised source-qualification run first establishes exact selected raw and cost-sample
bytes. Until bounded sample normalization measures items 2 through 4, they remain explicitly
`unknown` and storage sufficiency remains unproved. A developer must not invent a multiplier
or declare Gate 2 feasible merely because selected raw bytes fit.

## Consequences

- The project acquires the complete data needed by the original geometric-plus-derivatives
  hypothesis before modeling.
- Historical full L2 and an impossible claim of uncensored Binance liquidation history no
  longer block the model-ready release.
- Real hourly bars and taker flow, OI, funding, basis, liquidation aggregates, bounded cost
  evidence, provenance, gaps, reconciliation, and resumability remain mandatory.
- The 8.66 TB all-object estimate in CEX-002 review 97 is not an acquisition requirement;
  it measured the superseded tick/book scope and overlapping daily/monthly packaging.
- The direct Nautilus boundary avoids further custom backtest/paper/live-engine work while
  leaving the data release usable outside Nautilus.
