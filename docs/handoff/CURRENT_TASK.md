# CURRENT_TASK

Ticket: DATA-012
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

## Summary

DATA-012 — Uniswap V2 PairCreated Event Ingestion (Ethereum Mainnet).
REVIEW-0230 corrections applied. 13 tests added covering migrations, acquisition,
replay, dedup, integrity checks, and publication.

## Evidence

- `tickets/DATA-012.md`
- `docs/reviews/REVIEW-0230_DATA-012_CHANGES_REQUIRED.md`
- `src/cryptofactors/acquisition/uniswap_v2.py`
- `scripts/research/ingest_uniswap_v2_pair_created.py`
- `sql/migrations/0009_uniswap_v2_chunk_receipt.sql`
- `sql/migrations/0010_uniswap_v2_receipt_identity.sql`
- `sql/migrations/0011_uniswap_v2_chunk_receipt_identity.sql`
- `tests/acquisition/test_uniswap_v2.py`
