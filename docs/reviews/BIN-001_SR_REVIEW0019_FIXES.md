# BIN-001 — Sr REVIEW-0019 remediation drop

**Status:** Ready for Jr integration and test coverage  
**Production file (already in tree):** `src/cryptofactors/ingest/binance.py`  
**Transform version:** `2`  
**Governing review:** `docs/reviews/REVIEW-0019_BIN-001_CHANGES_REQUIRED.md`  
**Ticket:** `tickets/BIN-001.md`  
**Migration:** none  

Sr Dev — Grok Build source-only drop. No tests, Git, commits, pushes, or
acceptance runs by Sr. Jr Dev — Hermes owns everything below.

## Code changes (already in production file)

1. **Inclusive close-time validation (REVIEW-0019 #1).**  
   Accepts Binance archive convention  
   `close_time == open_time + interval − 1` (source unit: ms or us).  
   Exclusive `open + interval` is an interval mismatch quality issue.

2. **Normalized UTC microsecond timestamps (REVIEW-0019 #2).**  
   Output `open_time` / `close_time` are signed int64 UTC microseconds.  
   Source values preserved as `source_open_time`, `source_close_time`,  
   `source_timestamp_unit`. Coverage uses microsecond conversion (no  
   always-divide-by-1000). Partition notes `timestamp_storage=utc_microseconds`.

3. **Duplicate and gap quality issues (REVIEW-0019 #3).**  
   Emits `binance_kline_duplicate_open_time` and `binance_kline_gap`.  
   Within-object and cross-object duplicate open_time boundaries.  
   All parseable observations preserved (no silent drop/dedup/fill).

4. **MAN-001-publishable plan (REVIEW-0019 #4).**  
   `row_count_policy=REQUIRE_VERIFIER` with per-output parquet row counters  
   (`_parquet_row_counter` via metadata). Ready for `verify_outputs` / publisher.

5. **Market-type and volume semantics (REVIEW-0019 #5).**  
   Validates/resolves `spot`, `usdm`, `coinm` (aliases: `usd-m`, `coin-m`,  
   `um`, `cm`, …). Partition + quality_summary carry `volume_unit` and  
   `quote_volume_unit` (spot/usdm: base/quote asset; coinm: contracts/base).

6. **Malformed first-row handling (REVIEW-0019 #6).**  
   Header skip only when first cell is `open_time` / `opentime`.  
   Non-digit first rows are data and surface typed quality issues  
   (not silently treated as headers).

7. **Case-sensitive interval + calendar month (REVIEW-0019 #7).**  
   `1m` (minute) ≠ `1M` (calendar month). `1M` / `1mo` are calendar months,  
   never a fixed 30-day timedelta. Fixed 30-day aliases removed.

## Behavior Jr must encode in tests

Replace the two strict xfails and add focused regressions for:

| Case | Expectation |
|------|-------------|
| Inclusive close (ms) | `close = open + interval_ms − 1` → no interval_mismatch; PASS path |
| Inclusive close (us) | same for post-2025 microsecond archives |
| Exclusive close | `close = open + interval` → `binance_kline_interval_mismatch` |
| Normalized timestamps | bar `open_time` is UTC µs; ms source → `source * 1000`; coverage sane |
| Duplicate open_time | both rows kept; `binance_kline_duplicate_open_time` present |
| Interval gap | rows kept; `binance_kline_gap` present |
| Cross-object duplicate | same open_time in two raw objects → duplicate issue |
| Market-type rejection | unknown `market_type` → `ValueError` |
| Market volume semantics | partition carries correct volume units for spot/usdm/coinm |
| Malformed first row | non-header non-digit first row → `binance_kline_malformed_row` (or parse_failure), not silent skip |
| Header still skipped | explicit `open_time` header row skipped; one data bar remains |
| Calendar `1M` | inclusive close at next calendar month start − 1 source unit accepted |
| `1M` ≠ `1m` | monthly-length close fails under `interval="1m"` |
| MAN-001 publication | `verify_outputs` / DatasetPublisher succeeds with verified row counts |

Update fixtures: existing `_good_row_ms` used exclusive close; switch good-path  
fixtures to inclusive close.

## Jr work (see `tickets/BIN-001.md` and `docs/handoff/CURRENT_TASK.md`)

1. Confirm `src/cryptofactors/ingest/binance.py` is the REVIEW-0019 drop (transform  
   version `"2"`, inclusive close, row_counters, market-type validation).
2. Integrate in-tree (no zip merge required if working tree already has the file).
3. Update `tests/ingest/market/test_binance_kline.py`: remove the two  
   `xfail(strict=True)` markers; fix fixtures to inclusive close; add the  
   focused cases above.
4. Correct the two invalid acceptance-command source paths in  
   `tickets/BIN-001.md` (`src/cryptofactors/ingest/market` → actual paths  
   under `src/cryptofactors/ingest` / `tests/ingest/market` as appropriate).
5. Run every corrected acceptance gate from the ticket, plus  
   `python3 scripts/check_repo_control.py`.
6. Update `docs/reviews/BIN-001_CHANGE_REPORT.md` with real commands/results,  
   this Sr drop reference, and integration notes.
7. Commit and push per Hermes duties.
8. **Stop for reviewer inspection.** Do not begin BAR-001 or any other ticket.  
   `Next ticket authorized: NONE`.

## Out of scope for this drop

- Migrations, architecture docs, ADR changes  
- Canonical bar promotion (BAR-001)  
- Network access in the normalizer  
- Sr Git / commit / push / acceptance execution  
