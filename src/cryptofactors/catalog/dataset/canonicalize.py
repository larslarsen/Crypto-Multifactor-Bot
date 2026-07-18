"""Deterministic canonical JSON for dataset manifests (MAN-001)."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from cryptofactors.catalog.dataset.errors import InvalidManifestError
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetManifest,
    DatasetStatistics,
    DependencyRef,
    OutputFileSpec,
    QualityStatus,
    SchemaIdentity,
    TransformSpec,
)


def _require_utc(dt: datetime, *, field_name: str) -> str:
    if dt.tzinfo is None:
        raise InvalidManifestError(
            f"{field_name} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc).isoformat()


def normalize_value(value: Any) -> Any:
    """Convert supported values to JSON-safe deterministic forms."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise InvalidManifestError("NaN/Inf float rejected")
        raise InvalidManifestError(
            "float rejected; use Decimal for fractional numbers",
            context={"value": repr(value)},
        )
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise InvalidManifestError("non-finite Decimal rejected")
        # Exact fixed-point string without exponent.
        return format(value, "f")
    if isinstance(value, datetime):
        return _require_utc(value, field_name="datetime")
    if isinstance(value, Path):
        # Only relative posix paths in manifests (locators).
        text = value.as_posix()
        if value.is_absolute() or text.startswith("/") or ".." in Path(text).parts:
            raise InvalidManifestError(
                "absolute or traversal paths rejected in canonical form",
                context={"path": text},
            )
        return text
    if isinstance(value, Enum):
        return normalize_value(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return normalize_value(asdict(value))
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise InvalidManifestError(
                    f"mapping keys must be strings, got {type(key).__name__}"
                )
            out[key] = normalize_value(item)
        return out
    if isinstance(value, (list, tuple)):
        return [normalize_value(item) for item in value]
    if isinstance(value, set):
        raise InvalidManifestError("set is not supported (unordered)")
    raise InvalidManifestError(
        f"unsupported type for canonicalization: {type(value).__name__}"
    )


def dumps_canonical(value: Any) -> str:
    """Stable JSON: sorted keys, compact separators, trailing newline omitted."""
    normalized = normalize_value(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_bytes(value: Any) -> bytes:
    return dumps_canonical(value).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sorted_deps(deps: list[DependencyRef] | tuple[DependencyRef, ...]) -> list[dict[str, str]]:
    items = [
        {"id": d.id, "kind": d.kind.value if isinstance(d.kind, Enum) else str(d.kind), "role": d.role}
        for d in deps
    ]
    return sorted(items, key=lambda x: (x["kind"], x["role"], x["id"]))


def _sorted_files(files: list[OutputFileSpec] | tuple[OutputFileSpec, ...]) -> list[dict[str, Any]]:
    items = []
    for f in files:
        items.append(
            {
                "sha256": f.sha256,
                "rows": f.rows,
                "bytes": f.bytes,
                "partition": dict(f.partition),
                # relative_path is a locator; included for full manifest, excluded from identity.
                "uri": f.relative_path,
            }
        )
    return sorted(items, key=lambda x: (x["sha256"], x["uri"]))


def identity_payload(
    *,
    dataset_type: str,
    schema: SchemaIdentity,
    transform: TransformSpec,
    code: CodeIdentity,
    config: ConfigIdentity,
    dependencies: Any,
    files: Any,
    statistics: DatasetStatistics,
    coverage: CoverageWindow,
    quality_status: QualityStatus,
    quality_summary: Mapping[str, Any],
    supersedes_dataset_id: str | None,
) -> dict[str, Any]:
    """Identity-bearing fields only (no dataset_id, created_at, or free storage paths).

    File identity uses content hashes/rows/bytes/partition — not uri/path.
    """
    file_ident = [
        {
            "sha256": f.sha256,
            "rows": f.rows,
            "bytes": f.bytes,
            "partition": dict(f.partition),
        }
        for f in files
    ]
    file_ident = sorted(file_ident, key=lambda x: (x["sha256"], x["rows"], x["bytes"]))
    return {
        "dataset_type": dataset_type,
        "schema": {
            "name": schema.name,
            "version": schema.version,
            "fingerprint": schema.fingerprint,
        },
        "transform": {"name": transform.name, "version": transform.version},
        "code": {"commit": code.commit, "lock_sha256": code.lock_sha256},
        "config": {"config_sha256": config.config_sha256},
        "dependencies": _sorted_deps(list(dependencies)),
        "files": file_ident,
        "statistics": {
            "row_count": statistics.row_count,
            "byte_size": statistics.byte_size,
        },
        "coverage": {
            "event_start": coverage.event_start,
            "event_end": coverage.event_end,
            "availability_start": coverage.availability_start,
            "availability_end": coverage.availability_end,
        },
        "quality_status": quality_status.value
        if isinstance(quality_status, QualityStatus)
        else str(quality_status),
        "quality_summary": dict(quality_summary),
        "supersedes_dataset_id": supersedes_dataset_id,
    }


def compute_dataset_id(identity: Mapping[str, Any]) -> tuple[str, str]:
    """Return (dataset_id, identity_sha256)."""
    digest = sha256_hex(canonical_bytes(identity))
    return f"ds_{digest}", digest


def full_manifest_dict(manifest: DatasetManifest) -> dict[str, Any]:
    """Full published manifest including locators and dataset_id."""
    return {
        "dataset_id": manifest.dataset_id,
        "dataset_type": manifest.dataset_type,
        "schema_version": manifest.schema.version,
        "schema": {
            "name": manifest.schema.name,
            "version": manifest.schema.version,
            "fingerprint": manifest.schema.fingerprint,
        },
        "transform": {
            "name": manifest.transform.name,
            "version": manifest.transform.version,
        },
        "code_commit": manifest.code.commit,
        "code": {
            "commit": manifest.code.commit,
            "lock_sha256": manifest.code.lock_sha256,
        },
        "config_sha256": manifest.config.config_sha256,
        "dependencies": _sorted_deps(manifest.dependencies),
        "files": _sorted_files(manifest.files),
        "row_count": manifest.statistics.row_count,
        "byte_size": manifest.statistics.byte_size,
        "event_start": manifest.coverage.event_start,
        "event_end": manifest.coverage.event_end,
        "availability_start": manifest.coverage.availability_start,
        "availability_end": manifest.coverage.availability_end,
        "quality_status": manifest.quality_status.value,
        "quality_summary": dict(manifest.quality_summary),
        "supersedes_dataset_id": manifest.supersedes_dataset_id,
        "created_at": manifest.publication.created_at,
        "publication": {
            "created_at": manifest.publication.created_at,
            "publisher": manifest.publication.publisher,
            "publisher_version": manifest.publication.publisher_version,
        },
        "manifest_sha256": manifest.manifest_sha256,
    }


def compute_manifest_sha256(manifest: DatasetManifest) -> str:
    """Fingerprint of full manifest with empty manifest_sha256 field."""
    body = full_manifest_dict(manifest)
    body["manifest_sha256"] = ""
    return sha256_hex(canonical_bytes(body))
