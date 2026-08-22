# CEX-002 Authority Import Failure Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Subject record: `research/sprint_004/168_CEX002_AUTHORITY_SOURCE_INTEGRATION.md`

## Decision

**ACCEPT THE EXACT INTEGRATION AND REQUIRED C1 STOP; REJECT THE PRODUCTION SOURCE AS
NON-IMPORTABLE; AUTHORIZE ONE CONSTANT-BLOCK MOVE BY SPARK.**

Hermes integrated exactly the three review-167 paths in commit
`1e62cd854176177d25ddc9f5043c15f827aa5b86`, pushed it, ran C1 once, and stopped at the
first nonzero status. Commit `87ee7d38fea1ebc7080a7217442d9943799e5061` publishes only
the two controls and record 168. `HEAD == origin/main`; no source-data or transaction
operation occurred.

## Integrated source identities

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `bed5ab4a9d18ed0cb7410d8efc58b6a6fdb88153a68c03ae409494358d48fac7` | one ordering correction required |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` | accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4a9602d7247c0b211dd21925f724ec5e22d529646b71c77cbd529ad7d59a9fef` | accepted and frozen |

The test path still contains 305 unique `test_` function definitions. The reviewer ran no
test, Ruff, repository-control, network/data, transaction, migration, or ordinary
qualification command.

## Finding

C1 exited status 2 during collection. `CostSampleValidation` assigns
`COST_OBSERVATION_PRICEABLE` as a class-body default, but the quote-state and
cost-observation constant block is declared later in the module. Python evaluates that
default while creating the class, so the module raises `NameError` before tests collect.

No financial, source-authority, transaction, or test design is implicated. The exact
constant values and all consumers are already accepted. The declarations are simply in
the wrong execution order.

## Spark source authorization

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High may edit only
`src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`. It moves the exact
unchanged block declaring:

- `QUOTE_STATE_TWO_SIDED`, `QUOTE_STATE_BID_ONLY`, `QUOTE_STATE_ASK_ONLY`, and
  `QUOTE_STATE_EMPTY`;
- `QUOTE_STATES`; and
- `COST_OBSERVATION_PRICEABLE` and `COST_OBSERVATION_UNPRICEABLE`

from below `cost_sample_rows()` to immediately after `COST_VALIDATION_CHECKS` and before
`CostSampleValidation`. It changes no declaration text or value, leaves no duplicate,
and changes no other byte. The CLI and test paths remain exact at the hashes above.

Spark runs no command, test, Ruff, repository-control, network/data operation,
transaction, Git operation, or record edit. It returns only the corrected production
SHA-256, confirms the frozen CLI/test hashes, and confirms the unchanged 305-test count,
then stops. Hermes remains unauthorized pending reviewer source acceptance.

## Boundaries

No test/CLI edit, integration, live source-authority transaction, data mutation,
source-data network operation, ordinary qualification, reservation reconciliation,
Gate-1 acceptance, sizing, Gate 2, bulk acquisition, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, paid source, reduced
scope, or next-ticket work is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
