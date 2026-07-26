# CURRENT_TASK

Ticket: DATA-012
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

## Summary

DATA-012 — Uniswap V2 PairCreated Event Ingestion (Ethereum Mainnet).

Production source and migrations 0009-0011 are unchanged from the REVIEW-0230
corrections; no further source change was required to satisfy the ticket.

The obsolete 13-test suite was replaced with 52 tests exercising the finished
implementation and its runner. The previous suite passed vacuously: log fixtures
were not valid ABI encoding, so `pair` / `token0` / `token1` were never asserted;
REVIEW-0230 item 1 was covered only by `len(raw_object_ids) >= 3` on a scenario
with no empty chunk; item 2 had no test; item 3 exercised the private
`_read_raw_json` rather than `replay_receipts`; and the publication test
re-implemented the runner inline, leaving the runner and its `emit_rows=False`
acquisition mode uncovered.

Each REVIEW-0230 correction was mutation-checked: reverting it in the source
fails a named test. Same for the replay gap checks, resume end-block
reverification, and decoder ordering.

## Open reviewer decision

`src/cryptofactors/acquisition/uniswap_v2.py:296-297` is unreachable.
`replay_receipts` already filters `WHERE chain = ? AND factory = ? AND topic = ?`
with those same values, so the in-loop identity check cannot fire. Behaviour is
correct either way (foreign receipts are excluded by the query), so no test
asserts the dead branch. Options: delete it, or widen the query to all receipts
overlapping the block range and let the check reject foreign ones — the latter
appears closer to REVIEW-0229 item 1 intent. Not changed pending review.

## Evidence

- `tickets/DATA-012.md`
- `docs/reviews/REVIEW-0230_DATA-012_CHANGES_REQUIRED.md`
- `src/cryptofactors/acquisition/uniswap_v2.py`
- `scripts/research/ingest_uniswap_v2_pair_created.py`
- `sql/migrations/0009_uniswap_v2_chunk_receipt.sql`
- `sql/migrations/0010_uniswap_v2_receipt_identity.sql`
- `sql/migrations/0011_uniswap_v2_chunk_receipt_identity.sql`
- `tests/acquisition/test_uniswap_v2.py`
