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

## Final Edge-Case Corrections (post 0adf078)

### 1. Leading Comment / Whitespace Handling in Transaction Control Detection

**Problem:** `_reject_transaction_controls` used simple `strip().upper().split()` which failed to skip leading `--` and `/* */` comments.

**Fix:**
- Added `_first_significant_keyword(text)` — a small lexer that skips:
  - UTF-8 BOM
  - Whitespace
  - `--` line comments (to end of line)
  - `/* ... */` block comments
- Returns the first significant keyword (e.g. "COMMIT").
- Used **only** for preflight rejection.
- The full original statement (comments intact) is still passed to `conn.execute()`.

**Tests added:**
- Parametrized test for all forbidden keywords preceded by line comments and block comments.
- Specific test `test_create_then_comment_then_commit_leaves_no_changes` using the exact example from the ticket.

### 2. Statement Splitting at Actual Statement Boundaries

**Problem:** `_split_statements` only checked `complete_statement()` after full lines (`splitlines(keepends=True)`). Multiple statements on a single line were passed as one blob to `conn.execute()`.

**Fix:**
- Rewrote `_split_statements` to accumulate **character-by-character**.
- Only when `sql[i] == ';'` and `sqlite3.complete_statement(current)` is True do we split.
- This correctly separates same-line statements while still respecting strings, comments, and multi-statement constructs.

**Tests added:**
- Multiple statements on one line (2 and 3 statements).
- Trigger followed by another statement on the same line.
- Confirmed that `CREATE ...; CREATE ...;` now produces two separate executable statements.

### Acceptance Results After Fixes

```bash
uv run pytest -q tests/catalog     # 32 passed (all dots)
uv run ruff check src tests        # All checks passed
uv run mypy src                    # Success: no issues
cf catalog init --database .local/control.db
cf catalog status                  # Both migrations applied, pending (none)
git status --short                 # Only source changes shown (no .local)
git ls-files .local                # (empty)
```

All original atomicity, validation, and isolation guarantees preserved. No architecture changes.

**Commit:** next focused commit after these edits.

## Review of Commit 0adf078 (as requested)

**Reviewed commit:** 0adf078 (the state before the final parsing fixes).

**Bugs identified in 0adf078:**

1. Transaction-control detection:
   - Code used:
     ```python
     leading = stmt.strip().upper()
     token = leading.split(maxsplit=1)[0] ...
     first_word = token.rstrip(";, ").strip()
     ```
   - This failed on leading comments because `strip()` only removes whitespace.
   - Examples that would have executed the control statement:
     ```sql
     -- explanatory comment
     COMMIT;
     ```
     ```sql
     /* explanatory comment */
     ROLLBACK;
     ```

2. Statement splitting:
   - Code used:
     ```python
     for line in sql.splitlines(keepends=True):
         current += line
         if sqlite3.complete_statement(current):
     ```
   - Only checked after complete lines. Multi-statement lines were passed as single strings to `conn.execute()`.
   - Example that failed to split:
     ```sql
     CREATE TABLE first_table (id INTEGER); CREATE TABLE second_table (id INTEGER);
     ```

**Fixes applied (char-by-char splitter + lexical helper):**
- Added `_first_significant_keyword(text)` (small lexer, only for preflight):
  - Skips UTF-8 BOM, whitespace, `--` to EOL, `/* ... */`.
  - Returns first significant keyword for classification only.
  - Original statement text (with comments) is passed unchanged to SQLite.
- Rewrote `_split_statements` to accumulate character-by-character and check `sqlite3.complete_statement()` only when `sql[i] == ';'`.
- Preserved all required behavior: explicit `BEGIN IMMEDIATE`, per-statement `execute`, history INSERT in same tx, rollback on error.
- No changes to architecture, layer boundaries, or other logic.

**Tests added/verified against 0adf078 issues:**
- Parametrized test for every forbidden keyword (`BEGIN`, `COMMIT`, `END`, `ROLLBACK`, `SAVEPOINT`, `RELEASE`) preceded by both `--` and `/* */` comments.
- `test_create_then_comment_then_commit_leaves_no_changes` using the exact pattern:
  ```sql
  CREATE TABLE escaped (id INTEGER);
  -- comment
  COMMIT;
  INVALID SQL;
  ```
  (Rejected before any execution; no table, no history row.)
- Tests for 2 statements on one line, 3 statements on one line, trigger + statement on same line.
- Tests for commented transaction controls.

**Verification after fixes (on top of 0adf078):**
- Full CAT-001A acceptance suite run:
  ```bash
  uv run pytest -q tests/catalog          # all passed
  uv run ruff check src tests             # clean
  uv run mypy src                         # clean
  mkdir -p .local
  uv run cf catalog init --database .local/control.db
  uv run cf catalog status --database .local/control.db
  git status --short
  git ls-files .local                     # empty
  ```
- All original atomicity, validation, isolation, and WAL tests continue to pass without weakening.

Focused commit pushed. Stopped. No next ticket started.
