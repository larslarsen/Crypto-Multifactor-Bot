from __future__ import annotations
from typing import Any

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS_DIR = Path("sql/migrations")
MIGRATION_HISTORY_TABLE = "migration_history"


def _compute_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _discover_migrations(migrations_dir: Path) -> list[tuple[int, Path]]:
    """Return (version, path) sorted by version. Expects 0001_*.sql etc."""
    results: list[tuple[int, Path]] = []
    for p in migrations_dir.glob("*.sql"):
        stem = p.stem
        if len(stem) >= 4 and stem[:4].isdigit():
            version = int(stem[:4])
            results.append((version, p))
    results.sort(key=lambda x: x[0])
    return results


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
    """Apply all pending migrations transactionally. Idempotent on matching checksum."""
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

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

        for version, mig_path in _discover_migrations(migrations_dir):
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
            try:
                with conn:
                    conn.executescript(sql)
                    conn.execute(
                        f"""
                        INSERT INTO {MIGRATION_HISTORY_TABLE} (filename, checksum, applied_at)
                        VALUES (?, ?, ?)
                        """,
                        (filename, current_checksum, datetime.now(timezone.utc).isoformat()),
                    )
            except Exception as exc:
                # Explicit rollback not needed inside with conn: on exception it rolls back
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
