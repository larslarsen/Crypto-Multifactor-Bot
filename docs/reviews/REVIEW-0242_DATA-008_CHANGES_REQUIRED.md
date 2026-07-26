# REVIEW-0242 - DATA-008 CHANGES REQUIRED

**Ticket:** DATA-008 - Free CEX Universe Expansion (Binance-first)
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Base commit:** `b30dbc2`
**Date:** 2026-07-26

## Findings

1. **Critical - the controlled catalog reconciliation is false and pins the wrong
   base panel.** Report 36 declares additive dataset `ds_9624cffa...` registered and
   reconciled, but that ID is absent from the current `exp003.db`,
   `resolve_latest_by_type("binance_spot_daily_bars")` returns `None`, and no matching
   immutable dataset tree is present in `data/exp003_store`. The report also declares
   `ds_1f3e2633...` as its base because the runner resolves the latest `market_bars`;
   that is a 953,392-row BAR-001 dataset, not the accepted DATA-006 artifact
   `ds_7a0a1683...` with 90,276 rows. The additive evidence is therefore neither
   reproducibly cataloged nor anchored to the reviewer-authorized base.

2. **High - the result is not top N by 30-day volume over the target universe.** The
   runner first truncates candidates to a configurable top 60 using 24-hour ticker
   volume, then measures 30-day volume only for that subset. A symbol outside the
   24-hour cut can have higher trailing 30-day volume than a symbol inside it and can
   never enter the final ranking. `fetch_trailing_volume()` also labels any non-empty
   response as a `30d` observation without proving 30 unique, contiguous, closed daily
   bars over the pinned window.

3. **High - the persisted budget is a count, not a resumable cursor.** The runner loads
   `processed`, starts iteration again from the first ranked symbol, and immediately
   defers every symbol once the count reaches the limit; it never skips to the first
   unprocessed identity. It also keys the budget by the pinned market end date rather
   than the processing date. Report 36 was generated on July 26 but records budget day
   July 25. Re-running the same pinned window on a later processing day therefore does
   not reset or advance. The new test ignores the second runner return code and checks
   only that the stale count was reloaded, so it proves persistence but not progress.

4. **High - taxonomy and union reconciliation still misstate the published panel.**
   `RLUSD`, explicitly identified in REVIEW-0211 as a stablecoin-base omission, remains
   outside `STABLECOIN_BASES` and ranks fourth in the controlled report. History
   eligibility happens to defer it but does not correct its asset classification.
   Report 36 then calls all five selected symbols `added_symbols` and reports a logical
   union of 28, although `REUSDT` and `RLUSDUSDT` were deferred and the additive
   snapshot contains only three symbols (`ZECUSDT`, `BNBUSDT`, and `DEXEUSDT`). The
   consumer reconciliation must be derived from symbols actually present in the full
   additive snapshot, including carried-forward symbols on later refreshes, not from
   the current selection list.

5. **Medium - base-panel handling fails open and is not tested end to end.**
   `load_covered_symbols()` returns an empty set on reference-table errors, and the
   runner permits publication when no base dataset resolves. The new base-panel test
   deliberately uses a fresh store with no `market_bars` and accepts a null base ID;
   it does not seed the accepted DATA-006 dependency, verify exact base membership, or
   inspect the published dependency role as REVIEW-0241 required.

## Required corrections

1. Pin the exact accepted DATA-006 dataset ID `ds_7a0a1683...` through explicit
   configuration or a repository-controlled evidence binding; do not call
   `resolve_latest_by_type("market_bars")` for this decision. Fail closed if that
   dataset or its reconciled 23-symbol base membership is unavailable. Publish the
   additive artifact into the actual reviewed catalog/store and re-prove file, catalog,
   dependency, and resolve reconciliation from that same environment.
2. Measure and rank trailing 30-day quote volume for every symbol that survives the
   non-volume eligibility taxonomy. Remove the 24-hour rank truncation, or use 24-hour
   data only as a non-truncating observation. Validate exactly 30 unique, contiguous,
   closed daily bars at the pinned window before labeling evidence `30d`; otherwise
   record a terminal unavailable/insufficient-window reason.
3. Persist an identity-bearing cursor or queue and a real processing-day budget. Tests
   must run enough constrained passes to prove each deferred identity is eventually
   attempted exactly as intended, completed/current symbols do not consume the same
   slot forever, and the cursor changes only after the corresponding safe outcome.
4. Classify `RLUSD` and all other exchange-observed stablecoin bases before ranking.
   Separate selected, deferred, newly published, and carried-forward symbols. Compute
   disjointness, additive count, logical union count, and per-symbol spans from the
   published full snapshot plus the pinned DATA-006 base.
5. Add an actual-runner test with a seeded, pinned DATA-006 catalog artifact and inspect
   the additive dataset's direct `base_panel` dependency. Exercise missing/wrong base
   IDs and reference-table failures as fail-closed paths.
6. Include `prefilter_top_n`, capacity/cursor policy, pinned base ID, and other
   selection-controlling values in the effective configuration and fingerprint.

## Verification

- Focused DATA-008, legacy DATA-008, and DEX regression tests - PASS
- Complete repository pytest suite - PASS (6 skipped)
- Scoped and full ticket Ruff - PASS
- Repository control before decision routing - PASS
- The suite emitted the known non-blocking duplicate-ZIP-member warning in
  `tests/test_archives.py`.

Passing tests do not override the semantic and controlled-evidence failures above.

## Closed from REVIEW-0241

Historical kline pagination now covers ranges beyond 1,000 days while preserving each
page as raw evidence. Below-top-N candidates receive terminal reasons, the five named
taxonomy omissions from REVIEW-0241 are classified, net-row and global-span accounting
are implemented, and actual retry backoffs are recorded. Exact raw lineage,
full-snapshot publication, and post-publication watermark safety remain intact. Retain
these corrections.

## Architecture decision retained

DATA-006 remains immutable. DATA-008 continues as a separate additive
`binance_spot_daily_bars` dataset with a direct dependency on the accepted DATA-006
artifact. No `market_bars` publisher change, mass instrument mapping, or ownership of
unmapped Binance instruments is authorized.

## Next

- **Next required actor:** Sr Dev - Claude Opus 5
- **Next ticket authorized:** NONE
