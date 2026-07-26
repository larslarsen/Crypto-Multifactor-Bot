# REVIEW-0230 — DATA-012 CHANGES REQUIRED

**Ticket:** DATA-012 — Uniswap V2 PairCreated Event Ingestion (Ethereum Mainnet)
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Date:** 2026-07-25

## Required source corrections

1. Build `ReplayResult.raw_object_ids` from every receipt's `logs_raw_object_id` plus every ID in `header_raw_object_ids_json`, including empty chunks and end-block headers.
2. Close the fetch receipt database in `finally`.
3. Wrap both raw-byte reading and `json.loads()` so invalid raw JSON raises `UniswapV2IngestionError`.

## Constraints

- No tests yet.
- No Swap/Sync, OHLCV, universe building, Birdeye, Solana, factors, or LIVE.

## Next

- **Next required actor:** Sr Dev — Grok Build
- **Next ticket authorized:** NONE
