# ADR 0024 - Typed Normalization and Partition-Atomic Publication

- **Status:** Accepted
- **Date:** 2026-08-23
- **Amends:** ADR-0021 sections 2, 4, 5, 6, and 7
- **Evidence:** `research/sprint_004/230_CEX002_STORAGE_ARCHITECTURE_CORRECTION.md`

## Context

The accepted ADR-0021 sizing implementation completed successfully and reproducibly at
receipt SHA-256
`f2e1fef8156e3af1abd40554e5a8393ee6566e1719cf990a2a49867e5aef185c`.
It proves a 20,387,504,203-byte complete Binance-plus-Coinalyze raw footprint and a
20,380,788,328-byte projected new raw allocation after retained credit. It also reports a
432,141,608,507-byte capacity requirement against 158,559,266,533 available bytes, so
Gate 2 is blocked under that storage model.

The capacity result is not evidence that CEX-002 requires hundreds of gigabytes of raw
trades or historical order books. The required raw scope remains the exact 20.38 GB
selected release, including every whole-day object in the frozen first/midpoint/last cost
sample. The excess comes from two conservative implementation surrogates:

1. the sizing envelope stores every CSV token as a string and repeats family, symbol,
   interval, source key, and row ordinal on every row; the greatest whole-file ratio,
   including a Parquet footer from a tiny sample, is then applied to every byte in a
   physical family; and
2. the existing immutable publisher copies a complete already-normalized dataset tree
   into a second same-filesystem stage before exposing it.

Those surrogates are not the required research product or the only valid immutable
publication protocol. Keeping them would force a storage purchase or a research-scope
reduction without adding economic information.

## Decision

### 1. Required information is unchanged

ADR-0017's universe, source, temporal, and product contracts remain unchanged. Version-2
sizing may not reduce any of the following:

- the 771 accepted historical membership identities or any selected raw object;
- the 3,144 selected first/midpoint/last whole-day book-ticker/depth objects;
- any economically valid source row in a selected object;
- any source timestamp, price, quantity, volume, notional, rate, count, percentage,
  long/short liquidation value, or source state needed by a required product;
- raw object bytes, provider checksums, retrieval/source-availability semantics, typed
  gaps, censorship labels, or provider/native identity mappings; or
- the required separate products and their clean NautilusTrader catalog-load boundary.

Individual trades, aggregate trades, full historical book-ticker, and full historical
book-depth archives remain out of scope. Receipt 180 and all 98 version-1 envelopes remain
immutable blocked evidence; version 2 writes new content-addressed envelopes and a new
receipt and never overwrites either.

### 2. Size the typed research representation

The capacity envelope must represent the schemas the normalizer is required to publish,
not a generic audit table. Each retained source sample is parsed row by row under its
accepted physical-family schema and projected into every required logical output fed by
that family.

Target columns use fixed-width typed representations:

- timestamps, source row ordinals, update IDs, and trade counts are integers;
- prices, quantities, volumes, notionals, rates, ratios, percentages, and liquidation
  values are finite typed numerics;
- instrument/provider identities and finite state vocabularies use dictionary encoding;
- the cost product retains every valid book-ticker field and every valid book-depth
  field for every selected row; and
- raw object identity is referenced by a compact partition-local key. The immutable
  partition manifest maps that key to the full source key, SHA-256, checksum authority,
  retrieval time, and source-availability metadata once per raw object.

Exact original CSV tokens remain in the immutable raw archive. They are not duplicated as
strings in every normalized row. Typed conversion must parse strictly and reject overflow,
non-finite values, invalid integers, or semantic inconsistency; it may not round a value
silently, replace a missing value with zero, or discard a failed row. The version-2 sizing
receipt pins every target field, type, nullability rule, dictionary rule, logical output,
and writer setting. These identities become the maximum-allocation contract for Gate 3.

### 3. Separate payload from file overhead

The version-1 greatest whole-file ratio is superseded for version-2 normalized sizing.
For each exact physical-family/logical-output pair, the probe measures real retained
samples and separates:

1. encoded column-chunk/data-page bytes;
2. row count and row-group count;
3. footer and per-row-group metadata bytes; and
4. fixed Parquet framing bytes.

