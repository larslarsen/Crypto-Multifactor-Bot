"""Bounded Binance USD-M one-minute sample acquisition for CEX-002 Review 489.

This module is the only HTTP owner for the Gate 4 one-minute/hourly comparison.
It selects the pinned daily/klines 1h qualification roles, fetches at most nine
official 1m ZIP/CHECKSUM objects, and retains them immutably. It does not compare
economics and it does not amend generation 0 or the accepted hourly products.
"""

from __future__ import annotations

import calendar
import csv
import ctypes
import errno
import fcntl
import hashlib
import io
import json
import os
import re
import stat
import time
import urllib.error
import urllib.request
import uuid
import zipfile
import zlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Protocol
from urllib.parse import urlsplit

VISION_ORIGIN = "https://data.binance.vision"
REPORT_RELATIVE = "research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json"
REPORT_SHA256 = "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
BAR_ROOT = "data/.cex002_bar_1h"
BAR_COMPLETION = "3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7"
FLOW_ROOT = "data/.cex002_trade_flow_1h"
FLOW_COMPLETION = "a165f9e57065514cadc95620c280a82dbad5032d17c19e1caf012c9d12a84d0a"
GENERATION0_ROOT = "data/cex002_qualify"

MINUTE_FIELDS: tuple[str, ...] = (
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
    "ignore",
)
ROLES = ("early", "middle", "recent", "delisted")
HARD_MAX_OBJECTS = 9
HARD_MAX_ROWS = 1440
HARD_MAX_ZIP_BYTES = 8 * 2**20
HARD_MAX_SIDECAR_BYTES = 16 * 2**10
HARD_MAX_DECOMPRESSED_BYTES = 128 * 2**20
AUTHORITY_JSON_BYTES = 32 * 2**20
REQUEST_TIMEOUT_SECONDS = 30.0
SAMPLE_DOCUMENT = "cex002_bounded_kline_comparison_sample_manifest"
UNKNOWN_AVAILABILITY = "unknown_not_imputed"
USER_AGENT = "cex002-kline-comparison-sample"
RENAME_NOREPLACE = 1
_CHUNK = 64 * 1024
_OBJECT_KEY = re.compile(
    r"data/futures/um/daily/klines/(?P<symbol>[A-Z0-9]+)/1(?P<interval>[hm])/"
    r"(?P=symbol)-1(?P=interval)-(?P<day>\d{4}-\d{2}-\d{2})\.zip(?:\.CHECKSUM)?"
)
_HOURLY_KEY = re.compile(
    r"data/futures/um/daily/klines/(?P<symbol>[A-Z0-9]+)/1h/"
    r"(?P=symbol)-1h-(?P<day>\d{4}-\d{2}-\d{2})\.zip"
)
_SIDECAR_LINE = re.compile(r"^([0-9a-fA-F]{64})[ \t]+(\S+)\s*$")
_HEX = re.compile(r"[0-9a-f]{64}")


class SampleError(RuntimeError):
    """Fail-closed sample selection, transport, or retention error."""


@dataclass(frozen=True, slots=True)
class Role:
    symbol: str
    utc_date: str
    regime: str


@dataclass(frozen=True, slots=True)
class Policy:
    """Production pins. Tests may supply a fixture policy; the CLI cannot."""

    repo: Path
    report_relative: str
    report_sha256: str
    bar_root: str
    bar_completion: str
    flow_root: str
    flow_completion: str
    protected: tuple[str, ...]
    roles: tuple[Role, ...]
    request_timeout_seconds: float = REQUEST_TIMEOUT_SECONDS
    max_zip_bytes: int = HARD_MAX_ZIP_BYTES
    max_sidecar_bytes: int = HARD_MAX_SIDECAR_BYTES
    max_decompressed_bytes: int = HARD_MAX_DECOMPRESSED_BYTES


@dataclass(frozen=True, slots=True)
class PlannedObject:
    symbol: str
    utc_date: str
    roles: tuple[str, ...]
    hourly_source_key: str
    hourly_sample_sha256: str
    hourly_sample_bytes: int
    comparison_key: str
    comparison_url: str
    checksum_key: str
    checksum_url: str
    member_name: str


@dataclass(frozen=True, slots=True)
class RetainedObject:
    symbol: str
    utc_date: str
    roles: tuple[str, ...]
    comparison_key: str
    zip_sha256: str
    zip_bytes: int
    sidecar_sha256: str
    hourly_source_key: str
    hourly_sample_sha256: str
    hourly_sample_bytes: int
    retrieval_time: str


@dataclass(frozen=True, slots=True)
class LoadedSample:
    manifest_sha256: str
    objects: tuple[RetainedObject, ...]


@dataclass(frozen=True, slots=True)
class FetchResult:
    manifest_sha256: str
    manifest_path: Path
    distinct_objects: int
    logical_roles: int
    reused: bool
    fetched_objects: int


@dataclass(frozen=True, slots=True)
class FetchResponse:
    status: int
    final_url: str
    body: bytes
    content_length: int | None


@dataclass(frozen=True, slots=True)
class Hooks:
    before_object_publish: Callable[[], None] | None = None
    before_manifest_publish: Callable[[], None] | None = None


