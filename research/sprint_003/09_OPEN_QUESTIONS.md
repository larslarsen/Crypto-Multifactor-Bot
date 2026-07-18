# 09 — Open Questions

**Sprint:** 003
**Research cutoff:** 2026-07-18

1. **Binance bulk path** — Why did `data-api.binance.vision` return 404 from this
   environment on 2026-07-18? Is it host-specific, path-changed, or a transient outage?
   Does the provider-replacement checksum register validate re-pulled files? (SRC-002)

2. **Tokenomist reachability & vintage preservation** — Can `api.tokenomist.com` be reached
   from the data-acquisition host (TLS failed here)? If reachable, does it preserve
   historical unlock-schedule vintages, or only show current projections? This is the
   binding gap for `DIL-01`. (SRC-010)

3. **Kraken no-trade candles** — Do Kraken OHLC endpoints emit a zero-volume bar for
   intervals with no trades, or omit them? Reconcile reconstructed bars from trades against
   provider candles. (SRC-004)

4. **OKX/Bybit funding formula changes** — What are the exact effective dates of past
   `formulaType`/funding-interval changes? Store the formula/interval in force at each
   historical `fundingTime`. (SRC-005/SRC-006)

5. **Coin Metrics coverage for smaller assets** — `AdrActCnt` for SUSHI starts 2020-08-26;
   how do availability ranges behave for micro-cap assets, and does `community:true` flag
   indicate reduced quality? Does broad historical coverage need a Pro subscription?
   (SRC-007/SRC-012)

6. **DefiLlama recomputation drift** — How much do TVL/emissions values change after an
   adapter update at a pinned commit? Is a pinned-commit snapshot sufficient, or must we
   mirror adapter code? (SRC-008/SRC-009)

7. **On-chain publication vs block time** — For `NET-01`, what is the lag between block
   time and indexer publication, and how are revisions/backfills handled? Not queried this
   audit. (SRC-012)

8. **Cross-venue unit normalization** — Bybit inverse reports volume in contracts, not
   base; Kraken volume is in base while price is in quote; OKX `ctVal` varies. What is the
   canonical normalization for multi-venue turnover/cost aggregation? (SRC-004/SRC-005/SRC-006)

9. **Delisting last-trade durability** — How many polls / what gap duration upgrades a
   last-trade edge from `INFERRED` to `CONFIRMED_MARKET_DATA`? Define the polling SLA.
   (04_POINT_IN_TIME_REFERENCE_PLAN)

10. **Commercial procurement** — Which sources (Coin Metrics Pro/Atlas, Kaiko, Amberdata,
    Messari Pro, on-chain keys) require paid tiers, and what are their point-in-time /
    revision guarantees vs the free tiers audited here? (SRC-007/SRC-011/SRC-012)
