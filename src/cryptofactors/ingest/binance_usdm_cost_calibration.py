"""Normalize the complete frozen Binance USD-M cost-calibration manifest.

The product retains every book row, publishes the absence of historical fee authority,
and carries the two ADR-0026 scenario rows as configuration rather than market history.
"""

from __future__ import annotations

import csv
import ctypes
import errno
import fcntl
import gzip
import hashlib
import io
import json
import os
import re
import sqlite3
import stat
import uuid
import zipfile
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
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
    SIDECAR_CEILING_BYTES,
    content_path_for,
    parse_sidecar,
    register_domain_functions,
)
from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    COST_MANIFEST_DIGEST_VERSION,
    KNOWN_ARCHIVE_SCHEMAS,
    cost_manifest_digest,
)
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    ACCEPTED_FEE_AUTHORITY_GAPS,
    COST_COMPONENTS,
    FEE_AUTHORITY_CLASS,
    FEE_GAP_KIND,
    FEE_POLICY_KNOWN_AT,
    PARQUET_COMPRESSION,
    PARQUET_COMPRESSION_LEVEL,
    PARQUET_VERSION,
    PRODUCT_COST_CALIBRATION,
    PRODUCT_MEMBERSHIP,
    SIZING_ROW_BATCH,
    cost_component_columns,
    convert_decimal,
    convert_integer,
    convert_timestamp_text,
    fee_scenario_rows,
    final_product_schema,
    partition_schema_identity,
    product_schema_contract,
    product_schema_identity,
    writer_identity,
)

PRODUCT = PRODUCT_COST_CALIBRATION
FAMILY_TICKER = "daily/bookTicker"
FAMILY_DEPTH = "daily/bookDepth"
COMPONENT_TICKER = "retained_book_ticker"
COMPONENT_DEPTH = "retained_book_depth"
COMPONENT_OFFICIAL_FEE = "official_fee_schedule"
COMPONENT_FEE_GAP = "fee_authority_gap"
COMPONENT_SCENARIO = "scenario_policy"
FAMILIES = (FAMILY_TICKER, FAMILY_DEPTH)
COMPONENT_FOR_FAMILY = {FAMILY_TICKER: COMPONENT_TICKER, FAMILY_DEPTH: COMPONENT_DEPTH}

REPORT_SHA256 = "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
SIZING_SHA256 = "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589"
COST_MANIFEST_SHA256 = "04842ff6b9b58280b3ec2ea2644b3d44769be62d460bef785262cd4dd65cac57"
GENERATION0_SEAL = "8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab"
V3_MANIFEST_SHA256 = "4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d"
MEMBERSHIP_COMPLETION_SHA256 = "01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3"

ACCEPTED_COST_OBJECTS = 3_144
ACCEPTED_COST_BYTES = 12_522_974_218
ACCEPTED_TICKER_OBJECTS = 909
ACCEPTED_DEPTH_OBJECTS = 2_235
ACCEPTED_GENERATION0_OBJECTS = 2_790
ACCEPTED_RECOVERY_OBJECTS = 354
ACCEPTED_RECOVERY_BYTES = 8_661_432_243
ACCEPTED_GENERATION0_BINANCE_COMPLETIONS = 685_072
ACCEPTED_V3_ROWS = 51_275
ACCEPTED_V3_BYTES = 9_207_379_061
ACCEPTED_V3_METRICS_ROWS = 50_921
ACCEPTED_SOURCE_GAPS = 494
ACCEPTED_MEMBERSHIP_IDENTITIES = 771
PROJECTED_PARTITIONS = 3_865
NORMALIZED_ALLOCATION_BYTES = 37_957_477_079
COMPONENT_LIMITS: Mapping[str, Mapping[str, int]] = {
    COMPONENT_TICKER: {
        "rows": 745_543_507,
        "bytes": 33_300_608_759,
        "largest_partition_bytes": 644_623_616,
        "partitions": 866,
    },
    COMPONENT_DEPTH: {
        "rows": 213_335_188,
        "bytes": 4_654_218_130,
        "largest_partition_bytes": 6_282_405,
        "partitions": 2_226,
    },
    COMPONENT_OFFICIAL_FEE: {
        "rows": 0,
        "bytes": 3_551,
        "largest_partition_bytes": 3_551,
        "partitions": 1,
    },
    COMPONENT_FEE_GAP: {
        "rows": 771,
        "bytes": 2_642_988,
        "largest_partition_bytes": 3_428,
        "partitions": 771,
    },
    COMPONENT_SCENARIO: {
        "rows": 2,
        "bytes": 3_651,
        "largest_partition_bytes": 3_651,
        "partitions": 1,
    },
}

MAX_REPORT_BYTES = 16 * 2**20
MAX_SIZING_BYTES = 64 * 2**20
MAX_COMPRESSED_OBJECT_BYTES = 512 * 2**20
MAX_MEMBER_BYTES = 2 * 2**30
MAX_ROWS_PER_OBJECT = 30_000_000
MAX_FIELD_BYTES = 1 * 2**20
RENAME_NOREPLACE = 1
_HEX = re.compile(r"[0-9a-f]{64}")
_KEY = re.compile(
    r"data/futures/um/daily/(?P<kind>bookTicker|bookDepth)/"
    r"(?P<symbol>[^/]+)/(?P=symbol)-(?P=kind)-(?P<day>\d{4}-\d{2}-\d{2})\.zip"
)

SCHEMAS = {
    component: pa.schema([column.field() for column in cost_component_columns(component)])
    for component in COST_COMPONENTS
}
SCHEMA_SHA256 = product_schema_identity(PRODUCT)
SCHEMA_IDENTITIES = {
    component: partition_schema_identity(PRODUCT, component)
    for component in COST_COMPONENTS
}


class CostCalibrationError(RuntimeError):
    """Fail-closed authority, parsing, typing, or publication error."""


@dataclass(frozen=True, slots=True)
class RawCostObject:
    source_key: str
    family: str
    native_symbol: str
    economic_day: str
    path: Path
    source_sha256: str
    byte_size: int
    etag: str
    authority: str
    checksum_authority: str
    retrieval_time: str | None = None
    source_available_at: int | None = None
    revision: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class MembershipIdentity:
    venue: str
    native_symbol: str
    canonical_instrument_id: str | None
    canonical_instrument_version_id: str | None
    reference_identity_state: str

    def row(self) -> dict[str, Any]:
        return {
            "venue": self.venue,
            "native_symbol": self.native_symbol,
            "canonical_instrument_id": self.canonical_instrument_id,
            "canonical_instrument_version_id": self.canonical_instrument_version_id,
            "reference_identity_state": self.reference_identity_state,
        }


@dataclass(frozen=True, slots=True)
class PublishedComponent:
    component: str
    native_symbol: str
    utc_month: str
    row_count: int
    parquet_path: Path
    parquet_sha256: str
    parquet_bytes: int
    lineage_path: Path
    lineage_sha256: str
    lineage_bytes: int
    source_ordinal_ranges: tuple[Mapping[str, Any], ...]
    reused: bool


@dataclass(frozen=True, slots=True)
class CostCalibrationResult:
    product: str
    schema_sha256: str
    components: tuple[PublishedComponent, ...]
    completion_path: Path
    completion_sha256: str
    completion_reused: bool
    source_objects: int
    source_rows: int


@dataclass(frozen=True, slots=True)
class PublicationHooks:
    before_publish: Callable[[str, Path, Path], None] | None = None
    observe_batch: Callable[[str, int], None] | None = None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CostCalibrationError(message)


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _is_digest(value: object) -> bool:
    return type(value) is str and _HEX.fullmatch(value) is not None


def _safe_component(value: str) -> str:
    _require(type(value) is str and bool(value) and value not in {".", ".."}, "unsafe path component")
    _require("/" not in value and "\\" not in value and "\x00" not in value, "unsafe path component")
    return value


