# REVIEW-0244 - DATA-008 CHANGES REQUIRED

**Ticket:** DATA-008 - Free CEX Universe Expansion (Binance-first)
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Base commits:** `a337431`, `3382501`, `bcd3e20`, `704ebc1`
**Date:** 2026-07-27

## Findings

1. **Critical - unavailable 30-day evidence can silently change the selected top N.**
   `fetch_trailing_volume()` returns the same `None` for a valid incomplete window, an
   exhausted HTTP failure, and malformed provider data. The runner classifies every
   such result as `INSUFFICIENT_VOLUME_WINDOW`, removes the symbol, and can publish a
   lower-ranked survivor. A transient failure for a genuinely high-volume symbol can
   therefore produce a biased canonical universe instead of blocking and remaining
   retryable. The report's failed-symbol fields do not expose this failure.

2. **High - 24-hour evidence still gates the supposedly full 30-day measurement
   field.** The first `select_symbols()` pass requires an entry in the 24-hour ticker
   map. A tradable symbol that survives the non-volume taxonomy but has no ticker entry
   is assigned `NO_VOLUME_EVIDENCE` and never receives the required trailing 30-day
   measurement. A low 24-hour value no longer truncates the field, but missing 24-hour
   evidence still does. This does not satisfy REVIEW-0242's requirement to measure
   every symbol that survives the non-volume taxonomy.

3. **High - a failed history-eligibility request is persisted as safe completion.**
   `fetch_history_eligibility()` maps an exhausted request or malformed payload to
   `HISTORY_UNKNOWN`. The runner then emits `DEFERRED` and unconditionally adds that
   symbol to the persistent attempted set. If another symbol publishes, or if the run
   has only non-blocking outcomes, that cursor is saved and the failed identity is
   skipped permanently for the pinned selection. This directly violates the
   REVIEW-0243 requirement that failed acquisition outcomes stay retryable and do not
   advance.

4. **High - mixed safe and blocking outcomes still lose safe cursor progress.** When a
   batch contains a valid history deferral followed by a blocking bar failure, the
   runner builds the correct in-memory attempted set but refuses to save any of it
   because `blocked` is non-empty. With a constant daily limit, the safe head identity
   and the failure repeat each day and later ranks can starve. The tests cover all-safe
   and all-blocking batches, not the required mixed case. Persist independently safe
   terminal outcomes; do not persist blocked identities or publishable rows whose
   publication was prevented.

5. **Medium - the persistent queue key omits selection-controlling configuration.** It
   contains only `default_start` and pinned end. Changing `min_history_days`, `top_n`,
   quote assets, volume floor, taxonomy, or base binding for the same date range reuses
   old attempted identities. For example, a symbol deferred under 365 history days is
   still skipped after an authorized change to zero days. Capacity and processing day
   must not reset queue progress, but material selection changes must identify a new
   queue.

6. **Low - the runner's module description still says it ranks observed 24-hour
   volume.** The implementation and controlled report rank trailing 30-day quote
   volume. This stale documentation was explicitly included in REVIEW-0243's cleanup.

## Required corrections

1. Split non-volume taxonomy filtering from evidence ranking so every discovered,
   tradable target symbol receives a 30-day measurement regardless of whether it has a
   24-hour ticker entry. Keep 24-hour data only as non-truncating observation evidence.
2. Return or propagate typed 30-day measurement outcomes. A successful but genuinely
   incomplete closed window may receive the terminal insufficient-window reason;
   transport/retry exhaustion and malformed responses must be reported as failures,
   block canonical publication, and remain retryable.
3. Preserve the distinction between a successful short/no-history observation and a
   failed or malformed history request. Only proven terminal deferrals may advance the
   queue. Unknown acquisition outcomes must block publication, appear in failure
   evidence, and remain pending.
4. Persist safe terminal cursor progress in mixed batches while retaining blocked and
   unpublished identities for retry. Add a constant-limit, date-rollover test with a
   safe deferral and a separate failed identity; prove the deferral is not repeated,
   the failure is retried, and no unpublished bars or watermarks are skipped.
5. Key queue progress by all material selection controls, while keeping processing day
   and daily capacity separate. Add a test proving a material eligibility/configuration
   change does not inherit stale terminal identities; changing only capacity must still
   preserve position.
6. Add actual-runner tests for a missing 24-hour ticker entry with valid 30-day bars, a
   failed 30-day request that would otherwise alter top N, and a failed history request.
   Fix the stale runner description.
7. Commit the source correction before repeating the controlled publication. Record
   the real code commit in report 36, prove it equals the catalog manifest, and push the
   complete candidate before rereview.

## Verification

- Focused DATA-008 tests - PASS
- Legacy DATA-008 and DEX shared-path regressions - PASS
- Complete repository pytest suite - PASS (6 skipped)
- Scoped and full ticket Ruff - PASS
- Repository control before decision routing - PASS
- Controlled additive catalog/file/report reconciliation - PASS
- Pinned DATA-006 reconciliation: 160/160 files, 90,276 rows - PASS
- The suite emitted the known non-blocking duplicate-ZIP-member warning in
  `tests/test_archives.py`.

Passing tests do not exercise the unavailable-evidence and mixed-cursor paths above.

## Closed from REVIEW-0243

The controlled additive artifact now has honest code identity: report 36 and catalog
manifest both record `bcd3e2071f6d34259e21a4aeb8a9bb1b1b415f98`, and commits after
that identity change only repository evidence and routing. The latest additive dataset
is `ds_676f8e9008dcf1b68a3e0eb690c0ef688b9d335394ef01d576ec63253354dbb2`;
its 9,027 rows, four symbols, per-symbol spans, 448 raw dependencies, output hash, and
direct DATA-006 base dependency reconcile.

Queue position now survives ordinary processing-day rollover, all-safe no-publication
passes retain progress, ranking bars require valid close timestamps and acquisition
after close, taxonomy version `2026-07-27.1` binds the changed rule set, all declared
base files fail closed on missing/hash/size/row-count mismatch, the dead prefilter limit
is removed, and material run controls appear in the effective configuration. Retain
these corrections.

## Architecture decision retained

DATA-006 remains immutable. DATA-008 remains a separate additive
`binance_spot_daily_bars` dataset anchored to exact accepted DATA-006 dataset
`ds_7a0a16834098aa336155bc5cd8085066e09c20343f5933c7017e508250a6c988`.
No `market_bars` publisher change, mass instrument mapping, or ownership of unmapped
Binance instruments is authorized.

## Routing

Use Sr Dev - Grok Build for this bounded failure-state and cursor correction, followed
by Jr Dev - Hermes for integration, tests, records, commit, and push. Final acceptance
still requires Sol 5.6 High because DATA-008 controls quantitative universe selection
and canonical lineage; no new architecture decision requires Sol Max.

## Next

- **Next required actor:** Sr Dev - Grok Build
- **Next ticket authorized:** NONE
