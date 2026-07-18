"""MAN-001 migration acceptance coverage.

Focused tests proving the dataset_file PK correction migration (0005) preserves
data on upgrade, enforces constraints post-migration, rolls back atomically on
failure, and that the duplicate-content publication path passes dataset verification.

All databases are temporary; the repository's real migration file is never modified.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from cryptofactors.catalog.dataset import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetPublisher,
    DatasetStatistics,
    DatasetStoreConfig,
    DependencyKind,
    DependencyRef,
    OutputFileSpec,
    PublishPlan,
    QualityStatus,
    RowCountPolicy,
    SchemaIdentity,
    TransformSpec,
    stream_sha256_and_size,
    verify_dataset,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.runner import apply_migrations

REPO_MIGRATIONS = Path(__file__).resolve().parent.parent.parent / "sql" / "migrations"


def _copy_migrations(dst: Path, versions: list[int]) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for v in versions:
        src = next(REPO_MIGRATIONS.glob(f"{v:04d}_*.sql"))
        shutil.copy(src, dst / src.name)


def _db_at_0004(tmp_path: Path) -> tuple[Path, Path]:
    """Return (db_path, migrations_dir_with_0001_to_0004) applied through 0004."""
    mig = tmp_path / "mig_0004"
    _copy_migrations(mig, [1, 2, 3, 4])
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=mig)
    return db, mig


def _insert_parent_dataset(conn: sqlite3.Connection, dataset_id: str) -> None:
    conn.execute(
        """
        INSERT INTO dataset (
            dataset_id, dataset_type, schema_version, manifest_sha256, manifest_uri,
            transform_name, transform_version, code_commit, config_sha256,
            row_count, byte_size, quality_status, created_at
        ) VALUES (?, 'bars', '1', ?, ?, 'trades_to_bars', '1.0.0', 'abc1234deadbeef',
                  'c' * 64, 200, 20, 'PASS', '2024-01-01T00:00:00+00:00')
        """,
        (dataset_id, "m" * 64, f"manifest/{dataset_id}"),
    )


def _insert_dataset_file(
    conn: sqlite3.Connection,
    *,
    dataset_id: str,
    storage_uri: str,
    file_sha256: str,
    byte_size: int,
    row_count: int,
    partition_json: str,
) -> None:
    # Pre-0005 schema: PK is (dataset_id, file_sha256).
    conn.execute(
        """
        INSERT INTO dataset_file (
            dataset_id, file_sha256, storage_uri, byte_size, row_count, partition_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (dataset_id, file_sha256, storage_uri, byte_size, row_count, partition_json),
    )


def test_upgrade_preserves_dataset_file_fields(tmp_path: Path) -> None:
    db, mig = _db_at_0004(tmp_path)
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys = ON")
    ds_id = "ds-upgrade-001"
    _insert_parent_dataset(conn, ds_id)
    _insert_dataset_file(
        conn,
        dataset_id=ds_id,
        storage_uri="out/part_a.parquet",
        file_sha256="a" * 64,
        byte_size=10,
        row_count=100,
        partition_json='{"p": "a"}',
    )
    conn.commit()
    conn.close()

    # Apply the real migration 0005.
    shutil.copy(next(REPO_MIGRATIONS.glob("0005_*.sql")), mig / "0005_fix_dataset_file_pk.sql")
    apply_migrations(db, migrations_dir=mig)

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT dataset_id, storage_uri, file_sha256, byte_size, row_count, "
        "partition_json FROM dataset_file WHERE dataset_id = ?",
        (ds_id,),
    ).fetchone()
    assert dict(row) == {
        "dataset_id": ds_id,
        "storage_uri": "out/part_a.parquet",
        "file_sha256": "a" * 64,
        "byte_size": 10,
        "row_count": 100,
        "partition_json": '{"p": "a"}',
    }

    # New primary key is (dataset_id, storage_uri).
    pk_cols = [
        r[1]
        for r in conn.execute("PRAGMA table_info(dataset_file)").fetchall()
        if r[5] > 0
    ]
    assert pk_cols == ["dataset_id", "storage_uri"]

    # Non-unique SHA-256 index exists.
    indexes = {
        r[1]: r[2]
        for r in conn.execute("PRAGMA index_list(dataset_file)").fetchall()
    }
    assert "idx_dataset_file_sha256" in indexes
    assert indexes["idx_dataset_file_sha256"] == 0  # non-unique
    conn.close()