def _identity(key: str) -> tuple[str, str, str]:
    match = _KEY.fullmatch(key)
    _require(match is not None, "cost source key is not canonical")
    assert match is not None
    family = f"daily/{match.group('kind')}"
    try:
        day = datetime.strptime(match.group("day"), "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise CostCalibrationError("cost source key date is invalid") from exc
    _require(day == match.group("day"), "cost source key date is not canonical")
    return family, match.group("symbol"), day


def _authority_child(root: Path, relative: str, label: str) -> Path:
    parts = PurePosixPath(relative)
    _require(
        bool(parts.parts)
        and not parts.is_absolute()
        and ".." not in parts.parts
        and all(part not in {"", "."} for part in parts.parts),
        f"{label} path is unsafe",
    )
    _no_symlinks(root, f"{label} root")
    path = root.joinpath(*parts.parts)
    _no_symlinks(path, label)
    return path


def _no_symlinks(path: Path, label: str) -> None:
    absolute = path.absolute()
    for item in reversed((absolute, *absolute.parents)):
        if not item.exists() and not item.is_symlink():
            continue
        try:
            facts = item.lstat()
        except OSError as exc:
            raise CostCalibrationError(f"{label} cannot be inspected") from exc
        _require(not stat.S_ISLNK(facts.st_mode), f"{label} contains a symlink")


def _hash_fd(fd: int) -> tuple[str, int]:
    position = os.lseek(fd, 0, os.SEEK_CUR)
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    size = 0
    try:
        while block := os.read(fd, 1024 * 1024):
            digest.update(block)
            size += len(block)
    finally:
        os.lseek(fd, position, os.SEEK_SET)
    return digest.hexdigest(), size


def _open_authenticated(path: Path, digest: str, size: int, maximum: int) -> int:
    _no_symlinks(path, "authority path")
    _require(_is_digest(digest) and 0 < size <= maximum, "authority descriptor is invalid")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        raise CostCalibrationError("authority cannot be opened no-follow") from exc
    try:
        facts = os.fstat(fd)
        _require(stat.S_ISREG(facts.st_mode), "authority is not regular")
        observed, observed_size = _hash_fd(fd)
        _require(observed == digest and observed_size == size, "authority bytes changed")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except Exception:
        os.close(fd)
        raise


def _read_pinned(path: Path, digest: str, maximum: int) -> Mapping[str, Any]:
    _no_symlinks(path, "pinned authority")
    size = path.stat().st_size
    fd = _open_authenticated(path, digest, size, maximum)
    try:
        body = bytearray()
        while block := os.read(fd, 1024 * 1024):
            body.extend(block)
    finally:
        os.close(fd)
    try:
        value = json.loads(body)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CostCalibrationError("pinned authority is invalid JSON") from exc
    _require(type(value) is dict, "pinned authority is not an object")
    return value


def _same_fds(left: int, right: int) -> bool:
    if os.fstat(left).st_size != os.fstat(right).st_size:
        return False
    lp = os.lseek(left, 0, os.SEEK_CUR)
    rp = os.lseek(right, 0, os.SEEK_CUR)
    os.lseek(left, 0, os.SEEK_SET)
    os.lseek(right, 0, os.SEEK_SET)
    try:
        while block := os.read(left, 1024 * 1024):
            if block != os.read(right, len(block)):
                return False
        return os.read(right, 1) == b""
    finally:
        os.lseek(left, lp, os.SEEK_SET)
        os.lseek(right, rp, os.SEEK_SET)


def _rename(old_dir: int, old: str, new_dir: int, new: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        function = libc.renameat2
    except AttributeError as exc:
        raise CostCalibrationError("atomic no-replace rename is unavailable") from exc
    function.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    function.restype = ctypes.c_int
    if function(old_dir, os.fsencode(old), new_dir, os.fsencode(new), RENAME_NOREPLACE):
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), new)


class _OutputTree:
    def __init__(self, root: Path) -> None:
        _require(root.name.startswith("."), "cost output root must be hidden")
        _no_symlinks(root, "output root")
        if not root.exists():
            root.mkdir(mode=0o700)
            parent = os.open(root.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        self.root = root.resolve(strict=True)
        self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self.fd)
            raise CostCalibrationError("another normalizer holds the output root") from exc
        facts = os.fstat(self.fd)
        self.identity = (facts.st_dev, facts.st_ino)
        self._owned_stages: dict[str, tuple[int, int]] = {}
        os.close(self.directory((".staging",), True))

    def close(self) -> None:
        for name in tuple(self._owned_stages):
            self.cleanup_stage(name)
        os.close(self.fd)

    def verify_root(self) -> None:
        current = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            facts = os.fstat(current)
            _require((facts.st_dev, facts.st_ino) == self.identity, "held output root was replaced")
        finally:
            os.close(current)

    def directory(self, parts: Sequence[str], create: bool) -> int:
        current = os.dup(self.fd)
        try:
            for raw in parts:
                name = _safe_component(raw)
                if create:
                    try:
                        os.mkdir(name, 0o700, dir_fd=current)
                        os.fsync(current)
                    except FileExistsError:
                        pass
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
                os.close(current)
                current = child
            return current
        except Exception:
            os.close(current)
            raise

    def create_stage(self, prefix: str, suffix: str) -> tuple[int, str, Path]:
        staging = self.directory((".staging",), False)
        stage = f"{_safe_component(prefix)}-{uuid.uuid4().hex}{suffix}"
        fd = os.open(
            stage,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=staging,
        )
        facts = os.fstat(fd)
        self._owned_stages[stage] = (facts.st_dev, facts.st_ino)
        os.close(staging)
        return fd, stage, self.root / ".staging" / stage

    def _stage_matches(self, staging: int, name: str) -> bool:
        expected = self._owned_stages.get(name)
        if expected is None:
            return False
        try:
            facts = os.stat(name, dir_fd=staging, follow_symlinks=False)
        except FileNotFoundError:
            return False
        return stat.S_ISREG(facts.st_mode) and (facts.st_dev, facts.st_ino) == expected

    def cleanup_stage(self, name: str) -> None:
        staging = self.directory((".staging",), False)
        try:
            if self._stage_matches(staging, name):
                os.unlink(name, dir_fd=staging)
                os.fsync(staging)
            self._owned_stages.pop(name, None)
        finally:
            os.close(staging)

    def publish_stage(
        self,
        fd: int,
        stage: str,
        parts: Sequence[str],
        name: str,
        kind: str,
        hooks: PublicationHooks,
    ) -> tuple[Path, str, int, bool]:
        staging = self.directory((".staging",), False)
        final: int | None = None
        try:
            os.fsync(fd)
            digest, size = _hash_fd(fd)
            _require(name == f"{digest}.{name.rsplit('.', 1)[-1]}", "publication address changed")
            _require(self._stage_matches(staging, stage), "held staged object was replaced")
            destination = self.directory(parts, True)
            path = self.root.joinpath(*parts, name)
            try:
                if hooks.before_publish is not None:
                    hooks.before_publish(kind, self.root / ".staging" / stage, path)
                self.verify_root()
                _require(self._stage_matches(staging, stage), "held staged object was replaced")
                _require(_hash_fd(fd) == (digest, size), "held staged bytes changed")
                try:
                    _rename(staging, stage, destination, name)
                    self._owned_stages.pop(stage, None)
                    os.fsync(destination)
                    os.fsync(staging)
                    reused = False
                except OSError as exc:
                    if exc.errno != errno.EEXIST:
                        raise
                    reused = True
                final = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=destination)
                _require(stat.S_ISREG(os.fstat(final).st_mode), "published object is not regular")
                _require(_same_fds(fd, final), "published or replayed bytes differ")
                _require(_hash_fd(final) == (digest, size), "published object bytes changed")
                if reused:
                    self.cleanup_stage(stage)
                self.verify_root()
            finally:
                os.close(destination)
            return path, digest, size, reused
        finally:
            if final is not None:
                os.close(final)
            os.close(staging)

    def publish(self, writer: Callable[[int], None], parts: Sequence[str], name: str, kind: str, hooks: PublicationHooks) -> tuple[Path, str, int, bool]:
        fd, stage, _path = self.create_stage(kind, ".tmp")
        try:
            writer(fd)
            return self.publish_stage(fd, stage, parts, name, kind, hooks)
        finally:
            os.close(fd)
            self.cleanup_stage(stage)

    def only_completion(self, name: str) -> None:
        directory = self.directory((".complete",), True)
        try:
            _require(not [entry for entry in os.listdir(directory) if entry != name], "another completion exists")
        finally:
            os.close(directory)

    def open_final(self, path: Path) -> int:
        self.verify_root()
        try:
            relative = path.relative_to(self.root)
        except ValueError as exc:
            raise CostCalibrationError("published path escapes output root") from exc
        _require(len(relative.parts) >= 2, "published path is incomplete")
        directory = self.directory(relative.parts[:-1], False)
        try:
            try:
                fd = os.open(
                    _safe_component(relative.name),
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=directory,
                )
            except OSError as exc:
                raise CostCalibrationError("published object cannot be reopened") from exc
        finally:
            os.close(directory)
        try:
            _require(stat.S_ISREG(os.fstat(fd).st_mode), "published object is not regular")
            self.verify_root()
            return fd
        except Exception:
            os.close(fd)
            raise

    def inventory(self) -> tuple[set[str], set[str]]:
        files: set[str] = set()
        directories: set[str] = set()

        def walk(directory: int, prefix: tuple[str, ...]) -> None:
            for name in sorted(os.listdir(directory)):
                _safe_component(name)
                facts = os.stat(name, dir_fd=directory, follow_symlinks=False)
                relative = "/".join((*prefix, name))
                if stat.S_ISDIR(facts.st_mode):
                    child = os.open(
                        name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                        dir_fd=directory,
                    )
                    directories.add(relative)
                    try:
                        walk(child, (*prefix, name))
                    finally:
                        os.close(child)
                elif stat.S_ISREG(facts.st_mode):
                    files.add(relative)
                else:
                    raise CostCalibrationError("output tree contains an unsafe object")

        walk(self.fd, ())
        self.verify_root()
        return files, directories


