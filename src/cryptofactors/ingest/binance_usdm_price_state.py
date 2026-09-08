"""Normalize authenticated Binance USD-M hourly price-state archives.

One bounded pass reads premium-index rows once and publishes two independent,
hidden products.  Basis joins are exact on native symbol, open time, and close
time.  Relative basis is integer-floor arithmetic at scale 18; in particular,
negative non-terminating ratios floor toward negative infinity.
"""

from __future__ import annotations

import csv
import ctypes
import errno
import fcntl
import hashlib
import io
import json
import os
import re
import sqlite3
import stat
import uuid
import zipfile
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.acquisition.binance_usdm_harmonic_acquisition import (
    KIND_BINANCE,
    OUTCOME_CHECKSUM_VERIFIED,
    OUTCOME_RETAINED,
    PROVIDER_BINANCE,
    SIDECAR_CEILING_BYTES,
    STATE_APPLICATION_ID,
    STATE_USER_VERSION,
    AcquisitionState,
    register_domain_functions,
)
from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    KNOWN_ARCHIVE_SCHEMAS,
)
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    DECIMAL_SCALE,
    PARQUET_COMPRESSION,
    PARQUET_COMPRESSION_LEVEL,
    PARQUET_VERSION,
    PRODUCT_FUNDING_INDICATIVE_1H,
    PRODUCT_MARK_INDEX_BASIS_1H,
    QUALITY_GAP_COLUMNS,
    SIZING_ROW_BATCH,
    convert_decimal,
    convert_integer,
    final_product_schema,
    native_identity,
    product_schema_identity,
    writer_identity,
)

INDICATIVE_PRODUCT = PRODUCT_FUNDING_INDICATIVE_1H
BASIS_PRODUCT = PRODUCT_MARK_INDEX_BASIS_1H
PRODUCTS = (INDICATIVE_PRODUCT, BASIS_PRODUCT)
PREMIUM = "premium"
MARK = "mark"
INDEX = "index"
KINDS = (PREMIUM, MARK, INDEX)
FAMILY_BY_KIND_PERIOD = {
    (PREMIUM, "daily"): "daily/premiumIndexKlines",
    (PREMIUM, "monthly"): "monthly/premiumIndexKlines",
    (MARK, "daily"): "daily/markPriceKlines",
    (MARK, "monthly"): "monthly/markPriceKlines",
    (INDEX, "daily"): "daily/indexPriceKlines",
    (INDEX, "monthly"): "monthly/indexPriceKlines",
}
KIND_BY_FAMILY = {value: key[0] for key, value in FAMILY_BY_KIND_PERIOD.items()}
FAMILIES = tuple(FAMILY_BY_KIND_PERIOD.values())
FIELDS = KNOWN_ARCHIVE_SCHEMAS["premiumIndexKlines"]["headerless"]
INDICATIVE_SCHEMA = final_product_schema(INDICATIVE_PRODUCT)
BASIS_SCHEMA = final_product_schema(BASIS_PRODUCT)
SCHEMAS = {INDICATIVE_PRODUCT: INDICATIVE_SCHEMA, BASIS_PRODUCT: BASIS_SCHEMA}
SCHEMA_SHA256 = {product: product_schema_identity(product) for product in PRODUCTS}
QUALITY_GAP_SCHEMA = pa.schema([column.field() for column in QUALITY_GAP_COLUMNS])

EXPECTED_CADENCE_MS = 3_600_000
EXPECTED_CLOSE_OFFSET_MS = 3_599_999
MAX_COMPRESSED_OBJECT_BYTES = 64 * 2**20
MAX_DECOMPRESSED_MEMBER_BYTES = 128 * 2**20
MAX_ROWS_PER_OBJECT = 1_024
MAX_CSV_FIELD_BYTES = 1 * 2**20
MAX_REPORT_BYTES = 16 * 2**20
MAX_SIZING_BYTES = 48 * 2**20
MAX_SIDECAR_BYTES = SIDECAR_CEILING_BYTES
RENAME_NOREPLACE = 1

REPORT_SHA256 = "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
SIZING_SHA256 = "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589"
SIZING_POLICY_IDENTITY = "adr0027_review257_partition_aware_dictionary_storage_sizing_v3"
ACCEPTED_GENERATION0_BINANCE_COMPLETIONS = 685_072
ACCEPTED_GENERATION0_SEAL_HEAD = "8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab"
ACCEPTED_FAMILY_COUNTS = {
    "daily/indexPriceKlines": 12_266,
    "monthly/indexPriceKlines": 21_721,
    "daily/markPriceKlines": 14_096,
    "monthly/markPriceKlines": 22_286,
    "daily/premiumIndexKlines": 11_439,
    "monthly/premiumIndexKlines": 20_932,
}
ACCEPTED_FAMILY_BYTES = {
    "daily/indexPriceKlines": 10_088_018,
    "monthly/indexPriceKlines": 372_102_491,
    "daily/markPriceKlines": 10_458_575,
    "monthly/markPriceKlines": 346_831_322,
    "daily/premiumIndexKlines": 8_452_758,
    "monthly/premiumIndexKlines": 290_695_727,
}
ACCEPTED_FAMILY_RETAINED = {
    "daily/indexPriceKlines": 1,
    "monthly/indexPriceKlines": 9,
    "daily/markPriceKlines": 0,
    "monthly/markPriceKlines": 9,
    "daily/premiumIndexKlines": 1,
    "monthly/premiumIndexKlines": 9,
}
ACCEPTED_SOURCE_COUNT = 102_740
ACCEPTED_SOURCE_BYTES = 1_038_628_891
ACCEPTED_CHECKSUM_VERIFIED = 102_711
ACCEPTED_RETAINED = 29
ACCEPTED_PREMIUM_SOURCES = 32_371
ACCEPTED_PREMIUM_BYTES = 299_148_485
ACCEPTED_UNION_PARTITIONS = 23_268
ACCEPTED_PREMIUM_PARTITIONS = 21_507
ACCEPTED_JOINABLE_PARTITIONS = 21_491
ACCEPTED_PROJECTIONS = {
    INDICATIVE_PRODUCT: {
        "input_objects": 32_371,
        "input_compressed_bytes": 299_148_485,
        "partition_count": 21_507,
        "projected_rows": 44_004_402,
        "projected_bytes": 1_673_172_337,
        "largest_partition_bytes": 118_691,
    },
    BASIS_PRODUCT: {
        "input_objects": 102_740,
        "input_compressed_bytes": 1_038_628_891,
        "partition_count": 23_268,
        "projected_rows": 58_024_098,
        "projected_bytes": 3_312_444_308,
        "largest_partition_bytes": 265_090,
    },
}

INDICATIVE_UNAVAILABLE = "direct_indicative_rate_unavailable"
BASIS_JOIN_STATUS = "causal_open_time_join"
UNKNOWN_AVAILABILITY = "unknown_not_imputed"
IDENTICAL_OBSERVATION = "identical_source_observation"
_HEX_RE = re.compile(r"[0-9a-f]{64}")
_SIDECAR_STATEMENT = re.compile(r"([0-9a-fA-F]{64})[ \t]+(\S+)\s*")
_SOURCE_RE = re.compile(
    r"data/futures/um/(?P<period_type>daily|monthly)/"
    r"(?P<archive>premiumIndexKlines|markPriceKlines|indexPriceKlines)/"
    r"(?P<symbol>[A-Z0-9_]+)/1h/(?P=symbol)-1h-"
    r"(?P<period>\d{4}-\d{2}(?:-\d{2})?)\.zip"
)


class PriceStateNormalizationError(RuntimeError):
    """Fail-closed authority, economic, join, or publication error."""


@dataclass(frozen=True, slots=True)
class RawPriceStateObject:
    source_key: str
    family: str
    kind: str
    native_symbol: str
    economic_period: str
    path: Path
    source_sha256: str
    byte_size: int
    validation_state: str
    checksum_authority: str = "binance_checksum_sidecar"
    retrieval_time: str | None = None
    source_available_at: int | None = None


@dataclass(frozen=True, slots=True)
class PublishedPartition:
    product: str
    native_symbol: str
    utc_month: str
    row_count: int
    physical_row_count: int
    collapsed_row_count: int
    unjoinable_row_count: int
    parquet_path: Path
    parquet_sha256: str
    lineage_path: Path
    lineage_sha256: str
    reused: bool


@dataclass(frozen=True, slots=True)
class PublishedGapArtifact:
    product: str
    native_symbol: str
    utc_month: str
    row_count: int
    missing_grid_points: int
    unjoinable_source_rows: int
    parquet_path: Path
    parquet_sha256: str
    lineage_path: Path
    lineage_sha256: str
    reused: bool


@dataclass(frozen=True, slots=True)
class ProductResult:
    product: str
    schema_sha256: str
    partitions: tuple[PublishedPartition, ...]
    gap_artifacts: tuple[PublishedGapArtifact, ...]
    completion_path: Path
    completion_sha256: str
    completion_reused: bool
    physical_source_rows: int
    collapsed_identical_rows: int
    unjoinable_source_rows: int
    product_rows: int


@dataclass(frozen=True, slots=True)
class PriceStateNormalizationResult:
    indicative: ProductResult
    basis: ProductResult
    premium_zip_reads: int


@dataclass(frozen=True, slots=True)
class PublicationHooks:
    """Test-only interruption boundary; production callers leave it unset."""

    before_publish: Callable[[str, str, Path, Path], None] | None = None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PriceStateNormalizationError(message)


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _schema_contract(schema: pa.Schema) -> list[dict[str, Any]]:
    return [
        {"name": field.name, "arrow_type": str(field.type), "nullable": field.nullable}
        for field in schema
    ]


def _is_digest(value: object) -> bool:
    return type(value) is str and _HEX_RE.fullmatch(value) is not None


def _identity_parts(key: str) -> tuple[str, str, str, str]:
    match = _SOURCE_RE.fullmatch(key)
    _require(match is not None, "price-state source identity is not canonical hourly USD-M")
    assert match is not None
    period_type = match.group("period_type")
    period = match.group("period")
    date_format = "%Y-%m-%d" if period_type == "daily" else "%Y-%m"
    try:
        parsed = datetime.strptime(period, date_format).strftime(date_format)
    except ValueError as exc:
        raise PriceStateNormalizationError("price-state source period is invalid") from exc
    _require(parsed == period, "price-state source period is not canonical")
    archive = match.group("archive")
    family = f"{period_type}/{archive}"
    _require(family in KIND_BY_FAMILY, "price-state source family is not selected")
    return family, KIND_BY_FAMILY[family], match.group("symbol"), period


