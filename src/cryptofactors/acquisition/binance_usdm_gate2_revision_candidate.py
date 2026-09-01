"""CEX-002 Gate-2 listing-only post-plan revision candidate - ADR-0032.

Standalone planner. It holds the generation-0 acquisition lock nonblocking, opens
an actually immutable held-descriptor SQLite snapshot, derives the exact pending
metrics-revision and book-ticker ZIP-work identities, rehashes retained sidecars,
paginates current official listings for only those two family prefixes, and
commits one locator after privately building the candidate. It performs no raw
ZIP GET, no generation-0 mutation, and never claims acceptance.

This module uses the Python standard library and must not import the acquisition
engine.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import gzip
import hashlib
import http.client
import json
import os
import re
import sqlite3
import stat
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from xml.etree import ElementTree

TICKET_ID = "CEX-002"
ADR_ID = "0032"
CANDIDATE_SCHEMA = "cex002_gate2_revision_candidate_v2"
CHECKPOINT_SCHEMA = "cex002_gate2_revision_candidate_checkpoint_v2"
LINEAGE_SCHEMA = "cex002_gate2_revision_candidate_lineage_v2"
LOCATOR_SCHEMA = "cex002_gate2_revision_candidate_locator_v2"
MANIFEST_FORMAT = "gzip_jsonl"
POLICY_IDENTITY = (
    "adr0032_opaque_listing_cursor_normalization_and_v2_candidate_v2"
)
GENERATION0_POLICY_IDENTITY = (
    "adr0029_content_addressed_gate2_acquisition_and_resume_"
    "adr0030_exact_retained_credit_v2"
)
SOURCE_RELATIVE = Path(
    "src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py"
)
CLI_RELATIVE = Path("scripts/research/plan_binance_usdm_gate2_revision_candidate.py")
ACQUISITION_SOURCE_RELATIVE = Path(
    "src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py"
)
ACQUISITION_CLI_RELATIVE = Path(
    "scripts/research/acquire_binance_usdm_harmonic_release.py"
)

FIXED_STORE_ROOT = "data/cex002_qualify"
FIXED_ACTIVE_NAME = "gate2"
FIXED_CANDIDATE_NAME = "gate2_revision_candidate_v2"
LOCK_NAME = "acquisition.lock"
SQLITE_NAME = "state.sqlite"
SQLITE_WAL_NAME = "state.sqlite-wal"
SQLITE_SHM_NAME = "state.sqlite-shm"
CONTENT_NAME = "content"
CANDIDATE_LOCK_NAME = "candidate.lock"
CHECKPOINT_NAME = "checkpoint.json"
PAGES_NAME = "pages"
TMP_NAME = "tmp"
MANIFEST_NAME = "manifest"
RECEIPT_NAME = "receipts"
LINEAGE_NAME = "lineage"
LOCATOR_NAME = "locator.json"
LISTING_INDEX_NAME = "listing.sqlite"

VISION_S3_ENDPOINT = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
VISION_S3_HOST = "s3-ap-northeast-1.amazonaws.com"
VISION_S3_PATH = "/data.binance.vision"
VISION_OBJECT_BASE = "https://data.binance.vision"
LIST_DELIMITER = "/"
LIST_TYPE = "2"
LIST_PAGE_CEILING_BYTES = 8_388_608
SIDECAR_CEILING_BYTES = 4096
CHUNK_SIZE = 64 * 1024
CURSOR_BATCH = 256
RENAME_NOREPLACE = 1
GZIP_COMPRESSLEVEL = 9
PAGE_OBJECT_CEILING = 10_000
PREFIX_CEILING = 20_000
TOKEN_LENGTH_CEILING = 2_048
KEY_LENGTH_CEILING = 1_024
PAGE_COUNT_CEILING = 100_000
CHECKPOINT_CEILING_BYTES = 64 * 1024 * 1024
LOCATOR_CEILING_BYTES = 64 * 1024
RECEIPT_CEILING_BYTES = 16 * 1024 * 1024
LINEAGE_CEILING_BYTES = 64 * 1024 * 1024
MANIFEST_COMPRESSED_CEILING_BYTES = 256 * 1024 * 1024
MANIFEST_ROW_CEILING_BYTES = 1024 * 1024
MANIFEST_DECOMPRESSED_CEILING_BYTES = 1024 * 1024 * 1024
MANIFEST_ROW_COUNT_CEILING = 100_000
PASS_IDS: tuple[str, str] = ("pass_1", "pass_2")

PROVIDER_BINANCE = "binance_vision"
PROVIDER_COINALYZE = "coinalyze"
KIND_BINANCE = "binance_object"
KIND_COINALYZE_INVENTORY = "coinalyze_inventory"
KIND_COINALYZE_LIQUIDATION = "coinalyze_liquidation"
KIND_COINALYZE_UNSUPPORTED = "coinalyze_unsupported_gap"
GAP_UNSUPPORTED = "unsupported_mapping"
RETRY_TERMINAL = "terminal"
CHARGE_RESERVED = "reserved"
CHARGE_PUBLISHED = "published"
CHARGE_SETTLED = "settled"
OUTCOME_CHECKSUM_VERIFIED = "checksum_verified"

FAMILY_METRICS = "daily/metrics"
FAMILY_BOOK_TICKER = "daily/bookTicker"
AFFECTED_FAMILIES: tuple[str, ...] = (FAMILY_METRICS, FAMILY_BOOK_TICKER)
FAMILY_PREFIXES: tuple[str, ...] = (
    "data/futures/um/daily/metrics/",
    "data/futures/um/daily/bookTicker/",
)
ALL_BINANCE_FAMILIES: tuple[str, ...] = (
    "daily/bookDepth",
    "daily/bookTicker",
    "daily/indexPriceKlines",
    "daily/klines",
    "daily/markPriceKlines",
    "daily/metrics",
    "daily/premiumIndexKlines",
    "monthly/fundingRate",
    "monthly/indexPriceKlines",
    "monthly/klines",
    "monthly/markPriceKlines",
    "monthly/premiumIndexKlines",
)

CLASS_PROVIDER_REVISION = "provider_revision"
CLASS_ZIP_WORK = "zip_work"

MSG_SIZE = "AcquisitionError: listed byte size does not match"
MSG_CEILING = "AcquisitionError: stream exceeded the listed byte ceiling"
MSG_DIGEST = "AcquisitionError: streamed digest does not match the required checksum"
MSG_ZIP = "AcquisitionError: ZIP uncompressed expansion exceeds the accepted ceiling"
METRICS_REVISION_MESSAGES: frozenset[str] = frozenset({MSG_SIZE, MSG_CEILING, MSG_DIGEST})
ATTEMPT_FACT_KEYS: frozenset[str] = frozenset({"error", "kind", "status", "url"})

ZIP_RATIO = 16
ZIP_FLOOR_BYTES = 64 * 1024 * 1024
ZIP_ABSOLUTE_CEILING_BYTES = 4 * 1024 * 1024 * 1024
ZIP_POLICY_EQUATION = "min(4 GiB, max(64 MiB, compressed_bytes * 16))"

STATE_APPLICATION_ID = 0x43324732
STATE_USER_VERSION = 7
MINIMUM_OPERATING_RESERVE_BYTES = 16 * 2**30
RESERVE_DIVISOR = 5

RUN7_RECEIPT_SHA256 = (
    "8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab"
)
RUN7_RUN_ID = "902a6fdb3d405b8db18e05564399f38ffddd7032dfaa2df707ef2d9e8d30e15b"
GENERATION0_SOURCE_SHA256 = (
    "af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d"
)
GENERATION0_CLI_SHA256 = (
    "6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043"
)
GENERATION0_STATE_BYTES = 2_386_247_680
GENERATION0_STATE_SHA256 = (
    "5a5bdc8745c51b1b4b4a15e0de12b7dfa405f8c3a8ae1ba759aa0b6fd7ee33b4"
)
GENERATION0_WAL_BYTES = 0
GENERATION0_WAL_SHA256 = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)
GENERATION0_SHM_BYTES = 32_768
GENERATION0_SHM_SHA256 = (
    "fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb"
)

EXIT_COMPLETE = 0
EXIT_BLOCKED = 1
EXIT_RESUMABLE_PARTIAL = 2
EXIT_UNSAFE = 6

HEX64 = re.compile(r"^[0-9a-f]{64}$")
SINGLE_PART_ETAG = re.compile(r"^[0-9a-f]{32}$")
ECONOMIC_DATE = re.compile(r"-(\d{4}-\d{2}-\d{2})\.zip$")
PENDING_KEY_PATTERNS: Mapping[str, re.Pattern[str]] = {
    FAMILY_METRICS: re.compile(
        r"^data/futures/um/daily/metrics/"
        r"(?P<symbol>[A-Z0-9_]+)/(?P=symbol)-metrics-"
        r"(?P<date>\d{4}-\d{2}-\d{2})\.zip$"
    ),
    FAMILY_BOOK_TICKER: re.compile(
        r"^data/futures/um/daily/bookTicker/"
        r"(?P<symbol>[A-Z0-9_]+)/(?P=symbol)-bookTicker-"
        r"(?P<date>\d{4}-\d{2}-\d{2})\.zip$"
    ),
}
SIDECAR_LINE = re.compile(r"^([0-9a-fA-F]{64})[ \t]+(\S+)\s*$", re.MULTILINE)
TABLE_NAMES: frozenset[str] = frozenset(
    {
        "attempt",
        "authority",
        "charge_transition",
        "coinalyze_charge",
        "coinalyze_ledger",
        "completion",
        "plan_entry",
        "run_metadata",
        "run_publication",
        "run_seal",
        "seal_head",
        "sidecar_fact",
        "terminal_gap",
    }
)
INDEX_NAMES: frozenset[str] = frozenset(
    {
        "idx_attempt_identity",
        "idx_charge_identity",
        "idx_completion_content",
        "idx_completion_state",
        "idx_plan_kind",
        "idx_run_seal_receipt",
        "idx_transition_identity",
    }
)
PINS_JSON_KEYS: frozenset[str] = frozenset(
    {
        "amendment_ledger_sha256",
        "attestation_282_sha256",
        "capacity_cli_sha256",
        "capacity_source_sha256",
        "coinalyze_logical_receipts",
        "coinalyze_supported",
        "coinalyze_unsupported",
        "combined_bytes",
        "combined_objects",
        "contract_metadata_sha256",
        "cost_bytes",
        "cost_manifest_sha256",
        "cost_objects",
        "destination",
        "device",
        "holdout_boundary_id",
        "listing_checkpoint_sha256",
        "lock_sha256",
        "main_selected_bytes",
        "main_selected_objects",
        "manifest_compressed_sha256",
        "manifest_uncompressed_sha256",
        "new_binance_raw_bytes",
        "new_coinalyze_raw_bytes",
        "progress_sha256",
        "qualification_cli_sha256",
        "qualification_source_sha256",
        "receipt_258_sha256",
        "report_sha256",
        "retained_credit_bytes",
        "retained_credit_objects",
        "stable_requirement_bytes",
    }
)
SEMANTIC_RECEIPT_KEYS: tuple[str, ...] = (
    "schema_version",
    "ticket",
    "adr",
    "policy_identity",
    "code_identity",
    "generation_0",
    "pending",
    "classification",
    "bytes",
    "listing",
    "zip_work_policy",
    "manifest",
    "lineage",
    "authorization",
)
AUTHORIZATION = {
    "candidate_accepted": False,
    "acquisition_authorized": False,
    "gate_2_accepted": False,
    "statement": (
        "this candidate is listing-only evidence for a later reviewer decision; "
        "it accepts no revision, authorizes no acquisition, and changes no "
        "generation-0 state"
    ),
}
BYTE_EQUATION = "current_listed_bytes - old_planned_bytes = delta_bytes"
CAPACITY_STATEMENT = (
    "capacity projection is measurement evidence only; it accepts no "
    "candidate, authorizes no acquisition, and changes no ticket state"
)
PRODUCTION_MESSAGE_COUNTS: tuple[tuple[str, int], ...] = (
    (MSG_SIZE, 12_576),
    (MSG_CEILING, 38_344),
    (MSG_DIGEST, 1),
    (MSG_ZIP, 354),
)
PRODUCTION_FAMILY_COVERAGE: tuple[tuple[str, int, int, int, int], ...] = (
    ("daily/bookDepth", 2_235, 2_235, 0, 0),
    ("daily/bookTicker", 909, 555, 0, 354),
    ("daily/indexPriceKlines", 12_266, 12_266, 0, 0),
    ("daily/klines", 13_710, 13_710, 0, 0),
    ("daily/markPriceKlines", 14_096, 14_096, 0, 0),
    ("daily/metrics", 573_786, 522_865, 0, 50_921),
    ("daily/premiumIndexKlines", 11_439, 11_439, 0, 0),
    ("monthly/fundingRate", 21_035, 21_035, 0, 0),
    ("monthly/indexPriceKlines", 21_721, 21_721, 0, 0),
    ("monthly/klines", 21_932, 21_932, 0, 0),
    ("monthly/markPriceKlines", 22_286, 22_286, 0, 0),
    ("monthly/premiumIndexKlines", 20_932, 20_932, 0, 0),
)


class RevisionCandidateError(RuntimeError):
    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = dict(context or {})


class BlockedCandidateError(RevisionCandidateError):
    """Typed blocker; generation 0 is left untouched and no locator is committed."""


class UnsafeCandidateError(RevisionCandidateError):
    """Lock, path, device, or follow-safety failure."""


class ListingInterrupted(RevisionCandidateError):
    """Durable listing progress exists; no candidate locator was committed."""


@dataclass(frozen=True, slots=True)
class PlannerPins:
    run7_receipt_sha256: str = RUN7_RECEIPT_SHA256
    run7_run_id: str = RUN7_RUN_ID
    generation0_source_sha256: str = GENERATION0_SOURCE_SHA256
    generation0_cli_sha256: str = GENERATION0_CLI_SHA256
    generation0_policy_identity: str = GENERATION0_POLICY_IDENTITY
    expected_plan_rows: int = 737_119
    expected_attempts: int = 1_632_378
    expected_completions: int = 685_642
    expected_sidecars: int = 736_347
    expected_gaps: int = 202
    expected_runs: int = 7
    expected_publications: int = 7
    expected_seals: int = 7
    expected_charges: int = 569
    expected_charge_transitions: int = 1_707
    expected_pending_metrics: int = 50_921
    expected_pending_book_ticker: int = 354
    expected_open_charges: int = 0
    expected_unfinished_runs: int = 0
    expected_attempt_hi: int = 1_632_378
    expected_completion_hi: int = 685_642
    expected_sidecar_hi: int = 736_347
    expected_charge_hi: int = 569
    expected_transition_hi: int = 1_707
    expected_run_hi: int = 7
    expected_seal_hi: int = 6
    expected_charged_bytes: int = 20_126_995
    expected_charge_points: int = 479_340
    expected_reserved_transitions: int = 569
    expected_published_transitions: int = 569
    expected_settled_transitions: int = 569
    expected_inventory_complete: int = 1
    expected_liquidation_complete: int = 569
    expected_state_bytes: int = GENERATION0_STATE_BYTES
    expected_state_sha256: str = GENERATION0_STATE_SHA256
    expected_wal_bytes: int = GENERATION0_WAL_BYTES
    expected_wal_sha256: str = GENERATION0_WAL_SHA256
    expected_shm_bytes: int = GENERATION0_SHM_BYTES
    expected_shm_sha256: str = GENERATION0_SHM_SHA256
    expected_pending_metrics_bytes: int = 535_441_899
    expected_pending_book_bytes: int = 8_661_432_243
    application_id: int = STATE_APPLICATION_ID
    user_version: int = STATE_USER_VERSION
    destination: str = FIXED_STORE_ROOT
    require_generation0_code_hashes: bool = True
    require_physical_state_pins: bool = True
    expected_message_counts: tuple[tuple[str, int], ...] = PRODUCTION_MESSAGE_COUNTS
    expected_family_coverage: tuple[tuple[str, int, int, int, int], ...] = (
        PRODUCTION_FAMILY_COVERAGE
    )


PRODUCTION_PINS = PlannerPins()


@dataclass(frozen=True, slots=True)
class ListingObject:
    key: str
    size: int
    etag: str | None


@dataclass(frozen=True, slots=True)
class ListingResponse:
    status_code: int
    url: str
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True, slots=True)
class PendingIdentity:
    provider: str
    identity: str
    family: str
    symbol: str
    listed_bytes: int
    sidecar_key: str
    payload: Mapping[str, Any]
    envelope: Mapping[str, Any]
    attempt_id: int
    attempt_class: str
    status_code: int
    ended_at: str
    fact: Mapping[str, Any]
    terminal_message: str
    sidecar_sha256: str
    sidecar_path: str
    sidecar_bytes: int
    provider_checksum: str
    sidecar_body: bytes


class ListingTransport(Protocol):
    def fetch(self, url: str, *, max_bytes: int) -> ListingResponse:
        """Return one complete no-redirect listing response. Must not GET a raw ZIP."""


@dataclass
class PlannerHooks:
    transport: ListingTransport | None = None
    available_bytes: Callable[[int], int] | None = None
    before_network: Callable[[], None] | None = None
    after_page_publish: Callable[[Mapping[str, Any]], None] | None = None
    on_live_row_count: Callable[[int], None] | None = None
    on_listing_live_count: Callable[[int], None] | None = None
    on_network: Callable[[str], None] | None = None
    interrupt_after_pages: int | None = None
    interrupt_before_locator: Callable[[], None] | None = None
    interrupt_after_private_manifest: Callable[[], None] | None = None
    interrupt_after_manifest_publish: Callable[[], None] | None = None
    interrupt_after_lineage_publish: Callable[[], None] | None = None
    interrupt_after_receipt_publish: Callable[[], None] | None = None
    before_locator_commit: Callable[[], None] | None = None
    before_recovery_return: Callable[[], None] | None = None
    after_generation_open: Callable[[int], None] | None = None
    after_content_open: Callable[[int], None] | None = None
    after_candidate_open: Callable[[int], None] | None = None
    retrieval_clock: Callable[[], str] | None = None
    after_sqlite_open: Callable[[str, sqlite3.Connection], None] | None = None
    after_sqlite_leaf_open: Callable[[str, int], None] | None = None


@dataclass(frozen=True, slots=True)
class PlannerPaths:
    repository: Path
    store_root: Path
    gate2_root: Path
    candidate_root: Path
    planner_source_path: Path
    planner_cli_path: Path
    acquisition_source_path: Path
    acquisition_cli_path: Path


class HeldFds:
    def __init__(self) -> None:
        self._fds: list[int] = []

    def add(self, fd: int) -> int:
        self._fds.append(fd)
        return fd

    def close_all(self) -> None:
        while self._fds:
            fd = self._fds.pop()
            try:
                os.close(fd)
            except OSError:
                pass


def production_paths(repository: Path) -> PlannerPaths:
    repo = Path(repository)
    store = repo / FIXED_STORE_ROOT
    return PlannerPaths(
        repository=repo,
        store_root=store,
        gate2_root=store / FIXED_ACTIVE_NAME,
        candidate_root=store / FIXED_CANDIDATE_NAME,
        planner_source_path=repo / SOURCE_RELATIVE,
        planner_cli_path=repo / CLI_RELATIVE,
        acquisition_source_path=repo / ACQUISITION_SOURCE_RELATIVE,
        acquisition_cli_path=repo / ACQUISITION_CLI_RELATIVE,
    )


def default_paths(repository: Path, store_root: Path) -> PlannerPaths:
    """Test injection: store-relative gate2 and sibling candidate names only."""

    repo = Path(repository)
    store = Path(store_root)
    return PlannerPaths(
        repository=repo,
        store_root=store,
        gate2_root=store / FIXED_ACTIVE_NAME,
        candidate_root=store / FIXED_CANDIDATE_NAME,
        planner_source_path=repo / SOURCE_RELATIVE,
        planner_cli_path=repo / CLI_RELATIVE,
        acquisition_source_path=repo / ACQUISITION_SOURCE_RELATIVE,
        acquisition_cli_path=repo / ACQUISITION_CLI_RELATIVE,
    )


def canonical_json(payload: Any) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def compact_json(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def md5_hex(payload: bytes) -> str:
    return hashlib.md5(payload, usedforsecurity=False).hexdigest()


def zip_work_ceiling(compressed_bytes: int) -> int:
    if isinstance(compressed_bytes, bool) or type(compressed_bytes) is not int:
        raise BlockedCandidateError("compressed size is not an exact integer")
    if compressed_bytes < 0:
        raise BlockedCandidateError("compressed size is negative")
    return min(ZIP_ABSOLUTE_CEILING_BYTES, max(ZIP_FLOOR_BYTES, compressed_bytes * ZIP_RATIO))


def operating_reserve_bytes(available: int) -> int:
    if isinstance(available, bool) or type(available) is not int or available < 0:
        raise BlockedCandidateError("available bytes are not an exact integer")
    quartered = (available + RESERVE_DIVISOR - 1) // RESERVE_DIVISOR
    return max(MINIMUM_OPERATING_RESERVE_BYTES, quartered)


def listing_request_identity(
    *,
    endpoint: str,
    prefix: str,
    delimiter: str,
    continuation_token: str | None,
) -> dict[str, Any]:
    return {
        "continuation_token": continuation_token,
        "delimiter": delimiter,
        "endpoint": endpoint,
        "list_type": LIST_TYPE,
        "prefix": prefix,
    }


def listing_request_key(identity: Mapping[str, Any]) -> str:
    return sha256_bytes(compact_json(dict(identity)))


def listing_url(identity: Mapping[str, Any]) -> str:
    params: dict[str, str] = {
        "delimiter": str(identity["delimiter"]),
        "list-type": str(identity["list_type"]),
        "prefix": str(identity["prefix"]),
    }
    token = identity.get("continuation_token")
    if token is not None:
        params["continuation-token"] = str(token)
    return str(identity["endpoint"]) + "?" + urllib.parse.urlencode(params)


def _hex_digest(value: Any, *, label: str) -> str:
    if type(value) is not str or HEX64.fullmatch(value) is None:
        raise BlockedCandidateError(f"{label} is not sha256")
    return value


def _exact_int(value: Any, *, label: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise BlockedCandidateError(f"{label} is not an exact integer")
    if minimum is not None and value < minimum:
        raise BlockedCandidateError(f"{label} is below its bound")
    return value


def _require(
    condition: bool,
    message: str,
    context: Mapping[str, Any] | None = None,
    *,
    unsafe: bool = False,
) -> None:
    if condition:
        return
    if unsafe:
        raise UnsafeCandidateError(message, context=context)
    raise BlockedCandidateError(message, context=context)


def hash_fd(fd: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, CHUNK_SIZE)
        if not chunk:
            break
        size += len(chunk)
        digest.update(chunk)
    os.lseek(fd, 0, os.SEEK_SET)
    return digest.hexdigest(), size


def _read_fd_bounded(fd: int, *, ceiling: int, label: str) -> bytes:
    if ceiling < 0:
        raise UnsafeCandidateError("invalid bounded-read ceiling")
    chunks: list[bytes] = []
    size = 0
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, min(CHUNK_SIZE, ceiling - size + 1))
        if not chunk:
            break
        chunks.append(chunk)
        size += len(chunk)
        if size > ceiling:
            raise BlockedCandidateError(f"{label} exceeds the accepted byte ceiling")
    os.lseek(fd, 0, os.SEEK_SET)
    return b"".join(chunks)


def _open_optional_regular(parent_fd: int, name: str) -> int | None:
    """Return None only for a genuinely absent leaf; every unsafe leaf fails closed."""

    try:
        st = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise UnsafeCandidateError("an optional leaf cannot be inspected safely") from exc
    if stat.S_ISLNK(st.st_mode):
        raise UnsafeCandidateError(f"{name} is a symlink")
    if not stat.S_ISREG(st.st_mode):
        raise UnsafeCandidateError(f"{name} is not a regular file")
    return open_child_file(parent_fd, name)


def _regular_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(value.st_dev),
        int(value.st_ino),
        int(value.st_mode),
        int(value.st_size),
        int(value.st_mtime_ns),
    )


@contextmanager
def _bound_named_regular(parent_fd: int, name: str, *, label: str) -> Iterator[int]:
    """Hold and rebind one no-follow regular name for the complete read."""

    try:
        named_before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        raise UnsafeCandidateError(f"{label} name cannot be inspected safely") from exc
    if stat.S_ISLNK(named_before.st_mode) or not stat.S_ISREG(named_before.st_mode):
        raise UnsafeCandidateError(f"{label} name is not a regular file")
    fd = open_child_file(parent_fd, name)
    try:
        opened_before = os.fstat(fd)
        _require(
            _regular_identity(opened_before) == _regular_identity(named_before),
            f"{label} opened descriptor is not the named leaf",
            unsafe=True,
        )
        yield fd
        opened_after = os.fstat(fd)
        try:
            named_after = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError as exc:
            raise UnsafeCandidateError(f"{label} name changed during authentication") from exc
        _require(
            _regular_identity(opened_after) == _regular_identity(opened_before)
            and _regular_identity(named_after) == _regular_identity(opened_before),
            f"{label} identity changed during authentication",
            unsafe=True,
        )
    finally:
        os.close(fd)


def _read_bound_named_regular(
    parent_fd: int,
    name: str,
    *,
    ceiling: int,
    label: str,
) -> bytes:
    with _bound_named_regular(parent_fd, name, label=label) as fd:
        return _read_fd_bounded(fd, ceiling=ceiling, label=label)


def _utc_retrieval_clock(hooks: PlannerHooks) -> str:
    value = (
        hooks.retrieval_clock()
        if hooks.retrieval_clock is not None
        else datetime.now(timezone.utc).isoformat(timespec="microseconds")
    )
    if type(value) is not str or not value or value != value.strip():
        raise BlockedCandidateError("retrieval clock is not a canonical string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BlockedCandidateError("retrieval clock is not RFC3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise BlockedCandidateError("retrieval clock is not UTC")
    return value


def _canonical_headers(headers: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(headers, Mapping):
        raise BlockedCandidateError("listing response headers are not a mapping")
    result: dict[str, str] = {}
    if len(headers) > 128:
        raise BlockedCandidateError("listing response has too many headers")
    total = 0
    for raw_name, raw_value in headers.items():
        if type(raw_name) is not str or type(raw_value) is not str:
            raise BlockedCandidateError("listing response header is not text")
        name = raw_name.strip().lower()
        value = raw_value.strip()
        if not name or name != raw_name.lower().strip() or "\n" in value or "\r" in value:
            raise BlockedCandidateError("listing response header is not canonical")
        if name in result:
            raise BlockedCandidateError("listing response has duplicate canonical headers")
        total += len(name.encode("utf-8")) + len(value.encode("utf-8"))
        if len(name) > 256 or len(value) > 8192 or total > 65_536:
            raise BlockedCandidateError("listing response headers exceed the accepted ceiling")
        result[name] = value
    return dict(sorted(result.items()))


def _single_part_etag(value: Any, *, label: str) -> str:
    if type(value) is not str:
        raise BlockedCandidateError(f"{label} is missing")
    normalized = value.strip().strip('"').lower()
    if SINGLE_PART_ETAG.fullmatch(normalized) is None:
        raise BlockedCandidateError(f"{label} is not a single-part MD5 ETag")
    return normalized


def _normalize_sql(text: str) -> str:
    return " ".join(str(text or "").split())


def _local_tag(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def parse_s3_list_bucket(
    xml_text: str,
    *,
    request: Mapping[str, Any],
) -> tuple[list[str], list[ListingObject], bool, str | None]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise BlockedCandidateError("listing page is not XML") from exc
    if _local_tag(root.tag) != "ListBucketResult":
        raise BlockedCandidateError("listing root element is not ListBucketResult")
    seen: dict[str, str | None] = {}
    prefixes: list[str] = []
    objects: list[ListingObject] = []
    next_v1: str | None = None

    def _set_control(name: str, value: str | None) -> None:
        if name in seen:
            raise BlockedCandidateError(
                "listing page has duplicate control elements",
                context={"field": name},
            )
        seen[name] = value

    for node in list(root):
        local = _local_tag(node.tag)
        if local in {
            "Prefix",
            "Delimiter",
            "ContinuationToken",
            "NextContinuationToken",
            "IsTruncated",
            "NextMarker",
            "Name",
            "MaxKeys",
            "EncodingType",
            "KeyCount",
            "StartAfter",
        }:
            _set_control(local, None if node.text is None else str(node.text))
            if local == "NextMarker" and node.text:
                next_v1 = str(node.text)
        elif local == "CommonPrefixes":
            prefix_el = None
            for child in list(node):
                if _local_tag(child.tag) == "Prefix":
                    if prefix_el is not None:
                        raise BlockedCandidateError("CommonPrefixes has duplicate Prefix")
                    prefix_el = child
            if prefix_el is None or not prefix_el.text:
                raise BlockedCandidateError("CommonPrefixes is missing Prefix")
            prefixes.append(str(prefix_el.text))
        elif local == "Contents":
            fields: dict[str, str] = {}
            for child in list(node):
                name = _local_tag(child.tag)
                if name in fields:
                    raise BlockedCandidateError(
                        "Contents has duplicate fields", context={"field": name}
                    )
                fields[name] = "" if child.text is None else str(child.text)
            key = fields.get("Key")
            if not key or key.endswith("/"):
                raise BlockedCandidateError("listing object key is missing")
            size_text = fields.get("Size")
            if size_text is None:
                raise BlockedCandidateError("listing object size is missing")
            try:
                size = int(size_text)
            except ValueError as exc:
                raise BlockedCandidateError("listing object size is not an integer") from exc
            if size < 0:
                raise BlockedCandidateError("listing object size is negative")
            etag_raw = fields.get("ETag")
            etag = None if etag_raw is None else etag_raw.strip().strip('"').lower()
            objects.append(ListingObject(key=str(key), size=size, etag=etag))
        else:
            raise BlockedCandidateError(
                "listing page has an unknown element", context={"element": local}
            )
    if "IsTruncated" not in seen:
        raise BlockedCandidateError("listing page is missing IsTruncated")
    truncated_text = seen["IsTruncated"]
    if truncated_text not in {"true", "false"}:
        raise BlockedCandidateError("listing IsTruncated is not an exact boolean")
    truncated = truncated_text == "true"
    next_v2 = seen.get("NextContinuationToken")
    if truncated and not next_v2:
        raise BlockedCandidateError(
            "truncated S3 listing is not ListObjectsV2; NextMarker cannot continue a V2 request",
            context={"next_marker": next_v1},
        )
    if not truncated and next_v2:
        raise BlockedCandidateError("unterminated listing page has a continuation token")
    prefix = str(request["prefix"])
    delimiter = str(request["delimiter"])
    token = request.get("continuation_token")
    if "Prefix" not in seen or "Delimiter" not in seen:
        raise BlockedCandidateError("listing page is missing exact request controls")
    echoed_prefix = seen.get("Prefix")
    echoed_delimiter = seen.get("Delimiter")
    echoed_token = seen.get("ContinuationToken")
    _require(echoed_prefix == prefix, "listing Prefix does not echo the request")
    _require(echoed_delimiter == delimiter, "listing Delimiter does not echo the request")
    if token is None:
        _require(
            echoed_token in {None, ""},
            "listing ContinuationToken does not echo the request",
        )
    else:
        _require(echoed_token == token, "listing ContinuationToken does not echo the request")
    _validate_scope(prefix, delimiter, prefixes, objects)
    if len(objects) + len(prefixes) > PAGE_OBJECT_CEILING:
        raise BlockedCandidateError("listing page exceeds the object ceiling")
    if len(set(prefixes)) != len(prefixes):
        raise BlockedCandidateError("listing page repeats a common-prefix edge")
    if len({obj.key for obj in objects}) != len(objects):
        raise BlockedCandidateError("listing page repeats an object key")
    if next_v2 is not None and len(next_v2) > TOKEN_LENGTH_CEILING:
        raise BlockedCandidateError("continuation token exceeds the accepted ceiling")
    return prefixes, objects, truncated, next_v2


def _validate_scope(
    prefix: str,
    delimiter: str,
    prefixes: Sequence[str],
    objects: Sequence[ListingObject],
) -> None:
    for child in prefixes:
        if not child.startswith(prefix) or child == prefix:
            raise BlockedCandidateError(
                "common prefix is outside the requested prefix",
                context={"prefix": child},
            )
        if delimiter and not child.endswith(delimiter):
            raise BlockedCandidateError("common prefix is not a direct child")
        remainder = child[len(prefix) : -len(delimiter)] if delimiter else child[len(prefix) :]
        if not remainder or delimiter in remainder:
            raise BlockedCandidateError(
                "common prefix is not a direct child",
                context={"prefix": child},
            )
        if len(child) > KEY_LENGTH_CEILING:
            raise BlockedCandidateError("listing prefix exceeds the accepted ceiling")
    for obj in objects:
        if len(obj.key) > KEY_LENGTH_CEILING:
            raise BlockedCandidateError("listing key exceeds the accepted ceiling")
        if not obj.key.startswith(prefix) or obj.key == prefix:
            raise BlockedCandidateError(
                "listing object is outside the requested prefix",
                context={"key": obj.key},
            )
        remainder = obj.key[len(prefix) :]
        if delimiter and delimiter in remainder:
            raise BlockedCandidateError(
                "listing object is not a direct child of the requested prefix",
                context={"key": obj.key},
            )


def write_s3_list_bucket(
    *,
    prefixes: Sequence[str] = (),
    objects: Sequence[ListingObject] = (),
    truncated: bool = False,
    continuation: str | None = None,
    next_marker: str | None = None,
    prefix: str | None = None,
    delimiter: str | None = None,
    continuation_token: str | None = None,
) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">',
    ]
    if prefix is not None:
        parts.append(f"<Prefix>{_xml(prefix)}</Prefix>")
    if delimiter is not None:
        parts.append(f"<Delimiter>{_xml(delimiter)}</Delimiter>")
    if continuation_token is not None:
        parts.append(f"<ContinuationToken>{_xml(continuation_token)}</ContinuationToken>")
    parts.append(f"<IsTruncated>{'true' if truncated else 'false'}</IsTruncated>")
    if continuation is not None:
        parts.append(f"<NextContinuationToken>{_xml(continuation)}</NextContinuationToken>")
    if next_marker is not None:
        parts.append(f"<NextMarker>{_xml(next_marker)}</NextMarker>")
    for item in prefixes:
        parts.append(f"<CommonPrefixes><Prefix>{_xml(item)}</Prefix></CommonPrefixes>")
    for obj in objects:
        etag = "" if obj.etag is None else f"<ETag>&quot;{_xml(obj.etag)}&quot;</ETag>"
        parts.append(
            f"<Contents><Key>{_xml(obj.key)}</Key><Size>{int(obj.size)}</Size>{etag}</Contents>"
        )
    parts.append("</ListBucketResult>")
    return "".join(parts)


def parse_sidecar(body: bytes, *, basename: str) -> str:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BlockedCandidateError("sidecar is not UTF-8") from exc
    match = SIDECAR_LINE.fullmatch(text)
    if match is None:
        raise BlockedCandidateError(
            "sidecar does not name exactly one checksum and basename",
            context={"basename": basename},
        )
    digest, name = match.group(1).lower(), match.group(2)
    if name != basename:
        raise BlockedCandidateError(
            "sidecar names a different object basename",
            context={"sidecar_filename": name, "basename": basename},
        )
    return _hex_digest(digest, label="sidecar checksum")


def family_of(key: str) -> str:
    for family in ALL_BINANCE_FAMILIES:
        cadence, _, name = family.partition("/")
        if f"/{cadence}/{name}/" in key:
            return family
    return ""


def symbol_of(key: str, family: str) -> str:
    cadence, _, name = family.partition("/")
    marker = f"/{cadence}/{name}/"
    tail = key.split(marker, 1)[1] if marker in key else ""
    return tail.split("/", 1)[0] if tail else ""


def content_path_parts(digest: str) -> tuple[str, str]:
    digest = _hex_digest(digest, label="content digest")
    return digest[:2], digest


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        raise BlockedCandidateError("listing redirect is forbidden")


class UrllibListingTransport:
    def fetch(self, url: str, *, max_bytes: int) -> ListingResponse:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https":
            raise BlockedCandidateError("listing URL is not HTTPS")
        if parsed.netloc != VISION_S3_HOST or parsed.path != VISION_S3_PATH:
            raise BlockedCandidateError("listing URL is not the official S3 listing host")
        if ".zip" in parsed.path.lower():
            raise BlockedCandidateError("raw ZIP GET is forbidden")
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": "cex002-gate2-revision-candidate"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(request, timeout=60) as response:
                status = int(getattr(response, "status", response.getcode()))
                final_url = str(response.geturl())
                headers = _canonical_headers(
                    {str(k).lower(): str(v) for k, v in response.headers.items()}
                )
                chunks: list[bytes] = []
                size = 0
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise BlockedCandidateError(
                            "listing page exceeded the accepted byte ceiling"
                        )
                    chunks.append(chunk)
                body = b"".join(chunks)
        except BlockedCandidateError:
            raise
        except (TimeoutError, ConnectionError, InterruptedError, BrokenPipeError) as exc:
            raise ListingInterrupted("listing transport was interrupted") from exc
        except http.client.IncompleteRead as exc:
            raise ListingInterrupted("listing response was interrupted") from exc
        except urllib.error.HTTPError as exc:
            if exc.code >= 500:
                raise ListingInterrupted("listing server error") from exc
            raise BlockedCandidateError(
                "listing request failed", context={"status": exc.code}
            ) from exc
        except urllib.error.URLError as exc:
            raise ListingInterrupted("listing request failed transiently") from exc
        if status != 200:
            raise BlockedCandidateError(
                "listing status is not 200", context={"status": status}
            )
        if final_url != url:
            raise BlockedCandidateError("listing final URL diverged from the request")
        content_length = headers.get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError as exc:
                raise BlockedCandidateError(
                    "listing Content-Length is not an integer"
                ) from exc
            if declared != len(body):
                raise BlockedCandidateError("listing Content-Length does not match the body")
        return ListingResponse(status_code=status, url=final_url, headers=headers, body=body)


def _renameat2_noreplace(old_dir: int, old_name: str, new_dir: int, new_name: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        renameat2 = libc.renameat2
    except AttributeError as exc:
        raise UnsafeCandidateError("renameat2 is unavailable") from exc
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    result = renameat2(
        old_dir,
        old_name.encode("utf-8"),
        new_dir,
        new_name.encode("utf-8"),
        RENAME_NOREPLACE,
    )
    if result != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))


def open_root_dir(root: Path, *, create: bool = False) -> int:
    absolute = Path(root).absolute()
    parts = absolute.parts
    if not parts or parts[0] != os.sep:
        raise UnsafeCandidateError("the accepted root is not an absolute directory")
    try:
        current = os.open(os.sep, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise UnsafeCandidateError("the accepted root is not a no-follow directory") from exc
    try:
        for part in parts[1:]:
            if part in {"", ".", ".."} or os.sep in part:
                raise UnsafeCandidateError("unsafe path component", context={"part": part})
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=current)
                except FileExistsError:
                    pass
            try:
                nxt = os.open(
                    part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current
                )
            except OSError as exc:
                os.close(current)
                raise UnsafeCandidateError(
                    "a path component cannot be opened no-follow"
                ) from exc
            os.close(current)
            current = nxt
            if not stat.S_ISDIR(os.fstat(current).st_mode):
                os.close(current)
                raise UnsafeCandidateError("a path component is not a directory")
        return current
    except Exception:
        try:
            os.close(current)
        except OSError:
            pass
        raise


def open_child_dir(parent_fd: int, name: str, *, create: bool = False) -> int:
    if name in {"", ".", ".."} or os.sep in name or "/" in name:
        raise UnsafeCandidateError("unsafe path component", context={"part": name})
    if create:
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError:
            pass
    try:
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
    except OSError as exc:
        raise UnsafeCandidateError("a nested directory cannot be opened no-follow") from exc
    if not stat.S_ISDIR(os.fstat(fd).st_mode):
        os.close(fd)
        raise UnsafeCandidateError("a nested path is not a directory")
    return fd


def open_child_file(parent_fd: int, name: str, *, write: bool = False) -> int:
    if name in {"", ".", ".."} or os.sep in name or "/" in name:
        raise UnsafeCandidateError("unsafe path component", context={"part": name})
    flags = os.O_NOFOLLOW | (os.O_RDWR if write else os.O_RDONLY)
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        raise UnsafeCandidateError("a regular file cannot be opened no-follow") from exc
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise UnsafeCandidateError("path is not a regular file")
    return fd


def open_under(parent_fd: int, parts: Sequence[str], *, create: bool = False) -> int:
    current = parent_fd
    owned: list[int] = []
    try:
        for index, part in enumerate(parts):
            last = index == len(parts) - 1
            nxt = open_child_dir(current, part, create=create) if not last or True else current
            if current is not parent_fd:
                owned.append(current)
            current = nxt
        return current
    except Exception:
        if current is not parent_fd:
            try:
                os.close(current)
            except OSError:
                pass
        raise
    finally:
        for fd in owned:
            try:
                os.close(fd)
            except OSError:
                pass


def open_dir_chain_from(parent_fd: int, parts: Sequence[str], *, create: bool = False) -> int:
    current = None
    try:
        cursor = parent_fd
        for part in parts:
            nxt = open_child_dir(cursor, part, create=create)
            if current is not None:
                os.close(current)
            current = nxt
            cursor = nxt
        if current is None:
            raise UnsafeCandidateError("directory chain is empty")
        return current
    except Exception:
        if current is not None:
            try:
                os.close(current)
            except OSError:
                pass
        raise


def _cleanup_partials(directory: int) -> None:
    try:
        names = os.listdir(directory)
    except OSError:
        return
    for name in names:
        if not name.startswith(".partial-"):
            continue
        try:
            info = os.stat(name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if stat.S_ISREG(info.st_mode):
            try:
                os.unlink(name, dir_fd=directory)
            except FileNotFoundError:
                continue


def _leaf_stat_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(value.st_dev),
        int(value.st_ino),
        int(value.st_mode),
        int(value.st_size),
        int(value.st_mtime_ns),
    )


def _leaf_snapshot(
    dir_fd: int,
    name: str,
    hooks: PlannerHooks | None = None,
) -> dict[str, Any] | None:
    try:
        named_before = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise UnsafeCandidateError(f"{name} cannot be inspected safely") from exc
    if stat.S_ISLNK(named_before.st_mode):
        raise UnsafeCandidateError(f"{name} is a symlink")
    if not stat.S_ISREG(named_before.st_mode):
        raise UnsafeCandidateError(f"{name} is not a regular file")
    fd = open_child_file(dir_fd, name, write=False)
    try:
        opened_before = os.fstat(fd)
        _require(
            _leaf_stat_identity(opened_before) == _leaf_stat_identity(named_before),
            f"{name} opened descriptor is not the named leaf",
            unsafe=True,
        )
        if hooks is not None and hooks.after_sqlite_leaf_open is not None:
            hooks.after_sqlite_leaf_open(name, fd)
        digest, size = hash_fd(fd)
        opened_after = os.fstat(fd)
        try:
            named_after = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        except OSError as exc:
            raise UnsafeCandidateError(f"{name} name changed during hashing") from exc
        _require(
            _leaf_stat_identity(opened_after) == _leaf_stat_identity(opened_before)
            and _leaf_stat_identity(named_after) == _leaf_stat_identity(opened_before),
            f"{name} identity changed during hashing",
            unsafe=True,
        )
    finally:
        os.close(fd)
    return {
        "bytes": size,
        "device": int(opened_after.st_dev),
        "inode": int(opened_after.st_ino),
        "mode": int(stat.S_IMODE(opened_after.st_mode)),
        "mtime_ns": int(opened_after.st_mtime_ns),
        "name": name,
        "sha256": digest,
    }


def snapshot_sqlite_leaves(
    gate2_fd: int,
    hooks: PlannerHooks | None = None,
) -> dict[str, Any]:
    return {
        "shm": _leaf_snapshot(gate2_fd, SQLITE_SHM_NAME, hooks),
        "state": _leaf_snapshot(gate2_fd, SQLITE_NAME, hooks),
        "wal": _leaf_snapshot(gate2_fd, SQLITE_WAL_NAME, hooks),
    }


def inventory_tree(dir_fd: int, *, prefix: str = ".") -> list[dict[str, Any]]:
    """No-follow inventory used by tests to prove zero active-tree side effects."""

    entries: list[dict[str, Any]] = []
    st = os.fstat(dir_fd)
    entries.append(
        {
            "bytes": 0,
            "inode": int(st.st_ino),
            "mode": int(stat.S_IMODE(st.st_mode)),
            "mtime_ns": int(st.st_mtime_ns),
            "path": prefix,
            "sha256": None,
            "type": "directory",
        }
    )
    for name in sorted(os.listdir(dir_fd)):
        child_prefix = name if prefix == "." else f"{prefix}/{name}"
        try:
            info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            entries.append(
                {
                    "bytes": 0,
                    "inode": int(info.st_ino),
                    "mode": int(stat.S_IMODE(info.st_mode)),
                    "mtime_ns": int(info.st_mtime_ns),
                    "path": child_prefix,
                    "sha256": None,
                    "type": "symlink",
                }
            )
            continue
        if stat.S_ISDIR(info.st_mode):
            child = open_child_dir(dir_fd, name, create=False)
            try:
                entries.extend(inventory_tree(child, prefix=child_prefix))
            finally:
                os.close(child)
            continue
        if not stat.S_ISREG(info.st_mode):
            raise UnsafeCandidateError("active tree contains a special file")
        fd = open_child_file(dir_fd, name)
        try:
            digest, size = hash_fd(fd)
        finally:
            os.close(fd)
        entries.append(
            {
                "bytes": size,
                "inode": int(info.st_ino),
                "mode": int(stat.S_IMODE(info.st_mode)),
                "mtime_ns": int(info.st_mtime_ns),
                "path": child_prefix,
                "sha256": digest,
                "type": "regular_file",
            }
        )
    entries.sort(key=lambda item: str(item["path"]))
    return entries


def _acquire_lock(dir_fd: int, name: str, *, create: bool) -> int:
    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
    if create:
        flags |= os.O_CREAT
    try:
        st = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError:
        if not create:
            raise UnsafeCandidateError("acquisition lock is missing")
        st = None
    except OSError as exc:
        raise UnsafeCandidateError("a lock cannot be inspected safely") from exc
    if st is not None:
        if stat.S_ISLNK(st.st_mode):
            raise UnsafeCandidateError("a lock is a symlink")
        if not stat.S_ISREG(st.st_mode):
            raise UnsafeCandidateError("a lock is a special file")
    try:
        fd = os.open(name, flags, 0o600, dir_fd=dir_fd)
    except OSError as exc:
        raise UnsafeCandidateError("a lock cannot be opened no-follow") from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise UnsafeCandidateError("a lock is a special file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise UnsafeCandidateError("another writer holds the acquisition lock") from exc
        return fd
    except Exception:
        os.close(fd)
        raise


def _open_sqlite_immutable(file_fd: int, hooks: PlannerHooks) -> sqlite3.Connection:
    uri = f"file:/proc/self/fd/{file_fd}?mode=ro&immutable=1"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise UnsafeCandidateError("SQLite state cannot be opened immutable") from exc
    try:
        conn.execute("PRAGMA query_only=ON")
        flag = conn.execute("PRAGMA query_only").fetchone()
        if flag is None or int(flag[0]) != 1:
            raise UnsafeCandidateError("SQLite query_only is not enabled")
        try:
            conn.execute("CREATE TABLE revision_candidate_write_probe(x INTEGER)")
        except sqlite3.Error as exc:
            message = str(exc).lower()
            if not (
                "readonly" in message
                or "read-only" in message
                or "query_only" in message
                or "immutable" in message
            ):
                raise UnsafeCandidateError("SQLite write probe failed unexpectedly") from exc
        else:
            raise UnsafeCandidateError("SQLite opened writable")
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN")
        conn.execute(
            "SELECT type, name, rootpage FROM sqlite_schema "
            "ORDER BY type, name LIMIT 1"
        ).fetchone()
        if not conn.in_transaction:
            raise UnsafeCandidateError("SQLite read transaction was not established")
        if hooks.after_sqlite_open is not None:
            hooks.after_sqlite_open(uri, conn)
        return conn
    except Exception:
        conn.close()
        raise


def _hash_under_repo(repo_fd: int, relative: Path) -> str:
    parts = relative.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise BlockedCandidateError("code path is unsafe")
    directory = repo_fd
    owned: list[int] = []
    try:
        for part in parts[:-1]:
            nxt = open_child_dir(directory, part, create=False)
            if directory is not repo_fd:
                owned.append(directory)
            directory = nxt
        fd = open_child_file(directory, parts[-1])
        try:
            digest, _size = hash_fd(fd)
            return digest
        finally:
            os.close(fd)
    except UnsafeCandidateError as exc:
        raise BlockedCandidateError(
            "accepted generation-0 or planner code path is missing",
            context={"path": str(relative), "cause": exc.message},
        ) from exc
    finally:
        for fd in owned:
            try:
                os.close(fd)
            except OSError:
                pass
        if directory is not repo_fd:
            try:
                os.close(directory)
            except OSError:
                pass


def _schema_identity(conn: sqlite3.Connection) -> tuple[str, list[dict[str, str]]]:
    rows = conn.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' "
        "ORDER BY type, name"
    ).fetchall()
    payload = [
        {
            "name": str(row[1]),
            "sql": _normalize_sql(str(row[2] or "")),
            "type": str(row[0]),
        }
        for row in rows
    ]
    names = {item["name"] for item in payload if item["type"] == "table"}
    indexes = {
        item["name"]
        for item in payload
        if item["type"] == "index" and not str(item["name"]).startswith("sqlite_autoindex_")
    }
    extra_tables = sorted(names - TABLE_NAMES)
    missing_tables = sorted(TABLE_NAMES - names)
    if extra_tables or missing_tables:
        raise BlockedCandidateError(
            "SQLite table set changed",
            context={"extra": extra_tables, "missing": missing_tables},
        )
    extra_idx = sorted(indexes - INDEX_NAMES)
    missing_idx = sorted(INDEX_NAMES - indexes)
    if extra_idx or missing_idx:
        raise BlockedCandidateError(
            "SQLite index set changed",
            context={"extra": extra_idx, "missing": missing_idx},
        )
    expected = _expected_schema()
    observed = {(item["type"], item["name"]) for item in payload}
    unexpected_objects = sorted(observed - set(expected))
    missing_objects = sorted(set(expected) - observed)
    if unexpected_objects or missing_objects:
        raise BlockedCandidateError(
            "SQLite schema object set changed",
            context={"extra": unexpected_objects, "missing": missing_objects},
        )
    for item in payload:
        key = (item["type"], item["name"])
        if item["sql"] != expected[key]:
            raise BlockedCandidateError(
                "SQLite schema statement changed",
                context={"name": item["name"], "type": item["type"]},
            )
    return sha256_bytes(canonical_json(payload)), payload


def _expected_schema() -> dict[tuple[str, str], str]:
    expected: dict[tuple[str, str], str] = {}
    for statement in SCHEMA_SQL.split(";"):
        body = statement.strip()
        if not body:
            continue
        head = body.split("(", 1)[0].split()
        kind = head[1].lower()
        name = head[2]
        expected[(kind, name)] = _normalize_sql(body)
    return expected


def _table_count(conn: sqlite3.Connection, table: str) -> int:
    if table not in TABLE_NAMES:
        raise BlockedCandidateError("unknown SQLite table", context={"table": table})
    return int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def _bind_generation0(
    conn: sqlite3.Connection,
    pins: PlannerPins,
    *,
    state_snapshot: Mapping[str, Any],
    device_label: str,
    code_identity: Mapping[str, str],
) -> dict[str, Any]:
    app = conn.execute("PRAGMA application_id").fetchone()
    user = conn.execute("PRAGMA user_version").fetchone()
    integrity = conn.execute("PRAGMA integrity_check").fetchone()
    fk_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
    _require(int(app[0]) == pins.application_id, "SQLite application_id changed")
    _require(int(user[0]) == pins.user_version, "SQLite user_version changed")
    _require(str(integrity[0]) == "ok", "SQLite integrity_check failed")
    _require(len(fk_rows) == 0, "SQLite foreign key violations present")
    schema_sha, _schema = _schema_identity(conn)
    counts = {name: _table_count(conn, name) for name in sorted(TABLE_NAMES)}
    _require(counts["plan_entry"] == pins.expected_plan_rows, "plan row count changed")
    _require(counts["attempt"] == pins.expected_attempts, "attempt count changed")
    _require(counts["completion"] == pins.expected_completions, "completion count changed")
    _require(counts["sidecar_fact"] == pins.expected_sidecars, "sidecar count changed")
    _require(counts["terminal_gap"] == pins.expected_gaps, "gap count changed")
    _require(counts["run_metadata"] == pins.expected_runs, "run count changed")
    _require(counts["run_publication"] == pins.expected_publications, "publication count changed")
    _require(counts["run_seal"] == pins.expected_seals, "seal count changed")
    _require(counts["coinalyze_charge"] == pins.expected_charges, "charge count changed")
    _require(
        counts["charge_transition"] == pins.expected_charge_transitions,
        "charge transition count changed",
    )
    _require(counts["authority"] == 1, "authority cardinality changed")
    authority_rows = conn.execute(
        "SELECT id, plan_identity, plan_receipt_sha256, pins_json, code_json, "
        "destination, device, created_at FROM authority"
    ).fetchall()
    _require(len(authority_rows) == 1, "authority row cardinality changed")
    authority = authority_rows[0]
    _require(int(authority[0]) == 1, "authority id changed")
    plan_identity = _hex_digest(str(authority[1]), label="plan identity")
    plan_receipt = _hex_digest(str(authority[2]), label="plan receipt")
    try:
        pins_doc = json.loads(str(authority[3]))
        code = json.loads(str(authority[4]))
    except json.JSONDecodeError as exc:
        raise BlockedCandidateError("SQLite authority JSON is invalid") from exc
    if type(pins_doc) is not dict or frozenset(pins_doc) != PINS_JSON_KEYS:
        raise BlockedCandidateError("pins_json keys changed")
    if type(code) is not dict:
        raise BlockedCandidateError("SQLite code_json is not an object")
    policy = str(code.get("policy_identity") or "")
    source_sha = str(code.get("acquisition_source_sha256") or "")
    cli_sha = str(code.get("acquisition_cli_sha256") or "")
    if pins.require_generation0_code_hashes:
        _require(policy == pins.generation0_policy_identity, "generation-0 policy identity changed")
        _require(source_sha == pins.generation0_source_sha256, "generation-0 source identity changed")
        _require(cli_sha == pins.generation0_cli_sha256, "generation-0 CLI identity changed")
        _require(
            code_identity["acquisition_source_sha256"] == pins.generation0_source_sha256,
            "held generation-0 source identity changed",
        )
        _require(
            code_identity["acquisition_cli_sha256"] == pins.generation0_cli_sha256,
            "held generation-0 CLI identity changed",
        )
    _require(str(authority[5]) == pins.destination, "authority destination changed")
    _require(str(authority[6]) == device_label, "authority device does not match the live tree")
    unfinished = conn.execute(
        "SELECT COUNT(*) FROM run_metadata WHERE ended_at IS NULL"
    ).fetchone()
    _require(int(unfinished[0]) == pins.expected_unfinished_runs, "unfinished run count changed")
    open_charges = conn.execute(
        "SELECT COUNT(*) FROM coinalyze_charge c WHERE COALESCE("
        "(SELECT t.status FROM charge_transition t WHERE t.provider=c.provider "
        "AND t.identity=c.identity AND t.generation=c.generation "
        "ORDER BY t.seq DESC LIMIT 1), '') != ?",
        (CHARGE_SETTLED,),
    ).fetchone()
    _require(int(open_charges[0]) == pins.expected_open_charges, "open Coinalyze charge count changed")
    head = conn.execute(
        "SELECT receipt_sha256, prefix_digest, attempt_hi, completion_hi, sidecar_hi, "
        "charge_hi, transition_hi, run_hi, seal_hi, predecessor_sha256, receipt_path "
        "FROM seal_head WHERE id=1"
    ).fetchone()
    if head is None:
        raise BlockedCandidateError("SQLite seal head is missing")
    head_receipt = _hex_digest(str(head[0]), label="seal head receipt")
    _require(head_receipt == pins.run7_receipt_sha256, "run-7 seal head receipt changed")
    watermarks = {
        "attempt_hi": int(head[2]),
        "completion_hi": int(head[3]),
        "sidecar_hi": int(head[4]),
        "charge_hi": int(head[5]),
        "transition_hi": int(head[6]),
        "run_hi": int(head[7]),
        "seal_hi": int(head[8]),
    }
    _require(watermarks["attempt_hi"] == pins.expected_attempt_hi, "attempt watermark changed")
    _require(watermarks["completion_hi"] == pins.expected_completion_hi, "completion watermark changed")
    _require(watermarks["sidecar_hi"] == pins.expected_sidecar_hi, "sidecar watermark changed")
    _require(watermarks["charge_hi"] == pins.expected_charge_hi, "charge watermark changed")
    _require(watermarks["transition_hi"] == pins.expected_transition_hi, "transition watermark changed")
    _require(watermarks["run_hi"] == pins.expected_run_hi, "run watermark changed")
    _require(watermarks["seal_hi"] == pins.expected_seal_hi, "seal watermark changed")
    max_attempt = conn.execute("SELECT COALESCE(MAX(id), 0) FROM attempt").fetchone()
    max_completion = conn.execute("SELECT COALESCE(MAX(seq), 0) FROM completion").fetchone()
    max_sidecar = conn.execute("SELECT COALESCE(MAX(seq), 0) FROM sidecar_fact").fetchone()
    max_charge = conn.execute("SELECT COALESCE(MAX(seq), 0) FROM coinalyze_charge").fetchone()
    max_transition = conn.execute("SELECT COALESCE(MAX(seq), 0) FROM charge_transition").fetchone()
    _require(int(max_attempt[0]) == watermarks["attempt_hi"], "attempt watermark does not bound the table")
    _require(int(max_completion[0]) == watermarks["completion_hi"], "completion watermark does not bound the table")
    _require(int(max_sidecar[0]) == watermarks["sidecar_hi"], "sidecar watermark does not bound the table")
    _require(int(max_charge[0]) == watermarks["charge_hi"], "charge watermark does not bound the table")
    _require(
        int(max_transition[0]) == watermarks["transition_hi"],
        "transition watermark does not bound the table",
    )
    run = conn.execute(
        "SELECT run_id, stop_reason, ended_at FROM run_metadata WHERE run_id=?",
        (pins.run7_run_id,),
    ).fetchone()
    if run is None:
        raise BlockedCandidateError("run-7 metadata is missing")
    _require(str(run[1]) == "partial", "run-7 stop reason changed")
    _require(run[2] is not None, "run-7 has no end time")
    publication = conn.execute(
        "SELECT receipt_sha256, receipt_body FROM run_publication WHERE run_id=?",
        (pins.run7_run_id,),
    ).fetchone()
    if publication is None:
        raise BlockedCandidateError("run-7 publication is missing")
    _require(str(publication[0]) == head_receipt, "run publication does not match the seal head")
    body = str(publication[1]).encode("utf-8")
    _require(sha256_bytes(body) == head_receipt, "run publication body does not authenticate")
    seal = conn.execute(
        "SELECT receipt_sha256, prefix_digest FROM run_seal WHERE run_id=?",
        (pins.run7_run_id,),
    ).fetchone()
    if seal is None:
        raise BlockedCandidateError("run-7 seal is missing")
    _require(str(seal[0]) == head_receipt, "run seal does not match the seal head")
    _require(str(seal[1]) == str(head[1]), "run seal prefix digest does not match the head")
    _bind_family_coverage(conn, pins)
    _bind_coinalyze(conn, pins)
    wal_leaf = state_snapshot.get("wal")
    if wal_leaf is not None and int(wal_leaf["bytes"]) != 0:
        raise BlockedCandidateError("generation-0 WAL is not empty")
    if pins.require_physical_state_pins:
        state = state_snapshot["state"]
        wal = state_snapshot["wal"]
        shm = state_snapshot["shm"]
        if state is None:
            raise BlockedCandidateError("generation-0 state file is missing")
        _require(int(state["bytes"]) == pins.expected_state_bytes, "generation-0 state size changed")
        _require(str(state["sha256"]) == pins.expected_state_sha256, "generation-0 state digest changed")
        if wal is None:
            raise BlockedCandidateError("generation-0 WAL leaf is missing")
        _require(int(wal["bytes"]) == pins.expected_wal_bytes, "generation-0 WAL size changed")
        _require(str(wal["sha256"]) == pins.expected_wal_sha256, "generation-0 WAL digest changed")
        if pins.expected_wal_bytes != 0:
            raise BlockedCandidateError("generation-0 WAL is not empty")
        if shm is None:
            raise BlockedCandidateError("generation-0 SHM leaf is missing")
        _require(int(shm["bytes"]) == pins.expected_shm_bytes, "generation-0 SHM size changed")
        _require(str(shm["sha256"]) == pins.expected_shm_sha256, "generation-0 SHM digest changed")
    return {
        "application_id": pins.application_id,
        "authority_destination": str(authority[5]),
        "authority_device": str(authority[6]),
        "acquisition_cli_sha256": cli_sha,
        "acquisition_source_sha256": source_sha,
        "created_at": str(authority[7]),
        "counts": {
            "attempt": counts["attempt"],
            "charge_transition": counts["charge_transition"],
            "coinalyze_charge": counts["coinalyze_charge"],
            "completion": counts["completion"],
            "open_coinalyze_charges": int(open_charges[0]),
            "plan_entry": counts["plan_entry"],
            "run_metadata": counts["run_metadata"],
            "run_publication": counts["run_publication"],
            "run_seal": counts["run_seal"],
            "sidecar_fact": counts["sidecar_fact"],
            "terminal_gap": counts["terminal_gap"],
            "unfinished_runs": int(unfinished[0]),
        },
        "foreign_key_violation_count": 0,
        "integrity_check": "ok",
        "physical": {
            "shm": state_snapshot["shm"],
            "state": state_snapshot["state"],
            "wal": state_snapshot["wal"],
        },
        "pins_json_sha256": sha256_bytes(compact_json(pins_doc)),
        "plan_identity": plan_identity,
        "plan_receipt_sha256": plan_receipt,
        "policy_identity": policy,
        "run7_prefix_digest": str(head[1]),
        "run7_receipt_sha256": head_receipt,
        "run7_run_id": pins.run7_run_id,
        "schema_sha256": schema_sha,
        "user_version": pins.user_version,
        "watermarks": watermarks,
    }


def _bind_family_coverage(conn: sqlite3.Connection, pins: PlannerPins) -> None:
    observed: dict[str, tuple[int, int, int, int]] = {}
    rows = conn.execute(
        "SELECT json_extract(p.payload_json, '$.payload.family'), "
        "COUNT(*), "
        "SUM(CASE WHEN c.identity IS NOT NULL THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN g.identity IS NOT NULL THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN c.identity IS NULL AND g.identity IS NULL THEN 1 ELSE 0 END) "
        "FROM plan_entry p "
        "LEFT JOIN completion c ON c.provider=p.provider AND c.identity=p.identity "
        "LEFT JOIN terminal_gap g ON g.provider=p.provider AND g.identity=p.identity "
        "WHERE p.provider=? AND p.kind=? "
        "GROUP BY 1",
        (PROVIDER_BINANCE, KIND_BINANCE),
    ).fetchall()
    for family, planned, complete, gap, pending in rows:
        observed[str(family)] = (int(planned), int(complete or 0), int(gap or 0), int(pending or 0))
    expected = {item[0]: item[1:] for item in pins.expected_family_coverage}
    _require(observed == expected, "Binance family coverage changed", {"actual": observed})


def _bind_coinalyze(conn: sqlite3.Connection, pins: PlannerPins) -> None:
    kinds = dict(
        conn.execute(
            "SELECT kind, COUNT(*) FROM plan_entry WHERE provider=? GROUP BY kind",
            (PROVIDER_COINALYZE,),
        ).fetchall()
    )
    complete = dict(
        conn.execute(
            "SELECT p.kind, COUNT(*) FROM plan_entry p "
            "JOIN completion c ON c.provider=p.provider AND c.identity=p.identity "
            "WHERE p.provider=? GROUP BY p.kind",
            (PROVIDER_COINALYZE,),
        ).fetchall()
    )
    _require(
        int(kinds.get(KIND_COINALYZE_INVENTORY, 0)) == pins.expected_inventory_complete,
        "Coinalyze inventory count changed",
    )
    _require(
        int(complete.get(KIND_COINALYZE_INVENTORY, 0)) == pins.expected_inventory_complete,
        "Coinalyze inventory is not complete",
    )
    _require(
        int(kinds.get(KIND_COINALYZE_LIQUIDATION, 0)) == pins.expected_liquidation_complete,
        "Coinalyze liquidation count changed",
    )
    _require(
        int(complete.get(KIND_COINALYZE_LIQUIDATION, 0)) == pins.expected_liquidation_complete,
        "Coinalyze liquidation is not complete",
    )
    _require(
        int(kinds.get(KIND_COINALYZE_UNSUPPORTED, 0)) == pins.expected_gaps,
        "Coinalyze unsupported mapping count changed",
    )
    partition_rows = conn.execute(
        "SELECT p.identity, p.kind, c.identity, g.kind, g.fact_json "
        "FROM plan_entry p "
        "LEFT JOIN completion c ON c.provider=p.provider AND c.identity=p.identity "
        "LEFT JOIN terminal_gap g ON g.provider=p.provider AND g.identity=p.identity "
        "WHERE p.provider=? ORDER BY p.identity",
        (PROVIDER_COINALYZE,),
    ).fetchall()
    liquidation_identities: set[str] = set()
    unsupported_identities: set[str] = set()
    for identity, kind, completed_identity, gap_kind, gap_json in partition_rows:
        identity_text = str(identity)
        kind_text = str(kind)
        if kind_text in {KIND_COINALYZE_INVENTORY, KIND_COINALYZE_LIQUIDATION}:
            _require(
                str(completed_identity or "") == identity_text and gap_kind is None,
                "a supported Coinalyze identity is not exactly complete",
            )
            if kind_text == KIND_COINALYZE_LIQUIDATION:
                liquidation_identities.add(identity_text)
        elif kind_text == KIND_COINALYZE_UNSUPPORTED:
            _require(
                completed_identity is None and str(gap_kind or "") == GAP_UNSUPPORTED,
                "a Coinalyze unsupported identity lacks its typed gap",
            )
            try:
                gap_fact = json.loads(str(gap_json))
            except json.JSONDecodeError as exc:
                raise BlockedCandidateError("a Coinalyze gap fact is not JSON") from exc
            if type(gap_fact) is not dict:
                raise BlockedCandidateError("a Coinalyze gap fact is not an object")
            unsupported_identities.add(identity_text)
        else:
            raise BlockedCandidateError("an unknown Coinalyze plan kind is present")
    _require(
        len(unsupported_identities) == pins.expected_gaps,
        "Coinalyze unsupported-gap identity partition changed",
    )
    charge_rows = conn.execute(
        "SELECT seq, provider, identity, generation, content_sha256, charged_bytes, "
        "http_status, outcome, points, request_proof, retrieval_json, revision_json, created_at "
        "FROM coinalyze_charge ORDER BY provider, identity, generation"
    ).fetchall()
    _require(len(charge_rows) == pins.expected_charges, "checksum-verified charge count changed")
    charge_keys: set[tuple[str, str, int]] = set()
    charged_bytes = 0
    charged_points = 0
    for row in charge_rows:
        provider = str(row[1])
        identity = str(row[2])
        generation = _exact_int(row[3], label="Coinalyze charge generation", minimum=1)
        _require(provider == PROVIDER_COINALYZE, "a charge has the wrong provider")
        _require(identity in liquidation_identities, "a charge is not bound to a supported identity")
        _hex_digest(str(row[4]), label="Coinalyze charge content digest")
        byte_count = _exact_int(row[5], label="Coinalyze charged bytes", minimum=0)
        status = _exact_int(row[6], label="Coinalyze HTTP status", minimum=0)
        _require(status == 200, "a Coinalyze charge is not HTTP 200")
        _require(str(row[7]) == OUTCOME_CHECKSUM_VERIFIED, "a Coinalyze charge outcome changed")
        points = _exact_int(row[8], label="Coinalyze charge points", minimum=0)
        _hex_digest(str(row[9]), label="Coinalyze request proof")
        for label, value in (("retrieval", row[10]), ("revision", row[11])):
            try:
                document = json.loads(str(value))
            except json.JSONDecodeError as exc:
                raise BlockedCandidateError(f"Coinalyze charge {label} JSON is invalid") from exc
            if type(document) is not dict:
                raise BlockedCandidateError(f"Coinalyze charge {label} is not an object")
        _require(type(row[12]) is str and bool(row[12]), "a Coinalyze charge time is missing")
        key = (provider, identity, generation)
        _require(key not in charge_keys, "a Coinalyze charge identity is duplicated")
        charge_keys.add(key)
        charged_bytes += byte_count
        charged_points += points
    _require(
        {identity for _provider, identity, _generation in charge_keys} == liquidation_identities,
        "Coinalyze charges do not exactly partition supported identities",
    )
    transition_rows = conn.execute(
        "SELECT seq, provider, identity, generation, status, at "
        "FROM charge_transition ORDER BY provider, identity, generation, seq"
    ).fetchall()
    by_charge: dict[tuple[str, str, int], list[tuple[int, str, str]]] = {}
    for seq, provider, identity, generation, status, at in transition_rows:
        key = (str(provider), str(identity), _exact_int(generation, label="transition generation", minimum=1))
        by_charge.setdefault(key, []).append(
            (_exact_int(seq, label="transition sequence", minimum=1), str(status), str(at))
        )
    _require(set(by_charge) == charge_keys, "Coinalyze transition identities changed")
    for key, rows in by_charge.items():
        _require(
            [status for _seq, status, _at in rows]
            == [CHARGE_RESERVED, CHARGE_PUBLISHED, CHARGE_SETTLED],
            "a Coinalyze charge does not have one ordered reserved-published-settled chain",
            {"identity": key[1]},
        )
        _require(all(at for _seq, _status, at in rows), "a Coinalyze transition time is missing")
        _require(
            [seq for seq, _status, _at in rows] == sorted(seq for seq, _status, _at in rows),
            "a Coinalyze transition chain is not ordered",
        )
    _require(charged_bytes == pins.expected_charged_bytes, "charged byte total changed")
    _require(charged_points == pins.expected_charge_points, "charged point total changed")
    transitions = {status: 0 for status in (CHARGE_RESERVED, CHARGE_PUBLISHED, CHARGE_SETTLED)}
    for _seq, _provider, _identity, _generation, status, _at in transition_rows:
        transitions[str(status)] = transitions.get(str(status), 0) + 1
    _require(int(transitions.get(CHARGE_RESERVED, 0)) == pins.expected_reserved_transitions, "reserved transition count changed")
    _require(int(transitions.get(CHARGE_PUBLISHED, 0)) == pins.expected_published_transitions, "published transition count changed")
    _require(int(transitions.get(CHARGE_SETTLED, 0)) == pins.expected_settled_transitions, "settled transition count changed")
    ledger = conn.execute("SELECT charged FROM coinalyze_ledger WHERE id=1").fetchone()
    if ledger is None:
        raise BlockedCandidateError("Coinalyze ledger is missing")
    _require(int(ledger[0]) == pins.expected_charged_bytes, "Coinalyze ledger charged bytes changed")


_PENDING_SQL = """
SELECT p.provider, p.identity, p.kind, p.payload_json,
       a.id, a.class, a.status_code, a.ended_at, a.redacted_fact_json,
       s.sidecar_sha256, s.sidecar_path, s.sidecar_bytes, s.provider_checksum
