"""Concrete Gate-3 normalizer for Binance USD-M hourly kline products.

One authenticated generation-0 read produces two independent immutable products:
``binance_usdm_bar_1h`` and ``binance_usdm_trade_flow_1h``.  This is deliberately a
product adapter rather than a generic archive framework.
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
    OUTCOME_CHECKSUM_VERIFIED,
    OUTCOME_RETAINED,
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
    PRODUCT_BAR_1H,
    PRODUCT_TRADE_FLOW_1H,
    QUALITY_GAP_COLUMNS,
    SIZING_ROW_BATCH,
    convert_decimal,
    convert_integer,
    final_product_schema,
    native_identity,
    product_schema_identity,
    writer_identity,
)

BAR_PRODUCT = PRODUCT_BAR_1H
TRADE_FLOW_PRODUCT = PRODUCT_TRADE_FLOW_1H
PRODUCTS = (BAR_PRODUCT, TRADE_FLOW_PRODUCT)
FAMILIES = ("daily/klines", "monthly/klines")
KLINE_FIELDS = KNOWN_ARCHIVE_SCHEMAS["klines"]["headerless"]
BAR_SCHEMA = final_product_schema(BAR_PRODUCT)
TRADE_FLOW_SCHEMA = final_product_schema(TRADE_FLOW_PRODUCT)
SCHEMAS = {BAR_PRODUCT: BAR_SCHEMA, TRADE_FLOW_PRODUCT: TRADE_FLOW_SCHEMA}
SCHEMA_SHA256 = {product: product_schema_identity(product) for product in PRODUCTS}
QUALITY_GAP_SCHEMA = pa.schema([column.field() for column in QUALITY_GAP_COLUMNS])

EXPECTED_CADENCE_MS = 3_600_000
EXPECTED_CLOSE_OFFSET_MS = 3_599_999
MAX_COMPRESSED_OBJECT_BYTES = 64 * 2**20
MAX_DECOMPRESSED_MEMBER_BYTES = 128 * 2**20
MAX_ROWS_PER_OBJECT = 1_024
MAX_CSV_FIELD_BYTES = 1 * 2**20
RENAME_NOREPLACE = 1

ACCEPTED_GENERATION0_BINANCE_COMPLETIONS = 685_072
ACCEPTED_GENERATION0_SEAL_HEAD = "8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab"
ACCEPTED_DAILY_SOURCES = 13_710
ACCEPTED_MONTHLY_SOURCES = 21_932
ACCEPTED_SOURCE_COUNT = 35_642
ACCEPTED_SOURCE_BYTES = 661_676_054
ACCEPTED_PARTITIONS = 22_633
ACCEPTED_PRODUCT_ROWS = 16_033_509
ACCEPTED_GAP_ROWS = 114
ACCEPTED_MISSING_HOURS = 8_003

_HEX_RE = re.compile(r"[0-9a-f]{64}")
_DAILY_RE = re.compile(
    r"data/futures/um/daily/klines/(?P<symbol>[A-Z0-9_]+)/1h/"
    r"(?P=symbol)-1h-(?P<period>\d{4}-\d{2}-\d{2})\.zip"
)
_MONTHLY_RE = re.compile(
    r"data/futures/um/monthly/klines/(?P<symbol>[A-Z0-9_]+)/1h/"
    r"(?P=symbol)-1h-(?P<period>\d{4}-\d{2})\.zip"
)


class KlineNormalizationError(RuntimeError):
    """Fail-closed authority, typing, economic, or publication error."""


@dataclass(frozen=True, slots=True)
class RawKlineObject:
    source_key: str
    family: str
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
    parquet_path: Path
    parquet_sha256: str
    lineage_path: Path
    lineage_sha256: str
    reused: bool


@dataclass(frozen=True, slots=True)
class PublishedGapArtifact:
    product: str
    row_count: int
    missing_grid_points: int
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
    gap_artifact: PublishedGapArtifact
    completion_path: Path
    completion_sha256: str
    completion_reused: bool


@dataclass(frozen=True, slots=True)
class KlineNormalizationResult:
    bar: ProductResult
    trade_flow: ProductResult


@dataclass(frozen=True, slots=True)
class PublicationHooks:
    """Test-only interruption boundary; production callers leave it unset."""

    before_publish: Callable[[str, str, Path, Path], None] | None = None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise KlineNormalizationError(message)


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _digest_path(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def _identity_parts(key: str) -> tuple[str, str, str]:
    match = _DAILY_RE.fullmatch(key)
    family = "daily/klines"
    date_format = "%Y-%m-%d"
    if match is None:
        match = _MONTHLY_RE.fullmatch(key)
        family = "monthly/klines"
        date_format = "%Y-%m"
    _require(match is not None, "raw kline identity is not canonical hourly USD-M")
    assert match is not None
    period = match.group("period")
    try:
        parsed = datetime.strptime(period, date_format).strftime(date_format)
    except ValueError as exc:
        raise KlineNormalizationError("raw kline identity has an invalid economic period") from exc
    _require(parsed == period, "raw kline identity period is not canonical")
    return family, match.group("symbol"), period


def _require_no_symlink_components(path: Path, *, label: str) -> None:
    absolute = path.absolute()
    for component in reversed((absolute, *absolute.parents)):
        if not component.exists() and not component.is_symlink():
            continue
        try:
            facts = component.lstat()
        except OSError as exc:
            raise KlineNormalizationError(f"{label} cannot be inspected safely") from exc
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
            raise KlineNormalizationError("authority object is not reachable") from exc
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
        raise KlineNormalizationError(f"{label} cannot be opened no-follow") from exc
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise KlineNormalizationError(f"{label} is not a regular file")
    return descriptor


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


def _require_accepted_validation_state(state: object) -> None:
    _require(
        type(state) is str and state in (OUTCOME_CHECKSUM_VERIFIED, OUTCOME_RETAINED),
        "generation-0 kline completion validation state is not accepted",
    )


def _validate_plan_payload(identity: str, payload: object, listed_bytes: int) -> tuple[str, str, str]:
    _require(type(payload) is dict, "generation-0 kline plan payload is not an object")
    assert isinstance(payload, dict)
    family, symbol, period = _identity_parts(identity)
    _require(payload.get("key") == identity, "generation-0 kline plan key changed")
    _require(payload.get("family") == family, "generation-0 kline plan family changed")
    _require(payload.get("symbol") == symbol, "generation-0 kline plan symbol changed")
    _require(payload.get("economic_interval") == period, "generation-0 kline plan period changed")
    _require(payload.get("listed_bytes") == listed_bytes, "generation-0 kline plan byte size changed")
    _require(payload.get("sidecar_key") == f"{identity}.CHECKSUM", "generation-0 kline sidecar identity changed")
    return family, symbol, period


def load_generation0_kline_sources(state_path: Path, content_root: Path) -> tuple[RawKlineObject, ...]:
    """Authenticate and select the exact generation-0 hourly kline authority."""
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
            "SELECT p.identity,p.payload_json,c.content_sha256,c.content_path,c.listed_bytes,"
            "c.retrieved_at,c.validation_state,s.provider_checksum "
            "FROM plan_entry p JOIN completion c ON c.provider=p.provider AND c.identity=p.identity "
            "JOIN sidecar_fact s ON s.provider=p.provider AND s.identity=p.identity "
            "WHERE p.provider='binance_vision' ORDER BY p.identity"
        )
        accepted: list[RawKlineObject] = []
        family_counts = {family: 0 for family in FAMILIES}
        source_bytes = 0
        try:
            for identity, payload_json, content_sha, content_path, listed, retrieved, state, provider_sha in cursor:
                try:
                    envelope = json.loads(str(payload_json))
                except json.JSONDecodeError as exc:
                    raise KlineNormalizationError("generation-0 plan payload is invalid JSON") from exc
                payload = envelope.get("payload") if type(envelope) is dict else None
                if type(payload) is not dict or payload.get("family") not in FAMILIES:
                    continue
                size = int(listed)
                family, symbol, period = _validate_plan_payload(str(identity), payload, size)
                digest = str(content_sha)
                _require(_HEX_RE.fullmatch(digest) is not None, "generation-0 content digest is invalid")
                _require(str(provider_sha) == digest, "generation-0 provider/content checksum conflict")
                _require_accepted_validation_state(state)
                expected = content_root / digest[:2] / digest
                _require(Path(str(content_path)) == expected, "generation-0 content path is not its content address")
                path = _safe_authority_file(content_root, PurePosixPath(digest[:2], digest))
                accepted.append(
                    RawKlineObject(
                        source_key=str(identity), family=family, native_symbol=symbol,
                        economic_period=period, path=path, source_sha256=digest,
                        byte_size=size, validation_state=str(state), retrieval_time=str(retrieved),
                    )
                )
                family_counts[family] += 1
                source_bytes += size
        finally:
            cursor.close()
        _require(family_counts["daily/klines"] == ACCEPTED_DAILY_SOURCES, "generation-0 daily kline count changed")
        _require(family_counts["monthly/klines"] == ACCEPTED_MONTHLY_SOURCES, "generation-0 monthly kline count changed")
        _require(len(accepted) == ACCEPTED_SOURCE_COUNT, "generation-0 selected kline count changed")
        _require(source_bytes == ACCEPTED_SOURCE_BYTES, "generation-0 selected kline bytes changed")
        connection.execute("ROLLBACK")
        borrowed.conn = None
        return tuple(accepted)
    except sqlite3.Error as exc:
        raise KlineNormalizationError("generation-0 authority cannot be read safely") from exc
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


def _safe_component(value: str) -> str:
    _require(bool(value) and value not in {".", ".."} and "/" not in value and "\\" not in value, "output child name is unsafe")
    return value


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _hash_fd(descriptor: int) -> tuple[str, int]:
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


def _read_fd(descriptor: int) -> bytes:
    position = os.lseek(descriptor, 0, os.SEEK_CUR)
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    try:
        while block := os.read(descriptor, 1024 * 1024):
            chunks.append(block)
    finally:
        os.lseek(descriptor, position, os.SEEK_SET)
    return b"".join(chunks)


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
        raise KlineNormalizationError("atomic no-replace rename is unavailable") from exc
    renameat2.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    renameat2.restype = ctypes.c_int
    if renameat2(old_dir, os.fsencode(old_name), new_dir, os.fsencode(new_name), RENAME_NOREPLACE):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), new_name)


class _OutputTree:
    def __init__(self, root: Path) -> None:
        _require_no_symlink_components(root, label="output root")
        if not root.exists():
            root.mkdir(mode=0o700)
            _fsync_directory(root.parent)
        self.root = root.resolve(strict=True)
        self.root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        _require(stat.S_ISDIR(os.fstat(self.root_fd).st_mode), "output root is not a directory")
        try:
            fcntl.flock(self.root_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self.root_fd)
            raise KlineNormalizationError("another normalizer holds the output root") from exc
        self.root_facts = os.fstat(self.root_fd)
        stage = self.directory((".staging",), create=True)
        os.close(stage)

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
                    raise KlineNormalizationError("output child directory is unsafe") from exc
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
        _require(stat.S_ISREG(os.fstat(descriptor).st_mode), "output staging leaf is not regular")
        return name, descriptor

    def publish(
        self, stage_name: str, stage_fd: int, parts: Sequence[str], name: str, *,
        product: str, kind: str, hooks: PublicationHooks,
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
                    raise KlineNormalizationError("content-addressed publication failed") from exc
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
            _require(stat.S_ISREG(os.fstat(final_fd).st_mode), "published output is not regular")
            return reused, final_fd, path
        finally:
            os.close(destination)
            os.close(staging)

    def require_only_completion(self, name: str) -> None:
        directory = self.directory((".complete",), create=True)
        try:
            _require(not [entry for entry in os.listdir(directory) if entry != name], "a different product completion already exists")
        finally:
            os.close(directory)

    def verify_paths(self, paths: Iterable[Path]) -> None:
        current = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            facts = os.fstat(current)
            _require((facts.st_dev, facts.st_ino) == (self.root_facts.st_dev, self.root_facts.st_ino), "held output root was replaced")
        finally:
            os.close(current)
        for path in paths:
            _require(path.is_relative_to(self.root), "returned output path escapes held root")
            relative = path.relative_to(self.root)
            directory = self.directory(relative.parts[:-1], create=False)
            try:
                descriptor = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
                _require(stat.S_ISREG(os.fstat(descriptor).st_mode), "published output is not regular")
                os.close(descriptor)
            finally:
                os.close(directory)


def _safe_zip_member(archive: zipfile.ZipFile, source: RawKlineObject) -> zipfile.ZipInfo:
    members = archive.infolist()
    _require(len(members) == 1, "kline ZIP must contain exactly one member")
    member = members[0]
    name = member.filename
    parts = PurePosixPath(name.replace("\\", "/"))
    _require(bool(name) and not parts.is_absolute() and ".." not in parts.parts, "kline ZIP member path is unsafe")
    _require(len(parts.parts) == 1 and name.endswith(".csv"), "kline ZIP member is not one root CSV")
    _require(stat.S_IFMT(member.external_attr >> 16) in {0, stat.S_IFREG}, "kline ZIP member is not regular")
    _require(not (member.flag_bits & 0x1), "encrypted kline ZIP is unsupported")
    _require(member.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}, "kline ZIP compression is unsupported")
    _require(0 < member.file_size <= MAX_DECOMPRESSED_MEMBER_BYTES, "kline ZIP member exceeds parser bound")
    _require(member.compress_size <= MAX_COMPRESSED_OBJECT_BYTES, "kline compressed member exceeds parser bound")
    _require(name == source.source_key.rsplit("/", 1)[-1][:-4] + ".csv", "kline ZIP member name conflicts with source identity")
    return member


def _integer(token: str, source: RawKlineObject, column: str, ordinal: int) -> int:
    try:
        return convert_integer(token, key=source.source_key, output=BAR_PRODUCT, column=column, row=ordinal)
    except Exception as exc:
        raise KlineNormalizationError(f"kline {column} is not an exact integer") from exc


def _decimal(token: str, source: RawKlineObject, column: str, ordinal: int) -> Decimal:
    try:
        return convert_decimal(token, key=source.source_key, output=BAR_PRODUCT, column=column, row=ordinal)
    except Exception as exc:
        raise KlineNormalizationError(f"kline {column} is not an exact decimal") from exc


def _unscaled(value: Decimal) -> int:
    parts = value.as_tuple()
    coefficient = int("".join(str(digit) for digit in parts.digits) or "0")
    _require(parts.exponent >= -DECIMAL_SCALE, "decimal exceeds pinned scale")
    coefficient *= 10 ** (parts.exponent + DECIMAL_SCALE)
    return -coefficient if parts.sign else coefficient


def _scaled(value: int) -> Decimal:
    digits = tuple(int(character) for character in str(abs(value))) if value else (0,)
    _require(len(digits) <= 38, "derived flow decimal overflows pinned precision")
    return Decimal((1 if value < 0 else 0, digits, -DECIMAL_SCALE))


def _period_contains(source: RawKlineObject, open_time: int) -> bool:
    moment = datetime.fromtimestamp(open_time // 1000, tz=UTC)
    if source.family == "daily/klines":
        return moment.strftime("%Y-%m-%d") == source.economic_period
    return moment.strftime("%Y-%m") == source.economic_period


def _parse_kline_row(source: RawKlineObject, ordinal: int, row: Sequence[str]) -> dict[str, Any]:
    fields = dict(zip(KLINE_FIELDS, row, strict=True))
    open_time = _integer(fields["open_time"], source, "open_time", ordinal)
    close_time = _integer(fields["close_time"], source, "close_time", ordinal)
    _require(open_time >= 0 and open_time % EXPECTED_CADENCE_MS == 0, "kline open_time is not an hourly epoch millisecond")
    _require(close_time == open_time + EXPECTED_CLOSE_OFFSET_MS, "kline close_time does not close its hourly interval")
    _require(_period_contains(source, open_time), "kline row lies outside its source economic period")
    values = {name: _decimal(fields[name], source, name, ordinal) for name in (
        "open", "high", "low", "close", "volume", "quote_volume",
        "taker_buy_volume", "taker_buy_quote_volume",
    )}
    trade_count = _integer(fields["count"], source, "count", ordinal)
    reserved = _integer(fields["ignore"], source, "ignore", ordinal)
    _require(all(values[name] > 0 for name in ("open", "high", "low", "close")), "kline prices must be positive")
    _require(all(values[name] >= 0 for name in ("volume", "quote_volume", "taker_buy_volume", "taker_buy_quote_volume")), "kline volumes cannot be negative")
    _require(trade_count >= 0 and reserved >= 0, "kline count and reserved integer cannot be negative")
    _require(values["high"] >= max(values["open"], values["close"], values["low"]), "kline high violates OHLC bounds")
    _require(values["low"] <= min(values["open"], values["close"], values["high"]), "kline low violates OHLC bounds")
    _require(values["taker_buy_volume"] <= values["volume"], "taker-buy base volume exceeds total")
    _require(values["taker_buy_quote_volume"] <= values["quote_volume"], "taker-buy quote volume exceeds total")
    return {
        "source_row_ordinal": ordinal, "open_time": open_time, "close_time": close_time,
        **values, "trade_count": trade_count, "source_reserved": reserved,
    }


def _authenticated_source_bytes(source: RawKlineObject) -> bytes:
    try:
        descriptor = os.open(source.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        raise KlineNormalizationError("raw source cannot be opened no-follow") from exc
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


def _iter_kline_rows(source: RawKlineObject) -> Iterator[dict[str, Any]]:
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
                    _require(decompressed <= MAX_DECOMPRESSED_MEMBER_BYTES, "kline CSV exceeds decompressed parser bound")
                    _require(all(len(cell.encode()) <= MAX_CSV_FIELD_BYTES for cell in row), "kline CSV field exceeds parser bound")
                    if first:
                        first = False
                        if tuple(row) == KLINE_FIELDS:
                            continue
                    _require(bool(row), "kline CSV contains an empty row")
                    _require(len(row) == len(KLINE_FIELDS), "kline CSV row width is invalid")
                    _require(ordinal < MAX_ROWS_PER_OBJECT, "kline CSV exceeds row parser bound")
                    yield _parse_kline_row(source, ordinal, row)
                    ordinal += 1
                _require(ordinal > 0, "kline CSV contains no data rows")
    except (OSError, UnicodeError, csv.Error, zipfile.BadZipFile, RuntimeError) as exc:
        if isinstance(exc, KlineNormalizationError):
            raise
        raise KlineNormalizationError("kline ZIP/CSV is invalid") from exc


def _bar_row(record: Mapping[str, Any], raw_ref: int, symbol: str) -> dict[str, Any]:
    return {
        "raw_object_ref": raw_ref, "source_row_ordinal": record["source_row_ordinal"],
        "venue_symbol": symbol, "open_time": record["open_time"], "close_time": record["close_time"],
        "open": record["open"], "high": record["high"], "low": record["low"], "close": record["close"],
        "volume": record["volume"], "quote_volume": record["quote_volume"],
        "trade_count": record["trade_count"], "source_reserved": record["source_reserved"],
        **native_identity(symbol),
    }


def _flow_row(record: Mapping[str, Any], raw_ref: int, symbol: str) -> dict[str, Any]:
    volume = record["volume"]
    quote = record["quote_volume"]
    buy = record["taker_buy_volume"]
    buy_quote = record["taker_buy_quote_volume"]
    assert isinstance(volume, Decimal) and isinstance(quote, Decimal)
    assert isinstance(buy, Decimal) and isinstance(buy_quote, Decimal)
    sell = _unscaled(volume) - _unscaled(buy)
    sell_quote = _unscaled(quote) - _unscaled(buy_quote)
    return {
        "raw_object_ref": raw_ref, "source_row_ordinal": record["source_row_ordinal"],
        "venue_symbol": symbol, "open_time": record["open_time"], "close_time": record["close_time"],
        "volume": volume, "quote_volume": quote, "taker_buy_volume": buy,
        "taker_buy_quote_volume": buy_quote, "trade_count": record["trade_count"],
        **native_identity(symbol), "taker_sell_volume": _scaled(sell),
        "taker_sell_quote_volume": _scaled(sell_quote),
        "volume_imbalance": _scaled(_unscaled(buy) - sell),
        "quote_volume_imbalance": _scaled(_unscaled(buy_quote) - sell_quote),
    }


def _lineage_source(source: RawKlineObject, raw_ref: int) -> dict[str, Any]:
    return {
        "raw_object_ref": raw_ref, "source_key": source.source_key,
        "source_sha256": source.source_sha256, "checksum_authority": source.checksum_authority,
        "byte_size": source.byte_size, "retrieval_time": source.retrieval_time,
        "source_available_at": source.source_available_at,
        "source_availability_state": "unknown_not_imputed" if source.source_available_at is None else "known",
        "validation_state": source.validation_state,
    }


def _quality_gap_row(product: str, symbol: str, start: int, end: int, reason: str) -> dict[str, Any]:
    _require(start <= end and (end - start) % EXPECTED_CADENCE_MS == 0, "quality gap interval is invalid")
    start_month = datetime.fromtimestamp(start // 1000, tz=UTC).strftime("%Y-%m")
    end_month = datetime.fromtimestamp(end // 1000, tz=UTC).strftime("%Y-%m")
    _require(start_month == end_month, "quality gap row crosses a UTC month")
    return {
        **native_identity(symbol), "required_product": product, "utc_month": start_month,
        "missing_run_start_ms": start, "missing_run_end_ms": end,
        "expected_grid_count": (end - start) // EXPECTED_CADENCE_MS + 1,
        "gap_kind": "missing_hour_run", "reason": reason,
    }


def _split_gap(product: str, symbol: str, start: int, end: int, reason: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = start
    while cursor <= end:
        moment = datetime.fromtimestamp(cursor // 1000, tz=UTC)
        boundary = (datetime(moment.year + 1, 1, 1, tzinfo=UTC) if moment.month == 12 else datetime(moment.year, moment.month + 1, 1, tzinfo=UTC))
        boundary_ms = int(boundary.timestamp()) * 1000
        segment_end = min(end, boundary_ms - EXPECTED_CADENCE_MS)
        rows.append(_quality_gap_row(product, symbol, cursor, segment_end, reason))
        cursor = segment_end + EXPECTED_CADENCE_MS
    return rows


def _verify_parquet_fd(descriptor: int, rows: int, digest: str, schema: pa.Schema) -> None:
    actual, _size = _hash_fd(descriptor)
    _require(actual == digest, "published Parquet digest changed")
    try:
        parquet = pq.ParquetFile(f"/proc/self/fd/{descriptor}")
    except (OSError, pa.ArrowInvalid) as exc:
        raise KlineNormalizationError("published Parquet is unreadable") from exc
    _require(parquet.schema_arrow == schema, "published Parquet schema changed")
    _require(parquet.metadata.num_rows == rows, "published Parquet row count changed")


def _publish_parquet(tree: _OutputTree, table: pa.Table, *, product: str, parts: Sequence[str], prefix: str, kind: str, hooks: PublicationHooks) -> tuple[Path, str, bool]:
    stage_name, stage_fd = tree.stage(prefix)
    final_fd: int | None = None
    try:
        pq.write_table(table, f"/proc/self/fd/{stage_fd}", compression=PARQUET_COMPRESSION,
                       compression_level=PARQUET_COMPRESSION_LEVEL, version=PARQUET_VERSION,
                       write_statistics=False, store_schema=True, row_group_size=SIZING_ROW_BATCH)
        os.fsync(stage_fd)
        digest, _size = _hash_fd(stage_fd)
        _verify_parquet_fd(stage_fd, table.num_rows, digest, table.schema)
        reused, final_fd, path = tree.publish(stage_name, stage_fd, parts, f"{digest}.parquet", product=product, kind=kind, hooks=hooks)
        _verify_parquet_fd(final_fd, table.num_rows, digest, table.schema)
        return path, digest, reused
    finally:
        if final_fd is not None:
            os.close(final_fd)
        os.close(stage_fd)


def _publish_json(tree: _OutputTree, document: Mapping[str, Any], *, product: str, parts: Sequence[str], prefix: str, kind: str, hooks: PublicationHooks) -> tuple[Path, str, bool]:
    body = _canonical_json(document)
    digest = hashlib.sha256(body).hexdigest()
    stage_name, stage_fd = tree.stage(prefix)
    final_fd: int | None = None
    try:
        _rewrite_fd(stage_fd, body)
        reused, final_fd, path = tree.publish(stage_name, stage_fd, parts, f"{digest}.json", product=product, kind=kind, hooks=hooks)
        actual, _size = _hash_fd(final_fd)
        _require(actual == digest and _read_fd(final_fd) == body, "published JSON changed")
        return path, digest, reused
    finally:
        if final_fd is not None:
            os.close(final_fd)
        os.close(stage_fd)


def _source_sort_key(source: RawKlineObject) -> tuple[str, str, int, str]:
    return (source.native_symbol, source.economic_period[:7], 0 if source.family == "monthly/klines" else 1, source.source_key)


def _validate_source_descriptor(source: RawKlineObject) -> None:
    family, symbol, period = _identity_parts(source.source_key)
    _require((source.family, source.native_symbol, source.economic_period) == (family, symbol, period), "raw source descriptor conflicts with its identity")
    _require(_HEX_RE.fullmatch(source.source_sha256) is not None, "raw source digest is invalid")
    _require(type(source.byte_size) is int and 0 < source.byte_size <= MAX_COMPRESSED_OBJECT_BYTES, "raw source compressed size is invalid")
    _require_accepted_validation_state(source.validation_state)
    _require_no_symlink_components(source.path, label="raw source path")
    _require(source.path.is_file() and not source.path.is_symlink(), "raw source path is unsafe")


def _preflight_sources(sources: Iterable[RawKlineObject]) -> tuple[RawKlineObject, ...]:
    ordered = tuple(sorted(sources, key=_source_sort_key))
    identities: set[str] = set()
    coverage: dict[tuple[str, str], set[str]] = {}
    for source in ordered:
        _require(source.source_key not in identities, "raw authority repeats a kline identity")
        identities.add(source.source_key)
        _validate_source_descriptor(source)
        coverage.setdefault((source.native_symbol, source.economic_period[:7]), set()).add(source.family)
    _require(not [key for key, families in coverage.items() if len(families) > 1], "daily and monthly kline authority overlaps an economic month")
    return ordered


def _normalize_sources(
    sources: Iterable[RawKlineObject], bar_tree: _OutputTree, flow_tree: _OutputTree, *,
    hooks: PublicationHooks, enforce_full_corpus: bool,
) -> KlineNormalizationResult:
    ordered = _preflight_sources(sources)
    groups: dict[tuple[str, str], list[RawKlineObject]] = {}
    for source in ordered:
        groups.setdefault((source.native_symbol, source.economic_period[:7]), []).append(source)

    trees = {BAR_PRODUCT: bar_tree, TRADE_FLOW_PRODUCT: flow_tree}
    partitions: dict[str, list[PublishedPartition]] = {product: [] for product in PRODUCTS}
    gaps: dict[str, list[dict[str, Any]]] = {product: [] for product in PRODUCTS}
    physical_rows = 0
    previous: dict[str, tuple[int, str] | None] = {}
    for (symbol, month), month_sources in sorted(groups.items()):
        raw_objects = sorted(month_sources, key=lambda item: item.source_key)
        parsed: list[tuple[int, str, dict[str, Any]]] = []
        for raw_ref, source in enumerate(raw_objects):
            for record in _iter_kline_rows(source):
                parsed.append((raw_ref, source.source_key, record))
                physical_rows += 1
        parsed.sort(key=lambda item: int(item[2]["open_time"]))
        bar_rows: list[dict[str, Any]] = []
        flow_rows: list[dict[str, Any]] = []
        prior = previous.get(symbol)
        for raw_ref, source_key, record in parsed:
            moment = int(record["open_time"])
            _require(datetime.fromtimestamp(moment // 1000, tz=UTC).strftime("%Y-%m") == month, "kline row UTC month conflicts with partition")
            if prior is not None:
                _require(moment != prior[0], "duplicate kline open timestamp is forbidden")
                _require(moment > prior[0], "kline open timestamps are not strictly increasing")
                if moment - prior[0] > EXPECTED_CADENCE_MS:
                    reason = "within_object_missing_hour" if source_key == prior[1] else "between_object_missing_hour"
                    for product in PRODUCTS:
                        gaps[product].extend(_split_gap(product, symbol, prior[0] + EXPECTED_CADENCE_MS, moment - EXPECTED_CADENCE_MS, reason))
            bar_rows.append(_bar_row(record, raw_ref, symbol))
            flow_rows.append(_flow_row(record, raw_ref, symbol))
            prior = (moment, source_key)
        _require(bool(bar_rows), "kline partition has no rows")
        previous[symbol] = prior
        product_rows = {BAR_PRODUCT: bar_rows, TRADE_FLOW_PRODUCT: flow_rows}
        for product in PRODUCTS:
            tree = trees[product]
            table = pa.Table.from_pylist(product_rows[product], schema=SCHEMAS[product])
            parquet_path, parquet_sha, parquet_reused = _publish_parquet(
                tree, table, product=product, parts=(".partitions", symbol, month),
                prefix=f"partition-{symbol}-{month}", kind="partition", hooks=hooks,
            )
            lineage = {
                "document_type": f"{product}_partition_lineage", "schema_version": 1,
                "required_product": product, "native_symbol": symbol, "utc_month": month,
                "row_count": len(product_rows[product]), "schema_sha256": SCHEMA_SHA256[product],
                "writer_identity": writer_identity(), "parquet_sha256": parquet_sha,
                "parquet_name": parquet_path.name,
                "raw_objects": [_lineage_source(item, index) for index, item in enumerate(raw_objects)],
            }
            lineage_path, lineage_sha, lineage_reused = _publish_json(
                tree, lineage, product=product, parts=(".lineage", symbol, month),
                prefix=f"lineage-{symbol}-{month}", kind="lineage", hooks=hooks,
            )
            partitions[product].append(PublishedPartition(
                product, symbol, month, len(product_rows[product]), parquet_path,
                parquet_sha, lineage_path, lineage_sha, parquet_reused and lineage_reused,
            ))

    source_bytes = sum(source.byte_size for source in ordered)
    source_hasher = hashlib.sha256()
    for source in ordered:
        source_hasher.update(_canonical_json({
            "source_key": source.source_key, "source_sha256": source.source_sha256,
            "byte_size": source.byte_size, "validation_state": source.validation_state,
        }))
    sources_sha = source_hasher.hexdigest()
    normalizer_sha, _size = _digest_path(Path(__file__).resolve(strict=True))
    results: dict[str, ProductResult] = {}
    for product in PRODUCTS:
        gap_rows = sorted(gaps[product], key=lambda row: (str(row["native_symbol"]), int(row["missing_run_start_ms"])))
        missing_points = sum(int(row["expected_grid_count"]) for row in gap_rows)
        gap_table = pa.Table.from_pylist(gap_rows, schema=QUALITY_GAP_SCHEMA)
        gap_path, gap_sha, gap_reused = _publish_parquet(
            trees[product], gap_table, product=product, parts=(".quality-gaps",),
            prefix="quality-gaps", kind="quality_gap", hooks=hooks,
        )
        gap_lineage = {
            "document_type": f"{product}_quality_gap_lineage", "schema_version": 1,
            "required_product": product, "row_count": len(gap_rows),
            "missing_grid_points": missing_points, "quality_gap_parquet_sha256": gap_sha,
            "quality_gap_schema": [{"name": field.name, "type": str(field.type), "nullable": field.nullable} for field in QUALITY_GAP_SCHEMA],
        }
        gap_lineage_path, gap_lineage_sha, gap_lineage_reused = _publish_json(
            trees[product], gap_lineage, product=product, parts=(".quality-gap-lineage",),
            prefix="quality-gap-lineage", kind="quality_gap_lineage", hooks=hooks,
        )
        product_rows = sum(part.row_count for part in partitions[product])
        if enforce_full_corpus:
            _require(len(ordered) == ACCEPTED_SOURCE_COUNT and source_bytes == ACCEPTED_SOURCE_BYTES, "full-corpus source totals changed")
            _require(len(partitions[product]) == ACCEPTED_PARTITIONS, "full-corpus partition total changed")
            _require(physical_rows == ACCEPTED_PRODUCT_ROWS and product_rows == ACCEPTED_PRODUCT_ROWS, "full-corpus row totals changed")
            _require(len(gap_rows) == ACCEPTED_GAP_ROWS and missing_points == ACCEPTED_MISSING_HOURS, "full-corpus gap totals changed")
        _require(product_rows == physical_rows, "kline physical/product row equation failed")
        partition_facts = [{
            "native_symbol": part.native_symbol, "utc_month": part.utc_month,
            "row_count": part.row_count, "parquet_sha256": part.parquet_sha256,
            "parquet_path": str(part.parquet_path.relative_to(trees[product].root)),
            "lineage_sha256": part.lineage_sha256,
            "lineage_path": str(part.lineage_path.relative_to(trees[product].root)),
        } for part in partitions[product]]
        completion = {
            "document_type": f"{product}_product_completion", "schema_version": 1,
            "required_product": product, "schema_sha256": SCHEMA_SHA256[product],
            "writer_identity": writer_identity(), "normalizer_source_sha256": normalizer_sha,
            "authorities_authenticated": enforce_full_corpus, "source_count": len(ordered),
            "source_bytes": source_bytes, "sources_sha256": sources_sha,
            "partitions": partition_facts,
            "quality_gap_artifact": {
                "parquet_sha256": gap_sha, "parquet_path": str(gap_path.relative_to(trees[product].root)),
                "lineage_sha256": gap_lineage_sha, "lineage_path": str(gap_lineage_path.relative_to(trees[product].root)),
                "row_count": len(gap_rows), "missing_grid_points": missing_points,
            },
            "row_equation": {
                "physical_rows": physical_rows, "duplicate_rows": 0, "overlap_rows": 0,
                "collapsed_rows": 0, "excluded_rows": 0, "product_rows": product_rows,
            },
        }
        expected = hashlib.sha256(_canonical_json(completion)).hexdigest()
        trees[product].require_only_completion(f"{expected}.json")
        completion_path, completion_sha, completion_reused = _publish_json(
            trees[product], completion, product=product, parts=(".complete",),
            prefix="product-completion", kind="completion", hooks=hooks,
        )
        _require(completion_sha == expected, "product completion identity changed")
        trees[product].require_only_completion(f"{expected}.json")
        trees[product].verify_paths([
            *(part.parquet_path for part in partitions[product]),
            *(part.lineage_path for part in partitions[product]),
            gap_path, gap_lineage_path, completion_path,
        ])
        gap_artifact = PublishedGapArtifact(
            product, len(gap_rows), missing_points, gap_path, gap_sha,
            gap_lineage_path, gap_lineage_sha, gap_reused and gap_lineage_reused,
        )
        results[product] = ProductResult(
            product, SCHEMA_SHA256[product], tuple(partitions[product]), gap_artifact,
            completion_path, completion_sha, completion_reused,
        )
    return KlineNormalizationResult(results[BAR_PRODUCT], results[TRADE_FLOW_PRODUCT])


def normalize_kline_sources(
    sources: Iterable[RawKlineObject], bar_output_root: Path, trade_flow_output_root: Path, *,
    hooks: PublicationHooks = PublicationHooks(),
) -> KlineNormalizationResult:
    """Normalize bounded authenticated-shaped sources (primarily for focused tests)."""
    return _normalize_with_roots(sources, bar_output_root, trade_flow_output_root, hooks=hooks, enforce_full_corpus=False)


def _normalize_with_roots(
    sources: Iterable[RawKlineObject], bar_output_root: Path, trade_flow_output_root: Path, *,
    hooks: PublicationHooks, enforce_full_corpus: bool,
) -> KlineNormalizationResult:
    _require(bar_output_root.name.startswith(".") and trade_flow_output_root.name.startswith("."), "both product output roots must be hidden")
    _require(bar_output_root.absolute() != trade_flow_output_root.absolute(), "product output roots must be distinct")
    bar_tree = _OutputTree(bar_output_root)
    flow_tree: _OutputTree | None = None
    try:
        flow_tree = _OutputTree(trade_flow_output_root)
        _require((bar_tree.root_facts.st_dev, bar_tree.root_facts.st_ino) != (flow_tree.root_facts.st_dev, flow_tree.root_facts.st_ino), "product output roots resolve to the same directory")
        return _normalize_sources(sources, bar_tree, flow_tree, hooks=hooks, enforce_full_corpus=enforce_full_corpus)
    finally:
        if flow_tree is not None:
            flow_tree.close()
        bar_tree.close()


def normalize_from_generation0(
    *, generation0_state: Path, generation0_content_root: Path,
    bar_output_root: Path, trade_flow_output_root: Path,
    hooks: PublicationHooks = PublicationHooks(),
) -> KlineNormalizationResult:
    sources = load_generation0_kline_sources(generation0_state, generation0_content_root)
    return _normalize_with_roots(
        sources, bar_output_root, trade_flow_output_root,
        hooks=hooks, enforce_full_corpus=True,
    )
