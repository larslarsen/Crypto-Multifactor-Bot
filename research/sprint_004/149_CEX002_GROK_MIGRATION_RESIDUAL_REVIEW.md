# CEX-002 Grok Migration Residual Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Governing review: `research/sprint_004/148_CEX002_GROK_MIGRATION_SOURCE_REVIEW.md`

## Reviewed source

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` | accepted and frozen |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` | accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `8ee613cca4daaa0e6ead051ae989ea4da546503c6f85167b4bd7d47614d74996` | rejected on one harness defect |

The test path contains 285 unique `test_` function definitions and `git diff --check` is
clean. The reviewer ran no test, Ruff, migration, candidate, network, or data command.

## Decision

**ACCEPT AND FREEZE THE PRODUCTION AND CLI SOURCE; REJECT ONE TEST-HARNESS RESTORATION;
AUTHORIZE SPARK FOR A SINGLE LOCAL TEST CORRECTION.**

Grok closes both review-148 production residuals. Migration retained recovery now uses an
in-memory evidence overlay, calls neither sample-checkpoint `record()` nor `flush()`, and
skips the terminal sample-checkpoint flush. The accepted report-writer separation remains
unchanged. The amendment-ledger loader now rejects non-object binding JSON before
coercion; receipt shapes, fixed authority identities, and digest fields are validated; the
installed final receipt must exactly equal the live source identity and its code/config
digest must equal the lock input. The new source tests directly cover missing-entry
read-only recovery, two-file receipt substitution, and malformed binding/receipt types.

No production or CLI correction remains open from reviews 145-148.

## Test-source finding

`test_reviewed_migration_finishes_after_a_prepared_ledger_interruption` creates its
accepted fixture through `_accepted_v4_candidate()`, which uses the shared
`monkeypatch` fixture to replace all reviewed migration constants with the fixture's exact
report/lock/ledger identities. The test later calls `monkeypatch.undo()` after injecting
the lock-publication failure, then invokes `_migrate()` again.

`monkeypatch.undo()` restores every patch made by that fixture, not only
`install_migrated_lock`. The second `_migrate()` therefore sees production review-145
constants against the temporary fixture report and must fail migration preflight before
it can prove prepared-ledger recovery. The test cannot pass as written. This is a test-
harness scoping defect; it does not invalidate the accepted production transaction.

## Spark correction authorization

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High may edit only
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`, and only inside
`test_reviewed_migration_finishes_after_a_prepared_ledger_interruption`.

Spark must replace the global `monkeypatch.undo()` restoration with a local patch scope or
an exact restoration of only `install_migrated_lock`. The reviewed constants and the
sample-checkpoint watcher must remain active through the second `_migrate()` call. After
the recovered migration, the test must retain its existing lock/ledger assertions and
also assert that the watcher recorded no sample-checkpoint `record()` or `flush()` and that
the exact checkpoint bytes remain unchanged.

Every other byte in the test path and both frozen source paths remain unchanged. Spark
runs no command, test, Ruff, repository-control, network/data operation, migration,
integration, repository-record edit, or Git operation. It stops for reviewer inspection
with the exact test-file SHA-256 and unchanged count of 285 unique `test_` functions. Jr
Dev - Hermes remains unauthorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. No live migration or sample acquisition is authorized.
Gate 1 has not passed. Next ticket remains `NONE`.
