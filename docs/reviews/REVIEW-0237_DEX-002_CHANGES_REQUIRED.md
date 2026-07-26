# REVIEW-0237 - DEX-002 CHANGES REQUIRED

**Ticket:** DEX-002 - Screened Free DEX OHLCV Acquisition
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Base commit:** `b25b58b`
**Date:** 2026-07-26

## Findings

1. **High - a failed passed pool can ride into a PASS snapshot.**
   The runner blocks only acquisitions whose `has_unresolved_coverage` is true.
   HTTP/transport failure, invalid OHLCV, and zero-row outcomes return an error with
   no `missing_intervals` or internal gaps, so that property is false. If another pool
   has usable rows, the runner publishes the clean pool while silently omitting the
   screened-PASS pool that failed acquisition. Existing tests cover a clean pool plus
   a gap-bearing sibling, but not a clean pool plus a failed/empty/invalid sibling.

2. **High - authoritative screening is not bound to pool identity.**
   `DexScreenerScreeningProvider` uses the first returned pair without checking its
   `chainId` and `pairAddress` against the requested chain and canonical pool. Valid
   metrics for another pair can therefore admit the requested pool.

3. **Medium - DefiLlama context uses the wrong identity.**
   The coins endpoint is queried with `chain:pool_address`, but that endpoint expects
   token addresses. The controlled report consequently records zero matched coin
   prices. Context must use explicit base/quote token identities or report
   `CONTEXT_ONLY` without making a semantically invalid request.

4. **High - prior rows are not revalidated before canonical merge.**
   Prior file hash, row count, and column names are reconciled, but
   `bars_from_records()` only casts values into `OhlcvBar`. It does not reapply chain
   family/address validation, UTC daily alignment, finite/OHLC/volume constraints,
   provider capability, raw-object identity, or duplicate detection. REVIEW-0236
   explicitly required restored-row validation before merge.

## Required corrections

1. Give each screened-PASS acquisition an explicit terminal state. `FAILED`, `EMPTY`,
   `INVALID`, or `GAPPED` for any passed pool blocks the entire publication and all
   watermark changes. `ALREADY_CURRENT` is allowed only when verified prior canonical
   coverage proves that pool is complete through the pinned end. Add mixed-pool runner
   tests for clean plus HTTP failure, transport failure, invalid payload, and empty rows.
2. Require DexScreener `chainId` and `pairAddress` to match the requested canonical
   identity before metrics become authoritative. Missing or mismatched identity is
   `UNAVAILABLE`, never PASS or REJECT.
3. Carry optional base/quote token addresses in candidate input for DefiLlama context.
   Validate them by chain family. If absent, emit context-only evidence without an HTTP
   request; never query a token endpoint with a pool address.
4. Validate every restored prior row with the same invariants as newly decoded bars,
   reject duplicate identities, and verify each row's raw-object ID is declared by the
   prior dataset lineage before merge.
5. Repeat the controlled run and replace report 44 with evidence from the corrected
   implementation. Run ticket tests, scoped Ruff, the complete suite, and repo control.

## Closed from REVIEW-0236

The legacy runner is disabled; internal and boundary gaps block publication; prior
output files are hash/row reconciled; chain-family address validation is present; report
44 exists; and published/resolved catalog IDs are compared.

## Constraints

- No synthetic candles, Birdeye OHLCV, paid sources, DEX universe/death authority,
  factor work, paper promotion, or LIVE.
- No work on DATA-008, DATA-009, or DEX-003.

## Next

- **Next required actor:** Sr Dev - Claude Opus 5
- **Next ticket authorized:** NONE
