"""Catalog boundary protocol for content objects and acquisition provenance."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence

from cryptofactors.ingest.raw.models import (
    AcquisitionMetadata,
    ChecksumVerification,
    FailedAcquisitionRecord,
    PublicationReceipt,
)


class RawObjectCatalog(Protocol):
    """Catalog operations for content identity and acquisition provenance.

    Accepted ``raw_object`` rows represent immutable bytes only (unique by SHA-256).
    Each retrieval attempt is a distinct ``raw_acquisition`` row.
    """

    def ensure_source(
        self,
        source_id: str,
        *,
        source_type: str = "external",
        config: Mapping[str, Any] | None = None,
    ) -> None: ...

    def get_content_by_sha256(self, sha256: str) -> Mapping[str, Any] | None:
        """Return accepted content row fields, or None."""
        ...

    def get_acquisition(self, acquisition_id: str) -> Mapping[str, Any] | None: ...

    def list_acquisitions_for_object(self, raw_object_id: str) -> Sequence[Mapping[str, Any]]: ...

    def register_publication(
        self,
        *,
        receipt: PublicationReceipt,
        metadata: AcquisitionMetadata,
        checksum_verification: ChecksumVerification,
        store_root: str,
        object_prefix: str | None = None,
    ) -> tuple[bool, bool]:
        """Register content (if new) and acquisition from a verified publication receipt.

        Returns ``(content_inserted, acquisition_inserted)``.
        Idempotent only when the same acquisition_id is a genuine compatible retry.
        """
        ...

    def record_failed_acquisition(
        self,
        *,
        metadata: AcquisitionMetadata,
        error_message: str,
        checksum_verification: ChecksumVerification = ChecksumVerification.ABSENT,
        recorded_at: datetime | None = None,
    ) -> FailedAcquisitionRecord:
        """Record a failed acquisition with raw_object_id NULL."""
        ...