def test_constraints_after_migration(tmp_path: Path) -> None:
    db, mig = _db_at_0004(tmp_path)
    shutil.copy(next(REPO_MIGRATIONS.glob("0005_*.sql")), mig / "0005_fix_dataset_file_pk.sql")
    apply_migrations(db, migrations_dir=mig)

    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys = ON")
    ds_id = "ds-constraint-001"
    _insert_parent_dataset(conn, ds_id)
    conn.commit()

    # Unknown dataset_id rejected (FK).
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO dataset_file (dataset_id, storage_uri, file_sha256, "
            "byte_size, row_count) VALUES (?, 'x.parquet', ?, 1, 1)",
            ("ds-does-not-exist", "b" * 64),
        )

    # Two paths with the same hash are accepted (the fix).
    conn.execute(
        "INSERT INTO dataset_file (dataset_id, storage_uri, file_sha256, byte_size, "
        "row_count) VALUES (?, 'out/a.parquet', ?, 1, 1)",
        (ds_id, "c" * 64),
    )
    conn.execute(
        "INSERT INTO dataset_file (dataset_id, storage_uri, file_sha256, byte_size, "
        "row_count) VALUES (?, 'out/b.parquet', ?, 1, 1)",
        (ds_id, "c" * 64),
    )

    # Reusing the same path is rejected (PK on storage_uri).
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO dataset_file (dataset_id, storage_uri, file_sha256, byte_size, "
            "row_count) VALUES (?, 'out/a.parquet', ?, 9, 9)",
            (ds_id, "d" * 64),
        )

    # Negative byte_size rejected.
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO dataset_file (dataset_id, storage_uri, file_sha256, byte_size, "
            "row_count) VALUES (?, 'out/neg_bytes.parquet', ?, -1, 1)",
            (ds_id, "e" * 64),
        )

    # Negative row_count rejected.
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO dataset_file (dataset_id, storage_uri, file_sha256, byte_size, "
            "row_count) VALUES (?, 'out/neg_rows.parquet', ?, 1, -1)",
            (ds_id, "f" * 64),
        )
    conn.commit()
    conn.close()


def test_atomic_rollback_on_failed_migration(tmp_path: Path) -> None:
    db, mig = _db_at_0004(tmp_path)
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys = ON")
    ds_id = "ds-rollback-001"
    _insert_parent_dataset(conn, ds_id)
    _insert_dataset_file(
        conn,
        dataset_id=ds_id,
        storage_uri="out/part_a.parquet",
        file_sha256="a" * 64,
        byte_size=10,
        row_count=100,
        partition_json='{"p": "a"}',
    )
    conn.commit()
    conn.close()

    # Build a broken 0005: real rebuild + an intentional invalid final statement.
    real_0005 = next(REPO_MIGRATIONS.glob("0005_*.sql")).read_text(encoding="utf-8")
    broken = mig / "0005_broken.sql"
    broken.write_text(real_0005 + "\nSELECT * FROM no_such_table_for_rollback;\n")

    with pytest.raises(RuntimeError):
        apply_migrations(db, migrations_dir=mig)

    # Original state unchanged: still at 0004, old PK, data + partition_json intact.
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    applied = {
        r[0] for r in conn.execute("SELECT filename FROM migration_history").fetchall()
    }
    assert applied == {
        "0001_baseline.sql",
        "0002_evidence_registry.sql",
        "0003_raw_acquisition.sql",
        "0004_dataset_publication.sql",
    }

    # Old PK still in force (dataset_id, file_sha256) -> same hash+ds, new uri conflicts.
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO dataset_file (dataset_id, file_sha256, storage_uri, byte_size, "
            "row_count, partition_json) VALUES (?, ?, ?, ?, ?, ?)",
            (ds_id, "a" * 64, "out/part_b.parquet", 10, 100, '{"p": "b"}'),
        )

    row = conn.execute(
        "SELECT storage_uri, file_sha256, byte_size, row_count, partition_json "
        "FROM dataset_file WHERE dataset_id = ?",
        (ds_id,),
    ).fetchone()
    assert dict(row) == {
        "storage_uri": "out/part_a.parquet",
        "file_sha256": "a" * 64,
        "byte_size": 10,
        "row_count": 100,
        "partition_json": '{"p": "a"}',
    }
    conn.close()


