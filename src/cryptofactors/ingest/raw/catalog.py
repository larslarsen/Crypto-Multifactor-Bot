"""SQLite catalog integration for accepted raw objects and failed acquisitions."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cryptofactors.ingest.raw.errors import RawStoreError
from cryptofactors.ingest.raw.models import AcquisitionMetadata, FailedAcquisitionRecord
from cryptofactors.ingest.raw.paths import validate_sha256_hex


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


class SqliteRawObjectCatalog:
    """Catalog boundary backed by the control SQLite schema (``raw_object``, ``source``, ``build_run``)."""

    def __init__(self, database: Path | str, *, connection: sqlite3.Connection | None = None) -> None:
        self._database = Path(database) if connection is None else None
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

    def get_accepted_by_sha256(self, sha256: str) -> Mapping[str, Any] | None:
        digest = validate_sha256_hex(sha256)
        row = self._conn.execute(
            """
            SELECT raw_object_id, source_id, sha256, byte_size, storage_uri, status, acquired_at
            FROM raw_object
            WHERE sha256 = ? AND status IN ('ACQUIRED', 'VERIFIED')
            """,
            (digest,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def register_accepted(
        self,
        *,
        raw_object_id: str,
        sha256: str,
        byte_size: int,
        storage_uri: str,
        metadata: AcquisitionMetadata,
    ) -> bool:
        digest = validate_sha256_hex(sha256)
        if byte_size < 0:
            raise RawStoreError("byte_size must be >= 0")
        if not raw_object_id.startswith("raw_") or len(raw_object_id) != 4 + 64:
            raise RawStoreError(
                "raw_object_id must match raw_<sha256>",
                context={"raw_object_id": raw_object_id},
            )
        status = metadata.status or "ACQUIRED"
        if status not in ("ACQUIRED", "VERIFIED"):
            raise RawStoreError(
                "accepted registration requires status ACQUIRED or VERIFIED",
                context={"status": status},
            )
        acquired = metadata.acquired_at or _utc_now()
        self.ensure_source(metadata.source_id)

        existing = self.get_accepted_by_sha256(digest)
        if existing is not None:
            if (
                existing["sha256"] == digest
                and int(existing["byte_size"]) == byte_size
                and existing["storage_uri"] == storage_uri
            ):
                return False
            raise RawStoreError(
                "conflicting accepted catalog row for sha256",
                context={"existing": dict(existing), "storage_uri": storage_uri},
            )

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
                    raw_object_id,
                    metadata.source_id,
                    digest,
                    byte_size,
                    storage_uri,
                    metadata.original_name,
                    _dumps(metadata.request),
                    _dumps(metadata.response_metadata),
                    metadata.source_checksum,
                    _iso(acquired),
                    _iso(metadata.event_start) if metadata.event_start else None,
                    _iso(metadata.event_end) if metadata.event_end else None,
                    status,
                ),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError as exc:
            # Concurrent insert of same content — re-check for idempotent success.
            self._conn.rollback()
            existing = self.get_accepted_by_sha256(digest)
            if (
                existing is not None
                and existing["sha256"] == digest
                and int(existing["byte_size"]) == byte_size
                and existing["storage_uri"] == storage_uri
            ):
                return False
            raise RawStoreError(
                f"catalog registration integrity failure: {exc}",
                context={"sha256": digest, "raw_object_id": raw_object_id},
            ) from exc

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
        if not source_id:
            raise RawStoreError("source_id must be non-empty")
        self.ensure_source(source_id)
        when = recorded_at or _utc_now()
        rid = run_id or f"acqfail_{uuid.uuid4().hex}"
        error_payload = {
            "source_id": source_id,
            "error": error_message,
            "request": dict(request),
        }
        self._conn.execute(
            """
            INSERT INTO build_run (
                run_id, command, code_commit, config_sha256,
                started_at, ended_at, status, output_dataset_id, metrics_json, error_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?)
            """,
            (
                rid,
                command,
                "unknown",
                "0" * 64,
                _iso(when),
                _iso(when),
                "FAILED",
                _dumps(error_payload),
            ),
        )
        self._conn.commit()
        return FailedAcquisitionRecord(
            run_id=rid,
            source_id=source_id,
            status="FAILED",
            error_message=error_message,
            request=dict(request),
            recorded_at=when,
        )
