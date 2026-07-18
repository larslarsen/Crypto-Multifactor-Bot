"""Content-addressed immutable raw-object store (RAW-001)."""

from __future__ import annotations

from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog, verify_publication_receipt
from cryptofactors.ingest.raw.errors import (
    AcquisitionConflictError,
    CatalogRegistrationError,
    ChecksumError,
    CorruptDestinationError,
    DurabilityError,
    HashMismatchError,
    InterruptedWriteError,
    InvalidChunkError,
    PathSafetyError,
    PublicationError,
    RawStoreError,
    RecoverableCatalogRegistrationError,
)
from cryptofactors.ingest.raw.models import (
    AcquisitionMetadata,
    AcquisitionStatus,
    ChecksumAlgorithm,
    ChecksumVerification,
    FailedAcquisitionRecord,
    IdempotentDuplicateResult,
    OrphanReconciliationReport,
    ProviderChecksum,
    PublicationReceipt,
    PublishResult,
    RawObjectStoreConfig,
)
from cryptofactors.ingest.raw.paths import content_addressed_relative_path
from cryptofactors.ingest.raw.protocols import RawObjectCatalog
from cryptofactors.ingest.raw.reconcile import reconcile_orphan_temps
from cryptofactors.ingest.raw.writer import RawObjectWriter

__all__ = [
    "AcquisitionConflictError",
    "AcquisitionMetadata",
    "AcquisitionStatus",
    "CatalogRegistrationError",
    "ChecksumAlgorithm",
    "ChecksumError",
    "ChecksumVerification",
    "CorruptDestinationError",
    "DurabilityError",
    "FailedAcquisitionRecord",
    "HashMismatchError",
    "IdempotentDuplicateResult",
    "InterruptedWriteError",
    "InvalidChunkError",
    "OrphanReconciliationReport",
    "PathSafetyError",
    "ProviderChecksum",
    "PublicationError",
    "PublicationReceipt",
    "PublishResult",
    "RawObjectCatalog",
    "RawObjectStoreConfig",
    "RawObjectWriter",
    "RawStoreError",
    "RecoverableCatalogRegistrationError",
    "SqliteRawObjectCatalog",
    "content_addressed_relative_path",
    "reconcile_orphan_temps",
    "verify_publication_receipt",
]
