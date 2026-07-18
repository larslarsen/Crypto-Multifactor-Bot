from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cryptofactors.catalog.runner import (
    apply_migrations,
    get_status,
    MIGRATIONS_DIR,
)


def _temp_db() -> Path:
    fd, path = tempfile.mkstemp(suffix=".db")
    Path(path).unlink(missing_ok=True)
    return Path(path)


def test_new_database_reaches_latest_version():
    db = _temp_db()
    try:
        apply_migrations(db)
        status = get_status(db)
        assert len(status["pending"]) == 0
        assert len(status["applied"]) >= 1  # at least 0001
    finally:
        db.unlink(missing_ok=True)


def test_second_application_is_idempotent():
    db = _temp_db()
    try:
        apply_migrations(db)
        first_status = get_status(db)
        apply_migrations(db)
        second_status = get_status(db)
        assert first_status["applied"] == second_status["applied"]
    finally:
        db.unlink(missing_ok=True)


def test_checksum_mismatch_on_altered_migration_aborts():
    db = _temp_db()
    try:
        apply_migrations(db)
        # Tamper with the recorded checksum of 0001
        import sqlite3
        conn = sqlite3.connect(db)
        conn.execute(
            "UPDATE migration_history SET checksum = 'deadbeef' WHERE filename LIKE '0001%'"
        )
        conn.commit()
        conn.close()

        with pytest.raises(RuntimeError, match="Checksum mismatch"):
            apply_migrations(db)
    finally:
        db.unlink(missing_ok=True)


def test_invalid_migration_rolls_back_and_does_not_record():
    db = _temp_db()
    # Create a bad migration temporarily
    bad_mig = MIGRATIONS_DIR / "9999_bad.sql"
    bad_mig.write_text("CREATE TABLE boom (id INTEGER); INSERT INTO boom VALUES (1); BAD SQL;")
    try:
        with pytest.raises(RuntimeError):
            apply_migrations(db)

        # Should not have recorded the bad migration
        status = get_status(db)
        assert "9999_bad.sql" not in status["applied"]
    finally:
        bad_mig.unlink(missing_ok=True)
        db.unlink(missing_ok=True)


def test_foreign_key_violation_is_rejected():
    db = _temp_db()
    try:
        apply_migrations(db)
        import sqlite3
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO dataset_input_dataset (dataset_id, input_dataset_id, role) "
                "VALUES ('nonexistent', 'also-nonexistent', 'foo')"
            )
            conn.commit()
    finally:
        db.unlink(missing_ok=True)


def test_status_reports_pending_and_applied():
    db = _temp_db()
    try:
        status_before = get_status(db)
        assert len(status_before["pending"]) > 0
        apply_migrations(db)
        status_after = get_status(db)
        assert len(status_after["pending"]) == 0
        assert len(status_after["applied"]) > 0
    finally:
        db.unlink(missing_ok=True)
