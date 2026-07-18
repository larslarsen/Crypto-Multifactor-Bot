"""MAN-001 regression: dataset_file identity is (dataset_id, storage_uri).

The MAN-001 schema correction flips dataset_file's primary key from
(dataset_id, file_sha256) to (dataset_id, storage_uri). This means two output files
with identical bytes but different logical paths (storage_uri) are both retained, and
re-registering the same storage_uri is idempotent. These tests exercise the real
catalog API (DatasetPublisher.publish -> SqliteDatasetCatalog.register_from_receipt),
translating the Senior's MAN001_fix_patch intent into the shipped code path.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    return db


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
        (source_id, _dt.now(timezone.utc).isoformat()),
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
        (rid, source_id, sha, f"raw/sha256/ab/cd/{sha}", _dt.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def _plan_two_identical_files(
    tmp_path: Path,
    *,
    rel_a: str = "out/part_a.parquet",
    rel_b: str = "out/part_b.parquet",
    data: bytes = b"identical bytes here\n",
    rows: int = 100,
) -> PublishPlan:
    """Build a plan whose two outputs share identical bytes (same sha256)."""
    path_a = tmp_path / "src_a.bin"
    path_b = tmp_path / "src_b.bin"
    path_a.write_bytes(data)
    path_b.write_bytes(data)
    sha, sz = stream_sha256_and_size(path_a)

    specs = [
        OutputFileSpec(
            relative_path=rel_a, sha256=sha, rows=rows, bytes=sz, partition={"p": "a"}
        ),
        OutputFileSpec(
            relative_path=rel_b, sha256=sha, rows=rows, bytes=sz, partition={"p": "b"}
        ),
    ]
    return PublishPlan(
        dataset_type="bars",
        schema=SchemaIdentity(name="ohlcv", version="1", fingerprint="sch_" + "a" * 60),
        transform=TransformSpec(name="trades_to_bars", version="1.0.0"),
        code=CodeIdentity(commit="abc1234deadbeef"),
        config=ConfigIdentity(config_sha256="c" * 64),
        dependencies=[
            DependencyRef(
                id="raw_" + "b" * 64, kind=DependencyKind.RAW_OBJECT, role="trades"
            )
        ],
        output_sources={rel_a: path_a, rel_b: path_b},
        output_specs=specs,
        statistics=DatasetStatistics(row_count=rows * 2, byte_size=sz * 2),
        coverage=CoverageWindow(
            event_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            event_end=datetime(2024, 1, 2, tzinfo=timezone.utc),
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={"warnings": 0},
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters={rel_a: lambda p: rows, rel_b: lambda p: rows},
    )


def _list_dataset_files(db: Path, dataset_id: str) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT storage_uri, file_sha256 FROM dataset_file WHERE dataset_id = ? "
        "ORDER BY storage_uri",
        (dataset_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def test_duplicate_content_different_paths_two_rows(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    cat = SqliteDatasetCatalog(db)
    pub = DatasetPublisher(config, cat)

    plan = _plan_two_identical_files(tmp_path)
    result = pub.publish(plan)
    cat.register_from_receipt(result.receipt, manifest=result.manifest)

    files = _list_dataset_files(db, result.dataset_id)
    # Duplicate content at two logical paths => two rows retained.
    assert len(files) == 2
    uris = {f["storage_uri"] for f in files}
    assert uris == {"out/part_a.parquet", "out/part_b.parquet"}
    # Both rows carry the identical content hash.
    assert all(f["file_sha256"] == result.manifest.files[0].sha256 for f in files)
    assert len({f["file_sha256"] for f in files}) == 1


def test_duplicate_content_registration_idempotent(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    cat = SqliteDatasetCatalog(db)
    pub = DatasetPublisher(config, cat)

    plan = _plan_two_identical_files(tmp_path)
    result = pub.publish(plan)
    first = cat.register_from_receipt(result.receipt, manifest=result.manifest)
    second = cat.register_from_receipt(result.receipt, manifest=result.manifest)
    # Idempotent: identical re-register does not add rows (True on first insert when
    # the tree was not yet cataloged, False when already registered).
    assert (first, second) in {(True, False), (False, False)}
    assert len(_list_dataset_files(db, result.dataset_id)) == 2


def test_dataset_file_pk_is_storage_uri_not_sha256(tmp_path: Path) -> None:
    """Schema-level proof of the MAN-001 fix: identity is (dataset_id, storage_uri).

    Two output files with identical content (same sha256) but different logical paths
    are both retained; a second row reusing the same (dataset_id, storage_uri) with
    different content is rejected by the primary key.
    """
    db = _db(tmp_path)
    ds_id = "ds-pk-check"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO dataset_file (dataset_id, storage_uri, file_sha256, byte_size, "
        "row_count) VALUES (?, ?, ?, ?, ?)",
        (ds_id, "out/part_a.parquet", "a" * 64, 10, 1),
    )
    # Same content hash, different logical path => allowed (the fix).
    conn.execute(
        "INSERT INTO dataset_file (dataset_id, storage_uri, file_sha256, byte_size, "
        "row_count) VALUES (?, ?, ?, ?, ?)",
        (ds_id, "out/part_b.parquet", "a" * 64, 10, 1),
    )
    # Same (dataset_id, storage_uri) with different content => PK violation.
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO dataset_file (dataset_id, storage_uri, file_sha256, byte_size, "
            "row_count) VALUES (?, ?, ?, ?, ?)",
            (ds_id, "out/part_a.parquet", "b" * 64, 99, 9),
        )
    conn.commit()
    conn.close()
    rows = _list_dataset_files(db, ds_id)
    assert len(rows) == 2
    assert {r["storage_uri"] for r in rows} == {"out/part_a.parquet", "out/part_b.parquet"}
