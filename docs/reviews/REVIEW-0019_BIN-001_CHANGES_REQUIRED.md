# REVIEW-0019 - BIN-001: CHANGES_REQUIRED

**Ticket:** BIN-001 - Binance archive kline normalizer
**Implementation commit reviewed:** `d40ecea0aa5333b05b336430d15cb8ee1b481d74`
**Repository HEAD reviewed:** `3ad0e023a163d6639829a6e8c4aaae25ceec916e`
**Status:** CHANGES_REQUIRED
**Date:** 2026-07-19

This review supersedes REVIEW-0018 as the current BIN-001 disposition. REVIEW-0018
correctly rejected missing duplicate and gap detection, but it did not identify all
acceptance blockers.

## Blocking findings

1. Real Binance archive klines are rejected. `_validate_interval` requires
   `close_time == open_time + interval`; Binance uses an inclusive close of
   `open_time + interval - 1 source unit` (microsecond for post-2025 spot archives,
   millisecond where the source remains millisecond).
2. Output timestamps remain mixed raw millisecond/microsecond integers rather than
   normalized UTC microseconds or Arrow UTC timestamps as required by the data
   architecture. Coverage always divides by 1,000, so microsecond rows overflow and
   are silently omitted from coverage.
3. Duplicate-open-time and interval-gap detection remain unimplemented. Their required
   regressions are strict xfails.
4. The returned MAN-001 `PublishPlan` selects `REQUIRE_VERIFIER` but supplies no row
   counters or receipts. `DatasetPublisher` therefore cannot publish the staged output.
5. `market_type` is only checked for non-emptiness. Spot, USD-M, and COIN-M field and
   volume semantics are not validated or represented correctly.
6. A first row with any nonnumeric first field is silently treated as a header instead
   of surfacing a malformed-row quality issue.
7. Interval parsing lowercases `1M` into `1m`, and `1mo` is treated as a fixed 30-day
   interval rather than a calendar month.
8. The exact Ruff and mypy acceptance commands in `tickets/BIN-001.md` target the
   nonexistent `src/cryptofactors/ingest/market` path. The prior change report recorded
   different commands, so the ticket's stated gates have not all passed.

## Validation observed

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/ingest/market -q --tb=short` | exits 0 with 11 passed, 2 required cases xfailed |
| ticket-exact Ruff command | FAIL: source path does not exist |
| ticket-exact mypy command | FAIL: source path does not exist |
| Ruff against `src/cryptofactors/ingest/binance.py` and focused tests | PASS |
| mypy against `src/cryptofactors/ingest/binance.py` and focused tests | PASS |
| `PYTHONPATH=src uv run pytest -q` | PASS with the same 2 xfails |
| `python3 scripts/check_repo_control.py` | PASS |

## Authorized source task - Sr Dev - Grok Build

Read this review and `tickets/BIN-001.md`, then edit production source only in
`src/cryptofactors/ingest/binance.py`. Resolve findings 1-7 with the smallest auditable
implementation. Preserve every source observation; report duplicates, gaps, mixed or
invalid units, and malformed rows through typed quality issues rather than repairing,
deduplicating, filling, or silently dropping them. Preserve local-only operation and raw
object lineage. Return a MAN-001-publishable plan. Do not edit tests, migrations,
repository records, Git state, commits, or pushes. Stop after the source drop is ready
for Jr integration.

## Authorized integration task - Jr Dev - Hermes

After the Sr source drop is present, inspect and integrate it. Own all test, repository
record, and Git work. Replace the two xfails with passing regressions and add focused
coverage for actual Binance inclusive close semantics in ms/us, normalized timestamp
values and coverage, cross-row and cross-object duplicate/gap boundaries, supported
market-type volume semantics, malformed first-row handling, calendar-month handling,
and successful MAN-001 publication with verified row counts. Correct the two invalid
acceptance-command source paths in `tickets/BIN-001.md`, run every corrected acceptance
gate, update `docs/reviews/BIN-001_CHANGE_REPORT.md`, commit, and push. Do not begin
BAR-001 or any other ticket. Stop for reviewer inspection.

## Disposition

BIN-001 remains `IN_PROGRESS`. Next ticket authorized: `NONE`.
