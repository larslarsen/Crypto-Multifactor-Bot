from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cryptofactors.catalog.runner import apply_migrations


def _write_migration(directory: Path, filename: str, sql: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(sql, encoding="utf-8")


def _table_exists(database: Path, table_name: str) -> bool:
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (table_name,),
        ).fetchone()
    return row is not None


def test_failed_migration_leaves_no_partial_schema_or_data(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    database = tmp_path / "control.db"

    _write_migration(
        migrations,
        "0001_bad.sql",
        """
        CREATE TABLE boom (id INTEGER NOT NULL);
        INSERT INTO boom (id) VALUES (1);
        THIS IS NOT VALID SQL;
        """,
    )

    with pytest.raises(RuntimeError, match="0001_bad.sql"):
        apply_migrations(database, migrations_dir=migrations)

    assert not _table_exists(database, "boom")

    with sqlite3.connect(database) as connection:
        applied = connection.execute(
            "SELECT filename FROM migration_history ORDER BY filename"
        ).fetchall()

    assert applied == []


def test_duplicate_migration_versions_are_rejected_before_database_change(
    tmp_path: Path,
) -> None:
    migrations = tmp_path / "migrations"
    database = tmp_path / "control.db"

    _write_migration(migrations, "0001_first.sql", "CREATE TABLE first_table (id INTEGER);")
    _write_migration(migrations, "0001_second.sql", "CREATE TABLE second_table (id INTEGER);")

    with pytest.raises(RuntimeError, match=r"(?i)duplicate.*0001|0001.*duplicate"):
        apply_migrations(database, migrations_dir=migrations)

    assert not database.exists()


def test_migration_version_gaps_are_rejected_before_database_change(
    tmp_path: Path,
) -> None:
    migrations = tmp_path / "migrations"
    database = tmp_path / "control.db"

    _write_migration(migrations, "0001_first.sql", "CREATE TABLE first_table (id INTEGER);")
    _write_migration(migrations, "0003_third.sql", "CREATE TABLE third_table (id INTEGER);")

    with pytest.raises(RuntimeError, match=r"(?i)gap|missing.*0002|expected.*0002"):
        apply_migrations(database, migrations_dir=migrations)

    assert not database.exists()


@pytest.mark.parametrize(
    "filename",
    [
        "1_short.sql",
        "0001.sql",
        "0001_.sql",
        "abcd_name.sql",
        "0001-name.sql",
        "notes.sql",
    ],
)
def test_malformed_sql_migration_filenames_are_rejected(
    tmp_path: Path,
    filename: str,
) -> None:
    migrations = tmp_path / "migrations"
    database = tmp_path / "control.db"

    _write_migration(migrations, filename, "SELECT 1;")

    with pytest.raises(RuntimeError, match=r"(?i)filename|migration.*name|malformed"):
        apply_migrations(database, migrations_dir=migrations)

    assert not database.exists()