def _seed_raw(db: Path, raw_id: str, source_id: str = "src1") -> None:
    from datetime import datetime as _dt

    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        """
        INSERT OR IGNORE INTO source
        (source_id, source_type, official_url, terms_class, config_json, created_at)
        VALUES (?, 'external', NULL, NULL, '{}', ?)
        """,
        (source_id, _dt.now(__import__("datetime").timezone.utc).isoformat()),
    )
    sha = raw_id[4:] if raw_id.startswith("raw_") else __import__("hashlib").sha256(raw_id.encode()).hexdigest()
    rid = raw_id if raw_id.startswith("raw_") else f"raw_{sha}"
    conn.execute(
        """
        INSERT OR IGNORE INTO raw_object (
            raw_object_id, source_id, sha256, byte_size, storage_uri,
            original_name, request_json, response_metadata_json, source_checksum,
            acquired_at, event_start, event_end, status
        ) VALUES (?, ?, ?, 0, ?, NULL, '{}', '{}', NULL, ?, NULL, NULL, 'ACQUIRED')
        """,
        (rid, source_id, sha, f"raw/sha256/ab/cd/{sha}", _dt.now(__import__("datetime").timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def _plan_two_identical_files(tmp_path: Path, data: bytes = b"identical bytes here\n", rows: int = 100) -> PublishPlan:
    path_a = tmp_path / "src_a.bin"
    path_b = tmp_path / "src_b.bin"
    path_a.write_bytes(data)
    path_b.write_bytes(data)
    sha, sz = stream_sha256_and_size(path_a)
    specs = [
        OutputFileSpec(relative_path="out/part_a.parquet", sha256=sha, rows=rows, bytes=sz, partition={"p": "a"}),
        OutputFileSpec(relative_path="out/part_b.parquet", sha256=sha, rows=rows, bytes=sz, partition={"p": "b"}),
    ]
    return PublishPlan(
        dataset_type="bars",
        schema=SchemaIdentity(name="ohlcv", version="1", fingerprint="sch_" + "a" * 60),
        transform=TransformSpec(name="trades_to_bars", version="1.0.0"),
        code=CodeIdentity(commit="abc1234deadbeef"),
        config=ConfigIdentity(config_sha256="c" * 64),
        dependencies=[DependencyRef(id="raw_" + "b" * 64, kind=DependencyKind.RAW_OBJECT, role="trades")],
        output_sources={"out/part_a.parquet": path_a, "out/part_b.parquet": path_b},
        output_specs=specs,
        statistics=DatasetStatistics(row_count=rows * 2, byte_size=sz * 2),
        coverage=CoverageWindow(
            event_start=__import__("datetime").datetime(2024, 1, 1, tzinfo=__import__("datetime").timezone.utc),
            event_end=__import__("datetime").datetime(2024, 1, 2, tzinfo=__import__("datetime").timezone.utc),
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={"warnings": 0},
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters={"out/part_a.parquet": lambda p: rows, "out/part_b.parquet": lambda p: rows},
    )


def test_duplicate_content_paths_pass_verification(tmp_path: Path) -> None:
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=REPO_MIGRATIONS)
    _seed_raw(db, "raw_" + "b" * 64)
    config = DatasetStoreConfig(root=tmp_path / "store")
    cat = SqliteDatasetCatalog(db)
    pub = DatasetPublisher(config, cat)

    plan = _plan_two_identical_files(tmp_path)
    result = pub.publish(plan)
    cat.register_from_receipt(result.receipt, manifest=result.manifest)

    report = verify_dataset(config=config, catalog=cat, dataset_id=result.dataset_id)
    assert report.ok is True
    assert {f.relative_path for f in result.manifest.files} == {
        "out/part_a.parquet",
        "out/part_b.parquet",
    }
