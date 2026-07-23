"""Errors for execution domain (EXEC-001)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class PaperExecutionError(RuntimeError):
    """Base error for paper execution operations."""

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


class UnapprovedArtifactError(PaperExecutionError):
    """Raised when an execution operation is attempted on an unapproved artifact."""
