# REVIEW-0044 - BYB-001 SOURCE CHANGES REQUIRED

**Ticket:** BYB-001 - Bybit Public Trade-Archive Normalizer
**Reviewed file:** `src/cryptofactors/ingest/bybit.py`
**Status:** CHANGES_REQUIRED - SR SOURCE ONLY - RESOLVED (Sr drop integrated; BYB-001 ACCEPTED at REVIEW-0050_BYB-001_ACCEPTED.md)
**Next required actor:** Sr Dev - Grok Build
**Date:** 2026-07-20

The source follows the intended module boundary and exposes the required high-level contract,
but it is not approved for Jr integration. Correct the findings below without changing ticket
scope.

## Findings

### 1. Bounded gzip stream is not a valid binary IO wrapper

`_BoundedReader` is passed to `io.TextIOWrapper` but implements only `read`, `readable`, and
`close`. `TextIOWrapper` expects the binary IO interface (`writable`, `seekable`, closed-state
behavior and buffered read methods); construction or iteration can fail before parsing.

Its `read(-1)` also delegates an unbounded read before checking the resulting length, so the
configured limit does not prevent a large allocation.

Implement a real `io.RawIOBase`/`io.BufferedIOBase` compatible bounded stream (normally
`readinto` plus `io.BufferedReader`) that never requests more than remaining bytes plus one.
Do not suppress gzip CRC/truncation failures during close/finalization.

### 2. Valid descending archives generate one warning per row

Every timestamp decrease currently emits `bybit_trade_nonmonotonic_timestamp`. Real audited
Bybit archives are descending, which would produce a huge quality table and incorrectly mark
ordinary input `PASS_WITH_WARNINGS`.

Establish direction from the first non-equal pair. Ascending or descending is normal. Emit a
single warning only if a later non-equal comparison reverses the established direction; keep
the final diagnostic `mixed`. Equal timestamps do not establish or reverse direction.

### 3. Duplicate evidence depends on caller input order

Duplicate issues are attached only to whichever row/object is encountered later. Reversing
the same `raw_objects` changes quality partitions and therefore dataset identity.

Canonicalize processing by validated raw-object ID and make duplicate/conflict evidence
order-independent. Every involved object must receive deterministic context identifying all
raw object IDs and source row numbers. Preserve all trade rows.

### 4. Exact source tokens and malformed CSV are not fully preserved/typed

`_parse_trade_row` strips every cell before storing `source_timestamp`, so it does not retain
the exact source token. Header cells are also stripped before the supposedly exact schema
comparison. Preserve exact source text where promised and parse from a separate stripped
value. Reject, rather than normalize, whitespace-altered headers/symbols.

Catch `csv.Error` and surface it as a typed quality error with raw-object/row context. Use a
plain unsigned decimal-seconds grammar for timestamps; do not silently accept exponent or
signed forms absent from the audited source schema.

### 5. Out-of-range timestamps remain in typed trade output

UTC range validation occurs only during coverage calculation after the row has already been
accepted. The invalid row is still written to `trades.parquet`.

Validate UTC range during row parsing. An invalid event time must produce
`bybit_trade_invalid_timestamp` and must not enter typed trade output.

### 6. Safe raw-object identity is validated but not used

The preflight strips `raw_object_id` for validation, then dictionaries and output paths use
the original value. An ID such as `" raw_1 "` can pass the stripped check while producing
noncanonical keys/paths.

Require the original ID to equal its validated canonical token, or consistently replace all
uses with one canonical value. Dependency IDs must remain the immutable registered ID; do not
silently rewrite them.

### 7. Decimal values are not checked against the physical Arrow type

Finite Decimal values can still exceed `decimal128(38, 18)` precision/scale and fail during
Parquet construction, bypassing typed row-quality handling.

Validate every Decimal against the declared precision and scale without rounding. Values
that cannot be represented must become row-level `bybit_trade_parse_failure` issues and must
not reach the writer.

## Additional correction

Move `stream_sha256_and_size` to the module imports rather than importing it inside both
writers. Keep cleanup explicit and avoid broad exception suppression.

## Preserved decisions

- Archive trades only; no REST, funding, bars, or BAR-001 changes.
- Decimal-only timestamp/numeric parsing and no invented inverse quantities.
- Source rows remain in original order.
- Duplicate rows remain visible and make quality fail closed.
- RAW dependencies and MAN-001 plan structure remain required.

## Stop condition

Sr Dev edits production source only and returns the corrected source drop. No tests, records,
Git, commits, pushes, or acceptance-gate claims. Jr integration remains unauthorized. Next
ticket authorized: `NONE`.
