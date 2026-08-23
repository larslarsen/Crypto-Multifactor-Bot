# CEX-002 V3 Disjoint Layout Final Source Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Claude's review-260 correction rejected on one final disjoint-layout residual
- **Architecture:** ADR-0027 remains unchanged
- **Authorized actor:** Sr Dev - Claude Build
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## One static review

The reviewer waited for the completed drop to stop changing, then inspected it once at
these stable identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `9c85bc1ae8bf7c79784d44b8fc3b13a3c36cb350fe1a02ea89bcd597764b99b0` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `6412b99a2df9b3c8eb30486ed29e1ac3f401867847d2c3e03bfa88e88106e5a7` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file has 157 `def test_` functions. The two edited files pass static diff
whitespace validation. The reviewer ran no pytest, Ruff, sizing, qualification, control,
acceptance, network, or data-mutation command.

The correction is substantial and review 260's main findings are resolved. Coinalyze now
uses anchor/incremental/additional terms instead of a complete payload per point; all
applicable derivation cohorts are traversed and finite derived domains survive in the
receipt; exact bundle files carry their actual row-group cardinalities and measured
overhead; every projected identity is checked against the accepted detailed/funding-only
classes; and the v3 exact-layout test model is admitted. Preserve those changes.

## Blocking disjoint-layout residual

The remaining errors share one boundary: some current physical bytes are assigned to a
future owner, while other current terms disappear from the receipt or re-enter the
largest-partition charge. Correct the boundary once across all layouts.

### 1. Reference validity ownership is still mixed by layout

`_traverse_typed_rows` sets both future reference columns' incremental current width to
zero, while `future_reference_identity_bytes` charges index plus validity on every row.
That is not disjoint for fixed-schema, Coinalyze, or exact bundle layouts. Their measured
anchors/files physically contain the nullable columns as null, including the current null
definition/validity representation and page initialization. Zeroing a modeled
incremental width cannot remove those bytes from a measured anchor or exact file; the
future allocation adds validity a second time.

The archive-target and retained-cost path has the opposite gap. It excludes the complete
instrument identity from contribution envelopes, then its target-only allocation adds
only venue, native symbol, and reference-state dictionaries. It does not allocate the two
declared current-null reference columns at all. A global future owner therefore happens
to cover their validity there while duplicating it in the other layouts.

Use one rule everywhere:

- the current target schema owns the two null-validity terms and their current page
  initialization in every applicable archive, cost, fixed-schema, Coinalyze, and exact
  bundle layout;
- the future reference allocation owns only the dictionary indices and accepted opaque
  values/offsets that do not exist yet; it owns no second validity or current page term;
- current modeled incremental width is therefore one null-validity term per reference
  column, not zero, and archive/cost target-only identity allocation must add the same
  current-null representation explicitly;
- the future per-row reference term becomes two four-byte indices, not two
  index-plus-validity terms; and
- the receipt must name both owners and reconcile current plus future for each layout.

Do not mark a physically nullable column non-null merely to obtain the arithmetic. Keep
schema nullability true and expose the separate validity owner in the allocation record.
For an empty class scope, publish zero row groups and zero cardinality (or omit the empty
scope); never publish cardinality one for zero rows. Enforce the structural subset that a
version cardinality cannot exceed its instrument cardinality.

The same residual remains in `future_lineage_field_bytes`: projected Coinalyze response
byte/row counters already exist as null columns in the measured current manifest, but the
future term adds `INTEGER_WIDTH + NULL_VALIDITY_WIDTH` for each. It must add only the two
future integer values; current manifest validity remains the sole owner.

### 2. Coinalyze anchors cover only the two retained identities

The new Coinalyze ledger takes independent maxima from envelopes written for the retained
liquidation response. That response covers only `BTCUSDT_PERP.A` and `ETHUSDT_PERP.A`,
while the accepted projection contains 569 proved native/provider mappings. Real accepted
identities such as `1000000BOBUSDT` are wider than either retained anchor. The current
anchor/additional term therefore has neither the complete maximum native/provider value
width nor an explicit delta for the wider accepted partition-constant value.

Bind Coinalyze's venue, native symbol, provider symbol, reference state, and other
dictionary inputs to the complete accepted projected mapping/domain. It is valid to use a
real retained point for fixed-width numeric facts, but the identity cardinality and
maximum widths must come from all 569 accepted mappings, not the two retained series.
Publish the aggregate row, row-group, cardinality source, maximum width, anchor,
incremental, additional-value, overhead, manifest, exact-total, and largest-partition
facts. Independent maxima may conservatively combine real witnesses, but the receipt must
identify and retain every input that produced them.

### 3. Shared current identity facts disappear from the receipt

