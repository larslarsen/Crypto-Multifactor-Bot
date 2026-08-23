# CEX-002 V3 Measured Identity Anchor Completion

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-262 drop rejected on incomplete literal implementation
- **Architecture:** ADR-0027 remains unchanged
- **Authorized actor:** Sr Dev - Claude Build
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## One static review

The reviewer inspected the completed Spark/Luna review-262 drop once at:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `d9ae7c4e5cca2be345068958d0e8286bb1affd706cc9621e1d8d75194110500b` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `32c2aef09abbc9f305de94e0c88e6c51cdbe0f86f6e64ba6f3bb938e551daf81` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file has 159 `def test_` functions and the two edited files pass static diff
whitespace validation. The reviewer ran no pytest, Ruff, sizing, qualification, control,
network, or data-mutation command.

Preserve the completed corrections: the receipt exposes literal 12-byte shared indices,
2-byte current null validity, 14-byte current total, and 8-byte future indices; the
largest-lineage response term now uses two eight-byte values without validity; and shared
identity ledgers now receive each product's actual rows and row groups.

## Blocking completion

1. All four non-bundle scopes still hard-code instrument cardinality one. At least one
   real class scope has zero rows and zero row groups, so
   `future_reference_identity_bytes` deterministically raises before a receipt can be
   produced. Derive each cardinality from that scope's rows: empty is `(0, 0)`; nonempty
   detailed is `(1, 1)`; nonempty funding-only is `(1, 0)`.
2. The source did not measure a shared identity anchor. It renames the formula sum of
   three dictionary values/offsets as `row_group_anchor_bytes`; neither nullable reference
   column is present and no Arrow/Parquet page initialization is measured. Measure a real
   one-row `instrument_identity_columns()` payload using `native_identity()` with the
   widest accepted native symbol, publish that v3 envelope through the existing target
   envelope flow, and retain its traversal, payload, and envelope identity in the receipt.
3. Keep the disjoint shared-current equation literal. Let `A` be the measured one-row
   payload, `I = 12`, `N = 2`, and `D` the logical per-group value/offset total for the
   three present dictionaries. Require `A >= I + N + D`. The per-group page residual is
   `A - I - N - D`; for product rows `R` and groups `G`, shared bytes are
   `R*(I+N) + G*D + G*(A-I-N-D)`, equivalently `R*14 + G*(A-14)`. Do not add any
   anchor-owned value twice.
4. Serialize each product's actual `R`, `G`, 12-byte row-index total, two-byte current-null
   total, each present dictionary column's actual row-index and value/offset totals,
   measured anchor, page residual, and exact shared total. Reconcile the outer target-only
   allocation as shared current plus derived target terms; do not test only each ledger's
   internal arithmetic.
5. Rename the 14-byte constant and `_exact` field so neither claims to be index-only.
   Correct the stale `cost_identity_allocation` docstring and the stale validity test
   comment. Make both the per-column rule and stable receipt rule conditional: future
   reference allocation owns indices/values and explicitly excludes validity.
6. Replace the unchanged isolated `dictionary_column_allocation` width test with a real
   `project_coinalyze`-path comparison proving that adding a wider accepted, non-retained
   mapping raises identity delta, additional allocation, total payload, and largest
   partition while retained envelopes stay fixed. Add direct tests for empty scope
   construction, measured shared anchor facts, the full per-product equation, and the
   largest-lineage/aggregate lineage reconciliation.

This is corrective implementation of ADR-0027 and reviews 261-262. No architecture,
financial-semantic, source-authority, concurrency, or transaction decision is open.

## Exact Claude authorization and stop

Claude may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

Continue from the current files in place. Do not reset, restore, checkout, stash, discard,
or replace either file wholesale. Leave the CLI byte-identical. Do not run commands,
tests, Ruff, sizing, qualification, control, Git, network, acquisition, data/evidence, or
documentation work. Stop once after this complete correction and report SHA-256 for the
two edited paths and unchanged CLI plus the final `def test_` count. Hermes, integration,
execution, receipt 258, and later work remain unauthorized pending one reviewer static
acceptance.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/263_CEX002_V3_MEASURED_IDENTITY_ANCHOR_COMPLETION.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

Developer source/test/CLI paths, receipts, evidence, and unrelated dirty work are excluded.