def _publish_json(tree: _OutputTree, document: Mapping[str, Any], parts: Sequence[str], kind: str, hooks: PublicationHooks) -> tuple[Path, str, int, bool]:
    body = _canonical_json(document)
    digest = hashlib.sha256(body).hexdigest()

    def write(fd: int) -> None:
        view = memoryview(body)
        while view:
            count = os.write(fd, view)
            _require(count > 0, "JSON write stalled")
            view = view[count:]

    return tree.publish(write, parts, f"{digest}.json", kind, hooks)


def _publish_parquet_file(tree: _OutputTree, staged_fd: int, stage_name: str, digest: str, schema: pa.Schema, rows: int, parts: Sequence[str], kind: str, hooks: PublicationHooks) -> tuple[Path, str, int, bool]:
    path, observed, size, reused = tree.publish_stage(
        staged_fd,
        stage_name,
        parts,
        f"{digest}.parquet",
        kind,
        hooks,
    )
    _require(observed == digest, "published Parquet digest changed")
    final_fd = tree.open_final(path)
    try:
        final_digest, _ = _hash_fd(final_fd)
        parquet = pq.ParquetFile(f"/proc/self/fd/{final_fd}")
        _require(final_digest == digest, "published Parquet digest changed")
        _require(parquet.schema_arrow == schema and parquet.metadata.num_rows == rows, "published Parquet shape changed")
    finally:
        os.close(final_fd)
    return path, observed, size, reused


def _stage_table(tree: _OutputTree, table: pa.Table, prefix: str) -> tuple[int, str, str]:
    fd, name, _path = tree.create_stage(prefix, ".parquet")
    try:
        pq.write_table(
            table,
            f"/proc/self/fd/{fd}",
            compression=PARQUET_COMPRESSION,
            compression_level=PARQUET_COMPRESSION_LEVEL,
            version=PARQUET_VERSION,
            write_statistics=False,
            store_schema=True,
        )
        os.fsync(fd)
        digest, _ = _hash_fd(fd)
        parquet = pq.ParquetFile(f"/proc/self/fd/{fd}")
        _require(
            parquet.schema_arrow == table.schema
            and parquet.metadata.num_rows == table.num_rows,
            "staged Parquet shape changed",
        )
        return fd, name, digest
    except Exception:
        os.close(fd)
        tree.cleanup_stage(name)
        raise


def _publish_table(
    tree: _OutputTree,
    table: pa.Table,
    prefix: str,
    parts: Sequence[str],
    kind: str,
    hooks: PublicationHooks,
) -> tuple[Path, str, int, bool]:
    fd, name, digest = _stage_table(tree, table, prefix)
    try:
        return _publish_parquet_file(
            tree,
            fd,
            name,
            digest,
            table.schema,
            table.num_rows,
            parts,
            kind,
            hooks,
        )
    finally:
        os.close(fd)
        tree.cleanup_stage(name)


def _expected_directories(files: set[str]) -> set[str]:
    directories = {".staging", ".complete"}
    for relative in files:
        parts = PurePosixPath(relative).parts[:-1]
        for length in range(1, len(parts) + 1):
            directories.add("/".join(parts[:length]))
    return directories


def _reprove_json(
    tree: _OutputTree,
    path: Path,
    digest: str,
    size: int,
) -> Mapping[str, Any]:
    fd: int | None = None
    try:
        fd = tree.open_final(path)
        observed_digest, observed_size = _hash_fd(fd)
        _require(
            (observed_digest, observed_size) == (digest, size),
            "published JSON bytes changed",
        )
        os.lseek(fd, 0, os.SEEK_SET)
        body = bytearray()
        while block := os.read(fd, 1024 * 1024):
            body.extend(block)
    except Exception as exc:
        if isinstance(exc, CostCalibrationError):
            raise
        raise CostCalibrationError("published JSON cannot be re-proved") from exc
    finally:
        if fd is not None:
            os.close(fd)
    try:
        document = json.loads(body)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CostCalibrationError("published JSON is invalid") from exc
    _require(type(document) is dict, "published JSON is not an object")
    return document


def _reprove_parquet(tree: _OutputTree, item: PublishedComponent) -> None:
    fd: int | None = None
    try:
        fd = tree.open_final(item.parquet_path)
        digest, size = _hash_fd(fd)
        parquet = pq.ParquetFile(f"/proc/self/fd/{fd}")
        _require(
            digest == item.parquet_sha256
            and size == item.parquet_bytes
            and parquet.schema_arrow == SCHEMAS[item.component]
            and parquet.metadata.num_rows == item.row_count,
            "published Parquet descriptor changed",
        )
    except Exception as exc:
        if isinstance(exc, CostCalibrationError):
            raise
        raise CostCalibrationError("published Parquet cannot be re-proved") from exc
    finally:
        if fd is not None:
            os.close(fd)


def _reprove_output(
    tree: _OutputTree,
    components: Sequence[PublishedComponent],
    source_gap: tuple[Path, str, int],
    completion: tuple[Path, str, int] | None,
    *,
    completion_required: bool,
) -> None:
    expected_files: set[str] = set()
    for item in components:
        _reprove_parquet(tree, item)
        lineage = _reprove_json(
            tree,
            item.lineage_path,
            item.lineage_sha256,
            item.lineage_bytes,
        )
        _require(
            lineage.get("component") == item.component
            and lineage.get("row_count") == item.row_count
            and lineage.get("schema_sha256") == SCHEMA_IDENTITIES[item.component]
            and lineage.get("parquet_sha256") == item.parquet_sha256
            and lineage.get("parquet_bytes") == item.parquet_bytes
            and lineage.get("parquet_path")
            == str(item.parquet_path.relative_to(tree.root)),
            "published lineage descriptor changed",
        )
        expected_files.add(str(item.parquet_path.relative_to(tree.root)))
        expected_files.add(str(item.lineage_path.relative_to(tree.root)))
    source_gap_path, source_gap_sha, source_gap_bytes = source_gap
    _reprove_json(tree, source_gap_path, source_gap_sha, source_gap_bytes)
    expected_files.add(str(source_gap_path.relative_to(tree.root)))
    files, directories = tree.inventory()
    if completion is not None:
        completion_path, completion_sha, completion_bytes = completion
        relative = str(completion_path.relative_to(tree.root))
        if relative in files:
            _reprove_json(tree, completion_path, completion_sha, completion_bytes)
            expected_files.add(relative)
        else:
            _require(not completion_required, "completion disappeared")
    _require(files == expected_files, "output file inventory does not match completion")
    _require(
        directories == _expected_directories(expected_files),
        "output directory inventory does not match completion",
    )


def _report_manifest(report: Mapping[str, Any]) -> tuple[set[str], tuple[Mapping[str, Any], ...]]:
    storage = report.get("storage")
    _require(type(storage) is dict, "report storage block missing")
    block = storage.get("cost_sample")
    _require(type(block) is dict, "report cost manifest missing")
    keys = tuple(str(value) for value in block.get("keys", ()))
    gaps = tuple(block.get("gaps", ()))
    _require(len(keys) == ACCEPTED_COST_OBJECTS and len(set(keys)) == len(keys), "cost key inventory changed")
    _require(block.get("object_count") == ACCEPTED_COST_OBJECTS and block.get("compressed_raw_bytes") == ACCEPTED_COST_BYTES, "cost manifest totals changed")
    _require(block.get("families") == list(FAMILIES) and block.get("selector") == "first_midpoint_last_daily_book_v1", "cost selector changed")
    _require(block.get("manifest_digest_version") == COST_MANIFEST_DIGEST_VERSION and block.get("manifest_digest") == COST_MANIFEST_SHA256, "cost manifest identity changed")
    _require(len(gaps) == ACCEPTED_SOURCE_GAPS and all(type(gap) is dict for gap in gaps), "cost source gaps changed")
    gap_keys: set[tuple[str, str]] = set()
    for gap in gaps:
        family = gap.get("family")
        symbol = gap.get("symbol")
        _require(
            family in FAMILIES
            and type(symbol) is str
            and bool(symbol)
            and gap.get("family_group") == str(family).rsplit("/", 1)[-1]
            and gap.get("kind") == "cost_sample_unavailable"
            and gap.get("status") == "cost_sample_unavailable"
            and gap.get("blocking") is True,
            "cost source gap facts changed",
        )
        gap_key = (str(family), symbol)
        _require(gap_key not in gap_keys, "cost source gaps repeat a family/symbol")
        gap_keys.add(gap_key)
    for key in keys:
        _identity(key)
    return set(keys), gaps


