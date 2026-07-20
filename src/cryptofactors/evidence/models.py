from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HypothesisLifecycle(StrEnum):
    DRAFT = "DRAFT"
    REGISTERED = "REGISTERED"
    ACTIVE = "ACTIVE"
    DEFERRED = "DEFERRED"
    CLOSED = "CLOSED"


class HypothesisVerdict(StrEnum):
    UNTESTED = "UNTESTED"
    PRELIMINARY = "PRELIMINARY"
    SUPPORTED = "SUPPORTED"
    REPLICATED = "REPLICATED"
    NOT_REPLICATED = "NOT_REPLICATED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    QUARANTINED = "QUARANTINED"


class EvidenceKind(StrEnum):
    LITERATURE_PUBLISHED = "LITERATURE_PUBLISHED"
    LITERATURE_WORKING = "LITERATURE_WORKING"
    LEGACY_RESULT = "LEGACY_RESULT"
    EXPERIMENT_RESULT = "EXPERIMENT_RESULT"
    DATA_AUDIT = "DATA_AUDIT"
    THEORY = "THEORY"
    OPERATIONAL_OBSERVATION = "OPERATIONAL_OBSERVATION"


class EvidenceDirection(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    QUALIFIES = "QUALIFIES"
    NEUTRAL = "NEUTRAL"


class EvidenceRelevance(StrEnum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    CONTEXT = "CONTEXT"


class IntegrityGrade(StrEnum):
    UNKNOWN = "UNKNOWN"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    PASS = "PASS"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ReproductionGrade(StrEnum):
    NONE = "NONE"
    PARTIAL = "PARTIAL"
    FULL = "FULL"


class IndependenceClass(StrEnum):
    SAME_PIPELINE = "SAME_PIPELINE"
    INTERNAL_INDEPENDENT = "INTERNAL_INDEPENDENT"
    EXTERNAL = "EXTERNAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DecisionAction(StrEnum):
    REGISTER = "REGISTER"
    SET_VERDICT = "SET_VERDICT"
    DEFER = "DEFER"
    REOPEN = "REOPEN"
    CLOSE = "CLOSE"
    CORRECT = "CORRECT"


_NON_PROMOTION_KINDS = frozenset(
    {
        EvidenceKind.LITERATURE_PUBLISHED,
        EvidenceKind.LITERATURE_WORKING,
        EvidenceKind.LEGACY_RESULT,
    }
)

_ACTIONS_REQUIRING_SUPERSEDES = frozenset(
    {DecisionAction.CORRECT.value, DecisionAction.REOPEN.value}
)


class EvidenceIntegrity(StrictModel):
    point_in_time: IntegrityGrade
    causal_split: IntegrityGrade
    reproduction: ReproductionGrade
    costs: IntegrityGrade
    universe: IntegrityGrade
    independence: IndependenceClass

    def blocks_promotion(self) -> bool:
        return (
            self.point_in_time is IntegrityGrade.FAIL
            or self.causal_split is IntegrityGrade.FAIL
        )


class HypothesisVersion(StrictModel):
    hypothesis_id: str = Field(pattern=r"^H-[0-9]{3,}$")
    version: int = Field(ge=1)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=3)
    statement: str = Field(min_length=20)
    mechanism: str = Field(min_length=10)
    expected_sign: str
    phase: str
    primary_metric: str = Field(min_length=3)
    advancement_rule: str = Field(min_length=10)
    rejection_rule: str = Field(min_length=10)
    known_confounders: tuple[str, ...] = ()
    required_dataset_types: tuple[str, ...] = ()
    # Deterministic seed/provenance fields stored in immutable version content.
    sprint_002_source_basis: str | None = None
    preregistered_at: datetime | None = None

    @field_validator("preregistered_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("preregistered_at must be timezone-aware")
        return value


class EvidenceItem(StrictModel):
    evidence_id: str = Field(pattern=r"^EV-[A-Z0-9-]+$")
    kind: EvidenceKind
    title: str = Field(min_length=3)
    summary: str = Field(min_length=3)
    source_ref: str = Field(min_length=1)
    artifact_uri: str | None = None
    observed_at: datetime | None = None
    registered_at: datetime
    registered_by: str = Field(min_length=1)
    # Caller may supply; repository verifies against canonical body.
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("observed_at", "registered_at")
    @classmethod
    def require_tz(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("datetime fields must be timezone-aware")
        return value

    def body_for_hash(self) -> dict[str, Any]:
        """Canonical evidence body excluding the hash field itself.

        Repository normalizes timestamps to fixed-width UTC before hashing.
        Callers should prefer repository verification rather than hashing this
        payload alone when timestamps may omit microseconds.
        """
        payload = self.model_dump(mode="json")
        payload.pop("content_sha256", None)
        return payload


class HypothesisEvidenceLink(StrictModel):
    hypothesis_id: str = Field(pattern=r"^H-[0-9]{3,}$")
    hypothesis_version: int = Field(ge=1)
    evidence_id: str = Field(pattern=r"^EV-[A-Z0-9-]+$")
    direction: EvidenceDirection
    relevance: EvidenceRelevance
    rationale: str = Field(min_length=1)
    integrity: EvidenceIntegrity
    registered_at: datetime
    registered_by: str = Field(min_length=1)

    @field_validator("registered_at")
    @classmethod
    def require_tz(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("registered_at must be timezone-aware")
        return value


class EvidenceSnapshot(StrictModel):
    snapshot_id: str = Field(min_length=1)
    hypothesis_id: str = Field(pattern=r"^H-[0-9]{3,}$")
    hypothesis_version: int = Field(ge=1)
    as_of: datetime
    generated_at: datetime
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    artifact_uri: str | None = None
    links: tuple[dict[str, Any], ...] = ()

    @field_validator("as_of", "generated_at")
    @classmethod
    def require_tz(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("snapshot datetimes must be timezone-aware")
        return value


class HypothesisDecision(StrictModel):
    decision_id: str = Field(min_length=1)
    hypothesis_id: str = Field(pattern=r"^H-[0-9]{3,}$")
    hypothesis_version: int = Field(ge=1)
    action: str = Field(min_length=1)
    lifecycle: HypothesisLifecycle
    verdict: HypothesisVerdict
    evidence_snapshot_id: str = Field(min_length=1)
    reason: str = Field(min_length=3)
    actor: str = Field(min_length=1)
    event_at: datetime
    supersedes_decision_id: str | None = None

    @field_validator("event_at")
    @classmethod
    def require_tz(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("event_at must be timezone-aware")
        return value

    def is_promotion_verdict(self) -> bool:
        return self.verdict in {
            HypothesisVerdict.SUPPORTED,
            HypothesisVerdict.REPLICATED,
        }

    def normalized_action(self) -> str:
        return self.action.strip().upper()
