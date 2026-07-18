"""Ingest-layer primitives (RAW-001: content-addressed raw object writer)."""

from __future__ import annotations

from cryptofactors.ingest.raw import (
    AcquisitionMetadata,
    CorruptDestinationError,
    FailedAcquisitionRecord,
    HashMismatchError,
    IdempotentDuplicateResult,
    InterruptedWriteError,
    InvalidChunkError,
    OrphanReconciliationReport,
    PublishResult,
    RawObjectCatalog,
    RawObjectStoreConfig,
    RawObjectWriter,
    RawStoreError,
    RecoverableCatalogRegistrationError,
    SqliteRawObjectCatalog,
    content_addressed_relative_path,
    reconcile_orphan_temps,
)

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
