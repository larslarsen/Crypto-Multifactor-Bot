"""Errors for execution domain (EXEC-001, EXEC-002)."""

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


class PaperOpsError(PaperExecutionError):
    """Raised when paper session persistence or monitoring fails."""


class DrawdownLimitExceededError(PaperExecutionError):
    """Raised when equity drawdown exceeds the configured maximum threshold."""


class LiveExecutionError(RuntimeError):
    """Base error for live execution operations (EXEC-002)."""

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


class RiskLimitViolationError(LiveExecutionError):
    """Raised when a pre-trade risk limit check fails."""


class KillSwitchActiveError(LiveExecutionError):
    """Raised when an order is attempted while the kill-switch is active."""