def _safe_component(value: str) -> str:
    _require(
        type(value) is str
        and bool(value)
        and value not in {".", ".."}
        and "/" not in value
        and "\\" not in value
        and "\x00" not in value,
        "output child name is unsafe",
    )
    return value


def _require_no_symlink_components(path: Path, *, label: str) -> None:
    absolute = path.absolute()
    for component in reversed((absolute, *absolute.parents)):
        if not component.exists() and not component.is_symlink():
            continue
        try:
            facts = component.lstat()
        except OSError as exc:
            raise PriceStateNormalizationError(f"{label} cannot be inspected safely") from exc
        _require(not stat.S_ISLNK(facts.st_mode), f"{label} contains a symlink")


def _safe_authority_file(root: Path, relative: PurePosixPath) -> Path:
    _require(not relative.is_absolute() and ".." not in relative.parts, "authority path escapes its root")
    root = root.resolve(strict=True)
    current = root
    for part in relative.parts:
        current = current / part
        try:
            facts = current.lstat()
        except OSError as exc:
            raise PriceStateNormalizationError("authority object is not reachable") from exc
        _require(not stat.S_ISLNK(facts.st_mode), "authority path contains a symlink")
    _require(current.is_file(), "authority object is not a regular file")
    _require(current.resolve(strict=True).is_relative_to(root), "authority path escapes its root")
    return current


def _open_regular_child(directory: int, name: str, *, label: str) -> int | None:
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise PriceStateNormalizationError(f"{label} cannot be opened no-follow") from exc
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise PriceStateNormalizationError(f"{label} is not a regular file")
    return descriptor


def _digest_fd(descriptor: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    position = os.lseek(descriptor, 0, os.SEEK_CUR)
    os.lseek(descriptor, 0, os.SEEK_SET)
    try:
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
            size += len(block)
    finally:
        os.lseek(descriptor, position, os.SEEK_SET)
    return digest.hexdigest(), size


def _read_fd(descriptor: int, maximum: int | None = None) -> bytes:
    facts = os.fstat(descriptor)
    _require(stat.S_ISREG(facts.st_mode), "authority is not a regular file")
    if maximum is not None:
        _require(0 < facts.st_size <= maximum, "authority exceeds its fixed read bound")
    position = os.lseek(descriptor, 0, os.SEEK_CUR)
    os.lseek(descriptor, 0, os.SEEK_SET)
    body = bytearray()
    try:
        while block := os.read(descriptor, 1024 * 1024):
            body.extend(block)
            if maximum is not None:
                _require(len(body) <= maximum, "authority exceeds its fixed read bound")
    finally:
        os.lseek(descriptor, position, os.SEEK_SET)
    return bytes(body)


def _same_fds(left: int, right: int) -> bool:
    if os.fstat(left).st_size != os.fstat(right).st_size:
        return False
    left_position = os.lseek(left, 0, os.SEEK_CUR)
    right_position = os.lseek(right, 0, os.SEEK_CUR)
    os.lseek(left, 0, os.SEEK_SET)
    os.lseek(right, 0, os.SEEK_SET)
    try:
        while block := os.read(left, 1024 * 1024):
            if block != os.read(right, len(block)):
                return False
        return os.read(right, 1) == b""
    finally:
        os.lseek(left, left_position, os.SEEK_SET)
        os.lseek(right, right_position, os.SEEK_SET)


def _rewrite_fd(descriptor: int, body: bytes) -> None:
    os.ftruncate(descriptor, 0)
    os.lseek(descriptor, 0, os.SEEK_SET)
    view = memoryview(body)
    while view:
        written = os.write(descriptor, view)
        _require(written > 0, "staged output write was incomplete")
        view = view[written:]
    os.fsync(descriptor)


def _rename_noreplace_at(old_dir: int, old_name: str, new_dir: int, new_name: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        renameat2 = libc.renameat2
    except AttributeError as exc:
        raise PriceStateNormalizationError("atomic no-replace rename is unavailable") from exc
    renameat2.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    renameat2.restype = ctypes.c_int
    if renameat2(old_dir, os.fsencode(old_name), new_dir, os.fsencode(new_name), RENAME_NOREPLACE):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), new_name)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _digest_path(path: Path) -> tuple[str, int]:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        _require(stat.S_ISREG(os.fstat(descriptor).st_mode), "path is not a regular file")
        return _digest_fd(descriptor)
    finally:
        os.close(descriptor)


def _require_fixed_generation0_terminal(state: AcquisitionState) -> None:
    state.authenticate_schema()
    state.authenticate_domains()
    state.authenticate_singletons()
    state.authenticate_prefix()
    state._require_runnable_head()
    head = state.seal_head_row()
    _require(head is not None, "generation-0 seal head is missing")
    assert head is not None
    _require(
        head["receipt_sha256"] == ACCEPTED_GENERATION0_SEAL_HEAD,
        "generation-0 seal head changed",
    )


def _require_accepted_validation_state(value: object) -> None:
    _require(
        type(value) is str and value in (OUTCOME_CHECKSUM_VERIFIED, OUTCOME_RETAINED),
        "generation-0 price-state validation state is not accepted",
    )


def _validate_plan_envelope(
    identity: str, envelope: object, plan_kind: object
) -> Mapping[str, Any]:
    _require(plan_kind == KIND_BINANCE, "generation-0 plan kind is not binance_object")
    _require(type(envelope) is dict, "generation-0 plan envelope is not an object")
    assert isinstance(envelope, dict)
    _require(envelope.get("provider") == PROVIDER_BINANCE, "generation-0 plan provider changed")
    _require(envelope.get("identity") == identity, "generation-0 plan identity changed")
    _require(envelope.get("kind") == KIND_BINANCE, "generation-0 plan envelope kind changed")
    payload = envelope.get("payload")
    _require(type(payload) is dict, "generation-0 nested plan payload is not an object")
    assert isinstance(payload, dict)
    return payload


def _validate_plan_payload(
    identity: str, payload: Mapping[str, Any], listed_bytes: int
) -> tuple[str, str, str, str]:
    family, kind, symbol, period = _identity_parts(identity)
    _require(payload.get("key") == identity, "generation-0 plan key changed")
    _require(payload.get("family") == family, "generation-0 plan family changed")
    _require(payload.get("symbol") == symbol, "generation-0 plan symbol changed")
    # Generation 0 encodes the 1h interval in the authenticated key.  Older
    # accepted payloads omit a duplicate interval field; if present it must agree.
    _require(payload.get("interval") in (None, "1h"), "generation-0 plan interval changed")
    _require(payload.get("economic_interval") == period, "generation-0 plan period changed")
    _require(payload.get("listed_bytes") == listed_bytes, "generation-0 plan byte size changed")
    _require(payload.get("sidecar_key") == f"{identity}.CHECKSUM", "generation-0 sidecar key changed")
    return family, kind, symbol, period


def _parse_sidecar_statement(body: bytes, *, content_sha256: str, zip_basename: str) -> None:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PriceStateNormalizationError("price-state sidecar is not UTF-8") from exc
    match = _SIDECAR_STATEMENT.fullmatch(text)
    _require(match is not None, "price-state sidecar statement is malformed")
    assert match is not None
    _require(match.group(1).lower() == content_sha256, "sidecar checksum differs from raw digest")
    _require(match.group(2) == zip_basename, "sidecar names a different ZIP basename")


def _authenticate_checksum_sidecar(
    content_root: Path,
    *,
    zip_basename: str,
    content_sha256: str,
    completion_sidecar_sha256: object,
    completion_sidecar_path: object,
    fact_sidecar_sha256: object,
    fact_sidecar_path: object,
    fact_sidecar_bytes: object,
    provider_checksum: object,
) -> None:
    _require(_is_digest(completion_sidecar_sha256), "completion sidecar digest is invalid")
    _require(_is_digest(fact_sidecar_sha256), "sidecar-fact digest is invalid")
    _require(
        completion_sidecar_sha256 == fact_sidecar_sha256,
        "completion and sidecar-fact digests disagree",
    )
    _require(
        type(fact_sidecar_bytes) is int and 0 < fact_sidecar_bytes <= MAX_SIDECAR_BYTES,
        "sidecar byte count is not a positive exact bound",
    )
    digest = str(fact_sidecar_sha256)
    expected = content_root / digest[:2] / digest
    _require(Path(str(completion_sidecar_path)) == expected, "completion sidecar path is not content-addressed")
    _require(Path(str(fact_sidecar_path)) == expected, "sidecar-fact path is not content-addressed")
    _require(str(provider_checksum) == content_sha256, "provider checksum differs from raw digest")
    path = _safe_authority_file(content_root, PurePosixPath(digest[:2], digest))
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        body = _read_fd(descriptor, MAX_SIDECAR_BYTES)
    finally:
        os.close(descriptor)
    _require(len(body) == fact_sidecar_bytes, "physical sidecar size changed")
    _require(hashlib.sha256(body).hexdigest() == digest, "physical sidecar digest changed")
    _parse_sidecar_statement(body, content_sha256=content_sha256, zip_basename=zip_basename)


