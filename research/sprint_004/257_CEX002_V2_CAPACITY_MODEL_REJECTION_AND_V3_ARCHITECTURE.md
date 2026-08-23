# CEX-002 V2 Capacity Model Rejection and V3 Architecture

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** record 256 integration accepted; receipt 231 retained as diagnostic but rejected as Gate-2 capacity authority
- **Architecture:** ADR-0027
- **Authorized actor:** Sr Dev - Claude Build
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## One review outcome

Hermes's record 256 and commit
`a88e9109284448a01276ce48e97dc5e97a3ff8dd` are accepted as a faithful execution of
review 255. The commit is at `HEAD == origin/main` and contains exactly the two accepted
sizing paths, record 256, receipt 231, and the two control-plane paths. Focused pytest,
exact-path Ruff, the first real sizing invocation, and one identical idempotence
invocation all exited 0. The second invocation published no envelope and reused all 151.

Integrated identities are exact:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `39eff6a986e114b1c07f5af976709179a8ec5c5ad5d113b6dc4ae743df60d468` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `96c9bb542c32d0e1b4161e3d2b0c247c1496dd926662096ffac3a03624bca165` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |
| `research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json` | `d3b2e81e46ecb17ea98dee160a98a551720b4bb27f5c29497839081acabaad29` |

The test file has 144 `def test_` functions. The reviewer ran no pytest, Ruff, sizing,
qualification, control, acceptance, network, or data-mutation command.

## What receipt 231 proves

Receipt 231 is byte-stable, internally reconciled, and reports its implemented equation
exactly:

| Component | Bytes |
|---|---:|
| new Binance raw | 20,351,715,427 |
| new Coinalyze raw | 30,580,702 |
| typed normalized partitions | 584,035,445,256 |
| catalog/manifest/bundle | 5,556,368,003 |
| bounded temporary work | 5,556,368,003 |
| operating reserve | 30,901,349,581 |
| implemented v2 total | 646,431,826,972 |
| post-publication available | 154,464,187,767 |
| implemented v2 shortfall | 491,967,639,205 |

The source download remains 20.382 decimal GB / 18.983 binary GiB. There is no hidden
full trade tape, aggregate-trade tape, full book history, Tardis purchase, or terabyte raw
source. The large result is almost entirely a normalized maximum-allocation model.

## Blocking sizing defect

The receipt arithmetic is correct for the implemented coefficients, but those coefficients
do not implement ADR-0024's partition-aware dictionary and separated-overhead contract.
Three facts dominate:

| Allocation | Rows | Bytes |
|---|---:|---:|
| future reference identity | 1,610,286,520 | 246,373,837,560 |
| projected quality-gap product | 216,934,972 | 191,920,661,196 |
| retained book ticker plus book depth products | 958,878,695 | 107,947,605,573 |

`measure_maximum_width_product` writes one synthetic widest row. For quality gaps that
one-row column-chunk payload becomes 883 bytes per row, and
`project_fixed_schema_product` multiplies it by all 216,934,972 projected rows. Dictionary
pages and data-page initialization from the one-row file are therefore repeated per row,
not per output row group. This recreates the tiny-file amplification ADR-0024 removed.

`future_reference_identity_bytes` charges each opaque value, offset, index, and validity
byte on every row. `cost_identity_bytes_per_row` similarly repeats venue, native symbol,
and reference-state dictionary values on every quote/depth row. These values are constant
or authority-bounded within the declared product/component/native-symbol/UTC-month
partition. Dictionary indices are row costs; dictionary values and initialization are
row-group/cardinality costs. Treating both as per-row strings is not the selected physical
representation.

Receipt 231 therefore remains immutable reproducible diagnostic evidence, but its blocked
capacity state is rejected as a Gate-2 decision. It neither authorizes acquisition nor
proves that the corrected complete release needs 646.4 GB.

## One v3 correction contract

Claude may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

Leave `scripts/research/size_binance_usdm_harmonic_release.py` byte-identical.

### A. Implement ADR-0027 dictionary allocation

Replace every per-row repetition of dictionary value bytes with an explicit allocation
that separates row indices/validity, distinct values and offsets, and one conservative
payload anchor per projected row group. Publish cardinality, value-width, row, row-group,
anchor, incremental-row, and total terms so the receipt can be recomputed without source
code.

