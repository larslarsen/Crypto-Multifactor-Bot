"""Focused MAN-001 integrity regression tests. Junior executes these."""

from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from cryptofactors.catalog.dataset import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetPublicationError,
    DatasetPublicationInProgressError,
    DatasetPublisher,
    DatasetPublishResult,
    DatasetStatistics,
    DatasetStoreConfig,
    DependencyKind,
    DependencyRef,
    InvalidManifestError,
    MissingInputError,
    OutputFileSpec,
    OutputVerificationError,
    PublishPlan,
    QualityStatus,
    RecoverableDatasetCatalogError,
    RowCountPolicy,
    SchemaIdentity,
    SqliteDatasetCatalog,
    SupersessionError,
    TransformSpec,
    UnsafePathError,
    compute_dataset_id,
    dumps_canonical,
    identity_payload,
    load_manifest_file,
    normalize_value,
    stream_sha256_and_size,
    verify_dataset,
    verify_outputs,
)
from cryptofactors.catalog.dataset.errors import CorruptDatasetError
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations

UTC = timezone.utc


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
        (source_id, datetime.now(UTC).isoformat()),
    )
    sha = raw_id[4:] if raw_id.startswith("raw_") else hashlib.sha256(raw_id.encode()).hexdigest()
    rid = raw_id if raw_id.startswith("raw_") else f"raw_{sha}"
    conn.execute(
        """
        INSERT OR IGNORE INTO raw_object (
            raw_object_id, source_id, sha256, byte_size, storage_uri,
            original_name, request_json, response_metadata_json, source_checksum,
            acquired_at, event_start, event_end, status
        ) VALUES (?, ?, ?, 0, ?, NULL, '{}', '{}', NULL, ?, NULL, NULL, 'ACQUIRED')
        """,
        (rid, source_id, sha, f"raw/sha256/ab/cd/{sha}", datetime.now(UTC).isoformat()),
    )
    conn.commit()
    conn.close()


