"""Streaming content-addressed raw object writer."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import BinaryIO, Union

from cryptofactors.ingest.raw.errors import (
    CorruptDestinationError,
    HashMismatchError,
    InterruptedWriteError,
    InvalidChunkError,
    RawStoreError,
    RecoverableCatalogRegistrationError,
)
from cryptofactors.ingest.raw.models import (
    AcquisitionMetadata,
    FailedAcquisitionRecord,
    IdempotentDuplicateResult,
    PublishResult,
    RawObjectStoreConfig,
)
from cryptofactors.ingest.raw.paths import (
    content_addressed_absolute_path,
    content_addressed_relative_path,
    raw_object_id_for_sha256,
    validate_sha256_hex,
)
from cryptofactors.ingest.raw.protocols import RawObjectCatalog

ChunkSource = Union[BinaryIO, Iterable[bytes], Iterator[bytes]]


def _iter_chunks(source: ChunkSource, *, chunk_size: int) -> Iterator[bytes]:
    if hasattr(source, "read"):
        reader = source  # BinaryIO-like
        while True:
            try:
                piece = reader.read(chunk_size)
            except Exception as exc:
                raise InterruptedWriteError(
                    f"input stream read failed: {exc}",
                    context={"error": str(exc)},
                ) from exc
            if piece is None:
                break
            if piece == b"":
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
    except InvalidChunkError:
        raise
    except InterruptedWriteError:
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


def _publish_exclusive(tmp_path: Path, final_path: Path) -> bool:
    """Publish without overwriting. Returns True if this caller created final_path."""
    final_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(str(tmp_path), str(final_path))
        return True
    except FileExistsError:
        return False
    except OSError:
        try:
            fd = os.open(str(final_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
        except FileExistsError:
            return False
        os.replace(str(tmp_path), str(final_path))
        return True


class RawObjectWriter:
    """Immutable content-addressed writer with catalog registration ordering.

    Order:
    1. stream bytes to a same-filesystem temp file (hash + count);
    2. fsync; atomically publish or confirm identical existing object;
    3. only then commit the accepted catalog row.

    If catalog registration fails after publication, the content object remains
    and :class:`RecoverableCatalogRegistrationError` is raised for idempotent retry.
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
        self._config.temp_dir().mkdir(parents=True, exist_ok=True)

    def write_stream(
        self,
        source: ChunkSource,
        metadata: AcquisitionMetadata,
        *,
        expected_sha256: str | None = None,
        register_catalog: bool = True,
    ) -> PublishResult | IdempotentDuplicateResult:
        """Write exact original bytes from ``source`` and optionally register.

        Never transforms bytes. Never overwrites existing content. Identical
        existing content is an idempotent duplicate.
        """
        if not metadata.source_id:
            raise RawStoreError("metadata.source_id must be non-empty")

        tmp_path: Path | None = None
        digest = hashlib.sha256()
        byte_size = 0

        try:
            fd, tmp_name = tempfile.mkstemp(
                prefix=".partial-",
                suffix=".part",
                dir=self._config.temp_dir(),
            )
            tmp_path = Path(tmp_name)
            try:
                with os.fdopen(fd, "wb") as handle:
                    for chunk in _iter_chunks(source, chunk_size=self._chunk_size):
                        handle.write(chunk)
                        digest.update(chunk)
                        byte_size += len(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())
            except (InvalidChunkError, InterruptedWriteError):
                raise
            except OSError as exc:
                raise InterruptedWriteError(
                    f"write failed: {exc}",
                    context={"error": str(exc)},
                ) from exc

            content_hash = digest.hexdigest()
            if expected_sha256 is not None:
                expected = validate_sha256_hex(expected_sha256)
                if content_hash != expected:
                    raise HashMismatchError(
                        "computed SHA-256 does not match expected_sha256",
                        context={"expected": expected, "actual": content_hash},
                    )
            if metadata.source_checksum:
                sc = metadata.source_checksum.lower().strip()
                if len(sc) == 64 and all(c in "0123456789abcdef" for c in sc):
                    if content_hash != sc:
                        raise HashMismatchError(
                            "computed SHA-256 does not match source_checksum",
                            context={"expected": sc, "actual": content_hash},
                        )

            rel = content_addressed_relative_path(
                content_hash, prefix=self._config.object_prefix
            )
            final_path = content_addressed_absolute_path(
                self._config.root,
                content_hash,
                prefix=self._config.object_prefix,
            )
            storage_uri = rel.as_posix()
            object_id = raw_object_id_for_sha256(content_hash)

            reused = False
            if final_path.exists():
                existing_hash = _sha256_file(final_path, chunk_size=self._chunk_size)
                if existing_hash != content_hash:
                    raise CorruptDestinationError(
                        "preexisting destination bytes do not match content hash",
                        context={
                            "path": str(final_path),
                            "path_sha256": content_hash,
                            "actual_sha256": existing_hash,
                        },
                    )
                existing_size = final_path.stat().st_size
                if existing_size != byte_size:
                    raise CorruptDestinationError(
                        "preexisting destination size mismatch",
                        context={
                            "path": str(final_path),
                            "expected_size": byte_size,
                            "actual_size": existing_size,
                        },
                    )
                reused = True
                tmp_path.unlink(missing_ok=True)
                tmp_path = None
            else:
                created = _publish_exclusive(tmp_path, final_path)
                if created:
                    # link leaves both names; replace consumes tmp.
                    if tmp_path.exists():
                        tmp_path.unlink(missing_ok=True)
                    tmp_path = None
                else:
                    # Concurrent publisher won — verify identical, never overwrite.
                    existing_hash = _sha256_file(final_path, chunk_size=self._chunk_size)
                    if existing_hash != content_hash:
                        raise CorruptDestinationError(
                            "concurrent destination bytes do not match content hash",
                            context={
                                "path": str(final_path),
                                "path_sha256": content_hash,
                                "actual_sha256": existing_hash,
                            },
                        )
                    reused = True
                    tmp_path.unlink(missing_ok=True)
                    tmp_path = None

            # Bytes are published or confirmed identical. Catalog only after that.
            catalog_registered = False
            was_already = False
            if register_catalog:
                try:
                    inserted = self._catalog.register_accepted(
                        raw_object_id=object_id,
                        sha256=content_hash,
                        byte_size=byte_size,
                        storage_uri=storage_uri,
                        metadata=metadata,
                    )
                    catalog_registered = True
                    was_already = not inserted
                except RecoverableCatalogRegistrationError:
                    raise
                except Exception as exc:
                    raise RecoverableCatalogRegistrationError(
                        f"catalog registration failed after publication: {exc}",
                        sha256=content_hash,
                        byte_size=byte_size,
                        storage_path=str(final_path),
                        raw_object_id=object_id,
                        context={"storage_uri": storage_uri, "error": str(exc)},
                    ) from exc

            if reused:
                return IdempotentDuplicateResult(
                    raw_object_id=object_id,
                    sha256=content_hash,
                    byte_size=byte_size,
                    storage_path=final_path,
                    storage_uri=storage_uri,
                    catalog_registered=catalog_registered,
                    was_already_registered=was_already,
                )
            return PublishResult(
                raw_object_id=object_id,
                sha256=content_hash,
                byte_size=byte_size,
                storage_path=final_path,
                storage_uri=storage_uri,
                reused_existing=False,
                catalog_registered=catalog_registered,
            )
        except (
            InvalidChunkError,
            InterruptedWriteError,
            HashMismatchError,
            CorruptDestinationError,
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
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def record_failed_acquisition(
        self,
        *,
        source_id: str,
        error_message: str,
        request: dict[str, object] | None = None,
    ) -> FailedAcquisitionRecord:
        """Record a failed acquisition with no accepted raw object."""
        return self._catalog.record_failed_acquisition(
            source_id=source_id,
            error_message=error_message,
            request=request or {},
        )

    def retry_catalog_registration(
        self,
        *,
        sha256: str,
        byte_size: int,
        metadata: AcquisitionMetadata,
    ) -> bool:
        """Idempotent catalog registration for an already-published object."""
        digest = validate_sha256_hex(sha256)
        final_path = content_addressed_absolute_path(
            self._config.root, digest, prefix=self._config.object_prefix
        )
        if not final_path.exists():
            raise RawStoreError(
                "cannot retry catalog registration: content object missing",
                context={"path": str(final_path)},
            )
        actual = _sha256_file(final_path, chunk_size=self._chunk_size)
        if actual != digest:
            raise CorruptDestinationError(
                "content object hash mismatch on catalog retry",
                context={"path": str(final_path), "expected": digest, "actual": actual},
            )
        if final_path.stat().st_size != byte_size:
            raise CorruptDestinationError(
                "content object size mismatch on catalog retry",
                context={
                    "path": str(final_path),
                    "expected_size": byte_size,
                    "actual_size": final_path.stat().st_size,
                },
            )
        rel = content_addressed_relative_path(digest, prefix=self._config.object_prefix)
        return self._catalog.register_accepted(
            raw_object_id=raw_object_id_for_sha256(digest),
            sha256=digest,
            byte_size=byte_size,
            storage_uri=rel.as_posix(),
            metadata=metadata,
        )
