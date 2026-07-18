"""Focused synthetic tests for MAN-001 dataset manifests and publication."""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
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
    InvalidManifestError,
    LineageError,
    MissingInputError,
    OutputFileSpec,
    OutputVerificationError,
    PublishPlan,
    QualityStatus,
    SchemaIdentity,
    SqliteDatasetCatalog,
    TransformSpec,
    compute_dataset_id,
    dumps_canonical,
    identity_payload,
    normalize_value,
    stream_sha256_and_size,
    validate_dependencies,
    verify_dataset,
    verify_outputs,
)
from cryptofactors.catalog.dataset.errors import UnsafePathError
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations

UTC = timezone.utc


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    return db


def _seed_raw(db: Path, raw_id: str, source_id: str = "src1") -> None:
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        """
        INSERT OR IGNORE INTO source (source_id, source_type, official_url, terms_class, config_json, created_at)
        VALUES (?, 'external', NULL, NULL, '{}', ?)
        """,
        (source_id, datetime.now(UTC).isoformat()),
    )
    sha = raw_id[4:] if raw_id.startswith("raw_") else _sha(raw_id.encode())
    conn.execute(
        """
        INSERT OR IGNORE INTO raw_object (
            raw_object_id, source_id, sha256, byte_size, storage_uri,
            original_name, request_json, response_metadata_json, source_checksum,
            acquired_at, event_start, event_end, status
        ) VALUES (?, ?, ?, 0, ?, NULL, '{}', '{}', NULL, ?, NULL, NULL, 'ACQUIRED')
        """,
        (
            raw_id if raw_id.startswith("raw_") else f"raw_{sha}",
            source_id,
            sha if len(sha) == 64 else _sha(raw_id.encode()),
            f"raw/sha256/ab/cd/{sha if len(sha) == 64 else _sha(raw_id.encode())}",
            datetime.now(UTC).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def _file(tmp_path: Path, name: str, data: bytes) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def _plan(
    tmp_path: Path,
    *,
    data: bytes = b"row1\nrow2\n",
    rows: int = 2,
    deps: list[DependencyRef] | None = None,
    dataset_type: str = "bars",
) -> tuple[PublishPlan, dict[str, Path]]:
    path = _file(tmp_path, "out/part.parquet", data)
    sha, sz = stream_sha256_and_size(path)
    rel = "out/part.parquet"
    specs = [
        OutputFileSpec(relative_path=rel, sha256=sha, rows=rows, bytes=sz, partition={"p": "0"})
    ]
    sources = {rel: path}
    plan = PublishPlan(
        dataset_type=dataset_type,
        schema=SchemaIdentity(name="ohlcv", version="1", fingerprint="sch_" + "a" * 60),
        transform=TransformSpec(name="trades_to_bars", version="1.0.0"),
        code=CodeIdentity(commit="abc1234deadbeef"),
        config=ConfigIdentity(config_sha256="c" * 64),
        dependencies=deps
        or [
            DependencyRef(
                id="raw_" + "b" * 64,
                kind=DependencyKind.RAW_OBJECT,
                role="trades",
            )
        ],
        output_sources=sources,
        output_specs=specs,
        statistics=DatasetStatistics(row_count=rows, byte_size=sz),
        coverage=CoverageWindow(
            event_start=datetime(2024, 1, 1, tzinfo=UTC),
            event_end=datetime(2024, 1, 2, tzinfo=UTC),
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={"warnings": 0},
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    return plan, sources


def test_canonical_ordering_and_identity_stability(tmp_path: Path) -> None:
    deps = [
        DependencyRef(id="raw_" + "b" * 64, kind=DependencyKind.RAW_OBJECT, role="b"),
        DependencyRef(id="raw_" + "a" * 64, kind=DependencyKind.RAW_OBJECT, role="a"),
    ]
    files = [
        OutputFileSpec(relative_path="z.bin", sha256="f" * 64, rows=1, bytes=1),
        OutputFileSpec(relative_path="a.bin", sha256="e" * 64, rows=2, bytes=2),
    ]
    p1 = identity_payload(
        dataset_type="x",
        schema=SchemaIdentity("s", "1"),
        transform=TransformSpec("t", "1"),
        code=CodeIdentity("commit01"),
        config=ConfigIdentity("d" * 64),
        dependencies=deps,
        files=files,
        statistics=DatasetStatistics(3, 3),
        coverage=CoverageWindow(),
        quality_status=QualityStatus.PASS,
        quality_summary={"k": Decimal("1.50")},
        supersedes_dataset_id=None,
    )
    p2 = identity_payload(
        dataset_type="x",
        schema=SchemaIdentity("s", "1"),
        transform=TransformSpec("t", "1"),
        code=CodeIdentity("commit01"),
        config=ConfigIdentity("d" * 64),
        dependencies=list(reversed(deps)),
        files=list(reversed(files)),
        statistics=DatasetStatistics(3, 3),
        coverage=CoverageWindow(),
        quality_status=QualityStatus.PASS,
        quality_summary={"k": Decimal("1.50")},
        supersedes_dataset_id=None,
    )
    assert dumps_canonical(p1) == dumps_canonical(p2)
    id1, h1 = compute_dataset_id(p1)
    id2, h2 = compute_dataset_id(p2)
    assert id1 == id2 and h1 == h2 and id1.startswith("ds_")


def test_identity_changes_with_inputs(tmp_path: Path) -> None:
    base = dict(
        dataset_type="x",
        schema=SchemaIdentity("s", "1"),
        transform=TransformSpec("t", "1"),
        code=CodeIdentity("c" * 8),
        config=ConfigIdentity("d" * 64),
        dependencies=[DependencyRef("raw_" + "a" * 64, DependencyKind.RAW_OBJECT, "r")],
        files=[OutputFileSpec("a", "e" * 64, 1, 1)],
        statistics=DatasetStatistics(1, 1),
        coverage=CoverageWindow(),
        quality_status=QualityStatus.PASS,
        quality_summary={},
        supersedes_dataset_id=None,
    )
    a, _ = compute_dataset_id(identity_payload(**base))
    base2 = dict(base)
    base2["files"] = [OutputFileSpec("a", "f" * 64, 1, 1)]
    b, _ = compute_dataset_id(identity_payload(**base2))
    assert a != b


def test_reject_float_and_naive_datetime() -> None:
    with pytest.raises(InvalidManifestError):
        normalize_value(1.25)
    with pytest.raises(InvalidManifestError):
        normalize_value(datetime(2020, 1, 1))


def test_path_safety_config(tmp_path: Path) -> None:
    with pytest.raises(UnsafePathError):
        DatasetStoreConfig(root=tmp_path, object_prefix="/abs")
    with pytest.raises(UnsafePathError):
        DatasetStoreConfig(root=tmp_path, temp_dirname="../x")


def test_output_verification_mismatch(tmp_path: Path) -> None:
    p = _file(tmp_path, "f.bin", b"abc")
    with pytest.raises(OutputVerificationError, match="SHA-256"):
        verify_outputs(
            sources={"f.bin": p},
            specs=[OutputFileSpec("f.bin", "0" * 64, 1, 3)],
        )


def test_publish_and_verify_roundtrip(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    config = DatasetStoreConfig(root=store)
    catalog = SqliteDatasetCatalog(db)
    publisher = DatasetPublisher(config, catalog)
    plan, _ = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])
    result = publisher.publish(plan)
    assert result.dataset_id.startswith("ds_")
    assert result.catalog_registered is True
    assert (result.dataset_path / "manifest.json").is_file()
    assert (result.dataset_path / "out/part.parquet").read_bytes() == b"row1\nrow2\n"
    report = verify_dataset(
        config=config,
        catalog=catalog,
        dataset_id=result.dataset_id,
        expected_manifest=result.manifest,
    )
    assert report.ok is True


def test_idempotent_identical_publication(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    catalog = SqliteDatasetCatalog(db)
    publisher = DatasetPublisher(config, catalog)
    plan, _ = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])
    r1 = publisher.publish(plan)
    r2 = publisher.publish(plan)
    assert r1.dataset_id == r2.dataset_id
    assert r2.reused_existing is True
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM dataset").fetchone()[0]
    assert n == 1


def test_missing_raw_input_rejected(tmp_path: Path) -> None:
    db = _db(tmp_path)
    config = DatasetStoreConfig(root=tmp_path / "store")
    catalog = SqliteDatasetCatalog(db)
    publisher = DatasetPublisher(config, catalog)
    plan, _ = _plan(tmp_path)
    with pytest.raises(MissingInputError):
        publisher.publish(plan)


def test_lineage_edges_registered(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "c" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    catalog = SqliteDatasetCatalog(db)
    publisher = DatasetPublisher(config, catalog)
    plan, _ = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])
    result = publisher.publish(plan)
    raws = catalog.list_raw_inputs(result.dataset_id)
    assert len(raws) == 1
    assert raws[0]["raw_object_id"] == raw_id


def test_upstream_dataset_lineage_and_cycle(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "d" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    catalog = SqliteDatasetCatalog(db)
    publisher = DatasetPublisher(config, catalog)
    plan1, _ = _plan(
        tmp_path,
        data=b"a\n",
        rows=1,
        deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")],
        dataset_type="base",
    )
    r1 = publisher.publish(plan1)
    # second depends on first
    plan2, _ = _plan(
        tmp_path,
        data=b"b\n",
        rows=1,
        deps=[DependencyRef(r1.dataset_id, DependencyKind.DATASET, "parent")],
        dataset_type="child",
    )
    r2 = publisher.publish(plan2)
    ups = catalog.list_dataset_inputs(r2.dataset_id)
    assert ups[0]["input_dataset_id"] == r1.dataset_id

    # Cycle: if we claim r1 depends on r2 while registering a fake validation
    def fake_upstreams(ds: str) -> list[str]:
        if ds == r1.dataset_id:
            return [r2.dataset_id]
        if ds == r2.dataset_id:
            return [r1.dataset_id]
        return list(catalog.upstream_dataset_ids(ds))

    with pytest.raises(LineageError, match="cycle"):
        validate_dependencies(
            [DependencyRef(r1.dataset_id, DependencyKind.DATASET, "x")],
            raw_exists=catalog.raw_object_exists,
            dataset_exists=catalog.dataset_exists,
            dataset_upstreams=fake_upstreams,
        )


def test_concurrent_identical_publishers(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "e" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    barrier = threading.Barrier(3)
    results: list[object] = []
    errors: list[BaseException] = []

    def worker() -> None:
        # each worker needs own output copy path
        local = tmp_path / f"w_{threading.get_ident()}"
        plan, _ = _plan(
            local,
            data=b"same-content\n",
            rows=1,
            deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")],
        )
        cat = SqliteDatasetCatalog(db)
        pub = DatasetPublisher(DatasetStoreConfig(root=store), cat)
        barrier.wait()
        try:
            results.append(pub.publish(plan))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            cat.close()

    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = [pool.submit(worker) for _ in range(3)]
        for f in futs:
            f.result()
    assert not errors
    ids = {getattr(r, "dataset_id") for r in results}
    assert len(ids) == 1
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM dataset").fetchone()[0]
    assert n == 1


def test_catalog_retry_after_failure(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "f" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    plan, _ = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])

    class Boom(SqliteDatasetCatalog):
        def register_dataset(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("catalog down")

    pub = DatasetPublisher(config, Boom(db))
    with pytest.raises(Exception) as ei:
        pub.publish(plan)
    # published on disk even if catalog failed
    # RecoverableDatasetCatalogError wraps
    from cryptofactors.catalog.dataset.errors import RecoverableDatasetCatalogError

    assert ei.type is RecoverableDatasetCatalogError or "catalog" in str(ei.value).lower()
    # retry with healthy catalog using filesystem + rebuild is via retry on publisher
    # Re-publish is idempotent path
    healthy = DatasetPublisher(config, SqliteDatasetCatalog(db))
    result = healthy.publish(plan)
    assert result.catalog_registered is True
    assert healthy._catalog.get_dataset(result.dataset_id) is not None


def test_tamper_detected(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "1" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    catalog = SqliteDatasetCatalog(db)
    publisher = DatasetPublisher(config, catalog)
    plan, _ = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])
    result = publisher.publish(plan)
    # tamper file
    target = result.dataset_path / "out/part.parquet"
    target.write_bytes(b"TAMPERED")
    report = verify_dataset(
        config=config,
        catalog=catalog,
        dataset_id=result.dataset_id,
        expected_manifest=result.manifest,
    )
    assert report.ok is False
    assert any(f.code == "output_mismatch" for f in report.findings)


def test_catalog_manifest_disagreement(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "2" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    catalog = SqliteDatasetCatalog(db)
    publisher = DatasetPublisher(config, catalog)
    plan, _ = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])
    result = publisher.publish(plan)
    # Corrupt catalog hash
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE dataset SET manifest_sha256 = ? WHERE dataset_id = ?",
        ("0" * 64, result.dataset_id),
    )
    conn.commit()
    conn.close()
    report = verify_dataset(
        config=config,
        catalog=SqliteDatasetCatalog(db),
        dataset_id=result.dataset_id,
        expected_manifest=result.manifest,
    )
    assert report.ok is False
    assert any(f.code == "catalog_manifest_disagreement" for f in report.findings)


def test_statistics_must_match_files(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "3" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    publisher = DatasetPublisher(config, SqliteDatasetCatalog(db))
    plan, sources = _plan(
        tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")]
    )
    bad = PublishPlan(
        dataset_type=plan.dataset_type,
        schema=plan.schema,
        transform=plan.transform,
        code=plan.code,
        config=plan.config,
        dependencies=plan.dependencies,
        output_sources=plan.output_sources,
        output_specs=plan.output_specs,
        statistics=DatasetStatistics(row_count=999, byte_size=plan.statistics.byte_size),
        coverage=plan.coverage,
        quality_status=plan.quality_status,
        quality_summary=plan.quality_summary,
        created_at=plan.created_at,
    )
    with pytest.raises(Exception, match="row_count"):
        publisher.publish(bad)
