"""Strict Pydantic v2 wire model for dataset manifests (MAN-001).

This module is the single source of truth for the manifest wire representation.
The checked-in ``schemas/dataset_manifest.schema.json`` is generated from
``ManifestWireModel`` (see ``generate_schema_json``); a contract test guards it
against drift.

The runtime dataclass ``DatasetManifest`` (``models.py``) remains the in-memory
representation used throughout the package. ``validate_manifest_dict`` performs
the promised strict validation against this model *before* the dataclass is
constructed, so invalid manifests fail closed.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from cryptofactors.catalog.dataset.errors import InvalidManifestError

_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_DSID_RE = re.compile(r"^ds_[a-f0-9]{64}$")
_NONEMPTY_STR = Field(min_length=1)


class _StrictModel(BaseModel):
    """Shared config: forbid unknown fields; strict scalar coercion."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


class _SchemaIdentity(_StrictModel):
    name: StrictStr = _NONEMPTY_STR
    version: StrictStr = _NONEMPTY_STR
    fingerprint: StrictStr | None = None


class _TransformSpec(_StrictModel):
    name: StrictStr = _NONEMPTY_STR
    version: StrictStr = _NONEMPTY_STR


class _CodeIdentity(_StrictModel):
    commit: StrictStr
    lock_sha256: StrictStr | None = None


class _ConfigIdentity(_StrictModel):
    config_sha256: StrictStr = Field(pattern=_SHA256_RE.pattern)


class _DependencyRef(_StrictModel):
    id: StrictStr = _NONEMPTY_STR
    kind: StrictStr  # enum-checked below
    role: StrictStr = _NONEMPTY_STR


class _OutputFileSpec(_StrictModel):
    relative_path: StrictStr = _NONEMPTY_STR
    uri: StrictStr = _NONEMPTY_STR
    sha256: StrictStr = Field(pattern=_SHA256_RE.pattern)
    rows: StrictInt = Field(ge=0)
    bytes: StrictInt = Field(ge=0)
    partition: dict[str, Any] = Field(default_factory=dict)


class _CoverageWindow(_StrictModel):
    event_start: datetime | None = None
    event_end: datetime | None = None
    availability_start: datetime | None = None
    availability_end: datetime | None = None


class _PublicationMetadata(_StrictModel):
    created_at: datetime
    publisher: StrictStr = _NONEMPTY_STR
    publisher_version: StrictStr = _NONEMPTY_STR

    @field_validator("created_at")
    @classmethod
    def _tz(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("publication.created_at must be timezone-aware")
        return value


class ManifestWireModel(_StrictModel):
    """Strict schema for the canonical published dataset manifest."""

    dataset_id: StrictStr = Field(pattern=_DSID_RE.pattern)
    dataset_type: StrictStr = _NONEMPTY_STR
    schema_version: StrictStr = _NONEMPTY_STR
    schema_def: _SchemaIdentity = Field(alias="schema", serialization_alias="schema")
    transform: _TransformSpec
    code_commit: StrictStr
    code: _CodeIdentity
    config_sha256: StrictStr = Field(pattern=_SHA256_RE.pattern)
    dependencies: list[_DependencyRef] = Field(min_length=0)
    files: list[_OutputFileSpec] = Field(min_length=1)
    row_count: StrictInt = Field(ge=0)
    byte_size: StrictInt = Field(ge=0)
    event_start: datetime | None = None
    event_end: datetime | None = None
    availability_start: datetime | None = None
    availability_end: datetime | None = None
    quality_status: StrictStr  # enum-checked below
    quality_summary: dict[str, Any] = Field(default_factory=dict)
    supersedes_dataset_id: StrictStr | None = None
    created_at: datetime
    publication: _PublicationMetadata
    manifest_sha256: StrictStr = Field(pattern=_SHA256_RE.pattern)

    @field_validator("dependencies")
    @classmethod
    def _check_dep_kinds(cls, deps: list[_DependencyRef]) -> list[_DependencyRef]:
        for d in deps:
            if d.kind not in ("RAW_OBJECT", "DATASET"):
                raise ValueError(f"invalid dependency kind: {d.kind!r}")
        return deps

    @field_validator("quality_status")
    @classmethod
    def _check_quality(cls, value: str) -> str:
        if value not in ("PASS", "PASS_WITH_WARNINGS", "QUARANTINED", "REJECTED"):
            raise ValueError(f"invalid quality_status: {value!r}")
        return value

    @field_validator(
        "event_start",
        "event_end",
        "availability_start",
        "availability_end",
        "created_at",
    )
    @classmethod
    def _tz_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _cross_field(self) -> "ManifestWireModel":
        # Duplicated compatibility fields must agree.
        if self.schema_version != self.schema_def.version:
            raise ValueError("schema_version != schema.version")
        if self.code_commit != self.code.commit:
            raise ValueError("code_commit != code.commit")
        # Each file emits uri == relative_path.
        seen_paths: set[str] = set()
        for f in self.files:
            if f.uri != f.relative_path:
                raise ValueError(f"file uri != relative_path: {f.relative_path!r}")
            if f.relative_path in seen_paths:
                raise ValueError(
                    f"duplicate logical output path: {f.relative_path!r}"
                )
            seen_paths.add(f.relative_path)
        # Coverage ordering.
        pairs = [
            ("event_start", "event_end"),
            ("availability_start", "availability_end"),
        ]
        for a, b in pairs:
            va = getattr(self, a)
            vb = getattr(self, b)
            if va is not None and vb is not None and va > vb:
                raise ValueError(f"{a} must not be after {b}")
        dep_ids = {d.id for d in self.dependencies}
        if self.supersedes_dataset_id is not None:
            if self.supersedes_dataset_id == self.dataset_id:
                raise ValueError("self-supersession rejected")
            if self.supersedes_dataset_id in dep_ids:
                raise ValueError("supersedes_dataset_id must not be a dependency")
        return self


def validate_manifest_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Strictly validate a parsed manifest dict; return it unchanged if valid.

    Raises ``InvalidManifestError`` for any schema, type, format, ordering,
    duplicate-path, or cross-field-compatibility violation.  Coercion of strings
    to integers is rejected (strict types via ``StrictInt``).
    """
    try:
        ManifestWireModel.model_validate(data)
    except InvalidManifestError:
        raise
    except Exception as exc:  # pydantic ValidationError or similar
        msg = str(exc).replace("\n", " ")
        raise InvalidManifestError(
            f"manifest schema validation failed: {msg}"
        ) from exc
    return data


def generate_schema_json() -> str:
    """Generate the JSON Schema string from the Pydantic model (single source)."""
    return json.dumps(
        ManifestWireModel.model_json_schema(),
        sort_keys=True,
        indent=2,
    )


__all__ = [
    "ManifestWireModel",
    "validate_manifest_dict",
    "generate_schema_json",
]
