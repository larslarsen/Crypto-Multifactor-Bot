"""Streaming content-addressed raw object writer with acquisition provenance."""

from __future__ import annotations

import hashlib
import os
import stat as statmod
import tempfile
import uuid
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import BinaryIO, Union

from cryptofactors.ingest.raw.checksums import (
    evaluate_provider_checksum,
    raise_if_hard_fail,
    require_checksum_ok_for_verified_status,
)
from cryptofactors.ingest.raw.errors import (
    ChecksumError,
    CorruptDestinationError,
    HashMismatchError,
    InterruptedWriteError,
    InvalidChunkError,
    PathSafetyError,
    PublicationError,
    RawStoreError,
    RecoverableCatalogRegistrationError,
)
from cryptofactors.ingest.raw.models import (
    AcquisitionMetadata,
    ChecksumVerification,
    FailedAcquisitionRecord,
    IdempotentDuplicateResult,
    PublicationReceipt,
    PublishResult,
    RawObjectStoreConfig,
)
from cryptofactors.ingest.raw.paths import (
    assert_path_under_root,
    assert_regular_nonsymlink_file,
    content_addressed_absolute_path,
    content_addressed_relative_path,
    fsync_dir,
    raw_object_id_for_sha256,
    validate_sha256_hex,
)
from cryptofactors.ingest.raw.protocols import RawObjectCatalog

ChunkSource = Union[BinaryIO, Iterable[bytes], Iterator[bytes]]

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX
    fcntl = None  # type: ignore[assignment]


def _iter_chunks(source: ChunkSource, *, chunk_size: int) -> Iterator[bytes]:
    if hasattr(source, "read"):
        reader = source
        while True:
            try:
                piece = reader.read(chunk_size)
            except Exception as exc:
                raise InterruptedWriteError(
                    f"input stream read failed: {exc}",
                    context={"error": str(exc)},
                ) from exc
            if not piece:
                break
            if not isinstance(piece, (bytes, bytearray, memoryview)):
                raise InvalidChunkError(
                    f"stream read returned non-bytes: {type(piece).__name__}"
                )
            yield bytes(piece)
        return

    try:
        for item in source:
            if not isinstance(item, (bytes, bytearray, memoryview)):
                raise InvalidChunkError(
                    f"chunk must be bytes-like, got {type(item).__name__}"
                )
            yield bytes(item)
    except (InvalidChunkError, InterruptedWriteError):
        raise
    except Exception as exc:
        raise InterruptedWriteError(
            f"chunk iterable aborted: {exc}",
            context={"error": str(exc)},
        ) from exc


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            piece = handle.read(chunk_size)
            if not piece:
                break
            digest.update(piece)
    return digest.hexdigest()


def _publish_exclusive_link(tmp_path: Path, final_path: Path) -> bool:
    """Atomic no-clobber publication via hardlink only.

    Returns True if this caller created ``final_path``.
    Never creates an empty placeholder. Never overwrites.
    Raises PublicationError if the filesystem cannot provide the guarantee.
    """
    final_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(str(tmp_path), str(final_path))
        return True
    except FileExistsError:
        return False
    except OSError as exc:
        raise PublicationError(
            "atomic no-clobber publication unsupported or failed on this filesystem "
            "(hardlink required; no empty-file fallback)",
            context={
                "tmp": str(tmp_path),
                "final": str(final_path),
                "errno": getattr(exc, "errno", None),
                "error": str(exc),
            },
        ) from exc


