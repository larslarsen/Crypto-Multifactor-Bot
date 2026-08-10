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
    block_header_batch_request,
    block_header_request,
    chain_id_request,
    find_batch_response_by_id,
)
from cryptofactors.acquisition.uniswap_v2_pair_events_v2 import (
    CLAIM_ORDER_VERSION_CHRONOLOGICAL_V1,
    CLAIM_ORDER_VERSION_DOMAIN_HASH_V1,
    DEFAULT_EVENT_PROVIDER_ORGS,
    LOG_IDENTITY_VERSION,
    PRODUCTION_INITIAL_COHORT_SIZE,
    PRODUCTION_PLAN_ID,
    PRODUCTION_POOL_TOPIC_BLOCKS,
    PRODUCTION_REGISTRY_PARQUET_BYTES,
    PRODUCTION_REGISTRY_PARQUET_SHA256,
    PRODUCTION_ROOT_COUNT,
    PRODUCTION_ROOT_DOMAIN_SET_SHA256,
    RECEIPT_SCHEMA_VERSION,
    ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID,
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
    RootFilterPlan,
    RootManifestRecord,
    SplitReason,
    build_acquisition_plan_v2,
    compute_canonical_header_receipt_id,
    compute_log_candidate_id,
    compute_production_root_anchors,
    iter_production_root_filters,
    make_leaf_receipt_record,
    normalize_and_index_logs,
    normalize_provider_org,
    plan_record_from_config,
    production_plan_config,
    reconcile_log_sets_v2,
    request_for_domain,
    required_blocks_from_identities,
    split_node,
    validate_children_partition,
    verify_production_root_anchors,
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
# Migration 0020 additive tables (ADR-0015 §9.10).
ROOT_MANIFEST_TABLE: Final[str] = "uniswap_v2_pair_event_v2_root_manifest"
LOG_CANDIDATE_TABLE: Final[str] = "uniswap_v2_pair_event_v2_log_candidate"
LOG_CANDIDATE_BLOCK_TABLE: Final[str] = "uniswap_v2_pair_event_v2_log_candidate_block"
HEADER_BACKLOG_TABLE: Final[str] = "uniswap_v2_pair_event_v2_header_backlog"
HEADER_BACKLOG_METRIC_TABLE: Final[str] = "uniswap_v2_pair_event_v2_header_backlog_metric"
PLAN_RESUME_SESSION_TABLE: Final[str] = "uniswap_v2_pair_event_v2_plan_resume_session"
CREDENTIAL_REDACTED_DETAIL: Final[str] = "redacted_credential_or_endpoint"

# Bounded production work pages (ADR-0015 §9.10). One page per turn so node
# refill is never starved by an unbounded header/finalization drain.
HEADER_WORK_PAGE_SIZE: Final[int] = 32
FINALIZE_WORK_PAGE_SIZE: Final[int] = 32
CLAIM_SCAN_PAGE_SIZE: Final[int] = 32

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


def _load_authenticated_json_value(
    evidence: AuthenticatedEvidence,
    *,
    max_bytes: int,
    raw_root: Path,
    pulse: Callable[[], None] | None = None,
) -> Any:
    """Parse authenticated bytes via trusted raw-root traversal (one open identity).

    Always re-opens through configured ``raw_root`` + digest-canonical storage_uri.
    Never trusts ``storage_path.parent`` as a second root. Returns any JSON value
    (object or batch array) after sha256/size re-authentication.
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
    return payload


def _load_authenticated_json(
    evidence: AuthenticatedEvidence,
    *,
    max_bytes: int,
    raw_root: Path,
    pulse: Callable[[], None] | None = None,
) -> Mapping[str, Any]:
    """Load authenticated evidence and require a JSON object body."""
    payload = _load_authenticated_json_value(
        evidence, max_bytes=max_bytes, raw_root=raw_root, pulse=pulse
    )
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


def _canonical_request_json(request: Any) -> str:
    """Canonical JSON for a scalar JSON-RPC object or batch array request."""
    if isinstance(request, Mapping):
        return _canonical_json(dict(request))
    if isinstance(request, list):
        return _canonical_json(list(request))
    raise PairEventV2Error("request must be a JSON-RPC object or batch array")


def _extract_header_result_from_evidence(
    evidence: AuthenticatedEvidence,
    *,
    block_number: int,
    max_bytes: int,
    raw_root: Path,
) -> dict[str, Any]:
    """Extract one block header from scalar or batch-backed authenticated raw."""
    body = _load_authenticated_json_value(
        evidence, max_bytes=max_bytes, raw_root=raw_root
    )
    try:
        stored_request = json.loads(evidence.request_json)
    except json.JSONDecodeError as exc:
        raise PairEventV2Error("header evidence request_json is not JSON") from exc
    if isinstance(stored_request, list):
        req_id = None
        for item in stored_request:
            if not isinstance(item, Mapping):
                continue
            params = item.get("params")
            if isinstance(params, list) and params and isinstance(params[0], str):
                try:
                    if int(params[0], 16) == block_number:
                        req_id = item.get("id")
                        break
                except ValueError:
                    continue
        if req_id is None:
            raise PairEventV2Error(f"batch request missing block {block_number}")
        if not isinstance(body, list):
            raise PairEventV2Error("batch header raw body is not a list")
        member = find_batch_response_by_id(body, req_id)
        if "error" in member and member["error"] is not None:
            raise PairEventV2Error(
                f"batch header member error for block {block_number}"
            )
        result = member.get("result")
    elif isinstance(stored_request, Mapping):
        if not isinstance(body, Mapping):
            raise PairEventV2Error("scalar header raw body is not an object")
        if "error" in body and body["error"] is not None:
            raise PairEventV2Error("scalar header body has error")
        result = body.get("result")
    else:
        raise PairEventV2Error("header evidence request is neither object nor batch")
    if not isinstance(result, Mapping):
        raise PairEventV2Error("header result is not an object")
    try:
        number = _hex_quantity(
            _require(result, "number", label="header number"), label="header number"
        )
        block_hash = _hex_bytes(
            _require(result, "hash", label="header hash"), 32, label="header hash"
        )
        timestamp = _hex_quantity(
            _require(result, "timestamp", label="header timestamp"),
            label="header timestamp",
        )
    except UniswapV2IngestionError as exc:
        raise PairEventV2Error("canonical header fields are malformed") from exc
    return {"number": number, "hash": block_hash, "timestamp": timestamp}


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
        if isinstance(request, Mapping):
            if (
                request.get("jsonrpc") != "2.0"
                or not isinstance(request.get("method"), str)
                or not isinstance(request.get("params"), list)
                or _contains_sensitive_key(request)
                or self.request_json != _canonical_json(dict(request))
            ):
                raise PairEventV2Error(
                    "spool request is not a canonical JSON-RPC object payload"
                )
        elif isinstance(request, list):
            if not request:
                raise PairEventV2Error("spool batch request must be non-empty")
            for item in request:
                if (
                    not isinstance(item, Mapping)
                    or item.get("jsonrpc") != "2.0"
                    or not isinstance(item.get("method"), str)
                    or not isinstance(item.get("params"), list)
                    or "id" not in item
                    or _contains_sensitive_key(item)
                ):
                    raise PairEventV2Error(
                        "spool batch member is not a canonical JSON-RPC request"
                    )
            if self.request_json != _canonical_json(list(request)):
                raise PairEventV2Error(
                    "spool batch request is not canonical JSON"
                )
        else:
            raise PairEventV2Error(
                "spool request must be a JSON-RPC object or batch array"
            )
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
    # ADR-0015 §9.10 additive production metrics (never authority).
    provider_attempts_primary: int = 0
    provider_attempts_secondary: int = 0
    provider_attempts_total: int = 0
    in_flight_high_water_primary: int = 0
    in_flight_high_water_secondary: int = 0
    nodes_in_flight_high_water: int = 0
    spool_files_high_water: int = 0
    candidates_committed: int = 0
    header_batches: int = 0
    header_batch_members: int = 0
    header_backlog: int = 0
    finalizations: int = 0
    credential_detections: int = 0
    provider_latency_ms_total: float = 0.0
    last_error: str | None = None

    def snapshot(self) -> EngineMetrics:
        return replace(self)


@dataclass(frozen=True, slots=True)
class CredentialScanner:
    """Matrix-style rolling endpoint/secret scanner (ADR-0015 §9.10).

    Exact runtime URLs and extracted secrets are never serialized. Form-based
    bearer and secret-query checks always apply. A hit must prevent any spool
    write of secret-bearing candidate bytes.
    """

    forbidden_substrings: tuple[str, ...] = ()

    @classmethod
    def from_rpc_urls(
        cls, *urls: str | None, extra_secrets: Sequence[str] = ()
    ) -> CredentialScanner:
        from urllib.parse import parse_qs, unquote, urlparse

        forbidden: list[str] = []
        for raw in urls:
            if not raw:
                continue
            u = str(raw).strip()
            if not u:
                continue
            forbidden.append(u)
            try:
                parsed = urlparse(u)
            except Exception:
                continue
            if parsed.password:
                forbidden.append(unquote(parsed.password))
            if parsed.username:
                forbidden.append(unquote(parsed.username))
            if parsed.username or parsed.password:
                if parsed.netloc:
                    forbidden.append(parsed.netloc)
            if parsed.query:
                qs = parse_qs(parsed.query, keep_blank_values=False)
                for key, values in qs.items():
                    kl = key.lower()
                    if kl in {
                        "api_key",
                        "apikey",
                        "key",
                        "token",
                        "password",
                        "secret",
                        "access_token",
                        "authorization",
                        "bearer",
                    }:
                        for v in values:
                            if v:
                                forbidden.append(v)
            host = (parsed.hostname or "").lower()
            parts = [p for p in (parsed.path or "").split("/") if p]
            if host == "infura.io" or host.endswith(".infura.io"):
                for index, part in enumerate(parts[:-1]):
                    if part.lower() == "v3" and len(parts[index + 1]) >= 16:
                        forbidden.append(parts[index + 1])
            if host == "blockpi.network" or host.endswith(".blockpi.network"):
                for index in range(len(parts) - 2):
                    if (
                        parts[index].lower() == "v1"
                        and parts[index + 1].lower() == "rpc"
                        and len(parts[index + 2]) >= 16
                    ):
                        forbidden.append(parts[index + 2])
        for s in extra_secrets:
            if s:
                forbidden.append(str(s))
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in forbidden:
            if not item or item in seen:
                continue
            if item in {"http:", "https:", "http://", "https://"}:
                continue
            seen.add(item)
            cleaned.append(item)
        return cls(forbidden_substrings=tuple(cleaned))

    @property
    def max_needle_bytes(self) -> int:
        if not self.forbidden_substrings:
            return 512
        return max(
            512,
            max(len(s.encode("utf-8", errors="replace")) for s in self.forbidden_substrings)
            + 64,
        )

    def contains_credential(self, text: str) -> bool:
        if not text:
            return False
        import re as _re

        if _re.search(r"://[^/\s]*:[^@/\s]+@", text):
            return True
        bearer = _re.search(r"(?i)\bbearer\s+([A-Za-z0-9._\-+/=]{8,})", text)
        if bearer and bearer.group(1).lower() not in {"null", "undefined", "redacted"}:
            return True
        secret_q = _re.search(
            r"(?i)(?:api[_-]?key|apikey|key|token|password|secret|access_token)"
            r"\s*=\s*([^&\s]{6,})",
            text,
        )
        if secret_q and secret_q.group(1).lower() not in {
            "null",
            "undefined",
            "redacted",
        }:
            return True
        lower = text.lower()
        for needle in self.forbidden_substrings:
            if needle in text or needle.lower() in lower:
                return True
        return False

    def scan_bytes(self, data: bytes) -> bool:
        if not data:
            return False
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")
        return self.contains_credential(text)


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
        self._high_water = 0
        self._successes = 0
        self._condition = threading.Condition()

    @property
    def limit(self) -> int:
        with self._condition:
            return self._limit

    @property
    def active(self) -> int:
        with self._condition:
            return self._active

    @property
    def high_water(self) -> int:
        with self._condition:
            return self._high_water

    def acquire(self) -> None:
        with self._condition:
            self._condition.wait_for(lambda: self._active < self._limit)
            self._active += 1
            if self._active > self._high_water:
                self._high_water = self._active

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
    """Streams one JSON-RPC response to a durable spool. No SQLite.

    Every response byte is scanned with a rolling holdback before spool write
    (ADR-0015 §9.10). Credential hits drain remaining bytes without persistence.
    """

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
        credential_scanner: CredentialScanner | None = None,
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
        self._scanner = credential_scanner or CredentialScanner()

    def fetch(self, request: Mapping[str, Any] | Sequence[Any]) -> SpoolDescriptor:
        if isinstance(request, Mapping):
            request_obj: Any = dict(request)
        else:
            request_obj = list(request)
        request_json = _canonical_json(request_obj)
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
                        # Credential holdback: only write bytes proven free of secrets.
                        past_deadline = False
                        scanner_only = False
                        pending = bytearray()
                        holdback = max(1, self._scanner.max_needle_bytes - 1)

                        def _close_handle_for_stop() -> None:
                            nonlocal handle, error_kind, error_detail
                            if handle is not None:
                                try:
                                    handle.flush()
                                    os.fsync(handle.fileno())
                                    handle.close()
                                except OSError as exc:
                                    error_kind = "spool_io"
                                    error_detail = type(exc).__name__
                                handle = None

                        def _write_safe(piece: bytes) -> None:
                            nonlocal retained_bytes, truncated, handle
                            nonlocal error_kind, error_detail
                            if scanner_only or handle is None or not piece:
                                return
                            remaining = self._max_body_bytes - retained_bytes
                            if remaining <= 0:
                                truncated = True
                                return
                            out = piece[:remaining]
                            try:
                                handle.write(out)
                                retained_bytes += len(out)
                            except OSError as exc:
                                error_kind = "spool_io"
                                error_detail = type(exc).__name__
                                try:
                                    handle.close()
                                except OSError:
                                    pass
                                handle = None
                            if len(piece) > remaining:
                                truncated = True

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
                                _close_handle_for_stop()
                            # Scan every byte including over-cap / post-deadline drain.
                            pending.extend(chunk)
                            if self._scanner.scan_bytes(bytes(pending)):
                                scanner_only = True
                                error_kind = "credential_detection"
                                error_detail = CREDENTIAL_REDACTED_DETAIL
                                pending.clear()
                                # Delete any already-written spool prefix (no secret authority).
                                if handle is not None:
                                    try:
                                        handle.close()
                                    except OSError:
                                        pass
                                    handle = None
                                if spool_path is not None:
                                    spool_path.unlink(missing_ok=True)
                                retained_bytes = 0
                                continue
                            if past_deadline or scanner_only:
                                # Keep only holdback for rolling scan; write nothing.
                                if len(pending) > holdback:
                                    del pending[:-holdback]
                                continue
                            releasable = len(pending) - holdback
                            if releasable > 0:
                                _write_safe(bytes(pending[:releasable]))
                                del pending[:releasable]
                        # EOF: scan remaining pending; write only if clean.
                        if pending and not scanner_only:
                            if self._scanner.scan_bytes(bytes(pending)):
                                scanner_only = True
                                error_kind = "credential_detection"
                                error_detail = CREDENTIAL_REDACTED_DETAIL
                                if handle is not None:
                                    try:
                                        handle.close()
                                    except OSError:
                                        pass
                                    handle = None
                                if spool_path is not None:
                                    spool_path.unlink(missing_ok=True)
                                retained_bytes = 0
                            elif not past_deadline:
                                _write_safe(bytes(pending))
                        pending.clear()
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
        # O(plans) force keyset cursors only. Session generation + per-candidate
        # session_auth_generation live in SQLite (shared multi-process).
        self._resume_force_through: dict[str, str | None] = {}
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

    def ensure_production_plan_shell(
        self, *, config: PlanConfig, execution_policy: Mapping[str, Any]
    ) -> str:
        """Insert production plan + policy if absent; never requires full root set."""
        return self._call(
            "ensure_production_plan_shell",
            config=config,
            execution_policy=dict(execution_policy),
        )

    def authenticate_ready_root_manifest(
        self,
        *,
        plan_id: str,
        registry_parquet_sha256: str,
        registry_parquet_bytes: int,
    ) -> RootManifestRecord:
        """Re-authenticate pinned READY manifest fields + complete root set (streamed)."""
        return self._call(
            "authenticate_ready_root_manifest",
            plan_id=plan_id,
            registry_parquet_sha256=registry_parquet_sha256,
            registry_parquet_bytes=int(registry_parquet_bytes),
        )

    def initialize_production_roots_batch(
        self,
        *,
        plan_id: str,
        roots: Sequence[RootFilterPlan],
        registry_parquet_sha256: str,
        registry_parquet_bytes: int,
        expected_root_count: int,
        expected_root_domain_set_sha256: str,
        expected_pool_topic_blocks: int,
        finalize: bool = False,
    ) -> dict[str, Any]:
        """Additive production root insert; READY only when finalize authenticates anchors."""
        return self._call(
            "initialize_production_roots_batch",
            plan_id=plan_id,
            roots=tuple(roots),
            registry_parquet_sha256=registry_parquet_sha256,
            registry_parquet_bytes=int(registry_parquet_bytes),
            expected_root_count=int(expected_root_count),
            expected_root_domain_set_sha256=expected_root_domain_set_sha256,
            expected_pool_topic_blocks=int(expected_pool_topic_blocks),
            finalize=bool(finalize),
        )

    def load_root_manifest(self, *, plan_id: str) -> RootManifestRecord | None:
        return self._call("load_root_manifest", plan_id=plan_id)

    def commit_log_candidate(
        self,
        claim: Claim,
        *,
        candidate_kwargs: Mapping[str, Any],
        blocks: Sequence[tuple[int, str | None, bool]],
    ) -> str:
        """Persist immutable log candidate + blocks; return node to PENDING; release lease."""
        return self._call(
            "commit_log_candidate",
            claim=claim,
            candidate_kwargs=dict(candidate_kwargs),
            blocks=tuple(blocks),
        )

    def load_log_candidate(
        self, *, plan_id: str, domain_id: str
    ) -> dict[str, Any] | None:
        return self._call(
            "load_log_candidate", plan_id=plan_id, domain_id=domain_id
        )

    def finalize_log_candidate(
        self,
        *,
        plan_id: str,
        domain_id: str,
        header_receipt_ids: Sequence[str],
    ) -> str:
        """Atomic leaf insert + AGREED for a candidate with complete headers."""
        return self._call(
            "finalize_log_candidate",
            plan_id=plan_id,
            domain_id=domain_id,
            header_receipt_ids=tuple(header_receipt_ids),
        )

    def list_missing_candidate_blocks(
        self,
        *,
        plan_id: str,
        limit: int = HEADER_WORK_PAGE_SIZE,
        after_block_number: int | None = None,
    ) -> list[int]:
        """Distinct candidate-required blocks lacking a header (bounded keyset page)."""
        return self._call(
            "list_missing_candidate_blocks",
            plan_id=plan_id,
            limit=limit,
            after_block_number=after_block_number,
        )

    def list_finalizable_candidates(
        self,
        *,
        plan_id: str,
        limit: int = FINALIZE_WORK_PAGE_SIZE,
        after_domain_id: str | None = None,
    ) -> dict[str, Any]:
        """Bounded candidate scan page; ready subset + keyset cursor.

        Examines at most ``limit`` PENDING candidate rows (not the full table).
        Returns ``ready_domain_ids``, ``scan_through_domain_id``, and ``exhausted``.
        """
        return self._call(
            "list_finalizable_candidates",
            plan_id=plan_id,
            limit=limit,
            after_domain_id=after_domain_id,
        )

    def begin_plan_resume_session(self, *, plan_id: str) -> dict[str, Any]:
        """Bump shared plan resume generation (invalidates prior session auth marks)."""
        return self._call("begin_plan_resume_session", plan_id=plan_id)

    def authenticate_plan_attach(
        self,
        *,
        plan_id: str,
        plan_config: PlanConfig,
        execution_policy: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Authenticate persisted plan row + immutable execution-policy identity."""
        return self._call(
            "authenticate_plan_attach",
            plan_id=plan_id,
            plan_config=plan_config,
            execution_policy=dict(execution_policy),
        )

    def authenticate_resumed_candidates(
        self,
        *,
        plan_id: str,
        force: bool = False,
        limit: int = CLAIM_SCAN_PAGE_SIZE,
    ) -> dict[str, Any]:
        """One bounded page of resume re-validation for the active generation.

        Normal mode authenticates candidates not yet stamped for the active
        generation. ``force=True`` revalidates the next page of all candidates
        (still one page; caller continues until ``complete``).
        """
        return self._call(
            "authenticate_resumed_candidates",
            plan_id=plan_id,
            force=force,
            limit=limit,
        )

    def reauthenticate_root_domain_set(self, *, plan_id: str) -> dict[str, Any]:
        """Stream-recompute every root domain_id from semantic fields; return count+digest."""
        return self._call("reauthenticate_root_domain_set", plan_id=plan_id)

    def header_backlog_count(self, *, plan_id: str) -> int:
        """Exact distinct missing candidate-header block count (no full scan per call)."""
        return self._call("header_backlog_count", plan_id=plan_id)

    def claim_order_version(self, *, plan_id: str) -> str:
        return self._call("claim_order_version", plan_id=plan_id)

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
            "ensure_production_plan_shell": self._op_ensure_production_plan_shell,
            "initialize_production_roots_batch": self._op_initialize_production_roots_batch,
            "authenticate_ready_root_manifest": self._op_authenticate_ready_root_manifest,
            "load_root_manifest": self._op_load_root_manifest,
            "commit_log_candidate": self._op_commit_log_candidate,
            "load_log_candidate": self._op_load_log_candidate,
            "finalize_log_candidate": self._op_finalize_log_candidate,
            "list_missing_candidate_blocks": self._op_list_missing_candidate_blocks,
            "list_finalizable_candidates": self._op_list_finalizable_candidates,
            "authenticate_resumed_candidates": self._op_authenticate_resumed_candidates,
            "authenticate_plan_attach": self._op_authenticate_plan_attach,
            "begin_plan_resume_session": self._op_begin_plan_resume_session,
            "reauthenticate_root_domain_set": self._op_reauthenticate_root_domain_set,
            "header_backlog_count": self._op_header_backlog_count,
            "claim_order_version": self._op_claim_order_version,
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
                try:
                    recovered_request_json = _canonical_request_json(request)
                except PairEventV2Error:
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
                        request_json=recovered_request_json,
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
                        request_json=recovered_request_json,
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
                    request_json=recovered_request_json,
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
            if isinstance(request, Mapping):
                meta_request: Mapping[str, Any] | list[Any] = dict(request)
                method_label = str(request.get("method") or "rpc")
            elif isinstance(request, list):
                meta_request = list(request)
                method_label = "batch"
            else:
                raise PairEventV2Error(
                    "persisted spool request must be a JSON-RPC object or batch array"
                )
            metadata = AcquisitionMetadata(
                source_id=SOURCE_ID,
                acquisition_id=descriptor.acquisition_id,
                request=meta_request,
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
                    f"{descriptor.provider_org}_{method_label}_"
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
        request: Mapping[str, Any] | Sequence[Any] | None,
        require_successful_body: bool = True,
        require_request_match: bool = True,
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
        try:
            stored_request = json.loads(row["request_json"] or "null")
        except json.JSONDecodeError as exc:
            raise PairEventV2Error("raw acquisition request_json is not JSON") from exc
        # Canonical stored request JSON for AuthenticatedEvidence.request_json.
        expected = _canonical_json(stored_request)
        if require_request_match:
            if request is None:
                raise PairEventV2Error("request match required but request is None")
            if isinstance(request, Mapping):
                wanted = _canonical_json(dict(request))
            else:
                wanted = _canonical_json(list(request))
            if expected != wanted:
                raise PairEventV2Error(
                    "raw acquisition request does not match expected"
                )
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
                # Coherent zero backlog + resume generation at plan birth.
                conn.execute(
                    f"INSERT OR IGNORE INTO {HEADER_BACKLOG_METRIC_TABLE} "
                    "(plan_id, missing_count) VALUES (?, 0)",
                    (plan.plan_id,),
                )
                conn.execute(
                    f"INSERT OR IGNORE INTO {PLAN_RESUME_SESSION_TABLE} "
                    "(plan_id, active_generation, updated_at) VALUES (?,?,?)",
                    (plan.plan_id, 1, _now()),
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
                conn.execute(
                    f"INSERT OR IGNORE INTO {HEADER_BACKLOG_METRIC_TABLE} "
                    "(plan_id, missing_count) VALUES (?, 0)",
                    (plan.plan_id,),
                )
                conn.execute(
                    f"INSERT OR IGNORE INTO {PLAN_RESUME_SESSION_TABLE} "
                    "(plan_id, active_generation, updated_at) VALUES (?,?,?)",
                    (plan.plan_id, 1, _now()),
                )
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

    def _op_ensure_production_plan_shell(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        config: PlanConfig,
        execution_policy: Mapping[str, Any],
    ) -> str:
        del writer
        if config.plan_id() != PRODUCTION_PLAN_ID:
            raise PairEventV2Error("production shell requires pinned plan_id")
        if config.initial_cohort_size != PRODUCTION_INITIAL_COHORT_SIZE:
            raise PairEventV2Error("production shell requires cohort size 8")
        if _contains_sensitive_key(execution_policy):
            raise PairEventV2Error("execution policy contains sensitive keys")
        if str(execution_policy.get("plan_id", "")) != config.plan_id():
            raise PairEventV2Error("execution policy plan_id must bind the plan")
        if (
            str(execution_policy.get("claim_order_version"))
            != CLAIM_ORDER_VERSION_DOMAIN_HASH_V1
        ):
            raise PairEventV2Error(
                "production execution policy must use domain_hash_v1 claim order"
            )
        policy_json = _canonical_json(dict(execution_policy))
        policy_id = _identity("pol_", json.loads(policy_json))
        expected_record = plan_record_from_config(config, created_at=_now())
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                f"SELECT * FROM {PLAN_TABLE} WHERE plan_id = ?",
                (config.plan_id(),),
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
                conn.execute(
                    f"INSERT INTO {EXECUTION_POLICY_TABLE} ("
                    + ",".join(EXECUTION_POLICY_RECORD_COLUMNS)
                    + ") VALUES (?,?,?,?,?)",
                    (
                        policy_id,
                        config.plan_id(),
                        policy_json,
                        EXECUTION_POLICY_SCHEMA_VERSION,
                        _now(),
                    ),
                )
                conn.execute(
                    f"INSERT OR IGNORE INTO {HEADER_BACKLOG_METRIC_TABLE} "
                    "(plan_id, missing_count) VALUES (?, 0)",
                    (config.plan_id(),),
                )
                conn.execute(
                    f"INSERT OR IGNORE INTO {PLAN_RESUME_SESSION_TABLE} "
                    "(plan_id, active_generation, updated_at) VALUES (?,?,?)",
                    (config.plan_id(), 1, _now()),
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
                    raise PairEventV2Error(
                        "persisted production plan row is not the requested plan"
                    )
                conn.execute(
                    f"INSERT OR IGNORE INTO {HEADER_BACKLOG_METRIC_TABLE} "
                    "(plan_id, missing_count) VALUES (?, 0)",
                    (config.plan_id(),),
                )
                conn.execute(
                    f"INSERT OR IGNORE INTO {PLAN_RESUME_SESSION_TABLE} "
                    "(plan_id, active_generation, updated_at) VALUES (?,?,?)",
                    (config.plan_id(), 1, _now()),
                )
                policy_row = conn.execute(
                    f"SELECT * FROM {EXECUTION_POLICY_TABLE} WHERE plan_id = ?",
                    (config.plan_id(),),
                ).fetchone()
                if policy_row is None:
                    raise PairEventV2Error("production plan missing execution policy")
                if (
                    str(policy_row["identity_payload_json"]) != policy_json
                    or str(policy_row["policy_id"]) != policy_id
                ):
                    raise PairEventV2Error(
                        "production execution policy mismatch on resume"
                    )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return config.plan_id()

    def _op_initialize_production_roots_batch(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
        roots: Sequence[RootFilterPlan],
        registry_parquet_sha256: str,
        registry_parquet_bytes: int,
        expected_root_count: int,
        expected_root_domain_set_sha256: str,
        expected_pool_topic_blocks: int,
        finalize: bool,
    ) -> dict[str, Any]:
        """Insert a batch of production roots; optionally finalize READY gate."""
        del writer
        plan_id = str(plan_id)
        if plan_id != PRODUCTION_PLAN_ID:
            raise PairEventV2Error("production initializer requires pinned plan_id")
        if registry_parquet_sha256 != PRODUCTION_REGISTRY_PARQUET_SHA256:
            raise PairEventV2Error("registry_parquet_sha256 is not the accepted pin")
        if int(registry_parquet_bytes) != PRODUCTION_REGISTRY_PARQUET_BYTES:
            raise PairEventV2Error("registry_parquet_bytes is not the accepted pin")
        if int(expected_root_count) != PRODUCTION_ROOT_COUNT:
            raise PairEventV2Error("expected_root_count is not the accepted pin")
        if expected_root_domain_set_sha256 != PRODUCTION_ROOT_DOMAIN_SET_SHA256:
            raise PairEventV2Error("root_domain_set_sha256 is not the accepted pin")
        if int(expected_pool_topic_blocks) != PRODUCTION_POOL_TOPIC_BLOCKS:
            raise PairEventV2Error("pool_topic_blocks is not the accepted pin")
        now = _now()
        conn.execute("BEGIN IMMEDIATE")
        try:
            plan_row = conn.execute(
                f"SELECT plan_id, initial_cohort_size FROM {PLAN_TABLE} "
                "WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
            if plan_row is None:
                raise PairEventV2Error("production plan row missing — create plan first")
            if int(plan_row["initial_cohort_size"]) != PRODUCTION_INITIAL_COHORT_SIZE:
                raise PairEventV2Error("production plan must use cohort size 8")
            manifest = conn.execute(
                f"SELECT * FROM {ROOT_MANIFEST_TABLE} WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
            if manifest is None:
                conn.execute(
                    f"INSERT INTO {ROOT_MANIFEST_TABLE} ("
                    "plan_id, registry_dataset_id, registry_parquet_sha256, "
                    "registry_parquet_bytes, root_count, root_domain_set_sha256, "
                    "pool_topic_blocks, status, created_at, updated_at"
                    ") VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        plan_id,
                        ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID,
                        registry_parquet_sha256,
                        int(registry_parquet_bytes),
                        int(expected_root_count),
                        expected_root_domain_set_sha256,
                        int(expected_pool_topic_blocks),
                        "INITIALIZING",
                        now,
                        now,
                    ),
                )
            else:
                if str(manifest["status"]) == "READY":
                    # Idempotent: READY manifest rejects further mutation.
                    if roots:
                        raise PairEventV2Error(
                            "production root manifest is READY; refuse additional roots"
                        )
                    if finalize:
                        conn.execute("COMMIT")
                        return {
                            "status": "READY",
                            "inserted": 0,
                            "root_count": int(manifest["root_count"]),
                        }
                    conn.execute("COMMIT")
                    return {
                        "status": "READY",
                        "inserted": 0,
                        "root_count": int(manifest["root_count"]),
                    }
            inserted = 0
            for root in roots:
                if root.plan_id != plan_id:
                    raise PairEventV2Error("root plan_id mismatch")
                node = QueryNode(plan_id=plan_id, domain=root.domain)
                existing = conn.execute(
                    f"SELECT domain_id, start_block, end_block, addresses_json, "
                    f"topics_json FROM {NODE_TABLE} "
                    "WHERE plan_id = ? AND domain_id = ?",
                    (plan_id, node.domain_id),
                ).fetchone()
                if existing is None:
                    self._insert_node(conn, node, attempt=0, updated_at=now)
                    inserted += 1
                else:
                    # Resume idempotency: existing root must match exactly.
                    if (
                        int(existing["start_block"]) != root.domain.start_block
                        or int(existing["end_block"]) != root.domain.end_block
                        or str(existing["addresses_json"])
                        != _canonical_json(list(root.domain.addresses))
                        or str(existing["topics_json"])
                        != _canonical_json(list(root.domain.topics))
                    ):
                        raise PairEventV2Error(
                            "existing production root does not match expected domain"
                        )
            status = "INITIALIZING"
            if finalize:
                count, digest = self._stream_root_domain_digest(conn, plan_id)
                if count != PRODUCTION_ROOT_COUNT:
                    raise PairEventV2Error(
                        "production root count mismatch at finalize",
                    )
                if digest != PRODUCTION_ROOT_DOMAIN_SET_SHA256:
                    raise PairEventV2Error(
                        "production root domain-set digest mismatch at finalize"
                    )
                conn.execute(
                    f"UPDATE {ROOT_MANIFEST_TABLE} SET status = 'READY', "
                    "updated_at = ? WHERE plan_id = ?",
                    (now, plan_id),
                )
                status = "READY"
            else:
                conn.execute(
                    f"UPDATE {ROOT_MANIFEST_TABLE} SET updated_at = ? "
                    "WHERE plan_id = ?",
                    (now, plan_id),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        count_row = conn.execute(
            f"SELECT COUNT(*) AS c FROM {NODE_TABLE} "
            "WHERE plan_id = ? AND parent_domain_id IS NULL",
            (plan_id,),
        ).fetchone()
        return {
            "status": status,
            "inserted": inserted,
            "root_count": int(count_row["c"]) if count_row else 0,
        }

    def _stream_root_domain_digest(
        self, conn: sqlite3.Connection, plan_id: str
    ) -> tuple[int, str]:
        """Recompute every root domain_id from fields; hash ordered set without fetchall().

        READY authority requires that each root row's domain_id recompute from
        start_block/end_block/addresses/topics (not merely re-hashing stored ids).
        """
        hasher = hashlib.sha256()
        count = 0
        cursor = conn.execute(
            f"SELECT domain_id, start_block, end_block, addresses_json, topics_json "
            f"FROM {NODE_TABLE} "
            "WHERE plan_id = ? AND parent_domain_id IS NULL "
            "ORDER BY domain_id",
            (plan_id,),
        )
        while True:
            rows = cursor.fetchmany(2048)
            if not rows:
                break
            for row in rows:
                domain_id = str(row["domain_id"])
                try:
                    addresses = tuple(json.loads(str(row["addresses_json"])))
                    topics = tuple(json.loads(str(row["topics_json"])))
                except (json.JSONDecodeError, TypeError) as exc:
                    raise PairEventV2Error(
                        "root addresses/topics JSON is malformed during READY re-auth"
                    ) from exc
                if not isinstance(addresses, tuple) or not isinstance(topics, tuple):
                    raise PairEventV2Error(
                        "root addresses/topics must decode to sequences"
                    )
                domain = QueryDomain(
                    start_block=int(row["start_block"]),
                    end_block=int(row["end_block"]),
                    addresses=addresses,
                    topics=topics,
                )
                recomputed = domain.domain_id(plan_id)
                if recomputed != domain_id:
                    raise PairEventV2Error(
                        "READY root domain_id does not recompute from "
                        "start/end/addresses/topics fields"
                    )
                hasher.update(domain_id.encode("ascii"))
                hasher.update(b"\n")
                count += 1
        return count, hasher.hexdigest()

    def _op_authenticate_ready_root_manifest(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
        registry_parquet_sha256: str,
        registry_parquet_bytes: int,
    ) -> RootManifestRecord:
        del writer
        row = conn.execute(
            f"SELECT * FROM {ROOT_MANIFEST_TABLE} WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()
        if row is None:
            raise PairEventV2Error("root manifest missing")
        if str(row["status"]) != "READY":
            raise PairEventV2Error("root manifest is not READY")
        if str(row["registry_dataset_id"]) != ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID:
            raise PairEventV2Error("READY manifest registry_dataset_id drift")
        if str(row["registry_parquet_sha256"]) != registry_parquet_sha256:
            raise PairEventV2Error("READY manifest parquet sha256 drift")
        if int(row["registry_parquet_bytes"]) != int(registry_parquet_bytes):
            raise PairEventV2Error("READY manifest parquet bytes drift")
        # Semantic re-auth first: every root domain_id from start/end/addresses/topics.
        # Field tamper fails here before production pin checks.
        count, digest = self._stream_root_domain_digest(conn, plan_id)
        if count != int(row["root_count"]) or digest != str(row["root_domain_set_sha256"]):
            raise PairEventV2Error(
                "READY manifest stored count/digest disagree with recomputed root set"
            )
        if str(row["registry_parquet_sha256"]) != PRODUCTION_REGISTRY_PARQUET_SHA256:
            raise PairEventV2Error("READY manifest parquet sha256 not production pin")
        if int(row["registry_parquet_bytes"]) != PRODUCTION_REGISTRY_PARQUET_BYTES:
            raise PairEventV2Error("READY manifest parquet bytes not production pin")
        if int(row["root_count"]) != PRODUCTION_ROOT_COUNT:
            raise PairEventV2Error("READY manifest root_count not production pin")
        if int(row["pool_topic_blocks"]) != PRODUCTION_POOL_TOPIC_BLOCKS:
            raise PairEventV2Error("READY manifest pool_topic_blocks not production pin")
        if str(row["root_domain_set_sha256"]) != PRODUCTION_ROOT_DOMAIN_SET_SHA256:
            raise PairEventV2Error("READY manifest root digest not production pin")
        if count != PRODUCTION_ROOT_COUNT or digest != PRODUCTION_ROOT_DOMAIN_SET_SHA256:
            raise PairEventV2Error(
                "READY manifest root rows do not recompute pinned domain-set digest"
            )
        return RootManifestRecord(
            plan_id=str(row["plan_id"]),
            registry_dataset_id=str(row["registry_dataset_id"]),
            registry_parquet_sha256=str(row["registry_parquet_sha256"]),
            registry_parquet_bytes=int(row["registry_parquet_bytes"]),
            root_count=int(row["root_count"]),
            root_domain_set_sha256=str(row["root_domain_set_sha256"]),
            pool_topic_blocks=int(row["pool_topic_blocks"]),
            status="READY",
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _op_load_root_manifest(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
    ) -> RootManifestRecord | None:
        del writer
        row = conn.execute(
            f"SELECT * FROM {ROOT_MANIFEST_TABLE} WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()
        if row is None:
            return None
        return RootManifestRecord(
            plan_id=str(row["plan_id"]),
            registry_dataset_id=str(row["registry_dataset_id"]),
            registry_parquet_sha256=str(row["registry_parquet_sha256"]),
            registry_parquet_bytes=int(row["registry_parquet_bytes"]),
            root_count=int(row["root_count"]),
            root_domain_set_sha256=str(row["root_domain_set_sha256"]),
            pool_topic_blocks=int(row["pool_topic_blocks"]),
            status=str(row["status"]),  # type: ignore[arg-type]
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _op_commit_log_candidate(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        claim: Claim,
        candidate_kwargs: Mapping[str, Any],
        blocks: Sequence[tuple[int, str | None, bool]],
    ) -> str:
        """Commit immutable candidate; return node to PENDING; delete lease.

        Attempt is unchanged. No AGREED coverage. Candidate grants zero PTB.
        """
        del writer
        now = _now()
        plan_id = claim.plan_id
        domain_id = claim.domain_id
        attempt = int(claim.attempt)
        candidate_id = compute_log_candidate_id(
            plan_id=plan_id,
            domain_id=domain_id,
            attempt=attempt,
            log_identity_sha256=str(candidate_kwargs["log_identity_sha256"]),
            primary_logs_raw_object_id=str(
                candidate_kwargs["primary_logs_raw_object_id"]
            ),
            secondary_logs_raw_object_id=str(
                candidate_kwargs["secondary_logs_raw_object_id"]
            ),
            primary_logs_acquisition_id=str(
                candidate_kwargs["primary_logs_acquisition_id"]
            ),
            secondary_logs_acquisition_id=str(
                candidate_kwargs["secondary_logs_acquisition_id"]
            ),
        )
        conn.execute("BEGIN IMMEDIATE")
        try:
            lease = conn.execute(
                f"SELECT lease_token FROM {LEASE_TABLE} "
                "WHERE plan_id = ? AND domain_id = ?",
                (plan_id, domain_id),
            ).fetchone()
            if lease is None or str(lease["lease_token"]) != claim.lease_token:
                raise _LeaseLostError("claim lease missing or mismatched")
            existing = conn.execute(
                f"SELECT candidate_id FROM {LOG_CANDIDATE_TABLE} "
                "WHERE plan_id = ? AND domain_id = ?",
                (plan_id, domain_id),
            ).fetchone()
            if existing is not None:
                if str(existing["candidate_id"]) != candidate_id:
                    raise PairEventV2Error(
                        "domain already has a different log candidate"
                    )
            else:
                # Commit-time auth stamps the active generation so this process's
                # concurrent claims may exclude immediately; other generations must
                # re-replay after begin_plan_resume_session.
                gen = self._active_resume_generation(conn, plan_id)
                conn.execute(
                    f"INSERT INTO {LOG_CANDIDATE_TABLE} ("
                    "candidate_id, plan_id, domain_id, attempt, log_identity_sha256, "
                    "log_count, primary_provider_org, secondary_provider_org, "
                    "primary_logs_raw_object_id, secondary_logs_raw_object_id, "
                    "primary_logs_acquisition_id, secondary_logs_acquisition_id, "
                    "request_json, created_at, session_auth_generation"
                    ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        candidate_id,
                        plan_id,
                        domain_id,
                        attempt,
                        str(candidate_kwargs["log_identity_sha256"]),
                        int(candidate_kwargs["log_count"]),
                        normalize_provider_org(
                            str(candidate_kwargs["primary_provider_org"])
                        ),
                        normalize_provider_org(
                            str(candidate_kwargs["secondary_provider_org"])
                        ),
                        str(candidate_kwargs["primary_logs_raw_object_id"]),
                        str(candidate_kwargs["secondary_logs_raw_object_id"]),
                        str(candidate_kwargs["primary_logs_acquisition_id"]),
                        str(candidate_kwargs["secondary_logs_acquisition_id"]),
                        str(candidate_kwargs["request_json"]),
                        now,
                        gen,
                    ),
                )
                for block_number, expected_hash, is_boundary in blocks:
                    conn.execute(
                        f"INSERT INTO {LOG_CANDIDATE_BLOCK_TABLE} ("
                        "plan_id, domain_id, block_number, expected_block_hash, "
                        "is_boundary) VALUES (?,?,?,?,?)",
                        (
                            plan_id,
                            domain_id,
                            int(block_number),
                            expected_hash,
                            1 if is_boundary else 0,
                        ),
                    )
            # Return to PENDING at unchanged attempt; release lease. No coverage.
            conn.execute(
                f"UPDATE {NODE_TABLE} SET status = 'PENDING', updated_at = ? "
                "WHERE plan_id = ? AND domain_id = ? AND status = 'IN_FLIGHT'",
                (now, plan_id, domain_id),
            )
            if conn.execute("SELECT changes()").fetchone()[0] != 1:
                raise PairEventV2Error("candidate commit requires IN_FLIGHT node")
            conn.execute(
                f"DELETE FROM {LEASE_TABLE} WHERE plan_id = ? AND domain_id = ?",
                (plan_id, domain_id),
            )
            # Commit-time raw re-auth before durable candidate is trusted.
            # Session resume re-replays again on coordinator restart (watermark).
            if existing is None:
                self._authenticate_candidate_row(
                    conn, plan_id=plan_id, domain_id=domain_id
                )
                self._note_missing_blocks(conn, plan_id, blocks)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return candidate_id

    def _op_load_log_candidate(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
        domain_id: str,
    ) -> dict[str, Any] | None:
        del writer
        row = conn.execute(
            f"SELECT * FROM {LOG_CANDIDATE_TABLE} "
            "WHERE plan_id = ? AND domain_id = ?",
            (plan_id, domain_id),
        ).fetchone()
        if row is None:
            return None
        blocks = conn.execute(
            f"SELECT block_number, expected_block_hash, is_boundary "
            f"FROM {LOG_CANDIDATE_BLOCK_TABLE} "
            "WHERE plan_id = ? AND domain_id = ? ORDER BY block_number",
            (plan_id, domain_id),
        ).fetchall()
        return {
            "candidate_id": str(row["candidate_id"]),
            "plan_id": str(row["plan_id"]),
            "domain_id": str(row["domain_id"]),
            "attempt": int(row["attempt"]),
            "log_identity_sha256": str(row["log_identity_sha256"]),
            "log_count": int(row["log_count"]),
            "primary_provider_org": str(row["primary_provider_org"]),
            "secondary_provider_org": str(row["secondary_provider_org"]),
            "primary_logs_raw_object_id": str(row["primary_logs_raw_object_id"]),
            "secondary_logs_raw_object_id": str(row["secondary_logs_raw_object_id"]),
            "primary_logs_acquisition_id": str(row["primary_logs_acquisition_id"]),
            "secondary_logs_acquisition_id": str(row["secondary_logs_acquisition_id"]),
            "request_json": str(row["request_json"]),
            "blocks": [
                (
                    int(b["block_number"]),
                    None
                    if b["expected_block_hash"] is None
                    else str(b["expected_block_hash"]),
                    bool(int(b["is_boundary"])),
                )
                for b in blocks
            ],
        }

    def _op_finalize_log_candidate(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
        domain_id: str,
        header_receipt_ids: Sequence[str],
    ) -> str:
        """Atomic AGREED transition after full candidate + header raw replay."""
        del writer
        now = _now()
        conn.execute("BEGIN IMMEDIATE")
        try:
            cand = conn.execute(
                f"SELECT * FROM {LOG_CANDIDATE_TABLE} "
                "WHERE plan_id = ? AND domain_id = ?",
                (plan_id, domain_id),
            ).fetchone()
            if cand is None:
                raise PairEventV2Error("log candidate missing at finalize")
            node_row = conn.execute(
                f"SELECT * FROM {NODE_TABLE} WHERE plan_id = ? AND domain_id = ?",
                (plan_id, domain_id),
            ).fetchone()
            if node_row is None:
                raise PairEventV2Error("query node missing at finalize")
            if str(node_row["status"]) == "AGREED":
                leaf = conn.execute(
                    f"SELECT leaf_receipt_id FROM {LEAF_TABLE} "
                    "WHERE plan_id = ? AND domain_id = ?",
                    (plan_id, domain_id),
                ).fetchone()
                if leaf is None:
                    raise PairEventV2Error("AGREED node missing leaf")
                conn.execute("COMMIT")
                return str(leaf["leaf_receipt_id"])
            if str(node_row["status"]) != "PENDING":
                raise PairEventV2Error(
                    "finalize requires PENDING node with log candidate"
                )
            domain = QueryDomain(
                start_block=int(node_row["start_block"]),
                end_block=int(node_row["end_block"]),
                addresses=tuple(json.loads(str(node_row["addresses_json"]))),
                topics=tuple(json.loads(str(node_row["topics_json"]))),
            )
            if domain.domain_id(plan_id) != domain_id:
                raise PairEventV2Error("node domain_id does not match domain fields")
            # Authenticate dual log raw bodies + request + provider orgs.
            try:
                request = json.loads(str(cand["request_json"]))
            except json.JSONDecodeError as exc:
                raise PairEventV2Error("candidate request_json is not JSON") from exc
            if not isinstance(request, Mapping):
                raise PairEventV2Error("candidate request_json must be an object")
            expected_request = request_for_domain(domain)
            if _canonical_json(dict(request)) != _canonical_json(expected_request):
                raise PairEventV2Error(
                    "candidate request does not match domain canonical request"
                )
            p_ev = self._authenticate_raw_pair(
                conn,
                acquisition_id=str(cand["primary_logs_acquisition_id"]),
                raw_object_id=str(cand["primary_logs_raw_object_id"]),
                provider_org=str(cand["primary_provider_org"]),
                request=request,
            )
            s_ev = self._authenticate_raw_pair(
                conn,
                acquisition_id=str(cand["secondary_logs_acquisition_id"]),
                raw_object_id=str(cand["secondary_logs_raw_object_id"]),
                provider_org=str(cand["secondary_provider_org"]),
                request=request,
            )
            p_payload = _load_authenticated_rpc(
                p_ev, request, max_bytes=self._max_body_bytes, raw_root=self._raw_root
            )
            s_payload = _load_authenticated_rpc(
                s_ev, request, max_bytes=self._max_body_bytes, raw_root=self._raw_root
            )
            p_logs = p_payload.get("result")
            s_logs = s_payload.get("result")
            if not isinstance(p_logs, list) or not isinstance(s_logs, list):
                raise PairEventV2Error("candidate log bodies missing result lists")
            identities, digest = reconcile_log_sets_v2(p_logs, s_logs, domain)
            if digest != str(cand["log_identity_sha256"]):
                raise PairEventV2Error("candidate log_identity_sha256 replay mismatch")
            if len(identities) != int(cand["log_count"]):
                raise PairEventV2Error("candidate log_count replay mismatch")
            recomputed_id = compute_log_candidate_id(
                plan_id=plan_id,
                domain_id=domain_id,
                attempt=int(cand["attempt"]),
                log_identity_sha256=digest,
                primary_logs_raw_object_id=str(cand["primary_logs_raw_object_id"]),
                secondary_logs_raw_object_id=str(cand["secondary_logs_raw_object_id"]),
                primary_logs_acquisition_id=str(cand["primary_logs_acquisition_id"]),
                secondary_logs_acquisition_id=str(
                    cand["secondary_logs_acquisition_id"]
                ),
            )
            if recomputed_id != str(cand["candidate_id"]):
                raise PairEventV2Error("candidate_id does not match recomputed identity")
            expected_blocks = required_blocks_from_identities(
                identities, domain=domain
            )
            stored_blocks = conn.execute(
                f"SELECT block_number, expected_block_hash, is_boundary "
                f"FROM {LOG_CANDIDATE_BLOCK_TABLE} "
                "WHERE plan_id = ? AND domain_id = ? ORDER BY block_number",
                (plan_id, domain_id),
            ).fetchall()
            stored_norm = [
                (
                    int(b["block_number"]),
                    None
                    if b["expected_block_hash"] is None
                    else str(b["expected_block_hash"]),
                    bool(int(b["is_boundary"])),
                )
                for b in stored_blocks
            ]
            if tuple(stored_norm) != expected_blocks:
                raise PairEventV2Error(
                    "candidate required blocks do not match replay derivation"
                )
            # Replay each header receipt body (scalar or batch-backed).
            verified_header_ids: list[str] = []
            for block_number, expected_hash, _is_boundary in expected_blocks:
                hrow = conn.execute(
                    f"SELECT * FROM {HEADER_TABLE} "
                    "WHERE plan_id = ? AND block_number = ?",
                    (plan_id, int(block_number)),
                ).fetchone()
                if hrow is None:
                    raise PairEventV2Error(
                        f"canonical header missing for block {block_number}"
                    )
                header_id = str(hrow["header_receipt_id"])
                if header_id not in set(header_receipt_ids):
                    raise PairEventV2Error(
                        f"header {header_id} not in finalize header set"
                    )
                # Authenticate header raw pairs and re-check fields.
                hp = self._authenticate_raw_pair(
                    conn,
                    acquisition_id=str(hrow["primary_acquisition_id"]),
                    raw_object_id=str(hrow["primary_raw_object_id"]),
                    provider_org=str(hrow["primary_provider_org"]),
                    request=None,  # allow batch or scalar
                    require_request_match=False,
                )
                hs = self._authenticate_raw_pair(
                    conn,
                    acquisition_id=str(hrow["secondary_acquisition_id"]),
                    raw_object_id=str(hrow["secondary_raw_object_id"]),
                    provider_org=str(hrow["secondary_provider_org"]),
                    request=None,
                    require_request_match=False,
                )
                p_hdr = self._header_result_from_evidence(
                    hp, block_number=int(block_number)
                )
                s_hdr = self._header_result_from_evidence(
                    hs, block_number=int(block_number)
                )
                if (
                    p_hdr["hash"] != s_hdr["hash"]
                    or p_hdr["timestamp"] != s_hdr["timestamp"]
                    or p_hdr["number"] != int(block_number)
                    or s_hdr["number"] != int(block_number)
                ):
                    raise PairEventV2Error(
                        f"header replay disagreement at block {block_number}"
                    )
                if expected_hash is not None and p_hdr["hash"] != expected_hash:
                    raise PairEventV2Error(
                        f"header hash disagrees with candidate at block {block_number}"
                    )
                if str(hrow["block_hash"]) != p_hdr["hash"]:
                    raise PairEventV2Error(
                        f"stored header hash drift at block {block_number}"
                    )
                verified_header_ids.append(header_id)
            if sorted(verified_header_ids) != sorted(header_receipt_ids):
                raise PairEventV2Error(
                    "finalize header set does not match verified headers"
                )
            leaf_kwargs = {
                "plan_id": plan_id,
                "domain": domain,
                "log_identity_sha256": digest,
                "primary_provider_org": str(cand["primary_provider_org"]),
                "secondary_provider_org": str(cand["secondary_provider_org"]),
                "primary_logs_raw_object_id": str(cand["primary_logs_raw_object_id"]),
                "secondary_logs_raw_object_id": str(
                    cand["secondary_logs_raw_object_id"]
                ),
                "primary_logs_acquisition_id": str(
                    cand["primary_logs_acquisition_id"]
                ),
                "secondary_logs_acquisition_id": str(
                    cand["secondary_logs_acquisition_id"]
                ),
                "log_count": len(identities),
                "canonical_header_receipt_ids": verified_header_ids,
            }
            leaf = make_leaf_receipt_record(**leaf_kwargs, completed_at=now)
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
                    (plan_id, leaf.leaf_receipt_id, header_id),
                )
            # Post-write integrity (still in TX): prove leaf/deps landed and node
            # remains PENDING before AGREED. Failures here roll back all writes.
            leaf_present = conn.execute(
                f"SELECT leaf_receipt_id FROM {LEAF_TABLE} "
                "WHERE plan_id = ? AND domain_id = ?",
                (plan_id, domain_id),
            ).fetchone()
            if leaf_present is None or str(leaf_present["leaf_receipt_id"]) != (
                leaf.leaf_receipt_id
            ):
                raise PairEventV2Error("finalize leaf write missing before AGREED")
            dep_count = conn.execute(
                f"SELECT COUNT(*) AS c FROM {DEP_TABLE} "
                "WHERE plan_id = ? AND leaf_receipt_id = ?",
                (plan_id, leaf.leaf_receipt_id),
            ).fetchone()
            if int(dep_count["c"] if dep_count else 0) != len(
                leaf.canonical_header_receipt_ids
            ):
                raise PairEventV2Error("finalize dependency write incomplete")
            status_row = conn.execute(
                f"SELECT status FROM {NODE_TABLE} "
                "WHERE plan_id = ? AND domain_id = ?",
                (plan_id, domain_id),
            ).fetchone()
            if status_row is None or str(status_row["status"]) != "PENDING":
                raise PairEventV2Error(
                    "node status changed during finalize after leaf write"
                )
            conn.execute(
                f"UPDATE {NODE_TABLE} SET status = 'AGREED', updated_at = ? "
                "WHERE plan_id = ? AND domain_id = ? AND status = 'PENDING'",
                (now, plan_id, domain_id),
            )
            if conn.execute("SELECT changes()").fetchone()[0] != 1:
                raise PairEventV2Error("finalize could not mark node AGREED")
            conn.execute("COMMIT")
            return leaf.leaf_receipt_id
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def _authenticate_raw_pair(
        self,
        conn: sqlite3.Connection,
        *,
        acquisition_id: str,
        raw_object_id: str,
        provider_org: str,
        request: Mapping[str, Any] | Sequence[Any] | None,
        require_request_match: bool = True,
    ) -> AuthenticatedEvidence:
        """Re-open raw bytes and verify catalog pairing for finalize/header replay."""
        return self._authenticate_evidence(
            conn,
            acquisition_id=acquisition_id,
            raw_object_id=raw_object_id,
            provider_org=provider_org,
            request=request,
            require_request_match=require_request_match,
            require_successful_body=True,
        )

    def _header_result_from_evidence(
        self, evidence: AuthenticatedEvidence, *, block_number: int
    ) -> dict[str, Any]:
        """Extract one block header from scalar or batch-backed authenticated raw."""
        return _extract_header_result_from_evidence(
            evidence,
            block_number=block_number,
            max_bytes=self._max_body_bytes,
            raw_root=self._raw_root,
        )

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

    def _claim_order_version(self, conn: sqlite3.Connection, plan_id: str) -> str:
        """Read authenticated execution-policy claim order (default chronological)."""
        row = conn.execute(
            f"SELECT identity_payload_json FROM {EXECUTION_POLICY_TABLE} "
            "WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()
        if row is None:
            return CLAIM_ORDER_VERSION_CHRONOLOGICAL_V1
        try:
            payload = json.loads(str(row["identity_payload_json"]))
        except json.JSONDecodeError as exc:
            raise PairEventV2Error("execution policy JSON is malformed") from exc
        order = str(
            payload.get("claim_order_version") or CLAIM_ORDER_VERSION_CHRONOLOGICAL_V1
        )
        if order not in {
            CLAIM_ORDER_VERSION_CHRONOLOGICAL_V1,
            CLAIM_ORDER_VERSION_DOMAIN_HASH_V1,
        }:
            raise PairEventV2Error(f"unknown claim_order_version: {order}")
        return order

    def _op_claim_order_version(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
    ) -> str:
        del writer
        return self._claim_order_version(conn, plan_id)

    def _op_list_missing_candidate_blocks(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
        limit: int = HEADER_WORK_PAGE_SIZE,
        after_block_number: int | None = None,
    ) -> list[int]:
        del writer
        page = int(limit)
        if page <= 0:
            raise PairEventV2Error("list_missing_candidate_blocks limit must be positive")
        if page > 64:
            raise PairEventV2Error("list_missing_candidate_blocks limit exceeds hard bound 64")
        if after_block_number is None:
            rows = conn.execute(
                f"SELECT DISTINCT b.block_number "
                f"FROM {LOG_CANDIDATE_BLOCK_TABLE} b "
                f"WHERE b.plan_id = ? "
                f"AND NOT EXISTS ("
                f"  SELECT 1 FROM {HEADER_TABLE} h "
                f"  WHERE h.plan_id = b.plan_id AND h.block_number = b.block_number"
                f") "
                f"ORDER BY b.block_number "
                f"LIMIT ?",
                (plan_id, page),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT DISTINCT b.block_number "
                f"FROM {LOG_CANDIDATE_BLOCK_TABLE} b "
                f"WHERE b.plan_id = ? AND b.block_number > ? "
                f"AND NOT EXISTS ("
                f"  SELECT 1 FROM {HEADER_TABLE} h "
                f"  WHERE h.plan_id = b.plan_id AND h.block_number = b.block_number"
                f") "
                f"ORDER BY b.block_number "
                f"LIMIT ?",
                (plan_id, int(after_block_number), page),
            ).fetchall()
        return [
            int(r[0] if not isinstance(r, sqlite3.Row) else r["block_number"])
            for r in rows
        ]

    def _op_list_finalizable_candidates(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
        limit: int = FINALIZE_WORK_PAGE_SIZE,
        after_domain_id: str | None = None,
    ) -> dict[str, Any]:
        """Examine at most ``limit`` PENDING candidates; return ready subset + cursor.

        Bounds database work per call: never scans the full candidate population
        looking for ready rows. Callers advance ``after_domain_id`` across turns.
        """
        del writer
        page = int(limit)
        if page <= 0:
            raise PairEventV2Error("list_finalizable_candidates limit must be positive")
        if page > 64:
            raise PairEventV2Error(
                "list_finalizable_candidates limit exceeds hard bound 64"
            )
        if after_domain_id is None:
            examined = conn.execute(
                f"SELECT c.domain_id FROM {LOG_CANDIDATE_TABLE} c "
                f"JOIN {NODE_TABLE} n "
                f"ON n.plan_id = c.plan_id AND n.domain_id = c.domain_id "
                f"WHERE c.plan_id = ? AND n.status = 'PENDING' "
                f"ORDER BY c.domain_id "
                f"LIMIT ?",
                (plan_id, page),
            ).fetchall()
        else:
            examined = conn.execute(
                f"SELECT c.domain_id FROM {LOG_CANDIDATE_TABLE} c "
                f"JOIN {NODE_TABLE} n "
                f"ON n.plan_id = c.plan_id AND n.domain_id = c.domain_id "
                f"WHERE c.plan_id = ? AND n.status = 'PENDING' "
                f"AND c.domain_id > ? "
                f"ORDER BY c.domain_id "
                f"LIMIT ?",
                (plan_id, str(after_domain_id), page),
            ).fetchall()
        ready: list[str] = []
        last_domain: str | None = None
        for row in examined:
            domain_id = str(row["domain_id"])
            last_domain = domain_id
            incomplete = conn.execute(
                f"SELECT 1 FROM {LOG_CANDIDATE_BLOCK_TABLE} b "
                f"WHERE b.plan_id = ? AND b.domain_id = ? "
                f"AND NOT EXISTS ("
                f"  SELECT 1 FROM {HEADER_TABLE} h "
                f"  WHERE h.plan_id = b.plan_id AND h.block_number = b.block_number"
                f") "
                f"LIMIT 1",
                (plan_id, domain_id),
            ).fetchone()
            if incomplete is None:
                # All required blocks have headers (or candidate has zero blocks —
                # still finalizable only if block table has the boundary row).
                has_blocks = conn.execute(
                    f"SELECT 1 FROM {LOG_CANDIDATE_BLOCK_TABLE} "
                    f"WHERE plan_id = ? AND domain_id = ? LIMIT 1",
                    (plan_id, domain_id),
                ).fetchone()
                if has_blocks is not None:
                    ready.append(domain_id)
        return {
            "ready_domain_ids": ready,
            "scan_through_domain_id": last_domain,
            "exhausted": len(examined) < page,
            "examined": len(examined),
        }

    def _op_authenticate_plan_attach(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
        plan_config: PlanConfig,
        execution_policy: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Verify persisted plan + execution policy before attach mutates lifecycle."""
        del writer
        if _contains_sensitive_key(execution_policy):
            raise PairEventV2Error("execution policy contains sensitive keys")
        if str(execution_policy.get("plan_id", "")) != plan_id:
            raise PairEventV2Error("execution policy plan_id must bind the plan")
        expected_record = plan_record_from_config(plan_config, created_at="")
        if expected_record.plan_id != plan_id:
            raise PairEventV2Error(
                "attach plan_id does not match engine plan_config identity"
            )
        policy_json = _canonical_json(dict(execution_policy))
        policy_id = _identity("pol_", json.loads(policy_json))
        row = conn.execute(
            f"SELECT * FROM {PLAN_TABLE} WHERE plan_id = ?", (plan_id,)
        ).fetchone()
        if row is None:
            raise PairEventV2Error("attach plan is missing")
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
        if replace(actual, created_at="") != replace(expected_record, created_at=""):
            raise PairEventV2Error("persisted plan row is not the requested plan")
        policy_row = conn.execute(
            f"SELECT * FROM {EXECUTION_POLICY_TABLE} WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()
        if policy_row is None:
            raise PairEventV2Error(
                "plan resume missing immutable execution policy record"
            )
        if (
            str(policy_row["identity_payload_json"]) != policy_json
            or str(policy_row["policy_id"]) != policy_id
            or str(policy_row["schema_version"]) != EXECUTION_POLICY_SCHEMA_VERSION
        ):
            raise PairEventV2Error(
                "execution policy mismatch on plan resume — authority settings changed"
            )
        return {
            "plan_id": plan_id,
            "policy_id": policy_id,
            "schema_version": EXECUTION_POLICY_SCHEMA_VERSION,
        }

    def _op_begin_plan_resume_session(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
    ) -> dict[str, Any]:
        """Bump shared plan resume generation (invalidates prior session auth marks)."""
        del writer
        plan_ok = conn.execute(
            f"SELECT 1 FROM {PLAN_TABLE} WHERE plan_id = ?", (plan_id,)
        ).fetchone()
        if plan_ok is None:
            raise PairEventV2Error("resume session plan is missing")
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                f"SELECT active_generation FROM {PLAN_RESUME_SESSION_TABLE} "
                "WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
            if row is None:
                generation = 1
                conn.execute(
                    f"INSERT INTO {PLAN_RESUME_SESSION_TABLE} "
                    "(plan_id, active_generation, updated_at) VALUES (?,?,?)",
                    (plan_id, generation, _now()),
                )
            else:
                generation = int(row["active_generation"]) + 1
                conn.execute(
                    f"UPDATE {PLAN_RESUME_SESSION_TABLE} "
                    "SET active_generation = ?, updated_at = ? WHERE plan_id = ?",
                    (generation, _now(), plan_id),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        self._resume_force_through.pop(plan_id, None)
        return {"plan_id": plan_id, "active_generation": generation}

    def _active_resume_generation(
        self, conn: sqlite3.Connection, plan_id: str
    ) -> int:
        """Read active generation; safe inside or outside an open transaction."""
        row = conn.execute(
            f"SELECT active_generation FROM {PLAN_RESUME_SESSION_TABLE} "
            "WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()
        if row is not None:
            return int(row["active_generation"])
        # Insert generation 1 without nested BEGIN (caller may hold a TX).
        plan_ok = conn.execute(
            f"SELECT 1 FROM {PLAN_TABLE} WHERE plan_id = ?", (plan_id,)
        ).fetchone()
        if plan_ok is None:
            raise PairEventV2Error("resume session plan is missing")
        conn.execute(
            f"INSERT OR IGNORE INTO {PLAN_RESUME_SESSION_TABLE} "
            "(plan_id, active_generation, updated_at) VALUES (?,?,?)",
            (plan_id, 1, _now()),
        )
        row = conn.execute(
            f"SELECT active_generation FROM {PLAN_RESUME_SESSION_TABLE} "
            "WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()
        if row is None:
            raise PairEventV2Error("resume session could not be initialized")
        return int(row["active_generation"])

    def _op_authenticate_resumed_candidates(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
        force: bool = False,
        limit: int = CLAIM_SCAN_PAGE_SIZE,
    ) -> dict[str, Any]:
        """One bounded page of resume re-validation for the active generation.

        Normal mode selects only candidates not yet marked for the active
        generation (race-safe for inserts behind any prior cursor). ``force=True``
        revalidates the next page of all candidates (still one page per call).

        Generation-atomic: a concurrent attach that bumps the active generation
        mid-page aborts stamping for the captured generation, returns
        ``generation_restart=True``, and never advertises ``complete=True`` for a
        generation that is no longer active.
        """
        del writer
        page = int(limit)
        if page <= 0:
            raise PairEventV2Error("authenticate_resumed_candidates limit must be positive")
        if page > 64:
            raise PairEventV2Error(
                "authenticate_resumed_candidates limit exceeds hard bound 64"
            )
        generation = self._active_resume_generation(conn, plan_id)

        def _restart_result(
            *,
            authenticated: int,
            through: str | None,
            examined: int,
            live_generation: int,
        ) -> dict[str, Any]:
            return {
                "authenticated": authenticated,
                "complete": False,
                "through_domain_id": through,
                "examined": examined,
                "active_generation": live_generation,
                "generation_restart": True,
            }

        def _drop_bad_candidate(domain_id: str) -> None:
            conn.execute("BEGIN IMMEDIATE")
            try:
                block_rows = conn.execute(
                    f"SELECT block_number FROM {LOG_CANDIDATE_BLOCK_TABLE} "
                    "WHERE plan_id = ? AND domain_id = ?",
                    (plan_id, domain_id),
                ).fetchall()
                conn.execute(
                    f"DELETE FROM {LOG_CANDIDATE_TABLE} "
                    "WHERE plan_id = ? AND domain_id = ?",
                    (plan_id, domain_id),
                )
                for brow in block_rows:
                    bn = int(brow["block_number"])
                    still = conn.execute(
                        f"SELECT 1 FROM {LOG_CANDIDATE_BLOCK_TABLE} "
                        "WHERE plan_id = ? AND block_number = ? LIMIT 1",
                        (plan_id, bn),
                    ).fetchone()
                    if still is None:
                        self._backlog_remove_block(conn, plan_id, bn)
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        if force:
            after = self._resume_force_through.get(plan_id)
            if after is None:
                rows = conn.execute(
                    f"SELECT domain_id FROM {LOG_CANDIDATE_TABLE} "
                    "WHERE plan_id = ? ORDER BY domain_id LIMIT ?",
                    (plan_id, page),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT domain_id FROM {LOG_CANDIDATE_TABLE} "
                    "WHERE plan_id = ? AND domain_id > ? "
                    "ORDER BY domain_id LIMIT ?",
                    (plan_id, after, page),
                ).fetchall()
        else:
            # Unauthenticated for active generation only — includes inserts that
            # sort behind a prior watermark (generation mark still NULL/stale).
            rows = conn.execute(
                f"SELECT domain_id FROM {LOG_CANDIDATE_TABLE} "
                "WHERE plan_id = ? "
                "AND (session_auth_generation IS NULL "
                "     OR session_auth_generation != ?) "
                "ORDER BY domain_id LIMIT ?",
                (plan_id, generation, page),
            ).fetchall()

        authenticated = 0
        through: str | None = None
        examined = 0
        for row in rows:
            domain_id = str(row["domain_id"])
            through = domain_id
            examined += 1
            try:
                self._authenticate_candidate_row(
                    conn, plan_id=plan_id, domain_id=domain_id
                )
            except PairEventV2Error:
                live_before_drop = self._active_resume_generation(conn, plan_id)
                if live_before_drop != generation:
                    return _restart_result(
                        authenticated=authenticated,
                        through=through,
                        examined=examined,
                        live_generation=live_before_drop,
                    )
                _drop_bad_candidate(domain_id)
                if force:
                    self._resume_force_through[plan_id] = through
                    raise
                continue
            conn.execute("BEGIN IMMEDIATE")
            try:
                live_gen = self._active_resume_generation(conn, plan_id)
                if live_gen != generation:
                    conn.execute("COMMIT")
                    return _restart_result(
                        authenticated=authenticated,
                        through=through,
                        examined=examined,
                        live_generation=live_gen,
                    )
                # Re-check row still present; stamp only the still-active generation.
                still = conn.execute(
                    f"SELECT 1 FROM {LOG_CANDIDATE_TABLE} "
                    "WHERE plan_id = ? AND domain_id = ?",
                    (plan_id, domain_id),
                ).fetchone()
                if still is not None:
                    conn.execute(
                        f"UPDATE {LOG_CANDIDATE_TABLE} "
                        "SET session_auth_generation = ? "
                        "WHERE plan_id = ? AND domain_id = ?",
                        (live_gen, plan_id, domain_id),
                    )
                    authenticated += 1
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        live_gen = self._active_resume_generation(conn, plan_id)
        if live_gen != generation:
            return _restart_result(
                authenticated=authenticated,
                through=through,
                examined=examined,
                live_generation=live_gen,
            )

        exhausted = len(rows) < page
        if force:
            self._resume_force_through[plan_id] = None if exhausted else through
        complete = exhausted
        if complete and not force:
            # Confirm no unauth remain (race-safe LIMIT 1 probe, not full scan).
            more = conn.execute(
                f"SELECT 1 FROM {LOG_CANDIDATE_TABLE} "
                "WHERE plan_id = ? "
                "AND (session_auth_generation IS NULL OR session_auth_generation != ?) "
                "LIMIT 1",
                (plan_id, generation),
            ).fetchone()
            complete = more is None
            live_gen = self._active_resume_generation(conn, plan_id)
            if live_gen != generation:
                return _restart_result(
                    authenticated=authenticated,
                    through=through,
                    examined=examined,
                    live_generation=live_gen,
                )
        return {
            "authenticated": authenticated,
            "complete": complete,
            "through_domain_id": through,
            "examined": examined,
            "active_generation": generation,
            "generation_restart": False,
        }

    def _backlog_add_block(
        self, conn: sqlite3.Connection, plan_id: str, block_number: int
    ) -> None:
        """Add one missing block to durable backlog inside caller's TX."""
        bn = int(block_number)
        present = conn.execute(
            f"SELECT 1 FROM {HEADER_TABLE} "
            "WHERE plan_id = ? AND block_number = ? LIMIT 1",
            (plan_id, bn),
        ).fetchone()
        if present is not None:
            return
        conn.execute(
            f"INSERT OR IGNORE INTO {HEADER_BACKLOG_TABLE} "
            "(plan_id, block_number) VALUES (?,?)",
            (plan_id, bn),
        )
        if conn.execute("SELECT changes()").fetchone()[0] != 1:
            return
        conn.execute(
            f"INSERT INTO {HEADER_BACKLOG_METRIC_TABLE} (plan_id, missing_count) "
            "VALUES (?, 1) "
            "ON CONFLICT(plan_id) DO UPDATE SET "
            "missing_count = missing_count + 1",
            (plan_id,),
        )

    def _backlog_remove_block(
        self, conn: sqlite3.Connection, plan_id: str, block_number: int
    ) -> None:
        """Remove one block from durable backlog inside caller's TX."""
        bn = int(block_number)
        conn.execute(
            f"DELETE FROM {HEADER_BACKLOG_TABLE} "
            "WHERE plan_id = ? AND block_number = ?",
            (plan_id, bn),
        )
        if conn.execute("SELECT changes()").fetchone()[0] != 1:
            return
        conn.execute(
            f"UPDATE {HEADER_BACKLOG_METRIC_TABLE} "
            "SET missing_count = missing_count - 1 "
            "WHERE plan_id = ? AND missing_count > 0",
            (plan_id,),
        )

    def _note_missing_blocks(
        self,
        conn: sqlite3.Connection,
        plan_id: str,
        blocks: Sequence[tuple[int, str | None, bool]],
    ) -> None:
        """Transactionally record missing required blocks (caller's open TX)."""
        for block_number, _hash, _boundary in blocks:
            self._backlog_add_block(conn, plan_id, int(block_number))

    def _note_header_stored(
        self, conn: sqlite3.Connection, plan_id: str, block_number: int
    ) -> None:
        """Transactionally clear a block from backlog (must run inside store TX)."""
        self._backlog_remove_block(conn, plan_id, int(block_number))

    def _op_header_backlog_count(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
    ) -> int:
        """Exact multi-process backlog from durable metric row (O(1) read).

        No full-population bootstrap. Plan init inserts missing_count=0; commit
        and header store maintain the counter transactionally. Missing metric
        fails closed with a bounded zero-row insert only when the plan row exists
        and no backlog/candidate-block state is present.
        """
        del writer
        row = conn.execute(
            f"SELECT missing_count FROM {HEADER_BACKLOG_METRIC_TABLE} "
            "WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()
        if row is not None:
            return int(row["missing_count"])
        # Coherent zero init only — never SELECT DISTINCT over candidate blocks.
        plan_ok = conn.execute(
            f"SELECT 1 FROM {PLAN_TABLE} WHERE plan_id = ?", (plan_id,)
        ).fetchone()
        if plan_ok is None:
            raise PairEventV2Error("header backlog plan is missing")
        any_block = conn.execute(
            f"SELECT 1 FROM {LOG_CANDIDATE_BLOCK_TABLE} WHERE plan_id = ? LIMIT 1",
            (plan_id,),
        ).fetchone()
        any_backlog = conn.execute(
            f"SELECT 1 FROM {HEADER_BACKLOG_TABLE} WHERE plan_id = ? LIMIT 1",
            (plan_id,),
        ).fetchone()
        if any_block is not None or any_backlog is not None:
            raise PairEventV2Error(
                "header backlog metric missing while candidate/backlog state exists; "
                "refusing unbounded rebuild"
            )
        conn.execute("BEGIN IMMEDIATE")
        try:
            again = conn.execute(
                f"SELECT missing_count FROM {HEADER_BACKLOG_METRIC_TABLE} "
                "WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
            if again is not None:
                conn.execute("COMMIT")
                return int(again["missing_count"])
            conn.execute(
                f"INSERT INTO {HEADER_BACKLOG_METRIC_TABLE} "
                "(plan_id, missing_count) VALUES (?, 0)",
                (plan_id,),
            )
            conn.execute("COMMIT")
            return 0
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def _op_reauthenticate_root_domain_set(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
    ) -> dict[str, Any]:
        """Public semantic root re-auth (field recompute + ordered domain-set digest)."""
        del writer
        count, digest = self._stream_root_domain_digest(conn, plan_id)
        return {"root_count": count, "root_domain_set_sha256": digest}

    def _op_claim_pending(
        self,
        conn: sqlite3.Connection,
        writer: RawObjectWriter,
        *,
        plan_id: str,
        worker_id: str,
        lease_ttl_seconds: float,
    ) -> Claim | None:
        # Advance at most one resume-auth page OUTSIDE the write transaction.
        # No population COUNT; complete plans skip auth entirely.
        # Resume-auth is outside the write TX (no ROLLBACK coupling).
        # Advance one resume-validation page (never deletes valid candidates).
        self._op_authenticate_resumed_candidates(
            conn,
            writer,
            plan_id=plan_id,
            force=False,
            limit=CLAIM_SCAN_PAGE_SIZE,
        )
        generation = self._active_resume_generation(conn, plan_id)
        in_tx = False
        try:
            conn.execute("BEGIN IMMEDIATE")
            in_tx = True
            self._expire_leases(conn, plan_id)
            claim_order = self._claim_order_version(conn, plan_id)
            # Production domain_hash_v1 uses covering index (plan_id, status, domain_id).
            if claim_order == CLAIM_ORDER_VERSION_DOMAIN_HASH_V1:
                order_sql = "ORDER BY n.domain_id"
            else:
                order_sql = "ORDER BY n.start_block, n.domain_id"
            # Exclusion authority: only candidates stamped with the active
            # generation. Unvalidated candidates defer claim (do not suppress via
            # bare existence, do not get deleted for reclaim). Valid candidates
            # after session re-auth exclude reacquisition.
            row = conn.execute(
                f"SELECT n.* FROM {NODE_TABLE} n "
                f"WHERE n.plan_id = ? AND n.status = 'PENDING' "
                f"AND n.attempt < ? "
                f"AND NOT EXISTS ("
                f"  SELECT 1 FROM {LOG_CANDIDATE_TABLE} c "
                f"  WHERE c.plan_id = n.plan_id AND c.domain_id = n.domain_id "
                f"  AND c.session_auth_generation = ?"
                f") "
                f"AND NOT EXISTS ("
                f"  SELECT 1 FROM {LOG_CANDIDATE_TABLE} c "
                f"  WHERE c.plan_id = n.plan_id AND c.domain_id = n.domain_id "
                f"  AND (c.session_auth_generation IS NULL "
                f"       OR c.session_auth_generation != ?)"
                f") "
                f"{order_sql} "
                f"LIMIT 1",
                (plan_id, self._max_attempts, generation, generation),
            ).fetchone()
            if row is None:
                conn.execute("COMMIT")
                in_tx = False
                return None
            domain_id = str(row["domain_id"])
            now = datetime.now(UTC)
            token = uuid.uuid4().hex
            conn.execute(
                f"UPDATE {NODE_TABLE} SET status = 'IN_FLIGHT', updated_at = ? "
                "WHERE plan_id = ? AND domain_id = ? AND status = 'PENDING' "
                "AND attempt < ?",
                (now.isoformat(), plan_id, domain_id, self._max_attempts),
            )
            if conn.execute("SELECT changes()").fetchone()[0] != 1:
                conn.execute("COMMIT")
                in_tx = False
                return None
            conn.execute(
                f"INSERT INTO {LEASE_TABLE} (plan_id, domain_id, worker_id, "
                "lease_token, leased_at, expires_at) VALUES (?,?,?,?,?,?)",
                (
                    plan_id,
                    domain_id,
                    worker_id,
                    token,
                    now.isoformat(),
                    (now + timedelta(seconds=lease_ttl_seconds)).isoformat(),
                ),
            )
            conn.execute("COMMIT")
            in_tx = False
            node = self._node_from_row(row, status="IN_FLIGHT")
            return Claim(
                plan_id=plan_id,
                domain_id=domain_id,
                worker_id=worker_id,
                lease_token=token,
                attempt=int(row["attempt"]),
                node=node,
            )
        except Exception:
            if in_tx:
                conn.execute("ROLLBACK")
            raise

    def _authenticate_candidate_row(
        self,
        conn: sqlite3.Connection,
        *,
        plan_id: str,
        domain_id: str,
    ) -> None:
        """Fail closed if a stored candidate does not fully re-authenticate."""
        cand = conn.execute(
            f"SELECT * FROM {LOG_CANDIDATE_TABLE} "
            "WHERE plan_id = ? AND domain_id = ?",
            (plan_id, domain_id),
        ).fetchone()
        if cand is None:
            raise PairEventV2Error("candidate missing during authentication")
        node_row = conn.execute(
            f"SELECT * FROM {NODE_TABLE} WHERE plan_id = ? AND domain_id = ?",
            (plan_id, domain_id),
        ).fetchone()
        if node_row is None:
            raise PairEventV2Error("candidate node missing during authentication")
        domain = QueryDomain(
            start_block=int(node_row["start_block"]),
            end_block=int(node_row["end_block"]),
            addresses=tuple(json.loads(str(node_row["addresses_json"]))),
            topics=tuple(json.loads(str(node_row["topics_json"]))),
        )
        if domain.domain_id(plan_id) != domain_id:
            raise PairEventV2Error("candidate domain_id mismatch during auth")
        try:
            request = json.loads(str(cand["request_json"]))
        except json.JSONDecodeError as exc:
            raise PairEventV2Error("candidate request_json is not JSON") from exc
        if not isinstance(request, Mapping):
            raise PairEventV2Error("candidate request_json must be an object")
        if _canonical_json(dict(request)) != _canonical_json(
            request_for_domain(domain)
        ):
            raise PairEventV2Error("candidate request does not match domain")
        p_ev = self._authenticate_evidence(
            conn,
            acquisition_id=str(cand["primary_logs_acquisition_id"]),
            raw_object_id=str(cand["primary_logs_raw_object_id"]),
            provider_org=str(cand["primary_provider_org"]),
            request=request,
            require_request_match=True,
            require_successful_body=True,
        )
        s_ev = self._authenticate_evidence(
            conn,
            acquisition_id=str(cand["secondary_logs_acquisition_id"]),
            raw_object_id=str(cand["secondary_logs_raw_object_id"]),
            provider_org=str(cand["secondary_provider_org"]),
            request=request,
            require_request_match=True,
            require_successful_body=True,
        )
        p_payload = _load_authenticated_rpc(
            p_ev, request, max_bytes=self._max_body_bytes, raw_root=self._raw_root
        )
        s_payload = _load_authenticated_rpc(
            s_ev, request, max_bytes=self._max_body_bytes, raw_root=self._raw_root
        )
        p_logs = p_payload.get("result")
        s_logs = s_payload.get("result")
        if not isinstance(p_logs, list) or not isinstance(s_logs, list):
            raise PairEventV2Error("candidate log bodies missing result lists")
        identities, digest = reconcile_log_sets_v2(p_logs, s_logs, domain)
        if digest != str(cand["log_identity_sha256"]):
            raise PairEventV2Error("candidate log digest authentication failed")
        if len(identities) != int(cand["log_count"]):
            raise PairEventV2Error("candidate log_count authentication failed")
        recomputed = compute_log_candidate_id(
            plan_id=plan_id,
            domain_id=domain_id,
            attempt=int(cand["attempt"]),
            log_identity_sha256=digest,
            primary_logs_raw_object_id=str(cand["primary_logs_raw_object_id"]),
            secondary_logs_raw_object_id=str(cand["secondary_logs_raw_object_id"]),
            primary_logs_acquisition_id=str(cand["primary_logs_acquisition_id"]),
            secondary_logs_acquisition_id=str(cand["secondary_logs_acquisition_id"]),
        )
        if recomputed != str(cand["candidate_id"]):
            raise PairEventV2Error("candidate_id authentication failed")
        expected_blocks = required_blocks_from_identities(identities, domain=domain)
        stored_blocks = conn.execute(
            f"SELECT block_number, expected_block_hash, is_boundary "
            f"FROM {LOG_CANDIDATE_BLOCK_TABLE} "
            "WHERE plan_id = ? AND domain_id = ? ORDER BY block_number",
            (plan_id, domain_id),
        ).fetchall()
        stored_norm = tuple(
            (
                int(b["block_number"]),
                None
                if b["expected_block_hash"] is None
                else str(b["expected_block_hash"]),
                bool(int(b["is_boundary"])),
            )
            for b in stored_blocks
        )
        if stored_norm != expected_blocks:
            raise PairEventV2Error("candidate required-block authentication failed")

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
        """Fully authenticate a canonical header backed by scalar or batch raw pairs.

        Authority accepts either a single-block JSON-RPC object or a batch array
        raw pair that contains the recorded block. Both providers must re-open,
        re-hash, and re-derive the same number/hash/timestamp as the receipt.
        """
        del writer  # control pulses happen inside evidence open helpers if needed
        primary = self._authenticate_evidence(
            conn,
            raw_object_id=record.primary_raw_object_id,
            acquisition_id=record.primary_acquisition_id,
            provider_org=record.primary_provider_org,
            request=None,
            require_request_match=False,
            require_successful_body=True,
        )
        secondary = self._authenticate_evidence(
            conn,
            raw_object_id=record.secondary_raw_object_id,
            acquisition_id=record.secondary_acquisition_id,
            provider_org=record.secondary_provider_org,
            request=None,
            require_request_match=False,
            require_successful_body=True,
        )
        # Stored request must be a scalar eth_getBlockByNumber for this block, or
        # a batch that includes it; reject unrelated acquisitions.
        for evidence in (primary, secondary):
            self._assert_header_evidence_covers_block(
                evidence, block_number=record.block_number
            )
        p_hdr = self._header_result_from_evidence(
            primary, block_number=record.block_number
        )
        s_hdr = self._header_result_from_evidence(
            secondary, block_number=record.block_number
        )
        expected = {
            "number": record.block_number,
            "hash": record.block_hash,
            "timestamp": record.block_timestamp,
        }
        if p_hdr != expected or s_hdr != expected:
            raise PairEventV2Error("canonical header raw replay disagrees with receipt")
        recomputed = compute_canonical_header_receipt_id(
            plan_id=record.plan_id,
            block_number=record.block_number,
            block_hash=record.block_hash,
            block_timestamp=record.block_timestamp,
            primary_provider_org=record.primary_provider_org,
            secondary_provider_org=record.secondary_provider_org,
            primary_raw_object_id=primary.raw_object_id,
            secondary_raw_object_id=secondary.raw_object_id,
            primary_acquisition_id=primary.acquisition_id,
            secondary_acquisition_id=secondary.acquisition_id,
        )
        if recomputed != record.header_receipt_id:
            raise PairEventV2Error(
                "canonical header receipt identity failed recomputation on replay"
            )
        return record, primary, secondary

    def _assert_header_evidence_covers_block(
        self, evidence: AuthenticatedEvidence, *, block_number: int
    ) -> None:
        """Fail closed if stored request is neither scalar nor batch for block."""
        try:
            stored = json.loads(evidence.request_json)
        except json.JSONDecodeError as exc:
            raise PairEventV2Error("header evidence request is not JSON") from exc
        if isinstance(stored, Mapping):
            if stored.get("method") != "eth_getBlockByNumber":
                raise PairEventV2Error(
                    "scalar header evidence method is not eth_getBlockByNumber"
                )
            params = stored.get("params")
            if (
                not isinstance(params, list)
                or not params
                or not isinstance(params[0], str)
            ):
                raise PairEventV2Error("scalar header evidence params malformed")
            try:
                req_block = int(params[0], 16)
            except ValueError as exc:
                raise PairEventV2Error(
                    "scalar header evidence block param is not hex"
                ) from exc
            if req_block != block_number:
                raise PairEventV2Error(
                    f"scalar header evidence is for block {req_block}, "
                    f"not {block_number}"
                )
            return
        if isinstance(stored, list):
            for item in stored:
                if not isinstance(item, Mapping):
                    continue
                if item.get("method") != "eth_getBlockByNumber":
                    continue
                params = item.get("params")
                if (
                    isinstance(params, list)
                    and params
                    and isinstance(params[0], str)
                ):
                    try:
                        if int(params[0], 16) == block_number:
                            return
                    except ValueError:
                        continue
            raise PairEventV2Error(
                f"batch header evidence does not cover block {block_number}"
            )
        raise PairEventV2Error(
            "header evidence request is neither scalar object nor batch array"
        )

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
                # Existing winner still covers the block for backlog purposes.
                self._note_header_stored(conn, record.plan_id, record.block_number)
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
                self._note_header_stored(conn, record.plan_id, record.block_number)
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
        self._credential_scanner = CredentialScanner.from_rpc_urls(
            config.primary_rpc_url, config.secondary_rpc_url
        )
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
            credential_scanner=self._credential_scanner,
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
            credential_scanner=self._credential_scanner,
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
        snapshot.in_flight_high_water_primary = max(
            snapshot.in_flight_high_water_primary, self._primary_limiter.high_water
        )
        snapshot.in_flight_high_water_secondary = max(
            snapshot.in_flight_high_water_secondary, self._secondary_limiter.high_water
        )
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
        self._require_production_ready_if_applicable()

    def execution_policy_identity(
        self,
        plan_id: str,
        *,
        claim_order_version: str = CLAIM_ORDER_VERSION_CHRONOLOGICAL_V1,
    ) -> dict[str, Any]:
        """Immutable authority-affecting settings (no URLs, keys, or worker IDs).

        ``plan_id`` is part of the identity so identical settings cannot collide
        across distinct plans. Production uses ``domain_hash_v1`` claim order.
        """
        if claim_order_version not in {
            CLAIM_ORDER_VERSION_CHRONOLOGICAL_V1,
            CLAIM_ORDER_VERSION_DOMAIN_HASH_V1,
        }:
            raise PairEventV2Error(f"unknown claim_order_version: {claim_order_version}")
        cfg = self.config
        return {
            "backoff_base_seconds": cfg.backoff_base_seconds,
            "backoff_max_seconds": cfg.backoff_max_seconds,
            "claim_order_version": claim_order_version,
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

    def initialize(
        self,
        pools: Sequence[RegistryPoolBirth],
        *,
        claim_order_version: str = CLAIM_ORDER_VERSION_CHRONOLOGICAL_V1,
    ) -> AcquisitionPlanV2:
        """Insert plan + roots + execution policy. Does not claim work.

        ``claim_order_version`` selects chronological vs production domain_hash_v1
        logs-first policy via the public execution-policy identity (no internal
        monkeypatch required).
        """
        plan = build_acquisition_plan_v2(pools, self.config.plan_config)
        self.coordinator.initialize_plan(
            plan,
            execution_policy=self.execution_policy_identity(
                plan.plan_id, claim_order_version=claim_order_version
            ),
        )
        self._plan_id = plan.plan_id
        self._phase = EnginePhase.PLAN_INITIALIZED
        return plan

    def initialize_production(
        self,
        pools: Sequence[RegistryPoolBirth],
        *,
        registry_parquet_sha256: str,
        registry_parquet_bytes: int,
        batch_size: int = 512,
    ) -> dict[str, Any]:
        """Bounded-memory production plan init to READY (no network).

        Rejects caller-substituted cohort/config/anchors. Streams roots in batches.
        """
        if batch_size <= 0:
            raise PairEventV2Error("batch_size must be positive")
        if registry_parquet_sha256 != PRODUCTION_REGISTRY_PARQUET_SHA256:
            raise PairEventV2Error("caller registry_parquet_sha256 is not accepted")
        if int(registry_parquet_bytes) != PRODUCTION_REGISTRY_PARQUET_BYTES:
            raise PairEventV2Error("caller registry_parquet_bytes is not accepted")
        cfg = production_plan_config()
        if self.config.plan_config.initial_cohort_size != PRODUCTION_INITIAL_COHORT_SIZE:
            raise PairEventV2Error(
                "production initializer requires plan_config cohort size 8"
            )
        if self.config.plan_config.plan_id() != PRODUCTION_PLAN_ID:
            raise PairEventV2Error(
                "production initializer requires pinned production plan identity"
            )
        cfg = self.config.plan_config
        ordered = tuple(pools)
        anchors = compute_production_root_anchors(ordered, config=cfg)
        verify_production_root_anchors(anchors)
        policy = self.execution_policy_identity(
            cfg.plan_id(),
            claim_order_version=CLAIM_ORDER_VERSION_DOMAIN_HASH_V1,
        )
        self.coordinator.ensure_production_plan_shell(
            config=cfg, execution_policy=policy
        )
        # Do NOT mark PLAN_INITIALIZED until READY — network must not start early.
        self._plan_id = None
        self._phase = EnginePhase.CONSTRUCTED
        existing = self.coordinator.load_root_manifest(plan_id=cfg.plan_id())
        if existing is not None and existing.status == "READY":
            self.coordinator.authenticate_ready_root_manifest(
                plan_id=cfg.plan_id(),
                registry_parquet_sha256=registry_parquet_sha256,
                registry_parquet_bytes=registry_parquet_bytes,
            )
            self._plan_id = cfg.plan_id()
            self._phase = EnginePhase.PLAN_INITIALIZED
            return {
                "plan_id": cfg.plan_id(),
                "status": "READY",
                "inserted": 0,
                "root_count": existing.root_count,
                "anchors": anchors,
            }
        batch: list[RootFilterPlan] = []
        total_inserted = 0
        for root in iter_production_root_filters(
            ordered, config=cfg, batch_size=batch_size
        ):
            batch.append(root)
            if len(batch) >= batch_size:
                result = self.coordinator.initialize_production_roots_batch(
                    plan_id=cfg.plan_id(),
                    roots=batch,
                    registry_parquet_sha256=registry_parquet_sha256,
                    registry_parquet_bytes=registry_parquet_bytes,
                    expected_root_count=PRODUCTION_ROOT_COUNT,
                    expected_root_domain_set_sha256=PRODUCTION_ROOT_DOMAIN_SET_SHA256,
                    expected_pool_topic_blocks=PRODUCTION_POOL_TOPIC_BLOCKS,
                    finalize=False,
                )
                total_inserted += int(result["inserted"])
                batch.clear()
        if batch:
            result = self.coordinator.initialize_production_roots_batch(
                plan_id=cfg.plan_id(),
                roots=batch,
                registry_parquet_sha256=registry_parquet_sha256,
                registry_parquet_bytes=registry_parquet_bytes,
                expected_root_count=PRODUCTION_ROOT_COUNT,
                expected_root_domain_set_sha256=PRODUCTION_ROOT_DOMAIN_SET_SHA256,
                expected_pool_topic_blocks=PRODUCTION_POOL_TOPIC_BLOCKS,
                finalize=False,
            )
            total_inserted += int(result["inserted"])
        final = self.coordinator.initialize_production_roots_batch(
            plan_id=cfg.plan_id(),
            roots=(),
            registry_parquet_sha256=registry_parquet_sha256,
            registry_parquet_bytes=registry_parquet_bytes,
            expected_root_count=PRODUCTION_ROOT_COUNT,
            expected_root_domain_set_sha256=PRODUCTION_ROOT_DOMAIN_SET_SHA256,
            expected_pool_topic_blocks=PRODUCTION_POOL_TOPIC_BLOCKS,
            finalize=True,
        )
        if final.get("status") != "READY":
            raise PairEventV2Error("production root manifest did not become READY")
        self.coordinator.authenticate_ready_root_manifest(
            plan_id=cfg.plan_id(),
            registry_parquet_sha256=registry_parquet_sha256,
            registry_parquet_bytes=registry_parquet_bytes,
        )
        self._plan_id = cfg.plan_id()
        self._phase = EnginePhase.PLAN_INITIALIZED
        return {
            "plan_id": cfg.plan_id(),
            "status": "READY",
            "inserted": total_inserted,
            "root_count": final["root_count"],
            "anchors": anchors,
        }

    def _require_production_ready_if_applicable(self) -> None:
        """Fail closed if this is the production plan without READY manifest."""
        if self._plan_id is None:
            return
        if self._plan_id != PRODUCTION_PLAN_ID:
            return
        manifest = self.coordinator.load_root_manifest(plan_id=self._plan_id)
        if manifest is None or manifest.status != "READY":
            raise PairEventV2Error(
                "production network work requires READY root manifest"
            )
        self.coordinator.authenticate_ready_root_manifest(
            plan_id=self._plan_id,
            registry_parquet_sha256=PRODUCTION_REGISTRY_PARQUET_SHA256,
            registry_parquet_bytes=PRODUCTION_REGISTRY_PARQUET_BYTES,
        )

    def authenticate_chain(self) -> ChainIdentityReceipt:
        """Prerequisite: dual mainnet chain identity for the plan (cached once).

        Production plans must have READY root manifest before any network work.
        """
        if self._phase == EnginePhase.CONSTRUCTED or self._plan_id is None:
            raise PairEventV2Error("initialize() is required before chain authentication")
        self._require_production_ready_if_applicable()
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
        self, request: Mapping[str, Any] | Sequence[Any]
    ) -> tuple[PersistedEnvelope, PersistedEnvelope]:
        t0 = time.monotonic()
        primary_future = self._network_executor.submit(
            self._primary_worker.fetch, request
        )
        secondary_future = self._network_executor.submit(
            self._secondary_worker.fetch, request
        )
        with self._metrics_lock:
            self._metrics.provider_attempts_primary += 1
            self._metrics.provider_attempts_secondary += 1
            self._metrics.provider_attempts_total += 2
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
        # Sample limiter high-water after workers have acquired/released.
        with self._metrics_lock:
            self._metrics.in_flight_high_water_primary = max(
                self._metrics.in_flight_high_water_primary,
                self._primary_limiter.high_water,
            )
            self._metrics.in_flight_high_water_secondary = max(
                self._metrics.in_flight_high_water_secondary,
                self._secondary_limiter.high_water,
            )
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        self._add_metrics(provider_latency_ms_total=elapsed_ms)
        for descriptor in descriptors:
            if descriptor.error_kind == "credential_detection":
                self._add_metrics(credential_detections=1)
            self._add_metrics(
                response_bytes=descriptor.response_bytes,
                retained_spool_bytes=descriptor.retained_bytes,
                truncated_responses=int(descriptor.truncated),
            )
            if descriptor.spool_path is not None:
                with self._metrics_lock:
                    # Approximate spool high-water from live directory size when possible.
                    try:
                        n_spool = sum(
                            1 for _ in self.config.spool_dir.glob("*.spool")
                        )
                    except OSError:
                        n_spool = 0
                    self._metrics.spool_files_high_water = max(
                        self._metrics.spool_files_high_water, n_spool
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

        primary_evidence = pair[0].evidence
        secondary_evidence = pair[1].evidence
        if primary_evidence is None or secondary_evidence is None:
            raise _PairFailure(
                [_FailureFact(FailureClass.PERSISTENCE, None, {"stage": "logs"})]
            )

        # Production path (domain_hash_v1): logs-first candidate, headers later.
        # Generic chronological path keeps inline headers for backward compatibility.
        use_logs_first = self._production_logs_first_enabled()
        if use_logs_first:
            try:
                blocks = required_blocks_from_identities(identities, domain=domain)
            except PairEventV2Error:
                return self._route_failure(
                    claim,
                    _PairFailure(
                        [
                            _FailureFact(
                                FailureClass.MALFORMED_JSON,
                                None,
                                {
                                    "stage": "required_blocks",
                                    **self._pair_evidence_ids(pair),
                                },
                            )
                        ]
                    ),
                    request,
                    allow_split=False,
                )
            candidate_kwargs = {
                "log_identity_sha256": digest,
                "log_count": len(identities),
                "primary_provider_org": self.config.primary_org,
                "secondary_provider_org": self.config.secondary_org,
                "primary_logs_raw_object_id": primary_evidence.raw_object_id,
                "secondary_logs_raw_object_id": secondary_evidence.raw_object_id,
                "primary_logs_acquisition_id": primary_evidence.acquisition_id,
                "secondary_logs_acquisition_id": secondary_evidence.acquisition_id,
                "request_json": _canonical_json(request),
            }
            if self._lease_lost(claim):
                return self.coordinator.resolve_winner(claim)
            try:
                self.coordinator.commit_log_candidate(
                    claim, candidate_kwargs=candidate_kwargs, blocks=blocks
                )
            except _LeaseLostError:
                return self.coordinator.resolve_winner(claim)
            self._primary_limiter.on_success()
            self._secondary_limiter.on_success()
            self._add_metrics(candidates_committed=1)
            return "candidate"

        # --- generic chronological path: dual logs + per-node headers → AGREED ---
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

    def _production_logs_first_enabled(self) -> bool:
        """True when authenticated execution policy selects production claim order."""
        if self._plan_id is None:
            return False
        try:
            order = self.coordinator.claim_order_version(plan_id=self._plan_id)
        except Exception:
            return False
        return order == CLAIM_ORDER_VERSION_DOMAIN_HASH_V1

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

    def _verify_header_evidence_any(
        self,
        record: CanonicalHeaderReceiptRecord,
        primary_evidence: AuthenticatedEvidence,
        secondary_evidence: AuthenticatedEvidence,
        *,
        block_number: int,
    ) -> None:
        """Replay scalar or batch-backed header evidence for one block."""
        try:
            stored = json.loads(primary_evidence.request_json)
        except json.JSONDecodeError as exc:
            raise PairEventV2Error("header evidence request is not JSON") from exc
        if isinstance(stored, list):
            p_hdr = _extract_header_result_from_evidence(
                primary_evidence,
                block_number=block_number,
                max_bytes=self.config.max_body_bytes,
                raw_root=self.config.raw_root,
            )
            s_hdr = _extract_header_result_from_evidence(
                secondary_evidence,
                block_number=block_number,
                max_bytes=self.config.max_body_bytes,
                raw_root=self.config.raw_root,
            )
            if (
                p_hdr["hash"] != s_hdr["hash"]
                or p_hdr["timestamp"] != s_hdr["timestamp"]
                or p_hdr["number"] != block_number
                or s_hdr["number"] != block_number
            ):
                raise PairEventV2Error(
                    f"batch header replay disagreement at block {block_number}"
                )
            if record.block_hash != p_hdr["hash"]:
                raise PairEventV2Error(
                    f"stored header hash drift at block {block_number}"
                )
            return
        self._verify_cached_header(
            record, primary_evidence, secondary_evidence, block_number
        )

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

    def attach_existing_plan(
        self,
        plan_id: str,
        *,
        claim_order_version: str = CLAIM_ORDER_VERSION_CHRONOLOGICAL_V1,
    ) -> dict[str, Any]:
        """Public resume lifecycle: bind to an existing plan and start a resume generation.

        Authenticates the persisted plan row against ``config.plan_config`` and the
        immutable execution-policy identity (payload, policy_id, schema, claim order)
        against this engine's authority settings **before** any generation bump or
        lifecycle assignment. Expected claim order is independent of the stored
        policy record (caller/default); the pinned production plan always uses
        ``domain_hash_v1``. Requires durable chain identity. Bumps shared
        ``active_generation`` so prior session auth marks are invalid and all
        pre-existing candidates must be re-replayed in bounded pages.
        """
        if not plan_id or not str(plan_id).startswith("plan_"):
            raise PairEventV2Error("attach_existing_plan requires a plan_ id")
        # Independent expected claim order — never read from the record under test.
        expected_claim_order = str(claim_order_version)
        if expected_claim_order not in {
            CLAIM_ORDER_VERSION_CHRONOLOGICAL_V1,
            CLAIM_ORDER_VERSION_DOMAIN_HASH_V1,
        }:
            raise PairEventV2Error(
                f"unknown claim_order_version: {expected_claim_order}"
            )
        if (
            plan_id == PRODUCTION_PLAN_ID
            or self.config.plan_config.plan_id() == PRODUCTION_PLAN_ID
        ):
            # Pinned production identity always requires logs-first domain_hash_v1.
            expected_claim_order = CLAIM_ORDER_VERSION_DOMAIN_HASH_V1
        expected_policy = self.execution_policy_identity(
            plan_id, claim_order_version=expected_claim_order
        )
        self.coordinator.authenticate_plan_attach(
            plan_id=plan_id,
            plan_config=self.config.plan_config,
            execution_policy=expected_policy,
        )
        # Load chain identity for this plan (fail closed if missing).
        loaded = self.coordinator.load_chain_identity(
            plan_id=plan_id,
            primary_org=self.config.primary_org,
            secondary_org=self.config.secondary_org,
        )
        if loaded is None:
            raise PairEventV2Error(
                "attach_existing_plan requires durable chain identity for the plan"
            )
        session = self.coordinator.begin_plan_resume_session(plan_id=plan_id)
        self._plan_id = plan_id
        self._phase = EnginePhase.CHAIN_AUTHENTICATED
        return {
            "plan_id": plan_id,
            "active_generation": int(session["active_generation"]),
            "phase": str(self._phase),
            "claim_order_version": expected_claim_order,
        }

    def run_until_idle(self, *, max_steps: int | None = None) -> EngineMetrics:
        """Rolling node replenishment + production header/finalization + resume auth.

        Query-node claims fill up to ``max_nodes_in_flight``. Completed node slots
        are refilled **before** any header/finalization turn. Production plans also
        advance bounded candidate resume authentication every turn until the active
        generation has no unauthenticated candidates remaining — even when no
        candidate-free nodes or header work exist.

        Safe-boundary completion is generation-bound: every turn re-probes the
        active generation. A concurrent attach that bumps the generation invalidates
        local completion and drives bounded revalidation rather than idle exit on
        a stale generation.
        """
        self._require_chain_ready()
        completed_steps = 0
        pending: set[Future[str | None]] = set()
        idle_rounds = 0
        finalize_after: str | None = None
        missing_after: int | None = None
        suppress_node_submit = False
        # Bound completion to the generation that last reported complete=True.
        resume_auth_bound_generation: int | None = None

        def _try_submit_node() -> bool:
            if self._stop.is_set() or suppress_node_submit:
                return False
            if max_steps is not None and completed_steps + len(pending) >= max_steps:
                return False
            if len(pending) >= self.config.max_nodes_in_flight:
                return False
            pending.add(self._node_executor.submit(self.process_one))
            with self._metrics_lock:
                self._metrics.nodes_in_flight_high_water = max(
                    self._metrics.nodes_in_flight_high_water, len(pending)
                )
            return True

        while not self._stop.is_set():
            if max_steps is not None and completed_steps >= max_steps:
                break
            progressed = False
            while _try_submit_node():
                pass
            if pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                batch_had_work = False
                for future in done:
                    with self._metrics_lock:
                        self._metrics.in_flight_high_water_primary = max(
                            self._metrics.in_flight_high_water_primary,
                            self._primary_limiter.high_water,
                        )
                        self._metrics.in_flight_high_water_secondary = max(
                            self._metrics.in_flight_high_water_secondary,
                            self._secondary_limiter.high_water,
                        )
                    outcome = future.result()
                    if outcome is not None:
                        completed_steps += 1
                        progressed = True
                        batch_had_work = True
                if batch_had_work:
                    suppress_node_submit = False
                    while _try_submit_node():
                        pass
                elif not pending:
                    suppress_node_submit = True
            if self._plan_id is not None and self._production_logs_first_enabled():
                # Every turn re-probes generation-bound resume auth (never latch
                # an unversioned complete Boolean across generation bumps).
                auth_page = self.coordinator.authenticate_resumed_candidates(
                    plan_id=self._plan_id,
                    force=False,
                    limit=CLAIM_SCAN_PAGE_SIZE,
                )
                page_gen = int(auth_page.get("active_generation", 0))
                restarted = bool(auth_page.get("generation_restart"))
                page_complete = bool(auth_page.get("complete"))
                if restarted or (
                    resume_auth_bound_generation is not None
                    and page_gen != resume_auth_bound_generation
                    and not page_complete
                ):
                    # Concurrent generation bump — reopen safe-boundary work.
                    resume_auth_bound_generation = page_gen
                    progressed = True
                    suppress_node_submit = False
                elif page_complete:
                    resume_auth_bound_generation = page_gen
                    # complete with examined>0 still counts as progress this turn
                    if int(auth_page.get("examined", 0)) > 0:
                        progressed = True
                else:
                    resume_auth_bound_generation = None
                    progressed = True
                    suppress_node_submit = False
                header_work, finalize_after, missing_after = (
                    self._run_production_header_finalization_once(
                        finalize_after_domain_id=finalize_after,
                        missing_after_block=missing_after,
                    )
                )
                if header_work:
                    progressed = True
                    suppress_node_submit = False
            if not progressed and not pending:
                idle_rounds += 1
                if idle_rounds >= 2:
                    break
            else:
                idle_rounds = 0
        if pending:
            wait(pending)
            for future in pending:
                future.result()
        return self.metrics

    def _run_production_header_finalization_once(
        self,
        *,
        finalize_after_domain_id: str | None = None,
        missing_after_block: int | None = None,
    ) -> tuple[bool, str | None, int | None]:
        """One bounded header keyset page + one bounded finalization scan page.

        Returns ``(did_work, next_finalize_cursor, next_missing_cursor)``.
        Advances ``after_block_number`` so missing discovery never restarts
        through already-covered history. ``header_backlog`` is the exact
        coordinator-maintained distinct missing-block count.
        """
        assert self._plan_id is not None
        plan_id = self._plan_id
        did_work = False
        next_missing = missing_after_block
        if self._stop.is_set():
            return False, finalize_after_domain_id, next_missing
        # Exact backlog from incremental set (no per-turn full-table COUNT).
        with self._metrics_lock:
            self._metrics.header_backlog = self.coordinator.header_backlog_count(
                plan_id=plan_id
            )
        # One keyset page of missing blocks, continuing past prior cursor.
        missing_blocks = self.coordinator.list_missing_candidate_blocks(
            plan_id=plan_id,
            limit=HEADER_WORK_PAGE_SIZE,
            after_block_number=missing_after_block,
        )
        if missing_blocks:
            self.acquire_header_batch(plan_id=plan_id, block_numbers=missing_blocks)
            did_work = True
            next_missing = int(missing_blocks[-1])
            with self._metrics_lock:
                self._metrics.header_backlog = self.coordinator.header_backlog_count(
                    plan_id=plan_id
                )
        else:
            # End of keyset: wrap cursor so newly inserted lower blocks are seen
            # on a later turn; exact backlog remains authoritative.
            next_missing = None
        if self._stop.is_set():
            return did_work, finalize_after_domain_id, next_missing
        page = self.coordinator.list_finalizable_candidates(
            plan_id=plan_id,
            limit=FINALIZE_WORK_PAGE_SIZE,
            after_domain_id=finalize_after_domain_id,
        )
        ready = list(page.get("ready_domain_ids") or [])
        scan_through = page.get("scan_through_domain_id")
        exhausted = bool(page.get("exhausted"))
        for domain_id in ready:
            if self._stop.is_set():
                break
            self.finalize_candidate(plan_id=plan_id, domain_id=str(domain_id))
            did_work = True
        next_finalize: str | None
        if exhausted or scan_through is None:
            next_finalize = None
        else:
            next_finalize = str(scan_through)
        return did_work, next_finalize, next_missing

    def acquire_header_batch(
        self, *, plan_id: str, block_numbers: Sequence[int]
    ) -> list[CanonicalHeaderReceiptRecord]:
        """Dual-provider JSON-RPC batch for distinct blocks; shared batch raw pair.

        Validates response IDs, rejects missing/extra/duplicate members, block/hash/
        timestamp disagreement, truncation, and unauthenticated evidence. Multiple
        header receipts reference the same batch raw acquisition pair.
        """
        self._require_chain_ready()
        if self._plan_id != plan_id:
            raise PairEventV2Error("header batch plan_id does not match engine plan")
        unique_blocks = sorted({int(b) for b in block_numbers})
        if not unique_blocks:
            return []
        if len(unique_blocks) > 64:
            raise PairEventV2Error("header batch exceeds hard bound of 64 blocks")
        # Skip blocks already cached/stored.
        missing: list[int] = []
        records: list[CanonicalHeaderReceiptRecord] = []
        for block_number in unique_blocks:
            cached = self.coordinator.load_header(
                plan_id=plan_id,
                block_number=block_number,
                primary_org=self.config.primary_org,
                secondary_org=self.config.secondary_org,
            )
            if cached is not None:
                record, p_ev, s_ev = cached
                try:
                    # Batch-aware: scalar request objects use _verify_cached_header;
                    # batch array evidence uses member extraction.
                    self._verify_header_evidence_any(
                        record, p_ev, s_ev, block_number=block_number
                    )
                except Exception as exc:
                    raise PairEventV2Error(
                        f"cached header auth failed for {block_number}"
                    ) from exc
                records.append(record)
                self._add_metrics(headers_cached=1)
            else:
                missing.append(block_number)
        if not missing:
            return records
        batch_request = block_header_batch_request(missing)
        pair = self._dual_fetch(batch_request)
        # Persist batch as dual envelopes; inspect as batch JSON-RPC array.
        primary_body = self._parse_json_rpc_batch(pair[0], batch_request)
        secondary_body = self._parse_json_rpc_batch(pair[1], batch_request)
        p_ev = pair[0].evidence
        s_ev = pair[1].evidence
        if p_ev is None or s_ev is None:
            raise PairEventV2Error("header batch missing raw evidence")
        # Validate members by id.
        self._validate_header_batch_members(
            primary_body, batch_request, label="primary"
        )
        self._validate_header_batch_members(
            secondary_body, batch_request, label="secondary"
        )
        for index, block_number in enumerate(missing):
            p_member = find_batch_response_by_id(primary_body, index)
            s_member = find_batch_response_by_id(secondary_body, index)
            p_result = p_member.get("result")
            s_result = s_member.get("result")
            if not isinstance(p_result, Mapping) or not isinstance(s_result, Mapping):
                raise PairEventV2Error(
                    f"header batch member result missing for block {block_number}"
                )
            p_number = _hex_quantity(
                _require(p_result, "number", label="primary header"),
                label="primary header number",
            )
            s_number = _hex_quantity(
                _require(s_result, "number", label="secondary header"),
                label="secondary header number",
            )
            p_hash = _hex_bytes(
                _require(p_result, "hash", label="primary header"),
                32,
                label="primary header hash",
            )
            s_hash = _hex_bytes(
                _require(s_result, "hash", label="secondary header"),
                32,
                label="secondary header hash",
            )
            p_ts = _hex_quantity(
                _require(p_result, "timestamp", label="primary header"),
                label="primary header timestamp",
            )
            s_ts = _hex_quantity(
                _require(s_result, "timestamp", label="secondary header"),
                label="secondary header timestamp",
            )
            if p_number != block_number or s_number != block_number:
                raise PairEventV2Error(
                    f"header batch boundary mismatch for block {block_number}"
                )
            if p_hash != s_hash or p_ts != s_ts:
                raise PairEventV2Error(
                    f"header batch provider disagreement for block {block_number}"
                )
            header_id = compute_canonical_header_receipt_id(
                plan_id=plan_id,
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
                plan_id=plan_id,
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
            record = self.coordinator.store_header(record)
            records.append(record)
            self._add_metrics(headers_fetched=1, header_batch_members=1)
        self._add_metrics(header_batches=1)
        with self._metrics_lock:
            # Backlog proxy: missing blocks remaining after this batch (0 here).
            self._metrics.header_backlog = max(0, self._metrics.header_backlog)
        return records

    def _parse_json_rpc_batch(
        self,
        persisted: PersistedEnvelope,
        batch_request: Sequence[Mapping[str, Any]],
    ) -> list[Any]:
        if persisted.evidence is None:
            raise PairEventV2Error("batch response has no authenticated raw evidence")
        if persisted.descriptor.truncated:
            raise PairEventV2Error("header batch response was truncated")
        body = _load_authenticated_json_value(
            persisted.evidence,
            max_bytes=self.config.max_body_bytes,
            raw_root=self.config.raw_root,
        )
        # Re-check request binding against batch.
        if _canonical_json(json.loads(persisted.evidence.request_json)) != _canonical_json(
            list(batch_request)
        ):
            raise PairEventV2Error("batch request identity mismatch on evidence")
        if not isinstance(body, list):
            raise PairEventV2Error("header batch body is not a JSON array")
        return body

    def _validate_header_batch_members(
        self,
        body: Sequence[Any],
        batch_request: Sequence[Mapping[str, Any]],
        *,
        label: str,
    ) -> None:
        ids = [item.get("id") for item in batch_request if isinstance(item, Mapping)]
        seen: set[Any] = set()
        for item in body:
            if not isinstance(item, Mapping):
                raise PairEventV2Error(f"{label} batch member is not an object")
            rid = item.get("id")
            if rid in seen:
                raise PairEventV2Error(f"{label} batch has duplicate response id")
            seen.add(rid)
            if rid not in ids:
                raise PairEventV2Error(f"{label} batch has extra response id")
            if "error" in item and item["error"] is not None:
                raise PairEventV2Error(f"{label} batch member has JSON-RPC error")
        missing = [i for i in ids if i not in seen]
        if missing:
            raise PairEventV2Error(f"{label} batch missing response ids: {missing!r}")

    def finalize_candidate(
        self, *, plan_id: str, domain_id: str
    ) -> str:
        """Atomically finalize a log candidate once all required headers exist.

        Replays candidate + headers; inserts leaf/dependencies; sets AGREED.
        Candidate alone always has zero coverage credit.
        """
        self._require_chain_ready()
        if self._plan_id != plan_id:
            raise PairEventV2Error("finalize plan_id does not match engine plan")
        candidate = self.coordinator.load_log_candidate(
            plan_id=plan_id, domain_id=domain_id
        )
        if candidate is None:
            raise PairEventV2Error("log candidate missing for finalization")
        # Ensure every required block has a canonical header.
        header_ids: list[str] = []
        for block_number, expected_hash, _is_boundary in candidate["blocks"]:
            loaded = self.coordinator.load_header(
                plan_id=plan_id,
                block_number=int(block_number),
                primary_org=self.config.primary_org,
                secondary_org=self.config.secondary_org,
            )
            if loaded is None:
                raise PairEventV2Error(
                    f"canonical header missing for block {block_number}"
                )
            header = loaded[0]
            if expected_hash is not None and header.block_hash != expected_hash:
                raise PairEventV2Error(
                    f"header hash disagrees with candidate expected hash at {block_number}"
                )
            header_ids.append(header.header_receipt_id)
        # Reconstruct domain from node row via a claim-less agreed path.
        # Use internal finalize op that does not require a live lease.
        result = self.coordinator.finalize_log_candidate(
            plan_id=plan_id,
            domain_id=domain_id,
            header_receipt_ids=header_ids,
        )
        self._add_metrics(finalizations=1, agreed=1)
        return result


__all__ = [
    "AuthenticatedEvidence",
    "CHAIN_IDENTITY_RECORD_COLUMNS",
    "CHAIN_IDENTITY_SCHEMA_VERSION",
    "CHAIN_IDENTITY_TABLE",
    "CHAIN_IDENTITY_UNIQUENESS",
    "CREDENTIAL_REDACTED_DETAIL",
    "Claim",
    "ChainIdentityReceipt",
    "CredentialScanner",
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
    "HEADER_BACKLOG_METRIC_TABLE",
    "HEADER_BACKLOG_TABLE",
    "HEADER_UNIQUENESS",
    "LEAF_UNIQUENESS",
    "LOG_CANDIDATE_BLOCK_TABLE",
    "LOG_CANDIDATE_TABLE",
    "NetworkWorker",
    "PairEventV2Engine",
    "PersistedEnvelope",
    "PersistenceCoordinator",
    "ROOT_MANIFEST_TABLE",
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
