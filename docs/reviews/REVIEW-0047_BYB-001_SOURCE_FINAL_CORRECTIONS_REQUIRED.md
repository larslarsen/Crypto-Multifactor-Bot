# REVIEW-0047 - BYB-001 SOURCE FINAL CORRECTIONS REQUIRED

**Ticket:** BYB-001 - Bybit Public Trade-Archive Normalizer
**Reviewed file:** `src/cryptofactors/ingest/bybit.py`
**Status:** CHANGES_REQUIRED - SR SOURCE ONLY
**Next required actor:** Sr Dev - Grok Build
**Date:** 2026-07-20

REVIEW-0046 is substantially resolved. Strict CSV, typed gzip truncation/deflate errors,
partial-stream ordering, stable serialized diagnostics, ambient-context independence,
zero-length reads, and version `1` are present. Correct only the remaining items below.

## Remaining after latest source drop

All corrections below are resolved except these two points in timestamp/Decimal unscaling:

1. Apply digit-length and magnitude bounds **before** the loop that constructs `coeff`. The
   current code builds an arbitrarily large Python integer first, allowing repeated large CSV
   numeric tokens within the decompressed-byte limit to consume excessive CPU. Decimal128 values
   need at most 38 unscaled digits; valid timestamps need at most 16 unscaled digits. Reject
   impossible magnitudes before integer construction without changing exact boundary behavior.
2. Classify tiny nonzero values whose discarded fractional width exceeds the coefficient length
   (for example `0.0000000000001`) as sub-microsecond, not out-of-range. They remain rejected with
   `bybit_trade_invalid_timestamp`.

Sr Dev must make only these production-source corrections and return the source drop. All other
REVIEW-0047 items are accepted and must not be changed.

## 1. Ordinary close exceptions still escape untyped

`_close_stream` can re-raise any collected `Exception`, but `_process_raw_object` finalization
only handles the gzip tuple and `OSError`. A `RuntimeError` or other ordinary close exception
therefore escapes the normalizer and skips `_finalize_ordering`.

Add a final `except Exception` that emits stable `bybit_trade_parse_failure` evidence. Keep
`_finalize_ordering` guaranteed for every handled exit. Do not catch `BaseException`.

## 2. Positive-exponent zero is rejected before canonicalization

For `Decimal("0E+1000000")`, `as_tuple().digits == (0,)`; `if not digs` is false, and the
positive-exponent precision check returns `None`. The canonical zero branch is unreachable even
though this is a finite, nonnegative, exactly representable zero.

Recognize an all-zero coefficient before exponent/precision checks and return unscaled zero.
Canonicalize positive and negative zero to the same Arrow-safe representation. Keep nonzero
precision/scale bounds unchanged.

## 3. OSError classification remains storage-location-sensitive

The read/finalization handlers inspect `str(exc)` for substrings such as `gzip`, `compress`, and
`deflate`. An ordinary I/O error whose filename contains `/compress/` is therefore classified
differently from the same error under another storage root. This still lets location affect
quality identity.

Classify `gzip.BadGzipFile`, `EOFError`, and `zlib.error` structurally in their existing handler.
Map remaining `OSError` instances to stable I/O/close `bybit_trade_parse_failure` evidence without
message or path heuristics.

## 4. Timestamp conversion reuses the decimal128 precision ceiling

`_unscaled_int_from_decimal` always imposes the 38-digit Arrow precision bound. A large but
integral timestamp therefore returns `None` and is reported as sub-microsecond rather than
out-of-range. Timestamp integrality and UTC range are separate contracts.

Allow exact timestamp unscaling without the decimal128 precision ceiling, then apply the UTC
range to the exact integer result. Keep decimal field calls bounded to precision 38. Avoid large
power allocation by rejecting timestamp magnitude from digit/range evidence before constructing
an unbounded integer.

## 5. Parser failure can add false header-only evidence

When the first data record raises `csv.Error` or `UnicodeDecodeError`, `data_rows` is still zero,
so the post-loop block also emits `bybit_trade_empty_observations` with a `header-only` message.
Data was present but malformed.

Track clean EOF versus parser failure. Emit the header-only issue only when EOF follows the header
without any data record or parser failure. The malformed-record case should retain its typed
parse issue without false empty-input evidence.

## Preserved corrections

- Do not regress exact-limit behavior, strict CSV, gzip exception typing, partial ordering,
  deterministic duplicate evidence, source-row preservation, or path-independent messages.
- Decimal and timestamp results must remain independent of ambient Decimal context.
- Schema and transform versions remain `1`.

## Stop condition

Sr Dev edits production source only and returns the corrected source drop. No tests, records,
Git, commits, pushes, or gate claims. Jr integration remains unauthorized. Next ticket
authorized: `NONE`.
