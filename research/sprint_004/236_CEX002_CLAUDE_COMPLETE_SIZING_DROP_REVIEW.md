# CEX-002 Claude Complete Sizing Drop Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Rejected before integration; one complete residual correction authorized
- **Authorized actor:** Sr Dev - Claude Build
- **Integration actor after source acceptance:** NONE

## Reviewed state

The reviewer inspected the complete review-234/235 Claude drop once at these identities:

- sizing source: `01242910ffe80e275c58967c82164c7a27cbcf884c0973fba386694000a04727`;
- sizing tests: `e12636643be9fa258cb4bf66a6dd9b82cd83350eda8c0ad4a274c05c3fd6790a`;
- unchanged sizing CLI:
  `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c`;
- test functions: 123.

No reviewer pytest, Ruff, sizing, qualification, control, acceptance, network, or data
command was run. Static inspection is decisive because the production path rejects the
actual accepted authority before sizing and the liquidation writer cannot construct its
declared schema. Integration and execution are rejected.

The drop does correctly implement the accepted 106/96/10 alias decomposition,
context-independent fixed-decimal reconstruction, integer epoch conversion, 300-second
metrics, one-hour funding ceiling, the two fixed fee scenario values, and the corrected
single application of Coinalyze raw and typed coefficients. Preserve those corrections and
all previously accepted v1 immutability, authority-pin, no-network, no-credential,
content-addressed publication, path, race, symlink, reserve, and idempotence protections.

This is one consolidated review. The findings below are the complete residual defect set
for the next source drop; no separate finding-by-finding handoff is authorized.

## Blocking findings and exact correction

### 1. The real accepted authority is rejected immediately

`prove_coverage_authority` at reviewed source lines 2894-2904 counts every membership
classification and requires 771 rows. The pinned report actually contains 1,008
classification records, exactly 771 of which have `accepted == true`. It therefore fails
before fee-gap creation, fixed-product measurement, or receipt construction. The compact
test fixture at reviewed test lines 560-565 contains only three accepted records and hides
the defect.

Filter structurally valid classifications by `accepted is True`, require exactly 771
accepted identities, and retain the 237 rejected classifications only as proved exclusion
evidence. Fee-authority gaps and accepted membership sizing use exactly those 771 rows.
Add one end-to-end source test that loads the already accepted local report and authority
files and reaches complete receipt construction with durable publication redirected to a
temporary location. The test must assert the real 1,008/771 membership split, not just
compare constants or a synthetic fixture.

### 2. Membership and identity sizing invents reference truth

Reviewed source lines 4585-4593 fabricate `BINANCE_USDM:<symbol>:v1` as a canonical
instrument/version pair. REF-001 canonical IDs are opaque `ins_` and `iv_` fingerprints
whose inputs are created by `ReferenceStore`; no accepted Gate-1 artifact has created those
reference rows yet. A sizing probe may allocate their deterministic encoded widths, but it
may not publish ticker-derived strings as accepted canonical identities.

Reviewed source lines 4910-4925 also treat `symbol_snapshot[symbol]` as a metadata object.
The pinned contract file actually maps each symbol to a snapshot digest, while the accepted
classification's `evidence` records carry contract type, base, quote, margin, onboard,
close/status, and source identity. The fallback then hard-codes USDT margin and settlement,
which is false for accepted USDC and BUSD contracts.

Correct this boundary as follows:

- size exactly the 771 accepted native membership rows from their accepted evidence;
- preserve the real membership class/regime, base, quote, margin, contract type, lifecycle,
  and evidence/snapshot identity without ticker-suffix inference or USDT defaults;
- represent canonical instrument and version as future Gate-3 fields and allocate the exact
  REF fingerprint widths and encoding overhead separately, explicitly labelled as a schema
  width allocation rather than an existing ID;
- never write a fake canonical ID/version into a measurement row, bundle row, gap row, or
  liquidation row;
- fail on conflicting accepted evidence rather than selecting a convenient record.

### 3. Final product writers and derived semantics are not executable

