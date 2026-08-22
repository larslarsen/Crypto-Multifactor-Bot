# ADR 0021 - Bounded Real-Sample Storage Sizing

- **Status:** Accepted
- **Date:** 2026-08-21
- **Amends:** ADR-0017 storage preflight and ADR-0020 section 5
- **Evidence:** `research/sprint_004/179_CEX002_GATE1_ACCEPTANCE_AND_STORAGE_SIZING_ARCHITECTURE.md`

## Context

CEX-002 Gate 1 passed against real sources at report SHA-256
`bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227`.
The report proves 7,833,966,625 selected Binance compressed bytes and 12,522,974,218
complete cost-sample compressed bytes. After 5,225,416 bytes of verified retained credit,
the projected new Binance raw requirement is 20,351,715,427 bytes.

That is not yet a Gate-2 capacity decision. It excludes the full supported-symbol
Coinalyze liquidation receipts, normalized/catalog outputs, immutable-publication staging
space, and an operating reserve. The current report correctly leaves those components
unknown.

Gate 1 retained 96 unique physical Binance samples referenced by 106 logical sample rows.
They cover 12 exact physical archive families and headed/headerless forms. It also retained
the official Coinalyze market inventory and real BTC/ETH daily liquidation, OI, funding,
and price responses. These are the outcome-blind real samples used for bounded sizing.

## Decision

### 1. Frozen sizing authority

The sizing probe is pinned to the accepted Gate-1 report, manifest detail, version-4 lock,
amendment ledger, source identities, retained content paths, and provider checksums. It
accepts no caller-selected universe, family, sample, multiplier, quantile, compression,
reserve, output multiplicity, or storage credit.

The Binance cohort is exactly the 96 unique retained physical samples in report 62. A
logical alias is not measured twice. Every sample is rehashed, its provider sidecar is
re-proved, its ZIP members are inspected, and every data row is parsed under the declared
family schema. Missing, corrupt, empty, unparseable, or unrepresented required families
block sizing. No outcome-based replacement is permitted.

The Coinalyze cohort is the retained market inventory plus the exact qualified BTC/ETH
daily responses. The full raw projection covers the 569 report-supported Binance
perpetual mappings for the daily liquidation endpoint. OI, funding, and price remain
bounded overlap-reconciliation evidence; they are not silently expanded into a second
full historical panel.

### 2. Lossless normalized envelope

For every unique Binance sample, the probe writes a lossless sizing envelope with one
output row per parsed source row. It preserves every source token plus family, symbol,
economic interval, source key, and row ordinal. The envelope is written as PyArrow Parquet
with Zstandard compression and deterministic writer settings. It records source compressed
bytes, ZIP-extracted bytes, parsed rows, uncompressed Arrow IPC bytes, Parquet bytes, and
file/footer overhead. Envelopes are published content-addressably and an existing envelope
is reusable only after its bytes and complete measurement identity re-prove.

The per-family projection ratio is the greatest observed envelope-Parquet-to-source-
compressed ratio among all retained samples in that exact physical family. Integer
rational ceiling arithmetic applies the ratio to the exact compressed bytes required for
that family. No mean, fitted distribution, hidden safety factor, or fixed-N universe
projection is allowed.

The required logical-output multiplicities are fixed:

| Physical family | Output multiplicity | Reason |
|---|---:|---|
| daily/monthly `klines` | 2 | bars plus derived taker flow |
| daily/monthly `metrics` | 1 | OI/positioning metrics |
| monthly `fundingRate` | 1 | realized funding |
| daily/monthly `premiumIndexKlines` | 2 | indicative funding plus basis input |
| daily/monthly `markPriceKlines` | 1 | basis input |
| daily/monthly `indexPriceKlines` | 1 | basis input |
| daily `bookTicker` | 1 | cost calibration |
| daily `bookDepth` | 1 | cost calibration |
| Coinalyze daily liquidation | 1 | observed/censored liquidation |

