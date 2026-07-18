from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MIGRATIONS_DIR = Path("sql/migrations")
MIGRATION_HISTORY_TABLE = "migration_history"

# Strict convention: NNNN_descriptive_name.sql
MIGRATION_FILENAME_RE = re.compile(r"^(?P<version>\d{4})_(?P<name>[A-Za-z0-9_]+)\.sql$")

TRANSACTION_KEYWORDS = {
    "BEGIN", "COMMIT", "END", "ROLLBACK", "SAVEPOINT", "RELEASE"
}


def _compute_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _discover_migrations(migrations_dir: Path) -> list[tuple[int, Path]]:
    """Discover, validate, and return ordered migrations.

    Validation happens before any database is touched.
    """
    results: list[tuple[int, Path]] = []
    seen: dict[int, str] = {}

    for p in sorted(migrations_dir.glob("*.sql")):
        match = MIGRATION_FILENAME_RE.match(p.name)
        if not match:
            raise RuntimeError(
                f"Malformed migration filename: {p.name}. "
                "Expected format: NNNN_descriptive_name.sql"
            )
        version = int(match.group("version"))
        name = match.group("name")
        if not name:
            raise RuntimeError(f"Malformed migration filename (empty name): {p.name}")

        if version in seen:
            raise RuntimeError(
                f"Duplicate migration version {version:04d}: "
                f"{seen[version]} and {p.name}"
            )
        seen[version] = p.name
        results.append((version, p))

    results.sort(key=lambda x: x[0])

    if results:
        versions = [v for v, _ in results]
        min_v, max_v = versions[0], versions[-1]
        expected = list(range(min_v, max_v + 1))
        if versions != expected:
            missing = sorted(set(expected) - set(versions))
            raise RuntimeError(
                f"Migration version gap(s): missing {missing}. "
                f"Found versions: {versions}. "
                "Versions must be contiguous starting from the first."
            )

    return results


def _split_statements(sql: str) -> list[str]:
    """Split a SQL script into complete statements using sqlite3.complete_statement().

    This respects string literals, comments (including inside strings), and
    multi-statement constructs such as triggers. No regex stripping of comments
    or blind semicolon splitting is performed.
    """
    statements: list[str] = []
    current = ""
    for line in sql.splitlines(keepends=True):
        current += line
        if sqlite3.complete_statement(current):
            stmt = current.strip()
            if stmt:
                statements.append(stmt)
            current = ""
    if current.strip():
        statements.append(current.strip())
    return statements


def _reject_transaction_controls(filename: str, statements: list[str]) -> None:
    """Reject any top-level transaction-control statement.

    This must be called before any execution of the migration so that
    the migration file cannot commit or roll back the runner's transaction.
    """
    for stmt in statements:
        # Get the first significant token (uppercased)
        # We look at the leading non-whitespace text
        leading = stmt.strip().upper()
        # Take first word
        token = leading.split(maxsplit=1)[0] if leading else ""
        first_word = token.rstrip(";, ").strip()
        # Also catch BEGIN TRANSACTION etc.
        if first_word in TRANSACTION_KEYWORDS or first_word.startswith("BEGIN"):
            raise RuntimeError(
                f"Transaction-control statement '{first_word}' in migration "
                f"{filename}. Offending statement starts with: {stmt[:80]}"
            )


def _get_connection(db_path: Path, busy_timeout_ms: int = 5000) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute(f"PRAGMA busy_timeout = {busy_timeout_ms}")
    return conn


def ensure_migration_history(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MIGRATION_HISTORY_TABLE} (
            filename TEXT PRIMARY KEY,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def apply_migrations(
    db_path: Path,
    migrations_dir: Path = MIGRATIONS_DIR,
    busy_timeout_ms: int = 5000,
) -> None:
    """Apply pending migrations atomically.

    - Strict validation of migration directory happens BEFORE any database access.
    - Each migration + its history record commit in one explicit transaction.
    - Migration files are forbidden from containing top-level transaction control.
    - On any failure, no changes from that migration remain.
    """
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

    # Validation first — before touching db_path
    migrations = _discover_migrations(migrations_dir)

    conn = _get_connection(db_path, busy_timeout_ms)
    try:
        ensure_migration_history(conn)
        conn.commit()

        applied: dict[str, str] = {
            row[0]: row[1]
            for row in conn.execute(
                f"SELECT filename, checksum FROM {MIGRATION_HISTORY_TABLE}"
            )
        }

        for version, mig_path in migrations:
            filename = mig_path.name
            current_checksum = _compute_checksum(mig_path)

            if filename in applied:
                if applied[filename] != current_checksum:
                    raise RuntimeError(
                        f"Checksum mismatch for already-applied migration {filename}. "
                        f"Expected {applied[filename]}, got {current_checksum}"
                    )
                continue

            sql = mig_path.read_text(encoding="utf-8")
            statements = _split_statements(sql)

            # Reject transaction controls BEFORE starting any execution for this migration
            _reject_transaction_controls(filename, statements)

            try:
                conn.execute("BEGIN IMMEDIATE")
                for stmt in statements:
                    conn.execute(stmt)
                conn.execute(
                    f"""
                    INSERT INTO {MIGRATION_HISTORY_TABLE} (filename, checksum, applied_at)
                    VALUES (?, ?, ?)
                    """,
                    (filename, current_checksum, datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
            except Exception as exc:
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise RuntimeError(f"Migration {filename} failed: {exc}") from exc

    finally:
        conn.close()


def get_status(
    db_path: Path,
    migrations_dir: Path = MIGRATIONS_DIR,
) -> dict[str, Any]:
    """Return dict with applied and pending migrations."""
    conn = _get_connection(db_path)
    try:
        ensure_migration_history(conn)
        conn.commit()

        applied_rows = list(
            conn.execute(
                f"SELECT filename, checksum, applied_at FROM {MIGRATION_HISTORY_TABLE} ORDER BY filename"
            )
        )
        applied = {row[0]: {"checksum": row[1], "applied_at": row[2]} for row in applied_rows}

        pending: list[str] = []
        for _, mig_path in _discover_migrations(migrations_dir):
            if mig_path.name not in applied:
                pending.append(mig_path.name)

        return {"applied": applied, "pending": pending}
    finally:
        conn.close()
