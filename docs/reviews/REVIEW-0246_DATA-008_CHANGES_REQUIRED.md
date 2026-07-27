# REVIEW-0246 - DATA-008 CHANGES REQUIRED

**Ticket:** DATA-008 - Free CEX Universe Expansion (Binance-first)
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer - Sol 5.6 High
**Base commit:** `2c571e4`
**Date:** 2026-07-27

## Findings

1. **Critical - the REVIEW-0245 source correction was not implemented.** Commit
   `2c571e4` changes only report 36 and repository routing/records. Executable source
   and tests are byte-identical to `843de6f`. The remaining REVIEW-0245 findings below
   therefore still apply unchanged.
2. **Critical - coverage-invalid `ALREADY_CURRENT` identities are still persisted.**
   They enter `attempted` before prior-snapshot coverage reconciliation. A blocking
   first run saves the identity, and a later run can skip the unresolved coverage.
3. **Critical - malformed ranking close timestamps still become terminal
   insufficiency.** An invalid interval close and a structurally valid still-forming
   bar share `INCOMPLETE_WINDOW`, allowing malformed evidence to remove a symbol and
   promote a lower-ranked survivor. Non-finite timestamp conversion is also untyped.
4. **High - malformed successful history responses can still become safe deferrals.**
   Fractional, non-day-aligned, or future first-bar timestamps are not rejected through
   `HISTORY_REQUEST_FAILED`; non-finite/out-of-range values can escape typed handling.
5. **High - the production code-identity path remains unguarded.** The current
   controlled run is honest, but `--code-commit` is still accepted verbatim and tests
   still use a fabricated all-zero identity. A later run can recreate the false
   lineage that caused REVIEW-0243.
6. **Medium - failed history remains contradictory report evidence.**
   `HISTORY_REQUEST_FAILED` appears in `deferred_symbols` while its acquisition is also
   failed and blocking.
7. **Medium - queue identity still omits versioned selection-policy/provider-source
   identity.** Semantic changes under identical scalar configuration can inherit old
   terminal cursor state.
8. **Low - 30-day evidence still reports bar count as trade count.** Every complete
   window records 30 rather than validating and aggregating Binance's kline trade-count
   field.

## Required corrections

Implement all seven corrections in REVIEW-0245 lines 65-86 before another controlled
publication. In particular:

1. Reconcile `ALREADY_CURRENT` coverage before advancing its cursor and add a two-run
   invalid-coverage regression.
2. Strictly type and classify ranking/history timestamps; malformed evidence blocks,
   while only a structurally valid still-forming ranking bar is insufficient.
3. Keep failed history out of every deferred report field.
4. Add explicit selection-policy/provider-source identity to the queue key and bump it.
5. Validate and aggregate actual 30-day trade counts, or remove the misleading field.
6. Verify production `CodeIdentity` against the clean checked-out source; use a test
   seam rather than fabricated production identity.
7. Commit source and tests first, then republish report 36 from that exact clean commit.

Do not perform another report-only republication before these source corrections.

## Verification

- Focused DATA-008 tests - PASS
- Legacy DATA-008 and DEX shared-path regressions - PASS
- Complete repository pytest suite - PASS (6 skipped)
- Scoped and full ticket Ruff - PASS
- Targeted mypy over six source modules - PASS
- Repository control before decision routing - PASS
- Controlled additive catalog/file/report reconciliation - PASS at `843de6f`
- Pinned DATA-006 reconciliation: 160/160 files, 90,276 rows - PASS
- Worktree was clean and synchronized with `origin/main` before this decision.
- The suite emitted the known non-blocking duplicate-ZIP-member warning in
  `tests/test_archives.py`.

Passing tests still omit the required malformed-evidence and invalid
`ALREADY_CURRENT` regressions.

## Closed from REVIEW-0245

The controlled code-identity mismatch is closed. Report 36 and the latest additive
manifest both record executable source commit
`843de6facdd4a32c49dc21f94717ac515beeb45e`. Commit `2c571e4` changes only controlled
evidence and routing, so it does not require a new executable code identity.

The latest additive dataset
`ds_e4b29a2928e0772163ea1efa33aa4b901053efbdc06d15b09e0e50dd4b5a64f3`
reconciles internally: one matching output file, 9,027 rows, four symbols, matching
report membership, 448 declared raw dependencies, and the direct exact DATA-006 base
dependency. Retain this evidence pattern, but repeat it only after the source correction.

## Architecture decision retained

DATA-006 remains immutable. DATA-008 remains a separate additive
`binance_spot_daily_bars` dataset anchored to exact accepted DATA-006 dataset
`ds_7a0a16834098aa336155bc5cd8085066e09c20343f5933c7017e508250a6c988`.
No `market_bars` publisher change, mass instrument mapping, or ownership of unmapped
Binance instruments is authorized.

## Routing

Use Sr Dev - Grok Build for the already-specified bounded REVIEW-0245 source correction,
followed by Jr Dev - Hermes for integration, regressions, records, commit, controlled
publication, and push. Final acceptance remains assigned to **Sol 5.6 High**. No new
architecture decision requires Sol Max.

## Next

- **Next required actor:** Sr Dev - Grok Build
- **Final reviewer:** Sol 5.6 High
- **Next ticket authorized:** NONE
