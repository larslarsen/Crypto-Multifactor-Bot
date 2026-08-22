# CEX-002 Migration Focused Failure Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Subject record: `research/sprint_004/152_CEX002_MIGRATION_INTEGRATION_AND_EXECUTION.md`

## Decision

**ACCEPT THE EXACT INTEGRATION AND REQUIRED STOP; REJECT THE TEST SOURCE; AUTHORIZE GROK
FOR THREE BOUNDED TEST-HARNESS CORRECTIONS.**

Hermes integrated exactly the three review-151 identities in commit
`bce618f7e100e10751a5f342ba1c55ccc7c3ef7d` and pushed it. Publication commit
`1db4d0d365cbe32376a95783f58610cf6a3eb75f` contains exactly the two controls and record
152. `HEAD == origin/main`, repository control passes, and the integrated source hashes
remain exact.

C1 returned exit 1 with 15 migration-test failures. Hermes correctly stopped: C2-C5,
migration preconditions, the migration-only invocation, and every later action were not
run. No runtime or data result is inferred beyond record 152.

The production and CLI identities remain accepted and frozen:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` |

## Findings

### P1 - fixture identities and test assertions use different namespaces

`_accepted_v4_candidate()` patches the reviewed migration constants on the production
module to the fixture candidate's real report, plan, envelope, cost, prior-lock, ledger,
and shape identities. The test module imported those constants by value before the patch.
Fixture-based assertions therefore compare the correctly installed fixture digest
`d3fe13d96146d163bb39f338b058d3e59c26fbef6c0870b574db1dae68906da4` to the stale
production literal `2fb0e47a...`. This explains the repeated primary mismatch and every
fixture test that fails before reaching its intended tamper boundary.

The fixture scope must align both the production module and the fixture-based test
assertions to the same generated identity. The independent
`test_reviewed_migration_identities_are_the_review145_literals` must continue to prove all
production literals exactly; no production constant or production validation may change.

### P1 - the amendment-accounting fixture has no download entries

`_accepted_v4_candidate()` passes the same `_kline_manifest_index()` to
`_seed_v2_authority()` and candidate construction. The seed performs ordinary execution,
so all selected fixture objects are already retained. The candidate is retained-only and
`downloads[0]` is invalid in every amendment-accounting parameter case.

The real planner, not a hand-built or digest-forced plan, must produce at least two
legitimate candidate `download` entries and retain at least one re-proved object. A bounded
representative construction is to seed version 2 from a strict earlier inventory subset,
then build the candidate from the full fixture inventory. The resulting fixture report,
plan, envelope, shape, and patched identities must all continue to derive from the real
candidate path.

### P1 - wrong-authority ledger test expects the wrong validator message

`test_reviewed_migration_refuses_a_ledger_bound_to_another_authority` changes the reviewed
binding's plan digest, but expects `does not match the accepted identity`. The exact
binding validator correctly emits `the amendment ledger is not bound to the reviewed
migration`. Its synthetic source receipt is also malformed, weakening isolation of the
intended binding substitution.

The test must use an otherwise valid, typed fixture source receipt, change only the
authority field under test, and assert the actual binding-boundary error. Production error
ordering and validation strength remain unchanged.

## Grok correction authorization

Sr Dev - Grok Build using Grok 4.6 High may edit only
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Grok must:

1. align fixture-scoped test references with the generated identities already patched on
   the production module, without weakening or altering the production-literal test;
2. make `_accepted_v4_candidate()` construct a real candidate with at least two planned
   downloads and at least one retained object, preferably by seeding version 2 with a
   strict inventory subset before candidacy on the full inventory;
3. make the wrong-authority ledger fixture otherwise well-formed and assert the exact
   binding-validator failure; and
4. preserve every other migration, checkpoint, accounting, report, and tamper assertion.

The integrated production and CLI paths are frozen. Grok performs no command, test, Ruff,
repository-control, network/data operation, migration, record edit, or Git operation. It
stops for reviewer source inspection with the exact test-file SHA-256 and unchanged count
of 285 unique `test_` function definitions. Jr Dev - Hermes remains unauthorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. No migration or sample acquisition is authorized. Gate 1
has not passed. Next ticket remains `NONE`.
