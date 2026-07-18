"""Typed canonical dataset-manifest models (MAN-001)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence


class DependencyKind(str, Enum):
    RAW_OBJECT = "RAW_OBJECT"
    DATASET = "DATASET"


class QualityStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"


class PublicationStatus(str, Enum):
    REGISTERED = "REGISTERED"
    SUPERSEDED = "SUPERSEDED"


class VerificationSeverity(str, Enum):
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    FAILURE = "FAILURE"


@dataclass(frozen=True, slots=True)
class TransformSpec:
    name: str
    version: str


@dataclass(frozen=True, slots=True)
class SchemaIdentity:
    """Schema identity distinct from free-form schema_version string."""

    name: str
    version: str
    fingerprint: str | None = None  # optional content hash of schema definition


@dataclass(frozen=True, slots=True)
class CodeIdentity:
    commit: str
    # Optional lock/file identity for reproducibility.
    lock_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class ConfigIdentity:
    config_sha256: str


@dataclass(frozen=True, slots=True)
class DependencyRef:
    id: str
    kind: DependencyKind
    role: str


@dataclass(frozen=True, slots=True)
class OutputFileSpec:
    """Declared output before/after verification.

    ``relative_path`` is a locator under the dataset directory (not identity).
    Identity uses sha256 + rows + bytes + partition.
    """

    relative_path: str
    sha256: str
    rows: int
    bytes: int
    partition: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CoverageWindow:
    event_start: datetime | None = None
    event_end: datetime | None = None
    availability_start: datetime | None = None
    availability_end: datetime | None = None


@dataclass(frozen=True, slots=True)
class DatasetStatistics:
    row_count: int
    byte_size: int


@dataclass(frozen=True, slots=True)
class PublicationMetadata:
    """Non-identity publication bookkeeping (created_at is not fingerprinted)."""

    created_at: datetime
    publisher: str = "cryptofactors.catalog.dataset"
    publisher_version: str = "1"


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    """Full immutable dataset manifest including assigned dataset_id."""

    dataset_id: str
    dataset_type: str
    schema: SchemaIdentity
    transform: TransformSpec
    code: CodeIdentity
    config: ConfigIdentity
    dependencies: tuple[DependencyRef, ...]
    files: tuple[OutputFileSpec, ...]
    statistics: DatasetStatistics
    coverage: CoverageWindow
    quality_status: QualityStatus
    quality_summary: Mapping[str, Any]
    publication: PublicationMetadata
    supersedes_dataset_id: str | None = None
    manifest_sha256: str = ""
    # schema_version convenience mirror of schema.version for catalog columns
    @property
    def schema_version(self) -> str:
        return self.schema.version


@dataclass(frozen=True, slots=True)
class DatasetStoreConfig:
    """Filesystem layout for immutable datasets."""

    root: Path
    temp_dirname: str = "datasets_tmp"
    object_prefix: str = "datasets/sha256"

    def __post_init__(self) -> None:
        from cryptofactors.catalog.dataset.paths import validate_dataset_store_config

        validate_dataset_store_config(self)

    def temp_dir(self) -> Path:
        return (self.root / self.temp_dirname).resolve()

    def datasets_root(self) -> Path:
        return (self.root / Path(self.object_prefix)).resolve()


@dataclass(frozen=True, slots=True)
class PublishPlan:
    """Inputs to the publisher before identity assignment."""

    dataset_type: str
    schema: SchemaIdentity
    transform: TransformSpec
    code: CodeIdentity
    config: ConfigIdentity
    dependencies: Sequence[DependencyRef]
    # Local paths of outputs keyed by relative_path inside dataset dir.
    output_sources: Mapping[str, Path]
    # Declared content identity for each output (must match streaming verification).
    output_specs: Sequence[OutputFileSpec]
    statistics: DatasetStatistics
    coverage: CoverageWindow
    quality_status: QualityStatus
    quality_summary: Mapping[str, Any] = field(default_factory=dict)
    supersedes_dataset_id: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DatasetPublishResult:
    dataset_id: str
    manifest_sha256: str
    dataset_path: Path
    manifest_uri: str
    reused_existing: bool
    catalog_registered: bool
    manifest: DatasetManifest


@dataclass(frozen=True, slots=True)
class VerificationFinding:
    code: str
    severity: VerificationSeverity
    message: str
    context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DatasetVerificationReport:
    dataset_id: str
    ok: bool
    findings: tuple[VerificationFinding, ...]
    manifest_sha256: str | None = None
    catalog_manifest_sha256: str | None = None
