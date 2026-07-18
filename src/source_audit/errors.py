"""Explicit exception hierarchy for the source-audit toolkit."""

from __future__ import annotations

from typing import Any, Mapping


class AuditError(Exception):
    """Base exception for all source-audit failures."""

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


class DownloadError(AuditError):
    """Download or atomic-publication failure."""


class ChecksumMismatchError(DownloadError):
    """Provider checksum does not match the computed content hash."""


class SizeLimitError(DownloadError):
    """Byte, page, record, or member size limit exceeded."""


class UnsafeArchiveError(AuditError):
    """ZIP safety violation (path traversal, symlink, bomb, encryption, etc.)."""


class MalformedCSVError(AuditError):
    """CSV schema, header, encoding, or structural failure."""


class AmbiguousTimestampError(AuditError):
    """More than one timestamp unit is plausible for a value."""


class OutOfRangeTimestampError(AuditError):
    """No timestamp unit yields a datetime within the configured bounds."""


class PaginationError(AuditError):
    """Pagination loop, non-progress, bound violation, or ordering failure."""


class OrderingViolationError(AuditError):
    """Detected ordering, gap, or duplicate-policy violation."""


class InvalidNumericError(AuditError):
    """Non-finite, invalid, or precision-unsafe numeric input."""


class SerializationError(AuditError):
    """Unsupported type or non-deterministic serialization input."""


class BarReconstructionError(AuditError):
    """Trade-to-bar reconstruction failure."""


class PrecisionComparisonError(AuditError):
    """Binance archive precision comparison failure."""
