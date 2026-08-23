# CEX-002 V3 Literal Allocation Correction

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-261 drop rejected on bounded implementation contradictions
- **Architecture:** ADR-0027 remains unchanged
- **Authorized actor:** Implementation Dev - Codex Spark
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## One static review

The reviewer inspected Claude's completed review-261 drop once at these stable identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `8d37583cdf87bd0c7f9367c8cea193e0045fdf72f74a2b840b25be1145d3530b` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `d1baf99a691c3beb752fa8f173afdd73ca5f8792a0afa94a07df4f9d0575b382` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file has 159 `def test_` functions and the two edited files pass static diff
whitespace validation. The reviewer ran no pytest, Ruff, sizing, qualification, control,
network, or data-mutation command.

Preserve the accepted review-261 corrections: current typed layouts own reference null
validity, future reference allocation owns only indices and values, future Coinalyze
counter values exclude validity, accepted Coinalyze identities supply maximum widths,
exact files use measured largest bytes, bundle scopes keep actual cardinality, and future
largest candidates exclude shared current identity.

## Bounded blockers

1. `INSTRUMENT_IDENTITY_INDEX_BYTES_PER_ROW` now equals 14 although only 12 bytes are
   indices. The receipt serializes that 14 under an index-only name while the test expects
   12. The future reference receipt emits the correct index-only width 8 while the test
   still expects the rejected index-plus-validity width 10. Keep distinct literal facts:
   shared dictionary indices 12, current reference null validity 2, shared current total
   14, and future reference indices 8. Names, equations, receipt, and tests must agree.
2. The four non-bundle reference scopes hard-code instrument cardinality one. A zero-row,
   zero-row-group class therefore violates `future_reference_identity_bytes`' own
   fail-closed check. Emit `(0, 0)` instrument/version cardinalities for an empty scope;
   otherwise emit the accepted class cardinalities `(1, 1)` or `(1, 0)`.
3. `future_lineage_field_bytes` correctly charges two future eight-byte counter values,
   but `lineage_partition_charge` still multiplies by two times
   `INTEGER_WIDTH + NULL_VALIDITY_WIDTH`. Use the same value-only term in both total and
   largest equations and prove their reconciliation directly.
4. Archive/cost `identity_terms` set row-group initialization to zero and add only
   formula dictionary values. That still omits the current nullable reference columns'
   physical page initialization required by review 261. Measure one real one-row shared
   current identity anchor containing venue, the widest accepted native symbol,
   reference state, and both nullable reference columns as null. The current allocation
   owns that anchor's page initialization and its two validity bytes; subtract the one
   row's 14 incremental bytes before repeating initialization per row group, and do not
   add anchor-owned dictionary values again.
5. `shared_current_identity` is still a zero-row/one-group template copied into every
   product. Instantiate it with each product's actual rows and row groups. Serialize and
   reconcile its measured anchor/page term, 12-byte dictionary-index row term, two-byte
   current-null row term, each column's actual row-index and dictionary-value totals,
   actual rows/groups, and exact bytes with `projected_target_only_bytes`. Do not publish
   template column totals as product facts.
6. The generic dictionary rule always says null validity is charged even when
   `validity_charged_here` is false. Make the prose conditional and keep an explicit owner.
   Replace the isolated literal-width Coinalyze test with a production-path proof that a
   wider accepted non-retained mapping raises `project_coinalyze`'s additional allocation,
   total, and largest bound. Remove the stale validity-owner comments and assert all four
   literal representation widths and the full per-product reconciliation above.

These are implementation corrections to the already accepted disjoint allocation. No ADR,
financial-semantic, source-authority, concurrency, or transaction decision is open.

## Exact Spark authorization and stop

Spark may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

Continue from the current files in place. Do not reset, restore, checkout, stash, discard,
or replace either file wholesale. Leave the CLI byte-identical. Do not run commands,
tests, Ruff, sizing, qualification, control, Git, network, acquisition, data/evidence, or
documentation work. Stop once after the six literal corrections and report SHA-256 for
the two edited paths and the unchanged CLI plus the final `def test_` count. Hermes,
integration, execution, receipt 258, and later work remain unauthorized pending one
reviewer static acceptance.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/262_CEX002_V3_LITERAL_ALLOCATION_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

Developer source/test/CLI paths, receipts, evidence, and unrelated dirty work are excluded.
