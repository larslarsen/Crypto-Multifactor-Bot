# CEX-002 Spark Migration Test Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Governing review: `research/sprint_004/149_CEX002_GROK_MIGRATION_RESIDUAL_REVIEW.md`

## Reviewed source

| Path | SHA-256 | Decision |
|---|---|---|
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `1d22e79ae30fe2e70d9d46b540f284e72d06d9963b37ce59d86d43f05032ebcd` | rejected; final recovery assertions missing |

The frozen production and CLI hashes remain unchanged. The test path contains 285 unique
`test_` function definitions and `git diff --check` is clean. The reviewer ran no test,
Ruff, migration, candidate, network, or data command.

## Decision

**ACCEPT THE LOCAL RESTORATION REPAIR; REJECT THE INCOMPLETE TEST DROP; AUTHORIZE SPARK
ONLY FOR THREE POST-RECOVERY ASSERTIONS.**

Spark correctly replaced global `monkeypatch.undo()` with restoration of only
`install_migrated_lock`. The fixture-specific reviewed identity constants and the sample-
checkpoint watcher therefore remain active for the second `_migrate()` call.

The test stops after validating the recovered lock and ledger. Review 149 also required
post-recovery proof that the successful migration made no sample-checkpoint `record()` or
`flush()` call and preserved the exact checkpoint bytes. Those three assertions are absent,
so the test source is not accepted for Hermes integration.

## Spark correction authorization

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High may edit only
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`, and only inside
`test_reviewed_migration_finishes_after_a_prepared_ledger_interruption`.

Immediately after the successful recovery and its existing lock/ledger assertions, Spark
must add assertions equivalent to:

```python
assert recorded == []
assert flushed == []
assert (tmp_path / "cex002_qualification_progress.json").read_bytes() == progress_before
```

Every other byte in the test path and both frozen source paths remains unchanged. Spark
runs no command, test, Ruff, repository-control, network/data operation, migration,
integration, repository-record edit, or Git operation. It stops for reviewer inspection
with the exact test-file SHA-256 and unchanged count of 285 unique `test_` functions. Jr
Dev - Hermes remains unauthorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. No live migration or sample acquisition is authorized.
Gate 1 has not passed. Next ticket remains `NONE`.
