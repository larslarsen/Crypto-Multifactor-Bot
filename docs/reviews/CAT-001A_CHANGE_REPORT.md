# CAT-001A Change Report

**Date:** 2026-07-18  
**Ticket:** CAT-001A — Make SQLite migrations atomic and validate migration order  
**Based on:** REVIEW-0001 and tickets/CAT-001A.md  
**Commit:** 081b32a + follow-up remediation commit  

## Atomicity Implementation

Each migration is now applied as follows:

- `_discover_migrations()` is called first (strict validation before any DB access).
- `_split_statements()` uses `sqlite3.complete_statement()` accumulator to split the raw SQL text into complete statements. No comment stripping or blind `;` splitting is performed.
- Before `BEGIN IMMEDIATE`, `_reject_transaction_controls()` scans the statements and rejects any top-level transaction-control keyword.
- Inside an explicit `BEGIN IMMEDIATE` transaction: each statement is executed via `conn.execute(stmt)`, followed by the `migration_history` INSERT, then `COMMIT`.
- On any exception: `ROLLBACK` is performed before re-raising `RuntimeError` that includes the migration filename.

This ensures the migration SQL and the history record are one atomic unit. On failure, no schema, data, or history row from that migration remains.

## Transaction-Control Policy

Migration files are strictly forbidden from containing top-level:
- BEGIN (including BEGIN TRANSACTION)
- COMMIT
- END
- ROLLBACK
- SAVEPOINT
- RELEASE

The check happens after splitting but before any execution for that migration file. The error explicitly names the migration filename and the offending statement. A migration can never commit or roll back the transaction owned by the runner.

## Statement Parsing Behavior

- Uses incremental accumulation with `sqlite3.complete_statement(current_buffer)`.
- Correctly handles:
  - Semicolons inside string literals (e.g. `VALUES ('a;b')`).
  - `--` and `/* */` comments inside string literals.
  - Multi-statement bodies such as triggers (`CREATE TRIGGER ... BEGIN ...; ...; END;` treated as single statement).
- Comments outside strings are preserved as part of the statement text passed to `conn.execute()`.
- No preprocessing that would corrupt string content.

## Filename and Sequence Validation

- Filenames must match `NNNN_descriptive_name.sql` (enforced by regex before any DB touch).
- Duplicate versions are rejected with explicit message listing both files.
- Version gaps are rejected with message listing missing versions.
- Validation occurs in `_discover_migrations()` which is called before opening the target database in `apply_migrations()`.
- Discovery order is deterministic (sorted by filename then by version).

## WAL / Second-Connection Behavior

`test_wal_mode_and_concurrent_read_is_deterministic` (in test_runner.py):

- Applies migrations using real `MIGRATIONS_DIR`.
- Verifies `PRAGMA journal_mode` returns `wal`.
- Opens two independent connections and confirms both can read the same `migration_history` rows without error.
- Test is bounded and contains no sleeps or timing-dependent assertions.

## Files Changed

- `src/cryptofactors/catalog/runner.py` — new `_split_statements`, `_reject_transaction_controls`, updated `apply_migrations`.
- `tests/catalog/test_cat001_acceptance_gaps.py` — added 4 new regression tests for transaction controls and string/trigger cases.
- `.gitignore` — added `.local/`.
- `README.md` — updated review-gate wording to reflect CAT-001A awaiting final review.
- `docs/reviews/CAT-001A_CHANGE_REPORT.md` — this report (and removal of .local/control.db from tree).

## Commands Run and Results

```bash
uv run pytest -q tests/catalog
# .................... [20 passed]

uv run ruff check src tests
# All checks passed

uv run mypy src
# Success: no issues found in 11 source files

mkdir -p .local
uv run cf catalog init --database .local/control.db
# Catalog initialized/updated: .local/control.db

uv run cf catalog status --database .local/control.db
# Applied: 0001_baseline.sql ... and 0002_...
# Pending: (none)

git status --short
# Shows tracked changes for the fix + D .local/control.db (removal)
# .local/control.db itself does not appear as untracked (now ignored)

git ls-files .local
# (empty output)
```

`git ls-files .local` must return nothing.

All original gaps tests and retained coverage tests continue to pass without weakening assertions.

## Stop Condition

This change report is provided. CAT-001A awaits final review. No further tickets were started.
