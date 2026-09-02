"""Concrete Gate-3 normalizer for Binance USD-M realized funding events.

Each authenticated monthly ``fundingRate`` row is one observed settlement.  The
converter preserves its timestamp, source-declared positive interval, and exact
rate, publishes exact long/short cashflow, and never expands, fills, rescales,
or invents a settlement.  ADR-0036 is normative.
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
    PRODUCT_FUNDING_REALIZED,
    SIZING_ROW_BATCH,
    convert_decimal,
    convert_integer,
    final_product_schema,
    native_identity,
    product_schema_identity,
    writer_identity,
)

PRODUCT = PRODUCT_FUNDING_REALIZED
FAMILY = "monthly/fundingRate"
FUNDING_FIELDS = KNOWN_ARCHIVE_SCHEMAS["fundingRate"]["headerless"]
SCHEMA = final_product_schema(PRODUCT)
SCHEMA_SHA256 = product_schema_identity(PRODUCT)
REPORT_SHA256 = "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
SIZING_SHA256 = "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589"
SIZING_POLICY_IDENTITY = "adr0027_review257_partition_aware_dictionary_storage_sizing_v3"
CASHFLOW_SIGN_CONVENTION = "long_pays_short_when_rate_positive"
IDENTICAL_OBSERVED_SETTLEMENT = "identical_observed_settlement"
CHECKSUM_AUTHORITY = "binance_checksum_sidecar"
UNKNOWN_AVAILABILITY = "unknown_not_imputed"

ACCEPTED_GENERATION0_BINANCE_COMPLETIONS = 685_072
ACCEPTED_GENERATION0_SEAL_HEAD = "8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab"
ACCEPTED_SOURCE_COUNT = 21_035
ACCEPTED_SOURCE_BYTES = 21_351_804
ACCEPTED_CHECKSUM_VERIFIED_SOURCES = 21_020
ACCEPTED_RETAINED_CREDIT_SOURCES = 15
ACCEPTED_PROJECTED_ROWS = 15_660_013
ACCEPTED_PROJECTED_BYTES = 941_985_964
ACCEPTED_LARGEST_PARTITION_BYTES = 72_726
ACCEPTED_COVERAGE_GAP_ROWS = 959
ACCEPTED_TYPED_GAP_SYMBOLS = 675
ACCEPTED_COVERAGE_GAP_KINDS: tuple[str, ...] = (
    "current_unarchived",
    "head_gap_family_launch",
    "head_gap_pre_listing",
    "head_gap_unexplained",
    "head_gap_unknown_onboard",
    "interior_month_gap",
    "tail_gap_missing_recent",
    "tail_gap_post_close",
    "tail_gap_unknown_close",
)

MAX_COMPRESSED_OBJECT_BYTES = 16 * 2**20
MAX_DECOMPRESSED_MEMBER_BYTES = 32 * 2**20
MAX_ROWS_PER_OBJECT = 8_192
MAX_CSV_FIELD_BYTES = 1 * 2**20
MAX_REPORT_BYTES = 16 * 2**20
MAX_SIZING_BYTES = 48 * 2**20
MAX_SIDECAR_BYTES = SIDECAR_CEILING_BYTES
_SIDECAR_STATEMENT = re.compile(r"([0-9a-fA-F]{64})[ \t]+(\S+)\s*")
RENAME_NOREPLACE = 1

_HEX_RE = re.compile(r"[0-9a-f]{64}")
_KEY_RE = re.compile(
    r"data/futures/um/monthly/fundingRate/(?P<symbol>[A-Z0-9_]+)/"
    r"(?P=symbol)-fundingRate-(?P<period>\d{4}-\d{2})\.zip"
)


class FundingNormalizationError(RuntimeError):
    """Fail-closed authority, typing, cashflow, or publication error."""


@dataclass(frozen=True, slots=True)
class RawFundingObject:
    source_key: str
    family: str
    native_symbol: str
    economic_period: str
    path: Path
    source_sha256: str
    byte_size: int
    validation_state: str
    checksum_authority: str = CHECKSUM_AUTHORITY
    retrieval_time: str | None = None
    source_available_at: int | None = None


@dataclass(frozen=True, slots=True)
class PublishedPartition:
    native_symbol: str
    utc_month: str
    row_count: int
    physical_row_count: int
    collapsed_row_count: int
    parquet_path: Path
    parquet_sha256: str
    lineage_path: Path
    lineage_sha256: str
    reused: bool


@dataclass(frozen=True, slots=True)
class FundingNormalizationResult:
    schema_sha256: str
    writer_identity: str
    partitions: tuple[PublishedPartition, ...]
    completion_path: Path
    completion_sha256: str
    completion_reused: bool
    physical_source_rows: int
    collapsed_identical_rows: int
    product_rows: int


@dataclass(frozen=True, slots=True)
class PublicationHooks:
    """Test-only interruption boundary; production callers leave it unset."""

    before_publish: Callable[[str, Path, Path], None] | None = None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FundingNormalizationError(message)


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _schema_contract() -> list[dict[str, Any]]:
    return [
        {"name": field.name, "arrow_type": str(field.type), "nullable": field.nullable}
        for field in SCHEMA
    ]


def _is_digest(value: object) -> bool:
    return type(value) is str and _HEX_RE.fullmatch(value) is not None


def _identity_parts(key: str) -> tuple[str, str]:
    match = _KEY_RE.fullmatch(key)
    _require(match is not None, "raw funding identity is not canonical monthly USD-M")
    assert match is not None
    period = match.group("period")
    try:
        parsed = datetime.strptime(period, "%Y-%m").strftime("%Y-%m")
    except ValueError as exc:
        raise FundingNormalizationError("raw funding identity has an invalid economic period") from exc
    _require(parsed == period, "raw funding identity period is not canonical")
    return match.group("symbol"), period


def _require_no_symlink_components(path: Path, *, label: str) -> None:
    absolute = path.absolute()
    for component in reversed((absolute, *absolute.parents)):
        if not component.exists() and not component.is_symlink():
            continue
        try:
            facts = component.lstat()
        except OSError as exc:
            raise FundingNormalizationError(f"{label} cannot be inspected safely") from exc
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
            raise FundingNormalizationError("authority object is not reachable") from exc
        _require(not stat.S_ISLNK(facts.st_mode), "authority path contains a symlink")
    _require(current.is_file(), "authority object is not a regular file")
    _require(current.resolve(strict=True).is_relative_to(root), "authority path escapes its root")
    return current


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


def _open_regular_child(directory: int, name: str, *, label: str) -> int | None:
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise FundingNormalizationError(f"{label} cannot be opened no-follow") from exc
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise FundingNormalizationError(f"{label} is not a regular file")
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
        raise FundingNormalizationError("atomic no-replace rename is unavailable") from exc
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


def _require_accepted_validation_state(state: object) -> None:
    _require(
        type(state) is str and state in (OUTCOME_CHECKSUM_VERIFIED, OUTCOME_RETAINED),
        "generation-0 funding completion validation state is not accepted",
    )


def _require_fixed_generation0_terminal(state: AcquisitionState) -> None:
    state.authenticate_schema()
    state.authenticate_domains()
    state.authenticate_singletons()
    state.authenticate_prefix()
    state._require_runnable_head()
    head = state.seal_head_row()
    _require(head is not None, "generation-0 seal head is missing")
    assert head is not None
    _require(head["receipt_sha256"] == ACCEPTED_GENERATION0_SEAL_HEAD, "generation-0 seal head changed")


def _validate_plan_payload(identity: str, payload: object, listed_bytes: int) -> tuple[str, str]:
    _require(type(payload) is dict, "generation-0 funding plan payload is not an object")
    assert isinstance(payload, dict)
    symbol, period = _identity_parts(identity)
    _require(payload.get("key") == identity, "generation-0 funding plan key changed")
    _require(payload.get("family") == FAMILY, "generation-0 funding plan family changed")
    _require(payload.get("symbol") == symbol, "generation-0 funding plan symbol changed")
    _require(payload.get("economic_interval") == period, "generation-0 funding plan period changed")
    _require(payload.get("listed_bytes") == listed_bytes, "generation-0 funding plan byte size changed")
    _require(payload.get("sidecar_key") == f"{identity}.CHECKSUM", "generation-0 funding sidecar identity changed")
    return symbol, period


def _validate_plan_envelope(identity: str, envelope: object, plan_kind: object) -> Mapping[str, Any]:
    _require(plan_kind == KIND_BINANCE, "generation-0 plan kind is not binance_object")
    _require(type(envelope) is dict, "generation-0 plan envelope is not an object")
    assert isinstance(envelope, dict)
    _require(envelope.get("provider") == PROVIDER_BINANCE, "generation-0 plan envelope provider changed")
    _require(envelope.get("identity") == identity, "generation-0 plan envelope identity changed")
    _require(envelope.get("kind") == KIND_BINANCE, "generation-0 plan envelope kind is not binance_object")
    payload = envelope.get("payload")
    _require(type(payload) is dict, "generation-0 funding plan payload is not an object")
    assert isinstance(payload, dict)
    return payload


def _parse_sidecar_statement(body: bytes, *, content_sha256: str, zip_basename: str) -> None:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FundingNormalizationError("funding sidecar is not UTF-8") from exc
    match = _SIDECAR_STATEMENT.fullmatch(text)
    _require(match is not None, "funding sidecar statement is malformed")
    digest = match.group(1).lower()
    name = match.group(2)
    _require(_is_digest(digest), "funding sidecar checksum is invalid")
    _require(name == zip_basename, "funding sidecar names a different ZIP basename")
    _require(digest == content_sha256, "funding sidecar checksum does not equal the raw digest")


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
    _require(_is_digest(completion_sidecar_sha256), "generation-0 completion sidecar digest is invalid")
    _require(_is_digest(fact_sidecar_sha256), "generation-0 sidecar-fact digest is invalid")
    _require(
        completion_sidecar_sha256 == fact_sidecar_sha256,
        "generation-0 completion/sidecar-fact digest disagreement",
    )
    _require(
        type(fact_sidecar_bytes) is int and 0 < fact_sidecar_bytes <= MAX_SIDECAR_BYTES,
        "generation-0 sidecar byte count is not a positive exact bound",
    )
    digest = str(fact_sidecar_sha256)
    expected = content_root / digest[:2] / digest
    _require(
        Path(str(completion_sidecar_path)) == expected,
        "generation-0 completion sidecar path is not its content address",
    )
    _require(
        Path(str(fact_sidecar_path)) == expected,
        "generation-0 sidecar-fact path is not its content address",
    )
    _require(
        Path(str(completion_sidecar_path)) == Path(str(fact_sidecar_path)),
        "generation-0 completion/sidecar-fact path disagreement",
    )
    _require(str(provider_checksum) == content_sha256, "generation-0 provider/content checksum conflict")
    path = _safe_authority_file(content_root, PurePosixPath(digest[:2], digest))
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        raise FundingNormalizationError("funding sidecar cannot be opened no-follow") from exc
    try:
        body = _read_fd(descriptor, MAX_SIDECAR_BYTES)
    finally:
        os.close(descriptor)
    _require(len(body) == fact_sidecar_bytes, "generation-0 sidecar size changed")
    _require(hashlib.sha256(body).hexdigest() == digest, "generation-0 sidecar digest changed")
    _parse_sidecar_statement(body, content_sha256=content_sha256, zip_basename=zip_basename)


def load_generation0_sources(state_path: Path, content_root: Path) -> tuple[RawFundingObject, ...]:
    """Authenticate and select the exact generation-0 monthly funding authority."""
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
        connection = sqlite3.connect(f"file:/proc/self/fd/{parent_fd}/{name}?mode=ro", uri=True, isolation_level=None)
        reopened = _open_regular_child(parent_fd, name, label="generation-0 SQLite state")
        _require(reopened is not None, "generation-0 SQLite state disappeared")
        assert state_fd is not None and reopened is not None
        try:
            before = os.fstat(state_fd)
            after = os.fstat(reopened)
            _require((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino), "generation-0 SQLite state was replaced")
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
        _require(not connection.execute("PRAGMA foreign_key_check").fetchall(), "generation-0 SQLite foreign keys do not reconcile")
        borrowed = AcquisitionState(state_path, state_path.with_name("acquisition.lock"))
        borrowed.conn = connection
        _require_fixed_generation0_terminal(borrowed)
        total = connection.execute("SELECT COUNT(*) FROM completion WHERE provider='binance_vision'").fetchone()
        _require(total is not None and int(total[0]) == ACCEPTED_GENERATION0_BINANCE_COMPLETIONS, "generation-0 Binance completion count changed")
        cursor = connection.execute(
            "SELECT p.identity,p.kind,p.payload_json,c.content_sha256,c.content_path,c.listed_bytes,"
            "c.retrieved_at,c.validation_state,c.sidecar_sha256,c.sidecar_path,"
            "s.provider_checksum,s.sidecar_sha256,s.sidecar_path,s.sidecar_bytes "
            "FROM plan_entry p JOIN completion c ON c.provider=p.provider AND c.identity=p.identity "
            "JOIN sidecar_fact s ON s.provider=p.provider AND s.identity=p.identity "
            "WHERE p.provider='binance_vision' ORDER BY p.identity"
        )
        accepted: list[RawFundingObject] = []
        source_bytes = 0
        verified = 0
        retained = 0
        try:
            for (
                identity,
                plan_kind,
                payload_json,
                content_sha,
                content_path,
                listed,
                retrieved,
                state,
                completion_sidecar_sha,
                completion_sidecar_path,
                provider_sha,
                fact_sidecar_sha,
                fact_sidecar_path,
                fact_sidecar_bytes,
            ) in cursor:
                try:
                    envelope = json.loads(str(payload_json))
                except json.JSONDecodeError as exc:
                    raise FundingNormalizationError("generation-0 plan payload is invalid JSON") from exc
                nested = envelope.get("payload") if type(envelope) is dict else None
                if type(nested) is not dict or nested.get("family") != FAMILY:
                    continue
                payload = _validate_plan_envelope(str(identity), envelope, plan_kind)
                size = int(listed)
                symbol, period = _validate_plan_payload(str(identity), payload, size)
                digest = str(content_sha)
                _require(_is_digest(digest), "generation-0 content digest is invalid")
                _require_accepted_validation_state(state)
                expected = content_root / digest[:2] / digest
                _require(Path(str(content_path)) == expected, "generation-0 content path is not its content address")
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
                    RawFundingObject(
                        source_key=str(identity),
                        family=FAMILY,
                        native_symbol=symbol,
                        economic_period=period,
                        path=path,
                        source_sha256=digest,
                        byte_size=size,
                        validation_state=str(state),
                        retrieval_time=str(retrieved),
                    )
                )
                source_bytes += size
                if state == OUTCOME_CHECKSUM_VERIFIED:
                    verified += 1
                else:
                    retained += 1
        finally:
            cursor.close()
        _require(len(accepted) == ACCEPTED_SOURCE_COUNT, "generation-0 selected funding count changed")
        _require(source_bytes == ACCEPTED_SOURCE_BYTES, "generation-0 selected funding bytes changed")
        _require(verified == ACCEPTED_CHECKSUM_VERIFIED_SOURCES, "generation-0 checksum-verified funding count changed")
        _require(retained == ACCEPTED_RETAINED_CREDIT_SOURCES, "generation-0 retained-credit funding count changed")
        connection.execute("ROLLBACK")
        borrowed.conn = None
        return tuple(accepted)
    except sqlite3.Error as exc:
        raise FundingNormalizationError("generation-0 authority cannot be read safely") from exc
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
    _require_no_symlink_components(path, label="funding authority path")
    parent = path.absolute().parent
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    descriptor: int | None = None
    try:
        try:
            descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
        except OSError as exc:
            raise FundingNormalizationError("funding authority cannot be opened no-follow") from exc
        body = _read_fd(descriptor, maximum)
        _require(hashlib.sha256(body).hexdigest() == expected_sha256, "funding authority digest changed")
        try:
            document = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FundingNormalizationError("funding authority is not valid JSON") from exc
        _require(type(document) is dict, "funding authority is not an object")
        return document
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_fd)


def _funding_projection(sizing: Mapping[str, Any]) -> Mapping[str, Any]:
    projections = sizing.get("projections")
    _require(type(projections) is dict, "sizing projections are missing")
    products = projections.get("required_products")
    _require(type(products) is list and bool(products), "sizing required products are missing")
    matches = [item for item in products if type(item) is dict and item.get("required_product") == PRODUCT]
    _require(len(matches) == 1, "sizing realized-funding projection is missing")
    return matches[0]


def _validate_sizing(sizing: Mapping[str, Any]) -> None:
    authority = sizing.get("authority")
    code = sizing.get("code_identity")
    projections = sizing.get("projections")
    _require(type(authority) is dict and type(code) is dict and type(projections) is dict, "sizing authority shape changed")
    bindings = authority.get("bindings")
    _require(type(bindings) is dict, "sizing authority bindings are missing")
    _require(bindings.get("report_sha256") == REPORT_SHA256, "sizing report binding changed")
    _require(code.get("policy_identity") == SIZING_POLICY_IDENTITY, "sizing policy changed")
    _require(code.get("writer_identity") == writer_identity(), "sizing writer identity changed")
    schemas = projections.get("final_product_schemas")
    _require(type(schemas) is dict and schemas.get(PRODUCT) == _schema_contract(), "accepted realized-funding schema changed")
    projection = _funding_projection(sizing)
    _require(projection.get("projected_rows") == ACCEPTED_PROJECTED_ROWS, "realized-funding projected rows changed")
    _require(projection.get("projected_bytes") == ACCEPTED_PROJECTED_BYTES, "realized-funding projected bytes changed")
    _require(projection.get("partition_count") == ACCEPTED_SOURCE_COUNT, "realized-funding projected partitions changed")
    _require(projection.get("largest_partition_bytes") == ACCEPTED_LARGEST_PARTITION_BYTES, "realized-funding largest partition changed")
    _require(projection.get("input_objects") == ACCEPTED_SOURCE_COUNT, "realized-funding input objects changed")
    _require(projection.get("input_compressed_bytes") == ACCEPTED_SOURCE_BYTES, "realized-funding input bytes changed")


def _product_matrix_row(report: Mapping[str, Any]) -> Mapping[str, Any]:
    matrix = report.get("product_matrix")
    _require(type(matrix) is list and bool(matrix), "report product matrix is missing")
    matches = [item for item in matrix if type(item) is dict and item.get("product") == PRODUCT]
    _require(len(matches) == 1, "report realized-funding product row is missing")
    return matches[0]


def _validate_report(report: Mapping[str, Any], *, enforce_full_corpus: bool) -> Mapping[str, Any]:
    row = _product_matrix_row(report)
    gaps = row.get("universe_coverage_gaps")
    typed = row.get("typed_gap_symbols")
    kinds = row.get("coverage_gap_kinds")
    _require(type(gaps) is list, "report realized-funding coverage gaps are missing")
    _require(type(typed) is list, "report realized-funding typed-gap symbols are missing")
    _require(type(kinds) is list, "report realized-funding coverage-gap kinds are missing")
    if enforce_full_corpus:
        _require(len(gaps) == ACCEPTED_COVERAGE_GAP_ROWS, "report realized-funding coverage-gap count changed")
        _require(len(typed) == ACCEPTED_TYPED_GAP_SYMBOLS, "report realized-funding typed-gap symbol count changed")
        _require(tuple(kinds) == ACCEPTED_COVERAGE_GAP_KINDS, "report realized-funding coverage-gap kinds changed")
        _require(row.get("accepted_universe_object_count") == ACCEPTED_SOURCE_COUNT, "report realized-funding object count changed")
        _require(row.get("accepted_universe_listed_bytes") == ACCEPTED_SOURCE_BYTES, "report realized-funding listed bytes changed")
        storage = report.get("storage")
        _require(type(storage) is dict, "report storage authority is missing")
        stored = storage.get("universe_coverage_gaps")
        _require(type(stored) is dict, "report stored coverage gaps are missing")
        stored_gaps = stored.get(PRODUCT)
        _require(type(stored_gaps) is list and len(stored_gaps) == ACCEPTED_COVERAGE_GAP_ROWS, "stored realized-funding coverage-gap count changed")
    return {
        "report_sha256": REPORT_SHA256,
        "coverage_gap_rows": len(gaps),
        "typed_gap_symbol_count": len(typed),
        "coverage_gap_kinds": list(kinds),
        "bound": True,
    }


def _unscaled(value: Decimal) -> int:
    parts = value.as_tuple()
    coefficient = int("".join(str(digit) for digit in parts.digits) or "0")
    _require(parts.exponent >= -DECIMAL_SCALE, "decimal exceeds pinned scale")
    coefficient *= 10 ** (parts.exponent + DECIMAL_SCALE)
    return -coefficient if parts.sign else coefficient


def _scaled(value: int) -> Decimal:
    digits = tuple(int(character) for character in str(abs(value))) if value else (0,)
    _require(len(digits) <= 38, "derived cashflow decimal overflows pinned precision")
    return Decimal((1 if value < 0 else 0, digits, -DECIMAL_SCALE))


def _integer(token: str, source: RawFundingObject, column: str, ordinal: int) -> int:
    try:
        return convert_integer(token, key=source.source_key, output=PRODUCT, column=column, row=ordinal)
    except Exception as exc:
        raise FundingNormalizationError(f"funding {column} is not an exact integer") from exc


def _decimal(token: str, source: RawFundingObject, column: str, ordinal: int) -> Decimal:
    try:
        return convert_decimal(token, key=source.source_key, output=PRODUCT, column=column, row=ordinal)
    except Exception as exc:
        raise FundingNormalizationError(f"funding {column} is not an exact decimal") from exc


def _utc_month(calc_time: int) -> str:
    _require(calc_time >= 0, "funding calc_time is negative")
    return datetime.fromtimestamp(calc_time // 1000, tz=UTC).strftime("%Y-%m")


class _OutputTree:
    def __init__(self, root: Path) -> None:
        _require(root.name.startswith("."), "funding output root must be hidden")
        _require_no_symlink_components(root, label="funding output root")
        if not root.exists():
            root.mkdir(mode=0o700)
            _fsync_directory(root.parent)
        self.root = root.resolve(strict=True)
        self.root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            fcntl.flock(self.root_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self.root_fd)
            raise FundingNormalizationError("another normalizer holds the funding root") from exc
        self.root_facts = os.fstat(self.root_fd)
        os.close(self.directory((".staging",), create=True))

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
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
                except OSError as exc:
                    raise FundingNormalizationError("funding output directory is unsafe") from exc
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
            descriptor = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=directory)
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
        kind: str,
        hooks: PublicationHooks,
    ) -> tuple[bool, int, Path]:
        staging = self.directory((".staging",), create=False)
        destination = self.directory(parts, create=True)
        path = self.root.joinpath(*parts, name)
        try:
            if hooks.before_publish is not None:
                hooks.before_publish(kind, self.root / ".staging" / stage_name, path)
            try:
                _rename_noreplace_at(staging, stage_name, destination, name)
                os.fsync(destination)
                os.fsync(staging)
                reused = False
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise FundingNormalizationError("content-addressed funding publication failed") from exc
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
            _require(stat.S_ISREG(os.fstat(final_fd).st_mode), "published funding object is not regular")
            return reused, final_fd, path
        finally:
            os.close(destination)
            os.close(staging)

    def require_only_completion(self, name: str) -> None:
        directory = self.directory((".complete",), create=True)
        try:
            _require(not [entry for entry in os.listdir(directory) if entry != name], "another funding completion already exists")
        finally:
            os.close(directory)

    def verify_paths(self, paths: Iterable[Path]) -> None:
        current = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            facts = os.fstat(current)
            _require((facts.st_dev, facts.st_ino) == (self.root_facts.st_dev, self.root_facts.st_ino), "held funding root was replaced")
        finally:
            os.close(current)
        for path in paths:
            _require(path.is_relative_to(self.root), "published path escapes the held root")
            relative = path.relative_to(self.root)
            directory = self.directory(relative.parts[:-1], create=False)
            try:
                descriptor = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
                _require(stat.S_ISREG(os.fstat(descriptor).st_mode), "published funding path is unsafe")
                os.close(descriptor)
            finally:
                os.close(directory)


def _verify_parquet_fd(descriptor: int, rows: int, digest: str) -> None:
    actual, _size = _digest_fd(descriptor)
    _require(actual == digest, "published Parquet digest changed")
    try:
        parquet = pq.ParquetFile(f"/proc/self/fd/{descriptor}")
    except (OSError, pa.ArrowInvalid) as exc:
        raise FundingNormalizationError("published Parquet is unreadable") from exc
    _require(parquet.schema_arrow == SCHEMA, "published Parquet schema changed")
    _require(parquet.metadata.num_rows == rows, "published Parquet row count changed")


def _publish_parquet(
    tree: _OutputTree,
    table: pa.Table,
    *,
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
        _verify_parquet_fd(stage_fd, table.num_rows, digest)
        reused, final_fd, path = tree.publish(stage_name, stage_fd, parts, f"{digest}.parquet", kind=kind, hooks=hooks)
        _verify_parquet_fd(final_fd, table.num_rows, digest)
        return path, digest, reused
    finally:
        if final_fd is not None:
            os.close(final_fd)
        os.close(stage_fd)


def _publish_json(
    tree: _OutputTree,
    document: Mapping[str, Any],
    *,
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
        reused, final_fd, path = tree.publish(stage_name, stage_fd, parts, f"{digest}.json", kind=kind, hooks=hooks)
        actual, _size = _digest_fd(final_fd)
        _require(actual == digest and _read_fd(final_fd) == body, "published JSON changed")
        return path, digest, reused
    finally:
        if final_fd is not None:
            os.close(final_fd)
        os.close(stage_fd)


def _safe_zip_member(archive: zipfile.ZipFile, source: RawFundingObject) -> zipfile.ZipInfo:
    members = archive.infolist()
    _require(len(members) == 1, "funding ZIP must contain exactly one member")
    member = members[0]
    name = member.filename
    parts = PurePosixPath(name.replace("\\", "/"))
    _require(bool(name) and not parts.is_absolute() and ".." not in parts.parts, "funding ZIP member path is unsafe")
    _require(len(parts.parts) == 1 and name.endswith(".csv"), "funding ZIP member is not one root CSV")
    _require(stat.S_IFMT(member.external_attr >> 16) in {0, stat.S_IFREG}, "funding ZIP member is not regular")
    _require(not (member.flag_bits & 0x1), "encrypted funding ZIP is unsupported")
    _require(member.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}, "funding ZIP compression is unsupported")
    _require(0 < member.file_size <= MAX_DECOMPRESSED_MEMBER_BYTES, "funding ZIP member exceeds parser bound")
    _require(member.compress_size <= MAX_COMPRESSED_OBJECT_BYTES, "funding compressed member exceeds parser bound")
    _require(name == source.source_key.rsplit("/", 1)[-1][:-4] + ".csv", "funding ZIP member name conflicts with source identity")
    return member


def _authenticated_source_bytes(source: RawFundingObject) -> bytes:
    try:
        descriptor = os.open(source.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        raise FundingNormalizationError("raw source cannot be opened no-follow") from exc
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    size = 0
    try:
        _require(stat.S_ISREG(os.fstat(descriptor).st_mode), "raw source path is not regular")
        while block := os.read(descriptor, 1024 * 1024):
            size += len(block)
            _require(size <= MAX_COMPRESSED_OBJECT_BYTES, "raw source exceeds compressed parser bound")
            digest.update(block)
            chunks.append(block)
    finally:
        os.close(descriptor)
    _require((digest.hexdigest(), size) == (source.source_sha256, source.byte_size), "raw source bytes do not match authority")
    return b"".join(chunks)


def _parse_funding_row(source: RawFundingObject, ordinal: int, row: Sequence[str]) -> dict[str, Any]:
    fields = dict(zip(FUNDING_FIELDS, row, strict=True))
    calc_time = _integer(fields["calc_time"], source, "calc_time", ordinal)
    interval = _integer(fields["funding_interval_hours"], source, "funding_interval_hours", ordinal)
    rate = _decimal(fields["last_funding_rate"], source, "last_funding_rate", ordinal)
    _require(interval > 0, "funding_interval_hours is not a positive source integer")
    _require(_utc_month(calc_time) == source.economic_period, "funding calc_time lies outside its source month")
    long_rate = _scaled(-_unscaled(rate))
    short_rate = rate
    _require(_unscaled(long_rate) + _unscaled(short_rate) == 0, "long and short cashflow rates are not conserved")
    return {
        "source_row_ordinal": ordinal,
        "calc_time": calc_time,
        "funding_interval_hours": interval,
        "last_funding_rate": rate,
        "long_cashflow_rate": long_rate,
        "short_cashflow_rate": short_rate,
        "cashflow_sign_convention": CASHFLOW_SIGN_CONVENTION,
    }


def _iter_funding_rows(source: RawFundingObject) -> Iterator[dict[str, Any]]:
    payload = _authenticated_source_bytes(source)
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            member = _safe_zip_member(archive, source)
            with archive.open(member, "r") as raw:
                stream = io.TextIOWrapper(raw, encoding="utf-8", newline="")
                reader = csv.reader(stream, strict=True)
                ordinal = 0
                first = True
                decompressed = 0
                for row in reader:
                    decompressed += sum(len(cell.encode()) for cell in row) + len(row)
                    _require(decompressed <= MAX_DECOMPRESSED_MEMBER_BYTES, "funding CSV exceeds decompressed parser bound")
                    _require(all(len(cell.encode()) <= MAX_CSV_FIELD_BYTES for cell in row), "funding CSV field exceeds parser bound")
                    if first:
                        first = False
                        if tuple(row) == FUNDING_FIELDS:
                            continue
                    _require(bool(row), "funding CSV contains an empty row")
                    _require(len(row) == len(FUNDING_FIELDS), "funding CSV row width is invalid")
                    _require(ordinal < MAX_ROWS_PER_OBJECT, "funding CSV exceeds row parser bound")
                    yield _parse_funding_row(source, ordinal, row)
                    ordinal += 1
                _require(ordinal > 0, "funding CSV contains no data rows")
    except (OSError, UnicodeError, csv.Error, zipfile.BadZipFile, RuntimeError) as exc:
        if isinstance(exc, FundingNormalizationError):
            raise
        raise FundingNormalizationError("funding ZIP/CSV is invalid") from exc


def _product_row(record: Mapping[str, Any], raw_ref: int, symbol: str) -> dict[str, Any]:
    return {
        "raw_object_ref": raw_ref,
        "source_row_ordinal": record["source_row_ordinal"],
        "venue_symbol": symbol,
        "calc_time": record["calc_time"],
        "funding_interval_hours": record["funding_interval_hours"],
        "last_funding_rate": record["last_funding_rate"],
        **native_identity(symbol),
        "long_cashflow_rate": record["long_cashflow_rate"],
        "short_cashflow_rate": record["short_cashflow_rate"],
        "cashflow_sign_convention": record["cashflow_sign_convention"],
    }


def _lineage_source(source: RawFundingObject, raw_ref: int) -> dict[str, Any]:
    return {
        "raw_object_ref": raw_ref,
        "source_key": source.source_key,
        "family": source.family,
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


def _validate_source_descriptor(source: RawFundingObject) -> None:
    symbol, period = _identity_parts(source.source_key)
    _require(source.family == FAMILY, "raw source family is not monthly fundingRate")
    _require((source.native_symbol, source.economic_period) == (symbol, period), "raw source descriptor conflicts with its identity")
    _require(_is_digest(source.source_sha256), "raw source digest is invalid")
    _require(type(source.byte_size) is int and 0 < source.byte_size <= MAX_COMPRESSED_OBJECT_BYTES, "raw source compressed size is invalid")
    _require_accepted_validation_state(source.validation_state)
    _require_no_symlink_components(source.path, label="raw source path")
    _require(source.path.is_file() and not source.path.is_symlink(), "raw source path is unsafe")
    _safe_component(source.native_symbol)


def _preflight_sources(sources: Iterable[RawFundingObject]) -> tuple[RawFundingObject, ...]:
    ordered = tuple(sorted(sources, key=lambda item: (item.native_symbol, item.economic_period, item.source_key)))
    identities: set[str] = set()
    partitions: set[tuple[str, str]] = set()
    for source in ordered:
        _require(source.source_key not in identities, "raw authority repeats a funding identity")
        identities.add(source.source_key)
        _validate_source_descriptor(source)
        key = (source.native_symbol, source.economic_period)
        _require(key not in partitions, "multiple sources claim one native-symbol/month partition")
        partitions.add(key)
    return ordered


def _collapse_identical_events(
    parsed: Sequence[tuple[int, RawFundingObject, dict[str, Any]]],
) -> tuple[list[tuple[int, RawFundingObject, dict[str, Any]]], list[dict[str, Any]]]:
    ordered = sorted(
        parsed,
        key=lambda item: (int(item[2]["calc_time"]), item[1].source_key, int(item[2]["source_row_ordinal"])),
    )
    kept: list[tuple[int, RawFundingObject, dict[str, Any]]] = []
    collapsed: list[dict[str, Any]] = []
    for raw_ref, source, record in ordered:
        if kept and int(record["calc_time"]) == int(kept[-1][2]["calc_time"]):
            kept_ref, kept_source, kept_record = kept[-1]
            same = (
                int(record["funding_interval_hours"]) == int(kept_record["funding_interval_hours"])
                and record["last_funding_rate"] == kept_record["last_funding_rate"]
            )
            _require(same, "repeated funding timestamp has conflicting interval or rate")
            collapsed.append(
                {
                    "source_key": source.source_key,
                    "source_sha256": source.source_sha256,
                    "kept_source_key": kept_source.source_key,
                    "kept_source_sha256": kept_source.source_sha256,
                    "kept_raw_object_ref": kept_ref,
                    "kept_source_row_ordinal": int(kept_record["source_row_ordinal"]),
                    "collapsed_raw_object_ref": raw_ref,
                    "collapsed_source_row_ordinal": int(record["source_row_ordinal"]),
                    "calc_time": int(record["calc_time"]),
                    "funding_interval_hours": int(record["funding_interval_hours"]),
                    "last_funding_rate": str(record["last_funding_rate"]),
                    "reason": IDENTICAL_OBSERVED_SETTLEMENT,
                }
            )
            continue
        kept.append((raw_ref, source, record))
    return kept, collapsed


class _ObservedRangeAccumulator:
    """Partition-bounded extrema and per-interval counts; never retains product rows."""

    def __init__(self) -> None:
        self.calc_time_min: int | None = None
        self.calc_time_max: int | None = None
        self.interval_min: int | None = None
        self.interval_max: int | None = None
        self.symbol_min: str | None = None
        self.symbol_max: str | None = None
        self.interval_counts: dict[int, int] = {}

    def add(self, calc_time: int, interval: int, symbol: str) -> None:
        self.calc_time_min = calc_time if self.calc_time_min is None else min(self.calc_time_min, calc_time)
        self.calc_time_max = calc_time if self.calc_time_max is None else max(self.calc_time_max, calc_time)
        self.interval_min = interval if self.interval_min is None else min(self.interval_min, interval)
        self.interval_max = interval if self.interval_max is None else max(self.interval_max, interval)
        self.symbol_min = symbol if self.symbol_min is None else min(self.symbol_min, symbol)
        self.symbol_max = symbol if self.symbol_max is None else max(self.symbol_max, symbol)
        self.interval_counts[interval] = self.interval_counts.get(interval, 0) + 1

    def finish(self) -> dict[str, Any]:
        _require(
            self.calc_time_min is not None
            and self.calc_time_max is not None
            and self.interval_min is not None
            and self.interval_max is not None
            and self.symbol_min is not None
            and self.symbol_max is not None,
            "funding product has no observed events",
        )
        return {
            "calc_time_min": self.calc_time_min,
            "calc_time_max": self.calc_time_max,
            "funding_interval_hours_min": self.interval_min,
            "funding_interval_hours_max": self.interval_max,
            "native_symbol_min": self.symbol_min,
            "native_symbol_max": self.symbol_max,
            "interval_histogram": [
                {"funding_interval_hours": interval, "event_count": self.interval_counts[interval]}
                for interval in sorted(self.interval_counts)
            ],
        }


def _normalize(
    sources: Iterable[RawFundingObject],
    output_root: Path,
    *,
    report: Mapping[str, Any] | None,
    sizing: Mapping[str, Any] | None,
    enforce_full_corpus: bool,
    hooks: PublicationHooks,
) -> FundingNormalizationResult:
    if sizing is not None:
        _validate_sizing(sizing)
    gap_authority = {
        "report_sha256": REPORT_SHA256,
        "coverage_gap_rows": 0,
        "typed_gap_symbol_count": 0,
        "coverage_gap_kinds": [],
        "bound": False,
    }
    if report is not None:
        gap_authority = dict(_validate_report(report, enforce_full_corpus=enforce_full_corpus))
    ordered = _preflight_sources(sources)
    groups: dict[tuple[str, str], list[RawFundingObject]] = {}
    for source in ordered:
        groups.setdefault((source.native_symbol, source.economic_period), []).append(source)
    tree = _OutputTree(output_root)
    try:
        partitions: list[PublishedPartition] = []
        physical_rows = 0
        collapsed_rows = 0
        observed = _ObservedRangeAccumulator()
        for (symbol, month), month_sources in sorted(groups.items()):
            raw_objects = sorted(month_sources, key=lambda item: item.source_key)
            parsed: list[tuple[int, RawFundingObject, dict[str, Any]]] = []
            for raw_ref, source in enumerate(raw_objects):
                for record in _iter_funding_rows(source):
                    parsed.append((raw_ref, source, record))
            physical = len(parsed)
            _require(physical > 0, "funding partition has no physical rows")
            kept, collapsed = _collapse_identical_events(parsed)
            product_rows = [_product_row(record, raw_ref, symbol) for raw_ref, _source, record in kept]
            for row in product_rows:
                _require(_utc_month(int(row["calc_time"])) == month, "funding row UTC month conflicts with partition")
                _require(row["cashflow_sign_convention"] == CASHFLOW_SIGN_CONVENTION, "cashflow sign convention changed")
                _require(_unscaled(row["long_cashflow_rate"]) + _unscaled(row["short_cashflow_rate"]) == 0, "partition cashflow is not conserved")
                observed.add(int(row["calc_time"]), int(row["funding_interval_hours"]), str(row["native_symbol"]))
            _require(physical - len(collapsed) == len(product_rows), "partition physical/collapsed/product equation failed")
            table = pa.Table.from_pylist(product_rows, schema=SCHEMA)
            _require(table.schema == SCHEMA, "funding row deviates from typed schema")
            parquet_path, parquet_sha, parquet_reused = _publish_parquet(
                tree,
                table,
                parts=(".partitions", symbol, month),
                prefix=f"partition-{symbol}-{month}",
                kind="partition",
                hooks=hooks,
            )
            lineage = {
                "document_type": f"{PRODUCT}_partition_lineage",
                "schema_version": 1,
                "required_product": PRODUCT,
                "native_symbol": symbol,
                "utc_month": month,
                "physical_row_count": physical,
                "collapsed_identical_row_count": len(collapsed),
                "row_count": len(product_rows),
                "schema_sha256": SCHEMA_SHA256,
                "writer_identity": writer_identity(),
                "parquet_sha256": parquet_sha,
                "parquet_path": str(parquet_path.relative_to(tree.root)),
                "raw_objects": [_lineage_source(item, index) for index, item in enumerate(raw_objects)],
                "collapsed_identical_source_rows": collapsed,
            }
            lineage_path, lineage_sha, lineage_reused = _publish_json(
                tree,
                lineage,
                parts=(".lineage", symbol, month),
                prefix=f"lineage-{symbol}-{month}",
                kind="lineage",
                hooks=hooks,
            )
            partitions.append(
                PublishedPartition(
                    symbol,
                    month,
                    len(product_rows),
                    physical,
                    len(collapsed),
                    parquet_path,
                    parquet_sha,
                    lineage_path,
                    lineage_sha,
                    parquet_reused and lineage_reused,
                )
            )
            physical_rows += physical
            collapsed_rows += len(collapsed)
        product_row_count = sum(part.row_count for part in partitions)
        source_bytes = sum(source.byte_size for source in ordered)
        verified = sum(source.validation_state == OUTCOME_CHECKSUM_VERIFIED for source in ordered)
        retained = sum(source.validation_state == OUTCOME_RETAINED for source in ordered)
        _require(physical_rows - collapsed_rows == product_row_count, "physical source rows minus collapsed identical rows do not equal product rows")
        _require(product_row_count <= ACCEPTED_PROJECTED_ROWS, "product rows exceed the accepted sizing ceiling")
        if enforce_full_corpus:
            _require(len(ordered) == ACCEPTED_SOURCE_COUNT, "full-corpus source count changed")
            _require(source_bytes == ACCEPTED_SOURCE_BYTES, "full-corpus source bytes changed")
            _require(len(partitions) == ACCEPTED_SOURCE_COUNT, "full-corpus partition count changed")
            _require(verified == ACCEPTED_CHECKSUM_VERIFIED_SOURCES, "full-corpus checksum-verified count changed")
            _require(retained == ACCEPTED_RETAINED_CREDIT_SOURCES, "full-corpus retained-credit count changed")
            _require(gap_authority["coverage_gap_rows"] == ACCEPTED_COVERAGE_GAP_ROWS, "full-corpus coverage-gap count changed")
            _require(gap_authority["typed_gap_symbol_count"] == ACCEPTED_TYPED_GAP_SYMBOLS, "full-corpus typed-gap symbol count changed")
            _require(tuple(gap_authority["coverage_gap_kinds"]) == ACCEPTED_COVERAGE_GAP_KINDS, "full-corpus coverage-gap kinds changed")
        source_hasher = hashlib.sha256()
        for source in ordered:
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
        normalizer_sha, _size = _digest_path(Path(__file__).resolve(strict=True))
        ranges = observed.finish()
        partition_facts = [
            {
                "native_symbol": part.native_symbol,
                "utc_month": part.utc_month,
                "row_count": part.row_count,
                "physical_row_count": part.physical_row_count,
                "collapsed_identical_row_count": part.collapsed_row_count,
                "parquet_sha256": part.parquet_sha256,
                "parquet_path": str(part.parquet_path.relative_to(tree.root)),
                "lineage_sha256": part.lineage_sha256,
                "lineage_path": str(part.lineage_path.relative_to(tree.root)),
            }
            for part in partitions
        ]
        completion = {
            "document_type": f"{PRODUCT}_product_completion",
            "schema_version": 1,
            "required_product": PRODUCT,
            "schema_sha256": SCHEMA_SHA256,
            "writer_identity": writer_identity(),
            "normalizer_source_sha256": normalizer_sha,
            "authorities_authenticated": enforce_full_corpus,
            "authority_sha256": {
                "generation0_seal_head": ACCEPTED_GENERATION0_SEAL_HEAD,
                "report": REPORT_SHA256,
                "sizing": SIZING_SHA256,
                "schema": SCHEMA_SHA256,
            },
            "generation0": {
                "binance_completions": ACCEPTED_GENERATION0_BINANCE_COMPLETIONS,
                "seal_head_receipt_sha256": ACCEPTED_GENERATION0_SEAL_HEAD,
                "selected_sources": len(ordered),
                "selected_source_bytes": source_bytes,
                "checksum_verified_sources": verified,
                "retained_credit_sources": retained,
            },
            "source_gap_authority": gap_authority,
            "sizing_ceiling": {
                "projected_rows": ACCEPTED_PROJECTED_ROWS,
                "projected_bytes": ACCEPTED_PROJECTED_BYTES,
                "largest_projected_partition_bytes": ACCEPTED_LARGEST_PARTITION_BYTES,
                "partition_count": ACCEPTED_SOURCE_COUNT,
            },
            "sources_sha256": source_hasher.hexdigest(),
            "partitions": partition_facts,
            "observed_ranges": ranges,
            "row_equation": {
                "physical_source_rows": physical_rows,
                "collapsed_identical_rows": collapsed_rows,
                "excluded_source_rows": 0,
                "inferred_events": 0,
                "rounded_events": 0,
                "conflicting_events": 0,
                "product_rows": product_row_count,
            },
        }
        expected = hashlib.sha256(_canonical_json(completion)).hexdigest()
        tree.require_only_completion(f"{expected}.json")
        completion_path, completion_sha, completion_reused = _publish_json(
            tree,
            completion,
            parts=(".complete",),
            prefix="funding-completion",
            kind="completion",
            hooks=hooks,
        )
        _require(completion_sha == expected, "funding completion identity changed")
        tree.require_only_completion(f"{expected}.json")
        tree.verify_paths(
            [
                *(item.parquet_path for item in partitions),
                *(item.lineage_path for item in partitions),
                completion_path,
            ]
        )
        return FundingNormalizationResult(
            SCHEMA_SHA256,
            writer_identity(),
            tuple(partitions),
            completion_path,
            completion_sha,
            completion_reused,
            physical_rows,
            collapsed_rows,
            product_row_count,
        )
    finally:
        tree.close()


def normalize_funding_sources(
    sources: Iterable[RawFundingObject],
    output_root: Path,
    *,
    report: Mapping[str, Any] | None = None,
    sizing: Mapping[str, Any] | None = None,
    hooks: PublicationHooks = PublicationHooks(),
) -> FundingNormalizationResult:
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
) -> FundingNormalizationResult:
    """Publish the exact accepted realized-funding product from pinned authorities."""
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