def load_generation0_sources(
    state_path: Path, content_root: Path
) -> tuple[RawPriceStateObject, ...]:
    """Authenticate the complete generation-0 mark/index/premium authority."""
    _require_no_symlink_components(state_path, label="generation-0 state path")
    _require_no_symlink_components(content_root, label="generation-0 content root")
    parent = state_path.absolute().parent
    name = state_path.name
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    state_fd: int | None = None
    sidecars: dict[str, int | None] = {}
    connection: sqlite3.Connection | None = None
    borrowed: AcquisitionState | None = None
    try:
        state_fd = _open_regular_child(parent_fd, name, label="generation-0 SQLite state")
        _require(state_fd is not None, "generation-0 SQLite state is missing")
        for sidecar in (f"{name}-wal", f"{name}-shm", f"{name}-journal"):
            sidecars[sidecar] = _open_regular_child(parent_fd, sidecar, label=f"SQLite sidecar {sidecar}")
        connection = sqlite3.connect(
            f"file:/proc/self/fd/{parent_fd}/{name}?mode=ro", uri=True, isolation_level=None
        )
        reopened = _open_regular_child(parent_fd, name, label="generation-0 SQLite state")
        _require(reopened is not None, "generation-0 SQLite state disappeared")
        assert state_fd is not None and reopened is not None
        try:
            old = os.fstat(state_fd)
            new = os.fstat(reopened)
            _require((old.st_dev, old.st_ino) == (new.st_dev, new.st_ino), "generation-0 state was replaced")
        finally:
            os.close(reopened)
        for sidecar, descriptor in sidecars.items():
            observed = _open_regular_child(parent_fd, sidecar, label=f"SQLite sidecar {sidecar}")
            if descriptor is None:
                _require(observed is None, "a SQLite sidecar appeared during read-only open")
            else:
                _require(observed is not None, "a SQLite sidecar disappeared during read-only open")
                assert observed is not None
                old = os.fstat(descriptor)
                new = os.fstat(observed)
                _require((old.st_dev, old.st_ino) == (new.st_dev, new.st_ino), "a SQLite sidecar was replaced")
            if observed is not None:
                os.close(observed)
        register_domain_functions(connection)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN")
        _require(int(connection.execute("PRAGMA application_id").fetchone()[0]) == STATE_APPLICATION_ID, "generation-0 application_id changed")
        _require(int(connection.execute("PRAGMA user_version").fetchone()[0]) == STATE_USER_VERSION, "generation-0 user_version changed")
        _require(connection.execute("PRAGMA integrity_check").fetchone() == ("ok",), "generation-0 SQLite integrity check failed")
        _require(not connection.execute("PRAGMA foreign_key_check").fetchall(), "generation-0 foreign keys do not reconcile")
        borrowed = AcquisitionState(state_path, state_path.with_name("acquisition.lock"))
        borrowed.conn = connection
        _require_fixed_generation0_terminal(borrowed)
        total = connection.execute(
            "SELECT COUNT(*) FROM completion WHERE provider='binance_vision'"
        ).fetchone()
        _require(
            total is not None and int(total[0]) == ACCEPTED_GENERATION0_BINANCE_COMPLETIONS,
            "generation-0 Binance completion count changed",
        )
        cursor = connection.execute(
            "SELECT p.identity,p.kind,p.payload_json,c.content_sha256,c.content_path,"
            "c.listed_bytes,c.retrieved_at,c.validation_state,c.sidecar_sha256,c.sidecar_path,"
            "s.provider_checksum,s.sidecar_sha256,s.sidecar_path,s.sidecar_bytes "
            "FROM plan_entry p JOIN completion c ON c.provider=p.provider AND c.identity=p.identity "
            "JOIN sidecar_fact s ON s.provider=p.provider AND s.identity=p.identity "
            "WHERE p.provider='binance_vision' ORDER BY p.identity"
        )
        accepted: list[RawPriceStateObject] = []
        counts = {family: 0 for family in FAMILIES}
        byte_counts = {family: 0 for family in FAMILIES}
        retained = {family: 0 for family in FAMILIES}
        try:
            for row in cursor:
                (
                    identity,
                    plan_kind,
                    payload_json,
                    content_sha,
                    content_path,
                    listed,
                    retrieved,
                    validation_state,
                    completion_sidecar_sha,
                    completion_sidecar_path,
                    provider_sha,
                    fact_sidecar_sha,
                    fact_sidecar_path,
                    fact_sidecar_bytes,
                ) = row
                try:
                    envelope = json.loads(str(payload_json))
                except json.JSONDecodeError as exc:
                    raise PriceStateNormalizationError("generation-0 plan payload is invalid JSON") from exc
                nested = envelope.get("payload") if type(envelope) is dict else None
                if type(nested) is not dict or nested.get("family") not in FAMILIES:
                    continue
                payload = _validate_plan_envelope(str(identity), envelope, plan_kind)
                size = int(listed)
                family, kind, symbol, period = _validate_plan_payload(str(identity), payload, size)
                digest = str(content_sha)
                _require(_is_digest(digest), "generation-0 raw digest is invalid")
                _require_accepted_validation_state(validation_state)
                expected = content_root / digest[:2] / digest
                _require(Path(str(content_path)) == expected, "generation-0 raw path is not content-addressed")
                path = _safe_authority_file(content_root, PurePosixPath(digest[:2], digest))
                _authenticate_checksum_sidecar(
                    content_root,
                    zip_basename=str(identity).rsplit("/", 1)[-1],
                    content_sha256=digest,
                    completion_sidecar_sha256=completion_sidecar_sha,
                    completion_sidecar_path=completion_sidecar_path,
                    fact_sidecar_sha256=fact_sidecar_sha,
                    fact_sidecar_path=fact_sidecar_path,
                    fact_sidecar_bytes=fact_sidecar_bytes,
                    provider_checksum=provider_sha,
                )
                accepted.append(
                    RawPriceStateObject(
                        str(identity),
                        family,
                        kind,
                        symbol,
                        period,
                        path,
                        digest,
                        size,
                        str(validation_state),
                        retrieval_time=None if retrieved is None else str(retrieved),
                    )
                )
                counts[family] += 1
                byte_counts[family] += size
                retained[family] += int(validation_state == OUTCOME_RETAINED)
        finally:
            cursor.close()
        _require(counts == ACCEPTED_FAMILY_COUNTS, "generation-0 price-state family counts changed")
        _require(byte_counts == ACCEPTED_FAMILY_BYTES, "generation-0 price-state family bytes changed")
        _require(retained == ACCEPTED_FAMILY_RETAINED, "generation-0 retained-credit inventory changed")
        _require(len(accepted) == ACCEPTED_SOURCE_COUNT, "generation-0 selected source count changed")
        _require(sum(byte_counts.values()) == ACCEPTED_SOURCE_BYTES, "generation-0 selected bytes changed")
        _require(sum(retained.values()) == ACCEPTED_RETAINED, "generation-0 retained-credit count changed")
        _require(len(accepted) - sum(retained.values()) == ACCEPTED_CHECKSUM_VERIFIED, "generation-0 checksum-verified count changed")
        connection.execute("ROLLBACK")
        borrowed.conn = None
        return tuple(accepted)
    except sqlite3.Error as exc:
        raise PriceStateNormalizationError("generation-0 authority cannot be read safely") from exc
    finally:
        if borrowed is not None:
            borrowed.conn = None
        if connection is not None:
            connection.close()
        for descriptor in sidecars.values():
            if descriptor is not None:
                os.close(descriptor)
        if state_fd is not None:
            os.close(state_fd)
        os.close(parent_fd)


def _read_pinned_json(path: Path, expected_sha256: str, maximum: int) -> Mapping[str, Any]:
    _require_no_symlink_components(path, label="price-state authority path")
    parent_fd = os.open(path.absolute().parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    descriptor: int | None = None
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
        body = _read_fd(descriptor, maximum)
        _require(hashlib.sha256(body).hexdigest() == expected_sha256, "price-state authority digest changed")
        try:
            document = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PriceStateNormalizationError("price-state authority is not valid JSON") from exc
        _require(type(document) is dict, "price-state authority is not an object")
        return document
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_fd)


def _validate_sizing(sizing: Mapping[str, Any]) -> None:
    authority = sizing.get("authority")
    code = sizing.get("code_identity")
    projections = sizing.get("projections")
    _require(type(authority) is dict and type(code) is dict and type(projections) is dict, "sizing authority shape changed")
    bindings = authority.get("bindings")
    _require(type(bindings) is dict and bindings.get("report_sha256") == REPORT_SHA256, "sizing report binding changed")
    _require(code.get("policy_identity") == SIZING_POLICY_IDENTITY, "sizing policy changed")
    _require(code.get("writer_identity") == writer_identity(), "sizing writer identity changed")
    schemas = projections.get("final_product_schemas")
    _require(type(schemas) is dict, "sizing final schemas are missing")
    for product in PRODUCTS:
        _require(schemas.get(product) == _schema_contract(SCHEMAS[product]), f"accepted {product} schema changed")
    rows = projections.get("required_products")
    _require(type(rows) is list, "sizing product projections are missing")
    for product in PRODUCTS:
        matches = [item for item in rows if type(item) is dict and item.get("required_product") == product]
        _require(len(matches) == 1, f"sizing projection for {product} is missing")
        actual = matches[0]
        for field, expected in ACCEPTED_PROJECTIONS[product].items():
            _require(actual.get(field) == expected, f"sizing {product} {field} changed")


def _validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    matrix = report.get("product_matrix")
    _require(type(matrix) is list and bool(matrix), "qualification product matrix is missing")
    result: dict[str, Any] = {"report_sha256": REPORT_SHA256, "products": {}}
    for product in PRODUCTS:
        matches = [item for item in matrix if type(item) is dict and item.get("product") == product]
        _require(len(matches) == 1, f"qualification row for {product} is missing")
        item = matches[0]
        gaps = item.get("universe_coverage_gaps")
        typed = item.get("typed_gap_symbols")
        kinds = item.get("coverage_gap_kinds")
        _require(type(gaps) is list and type(typed) is list and type(kinds) is list, f"qualification gaps for {product} are missing")
        result["products"][product] = {
            "accepted_universe_object_count": item.get("accepted_universe_object_count"),
            "accepted_universe_listed_bytes": item.get("accepted_universe_listed_bytes"),
            "coverage_gap_rows": len(gaps),
            "typed_gap_symbol_count": len(typed),
            "coverage_gap_kinds": list(kinds),
        }
    return result