The partition key proves venue, native symbol, product, component, UTC month, fixed state,
gap kind, and gap reason where applicable. Data-dependent dictionaries use the complete
accepted values. Do not assume a value is constant merely to reduce storage, assume
compression not proved by the writer, use a mean or quantile, or omit a validity/index
term.

Separate `_INSTRUMENT_IDENTITY` from other target-only derived fields so one shared
partition-aware identity allocation is charged exactly once for every applicable product,
including both retained cost components. Do not double-count the existing
`venue_symbol`, raw-object reference, or source-row ordinal contribution fields.

### B. Bind future reference cardinality without invention

Allocate one canonical instrument fingerprint per accepted native identity and only
snapshot/version fingerprints supported by the accepted contract authority. The current
bound is at most one snapshot-backed version for a detailed identity and zero for a
funding-only identity. Allocate dictionary indices on applicable rows and accepted values
in row-group dictionaries. Rows outside supported effective coverage remain null with an
explicit reference state/gap; do not backdate the current snapshot or fabricate per-row
versions.

The receipt must publish detailed/funding-only identity counts, accepted version
cardinality, null/gap coverage rule, value widths, row-group repetition, and exact bytes.
Any unbounded future cardinality blocks. Later authority that exceeds the v3 bound forces
a sizing rerun before Gate 3.

### C. Correct quality-gap and bundle projection

Keep every real product/native-symbol/UTC-month quality partition and the exact
`ceil(expected_rows / 2)` reservation. Charge a conservative one-row/page/dictionary
anchor per projected row group, then only incremental fixed values, dictionary indices,
validity, and cardinality-required dictionary values for additional rows. Never multiply
one row's page initialization by the row count.

Measure the bundle's complete known projected row set, or use an exactly equivalent
batch/cardinality calculation. Preserve high-cardinality values such as distinct dataset
identities; do not treat them as constants. Publish the exact calculation and keep the
largest-partition and temporary-work equations consistent with the corrected terms.

### D. Version and preserve evidence

Change the corrected receipt schema/path/root to exactly:

- schema `cex002_gate2_storage_sizing_v3`;
- receipt `research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`;
- envelopes `evidence/sizing/v3/envelopes/sha256`.

Receipt 231 and every v1/v2 envelope are immutable. V3 publication, prior comparison,
stable-capacity comparison, content-addressed reuse, collision refusal, no-follow, race,
receipt wholeness, canonical first-return/rerun equality, and redaction protections must
remain strict at the new identities.

### E. Focused proof source

Preserve all 144 existing tests except assertions that deliberately freeze the rejected
per-row value equation. Add focused tests proving:

- doubling rows inside one row group repeats indices/fixed widths but not constant
  dictionary values or the row-group anchor;
- adding a row group recharges exactly one anchor and its dictionary values;
- different symbols/versions increase proved cardinality and unbounded cardinality blocks;
- detailed versus funding-only reference allocation never invents or backdates an ID;
- cost identity is charged once and partition-locally for both retained components;
- quality-gap rows remain exactly `ceil(N / 2)` while one-row initialization is not
  multiplied by those rows;
- the complete bundle preserves genuinely high-cardinality dictionary values;
- the v3 normalized, largest-partition, temporary-work, and six-component capacity sums
  reconcile exactly; and
- receipt 231 plus all v1/v2 evidence remain byte-identical and are never v3 targets.

Do not delete, skip, xfail, weaken, or replace a semantic/tamper/publication test merely to
obtain a smaller capacity number.

## Exact Claude authorization and stop

Work from the integrated paths in place. Do not reset, restore, checkout, stash, discard,
or replace either file wholesale. Do not run commands, tests, Ruff, sizing, qualification,
control, Git, network, acquisition, normalization, or data/evidence work. Do not edit any
CLI, ADR, research, ticket, handoff, receipt, manifest, database, catalog, v1/v2 evidence,
or unrelated path.

Stop once after the complete two-path production/test correction. Report SHA-256 for both
edited paths and the unchanged CLI, plus the final `def test_` function count. Grok,
Spark, Hermes, integration, execution, acquisition, and later work remain unauthorized
pending one reviewer static acceptance. Gate 2 remains not accepted and next ticket
remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/adr/0027-partition-aware-dictionary-storage-sizing.md`;
- `research/sprint_004/257_CEX002_V2_CAPACITY_MODEL_REJECTION_AND_V3_ARCHITECTURE.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

Developer source/test/CLI paths, receipt 231, data evidence, and unrelated dirty work are
excluded.
