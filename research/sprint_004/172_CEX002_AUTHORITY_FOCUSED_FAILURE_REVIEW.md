# CEX-002 Authority Focused Failure Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Subject record: `research/sprint_004/171_CEX002_AUTHORITY_IMPORT_INTEGRATION.md`

## Decision

**ACCEPT THE IMPORT CORRECTION AND HERMES'S REQUIRED C1 STOP; FREEZE PRODUCTION AND CLI;
AUTHORIZE ONE FIVE-ASSERTION SPARK TEST CORRECTION.**

Hermes integrated exactly the review-170 production path in commit
`c4a3df4e8c10590ebbc2413cd8683199a77f77a9`, pushed it, restarted at C1, and stopped at
the first nonzero status. C1 imported and collected the module, reached `[100%]`, and
reported five test failures. Commit `dc52fd3471bf8e563e23af61ea6ef62fa434d6af`
publishes only the two controls and record 171. `HEAD == origin/main`; no source-data or
transaction operation occurred.

## Frozen source identities

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e` | accepted and frozen |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` | accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4a9602d7247c0b211dd21925f724ec5e22d529646b71c77cbd529ad7d59a9fef` | five assertion corrections required |

The test path contains 305 unique `test_` function definitions. The reviewer ran no test,
Ruff, repository-control, network/data, transaction, migration, or ordinary qualification
command.

## Findings

All five C1 failures are stale or incorrectly ordered test assertions, not production
defects:

1. The headed-payload test still expects `uncrossed_quotes`; ADR-0020's accepted typed
   check is `uncrossed_two_sided_quotes`.
2. The negative-quantity case expects the superseded `quantity is negative`; the accepted
   unified finite/nonnegative classifier reports `quote value is negative`.
3. The zero-price/positive-quantity case expects `price is not positive`; ADR-0020 defines
   it as the accepted inconsistent-side failure `quote side is inconsistently zero`.
4. The all-empty outcome-blind test compares `items` insertion order with the separately
   sorted `keys` view. Both contain the same selected identities, but family/stratum order
   need not equal lexical key order. Sorted full-list equality proves exact membership,
   including multiplicity, without imposing an unreviewed order.
5. The CLI test expects a direct textual call to
   `reviewed_source_correction_preflight()`. Review 165 intentionally encapsulated that
   preflight inside `apply_reviewed_source_correction()`. The CLI must instead prove its
   correction branch invokes the public apply call and returns before `store_root.mkdir`.

## Spark test-only authorization

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High may edit only
`tests/acquisition/test_binance_usdm_harmonic_qualification.py` and only these five
assertions:

1. expect `uncrossed_two_sided_quotes` in the headed ticker checks;
2. expect `quote value is negative` for the negative-quantity row;
3. expect `quote side is inconsistently zero` for the zero-price/positive-quantity row;
4. compare the sorted full `items` key list with the sorted `keys` list in the all-empty
   no-substitution assertion; and
5. replace the obsolete direct-preflight CLI substring assertion with an ordering proof
   that the `if apply_correction:` branch calls
   `receipt = apply_reviewed_source_correction(`, returns 0, and does both before
   `store_root.mkdir`.

Spark changes no test name or function count and no other test byte. Production and CLI
remain exact at the hashes above. Spark runs no command, test, Ruff, repository-control,
network/data operation, transaction, Git operation, or record edit. It returns the new
test SHA-256, confirms the frozen production/CLI hashes, and confirms the unchanged
305-test count, then stops. Hermes remains unauthorized pending reviewer acceptance.

## Boundaries

No production/CLI edit, integration, live source-authority transaction, data mutation,
source-data network operation, ordinary qualification, reservation reconciliation,
Gate-1 acceptance, sizing, Gate 2, bulk acquisition, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, paid source, reduced
scope, or next-ticket work is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
