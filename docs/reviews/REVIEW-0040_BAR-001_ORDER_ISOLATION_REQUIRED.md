# REVIEW-0040 - BAR-001 ORDER ISOLATION REQUIRED

**Ticket:** BAR-001 - Canonical bar publisher and daily reconciliation
**Reviewed implementation:** `d12caff`
**Reviewed records:** `1d57bb6`
**Status:** CHANGES_REQUIRED (narrow Jr integration correction)
**Next required actor:** Jr Dev - Hermes (Tencent HY3)
**Date:** 2026-07-20

All REVIEW-0039 findings except source-order isolation are resolved.

## Finding

`test_no_merge_mixed_timeframe_daily_counts` executes both source orders through
`_publish(tmp_path, ...)`. Both results therefore reference the same
`tmp_path/market_out/...` file. The second publication overwrites the first before the loop
reads either result, so both assertions inspect only the second order. A regression affecting
only the first source order would pass.

The conflict-order regression also asserts no intraday promotion only for `res_ab`, not
`res_ba`.

## Required correction

1. Publish mixed-timeframe orders under separate output parents, read each independent
   output, and assert selected-1m OHLC/volume/trade totals for both.
2. Publish conflicting duplicate orders under separate output parents and assert both orders
   produce no intraday rows, quarantine all conflicting rows, and report the conflict.
3. Correct "byte-identical" in the change report unless the test actually compares bytes;
   current table equality proves semantic table equality.
4. Commit the test correction, run every ticket-exact gate at that clean implementation
   commit, then commit/push the exact evidence and all outstanding reviewer/control records.

No production source changes are authorized.

## Disposition

BAR-001 remains `IN_PROGRESS`. Next ticket authorized: `NONE`.
