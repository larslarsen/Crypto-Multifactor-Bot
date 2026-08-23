# CEX-002 Typed Sizing Correction Review

**Date:** 2026-08-23
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `REJECTED_SOURCE_BOUNDARY_REOPENED`
**Architecture:** ADR-0017 and ADR-0021 as amended by ADR-0024 and ADR-0025
**Gate 1:** Prior archive/Coinalyze evidence preserved; release-level source gate reopened
**Gate 2:** Blocked; acquisition is not authorized

## Reviewed drop

Claude edited exactly the three review-232 paths and stopped without integration, evidence
publication, or Git work. The unintegrated identities are:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `a1772979f6ceb979424c865deeb00ad796377170942f1f15292cb4c4a4806866` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `402429f7d12f76b0f818ace989a780a4b5fdfd6885027dc544a5e1a7e4a38e3e` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |

The test file has 109 `def test_` functions. Static whitespace inspection passes. The
reviewer did not execute source, tests, Ruff, sizing, qualification, or an acceptance
command. Read-only inspection covered the exact source drop, accepted report/checkpoint,
repository status/history, and the current FEE-001 row count.

The correction adds exact-decimal and typed-liquidation declarations, required-product
names, physical contribution mappings, real lineage fields, a 300-second metrics cadence,
fixed schemas, and one-allocation capacity arithmetic. Those are directionally correct.
The drop is still not executable against the accepted authority and materially understates
several required products.

## Blocking findings

### 1. The accepted report is rejected before sizing starts

`bind_sample_lineage` rejects every repeated report key at source lines 2315-2324. The
accepted report has 106 sample records and 96 unique keys; ten keys intentionally appear in
two sample regimes. Read-only inspection proved each repeated key has one identical
SHA-256/byte-size/family/retrieval/availability identity, with only its logical regime role
differing. The new duplicate test encodes rejection of the real accepted shape.

The binding must fold agreeing logical aliases to the 96 physical keys and reject only a
lineage disagreement or substituted object, as ADR-0025 specifies.

### 2. The exact-decimal implementation is context dependent

`convert_decimal` uses `Decimal.scaleb` at source lines 1969 and 1988 without an explicit
context. Python's default decimal precision is 28, while the declared Arrow contract is
38 digits. Valid 36- and 38-digit cases already listed as successful in tests at lines
2913 and 2918 are rounded by the ambient operation and then rejected by the equality check.
The source and its tests therefore contradict each other before Hermes runs them.

The conversion must use coefficient/exponent integer arithmetic and context-independent
reconstruction. `convert_timestamp_text` also calls the float-returning
`datetime.timestamp()` at source line 2026 despite claiming an integer-only conversion.

### 3. Partition-local lineage is still charged as a global average

`measure_partition_manifest` writes one cohort-wide file and exposes
`ceil(file_bytes / mappings)` at source lines 2400-2452. Projection then multiplies that
average by `len(members)` at lines 2806-2810. It never adds a footer, row-group metadata,
or framing once for each actual product/symbol/month manifest. Small partitions are
therefore undercounted by exactly the overhead ADR-0024 required to separate.

The only manifest entries are built from the 96 Binance cohort objects at lines
4591-4622. Coinalyze envelopes carry `raw_object_ref`, but no Coinalyze partition maps that
reference to a response receipt or provider/native identity. Coinalyze projected payload
and overhead are also not published as separate totals.

### 4. The declared products are still measurement inputs, not final products

Archive-fed products expose only `ProductContribution` schemas. Trade-flow declares that
sell/imbalance is derivable but allocates no published sell/imbalance fields. Indicative
funding contains premium input fields but no complete target contract. Basis contains
separate mark/index/premium inputs but no causal basis output. OI carries levels without
the required stock/change output semantics. Cost calibration contains quote/depth fields
but no effective fee schedule.

The fixed schemas are also incomplete. Membership has no canonical instrument or contract
version. The bundle has only product/symbol/month/hash/bytes/rows, omitting the schema,
manifest, mapping, source/code/config, unit, censorship, gap, and intersection pins the
ticket requires.

### 5. Known gap storage is understated by more than an order of magnitude

`_measure_fixed_schema_products` constructs gaps only from Coinalyze `unmapped` symbols at
source lines 4042-4053, and the final projection fixes the count to 202 at lines
4668-4669. The accepted report already contains 8,317 product-scoped
`universe_coverage_gaps` across seven products and 3,742 product/symbol typed-gap
memberships. The current schema also drops their family, status, explanation, and real
period fields.

This is not a future-quality estimate; it discards existing accepted evidence. ADR-0025
now pins the 8,317 records as the minimum and separately defines the row-level missing-run
ceiling.

### 6. Cadence and cost authority remain incomplete

The 300-second metrics fix is correct. The new 28,800-second realized-funding ceiling is
not. The retained source has an explicit `funding_interval_hours` column, and Binance has
published four-hour settlement contracts and a standard one-hour interval-adjustment
rule. Eight hours cannot be used as a calendar maximum; ADR-0025 pins one hour until a
stricter complete-history lower bound is proved.

More fundamentally, neither the accepted qualification report nor this drop contains an
effective fee-schedule source. The current `ref_fee_schedule` table has zero rows. The
official `/fapi/v1/commissionRate` API is signed, current, account-specific, and has no
historical interval parameter. A fee schema can be sized, but source completeness cannot
be asserted from current quote/depth data. The release-level source gate is reopened for a
reviewer fee-authority decision before more developer work.

### 7. New test arithmetic still encodes the rejected Coinalyze ratio

The corrected source projects liquidation payload from `group_points * typed_bytes_per_point`
plus per-file overhead. The test at lines 2591-2594 instead feeds
`group_points * raw_point_charge_bytes` into the typed coefficient a second time. Its
expected value cannot equal the implementation except by accidental unit equality. This
is another static source/test contradiction; no test execution is needed to establish it.

## Next authority

No implementation or integration actor is authorized. The next required actor is the Lead
Quantitative Finance Researcher/Engineer, who must publish one evidence-backed decision for
the missing effective-fee source and then issue one complete, bounded senior correction
contract under ADR-0025. The correction contract must cover all seven findings together;
it may not send successive agents back through the same file for isolated symptoms.

This reviewer-authored publication is restricted to exactly:

1. `docs/adr/0025-complete-product-sizing-and-fee-authority.md`;
2. `research/sprint_004/233_CEX002_TYPED_SIZING_CORRECTION_REVIEW.md`;
3. `docs/handoff/CURRENT_TASK.md`; and
4. `tickets/CEX-002.md`.

## Stop boundary

Claude's drop remains unintegrated and unaccepted. No source edit, test, Ruff, sizing run,
fee assumption, credential use, network acquisition, data mutation, Gate-2 acceptance,
bulk download, normalization, catalog publication, Harmonic Trader work, payoff analysis,
PAPER, LIVE, or next-ticket work is authorized. Next ticket remains `NONE`.
