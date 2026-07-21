"""Focused RAW-001 integrity regression tests. Junior executes these."""

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
    AcquisitionConflictError,
    AcquisitionMetadata,
    CatalogRegistrationError,
    ChecksumError,
    ChecksumVerification,
    DurabilityError,
    HashMismatchError,
    InterruptedWriteError,
    PathSafetyError,
    ProviderChecksum,
    PublicationError,
    PublicationReceipt,
    PublishResult,
    RawObjectStoreConfig,
    RawObjectWriter,
    RawStoreError,
    SqliteRawObjectCatalog,
    content_addressed_relative_path,
    reconcile_orphan_temps,
    verify_publication_receipt,
)
from cryptofactors.ingest.raw.paths import canonical_identity
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


def _store(
    tmp_path: Path,
) -> tuple[RawObjectStoreConfig, SqliteRawObjectCatalog, RawObjectWriter, Path]:
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    root = tmp_path / "store"
    config = RawObjectStoreConfig(root=root)
    catalog = SqliteRawObjectCatalog(db)
    writer = RawObjectWriter(config, catalog, chunk_size=8)
    return config, catalog, writer, db


def test_canonical_receipt_accepted(tmp_path: Path) -> None:
    config, catalog, writer, _ = _store(tmp_path)
    body = b"canonical-ok"
    r = writer.write_stream([body], _meta(acquisition_id="acq_c"))
    assert isinstance(r, PublishResult)
    digest, oid, path, uri = canonical_identity(
        root=config.root.resolve(),
        object_prefix=config.object_prefix,
        sha256_hex=r.sha256,
    )
    assert r.raw_object_id == oid
    assert r.storage_uri == uri
    assert r.storage_path.resolve() == path
    assert path.read_bytes() == body
    receipt = PublicationReceipt(
        raw_object_id=oid,
        sha256=digest,
        byte_size=len(body),
        storage_path=path,
        storage_uri=uri,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    verify_publication_receipt(
        receipt,
        store_root=config.root.resolve(),
        object_prefix=config.object_prefix,
    )


def test_arbitrary_under_root_path_rejected(tmp_path: Path) -> None:
    config, catalog, writer, _ = _store(tmp_path)
    body = b"bytes-here"
    digest = hashlib.sha256(body).hexdigest()
    # Correct bytes at non-canonical location under root
    rogue = config.root / "somewhere" / "else.bin"
    rogue.parent.mkdir(parents=True, exist_ok=True)
    rogue.write_bytes(body)
    oid = f"raw_{digest}"
    uri = content_addressed_relative_path(digest).as_posix()
    receipt = PublicationReceipt(
        raw_object_id=oid,
        sha256=digest,
        byte_size=len(body),
        storage_path=rogue,
        storage_uri=uri,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with pytest.raises(CatalogRegistrationError, match="canonical content path"):
        verify_publication_receipt(
            receipt,
            store_root=config.root.resolve(),
            object_prefix=config.object_prefix,
        )


def test_mismatched_raw_object_id_rejected(tmp_path: Path) -> None:
    config, _, writer, _ = _store(tmp_path)
    body = b"id-mismatch"
    r = writer.write_stream([body], _meta())
    receipt = PublicationReceipt(
        raw_object_id="raw_" + ("a" * 64),
        sha256=r.sha256,
        byte_size=r.byte_size,
        storage_path=r.storage_path,
        storage_uri=r.storage_uri,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with pytest.raises(CatalogRegistrationError, match="raw_object_id"):
        verify_publication_receipt(
            receipt,
            store_root=config.root.resolve(),
            object_prefix=config.object_prefix,
        )


def test_mismatched_storage_uri_rejected(tmp_path: Path) -> None:
    config, _, writer, _ = _store(tmp_path)
    body = b"uri-mismatch"
    r = writer.write_stream([body], _meta())
    receipt = PublicationReceipt(
        raw_object_id=r.raw_object_id,
        sha256=r.sha256,
        byte_size=r.byte_size,
        storage_path=r.storage_path,
        storage_uri="raw/sha256/ff/ff/" + r.sha256,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with pytest.raises(CatalogRegistrationError, match="storage_uri"):
        verify_publication_receipt(
            receipt,
            store_root=config.root.resolve(),
            object_prefix=config.object_prefix,
        )


def test_symlinked_parent_components_rejected(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    real = tmp_path / "real_objects"
    real.mkdir()
    # object_prefix first component is a symlink
    (store / "raw").symlink_to(real)
    # Corrected behavior: symlinked storage-parent is rejected at config validation.
    with pytest.raises(PathSafetyError):
        RawObjectStoreConfig(root=store, object_prefix="raw/sha256")


def test_identical_acquisition_retry_accepted(tmp_path: Path) -> None:
    config, catalog, writer, _ = _store(tmp_path)
    body = b"retry-same"
    meta = _meta(acquisition_id="acq_same")
    r1 = writer.write_stream([body], meta)
    c2, a2 = writer.retry_catalog_registration(
        acquisition_id="acq_same",
        sha256=r1.sha256,
        byte_size=r1.byte_size,
        metadata=meta,
        checksum_verification=ChecksumVerification.ABSENT,
    )
    assert c2 is False and a2 is False


def test_same_acquisition_id_other_source_rejected(tmp_path: Path) -> None:
    _, catalog, writer, _ = _store(tmp_path)
    body = b"conflict-src"
    writer.write_stream([body], _meta(source_id="src_a", acquisition_id="acq_c"))
    with pytest.raises(AcquisitionConflictError):
        writer.write_stream(
            [body],
            _meta(source_id="src_b", acquisition_id="acq_c"),
        )


def test_same_acquisition_id_different_request_rejected(tmp_path: Path) -> None:
    _, _, writer, _ = _store(tmp_path)
    body = b"conflict-req"
    writer.write_stream(
        [body],
        _meta(acquisition_id="acq_r", request={"url": "https://a.example/x"}),
    )
    with pytest.raises(AcquisitionConflictError):
        writer.write_stream(
            [body],
            _meta(acquisition_id="acq_r", request={"url": "https://b.example/y"}),
        )


def test_interrupted_write_records_failed(tmp_path: Path) -> None:
    _, catalog, writer, db = _store(tmp_path)

    def gen():
        yield b"partial"
        raise RuntimeError("drop")

    with pytest.raises(InterruptedWriteError):
        writer.write_stream(gen(), _meta(acquisition_id="acq_fail_int"))
    row = catalog.get_acquisition("acq_fail_int")
    assert row is not None
    assert row["status"] == "FAILED"
    assert row["raw_object_id"] is None
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM raw_object").fetchone()[0]
    assert n == 0


def test_checksum_and_hash_failures_record_failed(tmp_path: Path) -> None:
    _, catalog, writer, _ = _store(tmp_path)
    with pytest.raises(HashMismatchError):
        writer.write_stream(
            [b"x"],
            _meta(acquisition_id="acq_exp"),
            expected_content_sha256="0" * 64,
        )
    assert catalog.get_acquisition("acq_exp")["status"] == "FAILED"

    with pytest.raises(ChecksumError):
        writer.write_stream(
            [b"y"],
            _meta(
                acquisition_id="acq_bad_algo",
                provider_checksum=ProviderChecksum(algorithm="md5", value="ab" * 16),
            ),
        )
    assert catalog.get_acquisition("acq_bad_algo")["status"] == "FAILED"

    body = b"z"
    digest = hashlib.sha256(body).hexdigest()
    wrong = "1" * 64
    with pytest.raises(HashMismatchError):
        writer.write_stream(
            [body],
            _meta(
                acquisition_id="acq_mis",
                provider_checksum=ProviderChecksum(algorithm="sha256", value=wrong),
            ),
        )
    assert catalog.get_acquisition("acq_mis")["status"] == "FAILED"
    assert digest != wrong


def test_failed_record_retry_idempotent(tmp_path: Path) -> None:
    _, catalog, writer, _ = _store(tmp_path)
    meta = _meta(acquisition_id="acq_fail_id")
    r1 = writer.record_failed_acquisition(meta, "timeout")
    r2 = writer.record_failed_acquisition(meta, "timeout")
    assert r1.acquisition_id == r2.acquisition_id == "acq_fail_id"
    n = sqlite3.connect(tmp_path / "control.db").execute(
        "SELECT COUNT(*) FROM raw_acquisition WHERE acquisition_id = 'acq_fail_id'"
    ).fetchone()[0]
    assert n == 1


def test_original_exception_survives_recording_error(tmp_path: Path) -> None:
    config, _, _, db = _store(tmp_path)

    class BoomFailCatalog(SqliteRawObjectCatalog):
        def record_failed_acquisition(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("ledger unavailable")

    w = RawObjectWriter(config, BoomFailCatalog(db), chunk_size=8)

    def gen():
        yield b"a"
        raise RuntimeError("stream-broke")

    with pytest.raises(InterruptedWriteError) as ei:
        w.write_stream(gen(), _meta(acquisition_id="acq_mask"))
    # Original engineering failure preserved (not replaced by ledger error alone).
    assert "stream-broke" in str(ei.value) or "stream-broke" in str(ei.value.__cause__)


def test_active_lease_held_through_publication(tmp_path: Path) -> None:
    """Lease fd remains locked continuously until write completes."""
    config, catalog, writer, _ = _store(tmp_path)
    body = b"lease-hold"
    observed_locked = {"during": False}

    real_link = _publish_exclusive_link

    def link_and_probe(tmp: Path, final: Path) -> bool:
        import fcntl

        # tmp should still be exclusively locked by the writer while we publish.
        fd = os.open(str(tmp), os.O_RDONLY)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                observed_locked["during"] = False  # acquired → not locked
            except OSError:
                observed_locked["during"] = True
        finally:
            os.close(fd)
        return real_link(tmp, final)

    with mock.patch(
        "cryptofactors.ingest.raw.writer._publish_exclusive_link",
        side_effect=link_and_probe,
    ):
        writer.write_stream([body], _meta())
    assert observed_locked["during"] is True


def test_reconcile_cannot_delete_old_active_writer(tmp_path: Path) -> None:
    config, _, _, _ = _store(tmp_path)
    temp = config.temp_dir() / ".partial-old-active.part"
    temp.write_bytes(b"active")
    os.utime(temp, (time.time() - 99_000, time.time() - 99_000))
    import fcntl

    fd = os.open(str(temp), os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        report = reconcile_orphan_temps(config, min_age_seconds=10.0, dry_run=False)
        assert temp.exists()
        assert report.active_locked >= 1
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def test_destructive_reconcile_fails_without_lock_support(tmp_path: Path) -> None:
    config, _, _, _ = _store(tmp_path)
    stale = config.temp_dir() / ".partial-stale.part"
    stale.write_bytes(b"x")
    os.utime(stale, (time.time() - 99_000, time.time() - 99_000))
    with mock.patch("cryptofactors.ingest.raw.reconcile.fcntl", None):
        with pytest.raises(RawStoreError, match="lock primitive"):
            reconcile_orphan_temps(config, min_age_seconds=10.0, dry_run=False)
    assert stale.exists()


def test_directory_fsync_failure_surfaced(tmp_path: Path) -> None:
    config, catalog, writer, _ = _store(tmp_path)
    body = b"fsync-dir-fail"

    def boom_fsync_dir(path: Path) -> None:
        raise DurabilityError("directory fsync failed", context={"path": str(path)})

    with mock.patch(
        "cryptofactors.ingest.raw.writer.fsync_dir",
        side_effect=boom_fsync_dir,
    ):
        with pytest.raises(DurabilityError, match="fsync"):
            writer.write_stream([body], _meta(acquisition_id="acq_fsync"))
    # Link may succeed before parent fsync; object preserved and not FAILED.
    acq = catalog.get_acquisition("acq_fsync")
    assert acq is None or acq["status"] != "FAILED"
    digest = hashlib.sha256(body).hexdigest()
    final = config.root / content_addressed_relative_path(digest)
    if final.exists():
        assert final.read_bytes() == body


def test_multi_acquisition_and_sources(tmp_path: Path) -> None:
    _, catalog, writer, db = _store(tmp_path)
    body = b"shared"
    writer.write_stream([body], _meta(source_id="s1", acquisition_id="a1"))
    writer.write_stream([body], _meta(source_id="s2", acquisition_id="a2"))
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM raw_object").fetchone()[0]
    assert n == 1
    n_a = sqlite3.connect(db).execute("SELECT COUNT(*) FROM raw_acquisition").fetchone()[0]
    assert n_a == 2


def test_publication_failure_records_failed(tmp_path: Path) -> None:
    config, catalog, writer, _ = _store(tmp_path)

    def boom_link(tmp: Path, final: Path) -> bool:
        raise PublicationError("no hardlink", context={})

    with mock.patch(
        "cryptofactors.ingest.raw.writer._publish_exclusive_link",
        side_effect=boom_link,
    ):
        with pytest.raises(PublicationError):
            writer.write_stream([b"nope"], _meta(acquisition_id="acq_pubfail"))
    row = catalog.get_acquisition("acq_pubfail")
    assert row is not None and row["status"] == "FAILED" and row["raw_object_id"] is None


def test_concurrent_no_clobber(tmp_path: Path) -> None:
    config, _, _, db = _store(tmp_path)
    body = b"concurrent-zzzz"
    barrier = threading.Barrier(3)
    results: list[object] = []
    errors: list[BaseException] = []

    def worker(i: int) -> None:
        cat = SqliteRawObjectCatalog(db)
        w = RawObjectWriter(config, cat, chunk_size=16)
        barrier.wait()
        try:
            results.append(
                w.write_stream([body], _meta(acquisition_id=f"acq_c_{i}"))
            )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            cat.close()

    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = [pool.submit(worker, i) for i in range(3)]
        for f in futs:
            f.result()
    assert not errors
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM raw_object").fetchone()[0]
    assert n == 1


def test_final_path_symlink_rejected_no_hash(tmp_path: Path) -> None:
    """Canonical final path replaced by symlink to exact-matching outside-root file.

    Proves rejection before _sha256_file is invoked.
    """
    config, _, writer, _ = _store(tmp_path)
    body = b"sym-final"
    r = writer.write_stream([body], _meta(acquisition_id="acq_fs"))
    assert isinstance(r, PublishResult)

    outside = tmp_path / "outside_final"
    outside.write_bytes(body)
    r.storage_path.unlink()
    r.storage_path.symlink_to(outside)

    receipt = PublicationReceipt(
        raw_object_id=r.raw_object_id,
        sha256=r.sha256,
        byte_size=r.byte_size,
        storage_path=r.storage_path,
        storage_uri=r.storage_uri,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with mock.patch("cryptofactors.ingest.raw.catalog._sha256_file") as m:
        with pytest.raises(CatalogRegistrationError):
            verify_publication_receipt(
                receipt,
                store_root=config.root.resolve(),
                object_prefix=config.object_prefix,
            )
        m.assert_not_called()


def test_parent_symlink_rejected_no_hash(tmp_path: Path) -> None:
    """Parent component replaced by symlink to outside-root target with complete fanout.

    Proves rejection before _sha256_file is invoked.
    """
    import shutil

    config, _, writer, _ = _store(tmp_path)
    body = b"sym-parent"
    r = writer.write_stream([body], _meta(acquisition_id="acq_ps"))
    assert isinstance(r, PublishResult)

    cd_dir = r.storage_path.parent  # cd/
    cd_hash = r.storage_path.name

    outside = tmp_path / "outside_parent"
    outside.mkdir()
    (outside / cd_hash).write_bytes(body)

    shutil.rmtree(cd_dir)
    cd_dir.symlink_to(outside)

    receipt = PublicationReceipt(
        raw_object_id=r.raw_object_id,
        sha256=r.sha256,
        byte_size=r.byte_size,
        storage_path=r.storage_path,
        storage_uri=r.storage_uri,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with mock.patch("cryptofactors.ingest.raw.catalog._sha256_file") as m:
        with pytest.raises(CatalogRegistrationError):
            verify_publication_receipt(
                receipt,
                store_root=config.root.resolve(),
                object_prefix=config.object_prefix,
            )
        m.assert_not_called()


def test_traversal_alias_receipt_path_rejected(tmp_path: Path) -> None:
    """Receipt path with '..' that normalizes to canonical path is still rejected."""
    config, _, writer, _ = _store(tmp_path)
    body = b"trav-alias"
    r = writer.write_stream([body], _meta(acquisition_id="acq_ta"))
    assert isinstance(r, PublishResult)

    digest = r.sha256
    rel = content_addressed_relative_path(digest)
    prefix_parts = rel.parts[:2]
    fanout = rel.parts[2:]
    traversal_rel = Path(*prefix_parts) / ".." / Path(*prefix_parts[1:]) / Path(*fanout)
    traversal_path = config.root.resolve() / traversal_rel

    receipt = PublicationReceipt(
        raw_object_id=r.raw_object_id,
        sha256=digest,
        byte_size=r.byte_size,
        storage_path=traversal_path,
        storage_uri=r.storage_uri,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with pytest.raises(CatalogRegistrationError, match=r"\.\.|must not contain"):
        verify_publication_receipt(
            receipt,
            store_root=config.root.resolve(),
            object_prefix=config.object_prefix,
        )


def test_escaping_prefix_rejected_not_uri_mismatch(tmp_path: Path) -> None:
    """Traversal-containing prefix agreed by receipt and config; URI matches.

    Proves lexical escape rejection fires, not URI mismatch.
    """
    config, _, writer, _ = _store(tmp_path)
    body = b"esc-prefix"
    r = writer.write_stream([body], _meta(acquisition_id="acq_ep"))
    assert isinstance(r, PublishResult)

    digest = r.sha256
    bad_prefix = "../raw/sha256"
    rel = content_addressed_relative_path(digest, prefix=bad_prefix)
    bad_uri = rel.as_posix()

    receipt = PublicationReceipt(
        raw_object_id=r.raw_object_id,
        sha256=digest,
        byte_size=r.byte_size,
        storage_path=r.storage_path,
        storage_uri=bad_uri,
        object_prefix=bad_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with pytest.raises(CatalogRegistrationError, match=r"\.\.|must not contain"):
        verify_publication_receipt(
            receipt,
            store_root=config.root.resolve(),
            object_prefix=bad_prefix,
        )


def test_missing_component_lstat_rejected(tmp_path: Path) -> None:
    """Canonical receipt path retained but a filesystem component removed.

    Proves component-lstat failure (not identity comparison).
    """
    config, _, writer, _ = _store(tmp_path)
    body = b"miss-comp"
    r = writer.write_stream([body], _meta(acquisition_id="acq_mc"))
    assert isinstance(r, PublishResult)

    r.storage_path.unlink()
    r.storage_path.parent.rmdir()

    receipt = PublicationReceipt(
        raw_object_id=r.raw_object_id,
        sha256=r.sha256,
        byte_size=r.byte_size,
        storage_path=r.storage_path,
        storage_uri=r.storage_uri,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with pytest.raises(CatalogRegistrationError, match="missing|component"):
        verify_publication_receipt(
            receipt,
            store_root=config.root.resolve(),
            object_prefix=config.object_prefix,
        )


def test_digest_mismatch_after_path_validation(tmp_path: Path) -> None:
    """File mutated to same-size different bytes; SHA-256 mismatch after path checks."""
    config, _, writer, _ = _store(tmp_path)
    body = b"digest-ok"
    r = writer.write_stream([body], _meta(acquisition_id="acq_dm"))
    assert isinstance(r, PublishResult)

    r.storage_path.write_bytes(b"digest-NO")

    receipt = PublicationReceipt(
        raw_object_id=r.raw_object_id,
        sha256=r.sha256,
        byte_size=r.byte_size,
        storage_path=r.storage_path,
        storage_uri=r.storage_uri,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with pytest.raises(CatalogRegistrationError, match="SHA-256 mismatch"):
        verify_publication_receipt(
            receipt,
            store_root=config.root.resolve(),
            object_prefix=config.object_prefix,
        )


def test_non_directory_parent_rejected(tmp_path: Path) -> None:
    """Parent component replaced by a regular file."""
    import shutil

    config, _, writer, _ = _store(tmp_path)
    body = b"notdir"
    r = writer.write_stream([body], _meta(acquisition_id="acq_nd"))
    assert isinstance(r, PublishResult)

    ab_dir = r.storage_path.parent
    shutil.rmtree(ab_dir)
    ab_dir.write_bytes(b"not-a-directory")

    receipt = PublicationReceipt(
        raw_object_id=r.raw_object_id,
        sha256=r.sha256,
        byte_size=r.byte_size,
        storage_path=r.storage_path,
        storage_uri=r.storage_uri,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with pytest.raises(CatalogRegistrationError, match="not a directory"):
        verify_publication_receipt(
            receipt,
            store_root=config.root.resolve(),
            object_prefix=config.object_prefix,
        )


def test_non_regular_final_rejected(tmp_path: Path) -> None:
    """Final component replaced by a directory."""
    config, _, writer, _ = _store(tmp_path)
    body = b"notreg"
    r = writer.write_stream([body], _meta(acquisition_id="acq_nr"))
    assert isinstance(r, PublishResult)

    r.storage_path.unlink()
    r.storage_path.mkdir()

    receipt = PublicationReceipt(
        raw_object_id=r.raw_object_id,
        sha256=r.sha256,
        byte_size=r.byte_size,
        storage_path=r.storage_path,
        storage_uri=r.storage_uri,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with pytest.raises(CatalogRegistrationError, match="not a regular file"):
        verify_publication_receipt(
            receipt,
            store_root=config.root.resolve(),
            object_prefix=config.object_prefix,
        )


def test_id_uri_size_mismatches_rejected(tmp_path: Path) -> None:
    """object-ID, URI, and byte-size mismatches rejected independently."""
    config, _, writer, _ = _store(tmp_path)
    body = b"mism"
    r = writer.write_stream([body], _meta(acquisition_id="acq_m"))
    assert isinstance(r, PublishResult)

    receipt = PublicationReceipt(
        raw_object_id="raw_" + "a" * 64,
        sha256=r.sha256,
        byte_size=r.byte_size,
        storage_path=r.storage_path,
        storage_uri=r.storage_uri,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with pytest.raises(CatalogRegistrationError, match="raw_object_id"):
        verify_publication_receipt(receipt, store_root=config.root.resolve(), object_prefix=config.object_prefix)

    receipt = PublicationReceipt(
        raw_object_id=r.raw_object_id,
        sha256=r.sha256,
        byte_size=r.byte_size,
        storage_path=r.storage_path,
        storage_uri="raw/sha256/zz/zz/" + r.sha256,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with pytest.raises(CatalogRegistrationError, match="storage_uri"):
        verify_publication_receipt(receipt, store_root=config.root.resolve(), object_prefix=config.object_prefix)

    receipt = PublicationReceipt(
        raw_object_id=r.raw_object_id,
        sha256=r.sha256,
        byte_size=999,
        storage_path=r.storage_path,
        storage_uri=r.storage_uri,
        object_prefix=config.object_prefix,
        reused_existing=False,
        verified_regular_file=True,
        verified_size=True,
        verified_sha256=True,
    )
    with pytest.raises(CatalogRegistrationError, match="size mismatch"):
        verify_publication_receipt(receipt, store_root=config.root.resolve(), object_prefix=config.object_prefix)
