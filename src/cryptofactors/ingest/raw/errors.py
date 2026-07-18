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
    """Optional provider checksum does not match computed SHA-256."""


class CorruptDestinationError(RawStoreError):
    """Preexisting path exists but bytes do not match the content hash/path."""


class RecoverableCatalogRegistrationError(RawStoreError):
    """Object bytes are published; catalog registration failed and may be retried.

    The immutable content object is left intact. Callers should retry registration
    idempotently via the catalog boundary.
    """

    def __init__(
        self,
        message: str,
        *,
        sha256: str,
        byte_size: int,
        storage_path: str,
        raw_object_id: str,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context=context)
        self.sha256 = sha256
        self.byte_size = byte_size
        self.storage_path = storage_path
        self.raw_object_id = raw_object_id