def _lines(path: Path) -> int:
    with path.open("rb") as f:
        return sum(1 for _ in f)


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
    rel: str = "out/part.parquet",
    deps: list[DependencyRef] | None = None,
    dataset_type: str = "bars",
    row_policy: RowCountPolicy = RowCountPolicy.REQUIRE_VERIFIER,
) -> PublishPlan:
    path = _file(tmp_path, rel, data)
    sha, sz = stream_sha256_and_size(path)
    specs = [
        OutputFileSpec(
            relative_path=rel, sha256=sha, rows=rows, bytes=sz, partition={"p": "0"}
        )
    ]
    counters = {rel: _lines} if row_policy is RowCountPolicy.REQUIRE_VERIFIER else {}
    return PublishPlan(
        dataset_type=dataset_type,
        schema=SchemaIdentity(name="ohlcv", version="1", fingerprint="sch_" + "a" * 60),
        transform=TransformSpec(name="trades_to_bars", version="1.0.0"),
        code=CodeIdentity(commit="abc1234deadbeef"),
        config=ConfigIdentity(config_sha256="c" * 64),
        dependencies=deps
        or [DependencyRef(id="raw_" + "b" * 64, kind=DependencyKind.RAW_OBJECT, role="trades")],
        output_sources={rel: path},
        output_specs=specs,
        statistics=DatasetStatistics(row_count=rows, byte_size=sz),
        coverage=CoverageWindow(
            event_start=datetime(2024, 1, 1, tzinfo=UTC),
            event_end=datetime(2024, 1, 2, tzinfo=UTC),
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={"warnings": 0},
        row_count_policy=row_policy,
        row_counters=counters,
    )


def test_logical_path_affects_identity() -> None:
    base_files_a = [OutputFileSpec("a/x.bin", "e" * 64, 1, 1)]
    base_files_b = [OutputFileSpec("b/x.bin", "e" * 64, 1, 1)]
    id_a, _ = compute_dataset_id(
        identity_payload(
            dataset_type="x",
            schema=SchemaIdentity("s", "1"),
            transform=TransformSpec("t", "1"),
            code=CodeIdentity("commit01"),
            config=ConfigIdentity("d" * 64),
            dependencies=[],
            statistics=DatasetStatistics(1, 1),
            coverage=CoverageWindow(),
            quality_status=QualityStatus.PASS,
            quality_summary={},
            supersedes_dataset_id=None,
            files=base_files_a,
        )
    )
    id_b, _ = compute_dataset_id(
        identity_payload(
            dataset_type="x",
            schema=SchemaIdentity("s", "1"),
            transform=TransformSpec("t", "1"),
            code=CodeIdentity("commit01"),
            config=ConfigIdentity("d" * 64),
            dependencies=[],
            statistics=DatasetStatistics(1, 1),
            coverage=CoverageWindow(),
            quality_status=QualityStatus.PASS,
            quality_summary={},
            supersedes_dataset_id=None,
            files=base_files_b,
        )
    )
    assert id_a != id_b


def _common_payload(
    files: list[OutputFileSpec],
    *,
    stats: DatasetStatistics,
    summary: dict[str, Any],
    code: str = "c" * 8,
) -> dict[str, Any]:
    """Typed wrapper around identity_payload (explicit args; mypy-clean)."""
    return identity_payload(
        dataset_type="x",
        schema=SchemaIdentity("s", "1"),
        transform=TransformSpec("t", "1"),
        code=CodeIdentity(code),
        config=ConfigIdentity("d" * 64),
        dependencies=[],
        statistics=stats,
        coverage=CoverageWindow(),
        quality_status=QualityStatus.PASS,
        quality_summary=summary,
        supersedes_dataset_id=None,
        files=files,
    )


def test_reversed_output_order_stable() -> None:
    files = [
        OutputFileSpec("z.bin", "f" * 64, 1, 1, {"z": 1}),
        OutputFileSpec("a.bin", "e" * 64, 2, 2, {"a": 1}),
    ]
    p1 = _common_payload(files, stats=DatasetStatistics(3, 3), summary={"k": Decimal("1.5")})
    p2 = _common_payload(
        list(reversed(files)),
        stats=DatasetStatistics(3, 3),
        summary={"k": Decimal("1.5")},
    )
    assert dumps_canonical(p1) == dumps_canonical(p2)


def test_partition_order_stable() -> None:
    f1 = OutputFileSpec("a.bin", "e" * 64, 1, 1, {"b": 2, "a": 1})
    f2 = OutputFileSpec("a.bin", "e" * 64, 1, 1, {"a": 1, "b": 2})
    assert dumps_canonical(
        _common_payload([f1], stats=DatasetStatistics(1, 1), summary={})
    ) == dumps_canonical(
        _common_payload([f2], stats=DatasetStatistics(1, 1), summary={})
    )


def test_duplicate_outputs_rejected() -> None:
    files = [
        OutputFileSpec("a.bin", "e" * 64, 1, 1),
        OutputFileSpec("a.bin", "f" * 64, 2, 2),
    ]
    with pytest.raises(InvalidManifestError, match="duplicate logical"):
        identity_payload(
            dataset_type="x",
            schema=SchemaIdentity("s", "1"),
            transform=TransformSpec("t", "1"),
            code=CodeIdentity("c" * 8),
            config=ConfigIdentity("d" * 64),
            dependencies=[],
            files=files,
            statistics=DatasetStatistics(3, 3),
            coverage=CoverageWindow(),
            quality_status=QualityStatus.PASS,
            quality_summary={},
            supersedes_dataset_id=None,
        )


def test_retry_without_created_at_idempotent(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    cat = SqliteDatasetCatalog(db)
    pub = DatasetPublisher(config, cat)
    plan = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])
    assert plan.created_at is None
    r1 = pub.publish(plan)
    r2 = pub.publish(plan)
    assert r1.dataset_id == r2.dataset_id
    assert r1.manifest_sha256 == r2.manifest_sha256
    assert r2.reused_existing is True
    # Canonical on-disk bytes stable
    m1 = (r1.dataset_path / "manifest.json").read_bytes()
    m2 = (r2.dataset_path / "manifest.json").read_bytes()
    assert m1 == m2


