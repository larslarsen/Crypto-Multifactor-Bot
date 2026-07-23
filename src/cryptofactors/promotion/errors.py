"""Errors for the Promotion Registry domain (PROMO-001)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class PromotionError(RuntimeError):
    """Base error for promotion registry operations."""

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


class PromotionGateError(PromotionError):
    """Raised when a promotion state transition fails gate requirements."""


class InvalidPromotionPayloadError(PromotionError):
    """Raised when a promotion payload is missing required immutable identity fields."""
