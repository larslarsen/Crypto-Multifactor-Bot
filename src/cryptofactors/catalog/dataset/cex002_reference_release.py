"""CEX-002 reference publication and atomic eleven-dataset admission.

The generic publisher copies trees and commits one dataset at a time. This
adapter references accepted files in place, writes only bundle bytes and
release metadata, and inserts all eleven datasets in one BEGIN IMMEDIATE
transaction after a pinned consumer proof. A prepared descriptor is not a
published release. Catalog commit is the only visibility gate.

Receipt 258 records 1,133,590 measured current bytes and 150,331 projected
rows at projections.fixed_schema_products.binance_usdm_harmonic_bundle.
The 24,352,003-byte figure is the future-only
partitioning.largest_future_width_charge_candidates.harmonic_bundle term:
150,331 * 8 reference-index bytes, 22,850,312 future partition-field bytes,
and 299,043 bundle-dictionary bytes. Current plus that future charge is
25,485,593. This adapter keeps 24,352,003 as the conservative cap on the
actual bundle file. It is not capacity.catalog_manifest_bundle_bytes
(5,556,368,003). The metadata remainder is 4,985,471,619. The operating
reserve, 29,690,701,415, stays free on the filesystem and is not spent.
"""

from __future__ import annotations

import ctypes
import decimal
import errno
import fcntl
import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset.canonicalize import (
    compute_dataset_id,
    compute_manifest_sha256,
    dumps_canonical,
    full_manifest_dict,
    identity_payload,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.errors import DatasetError
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetManifest,
    DatasetPublicationReceipt,
    DatasetStatistics,
    DependencyKind,
    DependencyRef,
    OutputFileSpec,
    PublicationMetadata,
    PublicationStatus,
    QualityStatus,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.catalog.dataset.parse import load_manifest_bytes
from cryptofactors.catalog.dataset.paths import (
    assert_no_symlink_components,
    assert_regular_file,
    assert_relative_safe,
    fsync_file,
    lexical_join,
)

TRANSFORM_NAME = "cex002_reference_publication"
TRANSFORM_VERSION = "1"
SCHEMA_VERSION = "1"
PUBLISHER_NAME = "cryptofactors.catalog.dataset.cex002_reference_release"
PUBLISHER_VERSION = "1"
BUNDLE_ROOT_RELATIVE = "data/.cex002_harmonic_bundle"
SEALED_CREATED_AT = datetime(1970, 1, 1, tzinfo=timezone.utc)
HARMONIC_BUNDLE_ALLOCATION_BYTES = 24_352_003
MEASURED_CURRENT_BUNDLE_BYTES = 1_133_590
SIZING_PROJECTED_BUNDLE_ROWS = 150_331
FUTURE_REFERENCE_INDEX_BYTES_PER_ROW = 8
FUTURE_PARTITION_FIELD_BYTES = 22_850_312
FUTURE_BUNDLE_DICTIONARY_BYTES = 299_043
CURRENT_PLUS_FUTURE_PROVISION_BYTES = 25_485_593
RELEASE_METADATA_BYTES = 5_556_368_003
RELEASE_METADATA_REMAINDER_BYTES = 4_985_471_619
OPERATING_RESERVE_BYTES = 29_690_701_415
SQLITE_PAGE_BYTES = 4_096
HASH_CHUNK_BYTES = 1024 * 1024
PROOF_MAX_BYTES = 256 * 2**20
MANIFEST_MAX_BYTES = 64 * 2**20
PREPARED_MAX_BYTES = 8 * 2**20
REQUIRED_DATASET_TYPES: tuple[str, ...] = (
    "binance_usdm_perpetual_membership",
    "binance_usdm_bar_1h",
    "binance_usdm_trade_flow_1h",
    "binance_usdm_open_interest_5m",
    "binance_usdm_funding_realized",
    "binance_usdm_funding_indicative_1h",
    "binance_usdm_mark_index_basis_1h",
    "binance_usdm_liquidation_observed_daily",
    "binance_usdm_cost_calibration",
    "binance_usdm_coverage_gap",
    "binance_usdm_harmonic_bundle",
)
PROOF_DOCUMENT = "cex002_harmonic_bundle_consumer_proof"
PREPARED_DOCUMENT = "cex002_harmonic_bundle_prepared_release"
PUBLICATION_DOCUMENT = "cex002_harmonic_bundle_publication"
BOUNDS_DOCUMENT = "cex002_harmonic_bundle_bounds_block"
PROOF_SCOPE = "complete_release"
QUARANTINE_MARKER = "cex002_bitmex_false_authority"
RENAME_NOREPLACE = 1
CODE_PATHS: tuple[str, ...] = (
    "src/cryptofactors/catalog/dataset/cex002_reference_release.py",
    "src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py",
    "scripts/research/publish_binance_usdm_harmonic_bundle.py",
    "tests/catalog/test_cex002_reference_release.py",
    "tests/ingest/test_binance_usdm_harmonic_bundle.py",
)
RUNTIME_CODE_PATHS: tuple[str, ...] = CODE_PATHS[:3]
PROOF_KEYS = frozenset(
    {
        "document_type",
        "schema_version",
        "status",
        "scope",
        "candidate_sha256",
        "checker_source_sha256",
        "nautilus_version",
        "datasets",
    }
)
COMPONENT_KEYS = frozenset(
    {
        "relative_path",
        "physical_sha256",
        "physical_bytes",
        "kind",
        "source_row_count",
        "readback_row_count",
        "source_value_sha256",
        "roundtrip_value_sha256",
        "time_start",
        "time_end",
        "time_absence_reason",
        "value_identity",
    }
)
_DICTIONARY_TYPES = frozenset(
    {
        "dictionary<values=string, indices=int32, ordered=0>",
        "dictionary<values=string, indices=int32, ordered=false>",
    }
)
_LIBC = ctypes.CDLL(None, use_errno=True)
_LIBC.renameat2.argtypes = [
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_uint,
]
_LIBC.renameat2.restype = ctypes.c_int


@dataclass(frozen=True, slots=True)
class BitmexFalseAuthorityTarget:
    dataset_id: str
    dataset_type: str
    rows: int
    relative_path: str
    file_sha256: str
    byte_size: int
    manifest_sha256: str
    created_at: str


# Literals copied from the accepted quarantine record. This module does not
# import the acquisition package.
BITMEX_FALSE_AUTHORITY_TARGETS: tuple[BitmexFalseAuthorityTarget, ...] = (
    BitmexFalseAuthorityTarget(
        "ds_4f82fede83f446e3ca29522e6e5f5a0ad7fb6d03d8931f1300addfe413364933",
        "bitmex_funding",
        14_376,
        "bitmex/funding/funding.parquet",
        "0213d0b070b02c3a4db02f7028a21938b48237a806731ed4ba03166833b055e2",
        205_097,
        "7d43319236fc73f87bcbbcac19c2ec5028a70e5faed252ae9397ec83d1ca39f4",
        "1970-01-01T00:00:00+00:00",
    ),
    BitmexFalseAuthorityTarget(
        "ds_f61c69342932c78c370b7950faf46d3e78be3695dbde8e6077acf8ccfa115deb",
        "bitmex_funding",
        32_768,
        "bitmex/funding/funding.parquet",
        "8246d1eb5c77f242bc01178c29aa2fa4e9b2a62ea6d4f15192b82735e42a9c3f",
        295_554,
        "6083d41c906f6bf4278b48a0cc6cd376a0c3c3bdc334fa94f42385eec8083ebb",
        "1970-01-01T00:00:00+00:00",
    ),
    BitmexFalseAuthorityTarget(
        "ds_11b6665e7dcd37cb85c0098f60681a252801bbc4f80cb053eccc0fa0ce3679ea",
        "bitmex_funding",
        32_768,
        "bitmex/funding/funding.parquet",
        "8246d1eb5c77f242bc01178c29aa2fa4e9b2a62ea6d4f15192b82735e42a9c3f",
        295_554,
        "0e340f3e18f48bd93ccb3d8b00e17fe7883c677350a95c7dec677a08c1f274e6",
        "2026-07-24T01:32:06.704813+00:00",
    ),
    BitmexFalseAuthorityTarget(
        "ds_ab70ebd21268fe47cbde63b266c0b6f41d0e2ca529d319e3f6f0aa5a5646f512",
        "bitmex_funding",
        38_256,
        "bitmex/funding/funding.parquet",
        "658ef0f1b5409aaf075ce40f385195712967bb0d369dfdf6a02785525436771e",
        409_230,
        "e7b64fc0312f6e2dea118bb3699734e85ce590ab519390cf5d1867edea7947e1",
        "2026-07-24T01:51:15.156657+00:00",
    ),
    BitmexFalseAuthorityTarget(
        "ds_ee8e9cd9ddd4de87a0c68ef0ff9b4a0da6c6bd7692c96b9f29f8cca13daf46c8",
        "bitmex_funding_full",
        189_570,
        "bitmex/funding_full/funding.parquet",
        "2ef8257c9724ca1949344175276c11b8f7764fd37eedfa866d5a47cf012fd215",
        1_187_191,
        "a6427c8277f951a120984a654254e91d6e704b129aedf2bda8ee080a6cb4a39e",
        "2026-07-24T04:00:41.830213+00:00",
    ),
)


class ReleaseError(DatasetError):
    """Fail-closed reference publication. ``blocker`` names the exact gate."""

    def __init__(
        self,
        message: str,
        *,
        blocker: str,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        merged = {"blocker": blocker, **dict(context or {})}
        super().__init__(message, context=merged)
        self.blocker = blocker


@dataclass(frozen=True, slots=True)
class ReferenceFile:
    """One referenced artifact. ``rows`` is zero for metadata JSON."""

    relative_path: str
    sha256: str
    rows: int
    byte_size: int
    partition: Mapping[str, Any]
    is_table: bool
    schema_fields: tuple[tuple[str, str, bool], ...] = ()


@dataclass(frozen=True, slots=True)
class ReferenceDatasetPlan:
    dataset_type: str
    schema_fingerprint: str
    files: tuple[ReferenceFile, ...]
    quality_summary: Mapping[str, Any]
    dependency_roles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReleasePolicy:
    repo: Path
    catalog_path: Path
    code: CodeIdentity
    created_at: datetime
    bundle_allocation_bytes: int
    metadata_remainder_bytes: int
    operating_reserve_bytes: int
    enforce_published_allocation: bool = True
    enforce_metadata_pin: bool = True
    spend_operating_reserve: bool = False
    bundle_root_relative: str = BUNDLE_ROOT_RELATIVE
    observed_free_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class ReleaseHooks:
    before_commit: Callable[[Path], None] | None = None
    after_commit: Callable[["PublishedRelease"], None] | None = None
    after_insert: Callable[[int], None] | None = None


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    relative_path: str
    sha256: str
    byte_size: int
    inode: int
    device: int


@dataclass(frozen=True, slots=True)
class PreparedRelease:
    descriptor_sha256: str
    descriptor_relative_path: str
    manifests: tuple[DatasetManifest, ...]
    dataset_ids: Mapping[str, str]
    bundle_bytes: int
    metadata_bytes: int
    consumable: bool = False


@dataclass(frozen=True, slots=True)
class PublishedRelease:
    publication_sha256: str
    publication_relative_path: str
    prepared_sha256: str
    dataset_ids: Mapping[str, str]
    reused: bool
    consumable: bool


def _fail(blocker: str, message: str, **context: Any) -> Any:
    raise ReleaseError(message, blocker=blocker, context=context)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_document(document: Mapping[str, Any]) -> bytes:
    return (dumps_canonical(dict(document)) + "\n").encode("utf-8")


def _hex64(value: object, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        _fail("identity_pin", f"{label} is not lowercase sha256", label=label)
    return value


def _commit(value: str) -> str:
    if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        _fail("code_commit", "code commit must be 40 lowercase hex characters")
    return value


def _anchor(path: Path) -> Path:
    absolute = path if path.is_absolute() else Path.cwd() / path
    try:
        facts = os.lstat(absolute)
    except OSError as exc:
        _fail("unsafe_path", "repository anchor is unavailable", path=str(absolute), error=str(exc))
    if stat.S_ISLNK(facts.st_mode) or not stat.S_ISDIR(facts.st_mode):
        _fail("unsafe_path", "repository anchor must be a real directory", path=str(absolute))
    return absolute


def _relative(root: Path, relative: str) -> Path:
    safe = assert_relative_safe(relative, label="reference path")
    path = lexical_join(root, safe)
    assert_no_symlink_components(path, stop_at=root)
    assert_regular_file(path, label=safe)
    return path


def _hash_fd(descriptor: int) -> tuple[str, int, int, int]:
    """Hash an already-open descriptor and require a stable inode."""

    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode):
        _fail("unsafe_path", "reference is not a regular file")
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    size = 0
    while block := os.read(descriptor, HASH_CHUNK_BYTES):
        digest.update(block)
        size += len(block)
    after = os.fstat(descriptor)
    if (
        before.st_ino != after.st_ino
        or before.st_dev != after.st_dev
        or before.st_size != after.st_size
        or size != before.st_size
    ):
        _fail("input_changed_during_admission", "file identity changed while hashing")
    return digest.hexdigest(), size, before.st_ino, before.st_dev


def _hash_file(path: Path) -> tuple[str, int, int, int]:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        return _hash_fd(descriptor)
    finally:
        os.close(descriptor)


def _snapshot(root: Path, relative: str) -> FileSnapshot:
    path = _relative(root, relative)
    digest, size, inode, device = _hash_file(path)
    return FileSnapshot(relative, digest, size, inode, device)


def _arrow_type(text: str) -> pa.DataType:
    if text == "int64":
        return pa.int64()
    if text == "int32":
        return pa.int32()
    if text == "string":
        return pa.string()
    if text == "bool":
        return pa.bool_()
    if text in _DICTIONARY_TYPES:
        return pa.dictionary(pa.int32(), pa.string())
    if text in {"list<item: string>", "list<element: string>"}:
        return pa.list_(pa.string())
    if text.startswith("decimal128(") and text.endswith(")"):
        raw = text[len("decimal128(") : -1]
        precision, _, scale = raw.partition(",")
        if precision.strip().isdigit() and scale.strip().isdigit():
            return pa.decimal128(int(precision), int(scale))
    _fail("unsupported_arrow_type", "Arrow contract type is not supported", arrow_type=text)


def _schema_from_fields(fields: Sequence[tuple[str, str, bool]]) -> pa.Schema:
    return pa.schema(
        [
            pa.field(name, _arrow_type(arrow_type), nullable=nullable)
            for name, arrow_type, nullable in fields
        ]
    )


def _footer_from_partition(path: Path, spec: OutputFileSpec) -> None:
    schema = spec.partition.get("schema")
    if type(schema) is not list or not schema:
        _fail("schema_mismatch", "a table manifest has no sealed Arrow contract", path=spec.relative_path)
    fields = []
    for field in schema:
        if type(field) is not dict or type(field.get("nullable")) is not bool:
            _fail("schema_mismatch", "sealed Arrow field is malformed", path=spec.relative_path)
        name = field.get("name")
        arrow_type = field.get("arrow_type")
        if type(name) is not str or type(arrow_type) is not str:
            _fail("schema_mismatch", "sealed Arrow field is malformed", path=spec.relative_path)
        fields.append((name, arrow_type, field["nullable"]))
    _footer_matches(
        path,
        ReferenceFile(
            relative_path=spec.relative_path,
            sha256=spec.sha256,
            rows=spec.rows,
            byte_size=spec.bytes,
            partition=spec.partition,
            is_table=True,
            schema_fields=tuple(fields),
        ),
    )


def _footer_matches(path: Path, spec: ReferenceFile) -> None:
    parquet = pq.ParquetFile(path)
    if not spec.schema_fields:
        _fail("schema_mismatch", "a table reference has no Arrow contract", path=spec.relative_path)
    expected = _schema_from_fields(spec.schema_fields)
    actual = parquet.schema_arrow
    def contract(schema: pa.Schema) -> tuple[tuple[str, str, bool], ...]:
        return tuple(
            (field.name, "list<string>" if str(field.type) in {"list<item: string>", "list<element: string>"} else str(field.type), field.nullable)
            for field in schema
        )
    if contract(actual) != contract(expected):
        _fail("schema_mismatch", "Parquet footer schema mismatch", path=spec.relative_path)
    if int(parquet.metadata.num_rows) != spec.rows:
        _fail(
            "row_mismatch",
            "Parquet footer row count mismatch",
            path=spec.relative_path,
            footer_rows=int(parquet.metadata.num_rows),
            declared_rows=spec.rows,
        )


_TIME_INTEGER_FIELDS = frozenset(
    {
        "open_time",
        "close_time",
        "create_time",
        "calc_time",
        "event_time_ms",
        "missing_run_start_ms",
        "missing_run_end_ms",
    }
)
_TIME_SCALE = {"s": 1, "ms": 1_000, "us": 1_000_000, "ns": 1_000_000_000}
_TIME_DIGITS = {"s": 0, "ms": 3, "us": 6, "ns": 9}


def _length_prefix(body: bytes) -> bytes:
    return len(body).to_bytes(4, "big") + body


def _render_timestamp(value: Any, unit: str) -> str:
    digits = _TIME_DIGITS[unit]
    if type(value) is int:
        scale = _TIME_SCALE[unit]
        seconds, remainder = divmod(value, scale) if unit != "s" else (value, 0)
        moment = datetime.fromtimestamp(seconds, timezone.utc)
        if digits == 0:
            return moment.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        width = len(str(scale - 1))
        return moment.strftime("%Y-%m-%dT%H:%M:%S") + f".{remainder:0{width}d}+00:00"
    if not isinstance(value, datetime):
        _fail("consumer_proof_unsupported", "timestamp value is not a temporal scalar")
    moment = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    if digits == 0:
        return moment.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    fraction = f"{moment.microsecond:06d}"
    if digits <= 6:
        fraction = fraction[:digits]
    else:
        fraction = fraction + ("0" * (digits - 6))
    return moment.strftime("%Y-%m-%dT%H:%M:%S") + f".{fraction}+00:00"


def _timestamp_sort_key(value: Any, unit: str) -> int:
    if type(value) is int:
        return value * (1_000_000_000 // _TIME_SCALE[unit])
    if not isinstance(value, datetime):
        _fail("consumer_proof_unsupported", "timestamp value is not a temporal scalar")
    moment = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = moment - epoch
    return ((delta.days * 86_400) + delta.seconds) * 1_000_000_000 + moment.microsecond * 1_000


def _encode_logical(value: Any, data_type: pa.DataType) -> bytes:
    """Length-prefixed logical token. Dictionary and plain strings share one token."""

    if value is None:
        return _length_prefix(b"\x00")
    if pa.types.is_boolean(data_type):
        return _length_prefix(b"\x01" if value is False else b"\x02")
    if pa.types.is_integer(data_type):
        return _length_prefix(b"\x03" + str(int(value)).encode("ascii"))
    if pa.types.is_decimal(data_type):
        # Arrow has already enforced scale. Formatting does not round a
        # precision-38 coefficient through the ambient decimal context.
        rendered = format(decimal.Decimal(value), f".{data_type.scale}f").encode("ascii")
        return _length_prefix(b"\x04" + rendered)
    if pa.types.is_timestamp(data_type):
        rendered = _render_timestamp(value, data_type.unit).encode("ascii")
        return _length_prefix(b"\x05" + rendered)
    if pa.types.is_dictionary(data_type):
        return _encode_logical(value, data_type.value_type)
    if pa.types.is_string(data_type) or pa.types.is_large_string(data_type):
        return _length_prefix(b"\x06" + str(value).encode("utf-8"))
    if pa.types.is_list(data_type) or pa.types.is_large_list(data_type):
        body = bytearray(b"\x07")
        body.extend(len(value).to_bytes(4, "big"))
        for item in value:
            body.extend(_encode_logical(item, data_type.value_type))
        return _length_prefix(bytes(body))
    _fail("unsupported_arrow_type", "logical digest type is not supported", arrow_type=str(data_type))


def _time_plan(schema: pa.Schema) -> tuple[tuple[int, ...], str]:
    timestamps = tuple(index for index, field in enumerate(schema) if pa.types.is_timestamp(field.type))
    if timestamps:
        return timestamps, "timestamp"
    integers = tuple(
        index
        for index, field in enumerate(schema)
        if pa.types.is_integer(field.type) and field.name in _TIME_INTEGER_FIELDS
    )
    if integers:
        return integers, "integer"
    return (), "absent"


def reference_proof_component(path: Path, relative_path: str, kind: str) -> dict[str, Any]:
    """Recompute one proof component from the file.

    Physical SHA-256 stays separate from the typed-row digest. Equal logical
    rows in dictionary and plain encodings share the digest. Metadata is not
    claimed as a table: its logical digest is the physical SHA-256, its row
    counts are zero, and its time reason is ``non_temporal_component``.
    """

    if kind not in {"table", "metadata"}:
        _fail("consumer_proof_unsupported", "proof component kind is not table or metadata", path=relative_path)
    digest, size, _inode, _device = _hash_file(path)
    if kind == "metadata":
        return {
            "relative_path": relative_path,
            "physical_sha256": digest,
            "physical_bytes": size,
            "kind": "metadata",
            "source_row_count": 0,
            "readback_row_count": 0,
            "source_value_sha256": digest,
            "roundtrip_value_sha256": digest,
            "time_start": None,
            "time_end": None,
            "time_absence_reason": "non_temporal_component",
            "value_identity": "metadata_bytes",
        }
    parquet = pq.ParquetFile(path)
    schema = parquet.schema_arrow
    logical = hashlib.sha256()
    counted = 0
    time_indexes, time_kind = _time_plan(schema)
    earliest: tuple[int, str] | None = None
    latest: tuple[int, str] | None = None
    for batch in parquet.iter_batches(batch_size=65_536):
        columns = [
            batch.column(index).cast(pa.int64()).to_pylist()
            if pa.types.is_timestamp(schema.field(index).type)
            else batch.column(index).to_pylist()
            for index in range(batch.num_columns)
        ]
        for row_index in range(batch.num_rows):
            for field_index, field in enumerate(schema):
                logical.update(_encode_logical(columns[field_index][row_index], field.type))
            for field_index in time_indexes:
                value = columns[field_index][row_index]
                if value is None:
                    continue
                field = schema.field(field_index)
                if time_kind == "timestamp":
                    key = _timestamp_sort_key(value, field.type.unit)
                    rendered = _render_timestamp(value, field.type.unit)
                else:
                    key = int(value)
                    rendered = str(int(value))
                pair = (key, rendered)
                if earliest is None or pair < earliest:
                    earliest = pair
                if latest is None or pair > latest:
                    latest = pair
            counted += 1
    footer_rows = int(parquet.metadata.num_rows)
    if counted != footer_rows:
        _fail(
            "row_mismatch",
            "typed readback row count differs from the Parquet footer",
            path=relative_path,
            readback_row_count=counted,
            footer_rows=footer_rows,
        )
    logical_digest = logical.hexdigest()
    if time_indexes and earliest is None:
        reason: str | None = "empty_component"
        start = None
        end = None
    elif not time_indexes:
        reason = "non_temporal_component"
        start = None
        end = None
    else:
        reason = None
        assert earliest is not None and latest is not None
        start = earliest[1]
        end = latest[1]
    return {
        "relative_path": relative_path,
        "physical_sha256": digest,
        "physical_bytes": size,
        "kind": "table",
        "source_row_count": counted,
        "readback_row_count": counted,
        "source_value_sha256": logical_digest,
        "roundtrip_value_sha256": logical_digest,
        "time_start": start,
        "time_end": end,
        "time_absence_reason": reason,
        "value_identity": "typed_row_digest",
    }


def _git_commit_exists(repo: Path, commit: str) -> None:
    """Read-only confirmation that ``commit`` is a commit object."""

    kind = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-t", f"{commit}^{{commit}}"],
        check=False,
        capture_output=True,
    )
    if kind.returncode != 0 or kind.stdout != b"commit\n":
        _fail("dirty_code", "code commit is not a committed object", commit=commit)


def _git_blob(repo: Path, commit: str, relative: str) -> bytes:
    """Read one committed blob. This does not update the repository."""

    blob = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "blob", f"{commit}:{relative}"],
        check=False,
        capture_output=True,
    )
    if blob.returncode != 0:
        _fail("dirty_code", "committed source blob is missing", path=relative, commit=commit)
    return blob.stdout


