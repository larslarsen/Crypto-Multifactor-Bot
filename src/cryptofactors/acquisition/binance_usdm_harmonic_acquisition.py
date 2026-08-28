"""CEX-002 Gate 2 — content-addressed acquisition and deterministic resume.

Implements ADR-0029 as corrected by reviews 287, 288, and 289, and ADR-0030
exact retained credit: a hash-bound immutable plan, descriptor-bound no-follow
sharded publication, an exactly authenticated fail-closed SQLite state, a
crash-recoverable Coinalyze budget/publication/completion transition, one
coordinator that owns every database write and terminal transition, one shared
streaming provider-semantic validator used by resume and offline verification,
a prospective capacity guard at every transfer boundary, storage-neutral
retained adoption from receipt 258's exact key set, and exact terminal
reconciliation. Planning and verification perform no network call and no
production path holds a universe-proportional Python collection.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import gzip
import hashlib
import json
import os
import queue
import re
import signal
import sqlite3
import stat
import threading
import time
import zipfile
import zlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlencode, urlsplit

from cryptofactors.acquisition.binance_usdm_capacity_attestation import (
    EXPECTED_STABLE_REQUIREMENT_BYTES,
    MINIMUM_OPERATING_RESERVE_BYTES,
    STABLE_COMPONENTS,
    operating_reserve_bytes,
)
from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    COINALYZE_BASE,
    COINALYZE_EXCHANGE_CODE,
    COINALYZE_INTERVAL_DAILY,
    MANIFEST_DETAIL_FORMAT,
    MANIFEST_DETAIL_SCHEMA_VERSION,
    coinalyze_perp_symbol,
    cost_manifest_digest,
    parse_s3_list_bucket,
)

TICKET_ID = "CEX-002"
POLICY_IDENTITY = (
    "adr0029_content_addressed_gate2_acquisition_and_resume_"
    "adr0030_exact_retained_credit_v2"
)
PLAN_SCHEMA = "cex002_gate2_plan_receipt_v2"
SIZING_RECEIPT_SCHEMA = "cex002_gate2_storage_sizing_v3"
RECEIPT_258_RETAINED_CREDIT_KEYS: frozenset[str] = frozenset(
    {
        "bytes",
        "cost_retained_keys",
        "key_set_sha256",
        "keys",
        "objects",
        "rejected_recovered_rows",
        "report_summary",
        "selected_retained_keys",
        "source",
        "unverified_objects",
        "valid_requirement_keys",
    }
)
RECEIPT_258_REPORT_SUMMARY_KEYS: frozenset[str] = frozenset(
    {
        "rejected_retained_row_count",
        "retained_valid_requirement_keys",
        "retained_verified_credit_bytes",
        "retained_verified_credit_objects",
        "unverified_retained_objects",
    }
)
RETAINED_CREDIT_SOURCE = (
    "effective checkpoint rows inside the complete selected-plus-cost "
    "requirement, path-bound, rehashed, and deduplicated by content digest"
)
RUN_SCHEMA = "cex002_gate2_run_receipt_v1"
TERMINAL_SCHEMA = "cex002_gate2_terminal_receipt_v1"
STATE_SCHEMA = "cex002_gate2_acquisition_state_v1"
STATE_USER_VERSION = 7
STATE_APPLICATION_ID = 0x43324732
COST_SELECTOR = "first_midpoint_last_daily_book_v1"
COST_FAMILIES: tuple[str, ...] = ("daily/bookTicker", "daily/bookDepth")
ARCHIVE_FAMILIES: tuple[str, ...] = (
    "daily/klines",
    "daily/metrics",
    "daily/premiumIndexKlines",
    "daily/markPriceKlines",
    "daily/indexPriceKlines",
    "monthly/klines",
    "monthly/fundingRate",
    "monthly/premiumIndexKlines",
    "monthly/markPriceKlines",
    "monthly/indexPriceKlines",
)
PHYSICAL_FAMILIES: tuple[str, ...] = ARCHIVE_FAMILIES + COST_FAMILIES
FORBIDDEN_FAMILIES: frozenset[str] = frozenset(
    {
        "monthly/trades",
        "daily/trades",
        "monthly/aggTrades",
        "daily/aggTrades",
        "monthly/bookTicker",
        "monthly/bookDepth",
        "daily/fundingRate",
    }
)
VISION_OBJECT_BASE = "https://data.binance.vision"
COINALYZE_LIQUIDATION_PATH = "/liquidation-history"
COINALYZE_MARKETS_PATH = "/future-markets"
COINALYZE_RATE_PER_MINUTE = 40
COINALYZE_MAX_SYMBOLS_PER_REQUEST = 1
WORKER_CEILING = 8
QUEUE_CEILING = 16
MAX_TRANSIENT_ATTEMPTS = 5
MAX_RETRY_AFTER_SECONDS = 60
BACKOFF_SECONDS: tuple[int, ...] = (1, 2, 4, 8, 16)
CHUNK_SIZE = 64 * 1024
SIDECAR_CEILING_BYTES = 4096
MAX_JSON_TOKEN_BYTES = 4096
MAX_JSON_DEPTH = 32
MAX_DECIMAL_ABS_EXPONENT = 12
MAX_DECIMAL_DIGITS = 24
ZIP_MEMBER_CEILING = 256
ZIP_UNCOMPRESSED_CEILING = 64 * 1024 * 1024
ZIP_SYMLINK_MODE = 0o120000
NETWORK_SAMPLE_CEILING = 8
ERROR_SAMPLE_CEILING = 8
RESULT_QUEUE_CEILING = 64
MAX_CHARGE_TRANSITIONS = 8
MAX_DIAGNOSTIC_BYTES = 256
RENAME_NOREPLACE = 1
CURSOR_BATCH = 256
PROVIDER_BINANCE = "binance_vision"
PROVIDER_COINALYZE = "coinalyze"
KIND_BINANCE = "binance_object"
KIND_COINALYZE_INVENTORY = "coinalyze_inventory"
KIND_COINALYZE_LIQUIDATION = "coinalyze_liquidation"
KIND_COINALYZE_UNSUPPORTED = "coinalyze_unsupported_gap"
OUTCOME_CHECKSUM_VERIFIED = "checksum_verified"
OUTCOME_EMPTY_HISTORY = "empty_history"
OUTCOME_UNAVAILABLE = "provider_unavailable"
OUTCOME_RETAINED_INVENTORY = "retained_inventory"
OUTCOME_RETAINED = "retained_credit"
GAP_UNSUPPORTED = "unsupported_mapping"
RETRY_TRANSIENT = "transient"
RETRY_RATE_LIMIT = "rate_limit"
RETRY_TERMINAL = "terminal"
RETRY_TRANSPORT = "transport"
RETRY_OK = "ok"
CHARGE_RESERVED = "reserved"
CHARGE_PUBLISHED = "published"
CHARGE_SETTLED = "settled"
CHARGE_RELEASED = "released"
CHARGE_RETRIEVAL_KEYS: frozenset[str] = frozenset({"url", "status", "retrieved_at"})
CHARGE_REVISION_KEYS: frozenset[str] = frozenset({"status", "points"})
RUN_RECEIPT_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "ticket",
        "policy_identity",
        "plan_identity",
        "run_id",
        "authority",
        "code_identity",
        "started_at",
        "ended_at",
        "stop_reason",
        "attempt_delta",
        "completion_delta",
        "gap_delta",
        "byte_delta",
        "network_calls",
        "attempts",
        "error_count",
        "network_sample",
        "pre_capacity",
        "post_capacity",
        "capacity_blocked",
        "open_coinalyze_charges",
        "semantic_state_digest",
        "prefix_digest",
        "high_watermarks",
        "predecessor_sha256",
        "counts",
    }
)
COUNTS_KEYS: frozenset[str] = frozenset(
    {"planned", "completed", "attempts", "gaps", "coinalyze_charged"}
)
CAPACITY_FACT_KEYS: frozenset[str] = frozenset(
    {
        "stable_requirement_bytes",
        "operating_reserve_bytes",
        "total_future_storage_bytes",
        "available_bytes",
        "next_transfer_bytes",
        "needed_bytes",
        "storage_preflight_state",
        "reserve_floor_bytes",
        "stable_components",
    }
)
AUTHORITY_RECEIPT_KEYS: frozenset[str] = frozenset(
    {
        "report_62_sha256",
        "manifest_compressed_sha256",
        "manifest_uncompressed_sha256",
        "cost_manifest_sha256",
        "receipt_258_sha256",
        "attestation_282_sha256",
        "listing_checkpoint_sha256",
        "contract_metadata_sha256",
        "lock_sha256",
        "amendment_ledger_sha256",
        "progress_sha256",
        "holdout_boundary_id",
    }
)
WATERMARK_KEYS: tuple[str, ...] = (
    "attempt_hi",
    "completion_hi",
    "sidecar_hi",
    "charge_hi",
    "transition_hi",
    "run_hi",
    "seal_hi",
)
START_SNAPSHOT_KEYS: frozenset[str] = frozenset(WATERMARK_KEYS) | frozenset(
    {"gaps", "listed_bytes"}
)
PLAN_RECEIPT_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "ticket",
        "policy_identity",
        "plan_identity",
        "authority",
        "code_identity",
        "helper_identities",
        "counts",
        "bytes",
        "family_totals",
        "coinalyze",
        "holdout_boundary_id",
        "storage",
        "prohibitions",
        "retained_credit",
    }
)
PLAN_RETAINED_CREDIT_KEYS: frozenset[str] = frozenset(
    {
        "key_set_sha256",
        "valid_requirement_keys",
        "objects",
        "bytes",
        "selected_retained_keys",
        "cost_retained_keys",
        "unverified_objects",
    }
)
CADENCE_RULE = "monthly_preferred_daily_gap_tail_v1"
INTEGRITY_RULE = (
    "a listed provider sidecar is the outcome-blind selection precondition for "
    "both cadences; only a rehashed retained object with a re-proved sidecar is "
    "checksum-proved and consumable, and missing authority stays typed evidence"
)
PROHIBITIONS: tuple[str, ...] = (
    "no trades or aggTrades",
    "no full historical bookTicker or bookDepth",
    "no price-only or tick path",
    "no caller family/symbol/date filter",
    "no progress credit against the ADR-0028 stable requirement",
    "no secret in URL, query, database, receipt, log, or exception",
)

SOURCE_RELATIVE_PATH = Path(
    "src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py"
)
CLI_RELATIVE_PATH = Path("scripts/research/acquire_binance_usdm_harmonic_release.py")
QUALIFICATION_SOURCE_RELATIVE = Path(
    "src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py"
)
QUALIFICATION_CLI_RELATIVE = Path(
    "scripts/research/qualify_binance_usdm_harmonic_sources.py"
)
ATTESTATION_SOURCE_RELATIVE = Path(
    "src/cryptofactors/acquisition/binance_usdm_capacity_attestation.py"
)
ATTESTATION_CLI_RELATIVE = Path(
    "scripts/research/attest_binance_usdm_harmonic_capacity.py"
)
REPORT_RELATIVE = Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json")
RECEIPT_258_RELATIVE = Path("research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json")
ATTESTATION_282_RELATIVE = Path(
    "research/sprint_004/282_CEX002_GATE2_CAPACITY_ATTESTATION.json"
)

EXIT_COMPLETE = 0
EXIT_RESUMABLE_PARTIAL = 2
EXIT_COMPLETE_WITH_TERMINAL_GAPS = 3
EXIT_CAPACITY_BLOCKED = 4
EXIT_AUTHORITY_INVALID = 5
EXIT_UNSAFE_STATE = 6

HEX64 = re.compile(r"^[0-9a-f]{64}$")
SIDECAR_LINE = re.compile(r"^([0-9a-fA-F]{64})[ \t]+(\S+)\s*$", re.MULTILINE)
UTC_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class AcquisitionError(RuntimeError):
    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = dict(context or {})


class AuthorityError(AcquisitionError):
    pass


class CapacityBlocked(AcquisitionError):
    pass


class UnsafeStateError(AcquisitionError):
    pass


class FaultInjected(AcquisitionError):
    pass


@dataclass(frozen=True, slots=True)
class AuthorityPins:
    report_sha256: str
    manifest_compressed_sha256: str
    manifest_uncompressed_sha256: str
    cost_manifest_sha256: str
    receipt_258_sha256: str
    attestation_282_sha256: str
    listing_checkpoint_sha256: str
    contract_metadata_sha256: str
    lock_sha256: str
    amendment_ledger_sha256: str
    progress_sha256: str
    qualification_source_sha256: str
    qualification_cli_sha256: str
    capacity_source_sha256: str
    capacity_cli_sha256: str
    holdout_boundary_id: str
    main_selected_objects: int
    main_selected_bytes: int
    cost_objects: int
    cost_bytes: int
    combined_objects: int
    combined_bytes: int
    retained_credit_objects: int
    retained_credit_bytes: int
    coinalyze_supported: int
    coinalyze_unsupported: int
    coinalyze_logical_receipts: int
    new_binance_raw_bytes: int
    new_coinalyze_raw_bytes: int
    stable_requirement_bytes: int
    destination: str
    device: str
    report_bytes: int | None = None
    manifest_compressed_bytes: int | None = None
    receipt_258_bytes: int | None = None
    attestation_282_bytes: int | None = None


PRODUCTION_PINS = AuthorityPins(
    report_sha256="f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09",
    manifest_compressed_sha256=(
        "64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113"
    ),
    manifest_uncompressed_sha256=(
        "d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17"
    ),
    cost_manifest_sha256=(
        "04842ff6b9b58280b3ec2ea2644b3d44769be62d460bef785262cd4dd65cac57"
    ),
    receipt_258_sha256="3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589",
    attestation_282_sha256=(
        "0e12333d94b7ce2aea373c7f4bac7887a5f72c6a710cb9e697c5ffb660c22b25"
    ),
    listing_checkpoint_sha256=(
        "d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a"
    ),
    contract_metadata_sha256=(
        "7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42"
    ),
    lock_sha256="6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e",
    amendment_ledger_sha256=(
        "2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf"
    ),
    progress_sha256="cc8e02389d182e6d76d00b913503d95f72a352d883c50ffd81dd3c49df157b2f",
    qualification_source_sha256=(
        "2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74"
    ),
    qualification_cli_sha256=(
        "473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f"
    ),
    capacity_source_sha256=(
        "34973e6f801ef3a16e82c3333c01fb1ee81fad357810bc28fdd5eaabf18995ec"
    ),
    capacity_cli_sha256=(
        "e5195b967d83f3f1ab336f342c512ce375e80dbc66f67cb754acc2b86244ead5"
    ),
    holdout_boundary_id="c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2",
    main_selected_objects=733_203,
    main_selected_bytes=7_833_966_625,
    cost_objects=3_144,
    cost_bytes=12_522_974_218,
    combined_objects=736_347,
    combined_bytes=20_356_940_843,
    retained_credit_objects=73,
    retained_credit_bytes=5_225_416,
    coinalyze_supported=569,
    coinalyze_unsupported=202,
    coinalyze_logical_receipts=570,
    new_binance_raw_bytes=20_351_715_427,
    new_coinalyze_raw_bytes=30_580_702,
    stable_requirement_bytes=139_577_980_018,
    destination="data/cex002_qualify",
    device="dev:64513",
    report_bytes=13_745_360,
    manifest_compressed_bytes=11_292_635,
    receipt_258_bytes=39_727_059,
    attestation_282_bytes=3_794,
)
PRODUCTION_RETAINED_SELECTED_KEYS = 68
PRODUCTION_RETAINED_COST_KEYS = 5
PRODUCTION_RETAINED_UNVERIFIED_OBJECTS = 0
PRODUCTION_RETAINED_REJECTED_ROWS = 176


@dataclass(frozen=True, slots=True)
class RetainedCredit:
    keys: tuple[str, ...]
    key_set: frozenset[str]
    key_set_sha256: str
    valid_requirement_keys: int
    objects: int
    unique_bytes: int
    selected_retained_keys: int
    cost_retained_keys: int
    unverified_objects: int


@dataclass(frozen=True, slots=True)
class AcquisitionPaths:
    repository: Path
    store_root: Path
    report_path: Path
    receipt_258_path: Path
    attestation_path: Path
    lock_path: Path
    amendment_ledger_path: Path
    progress_path: Path
    listing_checkpoint_path: Path
    contract_metadata_path: Path
    listing_cache_dir: Path
    coinalyze_cache_dir: Path
    holdout_path: Path
    qualification_source_path: Path
    qualification_cli_path: Path
    attestation_source_path: Path
    attestation_cli_path: Path
    sample_dir: Path
    gate2_root: Path
    content_root: Path
    state_path: Path
    plan_receipt_dir: Path
    run_receipt_dir: Path
    terminal_dir: Path
    lockfile_path: Path
    tmp_root: Path


def default_paths(repository: Path, store_root: Path) -> AcquisitionPaths:
    store = Path(store_root)
    gate2 = store / "gate2"
    return AcquisitionPaths(
        repository=Path(repository),
        store_root=store,
        report_path=Path(repository) / REPORT_RELATIVE,
        receipt_258_path=Path(repository) / RECEIPT_258_RELATIVE,
        attestation_path=Path(repository) / ATTESTATION_282_RELATIVE,
        lock_path=store / "cex002_sample_plan_lock.json",
        amendment_ledger_path=store / "cex002_amendment_ledger.json",
        progress_path=store / "cex002_qualification_progress.json",
        listing_checkpoint_path=store / "cex002_listing_checkpoint.json",
        contract_metadata_path=store / "cex002_official_contract_metadata.json",
        listing_cache_dir=store / "list_cache",
        coinalyze_cache_dir=store / "coinalyze_cache",
        holdout_path=store / "cex002_holdout_boundary.json",
        qualification_source_path=Path(repository) / QUALIFICATION_SOURCE_RELATIVE,
        qualification_cli_path=Path(repository) / QUALIFICATION_CLI_RELATIVE,
        attestation_source_path=Path(repository) / ATTESTATION_SOURCE_RELATIVE,
        attestation_cli_path=Path(repository) / ATTESTATION_CLI_RELATIVE,
        sample_dir=store / "raw" / "sha256",
        gate2_root=gate2,
        content_root=gate2 / "content",
        state_path=gate2 / "state.sqlite",
        plan_receipt_dir=gate2 / "plan_receipts",
        run_receipt_dir=gate2 / "run_receipts",
        terminal_dir=gate2 / "terminal",
        lockfile_path=gate2 / "acquisition.lock",
        tmp_root=gate2 / "tmp",
    )



class StreamResponse:
    def __init__(
        self,
        status_code: int,
        headers: Mapping[str, str],
        iter_bytes: Iterator[bytes],
        close: Callable[[], None] | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = {str(key): str(value) for key, value in dict(headers).items()}
        self.iter_bytes = iter_bytes
        self._close = close or (lambda: None)
        self._closed = False

    def close_response(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._close()


class StreamTransport(Protocol):
    def stream_get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        timeout: float,
    ) -> StreamResponse: ...

    def close(self) -> None: ...


class Filesystem(Protocol):
    def device_of(self, path: Path) -> str: ...

    def available_bytes(self, path: Path) -> int: ...


class RealFilesystem:
    def __init__(self, store_fd: int | None = None) -> None:
        self._store_fd = store_fd

    def device_of(self, path: Path) -> str:
        if self._store_fd is not None:
            return f"dev:{os.fstat(self._store_fd).st_dev}"
        fd = open_root_dir(path if Path(path).is_dir() else path.parent, create=False)
        try:
            return f"dev:{os.fstat(fd).st_dev}"
        finally:
            os.close(fd)

    def available_bytes(self, path: Path) -> int:
        if self._store_fd is not None:
            result = os.fstatvfs(self._store_fd)
            return int(result.f_bavail) * int(result.f_frsize)
        fd = open_root_dir(path if Path(path).is_dir() else path.parent, create=False)
        try:
            result = os.fstatvfs(fd)
            return int(result.f_bavail) * int(result.f_frsize)
        finally:
            os.close(fd)


class HttpxStreamTransport:
    """One pooled streaming client for a bounded invocation."""

    def __init__(self) -> None:
        import httpx

        self._httpx = httpx
        self._client = httpx.Client(
            timeout=60.0,
            follow_redirects=False,
            limits=httpx.Limits(
                max_connections=WORKER_CEILING,
                max_keepalive_connections=WORKER_CEILING,
            ),
        )

    def stream_get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        timeout: float,
    ) -> StreamResponse:
        request = self._client.build_request(
            "GET", url, headers=dict(headers or {}), timeout=timeout
        )
        response = self._client.send(request, stream=True)

        def _chunks() -> Iterator[bytes]:
            try:
                yield from response.iter_bytes()
            finally:
                response.close()

        def _close() -> None:
            response.close()

        return StreamResponse(
            response.status_code,
            {key: value for key, value in response.headers.items()},
            _chunks(),
            _close,
        )

    def close(self) -> None:
        self._client.close()


class FaultInjector:
    def check(self, point: str, identity: str = "") -> None:
        return None


class NamedFault(FaultInjector):
    def __init__(self, point: str, identity: str | None = None) -> None:
        self.point = point
        self.identity = identity

    def check(self, point: str, identity: str = "") -> None:
        if point == self.point and (self.identity is None or identity == self.identity):
            raise FaultInjected(f"fault at {point}", context={"identity": identity})


@dataclass
class BoundTelemetry:
    """Deterministic production-path maxima; never a universe-sized collection."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    max_cursor_rows: int = 0
    max_queue_depth: int = 0
    max_work_depth: int = 0
    max_sample_len: int = 0
    max_token_bytes: int = 0
    max_batch_rows: int = 0
    max_recover_rows: int = 0

    def note(self, field: str, value: int) -> None:
        with self.lock:
            current = int(getattr(self, field))
            if int(value) > current:
                setattr(self, field, int(value))

    def snapshot(self) -> dict[str, int]:
        with self.lock:
            return {
                "max_cursor_rows": self.max_cursor_rows,
                "max_queue_depth": self.max_queue_depth,
                "max_work_depth": self.max_work_depth,
                "max_sample_len": self.max_sample_len,
                "max_token_bytes": self.max_token_bytes,
                "max_batch_rows": self.max_batch_rows,
                "max_recover_rows": self.max_recover_rows,
            }

    def reset(self) -> None:
        with self.lock:
            self.max_cursor_rows = 0
            self.max_queue_depth = 0
            self.max_work_depth = 0
            self.max_sample_len = 0
            self.max_token_bytes = 0
            self.max_batch_rows = 0
            self.max_recover_rows = 0


BOUND_TELEMETRY = BoundTelemetry()


@dataclass
class RateLimiter:
    max_calls: int = COINALYZE_RATE_PER_MINUTE
    period_s: float = 60.0
    sleeper: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    calls: int = 0
    _times: list[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = self.clock()
                self._times = [item for item in self._times if now - item < self.period_s]
                if len(self._times) < self.max_calls:
                    self._times.append(now)
                    self.calls += 1
                    return
                wait_for = self.period_s - (now - self._times[0])
            if wait_for > 0:
                self.sleeper(wait_for)


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


def requirement_key_set_sha256(keys: Sequence[str]) -> str:
    """SHA-256 of canonical JSON ``{"requirement_keys": sorted_keys}``."""

    return sha256_bytes(
        canonical_json({"requirement_keys": sorted(str(key) for key in keys)})
    )


def _exact_int(value: Any, *, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise UnsafeStateError(f"{label} is not an exact integer")
    if value < minimum:
        raise UnsafeStateError(f"{label} is below its bound")
    return value


def _exact_bool(value: Any, *, label: str) -> bool:
    if value is not True and value is not False:
        raise UnsafeStateError(f"{label} is not an exact boolean")
    return value


def _exact_str(value: Any, *, label: str) -> str:
    if type(value) is not str:
        raise UnsafeStateError(f"{label} is not an exact string")
    return value


def _exact_str_list(value: Any, *, label: str, ceiling: int) -> list[str]:
    if type(value) is not list:
        raise UnsafeStateError(f"{label} is not an exact list")
    if len(value) > ceiling:
        raise UnsafeStateError(f"{label} exceeds its sample ceiling")
    items: list[str] = []
    for item in value:
        if type(item) is not str:
            raise UnsafeStateError(f"{label} contains a non-string sample")
        items.append(item)
    return items


def _exact_object(value: Any, *, label: str, keys: frozenset[str]) -> dict[str, Any]:
    if type(value) is not dict:
        raise UnsafeStateError(f"{label} is not an exact object")
    observed = frozenset(value)
    extra = sorted(observed - keys)
    missing = sorted(keys - observed)
    if extra or missing:
        raise UnsafeStateError(
            f"{label} has extra or missing fields",
            context={"extra": extra, "missing": missing},
        )
    return value


# --------------------------------------------------------------------------------------
# Descriptor-bound, no-follow filesystem primitives.
#
# Every authority, state, temporary, content, sidecar, hard-link, and receipt path is
# reached by walking its parent chain one component at a time with O_NOFOLLOW, so an
# intermediate shard or parent symlink cannot escape the accepted root, and the checked
# identity stays bound to the descriptor that is actually read or written.
# --------------------------------------------------------------------------------------


def _relative_parts(root: Path, path: Path) -> tuple[str, ...]:
    root_s = os.path.abspath(str(root))
    path_s = os.path.abspath(str(path))
    if path_s == root_s:
        return ()
    try:
        relative = Path(os.path.relpath(path_s, root_s))
    except ValueError as exc:  # pragma: no cover - different drives are impossible here
        raise UnsafeStateError("path is not inside the accepted root") from exc
    parts = relative.parts
    if not parts or parts[0] in {"..", os.sep} or any(part == ".." for part in parts):
        raise UnsafeStateError(
            "path escapes the accepted root", context={"path": str(path)}
        )
    return tuple(part for part in parts if part != ".")


def open_root_dir(root: Path, *, create: bool = False) -> int:
    """Open ``root`` by walking every absolute component with ``O_NOFOLLOW``.

    Parents are never created by pathname and then opened as a leaf. Each missing
    component is mkdir'd from its already-opened parent descriptor and then opened
    from that same descriptor, so an ancestor symlink cannot redirect the root.
    """

    absolute = Path(root).absolute()
    parts = absolute.parts
    if not parts or parts[0] != os.sep:
        raise UnsafeStateError(
            "the accepted root is not an absolute directory", context={"root": str(root)}
        )
    try:
        current = os.open(os.sep, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise UnsafeStateError(
            "the accepted root is not a no-follow directory", context={"root": str(root)}
        ) from exc
    try:
        for part in parts[1:]:
            if part in {"", ".", ".."} or os.sep in part:
                raise UnsafeStateError("unsafe path component", context={"part": part})
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=current)
                except FileExistsError:
                    pass
            try:
                nxt = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=current,
                )
            except OSError as exc:
                raise UnsafeStateError(
                    "a parent component is a symlink or is not a directory",
                    context={"part": part, "root": str(root)},
                ) from exc
            os.close(current)
            current = nxt
        return current
    except Exception:
        os.close(current)
        raise


def _path_under(root: Path, path: Path) -> bool:
    try:
        _relative_parts(root, path)
    except UnsafeStateError:
        return False
    return True


def _session_override_roots(paths: AcquisitionPaths) -> tuple[Path, ...]:
    """Operator-overridden locations that are not under repository or store.

    Each such parent is bound as its own retained descriptor at session start so a
    bound production session never silently reopens a pathname root.
    """

    leaves = (
        paths.report_path,
        paths.receipt_258_path,
        paths.attestation_path,
        paths.lock_path,
        paths.amendment_ledger_path,
        paths.progress_path,
        paths.listing_checkpoint_path,
        paths.contract_metadata_path,
        paths.holdout_path,
        paths.qualification_source_path,
        paths.qualification_cli_path,
        paths.attestation_source_path,
        paths.attestation_cli_path,
        Path(__file__),
        Path(paths.repository) / CLI_RELATIVE_PATH,
    )
    directories = (
        paths.listing_cache_dir,
        paths.coinalyze_cache_dir,
        paths.sample_dir,
        paths.content_root,
        paths.plan_receipt_dir,
        paths.run_receipt_dir,
        paths.terminal_dir,
        paths.tmp_root,
        paths.gate2_root,
    )
    extras: list[Path] = []
    seen: set[Path] = set()
    repo = Path(paths.repository)
    store = Path(paths.store_root)

    def _consider(root: Path) -> None:
        absolute = Path(os.path.abspath(str(root)))
        if absolute in seen:
            return
        if _path_under(store, absolute) or _path_under(repo, absolute):
            return
        for existing in extras:
            if _path_under(existing, absolute):
                return
        seen.add(absolute)
        extras.append(absolute)

    for leaf in leaves:
        _consider(Path(leaf).parent)
    for directory in directories:
        _consider(Path(directory))
    return tuple(extras)


class BoundRoots:
    """Repository, store, and explicitly bound override descriptors for one session."""

    def __init__(
        self,
        repository: Path,
        store: Path,
        repo_fd: int,
        store_fd: int,
        extra: tuple[tuple[Path, int], ...] = (),
    ) -> None:
        self.repository = Path(repository)
        self.store = Path(store)
        self.repo_fd = repo_fd
        self.store_fd = store_fd
        self.extra = extra

    @classmethod
    def open(cls, paths: AcquisitionPaths) -> BoundRoots:
        repo_fd = open_root_dir(paths.repository, create=False)
        extra_fds: list[tuple[Path, int]] = []
        try:
            store_fd = open_root_dir(paths.store_root, create=True)
        except Exception:
            os.close(repo_fd)
            raise
        try:
            for extra_root in _session_override_roots(paths):
                extra_fds.append((extra_root, open_root_dir(extra_root, create=False)))
            return cls(
                paths.repository,
                paths.store_root,
                repo_fd,
                store_fd,
                extra=tuple(extra_fds),
            )
        except Exception:
            for _root, fd in extra_fds:
                os.close(fd)
            os.close(store_fd)
            os.close(repo_fd)
            raise

    def close(self) -> None:
        errors: list[BaseException] = []
        for _root, fd in self.extra:
            try:
                os.close(fd)
            except Exception as exc:  # noqa: BLE001 - nested resource cleanup
                errors.append(exc)
        self.extra = ()
        for fd_name in ("repo_fd", "store_fd"):
            fd = getattr(self, fd_name)
            if fd is None:
                continue
            try:
                os.close(fd)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            setattr(self, fd_name, None)
        if errors:
            raise UnsafeStateError(
                "session root descriptors could not be released",
                context={"error": type(errors[0]).__name__},
            ) from errors[0]

    def root_for(self, path: Path) -> tuple[int, Path]:
        try:
            _relative_parts(self.store, path)
            if self.store_fd is None:
                raise UnsafeStateError("store root descriptor is closed")
            return self.store_fd, self.store
        except UnsafeStateError:
            pass
        try:
            _relative_parts(self.repository, path)
            if self.repo_fd is None:
                raise UnsafeStateError("repository root descriptor is closed")
            return self.repo_fd, self.repository
        except UnsafeStateError:
            pass
        for extra_root, extra_fd in self.extra:
            try:
                _relative_parts(extra_root, path)
            except UnsafeStateError:
                continue
            return extra_fd, extra_root
        raise UnsafeStateError(
            "path is outside the bound session roots",
            context={"path": str(path)},
        )

    def root_for_or_none(self, path: Path) -> tuple[int, Path] | None:
        """The bound root containing ``path``, or ``None`` when it is outside every bound root."""

        try:
            return self.root_for(path)
        except UnsafeStateError:
            return None

    def open_parent(self, path: Path, *, create: bool = False) -> tuple[int, str]:
        root_fd, root = self.root_for(path)
        parts = _relative_parts(root, path)
        return open_dir_chain(root, parts[:-1], create=create, root_fd=root_fd), parts[-1]


def open_dir_chain(
    root: Path, parts: Sequence[str], *, create: bool = False, root_fd: int | None = None,
    roots: BoundRoots | None = None,
) -> int:
    if root_fd is None and roots is not None:
        # A bound session never silently reopens a pathname root. Operator-overridden
        # locations must have been bound as extra retained descriptors at session start.
        session = roots.root_for(Path(root))
        session_fd, session_root = session
        if Path(root) != session_root:
            parts = tuple(_relative_parts(session_root, Path(root))) + tuple(parts)
        root_fd = session_fd
    current = os.dup(root_fd) if root_fd is not None else open_root_dir(root, create=create)
    try:
        for part in parts:
            if part in {"", ".", ".."} or os.sep in part:
                raise UnsafeStateError("unsafe path component", context={"part": part})
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=current)
                except FileExistsError:
                    pass
            try:
                nxt = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=current,
                )
            except OSError as exc:
                raise UnsafeStateError(
                    "a parent component is a symlink or is not a directory",
                    context={"part": part},
                ) from exc
            os.close(current)
            current = nxt
        return current
    except Exception:
        os.close(current)
        raise


def open_parent_dir(
    root: Path,
    path: Path,
    *,
    create: bool = False,
    roots: BoundRoots | None = None,
) -> tuple[int, str]:
    """Descriptor for the safely walked parent of ``path`` plus its leaf name."""

    if roots is not None:
        return roots.open_parent(path, create=create)
    parts = _relative_parts(root, path)
    return open_dir_chain(root, parts[:-1], create=create), parts[-1]


def open_regular_file(
    root: Path,
    path: Path,
    *,
    flags: int = os.O_RDONLY,
    mode: int = 0o600,
    roots: BoundRoots | None = None,
) -> int:
    directory, name = open_parent_dir(root, path, roots=roots)
    try:
        fd = os.open(name, flags | os.O_NOFOLLOW, mode, dir_fd=directory)
    except OSError as exc:
        raise UnsafeStateError(
            "path is a symlink or cannot be opened no-follow", context={"path": str(path)}
        ) from exc
    finally:
        os.close(directory)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise UnsafeStateError("path is not a regular file", context={"path": str(path)})
    except Exception:
        os.close(fd)
        raise
    return fd


def read_fd(fd: int, *, limit: int | None = None) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if limit is not None and total > limit:
            raise UnsafeStateError("file exceeds its accepted ceiling")
        chunks.append(chunk)
    return b"".join(chunks)


def sha256_fd(fd: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        digest.update(chunk)
    return digest.hexdigest(), size


def sha256_file(path: Path, *, root: Path | None = None,
    roots: BoundRoots | None = None,
) -> str:
    """Rehash a regular file through a no-follow descriptor.

    ``root`` walks the whole parent chain; without it only the leaf is proved, which is
    reserved for paths whose parents were already walked by the caller. A bound session
    always uses the retained descriptors and never a pathname precheck.
    """

    if roots is not None:
        fd = open_regular_file(root or path.parent, path, roots=roots)
    elif root is not None:
        fd = open_regular_file(root, path)
    else:
        try:
            fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
        except OSError as exc:
            raise UnsafeStateError(
                "path is a symlink or cannot be opened no-follow",
                context={"path": str(path)},
            ) from exc
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise AuthorityError(f"{path} is not a regular file")
    try:
        return sha256_fd(fd)[0]
    finally:
        os.close(fd)


def write_all(fd: int, payload: bytes) -> int:
    """Loop until every byte is written; a short write is never a successful write."""

    view = memoryview(payload)
    written = 0
    while view:
        count = os.write(fd, view)
        if count <= 0:
            raise UnsafeStateError("write made no progress")
        written += count
        view = view[count:]
    return written


def _require(condition: bool, message: str, context: Mapping[str, Any] | None = None) -> None:
    if not condition:
        raise AuthorityError(message, context=context)


def _hex_digest(value: Any, *, label: str) -> str:
    text = str(value or "")
    if HEX64.fullmatch(text) is None:
        raise AuthorityError(f"{label} is not a SHA-256 digest")
    return text


def module_sha256(path: Path, *, root: Path | None = None,
    roots: BoundRoots | None = None,
) -> str:
    try:
        return sha256_file(path, root=root, roots=roots)
    except UnsafeStateError as exc:
        raise AuthorityError(f"required code file is missing: {path}") from exc


def _code_root_for(paths: AcquisitionPaths, path: Path) -> Path | None:
    return accepted_root_for(paths, path)


def code_identity(paths: AcquisitionPaths,
    *,
    roots: BoundRoots | None = None,
) -> dict[str, str]:
    repo = Path(paths.repository)
    cli = repo / CLI_RELATIVE_PATH
    source = Path(__file__)
    try:
        cli_sha = module_sha256(cli, root=repo, roots=roots)
    except AuthorityError as exc:
        raise AuthorityError("acquisition CLI identity is missing") from exc
    return {
        "policy_identity": POLICY_IDENTITY,
        "acquisition_source_sha256": module_sha256(
            source, root=_code_root_for(paths, source)
        , roots=roots),
        "acquisition_cli_sha256": cli_sha,
        "acquisition_source_path": str(SOURCE_RELATIVE_PATH),
        "acquisition_cli_path": str(CLI_RELATIVE_PATH),
        "qualification_source_sha256": module_sha256(
            paths.qualification_source_path,
            root=_code_root_for(paths, paths.qualification_source_path),
         roots=roots,),
        "qualification_cli_sha256": module_sha256(
            paths.qualification_cli_path,
            root=_code_root_for(paths, paths.qualification_cli_path),
         roots=roots,),
        "capacity_source_sha256": module_sha256(
            paths.attestation_source_path,
            root=_code_root_for(paths, paths.attestation_source_path),
         roots=roots,),
        "capacity_cli_sha256": module_sha256(
            paths.attestation_cli_path,
            root=_code_root_for(paths, paths.attestation_cli_path),
         roots=roots,),
    }


def read_authority_file(
    path: Path, *, label: str, root: Path | None = None, limit: int | None = None,
    roots: BoundRoots | None = None,
) -> bytes:
    """Read an accepted authority file once, through one no-follow descriptor.

    The bytes that are hashed are the bytes that were read from the proved descriptor;
    there is no second open by pathname between the check and the read. When an accepted
    root is known the whole parent chain below it is walked component by component, so an
    intermediate symlink cannot redirect the read.
    """

    try:
        if roots is not None:
            directory, name = roots.open_parent(path)
        elif root is not None:
            directory, name = open_parent_dir(root, path)
        else:
            directory, name = open_dir_chain(path.parent, ()), path.name
    except UnsafeStateError as exc:
        raise AuthorityError(
            f"the accepted {label} is not reachable without following a symlink"
        ) from exc
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    except OSError as exc:
        raise AuthorityError(f"the accepted {label} is missing or is a symlink") from exc
    finally:
        os.close(directory)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise AuthorityError(f"the accepted {label} is not a regular file")
        return read_fd(fd, limit=limit)
    finally:
        os.close(fd)


def accepted_root_for(paths: AcquisitionPaths, path: Path) -> Path | None:
    """The accepted root containing ``path``, or ``None`` when it lies outside both.

    Production authority files live under the store root or the repository, so their whole
    parent chain is walked component by component. An operator-overridden location has no
    accepted root and is proved at its parent and leaf instead.
    """

    for root in (paths.store_root, paths.repository):
        try:
            _relative_parts(root, path)
        except UnsafeStateError:
            continue
        return root
    return None


def _pin_file(
    path: Path, digest: str, size: int | None, *, label: str, root: Path | None = None,
    roots: BoundRoots | None = None,
) -> bytes:
    payload = read_authority_file(path, label=label, root=root, roots=roots)
    actual = sha256_bytes(payload)
    if actual != digest:
        raise AuthorityError(
            f"{label} hash changed",
            context={"expected": digest, "actual": actual},
        )
    if size is not None and len(payload) != size:
        raise AuthorityError(
            f"{label} length changed",
            context={"expected": size, "actual": len(payload)},
        )
    return payload


def _decode_json(payload: bytes, *, label: str) -> dict[str, Any]:
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthorityError(f"the {label} is not JSON") from exc
    if not isinstance(document, dict):
        raise AuthorityError(f"the {label} is not an object")
    return document


def _family_of(key: str) -> str:
    for family in PHYSICAL_FAMILIES + tuple(sorted(FORBIDDEN_FAMILIES)):
        cadence, _, name = family.partition("/")
        if f"/{cadence}/{name}/" in key:
            return family
    return ""


def _symbol_of(key: str, family: str) -> str:
    cadence, _, name = family.partition("/")
    marker = f"/{cadence}/{name}/"
    tail = key.split(marker, 1)[1] if marker in key else ""
    return tail.split("/", 1)[0] if tail else ""


def _interval_of(key: str) -> str:
    stem = key.rsplit("/", 1)[-1]
    stem = stem[: -len(".zip")] if stem.endswith(".zip") else stem
    parts = stem.split("-")
    return "-".join(parts[-3:]) if len(parts) >= 3 else stem


def content_path_for(root: Path, digest: str) -> Path:
    digest = _hex_digest(digest, label="content digest")
    return Path(root) / digest[:2] / digest


def _libc_renameat2() -> Any:
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        renameat2 = libc.renameat2
    except AttributeError as exc:
        raise UnsafeStateError("renameat2 is unavailable") from exc
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    return renameat2


def rename_no_replace(
    directory: int, temporary: str, target: str, *, target_dir: int | None = None
) -> None:
    renameat2 = _libc_renameat2()
    result = renameat2(
        directory,
        os.fsencode(temporary),
        directory if target_dir is None else target_dir,
        os.fsencode(target),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), target)


def link_no_replace(
    source_dir: int, source: str, target_dir: int, target: str
) -> None:
    """Storage-neutral no-replace hard link between two safely walked directories."""

    os.link(
        source,
        target,
        src_dir_fd=source_dir,
        dst_dir_fd=target_dir,
        follow_symlinks=False,
    )


def _move_no_replace(
    source_dir: int, source: str, target_dir: int, target: str
) -> None:
    """Publish a private file under its final name without ever replacing bytes."""

    try:
        rename_no_replace(source_dir, source, target, target_dir=target_dir)
        return
    except UnsafeStateError:
        pass
    except OSError as exc:
        if exc.errno not in {errno.ENOSYS, errno.EINVAL}:
            raise
    link_no_replace(source_dir, source, target_dir, target)
    os.unlink(source, dir_fd=source_dir)


def fsync_dir_fd(directory: int) -> None:
    os.fsync(directory)


@dataclass(frozen=True, slots=True)
class PrivateFile:
    """An unpublished private partial identified by its directory-relative name."""

    root: Path
    name: str
    digest: str
    size: int

    @property
    def path(self) -> Path:
        return self.root / self.name


def discard_private(private: PrivateFile,
    *,
    roots: BoundRoots | None = None,
) -> None:
    try:
        directory, name = open_parent_dir(private.root, private.path, roots=roots)
    except UnsafeStateError:
        return
    try:
        os.unlink(name, dir_fd=directory)
    except FileNotFoundError:
        pass
    finally:
        os.close(directory)


def probe_published_content(shard: int, name: str, digest: str) -> int | None:
    """Rehash an already-published name through its descriptor.

    Returns its size when the published bytes are exactly ``digest``, ``None`` when the
    name is absent, and fails closed when it is a symlink, is not a regular file, or
    holds different bytes.
    """

    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=shard)
    except FileNotFoundError:
        return None
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise UnsafeStateError(
                "a published content address is a symlink", context={"name": name}
            ) from exc
        raise UnsafeStateError(
            "a published content address cannot be opened no-follow",
            context={"name": name},
        ) from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise UnsafeStateError("content-address collision is not a regular file")
        existing, size = sha256_fd(fd)
        if existing != digest:
            raise UnsafeStateError("content-address collision with different bytes")
        return size
    finally:
        os.close(fd)


def _require_published(shard: int, name: str, digest: str) -> int:
    size = probe_published_content(shard, name, digest)
    if size is None:
        raise UnsafeStateError(
            "a published content address disappeared", context={"name": name}
        )
    return size


def publish_private_file(
    private: PrivateFile,
    *,
    content_root: Path,
    device: str,
    filesystem: Filesystem,
    roots: BoundRoots | None = None,
) -> tuple[Path, bool]:
    """Publish a proved private file at its content address, no-replace, then fsync.

    Only an unpublished private partial is ever removed; published content is never
    deleted or replaced.
    """

    digest = _hex_digest(private.digest, label="content digest")
    dest = content_path_for(content_root, digest)
    if filesystem.device_of(content_root) != device:
        raise UnsafeStateError("cross-device publication is refused")
    shard = open_dir_chain(content_root, (digest[:2],), create=True, roots=roots)
    try:
        if probe_published_content(shard, digest, digest) is not None:
            discard_private(private, roots=roots)
            return dest, True
        source_dir, source_name = open_parent_dir(private.root, private.path, roots=roots)
        try:
            try:
                _move_no_replace(source_dir, source_name, shard, digest)
            except FileExistsError:
                discard_private(private, roots=roots)
                _require_published(shard, digest, digest)
                return dest, True
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    discard_private(private, roots=roots)
                    _require_published(shard, digest, digest)
                    return dest, True
                raise UnsafeStateError("no-replace publication failed") from exc
        finally:
            os.close(source_dir)
        fsync_dir_fd(shard)
        return dest, False
    finally:
        os.close(shard)


def _open_private(tmp_root: Path, *, prefix: str,
    roots: BoundRoots | None = None,
) -> tuple[int, int, str]:
    """Create one exclusive private partial and return (dirfd, fd, name)."""

    directory = open_dir_chain(tmp_root, (), create=True, roots=roots)
    name = f".partial-{prefix}.{os.urandom(8).hex()}.tmp"
    try:
        fd = os.open(
            name,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
    except Exception:
        os.close(directory)
        raise
    return directory, fd, name


def stream_to_private(
    chunks: Iterator[bytes],
    *,
    tmp_root: Path,
    device: str,
    filesystem: Filesystem,
    max_bytes: int,
    expected_digest: str | None = None,
    expected_size: int | None = None,
    observer: Callable[[bytes], None] | None = None,
    roots: BoundRoots | None = None,
) -> PrivateFile:
    """Stream one response to a private partial, hashing and observing incrementally.

    Nothing is ever buffered whole: the caller receives only the digest, the size, and a
    private name that no reader can see until it is published.
    """

    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
        raise AcquisitionError(
            "a transfer ceiling must be a positive integer",
            context={"max_bytes": max_bytes},
        )
    if filesystem.device_of(tmp_root) != device:
        raise UnsafeStateError("cross-device publication is refused")
    directory, fd, name = _open_private(tmp_root, prefix="stream", roots=roots)
    digest = hashlib.sha256()
    size = 0
    try:
        try:
            for chunk in chunks:
                if not chunk:
                    continue
                size += len(chunk)
                if size > max_bytes:
                    raise AcquisitionError(
                        "stream exceeded the listed byte ceiling",
                        context={"max_bytes": max_bytes, "actual": size},
                    )
                digest.update(chunk)
                if observer is not None:
                    observer(chunk)
                write_all(fd, chunk)
            os.fsync(fd)
        finally:
            os.close(fd)
        hex_digest = digest.hexdigest()
        if expected_size is not None and size != expected_size:
            raise AcquisitionError(
                "listed byte size does not match",
                context={"expected": expected_size, "actual": size},
            )
        if expected_digest is not None and hex_digest != expected_digest:
            raise AcquisitionError(
                "streamed digest does not match the required checksum",
                context={"expected": expected_digest, "actual": hex_digest},
            )
    except Exception:
        try:
            os.unlink(name, dir_fd=directory)
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(directory)
    return PrivateFile(root=tmp_root, name=name, digest=hex_digest, size=size)


def stream_to_content(
    chunks: Iterator[bytes],
    *,
    content_root: Path,
    tmp_root: Path,
    device: str,
    filesystem: Filesystem,
    max_bytes: int,
    expected_digest: str | None = None,
    expected_size: int | None = None,
    roots: BoundRoots | None = None,
) -> tuple[str, Path, int, bool]:
    private = stream_to_private(
        chunks,
        tmp_root=tmp_root,
        device=device,
        filesystem=filesystem,
        max_bytes=max_bytes,
        expected_digest=expected_digest,
        expected_size=expected_size,
     roots=roots,)
    dest, reused = publish_private_file(
        private, content_root=content_root, device=device, filesystem=filesystem
    , roots=roots)
    return private.digest, dest, private.size, reused


def publish_bytes(
    body: bytes,
    *,
    content_root: Path,
    tmp_root: Path,
    device: str,
    filesystem: Filesystem,
    expected_digest: str | None = None,
    roots: BoundRoots | None = None,
) -> tuple[str, Path, bool]:
    digest = sha256_bytes(body)
    if expected_digest is not None and digest != expected_digest:
        raise AcquisitionError(
            "published bytes do not match the required digest",
            context={"expected": expected_digest, "actual": digest},
        )

    def _one() -> Iterator[bytes]:
        yield body

    published, dest, _size, reused = stream_to_content(
        _one(),
        content_root=content_root,
        tmp_root=tmp_root,
        device=device,
        filesystem=filesystem,
        max_bytes=max(len(body), 1),
        expected_digest=digest,
     roots=roots,)
    return published, dest, reused


def adopt_same_device_file(
    source: Path,
    *,
    source_root: Path,
    content_root: Path,
    digest: str,
    device: str,
    filesystem: Filesystem,
    roots: BoundRoots | None = None,
) -> tuple[Path, bool]:
    """Adopt already-authenticated retained bytes without copying their data blocks.

    The retained object is re-referenced by a safely walked, no-follow, no-replace hard
    link, so the accepted retained credit never consumes the new-raw allocation again.
    """

    digest = _hex_digest(digest, label="retained digest")
    dest = content_path_for(content_root, digest)
    if filesystem.device_of(source.parent) != device or filesystem.device_of(
        content_root
    ) != device:
        raise UnsafeStateError("cross-device retained adoption is refused")
    source_dir, source_name = open_parent_dir(source_root, source, roots=roots)
    try:
        probe = os.open(source_name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=source_dir)
        try:
            if not stat.S_ISREG(os.fstat(probe).st_mode):
                raise UnsafeStateError("retained source is not a regular file")
            actual, _size = sha256_fd(probe)
        finally:
            os.close(probe)
        if actual != digest:
            raise UnsafeStateError("retained source does not match its content address")
        shard = open_dir_chain(content_root, (digest[:2],), create=True, roots=roots)
        try:
            try:
                link_no_replace(source_dir, source_name, shard, digest)
            except FileExistsError:
                _require_published(shard, digest, digest)
                return dest, True
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    _require_published(shard, digest, digest)
                    return dest, True
                raise UnsafeStateError("retained adoption failed") from exc
            fsync_dir_fd(shard)
            return dest, False
        finally:
            os.close(shard)
    finally:
        os.close(source_dir)


def write_named_receipt(
    document: Mapping[str, Any],
    directory: Path,
    device: str,
    filesystem: Filesystem,
    *,
    roots: BoundRoots | None = None,
) -> dict[str, Any]:
    """Publish one immutable content-named receipt with looped writes and fsync."""

    body = canonical_json(document)
    digest = sha256_bytes(body)
    dest = directory / f"{digest}.json"
    if filesystem.device_of(directory) != device:
        raise UnsafeStateError("cross-device publication is refused")
    if roots is not None:
        root_fd, root = roots.root_for(directory)
        target = open_dir_chain(
            root, _relative_parts(root, directory), create=True, root_fd=root_fd
        )
    else:
        target = open_dir_chain(directory, (), create=True)
    try:
        if probe_published_content(target, dest.name, digest) is not None:
            return {"sha256": digest, "path": str(dest), "bytes": len(body), "reused": True}
        name = f".partial-{digest}.{os.urandom(8).hex()}.tmp"
        fd = os.open(
            name,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=target,
        )
        try:
            written = write_all(fd, body)
            if written != len(body):  # pragma: no cover - write_all loops to completion
                raise UnsafeStateError("receipt was written short")
            os.fsync(fd)
            os.lseek(fd, 0, os.SEEK_SET)
            rehashed, size = sha256_fd(fd)
            if rehashed != digest or size != len(body):
                raise UnsafeStateError("receipt bytes do not rehash to their identity")
        except Exception:
            os.close(fd)
            try:
                os.unlink(name, dir_fd=target)
            except FileNotFoundError:
                pass
            raise
        os.close(fd)
        try:
            _move_no_replace(target, name, target, dest.name)
        except FileExistsError:
            os.unlink(name, dir_fd=target)
            _require_published(target, dest.name, digest)
            return {"sha256": digest, "path": str(dest), "bytes": len(body), "reused": True}
        except OSError as exc:
            os.unlink(name, dir_fd=target)
            if exc.errno == errno.EEXIST:
                _require_published(target, dest.name, digest)
                return {
                    "sha256": digest,
                    "path": str(dest),
                    "bytes": len(body),
                    "reused": True,
                }
            raise UnsafeStateError("no-replace receipt publication failed") from exc
        fsync_dir_fd(target)
    finally:
        os.close(target)
    return {"sha256": digest, "path": str(dest), "bytes": len(body), "reused": False}


def write_run_locator(
    run_id: str,
    receipt_sha256: str,
    directory: Path,
    device: str,
    filesystem: Filesystem,
    *,
    roots: BoundRoots | None = None,
) -> None:
    """Bind one finished run to its content-addressed receipt without listing the directory."""

    body = canonical_json({"run_id": run_id, "receipt_sha256": receipt_sha256})
    if filesystem.device_of(directory) != device:
        raise UnsafeStateError("cross-device publication is refused")
    name = f"{run_id}.link"
    directory_fd, leaf = open_parent_dir(directory, directory / name, create=True, roots=roots)
    try:
        try:
            fd = os.open(
                leaf,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory_fd,
            )
        except FileExistsError:
            existing = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
            try:
                actual = read_fd(existing)
            finally:
                os.close(existing)
            if actual == body:
                return
            try:
                located = _decode_json(actual, label="run receipt locator")
            except AuthorityError as exc:
                raise UnsafeStateError(
                    "a published run receipt locator is malformed",
                    context={"run_id": run_id},
                ) from exc
            if canonical_json(located) != actual:
                raise UnsafeStateError("a published run receipt locator is not canonical JSON")
            raise UnsafeStateError("a run receipt locator disagrees with its receipt")
        try:
            write_all(fd, body)
            os.fsync(fd)
        except Exception:
            os.close(fd)
            try:
                os.unlink(leaf, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
            raise
        os.close(fd)
        fsync_dir_fd(directory_fd)
    finally:
        os.close(directory_fd)


def _cleanup_partials(tmp_root: Path, *, roots: BoundRoots | None = None) -> None:
    """Remove only unpublished private partials; published content is never deleted."""

    try:
        if roots is not None:
            parts = _relative_parts(roots.store, tmp_root)
            directory = open_dir_chain(
                roots.store, parts, create=True, root_fd=roots.store_fd
            )
        else:
            if not tmp_root.is_dir() or tmp_root.is_symlink():
                return
            directory = open_dir_chain(tmp_root, (), create=False)
    except UnsafeStateError:
        return
    try:
        for name in os.listdir(directory):
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
    finally:
        os.close(directory)


def parse_sidecar(body: bytes, *, basename: str) -> str:
    text = body.decode("utf-8")
    matches = list(SIDECAR_LINE.finditer(text))
    if len(matches) != 1:
        raise AcquisitionError(
            "sidecar does not name exactly one checksum and basename",
            context={"matches": len(matches), "basename": basename},
        )
    digest, name = matches[0].group(1).lower(), matches[0].group(2)
    if name != basename:
        raise AcquisitionError(
            "sidecar names a different object basename",
            context={"sidecar_filename": name, "basename": basename},
        )
    return _hex_digest(digest, label="sidecar checksum")


def _zip_member_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (int(info.external_attr) >> 16) & 0o170000
    return mode == ZIP_SYMLINK_MODE


def _zip_member_is_unsafe(name: str) -> bool:
    if not name or name.endswith("/"):
        return True
    if "\\" in name or name.startswith("/") or name.startswith("\\"):
        return True
    if len(name) >= 2 and name[1] == ":":
        return True
    parts = Path(name.replace("\\", "/")).parts
    return ".." in parts or any(part in {"", ".", ".."} for part in parts)


def validate_zip_fd(fd: int) -> None:
    """Prove the central directory, member safety, non-empty members, and every CRC."""

    handle = os.fdopen(os.dup(fd), "rb", closefd=True)
    try:
        handle.seek(0)
        try:
            archive = zipfile.ZipFile(handle)
        except (
            zipfile.BadZipFile,
            zipfile.LargeZipFile,
            RuntimeError,
            OSError,
            ValueError,
            NotImplementedError,
        ) as exc:
            raise AcquisitionError("ZIP central directory is invalid") from exc
        try:
            infos = archive.infolist()
            if not infos:
                raise AcquisitionError("ZIP has no members")
            if len(infos) > ZIP_MEMBER_CEILING:
                raise AcquisitionError(
                    "ZIP member count exceeds the accepted ceiling",
                    context={"members": len(infos)},
                )
            uncompressed = 0
            seen: set[str] = set()
            for info in infos:
                name = str(info.filename)
                if name in seen:
                    raise AcquisitionError(
                        "ZIP member path is duplicated", context={"member": name}
                    )
                seen.add(name)
                if _zip_member_is_unsafe(name):
                    raise AcquisitionError(
                        "ZIP member path is unsafe", context={"member": name}
                    )
                if _zip_member_is_symlink(info):
                    raise AcquisitionError(
                        "ZIP member is a symlink", context={"member": name}
                    )
                mode = (int(info.external_attr) >> 16) & 0o170000
                if mode and not stat.S_ISREG(mode):
                    raise AcquisitionError(
                        "ZIP member is empty or not a file", context={"member": name}
                    )
                if info.is_dir() or not name or int(info.file_size) <= 0:
                    raise AcquisitionError(
                        "ZIP member is empty or not a file", context={"member": name}
                    )
                uncompressed += int(info.file_size)
                if uncompressed > ZIP_UNCOMPRESSED_CEILING:
                    raise AcquisitionError(
                        "ZIP uncompressed expansion exceeds the accepted ceiling",
                        context={"uncompressed": uncompressed},
                    )
                crc = 0
                try:
                    with archive.open(info, "r") as member:
                        while True:
                            chunk = member.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            crc = zlib.crc32(chunk, crc)
                except (
                    zipfile.BadZipFile,
                    RuntimeError,
                    OSError,
                    zlib.error,
                    NotImplementedError,
                ) as exc:
                    raise AcquisitionError(
                        "ZIP member CRC does not match", context={"member": name}
                    ) from exc
                if (crc & 0xFFFFFFFF) != (int(info.CRC) & 0xFFFFFFFF):
                    raise AcquisitionError(
                        "ZIP member CRC does not match", context={"member": name}
                    )
        finally:
            try:
                archive.close()
            except (
                zipfile.BadZipFile,
                RuntimeError,
                OSError,
                ValueError,
                NotImplementedError,
            ) as exc:
                raise AcquisitionError("ZIP archive close failed") from exc
    finally:
        try:
            handle.close()
        except OSError as exc:
            raise AcquisitionError("ZIP handle close failed") from exc


def validate_zip(path: Path, *, root: Path | None = None,
    roots: BoundRoots | None = None,
) -> None:
    if root is not None:
        fd = open_regular_file(root, path, roots=roots)
    else:
        try:
            fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
        except OSError as exc:
            raise AcquisitionError("ZIP path is not a regular file") from exc
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise AcquisitionError("ZIP path is not a regular file")
    try:
        validate_zip_fd(fd)
    finally:
        os.close(fd)


class SecretScanner:
    """Incremental secret scan whose chunk windows overlap by the sentinel length.

    A sentinel split across two transport chunks is still found because the tail of every
    chunk is carried into the next comparison, and only that tail is retained.
    """

    def __init__(self, secret: str | None) -> None:
        self.needle = secret.encode("utf-8") if secret else b""
        self._tail = b""
        self.found = False

    def update(self, chunk: bytes) -> None:
        if not self.needle or self.found:
            return
        window = self._tail + chunk
        if self.needle in window:
            self.found = True
            self._tail = b""
            return
        overlap = len(self.needle) - 1
        self._tail = window[-overlap:] if overlap > 0 else b""

    def require_absent(self) -> None:
        if self.found:
            raise AcquisitionError("secret leaked into a Coinalyze response")


_JSON_WHITESPACE = frozenset(b" \t\r\n")
_JSON_STRUCTURAL = frozenset(b"{}[]:,")
_JSON_NUMBER = re.compile(rb"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?$")


@dataclass(frozen=True, slots=True)
class JsonToken:
    kind: str
    text: str = ""


def iter_json_tokens(chunks: Iterator[bytes]) -> Iterator[JsonToken]:
    """Tokenize a JSON byte stream incrementally with a bounded token ceiling.

    Only one token is ever materialised, so an arbitrarily large response is tokenized in
    constant memory. Numbers are emitted as their exact source lexemes; no binary float
    is ever constructed.
    """

    buffer = bytearray()
    mode = "value"
    escape = False
    unicode_left = 0
    for chunk in chunks:
        for byte in chunk:
            if mode == "string":
                buffer.append(byte)
                BOUND_TELEMETRY.note("max_token_bytes", len(buffer))
                if len(buffer) > MAX_JSON_TOKEN_BYTES:
                    raise AcquisitionError("a JSON string exceeds the accepted ceiling")
                if unicode_left:
                    unicode_left -= 1
                    continue
                if escape:
                    escape = False
                    if byte == 0x75:  # \uXXXX
                        unicode_left = 4
                    continue
                if byte == 0x5C:
                    escape = True
                    continue
                if byte == 0x22:
                    raw = bytes(buffer)
                    try:
                        yield JsonToken("str", json.loads(raw.decode("utf-8")))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise AcquisitionError("a JSON string is malformed") from exc
                    buffer.clear()
                    mode = "value"
                continue
            if mode == "literal":
                if byte in _JSON_WHITESPACE or byte in _JSON_STRUCTURAL:
                    yield _literal_token(bytes(buffer))
                    buffer.clear()
                    mode = "value"
                else:
                    buffer.append(byte)
                    BOUND_TELEMETRY.note("max_token_bytes", len(buffer))
                    if len(buffer) > MAX_JSON_TOKEN_BYTES:
                        raise AcquisitionError("a JSON literal exceeds the ceiling")
                    continue
            if byte in _JSON_WHITESPACE:
                continue
            if byte in _JSON_STRUCTURAL:
                yield JsonToken(chr(byte))
                continue
            if byte == 0x22:
                buffer.clear()
                buffer.append(byte)
                mode = "string"
                continue
            buffer.append(byte)
            mode = "literal"
    if mode == "string":
        raise AcquisitionError("a JSON string is unterminated")
    if mode == "literal":
        yield _literal_token(bytes(buffer))


def _literal_token(raw: bytes) -> JsonToken:
    if raw == b"true":
        return JsonToken("true")
    if raw == b"false":
        return JsonToken("false")
    if raw == b"null":
        return JsonToken("null")
    if _JSON_NUMBER.fullmatch(raw) is None:
        raise AcquisitionError("a JSON literal is not an exact number lexeme")
    return JsonToken("num", raw.decode("ascii"))


class _TokenCursor:
    def __init__(self, tokens: Iterator[JsonToken]) -> None:
        self._tokens = tokens
        self._peeked: JsonToken | None = None

    def next(self) -> JsonToken:
        if self._peeked is not None:
            token, self._peeked = self._peeked, None
            return token
        try:
            return next(self._tokens)
        except StopIteration as exc:
            raise AcquisitionError("the JSON response ended early") from exc

    def peek(self) -> JsonToken:
        if self._peeked is None:
            self._peeked = self.next()
        return self._peeked

    def expect(self, kind: str) -> JsonToken:
        token = self.next()
        if token.kind != kind:
            raise AcquisitionError(
                "the JSON response shape is invalid",
                context={"expected": kind, "actual": token.kind},
            )
        return token

    def exhausted(self) -> bool:
        if self._peeked is not None:
            return False
        try:
            self._peeked = next(self._tokens)
        except StopIteration:
            return True
        return False

    def skip_value(self, depth: int = 0) -> None:
        if depth > MAX_JSON_DEPTH:
            raise AcquisitionError("the JSON response nests beyond the accepted depth")
        token = self.next()
        if token.kind in {"str", "num", "true", "false", "null"}:
            return
        if token.kind == "{":
            if self.peek().kind == "}":
                self.next()
                return
            seen: set[str] = set()
            while True:
                name = self.expect("str").text
                if name in seen:
                    raise AcquisitionError("a JSON object repeats a field")
                seen.add(name)
                self.expect(":")
                self.skip_value(depth + 1)
                nxt = self.next()
                if nxt.kind == "}":
                    return
                if nxt.kind != ",":
                    raise AcquisitionError("the JSON object is malformed")
        if token.kind == "[":
            if self.peek().kind == "]":
                self.next()
                return
            while True:
                self.skip_value(depth + 1)
                nxt = self.next()
                if nxt.kind == "]":
                    return
                if nxt.kind != ",":
                    raise AcquisitionError("the JSON array is malformed")
        raise AcquisitionError("the JSON response shape is invalid")


def _decimal_lexeme(text: str, *, field_name: str) -> Decimal:
    lowered = text.lower()
    if "e" in lowered:
        exponent_text = lowered.rsplit("e", 1)[1]
        try:
            exponent = int(exponent_text)
        except ValueError as exc:
            raise AcquisitionError(f"Coinalyze {field_name} is not a decimal") from exc
        if abs(exponent) > MAX_DECIMAL_ABS_EXPONENT:
            raise AcquisitionError(
                f"Coinalyze {field_name} exponent exceeds the accepted ceiling"
            )
    digits = lowered.replace("-", "").replace("+", "").replace(".", "").split("e", 1)[0]
    if not digits or len(digits) > MAX_DECIMAL_DIGITS:
        raise AcquisitionError(
            f"Coinalyze {field_name} exceeds the accepted decimal digit ceiling"
        )
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise AcquisitionError(f"Coinalyze {field_name} is not a decimal") from exc
    if not number.is_finite() or number < 0:
        raise AcquisitionError(
            f"Coinalyze {field_name} is not a finite non-negative decimal"
        )
    if number.adjusted() > MAX_DECIMAL_ABS_EXPONENT:
        raise AcquisitionError(
            f"Coinalyze {field_name} exponent exceeds the accepted ceiling"
        )
    return number


@dataclass(frozen=True, slots=True)
class LiquidationSummary:
    """Bounded proof of one liquidation response; no point list is retained."""

    outcome: str
    points: int
    first_t: int | None
    last_t: int | None
    digest: str


def validate_liquidation_stream(
    chunks: Iterator[bytes], *, provider_symbol: str, start: int, end: int
) -> LiquidationSummary:
    """Incrementally prove one daily liquidation response against its exact request.

    The returned provider symbol must equal the requested one, timestamps must be unique,
    ascending, daily, and inside the fixed bounds, and ``l``/``s`` must be finite
    non-negative decimals parsed from their exact source lexemes. Only counters, the last
    timestamp, and a rolling digest of the accepted points are retained.
    """

    cursor = _TokenCursor(iter_json_tokens(chunks))
    token = cursor.next()
    rows_expected_close: str | None = None
    if token.kind == "[":
        if cursor.peek().kind == "]":
            raise AcquisitionError("Coinalyze response omitted the provider symbol")
        rows_expected_close = "]"
        token = cursor.next()
    if token.kind != "{":
        raise AcquisitionError("Coinalyze liquidation response shape is invalid")
    seen_symbol = False
    seen_history = False
    seen_fields: set[str] = set()
    points = 0
    first_t: int | None = None
    last_t: int | None = None
    digest = hashlib.sha256()
    if cursor.peek().kind == "}":
        raise AcquisitionError("Coinalyze response omitted the provider symbol")
    while True:
        name = cursor.expect("str").text
        if name in seen_fields:
            raise AcquisitionError("a JSON object repeats a field")
        seen_fields.add(name)
        cursor.expect(":")
        if name == "symbol":
            value = cursor.next()
            if value.kind != "str":
                raise AcquisitionError("Coinalyze provider symbol is not a string")
            if value.text != provider_symbol:
                raise AcquisitionError(
                    "Coinalyze returned a different provider symbol",
                    context={"expected": provider_symbol, "actual": value.text},
                )
            seen_symbol = True
        elif name == "history":
            if seen_history:
                raise AcquisitionError("Coinalyze history is declared twice")
            seen_history = True
            cursor.expect("[")
            if cursor.peek().kind == "]":
                cursor.next()
            else:
                while True:
                    stamp, long_text, short_text = _read_point(cursor)
                    if stamp % 86400 != 0:
                        raise AcquisitionError(
                            "Coinalyze timestamp is not a daily boundary"
                        )
                    if stamp < start or stamp > end:
                        raise AcquisitionError(
                            "Coinalyze timestamp is outside the fixed bounds"
                        )
                    if last_t is not None and stamp <= last_t:
                        raise AcquisitionError(
                            "Coinalyze timestamps are not unique and ascending"
                        )
                    long_v = _decimal_lexeme(long_text, field_name="l")
                    short_v = _decimal_lexeme(short_text, field_name="s")
                    digest.update(
                        compact_json(
                            {
                                "t": stamp,
                                "l": format(long_v, "f"),
                                "s": format(short_v, "f"),
                            }
                        )
                    )
                    if first_t is None:
                        first_t = stamp
                    last_t = stamp
                    points += 1
                    nxt = cursor.next()
                    if nxt.kind == "]":
                        break
                    if nxt.kind != ",":
                        raise AcquisitionError("Coinalyze history array is malformed")
        else:
            cursor.skip_value()
        nxt = cursor.next()
        if nxt.kind == "}":
            break
        if nxt.kind != ",":
            raise AcquisitionError("Coinalyze response object is malformed")
    if not seen_symbol:
        raise AcquisitionError("Coinalyze response omitted the provider symbol")
    if not seen_history:
        raise AcquisitionError("Coinalyze response omitted its history")
    if rows_expected_close is not None:
        closing = cursor.next()
        if closing.kind == ",":
            raise AcquisitionError(
                "Coinalyze returned more than one symbol for a one-symbol request"
            )
        if closing.kind != "]":
            raise AcquisitionError("Coinalyze response array is malformed")
    if not cursor.exhausted():
        raise AcquisitionError("Coinalyze response has trailing content")
    outcome = OUTCOME_EMPTY_HISTORY if points == 0 else "history"
    return LiquidationSummary(
        outcome=outcome,
        points=points,
        first_t=first_t,
        last_t=last_t,
        digest=digest.hexdigest(),
    )


def _exact_number_lexeme(token: JsonToken, *, field_name: str) -> str:
    """The exact source lexeme of a decimal field.

    Both the JSON number form and the quoted decimal form the provider has been observed
    to use are exact; a binary float is never constructed from either.
    """

    if token.kind == "num":
        return token.text
    if token.kind == "str":
        if _JSON_NUMBER.fullmatch(token.text.encode("utf-8")) is None:
            raise AcquisitionError(f"Coinalyze {field_name} is not a decimal lexeme")
        return token.text
    raise AcquisitionError(f"Coinalyze {field_name} is not a decimal lexeme")


def _read_point(cursor: _TokenCursor) -> tuple[int, str, str]:
    cursor.expect("{")
    stamp: int | None = None
    long_text: str | None = None
    short_text: str | None = None
    seen_fields: set[str] = set()
    if cursor.peek().kind == "}":
        raise AcquisitionError("Coinalyze history point is empty")
    while True:
        name = cursor.expect("str").text
        if name in seen_fields:
            raise AcquisitionError("a JSON object repeats a field")
        seen_fields.add(name)
        cursor.expect(":")
        if name == "t":
            token = cursor.next()
            if token.kind != "num":
                raise AcquisitionError("Coinalyze timestamp is invalid")
            value = _decimal_lexeme(token.text, field_name="t")
            if value != value.to_integral_value():
                raise AcquisitionError("Coinalyze timestamp is not an integer second")
            stamp = int(value)
        elif name == "l":
            long_text = _exact_number_lexeme(cursor.next(), field_name="l")
        elif name == "s":
            short_text = _exact_number_lexeme(cursor.next(), field_name="s")
        else:
            cursor.skip_value()
        nxt = cursor.next()
        if nxt.kind == "}":
            break
        if nxt.kind != ",":
            raise AcquisitionError("Coinalyze history point is malformed")
    if stamp is None or long_text is None or short_text is None:
        raise AcquisitionError("Coinalyze history point is missing a required field")
    return stamp, long_text, short_text


def validate_liquidation_file(
    path: Path, *, root: Path, provider_symbol: str, start: int, end: int,
    roots: BoundRoots | None = None,
) -> LiquidationSummary:
    fd = open_regular_file(root, path, roots=roots)
    try:
        return validate_liquidation_stream(
            _iter_fd(fd), provider_symbol=provider_symbol, start=start, end=end
        )
    finally:
        os.close(fd)


def _iter_fd(fd: int) -> Iterator[bytes]:
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, CHUNK_SIZE)
        if not chunk:
            return
        yield chunk


def parse_liquidation_history(
    payload: bytes, *, provider_symbol: str, start: int, end: int
) -> tuple[str, LiquidationSummary]:
    """Bytes-in wrapper over the streaming validator, used by focused tests."""

    def _one() -> Iterator[bytes]:
        for offset in range(0, len(payload), CHUNK_SIZE):
            yield payload[offset : offset + CHUNK_SIZE]

    summary = validate_liquidation_stream(
        _one(), provider_symbol=provider_symbol, start=start, end=end
    )
    return summary.outcome, summary


def classify_status(status: int) -> str:
    if status == 200:
        return RETRY_OK
    if status == 429:
        return RETRY_RATE_LIMIT
    if status in {400, 401, 403, 404, 409, 410, 422}:
        return RETRY_TERMINAL
    if status >= 500:
        return RETRY_TRANSIENT
    return RETRY_TERMINAL


def bounded_retry_after(headers: Mapping[str, str]) -> float:
    raw = headers.get("Retry-After") or headers.get("retry-after") or "0"
    try:
        delay = float(raw)
    except ValueError:
        delay = 0.0
    if delay < 0:
        delay = 0.0
    return min(delay, float(MAX_RETRY_AFTER_SECONDS))


def redact_text(text: str, secret: str | None) -> str:
    if not secret:
        return text
    return text.replace(secret, "<redacted>")


def url_has_secret(url: str, secret: str | None) -> bool:
    if not secret:
        return False
    split = urlsplit(url)
    haystack = "&".join((split.query, split.path, split.fragment))
    return secret in haystack


def _utc_day_from_iso(value: str) -> int:
    moment = datetime.fromisoformat(value.replace("Z", "+00:00").replace(" ", "T"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).date().toordinal()


def _utc_day_from_ms(value: int) -> int:
    return datetime.fromtimestamp(int(value) // 1000, UTC).date().toordinal()


def _ordinal_to_unix(day: int) -> int:
    return int(datetime.fromordinal(day).replace(tzinfo=UTC).timestamp())


@dataclass(frozen=True, slots=True)
class PlanObject:
    provider: str
    identity: str
    kind: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class PlanSummary:
    identity: str
    family_totals: dict[str, int]
    binance_bytes: int
    cost_digest: str
    coinalyze_supported: tuple[str, ...]
    coinalyze_unsupported: tuple[str, ...]
    coinalyze_mappings: tuple[dict[str, str], ...]
    cutoff: str
    holdout_id: str
    helper_identities: Mapping[str, str]
    code_identity: Mapping[str, str]
    object_count: int
    lifecycles: Mapping[str, tuple[int, int]]
    retained_credit: RetainedCredit


def authenticate_helpers(paths: AcquisitionPaths, pins: AuthorityPins,
    *,
    roots: BoundRoots | None = None,
) -> dict[str, str]:
    actual_source = module_sha256(
        paths.qualification_source_path,
        root=_code_root_for(paths, paths.qualification_source_path),
     roots=roots,)
    actual_cli = module_sha256(
        paths.qualification_cli_path,
        root=_code_root_for(paths, paths.qualification_cli_path),
     roots=roots,)
    actual_cap_source = module_sha256(
        paths.attestation_source_path,
        root=_code_root_for(paths, paths.attestation_source_path),
     roots=roots,)
    actual_cap_cli = module_sha256(
        paths.attestation_cli_path,
        root=_code_root_for(paths, paths.attestation_cli_path),
     roots=roots,)
    if actual_source != pins.qualification_source_sha256:
        raise AuthorityError(
            "qualification source identity changed",
            context={"expected": pins.qualification_source_sha256, "actual": actual_source},
        )
    if actual_cli != pins.qualification_cli_sha256:
        raise AuthorityError(
            "qualification CLI identity changed",
            context={"expected": pins.qualification_cli_sha256, "actual": actual_cli},
        )
    if actual_cap_source != pins.capacity_source_sha256:
        raise AuthorityError(
            "capacity source identity changed",
            context={"expected": pins.capacity_source_sha256, "actual": actual_cap_source},
        )
    if actual_cap_cli != pins.capacity_cli_sha256:
        raise AuthorityError(
            "capacity CLI identity changed",
            context={"expected": pins.capacity_cli_sha256, "actual": actual_cap_cli},
        )
    return {
        "qualification_source_sha256": actual_source,
        "qualification_cli_sha256": actual_cli,
        "capacity_source_sha256": actual_cap_source,
        "capacity_cli_sha256": actual_cap_cli,
        "iter_manifest_detail": (
            "cryptofactors.acquisition.binance_usdm_harmonic_qualification.iter_manifest_detail"
        ),
    }


def load_holdout(path: Path, pins: AuthorityPins, *, root: Path | None = None,
    roots: BoundRoots | None = None,
) -> dict[str, Any]:
    document = _decode_json(
        read_authority_file(path, label="holdout boundary", root=root, roots=roots), label="holdout"
    )
    body = document.get("payload") if isinstance(document.get("payload"), dict) else document
    boundary_id = str(body.get("boundary_id") or "")
    if boundary_id != pins.holdout_boundary_id:
        raise AuthorityError(
            "holdout boundary identity changed",
            context={"expected": pins.holdout_boundary_id, "actual": boundary_id},
        )
    return dict(body)


def load_attestation(
    path: Path, pins: AuthorityPins, *, root: Path | None = None,
    roots: BoundRoots | None = None,
) -> dict[str, Any]:
    payload = _pin_file(
        path,
        pins.attestation_282_sha256,
        pins.attestation_282_bytes,
        label="attestation 282",
        root=root,
     roots=roots,)
    document = _decode_json(payload, label="attestation 282")
    capacity = dict(document.get("capacity") or {})
    filesystem = dict(document.get("filesystem") or {})
    if int(capacity.get("stable_requirement_bytes") or 0) != pins.stable_requirement_bytes:
        raise AuthorityError("attestation 282 stable requirement changed")
    if filesystem.get("device") != pins.device:
        raise AuthorityError("attestation 282 device changed")
    if filesystem.get("destination") != pins.destination:
        raise AuthorityError("attestation 282 destination changed")
    if (
        int(capacity.get("stable_requirement_bytes") or 0) != EXPECTED_STABLE_REQUIREMENT_BYTES
        and pins.stable_requirement_bytes == PRODUCTION_PINS.stable_requirement_bytes
    ):
        raise AuthorityError("attestation 282 does not match ADR-0028")
    unsigned = dict(document)
    identity = dict(unsigned.pop("self_identity", {}) or {})
    if identity:
        expected = sha256_bytes(canonical_json(unsigned))
        if identity.get("payload_sha256") != expected:
            raise AuthorityError("attestation 282 self identity is wrong")
    return document


def evaluate_capacity(
    *,
    pins: AuthorityPins,
    available_bytes: int,
    next_transfer_bytes: int = 0,
) -> dict[str, Any]:
    if not isinstance(available_bytes, int) or isinstance(available_bytes, bool) or available_bytes < 0:
        raise CapacityBlocked("available bytes are invalid")
    reserve = operating_reserve_bytes(max(available_bytes, 1))
    total = pins.stable_requirement_bytes + reserve
    needed = total + max(int(next_transfer_bytes), 0)
    blocked = needed > available_bytes
    return {
        "stable_requirement_bytes": pins.stable_requirement_bytes,
        "operating_reserve_bytes": reserve,
        "total_future_storage_bytes": total,
        "available_bytes": available_bytes,
        "next_transfer_bytes": next_transfer_bytes,
        "needed_bytes": needed,
        "storage_preflight_state": "blocked" if blocked else "sufficient",
        "reserve_floor_bytes": MINIMUM_OPERATING_RESERVE_BYTES,
        "stable_components": dict(STABLE_COMPONENTS)
        if pins.stable_requirement_bytes == EXPECTED_STABLE_REQUIREMENT_BYTES
        else {"stable_requirement_bytes": pins.stable_requirement_bytes},
    }


def resolve_cost_objects(
    *,
    report: Mapping[str, Any],
    listing_checkpoint: Mapping[str, Any],
    listing_cache_dir: Path,
    pins: AuthorityPins,
    roots: BoundRoots | None = None,
) -> tuple[tuple[dict[str, Any], ...], str]:
    storage = dict(report.get("storage") or {})
    cost_block = dict(storage.get("cost_sample") or {})
    keys = [str(item) for item in (cost_block.get("keys") or ())]
    if len(keys) != pins.cost_objects:
        raise AuthorityError(
            "cost key count changed",
            context={"expected": pins.cost_objects, "actual": len(keys)},
        )
    entries = dict(listing_checkpoint.get("entries") or {})
    if not entries:
        raise AuthorityError("the accepted listing checkpoint has no entries")
    sizes: dict[str, int] = {}
    etags: dict[str, str] = {}
    wanted = set(keys)
    for name, entry in sorted(entries.items()):
        if not isinstance(entry, dict):
            continue
        content_path = Path(str(entry.get("content_path") or ""))
        digest = str(entry.get("response_sha256") or "")
        if not digest:
            continue
        try:
            body = read_authority_file(
                content_path, label="listing response", root=listing_cache_dir,
                roots=roots,
            )
        except AuthorityError:
            continue
        actual = sha256_bytes(body)
        if actual != digest:
            raise AuthorityError(
                "listing response digest changed",
                context={"entry": name, "expected": digest, "actual": actual},
            )
        try:
            _prefixes, listed, _truncated, _token = parse_s3_list_bucket(
                body.decode("utf-8")
            )
        except Exception:
            continue
        for obj in listed:
            key = str(obj.key)
            if key in wanted and key not in sizes:
                size = obj.size
                if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
                    raise AuthorityError(
                        "an accepted cost key has no positive listed size",
                        context={"key": key},
                    )
                sizes[key] = int(size)
                etags[key] = str(obj.etag or "")
    missing = sorted(key for key in keys if key not in sizes)
    if missing:
        raise AuthorityError(
            "the accepted listing evidence does not size every cost key",
            context={"missing": missing[:8], "missing_count": len(missing)},
        )
    objects: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    for key in sorted(keys):
        family = _family_of(key)
        if family not in COST_FAMILIES:
            raise AuthorityError(
                "an accepted cost key is outside the cost families",
                context={"key": key, "family": family},
            )
        symbol = _symbol_of(key, family)
        objects.append(
            {
                "key": key,
                "family": family,
                "symbol": symbol,
                "economic_interval": _interval_of(key),
                "byte_size": sizes[key],
                "etag": etags[key],
                "sidecar_key": f"{key}.CHECKSUM",
            }
        )
        items.append(
            {
                "family": family,
                "symbol": symbol,
                "key": key,
                "object": type("Obj", (), {"size": sizes[key], "etag": etags[key]})(),
            }
        )
    total = sum(int(item["byte_size"]) for item in objects)
    if total != pins.cost_bytes:
        raise AuthorityError(
            "cost bytes changed",
            context={"expected": pins.cost_bytes, "actual": total},
        )
    digest = cost_manifest_digest(
        items,
        selector=COST_SELECTOR,
        families=COST_FAMILIES,
        gaps=list(cost_block.get("gaps") or ()),
    )
    if digest != pins.cost_manifest_sha256:
        raise AuthorityError(
            "complete cost-manifest identity changed",
            context={"expected": pins.cost_manifest_sha256, "actual": digest},
        )
    return tuple(objects), digest


def derive_coinalyze_mappings(
    *,
    report: Mapping[str, Any],
    contract_metadata: Mapping[str, Any],
    pins: AuthorityPins,
    cache_root: Path | None = None,
    roots: BoundRoots | None = None,
) -> tuple[tuple[dict[str, str], ...], tuple[str, ...], tuple[str, ...], dict[str, tuple[int, int]], str]:
    block = dict(report.get("coinalyze") or {})
    support = dict(block.get("universe_support") or {})
    supported = tuple(str(item) for item in (support.get("supported_symbols") or ()))
    unmapped = tuple(str(item) for item in (support.get("unmapped_symbols") or ()))
    if len(supported) != pins.coinalyze_supported:
        raise AuthorityError(
            "Coinalyze supported mapping count changed",
            context={"expected": pins.coinalyze_supported, "actual": len(supported)},
        )
    if len(unmapped) != pins.coinalyze_unsupported:
        raise AuthorityError(
            "Coinalyze unsupported gap count changed",
            context={"expected": pins.coinalyze_unsupported, "actual": len(unmapped)},
        )
    if set(supported) & set(unmapped):
        raise AuthorityError("a Coinalyze symbol is both supported and unmapped")
    provenance = list(block.get("provenance") or ())
    inventory_body: bytes | None = None
    for item in provenance:
        if not isinstance(item, dict):
            continue
        if str(item.get("path") or "") != COINALYZE_MARKETS_PATH:
            continue
        content_path = Path(str(item.get("content_path") or ""))
        digest = str(item.get("sha256") or "")
        body = read_authority_file(
            content_path, label="retained Coinalyze inventory", root=cache_root
        , roots=roots)
        if sha256_bytes(body) != digest:
            raise AuthorityError("retained Coinalyze inventory digest changed")
        inventory_body = body
        break
    if inventory_body is None:
        raise AuthorityError("retained Coinalyze future-markets provenance is missing")
    markets = json.loads(inventory_body.decode("utf-8"))
    if not isinstance(markets, list):
        raise AuthorityError("Coinalyze inventory is not a list")
    native_to_provider: dict[str, str] = {}
    for row in markets:
        if not isinstance(row, dict):
            continue
        if str(row.get("exchange")) != COINALYZE_EXCHANGE_CODE:
            continue
        if not bool(row.get("is_perpetual")):
            continue
        native = str(row.get("symbol_on_exchange") or "").strip().upper()
        provider = str(row.get("symbol") or "")
        if not native or provider != coinalyze_perp_symbol(native):
            continue
        if native in native_to_provider:
            raise AuthorityError("Coinalyze inventory has a duplicate native identity")
        native_to_provider[native] = provider
    mappings: list[dict[str, str]] = []
    for native in supported:
        provider = native_to_provider.get(native)
        if provider is None:
            raise AuthorityError(
                "a supported Coinalyze mapping has no proved native inventory binding",
                context={"symbol": native},
            )
        mappings.append({"native_symbol": native, "provider_symbol": provider})
    if len({item["provider_symbol"] for item in mappings}) != len(mappings):
        raise AuthorityError("two supported native mappings share one Coinalyze provider identity")
    cutoff = str(report.get("generated_at") or "")
    if not cutoff:
        raise AuthorityError("the accepted report has no qualification cutoff")
    cutoff_day = _utc_day_from_iso(cutoff)
    snapshot = dict(contract_metadata.get("symbol_snapshot") or {})
    membership = dict(report.get("membership") or {})
    rows = {
        str(item.get("symbol")): item
        for item in (membership.get("classifications") or ())
        if isinstance(item, dict)
    }
    lifecycles: dict[str, tuple[int, int]] = {}
    unknown: list[str] = []
    for symbol in supported:
        if snapshot and symbol not in snapshot:
            raise AuthorityError(
                "a supported mapping has no retained contract snapshot",
                context={"symbol": symbol},
            )
        evidence = rows.get(symbol) or {}
        records = list(evidence.get("evidence") or ()) if isinstance(evidence, dict) else []
        onboard = None
        close = None
        for item in records:
            if not isinstance(item, dict) or item.get("onboard_ms") is None:
                continue
            onboard = item.get("onboard_ms")
            close = item.get("closed_observed_ms")
            if close is None:
                close = item.get("delivery_ms")
            break
        if not isinstance(onboard, int) or isinstance(onboard, bool) or onboard <= 0:
            unknown.append(symbol)
            continue
        first = _utc_day_from_ms(onboard)
        last = cutoff_day
        if isinstance(close, int) and not isinstance(close, bool) and close > 0:
            last = min(last, _utc_day_from_ms(close))
        if last < first:
            unknown.append(symbol)
            continue
        lifecycles[symbol] = (first, last)
    if unknown:
        raise AuthorityError(
            "a supported Coinalyze mapping has no authenticated lifecycle",
            context={"symbols": unknown[:8]},
        )
    inventory_digest = sha256_bytes(
        compact_json(
            [
                {"native_symbol": native, "provider_symbol": provider}
                for native, provider in sorted(native_to_provider.items())
            ]
        )
    )
    return (
        tuple(mappings),
        supported,
        unmapped,
        lifecycles,
        cutoff,
        {"digest": inventory_digest, "count": len(native_to_provider)},
    )


def _manifest_detail_path(store_root: Path, descriptor: Mapping[str, Any]) -> Path:
    relative = str(descriptor.get("relative_path") or "")
    candidate = Path(relative)
    if not relative or candidate.is_absolute() or ".." in candidate.parts:
        raise AuthorityError(
            "manifest detail path escapes the store evidence root",
            context={"relative_path": relative},
        )
    if not candidate.name.endswith(".jsonl.gz"):
        raise AuthorityError("manifest detail path is not a canonical JSONL gzip artifact")
    return Path(store_root) / candidate


def iter_selected_binance(
    store_root: Path,
    descriptor: Mapping[str, Any],
    pins: AuthorityPins,
    *,
    roots: BoundRoots | None = None,
    fault: FaultInjector | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream selected rows after proving the gzip through bound descriptors."""

    if str(descriptor.get("schema_version")) != MANIFEST_DETAIL_SCHEMA_VERSION:
        raise AuthorityError("manifest detail schema version is not supported")
    if str(descriptor.get("format")) != MANIFEST_DETAIL_FORMAT:
        raise AuthorityError("manifest detail format is not supported")
    expected_compressed = str(descriptor.get("compressed_sha256") or "")
    expected_uncompressed = str(descriptor.get("uncompressed_sha256") or "")
    if expected_compressed != pins.manifest_compressed_sha256:
        raise AuthorityError(
            "manifest compressed digest changed",
            context={"expected": pins.manifest_compressed_sha256, "actual": expected_compressed},
        )
    if expected_uncompressed != pins.manifest_uncompressed_sha256:
        raise AuthorityError(
            "manifest uncompressed digest changed",
            context={"expected": pins.manifest_uncompressed_sha256, "actual": expected_uncompressed},
        )
    path = _manifest_detail_path(store_root, descriptor)
    fault = fault or FaultInjector()
    fault.check("before_manifest_open")
    fd = open_regular_file(store_root, path, roots=roots)
    count = 0
    total = 0
    try:
        compressed, compressed_bytes = sha256_fd(fd)
        if compressed != expected_compressed:
            raise AuthorityError(
                "manifest compressed digest changed",
                context={"expected": expected_compressed, "actual": compressed},
            )
        declared_bytes = descriptor.get("compressed_bytes")
        if (
            declared_bytes is not None
            and (not isinstance(declared_bytes, int) or isinstance(declared_bytes, bool)
                 or int(declared_bytes) != compressed_bytes)
        ):
            raise AuthorityError("manifest compressed size does not match its descriptor")
        os.lseek(fd, 0, os.SEEK_SET)
        handle = os.fdopen(os.dup(fd), "rb")
        uncompressed = hashlib.sha256()
        try:
            with gzip.GzipFile(fileobj=handle, mode="rb") as archive:
                for raw in archive:
                    uncompressed.update(raw)
                    try:
                        record = json.loads(raw.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise AuthorityError("manifest detail record is not JSON") from exc
                    if not isinstance(record, dict):
                        raise AuthorityError("manifest detail record is not an object")
                    if str(record.get("record_type") or "") != "row":
                        continue
                    body = dict(record.get("record") or {})
                    family = str(body.get("family") or "")
                    if family in FORBIDDEN_FAMILIES:
                        raise AuthorityError(
                            "selected manifest contains a forbidden family",
                            context={"family": family, "key": body.get("key")},
                        )
                    if family not in ARCHIVE_FAMILIES:
                        raise AuthorityError(
                            "a selected manifest row is outside the archive families",
                            context={"family": family},
                        )
                    size = body.get("byte_size")
                    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
                        raise AuthorityError(
                            "a selected manifest row has no positive integer size"
                        )
                    count += 1
                    total += int(size)
                    key = str(body["key"])
                    yield {
                        "key": key,
                        "family": family,
                        "symbol": str(body.get("symbol") or ""),
                        "listed_bytes": int(size),
                        "economic_interval": body.get("economic_interval") or _interval_of(key),
                        "sidecar_key": body.get("sidecar_key") or f"{key}.CHECKSUM",
                        "consumable": bool(body.get("consumable")),
                        "url": f"{VISION_OBJECT_BASE}/{key}",
                        "sidecar_url": f"{VISION_OBJECT_BASE}/{key}.CHECKSUM",
                    }
        finally:
            handle.close()
        actual_uncompressed = uncompressed.hexdigest()
        if actual_uncompressed != expected_uncompressed:
            raise AuthorityError(
                "manifest uncompressed digest changed",
                context={"expected": expected_uncompressed, "actual": actual_uncompressed},
            )
    finally:
        os.close(fd)
    if count != pins.main_selected_objects:
        raise AuthorityError(
            "selected object count changed",
            context={"expected": pins.main_selected_objects, "actual": count},
        )
    if total != pins.main_selected_bytes:
        raise AuthorityError(
            "selected bytes changed",
            context={"expected": pins.main_selected_bytes, "actual": total},
        )


def _authority_int(value: Any, *, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise AuthorityError(f"{label} is not an exact integer")
    if value < minimum:
        raise AuthorityError(f"{label} is below its bound")
    return value


def _authority_str(value: Any, *, label: str) -> str:
    if type(value) is not str or value == "":
        raise AuthorityError(f"{label} is not a non-empty string")
    return value


def _require_authority(
    condition: bool, message: str, context: Mapping[str, Any] | None = None
) -> None:
    if not condition:
        raise AuthorityError(message, context=dict(context or {}))


def _authority_object(
    value: Any, *, label: str, keys: frozenset[str]
) -> dict[str, Any]:
    if type(value) is not dict:
        raise AuthorityError(f"{label} is not an exact object")
    observed = frozenset(value)
    extra = sorted(observed - keys)
    missing = sorted(keys - observed)
    if extra or missing:
        raise AuthorityError(
            f"{label} has extra or missing fields",
            context={"extra": extra, "missing": missing},
        )
    return value


def authenticate_retained_credit_receipt(
    document: Mapping[str, Any], pins: AuthorityPins
) -> RetainedCredit:
    """Decode receipt 258's exact retained-credit contract. Never a count-only set."""

    schema = document.get("schema_version")
    _require_authority(
        schema == SIZING_RECEIPT_SCHEMA,
        "receipt 258 schema version changed",
        {"expected": SIZING_RECEIPT_SCHEMA, "actual": schema},
    )
    ticket = document.get("ticket")
    _require_authority(
        ticket == TICKET_ID,
        "receipt 258 ticket changed",
        {"expected": TICKET_ID, "actual": ticket},
    )
    physical = document.get("physical_inputs")
    if type(physical) is not dict:
        raise AuthorityError("receipt 258 physical inputs are missing")
    credit_block = _authority_object(
        physical.get("retained_credit"),
        label="retained credit",
        keys=RECEIPT_258_RETAINED_CREDIT_KEYS,
    )
    summary = _authority_object(
        credit_block.get("report_summary"),
        label="retained credit report summary",
        keys=RECEIPT_258_REPORT_SUMMARY_KEYS,
    )
    lineage = document.get("lineage")
    if type(lineage) is not dict:
        raise AuthorityError("receipt 258 lineage is missing")
    raw_keys = credit_block.get("keys")
    if type(raw_keys) is not list:
        raise AuthorityError("retained credit keys are not a list")
    keys: list[str] = []
    previous: str | None = None
    for item in raw_keys:
        if type(item) is not str or item == "":
            raise AuthorityError(
                "a retained credit key is not a non-empty string",
                context={"key": item},
            )
        if previous is not None and item <= previous:
            raise AuthorityError(
                "retained credit keys are not strictly unique and ordered",
                context={"previous": previous, "key": item},
            )
        previous = item
        keys.append(item)
    digest = requirement_key_set_sha256(keys)
    declared_digest = _authority_str(
        credit_block.get("key_set_sha256"), label="retained credit key-set digest"
    )
    if not HEX64.match(declared_digest):
        raise AuthorityError("retained credit key-set digest is not sha256")
    _require_authority(
        digest == declared_digest,
        "retained credit key-set digest changed",
        {"expected": digest, "actual": declared_digest},
    )
    lineage_digest = _authority_str(
        lineage.get("retained_archive_key_set_sha256"),
        label="retained credit lineage key-set digest",
    )
    _require_authority(
        digest == lineage_digest,
        "retained credit lineage key-set digest changed",
        {"expected": digest, "actual": lineage_digest},
    )
    valid_keys = _authority_int(
        credit_block.get("valid_requirement_keys"),
        label="retained credit valid requirement keys",
    )
    objects = _authority_int(credit_block.get("objects"), label="retained credit objects")
    unique_bytes = _authority_int(credit_block.get("bytes"), label="retained credit bytes")
    selected_keys = _authority_int(
        credit_block.get("selected_retained_keys"),
        label="retained credit selected keys",
    )
    cost_keys = _authority_int(
        credit_block.get("cost_retained_keys"), label="retained credit cost keys"
    )
    unverified = _authority_int(
        credit_block.get("unverified_objects"),
        label="retained credit unverified objects",
    )
    rejected = _authority_int(
        credit_block.get("rejected_recovered_rows"),
        label="retained credit rejected recovered rows",
    )
    source = _authority_str(credit_block.get("source"), label="retained credit source")
    _require_authority(
        valid_keys == len(keys),
        "retained credit key count changed",
        {"expected": valid_keys, "actual": len(keys)},
    )
    lineage_keys = _authority_int(
        lineage.get("retained_archive_requirement_keys"),
        label="retained credit lineage key count",
    )
    _require_authority(
        lineage_keys == valid_keys,
        "retained credit lineage key count changed",
        {"expected": valid_keys, "actual": lineage_keys},
    )
    coefficient_only = _authority_int(
        lineage.get("coefficient_only_keys_marked_retained"),
        label="coefficient-only retained lineage count",
    )
    _require_authority(
        coefficient_only == 0,
        "coefficient-only keys are marked retained",
        {"actual": coefficient_only},
    )
    physical_objects = _authority_int(
        physical.get("retained_credit_objects"),
        label="physical retained credit objects",
    )
    physical_bytes = _authority_int(
        physical.get("retained_credit_bytes"),
        label="physical retained credit bytes",
    )
    _require_authority(
        physical_objects == objects,
        "retained credit object count changed",
        {"expected": objects, "actual": physical_objects},
    )
    _require_authority(
        physical_bytes == unique_bytes,
        "retained credit bytes changed",
        {"expected": unique_bytes, "actual": physical_bytes},
    )
    _require_authority(
        objects == valid_keys,
        "retained credit objects are aliased",
        {"keys": valid_keys, "objects": objects},
    )
    _require_authority(
        selected_keys + cost_keys == valid_keys,
        "retained credit selected and cost keys do not sum to the key count",
        {
            "selected_retained_keys": selected_keys,
            "cost_retained_keys": cost_keys,
            "valid_requirement_keys": valid_keys,
        },
    )
    _require_authority(
        unverified == 0,
        "retained credit unverified object count changed",
        {"expected": 0, "actual": unverified},
    )
    _require_authority(
        _authority_int(
            summary.get("rejected_retained_row_count"),
            label="report summary rejected retained row count",
        )
        == rejected,
        "retained credit rejected row count changed",
        {"expected": rejected, "actual": summary.get("rejected_retained_row_count")},
    )
    _require_authority(
        _authority_int(
            summary.get("retained_valid_requirement_keys"),
            label="report summary valid requirement keys",
        )
        == valid_keys,
        "retained credit report summary key count changed",
        {"expected": valid_keys, "actual": summary.get("retained_valid_requirement_keys")},
    )
    _require_authority(
        _authority_int(
            summary.get("retained_verified_credit_objects"),
            label="report summary retained objects",
        )
        == objects,
        "retained credit report summary object count changed",
        {"expected": objects, "actual": summary.get("retained_verified_credit_objects")},
    )
    _require_authority(
        _authority_int(
            summary.get("retained_verified_credit_bytes"),
            label="report summary retained bytes",
        )
        == unique_bytes,
        "retained credit report summary bytes changed",
        {"expected": unique_bytes, "actual": summary.get("retained_verified_credit_bytes")},
    )
    _require_authority(
        _authority_int(
            summary.get("unverified_retained_objects"),
            label="report summary unverified objects",
        )
        == unverified,
        "retained credit report summary unverified count changed",
        {"expected": unverified, "actual": summary.get("unverified_retained_objects")},
    )
    _require_authority(
        objects == pins.retained_credit_objects,
        "retained credit object count changed",
        {"expected": pins.retained_credit_objects, "actual": objects},
    )
    _require_authority(
        unique_bytes == pins.retained_credit_bytes,
        "retained credit bytes changed",
        {"expected": pins.retained_credit_bytes, "actual": unique_bytes},
    )
    if pins.receipt_258_sha256 == PRODUCTION_PINS.receipt_258_sha256:
        _require_authority(
            valid_keys == PRODUCTION_PINS.retained_credit_objects
            and objects == PRODUCTION_PINS.retained_credit_objects
            and unique_bytes == PRODUCTION_PINS.retained_credit_bytes
            and selected_keys == PRODUCTION_RETAINED_SELECTED_KEYS
            and cost_keys == PRODUCTION_RETAINED_COST_KEYS
            and unverified == PRODUCTION_RETAINED_UNVERIFIED_OBJECTS
            and rejected == PRODUCTION_RETAINED_REJECTED_ROWS
            and source == RETAINED_CREDIT_SOURCE,
            "production retained credit decomposition changed",
            {
                "keys": valid_keys,
                "objects": objects,
                "bytes": unique_bytes,
                "selected_retained_keys": selected_keys,
                "cost_retained_keys": cost_keys,
                "unverified_objects": unverified,
                "rejected_recovered_rows": rejected,
            },
        )
    return RetainedCredit(
        keys=tuple(keys),
        key_set=frozenset(keys),
        key_set_sha256=digest,
        valid_requirement_keys=valid_keys,
        objects=objects,
        unique_bytes=unique_bytes,
        selected_retained_keys=selected_keys,
        cost_retained_keys=cost_keys,
        unverified_objects=unverified,
    )


def _compact_retained_credit(credit: RetainedCredit) -> dict[str, Any]:
    return {
        "key_set_sha256": credit.key_set_sha256,
        "valid_requirement_keys": credit.valid_requirement_keys,
        "objects": credit.objects,
        "bytes": credit.unique_bytes,
        "selected_retained_keys": credit.selected_retained_keys,
        "cost_retained_keys": credit.cost_retained_keys,
        "unverified_objects": credit.unverified_objects,
    }


def authenticate_compact_retained_credit(
    block: Mapping[str, Any], *, pins: Mapping[str, Any]
) -> dict[str, Any]:
    """Prove the compact v2 retained block on every chain replay."""

    credit = _exact_object(
        block, label="retained_credit", keys=PLAN_RETAINED_CREDIT_KEYS
    )
    digest = _exact_str(credit["key_set_sha256"], label="retained credit key-set digest")
    if HEX64.fullmatch(digest) is None:
        raise UnsafeStateError("retained credit key-set digest is not sha256")
    valid_keys = _exact_int(
        credit["valid_requirement_keys"],
        label="retained credit valid requirement keys",
    )
    objects = _exact_int(credit["objects"], label="retained credit objects")
    unique_bytes = _exact_int(credit["bytes"], label="retained credit bytes")
    selected = _exact_int(
        credit["selected_retained_keys"], label="retained credit selected keys"
    )
    cost = _exact_int(credit["cost_retained_keys"], label="retained credit cost keys")
    unverified = _exact_int(
        credit["unverified_objects"], label="retained credit unverified objects"
    )
    if objects != valid_keys:
        raise UnsafeStateError(
            "retained credit objects are aliased",
            context={"keys": valid_keys, "objects": objects},
        )
    if selected + cost != valid_keys:
        raise UnsafeStateError(
            "retained credit selected and cost keys do not sum to the key count",
            context={
                "selected_retained_keys": selected,
                "cost_retained_keys": cost,
                "valid_requirement_keys": valid_keys,
            },
        )
    if unverified != 0:
        raise UnsafeStateError(
            "retained credit unverified object count changed",
            context={"expected": 0, "actual": unverified},
        )
    expected_objects = _exact_int(
        pins.get("retained_credit_objects"),
        label="persisted retained credit objects",
    )
    expected_bytes = _exact_int(
        pins.get("retained_credit_bytes"),
        label="persisted retained credit bytes",
    )
    if objects != expected_objects:
        raise UnsafeStateError(
            "retained credit object count changed",
            context={"expected": expected_objects, "actual": objects},
        )
    if unique_bytes != expected_bytes:
        raise UnsafeStateError(
            "retained credit bytes changed",
            context={"expected": expected_bytes, "actual": unique_bytes},
        )
    if pins.get("receipt_258_sha256") == PRODUCTION_PINS.receipt_258_sha256 and (
        selected != PRODUCTION_RETAINED_SELECTED_KEYS
        or cost != PRODUCTION_RETAINED_COST_KEYS
        or valid_keys != PRODUCTION_PINS.retained_credit_objects
        or unique_bytes != PRODUCTION_PINS.retained_credit_bytes
    ):
        raise UnsafeStateError(
            "production retained credit decomposition changed",
            context={
                "selected_retained_keys": selected,
                "cost_retained_keys": cost,
                "valid_requirement_keys": valid_keys,
                "bytes": unique_bytes,
            },
        )
    return credit


def _retained_plan_fields(
    key: str,
    retained_objects: Mapping[str, Any],
    *,
    authorized_keys: frozenset[str],
    sample_dir: Path,
    sidecar_dir: Path,
    roots: BoundRoots | None = None,
) -> dict[str, Any]:
    if key not in authorized_keys:
        return {"retained": False}
    entry = retained_objects.get(key)
    if not isinstance(entry, dict) or str(entry.get("status") or "") != "complete":
        raise AuthorityError(
            "a retained credit key is not complete in qualification progress",
            context={"key": key},
        )
    digest = _hex_digest(entry.get("sha256"), label="retained digest")
    sidecar_digest = _hex_digest(
        entry.get("provider_checksum_sha256") or entry.get("provider_checksum"),
        label="retained sidecar digest",
    )
    sidecar_path = Path(str(entry.get("provider_checksum_path") or ""))
    raw_path = sample_dir / digest
    try:
        raw_fd = open_regular_file(sample_dir, raw_path, roots=roots)
    except (UnsafeStateError, OSError) as exc:
        raise AuthorityError(
            "a retained raw source cannot be opened no-follow",
            context={"key": key, "path": str(raw_path)},
        ) from exc
    try:
        raw_digest, raw_size = sha256_fd(raw_fd)
        raw_stat = os.fstat(raw_fd)
    finally:
        os.close(raw_fd)
    if raw_digest != digest:
        raise AuthorityError("a retained raw source digest changed", context={"key": key})
    declared_bytes = _authority_int(
        entry.get("byte_size"),
        label="retained progress byte size",
        minimum=1,
    )
    if declared_bytes != raw_size:
        raise AuthorityError("a retained raw source size changed", context={"key": key})
    sidecar_body = read_authority_file(
        sidecar_path, label="retained sidecar source", root=sidecar_dir, roots=roots
    )
    if sha256_bytes(sidecar_body) != sidecar_digest:
        raise AuthorityError(
            "a retained sidecar source digest changed", context={"key": key}
        )
    checksum = parse_sidecar(sidecar_body, basename=key.rsplit("/", 1)[-1])
    if checksum != digest:
        raise AuthorityError(
            "a retained sidecar does not name its raw digest", context={"key": key}
        )
    return {
        "retained": True,
        "retained_digest": digest,
        "retained_bytes": raw_size,
        "retained_sidecar_digest": sidecar_digest,
        "retained_sidecar_bytes": len(sidecar_body),
        "retained_sidecar_revision": sidecar_digest,
        "retained_raw_source_path": str(raw_path),
        "retained_sidecar_source_path": str(sidecar_path),
        "retained_retrieval_time": str(entry.get("retrieval_time") or ""),
        "retained_source_device": int(raw_stat.st_dev),
        "retained_source_inode": int(raw_stat.st_ino),
    }


def iter_plan_objects(
    paths: AcquisitionPaths,
    pins: AuthorityPins,
    *,
    report: Mapping[str, Any],
    listing: Mapping[str, Any],
    mappings: Sequence[Mapping[str, str]],
    unmapped: Sequence[str],
    lifecycles: Mapping[str, tuple[int, int]],
    cost_objects: Sequence[Mapping[str, Any]],
    inventory_set: Mapping[str, Any],
    retained_credit: RetainedCredit,
    progress: Mapping[str, Any] | None = None,
    roots: BoundRoots | None = None,
    fault: FaultInjector | None = None,
) -> Iterator[PlanObject]:
    detail = dict(dict(report.get("acquisition_manifest") or {}).get("detail") or {})
    retained_objects = dict((progress or {}).get("objects") or {})
    cost_keys = {str(item["key"]) for item in cost_objects}
    authorized_keys = retained_credit.key_set
    seen_authorized: set[str] = set()
    unique_digests: set[str] = set()
    retained_bytes = 0
    selected_retained = 0
    cost_retained = 0

    def _with_retained(
        key: str, payload: dict[str, Any], *, cost: bool
    ) -> dict[str, Any]:
        nonlocal retained_bytes, selected_retained, cost_retained
        fields = _retained_plan_fields(
            key,
            retained_objects,
            authorized_keys=authorized_keys,
            sample_dir=paths.sample_dir,
            sidecar_dir=paths.listing_cache_dir,
            roots=roots,
        )
        if key in authorized_keys:
            if key in seen_authorized:
                raise AuthorityError(
                    "a retained credit key is duplicated in the plan",
                    context={"key": key},
                )
            seen_authorized.add(key)
            if fields.get("retained") is not True:
                raise AuthorityError(
                    "a retained credit key was not labeled retained",
                    context={"key": key},
                )
            digest = str(fields["retained_digest"])
            if digest in unique_digests:
                raise AuthorityError(
                    "retained credit objects are aliased",
                    context={"key": key, "digest": digest},
                )
            unique_digests.add(digest)
            retained_bytes += int(fields["retained_bytes"])
            if cost:
                cost_retained += 1
            else:
                selected_retained += 1
        elif fields.get("retained") is True:
            raise AuthorityError(
                "a plan row is labeled retained without receipt authority",
                context={"key": key},
            )
        payload.update(fields)
        return payload

    last_key: str | None = None
    main_count = 0
    for payload in iter_selected_binance(
        paths.store_root, detail, pins, roots=roots, fault=fault
    ):
        key = str(payload["key"])
        if last_key is not None and key <= last_key:
            raise AuthorityError("selected manifest keys are not strictly unique and ordered")
        if key in cost_keys:
            raise AuthorityError("main manifest and cost keys are not disjoint")
        last_key = key
        main_count += 1
        yield PlanObject(
            PROVIDER_BINANCE,
            key,
            KIND_BINANCE,
            _with_retained(key, dict(payload), cost=False),
        )
    if main_count + len(cost_keys) != pins.combined_objects:
        raise AuthorityError(
            "combined object count changed",
            context={
                "expected": pins.combined_objects,
                "actual": main_count + len(cost_keys),
            },
        )
    for item in cost_objects:
        key = str(item["key"])
        payload = {
            "key": key,
            "family": item["family"],
            "symbol": item["symbol"],
            "listed_bytes": int(item["byte_size"]),
            "economic_interval": item["economic_interval"],
            "sidecar_key": item["sidecar_key"],
            "etag": item["etag"],
            "url": f"{VISION_OBJECT_BASE}/{key}",
            "sidecar_url": f"{VISION_OBJECT_BASE}/{key}.CHECKSUM",
        }
        yield PlanObject(
            PROVIDER_BINANCE,
            key,
            KIND_BINANCE,
            _with_retained(key, payload, cost=True),
        )
    missing = authorized_keys - seen_authorized
    if missing:
        raise AuthorityError(
            "a retained credit key is not in the selected-plus-cost plan",
            context={"missing": sorted(missing)[:8], "missing_count": len(missing)},
        )
    _require_authority(
        len(seen_authorized) == retained_credit.valid_requirement_keys,
        "retained credit key count changed",
        {
            "expected": retained_credit.valid_requirement_keys,
            "actual": len(seen_authorized),
        },
    )
    _require_authority(
        len(unique_digests) == retained_credit.objects,
        "retained credit object count changed",
        {"expected": retained_credit.objects, "actual": len(unique_digests)},
    )
    _require_authority(
        retained_bytes == retained_credit.unique_bytes,
        "retained credit bytes changed",
        {"expected": retained_credit.unique_bytes, "actual": retained_bytes},
    )
    _require_authority(
        selected_retained == retained_credit.selected_retained_keys,
        "retained credit selected key count changed",
        {
            "expected": retained_credit.selected_retained_keys,
            "actual": selected_retained,
        },
    )
    _require_authority(
        cost_retained == retained_credit.cost_retained_keys,
        "retained credit cost key count changed",
        {"expected": retained_credit.cost_retained_keys, "actual": cost_retained},
    )
    if pins.receipt_258_sha256 == PRODUCTION_PINS.receipt_258_sha256:
        _require_authority(
            len(seen_authorized) == PRODUCTION_PINS.retained_credit_objects
            and len(unique_digests) == PRODUCTION_PINS.retained_credit_objects
            and retained_bytes == PRODUCTION_PINS.retained_credit_bytes
            and selected_retained == PRODUCTION_RETAINED_SELECTED_KEYS
            and cost_retained == PRODUCTION_RETAINED_COST_KEYS
            and retained_credit.unverified_objects
            == PRODUCTION_RETAINED_UNVERIFIED_OBJECTS,
            "production retained credit decomposition changed",
            {
                "keys": len(seen_authorized),
                "objects": len(unique_digests),
                "bytes": retained_bytes,
                "selected_retained_keys": selected_retained,
                "cost_retained_keys": cost_retained,
            },
        )
    inventory_digest = ""
    inventory_bytes = 0
    inventory_path = ""
    for item in list(dict(report.get("coinalyze") or {}).get("provenance") or ()):
        if isinstance(item, dict) and str(item.get("path") or "") == COINALYZE_MARKETS_PATH:
            inventory_digest = str(item.get("sha256") or "")
            inventory_bytes = int(item.get("byte_size") or 0)
            inventory_path = str(item.get("content_path") or "")
            break
    yield PlanObject(
        PROVIDER_COINALYZE,
        f"{PROVIDER_COINALYZE}:{COINALYZE_MARKETS_PATH}",
        KIND_COINALYZE_INVENTORY,
        {
            "path": COINALYZE_MARKETS_PATH,
            "url": f"{COINALYZE_BASE}{COINALYZE_MARKETS_PATH}",
            "params": {},
            "accepted_digest": inventory_digest,
            "accepted_bytes": inventory_bytes,
            "accepted_path": inventory_path,
            "accepted_mappings": [dict(item) for item in mappings],
            "inventory_mapping_digest": str(inventory_set["digest"]),
            "inventory_mapping_count": int(inventory_set["count"]),
        },
    )
    if 1 + len(mappings) != pins.coinalyze_logical_receipts:
        raise AuthorityError("Coinalyze logical receipt count changed")
    for mapping in mappings:
        native = mapping["native_symbol"]
        provider = mapping["provider_symbol"]
        first, last = lifecycles[native]
        params = {
            "symbols": provider,
            "interval": COINALYZE_INTERVAL_DAILY,
            "from": str(_ordinal_to_unix(first)),
            "to": str(_ordinal_to_unix(last)),
            "convert_to_usd": "false",
        }
        query = urlencode(params)
        identity = f"{COINALYZE_LIQUIDATION_PATH}?{query}"
        yield PlanObject(
            PROVIDER_COINALYZE,
            identity,
            KIND_COINALYZE_LIQUIDATION,
            {
                "path": COINALYZE_LIQUIDATION_PATH,
                "native_symbol": native,
                "provider_symbol": provider,
                "params": params,
                "query": query,
                "url": f"{COINALYZE_BASE}{COINALYZE_LIQUIDATION_PATH}",
            },
        )
    for native in unmapped:
        yield PlanObject(
            PROVIDER_COINALYZE,
            f"unsupported:{native}",
            KIND_COINALYZE_UNSUPPORTED,
            {"native_symbol": native, "kind": GAP_UNSUPPORTED},
        )


def plan_entry_bytes(obj: PlanObject) -> bytes:
    return compact_json(
        {
            "provider": obj.provider,
            "identity": obj.identity,
            "kind": obj.kind,
            "payload": dict(obj.payload),
        }
    )



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


def _pins_document(pins: AuthorityPins) -> dict[str, Any]:
    return {
        "report_sha256": pins.report_sha256,
        "manifest_compressed_sha256": pins.manifest_compressed_sha256,
        "manifest_uncompressed_sha256": pins.manifest_uncompressed_sha256,
        "cost_manifest_sha256": pins.cost_manifest_sha256,
        "receipt_258_sha256": pins.receipt_258_sha256,
        "attestation_282_sha256": pins.attestation_282_sha256,
        "listing_checkpoint_sha256": pins.listing_checkpoint_sha256,
        "contract_metadata_sha256": pins.contract_metadata_sha256,
        "lock_sha256": pins.lock_sha256,
        "amendment_ledger_sha256": pins.amendment_ledger_sha256,
        "progress_sha256": pins.progress_sha256,
        "qualification_source_sha256": pins.qualification_source_sha256,
        "qualification_cli_sha256": pins.qualification_cli_sha256,
        "capacity_source_sha256": pins.capacity_source_sha256,
        "capacity_cli_sha256": pins.capacity_cli_sha256,
        "holdout_boundary_id": pins.holdout_boundary_id,
        "main_selected_objects": pins.main_selected_objects,
        "main_selected_bytes": pins.main_selected_bytes,
        "cost_objects": pins.cost_objects,
        "cost_bytes": pins.cost_bytes,
        "combined_objects": pins.combined_objects,
        "combined_bytes": pins.combined_bytes,
        "retained_credit_objects": pins.retained_credit_objects,
        "retained_credit_bytes": pins.retained_credit_bytes,
        "coinalyze_supported": pins.coinalyze_supported,
        "coinalyze_unsupported": pins.coinalyze_unsupported,
        "coinalyze_logical_receipts": pins.coinalyze_logical_receipts,
        "new_binance_raw_bytes": pins.new_binance_raw_bytes,
        "new_coinalyze_raw_bytes": pins.new_coinalyze_raw_bytes,
        "stable_requirement_bytes": pins.stable_requirement_bytes,
        "destination": pins.destination,
        "device": pins.device,
    }


def _canonical_json_ok(text: Any, mode: Any) -> int:
    """1 when ``text`` is exactly the accepted canonical serialisation of its value."""

    if not isinstance(text, str):
        return 0
    try:
        document = json.loads(text)
    except (ValueError, TypeError):
        return 0
    try:
        if str(mode) == "indent":
            return 1 if canonical_json(document).decode("utf-8") == text else 0
        return 1 if compact_json(document).decode("utf-8") == text else 0
    except (ValueError, TypeError):
        return 0


def _utc_timestamp_ok(text: Any) -> int:
    """1 when ``text`` is an exact round-tripping UTC ISO-8601 instant."""

    if not isinstance(text, str):
        return 0
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return 0
    offset = moment.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        return 0
    return 1 if moment.isoformat() == text else 0


def register_domain_functions(conn: sqlite3.Connection) -> None:
    conn.create_function("cf_canonical_json", 2, _canonical_json_ok, deterministic=True)
    conn.create_function("cf_utc_timestamp", 1, _utc_timestamp_ok, deterministic=True)


def _normalize_sql(text: str) -> str:
    return " ".join(str(text or "").split())


def _expected_schema() -> dict[tuple[str, str], str]:
    expected: dict[tuple[str, str], str] = {}
    for statement in SCHEMA_SQL.split(";"):
        body = statement.strip()
        if not body:
            continue
        head = body.split("(", 1)[0].split()
        kind = head[1].lower()
        name = head[2] if kind == "table" else head[2]
        expected[(kind, name)] = _normalize_sql(body)
    return expected


EXPECTED_SCHEMA: dict[tuple[str, str], str] = _expected_schema()

DOMAIN_CHECKS: tuple[tuple[str, str], ...] = (
    (
        "plan_entry has an unknown provider or kind",
        "SELECT 1 FROM plan_entry WHERE provider NOT IN "
        f"('{PROVIDER_BINANCE}', '{PROVIDER_COINALYZE}') OR kind NOT IN "
        f"('{KIND_BINANCE}', '{KIND_COINALYZE_INVENTORY}', "
        f"'{KIND_COINALYZE_LIQUIDATION}', '{KIND_COINALYZE_UNSUPPORTED}') LIMIT 1",
    ),
    (
        "a completion digest is not a lowercase SHA-256",
        "SELECT 1 FROM completion WHERE length(content_sha256) != 64 OR "
        "content_sha256 GLOB '*[^0-9a-f]*' LIMIT 1",
    ),
    (
        "a completion has negative or non-integer bytes",
        "SELECT 1 FROM completion WHERE typeof(listed_bytes) != 'integer' "
        "OR listed_bytes < 0 LIMIT 1",
    ),
    (
        "a completion has an unknown validation state",
        "SELECT 1 FROM completion WHERE validation_state NOT IN "
        f"('{OUTCOME_CHECKSUM_VERIFIED}', '{OUTCOME_EMPTY_HISTORY}', "
        f"'{OUTCOME_UNAVAILABLE}', '{OUTCOME_RETAINED_INVENTORY}', "
        f"'{OUTCOME_RETAINED}') LIMIT 1",
    ),
    (
        "a Binance completion has no sidecar fact",
        "SELECT 1 FROM completion WHERE provider = "
        f"'{PROVIDER_BINANCE}' AND (sidecar_sha256 IS NULL OR sidecar_path IS NULL "
        "OR length(sidecar_sha256) != 64) LIMIT 1",
    ),
    (
        "a sidecar fact is not a lowercase SHA-256 pair",
        "SELECT 1 FROM sidecar_fact WHERE length(sidecar_sha256) != 64 OR "
        "sidecar_sha256 GLOB '*[^0-9a-f]*' OR length(provider_checksum) != 64 OR "
        "provider_checksum GLOB '*[^0-9a-f]*' OR typeof(sidecar_bytes) != 'integer' "
        "OR sidecar_bytes <= 0 LIMIT 1",
    ),
    (
        "a Binance completion carries a Coinalyze outcome",
        "SELECT 1 FROM completion WHERE provider = "
        f"'{PROVIDER_BINANCE}' AND validation_state NOT IN "
        f"('{OUTCOME_CHECKSUM_VERIFIED}', '{OUTCOME_RETAINED}') LIMIT 1",
    ),
    (
        "a Coinalyze completion carries a Binance outcome",
        "SELECT 1 FROM completion WHERE provider = "
        f"'{PROVIDER_COINALYZE}' AND validation_state NOT IN "
        f"('{OUTCOME_CHECKSUM_VERIFIED}', '{OUTCOME_EMPTY_HISTORY}', "
        f"'{OUTCOME_UNAVAILABLE}', '{OUTCOME_RETAINED_INVENTORY}') LIMIT 1",
    ),
    (
        "a terminal gap has an unknown kind",
        f"SELECT 1 FROM terminal_gap WHERE kind != '{GAP_UNSUPPORTED}' LIMIT 1",
    ),
    (
        "an attempt has an unknown classification",
        "SELECT 1 FROM attempt WHERE class NOT IN "
        f"('{RETRY_OK}', '{RETRY_TRANSIENT}', '{RETRY_RATE_LIMIT}', "
        f"'{RETRY_TERMINAL}', '{RETRY_TRANSPORT}') LIMIT 1",
    ),
    (
        "a Coinalyze charge digest is not a lowercase SHA-256",
        "SELECT 1 FROM coinalyze_charge WHERE length(content_sha256) != 64 OR "
        "content_sha256 GLOB '*[^0-9a-f]*' LIMIT 1",
    ),
    (
        "a Coinalyze charge belongs to a non-Coinalyze plan row",
        "SELECT 1 FROM coinalyze_charge WHERE provider != "
        f"'{PROVIDER_COINALYZE}' LIMIT 1",
    ),
    (
        "the Coinalyze ledger is not a single non-negative row",
        "SELECT 1 FROM coinalyze_ledger WHERE id != 1 OR typeof(charged) != 'integer' "
        "OR charged < 0 LIMIT 1",
    ),
    (
        "a Coinalyze charge is not joined to a liquidation plan row",
        "SELECT 1 FROM coinalyze_charge ch LEFT JOIN plan_entry p "
        "ON p.provider = ch.provider AND p.identity = ch.identity "
        f"WHERE p.kind IS NULL OR p.kind != '{KIND_COINALYZE_LIQUIDATION}' LIMIT 1",
    ),
    (
        "an attempt is not joined to a plan row",
        "SELECT 1 FROM attempt a LEFT JOIN plan_entry p "
        "ON p.provider = a.provider AND p.identity = a.identity "
        "WHERE p.identity IS NULL LIMIT 1",
    ),
    (
        "a run_metadata row has an invalid time or counter domain",
        "SELECT 1 FROM run_metadata WHERE cf_utc_timestamp(started_at) = 0 "
        "OR (ended_at IS NOT NULL AND cf_utc_timestamp(ended_at) = 0) "
        "OR typeof(attempt_hi) != 'integer' OR attempt_hi < 0 "
        "OR typeof(network_calls) != 'integer' OR network_calls < 0 LIMIT 1",
    ),
    (
        "a Coinalyze charge HTTP status is not an accepted recovery status",
        "SELECT 1 FROM coinalyze_charge WHERE http_status NOT IN (200, 404) LIMIT 1",
    ),
    (
        "a Coinalyze 404 charge is not provider-unavailable",
        f"SELECT 1 FROM coinalyze_charge WHERE http_status = 404 AND "
        f"(outcome != '{OUTCOME_UNAVAILABLE}' OR points != 0) LIMIT 1",
    ),
    (
        "a Coinalyze 200 charge has an invalid outcome",
        "SELECT 1 FROM coinalyze_charge WHERE http_status = 200 AND outcome NOT IN "
        f"('{OUTCOME_CHECKSUM_VERIFIED}', '{OUTCOME_EMPTY_HISTORY}') LIMIT 1",
    ),
    (
        "a Coinalyze request proof is not a lowercase SHA-256",
        "SELECT 1 FROM coinalyze_charge WHERE length(request_proof) != 64 OR "
        "request_proof GLOB '*[^0-9a-f]*' LIMIT 1",
    ),
    (
        "a charge transition has an unknown status",
        "SELECT 1 FROM charge_transition WHERE status NOT IN "
        f"('{CHARGE_RESERVED}', '{CHARGE_PUBLISHED}', '{CHARGE_SETTLED}', "
        f"'{CHARGE_RELEASED}') LIMIT 1",
    ),
    (
        "the seal head receipt identity is not a lowercase SHA-256",
        "SELECT 1 FROM seal_head WHERE length(receipt_sha256) != 64 OR "
        "receipt_sha256 GLOB '*[^0-9a-f]*' OR length(prefix_digest) != 64 OR "
        "prefix_digest GLOB '*[^0-9a-f]*' LIMIT 1",
    ),
    (
        "a trusted JSON document is not valid JSON",
        "SELECT 1 FROM plan_entry WHERE cf_canonical_json(payload_json, 'compact') = 0 LIMIT 1",
    ),
    (
        "a completion revision is not valid JSON",
        "SELECT 1 FROM completion WHERE cf_canonical_json(revision_json, 'compact') = 0 LIMIT 1",
    ),
    (
        "an attempt fact is not valid JSON",
        "SELECT 1 FROM attempt WHERE cf_canonical_json(redacted_fact_json, 'compact') = 0 LIMIT 1",
    ),
    (
        "a charge retrieval or revision is not valid JSON",
        "SELECT 1 FROM coinalyze_charge WHERE cf_canonical_json(retrieval_json, 'compact') = 0 "
        "OR cf_canonical_json(revision_json, 'compact') = 0 LIMIT 1",
    ),
    (
        "a gap fact is not valid JSON",
        "SELECT 1 FROM terminal_gap WHERE cf_canonical_json(fact_json, 'compact') = 0 LIMIT 1",
    ),
    (
        "authority pins or code are not valid JSON",
        "SELECT 1 FROM authority WHERE cf_canonical_json(pins_json, 'indent') = 0 "
        "OR cf_canonical_json(code_json, 'indent') = 0 LIMIT 1",
    ),
    (
        "a completion retrieved_at is not a UTC timestamp",
        "SELECT 1 FROM completion WHERE cf_utc_timestamp(retrieved_at) = 0 LIMIT 1",
    ),
    (
        "an attempt timestamp is not UTC",
        "SELECT 1 FROM attempt WHERE cf_utc_timestamp(started_at) = 0 "
        "OR (ended_at IS NOT NULL AND (cf_utc_timestamp(ended_at) = 0 "
        "OR ended_at < started_at)) LIMIT 1",
    ),
    (
        "a charge created_at is not a UTC timestamp",
        "SELECT 1 FROM coinalyze_charge WHERE cf_utc_timestamp(created_at) = 0 LIMIT 1",
    ),
    (
        "an OK attempt has an unexpected status",
        f"SELECT 1 FROM attempt WHERE class = '{RETRY_OK}' AND status_code NOT IN (200, 404) "
        "LIMIT 1",
    ),
    (
        "seal watermarks are negative",
        "SELECT 1 FROM seal_head WHERE attempt_hi < 0 OR completion_hi < 0 OR sidecar_hi < 0 "
        "OR charge_hi < 0 OR transition_hi < 0 OR run_hi < 0 LIMIT 1",
    ),
    (
        "a charge has no transition",
        "SELECT 1 FROM coinalyze_charge c WHERE NOT EXISTS ("
        "SELECT 1 FROM charge_transition t WHERE t.provider = c.provider "
        "AND t.identity = c.identity AND t.generation = c.generation) LIMIT 1",
    ),
    (
        "a run_seal receipt identity is not a lowercase SHA-256",
        "SELECT 1 FROM run_seal WHERE length(receipt_sha256) != 64 OR "
        "receipt_sha256 GLOB '*[^0-9a-f]*' OR length(predecessor_sha256) != 64 OR "
        "predecessor_sha256 GLOB '*[^0-9a-f]*' OR length(prefix_digest) != 64 OR "
        "prefix_digest GLOB '*[^0-9a-f]*' OR "
        "cf_canonical_json(marks_json, 'compact') = 0 LIMIT 1",
    ),
    (
        "a charge transition has no descriptor generation",
        "SELECT 1 FROM charge_transition t WHERE NOT EXISTS ("
        "SELECT 1 FROM coinalyze_charge c WHERE c.provider = t.provider "
        "AND c.identity = t.identity AND c.generation = t.generation) LIMIT 1",
    ),
    (
        "a Coinalyze charge generation is not contiguous",
        "SELECT 1 FROM coinalyze_charge c WHERE c.generation > 1 AND NOT EXISTS ("
        "SELECT 1 FROM coinalyze_charge p WHERE p.provider = c.provider "
        "AND p.identity = c.identity AND p.generation = c.generation - 1) LIMIT 1",
    ),
    (
        "a superseded Coinalyze charge generation was not released",
        "SELECT 1 FROM coinalyze_charge c WHERE EXISTS ("
        "SELECT 1 FROM coinalyze_charge n WHERE n.provider = c.provider "
        "AND n.identity = c.identity AND n.generation > c.generation) "
        "AND (SELECT t.status FROM charge_transition t WHERE t.provider = c.provider "
        "AND t.identity = c.identity AND t.generation = c.generation "
        f"ORDER BY t.seq DESC LIMIT 1) IS NOT '{CHARGE_RELEASED}' LIMIT 1",
    ),
    (
        "a Coinalyze charge transition order is not legal",
        "SELECT 1 FROM charge_transition t WHERE ("
        "SELECT x.status FROM charge_transition x WHERE x.provider = t.provider "
        "AND x.identity = t.identity AND x.generation = t.generation AND x.seq < t.seq "
        "ORDER BY x.seq DESC LIMIT 1) IS NOT (CASE t.status "
        f"WHEN '{CHARGE_RESERVED}' THEN NULL "
        f"WHEN '{CHARGE_PUBLISHED}' THEN '{CHARGE_RESERVED}' "
        f"WHEN '{CHARGE_SETTLED}' THEN '{CHARGE_PUBLISHED}' "
        f"WHEN '{CHARGE_RELEASED}' THEN '{CHARGE_RESERVED}' END) LIMIT 1",
    ),
    (
        "a charge transition timestamp is not UTC or is out of order",
        "SELECT 1 FROM charge_transition t WHERE cf_utc_timestamp(t.at) = 0 "
        "OR t.at < (SELECT x.at FROM charge_transition x WHERE x.provider = t.provider "
        "AND x.identity = t.identity AND x.generation = t.generation AND x.seq < t.seq "
        "ORDER BY x.seq DESC LIMIT 1) LIMIT 1",
    ),
    (
        "a Coinalyze charge point count is negative",
        "SELECT 1 FROM coinalyze_charge WHERE typeof(points) != 'integer' OR points < 0 "
        "OR typeof(generation) != 'integer' OR generation < 1 LIMIT 1",
    ),
    (
        "a Binance completion has no durable sidecar fact",
        "SELECT 1 FROM completion c WHERE c.provider = "
        f"'{PROVIDER_BINANCE}' AND NOT EXISTS (SELECT 1 FROM sidecar_fact s "
        "WHERE s.provider = c.provider AND s.identity = c.identity) LIMIT 1",
    ),
    (
        "a completion and its sidecar fact disagree",
        "SELECT 1 FROM completion c JOIN sidecar_fact s ON s.provider = c.provider "
        "AND s.identity = c.identity WHERE c.sidecar_sha256 IS NOT s.sidecar_sha256 "
        "OR c.sidecar_path IS NOT s.sidecar_path LIMIT 1",
    ),
    (
        "a sidecar fact belongs to a non-Binance plan row",
        "SELECT 1 FROM sidecar_fact s LEFT JOIN plan_entry p ON p.provider = s.provider "
        f"AND p.identity = s.identity WHERE p.kind IS NULL OR p.kind != '{KIND_BINANCE}' "
        "LIMIT 1",
    ),
    (
        "a terminal gap is not an unsupported plan row",
        "SELECT 1 FROM terminal_gap g LEFT JOIN plan_entry p ON p.provider = g.provider "
        f"AND p.identity = g.identity WHERE p.kind IS NULL "
        f"OR p.kind != '{KIND_COINALYZE_UNSUPPORTED}' LIMIT 1",
    ),
    (
        "a completion is not joined to a schedulable plan row",
        "SELECT 1 FROM completion c LEFT JOIN plan_entry p ON p.provider = c.provider "
        f"AND p.identity = c.identity WHERE p.kind IS NULL "
        f"OR p.kind = '{KIND_COINALYZE_UNSUPPORTED}' LIMIT 1",
    ),
    (
        "a rate-limited attempt does not carry its 429 status",
        f"SELECT 1 FROM attempt WHERE class = '{RETRY_RATE_LIMIT}' "
        "AND status_code IS NOT 429 LIMIT 1",
    ),
    (
        "a transient attempt carries a non-transient status",
        f"SELECT 1 FROM attempt WHERE class = '{RETRY_TRANSIENT}' "
        "AND status_code IS NOT NULL AND status_code < 500 LIMIT 1",
    ),
    (
        "a terminal attempt carries no status",
        f"SELECT 1 FROM attempt WHERE class = '{RETRY_TERMINAL}' "
        "AND status_code IS NULL LIMIT 1",
    ),
    (
        "a transport attempt shares a terminal provider status",
        f"SELECT 1 FROM attempt WHERE class = '{RETRY_TRANSPORT}' "
        "AND status_code IS NOT NULL AND status_code IN (200, 400, 401, 403, 404, "
        "409, 410, 422, 429) LIMIT 1",
    ),
    (
        "a transport attempt is missing its ended timestamp",
        f"SELECT 1 FROM attempt WHERE class = '{RETRY_TRANSPORT}' AND ended_at IS NULL "
        "LIMIT 1",
    ),
    (
        "a Binance plan row carries a Coinalyze kind",
        "SELECT 1 FROM plan_entry WHERE provider = "
        f"'{PROVIDER_BINANCE}' AND kind != '{KIND_BINANCE}' LIMIT 1",
    ),
    (
        "a Coinalyze plan row carries a Binance kind",
        "SELECT 1 FROM plan_entry WHERE provider = "
        f"'{PROVIDER_COINALYZE}' AND kind NOT IN "
        f"('{KIND_COINALYZE_INVENTORY}', '{KIND_COINALYZE_LIQUIDATION}', "
        f"'{KIND_COINALYZE_UNSUPPORTED}') LIMIT 1",
    ),
    (
        "an OK attempt is missing its ended timestamp",
        f"SELECT 1 FROM attempt WHERE class = '{RETRY_OK}' AND ended_at IS NULL LIMIT 1",
    ),
    (
        "a finished run has an invalid stop or counter domain",
        "SELECT 1 FROM run_metadata WHERE ended_at IS NOT NULL AND ("
        "stop_reason IS NULL OR attempt_hi < 0 OR network_calls < 0 "
        "OR ended_at < started_at) LIMIT 1",
    ),
    (
        "a run seal watermark is negative",
        "SELECT 1 FROM run_seal WHERE json_extract(marks_json, '$.attempt_hi') < 0 "
        "OR json_extract(marks_json, '$.completion_hi') < 0 "
        "OR json_extract(marks_json, '$.sidecar_hi') < 0 "
        "OR json_extract(marks_json, '$.charge_hi') < 0 "
        "OR json_extract(marks_json, '$.transition_hi') < 0 "
        "OR json_extract(marks_json, '$.run_hi') < 0 "
        "OR json_extract(marks_json, '$.seal_hi') < 0 LIMIT 1",
    ),
    (
        "a run seal does not name a recorded run",
        "SELECT 1 FROM run_seal s LEFT JOIN run_metadata r ON r.run_id = s.run_id "
        "WHERE r.run_id IS NULL OR r.ended_at IS NULL LIMIT 1",
    ),
    (
        "a run seal does not follow its predecessor seal",
        "SELECT 1 FROM run_seal s WHERE s.seq > (SELECT MIN(seq) FROM run_seal) "
        "AND s.predecessor_sha256 IS NOT (SELECT x.receipt_sha256 FROM run_seal x "
        "WHERE x.seq < s.seq ORDER BY x.seq DESC LIMIT 1) LIMIT 1",
    ),
    (
        "the seal head names a watermark beyond its stream",
        "SELECT 1 FROM seal_head WHERE "
        "attempt_hi > (SELECT COALESCE(MAX(id), 0) FROM attempt) "
        "OR completion_hi > (SELECT COALESCE(MAX(seq), 0) FROM completion) "
        "OR sidecar_hi > (SELECT COALESCE(MAX(seq), 0) FROM sidecar_fact) "
        "OR charge_hi > (SELECT COALESCE(MAX(seq), 0) FROM coinalyze_charge) "
        "OR transition_hi > (SELECT COALESCE(MAX(seq), 0) FROM charge_transition) "
        "OR run_hi > (SELECT COALESCE(MAX(seq), 0) FROM run_metadata) "
        "OR seal_hi > (SELECT COALESCE(MAX(seq), 0) FROM run_seal) LIMIT 1",
    ),
    (
        "the seal head is not a singleton pointer",
        "SELECT 1 FROM seal_head WHERE id != 1 OR seal_hi < 0 "
        "OR (predecessor_sha256 IS NOT NULL AND (length(predecessor_sha256) != 64 "
        "OR predecessor_sha256 GLOB '*[^0-9a-f]*')) LIMIT 1",
    ),
    (
        "the authority created_at is not a UTC timestamp",
        "SELECT 1 FROM authority WHERE cf_utc_timestamp(created_at) = 0 "
        "OR length(plan_receipt_sha256) != 64 "
        "OR plan_receipt_sha256 GLOB '*[^0-9a-f]*' LIMIT 1",
    ),
)


@dataclass(frozen=True, slots=True)
class CompletionFact:
    provider: str
    identity: str
    content_sha256: str
    content_path: str
    sidecar_sha256: str | None
    sidecar_path: str | None
    listed_bytes: int
    retrieved_at: str
    revision: Mapping[str, Any]
    validation_state: str

    def as_row(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "identity": self.identity,
            "content_sha256": self.content_sha256,
            "content_path": self.content_path,
            "sidecar_sha256": self.sidecar_sha256,
            "sidecar_path": self.sidecar_path,
            "listed_bytes": self.listed_bytes,
            "retrieved_at": self.retrieved_at,
            "revision": dict(self.revision),
            "validation_state": self.validation_state,
        }


class AcquisitionState:
    """The exactly authenticated durable progress store.

    Only the coordinator writes. Every trusted table, column, constraint, index, singleton
    row, and row domain is proved before scheduling or verification, so mutating or
    deleting any independently trusted field fails closed before any network activity or
    terminal publication.
    """

    def __init__(
        self,
        path: Path,
        lockfile: Path,
        *,
        roots: BoundRoots | None = None,
        plan_receipt_dir: Path | None = None,
        run_receipt_dir: Path | None = None,
    ) -> None:
        self.path = Path(path)
        self.lockfile = Path(lockfile)
        self.roots = roots
        gate2 = Path(path).parent
        self.plan_receipt_dir = Path(plan_receipt_dir) if plan_receipt_dir is not None else gate2 / "plan_receipts"
        self.run_receipt_dir = Path(run_receipt_dir) if run_receipt_dir is not None else gate2 / "run_receipts"
        self.filesystem: Filesystem | None = None
        self.publication_device: str | None = None
        self._open_run_id: str | None = None
        self._lock = threading.RLock()
        self._fd: int | None = None
        self._sqlite_fd: int | None = None
        self._state_dir_fd: int | None = None
        self._wal_fd: int | None = None
        self._shm_fd: int | None = None
        self._journal_fd: int | None = None
        self._pre_wal_fd: int | None = None
        self._pre_shm_fd: int | None = None
        self._pre_journal_fd: int | None = None
        self.conn: sqlite3.Connection | None = None

    def _open_state_parent(self, *, create: bool) -> tuple[int, str, str]:
        if self.roots is not None:
            lock_dir, lock_name = self.roots.open_parent(self.lockfile, create=create)
            try:
                state_dir, state_name = self.roots.open_parent(self.path, create=create)
            except Exception:
                os.close(lock_dir)
                raise
            os.close(lock_dir)
            return state_dir, state_name, lock_name
        root = self.path.parent
        lock_dir, lock_name = open_parent_dir(root, self.lockfile, create=create)
        try:
            state_dir, state_name = open_parent_dir(root, self.path, create=create)
        finally:
            os.close(lock_dir)
        return state_dir, state_name, lock_name

    def _prove_leaf_regular(self, directory: int, name: str, *, label: str) -> int:
        try:
            fd = os.open(name, os.O_RDWR | os.O_NOFOLLOW, dir_fd=directory)
        except OSError as exc:
            raise UnsafeStateError(f"{label} cannot be opened no-follow") from exc
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise UnsafeStateError(f"{label} is not a regular file")
        except Exception:
            os.close(fd)
            raise
        return fd

    def _require_same_leaf(
        self,
        before: int | None,
        after: int | None,
        *,
        label: str,
        allow_absent_after: bool = False,
    ) -> None:
        """A journal leaf that existed before setup must be the same device and inode."""

        if before is None:
            return
        if after is None:
            if allow_absent_after:
                return
            raise UnsafeStateError(f"{label} leaf disappeared during setup")
        first = os.fstat(before)
        second = os.fstat(after)
        if first.st_ino != second.st_ino or first.st_dev != second.st_dev:
            raise UnsafeStateError(f"{label} leaf was replaced")

    def _prove_sidecar_leaf(self, directory: int, name: str, *, label: str) -> int | None:
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise UnsafeStateError(f"{label} cannot be opened no-follow") from exc
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise UnsafeStateError(f"{label} is not a regular file")
        except Exception:
            os.close(fd)
            raise
        return fd

    # -- lifecycle -----------------------------------------------------------------

    def open(self) -> None:
        try:
            state_dir, state_name, lock_name = self._open_state_parent(create=True)
            self._state_dir_fd = state_dir
            try:
                self._fd = os.open(
                    lock_name,
                    os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=state_dir,
                )
            except OSError as exc:
                raise UnsafeStateError("state lock cannot be opened no-follow") from exc
            if not stat.S_ISREG(os.fstat(self._fd).st_mode):
                raise UnsafeStateError("state lock is not a regular file")
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise UnsafeStateError("another writer holds the acquisition lock") from exc
            try:
                self._sqlite_fd = os.open(
                    state_name,
                    os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=state_dir,
                )
            except OSError as exc:
                raise UnsafeStateError("SQLite state cannot be opened no-follow") from exc
            db_stat = os.fstat(self._sqlite_fd)
            if not stat.S_ISREG(db_stat.st_mode):
                raise UnsafeStateError("SQLite state is not a regular file")
            # Any pre-existing journal leaf is proved no-follow and regular before SQLite
            # can follow it, and is owned by close() from this point on.
            self._pre_wal_fd = self._prove_sidecar_leaf(
                state_dir, f"{state_name}-wal", label="SQLite WAL"
            )
            self._pre_shm_fd = self._prove_sidecar_leaf(
                state_dir, f"{state_name}-shm", label="SQLite SHM"
            )
            self._pre_journal_fd = self._prove_sidecar_leaf(
                state_dir, f"{state_name}-journal", label="SQLite rollback journal"
            )
            uri = f"file:/proc/self/fd/{state_dir}/{state_name}?mode=rw"
            self.conn = sqlite3.connect(
                uri,
                uri=True,
                isolation_level=None,
                check_same_thread=False,
            )
            opened = self._prove_sidecar_leaf(
                state_dir, state_name, label="SQLite state"
            )
            try:
                opened_stat = os.fstat(opened)
                if opened_stat.st_ino != db_stat.st_ino or opened_stat.st_dev != db_stat.st_dev:
                    raise UnsafeStateError("SQLite opened a different state leaf")
            finally:
                if opened is not None:
                    os.close(opened)
            register_domain_functions(self.conn)
            self.conn.execute("PRAGMA foreign_keys=ON")
            journal = str(self.conn.execute("PRAGMA journal_mode=WAL").fetchone()[0])
            if journal.lower() != "wal":
                raise UnsafeStateError(
                    "SQLite journal_mode is not wal",
                    context={"journal_mode": journal},
                )
            self.conn.execute("PRAGMA synchronous=FULL")
            # Materialise the journal so its leaves exist and can be proved now rather
            # than at some later first write.
            self.conn.execute("BEGIN IMMEDIATE")
            self.conn.execute("COMMIT")
            self._wal_fd = self._prove_sidecar_leaf(
                state_dir, f"{state_name}-wal", label="SQLite WAL"
            )
            self._shm_fd = self._prove_sidecar_leaf(
                state_dir, f"{state_name}-shm", label="SQLite SHM"
            )
            self._journal_fd = self._prove_sidecar_leaf(
                state_dir, f"{state_name}-journal", label="SQLite rollback journal"
            )
            if self._wal_fd is None:
                raise UnsafeStateError("SQLite WAL was not created as a regular file")
            self._require_same_leaf(self._pre_wal_fd, self._wal_fd, label="SQLite WAL")
            self._require_same_leaf(self._pre_shm_fd, self._shm_fd, label="SQLite SHM")
            self._require_same_leaf(
                self._pre_journal_fd,
                self._journal_fd,
                label="SQLite rollback journal",
                allow_absent_after=True,
            )
            app = int(self.conn.execute("PRAGMA application_id").fetchone()[0])
            version = int(self.conn.execute("PRAGMA user_version").fetchone()[0])
            tables = [
                str(row[0])
                for row in self.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            empty = not tables
            if app not in {0, STATE_APPLICATION_ID}:
                raise UnsafeStateError("SQLite application_id is not this schema")
            if version not in {0, STATE_USER_VERSION}:
                raise UnsafeStateError("SQLite user_version is not this schema")
            if app == 0 and not empty:
                raise UnsafeStateError("populated SQLite state has no application identity")
            if empty:
                self.conn.executescript(SCHEMA_SQL)
                self.conn.execute(f"PRAGMA application_id={STATE_APPLICATION_ID}")
                self.conn.execute(f"PRAGMA user_version={STATE_USER_VERSION}")
            check = self.conn.execute("PRAGMA integrity_check").fetchone()
            if not check or str(check[0]) != "ok":
                raise UnsafeStateError("SQLite state is corrupt")
            fk = self.conn.execute("PRAGMA foreign_key_check").fetchall()
            if fk:
                raise UnsafeStateError("SQLite foreign keys do not reconcile")
            self.authenticate_schema()
            self.authenticate_domains()
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        errors: list[BaseException] = []

        def _close_fd(attr: str, *, unlock: bool = False) -> None:
            fd = getattr(self, attr)
            if fd is None:
                return
            try:
                if unlock:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception as exc:  # noqa: BLE001 - nested resource cleanup
                errors.append(exc)
            try:
                os.close(fd)
            except Exception as exc:  # noqa: BLE001 - nested resource cleanup
                errors.append(exc)
            setattr(self, attr, None)

        if self.conn is not None:
            try:
                self.conn.close()
            except Exception as exc:  # noqa: BLE001 - nested resource cleanup
                errors.append(exc)
            self.conn = None
        _close_fd("_wal_fd")
        _close_fd("_shm_fd")
        _close_fd("_journal_fd")
        _close_fd("_pre_wal_fd")
        _close_fd("_pre_shm_fd")
        _close_fd("_pre_journal_fd")
        _close_fd("_sqlite_fd")
        _close_fd("_fd", unlock=True)
        _close_fd("_state_dir_fd")
        if errors:
            raise UnsafeStateError(
                "state resources could not be released",
                context={"error": type(errors[0]).__name__},
            ) from errors[0]

    def _db(self) -> sqlite3.Connection:
        if self.conn is None:
            raise UnsafeStateError("state is not open")
        return self.conn

    # -- authentication ------------------------------------------------------------

    def authenticate_schema(self) -> None:
        """Prove the exact accepted tables, columns, constraints, and indexes."""

        rows = self._db().execute(
            "SELECT type, name, sql FROM sqlite_master WHERE type IN "
            "('table','index','view','trigger')"
        ).fetchall()
        observed: dict[tuple[str, str], str] = {}
        for kind, name, sql in rows:
            if str(name).startswith("sqlite_"):
                continue
            observed[(str(kind), str(name))] = _normalize_sql(sql)
        missing = sorted(set(EXPECTED_SCHEMA) - set(observed))
        extra = sorted(set(observed) - set(EXPECTED_SCHEMA))
        if missing:
            raise UnsafeStateError(
                "the state schema is missing an accepted object",
                context={"missing": [f"{kind}:{name}" for kind, name in missing]},
            )
        if extra:
            raise UnsafeStateError(
                "the state schema has an object outside the accepted schema",
                context={"extra": [f"{kind}:{name}" for kind, name in extra]},
            )
        for key, sql in sorted(EXPECTED_SCHEMA.items()):
            if observed[key] != sql:
                raise UnsafeStateError(
                    "an accepted state object was redefined",
                    context={"object": f"{key[0]}:{key[1]}"},
                )

    def authenticate_domains(self) -> None:
        db = self._db()
        for message, sql in DOMAIN_CHECKS:
            if db.execute(sql).fetchone() is not None:
                raise UnsafeStateError(message)

    def authenticate_singletons(self) -> None:
        """Prove the required singleton authority and ledger rows and the ledger equation."""

        db = self._db()
        authority = int(db.execute("SELECT COUNT(*) FROM authority").fetchone()[0])
        if authority != 1:
            raise UnsafeStateError(
                "the singleton authority row is missing or duplicated",
                context={"rows": authority},
            )
        ledger = db.execute("SELECT charged FROM coinalyze_ledger WHERE id=1").fetchone()
        if ledger is None:
            raise UnsafeStateError("the singleton Coinalyze ledger row is missing")
        rows = int(db.execute("SELECT COUNT(*) FROM coinalyze_ledger").fetchone()[0])
        if rows != 1:
            raise UnsafeStateError("the Coinalyze ledger is not a singleton")
        charged = int(ledger[0])
        attributed = int(
            db.execute(
                "SELECT COALESCE(SUM(c.charged_bytes), 0) FROM coinalyze_charge c "
                "WHERE (SELECT t.status FROM charge_transition t "
                "WHERE t.provider = c.provider AND t.identity = c.identity "
                "AND t.generation = c.generation "
                f"ORDER BY t.seq DESC LIMIT 1) IS NOT '{CHARGE_RELEASED}'"
            ).fetchone()[0]
        )
        if charged != attributed:
            raise UnsafeStateError(
                "the Coinalyze ledger does not equal its attributed charges",
                context={"charged": charged, "attributed": attributed},
            )

    # -- plan installation ---------------------------------------------------------

    def has_plan(self) -> bool:
        row = self._db().execute("SELECT 1 FROM authority WHERE id=1").fetchone()
        return row is not None

    def install_or_compare(
        self,
        objects: Iterator[PlanObject],
        *,
        plan_identity: str,
        receipt_sha256: str,
        receipt_path: str,
        pins: AuthorityPins,
        code: Mapping[str, str],
        device: str,
        fault: FaultInjector | None = None,
    ) -> int:
        fault = fault or FaultInjector()
        db = self._db()
        with self._lock:
            existing = db.execute(
                "SELECT plan_identity, plan_receipt_sha256, code_json, destination, device, "
                "pins_json, created_at FROM authority WHERE id=1"
            ).fetchone()
            hasher = hashlib.sha256()
            count = 0
            gap_count = 0
            if existing is None:
                return self._install_fresh(
                    objects,
                    plan_identity=plan_identity,
                    receipt_sha256=receipt_sha256,
                    receipt_path=receipt_path,
                    pins=pins,
                    code=code,
                    device=device,
                    fault=fault,
                )
            if str(existing[0]) != plan_identity:
                raise UnsafeStateError(
                    "existing state belongs to a different plan",
                    context={"existing": existing[0], "new": plan_identity},
                )
            if str(existing[1]) != receipt_sha256:
                raise UnsafeStateError("installed plan receipt identity changed")
            if json.loads(existing[2]) != dict(code):
                raise UnsafeStateError("installed code identity changed")
            if str(existing[3]) != pins.destination or str(existing[4]) != device:
                raise UnsafeStateError("installed destination or device changed")
            if json.loads(str(existing[5])) != _pins_document(pins):
                raise UnsafeStateError("installed pin document changed")
            cursor = db.execute(
                "SELECT provider, identity, kind, payload_json FROM plan_entry ORDER BY seq"
            )
            for obj in objects:
                payload = plan_entry_bytes(obj)
                hasher.update(payload)
                count += 1
                row = cursor.fetchone()
                if row is None:
                    raise UnsafeStateError("installed plan is shorter than the regenerated plan")
                if (str(row[0]), str(row[1]), str(row[2]), str(row[3])) != (
                    obj.provider,
                    obj.identity,
                    obj.kind,
                    payload.decode("utf-8"),
                ):
                    raise UnsafeStateError("installed plan row does not match regenerated plan")
                if obj.kind == KIND_COINALYZE_UNSUPPORTED:
                    gap_count += 1
                    self._require_gap(obj)
            if cursor.fetchone() is not None:
                raise UnsafeStateError("installed plan is longer than the regenerated plan")
            if hasher.hexdigest() != plan_identity:
                raise UnsafeStateError(
                    "regenerated plan identity disagrees with the installed plan"
                )
            installed_gaps = int(db.execute("SELECT COUNT(*) FROM terminal_gap").fetchone()[0])
            if installed_gaps != gap_count:
                raise UnsafeStateError(
                    "the installed unsupported gap set changed",
                    context={"expected": gap_count, "actual": installed_gaps},
                )
            if gap_count != pins.coinalyze_unsupported:
                raise UnsafeStateError(
                    "the accepted unsupported mapping count changed",
                    context={"expected": pins.coinalyze_unsupported, "actual": gap_count},
                )
            self.authenticate_singletons()
            return count

    def _require_gap(self, obj: PlanObject) -> None:
        row = self._db().execute(
            "SELECT kind, fact_json FROM terminal_gap WHERE provider=? AND identity=?",
            (obj.provider, obj.identity),
        ).fetchone()
        if row is None:
            raise UnsafeStateError(
                "an accepted unsupported gap row is missing",
                context={"identity": obj.identity},
            )
        if str(row[0]) != GAP_UNSUPPORTED or str(row[1]) != compact_json(
            dict(obj.payload)
        ).decode("utf-8"):
            raise UnsafeStateError(
                "an accepted unsupported gap fact changed",
                context={"identity": obj.identity},
            )

    def _install_fresh(
        self,
        objects: Iterator[PlanObject],
        *,
        plan_identity: str,
        receipt_sha256: str,
        receipt_path: str,
        pins: AuthorityPins,
        code: Mapping[str, str],
        device: str,
        fault: FaultInjector,
    ) -> int:
        db = self._db()
        hasher = hashlib.sha256()
        count = 0
        gap_count = 0
        db.execute("BEGIN IMMEDIATE")
        try:
            created_at = datetime.now(UTC).isoformat()
            db.execute(
                "INSERT INTO authority(id, plan_identity, plan_receipt_sha256, pins_json, "
                "code_json, destination, device, created_at) VALUES (1, ?, ?, ?, ?, ?, ?, ?)",
                (
                    plan_identity,
                    receipt_sha256,
                    canonical_json(_pins_document(pins)).decode("utf-8"),
                    canonical_json(dict(code)).decode("utf-8"),
                    pins.destination,
                    device,
                    created_at,
                ),
            )
            db.execute("INSERT INTO coinalyze_ledger(id, charged) VALUES (1, 0)")
            batch: list[tuple[str, str, str, str]] = []
            gaps: list[tuple[str, str, str, str]] = []

            def _flush() -> None:
                # Every referenced plan row is inserted before the gap that references it,
                # inside the same all-or-nothing transaction, so the immediate foreign key
                # of the first unsupported mapping can never fail on a fresh plan.
                if batch:
                    db.executemany(
                        "INSERT INTO plan_entry(provider, identity, kind, payload_json) "
                        "VALUES (?, ?, ?, ?)",
                        batch,
                    )
                    batch.clear()
                if gaps:
                    db.executemany(
                        "INSERT INTO terminal_gap(provider, identity, kind, fact_json) "
                        "VALUES (?, ?, ?, ?)",
                        gaps,
                    )
                    gaps.clear()

            for obj in objects:
                payload = plan_entry_bytes(obj)
                hasher.update(payload)
                count += 1
                batch.append((obj.provider, obj.identity, obj.kind, payload.decode("utf-8")))
                if obj.kind == KIND_COINALYZE_UNSUPPORTED:
                    gap_count += 1
                    gaps.append(
                        (
                            obj.provider,
                            obj.identity,
                            GAP_UNSUPPORTED,
                            compact_json(dict(obj.payload)).decode("utf-8"),
                        )
                    )
                if len(batch) >= CURSOR_BATCH:
                    _flush()
                    fault.check("after_plan_batch", str(count))
            _flush()
            fault.check("after_plan_flush", str(count))
            actual = hasher.hexdigest()
            if actual != plan_identity:
                raise UnsafeStateError("streamed plan identity disagrees with the receipt")
            if gap_count != pins.coinalyze_unsupported:
                raise UnsafeStateError(
                    "the accepted unsupported mapping count changed",
                    context={"expected": pins.coinalyze_unsupported, "actual": gap_count},
                )
            prefix = self._prefix_digest_unlocked(self._zero_watermarks())
            db.execute(
                "INSERT INTO seal_head(id, receipt_sha256, receipt_path, prefix_digest, "
                "attempt_hi, completion_hi, sidecar_hi, charge_hi, transition_hi, run_hi, "
                "seal_hi, predecessor_sha256) VALUES (1, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, NULL)",
                (receipt_sha256, str(receipt_path), prefix),
            )
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
        return count

    # -- durable facts -------------------------------------------------------------

    def record_attempt(
        self,
        provider: str,
        identity: str,
        classification: str,
        *,
        status_code: int | None,
        fact: Mapping[str, Any],
        started_at: str | None = None,
        ended_at: str | None = None,
    ) -> None:
        db = self._db()
        now = datetime.now(UTC).isoformat()
        with self._lock:
            owned = db.execute(
                "SELECT 1 FROM plan_entry WHERE provider=? AND identity=?",
                (provider, identity),
            ).fetchone()
            if owned is None:
                raise UnsafeStateError(
                    "an attempt is not joined to a plan row",
                    context={"provider": provider, "identity": identity},
                )
            db.execute(
                "INSERT INTO attempt(provider, identity, started_at, ended_at, class, "
                "status_code, redacted_fact_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    provider,
                    identity,
                    started_at or now,
                    ended_at or now,
                    classification,
                    status_code,
                    compact_json(dict(fact)).decode("utf-8"),
                ),
            )

    def record_sidecar(
        self,
        provider: str,
        identity: str,
        digest: str,
        path: Path,
        checksum: str,
        *,
        sidecar_bytes: int,
    ) -> None:
        db = self._db()
        with self._lock:
            existing = db.execute(
                "SELECT sidecar_sha256, sidecar_path, provider_checksum, sidecar_bytes "
                "FROM sidecar_fact WHERE provider=? AND identity=?",
                (provider, identity),
            ).fetchone()
            if existing is not None:
                if (
                    str(existing[0]) != digest
                    or str(existing[1]) != str(path)
                    or str(existing[2]) != checksum
                    or int(existing[3]) != int(sidecar_bytes)
                ):
                    raise UnsafeStateError(
                        "sidecar fact revision conflict", context={"identity": identity}
                    )
                return
            db.execute(
                "INSERT INTO sidecar_fact(provider, identity, sidecar_sha256, sidecar_path, "
                "sidecar_bytes, provider_checksum) VALUES (?, ?, ?, ?, ?, ?)",
                (provider, identity, digest, str(path), int(sidecar_bytes), checksum),
            )

    def sidecar_fact(self, provider: str, identity: str) -> dict[str, Any] | None:
        row = self._db().execute(
            "SELECT sidecar_sha256, sidecar_path, provider_checksum, sidecar_bytes "
            "FROM sidecar_fact WHERE provider=? AND identity=?",
            (provider, identity),
        ).fetchone()
        if row is None:
            return None
        return {
            "sidecar_sha256": str(row[0]),
            "sidecar_path": str(row[1]),
            "provider_checksum": str(row[2]),
            "sidecar_bytes": int(row[3]),
        }

    def complete(
        self,
        provider: str,
        identity: str,
        *,
        content_sha256: str,
        content_path: Path,
        sidecar_sha256: str | None,
        sidecar_path: Path | None,
        listed_bytes: int,
        retrieved_at: str,
        revision: Mapping[str, Any],
        validation_state: str,
        fault: FaultInjector,
        settle_charge: bool = False,
    ) -> None:
        """Insert one immutable completion; every field is insert-once and monotone."""

        db = self._db()
        fault.check("before_db_commit", identity)
        with self._lock:
            existing = self.completion_fact(provider, identity)
            if existing is not None:
                same = (
                    existing.content_sha256 == content_sha256
                    and existing.content_path == str(content_path)
                    and existing.sidecar_sha256 == sidecar_sha256
                    and existing.sidecar_path
                    == (str(sidecar_path) if sidecar_path is not None else None)
                    and existing.listed_bytes == int(listed_bytes)
                    and existing.retrieved_at == retrieved_at
                    and dict(existing.revision) == dict(revision)
                    and existing.validation_state == validation_state
                )
                if not same:
                    raise UnsafeStateError(
                        "completion revision conflict", context={"identity": identity}
                    )
                return
            db.execute("BEGIN IMMEDIATE")
            try:
                if settle_charge:
                    row = db.execute(
                        "SELECT generation, content_sha256, charged_bytes "
                        "FROM coinalyze_charge WHERE provider=? AND identity=? "
                        "ORDER BY generation DESC LIMIT 1",
                        (provider, identity),
                    ).fetchone()
                    if row is None:
                        raise UnsafeStateError(
                            "a Coinalyze completion has no attributed charge",
                            context={"identity": identity},
                        )
                    generation = int(row[0])
                    if str(row[1]) != content_sha256 or int(row[2]) != int(listed_bytes):
                        raise UnsafeStateError(
                            "a Coinalyze charge does not match its completion",
                            context={"identity": identity},
                        )
                    latest = self.charge_status(provider, identity, generation)
                    if latest == CHARGE_SETTLED:
                        raise UnsafeStateError(
                            "a settled Coinalyze charge has no completion",
                            context={"identity": identity},
                        )
                    if latest != CHARGE_PUBLISHED:
                        raise UnsafeStateError(
                            "a Coinalyze charge cannot settle from a reservation",
                            context={"identity": identity, "status": latest},
                        )
                    db.execute(
                        "INSERT INTO charge_transition(provider, identity, generation, "
                        "status, at) VALUES (?, ?, ?, ?, ?)",
                        (
                            provider,
                            identity,
                            generation,
                            CHARGE_SETTLED,
                            datetime.now(UTC).isoformat(),
                        ),
                    )
                db.execute(
                    "INSERT INTO completion(provider, identity, content_sha256, content_path, "
                    "sidecar_sha256, sidecar_path, listed_bytes, retrieved_at, revision_json, "
                    "validation_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        provider,
                        identity,
                        content_sha256,
                        str(content_path),
                        sidecar_sha256,
                        str(sidecar_path) if sidecar_path is not None else None,
                        int(listed_bytes),
                        retrieved_at,
                        compact_json(dict(revision)).decode("utf-8"),
                        validation_state,
                    ),
                )
                db.execute("COMMIT")
            except Exception:
                db.execute("ROLLBACK")
                raise
        fault.check("after_db_commit", identity)

    # -- Coinalyze budget transition ------------------------------------------------

    def coinalyze_remaining(self, ceiling: int) -> int:
        """Remaining accepted allocation proved from the singleton ledger."""

        self.authenticate_singletons()
        charged = int(
            self._db().execute("SELECT charged FROM coinalyze_ledger WHERE id=1").fetchone()[0]
        )
        remaining = int(ceiling) - charged
        if remaining < 0:
            raise UnsafeStateError(
                "the Coinalyze ledger is over the accepted allocation ceiling",
                context={"ceiling": int(ceiling), "charged": charged},
            )
        return remaining

    def charge_generation(self, provider: str, identity: str) -> int:
        """The newest immutable charge generation for one request identity."""

        row = self._db().execute(
            "SELECT COALESCE(MAX(generation), 0) FROM coinalyze_charge "
            "WHERE provider=? AND identity=?",
            (provider, identity),
        ).fetchone()
        return int(row[0])

    def charge_status(
        self, provider: str, identity: str, generation: int | None = None
    ) -> str | None:
        if generation is None:
            generation = self.charge_generation(provider, identity)
        if not generation:
            return None
        row = self._db().execute(
            "SELECT status FROM charge_transition WHERE provider=? AND identity=? "
            "AND generation=? ORDER BY seq DESC LIMIT 1",
            (provider, identity, int(generation)),
        ).fetchone()
        return None if row is None else str(row[0])

    def open_charge(
        self, provider: str, identity: str, generation: int | None = None
    ) -> dict[str, Any] | None:
        """One generation descriptor with its derived transition state.

        ``generation`` defaults to the newest identity generation. Recovery batches pass
        the exact generation so a released-then-retried identity cannot appear twice.
        """

        if generation is None:
            row = self._db().execute(
                "SELECT generation, content_sha256, charged_bytes, http_status, outcome, points, "
                "request_proof, retrieval_json, revision_json, created_at FROM coinalyze_charge "
                "WHERE provider=? AND identity=? ORDER BY generation DESC LIMIT 1",
                (provider, identity),
            ).fetchone()
        else:
            row = self._db().execute(
                "SELECT generation, content_sha256, charged_bytes, http_status, outcome, points, "
                "request_proof, retrieval_json, revision_json, created_at FROM coinalyze_charge "
                "WHERE provider=? AND identity=? AND generation=?",
                (provider, identity, int(generation)),
            ).fetchone()
        if row is None:
            return None
        generation = int(row[0])
        return {
            "provider": provider,
            "identity": identity,
            "generation": generation,
            "content_sha256": str(row[1]),
            "charged_bytes": int(row[2]),
            "status": self.charge_status(provider, identity, generation),
            "http_status": int(row[3]),
            "outcome": str(row[4]),
            "points": int(row[5]),
            "request_proof": str(row[6]),
            "retrieval": json.loads(str(row[7])),
            "revision": json.loads(str(row[8])),
            "created_at": str(row[9]),
        }

    def open_charge_batch(self, after: int, limit: int = CURSOR_BATCH) -> list[dict[str, Any]]:
        """One bounded batch of unsettled charge generations after ``after``.

        Each reserved or published generation is selected once. A released generation is
        never resolved to a later retry of the same identity.
        """

        rows = self._db().execute(
            "SELECT c.seq, c.provider, c.identity, c.generation FROM coinalyze_charge c "
            "WHERE c.seq > ? AND (SELECT t.status FROM charge_transition t "
            "WHERE t.provider = c.provider AND t.identity = c.identity "
            "AND t.generation = c.generation ORDER BY t.seq DESC LIMIT 1) IN (?, ?) "
            "ORDER BY c.seq LIMIT ?",
            (int(after), CHARGE_RESERVED, CHARGE_PUBLISHED, int(limit)),
        ).fetchall()
        BOUND_TELEMETRY.note("max_cursor_rows", len(rows))
        batch: list[dict[str, Any]] = []
        for seq, provider, identity, generation in rows:
            item = self.open_charge(
                str(provider), str(identity), generation=int(generation)
            )
            if item is None:
                batch.append({"seq": int(seq)})
                continue
            batch.append({"seq": int(seq), **item})
        return batch

    def iter_open_charges(self) -> Iterator[dict[str, Any]]:
        after = 0
        while True:
            rows = self._db().execute(
                "SELECT c.seq, c.provider, c.identity, c.generation FROM coinalyze_charge c "
                "WHERE c.seq > ? AND (SELECT t.status FROM charge_transition t "
                "WHERE t.provider = c.provider AND t.identity = c.identity "
                "AND t.generation = c.generation ORDER BY t.seq DESC LIMIT 1) IN (?, ?) "
                "ORDER BY c.seq LIMIT ?",
                (after, CHARGE_RESERVED, CHARGE_PUBLISHED, CURSOR_BATCH),
            ).fetchall()
            if not rows:
                return
            BOUND_TELEMETRY.note("max_cursor_rows", len(rows))
            for seq, provider, identity, generation in rows:
                after = int(seq)
                item = self.open_charge(
                    str(provider), str(identity), generation=int(generation)
                )
                if item is None:
                    continue
                yield item

    def reserve_charge(
        self,
        provider: str,
        identity: str,
        *,
        content_sha256: str,
        charged_bytes: int,
        ceiling: int,
        fault: FaultInjector,
        http_status: int,
        outcome: str,
        points: int,
        request_proof: str,
        retrieval: Mapping[str, Any],
        revision: Mapping[str, Any],
    ) -> None:
        """Charge one accepted body exactly once, atomically with the ledger equation.

        The reservation persists the complete validated recovery descriptor before
        publication, so a crash recovers the original HTTP status and outcome rather
        than re-parsing every body as 200.
        """

        db = self._db()
        with self._lock:
            owned = db.execute(
                "SELECT kind FROM plan_entry WHERE provider=? AND identity=?",
                (provider, identity),
            ).fetchone()
            if owned is None or str(owned[0]) != KIND_COINALYZE_LIQUIDATION:
                raise UnsafeStateError(
                    "a Coinalyze charge is not joined to a liquidation plan row",
                    context={"identity": identity},
                )
            db.execute("BEGIN IMMEDIATE")
            try:
                ledger = db.execute(
                    "SELECT charged FROM coinalyze_ledger WHERE id=1"
                ).fetchone()
                if ledger is None:
                    raise UnsafeStateError("the singleton Coinalyze ledger row is missing")
                charged = int(ledger[0])
                attributed = int(
                    db.execute(
                        "SELECT COALESCE(SUM(c.charged_bytes), 0) FROM coinalyze_charge c "
                        "WHERE (SELECT t.status FROM charge_transition t "
                        "WHERE t.provider = c.provider AND t.identity = c.identity "
                        "AND t.generation = c.generation "
                        f"ORDER BY t.seq DESC LIMIT 1) IS NOT '{CHARGE_RELEASED}'"
                    ).fetchone()[0]
                )
                if charged != attributed:
                    raise UnsafeStateError(
                        "the Coinalyze ledger does not equal its attributed charges",
                        context={"charged": charged, "attributed": attributed},
                    )
                generation = int(
                    db.execute(
                        "SELECT COALESCE(MAX(generation), 0) FROM coinalyze_charge "
                        "WHERE provider=? AND identity=?",
                        (provider, identity),
                    ).fetchone()[0]
                )
                if generation:
                    latest = db.execute(
                        "SELECT status FROM charge_transition WHERE provider=? AND identity=? "
                        "AND generation=? ORDER BY seq DESC LIMIT 1",
                        (provider, identity, generation),
                    ).fetchone()
                    if latest is None:
                        raise UnsafeStateError(
                            "a Coinalyze charge generation has no transition",
                            context={"identity": identity},
                        )
                    if str(latest[0]) != CHARGE_RELEASED:
                        existing = db.execute(
                            "SELECT content_sha256, charged_bytes, http_status, outcome, "
                            "points, request_proof, retrieval_json, revision_json "
                            "FROM coinalyze_charge WHERE provider=? AND identity=? "
                            "AND generation=?",
                            (provider, identity, generation),
                        ).fetchone()
                        same = (
                            str(existing[0]) == content_sha256
                            and int(existing[1]) == int(charged_bytes)
                            and int(existing[2]) == int(http_status)
                            and str(existing[3]) == outcome
                            and int(existing[4]) == int(points)
                            and str(existing[5]) == request_proof
                            and str(existing[6])
                            == compact_json(dict(retrieval)).decode("utf-8")
                            and str(existing[7])
                            == compact_json(dict(revision)).decode("utf-8")
                        )
                        if not same:
                            raise UnsafeStateError(
                                "a Coinalyze charge revision conflict",
                                context={"identity": identity},
                            )
                        db.execute("COMMIT")
                        return
                    # The previous generation was refunded. Its descriptor and transitions
                    # stay sealed; this retry becomes a new immutable generation.
                generation += 1
                projected = charged + int(charged_bytes)
                if projected > int(ceiling):
                    raise AcquisitionError(
                        "Coinalyze new raw bytes exceed the accepted allocation",
                        context={"ceiling": int(ceiling), "projected": projected},
                    )
                db.execute(
                    "INSERT INTO coinalyze_charge(provider, identity, generation, "
                    "content_sha256, charged_bytes, http_status, outcome, points, "
                    "request_proof, retrieval_json, revision_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        provider,
                        identity,
                        generation,
                        content_sha256,
                        int(charged_bytes),
                        int(http_status),
                        outcome,
                        int(points),
                        request_proof,
                        compact_json(dict(retrieval)).decode("utf-8"),
                        compact_json(dict(revision)).decode("utf-8"),
                        datetime.now(UTC).isoformat(),
                    ),
                )
                db.execute(
                    "UPDATE coinalyze_ledger SET charged=? WHERE id=1", (projected,)
                )
                db.execute(
                    "INSERT INTO charge_transition(provider, identity, generation, "
                    "status, at) VALUES (?, ?, ?, ?, ?)",
                    (
                        provider,
                        identity,
                        generation,
                        CHARGE_RESERVED,
                        datetime.now(UTC).isoformat(),
                    ),
                )
                db.execute("COMMIT")
            except Exception:
                db.execute("ROLLBACK")
                raise
        fault.check("after_coinalyze_charge", identity)

    def mark_charge_published(self, provider: str, identity: str, *, fault: FaultInjector) -> None:
        with self._lock:
            generation = self.charge_generation(provider, identity)
            if not generation:
                raise UnsafeStateError(
                    "a Coinalyze publication has no reservation",
                    context={"identity": identity},
                )
            latest = self.charge_status(provider, identity, generation)
            if latest == CHARGE_PUBLISHED:
                pass
            elif latest != CHARGE_RESERVED:
                raise UnsafeStateError(
                    "a Coinalyze charge publication did not update one reserved row",
                    context={"identity": identity, "status": latest},
                )
            else:
                self._db().execute(
                    "INSERT INTO charge_transition(provider, identity, generation, "
                    "status, at) VALUES (?, ?, ?, ?, ?)",
                    (
                        provider,
                        identity,
                        generation,
                        CHARGE_PUBLISHED,
                        datetime.now(UTC).isoformat(),
                    ),
                )
        fault.check("after_coinalyze_publication", identity)

    def settle_existing_charge(
        self, provider: str, identity: str, *, content_sha256: str, charged_bytes: int
    ) -> None:
        """Settle a published charge whose completion is already durable."""

        db = self._db()
        with self._lock:
            db.execute("BEGIN IMMEDIATE")
            try:
                charge = self.open_charge(provider, identity)
                if charge is None:
                    raise UnsafeStateError(
                        "a Coinalyze charge disappeared while settling",
                        context={"identity": identity},
                    )
                completion = self.completion_fact(provider, identity)
                if completion is None:
                    raise UnsafeStateError(
                        "a Coinalyze charge cannot settle without its completion",
                        context={"identity": identity},
                    )
                payload = self.plan_payload(provider, identity)
                if payload is None:
                    raise UnsafeStateError(
                        "a Coinalyze charge has no plan row",
                        context={"identity": identity},
                    )
                plan = PlanObject(
                    provider, identity, KIND_COINALYZE_LIQUIDATION, dict(payload)
                )
                validate_charge_against_plan(
                    plan,
                    charge,
                    completion,
                    history=self.charge_history(
                        provider, identity, int(charge["generation"])
                    ),
                )
                if (
                    str(charge["content_sha256"]) != content_sha256
                    or int(charge["charged_bytes"]) != int(charged_bytes)
                ):
                    raise UnsafeStateError(
                        "a Coinalyze charge does not match its completion",
                        context={"identity": identity},
                    )
                latest = charge["status"]
                if latest == CHARGE_SETTLED:
                    db.execute("COMMIT")
                    return
                if latest != CHARGE_PUBLISHED:
                    raise UnsafeStateError(
                        "a Coinalyze charge cannot settle from a reservation",
                        context={"identity": identity, "status": latest},
                    )
                db.execute(
                    "INSERT INTO charge_transition(provider, identity, generation, "
                    "status, at) VALUES (?, ?, ?, ?, ?)",
                    (
                        provider,
                        identity,
                        int(charge["generation"]),
                        CHARGE_SETTLED,
                        datetime.now(UTC).isoformat(),
                    ),
                )
                db.execute("COMMIT")
            except Exception:
                db.execute("ROLLBACK")
                raise

    def release_charge(self, provider: str, identity: str) -> int:
        """Refund an unpublished reservation exactly, restoring the ledger equation."""

        db = self._db()
        with self._lock:
            db.execute("BEGIN IMMEDIATE")
            try:
                charge = self.open_charge(provider, identity)
                if charge is None:
                    db.execute("COMMIT")
                    return 0
                if charge["status"] == CHARGE_RELEASED:
                    db.execute("COMMIT")
                    return 0
                if charge["status"] != CHARGE_RESERVED:
                    raise UnsafeStateError(
                        "only an unpublished Coinalyze reservation may be released",
                        context={"identity": identity, "status": charge["status"]},
                    )
                amount = int(charge["charged_bytes"])
                ledger = db.execute(
                    "SELECT charged FROM coinalyze_ledger WHERE id=1"
                ).fetchone()
                if ledger is None:
                    raise UnsafeStateError("the singleton Coinalyze ledger row is missing")
                restored = int(ledger[0]) - amount
                if restored < 0:
                    raise UnsafeStateError(
                        "the Coinalyze ledger is over the accepted allocation ceiling",
                        context={"charged": int(ledger[0]), "release": amount},
                    )
                db.execute(
                    "UPDATE coinalyze_ledger SET charged=? WHERE id=1",
                    (restored,),
                )
                db.execute(
                    "INSERT INTO charge_transition(provider, identity, generation, "
                    "status, at) VALUES (?, ?, ?, ?, ?)",
                    (
                        provider,
                        identity,
                        int(charge["generation"]),
                        CHARGE_RELEASED,
                        datetime.now(UTC).isoformat(),
                    ),
                )
                db.execute("COMMIT")
                return amount
            except Exception:
                db.execute("ROLLBACK")
                raise

    # -- reads ----------------------------------------------------------------------

    def is_complete(self, provider: str, identity: str) -> bool:
        row = self._db().execute(
            "SELECT 1 FROM completion WHERE provider=? AND identity=?",
            (provider, identity),
        ).fetchone()
        return row is not None

    def completion_fact(self, provider: str, identity: str) -> CompletionFact | None:
        row = self._db().execute(
            "SELECT provider, identity, content_sha256, content_path, sidecar_sha256, "
            "sidecar_path, listed_bytes, retrieved_at, revision_json, validation_state "
            "FROM completion WHERE provider=? AND identity=?",
            (provider, identity),
        ).fetchone()
        return None if row is None else _completion_from_row(row)

    def plan_payload(self, provider: str, identity: str) -> dict[str, Any] | None:
        row = self._db().execute(
            "SELECT payload_json FROM plan_entry WHERE provider=? AND identity=?",
            (provider, identity),
        ).fetchone()
        if row is None:
            return None
        return dict(json.loads(str(row[0])).get("payload") or {})

    def iter_plan_rows(self, *, kinds: Sequence[str] | None = None) -> Iterator[PlanObject]:
        db = self._db()
        after = 0
        while True:
            if kinds:
                marks = ",".join("?" for _ in kinds)
                rows = db.execute(
                    f"SELECT seq, provider, identity, kind, payload_json FROM plan_entry "
                    f"WHERE seq > ? AND kind IN ({marks}) ORDER BY seq LIMIT ?",
                    (after, *kinds, CURSOR_BATCH),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT seq, provider, identity, kind, payload_json FROM plan_entry "
                    "WHERE seq > ? ORDER BY seq LIMIT ?",
                    (after, CURSOR_BATCH),
                ).fetchall()
            if not rows:
                return
            for row in rows:
                after = int(row[0])
                body = json.loads(str(row[4]))
                yield PlanObject(
                    str(row[1]), str(row[2]), str(row[3]), dict(body.get("payload") or {})
                )

    def schedulable_batch(
        self, after: int, limit: int = CURSOR_BATCH
    ) -> list[tuple[int, PlanObject, CompletionFact | None]]:
        """One bounded batch of plan rows with their completions, after ``after``."""

        rows = self._db().execute(
            "SELECT p.seq, p.provider, p.identity, p.kind, p.payload_json, "
            "c.provider, c.identity, c.content_sha256, c.content_path, c.sidecar_sha256, "
            "c.sidecar_path, c.listed_bytes, c.retrieved_at, c.revision_json, "
            "c.validation_state "
            "FROM plan_entry p LEFT JOIN completion c "
            "ON c.provider = p.provider AND c.identity = p.identity "
            "WHERE p.seq > ? AND p.kind != ? ORDER BY p.seq LIMIT ?",
            (int(after), KIND_COINALYZE_UNSUPPORTED, int(limit)),
        ).fetchall()
        BOUND_TELEMETRY.note("max_cursor_rows", len(rows))
        BOUND_TELEMETRY.note("max_batch_rows", len(rows))
        batch: list[tuple[int, PlanObject, CompletionFact | None]] = []
        for row in rows:
            body = json.loads(str(row[4]))
            plan = PlanObject(
                str(row[1]), str(row[2]), str(row[3]), dict(body.get("payload") or {})
            )
            fact = None if row[5] is None else _completion_from_row(row[5:15])
            batch.append((int(row[0]), plan, fact))
        return batch

    def iter_schedulable(self) -> Iterator[tuple[PlanObject, CompletionFact | None]]:
        """Every non-gap plan row with its completion, in installed order.

        The caller re-proves each completed provider object before it is skipped; nothing
        is skipped on the strength of a completion row alone.
        """

        db = self._db()
        after = 0
        while True:
            rows = db.execute(
                "SELECT p.seq, p.provider, p.identity, p.kind, p.payload_json, "
                "c.provider, c.identity, c.content_sha256, c.content_path, c.sidecar_sha256, "
                "c.sidecar_path, c.listed_bytes, c.retrieved_at, c.revision_json, "
                "c.validation_state "
                "FROM plan_entry p LEFT JOIN completion c "
                "ON c.provider = p.provider AND c.identity = p.identity "
                "WHERE p.seq > ? AND p.kind != ? ORDER BY p.seq LIMIT ?",
                (after, KIND_COINALYZE_UNSUPPORTED, CURSOR_BATCH),
            ).fetchall()
            if not rows:
                return
            for row in rows:
                after = int(row[0])
                body = json.loads(str(row[4]))
                plan = PlanObject(
                    str(row[1]), str(row[2]), str(row[3]), dict(body.get("payload") or {})
                )
                fact = None if row[5] is None else _completion_from_row(row[5:15])
                yield plan, fact

    def counts(self) -> dict[str, int]:
        db = self._db()
        planned = db.execute("SELECT COUNT(*) FROM plan_entry").fetchone()[0]
        completed = db.execute("SELECT COUNT(*) FROM completion").fetchone()[0]
        attempts = db.execute("SELECT COUNT(*) FROM attempt").fetchone()[0]
        gaps = db.execute("SELECT COUNT(*) FROM terminal_gap").fetchone()[0]
        charged = db.execute("SELECT charged FROM coinalyze_ledger WHERE id=1").fetchone()
        return {
            "planned": int(planned),
            "completed": int(completed),
            "attempts": int(attempts),
            "gaps": int(gaps),
            "coinalyze_charged": int(charged[0]) if charged else 0,
        }

    def iter_completions(self) -> Iterator[dict[str, Any]]:
        db = self._db()
        after = 0
        while True:
            rows = db.execute(
                "SELECT seq, provider, identity, content_sha256, content_path, sidecar_sha256, "
                "sidecar_path, listed_bytes, retrieved_at, revision_json, validation_state "
                "FROM completion WHERE seq > ? ORDER BY seq LIMIT ?",
                (after, CURSOR_BATCH),
            ).fetchall()
            if not rows:
                return
            BOUND_TELEMETRY.note("max_cursor_rows", len(rows))
            for row in rows:
                after = int(row[0])
                item = _completion_from_row(row[1:]).as_row()
                item["seq"] = int(row[0])
                yield item

    def iter_gaps(self) -> Iterator[dict[str, Any]]:
        db = self._db()
        for row in db.execute(
            "SELECT provider, identity, kind, fact_json FROM terminal_gap "
            "ORDER BY provider, identity"
        ):
            yield {
                "provider": row[0],
                "identity": row[1],
                "kind": row[2],
                "fact": json.loads(row[3]),
            }

    def iter_sidecar_facts(self) -> Iterator[dict[str, Any]]:
        after = 0
        while True:
            rows = self._db().execute(
                "SELECT seq, provider, identity, sidecar_sha256, sidecar_path, "
                "sidecar_bytes, provider_checksum FROM sidecar_fact "
                "WHERE seq > ? ORDER BY seq LIMIT ?",
                (after, CURSOR_BATCH),
            ).fetchall()
            if not rows:
                return
            BOUND_TELEMETRY.note("max_cursor_rows", len(rows))
            for row in rows:
                after = int(row[0])
                yield {
                    "seq": int(row[0]),
                    "provider": str(row[1]),
                    "identity": str(row[2]),
                    "sidecar_sha256": str(row[3]),
                    "sidecar_path": str(row[4]),
                    "sidecar_bytes": int(row[5]),
                    "provider_checksum": str(row[6]),
                }

    def plan_identity(self) -> str:
        row = self._db().execute("SELECT plan_identity FROM authority WHERE id=1").fetchone()
        if row is None:
            raise UnsafeStateError("state has no installed plan")
        return str(row[0])

    def authority_row(self) -> dict[str, Any]:
        row = self._db().execute(
            "SELECT plan_identity, plan_receipt_sha256, pins_json, code_json, destination, "
            "device, created_at FROM authority WHERE id=1"
        ).fetchone()
        if row is None:
            raise UnsafeStateError("state has no installed plan")
        return {
            "plan_identity": str(row[0]),
            "plan_receipt_sha256": str(row[1]),
            "pins": json.loads(str(row[2])),
            "code": json.loads(str(row[3])),
            "destination": str(row[4]),
            "device": str(row[5]),
            "created_at": str(row[6]),
        }

    def attempt_facts_digest(self, *, attempt_hi: int | None = None) -> tuple[str, int]:
        """Canonical digest and exact count of the durable attempt facts."""

        digest = hashlib.sha256()
        count = 0
        db = self._db()
        after = -1
        while True:
            if attempt_hi is None:
                rows = db.execute(
                    "SELECT id, provider, identity, started_at, ended_at, class, "
                    "status_code, redacted_fact_json FROM attempt "
                    "WHERE id > ? ORDER BY id LIMIT ?",
                    (after, CURSOR_BATCH),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT id, provider, identity, started_at, ended_at, class, "
                    "status_code, redacted_fact_json FROM attempt "
                    "WHERE id > ? AND id <= ? ORDER BY id LIMIT ?",
                    (after, int(attempt_hi), CURSOR_BATCH),
                ).fetchall()
            if not rows:
                break
            for row in rows:
                after = int(row[0])
                count += 1
                digest.update(
                    compact_json(
                        {
                            "id": int(row[0]),
                            "provider": str(row[1]),
                            "identity": str(row[2]),
                            "started_at": str(row[3]),
                            "ended_at": None if row[4] is None else str(row[4]),
                            "class": str(row[5]),
                            "status_code": None if row[6] is None else int(row[6]),
                            "fact": json.loads(str(row[7])),
                        }
                    )
                )
        return digest.hexdigest(), count

    def run_metadata_row(self, run_id: str) -> dict[str, Any] | None:
        if not run_id:
            return None
        row = self._db().execute(
            "SELECT seq, run_id, started_at, ended_at, stop_reason, attempt_hi, "
            "network_calls, start_snapshot_json, error_count, network_sample_json, "
            "pre_capacity_json, post_capacity_json, capacity_blocked, attempt_delta, "
            "completion_delta, gap_delta, byte_delta, open_coinalyze_charges, counts_json "
            "FROM run_metadata WHERE run_id=?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "seq": int(row[0]),
            "run_id": str(row[1]),
            "started_at": str(row[2]),
            "ended_at": None if row[3] is None else str(row[3]),
            "stop_reason": None if row[4] is None else str(row[4]),
            "attempt_hi": int(row[5]),
            "network_calls": int(row[6]),
            "start_snapshot": json.loads(str(row[7])),
            "error_count": int(row[8]),
            "network_sample": json.loads(str(row[9])),
            "pre_capacity": json.loads(str(row[10])),
            "post_capacity": json.loads(str(row[11])),
            "capacity_blocked": bool(int(row[12])),
            "attempt_delta": int(row[13]),
            "completion_delta": int(row[14]),
            "gap_delta": int(row[15]),
            "byte_delta": int(row[16]),
            "open_coinalyze_charges": int(row[17]),
            "counts": json.loads(str(row[18])),
        }

    def iter_run_facts(self, *, run_hi: int | None = None) -> Iterator[dict[str, Any]]:
        after = 0
        sql = (
            "SELECT seq, run_id, started_at, ended_at, stop_reason, attempt_hi, "
            "network_calls, start_snapshot_json, error_count, network_sample_json, "
            "pre_capacity_json, post_capacity_json, capacity_blocked, attempt_delta, "
            "completion_delta, gap_delta, byte_delta, open_coinalyze_charges, counts_json "
            "FROM run_metadata WHERE seq > ?"
        )
        while True:
            if run_hi is None:
                rows = self._db().execute(
                    sql + " ORDER BY seq LIMIT ?",
                    (after, CURSOR_BATCH),
                ).fetchall()
            else:
                rows = self._db().execute(
                    sql + " AND seq <= ? ORDER BY seq LIMIT ?",
                    (after, int(run_hi), CURSOR_BATCH),
                ).fetchall()
            if not rows:
                return
            for row in rows:
                after = int(row[0])
                yield {
                    "seq": int(row[0]),
                    "run_id": str(row[1]),
                    "started_at": str(row[2]),
                    "ended_at": None if row[3] is None else str(row[3]),
                    "stop_reason": None if row[4] is None else str(row[4]),
                    "attempt_hi": int(row[5]),
                    "network_calls": int(row[6]),
                    "start_snapshot": json.loads(str(row[7])),
                    "error_count": int(row[8]),
                    "network_sample": json.loads(str(row[9])),
                    "pre_capacity": json.loads(str(row[10])),
                    "post_capacity": json.loads(str(row[11])),
                    "capacity_blocked": int(row[12]),
                    "attempt_delta": int(row[13]),
                    "completion_delta": int(row[14]),
                    "gap_delta": int(row[15]),
                    "byte_delta": int(row[16]),
                    "open_coinalyze_charges": int(row[17]),
                    "counts": json.loads(str(row[18])),
                }

    def iter_charge_facts(self, *, charge_hi: int | None = None) -> Iterator[dict[str, Any]]:
        after = 0
        while True:
            if charge_hi is None:
                rows = self._db().execute(
                    "SELECT seq, provider, identity, content_sha256, charged_bytes, "
                    "http_status, outcome, points, request_proof, retrieval_json, "
                    "revision_json, created_at, generation FROM coinalyze_charge "
                    "WHERE seq > ? ORDER BY seq LIMIT ?",
                    (after, CURSOR_BATCH),
                ).fetchall()
            else:
                rows = self._db().execute(
                    "SELECT seq, provider, identity, content_sha256, charged_bytes, "
                    "http_status, outcome, points, request_proof, retrieval_json, "
                    "revision_json, created_at, generation FROM coinalyze_charge "
                    "WHERE seq > ? AND seq <= ? ORDER BY seq LIMIT ?",
                    (after, int(charge_hi), CURSOR_BATCH),
                ).fetchall()
            if not rows:
                return
            for row in rows:
                after = int(row[0])
                yield {
                    "seq": int(row[0]),
                    "provider": str(row[1]),
                    "identity": str(row[2]),
                    "content_sha256": str(row[3]),
                    "charged_bytes": int(row[4]),
                    "http_status": int(row[5]),
                    "outcome": str(row[6]),
                    "points": int(row[7]),
                    "request_proof": str(row[8]),
                    "retrieval": json.loads(str(row[9])),
                    "revision": json.loads(str(row[10])),
                    "created_at": str(row[11]),
                    "generation": int(row[12]),
                }

    def iter_charge_transitions(
        self, *, transition_hi: int | None = None
    ) -> Iterator[dict[str, Any]]:
        after = 0
        while True:
            if transition_hi is None:
                rows = self._db().execute(
                    "SELECT seq, provider, identity, status, at, generation "
                    "FROM charge_transition WHERE seq > ? ORDER BY seq LIMIT ?",
                    (after, CURSOR_BATCH),
                ).fetchall()
            else:
                rows = self._db().execute(
                    "SELECT seq, provider, identity, status, at, generation "
                    "FROM charge_transition WHERE seq > ? AND seq <= ? ORDER BY seq LIMIT ?",
                    (after, int(transition_hi), CURSOR_BATCH),
                ).fetchall()
            if not rows:
                return
            for row in rows:
                after = int(row[0])
                yield {
                    "seq": int(row[0]),
                    "provider": str(row[1]),
                    "identity": str(row[2]),
                    "status": str(row[3]),
                    "at": str(row[4]),
                    "generation": int(row[5]),
                }

    def charge_history(
        self, provider: str, identity: str, generation: int
    ) -> list[dict[str, Any]]:
        """The bounded, ordered transition history of one charge generation."""

        rows = self._db().execute(
            "SELECT seq, status, at FROM charge_transition WHERE provider=? AND identity=? "
            "AND generation=? ORDER BY seq LIMIT ?",
            (provider, identity, int(generation), MAX_CHARGE_TRANSITIONS),
        ).fetchall()
        return [
            {"seq": int(row[0]), "status": str(row[1]), "at": str(row[2])} for row in rows
        ]

    def iter_seal_facts(self, *, seal_hi: int | None = None) -> Iterator[dict[str, Any]]:
        """Every previously published seal link, in stable insertion order."""

        after = 0
        while True:
            if seal_hi is None:
                rows = self._db().execute(
                    "SELECT seq, run_id, receipt_sha256, predecessor_sha256, prefix_digest, "
                    "marks_json FROM run_seal WHERE seq > ? ORDER BY seq LIMIT ?",
                    (after, CURSOR_BATCH),
                ).fetchall()
            else:
                rows = self._db().execute(
                    "SELECT seq, run_id, receipt_sha256, predecessor_sha256, prefix_digest, "
                    "marks_json FROM run_seal WHERE seq > ? AND seq <= ? ORDER BY seq LIMIT ?",
                    (after, int(seal_hi), CURSOR_BATCH),
                ).fetchall()
            if not rows:
                return
            for row in rows:
                after = int(row[0])
                yield {
                    "seq": int(row[0]),
                    "run_id": str(row[1]),
                    "receipt_sha256": str(row[2]),
                    "predecessor_sha256": str(row[3]),
                    "prefix_digest": str(row[4]),
                    "marks": json.loads(str(row[5])),
                }

    def seal_fact(self, receipt_sha256: str) -> dict[str, Any] | None:
        row = self._db().execute(
            "SELECT seq, run_id, receipt_sha256, predecessor_sha256, prefix_digest, "
            "marks_json FROM run_seal WHERE receipt_sha256=?",
            (receipt_sha256,),
        ).fetchone()
        if row is None:
            return None
        return {
            "seq": int(row[0]),
            "run_id": str(row[1]),
            "receipt_sha256": str(row[2]),
            "predecessor_sha256": str(row[3]),
            "prefix_digest": str(row[4]),
            "marks": json.loads(str(row[5])),
        }

    def _zero_watermarks(self) -> dict[str, int]:
        return {key: 0 for key in WATERMARK_KEYS}

    def current_watermarks(self) -> dict[str, int]:
        db = self._db()
        return {
            "attempt_hi": int(db.execute("SELECT COALESCE(MAX(id), 0) FROM attempt").fetchone()[0]),
            "completion_hi": int(
                db.execute("SELECT COALESCE(MAX(seq), 0) FROM completion").fetchone()[0]
            ),
            "sidecar_hi": int(
                db.execute("SELECT COALESCE(MAX(seq), 0) FROM sidecar_fact").fetchone()[0]
            ),
            "charge_hi": int(
                db.execute("SELECT COALESCE(MAX(seq), 0) FROM coinalyze_charge").fetchone()[0]
            ),
            "transition_hi": int(
                db.execute("SELECT COALESCE(MAX(seq), 0) FROM charge_transition").fetchone()[0]
            ),
            "run_hi": int(
                db.execute("SELECT COALESCE(MAX(seq), 0) FROM run_metadata").fetchone()[0]
            ),
            "seal_hi": int(
                db.execute("SELECT COALESCE(MAX(seq), 0) FROM run_seal").fetchone()[0]
            ),
        }

    def _prefix_digest_unlocked(self, marks: Mapping[str, int]) -> str:
        db = self._db()
        hasher = hashlib.sha256()
        authority = self.authority_row()
        hasher.update(
            compact_json(
                {
                    "section": "authority",
                    "plan_identity": authority["plan_identity"],
                    "plan_receipt_sha256": authority["plan_receipt_sha256"],
                    "pins": authority["pins"],
                    "code": authority["code"],
                    "destination": authority["destination"],
                    "device": authority["device"],
                    "created_at": authority["created_at"],
                }
            )
        )
        plan_digest = hashlib.sha256()
        plan_rows = 0
        after = 0
        while True:
            rows = db.execute(
                "SELECT seq, payload_json FROM plan_entry WHERE seq > ? ORDER BY seq LIMIT ?",
                (after, CURSOR_BATCH),
            ).fetchall()
            if not rows:
                break
            for row in rows:
                after = int(row[0])
                plan_rows += 1
                plan_digest.update(str(row[1]).encode("utf-8"))
        hasher.update(
            compact_json(
                {
                    "section": "plan",
                    "rows": plan_rows,
                    "digest": plan_digest.hexdigest(),
                }
            )
        )
        hashed_completions = 0
        after = 0
        completion_hi = int(marks["completion_hi"])
        while True:
            rows = db.execute(
                "SELECT seq, provider, identity, content_sha256, content_path, "
                "sidecar_sha256, sidecar_path, listed_bytes, retrieved_at, revision_json, "
                "validation_state FROM completion WHERE seq > ? AND seq <= ? "
                "ORDER BY seq LIMIT ?",
                (after, completion_hi, CURSOR_BATCH),
            ).fetchall()
            if not rows:
                break
            for row in rows:
                after = int(row[0])
                hashed_completions += 1
                hasher.update(
                    compact_json(
                        {"section": "completion", "seq": int(row[0]), **_completion_from_row(row[1:]).as_row()}
                    )
                )
        expected_completions = int(
            db.execute(
                "SELECT COUNT(*) FROM completion WHERE seq <= ?", (completion_hi,)
            ).fetchone()[0]
        )
        if hashed_completions != expected_completions:
            raise UnsafeStateError(
                "authenticated prefix completions were rewritten or deleted",
                context={"expected": expected_completions, "actual": hashed_completions},
            )
        sidecar_hi = int(marks["sidecar_hi"])
        after = 0
        while True:
            rows = db.execute(
                "SELECT seq, provider, identity, sidecar_sha256, sidecar_path, "
                "sidecar_bytes, provider_checksum FROM sidecar_fact "
                "WHERE seq > ? AND seq <= ? ORDER BY seq LIMIT ?",
                (after, sidecar_hi, CURSOR_BATCH),
            ).fetchall()
            if not rows:
                break
            for row in rows:
                after = int(row[0])
                hasher.update(
                    compact_json(
                        {
                            "section": "sidecar",
                            "seq": int(row[0]),
                            "provider": str(row[1]),
                            "identity": str(row[2]),
                            "sidecar_sha256": str(row[3]),
                            "sidecar_path": str(row[4]),
                            "sidecar_bytes": int(row[5]),
                            "provider_checksum": str(row[6]),
                        }
                    )
                )
        for item in self.iter_gaps():
            hasher.update(compact_json({"section": "gap", **item}))
        for item in self.iter_charge_facts(charge_hi=int(marks["charge_hi"])):
            hasher.update(compact_json({"section": "charge", **item}))
        for item in self.iter_charge_transitions(
            transition_hi=int(marks["transition_hi"])
        ):
            hasher.update(compact_json({"section": "charge_transition", **item}))
        sealed_charged = int(
            db.execute(
                "SELECT COALESCE(SUM(c.charged_bytes), 0) FROM coinalyze_charge c "
                "WHERE c.seq <= ? AND (SELECT t.status FROM charge_transition t "
                "WHERE t.provider = c.provider AND t.identity = c.identity "
                "AND t.generation = c.generation AND t.seq <= ? "
                f"ORDER BY t.seq DESC LIMIT 1) IS NOT '{CHARGE_RELEASED}'",
                (int(marks["charge_hi"]), int(marks["transition_hi"])),
            ).fetchone()[0]
        )
        hasher.update(
            compact_json(
                {
                    "section": "ledger",
                    "charged": sealed_charged,
                }
            )
        )
        attempts_digest, attempts = self.attempt_facts_digest(
            attempt_hi=int(marks["attempt_hi"])
        )
        hasher.update(
            compact_json(
                {"section": "attempts", "count": attempts, "digest": attempts_digest}
            )
        )
        for item in self.iter_run_facts(run_hi=int(marks["run_hi"])):
            hasher.update(compact_json({"section": "run", **item}))
        for item in self.iter_seal_facts(seal_hi=int(marks.get("seal_hi", 0))):
            hasher.update(compact_json({"section": "seal", **item}))
        return hasher.hexdigest()

    def semantic_digest(self) -> str:
        """Digest of current watermarks plus the live ledger equation."""

        hasher = hashlib.sha256()
        hasher.update(self._prefix_digest_unlocked(self.current_watermarks()).encode("ascii"))
        ledger = self._db().execute(
            "SELECT charged FROM coinalyze_ledger WHERE id=1"
        ).fetchone()
        hasher.update(
            compact_json(
                {
                    "section": "live_ledger",
                    "charged": None if ledger is None else int(ledger[0]),
                }
            )
        )
        return hasher.hexdigest()

    def seal_head_row(self) -> dict[str, Any] | None:
        row = self._db().execute(
            "SELECT receipt_sha256, receipt_path, prefix_digest, attempt_hi, "
            "completion_hi, sidecar_hi, charge_hi, transition_hi, run_hi, seal_hi, "
            "predecessor_sha256 FROM seal_head WHERE id=1"
        ).fetchone()
        if row is None:
            return None
        return {
            "receipt_sha256": str(row[0]),
            "receipt_path": str(row[1]),
            "prefix_digest": str(row[2]),
            "attempt_hi": int(row[3]),
            "completion_hi": int(row[4]),
            "sidecar_hi": int(row[5]),
            "charge_hi": int(row[6]),
            "transition_hi": int(row[7]),
            "run_hi": int(row[8]),
            "seal_hi": int(row[9]),
            "predecessor_sha256": None if row[10] is None else str(row[10]),
        }

    def _receipt_dirs(self) -> tuple[Path, ...]:
        return (self.run_receipt_dir, self.plan_receipt_dir)

    def _open_receipt_fd(self, path: Path) -> int | None:
        """Open one receipt leaf through the bound session roots, no-follow."""

        try:
            directory, name = open_parent_dir(path.parent, path, roots=self.roots)
        except UnsafeStateError:
            return None
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise UnsafeStateError(
                "a receipt cannot be opened no-follow", context={"path": str(path)}
            ) from exc
        finally:
            os.close(directory)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise UnsafeStateError("a receipt is not a regular file")
        except Exception:
            os.close(fd)
            raise
        return fd

    def _find_receipt(self, digest: str, hint: Path) -> Path:
        """Locate one receipt by identity inside the accepted receipt roots only."""

        candidates: list[Path] = [hint.parent / f"{digest}.json"]
        candidates.extend(parent / f"{digest}.json" for parent in self._receipt_dirs())
        seen: set[Path] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            fd = self._open_receipt_fd(candidate)
            if fd is not None:
                os.close(fd)
                return candidate
        raise UnsafeStateError(
            "a receipt in the authenticated chain is missing", context={"digest": digest}
        )

    def _read_receipt(self, path: Path, *, expect: str | None = None) -> dict[str, Any]:
        """Rehash one receipt and prove its bytes are exactly canonical JSON."""

        fd = self._open_receipt_fd(path)
        if fd is None:
            raise UnsafeStateError(
                "a receipt in the authenticated chain is missing",
                context={"path": str(path)},
            )
        try:
            digest, _size = sha256_fd(fd)
            os.lseek(fd, 0, os.SEEK_SET)
            payload = read_fd(fd)
        finally:
            os.close(fd)
        if expect is not None and digest != expect:
            raise UnsafeStateError(
                "a receipt in the authenticated chain does not match its identity",
                context={"expected": expect, "actual": digest},
            )
        document = _decode_json(payload, label="chain receipt")
        if canonical_json(document) != payload:
            raise UnsafeStateError(
                "a receipt in the authenticated chain is not canonical JSON",
                context={"digest": digest},
            )
        return {"digest": digest, "document": document, "path": path}

    def _rehash_receipt_file(self, path: Path) -> tuple[str, dict[str, Any]]:
        record = self._read_receipt(path)
        return str(record["digest"]), dict(record["document"])

    def _receipt_marks(self, document: Mapping[str, Any]) -> dict[str, int]:
        raw = document.get("high_watermarks")
        if not isinstance(raw, dict):
            raise UnsafeStateError("a run receipt has no high-watermarks")
        marks: dict[str, int] = {}
        current = self.current_watermarks()
        for key in self._zero_watermarks():
            value = raw.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise UnsafeStateError(
                    "a run receipt watermark is not a non-negative integer",
                    context={"mark": key},
                )
            if value > current[key]:
                raise UnsafeStateError(
                    "a run receipt watermark exceeds the actual stream",
                    context={"mark": key, "claimed": value, "actual": current[key]},
                )
            marks[key] = int(value)
        if len(raw) != len(marks):
            raise UnsafeStateError("a run receipt carries an unknown watermark")
        return marks

    def _accepted_capacity_components(self) -> dict[str, int]:
        pins = self.authority_row()["pins"]
        stable = _exact_int(pins["stable_requirement_bytes"], label="pins.stable_requirement_bytes")
        if stable == EXPECTED_STABLE_REQUIREMENT_BYTES:
            return {key: int(value) for key, value in STABLE_COMPONENTS.items()}
        return {"stable_requirement_bytes": stable}

    def _capacity_component_keys(self) -> frozenset[str]:
        return frozenset(self._accepted_capacity_components())

    def _capacity_snapshot(
        self, *, available_bytes: int, next_transfer_bytes: int = 0
    ) -> dict[str, Any]:
        if (
            not isinstance(available_bytes, int)
            or isinstance(available_bytes, bool)
            or available_bytes < 0
        ):
            raise UnsafeStateError("available bytes are invalid")
        next_transfer = _exact_int(next_transfer_bytes, label="next_transfer_bytes")
        pins = self.authority_row()["pins"]
        stable = _exact_int(pins["stable_requirement_bytes"], label="pins.stable_requirement_bytes")
        reserve = operating_reserve_bytes(max(available_bytes, 1))
        total = stable + reserve
        needed = total + next_transfer
        blocked = needed > available_bytes
        components = self._accepted_capacity_components()
        return {
            "stable_requirement_bytes": stable,
            "operating_reserve_bytes": reserve,
            "total_future_storage_bytes": total,
            "available_bytes": available_bytes,
            "next_transfer_bytes": next_transfer,
            "needed_bytes": needed,
            "storage_preflight_state": "blocked" if blocked else "sufficient",
            "reserve_floor_bytes": MINIMUM_OPERATING_RESERVE_BYTES,
            "stable_components": components,
        }

    def _parse_capacity_fact(self, value: Any, *, label: str) -> dict[str, Any]:
        body = _exact_object(value, label=label, keys=CAPACITY_FACT_KEYS)
        parsed: dict[str, Any] = {}
        for key in (
            "stable_requirement_bytes",
            "operating_reserve_bytes",
            "total_future_storage_bytes",
            "available_bytes",
            "next_transfer_bytes",
            "needed_bytes",
            "reserve_floor_bytes",
        ):
            parsed[key] = _exact_int(body[key], label=f"{label}.{key}")
        state_name = _exact_str(body["storage_preflight_state"], label=f"{label}.storage_preflight_state")
        if state_name not in {"sufficient", "blocked"}:
            raise UnsafeStateError(f"{label}.storage_preflight_state is not an accepted state")
        parsed["storage_preflight_state"] = state_name
        component_keys = self._capacity_component_keys()
        components = _exact_object(
            body["stable_components"],
            label=f"{label}.stable_components",
            keys=component_keys,
        )
        parsed_components: dict[str, int] = {}
        for name in component_keys:
            parsed_components[name] = _exact_int(
                components[name], label=f"{label}.stable_components.{name}"
            )
        parsed["stable_components"] = parsed_components
        pins = self.authority_row()["pins"]
        auth_stable = _exact_int(
            pins["stable_requirement_bytes"], label="pins.stable_requirement_bytes"
        )
        if parsed["stable_requirement_bytes"] != auth_stable:
            raise UnsafeStateError(f"{label}.stable_requirement_bytes disagrees with authority")
        accepted_components = self._accepted_capacity_components()
        if parsed_components != accepted_components:
            raise UnsafeStateError(
                f"{label}.stable_components disagree with the accepted mapping"
            )
        if sum(parsed_components.values()) != parsed["stable_requirement_bytes"]:
            raise UnsafeStateError(f"{label}.stable_components do not equal the stable requirement")
        if parsed["total_future_storage_bytes"] != (
            parsed["stable_requirement_bytes"] + parsed["operating_reserve_bytes"]
        ):
            raise UnsafeStateError(f"{label} total-future equation is false")
        if parsed["needed_bytes"] != parsed["total_future_storage_bytes"] + parsed[
            "next_transfer_bytes"
        ]:
            raise UnsafeStateError(f"{label} needed-bytes equation is false")
        if parsed["reserve_floor_bytes"] != MINIMUM_OPERATING_RESERVE_BYTES:
            raise UnsafeStateError(f"{label}.reserve_floor_bytes disagrees with the accepted floor")
        expected_reserve = operating_reserve_bytes(max(parsed["available_bytes"], 1))
        if parsed["operating_reserve_bytes"] != expected_reserve:
            raise UnsafeStateError(f"{label}.operating_reserve_bytes disagrees with availability")
        blocked = parsed["needed_bytes"] > parsed["available_bytes"]
        expected_state = "blocked" if blocked else "sufficient"
        if parsed["storage_preflight_state"] != expected_state:
            raise UnsafeStateError(f"{label}.storage_preflight_state disagrees with the capacity equation")
        return parsed

    def _parse_counts_fact(self, value: Any, *, label: str) -> dict[str, int]:
        body = _exact_object(value, label=label, keys=COUNTS_KEYS)
        return {key: _exact_int(body[key], label=f"{label}.{key}") for key in COUNTS_KEYS}

    def _parse_start_snapshot(self, value: Any) -> dict[str, int]:
        body = _exact_object(value, label="start_snapshot", keys=START_SNAPSHOT_KEYS)
        return {
            key: _exact_int(body[key], label=f"start_snapshot.{key}")
            for key in START_SNAPSHOT_KEYS
        }

    def _run_receipt_facts(self, document: Mapping[str, Any]) -> dict[str, Any]:
        sample = _exact_str_list(
            document["network_sample"], label="network_sample", ceiling=NETWORK_SAMPLE_CEILING
        )
        return {
            "attempt_delta": _exact_int(document["attempt_delta"], label="attempt_delta"),
            "completion_delta": _exact_int(document["completion_delta"], label="completion_delta"),
            "gap_delta": _exact_int(document["gap_delta"], label="gap_delta"),
            "byte_delta": _exact_int(document["byte_delta"], label="byte_delta"),
            "attempts": _exact_int(document["attempts"], label="attempts"),
            "error_count": _exact_int(document["error_count"], label="error_count"),
            "network_sample": sample,
            "pre_capacity": self._parse_capacity_fact(document["pre_capacity"], label="pre_capacity"),
            "post_capacity": self._parse_capacity_fact(document["post_capacity"], label="post_capacity"),
            "capacity_blocked": _exact_bool(document["capacity_blocked"], label="capacity_blocked"),
            "open_coinalyze_charges": _exact_int(
                document["open_coinalyze_charges"], label="open_coinalyze_charges"
            ),
            "counts": self._parse_counts_fact(document["counts"], label="counts"),
            "network_calls": _exact_int(document["network_calls"], label="network_calls"),
        }

    def _validate_run_receipt_facts(
        self,
        document: Mapping[str, Any],
        *,
        authority: Mapping[str, Any],
        seal: Mapping[str, Any] | None,
        run_row: Mapping[str, Any] | None,
        expect_marks: Mapping[str, int] | None,
    ) -> None:
        facts = self._run_receipt_facts(document)
        if run_row is None:
            raise UnsafeStateError("a run receipt has no durable run_metadata")
        marks = self._receipt_marks(document)
        predecessor = _exact_str(document["predecessor_sha256"], label="predecessor_sha256")
        pred_marks = self._predecessor_marks(predecessor)
        snapshot = self._parse_start_snapshot(run_row["start_snapshot"])
        for key in WATERMARK_KEYS:
            if snapshot[key] != pred_marks[key]:
                raise UnsafeStateError(
                    "a run start snapshot disagrees with its predecessor watermarks",
                    context={"mark": key},
                )
        start_listed = snapshot["listed_bytes"]
        if start_listed != self._listed_bytes_at(int(pred_marks["completion_hi"])):
            raise UnsafeStateError("a run start snapshot disagrees with predecessor completions")
        pred_run = self._predecessor_run_row(predecessor)
        if pred_run is None:
            start_gaps = snapshot["gaps"]
        else:
            start_gaps = _exact_int(pred_run["counts"]["gaps"], label="predecessor.counts.gaps")
            if snapshot["gaps"] != start_gaps:
                raise UnsafeStateError("a run start snapshot disagrees with predecessor gaps")
        start_attempts = int(
            self._db().execute(
                "SELECT COUNT(*) FROM attempt WHERE id <= ?",
                (pred_marks["attempt_hi"],),
            ).fetchone()[0]
        )
        start_completed = int(
            self._db().execute(
                "SELECT COUNT(*) FROM completion WHERE seq <= ?",
                (pred_marks["completion_hi"],),
            ).fetchone()[0]
        )
        derived_gaps = start_gaps + int(run_row["gap_delta"])
        derived_counts = self._counts_at(marks, gaps=derived_gaps)
        derived_open = self._open_charges_at(
            charge_hi=int(marks["charge_hi"]),
            transition_hi=int(marks["transition_hi"]),
        )
        derived_bytes = self._listed_bytes_at(int(marks["completion_hi"]))
        if facts["attempt_delta"] != run_row["attempt_delta"]:
            raise UnsafeStateError("a run receipt attempt_delta disagrees with run_metadata")
        if facts["completion_delta"] != run_row["completion_delta"]:
            raise UnsafeStateError("a run receipt completion_delta disagrees with run_metadata")
        if facts["gap_delta"] != run_row["gap_delta"]:
            raise UnsafeStateError("a run receipt gap_delta disagrees with run_metadata")
        if facts["byte_delta"] != run_row["byte_delta"]:
            raise UnsafeStateError("a run receipt byte_delta disagrees with run_metadata")
        if facts["error_count"] != run_row["error_count"]:
            raise UnsafeStateError("a run receipt error_count disagrees with run_metadata")
        if facts["network_sample"] != list(run_row["network_sample"]):
            raise UnsafeStateError("a run receipt network_sample disagrees with run_metadata")
        if facts["pre_capacity"] != self._parse_capacity_fact(
            run_row["pre_capacity"], label="run_metadata.pre_capacity"
        ):
            raise UnsafeStateError("a run receipt pre_capacity disagrees with run_metadata")
        if facts["post_capacity"] != self._parse_capacity_fact(
            run_row["post_capacity"], label="run_metadata.post_capacity"
        ):
            raise UnsafeStateError("a run receipt post_capacity disagrees with run_metadata")
        if facts["capacity_blocked"] != bool(run_row["capacity_blocked"]):
            raise UnsafeStateError("a run receipt capacity_blocked disagrees with run_metadata")
        if facts["open_coinalyze_charges"] != run_row["open_coinalyze_charges"]:
            raise UnsafeStateError(
                "a run receipt open-charge count disagrees with run_metadata"
            )
        if facts["counts"] != self._parse_counts_fact(run_row["counts"], label="run_metadata.counts"):
            raise UnsafeStateError("a run receipt counts disagree with run_metadata")
        if facts["network_calls"] != run_row["network_calls"]:
            raise UnsafeStateError("a run receipt network_calls disagrees with run_metadata")
        if _exact_str(document["started_at"], label="started_at") != run_row["started_at"]:
            raise UnsafeStateError("a run receipt started_at disagrees with run_metadata")
        if _exact_str(document["ended_at"], label="ended_at") != str(run_row["ended_at"] or ""):
            raise UnsafeStateError("a run receipt ended_at disagrees with run_metadata")
        if _exact_str(document["stop_reason"], label="stop_reason") != str(
            run_row["stop_reason"] or ""
        ):
            raise UnsafeStateError("a run receipt stop_reason disagrees with run_metadata")
        if facts["attempt_delta"] != derived_counts["attempts"] - start_attempts:
            raise UnsafeStateError("a run receipt attempt_delta disagrees with watermarks")
        if facts["completion_delta"] != derived_counts["completed"] - start_completed:
            raise UnsafeStateError("a run receipt completion_delta disagrees with watermarks")
        if facts["gap_delta"] != derived_counts["gaps"] - start_gaps:
            raise UnsafeStateError("a run receipt gap_delta disagrees with watermarks")
        if facts["byte_delta"] != derived_bytes - start_listed:
            raise UnsafeStateError("a run receipt byte_delta disagrees with completions")
        if facts["attempts"] != facts["attempt_delta"]:
            raise UnsafeStateError("a run receipt attempts disagrees with attempt_delta")
        if facts["network_calls"] != facts["attempt_delta"]:
            raise UnsafeStateError("a run receipt network_calls disagrees with attempt_delta")
        if facts["open_coinalyze_charges"] != derived_open:
            raise UnsafeStateError("a run receipt open-charge count disagrees with state")
        if facts["counts"] != derived_counts:
            raise UnsafeStateError("a run receipt counts disagree with watermarked state")
        post_blocked = facts["post_capacity"]["storage_preflight_state"] == "blocked"
        stop_capacity = str(run_row.get("stop_reason") or "") == "capacity"
        if (post_blocked or stop_capacity) and facts["capacity_blocked"] is not True:
            raise UnsafeStateError("a run receipt capacity_blocked disagrees with capacity facts")
        prefix = _exact_str(document["prefix_digest"], label="prefix_digest")
        if HEX64.fullmatch(prefix) is None:
            raise UnsafeStateError("a run receipt prefix is not a SHA-256 digest")
        expected_semantic = self._semantic_at(prefix, marks)
        if _exact_str(document["semantic_state_digest"], label="semantic_state_digest") != expected_semantic:
            raise UnsafeStateError("a run receipt semantic digest disagrees with its sealed ledger")
        _ = authority
        _ = seal
        _ = expect_marks

    def _predecessor_marks(self, predecessor_sha256: str) -> dict[str, int]:
        head = self.seal_head_row()
        if head is not None and str(head["receipt_sha256"]) == predecessor_sha256:
            return {key: int(head[key]) for key in WATERMARK_KEYS}
        seal = self.seal_fact(predecessor_sha256)
        if seal is not None:
            marks = dict(seal["marks"])
            return {
                key: _exact_int(marks[key], label=f"predecessor.{key}") for key in WATERMARK_KEYS
            }
        authority = self.authority_row()
        if predecessor_sha256 == str(authority["plan_receipt_sha256"]):
            return self._zero_watermarks()
        raise UnsafeStateError(
            "a run receipt predecessor has no sealed watermarks",
            context={"predecessor": predecessor_sha256},
        )

    def _predecessor_run_row(self, predecessor_sha256: str) -> dict[str, Any] | None:
        row = self._db().execute(
            "SELECT run_id FROM run_seal WHERE receipt_sha256=?",
            (predecessor_sha256,),
        ).fetchone()
        if row is None:
            return None
        return self.run_metadata_row(str(row[0]))

    def _receipt_authority_block(self) -> dict[str, Any]:
        pins = dict(self.authority_row()["pins"])
        return {
            "report_62_sha256": pins.get("report_sha256"),
            "manifest_compressed_sha256": pins.get("manifest_compressed_sha256"),
            "manifest_uncompressed_sha256": pins.get("manifest_uncompressed_sha256"),
            "cost_manifest_sha256": pins.get("cost_manifest_sha256"),
            "receipt_258_sha256": pins.get("receipt_258_sha256"),
            "attestation_282_sha256": pins.get("attestation_282_sha256"),
            "listing_checkpoint_sha256": pins.get("listing_checkpoint_sha256"),
            "contract_metadata_sha256": pins.get("contract_metadata_sha256"),
            "lock_sha256": pins.get("lock_sha256"),
            "amendment_ledger_sha256": pins.get("amendment_ledger_sha256"),
            "progress_sha256": pins.get("progress_sha256"),
            "holdout_boundary_id": pins.get("holdout_boundary_id"),
        }

    def _authenticate_run_publication(
        self, run_id: str, digest: str, document: Mapping[str, Any]
    ) -> None:
        row = self._db().execute(
            "SELECT receipt_sha256, receipt_directory, receipt_body "
            "FROM run_publication WHERE run_id=?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise UnsafeStateError(
                "a sealed run has no durable receipt intent",
                context={"run_id": run_id},
            )
        stored_digest = _exact_str(row[0], label="receipt_sha256")
        if stored_digest != digest:
            raise UnsafeStateError("a receipt intent identity disagrees with its receipt")
        directory = Path(_exact_str(row[1], label="receipt_directory"))
        if directory != self.run_receipt_dir:
            raise UnsafeStateError(
                "a receipt intent names a different run receipt directory",
                context={"run_id": run_id},
            )
        body_text = _exact_str(row[2], label="receipt_body")
        body = body_text.encode("utf-8")
        if canonical_json(document) != body:
            raise UnsafeStateError("a receipt intent disagrees with its receipt")
        if sha256_bytes(body) != digest:
            raise UnsafeStateError("a receipt intent identity conflicts with its body")

    def _validate_receipt_document(
        self,
        document: Mapping[str, Any],
        *,
        authority: Mapping[str, Any],
        seal: Mapping[str, Any] | None = None,
        run_row: Mapping[str, Any] | None = None,
        expect_predecessor: str | None = None,
        expect_marks: Mapping[str, int] | None = None,
        expect_prefix: str | None = None,
        require_publication: bool = True,
    ) -> str:
        """Prove one chain receipt's exact keys, authority, run identity, and seal link."""

        schema_value = document.get("schema_version")
        if type(schema_value) is not str:
            raise UnsafeStateError(
                "a receipt in the authenticated chain has an unknown schema",
                context={"schema_version": schema_value},
            )
        schema = schema_value
        if schema not in {PLAN_SCHEMA, RUN_SCHEMA}:
            raise UnsafeStateError(
                "a receipt in the authenticated chain has an unknown schema",
                context={"schema_version": schema},
            )
        expected_keys = PLAN_RECEIPT_KEYS if schema == PLAN_SCHEMA else RUN_RECEIPT_KEYS
        observed = frozenset(document)
        extra = sorted(observed - expected_keys)
        missing = sorted(expected_keys - observed)
        if extra or missing:
            raise UnsafeStateError(
                "a chain receipt has extra or missing fields",
                context={"extra": extra, "missing": missing, "schema_version": schema},
            )
        if _exact_str(document["ticket"], label="ticket") != TICKET_ID:
            raise UnsafeStateError("a chain receipt is not this ticket")
        if _exact_str(document["policy_identity"], label="policy_identity") != POLICY_IDENTITY:
            raise UnsafeStateError("a chain receipt has a different policy identity")
        if _exact_str(document["plan_identity"], label="plan_identity") != str(
            authority["plan_identity"]
        ):
            raise UnsafeStateError("a chain receipt names a different plan identity")
        if schema == PLAN_SCHEMA:
            authenticate_compact_retained_credit(
                document["retained_credit"],
                pins=dict(authority.get("pins") or {}),
            )
            return schema
        pins = dict(authority.get("pins") or {})
        expected_authority = {
            "report_62_sha256": pins.get("report_sha256"),
            "manifest_compressed_sha256": pins.get("manifest_compressed_sha256"),
            "manifest_uncompressed_sha256": pins.get("manifest_uncompressed_sha256"),
            "cost_manifest_sha256": pins.get("cost_manifest_sha256"),
            "receipt_258_sha256": pins.get("receipt_258_sha256"),
            "attestation_282_sha256": pins.get("attestation_282_sha256"),
            "listing_checkpoint_sha256": pins.get("listing_checkpoint_sha256"),
            "contract_metadata_sha256": pins.get("contract_metadata_sha256"),
            "lock_sha256": pins.get("lock_sha256"),
            "amendment_ledger_sha256": pins.get("amendment_ledger_sha256"),
            "progress_sha256": pins.get("progress_sha256"),
            "holdout_boundary_id": pins.get("holdout_boundary_id"),
        }
        authority_block = _exact_object(
            document["authority"], label="authority", keys=AUTHORITY_RECEIPT_KEYS
        )
        if authority_block != expected_authority:
            raise UnsafeStateError("a run receipt names a different authority")
        expected_code = dict(authority.get("code") or {})
        code = _exact_object(
            document["code_identity"],
            label="code_identity",
            keys=frozenset(expected_code),
        )
        if code != expected_code:
            raise UnsafeStateError("a run receipt names a different code identity")
        run_id = _exact_str(document["run_id"], label="run_id")
        if HEX64.fullmatch(run_id) is None:
            raise UnsafeStateError("a run receipt has no immutable run identity")
        if run_row is not None:
            if str(run_row.get("run_id") or "") != run_id:
                raise UnsafeStateError("a run receipt names a different run")
            if str(run_row.get("started_at") or "") != _exact_str(
                document["started_at"], label="started_at"
            ):
                raise UnsafeStateError("a run receipt started_at disagrees with run_metadata")
            if str(run_row.get("ended_at") or "") != _exact_str(
                document["ended_at"], label="ended_at"
            ):
                raise UnsafeStateError("a run receipt ended_at disagrees with run_metadata")
            if str(run_row.get("stop_reason") or "") != _exact_str(
                document["stop_reason"], label="stop_reason"
            ):
                raise UnsafeStateError("a run receipt stop_reason disagrees with run_metadata")
            if int(run_row["network_calls"]) != _exact_int(
                document["network_calls"], label="network_calls"
            ):
                raise UnsafeStateError("a run receipt network_calls disagrees with run_metadata")
        predecessor = _exact_str(document["predecessor_sha256"], label="predecessor_sha256")
        if HEX64.fullmatch(predecessor) is None:
            raise UnsafeStateError("a run receipt predecessor is not a SHA-256 digest")
        if expect_predecessor is not None and predecessor != expect_predecessor:
            raise UnsafeStateError("a run receipt names a different predecessor")
        prefix = _exact_str(document["prefix_digest"], label="prefix_digest")
        if expect_prefix is not None and prefix != expect_prefix:
            raise UnsafeStateError("a run receipt prefix does not match state")
        if expect_marks is not None:
            documented = self._receipt_marks(document)
            if documented != dict(expect_marks):
                raise UnsafeStateError("a run receipt watermark disagrees with its seal")
        self._validate_run_receipt_facts(
            document,
            authority=authority,
            seal=seal,
            run_row=run_row,
            expect_marks=expect_marks,
        )
        if seal is not None:
            if str(seal.get("run_id") or "") != run_id:
                raise UnsafeStateError("a recorded seal link names a different run")
            if str(seal.get("predecessor_sha256") or "") != str(
                document.get("predecessor_sha256") or ""
            ):
                raise UnsafeStateError("a recorded seal link names a different predecessor")
            if str(seal.get("prefix_digest") or "") != str(document.get("prefix_digest") or ""):
                raise UnsafeStateError("a recorded seal link disagrees with its receipt digest")
            documented = self._receipt_marks(document)
            if {key: int(dict(seal.get("marks") or {}).get(key, -1)) for key in documented} != documented:
                raise UnsafeStateError(
                    "a recorded seal link disagrees with its receipt watermarks"
                )
        if require_publication:
            self._authenticate_run_publication(
                run_id,
                sha256_bytes(canonical_json(document)),
                document,
            )
        return schema

    def authenticate_prefix(self) -> None:
        """Authenticate the complete receipt lineage back to the installed plan receipt.

        Every link is rehashed from its accepted receipt root, proved to be canonical
        JSON of the accepted schema and authority, and required to name its predecessor
        and carry monotone in-range watermarks. The sealed prefix is then recomputed at
        the head's exact watermarks, so no fact inside it can be rewritten or deleted.
        """

        head = self.seal_head_row()
        if head is None:
            if self.has_plan():
                raise UnsafeStateError("the authenticated seal head is missing")
            return
        authority = self.authority_row()
        record = self._read_receipt(
            Path(head["receipt_path"]), expect=head["receipt_sha256"]
        )
        document = dict(record["document"])
        marks = {key: int(head[key]) for key in self._zero_watermarks()}
        schema = str(document.get("schema_version") or "")
        head_seal = (
            self.seal_fact(head["receipt_sha256"]) if schema == RUN_SCHEMA else None
        )
        run_row = None
        if schema == RUN_SCHEMA:
            run_row = self.run_metadata_row(str(document.get("run_id") or ""))
        schema = self._validate_receipt_document(
            document,
            authority=authority,
            seal=head_seal,
            run_row=run_row,
            expect_predecessor=str(head["predecessor_sha256"] or "") or None,
            expect_marks=marks if schema == RUN_SCHEMA else None,
            expect_prefix=head["prefix_digest"] if schema == RUN_SCHEMA else None,
        )
        if schema == RUN_SCHEMA:
            documented = self._receipt_marks(document)
            if documented != marks:
                raise UnsafeStateError(
                    "the seal head watermarks do not equal its receipt",
                    context={"head": marks, "receipt": documented},
                )
            if str(document.get("prefix_digest") or "") != head["prefix_digest"]:
                raise UnsafeStateError("the seal head digest does not equal its receipt")
            if head_seal is None:
                raise UnsafeStateError("the seal head has no recorded seal link")
            if (
                head_seal["predecessor_sha256"] != str(head["predecessor_sha256"] or "")
                or head_seal["prefix_digest"] != head["prefix_digest"]
                or {key: int(head_seal["marks"].get(key, -1)) for key in marks} != marks
            ):
                raise UnsafeStateError(
                    "the recorded seal link disagrees with the head it sealed"
                )
        elif any(marks.values()) or head["predecessor_sha256"] is not None:
            raise UnsafeStateError("the installed plan receipt head is not empty")
        self._walk_chain(head, document, schema, authority)
        actual = self._prefix_digest_unlocked(marks)
        if actual != head["prefix_digest"]:
            raise UnsafeStateError(
                "authenticated prefix was rewritten or deleted",
                context={"expected": head["prefix_digest"], "actual": actual},
            )
        self._recover_published_receipt_head()
        self._recover_unfinished_run()

    def _walk_chain(
        self,
        head: Mapping[str, Any],
        document: Mapping[str, Any],
        schema: str,
        authority: Mapping[str, Any],
    ) -> None:
        """Follow every predecessor link back to the installed plan receipt."""

        plan_receipt = str(authority["plan_receipt_sha256"])
        if schema == PLAN_SCHEMA:
            if str(head["receipt_sha256"]) != plan_receipt:
                raise UnsafeStateError(
                    "the chain head is a plan receipt of a different plan"
                )
            return
        limit = int(self._db().execute("SELECT COUNT(*) FROM run_seal").fetchone()[0]) + 2
        current_digest = str(head["receipt_sha256"])
        current_document = dict(document)
        current_marks = self._receipt_marks(current_document)
        hint = Path(head["receipt_path"])
        for _step in range(limit):
            predecessor = str(current_document.get("predecessor_sha256") or "")
            if not predecessor:
                raise UnsafeStateError(
                    "a run receipt in the chain names no predecessor",
                    context={"receipt": current_digest},
                )
            path = self._find_receipt(predecessor, hint)
            record = self._read_receipt(path, expect=predecessor)
            previous = dict(record["document"])
            previous_seal = self.seal_fact(predecessor)
            previous_run = None
            if str(previous.get("schema_version") or "") == RUN_SCHEMA:
                previous_run = self.run_metadata_row(str(previous.get("run_id") or ""))
            previous_schema = self._validate_receipt_document(
                previous,
                authority=authority,
                seal=previous_seal if previous_seal is not None else None,
                run_row=previous_run,
            )
            if previous_schema == PLAN_SCHEMA:
                if predecessor != plan_receipt:
                    raise UnsafeStateError(
                        "the chain terminates at a different plan receipt",
                        context={"expected": plan_receipt, "actual": predecessor},
                    )
                return
            previous_marks = self._receipt_marks(previous)
            for key, value in previous_marks.items():
                if value > current_marks[key]:
                    raise UnsafeStateError(
                        "a chain predecessor claims a later watermark than its successor",
                        context={"mark": key},
                    )
            seal = self.seal_fact(predecessor)
            if seal is None:
                raise UnsafeStateError(
                    "a chain predecessor has no recorded seal link",
                    context={"receipt": predecessor},
                )
            if seal["prefix_digest"] != str(previous.get("prefix_digest") or ""):
                raise UnsafeStateError(
                    "a recorded seal link disagrees with its receipt",
                    context={"receipt": predecessor},
                )
            if {
                key: int(seal["marks"].get(key, -1)) for key in previous_marks
            } != previous_marks:
                raise UnsafeStateError(
                    "a recorded seal link disagrees with its receipt watermarks",
                    context={"receipt": predecessor},
                )
            if seal["predecessor_sha256"] != str(
                previous.get("predecessor_sha256") or ""
            ):
                raise UnsafeStateError(
                    "a recorded seal link names a different predecessor",
                    context={"receipt": predecessor},
                )
            current_digest = predecessor
            current_document = previous
            current_marks = previous_marks
            hint = path
        raise UnsafeStateError("the authenticated receipt chain does not terminate")

    def _recover_published_receipt_head(self) -> None:
        """Resume every unfinished publication prefix from durable receipt intent."""

        head = self.seal_head_row()
        if head is None:
            return
        db = self._db()
        missing = db.execute(
            "SELECT run_id FROM run_metadata WHERE ended_at IS NOT NULL AND NOT EXISTS "
            "(SELECT 1 FROM run_publication p WHERE p.run_id = run_metadata.run_id) "
            "ORDER BY seq LIMIT 2"
        ).fetchall()
        BOUND_TELEMETRY.note("max_recover_rows", len(missing))
        BOUND_TELEMETRY.note("max_cursor_rows", len(missing))
        if missing:
            raise UnsafeStateError(
                "a finished run has no durable receipt intent",
                context={"run_id": str(missing[0][0])},
            )
        unpublished = db.execute(
            "SELECT run_id FROM run_metadata WHERE ended_at IS NOT NULL AND NOT EXISTS "
            "(SELECT 1 FROM run_seal s WHERE s.run_id = run_metadata.run_id) "
            "ORDER BY seq LIMIT 2"
        ).fetchall()
        BOUND_TELEMETRY.note("max_recover_rows", len(unpublished))
        BOUND_TELEMETRY.note("max_cursor_rows", len(unpublished))
        if len(unpublished) > 1:
            raise UnsafeStateError("finished runs with no recorded seal are ambiguous")
        if unpublished:
            self.complete_publication(str(unpublished[0][0]))
            return
        row = db.execute(
            "SELECT run_id, receipt_sha256 FROM run_seal ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return
        latest_run = str(row[0])
        latest = str(row[1])
        if latest == head["receipt_sha256"]:
            return
        self.complete_publication(latest_run)

    def _recover_unfinished_run(self) -> None:
        """Finalize an interrupted run under its own identity before any new run starts."""

        db = self._db()
        rows = db.execute(
            "SELECT run_id FROM run_metadata WHERE ended_at IS NULL ORDER BY seq LIMIT 2"
        ).fetchall()
        BOUND_TELEMETRY.note("max_recover_rows", len(rows))
        BOUND_TELEMETRY.note("max_cursor_rows", len(rows))
        if len(rows) > 1:
            raise UnsafeStateError("unfinished runs are ambiguous")
        if not rows:
            return
        self._finalize_interrupted_run(str(rows[0][0]))

    def _attempt_sample_between(self, lo: int, hi: int) -> list[str]:
        rows = self._db().execute(
            "SELECT redacted_fact_json FROM attempt WHERE id > ? AND id <= ? "
            "ORDER BY id LIMIT ?",
            (int(lo), int(hi), NETWORK_SAMPLE_CEILING),
        ).fetchall()
        BOUND_TELEMETRY.note("max_cursor_rows", len(rows))
        sample: list[str] = []
        for row in rows:
            fact = json.loads(str(row[0]))
            url = fact.get("url")
            if type(url) is str:
                sample.append(url)
            if len(sample) >= NETWORK_SAMPLE_CEILING:
                break
        return sample

    def note_run_error(self) -> None:
        """Record one coordinator-owned worker failure for the open run."""

        run_id = self._open_run_id
        if run_id is None:
            raise UnsafeStateError("a run error has no open run")
        db = self._db()
        with self._lock:
            updated = db.execute(
                "UPDATE run_metadata SET error_count = error_count + 1 "
                "WHERE run_id=? AND ended_at IS NULL",
                (run_id,),
            )
            if updated.rowcount != 1:
                raise UnsafeStateError("a run error was not recorded")

    def note_run_capacity_blocked(self) -> None:
        """Record that the open run crossed the capacity guard."""

        run_id = self._open_run_id
        if run_id is None:
            raise UnsafeStateError("a capacity block has no open run")
        db = self._db()
        with self._lock:
            updated = db.execute(
                "UPDATE run_metadata SET capacity_blocked = 1 "
                "WHERE run_id=? AND ended_at IS NULL",
                (run_id,),
            )
            if updated.rowcount != 1:
                raise UnsafeStateError("a capacity block was not recorded")

    def _finalize_interrupted_run(self, run_id: str) -> None:
        head = self.seal_head_row()
        if head is None:
            raise UnsafeStateError("the authenticated seal head is missing")
        pred_marks = {key: int(head[key]) for key in WATERMARK_KEYS}
        marks = self.current_watermarks()
        attempt_delta = int(self._counts_at(marks)["attempts"]) - int(
            self._counts_at(pred_marks)["attempts"]
        )
        if self.filesystem is None:
            raise UnsafeStateError("publication cannot proceed without a bound filesystem")
        post = self._capacity_snapshot(
            available_bytes=int(self.filesystem.available_bytes(self.run_receipt_dir))
        )
        run_row = self.run_metadata_row(run_id)
        if run_row is None:
            raise UnsafeStateError("an unfinished run disappeared")
        pre = self._parse_capacity_fact(run_row["pre_capacity"], label="pre_capacity")
        sample = self._attempt_sample_between(pred_marks["attempt_hi"], marks["attempt_hi"])
        stored_blocked = bool(run_row["capacity_blocked"])
        post_blocked = post["storage_preflight_state"] == "blocked"
        receipt = self.finish_run(
            run_id,
            ended_at=datetime.now(UTC).isoformat(),
            stop_reason="interrupted",
            receipt_sha256=None,
            network_calls=attempt_delta,
            error_count=int(run_row["error_count"]),
            network_sample=sample,
            pre_capacity=pre,
            post_capacity=post,
            capacity_blocked=stored_blocked or post_blocked,
            receipt_directory=str(self.run_receipt_dir),
            authority_block=self._receipt_authority_block(),
            code_identity=dict(self.authority_row()["code"]),
        )
        if receipt is None:
            raise UnsafeStateError("interrupted run finalization produced no receipt intent")
        self.complete_publication(run_id)

    def advance_seal(
        self,
        *,
        receipt_sha256: str,
        receipt_path: str,
        prefix_digest: str,
        marks: Mapping[str, int],
        predecessor_sha256: str,
    ) -> None:
        db = self._db()
        with self._lock:
            updated = db.execute(
                "UPDATE seal_head SET receipt_sha256=?, receipt_path=?, prefix_digest=?, "
                "attempt_hi=?, completion_hi=?, sidecar_hi=?, charge_hi=?, transition_hi=?, "
                "run_hi=?, seal_hi=?, predecessor_sha256=? WHERE id=1 AND receipt_sha256=?",
                (
                    receipt_sha256,
                    receipt_path,
                    prefix_digest,
                    int(marks["attempt_hi"]),
                    int(marks["completion_hi"]),
                    int(marks["sidecar_hi"]),
                    int(marks["charge_hi"]),
                    int(marks["transition_hi"]),
                    int(marks["run_hi"]),
                    int(marks["seal_hi"]),
                    predecessor_sha256,
                    predecessor_sha256,
                ),
            )
            if updated.rowcount != 1:
                raise UnsafeStateError("the seal head was not advanced")

    def _zero_capacity_fact(self) -> dict[str, Any]:
        return {
            "stable_requirement_bytes": 0,
            "operating_reserve_bytes": 0,
            "total_future_storage_bytes": 0,
            "available_bytes": 0,
            "next_transfer_bytes": 0,
            "needed_bytes": 0,
            "storage_preflight_state": "sufficient",
            "reserve_floor_bytes": 0,
            "stable_components": {"stable_requirement_bytes": 0},
        }

    def _zero_counts_fact(self) -> dict[str, int]:
        return {
            "planned": 0,
            "completed": 0,
            "attempts": 0,
            "gaps": 0,
            "coinalyze_charged": 0,
        }

    def _listed_bytes_at(self, completion_hi: int) -> int:
        return int(
            self._db().execute(
                "SELECT COALESCE(SUM(listed_bytes), 0) FROM completion WHERE seq <= ?",
                (int(completion_hi),),
            ).fetchone()[0]
        )

    def _sealed_charged_at(self, *, charge_hi: int, transition_hi: int) -> int:
        return int(
            self._db().execute(
                "SELECT COALESCE(SUM(c.charged_bytes), 0) FROM coinalyze_charge c "
                "WHERE c.seq <= ? AND (SELECT t.status FROM charge_transition t "
                "WHERE t.provider = c.provider AND t.identity = c.identity "
                "AND t.generation = c.generation AND t.seq <= ? "
                f"ORDER BY t.seq DESC LIMIT 1) IS NOT '{CHARGE_RELEASED}'",
                (int(charge_hi), int(transition_hi)),
            ).fetchone()[0]
        )

    def _semantic_at(self, prefix: str, marks: Mapping[str, int]) -> str:
        hasher = hashlib.sha256()
        hasher.update(prefix.encode("ascii"))
        hasher.update(
            compact_json(
                {
                    "section": "live_ledger",
                    "charged": self._sealed_charged_at(
                        charge_hi=int(marks["charge_hi"]),
                        transition_hi=int(marks["transition_hi"]),
                    ),
                }
            )
        )
        return hasher.hexdigest()

    def _open_charges_at(self, *, charge_hi: int, transition_hi: int) -> int:
        return int(
            self._db().execute(
                "SELECT COUNT(*) FROM coinalyze_charge c WHERE c.seq <= ? AND "
                "(SELECT t.status FROM charge_transition t WHERE t.provider = c.provider "
                "AND t.identity = c.identity AND t.generation = c.generation "
                "AND t.seq <= ? ORDER BY t.seq DESC LIMIT 1) IN (?, ?)",
                (int(charge_hi), int(transition_hi), CHARGE_RESERVED, CHARGE_PUBLISHED),
            ).fetchone()[0]
        )

    def _counts_at(self, marks: Mapping[str, int], *, gaps: int | None = None) -> dict[str, int]:
        db = self._db()
        planned = int(db.execute("SELECT COUNT(*) FROM plan_entry").fetchone()[0])
        completed = int(
            db.execute(
                "SELECT COUNT(*) FROM completion WHERE seq <= ?",
                (int(marks["completion_hi"]),),
            ).fetchone()[0]
        )
        attempts = int(
            db.execute(
                "SELECT COUNT(*) FROM attempt WHERE id <= ?",
                (int(marks["attempt_hi"]),),
            ).fetchone()[0]
        )
        if gaps is None:
            gap_count = int(db.execute("SELECT COUNT(*) FROM terminal_gap").fetchone()[0])
        else:
            gap_count = _exact_int(gaps, label="counts.gaps")
        return {
            "planned": planned,
            "completed": completed,
            "attempts": attempts,
            "gaps": gap_count,
            "coinalyze_charged": self._sealed_charged_at(
                charge_hi=int(marks["charge_hi"]),
                transition_hi=int(marks["transition_hi"]),
            ),
        }

    def _require_runnable_head(self) -> None:
        db = self._db()
        opened = db.execute(
            "SELECT run_id FROM run_metadata WHERE ended_at IS NULL ORDER BY seq LIMIT 2"
        ).fetchall()
        BOUND_TELEMETRY.note("max_recover_rows", len(opened))
        BOUND_TELEMETRY.note("max_cursor_rows", len(opened))
        if len(opened) > 1:
            raise UnsafeStateError("unfinished runs are ambiguous")
        if opened:
            raise UnsafeStateError(
                "an unfinished run is still open",
                context={"run_id": str(opened[0][0])},
            )
        head = self.seal_head_row()
        if head is None:
            raise UnsafeStateError("the authenticated seal head is missing")
        current = self.current_watermarks()
        for key in (
            "attempt_hi",
            "completion_hi",
            "sidecar_hi",
            "charge_hi",
            "transition_hi",
            "run_hi",
        ):
            if int(current[key]) != int(head[key]):
                raise UnsafeStateError(
                    "an unsealed fact tail remains",
                    context={"mark": key, "head": int(head[key]), "actual": int(current[key])},
                )
        seal_hi = int(current["seal_hi"])
        head_seal = int(head["seal_hi"])
        if seal_hi == head_seal:
            return
        if seal_hi != head_seal + 1:
            raise UnsafeStateError("an unsealed fact tail remains", context={"mark": "seal_hi"})
        own = self.seal_fact(str(head["receipt_sha256"]))
        if own is None or int(own["seq"]) != seal_hi:
            raise UnsafeStateError("the seal head does not own its current seal link")

    def begin_run(
        self,
        run_id: str,
        started_at: str,
        *,
        pre_capacity: Mapping[str, Any] | None = None,
    ) -> None:
        self._require_runnable_head()
        head = self.seal_head_row()
        if head is None:
            raise UnsafeStateError("the authenticated seal head is missing")
        marks = {key: int(head[key]) for key in WATERMARK_KEYS}
        if pre_capacity is None:
            if self.filesystem is None:
                raise UnsafeStateError("run start is missing pre_capacity")
            pre_capacity = self._capacity_snapshot(
                available_bytes=int(self.filesystem.available_bytes(self.run_receipt_dir))
            )
        pre = self._parse_capacity_fact(pre_capacity, label="pre_capacity")
        snapshot = {
            **marks,
            "gaps": int(
                self._db().execute("SELECT COUNT(*) FROM terminal_gap").fetchone()[0]
            ),
            "listed_bytes": self._listed_bytes_at(int(marks["completion_hi"])),
        }
        with self._lock:
            self._db().execute(
                "INSERT INTO run_metadata(run_id, started_at, ended_at, stop_reason, "
                "attempt_hi, network_calls, start_snapshot_json, error_count, "
                "network_sample_json, pre_capacity_json, post_capacity_json, "
                "capacity_blocked, attempt_delta, completion_delta, gap_delta, "
                "byte_delta, open_coinalyze_charges, counts_json) "
                "VALUES (?, ?, NULL, NULL, ?, 0, ?, 0, ?, ?, ?, 0, 0, 0, 0, 0, 0, ?)",
                (
                    run_id,
                    started_at,
                    int(marks["attempt_hi"]),
                    compact_json(snapshot).decode("utf-8"),
                    compact_json([]).decode("utf-8"),
                    compact_json(pre).decode("utf-8"),
                    compact_json(pre).decode("utf-8"),
                    compact_json(self._zero_counts_fact()).decode("utf-8"),
                ),
            )
            self._open_run_id = run_id

    def finish_run(
        self,
        run_id: str,
        *,
        ended_at: str,
        stop_reason: str,
        receipt_sha256: str | None,
        network_calls: int,
        error_count: int = 0,
        network_sample: Sequence[str] = (),
        pre_capacity: Mapping[str, Any] | None = None,
        post_capacity: Mapping[str, Any] | None = None,
        capacity_blocked: bool = False,
        receipt_directory: str | None = None,
        authority_block: Mapping[str, Any] | None = None,
        code_identity: Mapping[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Finalize the run and persist exact canonical receipt intent in one transaction."""

        _ = receipt_sha256
        db = self._db()
        with self._lock:
            db.execute("BEGIN IMMEDIATE")
            try:
                existing = db.execute(
                    "SELECT start_snapshot_json, error_count, capacity_blocked "
                    "FROM run_metadata WHERE run_id=? AND ended_at IS NULL",
                    (run_id,),
                ).fetchone()
                if existing is None:
                    published = db.execute(
                        "SELECT receipt_body FROM run_publication WHERE run_id=?",
                        (run_id,),
                    ).fetchone()
                    db.execute("COMMIT")
                    if published is None:
                        raise UnsafeStateError(
                            "run_metadata was not sealed for this invocation",
                            context={"run_id": run_id},
                        )
                    self._open_run_id = None
                    return json.loads(str(published[0]))
                if authority_block is None or code_identity is None or receipt_directory is None:
                    raise UnsafeStateError("run finalization is missing durable receipt identity")
                directory_path = Path(_exact_str(str(receipt_directory), label="receipt_directory"))
                if directory_path != self.run_receipt_dir:
                    raise UnsafeStateError(
                        "run finalization names a different run receipt directory"
                    )
                start = self._parse_start_snapshot(json.loads(str(existing[0])))
                head = self.seal_head_row()
                if head is None:
                    raise UnsafeStateError("the authenticated seal head is missing")
                pred_marks = {key: int(head[key]) for key in WATERMARK_KEYS}
                for key in WATERMARK_KEYS:
                    if start[key] != pred_marks[key]:
                        raise UnsafeStateError(
                            "a run start snapshot disagrees with its predecessor watermarks",
                            context={"mark": key},
                        )
                if start["listed_bytes"] != self._listed_bytes_at(
                    int(pred_marks["completion_hi"])
                ):
                    raise UnsafeStateError(
                        "a run start snapshot disagrees with predecessor completions"
                    )
                pred_run = self._predecessor_run_row(str(head["receipt_sha256"]))
                if pred_run is not None and start["gaps"] != _exact_int(
                    pred_run["counts"]["gaps"], label="predecessor.counts.gaps"
                ):
                    raise UnsafeStateError("a run start snapshot disagrees with predecessor gaps")
                marks = self.current_watermarks()
                counts = self._counts_at(marks)
                start_counts_attempts = int(
                    db.execute(
                        "SELECT COUNT(*) FROM attempt WHERE id <= ?",
                        (pred_marks["attempt_hi"],),
                    ).fetchone()[0]
                )
                start_counts_completed = int(
                    db.execute(
                        "SELECT COUNT(*) FROM completion WHERE seq <= ?",
                        (pred_marks["completion_hi"],),
                    ).fetchone()[0]
                )
                attempt_delta = int(counts["attempts"]) - start_counts_attempts
                completion_delta = int(counts["completed"]) - start_counts_completed
                gap_delta = int(counts["gaps"]) - start["gaps"]
                byte_delta = self._listed_bytes_at(int(marks["completion_hi"])) - start[
                    "listed_bytes"
                ]
                open_charges = self._open_charges_at(
                    charge_hi=int(marks["charge_hi"]),
                    transition_hi=int(marks["transition_hi"]),
                )
                pre = self._parse_capacity_fact(
                    pre_capacity if pre_capacity is not None else self._zero_capacity_fact(),
                    label="pre_capacity",
                )
                post = self._parse_capacity_fact(
                    post_capacity if post_capacity is not None else self._zero_capacity_fact(),
                    label="post_capacity",
                )
                sample = _exact_str_list(
                    list(network_sample),
                    label="network_sample",
                    ceiling=NETWORK_SAMPLE_CEILING,
                )
                ended = _exact_str(ended_at, label="ended_at")
                reason = _exact_str(stop_reason, label="stop_reason")
                network_calls_n = _exact_int(network_calls, label="network_calls")
                durable_errors = _exact_int(int(existing[1]), label="error_count")
                if _exact_int(error_count, label="error_count") != durable_errors:
                    raise UnsafeStateError("run error_count disagrees with durable worker errors")
                error_count_n = durable_errors
                stored_blocked = bool(int(existing[2]))
                caller_blocked = _exact_bool(capacity_blocked, label="capacity_blocked")
                post_blocked = post["storage_preflight_state"] == "blocked"
                blocked = stored_blocked or caller_blocked or post_blocked or reason == "capacity"
                if network_calls_n != attempt_delta:
                    raise UnsafeStateError("network-call count does not equal durable attempt delta")
                authority_fact = _exact_object(
                    dict(authority_block), label="authority", keys=AUTHORITY_RECEIPT_KEYS
                )
                code_fact = _exact_object(
                    dict(code_identity),
                    label="code_identity",
                    keys=frozenset(dict(code_identity)),
                )
                updated = db.execute(
                    "UPDATE run_metadata SET ended_at=?, stop_reason=?, attempt_hi=?, "
                    "network_calls=?, error_count=?, network_sample_json=?, "
                    "pre_capacity_json=?, post_capacity_json=?, capacity_blocked=?, "
                    "attempt_delta=?, completion_delta=?, gap_delta=?, byte_delta=?, "
                    "open_coinalyze_charges=?, counts_json=? WHERE run_id=? AND ended_at IS NULL",
                    (
                        ended,
                        reason,
                        int(marks["attempt_hi"]),
                        network_calls_n,
                        error_count_n,
                        compact_json(sample).decode("utf-8"),
                        compact_json(pre).decode("utf-8"),
                        compact_json(post).decode("utf-8"),
                        1 if blocked else 0,
                        attempt_delta,
                        completion_delta,
                        gap_delta,
                        byte_delta,
                        open_charges,
                        compact_json(counts).decode("utf-8"),
                        run_id,
                    ),
                )
                if updated.rowcount != 1:
                    raise UnsafeStateError(
                        "run_metadata was not sealed for this invocation",
                        context={"run_id": run_id},
                    )
                prefix = self._prefix_digest_unlocked(marks)
                semantic = self._semantic_at(prefix, marks)
                row = self.run_metadata_row(run_id)
                if row is None:
                    raise UnsafeStateError("run_metadata disappeared while finalizing")
                head = self.seal_head_row()
                if head is None:
                    raise UnsafeStateError("the authenticated seal head is missing")
                receipt = {
                    "schema_version": RUN_SCHEMA,
                    "ticket": TICKET_ID,
                    "policy_identity": POLICY_IDENTITY,
                    "plan_identity": str(self.plan_identity()),
                    "run_id": run_id,
                    "authority": authority_fact,
                    "code_identity": code_fact,
                    "started_at": row["started_at"],
                    "ended_at": ended,
                    "stop_reason": reason,
                    "attempt_delta": attempt_delta,
                    "completion_delta": completion_delta,
                    "gap_delta": gap_delta,
                    "byte_delta": byte_delta,
                    "network_calls": network_calls_n,
                    "attempts": attempt_delta,
                    "error_count": error_count_n,
                    "network_sample": sample,
                    "pre_capacity": pre,
                    "post_capacity": post,
                    "capacity_blocked": blocked,
                    "open_coinalyze_charges": open_charges,
                    "semantic_state_digest": semantic,
                    "prefix_digest": prefix,
                    "high_watermarks": marks,
                    "predecessor_sha256": head["receipt_sha256"],
                    "counts": counts,
                }
                self._validate_receipt_document(
                    receipt,
                    authority=self.authority_row(),
                    run_row=row,
                    expect_predecessor=head["receipt_sha256"],
                    expect_marks=marks,
                    expect_prefix=prefix,
                    require_publication=False,
                )
                body = canonical_json(receipt)
                digest = sha256_bytes(body)
                db.execute(
                    "INSERT INTO run_publication(run_id, receipt_sha256, receipt_directory, "
                    "receipt_body) VALUES (?, ?, ?, ?)",
                    (run_id, digest, str(directory_path), body.decode("utf-8")),
                )
                db.execute("COMMIT")
                self._open_run_id = None
                return receipt
            except Exception:
                db.execute("ROLLBACK")
                raise

    def complete_publication(
        self,
        run_id: str,
        *,
        filesystem: Filesystem | None = None,
        device: str | None = None,
        roots: BoundRoots | None = None,
        fault: FaultInjector | None = None,
    ) -> dict[str, Any]:
        """Publish or re-prove receipt, locator, seal, and head from durable intent."""

        fault = fault or FaultInjector()
        filesystem = filesystem or self.filesystem
        device = device or self.publication_device
        roots = roots or self.roots
        if filesystem is None or device is None or roots is None:
            raise UnsafeStateError("publication cannot proceed without a bound filesystem")
        db = self._db()
        with self._lock:
            intent = db.execute(
                "SELECT receipt_sha256, receipt_directory, receipt_body "
                "FROM run_publication WHERE run_id=?",
                (run_id,),
            ).fetchone()
            if intent is None:
                raise UnsafeStateError(
                    "a finished run has no durable receipt intent",
                    context={"run_id": run_id},
                )
            digest = _exact_str(intent[0], label="receipt_sha256")
            if HEX64.fullmatch(digest) is None:
                raise UnsafeStateError("a receipt intent identity is malformed")
            directory = Path(_exact_str(intent[1], label="receipt_directory"))
            if directory != self.run_receipt_dir:
                raise UnsafeStateError(
                    "a receipt intent names a different run receipt directory",
                    context={"run_id": run_id},
                )
            body_text = _exact_str(intent[2], label="receipt_body")
            body = body_text.encode("utf-8")
            try:
                document = json.loads(body_text)
            except (ValueError, TypeError) as exc:
                raise UnsafeStateError("a receipt intent is malformed") from exc
            if type(document) is not dict:
                raise UnsafeStateError("a receipt intent is not an object")
            if canonical_json(document) != body:
                raise UnsafeStateError("a receipt intent is not canonical JSON")
            if sha256_bytes(body) != digest:
                raise UnsafeStateError("a receipt intent identity conflicts with its body")
            run_row = self.run_metadata_row(run_id)
            if run_row is None or run_row["ended_at"] is None:
                raise UnsafeStateError("a receipt intent has no finished run_metadata")
            authority = self.authority_row()
            head = self.seal_head_row()
            if head is None:
                raise UnsafeStateError("the authenticated seal head is missing")
            existing_seal = self.seal_fact(digest)
            expect_predecessor = (
                existing_seal["predecessor_sha256"]
                if existing_seal is not None
                else head["receipt_sha256"]
            )
            self._validate_receipt_document(
                document,
                authority=authority,
                seal=existing_seal,
                run_row=run_row,
                expect_predecessor=expect_predecessor,
            )
            predecessor = _exact_str(document["predecessor_sha256"], label="predecessor_sha256")
            marks = self._receipt_marks(document)
            prefix = _exact_str(document["prefix_digest"], label="prefix_digest")
            if prefix != self._prefix_digest_unlocked(marks):
                raise UnsafeStateError("a recorded run receipt prefix does not match state")
            if existing_seal is None:
                for key, value in marks.items():
                    if value < int(head[key]):
                        raise UnsafeStateError(
                            "a recorded run receipt moves a watermark backwards",
                            context={"mark": key},
                        )
            fault.check("before_run_receipt_publication", run_id)
            published = write_named_receipt(
                document, directory, str(device), filesystem, roots=roots
            )
            if str(published["sha256"]) != digest:
                raise UnsafeStateError("published receipt identity conflicts with intent")
            fault.check("after_run_receipt_publication", run_id)
            fault.check("before_run_locator_publication", run_id)
            write_run_locator(
                run_id, digest, directory, str(device), filesystem, roots=roots
            )
            fault.check("after_run_locator_publication", run_id)
            fault.check("before_run_seal_insert", run_id)
            if existing_seal is None:
                db.execute(
                    "INSERT INTO run_seal(run_id, receipt_sha256, predecessor_sha256, "
                    "prefix_digest, marks_json) VALUES (?, ?, ?, ?, ?)",
                    (
                        run_id,
                        digest,
                        predecessor,
                        prefix,
                        compact_json(dict(marks)).decode("utf-8"),
                    ),
                )
            else:
                recorded_marks = {
                    key: int(existing_seal["marks"].get(key, -1)) for key in marks
                }
                if (
                    existing_seal["run_id"] != run_id
                    or existing_seal["predecessor_sha256"] != predecessor
                    or existing_seal["prefix_digest"] != prefix
                    or recorded_marks != marks
                ):
                    raise UnsafeStateError("a recorded seal link disagrees with its receipt")
            fault.check("after_run_seal_insert", run_id)
            fault.check("before_seal_head_cas", run_id)
            current = self.seal_head_row()
            if current is None:
                raise UnsafeStateError("the authenticated seal head is missing")
            if current["receipt_sha256"] == digest:
                documented = {key: int(current[key]) for key in marks}
                if (
                    documented != marks
                    or current["prefix_digest"] != prefix
                    or str(current["receipt_path"]) != str(published["path"])
                    or str(current["predecessor_sha256"] or "") != predecessor
                ):
                    raise UnsafeStateError("the seal head disagrees with its receipt intent")
            elif current["receipt_sha256"] == predecessor:
                self.advance_seal(
                    receipt_sha256=digest,
                    receipt_path=str(published["path"]),
                    prefix_digest=prefix,
                    marks=marks,
                    predecessor_sha256=predecessor,
                )
            else:
                raise UnsafeStateError(
                    "a recorded seal link does not name the current head",
                    context={"run_id": run_id},
                )
            fault.check("after_seal_head_cas", run_id)
            return published

    def pending_count(self) -> int:
        row = self._db().execute(
            "SELECT COUNT(*) FROM plan_entry WHERE kind != ? AND NOT EXISTS ("
            "SELECT 1 FROM completion c WHERE c.provider=plan_entry.provider "
            "AND c.identity=plan_entry.identity)",
            (KIND_COINALYZE_UNSUPPORTED,),
        ).fetchone()
        return int(row[0])

    def open_charge_count(self) -> int:
        row = self._db().execute(
            "SELECT COUNT(*) FROM coinalyze_charge c WHERE "
            "(SELECT t.status FROM charge_transition t "
            "WHERE t.provider = c.provider AND t.identity = c.identity "
            "AND t.generation = c.generation "
            "ORDER BY t.seq DESC LIMIT 1) IN (?, ?)",
            (CHARGE_RESERVED, CHARGE_PUBLISHED),
        ).fetchone()
        return int(row[0])

    def typed_gap_present(self) -> bool:
        if self.counts()["gaps"]:
            return True
        row = self._db().execute(
            "SELECT 1 FROM completion WHERE validation_state IN (?, ?) LIMIT 1",
            (OUTCOME_EMPTY_HISTORY, OUTCOME_UNAVAILABLE),
        ).fetchone()
        return row is not None

    def unique_raw_content(self) -> tuple[int, int]:
        row = self._db().execute(
            "SELECT COUNT(*), COALESCE(SUM(sz), 0) FROM ("
            "SELECT content_sha256, MIN(listed_bytes) AS sz FROM completion "
            "GROUP BY content_sha256)"
        ).fetchone()
        return int(row[0]), int(row[1])

    def unique_sidecar_content(self) -> tuple[int, int]:
        row = self._db().execute(
            "SELECT COUNT(*), COALESCE(SUM(sz), 0) FROM ("
            "SELECT sidecar_sha256, MIN(sidecar_bytes) AS sz FROM sidecar_fact "
            "GROUP BY sidecar_sha256)"
        ).fetchone()
        return int(row[0]), int(row[1])

    def unique_physical(self) -> tuple[int, int]:
        """Unique physical objects and bytes: raw content plus sidecars, from SQL."""

        raw_n, raw_b = self.unique_raw_content()
        side_n, side_b = self.unique_sidecar_content()
        return raw_n + side_n, raw_b + side_b


def _completion_from_row(row: Sequence[Any]) -> CompletionFact:
    return CompletionFact(
        provider=str(row[0]),
        identity=str(row[1]),
        content_sha256=str(row[2]),
        content_path=str(row[3]),
        sidecar_sha256=None if row[4] is None else str(row[4]),
        sidecar_path=None if row[5] is None else str(row[5]),
        listed_bytes=int(row[6]),
        retrieved_at=str(row[7]),
        revision=json.loads(str(row[8])),
        validation_state=str(row[9]),
    )


def _require_bound(roots: BoundRoots | None, *, operation: str) -> BoundRoots:
    """Every production operation runs against the retained session descriptors."""

    if roots is None:
        raise UnsafeStateError(
            "a bound session capability is required",
            context={"operation": operation},
        )
    return roots


class BudgetExhausted(AcquisitionError):
    """The accepted Coinalyze allocation cannot fund another response."""


# --------------------------------------------------------------------------------------
# One shared streaming provider-semantic validator.
#
# Resume uses it before a completed object is skipped and offline verification uses it
# again; there is exactly one definition of what a completed provider object means.
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderProof:
    kind: str
    retained: bool
    content_bytes: int
    sidecar_bytes: int
    outcome: str
    points: int


def expected_liquidation_url(plan: PlanObject) -> str:
    return f"{plan.payload['url']}?{plan.payload['query']}"


def expected_liquidation_proof(plan: PlanObject) -> str:
    return sha256_bytes(
        compact_json(
            {"identity": plan.identity, "query": str(plan.payload.get("query") or "")}
        )
    )


def validate_charge_against_plan(
    plan: PlanObject,
    charge: Mapping[str, Any],
    completion: CompletionFact | None = None,
    *,
    require_settled: bool = False,
    history: Sequence[Mapping[str, Any]] | None = None,
) -> None:
    """Exact plan/descriptor/completion validator used at every charge boundary."""

    if plan.kind != KIND_COINALYZE_LIQUIDATION:
        raise UnsafeStateError(
            "a Coinalyze charge is not joined to a liquidation plan row",
            context={"identity": plan.identity},
        )
    retrieval = dict(charge.get("retrieval") or {})
    revision = dict(charge.get("revision") or {})
    if set(retrieval) != CHARGE_RETRIEVAL_KEYS:
        raise UnsafeStateError(
            "a Coinalyze retrieval document has the wrong key set",
            context={"identity": plan.identity, "keys": sorted(retrieval)},
        )
    if set(revision) != CHARGE_REVISION_KEYS:
        raise UnsafeStateError(
            "a Coinalyze revision document has the wrong key set",
            context={"identity": plan.identity, "keys": sorted(revision)},
        )
    http_status = int(charge["http_status"])
    outcome = str(charge["outcome"])
    points = int(charge["points"])
    if http_status not in {200, 404}:
        raise UnsafeStateError(
            "a Coinalyze charge HTTP status is not an accepted recovery status",
            context={"identity": plan.identity, "status": http_status},
        )
    if http_status == 404:
        if outcome != OUTCOME_UNAVAILABLE or points != 0:
            raise UnsafeStateError(
                "a Coinalyze 404 charge is not provider-unavailable",
                context={"identity": plan.identity},
            )
    elif outcome not in {OUTCOME_CHECKSUM_VERIFIED, OUTCOME_EMPTY_HISTORY}:
        raise UnsafeStateError(
            "a Coinalyze 200 charge has an invalid outcome",
            context={"identity": plan.identity},
        )
    if str(charge.get("request_proof") or "") != expected_liquidation_proof(plan):
        raise UnsafeStateError(
            "a Coinalyze request proof does not match the plan",
            context={"identity": plan.identity},
        )
    if str(retrieval.get("url") or "") != expected_liquidation_url(plan):
        raise UnsafeStateError(
            "a Coinalyze retrieval URL is not the exact planned request",
            context={"identity": plan.identity},
        )
    if int(retrieval.get("status") or 0) != http_status:
        raise UnsafeStateError(
            "a Coinalyze retrieval status disagrees with its descriptor",
            context={"identity": plan.identity},
        )
    retrieved_at = str(retrieval.get("retrieved_at") or "")
    created_at = str(charge.get("created_at") or "")
    if _utc_timestamp_ok(retrieved_at) != 1 or _utc_timestamp_ok(created_at) != 1:
        raise UnsafeStateError(
            "a Coinalyze charge timestamp is not UTC",
            context={"identity": plan.identity},
        )
    if retrieved_at > created_at:
        raise UnsafeStateError(
            "a Coinalyze retrieval is after its reservation",
            context={"identity": plan.identity},
        )
    if int(revision.get("status") or 0) != http_status or int(revision.get("points") or 0) != points:
        raise UnsafeStateError(
            "a Coinalyze revision disagrees with its descriptor",
            context={"identity": plan.identity},
        )
    generation = int(charge.get("generation") or 0)
    if generation < 1:
        raise UnsafeStateError(
            "a Coinalyze charge generation is not positive",
            context={"identity": plan.identity},
        )
    digest = str(charge["content_sha256"])
    charged_bytes = int(charge["charged_bytes"])
    if HEX64.fullmatch(digest) is None or charged_bytes < 0:
        raise UnsafeStateError(
            "a Coinalyze charge digest or byte count is invalid",
            context={"identity": plan.identity},
        )
    status = str(charge.get("status") or "")
    if require_settled and status != CHARGE_SETTLED:
        raise UnsafeStateError(
            "a Coinalyze charge is not settled",
            context={"identity": plan.identity, "status": status},
        )
    if history is not None:
        observed = [str(item["status"]) for item in history]
        if status == CHARGE_SETTLED and observed != [
            CHARGE_RESERVED,
            CHARGE_PUBLISHED,
            CHARGE_SETTLED,
        ]:
            raise UnsafeStateError(
                "a settled Coinalyze charge has an illegal transition history",
                context={"identity": plan.identity, "history": observed},
            )
        if status == CHARGE_PUBLISHED and observed not in (
            [CHARGE_RESERVED, CHARGE_PUBLISHED],
        ):
            raise UnsafeStateError(
                "a published Coinalyze charge has an illegal transition history",
                context={"identity": plan.identity, "history": observed},
            )
        if status == CHARGE_RESERVED and observed != [CHARGE_RESERVED]:
            raise UnsafeStateError(
                "a reserved Coinalyze charge has an illegal transition history",
                context={"identity": plan.identity, "history": observed},
            )
    if completion is None:
        return
    if (
        completion.content_sha256 != digest
        or int(completion.listed_bytes) != charged_bytes
        or completion.validation_state != outcome
        or int(dict(completion.revision).get("status") or 0) != http_status
        or int(dict(completion.revision).get("points") or 0) != points
        or str(completion.retrieved_at) != retrieved_at
        or compact_json(dict(completion.revision)) != compact_json(revision)
    ):
        raise UnsafeStateError(
            "a Coinalyze charge does not match its completion",
            context={"identity": plan.identity},
        )


def validate_provider_completion(
    plan: PlanObject,
    fact: CompletionFact,
    sidecar: Mapping[str, Any] | None,
    *,
    paths: AcquisitionPaths,
    pins: AuthorityPins,
    roots: BoundRoots | None = None,
) -> ProviderProof:
    if fact.provider != plan.provider or fact.identity != plan.identity:
        raise UnsafeStateError(
            "a completion is not joined to its exact plan row",
            context={"identity": plan.identity},
        )
    expected_path = content_path_for(paths.content_root, fact.content_sha256)
    if Path(fact.content_path) != expected_path:
        raise UnsafeStateError(
            "completed content is not at its content address",
            context={"identity": plan.identity},
        )
    fd = open_regular_file(paths.content_root, expected_path, roots=roots)
    try:
        digest, size = sha256_fd(fd)
        if digest != fact.content_sha256:
            raise UnsafeStateError(
                "completed content digest changed", context={"identity": plan.identity}
            )
        if size != fact.listed_bytes:
            raise UnsafeStateError(
                "completed content size does not match its recorded size",
                context={"identity": plan.identity, "recorded": fact.listed_bytes},
            )
        if plan.kind == KIND_BINANCE:
            listed = int(plan.payload["listed_bytes"])
            if size != listed:
                raise UnsafeStateError(
                    "completed content size does not match its exact plan row",
                    context={"identity": plan.identity, "planned": listed},
                )
            planned_retained = bool(plan.payload.get("retained"))
            recorded_retained = fact.validation_state == OUTCOME_RETAINED
            if planned_retained != recorded_retained:
                raise UnsafeStateError(
                    "retained label disagrees with plan provenance",
                    context={"identity": plan.identity},
                )
            if planned_retained:
                if digest != str(plan.payload.get("retained_digest") or ""):
                    raise UnsafeStateError(
                        "retained digest disagrees with plan provenance",
                        context={"identity": plan.identity},
                    )
                if size != int(plan.payload.get("retained_bytes") or -1):
                    raise UnsafeStateError(
                        "retained bytes disagree with plan provenance",
                        context={"identity": plan.identity},
                    )
                revision = dict(fact.revision)
                if (
                    "content_inode" not in revision
                    or "source_inode" not in revision
                    or "source_device" not in revision
                ):
                    raise UnsafeStateError(
                        "retained inode lineage is missing",
                        context={"identity": plan.identity},
                    )
                source_path = Path(str(plan.payload.get("retained_raw_source_path") or ""))
                source_root = paths.sample_dir
                source_fd = open_regular_file(source_root, source_path, roots=roots)
                try:
                    source_digest, source_size = sha256_fd(source_fd)
                    source_stat = os.fstat(source_fd)
                finally:
                    os.close(source_fd)
                dest_stat = os.fstat(fd)
                if source_digest != digest or source_size != size:
                    raise UnsafeStateError(
                        "retained source digest changed",
                        context={"identity": plan.identity},
                    )
                if (
                    int(source_stat.st_ino) != int(dest_stat.st_ino)
                    or int(source_stat.st_dev) != int(dest_stat.st_dev)
                    or int(revision["content_inode"]) != int(dest_stat.st_ino)
                    or int(revision["source_inode"]) != int(source_stat.st_ino)
                    or int(revision["source_device"]) != int(source_stat.st_dev)
                ):
                    raise UnsafeStateError(
                        "retained inode lineage changed",
                        context={"identity": plan.identity},
                    )
                planned_inode = plan.payload.get("retained_source_inode")
                planned_device = plan.payload.get("retained_source_device")
                if planned_inode is not None and int(planned_inode) != int(source_stat.st_ino):
                    raise UnsafeStateError(
                        "retained source inode disagrees with plan provenance",
                        context={"identity": plan.identity},
                    )
                if planned_device is not None and int(planned_device) != int(source_stat.st_dev):
                    raise UnsafeStateError(
                        "retained source device disagrees with plan provenance",
                        context={"identity": plan.identity},
                    )
                sidecar_src = Path(str(plan.payload.get("retained_sidecar_source_path") or ""))
                sidecar_fd = open_regular_file(
                    paths.listing_cache_dir, sidecar_src, roots=roots
                )
                try:
                    sidecar_digest, sidecar_size = sha256_fd(sidecar_fd)
                    sidecar_stat = os.fstat(sidecar_fd)
                finally:
                    os.close(sidecar_fd)
                expected_sidecar = str(plan.payload.get("retained_sidecar_digest") or "")
                if sidecar_digest != expected_sidecar:
                    raise UnsafeStateError(
                        "retained sidecar source digest changed",
                        context={"identity": plan.identity},
                    )
                if sidecar_size != int(plan.payload.get("retained_sidecar_bytes") or -1):
                    raise UnsafeStateError(
                        "retained sidecar source bytes changed",
                        context={"identity": plan.identity},
                    )
                if sidecar_digest != str(plan.payload.get("retained_sidecar_revision") or ""):
                    raise UnsafeStateError(
                        "retained sidecar source revision changed",
                        context={"identity": plan.identity},
                    )
                _ = sidecar_stat
                retrieval_time = str(plan.payload.get("retained_retrieval_time") or "")
                if retrieval_time and retrieval_time != str(fact.retrieved_at):
                    raise UnsafeStateError(
                        "retained retrieval time disagrees with plan provenance",
                        context={"identity": plan.identity},
                    )
            validate_zip_fd(fd)
        elif plan.kind == KIND_COINALYZE_LIQUIDATION:
            _validate_coinalyze_liquidation(plan, fact, fd, roots=roots)
        elif plan.kind == KIND_COINALYZE_INVENTORY:
            if fact.validation_state != OUTCOME_RETAINED_INVENTORY:
                raise UnsafeStateError(
                    "the retained Coinalyze inventory has the wrong outcome",
                    context={"identity": plan.identity},
                )
            accepted = str(plan.payload.get("accepted_digest") or "")
            if digest != accepted:
                raise UnsafeStateError(
                    "retained Coinalyze inventory digest changed",
                    context={"identity": plan.identity},
                )
            accepted_bytes = int(plan.payload.get("accepted_bytes") or -1)
            if accepted_bytes > 0 and size != accepted_bytes:
                raise UnsafeStateError(
                    "retained Coinalyze inventory size changed",
                    context={"identity": plan.identity},
                )
            os.lseek(fd, 0, os.SEEK_SET)
            body = read_fd(fd)
            _reparse_inventory_mappings(body, plan)
        else:
            raise UnsafeStateError(
                "a completion has an unplannable kind", context={"kind": plan.kind}
            )
    finally:
        os.close(fd)
    sidecar_bytes = 0
    if plan.kind == KIND_BINANCE:
        sidecar_bytes = _validate_binance_sidecar(plan, fact, sidecar, paths=paths, roots=roots)
    elif sidecar is not None:
        raise UnsafeStateError(
            "a Coinalyze completion carries a Binance sidecar fact",
            context={"identity": plan.identity},
        )
    retained = bool(plan.payload.get("retained")) if plan.kind == KIND_BINANCE else False
    points = 0
    if plan.kind == KIND_COINALYZE_LIQUIDATION and fact.validation_state in {
        OUTCOME_CHECKSUM_VERIFIED,
        OUTCOME_EMPTY_HISTORY,
    }:
        points = int(dict(fact.revision).get("points") or 0)
    return ProviderProof(
        kind=plan.kind,
        retained=retained,
        content_bytes=fact.listed_bytes,
        sidecar_bytes=sidecar_bytes,
        outcome=fact.validation_state,
        points=points,
    )


def _reparse_inventory_mappings(body: bytes, plan: PlanObject) -> None:
    try:
        markets = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UnsafeStateError("retained Coinalyze inventory is not JSON") from exc
    if not isinstance(markets, list):
        raise UnsafeStateError("retained Coinalyze inventory is not a list")
    native_to_provider: dict[str, str] = {}
    for row in markets:
        if not isinstance(row, dict):
            continue
        if str(row.get("exchange")) != COINALYZE_EXCHANGE_CODE:
            continue
        if not bool(row.get("is_perpetual")):
            continue
        native = str(row.get("symbol_on_exchange") or "").strip().upper()
        provider = str(row.get("symbol") or "")
        if not native or provider != coinalyze_perp_symbol(native):
            continue
        if native in native_to_provider:
            raise UnsafeStateError(
                "retained Coinalyze inventory has a duplicate native identity"
            )
        native_to_provider[native] = provider
    accepted_pairs = sorted(
        (str(item.get("native_symbol")), str(item.get("provider_symbol")))
        for item in list(plan.payload.get("accepted_mappings") or ())
        if isinstance(item, dict)
    )
    expected_count = int(plan.payload.get("inventory_mapping_count") or 0)
    expected_digest = str(plan.payload.get("inventory_mapping_digest") or "")
    if not expected_digest:
        raise UnsafeStateError(
            "the retained Coinalyze inventory plan fact has no mapping identity",
            context={"identity": plan.identity},
        )
    if len(native_to_provider) != expected_count:
        raise UnsafeStateError(
            "retained Coinalyze inventory mapping count changed",
            context={
                "identity": plan.identity,
                "expected": expected_count,
                "actual": len(native_to_provider),
            },
        )
    actual_digest = sha256_bytes(
        compact_json(
            [
                {"native_symbol": native, "provider_symbol": provider}
                for native, provider in sorted(native_to_provider.items())
            ]
        )
    )
    if actual_digest != expected_digest:
        raise UnsafeStateError(
            "retained Coinalyze inventory mapping set changed",
            context={"identity": plan.identity},
        )
    rebuilt_accepted = sorted(
        (native, native_to_provider.get(native, "")) for native, _p in accepted_pairs
    )
    if rebuilt_accepted != accepted_pairs:
        raise UnsafeStateError(
            "retained Coinalyze inventory no longer proves every accepted mapping",
            context={"identity": plan.identity},
        )


def _validate_coinalyze_liquidation(
    plan: PlanObject, fact: CompletionFact, fd: int,
    *,
    roots: BoundRoots | None = None,
) -> None:
    params = dict(plan.payload.get("params") or {})
    revision = dict(fact.revision)
    status = int(revision.get("status") or 0)
    if fact.validation_state == OUTCOME_UNAVAILABLE:
        if status != 404:
            raise UnsafeStateError(
                "a provider-unavailable outcome does not carry its 404 status",
                context={"identity": plan.identity},
            )
        return
    if status != 200:
        raise UnsafeStateError(
            "a Coinalyze completion does not carry its accepted 200 status",
            context={"identity": plan.identity},
        )
    summary = validate_liquidation_stream(
        _iter_fd(fd),
        provider_symbol=str(plan.payload["provider_symbol"]),
        start=int(params["from"]),
        end=int(params["to"]),
    )
    expected = (
        OUTCOME_EMPTY_HISTORY if summary.points == 0 else OUTCOME_CHECKSUM_VERIFIED
    )
    if fact.validation_state != expected:
        raise UnsafeStateError(
            "a Coinalyze outcome disagrees with its content",
            context={
                "identity": plan.identity,
                "recorded": fact.validation_state,
                "actual": expected,
            },
        )
    if int(revision.get("points") or 0) != summary.points:
        raise UnsafeStateError(
            "a Coinalyze completion point count disagrees with its content",
            context={"identity": plan.identity},
        )


def _validate_binance_sidecar(
    plan: PlanObject,
    fact: CompletionFact,
    sidecar: Mapping[str, Any] | None,
    *,
    paths: AcquisitionPaths,
    roots: BoundRoots | None = None,
) -> int:
    if sidecar is None:
        raise UnsafeStateError(
            "a Binance completion has no durable sidecar fact",
            context={"identity": plan.identity},
        )
    if fact.sidecar_sha256 is None or fact.sidecar_path is None:
        raise UnsafeStateError(
            "a Binance completion is missing its sidecar",
            context={"identity": plan.identity},
        )
    if str(sidecar["sidecar_sha256"]) != fact.sidecar_sha256 or str(
        sidecar["sidecar_path"]
    ) != fact.sidecar_path:
        raise UnsafeStateError(
            "a Binance sidecar fact disagrees with its completion",
            context={"identity": plan.identity},
        )
    if str(sidecar["provider_checksum"]) != fact.content_sha256:
        raise UnsafeStateError(
            "a Binance provider checksum does not equal its raw digest",
            context={"identity": plan.identity},
        )
    expected = content_path_for(paths.content_root, fact.sidecar_sha256)
    if Path(fact.sidecar_path) != expected:
        raise UnsafeStateError(
            "a sidecar is not at its content address", context={"identity": plan.identity}
        )
    fd = open_regular_file(paths.content_root, expected, roots=roots)
    try:
        digest, size = sha256_fd(fd)
        if digest != fact.sidecar_sha256:
            raise UnsafeStateError(
                "a completed sidecar digest changed", context={"identity": plan.identity}
            )
        if size != int(sidecar["sidecar_bytes"]):
            raise UnsafeStateError(
                "a completed sidecar size changed", context={"identity": plan.identity}
            )
        os.lseek(fd, 0, os.SEEK_SET)
        body = read_fd(fd, limit=SIDECAR_CEILING_BYTES)
    finally:
        os.close(fd)
    basename = str(plan.payload["key"]).rsplit("/", 1)[-1]
    checksum = parse_sidecar(body, basename=basename)
    if checksum != fact.content_sha256:
        raise UnsafeStateError(
            "a parsed sidecar checksum does not equal the raw digest",
            context={"identity": plan.identity},
        )
    return size


def load_authority_bundle(
    paths: AcquisitionPaths, pins: AuthorityPins, filesystem: Filesystem,
    *,
    roots: BoundRoots | None = None,
    fault: FaultInjector | None = None,
) -> dict[str, Any]:
    helpers = authenticate_helpers(paths, pins, roots=roots)
    code = code_identity(paths, roots=roots)
    def _pin(path: Path, digest: str, size: int | None, label: str) -> bytes:
        return _pin_file(
            path, digest, size, label=label, root=accepted_root_for(paths, path)
        , roots=roots)

    report_payload = _pin(
        paths.report_path, pins.report_sha256, pins.report_bytes, "report 62"
    )
    report = _decode_json(report_payload, label="report 62")
    receipt_258 = _decode_json(
        _pin(
            paths.receipt_258_path,
            pins.receipt_258_sha256,
            pins.receipt_258_bytes,
            "receipt 258",
        ),
        label="receipt 258",
    )
    retained_credit = authenticate_retained_credit_receipt(receipt_258, pins)
    load_attestation(
        paths.attestation_path, pins, root=accepted_root_for(paths, paths.attestation_path),
        roots=roots,
    )
    listing = _decode_json(
        _pin(
            paths.listing_checkpoint_path,
            pins.listing_checkpoint_sha256,
            None,
            "listing checkpoint",
        ),
        label="listing checkpoint",
    )
    metadata = _decode_json(
        _pin(
            paths.contract_metadata_path,
            pins.contract_metadata_sha256,
            None,
            "official contract metadata",
        ),
        label="official contract metadata",
    )
    _pin(paths.lock_path, pins.lock_sha256, None, "version-4 lock")
    _pin(paths.amendment_ledger_path, pins.amendment_ledger_sha256, None, "amendment ledger")
    progress = _decode_json(
        _pin(paths.progress_path, pins.progress_sha256, None, "qualification progress"),
        label="qualification progress",
    )
    holdout = load_holdout(
        paths.holdout_path, pins, root=accepted_root_for(paths, paths.holdout_path),
        roots=roots,
    )
    device = filesystem.device_of(paths.store_root)
    if pins.device and device != pins.device:
        raise AuthorityError(
            "store is not on the attested device",
            context={"expected": pins.device, "actual": device},
        )
    capacity = evaluate_capacity(
        pins=pins, available_bytes=filesystem.available_bytes(paths.store_root)
    )
    if capacity["storage_preflight_state"] != "sufficient":
        raise CapacityBlocked("current capacity cannot host the unchanged stable requirement")
    cost_objects, cost_digest = resolve_cost_objects(
        report=report,
        listing_checkpoint=listing,
        listing_cache_dir=paths.listing_cache_dir,
        pins=pins,
        roots=roots,
    )
    mappings, supported, unmapped, lifecycles, cutoff, inventory_set = derive_coinalyze_mappings(
        report=report,
        contract_metadata=metadata,
        pins=pins,
        cache_root=paths.coinalyze_cache_dir,
        roots=roots,
    )
    family_totals: dict[str, int] = {}
    hasher = hashlib.sha256()
    object_count = 0
    for obj in iter_plan_objects(
        paths,
        pins,
        report=report,
        listing=listing,
        mappings=mappings,
        unmapped=unmapped,
        lifecycles=lifecycles,
        cost_objects=cost_objects,
        inventory_set=inventory_set,
        retained_credit=retained_credit,
        progress=progress,
        roots=roots,
        fault=fault,
    ):
        hasher.update(plan_entry_bytes(obj))
        object_count += 1
        if obj.kind == KIND_BINANCE:
            family = str(obj.payload.get("family") or "")
            family_totals[family] = family_totals.get(family, 0) + 1
    identity = hasher.hexdigest()
    summary = PlanSummary(
        identity=identity,
        family_totals=dict(sorted(family_totals.items())),
        binance_bytes=pins.combined_bytes,
        cost_digest=cost_digest,
        coinalyze_supported=supported,
        coinalyze_unsupported=unmapped,
        coinalyze_mappings=tuple(mappings),
        cutoff=cutoff,
        holdout_id=str(holdout.get("boundary_id") or pins.holdout_boundary_id),
        helper_identities=helpers,
        code_identity=code,
        object_count=object_count,
        lifecycles=lifecycles,
        retained_credit=retained_credit,
    )
    return {
        "summary": summary,
        "report": report,
        "listing": listing,
        "progress": progress,
        "cost_objects": cost_objects,
        "inventory_set": inventory_set,
        "capacity": capacity,
        "device": device,
        "code": code,
        "retained_credit": retained_credit,
    }


def plan_receipt_document(
    summary: PlanSummary, paths: AcquisitionPaths, pins: AuthorityPins, *, device: str
) -> dict[str, Any]:
    return {
        "schema_version": PLAN_SCHEMA,
        "ticket": TICKET_ID,
        "policy_identity": POLICY_IDENTITY,
        "plan_identity": summary.identity,
        "authority": {
            "report_62_sha256": pins.report_sha256,
            "manifest_compressed_sha256": pins.manifest_compressed_sha256,
            "manifest_uncompressed_sha256": pins.manifest_uncompressed_sha256,
            "cost_manifest_sha256": pins.cost_manifest_sha256,
            "receipt_258_sha256": pins.receipt_258_sha256,
            "attestation_282_sha256": pins.attestation_282_sha256,
            "listing_checkpoint_sha256": pins.listing_checkpoint_sha256,
            "contract_metadata_sha256": pins.contract_metadata_sha256,
            "lock_sha256": pins.lock_sha256,
            "amendment_ledger_sha256": pins.amendment_ledger_sha256,
            "progress_sha256": pins.progress_sha256,
            "holdout_boundary_id": pins.holdout_boundary_id,
        },
        "code_identity": dict(summary.code_identity),
        "helper_identities": dict(summary.helper_identities),
        "counts": {
            "binance_objects": pins.combined_objects,
            "main_selected_objects": pins.main_selected_objects,
            "cost_objects": pins.cost_objects,
            "coinalyze_logical_receipts": pins.coinalyze_logical_receipts,
            "coinalyze_supported": pins.coinalyze_supported,
            "coinalyze_unsupported": pins.coinalyze_unsupported,
            "retained_credit_objects": pins.retained_credit_objects,
            "plan_objects": summary.object_count,
        },
        "bytes": {
            "binance_listed_bytes": pins.combined_bytes,
            "new_binance_raw_bytes": pins.new_binance_raw_bytes,
            "new_coinalyze_raw_bytes": pins.new_coinalyze_raw_bytes,
            "retained_credit_bytes": pins.retained_credit_bytes,
        },
        "family_totals": summary.family_totals,
        "coinalyze": {
            "request_path": COINALYZE_LIQUIDATION_PATH,
            "interval": COINALYZE_INTERVAL_DAILY,
            "symbols_per_request": COINALYZE_MAX_SYMBOLS_PER_REQUEST,
            "convert_to_usd": False,
            "rate_per_minute": COINALYZE_RATE_PER_MINUTE,
            "cutoff": summary.cutoff,
            "supported_count": len(summary.coinalyze_supported),
            "unsupported_count": len(summary.coinalyze_unsupported),
            "anchors_are_not_the_universe": True,
            "current_inventory_is_not_authority": True,
        },
        "holdout_boundary_id": summary.holdout_id,
        "storage": {
            "destination": pins.destination,
            "device": device,
            "store_root": str(paths.store_root),
        },
        "prohibitions": list(PROHIBITIONS),
        "retained_credit": _compact_retained_credit(summary.retained_credit),
    }


def bind_session(
    paths: AcquisitionPaths,
    pins: AuthorityPins,
    filesystem: Filesystem,
    *,
    install: bool,
    fault: FaultInjector | None = None,
    roots: BoundRoots | None = None,
) -> tuple[PlanSummary, AcquisitionState, dict[str, Any]]:
    roots = BoundRoots.open(paths)
    try:
        bound_fs: Filesystem = filesystem
        if isinstance(filesystem, RealFilesystem):
            bound_fs = RealFilesystem(store_fd=roots.store_fd)
        bundle = load_authority_bundle(paths, pins, bound_fs, roots=roots, fault=fault)
        summary: PlanSummary = bundle["summary"]
        device = bundle["device"]
        document = plan_receipt_document(summary, paths, pins, device=device)
        receipt = write_named_receipt(
            document, paths.plan_receipt_dir, device, bound_fs, roots=roots
        )
        state = AcquisitionState(
            paths.state_path,
            paths.lockfile_path,
            roots=roots,
            plan_receipt_dir=paths.plan_receipt_dir,
            run_receipt_dir=paths.run_receipt_dir,
        )
        try:
            state.open()
        except Exception:
            state.close()
            raise
        try:
            objects = iter_plan_objects(
                paths,
                pins,
                report=bundle["report"],
                listing=bundle["listing"],
                mappings=summary.coinalyze_mappings,
                unmapped=summary.coinalyze_unsupported,
                lifecycles=summary.lifecycles,
                cost_objects=bundle["cost_objects"],
                inventory_set=bundle["inventory_set"],
                retained_credit=bundle["retained_credit"],
                progress=bundle["progress"],
                roots=roots,
                fault=fault,
            )
            if not install and not state.has_plan():
                raise UnsafeStateError("verify has no installed plan")
            state.install_or_compare(
                objects,
                plan_identity=summary.identity,
                receipt_sha256=receipt["sha256"],
                receipt_path=str(receipt["path"]),
                pins=pins,
                code=bundle["code"],
                device=device,
                fault=fault,
            )
            state.filesystem = bound_fs
            state.publication_device = device
            state.authenticate_singletons()
            state.authenticate_prefix()
        except Exception:
            state.close()
            raise
        bundle["receipt"] = receipt
        bundle["device"] = device
        bundle["roots"] = roots
        bundle["filesystem"] = bound_fs
        return summary, state, bundle
    except Exception:
        roots.close()
        raise


# --------------------------------------------------------------------------------------
# Bounded run instrumentation. Exact counters are integers under one lock; only a small
# deterministic redacted sample is retained, never a manifest-sized list.
# --------------------------------------------------------------------------------------


@dataclass
class RunCounters:
    lock: threading.Lock = field(default_factory=threading.Lock)
    network_calls: int = 0
    errors: int = 0
    network_sample: list[str] = field(default_factory=list)
    error_sample: list[str] = field(default_factory=list)

    def note_call(self, redacted_url: str) -> None:
        with self.lock:
            self.network_calls += 1
            if len(self.network_sample) < NETWORK_SAMPLE_CEILING:
                self.network_sample.append(redacted_url)
            BOUND_TELEMETRY.note("max_sample_len", len(self.network_sample))

    def note_error(self, message: str) -> None:
        with self.lock:
            self.errors += 1
            if len(self.error_sample) < ERROR_SAMPLE_CEILING:
                self.error_sample.append(message)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "network_calls": self.network_calls,
                "errors": self.errors,
                "network_sample": list(self.network_sample),
                "error_sample": list(self.error_sample),
            }


class FatalSlot:
    """The first authority or unsafe-state failure, preserved with its original class."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._error: BaseException | None = None

    def offer(self, error: BaseException) -> None:
        with self._lock:
            if self._error is None:
                self._error = error

    @property
    def error(self) -> BaseException | None:
        return self._error


class CapacityGuard:
    """The exact prospective equation, revalidated at every transfer boundary."""

    def __init__(
        self,
        *,
        pins: AuthorityPins,
        paths: AcquisitionPaths,
        filesystem: Filesystem,
        coordinator: Coordinator | None = None,
    ) -> None:
        self._pins = pins
        self._paths = paths
        self._filesystem = filesystem
        self._coordinator = coordinator
        self.blocked = False

    def evaluate(self, next_transfer_bytes: int = 0) -> dict[str, Any]:
        return evaluate_capacity(
            pins=self._pins,
            available_bytes=self._filesystem.available_bytes(self._paths.store_root),
            next_transfer_bytes=int(next_transfer_bytes),
        )

    def require(self, next_transfer_bytes: int, *, boundary: str) -> dict[str, Any]:
        facts = self.evaluate(next_transfer_bytes)
        if facts["storage_preflight_state"] != "sufficient":
            self.blocked = True
            if self._coordinator is not None:
                self._coordinator.call("note_run_capacity_blocked")
            raise CapacityBlocked(
                "stop before transfer: capacity guard failed",
                context={"boundary": boundary, "next_transfer_bytes": next_transfer_bytes},
            )
        return facts


@dataclass
class _CoordinatorRequest:
    name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    event: threading.Event
    result: Any = None
    error: BaseException | None = None


class Coordinator:
    """The single owner of every database write and terminal transition.

    Workers never touch SQLite. They stream, validate, and return bounded results through
    this channel; one thread applies them in order, so there is no concurrent writer, no
    racy shared element, and no partially applied transition.
    """

    def __init__(self, state: AcquisitionState) -> None:
        self._state = state
        self._queue: queue.Queue[_CoordinatorRequest | None] = queue.Queue(
            maxsize=QUEUE_CEILING
        )
        self._thread: threading.Thread | None = None
        self._closed = threading.Event()

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._loop, name="gate2-coordinator", daemon=True
        )
        self._thread.start()

    def _loop(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            try:
                item.result = getattr(self._state, item.name)(*item.args, **item.kwargs)
            except BaseException as exc:  # noqa: BLE001 - relayed to the caller verbatim
                item.error = exc
            finally:
                item.event.set()

    def call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        if self._closed.is_set() or self._thread is None:
            return getattr(self._state, name)(*args, **kwargs)
        request = _CoordinatorRequest(name, args, kwargs, threading.Event())
        self._queue.put(request)
        BOUND_TELEMETRY.note("max_queue_depth", self._queue.qsize())
        if not request.event.wait(timeout=300.0):
            raise UnsafeStateError("the state coordinator did not answer")
        if request.error is not None:
            raise request.error
        return request.result

    def stop(self) -> None:
        if self._thread is None:
            return
        self._closed.set()
        self._queue.put(None)
        self._thread.join(timeout=30.0)
        if self._thread.is_alive():  # pragma: no cover - defensive
            raise UnsafeStateError("the state coordinator did not settle")
        self._thread = None


def _diagnostic(exc: BaseException, secret: str | None) -> str:
    text = redact_text(f"{type(exc).__name__}: {exc}", secret)
    raw = text.encode("utf-8")
    if len(raw) > MAX_DIAGNOSTIC_BYTES:
        raw = raw[:MAX_DIAGNOSTIC_BYTES]
        text = raw.decode("utf-8", errors="ignore")
    return text


def request_with_retry(
    transport: StreamTransport,
    url: str,
    *,
    headers: Mapping[str, str] | None,
    secret: str | None,
    sleeper: Callable[[float], None],
    coordinator: Coordinator,
    provider: str,
    identity: str,
    counters: RunCounters,
    tmp_root: Path,
    device: str,
    filesystem: Filesystem,
    max_bytes: int,
    allow_statuses: set[int] | None = None,
    limiter: RateLimiter | None = None,
    expected_digest: str | None = None,
    expected_size: int | None = None,
    observer: Callable[[bytes], None] | None = None,
    validator: Callable[[Any, StreamResponse], None] | None = None,
    roots: BoundRoots | None = None,
) -> tuple[StreamResponse, Any]:
    """One attempt is headers plus complete streamed-body consumption and validation."""

    last_error = "retry budget exhausted"
    allowed = allow_statuses or {200}

    def _record(
        classification: str,
        *,
        started_at: str,
        status_code: int | None,
        fact: Mapping[str, Any],
    ) -> None:
        coordinator.call(
            "record_attempt",
            provider,
            identity,
            classification,
            status_code=status_code,
            fact=dict(fact),
            started_at=started_at,
            ended_at=datetime.now(UTC).isoformat(),
        )

    for attempt in range(MAX_TRANSIENT_ATTEMPTS):
        if url_has_secret(url, secret):
            raise AcquisitionError("secret leaked into a URL")
        if limiter is not None:
            limiter.acquire()
        started_at = datetime.now(UTC).isoformat()
        response: StreamResponse | None = None
        try:
            counters.note_call(redact_text(url, secret))
            response = transport.stream_get(url, headers=headers, timeout=60.0)
        except FaultInjected as exc:
            _record(
                RETRY_TRANSIENT,
                started_at=started_at,
                status_code=None,
                fact={
                    "url": redact_text(url, secret),
                    "attempt": attempt + 1,
                    "error": _diagnostic(exc, secret),
                },
            )
            raise
        except AcquisitionError as exc:
            _record(
                RETRY_TRANSPORT,
                started_at=started_at,
                status_code=None,
                fact={
                    "url": redact_text(url, secret),
                    "attempt": attempt + 1,
                    "error": _diagnostic(exc, secret),
                    "kind": "transport",
                },
            )
            sleeper(float(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]))
            last_error = RETRY_TRANSPORT
            continue
        except Exception as exc:
            _record(
                RETRY_TRANSPORT,
                started_at=started_at,
                status_code=None,
                fact={
                    "url": redact_text(url, secret),
                    "attempt": attempt + 1,
                    "error": _diagnostic(exc, secret),
                    "kind": "transport",
                },
            )
            sleeper(float(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]))
            last_error = RETRY_TRANSPORT
            continue
        classification = classify_status(response.status_code)
        if response.status_code not in allowed:
            headers_map = dict(response.headers)
            status = response.status_code
            try:
                response.close_response()
            except Exception as exc:
                _record(
                    RETRY_TRANSPORT,
                    started_at=started_at,
                    status_code=None,
                    fact={
                        "url": redact_text(url, secret),
                        "status": status,
                        "error": _diagnostic(exc, secret),
                        "kind": "close",
                    },
                )
                sleeper(float(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]))
                last_error = RETRY_TRANSPORT
                continue
            _record(
                classification,
                started_at=started_at,
                status_code=status,
                fact={
                    "url": redact_text(url, secret),
                    "status": status,
                    "attempt": attempt + 1,
                },
            )
            if classification == RETRY_TERMINAL:
                raise AcquisitionError(
                    "request failed terminally", context={"status": status}
                )
            if classification == RETRY_RATE_LIMIT:
                sleeper(bounded_retry_after(headers_map))
            else:
                sleeper(float(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]))
            last_error = classification
            continue
        private = None
        recorded = False
        try:
            try:
                private = stream_to_private(
                    response.iter_bytes,
                    tmp_root=tmp_root,
                    device=device,
                    filesystem=filesystem,
                    max_bytes=max_bytes,
                    expected_digest=expected_digest,
                    expected_size=expected_size,
                    observer=observer,
                 roots=roots,)
                if validator is not None:
                    validator(private, response)
            finally:
                try:
                    response.close_response()
                except Exception as exc:
                    if private is not None:
                        discard_private(private, roots=roots)
                    if not recorded:
                        _record(
                            RETRY_TRANSPORT,
                            started_at=started_at,
                            status_code=None,
                            fact={
                                "url": redact_text(url, secret),
                                "error": _diagnostic(exc, secret),
                                "kind": "close",
                            },
                        )
                        recorded = True
                    raise
        except FaultInjected as exc:
            if private is not None:
                discard_private(private, roots=roots)
            if not recorded:
                _record(
                    RETRY_TRANSPORT,
                    started_at=started_at,
                    status_code=None,
                    fact={
                        "url": redact_text(url, secret),
                        "error": _diagnostic(exc, secret),
                        "kind": "interrupt",
                    },
                )
            raise
        except AcquisitionError as exc:
            if private is not None:
                discard_private(private, roots=roots)
            if not recorded:
                _record(
                    RETRY_TERMINAL,
                    started_at=started_at,
                    status_code=response.status_code,
                    fact={
                        "url": redact_text(url, secret),
                        "status": response.status_code,
                        "error": _diagnostic(exc, secret),
                        "kind": "validation",
                    },
                )
            raise
        except Exception as exc:
            if private is not None:
                discard_private(private, roots=roots)
            if not recorded:
                _record(
                    RETRY_TRANSPORT,
                    started_at=started_at,
                    status_code=None,
                    fact={
                        "url": redact_text(url, secret),
                        "error": _diagnostic(exc, secret),
                        "kind": "transport",
                    },
                )
            sleeper(float(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]))
            last_error = RETRY_TRANSPORT
            continue
        _record(
            RETRY_OK,
            started_at=started_at,
            status_code=response.status_code,
            fact={
                "url": redact_text(url, secret),
                "status": response.status_code,
                "bytes": private.size,
            },
        )
        return response, private
    raise AcquisitionError(last_error)


def verify_retained_object(
    key: str,
    entry: Mapping[str, Any],
    *,
    sample_dir: Path,
    sidecar_dir: Path,
    roots: BoundRoots | None = None,
) -> int | None:
    """Re-prove one retained object through bound descriptors, never pathname APIs."""

    if str(entry.get("status") or "") != "complete":
        return None
    digest = str(entry.get("sha256") or "")
    provider = str(entry.get("provider_checksum") or "")
    if HEX64.fullmatch(digest) is None or provider != digest:
        return None
    source = sample_dir / digest
    try:
        fd = open_regular_file(sample_dir, source, roots=roots)
    except UnsafeStateError:
        return None
    try:
        actual, size = sha256_fd(fd)
        if actual != digest:
            return None
    finally:
        os.close(fd)
    sidecar_src = Path(str(entry.get("provider_checksum_path") or ""))
    try:
        sidecar_body = read_authority_file(
            sidecar_src, label="retained sidecar", root=sidecar_dir, roots=roots
        )
    except (AuthorityError, UnsafeStateError):
        return None
    expected_sidecar = str(entry.get("provider_checksum_sha256") or "")
    if expected_sidecar and sha256_bytes(sidecar_body) != expected_sidecar:
        return None
    try:
        checksum = parse_sidecar(sidecar_body, basename=key.rsplit("/", 1)[-1])
    except AcquisitionError:
        return None
    if checksum != digest:
        return None
    return size


def retained_credit_decomposition(
    retained_objects: Mapping[str, Mapping[str, Any]],
    *,
    requirement_keys: Sequence[str],
    sample_dir: Path,
    sidecar_dir: Path,
    roots: BoundRoots | None = None,
) -> dict[str, Any]:
    """The three ADR-0022 credit quantities, proved through bound descriptors."""

    digests: set[str] = set()
    keys: list[str] = []
    byte_total = 0
    unverified = 0
    wanted = set(requirement_keys)
    for key, entry in sorted(retained_objects.items()):
        if key not in wanted:
            continue
        size = verify_retained_object(
            key,
            entry,
            sample_dir=sample_dir,
            sidecar_dir=sidecar_dir,
            roots=roots,
        )
        if size is None:
            unverified += 1
            continue
        keys.append(key)
        digest = str(entry.get("sha256") or "")
        if digest in digests:
            continue
        digests.add(digest)
        byte_total += size
    return {
        "valid_requirement_keys": len(keys),
        "keys": sorted(keys),
        "unique_objects": len(digests),
        "unique_bytes": byte_total,
        "unverified_objects": unverified,
    }


def adopt_retained(
    paths: AcquisitionPaths,
    pins: AuthorityPins,
    coordinator: Coordinator,
    state: AcquisitionState,
    *,
    progress: Mapping[str, Any],
    retained_credit: RetainedCredit,
    filesystem: Filesystem,
    device: str,
    fault: FaultInjector,
    roots: BoundRoots | None = None,
) -> dict[str, Any]:
    """Adopt the accepted retained credit exactly, validated, and storage-neutral.

    The already-authenticated raw and sidecar bytes are re-referenced by a no-follow,
    no-replace hard link on the same device, so the accepted new-raw equation is never
    charged again for bytes it already credited as retained. Authority is the receipt
    258 key set, never the intersection of qualification progress and the plan.
    """
    roots = _require_bound(roots, operation="adopt_retained")

    objects = dict(progress.get("objects") or {})
    requirement_keys = list(retained_credit.keys)
    decomposition = retained_credit_decomposition(
        objects,
        requirement_keys=requirement_keys,
        sample_dir=paths.sample_dir,
        sidecar_dir=paths.listing_cache_dir,
        roots=roots,
    )
    if int(decomposition["unverified_objects"]) != retained_credit.unverified_objects:
        raise AuthorityError("a retained requirement object cannot be re-proved")
    if set(decomposition["keys"]) != retained_credit.key_set:
        raise AuthorityError(
            "retained credit key set changed",
            context={
                "expected": retained_credit.valid_requirement_keys,
                "actual": len(decomposition["keys"]),
            },
        )
    if int(decomposition["valid_requirement_keys"]) != retained_credit.valid_requirement_keys:
        raise AuthorityError(
            "retained credit key count changed",
            context={
                "expected": retained_credit.valid_requirement_keys,
                "actual": decomposition["valid_requirement_keys"],
            },
        )
    if int(decomposition["unique_objects"]) != retained_credit.objects:
        raise AuthorityError(
            "retained credit object count changed",
            context={
                "expected": retained_credit.objects,
                "actual": decomposition["unique_objects"],
            },
        )
    if int(decomposition["unique_objects"]) != pins.retained_credit_objects:
        raise AuthorityError(
            "retained credit object count changed",
            context={
                "expected": pins.retained_credit_objects,
                "actual": decomposition["unique_objects"],
            },
        )
    if int(decomposition["unique_bytes"]) != retained_credit.unique_bytes:
        raise AuthorityError(
            "retained credit bytes changed",
            context={
                "expected": retained_credit.unique_bytes,
                "actual": decomposition["unique_bytes"],
            },
        )
    if int(decomposition["unique_bytes"]) != pins.retained_credit_bytes:
        raise AuthorityError(
            "retained credit bytes changed",
            context={
                "expected": pins.retained_credit_bytes,
                "actual": decomposition["unique_bytes"],
            },
        )
    keys = list(decomposition["keys"])
    cost_retained = sum(1 for key in keys if _family_of(key) in COST_FAMILIES)
    selected_retained = len(keys) - cost_retained
    if cost_retained != retained_credit.cost_retained_keys:
        raise AuthorityError(
            "retained credit cost key count changed",
            context={
                "expected": retained_credit.cost_retained_keys,
                "actual": cost_retained,
            },
        )
    if selected_retained != retained_credit.selected_retained_keys:
        raise AuthorityError(
            "retained credit selected key count changed",
            context={
                "expected": retained_credit.selected_retained_keys,
                "actual": selected_retained,
            },
        )
    if pins.receipt_258_sha256 == PRODUCTION_PINS.receipt_258_sha256 and (
        cost_retained != PRODUCTION_RETAINED_COST_KEYS
        or selected_retained != PRODUCTION_RETAINED_SELECTED_KEYS
    ):
        raise AuthorityError(
            "production retained credit decomposition changed",
            context={"selected": selected_retained, "cost": cost_retained},
        )
    adopted = 0
    reproved = 0
    for key in keys:
        plan_payload = coordinator.call("plan_payload", PROVIDER_BINANCE, key)
        if plan_payload is None:
            raise AuthorityError("a retained key is not in the plan", context={"key": key})
        plan = PlanObject(PROVIDER_BINANCE, key, KIND_BINANCE, plan_payload)
        existing = coordinator.call("completion_fact", PROVIDER_BINANCE, key)
        if existing is not None:
            # A completed retained row is first fully re-proved and only then skipped;
            # a corrupt completed retained row is never silently accepted.
            sidecar_fact = coordinator.call("sidecar_fact", PROVIDER_BINANCE, key)
            validate_provider_completion(
                plan, existing, sidecar_fact, paths=paths, pins=pins, roots=roots
            )
            reproved += 1
            continue
        entry = objects[key]
        try:
            size = verify_retained_object(
                key,
                entry,
                sample_dir=paths.sample_dir,
                sidecar_dir=paths.listing_cache_dir,
                roots=roots,
            )
        except Exception as exc:
            raise AuthorityError(
                "retained object failed re-proof", context={"key": key}
            ) from exc
        if size is None:
            raise AuthorityError("retained object failed re-proof", context={"key": key})
        digest = _hex_digest(entry["sha256"], label="retained digest")
        source = paths.sample_dir / digest
        sidecar_src = Path(str(entry["provider_checksum_path"]))
        sidecar_body = read_authority_file(
            sidecar_src, label="retained sidecar", root=paths.listing_cache_dir
        , roots=roots)
        checksum = parse_sidecar(sidecar_body, basename=key.rsplit("/", 1)[-1])
        if checksum != digest:
            raise AuthorityError(
                "a retained sidecar does not name its raw digest", context={"key": key}
            )
        validate_zip(source, root=paths.sample_dir, roots=roots)
        source_fd = open_regular_file(paths.sample_dir, source, roots=roots)
        try:
            source_stat = os.fstat(source_fd)
        finally:
            os.close(source_fd)
        raw_path, _reused = adopt_same_device_file(
            source,
            source_root=paths.sample_dir,
            content_root=paths.content_root,
            digest=digest,
            device=device,
            filesystem=filesystem,
         roots=roots,)
        dest_fd = open_regular_file(paths.content_root, raw_path, roots=roots)
        try:
            content_stat = os.fstat(dest_fd)
        finally:
            os.close(dest_fd)
        sidecar_digest = _hex_digest(
            entry.get("provider_checksum_sha256") or sha256_bytes(sidecar_body),
            label="retained sidecar digest",
        )
        sidecar_path, _sidecar_reused = adopt_same_device_file(
            sidecar_src,
            source_root=paths.listing_cache_dir,
            content_root=paths.content_root,
            digest=sidecar_digest,
            device=device,
            filesystem=filesystem,
         roots=roots,)
        coordinator.call(
            "record_sidecar",
            PROVIDER_BINANCE,
            key,
            sidecar_digest,
            sidecar_path,
            digest,
            sidecar_bytes=len(sidecar_body),
        )
        coordinator.call(
            "complete",
            PROVIDER_BINANCE,
            key,
            content_sha256=digest,
            content_path=raw_path,
            sidecar_sha256=sidecar_digest,
            sidecar_path=sidecar_path,
            listed_bytes=int(size),
            retrieved_at=str(entry.get("retrieval_time") or datetime.now(UTC).isoformat()),
            revision={
                "retained": True,
                "source_inode": int(source_stat.st_ino),
                "content_inode": int(content_stat.st_ino),
                "source_device": int(source_stat.st_dev),
            },
            validation_state=OUTCOME_RETAINED,
            fault=fault,
        )
        adopted += 1
    return {
        "adopted_keys": adopted,
        "reproved_keys": reproved,
        "unique_objects": int(decomposition["unique_objects"]),
        "unique_bytes": int(decomposition["unique_bytes"]),
        "cost_keys": cost_retained,
    }


def acquire_binance_object(
    obj: PlanObject,
    *,
    paths: AcquisitionPaths,
    coordinator: Coordinator,
    transport: StreamTransport,
    filesystem: Filesystem,
    device: str,
    pins: AuthorityPins,
    capacity: CapacityGuard,
    fault: FaultInjector,
    counters: RunCounters,
    sleeper: Callable[[float], None],
    roots: BoundRoots | None = None,
) -> str:
    roots = _require_bound(roots, operation="acquire_binance_object")
    payload = dict(obj.payload)
    identity = obj.identity
    listed = int(payload["listed_bytes"])
    if listed <= 0:
        raise UnsafeStateError("a plan row has no positive listed size")
    basename = str(payload["key"]).rsplit("/", 1)[-1]
    sidecar = coordinator.call("sidecar_fact", obj.provider, identity)
    if sidecar is None:
        # The prospective equation is enforced before the sidecar transfer, and then
        # recomputed below after the sidecar has consumed space on the same device.
        capacity.require(SIDECAR_CEILING_BYTES, boundary="binance_sidecar")
        fault.check("before_sidecar_publication", identity)
        parsed: dict[str, str] = {}

        def _validate_sidecar(private: Any, _response: StreamResponse) -> None:
            fd = open_regular_file(paths.tmp_root, private.path, roots=roots)
            try:
                body = read_fd(fd, limit=SIDECAR_CEILING_BYTES)
            finally:
                os.close(fd)
            parsed["checksum"] = parse_sidecar(body, basename=basename)

        _response, private = request_with_retry(
            transport,
            str(payload["sidecar_url"]),
            headers=None,
            secret=None,
            sleeper=sleeper,
            coordinator=coordinator,
            provider=obj.provider,
            identity=identity,
            counters=counters,
            tmp_root=paths.tmp_root,
            device=device,
            filesystem=filesystem,
            max_bytes=SIDECAR_CEILING_BYTES,
            validator=_validate_sidecar,
         roots=roots,)
        checksum = parsed["checksum"]
        sidecar_path, _reused = publish_private_file(
            private, content_root=paths.content_root, device=device, filesystem=filesystem
        , roots=roots)
        fault.check("after_sidecar_publication", identity)
        coordinator.call(
            "record_sidecar",
            obj.provider,
            identity,
            private.digest,
            sidecar_path,
            checksum,
            sidecar_bytes=private.size,
        )
        sidecar = {
            "sidecar_sha256": private.digest,
            "sidecar_path": str(sidecar_path),
            "provider_checksum": checksum,
            "sidecar_bytes": private.size,
        }
    else:
        sidecar_path = Path(sidecar["sidecar_path"])
        fd = open_regular_file(paths.content_root, sidecar_path, roots=roots)
        try:
            digest, size = sha256_fd(fd)
            if digest != sidecar["sidecar_sha256"] or size != int(sidecar["sidecar_bytes"]):
                raise UnsafeStateError("recorded sidecar bytes changed")
            os.lseek(fd, 0, os.SEEK_SET)
            body = read_fd(fd, limit=SIDECAR_CEILING_BYTES)
        finally:
            os.close(fd)
        if parse_sidecar(body, basename=basename) != sidecar["provider_checksum"]:
            raise UnsafeStateError("recorded sidecar checksum changed")
    expected = _hex_digest(sidecar["provider_checksum"], label="provider checksum")
    dest = content_path_for(paths.content_root, expected)
    shard = open_dir_chain(paths.content_root, (expected[:2],), create=True, roots=roots)
    try:
        adopted_size = probe_published_content(shard, expected, expected)
    finally:
        os.close(shard)
    if adopted_size is not None and adopted_size != listed:
        raise UnsafeStateError("published raw content does not match its listed size")
    if adopted_size is not None:
        validate_zip(dest, root=paths.content_root, roots=roots)
        revision = {"adopted": True}
        raw_path = dest
    else:
        capacity.require(listed, boundary="binance_raw")
        fault.check("before_raw_publication", identity)
        def _validate_zip(private: Any, _response: StreamResponse) -> None:
            fd = open_regular_file(paths.tmp_root, private.path, roots=roots)
            try:
                validate_zip_fd(fd)
            finally:
                os.close(fd)

        response, private = request_with_retry(
            transport,
            str(payload["url"]),
            headers=None,
            secret=None,
            sleeper=sleeper,
            coordinator=coordinator,
            provider=obj.provider,
            identity=identity,
            counters=counters,
            tmp_root=paths.tmp_root,
            device=device,
            filesystem=filesystem,
            max_bytes=listed,
            expected_digest=expected,
            expected_size=listed,
            validator=_validate_zip,
         roots=roots,)
        headers = dict(response.headers)
        raw_path, _reused = publish_private_file(
            private, content_root=paths.content_root, device=device, filesystem=filesystem
        , roots=roots)
        fault.check("after_raw_publication", identity)
        revision = {
            "etag": headers.get("ETag") or headers.get("etag") or payload.get("etag") or "",
            "last_modified": headers.get("Last-Modified") or headers.get("last-modified") or "",
        }
    coordinator.call(
        "complete",
        obj.provider,
        identity,
        content_sha256=expected,
        content_path=raw_path,
        sidecar_sha256=sidecar["sidecar_sha256"],
        sidecar_path=Path(sidecar["sidecar_path"]),
        listed_bytes=listed,
        retrieved_at=datetime.now(UTC).isoformat(),
        revision=revision,
        validation_state=OUTCOME_CHECKSUM_VERIFIED,
        fault=fault,
    )
    return OUTCOME_CHECKSUM_VERIFIED


def acquire_coinalyze_inventory(
    obj: PlanObject,
    *,
    paths: AcquisitionPaths,
    coordinator: Coordinator,
    filesystem: Filesystem,
    device: str,
    fault: FaultInjector,
    report: Mapping[str, Any],
    roots: BoundRoots | None = None,
) -> str:
    """Adopt the one accepted retained inventory; it is never a charged network body."""
    roots = _require_bound(roots, operation="acquire_coinalyze_inventory")

    provenance = [
        item
        for item in list(dict(report.get("coinalyze") or {}).get("provenance") or ())
        if isinstance(item, dict) and str(item.get("path") or "") == COINALYZE_MARKETS_PATH
    ]
    if not provenance:
        raise AuthorityError("retained Coinalyze inventory provenance is missing")
    item = provenance[0]
    content_path = Path(str(item["content_path"]))
    body = read_authority_file(
        content_path, label="retained Coinalyze inventory", root=paths.coinalyze_cache_dir
    , roots=roots)
    digest = sha256_bytes(body)
    if digest != str(item.get("sha256") or ""):
        raise AuthorityError("retained Coinalyze inventory digest changed")
    published, dest, _reused = publish_bytes(
        body,
        content_root=paths.content_root,
        tmp_root=paths.tmp_root,
        device=device,
        filesystem=filesystem,
        expected_digest=digest,
     roots=roots,)
    coordinator.call(
        "complete",
        obj.provider,
        obj.identity,
        content_sha256=published,
        content_path=dest,
        sidecar_sha256=None,
        sidecar_path=None,
        listed_bytes=len(body),
        retrieved_at=str(item.get("retrieved_at") or datetime.now(UTC).isoformat()),
        revision={"retained": True},
        validation_state=OUTCOME_RETAINED_INVENTORY,
        fault=fault,
    )
    return OUTCOME_RETAINED_INVENTORY


def acquire_coinalyze_liquidation(
    obj: PlanObject,
    *,
    paths: AcquisitionPaths,
    coordinator: Coordinator,
    transport: StreamTransport,
    filesystem: Filesystem,
    device: str,
    pins: AuthorityPins,
    secret: str | None,
    limiter: RateLimiter,
    capacity: CapacityGuard,
    fault: FaultInjector,
    counters: RunCounters,
    sleeper: Callable[[float], None],
    roots: BoundRoots | None = None,
) -> str:
    """One crash-recoverable budget, publication, and completion transition.

    The response is validated entirely in private; the accepted bytes are then charged
    exactly once against the singleton ledger, published no-replace, and completed. Any
    fault between those boundaries leaves a reconcilable reservation, never a silently
    consumed allocation and never an unvalidated body in the content store.
    """
    roots = _require_bound(roots, operation="acquire_coinalyze_liquidation")

    if not secret:
        raise AuthorityError("COINALYZE_API_KEY is required for Coinalyze acquisition")
    payload = dict(obj.payload)
    params = dict(payload["params"])
    if "," in str(params.get("symbols") or ""):
        raise AcquisitionError("Coinalyze request is not one-symbol")
    provider_symbol = str(payload["provider_symbol"])
    query = str(payload["query"])
    if f"{COINALYZE_LIQUIDATION_PATH}?{query}" != obj.identity:
        raise UnsafeStateError(
            "the planned request query does not equal its plan identity",
            context={"identity": obj.identity},
        )
    # The singleton ledger, its equation, and a positive remaining allocation are proved
    # before any network work; a missing or altered ledger is never discovered after a
    # request has already been made.
    remaining = int(
        coordinator.call("coinalyze_remaining", pins.new_coinalyze_raw_bytes)
    )
    if remaining <= 0:
        raise BudgetExhausted(
            "the accepted Coinalyze allocation is exhausted",
            context={"ceiling": pins.new_coinalyze_raw_bytes},
        )
    capacity.require(remaining, boundary="coinalyze_response")
    url = f"{payload['url']}?{query}"
    headers = {"api_key": secret}
    scanner = SecretScanner(secret)
    parsed: dict[str, Any] = {}

    def _validate_liquidation(private: Any, response: StreamResponse) -> None:
        scanner.require_absent()
        status = response.status_code
        outcome = OUTCOME_UNAVAILABLE
        points = 0
        if status != 404:
            fd = open_regular_file(paths.tmp_root, private.path, roots=roots)
            try:
                summary = validate_liquidation_stream(
                    _iter_fd(fd),
                    provider_symbol=provider_symbol,
                    start=int(params["from"]),
                    end=int(params["to"]),
                )
            finally:
                os.close(fd)
            points = summary.points
            outcome = (
                OUTCOME_EMPTY_HISTORY if points == 0 else OUTCOME_CHECKSUM_VERIFIED
            )
        parsed["status"] = status
        parsed["outcome"] = outcome
        parsed["points"] = points
        parsed["retrieved_at"] = datetime.now(UTC).isoformat()

    response, private = request_with_retry(
        transport,
        url,
        headers=headers,
        secret=secret,
        sleeper=sleeper,
        coordinator=coordinator,
        provider=obj.provider,
        identity=obj.identity,
        counters=counters,
        tmp_root=paths.tmp_root,
        device=device,
        filesystem=filesystem,
        max_bytes=remaining,
        allow_statuses={200, 404},
        limiter=limiter,
        observer=scanner.update,
        validator=_validate_liquidation,
     roots=roots,)
    status = int(parsed["status"])
    outcome = str(parsed["outcome"])
    points = int(parsed["points"])
    published = False
    try:
        retrieval = {
            "url": redact_text(url, secret),
            "status": status,
            "retrieved_at": str(parsed["retrieved_at"]),
        }
        revision = {"status": status, "points": points}
        coordinator.call(
            "reserve_charge",
            obj.provider,
            obj.identity,
            content_sha256=private.digest,
            charged_bytes=private.size,
            ceiling=pins.new_coinalyze_raw_bytes,
            fault=fault,
            http_status=status,
            outcome=outcome,
            points=points,
            request_proof=sha256_bytes(compact_json({"identity": obj.identity, "query": query})),
            retrieval=retrieval,
            revision=revision,
        )
        reserved = coordinator.call("open_charge", obj.provider, obj.identity)
        validate_charge_against_plan(
            obj,
            reserved,
            None,
            history=coordinator.call(
                "charge_history", obj.provider, obj.identity, int(reserved["generation"])
            ),
        )
        dest, _reused = publish_private_file(
            private, content_root=paths.content_root, device=device, filesystem=filesystem
        , roots=roots)
        published = True
        coordinator.call(
            "mark_charge_published", obj.provider, obj.identity, fault=fault
        )
        coordinator.call(
            "complete",
            obj.provider,
            obj.identity,
            content_sha256=private.digest,
            content_path=dest,
            sidecar_sha256=None,
            sidecar_path=None,
            listed_bytes=private.size,
            retrieved_at=str(parsed["retrieved_at"]),
            revision=revision,
            validation_state=outcome,
            fault=fault,
            settle_charge=True,
        )
        settled = coordinator.call("open_charge", obj.provider, obj.identity)
        completion = coordinator.call("completion_fact", obj.provider, obj.identity)
        validate_charge_against_plan(
            obj,
            settled,
            completion,
            require_settled=True,
            history=coordinator.call(
                "charge_history", obj.provider, obj.identity, int(settled["generation"])
            ),
        )
        return outcome
    except BaseException:
        if not published:
            # An over-budget, secret-bearing, malformed, wrong-symbol, or wrong-window
            # body never reaches the content store, the state, a receipt, or an error.
            discard_private(private, roots=roots)
            coordinator.call("release_charge", obj.provider, obj.identity)
        raise


def reconcile_open_charges(
    *,
    paths: AcquisitionPaths,
    pins: AuthorityPins,
    coordinator: Coordinator,
    state: AcquisitionState,
    fault: FaultInjector,
    roots: BoundRoots | None = None,
) -> dict[str, int]:
    """Settle or refund every reservation left behind by an interrupted transition."""
    roots = _require_bound(roots, operation="reconcile_open_charges")

    finished = 0
    released = 0
    after = 0
    while True:
        batch = coordinator.call("open_charge_batch", after)
        if not batch:
            break
        for charge in batch:
            after = int(charge["seq"])
            if "identity" not in charge:
                continue
            provider = charge["provider"]
            identity = charge["identity"]
            digest = charge["content_sha256"]
            plan_payload = coordinator.call("plan_payload", provider, identity)
            if plan_payload is None:
                raise UnsafeStateError(
                    "a Coinalyze charge has no plan row", context={"identity": identity}
                )
            shard = open_dir_chain(paths.content_root, (digest[:2],), create=True, roots=roots)
            try:
                size = probe_published_content(shard, digest, digest)
            finally:
                os.close(shard)
            if size is None:
                coordinator.call("release_charge", provider, identity)
                released += 1
                continue
            if size != int(charge["charged_bytes"]):
                raise UnsafeStateError(
                    "a reserved Coinalyze charge does not match its published bytes",
                    context={"identity": identity},
                )
            existing = coordinator.call("completion_fact", provider, identity)
            plan = PlanObject(
                provider, identity, KIND_COINALYZE_LIQUIDATION, dict(plan_payload)
            )
            history = coordinator.call(
                "charge_history", provider, identity, int(charge["generation"])
            )
            validate_charge_against_plan(plan, charge, existing, history=history)
            if existing is not None:
                validate_provider_completion(
                    plan, existing, None, paths=paths, pins=pins, roots=roots
                )
                coordinator.call(
                    "settle_existing_charge",
                    provider,
                    identity,
                    content_sha256=digest,
                    charged_bytes=int(charge["charged_bytes"]),
                )
                finished += 1
                continue
            http_status = int(charge["http_status"])
            stored_outcome = str(charge["outcome"])
            stored_points = int(charge["points"])
            dest = content_path_for(paths.content_root, digest)
            retrieval = dict(charge.get("retrieval") or {})
            retrieved_at = str(retrieval.get("retrieved_at") or "")
            if http_status == 404:
                outcome = OUTCOME_UNAVAILABLE
                points = 0
                if stored_points != 0:
                    raise UnsafeStateError(
                        "a recovered 404 Coinalyze charge has a nonzero point count",
                        context={"identity": identity},
                    )
            else:
                params = dict(plan_payload.get("params") or {})
                summary = validate_liquidation_file(
                    dest,
                    root=paths.content_root,
                    provider_symbol=str(plan_payload["provider_symbol"]),
                    start=int(params["from"]),
                    end=int(params["to"]),
                 roots=roots,)
                outcome = (
                    OUTCOME_EMPTY_HISTORY if summary.points == 0 else OUTCOME_CHECKSUM_VERIFIED
                )
                if stored_outcome != outcome:
                    raise UnsafeStateError(
                        "a recovered Coinalyze charge outcome disagrees with its body",
                        context={"identity": identity},
                    )
                if stored_points != summary.points:
                    raise UnsafeStateError(
                        "a recovered Coinalyze charge point count disagrees with its body",
                        context={"identity": identity},
                    )
                points = summary.points
            revision = dict(charge.get("revision") or {"status": http_status, "points": points})
            if str(charge.get("status") or "") == CHARGE_RESERVED:
                coordinator.call(
                    "mark_charge_published", provider, identity, fault=fault
                )
            coordinator.call(
                "complete",
                provider,
                identity,
                content_sha256=digest,
                content_path=dest,
                sidecar_sha256=None,
                sidecar_path=None,
                listed_bytes=size,
                retrieved_at=retrieved_at,
                revision=revision,
                validation_state=outcome,
                fault=fault,
                settle_charge=True,
            )
            finished += 1
    coordinator.call("authenticate_singletons")
    return {"finished": finished, "released": released}


@dataclass
class RunControls:
    max_objects: int | None = None
    max_wall_seconds: float | None = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    stop_reason: str = ""
    started_monotonic: float = 0.0
    objects_started: int = 0
    # Reentrant so a signal delivered inside a bound check cannot deadlock the handler.
    lock: threading.RLock = field(default_factory=threading.RLock)

    def request_stop(self, reason: str) -> None:
        with self.lock:
            if not self.stop_reason:
                self.stop_reason = reason
        self.stop_event.set()

    def should_stop(self) -> bool:
        if self.stop_event.is_set():
            return True
        if self.max_wall_seconds is not None:
            if time.monotonic() - self.started_monotonic >= self.max_wall_seconds:
                self.request_stop("max_wall_seconds")
                return True
        with self.lock:
            if self.max_objects is not None and self.objects_started >= self.max_objects:
                stop = True
            else:
                stop = False
        if stop:
            self.request_stop("max_objects")
        return stop

    def note_start(self) -> bool:
        with self.lock:
            if self.max_objects is not None and self.objects_started >= self.max_objects:
                reached = True
            else:
                self.objects_started += 1
                reached = False
        if reached:
            self.request_stop("max_objects")
            return False
        return True


def validate_stop_bounds(
    max_objects: int | None, max_wall_seconds: float | None
) -> None:
    if max_objects is not None:
        if (
            not isinstance(max_objects, int)
            or isinstance(max_objects, bool)
            or max_objects <= 0
        ):
            raise AuthorityError(
                "an operational object bound must be a positive integer",
                context={"max_objects": max_objects},
            )
    if max_wall_seconds is not None:
        try:
            value = float(max_wall_seconds)
        except (TypeError, ValueError) as exc:
            raise AuthorityError("an operational wall bound must be numeric") from exc
        if value != value or value in {float("inf"), float("-inf")} or value <= 0:
            raise AuthorityError(
                "an operational wall bound must be a positive finite value",
                context={"max_wall_seconds": max_wall_seconds},
            )


def _install_signal_handlers(controls: RunControls) -> Callable[[], None]:
    previous: dict[int, Any] = {}

    def handler(signum: int, _frame: Any) -> None:
        controls.request_stop(f"signal:{signum}")

    for sig in (signal.SIGINT, signal.SIGTERM):
        previous[sig] = signal.getsignal(sig)
        try:
            signal.signal(sig, handler)
        except ValueError:
            pass

    def restore() -> None:
        for sig, prior in previous.items():
            try:
                signal.signal(sig, prior)
            except ValueError:
                pass

    return restore


def _exit_for_state(state: AcquisitionState, *, capacity: bool) -> tuple[int, str]:
    if capacity:
        return EXIT_CAPACITY_BLOCKED, "capacity"
    remaining = state.pending_count()
    if remaining or state.open_charge_count():
        return EXIT_RESUMABLE_PARTIAL, "partial"
    if state.typed_gap_present():
        return EXIT_COMPLETE_WITH_TERMINAL_GAPS, "complete_with_typed_gaps"
    return EXIT_COMPLETE, "complete"


def build_plan(
    paths: AcquisitionPaths,
    pins: AuthorityPins,
    *,
    filesystem: Filesystem | None = None,
) -> PlanSummary:
    filesystem = filesystem or RealFilesystem()
    return load_authority_bundle(paths, pins, filesystem)["summary"]


def consume_manifest(
    store_root: Path,
    descriptor: Mapping[str, Any],
    pins: AuthorityPins,
    *,
    roots: BoundRoots | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream selected Binance rows; never materialize the accepted main universe."""

    yield from iter_selected_binance(store_root, descriptor, pins, roots=roots)


def run_plan(
    paths: AcquisitionPaths,
    pins: AuthorityPins = PRODUCTION_PINS,
    *,
    filesystem: Filesystem | None = None,
    transport: StreamTransport | None = None,
    fault: FaultInjector | None = None,
) -> dict[str, Any]:
    if transport is not None:
        raise AuthorityError("plan cannot use a network transport")
    filesystem = filesystem or RealFilesystem()
    summary, state, bundle = bind_session(
        paths, pins, filesystem, install=True, fault=fault
    )
    try:
        return {
            "plan_identity": summary.identity,
            "plan_receipt": bundle["receipt"],
            "counts": {
                "objects": summary.object_count,
                "binance": pins.combined_objects,
                "coinalyze_logical_receipts": pins.coinalyze_logical_receipts,
            },
            "exit_code": EXIT_COMPLETE,
        }
    finally:
        _close_session(state, bundle)


def _close_session(state: AcquisitionState, bundle: Mapping[str, Any]) -> None:
    errors: list[BaseException] = []
    try:
        state.close()
    except Exception as exc:  # noqa: BLE001
        errors.append(exc)
    roots = bundle.get("roots")
    if roots is not None:
        try:
            roots.close()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
    if errors:
        raise UnsafeStateError(
            "session resources could not be released",
            context={"error": type(errors[0]).__name__},
        ) from errors[0]


def run_acquire(
    paths: AcquisitionPaths,
    pins: AuthorityPins = PRODUCTION_PINS,
    *,
    filesystem: Filesystem | None = None,
    transport: StreamTransport | None = None,
    max_objects: int | None = None,
    max_wall_seconds: float | None = None,
    secret: str | None = None,
    fault: FaultInjector | None = None,
    sleeper: Callable[[float], None] | None = None,
    limiter: RateLimiter | None = None,
    roots: BoundRoots | None = None,
) -> dict[str, Any]:
    if transport is None:
        raise AuthorityError("acquire requires an injected or production transport")
    validate_stop_bounds(max_objects, max_wall_seconds)
    filesystem = filesystem or RealFilesystem()
    fault = fault or FaultInjector()
    secret = secret if secret is not None else os.environ.get("COINALYZE_API_KEY")
    if secret == "":
        secret = None
    summary, state, bundle = bind_session(
        paths, pins, filesystem, install=True, fault=fault
    )
    restore_signals: Callable[[], None] | None = None
    coordinator: Coordinator | None = None
    try:
        filesystem = bundle.get("filesystem") or filesystem
        roots = _require_bound(bundle.get("roots"), operation="run_acquire")
        for scratch in (paths.tmp_root, paths.run_receipt_dir, paths.terminal_dir):
            _cleanup_partials(scratch, roots=roots)
        device = bundle["device"]
        controls = RunControls(
            max_objects=max_objects,
            max_wall_seconds=max_wall_seconds,
            started_monotonic=time.monotonic(),
        )
        restore_signals = _install_signal_handlers(controls)
        counters = RunCounters()
        fatal = FatalSlot()
        sleeper_fn = sleeper or time.sleep
        limiter = limiter or RateLimiter(sleeper=sleeper_fn)
        started_at = datetime.now(UTC).isoformat()
        run_id = sha256_bytes(f"{started_at}:{os.urandom(8).hex()}".encode("utf-8"))
        pre_capacity = bundle["capacity"]
        before = state.counts()
        coordinator = Coordinator(state)
        capacity = CapacityGuard(
            pins=pins, paths=paths, filesystem=filesystem, coordinator=coordinator
        )
        coordinator.start()
        workers: list[threading.Thread] = []
        work: queue.Queue[tuple[PlanObject, CompletionFact | None] | None] = queue.Queue(
            maxsize=QUEUE_CEILING
        )
        try:
            state.begin_run(run_id, started_at, pre_capacity=pre_capacity)
            fault.check("after_run_begin", run_id)
            reconcile_open_charges(
                paths=paths,
                pins=pins,
                coordinator=coordinator,
                state=state,
                fault=fault,
             roots=roots,)
            adopt_retained(
                paths,
                pins,
                coordinator,
                state,
                progress=bundle["progress"],
                retained_credit=bundle["retained_credit"],
                filesystem=filesystem,
                device=device,
                fault=fault,
             roots=roots,)

            def _process(item: tuple[PlanObject, CompletionFact | None]) -> None:
                plan, done = item
                if done is not None:
                    # A completed provider object is fully re-proved before it is skipped;
                    # a completion row alone is never coverage.
                    sidecar = (
                        coordinator.call("sidecar_fact", plan.provider, plan.identity)
                        if plan.kind == KIND_BINANCE
                        else None
                    )
                    validate_provider_completion(
                        plan,
                        done,
                        sidecar,
                        paths=paths,
                        pins=pins,
                        roots=bundle.get("roots"),
                    )
                    return
                if controls.stop_event.is_set() or not controls.note_start():
                    return
                if plan.kind == KIND_BINANCE:
                    acquire_binance_object(
                        plan,
                        paths=paths,
                        coordinator=coordinator,
                        transport=transport,
                        filesystem=filesystem,
                        device=device,
                        pins=pins,
                        capacity=capacity,
                        fault=fault,
                        counters=counters,
                        sleeper=sleeper_fn,
                     roots=roots,)
                elif plan.kind == KIND_COINALYZE_INVENTORY:
                    acquire_coinalyze_inventory(
                        plan,
                        paths=paths,
                        coordinator=coordinator,
                        filesystem=filesystem,
                        device=device,
                        fault=fault,
                        report=bundle["report"],
                     roots=roots,)
                else:
                    acquire_coinalyze_liquidation(
                        plan,
                        paths=paths,
                        coordinator=coordinator,
                        transport=transport,
                        filesystem=filesystem,
                        device=device,
                        pins=pins,
                        secret=secret,
                        limiter=limiter,
                        capacity=capacity,
                        fault=fault,
                        counters=counters,
                        sleeper=sleeper_fn,
                     roots=roots,)

            def worker() -> None:
                # A worker never dies with work outstanding and never re-raises past this
                # loop, so a fatal can neither strand a queue item nor deadlock settlement.
                while True:
                    item = work.get()
                    if item is None:
                        return
                    try:
                        _process(item)
                    except CapacityBlocked as exc:
                        counters.note_error(redact_text(exc.message, secret))
                        coordinator.call("note_run_error")
                        controls.request_stop("capacity")
                    except BudgetExhausted as exc:
                        counters.note_error(redact_text(exc.message, secret))
                        coordinator.call("note_run_error")
                        controls.request_stop("coinalyze_budget")
                    except FaultInjected as exc:
                        counters.note_error(redact_text(exc.message, secret))
                        coordinator.call("note_run_error")
                        controls.request_stop("fault")
                    except (AuthorityError, UnsafeStateError) as exc:
                        counters.note_error(redact_text(exc.message, secret))
                        coordinator.call("note_run_error")
                        fatal.offer(exc)
                        controls.request_stop("fatal")
                    except AcquisitionError as exc:
                        counters.note_error(redact_text(exc.message, secret))
                        coordinator.call("note_run_error")
                    except BaseException as exc:  # noqa: BLE001 - settled, never stranded
                        try:
                            raise UnsafeStateError(
                                "an unexpected worker failure stopped the run: "
                                f"{_diagnostic(exc, secret)}",
                                context={
                                    "error_type": type(exc).__name__,
                                    "error": _diagnostic(exc, secret),
                                },
                            ) from exc
                        except UnsafeStateError as wrapped:
                            fatal.offer(wrapped)
                        controls.request_stop("fatal")

            workers = [
                threading.Thread(target=worker, name=f"gate2-worker-{index}", daemon=True)
                for index in range(WORKER_CEILING)
            ]
            for thread in workers:
                thread.start()
            after = 0
            feeding = True
            while feeding:
                batch = coordinator.call("schedulable_batch", after)
                if not batch:
                    break
                for seq, plan, done in batch:
                    after = seq
                    if controls.should_stop():
                        feeding = False
                        break
                    work.put((plan, done))
                    BOUND_TELEMETRY.note("max_work_depth", work.qsize())
        finally:
            for _ in workers:
                work.put(None)
            for thread in workers:
                thread.join(timeout=120.0)
            for thread in workers:
                if thread.is_alive():  # pragma: no cover - defensive
                    fatal.offer(UnsafeStateError("a worker did not settle"))
            coordinator.stop()
        after = state.counts()
        post_capacity = capacity.evaluate()
        capacity_blocked = (
            capacity.blocked
            or controls.stop_reason == "capacity"
            or post_capacity["storage_preflight_state"] != "sufficient"
        )
        exit_code, stop_reason = _exit_for_state(state, capacity=capacity_blocked)
        fatal_error = fatal.error
        if fatal_error is not None:
            exit_code = map_exception(fatal_error)
            stop_reason = "fatal"
        elif controls.stop_reason and exit_code == EXIT_RESUMABLE_PARTIAL:
            stop_reason = controls.stop_reason
        snapshot = counters.snapshot()
        # The exact attempt delta is derived from the durable coordinator-owned attempt
        # facts; the in-run counter only bounds the redacted network sample.
        durable_attempts = after["attempts"] - before["attempts"]
        if int(snapshot["network_calls"]) != int(durable_attempts):
            raise UnsafeStateError(
                "network-call count does not equal durable attempt delta",
                context={
                    "network_calls": snapshot["network_calls"],
                    "attempt_delta": durable_attempts,
                },
            )
        state.authenticate_domains()
        state.authenticate_singletons()
        fault.check("before_run_finalization", run_id)
        ended_at = datetime.now(UTC).isoformat()
        authority_doc = plan_receipt_document(summary, paths, pins, device=device)
        receipt = state.finish_run(
            run_id,
            ended_at=ended_at,
            stop_reason=stop_reason,
            receipt_sha256=None,
            network_calls=int(snapshot["network_calls"]),
            error_count=int(snapshot["errors"]),
            network_sample=list(snapshot["network_sample"]),
            pre_capacity=pre_capacity,
            post_capacity=post_capacity,
            capacity_blocked=capacity_blocked,
            receipt_directory=str(paths.run_receipt_dir),
            authority_block=authority_doc["authority"],
            code_identity=dict(summary.code_identity),
        )
        if receipt is None:
            raise UnsafeStateError("run finalization produced no receipt intent")
        state.authenticate_domains()
        published = state.complete_publication(
            run_id,
            filesystem=filesystem,
            device=device,
            roots=roots,
            fault=fault,
        )
        result = {
            "exit_code": exit_code,
            "run_receipt": published,
            "counts": after,
            "network_calls": snapshot["network_sample"],
            "network_call_count": snapshot["network_calls"],
            "stop_reason": stop_reason,
            "errors": snapshot["error_sample"],
            "error_count": snapshot["errors"],
            "semantic_state_digest": receipt["semantic_state_digest"],
            "attempts": durable_attempts,
        }
        if fatal_error is not None:
            raise fatal_error
        return result
    finally:
        if restore_signals is not None:
            restore_signals()
        if coordinator is not None:
            coordinator.stop()
        _close_session(state, bundle)


def _require_equal(actual: int, expected: int, message: str) -> None:
    if int(actual) != int(expected):
        raise UnsafeStateError(
            message, context={"expected": int(expected), "actual": int(actual)}
        )


def verify_state(
    paths: AcquisitionPaths,
    pins: AuthorityPins = PRODUCTION_PINS,
    *,
    filesystem: Filesystem | None = None,
    transport: StreamTransport | None = None,
    roots: BoundRoots | None = None,
) -> dict[str, Any]:
    """Offline terminal verification: prove the accepted release, then publish it.

    Every completion is joined to its exact plan row and re-proved by the same shared
    provider validator that resume uses. No terminal artifact is written until the whole
    proof succeeds, and repeated verification publishes byte-identical evidence with zero
    network activity.
    """

    if transport is not None:
        raise AuthorityError("verify cannot use a network transport")
    filesystem = filesystem or RealFilesystem()
    summary, state, bundle = bind_session(paths, pins, filesystem, install=False)
    try:
        filesystem = bundle.get("filesystem") or filesystem
        roots = _require_bound(bundle.get("roots"), operation="verify_state")
        _cleanup_partials(paths.terminal_dir, roots=roots)
        device = bundle["device"]
        db = state._db()
        head = state.seal_head_row()
        if head is None:
            raise UnsafeStateError("the authenticated seal head is missing")
        current = state.current_watermarks()
        for key in state._zero_watermarks():
            if key == "seal_hi":
                # A receipt cannot seal its own link without a hash cycle, so the head's
                # own seal row is the one legitimate row beyond the sealed prefix.
                own = state.seal_fact(head["receipt_sha256"])
                expected = int(head[key]) + (1 if own is not None else 0)
                if int(current[key]) != expected or (
                    own is not None and int(own["seq"]) != expected
                ):
                    raise UnsafeStateError(
                        "terminal verification refuses an unsealed seal tail",
                        context={"head": head[key], "current": current[key]},
                    )
                continue
            if int(current[key]) != int(head[key]):
                raise UnsafeStateError(
                    "terminal verification refuses an unsealed tail",
                    context={"watermark": key, "head": head[key], "current": current[key]},
                )
        state.authenticate_singletons()
        if state.open_charge_count():
            raise UnsafeStateError(
                "terminal success refused while a Coinalyze charge is unsettled"
            )
        binance_plan = 0
        binance_completions = 0
        binance_listed = 0
        retained_rows = 0
        retained_listed = 0
        retained_cost_keys = 0
        new_listed = 0
        coinalyze_logical = 0
        coinalyze_listed = 0
        sidecar_rows = 0
        sidecar_listed = 0
        for plan, fact in state.iter_schedulable():
            if plan.kind == KIND_BINANCE:
                binance_plan += 1
            else:
                coinalyze_logical += 1
            if fact is None:
                raise UnsafeStateError(
                    "terminal success refused while requests remain pending",
                    context={"identity": plan.identity},
                )
            sidecar = (
                state.sidecar_fact(plan.provider, plan.identity)
                if plan.kind == KIND_BINANCE
                else None
            )
            proof = validate_provider_completion(
                plan, fact, sidecar, paths=paths, pins=pins, roots=bundle.get("roots")
            )
            if plan.kind == KIND_BINANCE:
                binance_completions += 1
                binance_listed += proof.content_bytes
                sidecar_rows += 1
                sidecar_listed += proof.sidecar_bytes
                if proof.retained:
                    retained_rows += 1
                    retained_listed += proof.content_bytes
                    if _family_of(plan.identity) in COST_FAMILIES:
                        retained_cost_keys += 1
                else:
                    new_listed += proof.content_bytes
            elif plan.kind == KIND_COINALYZE_LIQUIDATION:
                coinalyze_listed += proof.content_bytes
                charge = state.open_charge(plan.provider, plan.identity)
                if charge is None:
                    raise UnsafeStateError(
                        "a liquidation completion has no charge descriptor",
                        context={"identity": plan.identity},
                    )
                validate_charge_against_plan(
                    plan,
                    charge,
                    fact,
                    require_settled=True,
                    history=state.charge_history(
                        plan.provider, plan.identity, int(charge["generation"])
                    ),
                )
        gap_rows = 0
        for gap in state.iter_gaps():
            plan_row = state.plan_payload(gap["provider"], gap["identity"])
            if plan_row is None:
                raise UnsafeStateError(
                    "a terminal gap has no plan row", context={"identity": gap["identity"]}
                )
            if str(gap["kind"]) != GAP_UNSUPPORTED:
                raise UnsafeStateError("a terminal gap is not an unsupported mapping")
            gap_rows += 1
        counts = state.counts()
        _require_equal(
            binance_plan, pins.combined_objects, "the Binance plan row count changed"
        )
        _require_equal(
            binance_completions,
            pins.combined_objects,
            "not every Binance plan object is reconciled",
        )
        _require_equal(
            coinalyze_logical,
            pins.coinalyze_logical_receipts,
            "the Coinalyze logical receipt count changed",
        )
        _require_equal(
            gap_rows, pins.coinalyze_unsupported, "the unsupported gap count changed"
        )
        _require_equal(
            counts["planned"],
            pins.combined_objects + pins.coinalyze_logical_receipts + pins.coinalyze_unsupported,
            "the installed plan row count changed",
        )
        _require_equal(
            binance_listed, pins.combined_bytes, "the Binance listed byte total changed"
        )
        _require_equal(
            retained_rows,
            pins.retained_credit_objects,
            "the retained object count changed",
        )
        _require_equal(
            retained_listed,
            pins.retained_credit_bytes,
            "the retained byte credit changed",
        )
        if pins.retained_credit_objects == PRODUCTION_PINS.retained_credit_objects:
            _require_equal(retained_cost_keys, 5, "the five retained cost keys changed")
        _require_equal(
            new_listed,
            pins.combined_bytes - pins.retained_credit_bytes,
            "the new Binance raw byte equation does not reconcile",
        )
        if pins.new_binance_raw_bytes == pins.combined_bytes - pins.retained_credit_bytes:
            _require_equal(
                new_listed,
                pins.new_binance_raw_bytes,
                "the accepted new Binance raw allocation does not reconcile",
            )
        settled = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(c.charged_bytes), 0) FROM coinalyze_charge c "
            "WHERE (SELECT t.status FROM charge_transition t "
            "WHERE t.provider = c.provider AND t.identity = c.identity "
            "AND t.generation = c.generation "
            "ORDER BY t.seq DESC LIMIT 1) = ?",
            (CHARGE_SETTLED,),
        ).fetchone()
        _require_equal(
            int(settled[1]),
            counts["coinalyze_charged"],
            "the Coinalyze ledger does not equal its settled charges",
        )
        _require_equal(
            int(settled[1]),
            coinalyze_listed,
            "the Coinalyze ledger does not equal its completed response bytes",
        )
        if counts["coinalyze_charged"] > pins.new_coinalyze_raw_bytes:
            raise UnsafeStateError("Coinalyze budget is over the accepted allocation")
        if state.pending_count():
            raise UnsafeStateError("terminal success refused while requests remain pending")
        unique_objects, unique_bytes = state.unique_physical()
        unique_raw_n, unique_raw_b = state.unique_raw_content()
        unique_side_n, unique_side_b = state.unique_sidecar_content()
        overlap = db.execute(
            "SELECT 1 FROM (SELECT DISTINCT content_sha256 AS d FROM completion) "
            "INTERSECT SELECT sidecar_sha256 FROM sidecar_fact LIMIT 1"
        ).fetchone()
        if overlap is not None:
            raise UnsafeStateError("a sidecar shares a content address with a raw object")
        _require_equal(
            unique_objects,
            unique_raw_n + unique_side_n,
            "the unique physical object count omits sidecars",
        )
        _require_equal(
            unique_bytes,
            unique_raw_b + unique_side_b,
            "the unique physical byte total omits sidecars",
        )
        _require_equal(
            unique_side_n,
            sidecar_rows,
            "the unique sidecar object count disagrees with sidecar facts",
        )
        liquidation_join = db.execute(
            "SELECT COUNT(*) FROM completion c "
            "JOIN coinalyze_charge ch ON ch.provider = c.provider AND ch.identity = c.identity "
            "JOIN plan_entry p ON p.provider = c.provider AND p.identity = c.identity "
            "WHERE p.kind = ? AND (SELECT t.status FROM charge_transition t "
            "WHERE t.provider = ch.provider AND t.identity = ch.identity "
            "AND t.generation = ch.generation "
            "ORDER BY t.seq DESC LIMIT 1) = ?",
            (KIND_COINALYZE_LIQUIDATION, CHARGE_SETTLED),
        ).fetchone()
        _require_equal(
            int(liquidation_join[0]),
            pins.coinalyze_supported,
            "the Coinalyze liquidation completion/charge join changed",
        )
        non_liquidation_charges = db.execute(
            "SELECT COUNT(*) FROM coinalyze_charge ch JOIN plan_entry p "
            "ON p.provider = ch.provider AND p.identity = ch.identity "
            "WHERE p.kind != ?",
            (KIND_COINALYZE_LIQUIDATION,),
        ).fetchone()
        _require_equal(
            int(non_liquidation_charges[0]),
            0,
            "a Coinalyze inventory or gap row carries a charge",
        )
        _require_equal(
            sidecar_rows,
            int(db.execute("SELECT COUNT(*) FROM sidecar_fact").fetchone()[0]),
            "a sidecar fact is not joined to a Binance completion",
        )
        exit_code, status_name = _exit_for_state(state, capacity=False)
        terminal_digest, uncompressed_digest, rows = _publish_terminal_manifest(
            state, paths=paths, device=device, filesystem=filesystem
        , roots=roots)
        live_ledger = db.execute("SELECT charged FROM coinalyze_ledger WHERE id=1").fetchone()
        semantic = hashlib.sha256()
        semantic.update(str(head["prefix_digest"]).encode("ascii"))
        semantic.update(
            compact_json(
                {
                    "section": "live_ledger",
                    "charged": None if live_ledger is None else int(live_ledger[0]),
                }
            )
        )
        receipt = {
            "schema_version": TERMINAL_SCHEMA,
            "ticket": TICKET_ID,
            "policy_identity": POLICY_IDENTITY,
            "plan_identity": state.plan_identity(),
            "code_identity": dict(summary.code_identity),
            "status": status_name.upper()
            if status_name != "complete_with_typed_gaps"
            else "COMPLETE_WITH_TYPED_GAPS",
            "counts": counts,
            "pending": 0,
            "chain_receipt_sha256": head["receipt_sha256"],
            "semantic_state_digest": semantic.hexdigest(),
            "chain": {
                "head_receipt_sha256": head["receipt_sha256"],
                "head_prefix_digest": head["prefix_digest"],
                "head_predecessor_sha256": head["predecessor_sha256"],
                "plan_receipt_sha256": state.authority_row()["plan_receipt_sha256"],
                "high_watermarks": {
                    key: int(head[key]) for key in state._zero_watermarks()
                },
                "seal_links": int(
                    db.execute("SELECT COUNT(*) FROM run_seal").fetchone()[0]
                ),
            },
            "terminal_manifest_sha256": terminal_digest,
            "terminal_manifest_uncompressed_sha256": uncompressed_digest,
            "terminal_rows": rows,
            "reconciliation": {
                "binance_plan_objects": binance_plan,
                "binance_completions": binance_completions,
                "binance_listed_bytes": binance_listed,
                "coinalyze_logical_receipts": coinalyze_logical,
                "coinalyze_response_bytes": coinalyze_listed,
                "unsupported_gaps": gap_rows,
                "retained_objects": retained_rows,
                "retained_listed_bytes": retained_listed,
                "retained_cost_keys": retained_cost_keys,
                "new_listed_bytes": new_listed,
                "sidecar_objects": sidecar_rows,
                "sidecar_bytes": sidecar_listed,
                "unique_raw_content_objects": unique_raw_n,
                "unique_raw_content_bytes": unique_raw_b,
                "unique_sidecar_objects": unique_side_n,
                "unique_sidecar_bytes": unique_side_b,
                "unique_physical_objects": unique_objects,
                "unique_physical_bytes": unique_bytes,
                "coinalyze_charged_bytes": counts["coinalyze_charged"],
                "coinalyze_settled_liquidations": int(liquidation_join[0]),
            },
        }
        published = write_named_receipt(
            receipt, paths.terminal_dir, device, filesystem, roots=bundle.get("roots")
        )
        return {
            "exit_code": exit_code,
            "status": receipt["status"],
            "terminal_receipt": published,
            "terminal_manifest": str(
                paths.terminal_dir / f"{terminal_digest}.jsonl.gz"
            ),
            "counts": counts,
            "reconciliation": receipt["reconciliation"],
            "semantic_state_digest": receipt["semantic_state_digest"],
        }
    finally:
        _close_session(state, bundle)


def _publish_terminal_manifest(
    state: AcquisitionState,
    *,
    paths: AcquisitionPaths,
    device: str,
    filesystem: Filesystem,
    roots: BoundRoots | None = None,
) -> tuple[str, str, int]:
    """Deterministic gzip: empty header filename, mtime 0, hashed while streaming."""
    roots = _require_bound(roots, operation="_publish_terminal_manifest")

    if filesystem.device_of(paths.terminal_dir) != device:
        raise UnsafeStateError("cross-device publication is refused")
    directory, _name = open_parent_dir(
        paths.terminal_dir, paths.terminal_dir / "probe", create=True
    , roots=roots)
    os.close(directory)
    expected_rows = int(
        state._db().execute(
            "SELECT "
            "(SELECT COUNT(*) FROM plan_entry) + "
            "(SELECT COUNT(*) FROM completion) + "
            "(SELECT COUNT(*) FROM sidecar_fact) + "
            "(SELECT COUNT(*) FROM coinalyze_charge) + "
            "(SELECT COUNT(*) FROM charge_transition) + "
            "(SELECT COUNT(*) FROM attempt) + "
            "(SELECT COUNT(*) FROM run_metadata) + "
            "(SELECT COUNT(*) FROM run_seal) + "
            "(SELECT COUNT(*) FROM terminal_gap) + 3"
        ).fetchone()[0]
    )
    tmp_dir, fd, tmp_name = _open_private(paths.terminal_dir, prefix="terminal", roots=roots)
    uncompressed = hashlib.sha256()
    rows = 0
    published = False
    try:
        handle = os.fdopen(os.dup(fd), "wb", closefd=True)
        try:
            with gzip.GzipFile(
                filename="", fileobj=handle, mode="wb", mtime=0, compresslevel=9
            ) as archive:
                head = state.seal_head_row() or {}
                line = compact_json({"record_type": "seal", **head})
                archive.write(line)
                uncompressed.update(line)
                rows += 1
                authority = state.authority_row()
                line = compact_json(
                    {
                        "record_type": "authority",
                        "plan_identity": authority["plan_identity"],
                        "plan_receipt_sha256": authority["plan_receipt_sha256"],
                        "pins": authority["pins"],
                        "code": authority["code"],
                        "destination": authority["destination"],
                        "device": authority["device"],
                        "created_at": authority["created_at"],
                    }
                )
                archive.write(line)
                uncompressed.update(line)
                rows += 1
                after_plan = 0
                while True:
                    batch = state._db().execute(
                        "SELECT seq, provider, identity, kind, payload_json FROM plan_entry "
                        "WHERE seq > ? ORDER BY seq LIMIT ?",
                        (after_plan, CURSOR_BATCH),
                    ).fetchall()
                    if not batch:
                        break
                    for row in batch:
                        after_plan = int(row[0])
                        line = compact_json(
                            {
                                "record_type": "plan",
                                "seq": int(row[0]),
                                "provider": str(row[1]),
                                "identity": str(row[2]),
                                "kind": str(row[3]),
                                "payload_json": str(row[4]),
                            }
                        )
                        archive.write(line)
                        uncompressed.update(line)
                        rows += 1
                for item in state.iter_completions():
                    line = compact_json({"record_type": "completion", **item})
                    archive.write(line)
                    uncompressed.update(line)
                    rows += 1
                for item in state.iter_sidecar_facts():
                    line = compact_json({"record_type": "sidecar", **item})
                    archive.write(line)
                    uncompressed.update(line)
                    rows += 1
                for item in state.iter_gaps():
                    line = compact_json(
                        {
                            "record_type": "gap",
                            "provider": item["provider"],
                            "identity": item["identity"],
                            "kind": item["kind"],
                            "fact": item["fact"],
                        }
                    )
                    archive.write(line)
                    uncompressed.update(line)
                    rows += 1
                for item in state.iter_charge_facts():
                    line = compact_json({"record_type": "charge", **item})
                    archive.write(line)
                    uncompressed.update(line)
                    rows += 1
                for item in state.iter_charge_transitions():
                    line = compact_json({"record_type": "charge_transition", **item})
                    archive.write(line)
                    uncompressed.update(line)
                    rows += 1
                marks = {
                    key: int(head.get(key, 0)) for key in state._zero_watermarks()
                } if head else state.current_watermarks()
                sealed_charged = int(
                    state._db().execute(
                        "SELECT COALESCE(SUM(c.charged_bytes), 0) FROM coinalyze_charge c "
                        "WHERE c.seq <= ? AND (SELECT t.status FROM charge_transition t "
                        "WHERE t.provider = c.provider AND t.identity = c.identity "
                        "AND t.generation = c.generation AND t.seq <= ? "
                        f"ORDER BY t.seq DESC LIMIT 1) IS NOT '{CHARGE_RELEASED}'",
                        (int(marks["charge_hi"]), int(marks["transition_hi"])),
                    ).fetchone()[0]
                )
                live_row = state._db().execute(
                    "SELECT charged FROM coinalyze_ledger WHERE id=1"
                ).fetchone()
                line = compact_json(
                    {
                        "record_type": "ledger",
                        "charged": sealed_charged,
                        "live_charged": None if live_row is None else int(live_row[0]),
                    }
                )
                archive.write(line)
                uncompressed.update(line)
                rows += 1
                after_attempt = -1
                while True:
                    batch = state._db().execute(
                        "SELECT id, provider, identity, started_at, ended_at, class, "
                        "status_code, redacted_fact_json FROM attempt "
                        "WHERE id > ? ORDER BY id LIMIT ?",
                        (after_attempt, CURSOR_BATCH),
                    ).fetchall()
                    if not batch:
                        break
                    for row in batch:
                        after_attempt = int(row[0])
                        line = compact_json(
                            {
                                "record_type": "attempt",
                                "id": int(row[0]),
                                "provider": str(row[1]),
                                "identity": str(row[2]),
                                "started_at": str(row[3]),
                                "ended_at": None if row[4] is None else str(row[4]),
                                "class": str(row[5]),
                                "status_code": None if row[6] is None else int(row[6]),
                                "fact": json.loads(str(row[7])),
                            }
                        )
                        archive.write(line)
                        uncompressed.update(line)
                        rows += 1
                for item in state.iter_run_facts():
                    line = compact_json({"record_type": "run", **item})
                    archive.write(line)
                    uncompressed.update(line)
                    rows += 1
                for item in state.iter_seal_facts():
                    line = compact_json({"record_type": "seal_link", **item})
                    archive.write(line)
                    uncompressed.update(line)
                    rows += 1
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
        if rows != expected_rows:
            raise UnsafeStateError(
                "terminal manifest row equation does not reconcile",
                context={"expected": expected_rows, "actual": rows},
            )
        os.fsync(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        digest, size = sha256_fd(fd)
    except Exception:
        os.close(fd)
        try:
            os.unlink(tmp_name, dir_fd=tmp_dir)
        except FileNotFoundError:
            pass
        os.close(tmp_dir)
        raise
    os.close(fd)
    os.close(tmp_dir)
    private = PrivateFile(root=paths.terminal_dir, name=tmp_name, digest=digest, size=size)
    try:
        target = open_dir_chain(paths.terminal_dir, (), create=True, roots=roots)
        try:
            final = f"{digest}.jsonl.gz"
            if probe_published_content(target, final, digest) is not None:
                discard_private(private, roots=roots)
                published = True
                return digest, uncompressed.hexdigest(), rows
            source_dir, source_name = open_parent_dir(private.root, private.path, roots=roots)
            try:
                try:
                    _move_no_replace(source_dir, source_name, target, final)
                except FileExistsError:
                    discard_private(private, roots=roots)
                    _require_published(target, final, digest)
                    published = True
                    return digest, uncompressed.hexdigest(), rows
                except OSError as exc:
                    if exc.errno == errno.EEXIST:
                        discard_private(private, roots=roots)
                        _require_published(target, final, digest)
                        published = True
                        return digest, uncompressed.hexdigest(), rows
                    raise UnsafeStateError("no-replace terminal publication failed") from exc
            finally:
                os.close(source_dir)
            fsync_dir_fd(target)
        finally:
            os.close(target)
        published = True
        return digest, uncompressed.hexdigest(), rows
    finally:
        if not published:
            discard_private(private, roots=roots)


def reconstruct_digests_from_terminal_lines(
    lines: Iterator[bytes],
) -> tuple[str, str]:
    """Rebuild head prefix and terminal semantic digest from one bounded record stream."""

    hasher = hashlib.sha256()
    plan_digest = hashlib.sha256()
    plan_rows = 0
    attempt_digest = hashlib.sha256()
    attempts = 0
    marks: dict[str, int] | None = None
    live_charged: int | None = None
    sealed_charged: int | None = None
    saw_authority = False
    flushed_plan = False
    flushed_attempts = False
    for raw in lines:
        item = json.loads(raw.decode("utf-8"))
        kind = str(item.get("record_type") or "")
        if kind == "seal":
            marks = {
                key: int(item.get(key, 0))
                for key in (
                    "attempt_hi",
                    "completion_hi",
                    "sidecar_hi",
                    "charge_hi",
                    "transition_hi",
                    "run_hi",
                    "seal_hi",
                )
            }
            continue
        if kind == "authority":
            hasher.update(
                compact_json(
                    {
                        "section": "authority",
                        "plan_identity": item["plan_identity"],
                        "plan_receipt_sha256": item["plan_receipt_sha256"],
                        "pins": item["pins"],
                        "code": item["code"],
                        "destination": item["destination"],
                        "device": item["device"],
                        "created_at": item["created_at"],
                    }
                )
            )
            saw_authority = True
            continue
        if kind == "plan":
            plan_rows += 1
            plan_digest.update(str(item["payload_json"]).encode("utf-8"))
            continue
        if not flushed_plan:
            hasher.update(
                compact_json(
                    {"section": "plan", "rows": plan_rows, "digest": plan_digest.hexdigest()}
                )
            )
            flushed_plan = True
        if kind == "completion":
            seq = int(item["seq"])
            if marks is not None and seq > int(marks["completion_hi"]):
                continue
            hasher.update(
                compact_json(
                    {
                        "section": "completion",
                        "seq": seq,
                        "provider": item["provider"],
                        "identity": item["identity"],
                        "content_sha256": item["content_sha256"],
                        "content_path": item["content_path"],
                        "sidecar_sha256": item["sidecar_sha256"],
                        "sidecar_path": item["sidecar_path"],
                        "listed_bytes": item["listed_bytes"],
                        "retrieved_at": item["retrieved_at"],
                        "revision": item["revision"],
                        "validation_state": item["validation_state"],
                    }
                )
            )
            continue
        if kind == "sidecar":
            seq = int(item["seq"])
            if marks is not None and seq > int(marks["sidecar_hi"]):
                continue
            hasher.update(
                compact_json(
                    {
                        "section": "sidecar",
                        "seq": seq,
                        "provider": item["provider"],
                        "identity": item["identity"],
                        "sidecar_sha256": item["sidecar_sha256"],
                        "sidecar_path": item["sidecar_path"],
                        "sidecar_bytes": item["sidecar_bytes"],
                        "provider_checksum": item["provider_checksum"],
                    }
                )
            )
            continue
        if kind == "gap":
            hasher.update(
                compact_json(
                    {
                        "section": "gap",
                        "provider": item["provider"],
                        "identity": item["identity"],
                        "kind": item["kind"],
                        "fact": item["fact"],
                    }
                )
            )
            continue
        if kind == "charge":
            seq = int(item["seq"])
            if marks is not None and seq > int(marks["charge_hi"]):
                continue
            hasher.update(
                compact_json(
                    {
                        "section": "charge",
                        **{key: value for key, value in item.items() if key != "record_type"},
                    }
                )
            )
            continue
        if kind == "charge_transition":
            seq = int(item["seq"])
            if marks is not None and seq > int(marks["transition_hi"]):
                continue
            hasher.update(
                compact_json(
                    {
                        "section": "charge_transition",
                        **{key: value for key, value in item.items() if key != "record_type"},
                    }
                )
            )
            continue
        if kind == "ledger":
            sealed_charged = int(item["charged"])
            live_charged = item.get("live_charged")
            hasher.update(compact_json({"section": "ledger", "charged": sealed_charged}))
            continue
        if kind == "attempt":
            ident = int(item["id"])
            if marks is not None and ident > int(marks["attempt_hi"]):
                continue
            attempts += 1
            attempt_digest.update(
                compact_json({key: value for key, value in item.items() if key != "record_type"})
            )
            continue
        if not flushed_attempts:
            hasher.update(
                compact_json(
                    {
                        "section": "attempts",
                        "count": attempts,
                        "digest": attempt_digest.hexdigest(),
                    }
                )
            )
            flushed_attempts = True
        if kind == "run":
            seq = int(item["seq"])
            if marks is not None and seq > int(marks["run_hi"]):
                continue
            hasher.update(
                compact_json(
                    {"section": "run", **{key: value for key, value in item.items() if key != "record_type"}}
                )
            )
            continue
        if kind == "seal_link":
            seq = int(item["seq"])
            if marks is not None and seq > int(marks["seal_hi"]):
                continue
            hasher.update(
                compact_json(
                    {
                        "section": "seal",
                        **{key: value for key, value in item.items() if key != "record_type"},
                    }
                )
            )
            continue
    if not flushed_plan:
        hasher.update(
            compact_json(
                {"section": "plan", "rows": plan_rows, "digest": plan_digest.hexdigest()}
            )
        )
    if not flushed_attempts:
        hasher.update(
            compact_json(
                {"section": "attempts", "count": attempts, "digest": attempt_digest.hexdigest()}
            )
        )
    if not saw_authority:
        raise UnsafeStateError("terminal records omit the authority fact")
    if sealed_charged is None:
        raise UnsafeStateError("terminal records omit the paired ledger fact")
    prefix = hasher.hexdigest()
    semantic = hashlib.sha256()
    semantic.update(prefix.encode("ascii"))
    semantic.update(
        compact_json({"section": "live_ledger", "charged": live_charged})
    )
    return prefix, semantic.hexdigest()


def reconstruct_digests_from_terminal_path(
    path: Path, *, roots: BoundRoots | None = None
) -> tuple[str, str]:
    """Stream a published terminal gzip and reconstruct both authenticated digests."""

    fd = open_regular_file(path.parent, path, roots=roots)
    handle = os.fdopen(os.dup(fd), "rb")
    os.close(fd)
    try:
        with gzip.GzipFile(fileobj=handle, mode="rb") as archive:
            def _lines() -> Iterator[bytes]:
                for raw in archive:
                    yield raw

            return reconstruct_digests_from_terminal_lines(_lines())
    finally:
        handle.close()


def map_exception(exc: BaseException) -> int:
    if isinstance(exc, CapacityBlocked):
        return EXIT_CAPACITY_BLOCKED
    if isinstance(exc, AuthorityError):
        return EXIT_AUTHORITY_INVALID
    if isinstance(exc, UnsafeStateError):
        return EXIT_UNSAFE_STATE
    return EXIT_UNSAFE_STATE