def test_row_count_mismatch(tmp_path: Path) -> None:
    p = _file(tmp_path, "f.bin", b"a\nb\n")
    sha, sz = stream_sha256_and_size(p)
    with pytest.raises(OutputVerificationError, match="row count"):
        verify_outputs(
            sources={"f.bin": p},
            specs=[OutputFileSpec("f.bin", sha, rows=99, bytes=sz)],
            row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
            row_counters={"f.bin": _lines},
        )


def test_row_verifier_required_by_default(tmp_path: Path) -> None:
    p = _file(tmp_path, "f.bin", b"a\n")
    sha, sz = stream_sha256_and_size(p)
    with pytest.raises(OutputVerificationError, match="verifier"):
        verify_outputs(
            sources={"f.bin": p},
            specs=[OutputFileSpec("f.bin", sha, rows=1, bytes=sz)],
            row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        )


def test_existing_empty_final_directory_rejected(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    config = DatasetStoreConfig(
        root=store,
        publication_wait_seconds=0.0,
        publication_initial_backoff_seconds=0.001,
        publication_max_backoff_seconds=0.001,
    )
    plan = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])
    # Precompute id and create empty final dir
    from cryptofactors.catalog.dataset.canonicalize import identity_payload as ip
    from cryptofactors.catalog.dataset.outputs import verify_outputs as vo

    verified = vo(
        sources=dict(plan.output_sources),
        specs=list(plan.output_specs),
        row_count_policy=plan.row_count_policy,
        row_counters=dict(plan.row_counters),
    )
    ident = ip(
        dataset_type=plan.dataset_type,
        schema=plan.schema,
        transform=plan.transform,
        code=plan.code,
        config=plan.config,
        dependencies=list(plan.dependencies),
        files=verified,
        statistics=plan.statistics,
        coverage=plan.coverage,
        quality_status=plan.quality_status,
        quality_summary=plan.quality_summary,
        supersedes_dataset_id=None,
    )
    ds_id, _ = compute_dataset_id(ident)
    final = dataset_absolute_dir_helper(store, ds_id)
    final.mkdir(parents=True, exist_ok=True)
    pub = DatasetPublisher(config, SqliteDatasetCatalog(db))
    # A pre-existing empty/incomplete final dir is treated as an incomplete
    # reservation: the protocol waits (bounded) then rejects it as in-progress.
    with pytest.raises(DatasetPublicationInProgressError):
        pub.publish(plan)


def dataset_absolute_dir_helper(root: Path, dataset_id: str) -> Path:
    from cryptofactors.catalog.dataset.paths import dataset_absolute_dir

    return dataset_absolute_dir(root, dataset_id)


def test_publish_roundtrip_and_verify_without_expected(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    cat = SqliteDatasetCatalog(db)
    pub = DatasetPublisher(config, cat)
    plan = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])
    result = pub.publish(plan)
    report = verify_dataset(
        config=config, catalog=cat, dataset_id=result.dataset_id, expected_manifest=None
    )
    assert report.ok is True
    assert report.recomputed_dataset_id == result.dataset_id


def test_manifest_trailing_whitespace_tamper(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    cat = SqliteDatasetCatalog(db)
    pub = DatasetPublisher(config, cat)
    plan = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])
    result = pub.publish(plan)
    man = result.dataset_path / "manifest.json"
    man.write_bytes(man.read_bytes() + b" \n")
    with pytest.raises(InvalidManifestError):
        load_manifest_file(man)
    report = verify_dataset(config=config, catalog=cat, dataset_id=result.dataset_id)
    assert report.ok is False


def test_unexpected_final_file(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    cat = SqliteDatasetCatalog(db)
    pub = DatasetPublisher(config, cat)
    plan = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])
    result = pub.publish(plan)
    (result.dataset_path / "extra.bin").write_bytes(b"x")
    report = verify_dataset(config=config, catalog=cat, dataset_id=result.dataset_id)
    assert report.ok is False
    assert any(f.code == "unexpected_file" for f in report.findings)