def seal_code_identity(
    repo: Path,
    commit: str,
    *,
    bind_runtime: bool,
    executing: Mapping[str, Path] | None = None,
    file_bytes: Mapping[str, bytes] | None = None,
) -> CodeIdentity:
    """Hash the five drop paths in path order.

    Injected ``file_bytes`` are the private fixture seam. Production reads the
    commit's blobs, the working tree, and the three executing files. Those
    three copies must be identical. Identity is the digest list, not a path.
    """

    _commit(commit)
    root = _anchor(repo)
    payloads: list[bytes] = []
    if file_bytes is not None:
        if bind_runtime:
            _fail("dirty_code", "runtime binding reads the repository, not injected bytes")
        if tuple(file_bytes) != CODE_PATHS and set(file_bytes) != set(CODE_PATHS):
            _fail("dirty_code", "injected code bytes must cover the five drop paths")
        payloads = [file_bytes[relative] for relative in CODE_PATHS]
    else:
        _git_commit_exists(root, commit)
        for relative in CODE_PATHS:
            blob = _git_blob(root, commit, relative)
            working = _relative(root, relative).read_bytes()
            if working != blob:
                _fail("dirty_code", "working tree differs from the committed blob", path=relative)
            payloads.append(blob)
        if bind_runtime:
            running = executing or {}
            if set(running) != set(RUNTIME_CODE_PATHS):
                _fail("dirty_code", "runtime binding requires the three executing files")
            for relative in RUNTIME_CODE_PATHS:
                current = running[relative].read_bytes()
                if current != payloads[CODE_PATHS.index(relative)]:
                    _fail("dirty_code", "executing source differs from the committed blob", path=relative)
    digests = [_sha256(payload) for payload in payloads]
    lock = _sha256("".join(digests).encode("ascii"))
    return CodeIdentity(commit=commit, lock_sha256=lock)


