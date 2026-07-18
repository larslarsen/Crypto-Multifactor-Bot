# Source note — Bybit

**Role:** REFERENCE_METADATA (instruments, tickers) / COST_CALIBRATION (funding)
**Audit date:** 2026-07-18

## Samples acquired
- Tickers linear `BTCUSDT`: sha de7b7b60…; turnover24h=2.99e9 (quote), volume24h=47230 (base).
- Instruments-info linear `BTCUSDT`: sha e814decf…; launchTime=1584230400000 (2020-03-15), deliveryTime=0, contractType=LinearPerpetual.
- Funding history linear `BTCUSDT`: 10 rows, sha da881260…; fundingRateTimestamp ms-epoch; nextPageCursor present.
- Instruments-info inverse `BTCUSD`: sha 71c5d8e5…; contractType=InversePerpetual.

## Schema / semantics
- `launchTime`, `deliveryTime`, `contractType`, `fundingInterval` are explicit fields →
  enable CONFIRMED_MARKET_DATA listing/delivery reconstruction.
- Funding history is **cursor-paginated** (`nextPageCursor`); must walk fully.
- Tickers carry `turnover24h` (quote) and `volume24h` (base).

## Unit divergence (critical)
- **Linear:** volume in base asset, turnover in quote.
- **Inverse:** volume in **contracts**, not base (BTCUSD inverse). Normalization required
  before any cross-venue aggregation (Open Question 8).

## Timestamp precision
Millisecond epoch UTC.

## Licensing
Public v5 market endpoints usable for research; review Bybit API terms.

## Gaps
- Linear vs inverse volume-unit normalization must be implemented and tested.
- Funding interval field should be snapshotted per instrument over time.
