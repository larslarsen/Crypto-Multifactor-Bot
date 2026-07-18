"""Explicit exception types for the source-audit toolkit."""

from dataclasses import dataclass
from typing import Any, Optional


class AuditError(Exception):
    """Base exception for all audit failures."""
    def __init__(self, message: str, context: Optional[dict] = None):
        super().__init__(message)
        self.context = context or {}


class DownloadError(AuditError):
    """Raised on download failures (limits, HTTP errors, timeouts)."""
    pass


class ChecksumMismatchError(AuditError):
    """Raised when provider checksum does not match computed hash."""
    pass


class UnsafeArchiveError(AuditError):
    """Raised on ZIP-slip, encrypted archives, decompression bombs, etc."""
    pass


class MalformedCSVError(AuditError):
    """Raised on schema drift, malformed rows, encoding issues."""
    pass


class AmbiguousTimestampError(AuditError):
    """Raised when timestamp unit cannot be determined without ambiguity."""
    pass


class PaginationError(AuditError):
    """Raised on pagination loops, non-progress, repeated cursors."""
    pass


class OrderingViolationError(AuditError):
    """Raised on detected ordering or duplicate issues in data."""
    pass


class InvalidNumericError(AuditError):
    """Raised on overflow or invalid numeric values in financial data."""
    pass
