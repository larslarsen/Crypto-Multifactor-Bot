"""Content-addressed immutable raw-object store (RAW-001)."""

from __future__ import annotations

from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.errors import (
    CorruptDestinationError,
    HashMismatchError,
    InterruptedWriteError,
    InvalidChunkError,
    RawStoreError,
    RecoverableCatalogRegistrationError,
)
from cryptofactors.ingest.raw.models import (
    AcquisitionMetadata,
    FailedAcquisitionRecord,
    IdempotentDuplicateResult,
    OrphanReconciliationReport,
    PublishResult,
    RawObjectStoreConfig,
)
from cryptofactors.ingest.raw.paths import content_addressed_relative_path
from cryptofactors.ingest.raw.protocols import RawObjectCatalog
from cryptofactors.ingest.raw.reconcile import reconcile_orphan_temps
from cryptofactors.ingest.raw.writer import RawObjectWriter

__all__ = [
    "AcquisitionMetadata",
    "CorruptDestinationError",
    "FailedAcquisitionRecord",
    "HashMismatchError",
    "IdempotentDuplicateResult",
    "InterruptedWriteError",
    "InvalidChunkError",
    "OrphanReconciliationReport",
    "PublishResult",
    "RawObjectCatalog",
    "RawObjectStoreConfig",
    "RawObjectWriter",
    "RawStoreError",
    "RecoverableCatalogRegistrationError",
    "SqliteRawObjectCatalog",
    "content_addressed_relative_path",
    "reconcile_orphan_temps",
]