class _OutputTree:
    def __init__(self, root: Path) -> None:
        _require(root.name.startswith("."), "price-state output root must be hidden")
        _require_no_symlink_components(root, label="price-state output root")
        if not root.exists():
            root.mkdir(mode=0o700)
            _fsync_directory(root.parent)
        self.root = root.resolve(strict=True)
        self.root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            fcntl.flock(self.root_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self.root_fd)
            raise PriceStateNormalizationError("another normalizer holds the price-state root") from exc
        self.root_facts = os.fstat(self.root_fd)
        os.close(self.directory((".staging",), create=True))
        for product in PRODUCTS:
            os.close(self.directory((product,), create=True))

    def close(self) -> None:
        os.close(self.root_fd)

    def directory(self, parts: Sequence[str], *, create: bool) -> int:
        current = os.dup(self.root_fd)
        try:
            for raw in parts:
                name = _safe_component(raw)
                if create:
                    try:
                        os.mkdir(name, 0o700, dir_fd=current)
                        os.fsync(current)
                    except FileExistsError:
                        pass
                try:
                    child = os.open(
                        name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                        dir_fd=current,
                    )
                except OSError as exc:
                    raise PriceStateNormalizationError("price-state output directory is unsafe") from exc
                os.close(current)
                current = child
            return current
        except Exception:
            os.close(current)
            raise

    def stage(self, prefix: str) -> tuple[str, int]:
        directory = self.directory((".staging",), create=False)
        name = f"{_safe_component(prefix)}-{uuid.uuid4().hex}.tmp"
        try:
            descriptor = os.open(
                name,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                0o600,
                dir_fd=directory,
            )
        finally:
            os.close(directory)
        return name, descriptor

    def publish(
        self,
        stage_name: str,
        stage_fd: int,
        parts: Sequence[str],
        name: str,
        *,
        product: str,
        kind: str,
        hooks: PublicationHooks,
    ) -> tuple[bool, int, Path]:
        staging = self.directory((".staging",), create=False)
        destination = self.directory(parts, create=True)
        path = self.root.joinpath(*parts, name)
        try:
            if hooks.before_publish is not None:
                hooks.before_publish(product, kind, self.root / ".staging" / stage_name, path)
            try:
                _rename_noreplace_at(staging, stage_name, destination, name)
                os.fsync(destination)
                os.fsync(staging)
                reused = False
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise PriceStateNormalizationError("content-addressed publication failed") from exc
                winner = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=destination)
                try:
                    _require(stat.S_ISREG(os.fstat(winner).st_mode), "publication winner is not regular")
                    _require(_same_fds(stage_fd, winner), "content-addressed replay differs from existing bytes")
                finally:
                    os.close(winner)
                os.unlink(stage_name, dir_fd=staging)
                os.fsync(staging)
                reused = True
            final_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=destination)
            _require(stat.S_ISREG(os.fstat(final_fd).st_mode), "published object is not regular")
            return reused, final_fd, path
        finally:
            os.close(destination)
            os.close(staging)

    def require_only_completion(self, product: str, name: str) -> None:
        directory = self.directory((product, ".complete"), create=True)
        try:
            _require(
                not [entry for entry in os.listdir(directory) if entry != name],
                f"another {product} completion already exists",
            )
        finally:
            os.close(directory)

    def verify_paths(self, paths: Iterable[Path]) -> None:
        held = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            facts = os.fstat(held)
            _require(
                (facts.st_dev, facts.st_ino) == (self.root_facts.st_dev, self.root_facts.st_ino),
                "held price-state root was replaced",
            )
        finally:
            os.close(held)
        for path in paths:
            _require(path.is_relative_to(self.root), "published path escapes held root")
            relative = path.relative_to(self.root)
            directory = self.directory(relative.parts[:-1], create=False)
            descriptor: int | None = None
            try:
                descriptor = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
                _require(stat.S_ISREG(os.fstat(descriptor).st_mode), "published path is unsafe")
            finally:
                if descriptor is not None:
                    os.close(descriptor)
                os.close(directory)


def _verify_parquet_fd(descriptor: int, rows: int, digest: str, schema: pa.Schema) -> None:
    actual, _size = _digest_fd(descriptor)
    _require(actual == digest, "published Parquet digest changed")
    try:
        parquet = pq.ParquetFile(f"/proc/self/fd/{descriptor}")
    except (OSError, pa.ArrowInvalid) as exc:
        raise PriceStateNormalizationError("published Parquet is unreadable") from exc
    _require(parquet.schema_arrow == schema, "published Parquet schema changed")
    _require(parquet.metadata.num_rows == rows, "published Parquet row count changed")


def _publish_parquet(
    tree: _OutputTree,
    table: pa.Table,
    *,
    product: str,
    parts: Sequence[str],
    prefix: str,
    kind: str,
    hooks: PublicationHooks,
) -> tuple[Path, str, bool]:
    stage_name, stage_fd = tree.stage(prefix)
    final_fd: int | None = None
    try:
        pq.write_table(
            table,
            f"/proc/self/fd/{stage_fd}",
            compression=PARQUET_COMPRESSION,
            compression_level=PARQUET_COMPRESSION_LEVEL,
            version=PARQUET_VERSION,
            write_statistics=False,
            store_schema=True,
            row_group_size=SIZING_ROW_BATCH,
        )
        os.fsync(stage_fd)
        digest, _size = _digest_fd(stage_fd)
        _verify_parquet_fd(stage_fd, table.num_rows, digest, table.schema)
        reused, final_fd, path = tree.publish(
            stage_name,
            stage_fd,
            parts,
            f"{digest}.parquet",
            product=product,
            kind=kind,
            hooks=hooks,
        )
        _verify_parquet_fd(final_fd, table.num_rows, digest, table.schema)
        return path, digest, reused
    finally:
        if final_fd is not None:
            os.close(final_fd)
        os.close(stage_fd)


def _publish_json(
    tree: _OutputTree,
    document: Mapping[str, Any],
    *,
    product: str,
    parts: Sequence[str],
    prefix: str,
    kind: str,
    hooks: PublicationHooks,
) -> tuple[Path, str, bool]:
    body = _canonical_json(document)
    digest = hashlib.sha256(body).hexdigest()
    stage_name, stage_fd = tree.stage(prefix)
    final_fd: int | None = None
    try:
        _rewrite_fd(stage_fd, body)
        reused, final_fd, path = tree.publish(
            stage_name,
            stage_fd,
            parts,
            f"{digest}.json",
            product=product,
            kind=kind,
            hooks=hooks,
        )
        actual, _size = _digest_fd(final_fd)
        _require(actual == digest and _read_fd(final_fd) == body, "published JSON changed")
        return path, digest, reused
    finally:
        if final_fd is not None:
            os.close(final_fd)
        os.close(stage_fd)


def _validate_source_descriptor(source: RawPriceStateObject) -> None:
    family, kind, symbol, period = _identity_parts(source.source_key)
    _require(
        (source.family, source.kind, source.native_symbol, source.economic_period)
        == (family, kind, symbol, period),
        "raw price-state descriptor conflicts with identity",
    )
    _require(_is_digest(source.source_sha256), "raw source digest is invalid")
    _require(type(source.byte_size) is int and 0 < source.byte_size <= MAX_COMPRESSED_OBJECT_BYTES, "raw source size is invalid")
    _require_accepted_validation_state(source.validation_state)
    _require_no_symlink_components(source.path, label="raw source path")
    _require(source.path.is_file() and not source.path.is_symlink(), "raw source path is unsafe")
    _safe_component(source.native_symbol)


def _preflight_sources(sources: Iterable[RawPriceStateObject]) -> tuple[RawPriceStateObject, ...]:
    ordered = tuple(
        sorted(
            sources,
            key=lambda item: (
                item.native_symbol,
                item.economic_period[:7],
                KINDS.index(item.kind),
                0 if item.family.startswith("monthly/") else 1,
                item.source_key,
            ),
        )
    )
    identities: set[str] = set()
    coverage: dict[tuple[str, str, str], set[str]] = {}
    for source in ordered:
        _require(source.source_key not in identities, "raw authority repeats a source identity")
        identities.add(source.source_key)
        _validate_source_descriptor(source)
        key = (source.native_symbol, source.economic_period[:7], source.kind)
        coverage.setdefault(key, set()).add(source.family.split("/", 1)[0])
    _require(
        not [key for key, period_types in coverage.items() if len(period_types) > 1],
        "daily and monthly authority overlap one family symbol/month",
    )
    return ordered


def _safe_zip_member(archive: zipfile.ZipFile, source: RawPriceStateObject) -> zipfile.ZipInfo:
    members = archive.infolist()
    _require(len(members) == 1, "price-state ZIP must contain exactly one member")
    member = members[0]
    name = member.filename
    parts = PurePosixPath(name.replace("\\", "/"))
    _require(bool(name) and not parts.is_absolute() and ".." not in parts.parts, "ZIP member path is unsafe")
    _require(len(parts.parts) == 1 and name.endswith(".csv"), "ZIP member is not one root CSV")
    _require(stat.S_IFMT(member.external_attr >> 16) in {0, stat.S_IFREG}, "ZIP member is not regular")
    _require(not (member.flag_bits & 0x1), "encrypted price-state ZIP is unsupported")
    _require(member.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}, "ZIP compression is unsupported")
    _require(0 < member.file_size <= MAX_DECOMPRESSED_MEMBER_BYTES, "ZIP member exceeds parser bound")
    _require(member.compress_size <= MAX_COMPRESSED_OBJECT_BYTES, "compressed member exceeds parser bound")
    _require(name == source.source_key.rsplit("/", 1)[-1][:-4] + ".csv", "ZIP member name conflicts with source identity")
    return member


