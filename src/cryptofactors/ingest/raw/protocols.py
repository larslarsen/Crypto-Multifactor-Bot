"""Catalog boundary protocol for accepted raw objects and failed acquisitions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Protocol

from cryptofactors.ingest.raw.models import AcquisitionMetadata, FailedAcquisitionRecord


class RawObjectCatalog(Protocol):
    """Catalog operations used by the raw-object writer.

    Implementations must never create an accepted ``raw_object`` row that points
    at partial or unverified bytes. Registration is called only after atomic
    publication (or identical-byte confirmation).
    """

    def ensure_source(
        self,
        source_id: str,
        *,
        source_type: str = "external",
        config: Mapping[str, Any] | None = None,
    ) -> None:
        """Ensure a ``source`` row exists for foreign-key integrity."""
        ...

    def get_accepted_by_sha256(self, sha256: str) -> Mapping[str, Any] | None:
        """Return accepted raw_object row fields, or None."""
        ...

    def register_accepted(
        self,
        *,
        raw_object_id: str,
        sha256: str,
        byte_size: int,
        storage_uri: str,
        metadata: AcquisitionMetadata,
    ) -> bool:
        """Insert or confirm the accepted catalog row.

        Returns True if a new row was inserted; False if an identical accepted
        row already existed (idempotent retry).
        """
        ...

    def record_failed_acquisition(
        self,
        *,
        source_id: str,
        error_message: str,
        request: Mapping[str, Any],
        command: str = "raw_acquire",
        run_id: str | None = None,
        recorded_at: datetime | None = None,
    ) -> FailedAcquisitionRecord:
        """Record a failed acquisition without registering an accepted raw object."""
        ...
