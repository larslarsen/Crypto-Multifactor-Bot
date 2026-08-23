# CEX-002 V3 Measured Anchor Test Residual

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-263 drop rejected on deterministic mechanical residuals
- **Architecture:** ADR-0027 remains unchanged
- **Authorized actor:** Implementation Dev - Codex Spark
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## One static review

The reviewer inspected Claude's completed review-263 drop once at:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `a4c266f2970aac175e1ad95c78cf03c1afba44642921310fb185f6f7645951c8` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `717e184525acfd04537104b42b16f1397ca2c2fbb1fc8459c53c89095b804aff` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file has 161 `def test_` functions and the two edited files pass static diff
whitespace validation. The reviewer ran no pytest, Ruff, sizing, qualification, control,
network, or data-mutation command.

Preserve Claude's production correction: the real five-column shared identity anchor is
measured and published; empty class scopes derive zero cardinality; the literal
`R*14 + G*(A-14)` equation and per-product ledger are present; the future lineage charge
excludes validity; and the real `project_coinalyze` comparison covers the wider mapping.

## Exact mechanical residual

1. In `test_the_v3_capacity_terms_reconcile_exactly`, delete the stale pre-review-263
   assertions that require `row_index_bytes == rows * bytes_per_row` and the removed
   `row_group_anchor_bytes`, `row_group_dictionary_bytes`, and `row_group_total_bytes`
   keys. The following review-263 block is the authoritative 12-index + 2-null + measured
   anchor/page equation.
2. Move `partitioning`, `candidates`, and `inputs` assignment before the lineage assertion;
   the current test reads `candidates` before assignment. Publish the selected lineage
   partition's projected mapping count and response count in the receipt, and assert
   exactly `candidate == mappings*bytes_per_mapping + responses*2*INTEGER_WIDTH`, plus
   `candidate <= aggregate lineage bytes`.
3. Rename receipt field `shared_instrument_identity_current_bytes_per_row` to
   `shared_instrument_identity_index_bytes_per_row`; its value is 12. Keep the separate
   current-null field at 2 and total field at 14. Correct the helper docstring that calls
   the 14-byte total an index cost.
4. Make `dictionary_column_allocation`'s rule genuinely three-way: nullable and owned here;
   nullable with validity excluded here and owned by current typed storage; non-nullable,
   for which no validity term exists. Preserve the stable receipt's conditional owner rule.
5. Remove the stale test comment claiming future reference owns validity/current owns
   nothing. Do not weaken, delete, skip, or replace any accepted coverage.

## Exact implementation-dev authorization and stop

Edit only the sizing source and sizing test in place. Do not reset, restore, checkout,
stash, discard, or replace either file wholesale. Leave the CLI byte-identical. Do not run
commands, tests, Ruff, sizing, qualification, control, Git, network, acquisition,
data/evidence, or documentation work. Stop once after these five mechanical corrections
and report both edited SHA-256 values, unchanged CLI SHA-256, and the final `def test_`
count. Hermes, integration, execution, receipt 258, and later work remain unauthorized
pending one reviewer static acceptance.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/264_CEX002_V3_MEASURED_ANCHOR_TEST_RESIDUAL.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

Developer source/test/CLI paths, receipts, evidence, and unrelated dirty work are excluded.