`LIQUIDATION_COLUMNS` requires four identity fields plus imbalance, interval, censorship,
and event-completeness fields. `write_liquidation_envelope` at reviewed source lines
4264-4274 instead supplies undeclared `venue_symbol`, omits every required identity field,
and omits all four derived/semantic fields. Arrow cannot construct that table with the
declared schema.

The derived measurement path is also not causal. Reviewed lines 5570-5589 overwrite each
family sample across the 96-object cohort and retain one unrelated first symbol. Lines
5630-5645 then combine the surviving samples for every product. Basis derivation at lines
4813-4853 joins mark and index rows by ordinal and minimum length without proving equal
native symbol, open time, close time, or overlapping premium input. OI derivation at lines
4752-4778 labels a discontinuity `gap_break` but still publishes the previous comparable
and a change across the gap. The generic fallback at lines 4856-4857 can measure an
identity coefficient from an unrelated first family.

Group real samples by native symbol and economic interval before deriving target rows.
For basis, inner-join mark, index, and premium on identical native symbol, open time, and
close time; fail or mark the target witness unavailable when no such real join exists.
For OI, keep the observed interval and `gap_break` status but set previous comparable and
both changes null whenever the interval is not exactly 300 seconds. For liquidations,
write every declared field, use the proved native/provider mapping, store the daily source
interval, set `event_complete=false`, use the accepted censored-observation label, and
define imbalance as exact `long_liquidation - short_liquidation` with positive meaning
long-liquidation dominated. Every writer must round-trip through its own final schema.

### 4. Cost calibration must remain five separately typed components

Reviewed `final_product_columns` lines 1758-1783 flatten book-ticker, book-depth, and fee
scenario fields into one non-null row shape. Those are heterogeneous ADR-0026 components,
not columns that coexist in every cost row. There is no official fee-schedule component
schema, the 771 fee gaps are treated only as generic coverage rows, and scenario
measurement uses a different schema from the claimed final cost schema.

Model `binance_usdm_cost_calibration` as a product descriptor containing five component
schemas and projections:

1. retained book-ticker rows;
2. retained book-depth rows;
3. a complete effective fee-schedule schema with tier/rates, valid interval, availability
   interval, authority/evidence/source identity, and exactly zero rows for this release;
4. exactly 771 accepted-identity-scoped historical-fee-authority gap rows; and
5. exactly two global venue/product scenario-policy rows with all ADR-0026 fields.

Allocate each component's schema, rows, partition/catalog/manifest costs, and receipt count
separately, then sum them once into the cost product. The assumed scenarios are global
configuration, not fake instrument observations and not FEE-001 rows. Zero official rows
must still retain and pin the official-component schema; absence never becomes zero cost.

### 5. Accepted coverage evidence is discarded or mis-sized

The pinned matrix contains exactly 8,317 source-gap records and 3,742 separate typed-gap
product/symbol memberships. Of the source-gap records, 6,466 name two physical families,
1,649 name one, and 202 name none. Reviewed `_coverage_gap_row` lines 5016-5036 keeps only
the first family, drops accepted family and interval evidence, and renames
`first_observed`/`last_observed` as missing bounds. The 3,742 typed-gap memberships are
counted but receive no row schema or storage allocation.

Preserve each of the 8,317 accepted source-gap records losslessly in structured typed
columns, including the full family list and family first/last evidence; do not explode or
truncate them and do not reinterpret observed bounds as missing bounds. Store and size the
3,742 typed-gap memberships as a separate typed component. Store and size the 771 fee gaps
as another distinct component. Keep all three counts separate in the receipt.

Reviewed lines 5701-5708 apply `ceil(rows/2)` after aggregating an entire product. Instead,
materialize the projected fixed-cadence product/native-symbol/UTC-month partitions and sum
`ceil(expected_rows / 2)` independently for every partition. Do not reserve inferred
absence for event-driven products. Report source gaps, typed-gap memberships, fee gaps,
and projected quality gaps separately before their byte totals are combined.

