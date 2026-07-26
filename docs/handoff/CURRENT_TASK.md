# CURRENT_TASK

Ticket: DATA-012
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

## Summary

DATA-012 — Uniswap V2 PairCreated Event Ingestion (Ethereum Mainnet).

REVIEW-0231 rework complete. All six required corrections applied by Sr Dev —
Claude Opus 5, who owns source and tests for this ticket. 149 ticket tests pass;
each correction is mutation-checked (reverting it in the source fails a named test).

## REVIEW-0231 corrections

1. **Acquisition authentication.** Every `logs_acquisition_id`,
   `end_header_acquisition_id`, and per-dependency `acquisition_id` is reconciled
   against its `raw_acquisition` row: the row must exist, have status `SUCCEEDED`,
   name the same `raw_object_id`, carry the same canonical request, and record the
   same acquisition timestamp. A missing, orphaned, or contradictory record is
   refused. Applied on both replay and resume.
   → `_load_acquisitions`, `_authenticate_acquisition`, `TestAcquisitionAuthentication`

2. **Chain identity in receipt lineage (migration 0013).** `eth_chainId` is a
   preserved production acquisition, not a preflight. Its request, raw object,
   acquisition id and timestamp are recorded on every chunk receipt, surfaced in
   `ReplayResult.raw_object_ids` / `.acquisition_ids`, and re-verified offline from
   preserved bytes during replay.
   → `_verify_chain_lineage`, `TestChainLineage`

3. **Exact deployment start.** `start_block` must equal 10,000,835. A later start
   is refused before contacting the node.
   → `TestDeploymentBlock`

4. **Duplicate/conflicting header dependencies.** A block number appearing twice in
   `header_dependencies_json` is refused; two different hashes for one height is
   reported as a conflict.
   → `_receipt_from_row`, `TestHeaderDependencyConsistency`

5. **Unrelated housekeeping reverted.** The `.gitignore` `opencode.json` entry and
   the `opencode.json` deletion introduced by `da6cac8` are reverted forward.
   `opencode.json` is restored byte-identical to its pre-DATA-012 content
   (sha256 `92657c18…bff0`). The owner's `~/.config/opencode/opencode.json` was not
   read, written, or removed. Reverted forward rather than by rewriting pushed
   history, which would break any clone of `da6cac8`.

6. **Control-plane records committed and pushed.** The REVIEW-0231 record, ticket
   status and handoff were already committed in `b09e5fa`; this commit carries the
   rework and the state transition back to AWAITING_REVIEW.

## Defects found and fixed during self-audit

Three defects were found by auditing the integrated commit, independent of the
review items:

- The chunk-end block was requested twice whenever it also carried an event —
  one redundant round trip per chunk against a metered endpoint.
- `fetch(emit_rows=True)` returned `[]` for an already-complete range, which is
  indistinguishable from "this range has no events" and could publish an empty
  dataset. It now refuses and directs callers to `replay_receipts()`.
- Per-chunk decoding could not see an event repeated across a chunk boundary;
  `fetch` now applies a range-wide `(tx_hash, log_index)` check, matching replay.

A fourth was found by mutation testing: replay never bounded decoded events to the
receipt's own block range, so a repointed logs object could widen coverage.

## Evidence

- `tickets/DATA-012.md`
- `docs/reviews/REVIEW-0231_DATA-012_CHANGES_REQUIRED.md`
- `src/cryptofactors/acquisition/uniswap_v2.py`
- `scripts/research/ingest_uniswap_v2_pair_created.py`
- `sql/migrations/0012_uniswap_v2_receipt_binding.sql`
- `sql/migrations/0013_uniswap_v2_receipt_chain_lineage.sql`
- `tests/acquisition/test_uniswap_v2.py`
