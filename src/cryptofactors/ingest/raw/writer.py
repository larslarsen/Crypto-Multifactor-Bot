"""Streaming content-addressed raw object writer with acquisition provenance."""

from __future__ import annotations

import hashlib
import os
import stat as statmod
import tempfile
import uuid
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import BinaryIO, IO, Union

from cryptofactors.ingest.raw.checksums import (
    evaluate_provider_checksum,
    raise_if_hard_fail,
    require_checksum_ok_for_verified_status,
)
from cryptofactors.ingest.raw.errors import (
    AcquisitionConflictError,
    CatalogRegistrationError,
    ChecksumError,
    CorruptDestinationError,
    DurabilityError,
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
    assert_no_symlink_components,
    assert_parents_are_directories,
    assert_path_under_root,
    assert_regular_nonsymlink_file,
    canonical_identity,
    fsync_dir,
    fsync_file,
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
    """Atomic no-clobber publication via hardlink only."""
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
        fsync_dir(current)
        if current == stop or current.parent == current:
            break
        try:
            current.relative_to(stop)
        except ValueError:
            break
        current = current.parent


class RawObjectWriter:
    """Immutable content-addressed writer with continuous temp lease + provenance."""

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
        root = self._config.root
        root.mkdir(parents=True, exist_ok=True)
        if root.exists() and root.is_symlink():
            raise PathSafetyError(
                "store root must not be a symlink",
                context={"root": str(root)},
            )
        assert_no_symlink_components(root.resolve(), stop_at=root.resolve())
        temp = self._config.temp_dir()
        temp.mkdir(parents=True, exist_ok=True)
        if temp.is_symlink():
            raise PathSafetyError(
                "temp dir must not be a symlink",
                context={"temp_dir": str(temp)},
            )
        assert_no_symlink_components(temp, stop_at=root.resolve())

    def _record_pre_publication_failure(
        self,
        metadata: AcquisitionMetadata,
        exc: BaseException,
        *,
        register_catalog: bool,
        checksum_verification: ChecksumVerification = ChecksumVerification.ABSENT,
    ) -> None:
        """Record FAILED acquisition without masking the original exception."""
        if not register_catalog:
            return
        if isinstance(exc, RecoverableCatalogRegistrationError):
            # Post-publication failure — must not misclassify published bytes.
            return
        try:
            self._catalog.record_failed_acquisition(
                metadata=metadata,
                error_message=f"{type(exc).__name__}: {exc}",
                checksum_verification=checksum_verification,
            )
        except Exception as rec_err:
            # Preserve original as the raised exception; attach recording failure.
            raise exc from rec_err

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

        root = self._config.root.resolve()
        tmp_path: Path | None = None
        handle: IO[bytes] | None = None
        digest = hashlib.sha256()
        byte_size = 0
        verification = ChecksumVerification.ABSENT
        published = False

        try:
            assert_no_symlink_components(self._config.temp_dir(), stop_at=root)
            fd, tmp_name = tempfile.mkstemp(
                prefix=".partial-",
                suffix=".part",
                dir=str(self._config.temp_dir()),
            )
            tmp_path = Path(tmp_name)
            assert_path_under_root(tmp_path, root, label="temp file")

            # Continuous exclusive lease on one fd from create through cleanup.
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

            handle = os.fdopen(fd, "wb")
            # fd ownership transferred to handle; lease held until handle.close().
            try:
                for chunk in _iter_chunks(source, chunk_size=self._chunk_size):
                    handle.write(chunk)
                    digest.update(chunk)
                    byte_size += len(chunk)
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError as exc:
                    raise DurabilityError(
                        f"temp file fsync failed: {tmp_path}",
                        context={"path": str(tmp_path), "error": str(exc)},
                    ) from exc

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
                require_checksum_ok_for_verified_status(
                    metadata.content_status, verification
                )

                digest_c, object_id, final_path, storage_uri = canonical_identity(
                    root=root,
                    object_prefix=self._config.object_prefix,
                    sha256_hex=content_hash,
                )
                assert digest_c == content_hash

                # Path safety immediately before publication.
                assert_path_under_root(final_path, root, label="final path")
                assert_no_symlink_components(final_path.parent, stop_at=root)
                assert_parents_are_directories(final_path, stop_at=root)

                reused = False
                if final_path.exists() or final_path.is_symlink():
                    _verify_existing_object(
                        final_path,
                        expected_sha256=content_hash,
                        expected_size=byte_size,
                    )
                    reused = True
                    published = True
                else:
                    created = _publish_exclusive_link(tmp_path, final_path)
                    if created:
                        # Link succeeded → object is published; durability errors must
                        # not misclassify it as a failed acquisition.
                        published = True
                        fsync_file(final_path)
                        _fsync_parents(final_path, stop_at=root)
                    else:
                        _verify_existing_object(
                            final_path,
                            expected_sha256=content_hash,
                            expected_size=byte_size,
                        )
                        reused = True
                        published = True

                receipt = PublicationReceipt(
                    raw_object_id=object_id,
                    sha256=content_hash,
                    byte_size=byte_size,
                    storage_path=final_path,
                    storage_uri=storage_uri,
                    object_prefix=self._config.object_prefix,
                    reused_existing=reused,
                    verified_regular_file=True,
                    verified_size=True,
                    verified_sha256=True,
                )

                catalog_registered = False
                acq_inserted = False
                if register_catalog:
                    try:
                        _content_ins, acq_inserted = self._catalog.register_publication(
                            receipt=receipt,
                            metadata=metadata,
                            checksum_verification=verification,
                            store_root=str(root),
                            object_prefix=self._config.object_prefix,
                        )
                        catalog_registered = True
                    except (
                        RecoverableCatalogRegistrationError,
                        AcquisitionConflictError,
                        CatalogRegistrationError,
                    ):
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
                # Continuous lease ends only here (single close of write handle).
                if handle is not None:
                    if fcntl is not None:
                        try:
                            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                        except OSError:
                            pass
                    try:
                        handle.close()
                    except OSError:
                        pass
                    handle = None
                if tmp_path is not None and tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                    tmp_path = None

        except RecoverableCatalogRegistrationError:
            # Published bytes remain; do not record FAILED acquisition.
            raise
        except (
            InvalidChunkError,
            InterruptedWriteError,
            HashMismatchError,
            ChecksumError,
            CorruptDestinationError,
            PublicationError,
            DurabilityError,
            PathSafetyError,
            AcquisitionConflictError,
            CatalogRegistrationError,
            RawStoreError,
        ) as exc:
            # Pre-publication failures only. Post-link durability errors keep the object.
            if not published:
                try:
                    self._record_pre_publication_failure(
                        metadata,
                        exc,
                        register_catalog=register_catalog,
                        checksum_verification=verification,
                    )
                except type(exc):
                    raise
            raise
        except Exception as exc:
            wrapped = InterruptedWriteError(
                f"raw write failed: {exc}",
                context={"error": str(exc)},
            )
            if not published:
                try:
                    self._record_pre_publication_failure(
                        metadata,
                        wrapped,
                        register_catalog=register_catalog,
                        checksum_verification=verification,
                    )
                except InterruptedWriteError:
                    raise
            raise wrapped from exc
        finally:
            if handle is not None:
                try:
                    handle.close()
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
        digest, object_id, final_path, storage_uri = canonical_identity(
            root=self._config.root.resolve(),
            object_prefix=self._config.object_prefix,
            sha256_hex=sha256,
        )
        _verify_existing_object(
            final_path, expected_sha256=digest, expected_size=byte_size
        )
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
            raw_object_id=object_id,
            sha256=digest,
            byte_size=byte_size,
            storage_path=final_path,
            storage_uri=storage_uri,
            object_prefix=self._config.object_prefix,
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
            object_prefix=self._config.object_prefix,
        )
