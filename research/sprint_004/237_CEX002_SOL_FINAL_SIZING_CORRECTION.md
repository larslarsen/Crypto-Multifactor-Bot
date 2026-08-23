# CEX-002 Sol Final Sizing Correction

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Claude drop rejected before integration; one complete alternate-senior correction authorized
- **Authorized actor:** Sr Dev - Codex Sol High
- **Integration actor after source acceptance:** NONE

## Reviewed drop

The reviewer inspected Claude's complete review-236 drop once at:

- sizing source: `01cf5ef6426cb62e7db4df4998e50d168928d5df16c1225cf0060e50bdcd2644`;
- sizing tests: `fa1ed3827681603122e0d4967a7eadceb37da486604605b4e2be4abafd8c8004`;
- unchanged sizing CLI:
  `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c`;
- test functions: 137.

No reviewer pytest, Ruff, sizing, qualification, control, acceptance, network, or data
command was run. Static inspection proves that the real receipt path and multiple existing
tests cannot execute, so integration and test execution are rejected.

Preserve the now-correct 1,008/771 classification split, 106/96/10 alias folding, exact
numeric/time conversion, causal derivation grouping, OI gap nulls, liquidation schema and
semantics, 300-second metrics, one-hour funding ceiling, fee scenario values, Coinalyze
coefficient arithmetic, native/canonical identity distinction, and all accepted security,
authority, v1 immutability, credit, reserve, publication, and idempotence protections.

The owner reports that both formal senior actors are on cooldown and explicitly authorizes
Sol High when another developer is required. Under the alternate-senior route in
`docs/engineering/DEVELOPMENT_ROLES.md`, Codex Sol High is the sole source actor for this
bounded correction and inherits the same source/test-only scope and prohibitions as Grok
Build and Claude Build.

## Complete residual correction

### 1. Make all 771 accepted memberships executable without inventing terms

Reviewed `contract_evidence` lines 3116-3180 requires explicit contract type, base, quote,
and margin fields for every accepted identity. The real authority has 698 accepted rows
with exchange-info contract terms and 73 archive-only accepted rows whose official
realized-funding evidence proves perpetual membership but does not contain those terms.
The current code therefore fails during fixed membership measurement.

Represent the real evidence boundary exactly:

- preserve all explicit exchange-info terms for the 698 detailed identities;
- for the 73 archive-only identities, derive only `contract_type=PERPETUAL` from the
  accepted official realized-funding evidence and its explicit perpetual semantics;
- keep unavailable base, quote, margin, pair, status, and lifecycle terms nullable, with a
  typed `contract_metadata_state` and exact evidence class/source fields;
- do not infer an unavailable term from a ticker suffix or default it to USDT;
- allocate each unavailable future term conservatively using its native-symbol width as a
  schema-width bound, including dictionary/index overhead, and include that charge in the
  receipt rather than merely describing it.

The real membership test must traverse all 771 rows and assert the exact 698 detailed / 73
funding-only split. Its full receipt invocation must use a temporary `store_root` (while
pointing authority inputs to their pinned accepted paths), so both receipt and envelope
publication stay under `tmp_path`. The current test redirects only the receipt and would
mutate `data/cex002_qualify/evidence/sizing/v2`.

### 2. Remove the still-flattened cost product and allocate all five components

Reviewed `final_product_columns` lines 1866-1891 still merges book-ticker, book-depth,
native/reference identity, and fee-scenario fields into one non-null cost row. The generic
target-only loop then derives only identity fields and passes rows missing every scenario
field to `_column_values`; the receipt path fails even after membership is repaired.

The cost product is a descriptor over five heterogeneous component schemas, never a sixth
flattened table. Remove cost calibration from generic final-row and target-only derivation.
Expose its five component schemas through the final product contract and project each
component independently:

1. book-ticker rows with their own product/symbol/month partitions, payload, overhead,
   manifests, and catalog entries;
2. book-depth rows with the same independent accounting;
3. the complete official fee-schedule schema, zero data rows, and one real schema/catalog
   descriptor allocation;
4. 771 fee-authority gap rows; and
5. two scenario-policy rows.

Do not combine ticker and depth into one partition overhead or manifest. Publish each
component's row, partition, payload, overhead, manifest, schema, and catalog counts and sum
them exactly once into cost calibration and total capacity.

For multi-input target products, physical contribution bytes still sum, but target output
rows use one causally aligned product grid, not the sum of mark, index, and premium row
counts. Compute one target-row ceiling per product/native/month from the maximum applicable
aligned cadence ceiling. Reserve `ceil(target_grid_rows / 2)` quality gaps from that grid.
Declare, measure, and project quality-gap rows as their own typed component with product,
native symbol, month, missing-run bounds, expected grid count, and reason; do not price them
as accepted source-gap rows.

### 3. Build lineage and bundle authority from every projected partition