def production_release_policy(repo: Path, catalog_path: Path, code: CodeIdentity) -> ReleasePolicy:
    return ReleasePolicy(
        repo=repo,
        catalog_path=catalog_path,
        code=code,
        created_at=SEALED_CREATED_AT,
        bundle_allocation_bytes=HARMONIC_BUNDLE_ALLOCATION_BYTES,
        metadata_remainder_bytes=RELEASE_METADATA_REMAINDER_BYTES,
        operating_reserve_bytes=OPERATING_RESERVE_BYTES,
    )


def _require_bundle_arithmetic() -> None:
    index_bytes = SIZING_PROJECTED_BUNDLE_ROWS * FUTURE_REFERENCE_INDEX_BYTES_PER_ROW
    future = index_bytes + FUTURE_PARTITION_FIELD_BYTES + FUTURE_BUNDLE_DICTIONARY_BYTES
    provision = MEASURED_CURRENT_BUNDLE_BYTES + HARMONIC_BUNDLE_ALLOCATION_BYTES
    if future != HARMONIC_BUNDLE_ALLOCATION_BYTES or provision != CURRENT_PLUS_FUTURE_PROVISION_BYTES:
        _fail("bundle_allocation_pin", "bundle provision arithmetic drifted")


def _check_policy(policy: ReleasePolicy) -> Path:
    root = _anchor(policy.repo)
    _require_bundle_arithmetic()
    _commit(policy.code.commit)
    _hex64(policy.code.lock_sha256, "code lock")
    if policy.created_at != SEALED_CREATED_AT:
        _fail("bookkeeping_clock", "reference created_at is the sealed epoch bookkeeping instant")
    if policy.spend_operating_reserve or policy.operating_reserve_bytes != OPERATING_RESERVE_BYTES:
        _fail(
            "operating_reserve_not_preserved",
            "the operating reserve is not free space and is not spent",
            operating_reserve_bytes=policy.operating_reserve_bytes,
        )
    if policy.enforce_published_allocation and policy.bundle_allocation_bytes != HARMONIC_BUNDLE_ALLOCATION_BYTES:
        _fail(
            "bundle_allocation_pin",
            "bundle file cap must stay at the future-only harmonic charge",
            bundle_allocation_bytes=policy.bundle_allocation_bytes,
            measured_current_bundle_bytes=MEASURED_CURRENT_BUNDLE_BYTES,
        )
    if policy.enforce_metadata_pin and policy.metadata_remainder_bytes != RELEASE_METADATA_REMAINDER_BYTES:
        _fail(
            "metadata_remainder_pin",
            "metadata remainder must stay at the post-coverage reservation",
            metadata_remainder_bytes=policy.metadata_remainder_bytes,
        )
    if policy.bundle_allocation_bytes < 0 or policy.metadata_remainder_bytes < 0:
        _fail("metadata_remainder_exceeded", "resource bounds are negative")
    safe_root = assert_relative_safe(policy.bundle_root_relative, label="bundle root")
    if safe_root != BUNDLE_ROOT_RELATIVE:
        _fail("unsafe_path", "bundle metadata root is fixed", path=safe_root)
    return root


def _bundle_root(root: Path) -> Path:
    """Create missing bundle directories without changing existing ancestors."""

    cursor = root
    for part in BUNDLE_ROOT_RELATIVE.split("/"):
        cursor = cursor / part
        if cursor.is_symlink():
            _fail("unsafe_path", "bundle ancestor is a symlink", path=str(cursor))
        created = False
        if not cursor.exists():
            cursor.mkdir(mode=0o700)
            created = True
        facts = cursor.lstat()
        if stat.S_ISLNK(facts.st_mode) or not stat.S_ISDIR(facts.st_mode):
            _fail("unsafe_path", "bundle ancestor is not a real directory", path=str(cursor))
        if created:
            os.chmod(cursor, 0o700)
    path = lexical_join(root, BUNDLE_ROOT_RELATIVE)
    assert_no_symlink_components(path, stop_at=root)
    return path


