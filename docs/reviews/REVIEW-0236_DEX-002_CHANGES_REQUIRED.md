# REVIEW-0236 - DEX-002 CHANGES REQUIRED

**Ticket:** DEX-002 - Screened Free DEX OHLCV Acquisition
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Base commit:** `5ed8da1`
**Date:** 2026-07-26

## Findings

1. **Critical - the superseded publisher remains executable.**
   `scripts/research/dex_multi_provider_fanout.py` still runs the legacy
   `dex_fanout` implementation and can publish a separate PASS dataset without raw
   lineage or full-snapshot semantics. The legacy gate and watermark code also retain
   behavior prohibited by REVIEW-0235. Marking report 37 as superseded does not disable
   the code path that produced it.

2. **High - unresolved gaps are published as PASS.**
   `DexSnapshotEngine.acquire_pool()` records internal gaps but returns the bars as
   usable, and the runner publishes every returned bar with `QualityStatus.PASS` while
   merely counting `unresolved_gaps` in the summary. Missing intervals at the beginning
   and end of the requested range are not detected at all. A partial or gap-bearing
   response can therefore become canonical data.

3. **High - missing prior output silently becomes a delta replacement.**
   `load_prior_snapshot()` returns `(dataset_id, [])` when the catalog resolves a prior
   dataset but its Parquet output is missing. The next run then publishes only newly
   acquired rows as a purported full snapshot. Prior output identity, hash, row count,
   and row validity are not reconciled before merge.

4. **High - pool-address validation is not chain aware.**
   Any non-empty value that does not match the EVM regex is accepted as a non-EVM
   address. A malformed `0x...` value on an EVM chain is therefore accepted instead of
   failing closed.

5. **High - required controlled evidence is absent.**
   `research/sprint_004/44_DEX002_REWORK_REPORT.json` does not exist. The handoff points
   only to superseded report 37, so the controlled real-run acceptance criterion is not
   met.

6. **Medium - catalog reconciliation is asserted, not proven.**
   The runner discards the publisher result, resolves latest afterward, and records
   `catalog_reconciled: true` whenever any dataset ID is returned. It never compares the
   published ID to the resolved ID.

7. **Control-plane failure.**
   `CURRENT_TASK` says `AWAITING_REVIEW` while `tickets/DEX-002.md` remains `READY`.
   Repository control fails on this mismatch despite the handoff claiming PASS.

## Required corrections

1. Disable the legacy DEX-002 runner at its entry point or route it exclusively through
   the new snapshot implementation. It must be impossible to publish through the old
   path. Preserve old files only as non-executable historical compatibility if needed.
2. Treat any internal or requested-boundary gap as unresolved quality. If any pool that
   passed screening lacks exact requested coverage, publish no PASS dataset and advance
   no watermark. Add actual-runner tests for internal, leading, and trailing gaps.
3. Fail closed when a prior canonical dataset is missing, corrupt, hash-mismatched, or
   schema/row-count inconsistent. Validate restored rows before merge.
4. Validate pool addresses according to the configured chain family; malformed EVM
   addresses must not fall through as non-EVM identities.
5. Compare the publisher-returned dataset ID to `resolve_latest_by_type()` and record the
   exact reconciliation values.
6. Produce the required controlled real-run report 44 with pinned configuration, raw
   dependencies, full-snapshot coverage, watermarks, and matching catalog IDs.
7. Reconcile ticket/handoff state and run ticket tests, scoped Ruff, the complete suite,
   and repository control.

## Constraints

- No synthetic candles, Birdeye OHLCV, paid sources, DEX death/universe authority,
  factors, paper promotion, or LIVE.
- No work on DATA-008, DATA-009, or DEX-003.

## Next

- **Next required actor:** Sr Dev - Claude Opus 5
- **Next ticket authorized:** NONE
