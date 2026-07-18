# CAT-001A — Make SQLite migrations atomic and validate migration order

**Priority:** P0  
**Dependencies:** CAT-001 implementation  
**Layer:** catalog  
**Architecture change:** none  
**ADR required:** no
**Status:** ACCEPTED

## Objective

Bring CAT-001 into conformance with its committed acceptance criteria before any downstream
catalog or raw-data work begins.

## Required changes

### 1. Atomic migration application

Apply each pending migration and insert its `migration_history` row in the same explicit
SQLite transaction.

On failure, the database must contain none of that migration's schema or data changes.

The implementation must account for Python `sqlite3.Connection.executescript()` transaction
semantics. A surrounding `with conn:` block by itself is not sufficient.

Migration files must not be allowed to manage their own transactions unless the runner
implements and tests a safe, explicit policy for that behavior.

### 2. Strict migration discovery

Validate the entire migration directory before modifying the database.

Use one documented filename convention, for example:

```text
NNNN_descriptive_name.sql
```

Reject:

- malformed SQL migration filenames;
- duplicate numeric versions;
- missing versions in the sequence;
- an empty migration name;
- nondeterministic ordering.

Errors must identify the relevant filenames or missing version.

### 3. Tests must be isolated

Do not create temporary migrations inside `sql/migrations`.

Use `tmp_path` to create an isolated migration directory and database for each test.

### 4. Close temporary resources

Remove the `mkstemp()` descriptor leak by using `tmp_path` or closing the descriptor
explicitly.

### 5. Minimal concurrency/read behavior

Document and test at least one second-connection behavior under WAL mode. The test should be
bounded and deterministic; it must not rely on sleeps or timing races.

## Required regression tests

The repository includes `tests/catalog/test_cat001_acceptance_gaps.py`. Make all tests pass
without weakening or deleting their assertions.

Also retain coverage for:

1. new database reaches latest version;
2. second application is idempotent;
3. changed applied migration is rejected;
4. foreign-key violations are rejected;
5. status reports pending and applied migrations;
6. a failed migration leaves no partial schema or data;
7. duplicate versions are rejected;
8. version gaps are rejected;
9. tests do not mutate the repository migration directory.

## Acceptance commands

```bash
uv run pytest -q tests/catalog
uv run ruff check src tests
uv run mypy src
mkdir -p .local
uv run cf catalog init --database .local/control.db
uv run cf catalog status --database .local/control.db
git status --short
```

`git status --short` must not show a temporary migration created by tests.

## Stop condition

After the acceptance commands pass, write a change report that states:

- how atomicity is achieved;
- how transaction-control statements in migration files are handled;
- the migration filename and sequence rules;
- the concurrency behavior tested;
- all files changed;
- all commands run and their results.

Stop after CAT-001A. Do not begin the next ticket.
