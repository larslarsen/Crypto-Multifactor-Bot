# REVIEW-0001 — CAT-001 control catalog

**Review date:** 2026-07-18  
**Decision:** changes required  
**Architecture impact:** none  
**ADR required:** no

## Scope

Reviewed:

- `src/cryptofactors/catalog/runner.py`
- `src/cryptofactors/cli.py`
- `tests/catalog/test_runner.py`
- `sql/migrations/0001_baseline.sql`
- `sql/migrations/0002_evidence_registry.sql`
- `tickets/CAT-001.md`

The implementation is directionally consistent with the frozen architecture, but CAT-001
does not yet satisfy its own acceptance contract.

## Blocking finding 1 — failed migrations are not atomic

The runner executes a migration with:

```python
with conn:
    conn.executescript(sql)
    conn.execute("INSERT INTO migration_history ...")
```

Python's SQLite `executescript()` performs its own transaction handling. Without an
explicit `BEGIN` inside the executed script, statements before a syntax error can remain
committed even though the migration-history insert is not recorded.

A migration such as:

```sql
CREATE TABLE boom (id INTEGER);
INSERT INTO boom VALUES (1);
BAD SQL;
```

currently raises an error but can leave `boom` and its row in the database. This creates
an unrecorded, partially migrated catalog.

The existing test checks only that the bad migration is absent from `migration_history`.
It does not assert that all schema and data changes were rolled back.

### Required behavior

The migration SQL and its history record must commit as one atomic unit. On any failure:

- no migration-created table, index, trigger, view, or data change may remain;
- no migration-history row may be recorded;
- the connection must return to a usable state;
- the error must identify the migration filename.

## Blocking finding 2 — migration layout is not validated

CAT-001 requires a clear failure on migration gaps and duplicate versions.

The current discovery function:

- accepts any filename whose first four characters are digits;
- silently ignores malformed SQL filenames;
- allows two files with the same numeric version;
- allows version gaps such as `0001` followed by `0003`.

This makes migration order ambiguous and permits accidental history forks.

### Required behavior

Before opening or modifying the target database, discovery must verify:

- filenames follow one documented convention;
- numeric versions are unique;
- versions are contiguous;
- discovery order is deterministic;
- violations list the offending files or missing version.

## Major finding 3 — the failure test modifies the repository

`test_invalid_migration_rolls_back_and_does_not_record` writes
`sql/migrations/9999_bad.sql` into the working tree.

That creates avoidable risks:

- an interrupted test can leave a dirty repository;
- parallel test runs can interfere;
- a watcher or another process can observe a temporary production migration.

All migration-runner tests must use a temporary migration directory.

## Minor finding 4 — temporary file descriptor leak

The test helper calls `tempfile.mkstemp()` but does not close the returned file descriptor
before unlinking the path. Prefer pytest's `tmp_path`, or explicitly close the descriptor.

## Acceptance status

| Requirement | Status |
|---|---|
| ordered migration discovery | partial |
| CLI init/status | implemented |
| filename and SHA-256 history | implemented |
| transactional migration application | failed |
| foreign keys on runner connections | implemented |
| busy timeout and WAL | implemented |
| changed-checksum rejection | implemented |
| gap rejection | missing |
| duplicate-version rejection | missing |
| failed-statement rollback | failed |
| temporary-database tests | partial |
| concurrency/read behavior | not demonstrated |

## Decision

Do not start the next implementation ticket. Complete `CAT-001A`, run the full acceptance
suite, and submit a focused change report.

This is a conformance correction, not an architecture change. No ADR should be created.
