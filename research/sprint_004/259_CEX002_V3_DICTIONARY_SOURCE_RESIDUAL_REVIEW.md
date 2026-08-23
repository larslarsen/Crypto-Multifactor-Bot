# CEX-002 V3 Dictionary Source Residual Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Claude's first v3 drop rejected on one consolidated accounting residual
- **Architecture:** ADR-0027 remains unchanged
- **Authorized actor:** Sr Dev - Claude Build
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## One static review

The reviewer inspected Claude's complete two-file drop once at these identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `d3f6cf5b3eaf198dc8189bc70ec2c508d8369cfc2101e36e261424c7477efd5f` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `b452e2f1b84fc3e4ab3ccaa42f91677010d124ef396a059a9da884a864ed4cf0` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file has 151 `def test_` functions. The reviewer ran no pytest, Ruff, sizing,
qualification, control, acceptance, network, or data-mutation command.

The drop correctly introduces v3 receipt/evidence paths, protects v1 and v2 evidence,
separates shared identity from derived-only columns, publishes explicit dictionary
allocation structures, retains the complete quality-gap ceiling, and removes the rejected
full-value-per-row future-reference equation. Those parts remain the implementation base.

## Blocking residual

The new equation is not disjoint across every projected physical layout.

1. `measure_maximum_width_product` records the complete one-row Parquet column-chunk
   payload as `row_group_anchor_bytes`. That payload already contains the first row,
   dictionary values, dictionary indices, and page initialization. The same function then
   computes `row_group_dictionary_bytes`, and `project_fixed_schema_product` adds both
   terms. The dictionary values are therefore counted twice. The new test fixture freezes
   that overlap by asserting `anchor + dictionary` rather than proving disjoint terms.
2. A row set being complete does not make its measured file layout the projected layout.
   Membership is measured as one 771-row file but projected as 771 one-row files;
   source/typed/fee gaps similarly change partition layout. The current
   `measured_complete_row_set` branch multiplies one combined-file average by rows and
   fails to recharge data-page/dictionary initialization per projected row group. This can
   understate rather than merely overstate.
3. The bundle's real 150,331-row set still takes the synthetic widest-row branch. It uses
   the complete-set dictionary cardinality as though every one of three row groups held
   every value. That is not the complete batch-exact calculation review 257 required, and
   the new bundle test covers only two rows, which never reaches this branch.
4. Dictionary-bearing derived-only fields still become one scalar `bytes_per_row` and are
   multiplied by projected rows. Status/convention dictionaries and their one-witness
   page initialization therefore remain in the rejected model even though shared identity
   was separated correctly.
5. The main future-reference scope assigns version cardinality one to every native-symbol
   partition. Funding-only identities have accepted version cardinality zero. The unit
   helper proves this distinction, but the real receipt construction does not apply it.
6. `SIZING_POLICY_IDENTITY` still names the ADR-0024/review-230 v2 policy even though it is
   a stable receipt and code-identity field for ADR-0027 v3. The unused local
   `identity_rows` also remains in the production function and is expected to fail exact
   Ruff.

Receipt 258 is absent and v3 execution remains unauthorized. Receipt 231 and all v1/v2
evidence remain immutable.

## One final source correction

Claude may continue editing only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

Leave `scripts/research/size_binance_usdm_harmonic_release.py` byte-identical.

### A. Make every allocation term disjoint

Use one explicit physical equation for projected row groups:

- a measured one-row anchor contains page initialization, the first row, and the first
  non-null dictionary value already present in that anchor;
- incremental rows contain only fixed-width values, dictionary indices, and null validity
  not already represented by their anchor row; and
- additional dictionary-value bytes contain only accepted distinct values beyond the one
  value already present in that row group's anchor.

Do not add a complete dictionary term to an anchor that already contains it. If another
equivalent decomposition is used, prove its byte sets are non-overlapping and publish all
terms. Nullable `None` carries one validity allocation, not two. Each receipt projection
must expose row count, row-group count, anchor count/bytes, incremental count/bytes,
dictionary cardinality/value width/additional-value bytes, and exact total.

### B. Project the target file layout, not the witness layout

Apply the anchor/incremental/cardinality model whenever witness rows are regrouped into a
different product/component/native-symbol/UTC-month file or row-group layout, regardless
of whether the witness has fewer than 65,536 rows. Membership, source gaps, typed gaps,
fee gaps, quality gaps, and other fixed-schema products must each charge the actual
projected partition/row-group set. A combined witness file may not supply a per-row average
to thousands of different files.

When the complete projected layout and values are already known, as for the bundle,
measure that complete deterministic row order in its actual row groups and use the exact
payload, footer, and framing result. Otherwise compute the exactly equivalent per-row-group
cardinality. Do not apply one global high-cardinality dictionary to every bundle row group.

### C. Close every remaining dictionary fallback

Audit every v3 path that projects a scalar `bytes_per_row` or a witness payload into a
larger or differently partitioned target. At minimum, move derived-only dictionary fields
such as gap-break/status/sign-convention fields into the same disjoint row-group model;
their dictionary values and page initialization may not remain hidden in a per-row scalar.
Keep fixed-width derived numerics exact and keep shared instrument identity charged once.

Preserve ADR-0024's accepted physical-contribution coefficient and ADR-0025's explicit
partition-lineage contract unless a term is now separately removed from one of them. Any
term moved into the v3 dictionary allocation must be subtracted from its former model so
it is counted exactly once.

### D. Apply real reference classes and v3 identity

Split or otherwise exactly bind real receipt reference scopes so detailed identities have
at most one snapshot-backed version and funding-only identities have zero. Canonical
instrument allocation remains one per accepted native identity. Bundle row groups use
their actual accepted identity membership/cardinality. Unknown or excessive cardinality
blocks; no current snapshot is backdated and no per-row identity is fabricated.

Change `SIZING_POLICY_IDENTITY` to a stable ADR-0027/review-257 version-3 identity, update
its exact assertions, and remove the unused `identity_rows`. Preserve the exact v3 schema,
receipt path, evidence root, and immutable v1/v2 boundaries already implemented.

### E. Prove the residual directly

Keep all 151 tests except assertions that freeze the overlapping equation. Add or correct
focused tests proving:

- an anchor plus its additional dictionary term contains no value already in the anchor;
- adding rows inside one row group adds only incremental bytes, while adding a row group
  adds exactly one disjoint anchor and its actually applicable additional values;
- a complete witness regrouped into many one-row partitions recharges each target
  row-group anchor;
- a bundle with more than 65,536 rows uses the actual deterministic row-group
  cardinalities and exact complete-layout measurement;
- at least one derived-only dictionary field uses the row-group model rather than a
  scalar per-row witness average;
- the real detailed/funding-only receipt scopes apply version cardinalities one/zero;
- the policy/code identity names ADR-0027 v3; and
- all normalized payload, largest-partition, temporary-work, stable receipt, and six
  capacity components still reconcile with no overlap.

Do not delete, skip, xfail, or weaken any accepted authority, semantic, redaction,
collision, no-follow, race, idempotence, receipt-wholeness, or v1/v2-immutability test.

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

- `research/sprint_004/259_CEX002_V3_DICTIONARY_SOURCE_RESIDUAL_REVIEW.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

Developer source/test/CLI paths, receipts, evidence, and unrelated dirty work are excluded.
