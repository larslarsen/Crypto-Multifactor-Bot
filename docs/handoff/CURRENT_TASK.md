# CURRENT_TASK

Ticket: DATA-012
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

## Summary

DATA-012 — Uniswap V2 PairCreated Event Ingestion (Ethereum Mainnet).
REVIEW-0228 corrections applied: import sort, tz fix, receipt identity migration 0010.

## Evidence

- `tickets/DATA-012.md`
- `docs/reviews/REVIEW-0228_DATA-012_CHANGES_REQUIRED.md`
- `src/cryptofactors/acquisition/uniswap_v2.py`
- `scripts/research/ingest_uniswap_v2_pair_created.py`
- `sql/migrations/0009_uniswap_v2_chunk_receipt.sql`
- `sql/migrations/0010_uniswap_v2_receipt_identity.sql`
