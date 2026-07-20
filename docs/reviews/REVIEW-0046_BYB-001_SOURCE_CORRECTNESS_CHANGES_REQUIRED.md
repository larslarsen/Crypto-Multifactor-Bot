# REVIEW-0046 - BYB-001 SOURCE CORRECTNESS CHANGES REQUIRED

**Ticket:** BYB-001 - Bybit Public Trade-Archive Normalizer
**Reviewed file:** `src/cryptofactors/ingest/bybit.py`
**Status:** CHANGES_REQUIRED - SR SOURCE ONLY - RESOLVED (Sr drop integrated; BYB-001 ACCEPTED at REVIEW-0050_BYB-001_ACCEPTED.md)
**Next required actor:** Sr Dev - Grok Build
**Date:** 2026-07-20

The three explicit REVIEW-0045 corrections are present: exact-limit EOF is probed,
transform version `1` is restored, and cleanup catches `Exception` rather than
`BaseException`. A full regression pass found the remaining fail-closed defects below.

## 1. Decimal128 admission is rounded under the ambient Decimal context

`_fits_decimal128_38_18` multiplies under Python's current Decimal context, whose default
precision is 28 rather than the target precision 38. The guard can therefore round away
forbidden fractional digits before testing integrality. For example:

```text
1234567890.1234567890123456789 * 1e18
-> 1234567890123456789012345679  (rounded under the default context)
```

The guard admits that value even though writing it as `decimal128(38, 18)` requires data
loss. The same context dependence can falsely reject valid boundary values. It also returns
the original Decimal representation, so unusual but numerically representable zero/exponent
forms can reach Arrow in a representation Arrow cannot rescale.

Determine exact decimal128 representability without context-rounded arithmetic, preferably
from `Decimal.as_tuple()`. Reject nonzero precision/scale overflow row-locally and return an
exact canonical Arrow-safe Decimal representation. Do not alter the process-global Decimal
context.

## 2. Timestamp conversion is also context-rounded

`_timestamp_token_to_utc_us` has the same defect at `d * Decimal(1_000_000)`.

- `1585180700.1234560000000000001` is currently rounded and accepted instead of failing as
  sub-microsecond input.
- Under an ambient Decimal precision of 10, valid `1585180700.0647` becomes
  `1585180700000000` instead of `1585180700064700`.

Derive integral microseconds exactly and independently of ambient context. Preserve the exact
source token, permit excess trailing fractional zeroes only when multiplication is exactly
integral, reject nonzero sub-microsecond digits, and apply the UTC range to the exact result.

## 3. CSV parsing is not strict

`csv.reader(text)` defaults to permissive parsing. An unterminated quoted final value such as
`"0\n` is accepted as a cell containing `0\n`; Decimal accepts that whitespace, so malformed
CSV can produce a clean `PASS`. Construct the reader with `strict=True` and retain typed
`csv.Error` handling for the header and data rows.

## 4. Truncated/invalid gzip exceptions can escape untyped

Python gzip reads use `EOFError` for truncated streams and may use `zlib.error` for invalid
deflate data. Neither is handled by the current archive-level exception mapping, so malformed
input can escape `normalize_bybit_trades` rather than emit `bybit_archive_bad_gzip` and a
`REJECTED` plan.

Classify `gzip.BadGzipFile`, `EOFError`, and `zlib.error` as
`bybit_archive_bad_gzip` during both reading and finalization. Keep ordinary non-process-control
close failures typed as `bybit_trade_parse_failure`; do not catch `BaseException`.

## 5. Partial archive failures leave false ordering metadata

Ordering is assigned only after normal loop termination. A byte-limit, gzip, or I/O exception
after accepted rows bypasses that block, leaving `ordering_per_object="empty"` while the trade
output contains rows. Derive `empty` / `single` / `ascending` / `descending` / `mixed` from
accepted rows on every exit path, including rejected partial streams. Continue preserving row
order and emitting at most one direction-reversal warning.

## 6. Storage location leaks into deterministic quality identity

The bounded-reader label is `str(storage_path)`, and that label is serialized into the limit
issue message. Moving the same registered raw object and bytes between storage roots therefore
changes `quality.parquet`, its output hash, and dataset identity. File paths are locations, not
MAN-001 identity, and BYB-001 grants filenames/directories no identity authority.

Use `raw_object_id` or a stable generic label in identity-bearing diagnostics. Do not serialize
absolute/local storage paths from path validation or I/O exceptions into quality output.

## 7. Preserve zero-length read semantics

The exact-limit probe is otherwise correct, but `_BoundedRawReader.read(0)` at the byte limit
currently probes/consumes the underlying stream. Return `b""` immediately for an explicit
zero-length read, as `readinto` already does for an empty destination. Actual EOF probes must
remain bounded to one byte and exact-limit content must remain accepted.

## Required regression behavior for Jr handoff

Sr does not write or run tests. The corrected source must make these cases directly testable by
Jr: ambient Decimal precision independence, decimal128 boundaries and over-scale rejection,
exact timestamp conversion, strict malformed-quote rejection, truncated/invalid-deflate typed
rejection, partial-stream ordering, storage-root-independent quality identity, and zero-length
bounded reads.

Keep schema and transform versions at `1`; no accepted or published v1 behavior exists to bump.

## Stop condition

Sr Dev edits production source only and returns the corrected source drop. No tests, records,
Git, commits, pushes, or gate claims. Jr integration remains unauthorized. Next ticket
authorized: `NONE`.
