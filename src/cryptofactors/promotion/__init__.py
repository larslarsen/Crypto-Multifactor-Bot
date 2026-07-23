"""Promotion Registry domain module (PROMO-001)."""

from cryptofactors.promotion.errors import (
    InvalidPromotionPayloadError,
    PromotionError,
    PromotionGateError,
)
from cryptofactors.promotion.models import (
    PromotionEvent,
    PromotionIdentityPayload,
    PromotionState,
    PromotionTarget,
)
from cryptofactors.promotion.registry import PromotionRegistry
from cryptofactors.promotion.state_machine import validate_transition_and_gates

__all__ = [
    "InvalidPromotionPayloadError",
    "PromotionError",
    "PromotionEvent",
    "PromotionGateError",
    "PromotionIdentityPayload",
    "PromotionRegistry",
    "PromotionState",
    "PromotionTarget",
    "validate_transition_and_gates",
]
