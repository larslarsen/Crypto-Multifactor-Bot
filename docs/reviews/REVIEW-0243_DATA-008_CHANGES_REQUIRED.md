# REVIEW-0243 - DATA-008 CHANGES REQUIRED

**Ticket:** DATA-008 - Free CEX Universe Expansion (Binance-first)
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Base commits:** `ee34529`, `dc504f6`
**Date:** 2026-07-27

## Findings

1. **Critical - the controlled dataset has false code identity.** The additive dataset
   and report reconcile to `ds_78b36bd8...`, and its output and the pinned DATA-006
   base are present with matching catalog hashes. However, the additive manifest records
   code commit `7a85bad`, which is the REVIEW-0242 routing commit before the source
   correction. The reviewed source first exists at `ee34529`; current HEAD is
   `dc504f6`. A dataset produced from uncommitted correction code cannot claim the
   pre-correction review commit and is not reproducible from its own lineage.

2. **High - the identity cursor still cannot make multi-day progress at a fixed daily
   limit.** Attempted identities are keyed by processing date plus pinned end time.
   When the processing date changes, the set resets and iteration starts from rank one.
   Already-current or history-deferred head symbols consume the new day's capacity
   again, so a limit of two can repeat the first two symbols every day and never reach
   rank three. On a run with only deferred/already-current outcomes, the early
   `no_publishable_rows` return also occurs before `save_attempted()`, so even same-day
   progress is lost. The test only increases the same day's limit from two to four; it
   does not exercise an actual date rollover, a constant limit, or a no-publication
   terminal pass.

3. **High - the 30-day validator proves timestamps, not closed bars.**
   `fetch_trailing_volume()` verifies exactly 30 aligned open timestamps but ignores
   each kline close timestamp and does not require the pinned end day to have closed by
   `outcome.acquired_at`. A run during the current UTC day can therefore include the
   still-forming final candle and label it a closed 30-day volume window. The controlled
   July 26 window was acquired after its close, but the shipped path does not enforce
   that property.

4. **Medium - the exclusion taxonomy changed without a version change.** RLUSD and
   additional stablecoin bases were added while `EXCLUSION_TAXONOMY_VERSION` remained
   `2026-07-26.1`. Earlier report 36 evidence under that same version allowed RLUSD into
   ranking; current evidence excludes it. Identical version labels now represent
   different classification rules, defeating the required audit comparison.

5. **Medium - base membership does not fail closed on partial corruption.**
   `load_base_panel_symbols()` reads declared Parquet files without comparing their
   hashes, sizes, or row counts to the catalog and silently skips missing or unreadable
   files. It succeeds whenever the remaining files happen to expose all 23 instrument
   IDs. The current reviewed base is intact (all 160 files independently hash-match),
   but a later partial store corruption could be accepted as reconciled membership.

6. **Low - stale controls obscure the actual ranking contract.** The runner still
   exposes unused `--prefilter-top-n`, and module/runner documentation still describes
   24-hour prefilter ranking although 24-hour data no longer truncates the field.
   Remove the dead option and include the pinned range plus cursor policy in the
   effective configuration/fingerprint so the published run identity states every
   selection-controlling value.

## Required corrections

1. Make source changes first, commit them, then repeat the controlled publication with
   that real commit (or current integrated HEAD) as `CodeIdentity`. Report the code
   commit and prove it equals the catalog manifest. Push the complete candidate before
   rereview.
2. Separate the persistent queue/cursor for a pinned selection from the per-processing-
   day request counter. A new day must reset capacity without resetting queue position.
   Persist safe terminal progress even when no dataset publication is needed, while
   failed/blocking acquisition outcomes remain retryable and do not advance.
3. Add constant-limit, multi-day tests with an injectable processing clock. Prove every
   queued identity is eventually attempted, already-current/deferred identities do not
   starve later ranks, and all-terminal/no-publication runs preserve canonical data
   while retaining safe cursor progress.
4. Validate kline close timestamps and require every ranking bar, especially the final
   one, to be closed at acquisition time. Add a test for a current, still-forming daily
   bar with otherwise correct open timestamps.
5. Bump the taxonomy version for the RLUSD/additional-stablecoin rule change and repeat
   report 36 under the new version.
6. Reconcile all declared base files against catalog hash, size, and row count before
   deriving membership, or validate the canonical manifest/tree through an equivalent
   strict helper. Add partial-missing and tampered-file tests where other files still
   contain all expected instrument IDs.
7. Remove the unused prefilter limit and stale 24-hour-ranking documentation. Include
   `default_start`, pinned end, base ID, budget/cursor policy, and other material run
   controls in the effective configuration and fingerprint.

## Verification

- Focused DATA-008, legacy DATA-008, and DEX regression tests - PASS
- Complete repository pytest suite - PASS (6 skipped)
- Scoped and full ticket Ruff - PASS
- Repository control before decision routing - PASS
- Controlled additive catalog/file reconciliation - PASS
- Pinned DATA-006 catalog/file reconciliation: 160/160 files - PASS
- The suite emitted the known non-blocking duplicate-ZIP-member warning in
  `tests/test_archives.py`.

## Closed from REVIEW-0242

The exact accepted DATA-006 artifact is pinned and directly declared as `base_panel`;
the controlled additive dataset now exists in the reviewed catalog/store; all eligible
symbols receive validated 30-open-time measurements without 24-hour truncation; RLUSD
is excluded; report union counts and per-symbol spans derive from the published full
snapshot; and base lookup fails on absent or unmappable membership. Pagination, exact
raw lineage, immutable full snapshots, net-row accounting, backoff reporting, and
watermark publication safety remain correct. Retain these changes.

## Architecture decision retained

DATA-006 remains immutable. DATA-008 remains a separate additive
`binance_spot_daily_bars` dataset. No `market_bars` publisher change, mass instrument
mapping, or ownership of unmapped Binance instruments is authorized.

## Routing

Use Claude Opus 5 for this bounded correction. Final acceptance still requires Sol
5.6 High because it controls quantitative universe ranking and canonical lineage; no
new architecture decision requires Sol Max.

## Next

- **Next required actor:** Sr Dev - Claude Opus 5
- **Next ticket authorized:** NONE
