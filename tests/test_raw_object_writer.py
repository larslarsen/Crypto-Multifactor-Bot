"""Focused synthetic tests for RAW-001 content-addressed raw object writer.

These tests are intended to be executed by the Junior Developer / CI — not by the
senior implementation agent.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations
from cryptofactors.ingest.raw import (
    AcquisitionMetadata,
    CorruptDestinationError,
    HashMismatchError,
    IdempotentDuplicateResult,
    InterruptedWriteError,
    InvalidChunkError,
    PublishResult,
    RawObjectStoreConfig,
    RawObjectWriter,
    RecoverableCatalogRegistrationError,
    SqliteRawObjectCatalog,
    content_addressed_relative_path,
    reconcile_orphan_temps,
)


UTC = timezone.utc


def _meta(source_id: str = "src_test", **kwargs: object) -> AcquisitionMetadata:
    base = {
        "source_id": source_id,
        "request": {"url": "https://example.test/obj"},
        "response_metadata": {"status": 200},
        "acquired_at": datetime(2025, 1, 1, tzinfo=UTC),
    }
    base.update(kwargs)
    return AcquisitionMetadata(**base)  # type: ignore[arg-type]


def _store(tmp_path: Path) -> tuple[RawObjectStoreConfig, SqliteRawObjectCatalog, RawObjectWriter]:
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    root = tmp_path / "store"
    config = RawObjectStoreConfig(root=root)
    catalog = SqliteRawObjectCatalog(db)
    writer = RawObjectWriter(config, catalog, chunk_size=8)
    return config, catalog, writer


def test_empty_object(tmp_path: Path) -> None:
    config, catalog, writer = _store(tmp_path)
    result = writer.write_stream([b""], _meta())
    # empty iterable yields no chunks → empty object
    assert isinstance(result, PublishResult)
    assert result.byte_size == 0
    assert result.sha256 == hashlib.sha256(b"").hexdigest()
    assert result.storage_path.exists()
    assert result.storage_path.read_bytes() == b""
    assert result.catalog_registered is True
    row = catalog.get_accepted_by_sha256(result.sha256)
    assert row is not None
    assert int(row["byte_size"]) == 0


def test_single_and_multi_chunk_exact_hash_and_path(tmp_path: Path) -> None:
    _, _, writer = _store(tmp_path)
    body = b"abcdefghijKLMNOP"
    # multi-chunk via small chunk_size on writer
    result = writer.write_stream([body[:4], body[4:10], body[10:]], _meta())
    assert result.sha256 == hashlib.sha256(body).hexdigest()
    assert result.byte_size == len(body)
    rel = content_addressed_relative_path(result.sha256)
    assert result.storage_uri == rel.as_posix()
    assert result.storage_path.read_bytes() == body
    # deterministic layout raw/sha256/ab/cd/<full>
    parts = Path(result.storage_uri).parts
    assert parts[0] == "raw" and parts[1] == "sha256"
    assert parts[2] == result.sha256[:2]
    assert parts[3] == result.sha256[2:4]
    assert parts[4] == result.sha256


def test_identical_duplicate_ingestion(tmp_path: Path) -> None:
    _, catalog, writer = _store(tmp_path)
    body = b"same-bytes"
    first = writer.write_stream([body], _meta())
    second = writer.write_stream([body], _meta())
    assert isinstance(second, IdempotentDuplicateResult)
    assert second.sha256 == first.sha256
    assert second.storage_path == first.storage_path
    assert second.catalog_registered is True
    # single catalog row
    conn = sqlite3.connect(tmp_path / "control.db")
    n = conn.execute("SELECT COUNT(*) FROM raw_object").fetchone()[0]
    conn.close()
    assert n == 1
    assert catalog.get_accepted_by_sha256(first.sha256) is not None


def test_interrupted_input_stream(tmp_path: Path) -> None:
    config, catalog, writer = _store(tmp_path)

    def gen():
        yield b"abc"
        raise RuntimeError("network drop")

    with pytest.raises(InterruptedWriteError):
        writer.write_stream(gen(), _meta())
    # no accepted object
    assert list((config.root / "raw").rglob("*")) == [] if (config.root / "raw").exists() else True
    assert catalog.get_accepted_by_sha256(hashlib.sha256(b"abc").hexdigest()) is None
    # temps cleaned
    assert list(config.temp_dir().glob(".partial-*")) == []


def test_invalid_non_byte_chunks(tmp_path: Path) -> None:
    _, _, writer = _store(tmp_path)
    with pytest.raises(InvalidChunkError):
        writer.write_stream(["not-bytes"], _meta())  # type: ignore[list-item]


def test_temp_file_cleanup_on_success(tmp_path: Path) -> None:
    config, _, writer = _store(tmp_path)
    writer.write_stream([b"payload"], _meta())
    assert list(config.temp_dir().glob(".partial-*")) == []
    assert list(config.temp_dir().glob("*.part")) == []


def test_preexisting_corrupt_destination(tmp_path: Path) -> None:
    config, _, writer = _store(tmp_path)
    body = b"legitimate-content"
    digest = hashlib.sha256(body).hexdigest()
    final = config.root / content_addressed_relative_path(digest)
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(b"CORRUPT-NOT-MATCHING!!!!!!")
    with pytest.raises(CorruptDestinationError):
        writer.write_stream([body], _meta())
    # corrupt bytes preserved (never overwritten)
    assert final.read_bytes() == b"CORRUPT-NOT-MATCHING!!!!!!"


def test_hash_mismatch_expected_sha256(tmp_path: Path) -> None:
    config, _, writer = _store(tmp_path)
    with pytest.raises(HashMismatchError):
        writer.write_stream([b"abc"], _meta(), expected_sha256="0" * 64)
    assert list(config.temp_dir().glob(".partial-*")) == []


def test_retry_after_failure_then_success(tmp_path: Path) -> None:
    _, catalog, writer = _store(tmp_path)

    def bad():
        yield b"x"
        raise RuntimeError("fail")

    with pytest.raises(InterruptedWriteError):
        writer.write_stream(bad(), _meta())
    body = b"recovered"
    result = writer.write_stream([body], _meta())
    assert result.sha256 == hashlib.sha256(body).hexdigest()
    assert catalog.get_accepted_by_sha256(result.sha256) is not None


def test_concurrent_duplicate_writers(tmp_path: Path) -> None:
    config, catalog, _ = _store(tmp_path)
    body = b"concurrent-identical-payload-zzzz"
    barrier = threading.Barrier(4)
    results: list[object] = []
    errors: list[BaseException] = []

    def worker() -> None:
        # each worker needs its own catalog connection (sqlite)
        cat = SqliteRawObjectCatalog(tmp_path / "control.db")
        w = RawObjectWriter(config, cat, chunk_size=16)
        barrier.wait()
        try:
            results.append(w.write_stream([body], _meta()))
        except BaseException as exc:  # noqa: BLE001 — collect for assertion
            errors.append(exc)
        finally:
            cat.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(worker) for _ in range(4)]
        for f in futs:
            f.result()
    assert not errors
    assert len(results) == 4
    digests = {getattr(r, "sha256") for r in results}
    assert digests == {hashlib.sha256(body).hexdigest()}
    paths = {getattr(r, "storage_path") for r in results}
    assert len(paths) == 1
    only = next(iter(paths))
    assert only.read_bytes() == body
    conn = sqlite3.connect(tmp_path / "control.db")
    n = conn.execute("SELECT COUNT(*) FROM raw_object").fetchone()[0]
    conn.close()
    assert n == 1


def test_catalog_failure_after_publication_recoverable(tmp_path: Path) -> None:
    config, _, writer = _store(tmp_path)
    body = b"published-but-catalog-fails"

    class BoomCatalog(SqliteRawObjectCatalog):
        def register_accepted(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("catalog down")

    boom = BoomCatalog(tmp_path / "control.db")
    w = RawObjectWriter(config, boom, chunk_size=8)
    with pytest.raises(RecoverableCatalogRegistrationError) as ei:
        w.write_stream([body], _meta())
    err = ei.value
    assert Path(err.storage_path).exists()
    assert Path(err.storage_path).read_bytes() == body
    assert err.sha256 == hashlib.sha256(body).hexdigest()
    # not registered
    good = SqliteRawObjectCatalog(tmp_path / "control.db")
    assert good.get_accepted_by_sha256(err.sha256) is None


def test_idempotent_catalog_retry(tmp_path: Path) -> None:
    config, catalog, writer = _store(tmp_path)
    body = b"retry-reg"
    # Publish without catalog by using boom then retry
    class BoomCatalog(SqliteRawObjectCatalog):
        def register_accepted(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("down")

    w = RawObjectWriter(config, BoomCatalog(tmp_path / "control.db"), chunk_size=8)
    with pytest.raises(RecoverableCatalogRegistrationError) as ei:
        w.write_stream([body], _meta())
    err = ei.value
    # retry with healthy catalog
    healthy = RawObjectWriter(config, catalog, chunk_size=8)
    inserted = healthy.retry_catalog_registration(
        sha256=err.sha256,
        byte_size=err.byte_size,
        metadata=_meta(),
    )
    assert inserted is True
    # second retry idempotent
    inserted2 = healthy.retry_catalog_registration(
        sha256=err.sha256,
        byte_size=err.byte_size,
        metadata=_meta(),
    )
    assert inserted2 is False
    assert catalog.get_accepted_by_sha256(err.sha256) is not None


def test_failed_acquisition_record_no_raw_object(tmp_path: Path) -> None:
    _, catalog, writer = _store(tmp_path)
    rec = writer.record_failed_acquisition(
        source_id="src_test",
        error_message="timeout",
        request={"url": "https://example.test/x"},
    )
    assert rec.status == "FAILED"
    conn = sqlite3.connect(tmp_path / "control.db")
    n_raw = conn.execute("SELECT COUNT(*) FROM raw_object").fetchone()[0]
    n_run = conn.execute(
        "SELECT COUNT(*) FROM build_run WHERE status = 'FAILED'"
    ).fetchone()[0]
    conn.close()
    assert n_raw == 0
    assert n_run == 1
    assert catalog.get_accepted_by_sha256("0" * 64) is None


def test_orphan_reconciliation_dry_run_and_stale_cleanup(tmp_path: Path) -> None:
    config, _, writer = _store(tmp_path)
    # accepted object must never be touched
    body = b"keep-me"
    pub = writer.write_stream([body], _meta())
    accepted = pub.storage_path

    temp_dir = config.temp_dir()
    stale = temp_dir / ".partial-stale.part"
    recent = temp_dir / ".partial-recent.part"
    other = temp_dir / "not-a-partial.bin"
    stale.write_bytes(b"stale")
    recent.write_bytes(b"recent")
    other.write_bytes(b"other")
    # backdate stale
    old = time.time() - 10_000
    os.utime(stale, (old, old))

    report = reconcile_orphan_temps(config, min_age_seconds=60.0, dry_run=True)
    assert report.dry_run is True
    assert report.stale_candidates >= 1
    assert report.removed == 0
    assert stale.exists()
    assert recent.exists()
    assert accepted.exists()

    report2 = reconcile_orphan_temps(config, min_age_seconds=60.0, dry_run=False)
    assert report2.removed >= 1
    assert not stale.exists()
    assert recent.exists()  # recent preserved
    assert other.exists()  # non-matching preserved
    assert accepted.exists()
    assert accepted.read_bytes() == body


def test_binary_io_stream(tmp_path: Path) -> None:
    _, _, writer = _store(tmp_path)
    path = tmp_path / "input.bin"
    data = b"from-file-handle"
    path.write_bytes(data)
    with path.open("rb") as fh:
        result = writer.write_stream(fh, _meta())
    assert result.byte_size == len(data)
    assert result.storage_path.read_bytes() == data
