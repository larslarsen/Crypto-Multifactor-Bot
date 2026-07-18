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
    AcquisitionConflictError,
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
    assert_no_symlink_components,
    assert_regular_nonsymlink_file,
    canonical_identity,
    content_addressed_relative_path,
    raw_object_id_for_sha256,
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


def _loads_obj(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        return {}
    return data


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


def verify_publication_receipt(
    receipt: PublicationReceipt,
    *,
    store_root: Path,
    object_prefix: str,
) -> None:
    """Fail closed unless receipt identity is fully canonical and on-disk verified."""
    if not receipt.is_complete():
        raise CatalogRegistrationError(
            "publication receipt is incomplete",
            context={"receipt_sha256": receipt.sha256},
        )

    root = Path(store_root).resolve()
    prefix = object_prefix or receipt.object_prefix
    if receipt.object_prefix != prefix:
        raise CatalogRegistrationError(
            "receipt object_prefix does not match catalog configuration",
            context={
                "receipt_prefix": receipt.object_prefix,
                "configured_prefix": prefix,
            },
        )

    digest, expected_id, expected_path, expected_uri = canonical_identity(
        root=root,
        object_prefix=prefix,
        sha256_hex=receipt.sha256,
    )

    if receipt.raw_object_id != expected_id:
        raise CatalogRegistrationError(
            "receipt raw_object_id is not canonical for SHA-256",
            context={
                "expected": expected_id,
                "observed": receipt.raw_object_id,
                "sha256": digest,
            },
        )
    if receipt.storage_uri != expected_uri:
        raise CatalogRegistrationError(
            "receipt storage_uri is not canonical",
            context={
                "expected": expected_uri,
                "observed": receipt.storage_uri,
                "sha256": digest,
            },
        )

    observed_path = Path(receipt.storage_path).resolve()
    if observed_path != expected_path:
        raise CatalogRegistrationError(
            "receipt storage_path is not the canonical content path",
            context={
                "expected": str(expected_path),
                "observed": str(observed_path),
                "sha256": digest,
            },
        )

    try:
        assert_no_symlink_components(expected_path, stop_at=root)
    except PathSafetyError as exc:
        raise CatalogRegistrationError(str(exc), context=exc.context) from exc

    if expected_path.is_symlink():
        raise CatalogRegistrationError(
            "publication path must not be a symlink",
            context={"path": str(expected_path)},
        )
    if not expected_path.exists():
        raise CatalogRegistrationError(
            "publication path missing",
            context={"path": str(expected_path)},
        )
    try:
        assert_regular_nonsymlink_file(expected_path, label="publication path")
    except PathSafetyError as exc:
        raise CatalogRegistrationError(str(exc), context=exc.context) from exc

    st = os.lstat(expected_path)
    if not statmod.S_ISREG(st.st_mode):
        raise CatalogRegistrationError(
            "publication path is not a regular file",
            context={"path": str(expected_path)},
        )
    if st.st_size != receipt.byte_size:
        raise CatalogRegistrationError(
            "publication size mismatch",
            context={
                "path": str(expected_path),
                "expected": receipt.byte_size,
                "actual": st.st_size,
            },
        )
    actual = _sha256_file(expected_path)
    if actual != digest:
        raise CatalogRegistrationError(
            "publication SHA-256 mismatch",
            context={"path": str(expected_path), "expected": digest, "actual": actual},
        )


def _provenance_snapshot(
    metadata: AcquisitionMetadata,
    *,
    checksum_verification: ChecksumVerification,
    raw_object_id: str | None,
) -> dict[str, Any]:
    algo = None
    cval = None
    if metadata.provider_checksum is not None:
        algo = metadata.provider_checksum.algorithm
        cval = metadata.provider_checksum.value
    return {
        "source_id": metadata.source_id,
        "raw_object_id": raw_object_id,
        "request": dict(metadata.request),
        "response_metadata": dict(metadata.response_metadata),
        "original_name": metadata.original_name,
        "checksum_algorithm": algo,
        "checksum_value": cval,
        "checksum_verification": checksum_verification.value,
        "event_start": _iso(metadata.event_start) if metadata.event_start else None,
        "event_end": _iso(metadata.event_end) if metadata.event_end else None,
        "acquired_at": _iso(metadata.acquired_at) if metadata.acquired_at else None,
    }


def _row_provenance_snapshot(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_id": row["source_id"],
        "raw_object_id": row["raw_object_id"],
        "request": _loads_obj(row["request_json"]),
        "response_metadata": _loads_obj(row["response_metadata_json"]),
        "original_name": row["original_name"],
        "checksum_algorithm": row["checksum_algorithm"],
        "checksum_value": row["checksum_value"],
        "checksum_verification": row["checksum_verification"],
        "event_start": row["event_start"],
        "event_end": row["event_end"],
        # Only compare acquired_at when the incoming registration supplied one;
        # handled by caller for optional equality.
        "acquired_at": row["acquired_at"],
    }


def _compatible_provenance(
    existing: dict[str, Any],
    proposed: dict[str, Any],
    *,
    compare_acquired_at: bool,
) -> bool:
    keys = [
        "source_id",
        "raw_object_id",
        "request",
        "response_metadata",
        "original_name",
        "checksum_algorithm",
        "checksum_value",
        "checksum_verification",
        "event_start",
        "event_end",
    ]
    for key in keys:
        if existing.get(key) != proposed.get(key):
            return False
    if compare_acquired_at and proposed.get("acquired_at") is not None:
        if existing.get("acquired_at") != proposed.get("acquired_at"):
            return False
    return True


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
        object_prefix: str | None = None,
    ) -> tuple[bool, bool]:
        prefix = object_prefix or receipt.object_prefix
        verify_publication_receipt(
            receipt,
            store_root=Path(store_root),
            object_prefix=prefix,
        )
        if not metadata.source_id:
            raise CatalogRegistrationError("source_id required")

        content_status = require_checksum_ok_for_verified_status(
            metadata.content_status, checksum_verification
        )
        digest = validate_sha256_hex(receipt.sha256)
        # Reconfirm id/uri match canonical for prefix (already in verify).
        expected_id = raw_object_id_for_sha256(digest)
        expected_uri = content_addressed_relative_path(
            digest, prefix=prefix
        ).as_posix()
        if receipt.raw_object_id != expected_id or receipt.storage_uri != expected_uri:
            raise CatalogRegistrationError("noncanonical receipt identity")

        acquired = metadata.acquired_at or _utc_now()
        acquisition_id = metadata.acquisition_id or f"acq_{uuid.uuid4().hex}"
        now = _utc_now()
        proposed = _provenance_snapshot(
            metadata,
            checksum_verification=checksum_verification,
            raw_object_id=receipt.raw_object_id,
        )

        self.ensure_source(metadata.source_id)

        existing_acq = self.get_acquisition(acquisition_id)
        if existing_acq is not None:
            if existing_acq["status"] == "SUCCEEDED":
                existing_snap = _row_provenance_snapshot(existing_acq)
                if _compatible_provenance(
                    existing_snap,
                    proposed,
                    compare_acquired_at=metadata.acquired_at is not None,
                ):
                    return (False, False)
                raise AcquisitionConflictError(
                    "acquisition_id already SUCCEEDED with conflicting provenance",
                    context={
                        "acquisition_id": acquisition_id,
                        "existing": existing_snap,
                        "proposed": proposed,
                    },
                )
            if existing_acq["status"] == "FAILED":
                raise AcquisitionConflictError(
                    "acquisition_id already FAILED; cannot register successful publication",
                    context={"acquisition_id": acquisition_id},
                )
            if existing_acq["status"] == "REGISTRATION_PENDING":
                pass  # complete below
            else:
                raise AcquisitionConflictError(
                    f"acquisition_id in unexpected status {existing_acq['status']!r}",
                    context={"acquisition_id": acquisition_id},
                )

        algo = proposed["checksum_algorithm"]
        cval = proposed["checksum_value"]

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
                        metadata.original_name,
                        _dumps(metadata.request),
                        _dumps(metadata.response_metadata),
                        cval,
                        _iso(acquired),
                        proposed["event_start"],
                        proposed["event_end"],
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
        if existing_acq is not None and existing_acq.get("status") == "REGISTRATION_PENDING":
            self._conn.execute(
                """
                UPDATE raw_acquisition SET
                    raw_object_id = ?,
                    source_id = ?,
                    request_json = ?,
                    response_metadata_json = ?,
                    original_name = ?,
                    checksum_algorithm = ?,
                    checksum_value = ?,
                    checksum_verification = ?,
                    status = 'SUCCEEDED',
                    failure_json = NULL,
                    updated_at = ?
                WHERE acquisition_id = ?
                """,
                (
                    receipt.raw_object_id,
                    metadata.source_id,
                    _dumps(metadata.request),
                    _dumps(metadata.response_metadata),
                    metadata.original_name,
                    algo,
                    cval,
                    checksum_verification.value,
                    _iso(now),
                    acquisition_id,
                ),
            )
            acquisition_inserted = False
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
                        proposed["event_start"],
                        proposed["event_end"],
                        _iso(now),
                        _iso(now),
                    ),
                )
                acquisition_inserted = True
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                again = self.get_acquisition(acquisition_id)
                if again and again.get("status") == "SUCCEEDED":
                    snap = _row_provenance_snapshot(again)
                    if _compatible_provenance(
                        snap, proposed, compare_acquired_at=metadata.acquired_at is not None
                    ):
                        return (content_inserted, False)
                    raise AcquisitionConflictError(
                        "concurrent acquisition_id conflict",
                        context={"acquisition_id": acquisition_id},
                    ) from exc
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
        proposed = _provenance_snapshot(
            metadata,
            checksum_verification=checksum_verification,
            raw_object_id=None,
        )
        failure = {"error": error_message, "request": dict(metadata.request)}
        now = _utc_now()

        existing = self.get_acquisition(acquisition_id)
        if existing is not None:
            if existing["status"] == "FAILED" and existing["raw_object_id"] is None:
                existing_snap = _row_provenance_snapshot(existing)
                # For FAILED rows, raw_object_id is None; compare core provenance.
                if _compatible_provenance(
                    {**existing_snap, "raw_object_id": None},
                    proposed,
                    compare_acquired_at=metadata.acquired_at is not None,
                ):
                    return FailedAcquisitionRecord(
                        acquisition_id=acquisition_id,
                        source_id=str(existing["source_id"]),
                        status="FAILED",
                        error_message=error_message,
                        request=dict(metadata.request),
                        checksum_algorithm=algo,
                        checksum_value=cval,
                        checksum_verification=checksum_verification,
                        recorded_at=when,
                    )
                raise AcquisitionConflictError(
                    "FAILED acquisition_id reused with conflicting provenance",
                    context={
                        "acquisition_id": acquisition_id,
                        "existing": existing_snap,
                        "proposed": proposed,
                    },
                )
            raise AcquisitionConflictError(
                f"acquisition_id already exists with status {existing['status']!r}",
                context={"acquisition_id": acquisition_id},
            )

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
                proposed["event_start"],
                proposed["event_end"],
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