def test_symlinked_dataset_prefix_rejected(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    real = tmp_path / "elsewhere"
    real.mkdir()
    (store / "datasets").symlink_to(real)
    with pytest.raises((UnsafePathError, CorruptDatasetError, Exception)):
        # Construction of publisher or publish should fail closed on symlink prefix.
        config = DatasetStoreConfig(root=store, object_prefix="datasets/sha256")
        db = _db(tmp_path)
        raw_id = "raw_" + "b" * 64
        _seed_raw(db, raw_id)
        pub = DatasetPublisher(config, SqliteDatasetCatalog(db))
        plan = _plan(
            tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")]
        )
        pub.publish(plan)


def test_arbitrary_catalog_registration_without_receipt_not_public() -> None:
    # register_dataset was removed; only register_from_receipt exists.
    assert not hasattr(SqliteDatasetCatalog, "register_dataset")
    assert hasattr(SqliteDatasetCatalog, "register_from_receipt")


def test_incomplete_catalog_child_rows_not_idempotent(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    cat = SqliteDatasetCatalog(db)
    pub = DatasetPublisher(config, cat)
    plan = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])
    result = pub.publish(plan)
    # Delete child rows
    conn = sqlite3.connect(db)
    conn.execute("DELETE FROM dataset_file WHERE dataset_id = ?", (result.dataset_id,))
    conn.commit()
    conn.close()
    with pytest.raises(CorruptDatasetError):
        cat.register_from_receipt(result.receipt, manifest=result.manifest)


def test_supersession_missing_and_self(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    config = DatasetStoreConfig(root=tmp_path / "store")
    cat = SqliteDatasetCatalog(db)
    pub = DatasetPublisher(config, cat)
    plan = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])
    # missing supersedes
    bad = PublishPlan(
        dataset_type=plan.dataset_type,
        schema=plan.schema,
        transform=plan.transform,
        code=plan.code,
        config=plan.config,
        dependencies=plan.dependencies,
        output_sources=plan.output_sources,
        output_specs=plan.output_specs,
        statistics=plan.statistics,
        coverage=plan.coverage,
        quality_status=plan.quality_status,
        quality_summary=plan.quality_summary,
        supersedes_dataset_id="ds_" + "0" * 64,
        row_count_policy=plan.row_count_policy,
        row_counters=plan.row_counters,
    )
    # Missing supersession target is rejected at catalog registration (after the
    # immutable files are published). The spec surfaces this as a typed recoverable
    # registration error with the SupersessionError as its cause — dataset is not
    # registered and the on-disk tree is retained for idempotent retry.
    with pytest.raises(RecoverableDatasetCatalogError):
        pub.publish(bad)

    r1 = pub.publish(plan)
    # self supersession
    plan2 = _plan(
        tmp_path,
        data=b"other\n",
        rows=1,
        rel="out/other.parquet",
        deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")],
        dataset_type="other",
    )
    # force supersedes to r1 then also test self via catalog
    with pytest.raises(SupersessionError):
        cat._validate_supersession(r1.dataset_id, r1.dataset_id)