def _lock_bundle(root: Path) -> int:
    bundle = _bundle_root(root)
    descriptor = os.open(bundle, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
    except OSError:
        os.close(descriptor)
        raise
    return descriptor


def _unlock(descriptor: int) -> None:
    fcntl.flock(descriptor, fcntl.LOCK_UN)
    os.close(descriptor)


def _rename_noreplace(directory: int, source: str, destination: str) -> None:
    result = _LIBC.renameat2(directory, source.encode(), directory, destination.encode(), RENAME_NOREPLACE)
    if result == 0:
        return
    error = ctypes.get_errno()
    raise OSError(error, os.strerror(error), destination)


def _open_directory(root: Path, relative_dir: str) -> int:
    current = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    if relative_dir in ("", "."):
        return current
    try:
        for part in assert_relative_safe(relative_dir, label="output directory").split("/"):
            created = False
            try:
                os.mkdir(part, 0o700, dir_fd=current)
                os.fsync(current)
                created = True
            except FileExistsError:
                created = False
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
            facts = os.fstat(child)
            if not stat.S_ISDIR(facts.st_mode):
                os.close(child)
                _fail("unsafe_path", "output parent is not a directory", name=part)
            if created:
                os.fchmod(child, 0o700)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _write_exclusive(root: Path, relative: str, payload: bytes) -> str:
    """Content-addressed no-clobber write. Returns ``created`` or ``reused``."""

    safe = assert_relative_safe(relative, label="output path")
    parent, _, name = safe.rpartition("/")
    directory = _open_directory(root, parent)
    temporary = f".{name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    stage: int | None = None
    renamed = False
    try:
        stage = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        view = memoryview(payload)
        while view:
            written = os.write(stage, view)
            if written <= 0:
                _fail("durability", "temporary release write made no progress", path=safe)
            view = view[written:]
        os.fchmod(stage, 0o600)
        os.fsync(stage)
        try:
            _rename_noreplace(directory, temporary, name)
            os.fsync(directory)
            renamed = True
            outcome = "created"
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
            outcome = "reused"
        winner = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
        try:
            digest, size, _inode, _device = _hash_fd(winner)
        finally:
            os.close(winner)
        if digest != _sha256(payload) or size != len(payload):
            _fail("conflicting_occupant", "content-addressed path holds different bytes", path=safe)
        if not renamed:
            os.unlink(temporary, dir_fd=directory)
            os.fsync(directory)
        return outcome
    except BaseException:
        if not renamed:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass
        raise
    finally:
        if stage is not None:
            os.close(stage)
        os.close(directory)


def write_new_bundle_object(repo: Path, payload: bytes, policy: ReleasePolicy | None = None) -> tuple[str, str, int]:
    """Place one new bundle Parquet under the content-addressed object root."""

    root = _anchor(repo)
    held = _lock_bundle(root)
    try:
        digest = _sha256(payload)
        relative = f"{BUNDLE_ROOT_RELATIVE}/.objects/{digest[:2]}/{digest}"
        if policy is not None:
            objects, other = _tree_bytes(root)
            incoming = 0 if lexical_join(root, relative).exists() else len(payload)
            _enforce_resources(
                policy, root, objects + incoming, other,
                stage="bundle_write",
                incoming_bytes=incoming,
            )
        _write_exclusive(root, relative, payload)
        return relative, digest, len(payload)
    finally:
        _unlock(held)


def manifest_bytes(manifest: DatasetManifest) -> bytes:
    return (dumps_canonical(full_manifest_dict(manifest)) + "\n").encode("utf-8")


def manifest_for_plan(
    plan: ReferenceDatasetPlan,
    policy: ReleasePolicy,
    *,
    dependency_ids: Mapping[str, str],
) -> DatasetManifest:
    if not plan.files:
        _fail("empty_required", "a reference dataset declares no artifacts", dataset_type=plan.dataset_type)
    _hex64(plan.schema_fingerprint, f"{plan.dataset_type} schema fingerprint")
    files = []
    seen: set[str] = set()
    for spec in plan.files:
        relative = assert_relative_safe(spec.relative_path, label="reference path")
        if relative in seen:
            _fail("duplicate_reference", "a dataset repeats a logical path", path=relative)
        seen.add(relative)
        _hex64(spec.sha256, relative)
        if spec.rows < 0 or spec.byte_size < 0:
            _fail("row_mismatch", "negative file accounting", path=relative)
        if not spec.is_table and spec.rows != 0:
            _fail("metadata_row", "metadata references have table row count zero", path=relative)
        partition = dict(spec.partition)
        if spec.is_table:
            if not spec.schema_fields:
                _fail("schema_mismatch", "a table reference has no Arrow contract", path=relative)
            partition["kind"] = "table"
            partition["schema"] = [
                {"name": name, "arrow_type": arrow_type, "nullable": nullable}
                for name, arrow_type, nullable in spec.schema_fields
            ]
        else:
            partition["kind"] = "metadata"
            partition.pop("schema", None)
        files.append(
            OutputFileSpec(
                relative_path=relative,
                sha256=spec.sha256,
                rows=spec.rows,
                bytes=spec.byte_size,
                partition=partition,
                rows_verified=True,
            )
        )
    missing = [role for role in plan.dependency_roles if role not in dependency_ids]
    if missing:
        _fail("missing_dependency", "bundle dependency dataset is unknown", roles=missing)
    dependencies = tuple(
        DependencyRef(id=dependency_ids[role], kind=DependencyKind.DATASET, role=role)
        for role in plan.dependency_roles
    )
    schema = SchemaIdentity(plan.dataset_type, SCHEMA_VERSION, plan.schema_fingerprint)
    transform = TransformSpec(TRANSFORM_NAME, TRANSFORM_VERSION)
    statistics = DatasetStatistics(
        row_count=sum(spec.rows for spec in files),
        byte_size=sum(spec.bytes for spec in files),
    )
    quality = dict(plan.quality_summary)
    base = DatasetManifest(
        dataset_id="",
        dataset_type=plan.dataset_type,
        schema=schema,
        transform=transform,
        code=policy.code,
        config=ConfigIdentity(config_sha256=""),
        dependencies=dependencies,
        files=tuple(files),
        statistics=statistics,
        coverage=CoverageWindow(),
        quality_status=QualityStatus.PASS,
        quality_summary=quality,
        publication=PublicationMetadata(
            created_at=policy.created_at,
            publisher=PUBLISHER_NAME,
            publisher_version=PUBLISHER_VERSION,
        ),
    )
    # Config is attached below once the caller-supplied digest is known. The
    # empty placeholder is replaced before either identifier is computed.
    return base


def _with_config(manifest: DatasetManifest, config_sha256: str) -> DatasetManifest:
    _hex64(config_sha256, "config")
    current = replace(manifest, config=ConfigIdentity(config_sha256=config_sha256), dataset_id="", manifest_sha256="")
    payload = identity_payload(
        dataset_type=current.dataset_type,
        schema=current.schema,
        transform=current.transform,
        code=current.code,
        config=current.config,
        dependencies=current.dependencies,
        files=current.files,
        statistics=current.statistics,
        coverage=current.coverage,
        quality_status=current.quality_status,
        quality_summary=current.quality_summary,
        supersedes_dataset_id=None,
    )
    dataset_id, _digest = compute_dataset_id(payload)
    identified = replace(current, dataset_id=dataset_id)
    return replace(identified, manifest_sha256=compute_manifest_sha256(identified))


def _authenticate_files(root: Path, manifest: DatasetManifest, plans_by_type: Mapping[str, ReferenceDatasetPlan]) -> None:
    plan = plans_by_type[manifest.dataset_type]
    by_path = {spec.relative_path: spec for spec in plan.files}
    for spec in manifest.files:
        snapshot = _snapshot(root, spec.relative_path)
        if snapshot.sha256 != spec.sha256 or snapshot.byte_size != spec.bytes:
            _fail(
                "reference_mismatch",
                "referenced bytes differ from the manifest",
                path=spec.relative_path,
            )
        source = by_path[spec.relative_path]
        if source.is_table:
            _footer_matches(_relative(root, spec.relative_path), source)


def _sqlite_reservation(manifests: Sequence[DatasetManifest]) -> int:
    """Bound packed SQLite records plus indexes and concurrent DB/WAL/temp.

    The prior per-row page charge cannot admit the accepted reference count.
    Actual serialized lengths include each dataset ID, SHA, storage URI and
    partition JSON. Fourfold room covers the table, the composite
    (dataset_id, storage_uri) primary-key index, the file_sha256 index, and
    page fill/overflow; 256 additional bytes per row cover record headers,
    rowids and cell pointers. Three file copies cover database and WAL growth
    with another margin. SQLite temp_store is MEMORY during admission. Fixed
    pages cover headers and rounding.
    """

    logical_bytes = 64 * SQLITE_PAGE_BYTES
    for item in manifests:
        logical_bytes += 256 + len(_dumps(item.quality_summary)) + len(item.dataset_type) + 1024
        for spec in item.files:
            logical_bytes += (
                256 + len(item.dataset_id) + len(spec.sha256)
                + len(spec.relative_path.encode("utf-8"))
                + len(_dumps(dict(spec.partition))) + 32
            )
        for dep in item.dependencies:
            logical_bytes += 256 + len(item.dataset_id) + len(dep.id) + len(dep.role)
    pages = (logical_bytes + SQLITE_PAGE_BYTES - 1) // SQLITE_PAGE_BYTES
    return pages * SQLITE_PAGE_BYTES * 12


def _resource_totals(
    manifests: Sequence[DatasetManifest],
    *,
    manifest_payload_bytes: int,
    prepared_bytes: int,
    publication_bytes: int,
    proof_bytes: int = 0,
    leftover_bytes: int = 0,
) -> tuple[int, int, int]:
    bundle = next(item for item in manifests if item.dependencies)
    bundle_bytes = sum(
        spec.bytes for spec in bundle.files if spec.relative_path.startswith(f"{BUNDLE_ROOT_RELATIVE}/.objects/")
    )
    sqlite_bytes = _sqlite_reservation(manifests)
    metadata_bytes = (
        manifest_payload_bytes + prepared_bytes + publication_bytes + proof_bytes + leftover_bytes + sqlite_bytes
    )
    return bundle_bytes, metadata_bytes, sqlite_bytes


def _tree_bytes(root: Path) -> tuple[int, int]:
    """Return ``(admitted-object bytes, other candidate bytes)`` already on disk."""

    base = lexical_join(root, BUNDLE_ROOT_RELATIVE)
    if not base.exists():
        return 0, 0
    objects = 0
    other = 0
    for directory, dirnames, filenames in os.walk(base, followlinks=False):
        current = Path(directory)
        for name in list(dirnames):
            child = current / name
            if child.is_symlink():
                _fail("unsafe_path", "bundle tree contains a symlink", path=str(child))
        for name in filenames:
            child = current / name
            if child.is_symlink() or not stat.S_ISREG(child.lstat().st_mode):
                _fail("unsafe_path", "bundle tree contains a non-regular file", path=str(child))
            size = child.lstat().st_size
            relative = child.relative_to(base).as_posix()
            if relative.startswith(".objects/"):
                objects += size
            else:
                other += size
    return objects, other


def _free_bytes(path: Path, observed: int | None) -> int:
    if observed is not None:
        if type(observed) is not int or observed < 0:
            _fail("operating_reserve_not_preserved", "observed free space is not a byte count")
        return observed
    facts = os.statvfs(path if path.is_dir() else path.parent)
    return int(facts.f_bavail) * int(facts.f_frsize)


def _enforce_resources(
    policy: ReleasePolicy,
    root: Path,
    bundle_bytes: int,
    metadata_bytes: int,
    *,
    stage: str,
    incoming_bytes: int,
) -> None:
    if bundle_bytes > policy.bundle_allocation_bytes:
        _fail(
            "bundle_allocation_exceeded",
            "bundle parquet exceeds the conservative future-charge cap",
            stage=stage,
            bundle_bytes=bundle_bytes,
            bundle_allocation_bytes=policy.bundle_allocation_bytes,
            measured_current_bundle_bytes=MEASURED_CURRENT_BUNDLE_BYTES,
        )
    if metadata_bytes > policy.metadata_remainder_bytes:
        _fail(
            "metadata_remainder_exceeded",
            "new release metadata exceeds the post-coverage remainder",
            stage=stage,
            metadata_bytes=metadata_bytes,
            metadata_remainder_bytes=policy.metadata_remainder_bytes,
            release_metadata_bytes=RELEASE_METADATA_BYTES,
        )
    catalog = _require_catalog_file(policy)
    bundle_free = _free_bytes(root, policy.observed_free_bytes)
    catalog_free = _free_bytes(catalog, policy.observed_free_bytes)
    # Admission can grow SQLite, WAL and temp on the catalog filesystem.
    # metadata_bytes includes that reservation; on one filesystem it also
    # covers new durable descriptors and any owned stage left by a crash.
    staged = incoming_bytes * 2
    same_device = root.stat().st_dev == catalog.stat().st_dev
    if same_device:
        if bundle_free < OPERATING_RESERVE_BYTES + staged + metadata_bytes:
            _fail(
                "operating_reserve_not_preserved",
                "filesystem free space would consume the operating reserve",
                stage=stage,
                free_bytes=bundle_free,
                incoming_bytes=staged,
                operating_reserve_bytes=OPERATING_RESERVE_BYTES,
            )
        return
    if bundle_free < OPERATING_RESERVE_BYTES + staged:
        _fail(
            "operating_reserve_not_preserved",
            "bundle filesystem free space would consume the operating reserve",
            stage=stage,
            free_bytes=bundle_free,
            incoming_bytes=staged,
        )
    if catalog_free < OPERATING_RESERVE_BYTES + metadata_bytes:
        _fail(
            "operating_reserve_not_preserved",
            "catalog filesystem free space would consume the operating reserve",
            stage=stage,
            free_bytes=catalog_free,
        )


def _require_catalog_file(policy: ReleasePolicy) -> Path:
    path = policy.catalog_path
    if path.is_symlink():
        _fail("unsafe_path", "catalog path is a symlink", path=str(path))
    try:
        facts = path.lstat()
    except OSError as exc:
        _fail("unsafe_path", "catalog database is absent", path=str(path), error=str(exc))
    if stat.S_ISLNK(facts.st_mode) or not stat.S_ISREG(facts.st_mode):
        _fail("unsafe_path", "catalog database is not a regular file", path=str(path))
    return path


def _require_connection_binding(connection: sqlite3.Connection, catalog: Path) -> None:
    if connection.in_transaction or connection.isolation_level is not None:
        _fail("pending_catalog_transaction", "admission requires an idle autocommit connection")
    row = connection.execute("PRAGMA database_list").fetchone()
    database = "" if row is None else str((row["file"] if isinstance(row, sqlite3.Row) else row[2]) or "")
    if not database or not os.path.samefile(database, catalog):
        _fail("unsafe_path", "connection is not bound to the release catalog", path=database)


def _release_charge(
    root: Path,
    manifests: Sequence[DatasetManifest],
    planned: Sequence[tuple[str, int]],
) -> tuple[int, int, int]:
    """Return bundle bytes, metadata bytes, and bytes that do not exist yet.

    Existing bundle-root files count once. The admitted bundle object is
    excluded from metadata. Content-addressed files already on disk are not
    added again. Incoming bytes are charged twice later against free space
    because the stage and the final name coexist.
    """

    bundle_bytes, _ignored, sqlite_bytes = _resource_totals(
        manifests,
        manifest_payload_bytes=0,
        prepared_bytes=0,
        publication_bytes=0,
    )
    objects, other = _tree_bytes(root)
    incoming = 0
    for relative, nbytes in planned:
        path = lexical_join(root, relative)
        if path.is_symlink():
            _fail("unsafe_path", "planned release path is a symlink", path=relative)
        if not path.exists():
            incoming += nbytes
    metadata_bytes = other + max(0, objects - bundle_bytes) + incoming + sqlite_bytes
    return bundle_bytes, metadata_bytes, incoming


def _guard_resources(
    policy: ReleasePolicy,
    root: Path,
    bundle_bytes: int,
    metadata_bytes: int,
    *,
    stage: str,
    incoming_bytes: int,
) -> None:
    try:
        _enforce_resources(
            policy,
            root,
            bundle_bytes,
            metadata_bytes,
            stage=stage,
            incoming_bytes=incoming_bytes,
        )
    except ReleaseError as exc:
        if exc.blocker != "operating_reserve_not_preserved":
            _write_bounds(root, exc.blocker, exc.context)
        raise


def _write_bounds(root: Path, blocker: str, detail: Mapping[str, Any]) -> None:
    document = {
        "document_type": BOUNDS_DOCUMENT,
        "schema_version": 1,
        "consumable": False,
        "blocker": blocker,
        "detail": dict(detail),
    }
    payload = _canonical_document(document)
    relative = f"{BUNDLE_ROOT_RELATIVE}/.prepared/{_sha256(payload)}.json"
    _write_exclusive(root, relative, payload)


def _build_manifests(
    plans: Sequence[ReferenceDatasetPlan], policy: ReleasePolicy, config_sha256: str
) -> tuple[DatasetManifest, ...]:
    if len(plans) != 11:
        _fail("partial_release", "a reference release has eleven datasets", datasets=len(plans))
    types = [plan.dataset_type for plan in plans]
    forbidden = set(types) & {"bitmex_funding", "bitmex_funding_full"}
    if forbidden:
        _fail("mixed_authority", "false-authority dataset types cannot enter the release")
    if tuple(types) != REQUIRED_DATASET_TYPES:
        _fail("mixed_release", "reference dataset types must be the eleven-type chain in order")
    dependents = [plan for plan in plans if plan.dependency_roles]
    if len(dependents) != 1:
        _fail("bundle_dependencies", "exactly the bundle dataset depends on the other ten")
    bundle = dependents[0]
    if tuple(bundle.dependency_roles) != tuple(plan.dataset_type for plan in plans if plan is not bundle):
        _fail("bundle_dependencies", "bundle dependencies must be the other ten dataset types in order")
    product_plans = [plan for plan in plans if plan is not bundle]
    bare = [_with_config(manifest_for_plan(plan, policy, dependency_ids={}), config_sha256) for plan in product_plans]
    dependency_ids = {item.dataset_type: item.dataset_id for item in bare}
    bundle_manifest = _with_config(
        manifest_for_plan(bundle, policy, dependency_ids=dependency_ids),
        config_sha256,
    )
    return (*bare, bundle_manifest)


def identify_products(
    plans: Sequence[ReferenceDatasetPlan],
    policy: ReleasePolicy,
    config_sha256: str,
) -> tuple[DatasetManifest, ...]:
    """Dataset identities for the ten constituents, before the bundle file exists."""

    _check_policy(policy)
    if len(plans) != 10 or any(plan.dependency_roles for plan in plans):
        _fail("partial_release", "product identification requires the ten constituent plans")
    return tuple(
        _with_config(manifest_for_plan(plan, policy, dependency_ids={}), config_sha256) for plan in plans
    )


def _dataset_entry(item: DatasetManifest) -> dict[str, Any]:
    body = manifest_bytes(item)
    return {
        "dataset_id": item.dataset_id,
        "dataset_type": item.dataset_type,
        "manifest_sha256": item.manifest_sha256,
        "manifest_relative_path": f"{BUNDLE_ROOT_RELATIVE}/.manifests/{item.manifest_sha256}.json",
        "manifest_file_sha256": _sha256(body),
        "manifest_bytes": len(body),
        "bookkeeping_created_at": item.publication.created_at.isoformat(),
        "publisher": item.publication.publisher,
        "publisher_version": item.publication.publisher_version,
    }


def _descriptor(
    manifests: Sequence[DatasetManifest],
    *,
    document_type: str,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    datasets = [_dataset_entry(item) for item in manifests]
    return {
        "document_type": document_type,
        "schema_version": 1,
        "consumable": document_type == PUBLICATION_DOCUMENT,
        "catalog_commit_required": True,
        "filesystem_marker_is_not_visibility": True,
        "created_at": SEALED_CREATED_AT.isoformat(),
        "transform": {"name": TRANSFORM_NAME, "version": TRANSFORM_VERSION},
        "datasets": datasets,
        **dict(extra),
    }


def prepare_release(
    plans: Sequence[ReferenceDatasetPlan],
    policy: ReleasePolicy,
    *,
    config_sha256: str,
    authorities: Mapping[str, Any],
) -> PreparedRelease:
    """Write manifests and a non-consumable prepared descriptor. No catalog rows."""

    root = _check_policy(policy)
    manifests = _build_manifests(plans, policy, config_sha256)
    plans_by_type = {plan.dataset_type: plan for plan in plans}
    for manifest in manifests:
        _authenticate_files(root, manifest, plans_by_type)
    bodies = [manifest_bytes(manifest) for manifest in manifests]
    prepared = _descriptor(
        manifests,
        document_type=PREPARED_DOCUMENT,
        extra={"authorities": dict(authorities), "quality_summary_carries_descriptor_hash": False},
    )
    prepared_payload = _canonical_document(prepared)
    digest = _sha256(prepared_payload)
    prepared_relative = f"{BUNDLE_ROOT_RELATIVE}/.prepared/{digest}.json"
    planned = [
        (f"{BUNDLE_ROOT_RELATIVE}/.manifests/{manifest.manifest_sha256}.json", len(body))
        for manifest, body in zip(manifests, bodies, strict=True)
    ]
    planned.append((prepared_relative, len(prepared_payload)))
    held = _lock_bundle(root)
    try:
        bundle_bytes, metadata_bytes, incoming = _release_charge(root, manifests, planned)
        _guard_resources(
            policy,
            root,
            bundle_bytes,
            metadata_bytes,
            stage="prepare",
            incoming_bytes=incoming,
        )
        for manifest, body in zip(manifests, bodies, strict=True):
            relative = f"{BUNDLE_ROOT_RELATIVE}/.manifests/{manifest.manifest_sha256}.json"
            _write_exclusive(root, relative, body)
            loaded = load_manifest_bytes(body)
            if loaded.dataset_id != manifest.dataset_id or loaded.manifest_sha256 != manifest.manifest_sha256:
                _fail("manifest_identity", "manifest bytes do not round-trip", dataset_type=manifest.dataset_type)
        digest = _sha256(prepared_payload)
        relative = f"{BUNDLE_ROOT_RELATIVE}/.prepared/{digest}.json"
        _write_exclusive(root, relative, prepared_payload)
    finally:
        _unlock(held)
    return PreparedRelease(
        descriptor_sha256=digest,
        descriptor_relative_path=relative,
        manifests=manifests,
        dataset_ids={item.dataset_type: item.dataset_id for item in manifests},
        bundle_bytes=bundle_bytes,
        metadata_bytes=metadata_bytes,
    )


def _read_capped(path: Path, relative: str, maximum: int) -> tuple[str, bytes]:
    """Read one regular file through the descriptor that enforces the cap."""

    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail("unsafe_path", "metadata is not a regular file", path=relative)
        if before.st_size > maximum:
            _fail("metadata_bound", "metadata document exceeds its read bound", path=relative, byte_size=before.st_size)
        digest = hashlib.sha256()
        payload = bytearray()
        while block := os.read(descriptor, HASH_CHUNK_BYTES):
            if len(payload) + len(block) > maximum:
                _fail("metadata_bound", "metadata document exceeds its read bound", path=relative)
            digest.update(block)
            payload.extend(block)
        after = os.fstat(descriptor)
        if (
            before.st_ino != after.st_ino
            or before.st_dev != after.st_dev
            or before.st_size != after.st_size
            or len(payload) != before.st_size
        ):
            _fail("input_changed_during_admission", "metadata changed while reading", path=relative)
        return digest.hexdigest(), bytes(payload)
    finally:
        os.close(descriptor)


def _load_json(root: Path, relative: str, expected: str | None, maximum: int) -> tuple[dict[str, Any], bytes]:
    path = _relative(root, relative)
    digest, payload = _read_capped(path, relative, maximum)
    if expected is not None and digest != expected:
        _fail("reference_mismatch", "metadata digest mismatch", path=relative)
    if _sha256(payload) != digest:
        _fail("reference_mismatch", "metadata changed while reading", path=relative)
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ReleaseError(
            "metadata is not JSON",
            blocker="malformed_metadata",
            context={"path": relative},
        ) from exc
    if type(document) is not dict:
        _fail("malformed_metadata", "metadata root is not an object", path=relative)
    return document, payload


def _seal_manifest_entry(root: Path, entry: Mapping[str, Any], index: int) -> DatasetManifest:
    if type(entry) is not dict:
        _fail("malformed_metadata", "release dataset entry is malformed", index=index)
    manifest_path = str(entry.get("manifest_relative_path") or "")
    expected_file_sha = _hex64(entry.get("manifest_file_sha256"), "manifest file")
    expected_bytes = entry.get("manifest_bytes")
    if type(expected_bytes) is not int or expected_bytes < 0:
        _fail("manifest_identity", "manifest byte pin is absent", path=manifest_path)
    path = _relative(root, manifest_path)
    digest, body = _read_capped(path, manifest_path, MANIFEST_MAX_BYTES)
    if digest != expected_file_sha or len(body) != expected_bytes or _sha256(body) != expected_file_sha:
        _fail("manifest_identity", "manifest file bytes differ from the release pin", path=manifest_path)
    manifest = load_manifest_bytes(body)
    if manifest.dataset_id != entry.get("dataset_id") or manifest.manifest_sha256 != entry.get("manifest_sha256"):
        _fail("manifest_identity", "prepared manifest binding changed", path=manifest_path)
    if manifest.dataset_type != entry.get("dataset_type"):
        _fail("mixed_release", "manifest dataset type differs from the release entry", path=manifest_path)
    if manifest.transform.name != TRANSFORM_NAME or manifest.transform.version != TRANSFORM_VERSION:
        _fail("incompatible_release", "manifest transform is not the reference protocol")
    created = manifest.publication.created_at
    if created != SEALED_CREATED_AT or entry.get("bookkeeping_created_at") != created.isoformat():
        _fail("bookkeeping_clock", "manifest bookkeeping clock is not the sealed instant", path=manifest_path)
    if entry.get("publisher") != manifest.publication.publisher or manifest.publication.publisher != PUBLISHER_NAME:
        _fail("manifest_identity", "manifest publisher bookkeeping changed", path=manifest_path)
    if (
        entry.get("publisher_version") != manifest.publication.publisher_version
        or manifest.publication.publisher_version != PUBLISHER_VERSION
    ):
        _fail("manifest_identity", "manifest publisher version changed", path=manifest_path)
    if manifest.supersedes_dataset_id is not None:
        _fail("conflicting_release", "a reference dataset supersedes another dataset", dataset_id=manifest.dataset_id)
    for spec in manifest.files:
        kind = spec.partition.get("kind")
        if kind == "table":
            schema = spec.partition.get("schema")
            if type(schema) is not list or not schema:
                _fail("schema_mismatch", "a table manifest has no sealed Arrow contract", path=spec.relative_path)
        elif kind == "metadata":
            if spec.rows != 0:
                _fail("metadata_row", "metadata references have table row count zero", path=spec.relative_path)
        else:
            _fail("malformed_metadata", "manifest file kind is not table or metadata", path=spec.relative_path)
    return manifest


def _seal_chain(manifests: Sequence[DatasetManifest]) -> None:
    if tuple(item.dataset_type for item in manifests) != REQUIRED_DATASET_TYPES:
        _fail("mixed_release", "release chain is not the eleven dataset types in order")
    identifiers = [item.dataset_id for item in manifests]
    if len(set(identifiers)) != len(identifiers):
        _fail("mixed_release", "release dataset identifiers are not unique")
    if len({item.code.commit for item in manifests}) != 1 or len({item.code.lock_sha256 for item in manifests}) != 1:
        _fail("dirty_code", "release datasets were not sealed with one code identity")
    if len({item.config.config_sha256 for item in manifests}) != 1:
        _fail("incompatible_release", "release datasets were not sealed with one configuration")
    transforms = {(item.transform.name, item.transform.version) for item in manifests}
    if transforms != {(TRANSFORM_NAME, TRANSFORM_VERSION)}:
        _fail("incompatible_release", "release datasets do not share the reference transform")
    products = manifests[:10]
    bundle = manifests[10]
    for item in products:
        if item.dependencies:
            _fail("bundle_dependencies", "a constituent dataset has a dependency edge", dataset_type=item.dataset_type)
    expected_ids = tuple(item.dataset_id for item in products)
    expected_edges = set(zip(REQUIRED_DATASET_TYPES[:10], expected_ids, strict=True))
    actual_edges = [(item.role, item.id) for item in bundle.dependencies if item.kind is DependencyKind.DATASET]
    if len(bundle.dependencies) != 10 or len(actual_edges) != 10 or len(set(actual_edges)) != 10 or set(actual_edges) != expected_edges:
        _fail("bundle_dependencies", "bundle edges are not exactly the ten constituent identifiers")


def _load_prepared(root: Path, prepared_sha256: str) -> tuple[dict[str, Any], tuple[DatasetManifest, ...]]:
    _hex64(prepared_sha256, "prepared descriptor")
    relative = f"{BUNDLE_ROOT_RELATIVE}/.prepared/{prepared_sha256}.json"
    document, payload = _load_json(root, relative, prepared_sha256, PREPARED_MAX_BYTES)
    if document.get("document_type") != PREPARED_DOCUMENT or document.get("consumable") is not False:
        _fail("prepared_not_release", "descriptor is not an immutable prepared release")
    if _sha256(payload) != prepared_sha256:
        _fail("prepared_not_release", "prepared descriptor bytes changed")
    datasets = document.get("datasets")
    if type(datasets) is not list or len(datasets) != 11:
        _fail("partial_release", "prepared descriptor does not list eleven datasets")
    manifests = tuple(_seal_manifest_entry(root, entry, index) for index, entry in enumerate(datasets))
    _seal_chain(manifests)
    return document, manifests


def _verify_proof(
    root: Path,
    proof: Mapping[str, Any],
    manifests: Sequence[DatasetManifest],
    *,
    candidate_sha256: str,
    checker_sha256: str,
    nautilus_version: str,
) -> None:
    if set(proof) != PROOF_KEYS:
        _fail("consumer_proof_unsupported", "consumer proof keys are not the strict v1 set")
    if proof.get("document_type") != PROOF_DOCUMENT or proof.get("schema_version") != 1:
        _fail("consumer_proof_unsupported", "consumer proof is not strict v1")
    if proof.get("status") != "PASS":
        _fail("consumer_proof_status", "consumer proof status is not PASS")
    if proof.get("scope") != PROOF_SCOPE:
        _fail("consumer_proof_sample_only", "consumer proof scope is not the complete release")
    if proof.get("candidate_sha256") != candidate_sha256:
        _fail("consumer_proof_candidate_mismatch", "consumer proof is not bound to this prepared descriptor")
    if proof.get("checker_source_sha256") != checker_sha256 or not nautilus_version:
        _fail("consumer_proof_checker", "checker source or Nautilus version pin was not met")
    _hex64(checker_sha256, "checker source")
    if proof.get("nautilus_version") != nautilus_version:
        _fail("consumer_proof_checker", "Nautilus version pin was not met")
    entries = proof.get("datasets")
    if type(entries) is not list or len(entries) != len(manifests):
        _fail("consumer_proof_incomplete", "consumer proof datasets are absent")
    for manifest, entry in zip(manifests, entries, strict=True):
        if type(entry) is not dict or set(entry) != {"dataset_id", "components"}:
            _fail("consumer_proof_unsupported", "consumer proof dataset entry is not strict")
        if entry.get("dataset_id") != manifest.dataset_id:
            _fail("consumer_proof_incomplete", "consumer proof dataset order differs from the release chain")
        components = entry.get("components")
        if type(components) is not list:
            _fail("consumer_proof_incomplete", "consumer proof components are absent", dataset_id=manifest.dataset_id)
        observed: dict[str, Mapping[str, Any]] = {}
        for component in components:
            if type(component) is not dict or set(component) != COMPONENT_KEYS:
                _fail("consumer_proof_unsupported", "consumer proof component is not strict")
            path = component.get("relative_path")
            if type(path) is not str or path in observed:
                _fail("consumer_proof_incomplete", "consumer proof component path is invalid")
            if type(component.get("source_row_count")) is not int or type(component.get("physical_bytes")) is not int:
                _fail("consumer_proof_unsupported", "consumer proof row accounting is not an integer", path=path)
            observed[path] = component
        expected = {spec.relative_path: spec for spec in manifest.files}
        if set(observed) != set(expected):
            _fail(
                "consumer_proof_incomplete",
                "consumer proof files differ from the manifest",
                dataset_id=manifest.dataset_id,
            )
        for path, spec in expected.items():
            kind = spec.partition.get("kind")
            if kind not in {"table", "metadata"}:
                _fail("malformed_metadata", "manifest file kind is not table or metadata", path=path)
            recomputed = reference_proof_component(_relative(root, path), path, str(kind))
            component = observed[path]
            if dict(component) != recomputed or recomputed["physical_sha256"] != spec.sha256:
                _fail("consumer_proof_value_mismatch", "typed readback does not reconcile", path=path)
            if recomputed["physical_bytes"] != spec.bytes or recomputed["readback_row_count"] != spec.rows:
                _fail("consumer_proof_value_mismatch", "proof accounting differs from the manifest", path=path)
            if recomputed["source_row_count"] != recomputed["readback_row_count"]:
                _fail("consumer_proof_value_mismatch", "source and readback row counts differ", path=path)
            if recomputed["source_value_sha256"] != recomputed["roundtrip_value_sha256"]:
                _fail("consumer_proof_value_mismatch", "source and round-trip digests differ", path=path)


def _bitmex_snapshot(catalog: SqliteDatasetCatalog) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for target in BITMEX_FALSE_AUTHORITY_TARGETS:
        dataset = catalog.get_dataset(target.dataset_id)
        if dataset is None:
            _fail("bitmex_false_authority_missing", "a false-authority row is absent", dataset_id=target.dataset_id)
        summary = json.loads(dataset.get("quality_summary_json") or "{}")
        files = list(catalog.list_files(target.dataset_id))
        file_identity = [
            (str(item["storage_uri"]), str(item["file_sha256"]), int(item["byte_size"]), int(item["row_count"]))
            for item in files
        ]
        rows.append(
            (
                target.dataset_id,
                dataset.get("dataset_type"),
                dataset.get("quality_status"),
                dataset.get("publication_status"),
                dataset.get("created_at"),
                dataset.get("manifest_sha256"),
                summary.get("quarantine_marker"),
                tuple(file_identity),
                catalog.is_consumable(target.dataset_id),
            )
        )
    return rows


def _require_bitmex(rows: Sequence[tuple[Any, ...]]) -> None:
    if len(rows) != len(BITMEX_FALSE_AUTHORITY_TARGETS):
        _fail("bitmex_false_authority_missing", "false-authority snapshot is incomplete")
    for target, row in zip(BITMEX_FALSE_AUTHORITY_TARGETS, rows, strict=True):
        dataset_id, dataset_type, quality, publication, created, manifest, marker, files, consumable = row
        expected_files = ((target.relative_path, target.file_sha256, target.byte_size, target.rows),)
        if (
            dataset_id != target.dataset_id
            or dataset_type != target.dataset_type
            or quality != QualityStatus.REJECTED.value
            or publication != PublicationStatus.REGISTERED.value
            or created != target.created_at
            or manifest != target.manifest_sha256
            or marker != QUARANTINE_MARKER
            or files != expected_files
            or consumable
        ):
            _fail(
                "bitmex_false_authority_changed",
                "a false-authority row is not the accepted rejected snapshot",
                dataset_id=target.dataset_id,
            )


def _dumps(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _same_release(catalog: SqliteDatasetCatalog, manifest: DatasetManifest, publication_relative: str) -> bool:
    existing = catalog.get_dataset(manifest.dataset_id)
    if existing is None:
        return False
    if (
        existing.get("dataset_type") != manifest.dataset_type
        or existing.get("schema_version") != manifest.schema.version
        or (existing.get("schema_fingerprint") or None) != manifest.schema.fingerprint
        or existing.get("manifest_sha256") != manifest.manifest_sha256
        or existing.get("manifest_uri") != f"{BUNDLE_ROOT_RELATIVE}/.manifests/{manifest.manifest_sha256}.json"
        or existing.get("publication_uri") != publication_relative
        or existing.get("transform_name") != manifest.transform.name
        or existing.get("transform_version") != manifest.transform.version
        or existing.get("code_commit") != manifest.code.commit
        or existing.get("config_sha256") != manifest.config.config_sha256
        or int(existing.get("row_count")) != manifest.statistics.row_count
        or int(existing.get("byte_size")) != manifest.statistics.byte_size
        or existing.get("event_start") is not None
        or existing.get("event_end") is not None
        or existing.get("availability_start") is not None
        or existing.get("availability_end") is not None
        or existing.get("quality_status") != QualityStatus.PASS.value
        or (existing.get("quality_summary_json") or "{}") != _dumps(manifest.quality_summary)
        or existing.get("supersedes_dataset_id") is not None
        or existing.get("publication_status") != PublicationStatus.REGISTERED.value
        or existing.get("created_at") != SEALED_CREATED_AT.isoformat()
    ):
        return False
    files = {str(item["storage_uri"]): item for item in catalog.list_files(manifest.dataset_id)}
    if set(files) != {spec.relative_path for spec in manifest.files}:
        return False
    for spec in manifest.files:
        row = files[spec.relative_path]
        if (
            str(row["file_sha256"]) != spec.sha256
            or int(row["row_count"]) != spec.rows
            or int(row["byte_size"]) != spec.bytes
            or (row.get("partition_json") or "{}") != _dumps(spec.partition)
        ):
            return False
    expected = {(dep.id, dep.role) for dep in manifest.dependencies}
    actual = {(str(row["input_dataset_id"]), str(row["role"])) for row in catalog.list_dataset_inputs(manifest.dataset_id)}
    return actual == expected and not catalog.list_raw_inputs(manifest.dataset_id)


def _receipt(manifest: DatasetManifest, publication_relative: str) -> DatasetPublicationReceipt:
    manifest_relative = f"{BUNDLE_ROOT_RELATIVE}/.manifests/{manifest.manifest_sha256}.json"
    return DatasetPublicationReceipt(
        dataset_id=manifest.dataset_id,
        manifest_sha256=manifest.manifest_sha256,
        manifest_uri=manifest_relative,
        publication_uri=publication_relative,
        dataset_path=Path(manifest_relative),
        verified_outputs=manifest.files,
        publication_verified=False,
        object_prefix=BUNDLE_ROOT_RELATIVE,
        dependencies=manifest.dependencies,
        supersedes_dataset_id=None,
        dataset_type=manifest.dataset_type,
        schema=manifest.schema,
        transform=manifest.transform,
        code=manifest.code,
        config=manifest.config,
        statistics=manifest.statistics,
        coverage=manifest.coverage,
        quality_status=manifest.quality_status,
        quality_summary=manifest.quality_summary,
        catalog_created_at=manifest.publication.created_at,
    )


def _classify(catalog: SqliteDatasetCatalog, manifests: Sequence[DatasetManifest], publication_relative: str) -> str:
    present = []
    for manifest in manifests:
        other = catalog.resolve_latest_by_type(manifest.dataset_type, consumable_only=True)
        if other is not None and other != manifest.dataset_id:
            return "conflict"
        if catalog.get_dataset(manifest.dataset_id) is None:
            present.append(False)
            continue
        if not _same_release(catalog, manifest, publication_relative):
            return "conflict"
        present.append(True)
    if all(present):
        return "identical"
    if any(present):
        return "partial"
    return "absent"


def _recheck(root: Path, snapshots: Sequence[FileSnapshot]) -> None:
    for prior in snapshots:
        current = _snapshot(root, prior.relative_path)
        if current != prior:
            _fail("input_changed_during_admission", "a referenced file changed before commit", path=prior.relative_path)


def _refuse_pending_caller(connection: sqlite3.Connection | None) -> None:
    """Reject caller work without committing or rolling it back."""

    if connection is None:
        return
    if connection.in_transaction or connection.isolation_level is not None:
        _fail("pending_catalog_transaction", "admission requires an idle autocommit connection")


def _open_catalog(policy: ReleasePolicy, connection: sqlite3.Connection | None) -> SqliteDatasetCatalog:
    _require_catalog_file(policy)
    _refuse_pending_caller(connection)
    if connection is not None:
        _require_connection_binding(connection, policy.catalog_path)
    catalog = SqliteDatasetCatalog(policy.catalog_path, connection=connection)
    if connection is None:
        # The adapter owns this connection. Clearing the default isolation
        # commits only the empty transaction opened by its own PRAGMA.
        catalog._conn.isolation_level = None
    # Keep SQLite's temporary sort/index work in memory so its disk growth is
    # confined to the checked catalog filesystem (database and WAL).
    catalog._conn.execute("PRAGMA temp_store = MEMORY")
    return catalog


def _open_readonly(policy: ReleasePolicy) -> SqliteDatasetCatalog:
    path = _require_catalog_file(policy)
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.isolation_level = None
    catalog = SqliteDatasetCatalog(path, connection=connection)
    catalog._conn.execute("PRAGMA query_only = ON")
    return catalog


def publish_release(
    policy: ReleasePolicy,
    prepared_sha256: str,
    proof_bytes: bytes,
    *,
    proof_sha256: str,
    checker_sha256: str,
    nautilus_version: str,
    hooks: ReleaseHooks | None = None,
    connection: sqlite3.Connection | None = None,
) -> PublishedRelease:
    """Admit all eleven datasets, or none, after the caller-pinned consumer proof."""

    root = _check_policy(policy)
    _refuse_pending_caller(connection)
    _hex64(checker_sha256, "checker source")
    _hex64(proof_sha256, "consumer proof")
    if not nautilus_version or any(char in nautilus_version for char in "\x00\n"):
        _fail("consumer_proof_checker", "Nautilus version pin is empty")
    if len(proof_bytes) > PROOF_MAX_BYTES:
        _fail("metadata_bound", "consumer proof exceeds its read bound")
    if _sha256(proof_bytes) != proof_sha256:
        _fail("consumer_proof_pin", "caller proof SHA-256 is not the admission pin")
    try:
        proof = json.loads(proof_bytes)
    except json.JSONDecodeError as exc:
        raise ReleaseError(
            "consumer proof is not JSON",
            blocker="consumer_proof_unsupported",
        ) from exc
    if type(proof) is not dict:
        _fail("consumer_proof_bare_pass", "a bare consumer proof cannot admit a release")
    if set(proof) == {"status"}:
        _fail("consumer_proof_bare_pass", "a bare PASS token cannot admit a release")
    held = _lock_bundle(root)
    catalog: SqliteDatasetCatalog | None = None
    try:
        _prepared, manifests = _load_prepared(root, prepared_sha256)
        for manifest in manifests:
            if (
                manifest.code.commit != policy.code.commit
                or manifest.code.lock_sha256 != policy.code.lock_sha256
            ):
                _fail("dirty_code", "prepared release was sealed with different code")
        _verify_proof(
            root,
            proof,
            manifests,
            candidate_sha256=prepared_sha256,
            checker_sha256=checker_sha256,
            nautilus_version=nautilus_version,
        )
        for manifest in manifests:
            if "publication_sha256" in manifest.quality_summary or "prepared_sha256" in manifest.quality_summary:
                _fail("circular_quality", "quality summary captures a publication descriptor")
        snapshots: list[FileSnapshot] = []
        prepared_relative = f"{BUNDLE_ROOT_RELATIVE}/.prepared/{prepared_sha256}.json"
        prepared_snapshot = _snapshot(root, prepared_relative)
        if prepared_snapshot.sha256 != prepared_sha256:
            _fail("input_changed_during_admission", "prepared descriptor changed after proof")
        snapshots.append(prepared_snapshot)
        for entry in _prepared["datasets"]:
            manifest_snapshot = _snapshot(root, str(entry["manifest_relative_path"]))
            if (manifest_snapshot.sha256, manifest_snapshot.byte_size) != (
                entry["manifest_file_sha256"], entry["manifest_bytes"]
            ):
                _fail("input_changed_during_admission", "manifest changed after proof")
            snapshots.append(manifest_snapshot)
        for manifest in manifests:
            for spec in manifest.files:
                current = _snapshot(root, spec.relative_path)
                if current.sha256 != spec.sha256 or current.byte_size != spec.bytes:
                    _fail("reference_mismatch", "referenced bytes changed after prepare", path=spec.relative_path)
                if spec.partition.get("kind") == "table":
                    _footer_from_partition(_relative(root, spec.relative_path), spec)
                snapshots.append(current)
        proof_relative = f"{BUNDLE_ROOT_RELATIVE}/.proofs/{proof_sha256}.json"
        publication = _descriptor(
            manifests,
            document_type=PUBLICATION_DOCUMENT,
            extra={
                "prepared_sha256": prepared_sha256,
                "proof_sha256": proof_sha256,
                "proof_relative_path": proof_relative,
                "proof_bytes": len(proof_bytes),
                "checker_source_sha256": checker_sha256,
                "nautilus_version": nautilus_version,
            },
        )
        publication_payload = _canonical_document(publication)
        publication_sha = _sha256(publication_payload)
        publication_relative = f"{BUNDLE_ROOT_RELATIVE}/.publication/{publication_sha}.json"
        bundle_bytes, metadata_bytes, incoming = _release_charge(
            root,
            manifests,
            (
                (publication_relative, len(publication_payload)),
                (proof_relative, len(proof_bytes)),
            ),
        )
        _guard_resources(
            policy,
            root,
            bundle_bytes,
            metadata_bytes,
            stage="publish",
            incoming_bytes=incoming,
        )
        catalog = _open_catalog(policy, connection)
        _require_bitmex(_bitmex_snapshot(catalog))
        _write_exclusive(root, proof_relative, proof_bytes)
        _write_exclusive(root, publication_relative, publication_payload)
        for relative, digest, byte_size in (
            (proof_relative, proof_sha256, len(proof_bytes)),
            (publication_relative, publication_sha, len(publication_payload)),
        ):
            current = _snapshot(root, relative)
            if (current.sha256, current.byte_size) != (digest, byte_size):
                _fail("input_changed_during_admission", "durable release metadata changed", path=relative)
            snapshots.append(current)
        fsync_file(_relative(root, publication_relative))
        if hooks and hooks.before_commit is not None:
            hooks.before_commit(_relative(root, publication_relative))
        _recheck(root, snapshots)
        _require_bitmex(_bitmex_snapshot(catalog))
        if catalog._conn.in_transaction:
            _fail("pending_catalog_transaction", "admission connection became busy")
        catalog._conn.execute("BEGIN IMMEDIATE")
        try:
            _require_bitmex(_bitmex_snapshot(catalog))
            _recheck(root, snapshots)
            kind = _classify(catalog, manifests, publication_relative)
            if kind == "identical":
                catalog._conn.rollback()
                published = PublishedRelease(
                    publication_sha256=publication_sha,
                    publication_relative_path=publication_relative,
                    prepared_sha256=prepared_sha256,
                    dataset_ids={item.dataset_type: item.dataset_id for item in manifests},
                    reused=True,
                    consumable=True,
                )
            elif kind == "partial":
                _fail("partial_release", "an incomplete reference release is already present")
            elif kind == "conflict":
                _fail("conflicting_release", "an existing dataset conflicts with this release")
            else:
                for index, manifest in enumerate(manifests, start=1):
                    # publication_verified stays false: insertion is authorized by
                    # the checks above, never by a caller's verified flag.
                    catalog._insert_all(_receipt(manifest, publication_relative), manifest)
                    if hooks is not None and hooks.after_insert is not None:
                        hooks.after_insert(index)
                _recheck(root, snapshots)
                _require_bitmex(_bitmex_snapshot(catalog))
                catalog._conn.commit()
                published = PublishedRelease(
                    publication_sha256=publication_sha,
                    publication_relative_path=publication_relative,
                    prepared_sha256=prepared_sha256,
                    dataset_ids={item.dataset_type: item.dataset_id for item in manifests},
                    reused=False,
                    consumable=True,
                )
        except BaseException:
            if catalog._conn.in_transaction:
                catalog._conn.rollback()
            raise
        if hooks and hooks.after_commit is not None:
            hooks.after_commit(published)
        return published
    finally:
        if catalog is not None and catalog._owned:
            catalog.close()
        _unlock(held)


def _require_publication_entries(document: Mapping[str, Any], manifests: Sequence[DatasetManifest]) -> None:
    entries = document.get("datasets")
    if type(entries) is not list or len(entries) != len(manifests):
        _fail("mixed_release", "publication datasets differ from the prepared manifests")
    for entry, manifest in zip(entries, manifests, strict=True):
        if type(entry) is not dict:
            _fail("mixed_release", "publication dataset entry is malformed")
        if entry != _dataset_entry(manifest):
            _fail(
                "mixed_release",
                "publication entry is not the sealed manifest",
                dataset_id=manifest.dataset_id,
            )


def read_release(
    policy: ReleasePolicy,
    publication_sha256: str,
    proof_bytes: bytes,
    *,
    proof_sha256: str,
    checker_sha256: str,
    nautilus_version: str,
    connection: sqlite3.Connection | None = None,
) -> PublishedRelease:
    """Reauthenticate one explicit publication. Prepared or mixed state fails."""

    root = _check_policy(policy)
    _refuse_pending_caller(connection)
    if connection is not None:
        _require_connection_binding(connection, _require_catalog_file(policy))
    _hex64(publication_sha256, "publication")
    _hex64(proof_sha256, "consumer proof")
    if len(proof_bytes) > PROOF_MAX_BYTES:
        _fail("metadata_bound", "consumer proof exceeds its read bound")
    if _sha256(proof_bytes) != proof_sha256:
        _fail("consumer_proof_pin", "caller proof SHA-256 is not the admission pin")
    relative = f"{BUNDLE_ROOT_RELATIVE}/.publication/{publication_sha256}.json"
    document, _payload = _load_json(root, relative, publication_sha256, PREPARED_MAX_BYTES)
    if document.get("document_type") != PUBLICATION_DOCUMENT or document.get("consumable") is not True:
        _fail("absent_release", "publication descriptor is not a final release")
    if document.get("proof_sha256") != proof_sha256 or document.get("proof_bytes") != len(proof_bytes):
        _fail("consumer_proof_pin", "publication proof pin does not match the caller bytes")
    proof_relative = str(document.get("proof_relative_path") or "")
    persisted_digest, persisted = _read_capped(_relative(root, proof_relative), proof_relative, PROOF_MAX_BYTES)
    if persisted_digest != proof_sha256 or persisted != proof_bytes:
        _fail("consumer_proof_pin", "persisted proof bytes differ from the caller pin")
    prepared_sha = str(document.get("prepared_sha256") or "")
    _prepared, manifests = _load_prepared(root, prepared_sha)
    for manifest in manifests:
        if manifest.code.commit != policy.code.commit or manifest.code.lock_sha256 != policy.code.lock_sha256:
            _fail("dirty_code", "publication was sealed with different code")
    try:
        proof = json.loads(proof_bytes)
    except json.JSONDecodeError as exc:
        raise ReleaseError(
            "consumer proof is not JSON",
            blocker="consumer_proof_unsupported",
        ) from exc
    if type(proof) is not dict or set(proof) == {"status"}:
        _fail("consumer_proof_bare_pass", "a bare PASS token is not a publication proof")
    if document.get("checker_source_sha256") != checker_sha256 or document.get("nautilus_version") != nautilus_version:
        _fail("consumer_proof_checker", "publication checker pins changed")
    _verify_proof(
        root,
        proof,
        manifests,
        candidate_sha256=prepared_sha,
        checker_sha256=checker_sha256,
        nautilus_version=nautilus_version,
    )
    _require_publication_entries(document, manifests)
    for manifest in manifests:
        for spec in manifest.files:
            snapshot = _snapshot(root, spec.relative_path)
            if snapshot.sha256 != spec.sha256 or snapshot.byte_size != spec.bytes:
                _fail("stale_release", "a published reference changed", path=spec.relative_path)
            if spec.partition.get("kind") == "table":
                _footer_from_partition(_relative(root, spec.relative_path), spec)
        if "publication_sha256" in _dumps(manifest.quality_summary) or "prepared_sha256" in _dumps(manifest.quality_summary):
            _fail("circular_quality", "quality summary captures the publication descriptor")
    catalog = _open_readonly(policy)
    try:
        catalog._conn.execute("BEGIN")
        try:
            _require_bitmex(_bitmex_snapshot(catalog))
            kind = _classify(catalog, manifests, relative)
            if kind != "identical":
                _fail(
                    "partial_release" if kind == "partial" else "mixed_release" if kind == "conflict" else "absent_release",
                    "catalog rows do not reproduce the publication",
                    state=kind,
                )
            for manifest in manifests:
                if not catalog.is_consumable(manifest.dataset_id):
                    _fail("absent_release", "a published dataset is not consumable", dataset_id=manifest.dataset_id)
            return PublishedRelease(
                publication_sha256=publication_sha256,
                publication_relative_path=relative,
                prepared_sha256=prepared_sha,
                dataset_ids={item.dataset_type: item.dataset_id for item in manifests},
                reused=True,
                consumable=True,
            )
        finally:
            catalog._conn.rollback()
    finally:
        catalog._conn.close()
