# CEX Data Destination Decision

Date: 2026-08-18

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **ACQUIRE THE COMPLETE FREE HARMONIC-READY DATASET FIRST**

## Correction

The platform recommendation in `59_CEX001_SOURCE_AND_PLATFORM_REVIEW.md` incorrectly
treated the deliberately staged price-only G1 study as the destination and presented an
unaffordable full historical capture product as the alternative. That recommendation is
withdrawn. The source-code rejection findings in record 59 remain valid; its reduced
proof-of-life/platform choice does not.

The design source `Harmonic_Trader/research/autonomousgemetricdiscovery.md` defines the
actual input vector as price geometry plus terminal-leg open-interest change, funding
state, and cumulative long/short liquidation imbalance. The model needs real derivatives
data before development. It does not require full incremental historical L2 as a feature.

## Free source determination

### Binance

Binance's official public-data project documents free daily/monthly USD-M archive objects,
all-symbol support, next-day daily publication, checksums, trades, aggregate trades, and
klines. Direct source inspection additionally established USD-M archive families for
five-minute metrics, mark/index/premium klines, book depth, and book ticker. The official
funding-rate endpoint supplies realized funding history.

Primary references:

- https://github.com/binance/binance-public-data
- https://data.binance.vision/
- https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History
- https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Liquidation-Order-Streams

### Liquidation limitation and Coinalyze

The Binance force-order stream publishes only the latest liquidation order for a symbol
within each 1,000 ms interval. Coinalyze independently notes that Binance stopped providing
full liquidations on 2021-04-27 and thereafter provides one liquidation order per second.
Therefore public-source historical Binance liquidation data is censored by venue
publication; it cannot honestly be called an event-complete tape even if bought from a
recorder.

Coinalyze's official API is free at 40 calls/minute. It exposes venue-specific liquidation
history as timestamped long and short values. It retains only roughly 1,500–2,000 points
for intraday intervals but does not delete old daily observations. Daily Binance
liquidation totals can therefore support the original multi-day terminal-leg imbalance,
provided price/OI/funding overlap is reconciled with official Binance sources and the
output is labeled `observed/censored` rather than `complete`.

Primary reference:

- https://api.coinalyze.net/v1/doc/

## Exact destination

CEX-002 acquires every historically observed Binance USD-M perpetual, not a fixed panel,
and publishes source-native trades, one-minute bars, five-minute OI/metrics, realized and
indicative funding, mark/index/premium basis, observed liquidation aggregates, cost
calibration evidence, typed gaps, and a pinned full-history daily intersection. It also
starts forward collection of the same public streams.

Full historical L2 is not purchased or manufactured. All freely available book/depth data
is retained for cost calibration, and live BBO/depth is captured prospectively. This is an
execution-evidence boundary, not a reduction of the Harmonic feature vector.

The repository remains the data/provenance authority. A clean NautilusTrader catalog-load
check proves the release is usable by the eventual trading project without continuing to
build a proprietary engine here. No model or payoff work begins under the data ticket.

## Cost decision

No paid data source is authorized. Expected monetary data-license cost is $0. Coinalyze
requires a free API key supplied out of band through an environment variable. Ordinary
local storage and bandwidth remain owner infrastructure costs and must be measured from a
complete archive inventory before bulk acquisition.

## Control disposition

- CEX-001: `SUPERSEDED`; rejected source remains preserved and unintegrated.
- CEX-002: `IN_PROGRESS`; sole active ticket.
- DEX-003: remains `SUPERSEDED`.
- Harmonic/model/PAPER/LIVE work: unauthorized until CEX-002 acceptance.

The first source-authoring drop is deliberately assigned to Codex Spark only for bounded
inventory/client/report plumbing with already fixed semantics. Senior review-hard work is
not spent until the free real-source matrix has been established.
