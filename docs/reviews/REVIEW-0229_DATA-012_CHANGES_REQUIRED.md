# REVIEW-0229 — DATA-012 CHANGES REQUIRED

**Ticket:** DATA-012 — Uniswap V2 PairCreated Event Ingestion (Ethereum Mainnet)
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Date:** 2026-07-25

## Required source corrections

1. Make receipt identity include `(chain, factory, topic, start_block, end_block)`. Add a new migration; do not modify committed 0009/0010.
2. Make replay return: `ReplayResult(rows, raw_object_ids, completed_ranges)`. Include log responses, event-block headers, empty chunks, and end-block headers.
3. Set receipt `completed_at` to the maximum acquisition time of every required response.
4. Replace manual raw paths with validated content-addressed path helpers and verify SHA-256 before decoding.
5. Close the receipt database in `finally`.
6. Publish PASS only when replay proves contiguous requested coverage and includes every raw dependency.

## Constraints

- No tests yet.
- No Swap/Sync, OHLCV, universe building, Birdeye, Solana, factors, or LIVE.

## Next

- **Next required actor:** Sr Dev — Grok Build
- **Next ticket authorized:** NONE