class Transport(Protocol):
    def fetch(self, url: str, *, timeout: float, max_bytes: int) -> FetchResponse:
        """Return one bounded response. Do not follow an alternate URL."""


PINNED_ROLES: tuple[Role, ...] = (
    Role("0GUSDT", "2025-09-17", "early"),
    Role("0GUSDT", "2026-03-21", "middle"),
    Role("0GUSDT", "2026-05-30", "recent"),
    Role("1000BTTCUSDT", "2022-01-26", "early"),
    Role("1000BTTCUSDT", "2022-03-12", "middle"),
    Role("1000BTTCUSDT", "2022-04-11", "recent"),
    Role("1000BTTCUSDT", "2022-04-11", "delisted"),
    Role("KAIAUSDT", "2024-12-04", "early"),
    Role("KAIAUSDT", "2025-10-25", "middle"),
    Role("KAIAUSDT", "2026-07-19", "recent"),
)


def production_policy(repo: Path) -> Policy:
    """The fixed Review 489 authority. Paths are repository-relative."""

    return Policy(
        repo=repo,
        report_relative=REPORT_RELATIVE,
        report_sha256=REPORT_SHA256,
        bar_root=BAR_ROOT,
        bar_completion=BAR_COMPLETION,
        flow_root=FLOW_ROOT,
        flow_completion=FLOW_COMPLETION,
        protected=(REPORT_RELATIVE, BAR_ROOT, FLOW_ROOT, GENERATION0_ROOT),
        roles=PINNED_ROLES,
    )


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("ascii")


