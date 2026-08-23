# CEX-002 V3 Complete Allocation Residual Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Claude's review-259 correction rejected on one complete-allocation residual
- **Architecture:** ADR-0027 remains unchanged
- **Authorized actor:** Sr Dev - Claude Build
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## One static review

The reviewer inspected Claude's complete review-259 retry once at these identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `d2fa39fff423fab629f56048fc002a68bc5d76f5c0d3355c3b047866d2f8df71` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `e896c2f0c8dca965c93714315e2ead0011d324cbc0dc1e8afcf8ec8b2e96aafb` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file has 155 `def test_` functions. The reviewer ran no pytest, Ruff, sizing,
qualification, control, acceptance, network, or data-mutation command.

The retry correctly changes the stable policy identity to ADR-0027 v3, removes the unused
`identity_rows`, subtracts an anchor row's own dictionary value from the additional-value
term, recharges anchors when a complete witness is regrouped, writes the bundle's complete
row set, and splits the main native partition scope into detailed and funding-only version
cardinalities one and zero. Those changes remain the implementation base.

## Blocking complete-allocation residual

The receipt is still not a disjoint, recomputable representation of every projected
physical layout.

### 1. Current-null and future-reference validity overlap

`_traverse_typed_rows` allocates one null-validity byte per current null canonical
instrument/version field on every incremental row, while the one-row anchor already
contains the anchor row's null encoding. `future_reference_identity_bytes` then allocates
an index **and another validity byte** for both fields on every applicable row. The final
sum adds the current normalized projection and the future allocation, so nullable
validity is counted twice. The new nullable test checks one helper in isolation and does
not reconcile the two owners.

The same ownership audit is still required for other currently-null fields whose future
values are added separately. `future_membership_term_bytes`, `future_bundle_field_bytes`,
and `future_lineage_field_bytes` must add only bytes not already present in their current
typed/manifest representation. `future_quality_gap_bound_bytes`, which adds the future
integer value width without adding a second validity byte, is the relevant pattern. One
physical validity/index/page/value term must have one owner.

### 2. Coinalyze still uses the rejected scalar payload model

`project_coinalyze` selects a complete Parquet `bytes_per_point` from a retained
liquidation envelope and multiplies it by every projected point. That payload contains
dictionary values, dictionary indices, nullable reference encodings, and data/dictionary
page initialization. It therefore repeats row-group initialization and constant identity,
provider, state, and semantics values per point. This is the same rejected equation that
ADR-0027 removed from fixed-schema products. Coinalyze partitions must use disjoint
anchor, incremental-row, applicable dictionary-value, footer, framing, and manifest terms,
and the receipt must publish those inputs and totals.

### 3. Derived dictionary authority is only one cohort

`measure_target_only_columns` stops after the first cohort that derives rows. The returned
traversal nevertheless describes its dictionaries as the complete accepted row set.
`gap_break_status` demonstrates the undercount risk: the first retained cohort need not
contain every accepted state that later partitions can publish. Traverse every applicable
retained cohort or bind each finite derived state/convention dictionary to its complete
declared domain. Unknown data-dependent cardinality still blocks.

The allocation is also reduced to `projected_target_only_bytes` in `ProductProjection` and
to `bytes_per_row` in `projections.target_only_fields`. The receipt omits the target-only
anchor, incremental-row, row-group, dictionary cardinality/value-width, additional-value,
and exact-total terms required by ADR-0027. Preserve those structures through projection
and serialization.

### 4. Bundle cardinality and exact-layout accounting are not row-group exact

For an exact-layout bundle, `_traverse_typed_rows` computes one global distinct-value set
because no partition fields are supplied, then publishes it as
`dictionary_cardinality_per_row_group`. The new 65,537-row test freezes the error by
asserting cardinality 65,537 even though the deterministic groups contain 65,536 and one
row. The receipt needs each actual row group's cardinalities or an exactly equivalent
summed allocation, not a global set repeated under a per-group label.

