# ADR 0027 - Partition-Aware Dictionary Storage Sizing

- **Status:** Accepted
- **Date:** 2026-08-23
- **Amends:** ADR-0024 sections 2, 3, 5, and 6; ADR-0025 sections 2 and 6
- **Evidence:** `research/sprint_004/257_CEX002_V2_CAPACITY_MODEL_REJECTION_AND_V3_ARCHITECTURE.md`

## Context

The accepted review-255 implementation executed successfully and reproducibly. Receipt
231 reports 646,431,826,972 future bytes against 154,464,187,767 available bytes. Its raw
components remain authoritative: 20,351,715,427 new Binance bytes and 30,580,702 new
Coinalyze bytes. The result contains no full historical trades, aggregate trades,
book-ticker history, book-depth history, or paid data.

The normalized bound is not yet suitable for a Gate-2 capacity decision. Two allocation
surrogates dominate it:

1. a one-row maximum-width Parquet payload is multiplied by all 216,934,972 projected
   quality-gap rows, producing a 191,920,661,196-byte gap product; and
2. the full string value, offset, dictionary index, and validity width of two future
   reference identities is charged on every one of 1,610,286,520 rows, producing a
   246,373,837,560-byte allocation.

The retained cost projections also charge venue, native symbol, and reference-state
dictionary values on every quote/depth row even though those values are fixed by the
product/component/native-symbol/UTC-month partition. These models are conservative, but
they are not the partition-aware dictionary representation ADR-0024 selected. In
particular, page and dictionary initialization from a one-row file is file/row-group
overhead, not an incremental cost of every later row.

## Decision

### 1. Preserve the complete research contract

This decision removes no source object, membership identity, product, source row, target
field, cost sample, quality-gap bound, lineage mapping, fee scenario, or operating
reserve. The exact source tokens remain in immutable raw objects. All eleven target
products, the complete 771-identity universe, the 3,144 selected whole-day cost objects,
and the `ceil(N / 2)` quality-gap ceiling remain mandatory.

### 2. Size dictionary columns as dictionaries

For a dictionary-encoded target column, the allocation has separate terms:

1. dictionary indices and null validity for every projected row;
2. each distinct dictionary value and its offset once in every row group in which it can
   occur; and
3. an explicit row-group payload anchor covering dictionary/data-page initialization.

A value may not be charged once per partition if it can vary within that partition.
Conversely, a value proved constant by the partition key or accepted authority may not be
charged as a new string on every row. The receipt publishes, for every such allocation,
the row count, row-group count, dictionary cardinality bound and source, maximum value
width, index/validity bytes, dictionary-value bytes, anchor bytes, incremental-row bytes,
and exact total.

The product/component/native-symbol/UTC-month partition proves the constancy of venue,
native symbol, product, component, UTC month, and declared fixed state/kind labels.
Data-dependent dictionaries use their complete accepted row set. If a future dictionary's
cardinality has no accepted upper bound, sizing blocks as unknown; it may not invent a
cardinality or silently revert to a different physical representation.

### 3. Reference identity is authority-bounded and never backdated

One accepted native membership identity maps to at most one canonical instrument identity.
Contract-version dictionary values are limited to versions actually supported by the
accepted contract authority. The current authority has at most one snapshot-backed
version for a detailed membership identity and no version for a funding-only identity.
Rows outside an accepted version's effective coverage remain null with an explicit typed
reference gap/state; a current snapshot is never projected backward and a different
opaque fingerprint is never fabricated for each economic row.

The physical Parquet columns remain the declared dictionary-encoded canonical instrument
and version strings. Their indices occur on rows, while their accepted opaque values occur
in the relevant row-group dictionaries. If later reference acquisition adds a version or
changes the accepted cardinality, Gate 3 must stop and sizing must be rerun before the new
authority can be published.

### 4. Separate row-group anchors from incremental rows

When a projected fixed-schema product has more rows than its real witness, a one-row
payload may bound the initialization of one output row group. It is multiplied by the
projected row-group count, never by the projected row count. Additional rows are charged
only their conservative fixed-width values, dictionary indices, null validity, and any
dictionary values whose accepted cardinality requires them.

The quality-gap projection applies this model independently to every real
product/native-symbol/UTC-month partition and keeps the exact `ceil(N / 2)` row bound.
The bundle descriptor already has its complete projected row set; it is measured from
that complete set or by an equivalent batch-exact calculation. It may not replace the
set with one synthetic maximum-width row and multiply that row's page initialization.

### 5. Version the corrected evidence

Receipt 231, schema `cex002_gate2_storage_sizing_v2`, and all v2 envelopes remain immutable
diagnostic evidence. The corrected schema is `cex002_gate2_storage_sizing_v3`, its fixed
repository target is
`research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`, and its envelopes use
`evidence/sizing/v3/envelopes/sha256`. V3 reuse requires exact source, schema, writer,
authority, policy, and byte identity. V1 and v2 receipts and envelopes are read-only.

### 6. Gate boundary

The corrected receipt retains ADR-0024's six non-overlapping capacity components and
partition-atomic temporary-work rule. Gate-2 storage is sufficient only if the reviewed
v3 total is no greater than post-publication available bytes. Receipt 231 does not accept
or reject capacity under the corrected representation. No acquisition, normalization,
catalog publication, NautilusTrader load, Harmonic Trader work, or storage purchase is
authorized by this ADR.

## Consequences

- The 20.38 GB raw projection remains exact and is not confused with working storage.
- Repeated dictionary values and one-row page initialization no longer masquerade as
  per-row payload.
- Historical reference identity is not fabricated or backdated to obtain a smaller
  number.
- A new deterministic v3 run is required before the project knows whether present disk
  capacity is sufficient.