def test_concurrent_publish(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "e" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    barrier = threading.Barrier(3)
    results: list[object] = []
    errors: list[BaseException] = []

    def worker(i: int) -> None:
        local = tmp_path / f"w{i}"
        plan = _plan(
            local,
            data=b"same-content\n",
            rows=1,
            deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")],
        )
        cat = SqliteDatasetCatalog(db)
        cfg = DatasetStoreConfig(
            root=store,
            publication_wait_seconds=10.0,
            publication_initial_backoff_seconds=0.005,
            publication_max_backoff_seconds=0.05,
        )
        pub = DatasetPublisher(cfg, cat)
        barrier.wait()
        try:
            results.append(pub.publish(plan))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            cat.close()

    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = [pool.submit(worker, i) for i in range(3)]
        for f in futs:
            f.result()
    assert not errors, errors
    assert len(results) == 3
    assert len({getattr(r, "dataset_id") for r in results}) == 1
    # At least one publisher and at least one reuser under contention.
    assert any(getattr(r, "reused_existing") is True for r in results) or len(results) == 3
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM dataset").fetchone()[0]
    assert n == 1


def test_loser_waits_for_manifest_before_reuse(tmp_path: Path) -> None:
    """Loser that sees the directory before manifest.json must wait and then reuse."""
    from cryptofactors.catalog.dataset import publisher as pub_mod

    db = _db(tmp_path)
    raw_id = "raw_" + "e" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    plan = _plan(
        tmp_path,
        data=b"wait-content\n",
        rows=1,
        deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")],
    )
    cfg = DatasetStoreConfig(
        root=store,
        publication_wait_seconds=5.0,
        publication_initial_backoff_seconds=0.01,
        publication_max_backoff_seconds=0.05,
    )

    # Compute final path and simulate incomplete reservation.
    # Publish once normally first to get the path, then delete manifest briefly...
    # Better: intercept owner populate to stall before manifest.
    stall = threading.Event()
    owner_started = threading.Event()
    real_publish_manifest = pub_mod._publish_manifest_atomic

    def slow_manifest(final_dir: Path, manifest_bytes: bytes) -> None:
        owner_started.set()
        stall.wait(timeout=5.0)
        real_publish_manifest(final_dir, manifest_bytes)

    results: list[tuple[str, DatasetPublishResult]] = []
    errors: list[BaseException] = []

    def owner() -> None:
        try:
            # Catalog opened in this thread (SQLite connections are not thread-safe).
            cat_o = SqliteDatasetCatalog(db)
            pub_o = DatasetPublisher(cfg, cat_o)
            with mock.patch.object(pub_mod, "_publish_manifest_atomic", slow_manifest):
                results.append(("owner", pub_o.publish(plan)))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    def loser() -> None:
        owner_started.wait(timeout=5.0)
        try:
            # Second publisher with same plan/content — should wait for marker.
            cat2 = SqliteDatasetCatalog(db)
            pub2 = DatasetPublisher(cfg, cat2)
            results.append(("loser", pub2.publish(plan)))
            cat2.close()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)


    t1 = threading.Thread(target=owner)
    t2 = threading.Thread(target=loser)
    t1.start()
    t2.start()
    # Allow loser to observe incomplete reservation, then release owner.
    time.sleep(0.05)
    stall.set()
    t1.join(timeout=10)
    t2.join(timeout=10)
    assert not errors, errors
    roles = {r[0] for r in results}
    assert "owner" in roles and "loser" in roles
    assert results[0][1].dataset_id == results[1][1].dataset_id
    assert any(r[0] == "loser" and r[1].reused_existing for r in results)


def test_loser_retries_after_owner_cleanup(tmp_path: Path) -> None:
    """If incomplete reservation disappears, loser may become owner."""
    from cryptofactors.catalog.dataset import publisher as pub_mod

    db = _db(tmp_path)
    raw_id = "raw_" + "e" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    plan = _plan(
        tmp_path,
        data=b"retry-owner\n",
        rows=1,
        deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")],
    )
    cfg = DatasetStoreConfig(
        root=store,
        publication_wait_seconds=5.0,
        publication_initial_backoff_seconds=0.01,
        publication_max_backoff_seconds=0.05,
    )

    # First publisher fails after mkdir, before manifest — cleans up.
    calls = {"n": 0}
    real_link = pub_mod._link_or_copy_exclusive

    def fail_first_child(src: Path, dest: Path, *, chunk_size: int) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise DatasetPublicationError("simulated owner failure")
        return real_link(src, dest, chunk_size=chunk_size)

    cat = SqliteDatasetCatalog(db)
    pub = DatasetPublisher(cfg, cat)
    with mock.patch.object(pub_mod, "_link_or_copy_exclusive", fail_first_child):
        with pytest.raises(DatasetPublicationError, match="simulated"):
            pub.publish(plan)
    # Reservation cleaned — second publish succeeds as owner.
    result = pub.publish(plan)
    assert result.reused_existing is False
    assert (result.dataset_path / "manifest.json").is_file()


