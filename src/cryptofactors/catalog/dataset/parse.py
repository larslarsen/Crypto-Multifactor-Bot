"""Strict independent dataset manifest parser (MAN-001)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cryptofactors.catalog.dataset.canonicalize import (
    compute_dataset_id,
    compute_manifest_sha256,
    dumps_canonical,
    identity_from_manifest_dict,
)
from cryptofactors.catalog.dataset.errors import InvalidManifestError
from cryptofactors.catalog.dataset.schema_model import validate_manifest_dict
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetManifest,
    DatasetStatistics,
    DependencyKind,
    DependencyRef,
    OutputFileSpec,
    PublicationMetadata,
    QualityStatus,
    SchemaIdentity,
    TransformSpec,
)

_KNOWN_TOP_LEVEL = frozenset(
    {
        "dataset_id",
        "dataset_type",
        "schema_version",
        "schema",
        "transform",
        "code_commit",
        "code",
        "config_sha256",
        "dependencies",
        "files",
        "row_count",
        "byte_size",
        "event_start",
        "event_end",
        "availability_start",
        "availability_end",
        "quality_status",
        "quality_summary",
        "supersedes_dataset_id",
        "created_at",
        "publication",
        "manifest_sha256",
    }
)


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise InvalidManifestError("datetime fields must be timezone-aware")
    return dt.astimezone(timezone.utc)


def load_manifest_bytes(raw: bytes) -> DatasetManifest:
    """Parse exact manifest file bytes (no whitespace normalization)."""
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise InvalidManifestError("manifest is not valid UTF-8") from exc
    if not text.endswith("\n"):
        raise InvalidManifestError("manifest must end with a single trailing newline")
    body = text[:-1]
    if body.endswith("\n") or body.endswith("\r"):
        raise InvalidManifestError("manifest must not contain extra trailing newlines")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise InvalidManifestError(f"manifest JSON parse error: {exc}") from exc
    if not isinstance(data, dict):
        raise InvalidManifestError("manifest root must be an object")
    unknown = set(data) - _KNOWN_TOP_LEVEL
    if unknown:
        raise InvalidManifestError(
            "unknown manifest fields",
            context={"unknown": sorted(unknown)},
        )
    return manifest_from_dict(data, exact_file_bytes=raw)


def load_manifest_file(path: Path) -> DatasetManifest:
    raw = path.read_bytes()
    return load_manifest_bytes(raw)


def manifest_from_dict(
    data: Mapping[str, Any],
    *,
    exact_file_bytes: bytes | None = None,
) -> DatasetManifest:
    # Strict wire-model validation (single source of truth via Pydantic).
    validate_manifest_dict(dict(data))

    required = [
        "dataset_id",
        "dataset_type",
        "transform",
        "config_sha256",
        "dependencies",
        "files",
        "row_count",
        "byte_size",
        "quality_status",
        "manifest_sha256",
    ]
    for key in required:
        if key not in data:
            raise InvalidManifestError(f"missing required field: {key}")

    schema_raw = data.get("schema") or {
        "name": "unknown",
        "version": data.get("schema_version", ""),
        "fingerprint": None,
    }
    transform = data["transform"]
    code_raw = data.get("code") or {
        "commit": data.get("code_commit", ""),
        "lock_sha256": None,
    }
    files = []
    for f in data["files"]:
        path = str(f.get("relative_path") or f.get("uri") or "")
        files.append(
            OutputFileSpec(
                relative_path=path,
                sha256=str(f["sha256"]).lower(),
                rows=int(f["rows"]),
                bytes=int(f["bytes"]),
                partition=dict(f.get("partition") or {}),
            )
        )
    deps = [
        DependencyRef(
            id=str(d["id"]),
            kind=DependencyKind(str(d["kind"])),
            role=str(d["role"]),
        )
        for d in data["dependencies"]
    ]
    pub_raw = data.get("publication") or {}
    created = _parse_dt(data.get("created_at") or pub_raw.get("created_at"))
    if created is None:
        created = datetime(1970, 1, 1, tzinfo=timezone.utc)

    manifest = DatasetManifest(
        dataset_id=str(data["dataset_id"]),
        dataset_type=str(data["dataset_type"]),
        schema=SchemaIdentity(
            name=str(schema_raw["name"]),
            version=str(schema_raw["version"]),
            fingerprint=schema_raw.get("fingerprint"),
        ),
        transform=TransformSpec(
            name=str(transform["name"]),
            version=str(transform["version"]),
        ),
        code=CodeIdentity(
            commit=str(code_raw["commit"]),
            lock_sha256=code_raw.get("lock_sha256"),
        ),
        config=ConfigIdentity(config_sha256=str(data["config_sha256"]).lower()),
        dependencies=tuple(deps),
        files=tuple(files),
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
        publication=PublicationMetadata(
            created_at=created,
            publisher=str(pub_raw.get("publisher") or "cryptofactors.catalog.dataset"),
            publisher_version=str(pub_raw.get("publisher_version") or "1"),
        ),
        supersedes_dataset_id=data.get("supersedes_dataset_id"),
        manifest_sha256=str(data["manifest_sha256"]).lower(),
    )

    # Recompute hashes / identity.
    recomputed_manifest_sha = compute_manifest_sha256(manifest)
    if manifest.manifest_sha256 != recomputed_manifest_sha:
        raise InvalidManifestError(
            "embedded manifest_sha256 mismatch",
            context={
                "embedded": manifest.manifest_sha256,
                "recomputed": recomputed_manifest_sha,
            },
        )
    identity = identity_from_manifest_dict(dict(data))
    expected_id, _ = compute_dataset_id(identity)
    if manifest.dataset_id != expected_id:
        raise InvalidManifestError(
            "dataset_id does not match recomputed identity",
            context={"embedded": manifest.dataset_id, "recomputed": expected_id},
        )

    if exact_file_bytes is not None:
        from cryptofactors.catalog.dataset.canonicalize import full_manifest_dict

        expected_bytes = (dumps_canonical(full_manifest_dict(manifest)) + "\n").encode(
            "utf-8"
        )
        if exact_file_bytes != expected_bytes:
            raise InvalidManifestError(
                "manifest file bytes are not exactly canonical",
                context={
                    "expected_len": len(expected_bytes),
                    "actual_len": len(exact_file_bytes),
                },
            )

    return manifest
