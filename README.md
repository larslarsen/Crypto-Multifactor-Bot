# Crypto-Multifactor-Bot

## Structure

`src/` — production packages  
`tests/` — pytest suite  
`tickets/` — work ticket per deliverable  
`docs/` — review handoff records  

## Current review gate

Active tickets:  
- [`BIN-001`](tickets/BIN-001.md) — Binance archive kline normalizer (`ACCEPTED` at `b8813358`).  
- [`BAR-001`](tickets/BAR-001.md) — canonical bar publisher and daily reconciliation (`ACCEPTED` at integration commit `c10dd3a`; `docs/reviews/REVIEW-0042_BAR-001_ACCEPTED.md`).
- [`RES-001`](tickets/RES-001.md) — post-Sprint-003 research protocol reconciliation (`ACCEPTED` at `ff31763`; `docs/reviews/REVIEW-0043_RES-001_ACCEPTED.md`).
- [`BYB-001`](tickets/BYB-001.md) — Bybit public trade-archive normalizer (`ACCEPTED` at integration commit `f667c6d`; governing review chain REVIEW-0044→0050; `docs/reviews/REVIEW-0050_BYB-001_ACCEPTED.md`).
- [`EVD-001`](tickets/EVD-001.md) — Operational Evidence Registry (`ACCEPTED` at integration commit `6bd1f43`; evidence head `f774944`; `docs/reviews/REVIEW-0057_EVD-001_ACCEPTED.md`).
- [`AUD-004`](tickets/AUD-004.md) — Native headerless support for Binance archive precision comparator (`ACCEPTED`).
- [`AUD-005`](tickets/AUD-005.md) — Provider-candle comparison by explicit comparable dimensions (`ACCEPTED`; closed).
- [`RAW-002`](tickets/RAW-002.md) — Harden publication-receipt verification against symlink substitution (`ACCEPTED`).
- [`FX-001`](tickets/FX-001.md) — Point-in-Time Stablecoin FX readiness (`ACCEPTED`; implementation blocked by source authority).
- [`FX-003`](tickets/FX-003.md) — Kraken Bulk Stablecoin FX Source Semantics Audit (`ACCEPTED - NO_PRIMARY_SOURCE_AUTHORITY`).
- [`FUND-001`](tickets/FUND-001.md) — Binance Funding-Cashflow Readiness (`ACCEPTED`; source evidence required before implementation).
- [`FUND-002`](tickets/FUND-002.md) — Binance Funding Source Semantics Audit (`ACCEPTED - NO IMPLEMENTATION AUTHORITY`).
- [`FUND-003`](tickets/FUND-003.md) — OKX Funding Archive Source Semantics Audit (`ACCEPTED - NO_IMPLEMENTATION_AUTHORITY`).
- [`REF-003`](tickets/REF-003.md) — Bybit Prospective Instrument Snapshot Authority Audit (`ACCEPTED - NO_AUTHORITY`).
- [`FEE-001`](tickets/FEE-001.md) — Point-in-Time Fee Schedules and Conservative Assumptions (`ACCEPTED`; no numeric fee assumptions authorized).
- [`GOV-002`](tickets/GOV-002.md) — Repository Status Index Reconciliation (`ACCEPTED`; RECONCILIATION_COMPLETE, REVIEW-0119/0120/0121).
- [`DF-01`](tickets/DF-01.md) — Coin Metrics Point-in-Time Supply Authority Audit (`ACCEPTED - NO_PRIMARY_PIT_SUPPLY_AUTHORITY`; REVIEW-0122/0123/0124).
- [`DF-08`](tickets/DF-08.md) — Survivorship-Free Universe Source Authority Audit (`ACCEPTED - NO_SURVIVORSHIP_FREE_UNIVERSE_AUTHORITY`; REVIEW-0125/0126/0127).
- [`DF-02`](tickets/DF-02.md) — Point-in-Time Token Unlock Authority Audit (`ACCEPTED - NO_POINT_IN_TIME_UNLOCK_AUTHORITY`; REVIEW-0128/0129/0130/0131).
- [`DF-03`](tickets/DF-03.md) — Point-in-Time Funding Cashflow Authority Audit (`ACCEPTED - NO_POINT_IN_TIME_FUNDING_CASHFLOW_AUTHORITY`; REVIEW-0132/0133/0134).
- [`DF-07`](tickets/DF-07.md) — Point-in-Time On-Chain Observation Authority Audit (`IN_PROGRESS`; evidence synthesis, REVIEW-0135/0136).