def _validate_sizing(sizing: Mapping[str, Any]) -> None:
    typed = sizing.get("typed_schema_contract")
    _require(type(typed) is dict and typed.get("cost_component_schemas") == product_schema_contract(PRODUCT), "cost component schemas changed")
    projections = sizing.get("projections")
    _require(type(projections) is dict and projections.get("row_batch_cap") == SIZING_ROW_BATCH, "cost writer row-group bound changed")
    components = sizing.get("cost_calibration_components")
    _require(type(components) is dict, "cost component allocation missing")
    for component, limits in COMPONENT_LIMITS.items():
        value = components.get(component)
        _require(
            type(value) is dict
            and value.get("component") == component
            and value.get("projected_rows") == limits["rows"]
            and value.get("projected_bytes") == limits["bytes"]
            and value.get("largest_partition_bytes")
            == limits["largest_partition_bytes"]
            and value.get("partition_count") == limits["partitions"],
            f"{component} allocation changed",
        )
    _require(
        sum(limits["bytes"] for limits in COMPONENT_LIMITS.values())
        == NORMALIZED_ALLOCATION_BYTES,
        "cost normalized allocation changed",
    )


def _open_regular_child(directory: int, name: str) -> int | None:
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
    except FileNotFoundError:
        return None
    _require(stat.S_ISREG(os.fstat(fd).st_mode), "SQLite authority leaf is not regular")
    return fd


def load_generation0_cost_sources(state_path: Path, content_root: Path, selected: set[str]) -> tuple[RawCostObject, ...]:
    _no_symlinks(state_path, "generation-0 state")
    _no_symlinks(content_root, "generation-0 content")
    parent = state_path.absolute().parent
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    state_fd = _open_regular_child(parent_fd, state_path.name)
    _require(state_fd is not None, "generation-0 state missing")
    sidecars = {name: _open_regular_child(parent_fd, name) for name in (f"{state_path.name}-wal", f"{state_path.name}-shm", f"{state_path.name}-journal")}
    connection: sqlite3.Connection | None = None
    borrowed: AcquisitionState | None = None
    try:
        connection = sqlite3.connect(f"file:/proc/self/fd/{parent_fd}/{state_path.name}?mode=ro", uri=True, isolation_level=None)
        reopened = _open_regular_child(parent_fd, state_path.name)
        _require(reopened is not None, "generation-0 state disappeared")
        assert state_fd is not None and reopened is not None
        before = os.fstat(state_fd)
        after = os.fstat(reopened)
        os.close(reopened)
        _require((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino), "generation-0 state was replaced")
        for name, held in sidecars.items():
            observed = _open_regular_child(parent_fd, name)
            if held is None:
                _require(observed is None, "a SQLite sidecar appeared during read-only open")
            else:
                _require(observed is not None, "a SQLite sidecar disappeared during read-only open")
                assert observed is not None
                old = os.fstat(held)
                new = os.fstat(observed)
                _require((old.st_dev, old.st_ino) == (new.st_dev, new.st_ino), "a SQLite sidecar was replaced")
            if observed is not None:
                os.close(observed)
        register_domain_functions(connection)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        _require(connection.execute("PRAGMA application_id").fetchone()[0] == STATE_APPLICATION_ID, "generation-0 application id changed")
        _require(connection.execute("PRAGMA user_version").fetchone()[0] == STATE_USER_VERSION, "generation-0 schema version changed")
        _require(connection.execute("PRAGMA integrity_check").fetchone() == ("ok",), "generation-0 integrity failed")
        _require(not connection.execute("PRAGMA foreign_key_check").fetchall(), "generation-0 foreign keys failed")
        borrowed = AcquisitionState(state_path, state_path.with_name("acquisition.lock"))
        borrowed.conn = connection
        borrowed.authenticate_schema()
        borrowed.authenticate_domains()
        borrowed.authenticate_singletons()
        borrowed.authenticate_prefix()
        borrowed._require_runnable_head()
        head = borrowed.seal_head_row()
        _require(head is not None and head["receipt_sha256"] == GENERATION0_SEAL, "generation-0 seal changed")
        count = connection.execute("SELECT COUNT(*) FROM completion WHERE provider='binance_vision'").fetchone()[0]
        _require(count == ACCEPTED_GENERATION0_BINANCE_COMPLETIONS, "generation-0 completion count changed")
        query = (
            "SELECT p.identity,p.payload_json,c.content_sha256,c.content_path,c.listed_bytes,"
            "c.retrieved_at,c.revision_json,c.validation_state,c.sidecar_sha256,c.sidecar_path,"
            "s.sidecar_sha256,s.sidecar_path,s.provider_checksum,s.sidecar_bytes "
            "FROM plan_entry p JOIN completion c "
            "ON c.provider=p.provider AND c.identity=p.identity JOIN sidecar_fact s "
            "ON s.provider=p.provider AND s.identity=p.identity WHERE p.provider='binance_vision' ORDER BY p.identity"
        )
        result: list[RawCostObject] = []
        for row in connection.execute(query):
            (
                identity,
                payload_json,
                digest,
                recorded_path,
                size,
                retrieved,
                revision_json,
                state,
                completion_sidecar_sha,
                completion_sidecar_path,
                fact_sidecar_sha,
                fact_sidecar_path,
                provider_digest,
                sidecar_size,
            ) = row
            if str(identity) not in selected:
                continue
            try:
                envelope = json.loads(str(payload_json))
                revision = json.loads(str(revision_json))
            except json.JSONDecodeError as exc:
                raise CostCalibrationError("generation-0 plan or revision JSON changed") from exc
            _require(type(revision) is dict, "generation-0 revision changed")
            payload = envelope.get("payload") if type(envelope) is dict else None
            _require(type(payload) is dict and payload.get("key") == identity, "generation-0 plan identity changed")
            family, symbol, day = _identity(str(identity))
            _require(payload.get("family") == family and payload.get("symbol") == symbol and payload.get("economic_interval") == day, "generation-0 plan facts changed")
            _require(payload.get("listed_bytes") == size and type(payload.get("etag")) is str, "generation-0 listing facts changed")
            _require(state in (OUTCOME_CHECKSUM_VERIFIED, OUTCOME_RETAINED), "generation-0 cost state changed")
            _require(str(digest) == str(provider_digest) and _is_digest(str(digest)), "generation-0 checksum proof changed")
            path = content_path_for(content_root, str(digest))
            _require(Path(str(recorded_path)) == path, "generation-0 raw content address changed")
            _require(
                completion_sidecar_sha == fact_sidecar_sha
                and completion_sidecar_path == fact_sidecar_path
                and _is_digest(str(fact_sidecar_sha)),
                "generation-0 sidecar fact disagrees with completion",
            )
            sidecar_path = content_path_for(content_root, str(fact_sidecar_sha))
            _require(Path(str(fact_sidecar_path)) == sidecar_path, "generation-0 sidecar content address changed")
            sidecar_fd = _open_authenticated(
                sidecar_path,
                str(fact_sidecar_sha),
                int(sidecar_size),
                SIDECAR_CEILING_BYTES,
            )
            try:
                body = bytearray()
                while block := os.read(sidecar_fd, SIDECAR_CEILING_BYTES):
                    body.extend(block)
            finally:
                os.close(sidecar_fd)
            try:
                parsed = parse_sidecar(bytes(body), basename=str(identity).rsplit("/", 1)[-1])
            except Exception as exc:
                raise CostCalibrationError("generation-0 sidecar statement changed") from exc
            _require(parsed == str(digest), "generation-0 sidecar checksum changed")
            result.append(RawCostObject(str(identity), family, symbol, day, path, str(digest), int(size), str(payload["etag"]), "accepted_generation_0_completion", "binance_checksum_sidecar", str(retrieved), revision=revision))
        connection.execute("ROLLBACK")
        borrowed.conn = None
        _require(len(result) == ACCEPTED_GENERATION0_OBJECTS, "generation-0 cost source count changed")
        return tuple(result)
    except sqlite3.Error as exc:
        raise CostCalibrationError("generation-0 authority cannot be read safely") from exc
    finally:
        if borrowed is not None:
            borrowed.conn = None
        if connection is not None:
            connection.close()
        for fd in sidecars.values():
            if fd is not None:
                os.close(fd)
        if state_fd is not None:
            os.close(state_fd)
        os.close(parent_fd)