def _verify_existing_object(path: Path, *, expected_sha256: str, expected_size: int) -> None:
    if path.is_symlink():
        raise CorruptDestinationError(
            "destination is a symlink",
            context={"path": str(path)},
        )
    try:
        assert_regular_nonsymlink_file(path, label="destination")
    except PathSafetyError as exc:
        raise CorruptDestinationError(str(exc), context=exc.context) from exc
    st = os.lstat(path)
    if not statmod.S_ISREG(st.st_mode):
        raise CorruptDestinationError(
            "destination is not a regular file",
            context={"path": str(path)},
        )
    if st.st_size != expected_size:
        raise CorruptDestinationError(
            "destination size mismatch",
            context={
                "path": str(path),
                "expected_size": expected_size,
                "actual_size": st.st_size,
            },
        )
    actual = _sha256_file(path)
    if actual != expected_sha256:
        raise CorruptDestinationError(
            "destination SHA-256 mismatch",
            context={
                "path": str(path),
                "expected": expected_sha256,
                "actual": actual,
            },
        )


def _fsync_parents(path: Path, *, stop_at: Path) -> None:
    """fsync directory entries from path's parent up to stop_at (inclusive)."""
    stop = stop_at.resolve()
    current = path.parent.resolve()
    seen: set[Path] = set()
    while True:
        if current in seen:
            break
        seen.add(current)
        try:
            fsync_dir(current)
        except OSError:
            pass
        if current == stop or current.parent == current:
            break
        current = current.parent