FROM plan_entry p
LEFT JOIN completion c ON c.provider=p.provider AND c.identity=p.identity
LEFT JOIN terminal_gap g ON g.provider=p.provider AND g.identity=p.identity
LEFT JOIN attempt a ON a.provider=p.provider AND a.identity=p.identity
 AND a.id = (SELECT MAX(x.id) FROM attempt x
             WHERE x.provider=p.provider AND x.identity=p.identity)
LEFT JOIN sidecar_fact s ON s.provider=p.provider AND s.identity=p.identity
WHERE c.identity IS NULL AND g.identity IS NULL
ORDER BY p.provider, p.identity
"""


def _payload_envelope(payload_json: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        document = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise BlockedCandidateError("plan payload is not JSON") from exc
    if type(document) is not dict:
        raise BlockedCandidateError("plan payload is not an object")
    if set(document) != {"identity", "kind", "payload", "provider"}:
        raise BlockedCandidateError("plan payload envelope keys changed")
    inner = document.get("payload")
    if type(inner) is not dict:
        raise BlockedCandidateError("plan payload envelope is missing payload")
    common_fields = {
        "economic_interval",
        "family",
        "key",
        "listed_bytes",
        "retained",
        "sidecar_key",
        "sidecar_url",
        "symbol",
        "url",
    }
    family = inner.get("family")
    family_fields: set[str] = set()
    if family == FAMILY_METRICS:
        family_fields = {"consumable"}
    elif family == FAMILY_BOOK_TICKER:
        family_fields = {"etag"}
    if set(inner) != common_fields | family_fields:
        raise BlockedCandidateError("pending plan payload keys changed")
    if family == FAMILY_METRICS and type(inner.get("consumable")) is not bool:
        raise BlockedCandidateError("pending metrics consumable is not an exact bool")
    if family == FAMILY_BOOK_TICKER and type(inner.get("etag")) is not str:
        raise BlockedCandidateError("pending bookTicker etag is not exact text")
    return dict(document), dict(inner)


def _pending_key_identity(key: Any, family: Any) -> tuple[str, str]:
    if type(key) is not str or type(family) is not str:
        raise BlockedCandidateError("pending key and family must be exact text")
    pattern = PENDING_KEY_PATTERNS.get(family)
    if pattern is None:
        raise BlockedCandidateError(
            "an unexpected pending family is present",
            context={"family": family, "identity": key},
        )
    match = pattern.fullmatch(key)
    if match is None:
        raise BlockedCandidateError(
            "pending identity does not match its exact family/symbol/date grammar",
            context={"family": family, "identity": key},
        )
    interval = match.group("date")
    try:
        parsed_interval = datetime.strptime(interval, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise BlockedCandidateError("pending economic interval is not a calendar date") from exc
    _require(parsed_interval == interval, "pending economic interval is not canonical")
    return match.group("symbol"), interval


def _classify_pending_row(row: sqlite3.Row, *, attempt_hi: int) -> PendingIdentity:
    _require(type(row[0]) is str, "pending provider is not text")
    _require(type(row[1]) is str, "pending identity is not text")
    _require(type(row[2]) is str, "pending kind is not text")
    provider = row[0]
    identity = row[1]
    kind = row[2]
    _require(provider == PROVIDER_BINANCE, "a non-Binance identity is pending")
    _require(kind == KIND_BINANCE, "a non-object Binance identity is pending")
    envelope, payload = _payload_envelope(str(row[3]))
    _require(str(envelope.get("provider")) == provider, "plan envelope provider mismatch")
    _require(str(envelope.get("identity")) == identity, "plan envelope identity mismatch")
    _require(str(envelope.get("kind")) == kind, "plan envelope kind mismatch")
    _require(type(payload.get("key")) is str, "pending plan key is not text")
    key = payload["key"]
    _require(key == identity, "plan payload key does not equal the database identity")
    _require(type(payload.get("family")) is str, "pending plan family is not text")
    family = payload["family"]
    listed_bytes = _exact_int(payload.get("listed_bytes"), label="old listed bytes", minimum=1)
    expected_symbol, interval = _pending_key_identity(key, family)
    _require(type(payload.get("symbol")) is str, "pending plan symbol is not text")
    _require(payload["symbol"] == expected_symbol, "pending plan symbol is not canonical")
    _require(
        type(payload.get("economic_interval")) is str
        and payload["economic_interval"] == interval,
        "pending economic interval is not canonical",
    )
    _require(payload.get("retained") is False, "a pending identity is marked retained")
    _require(type(payload.get("sidecar_key")) is str, "sidecar key is not text")
    sidecar_key = payload["sidecar_key"]
    _require(sidecar_key == f"{key}.CHECKSUM", "sidecar key is not the official checksum object")
    _require(
        type(payload.get("url")) is str
        and payload["url"] == f"{VISION_OBJECT_BASE}/{key}",
        "plan URL is not the official object URL",
    )
    _require(
        type(payload.get("sidecar_url")) is str
        and payload["sidecar_url"] == f"{VISION_OBJECT_BASE}/{key}.CHECKSUM",
        "plan sidecar URL is not the official checksum URL",
    )
    attempt_id = row[4]
    attempt_class = str(row[5] or "")
    status_code = row[6]
    ended_at = row[7]
    if attempt_id is None or ended_at is None:
        raise BlockedCandidateError("a pending identity has no sealed terminal attempt")
    attempt_id = int(attempt_id)
    _require(attempt_id <= attempt_hi, "a pending attempt is outside the sealed watermark")
    _require(attempt_class == RETRY_TERMINAL, "a pending identity has no terminal attempt")
    _require(int(status_code) == 200, "a pending terminal attempt is not HTTP 200")
    try:
        fact = json.loads(str(row[8]))
    except json.JSONDecodeError as exc:
        raise BlockedCandidateError("attempt fact is not JSON") from exc
    if type(fact) is not dict or frozenset(fact) != ATTEMPT_FACT_KEYS:
        raise BlockedCandidateError("attempt fact keys changed")
    _require(str(fact.get("kind")) == "validation", "attempt fact kind is not validation")
    _require(int(fact.get("status")) == 200, "attempt fact status is not 200")
    _require(
        str(fact.get("url")) == f"{VISION_OBJECT_BASE}/{key}",
        "attempt URL is not the official object URL",
    )
    message = str(fact.get("error") or "")
    if family == FAMILY_METRICS:
        _require(message in METRICS_REVISION_MESSAGES, "a metrics pending identity has an unexpected terminal message")
    else:
        _require(message == MSG_ZIP, "a book-ticker pending identity has an unexpected terminal message")
    sidecar_sha = row[9]
    sidecar_path = row[10]
    sidecar_bytes = row[11]
    provider_checksum = row[12]
    if sidecar_sha is None or sidecar_path is None or sidecar_bytes is None or provider_checksum is None:
        raise BlockedCandidateError("a pending identity has no retained sidecar")
    return PendingIdentity(
        provider=provider,
        identity=key,
        family=family,
        symbol=expected_symbol,
        listed_bytes=listed_bytes,
        sidecar_key=sidecar_key,
        payload=payload,
        envelope=envelope,
        attempt_id=attempt_id,
        attempt_class=attempt_class,
        status_code=200,
        ended_at=str(ended_at),
        fact=fact,
        terminal_message=message,
        sidecar_sha256=_hex_digest(str(sidecar_sha), label="sidecar digest"),
        sidecar_path=str(sidecar_path),
        sidecar_bytes=_exact_int(sidecar_bytes, label="sidecar bytes", minimum=1),
        provider_checksum=_hex_digest(str(provider_checksum), label="provider checksum"),
        sidecar_body=b"",
    )


def iter_pending(
    conn: sqlite3.Connection,
    pins: PlannerPins,
    hooks: PlannerHooks,
    *,
    attempt_hi: int,
) -> Iterator[PendingIdentity]:
    yielded = 0
    cursor = conn.execute(_PENDING_SQL)
    try:
        while True:
            batch = cursor.fetchmany(CURSOR_BATCH)
            if not batch:
                break
            if hooks.on_live_row_count is not None:
                hooks.on_live_row_count(len(batch))
            for row in batch:
                yielded += 1
                yield _classify_pending_row(row, attempt_hi=attempt_hi)
    finally:
        cursor.close()
    expected = pins.expected_pending_metrics + pins.expected_pending_book_ticker
    _require(yielded == expected, "pending stream count changed", {"actual": yielded})


def _count_and_prove_pending(
    conn: sqlite3.Connection,
    pins: PlannerPins,
    hooks: PlannerHooks,
    *,
    attempt_hi: int,
) -> dict[str, Any]:
    metrics = 0
    book = 0
    messages: dict[str, int] = {}
    metrics_bytes = 0
    book_bytes = 0
    pending_digest = hashlib.sha256()
    for item in iter_pending(conn, pins, hooks, attempt_hi=attempt_hi):
        pending_digest.update(compact_json({"identity": item.identity, "family": item.family}))
        if item.family == FAMILY_METRICS:
            metrics += 1
            metrics_bytes += item.listed_bytes
        else:
            book += 1
            book_bytes += item.listed_bytes
        messages[item.terminal_message] = messages.get(item.terminal_message, 0) + 1
    _require(metrics == pins.expected_pending_metrics, "pending metrics count changed")
    _require(book == pins.expected_pending_book_ticker, "pending book-ticker count changed")
    expected_messages = dict(pins.expected_message_counts)
    _require(messages == expected_messages, "pending message split changed", {"actual": messages})
    _require(metrics_bytes == pins.expected_pending_metrics_bytes, "pending metrics bytes changed")
    _require(book_bytes == pins.expected_pending_book_bytes, "pending book-ticker bytes changed")
    return {
        "book_ticker_zip_work": book,
        "identity_sha256": pending_digest.hexdigest(),
        "messages": dict(sorted(messages.items())),
        "metrics_revision": metrics,
        "total": metrics + book,
    }


def _rehash_sidecar(
    item: PendingIdentity,
    content_fd: int,
    *,
    pinned_destination: str,
) -> PendingIdentity:
    shard, name = content_path_parts(item.sidecar_sha256)
    expected_path = (
        f"{pinned_destination}/{FIXED_ACTIVE_NAME}/{CONTENT_NAME}/{shard}/{name}"
    )
    _require(
        item.sidecar_path == expected_path,
        "a retained sidecar path is not the canonical content-addressed leaf",
    )
    shard_fd = open_child_dir(content_fd, shard, create=False)
    try:
        fd = open_child_file(shard_fd, name)
        try:
            digest, size = hash_fd(fd)
            _require(digest == item.sidecar_sha256, "a retained sidecar digest changed")
            _require(size == item.sidecar_bytes, "a retained sidecar size changed")
            body = _read_fd_bounded(
                fd, ceiling=SIDECAR_CEILING_BYTES, label="retained sidecar"
            )
        finally:
            os.close(fd)
    finally:
        os.close(shard_fd)
    basename = item.identity.rsplit("/", 1)[-1]
    checksum = parse_sidecar(body, basename=basename)
    _require(checksum == item.provider_checksum, "a parsed sidecar checksum does not match the recorded provider checksum")
    return replace(item, sidecar_body=body)


def _empty_pass(pass_id: str) -> dict[str, Any]:
    roots = [
        listing_request_key(
            listing_request_identity(
                endpoint=VISION_S3_ENDPOINT,
                prefix=prefix,
                delimiter=LIST_DELIMITER,
                continuation_token=None,
            )
        )
        for prefix in FAMILY_PREFIXES
    ]
    return {
        "completed_prefixes": [],
        "cursor": {
            "continuation_token": None,
            "prefix": sorted(FAMILY_PREFIXES)[0],
        },
        "discovered_prefixes": sorted(FAMILY_PREFIXES),
        "graph": [],
        "listing_complete": False,
        "pages": {},
        "pass_id": pass_id,
        "published_pages": 0,
        "roots": roots,
        "seen_tokens": {},
    }


def _empty_checkpoint(
    generation: Mapping[str, Any],
    pending: Mapping[str, Any],
    code: Mapping[str, str],
) -> dict[str, Any]:
    state = (generation.get("physical") or {}).get("state") or {}
    return {
        "code_identity": dict(code),
        "family_prefixes": list(FAMILY_PREFIXES),
        "generation": {
            "plan_identity": generation["plan_identity"],
            "state_sha256": state.get("sha256"),
        },
        "passes": {pass_id: _empty_pass(pass_id) for pass_id in PASS_IDS},
        "pending_identity_sha256": pending["identity_sha256"],
        "s3_endpoint": VISION_S3_ENDPOINT,
        "schema_version": CHECKPOINT_SCHEMA,
    }


def _write_replace_json(
    dir_fd: int,
    name: str,
    document: Mapping[str, Any],
    *,
    ceiling: int,
    label: str,
) -> None:
    body = canonical_json(document)
    _require(len(body) <= ceiling, f"{label} exceeds the accepted byte ceiling")
    tmp_name = f".partial-{name}.{os.urandom(8).hex()}.tmp"
    fd = os.open(
        tmp_name,
        os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=dir_fd,
    )
    try:
        written = 0
        view = memoryview(body)
        while written < len(body):
            written += os.write(fd, view[written:])
        os.fsync(fd)
    except Exception:
        os.close(fd)
        try:
            os.unlink(tmp_name, dir_fd=dir_fd)
        except FileNotFoundError:
            pass
        raise
    os.close(fd)
    os.replace(tmp_name, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
    os.fsync(dir_fd)


def _publish_named(
    dest_fd: int,
    tmp_fd: int,
    payload: bytes,
    *,
    suffix: str,
) -> dict[str, Any]:
    digest = sha256_bytes(payload)
    name = f"{digest}{suffix}"
    existing = _open_optional_regular(dest_fd, name)
    if existing is not None:
        try:
            actual, size = hash_fd(existing)
        finally:
            os.close(existing)
        _require(actual == digest, "a published candidate object was replaced")
        return {"bytes": size, "name": name, "reused": True, "sha256": digest}
    tmp_name = f".partial-{digest}.{os.urandom(8).hex()}.tmp"
    fd = os.open(
        tmp_name,
        os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=tmp_fd,
    )
    try:
        written = 0
        view = memoryview(payload)
        while written < len(payload):
            written += os.write(fd, view[written:])
        os.fsync(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        actual, size = hash_fd(fd)
        _require(actual == digest and size == len(payload), "candidate object does not rehash")
    except Exception:
        os.close(fd)
        try:
            os.unlink(tmp_name, dir_fd=tmp_fd)
        except FileNotFoundError:
            pass
        raise
    os.close(fd)
    try:
        _renameat2_noreplace(tmp_fd, tmp_name, dest_fd, name)
    except OSError as exc:
        try:
            os.unlink(tmp_name, dir_fd=tmp_fd)
        except FileNotFoundError:
            pass
        if exc.errno == errno.EEXIST:
            winner = open_child_file(dest_fd, name)
            try:
                actual, size = hash_fd(winner)
            finally:
                os.close(winner)
            _require(actual == digest, "collision winner does not match the intended digest")
            return {"bytes": size, "name": name, "reused": True, "sha256": digest}
        raise UnsafeCandidateError("no-replace candidate publication failed") from exc
    os.fsync(dest_fd)
    return {"bytes": len(payload), "name": name, "reused": False, "sha256": digest}


def _publish_fd_named(
    dest_fd: int,
    tmp_fd: int,
    source_fd: int,
    *,
    digest: str,
    size: int,
    suffix: str,
) -> dict[str, Any]:
    digest = _hex_digest(digest, label="streamed publication digest")
    size = _exact_int(size, label="streamed publication bytes", minimum=0)
    name = f"{digest}{suffix}"
    existing = _open_optional_regular(dest_fd, name)
    if existing is not None:
        try:
            actual, actual_size = hash_fd(existing)
        finally:
            os.close(existing)
        _require(
            actual == digest and actual_size == size,
            "a published candidate object was replaced",
        )
        return {"bytes": size, "name": name, "reused": True, "sha256": digest}
    tmp_name = f".partial-{digest}.{os.urandom(8).hex()}.tmp"
    output = os.open(
        tmp_name,
        os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=tmp_fd,
    )
    copied = 0
    try:
        os.lseek(source_fd, 0, os.SEEK_SET)
        while True:
            chunk = os.read(source_fd, CHUNK_SIZE)
            if not chunk:
                break
            offset = 0
            while offset < len(chunk):
                offset += os.write(output, chunk[offset:])
            copied += len(chunk)
            if copied > size:
                raise BlockedCandidateError("streamed publication exceeded its authenticated size")
        _require(copied == size, "streamed publication was short")
        os.fsync(output)
        actual, actual_size = hash_fd(output)
        _require(
            actual == digest and actual_size == size,
            "streamed publication does not match its authenticated source",
        )
    except Exception:
        os.close(output)
        try:
            os.unlink(tmp_name, dir_fd=tmp_fd)
        except FileNotFoundError:
            pass
        raise
    os.close(output)
    try:
        _renameat2_noreplace(tmp_fd, tmp_name, dest_fd, name)
    except OSError as exc:
        try:
            os.unlink(tmp_name, dir_fd=tmp_fd)
        except FileNotFoundError:
            pass
        if exc.errno != errno.EEXIST:
            raise UnsafeCandidateError("no-replace streamed publication failed") from exc
        winner = open_child_file(dest_fd, name)
        try:
            actual, actual_size = hash_fd(winner)
        finally:
            os.close(winner)
        _require(
            actual == digest and actual_size == size,
            "streamed publication collision winner changed",
        )
        return {"bytes": size, "name": name, "reused": True, "sha256": digest}
    os.fsync(dest_fd)
    return {"bytes": size, "name": name, "reused": False, "sha256": digest}


def _publish_page_bytes(pages_fd: int, tmp_fd: int, payload: bytes) -> str:
    digest = sha256_bytes(payload)
    shard, name = content_path_parts(digest)
    shard_fd = open_child_dir(pages_fd, shard, create=True)
    try:
        published = _publish_named(shard_fd, tmp_fd, payload, suffix="")
        _require(published["sha256"] == digest, "published page digest changed")
        _require(published["name"] == name, "published page name changed")
        return digest
    finally:
        os.close(shard_fd)


def _prefix_allowed(prefix: str) -> bool:
    return any(prefix == family or prefix.startswith(family) for family in FAMILY_PREFIXES)


def _open_listing_index(tmp_fd: int, held: HeldFds) -> sqlite3.Connection:
    try:
        os.unlink(LISTING_INDEX_NAME, dir_fd=tmp_fd)
    except FileNotFoundError:
        pass
    fd = held.add(
        os.open(
            LISTING_INDEX_NAME,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=tmp_fd,
        )
    )
    uri = f"file:/proc/self/fd/{fd}?mode=rw"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute(
        "CREATE TABLE listing_object ("
        "pass_id TEXT NOT NULL, key TEXT NOT NULL, size INTEGER NOT NULL, etag TEXT, "
        "page_sha256 TEXT NOT NULL, request_key TEXT NOT NULL, prefix TEXT NOT NULL, "
        "PRIMARY KEY(pass_id, key))"
    )
    return conn


def _load_checkpoint(candidate_fd: int, pages_fd: int) -> dict[str, Any] | None:
    _ = pages_fd
    try:
        os.stat(CHECKPOINT_NAME, dir_fd=candidate_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise UnsafeCandidateError("checkpoint name cannot be inspected safely") from exc
    payload = _read_bound_named_regular(
        candidate_fd,
        CHECKPOINT_NAME,
        ceiling=CHECKPOINT_CEILING_BYTES,
        label="checkpoint",
    )
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BlockedCandidateError("checkpoint is not JSON") from exc
    if type(document) is not dict:
        raise BlockedCandidateError("checkpoint is not an object")
    return document


def _exact_keys(document: Mapping[str, Any], expected: set[str], *, label: str) -> None:
    if type(document) is not dict or set(document) != expected:
        raise BlockedCandidateError(f"{label} schema changed")


def _validate_retrieved_at(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise BlockedCandidateError("listing retrieval clock is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BlockedCandidateError("listing retrieval clock is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise BlockedCandidateError("listing retrieval clock is not UTC")
    return value


def _read_page_payload(pages_fd: int, digest: str) -> bytes:
    shard, name = content_path_parts(digest)
    shard_fd = open_child_dir(pages_fd, shard, create=False)
    try:
        with _bound_named_regular(
            shard_fd, name, label="retained listing page"
        ) as fd:
            payload = _read_fd_bounded(
                fd, ceiling=LIST_PAGE_CEILING_BYTES, label="retained listing page"
            )
            actual, size = hash_fd(fd)
    finally:
        os.close(shard_fd)
    _require(actual == digest, "a retained listing page was tampered")
    _require(size == len(payload), "a retained listing page size changed")
    return payload


def _validate_page_record(
    record: Mapping[str, Any],
    *,
    pass_id: str,
    request_key: str,
    pages_fd: int,
) -> tuple[list[str], list[ListingObject], bool, str | None]:
    _exact_keys(
        record,
        {
            "byte_size",
            "child_prefixes",
            "final_url",
            "headers",
            "is_truncated",
            "next_continuation_token",
            "pass_id",
            "request",
            "request_key",
            "response_sha256",
            "retrieved_at",
            "status_code",
        },
        label="checkpoint page record",
    )
    _require(record["pass_id"] == pass_id, "checkpoint page belongs to another pass")
    _require(record["request_key"] == request_key, "checkpoint page request key changed")
    request = record["request"]
    _exact_keys(
        request,
        {"continuation_token", "delimiter", "endpoint", "list_type", "prefix"},
        label="checkpoint request",
    )
    token = request["continuation_token"]
    if token is not None and type(token) is not str:
        raise BlockedCandidateError("checkpoint continuation token has the wrong type")
    for field in ("delimiter", "endpoint", "list_type", "prefix"):
        if type(request[field]) is not str:
            raise BlockedCandidateError("checkpoint request field has the wrong type")
    if token is not None and len(token) > TOKEN_LENGTH_CEILING:
        raise BlockedCandidateError("checkpoint continuation token exceeds the ceiling")
    identity = listing_request_identity(
        endpoint=request["endpoint"],
        prefix=request["prefix"],
        delimiter=request["delimiter"],
        continuation_token=token,
    )
    _require(identity == request, "checkpoint request identity is noncanonical")
    _require(identity["endpoint"] == VISION_S3_ENDPOINT, "checkpoint endpoint changed")
    _require(identity["delimiter"] == LIST_DELIMITER, "checkpoint delimiter changed")
    _require(_prefix_allowed(identity["prefix"]), "checkpoint prefix is outside scope")
    _require(listing_request_key(identity) == request_key, "checkpoint request key changed")
    _require(record["final_url"] == listing_url(identity), "checkpoint final URL changed")
    _require(
        _exact_int(record["status_code"], label="checkpoint status") == 200,
        "checkpoint status is not 200",
    )
    _require(
        _canonical_headers(record["headers"]) == record["headers"],
        "checkpoint response headers are noncanonical",
    )
    _validate_retrieved_at(record["retrieved_at"])
    digest = _hex_digest(record["response_sha256"], label="page digest")
    payload = _read_page_payload(pages_fd, digest)
    _require(
        _exact_int(record["byte_size"], label="page byte size", minimum=0)
        == len(payload),
        "a retained listing page size changed",
    )
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BlockedCandidateError("listing page is not UTF-8") from exc
    prefixes, objects, truncated, next_token = parse_s3_list_bucket(text, request=identity)
    _require(record["child_prefixes"] == prefixes, "checkpoint child-prefix facts changed")
    _require(record["is_truncated"] is truncated, "checkpoint truncation fact changed")
    _require(
        record["next_continuation_token"] == next_token,
        "checkpoint continuation edge changed",
    )
    return prefixes, objects, truncated, next_token


def _reconstruct_pass(
    state: Mapping[str, Any],
    *,
    pass_id: str,
    pages_fd: int,
) -> dict[str, Any]:
    _exact_keys(
        state,
        {
            "completed_prefixes",
            "cursor",
            "discovered_prefixes",
            "graph",
            "listing_complete",
            "pages",
            "pass_id",
            "published_pages",
            "roots",
            "seen_tokens",
        },
        label="checkpoint pass",
    )
    _require(state["pass_id"] == pass_id, "checkpoint pass identity changed")
    pages = state["pages"]
    graph = state["graph"]
    if type(pages) is not dict or type(graph) is not list:
        raise BlockedCandidateError("checkpoint pass graph has the wrong type")
    for field in ("completed_prefixes", "discovered_prefixes", "roots"):
        values = state[field]
        if type(values) is not list or any(type(value) is not str for value in values):
            raise BlockedCandidateError(f"checkpoint {field} has the wrong type")
    if type(state["listing_complete"]) is not bool:
        raise BlockedCandidateError("checkpoint completion flag has the wrong type")
    _exact_int(state["published_pages"], label="checkpoint published pages", minimum=0)
    cursor_value = state["cursor"]
    if cursor_value is not None:
        _exact_keys(
            cursor_value,
            {"continuation_token", "prefix"},
            label="checkpoint cursor",
        )
        if type(cursor_value["prefix"]) is not str or (
            cursor_value["continuation_token"] is not None
            and type(cursor_value["continuation_token"]) is not str
        ):
            raise BlockedCandidateError("checkpoint cursor has the wrong type")
    token_state = state["seen_tokens"]
    if type(token_state) is not dict:
        raise BlockedCandidateError("checkpoint token ledger has the wrong type")
    for token_prefix, tokens in token_state.items():
        if type(token_prefix) is not str or type(tokens) is not list or any(
            type(token) is not str for token in tokens
        ):
            raise BlockedCandidateError("checkpoint token ledger has the wrong type")
    if any(type(key) is not str or type(value) is not dict for key, value in pages.items()):
        raise BlockedCandidateError("checkpoint page map has the wrong type")
    if any(type(key) is not str for key in graph) or len(set(graph)) != len(graph):
        raise BlockedCandidateError("checkpoint graph is duplicated or mistyped")
    if set(pages) != set(graph):
        raise BlockedCandidateError("checkpoint contains orphan or missing pages")
    if len(pages) > PAGE_COUNT_CEILING:
        raise BlockedCandidateError("checkpoint exceeds the page ceiling")
    expected_roots = _empty_pass(pass_id)["roots"]
    _require(state["roots"] == expected_roots, "checkpoint roots changed")
    discovered = set(FAMILY_PREFIXES)
    completed: set[str] = set()
    expected_graph: list[str] = []
    expected_tokens: dict[str, list[str]] = {}
    parsed: dict[str, tuple[list[str], list[ListingObject], bool, str | None]] = {}
    cursor: dict[str, Any] | None = None
    while True:
        remaining = sorted(discovered - completed)
        if not remaining:
            break
        prefix = remaining[0]
        token: str | None = None
        per_prefix: set[str] = set()
        while True:
            identity = listing_request_identity(
                endpoint=VISION_S3_ENDPOINT,
                prefix=prefix,
                delimiter=LIST_DELIMITER,
                continuation_token=token,
            )
            key = listing_request_key(identity)
            if key not in pages:
                cursor = {"continuation_token": token, "prefix": prefix}
                break
            prefixes, objects, truncated, next_token = _validate_page_record(
                pages[key], pass_id=pass_id, request_key=key, pages_fd=pages_fd
            )
            parsed[key] = (prefixes, objects, truncated, next_token)
            expected_graph.append(key)
            for child in prefixes:
                if child not in discovered and len(discovered) >= PREFIX_CEILING:
                    raise BlockedCandidateError("checkpoint prefix count exceeds the ceiling")
                discovered.add(child)
            if not truncated:
                completed.add(prefix)
                break
            assert next_token is not None
            if next_token in per_prefix:
                raise BlockedCandidateError("checkpoint continuation token cycle")
            per_prefix.add(next_token)
            expected_tokens.setdefault(prefix, []).append(next_token)
            token = next_token
        if cursor is not None:
            break
    _require(graph == expected_graph, "checkpoint graph is reordered or unreachable")
    _require(
        state["published_pages"] == len(expected_graph),
        "checkpoint published-page count changed",
    )
    _require(
        state["discovered_prefixes"] == sorted(discovered),
        "checkpoint discovered-prefix state is forged",
    )
    _require(
        state["completed_prefixes"] == sorted(completed),
        "checkpoint completed-prefix state is forged",
    )
    _require(state["seen_tokens"] == expected_tokens, "checkpoint token ledger is forged")
    complete = cursor is None
    _require(state["listing_complete"] is complete, "checkpoint completion state is forged")
    _require(state["cursor"] == cursor, "checkpoint cursor state is forged")
    return {
        "completed": completed,
        "cursor": cursor,
        "discovered": discovered,
        "parsed": parsed,
        "seen_tokens": expected_tokens,
    }


def _authenticate_checkpoint(
    checkpoint: Mapping[str, Any],
    *,
    generation: Mapping[str, Any],
    pending: Mapping[str, Any],
    code: Mapping[str, str],
    pages_fd: int,
) -> None:
    _exact_keys(
        checkpoint,
        {
            "code_identity",
            "family_prefixes",
            "generation",
            "passes",
            "pending_identity_sha256",
            "s3_endpoint",
            "schema_version",
        },
        label="checkpoint",
    )
    _require(checkpoint["schema_version"] == CHECKPOINT_SCHEMA, "checkpoint schema version changed")
    _require(checkpoint["s3_endpoint"] == VISION_S3_ENDPOINT, "checkpoint endpoint changed")
    _require(checkpoint["family_prefixes"] == list(FAMILY_PREFIXES), "checkpoint family prefixes changed")
    generation_binding = checkpoint["generation"]
    _exact_keys(generation_binding, {"plan_identity", "state_sha256"}, label="checkpoint generation")
    state = (generation.get("physical") or {}).get("state") or {}
    _require(generation_binding["plan_identity"] == generation["plan_identity"], "checkpoint plan identity changed")
    _require(generation_binding["state_sha256"] == state.get("sha256"), "checkpoint state identity changed")
    _require(
        checkpoint.get("pending_identity_sha256") == pending["identity_sha256"],
        "checkpoint pending identity changed",
    )
    _require(checkpoint["code_identity"] == dict(code), "checkpoint code identity changed")
    passes = checkpoint["passes"]
    _exact_keys(passes, set(PASS_IDS), label="checkpoint pass map")
    for pass_id in PASS_IDS:
        _reconstruct_pass(passes[pass_id], pass_id=pass_id, pages_fd=pages_fd)


def _fetch_page(
    identity: Mapping[str, Any],
    *,
    pass_id: str,
    transport: ListingTransport,
    hooks: PlannerHooks,
    pages_fd: int,
    tmp_fd: int,
    known_prefixes: set[str],
) -> tuple[list[str], list[ListingObject], bool, str | None, dict[str, Any]]:
    key = listing_request_key(identity)
    if hooks.before_network is not None:
        hooks.before_network()
    url = listing_url(identity)
    if hooks.on_network is not None:
        hooks.on_network(url)
    try:
        response = transport.fetch(url, max_bytes=LIST_PAGE_CEILING_BYTES)
    except ListingInterrupted:
        raise
    except BlockedCandidateError:
        raise
    except (TimeoutError, ConnectionError, InterruptedError, BrokenPipeError) as exc:
        raise ListingInterrupted("listing transport was interrupted") from exc
    except urllib.error.URLError as exc:
        raise ListingInterrupted("listing request failed transiently") from exc
    if isinstance(response.status_code, bool) or type(response.status_code) is not int:
        raise BlockedCandidateError("listing status is not an exact integer")
    if response.status_code != 200:
        raise BlockedCandidateError("listing status is not 200")
    if type(response.body) is not bytes:
        raise BlockedCandidateError("listing response body is not bytes")
    if len(response.body) > LIST_PAGE_CEILING_BYTES:
        raise BlockedCandidateError("listing page exceeded the accepted byte ceiling")
    if type(response.url) is not str or response.url != url:
        raise BlockedCandidateError("listing final URL diverged from the request")
    headers = _canonical_headers(response.headers)
    content_length = headers.get("content-length")
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError as exc:
            raise BlockedCandidateError("listing Content-Length is not an integer") from exc
        _require(declared == len(response.body), "listing Content-Length does not match the body")
    try:
        xml_text = response.body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BlockedCandidateError("listing page is not UTF-8") from exc
    prefixes, objects, truncated, token = parse_s3_list_bucket(xml_text, request=identity)
    newly_discovered = {prefix for prefix in prefixes if prefix not in known_prefixes}
    if len(known_prefixes) + len(newly_discovered) > PREFIX_CEILING:
        raise BlockedCandidateError("live listing prefix count exceeds the ceiling")
    retrieved_at = _utc_retrieval_clock(hooks)
    digest = _publish_page_bytes(pages_fd, tmp_fd, response.body)
    record = {
        "byte_size": len(response.body),
        "child_prefixes": list(prefixes),
        "final_url": response.url,
        "headers": headers,
        "is_truncated": truncated,
        "next_continuation_token": token,
        "pass_id": pass_id,
        "request": dict(identity),
        "request_key": key,
        "response_sha256": digest,
        "retrieved_at": retrieved_at,
        "status_code": response.status_code,
    }
    return prefixes, objects, truncated, token, record


def _insert_objects(
    index: sqlite3.Connection,
    objects: Sequence[ListingObject],
    *,
    pass_id: str,
    page_sha256: str,
    request_key: str,
    prefix: str,
    hooks: PlannerHooks,
) -> None:
    if hooks.on_listing_live_count is not None:
        hooks.on_listing_live_count(len(objects))
    for obj in objects:
        try:
            index.execute(
                "INSERT INTO listing_object(pass_id, key, size, etag, page_sha256, request_key, prefix) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pass_id, obj.key, obj.size, obj.etag, page_sha256, request_key, prefix),
            )
        except sqlite3.IntegrityError as exc:
            raise BlockedCandidateError(
                "listing contains a duplicate key", context={"key": obj.key}
            ) from exc
    index.commit()


def _rebuild_index_from_graph(
    state: Mapping[str, Any],
    *,
    pass_id: str,
    pages_fd: int,
    index: sqlite3.Connection,
    hooks: PlannerHooks,
) -> None:
    pages = state["pages"]
    for key in state["graph"]:
        record = pages[str(key)]
        request = record["request"]
        digest = str(record["response_sha256"])
        shard, name = content_path_parts(digest)
        shard_fd = open_child_dir(pages_fd, shard, create=False)
        try:
            with _bound_named_regular(
                shard_fd, name, label="retained listing page"
            ) as fd:
                payload = _read_fd_bounded(
                    fd, ceiling=LIST_PAGE_CEILING_BYTES, label="retained listing page"
                )
        finally:
            os.close(shard_fd)
        prefixes, objects, _truncated, _token = parse_s3_list_bucket(
            payload.decode("utf-8"), request=request
        )
        _ = prefixes
        _insert_objects(
            index,
            objects,
            pass_id=pass_id,
            page_sha256=digest,
            request_key=str(key),
            prefix=str(request["prefix"]),
            hooks=hooks,
        )


def _complete_pass(
    *,
    pass_id: str,
    candidate_fd: int,
    pages_fd: int,
    tmp_fd: int,
    transport: ListingTransport,
    hooks: PlannerHooks,
    checkpoint: dict[str, Any],
    index: sqlite3.Connection,
) -> None:
    state = checkpoint["passes"][pass_id]
    rebuilt = _reconstruct_pass(state, pass_id=pass_id, pages_fd=pages_fd)
    _rebuild_index_from_graph(
        state, pass_id=pass_id, pages_fd=pages_fd, index=index, hooks=hooks
    )
    discovered = set(rebuilt["discovered"])
    completed = set(rebuilt["completed"])
    seen_tokens = {
        prefix: list(tokens) for prefix, tokens in rebuilt["seen_tokens"].items()
    }
    if state["listing_complete"]:
        return
    while True:
        remaining = sorted(discovered - completed)
        if not remaining:
            break
        prefix = remaining[0]
        _require(_prefix_allowed(prefix), "listing prefix is outside the affected families")
        if len(discovered) > PREFIX_CEILING:
            raise BlockedCandidateError("listing prefix count exceeds the accepted ceiling")
        cursor = state.get("cursor")
        token: str | None
        if type(cursor) is dict and cursor.get("prefix") == prefix:
            token = cursor.get("continuation_token")
        else:
            token = None
        while True:
            if len(state["pages"]) >= PAGE_COUNT_CEILING:
                raise BlockedCandidateError("live listing page count exceeds the ceiling")
            identity = listing_request_identity(
                endpoint=VISION_S3_ENDPOINT,
                prefix=prefix,
                delimiter=LIST_DELIMITER,
                continuation_token=token,
            )
            prefixes, objects, truncated, next_token, record = _fetch_page(
                identity,
                pass_id=pass_id,
                transport=transport,
                hooks=hooks,
                pages_fd=pages_fd,
                tmp_fd=tmp_fd,
                known_prefixes=discovered,
            )
            request_key = listing_request_key(identity)
            _require(request_key not in state["pages"], "listing request was fetched twice in one pass")
            _insert_objects(
                index,
                objects,
                pass_id=pass_id,
                page_sha256=str(record["response_sha256"]),
                request_key=request_key,
                prefix=prefix,
                hooks=hooks,
            )
            for child in prefixes:
                _require(_prefix_allowed(child), "listing expanded past the affected family prefixes")
                if child not in discovered and len(discovered) >= PREFIX_CEILING:
                    raise BlockedCandidateError("live listing prefix count exceeds the ceiling")
                discovered.add(child)
            state["pages"][request_key] = record
            state["graph"].append(request_key)
            state["published_pages"] = len(state["graph"])
            state["discovered_prefixes"] = sorted(discovered)
            if not truncated:
                completed.add(prefix)
                state["completed_prefixes"] = sorted(completed)
                next_remaining = sorted(discovered - completed)
                state["listing_complete"] = not next_remaining
                state["cursor"] = (
                    None
                    if not next_remaining
                    else {"continuation_token": None, "prefix": next_remaining[0]}
                )
                state["seen_tokens"] = seen_tokens
                _write_replace_json(
                    candidate_fd,
                    CHECKPOINT_NAME,
                    checkpoint,
                    ceiling=CHECKPOINT_CEILING_BYTES,
                    label="checkpoint",
                )
                if hooks.after_page_publish is not None:
                    hooks.after_page_publish(record)
                if hooks.interrupt_after_pages is not None and sum(
                    int(checkpoint["passes"][item]["published_pages"]) for item in PASS_IDS
                ) >= int(hooks.interrupt_after_pages):
                    raise ListingInterrupted("listing interrupted after a durable page")
                break
            if not next_token:
                raise BlockedCandidateError("S3 listing truncated without V2 continuation token")
            prefix_tokens = seen_tokens.setdefault(prefix, [])
            if next_token in prefix_tokens:
                raise BlockedCandidateError("listing continuation token cycle")
            prefix_tokens.append(next_token)
            token = next_token
            state["cursor"] = {"continuation_token": token, "prefix": prefix}
            state["seen_tokens"] = seen_tokens
            _write_replace_json(
                candidate_fd,
                CHECKPOINT_NAME,
                checkpoint,
                ceiling=CHECKPOINT_CEILING_BYTES,
                label="checkpoint",
            )
            if hooks.after_page_publish is not None:
                hooks.after_page_publish(record)
            if hooks.interrupt_after_pages is not None and sum(
                int(checkpoint["passes"][item]["published_pages"]) for item in PASS_IDS
            ) >= int(hooks.interrupt_after_pages):
                raise ListingInterrupted("listing interrupted after a durable page")
    state["listing_complete"] = True
    state["cursor"] = None
    _write_replace_json(
        candidate_fd,
        CHECKPOINT_NAME,
        checkpoint,
        ceiling=CHECKPOINT_CEILING_BYTES,
        label="checkpoint",
    )


def _complete_listings(
    *,
    candidate_fd: int,
    pages_fd: int,
    tmp_fd: int,
    transport: ListingTransport,
    hooks: PlannerHooks,
    checkpoint: dict[str, Any],
    index: sqlite3.Connection,
) -> None:
    for pass_id in PASS_IDS:
        _complete_pass(
            pass_id=pass_id,
            candidate_fd=candidate_fd,
            pages_fd=pages_fd,
            tmp_fd=tmp_fd,
            transport=transport,
            hooks=hooks,
            checkpoint=checkpoint,
            index=index,
        )
    _authenticate_checkpoint(
        checkpoint,
        generation={
            "plan_identity": checkpoint["generation"]["plan_identity"],
            "physical": {"state": {"sha256": checkpoint["generation"]["state_sha256"]}},
        },
        pending={"identity_sha256": checkpoint["pending_identity_sha256"]},
        code=checkpoint["code_identity"],
        pages_fd=pages_fd,
    )


def _lookup_listing(
    index: sqlite3.Connection,
    pass_id: str,
    key: str,
) -> tuple[int, str | None, str, str] | None:
    row = index.execute(
        "SELECT size, etag, page_sha256, request_key FROM listing_object "
        "WHERE pass_id=? AND key=?",
        (pass_id, key),
    ).fetchone()
    if row is None:
        return None
    return int(row[0]), None if row[1] is None else str(row[1]), str(row[2]), str(row[3])


def _stable_pass_graph(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    pages = state["pages"]
    ordinals: dict[str, int] = {}
    normalized: list[dict[str, Any]] = []
    for key in state["graph"]:
        record = pages[key]
        request = record["request"]
        prefix = request["prefix"]
        ordinal = ordinals.get(prefix, 0)
        ordinals[prefix] = ordinal + 1
        normalized.append(
            {
                "child_prefixes": sorted(record["child_prefixes"]),
                "is_truncated": record["is_truncated"],
                "page_ordinal": ordinal,
                "prefix": prefix,
            }
        )
    return sorted(normalized, key=lambda item: (item["prefix"], item["page_ordinal"]))


def _compare_listing_passes(
    conn: sqlite3.Connection,
    pins: PlannerPins,
    hooks: PlannerHooks,
    *,
    attempt_hi: int,
    checkpoint: Mapping[str, Any],
    index: sqlite3.Connection,
) -> dict[str, Any]:
    first_state = checkpoint["passes"][PASS_IDS[0]]
    second_state = checkpoint["passes"][PASS_IDS[1]]
    _require(
        first_state["roots"] == second_state["roots"],
        "listing roots drifted across independent passes",
    )
    _require(
        first_state["discovered_prefixes"] == second_state["discovered_prefixes"],
        "listing discovered-prefix reachability drifted across independent passes",
    )
    _require(
        first_state["completed_prefixes"] == second_state["completed_prefixes"],
        "listing completed-prefix reachability drifted across independent passes",
    )
    first_graph = _stable_pass_graph(first_state)
    second_graph = _stable_pass_graph(second_state)
    _require(
        first_graph == second_graph,
        "listing reachability or pagination authority drifted across independent passes",
    )
    digest = hashlib.sha256()
    count = 0
    for item in iter_pending(conn, pins, hooks, attempt_hi=attempt_hi):
        facts: list[dict[str, Any]] = []
        for pass_id in PASS_IDS:
            raw = _lookup_listing(index, pass_id, item.identity)
            sidecar = _lookup_listing(index, pass_id, item.sidecar_key)
            if raw is None or sidecar is None:
                raise BlockedCandidateError(
                    "a pending raw or sidecar key is absent from an independent pass",
                    context={"identity": item.identity, "pass_id": pass_id},
                )
            sidecar_etag = _single_part_etag(
                sidecar[1], label="checksum-sidecar ETag"
            )
            facts.append(
                {
                    "raw": {
                        "etag": raw[1],
                        "key": item.identity,
                        "size": raw[0],
                    },
                    "sidecar": {
                        "etag": sidecar_etag,
                        "key": item.sidecar_key,
                        "size": sidecar[0],
                    },
                }
            )
        _require(
            facts[0] == facts[1],
            "pending listing facts drifted across independent passes",
            {"identity": item.identity},
        )
        digest.update(compact_json({"identity": item.identity, **facts[1]}))
        count += 1
    expected = pins.expected_pending_metrics + pins.expected_pending_book_ticker
    _require(count == expected, "stable listing comparison count changed")
    return {
        "graph_sha256": sha256_bytes(canonical_json(first_graph)),
        "pending_fact_count": count,
        "pending_facts_sha256": digest.hexdigest(),
    }


def _manifest_ceiling(value: int, *, label: str) -> int:
    if isinstance(value, bool) or type(value) is not int or value < 1:
        raise UnsafeCandidateError(f"{label} is not a positive exact integer")
    return value


@contextmanager
def _closing_manifest_iterator(
    lines: Iterator[bytes],
) -> Iterator[Iterator[bytes]]:
    iterator = iter(lines)
    try:
        yield iterator
    finally:
        close = getattr(iterator, "close", None)
        if close is not None:
            close()


def _iter_bounded_manifest_lines(manifest_fd: int) -> Iterator[bytes]:
    """Yield JSONL rows without an unbounded gzip readline allocation."""

    compressed_ceiling = _manifest_ceiling(
        MANIFEST_COMPRESSED_CEILING_BYTES, label="manifest compressed ceiling"
    )
    row_ceiling = _manifest_ceiling(
        MANIFEST_ROW_CEILING_BYTES, label="manifest row ceiling"
    )
    total_ceiling = _manifest_ceiling(
        MANIFEST_DECOMPRESSED_CEILING_BYTES,
        label="manifest decompressed ceiling",
    )
    row_count_ceiling = _manifest_ceiling(
        MANIFEST_ROW_COUNT_CEILING, label="manifest row-count ceiling"
    )
    _require(
        int(os.fstat(manifest_fd).st_size) <= compressed_ceiling,
        "manifest exceeds the compressed-byte ceiling",
    )
    os.lseek(manifest_fd, 0, os.SEEK_SET)
    handle = gzip.GzipFile(fileobj=os.fdopen(os.dup(manifest_fd), "rb"))
    buffered = bytearray()
    total = 0
    row_count = 0
    try:
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > total_ceiling:
                raise BlockedCandidateError(
                    "manifest exceeds the decompressed-byte ceiling"
                )
            buffered.extend(chunk)
            while True:
                newline = buffered.find(b"\n")
                if newline < 0:
                    break
                line_size = newline + 1
                if line_size > row_ceiling:
                    raise BlockedCandidateError(
                        "manifest row exceeds the per-row byte ceiling"
                    )
                row_count += 1
                if row_count > row_count_ceiling:
                    raise BlockedCandidateError(
                        "manifest exceeds the row-count ceiling"
                    )
                line = bytes(buffered[:line_size])
                del buffered[:line_size]
                yield line
            if len(buffered) > row_ceiling:
                raise BlockedCandidateError(
                    "manifest row exceeds the per-row byte ceiling"
                )
        if buffered:
            if len(buffered) > row_ceiling:
                raise BlockedCandidateError(
                    "manifest row exceeds the per-row byte ceiling"
                )
            row_count += 1
            if row_count > row_count_ceiling:
                raise BlockedCandidateError("manifest exceeds the row-count ceiling")
            yield bytes(buffered)
    except (OSError, EOFError, gzip.BadGzipFile, zlib.error) as exc:
        raise BlockedCandidateError("manifest gzip stream is invalid") from exc
    finally:
        handle.close()
        os.lseek(manifest_fd, 0, os.SEEK_SET)


def _write_private_gzip(
    tmp_fd: int, name: str, lines: Iterator[bytes]
) -> tuple[str, int, str]:
    with _closing_manifest_iterator(lines) as owned_lines:
        return _write_private_gzip_from_iterator(tmp_fd, name, owned_lines)


def _write_private_gzip_from_iterator(
    tmp_fd: int, name: str, lines: Iterator[bytes]
) -> tuple[str, int, str]:
    raw = os.open(
        name,
        os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=tmp_fd,
    )
    row_ceiling = _manifest_ceiling(
        MANIFEST_ROW_CEILING_BYTES, label="manifest row ceiling"
    )
    total_ceiling = _manifest_ceiling(
        MANIFEST_DECOMPRESSED_CEILING_BYTES,
        label="manifest decompressed ceiling",
    )
    row_count_ceiling = _manifest_ceiling(
        MANIFEST_ROW_COUNT_CEILING, label="manifest row-count ceiling"
    )
    uncompressed = hashlib.sha256()
    decompressed_bytes = 0
    row_count = 0
    handle = gzip.GzipFile(
        filename="",
        mode="wb",
        fileobj=os.fdopen(os.dup(raw), "wb"),
        mtime=0,
        compresslevel=GZIP_COMPRESSLEVEL,
    )
    try:
        for line in lines:
            if type(line) is not bytes:
                raise BlockedCandidateError("manifest row is not bytes")
            row_count += 1
            if row_count > row_count_ceiling:
                raise BlockedCandidateError("manifest exceeds the row-count ceiling")
            if len(line) > row_ceiling:
                raise BlockedCandidateError(
                    "manifest row exceeds the per-row byte ceiling"
                )
            decompressed_bytes += len(line)
            if decompressed_bytes > total_ceiling:
                raise BlockedCandidateError(
                    "manifest exceeds the decompressed-byte ceiling"
                )
            handle.write(line)
            uncompressed.update(line)
        handle.flush()
    finally:
        handle.close()
        os.fsync(raw)
        digest, size = hash_fd(raw)
        os.close(raw)
    _require(
        size
        <= _manifest_ceiling(
            MANIFEST_COMPRESSED_CEILING_BYTES,
            label="manifest compressed ceiling",
        ),
        "manifest exceeds the compressed-byte ceiling",
    )
    return digest, size, uncompressed.hexdigest()


def _iter_manifest_lines(
    conn: sqlite3.Connection,
    pins: PlannerPins,
    hooks: PlannerHooks,
    *,
    attempt_hi: int,
    content_fd: int,
    pinned_destination: str,
    index: sqlite3.Connection,
    checkpoint: Mapping[str, Any],
) -> Iterator[bytes]:
    pass_id = PASS_IDS[1]
    pages = checkpoint["passes"][pass_id]["pages"]
    for item in iter_pending(conn, pins, hooks, attempt_hi=attempt_hi):
        filled = _rehash_sidecar(
            item, content_fd, pinned_destination=pinned_destination
        )
        raw = _lookup_listing(index, pass_id, filled.identity)
        sidecar_listing = _lookup_listing(index, pass_id, filled.sidecar_key)
        if raw is None:
            raise BlockedCandidateError(
                "a pending raw key is missing from the current listing",
                context={"identity": filled.identity},
            )
        if sidecar_listing is None:
            raise BlockedCandidateError(
                "a pending sidecar key is missing from the current listing",
                context={"identity": filled.sidecar_key},
            )
        current_size, current_etag, page_sha, request_key = raw
        sidecar_size, sidecar_etag, sidecar_page, sidecar_request = sidecar_listing
        _require(
            sidecar_size == filled.sidecar_bytes,
            "retained sidecar/current listing size-and-ETag mismatch",
            context={"identity": filled.sidecar_key},
        )
        expected_etag = md5_hex(filled.sidecar_body)
        exact_sidecar_etag = _single_part_etag(
            sidecar_etag, label="checksum-sidecar ETag"
        )
        _require(
            exact_sidecar_etag == expected_etag,
            "retained sidecar/current listing size-and-ETag mismatch",
            context={"identity": filled.sidecar_key},
        )
        if filled.family == FAMILY_BOOK_TICKER:
            _require(
                current_size == filled.listed_bytes,
                "a book-ticker listing size changed",
            )
        classification = CLASS_ZIP_WORK if filled.family == FAMILY_BOOK_TICKER else CLASS_PROVIDER_REVISION
        page = pages.get(request_key) or {}
        row = {
            "record_type": "row",
            "record": {
                "classification": classification,
                "current_listed_bytes": current_size,
                "current_listing": {
                    "etag": current_etag,
                    "key": filled.identity,
                    "page_sha256": page_sha,
                    "request_key": request_key,
                    "size": current_size,
                },
                "current_sidecar_listing": {
                    "etag": exact_sidecar_etag,
                    "key": filled.sidecar_key,
                    "page_sha256": sidecar_page,
                    "request_key": sidecar_request,
                    "size": sidecar_size,
                },
                "delta_bytes": current_size - filled.listed_bytes,
                "family": filled.family,
                "identity": filled.identity,
                "listing_page_lineage": {
                    "final_url": page.get("final_url"),
                    "prefix": (page.get("request") or {}).get("prefix"),
                    "request": page.get("request"),
                    "response_sha256": page.get("response_sha256"),
                    "status_code": page.get("status_code"),
                },
                "old_listed_bytes": filled.listed_bytes,
                "old_plan_envelope": dict(filled.envelope),
                "old_plan_facts": dict(filled.payload),
                "provider": filled.provider,
                "provider_checksum": filled.provider_checksum,
                "retained_sidecar_bytes": filled.sidecar_bytes,
                "retained_sidecar_path": filled.sidecar_path,
                "retained_sidecar_sha256": filled.sidecar_sha256,
                "symbol": filled.symbol,
                "terminal_attempt": {
                    "class": filled.attempt_class,
                    "ended_at": filled.ended_at,
                    "fact": dict(filled.fact),
                    "id": filled.attempt_id,
                    "status_code": filled.status_code,
                },
                "terminal_error_class": filled.attempt_class,
                "terminal_message": filled.terminal_message,
                "zip_work_ceiling_bytes": zip_work_ceiling(current_size),
            },
        }
        yield compact_json(row)


def _lineage_document(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    passes: dict[str, Any] = {}
    for pass_id in PASS_IDS:
        state = checkpoint["passes"][pass_id]
        pages = state["pages"]
        items = []
        for key in state["graph"]:
            record = pages[key]
            items.append(
                {
                    "byte_size": record["byte_size"],
                    "child_prefixes": list(record["child_prefixes"]),
                    "final_url": record["final_url"],
                    "headers": dict(record["headers"]),
                    "is_truncated": record["is_truncated"],
                    "next_continuation_token": record["next_continuation_token"],
                    "pass_id": pass_id,
                    "request": dict(record["request"]),
                    "request_key": key,
                    "response_sha256": record["response_sha256"],
                    "retrieved_at": record["retrieved_at"],
                    "status_code": record["status_code"],
                }
            )
        passes[pass_id] = {
            "graph": list(state["graph"]),
            "pages": items,
            "roots": list(state["roots"]),
        }
    return {
        "passes": passes,
        "schema_version": LINEAGE_SCHEMA,
    }


def _semantic_receipt_payload(receipt: Mapping[str, Any]) -> dict[str, Any]:
    payload = {key: receipt[key] for key in SEMANTIC_RECEIPT_KEYS}
    lineage = dict(payload["lineage"])
    for key in ("asset_bytes", "asset_name", "asset_sha256"):
        lineage.pop(key, None)
    payload["lineage"] = lineage
    manifest = payload["manifest"]
    payload["manifest"] = {
        "format": manifest["format"],
        "row_count": manifest["row_count"],
        "semantic_rows_sha256": manifest["semantic_rows_sha256"],
    }
    return payload


def _semantic_manifest_row(row: Mapping[str, Any]) -> dict[str, Any]:
    record = dict(row["record"])
    current_listing = dict(record["current_listing"])
    current_sidecar_listing = dict(record["current_sidecar_listing"])
    for locator in (current_listing, current_sidecar_listing):
        locator.pop("page_sha256")
        locator.pop("request_key")
    record["current_listing"] = current_listing
    record["current_sidecar_listing"] = current_sidecar_listing
    record.pop("listing_page_lineage")
    return {"record": record, "record_type": row["record_type"]}


def _read_json_asset(
    directory_fd: int,
    name: str,
    *,
    expected_sha256: str,
    suffix: str,
    ceiling: int,
    label: str,
) -> tuple[dict[str, Any], bytes]:
    digest = _hex_digest(expected_sha256, label=f"{label} digest")
    _require(name == f"{digest}{suffix}", f"{label} name is not content addressed")
    with _bound_named_regular(directory_fd, name, label=label) as fd:
        body = _read_fd_bounded(fd, ceiling=ceiling, label=label)
        actual, size = hash_fd(fd)
    _require(actual == digest and size == len(body), f"{label} does not rehash")
    try:
        document = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BlockedCandidateError(f"{label} is not canonical JSON") from exc
    if type(document) is not dict:
        raise BlockedCandidateError(f"{label} is not an object")
    _require(canonical_json(document) == body, f"{label} JSON is not canonical")
    return document, body


def _authenticate_manifest_asset(
    manifest_fd: int,
    *,
    receipt: Mapping[str, Any],
    expected_lines: Iterator[bytes],
) -> dict[str, Any]:
    with _closing_manifest_iterator(expected_lines) as expected:
        return _authenticate_manifest_asset_from_iterators(
            manifest_fd,
            receipt=receipt,
            expected=expected,
        )


def _authenticate_manifest_asset_from_iterators(
    manifest_fd: int,
    *,
    receipt: Mapping[str, Any],
    expected: Iterator[bytes],
) -> dict[str, Any]:
    manifest = receipt["manifest"]
    compressed_ceiling = _manifest_ceiling(
        MANIFEST_COMPRESSED_CEILING_BYTES, label="manifest compressed ceiling"
    )
    declared_size = _exact_int(
        manifest["compressed_bytes"], label="receipt manifest bytes", minimum=1
    )
    _require(
        declared_size <= compressed_ceiling,
        "manifest exceeds the compressed-byte ceiling",
    )
    _require(
        int(os.fstat(manifest_fd).st_size) <= compressed_ceiling,
        "manifest exceeds the compressed-byte ceiling",
    )
    declared_rows = _exact_int(
        manifest["row_count"], label="receipt manifest rows", minimum=0
    )
    _require(
        declared_rows
        <= _manifest_ceiling(
            MANIFEST_ROW_COUNT_CEILING, label="manifest row-count ceiling"
        ),
        "manifest exceeds the row-count ceiling",
    )
    digest, size = hash_fd(manifest_fd)
    _require(digest == manifest["compressed_sha256"], "manifest digest changed")
    _require(size == manifest["compressed_bytes"], "manifest byte size changed")
    uncompressed = hashlib.sha256()
    semantic_rows = hashlib.sha256()
    pending_digest = hashlib.sha256()
    row_count = 0
    old_total = 0
    current_total = 0
    metrics_old = 0
    metrics_current = 0
    book_old = 0
    book_current = 0
    maximum = 0
    class_counts = {CLASS_PROVIDER_REVISION: 0, CLASS_ZIP_WORK: 0}
    message_counts: dict[str, int] = {}
    actual_lines = _iter_bounded_manifest_lines(manifest_fd)
    with _closing_manifest_iterator(actual_lines) as actual:
        for line in actual:
            try:
                expected_line = next(expected)
            except StopIteration as exc:
                raise BlockedCandidateError(
                    "manifest contains an unexpected extra row"
                ) from exc
            _require(
                line == expected_line,
                "manifest row changed from current authority",
            )
            uncompressed.update(line)
            try:
                row = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise BlockedCandidateError("manifest contains invalid JSON") from exc
            _exact_keys(row, {"record", "record_type"}, label="manifest row")
            _require(row["record_type"] == "row", "manifest record type changed")
            semantic_rows.update(compact_json(_semantic_manifest_row(row)))
            record = row["record"]
            if type(record) is not dict:
                raise BlockedCandidateError("manifest record is not an object")
            identity = str(record.get("identity") or "")
            family = str(record.get("family") or "")
            _require(
                identity and family in AFFECTED_FAMILIES,
                "manifest identity changed",
            )
            pending_digest.update(
                compact_json({"identity": identity, "family": family})
            )
            old_bytes = _exact_int(
                record.get("old_listed_bytes"),
                label="manifest old bytes",
                minimum=1,
            )
            current_bytes = _exact_int(
                record.get("current_listed_bytes"),
                label="manifest current bytes",
                minimum=1,
            )
            classification = record.get("classification")
            _require(
                classification in class_counts,
                "manifest classification changed",
            )
            terminal_message = record.get("terminal_message")
            _require(
                type(terminal_message) is str,
                "manifest terminal message changed",
            )
            old_total += old_bytes
            current_total += current_bytes
            maximum = max(maximum, current_bytes)
            class_counts[classification] += 1
            message_counts[terminal_message] = (
                message_counts.get(terminal_message, 0) + 1
            )
            if family == FAMILY_METRICS:
                metrics_old += old_bytes
                metrics_current += current_bytes
            else:
                book_old += old_bytes
                book_current += current_bytes
            row_count += 1
    try:
        next(expected)
    except StopIteration:
        pass
    else:
        raise BlockedCandidateError("manifest is missing a current-authority row")
    _require(row_count == manifest["row_count"], "manifest row count changed")
    _require(
        uncompressed.hexdigest() == manifest["uncompressed_sha256"],
        "manifest uncompressed digest changed",
    )
    _require(
        semantic_rows.hexdigest() == manifest["semantic_rows_sha256"],
        "manifest semantic-row digest changed",
    )
    _require(
        pending_digest.hexdigest() == receipt["pending"]["identity_sha256"],
        "manifest pending identity changed",
    )
    _require(old_total == receipt["bytes"]["old_planned_bytes"], "manifest old byte equation changed")
    _require(current_total == receipt["bytes"]["current_listed_bytes"], "manifest current byte equation changed")
    return {
        "book_current": book_current,
        "book_old": book_old,
        "class_counts": class_counts,
        "compressed_bytes": size,
        "compressed_sha256": digest,
        "current_total": current_total,
        "maximum": maximum,
        "message_counts": dict(sorted(message_counts.items())),
        "metrics_current": metrics_current,
        "metrics_old": metrics_old,
        "old_total": old_total,
        "row_count": row_count,
        "semantic_rows_sha256": semantic_rows.hexdigest(),
        "uncompressed_sha256": uncompressed.hexdigest(),
    }


def _authenticate_completed_candidate(
    *,
    locator_body: bytes,
    candidate_fd: int,
    pages_fd: int,
    manifest_fd: int,
    receipt_fd: int,
    lineage_fd: int,
    generation: Mapping[str, Any],
    pending: Mapping[str, Any],
    code_identity: Mapping[str, str],
    conn: sqlite3.Connection,
    pins: PlannerPins,
    hooks: PlannerHooks,
    attempt_hi: int,
    index: sqlite3.Connection,
    content_fd: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        locator = json.loads(locator_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BlockedCandidateError("locator is not JSON") from exc
    _exact_keys(
        locator,
        {
            "code_identity",
            "generation_plan_identity",
            "generation_state_sha256",
            "lineage_name",
            "lineage_sha256",
            "manifest_name",
            "manifest_sha256",
            "pending_identity_sha256",
            "receipt_name",
            "receipt_sha256",
            "schema_version",
            "semantic_sha256",
        },
        label="locator",
    )
    _require(canonical_json(locator) == locator_body, "locator JSON is not canonical")
    _require(locator["schema_version"] == LOCATOR_SCHEMA, "locator schema changed")
    for field in (
        "generation_state_sha256",
        "lineage_sha256",
        "manifest_sha256",
        "pending_identity_sha256",
        "receipt_sha256",
        "semantic_sha256",
    ):
        _hex_digest(locator[field], label=f"locator {field}")
    for field in ("lineage_name", "manifest_name", "receipt_name"):
        _require(type(locator[field]) is str, f"locator {field} is not text")
    _require(locator["code_identity"] == dict(code_identity), "completed locator code identity changed")
    _require(locator["generation_plan_identity"] == generation["plan_identity"], "completed locator plan identity changed")
    state = (generation.get("physical") or {}).get("state") or {}
    _require(locator["generation_state_sha256"] == state.get("sha256"), "completed locator state identity changed")
    _require(locator["pending_identity_sha256"] == pending["identity_sha256"], "completed locator pending identity changed")
    checkpoint = _load_checkpoint(candidate_fd, pages_fd)
    if checkpoint is None:
        raise BlockedCandidateError("completed locator has no checkpoint authority")
    _authenticate_checkpoint(
        checkpoint,
        generation=generation,
        pending=pending,
        code=code_identity,
        pages_fd=pages_fd,
    )
    for pass_id in PASS_IDS:
        _require(checkpoint["passes"][pass_id]["listing_complete"] is True, "completed locator has an incomplete listing pass")
        _rebuild_index_from_graph(
            checkpoint["passes"][pass_id],
            pass_id=pass_id,
            pages_fd=pages_fd,
            index=index,
            hooks=hooks,
        )
    stable_listing = _compare_listing_passes(
        conn,
        pins,
        hooks,
        attempt_hi=attempt_hi,
        checkpoint=checkpoint,
        index=index,
    )
    lineage, lineage_body = _read_json_asset(
        lineage_fd,
        str(locator["lineage_name"]),
        expected_sha256=str(locator["lineage_sha256"]),
        suffix=".json",
        ceiling=LINEAGE_CEILING_BYTES,
        label="lineage asset",
    )
    _require(lineage == _lineage_document(checkpoint), "lineage asset does not match the reachable checkpoint graphs")
    receipt, receipt_body = _read_json_asset(
        receipt_fd,
        str(locator["receipt_name"]),
        expected_sha256=str(locator["receipt_sha256"]),
        suffix=".json",
        ceiling=RECEIPT_CEILING_BYTES,
        label="receipt asset",
    )
    _exact_keys(
        receipt,
        {
            "adr",
            "authorization",
            "bytes",
            "capacity_projection",
            "classification",
            "code_identity",
            "generation_0",
            "lineage",
            "listing",
            "manifest",
            "pending",
            "policy_identity",
            "schema_version",
            "semantic_sha256",
            "ticket",
            "zip_work_policy",
        },
        label="candidate receipt",
    )
    _require(receipt["schema_version"] == CANDIDATE_SCHEMA, "candidate receipt schema changed")
    _exact_keys(
        receipt["authorization"],
        {"acquisition_authorized", "candidate_accepted", "gate_2_accepted", "statement"},
        label="candidate authorization",
    )
    _exact_keys(
        receipt["bytes"],
        {
            "book_ticker_current_bytes",
            "book_ticker_delta_bytes",
            "book_ticker_old_bytes",
            "current_listed_bytes",
            "delta_bytes",
            "equation",
            "metrics_current_bytes",
            "metrics_delta_bytes",
            "metrics_old_bytes",
            "old_planned_bytes",
        },
        label="candidate byte equations",
    )
    _exact_keys(
        receipt["capacity_projection"],
        {
            "acquisition_authorized",
            "available_bytes",
            "candidate_accepted",
            "measurement_only",
            "needed_bytes",
            "operating_reserve_bytes",
            "pending_current_listed_bytes",
            "remainder_bytes",
            "statement",
        },
        label="candidate capacity projection",
    )
    _exact_keys(
        receipt["classification"],
        {
            "book_ticker_zip_work",
            "message_counts",
            "metrics_revision",
            "provider_revision_rows",
            "zip_work_rows",
        },
        label="candidate classification",
    )
    _exact_keys(
        receipt["lineage"],
        {
            "asset_bytes",
            "asset_name",
            "asset_sha256",
            "pass_page_counts",
            "schema_version",
            "stable_graph_sha256",
            "stable_pending_fact_count",
            "stable_pending_facts_sha256",
        },
        label="candidate lineage reference",
    )
    _exact_keys(
        receipt["listing"],
        {
            "current_maximum_object_bytes",
            "family_prefixes",
            "independent_passes",
            "page_count",
            "pass_page_counts",
            "stable_graph_sha256",
            "stable_pending_facts_sha256",
        },
        label="candidate listing proof",
    )
    _exact_keys(
        receipt["manifest"],
        {
            "compressed_bytes",
            "compressed_sha256",
            "format",
            "name",
            "row_count",
            "semantic_rows_sha256",
            "uncompressed_sha256",
        },
        label="candidate manifest reference",
    )
    _exact_keys(
        receipt["pending"],
        {
            "book_ticker_zip_work",
            "identity_sha256",
            "messages",
            "metrics_revision",
            "total",
        },
        label="candidate pending proof",
    )
    _exact_keys(
        receipt["zip_work_policy"],
        {"absolute_ceiling_bytes", "equation", "floor_bytes", "ratio"},
        label="candidate ZIP-work policy",
    )
    _require(receipt["ticket"] == TICKET_ID and receipt["adr"] == ADR_ID, "candidate governance identity changed")
    _require(receipt["policy_identity"] == POLICY_IDENTITY, "candidate policy identity changed")
    _require(
        receipt["authorization"]["acquisition_authorized"] is False
        and receipt["authorization"]["candidate_accepted"] is False
        and receipt["authorization"]["gate_2_accepted"] is False,
        "candidate authorization booleans changed",
    )
    _require(receipt["authorization"] == AUTHORIZATION, "candidate authorization changed")
    _require(receipt["manifest"]["format"] == MANIFEST_FORMAT, "candidate manifest format changed")
    _hex_digest(receipt["manifest"]["compressed_sha256"], label="receipt manifest digest")
    _hex_digest(
        receipt["manifest"]["semantic_rows_sha256"],
        label="receipt semantic-row digest",
    )
    _hex_digest(receipt["manifest"]["uncompressed_sha256"], label="receipt uncompressed manifest digest")
    _exact_int(receipt["manifest"]["compressed_bytes"], label="receipt manifest bytes", minimum=1)
    _exact_int(receipt["manifest"]["row_count"], label="receipt manifest rows", minimum=0)
    _hex_digest(receipt["lineage"]["asset_sha256"], label="receipt lineage digest")
    _exact_int(receipt["lineage"]["asset_bytes"], label="receipt lineage bytes", minimum=1)
    for key in ("absolute_ceiling_bytes", "floor_bytes", "ratio"):
        _exact_int(receipt["zip_work_policy"][key], label=f"receipt ZIP policy {key}", minimum=1)
    _require(
        receipt["zip_work_policy"]
        == {
            "absolute_ceiling_bytes": ZIP_ABSOLUTE_CEILING_BYTES,
            "equation": ZIP_POLICY_EQUATION,
            "floor_bytes": ZIP_FLOOR_BYTES,
            "ratio": ZIP_RATIO,
        },
        "candidate ZIP-work policy changed",
    )
    _require(receipt["code_identity"] == dict(code_identity), "candidate receipt code identity changed")
    _require(receipt["generation_0"] == generation, "candidate receipt generation identity changed")
    for key in ("book_ticker_zip_work", "metrics_revision", "total"):
        _exact_int(receipt["pending"][key], label=f"receipt pending {key}", minimum=0)
    _hex_digest(receipt["pending"]["identity_sha256"], label="receipt pending identity digest")
    if type(receipt["pending"]["messages"]) is not dict:
        raise BlockedCandidateError("receipt pending messages are not an object")
    for value in receipt["pending"]["messages"].values():
        _exact_int(value, label="receipt pending message count", minimum=0)
    _require(receipt["pending"] == pending, "candidate receipt pending identity changed")
    pass_page_counts = {
        pass_id: len(checkpoint["passes"][pass_id]["graph"]) for pass_id in PASS_IDS
    }
    _require(receipt["listing"]["family_prefixes"] == list(FAMILY_PREFIXES), "receipt listing family prefixes changed")
    _require(receipt["listing"]["independent_passes"] == list(PASS_IDS), "receipt listing pass identities changed")
    _require(receipt["listing"]["pass_page_counts"] == pass_page_counts, "receipt listing page counts changed")
    _require(receipt["listing"]["page_count"] == sum(pass_page_counts.values()), "receipt listing total page count changed")
    _require(receipt["lineage"]["pass_page_counts"] == pass_page_counts, "receipt lineage page counts changed")
    _require(receipt["lineage"]["schema_version"] == LINEAGE_SCHEMA, "receipt lineage schema changed")
    _require(receipt["manifest"]["row_count"] == pending["total"], "receipt manifest row count changed")
    _require(receipt["lineage"]["asset_name"] == locator["lineage_name"], "receipt lineage name changed")
    _require(receipt["lineage"]["asset_sha256"] == locator["lineage_sha256"], "receipt lineage digest changed")
    _require(receipt["lineage"]["asset_bytes"] == len(lineage_body), "receipt lineage byte size changed")
    _require(receipt["manifest"]["name"] == locator["manifest_name"], "receipt manifest name changed")
    _require(receipt["manifest"]["compressed_sha256"] == locator["manifest_sha256"], "receipt manifest digest changed")
    _require(
        receipt["listing"]["stable_graph_sha256"] == stable_listing["graph_sha256"],
        "receipt stable graph identity changed",
    )
    _require(
        receipt["listing"]["stable_pending_facts_sha256"]
        == stable_listing["pending_facts_sha256"],
        "receipt stable pending facts changed",
    )
    _require(
        receipt["lineage"]["stable_graph_sha256"] == stable_listing["graph_sha256"]
        and receipt["lineage"]["stable_pending_facts_sha256"]
        == stable_listing["pending_facts_sha256"]
        and receipt["lineage"]["stable_pending_fact_count"]
        == stable_listing["pending_fact_count"],
        "receipt lineage stability proof changed",
    )
    semantic = sha256_bytes(canonical_json(_semantic_receipt_payload(receipt)))
    _require(semantic == receipt["semantic_sha256"], "candidate receipt semantic identity changed")
    _require(semantic == locator["semantic_sha256"], "locator semantic identity changed")
    _require(sha256_bytes(receipt_body) == locator["receipt_sha256"], "receipt asset changed")
    manifest_name = str(locator["manifest_name"])
    manifest_digest = _hex_digest(str(locator["manifest_sha256"]), label="manifest digest")
    _require(manifest_name == f"{manifest_digest}.json.gz", "manifest name is not content addressed")
    with _bound_named_regular(
        manifest_fd, manifest_name, label="manifest asset"
    ) as manifest_file:
        manifest_facts = _authenticate_manifest_asset(
            manifest_file,
            receipt=receipt,
            expected_lines=_iter_manifest_lines(
                conn,
                pins,
                hooks,
                attempt_hi=attempt_hi,
                content_fd=content_fd,
                pinned_destination=str(generation["authority_destination"]),
                index=index,
                checkpoint=checkpoint,
            ),
        )
    expected_bytes = {
        "book_ticker_current_bytes": manifest_facts["book_current"],
        "book_ticker_delta_bytes": manifest_facts["book_current"]
        - manifest_facts["book_old"],
        "book_ticker_old_bytes": manifest_facts["book_old"],
        "current_listed_bytes": manifest_facts["current_total"],
        "delta_bytes": manifest_facts["current_total"] - manifest_facts["old_total"],
        "equation": BYTE_EQUATION,
        "metrics_current_bytes": manifest_facts["metrics_current"],
        "metrics_delta_bytes": manifest_facts["metrics_current"]
        - manifest_facts["metrics_old"],
        "metrics_old_bytes": manifest_facts["metrics_old"],
        "old_planned_bytes": manifest_facts["old_total"],
    }
    for key, value in receipt["bytes"].items():
        if key != "equation":
            _exact_int(value, label=f"receipt byte claim {key}", minimum=0)
    _require(receipt["bytes"] == expected_bytes, "candidate byte claims changed")
    expected_classification = {
        "book_ticker_zip_work": manifest_facts["class_counts"][CLASS_ZIP_WORK],
        "message_counts": manifest_facts["message_counts"],
        "metrics_revision": manifest_facts["class_counts"][CLASS_PROVIDER_REVISION],
        "provider_revision_rows": manifest_facts["class_counts"][CLASS_PROVIDER_REVISION],
        "zip_work_rows": manifest_facts["class_counts"][CLASS_ZIP_WORK],
    }
    for key in (
        "book_ticker_zip_work",
        "metrics_revision",
        "provider_revision_rows",
        "zip_work_rows",
    ):
        _exact_int(receipt["classification"][key], label=f"receipt classification {key}", minimum=0)
    if type(receipt["classification"]["message_counts"]) is not dict:
        raise BlockedCandidateError("receipt message counts are not an object")
    for value in receipt["classification"]["message_counts"].values():
        _exact_int(value, label="receipt terminal-message count", minimum=0)
    _require(
        receipt["classification"] == expected_classification,
        "candidate classification claims changed",
    )
    expected_listing = {
        "current_maximum_object_bytes": manifest_facts["maximum"],
        "family_prefixes": list(FAMILY_PREFIXES),
        "independent_passes": list(PASS_IDS),
        "page_count": sum(pass_page_counts.values()),
        "pass_page_counts": pass_page_counts,
        "stable_graph_sha256": stable_listing["graph_sha256"],
        "stable_pending_facts_sha256": stable_listing["pending_facts_sha256"],
    }
    _exact_int(
        receipt["listing"]["current_maximum_object_bytes"],
        label="receipt current maximum object bytes",
        minimum=0,
    )
    _exact_int(receipt["listing"]["page_count"], label="receipt page count", minimum=0)
    if type(receipt["listing"]["pass_page_counts"]) is not dict:
        raise BlockedCandidateError("receipt pass-page counts are not an object")
    for value in receipt["listing"]["pass_page_counts"].values():
        _exact_int(value, label="receipt pass-page count", minimum=0)
    _require(receipt["listing"] == expected_listing, "candidate listing claims changed")
    expected_lineage = {
        "asset_bytes": len(lineage_body),
        "asset_name": locator["lineage_name"],
        "asset_sha256": locator["lineage_sha256"],
        "pass_page_counts": pass_page_counts,
        "schema_version": LINEAGE_SCHEMA,
        "stable_graph_sha256": stable_listing["graph_sha256"],
        "stable_pending_fact_count": stable_listing["pending_fact_count"],
        "stable_pending_facts_sha256": stable_listing["pending_facts_sha256"],
    }
    _exact_int(
        receipt["lineage"]["stable_pending_fact_count"],
        label="receipt stable pending fact count",
        minimum=0,
    )
    if type(receipt["lineage"]["pass_page_counts"]) is not dict:
        raise BlockedCandidateError("receipt lineage pass-page counts are not an object")
    for value in receipt["lineage"]["pass_page_counts"].values():
        _exact_int(value, label="receipt lineage pass-page count", minimum=0)
    _require(receipt["lineage"] == expected_lineage, "candidate lineage claims changed")
    expected_manifest = {
        "compressed_bytes": manifest_facts["compressed_bytes"],
        "compressed_sha256": manifest_facts["compressed_sha256"],
        "format": MANIFEST_FORMAT,
        "name": manifest_name,
        "row_count": manifest_facts["row_count"],
        "semantic_rows_sha256": manifest_facts["semantic_rows_sha256"],
        "uncompressed_sha256": manifest_facts["uncompressed_sha256"],
    }
    _require(receipt["manifest"] == expected_manifest, "candidate manifest claims changed")
    available = _exact_int(
        receipt["capacity_projection"]["available_bytes"],
        label="historical available bytes",
        minimum=0,
    )
    reserve = operating_reserve_bytes(available)
    expected_capacity = {
        "acquisition_authorized": False,
        "available_bytes": available,
        "candidate_accepted": False,
        "measurement_only": True,
        "needed_bytes": manifest_facts["current_total"] + reserve,
        "operating_reserve_bytes": reserve,
        "pending_current_listed_bytes": manifest_facts["current_total"],
        "remainder_bytes": available - manifest_facts["current_total"] - reserve,
        "statement": CAPACITY_STATEMENT,
    }
    for key in (
        "needed_bytes",
        "operating_reserve_bytes",
        "pending_current_listed_bytes",
        "remainder_bytes",
    ):
        _exact_int(receipt["capacity_projection"][key], label=f"receipt capacity {key}")
    _require(
        receipt["capacity_projection"]["acquisition_authorized"] is False
        and receipt["capacity_projection"]["candidate_accepted"] is False
        and receipt["capacity_projection"]["measurement_only"] is True,
        "candidate capacity booleans changed",
    )
    _require(
        receipt["capacity_projection"] == expected_capacity,
        "candidate capacity projection changed",
    )
    return locator, receipt


def _prove_candidate_layout(paths: PlannerPaths) -> None:
    store = Path(os.path.abspath(str(paths.store_root)))
    gate2 = Path(os.path.abspath(str(paths.gate2_root)))
    candidate = Path(os.path.abspath(str(paths.candidate_root)))
    _require(".." not in Path(paths.candidate_root).parts, "candidate root contains a parent traversal", unsafe=True)
    _require(gate2.name == FIXED_ACTIVE_NAME, "generation-0 active name changed", unsafe=True)
    _require(candidate.name == FIXED_CANDIDATE_NAME, "candidate name is not the required sibling", unsafe=True)
    _require(candidate.parent == gate2.parent, "candidate root is not the required sibling of gate2", unsafe=True)
    _require(gate2.parent == store, "gate2 is not under the store root", unsafe=True)
    _require(candidate != store, "candidate root is the store root", unsafe=True)


def _rebind_child_dir(parent_fd: int, name: str, held_fd: int, *, label: str) -> None:
    try:
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise UnsafeCandidateError(f"{label} name disappeared after open") from exc
    except OSError as exc:
        raise UnsafeCandidateError(f"{label} name cannot be rebound safely") from exc
    if stat.S_ISLNK(named.st_mode) or not stat.S_ISDIR(named.st_mode):
        raise UnsafeCandidateError(f"{label} name is not the held directory")
    held = os.fstat(held_fd)
    _require(
        (int(named.st_dev), int(named.st_ino)) == (int(held.st_dev), int(held.st_ino)),
        f"{label} name no longer identifies the held directory",
        unsafe=True,
    )


def _snapshot_named_regular_identity(
    parent_fd: int, name: str, *, label: str
) -> tuple[int, int, int, int, int]:
    with _bound_named_regular(parent_fd, name, label=label) as fd:
        return _regular_identity(os.fstat(fd))


def _completed_tree_identity(
    *,
    locator: Mapping[str, Any],
    candidate_fd: int,
    pages_fd: int,
    manifest_fd: int,
    receipt_fd: int,
    lineage_fd: int,
) -> dict[str, Any]:
    """Capture every current completed-candidate name across a recovery hook."""

    checkpoint = _load_checkpoint(candidate_fd, pages_fd)
    if checkpoint is None:
        raise BlockedCandidateError("completed locator has no checkpoint authority")
    identities: dict[str, Any] = {
        "checkpoint": _snapshot_named_regular_identity(
            candidate_fd, CHECKPOINT_NAME, label="checkpoint"
        ),
        "lineage": _snapshot_named_regular_identity(
            lineage_fd, str(locator["lineage_name"]), label="lineage asset"
        ),
        "locator": _snapshot_named_regular_identity(
            candidate_fd, LOCATOR_NAME, label="locator"
        ),
        "manifest": _snapshot_named_regular_identity(
            manifest_fd, str(locator["manifest_name"]), label="manifest asset"
        ),
        "receipt": _snapshot_named_regular_identity(
            receipt_fd, str(locator["receipt_name"]), label="receipt asset"
        ),
    }
    page_directories: dict[str, tuple[int, int, int]] = {}
    page_leaves: dict[str, tuple[int, int, int, int, int]] = {}
    for pass_id in PASS_IDS:
        state = checkpoint["passes"][pass_id]
        for request_key in state["graph"]:
            digest = str(state["pages"][request_key]["response_sha256"])
            shard, name = content_path_parts(digest)
            shard_fd = open_child_dir(pages_fd, shard, create=False)
            try:
                _rebind_child_dir(
                    pages_fd,
                    shard,
                    shard_fd,
                    label="candidate listing-page shard",
                )
                shard_stat = os.fstat(shard_fd)
                page_directories[shard] = (
                    int(shard_stat.st_dev),
                    int(shard_stat.st_ino),
                    int(shard_stat.st_mode),
                )
                page_leaves[digest] = _snapshot_named_regular_identity(
                    shard_fd, name, label="retained listing page"
                )
                _rebind_child_dir(
                    pages_fd,
                    shard,
                    shard_fd,
                    label="candidate listing-page shard",
                )
            finally:
                os.close(shard_fd)
    identities["page_directories"] = dict(sorted(page_directories.items()))
    identities["page_leaves"] = dict(sorted(page_leaves.items()))
    return identities


def _rebind_completed_directories(
    *,
    store_parent_fd: int,
    store_path: Path,
    store_fd: int,
    gate2_fd: int,
    content_fd: int,
    candidate_fd: int,
    tmp_fd: int,
    pages_fd: int,
    manifest_fd: int,
    receipt_fd: int,
    lineage_fd: int,
) -> None:
    _rebind_child_dir(store_parent_fd, store_path.name, store_fd, label="store root")
    _rebind_child_dir(store_fd, FIXED_ACTIVE_NAME, gate2_fd, label="generation-0 root")
    _rebind_child_dir(
        gate2_fd, CONTENT_NAME, content_fd, label="generation-0 content root"
    )
    _rebind_child_dir(
        store_fd, FIXED_CANDIDATE_NAME, candidate_fd, label="candidate root"
    )
    for child_name, child_fd, label in (
        (TMP_NAME, tmp_fd, "candidate temporary root"),
        (PAGES_NAME, pages_fd, "candidate listing-page root"),
        (MANIFEST_NAME, manifest_fd, "candidate manifest root"),
        (RECEIPT_NAME, receipt_fd, "candidate receipt root"),
        (LINEAGE_NAME, lineage_fd, "candidate lineage root"),
    ):
        _rebind_child_dir(candidate_fd, child_name, child_fd, label=label)


def plan_revision_candidate(
    paths: PlannerPaths,
    pins: PlannerPins = PRODUCTION_PINS,
    *,
    hooks: PlannerHooks | None = None,
    transport: ListingTransport | None = None,
) -> dict[str, Any]:
    hooks = hooks or PlannerHooks()
    try:
        return _plan_revision_candidate(
            paths, pins, hooks=hooks, transport=transport or hooks.transport
        )
    except ListingInterrupted as exc:
        return {
            "checkpoint_path": str(paths.candidate_root / CHECKPOINT_NAME),
            "exit_code": EXIT_RESUMABLE_PARTIAL,
            "locator_path": None,
            "manifest_path": None,
            "message": exc.message,
            "receipt": None,
            "receipt_path": None,
            "stop_reason": "resumable_partial",
        }
    except UnsafeCandidateError as exc:
        return {
            "checkpoint_path": None,
            "exit_code": EXIT_UNSAFE,
            "locator_path": None,
            "manifest_path": None,
            "message": exc.message,
            "receipt": None,
            "receipt_path": None,
            "stop_reason": "unsafe",
        }
    except BlockedCandidateError as exc:
        return {
            "checkpoint_path": None,
            "exit_code": EXIT_BLOCKED,
            "locator_path": None,
            "manifest_path": None,
            "message": exc.message,
            "receipt": None,
            "receipt_path": None,
            "stop_reason": "blocked",
        }


def _plan_revision_candidate(
    paths: PlannerPaths,
    pins: PlannerPins,
    *,
    hooks: PlannerHooks,
    transport: ListingTransport | None,
) -> dict[str, Any]:
    _prove_candidate_layout(paths)
    held = HeldFds()
    conn: sqlite3.Connection | None = None
    listing_index: sqlite3.Connection | None = None
    try:
        repo_fd = held.add(open_root_dir(paths.repository, create=False))
        code_start = {
            "acquisition_cli_sha256": _hash_under_repo(repo_fd, ACQUISITION_CLI_RELATIVE),
            "acquisition_source_sha256": _hash_under_repo(repo_fd, ACQUISITION_SOURCE_RELATIVE),
            "planner_cli_sha256": _hash_under_repo(repo_fd, CLI_RELATIVE),
            "planner_source_sha256": _hash_under_repo(repo_fd, SOURCE_RELATIVE),
        }
        store_path = Path(os.path.abspath(str(paths.store_root)))
        store_parent_fd = held.add(open_root_dir(store_path.parent, create=False))
        store_fd = held.add(open_child_dir(store_parent_fd, store_path.name, create=False))
        _rebind_child_dir(store_parent_fd, store_path.name, store_fd, label="store root")
        gate2_fd = held.add(open_child_dir(store_fd, FIXED_ACTIVE_NAME, create=False))
        if hooks.after_generation_open is not None:
            hooks.after_generation_open(gate2_fd)
        _rebind_child_dir(store_fd, FIXED_ACTIVE_NAME, gate2_fd, label="generation-0 root")
        lock_fd = held.add(_acquire_lock(gate2_fd, LOCK_NAME, create=False))
        _ = lock_fd
        before = snapshot_sqlite_leaves(gate2_fd, hooks)
        if before["state"] is None:
            raise UnsafeCandidateError("SQLite state is missing")
        if pins.require_physical_state_pins:
            _require(int(before["state"]["bytes"]) == pins.expected_state_bytes, "generation-0 state size changed")
            _require(str(before["state"]["sha256"]) == pins.expected_state_sha256, "generation-0 state digest changed")
        sqlite_fd = held.add(open_child_file(gate2_fd, SQLITE_NAME))
        after_open_hash, _size = hash_fd(sqlite_fd)
        _require(after_open_hash == before["state"]["sha256"], "state digest changed during open")
        conn = _open_sqlite_immutable(sqlite_fd, hooks)
        device_label = f"dev:{os.fstat(gate2_fd).st_dev}"
        generation = _bind_generation0(
            conn,
            pins,
            state_snapshot=before,
            device_label=device_label,
            code_identity=code_start,
        )
        pending_summary = _count_and_prove_pending(
            conn, pins, hooks, attempt_hi=int(generation["watermarks"]["attempt_hi"])
        )
        content_fd = held.add(open_child_dir(gate2_fd, CONTENT_NAME, create=False))
        if hooks.after_content_open is not None:
            hooks.after_content_open(content_fd)
        _rebind_child_dir(gate2_fd, CONTENT_NAME, content_fd, label="generation-0 content root")
        for item in iter_pending(
            conn, pins, hooks, attempt_hi=int(generation["watermarks"]["attempt_hi"])
        ):
            _rehash_sidecar(
                item,
                content_fd,
                pinned_destination=str(generation["authority_destination"]),
            )
        candidate_fd = held.add(
            open_child_dir(store_fd, FIXED_CANDIDATE_NAME, create=True)
        )
        if hooks.after_candidate_open is not None:
            hooks.after_candidate_open(candidate_fd)
        _rebind_child_dir(
            store_fd,
            FIXED_CANDIDATE_NAME,
            candidate_fd,
            label="candidate root",
        )
        held.add(_acquire_lock(candidate_fd, CANDIDATE_LOCK_NAME, create=True))
        after_layout = os.fstat(candidate_fd)
        gate2_stat = os.fstat(gate2_fd)
        _require(after_layout.st_dev == gate2_stat.st_dev, "candidate root is on a different device", unsafe=True)
        tmp_fd = held.add(open_child_dir(candidate_fd, TMP_NAME, create=True))
        _cleanup_partials(tmp_fd)
        pages_fd = held.add(open_child_dir(candidate_fd, PAGES_NAME, create=True))
        manifest_fd = held.add(open_child_dir(candidate_fd, MANIFEST_NAME, create=True))
        receipt_fd = held.add(open_child_dir(candidate_fd, RECEIPT_NAME, create=True))
        lineage_fd = held.add(open_child_dir(candidate_fd, LINEAGE_NAME, create=True))
        listing_index = _open_listing_index(tmp_fd, held)
        locator_fd = _open_optional_regular(candidate_fd, LOCATOR_NAME)
        if locator_fd is not None:
            os.close(locator_fd)
            payload = _read_bound_named_regular(
                candidate_fd,
                LOCATOR_NAME,
                ceiling=LOCATOR_CEILING_BYTES,
                label="locator",
            )
            locator, document = _authenticate_completed_candidate(
                locator_body=payload,
                candidate_fd=candidate_fd,
                pages_fd=pages_fd,
                manifest_fd=manifest_fd,
                receipt_fd=receipt_fd,
                lineage_fd=lineage_fd,
                generation=generation,
                pending=pending_summary,
                code_identity=code_start,
                conn=conn,
                pins=pins,
                hooks=hooks,
                attempt_hi=int(generation["watermarks"]["attempt_hi"]),
                index=listing_index,
                content_fd=content_fd,
            )
            authenticated_tree = _completed_tree_identity(
                locator=locator,
                candidate_fd=candidate_fd,
                pages_fd=pages_fd,
                manifest_fd=manifest_fd,
                receipt_fd=receipt_fd,
                lineage_fd=lineage_fd,
            )
            if hooks.before_recovery_return is not None:
                hooks.before_recovery_return()
            _rebind_completed_directories(
                store_parent_fd=store_parent_fd,
                store_path=store_path,
                store_fd=store_fd,
                gate2_fd=gate2_fd,
                content_fd=content_fd,
                candidate_fd=candidate_fd,
                tmp_fd=tmp_fd,
                pages_fd=pages_fd,
                manifest_fd=manifest_fd,
                receipt_fd=receipt_fd,
                lineage_fd=lineage_fd,
            )
            code_boundary = {
                "acquisition_cli_sha256": _hash_under_repo(repo_fd, ACQUISITION_CLI_RELATIVE),
                "acquisition_source_sha256": _hash_under_repo(repo_fd, ACQUISITION_SOURCE_RELATIVE),
                "planner_cli_sha256": _hash_under_repo(repo_fd, CLI_RELATIVE),
                "planner_source_sha256": _hash_under_repo(repo_fd, SOURCE_RELATIVE),
            }
            _require(
                code_boundary == code_start,
                "planner or generation-0 code identity changed at the recovery boundary",
            )
            state_boundary = snapshot_sqlite_leaves(gate2_fd, hooks)
            _require(
                state_boundary == before,
                "generation-0 sqlite leaves changed at the recovery boundary",
            )
            current_locator_body = _read_bound_named_regular(
                candidate_fd,
                LOCATOR_NAME,
                ceiling=LOCATOR_CEILING_BYTES,
                label="locator",
            )
            _require(
                current_locator_body == payload,
                "locator changed at the recovery boundary",
            )
            listing_index.execute("DELETE FROM listing_object")
            listing_index.commit()
            locator, document = _authenticate_completed_candidate(
                locator_body=current_locator_body,
                candidate_fd=candidate_fd,
                pages_fd=pages_fd,
                manifest_fd=manifest_fd,
                receipt_fd=receipt_fd,
                lineage_fd=lineage_fd,
                generation=generation,
                pending=pending_summary,
                code_identity=code_start,
                conn=conn,
                pins=pins,
                hooks=hooks,
                attempt_hi=int(generation["watermarks"]["attempt_hi"]),
                index=listing_index,
                content_fd=content_fd,
            )
            current_tree = _completed_tree_identity(
                locator=locator,
                candidate_fd=candidate_fd,
                pages_fd=pages_fd,
                manifest_fd=manifest_fd,
                receipt_fd=receipt_fd,
                lineage_fd=lineage_fd,
            )
            _require(
                current_tree == authenticated_tree,
                "a completed candidate name changed at the recovery boundary",
                unsafe=True,
            )
            _rebind_completed_directories(
                store_parent_fd=store_parent_fd,
                store_path=store_path,
                store_fd=store_fd,
                gate2_fd=gate2_fd,
                content_fd=content_fd,
                candidate_fd=candidate_fd,
                tmp_fd=tmp_fd,
                pages_fd=pages_fd,
                manifest_fd=manifest_fd,
                receipt_fd=receipt_fd,
                lineage_fd=lineage_fd,
            )
            code_final = {
                "acquisition_cli_sha256": _hash_under_repo(repo_fd, ACQUISITION_CLI_RELATIVE),
                "acquisition_source_sha256": _hash_under_repo(repo_fd, ACQUISITION_SOURCE_RELATIVE),
                "planner_cli_sha256": _hash_under_repo(repo_fd, CLI_RELATIVE),
                "planner_source_sha256": _hash_under_repo(repo_fd, SOURCE_RELATIVE),
            }
            _require(
                code_final == code_start,
                "planner or generation-0 code identity changed during final recovery authentication",
            )
            state_final = snapshot_sqlite_leaves(gate2_fd, hooks)
            _require(
                state_final == before,
                "generation-0 sqlite leaves changed during final recovery authentication",
            )
            return {
                "checkpoint_path": str(paths.candidate_root / CHECKPOINT_NAME),
                "exit_code": EXIT_COMPLETE,
                "locator_path": str(paths.candidate_root / LOCATOR_NAME),
                "manifest_path": str(paths.candidate_root / MANIFEST_NAME / locator["manifest_name"]),
                "message": AUTHORIZATION["statement"],
                "receipt": document,
                "receipt_path": str(
                    paths.candidate_root / RECEIPT_NAME / str(locator["receipt_name"])
                ),
                "semantic_sha256": document.get("semantic_sha256"),
                "stop_reason": "complete",
            }
        checkpoint = _load_checkpoint(candidate_fd, pages_fd)
        if checkpoint is None:
            checkpoint = _empty_checkpoint(generation, pending_summary, code_start)
        else:
            _authenticate_checkpoint(
                checkpoint,
                generation=generation,
                pending=pending_summary,
                code=code_start,
                pages_fd=pages_fd,
            )
        resolved = transport or UrllibListingTransport()
        _complete_listings(
            candidate_fd=candidate_fd,
            pages_fd=pages_fd,
            tmp_fd=tmp_fd,
            transport=resolved,
            hooks=hooks,
            checkpoint=checkpoint,
            index=listing_index,
        )
        stable_listing = _compare_listing_passes(
            conn,
            pins,
            hooks,
            attempt_hi=int(generation["watermarks"]["attempt_hi"]),
            checkpoint=checkpoint,
            index=listing_index,
        )
        private_manifest = ".partial-manifest.json.gz"
        _write_private_gzip(
            tmp_fd,
            private_manifest,
            _iter_manifest_lines(
                conn,
                pins,
                hooks,
                attempt_hi=int(generation["watermarks"]["attempt_hi"]),
                content_fd=content_fd,
                pinned_destination=str(generation["authority_destination"]),
                index=listing_index,
                checkpoint=checkpoint,
            ),
        )
        if hooks.interrupt_after_private_manifest is not None:
            hooks.interrupt_after_private_manifest()
            raise ListingInterrupted("publication interrupted after private manifest")
        manifest_file = open_child_file(tmp_fd, private_manifest)
        try:
            manifest_sha, manifest_bytes = hash_fd(manifest_file)
            uncompressed = hashlib.sha256()
            semantic_rows = hashlib.sha256()
            row_count = 0
            old_total = 0
            current_total = 0
            metrics_old = 0
            metrics_current = 0
            book_old = 0
            book_current = 0
            max_object = 0
            class_counts = {CLASS_PROVIDER_REVISION: 0, CLASS_ZIP_WORK: 0}
            message_counts: dict[str, int] = {}
            for raw_line in _iter_bounded_manifest_lines(manifest_file):
                uncompressed.update(raw_line)
                try:
                    row = json.loads(raw_line)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise BlockedCandidateError(
                        "private manifest contains invalid JSON"
                    ) from exc
                record = row["record"]
                semantic_rows.update(compact_json(_semantic_manifest_row(row)))
                row_count += 1
                old_total += int(record["old_listed_bytes"])
                current_total += int(record["current_listed_bytes"])
                max_object = max(max_object, int(record["current_listed_bytes"]))
                class_counts[str(record["classification"])] += 1
                message_counts[str(record["terminal_message"])] = (
                    message_counts.get(str(record["terminal_message"]), 0) + 1
                )
                if record["family"] == FAMILY_METRICS:
                    metrics_old += int(record["old_listed_bytes"])
                    metrics_current += int(record["current_listed_bytes"])
                else:
                    book_old += int(record["old_listed_bytes"])
                    book_current += int(record["current_listed_bytes"])
        finally:
            os.close(manifest_file)
        expected_rows = pins.expected_pending_metrics + pins.expected_pending_book_ticker
        _require(row_count == expected_rows, "manifest row count changed")
        lineage = _lineage_document(checkpoint)
        lineage_body = canonical_json(lineage)
        _require(
            len(lineage_body) <= LINEAGE_CEILING_BYTES,
            "lineage exceeds the accepted byte ceiling",
        )
        lineage_sha256 = sha256_bytes(lineage_body)
        lineage_name = f"{lineage_sha256}.json"
        manifest_name = f"{manifest_sha}.json.gz"
        pass_page_counts = {
            pass_id: len(lineage["passes"][pass_id]["pages"]) for pass_id in PASS_IDS
        }
        if hooks.available_bytes is not None:
            available = hooks.available_bytes(candidate_fd)
        else:
            available = int(os.fstatvfs(candidate_fd).f_bavail * os.fstatvfs(candidate_fd).f_frsize)
        reserve = operating_reserve_bytes(available)
        measurement = {
            "acquisition_authorized": False,
            "available_bytes": available,
            "candidate_accepted": False,
            "measurement_only": True,
            "needed_bytes": current_total + reserve,
            "operating_reserve_bytes": reserve,
            "pending_current_listed_bytes": current_total,
            "remainder_bytes": available - current_total - reserve,
            "statement": CAPACITY_STATEMENT,
        }
        code_end = {
            "acquisition_cli_sha256": _hash_under_repo(repo_fd, ACQUISITION_CLI_RELATIVE),
            "acquisition_source_sha256": _hash_under_repo(repo_fd, ACQUISITION_SOURCE_RELATIVE),
            "planner_cli_sha256": _hash_under_repo(repo_fd, CLI_RELATIVE),
            "planner_source_sha256": _hash_under_repo(repo_fd, SOURCE_RELATIVE),
        }
        _require(code_end == code_start, "planner or generation-0 code identity changed during the run")
        receipt = {
            "adr": ADR_ID,
            "authorization": dict(AUTHORIZATION),
            "bytes": {
                "book_ticker_current_bytes": book_current,
                "book_ticker_delta_bytes": book_current - book_old,
                "book_ticker_old_bytes": book_old,
                "current_listed_bytes": current_total,
                "delta_bytes": current_total - old_total,
                "equation": BYTE_EQUATION,
                "metrics_current_bytes": metrics_current,
                "metrics_delta_bytes": metrics_current - metrics_old,
                "metrics_old_bytes": metrics_old,
                "old_planned_bytes": old_total,
            },
            "classification": {
                "book_ticker_zip_work": pending_summary["book_ticker_zip_work"],
                "message_counts": dict(sorted(message_counts.items())),
                "metrics_revision": pending_summary["metrics_revision"],
                "provider_revision_rows": class_counts[CLASS_PROVIDER_REVISION],
                "zip_work_rows": class_counts[CLASS_ZIP_WORK],
            },
            "code_identity": code_end,
            "generation_0": generation,
            "lineage": {
                "asset_bytes": len(lineage_body),
                "asset_name": lineage_name,
                "asset_sha256": lineage_sha256,
                "pass_page_counts": pass_page_counts,
                "schema_version": LINEAGE_SCHEMA,
                "stable_graph_sha256": stable_listing["graph_sha256"],
                "stable_pending_fact_count": stable_listing["pending_fact_count"],
                "stable_pending_facts_sha256": stable_listing["pending_facts_sha256"],
            },
            "listing": {
                "current_maximum_object_bytes": max_object,
                "family_prefixes": list(FAMILY_PREFIXES),
                "independent_passes": list(PASS_IDS),
                "page_count": sum(pass_page_counts.values()),
                "pass_page_counts": pass_page_counts,
                "stable_graph_sha256": stable_listing["graph_sha256"],
                "stable_pending_facts_sha256": stable_listing["pending_facts_sha256"],
            },
            "manifest": {
                "compressed_bytes": manifest_bytes,
                "compressed_sha256": manifest_sha,
                "format": MANIFEST_FORMAT,
                "name": manifest_name,
                "row_count": row_count,
                "semantic_rows_sha256": semantic_rows.hexdigest(),
                "uncompressed_sha256": uncompressed.hexdigest(),
            },
            "pending": pending_summary,
            "policy_identity": POLICY_IDENTITY,
            "schema_version": CANDIDATE_SCHEMA,
            "ticket": TICKET_ID,
            "zip_work_policy": {
                "absolute_ceiling_bytes": ZIP_ABSOLUTE_CEILING_BYTES,
                "equation": ZIP_POLICY_EQUATION,
                "floor_bytes": ZIP_FLOOR_BYTES,
                "ratio": ZIP_RATIO,
            },
        }
        semantic_sha256 = sha256_bytes(canonical_json(_semantic_receipt_payload(receipt)))
        envelope = {
            **receipt,
            "capacity_projection": measurement,
            "semantic_sha256": semantic_sha256,
        }
        manifest_body_fd = open_child_file(tmp_fd, private_manifest)
        try:
            rehash, size = hash_fd(manifest_body_fd)
            _require(rehash == manifest_sha and size == manifest_bytes, "private manifest changed before commit")
            manifest_pub = _publish_fd_named(
                manifest_fd,
                tmp_fd,
                manifest_body_fd,
                digest=manifest_sha,
                size=manifest_bytes,
                suffix=".json.gz",
            )
        finally:
            os.close(manifest_body_fd)
        if hooks.interrupt_after_manifest_publish is not None:
            hooks.interrupt_after_manifest_publish()
            raise ListingInterrupted("publication interrupted after manifest publication")
        lineage_pub = _publish_named(lineage_fd, tmp_fd, lineage_body, suffix=".json")
        if hooks.interrupt_after_lineage_publish is not None:
            hooks.interrupt_after_lineage_publish()
            raise ListingInterrupted("publication interrupted after lineage publication")
        receipt_body = canonical_json(envelope)
        receipt_pub = _publish_named(receipt_fd, tmp_fd, receipt_body, suffix=".json")
        if hooks.interrupt_after_receipt_publish is not None:
            hooks.interrupt_after_receipt_publish()
            raise ListingInterrupted("publication interrupted after receipt publication")
        _require(manifest_pub["name"] == manifest_name, "published manifest name changed")
        _require(lineage_pub["name"] == lineage_name, "published lineage name changed")
        locator = {
            "code_identity": code_end,
            "generation_plan_identity": generation["plan_identity"],
            "generation_state_sha256": before["state"]["sha256"],
            "lineage_name": lineage_pub["name"],
            "lineage_sha256": lineage_pub["sha256"],
            "manifest_name": manifest_pub["name"],
            "manifest_sha256": manifest_pub["sha256"],
            "pending_identity_sha256": pending_summary["identity_sha256"],
            "receipt_name": receipt_pub["name"],
            "receipt_sha256": receipt_pub["sha256"],
            "schema_version": LOCATOR_SCHEMA,
            "semantic_sha256": semantic_sha256,
        }
        locator_body = canonical_json(locator)
        tmp_name = f".partial-{LOCATOR_NAME}.{os.urandom(8).hex()}.tmp"
        loc_tmp = os.open(
            tmp_name,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=tmp_fd,
        )
        try:
            written = 0
            view = memoryview(locator_body)
            while written < len(locator_body):
                written += os.write(loc_tmp, view[written:])
            os.fsync(loc_tmp)
        finally:
            os.close(loc_tmp)
        for directory, publication, label in (
            (manifest_fd, manifest_pub, "manifest"),
            (lineage_fd, lineage_pub, "lineage"),
            (receipt_fd, receipt_pub, "receipt"),
        ):
            published_fd = open_child_file(directory, str(publication["name"]))
            try:
                actual, actual_size = hash_fd(published_fd)
            finally:
                os.close(published_fd)
            _require(
                actual == publication["sha256"] and actual_size == publication["bytes"],
                f"published {label} changed before locator commit",
            )
        code_final = {
            "acquisition_cli_sha256": _hash_under_repo(repo_fd, ACQUISITION_CLI_RELATIVE),
            "acquisition_source_sha256": _hash_under_repo(repo_fd, ACQUISITION_SOURCE_RELATIVE),
            "planner_cli_sha256": _hash_under_repo(repo_fd, CLI_RELATIVE),
            "planner_source_sha256": _hash_under_repo(repo_fd, SOURCE_RELATIVE),
        }
        _require(code_final == code_end, "planner or generation-0 code changed before locator commit")
        if hooks.interrupt_before_locator is not None:
            hooks.interrupt_before_locator()
            _rebind_child_dir(store_parent_fd, store_path.name, store_fd, label="store root")
            _rebind_child_dir(store_fd, FIXED_ACTIVE_NAME, gate2_fd, label="generation-0 root")
            _rebind_child_dir(gate2_fd, CONTENT_NAME, content_fd, label="generation-0 content root")
            _rebind_child_dir(store_fd, FIXED_CANDIDATE_NAME, candidate_fd, label="candidate root")
            raise ListingInterrupted("publication interrupted before locator commit")
        if hooks.before_locator_commit is not None:
            hooks.before_locator_commit()
        _rebind_child_dir(store_parent_fd, store_path.name, store_fd, label="store root")
        _rebind_child_dir(store_fd, FIXED_ACTIVE_NAME, gate2_fd, label="generation-0 root")
        _rebind_child_dir(gate2_fd, CONTENT_NAME, content_fd, label="generation-0 content root")
        _rebind_child_dir(store_fd, FIXED_CANDIDATE_NAME, candidate_fd, label="candidate root")
        for child_name, child_fd, label in (
            (TMP_NAME, tmp_fd, "candidate temporary root"),
            (PAGES_NAME, pages_fd, "candidate listing-page root"),
            (MANIFEST_NAME, manifest_fd, "candidate manifest root"),
            (RECEIPT_NAME, receipt_fd, "candidate receipt root"),
            (LINEAGE_NAME, lineage_fd, "candidate lineage root"),
        ):
            _rebind_child_dir(candidate_fd, child_name, child_fd, label=label)
        code_precommit = {
            "acquisition_cli_sha256": _hash_under_repo(repo_fd, ACQUISITION_CLI_RELATIVE),
            "acquisition_source_sha256": _hash_under_repo(repo_fd, ACQUISITION_SOURCE_RELATIVE),
            "planner_cli_sha256": _hash_under_repo(repo_fd, CLI_RELATIVE),
            "planner_source_sha256": _hash_under_repo(repo_fd, SOURCE_RELATIVE),
        }
        _require(
            code_precommit == code_end,
            "planner or generation-0 code changed at the locator boundary",
        )
        state_precommit = snapshot_sqlite_leaves(gate2_fd, hooks)
        _require(
            state_precommit == before,
            "generation-0 sqlite leaves changed at the locator boundary",
        )
        locator_tmp_fd = open_child_file(tmp_fd, tmp_name)
        try:
            locator_tmp_sha256, locator_tmp_bytes = hash_fd(locator_tmp_fd)
        finally:
            os.close(locator_tmp_fd)
        _require(
            locator_tmp_sha256 == sha256_bytes(locator_body)
            and locator_tmp_bytes == len(locator_body),
            "private locator changed at the locator boundary",
        )
        for directory, publication, label in (
            (manifest_fd, manifest_pub, "manifest"),
            (lineage_fd, lineage_pub, "lineage"),
            (receipt_fd, receipt_pub, "receipt"),
        ):
            published_fd = open_child_file(directory, str(publication["name"]))
            try:
                actual, actual_size = hash_fd(published_fd)
            finally:
                os.close(published_fd)
            _require(
                actual == publication["sha256"] and actual_size == publication["bytes"],
                f"published {label} changed at the locator boundary",
            )
        try:
            _renameat2_noreplace(tmp_fd, tmp_name, candidate_fd, LOCATOR_NAME)
        except OSError as exc:
            try:
                os.unlink(tmp_name, dir_fd=tmp_fd)
            except FileNotFoundError:
                pass
            if exc.errno == errno.EEXIST:
                winner = open_child_file(candidate_fd, LOCATOR_NAME)
                try:
                    actual, _sz = hash_fd(winner)
                finally:
                    os.close(winner)
                _require(actual == sha256_bytes(locator_body), "collision winner locator does not match")
            else:
                raise UnsafeCandidateError("no-replace locator commit failed") from exc
        os.fsync(candidate_fd)
        after = snapshot_sqlite_leaves(gate2_fd, hooks)
        _require(after == before, "generation-0 sqlite leaves changed")
        try:
            os.unlink(private_manifest, dir_fd=tmp_fd)
        except FileNotFoundError:
            pass
        return {
            "checkpoint_path": str(paths.candidate_root / CHECKPOINT_NAME),
            "exit_code": EXIT_COMPLETE,
            "locator_path": str(paths.candidate_root / LOCATOR_NAME),
            "manifest_path": str(paths.candidate_root / MANIFEST_NAME / manifest_pub["name"]),
            "message": AUTHORIZATION["statement"],
            "receipt": envelope,
            "receipt_path": str(paths.candidate_root / RECEIPT_NAME / receipt_pub["name"]),
            "semantic_sha256": semantic_sha256,
            "stop_reason": "complete",
        }
    finally:
        if listing_index is not None:
            try:
                listing_index.close()
            except sqlite3.Error:
                pass
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        held.close_all()


SCHEMA_SQL = """
CREATE TABLE authority (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    plan_identity TEXT NOT NULL UNIQUE,
    plan_receipt_sha256 TEXT NOT NULL,
    pins_json TEXT NOT NULL,
    code_json TEXT NOT NULL,
    destination TEXT NOT NULL,
    device TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE plan_entry (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE(provider, identity)
);
CREATE TABLE attempt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    class TEXT NOT NULL,
    status_code INTEGER,
    redacted_fact_json TEXT NOT NULL,
    FOREIGN KEY (provider, identity) REFERENCES plan_entry(provider, identity)
);
CREATE TABLE sidecar_fact (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    sidecar_sha256 TEXT NOT NULL,
    sidecar_path TEXT NOT NULL,
    sidecar_bytes INTEGER NOT NULL,
    provider_checksum TEXT NOT NULL,
    UNIQUE(provider, identity),
    FOREIGN KEY (provider, identity) REFERENCES plan_entry(provider, identity)
);
CREATE TABLE completion (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    content_path TEXT NOT NULL,
    sidecar_sha256 TEXT,
    sidecar_path TEXT,
    listed_bytes INTEGER NOT NULL,
    retrieved_at TEXT NOT NULL,
    revision_json TEXT NOT NULL,
    validation_state TEXT NOT NULL,
    UNIQUE(provider, identity),
    FOREIGN KEY (provider, identity) REFERENCES plan_entry(provider, identity)
);
CREATE TABLE terminal_gap (
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    kind TEXT NOT NULL,
    fact_json TEXT NOT NULL,
    PRIMARY KEY (provider, identity),
    FOREIGN KEY (provider, identity) REFERENCES plan_entry(provider, identity)
);
CREATE TABLE coinalyze_ledger (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    charged INTEGER NOT NULL CHECK (charged >= 0)
);
CREATE TABLE coinalyze_charge (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK (generation >= 1),
    content_sha256 TEXT NOT NULL,
    charged_bytes INTEGER NOT NULL CHECK (charged_bytes >= 0),
    http_status INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    points INTEGER NOT NULL,
    request_proof TEXT NOT NULL,
    retrieval_json TEXT NOT NULL,
    revision_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(provider, identity, generation),
    FOREIGN KEY (provider, identity) REFERENCES plan_entry(provider, identity)
);
CREATE TABLE charge_transition (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK (generation >= 1),
    status TEXT NOT NULL,
    at TEXT NOT NULL,
    FOREIGN KEY (provider, identity) REFERENCES plan_entry(provider, identity)
);
CREATE TABLE run_metadata (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    stop_reason TEXT,
    attempt_hi INTEGER NOT NULL,
    network_calls INTEGER NOT NULL,
    start_snapshot_json TEXT NOT NULL,
    error_count INTEGER NOT NULL,
    network_sample_json TEXT NOT NULL,
    pre_capacity_json TEXT NOT NULL,
    post_capacity_json TEXT NOT NULL,
    capacity_blocked INTEGER NOT NULL CHECK (capacity_blocked IN (0, 1)),
    attempt_delta INTEGER NOT NULL,
    completion_delta INTEGER NOT NULL,
    gap_delta INTEGER NOT NULL,
    byte_delta INTEGER NOT NULL,
    open_coinalyze_charges INTEGER NOT NULL,
    counts_json TEXT NOT NULL
);
CREATE TABLE run_publication (
    run_id TEXT PRIMARY KEY,
    receipt_sha256 TEXT NOT NULL,
    receipt_directory TEXT NOT NULL,
    receipt_body TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_metadata(run_id)
);
CREATE TABLE run_seal (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    receipt_sha256 TEXT NOT NULL,
    predecessor_sha256 TEXT NOT NULL,
    prefix_digest TEXT NOT NULL,
    marks_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_metadata(run_id)
);
CREATE TABLE seal_head (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    receipt_sha256 TEXT NOT NULL,
    receipt_path TEXT NOT NULL,
    prefix_digest TEXT NOT NULL,
    attempt_hi INTEGER NOT NULL,
    completion_hi INTEGER NOT NULL,
    sidecar_hi INTEGER NOT NULL,
    charge_hi INTEGER NOT NULL,
    transition_hi INTEGER NOT NULL,
    run_hi INTEGER NOT NULL,
    seal_hi INTEGER NOT NULL,
    predecessor_sha256 TEXT
);
CREATE INDEX idx_attempt_identity ON attempt(provider, identity);
CREATE INDEX idx_completion_content ON completion(content_sha256);
CREATE INDEX idx_completion_state ON completion(validation_state);
CREATE INDEX idx_plan_kind ON plan_entry(kind);
CREATE INDEX idx_transition_identity ON charge_transition(provider, identity, generation);
CREATE INDEX idx_charge_identity ON coinalyze_charge(provider, identity, generation);
CREATE INDEX idx_run_seal_receipt ON run_seal(receipt_sha256);
"""
