# REVIEW-0238 - DEX-002 CHANGES REQUIRED

**Ticket:** DEX-002 - Screened Free DEX OHLCV Acquisition
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Base commit:** `92dc99d`
**Date:** 2026-07-26

## Findings

1. **Critical - full-snapshot raw lineage breaks on the third refresh.**
   The runner validates every prior row's `raw_object_id` against
   `catalog.list_raw_inputs(prior_dataset_id)`, which returns only direct raw inputs.
   An incremental publication declares current-run raw objects plus the prior dataset,
   but does not directly redeclare raw objects cited by rows carried forward from that
   prior snapshot. The second refresh succeeds because the first snapshot's rows are
   direct inputs. On the third refresh, first-snapshot rows remain in Parquet but their
   raw IDs are only transitively reachable through the prior-dataset chain, so restored
   row validation rejects them as undeclared. A normal daily refresh sequence therefore
   fails after two publications.

2. **High - `ALREADY_CURRENT` does not prove complete prior coverage.**
   `pool_covers_through()` returns true when the pinned end timestamp exists for the
   pool. It does not verify every interval from the configured default start through
   the pinned end. A prior snapshot with internal or leading gaps but an end bar can
   validate an `ALREADY_CURRENT` watermark and remain canonical.

## Required corrections

1. A published full snapshot must directly declare every raw object cited by every row
   in that snapshot, including carried-forward rows, in addition to current screening
   evidence and the prior dataset dependency. Verify those raw objects still exist.
   Alternatively, implement and test complete transitive lineage resolution; direct
   declaration is preferred because the snapshot is self-auditing.
2. Replace end-point-only coverage with exact interval coverage for each
   `ALREADY_CURRENT` pool from the run's configured default start through pinned end.
   Missing leading, internal, or trailing intervals must block publication.
3. Add an actual-runner test covering at least three consecutive incremental
   publications and proving all carried-forward row raw IDs remain declared.
4. Add tests where prior data contains the end bar but has leading/internal gaps;
   `ALREADY_CURRENT` must fail closed.
5. Repeat the controlled run, update report 44, and run ticket tests, scoped Ruff, the
   complete suite, and repository control.

## Closed from REVIEW-0237

Terminal acquisition states now block mixed-pool partial publication; DexScreener
screening is bound to chain and pair identity; DefiLlama uses validated token addresses;
and restored prior rows are revalidated for identity, bar invariants, provider
capability, duplicates, and direct lineage.

## Constraints

- No architecture rewrite. Correct only snapshot lineage closure and exact prior
  coverage proof.
- No synthetic candles, Birdeye OHLCV, paid sources, universe/death authority, factor
  work, paper promotion, or LIVE.

## Next

- **Next required actor:** Sr Dev - Claude Opus 5
- **Next ticket authorized:** NONE
