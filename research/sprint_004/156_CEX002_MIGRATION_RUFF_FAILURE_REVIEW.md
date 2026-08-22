# CEX-002 Migration Ruff Failure Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Subject record: `research/sprint_004/155_CEX002_MIGRATION_TEST_INTEGRATION_AND_EXECUTION.md`

## Decision

**ACCEPT THE TEST INTEGRATION AND EXIT-0 FOCUSED TESTS; ACCEPT THE REQUIRED C3 STOP;
AUTHORIZE SPARK ONLY TO REMOVE FIVE UNUSED IMPORTS.**

Hermes integrated review 154's exact test identity in commit
`31552933df41b4c8f769fb5b4237299d620a6380` and pushed it. Publication commit
`fb4e06236b70d9541e7918bc0e3412396c60ee33` contains exactly the two controls and record
155. `HEAD == origin/main`, repository control passes, and all three accepted source
hashes remain exact.

The restarted focused sequence established:

- C1: the 285-definition CEX migration test path reached `[100%]`, exit 0;
- C2: the 18-case download atomicity path reached `[100%]`, exit 0; and
- C3: Ruff exited 1 on exactly five `F401` findings in the CEX test import list.

Hermes correctly stopped before C4-C5 and every migration precondition or invocation. No
migration or sample acquisition occurred.

## Finding

The five imported names occur nowhere as direct references in the test path:

- `execute_reviewed_v4_migration`;
- `install_migrated_lock`;
- `load_migrated_amendment_ledger`;
- `prepare_amendment_ledger`; and
- `preserve_prior_lock_bytes`.

Where the latter helper names are needed for interruption tests, the code deliberately
accesses them through the imported production module so monkeypatching observes the real
boundary. Removing the stale direct imports changes no behavior or authority assertion.

## Spark correction authorization

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High may edit only
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`, and only by deleting the
five exact import-list entries above.

Every other byte remains unchanged. Spark runs no command, test, Ruff, repository-control,
network/data operation, migration, record edit, or Git operation. It stops for reviewer
inspection with the exact test-file SHA-256 and unchanged count of 285 unique `test_`
function definitions. Jr Dev - Hermes remains unauthorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. No migration or sample acquisition is authorized. Gate 1
has not passed. Next ticket remains `NONE`.