The future bundle reference scope similarly assigns every accepted instrument/version
value to every bundle row group. Derive the actual accepted identity membership of each
deterministic group and sum its cardinalities. Do not repeat the complete universe in a
group that does not contain it.

The exact-layout branch also reprojects measured overhead as
`row_groups * ceil((footer + residual) / row_groups) + framing`. That can differ from the
actual measured footer/residual/framing when the division has a remainder. Exact layout
must use and publish the exact measured payload, footer, residual, framing, file total,
row-group facts, and reconciliation. Its `allocation_model` currently exposes only rows,
row groups, and payload, so the stable receipt is not independently recomputable.

### 5. Reference classes are not exact in every real scope

The main projected native partitions now use detailed/funding-only classes correctly, but
`split_reference_identity_scopes` treats every symbol absent from the funding-only set as
detailed rather than proving it belongs to the accepted detailed set. The Coinalyze scope
then assigns version cardinality one to all liquidation partitions while admitting it has
no per-partition membership class. Validate every symbol against exactly one accepted
class, block unknown or duplicate classification, and split the Coinalyze partitions too.
The bundle uses its actual per-row-group class membership as required above.

### 6. The new test source contains deterministic failures and freezes wrong facts

`test_the_v3_capacity_terms_reconcile_exactly` permits only
`measured_complete_row_set` and `row_group_anchor_plus_incremental_rows`, while the source
now emits `measured_projected_layout` for both bundle and scenario projections. The test
must accept and fully reconcile the intentional exact-layout model. Three consecutive
blank lines before that test are also expected to fail exact-path Ruff's E303 rule.

The large-bundle test must stop asserting global cardinality as per-row-group cardinality.
Add direct end-to-end tests proving one validity owner across current-plus-future fields,
Coinalyze no longer uses a scalar complete-payload-per-point coefficient, every derived
dictionary has complete cardinality authority, each exact bundle group has its actual
cardinality, exact measured overhead/file bytes reconcile without ceiling drift, and the
receipt retains every allocation input.

Receipt 258 remains absent. Receipt 231 and every v1/v2 envelope remain immutable.

## One complete correction

Claude may continue editing only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

Leave `scripts/research/size_binance_usdm_harmonic_release.py` byte-identical.

Implement one physical allocation ledger whose current and future terms are disjoint.
Apply it to all fixed-schema products, target-only derived fields, Coinalyze liquidation,
bundle rows, and separately allocated future fields. Preserve ADR-0024's accepted archive
physical-contribution coefficient and ADR-0025's partition-lineage contract; when a term
is moved to the v3 ledger, subtract it from its former owner so it is counted once.

For exact known layouts, record actual deterministic row-group boundaries and
cardinalities and use the measured payload/footer/residual/framing/file bytes exactly. For
projected layouts, publish row count, per-partition row groups, anchor count/bytes,
incremental count/bytes, cardinality source and value width per dictionary, additional
dictionary bytes, overhead, manifests, largest partition, and exact total. Retain these
facts in the stable receipt instead of collapsing them to a scalar total.

Keep the v3 schema/path/root, v1/v2 immutability, full universe/products/rows, exact
quality-gap ceiling, cost sample, lineage, reserve, redaction, collision, no-follow, race,
idempotence, wholeness, and six capacity components unchanged. Do not delete, skip, xfail,
or weaken an accepted test.

## Exact Claude authorization and stop

Continue from the two edited files in place. Do not reset, restore, checkout, stash,
discard, or replace either file wholesale. Do not run commands, tests, Ruff, sizing,
qualification, control, Git, network, acquisition, normalization, data/evidence, or
documentation work.

Stop once after this complete two-file correction. Report SHA-256 for both edited paths
and the unchanged CLI, plus the final `def test_` function count. Grok, Spark, Hermes,
integration, execution, acquisition, and later work remain unauthorized pending one
reviewer static acceptance. Gate 2 remains not accepted and next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/260_CEX002_V3_COMPLETE_ALLOCATION_RESIDUAL_REVIEW.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

Developer source/test/CLI paths, receipts, evidence, and unrelated dirty work are excluded.