def load_recovery_cost_sources(manifest_path: Path, recovery_root: Path, selected: set[str]) -> tuple[RawCostObject, ...]:
    _no_symlinks(manifest_path, "v3 manifest")
    _no_symlinks(recovery_root, "recovery root")
    manifest_size = manifest_path.stat().st_size
    fd = _open_authenticated(manifest_path, V3_MANIFEST_SHA256, manifest_size, 32 * 2**20)
    result: list[RawCostObject] = []
    rows = total = metrics = 0
    seen: set[str] = set()
    try:
        with (
            os.fdopen(os.dup(fd), "rb") as raw,
            gzip.GzipFile(fileobj=raw, mode="rb") as compressed,
            io.TextIOWrapper(compressed, encoding="utf-8", newline="") as handle,
        ):
            for line in handle:
                envelope = json.loads(line)
                _require(type(envelope) is dict and envelope.get("record_type") == "row", "v3 manifest envelope changed")
                record = envelope.get("record")
                _require(type(record) is dict, "v3 manifest record changed")
                family = record.get("family")
                _require(family in ("daily/metrics", FAMILY_TICKER), "v3 manifest family changed")
                size = record.get("current_listed_bytes")
                _require(type(size) is int and size > 0, "v3 listed size changed")
                rows += 1
                total += size
                metrics += family == "daily/metrics"
                if family != FAMILY_TICKER:
                    continue
                key = str(record.get("identity") or "")
                _require(key not in seen, "v3 manifest repeats a cost key")
                seen.add(key)
                source_family, symbol, day = _identity(key)
                digest = str(record.get("provider_checksum") or "")
                _require(source_family == FAMILY_TICKER and key in selected and _is_digest(digest), "v3 cost record changed")
                path = _authority_child(recovery_root, key, "recovery source")
                result.append(RawCostObject(key, source_family, symbol, day, path, digest, size, str(record.get("current_listing", {}).get("etag") or ""), "accepted_v3_direct_recovery", "v3_manifest_provider_checksum", revision=dict(record)))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CostCalibrationError("v3 manifest cannot be read safely") from exc
    finally:
        os.close(fd)
    _require(rows == ACCEPTED_V3_ROWS and total == ACCEPTED_V3_BYTES and metrics == ACCEPTED_V3_METRICS_ROWS, "v3 manifest totals changed")
    _require(len(result) == ACCEPTED_RECOVERY_OBJECTS and sum(item.byte_size for item in result) == ACCEPTED_RECOVERY_BYTES, "v3 recovery cost inventory changed")
    return tuple(result)


def _manifest_reproof(sources: Sequence[RawCostObject], gaps: Sequence[Mapping[str, Any]]) -> None:
    class Obj:
        def __init__(self, size: int, etag: str) -> None:
            self.size = size
            self.etag = etag

    items = [{"family": source.family, "symbol": source.native_symbol, "key": source.source_key, "object": Obj(source.byte_size, source.etag)} for source in sources]
    digest = cost_manifest_digest(items, selector="first_midpoint_last_daily_book_v1", families=FAMILIES, gaps=gaps)
    _require(digest == COST_MANIFEST_SHA256, "complete cost manifest cannot be re-proved")


def load_membership_identities(root: Path) -> tuple[MembershipIdentity, ...]:
    _no_symlinks(root, "membership root")
    complete = root / ".complete" / f"{MEMBERSHIP_COMPLETION_SHA256}.json"
    completion_dir = root / ".complete"
    _require(
        completion_dir.is_dir()
        and sorted(path.name for path in completion_dir.iterdir())
        == [f"{MEMBERSHIP_COMPLETION_SHA256}.json"],
        "membership completion inventory changed",
    )
    document = _read_pinned(complete, MEMBERSHIP_COMPLETION_SHA256, MAX_REPORT_BYTES)
    _require(
        document.get("required_product") == PRODUCT_MEMBERSHIP
        and document.get("schema_sha256") == product_schema_identity(PRODUCT_MEMBERSHIP)
        and document.get("membership_rows") == ACCEPTED_MEMBERSHIP_IDENTITIES,
        "membership completion changed",
    )
    descriptors = document.get("partitions")
    _require(type(descriptors) is list and len(descriptors) == ACCEPTED_MEMBERSHIP_IDENTITIES, "membership descriptors changed")
    schema = final_product_schema(PRODUCT_MEMBERSHIP)
    rows: list[MembershipIdentity] = []
    seen: set[str] = set()
    for descriptor in descriptors:
        _require(type(descriptor) is dict and descriptor.get("row_count") == 1, "membership descriptor changed")
        symbol = str(descriptor.get("native_symbol") or "")
        _safe_component(symbol)
        _require(symbol not in seen, "membership repeats an identity")
        seen.add(symbol)
        path = _authority_child(root, str(descriptor.get("parquet_path") or ""), "membership partition")
        digest = str(descriptor.get("parquet_sha256"))
        fd = _open_authenticated(path, digest, path.stat().st_size, 4 * 2**20)
        try:
            parquet = pq.ParquetFile(f"/proc/self/fd/{fd}")
            _require(parquet.schema_arrow == schema and parquet.metadata.num_rows == 1, "membership partition schema changed")
            table = parquet.read()
        finally:
            os.close(fd)
        values = table.to_pylist()
        _require(len(values) == 1 and values[0]["native_symbol"] == symbol, "membership partition changed")
        row = values[0]
        rows.append(MembershipIdentity(row["venue"], symbol, row["canonical_instrument_id"], row["canonical_instrument_version_id"], row["reference_identity_state"]))
    _require(len(rows) == ACCEPTED_MEMBERSHIP_IDENTITIES, "membership identity count changed")
    return tuple(sorted(rows, key=lambda item: item.native_symbol))


def _member(source: RawCostObject) -> Iterator[tuple[int, list[str]]]:
    fd = _open_authenticated(source.path, source.source_sha256, source.byte_size, MAX_COMPRESSED_OBJECT_BYTES)
    expected_fields = KNOWN_ARCHIVE_SCHEMAS["bookTicker" if source.family == FAMILY_TICKER else "bookDepth"]
    fields = expected_fields["headerless"]
    try:
        with os.fdopen(os.dup(fd), "rb") as raw_file, zipfile.ZipFile(raw_file) as archive:
            members = archive.infolist()
            _require(len(members) == 1, "cost ZIP must contain one member")
            info = members[0]
            name = info.filename
            parts = PurePosixPath(name.replace("\\", "/"))
            expected = source.source_key.rsplit("/", 1)[-1][:-4] + ".csv"
            _require(name == expected and len(parts.parts) == 1 and not parts.is_absolute() and ".." not in parts.parts, "cost ZIP member is unsafe")
            _require(not info.is_dir() and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG), "cost ZIP member is not regular")
            _require(not (info.flag_bits & 1) and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), "cost ZIP encoding is unsupported")
            _require(0 < info.file_size <= MAX_MEMBER_BYTES, "cost ZIP expansion exceeds bound")
            with archive.open(info) as binary:
                text = io.TextIOWrapper(binary, encoding="utf-8", newline="")
                reader = csv.reader(text, strict=True)
                ordinal = 0
                first = True
                for physical in reader:
                    _require(all(len(cell.encode()) <= MAX_FIELD_BYTES for cell in physical), "cost CSV field exceeds bound")
                    if first:
                        first = False
                        if tuple(cell.strip() for cell in physical) == fields:
                            continue
                    _require(bool(physical) and len(physical) == len(fields), "cost CSV row width changed")
                    _require(ordinal < MAX_ROWS_PER_OBJECT, "cost CSV row count exceeds bound")
                    yield ordinal, physical
                    ordinal += 1
                _require(ordinal > 0, "cost CSV has no data rows")
    except (OSError, UnicodeError, csv.Error, zipfile.BadZipFile, RuntimeError) as exc:
        if isinstance(exc, CostCalibrationError):
            raise
        raise CostCalibrationError("cost ZIP/CSV is invalid") from exc
    finally:
        os.close(fd)


def _integer(token: str, source: RawCostObject, column: str, ordinal: int) -> int:
    try:
        return convert_integer(token, key=source.source_key, output=PRODUCT, column=column, row=ordinal)
    except Exception as exc:
        raise CostCalibrationError(f"cost {column} is invalid") from exc


