"""Typed canonical dataset-manifest models (MAN-001)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence


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


class RowCountPolicy(str, Enum):
    """How declared row counts are treated when verifying outputs."""

    REQUIRE_VERIFIER = "require_verifier"
    """Caller must supply a row counter or receipt for every output."""

    ALLOW_UNVERIFIED_DECLARED = "allow_unverified_declared"
    """Explicit opt-in: declared rows are recorded but not observed/verified."""


@dataclass(frozen=True, slots=True)
class TransformSpec:
    name: str
    version: str


@dataclass(frozen=True, slots=True)
class SchemaIdentity:
    name: str
    version: str
    fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class CodeIdentity:
    commit: str
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
    """Output declaration. Logical relative_path is identity-bearing."""

    relative_path: str
    sha256: str
    rows: int
    bytes: int
    partition: Mapping[str, Any] = field(default_factory=dict)
    rows_verified: bool = False


@dataclass(frozen=True, slots=True)
class RowCountReceipt:
    """Verified observation of row count for one output (not a bare declaration)."""

    relative_path: str
    row_count: int
    verifier_name: str


class RowCounter(Protocol):
    def __call__(self, path: Path) -> int: ...


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
    """Mutable/bookkeeping publication metadata (not identity-bearing).

    ``created_at`` is catalog bookkeeping only and must not affect
    ``dataset_id`` or ``manifest_sha256``.
    """

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

    @property
    def schema_version(self) -> str:
        return self.schema.version


@dataclass(frozen=True, slots=True)
class DatasetStoreConfig:
    root: Path
    temp_dirname: str = "datasets_tmp"
    object_prefix: str = "datasets/sha256"
    # Concurrent-publication wait: losers poll until manifest.json appears.
    publication_wait_seconds: float = 30.0
    publication_initial_backoff_seconds: float = 0.01
    publication_max_backoff_seconds: float = 0.5

    def __post_init__(self) -> None:
        from cryptofactors.catalog.dataset.paths import validate_dataset_store_config

        validate_dataset_store_config(self)
        if self.publication_wait_seconds < 0:
            raise ValueError("publication_wait_seconds must be >= 0")
        if self.publication_initial_backoff_seconds <= 0:
            raise ValueError("publication_initial_backoff_seconds must be > 0")
        if self.publication_max_backoff_seconds < self.publication_initial_backoff_seconds:
            raise ValueError(
                "publication_max_backoff_seconds must be >= publication_initial_backoff_seconds"
            )

    def temp_dir(self) -> Path:
        return self.root / self.temp_dirname

    def datasets_root(self) -> Path:
        return self.root / Path(self.object_prefix)


@dataclass(frozen=True, slots=True)
class PublishPlan:
    dataset_type: str
    schema: SchemaIdentity
    transform: TransformSpec
    code: CodeIdentity
    config: ConfigIdentity
    dependencies: Sequence[DependencyRef]
    output_sources: Mapping[str, Path]
    output_specs: Sequence[OutputFileSpec]
    statistics: DatasetStatistics
    coverage: CoverageWindow
    quality_status: QualityStatus
    quality_summary: Mapping[str, Any] = field(default_factory=dict)
    supersedes_dataset_id: str | None = None
    created_at: datetime | None = None
    row_count_policy: RowCountPolicy = RowCountPolicy.REQUIRE_VERIFIER
    row_counters: Mapping[str, Callable[[Path], int]] = field(default_factory=dict)
    row_receipts: Mapping[str, RowCountReceipt] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DatasetPublicationReceipt:
    """Verified publication evidence required for catalog registration."""

    dataset_id: str
    manifest_sha256: str
    manifest_uri: str
    publication_uri: str
    dataset_path: Path
    verified_outputs: tuple[OutputFileSpec, ...]
    publication_verified: bool
    object_prefix: str
    dependencies: tuple[DependencyRef, ...]
    supersedes_dataset_id: str | None
    # Immutable catalog-facing fields from the verified manifest body.
    dataset_type: str
    schema: SchemaIdentity
    transform: TransformSpec
    code: CodeIdentity
    config: ConfigIdentity
    statistics: DatasetStatistics
    coverage: CoverageWindow
    quality_status: QualityStatus
    quality_summary: Mapping[str, Any]
    # Bookkeeping only (not used for identity agreement of immutable content).
    catalog_created_at: datetime

    def is_complete(self) -> bool:
        return (
            self.publication_verified
            and self.dataset_id.startswith("ds_")
            and len(self.manifest_sha256) == 64
            and bool(self.manifest_uri)
            and bool(self.publication_uri)
        )


@dataclass(frozen=True, slots=True)
class DatasetPublishResult:
    dataset_id: str
    manifest_sha256: str
    dataset_path: Path
    manifest_uri: str
    reused_existing: bool
    catalog_registered: bool
    manifest: DatasetManifest
    receipt: DatasetPublicationReceipt


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
    recomputed_dataset_id: str | None = None
