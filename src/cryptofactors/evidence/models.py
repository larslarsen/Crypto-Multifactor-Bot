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


class EvidenceIntegrity(StrictModel):
    point_in_time: IntegrityGrade
    causal_split: IntegrityGrade
    reproduction: ReproductionGrade
    costs: IntegrityGrade
    universe: IntegrityGrade
    independence: IndependenceClass


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
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class HypothesisDecision(StrictModel):
    decision_id: str
    hypothesis_id: str = Field(pattern=r"^H-[0-9]{3,}$")
    hypothesis_version: int = Field(ge=1)
    action: str
    lifecycle: HypothesisLifecycle
    verdict: HypothesisVerdict
    evidence_snapshot_id: str
    reason: str = Field(min_length=3)
    actor: str = Field(min_length=1)
    event_at: datetime
    supersedes_decision_id: str | None = None
