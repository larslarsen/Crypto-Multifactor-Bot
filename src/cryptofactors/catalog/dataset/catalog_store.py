"""SQLite registration for immutable datasets via verified publication receipts."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from cryptofactors.catalog.dataset.errors import (
    CorruptDatasetError,
    RecoverableDatasetCatalogError,
    SupersessionError,
)
from cryptofactors.catalog.dataset.models import (
    DatasetManifest,
    DatasetPublicationReceipt,
    DependencyKind,
    PublicationStatus,
)
from cryptofactors.catalog.dataset.verify_tree import verify_published_tree


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise CorruptDatasetError(
            "datetime must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc).isoformat()


def _iso_coalesce(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return _iso(dt)


def _dumps(value: Mapping[str, Any] | None) -> str:
    return json.dumps(
        dict(value or {}),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _loads(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    data = json.loads(text)
    return dict(data) if isinstance(data, dict) else {}


class SqliteDatasetCatalog:
    """Atomic registration of dataset, files, and lineage from a verified receipt."""

    def __init__(
        self,
        database: Path | str,
        *,
        connection: sqlite3.Connection | None = None,
        chunk_size: int = 1024 * 1024,
    ) -> None:
        self._owned = connection is None
        if connection is not None:
            self._conn = connection
        else:
            self._conn = sqlite3.connect(str(database))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._chunk_size = chunk_size

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
            WHERE dataset_id = ? ORDER BY input_dataset_id
            """,
            (dataset_id,),
        ).fetchall()
        return [str(r["input_dataset_id"]) for r in rows]

    def list_files(self, dataset_id: str) -> Sequence[Mapping[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM dataset_file WHERE dataset_id = ? ORDER BY storage_uri",
            (dataset_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_raw_inputs(self, dataset_id: str) -> Sequence[Mapping[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM dataset_input_raw_object
            WHERE dataset_id = ? ORDER BY raw_object_id, role
            """,
            (dataset_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_dataset_inputs(self, dataset_id: str) -> Sequence[Mapping[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM dataset_input_dataset
            WHERE dataset_id = ? ORDER BY input_dataset_id, role
            """,
            (dataset_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def register_from_receipt(
        self,
        receipt: DatasetPublicationReceipt,
        *,
        manifest: DatasetManifest,
    ) -> bool:
        """Register only from a verified publication receipt + matching manifest.

        Returns True if newly inserted; False if complete identical registration exists.
        """
        if not receipt.is_complete():
            raise CorruptDatasetError(
                "publication receipt incomplete",
                context={"dataset_id": receipt.dataset_id},
            )
        if receipt.dataset_id != manifest.dataset_id:
            raise CorruptDatasetError("receipt/manifest dataset_id disagree")
        if receipt.manifest_sha256 != manifest.manifest_sha256:
            raise CorruptDatasetError("receipt/manifest sha256 disagree")
        if tuple(receipt.verified_outputs) != manifest.files:
            # Compare by semantic fields
            if len(receipt.verified_outputs) != len(manifest.files):
                raise CorruptDatasetError("receipt outputs disagree with manifest")
            for a, b in zip(receipt.verified_outputs, manifest.files, strict=True):
                if (
                    a.relative_path != b.relative_path
                    or a.sha256 != b.sha256
                    or a.rows != b.rows
                    or a.bytes != b.bytes
                ):
                    raise CorruptDatasetError("receipt outputs disagree with manifest")

        # Defect #6: independently confirm the immutable tree still exists and
        # matches the receipt before touching the catalog.  Read-only.
        verify_published_tree(receipt, manifest, chunk_size=self._chunk_size)

        existing = self.get_dataset(receipt.dataset_id)
        if existing is not None:
            if self._complete_identical_registration(receipt, manifest, existing):
                return False
            raise CorruptDatasetError(
                "dataset_id already registered with incomplete or conflicting records",
                context={"dataset_id": receipt.dataset_id},
            )

        self._validate_supersession(receipt.supersedes_dataset_id, receipt.dataset_id)

        try:
            self._insert_all(receipt, manifest)
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            self._conn.rollback()
            # Concurrent winner: re-read and validate.
            existing = self.get_dataset(receipt.dataset_id)
            if existing is not None and self._complete_identical_registration(
                receipt, manifest, existing
            ):
                return False
            raise RecoverableDatasetCatalogError(
                "concurrent catalog registration conflict",
                dataset_id=receipt.dataset_id,
                manifest_sha256=receipt.manifest_sha256,
                dataset_path=str(receipt.dataset_path),
            )
        except Exception as exc:
            self._conn.rollback()
            if isinstance(exc, (CorruptDatasetError, SupersessionError, RecoverableDatasetCatalogError)):
                raise
            raise RecoverableDatasetCatalogError(
                f"catalog registration failed: {exc}",
                dataset_id=receipt.dataset_id,
                manifest_sha256=receipt.manifest_sha256,
                dataset_path=str(receipt.dataset_path),
                context={"error": str(exc)},
            ) from exc

    def _validate_supersession(
        self, supersedes: str | None, new_id: str
    ) -> None:
        if supersedes is None:
            return
        if supersedes == new_id:
            raise SupersessionError(
                "self-supersession is rejected",
                context={"dataset_id": new_id},
            )
        if not self.dataset_exists(supersedes):
            raise SupersessionError(
                "supersedes_dataset_id does not exist",
                context={"supersedes_dataset_id": supersedes},
            )
        # Reject if target already supersedes new_id (simple cycle) or target's
        # supersession chain includes new_id.
        seen: set[str] = set()
        current: str | None = supersedes
        while current is not None:
            if current == new_id:
                raise SupersessionError(
                    "supersession cycle detected",
                    context={"dataset_id": new_id, "via": supersedes},
                )
            if current in seen:
                break
            seen.add(current)
            row = self.get_dataset(current)
            if row is None:
                break
            current = row.get("supersedes_dataset_id")

    def _complete_identical_registration(
        self,
        receipt: DatasetPublicationReceipt,
        manifest: DatasetManifest,
        existing: Mapping[str, Any],
    ) -> bool:
        """Exact comparison of every persisted field (Defect #5)."""
        if existing["manifest_sha256"] != receipt.manifest_sha256:
            return False
        if existing["manifest_uri"] != receipt.manifest_uri:
            return False
        if existing.get("publication_uri") is not None and existing.get(
            "publication_uri"
        ) != receipt.publication_uri:
            return False
        if int(existing["row_count"]) != manifest.statistics.row_count:
            return False
        if int(existing["byte_size"]) != manifest.statistics.byte_size:
            return False
        if existing["dataset_type"] != manifest.dataset_type:
            return False
        if existing["schema_version"] != manifest.schema.version:
            return False
        if (existing.get("schema_fingerprint") or None) != manifest.schema.fingerprint:
            return False
        if existing["transform_name"] != manifest.transform.name:
            return False
        if existing["transform_version"] != manifest.transform.version:
            return False
        if existing["code_commit"] != manifest.code.commit:
            return False
        if existing["config_sha256"] != manifest.config.config_sha256:
            return False
        if existing["quality_status"] != manifest.quality_status.value:
            return False
        if _dumps(manifest.quality_summary) != (existing.get("quality_summary_json") or "{}"):
            return False
        if _iso_coalesce(manifest.coverage.event_start) != (
            existing.get("event_start")
        ):
            return False
        if _iso_coalesce(manifest.coverage.event_end) != (existing.get("event_end")):
            return False
        if _iso_coalesce(manifest.coverage.availability_start) != (
            existing.get("availability_start")
        ):
            return False
        if _iso_coalesce(manifest.coverage.availability_end) != (
            existing.get("availability_end")
        ):
            return False
        if _iso(receipt.catalog_created_at) != existing.get("created_at"):
            return False
        if existing.get("supersedes_dataset_id") != manifest.supersedes_dataset_id:
            return False
        if not self._publication_status_consistent(existing, manifest):
            return False

        files = self.list_files(receipt.dataset_id)
        if len(files) != len(manifest.files):
            return False
        file_map = {str(f["storage_uri"]): f for f in files}
        for spec in manifest.files:
            row = file_map.get(spec.relative_path)
            if row is None:
                return False
            if (
                str(row["file_sha256"]) != spec.sha256
                or int(row["row_count"]) != spec.rows
                or int(row["byte_size"]) != spec.bytes
                or _dumps(spec.partition) != (row.get("partition_json") or "{}")
            ):
                return False

        raws = self.list_raw_inputs(receipt.dataset_id)
        ups = self.list_dataset_inputs(receipt.dataset_id)
        expected_raw = {
            (d.id, d.role)
            for d in manifest.dependencies
            if d.kind is DependencyKind.RAW_OBJECT
        }
        expected_ds = {
            (d.id, d.role)
            for d in manifest.dependencies
            if d.kind is DependencyKind.DATASET
        }
        got_raw = {(str(r["raw_object_id"]), str(r["role"])) for r in raws}
        got_ds = {(str(r["input_dataset_id"]), str(r["role"])) for r in ups}
        if got_raw != expected_raw or got_ds != expected_ds:
            return False
        return True

    def _publication_status_consistent(
        self,
        existing: Mapping[str, Any],
        manifest: DatasetManifest,
    ) -> bool:
        """Validate publication_status vs supersession state (Defect #5)."""
        status = existing.get("publication_status")
        # A successor (manifest supersedes another) requires that predecessor to
        # already be SUPERSEDED; otherwise the chain is inconsistent.
        if manifest.supersedes_dataset_id:
            pred = self.get_dataset(manifest.supersedes_dataset_id)
            if pred is None:
                return False
            if pred.get("publication_status") != PublicationStatus.SUPERSEDED.value:
                return False
        # If this row is SUPERSEDED, a registered successor must reference it.
        if status == PublicationStatus.SUPERSEDED.value:
            ok = self._conn.execute(
                "SELECT 1 FROM dataset WHERE supersedes_dataset_id = ? LIMIT 1",
                (existing["dataset_id"],),
            ).fetchone()
            if ok is None:
                return False
        return True

    def _insert_all(
        self, receipt: DatasetPublicationReceipt, manifest: DatasetManifest
    ) -> None:
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
                receipt.dataset_id,
                manifest.dataset_type,
                manifest.schema.version,
                manifest.schema.fingerprint,
                receipt.manifest_sha256,
                receipt.manifest_uri,
                receipt.publication_uri,
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
                PublicationStatus.REGISTERED.value,
                _iso(receipt.catalog_created_at),
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
                    receipt.dataset_id,
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
                    (receipt.dataset_id, dep.id, dep.role),
                )
            else:
                self._conn.execute(
                    """
                    INSERT INTO dataset_input_dataset (dataset_id, input_dataset_id, role)
                    VALUES (?, ?, ?)
                    """,
                    (receipt.dataset_id, dep.id, dep.role),
                )
        if manifest.supersedes_dataset_id:
            self._conn.execute(
                """
                UPDATE dataset SET publication_status = ?
                WHERE dataset_id = ?
                """,
                (PublicationStatus.SUPERSEDED.value, manifest.supersedes_dataset_id),
            )