class RawObjectWriter:
    """Immutable content-addressed writer with acquisition provenance.

    Order:
    1. stream bytes to a leased temp file (hash + count);
    2. fsync; atomically hardlink-publish or confirm identical existing object;
    3. build a :class:`PublicationReceipt` and register content + acquisition.
    """

    def __init__(
        self,
        config: RawObjectStoreConfig,
        catalog: RawObjectCatalog,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self._config = config
        self._catalog = catalog
        self._chunk_size = chunk_size
        self._config.root.mkdir(parents=True, exist_ok=True)
        # Reject symlinked root components when present.
        if self._config.root.exists() and self._config.root.is_symlink():
            raise PathSafetyError(
                "store root must not be a symlink",
                context={"root": str(self._config.root)},
            )
        self._config.temp_dir().mkdir(parents=True, exist_ok=True)
        if self._config.temp_dir().is_symlink():
            raise PathSafetyError(
                "temp dir must not be a symlink",
                context={"temp_dir": str(self._config.temp_dir())},
            )

    def write_stream(
        self,
        source: ChunkSource,
        metadata: AcquisitionMetadata,
        *,
        expected_content_sha256: str | None = None,
        register_catalog: bool = True,
        reject_unsupported_checksum: bool = True,
        reject_malformed_checksum: bool = True,
    ) -> PublishResult | IdempotentDuplicateResult:
        if not metadata.source_id:
            raise RawStoreError("metadata.source_id must be non-empty")

        acquisition_id = metadata.acquisition_id or f"acq_{uuid.uuid4().hex}"
        # Ensure stable id on metadata for catalog
        metadata = AcquisitionMetadata(
            source_id=metadata.source_id,
            acquisition_id=acquisition_id,
            request=metadata.request,
            response_metadata=metadata.response_metadata,
            original_name=metadata.original_name,
            provider_checksum=metadata.provider_checksum,
            acquired_at=metadata.acquired_at,
            event_start=metadata.event_start,
            event_end=metadata.event_end,
            content_status=metadata.content_status,
        )

        tmp_path: Path | None = None
        lock_fd: int | None = None
        digest = hashlib.sha256()
        byte_size = 0

        try:
            fd, tmp_name = tempfile.mkstemp(
                prefix=".partial-",
                suffix=".part",
                dir=str(self._config.temp_dir()),
            )
            tmp_path = Path(tmp_name)
            assert_path_under_root(tmp_path, self._config.root.resolve(), label="temp file")

            # Active-writer exclusive lease for the duration of the write.
            if fcntl is not None:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    os.close(fd)
                    tmp_path.unlink(missing_ok=True)
                    tmp_path = None
                    raise InterruptedWriteError(
                        f"could not acquire exclusive temp lease: {exc}",
                        context={"tmp": str(tmp_name)},
                    ) from exc
            lock_fd = fd

            try:
                with os.fdopen(fd, "wb") as handle:
                    lock_fd = None  # owned by handle now; flock remains on fileno
                    fd = -1
                    for chunk in _iter_chunks(source, chunk_size=self._chunk_size):
                        handle.write(chunk)
                        digest.update(chunk)
                        byte_size += len(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())
                    # Keep lock until after we close by re-flocking? flock is on the
                    # file description; closing handle releases the lock. Hold via
                    # separate lock file descriptor:
            except (InvalidChunkError, InterruptedWriteError, ChecksumError, HashMismatchError):
                raise
            except OSError as exc:
                raise InterruptedWriteError(
                    f"write failed: {exc}",
                    context={"error": str(exc)},
                ) from exc
            finally:
                if fd >= 0:
                    try:
                        os.close(fd)
                    except OSError:
                        pass

            # Re-open temp for lease duration through publish.
            lease_fd = os.open(str(tmp_path), os.O_RDONLY)
            try:
                if fcntl is not None:
                    fcntl.flock(lease_fd, fcntl.LOCK_EX)
                content_hash = digest.hexdigest()

                if expected_content_sha256 is not None:
                    expected = validate_sha256_hex(expected_content_sha256)
                    if content_hash != expected:
                        raise HashMismatchError(
                            "computed content SHA-256 does not match expected_content_sha256",
                            context={"expected": expected, "actual": content_hash},
                        )

                verification = evaluate_provider_checksum(
                    metadata.provider_checksum,
                    content_sha256=content_hash,
                    reject_unsupported=reject_unsupported_checksum,
                    reject_malformed=reject_malformed_checksum,
                )
                raise_if_hard_fail(verification, content_sha256=content_hash)
                # Refuse VERIFIED content status without verified checksum.
                require_checksum_ok_for_verified_status(
                    metadata.content_status, verification
                )

                rel = content_addressed_relative_path(
                    content_hash, prefix=self._config.object_prefix
                )
                final_path = content_addressed_absolute_path(
                    self._config.root,
                    content_hash,
                    prefix=self._config.object_prefix,
                )
                assert_path_under_root(
                    final_path, self._config.root.resolve(), label="final path"
                )
                storage_uri = rel.as_posix()
                object_id = raw_object_id_for_sha256(content_hash)

                reused = False
                if final_path.exists() or final_path.is_symlink():
                    _verify_existing_object(
                        final_path,
                        expected_sha256=content_hash,
                        expected_size=byte_size,
                    )
                    reused = True
                else:
                    created = _publish_exclusive_link(tmp_path, final_path)
                    if created:
                        # fsync published inode and parent directories.
                        pfd = os.open(str(final_path), os.O_RDONLY)
                        try:
                            os.fsync(pfd)
                        finally:
                            os.close(pfd)
                        _fsync_parents(final_path, stop_at=self._config.root)
                    else:
                        _verify_existing_object(
                            final_path,
                            expected_sha256=content_hash,
                            expected_size=byte_size,
                        )
                        reused = True

                receipt = PublicationReceipt(
                    raw_object_id=object_id,
                    sha256=content_hash,
                    byte_size=byte_size,
                    storage_path=final_path,
                    storage_uri=storage_uri,
                    reused_existing=reused,
                    verified_regular_file=True,
                    verified_size=True,
                    verified_sha256=True,
                )

                catalog_registered = False
                content_inserted = False
                acq_inserted = False
                if register_catalog:
                    try:
                        content_inserted, acq_inserted = self._catalog.register_publication(
                            receipt=receipt,
                            metadata=metadata,
                            checksum_verification=verification,
                            store_root=str(self._config.root.resolve()),
                        )
                        catalog_registered = True
                    except RecoverableCatalogRegistrationError:
                        raise
                    except Exception as exc:
                        raise RecoverableCatalogRegistrationError(
                            f"catalog registration failed after publication: {exc}",
                            acquisition_id=acquisition_id,
                            sha256=content_hash,
                            byte_size=byte_size,
                            storage_path=str(final_path),
                            storage_uri=storage_uri,
                            raw_object_id=object_id,
                            context={"error": str(exc)},
                        ) from exc

                if reused:
                    return IdempotentDuplicateResult(
                        acquisition_id=acquisition_id,
                        raw_object_id=object_id,
                        sha256=content_hash,
                        byte_size=byte_size,
                        storage_path=final_path,
                        storage_uri=storage_uri,
                        catalog_registered=catalog_registered,
                        content_already_present=True,
                        acquisition_already_registered=catalog_registered and not acq_inserted,
                        checksum_verification=verification,
                    )
                return PublishResult(
                    acquisition_id=acquisition_id,
                    raw_object_id=object_id,
                    sha256=content_hash,
                    byte_size=byte_size,
                    storage_path=final_path,
                    storage_uri=storage_uri,
                    reused_existing=False,
                    catalog_registered=catalog_registered,
                    checksum_verification=verification,
                    new_acquisition=acq_inserted if catalog_registered else True,
                )
            finally:
                if fcntl is not None:
                    try:
                        fcntl.flock(lease_fd, fcntl.LOCK_UN)
                    except OSError:
                        pass
                os.close(lease_fd)
                if tmp_path is not None and tmp_path.exists():
                    # After successful hardlink, tmp is a second name; always unlink tmp.
                    tmp_path.unlink(missing_ok=True)
                    tmp_path = None
        except (
            InvalidChunkError,
            InterruptedWriteError,
            HashMismatchError,
            ChecksumError,
            CorruptDestinationError,
            PublicationError,
            PathSafetyError,
            RecoverableCatalogRegistrationError,
            RawStoreError,
        ):
            raise
        except Exception as exc:
            raise InterruptedWriteError(
                f"raw write failed: {exc}",
                context={"error": str(exc)},
            ) from exc
        finally:
            if lock_fd is not None:
                try:
                    os.close(lock_fd)
                except OSError:
                    pass
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def record_failed_acquisition(
        self,
        metadata: AcquisitionMetadata,
        error_message: str,
        *,
        checksum_verification: ChecksumVerification = ChecksumVerification.ABSENT,
    ) -> FailedAcquisitionRecord:
        return self._catalog.record_failed_acquisition(
            metadata=metadata,
            error_message=error_message,
            checksum_verification=checksum_verification,
        )

    def retry_catalog_registration(
        self,
        *,
        acquisition_id: str,
        sha256: str,
        byte_size: int,
        metadata: AcquisitionMetadata,
        checksum_verification: ChecksumVerification,
    ) -> tuple[bool, bool]:
        """Idempotent registration using the same acquisition_id and a fresh receipt."""
        digest = validate_sha256_hex(sha256)
        final_path = content_addressed_absolute_path(
            self._config.root, digest, prefix=self._config.object_prefix
        )
        _verify_existing_object(
            final_path, expected_sha256=digest, expected_size=byte_size
        )
        rel = content_addressed_relative_path(digest, prefix=self._config.object_prefix)
        meta = AcquisitionMetadata(
            source_id=metadata.source_id,
            acquisition_id=acquisition_id,
            request=metadata.request,
            response_metadata=metadata.response_metadata,
            original_name=metadata.original_name,
            provider_checksum=metadata.provider_checksum,
            acquired_at=metadata.acquired_at,
            event_start=metadata.event_start,
            event_end=metadata.event_end,
            content_status=metadata.content_status,
        )
        receipt = PublicationReceipt(
            raw_object_id=raw_object_id_for_sha256(digest),
            sha256=digest,
            byte_size=byte_size,
            storage_path=final_path,
            storage_uri=rel.as_posix(),
            reused_existing=True,
            verified_regular_file=True,
            verified_size=True,
            verified_sha256=True,
        )
        return self._catalog.register_publication(
            receipt=receipt,
            metadata=meta,
            checksum_verification=checksum_verification,
            store_root=str(self._config.root.resolve()),
        )
