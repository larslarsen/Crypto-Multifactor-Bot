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
# - exactly 4 digits
# - underscore
# - non-empty descriptive name (letters, digits, underscores)
# - .sql
MIGRATION_FILENAME_RE = re.compile(r"^(?P<version>\d{4})_(?P<name>[A-Za-z0-9_]+)\.sql$")


def _compute_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _discover_migrations(migrations_dir: Path) -> list[tuple[int, Path]]:
    """Discover, validate, and return ordered migrations.

    Validation happens before any database is touched:
    - Filename must match NNNN_name.sql
    - No duplicate versions
    - Versions must be contiguous (no gaps)
    - Deterministic sort by version
    """
    results: list[tuple[int, Path]] = []
    seen: dict[int, str] = {}

    for p in sorted(migrations_dir.glob("*.sql")):  # sorted for determinism
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
    """Split SQL script into executable statements.

    Handles basic line comments and block comments for catalog migrations.
    Does not support ; inside string literals (migrations are controlled DDL).
    """
    # Remove block comments /* ... */
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    # Remove line comments --
    sql = re.sub(r"--.*", "", sql)
    # Split on ; and strip
    parts = re.split(r";\s*", sql)
    return [p.strip() for p in parts if p.strip()]


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
    - On any failure (including inside the migration SQL), no changes from that
      migration remain (no partial schema or data, no history row).
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

        # Pending computed from dir (may raise on bad dir, which is acceptable)
        pending: list[str] = []
        for _, mig_path in _discover_migrations(migrations_dir):
            if mig_path.name not in applied:
                pending.append(mig_path.name)

        return {"applied": applied, "pending": pending}
    finally:
        conn.close()