### 6. Lineage and bundle sizing use global or fabricated witnesses

Reviewed `model_partition_lineage` lines 2813-2849 writes one cohort-global manifest and
one first-row manifest. The declared manifest has no native-symbol/month/partition key,
and the Coinalyze loop merely applies `partition_bytes(1)` without constructing the promised
receipt/provider/native mapping. This does not prove or measure distinct
product/native-symbol/UTC-month manifests.

Build the projected partition set first. For every archive and Coinalyze partition, create
the local mapping set with the actual product, native symbol, UTC month, raw object or
projected response receipt, source hash, availability facts, and provider/native identity
where applicable. Measure or conservatively bound that partition's payload, row-group
footer, and framing independently. Sum every partition; expose mapping count, partition
count, payload, overhead, and largest partition. There is no extra cohort-global manifest
copy.

Reviewed bundle lines 4954-4984 use all-zero partition and manifest hashes, zero byte/row/
mapping values, a contribution count as the cross-product intersection, an incomplete code
pin, and a scenario hash over only `policy_known_at`. Do not create a fake completed bundle
row during sizing. Allocate known fixed-width future fields as explicitly labelled schema
width charges, and measure real values only where they already exist. Pin the complete
source/code/configuration/schema/scenario policy identity set; hash both complete scenario
rows; derive cross-product intersections from the actual projected partition sets. Receipt
arithmetic must include every bundle descriptor, schema, manifest, catalog page, temporary
file, and self-size exactly once.

## Required correction tests

Keep all existing protections and add or strengthen tests that directly prove:

1. the real local authority passes the 1,008-total/771-accepted membership boundary and
   completes the receipt path in a temporary publication root;
2. rejected membership rows never create fee gaps or accepted membership rows;
3. native membership fields come from accepted evidence, including non-USDT examples, and
   no ticker-derived canonical ID/version is published as reference truth;
4. every final writer constructs and round-trips its exact schema, especially liquidation
   and all five cost components;
5. an OI time gap nulls the previous comparable and changes, and mismatched symbol/time
   mark/index/premium rows never receive `causal_open_time_join`;
6. all 8,317 source gaps survive losslessly, all 3,742 typed-gap memberships are allocated,
   all 771 fee gaps are separate, and partition-local quality ceilings sum independently;
7. two differently sized partitions each pay their own full manifest overhead, with exact
   sum assertions rather than a divided lower bound, and Coinalyze manifests carry actual
   receipt/provider/native fields;
8. the bundle contains no zero/fabricated witness values, pins complete policy/code/config
   identities, and derives real intersection counts;
9. zero official fee rows and two scenario rows remain structurally distinct from 771 fee
   gaps; and
10. the accepted 106/96/10, exact numeric/time, cadence, Coinalyze-unit, security,
    immutability, capacity-boundary, and byte-identical-rerun protections remain unchanged.

Synthetic unit fixtures remain useful, but they cannot replace the real-authority
end-to-end test. A test that only asserts pinned integer constants is not authority proof.

## Exact authorization and stop

Claude Build may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`;
3. `scripts/research/size_binance_usdm_harmonic_release.py`.

Work from the current shared drop in place. Do not reset, restore, checkout, discard, or
wholesale replace it. Close all six findings and all ten test requirements in one source/
test drop; a partial subset is not a deliverable. Claude does not run commands or tests,
mutate evidence/data, use Git, or write research, ticket, handoff, ADR, receipt, envelope,
database, manifest, or catalog records. Stop once with SHA-256 for all three allowed paths,
marking an unchanged path explicitly, plus the final `test_` function count.

Grok remains unavailable and deauthorized for this drop. No integration actor is
authorized until reviewer static acceptance. Gate 2 remains blocked, bulk acquisition and
all later work remain unauthorized, and next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS.md reviewer exception, the reviewer may stage, commit, and push exactly:

- `research/sprint_004/236_CEX002_CLAUDE_COMPLETE_SIZING_DROP_REVIEW.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

The three developer paths and all unrelated dirty work are excluded.
