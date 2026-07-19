"""MAN-001 Senior-review correction regression tests.

Covers all seven required defect categories:
1. Published output bytes are independent of caller-owned source files.
2. Temporary build area + atomic final rename; no partial final directory.
3. Output-keyed mappings canonicalized consistently; collisions rejected typed.
4. Pydantic wire model = source of truth; schema synced; fail-closed.
5. Exact catalog idempotence + verify_dataset field comparison.
6. Receipt verification independently confirms the on-disk tree before catalog txn.
7. (Covered in test_dataset_manifest.py) ruff hygiene.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import threading
import time
from datetime import datetime, UTC
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
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.errors import (
    CorruptDatasetError,
    DatasetPublicationError,
    OutputVerificationError,
)
from cryptofactors.catalog.dataset.models import (
    DatasetPublicationReceipt,
    RowCountReceipt,
)
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size, verify_outputs
from cryptofactors.catalog.dataset.schema_model import (
    generate_schema_json,
    validate_manifest_dict,
)
from cryptofactors.catalog.dataset.verification import verify_dataset
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations


# --- fixtures ---------------------------------------------------------------

def _seed_raw(db: Path, raw_id: str) -> None:
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "INSERT OR IGNORE INTO source "
        "(source_id, source_type, official_url, terms_class, config_json, created_at) "
        "VALUES (?, 'external', NULL, NULL, '{}', ?)",
        ("src1", datetime.now(UTC).isoformat()),
    )
    sha = raw_id[4:]
    conn.execute(
        "INSERT OR IGNORE INTO raw_object "
        "(raw_object_id, source_id, sha256, byte_size, storage_uri, original_name, "
        "request_json, response_metadata_json, source_checksum, acquired_at, "
        "event_start, event_end, status) "
        "VALUES (?, ?, ?, 0, ?, NULL, '{}', '{}', NULL, ?, NULL, NULL, 'ACQUIRED')",
        (raw_id, "src1", sha, f"raw/sha256/ab/cd/{sha}", datetime.now(UTC).isoformat()),
    )
    conn.commit()
    conn.close()


def _plan(
    tmp_path: Path,
    *,
    data: bytes = b"row1\nrow2\n",
    rows: int = 2,
    rel: str = "out/part.parquet",
    deps: list[DependencyRef] | None = None,
    dataset_type: str = "bars",
) -> tuple[Path, PublishPlan]:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    sha, sz = stream_sha256_and_size(path)
    specs = [
        OutputFileSpec(
            relative_path=rel, sha256=sha, rows=rows, bytes=sz, partition={"p": "0"}
        )
    ]
    return path, PublishPlan(
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
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters={rel: lambda p: rows},
    )


def _publish_roundtrip(tmp_path: Path) -> tuple[Any, Any, Any, Any, Any, Any, Any]:
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    cat = SqliteDatasetCatalog(db)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    cfg = DatasetStoreConfig(
        root=store,
        publication_wait_seconds=10.0,
        publication_initial_backoff_seconds=0.01,
        publication_max_backoff_seconds=0.1,
    )
    pub = DatasetPublisher(cfg, cat)
    src_path, plan = _plan(
        tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")]
    )
    result = pub.publish(plan)
    cat.register_from_receipt(result.receipt, manifest=result.manifest)
    return db, cat, cfg, pub, src_path, plan, result


def _dsid_of_plan(plan: PublishPlan) -> str:
    from cryptofactors.catalog.dataset.canonicalize import (
        compute_dataset_id,
        identity_payload,
    )

    verified = verify_outputs(
        sources=dict(plan.output_sources),
        specs=list(plan.output_specs),
        row_count_policy=plan.row_count_policy,
        row_counters=dict(plan.row_counters),
        row_receipts=dict(plan.row_receipts),
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
        supersedes_dataset_id=plan.supersedes_dataset_id,
    )
    ds_id, _ = compute_dataset_id(ident)
    return ds_id


def _final_dir_of(pub: DatasetPublisher, plan: PublishPlan) -> Path:
    return dataset_absolute_dir(pub._config.root, _dsid_of_plan(plan))


# --- Defect #1: independent published bytes ---------------------------------

def test_published_bytes_independent_of_source(tmp_path: Path) -> None:
    db, cat, cfg, pub, src_path, plan, result = _publish_roundtrip(tmp_path)
    dest = result.dataset_path / "out" / "part.parquet"
    assert dest.is_file()
    s_src = os.stat(src_path)
    s_dst = os.stat(dest)
    if s_src.st_dev == s_dst.st_dev and s_src.st_ino == s_dst.st_ino:
        pytest.fail("published file shares inode with source (hard link)")

    expected_sha = result.manifest.files[0].sha256
    expected_sz = result.manifest.files[0].bytes
    src_path.write_bytes(b"tampered-after-publish\n")
    src_path.unlink()
    sha, sz = stream_sha256_and_size(dest)
    assert sha == expected_sha and sz == expected_sz
    report = verify_dataset(config=cfg, catalog=cat, dataset_id=result.dataset_id)
    assert report.ok is True


# --- Defect #2: temp build area + atomic rename -----------------------------

def test_stall_before_rename_final_path_absent(tmp_path: Path) -> None:
    from unittest import mock

    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    cfg = DatasetStoreConfig(root=store, publication_wait_seconds=10.0)
    pub = DatasetPublisher(cfg, SqliteDatasetCatalog(db))
    _, plan = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])

    final_dir = _final_dir_of(pub, plan)
    release = threading.Event()
    real_rename = os.rename

    def stalled_rename(src: str, dst: str) -> None:
        if dst == str(final_dir):
            release.wait(timeout=5.0)
        real_rename(src, dst)

    def owner() -> None:
        # Fresh catalog/connection inside the worker thread (SQLite threadsafety).
        p = DatasetPublisher(cfg, SqliteDatasetCatalog(db))
        p.publish(plan)

    with mock.patch.object(os, "rename", stalled_rename):
        t = threading.Thread(target=owner, daemon=True)
        t.start()
        time.sleep(0.3)
        assert not final_dir.exists(), "final path must be absent before atomic rename"
        release.set()
        t.join(timeout=10)
    assert final_dir.is_dir() and (final_dir / "manifest.json").is_file()


def test_injected_rename_failure_leaves_no_final_path(tmp_path: Path) -> None:
    from unittest import mock

    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    cfg = DatasetStoreConfig(root=store, publication_wait_seconds=10.0)
    cat = SqliteDatasetCatalog(db)
    pub = DatasetPublisher(cfg, cat)
    _, plan = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])

    final_dir = _final_dir_of(pub, plan)

    def failing_rename(src: str, dst: str) -> None:
        if dst == str(final_dir):
            raise OSError("injected pre-rename failure")
        real_rename(src, dst)

    real_rename = os.rename

    def owner() -> None:
        p = DatasetPublisher(cfg, SqliteDatasetCatalog(db))
        p.publish(plan)

    with mock.patch.object(os, "rename", failing_rename):
        with pytest.raises(DatasetPublicationError):
            owner()
    assert not final_dir.exists()
    assert cat.get_dataset(_dsid_of_plan(plan)) is None


def test_preexisting_empty_final_directory_never_replaced(tmp_path: Path) -> None:
    from cryptofactors.catalog.dataset import DatasetPublicationInProgressError

    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    cfg = DatasetStoreConfig(
        root=store,
        publication_wait_seconds=0.2,
        publication_initial_backoff_seconds=0.02,
        publication_max_backoff_seconds=0.05,
    )
    pub = DatasetPublisher(cfg, SqliteDatasetCatalog(db))
    _, plan = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])

    final_dir = _final_dir_of(pub, plan)
    final_dir.mkdir(parents=True, exist_ok=True)
    with pytest.raises(DatasetPublicationInProgressError):
        pub.publish(plan)
    assert final_dir.is_dir()
    assert not (final_dir / "manifest.json").exists()
    assert not any(final_dir.iterdir())


def test_multi_worker_converge_one_dataset_and_row(tmp_path: Path) -> None:
    import concurrent.futures as cf

    for n_workers in (3, 8):
        db = tmp_path / f"control_{n_workers}.db"
        apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
        raw_id = "raw_" + "c" * 64
        _seed_raw(db, raw_id)
        store = tmp_path / f"store_{n_workers}"
        cfg = DatasetStoreConfig(
            root=store,
            publication_wait_seconds=15.0,
            publication_initial_backoff_seconds=0.002,
            publication_max_backoff_seconds=0.05,
        )
        _, plan = _plan(
            tmp_path / f"p_{n_workers}",
            deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")],
        )

        def _worker() -> None:
            c = SqliteDatasetCatalog(db)
            p = DatasetPublisher(cfg, c)
            res = p.publish(plan)
            c.register_from_receipt(res.receipt, manifest=res.manifest)
            c.close()

        with cf.ThreadPoolExecutor(max_workers=n_workers) as pool:
            futs = [pool.submit(_worker) for _ in range(n_workers)]
            for f in futs:
                f.result()

        cat = SqliteDatasetCatalog(db)
        rows = cat._conn.execute(
            "SELECT dataset_id FROM dataset WHERE dataset_id = ?",
            (_dsid_of_plan(plan),),
        ).fetchall()
        assert len(rows) == 1, f"{n_workers}-worker produced {len(rows)} catalog rows"
        trees = list((store / "datasets").rglob("manifest.json"))
        assert len(trees) == 1


def test_no_successful_caller_sees_incomplete_tree(tmp_path: Path) -> None:
    from cryptofactors.catalog.dataset import publisher as pub_mod
    from unittest import mock

    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    cfg = DatasetStoreConfig(root=store, publication_wait_seconds=10.0)
    cat = SqliteDatasetCatalog(db)
    pub = DatasetPublisher(cfg, cat)
    _, plan = _plan(tmp_path, deps=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")])

    final_dir = _final_dir_of(pub, plan)
    real_copy = pub_mod._copy_to_new_inode
    calls = {"n": 0}

    def flaky_copy(src: Any, dest: Any, *, chunk_size: int) -> None:
        calls["n"] += 1
        if calls["n"] >= 1:
            raise DatasetPublicationError("mid-build simulated crash")
        real_copy(src, dest, chunk_size=chunk_size)

    def owner() -> None:
        p = DatasetPublisher(cfg, SqliteDatasetCatalog(db))
        p.publish(plan)

    with mock.patch.object(pub_mod, "_copy_to_new_inode", flaky_copy):
        with pytest.raises(DatasetPublicationError):
            owner()
    assert not final_dir.exists()
    assert cat.get_dataset(_dsid_of_plan(plan)) is None


# --- Defect #3: canonicalization of all output-keyed mappings ---------------

def test_equivalent_noncanonical_keys_handled_consistently(tmp_path: Path) -> None:
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    raw_id = "raw_" + "b" * 64
    _seed_raw(db, raw_id)
    store = tmp_path / "store"
    cfg = DatasetStoreConfig(root=store)
    pub = DatasetPublisher(cfg, SqliteDatasetCatalog(db))

    path = tmp_path / "src.bin"
    path.write_bytes(b"row1\nrow2\n")
    sha, sz = stream_sha256_and_size(path)
    plan = PublishPlan(
        dataset_type="bars",
        schema=SchemaIdentity(name="ohlcv", version="1", fingerprint="sch_" + "a" * 60),
        transform=TransformSpec(name="trades_to_bars", version="1.0.0"),
        code=CodeIdentity(commit="abc1234deadbeef"),
        config=ConfigIdentity(config_sha256="c" * 64),
        dependencies=[DependencyRef(raw_id, DependencyKind.RAW_OBJECT, "trades")],
        output_sources={"out/part.parquet": path},
        output_specs=[
            OutputFileSpec("out//part.parquet", sha, 2, sz, partition={"p": "0"})
        ],
        statistics=DatasetStatistics(2, sz),
        coverage=CoverageWindow(
            event_start=datetime(2024, 1, 1, tzinfo=UTC),
            event_end=datetime(2024, 1, 2, tzinfo=UTC),
        ),
        quality_status=QualityStatus.PASS,
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters={"out//part.parquet": lambda p: 2},
    )
    result = pub.publish(plan)
    assert (result.dataset_path / "out" / "part.parquet").is_file()


def test_distinct_keys_collapsing_to_same_canonical_rejected(tmp_path: Path) -> None:
    path = tmp_path / "src.bin"
    path.write_bytes(b"row1\nrow2\n")
    sha, sz = stream_sha256_and_size(path)
    with pytest.raises(OutputVerificationError, match="duplicate canonical"):
        verify_outputs(
            sources={"out/a.parquet": path, "out//a.parquet": path},
            specs=[OutputFileSpec("out/a.parquet", sha, 2, sz)],
            row_count_policy=RowCountPolicy.ALLOW_UNVERIFIED_DECLARED,
        )


def test_receipt_counter_keys_canonicalized(tmp_path: Path) -> None:
    path = tmp_path / "src.bin"
    path.write_bytes(b"row1\nrow2\n")
    sha, sz = stream_sha256_and_size(path)
    files = verify_outputs(
        sources={"out/a.parquet": path},
        specs=[OutputFileSpec("out/a.parquet", sha, 2, sz)],
        row_count_policy=RowCountPolicy.ALLOW_UNVERIFIED_DECLARED,
        row_receipts={
            "out//a.parquet": RowCountReceipt("out//a.parquet", 2, "verifier")
        },
    )
    assert files[0].rows == 2
    assert files[0].rows_verified is True


# --- Defect #4: Pydantic schema source of truth + contract -------------------

def test_canonical_manifest_validates_against_wire_model(tmp_path: Path) -> None:
    _, _, _, _, _, _, result = _publish_roundtrip(tmp_path)
    parsed = json.loads((result.dataset_path / "manifest.json").read_text())
    assert validate_manifest_dict(parsed) == parsed


def test_schema_describes_every_emitted_field(tmp_path: Path) -> None:
    _, _, _, _, _, _, result = _publish_roundtrip(tmp_path)
    schema = json.loads(generate_schema_json())
    emitted = json.loads((result.dataset_path / "manifest.json").read_text())
    for key in emitted:
        assert key in schema["properties"], f"schema missing emitted field {key!r}"
    for req in (
        "dataset_id",
        "dataset_type",
        "schema_version",
        "transform",
        "code_commit",
        "config_sha256",
        "dependencies",
        "files",
        "row_count",
        "byte_size",
        "quality_status",
        "manifest_sha256",
    ):
        assert req in schema["required"]


def test_schema_rejects_unknown_missing_malformed(tmp_path: Path) -> None:
    _, _, _, _, _, _, result = _publish_roundtrip(tmp_path)
    good = json.loads((result.dataset_path / "manifest.json").read_text())

    def _clone() -> Any:
        return json.loads(json.dumps(good))

    # unknown field
    bad = _clone()
    bad["extra_field"] = 1
    with pytest.raises(Exception):
        validate_manifest_dict(bad)
    # missing required
    bad = _clone()
    del bad["quality_status"]
    with pytest.raises(Exception):
        validate_manifest_dict(bad)
    # malformed sha256
    bad = _clone()
    bad["config_sha256"] = "not-a-hex"
    with pytest.raises(Exception):
        validate_manifest_dict(bad)
    # negative count
    bad = _clone()
    bad["row_count"] = -1
    with pytest.raises(Exception):
        validate_manifest_dict(bad)
    # naive timestamp
    bad = _clone()
    bad["created_at"] = "2024-01-01T00:00:00"
    with pytest.raises(Exception):
        validate_manifest_dict(bad)
    # inconsistent duplicate compat fields
    bad = _clone()
    bad["schema_version"] = "99"
    with pytest.raises(Exception):
        validate_manifest_dict(bad)
    # noncanonical wire bytes (uri != relative_path)
    bad = _clone()
    bad["files"][0]["uri"] = "out/other.parquet"
    with pytest.raises(Exception):
        validate_manifest_dict(bad)


def test_checked_in_schema_matches_generated(tmp_path: Path) -> None:
    repo_schema = json.loads(
        (Path(__file__).resolve().parent.parent.parent / "schemas" / "dataset_manifest.schema.json").read_text()
    )
    generated = json.loads(generate_schema_json())
    assert set(repo_schema["required"]) == set(generated["required"])
    assert set(repo_schema["properties"].keys()) == set(generated["properties"].keys())


# --- Defect #5: exact idempotence + verify_dataset field comparison ----------

@pytest.mark.parametrize(
    "field",
    [
        "schema_fingerprint",
        "quality_summary_json",
        "event_start",
        "event_end",
        "availability_start",
        "availability_end",
        "publication_status",
        "supersedes_dataset_id",
    ],
)
def test_verify_detects_catalog_tamper(tmp_path: Path, field: str) -> None:
    db, cat, cfg, _, _, _, result = _publish_roundtrip(tmp_path)
    ds_id = result.dataset_id
    if field == "schema_fingerprint":
        cat._conn.execute(
            "UPDATE dataset SET schema_fingerprint = 'tampered' WHERE dataset_id = ?", (ds_id,)
        )
    elif field == "quality_summary_json":
        cat._conn.execute(
            "UPDATE dataset SET quality_summary_json = '{\"x\":1}' WHERE dataset_id = ?", (ds_id,)
        )
    elif field == "event_start":
        cat._conn.execute(
            "UPDATE dataset SET event_start = '2000-01-01T00:00:00+00:00' WHERE dataset_id = ?", (ds_id,)
        )
    elif field == "event_end":
        cat._conn.execute(
            "UPDATE dataset SET event_end = '2000-01-01T00:00:00+00:00' WHERE dataset_id = ?", (ds_id,)
        )
    elif field == "availability_start":
        cat._conn.execute(
            "UPDATE dataset SET availability_start = '2000-01-01T00:00:00+00:00' WHERE dataset_id = ?", (ds_id,)
        )
    elif field == "availability_end":
        cat._conn.execute(
            "UPDATE dataset SET availability_end = '2000-01-01T00:00:00+00:00' WHERE dataset_id = ?", (ds_id,)
        )
    elif field == "publication_status":
        cat._conn.execute(
            "UPDATE dataset SET publication_status = 'QUARANTINED' WHERE dataset_id = ?", (ds_id,)
        )
    elif field == "supersedes_dataset_id":
        # Self-reference (valid FK, since the row exists) diverges from the
        # manifest (which supersedes nothing) and must fail verification.
        cat._conn.execute(
            "UPDATE dataset SET supersedes_dataset_id = ? WHERE dataset_id = ?",
            (ds_id, ds_id),
        )
    cat._conn.commit()
    report = verify_dataset(config=cfg, catalog=cat, dataset_id=ds_id)
    assert report.ok is False


def test_idempotent_reregistration_rejects_tampered_fields(tmp_path: Path) -> None:
    db, cat, cfg, pub, _, _, result = _publish_roundtrip(tmp_path)
    ds_id = result.dataset_id
    cat._conn.execute(
        "UPDATE dataset SET quality_summary_json = '{\"x\":1}' WHERE dataset_id = ?", (ds_id,)
    )
    cat._conn.commit()
    with pytest.raises(CorruptDatasetError):
        cat.register_from_receipt(result.receipt, manifest=result.manifest)


# --- Defect #6: receipt verification before catalog txn ----------------------

def test_register_fails_when_tree_deleted(tmp_path: Path) -> None:
    db, cat, cfg, pub, _, _, result = _publish_roundtrip(tmp_path)
    shutil.rmtree(result.dataset_path)
    before = cat.get_dataset(result.dataset_id)
    with pytest.raises(CorruptDatasetError):
        cat.register_from_receipt(result.receipt, manifest=result.manifest)
    assert cat.get_dataset(result.dataset_id) == before


def test_register_fails_when_output_mutated(tmp_path: Path) -> None:
    db, cat, cfg, pub, _, _, result = _publish_roundtrip(tmp_path)
    out = result.dataset_path / "out" / "part.parquet"
    out.write_bytes(b"mutated-content-after-receipt\n")
    with pytest.raises(CorruptDatasetError):
        cat.register_from_receipt(result.receipt, manifest=result.manifest)


def test_register_fails_when_manifest_mutated(tmp_path: Path) -> None:
    db, cat, cfg, pub, _, _, result = _publish_roundtrip(tmp_path)
    man = result.dataset_path / "manifest.json"
    text = man.read_text()
    # Canonical JSON has no spaces: {"warnings":0} not {"warnings": 0}.
    man.write_text(text.replace('"warnings":0', '"warnings":99'))
    with pytest.raises(CorruptDatasetError):
        cat.register_from_receipt(result.receipt, manifest=result.manifest)


def test_fabricated_complete_receipt_cannot_register_absent_tree(tmp_path: Path) -> None:
    db, cat, cfg, pub, _, _, result = _publish_roundtrip(tmp_path)
    fake_receipt = DatasetPublicationReceipt(
        dataset_id=result.dataset_id,
        manifest_sha256=result.manifest.manifest_sha256,
        manifest_uri=result.receipt.manifest_uri,
        publication_uri=result.receipt.publication_uri,
        dataset_path=tmp_path / "absent" / "ds_x",
        verified_outputs=result.manifest.files,
        publication_verified=True,
        object_prefix=cfg.object_prefix,
        dependencies=result.manifest.dependencies,
        supersedes_dataset_id=None,
        dataset_type=result.manifest.dataset_type,
        schema=result.manifest.schema,
        transform=result.manifest.transform,
        code=result.manifest.code,
        config=result.manifest.config,
        statistics=result.manifest.statistics,
        coverage=result.manifest.coverage,
        quality_status=result.manifest.quality_status,
        quality_summary=dict(result.manifest.quality_summary),
        catalog_created_at=result.manifest.publication.created_at,
    )
    with pytest.raises(CorruptDatasetError):
        cat.register_from_receipt(fake_receipt, manifest=result.manifest)


def test_valid_retry_registration_idempotent(tmp_path: Path) -> None:
    db, cat, cfg, pub, _, _, result = _publish_roundtrip(tmp_path)
    inserted = cat.register_from_receipt(result.receipt, manifest=result.manifest)
    assert inserted is False
