# REVIEW-0227 — DATA-012 CHANGES REQUIRED

**Ticket:** DATA-012 — Uniswap V2 PairCreated Event Ingestion (Ethereum Mainnet)
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Date:** 2026-07-25

## Required source corrections

1. Persist and validate completed `[start_block,end_block]` chunk receipts; resume by skipping verified chunks only.
2. Add a pure decoder that replays pinned raw objects deterministically.
3. Publish sorted Parquet through DatasetPublisher; no mutable NDJSON output.
4. Preserve HTTP error responses before raising.
5. Record both log and block-header raw object IDs, use their recorded acquisition times, and verify log block hash equals header hash.
6. Close owned HTTP clients.

## Constraints

- Do not add tests yet.
- No Swap/Sync, OHLCV, universe building, Birdeye, Solana, factors, or LIVE.

## Next

- **Next required actor:** Sr Dev — Grok Build
- **Next ticket authorized:** NONE