def _authenticated_source_bytes(source: RawPriceStateObject) -> bytes:
    try:
        descriptor = os.open(source.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        raise PriceStateNormalizationError("raw source cannot be opened no-follow") from exc
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    size = 0
    try:
        _require(stat.S_ISREG(os.fstat(descriptor).st_mode), "raw source is not regular")
        while block := os.read(descriptor, 1024 * 1024):
            size += len(block)
            _require(size <= MAX_COMPRESSED_OBJECT_BYTES, "raw source exceeds parser bound")
            digest.update(block)
            chunks.append(block)
    finally:
        os.close(descriptor)
    _require((digest.hexdigest(), size) == (source.source_sha256, source.byte_size), "raw source bytes differ from authority")
    return b"".join(chunks)


def _integer(token: str, source: RawPriceStateObject, column: str, ordinal: int) -> int:
    try:
        return convert_integer(token, key=source.source_key, output=BASIS_PRODUCT, column=column, row=ordinal)
    except Exception as exc:
        raise PriceStateNormalizationError(f"price-state {column} is not an exact integer") from exc


def _decimal(token: str, source: RawPriceStateObject, column: str, ordinal: int) -> Decimal:
    try:
        return convert_decimal(token, key=source.source_key, output=BASIS_PRODUCT, column=column, row=ordinal)
    except Exception as exc:
        raise PriceStateNormalizationError(f"price-state {column} is not an exact scale-18 decimal") from exc


def _period_contains(source: RawPriceStateObject, open_time: int) -> bool:
    moment = datetime.fromtimestamp(open_time // 1000, tz=UTC)
    expected = moment.strftime("%Y-%m-%d" if source.family.startswith("daily/") else "%Y-%m")
    return expected == source.economic_period


def _parse_row(source: RawPriceStateObject, ordinal: int, row: Sequence[str]) -> dict[str, Any]:
    fields = dict(zip(FIELDS, row, strict=True))
    open_time = _integer(fields["open_time"], source, "open_time", ordinal)
    close_time = _integer(fields["close_time"], source, "close_time", ordinal)
    _require(open_time >= 0 and open_time % EXPECTED_CADENCE_MS == 0, "open_time is not an hourly epoch millisecond")
    _require(close_time == open_time + EXPECTED_CLOSE_OFFSET_MS, "close_time does not close the hourly interval")
    _require(_period_contains(source, open_time), "row lies outside its source economic period")
    values = {
        name: _decimal(fields[name], source, name, ordinal)
        for name in (
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_volume",
            "taker_buy_volume",
            "taker_buy_quote_volume",
        )
    }
    count = _integer(fields["count"], source, "count", ordinal)
    reserved = _integer(fields["ignore"], source, "ignore", ordinal)
    if source.kind in (MARK, INDEX):
        _require(all(values[name] > 0 for name in ("open", "high", "low", "close")), "mark/index prices must be positive")
    _require(values["high"] >= max(values["open"], values["close"], values["low"]), "high violates OHLC bounds")
    _require(values["low"] <= min(values["open"], values["close"], values["high"]), "low violates OHLC bounds")
    _require(count >= 0 and reserved >= 0, "count and reserved must be nonnegative")
    return {
        "source_row_ordinal": ordinal,
        "open_time": open_time,
        "close_time": close_time,
        **values,
        "count": count,
        "source_reserved": reserved,
    }


def _iter_rows(source: RawPriceStateObject) -> Iterator[dict[str, Any]]:
    payload = _authenticated_source_bytes(source)
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            member = _safe_zip_member(archive, source)
            with archive.open(member, "r") as raw:
                reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", newline=""), strict=True)
                ordinal = 0
                first = True
                decompressed = 0
                for row in reader:
                    decompressed += sum(len(cell.encode()) for cell in row) + len(row)
                    _require(decompressed <= MAX_DECOMPRESSED_MEMBER_BYTES, "CSV exceeds decompressed parser bound")
                    _require(all(len(cell.encode()) <= MAX_CSV_FIELD_BYTES for cell in row), "CSV field exceeds parser bound")
                    if first:
                        first = False
                        if tuple(row) == FIELDS:
                            continue
                    _require(bool(row) and len(row) == len(FIELDS), "CSV row width is invalid")
                    _require(ordinal < MAX_ROWS_PER_OBJECT, "CSV exceeds row parser bound")
                    yield _parse_row(source, ordinal, row)
                    ordinal += 1
                _require(ordinal > 0, "CSV contains no data rows")
    except (OSError, UnicodeError, csv.Error, zipfile.BadZipFile, RuntimeError) as exc:
        if isinstance(exc, PriceStateNormalizationError):
            raise
        raise PriceStateNormalizationError("price-state ZIP/CSV is invalid") from exc


def _unscaled(value: Decimal) -> int:
    parts = value.as_tuple()
    coefficient = int("".join(str(digit) for digit in parts.digits) or "0")
    _require(parts.exponent >= -DECIMAL_SCALE, "decimal exceeds pinned scale")
    coefficient *= 10 ** (parts.exponent + DECIMAL_SCALE)
    return -coefficient if parts.sign else coefficient


def _scaled(value: int) -> Decimal:
    digits = tuple(int(character) for character in str(abs(value))) if value else (0,)
    _require(len(digits) <= 38, "derived basis decimal overflows pinned precision")
    return Decimal((1 if value < 0 else 0, digits, -DECIMAL_SCALE))


def _record_values(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(
        record[name]
        for name in (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "source_reserved",
        )
    )


def _collapse_family(
    kind: str,
    parsed: Sequence[tuple[int, RawPriceStateObject, dict[str, Any]]],
) -> tuple[dict[tuple[int, int], tuple[int, RawPriceStateObject, dict[str, Any]]], list[dict[str, Any]]]:
    ordered = sorted(
        parsed,
        key=lambda item: (
            int(item[2]["open_time"]),
            int(item[2]["close_time"]),
            item[1].source_key,
            int(item[2]["source_row_ordinal"]),
        ),
    )
    kept: dict[tuple[int, int], tuple[int, RawPriceStateObject, dict[str, Any]]] = {}
    collapsed: list[dict[str, Any]] = []
    for raw_ref, source, record in ordered:
        stamp = (int(record["open_time"]), int(record["close_time"]))
        if stamp not in kept:
            kept[stamp] = (raw_ref, source, record)
            continue
        kept_ref, kept_source, kept_record = kept[stamp]
        _require(_record_values(record) == _record_values(kept_record), f"conflicting duplicate {kind} observation")
        collapsed.append(
            {
                "kind": kind,
                "open_time": stamp[0],
                "close_time": stamp[1],
                "reason": IDENTICAL_OBSERVATION,
                "kept_raw_object_ref": kept_ref,
                "kept_source_row_ordinal": int(kept_record["source_row_ordinal"]),
                "collapsed_raw_object_ref": raw_ref,
                "collapsed_source_row_ordinal": int(record["source_row_ordinal"]),
            }
        )
        _require(kept_source.kind == kind and source.kind == kind, "duplicate source kind changed")
    return kept, collapsed


def _lineage_source(source: RawPriceStateObject, raw_ref: int) -> dict[str, Any]:
    return {
        "raw_object_ref": raw_ref,
        "source_key": source.source_key,
        "family": source.family,
        "kind": source.kind,
        "native_symbol": source.native_symbol,
        "economic_period": source.economic_period,
        "source_sha256": source.source_sha256,
        "checksum_authority": source.checksum_authority,
        "byte_size": source.byte_size,
        "listed_bytes": source.byte_size,
        "sidecar_key": f"{source.source_key}.CHECKSUM",
        "retrieval_time": source.retrieval_time,
        "source_available_at": source.source_available_at,
        "source_availability_state": UNKNOWN_AVAILABILITY if source.source_available_at is None else "known",
        "validation_state": source.validation_state,
    }


def _indicative_row(
    symbol: str, raw_ref: int, record: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "raw_object_ref": raw_ref,
        "source_row_ordinal": record["source_row_ordinal"],
        "venue_symbol": symbol,
        "open_time": record["open_time"],
        "close_time": record["close_time"],
        "premium_open": record["open"],
        "premium_high": record["high"],
        "premium_low": record["low"],
        "premium_close": record["close"],
        "premium_volume": record["volume"],
        "premium_quote_volume": record["quote_volume"],
        "premium_count": record["count"],
        "premium_taker_buy_volume": record["taker_buy_volume"],
        "premium_taker_buy_quote_volume": record["taker_buy_quote_volume"],
        "source_reserved": record["source_reserved"],
        **native_identity(symbol),
        "indicative_funding_rate": None,
        "indicative_rate_status": INDICATIVE_UNAVAILABLE,
    }


def _basis_row(
    symbol: str,
    mark_item: tuple[int, RawPriceStateObject, Mapping[str, Any]],
    index_item: tuple[int, RawPriceStateObject, Mapping[str, Any]],
    premium_item: tuple[int, RawPriceStateObject, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    mark_ref, mark_source, mark = mark_item
    index_ref, index_source, index = index_item
    premium_ref, premium_source, premium = premium_item
    _require(mark["source_reserved"] == index["source_reserved"], "joined mark/index source_reserved values disagree")
    mark_close = mark["close"]
    index_close = index["close"]
    assert isinstance(mark_close, Decimal) and isinstance(index_close, Decimal)
    absolute_unscaled = _unscaled(mark_close) - _unscaled(index_close)
    index_unscaled = _unscaled(index_close)
    _require(index_unscaled > 0, "joined index close must be positive")
    relative_unscaled = (absolute_unscaled * 10**DECIMAL_SCALE) // index_unscaled
    row = {
        "raw_object_ref": mark_ref,
        "source_row_ordinal": mark["source_row_ordinal"],
        "venue_symbol": symbol,
        "open_time": mark["open_time"],
        "close_time": mark["close_time"],
        "mark_open": mark["open"],
        "mark_high": mark["high"],
        "mark_low": mark["low"],
        "mark_close": mark_close,
        "mark_volume": mark["volume"],
        "mark_quote_volume": mark["quote_volume"],
        "mark_count": mark["count"],
        "mark_taker_buy_volume": mark["taker_buy_volume"],
        "mark_taker_buy_quote_volume": mark["taker_buy_quote_volume"],
        "source_reserved": mark["source_reserved"],
        "index_open": index["open"],
        "index_high": index["high"],
        "index_low": index["low"],
        "index_close": index_close,
        "index_volume": index["volume"],
        "index_quote_volume": index["quote_volume"],
        "index_count": index["count"],
        "index_taker_buy_volume": index["taker_buy_volume"],
        "index_taker_buy_quote_volume": index["taker_buy_quote_volume"],
        "premium_close": premium["close"],
        **native_identity(symbol),
        "absolute_basis": _scaled(absolute_unscaled),
        "relative_basis": _scaled(relative_unscaled),
        "basis_join_status": BASIS_JOIN_STATUS,
    }
    join_lineage = {
        "open_time": mark["open_time"],
        "close_time": mark["close_time"],
        "mark_raw_object_ref": mark_ref,
        "mark_source_row_ordinal": mark["source_row_ordinal"],
        "index_raw_object_ref": index_ref,
        "index_source_row_ordinal": index["source_row_ordinal"],
        "premium_raw_object_ref": premium_ref,
        "premium_source_row_ordinal": premium["source_row_ordinal"],
    }
    _require(mark_source.kind == MARK and index_source.kind == INDEX and premium_source.kind == PREMIUM, "joined source kinds changed")
    return row, join_lineage


def _compact_join_lineage(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Run-length encode exact per-source join refs and original ordinals."""
    runs: list[dict[str, Any]] = []
    for row in rows:
        if runs:
            prior = runs[-1]
            contiguous = (
                int(row["open_time"]) == int(prior["open_time_end_ms"]) + EXPECTED_CADENCE_MS
                and int(row["close_time"]) == int(prior["close_time_end_ms"]) + EXPECTED_CADENCE_MS
                and all(
                    int(row[f"{kind}_raw_object_ref"]) == int(prior[f"{kind}_raw_object_ref"])
                    and int(row[f"{kind}_source_row_ordinal"])
                    == int(prior[f"{kind}_source_row_ordinal_end"]) + 1
                    for kind in KINDS
                )
            )
            if contiguous:
                prior["open_time_end_ms"] = int(row["open_time"])
                prior["close_time_end_ms"] = int(row["close_time"])
                prior["row_count"] = int(prior["row_count"]) + 1
                for kind in KINDS:
                    prior[f"{kind}_source_row_ordinal_end"] = int(row[f"{kind}_source_row_ordinal"])
                continue
        run = {
            "open_time_start_ms": int(row["open_time"]),
            "open_time_end_ms": int(row["open_time"]),
            "close_time_start_ms": int(row["close_time"]),
            "close_time_end_ms": int(row["close_time"]),
            "row_count": 1,
        }
        for kind in KINDS:
            run[f"{kind}_raw_object_ref"] = int(row[f"{kind}_raw_object_ref"])
            run[f"{kind}_source_row_ordinal_start"] = int(row[f"{kind}_source_row_ordinal"])
            run[f"{kind}_source_row_ordinal_end"] = int(row[f"{kind}_source_row_ordinal"])
        runs.append(run)
    _require(sum(int(run["row_count"]) for run in runs) == len(rows), "compact join lineage row count changed")
    return runs


def _gap_row(product: str, symbol: str, month: str, start: int, end: int, count: int, kind: str, reason: str) -> dict[str, Any]:
    return {
        **native_identity(symbol),
        "required_product": product,
        "utc_month": month,
        "missing_run_start_ms": start,
        "missing_run_end_ms": end,
        "expected_grid_count": count,
        "gap_kind": kind,
        "reason": reason,
    }


def _missing_grid_gaps(
    product: str,
    symbol: str,
    month: str,
    stamps: set[tuple[int, int]],
    *,
    reason: str,
) -> list[dict[str, Any]]:
    if len(stamps) < 2:
        return []
    opens = sorted(stamp[0] for stamp in stamps)
    gaps: list[dict[str, Any]] = []
    for left, right in zip(opens, opens[1:], strict=False):
        if right - left <= EXPECTED_CADENCE_MS:
            continue
        start = left + EXPECTED_CADENCE_MS
        end = right - EXPECTED_CADENCE_MS
        count = (end - start) // EXPECTED_CADENCE_MS + 1
        gaps.append(_gap_row(product, symbol, month, start, end, count, "missing_hour_run", reason))
    return gaps


def _unjoinable_lineage(
    symbol: str,
    month: str,
    family_maps: Mapping[str, Mapping[tuple[int, int], Any]],
) -> list[dict[str, Any]]:
    union = set().union(*(set(family_maps[kind]) for kind in KINDS))
    common = set.intersection(*(set(family_maps[kind]) for kind in KINDS))
    stamps = sorted(union - common)
    observations: list[dict[str, Any]] = []
    for stamp in stamps:
        missing = [kind for kind in KINDS if stamp not in family_maps[kind]]
        present = [kind for kind in KINDS if stamp in family_maps[kind]]
        reason = "missing_" + "_and_".join(missing) + "_for_causal_join"
        for kind in present:
            raw_ref, source, record = family_maps[kind][stamp]
            observations.append(
                {
                    "kind": kind,
                    "open_time": stamp[0],
                    "close_time": stamp[1],
                    "raw_object_ref": raw_ref,
                    "source_row_ordinal": record["source_row_ordinal"],
                    "missing_join_families": missing,
                    "reason": reason,
                }
            )
            _require(source.kind == kind, "unjoinable source kind changed")
    lineage: list[dict[str, Any]] = []
    for item in sorted(
        observations,
        key=lambda value: (
            KINDS.index(str(value["kind"])),
            int(value["raw_object_ref"]),
            int(value["open_time"]),
            int(value["source_row_ordinal"]),
        ),
    ):
        if lineage:
            prior = lineage[-1]
            if (
                item["kind"] == prior["kind"]
                and item["missing_join_families"] == prior["missing_join_families"]
                and int(item["raw_object_ref"]) == int(prior["raw_object_ref"])
                and int(item["open_time"]) == int(prior["open_time_end_ms"]) + EXPECTED_CADENCE_MS
                and int(item["source_row_ordinal"]) == int(prior["source_row_ordinal_end"]) + 1
            ):
                prior["open_time_end_ms"] = int(item["open_time"])
                prior["close_time_end_ms"] = int(item["close_time"])
                prior["source_row_ordinal_end"] = int(item["source_row_ordinal"])
                prior["source_row_count"] = int(prior["source_row_count"]) + 1
                continue
        lineage.append(
            {
                "kind": item["kind"],
                "open_time_start_ms": int(item["open_time"]),
                "open_time_end_ms": int(item["open_time"]),
                "close_time_start_ms": int(item["close_time"]),
                "close_time_end_ms": int(item["close_time"]),
                "raw_object_ref": int(item["raw_object_ref"]),
                "source_row_ordinal_start": int(item["source_row_ordinal"]),
                "source_row_ordinal_end": int(item["source_row_ordinal"]),
                "source_row_count": 1,
                "missing_join_families": item["missing_join_families"],
                "reason": item["reason"],
            }
        )
    _require(
        sum(int(run["source_row_count"]) for run in lineage) == len(observations),
        "compact unjoinable lineage row count changed",
    )
    return lineage


def _basis_availability_gaps(
    symbol: str,
    month: str,
    union: set[tuple[int, int]],
    common: set[tuple[int, int]],
) -> list[dict[str, Any]]:
    """Coalesce every consecutive hour without a causal triple into one run."""
    if not union:
        return []
    start = min(stamp[0] for stamp in union)
    end = max(stamp[0] for stamp in union)
    missing = [
        moment
        for moment in range(start, end + EXPECTED_CADENCE_MS, EXPECTED_CADENCE_MS)
        if (moment, moment + EXPECTED_CLOSE_OFFSET_MS) not in common
    ]
    runs: list[dict[str, Any]] = []
    run_start: int | None = None
    run_end: int | None = None
    for moment in missing:
        if run_start is None:
            run_start = run_end = moment
        elif moment == int(run_end) + EXPECTED_CADENCE_MS:
            run_end = moment
        else:
            assert run_end is not None
            count = (run_end - run_start) // EXPECTED_CADENCE_MS + 1
            runs.append(
                _gap_row(
                    BASIS_PRODUCT,
                    symbol,
                    month,
                    run_start,
                    run_end,
                    count,
                    "causal_join_unavailable_run",
                    "one_or_more_price_state_families_unavailable",
                )
            )
            run_start = run_end = moment
    if run_start is not None:
        assert run_end is not None
        count = (run_end - run_start) // EXPECTED_CADENCE_MS + 1
        runs.append(
            _gap_row(
                BASIS_PRODUCT,
                symbol,
                month,
                run_start,
                run_end,
                count,
                "causal_join_unavailable_run",
                "one_or_more_price_state_families_unavailable",
            )
        )
    return runs


def _publish_gap_artifact(
    tree: _OutputTree,
    *,
    product: str,
    symbol: str,
    month: str,
    gap_rows: Sequence[Mapping[str, Any]],
    raw_objects: Sequence[RawPriceStateObject],
    collapsed: Sequence[Mapping[str, Any]],
    unjoinable: Sequence[Mapping[str, Any]],
    hooks: PublicationHooks,
) -> PublishedGapArtifact | None:
    if not gap_rows:
        return None
    ordered = sorted(
        gap_rows,
        key=lambda row: (
            int(row["missing_run_start_ms"]),
            int(row["missing_run_end_ms"]),
            str(row["reason"]),
        ),
    )
    table = pa.Table.from_pylist(list(ordered), schema=QUALITY_GAP_SCHEMA)
    path, digest, reused = _publish_parquet(
        tree,
        table,
        product=product,
        parts=(product, ".quality-gaps", symbol, month),
        prefix=f"quality-gap-{product}-{symbol}-{month}",
        kind="quality_gap",
        hooks=hooks,
    )
    unjoinable_source_rows = sum(int(run["source_row_count"]) for run in unjoinable)
    lineage = {
        "document_type": f"{product}_partition_quality_gap_lineage",
        "schema_version": 1,
        "required_product": product,
        "native_symbol": symbol,
        "utc_month": month,
        "row_count": len(ordered),
        "missing_grid_points": sum(int(row["expected_grid_count"]) for row in ordered),
        "unjoinable_source_rows": unjoinable_source_rows,
        "quality_gap_parquet_sha256": digest,
        "quality_gap_parquet_path": str(path.relative_to(tree.root)),
        "raw_objects": [_lineage_source(source, ref) for ref, source in enumerate(raw_objects)],
        "collapsed_identical_source_rows": list(collapsed),
        "unjoinable_observations": list(unjoinable),
    }
    lineage_path, lineage_sha, lineage_reused = _publish_json(
        tree,
        lineage,
        product=product,
        parts=(product, ".quality-gap-lineage", symbol, month),
        prefix=f"quality-gap-lineage-{product}-{symbol}-{month}",
        kind="quality_gap_lineage",
        hooks=hooks,
    )
    return PublishedGapArtifact(
        product,
        symbol,
        month,
        len(ordered),
        sum(int(row["expected_grid_count"]) for row in ordered),
        unjoinable_source_rows,
        path,
        digest,
        lineage_path,
        lineage_sha,
        reused and lineage_reused,
    )


def _partition_descriptor(part: PublishedPartition, tree: _OutputTree) -> dict[str, Any]:
    return {
        "native_symbol": part.native_symbol,
        "utc_month": part.utc_month,
        "row_count": part.row_count,
        "physical_row_count": part.physical_row_count,
        "collapsed_identical_row_count": part.collapsed_row_count,
        "unjoinable_source_row_count": part.unjoinable_row_count,
        "parquet_path": str(part.parquet_path.relative_to(tree.root)),
        "parquet_sha256": part.parquet_sha256,
        "lineage_path": str(part.lineage_path.relative_to(tree.root)),
        "lineage_sha256": part.lineage_sha256,
    }


def _gap_descriptor(gap: PublishedGapArtifact, tree: _OutputTree) -> dict[str, Any]:
    return {
        "native_symbol": gap.native_symbol,
        "utc_month": gap.utc_month,
        "row_count": gap.row_count,
        "missing_grid_points": gap.missing_grid_points,
        "unjoinable_source_rows": gap.unjoinable_source_rows,
        "parquet_path": str(gap.parquet_path.relative_to(tree.root)),
        "parquet_sha256": gap.parquet_sha256,
        "lineage_path": str(gap.lineage_path.relative_to(tree.root)),
        "lineage_sha256": gap.lineage_sha256,
    }


class _RangeAccumulator:
    def __init__(self) -> None:
        self.minimum: int | None = None
        self.maximum: int | None = None
        self.symbol_min: str | None = None
        self.symbol_max: str | None = None

    def add(self, symbol: str, open_time: int) -> None:
        self.minimum = open_time if self.minimum is None else min(self.minimum, open_time)
        self.maximum = open_time if self.maximum is None else max(self.maximum, open_time)
        self.symbol_min = symbol if self.symbol_min is None else min(self.symbol_min, symbol)
        self.symbol_max = symbol if self.symbol_max is None else max(self.symbol_max, symbol)

    def finish(self) -> dict[str, Any]:
        _require(self.minimum is not None and self.maximum is not None, "price-state product has no rows")
        return {
            "open_time_min": self.minimum,
            "open_time_max": self.maximum,
            "native_symbol_min": self.symbol_min,
            "native_symbol_max": self.symbol_max,
        }


def _normalize(
    sources: Iterable[RawPriceStateObject],
    output_root: Path,
    *,
    report: Mapping[str, Any] | None,
    sizing: Mapping[str, Any] | None,
    enforce_full_corpus: bool,
    hooks: PublicationHooks,
) -> PriceStateNormalizationResult:
    if sizing is not None:
        _validate_sizing(sizing)
    report_binding: dict[str, Any] = {"report_sha256": REPORT_SHA256, "bound": False}
    if report is not None:
        report_binding = {**_validate_report(report), "bound": True}
    ordered = _preflight_sources(sources)
    groups: dict[tuple[str, str], list[RawPriceStateObject]] = {}
    for source in ordered:
        groups.setdefault((source.native_symbol, source.economic_period[:7]), []).append(source)
    if enforce_full_corpus:
        _require(len(ordered) == ACCEPTED_SOURCE_COUNT, "full-corpus price-state source count changed")
        _require(sum(source.byte_size for source in ordered) == ACCEPTED_SOURCE_BYTES, "full-corpus price-state bytes changed")
        _require(len(groups) == ACCEPTED_UNION_PARTITIONS, "full-corpus source partition union changed")
        premium_partitions = sum(any(source.kind == PREMIUM for source in group) for group in groups.values())
        joinable_partitions = sum({source.kind for source in group} == set(KINDS) for group in groups.values())
        _require(premium_partitions == ACCEPTED_PREMIUM_PARTITIONS, "full-corpus premium partition count changed")
        _require(joinable_partitions == ACCEPTED_JOINABLE_PARTITIONS, "full-corpus all-family partition count changed")
    tree = _OutputTree(output_root)
    try:
        partitions: dict[str, list[PublishedPartition]] = {product: [] for product in PRODUCTS}
        gap_artifacts: dict[str, list[PublishedGapArtifact]] = {product: [] for product in PRODUCTS}
        physical_rows = {product: 0 for product in PRODUCTS}
        collapsed_rows = {product: 0 for product in PRODUCTS}
        unjoinable_rows = {product: 0 for product in PRODUCTS}
        physical_by_family = {family: 0 for family in FAMILIES}
        collapsed_by_family = {family: 0 for family in FAMILIES}
        unjoinable_by_kind = {kind: 0 for kind in KINDS}
        ranges = {product: _RangeAccumulator() for product in PRODUCTS}
        premium_zip_reads = 0
        for (symbol, month), month_sources in sorted(groups.items()):
            raw_objects = sorted(month_sources, key=lambda item: (KINDS.index(item.kind), item.source_key))
            raw_ref_by_key = {source.source_key: ref for ref, source in enumerate(raw_objects)}
            parsed_by_kind: dict[str, list[tuple[int, RawPriceStateObject, dict[str, Any]]]] = {
                kind: [] for kind in KINDS
            }
            for source in raw_objects:
                if source.kind == PREMIUM:
                    premium_zip_reads += 1
                raw_ref = raw_ref_by_key[source.source_key]
                for record in _iter_rows(source):
                    parsed_by_kind[source.kind].append((raw_ref, source, record))
                    physical_by_family[source.family] += 1
            maps: dict[str, dict[tuple[int, int], tuple[int, RawPriceStateObject, dict[str, Any]]]] = {}
            collapsed_by_kind: dict[str, list[dict[str, Any]]] = {}
            for kind in KINDS:
                maps[kind], collapsed_by_kind[kind] = _collapse_family(kind, parsed_by_kind[kind])
                for item in collapsed_by_kind[kind]:
                    collapsed_ref = int(item["collapsed_raw_object_ref"])
                    collapsed_by_family[raw_objects[collapsed_ref].family] += 1
            premium_collapsed = collapsed_by_kind[PREMIUM]
            all_collapsed = [item for kind in KINDS for item in collapsed_by_kind[kind]]

            premium_map = maps[PREMIUM]
            if premium_map:
                indicative_rows = [
                    _indicative_row(symbol, raw_ref, record)
                    for _stamp, (raw_ref, _source, record) in sorted(premium_map.items())
                ]
                for row in indicative_rows:
                    _require(row["indicative_funding_rate"] is None, "indicative rate was fabricated")
                    _require(row["indicative_rate_status"] == INDICATIVE_UNAVAILABLE, "indicative unavailable state changed")
                    ranges[INDICATIVE_PRODUCT].add(symbol, int(row["open_time"]))
                table = pa.Table.from_pylist(indicative_rows, schema=INDICATIVE_SCHEMA)
                _require(table.schema == INDICATIVE_SCHEMA and table.num_rows > 0, "indicative partition schema or rows changed")
                path, digest, reused = _publish_parquet(
                    tree,
                    table,
                    product=INDICATIVE_PRODUCT,
                    parts=(INDICATIVE_PRODUCT, ".partitions", symbol, month),
                    prefix=f"indicative-{symbol}-{month}",
                    kind="partition",
                    hooks=hooks,
                )
                lineage = {
                    "document_type": f"{INDICATIVE_PRODUCT}_partition_lineage",
                    "schema_version": 1,
                    "required_product": INDICATIVE_PRODUCT,
                    "native_symbol": symbol,
                    "utc_month": month,
                    "physical_row_count": len(parsed_by_kind[PREMIUM]),
                    "collapsed_identical_row_count": len(premium_collapsed),
                    "unjoinable_source_row_count": 0,
                    "row_count": len(indicative_rows),
                    "schema_sha256": SCHEMA_SHA256[INDICATIVE_PRODUCT],
                    "writer_identity": writer_identity(),
                    "parquet_path": str(path.relative_to(tree.root)),
                    "parquet_sha256": digest,
                    "raw_objects": [
                        _lineage_source(source, raw_ref_by_key[source.source_key])
                        for source in raw_objects
                        if source.kind == PREMIUM
                    ],
                    "collapsed_identical_source_rows": premium_collapsed,
                    "indicative_rate_semantics": INDICATIVE_UNAVAILABLE,
                }
                lineage_path, lineage_sha, lineage_reused = _publish_json(
                    tree,
                    lineage,
                    product=INDICATIVE_PRODUCT,
                    parts=(INDICATIVE_PRODUCT, ".lineage", symbol, month),
                    prefix=f"indicative-lineage-{symbol}-{month}",
                    kind="lineage",
                    hooks=hooks,
                )
                partitions[INDICATIVE_PRODUCT].append(
                    PublishedPartition(
                        INDICATIVE_PRODUCT,
                        symbol,
                        month,
                        len(indicative_rows),
                        len(parsed_by_kind[PREMIUM]),
                        len(premium_collapsed),
                        0,
                        path,
                        digest,
                        lineage_path,
                        lineage_sha,
                        reused and lineage_reused,
                    )
                )
                indicative_gaps = _missing_grid_gaps(
                    INDICATIVE_PRODUCT,
                    symbol,
                    month,
                    set(premium_map),
                    reason="premium_source_missing_hour",
                )
                gap = _publish_gap_artifact(
                    tree,
                    product=INDICATIVE_PRODUCT,
                    symbol=symbol,
                    month=month,
                    gap_rows=indicative_gaps,
                    raw_objects=[source for source in raw_objects if source.kind == PREMIUM],
                    collapsed=premium_collapsed,
                    unjoinable=[],
                    hooks=hooks,
                )
                if gap is not None:
                    gap_artifacts[INDICATIVE_PRODUCT].append(gap)
                physical_rows[INDICATIVE_PRODUCT] += len(parsed_by_kind[PREMIUM])
                collapsed_rows[INDICATIVE_PRODUCT] += len(premium_collapsed)

            common = set.intersection(*(set(maps[kind]) for kind in KINDS))
            basis_rows: list[dict[str, Any]] = []
            join_lineage: list[dict[str, Any]] = []
            for stamp in sorted(common):
                row, row_lineage = _basis_row(symbol, maps[MARK][stamp], maps[INDEX][stamp], maps[PREMIUM][stamp])
                basis_rows.append(row)
                join_lineage.append(row_lineage)
                ranges[BASIS_PRODUCT].add(symbol, int(row["open_time"]))
            unjoinable = _unjoinable_lineage(symbol, month, maps)
            union = set().union(*(set(maps[kind]) for kind in KINDS))
            basis_gap_rows = _basis_availability_gaps(symbol, month, union, common)
            partition_unjoinable = sum(int(run["source_row_count"]) for run in unjoinable)
            for run in unjoinable:
                unjoinable_by_kind[str(run["kind"])] += int(run["source_row_count"])
            if basis_rows:
                table = pa.Table.from_pylist(basis_rows, schema=BASIS_SCHEMA)
                _require(table.schema == BASIS_SCHEMA, "basis partition schema changed")
                path, digest, reused = _publish_parquet(
                    tree,
                    table,
                    product=BASIS_PRODUCT,
                    parts=(BASIS_PRODUCT, ".partitions", symbol, month),
                    prefix=f"basis-{symbol}-{month}",
                    kind="partition",
                    hooks=hooks,
                )
                lineage = {
                    "document_type": f"{BASIS_PRODUCT}_partition_lineage",
                    "schema_version": 1,
                    "required_product": BASIS_PRODUCT,
                    "native_symbol": symbol,
                    "utc_month": month,
                    "physical_row_count": sum(len(parsed_by_kind[kind]) for kind in KINDS),
                    "collapsed_identical_row_count": len(all_collapsed),
                    "unjoinable_source_row_count": partition_unjoinable,
                    "joined_input_row_count": 3 * len(basis_rows),
                    "row_count": len(basis_rows),
                    "schema_sha256": SCHEMA_SHA256[BASIS_PRODUCT],
                    "writer_identity": writer_identity(),
                    "parquet_path": str(path.relative_to(tree.root)),
                    "parquet_sha256": digest,
                    "raw_objects": [_lineage_source(source, raw_ref_by_key[source.source_key]) for source in raw_objects],
                    "collapsed_identical_source_rows": all_collapsed,
                    "joined_source_runs": _compact_join_lineage(join_lineage),
                    "relative_basis_rule": "floor((mark_close_unscaled-index_close_unscaled)*10**18/index_close_unscaled)_including_negative",
                    "basis_join_status": BASIS_JOIN_STATUS,
                    "derived_value_time_semantics": "close_time_not_open_time",
                }
                lineage_path, lineage_sha, lineage_reused = _publish_json(
                    tree,
                    lineage,
                    product=BASIS_PRODUCT,
                    parts=(BASIS_PRODUCT, ".lineage", symbol, month),
                    prefix=f"basis-lineage-{symbol}-{month}",
                    kind="lineage",
                    hooks=hooks,
                )
                partitions[BASIS_PRODUCT].append(
                    PublishedPartition(
                        BASIS_PRODUCT,
                        symbol,
                        month,
                        len(basis_rows),
                        sum(len(parsed_by_kind[kind]) for kind in KINDS),
                        len(all_collapsed),
                        partition_unjoinable,
                        path,
                        digest,
                        lineage_path,
                        lineage_sha,
                        reused and lineage_reused,
                    )
                )
            gap = _publish_gap_artifact(
                tree,
                product=BASIS_PRODUCT,
                symbol=symbol,
                month=month,
                gap_rows=basis_gap_rows,
                raw_objects=raw_objects,
                collapsed=all_collapsed,
                unjoinable=unjoinable,
                hooks=hooks,
            )
            if gap is not None:
                gap_artifacts[BASIS_PRODUCT].append(gap)
            physical_rows[BASIS_PRODUCT] += sum(len(parsed_by_kind[kind]) for kind in KINDS)
            collapsed_rows[BASIS_PRODUCT] += len(all_collapsed)
            unjoinable_rows[BASIS_PRODUCT] += partition_unjoinable

        _require(premium_zip_reads == sum(source.kind == PREMIUM for source in ordered), "premium ZIP was not read exactly once")
        _require(bool(partitions[INDICATIVE_PRODUCT]), "indicative product has no observed premium rows")
        _require(bool(partitions[BASIS_PRODUCT]), "basis product has no causally joined rows")
        product_rows = {product: sum(part.row_count for part in partitions[product]) for product in PRODUCTS}
        _require(
            physical_rows[INDICATIVE_PRODUCT] - collapsed_rows[INDICATIVE_PRODUCT] == product_rows[INDICATIVE_PRODUCT],
            "indicative physical/collapsed/product row equation failed",
        )
        _require(
            physical_rows[BASIS_PRODUCT] - collapsed_rows[BASIS_PRODUCT]
            == 3 * product_rows[BASIS_PRODUCT] + unjoinable_rows[BASIS_PRODUCT],
            "basis physical/collapsed/joined/unjoinable row equation failed",
        )
        _require(product_rows[INDICATIVE_PRODUCT] <= ACCEPTED_PROJECTIONS[INDICATIVE_PRODUCT]["projected_rows"], "indicative rows exceed sizing ceiling")
        _require(product_rows[BASIS_PRODUCT] <= ACCEPTED_PROJECTIONS[BASIS_PRODUCT]["projected_rows"], "basis rows exceed sizing ceiling")
        _require(
            sum(gap.unjoinable_source_rows for gap in gap_artifacts[BASIS_PRODUCT])
            == unjoinable_rows[BASIS_PRODUCT],
            "basis gap artifacts do not reconcile unjoinable source rows",
        )
        source_partition_keys = {
            INDICATIVE_PRODUCT: {
                key
                for key, group in groups.items()
                if any(source.kind == PREMIUM for source in group)
            },
            BASIS_PRODUCT: set(groups),
        }
        partition_keys = {
            product: {(part.native_symbol, part.utc_month) for part in partitions[product]}
            for product in PRODUCTS
        }
        gap_keys = {
            product: {(gap.native_symbol, gap.utc_month) for gap in gap_artifacts[product]}
            for product in PRODUCTS
        }
        for product in PRODUCTS:
            _require(
                partition_keys[product] | gap_keys[product] == source_partition_keys[product],
                f"{product} source partitions do not reconcile to products and gaps",
            )
        if enforce_full_corpus:
            _require(premium_zip_reads == ACCEPTED_PREMIUM_SOURCES, "full-corpus premium reads changed")
            _require(sum(source.byte_size for source in ordered if source.kind == PREMIUM) == ACCEPTED_PREMIUM_BYTES, "full-corpus premium bytes changed")
            _require(len(partitions[INDICATIVE_PRODUCT]) == ACCEPTED_PREMIUM_PARTITIONS, "full-corpus indicative partitions changed")
            _require(len(partitions[BASIS_PRODUCT]) <= ACCEPTED_JOINABLE_PARTITIONS, "basis output partitions exceed all-family partitions")

        normalizer_sha, _size = _digest_path(Path(__file__).resolve(strict=True))
        results: dict[str, ProductResult] = {}
        for product in PRODUCTS:
            selected_sources = [
                source for source in ordered if product == BASIS_PRODUCT or source.kind == PREMIUM
            ]
            source_hasher = hashlib.sha256()
            for source in selected_sources:
                source_hasher.update(
                    _canonical_json(
                        {
                            "source_key": source.source_key,
                            "source_sha256": source.source_sha256,
                            "byte_size": source.byte_size,
                            "validation_state": source.validation_state,
                        }
                    )
                )
            verified = sum(source.validation_state == OUTCOME_CHECKSUM_VERIFIED for source in selected_sources)
            retained = sum(source.validation_state == OUTCOME_RETAINED for source in selected_sources)
            gaps = gap_artifacts[product]
            completion = {
                "document_type": f"{product}_product_completion",
                "schema_version": 1,
                "required_product": product,
                "schema_sha256": SCHEMA_SHA256[product],
                "schema": _schema_contract(SCHEMAS[product]),
                "writer_identity": writer_identity(),
                "normalizer_source_sha256": normalizer_sha,
                "authorities_authenticated": enforce_full_corpus,
                "authority_sha256": {
                    "generation0_seal_head": ACCEPTED_GENERATION0_SEAL_HEAD,
                    "report": REPORT_SHA256,
                    "sizing": SIZING_SHA256,
                    "schema": SCHEMA_SHA256[product],
                },
                "generation0": {
                    "binance_completions": ACCEPTED_GENERATION0_BINANCE_COMPLETIONS,
                    "selected_sources": len(selected_sources),
                    "selected_source_bytes": sum(source.byte_size for source in selected_sources),
                    "checksum_verified_sources": verified,
                    "retained_credit_sources": retained,
                },
                "source_families": {
                    family: {
                        "source_count": sum(source.family == family for source in selected_sources),
                        "source_bytes": sum(source.byte_size for source in selected_sources if source.family == family),
                        "checksum_verified_sources": sum(source.family == family and source.validation_state == OUTCOME_CHECKSUM_VERIFIED for source in selected_sources),
                        "retained_credit_sources": sum(source.family == family and source.validation_state == OUTCOME_RETAINED for source in selected_sources),
                        "physical_source_rows": physical_by_family[family],
                        "collapsed_identical_rows": collapsed_by_family[family],
                    }
                    for family in FAMILIES
                    if any(source.family == family for source in selected_sources)
                },
                "qualification_report": report_binding,
                "sizing_ceiling": ACCEPTED_PROJECTIONS[product],
                "sources_sha256": source_hasher.hexdigest(),
                "partitions": [_partition_descriptor(part, tree) for part in partitions[product]],
                "quality_gap_artifacts": [_gap_descriptor(gap, tree) for gap in gaps],
                "partition_reconciliation": {
                    "source_partition_count": len(source_partition_keys[product]),
                    "successful_partition_count": len(partition_keys[product]),
                    "gap_only_partition_count": len(gap_keys[product] - partition_keys[product]),
                    "partitions_with_gaps": len(gap_keys[product] & partition_keys[product]),
                },
                "observed_ranges": ranges[product].finish(),
                "row_equation": {
                    "physical_source_rows": physical_rows[product],
                    "collapsed_identical_rows": collapsed_rows[product],
                    "joined_input_rows": 3 * product_rows[product] if product == BASIS_PRODUCT else product_rows[product],
                    "unjoinable_source_rows": unjoinable_rows[product],
                    "excluded_source_rows": 0,
                    "fabricated_rows": 0,
                    "source_decimal_rounding_events": 0,
                    "relative_basis_floor_applications": product_rows[product] if product == BASIS_PRODUCT else 0,
                    "product_rows": product_rows[product],
                },
                "gap_reconciliation": {
                    "artifact_count": len(gaps),
                    "gap_rows": sum(gap.row_count for gap in gaps),
                    "missing_grid_points": sum(gap.missing_grid_points for gap in gaps),
                    "unjoinable_source_rows": sum(gap.unjoinable_source_rows for gap in gaps),
                    "unjoinable_source_rows_by_kind": dict(unjoinable_by_kind) if product == BASIS_PRODUCT else {},
                },
            }
            expected = hashlib.sha256(_canonical_json(completion)).hexdigest()
            tree.require_only_completion(product, f"{expected}.json")
            completion_path, completion_sha, completion_reused = _publish_json(
                tree,
                completion,
                product=product,
                parts=(product, ".complete"),
                prefix=f"completion-{product}",
                kind="completion",
                hooks=hooks,
            )
            _require(completion_sha == expected, f"{product} completion identity changed")
            tree.require_only_completion(product, f"{expected}.json")
            tree.verify_paths(
                [
                    *(part.parquet_path for part in partitions[product]),
                    *(part.lineage_path for part in partitions[product]),
                    *(gap.parquet_path for gap in gaps),
                    *(gap.lineage_path for gap in gaps),
                    completion_path,
                ]
            )
            results[product] = ProductResult(
                product,
                SCHEMA_SHA256[product],
                tuple(partitions[product]),
                tuple(gaps),
                completion_path,
                completion_sha,
                completion_reused,
                physical_rows[product],
                collapsed_rows[product],
                unjoinable_rows[product],
                product_rows[product],
            )
        return PriceStateNormalizationResult(
            results[INDICATIVE_PRODUCT], results[BASIS_PRODUCT], premium_zip_reads
        )
    finally:
        tree.close()


def normalize_price_state_sources(
    sources: Iterable[RawPriceStateObject],
    output_root: Path,
    *,
    report: Mapping[str, Any] | None = None,
    sizing: Mapping[str, Any] | None = None,
    hooks: PublicationHooks = PublicationHooks(),
) -> PriceStateNormalizationResult:
    """Normalize bounded authenticated-shaped sources for focused tests."""
    return _normalize(
        sources,
        output_root,
        report=report,
        sizing=sizing,
        enforce_full_corpus=False,
        hooks=hooks,
    )


def normalize_from_authorities(
    *,
    generation0_state: Path,
    generation0_content_root: Path,
    report: Path,
    sizing: Path,
    output_root: Path,
    hooks: PublicationHooks = PublicationHooks(),
) -> PriceStateNormalizationResult:
    """Publish both products from the exact pinned generation-0 authorities."""
    sources = load_generation0_sources(generation0_state, generation0_content_root)
    report_document = _read_pinned_json(report, REPORT_SHA256, MAX_REPORT_BYTES)
    sizing_document = _read_pinned_json(sizing, SIZING_SHA256, MAX_SIZING_BYTES)
    return _normalize(
        sources,
        output_root,
        report=report_document,
        sizing=sizing_document,
        enforce_full_corpus=True,
        hooks=hooks,
    )
