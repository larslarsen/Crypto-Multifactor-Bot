"""Typed models for raw-object publication, acquisition, and reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


class ChecksumAlgorithm(str, Enum):
    """Supported provider checksum algorithms. SHA-256 only for now."""

    SHA256 = "sha256"


class ChecksumVerification(str, Enum):
    """Explicit outcome of provider checksum evaluation."""

    ABSENT = "absent"
    VERIFIED = "verified"
    MISMATCH = "mismatch"
    UNSUPPORTED = "unsupported"
    MALFORMED = "malformed"
    FAILED = "failed"


class AcquisitionStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REGISTRATION_PENDING = "REGISTRATION_PENDING"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class RawObjectStoreConfig:
    """Filesystem layout for the content-addressed raw store.

    Temporary files live under ``root / temp_dirname`` only.
    Accepted objects live under ``root / object_prefix / ..``.
    Paths are validated at construction time (no absolute prefixes, no traversal,
    no escape from root). Symlinked storage roots are rejected when resolved.
    """

    root: Path
    temp_dirname: str = "raw_tmp"
    object_prefix: str = "raw/sha256"

    def __post_init__(self) -> None:
        from cryptofactors.ingest.raw.paths import validate_store_config

        validate_store_config(self)

    def temp_dir(self) -> Path:
        return (self.root / self.temp_dirname).resolve()

    def objects_root(self) -> Path:
        return (self.root / Path(self.object_prefix)).resolve()


@dataclass(frozen=True, slots=True)
class ProviderChecksum:
    """Explicit provider checksum evidence (distinct from content SHA-256 identity)."""

    algorithm: str
    value: str


@dataclass(frozen=True, slots=True)
class AcquisitionMetadata:
    """Source/request/response provenance for one retrieval attempt.

    Separate from content identity (SHA-256). Each attempt has its own
    ``acquisition_id`` (generated if omitted).
    """

    source_id: str
    acquisition_id: str | None = None
    request: Mapping[str, Any] = field(default_factory=dict)
    response_metadata: Mapping[str, Any] = field(default_factory=dict)
    original_name: str | None = None
    provider_checksum: ProviderChecksum | None = None
    acquired_at: datetime | None = None
    event_start: datetime | None = None
    event_end: datetime | None = None
    # Requested object status for the content row when first published.
    # VERIFIED is only allowed when checksum_verification is verified.
    content_status: str = "ACQUIRED"


@dataclass(frozen=True, slots=True)
class PublicationReceipt:
    """Typed evidence that bytes are published at a verified content path.

    Catalog registration requires a receipt; it cannot be confused with
    unverified acquisition metadata. Identity fields must agree with the
    configured object prefix and canonical layout
    ``<object_prefix>/<H[0:2]>/<H[2:4]>/<H>``.
    """

    raw_object_id: str
    sha256: str
    byte_size: int
    storage_path: Path
    storage_uri: str
    object_prefix: str
    reused_existing: bool
    verified_regular_file: bool
    verified_size: bool
    verified_sha256: bool

    def is_complete(self) -> bool:
        return (
            self.verified_regular_file
            and self.verified_size
            and self.verified_sha256
            and self.byte_size >= 0
            and len(self.sha256) == 64
            and bool(self.object_prefix)
            and bool(self.storage_uri)
            and bool(self.raw_object_id)
        )


@dataclass(frozen=True, slots=True)
class PublishResult:
    """Successful write with content publication and acquisition registration."""

    acquisition_id: str
    raw_object_id: str
    sha256: str
    byte_size: int
    storage_path: Path
    storage_uri: str
    reused_existing: bool
    catalog_registered: bool
    checksum_verification: ChecksumVerification
    new_acquisition: bool


@dataclass(frozen=True, slots=True)
class IdempotentDuplicateResult:
    """Identical bytes already on disk; acquisition recorded or confirmed."""

    acquisition_id: str
    raw_object_id: str
    sha256: str
    byte_size: int
    storage_path: Path
    storage_uri: str
    catalog_registered: bool
    content_already_present: bool
    acquisition_already_registered: bool
    checksum_verification: ChecksumVerification


@dataclass(frozen=True, slots=True)
class FailedAcquisitionRecord:
    """Failed acquisition attempt with no accepted raw-object reference."""

    acquisition_id: str
    source_id: str
    status: str
    error_message: str
    request: Mapping[str, Any]
    checksum_algorithm: str | None
    checksum_value: str | None
    checksum_verification: ChecksumVerification
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class OrphanTempCandidate:
    path: Path
    size_bytes: int
    age_seconds: float
    active: bool
    stale: bool
    removed: bool
    reason: str


@dataclass(frozen=True, slots=True)
class OrphanReconciliationReport:
    temp_dir: Path
    dry_run: bool
    min_age_seconds: float
    scanned: int
    active_locked: int
    preserved_recent: int
    stale_candidates: int
    removed: int
    remove_failed: int
    preserved_non_matching: int
    candidates: tuple[OrphanTempCandidate, ...]
