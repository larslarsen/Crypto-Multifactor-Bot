"""Typed errors for REF-001 reference master."""

from __future__ import annotations

from typing import Any, Mapping


class ReferenceError(Exception):
    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


class ReferenceValidationError(ReferenceError):
    """Invalid interval, missing required field, or schema violation."""


class ReferenceConflictError(ReferenceError):
    """Conflicting active version, impossible reference, or alias collision."""


class ReferenceNotFoundError(ReferenceError):
    """Requested identity does not exist."""


class ReferenceResolutionError(ReferenceError):
    """Alias resolution failed in an unexpected way."""
