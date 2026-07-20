# REVIEW-0020 - BIN-001: CHANGES_REQUIRED

**Ticket:** BIN-001 - Binance archive kline normalizer
**Workspace reviewed:** Jr-pushed v2 state; the v2 integration hash is not recorded accurately in the change report
**Status:** CHANGES_REQUIRED - RESOLVED (superseded by REVIEW-0025_BIN-001_ACCEPTED.md)
**Date:** 2026-07-19

REVIEW-0019 remains the governing defect history. The v2 revision resolves real
Binance inclusive-close semantics, basic UTC-microsecond conversion, within-object
duplicate/gap detection, explicit header recognition, and MAN-001 row counters, but it
does not complete the authorized remediation.

## Blocking findings

1. **Cross-object gaps are not detected.** `_detect_duplicates_and_gaps` is called
   separately for each object's `bar_rows`. The only global state is
   `global_open_seen`, which detects cross-object duplicates but never compares the
   final/first or globally adjacent opens from different objects. This contradicts the
   change report's "within + cross-object" claim and REVIEW-0019's boundary requirement.
2. **Empty and header-only archives pass quality.** A single empty CSV or header-only
   CSV produces zero bars, zero issues, and `QualityStatus.PASS`. A source-normalized
   partition with no observations must fail closed through a typed quality issue.
3. **Mixed-unit rows are normalized with the wrong unit.** `_parse_kline_row` records a
   mixed-unit issue but retains `eff_unit = unit or detected`; after the first row,
   subsequent rows are converted using the object's first unit rather than their own
   detected unit. The raw fields are preserved, but normalized UTC fields become false.
   Coverage conversion failures are then silently swallowed by `except Exception: pass`.
4. **COIN-M volume fields remain semantically mislabeled.** The fixed schema stores CSV
   field 7 as `quote_volume`, while the COIN-M metadata declares that same field to be
   base-asset volume. COIN-M taker-volume meanings also differ from spot/USD-M but retain
   the spot-oriented field names. Metadata cannot make a contradictory physical schema
   typed or safe for downstream use. Unsupported market types must be rejected unless
   their physical fields are represented accurately.
5. **The schema identity was not versioned.** The v2 bar schema adds source timestamp
   columns and changes timestamp semantics, but `BINANCE_KLINE_SCHEMA_VERSION` remains
   `"1"` with no fingerprint. A materially different immutable dataset schema must not
   reuse the prior schema identity.
6. **Required integration regressions are missing.** The focused file has ten test
   functions, not the twelve claimed. It does not test cross-object gaps, empty/header-
   only failure, mixed-unit output correctness, coverage bounds, market-specific volume
   values, malformed first rows, calendar-month boundaries, source lineage, or a full
   two-output MAN-001 publication. The MAN-001 test verifies only the bar subset with
   `verify_outputs`; it does not publish the returned plan.
7. **The change report is not traceable or accurate.** It names original v1 commit
   `d40ecea` rather than the pushed v2 integration, claims cross-object gap handling that
   is absent, and reports twelve focused passes inconsistent with the current test file.

## Reviewer validation

This disposition is based on direct source, test, handoff, ticket, and change-report
inspection. Acceptance commands were not rerun by the reviewer; test execution remains
Jr Dev responsibility. The Jr-reported gate results do not overcome the source defects
or evidence inconsistencies above.

## Authorized source task - Sr Dev - Grok Build

Read REVIEW-0019 and this review, then edit only
`src/cryptofactors/ingest/binance.py`. Add duplicate/gap assessment across the complete
multi-object normalized sequence while retaining per-object issue lineage; reject empty
or header-only objects through a typed error; normalize each mixed-unit row with its
observed unit while rejecting the mixed object and surfacing invalid/out-of-range times
instead of swallowing coverage failures; and either model each supported market type's
physical volume fields accurately or reject unsupported types. Assign a new schema
identity for the changed Parquet schema. Preserve all source observations, no-network
operation, and MAN-001 row verification. Do not edit tests, records, migrations, Git,
commits, or pushes. Stop after the source drop.

## Authorized integration task - Jr Dev - Hermes

After the Sr source drop is present, integrate it without making independent production
source changes. Add focused regressions for every finding above plus the omitted
REVIEW-0019 cases: cross-object gap and duplicate boundaries, empty/header-only input,
mixed ms/us rows and coverage, actual market-specific volume values, malformed first
row, month-end/leap-year `1M` behavior, source lineage, local-only operation, and
publication of the complete returned `PublishPlan` including bars and quality output.
Run every ticket acceptance command. Correct the test counts, behavioral claims, and
immutable integration hash in `BIN-001_CHANGE_REPORT.md`; commit and push; then stop for
reviewer inspection.

## Disposition

BIN-001 remains `IN_PROGRESS`. Next ticket authorized: `NONE`.
