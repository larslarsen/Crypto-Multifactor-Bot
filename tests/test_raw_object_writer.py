"""Focused synthetic tests for RAW-001 (correction pass). Junior executes these."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations
from cryptofactors.ingest.raw import (
    AcquisitionMetadata,
    CatalogRegistrationError,
    ChecksumError,
    ChecksumVerification,
    HashMismatchError,
    IdempotentDuplicateResult,
    InterruptedWriteError,
    InvalidChunkError,
    PathSafetyError,
    ProviderChecksum,
    PublicationError,
    PublicationReceipt,
    RawObjectStoreConfig,
    RawObjectWriter,
    RecoverableCatalogRegistrationError,
    SqliteRawObjectCatalog,
    content_addressed_relative_path,
    reconcile_orphan_temps,
    verify_publication_receipt,
)
from cryptofactors.ingest.raw.writer import _publish_exclusive_link

UTC = timezone.utc


def _meta(source_id: str = "src_a", **kwargs: object) -> AcquisitionMetadata:
    base: dict[str, object] = {
        "source_id": source_id,
        "request": {"url": "https://example.test/obj"},
        "response_metadata": {"status": 200},
        "acquired_at": datetime(2025, 1, 1, tzinfo=UTC),
    }
    base.update(kwargs)
    return AcquisitionMetadata(**base)  # type: ignore[arg-type]


def _store(tmp_path: Path) -> tuple[RawObjectStoreConfig, SqliteRawObjectCatalog, RawObjectWriter, Path]:
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    root = tmp_path / "store"
    config = RawObjectStoreConfig(root=root)
    catalog = SqliteRawObjectCatalog(db)
    writer = RawObjectWriter(config, catalog, chunk_size=8)
    return config, catalog, writer, db


def test_empty_and_multi_chunk(tmp_path: Path) -> None:
    _, catalog, writer, _ = _store(tmp_path)
    empty = writer.write_stream([], _meta())
    assert empty.byte_size == 0
    assert empty.sha256 == hashlib.sha256(b"").hexdigest()
    body = b"abcdefghij"
    multi = writer.write_stream([body[:3], body[3:]], _meta(source_id="src_b"))
    assert multi.sha256 == hashlib.sha256(body).hexdigest()
    assert multi.storage_path.read_bytes() == body
    rel = content_addressed_relative_path(multi.sha256)
    assert multi.storage_uri == rel.as_posix()


def test_one_object_multiple_acquisitions(tmp_path: Path) -> None:
    _, catalog, writer, db = _store(tmp_path)
    body = b"shared-bytes"
    a1 = writer.write_stream(
        [body], _meta(source_id="src_a", acquisition_id="acq_1")
    )
    a2 = writer.write_stream(
        [body], _meta(source_id="src_a", acquisition_id="acq_2")
    )
    assert a1.raw_object_id == a2.raw_object_id
    assert a1.sha256 == a2.sha256
    acqs = catalog.list_acquisitions_for_object(a1.raw_object_id)
    assert len(acqs) == 2
    ids = {a["acquisition_id"] for a in acqs}
    assert ids == {"acq_1", "acq_2"}
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM raw_object").fetchone()[0]
    assert n == 1


def test_identical_content_different_sources(tmp_path: Path) -> None:
    _, catalog, writer, _ = _store(tmp_path)
    body = b"cross-source"
    r1 = writer.write_stream([body], _meta(source_id="src_x", acquisition_id="acq_x"))
    r2 = writer.write_stream([body], _meta(source_id="src_y", acquisition_id="acq_y"))
    assert r1.raw_object_id == r2.raw_object_id
    acqs = catalog.list_acquisitions_for_object(r1.raw_object_id)
    sources = {a["source_id"] for a in acqs}
    assert sources == {"src_x", "src_y"}


def test_idempotent_retry_same_acquisition_id(tmp_path: Path) -> None:
    config, catalog, writer, _ = _store(tmp_path)
    body = b"retry-me"
    meta = _meta(acquisition_id="acq_stable")

    class Boom(SqliteRawObjectCatalog):
        def register_publication(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("down")

    w = RawObjectWriter(config, Boom(tmp_path / "control.db"), chunk_size=8)
    with pytest.raises(RecoverableCatalogRegistrationError) as ei:
        w.write_stream([body], meta)
    err = ei.value
    assert err.acquisition_id == "acq_stable"
    assert Path(err.storage_path).exists()

    healthy = RawObjectWriter(config, catalog, chunk_size=8)
    c1, a1 = healthy.retry_catalog_registration(
        acquisition_id="acq_stable",
        sha256=err.sha256,
        byte_size=err.byte_size,
        metadata=meta,
        checksum_verification=ChecksumVerification.ABSENT,
    )
    assert c1 is True and a1 is True
    c2, a2 = healthy.retry_catalog_registration(
        acquisition_id="acq_stable",
        sha256=err.sha256,
        byte_size=err.byte_size,
        metadata=meta,
        checksum_verification=ChecksumVerification.ABSENT,
    )
    assert c2 is False and a2 is False
    assert catalog.get_acquisition("acq_stable")["status"] == "SUCCEEDED"


def test_new_acquisition_of_existing_bytes(tmp_path: Path) -> None:
    _, catalog, writer, _ = _store(tmp_path)
    body = b"again"
    writer.write_stream([body], _meta(acquisition_id="acq_old"))
    r = writer.write_stream([body], _meta(acquisition_id="acq_new"))
    assert isinstance(r, IdempotentDuplicateResult)
    assert r.content_already_present is True
    assert r.acquisition_id == "acq_new"
    assert len(catalog.list_acquisitions_for_object(r.raw_object_id)) == 2


def test_failed_acquisition_no_raw_object(tmp_path: Path) -> None:
    _, catalog, writer, db = _store(tmp_path)
    rec = writer.record_failed_acquisition(
        _meta(acquisition_id="acq_fail"),
        "timeout",
    )
    assert rec.acquisition_id == "acq_fail"
    row = catalog.get_acquisition("acq_fail")
    assert row is not None
    assert row["status"] == "FAILED"
    assert row["raw_object_id"] is None
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM raw_object").fetchone()[0]
    assert n == 0


def test_unsupported_and_malformed_checksums(tmp_path: Path) -> None:
    _, _, writer, _ = _store(tmp_path)
    with pytest.raises(ChecksumError, match="unsupported"):
        writer.write_stream(
            [b"x"],
            _meta(provider_checksum=ProviderChecksum(algorithm="md5", value="ab" * 16)),
        )
    with pytest.raises(ChecksumError, match="malformed"):
        writer.write_stream(
            [b"x"],
            _meta(provider_checksum=ProviderChecksum(algorithm="sha256", value="not-hex")),
        )


def test_refuse_verified_without_checksum_success(tmp_path: Path) -> None:
    _, _, writer, _ = _store(tmp_path)
    with pytest.raises(ChecksumError, match="VERIFIED"):
        writer.write_stream(
            [b"abc"],
            _meta(content_status="VERIFIED"),
        )
    # With matching checksum, VERIFIED is allowed
    body = b"abc"
    digest = hashlib.sha256(body).hexdigest()
    r = writer.write_stream(
        [body],
        _meta(
            content_status="VERIFIED",
            provider_checksum=ProviderChecksum(algorithm="sha256", value=digest),
            acquisition_id="acq_ver",
        ),
    )
    assert r.checksum_verification is ChecksumVerification.VERIFIED


def test_absolute_and_traversal_config_rejected(tmp_path: Path) -> None:
    with pytest.raises(PathSafetyError):
        RawObjectStoreConfig(root=tmp_path, object_prefix="/abs/raw")
    with pytest.raises(PathSafetyError):
        RawObjectStoreConfig(root=tmp_path, temp_dirname="/tmp/out")
    with pytest.raises(PathSafetyError):
        RawObjectStoreConfig(root=tmp_path, object_prefix="raw/../escape")
    with pytest.raises(PathSafetyError):
        RawObjectStoreConfig(root=tmp_path, temp_dirname="tmp/./x")


def test_symlink_parent_and_final_rejected(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    # symlink as object parent -> rejected at config validation time (safe-path check)
    real = tmp_path / "elsewhere"
    real.mkdir()
    link = store / "raw"
    link.symlink_to(real)
    with pytest.raises(PathSafetyError):
        RawObjectStoreConfig(root=store, object_prefix="raw/sha256")

    # destination symlink -> rejected at write time (CorruptDestinationError)
    store2 = tmp_path / "store2"
    store2.mkdir()
    config = RawObjectStoreConfig(root=store2, object_prefix="raw/sha256")
    db = tmp_path / "c.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    cat = SqliteRawObjectCatalog(db)
    writer = RawObjectWriter(config, cat, chunk_size=8)
    body = b"sym-target"
    digest = hashlib.sha256(body).hexdigest()
    final = store2 / content_addressed_relative_path(digest)
    final.parent.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "blob"
    target.write_bytes(body)
    if final.exists():
        final.unlink()
    final.symlink_to(target)
    with pytest.raises(PathSafetyError):
        writer.write_stream([body], _meta())


def test_publication_no_empty_final_on_link_failure(tmp_path: Path) -> None:
    config, _, writer, _ = _store(tmp_path)
    body = b"no-empty"
    digest = hashlib.sha256(body).hexdigest()
    final = config.root / content_addressed_relative_path(digest)

    def boom_link(tmp: Path, dest: Path) -> bool:
        raise PublicationError("hardlink unsupported", context={})

    with mock.patch(
        "cryptofactors.ingest.raw.writer._publish_exclusive_link",
        side_effect=boom_link,
    ):
        with pytest.raises(PublicationError):
            writer.write_stream([body], _meta())
    assert not final.exists()


def test_concurrent_no_clobber(tmp_path: Path) -> None:
    config, _, _, db = _store(tmp_path)
    body = b"concurrent-payload-zzzzzzzz"
    barrier = threading.Barrier(4)
    results: list[object] = []
    errors: list[BaseException] = []

    def worker() -> None:
        cat = SqliteRawObjectCatalog(db)
        w = RawObjectWriter(config, cat, chunk_size=16)
        barrier.wait()
        try:
            results.append(
                w.write_stream(
                    [body],
                    _meta(acquisition_id=f"acq_{threading.get_ident()}"),
                )
            )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            cat.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(worker) for _ in range(4)]
        for f in futs:
            f.result()
    assert not errors
    digests = {getattr(r, "sha256") for r in results}
    assert digests == {hashlib.sha256(body).hexdigest()}
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM raw_object").fetchone()[0]
    assert n == 1
    n_acq = sqlite3.connect(db).execute("SELECT COUNT(*) FROM raw_acquisition").fetchone()[0]
    assert n_acq == 4


def test_active_old_temp_preserved(tmp_path: Path) -> None:
    config, _, _, _ = _store(tmp_path)
    temp = config.temp_dir() / ".partial-active.part"
    temp.write_bytes(b"locked")
    old = time.time() - 10_000
    os.utime(temp, (old, old))
    fd = os.open(str(temp), os.O_RDONLY)
    try:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX)
        report = reconcile_orphan_temps(config, min_age_seconds=60.0, dry_run=False)
        assert temp.exists()
        assert report.active_locked >= 1
        assert any(c.reason == "active_writer_lease_preserved" for c in report.candidates)
    finally:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def test_stale_unlocked_cleanup_and_accepted_preserved(tmp_path: Path) -> None:
    config, _, writer, _ = _store(tmp_path)
    pub = writer.write_stream([b"keep"], _meta())
    stale = config.temp_dir() / ".partial-stale.part"
    recent = config.temp_dir() / ".partial-recent.part"
    other = config.temp_dir() / "notes.txt"
    stale.write_bytes(b"s")
    recent.write_bytes(b"r")
    other.write_bytes(b"o")
    os.utime(stale, (time.time() - 9999, time.time() - 9999))
    dry = reconcile_orphan_temps(config, min_age_seconds=60.0, dry_run=True)
    assert dry.removed == 0
    assert stale.exists()
    live = reconcile_orphan_temps(config, min_age_seconds=60.0, dry_run=False)
    assert live.removed >= 1
    assert not stale.exists()
    assert recent.exists()
    assert other.exists()
    assert pub.storage_path.exists()


def test_catalog_rejects_bad_receipts(tmp_path: Path) -> None:
    config, catalog, _, _ = _store(tmp_path)
    root = config.root.resolve()
    good_body = b"ok-bytes"
    digest = hashlib.sha256(good_body).hexdigest()
    path = root / content_addressed_relative_path(digest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(good_body)

    def receipt(**over: object) -> PublicationReceipt:
        base = dict(
            raw_object_id=f"raw_{digest}",
            sha256=digest,
            byte_size=len(good_body),
            storage_path=path,
            storage_uri=content_addressed_relative_path(digest).as_posix(),
            reused_existing=False,
            verified_regular_file=True,
            verified_size=True,
            verified_sha256=True,
        )
        base.update(over)
        return PublicationReceipt(**base)  # type: ignore[arg-type]

    # missing
    missing_path = root / "raw" / "sha256" / "00" / "00" / ("0" * 64)
    missing = receipt(storage_path=missing_path)
    with pytest.raises(CatalogRegistrationError, match="missing"):
        verify_publication_receipt(missing, store_root=root)

    # wrong size flag still re-checked on disk — write partial content under real path
    path.write_bytes(b"short")
    with pytest.raises(CatalogRegistrationError, match="size"):
        verify_publication_receipt(receipt(byte_size=len(good_body)), store_root=root)

    path.write_bytes(good_body)
    # wrong hash on disk
    path.write_bytes(b"different-content!!!!")
    with pytest.raises(CatalogRegistrationError, match="SHA-256"):
        verify_publication_receipt(receipt(byte_size=path.stat().st_size), store_root=root)

    # symlink destination -> resolved path escapes store root -> rejected
    path.unlink()
    target = tmp_path / "t.bin"
    target.write_bytes(good_body)
    path.symlink_to(target)
    with pytest.raises(CatalogRegistrationError, match="symlink|escape"):
        verify_publication_receipt(
            receipt(byte_size=len(good_body), storage_path=path),
            store_root=root,
        )


def test_invalid_chunk_and_interrupted(tmp_path: Path) -> None:
    _, _, writer, _ = _store(tmp_path)
    with pytest.raises(InvalidChunkError):
        writer.write_stream(["nope"], _meta())  # type: ignore[list-item]

    def gen():
        yield b"a"
        raise RuntimeError("drop")

    with pytest.raises(InterruptedWriteError):
        writer.write_stream(gen(), _meta())


def test_expected_content_sha256_mismatch(tmp_path: Path) -> None:
    _, _, writer, _ = _store(tmp_path)
    with pytest.raises(HashMismatchError):
        writer.write_stream([b"x"], _meta(), expected_content_sha256="0" * 64)


def test_publish_exclusive_link_no_clobber(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.write_bytes(b"one")
    b.write_bytes(b"two")
    assert _publish_exclusive_link(a, b) is False
    assert b.read_bytes() == b"two"
