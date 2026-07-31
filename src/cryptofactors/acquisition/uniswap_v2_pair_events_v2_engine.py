"""DEX-003 / ADR-0015 §9 — bounded v2 acquisition engine (Sr rewrite).

Architecture (designed in, not patched on):

* **HTTP workers** stream every started response into a durable spool and emit a
  ``SpoolDescriptor`` only. They never hold SQLite or ``RawObjectWriter``.
* **One persistence thread** exclusively owns SQLite, the raw catalog, and
  ``RawObjectWriter``. All mutations cross a bounded command queue.
* **Claim-bound terminals** — ``commit_agreed``, ``commit_split``,
  ``release_retry``, ``terminalize``, and ``resolve_winner`` take a ``Claim``
  that carries the lease token. Semantic winner verification runs before lease
  validation so a lost lease can still verify an AGREED/SPLIT winner.
* **Lease-token-keyed workers** — the engine's active-work map is keyed by
  ``lease_token``, not ``domain_id``, so reclaim after expiry cannot confuse
  owners.
* **Chain authentication is a prerequisite state** — ``process_one`` /
  ``run_until_idle`` refuse work until dual mainnet chain identity is durable
  for the plan.
* **0018 contracts** are declared below as unambiguous column/uniqueness
  contracts for Jr's forward migration. This module does **not** create those
  tables and does **not** alter accepted pure foundation contracts in
  ``uniswap_v2_pair_events_v2``.

Out of scope: CLI, live RPC runs, v1 evidence, publication, metadata phase,
factors, LIVE, tests, migration application.
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import random
import sqlite3
import stat
import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable, Iterator, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

import httpx

from cryptofactors.acquisition.uniswap_v2 import (
    UniswapV2IngestionError,
    _canonical_json,
    _hex_bytes,
    _hex_quantity,
    _require,
    block_header_request,
    chain_id_request,
)
from cryptofactors.acquisition.uniswap_v2_pair_events_v2 import (
    DEFAULT_EVENT_PROVIDER_ORGS,
    LOG_IDENTITY_VERSION,
    RECEIPT_SCHEMA_VERSION,
    AcquisitionPlanV2,
    CanonicalHeaderReceiptRecord,
    LeafReceiptRecord,
    PairEventV2Error,
    PlanConfig,
    PlanRecord,
    QueryDomain,
    QueryNode,
    QueryNodeRecord,
    RegistryPoolBirth,
    SplitReason,
    build_acquisition_plan_v2,
    compute_canonical_header_receipt_id,
    make_leaf_receipt_record,
    normalize_and_index_logs,
    normalize_provider_org,
    plan_record_from_config,
    reconcile_log_sets_v2,
    request_for_domain,
    split_node,
    validate_children_partition,
)
from cryptofactors.ingest.raw.catalog import (
    SqliteRawObjectCatalog,
    verify_publication_receipt,
)
from cryptofactors.ingest.raw.models import (
    AcquisitionMetadata,
    PublicationReceipt,
    RawObjectStoreConfig,
)
from cryptofactors.ingest.raw.writer import RawObjectWriter

# ---------------------------------------------------------------------------
# Accepted 0017 table names (existing migration — do not redefine schema here)
# ---------------------------------------------------------------------------

SOURCE_ID: Final[str] = "ethereum_json_rpc_uniswap_v2_pair_events_v2"

PLAN_TABLE: Final[str] = "uniswap_v2_pair_event_v2_plan"
NODE_TABLE: Final[str] = "uniswap_v2_pair_event_v2_query_node"
LEASE_TABLE: Final[str] = "uniswap_v2_pair_event_v2_query_lease"
HEADER_TABLE: Final[str] = "uniswap_v2_pair_event_v2_canonical_header_receipt"
LEAF_TABLE: Final[str] = "uniswap_v2_pair_event_v2_leaf_receipt"
DEP_TABLE: Final[str] = "uniswap_v2_pair_event_v2_leaf_header_dependency"

# ---------------------------------------------------------------------------
# Forward migration 0018 — unambiguous persistence contracts (Jr implements)
# ---------------------------------------------------------------------------
#
# This engine REQUIRES these tables at runtime. Sr does not apply migrations.
# Jr must ship migration 0018 matching these contracts exactly.

CHAIN_IDENTITY_TABLE: Final[str] = "uniswap_v2_pair_event_v2_chain_identity_receipt"
ENGINE_EVENT_TABLE: Final[str] = "uniswap_v2_pair_event_v2_engine_event"
EXECUTION_POLICY_TABLE: Final[str] = "uniswap_v2_pair_event_v2_execution_policy"

CHAIN_IDENTITY_SCHEMA_VERSION: Final[str] = "1"
ENGINE_EVENT_SCHEMA_VERSION: Final[str] = "1"
EXECUTION_POLICY_SCHEMA_VERSION: Final[str] = "1"
SPOOL_DESCRIPTOR_SCHEMA_VERSION: Final[str] = "1"

# ---------------------------------------------------------------------------
# Exact 0018 contracts for one forward migration (Jr implements DDL)
# ---------------------------------------------------------------------------
#
# raw_acquisition pairing key (0018 MUST add if missing):
#   UNIQUE (acquisition_id, raw_object_id)
#   This parent key makes every child composite FK enforce acquisition↔raw pairing.
#
# CHAIN_IDENTITY_TABLE (plan_id NOT NULL on every owning row):
#   PK (chain_identity_receipt_id TEXT) CHECK LIKE 'chain_%'
#   UNIQUE (plan_id)
#   FK plan_id → plan(plan_id) ON DELETE CASCADE ON UPDATE RESTRICT
#   chain_id INTEGER NOT NULL CHECK (= 1)
#   primary_provider_org / secondary_provider_org TEXT NOT NULL CHECK (primary != secondary)
#   primary_raw_object_id / secondary_raw_object_id TEXT NOT NULL CHECK LIKE 'raw_%'
#   primary_acquisition_id / secondary_acquisition_id TEXT NOT NULL CHECK LIKE 'acq_%'
#   MANDATORY composite pairing FKs (independent single-column FKs are NOT sufficient):
#     FK (primary_acquisition_id, primary_raw_object_id)
#       → raw_acquisition(acquisition_id, raw_object_id)
#       ON DELETE RESTRICT ON UPDATE RESTRICT
#     FK (secondary_acquisition_id, secondary_raw_object_id)
#       → raw_acquisition(acquisition_id, raw_object_id)
#       ON DELETE RESTRICT ON UPDATE RESTRICT
#   schema_version TEXT NOT NULL CHECK (= '1'); completed_at TEXT NOT NULL
#
# ENGINE_EVENT_TABLE:
#   PK (event_id TEXT) CHECK LIKE 'evt_%'
#   plan_id TEXT NOT NULL
#   FK plan_id → plan(plan_id) ON DELETE CASCADE ON UPDATE RESTRICT
#   domain_id TEXT NULL — when non-NULL CHECK LIKE 'qd_%'
#     MANDATORY composite FK (plan_id, domain_id) → query_node(plan_id, domain_id)
#       ON DELETE RESTRICT ON UPDATE RESTRICT
#   attempt INTEGER NOT NULL CHECK (>= 0)
#   event_kind TEXT NOT NULL CHECK ∈ ENGINE_EVENT_KINDS
#   failure_class / decision / provider_org / request_json nullable as today
#   primary_raw_object_id / secondary_raw_object_id TEXT NULL
#   primary_acquisition_id / secondary_acquisition_id TEXT NULL
#   NULL parity (both directions) is mandatory:
#     CHECK ((primary_raw_object_id IS NULL) = (primary_acquisition_id IS NULL))
#     CHECK ((secondary_raw_object_id IS NULL) = (secondary_acquisition_id IS NULL))
#   When a primary pair is non-NULL:
#     FK (primary_acquisition_id, primary_raw_object_id)
#       → raw_acquisition(acquisition_id, raw_object_id)
#       ON DELETE RESTRICT ON UPDATE RESTRICT
#   When a secondary pair is non-NULL: same composite FK for secondary side.
#   Independent single-column FKs are forbidden as a substitute for pairing FKs.
#   detail_json TEXT NOT NULL; schema_version TEXT NOT NULL CHECK (= '1'); created_at TEXT NOT NULL
#
# EXECUTION_POLICY_TABLE:
#   PK (policy_id TEXT) CHECK LIKE 'pol_%'
#   plan_id TEXT NOT NULL UNIQUE
#   FK plan_id → plan(plan_id) ON DELETE CASCADE ON UPDATE RESTRICT
#   identity_payload_json TEXT NOT NULL (plan_id + all authority settings incl. timeouts)
#   schema_version TEXT NOT NULL CHECK (= '1'); created_at TEXT NOT NULL
#
# HEADER_TABLE (0018 MUST add if missing on 0017):
#   plan_id TEXT NOT NULL
#   UNIQUE (plan_id, block_number)
#   UNIQUE (plan_id, header_receipt_id)
#   primary/secondary raw+acq all NOT NULL
#   MANDATORY composite pairing FKs for each side:
#     FK (primary_acquisition_id, primary_raw_object_id)
#       → raw_acquisition(acquisition_id, raw_object_id)
#       ON DELETE RESTRICT ON UPDATE RESTRICT
#     FK (secondary_acquisition_id, secondary_raw_object_id) … same
#   FK plan_id → plan ON DELETE CASCADE ON UPDATE RESTRICT
#
# LEAF_TABLE:
#   plan_id TEXT NOT NULL; domain_id TEXT NOT NULL
#   UNIQUE (plan_id, domain_id)
#   UNIQUE (plan_id, leaf_receipt_id)
#   FK (plan_id, domain_id) → query_node ON DELETE RESTRICT ON UPDATE RESTRICT
#   dual logs raw/acq all NOT NULL with composite pairing FKs to
#     raw_acquisition(acquisition_id, raw_object_id) ON DELETE RESTRICT ON UPDATE RESTRICT
#
# DEP_TABLE (same-plan dependency ownership):
#   plan_id TEXT NOT NULL
#   FK (plan_id, leaf_receipt_id) → leaf(plan_id, leaf_receipt_id)
#     ON DELETE CASCADE ON UPDATE RESTRICT
#   FK (plan_id, header_receipt_id) → header(plan_id, header_receipt_id)
#     ON DELETE RESTRICT ON UPDATE RESTRICT
#   Requires parent composite UNIQUE (plan_id, leaf_receipt_id) and
#   (plan_id, header_receipt_id).
#
# TERMINAL_RECEIPT_TABLE (claim-bound durable terminal winner identity):
#   PK (terminal_receipt_id TEXT) CHECK LIKE 'term_%'
#   plan_id TEXT NOT NULL; domain_id TEXT NOT NULL
#   UNIQUE (plan_id, domain_id)  — one terminal winner per node
#   FK (plan_id, domain_id) → query_node(plan_id, domain_id)
#     ON DELETE RESTRICT ON UPDATE RESTRICT
#   terminal_mode TEXT NOT NULL CHECK (terminal_mode IN (
#     'lease_expired', 'unsplittable_singleton', 'http_429', 'explicit_range_limit',
#     'body_size_pressure', 'result_size_pressure', 'provider_disagreement',
#     'transport', 'authentication', 'http_status', 'malformed_json', 'rpc_error',
#     'boundary_mismatch', 'header_conflict', 'persistence', 'internal'
#   ))
#   attempt INTEGER NOT NULL CHECK (attempt >= 0)
#   schema_version TEXT NOT NULL CHECK (= '1')
#   completed_at TEXT NOT NULL
#   terminal_receipt_id is content-addressed over
#     {plan_id, domain_id, terminal_mode, attempt, schema_version}.
#   PENDING + attempt >= max_attempts alone is NOT terminal identity.
#   Engine always writes attempt = configured max_attempts for terminal receipts.

TERMINAL_RECEIPT_TABLE: Final[str] = "uniswap_v2_pair_event_v2_terminal_receipt"
TERMINAL_RECEIPT_SCHEMA_VERSION: Final[str] = "1"
TERMINAL_MODE_LEASE_EXPIRED: Final[str] = "lease_expired"
TERMINAL_MODE_UNSPLITTABLE: Final[str] = "unsplittable_singleton"
# Exact durable terminal-mode domain (16 literals). Runtime and SQL CHECK must match.
TERMINAL_MODES: Final[frozenset[str]] = frozenset(
    {
        "lease_expired",
        "unsplittable_singleton",
        "http_429",
        "explicit_range_limit",
        "body_size_pressure",
        "result_size_pressure",
        "provider_disagreement",
        "transport",
        "authentication",
        "http_status",
        "malformed_json",
        "rpc_error",
        "boundary_mismatch",
        "header_conflict",
        "persistence",
        "internal",
    }
)
TERMINAL_RECEIPT_RECORD_COLUMNS: Final[tuple[str, ...]] = (
    "terminal_receipt_id",
    "plan_id",
    "domain_id",
    "terminal_mode",
    "attempt",
    "schema_version",
    "completed_at",
)
TERMINAL_RECEIPT_UNIQUENESS: Final[tuple[str, ...]] = ("plan_id", "domain_id")

# Insert column order (positional). Jr CREATE TABLE must include every column.
CHAIN_IDENTITY_RECORD_COLUMNS: Final[tuple[str, ...]] = (
    "chain_identity_receipt_id",
    "plan_id",
    "chain_id",
    "primary_provider_org",
    "secondary_provider_org",
    "primary_raw_object_id",
    "secondary_raw_object_id",
    "primary_acquisition_id",
    "secondary_acquisition_id",
    "schema_version",
    "completed_at",
)
ENGINE_EVENT_RECORD_COLUMNS: Final[tuple[str, ...]] = (
    "event_id",
    "schema_version",
    "plan_id",
    "domain_id",
    "attempt",
    "event_kind",
    "failure_class",
    "decision",
    "provider_org",
    "request_json",
    "primary_raw_object_id",
    "secondary_raw_object_id",
    "primary_acquisition_id",
    "secondary_acquisition_id",
    "detail_json",
    "created_at",
)
EXECUTION_POLICY_RECORD_COLUMNS: Final[tuple[str, ...]] = (
    "policy_id",
    "plan_id",
    "identity_payload_json",
    "schema_version",
    "created_at",
)

# Uniqueness contracts Jr must enforce (application also enforces).
CHAIN_IDENTITY_UNIQUENESS: Final[tuple[str, ...]] = ("plan_id",)
ENGINE_EVENT_UNIQUENESS: Final[tuple[str, ...]] = ("event_id",)
EXECUTION_POLICY_UNIQUENESS: Final[tuple[str, ...]] = ("plan_id",)
HEADER_UNIQUENESS: Final[tuple[str, ...]] = ("plan_id", "block_number")
LEAF_UNIQUENESS: Final[tuple[str, ...]] = ("plan_id", "domain_id")

# Deterministic mixed-failure routing precedence (highest first).
FAILURE_ROUTE_PRECEDENCE: Final[tuple[str, ...]] = (
    "http_429",
    "authentication",
    "transport",
    "persistence",
    "boundary_mismatch",
    "malformed_json",
    "http_status",
    "rpc_error",
    "header_conflict",
    "provider_disagreement",
    "explicit_range_limit",
    "body_size_pressure",
    "result_size_pressure",
    "internal",
)

ENGINE_EVENT_KINDS: Final[frozenset[str]] = frozenset(
    {
        "failure",
        "lease_expiry",
        "provider_disagreement",
        "retry_decision",
        "split_decision",
        "terminal_blocker",
    }
)

# ---------------------------------------------------------------------------
# Runtime bounds
# ---------------------------------------------------------------------------

DEFAULT_LEASE_TTL_SECONDS: Final[float] = 120.0
DEFAULT_MAX_ATTEMPTS: Final[int] = 3
DEFAULT_MAX_LOG_COUNT: Final[int] = 8_000
DEFAULT_MAX_BODY_BYTES: Final[int] = 8_000_000
DEFAULT_SPOOL_CHUNK_BYTES: Final[int] = 64 * 1024
DEFAULT_RPS: Final[float] = 8.0
DEFAULT_MAX_IN_FLIGHT: Final[int] = 4
DEFAULT_MAX_NODE_IN_FLIGHT: Final[int] = 4
DEFAULT_PERSISTENCE_QUEUE_SIZE: Final[int] = 32
DEFAULT_BACKOFF_BASE_SECONDS: Final[float] = 1.0
DEFAULT_BACKOFF_MAX_SECONDS: Final[float] = 60.0
DEFAULT_HEADER_CACHE_SIZE: Final[int] = 512
DEFAULT_MAX_SPOOL_FILES: Final[int] = 64
DEFAULT_RESPONSE_DRAIN_DEADLINE_SECONDS: Final[float] = 120.0

_RANGE_LIMIT_MARKERS: Final[tuple[str, ...]] = (
    "block range limit",
    "block range is too wide",
    "maximum block range",
    "max block range",
    "limited to a range of",
    "range exceeds",
)
_RESULT_PRESSURE_MARKERS: Final[tuple[str, ...]] = (
    "response size limit",
    "result limit",
    "too many results",
    "more than 10000 results",
    "query returned more than",
    "log response size exceeded",
)
# Exact-key secrets (substring match on "token" falsely blocked lease fingerprints).
_SENSITIVE_EXACT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "lease_token",
        "private_key",
        "rpc_url",
        "endpoint",
        "url",
        "worker_id",
    }
)
_SENSITIVE_SUBSTRING_MARKERS: Final[tuple[str, ...]] = (
    "api_key",
    "apikey",
    "password",
    "secret",
    "private_key",
    "rpc_url",
)


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _identity(prefix: str, payload: Mapping[str, Any]) -> str:
    return prefix + hashlib.sha256(
        _canonical_json(dict(payload)).encode("utf-8")
    ).hexdigest()


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise PairEventV2Error(f"duplicate JSON key {key!r}")
        seen.add(key)
        out[key] = value
    return out


def _contains_sensitive_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_l = str(key).lower()
            if key_l in _SENSITIVE_EXACT_KEYS:
                return True
            if any(marker in key_l for marker in _SENSITIVE_SUBSTRING_MARKERS):
                return True
            if _contains_sensitive_key(item):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def _lease_fingerprint(lease_token: str) -> str:
    """One-way non-secret identity for durable event details (never the raw token)."""
    return hashlib.sha256(lease_token.encode("utf-8")).hexdigest()


def _dir_fd(path: Path) -> int:
    """Open a directory for trusted relative opens (no follow on the directory itself)."""
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return os.open(path, flags)


def _openat_nofollow_read(dir_fd: int, name: str) -> int:
    """Relative open of a final component under a trusted directory descriptor."""
    if Path(name).name != name or name in ("", ".", ".."):
        raise PairEventV2Error("relative open name is not a single path component")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(name, flags, dir_fd=dir_fd)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise PairEventV2Error("evidence path is not a regular file")
    except Exception:
        os.close(fd)
        raise
    return fd


def _open_under_root(root: Path, relative: str) -> tuple[int, Path]:
    """Open ``root/relative`` via successive trusted dirfds + final O_NOFOLLOW.

    Returns (fd, lexical_path). Caller owns fd. Intermediate components are opened
    as directories with O_NOFOLLOW where available; the leaf is O_NOFOLLOW regular.
    """
    if relative.startswith("/") or Path(relative).is_absolute():
        raise PairEventV2Error("relative evidence path must not be absolute")
    parts = [p for p in Path(relative).parts if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        raise PairEventV2Error("evidence path escapes store root")
    dir_fd = _dir_fd(root)
    owned: list[int] = [dir_fd]
    try:
        for component in parts[:-1]:
            flags = os.O_RDONLY
            if hasattr(os, "O_DIRECTORY"):
                flags |= os.O_DIRECTORY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            next_fd = os.open(component, flags, dir_fd=dir_fd)
            owned.append(next_fd)
            dir_fd = next_fd
        leaf_fd = _openat_nofollow_read(dir_fd, parts[-1])
    except Exception:
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                pass
        raise
    for fd in reversed(owned):
        try:
            os.close(fd)
        except OSError:
            pass
    return leaf_fd, root.joinpath(*parts)


def _read_fd_bounded(
    fd: int,
    *,
    max_bytes: int,
    expected_size: int | None = None,
    pulse: Callable[[], None] | None = None,
) -> tuple[bytes, str, int]:
    """Hash and read from an already-opened fd (same identity for size/hash/parse)."""
    st = os.fstat(fd)
    size = int(st.st_size)
    if size > max_bytes:
        raise PairEventV2Error("file exceeds engine byte bound")
    if expected_size is not None and size != expected_size:
        raise PairEventV2Error("file size disagrees with expected evidence size")
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        if pulse is not None:
            pulse()
        piece = os.read(fd, min(64 * 1024, remaining))
        if not piece:
            break
        digest.update(piece)
        chunks.append(piece)
        remaining -= len(piece)
    body = b"".join(chunks)
    if len(body) != size:
        raise PairEventV2Error("short read on evidence file")
    return body, digest.hexdigest(), size


def _write_durable_json_under(root: Path, name: str, payload: Mapping[str, Any]) -> Path:
    """Atomically write a JSON journal as a single component under ``root``."""
    if _contains_sensitive_key(payload):
        raise PairEventV2Error("spool journal payload contains sensitive data")
    if Path(name).name != name:
        raise PairEventV2Error("journal name must be a single path component")
    text = _canonical_json(dict(payload))
    tmp_name = f".{name}.tmp-{uuid.uuid4().hex}"
    dir_fd = _dir_fd(root)
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(tmp_name, flags, 0o600, dir_fd=dir_fd)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            try:
                os.unlink(tmp_name, dir_fd=dir_fd)
            except OSError:
                pass
            raise
        os.rename(tmp_name, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    return root / name


def _load_authenticated_json(
    evidence: AuthenticatedEvidence,
    *,
    max_bytes: int,
    raw_root: Path,
    pulse: Callable[[], None] | None = None,
) -> Mapping[str, Any]:
    """Parse authenticated bytes via trusted raw-root traversal (one open identity).

    Always re-opens through configured ``raw_root`` + digest-canonical storage_uri.
    Never trusts ``storage_path.parent`` as a second root.
    """
    if evidence.byte_size > max_bytes:
        raise PairEventV2Error("authenticated body exceeds engine byte bound")
    # Verify digest-derived canonical storage URI before open.
    expected_uri = (
        f"raw/sha256/{evidence.sha256[0:2]}/{evidence.sha256[2:4]}/{evidence.sha256}"
    )
    if evidence.storage_uri != expected_uri:
        raise PairEventV2Error(
            "storage_uri is not the digest-derived raw/sha256 canonical path"
        )
    if evidence.raw_object_id != "raw_" + evidence.sha256:
        raise PairEventV2Error("raw_object_id is not canonical for sha256")
    fd, _path = _open_under_root(raw_root.resolve(), evidence.storage_uri)
    try:
        body, digest, size = _read_fd_bounded(
            fd,
            max_bytes=max_bytes,
            expected_size=evidence.byte_size,
            pulse=pulse,
        )
    finally:
        os.close(fd)
    if size != evidence.byte_size or digest != evidence.sha256:
        raise PairEventV2Error("authenticated evidence sha256/size mismatch")
    try:
        payload = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PairEventV2Error("authenticated body is not JSON") from exc
    if not isinstance(payload, Mapping):
        raise PairEventV2Error("authenticated body must be a JSON object")
    return payload


def _load_authenticated_rpc(
    evidence: AuthenticatedEvidence,
    request: Mapping[str, Any],
    *,
    max_bytes: int,
    raw_root: Path,
    pulse: Callable[[], None] | None = None,
) -> Mapping[str, Any]:
    payload = _load_authenticated_json(
        evidence, max_bytes=max_bytes, raw_root=raw_root, pulse=pulse
    )
    if payload.get("jsonrpc") != request.get("jsonrpc"):
        raise _JsonRpcBoundaryError("JSON-RPC version boundary mismatch")
    if payload.get("id") != request.get("id"):
        raise _JsonRpcBoundaryError("JSON-RPC correlation id mismatch")
    return payload


# ---------------------------------------------------------------------------
# Failure taxonomy (routing-significant; never collapse transport → size)
# ---------------------------------------------------------------------------


class FailureClass(StrEnum):
    HTTP_429 = "http_429"
    EXPLICIT_RANGE_LIMIT = "explicit_range_limit"
    BODY_SIZE_PRESSURE = "body_size_pressure"
    RESULT_SIZE_PRESSURE = "result_size_pressure"
    PROVIDER_DISAGREEMENT = "provider_disagreement"
    TRANSPORT = "transport"
    AUTHENTICATION = "authentication"
    HTTP_STATUS = "http_status"
    MALFORMED_JSON = "malformed_json"
    RPC_ERROR = "rpc_error"
    BOUNDARY_MISMATCH = "boundary_mismatch"
    HEADER_CONFLICT = "header_conflict"
    PERSISTENCE = "persistence"
    INTERNAL = "internal"


class EnginePhase(StrEnum):
    """Lifecycle: chain authentication is a hard prerequisite for work."""

    CONSTRUCTED = "constructed"
    PLAN_INITIALIZED = "plan_initialized"
    CHAIN_AUTHENTICATED = "chain_authenticated"


class _LeaseLostError(PairEventV2Error):
    """Caller no longer owns an unexpired IN_FLIGHT lease for this claim."""


class _JsonRpcBoundaryError(PairEventV2Error):
    """JSON-RPC id/version boundary mismatch (not size pressure)."""


# ---------------------------------------------------------------------------
# Spool / evidence / claim (first-class)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SpoolDescriptor:
    """Bounded durable response evidence. Workers produce only this type."""

    provider_org: str
    request_json: str
    acquired_at: datetime
    status_code: int | None
    spool_path: Path | None
    response_started: bool
    response_bytes: int
    retained_bytes: int
    truncated: bool
    error_kind: str | None
    error_detail: str | None
    acquisition_id: str | None = None
    journal_path: Path | None = None
    reservation_id: str | None = None
    schema_version: str = SPOOL_DESCRIPTOR_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_org", normalize_provider_org(self.provider_org))
        if self.schema_version != SPOOL_DESCRIPTOR_SCHEMA_VERSION:
            raise PairEventV2Error("spool descriptor schema version mismatch")
        try:
            request = json.loads(self.request_json)
        except json.JSONDecodeError as exc:
            raise PairEventV2Error("spool request is not JSON") from exc
        if (
            not isinstance(request, Mapping)
            or request.get("jsonrpc") != "2.0"
            or not isinstance(request.get("method"), str)
            or not isinstance(request.get("params"), list)
            or _contains_sensitive_key(request)
            or self.request_json != _canonical_json(dict(request))
        ):
            raise PairEventV2Error("spool request is not a canonical JSON-RPC payload")
        if self.acquired_at.tzinfo is None:
            raise PairEventV2Error("spool acquired_at must be timezone-aware")
        if self.reservation_id is not None and self.journal_path is None:
            raise PairEventV2Error("a spool reservation requires a durable journal")
        if self.acquisition_id is not None and not str(self.acquisition_id).startswith(
            "acq_"
        ):
            raise PairEventV2Error("spool acquisition_id must use the acq_ namespace")
        if self.response_bytes < 0 or self.retained_bytes < 0:
            raise PairEventV2Error("spool byte counts must be non-negative")
        if self.retained_bytes > self.response_bytes:
            raise PairEventV2Error("retained spool bytes exceed response bytes")
        if self.spool_path is None and self.retained_bytes != 0:
            raise PairEventV2Error("missing spool path with retained bytes")


@dataclass(frozen=True, slots=True)
class AuthenticatedEvidence:
    """Re-authenticated raw/acquisition evidence safe for bounded JSON parsing.

    ``storage_uri`` is the digest-canonical relative path under the configured
    raw root (``raw/sha256/ab/cd/<sha>``). Replay always re-opens via that root
    + URI; ``storage_path`` is diagnostic only and must not be used as a second root.
    """

    provider_org: str
    request_json: str
    raw_object_id: str
    acquisition_id: str
    sha256: str
    byte_size: int
    storage_uri: str
    storage_path: Path


@dataclass(frozen=True, slots=True)
class PersistedEnvelope:
    descriptor: SpoolDescriptor
    evidence: AuthenticatedEvidence | None
    acquisition_id: str | None
    writer_latency_seconds: float


@dataclass(frozen=True, slots=True)
class Claim:
    """Lease-token-keyed ownership of one IN_FLIGHT node.

    Terminal persistence operations are claim-bound: they accept this object and
    either (a) validate the lease token for a writer path, or (b) verify the
    semantic winner after the lease is gone.
    """

    plan_id: str
    domain_id: str
    worker_id: str
    lease_token: str
    attempt: int
    node: QueryNode

    def __post_init__(self) -> None:
        if not self.lease_token:
            raise PairEventV2Error("claim lease_token is required")
        if self.attempt < 0:
            raise PairEventV2Error("claim attempt must be non-negative")
        if self.node.plan_id != self.plan_id or self.node.domain_id != self.domain_id:
            raise PairEventV2Error("claim node identity mismatch")
        if not self.worker_id.strip():
            raise PairEventV2Error("claim worker_id is required")


@dataclass(frozen=True, slots=True)
class ChainIdentityReceipt:
    chain_identity_receipt_id: str
    plan_id: str
    chain_id: int
    primary_provider_org: str
    secondary_provider_org: str
    primary_raw_object_id: str
    secondary_raw_object_id: str
    primary_acquisition_id: str
    secondary_acquisition_id: str
    schema_version: str = CHAIN_IDENTITY_SCHEMA_VERSION
    completed_at: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != CHAIN_IDENTITY_SCHEMA_VERSION:
            raise PairEventV2Error("chain identity schema version mismatch")
        primary = normalize_provider_org(self.primary_provider_org)
        secondary = normalize_provider_org(self.secondary_provider_org)
        if primary == secondary:
            raise PairEventV2Error("chain identity providers must be independent")
        if self.chain_id != 1:
            raise PairEventV2Error("chain identity receipt must authenticate mainnet")
        expected = compute_chain_identity_receipt_id(
            plan_id=self.plan_id,
            chain_id=self.chain_id,
            primary_provider_org=primary,
            secondary_provider_org=secondary,
            primary_raw_object_id=self.primary_raw_object_id,
            secondary_raw_object_id=self.secondary_raw_object_id,
            primary_acquisition_id=self.primary_acquisition_id,
            secondary_acquisition_id=self.secondary_acquisition_id,
        )
        if self.chain_identity_receipt_id != expected:
            raise PairEventV2Error("chain identity receipt id mismatch")
        object.__setattr__(self, "primary_provider_org", primary)
        object.__setattr__(self, "secondary_provider_org", secondary)


def compute_terminal_receipt_id(
    *,
    plan_id: str,
    domain_id: str,
    terminal_mode: str,
    attempt: int,
) -> str:
    payload = {
        "attempt": int(attempt),
        "domain_id": str(domain_id),
        "plan_id": str(plan_id),
        "schema_version": TERMINAL_RECEIPT_SCHEMA_VERSION,
        "terminal_mode": str(terminal_mode),
    }
    return _identity("term_", payload)


def compute_chain_identity_receipt_id(
    *,
    plan_id: str,
    chain_id: int,
    primary_provider_org: str,
    secondary_provider_org: str,
    primary_raw_object_id: str,
    secondary_raw_object_id: str,
    primary_acquisition_id: str,
    secondary_acquisition_id: str,
) -> str:
    payload = {
        "chain_id": int(chain_id),
        "plan_id": str(plan_id),
        "primary_acquisition_id": str(primary_acquisition_id),
        "primary_provider_org": normalize_provider_org(primary_provider_org),
        "primary_raw_object_id": str(primary_raw_object_id),
        "schema_version": CHAIN_IDENTITY_SCHEMA_VERSION,
        "secondary_acquisition_id": str(secondary_acquisition_id),
        "secondary_provider_org": normalize_provider_org(secondary_provider_org),
        "secondary_raw_object_id": str(secondary_raw_object_id),
    }
    return _identity("chain_", payload)


@dataclass(frozen=True, slots=True)
class EngineEventRecord:
    event_id: str
    plan_id: str
    domain_id: str | None
    attempt: int
    event_kind: str
    failure_class: str | None
    decision: str | None
    provider_org: str | None
    request_json: str | None
    primary_raw_object_id: str | None
    secondary_raw_object_id: str | None
    primary_acquisition_id: str | None
    secondary_acquisition_id: str | None
    detail_json: str
    created_at: str
    schema_version: str = ENGINE_EVENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ENGINE_EVENT_SCHEMA_VERSION:
            raise PairEventV2Error("engine event schema version mismatch")
        if self.event_kind not in ENGINE_EVENT_KINDS:
            raise PairEventV2Error("unsupported engine event kind")
        if self.attempt < 0:
            raise PairEventV2Error("engine event attempt must be non-negative")
        if self.failure_class is not None and self.failure_class not in {
            item.value for item in FailureClass
        }:
            raise PairEventV2Error("unsupported engine failure class")
        detail = json.loads(self.detail_json)
        if not isinstance(detail, Mapping) or _contains_sensitive_key(detail):
            raise PairEventV2Error("engine event detail is invalid or sensitive")
        request: Mapping[str, Any] | None = None
        if self.request_json is not None:
            parsed = json.loads(self.request_json)
            if (
                not isinstance(parsed, Mapping)
                or parsed.get("jsonrpc") != "2.0"
                or not isinstance(parsed.get("method"), str)
                or not isinstance(parsed.get("params"), list)
                or _contains_sensitive_key(parsed)
            ):
                raise PairEventV2Error("engine event request is not a JSON-RPC payload")
            request = parsed
        org = (
            normalize_provider_org(self.provider_org)
            if self.provider_org is not None
            else None
        )
        identity_payload = {
            "attempt": int(self.attempt),
            "decision": self.decision,
            "detail": detail,
            "domain_id": self.domain_id,
            "event_kind": self.event_kind,
            "failure_class": self.failure_class,
            "plan_id": self.plan_id,
            "primary_acquisition_id": self.primary_acquisition_id,
            "primary_raw_object_id": self.primary_raw_object_id,
            "provider_org": org,
            "request": request,
            "schema_version": self.schema_version,
            "secondary_acquisition_id": self.secondary_acquisition_id,
            "secondary_raw_object_id": self.secondary_raw_object_id,
        }
        if self.event_id != _identity("evt_", identity_payload):
            raise PairEventV2Error("engine event id does not match its payload")
        object.__setattr__(self, "provider_org", org)


def make_engine_event_record(
    *,
    plan_id: str,
    domain_id: str | None,
    attempt: int,
    event_kind: str,
    failure_class: FailureClass | str | None = None,
    decision: str | None = None,
    provider_org: str | None = None,
    request: Mapping[str, Any] | None = None,
    primary_raw_object_id: str | None = None,
    secondary_raw_object_id: str | None = None,
    primary_acquisition_id: str | None = None,
    secondary_acquisition_id: str | None = None,
    detail: Mapping[str, Any] | None = None,
    created_at: str | None = None,
) -> EngineEventRecord:
    org = normalize_provider_org(provider_org) if provider_org is not None else None
    failure = str(failure_class) if failure_class is not None else None
    request_json = _canonical_json(dict(request)) if request is not None else None
    detail_json = _canonical_json(dict(detail or {}))
    identity_payload = {
        "attempt": int(attempt),
        "decision": decision,
        "detail": json.loads(detail_json),
        "domain_id": domain_id,
        "event_kind": event_kind,
        "failure_class": failure,
        "plan_id": plan_id,
        "primary_acquisition_id": primary_acquisition_id,
        "primary_raw_object_id": primary_raw_object_id,
        "provider_org": org,
        "request": json.loads(request_json) if request_json is not None else None,
        "schema_version": ENGINE_EVENT_SCHEMA_VERSION,
        "secondary_acquisition_id": secondary_acquisition_id,
        "secondary_raw_object_id": secondary_raw_object_id,
    }
    return EngineEventRecord(
        event_id=_identity("evt_", identity_payload),
        plan_id=plan_id,
        domain_id=domain_id,
        attempt=int(attempt),
        event_kind=event_kind,
        failure_class=failure,
        decision=decision,
        provider_org=org,
        request_json=request_json,
        primary_raw_object_id=primary_raw_object_id,
        secondary_raw_object_id=secondary_raw_object_id,
        primary_acquisition_id=primary_acquisition_id,
        secondary_acquisition_id=secondary_acquisition_id,
        detail_json=detail_json,
        created_at=created_at or _now(),
    )


# ---------------------------------------------------------------------------
# Config / metrics
# ---------------------------------------------------------------------------


@dataclass
class EngineMetrics:
    claims: int = 0
    agreed: int = 0
    splits: int = 0
    retries: int = 0
    terminal_blockers: int = 0
    lease_expiries: int = 0
    http_429: int = 0
    transport_errors: int = 0
    disagreements: int = 0
    headers_cached: int = 0
    headers_fetched: int = 0
    response_bytes: int = 0
    retained_spool_bytes: int = 0
    truncated_responses: int = 0
    writer_operations: int = 0
    writer_latency_seconds: float = 0.0
    writer_latency_max_seconds: float = 0.0
    persistence_queue_high_water: int = 0
    last_error: str | None = None

    def snapshot(self) -> EngineMetrics:
        return replace(self)


@dataclass
class EngineConfig:
    """Runtime-only endpoints + bounds. URLs never enter plan identity."""

    receipt_db_path: Path
    raw_root: Path
    spool_dir: Path
    primary_rpc_url: str
    secondary_rpc_url: str
    worker_id: str
    plan_config: PlanConfig = field(default_factory=PlanConfig)
    primary_org: str = DEFAULT_EVENT_PROVIDER_ORGS[0]
    secondary_org: str = DEFAULT_EVENT_PROVIDER_ORGS[1]
    lease_ttl_seconds: float = DEFAULT_LEASE_TTL_SECONDS
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    max_log_count: int = DEFAULT_MAX_LOG_COUNT
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
    spool_chunk_bytes: int = DEFAULT_SPOOL_CHUNK_BYTES
    persistence_queue_size: int = DEFAULT_PERSISTENCE_QUEUE_SIZE
    requests_per_second: float = DEFAULT_RPS
    max_in_flight_per_provider: int = DEFAULT_MAX_IN_FLIGHT
    max_nodes_in_flight: int = DEFAULT_MAX_NODE_IN_FLIGHT
    http_timeout_seconds: float = 60.0
    backoff_base_seconds: float = DEFAULT_BACKOFF_BASE_SECONDS
    backoff_max_seconds: float = DEFAULT_BACKOFF_MAX_SECONDS
    header_cache_size: int = DEFAULT_HEADER_CACHE_SIZE
    max_spool_files: int = DEFAULT_MAX_SPOOL_FILES
    response_drain_deadline_seconds: float = DEFAULT_RESPONSE_DRAIN_DEADLINE_SECONDS
    command_offer_timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        self.receipt_db_path = Path(self.receipt_db_path)
        self.raw_root = Path(self.raw_root)
        self.spool_dir = Path(self.spool_dir)
        if not self.primary_rpc_url or not self.secondary_rpc_url:
            raise PairEventV2Error("primary and secondary RPC URLs are required")
        if self.primary_rpc_url.rstrip("/") == self.secondary_rpc_url.rstrip("/"):
            raise PairEventV2Error("primary and secondary RPC URLs must be distinct")
        self.primary_org = normalize_provider_org(self.primary_org)
        self.secondary_org = normalize_provider_org(self.secondary_org)
        if self.primary_org == self.secondary_org:
            raise PairEventV2Error("provider organizations must be distinct")
        if (self.primary_org, self.secondary_org) != self.plan_config.event_provider_orgs:
            raise PairEventV2Error("runtime provider orgs must match plan identity")
        positive = {
            "lease_ttl_seconds": self.lease_ttl_seconds,
            "max_attempts": self.max_attempts,
            "max_log_count": self.max_log_count,
            "max_body_bytes": self.max_body_bytes,
            "spool_chunk_bytes": self.spool_chunk_bytes,
            "persistence_queue_size": self.persistence_queue_size,
            "requests_per_second": self.requests_per_second,
            "max_in_flight_per_provider": self.max_in_flight_per_provider,
            "max_nodes_in_flight": self.max_nodes_in_flight,
            "http_timeout_seconds": self.http_timeout_seconds,
            "backoff_base_seconds": self.backoff_base_seconds,
            "backoff_max_seconds": self.backoff_max_seconds,
            "header_cache_size": self.header_cache_size,
            "max_spool_files": self.max_spool_files,
            "response_drain_deadline_seconds": self.response_drain_deadline_seconds,
            "command_offer_timeout_seconds": self.command_offer_timeout_seconds,
        }
        if any(value <= 0 for value in positive.values()):
            raise PairEventV2Error("all engine bounds and timeouts must be positive")
        if self.backoff_base_seconds > self.backoff_max_seconds:
            raise PairEventV2Error("backoff base exceeds backoff maximum")
        if self.max_spool_files < self.max_nodes_in_flight * 2:
            raise PairEventV2Error(
                "max_spool_files must reserve both provider spools for every active node"
            )
        if not self.worker_id.strip():
            raise PairEventV2Error("worker_id is required")


# ---------------------------------------------------------------------------
# Provider limits
# ---------------------------------------------------------------------------


class _TokenBucket:
    def __init__(self, *, rate: float, capacity: float) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self._capacity,
                    self._tokens + (now - self._updated) * self._rate,
                )
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                delay = (1.0 - self._tokens) / self._rate
            time.sleep(delay)


class _AdaptiveLimiter:
    """Provider-global in-flight cap: contracts on 429, recovers on success."""

    def __init__(self, maximum: int) -> None:
        self._maximum = maximum
        self._limit = maximum
        self._active = 0
        self._successes = 0
        self._condition = threading.Condition()

    @property
    def limit(self) -> int:
        with self._condition:
            return self._limit

    def acquire(self) -> None:
        with self._condition:
            self._condition.wait_for(lambda: self._active < self._limit)
            self._active += 1

    def release(self) -> None:
        with self._condition:
            self._active -= 1
            self._condition.notify_all()

    def on_429(self) -> None:
        with self._condition:
            self._limit = max(1, self._limit // 2)
            self._successes = 0
            self._condition.notify_all()

    def on_success(self) -> None:
        with self._condition:
            self._successes += 1
            if self._limit < self._maximum and self._successes >= self._limit * 8:
                self._limit += 1
                self._successes = 0
                self._condition.notify_all()


# ---------------------------------------------------------------------------
# Network worker (HTTP → spool only)
# ---------------------------------------------------------------------------


class NetworkWorker:
    """Streams one JSON-RPC response to a durable spool. No SQLite."""

    def __init__(
        self,
        *,
        client: httpx.Client,
        rpc_url: str,
        provider_org: str,
        bucket: _TokenBucket,
        limiter: _AdaptiveLimiter,
        spool_dir: Path,
        spool_capacity: threading.BoundedSemaphore,
        max_body_bytes: int,
        chunk_bytes: int,
        response_drain_deadline_seconds: float,
    ) -> None:
        self._client = client
        self._url = rpc_url
        self._org = normalize_provider_org(provider_org)
        self._bucket = bucket
        self._limiter = limiter
        self._spool_dir = spool_dir
        self._spool_capacity = spool_capacity
        self._max_body_bytes = max_body_bytes
        self._chunk_bytes = chunk_bytes
        self._response_drain_deadline_seconds = response_drain_deadline_seconds

    def fetch(self, request: Mapping[str, Any]) -> SpoolDescriptor:
        request_json = _canonical_json(dict(request))
        acquired_at = datetime.now(UTC)
        acquisition_id = f"acq_{uuid.uuid4().hex}"
        reservation_id = uuid.uuid4().hex
        status_code: int | None = None
        response_started = False
        response_bytes = 0
        retained_bytes = 0
        truncated = False
        spool_path: Path | None = None
        journal_path: Path | None = None
        handle: Any = None
        error_kind: str | None = None
        error_detail: str | None = None

        self._spool_capacity.acquire()
        spool_name = f"response-{uuid.uuid4().hex}.spool"
        journal_name = f"{spool_name}.journal.json"
        try:
            self._spool_dir.mkdir(parents=True, exist_ok=True)
            if self._spool_dir.is_symlink():
                raise OSError("spool directory is a symlink")
            spool_path = self._spool_dir / spool_name
            # Durably mark the reservation *before* any network bytes can arrive.
            journal_path = _write_durable_json_under(
                self._spool_dir,
                journal_name,
                {
                    "acquired_at": acquired_at.isoformat(),
                    "acquisition_id": acquisition_id,
                    "complete": False,
                    "error_detail": None,
                    "error_kind": None,
                    "provider_org": self._org,
                    "request": json.loads(request_json),
                    "reservation_id": reservation_id,
                    "response_bytes": 0,
                    "response_started": True,
                    "retained_bytes": 0,
                    "schema_version": SPOOL_DESCRIPTOR_SCHEMA_VERSION,
                    "spool_name": spool_name,
                    "status_code": None,
                    "truncated": False,
                },
            )
            response_started = True
            dir_fd = _dir_fd(self._spool_dir)
            try:
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                if hasattr(os, "O_NOFOLLOW"):
                    flags |= os.O_NOFOLLOW
                spool_fd = os.open(spool_name, flags, 0o600, dir_fd=dir_fd)
            finally:
                os.close(dir_fd)
            handle = os.fdopen(spool_fd, "wb")
        except Exception as exc:
            if handle is not None:
                handle.close()
            if spool_path is not None:
                spool_path.unlink(missing_ok=True)
            if journal_path is not None:
                journal_path.unlink(missing_ok=True)
            self._spool_capacity.release()
            return SpoolDescriptor(
                provider_org=self._org,
                request_json=request_json,
                acquired_at=acquired_at,
                status_code=None,
                spool_path=None,
                response_started=response_started,
                response_bytes=0,
                retained_bytes=0,
                truncated=False,
                error_kind="spool_io",
                error_detail=type(exc).__name__,
            )

        def journal(*, complete: bool = False) -> None:
            if journal_path is None or spool_path is None:
                return
            _write_durable_json_under(
                self._spool_dir,
                journal_name,
                {
                    "acquired_at": acquired_at.isoformat(),
                    "acquisition_id": acquisition_id,
                    "complete": complete,
                    "error_detail": error_detail,
                    "error_kind": error_kind,
                    "provider_org": self._org,
                    "request": json.loads(request_json),
                    "reservation_id": reservation_id,
                    "response_bytes": response_bytes,
                    "response_started": True,
                    "retained_bytes": retained_bytes,
                    "schema_version": SPOOL_DESCRIPTOR_SCHEMA_VERSION,
                    "spool_name": spool_name,
                    "status_code": status_code,
                    "truncated": truncated,
                },
            )

        self._bucket.acquire()
        self._limiter.acquire()
        drain_started = time.monotonic()
        try:
            try:
                with self._client.stream(
                    "POST",
                    self._url,
                    content=request_json,
                    headers={"content-type": "application/json"},
                ) as response:
                    acquired_at = datetime.now(UTC)
                    status_code = response.status_code
                    try:
                        journal()
                    except Exception as exc:
                        error_kind = "spool_io"
                        error_detail = type(exc).__name__
                    try:
                        # Always drain the full HTTP body. After the deadline we stop
                        # retaining bytes but continue reading so the response is not
                        # abandoned mid-stream (ADR-0015 started-response rule).
                        past_deadline = False
                        for chunk in response.iter_bytes(chunk_size=self._chunk_bytes):
                            response_bytes += len(chunk)
                            if (
                                not past_deadline
                                and time.monotonic() - drain_started
                                >= self._response_drain_deadline_seconds
                            ):
                                past_deadline = True
                                error_kind = "transport"
                                error_detail = "response_drain_deadline"
                                # Close the retain handle; keep reading to drain.
                                if handle is not None:
                                    try:
                                        handle.flush()
                                        os.fsync(handle.fileno())
                                        handle.close()
                                    except OSError as exc:
                                        error_kind = "spool_io"
                                        error_detail = type(exc).__name__
                                    handle = None
                            if past_deadline:
                                continue
                            remaining = self._max_body_bytes - retained_bytes
                            if remaining > 0 and handle is not None:
                                piece = chunk[:remaining]
                                try:
                                    handle.write(piece)
                                    retained_bytes += len(piece)
                                except OSError as exc:
                                    error_kind = "spool_io"
                                    error_detail = type(exc).__name__
                                    try:
                                        handle.close()
                                    except OSError:
                                        pass
                                    handle = None
                            if len(chunk) > max(remaining, 0):
                                truncated = True
                    except httpx.HTTPError as exc:
                        error_kind = "transport"
                        error_detail = type(exc).__name__
                    finally:
                        if handle is not None:
                            try:
                                handle.flush()
                                os.fsync(handle.fileno())
                            except OSError as exc:
                                error_kind = "spool_io"
                                error_detail = type(exc).__name__
                                handle.close()
                                handle = None
                            if handle is not None:
                                handle.close()
                                handle = None
                        if spool_path is not None and spool_path.exists():
                            retained_bytes = os.lstat(spool_path).st_size
            except httpx.HTTPError as exc:
                error_kind = "transport"
                error_detail = type(exc).__name__
            except Exception as exc:
                error_kind = "transport"
                error_detail = type(exc).__name__
        finally:
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass
            self._limiter.release()

        try:
            journal(complete=True)
        except Exception as exc:
            error_kind = "spool_io"
            error_detail = type(exc).__name__

        return SpoolDescriptor(
            provider_org=self._org,
            request_json=request_json,
            acquired_at=acquired_at,
            status_code=status_code,
            spool_path=spool_path,
            response_started=response_started,
            response_bytes=response_bytes,
            retained_bytes=retained_bytes,
            truncated=truncated,
            error_kind=error_kind,
            error_detail=error_detail,
            acquisition_id=acquisition_id,
            journal_path=journal_path,
            reservation_id=reservation_id,
        )


# ---------------------------------------------------------------------------
# Persistence coordinator (sole SQLite / raw owner)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _PersistenceCommand:
    operation: str
    arguments: dict[str, Any]
    result: Future[Any]


class PersistenceCoordinator:
    """Bounded command client for the dedicated persistence-owner thread.

    Terminal operations are claim-bound. Control-plane lease renewal uses a
    separate queue so heartbeats are not blocked behind raw writes.
    """

    def __init__(
        self,
        *,
        db_path: Path,
        raw_root: Path,
        spool_dir: Path,
        spool_capacity: threading.BoundedSemaphore,
        queue_size: int,
        offer_timeout_seconds: float,
        max_body_bytes: int,
        max_attempts: int,
        max_spool_files: int,
    ) -> None:
        self._db_path = Path(db_path)
        self._raw_root = Path(raw_root)
        self._spool_dir = Path(spool_dir)
        self._spool_root = self._spool_dir.resolve()
        self._spool_capacity = spool_capacity
        self._commands: queue.Queue[_PersistenceCommand | None] = queue.Queue(
            maxsize=queue_size
        )
        self._control_commands: queue.Queue[_PersistenceCommand] = queue.Queue(
            maxsize=queue_size
        )
        self._offer_timeout = offer_timeout_seconds
        self._max_body_bytes = max_body_bytes
        self._max_attempts = max_attempts
        self._max_spool_files = max_spool_files
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None
        self._closed = False
        self._high_water = 0
        self._lease_expiries = 0
        self._writer_ops = 0
        self._writer_latency = 0.0
        self._writer_latency_max = 0.0
        self._high_water_lock = threading.Lock()
        self._thread = threading.Thread(
            target=self._run,
            name="pair-event-v2-persistence",
            daemon=False,
        )
        self._thread.start()
        if not self._ready.wait(timeout=30.0):
            raise PairEventV2Error("persistence thread failed to start")
        if self._startup_error is not None:
            raise PairEventV2Error(
                f"persistence thread startup failed: {self._startup_error!r}"
            )

    @property
    def queue_high_water(self) -> int:
        with self._high_water_lock:
            return self._high_water

    @property
    def lease_expiries(self) -> int:
        with self._high_water_lock:
            return self._lease_expiries

    @property
    def writer_metrics(self) -> tuple[int, float, float]:
        with self._high_water_lock:
            return (
                self._writer_ops,
                self._writer_latency,
                self._writer_latency_max,
            )

    def _offer(self, operation: str, **arguments: Any) -> Future[Any]:
        if self._closed:
            raise PairEventV2Error("persistence coordinator is closed")
        future: Future[Any] = Future()
        command = _PersistenceCommand(operation, arguments, future)
        target = (
            self._control_commands if operation == "renew_lease" else self._commands
        )
        try:
            target.put(command, timeout=self._offer_timeout)
        except queue.Full as exc:
            raise PairEventV2Error("bounded persistence queue offer timed out") from exc
        with self._high_water_lock:
            self._high_water = max(
                self._high_water,
                self._commands.qsize() + self._control_commands.qsize(),
            )
        return future

    def _call(self, operation: str, **arguments: Any) -> Any:
        return self._offer(operation, **arguments).result()

    # ---- public claim-bound and lifecycle API ----

    def persist_async(self, descriptor: SpoolDescriptor) -> Future[PersistedEnvelope]:
        return self._offer("persist_envelope", descriptor=descriptor)

    def initialize_plan(
        self,
        plan: AcquisitionPlanV2,
        *,
        execution_policy: Mapping[str, Any],
    ) -> str:
        return self._call(
            "initialize_plan", plan=plan, execution_policy=dict(execution_policy)
        )

    def claim_pending(
        self, *, plan_id: str, worker_id: str, lease_ttl_seconds: float
    ) -> Claim | None:
        return self._call(
            "claim_pending",
            plan_id=plan_id,
            worker_id=worker_id,
            lease_ttl_seconds=lease_ttl_seconds,
        )

    def renew_lease(self, claim: Claim, *, lease_ttl_seconds: float) -> bool:
        """Heartbeat path — keyed by claim.lease_token."""
        return self._call(
            "renew_lease",
            claim=claim,
            lease_ttl_seconds=lease_ttl_seconds,
        )

    def record_events(self, events: Sequence[EngineEventRecord]) -> None:
        self._call("record_events", events=tuple(events))

    def release_retry(
        self, claim: Claim, events: Sequence[EngineEventRecord] = ()
    ) -> None:
        """Atomic: retry evidence + attempt increment + lease delete (after backoff)."""
        self._call("release_retry", claim=claim, events=tuple(events))

    def terminalize(
        self,
        claim: Claim,
        events: Sequence[EngineEventRecord],
        *,
        terminal_mode: str,
    ) -> None:
        """Claim-bound terminal transition with durable terminal_mode identity."""
        self._call(
            "terminalize",
            claim=claim,
            events=tuple(events),
            terminal_mode=terminal_mode,
        )

    def commit_split(
        self,
        claim: Claim,
        children: Sequence[QueryNode],
        reason: SplitReason,
        events: Sequence[EngineEventRecord],
    ) -> None:
        self._call(
            "commit_split",
            claim=claim,
            children=tuple(children),
            reason=reason,
            events=tuple(events),
        )

    def commit_agreed(self, claim: Claim, leaf_kwargs: Mapping[str, Any]) -> str:
        return self._call(
            "commit_agreed", claim=claim, leaf_kwargs=dict(leaf_kwargs)
        )

    def resolve_winner(
        self,
        claim: Claim,
        leaf_kwargs: Mapping[str, Any] | None = None,
        *,
        split_reason: SplitReason | None = None,
        terminal_mode: str | None = None,
    ) -> str:
        """Post-lease-loss winner verification (claim-bound, no lease required).

        ``terminal_mode`` is the explicit candidate for unsplittable/terminal failure
        when there is no comparable leaf/children set (e.g. ``unsplittable_singleton``).
        """
        return self._call(
            "resolve_winner",
            claim=claim,
            leaf_kwargs=dict(leaf_kwargs) if leaf_kwargs is not None else None,
            split_reason=split_reason,
            terminal_mode=terminal_mode,
        )

    def load_header(
        self,
        *,
        plan_id: str,
        block_number: int,
        primary_org: str,
        secondary_org: str,
    ) -> tuple[
        CanonicalHeaderReceiptRecord, AuthenticatedEvidence, AuthenticatedEvidence
    ] | None:
        return self._call(
            "load_header",
            plan_id=plan_id,
            block_number=block_number,
            primary_org=primary_org,
            secondary_org=secondary_org,
        )

    def store_header(
        self, record: CanonicalHeaderReceiptRecord
    ) -> CanonicalHeaderReceiptRecord:
        return self._call("store_header", record=record)

    def load_chain_identity(
        self, *, plan_id: str, primary_org: str, secondary_org: str
    ) -> tuple[
        ChainIdentityReceipt, AuthenticatedEvidence, AuthenticatedEvidence
    ] | None:
        return self._call(
            "load_chain_identity",
            plan_id=plan_id,
            primary_org=primary_org,
            secondary_org=secondary_org,
        )

    def store_chain_identity(
        self, record: ChainIdentityReceipt
    ) -> ChainIdentityReceipt:
        return self._call("store_chain_identity", record=record)

    def count_by_status(self, plan_id: str) -> dict[str, int]:
        return self._call("count_by_status", plan_id=plan_id)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._commands.put(None)
        self._thread.join()

    # ---- thread loop ----

    def _run(self) -> None:
        conn: sqlite3.Connection | None = None
        catalog: SqliteRawObjectCatalog | None = None
        try:
            conn = sqlite3.connect(self._db_path, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 5000")
            catalog = SqliteRawObjectCatalog(self._db_path, connection=conn)
            writer = RawObjectWriter(RawObjectStoreConfig(root=self._raw_root), catalog)
            self._recover_journaled_spools(conn, writer)
        except BaseException as exc:
            self._startup_error = exc
            if catalog is not None:
                catalog.close()
            if conn is not None:
                conn.close()
            self._ready.set()
            return
        self._ready.set()

        while True:
            try:
                command: _PersistenceCommand | None = (
                    self._control_commands.get_nowait()
                )
                source_queue: queue.Queue[Any] = self._control_commands
            except queue.Empty:
                try:
                    command = self._commands.get(timeout=0.05)
                except queue.Empty:
                    continue
                source_queue = self._commands
            if command is None:
                source_queue.task_done()
                break
            try:
                result = self._execute_command(conn, writer, command)
                if not command.result.cancelled():
                    command.result.set_result(result)
            except BaseException as exc:
                if not command.result.cancelled():
                    command.result.set_exception(exc)
            finally:
                source_queue.task_done()
                self._service_control_commands(conn, writer)

        catalog.close()
        conn.close()

    def _execute_command(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        command: _PersistenceCommand,
    ) -> Any:
        op = command.operation
        args = command.arguments
        handlers: dict[str, Callable[..., Any]] = {
            "persist_envelope": self._op_persist_envelope,
            "initialize_plan": self._op_initialize_plan,
            "claim_pending": self._op_claim_pending,
            "renew_lease": self._op_renew_lease,
            "record_events": self._op_record_events,
            "release_retry": self._op_release_retry,
            "terminalize": self._op_terminalize,
            "commit_split": self._op_commit_split,
            "commit_agreed": self._op_commit_agreed,
            "resolve_winner": self._op_resolve_winner,
            "load_header": self._op_load_header,
            "store_header": self._op_store_header,
            "load_chain_identity": self._op_load_chain_identity,
            "store_chain_identity": self._op_store_chain_identity,
            "count_by_status": self._op_count_by_status,
        }
        handler = handlers.get(op)
        if handler is None:
            raise PairEventV2Error(f"unknown persistence operation {op!r}")
        return handler(conn, writer, **args)

    def _service_control_commands(
        self, conn: sqlite3.Connection, writer: RawObjectWriter
    ) -> None:
        while True:
            try:
                command = self._control_commands.get_nowait()
            except queue.Empty:
                return
            try:
                result = self._execute_command(conn, writer, command)
                if not command.result.cancelled():
                    command.result.set_result(result)
            except BaseException as exc:
                if not command.result.cancelled():
                    command.result.set_exception(exc)
            finally:
                self._control_commands.task_done()

    # ---- spool recovery / persist ----

    def _read_spool_journal(self, journal_name: str) -> Mapping[str, Any]:
        """Read a journal via trusted dirfd + relative O_NOFOLLOW open."""
        fd, _path = _open_under_root(self._spool_root, journal_name)
        try:
            body, _digest, size = _read_fd_bounded(
                fd, max_bytes=self._max_body_bytes
            )
        finally:
            os.close(fd)
        if size > self._max_body_bytes:
            raise PairEventV2Error("spool journal is not a bounded regular file")
        payload = json.loads(
            body.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys
        )
        if not isinstance(payload, Mapping) or _contains_sensitive_key(payload):
            raise PairEventV2Error("spool journal is malformed or sensitive")
        return payload

    def _count_surviving_spool_slots(self) -> int:
        """Count distinct started-response reservations occupying capacity."""
        keys: set[str] = set()
        for path in self._spool_dir.glob("response-*.spool"):
            keys.add(path.name)
        for path in self._spool_dir.glob("*.journal.json"):
            # journal name is ``<spool_name>.journal.json``
            name = path.name
            if name.endswith(".journal.json"):
                keys.add(name[: -len(".journal.json")])
            else:
                keys.add(name)
        return len(keys)

    def _recover_journaled_spools(
        self, conn: sqlite3.Connection, writer: RawObjectWriter
    ) -> None:
        """Recover started spools; capacity accounts for all survivors.

        Never delete an unreadable journal while leaving its spool untracked.
        Malformed per-journal fields are isolated without aborting startup.
        """
        self._spool_dir.mkdir(parents=True, exist_ok=True)
        for temporary in self._spool_dir.glob("*.tmp-*"):
            temporary.unlink(missing_ok=True)
        journals = sorted(self._spool_dir.glob("*.journal.json"))
        for journal_path in journals:
            journal_name = journal_path.name
            try:
                payload = self._read_spool_journal(journal_name)
            except Exception:
                # Keep the journal+sibling spool tracked for capacity; do not delete.
                continue
            try:
                if payload.get("schema_version") != SPOOL_DESCRIPTOR_SCHEMA_VERSION:
                    continue
                spool_name = payload.get("spool_name")
                if (
                    not isinstance(spool_name, str)
                    or Path(spool_name).name != spool_name
                ):
                    continue
                spool_path = self._spool_dir / spool_name
                complete = bool(payload.get("complete"))
                response_started = bool(payload.get("response_started"))
                request = payload.get("request")
                if not isinstance(request, Mapping):
                    continue
                if not complete and not response_started:
                    # Pre-start reservation with no response — safe to free both.
                    spool_path.unlink(missing_ok=True)
                    journal_path.unlink(missing_ok=True)
                    continue
                actual_bytes = 0
                spool_ok = False
                if spool_path.exists():
                    try:
                        fd, _p = _open_under_root(self._spool_root, spool_name)
                        try:
                            actual_bytes = int(os.fstat(fd).st_size)
                            spool_ok = True
                        finally:
                            os.close(fd)
                    except Exception:
                        spool_ok = False
                        actual_bytes = 0
                journal_response_bytes = int(payload.get("response_bytes") or 0)
                journal_truncated = bool(payload.get("truncated"))
                error_kind = (
                    str(payload["error_kind"])
                    if payload.get("error_kind") is not None
                    else None
                )
                error_detail = (
                    str(payload["error_detail"])
                    if payload.get("error_detail") is not None
                    else None
                )
                # Complete truncated: journaled response_bytes may exceed file retained
                # bytes — that is valid, not spool_incomplete.
                if complete and spool_ok:
                    descriptor = SpoolDescriptor(
                        provider_org=str(payload["provider_org"]),
                        request_json=_canonical_json(dict(request)),
                        acquired_at=datetime.fromisoformat(
                            str(payload["acquired_at"])
                        ),
                        status_code=(
                            int(payload["status_code"])
                            if payload.get("status_code") is not None
                            else None
                        ),
                        spool_path=spool_path,
                        response_started=True,
                        response_bytes=journal_response_bytes,
                        retained_bytes=actual_bytes,
                        truncated=journal_truncated,
                        error_kind=error_kind,
                        error_detail=error_detail,
                        acquisition_id=(
                            str(payload["acquisition_id"])
                            if payload.get("acquisition_id") is not None
                            else None
                        ),
                        journal_path=journal_path,
                        reservation_id=(
                            str(payload["reservation_id"])
                            if payload.get("reservation_id") is not None
                            else None
                        ),
                    )
                    try:
                        self._op_persist_envelope(
                            conn,
                            writer,
                            descriptor=descriptor,
                            release_capacity=False,
                        )
                    except Exception:
                        continue
                    continue
                incomplete = not complete
                if not spool_ok and response_started:
                    error_kind = error_kind or "spool_missing_after_start"
                    error_detail = (
                        error_detail
                        or "started response journal is missing its spool evidence"
                    )
                    descriptor = SpoolDescriptor(
                        provider_org=str(payload.get("provider_org") or "unknown"),
                        request_json=_canonical_json(dict(request)),
                        acquired_at=datetime.fromisoformat(
                            str(payload["acquired_at"])
                        ),
                        status_code=(
                            int(payload["status_code"])
                            if payload.get("status_code") is not None
                            else None
                        ),
                        spool_path=None,
                        response_started=True,
                        response_bytes=0,
                        retained_bytes=0,
                        truncated=False,
                        error_kind=error_kind,
                        error_detail=error_detail,
                        acquisition_id=(
                            str(payload["acquisition_id"])
                            if payload.get("acquisition_id") is not None
                            else None
                        ),
                        journal_path=journal_path,
                        reservation_id=(
                            str(payload["reservation_id"])
                            if payload.get("reservation_id") is not None
                            else None
                        ),
                    )
                    try:
                        self._op_persist_envelope(
                            conn,
                            writer,
                            descriptor=descriptor,
                            release_capacity=False,
                        )
                    except Exception:
                        continue
                    continue
                if not spool_ok:
                    continue
                # Incomplete (not complete) recovery — separate failure class.
                if incomplete and error_kind is None:
                    error_kind = "spool_incomplete"
                    error_detail = (
                        "incomplete started spool recovered as non-authoritative failure"
                    )
                descriptor = SpoolDescriptor(
                    provider_org=str(payload["provider_org"]),
                    request_json=_canonical_json(dict(request)),
                    acquired_at=datetime.fromisoformat(str(payload["acquired_at"])),
                    status_code=(
                        int(payload["status_code"])
                        if payload.get("status_code") is not None
                        else None
                    ),
                    spool_path=spool_path,
                    response_started=True,
                    # Incomplete: use actual retained file size for both counts.
                    response_bytes=actual_bytes,
                    retained_bytes=actual_bytes,
                    truncated=journal_truncated,
                    error_kind=error_kind,
                    error_detail=error_detail,
                    acquisition_id=(
                        str(payload["acquisition_id"])
                        if payload.get("acquisition_id") is not None
                        else None
                    ),
                    journal_path=journal_path,
                    reservation_id=(
                        str(payload["reservation_id"])
                        if payload.get("reservation_id") is not None
                        else None
                    ),
                )
                try:
                    self._op_persist_envelope(
                        conn,
                        writer,
                        descriptor=descriptor,
                        release_capacity=False,
                    )
                except Exception:
                    continue
            except Exception:
                # Isolate malformed fields; keep capacity occupancy.
                continue
        occupied = self._count_surviving_spool_slots()
        if occupied > self._max_spool_files:
            raise PairEventV2Error(
                "surviving spool/journal occupancy exceeds max_spool_files"
            )
        # Semaphore starts full; hold occupied permits so free = max - occupied.
        for _ in range(occupied):
            if not self._spool_capacity.acquire(blocking=False):
                break

    def _cleanup_registered_descriptor(
        self, descriptor: SpoolDescriptor, *, release_capacity: bool = True
    ) -> None:
        if descriptor.spool_path is not None:
            descriptor.spool_path.unlink(missing_ok=True)
        if descriptor.journal_path is not None:
            descriptor.journal_path.unlink(missing_ok=True)
        if release_capacity and (
            descriptor.reservation_id is not None or descriptor.spool_path is not None
        ):
            try:
                self._spool_capacity.release()
            except ValueError:
                pass

    def _spool_chunks(
        self,
        path: Path,
        *,
        pulse: Callable[[], None] | None = None,
    ) -> Iterator[bytes]:
        """Stream spool bytes under trusted dirfd; pulse control queue between chunks."""
        fd, _p = _open_under_root(path.parent, path.name)
        try:
            while True:
                if pulse is not None:
                    pulse()
                chunk = os.read(fd, 64 * 1024)
                if not chunk:
                    return
                yield chunk
        finally:
            os.close(fd)

    def _op_persist_envelope(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        descriptor: SpoolDescriptor,
        release_capacity: bool = True,
    ) -> PersistedEnvelope:
        started = time.monotonic()
        try:
            request = json.loads(descriptor.request_json)
            metadata = AcquisitionMetadata(
                source_id=SOURCE_ID,
                acquisition_id=descriptor.acquisition_id,
                request=dict(request),
                response_metadata={
                    "provider_org": descriptor.provider_org,
                    "status_code": descriptor.status_code,
                    "response_bytes": descriptor.response_bytes,
                    "retained_bytes": descriptor.retained_bytes,
                    "truncated": descriptor.truncated,
                    "error_kind": descriptor.error_kind,
                    "error_detail": descriptor.error_detail,
                },
                original_name=(
                    f"{descriptor.provider_org}_{request.get('method', 'rpc')}_"
                    f"{descriptor.acquired_at.strftime('%Y%m%dT%H%M%S%f')}.json"
                ),
                acquired_at=descriptor.acquired_at,
            )

            def pulse() -> None:
                # Lease renewals must not wait behind write_stream.
                self._service_control_commands(conn, writer)


            if descriptor.spool_path is None or descriptor.retained_bytes == 0:
                pulse()
                failed = writer.record_failed_acquisition(
                    metadata,
                    descriptor.error_detail or "empty or transport failure",
                )
                latency = time.monotonic() - started
                with self._high_water_lock:
                    self._writer_ops += 1
                    self._writer_latency += latency
                    self._writer_latency_max = max(self._writer_latency_max, latency)
                self._cleanup_registered_descriptor(
                    descriptor, release_capacity=release_capacity
                )
                return PersistedEnvelope(
                    descriptor=descriptor,
                    evidence=None,
                    acquisition_id=getattr(failed, "acquisition_id", None),
                    writer_latency_seconds=latency,
                )
            published = writer.write_stream(
                self._spool_chunks(descriptor.spool_path, pulse=pulse),
                metadata,
            )
            latency = time.monotonic() - started
            with self._high_water_lock:
                self._writer_ops += 1
                self._writer_latency += latency
                self._writer_latency_max = max(self._writer_latency_max, latency)
            evidence = AuthenticatedEvidence(
                provider_org=descriptor.provider_org,
                request_json=descriptor.request_json,
                raw_object_id=published.raw_object_id,
                acquisition_id=published.acquisition_id,
                sha256=published.sha256,
                byte_size=published.byte_size,
                storage_uri=str(published.storage_uri),
                storage_path=Path(published.storage_path),
            )
            receipt = PublicationReceipt(
                raw_object_id=published.raw_object_id,
                sha256=published.sha256,
                byte_size=published.byte_size,
                storage_path=Path(published.storage_path),
                storage_uri=published.storage_uri,
                object_prefix="raw/sha256",
                reused_existing=getattr(published, "reused_existing", False)
                or getattr(published, "content_already_present", False),
                verified_regular_file=True,
                verified_size=True,
                verified_sha256=True,
            )
            verify_publication_receipt(
                receipt,
                store_root=self._raw_root.resolve(),
                object_prefix="raw/sha256",
            )
            self._cleanup_registered_descriptor(
                descriptor, release_capacity=release_capacity
            )
            return PersistedEnvelope(
                descriptor=descriptor,
                evidence=evidence,
                acquisition_id=published.acquisition_id,
                writer_latency_seconds=latency,
            )
        except Exception:
            # Leave journal/spool for crash recovery on hard failures mid-write.
            raise

    def _authenticate_evidence(
        self,
        conn: sqlite3.Connection,
        *,
        raw_object_id: str,
        acquisition_id: str,
        provider_org: str,
        request: Mapping[str, Any],
        require_successful_body: bool = True,
    ) -> AuthenticatedEvidence:
        """Bind raw evidence to source, provider, request, object, acquisition.

        Successful authority requires: SUCCEEDED, SOURCE_ID, matching provider_org,
        integer 2xx status, truncated is False, no error kind/detail, and
        response_bytes == retained_bytes == raw_object.byte_size. Re-opens via
        trusted dirfds and re-establishes canonical raw_object_id/SHA/storage.
        """
        expected_org = normalize_provider_org(provider_org)
        row = conn.execute(
            "SELECT a.acquisition_id, a.raw_object_id, a.source_id, a.request_json, "
            "a.response_metadata_json, a.status, "
            "o.sha256, o.byte_size, o.storage_uri "
            "FROM raw_acquisition a "
            "JOIN raw_object o ON o.raw_object_id = a.raw_object_id "
            "WHERE a.acquisition_id = ? AND a.raw_object_id = ?",
            (acquisition_id, raw_object_id),
        ).fetchone()
        if row is None:
            raise PairEventV2Error("raw acquisition evidence missing")
        if str(row["source_id"]) != SOURCE_ID:
            raise PairEventV2Error("raw acquisition source_id is not the v2 engine source")
        if require_successful_body and row["status"] != "SUCCEEDED":
            raise PairEventV2Error("raw acquisition is not SUCCEEDED")
        stored_request = json.loads(row["request_json"] or "{}")
        expected = _canonical_json(dict(request))
        if _canonical_json(stored_request) != expected:
            raise PairEventV2Error("raw acquisition request does not match expected")
        if _contains_sensitive_key(stored_request):
            raise PairEventV2Error("stored acquisition request is sensitive")
        try:
            response_meta = json.loads(row["response_metadata_json"] or "{}")
        except json.JSONDecodeError as exc:
            raise PairEventV2Error("response_metadata_json is not JSON") from exc
        if not isinstance(response_meta, Mapping):
            raise PairEventV2Error("response_metadata_json must be an object")
        meta_org = response_meta.get("provider_org")
        if meta_org is None:
            raise PairEventV2Error("response_metadata_json missing provider_org")
        if normalize_provider_org(meta_org) != expected_org:
            raise PairEventV2Error(
                "response_metadata provider_org does not match expected authority"
            )
        catalog_byte_size = int(row["byte_size"])
        if require_successful_body:
            status_code = response_meta.get("status_code")
            if not isinstance(status_code, int) or not (200 <= status_code < 300):
                raise PairEventV2Error(
                    "successful authority requires integer 2xx status_code metadata"
                )
            if response_meta.get("truncated") is not False:
                raise PairEventV2Error(
                    "successful authority requires truncated is False"
                )
            if response_meta.get("error_kind") not in (None, ""):
                raise PairEventV2Error(
                    "successful authority requires empty error_kind"
                )
            if response_meta.get("error_detail") not in (None, ""):
                raise PairEventV2Error(
                    "successful authority requires empty error_detail"
                )
            response_bytes = response_meta.get("response_bytes")
            retained_bytes = response_meta.get("retained_bytes")
            if not isinstance(response_bytes, int) or not isinstance(
                retained_bytes, int
            ):
                raise PairEventV2Error(
                    "successful authority requires integer response/retained byte metadata"
                )
            if not (
                response_bytes == retained_bytes == catalog_byte_size
            ):
                raise PairEventV2Error(
                    "successful authority requires response_bytes == retained_bytes "
                    "== raw_object.byte_size"
                )
        storage_uri = str(row["storage_uri"])
        root = self._raw_root.resolve()
        if ".." in Path(storage_uri).parts or Path(storage_uri).is_absolute():
            raise PairEventV2Error("raw object path escapes store root")
        fd, storage_path = _open_under_root(root, storage_uri)
        try:
            body, digest, size = _read_fd_bounded(
                fd,
                max_bytes=max(self._max_body_bytes, catalog_byte_size),
                expected_size=catalog_byte_size,
            )
        finally:
            os.close(fd)
        if digest != str(row["sha256"]) or size != catalog_byte_size:
            raise PairEventV2Error("on-disk raw object disagrees with catalog identity")
        # Re-establish canonical identity (raw_object_id / sha / storage_uri).
        expected_raw_id = "raw_" + digest
        expected_uri = f"raw/sha256/{digest[0:2]}/{digest[2:4]}/{digest}"
        if str(row["raw_object_id"]) != expected_raw_id or str(row["sha256"]) != digest:
            raise PairEventV2Error("catalog raw_object_id/SHA is not canonical")
        if storage_uri != expected_uri:
            raise PairEventV2Error(
                "storage_uri is not the digest-derived raw/sha256 canonical path"
            )
        return AuthenticatedEvidence(
            provider_org=expected_org,
            request_json=expected,
            raw_object_id=expected_raw_id,
            acquisition_id=str(row["acquisition_id"]),
            sha256=digest,
            byte_size=catalog_byte_size,
            storage_uri=expected_uri,
            storage_path=storage_path,
        )

    # ---- plan / claim / lease ----

    def _op_initialize_plan(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan: AcquisitionPlanV2,
        execution_policy: Mapping[str, Any],
    ) -> str:
        del writer
        if _contains_sensitive_key(execution_policy):
            raise PairEventV2Error("execution policy contains sensitive keys")
        if str(execution_policy.get("plan_id", "")) != plan.plan_id:
            raise PairEventV2Error("execution policy plan_id must bind the plan")
        policy_json = _canonical_json(dict(execution_policy))
        # Include plan_id in the hash so identical settings on distinct plans never collide.
        policy_id = _identity("pol_", json.loads(policy_json))
        expected_record = plan_record_from_config(plan.config, created_at=_now())
        expected_roots = {
            root.domain_id: QueryNode(plan_id=plan.plan_id, domain=root.domain)
            for root in plan.root_filters
        }
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                f"SELECT * FROM {PLAN_TABLE} WHERE plan_id = ?", (plan.plan_id,)
            ).fetchone()
            if row is None:
                conn.execute(
                    f"INSERT INTO {PLAN_TABLE} (plan_id, registry_dataset_id, "
                    "identity_payload_json, event_provider_orgs_json, "
                    "metadata_provider_orgs_json, root_block_size, initial_cohort_size, "
                    "deployment_block, cutoff_block, plan_schema_version, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        expected_record.plan_id,
                        expected_record.registry_dataset_id,
                        expected_record.identity_payload_json,
                        expected_record.event_provider_orgs_json,
                        expected_record.metadata_provider_orgs_json,
                        expected_record.root_block_size,
                        expected_record.initial_cohort_size,
                        expected_record.deployment_block,
                        expected_record.cutoff_block,
                        expected_record.plan_schema_version,
                        expected_record.created_at,
                    ),
                )
                for node in expected_roots.values():
                    self._insert_node(conn, node, attempt=0, updated_at=_now())
                conn.execute(
                    f"INSERT INTO {EXECUTION_POLICY_TABLE} ("
                    + ",".join(EXECUTION_POLICY_RECORD_COLUMNS)
                    + ") VALUES (?,?,?,?,?)",
                    (
                        policy_id,
                        plan.plan_id,
                        policy_json,
                        EXECUTION_POLICY_SCHEMA_VERSION,
                        _now(),
                    ),
                )
            else:
                actual = PlanRecord(
                    plan_id=row["plan_id"],
                    registry_dataset_id=row["registry_dataset_id"],
                    identity_payload_json=row["identity_payload_json"],
                    event_provider_orgs_json=row["event_provider_orgs_json"],
                    metadata_provider_orgs_json=row["metadata_provider_orgs_json"],
                    root_block_size=row["root_block_size"],
                    initial_cohort_size=row["initial_cohort_size"],
                    deployment_block=row["deployment_block"],
                    cutoff_block=row["cutoff_block"],
                    plan_schema_version=row["plan_schema_version"],
                    created_at=row["created_at"],
                )
                if replace(actual, created_at="") != replace(
                    expected_record, created_at=""
                ):
                    raise PairEventV2Error("persisted plan row is not the requested plan")
                root_rows = conn.execute(
                    f"SELECT * FROM {NODE_TABLE} WHERE plan_id = ? "
                    "AND parent_domain_id IS NULL",
                    (plan.plan_id,),
                ).fetchall()
                if {str(item["domain_id"]) for item in root_rows} != set(expected_roots):
                    raise PairEventV2Error("persisted root set is not exact")
                for root_row in root_rows:
                    record = QueryNodeRecord(
                        plan_id=root_row["plan_id"],
                        domain_id=root_row["domain_id"],
                        start_block=root_row["start_block"],
                        end_block=root_row["end_block"],
                        addresses_json=root_row["addresses_json"],
                        topics_json=root_row["topics_json"],
                        status=root_row["status"],
                        parent_domain_id=root_row["parent_domain_id"],
                        split_reason=root_row["split_reason"],
                        attempt=root_row["attempt"],
                        updated_at=root_row["updated_at"],
                    )
                    expected = expected_roots[record.domain_id]
                    if (
                        record.start_block != expected.domain.start_block
                        or record.end_block != expected.domain.end_block
                        or record.addresses_json
                        != _canonical_json(list(expected.domain.addresses))
                        or record.topics_json
                        != _canonical_json(list(expected.domain.topics))
                    ):
                        raise PairEventV2Error("persisted root domain is not authentic")
                policy_row = conn.execute(
                    f"SELECT * FROM {EXECUTION_POLICY_TABLE} WHERE plan_id = ?",
                    (plan.plan_id,),
                ).fetchone()
                if policy_row is None:
                    raise PairEventV2Error(
                        "plan resume missing immutable execution policy record"
                    )
                if (
                    str(policy_row["identity_payload_json"]) != policy_json
                    or str(policy_row["policy_id"]) != policy_id
                    or str(policy_row["schema_version"])
                    != EXECUTION_POLICY_SCHEMA_VERSION
                ):
                    raise PairEventV2Error(
                        "execution policy mismatch on plan resume — authority settings changed"
                    )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return plan.plan_id

    def _insert_node(
        self,
        conn: sqlite3.Connection,
        node: QueryNode,
        *,
        attempt: int,
        updated_at: str,
    ) -> None:
        conn.execute(
            f"INSERT INTO {NODE_TABLE} (plan_id, domain_id, start_block, end_block, "
            "addresses_json, topics_json, status, parent_domain_id, split_reason, "
            "attempt, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                node.plan_id,
                node.domain_id,
                node.domain.start_block,
                node.domain.end_block,
                _canonical_json(list(node.domain.addresses)),
                _canonical_json(list(node.domain.topics)),
                node.status,
                node.parent_domain_id,
                node.split_reason,
                attempt,
                updated_at,
            ),
        )

    def _node_from_row(
        self, row: sqlite3.Row, *, status: str | None = None
    ) -> QueryNode:
        return QueryNode(
            plan_id=str(row["plan_id"]),
            domain=QueryDomain(
                start_block=int(row["start_block"]),
                end_block=int(row["end_block"]),
                addresses=tuple(json.loads(row["addresses_json"])),
                topics=tuple(json.loads(row["topics_json"])),
            ),
            status=status or str(row["status"]),  # type: ignore[arg-type]
            parent_domain_id=row["parent_domain_id"],
            split_reason=row["split_reason"],
        )

    def _insert_event(self, conn: sqlite3.Connection, event: EngineEventRecord) -> None:
        """Insert by event_id; on conflict authenticate the existing identity payload."""
        values = (
            event.event_id,
            event.schema_version,
            event.plan_id,
            event.domain_id,
            event.attempt,
            event.event_kind,
            event.failure_class,
            event.decision,
            event.provider_org,
            event.request_json,
            event.primary_raw_object_id,
            event.secondary_raw_object_id,
            event.primary_acquisition_id,
            event.secondary_acquisition_id,
            event.detail_json,
            event.created_at,
        )
        placeholders = ",".join("?" for _ in ENGINE_EVENT_RECORD_COLUMNS)
        try:
            conn.execute(
                f"INSERT INTO {ENGINE_EVENT_TABLE} ("
                + ",".join(ENGINE_EVENT_RECORD_COLUMNS)
                + f") VALUES ({placeholders})",
                values,
            )
        except sqlite3.IntegrityError:
            row = conn.execute(
                f"SELECT * FROM {ENGINE_EVENT_TABLE} WHERE event_id = ?",
                (event.event_id,),
            ).fetchone()
            if row is None:
                raise PairEventV2Error("engine event conflict without existing row")
            existing = EngineEventRecord(
                event_id=row["event_id"],
                plan_id=row["plan_id"],
                domain_id=row["domain_id"],
                attempt=int(row["attempt"]),
                event_kind=row["event_kind"],
                failure_class=row["failure_class"],
                decision=row["decision"],
                provider_org=row["provider_org"],
                request_json=row["request_json"],
                primary_raw_object_id=row["primary_raw_object_id"],
                secondary_raw_object_id=row["secondary_raw_object_id"],
                primary_acquisition_id=row["primary_acquisition_id"],
                secondary_acquisition_id=row["secondary_acquisition_id"],
                detail_json=row["detail_json"],
                created_at=row["created_at"],
                schema_version=row["schema_version"],
            )
            if replace(existing, created_at="") != replace(event, created_at=""):
                raise PairEventV2Error(
                    "engine event_id collision with divergent identity payload"
                )

    def _expire_leases(self, conn: sqlite3.Connection, plan_id: str) -> int:
        """Atomically expire leases: evidence + attempt bump + exact lease delete."""
        timestamp = _now()
        rows = conn.execute(
            f"SELECT l.*, n.attempt FROM {LEASE_TABLE} l JOIN {NODE_TABLE} n "
            "ON n.plan_id = l.plan_id AND n.domain_id = l.domain_id "
            "WHERE l.plan_id = ? AND l.expires_at < ?",
            (plan_id, timestamp),
        ).fetchall()
        expired = 0
        for row in rows:
            next_attempt = int(row["attempt"]) + 1
            fingerprint = _lease_fingerprint(str(row["lease_token"]))
            self._insert_event(
                conn,
                make_engine_event_record(
                    plan_id=plan_id,
                    domain_id=row["domain_id"],
                    attempt=int(row["attempt"]),
                    event_kind="lease_expiry",
                    failure_class=FailureClass.TRANSPORT,
                    detail={
                        "expires_at": row["expires_at"],
                        "leased_at": row["leased_at"],
                        "lease_fingerprint": fingerprint,
                    },
                ),
            )
            self._insert_event(
                conn,
                make_engine_event_record(
                    plan_id=plan_id,
                    domain_id=row["domain_id"],
                    attempt=int(row["attempt"]),
                    event_kind=(
                        "terminal_blocker"
                        if next_attempt >= self._max_attempts
                        else "retry_decision"
                    ),
                    failure_class=FailureClass.TRANSPORT,
                    decision=(
                        "terminal" if next_attempt >= self._max_attempts else "retry"
                    ),
                    detail={
                        "reason": "lease_expired",
                        "lease_fingerprint": fingerprint,
                        "terminal_mode": (
                            TERMINAL_MODE_LEASE_EXPIRED
                            if next_attempt >= self._max_attempts
                            else None
                        ),
                    },
                ),
            )
            # Exact-token delete so a concurrent renew cannot be clobbered by domain-only delete.
            conn.execute(
                f"UPDATE {NODE_TABLE} SET status = 'PENDING', attempt = ?, updated_at = ? "
                "WHERE plan_id = ? AND domain_id = ? AND status = 'IN_FLIGHT'",
                (next_attempt, timestamp, plan_id, row["domain_id"]),
            )
            conn.execute(
                f"DELETE FROM {LEASE_TABLE} WHERE plan_id = ? AND domain_id = ? "
                "AND lease_token = ?",
                (plan_id, row["domain_id"], row["lease_token"]),
            )
            if next_attempt >= self._max_attempts:
                # Durable terminal winner identity — distinct from other terminal modes.
                self._upsert_terminal_receipt(
                    conn,
                    plan_id=plan_id,
                    domain_id=str(row["domain_id"]),
                    terminal_mode=TERMINAL_MODE_LEASE_EXPIRED,
                    attempt=next_attempt,
                    completed_at=timestamp,
                )
            expired += 1
        if expired:
            with self._high_water_lock:
                self._lease_expiries += expired
        return expired

    def _op_claim_pending(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
        worker_id: str,
        lease_ttl_seconds: float,
    ) -> Claim | None:
        del writer
        conn.execute("BEGIN IMMEDIATE")
        try:
            self._expire_leases(conn, plan_id)
            row = conn.execute(
                f"SELECT * FROM {NODE_TABLE} WHERE plan_id = ? AND status = 'PENDING' "
                "AND attempt < ? ORDER BY start_block, domain_id LIMIT 1",
                (plan_id, self._max_attempts),
            ).fetchone()
            if row is None:
                conn.execute("COMMIT")
                return None
            now = datetime.now(UTC)
            token = uuid.uuid4().hex
            conn.execute(
                f"UPDATE {NODE_TABLE} SET status = 'IN_FLIGHT', updated_at = ? "
                "WHERE plan_id = ? AND domain_id = ? AND status = 'PENDING' "
                "AND attempt < ?",
                (now.isoformat(), plan_id, row["domain_id"], self._max_attempts),
            )
            if conn.execute("SELECT changes()").fetchone()[0] != 1:
                conn.execute("COMMIT")
                return None
            conn.execute(
                f"INSERT INTO {LEASE_TABLE} (plan_id, domain_id, worker_id, "
                "lease_token, leased_at, expires_at) VALUES (?,?,?,?,?,?)",
                (
                    plan_id,
                    row["domain_id"],
                    worker_id,
                    token,
                    now.isoformat(),
                    (now + timedelta(seconds=lease_ttl_seconds)).isoformat(),
                ),
            )
            conn.execute("COMMIT")
            node = self._node_from_row(row, status="IN_FLIGHT")
            return Claim(
                plan_id=plan_id,
                domain_id=str(row["domain_id"]),
                worker_id=worker_id,
                lease_token=token,
                attempt=int(row["attempt"]),
                node=node,
            )
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def _op_renew_lease(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        claim: Claim,
        lease_ttl_seconds: float,
    ) -> bool:
        del writer
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=float(lease_ttl_seconds))
        conn.execute(
            f"UPDATE {LEASE_TABLE} SET expires_at = ? WHERE plan_id = ? "
            "AND domain_id = ? AND worker_id = ? AND lease_token = ? "
            "AND expires_at >= ? AND EXISTS ("
            f"SELECT 1 FROM {NODE_TABLE} n WHERE n.plan_id = ? "
            "AND n.domain_id = ? AND n.status = 'IN_FLIGHT')",
            (
                expires.isoformat(),
                claim.plan_id,
                claim.domain_id,
                claim.worker_id,
                claim.lease_token,
                now.isoformat(),
                claim.plan_id,
                claim.domain_id,
            ),
        )
        return conn.execute("SELECT changes()").fetchone()[0] == 1

    def _require_lease(self, conn: sqlite3.Connection, claim: Claim) -> None:
        row = conn.execute(
            f"SELECT worker_id, lease_token, expires_at FROM {LEASE_TABLE} "
            "WHERE plan_id = ? AND domain_id = ?",
            (claim.plan_id, claim.domain_id),
        ).fetchone()
        if row is None:
            raise _LeaseLostError("lease missing for claimed node")
        if (
            row["worker_id"] != claim.worker_id
            or row["lease_token"] != claim.lease_token
        ):
            raise _LeaseLostError("lease ownership mismatch")
        if row["expires_at"] < _now():
            raise _LeaseLostError("lease expired before terminal commit")

    def _op_record_events(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        events: Sequence[EngineEventRecord],
    ) -> None:
        del writer
        conn.execute("BEGIN IMMEDIATE")
        try:
            for event in events:
                self._insert_event(conn, event)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def _op_release_retry(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        claim: Claim,
        events: Sequence[EngineEventRecord] = (),
    ) -> None:
        """Claim-bound atomic retry: evidence rows + attempt + exact lease delete."""
        del writer
        now = _now()
        conn.execute("BEGIN IMMEDIATE")
        try:
            self._require_lease(conn, claim)
            for event in events:
                self._insert_event(conn, event)
            conn.execute(
                f"UPDATE {NODE_TABLE} SET status = 'PENDING', "
                "attempt = attempt + 1, updated_at = ? "
                "WHERE plan_id = ? AND domain_id = ?",
                (now, claim.plan_id, claim.domain_id),
            )
            conn.execute(
                f"DELETE FROM {LEASE_TABLE} WHERE plan_id = ? AND domain_id = ? "
                "AND lease_token = ?",
                (claim.plan_id, claim.domain_id, claim.lease_token),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def _upsert_terminal_receipt(
        self,
        conn: sqlite3.Connection,
        *,
        plan_id: str,
        domain_id: str,
        terminal_mode: str,
        attempt: int,
        completed_at: str,
    ) -> str:
        """Persist durable terminal winner identity; reject mode aliasing."""
        if not terminal_mode or not str(terminal_mode).strip():
            raise PairEventV2Error("terminal_mode is required")
        mode = str(terminal_mode)
        if mode not in TERMINAL_MODES:
            raise PairEventV2Error(f"terminal_mode not in TERMINAL_MODES: {mode!r}")
        if int(attempt) != self._max_attempts:
            raise PairEventV2Error(
                "terminal receipt attempt must equal configured max_attempts"
            )
        receipt_id = compute_terminal_receipt_id(
            plan_id=plan_id,
            domain_id=domain_id,
            terminal_mode=mode,
            attempt=int(attempt),
        )
        existing = conn.execute(
            f"SELECT * FROM {TERMINAL_RECEIPT_TABLE} "
            "WHERE plan_id = ? AND domain_id = ?",
            (plan_id, domain_id),
        ).fetchone()
        if existing is not None:
            if str(existing["terminal_mode"]) != mode:
                raise PairEventV2Error(
                    "terminal winner mode conflict: "
                    f"existing {existing['terminal_mode']!r} != candidate {mode!r}"
                )
            if str(existing["terminal_receipt_id"]) != receipt_id:
                # Same mode must recompute the same identity (attempt included).
                if int(existing["attempt"]) != int(attempt):
                    raise PairEventV2Error(
                        "terminal winner attempt/identity disagrees with candidate"
                    )
                raise PairEventV2Error("terminal receipt id mismatch for same mode")
            return str(existing["terminal_receipt_id"])
        conn.execute(
            f"INSERT INTO {TERMINAL_RECEIPT_TABLE} ("
            + ",".join(TERMINAL_RECEIPT_RECORD_COLUMNS)
            + ") VALUES (?,?,?,?,?,?,?)",
            (
                receipt_id,
                plan_id,
                domain_id,
                mode,
                int(attempt),
                TERMINAL_RECEIPT_SCHEMA_VERSION,
                completed_at,
            ),
        )
        return receipt_id

    def _op_terminalize(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        claim: Claim,
        events: Sequence[EngineEventRecord],
        terminal_mode: str,
    ) -> None:
        """Claim-bound terminal: events + durable mode identity + PENDING at limit."""
        del writer
        now = _now()
        conn.execute("BEGIN IMMEDIATE")
        try:
            self._require_lease(conn, claim)
            for event in events:
                self._insert_event(conn, event)
            # Attempt forced to max so claim filter excludes the node.
            conn.execute(
                f"UPDATE {NODE_TABLE} SET status = 'PENDING', attempt = ?, updated_at = ? "
                "WHERE plan_id = ? AND domain_id = ?",
                (self._max_attempts, now, claim.plan_id, claim.domain_id),
            )
            self._upsert_terminal_receipt(
                conn,
                plan_id=claim.plan_id,
                domain_id=claim.domain_id,
                terminal_mode=terminal_mode,
                attempt=self._max_attempts,
                completed_at=now,
            )
            conn.execute(
                f"DELETE FROM {LEASE_TABLE} WHERE plan_id = ? AND domain_id = ? "
                "AND lease_token = ?",
                (claim.plan_id, claim.domain_id, claim.lease_token),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def _verify_split_winner(
        self,
        conn: sqlite3.Connection,
        claim: Claim,
        children: Sequence[QueryNode],
        *,
        reason: SplitReason,
    ) -> None:
        """Authenticate every persisted SPLIT child row, not only IDs."""
        expected = {
            child.domain_id: child for child in children
        }
        rows = conn.execute(
            f"SELECT * FROM {NODE_TABLE} WHERE plan_id = ? AND parent_domain_id = ?",
            (claim.plan_id, claim.domain_id),
        ).fetchall()
        if {str(row["domain_id"]) for row in rows} != set(expected):
            raise PairEventV2Error("split winner children do not match candidate")
        reconstructed: list[QueryDomain] = []
        for row in rows:
            record = QueryNodeRecord(
                plan_id=row["plan_id"],
                domain_id=row["domain_id"],
                start_block=row["start_block"],
                end_block=row["end_block"],
                addresses_json=row["addresses_json"],
                topics_json=row["topics_json"],
                status=row["status"],
                parent_domain_id=row["parent_domain_id"],
                split_reason=row["split_reason"],
                attempt=int(row["attempt"]),
                updated_at=row["updated_at"],
            )
            exp = expected[record.domain_id]
            if record.parent_domain_id != claim.domain_id:
                raise PairEventV2Error("SPLIT child parent_domain_id mismatch")
            if record.split_reason != reason:
                raise PairEventV2Error("SPLIT child split_reason mismatch")
            # Allow legitimate progression PENDING → IN_FLIGHT → AGREED/SPLIT.
            if record.status not in ("PENDING", "IN_FLIGHT", "AGREED", "SPLIT"):
                raise PairEventV2Error(
                    f"SPLIT child has unexpected status {record.status!r}"
                )
            if (
                record.start_block != exp.domain.start_block
                or record.end_block != exp.domain.end_block
                or record.addresses_json
                != _canonical_json(list(exp.domain.addresses))
                or record.topics_json != _canonical_json(list(exp.domain.topics))
            ):
                raise PairEventV2Error("SPLIT child domain fields are not authentic")
            reconstructed.append(
                QueryDomain(
                    start_block=record.start_block,
                    end_block=record.end_block,
                    addresses=tuple(json.loads(record.addresses_json)),
                    topics=tuple(json.loads(record.topics_json)),
                )
            )
        validate_children_partition(claim.node.domain, reconstructed)

    def _op_commit_split(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        claim: Claim,
        children: Sequence[QueryNode],
        reason: SplitReason,
        events: Sequence[EngineEventRecord],
    ) -> None:
        del writer
        # Recompute children from the claimed node — never trust caller partitions alone.
        expected_children = split_node(claim.node, reason=reason)
        validate_children_partition(
            claim.node.domain, [child.domain for child in expected_children]
        )
        if {c.domain_id for c in children} != {c.domain_id for c in expected_children}:
            raise PairEventV2Error(
                "SPLIT children do not match versioned partition of the claim domain"
            )
        canonical_children = expected_children
        now = _now()
        conn.execute("BEGIN IMMEDIATE")
        try:
            status = conn.execute(
                f"SELECT status, split_reason FROM {NODE_TABLE} "
                "WHERE plan_id = ? AND domain_id = ?",
                (claim.plan_id, claim.domain_id),
            ).fetchone()
            # Semantic winner first (works after lease loss).
            if status is not None and status["status"] == "SPLIT":
                if status["split_reason"] != reason:
                    raise PairEventV2Error("SPLIT winner reason disagrees with candidate")
                self._verify_split_winner(
                    conn, claim, canonical_children, reason=reason
                )
                for event in events:
                    self._insert_event(conn, event)
                conn.execute("COMMIT")
                return
            if status is None or status["status"] != "IN_FLIGHT":
                raise _LeaseLostError("cannot split node that is not IN_FLIGHT")
            self._require_lease(conn, claim)
            for event in events:
                self._insert_event(conn, event)
            conn.execute(
                f"UPDATE {NODE_TABLE} SET status = 'SPLIT', split_reason = ?, "
                "updated_at = ? WHERE plan_id = ? AND domain_id = ?",
                (reason, now, claim.plan_id, claim.domain_id),
            )
            for child in canonical_children:
                self._insert_node(conn, child, attempt=0, updated_at=now)
            conn.execute(
                f"DELETE FROM {LEASE_TABLE} WHERE plan_id = ? AND domain_id = ? "
                "AND lease_token = ?",
                (claim.plan_id, claim.domain_id, claim.lease_token),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    # ---- headers / chain / leaves ----

    def _header_from_row(self, row: sqlite3.Row) -> CanonicalHeaderReceiptRecord:
        return CanonicalHeaderReceiptRecord(
            header_receipt_id=row["header_receipt_id"],
            plan_id=row["plan_id"],
            block_number=row["block_number"],
            block_hash=row["block_hash"],
            block_timestamp=row["block_timestamp"],
            primary_provider_org=row["primary_provider_org"],
            secondary_provider_org=row["secondary_provider_org"],
            primary_raw_object_id=row["primary_raw_object_id"],
            secondary_raw_object_id=row["secondary_raw_object_id"],
            primary_acquisition_id=row["primary_acquisition_id"],
            secondary_acquisition_id=row["secondary_acquisition_id"],
            receipt_schema_version=row["receipt_schema_version"],
            completed_at=row["completed_at"],
        )

    def _replay_header_record(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        record: CanonicalHeaderReceiptRecord,
    ) -> tuple[
        CanonicalHeaderReceiptRecord, AuthenticatedEvidence, AuthenticatedEvidence
    ]:
        def pulse() -> None:
            self._service_control_commands(conn, writer)

        request = block_header_request(record.block_number)
        primary = self._authenticate_evidence(
            conn,
            raw_object_id=record.primary_raw_object_id,
            acquisition_id=record.primary_acquisition_id,
            provider_org=record.primary_provider_org,
            request=request,
        )
        secondary = self._authenticate_evidence(
            conn,
            raw_object_id=record.secondary_raw_object_id,
            acquisition_id=record.secondary_acquisition_id,
            provider_org=record.secondary_provider_org,
            request=request,
        )
        payloads = (
            _load_authenticated_rpc(
                primary,
                request,
                max_bytes=self._max_body_bytes,
                raw_root=self._raw_root,
                pulse=pulse,
            ),
            _load_authenticated_rpc(
                secondary,
                request,
                max_bytes=self._max_body_bytes,
                raw_root=self._raw_root,
                pulse=pulse,
            ),
        )
        parsed: list[tuple[int, str, int]] = []
        for payload in payloads:
            if payload.get("error") is not None or not isinstance(
                payload.get("result"), Mapping
            ):
                raise PairEventV2Error("canonical header evidence is not successful")
            header = payload["result"]
            try:
                parsed.append(
                    (
                        _hex_quantity(
                            _require(header, "number", label="header"), label="number"
                        ),
                        _hex_bytes(
                            _require(header, "hash", label="header"), 32, label="hash"
                        ),
                        _hex_quantity(
                            _require(header, "timestamp", label="header"),
                            label="timestamp",
                        ),
                    )
                )
            except UniswapV2IngestionError as exc:
                raise PairEventV2Error("canonical header fields are malformed") from exc
        expected = (record.block_number, record.block_hash, record.block_timestamp)
        if parsed != [expected, expected]:
            raise PairEventV2Error("canonical header raw replay disagrees with receipt")
        return record, primary, secondary

    def _op_load_header(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
        block_number: int,
        primary_org: str,
        secondary_org: str,
    ) -> Any:
        rows = conn.execute(
            f"SELECT * FROM {HEADER_TABLE} WHERE plan_id = ? AND block_number = ?",
            (plan_id, block_number),
        ).fetchall()
        if not rows:
            return None
        if len(rows) != 1:
            raise PairEventV2Error("multiple canonical headers exist for one plan block")
        record = self._header_from_row(rows[0])
        if (
            record.primary_provider_org != normalize_provider_org(primary_org)
            or record.secondary_provider_org != normalize_provider_org(secondary_org)
        ):
            raise PairEventV2Error("cached header provider binding mismatch")
        return self._replay_header_record(conn, writer, record)

    def _op_store_header(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        record: CanonicalHeaderReceiptRecord,
    ) -> CanonicalHeaderReceiptRecord:
        self._replay_header_record(conn, writer, record)
        winner_row: sqlite3.Row | None = None
        conn.execute("BEGIN IMMEDIATE")
        try:
            rows = conn.execute(
                f"SELECT * FROM {HEADER_TABLE} WHERE plan_id = ? AND block_number = ?",
                (record.plan_id, record.block_number),
            ).fetchall()
            if rows:
                if len(rows) != 1:
                    raise PairEventV2Error(
                        "multiple canonical headers exist for plan block"
                    )
                winner_row = rows[0]
                conn.execute("COMMIT")
            else:
                conn.execute(
                    f"INSERT INTO {HEADER_TABLE} (header_receipt_id, plan_id, "
                    "block_number, block_hash, block_timestamp, primary_provider_org, "
                    "secondary_provider_org, primary_raw_object_id, "
                    "secondary_raw_object_id, primary_acquisition_id, "
                    "secondary_acquisition_id, receipt_schema_version, completed_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        record.header_receipt_id,
                        record.plan_id,
                        record.block_number,
                        record.block_hash,
                        record.block_timestamp,
                        record.primary_provider_org,
                        record.secondary_provider_org,
                        record.primary_raw_object_id,
                        record.secondary_raw_object_id,
                        record.primary_acquisition_id,
                        record.secondary_acquisition_id,
                        RECEIPT_SCHEMA_VERSION,
                        record.completed_at or _now(),
                    ),
                )
                conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        if winner_row is None:
            return record
        winner = self._header_from_row(winner_row)
        self._replay_header_record(conn, writer, winner)
        if (
            winner.plan_id,
            winner.block_number,
            winner.block_hash,
            winner.block_timestamp,
            winner.primary_provider_org,
            winner.secondary_provider_org,
        ) != (
            record.plan_id,
            record.block_number,
            record.block_hash,
            record.block_timestamp,
            record.primary_provider_org,
            record.secondary_provider_org,
        ):
            raise PairEventV2Error("conflicting canonical header for plan block")
        return winner

    def _chain_from_row(self, row: sqlite3.Row) -> ChainIdentityReceipt:
        return ChainIdentityReceipt(
            chain_identity_receipt_id=row["chain_identity_receipt_id"],
            plan_id=row["plan_id"],
            chain_id=row["chain_id"],
            primary_provider_org=row["primary_provider_org"],
            secondary_provider_org=row["secondary_provider_org"],
            primary_raw_object_id=row["primary_raw_object_id"],
            secondary_raw_object_id=row["secondary_raw_object_id"],
            primary_acquisition_id=row["primary_acquisition_id"],
            secondary_acquisition_id=row["secondary_acquisition_id"],
            schema_version=row["schema_version"],
            completed_at=row["completed_at"],
        )

    def _replay_chain_record(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        record: ChainIdentityReceipt,
    ) -> tuple[ChainIdentityReceipt, AuthenticatedEvidence, AuthenticatedEvidence]:
        def pulse() -> None:
            self._service_control_commands(conn, writer)

        request = chain_id_request()
        primary = self._authenticate_evidence(
            conn,
            raw_object_id=record.primary_raw_object_id,
            acquisition_id=record.primary_acquisition_id,
            provider_org=record.primary_provider_org,
            request=request,
        )
        secondary = self._authenticate_evidence(
            conn,
            raw_object_id=record.secondary_raw_object_id,
            acquisition_id=record.secondary_acquisition_id,
            provider_org=record.secondary_provider_org,
            request=request,
        )
        payloads = (
            _load_authenticated_rpc(
                primary,
                request,
                max_bytes=self._max_body_bytes,
                raw_root=self._raw_root,
                pulse=pulse,
            ),
            _load_authenticated_rpc(
                secondary,
                request,
                max_bytes=self._max_body_bytes,
                raw_root=self._raw_root,
                pulse=pulse,
            ),
        )
        try:
            chain_ids = tuple(
                _hex_quantity(payload.get("result"), label="chainId")
                if payload.get("error") is None
                else -1
                for payload in payloads
            )
        except UniswapV2IngestionError as exc:
            raise PairEventV2Error("chain identity raw result is malformed") from exc
        if chain_ids != (1, 1) or chain_ids != (record.chain_id, record.chain_id):
            raise PairEventV2Error("chain identity raw replay is not dual mainnet")
        return record, primary, secondary

    def _op_load_chain_identity(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
        primary_org: str,
        secondary_org: str,
    ) -> Any:
        rows = conn.execute(
            f"SELECT * FROM {CHAIN_IDENTITY_TABLE} WHERE plan_id = ?", (plan_id,)
        ).fetchall()
        if not rows:
            return None
        if len(rows) != 1:
            raise PairEventV2Error("plan has multiple chain identity receipts")
        record = self._chain_from_row(rows[0])
        if (
            record.primary_provider_org != normalize_provider_org(primary_org)
            or record.secondary_provider_org != normalize_provider_org(secondary_org)
        ):
            raise PairEventV2Error("cached chain provider binding mismatch")
        return self._replay_chain_record(conn, writer, record)

    def _op_store_chain_identity(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        record: ChainIdentityReceipt,
    ) -> ChainIdentityReceipt:
        self._replay_chain_record(conn, writer, record)
        winner_row: sqlite3.Row | None = None
        conn.execute("BEGIN IMMEDIATE")
        try:
            rows = conn.execute(
                f"SELECT * FROM {CHAIN_IDENTITY_TABLE} WHERE plan_id = ?",
                (record.plan_id,),
            ).fetchall()
            if rows:
                if len(rows) != 1:
                    raise PairEventV2Error("plan has multiple chain identity receipts")
                winner_row = rows[0]
                conn.execute("COMMIT")
            else:
                conn.execute(
                    f"INSERT INTO {CHAIN_IDENTITY_TABLE} ("
                    + ",".join(CHAIN_IDENTITY_RECORD_COLUMNS)
                    + ") VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        record.chain_identity_receipt_id,
                        record.plan_id,
                        record.chain_id,
                        record.primary_provider_org,
                        record.secondary_provider_org,
                        record.primary_raw_object_id,
                        record.secondary_raw_object_id,
                        record.primary_acquisition_id,
                        record.secondary_acquisition_id,
                        record.schema_version,
                        record.completed_at or _now(),
                    ),
                )
                conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        if winner_row is None:
            return record
        winner = self._chain_from_row(winner_row)
        self._replay_chain_record(conn, writer, winner)
        if (
            winner.plan_id,
            winner.chain_id,
            winner.primary_provider_org,
            winner.secondary_provider_org,
        ) != (
            record.plan_id,
            record.chain_id,
            record.primary_provider_org,
            record.secondary_provider_org,
        ):
            raise PairEventV2Error("conflicting chain identity receipt for plan")
        return winner

    def _leaf_from_row(self, row: sqlite3.Row) -> LeafReceiptRecord:
        return LeafReceiptRecord(
            leaf_receipt_id=row["leaf_receipt_id"],
            plan_id=row["plan_id"],
            domain_id=row["domain_id"],
            start_block=row["start_block"],
            end_block=row["end_block"],
            addresses=tuple(json.loads(row["addresses_json"])),
            topics=tuple(json.loads(row["topics_json"])),
            primary_provider_org=row["primary_provider_org"],
            secondary_provider_org=row["secondary_provider_org"],
            primary_logs_raw_object_id=row["primary_logs_raw_object_id"],
            secondary_logs_raw_object_id=row["secondary_logs_raw_object_id"],
            primary_logs_acquisition_id=row["primary_logs_acquisition_id"],
            secondary_logs_acquisition_id=row["secondary_logs_acquisition_id"],
            log_count=row["log_count"],
            log_identity_sha256=row["log_identity_sha256"],
            canonical_header_receipt_ids=tuple(
                json.loads(row["canonical_header_receipt_ids_json"])
            ),
            log_identity_version=row["log_identity_version"],
            receipt_schema_version=row["receipt_schema_version"],
            reconciliation_status=row["reconciliation_status"],
            completed_at=row["completed_at"],
        )

    def _replay_leaf(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        leaf: LeafReceiptRecord,
    ) -> tuple[Any, ...]:
        def pulse() -> None:
            self._service_control_commands(conn, writer)

        domain = QueryDomain(
            start_block=leaf.start_block,
            end_block=leaf.end_block,
            addresses=leaf.addresses,
            topics=leaf.topics,
        )
        request = request_for_domain(domain)
        plan_row = conn.execute(
            f"SELECT * FROM {PLAN_TABLE} WHERE plan_id = ?", (leaf.plan_id,)
        ).fetchone()
        if plan_row is None:
            raise PairEventV2Error("leaf references a missing plan")
        authenticated_plan = PlanRecord(
            plan_id=plan_row["plan_id"],
            registry_dataset_id=plan_row["registry_dataset_id"],
            identity_payload_json=plan_row["identity_payload_json"],
            event_provider_orgs_json=plan_row["event_provider_orgs_json"],
            metadata_provider_orgs_json=plan_row["metadata_provider_orgs_json"],
            root_block_size=plan_row["root_block_size"],
            initial_cohort_size=plan_row["initial_cohort_size"],
            deployment_block=plan_row["deployment_block"],
            cutoff_block=plan_row["cutoff_block"],
            plan_schema_version=plan_row["plan_schema_version"],
            created_at=plan_row["created_at"],
        )
        if tuple(json.loads(authenticated_plan.event_provider_orgs_json)) != (
            leaf.primary_provider_org,
            leaf.secondary_provider_org,
        ):
            raise PairEventV2Error("leaf providers do not match authenticated plan")
        primary = self._authenticate_evidence(
            conn,
            raw_object_id=leaf.primary_logs_raw_object_id,
            acquisition_id=leaf.primary_logs_acquisition_id,
            provider_org=leaf.primary_provider_org,
            request=request,
        )
        secondary = self._authenticate_evidence(
            conn,
            raw_object_id=leaf.secondary_logs_raw_object_id,
            acquisition_id=leaf.secondary_logs_acquisition_id,
            provider_org=leaf.secondary_provider_org,
            request=request,
        )
        payloads = (
            _load_authenticated_rpc(
                primary,
                request,
                max_bytes=self._max_body_bytes,
                raw_root=self._raw_root,
                pulse=pulse,
            ),
            _load_authenticated_rpc(
                secondary,
                request,
                max_bytes=self._max_body_bytes,
                raw_root=self._raw_root,
                pulse=pulse,
            ),
        )
        results: list[list[Any]] = []
        for payload in payloads:
            result = payload.get("result")
            if payload.get("error") is not None or not isinstance(result, list):
                raise PairEventV2Error("leaf raw replay is not a successful log result")
            results.append(result)
        identities, digest = reconcile_log_sets_v2(results[0], results[1], domain)
        if leaf.log_count != len(identities) or leaf.log_identity_sha256 != digest:
            raise PairEventV2Error("leaf count/digest disagrees with exact raw replay")

        required_blocks = {domain.end_block}
        required_blocks.update(identity.block_number for identity in identities)
        headers_by_block: dict[int, CanonicalHeaderReceiptRecord] = {}
        for header_id in leaf.canonical_header_receipt_ids:
            row = conn.execute(
                f"SELECT * FROM {HEADER_TABLE} WHERE plan_id = ? "
                "AND header_receipt_id = ?",
                (leaf.plan_id, header_id),
            ).fetchone()
            if row is None:
                raise PairEventV2Error("leaf winner references a missing header")
            record = self._header_from_row(row)
            loaded = self._op_load_header(
                conn,
                writer,
                plan_id=leaf.plan_id,
                block_number=record.block_number,
                primary_org=leaf.primary_provider_org,
                secondary_org=leaf.secondary_provider_org,
            )
            if loaded is None or loaded[0].header_receipt_id != record.header_receipt_id:
                raise PairEventV2Error("leaf header is not the unique canonical winner")
            if record.block_number in headers_by_block:
                raise PairEventV2Error("leaf references duplicate headers for one block")
            headers_by_block[record.block_number] = record
        if set(headers_by_block) != required_blocks:
            raise PairEventV2Error(
                "leaf header dependencies are not the exact required set"
            )
        for identity in identities:
            if headers_by_block[identity.block_number].block_hash != identity.block_hash:
                raise PairEventV2Error(
                    "leaf log block_hash is not canonical-header bound"
                )
        derived = make_leaf_receipt_record(
            plan_id=leaf.plan_id,
            domain=domain,
            log_identity_sha256=digest,
            primary_provider_org=leaf.primary_provider_org,
            secondary_provider_org=leaf.secondary_provider_org,
            primary_logs_raw_object_id=primary.raw_object_id,
            secondary_logs_raw_object_id=secondary.raw_object_id,
            primary_logs_acquisition_id=primary.acquisition_id,
            secondary_logs_acquisition_id=secondary.acquisition_id,
            log_count=len(identities),
            canonical_header_receipt_ids=tuple(leaf.canonical_header_receipt_ids),
            completed_at=leaf.completed_at,
        )
        if replace(derived, completed_at="") != replace(leaf, completed_at=""):
            raise PairEventV2Error(
                "leaf fields are not derived from authenticated replay"
            )
        return (
            leaf.plan_id,
            leaf.domain_id,
            leaf.start_block,
            leaf.end_block,
            leaf.addresses,
            leaf.topics,
            leaf.primary_provider_org,
            leaf.secondary_provider_org,
            len(identities),
            digest,
            tuple(
                (
                    n,
                    headers_by_block[n].block_hash,
                    headers_by_block[n].block_timestamp,
                )
                for n in sorted(headers_by_block)
            ),
        )

    def _op_commit_agreed(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        claim: Claim,
        leaf_kwargs: Mapping[str, Any],
    ) -> str:
        leaf = make_leaf_receipt_record(**dict(leaf_kwargs), completed_at=_now())
        # Bind candidate to the claim's plan/domain before any mutation.
        if leaf.plan_id != claim.plan_id or leaf.domain_id != claim.domain_id:
            raise PairEventV2Error("AGREED leaf does not match claim plan/domain")
        if (
            leaf.start_block != claim.node.domain.start_block
            or leaf.end_block != claim.node.domain.end_block
            or leaf.addresses != claim.node.domain.addresses
            or leaf.topics != claim.node.domain.topics
        ):
            raise PairEventV2Error("AGREED leaf domain fields do not match claim node")
        candidate_semantics = self._replay_leaf(conn, writer, leaf)
        winner_row: sqlite3.Row | None = None
        conn.execute("BEGIN IMMEDIATE")
        try:
            status = conn.execute(
                f"SELECT status FROM {NODE_TABLE} WHERE plan_id = ? AND domain_id = ?",
                (claim.plan_id, claim.domain_id),
            ).fetchone()
            # Semantic winner verification deliberately precedes lease validation.
            if status is not None and status["status"] == "AGREED":
                winner_row = conn.execute(
                    f"SELECT * FROM {LEAF_TABLE} WHERE plan_id = ? AND domain_id = ?",
                    (claim.plan_id, claim.domain_id),
                ).fetchone()
                if winner_row is None:
                    raise PairEventV2Error("AGREED node has no leaf winner")
                conn.execute("COMMIT")
            elif status is None or status["status"] != "IN_FLIGHT":
                raise _LeaseLostError("node cannot become AGREED from current state")
            else:
                self._require_lease(conn, claim)
                conn.execute(
                    f"INSERT INTO {LEAF_TABLE} (leaf_receipt_id, plan_id, domain_id, "
                    "start_block, end_block, addresses_json, topics_json, "
                    "primary_provider_org, secondary_provider_org, "
                    "primary_logs_raw_object_id, secondary_logs_raw_object_id, "
                    "primary_logs_acquisition_id, secondary_logs_acquisition_id, "
                    "log_count, log_identity_sha256, canonical_header_receipt_ids_json, "
                    "log_identity_version, receipt_schema_version, "
                    "reconciliation_status, completed_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        leaf.leaf_receipt_id,
                        leaf.plan_id,
                        leaf.domain_id,
                        leaf.start_block,
                        leaf.end_block,
                        leaf.addresses_json,
                        leaf.topics_json,
                        leaf.primary_provider_org,
                        leaf.secondary_provider_org,
                        leaf.primary_logs_raw_object_id,
                        leaf.secondary_logs_raw_object_id,
                        leaf.primary_logs_acquisition_id,
                        leaf.secondary_logs_acquisition_id,
                        leaf.log_count,
                        leaf.log_identity_sha256,
                        leaf.canonical_header_receipt_ids_json,
                        LOG_IDENTITY_VERSION,
                        RECEIPT_SCHEMA_VERSION,
                        "AGREED",
                        leaf.completed_at,
                    ),
                )
                for header_id in leaf.canonical_header_receipt_ids:
                    conn.execute(
                        f"INSERT INTO {DEP_TABLE} "
                        "(plan_id, leaf_receipt_id, header_receipt_id) VALUES (?,?,?)",
                        (claim.plan_id, leaf.leaf_receipt_id, header_id),
                    )
                conn.execute(
                    f"UPDATE {NODE_TABLE} SET status = 'AGREED', updated_at = ? "
                    "WHERE plan_id = ? AND domain_id = ?",
                    (_now(), claim.plan_id, claim.domain_id),
                )
                conn.execute(
                    f"DELETE FROM {LEASE_TABLE} WHERE plan_id = ? AND domain_id = ? "
                    "AND lease_token = ?",
                    (claim.plan_id, claim.domain_id, claim.lease_token),
                )
                conn.execute("COMMIT")
                return leaf.leaf_receipt_id
        except Exception:
            conn.execute("ROLLBACK")
            raise

        winner = self._leaf_from_row(winner_row)
        winner_semantics = self._replay_leaf(conn, writer, winner)
        if winner_semantics != candidate_semantics:
            raise PairEventV2Error("duplicate worker lost: AGREED leaf semantics differ")
        if winner.leaf_receipt_id != leaf.leaf_receipt_id:
            # Same semantics can still share identity when raw ids match; if ids
            # differ after semantic equality, reject.
            if winner_semantics != candidate_semantics:
                raise PairEventV2Error("duplicate worker lost: leaf id conflict")
        return winner.leaf_receipt_id

    def _op_resolve_winner(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        claim: Claim,
        leaf_kwargs: Mapping[str, Any] | None,
        split_reason: SplitReason | None = None,
        terminal_mode: str | None = None,
    ) -> str:
        """Authenticate AGREED/SPLIT/terminal winner semantics for the claim.

        ``terminal_mode`` is required when the losing worker had no comparable
        leaf/children (unsplittable or max-attempt terminal). Accepted terminal
        winners are PENDING nodes at the retry limit.
        """
        status = conn.execute(
            f"SELECT status, split_reason, attempt FROM {NODE_TABLE} "
            "WHERE plan_id = ? AND domain_id = ?",
            (claim.plan_id, claim.domain_id),
        ).fetchone()
        if status is None:
            raise PairEventV2Error("resolve_winner: node missing")
        state = status["status"]
        if state == "AGREED":
            row = conn.execute(
                f"SELECT * FROM {LEAF_TABLE} WHERE plan_id = ? AND domain_id = ?",
                (claim.plan_id, claim.domain_id),
            ).fetchone()
            if row is None:
                raise PairEventV2Error("AGREED node missing leaf")
            winner = self._leaf_from_row(row)
            winner_semantics = self._replay_leaf(conn, writer, winner)
            if leaf_kwargs is None:
                raise PairEventV2Error(
                    "lost-lease AGREED resolution requires candidate leaf_kwargs"
                )
            candidate = make_leaf_receipt_record(**dict(leaf_kwargs))
            if (
                candidate.plan_id != claim.plan_id
                or candidate.domain_id != claim.domain_id
            ):
                raise PairEventV2Error("candidate leaf is not bound to the claim")
            if self._replay_leaf(conn, writer, candidate) != winner_semantics:
                raise PairEventV2Error("lost-lease winner semantics disagree")
            return winner.leaf_receipt_id
        if state == "SPLIT":
            if split_reason is None:
                raise PairEventV2Error(
                    "lost-lease SPLIT resolution requires candidate split_reason"
                )
            if status["split_reason"] != split_reason:
                raise PairEventV2Error("SPLIT winner reason disagrees with candidate")
            expected = split_node(claim.node, reason=split_reason)
            self._verify_split_winner(conn, claim, expected, reason=split_reason)
            return "split_winner"
        if state == "PENDING":
            attempt = int(status["attempt"])
            receipt = conn.execute(
                f"SELECT * FROM {TERMINAL_RECEIPT_TABLE} "
                "WHERE plan_id = ? AND domain_id = ?",
                (claim.plan_id, claim.domain_id),
            ).fetchone()
            if attempt < self._max_attempts:
                if receipt is not None:
                    raise PairEventV2Error(
                        "terminal receipt present on non-terminal-attempt node"
                    )
                return "pending_after_loss"
            # Terminal-attempt node: must authenticate durable terminal identity.
            if terminal_mode is None:
                raise PairEventV2Error(
                    "terminal-attempt PENDING node requires candidate terminal_mode"
                )
            if str(terminal_mode) not in TERMINAL_MODES:
                raise PairEventV2Error(
                    f"terminal_mode not in TERMINAL_MODES: {terminal_mode!r}"
                )
            if receipt is None:
                raise PairEventV2Error(
                    "terminal winner missing durable terminal_receipt identity"
                )
            winner_mode = str(receipt["terminal_mode"])
            receipt_attempt = int(receipt["attempt"])
            if receipt_attempt != attempt or receipt_attempt != self._max_attempts:
                raise PairEventV2Error(
                    "terminal receipt attempt must equal node attempt and max_attempts"
                )
            if winner_mode != str(terminal_mode):
                raise PairEventV2Error(
                    "terminal winner mode mismatch: "
                    f"winner {winner_mode!r} != candidate {terminal_mode!r}"
                )
            expected_id = compute_terminal_receipt_id(
                plan_id=claim.plan_id,
                domain_id=claim.domain_id,
                terminal_mode=winner_mode,
                attempt=receipt_attempt,
            )
            if str(receipt["terminal_receipt_id"]) != expected_id:
                raise PairEventV2Error(
                    "terminal_receipt_id does not match durable identity"
                )
            if str(receipt["schema_version"]) != TERMINAL_RECEIPT_SCHEMA_VERSION:
                raise PairEventV2Error("terminal receipt schema version mismatch")
            return f"terminal:{winner_mode}"
        if state == "IN_FLIGHT":
            if terminal_mode is not None:
                # Another worker holds the lease; terminal candidate not yet applied.
                return "lease_lost"
            return "lease_lost"
        raise PairEventV2Error(f"resolve_winner: unexpected status {state!r}")

    def _op_count_by_status(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
    ) -> dict[str, int]:
        del writer
        rows = conn.execute(
            f"SELECT status, COUNT(*) AS n FROM {NODE_TABLE} WHERE plan_id = ? "
            "GROUP BY status",
            (plan_id,),
        ).fetchall()
        result = {str(row["status"]): int(row["n"]) for row in rows}
        blocked = conn.execute(
            f"SELECT COUNT(*) FROM {NODE_TABLE} WHERE plan_id = ? AND status = 'PENDING' "
            "AND attempt >= ?",
            (plan_id, self._max_attempts),
        ).fetchone()[0]
        result["TERMINAL_BLOCKER"] = int(blocked)
        return result


# ---------------------------------------------------------------------------
# Failure routing helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _FailureFact:
    failure_class: FailureClass
    provider_org: str | None
    detail: Mapping[str, Any]


class _PairFailure(Exception):
    def __init__(self, facts: Sequence[_FailureFact]) -> None:
        super().__init__(facts[0].failure_class if facts else FailureClass.INTERNAL)
        self.facts = tuple(facts)

    @property
    def route(self) -> FailureClass:
        """Deterministic mixed-failure precedence (transport before size, etc.)."""
        classes = {fact.failure_class for fact in self.facts}
        if not classes:
            return FailureClass.INTERNAL
        order = {name: index for index, name in enumerate(FAILURE_ROUTE_PRECEDENCE)}
        return min(
            classes,
            key=lambda item: order.get(item.value, len(order)),
        )


@dataclass(slots=True)
class _ActiveWork:
    """Lease-token-keyed active claim handle for heartbeats."""

    claim: Claim
    lost: threading.Event = field(default_factory=threading.Event)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class PairEventV2Engine:
    """Bounded concurrent engine with claim-bound terminals and chain prerequisite."""

    def __init__(
        self,
        config: EngineConfig,
        *,
        primary_client: httpx.Client | None = None,
        secondary_client: httpx.Client | None = None,
    ) -> None:
        self.config = config
        self._phase = EnginePhase.CONSTRUCTED
        self._owns_primary = primary_client is None
        self._owns_secondary = secondary_client is None
        timeout = httpx.Timeout(config.http_timeout_seconds)
        self._primary_client = primary_client or httpx.Client(timeout=timeout)
        self._secondary_client = secondary_client or httpx.Client(timeout=timeout)
        self._primary_limiter = _AdaptiveLimiter(config.max_in_flight_per_provider)
        self._secondary_limiter = _AdaptiveLimiter(config.max_in_flight_per_provider)
        self._spool_capacity = threading.BoundedSemaphore(config.max_spool_files)
        self._primary_worker = NetworkWorker(
            client=self._primary_client,
            rpc_url=config.primary_rpc_url,
            provider_org=config.primary_org,
            bucket=_TokenBucket(
                rate=config.requests_per_second,
                capacity=float(config.max_in_flight_per_provider),
            ),
            limiter=self._primary_limiter,
            spool_dir=config.spool_dir,
            spool_capacity=self._spool_capacity,
            max_body_bytes=config.max_body_bytes,
            chunk_bytes=config.spool_chunk_bytes,
            response_drain_deadline_seconds=config.response_drain_deadline_seconds,
        )
        self._secondary_worker = NetworkWorker(
            client=self._secondary_client,
            rpc_url=config.secondary_rpc_url,
            provider_org=config.secondary_org,
            bucket=_TokenBucket(
                rate=config.requests_per_second,
                capacity=float(config.max_in_flight_per_provider),
            ),
            limiter=self._secondary_limiter,
            spool_dir=config.spool_dir,
            spool_capacity=self._spool_capacity,
            max_body_bytes=config.max_body_bytes,
            chunk_bytes=config.spool_chunk_bytes,
            response_drain_deadline_seconds=config.response_drain_deadline_seconds,
        )
        self.coordinator = PersistenceCoordinator(
            db_path=config.receipt_db_path,
            raw_root=config.raw_root,
            spool_dir=config.spool_dir,
            spool_capacity=self._spool_capacity,
            queue_size=config.persistence_queue_size,
            offer_timeout_seconds=config.command_offer_timeout_seconds,
            max_body_bytes=config.max_body_bytes,
            max_attempts=config.max_attempts,
            max_spool_files=config.max_spool_files,
        )
        self._network_executor = ThreadPoolExecutor(
            max_workers=config.max_nodes_in_flight * 2,
            thread_name_prefix="pair-event-v2-network",
        )
        self._node_executor = ThreadPoolExecutor(
            max_workers=config.max_nodes_in_flight,
            thread_name_prefix="pair-event-v2-node",
        )
        self._metrics = EngineMetrics()
        self._metrics_lock = threading.Lock()
        self._stop = threading.Event()
        self._closed = False
        self._plan_id: str | None = None
        # Lease-token-keyed — never domain_id.
        self._active_by_token: dict[str, _ActiveWork] = {}
        self._active_lock = threading.Lock()
        self._header_cache: OrderedDict[int, str] = OrderedDict()
        self._header_cache_lock = threading.Lock()
        self._header_stripes = tuple(threading.Lock() for _ in range(257))
        self._heartbeat_stop = threading.Event()
        self._heartbeat = threading.Thread(
            target=self._heartbeat_loop,
            name="pair-event-v2-lease-heartbeat",
            daemon=False,
        )
        self._heartbeat.start()

    @property
    def phase(self) -> EnginePhase:
        return self._phase

    @property
    def metrics(self) -> EngineMetrics:
        with self._metrics_lock:
            snapshot = self._metrics.snapshot()
        snapshot.persistence_queue_high_water = self.coordinator.queue_high_water
        snapshot.lease_expiries = self.coordinator.lease_expiries
        (
            snapshot.writer_operations,
            snapshot.writer_latency_seconds,
            snapshot.writer_latency_max_seconds,
        ) = self.coordinator.writer_metrics
        return snapshot

    def _add_metrics(self, **values: int | float) -> None:
        with self._metrics_lock:
            for key, value in values.items():
                setattr(self._metrics, key, getattr(self._metrics, key) + value)

    def _set_error(self, detail: str) -> None:
        with self._metrics_lock:
            self._metrics.last_error = detail

    def request_stop(self) -> None:
        self._stop.set()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.request_stop()
        self._node_executor.shutdown(wait=True, cancel_futures=False)
        self._network_executor.shutdown(wait=True, cancel_futures=False)
        self._heartbeat_stop.set()
        self._heartbeat.join()
        self.coordinator.close()
        if self._owns_primary:
            self._primary_client.close()
        if self._owns_secondary:
            self._secondary_client.close()

    def _heartbeat_loop(self) -> None:
        interval = max(0.001, self.config.lease_ttl_seconds / 3.0)
        while not self._heartbeat_stop.wait(interval):
            with self._active_lock:
                works = tuple(self._active_by_token.values())
            for work in works:
                try:
                    renewed = self.coordinator.renew_lease(
                        work.claim,
                        lease_ttl_seconds=self.config.lease_ttl_seconds,
                    )
                except Exception:
                    renewed = False
                if not renewed:
                    work.lost.set()

    def _lease_lost(self, claim: Claim) -> bool:
        with self._active_lock:
            work = self._active_by_token.get(claim.lease_token)
            return work is not None and work.lost.is_set()

    def _require_chain_ready(self) -> None:
        if self._phase != EnginePhase.CHAIN_AUTHENTICATED:
            raise PairEventV2Error(
                "chain authentication is a prerequisite before acquisition work"
            )
        if self._plan_id is None:
            raise PairEventV2Error("plan is not initialized")

    def execution_policy_identity(self, plan_id: str) -> dict[str, Any]:
        """Immutable authority-affecting settings (no URLs, keys, or worker IDs).

        ``plan_id`` is part of the identity so identical settings cannot collide
        across distinct plans.
        """
        cfg = self.config
        return {
            "backoff_base_seconds": cfg.backoff_base_seconds,
            "backoff_max_seconds": cfg.backoff_max_seconds,
            "event_provider_orgs": list(cfg.plan_config.event_provider_orgs),
            "lease_ttl_seconds": cfg.lease_ttl_seconds,
            "max_attempts": cfg.max_attempts,
            "max_body_bytes": cfg.max_body_bytes,
            "max_in_flight_per_provider": cfg.max_in_flight_per_provider,
            "max_log_count": cfg.max_log_count,
            "max_nodes_in_flight": cfg.max_nodes_in_flight,
            "max_spool_files": cfg.max_spool_files,
            "persistence_queue_size": cfg.persistence_queue_size,
            "plan_id": plan_id,
            "primary_org": cfg.primary_org,
            "command_offer_timeout_seconds": cfg.command_offer_timeout_seconds,
            "http_timeout_seconds": cfg.http_timeout_seconds,
            "requests_per_second": cfg.requests_per_second,
            "response_drain_deadline_seconds": cfg.response_drain_deadline_seconds,
            "schema_version": EXECUTION_POLICY_SCHEMA_VERSION,
            "secondary_org": cfg.secondary_org,
            "spool_chunk_bytes": cfg.spool_chunk_bytes,
        }

    def initialize(self, pools: Sequence[RegistryPoolBirth]) -> AcquisitionPlanV2:
        """Insert plan + roots + execution policy. Does not claim work."""
        plan = build_acquisition_plan_v2(pools, self.config.plan_config)
        self.coordinator.initialize_plan(
            plan, execution_policy=self.execution_policy_identity(plan.plan_id)
        )
        self._plan_id = plan.plan_id
        self._phase = EnginePhase.PLAN_INITIALIZED
        return plan

    def authenticate_chain(self) -> ChainIdentityReceipt:
        """Prerequisite: dual mainnet chain identity for the plan (cached once)."""
        if self._phase == EnginePhase.CONSTRUCTED or self._plan_id is None:
            raise PairEventV2Error("initialize() is required before chain authentication")
        if self._phase == EnginePhase.CHAIN_AUTHENTICATED:
            cached = self.coordinator.load_chain_identity(
                plan_id=self._plan_id,
                primary_org=self.config.primary_org,
                secondary_org=self.config.secondary_org,
            )
            if cached is None:
                raise PairEventV2Error("chain phase set but receipt missing")
            return cached[0]
        record = self._fetch_and_store_chain(self._plan_id)
        self._phase = EnginePhase.CHAIN_AUTHENTICATED
        return record

    def _fetch_and_store_chain(self, plan_id: str) -> ChainIdentityReceipt:
        request = chain_id_request()
        try:
            cached = self.coordinator.load_chain_identity(
                plan_id=plan_id,
                primary_org=self.config.primary_org,
                secondary_org=self.config.secondary_org,
            )
        except PairEventV2Error as exc:
            self.coordinator.record_events(
                (
                    make_engine_event_record(
                        plan_id=plan_id,
                        domain_id=None,
                        attempt=0,
                        event_kind="terminal_blocker",
                        failure_class=FailureClass.AUTHENTICATION,
                        decision="terminal",
                        request=request,
                        detail={"phase": "cached_chain_identity_load"},
                    ),
                )
            )
            raise PairEventV2Error("cached chain identity load failed") from exc
        if cached is not None:
            record, p_ev, s_ev = cached
            for evidence in (p_ev, s_ev):
                payload = _load_authenticated_rpc(
                    evidence,
                    request,
                    max_bytes=self.config.max_body_bytes,
                    raw_root=self.config.raw_root,
                )
                if (
                    _hex_quantity(payload.get("result"), label="chainId")
                    != 1
                ):
                    raise PairEventV2Error("cached chain evidence is not dual mainnet")
            return record

        last_failure: _PairFailure | None = None
        for attempt in range(self.config.max_attempts):
            try:
                pair = self._dual_fetch(request)
                primary, secondary = self._inspect_pair(pair, request)
                primary_id = _hex_quantity(
                    primary.get("result"), label="primary chainId"
                )
                secondary_id = _hex_quantity(
                    secondary.get("result"), label="secondary chainId"
                )
                if primary_id != 1 or secondary_id != 1:
                    raise _PairFailure(
                        [
                            _FailureFact(
                                FailureClass.AUTHENTICATION,
                                None,
                                {"expected_chain_id": 1},
                            )
                        ]
                    )
                p_ev = pair[0].evidence
                s_ev = pair[1].evidence
                if p_ev is None or s_ev is None:
                    raise _PairFailure(
                        [_FailureFact(FailureClass.PERSISTENCE, None, {})]
                    )
                record = ChainIdentityReceipt(
                    chain_identity_receipt_id=compute_chain_identity_receipt_id(
                        plan_id=plan_id,
                        chain_id=1,
                        primary_provider_org=self.config.primary_org,
                        secondary_provider_org=self.config.secondary_org,
                        primary_raw_object_id=p_ev.raw_object_id,
                        secondary_raw_object_id=s_ev.raw_object_id,
                        primary_acquisition_id=p_ev.acquisition_id,
                        secondary_acquisition_id=s_ev.acquisition_id,
                    ),
                    plan_id=plan_id,
                    chain_id=1,
                    primary_provider_org=self.config.primary_org,
                    secondary_provider_org=self.config.secondary_org,
                    primary_raw_object_id=p_ev.raw_object_id,
                    secondary_raw_object_id=s_ev.raw_object_id,
                    primary_acquisition_id=p_ev.acquisition_id,
                    secondary_acquisition_id=s_ev.acquisition_id,
                    completed_at=_now(),
                )
                return self.coordinator.store_chain_identity(record)
            except _PairFailure as failure:
                last_failure = failure
                if failure.route == FailureClass.HTTP_429:
                    for fact in failure.facts:
                        if fact.failure_class != FailureClass.HTTP_429:
                            continue
                        if fact.provider_org == self.config.primary_org:
                            self._primary_limiter.on_429()
                        elif fact.provider_org == self.config.secondary_org:
                            self._secondary_limiter.on_429()
                    self._add_metrics(http_429=1)
                events = self._failure_events(None, failure, request, plan_id=plan_id)
                terminal = attempt + 1 >= self.config.max_attempts
                decision = make_engine_event_record(
                    plan_id=plan_id,
                    domain_id=None,
                    attempt=attempt,
                    event_kind="terminal_blocker" if terminal else "retry_decision",
                    failure_class=failure.route,
                    decision="terminal" if terminal else "retry",
                    request=request,
                    detail={"phase": "chain_identity"},
                )
                self.coordinator.record_events((*events, decision))
                if terminal:
                    break
                delay = min(
                    self.config.backoff_max_seconds,
                    self.config.backoff_base_seconds * (2**attempt),
                ) * random.uniform(0.5, 1.5)
                self._stop.wait(min(delay, self.config.backoff_max_seconds))
        raise PairEventV2Error(
            f"dual mainnet authentication failed: {last_failure.route if last_failure else 'unknown'}"
        )

    def _dual_fetch(
        self, request: Mapping[str, Any]
    ) -> tuple[PersistedEnvelope, PersistedEnvelope]:
        primary_future = self._network_executor.submit(
            self._primary_worker.fetch, request
        )
        secondary_future = self._network_executor.submit(
            self._secondary_worker.fetch, request
        )
        descriptors: list[SpoolDescriptor] = []
        offer_facts: list[_FailureFact] = []
        for org, future in (
            (self.config.primary_org, primary_future),
            (self.config.secondary_org, secondary_future),
        ):
            try:
                descriptors.append(future.result())
            except Exception:
                self._stop.set()
                offer_facts.append(
                    _FailureFact(FailureClass.TRANSPORT, org, {"stage": "network_worker"})
                )
        for descriptor in descriptors:
            self._add_metrics(
                response_bytes=descriptor.response_bytes,
                retained_spool_bytes=descriptor.retained_bytes,
                truncated_responses=int(descriptor.truncated),
            )
        persistence_futures: list[Future[PersistedEnvelope]] = []
        for descriptor in descriptors:
            try:
                persistence_futures.append(self.coordinator.persist_async(descriptor))
            except Exception:
                self._stop.set()
                offer_facts.append(
                    _FailureFact(
                        FailureClass.PERSISTENCE,
                        descriptor.provider_org,
                        {"stage": "queue_offer"},
                    )
                )
        persisted: list[PersistedEnvelope] = []
        for future in persistence_futures:
            try:
                persisted.append(future.result())
            except Exception:
                self._stop.set()
                offer_facts.append(
                    _FailureFact(
                        FailureClass.PERSISTENCE, None, {"stage": "raw_persistence"}
                    )
                )
        if offer_facts:
            raise _PairFailure(offer_facts)
        if len(persisted) != 2:
            raise _PairFailure(
                [_FailureFact(FailureClass.PERSISTENCE, None, {"stage": "pair_count"})]
            )
        by_org = {item.descriptor.provider_org: item for item in persisted}
        return by_org[self.config.primary_org], by_org[self.config.secondary_org]

    def _parse_json_rpc(
        self, persisted: PersistedEnvelope, request: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        if persisted.evidence is None:
            raise PairEventV2Error("response has no authenticated raw evidence")
        return _load_authenticated_rpc(
            persisted.evidence,
            request,
            max_bytes=self.config.max_body_bytes,
            raw_root=self.config.raw_root,
        )

    def _classify_rpc_error(self, error: object) -> FailureClass:
        if not isinstance(error, Mapping):
            return FailureClass.RPC_ERROR
        message = error.get("message")
        text = message.lower() if isinstance(message, str) else ""
        if any(marker in text for marker in _RANGE_LIMIT_MARKERS):
            return FailureClass.EXPLICIT_RANGE_LIMIT
        if any(marker in text for marker in _RESULT_PRESSURE_MARKERS):
            return FailureClass.RESULT_SIZE_PRESSURE
        return FailureClass.RPC_ERROR

    def _inspect_pair(
        self,
        pair: tuple[PersistedEnvelope, PersistedEnvelope],
        request: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        facts: list[_FailureFact] = []
        payloads: list[Mapping[str, Any]] = []
        order = {name: index for index, name in enumerate(FAILURE_ROUTE_PRECEDENCE)}

        def pick(candidates: list[_FailureFact]) -> _FailureFact:
            return min(
                candidates,
                key=lambda item: order.get(item.failure_class.value, len(order)),
            )

        for persisted in pair:
            descriptor = persisted.descriptor
            detail: dict[str, Any] = {"status_code": descriptor.status_code}
            if persisted.evidence is not None:
                detail.update(
                    {
                        "acquisition_id": persisted.evidence.acquisition_id,
                        "raw_object_id": persisted.evidence.raw_object_id,
                    }
                )
            # Collect ALL simultaneous per-response facts, then apply precedence.
            candidates: list[_FailureFact] = []
            if descriptor.status_code == 429:
                candidates.append(
                    _FailureFact(FailureClass.HTTP_429, descriptor.provider_org, detail)
                )
            if descriptor.status_code in (401, 403):
                candidates.append(
                    _FailureFact(
                        FailureClass.AUTHENTICATION, descriptor.provider_org, detail
                    )
                )
            if descriptor.error_kind == "spool_io":
                candidates.append(
                    _FailureFact(
                        FailureClass.PERSISTENCE, descriptor.provider_org, detail
                    )
                )
            if descriptor.error_kind is not None:
                failure_class = (
                    FailureClass.PERSISTENCE
                    if descriptor.error_kind
                    in ("spool_incomplete", "spool_missing_after_start")
                    else FailureClass.TRANSPORT
                )
                candidates.append(
                    _FailureFact(
                        failure_class,
                        descriptor.provider_org,
                        {**detail, "error_kind": descriptor.error_kind},
                    )
                )
            non_2xx = descriptor.status_code is None or not (
                200 <= int(descriptor.status_code or -1) < 300
            )
            if non_2xx and descriptor.status_code != 429:
                # Always retain HTTP_STATUS; add RPC-derived class separately so
                # range/result classification cannot replace status in precedence.
                rpc_code: object = None
                boundary_mismatch = False
                rpc_classified: FailureClass | None = None
                if not descriptor.truncated and persisted.evidence is not None:
                    try:
                        error_payload = self._parse_json_rpc(persisted, request)
                    except _JsonRpcBoundaryError:
                        boundary_mismatch = True
                    except PairEventV2Error:
                        pass
                    else:
                        if error_payload.get("error") is not None:
                            rpc_classified = self._classify_rpc_error(
                                error_payload["error"]
                            )
                            error = error_payload["error"]
                            if isinstance(error, Mapping):
                                rpc_code = error.get("code")
                if boundary_mismatch:
                    candidates.append(
                        _FailureFact(
                            FailureClass.BOUNDARY_MISMATCH,
                            descriptor.provider_org,
                            {**detail, "rpc_code": rpc_code},
                        )
                    )
                candidates.append(
                    _FailureFact(
                        FailureClass.HTTP_STATUS,
                        descriptor.provider_org,
                        {**detail, "rpc_code": rpc_code},
                    )
                )
                if rpc_classified is not None and rpc_classified != FailureClass.HTTP_STATUS:
                    candidates.append(
                        _FailureFact(
                            rpc_classified,
                            descriptor.provider_org,
                            {**detail, "rpc_code": rpc_code},
                        )
                    )
            # Size only considered when not already a pure auth/transport-only pick path
            # — still collected so precedence can demote size under non-2xx.
            if descriptor.truncated or (
                descriptor.response_bytes > self.config.max_body_bytes
            ):
                candidates.append(
                    _FailureFact(
                        FailureClass.BODY_SIZE_PRESSURE,
                        descriptor.provider_org,
                        {
                            **detail,
                            "cap_bytes": self.config.max_body_bytes,
                            "response_bytes": descriptor.response_bytes,
                        },
                    )
                )
            if candidates:
                facts.append(pick(candidates))
                continue
            try:
                payload = self._parse_json_rpc(persisted, request)
            except _JsonRpcBoundaryError:
                facts.append(
                    _FailureFact(
                        FailureClass.BOUNDARY_MISMATCH,
                        descriptor.provider_org,
                        {**detail, "stage": "json_rpc_boundary"},
                    )
                )
                continue
            except PairEventV2Error:
                facts.append(
                    _FailureFact(
                        FailureClass.MALFORMED_JSON,
                        descriptor.provider_org,
                        {**detail, "stage": "json_decode"},
                    )
                )
                continue
            if payload.get("error") is not None:
                failure_class = self._classify_rpc_error(payload["error"])
                error = payload["error"]
                code = error.get("code") if isinstance(error, Mapping) else None
                facts.append(
                    _FailureFact(
                        failure_class,
                        descriptor.provider_org,
                        {**detail, "rpc_code": code},
                    )
                )
                continue
            payloads.append(payload)
        if facts:
            raise _PairFailure(facts)
        if len(payloads) != 2:
            raise _PairFailure(
                [_FailureFact(FailureClass.INTERNAL, None, {"stage": "payload_count"})]
            )
        return payloads[0], payloads[1]

    def _failure_events(
        self,
        claim: Claim | None,
        failure: _PairFailure,
        request: Mapping[str, Any],
        *,
        plan_id: str | None = None,
    ) -> list[EngineEventRecord]:
        actual_plan = claim.plan_id if claim is not None else str(plan_id)
        domain_id = claim.domain_id if claim is not None else None
        attempt = claim.attempt if claim is not None else 0
        kind = (
            "provider_disagreement"
            if failure.route == FailureClass.PROVIDER_DISAGREEMENT
            else "failure"
        )
        events: list[EngineEventRecord] = []
        for fact in failure.facts:
            primary_raw = fact.detail.get("primary_raw_object_id")
            secondary_raw = fact.detail.get("secondary_raw_object_id")
            provider_raw = fact.detail.get("raw_object_id")
            if fact.provider_org == self.config.primary_org and provider_raw is not None:
                primary_raw = provider_raw
            if (
                fact.provider_org == self.config.secondary_org
                and provider_raw is not None
            ):
                secondary_raw = provider_raw
            primary_acq = fact.detail.get("primary_acquisition_id")
            secondary_acq = fact.detail.get("secondary_acquisition_id")
            provider_acq = fact.detail.get("acquisition_id")
            if fact.provider_org == self.config.primary_org and provider_acq is not None:
                primary_acq = provider_acq
            if (
                fact.provider_org == self.config.secondary_org
                and provider_acq is not None
            ):
                secondary_acq = provider_acq
            events.append(
                make_engine_event_record(
                    plan_id=actual_plan,
                    domain_id=domain_id,
                    attempt=attempt,
                    event_kind=kind,
                    failure_class=fact.failure_class,
                    provider_org=fact.provider_org,
                    request=request,
                    primary_raw_object_id=(
                        str(primary_raw) if primary_raw is not None else None
                    ),
                    secondary_raw_object_id=(
                        str(secondary_raw) if secondary_raw is not None else None
                    ),
                    primary_acquisition_id=(
                        str(primary_acq) if primary_acq is not None else None
                    ),
                    secondary_acquisition_id=(
                        str(secondary_acq) if secondary_acq is not None else None
                    ),
                    detail=fact.detail,
                )
            )
        return events

    def _pair_evidence_ids(
        self, pair: tuple[PersistedEnvelope, PersistedEnvelope]
    ) -> dict[str, Any]:
        primary = pair[0].evidence
        secondary = pair[1].evidence
        return {
            "primary_acquisition_id": (
                primary.acquisition_id if primary is not None else None
            ),
            "primary_raw_object_id": (
                primary.raw_object_id if primary is not None else None
            ),
            "secondary_acquisition_id": (
                secondary.acquisition_id if secondary is not None else None
            ),
            "secondary_raw_object_id": (
                secondary.raw_object_id if secondary is not None else None
            ),
        }

    def _retry(
        self, claim: Claim, failure: _PairFailure, request: Mapping[str, Any]
    ) -> str:
        events = self._failure_events(claim, failure, request)
        backoff = 0.0
        if failure.route == FailureClass.HTTP_429:
            for fact in failure.facts:
                if fact.failure_class != FailureClass.HTTP_429:
                    continue
                if fact.provider_org == self.config.primary_org:
                    self._primary_limiter.on_429()
                elif fact.provider_org == self.config.secondary_org:
                    self._secondary_limiter.on_429()
            ceiling = min(
                self.config.backoff_max_seconds,
                self.config.backoff_base_seconds * (2**claim.attempt),
            )
            backoff = min(
                self.config.backoff_max_seconds,
                ceiling * random.uniform(0.5, 1.5),
            )
            self._add_metrics(http_429=1)
        if claim.attempt + 1 >= self.config.max_attempts:
            terminal = make_engine_event_record(
                plan_id=claim.plan_id,
                domain_id=claim.domain_id,
                attempt=claim.attempt,
                event_kind="terminal_blocker",
                failure_class=failure.route,
                decision="terminal",
                request=request,
                detail={"reason": failure.route},
            )
            mode = str(failure.route)
            try:
                self.coordinator.terminalize(
                    claim, (*events, terminal), terminal_mode=mode
                )
            except _LeaseLostError:
                # Persist observations idempotently before winner resolution.
                self.coordinator.record_events((*events, terminal))
                return self.coordinator.resolve_winner(claim, terminal_mode=mode)
            self._add_metrics(terminal_blockers=1)
            return f"terminal:{mode}"
        decision = make_engine_event_record(
            plan_id=claim.plan_id,
            domain_id=claim.domain_id,
            attempt=claim.attempt,
            event_kind="retry_decision",
            failure_class=failure.route,
            decision="retry",
            request=request,
            detail={"backoff_seconds": round(backoff, 6)},
        )
        # Backoff first, then atomic evidence + attempt + lease deletion.
        if backoff:
            self._stop.wait(backoff)
        try:
            self.coordinator.release_retry(claim, (*events, decision))
        except _LeaseLostError:
            self.coordinator.record_events((*events, decision))
            return self.coordinator.resolve_winner(claim)
        self._add_metrics(retries=1)
        return f"retry:{failure.route}"

    def _split_or_terminal(
        self,
        claim: Claim,
        failure: _PairFailure,
        request: Mapping[str, Any],
        reason: SplitReason,
    ) -> str:
        events = self._failure_events(claim, failure, request)
        # Derive candidate split reason before any early lease-loss branch.
        candidate_reason: SplitReason = reason
        try:
            children = split_node(claim.node, reason=candidate_reason)
        except PairEventV2Error:
            terminal = make_engine_event_record(
                plan_id=claim.plan_id,
                domain_id=claim.domain_id,
                attempt=claim.attempt,
                event_kind="terminal_blocker",
                failure_class=failure.route,
                decision="terminal",
                request=request,
                detail={
                    "reason": "unsplittable_singleton",
                    "attempted_split_reason": candidate_reason,
                },
            )
            try:
                self.coordinator.terminalize(
                    claim,
                    (*events, terminal),
                    terminal_mode=TERMINAL_MODE_UNSPLITTABLE,
                )
            except _LeaseLostError:
                self.coordinator.record_events((*events, terminal))
                # Explicit terminal-candidate mode carrying the derived split reason.
                return self.coordinator.resolve_winner(
                    claim,
                    split_reason=candidate_reason,
                    terminal_mode=TERMINAL_MODE_UNSPLITTABLE,
                )
            self._add_metrics(terminal_blockers=1)
            return f"terminal:{TERMINAL_MODE_UNSPLITTABLE}"
        split_event = make_engine_event_record(
            plan_id=claim.plan_id,
            domain_id=claim.domain_id,
            attempt=claim.attempt,
            event_kind="split_decision",
            failure_class=failure.route,
            decision=f"split:{candidate_reason}",
            request=request,
            detail={"children": [child.domain_id for child in children]},
        )
        try:
            self.coordinator.commit_split(
                claim, children, candidate_reason, (*events, split_event)
            )
        except _LeaseLostError:
            self.coordinator.record_events((*events, split_event))
            return self.coordinator.resolve_winner(
                claim, split_reason=candidate_reason
            )
        self._add_metrics(splits=1)
        return f"split:{candidate_reason}"

    def _route_failure(
        self,
        claim: Claim,
        failure: _PairFailure,
        request: Mapping[str, Any],
        *,
        allow_split: bool,
        leaf_kwargs: Mapping[str, Any] | None = None,
        split_reason: SplitReason | None = None,
    ) -> str:
        # Derive candidate split reason before early lease-loss resolution.
        derived_split: SplitReason | None = split_reason
        classes = {fact.failure_class for fact in failure.facts}
        if allow_split and derived_split is None:
            if classes == {FailureClass.EXPLICIT_RANGE_LIMIT}:
                derived_split = "block_range_limit"
            elif classes and classes <= {
                FailureClass.BODY_SIZE_PRESSURE,
                FailureClass.RESULT_SIZE_PRESSURE,
            }:
                derived_split = "oversized_result"
            elif (
                classes == {FailureClass.PROVIDER_DISAGREEMENT}
                and claim.attempt + 1 >= self.config.max_attempts
            ):
                derived_split = "provider_disagreement"

        # Before the early lease-loss branch: derive candidate terminal mode.
        # Keep ``derived_split`` intact for the live path; only the resolve_winner
        # argument drops the split reason when the candidate is unsplittable.
        terminal_mode: str | None = None
        terminal_event: EngineEventRecord | None = None
        resolve_split: SplitReason | None = derived_split
        at_limit = claim.attempt + 1 >= self.config.max_attempts
        if at_limit and derived_split is None:
            terminal_mode = failure.route.value
            terminal_event = make_engine_event_record(
                plan_id=claim.plan_id,
                domain_id=claim.domain_id,
                attempt=claim.attempt,
                event_kind="terminal_blocker",
                failure_class=failure.route,
                decision="terminal",
                request=request,
                detail={"reason": failure.route},
            )
        elif derived_split is not None:
            try:
                split_node(claim.node, reason=derived_split)
            except PairEventV2Error:
                terminal_mode = TERMINAL_MODE_UNSPLITTABLE
                terminal_event = make_engine_event_record(
                    plan_id=claim.plan_id,
                    domain_id=claim.domain_id,
                    attempt=claim.attempt,
                    event_kind="terminal_blocker",
                    failure_class=failure.route,
                    decision="terminal",
                    request=request,
                    detail={
                        "reason": "unsplittable_singleton",
                        "attempted_split_reason": derived_split,
                    },
                )
                # Unsplittable: no valid SPLIT candidate for resolve_winner.
                resolve_split = None

        if self._lease_lost(claim):
            observations = self._failure_events(claim, failure, request)
            if terminal_event is not None:
                self.coordinator.record_events((*observations, terminal_event))
            else:
                self.coordinator.record_events(observations)
            # Valid SPLIT candidate: pass split_reason, no terminal_mode.
            # Terminal candidate: pass terminal_mode; a terminal winner with a
            # SPLIT-only candidate is a semantic mismatch (not pending_after_loss).
            return self.coordinator.resolve_winner(
                claim,
                leaf_kwargs=leaf_kwargs,
                split_reason=resolve_split if terminal_mode is None else None,
                terminal_mode=terminal_mode,
            )
        self._set_error(str(failure.route))
        if failure.route == FailureClass.TRANSPORT:
            self._add_metrics(transport_errors=1)
        if failure.route == FailureClass.PROVIDER_DISAGREEMENT:
            self._add_metrics(disagreements=1)
        # Live claim: split candidates (valid or unsplittable) stay on the
        # _split_or_terminal path so unsplittable terminals keep mode identity.
        if allow_split and derived_split is not None:
            return self._split_or_terminal(
                claim, failure, request, derived_split
            )
        return self._retry(claim, failure, request)

    def process_one(self) -> str | None:
        if self._stop.is_set():
            return None
        self._require_chain_ready()
        claim = self.coordinator.claim_pending(
            plan_id=self._plan_id,  # type: ignore[arg-type]
            worker_id=self.config.worker_id,
            lease_ttl_seconds=self.config.lease_ttl_seconds,
        )
        if claim is None:
            return None
        work = _ActiveWork(claim)
        with self._active_lock:
            self._active_by_token[claim.lease_token] = work
        self._add_metrics(claims=1)
        try:
            return self._process_claimed(claim)
        except _LeaseLostError:
            return self.coordinator.resolve_winner(claim)
        except _PairFailure as failure:
            return self._route_failure(
                claim,
                failure,
                request_for_domain(claim.node.domain),
                allow_split=False,
            )
        except Exception as exc:
            self._set_error(type(exc).__name__)
            return self._route_failure(
                claim,
                _PairFailure(
                    [
                        _FailureFact(
                            FailureClass.INTERNAL, None, {"stage": "process_node"}
                        )
                    ]
                ),
                request_for_domain(claim.node.domain),
                allow_split=False,
            )
        finally:
            with self._active_lock:
                self._active_by_token.pop(claim.lease_token, None)

    def _process_claimed(self, claim: Claim) -> str:
        domain = claim.node.domain
        request = request_for_domain(domain)
        try:
            pair = self._dual_fetch(request)
            primary_payload, secondary_payload = self._inspect_pair(pair, request)
        except _PairFailure as failure:
            return self._route_failure(claim, failure, request, allow_split=True)

        primary_logs = primary_payload.get("result")
        secondary_logs = secondary_payload.get("result")
        malformed: list[_FailureFact] = []
        if not isinstance(primary_logs, list):
            malformed.append(
                _FailureFact(
                    FailureClass.MALFORMED_JSON,
                    self.config.primary_org,
                    {"stage": "logs_result", **self._pair_evidence_ids(pair)},
                )
            )
        if not isinstance(secondary_logs, list):
            malformed.append(
                _FailureFact(
                    FailureClass.MALFORMED_JSON,
                    self.config.secondary_org,
                    {"stage": "logs_result", **self._pair_evidence_ids(pair)},
                )
            )
        if malformed:
            return self._route_failure(
                claim, _PairFailure(malformed), request, allow_split=False
            )

        pressure: list[_FailureFact] = []
        # Overflow is count > max. Exact-cap (== max) is conservative_cap pressure only.
        for org, logs in (
            (self.config.primary_org, primary_logs),
            (self.config.secondary_org, secondary_logs),
        ):
            count = len(logs)
            if count > self.config.max_log_count:
                pressure.append(
                    _FailureFact(
                        FailureClass.RESULT_SIZE_PRESSURE,
                        org,
                        {
                            "cap": self.config.max_log_count,
                            "count": count,
                            "rule": "result_overflow",
                            **self._pair_evidence_ids(pair),
                        },
                    )
                )
            elif count == self.config.max_log_count:
                pressure.append(
                    _FailureFact(
                        FailureClass.RESULT_SIZE_PRESSURE,
                        org,
                        {
                            "cap": self.config.max_log_count,
                            "count": count,
                            "rule": "conservative_cap",
                            **self._pair_evidence_ids(pair),
                        },
                    )
                )
        if pressure:
            return self._route_failure(
                claim, _PairFailure(pressure), request, allow_split=True
            )

        for org, logs in (
            (self.config.primary_org, primary_logs),
            (self.config.secondary_org, secondary_logs),
        ):
            try:
                normalize_and_index_logs(logs, domain)
            except PairEventV2Error:
                return self._route_failure(
                    claim,
                    _PairFailure(
                        [
                            _FailureFact(
                                FailureClass.MALFORMED_JSON,
                                org,
                                {
                                    "stage": "log_shape",
                                    **self._pair_evidence_ids(pair),
                                },
                            )
                        ]
                    ),
                    request,
                    allow_split=False,
                )

        try:
            identities, digest = reconcile_log_sets_v2(
                primary_logs, secondary_logs, domain
            )
        except PairEventV2Error:
            return self._route_failure(
                claim,
                _PairFailure(
                    [
                        _FailureFact(
                            FailureClass.PROVIDER_DISAGREEMENT,
                            None,
                            {
                                "boundary_verified": True,
                                **self._pair_evidence_ids(pair),
                            },
                        )
                    ]
                ),
                request,
                allow_split=True,
            )

        needed_blocks = {domain.end_block}
        needed_blocks.update(identity.block_number for identity in identities)
        header_ids: list[str] = []
        header_hashes: dict[int, str] = {}
        for block_number in sorted(needed_blocks):
            try:
                header = self._get_header(claim, block_number)
            except _PairFailure as failure:
                return self._route_failure(
                    claim,
                    failure,
                    block_header_request(block_number),
                    allow_split=(
                        failure.route == FailureClass.PROVIDER_DISAGREEMENT
                    ),
                )
            header_ids.append(header.header_receipt_id)
            header_hashes[block_number] = header.block_hash

        for identity in identities:
            if header_hashes.get(identity.block_number) != identity.block_hash:
                return self._route_failure(
                    claim,
                    _PairFailure(
                        [
                            _FailureFact(
                                FailureClass.PROVIDER_DISAGREEMENT,
                                None,
                                {
                                    "block_number": identity.block_number,
                                    "boundary_verified": True,
                                    "kind": "log_header_hash",
                                    **self._pair_evidence_ids(pair),
                                },
                            )
                        ]
                    ),
                    request,
                    allow_split=True,
                )

        primary_evidence = pair[0].evidence
        secondary_evidence = pair[1].evidence
        if primary_evidence is None or secondary_evidence is None:
            raise _PairFailure(
                [_FailureFact(FailureClass.PERSISTENCE, None, {"stage": "leaf"})]
            )
        leaf_kwargs = {
            "plan_id": claim.plan_id,
            "domain": domain,
            "log_identity_sha256": digest,
            "primary_provider_org": self.config.primary_org,
            "secondary_provider_org": self.config.secondary_org,
            "primary_logs_raw_object_id": primary_evidence.raw_object_id,
            "secondary_logs_raw_object_id": secondary_evidence.raw_object_id,
            "primary_logs_acquisition_id": primary_evidence.acquisition_id,
            "secondary_logs_acquisition_id": secondary_evidence.acquisition_id,
            "log_count": len(identities),
            "canonical_header_receipt_ids": header_ids,
        }
        if self._lease_lost(claim):
            return self.coordinator.resolve_winner(claim, leaf_kwargs=leaf_kwargs)
        try:
            self.coordinator.commit_agreed(claim, leaf_kwargs)
        except _LeaseLostError:
            return self.coordinator.resolve_winner(claim, leaf_kwargs=leaf_kwargs)
        self._primary_limiter.on_success()
        self._secondary_limiter.on_success()
        self._add_metrics(agreed=1)
        return "agreed"

    def _get_header(
        self, claim: Claim, block_number: int
    ) -> CanonicalHeaderReceiptRecord:
        lock = self._header_stripes[block_number % len(self._header_stripes)]
        with lock:
            try:
                cached = self.coordinator.load_header(
                    plan_id=claim.plan_id,
                    block_number=block_number,
                    primary_org=self.config.primary_org,
                    secondary_org=self.config.secondary_org,
                )
            except Exception as exc:
                raise _PairFailure(
                    [
                        _FailureFact(
                            FailureClass.AUTHENTICATION,
                            None,
                            {
                                "block_number": block_number,
                                "stage": "cached_header_load",
                            },
                        )
                    ]
                ) from exc
            if cached is not None:
                record, p_ev, s_ev = cached
                try:
                    self._verify_cached_header(record, p_ev, s_ev, block_number)
                except UniswapV2IngestionError as exc:
                    raise _PairFailure(
                        [
                            _FailureFact(
                                FailureClass.AUTHENTICATION,
                                None,
                                {
                                    "block_number": block_number,
                                    "stage": "cached_header",
                                },
                            )
                        ]
                    ) from exc
                with self._header_cache_lock:
                    self._header_cache[block_number] = record.header_receipt_id
                    self._header_cache.move_to_end(block_number)
                    while len(self._header_cache) > self.config.header_cache_size:
                        self._header_cache.popitem(last=False)
                self._add_metrics(headers_cached=1)
                return record

            request = block_header_request(block_number)
            pair = self._dual_fetch(request)
            primary_payload, secondary_payload = self._inspect_pair(pair, request)
            primary = primary_payload.get("result")
            secondary = secondary_payload.get("result")
            if not isinstance(primary, Mapping) or not isinstance(secondary, Mapping):
                raise _PairFailure(
                    [
                        _FailureFact(
                            FailureClass.MALFORMED_JSON,
                            None,
                            {
                                "stage": "header_result",
                                **self._pair_evidence_ids(pair),
                            },
                        )
                    ]
                )
            try:
                p_number = _hex_quantity(
                    _require(primary, "number", label="primary header"),
                    label="primary header number",
                )
                s_number = _hex_quantity(
                    _require(secondary, "number", label="secondary header"),
                    label="secondary header number",
                )
                p_hash = _hex_bytes(
                    _require(primary, "hash", label="primary header"),
                    32,
                    label="primary header hash",
                )
                s_hash = _hex_bytes(
                    _require(secondary, "hash", label="secondary header"),
                    32,
                    label="secondary header hash",
                )
                p_ts = _hex_quantity(
                    _require(primary, "timestamp", label="primary header"),
                    label="primary header timestamp",
                )
                s_ts = _hex_quantity(
                    _require(secondary, "timestamp", label="secondary header"),
                    label="secondary header timestamp",
                )
            except UniswapV2IngestionError as exc:
                raise _PairFailure(
                    [
                        _FailureFact(
                            FailureClass.MALFORMED_JSON,
                            None,
                            {
                                "stage": "header_fields",
                                **self._pair_evidence_ids(pair),
                            },
                        )
                    ]
                ) from exc
            wrong: list[_FailureFact] = []
            if p_number != block_number:
                wrong.append(
                    _FailureFact(
                        FailureClass.BOUNDARY_MISMATCH,
                        self.config.primary_org,
                        {"block_number": block_number, **self._pair_evidence_ids(pair)},
                    )
                )
            if s_number != block_number:
                wrong.append(
                    _FailureFact(
                        FailureClass.BOUNDARY_MISMATCH,
                        self.config.secondary_org,
                        {"block_number": block_number, **self._pair_evidence_ids(pair)},
                    )
                )
            if wrong:
                raise _PairFailure(wrong)
            if p_hash != s_hash or p_ts != s_ts:
                raise _PairFailure(
                    [
                        _FailureFact(
                            FailureClass.PROVIDER_DISAGREEMENT,
                            None,
                            {
                                "block_number": block_number,
                                "boundary_verified": True,
                                "kind": "header",
                                **self._pair_evidence_ids(pair),
                            },
                        )
                    ]
                )
            p_ev = pair[0].evidence
            s_ev = pair[1].evidence
            if p_ev is None or s_ev is None:
                raise _PairFailure(
                    [_FailureFact(FailureClass.PERSISTENCE, None, {"stage": "header"})]
                )
            header_id = compute_canonical_header_receipt_id(
                plan_id=claim.plan_id,
                block_number=block_number,
                block_hash=p_hash,
                block_timestamp=p_ts,
                primary_provider_org=self.config.primary_org,
                secondary_provider_org=self.config.secondary_org,
                primary_raw_object_id=p_ev.raw_object_id,
                secondary_raw_object_id=s_ev.raw_object_id,
                primary_acquisition_id=p_ev.acquisition_id,
                secondary_acquisition_id=s_ev.acquisition_id,
            )
            record = CanonicalHeaderReceiptRecord(
                header_receipt_id=header_id,
                plan_id=claim.plan_id,
                block_number=block_number,
                block_hash=p_hash,
                block_timestamp=p_ts,
                primary_provider_org=self.config.primary_org,
                secondary_provider_org=self.config.secondary_org,
                primary_raw_object_id=p_ev.raw_object_id,
                secondary_raw_object_id=s_ev.raw_object_id,
                primary_acquisition_id=p_ev.acquisition_id,
                secondary_acquisition_id=s_ev.acquisition_id,
                completed_at=_now(),
            )
            try:
                record = self.coordinator.store_header(record)
            except Exception as exc:
                raise _PairFailure(
                    [
                        _FailureFact(
                            FailureClass.HEADER_CONFLICT,
                            None,
                            {
                                "block_number": block_number,
                                **self._pair_evidence_ids(pair),
                            },
                        )
                    ]
                ) from exc
            self._add_metrics(headers_fetched=1)
            return record

    def _verify_cached_header(
        self,
        record: CanonicalHeaderReceiptRecord,
        primary_evidence: AuthenticatedEvidence,
        secondary_evidence: AuthenticatedEvidence,
        block_number: int,
    ) -> None:
        request = block_header_request(block_number)
        payloads = []
        for evidence in (primary_evidence, secondary_evidence):
            payloads.append(
                _load_authenticated_rpc(
                    evidence,
                    request,
                    max_bytes=self.config.max_body_bytes,
                    raw_root=self.config.raw_root,
                )
            )
        headers = [payload.get("result") for payload in payloads]
        if not all(isinstance(header, Mapping) for header in headers):
            raise PairEventV2Error("cached header body is malformed")
        numbers = [
            _hex_quantity(_require(header, "number", label="header"), label="number")
            for header in headers
        ]
        hashes = [
            _hex_bytes(_require(header, "hash", label="header"), 32, label="hash")
            for header in headers
        ]
        timestamps = [
            _hex_quantity(
                _require(header, "timestamp", label="header"), label="timestamp"
            )
            for header in headers
        ]
        if numbers != [block_number, block_number]:
            raise PairEventV2Error("cached header number authentication failed")
        if hashes != [record.block_hash, record.block_hash]:
            raise PairEventV2Error("cached header hash authentication failed")
        if timestamps != [record.block_timestamp, record.block_timestamp]:
            raise PairEventV2Error("cached header timestamp authentication failed")
        recomputed = compute_canonical_header_receipt_id(
            plan_id=record.plan_id,
            block_number=record.block_number,
            block_hash=record.block_hash,
            block_timestamp=record.block_timestamp,
            primary_provider_org=record.primary_provider_org,
            secondary_provider_org=record.secondary_provider_org,
            primary_raw_object_id=primary_evidence.raw_object_id,
            secondary_raw_object_id=secondary_evidence.raw_object_id,
            primary_acquisition_id=primary_evidence.acquisition_id,
            secondary_acquisition_id=secondary_evidence.acquisition_id,
        )
        if recomputed != record.header_receipt_id:
            raise PairEventV2Error("cached header receipt identity failed recomputation")

    def run_until_idle(self, *, max_steps: int | None = None) -> EngineMetrics:
        """Run bounded concurrent waves. Requires chain authentication."""
        self._require_chain_ready()
        completed_steps = 0
        while not self._stop.is_set():
            if max_steps is not None and completed_steps >= max_steps:
                break
            width = self.config.max_nodes_in_flight
            if max_steps is not None:
                width = min(width, max_steps - completed_steps)
            futures = [
                self._node_executor.submit(self.process_one) for _ in range(width)
            ]
            pending = set(futures)
            outcomes: list[str | None] = []
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    outcomes.append(future.result())
            made_progress = sum(outcome is not None for outcome in outcomes)
            completed_steps += made_progress
            if made_progress == 0:
                break
        return self.metrics


__all__ = [
    "AuthenticatedEvidence",
    "CHAIN_IDENTITY_RECORD_COLUMNS",
    "CHAIN_IDENTITY_SCHEMA_VERSION",
    "CHAIN_IDENTITY_TABLE",
    "CHAIN_IDENTITY_UNIQUENESS",
    "Claim",
    "ChainIdentityReceipt",
    "DEFAULT_BACKOFF_BASE_SECONDS",
    "DEFAULT_BACKOFF_MAX_SECONDS",
    "DEFAULT_HEADER_CACHE_SIZE",
    "DEFAULT_LEASE_TTL_SECONDS",
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_MAX_BODY_BYTES",
    "DEFAULT_MAX_IN_FLIGHT",
    "DEFAULT_MAX_LOG_COUNT",
    "DEFAULT_MAX_NODE_IN_FLIGHT",
    "DEFAULT_MAX_SPOOL_FILES",
    "DEFAULT_PERSISTENCE_QUEUE_SIZE",
    "DEFAULT_RESPONSE_DRAIN_DEADLINE_SECONDS",
    "DEFAULT_RPS",
    "DEFAULT_SPOOL_CHUNK_BYTES",
    "ENGINE_EVENT_KINDS",
    "ENGINE_EVENT_RECORD_COLUMNS",
    "ENGINE_EVENT_SCHEMA_VERSION",
    "ENGINE_EVENT_TABLE",
    "ENGINE_EVENT_UNIQUENESS",
    "EXECUTION_POLICY_RECORD_COLUMNS",
    "EXECUTION_POLICY_SCHEMA_VERSION",
    "EXECUTION_POLICY_TABLE",
    "EXECUTION_POLICY_UNIQUENESS",
    "FAILURE_ROUTE_PRECEDENCE",
    "EngineConfig",
    "EngineEventRecord",
    "EngineMetrics",
    "EnginePhase",
    "FailureClass",
    "HEADER_UNIQUENESS",
    "LEAF_UNIQUENESS",
    "NetworkWorker",
    "PairEventV2Engine",
    "PersistedEnvelope",
    "PersistenceCoordinator",
    "SOURCE_ID",
    "SPOOL_DESCRIPTOR_SCHEMA_VERSION",
    "SpoolDescriptor",
    "TERMINAL_MODE_LEASE_EXPIRED",
    "TERMINAL_MODE_UNSPLITTABLE",
    "TERMINAL_MODES",
    "TERMINAL_RECEIPT_RECORD_COLUMNS",
    "TERMINAL_RECEIPT_SCHEMA_VERSION",
    "TERMINAL_RECEIPT_TABLE",
    "TERMINAL_RECEIPT_UNIQUENESS",
    "compute_chain_identity_receipt_id",
    "compute_terminal_receipt_id",
    "make_engine_event_record",
]
