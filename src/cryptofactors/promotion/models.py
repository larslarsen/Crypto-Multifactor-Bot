"""Models and state vocabulary for Promotion Registry (PROMO-001)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from cryptofactors.promotion.errors import InvalidPromotionPayloadError


class PromotionState(str, Enum):
    """The nine canonical promotion states from ADR-0008."""

    RESEARCH_CANDIDATE = "RESEARCH_CANDIDATE"
    RESEARCH_ACCEPTED = "RESEARCH_ACCEPTED"
    PAPER_APPROVED = "PAPER_APPROVED"
    PAPER_SUSPENDED = "PAPER_SUSPENDED"
    LIVE_APPROVED = "LIVE_APPROVED"
    LIVE_SUSPENDED = "LIVE_SUSPENDED"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"

    def is_terminal(self) -> bool:
        """Terminal states from which an artifact cannot be promoted without a new identity."""
        return self in (
            PromotionState.RETIRED,
            PromotionState.REJECTED,
            PromotionState.QUARANTINED,
        )


class PromotionTarget(str, Enum):
    """Authorization target stage."""

    RESEARCH = "RESEARCH"
    PAPER = "PAPER"
    LIVE = "LIVE"


def _require_utc_datetime(value: Any, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise InvalidPromotionPayloadError(
            f"{field_name} must be a datetime object",
            context={"field": field_name, "type": type(value).__name__},
        )
    if value.tzinfo is None:
        raise InvalidPromotionPayloadError(
            f"{field_name} must be timezone-aware UTC",
            context={"field": field_name, "value": str(value)},
        )
    return value.astimezone(timezone.utc)


def _require_non_empty_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise InvalidPromotionPayloadError(
            f"{field_name} must be a string",
            context={"field": field_name, "type": type(value).__name__},
        )
    s = value.strip()
    if not s:
        raise InvalidPromotionPayloadError(
            f"{field_name} must be a non-empty string",
            context={"field": field_name},
        )
    return s


@dataclass(frozen=True, slots=True)
class PromotionIdentityPayload:
    """Immutable identity payload required on every promotion event."""

    model_artifact_id: str
    experiment_fingerprint: str
    dataset_ids: tuple[str, ...]
    universe_ids: tuple[str, ...]
    code_commit: str
    config_version: str
    feature_version: str
    representation_version: str
    portfolio_version: str
    cost_model_version: str
    risk_policy_version: str
    target_stage: PromotionTarget
    effective_time: datetime
    approving_authority: str
    evidence_reference: str
    paper_observation_reference: str | None = None
    kill_switch_procedure: str | None = None

    def validate(self) -> None:
        """Validate that all required immutable identity fields are present and valid."""
        _require_non_empty_str(self.model_artifact_id, field_name="model_artifact_id")
        _require_non_empty_str(self.experiment_fingerprint, field_name="experiment_fingerprint")
        _require_non_empty_str(self.code_commit, field_name="code_commit")
        _require_non_empty_str(self.config_version, field_name="config_version")
        _require_non_empty_str(self.feature_version, field_name="feature_version")
        _require_non_empty_str(self.representation_version, field_name="representation_version")
        _require_non_empty_str(self.portfolio_version, field_name="portfolio_version")
        _require_non_empty_str(self.cost_model_version, field_name="cost_model_version")
        _require_non_empty_str(self.risk_policy_version, field_name="risk_policy_version")
        _require_non_empty_str(self.approving_authority, field_name="approving_authority")
        _require_non_empty_str(self.evidence_reference, field_name="evidence_reference")
        _require_utc_datetime(self.effective_time, field_name="effective_time")

        if not isinstance(self.target_stage, PromotionTarget):
            raise InvalidPromotionPayloadError(
                "target_stage must be a valid PromotionTarget enum",
                context={"value": str(self.target_stage)},
            )

        if not isinstance(self.dataset_ids, tuple) or not self.dataset_ids:
            raise InvalidPromotionPayloadError(
                "dataset_ids must be a non-empty tuple of dataset strings",
                context={"dataset_ids": self.dataset_ids},
            )
        for d in self.dataset_ids:
            _require_non_empty_str(d, field_name="dataset_id item")

        if not isinstance(self.universe_ids, tuple) or not self.universe_ids:
            raise InvalidPromotionPayloadError(
                "universe_ids must be a non-empty tuple of universe strings",
                context={"universe_ids": self.universe_ids},
            )
        for u in self.universe_ids:
            _require_non_empty_str(u, field_name="universe_id item")


@dataclass(frozen=True, slots=True)
class PromotionEvent:
    """An append-only promotion record representing a state transition."""

    promotion_event_id: str
    payload: PromotionIdentityPayload
    promotion_state: PromotionState
    event_at: datetime
    reason: str
