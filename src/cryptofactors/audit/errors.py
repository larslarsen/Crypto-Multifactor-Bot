"""Typed exceptions for AUD-001 schema/coverage profiler."""

from __future__ import annotations

from typing import Any, Mapping


class AuditProfileError(Exception):
    """Base error for AUD-001 profiler operations."""

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


class AuditInputError(AuditProfileError):
    """Invalid path, identity, or profiler configuration."""


class AuditFormatError(AuditProfileError):
    """Unsupported or unreadable candidate format."""


class AuditMappingError(AuditProfileError):
    """Required column mapping missing or contradictory."""


class AuditOutputError(AuditProfileError):
    """Failed to stage profiler artifacts."""