This deliberately overstates combined basis storage and row-preserving cost output. A
later normalizer may use less space, but it may not exceed its frozen family allocation.
Exceeding any allocation stops Gate 3 and requires a new reviewed sizing version.

### 3. Coinalyze raw and normalized projection

For each qualified endpoint response, the probe records exact response bytes, response
framing bytes, point counts, and bytes per point. The liquidation projection uses the
greatest observed integer-ceiling bytes per point and the greatest observed per-symbol
response framing charge. It assumes one symbol per request, so it receives no unproved
batching credit.

For each of the 569 mapped contracts, the projected daily row count spans its authenticated
available lifecycle through the accepted qualification cutoff. A missing lifecycle bound
blocks rather than assuming zero history. The raw receipt projection, normalized lossless
envelope projection, future-market inventory receipt, and retained-credit calculation are
reported separately. API keys never enter a URL, receipt, sizing artifact, or log.

### 4. Catalog and partition overhead

Normalized output is bounded to at most one file per logical product, symbol, UTC month,
and source family. The probe derives the output partition count from the accepted manifest,
cost keys, supported Coinalyze lifecycles, and fixed multiplicities.

Catalog/manifest overhead reserves one 4,096-byte page for every physical raw object,
projected normalized output file, typed gap record, membership row, and Coinalyze receipt,
plus the exact current report and manifest-detail bytes. This is an explicit storage
contract, not an empirical data multiplier. Publication must stay within it or stop.

### 5. Temporary high-water and reserve

The existing immutable dataset publisher copies verified staged outputs into its own
same-filesystem publication stage before the final rename. Sizing therefore counts a full
second normalized/catalog allocation as temporary high-water. It also adds the larger of:

- the accepted largest selected compressed object, 200,457,493 bytes; and
- the greatest projected normalized partition.

Normalization must stream ZIP members in batches of at most 65,536 rows and may not write
a whole extracted archive to disk. The batch cap is a memory contract, not disk credit.

The operating reserve is frozen at sizing time as the greater of 16 GiB and one fifth of
the pre-write available bytes on the destination filesystem, rounded upward. It is never
recomputed downward on a later run. The capacity comparison uses available bytes measured
after all retained sizing evidence is durably published. The receipt reports pre-write
available bytes, post-publication available bytes, and retained sizing-evidence bytes so
the evidence cost is visible without adding it again to the future-storage equation.

### 6. Gate-2 capacity equation

The sizing receipt reports, without overlap:

1. projected new Binance compressed raw bytes after verified retained credit;
2. projected new Coinalyze raw receipt bytes after verified retained credit;
3. the normalized/catalog bound, including fixed logical fan-out and catalog overhead;
4. temporary high-water;
5. the frozen operating reserve; and
6. their exact integer sum.

Gate-2 storage is `sufficient` only if every component is known, every required family and
Coinalyze lifecycle is represented, the retained credits re-prove, and current available
bytes are at least the frozen total. Otherwise it is `blocked`; a partial estimate never
passes. `Sufficient` is a storage-preflight result only; the sizing tool cannot accept
Gate 2, authorize acquisition, or change ticket state.

### 7. Execution boundary

Sizing is local and bounded. It performs no network call, raw acquisition, reservation,
qualification rerun, report-62 rewrite, plan/lock/ledger/checkpoint mutation, normalization
publication, catalog registration, or deletion. It may write only its content-addressed
sizing-envelope evidence and one versioned sizing receipt. Source implementation, source
integration, sizing execution, Gate-2 acceptance, and raw acquisition are separate
reviewer gates.

## Consequences

- Gate 1 is complete without pretending release coverage is complete.
- The 20.35 GB Binance figure is retained as an exact raw component, not mislabeled as the
  whole release.
- Coinalyze raw provenance and logical-output fan-out cannot disappear from capacity
  planning.
- Immutable publication's real duplicate-stage cost is budgeted before acquisition.
- No storage purchase, reduced universe, reduced cost sample, or bulk download is implied
  by this ADR.
