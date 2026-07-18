"""Typed exceptions for the raw-object store."""

from __future__ import annotations

from typing import Any, Mapping


class RawStoreError(Exception):
    """Base error for raw-object store operations."""

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


class InvalidChunkError(RawStoreError):
    """Chunk was not bytes / bytearray / memoryview."""


class InterruptedWriteError(RawStoreError):
    """Input stream raised or aborted before a complete write."""


class HashMismatchError(RawStoreError):
    """Provider checksum or expected content hash does not match computed SHA-256."""


class ChecksumError(RawStoreError):
    """Malformed or unsupported checksum configuration/evidence."""


class CorruptDestinationError(RawStoreError):
    """Preexisting path exists but is not a valid matching content object."""


class PublicationError(RawStoreError):
    """Atomic no-clobber publication failed or is unsupported on this filesystem."""


class DurabilityError(PublicationError):
    """Required file or directory fsync failed."""


class PathSafetyError(RawStoreError):
    """Storage path configuration or destination failed safety validation."""


class CatalogRegistrationError(RawStoreError):
    """Catalog refused registration (missing/invalid publication evidence)."""


class AcquisitionConflictError(RawStoreError):
    """Same acquisition_id reused with conflicting provenance or content."""


class RecoverableCatalogRegistrationError(RawStoreError):
    """Object bytes are published; catalog/acquisition registration failed and may be retried.

    The immutable content object is left intact. Retry with the same acquisition_id.
    """

    def __init__(
        self,
        message: str,
        *,
        acquisition_id: str,
        sha256: str,
        byte_size: int,
        storage_path: str,
        storage_uri: str,
        raw_object_id: str,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context=context)
        self.acquisition_id = acquisition_id
        self.sha256 = sha256
        self.byte_size = byte_size
        self.storage_path = storage_path
        self.storage_uri = storage_uri
        self.raw_object_id = raw_object_id
