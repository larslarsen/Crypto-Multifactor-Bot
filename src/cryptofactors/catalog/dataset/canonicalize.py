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
        return format(value, "f")
    if isinstance(value, datetime):
        return _require_utc(value, field_name="datetime")
    if isinstance(value, Path):
        text = value.as_posix()
        if value.is_absolute() or text.startswith("/"):
            raise InvalidManifestError(
                "absolute paths rejected in canonical form",
                context={"path": text},
            )
        parts = Path(text).parts
        if any(p in (".", "..") for p in parts):
            raise InvalidManifestError(
                "traversal path components rejected",
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


def canonical_relative_path(rel: str) -> str:
    """Normalize logical relative path for identity (posix, no traversal)."""
    text = rel.replace("\\", "/").strip()
    if not text or text.startswith("/") or text.startswith("./"):
        raise InvalidManifestError(
            "logical output path must be a non-empty relative path",
            context={"path": rel},
        )
    parts = [p for p in text.split("/") if p != ""]
    if any(p in (".", "..") for p in parts):
        raise InvalidManifestError(
            "logical output path must not contain '.' or '..'",
            context={"path": rel},
        )
    return "/".join(parts)


def _canonical_partition(partition: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = normalize_value(dict(partition))
    return result


def file_sort_key(f: OutputFileSpec | Mapping[str, Any]) -> tuple[Any, ...]:
    """Complete deterministic ordering key across all semantic file fields."""
    if isinstance(f, OutputFileSpec):
        path = canonical_relative_path(f.relative_path)
        part = dumps_canonical(_canonical_partition(f.partition))
        return (path, f.sha256.lower(), f.rows, f.bytes, part)
    path = canonical_relative_path(str(f["uri"] if "uri" in f else f["relative_path"]))
    part = dumps_canonical(dict(f.get("partition") or {}))
    return (path, str(f["sha256"]).lower(), int(f["rows"]), int(f["bytes"]), part)


def _sorted_deps(deps: list[DependencyRef] | tuple[DependencyRef, ...]) -> list[dict[str, str]]:
    items = [
        {
            "id": d.id,
            "kind": d.kind.value if isinstance(d.kind, Enum) else str(d.kind),
            "role": d.role,
        }
        for d in deps
    ]
    return sorted(items, key=lambda x: (x["kind"], x["role"], x["id"]))


def _normalize_files(
    files: list[OutputFileSpec] | tuple[OutputFileSpec, ...],
    *,
    include_uri: bool,
) -> list[dict[str, Any]]:
    """Normalize files for identity or full manifest; reject duplicates."""
    seen_paths: set[str] = set()
    seen_semantic: set[tuple[Any, ...]] = set()
    items: list[dict[str, Any]] = []
    for f in files:
        path = canonical_relative_path(f.relative_path)
        if path in seen_paths:
            raise InvalidManifestError(
                "duplicate logical output path",
                context={"path": path},
            )
        seen_paths.add(path)
        part = _canonical_partition(f.partition)
        semantic = (path, f.sha256.lower(), f.rows, f.bytes, dumps_canonical(part))
        if semantic in seen_semantic:
            raise InvalidManifestError(
                "duplicate semantic output declaration",
                context={"path": path, "sha256": f.sha256},
            )
        seen_semantic.add(semantic)
        entry: dict[str, Any] = {
            "sha256": f.sha256.lower(),
            "rows": f.rows,
            "bytes": f.bytes,
            "partition": part,
            "relative_path": path,
        }
        if include_uri:
            entry["uri"] = path
        items.append(entry)
    items.sort(
        key=lambda x: (
            x["relative_path"],
            x["sha256"],
            x["rows"],
            x["bytes"],
            dumps_canonical(x["partition"]),
        )
    )
    return items


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
    """Identity-bearing fields.

    Logical relative paths are identity-bearing together with sha256, rows,
    bytes, and partition. Wall-clock publication time is excluded.
    """
    file_ident = _normalize_files(list(files), include_uri=False)
    # Identity file records keep relative_path (logical path).
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
    digest = sha256_hex(canonical_bytes(identity))
    return f"ds_{digest}", digest


def full_manifest_dict(manifest: DatasetManifest) -> dict[str, Any]:
    """Full published manifest. created_at is present for humans but excluded from hash."""
    files = _normalize_files(list(manifest.files), include_uri=True)
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
        "files": files,
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


def immutable_manifest_body(manifest: DatasetManifest) -> dict[str, Any]:
    """Identity-stable body for manifest_sha256 (excludes wall-clock fields)."""
    body = full_manifest_dict(manifest)
    body["manifest_sha256"] = ""
    body["created_at"] = None
    body["publication"] = {
        "publisher": manifest.publication.publisher,
        "publisher_version": manifest.publication.publisher_version,
        # created_at intentionally omitted from immutable fingerprint
    }
    return body


def compute_manifest_sha256(manifest: DatasetManifest) -> str:
    return sha256_hex(canonical_bytes(immutable_manifest_body(manifest)))


def identity_from_manifest_dict(data: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct identity payload from a parsed full manifest dict."""
    files_in = list(data.get("files") or [])
    files: list[OutputFileSpec] = []
    for f in files_in:
        path = str(f.get("relative_path") or f.get("uri") or "")
        files.append(
            OutputFileSpec(
                relative_path=path,
                sha256=str(f["sha256"]),
                rows=int(f["rows"]),
                bytes=int(f["bytes"]),
                partition=dict(f.get("partition") or {}),
            )
        )
    deps_in = list(data.get("dependencies") or [])
    deps = [
        DependencyRef(
            id=str(d["id"]),
            kind=DependencyRef.__dataclass_fields__["kind"].type
            if False
            else __import__(
                "cryptofactors.catalog.dataset.models", fromlist=["DependencyKind"]
            ).DependencyKind(d["kind"]),
            role=str(d["role"]),
        )
        for d in deps_in
    ]
    schema = data.get("schema") or {
        "name": "unknown",
        "version": data.get("schema_version", ""),
        "fingerprint": None,
    }
    code = data.get("code") or {"commit": data.get("code_commit", ""), "lock_sha256": None}
    transform = data.get("transform") or {}
    return identity_payload(
        dataset_type=str(data["dataset_type"]),
        schema=SchemaIdentity(
            name=str(schema["name"]),
            version=str(schema["version"]),
            fingerprint=schema.get("fingerprint"),
        ),
        transform=TransformSpec(
            name=str(transform["name"]),
            version=str(transform["version"]),
        ),
        code=CodeIdentity(
            commit=str(code["commit"]),
            lock_sha256=code.get("lock_sha256"),
        ),
        config=ConfigIdentity(config_sha256=str(data["config_sha256"])),
        dependencies=deps,
        files=files,
        statistics=DatasetStatistics(
            row_count=int(data["row_count"]),
            byte_size=int(data["byte_size"]),
        ),
        coverage=CoverageWindow(
            event_start=_parse_dt(data.get("event_start")),
            event_end=_parse_dt(data.get("event_end")),
            availability_start=_parse_dt(data.get("availability_start")),
            availability_end=_parse_dt(data.get("availability_end")),
        ),
        quality_status=QualityStatus(str(data["quality_status"])),
        quality_summary=dict(data.get("quality_summary") or {}),
        supersedes_dataset_id=data.get("supersedes_dataset_id"),
    )


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)