The projection groups exact selected compressed objects by the actual logical
product/symbol/UTC-month partition. It applies the greatest observed exact rational
typed-payload-to-compressed-input ratio to each group with integer ceiling arithmetic,
then adds an independently conservative footer/row-group bound and fixed framing once per
projected file. A tiny one-row archive therefore contributes its measured file overhead
to its own projected partition; its footer is not multiplied across all family bytes.

For fixed-cadence products, declared interval/calendar maxima provide an independent row
and row-group ceiling. For event-driven cost objects, the greatest observed exact
row-to-compressed-byte ratio provides that ceiling. The greater applicable bound wins.
Every numerator, denominator, witness, partition count, projected row/row-group count,
payload byte count, overhead byte count, and final file byte count is published. Unknown,
unrepresented, unparseable, or non-integer input blocks sizing.

No mean, quantile, fitted compression estimate, assumed batching credit, arbitrary safety
factor, or outcome-selected sample is allowed. The cohort remains the accepted 96 unique
Binance physical samples plus the exact retained Coinalyze authority.

### 4. Partition-atomic immutable publication

CEX-002 normalized outputs use content-addressed immutable partitions rather than a
second copy of a complete release tree:

1. stream one logical product/symbol/UTC-month partition to a unique bounded temporary
   path on the destination filesystem;
2. verify rows, schema, coverage, raw-object lineage, byte count, and content hash, then
   flush and fsync the file and its parent;
3. reserve its content-addressed final path without clobbering an existing path;
4. atomically rename the verified file into that final path, or strictly verify and reuse
   an identical winner; and
5. expose no release to readers until one final immutable bundle descriptor and catalog
   transaction pins the complete ordered partition set, products, gaps, and manifests.

An interruption may leave verified content-addressed partitions that a replay can reprove
and reuse, but cannot leave a visible partial release. Unreferenced incomplete temporary
files are not datasets and may be cleaned only under explicit ownership. A conflicting
existing content path, manifest, or catalog identity blocks. Publication must prove
concurrent no-clobber behavior, interrupted resume, byte-identical replay, and reader
invisibility before the final bundle commit.

This protocol is a CEX-002 publication adapter at the catalog boundary. It does not weaken
the existing `DatasetPublisher` contract for other tickets or authorize edits to unrelated
catalog work already present in the shared workspace.

### 5. Revised capacity equation

Version-2 capacity reports, without overlap:

1. projected new Binance raw bytes after re-proved retained credit;
2. projected new Coinalyze raw receipt bytes after re-proved retained credit;
3. the typed normalized partition bound;
4. catalog, manifest, membership, gap, and final bundle overhead;
5. bounded temporary work bytes equal to the greatest of the largest accepted compressed
   object, largest projected normalized partition, and explicitly bounded catalog/bundle
   transaction temporary bytes; and
6. the operating reserve frozen by ADR-0021.

The normalized output bytes are counted once. A temporary file that becomes the final
partition by atomic rename is not a second normalized allocation. The conservative
temporary-work component remains additional to the final raw/normalized/catalog bound.

Gate-2 storage is sufficient only if all components are known and their exact sum is no
greater than post-publication available bytes. The sizing command remains measurement
only: a sufficient result does not itself accept Gate 2 or authorize acquisition.

### 6. Versioned evidence and stop boundary

The revised receipt schema is `cex002_gate2_storage_sizing_v2`, and its fixed repository
target is
`research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json`. Version-2 envelopes use a
distinct versioned evidence root and complete measurement identity. Reuse requires exact
byte, schema, writer, policy, source, and authority agreement.

This ADR authorizes implementation and bounded local sizing only through separate reviewer
handoffs. It does not authorize network access, bulk acquisition, normalization, catalog
publication, data deletion, a paid source, a smaller universe or sample, Harmonic Trader
model work, backtesting, PAPER, or LIVE work.

## Consequences

- The accepted v1 run remains a reproducible diagnosis rather than being rewritten.
- The project measures the storage needed by the actual typed products while retaining
  every required row and economic field.
- Immutable publication no longer requires a full second normalized release allocation.
- Gate 2 remains blocked until a reviewed v2 implementation produces a valid sufficient
  receipt and the reviewer accepts that result.