`cost_identity_allocation(objects, rows=0, row_groups=1)` computes the venue/native/state
column allocations, but `run_storage_sizing` extracts only one scalar dictionary byte
total. Archive and cost `target_only_allocation` records consequently omit the column
cardinalities, authority source, maximum value widths, row-index bytes, dictionary-value
bytes, and the new current-null reference terms. Listing column schemas beside three
scalar rates is not the independently recomputable ledger ADR-0027 requires.

Retain the full shared-current identity allocation through every applicable
product/component projection and stable receipt. Its per-product rows, row groups, anchor
or page-initialization term, incremental/current-null terms, per-column cardinality and
value-width facts, dictionary values, and exact total must reconcile with
`projected_target_only_bytes`. The shared identity is a current allocation, not a future
width.

### 4. Exact and future largest-partition charges do not describe the layout

`project_fixed_schema_product` uses exact measured payload and exact measured overhead for
an exact one-partition file, but computes `largest_partition_bytes` with the generic
ceiling-derived footer-per-row-group expression. The bundle/scenario exact branch must set
the one partition's largest bytes to the same measured file bytes used by the exact total;
no ceiling-derived overhead may enter that result.

The future largest charge then adds `instrument_identity_allocation`'s row-group
dictionary even though the source comment correctly says shared identity is already
inside the current product allocation. That counts a current dictionary twice. At the
same time it adds only one reference dictionary to candidates that can span multiple row
groups. The exact bundle needs the sum of its actual per-row-group reference scopes, and
any other multi-row-group partition must repeat its applicable reference dictionary in
every actual row group.

Compute the future charge from real partition row counts, row-group counts, and accepted
membership class. Do not combine one partition's row count with an unrelated scope's
dictionary cardinality without retaining that conservative construction explicitly. The
largest current plus future bound may remain conservative, but every candidate term must
fully cover its own physical layout and contain no byte already owned by current storage.
Publish enough per-layout facts to recompute the selected maximum.

### 5. Test source freezes the rejected owners and contains a real contradiction

The new validity test asserts current reference width zero and future width ten, which
freezes the mixed ownership above. Direct bundle/reference tests make the same assumption.
They must instead prove current null validity plus future index/value allocation across
archive target, retained cost, modeled fixed-schema, Coinalyze, and exact bundle paths.

`test_the_v3_capacity_terms_reconcile_exactly` also attempts to exclude a scope named
`harmonic_bundle_descriptor` before asserting instrument cardinality one. The source emits
`harmonic_bundle_row_group_<n>` scopes, whose exact accepted cardinality may be greater
than one. The condition therefore contradicts the exact bundle grouping it is intended
to prove.

Add or correct focused tests that directly prove:

1. one current validity owner and one future index/value owner in every layout;
2. future Coinalyze response counters do not add a second validity term;
3. an accepted Coinalyze mapping wider than both retained anchors increases the bound;
4. complete shared-current identity allocation facts survive projection and receipt;
5. an exact one-partition layout has `largest_partition_bytes == file_bytes`;
6. multi-row-group and exact-bundle future dictionaries repeat by their actual groups,
   while current shared identity is absent from the future charge; and
7. single-identity scopes have cardinality one, empty scopes zero, and bundle scopes keep
   their actual accepted cardinality rather than being forced to one.

Preserve every accepted semantic, tamper, publication, stable-reuse, idempotence,
wholeness, redaction, collision, no-follow, race, v1/v2 immutability, full-universe,
full-product, full-row, cost-sample, quality-gap, lineage, reserve, and six-component test.
Do not delete, skip, xfail, weaken, or replace one to make the new assertions pass.

## One complete correction

Claude may continue editing only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

Leave `scripts/research/size_binance_usdm_harmonic_release.py` byte-identical. Continue
from the review-260 drop in place and preserve every accepted improvement named above.
This is corrective implementation of accepted ADR-0027; no ADR amendment or new research
contract is authorized.

## Exact Claude authorization and stop

Do not reset, restore, checkout, stash, discard, or replace either edited file wholesale.
Do not run commands, tests, Ruff, sizing, qualification, control, Git, network,
acquisition, normalization, data/evidence, or documentation work.

Stop once after this complete two-file correction. Report SHA-256 for both edited paths
and the unchanged CLI, plus the final `def test_` function count. Grok, Spark, Hermes,
integration, execution, acquisition, and later work remain unauthorized pending one
reviewer static acceptance. Receipt 258 remains absent, Gate 2 remains not accepted, and
next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/261_CEX002_V3_DISJOINT_LAYOUT_FINAL_SOURCE_REVIEW.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

Developer source/test/CLI paths, receipts, evidence, and unrelated dirty work are excluded.
