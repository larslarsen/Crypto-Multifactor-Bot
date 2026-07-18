"""Typed models for raw-object publication and reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class RawObjectStoreConfig:
    """Filesystem layout for the content-addressed raw store.

    Temporary files live under ``root / temp_dirname`` only.
    Accepted objects live under ``root / 'raw' / 'sha256' / ..``.
    """

    root: Path
    temp_dirname: str = "raw_tmp"
    object_prefix: str = "raw/sha256"

    def temp_dir(self) -> Path:
        return self.root / self.temp_dirname

    def objects_root(self) -> Path:
        return self.root / Path(self.object_prefix)


@dataclass(frozen=True, slots=True)
class AcquisitionMetadata:
    """Source/request/response metadata — separate from content identity."""

    source_id: str
    request: Mapping[str, Any] = field(default_factory=dict)
    response_metadata: Mapping[str, Any] = field(default_factory=dict)
    original_name: str | None = None
    source_checksum: str | None = None
    acquired_at: datetime | None = None
    event_start: datetime | None = None
    event_end: datetime | None = None
    status: str = "ACQUIRED"


@dataclass(frozen=True, slots=True)
class PublishResult:
    """Successful first-time publication of accepted bytes + catalog row."""

    raw_object_id: str
    sha256: str
    byte_size: int
    storage_path: Path
    storage_uri: str
    reused_existing: bool
    catalog_registered: bool


@dataclass(frozen=True, slots=True)
class IdempotentDuplicateResult:
    """Identical bytes already present; no overwrite; catalog row confirmed."""

    raw_object_id: str
    sha256: str
    byte_size: int
    storage_path: Path
    storage_uri: str
    catalog_registered: bool
    was_already_registered: bool


@dataclass(frozen=True, slots=True)
class FailedAcquisitionRecord:
    """Failed acquisition attempt with no accepted raw object."""

    run_id: str
    source_id: str
    status: str
    error_message: str
    request: Mapping[str, Any]
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class OrphanTempCandidate:
    path: Path
    size_bytes: int
    age_seconds: float
    stale: bool
    removed: bool
    reason: str


@dataclass(frozen=True, slots=True)
class OrphanReconciliationReport:
    temp_dir: Path
    dry_run: bool
    min_age_seconds: float
    scanned: int
    stale_candidates: int
    removed: int
    preserved_recent: int
    preserved_non_matching: int
    candidates: tuple[OrphanTempCandidate, ...]