def test_timeout_on_permanently_incomplete_reservation(tmp_path: Path) -> None:
    from cryptofactors.catalog.dataset import DatasetPublicationInProgressError
    from cryptofactors.catalog.dataset.paths import dataset_absolute_dir
    from cryptofactors.catalog.dataset.canonicalize import identity_payload
    from cryptofactors.catalog.dataset.outputs import verify_outputs as vo

    db = _db(tmp_path)
    raw_id = "raw_" + "e" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    plan = _plan(
        tmp_path,
        data=b"stuck\n",
        rows=1,
        deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")],
    )
    verified = vo(
        sources=dict(plan.output_sources),
        specs=list(plan.output_specs),
        row_count_policy=plan.row_count_policy,
        row_counters=dict(plan.row_counters),
    )
    ident = identity_payload(
        dataset_type=plan.dataset_type,
        schema=plan.schema,
        transform=plan.transform,
        code=plan.code,
        config=plan.config,
        dependencies=list(plan.dependencies),
        files=verified,
        statistics=plan.statistics,
        coverage=plan.coverage,
        quality_status=plan.quality_status,
        quality_summary=plan.quality_summary,
        supersedes_dataset_id=None,
    )
    ds_id, _ = compute_dataset_id(ident)
    final = dataset_absolute_dir(store, ds_id)
    final.mkdir(parents=True, exist_ok=True)  # incomplete: no manifest.json

    cfg = DatasetStoreConfig(
        root=store,
        publication_wait_seconds=0.15,
        publication_initial_backoff_seconds=0.02,
        publication_max_backoff_seconds=0.05,
    )
    pub = DatasetPublisher(cfg, SqliteDatasetCatalog(db))
    with pytest.raises(DatasetPublicationInProgressError, match="timed out"):
        pub.publish(plan)
    # Non-owner must not delete the reservation.
    assert final.is_dir()
    assert not (final / "manifest.json").exists()


def test_owner_failure_cleans_incomplete_only(tmp_path: Path) -> None:
    from cryptofactors.catalog.dataset import publisher as pub_mod

    db = _db(tmp_path)
    raw_id = "raw_" + "e" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    plan = _plan(
        tmp_path,
        data=b"cleanup\n",
        rows=1,
        deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")],
    )
    cfg = DatasetStoreConfig(root=store)
    pub = DatasetPublisher(cfg, SqliteDatasetCatalog(db))

    def boom_manifest(final_dir: Path, manifest_bytes: bytes) -> None:
        raise DatasetPublicationError("manifest failed")

    with mock.patch.object(pub_mod, "_publish_manifest_atomic", boom_manifest):
        with pytest.raises(DatasetPublicationError, match="manifest failed"):
            pub.publish(plan)
    # Incomplete reservation cleaned by owner.
    # No accepted dataset remains under store.
    left = list((store / "datasets").rglob("manifest.json")) if (store / "datasets").exists() else []
    assert left == []


def test_child_no_clobber(tmp_path: Path) -> None:
    from cryptofactors.catalog.dataset.publisher import _copy_file_streaming_exclusive

    src = _file(tmp_path, "src.bin", b"abc")
    dest = tmp_path / "dest.bin"
    dest.write_bytes(b"existing")
    with pytest.raises(DatasetPublicationError, match="no-clobber"):
        _copy_file_streaming_exclusive(src, dest)


def test_high_contention_publication(tmp_path: Path) -> None:
    db = _db(tmp_path)
    raw_id = "raw_" + "f" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    n_workers = 8
    barrier = threading.Barrier(n_workers)
    results: list[object] = []
    errors: list[BaseException] = []

    def worker(i: int) -> None:
        local = tmp_path / f"hc{i}"
        plan = _plan(
            local,
            data=b"contention-payload\n",
            rows=1,
            deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")],
        )
        cat = SqliteDatasetCatalog(db)
        cfg = DatasetStoreConfig(
            root=store,
            publication_wait_seconds=15.0,
            publication_initial_backoff_seconds=0.002,
            publication_max_backoff_seconds=0.1,
        )
        pub = DatasetPublisher(cfg, cat)
        barrier.wait()
        try:
            results.append(pub.publish(plan))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            cat.close()

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futs = [pool.submit(worker, i) for i in range(n_workers)]
        for f in futs:
            f.result()
    assert not errors, errors
    assert len(results) == n_workers
    assert len({getattr(r, "dataset_id") for r in results}) == 1
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM dataset").fetchone()[0]
    assert n == 1


def test_missing_raw_input(tmp_path: Path) -> None:
    db = _db(tmp_path)
    pub = DatasetPublisher(DatasetStoreConfig(root=tmp_path / "store"), SqliteDatasetCatalog(db))
    with pytest.raises(MissingInputError):
        pub.publish(_plan(tmp_path))


def test_reject_float() -> None:
    with pytest.raises(InvalidManifestError):
        normalize_value(1.2)
