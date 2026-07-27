# REVIEW-0245 - DATA-008 CHANGES REQUIRED

**Ticket:** DATA-008 - Free CEX Universe Expansion (Binance-first)
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer - Sol 5.6 High
**Base commits:** `5a03f25`, `5513d23`, `26cfb35`, `843de6f`
**Date:** 2026-07-27

## Findings

1. **Critical - the controlled artifact predates the final reviewed source.** Report
   36 and additive manifest consistently record
   `5513d23a1a3ba32d40e8d11a20219fbb2ed9a6db`, but current integrated HEAD is
   `843de6f`. The later commit changes the DATA-008 runner, snapshot code, shared raw
   HTTP code, tests, and another acquisition module. The artifact remains reproducible
   from `5513d23`, but it does not exercise or prove the source now proposed for
   acceptance. The runner also accepts `--code-commit` verbatim, and the test proves
   report/manifest equality with forty zeroes rather than proving the declared commit
   is the source actually executing. This leaves the same false-identity path that
   caused REVIEW-0243.

2. **Critical - a coverage-invalid `ALREADY_CURRENT` identity is persisted as safe.**
   The runner adds `ALREADY_CURRENT` to `attempted` before checking the prior canonical
   snapshot. If a watermark says current but prior rows do not cover the effective
   range, the first run blocks, then saves that identity in the mixed-batch cursor.
   Later runs skip it and can publish while its coverage remains unresolved. Existing
   tests cover only an `ALREADY_CURRENT` identity whose prior coverage is valid.

3. **Critical - malformed close timestamps can still bias top-N selection.** A close
   timestamp that differs from `open + one day - 1 ms` is classified together with a
   structurally valid still-forming bar as `INCOMPLETE_WINDOW`. The runner treats that
   as terminal `INSUFFICIENT_VOLUME_WINDOW` and may publish a lower-ranked survivor.
   Non-finite timestamps can also escape through `int()` as an untyped exception. Only
   a structurally valid bar observed before its declared close is incomplete; malformed
   timestamps are failed evidence and must block publication.

4. **High - malformed successful history responses are not reliably failed.** The
   earliest-bar parser accepts fractional, non-day-aligned, and future timestamps.
   Non-finite or out-of-range values can raise conversion exceptions outside the typed
   failure path, while a future timestamp becomes negative history and is persisted as
   terminal `INSUFFICIENT_HISTORY`. Provider success does not make malformed evidence
   a safe deferral.

5. **Medium - failed history observations are still reported as deferrals.**
   `build_report()` puts every ineligible `HistoryEligibility` in `deferred_symbols`,
   including `HISTORY_REQUEST_FAILED`, even though the matching acquisition is also
   failed and blocking. The actual-runner regression checks only
   `deferred_symbols_this_run`, so this contradictory report field is unprotected.

6. **Medium - queue identity still has no explicit selection-policy/source version.**
   The new fingerprint correctly excludes capacity and includes scalar selection
   controls, but corrected selection or eligibility semantics under the same config
   inherit old terminal identities. The configurable evidence endpoint is also absent.
   Use an explicit versioned policy/source identity rather than the Git commit, so
   semantic changes reset the queue without resetting it for unrelated code changes.

7. **Low - 30-day evidence reports bar count as trade count.** Successful measurement
   sets `trade_count=len(seen)`, making every complete window report 30 instead of
   validating and aggregating Binance's per-kline trade-count field. Report 36 therefore
   presents a misleading evidence attribute even though ranking itself uses quote
   volume.

## Required corrections

1. Add an identity to the attempted cursor only after its terminal safety is proven.
   For `ALREADY_CURRENT`, reconcile prior canonical coverage first; a coverage-invalid
   identity must remain pending. Add a two-run regression proving it is not skipped.
2. Validate ranking timestamps as finite whole milliseconds. Classify an invalid close
   interval as failed evidence; classify only a structurally valid bar whose close is
   not yet observable as incomplete. Add actual-runner tests proving malformed closes
   block publication and still-forming valid bars remain terminally insufficient.
3. Strictly validate earliest-history timestamps as finite, integral, UTC-day-aligned,
   and not after the pinned `as_of`. Convert every malformed successful response into
   `HISTORY_REQUEST_FAILED`, keep it pending, and test the runner path.
4. Exclude failed eligibility observations from all deferred report fields. Preserve
   mutually consistent selected, excluded, deferred, failed, and blocking evidence.
5. Add a versioned selection/eligibility policy and provider-source identity to the
   persistent queue key. Bump it for this semantic correction. Keep daily capacity and
   processing day excluded so ordinary multi-day progress remains intact.
6. Validate and aggregate actual per-kline trade counts for the 30-day evidence, or
   remove/rename the field so it cannot claim trades while containing bar count.
7. Harden controlled code identity. A production publication must fail if its declared
   commit differs from the checked-out commit or relevant source is dirty. Tests may
   inject identity through a test seam, but must not prove the production path with a
   fabricated commit. Commit all source first, then repeat report 36 under that exact
   clean commit and prove report, manifest, and reviewed source identity agree.

## Verification

- Focused DATA-008 tests - PASS
- Legacy DATA-008 and DEX shared-path regressions - PASS
- Complete repository pytest suite - PASS (6 skipped)
- Scoped and full ticket Ruff - PASS
- Targeted mypy over six changed source modules - PASS
- Repository control before decision routing - PASS
- Controlled additive catalog/file/report reconciliation - PASS at `5513d23`
- Pinned DATA-006 reconciliation: 160/160 files, 90,276 rows - PASS
- The suite emitted the known non-blocking duplicate-ZIP-member warning in
  `tests/test_archives.py`.

Passing tests do not cover the malformed-close, malformed-history, or invalid
`ALREADY_CURRENT` cursor paths above. Controlled reconciliation at `5513d23` does not
prove current HEAD `843de6f`.

## Closed from REVIEW-0244

The runner now measures every non-volume-taxonomy survivor even when its 24-hour ticker
entry is absent. Exhausted 30-day HTTP requests and malformed response containers are
typed as failures and block publication. Failed history HTTP requests remain pending.
Safe history deferrals persist through mixed blocking batches while unpublished rows
and failed identities remain retryable. Scalar material selection controls identify
the queue independently of daily capacity, and the stale 24-hour-ranking description
is corrected. Retain these changes.

The current controlled additive dataset
`ds_72faed1a84bd26981751703f66bdaca4c14a4973649497a378d007285cc0b62c`
also reconciles internally: 9,027 rows, four symbols, matching report spans, 448 raw
dependencies, one matching output file, and the direct exact DATA-006 base dependency.

## Architecture decision retained

DATA-006 remains immutable. DATA-008 remains a separate additive
`binance_spot_daily_bars` dataset anchored to exact accepted DATA-006 dataset
`ds_7a0a16834098aa336155bc5cd8085066e09c20343f5933c7017e508250a6c988`.
No `market_bars` publisher change, mass instrument mapping, or ownership of unmapped
Binance instruments is authorized.

## Routing

Use Sr Dev - Grok Build for this bounded validation, cursor, and code-identity
correction, followed by Jr Dev - Hermes for integration, tests, records, commit, and
push. The final acceptance review is explicitly assigned to **Sol 5.6 High** because
DATA-008 controls quantitative universe selection and canonical lineage. No new
architecture decision requires Sol Max.

## Next

- **Next required actor:** Sr Dev - Grok Build
- **Final reviewer:** Sol 5.6 High
- **Next ticket authorized:** NONE
