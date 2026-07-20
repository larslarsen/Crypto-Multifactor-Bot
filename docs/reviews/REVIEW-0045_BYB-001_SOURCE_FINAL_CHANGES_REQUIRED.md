# REVIEW-0045 - BYB-001 SOURCE FINAL CHANGES REQUIRED

**Ticket:** BYB-001 - Bybit Public Trade-Archive Normalizer
**Reviewed file:** `src/cryptofactors/ingest/bybit.py`
**Status:** CHANGES_REQUIRED - SR SOURCE ONLY
**Next required actor:** Sr Dev - Grok Build
**Date:** 2026-07-20

REVIEW-0044 findings are resolved except for the two items below.

## 1. Exact-limit input is rejected even when it does not exceed the limit

`_BoundedRawReader.read` and `readinto` immediately raise when `remaining <= 0`. After a
stream consumes exactly `max_decompressed_bytes`, the normal EOF probe therefore raises
`_LimitExceeded` without checking whether another decompressed byte exists.

The contract rejects content that **exceeds** the limit, not content exactly equal to it.
When remaining is zero, probe the underlying stream for at most one byte:

- EOF -> return `b""` / `0`;
- one byte -> raise `_LimitExceeded`.

Keep every underlying request bounded to remaining plus one.

## 2. Transform version conflicts with the ticket

The ticket defines the first unpublished BYB normalizer as transform version `1`, but the
corrected source declares `BYBIT_TRADE_TRANSFORM_VERSION = "2"`. The initial source drop was
never approved, published, committed, or consumed, so no persisted v1 contract exists and no
compatibility bump is justified. Restore version `1` throughout generated config/metadata.

## Cleanup

In `_close_stream`, catch `Exception`, not `BaseException`; normal cleanup must not intercept
`KeyboardInterrupt`, `SystemExit`, or other process-control exceptions. Continue collecting
ordinary close errors and surfacing gzip/CRC failures as typed issues.

## Stop condition

Sr Dev edits production source only and returns the corrected source drop. No tests, records,
Git, commits, pushes, or gate claims. Jr integration remains unauthorized. Next ticket
authorized: `NONE`.
