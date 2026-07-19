"""Typed models for REF-001 point-in-time reference master."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence


class VenueType(str, Enum):
    CEX = "CEX"
    DEX = "DEX"
    INDEX = "INDEX"
    OTHER = "OTHER"


class AssetClass(str, Enum):
    CRYPTO = "CRYPTO"
    FIAT = "FIAT"
    STABLE = "STABLE"
    DERIVATIVE_UNDERLIER = "DERIVATIVE_UNDERLIER"
    OTHER = "OTHER"


class InstrumentType(str, Enum):
    SPOT = "SPOT"
    PERPETUAL = "PERPETUAL"
    FUTURE = "FUTURE"
    OPTION = "OPTION"
    INDEX = "INDEX"
    OTHER = "OTHER"


class TargetKind(str, Enum):
    ASSET = "ASSET"
    INSTRUMENT = "INSTRUMENT"
    VENUE = "VENUE"


class ListingEventType(str, Enum):
    LIST = "LIST"
    DELIST = "DELIST"
    SUSPEND = "SUSPEND"
    RESUME = "RESUME"


class MigrationEventType(str, Enum):
    REDENOMINATION = "REDENOMINATION"
    CONTRACT_MIGRATION = "CONTRACT_MIGRATION"
    ASSET_SPLIT = "ASSET_SPLIT"
    ASSET_MERGE = "ASSET_MERGE"
    OTHER = "OTHER"


class AmbiguityStatus(str, Enum):
    QUEUED = "QUEUED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class ResolutionOutcome(str, Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"
    QUEUED = "QUEUED"


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware UTC")
    return dt.astimezone(timezone.utc)


def dt_to_iso(dt: datetime) -> str:
    return ensure_utc(dt).isoformat().replace("+00:00", "Z")


def iso_to_dt(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError("stored timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


def normalize_alias(text: str) -> str:
    return " ".join(text.strip().split()).upper()


@dataclass(frozen=True, slots=True)
class BiTemporalWindow:
    """Half-open [valid_from, valid_to) x [known_from, known_to)."""

    valid_from: datetime
    known_from: datetime
    valid_to: datetime | None = None
    known_to: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "valid_from", ensure_utc(self.valid_from))
        object.__setattr__(self, "known_from", ensure_utc(self.known_from))
        if self.valid_to is not None:
            object.__setattr__(self, "valid_to", ensure_utc(self.valid_to))
            if self.valid_to <= self.valid_from:
                raise ValueError("valid_to must be > valid_from")
        if self.known_to is not None:
            object.__setattr__(self, "known_to", ensure_utc(self.known_to))
            if self.known_to <= self.known_from:
                raise ValueError("known_to must be > known_from")

    def active_at(self, *, decision_time: datetime, knowledge_time: datetime) -> bool:
        d = ensure_utc(decision_time)
        k = ensure_utc(knowledge_time)
        if d < self.valid_from:
            return False
        if self.valid_to is not None and d >= self.valid_to:
            return False
        if k < self.known_from:
            return False
        if self.known_to is not None and k >= self.known_to:
            return False
        return True


@dataclass(frozen=True, slots=True)
class Venue:
    venue_id: str
    venue_code: str
    display_name: str
    venue_type: VenueType
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Asset:
    asset_id: str
    asset_class: AssetClass
    display_name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Instrument:
    instrument_id: str
    asset_id: str
    venue_id: str
    instrument_type: InstrumentType
    created_at: datetime
    base_asset_id: str | None = None
    quote_asset_id: str | None = None


@dataclass(frozen=True, slots=True)
class InstrumentVersion:
    instrument_version_id: str
    instrument_id: str
    version_seq: int
    contract_spec: Mapping[str, Any]
    window: BiTemporalWindow
    supersedes_version_id: str | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AliasRecord:
    alias_id: str
    alias_text: str
    alias_text_norm: str
    target_kind: TargetKind
    target_id: str
    window: BiTemporalWindow
    venue_id: str | None = None
    confidence: float = 1.0
    evidence: Mapping[str, Any] = field(default_factory=dict)
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class ListingEvent:
    listing_event_id: str
    instrument_id: str
    venue_id: str
    event_type: ListingEventType
    window: BiTemporalWindow
    evidence: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MigrationEvent:
    migration_event_id: str
    event_type: MigrationEventType
    from_kind: TargetKind
    from_id: str
    to_kind: TargetKind
    to_id: str
    window: BiTemporalWindow
    ratio_num: float | None = None
    ratio_den: float | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AmbiguityCase:
    case_id: str
    alias_text: str
    alias_text_norm: str
    decision_time: datetime
    knowledge_time: datetime
    status: AmbiguityStatus
    candidates: Sequence[Mapping[str, Any]]
    created_at: datetime
    updated_at: datetime
    venue_id: str | None = None
    resolution_target_kind: TargetKind | None = None
    resolution_target_id: str | None = None
    resolution_note: str | None = None


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    outcome: ResolutionOutcome
    alias_text: str
    alias_text_norm: str
    decision_time: datetime
    knowledge_time: datetime
    target_kind: TargetKind | None = None
    target_id: str | None = None
    confidence: float | None = None
    candidates: tuple[AliasRecord, ...] = ()
    case_id: str | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)
