"""SQLite catalog: content-addressed raw_object + raw_acquisition provenance."""

from __future__ import annotations

import json
import os
import sqlite3
import stat as statmod
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from cryptofactors.ingest.raw.checksums import require_checksum_ok_for_verified_status
from cryptofactors.ingest.raw.errors import (
    CatalogRegistrationError,
    PathSafetyError,
    RawStoreError,
)
from cryptofactors.ingest.raw.models import (
    AcquisitionMetadata,
    ChecksumVerification,
    FailedAcquisitionRecord,
    PublicationReceipt,
)
from cryptofactors.ingest.raw.paths import (
    assert_regular_nonsymlink_file,
    validate_sha256_hex,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise RawStoreError("datetime must be timezone-aware UTC")
    return dt.astimezone(timezone.utc).isoformat()


def _dumps(value: Mapping[str, Any] | None) -> str:
    return json.dumps(
        dict(value or {}),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            piece = handle.read(chunk_size)
            if not piece:
                break
            digest.update(piece)
    return digest.hexdigest()


def verify_publication_receipt(receipt: PublicationReceipt, *, store_root: Path) -> None:
    """Fail closed unless the receipt points at a complete published object on disk."""
    if not receipt.is_complete():
        raise CatalogRegistrationError(
            "publication receipt is incomplete",
            context={"receipt": str(receipt)},
        )
    digest = validate_sha256_hex(receipt.sha256)
    path = Path(receipt.storage_path)
    root = Path(store_root).resolve()
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise CatalogRegistrationError(
            "publication path escapes store root",
            context={"path": str(path), "root": str(root)},
        ) from exc

    if path.is_symlink():
        raise CatalogRegistrationError(
            "publication path must not be a symlink",
            context={"path": str(path)},
        )
    if not path.exists():
        raise CatalogRegistrationError(
            "publication path missing",
            context={"path": str(path)},
        )
    try:
        assert_regular_nonsymlink_file(path, label="publication path")
    except PathSafetyError as exc:
        raise CatalogRegistrationError(str(exc), context=exc.context) from exc

    st = os.lstat(path)
    if not statmod.S_ISREG(st.st_mode):
        raise CatalogRegistrationError(
            "publication path is not a regular file",
            context={"path": str(path)},
        )
    if st.st_size != receipt.byte_size:
        raise CatalogRegistrationError(
            "publication size mismatch",
            context={
                "path": str(path),
                "expected": receipt.byte_size,
                "actual": st.st_size,
            },
        )
    actual = _sha256_file(path)
    if actual != digest:
        raise CatalogRegistrationError(
            "publication SHA-256 mismatch",
            context={"path": str(path), "expected": digest, "actual": actual},
        )


class SqliteRawObjectCatalog:
    """Catalog boundary: raw_object (content) + raw_acquisition (provenance)."""

    def __init__(
        self, database: Path | str, *, connection: sqlite3.Connection | None = None
    ) -> None:
        self._owned = connection is None
        if connection is not None:
            self._conn = connection
        else:
            self._conn = sqlite3.connect(str(database))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA busy_timeout = 5000")

    def close(self) -> None:
        if self._owned:
            self._conn.close()

    def ensure_source(
        self,
        source_id: str,
        *,
        source_type: str = "external",
        config: Mapping[str, Any] | None = None,
    ) -> None:
        if not source_id:
            raise RawStoreError("source_id must be non-empty")
        now = _iso(_utc_now())
        self._conn.execute(
            """
            INSERT INTO source (source_id, source_type, official_url, terms_class, config_json, created_at)
            VALUES (?, ?, NULL, NULL, ?, ?)
            ON CONFLICT(source_id) DO NOTHING
            """,
            (source_id, source_type, _dumps(config), now),
        )
        self._conn.commit()

    def get_content_by_sha256(self, sha256: str) -> Mapping[str, Any] | None:
        digest = validate_sha256_hex(sha256)
        row = self._conn.execute(
            """
            SELECT raw_object_id, source_id, sha256, byte_size, storage_uri, status, acquired_at
            FROM raw_object
            WHERE sha256 = ?
            """,
            (digest,),
        ).fetchone()
        return dict(row) if row is not None else None

    # Back-compat alias used by earlier tests/helpers
    def get_accepted_by_sha256(self, sha256: str) -> Mapping[str, Any] | None:
        return self.get_content_by_sha256(sha256)

    def get_acquisition(self, acquisition_id: str) -> Mapping[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM raw_acquisition WHERE acquisition_id = ?",
            (acquisition_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def list_acquisitions_for_object(
        self, raw_object_id: str
    ) -> Sequence[Mapping[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM raw_acquisition
            WHERE raw_object_id = ?
            ORDER BY acquired_at, acquisition_id
            """,
            (raw_object_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def register_publication(
        self,
        *,
        receipt: PublicationReceipt,
        metadata: AcquisitionMetadata,
        checksum_verification: ChecksumVerification,
        store_root: str,
    ) -> tuple[bool, bool]:
        verify_publication_receipt(receipt, store_root=Path(store_root))
        if not metadata.source_id:
            raise CatalogRegistrationError("source_id required")

        content_status = require_checksum_ok_for_verified_status(
            metadata.content_status, checksum_verification
        )
        digest = validate_sha256_hex(receipt.sha256)
        acquired = metadata.acquired_at or _utc_now()
        acquisition_id = metadata.acquisition_id or f"acq_{uuid.uuid4().hex}"
        now = _utc_now()

        self.ensure_source(metadata.source_id)

        existing_acq = self.get_acquisition(acquisition_id)
        if existing_acq is not None:
            # Idempotent retry of the same acquisition ID.
            if (
                existing_acq.get("raw_object_id") == receipt.raw_object_id
                and existing_acq.get("status") == "SUCCEEDED"
            ):
                return (False, False)
            if existing_acq.get("status") == "REGISTRATION_PENDING":
                # Complete pending registration.
                pass
            elif existing_acq.get("status") == "SUCCEEDED":
                raise CatalogRegistrationError(
                    "acquisition_id already bound to a different object",
                    context={
                        "acquisition_id": acquisition_id,
                        "existing": dict(existing_acq),
                    },
                )

        algo = None
        cval = None
        if metadata.provider_checksum is not None:
            algo = metadata.provider_checksum.algorithm
            cval = metadata.provider_checksum.value

        content_inserted = False
        existing_content = self.get_content_by_sha256(digest)
        if existing_content is None:
            try:
                self._conn.execute(
                    """
                    INSERT INTO raw_object (
                        raw_object_id, source_id, sha256, byte_size, storage_uri,
                        original_name, request_json, response_metadata_json, source_checksum,
                        acquired_at, event_start, event_end, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.raw_object_id,
                        metadata.source_id,
                        digest,
                        receipt.byte_size,
                        receipt.storage_uri,
                        # Provenance columns on raw_object are legacy mirrors of first acquisition.
                        metadata.original_name,
                        _dumps(metadata.request),
                        _dumps(metadata.response_metadata),
                        cval,
                        _iso(acquired),
                        _iso(metadata.event_start) if metadata.event_start else None,
                        _iso(metadata.event_end) if metadata.event_end else None,
                        content_status,
                    ),
                )
                content_inserted = True
            except sqlite3.IntegrityError:
                self._conn.rollback()
                existing_content = self.get_content_by_sha256(digest)
                if existing_content is None:
                    raise
                content_inserted = False
        else:
            if (
                existing_content["raw_object_id"] != receipt.raw_object_id
                or int(existing_content["byte_size"]) != receipt.byte_size
                or existing_content["storage_uri"] != receipt.storage_uri
            ):
                raise CatalogRegistrationError(
                    "conflicting content row for sha256",
                    context={"existing": dict(existing_content)},
                )

        acquisition_inserted = False
        if existing_acq is not None and existing_acq.get("status") == "SUCCEEDED":
            acquisition_inserted = False
        elif existing_acq is not None and existing_acq.get("status") == "REGISTRATION_PENDING":
            self._conn.execute(
                """
                UPDATE raw_acquisition SET
                    raw_object_id = ?,
                    status = 'SUCCEEDED',
                    checksum_verification = ?,
                    failure_json = NULL,
                    updated_at = ?
                WHERE acquisition_id = ?
                """,
                (
                    receipt.raw_object_id,
                    checksum_verification.value,
                    _iso(now),
                    acquisition_id,
                ),
            )
            acquisition_inserted = False  # updated, not new
        else:
            try:
                self._conn.execute(
                    """
                    INSERT INTO raw_acquisition (
                        acquisition_id, source_id, raw_object_id,
                        request_json, response_metadata_json, original_name,
                        checksum_algorithm, checksum_value, checksum_verification,
                        acquired_at, event_start, event_end, status,
                        failure_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SUCCEEDED', NULL, ?, ?)
                    """,
                    (
                        acquisition_id,
                        metadata.source_id,
                        receipt.raw_object_id,
                        _dumps(metadata.request),
                        _dumps(metadata.response_metadata),
                        metadata.original_name,
                        algo,
                        cval,
                        checksum_verification.value,
                        _iso(acquired),
                        _iso(metadata.event_start) if metadata.event_start else None,
                        _iso(metadata.event_end) if metadata.event_end else None,
                        _iso(now),
                        _iso(now),
                    ),
                )
                acquisition_inserted = True
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                again = self.get_acquisition(acquisition_id)
                if again and again.get("status") == "SUCCEEDED":
                    self._conn.commit()
                    return (content_inserted, False)
                raise CatalogRegistrationError(
                    f"acquisition insert failed: {exc}",
                    context={"acquisition_id": acquisition_id},
                ) from exc

        self._conn.commit()
        return (content_inserted, acquisition_inserted)

    def record_failed_acquisition(
        self,
        *,
        metadata: AcquisitionMetadata,
        error_message: str,
        checksum_verification: ChecksumVerification = ChecksumVerification.ABSENT,
        recorded_at: datetime | None = None,
    ) -> FailedAcquisitionRecord:
        if not metadata.source_id:
            raise RawStoreError("source_id must be non-empty")
        self.ensure_source(metadata.source_id)
        when = recorded_at or metadata.acquired_at or _utc_now()
        acquisition_id = metadata.acquisition_id or f"acq_{uuid.uuid4().hex}"
        algo = None
        cval = None
        if metadata.provider_checksum is not None:
            algo = metadata.provider_checksum.algorithm
            cval = metadata.provider_checksum.value
        failure = {"error": error_message, "request": dict(metadata.request)}
        now = _utc_now()
        self._conn.execute(
            """
            INSERT INTO raw_acquisition (
                acquisition_id, source_id, raw_object_id,
                request_json, response_metadata_json, original_name,
                checksum_algorithm, checksum_value, checksum_verification,
                acquired_at, event_start, event_end, status,
                failure_json, created_at, updated_at
            ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'FAILED', ?, ?, ?)
            """,
            (
                acquisition_id,
                metadata.source_id,
                _dumps(metadata.request),
                _dumps(metadata.response_metadata),
                metadata.original_name,
                algo,
                cval,
                checksum_verification.value,
                _iso(when),
                _iso(metadata.event_start) if metadata.event_start else None,
                _iso(metadata.event_end) if metadata.event_end else None,
                _dumps(failure),
                _iso(now),
                _iso(now),
            ),
        )
        self._conn.commit()
        return FailedAcquisitionRecord(
            acquisition_id=acquisition_id,
            source_id=metadata.source_id,
            status="FAILED",
            error_message=error_message,
            request=dict(metadata.request),
            checksum_algorithm=algo,
            checksum_value=cval,
            checksum_verification=checksum_verification,
            recorded_at=when,
        )
