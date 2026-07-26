# REVIEW-0241 - DATA-008 CHANGES REQUIRED

**Ticket:** DATA-008 - Free CEX Universe Expansion (Binance-first)
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Base commit:** `6fcc86c`
**Date:** 2026-07-26

## Findings

1. **Critical - the publication does not expand the DATA-006 canonical panel.**
   DATA-006 published 90,276 `market_bars` rows for 23 symbols from 2020 through
   2026. The new runner neither loads that dataset nor passes its symbols through
   `already_covered`; it creates an unrelated `binance_spot_daily_bars` dataset.
   Report 36 consequently contains only 70 rows for seven symbols over ten days.
   Four of those seven (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`, and `DOGEUSDT`) were already
   in DATA-006, so the pinned dataset is a smaller parallel panel rather than the
   expanded canonical history the ticket promises consumers.

2. **High - the priority measure does not satisfy the ticket's 30-day rule.**
   Selection sorts `/api/v3/ticker/24hr` quote volume and explicitly fingerprints a
   `24h` window. REVIEW-0240 required honest window labeling; it did not replace the
   ticket's top-N-by-30-day-volume requirement. Correct labeling closes the prior
   misstatement but not the required measurement.

3. **High - historical and multi-day backfill cannot execute as specified.**
   `BinanceBarAcquirer.acquire()` makes one kline request capped at 1,000 rows. Any
   daily range longer than 1,000 days returns a trailing coverage gap and blocks the
   run, so it cannot backfill an added symbol from 2020, much less from listing. The
   runner also has no persisted daily work budget/cursor tied to DATA-007 capacity;
   `top_n` is only a selection limit. The ten-day controlled run does not exercise
   either historical pagination or multi-day resume.

4. **High - the selection audit and exclusion taxonomy remain incomplete.**
   Candidates that pass all filters but fall below the top-N cut disappear after
   truncation: they are neither selected, excluded, failed, nor deferred, despite the
   required auditable terminal classification. The stablecoin taxonomy also omits
   exchange-observed non-target bases including `BFUSD`, `FRAX`, `USDE`, `USDS`, and
   `XUSD`; report 36 classifies them only as below the current volume floor. A volume
   increase could therefore admit them as research assets.

5. **Medium - report accounting is not reliable across incremental runs.**
   `total_rows_added` sums fetched rows rather than the net new rows after merge and
   deduplication. `snapshot_span` takes the first and last rows of a symbol-major
   sorted snapshot rather than the global minimum and maximum timestamps. Rate-limit
   entries record HTTP attempts but not the backoff durations actually applied, even
   though the ticket requires reporting 429s and backoffs.

## Required corrections

1. Extend the accepted DATA-006 `market_bars` panel, or publish a schema-compatible
   full replacement with a declared DATA-006 dependency. Exclude the existing 23
   symbols from the added-symbol take, retain their history, and report base, added,
   and total panel coverage separately.
2. Rank on an actual trailing 30-day Binance volume measure with pinned observation
   time and exact raw lineage. If 24-hour priority is desired instead, stop and obtain
   an explicit reviewer-approved ticket rescope before implementation or evidence.
3. Paginate klines until the requested interval is complete, preserving every page as
   raw evidence. Add an explicit persisted per-day work budget/cursor so an interrupted
   or capacity-limited run resumes without silently shrinking the requested panel.
4. Give every discovered symbol a terminal, reasoned state, including valid candidates
   outside top N. Complete the versioned non-target taxonomy using the assets observed
   in the controlled exchange response.
5. Compute net rows added after merge, global snapshot spans, and actual retry/backoff
   events. Repeat report 36 with a meaningful historical expansion beyond DATA-006.
6. Add actual-runner tests for a seeded DATA-006 panel, exclusion of its 23 symbols
   from additions, a range longer than 1,000 daily bars, multi-run budget resume,
   complete top-N audit, omitted stablecoin bases, and incremental report accounting.

## Verification

- Focused DATA-008, legacy DATA-008, and DEX regression tests - PASS
- Complete repository pytest suite - PASS (6 skipped)
- Scoped and full ticket Ruff - PASS
- Repository control before decision routing - PASS
- The suite emitted the known non-blocking duplicate-ZIP-member warning in
  `tests/test_archives.py`.

Passing tests do not override the ticket and controlled-evidence mismatches above.

## Closed from REVIEW-0240

The rewrite correctly separates exchange discovery, eligibility, and ranking; avoids
substring leveraged-token filtering; labels 24-hour evidence honestly; preserves raw
responses before decoding; validates prior snapshots; directly closes carried-row raw
lineage; blocks partial publication; and advances watermarks only after publication.
These improvements should be retained.

## Constraints

- Correct DATA-008 only; do not start another ticket.
- No architecture rewrite, synthetic bars, Birdeye OHLCV, paid sources, factor work,
  paper promotion, or LIVE.
- Retain exact raw-response preservation and full-snapshot retry safety.

## Next

- **Next required actor:** Sr Dev - Claude Opus 5
- **Next ticket authorized:** NONE
