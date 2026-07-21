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
- [`FX-002`](tickets/FX-002.md) — Stablecoin FX Source Feasibility Audit (`ACCEPTED`; no viable primary source, implementation remains blocked).
- [`FUND-001`](tickets/FUND-001.md) — Binance Funding-Cashflow Readiness (`ACCEPTED`; source evidence required before implementation).
- [`FUND-002`](tickets/FUND-002.md) — Binance Funding Source Semantics Audit (`IN_PROGRESS`; evidence only).