def _decimal(token: str, source: RawCostObject, column: str, ordinal: int) -> Decimal:
    try:
        return convert_decimal(token, key=source.source_key, output=PRODUCT, column=column, row=ordinal)
    except Exception as exc:
        raise CostCalibrationError(f"cost {column} is invalid") from exc


def _timestamp(token: str, source: RawCostObject, ordinal: int) -> int:
    try:
        return convert_timestamp_text(token, key=source.source_key, output=PRODUCT, column="timestamp", row=ordinal)
    except Exception as exc:
        raise CostCalibrationError("cost depth timestamp is invalid") from exc


def _day_start_ms(value: str) -> int:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise CostCalibrationError("cost economic day is invalid") from exc
    _require(parsed.isoformat() == value, "cost economic day is not canonical")
    epoch = date(1970, 1, 1)
    return (parsed.toordinal() - epoch.toordinal()) * 86_400_000


def _typed_row(source: RawCostObject, raw_ref: int, ordinal: int, cells: Sequence[str], identity: MembershipIdentity) -> tuple[dict[str, Any], str, str | None]:
    base = {"raw_object_ref": raw_ref, "source_row_ordinal": ordinal, "venue_symbol": source.native_symbol, **identity.row()}
    if source.family == FAMILY_TICKER:
        update, bid, bid_qty, ask, ask_qty, transaction, event = cells
        values = {
            **base,
            "update_id": _integer(update, source, "update_id", ordinal),
            "best_bid_price": _decimal(bid, source, "best_bid_price", ordinal),
            "best_bid_qty": _decimal(bid_qty, source, "best_bid_qty", ordinal),
            "best_ask_price": _decimal(ask, source, "best_ask_price", ordinal),
            "best_ask_qty": _decimal(ask_qty, source, "best_ask_qty", ordinal),
            "transaction_time": _integer(transaction, source, "transaction_time", ordinal),
            "event_time": _integer(event, source, "event_time", ordinal),
        }
        _require(values["update_id"] >= 0 and values["transaction_time"] > 0 and values["event_time"] > 0, "ticker integer domain changed")
        sides = (values["best_bid_price"], values["best_bid_qty"], values["best_ask_price"], values["best_ask_qty"])
        _require(all(value >= 0 for value in sides), "ticker quote value is negative")
        _require(not (values["best_bid_price"] <= 0 < values["best_bid_qty"]), "ticker bid is inconsistent")
        _require(not (values["best_ask_price"] <= 0 < values["best_ask_qty"]), "ticker ask is inconsistent")
        if values["best_bid_price"] > 0 and values["best_ask_price"] > 0:
            _require(values["best_bid_price"] <= values["best_ask_price"], "ticker quote is crossed")
            state = "two_sided"
        elif values["best_bid_price"] > 0:
            state = "bid_only"
        elif values["best_ask_price"] > 0:
            state = "ask_only"
        else:
            state = "empty"
        moment = values["transaction_time"]
    else:
        timestamp, percentage, depth, notional = cells
        values = {
            **base,
            "timestamp": _timestamp(timestamp, source, ordinal),
            "percentage": _decimal(percentage, source, "percentage", ordinal),
            "depth": _decimal(depth, source, "depth", ordinal),
            "notional": _decimal(notional, source, "notional", ordinal),
        }
        _require(values["timestamp"] > 0 and values["percentage"] != 0, "depth time or band is invalid")
        _require(values["depth"] >= 0 and values["notional"] >= 0, "depth value is negative")
        moment = values["timestamp"]
        state = None
    day_start = _day_start_ms(source.economic_day)
    _require(
        day_start <= moment <= day_start + 86_400_000,
        "cost row is outside its source day boundary",
    )
    month = datetime.fromtimestamp(moment // 1000, UTC).strftime("%Y-%m")
    return values, month, state


def _source_lineage(source: RawCostObject, raw_ref: int) -> dict[str, Any]:
    return {
        "raw_object_ref": raw_ref,
        "source_key": source.source_key,
        "source_sha256": source.source_sha256,
        "byte_size": source.byte_size,
        "etag": source.etag,
        "economic_day": source.economic_day,
        "authority": source.authority,
        "checksum_authority": source.checksum_authority,
        "retrieval_time": source.retrieval_time,
        "source_available_at": source.source_available_at,
        "revision": None if source.revision is None else dict(source.revision),
        "availability_semantics": "unknown_when_not_proved_by_retained_evidence" if source.source_available_at is None else "proved",
    }


def _write_partition(tree: _OutputTree, component: str, symbol: str, month: str, sources: Sequence[RawCostObject], identity: MembershipIdentity, hooks: PublicationHooks) -> tuple[PublishedComponent, Counter[str]]:
    schema = SCHEMAS[component]
    fd, name, _path = tree.create_stage("partition-build", ".parquet")
    writer: pq.ParquetWriter | None = None
    rows: list[dict[str, Any]] = []
    row_count = 0
    states: Counter[str] = Counter()
    previous: dict[int, int] = {}
    ordinals: dict[int, tuple[int, int]] = {}
    physical_counts: dict[int, int] = {}
    try:
        writer = pq.ParquetWriter(f"/proc/self/fd/{fd}", schema, compression=PARQUET_COMPRESSION, compression_level=PARQUET_COMPRESSION_LEVEL, version=PARQUET_VERSION, write_statistics=False, store_schema=True)
        for raw_ref, source in enumerate(sources):
            first_ordinal: int | None = None
            last_ordinal: int | None = None
            for ordinal, cells in _member(source):
                physical_counts[raw_ref] = ordinal + 1
                values, observed_month, quote_state = _typed_row(source, raw_ref, ordinal, cells, identity)
                time_column = "transaction_time" if component == COMPONENT_TICKER else "timestamp"
                moment = int(values[time_column])
                _require(moment >= previous.get(raw_ref, 0), "cost source time moves backwards")
                previous[raw_ref] = moment
                if observed_month != month:
                    continue
                first_ordinal = ordinal if first_ordinal is None else first_ordinal
                last_ordinal = ordinal
                if quote_state is not None:
                    states[quote_state] += 1
                rows.append(values)
                if len(rows) == SIZING_ROW_BATCH:
                    writer.write_table(pa.Table.from_pylist(rows, schema=schema), row_group_size=SIZING_ROW_BATCH)
                    if hooks.observe_batch is not None:
                        hooks.observe_batch(component, len(rows))
                    row_count += len(rows)
                    rows.clear()
            if first_ordinal is not None and last_ordinal is not None:
                ordinals[raw_ref] = (first_ordinal, last_ordinal)
        if rows:
            writer.write_table(pa.Table.from_pylist(rows, schema=schema), row_group_size=SIZING_ROW_BATCH)
            if hooks.observe_batch is not None:
                hooks.observe_batch(component, len(rows))
            row_count += len(rows)
            rows.clear()
        _require(row_count > 0, "cost partition has no rows")
        writer.close()
        writer = None
        os.fsync(fd)
        digest, _size = _hash_fd(fd)
        staged = pq.ParquetFile(f"/proc/self/fd/{fd}")
        _require(staged.schema_arrow == schema and staged.metadata.num_rows == row_count, "staged cost partition changed")
        parquet_path, parquet_sha, parquet_bytes, reused = _publish_parquet_file(tree, fd, name, digest, schema, row_count, (".partitions", component, symbol, month), "partition", hooks)
        ordinal_ranges = tuple(
            {
                "raw_object_ref": index,
                "source_key": sources[index].source_key,
                "first": bounds[0],
                "last": bounds[1],
                "retained_rows": bounds[1] - bounds[0] + 1,
                "physical_rows": physical_counts[index],
            }
            for index, bounds in sorted(ordinals.items())
        )
        lineage = {
            "document_type": f"{PRODUCT}_{component}_partition_lineage",
            "schema_version": 1,
            "required_product": PRODUCT,
            "component": component,
            "native_symbol": symbol,
            "utc_month": month,
            "row_count": row_count,
            "schema_sha256": SCHEMA_IDENTITIES[component],
            "writer_identity": writer_identity(),
            "parquet_path": str(parquet_path.relative_to(tree.root)),
            "parquet_sha256": parquet_sha,
            "parquet_bytes": parquet_bytes,
            "raw_objects": [_source_lineage(source, index) for index, source in enumerate(sources)],
            "source_ordinal_ranges": list(ordinal_ranges),
            "partition_time_basis": "transaction_time" if component == COMPONENT_TICKER else "source_timestamp",
        }
        lineage_path, lineage_sha, lineage_bytes, lineage_reused = _publish_json(tree, lineage, (".lineage", component, symbol, month), "lineage", hooks)
        return PublishedComponent(component, symbol, month, row_count, parquet_path, parquet_sha, parquet_bytes, lineage_path, lineage_sha, lineage_bytes, ordinal_ranges, reused and lineage_reused), states
    finally:
        if writer is not None:
            writer.close()
        if fd >= 0:
            os.close(fd)
        tree.cleanup_stage(name)


def _source_row_reconciliation(
    sources: Sequence[RawCostObject],
    components: Sequence[PublishedComponent],
) -> tuple[int, tuple[Mapping[str, Any], ...]]:
    expected_keys = {source.source_key for source in sources}
    physical: dict[str, int] = {}
    retained: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for item in components:
        for value in item.source_ordinal_ranges:
            key = str(value["source_key"])
            _require(key in expected_keys, "partition lineage names an unknown source")
            count = int(value["physical_rows"])
            previous = physical.setdefault(key, count)
            _require(previous == count and count > 0, "source physical row count changed")
            first = int(value["first"])
            last = int(value["last"])
            _require(
                0 <= first <= last < count
                and int(value["retained_rows"]) == last - first + 1,
                "source ordinal range changed",
            )
            retained[key].append((first, last))
    _require(set(physical) == expected_keys, "a physical source has no retained rows")
    facts: list[Mapping[str, Any]] = []
    for source in sources:
        ranges = sorted(retained[source.source_key])
        cursor = 0
        for first, last in ranges:
            _require(first == cursor, "source rows overlap or were omitted")
            cursor = last + 1
        _require(cursor == physical[source.source_key], "source rows were not retained exactly once")
        facts.append(
            {
                "source_key": source.source_key,
                "physical_rows": physical[source.source_key],
                "retained_rows": cursor,
                "first_ordinal": 0,
                "last_ordinal": cursor - 1,
                "partition_ranges": [
                    {"first": first, "last": last} for first, last in ranges
                ],
            }
        )
    return sum(physical.values()), tuple(facts)


def _enforce_component_bounds(components: Sequence[PublishedComponent]) -> None:
    for component, limits in COMPONENT_LIMITS.items():
        selected = [item for item in components if item.component == component]
        _require(
            len(selected) <= limits["partitions"]
            and sum(item.row_count for item in selected) <= limits["rows"]
            and sum(item.parquet_bytes for item in selected) <= limits["bytes"]
            and all(
                item.parquet_bytes <= limits["largest_partition_bytes"]
                for item in selected
            ),
            f"{component} measured allocation exceeded",
        )


def normalize_cost_sources(sources: Sequence[RawCostObject], memberships: Sequence[MembershipIdentity], source_gaps: Sequence[Mapping[str, Any]], output_root: Path, *, report_sha256: str = REPORT_SHA256, sizing_sha256: str = SIZING_SHA256, enforce_full_corpus: bool = False, hooks: PublicationHooks = PublicationHooks()) -> CostCalibrationResult:
    ordered = tuple(sorted(sources, key=lambda source: source.source_key))
    _require(len({source.source_key for source in ordered}) == len(ordered), "cost sources repeat a key")
    for source in ordered:
        family, symbol, day = _identity(source.source_key)
        _require(
            (family, symbol, day)
            == (source.family, source.native_symbol, source.economic_day)
            and _is_digest(source.source_sha256)
            and type(source.byte_size) is int
            and 0 < source.byte_size <= MAX_COMPRESSED_OBJECT_BYTES
            and type(source.etag) is str
            and source.authority
            in {"accepted_generation_0_completion", "accepted_v3_direct_recovery"},
            "cost source descriptor changed",
        )
    identities = {identity.native_symbol: identity for identity in memberships}
    _require(len(identities) == len(memberships), "membership identities repeat")
    _require(
        all(identity.venue == "BINANCE_USDM" for identity in memberships),
        "membership venue changed",
    )
    _require(all(source.native_symbol in identities for source in ordered), "cost source is outside membership")
    tree = _OutputTree(output_root)
    try:
        groups: dict[tuple[str, str, str], list[RawCostObject]] = defaultdict(list)
        for source in ordered:
            # The source day and following month are the only possible daily-file owners;
            # empty candidate partitions are discarded after exact timestamp filtering.
            day_start = _day_start_ms(source.economic_day)
            months = {
                datetime.fromtimestamp(day_start // 1000, UTC).strftime("%Y-%m"),
                datetime.fromtimestamp((day_start + 86_400_000) // 1000, UTC).strftime("%Y-%m"),
            }
            for month in months:
                groups[(COMPONENT_FOR_FAMILY[source.family], source.native_symbol, month)].append(source)
        published: list[PublishedComponent] = []
        quote_states: Counter[str] = Counter()
        for (component, symbol, month), grouped in sorted(groups.items()):
            try:
                item, states = _write_partition(tree, component, symbol, month, tuple(grouped), identities[symbol], hooks)
            except CostCalibrationError as exc:
                if str(exc) == "cost partition has no rows":
                    continue
                raise
            published.append(item)
            quote_states.update(states)
        official_schema = SCHEMAS[COMPONENT_OFFICIAL_FEE]
        empty = pa.Table.from_pylist([], schema=official_schema)
        official_path, official_sha, official_bytes, official_reused = _publish_table(tree, empty, "official-fee", (".partitions", COMPONENT_OFFICIAL_FEE, "__schema__", "schema"), "official-fee", hooks)
        official_lineage = {"document_type": f"{PRODUCT}_{COMPONENT_OFFICIAL_FEE}_lineage", "schema_version": 1, "required_product": PRODUCT, "component": COMPONENT_OFFICIAL_FEE, "row_count": 0, "schema_sha256": SCHEMA_IDENTITIES[COMPONENT_OFFICIAL_FEE], "parquet_path": str(official_path.relative_to(tree.root)), "parquet_sha256": official_sha, "parquet_bytes": official_bytes, "authority_state": "historical_fee_schedule_unavailable"}
        official_lineage_path, official_lineage_sha, official_lineage_bytes, official_lineage_reused = _publish_json(tree, official_lineage, (".lineage", COMPONENT_OFFICIAL_FEE, "__schema__", "schema"), "official-fee-lineage", hooks)
        published.append(PublishedComponent(COMPONENT_OFFICIAL_FEE, "__schema__", "schema", 0, official_path, official_sha, official_bytes, official_lineage_path, official_lineage_sha, official_lineage_bytes, (), official_reused and official_lineage_reused))

        for identity in memberships:
            row = {**identity.row(), "required_product": PRODUCT, "gap_kind": FEE_GAP_KIND, "gap_status": FEE_GAP_KIND, "blocking": False, "authority_class": FEE_AUTHORITY_CLASS, "explained_by": "no_free_reproducible_historical_fee_authority"}
            table = pa.Table.from_pylist([row], schema=SCHEMAS[COMPONENT_FEE_GAP])
            gap_path, gap_sha, gap_bytes, reused = _publish_table(tree, table, "fee-gap", (".partitions", COMPONENT_FEE_GAP, identity.native_symbol, "authority"), "fee-gap", hooks)
            lineage = {"document_type": f"{PRODUCT}_{COMPONENT_FEE_GAP}_lineage", "schema_version": 1, "required_product": PRODUCT, "component": COMPONENT_FEE_GAP, "native_symbol": identity.native_symbol, "row_count": 1, "schema_sha256": SCHEMA_IDENTITIES[COMPONENT_FEE_GAP], "membership_completion_sha256": MEMBERSHIP_COMPLETION_SHA256, "parquet_path": str(gap_path.relative_to(tree.root)), "parquet_sha256": gap_sha, "parquet_bytes": gap_bytes}
            lineage_path, lineage_sha, lineage_bytes, lineage_reused = _publish_json(tree, lineage, (".lineage", COMPONENT_FEE_GAP, identity.native_symbol, "authority"), "fee-gap-lineage", hooks)
            published.append(PublishedComponent(COMPONENT_FEE_GAP, identity.native_symbol, "authority", 1, gap_path, gap_sha, gap_bytes, lineage_path, lineage_sha, lineage_bytes, (), reused and lineage_reused))

        scenario_table = pa.Table.from_pylist(list(fee_scenario_rows()), schema=SCHEMAS[COMPONENT_SCENARIO])
        scenario_path, scenario_sha, scenario_bytes, scenario_reused = _publish_table(tree, scenario_table, "scenario", (".partitions", COMPONENT_SCENARIO, "BINANCE_USDM", "configuration"), "scenario", hooks)
        scenario_lineage = {"document_type": f"{PRODUCT}_{COMPONENT_SCENARIO}_lineage", "schema_version": 1, "required_product": PRODUCT, "component": COMPONENT_SCENARIO, "row_count": 2, "schema_sha256": SCHEMA_IDENTITIES[COMPONENT_SCENARIO], "policy_known_at": FEE_POLICY_KNOWN_AT, "historical_observation": False, "parquet_path": str(scenario_path.relative_to(tree.root)), "parquet_sha256": scenario_sha, "parquet_bytes": scenario_bytes}
        scenario_lineage_path, scenario_lineage_sha, scenario_lineage_bytes, scenario_lineage_reused = _publish_json(tree, scenario_lineage, (".lineage", COMPONENT_SCENARIO, "BINANCE_USDM", "configuration"), "scenario-lineage", hooks)
        published.append(PublishedComponent(COMPONENT_SCENARIO, "BINANCE_USDM", "configuration", 2, scenario_path, scenario_sha, scenario_bytes, scenario_lineage_path, scenario_lineage_sha, scenario_lineage_bytes, (), scenario_reused and scenario_lineage_reused))

        enriched_gaps: list[dict[str, Any]] = []
        for gap in source_gaps:
            symbol = gap.get("symbol")
            _require(type(symbol) is str and symbol in identities, "cost source gap is outside membership")
            enriched_gaps.append({**dict(gap), "membership": identities[symbol].row()})
        gap_document = {"document_type": f"{PRODUCT}_frozen_source_gaps", "schema_version": 1, "required_product": PRODUCT, "manifest_sha256": COST_MANIFEST_SHA256, "row_count": len(enriched_gaps), "gaps": enriched_gaps}
        source_gap_path, source_gap_sha, source_gap_bytes, _ = _publish_json(tree, gap_document, (".source-gaps",), "source-gaps", hooks)
        source_rows = sum(item.row_count for item in published if item.component in (COMPONENT_TICKER, COMPONENT_DEPTH))
        physical_rows, source_row_facts = _source_row_reconciliation(ordered, published)
        _require(physical_rows == source_rows, "physical and retained source rows differ")
        _enforce_component_bounds(published)
        if enforce_full_corpus:
            _require(len(ordered) == ACCEPTED_COST_OBJECTS and sum(source.byte_size for source in ordered) == ACCEPTED_COST_BYTES, "full cost source equation changed")
            _require(Counter(source.family for source in ordered) == Counter({FAMILY_TICKER: ACCEPTED_TICKER_OBJECTS, FAMILY_DEPTH: ACCEPTED_DEPTH_OBJECTS}), "full cost family equation changed")
            _require(len(memberships) == ACCEPTED_FEE_AUTHORITY_GAPS and len(source_gaps) == ACCEPTED_SOURCE_GAPS, "full cost gap equation changed")
            _require(len(published) <= PROJECTED_PARTITIONS, "cost partition projection exceeded")
        completion = {
            "document_type": f"{PRODUCT}_product_completion",
            "schema_version": 1,
            "required_product": PRODUCT,
            "schema_sha256": SCHEMA_SHA256,
            "component_schemas": SCHEMA_IDENTITIES,
            "writer_identity": writer_identity(),
            "normalizer_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "authority_sha256": {"report": report_sha256, "sizing": sizing_sha256, "cost_manifest": COST_MANIFEST_SHA256, "generation0_seal": GENERATION0_SEAL, "v3_manifest": V3_MANIFEST_SHA256, "membership_completion": MEMBERSHIP_COMPLETION_SHA256},
            "source_equation": {"objects": len(ordered), "compressed_bytes": sum(source.byte_size for source in ordered), "generation0_objects": sum(source.authority == "accepted_generation_0_completion" for source in ordered), "recovery_objects": sum(source.authority == "accepted_v3_direct_recovery" for source in ordered), "physical_rows": physical_rows, "retained_rows": source_rows, "dropped_rows": physical_rows - source_rows, "deduplicated_rows": 0},
            "source_row_reconciliation": list(source_row_facts),
            "component_rows": {component: sum(item.row_count for item in published if item.component == component) for component in COST_COMPONENTS},
            "quote_states": dict(sorted(quote_states.items())),
            "fee_authority": {"official_historical_rows": 0, "gap_rows": len(memberships), "gap_kind": FEE_GAP_KIND, "missing_fee_is_zero": False},
            "scenario_policy": {"rows": 2, "policy_known_at": FEE_POLICY_KNOWN_AT, "authority_class": FEE_AUTHORITY_CLASS, "historical_observation": False, "historical_upper_bound": False, "charges_each_side": True},
            "frozen_source_gaps": {"row_count": len(source_gaps), "path": str(source_gap_path.relative_to(tree.root)), "sha256": source_gap_sha, "bytes": source_gap_bytes},
            "partition_count": len(published),
            "projected_partition_ceiling": PROJECTED_PARTITIONS,
            "normalized_allocation_bytes": NORMALIZED_ALLOCATION_BYTES,
            "partitions": [{"component": item.component, "native_symbol": item.native_symbol, "utc_month": item.utc_month, "row_count": item.row_count, "parquet_path": str(item.parquet_path.relative_to(tree.root)), "parquet_sha256": item.parquet_sha256, "parquet_bytes": item.parquet_bytes, "lineage_path": str(item.lineage_path.relative_to(tree.root)), "lineage_sha256": item.lineage_sha256, "lineage_bytes": item.lineage_bytes} for item in published],
        }
        parquet_bytes = sum(item.parquet_bytes for item in published)
        lineage_bytes = sum(item.lineage_bytes for item in published)
        noncompletion_bytes = parquet_bytes + lineage_bytes + source_gap_bytes
        completion["measured_output_bytes"] = {
            "parquet": parquet_bytes,
            "lineage": lineage_bytes,
            "source_gaps": source_gap_bytes,
            "completion": 0,
            "total": 0,
        }
        for _attempt in range(16):
            completion_bytes = len(_canonical_json(completion))
            total_bytes = noncompletion_bytes + completion_bytes
            measurement = completion["measured_output_bytes"]
            assert type(measurement) is dict
            if (
                measurement["completion"] == completion_bytes
                and measurement["total"] == total_bytes
            ):
                break
            measurement["completion"] = completion_bytes
            measurement["total"] = total_bytes
        else:
            raise CostCalibrationError("completion byte measurement did not stabilize")
        _require(total_bytes <= NORMALIZED_ALLOCATION_BYTES, "cost normalized allocation exceeded")
        digest = hashlib.sha256(_canonical_json(completion)).hexdigest()
        tree.only_completion(f"{digest}.json")
        prospective_completion = tree.root / ".complete" / f"{digest}.json"
        _reprove_output(
            tree,
            published,
            (source_gap_path, source_gap_sha, source_gap_bytes),
            (prospective_completion, digest, completion_bytes),
            completion_required=False,
        )
        completion_path, completion_sha, published_completion_bytes, completion_reused = _publish_json(tree, completion, (".complete",), "completion", hooks)
        _require(published_completion_bytes == completion_bytes, "completion byte measurement changed")
        tree.only_completion(f"{digest}.json")
        _reprove_output(
            tree,
            published,
            (source_gap_path, source_gap_sha, source_gap_bytes),
            (completion_path, completion_sha, completion_bytes),
            completion_required=True,
        )
        return CostCalibrationResult(PRODUCT, SCHEMA_SHA256, tuple(published), completion_path, completion_sha, completion_reused, len(ordered), source_rows)
    finally:
        tree.close()


def normalize_from_authorities(*, report_path: Path, sizing_path: Path, generation0_state: Path, generation0_content_root: Path, v3_manifest: Path, recovery_root: Path, membership_root: Path, output_root: Path, hooks: PublicationHooks = PublicationHooks()) -> CostCalibrationResult:
    report = _read_pinned(report_path, REPORT_SHA256, MAX_REPORT_BYTES)
    sizing = _read_pinned(sizing_path, SIZING_SHA256, MAX_SIZING_BYTES)
    selected, gaps = _report_manifest(report)
    _validate_sizing(sizing)
    generation0 = load_generation0_cost_sources(generation0_state, generation0_content_root, selected)
    recovery = load_recovery_cost_sources(v3_manifest, recovery_root, selected)
    sources = tuple(sorted((*generation0, *recovery), key=lambda source: source.source_key))
    _require(len(sources) == ACCEPTED_COST_OBJECTS and {source.source_key for source in sources} == selected, "authority union does not equal frozen cost manifest")
    _require(not ({source.source_key for source in generation0} & {source.source_key for source in recovery}), "cost authorities overlap")
    _manifest_reproof(sources, gaps)
    memberships = load_membership_identities(membership_root)
    return normalize_cost_sources(sources, memberships, gaps, output_root, enforce_full_corpus=True, hooks=hooks)
