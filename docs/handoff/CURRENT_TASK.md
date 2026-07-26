# CURRENT_TASK

Ticket: DATA-012
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

## Summary

DATA-012 — Uniswap V2 PairCreated Event Ingestion (Ethereum Mainnet).

Migrations 0009-0011 are unchanged; no schema change was required. The source
carries two corrections described below (69 tests total).

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

## Source changes

Two source corrections, decided by the Sr Dev under its senior-code-reasoning
remit and covered by 17 new tests that fail against the previous source.

1. **Typed failures on malformed input.** The ingestor leaked bare `KeyError`,
   `JSONDecodeError` and `ValueError` from twelve paths reachable by a malformed
   node response or a corrupt receipt row: absent log/header fields, a
   non-hex-string event topic, a log with no preserved header, a non-JSON body on
   an HTTP 200, a corrupt `header_raw_object_ids_json`, and an unparseable
   `completed_at`. These are indistinguishable from a programming fault at the
   call site and defeat the typed-error posture REVIEW-0227 through REVIEW-0230
   established. All now raise `UniswapV2IngestionError`, via a `_require` field
   accessor and a `_receipt_header_ids` parser.

2. **Removed the unreachable receipt-identity check** (previously lines 296-297).
   `replay_receipts` already filters `WHERE chain = ? AND factory = ? AND topic = ?`
   with those same values, so the in-loop check could never fire. It was not
   replaced by widening the query to reject overlapping foreign receipts:
   migration 0011 puts `factory` in the primary key precisely so several factories
   can share one receipt table, and rejecting on range overlap would make such a
   database unreplayable for either factory. The `WHERE` clause is the correct
   enforcement point.

## Evidence

- `tickets/DATA-012.md`
- `docs/reviews/REVIEW-0230_DATA-012_CHANGES_REQUIRED.md`
- `src/cryptofactors/acquisition/uniswap_v2.py`
- `scripts/research/ingest_uniswap_v2_pair_created.py`
- `sql/migrations/0009_uniswap_v2_chunk_receipt.sql`
- `sql/migrations/0010_uniswap_v2_receipt_identity.sql`
- `sql/migrations/0011_uniswap_v2_chunk_receipt_identity.sql`
- `tests/acquisition/test_uniswap_v2.py`
