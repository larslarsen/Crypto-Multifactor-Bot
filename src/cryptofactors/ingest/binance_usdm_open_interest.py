"""Concrete Gate-3 normalizer for Binance USD-M five-minute open interest.

This module deliberately implements one product, not a normalization framework.  It reads
the two Gate-2 authorities without mutating them, authenticates every consumed object, and
publishes only hidden, content-addressed Parquet partitions and their lineage manifests.
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
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    KNOWN_ARCHIVE_SCHEMAS,
)
from cryptofactors.acquisition.binance_usdm_harmonic_acquisition import (
    OUTCOME_CHECKSUM_VERIFIED,
    OUTCOME_RETAINED,
    STATE_APPLICATION_ID,
    STATE_USER_VERSION,
    AcquisitionState,
    register_domain_functions,
)
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    DECIMAL_SCALE,
    FAMILY_CADENCE_SECONDS,
    PARQUET_COMPRESSION,
    PARQUET_COMPRESSION_LEVEL,
    PARQUET_VERSION,
    PRODUCT_OPEN_INTEREST_5M,
    QUALITY_GAP_COLUMNS,
    SIZING_ROW_BATCH,
    convert_decimal,
    convert_timestamp_text,
    final_product_schema,
    native_identity,
    product_schema_identity,
    writer_identity,
)

PRODUCT = PRODUCT_OPEN_INTEREST_5M
FAMILY = "daily/metrics"
EXPECTED_CADENCE_SECONDS = FAMILY_CADENCE_SECONDS[FAMILY]
METRICS_FIELDS = KNOWN_ARCHIVE_SCHEMAS["metrics"]["headerless"]
SCHEMA = final_product_schema(PRODUCT)
SCHEMA_SHA256 = product_schema_identity(PRODUCT)

PROVIDER_CONFLICT_UNAVAILABLE = "PROVIDER_CHECKSUM_CONFLICT_UNAVAILABLE"
HBAR_CONFLICT_KEY = (
    "data/futures/um/daily/metrics/HBARUSDC/"
    "HBARUSDC-metrics-2026-07-09.zip"
)
HBAR_EXPECTED_SHA256 = "060025bb8887f2c0456d3333fb3a70001f3dfa5662132b0f895a7f3d3247bd52"
HBAR_SERVED_SHA256 = "8d6e3d3efff6e615be11e43c22df3ecda579aeeb45b3da41c88a65662b5e2cc5"
HBAR_LISTED_BYTES = 9_810
HBAR_ETAG = "d7f563900c0c2c99b7fd066e02d404c4"

# These are independent parser safety limits, not the retired raw-download expansion
# ceiling.  They comfortably exceed a production daily metrics member while bounding
# both decompression work and row cardinality.
MAX_COMPRESSED_OBJECT_BYTES = 256 * 2**20
MAX_DECOMPRESSED_MEMBER_BYTES = 512 * 2**20
MAX_ROWS_PER_OBJECT = 2_000_000
MAX_CSV_FIELD_BYTES = 1 * 2**20
RENAME_NOREPLACE = 1
ACCEPTED_GENERATION0_BINANCE_COMPLETIONS = 685_072
ACCEPTED_V3_ROWS = 51_275
ACCEPTED_V3_BYTES = 9_207_379_061
ACCEPTED_V3_METRICS_ROWS = 50_921
ACCEPTED_V3_BOOK_TICKER_ROWS = 354
ACCEPTED_V3_MANIFEST_SHA256 = "4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d"
ACCEPTED_GENERATION0_METRICS_COMPLETIONS = 522_865
ACCEPTED_GENERATION0_SEAL_HEAD = "8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab"
QUALITY_GAP_SCHEMA = pa.schema([column.field() for column in QUALITY_GAP_COLUMNS])

_KEY_RE = re.compile(
    r"data/futures/um/daily/metrics/(?P<symbol>[A-Z0-9_]+)/"
    r"(?P=symbol)-metrics-(?P<date>\d{4}-\d{2}-\d{2})\.zip"
)
_HEX_RE = re.compile(r"[0-9a-f]{64}")


class OpenInterestNormalizationError(RuntimeError):
    """Fail-closed input, typing, lineage, or publication error."""


@dataclass(frozen=True, slots=True)
class RawMetricObject:
    """One authenticated raw object supplied by an accepted Gate-2 authority."""

    source_key: str
    path: Path
    source_sha256: str
    byte_size: int
    authority: str
    checksum_authority: str
    retrieval_time: str | None = None
    source_available_at: int | None = None


@dataclass(frozen=True, slots=True)
class CoverageGap:
    product: str
    native_symbol: str
    economic_interval: str
    source_key: str
    outcome: str
    expected_provider_sha256: str
    observed_sha256: str
    listed_bytes: int
    etag: str
    continuity_break: bool


@dataclass(frozen=True, slots=True)
class PublishedPartition:
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
    row_count: int
    parquet_path: Path
    parquet_sha256: str
    lineage_path: Path
    lineage_sha256: str
    reused: bool


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    product: str
    schema_sha256: str
    writer_identity: str
    partitions: tuple[PublishedPartition, ...]
    gaps: tuple[CoverageGap, ...]
    gap_artifact: PublishedGapArtifact
    completion_path: Path
    completion_sha256: str
    completion_reused: bool


@dataclass(frozen=True, slots=True)
class PublicationHooks:
    """Test-only interruption boundary; production callers leave it unset."""

    before_publish: Callable[[str, Path, Path], None] | None = None


HBAR_CONFLICT_GAP = CoverageGap(
    product=PRODUCT,
    native_symbol="HBARUSDC",
    economic_interval="2026-07-09",
    source_key=HBAR_CONFLICT_KEY,
    outcome=PROVIDER_CONFLICT_UNAVAILABLE,
    expected_provider_sha256=HBAR_EXPECTED_SHA256,
    observed_sha256=HBAR_SERVED_SHA256,
    listed_bytes=HBAR_LISTED_BYTES,
    etag=HBAR_ETAG,
    continuity_break=True,
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise OpenInterestNormalizationError(message)


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


def _identity_parts(key: str) -> tuple[str, str]:
    match = _KEY_RE.fullmatch(key)
    _require(match is not None, "raw metrics identity is not canonical")
    assert match is not None
    try:
        economic_date = datetime.strptime(match.group("date"), "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise OpenInterestNormalizationError("raw metrics identity has an invalid date") from exc
    _require(economic_date == match.group("date"), "raw metrics identity date is not canonical")
    return match.group("symbol"), economic_date


def _safe_authority_file(root: Path, relative: PurePosixPath) -> Path:
    _require(not relative.is_absolute() and ".." not in relative.parts, "authority path escapes its root")
    root = root.resolve(strict=True)
    current = root
    for part in relative.parts:
        current = current / part
        try:
            facts = current.lstat()
        except OSError as exc:
            raise OpenInterestNormalizationError("authority object is not reachable") from exc
        _require(not stat.S_ISLNK(facts.st_mode), "authority path contains a symlink")
    _require(current.is_file(), "authority object is not a regular file")
    _require(current.resolve(strict=True).is_relative_to(root), "authority path escapes its root")
    return current


def _require_no_symlink_components(path: Path, *, label: str) -> None:
    absolute = path.absolute()
    for component in reversed((absolute, *absolute.parents)):
        if not component.exists() and not component.is_symlink():
            continue
        try:
            facts = component.lstat()
        except OSError as exc:
            raise OpenInterestNormalizationError(f"{label} cannot be inspected safely") from exc
        _require(not stat.S_ISLNK(facts.st_mode), f"{label} contains a symlink")


def _safe_component(value: str) -> str:
    _require(bool(value) and value not in {".", ".."} and "/" not in value and "\\" not in value, "output child name is unsafe")
    return value


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


def _rename_noreplace_at(old_dir: int, old_name: str, new_dir: int, new_name: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        renameat2 = libc.renameat2
    except AttributeError as exc:
        raise OpenInterestNormalizationError("atomic no-replace rename is unavailable") from exc
    renameat2.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    renameat2.restype = ctypes.c_int
    result = renameat2(old_dir, os.fsencode(old_name), new_dir, os.fsencode(new_name), RENAME_NOREPLACE)
    if result:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), new_name)


class _OutputTree:
    """One held no-follow output tree used for every child operation."""

    def __init__(self, root: Path) -> None:
        _require_no_symlink_components(root, label="output root")
        if not root.exists():
            root.mkdir(mode=0o700)
            _fsync_directory(root.parent)
        self.root = root.resolve(strict=True)
        try:
            self.root_fd = os.open(
                self.root,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
        except OSError as exc:
            raise OpenInterestNormalizationError("output root cannot be held no-follow") from exc
        _require(stat.S_ISDIR(os.fstat(self.root_fd).st_mode), "output root is not a directory")
        try:
            fcntl.flock(self.root_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self.root_fd)
            raise OpenInterestNormalizationError("another normalizer holds the output root") from exc
        self.root_facts = os.fstat(self.root_fd)
        try:
            staging = self.directory((".staging",), create=True)
            os.close(staging)
        except Exception:
            os.close(self.root_fd)
            raise

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
                    raise OpenInterestNormalizationError("output child directory is unsafe") from exc
                if not stat.S_ISDIR(os.fstat(child).st_mode):
                    os.close(child)
                    raise OpenInterestNormalizationError("output child is not a directory")
                os.close(current)
                current = child
            return current
        except Exception:
            os.close(current)
            raise

    def stage(self, prefix: str) -> tuple[str, int, Path]:
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
        _require(stat.S_ISREG(os.fstat(descriptor).st_mode), "output staging leaf is not regular")
        return name, descriptor, self.root / ".staging" / name

    def open_final(self, parts: Sequence[str], name: str) -> int:
        directory = self.directory(parts, create=False)
        try:
            descriptor = os.open(
                _safe_component(name),
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=directory,
            )
        except OSError as exc:
            raise OpenInterestNormalizationError("published output cannot be opened no-follow") from exc
        finally:
            os.close(directory)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise OpenInterestNormalizationError("published output is not regular")
        return descriptor

    def publish(
        self,
        stage_name: str,
        stage_fd: int,
        destination_parts: Sequence[str],
        destination_name: str,
        *,
        kind: str,
        hooks: PublicationHooks,
    ) -> tuple[bool, int, Path]:
        staging = self.directory((".staging",), create=False)
        destination = self.directory(destination_parts, create=True)
        path = self.root.joinpath(*destination_parts, destination_name)
        try:
            if hooks.before_publish is not None:
                hooks.before_publish(kind, self.root / ".staging" / stage_name, path)
            try:
                _rename_noreplace_at(staging, stage_name, destination, destination_name)
                os.fsync(destination)
                os.fsync(staging)
                reused = False
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise OpenInterestNormalizationError("content-addressed publication failed") from exc
                winner = os.open(
                    destination_name,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=destination,
                )
                try:
                    _require(stat.S_ISREG(os.fstat(winner).st_mode), "publication winner is not regular")
                    _require(_same_fds(stage_fd, winner), "content-addressed replay differs from existing bytes")
                finally:
                    os.close(winner)
                os.unlink(stage_name, dir_fd=staging)
                os.fsync(staging)
                reused = True
            final_fd = os.open(
                destination_name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=destination,
            )
            if not stat.S_ISREG(os.fstat(final_fd).st_mode):
                os.close(final_fd)
                raise OpenInterestNormalizationError("published output is not regular")
            return reused, final_fd, path
        finally:
            os.close(destination)
            os.close(staging)

    def verify_paths(self, paths: Iterable[Path]) -> None:
        current = os.open(
            self.root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        try:
            facts = os.fstat(current)
            _require(
                (facts.st_dev, facts.st_ino) == (self.root_facts.st_dev, self.root_facts.st_ino),
                "held output root was replaced",
            )
        finally:
            os.close(current)
        for path in paths:
            _require(path.is_relative_to(self.root), "returned output path escapes held root")
            relative = path.relative_to(self.root)
            descriptor = self.open_final(relative.parts[:-1], relative.name)
            os.close(descriptor)

    def require_only_entry(self, parts: Sequence[str], name: str) -> None:
        directory = self.directory(parts, create=True)
        try:
            entries = os.listdir(directory)
        finally:
            os.close(directory)
        _require(
            not [entry for entry in entries if entry != name],
            "a different product-completion descriptor already exists",
        )


def _open_regular_child(directory: int, name: str, *, label: str) -> int | None:
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise OpenInterestNormalizationError(f"{label} cannot be opened no-follow") from exc
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise OpenInterestNormalizationError(f"{label} is not a regular file")
    return descriptor


def _require_fixed_generation0_terminal(state: AcquisitionState) -> dict[str, Any]:
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
        "generation-0 run-7 seal head changed",
    )
    return head


def _require_accepted_generation0_validation_state(state: object) -> None:
    _require(
        type(state) is str and state in (OUTCOME_CHECKSUM_VERIFIED, OUTCOME_RETAINED),
        "generation-0 metrics completion validation state is not accepted",
    )


def load_generation0_sources(
    state_path: Path,
    content_root: Path,
) -> tuple[RawMetricObject, ...]:
    """Read accepted checksum-verified metrics completions in one read-only snapshot."""
    _require_no_symlink_components(state_path, label="generation-0 state path")
    _require_no_symlink_components(content_root, label="generation-0 content root")
    parent = state_path.absolute().parent
    name = state_path.name
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    state_fd: int | None = None
    sidecars: dict[str, int | None] = {}
    try:
        state_fd = _open_regular_child(parent_fd, name, label="generation-0 SQLite state")
        _require(state_fd is not None, "generation-0 SQLite state is missing")
        sidecar_names = (f"{name}-wal", f"{name}-shm", f"{name}-journal")
        for sidecar in sidecar_names:
            sidecars[sidecar] = _open_regular_child(
                parent_fd, sidecar, label=f"SQLite sidecar {sidecar}"
            )
    except Exception:
        for descriptor in sidecars.values():
            if descriptor is not None:
                os.close(descriptor)
        if state_fd is not None:
            os.close(state_fd)
        os.close(parent_fd)
        raise
    assert state_fd is not None
    uri = f"file:/proc/self/fd/{parent_fd}/{name}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, isolation_level=None)
        reopened = _open_regular_child(parent_fd, name, label="generation-0 SQLite state")
        _require(reopened is not None, "generation-0 SQLite state disappeared")
        assert reopened is not None
        try:
            first = os.fstat(state_fd)
            second = os.fstat(reopened)
            _require((first.st_dev, first.st_ino) == (second.st_dev, second.st_ino), "generation-0 SQLite state was replaced")
        finally:
            os.close(reopened)
        for sidecar, before in sidecars.items():
            after = _open_regular_child(parent_fd, sidecar, label=f"SQLite sidecar {sidecar}")
            if before is None:
                _require(after is None, "a SQLite sidecar appeared during read-only open")
            else:
                _require(after is not None, "a SQLite sidecar disappeared during read-only open")
                assert after is not None
                old = os.fstat(before)
                new = os.fstat(after)
                _require((old.st_dev, old.st_ino) == (new.st_dev, new.st_ino), "a SQLite sidecar was replaced")
            if after is not None:
                os.close(after)
        register_domain_functions(connection)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN")
        app = int(connection.execute("PRAGMA application_id").fetchone()[0])
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        _require(app == STATE_APPLICATION_ID, "generation-0 SQLite application_id changed")
        _require(version == STATE_USER_VERSION, "generation-0 SQLite user_version changed")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        _require(integrity is not None and str(integrity[0]) == "ok", "generation-0 SQLite integrity check failed")
        _require(not connection.execute("PRAGMA foreign_key_check").fetchall(), "generation-0 SQLite foreign keys do not reconcile")
        borrowed = AcquisitionState(state_path, state_path.with_name("acquisition.lock"))
        borrowed.conn = connection
        _require_fixed_generation0_terminal(borrowed)
        completion_count = connection.execute(
            "SELECT COUNT(*) FROM completion WHERE provider='binance_vision'"
        ).fetchone()
        _require(
            completion_count is not None
            and int(completion_count[0]) == ACCEPTED_GENERATION0_BINANCE_COMPLETIONS,
            "generation-0 Binance completion count changed",
        )
        metrics_count = connection.execute(
            "SELECT COUNT(*) FROM completion c JOIN plan_entry p "
            "ON p.provider=c.provider AND p.identity=c.identity "
            "WHERE c.provider='binance_vision' "
            "AND json_extract(p.payload_json,'$.payload.family')='daily/metrics'"
        ).fetchone()
        _require(
            metrics_count is not None
            and int(metrics_count[0]) == ACCEPTED_GENERATION0_METRICS_COMPLETIONS,
            "generation-0 metrics completion count changed",
        )
        rows = connection.execute(
            "SELECT p.identity,p.payload_json,c.content_sha256,c.listed_bytes,"
            "c.retrieved_at,c.validation_state,s.provider_checksum "
            "FROM plan_entry p JOIN completion c ON c.provider=p.provider AND c.identity=p.identity "
            "JOIN sidecar_fact s ON s.provider=p.provider AND s.identity=p.identity "
            "WHERE p.provider='binance_vision' ORDER BY p.identity"
        )
        accepted: list[RawMetricObject] = []
        for identity, payload_json, content_sha, listed_bytes, retrieved_at, state, provider_sha in rows:
            try:
                envelope = json.loads(str(payload_json))
            except json.JSONDecodeError as exc:
                raise OpenInterestNormalizationError("generation-0 plan payload is invalid JSON") from exc
            payload = envelope.get("payload") if type(envelope) is dict else None
            if type(payload) is not dict or payload.get("family") != FAMILY:
                continue
            _identity_parts(str(identity))
            digest = str(content_sha)
            _require(_HEX_RE.fullmatch(digest) is not None, "generation-0 content digest is invalid")
            _require(str(provider_sha) == digest, "generation-0 provider/content digest conflict")
            _require_accepted_generation0_validation_state(state)
            path = _safe_authority_file(content_root, PurePosixPath(digest[:2], digest))
            accepted.append(
                RawMetricObject(
                    source_key=str(identity),
                    path=path,
                    source_sha256=digest,
                    byte_size=int(listed_bytes),
                    authority="accepted_generation_0_completion",
                    checksum_authority="binance_checksum_sidecar",
                    retrieval_time=str(retrieved_at),
                )
            )
        _require(
            len(accepted) == ACCEPTED_GENERATION0_METRICS_COMPLETIONS,
            "generation-0 selected metrics mapping count changed",
        )
        connection.execute("ROLLBACK")
        borrowed.conn = None
        return tuple(accepted)
    except sqlite3.Error as exc:
        raise OpenInterestNormalizationError("generation-0 authority cannot be read safely") from exc
    finally:
        if "connection" in locals():
            if "borrowed" in locals():
                borrowed.conn = None
            connection.close()
        for descriptor in sidecars.values():
            if descriptor is not None:
                os.close(descriptor)
        os.close(state_fd)
        os.close(parent_fd)


def load_v3_recovery_sources(
    manifest_path: Path,
    recovery_root: Path,
) -> tuple[RawMetricObject, ...]:
    """Read the accepted v3 JSONL manifest and bind each usable metrics identity."""
    accepted: list[RawMetricObject] = []
    seen: set[str] = set()
    _require_no_symlink_components(manifest_path, label="v3 manifest path")
    _require_no_symlink_components(recovery_root, label="v3 recovery root")
    compressed_sha, _manifest_size = _digest_path(manifest_path)
    _require(compressed_sha == ACCEPTED_V3_MANIFEST_SHA256, "v3 manifest digest is not the accepted authority")
    _require(
        manifest_path.name == f"{compressed_sha}.json.gz",
        "v3 manifest name is not its compressed content address",
    )
    row_count = 0
    listed_bytes = 0
    family_counts = {FAMILY: 0, "daily/bookTicker": 0}
    try:
        with gzip.open(manifest_path, "rt", encoding="utf-8", newline="") as handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    envelope = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise OpenInterestNormalizationError("v3 manifest contains invalid JSON") from exc
                if type(envelope) is not dict or envelope.get("record_type") != "row":
                    raise OpenInterestNormalizationError("v3 manifest row envelope changed")
                record = envelope.get("record")
                if type(record) is not dict:
                    raise OpenInterestNormalizationError("v3 manifest record is not an object")
                family = record.get("family")
                _require(family in family_counts, "v3 manifest contains an unauthorized family")
                size = record.get("current_listed_bytes")
                _require(type(size) is int and size > 0, "v3 manifest listed size is invalid")
                row_count += 1
                listed_bytes += size
                family_counts[str(family)] += 1
                if record.get("family") != FAMILY:
                    continue
                identity = str(record.get("identity") or "")
                _identity_parts(identity)
                _require(identity not in seen, "v3 manifest repeats a metrics identity")
                seen.add(identity)
                if identity == HBAR_CONFLICT_KEY:
                    _require(str(record.get("provider_checksum")) == HBAR_EXPECTED_SHA256, "HBAR conflict authority changed")
                    _require(int(record.get("current_listed_bytes", -1)) == HBAR_LISTED_BYTES, "HBAR conflict size changed")
                    continue
                digest = str(record.get("provider_checksum") or "")
                _require(_HEX_RE.fullmatch(digest) is not None, "v3 provider digest is invalid")
                _require(type(size) is int and 0 < size <= MAX_COMPRESSED_OBJECT_BYTES, "v3 metrics size is invalid")
                path = _safe_authority_file(recovery_root, PurePosixPath(identity))
                accepted.append(
                    RawMetricObject(
                        source_key=identity,
                        path=path,
                        source_sha256=digest,
                        byte_size=size,
                        authority="accepted_v3_direct_recovery",
                        checksum_authority="binance_checksum_sidecar",
                    )
                )
    except (OSError, UnicodeError) as exc:
        raise OpenInterestNormalizationError("v3 manifest cannot be read safely") from exc
    _require(row_count == ACCEPTED_V3_ROWS, "v3 manifest row count changed")
    _require(listed_bytes == ACCEPTED_V3_BYTES, "v3 manifest listed-byte equation changed")
    _require(family_counts[FAMILY] == ACCEPTED_V3_METRICS_ROWS, "v3 metrics row count changed")
    _require(
        family_counts["daily/bookTicker"] == ACCEPTED_V3_BOOK_TICKER_ROWS,
        "v3 book-ticker row count changed",
    )
    _require(HBAR_CONFLICT_KEY in seen, "v3 manifest is missing the fixed HBAR conflict")
    _require(
        len(accepted) == ACCEPTED_V3_METRICS_ROWS - 1,
        "v3 usable metrics mapping count changed",
    )
    return tuple(accepted)


def _safe_zip_member(archive: zipfile.ZipFile, *, source_key: str) -> zipfile.ZipInfo:
    members = archive.infolist()
    _require(len(members) == 1, "metrics ZIP must contain exactly one member")
    member = members[0]
    name = member.filename
    parts = PurePosixPath(name.replace("\\", "/"))
    _require(bool(name) and not parts.is_absolute() and ".." not in parts.parts, "metrics ZIP member path is unsafe")
    _require(len(parts.parts) == 1 and name.lower().endswith(".csv"), "metrics ZIP member is not one root CSV")
    mode = member.external_attr >> 16
    file_type = stat.S_IFMT(mode)
    _require(file_type in {0, stat.S_IFREG}, "metrics ZIP member is not a regular file")
    _require(not (member.flag_bits & 0x1), "encrypted metrics ZIP is unsupported")
    _require(member.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}, "metrics ZIP compression is unsupported")
    _require(0 < member.file_size <= MAX_DECOMPRESSED_MEMBER_BYTES, "metrics ZIP member exceeds its parser bound")
    _require(member.compress_size <= MAX_COMPRESSED_OBJECT_BYTES, "metrics ZIP compressed member exceeds its bound")
    expected_name = source_key.rsplit("/", 1)[-1][:-4] + ".csv"
    _require(name == expected_name, "metrics ZIP member name does not match its source identity")
    return member


def _iter_metric_rows(source: RawMetricObject) -> Iterator[tuple[int, list[str]]]:
    try:
        with zipfile.ZipFile(source.path) as archive:
            member = _safe_zip_member(archive, source_key=source.source_key)
            with archive.open(member, "r") as raw:
                stream = io.TextIOWrapper(raw, encoding="utf-8", newline="")
                reader = csv.reader(stream, strict=True)
                decompressed = 0
                ordinal = 0
                first = True
                for physical_row in reader:
                    decompressed += sum(len(cell.encode("utf-8")) for cell in physical_row) + len(physical_row)
                    _require(decompressed <= MAX_DECOMPRESSED_MEMBER_BYTES, "metrics ZIP expanded beyond its parser bound")
                    _require(all(len(cell.encode("utf-8")) <= MAX_CSV_FIELD_BYTES for cell in physical_row), "metrics CSV field exceeds its bound")
                    if first:
                        first = False
                        if tuple(cell.strip() for cell in physical_row) == METRICS_FIELDS:
                            continue
                    _require(bool(physical_row), "metrics CSV contains an empty row")
                    _require(len(physical_row) == len(METRICS_FIELDS), "metrics CSV row width is invalid")
                    _require(ordinal < MAX_ROWS_PER_OBJECT, "metrics CSV exceeds its row bound")
                    yield ordinal, [str(cell) for cell in physical_row]
                    ordinal += 1
                _require(ordinal > 0, "metrics CSV contains no data rows")
    except (OSError, UnicodeError, csv.Error, zipfile.BadZipFile, RuntimeError) as exc:
        if isinstance(exc, OpenInterestNormalizationError):
            raise
        raise OpenInterestNormalizationError("metrics ZIP/CSV is invalid") from exc


def _decimal(token: str, source: RawMetricObject, column: str, ordinal: int, *, nullable: bool = False) -> Decimal | None:
    if nullable and not token.strip():
        return None
    try:
        value = convert_decimal(token, key=source.source_key, output=PRODUCT, column=column, row=ordinal)
        _require(value >= 0, f"metrics {column} cannot be negative")
        return value
    except Exception as exc:
        raise OpenInterestNormalizationError(f"metrics {column} is not an exact accepted decimal") from exc


def _timestamp(token: str, source: RawMetricObject, ordinal: int) -> int:
    try:
        value = convert_timestamp_text(token, key=source.source_key, output=PRODUCT, column="create_time", row=ordinal)
    except Exception as exc:
        raise OpenInterestNormalizationError("metrics create_time is invalid") from exc
    _require(value % 1000 == 0, "metrics create_time has subsecond precision")
    _require(value % (EXPECTED_CADENCE_SECONDS * 1000) == 0, "metrics create_time is off the five-minute grid")
    return value


def _unscaled(value: Decimal) -> int:
    parts = value.as_tuple()
    coefficient = int("".join(str(digit) for digit in parts.digits) or "0")
    if parts.exponent < -DECIMAL_SCALE:
        raise OpenInterestNormalizationError("decimal exceeds pinned scale")
    coefficient *= 10 ** (parts.exponent + DECIMAL_SCALE)
    return -coefficient if parts.sign else coefficient


def _scaled(value: int) -> Decimal:
    sign = 1 if value < 0 else 0
    digits = tuple(int(char) for char in str(abs(value))) if value else (0,)
    _require(len(digits) <= 38, "derived decimal overflows pinned precision")
    return Decimal((sign, digits, -DECIMAL_SCALE))


def _row_values(
    source: RawMetricObject,
    raw_ref: int,
    ordinal: int,
    row: Sequence[str],
) -> dict[str, Any]:
    symbol, economic_date = _identity_parts(source.source_key)
    values = dict(zip(METRICS_FIELDS, row, strict=True))
    _require(values["symbol"].strip() == symbol, "metrics row symbol conflicts with source identity")
    moment = _timestamp(values["create_time"], source, ordinal)
    row_date = datetime.fromtimestamp(moment // 1000, tz=UTC).date().isoformat()
    _require(row_date == economic_date, "metrics row lies outside its source contract-day")
    return {
        "raw_object_ref": raw_ref,
        "source_row_ordinal": ordinal,
        "venue_symbol": symbol,
        "create_time": moment,
        "metric_symbol": symbol,
        "sum_open_interest": _decimal(values["sum_open_interest"], source, "sum_open_interest", ordinal),
        "sum_open_interest_value": _decimal(values["sum_open_interest_value"], source, "sum_open_interest_value", ordinal),
        "count_toptrader_long_short_ratio": _decimal(values["count_toptrader_long_short_ratio"], source, "count_toptrader_long_short_ratio", ordinal, nullable=True),
        "sum_toptrader_long_short_ratio": _decimal(values["sum_toptrader_long_short_ratio"], source, "sum_toptrader_long_short_ratio", ordinal, nullable=True),
        "count_long_short_ratio": _decimal(values["count_long_short_ratio"], source, "count_long_short_ratio", ordinal, nullable=True),
        "sum_taker_long_short_vol_ratio": _decimal(values["sum_taker_long_short_vol_ratio"], source, "sum_taker_long_short_vol_ratio", ordinal, nullable=True),
    }


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rewrite_fd(descriptor: int, body: bytes) -> None:
    os.ftruncate(descriptor, 0)
    os.lseek(descriptor, 0, os.SEEK_SET)
    view = memoryview(body)
    while view:
        written = os.write(descriptor, view)
        _require(written > 0, "staged output write was incomplete")
        view = view[written:]
    os.fsync(descriptor)


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


def _verify_parquet_fd(descriptor: int, *, expected_rows: int, expected_sha256: str, schema: pa.Schema) -> None:
    digest, _size = _hash_fd(descriptor)
    _require(digest == expected_sha256, "published Parquet digest changed")
    try:
        parquet = pq.ParquetFile(f"/proc/self/fd/{descriptor}")
    except (OSError, pa.ArrowInvalid) as exc:
        raise OpenInterestNormalizationError("published Parquet is unreadable") from exc
    _require(parquet.schema_arrow == schema, "published Parquet schema changed")
    _require(parquet.metadata.num_rows == expected_rows, "published Parquet row count changed")


def _lineage_source(source: RawMetricObject, raw_ref: int) -> dict[str, Any]:
    return {
        "raw_object_ref": raw_ref,
        "source_key": source.source_key,
        "source_sha256": source.source_sha256,
        "byte_size": source.byte_size,
        "authority": source.authority,
        "checksum_authority": source.checksum_authority,
        "retrieval_time": source.retrieval_time,
        "source_available_at": source.source_available_at,
    }


HBAR_GAP_START_MS = convert_timestamp_text(
    "2026-07-09T00:00:00Z",
    key=HBAR_CONFLICT_KEY,
    output=PRODUCT,
    column="missing_run_start_ms",
    row=0,
)
HBAR_GAP_POINTS = 288
HBAR_GAP_END_MS = HBAR_GAP_START_MS + (HBAR_GAP_POINTS - 1) * EXPECTED_CADENCE_SECONDS * 1000


def _quality_gap_row(
    symbol: str,
    start_ms: int,
    end_ms: int,
    *,
    gap_kind: str,
    reason: str,
) -> dict[str, Any]:
    _require(start_ms <= end_ms, "quality gap interval is reversed")
    step = EXPECTED_CADENCE_SECONDS * 1000
    _require(start_ms % step == 0 and end_ms % step == 0, "quality gap is off grid")
    start_month = datetime.fromtimestamp(start_ms // 1000, tz=UTC).strftime("%Y-%m")
    end_month = datetime.fromtimestamp(end_ms // 1000, tz=UTC).strftime("%Y-%m")
    _require(start_month == end_month, "quality gap row crosses a UTC month")
    return {
        **native_identity(symbol),
        "required_product": PRODUCT,
        "utc_month": start_month,
        "missing_run_start_ms": start_ms,
        "missing_run_end_ms": end_ms,
        "expected_grid_count": (end_ms - start_ms) // step + 1,
        "gap_kind": gap_kind,
        "reason": reason,
    }


def _split_quality_gap(
    symbol: str,
    start_ms: int,
    end_ms: int,
    *,
    gap_kind: str = "missing_five_minute_run",
    reason: str = "missing_expected_cadence_between_observations",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = start_ms
    step = EXPECTED_CADENCE_SECONDS * 1000
    while cursor <= end_ms:
        moment = datetime.fromtimestamp(cursor // 1000, tz=UTC)
        if moment.month == 12:
            boundary = datetime(moment.year + 1, 1, 1, tzinfo=UTC)
        else:
            boundary = datetime(moment.year, moment.month + 1, 1, tzinfo=UTC)
        boundary_ms = (boundary.toordinal() - datetime(1970, 1, 1, tzinfo=UTC).toordinal()) * 86_400_000
        segment_end = min(end_ms, boundary_ms - step)
        rows.append(
            _quality_gap_row(
                symbol,
                cursor,
                segment_end,
                gap_kind=gap_kind,
                reason=reason,
            )
        )
        cursor = segment_end + step
    return rows


def _inferred_quality_rows(symbol: str, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    if symbol != "HBARUSDC" or end_ms < HBAR_GAP_START_MS or start_ms > HBAR_GAP_END_MS:
        return _split_quality_gap(symbol, start_ms, end_ms)
    rows: list[dict[str, Any]] = []
    step = EXPECTED_CADENCE_SECONDS * 1000
    if start_ms < HBAR_GAP_START_MS:
        rows.extend(_split_quality_gap(symbol, start_ms, HBAR_GAP_START_MS - step))
    if end_ms > HBAR_GAP_END_MS:
        rows.extend(_split_quality_gap(symbol, HBAR_GAP_END_MS + step, end_ms))
    return rows


def _publish_parquet_artifact(
    tree: _OutputTree,
    table: pa.Table,
    *,
    destination_parts: Sequence[str],
    prefix: str,
    kind: str,
    hooks: PublicationHooks,
) -> tuple[Path, str, bool]:
    stage_name, stage_fd, _stage_path = tree.stage(prefix)
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
        digest, _size = _hash_fd(stage_fd)
        _verify_parquet_fd(
            stage_fd,
            expected_rows=table.num_rows,
            expected_sha256=digest,
            schema=table.schema,
        )
        reused, final_fd, path = tree.publish(
            stage_name,
            stage_fd,
            destination_parts,
            f"{digest}.parquet",
            kind=kind,
            hooks=hooks,
        )
        _verify_parquet_fd(
            final_fd,
            expected_rows=table.num_rows,
            expected_sha256=digest,
            schema=table.schema,
        )
        return path, digest, reused
    finally:
        if final_fd is not None:
            os.close(final_fd)
        os.close(stage_fd)


def _publish_json_artifact(
    tree: _OutputTree,
    document: Mapping[str, Any],
    *,
    destination_parts: Sequence[str],
    prefix: str,
    kind: str,
    hooks: PublicationHooks,
) -> tuple[Path, str, bool]:
    body = _canonical_json(document)
    digest = hashlib.sha256(body).hexdigest()
    stage_name, stage_fd, _stage_path = tree.stage(prefix)
    final_fd: int | None = None
    try:
        _rewrite_fd(stage_fd, body)
        reused, final_fd, path = tree.publish(
            stage_name,
            stage_fd,
            destination_parts,
            f"{digest}.json",
            kind=kind,
            hooks=hooks,
        )
        actual, _size = _hash_fd(final_fd)
        _require(actual == digest, "published JSON digest changed")
        try:
            _require(json.loads(_read_fd(final_fd)) == document, "published JSON content changed")
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise OpenInterestNormalizationError("published JSON is unreadable") from exc
        return path, digest, reused
    finally:
        if final_fd is not None:
            os.close(final_fd)
        os.close(stage_fd)


def _normalize_open_interest_tree(
    sources: Iterable[RawMetricObject],
    tree: _OutputTree,
    *,
    gaps: Sequence[CoverageGap] = (HBAR_CONFLICT_GAP,),
    hooks: PublicationHooks = PublicationHooks(),
    authorities_authenticated: bool = False,
) -> NormalizationResult:
    """Authenticate, normalize, and publish every supplied metrics source."""
    root = tree.root

    ordered = sorted(sources, key=lambda item: _identity_parts(item.source_key))
    identities: set[str] = set()
    checked: list[RawMetricObject] = []
    for source in ordered:
        _require(source.source_key not in identities, "raw authority repeats an identity")
        identities.add(source.source_key)
        _require(source.source_key != HBAR_CONFLICT_KEY, "unavailable HBAR conflict body is not consumable")
        _require(_HEX_RE.fullmatch(source.source_sha256) is not None, "raw source digest is invalid")
        _require(type(source.byte_size) is int and 0 < source.byte_size <= MAX_COMPRESSED_OBJECT_BYTES, "raw source compressed size is invalid")
        _require_no_symlink_components(source.path, label="raw source path")
        _require(source.path.is_file() and not source.path.is_symlink(), "raw source path is unsafe")
        actual_digest, actual_size = _digest_path(source.path)
        _require(actual_size == source.byte_size, "raw source byte size changed")
        _require(actual_digest == source.source_sha256, "raw source checksum changed")
        checked.append(source)

    authority_counts = {
        "accepted_generation_0_completion": sum(
            source.authority == "accepted_generation_0_completion" for source in checked
        ),
        "accepted_v3_direct_recovery": sum(
            source.authority == "accepted_v3_direct_recovery" for source in checked
        ),
    }
    if authorities_authenticated:
        _require(
            authority_counts["accepted_generation_0_completion"]
            == ACCEPTED_GENERATION0_METRICS_COMPLETIONS,
            "normalized generation-0 metrics source count changed",
        )
        _require(
            authority_counts["accepted_v3_direct_recovery"]
            == ACCEPTED_V3_METRICS_ROWS - 1,
            "normalized v3 usable metrics source count changed",
        )
        _require(sum(authority_counts.values()) == len(checked), "normalized source authority is unknown")

    gap_dates: dict[str, set[str]] = {}
    for gap in gaps:
        _require(gap.product == PRODUCT and gap.continuity_break, "coverage gap contract is invalid")
        gap_dates.setdefault(gap.native_symbol, set()).add(gap.economic_interval)

    by_symbol: dict[str, list[RawMetricObject]] = {}
    for source in checked:
        symbol, _date = _identity_parts(source.source_key)
        by_symbol.setdefault(symbol, []).append(source)

    quality_rows: list[dict[str, Any]] = [
        _quality_gap_row(
            "HBARUSDC",
            HBAR_GAP_START_MS,
            HBAR_GAP_END_MS,
            gap_kind="provider_checksum_conflict_unavailable",
            reason=PROVIDER_CONFLICT_UNAVAILABLE,
        )
    ]
    published: list[PublishedPartition] = []
    for symbol, symbol_sources in sorted(by_symbol.items()):
        previous_time: int | None = None
        previous_level: Decimal | None = None
        previous_value: Decimal | None = None
        previous_fingerprint: tuple[Any, ...] | None = None
        current_month: str | None = None
        month_rows: list[dict[str, Any]] = []
        month_sources: list[RawMetricObject] = []

        def publish_month() -> None:
            nonlocal month_rows, month_sources
            if current_month is None:
                return
            _require(bool(month_rows), "a partition has no rows")
            table = pa.Table.from_pylist(month_rows, schema=SCHEMA)
            parquet_path, parquet_sha, reused_parquet = _publish_parquet_artifact(
                tree,
                table,
                destination_parts=(".partitions", symbol, current_month),
                prefix=f"partition-{symbol}-{current_month}",
                kind="parquet",
                hooks=hooks,
            )
            manifest = {
                "document_type": "binance_usdm_open_interest_5m_partition_lineage",
                "schema_version": 1,
                "required_product": PRODUCT,
                "native_symbol": symbol,
                "utc_month": current_month,
                "row_count": len(month_rows),
                "schema_sha256": SCHEMA_SHA256,
                "writer_identity": writer_identity(),
                "parquet_sha256": parquet_sha,
                "parquet_name": parquet_path.name,
                "raw_objects": [_lineage_source(item, index) for index, item in enumerate(month_sources)],
                "coverage_gaps": [asdict(gap) for gap in gaps if gap.native_symbol == symbol and gap.economic_interval.startswith(current_month)],
            }
            lineage_path, lineage_sha, reused_lineage = _publish_json_artifact(
                tree,
                manifest,
                destination_parts=(".lineage", symbol, current_month),
                prefix=f"lineage-{symbol}-{current_month}",
                kind="lineage",
                hooks=hooks,
            )
            published.append(
                PublishedPartition(
                    native_symbol=symbol,
                    utc_month=current_month,
                    row_count=len(month_rows),
                    parquet_path=parquet_path,
                    parquet_sha256=parquet_sha,
                    lineage_path=lineage_path,
                    lineage_sha256=lineage_sha,
                    reused=reused_parquet and reused_lineage,
                )
            )
            month_rows = []
            month_sources = []

        for source in symbol_sources:
            _source_symbol, source_date = _identity_parts(source.source_key)
            source_month = source_date[:7]
            if current_month is None:
                current_month = source_month
            elif source_month != current_month:
                publish_month()
                current_month = source_month
            raw_ref = len(month_sources)
            source_added = False
            for ordinal, raw_row in _iter_metric_rows(source):
                values = _row_values(source, raw_ref, ordinal, raw_row)
                moment = int(values["create_time"])
                month = datetime.fromtimestamp(moment // 1000, tz=UTC).strftime("%Y-%m")
                _require(month == current_month, "metrics row UTC month conflicts with source identity")
                fingerprint = tuple(values[name] for name in METRICS_FIELDS if name != "symbol")
                if moment == previous_time:
                    if previous_fingerprint != fingerprint:
                        raise OpenInterestNormalizationError("duplicate metrics timestamp has conflicting values")
                    raise OpenInterestNormalizationError("duplicate metrics timestamp is ambiguous")
                interval = None if previous_time is None else (moment - previous_time) // 1000
                _require(previous_time is None or moment > previous_time, "metrics timestamps are not strictly increasing")
                if (
                    previous_time is not None
                    and interval is not None
                    and interval > EXPECTED_CADENCE_SECONDS
                ):
                    quality_rows.extend(
                        _inferred_quality_rows(
                            symbol,
                            previous_time + EXPECTED_CADENCE_SECONDS * 1000,
                            moment - EXPECTED_CADENCE_SECONDS * 1000,
                        )
                    )
                crossed_declared_gap = False
                if previous_time is not None:
                    previous_date = datetime.fromtimestamp(previous_time // 1000, tz=UTC).date()
                    current_date = datetime.fromtimestamp(moment // 1000, tz=UTC).date()
                    crossed_declared_gap = any(
                        previous_date.isoformat() < gap_date <= current_date.isoformat()
                        for gap_date in gap_dates.get(symbol, ())
                    )
                contiguous = interval == EXPECTED_CADENCE_SECONDS and not crossed_declared_gap
                status_value = "first_observation" if previous_time is None else ("contiguous" if contiguous else "gap_break")
                level = values["sum_open_interest"]
                value = values["sum_open_interest_value"]
                assert isinstance(level, Decimal) and isinstance(value, Decimal)
                values.update(native_identity(symbol))
                values.update(
                    {
                        "previous_sum_open_interest": previous_level if contiguous else None,
                        "open_interest_change": _scaled(_unscaled(level) - _unscaled(previous_level)) if contiguous and previous_level is not None else None,
                        "open_interest_value_change": _scaled(_unscaled(value) - _unscaled(previous_value)) if contiguous and previous_value is not None else None,
                        "change_interval_seconds": interval,
                        "gap_break_status": status_value,
                    }
                )
                month_rows.append(values)
                if not source_added:
                    month_sources.append(source)
                    source_added = True
                previous_time, previous_level, previous_value = moment, level, value
                previous_fingerprint = fingerprint
        publish_month()

    quality_rows.sort(
        key=lambda row: (
            str(row["native_symbol"]),
            int(row["missing_run_start_ms"]),
            int(row["missing_run_end_ms"]),
        )
    )
    gap_table = pa.Table.from_pylist(quality_rows, schema=QUALITY_GAP_SCHEMA)
    gap_path, gap_sha, gap_parquet_reused = _publish_parquet_artifact(
        tree,
        gap_table,
        destination_parts=(".quality-gaps",),
        prefix="quality-gaps",
        kind="quality_gap",
        hooks=hooks,
    )
    gap_lineage = {
        "document_type": "binance_usdm_open_interest_5m_quality_gap_lineage",
        "schema_version": 1,
        "required_product": PRODUCT,
        "quality_gap_schema": [
            {"name": field.name, "type": str(field.type), "nullable": field.nullable}
            for field in QUALITY_GAP_SCHEMA
        ],
        "quality_gap_parquet_sha256": gap_sha,
        "row_count": len(quality_rows),
        "hbar_checksum_conflict": asdict(HBAR_CONFLICT_GAP),
    }
    gap_lineage_path, gap_lineage_sha, gap_lineage_reused = _publish_json_artifact(
        tree,
        gap_lineage,
        destination_parts=(".quality-gap-lineage",),
        prefix="quality-gap-lineage",
        kind="quality_gap_lineage",
        hooks=hooks,
    )
    gap_artifact = PublishedGapArtifact(
        row_count=len(quality_rows),
        parquet_path=gap_path,
        parquet_sha256=gap_sha,
        lineage_path=gap_lineage_path,
        lineage_sha256=gap_lineage_sha,
        reused=gap_parquet_reused and gap_lineage_reused,
    )

    normalizer_sha, _normalizer_bytes = _digest_path(Path(__file__).resolve(strict=True))
    normalized_source_hasher = hashlib.sha256()
    for source in checked:
        normalized_source_hasher.update(
            _canonical_json(
                {
                    "authority": source.authority,
                    "source_key": source.source_key,
                    "source_sha256": source.source_sha256,
                    "byte_size": source.byte_size,
                }
            )
        )
    normalized_sources_sha = normalized_source_hasher.hexdigest()
    partition_facts = [
        {
            "native_symbol": part.native_symbol,
            "utc_month": part.utc_month,
            "row_count": part.row_count,
            "parquet_sha256": part.parquet_sha256,
            "parquet_path": str(part.parquet_path.relative_to(root)),
            "lineage_sha256": part.lineage_sha256,
            "lineage_path": str(part.lineage_path.relative_to(root)),
        }
        for part in published
    ]
    completion = {
        "document_type": "binance_usdm_open_interest_5m_product_completion",
        "schema_version": 1,
        "required_product": PRODUCT,
        "schema_sha256": SCHEMA_SHA256,
        "writer_identity": writer_identity(),
        "normalizer_source_sha256": normalizer_sha,
        "authorities_authenticated": authorities_authenticated,
        "normalized_source_count": len(checked),
        "normalized_sources_sha256": normalized_sources_sha,
        "raw_authorities": {
            "generation_0": {
                "seal_head_receipt_sha256": ACCEPTED_GENERATION0_SEAL_HEAD,
                "binance_completions": ACCEPTED_GENERATION0_BINANCE_COMPLETIONS,
                "metrics_completions": ACCEPTED_GENERATION0_METRICS_COMPLETIONS,
            },
            "v3_direct_recovery": {
                "manifest_compressed_sha256": ACCEPTED_V3_MANIFEST_SHA256,
                "manifest_rows": ACCEPTED_V3_ROWS,
                "listed_bytes": ACCEPTED_V3_BYTES,
                "metrics_rows": ACCEPTED_V3_METRICS_ROWS,
                "book_ticker_rows": ACCEPTED_V3_BOOK_TICKER_ROWS,
                "usable_metrics_rows": ACCEPTED_V3_METRICS_ROWS - 1,
                "checksum_conflict_rows": 1,
            },
        },
        "partitions": partition_facts,
        "quality_gap_artifact": {
            "parquet_sha256": gap_sha,
            "parquet_path": str(gap_path.relative_to(root)),
            "lineage_sha256": gap_lineage_sha,
            "lineage_path": str(gap_lineage_path.relative_to(root)),
            "row_count": len(quality_rows),
        },
        "totals": {
            "partition_count": len(published),
            "product_rows": sum(part.row_count for part in published),
            "quality_gap_rows": len(quality_rows),
        },
    }
    expected_completion_sha = hashlib.sha256(_canonical_json(completion)).hexdigest()
    tree.require_only_entry((".complete",), f"{expected_completion_sha}.json")
    completion_path, completion_sha, completion_reused = _publish_json_artifact(
        tree,
        completion,
        destination_parts=(".complete",),
        prefix="product-completion",
        kind="completion",
        hooks=hooks,
    )
    _require(completion_sha == expected_completion_sha, "product-completion identity changed")
    tree.require_only_entry((".complete",), f"{expected_completion_sha}.json")
    tree.verify_paths(
        [
            *(part.parquet_path for part in published),
            *(part.lineage_path for part in published),
            gap_path,
            gap_lineage_path,
            completion_path,
        ]
    )
    return NormalizationResult(
        product=PRODUCT,
        schema_sha256=SCHEMA_SHA256,
        writer_identity=writer_identity(),
        partitions=tuple(published),
        gaps=tuple(gaps),
        gap_artifact=gap_artifact,
        completion_path=completion_path,
        completion_sha256=completion_sha,
        completion_reused=completion_reused,
    )


def normalize_open_interest(
    sources: Iterable[RawMetricObject],
    output_root: Path,
    *,
    gaps: Sequence[CoverageGap] = (HBAR_CONFLICT_GAP,),
    hooks: PublicationHooks = PublicationHooks(),
) -> NormalizationResult:
    _require(output_root.name.startswith("."), "output root must be caller-specified and hidden")
    tree = _OutputTree(output_root)
    try:
        return _normalize_open_interest_tree(sources, tree, gaps=gaps, hooks=hooks)
    finally:
        tree.close()


def normalize_from_authorities(
    *,
    generation0_state: Path,
    generation0_content_root: Path,
    v3_manifest: Path,
    recovery_root: Path,
    output_root: Path,
    hooks: PublicationHooks = PublicationHooks(),
) -> NormalizationResult:
    sources = load_generation0_sources(generation0_state, generation0_content_root)
    sources += load_v3_recovery_sources(v3_manifest, recovery_root)
    _require(output_root.name.startswith("."), "output root must be caller-specified and hidden")
    tree = _OutputTree(output_root)
    try:
        return _normalize_open_interest_tree(
            sources,
            tree,
            hooks=hooks,
            authorities_authenticated=True,
        )
    finally:
        tree.close()
