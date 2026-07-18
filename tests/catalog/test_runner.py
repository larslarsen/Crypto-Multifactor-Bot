from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cryptofactors.catalog.runner import (
    apply_migrations,
    get_status,
    MIGRATIONS_DIR,
)


def test_new_database_reaches_latest_version(tmp_path: Path):
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    status = get_status(db, migrations_dir=MIGRATIONS_DIR)
    assert len(status["pending"]) == 0
    assert len(status["applied"]) >= 1


def test_second_application_is_idempotent(tmp_path: Path):
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    first = get_status(db, migrations_dir=MIGRATIONS_DIR)
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    second = get_status(db, migrations_dir=MIGRATIONS_DIR)
    assert first["applied"] == second["applied"]


def test_checksum_mismatch_on_altered_migration_aborts(tmp_path: Path):
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)

    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE migration_history SET checksum = 'deadbeef' WHERE filename LIKE '0001%'"
    )
    conn.commit()
    conn.close()

    with pytest.raises(RuntimeError, match="Checksum mismatch"):
        apply_migrations(db, migrations_dir=MIGRATIONS_DIR)


def test_invalid_migration_rolls_back_and_does_not_record(tmp_path: Path):
    """Use isolated tmp migrations dir to avoid mutating repository."""
    migrations = tmp_path / "migrations"
    db = tmp_path / "control.db"

    bad_sql = "CREATE TABLE boom (id INTEGER); INSERT INTO boom VALUES (1); BAD SQL;"
    migrations.mkdir(parents=True, exist_ok=True)
    (migrations / "0001_bad.sql").write_text(bad_sql, encoding="utf-8")

    with pytest.raises(RuntimeError):
        apply_migrations(db, migrations_dir=migrations)

    status = get_status(db, migrations_dir=migrations)
    assert "0001_bad.sql" not in status.get("applied", {})


def test_foreign_key_violation_is_rejected(tmp_path: Path):
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)

    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO dataset_input_dataset (dataset_id, input_dataset_id, role) "
            "VALUES ('nonexistent', 'also-nonexistent', 'foo')"
        )
        conn.commit()
    conn.close()


def test_status_reports_pending_and_applied(tmp_path: Path):
    db = tmp_path / "control.db"
    status_before = get_status(db, migrations_dir=MIGRATIONS_DIR)
    assert len(status_before["pending"]) > 0
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    status_after = get_status(db, migrations_dir=MIGRATIONS_DIR)
    assert len(status_after["pending"]) == 0
    assert len(status_after["applied"]) > 0


def test_wal_mode_and_concurrent_read_is_deterministic(tmp_path: Path):
    """Minimal, bounded test of WAL + second connection behavior.

    No sleeps. After apply, two independent connections can read the
    migration_history table. Verifies journal_mode = wal.
    """
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)

    conn1 = sqlite3.connect(db)
    conn2 = sqlite3.connect(db)

    mode = conn1.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"

    # Second connection can read without error (consistent snapshot possible)
    rows1 = conn1.execute("SELECT filename FROM migration_history").fetchall()
    rows2 = conn2.execute("SELECT filename FROM migration_history").fetchall()
    assert rows1 == rows2

    conn1.close()
    conn2.close()