def sha256_hex(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def hourly_object_key(symbol: str, utc_date: str) -> str:
    return f"data/futures/um/daily/klines/{symbol}/1h/{symbol}-1h-{utc_date}.zip"


def minute_object_key(symbol: str, utc_date: str) -> str:
    return f"data/futures/um/daily/klines/{symbol}/1m/{symbol}-1m-{utc_date}.zip"


def minute_member_name(symbol: str, utc_date: str) -> str:
    return f"{symbol}-1m-{utc_date}.csv"


def official_object_url(key: str) -> str:
    if _OBJECT_KEY.fullmatch(key) is None:
        raise SampleError("comparison URL is not an official daily kline object")
    return f"{VISION_ORIGIN}/{key}"


def utc_day_start_ms(utc_date: str) -> int:
    """UTC midnight in integer milliseconds. ``datetime.timestamp`` is not used."""

    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", utc_date)
    if match is None:
        raise SampleError("sample date is not YYYY-MM-DD")
    year, month, day = (int(match.group(index)) for index in range(1, 4))
    if not 1970 <= year <= 2100 or not 1 <= month <= 12:
        raise SampleError("sample date is outside the supported UTC range")
    if not 1 <= day <= calendar.monthrange(year, month)[1]:
        raise SampleError("sample date is not a real UTC day")
    return calendar.timegm((year, month, day, 0, 0, 0)) * 1000


def utc_civil(milliseconds: int) -> tuple[int, int, int]:
    if type(milliseconds) is not int or milliseconds < 0:
        raise SampleError("timestamp is not a nonnegative integer millisecond")
    try:
        year, month, day, *_rest = time.gmtime(milliseconds // 1000)
    except (OverflowError, OSError, ValueError) as exc:
        raise SampleError("timestamp is outside the UTC calendar") from exc
    return year, month, day


def utc_year_month(milliseconds: int) -> str:
    """``YYYY-MM`` for an integer UTC millisecond, without ``datetime.timestamp``."""

    year, month, _day = utc_civil(milliseconds)
    return f"{year:04d}-{month:02d}"


def zip_limit(policy: Policy) -> int:
    return min(policy.max_zip_bytes, HARD_MAX_ZIP_BYTES)


def sidecar_limit(policy: Policy) -> int:
    return min(policy.max_sidecar_bytes, HARD_MAX_SIDECAR_BYTES)


def decompressed_limit(policy: Policy) -> int:
    return min(policy.max_decompressed_bytes, HARD_MAX_DECOMPRESSED_BYTES)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SampleError(message)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in document, "JSON object repeats a key")
        document[key] = value
    return document


def parse_json_object(body: bytes, *, limit: int) -> dict[str, Any]:
    _require(len(body) <= limit, "JSON object exceeds its byte limit")
    try:
        text = body.decode("utf-8")
        value = json.loads(text, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SampleError("JSON object is malformed") from exc
    _require(type(value) is dict, "JSON value is not an object")
    return value


def lexical_path(path: Path) -> Path:
    """Absolute path that rejects ``..`` and any symlink component."""

    absolute = path.absolute()
    _require(".." not in absolute.parts, "path contains ..")
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        _require(part not in {"", ".", ".."}, "unsafe path component")
        current = current / part
        if current.is_symlink():
            raise SampleError("path contains a symlink")
    return current


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def guarded_roots(policy: Policy) -> tuple[Path, ...]:
    repo = lexical_path(policy.repo)
    relatives = (
        *policy.protected,
        policy.report_relative,
        policy.bar_root,
        policy.flow_root,
    )
    return tuple(lexical_path(repo / relative) for relative in relatives)


def assert_isolated(policy: Policy, evidence_root: Path, output_root: Path) -> tuple[Path, Path]:
    evidence = lexical_path(evidence_root)
    output = lexical_path(output_root)
    _require(not _overlaps(evidence, output), "evidence and comparison output overlap")
    for guarded in guarded_roots(policy):
        _require(
            not _overlaps(evidence, guarded) and not _overlaps(output, guarded),
            "sample output overlaps a protected root",
        )
    return evidence, output


def _ensure_directory(path: Path) -> Path:
    path = lexical_path(path)
    if path.exists():
        _require(path.is_dir(), "sample path exists and is not a directory")
        return path
    _require(path.parent.is_dir() and not path.parent.is_symlink(), "sample parent is not a directory")
    path.mkdir(mode=0o700)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return path


class _LockedDirectory:
    def __init__(self, path: Path) -> None:
        self.path = _ensure_directory(path)
        self.fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            _require(stat.S_ISDIR(os.fstat(self.fd).st_mode), "locked path is not a directory")
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self.fd)
            raise SampleError("sample directory is locked") from exc
        except Exception:
            os.close(self.fd)
            raise

    def close(self) -> None:
        os.close(self.fd)


def _safe_component(name: str) -> str:
    _require(bool(name) and name not in {".", ".."} and "/" not in name and "\\" not in name, "unsafe path component")
    _require("\x00" not in name, "unsafe path component")
    return name


def _mkdir_open(parent: int, name: str) -> int:
    name = _safe_component(name)
    try:
        os.mkdir(name, 0o700, dir_fd=parent)
        os.fsync(parent)
    except FileExistsError:
        pass
    try:
        handle = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
    except OSError as exc:
        raise SampleError("publication directory is unsafe") from exc
    if not stat.S_ISDIR(os.fstat(handle).st_mode):
        os.close(handle)
        raise SampleError("publication directory is unsafe")
    return handle


def _read_fd(handle: int, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        block = os.read(handle, 1024 * 1024)
        if not block:
            break
        total += len(block)
        _require(total <= limit, "retained file exceeds its byte limit")
        chunks.append(block)
    return b"".join(chunks)


def _write_fd(handle: int, body: bytes) -> None:
    view = memoryview(body)
    while view:
        written = os.write(handle, view)
        _require(written > 0, "publication write was incomplete")
        view = view[written:]
    os.fsync(handle)


def _rename_noreplace(directory: int, source: str, destination: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        renameat2 = libc.renameat2
    except AttributeError as exc:
        raise SampleError("atomic no-replace rename is unavailable") from exc
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        directory,
        os.fsencode(source),
        directory,
        os.fsencode(destination),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), destination)


def publish_immutable(
    root: Path,
    relative: str,
    body: bytes,
    *,
    before: Callable[[], None] | None = None,
    read_limit: int | None = None,
) -> bool:
    """Publish ``body`` at ``relative`` or reuse identical bytes. Never clobber."""

    path = PurePosixPath(relative)
    _require(not path.is_absolute() and ".." not in path.parts and bool(path.parts), "unsafe publication path")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    opened = [root_fd]
    directory = root_fd
    temporary: str | None = None
    try:
        for part in path.parts[:-1]:
            child = _mkdir_open(directory, part)
            opened.append(child)
            directory = child
        name = _safe_component(path.name)
        try:
            info = os.lstat(name, dir_fd=directory)
        except FileNotFoundError:
            info = None
        if info is not None:
            _require(stat.S_ISREG(info.st_mode), "publication destination is not a regular file")
            limit = len(body) if read_limit is None else read_limit
            _require(info.st_size <= limit, "retained file exceeds its byte limit")
            if info.st_size != len(body):
                raise SampleError("conflicting retained bytes")
            existing = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
            try:
                retained = _read_fd(existing, limit)
            finally:
                os.close(existing)
            _require(retained == body, "conflicting retained bytes")
            return True
        temporary = f".tmp-{uuid.uuid4().hex}"
        handle = os.open(
            temporary,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        try:
            _write_fd(handle, body)
            if before is not None:
                before()
            try:
                _rename_noreplace(directory, temporary, name)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise SampleError("content-addressed publication failed") from exc
                winner = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
                try:
                    retained = _read_fd(winner, len(body))
                finally:
                    os.close(winner)
                _require(retained == body, "conflicting retained bytes")
                os.unlink(temporary, dir_fd=directory)
                temporary = None
                os.fsync(directory)
                return True
            temporary = None
            os.fsync(directory)
            return False
        finally:
            os.close(handle)
            if temporary is not None:
                try:
                    os.unlink(temporary, dir_fd=directory)
                    os.fsync(directory)
                except OSError:
                    pass
    finally:
        for handle in reversed(opened):
            os.close(handle)


def list_regular(root: Path, relative: str, *, limit: int) -> list[str]:
    path = root / PurePosixPath(relative)
    if not path.exists():
        return []
    directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        names = os.listdir(directory)
        _require(len(names) <= limit, "evidence directory listing exceeds its bound")
        files: list[str] = []
        for name in names:
            info = os.lstat(name, dir_fd=directory)
            if stat.S_ISLNK(info.st_mode):
                raise SampleError("evidence directory contains a symlink")
            if not stat.S_ISREG(info.st_mode):
                raise SampleError("evidence directory contains a non-file")
            files.append(name)
        return sorted(files)
    finally:
        os.close(directory)


def read_regular(path: Path, limit: int) -> bytes:
    lexical_path(path)
    handle = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        _require(stat.S_ISREG(os.fstat(handle).st_mode), "input is not a regular file")
        return _read_fd(handle, limit)
    finally:
        os.close(handle)


def read_bounded(stream: Any, *, max_bytes: int, content_length: int | None) -> bytes:
    """Count bytes while streaming. A Content-Length header cannot raise the cap."""

    _require(max_bytes >= 0, "byte limit is negative")
    if content_length is not None:
        _require(type(content_length) is int and content_length >= 0, "Content-Length is not an integer")
    chunks: list[bytes] = []
    total = 0
    while True:
        block = stream.read(_CHUNK)
        if not block:
            break
        total += len(block)
        if total > max_bytes:
            raise SampleError("response exceeds its streaming byte limit")
        chunks.append(block)
    body = b"".join(chunks)
    if content_length is not None and content_length != len(body):
        raise SampleError("Content-Length does not match the streamed body")
    return body


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: Any, headers: Any, newurl: str) -> None:
        raise SampleError("redirect outside the exact official object")


class UrllibTransport:
    """One GET, no retry, no proxy, no redirect."""

    def fetch(self, url: str, *, timeout: float, max_bytes: int) -> FetchResponse:
        parsed = urlsplit(url)
        _require(parsed.scheme == "https", "sample URL is not HTTPS")
        _require(parsed.hostname == "data.binance.vision", "sample URL host is not official")
        _require(parsed.username is None and parsed.password is None and parsed.port is None, "sample URL is not canonical")
        _require(parsed.query == "" and parsed.fragment == "", "sample URL carries a query or fragment")
        _require(_OBJECT_KEY.fullmatch(parsed.path.lstrip("/")) is not None, "sample URL is not an official object")
        headers = {"User-Agent": USER_AGENT}
        request = urllib.request.Request(url, method="GET", headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)
        try:
            with opener.open(request, timeout=timeout) as response:
                status = int(getattr(response, "status", response.getcode()))
                final_url = str(response.geturl())
                header = response.headers.get("Content-Length")
                if header is None:
                    content_length = None
                else:
                    try:
                        content_length = int(header)
                    except ValueError as exc:
                        raise SampleError("Content-Length is not an integer") from exc
                body = read_bounded(response, max_bytes=max_bytes, content_length=content_length)
        except SampleError:
            raise
        except urllib.error.HTTPError as exc:
            raise SampleError(f"sample HTTP status {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError, http_incomplete()) as exc:
            raise SampleError("sample request failed") from exc
        return FetchResponse(status, final_url, body, content_length)


def http_incomplete() -> type[BaseException]:
    import http.client

    return http.client.IncompleteRead


def _accept_response(url: str, response: FetchResponse, *, max_bytes: int) -> bytes:
    _require(response.status == 200, "sample HTTP status is not 200")
    _require(response.final_url == url, "sample response left the exact official object")
    _require(len(response.body) <= max_bytes, "response exceeds its streaming byte limit")
    if response.content_length is not None:
        _require(response.content_length == len(response.body), "Content-Length does not match the streamed body")
    return response.body


def _member_is_safe(member: zipfile.ZipInfo, member_name: str, decompressed: int) -> None:
    name = member.filename
    posix = PurePosixPath(name.replace("\\", "/"))
    _require(bool(name) and not posix.is_absolute() and ".." not in posix.parts, "ZIP member path escapes")
    _require(len(posix.parts) == 1 and name == member_name and name.endswith(".csv"), "ZIP member name is not the expected CSV")
    mode = stat.S_IFMT(member.external_attr >> 16)
    _require(mode in {0, stat.S_IFREG}, "ZIP member is not a regular file")
    _require(not (member.flag_bits & 0x1), "encrypted ZIP member is rejected")
    _require(member.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}, "ZIP compression is unsupported")
    _require(0 <= member.file_size <= decompressed, "declared decompressed size exceeds the limit")


def extract_minute_rows(
    payload: bytes,
    *,
    member_name: str,
    zip_byte_limit: int,
    decompressed_byte_limit: int,
    max_rows: int,
) -> tuple[tuple[str, ...], ...]:
    """Validate one ZIP in memory and return its data rows. Never extracts to disk."""

    _require(0 < len(payload) <= zip_byte_limit, "ZIP exceeds the compressed byte limit")
    _require(max_rows == HARD_MAX_ROWS or max_rows < HARD_MAX_ROWS, "row limit exceeds the hard cap")
    row_cap = min(max_rows, HARD_MAX_ROWS)
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise SampleError("ZIP is truncated or malformed") from exc
    try:
        members = archive.infolist()
        _require(len(members) == 1, "ZIP must contain exactly one member")
        member = members[0]
        _member_is_safe(member, member_name, decompressed_byte_limit)
        chunks: list[bytes] = []
        total = 0
        try:
            with archive.open(member, "r") as raw:
                while True:
                    block = raw.read(_CHUNK)
                    if not block:
                        break
                    total += len(block)
                    _require(total <= decompressed_byte_limit, "decompressed ZIP member exceeds the limit")
                    chunks.append(block)
        except zipfile.BadZipFile as exc:
            raise SampleError("ZIP CRC or truncation failure") from exc
        data = b"".join(chunks)
        _require(zlib.crc32(data) & 0xFFFFFFFF == member.CRC, "ZIP CRC failure")
        _require(member.file_size == len(data), "ZIP member size does not match its header")
    finally:
        archive.close()
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise SampleError("ZIP member is not UTF-8") from exc
    try:
        parsed = csv.reader(io.StringIO(text, newline=""), strict=True)
        rows: list[tuple[str, ...]] = []
        first = True
        for row in parsed:
            if first:
                first = False
                if tuple(row) == MINUTE_FIELDS:
                    continue
            _require(len(row) == len(MINUTE_FIELDS), "minute CSV row width is invalid")
            rows.append(tuple(row))
            _require(len(rows) <= row_cap, "minute CSV exceeds 1440 data rows")
    except csv.Error as exc:
        raise SampleError("minute CSV is malformed") from exc
    _require(bool(rows), "minute CSV contains no data rows")
    return tuple(rows)


def parse_sidecar(body: bytes, *, filename: str, limit: int) -> str:
    _require(len(body) <= limit, "checksum sidecar exceeds its byte limit")
    try:
        text = body.decode("utf-8")
    except UnicodeError as exc:
        raise SampleError("checksum sidecar is not UTF-8") from exc
    match = _SIDECAR_LINE.fullmatch(text)
    _require(match is not None, "malformed checksum statement")
    assert match is not None
    digest = match.group(1).lower()
    _require(match.group(2) == filename, "checksum filename mismatch")
    return digest


def _sample_record(item: Mapping[str, Any]) -> tuple[str, str, str, str, int, str]:
    _require(type(item) is dict, "qualification sample is not an object")
    _require(item.get("family") == "daily/klines", "sample family is not daily/klines")
    key = item.get("key")
    match = _HOURLY_KEY.fullmatch(key) if type(key) is str else None
    _require(match is not None, "daily kline sample key is not a canonical 1h object")
    assert match is not None
    symbol = match.group("symbol")
    utc_date = match.group("day")
    _require(item.get("symbol") == symbol, "sample symbol does not match its key")
    _require(item.get("regime") in ROLES, "sample role is not early, middle, recent, or delisted")
    utc_day_start_ms(utc_date)
    digest = item.get("sha256")
    _require(
        type(digest) is str and _HEX.fullmatch(digest) is not None and digest == item.get("provider_checksum"),
        "sample checksum identity disagrees",
    )
    size = item.get("byte_size")
    _require(type(size) is int and size > 0, "sample byte size is invalid")
    _require(item.get("checksum_match") is True, "sample checksum was not proved")
    _require(item.get("url") == official_object_url(str(key)), "sample URL is not the official hourly object")
    regime = item.get("regime")
    assert type(regime) is str and type(digest) is str and type(size) is int
    return symbol, utc_date, regime, str(key), size, digest


def select_samples(document: Mapping[str, Any], policy: Policy) -> tuple[PlannedObject, ...]:
    """Select exactly the policy's daily/klines 1h roles and fold agreeing duplicates."""

    samples = document.get("samples")
    _require(type(samples) is list, "qualification report has no sample list")
    assert type(samples) is list
    _require(len(samples) <= 10_000, "qualification sample list exceeds its bound")
    found: list[tuple[str, str, str, str, int, str]] = []
    for item in samples:
        _require(type(item) is dict, "qualification sample is not an object")
        assert type(item) is dict
        if item.get("family") != "daily/klines":
            continue
        found.append(_sample_record(item))
    expected = sorted((role.symbol, role.utc_date, role.regime) for role in policy.roles)
    observed = sorted((symbol, utc_date, regime) for symbol, utc_date, regime, _key, _size, _digest in found)
    _require(observed == expected, "sample roles do not match the pinned daily kline selection")
    grouped: dict[tuple[str, str], list[tuple[str, str, str, str, int, str]]] = {}
    for record in found:
        grouped.setdefault((record[0], record[1]), []).append(record)
    _require(len(grouped) <= HARD_MAX_OBJECTS, "comparison sample exceeds nine ZIP objects")
    planned: list[PlannedObject] = []
    for symbol, utc_date in sorted(grouped):
        items = grouped[symbol, utc_date]
        identity = {(key, size, digest) for _symbol, _day, _regime, key, size, digest in items}
        _require(len(identity) == 1, "duplicate sample role disagrees on the retained hourly object")
        regimes = tuple(sorted(regime for _symbol, _day, regime, _key, _size, _digest in items))
        _require(len(regimes) == len(set(regimes)), "sample role is repeated on one object")
        _key, size, digest = identity.pop()
        comparison = minute_object_key(symbol, utc_date)
        checksum = f"{comparison}.CHECKSUM"
        planned.append(
            PlannedObject(
                symbol=symbol,
                utc_date=utc_date,
                roles=regimes,
                hourly_source_key=_key,
                hourly_sample_sha256=digest,
                hourly_sample_bytes=size,
                comparison_key=comparison,
                comparison_url=official_object_url(comparison),
                checksum_key=checksum,
                checksum_url=official_object_url(checksum),
                member_name=minute_member_name(symbol, utc_date),
            )
        )
    return tuple(planned)


def _object_record(planned: PlannedObject, *, zip_sha: str, zip_bytes: int, side_sha: str, side_bytes: int, retrieval_time: str) -> dict[str, Any]:
    _require(type(retrieval_time) is str and bool(retrieval_time), "retrieval time is missing")
    return {
        "checksum_key": planned.checksum_key,
        "checksum_url": planned.checksum_url,
        "comparison_key": planned.comparison_key,
        "comparison_url": planned.comparison_url,
        "hourly_sample_bytes": planned.hourly_sample_bytes,
        "hourly_sample_sha256": planned.hourly_sample_sha256,
        "hourly_source_key": planned.hourly_source_key,
        "retrieval_time": retrieval_time,
        "roles": list(planned.roles),
        "sidecar_bytes": side_bytes,
        "sidecar_sha256": side_sha,
        "source_availability_state": UNKNOWN_AVAILABILITY,
        "source_available_at": None,
        "symbol": planned.symbol,
        "utc_date": planned.utc_date,
        "zip_bytes": zip_bytes,
        "zip_sha256": zip_sha,
    }


def _receipt_matches(stored: Mapping[str, Any], fresh: Mapping[str, Any]) -> bool:
    if stored.get("source_available_at") is not None or stored.get("source_availability_state") != UNKNOWN_AVAILABILITY:
        return False
    retrieval = stored.get("retrieval_time")
    if type(retrieval) is not str or not retrieval:
        return False
    compared = dict(fresh)
    compared["retrieval_time"] = retrieval
    return dict(stored) == compared


def _manifest_body(policy: Policy, records: Sequence[Mapping[str, Any]]) -> bytes:
    document = {
        "distinct_object_count": len(records),
        "document_type": SAMPLE_DOCUMENT,
        "logical_role_count": sum(len(record["roles"]) for record in records),
        "max_objects": HARD_MAX_OBJECTS,
        "objects": list(records),
        "qualification_report_sha256": policy.report_sha256,
        "schema_version": 1,
    }
    return canonical_json(document)


def _content_relative(digest: str) -> str:
    _require(_HEX.fullmatch(digest) is not None, "content digest is invalid")
    return f".objects/{digest[:2]}/{digest}"


def _validate_pair(
    planned: PlannedObject,
    zip_body: bytes,
    side_body: bytes,
    policy: Policy,
) -> tuple[str, str]:
    filename = planned.comparison_key.rsplit("/", 1)[-1]
    digest = parse_sidecar(side_body, filename=filename, limit=sidecar_limit(policy))
    zip_sha = sha256_hex(zip_body)
    _require(digest == zip_sha, "ZIP bytes do not match the checksum statement")
    extract_minute_rows(
        zip_body,
        member_name=planned.member_name,
        zip_byte_limit=zip_limit(policy),
        decompressed_byte_limit=decompressed_limit(policy),
        max_rows=HARD_MAX_ROWS,
    )
    return zip_sha, sha256_hex(side_body)


def _find_receipt(evidence: Path, planned: PlannedObject) -> dict[str, Any] | None:
    matches: list[dict[str, Any]] = []
    for name in list_regular(evidence, ".receipts", limit=16):
        body = read_regular(evidence / ".receipts" / name, AUTHORITY_JSON_BYTES)
        document = parse_json_object(body, limit=AUTHORITY_JSON_BYTES)
        if document.get("comparison_key") != planned.comparison_key:
            continue
        zip_sha = document.get("zip_sha256")
        _require(
            type(zip_sha) is str and name == f"{zip_sha}.json",
            "retained receipt filename disagrees",
        )
        _require(canonical_json(document) == body, "retained receipt is corrupt")
        matches.append(document)
    _require(len(matches) <= 1, "duplicate receipts for one comparison object")
    return matches[0] if matches else None


def _publish_bytes(evidence: Path, digest: str, body: bytes, *, limit: int) -> None:
    _require(sha256_hex(body) == digest, "publication digest does not match its bytes")
    publish_immutable(evidence, _content_relative(digest), body, read_limit=limit)


def fetch_sample(
    policy: Policy,
    evidence_root: Path,
    *,
    fetch: bool,
    transport: Transport | None = None,
    hooks: Hooks | None = None,
    clock: Callable[[], str] | None = None,
) -> FetchResult:
    """Authenticate retained evidence, or fetch missing official objects when asked."""

    hooks = hooks or Hooks()
    clock = clock or (lambda: datetime.now(UTC).isoformat())
    evidence, _output = assert_isolated(policy, evidence_root, evidence_root.parent / f".{evidence_root.name}-comparison-output-guard")
    # The guard path above is only used to reject a protected evidence root before any
    # write. Re-check the evidence root alone against protected paths.
    evidence = lexical_path(evidence_root)
    for guarded in guarded_roots(policy):
        _require(not _overlaps(evidence, guarded), "sample evidence overlaps a protected root")
    report_path = lexical_path(policy.repo / policy.report_relative)
    report_body = read_regular(report_path, AUTHORITY_JSON_BYTES)
    _require(sha256_hex(report_body) == policy.report_sha256, "qualification report digest mismatch")
    planned = select_samples(parse_json_object(report_body, limit=AUTHORITY_JSON_BYTES), policy)
    _require(len(planned) <= HARD_MAX_OBJECTS, "comparison sample exceeds nine ZIP objects")
    evidence = _ensure_directory(evidence)
    locked = _LockedDirectory(evidence)
    fetched = 0
    try:
        records: list[dict[str, Any]] = []
        active = transport
        if fetch and active is None:
            active = UrllibTransport()
        for planned_object in planned:
            if hooks.before_object_publish is not None:
                hooks.before_object_publish()
            stored = _find_receipt(evidence, planned_object)
            if stored is not None:
                record = _reuse_receipt(evidence, planned_object, stored, policy)
            else:
                _require(fetch and active is not None, "retained comparison sample is missing")
                record = _download_object(evidence, planned_object, policy, active, clock)
                fetched += 1
            records.append(record)
        body = _manifest_body(policy, records)
        digest = sha256_hex(body)
        if hooks.before_manifest_publish is not None:
            hooks.before_manifest_publish()
        existing = list_regular(evidence, ".complete", limit=4)
        _require(not existing or existing == [f"{digest}.json"], "conflicting sample manifest")
        reused = publish_immutable(evidence, f".complete/{digest}.json", body, read_limit=AUTHORITY_JSON_BYTES)
        roles = sum(len(record["roles"]) for record in records)
        return FetchResult(digest, evidence / ".complete" / f"{digest}.json", len(records), roles, reused, fetched)
    finally:
        locked.close()


def _reuse_receipt(evidence: Path, planned: PlannedObject, stored: Mapping[str, Any], policy: Policy) -> dict[str, Any]:
    zip_sha = stored.get("zip_sha256")
    side_sha = stored.get("sidecar_sha256")
    _require(type(zip_sha) is str and type(side_sha) is str, "retained receipt digest is invalid")
    assert type(zip_sha) is str and type(side_sha) is str
    zip_body = read_regular(evidence / _content_relative(zip_sha), zip_limit(policy))
    side_body = read_regular(evidence / _content_relative(side_sha), sidecar_limit(policy))
    checked_zip, checked_side = _validate_pair(planned, zip_body, side_body, policy)
    _require((checked_zip, checked_side) == (zip_sha, side_sha), "retained object digest mismatch")
    fresh = _object_record(
        planned,
        zip_sha=checked_zip,
        zip_bytes=len(zip_body),
        side_sha=checked_side,
        side_bytes=len(side_body),
        retrieval_time=str(stored.get("retrieval_time") or ""),
    )
    _require(_receipt_matches(stored, fresh), "conflicting retained receipt")
    return dict(stored)


def _download_object(
    evidence: Path,
    planned: PlannedObject,
    policy: Policy,
    transport: Transport,
    clock: Callable[[], str],
) -> dict[str, Any]:
    timeout = policy.request_timeout_seconds
    try:
        sidecar_response = transport.fetch(planned.checksum_url, timeout=timeout, max_bytes=sidecar_limit(policy))
        zip_response = transport.fetch(planned.comparison_url, timeout=timeout, max_bytes=zip_limit(policy))
    except SampleError:
        raise
    except Exception as exc:
        raise SampleError("sample transport failed") from exc
    side_body = _accept_response(planned.checksum_url, sidecar_response, max_bytes=sidecar_limit(policy))
    zip_body = _accept_response(planned.comparison_url, zip_response, max_bytes=zip_limit(policy))
    zip_sha, side_sha = _validate_pair(planned, zip_body, side_body, policy)
    _publish_bytes(evidence, side_sha, side_body, limit=sidecar_limit(policy))
    _publish_bytes(evidence, zip_sha, zip_body, limit=zip_limit(policy))
    record = _object_record(
        planned,
        zip_sha=zip_sha,
        zip_bytes=len(zip_body),
        side_sha=side_sha,
        side_bytes=len(side_body),
        retrieval_time=clock(),
    )
    receipt = canonical_json(record)
    publish_immutable(evidence, f".receipts/{zip_sha}.json", receipt, read_limit=AUTHORITY_JSON_BYTES)
    return record


def _read_receipt_file(evidence: Path, zip_sha: str) -> dict[str, Any]:
    """Read one physical receipt and bind it to its content-addressed name."""

    _require(_HEX.fullmatch(zip_sha) is not None, "retained receipt digest is invalid")
    path = evidence / ".receipts" / f"{zip_sha}.json"
    try:
        body = read_regular(path, AUTHORITY_JSON_BYTES)
    except FileNotFoundError as exc:
        raise SampleError("retained receipt is missing") from exc
    receipt = parse_json_object(body, limit=AUTHORITY_JSON_BYTES)
    _require(canonical_json(receipt) == body, "retained receipt is corrupt")
    _require(receipt.get("zip_sha256") == zip_sha, "retained receipt filename disagrees")
    return receipt


def load_sample(policy: Policy, evidence_root: Path) -> LoadedSample:
    """Re-authenticate a completed sample manifest and every retained object."""

    evidence = lexical_path(evidence_root)
    for guarded in guarded_roots(policy):
        _require(not _overlaps(evidence, guarded), "sample evidence overlaps a protected root")
    report_body = read_regular(lexical_path(policy.repo / policy.report_relative), AUTHORITY_JSON_BYTES)
    _require(sha256_hex(report_body) == policy.report_sha256, "qualification report digest mismatch")
    planned = select_samples(parse_json_object(report_body, limit=AUTHORITY_JSON_BYTES), policy)
    names = list_regular(evidence, ".complete", limit=4)
    _require(len(names) == 1 and names[0].endswith(".json"), "sample manifest is missing")
    manifest_name = names[0]
    manifest_body = read_regular(evidence / ".complete" / manifest_name, AUTHORITY_JSON_BYTES)
    digest = sha256_hex(manifest_body)
    _require(manifest_name == f"{digest}.json", "sample manifest name does not match its bytes")
    manifest = parse_json_object(manifest_body, limit=AUTHORITY_JSON_BYTES)
    _require(manifest.get("document_type") == SAMPLE_DOCUMENT and manifest.get("schema_version") == 1, "sample manifest identity")
    _require(manifest.get("qualification_report_sha256") == policy.report_sha256, "sample manifest report binding")
    objects = manifest.get("objects")
    _require(type(objects) is list and len(objects) == len(planned), "sample manifest object count")
    assert type(objects) is list
    retained: list[RetainedObject] = []
    expected_receipts: list[str] = []
    receipt_names = list_regular(evidence, ".receipts", limit=16)
    for planned_object, record in zip(planned, objects, strict=True):
        _require(type(record) is dict, "sample manifest object is invalid")
        assert type(record) is dict
        zip_sha = record.get("zip_sha256")
        _require(type(zip_sha) is str, "retained receipt digest is invalid")
        assert type(zip_sha) is str
        receipt = _read_receipt_file(evidence, zip_sha)
        _require(receipt == record, "conflicting retained receipt")
        checked = _reuse_receipt(evidence, planned_object, receipt, policy)
        _require(checked == record, "sample manifest does not match its receipt")
        expected_receipts.append(f"{zip_sha}.json")
        retained.append(
            RetainedObject(
                symbol=planned_object.symbol,
                utc_date=planned_object.utc_date,
                roles=planned_object.roles,
                comparison_key=planned_object.comparison_key,
                zip_sha256=str(record["zip_sha256"]),
                zip_bytes=int(record["zip_bytes"]),
                sidecar_sha256=str(record["sidecar_sha256"]),
                hourly_source_key=planned_object.hourly_source_key,
                hourly_sample_sha256=planned_object.hourly_sample_sha256,
                hourly_sample_bytes=planned_object.hourly_sample_bytes,
                retrieval_time=str(record["retrieval_time"]),
            )
        )
    _require(receipt_names == sorted(expected_receipts), "conflicting retained receipt")
    expected = _manifest_body(policy, objects)
    _require(expected == manifest_body, "sample manifest is not canonical")
    _require(manifest.get("logical_role_count") == sum(len(item.roles) for item in retained), "sample role count")
    _require(manifest.get("distinct_object_count") == len(retained), "sample object count")
    return LoadedSample(digest, tuple(retained))


def read_retained_rows(policy: Policy, evidence_root: Path, retained: RetainedObject) -> tuple[tuple[str, ...], ...]:
    """Re-read one retained day. Callers keep at most one day of rows."""

    evidence = lexical_path(evidence_root)
    zip_body = read_regular(evidence / _content_relative(retained.zip_sha256), zip_limit(policy))
    side_body = read_regular(evidence / _content_relative(retained.sidecar_sha256), sidecar_limit(policy))
    _require(sha256_hex(zip_body) == retained.zip_sha256 and len(zip_body) == retained.zip_bytes, "retained ZIP changed")
    filename = retained.comparison_key.rsplit("/", 1)[-1]
    _require(sha256_hex(side_body) == retained.sidecar_sha256, "retained checksum changed")
    stated = parse_sidecar(side_body, filename=filename, limit=sidecar_limit(policy))
    _require(stated == retained.zip_sha256, "retained checksum changed")
    return extract_minute_rows(
        zip_body,
        member_name=minute_member_name(retained.symbol, retained.utc_date),
        zip_byte_limit=zip_limit(policy),
        decompressed_byte_limit=decompressed_limit(policy),
        max_rows=HARD_MAX_ROWS,
    )
