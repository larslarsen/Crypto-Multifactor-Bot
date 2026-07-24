"""Regression: resolve_latest_by_type must prefer PASS over REJECTED.

When two market_bars datasets share the same deterministic created_at (epoch) and
differ only in quality_status, the catalog resolver must not prefer the older
REJECTED dataset simply because its hash sorts later. This test exercises the
real catalog registration path and the public `resolve_latest_by_type` API.
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
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        """
        INSERT OR IGNORE INTO source
        (source_id, source_type, official_url, terms_class, config_json, created_at)
        VALUES (?, 'external', NULL, NULL, '{}', ?)
        """,
        (source_id, datetime.now(timezone.utc).isoformat()),
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
        (rid, source_id, sha, f"raw/sha256/ab/cd/{sha}", datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def _publish_dataset(
    tmp_path: Path,
    db_path: Path,
    *,
    dataset_id_hint: str,
    quality_status: QualityStatus,
    created_at: datetime | None = None,
    code_commit: str = "PAPER-009",
) -> str:
    """Publish a tiny dataset with a specific content-hash-derived dataset_id."""
    # Build a tiny file whose content is salted by the hint so the dataset_id is
    # deterministic per hint. The exact id is not asserted; we use the returned id.
    src = tmp_path / f"{dataset_id_hint}.bin"
    src.write_bytes(dataset_id_hint.encode())
    sha, sz = stream_sha256_and_size(src)
    rel = "out/data.bin"
    spec = OutputFileSpec(relative_path=rel, sha256=sha, rows=1, bytes=sz, partition={"p": "x"})
    raw_dep_id = f"raw_{'a' * 64}"
    plan = PublishPlan(
        dataset_type="market_bars",
        schema=SchemaIdentity(name="ohlcv", version="1", fingerprint="sch_" + "0" * 60),
        transform=TransformSpec(name="trades_to_bars", version="1.0.0"),
        code=CodeIdentity(commit=code_commit),
        config=ConfigIdentity(config_sha256="c" * 64),
        dependencies=[
            DependencyRef(id=raw_dep_id, kind=DependencyKind.RAW_OBJECT, role="trades")
        ],
        output_sources={rel: src},
        output_specs=[spec],
        statistics=DatasetStatistics(row_count=1, byte_size=sz),
        coverage=CoverageWindow(
            event_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            event_end=datetime(2024, 1, 2, tzinfo=timezone.utc),
        ),
        quality_status=quality_status,
        quality_summary={"note": quality_status.value},
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters={rel: lambda p: 1},
        created_at=created_at,
    )
    _seed_raw(db_path, raw_dep_id)
    store_root = tmp_path / "store"
    config = DatasetStoreConfig(root=store_root)
    catalog = SqliteDatasetCatalog(db_path)
    try:
        publisher = DatasetPublisher(config, catalog)
        result = publisher.publish(plan, register_catalog=True)
        return result.dataset_id
    finally:
        catalog.close()


def test_resolve_latest_by_type_prefers_pass_over_rejected_at_same_created_at(
    tmp_path: Path,
) -> None:
    """PASS must win over REJECTED even when both have epoch created_at."""
    db_path = _db(tmp_path)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

    rejected_id = _publish_dataset(
        tmp_path,
        db_path,
        dataset_id_hint="rejected_dataset",
        quality_status=QualityStatus.REJECTED,
        created_at=epoch,
    )
    pass_id = _publish_dataset(
        tmp_path,
        db_path,
        dataset_id_hint="pass_dataset",
        quality_status=QualityStatus.PASS,
        created_at=epoch,
    )

    # Ensure both are registered.
    cat = SqliteDatasetCatalog(db_path)
    try:
        assert cat.get_dataset(rejected_id) is not None
        assert cat.get_dataset(pass_id) is not None
        resolved = cat.resolve_latest_by_type("market_bars")
        assert resolved == pass_id, f"expected PASS {pass_id}, got {resolved}"
    finally:
        cat.close()


def test_resolve_latest_by_type_prefers_pass_over_warnings(
    tmp_path: Path,
) -> None:
    """PASS wins over PASS_WITH_WARNINGS, and warnings win over REJECTED."""
    db_path = _db(tmp_path)

    _publish_dataset(
        tmp_path,
        db_path,
        dataset_id_hint="rejected_dataset_2",
        quality_status=QualityStatus.REJECTED,
    )
    pass_warn_id = _publish_dataset(
        tmp_path,
        db_path,
        dataset_id_hint="warning_dataset",
        quality_status=QualityStatus.PASS_WITH_WARNINGS,
    )
    pass_id = _publish_dataset(
        tmp_path,
        db_path,
        dataset_id_hint="pass_dataset_2",
        quality_status=QualityStatus.PASS,
    )

    cat = SqliteDatasetCatalog(db_path)
    try:
        resolved = cat.resolve_latest_by_type("market_bars")
        assert resolved == pass_id
    finally:
        cat.close()


def test_resolve_latest_by_type_returns_none_when_empty(
    tmp_path: Path,
) -> None:
    db_path = _db(tmp_path)
    cat = SqliteDatasetCatalog(db_path)
    try:
        assert cat.resolve_latest_by_type("market_bars") is None
    finally:
        cat.close()


def test_resolve_latest_by_type_falls_back_to_created_at_and_id(
    tmp_path: Path,
) -> None:
    """Among same quality, later created_at and then larger dataset_id wins."""
    db_path = _db(tmp_path)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

    first_id = _publish_dataset(
        tmp_path,
        db_path,
        dataset_id_hint="first_pass",
        quality_status=QualityStatus.PASS,
        created_at=epoch,
    )
    second_id = _publish_dataset(
        tmp_path,
        db_path,
        dataset_id_hint="second_pass",
        quality_status=QualityStatus.PASS,
        created_at=epoch,
    )

    cat = SqliteDatasetCatalog(db_path)
    try:
        resolved = cat.resolve_latest_by_type("market_bars")
        assert resolved == max(first_id, second_id)
    finally:
        cat.close()


def test_resolve_latest_by_type_respects_created_at_across_quality(
    tmp_path: Path,
) -> None:
    """A much newer PASS_WITH_WARNINGS should not beat an older PASS; quality dominates."""
    db_path = _db(tmp_path)
    now = datetime.now(timezone.utc)

    _publish_dataset(
        tmp_path,
        db_path,
        dataset_id_hint="older_pass",
        quality_status=QualityStatus.PASS,
        created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    warning_id = _publish_dataset(
        tmp_path,
        db_path,
        dataset_id_hint="newer_warning",
        quality_status=QualityStatus.PASS_WITH_WARNINGS,
        created_at=now,
    )

    cat = SqliteDatasetCatalog(db_path)
    try:
        resolved = cat.resolve_latest_by_type("market_bars")
        assert resolved != warning_id
    finally:
        cat.close()


def test_resolve_latest_by_type_respects_newer_pass_created_at(
    tmp_path: Path,
) -> None:
    """Among PASS datasets, the newer created_at wins."""
    db_path = _db(tmp_path)

    older_id = _publish_dataset(
        tmp_path,
        db_path,
        dataset_id_hint="older_pass_2",
        quality_status=QualityStatus.PASS,
        created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    newer_id = _publish_dataset(
        tmp_path,
        db_path,
        dataset_id_hint="newer_pass_2",
        quality_status=QualityStatus.PASS,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    cat = SqliteDatasetCatalog(db_path)
    try:
        resolved = cat.resolve_latest_by_type("market_bars")
        assert resolved == newer_id
    finally:
        cat.close()
