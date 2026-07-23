"""State machine and gate enforcement for Promotion Registry (PROMO-001)."""

from __future__ import annotations

from typing import Final

from cryptofactors.promotion.errors import PromotionGateError
from cryptofactors.promotion.models import PromotionIdentityPayload, PromotionState

# State transition matrix: current_state -> set of allowed target_states
# None represents a new artifact identity being registered.
ALLOWED_TRANSITIONS: Final[dict[PromotionState | None, set[PromotionState]]] = {
    None: {
        PromotionState.RESEARCH_CANDIDATE,
    },
    PromotionState.RESEARCH_CANDIDATE: {
        PromotionState.RESEARCH_ACCEPTED,
        PromotionState.PAPER_APPROVED,
        PromotionState.REJECTED,
        PromotionState.QUARANTINED,
    },
    PromotionState.RESEARCH_ACCEPTED: {
        PromotionState.PAPER_APPROVED,
        PromotionState.REJECTED,
        PromotionState.QUARANTINED,
    },
    PromotionState.PAPER_APPROVED: {
        PromotionState.PAPER_SUSPENDED,
        PromotionState.LIVE_APPROVED,
        PromotionState.RETIRED,
        PromotionState.REJECTED,
        PromotionState.QUARANTINED,
    },
    PromotionState.PAPER_SUSPENDED: {
        PromotionState.PAPER_APPROVED,
        PromotionState.RETIRED,
        PromotionState.REJECTED,
        PromotionState.QUARANTINED,
    },
    PromotionState.LIVE_APPROVED: {
        PromotionState.LIVE_SUSPENDED,
        PromotionState.RETIRED,
        PromotionState.REJECTED,
        PromotionState.QUARANTINED,
    },
    PromotionState.LIVE_SUSPENDED: {
        PromotionState.LIVE_APPROVED,
        PromotionState.RETIRED,
        PromotionState.REJECTED,
        PromotionState.QUARANTINED,
    },
    PromotionState.RETIRED: set(),
    PromotionState.REJECTED: set(),
    PromotionState.QUARANTINED: set(),
}


def validate_transition_and_gates(
    current_state: PromotionState | None,
    target_state: PromotionState,
    payload: PromotionIdentityPayload,
) -> None:
    """Validate that the state transition is valid and all required gates are satisfied.

    Raises
    ------
    PromotionGateError
        If the state transition is forbidden or gate requirements are not met.
    """
    payload.validate()

    # Rule: Terminal states check
    if current_state is not None and current_state.is_terminal():
        raise PromotionGateError(
            f"Cannot transition from terminal state '{current_state.value}'",
            context={
                "current_state": current_state.value,
                "target_state": target_state.value,
                "model_artifact_id": payload.model_artifact_id,
            },
        )

    # Rule: State transition matrix check
    allowed = ALLOWED_TRANSITIONS.get(current_state, set())
    if target_state not in allowed:
        current_str = current_state.value if current_state else "NEW_ARTIFACT"
        raise PromotionGateError(
            f"Invalid promotion transition from '{current_str}' to '{target_state.value}'",
            context={
                "current_state": current_str,
                "target_state": target_state.value,
                "model_artifact_id": payload.model_artifact_id,
            },
        )

    # Rule: Gate checks for PAPER_APPROVED
    if target_state == PromotionState.PAPER_APPROVED:
        if not payload.evidence_reference or not payload.evidence_reference.strip():
            raise PromotionGateError(
                "PAPER_APPROVED promotion requires a non-empty scientific review or evidence reference",
                context={"model_artifact_id": payload.model_artifact_id},
            )

    # Rule: Gate checks for LIVE_APPROVED
    if target_state == PromotionState.LIVE_APPROVED:
        # Must have owner authority
        auth = payload.approving_authority.strip().lower()
        if "owner" not in auth:
            raise PromotionGateError(
                "LIVE_APPROVED promotion requires owner authority",
                context={
                    "model_artifact_id": payload.model_artifact_id,
                    "approving_authority": payload.approving_authority,
                },
            )

        # Must have prospective paper observation reference
        if (
            not payload.paper_observation_reference
            or not payload.paper_observation_reference.strip()
        ):
            raise PromotionGateError(
                "LIVE_APPROVED promotion requires prospective paper observation evaluation reference",
                context={"model_artifact_id": payload.model_artifact_id},
            )
