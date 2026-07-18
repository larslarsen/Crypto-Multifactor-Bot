"""SQLite registration for immutable datasets and lineage (MAN-001)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from cryptofactors.catalog.dataset.errors import (
    CorruptDatasetError,
    RecoverableDatasetCatalogError,
)
from cryptofactors.catalog.dataset.models import (
    DatasetManifest,
    DependencyKind,
    PublicationStatus,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(timezone.utc).isoformat()


def _dumps(value: Mapping[str, Any] | None) -> str:
    return json.dumps(
        dict(value or {}),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


class SqliteDatasetCatalog:
    """Atomic registration of dataset, files, and lineage edges."""

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

    def get_dataset(self, dataset_id: str) -> Mapping[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM dataset WHERE dataset_id = ?",
            (dataset_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def dataset_exists(self, dataset_id: str) -> bool:
        return self.get_dataset(dataset_id) is not None

    def raw_object_exists(self, raw_object_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM raw_object WHERE raw_object_id = ?",
            (raw_object_id,),
        ).fetchone()
        return row is not None

    def upstream_dataset_ids(self, dataset_id: str) -> Sequence[str]:
        rows = self._conn.execute(
            """
            SELECT input_dataset_id FROM dataset_input_dataset
            WHERE dataset_id = ?
            ORDER BY input_dataset_id
            """,
            (dataset_id,),
        ).fetchall()
        return [str(r["input_dataset_id"]) for r in rows]

    def list_files(self, dataset_id: str) -> Sequence[Mapping[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM dataset_file WHERE dataset_id = ?
            ORDER BY file_sha256
            """,
            (dataset_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_raw_inputs(self, dataset_id: str) -> Sequence[Mapping[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM dataset_input_raw_object WHERE dataset_id = ?
            ORDER BY raw_object_id, role
            """,
            (dataset_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_dataset_inputs(self, dataset_id: str) -> Sequence[Mapping[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM dataset_input_dataset WHERE dataset_id = ?
            ORDER BY input_dataset_id, role
            """,
            (dataset_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def register_dataset(
        self,
        *,
        manifest: DatasetManifest,
        manifest_uri: str,
        publication_uri: str,
        publication_status: PublicationStatus = PublicationStatus.REGISTERED,
    ) -> bool:
        """Insert dataset + files + lineage atomically.

        Returns True if newly inserted; False if identical idempotent row exists.
        """
        existing = self.get_dataset(manifest.dataset_id)
        if existing is not None:
            if (
                existing["manifest_sha256"] == manifest.manifest_sha256
                and existing["manifest_uri"] == manifest_uri
                and int(existing["row_count"]) == manifest.statistics.row_count
                and int(existing["byte_size"]) == manifest.statistics.byte_size
            ):
                return False
            raise CorruptDatasetError(
                "dataset_id already registered with different manifest",
                context={
                    "dataset_id": manifest.dataset_id,
                    "existing_manifest_sha256": existing["manifest_sha256"],
                    "new_manifest_sha256": manifest.manifest_sha256,
                },
            )

        try:
            self._conn.execute(
                """
                INSERT INTO dataset (
                    dataset_id, dataset_type, schema_version, schema_fingerprint,
                    manifest_sha256, manifest_uri, publication_uri,
                    transform_name, transform_version, code_commit, config_sha256,
                    row_count, byte_size,
                    event_start, event_end, availability_start, availability_end,
                    quality_status, quality_summary_json, supersedes_dataset_id,
                    publication_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    manifest.dataset_id,
                    manifest.dataset_type,
                    manifest.schema.version,
                    manifest.schema.fingerprint,
                    manifest.manifest_sha256,
                    manifest_uri,
                    publication_uri,
                    manifest.transform.name,
                    manifest.transform.version,
                    manifest.code.commit,
                    manifest.config.config_sha256,
                    manifest.statistics.row_count,
                    manifest.statistics.byte_size,
                    _iso(manifest.coverage.event_start)
                    if manifest.coverage.event_start
                    else None,
                    _iso(manifest.coverage.event_end) if manifest.coverage.event_end else None,
                    _iso(manifest.coverage.availability_start)
                    if manifest.coverage.availability_start
                    else None,
                    _iso(manifest.coverage.availability_end)
                    if manifest.coverage.availability_end
                    else None,
                    manifest.quality_status.value,
                    _dumps(manifest.quality_summary),
                    manifest.supersedes_dataset_id,
                    publication_status.value,
                    _iso(manifest.publication.created_at),
                ),
            )
            for f in manifest.files:
                self._conn.execute(
                    """
                    INSERT INTO dataset_file (
                        dataset_id, file_sha256, storage_uri, row_count, byte_size, partition_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        manifest.dataset_id,
                        f.sha256,
                        f.relative_path,
                        f.rows,
                        f.bytes,
                        _dumps(f.partition),
                    ),
                )
            for dep in manifest.dependencies:
                if dep.kind is DependencyKind.RAW_OBJECT:
                    self._conn.execute(
                        """
                        INSERT INTO dataset_input_raw_object (dataset_id, raw_object_id, role)
                        VALUES (?, ?, ?)
                        """,
                        (manifest.dataset_id, dep.id, dep.role),
                    )
                else:
                    self._conn.execute(
                        """
                        INSERT INTO dataset_input_dataset (dataset_id, input_dataset_id, role)
                        VALUES (?, ?, ?)
                        """,
                        (manifest.dataset_id, dep.id, dep.role),
                    )
            if (
                manifest.supersedes_dataset_id
                and self.dataset_exists(manifest.supersedes_dataset_id)
            ):
                self._conn.execute(
                    """
                    UPDATE dataset SET publication_status = ?
                    WHERE dataset_id = ?
                    """,
                    (PublicationStatus.SUPERSEDED.value, manifest.supersedes_dataset_id),
                )
            self._conn.commit()
            return True
        except Exception as exc:
            self._conn.rollback()
            raise RecoverableDatasetCatalogError(
                f"catalog registration failed: {exc}",
                dataset_id=manifest.dataset_id,
                manifest_sha256=manifest.manifest_sha256,
                dataset_path=publication_uri,
                context={"error": str(exc)},
            ) from exc