Reviewed `build_partition_lineage` receives only the 96 retained coefficient-sample
entries, so its archive partition set is not the release's projected partition set.
`PARTITION_MANIFEST_SCHEMA` also drops native symbol, UTC month, provider identity, and
receipt state even when callers put them in dictionaries. Coinalyze then labels every
future symbol/month mapping with the one retained witness response hash and
`retained_coinalyze_response_receipt`, which is false.

Build the lineage mapping plan from every selected and cost `PhysicalObject`, with one
mapping per product/component partition it feeds. Retained objects carry their real hash,
retrieval, checksum, and availability evidence. Unacquired objects carry their real
requirement key/listing evidence plus an explicit `projected_unacquired` state and nullable
future receipt/hash fields whose widths are allocated, never a fabricated hash. Coinalyze
future partitions likewise carry a projected-response state; only genuinely retained
coverage maps to the retained witness receipt.

Every serialized local manifest row must include required product/component, native
symbol, UTC month, source/receipt state, and the provider/native pair when applicable.
Measure conservative archive and Coinalyze manifest schemas separately if their fields
differ. Charge every projected partition's mappings, row-group/footer, and framing, expose
their exact sums, and keep no cohort-global manifest copy.

Build bundle rows from this complete projected archive-plus-Coinalyze partition set, not
the coefficient cohort. Pin both qualification source and CLI, both sizing source and CLI,
all component/final schemas, the complete configuration, and both complete scenario rows.
Derive and pin the actual cross-product partition intersection set and digest, not merely
the number of unique symbol/month keys.

### 4. Include all rows and all future-width charges in capacity

Reviewed fixed-product measurement slices source gaps and bundle rows at
`SIZING_ROW_BATCH`. Measure all 8,317 accepted source-gap rows losslessly and all projected
bundle descriptors, or use a separately proved maximum-width model that covers every
omitted value. A first-batch average is not a conservative coefficient for unseen symbols
or strings.

`future_reference_identity_bytes` and unresolved bundle fields are currently receipt
annotations only; no capacity component consumes their bytes. Add explicit capacity
allocations for canonical IDs/versions, future partition and lineage hashes, future byte/
row counters, projected source receipts, and the 73 unresolved membership-term widths.
Use fixed integer widths and fixed digest widths where the type contract provides them.
Expose these charges separately and include them exactly once in normalized, catalog,
temporary-high-water, and total calculations as appropriate.

Catalog-page accounting must include every component data partition, source-gap component,
typed-gap component, quality-gap component, fee-gap component, scenario component, zero-row
official schema descriptor, local manifest, bundle descriptor, and projected acquisition
receipt. Receipt equations and self-size must reconcile from those components without an
unlisted remainder.

## Required source-test correction

Keep every valid test and repair all stale assertions in the same drop. At minimum:

1. traverse all 771 real memberships and prove 698 detailed plus 73 funding-only without
   invented terms;
2. run the real receipt path entirely under temporary publication/storage roots;
3. assert cost calibration has no generic flattened final row schema or target-only writer
   and that all five independent projections reconcile to its total;
4. prove three aligned basis inputs create one target grid, not three rows, and quality-gap
   reservation is partition-local on that one grid;
5. serialize and read back archive and Coinalyze manifest rows with product/component,
   symbol, month, source state, and provider/native fields;
6. prove the complete projected archive partition set, not only 96 sample bindings, feeds
   lineage and bundle descriptors;
7. prove every future-width allocation appears in a named byte component and the capacity
   sum exactly once;
8. remove stale expectations for liquidation `venue_symbol`, nonexistent
   `projections["partition_manifest"]`, and fee-gap `kind` (the field is `gap_kind`);
9. correct the typed byte equation so payload + file overhead + local manifests equals
   normalized bytes; and
10. retain the complete real-authority rerun, capacity boundary, no-network/no-credential,
    path, symlink, race, v1 immutability, and byte-identical publication protections.

The existing weak manifest assertion at reviewed test line 3761 divides the expected sum
by partition count; replace it with an exact full-sum assertion. Do not add skips for an
authority that is present, weaken a production invariant, or retain contradictory legacy
assertions.

## Exact Sol authorization and stop

Codex Sol High may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`;
3. `scripts/research/size_binance_usdm_harmonic_release.py`.

Work from the current shared drop in place. Do not reset, restore, checkout, discard, or
wholesale replace it. Close all four correction sections and all ten test requirements as
one drop. Sol does not run commands or tests, mutate evidence/data, use Git, or write
research, ticket, handoff, ADR, receipt, envelope, database, manifest, or catalog records.
Stop once with SHA-256 for all three allowed paths, explicitly marking an unchanged path,
plus the final `test_` function count.

Claude and Grok are deauthorized while on cooldown. No integration actor is authorized
until reviewer static acceptance. Gate 2 remains blocked, bulk acquisition and all later
work remain unauthorized, and next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS.md reviewer exception, the reviewer may stage, commit, and push exactly:

- `research/sprint_004/237_CEX002_SOL_FINAL_SIZING_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

The three developer paths and all unrelated dirty work are excluded.
