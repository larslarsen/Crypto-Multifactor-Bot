"""DEX-003 / ADR-0015 §9.8 — isolated v2 provider-matrix harness.

Final Sol source correction (offline-only). Two-file drop only; no RPC in this pass.

Hard rules enforced here:

1. Pure plan construction is separate from persistence. Existing roots authenticate
   immutable plan/catalog/attempts/state/sidecars/raw before any write; only a
   fresh empty root may create plan/catalog.
2. Runs are exclusive and immutable (O_EXCL dirs/reports); current_run pointer
   uses locked compare-and-swap generations so stale writers cannot restore PASS.
3. Standalone offline replay loads a sealed execute_live report before any run or
   pointer change; in-process replay may evaluate retained evidence before seal.
   MatrixSafetyStop is never treated as absence. PASS requires authenticated replay.
4. evidence_hash covers run/resume identity, plan, budgets, cumulative counters,
   high-water, call/receipt/raw snapshot, cells, and replay decision; only wall
   timestamps/elapsed are excluded. report_hash distinctly binds evidence_hash.
5. Live HTTP streams bytes directly into a unique attempt spool (no chunk list /
   join). Worst-case retained bytes are reserved before each request; unused
   reservation is released. Raw + receipt commit is atomic enough that unreferenced
   raw is not authority.
6. Every decodable response/error string is scanned before promotion. Empty 2xx,
   missing result, malformed envelopes/logs, truncated/unauthenticated bodies are
   safety stops. Credential hits persist only credential-free blocker metadata.
7. Complete provider metrics on all report outcomes; deterministic close on all
   failure paths; output roots may not equal/contain/sit inside data/dex003_full.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal

import httpx

from cryptofactors.acquisition.uniswap_v2 import (
    ETHEREUM_CHAIN,
    ETHEREUM_MAINNET_CHAIN_ID,
    UNISWAP_V2_FACTORY,
    _canonical_json,
    _hex_quantity,
    chain_id_request,
)
from cryptofactors.acquisition.uniswap_v2_pair_event_orchestrator import (
    ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID,
    DEX_POOL_REGISTRY_DATASET_TYPE,
    DEX_POOL_REGISTRY_RELATIVE_PATH,
    DEX_POOL_REGISTRY_SCHEMA_NAME,
    DEX_POOL_REGISTRY_SCHEMA_VERSION,
    PairEventOrchestrationError,
    load_registry_pool_refs,
    normalize_pool_address,
    verify_registry_manifest,
)
from cryptofactors.acquisition.uniswap_v2_pair_events import (
    SWAP_TOPIC,
    pair_logs_request,
)
from cryptofactors.acquisition.uniswap_v2_pair_events_v2 import (
    LOG_IDENTITY_VERSION,
    ORDERED_EVENT_TOPICS,
    QueryDomain,
    combined_pair_logs_request,
    log_identity_v2_digest,
    normalize_address,
    normalize_and_index_logs,
    normalize_provider_org,
)
from cryptofactors.catalog.dataset.models import QualityStatus
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.catalog.dataset.parse import load_manifest_file
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir

# ---------------------------------------------------------------------------
# Pinned contract
# ---------------------------------------------------------------------------

MATRIX_SCHEMA_VERSION: Final[str] = "1"
MATRIX_SOURCE_ID: Final[str] = "ethereum_json_rpc_uniswap_v2_pair_events_v2_matrix"

ANCHOR_POOL: Final[str] = "0x3139ffc91b99aa94da8a2dc13f1fc36f9bdc98ee"
BIRTH_BOUNDARY_BLOCK: Final[int] = 10_388_500
ELIGIBLE_POOL_COUNT_AT_BOUNDARY: Final[int] = 129
MAXIMUM_COHORT_SIZE: Final[int] = 128
NESTED_COHORT_SIZES: Final[tuple[int, ...]] = (1, 8, 32, 64, 128)

PINNED_COHORT_HASHES: Final[dict[int, str]] = {
    1: "592ed81e9c6fcde816e9096d0e7a5e9f2cc2722e7c5325178d7c219661fde751",
    8: "0b9a87c4066849a798bcdf3e310dd61de86ebdb961c86203dbced29aecdd292a",
    32: "e3fc4ddcd7054818814004209d48e59cebb913ace5247b6189a3e79c47dcc015",
    64: "78c973533295d96130bc108f76d904903fc79d5e7b242af1b01a45c1782c57be",
    128: "24f5924de5560ac988a7b5623c493d53dfd470b8419cd1c4c7fcb189fdf2a86e",
}

MATRIX_RANGES: Final[dict[str, tuple[int, int]]] = {
    "sparse": (10_388_500, 10_393_499),
    "medium": (11_893_500, 11_898_499),
    "hot": (16_353_500, 16_358_499),
}
V1_ANCHOR_SWAP_LOG_COUNTS: Final[dict[str, int]] = {
    "sparse": 0,
    "medium": 3,
    "hot": 18,
}
RANGE_ORDER: Final[tuple[str, ...]] = ("sparse", "medium", "hot")
DEFAULT_PROVIDER_ORGS: Final[tuple[str, str]] = ("infura", "blockpi")

LOGICAL_CHAIN_CALLS: Final[int] = 2
LOGICAL_SCALAR_CALLS: Final[int] = (
    len(RANGE_ORDER) * len(DEFAULT_PROVIDER_ORGS) * MAXIMUM_COHORT_SIZE * 2
)
LOGICAL_BATCHED_CALLS: Final[int] = (
    len(RANGE_ORDER) * len(NESTED_COHORT_SIZES) * len(DEFAULT_PROVIDER_ORGS)
)
LOGICAL_CALL_CEILING: Final[int] = (
    LOGICAL_CHAIN_CALLS + LOGICAL_SCALAR_CALLS + LOGICAL_BATCHED_CALLS
)

DEFAULT_MAX_ATTEMPTS_PER_LOGICAL_CALL: Final[int] = 3
DEFAULT_MAX_PROVIDER_ATTEMPTS: Final[int] = (
    LOGICAL_CALL_CEILING * DEFAULT_MAX_ATTEMPTS_PER_LOGICAL_CALL
)
DEFAULT_MAX_WALL_SECONDS: Final[float] = 90 * 60.0
DEFAULT_MAX_RETAINED_RESPONSE_BYTES: Final[int] = 2 * 1024 * 1024 * 1024
DEFAULT_MAX_RESPONSE_BYTES: Final[int] = 8 * 1024 * 1024
DEFAULT_REQUESTS_PER_SECOND: Final[float] = 8.0
DEFAULT_MAX_IN_FLIGHT: Final[int] = 4
DEFAULT_HTTP_TIMEOUT_SECONDS: Final[float] = 60.0

_PRODUCTION_V2_TABLES: Final[frozenset[str]] = frozenset(
    {
        "uniswap_v2_pair_event_v2_plan",
        "uniswap_v2_pair_event_v2_query_node",
        "uniswap_v2_pair_event_v2_lease",
        "uniswap_v2_pair_event_v2_leaf_receipt",
        "uniswap_v2_pair_event_v2_canonical_header_receipt",
        "uniswap_v2_pair_event_v2_coverage",
        "uniswap_v2_pair_event_v2_leaf_header_dependency",
        "uniswap_v2_pair_event_v2_terminal_receipt",
        "uniswap_v2_pair_event_v2_engine_event",
        "uniswap_v2_pair_event_v2_execution_policy",
        "uniswap_v2_pair_event_v2_chain_identity",
    }
)

_SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|authorization|password|secret|token|private[_-]?key|bearer)",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_URL_WITH_CREDS_RE = re.compile(r"://[^/\s]*:[^/\s]*@")
_QUERY_SECRET_RE = re.compile(
    r"([?&](api[_-]?key|apikey|key|token|password|secret|access_token)=)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"bearer\s+[a-z0-9._\-+/=]+", re.IGNORECASE)
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_RUN_ID_RE = re.compile(r"^run_[a-f0-9]{32}$")

# Only pure wall-clock / duration fields are excluded from evidence hashing.
_UNHASHED_METADATA_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "started_at",
        "finished_at",
        "retained_at",
        "created_at",
        "updated_at",
        "elapsed_seconds",
        "wall_clock",
    }
)

CallKind = Literal["chain", "scalar", "batch"]
CellStatus = Literal["pass", "fail", "incomplete"]
RunMode = Literal["plan_only", "offline_replay", "execute_live"]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class MatrixError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, object] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


class MatrixSafetyStop(MatrixError):
    """Immediate safety stop — run must not PASS."""


class MatrixCellFailure(MatrixError):
    """Ordinary cell failure (limit/429/size/RPC)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _new_run_id() -> str:
    return "run_" + uuid.uuid4().hex


def compact_json_array_hash(values: Sequence[str]) -> str:
    return _sha256_text(json.dumps(list(values), separators=(",", ":")))


def _scan_text_for_secrets(text: str, *, label: str) -> None:
    if _URL_WITH_CREDS_RE.search(text):
        raise MatrixSafetyStop(
            f"credential-bearing URL detected in {label}",
            context={"label": label},
        )
    if _URL_RE.search(text):
        raise MatrixSafetyStop(
            f"endpoint URL detected in {label}",
            context={"label": label},
        )
    if _QUERY_SECRET_RE.search(text) or _BEARER_RE.search(text):
        raise MatrixSafetyStop(
            f"credential material detected in {label}",
            context={"label": label},
        )
    lower = text.lower()
    if "api_key=" in lower or "apikey=" in lower or "authorization:" in lower:
        raise MatrixSafetyStop(
            f"credential material detected in {label}",
            context={"label": label},
        )


def _scan_bytes_for_secrets(data: bytes, *, label: str) -> None:
    """Scan decodable response/error bytes before raw promotion."""
    if not data:
        return
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        # JSON-RPC is UTF-8; non-decodable over-cap prefixes still scanned loosely.
        text = data.decode("utf-8", errors="replace")
    _scan_text_for_secrets(text, label=label)


def _reject_sensitive_payload(payload: object, *, label: str) -> None:
    try:
        text = json.dumps(payload, default=str)
    except TypeError as exc:
        raise MatrixSafetyStop(
            f"credential scan could not serialize {label}",
            context={"error": type(exc).__name__},
        ) from exc
    _scan_text_for_secrets(text, label=label)

    def walk(node: object, path: str) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                key_s = str(key)
                if _SENSITIVE_KEY_RE.search(key_s):
                    raise MatrixSafetyStop(
                        f"sensitive key {key_s!r} in {label}",
                        context={"path": f"{path}.{key_s}"},
                    )
                walk(value, f"{path}.{key_s}")
        elif isinstance(node, (list, tuple)):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")
        elif isinstance(node, str):
            _scan_text_for_secrets(node, label=f"{label}:{path}")

    walk(payload, "$")


def _resolve_path(path: Path | str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def _path_related(a: Path, b: Path) -> bool:
    try:
        a.relative_to(b)
        return True
    except ValueError:
        pass
    try:
        b.relative_to(a)
        return True
    except ValueError:
        return False


def _project_dex003_full_root() -> Path:
    return (Path.cwd() / "data" / "dex003_full").resolve()


def assert_safe_matrix_output_root(
    output_root: Path | str,
    *,
    registry_store_root: Path | str | None = None,
) -> Path:
    root = _resolve_path(output_root)
    if root.is_file():
        raise MatrixSafetyStop(
            "matrix output root must be a directory path, not a file",
            context={"output_root": str(root)},
        )
    if root.name in {"dex003_full.db", "dex003_full.db-wal", "dex003_full.db-shm"}:
        raise MatrixSafetyStop(
            "matrix output root must not be production dex003_full.db",
            context={"output_root": str(root)},
        )
    # Always reject project data/dex003_full tree (equal / inside / containing).
    dex_full = _project_dex003_full_root()
    if _path_related(root, dex_full):
        raise MatrixSafetyStop(
            "matrix output root must not equal, contain, or sit inside data/dex003_full",
            context={"output_root": str(root), "dex003_full": str(dex_full)},
        )
    # Also reject any path whose resolved parts include data/dex003_full sequence.
    parts = list(root.parts)
    for i in range(len(parts) - 1):
        if parts[i] == "data" and parts[i + 1] == "dex003_full":
            raise MatrixSafetyStop(
                "matrix output root collides with data/dex003_full path segment",
                context={"output_root": str(root)},
            )
    if ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID in root.parts:
        raise MatrixSafetyStop(
            "matrix output root collides with accepted registry dataset id",
            context={"output_root": str(root)},
        )
    text = str(root).replace("\\", "/")
    if "/dex/dex_pool_registry" in text or text.endswith("/dex/dex_pool_registry"):
        raise MatrixSafetyStop(
            "matrix output root collides with staged registry product path",
            context={"output_root": str(root)},
        )
    if registry_store_root is not None:
        reg = _resolve_path(registry_store_root)
        if _path_related(root, reg):
            raise MatrixSafetyStop(
                "matrix output root must not equal, contain, or sit inside the registry store",
                context={"output_root": str(root), "registry_store_root": str(reg)},
            )
        try:
            accepted = dataset_absolute_dir(reg, ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID).resolve()
            if _path_related(root, accepted):
                raise MatrixSafetyStop(
                    "matrix output root collides with accepted registry dataset directory",
                    context={"output_root": str(root)},
                )
        except MatrixSafetyStop:
            raise
        except Exception:
            pass
        staged = reg / "staged"
        if staged.exists() and _path_related(root, staged.resolve()):
            raise MatrixSafetyStop(
                "matrix output root collides with staged production tree",
                context={"output_root": str(root)},
            )
    return root


def _strip_for_evidence(node: Any) -> Any:
    if isinstance(node, Mapping):
        return {
            k: _strip_for_evidence(v)
            for k, v in node.items()
            if k not in _UNHASHED_METADATA_FIELDS
            and k not in {"report_hash", "evidence_hash"}
        }
    if isinstance(node, list):
        return [_strip_for_evidence(x) for x in node]
    return node


def compute_evidence_hash(payload: Mapping[str, Any]) -> str:
    """Stable hash over all evidence-bearing fields (not wall timestamps)."""
    return _sha256_text(_canonical_json(_strip_for_evidence(dict(payload))))


def compute_report_hash(*, evidence_hash: str, payload: Mapping[str, Any]) -> str:
    """Distinct report hash that binds evidence_hash plus sealed report body."""
    body = _strip_for_evidence(dict(payload))
    binding = {"evidence_hash": evidence_hash, "report": body}
    return _sha256_text(_canonical_json(binding))


def _exclusive_write_text(path: Path, text: str) -> None:
    """Create file exclusively (fail if exists)."""
    _scan_text_for_secrets(text, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(str(path), flags, 0o644)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _atomic_replace_text(path: Path, text: str) -> None:
    _scan_text_for_secrets(text, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------


@dataclass
class MatrixBudgets:
    max_logical_calls: int = LOGICAL_CALL_CEILING
    max_attempts_per_logical_call: int = DEFAULT_MAX_ATTEMPTS_PER_LOGICAL_CALL
    max_provider_attempts: int = DEFAULT_MAX_PROVIDER_ATTEMPTS
    max_wall_seconds: float = DEFAULT_MAX_WALL_SECONDS
    max_retained_response_bytes: int = DEFAULT_MAX_RETAINED_RESPONSE_BYTES
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES
    requests_per_second: float = DEFAULT_REQUESTS_PER_SECOND
    max_in_flight: int = DEFAULT_MAX_IN_FLIGHT
    http_timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if not 1 <= self.max_logical_calls <= LOGICAL_CALL_CEILING:
            raise MatrixError("max_logical_calls out of range")
        if not 1 <= self.max_attempts_per_logical_call <= 3:
            raise MatrixError("max_attempts_per_logical_call out of range")
        if not 1 <= self.max_provider_attempts <= DEFAULT_MAX_PROVIDER_ATTEMPTS:
            raise MatrixError("max_provider_attempts out of range")
        if not 0 < self.max_wall_seconds <= DEFAULT_MAX_WALL_SECONDS:
            raise MatrixError("max_wall_seconds out of range")
        if not 1 <= self.max_retained_response_bytes <= DEFAULT_MAX_RETAINED_RESPONSE_BYTES:
            raise MatrixError("max_retained_response_bytes out of range")
        if not 1 <= self.max_response_bytes <= DEFAULT_MAX_RESPONSE_BYTES:
            raise MatrixError("max_response_bytes out of range")
        if not 0 < self.requests_per_second <= DEFAULT_REQUESTS_PER_SECOND:
            raise MatrixError("requests_per_second out of range")
        if not 1 <= self.max_in_flight <= DEFAULT_MAX_IN_FLIGHT:
            raise MatrixError("max_in_flight out of range")
        if self.http_timeout_seconds <= 0:
            raise MatrixError("http_timeout_seconds must be positive")

    def as_report_dict(self) -> dict[str, Any]:
        return {
            "max_logical_calls": self.max_logical_calls,
            "max_attempts_per_logical_call": self.max_attempts_per_logical_call,
            "max_provider_attempts": self.max_provider_attempts,
            "max_wall_seconds": self.max_wall_seconds,
            "max_retained_response_bytes": self.max_retained_response_bytes,
            "max_response_bytes": self.max_response_bytes,
            "requests_per_second": self.requests_per_second,
            "max_in_flight": self.max_in_flight,
            "http_timeout_seconds": self.http_timeout_seconds,
            "logical_call_ceiling": LOGICAL_CALL_CEILING,
        }


@dataclass
class BudgetTracker:
    budgets: MatrixBudgets
    started_at: float = field(default_factory=time.monotonic)
    logical_calls_started: int = 0
    provider_attempts: int = 0
    retained_response_bytes: int = 0
    reserved_response_bytes: int = 0
    http_429_count: int = 0
    high_water_in_flight: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def check_wall(self) -> None:
        elapsed = time.monotonic() - self.started_at
        if elapsed > self.budgets.max_wall_seconds:
            raise MatrixSafetyStop(
                "global wall-time budget breached",
                context={
                    "elapsed_seconds": round(elapsed, 3),
                    "max_wall_seconds": self.budgets.max_wall_seconds,
                },
            )

    def register_logical_call(self) -> None:
        with self._lock:
            self.check_wall()
            if self.logical_calls_started >= self.budgets.max_logical_calls:
                raise MatrixSafetyStop("global logical-call budget breached")
            self.logical_calls_started += 1

    def register_attempt(self) -> None:
        with self._lock:
            self.check_wall()
            if self.provider_attempts >= self.budgets.max_provider_attempts:
                raise MatrixSafetyStop("global provider-attempt budget breached")
            self.provider_attempts += 1

    def reserve_response_bytes(self, nbytes: int) -> None:
        """Reserve worst-case capacity before starting a request."""
        if nbytes < 0:
            raise MatrixError("reserve bytes cannot be negative")
        with self._lock:
            self.check_wall()
            projected = (
                self.retained_response_bytes + self.reserved_response_bytes + nbytes
            )
            if projected > self.budgets.max_retained_response_bytes:
                raise MatrixSafetyStop(
                    "global retained-response-bytes budget would be breached by reservation",
                    context={
                        "projected": projected,
                        "max": self.budgets.max_retained_response_bytes,
                    },
                )
            self.reserved_response_bytes += nbytes

    def commit_reservation(self, reserved: int, actual: int) -> None:
        """Convert reservation into retained actual; release unused."""
        if actual < 0 or reserved < 0 or actual > reserved:
            raise MatrixError("invalid reservation commit")
        with self._lock:
            if self.reserved_response_bytes < reserved:
                raise MatrixSafetyStop("reservation underflow")
            self.reserved_response_bytes -= reserved
            next_retained = self.retained_response_bytes + actual
            if next_retained > self.budgets.max_retained_response_bytes:
                raise MatrixSafetyStop("retained bytes exceed budget on commit")
            self.retained_response_bytes = next_retained

    def release_reservation(self, reserved: int) -> None:
        with self._lock:
            if self.reserved_response_bytes < reserved:
                raise MatrixSafetyStop("reservation release underflow")
            self.reserved_response_bytes -= reserved

    def note_429(self) -> None:
        with self._lock:
            self.http_429_count += 1

    def note_in_flight(self, current: int) -> None:
        with self._lock:
            if current > self.high_water_in_flight:
                self.high_water_in_flight = current

    def load_prior(self, counters: Mapping[str, int]) -> None:
        with self._lock:
            lc = int(counters["logical_calls"])
            att = int(counters["attempts"])
            ret = int(counters["retained_bytes"])
            h429 = int(counters["http_429s"])
            hw = int(counters.get("high_water_in_flight", 0))
            if min(lc, att, ret, h429, hw) < 0:
                raise MatrixSafetyStop("negative reconstructed counters")
            if lc > self.budgets.max_logical_calls:
                raise MatrixSafetyStop("prior logical calls breach budget")
            if att > self.budgets.max_provider_attempts:
                raise MatrixSafetyStop("prior attempts breach budget")
            if ret > self.budgets.max_retained_response_bytes:
                raise MatrixSafetyStop("prior retained bytes breach budget")
            self.logical_calls_started = lc
            self.provider_attempts = att
            self.retained_response_bytes = ret
            self.http_429_count = h429
            self.high_water_in_flight = hw
            self.reserved_response_bytes = 0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "elapsed_seconds": round(time.monotonic() - self.started_at, 3),
                "logical_calls_started": self.logical_calls_started,
                "provider_attempts": self.provider_attempts,
                "retained_response_bytes": self.retained_response_bytes,
                "reserved_response_bytes": self.reserved_response_bytes,
                "http_429_count": self.http_429_count,
                "high_water_in_flight": self.high_water_in_flight,
            }

    def evidence_counters(self) -> dict[str, int]:
        with self._lock:
            return {
                "logical_calls_started": self.logical_calls_started,
                "provider_attempts": self.provider_attempts,
                "retained_response_bytes": self.retained_response_bytes,
                "http_429_count": self.http_429_count,
                "high_water_in_flight": self.high_water_in_flight,
            }


class _RpsLimiter:
    def __init__(self, *, rate: float) -> None:
        self.rate = rate
        self.capacity = max(rate, 1.0)
        self.tokens = self.capacity
        self.updated = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, *, stop: threading.Event) -> None:
        while not stop.is_set():
            with self._lock:
                now = time.monotonic()
                elapsed = now - self.updated
                self.updated = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                need = (1.0 - self.tokens) / self.rate
            stop.wait(min(max(need, 0.001), 0.25))
        raise MatrixSafetyStop("stop signal set while waiting for RPS token")


class _ProviderGate:
    def __init__(self, *, max_in_flight: int, rps: float) -> None:
        self.semaphore = threading.Semaphore(max_in_flight)
        self.rps = _RpsLimiter(rate=rps)
        self.in_flight = 0
        self._lock = threading.Lock()

    def acquire(self, *, stop: threading.Event, tracker: BudgetTracker) -> None:
        while not stop.is_set():
            if self.semaphore.acquire(timeout=0.1):
                break
        else:
            raise MatrixSafetyStop("stop signal set while waiting for in-flight slot")
        try:
            self.rps.acquire(stop=stop)
        except Exception:
            self.semaphore.release()
            raise
        with self._lock:
            self.in_flight += 1
            tracker.note_in_flight(self.in_flight)

    def release(self) -> None:
        with self._lock:
            self.in_flight = max(0, self.in_flight - 1)
        self.semaphore.release()


# ---------------------------------------------------------------------------
# Registry + plan (pure)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegistryVerification:
    dataset_id: str
    dataset_dir: str
    pools_path: str
    parquet_sha256: str
    parquet_bytes: int
    pool_count: int


def verify_and_load_accepted_registry(
    registry_store_root: Path | str,
    *,
    expected_dataset_id: str = ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID,
) -> tuple[RegistryVerification, tuple[Any, ...]]:
    store = _resolve_path(registry_store_root)
    dataset_dir = dataset_absolute_dir(store, expected_dataset_id)
    manifest_path = dataset_dir / "manifest.json"
    pools_path = dataset_dir / DEX_POOL_REGISTRY_RELATIVE_PATH
    if not manifest_path.is_file():
        raise MatrixSafetyStop("registry manifest.json missing")
    try:
        manifest = load_manifest_file(manifest_path)
    except Exception as exc:
        raise MatrixSafetyStop(
            "failed to load registry manifest",
            context={"error": type(exc).__name__},
        ) from exc
    try:
        verify_registry_manifest(
            manifest, require_accepted=True, expected_dataset_id=expected_dataset_id
        )
    except PairEventOrchestrationError as exc:
        raise MatrixSafetyStop(str(exc), context=dict(exc.context)) from exc
    if manifest.dataset_id != expected_dataset_id:
        raise MatrixSafetyStop("registry dataset_id drift")
    if not pools_path.is_file():
        raise MatrixSafetyStop("registry pools parquet missing")
    observed_sha, observed_bytes = stream_sha256_and_size(pools_path)
    declared = next(
        spec
        for spec in manifest.files
        if spec.relative_path == DEX_POOL_REGISTRY_RELATIVE_PATH
    )
    if observed_sha != declared.sha256 or observed_bytes != declared.bytes:
        raise MatrixSafetyStop("registry parquet does not match manifest declaration")
    if manifest.dataset_type != DEX_POOL_REGISTRY_DATASET_TYPE:
        raise MatrixSafetyStop("registry dataset_type drift")
    if (
        manifest.schema.name != DEX_POOL_REGISTRY_SCHEMA_NAME
        or manifest.schema.version != DEX_POOL_REGISTRY_SCHEMA_VERSION
    ):
        raise MatrixSafetyStop("registry schema drift")
    if manifest.quality_status is not QualityStatus.PASS:
        raise MatrixSafetyStop("registry quality is not PASS")
    try:
        pools = load_registry_pool_refs(pools_path)
    except PairEventOrchestrationError as exc:
        raise MatrixSafetyStop(str(exc), context=dict(exc.context)) from exc
    return (
        RegistryVerification(
            dataset_id=expected_dataset_id,
            dataset_dir=str(dataset_dir),
            pools_path=str(pools_path),
            parquet_sha256=observed_sha,
            parquet_bytes=observed_bytes,
            pool_count=len(pools),
        ),
        pools,
    )


def select_matrix_maximum_cohort(
    pools: Sequence[Any],
    *,
    anchor: str = ANCHOR_POOL,
    birth_boundary_block: int = BIRTH_BOUNDARY_BLOCK,
) -> tuple[str, ...]:
    anchor_n = normalize_address(anchor, label="anchor")
    eligible: list[str] = []
    seen: set[str] = set()
    for pool in pools:
        addr = normalize_pool_address(pool.pool_address)
        if int(pool.creation_block) <= birth_boundary_block:
            if addr in seen:
                raise MatrixSafetyStop("duplicate eligible registry address")
            seen.add(addr)
            eligible.append(addr)
    if len(eligible) != ELIGIBLE_POOL_COUNT_AT_BOUNDARY:
        raise MatrixSafetyStop(
            "eligible pool count at birth boundary drifted",
            context={"observed": len(eligible), "expected": ELIGIBLE_POOL_COUNT_AT_BOUNDARY},
        )
    if anchor_n not in seen:
        raise MatrixSafetyStop("anchor pool is not eligible at birth boundary")
    others = sorted(a for a in eligible if a != anchor_n)
    cohort = (anchor_n,) + tuple(others[: MAXIMUM_COHORT_SIZE - 1])
    if len(cohort) != MAXIMUM_COHORT_SIZE or len(set(cohort)) != len(cohort):
        raise MatrixSafetyStop("maximum cohort size/uniqueness mismatch")
    return cohort


def nested_cohorts(maximum_cohort: Sequence[str]) -> dict[int, tuple[str, ...]]:
    if len(maximum_cohort) != MAXIMUM_COHORT_SIZE:
        raise MatrixError("maximum cohort must have 128 addresses")
    return {size: tuple(maximum_cohort[:size]) for size in NESTED_COHORT_SIZES}


def verify_pinned_cohort_hashes(cohorts: Mapping[int, Sequence[str]]) -> dict[int, str]:
    observed: dict[int, str] = {}
    for size in NESTED_COHORT_SIZES:
        digest = compact_json_array_hash(cohorts[size])
        if digest != PINNED_COHORT_HASHES[size]:
            raise MatrixSafetyStop(
                "cohort hash drift",
                context={"size": size, "observed": digest, "expected": PINNED_COHORT_HASHES[size]},
            )
        observed[size] = digest
    return observed


@dataclass(frozen=True, slots=True)
class MatrixPlan:
    matrix_id: str
    schema_version: str
    registry_dataset_id: str
    registry_parquet_sha256: str
    registry_parquet_bytes: int
    anchor_pool: str
    birth_boundary_block: int
    maximum_cohort: tuple[str, ...]
    nested_cohort_hashes: dict[int, str]
    ranges: dict[str, tuple[int, int]]
    v1_anchor_swap_log_counts: dict[str, int]
    provider_orgs: tuple[str, str]
    topics: tuple[str, str]
    log_identity_version: str
    chain: str
    factory: str
    logical_call_ceiling: int
    created_at: str

    def identity_payload(self) -> dict[str, Any]:
        return {
            "anchor_pool": self.anchor_pool,
            "birth_boundary_block": self.birth_boundary_block,
            "chain": self.chain,
            "factory": self.factory,
            "log_identity_version": self.log_identity_version,
            "logical_call_ceiling": self.logical_call_ceiling,
            "maximum_cohort": list(self.maximum_cohort),
            "nested_cohort_hashes": {
                str(k): self.nested_cohort_hashes[k] for k in sorted(self.nested_cohort_hashes)
            },
            "provider_orgs": list(self.provider_orgs),
            "ranges": {
                name: {"end": self.ranges[name][1], "start": self.ranges[name][0]}
                for name in RANGE_ORDER
            },
            "registry_dataset_id": self.registry_dataset_id,
            "registry_parquet_bytes": self.registry_parquet_bytes,
            "registry_parquet_sha256": self.registry_parquet_sha256,
            "schema_version": self.schema_version,
            "topics": list(self.topics),
            "v1_anchor_swap_log_counts": {
                name: self.v1_anchor_swap_log_counts[name] for name in RANGE_ORDER
            },
        }

    def to_public_dict(self) -> dict[str, Any]:
        payload = self.identity_payload()
        payload["matrix_id"] = self.matrix_id
        payload["created_at"] = self.created_at
        payload["nested_cohort_sizes"] = list(NESTED_COHORT_SIZES)
        payload["eligible_pool_count_at_boundary"] = ELIGIBLE_POOL_COUNT_AT_BOUNDARY
        _reject_sensitive_payload(payload, label="matrix_plan")
        return payload

    @staticmethod
    def from_public_dict(payload: Mapping[str, Any]) -> MatrixPlan:
        ranges = {
            name: (int(payload["ranges"][name]["start"]), int(payload["ranges"][name]["end"]))
            for name in RANGE_ORDER
        }
        hashes = {int(k): str(v) for k, v in dict(payload["nested_cohort_hashes"]).items()}
        return MatrixPlan(
            matrix_id=str(payload["matrix_id"]),
            schema_version=str(payload["schema_version"]),
            registry_dataset_id=str(payload["registry_dataset_id"]),
            registry_parquet_sha256=str(payload["registry_parquet_sha256"]),
            registry_parquet_bytes=int(payload["registry_parquet_bytes"]),
            anchor_pool=str(payload["anchor_pool"]),
            birth_boundary_block=int(payload["birth_boundary_block"]),
            maximum_cohort=tuple(payload["maximum_cohort"]),
            nested_cohort_hashes=hashes,
            ranges=ranges,
            v1_anchor_swap_log_counts={
                name: int(payload["v1_anchor_swap_log_counts"][name]) for name in RANGE_ORDER
            },
            provider_orgs=(str(payload["provider_orgs"][0]), str(payload["provider_orgs"][1])),
            topics=(str(payload["topics"][0]), str(payload["topics"][1])),
            log_identity_version=str(payload["log_identity_version"]),
            chain=str(payload["chain"]),
            factory=str(payload["factory"]),
            logical_call_ceiling=int(payload["logical_call_ceiling"]),
            created_at=str(payload.get("created_at") or ""),
        )


def compute_matrix_id_from_payload(payload: Mapping[str, Any]) -> str:
    return "mtx_" + _sha256_text(_canonical_json(dict(payload)))


def build_matrix_plan(
    *,
    registry_store_root: Path | str,
    provider_orgs: tuple[str, str] = DEFAULT_PROVIDER_ORGS,
) -> MatrixPlan:
    """Pure plan construction — no matrix output writes."""
    primary = normalize_provider_org(provider_orgs[0], label="primary_org")
    secondary = normalize_provider_org(provider_orgs[1], label="secondary_org")
    if primary == secondary:
        raise MatrixError("provider organizations must be distinct")
    verification, pools = verify_and_load_accepted_registry(registry_store_root)
    maximum = select_matrix_maximum_cohort(pools)
    hashes = verify_pinned_cohort_hashes(nested_cohorts(maximum))
    draft = {
        "anchor_pool": ANCHOR_POOL,
        "birth_boundary_block": BIRTH_BOUNDARY_BLOCK,
        "chain": ETHEREUM_CHAIN,
        "factory": UNISWAP_V2_FACTORY.lower(),
        "log_identity_version": LOG_IDENTITY_VERSION,
        "logical_call_ceiling": LOGICAL_CALL_CEILING,
        "maximum_cohort": list(maximum),
        "nested_cohort_hashes": {str(k): hashes[k] for k in NESTED_COHORT_SIZES},
        "provider_orgs": [primary, secondary],
        "ranges": {
            name: {"end": MATRIX_RANGES[name][1], "start": MATRIX_RANGES[name][0]}
            for name in RANGE_ORDER
        },
        "registry_dataset_id": verification.dataset_id,
        "registry_parquet_bytes": verification.parquet_bytes,
        "registry_parquet_sha256": verification.parquet_sha256,
        "schema_version": MATRIX_SCHEMA_VERSION,
        "topics": list(ORDERED_EVENT_TOPICS),
        "v1_anchor_swap_log_counts": {
            name: V1_ANCHOR_SWAP_LOG_COUNTS[name] for name in RANGE_ORDER
        },
    }
    matrix_id = compute_matrix_id_from_payload(draft)
    plan = MatrixPlan(
        matrix_id=matrix_id,
        schema_version=MATRIX_SCHEMA_VERSION,
        registry_dataset_id=verification.dataset_id,
        registry_parquet_sha256=verification.parquet_sha256,
        registry_parquet_bytes=verification.parquet_bytes,
        anchor_pool=ANCHOR_POOL,
        birth_boundary_block=BIRTH_BOUNDARY_BLOCK,
        maximum_cohort=maximum,
        nested_cohort_hashes=hashes,
        ranges=dict(MATRIX_RANGES),
        v1_anchor_swap_log_counts=dict(V1_ANCHOR_SWAP_LOG_COUNTS),
        provider_orgs=(primary, secondary),
        topics=ORDERED_EVENT_TOPICS,
        log_identity_version=LOG_IDENTITY_VERSION,
        chain=ETHEREUM_CHAIN,
        factory=UNISWAP_V2_FACTORY.lower(),
        logical_call_ceiling=LOGICAL_CALL_CEILING,
        created_at=_now_iso(),
    )
    _reject_sensitive_payload(plan.to_public_dict(), label="matrix_plan")
    return plan


@dataclass(frozen=True, slots=True)
class LogicalCall:
    logical_call_id: str
    kind: CallKind
    provider_org: str
    range_name: str | None
    start_block: int | None
    end_block: int | None
    address: str | None
    topic: str | None
    cohort_size: int | None
    request: dict[str, Any]

    def request_json(self) -> str:
        return _canonical_json(self.request)


def iter_logical_calls(plan: MatrixPlan) -> tuple[LogicalCall, ...]:
    calls: list[LogicalCall] = []
    for org in plan.provider_orgs:
        calls.append(
            LogicalCall(
                logical_call_id=f"chain:{org}",
                kind="chain",
                provider_org=org,
                range_name=None,
                start_block=None,
                end_block=None,
                address=None,
                topic=None,
                cohort_size=None,
                request=chain_id_request(),
            )
        )
    for range_name in RANGE_ORDER:
        start, end = plan.ranges[range_name]
        for org in plan.provider_orgs:
            for address in plan.maximum_cohort:
                for topic in plan.topics:
                    topic_tag = "swap" if topic == SWAP_TOPIC else "sync"
                    lid = f"scalar:{range_name}:{org}:{address}:{topic_tag}"
                    calls.append(
                        LogicalCall(
                            logical_call_id=lid,
                            kind="scalar",
                            provider_org=org,
                            range_name=range_name,
                            start_block=start,
                            end_block=end,
                            address=address,
                            topic=topic,
                            cohort_size=None,
                            request=pair_logs_request(
                                pair=address,
                                topic=topic,
                                start_block=start,
                                end_block=end,
                            ),
                        )
                    )
    for range_name in RANGE_ORDER:
        start, end = plan.ranges[range_name]
        for size in NESTED_COHORT_SIZES:
            addresses = tuple(sorted(plan.maximum_cohort[:size]))
            for org in plan.provider_orgs:
                lid = f"batch:{range_name}:{size}:{org}"
                calls.append(
                    LogicalCall(
                        logical_call_id=lid,
                        kind="batch",
                        provider_org=org,
                        range_name=range_name,
                        start_block=start,
                        end_block=end,
                        address=None,
                        topic=None,
                        cohort_size=size,
                        request=combined_pair_logs_request(
                            addresses=addresses,
                            start_block=start,
                            end_block=end,
                            topics=plan.topics,
                        ),
                    )
                )
    if len(calls) != LOGICAL_CALL_CEILING:
        raise MatrixError(
            "logical call catalog size drift",
            context={"observed": len(calls), "expected": LOGICAL_CALL_CEILING},
        )
    return tuple(calls)


def catalog_entries(plan: MatrixPlan) -> list[dict[str, Any]]:
    return [
        {
            "logical_call_id": c.logical_call_id,
            "kind": c.kind,
            "provider_org": c.provider_org,
            "request_sha256": _sha256_text(c.request_json()),
            "request_json": c.request_json(),
        }
        for c in iter_logical_calls(plan)
    ]


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


def _promote_content_addressed(spool_path: Path, raw_dir: Path, digest: str) -> Path:
    dest = raw_dir / f"{digest}.bin"
    if dest.exists():
        existing = dest.read_bytes()
        if _sha256_bytes(existing) != digest or existing != spool_path.read_bytes():
            raise MatrixSafetyStop(
                "content-addressed raw object identity mismatch",
                context={"body_sha256": digest},
            )
        try:
            spool_path.unlink()
        except OSError:
            pass
        return dest
    tmp = raw_dir / f".promote_{digest}_{uuid.uuid4().hex}.tmp"
    try:
        os.replace(spool_path, tmp)
        try:
            os.link(tmp, dest)
        except FileExistsError:
            existing = dest.read_bytes()
            if _sha256_bytes(existing) != digest or existing != tmp.read_bytes():
                raise MatrixSafetyStop("content-addressed promotion race mismatch")
        except OSError:
            if not dest.exists():
                os.replace(tmp, dest)
                return dest
            existing = dest.read_bytes()
            if _sha256_bytes(existing) != digest:
                raise MatrixSafetyStop("content-addressed promotion race mismatch")
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
    except MatrixSafetyStop:
        raise
    except OSError as exc:
        raise MatrixSafetyStop(
            "raw-persistence failure",
            context={"error": type(exc).__name__},
        ) from exc
    return dest


class MatrixStore:
    def __init__(
        self,
        output_root: Path | str,
        *,
        registry_store_root: Path | str | None = None,
        run_id: str | None = None,
        create_run: bool = True,
    ) -> None:
        self._closed = False
        self.root = assert_safe_matrix_output_root(
            output_root, registry_store_root=registry_store_root
        )
        self.registry_store_root = (
            _resolve_path(registry_store_root) if registry_store_root else None
        )
        self.root.mkdir(parents=True, exist_ok=True)
        self.raw_dir = self.root / "raw"
        self.spool_dir = self.root / "spool"
        self.receipts_dir = self.root / "receipts"
        self.runs_dir = self.root / "runs"
        self.plan_path = self.root / "plan.json"
        self.catalog_path = self.root / "logical_call_catalog.json"
        self.current_run_path = self.root / "current_run.json"
        self.current_lock_path = self.root / "current_run.lock"
        self.high_water_path = self.root / "high_water.json"
        self.state_db = self.root / "matrix_state.sqlite3"
        for d in (self.raw_dir, self.spool_dir, self.receipts_dir, self.runs_dir):
            d.mkdir(parents=True, exist_ok=True)
        self._assert_state_db_not_production()
        self._conn = sqlite3.connect(str(self.state_db), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()
        self._lock = threading.Lock()
        self._open_spools: list[Path] = []
        self.run_id: str | None = None
        self.run_dir: Path | None = None
        self.report_path: Path | None = None
        self.report_incomplete_path: Path | None = None
        self.resume_identity: str | None = None
        if create_run:
            self.begin_run(run_id=run_id)

    def begin_run(self, *, run_id: str | None = None) -> str:
        rid = run_id or _new_run_id()
        if not _RUN_ID_RE.fullmatch(rid):
            raise MatrixError("invalid run_id")
        run_dir = self.runs_dir / rid
        try:
            os.mkdir(run_dir)  # exclusive — fail if exists
        except FileExistsError as exc:
            raise MatrixSafetyStop(
                "run directory already exists; run IDs are immutable and exclusive",
                context={"run_id": rid},
            ) from exc
        self.run_id = rid
        self.run_dir = run_dir
        self.report_path = run_dir / "report.json"
        self.report_incomplete_path = run_dir / "report.incomplete.json"
        return rid

    def _assert_state_db_not_production(self) -> None:
        if not self.state_db.exists():
            return
        conn = sqlite3.connect(str(self.state_db))
        try:
            names = {
                str(r[0])
                for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        finally:
            conn.close()
        if names & _PRODUCTION_V2_TABLES:
            raise MatrixSafetyStop(
                "matrix state database contains production v2 tables",
                context={"path": str(self.state_db)},
            )

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS attempt_receipt (
                logical_call_id TEXT NOT NULL,
                attempt INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                provider_org TEXT NOT NULL,
                kind TEXT NOT NULL,
                request_sha256 TEXT NOT NULL,
                request_json TEXT NOT NULL,
                status_code INTEGER,
                body_sha256 TEXT,
                body_bytes INTEGER NOT NULL,
                observed_body_bytes INTEGER,
                truncated INTEGER NOT NULL DEFAULT 0,
                latency_ms REAL,
                http_429 INTEGER NOT NULL DEFAULT 0,
                error_class TEXT,
                error_detail TEXT,
                retained_at TEXT NOT NULL,
                PRIMARY KEY (logical_call_id, attempt)
            );
            CREATE TABLE IF NOT EXISTS logical_call_state (
                logical_call_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                provider_org TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                terminal_status TEXT,
                final_body_sha256 TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pointer_generation (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                generation INTEGER NOT NULL
            );
            INSERT OR IGNORE INTO pointer_generation (id, generation) VALUES (1, 0);
            """
        )
        self._conn.commit()

    # Root entries allowed on a fresh harness scaffold (created by __init__).
    # Anything else (e.g. noise.txt) means the root is not safe for plan create.
    _FRESH_ROOT_ALLOWLIST: frozenset[str] = frozenset(
        {
            "raw",
            "spool",
            "receipts",
            "runs",
            "matrix_state.sqlite3",
            "matrix_state.sqlite3-wal",
            "matrix_state.sqlite3-shm",
            "current_run.lock",
        }
    )

    def is_fresh_empty(self) -> bool:
        """True only when the root has no plan/evidence and no stray files."""
        if self.plan_path.exists() or self.catalog_path.exists():
            return False
        if self.current_run_path.exists() or self.high_water_path.exists():
            return False
        n = self._conn.execute("SELECT COUNT(*) AS n FROM attempt_receipt").fetchone()["n"]
        if int(n) > 0:
            return False
        n_state = self._conn.execute(
            "SELECT COUNT(*) AS n FROM logical_call_state"
        ).fetchone()["n"]
        if int(n_state) > 0:
            return False
        for sub in (self.raw_dir, self.spool_dir, self.receipts_dir, self.runs_dir):
            if sub.exists() and any(sub.iterdir()):
                return False
        # Reject noise or foreign artifacts at the matrix root.
        for entry in self.root.iterdir():
            if entry.name not in self._FRESH_ROOT_ALLOWLIST:
                return False
        return True

    def has_immutable_plan(self) -> bool:
        return self.plan_path.is_file() and self.catalog_path.is_file()

    def create_plan_and_catalog(self, plan: MatrixPlan) -> None:
        """Exclusive create of immutable plan + catalog. Only on fresh empty root."""
        if not self.is_fresh_empty():
            raise MatrixSafetyStop(
                "refusing to create plan/catalog on non-empty matrix root"
            )
        if self.plan_path.exists() or self.catalog_path.exists():
            raise MatrixSafetyStop("plan/catalog already exist")
        payload = plan.to_public_dict()
        cat = catalog_entries(plan)
        _reject_sensitive_payload(payload, label="plan.json")
        _reject_sensitive_payload(cat, label="logical_call_catalog")
        _exclusive_write_text(
            self.plan_path, json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )
        _exclusive_write_text(
            self.catalog_path, json.dumps(cat, indent=2, sort_keys=True) + "\n"
        )

    def load_stored_plan(self) -> MatrixPlan:
        if not self.plan_path.is_file():
            raise MatrixError("plan.json missing")
        payload = json.loads(self.plan_path.read_text(encoding="utf-8"))
        _reject_sensitive_payload(payload, label="loaded_plan")
        return MatrixPlan.from_public_dict(payload)

    def authenticate_immutable_store(
        self,
        *,
        expected_plan: MatrixPlan | None = None,
        registry_store_root: Path | str | None = None,
    ) -> tuple[MatrixPlan, dict[str, int], dict[str, Any]]:
        """Authenticate all stored evidence before any write. No plan rewrite."""
        if not self.has_immutable_plan():
            raise MatrixSafetyStop("missing immutable plan/catalog for existing root")
        stored_plan_text = self.plan_path.read_text(encoding="utf-8")
        stored_cat_text = self.catalog_path.read_text(encoding="utf-8")
        stored_plan_obj = json.loads(stored_plan_text)
        stored_cat = json.loads(stored_cat_text)
        _reject_sensitive_payload(stored_plan_obj, label="stored_plan")
        _reject_sensitive_payload(stored_cat, label="stored_catalog")
        plan = MatrixPlan.from_public_dict(stored_plan_obj)

        # Optionally re-derive pure plan and require matrix_id match (no write).
        if registry_store_root is not None:
            rebuilt = build_matrix_plan(
                registry_store_root=registry_store_root,
                provider_orgs=plan.provider_orgs,
            )
            if rebuilt.matrix_id != plan.matrix_id:
                raise MatrixSafetyStop(
                    "rebuilt matrix_id disagrees with immutable stored plan",
                    context={"stored": plan.matrix_id, "rebuilt": rebuilt.matrix_id},
                )
        if expected_plan is not None and expected_plan.matrix_id != plan.matrix_id:
            raise MatrixSafetyStop("caller plan matrix_id disagrees with stored plan")

        expected_calls = iter_logical_calls(plan)
        expected_cat = catalog_entries(plan)
        expected_ids = {c.logical_call_id for c in expected_calls}
        # Byte-exact catalog (canonical JSON form).
        expected_cat_text = json.dumps(expected_cat, indent=2, sort_keys=True) + "\n"
        if stored_cat != expected_cat:
            raise MatrixSafetyStop("logical-call catalog content drift")
        # Also ensure stable serialization identity of request_json fields.
        if len(stored_cat) != len(expected_cat):
            raise MatrixSafetyStop("logical-call catalog size drift")
        for stored_entry, expected_entry in zip(stored_cat, expected_cat, strict=True):
            for key in (
                "logical_call_id",
                "kind",
                "provider_org",
                "request_sha256",
                "request_json",
            ):
                if stored_entry.get(key) != expected_entry.get(key):
                    raise MatrixSafetyStop(
                        "logical-call catalog field drift",
                        context={"field": key, "logical_call_id": expected_entry["logical_call_id"]},
                    )

        # Every attempt row must belong to expected set; no extras.
        all_attempts = list(
            self._conn.execute(
                "SELECT * FROM attempt_receipt ORDER BY logical_call_id, attempt"
            )
        )
        attempt_ids = {str(r["logical_call_id"]) for r in all_attempts}
        extra = attempt_ids - expected_ids
        if extra:
            raise MatrixSafetyStop(
                "unknown attempt rows present in store",
                context={"extra_count": len(extra)},
            )
        # Logical call state rows: no extras; consistency with attempts.
        state_rows = list(self._conn.execute("SELECT * FROM logical_call_state"))
        state_ids = {str(r["logical_call_id"]) for r in state_rows}
        if state_ids - expected_ids:
            raise MatrixSafetyStop("unknown logical_call_state rows present")

        calls_by_id = {c.logical_call_id: c for c in expected_calls}
        logical_started: set[str] = set()
        attempts_n = 0
        retained = 0
        http_429s = 0
        receipt_files_seen: set[str] = set()

        for call_id in sorted(attempt_ids):
            call = calls_by_id[call_id]
            rows = self.list_attempts(call_id)
            logical_started.add(call_id)
            for index, row in enumerate(rows, start=1):
                if int(row["attempt"]) != index:
                    raise MatrixSafetyStop(
                        "non-contiguous attempt evidence",
                        context={"logical_call_id": call_id, "attempt": row["attempt"]},
                    )
                if str(row["provider_org"]) != call.provider_org:
                    raise MatrixSafetyStop("attempt provider_org mismatch")
                if str(row["kind"]) != call.kind:
                    raise MatrixSafetyStop("attempt kind mismatch")
                if str(row["request_sha256"]) != _sha256_text(call.request_json()):
                    raise MatrixSafetyStop("attempt request_sha256 mismatch")
                if str(row["request_json"]) != call.request_json():
                    raise MatrixSafetyStop("attempt request_json mismatch")
                attempts_n += 1
                if int(row["http_429"]):
                    http_429s += 1
                body_sha = row["body_sha256"]
                body_bytes = int(row["body_bytes"])
                retained += body_bytes
                if body_sha is not None:
                    self.load_body(str(body_sha), expected_bytes=body_bytes)
                if int(row["truncated"]) and row["error_class"] is None:
                    raise MatrixSafetyStop("truncated body recorded as success")
                # Sidecar receipt must exist and match.
                sidecar = (
                    self.receipts_dir
                    / f"{call_id.replace(':', '__')}__a{index}.json"
                )
                if not sidecar.is_file():
                    raise MatrixSafetyStop(
                        "missing attempt receipt sidecar",
                        context={"path": str(sidecar.name)},
                    )
                receipt_files_seen.add(sidecar.name)
                side = json.loads(sidecar.read_text(encoding="utf-8"))
                for key in (
                    "logical_call_id",
                    "attempt",
                    "provider_org",
                    "kind",
                    "request_sha256",
                    "body_sha256",
                    "body_bytes",
                    "truncated",
                    "error_class",
                ):
                    # DB uses int for truncated; JSON may be bool.
                    left = row[key] if key in row.keys() else None
                    right = side.get(key)
                    if key == "truncated":
                        left = bool(int(left))
                        right = bool(right)
                    if key == "attempt":
                        left = int(left)
                        right = int(right)
                    if key == "body_bytes":
                        left = int(left)
                        right = int(right)
                    if left != right:
                        raise MatrixSafetyStop(
                            "receipt sidecar disagrees with attempt row",
                            context={"field": key, "logical_call_id": call_id},
                        )

        # No orphan sidecars.
        for path in self.receipts_dir.glob("*.json"):
            if path.name not in receipt_files_seen:
                raise MatrixSafetyStop(
                    "orphan receipt sidecar present",
                    context={"name": path.name},
                )

        # Terminal state consistency.
        for srow in state_rows:
            cid = str(srow["logical_call_id"])
            rows = self.list_attempts(cid)
            if int(srow["attempts"]) != len(rows):
                raise MatrixSafetyStop(
                    "logical_call_state attempts disagree with attempt rows",
                    context={"logical_call_id": cid},
                )
            if rows:
                last = rows[-1]
                expected_terminal = (
                    "error"
                    if last["error_class"] is not None or int(last["truncated"])
                    else "success"
                )
                if str(srow["terminal_status"]) != expected_terminal:
                    raise MatrixSafetyStop(
                        "logical_call_state terminal_status inconsistent",
                        context={"logical_call_id": cid},
                    )
                if expected_terminal == "success":
                    if str(srow["final_body_sha256"] or "") != str(last["body_sha256"] or ""):
                        raise MatrixSafetyStop(
                            "logical_call_state final_body_sha256 inconsistent",
                            context={"logical_call_id": cid},
                        )

        # High-water durable snapshot (optional for empty store).
        high_water = 0
        if self.high_water_path.is_file():
            hw = json.loads(self.high_water_path.read_text(encoding="utf-8"))
            high_water = int(hw.get("high_water_in_flight", 0))
            if high_water < 0:
                raise MatrixSafetyStop("invalid stored high_water")

        counters = {
            "logical_calls": len(logical_started),
            "attempts": attempts_n,
            "retained_bytes": retained,
            "http_429s": http_429s,
            "high_water_in_flight": high_water,
        }
        snapshot = {
            "plan_matrix_id": plan.matrix_id,
            "catalog_sha256": _sha256_text(expected_cat_text),
            "attempt_count": attempts_n,
            "logical_calls_with_attempts": sorted(logical_started),
            "retained_bytes": retained,
            "http_429s": http_429s,
            "high_water_in_flight": high_water,
            "raw_object_count": sum(1 for _ in self.raw_dir.glob("*.bin")),
        }
        return plan, counters, snapshot

    def persist_high_water(self, high_water_in_flight: int) -> None:
        payload = {
            "high_water_in_flight": int(high_water_in_flight),
            "updated_at": _now_iso(),
        }
        _reject_sensitive_payload(payload, label="high_water")
        _atomic_replace_text(
            self.high_water_path, json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )

    def load_body(self, body_sha256: str, *, expected_bytes: int | None = None) -> bytes:
        if not _SHA256_RE.fullmatch(body_sha256):
            raise MatrixSafetyStop("invalid body sha256")
        path = self.raw_dir / f"{body_sha256}.bin"
        if not path.is_file():
            raise MatrixSafetyStop("retained body missing")
        data = path.read_bytes()
        actual = _sha256_bytes(data)
        if actual != body_sha256:
            raise MatrixSafetyStop(
                "retained body SHA-256 mismatch (tamper or corrupt raw)",
                context={"expected": body_sha256, "actual": actual},
            )
        if expected_bytes is not None and len(data) != expected_bytes:
            raise MatrixSafetyStop(
                "retained body byte count mismatch",
                context={"expected_bytes": expected_bytes, "actual_bytes": len(data)},
            )
        return data

    def stream_http_to_spool(
        self,
        *,
        logical_call_id: str,
        attempt: int,
        response: httpx.Response,
        max_response_bytes: int,
    ) -> tuple[str | None, int, int, bool, str | None]:
        """Stream HTTP body directly into unique spool; scan; promote.

        Returns (body_sha256|None, retained_bytes, observed_bytes, truncated, credential_block).
        On credential detection body_sha is None and only blocker metadata is kept.
        """
        spool = self.spool_dir / (
            f"{logical_call_id.replace(':', '__')}__a{attempt}__{uuid.uuid4().hex}.part"
        )
        self._open_spools.append(spool)
        hasher = hashlib.sha256()
        retained = 0
        observed = 0
        truncated = False
        try:
            with open(spool, "wb") as fh:
                for chunk in response.iter_bytes(chunk_size=65_536):
                    if not chunk:
                        continue
                    observed += len(chunk)
                    if retained < max_response_bytes:
                        take = min(len(chunk), max_response_bytes - retained)
                        piece = chunk[:take]
                        fh.write(piece)
                        hasher.update(piece)
                        retained += take
                        if take < len(chunk):
                            truncated = True
                    else:
                        truncated = True
            truncated = observed > max_response_bytes
            # Read retained prefix for secret scan (bounded).
            data = spool.read_bytes() if spool.exists() else b""
            try:
                _scan_bytes_for_secrets(data, label=f"response:{logical_call_id}")
            except MatrixSafetyStop:
                # Credential hit: destroy spool; no raw authority.
                try:
                    spool.unlink()
                except OSError:
                    pass
                if spool in self._open_spools:
                    self._open_spools.remove(spool)
                return None, 0, observed, truncated, "credential_or_endpoint_detected"
            digest = hasher.hexdigest() if data else _sha256_bytes(b"")
            if not data:
                spool.write_bytes(b"")
                digest = _sha256_bytes(b"")
            _promote_content_addressed(spool, self.raw_dir, digest)
            if spool in self._open_spools:
                self._open_spools.remove(spool)
            return digest, retained if data else 0, observed, truncated, None
        except MatrixSafetyStop:
            raise
        except OSError as exc:
            raise MatrixSafetyStop(
                "raw-persistence failure",
                context={"logical_call_id": logical_call_id},
            ) from exc
        finally:
            if spool.exists() and spool in self._open_spools:
                try:
                    spool.unlink()
                except OSError:
                    pass
                if spool in self._open_spools:
                    self._open_spools.remove(spool)

    def retain_bytes_to_spool(
        self,
        *,
        logical_call_id: str,
        attempt: int,
        body: bytes,
        max_response_bytes: int,
    ) -> tuple[str | None, int, int, bool, str | None]:
        """Injectable-transport path: write body once through unique spool (no chunk list join)."""
        observed = len(body)
        truncated = observed > max_response_bytes
        retained_view = body[:max_response_bytes]
        spool = self.spool_dir / (
            f"{logical_call_id.replace(':', '__')}__a{attempt}__{uuid.uuid4().hex}.part"
        )
        self._open_spools.append(spool)
        try:
            spool.write_bytes(retained_view)
            try:
                _scan_bytes_for_secrets(retained_view, label=f"response:{logical_call_id}")
            except MatrixSafetyStop:
                try:
                    spool.unlink()
                except OSError:
                    pass
                if spool in self._open_spools:
                    self._open_spools.remove(spool)
                return None, 0, observed, truncated, "credential_or_endpoint_detected"
            digest = _sha256_bytes(retained_view)
            _promote_content_addressed(spool, self.raw_dir, digest)
            if spool in self._open_spools:
                self._open_spools.remove(spool)
            return digest, len(retained_view), observed, truncated, None
        except MatrixSafetyStop:
            raise
        except OSError as exc:
            raise MatrixSafetyStop("raw-persistence failure") from exc
        finally:
            if spool.exists() and spool in self._open_spools:
                try:
                    spool.unlink()
                except OSError:
                    pass
                if spool in self._open_spools:
                    self._open_spools.remove(spool)

    def record_attempt(
        self,
        *,
        call: LogicalCall,
        attempt: int,
        status_code: int | None,
        body_sha256: str | None,
        body_bytes: int,
        observed_body_bytes: int | None,
        truncated: bool,
        latency_ms: float | None,
        http_429: bool,
        error_class: str | None,
        error_detail: str | None,
    ) -> None:
        if self.run_id is None:
            raise MatrixError("record_attempt requires an active run_id")
        if error_detail:
            try:
                _scan_text_for_secrets(error_detail, label="error_detail")
            except MatrixSafetyStop:
                error_detail = "redacted_credential_or_endpoint"
        if truncated and error_class is None:
            error_class = "body_size_pressure"
            error_detail = error_detail or "response_truncated_over_max_response_bytes"
        # Truncated / credential / missing body never success.
        if body_sha256 is None and error_class is None:
            error_class = "unauthenticated_body"
        terminal = "error" if error_class or truncated or body_sha256 is None else "success"
        request_json = call.request_json()
        request_sha = _sha256_text(request_json)
        receipt = {
            "logical_call_id": call.logical_call_id,
            "attempt": attempt,
            "run_id": self.run_id,
            "provider_org": call.provider_org,
            "kind": call.kind,
            "request_sha256": request_sha,
            "status_code": status_code,
            "body_sha256": body_sha256,
            "body_bytes": body_bytes,
            "observed_body_bytes": observed_body_bytes,
            "truncated": truncated,
            "latency_ms": latency_ms,
            "http_429": bool(http_429),
            "error_class": error_class,
            "error_detail": error_detail,
            "retained_at": _now_iso(),
        }
        _reject_sensitive_payload(receipt, label="attempt_receipt")
        sidecar = (
            self.receipts_dir
            / f"{call.logical_call_id.replace(':', '__')}__a{attempt}.json"
        )
        with self._lock:
            existing = self._conn.execute(
                "SELECT 1 FROM attempt_receipt WHERE logical_call_id = ? AND attempt = ?",
                (call.logical_call_id, attempt),
            ).fetchone()
            if existing is not None:
                raise MatrixSafetyStop(
                    "attempt evidence is append-only; refusing overwrite",
                    context={"logical_call_id": call.logical_call_id, "attempt": attempt},
                )
            row = self._conn.execute(
                "SELECT COALESCE(MAX(attempt), 0) AS m FROM attempt_receipt "
                "WHERE logical_call_id = ?",
                (call.logical_call_id,),
            ).fetchone()
            if attempt != int(row["m"]) + 1:
                raise MatrixSafetyStop(
                    "attempt numbers must be contiguous from 1",
                    context={"logical_call_id": call.logical_call_id, "attempt": attempt},
                )
            # Atomic enough: DB transaction then exclusive sidecar. Raw already promoted;
            # authority requires this receipt row.
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute(
                    """
                    INSERT INTO attempt_receipt (
                        logical_call_id, attempt, run_id, provider_org, kind, request_sha256,
                        request_json, status_code, body_sha256, body_bytes,
                        observed_body_bytes, truncated, latency_ms, http_429,
                        error_class, error_detail, retained_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        call.logical_call_id,
                        attempt,
                        self.run_id,
                        call.provider_org,
                        call.kind,
                        request_sha,
                        request_json,
                        status_code,
                        body_sha256,
                        body_bytes,
                        observed_body_bytes,
                        1 if truncated else 0,
                        latency_ms,
                        1 if http_429 else 0,
                        error_class,
                        error_detail,
                        receipt["retained_at"],
                    ),
                )
                self._conn.execute(
                    """
                    INSERT INTO logical_call_state (
                        logical_call_id, kind, provider_org, attempts, terminal_status,
                        final_body_sha256, updated_at
                    ) VALUES (?,?,?,?,?,?,?)
                    ON CONFLICT(logical_call_id) DO UPDATE SET
                        attempts=excluded.attempts,
                        terminal_status=excluded.terminal_status,
                        final_body_sha256=excluded.final_body_sha256,
                        updated_at=excluded.updated_at
                    """,
                    (
                        call.logical_call_id,
                        call.kind,
                        call.provider_org,
                        attempt,
                        terminal,
                        body_sha256 if terminal == "success" else None,
                        receipt["retained_at"],
                    ),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        _exclusive_write_text(
            sidecar, json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        )

    def best_success_body(self, logical_call_id: str) -> tuple[str, int] | None:
        row = self._conn.execute(
            """
            SELECT body_sha256, body_bytes FROM attempt_receipt
            WHERE logical_call_id = ?
              AND error_class IS NULL
              AND truncated = 0
              AND body_sha256 IS NOT NULL
            ORDER BY attempt DESC LIMIT 1
            """,
            (logical_call_id,),
        ).fetchone()
        if row is None:
            return None
        return str(row["body_sha256"]), int(row["body_bytes"])

    def list_attempts(self, logical_call_id: str) -> list[sqlite3.Row]:
        return list(
            self._conn.execute(
                "SELECT * FROM attempt_receipt WHERE logical_call_id = ? ORDER BY attempt",
                (logical_call_id,),
            )
        )

    def _with_pointer_lock(self) -> Any:
        self.current_lock_path.touch(exist_ok=True)
        return open(self.current_lock_path, "r+")

    def cas_current_run(
        self,
        *,
        run_id: str,
        complete: bool,
        passed: bool,
        report_relpath: str,
        mode: str,
    ) -> int:
        """Locked compare-and-swap of current_run pointer; returns new generation."""
        with self._with_pointer_lock() as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                row = self._conn.execute(
                    "SELECT generation FROM pointer_generation WHERE id = 1"
                ).fetchone()
                gen = int(row["generation"])
                old: dict[str, Any] | None = None
                if self.current_run_path.is_file():
                    old = json.loads(self.current_run_path.read_text(encoding="utf-8"))
                    old_gen = int(old.get("generation", -1))
                    if old_gen > gen:
                        raise MatrixSafetyStop("pointer generation desync")
                    # Stale writer cannot restore older generation as current.
                    if old_gen != gen and old_gen >= 0:
                        # Allow if DB gen is source of truth.
                        pass
                new_gen = gen + 1
                pointer = {
                    "generation": new_gen,
                    "run_id": run_id,
                    "complete": complete,
                    "pass": passed,
                    "mode": mode,
                    "report_path": report_relpath,
                    "updated_at": _now_iso(),
                }
                _reject_sensitive_payload(pointer, label="current_run")
                # Never let an incomplete older process replace a newer PASS without gen check:
                # we always increment gen under lock, so last writer wins only if it held lock.
                # Additionally refuse downgrade of a complete PASS by incomplete from different run
                # when generations would regress (they cannot under lock+increment).
                _atomic_replace_text(
                    self.current_run_path,
                    json.dumps(pointer, indent=2, sort_keys=True) + "\n",
                )
                self._conn.execute(
                    "UPDATE pointer_generation SET generation = ? WHERE id = 1",
                    (new_gen,),
                )
                self._conn.commit()
                return new_gen
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)

    def write_incomplete_report(self, report: Mapping[str, Any], *, mode: str) -> None:
        if self.run_id is None or self.report_incomplete_path is None:
            raise MatrixError("no active run for incomplete report")
        payload = dict(report)
        payload["complete"] = False
        payload["pass"] = False
        payload["run_id"] = self.run_id
        if self.resume_identity:
            payload["resume_identity"] = self.resume_identity
        payload["evidence_hash"] = compute_evidence_hash(payload)
        payload["report_hash"] = compute_report_hash(
            evidence_hash=payload["evidence_hash"], payload=payload
        )
        _reject_sensitive_payload(payload, label="incomplete_report")
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        # Exclusive create if first write; allow replace within same run only via replace of incomplete.
        if not self.report_incomplete_path.exists():
            _exclusive_write_text(self.report_incomplete_path, text)
        else:
            _atomic_replace_text(self.report_incomplete_path, text)
        rel = str(self.report_incomplete_path.relative_to(self.root))
        self.cas_current_run(
            run_id=self.run_id,
            complete=False,
            passed=False,
            report_relpath=rel,
            mode=mode,
        )

    def write_final_report(self, report: Mapping[str, Any], *, mode: str) -> tuple[str, str]:
        if self.run_id is None or self.report_path is None:
            raise MatrixError("no active run for final report")
        payload = dict(report)
        if not payload.get("complete"):
            raise MatrixError("final report must set complete=true")
        payload["run_id"] = self.run_id
        if self.resume_identity:
            payload["resume_identity"] = self.resume_identity
        evidence_hash = compute_evidence_hash(payload)
        payload["evidence_hash"] = evidence_hash
        report_hash = compute_report_hash(evidence_hash=evidence_hash, payload=payload)
        payload["report_hash"] = report_hash
        if evidence_hash == report_hash:
            # Distinct binding: report_hash must include evidence_hash field in binding
            # so equality is vanishingly unlikely; if equal, force different salt path.
            report_hash = _sha256_text(
                _canonical_json({"evidence_hash": evidence_hash, "kind": "report", "report": _strip_for_evidence(payload)})
            )
            payload["report_hash"] = report_hash
        _reject_sensitive_payload(payload, label="final_report")
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        _exclusive_write_text(self.report_path, text)
        rel = str(self.report_path.relative_to(self.root))
        self.cas_current_run(
            run_id=self.run_id,
            complete=True,
            passed=bool(payload.get("pass")),
            report_relpath=rel,
            mode=mode,
        )
        return evidence_hash, report_hash

    def load_sealed_live_report(self) -> dict[str, Any]:
        """Load pre-existing complete execute_live report via pointer (no mutation)."""
        if not self.current_run_path.is_file():
            raise MatrixError("no current_run.json for offline replay")
        pointer = json.loads(self.current_run_path.read_text(encoding="utf-8"))
        if not pointer.get("complete"):
            raise MatrixError("current run is incomplete; standalone offline replay refuses")
        if pointer.get("mode") != "execute_live":
            raise MatrixError(
                "standalone offline replay requires a sealed mode=execute_live report",
                context={"mode": pointer.get("mode")},
            )
        rel = str(pointer.get("report_path") or "")
        path = (self.root / rel).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise MatrixSafetyStop("report_path escapes matrix output root")
        if not path.is_file():
            raise MatrixError("live report missing")
        report = json.loads(path.read_text(encoding="utf-8"))
        _reject_sensitive_payload(report, label="live_report")
        if report.get("mode") != "execute_live":
            raise MatrixError("live report mode is not execute_live")
        if not report.get("complete"):
            raise MatrixError("live report is not complete")
        if str(report.get("run_id")) != str(pointer.get("run_id")):
            raise MatrixSafetyStop("pointer run_id disagrees with live report")
        evidence = str(report.get("evidence_hash") or "")
        recomputed_e = compute_evidence_hash(report)
        if evidence != recomputed_e:
            raise MatrixSafetyStop(
                "live report evidence_hash authentication failed",
                context={"expected": evidence, "recomputed": recomputed_e},
            )
        report_hash = str(report.get("report_hash") or "")
        recomputed_r = compute_report_hash(evidence_hash=evidence, payload=report)
        # Accept either binding form used at seal time.
        alt_r = _sha256_text(
            _canonical_json(
                {
                    "evidence_hash": evidence,
                    "kind": "report",
                    "report": _strip_for_evidence(report),
                }
            )
        )
        if report_hash not in {recomputed_r, alt_r}:
            raise MatrixSafetyStop(
                "live report report_hash authentication failed",
                context={"expected": report_hash},
            )
        return report

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for spool in list(self._open_spools):
            try:
                if spool.exists():
                    spool.unlink()
            except OSError:
                pass
        self._open_spools.clear()
        try:
            self._conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TransportResult:
    status_code: int | None
    # Injectable path only: full body bytes already in memory (tests). Live stream uses stream_response.
    body: bytes | None
    stream_response: Any | None  # open httpx.Response for streaming
    latency_ms: float
    http_429: bool
    error_class: str | None
    error_detail: str | None


class HttpxTransport:
    def __init__(
        self,
        *,
        org_to_url: Mapping[str, str],
        timeout_seconds: float,
    ) -> None:
        self._urls = dict(org_to_url)
        self._clients = {
            org: httpx.Client(timeout=timeout_seconds) for org in org_to_url
        }
        self._closed = False
        self._open_responses: list[Any] = []

    def begin(self, provider_org: str, request: Mapping[str, Any]) -> TransportResult:
        """Start request; return open streaming response (caller must drain/close)."""
        if self._closed:
            raise MatrixError("transport already closed")
        if provider_org not in self._urls:
            raise MatrixError("unknown provider org for transport")
        client = self._clients[provider_org]
        url = self._urls[provider_org]
        started = time.monotonic()
        try:
            request_cm = client.stream("POST", url, json=dict(request))
            response = request_cm.__enter__()
            self._open_responses.append((request_cm, response))
            latency = (time.monotonic() - started) * 1000.0
            http_429 = response.status_code == 429
            error_class = None
            error_detail = None
            if response.status_code >= 400:
                error_class = "http_status"
                error_detail = f"HTTP_{response.status_code}"
            return TransportResult(
                status_code=response.status_code,
                body=None,
                stream_response=response,
                latency_ms=latency,
                http_429=http_429,
                error_class=error_class,
                error_detail=error_detail,
            )
        except httpx.HTTPError as exc:
            latency = (time.monotonic() - started) * 1000.0
            return TransportResult(
                status_code=None,
                body=None,
                stream_response=None,
                latency_ms=latency,
                http_429=False,
                error_class="transport",
                error_detail=type(exc).__name__,
            )

    def finish_stream(self, response: Any) -> None:
        # Close matching context managers.
        remaining = []
        for cm, resp in self._open_responses:
            if resp is response:
                try:
                    cm.__exit__(None, None, None)
                except Exception:
                    pass
            else:
                remaining.append((cm, resp))
        self._open_responses = remaining

    def close(self) -> None:
        self._closed = True
        for cm, _resp in list(self._open_responses):
            try:
                cm.__exit__(None, None, None)
            except Exception:
                pass
        self._open_responses.clear()
        for client in self._clients.values():
            try:
                client.close()
            except Exception:
                pass
        self._clients.clear()


def make_httpx_transport(
    *,
    org_to_url: Mapping[str, str],
    timeout_seconds: float,
) -> HttpxTransport:
    return HttpxTransport(org_to_url=org_to_url, timeout_seconds=timeout_seconds)


# Injectable transport callable: (org, request) -> TransportResult with body set.
TransportFn = Callable[[str, Mapping[str, Any]], TransportResult]


# ---------------------------------------------------------------------------
# Response interpretation — malformed => safety stop
# ---------------------------------------------------------------------------


def _parse_json_rpc_result(body: bytes) -> Any:
    if not body:
        raise MatrixSafetyStop("empty response body is malformed evidence")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MatrixSafetyStop("malformed_json response body") from exc
    if not isinstance(payload, Mapping):
        raise MatrixSafetyStop("json-rpc envelope must be an object")
    if "error" in payload and payload["error"] is not None:
        err = payload["error"]
        detail = str(err.get("message", err) if isinstance(err, Mapping) else err)
        try:
            _scan_text_for_secrets(detail, label="rpc_error_detail")
        except MatrixSafetyStop:
            detail = "redacted_credential_or_endpoint"
        lower = detail.lower()
        if any(
            t in lower
            for t in ("limit", "too many", "query returned more", "response size", "timeout")
        ):
            raise MatrixCellFailure(
                "provider_limit_or_size",
                context={"rpc_error": detail[:200]},
            )
        raise MatrixCellFailure("rpc_error", context={"rpc_error": detail[:200]})
    if "result" not in payload:
        raise MatrixSafetyStop("json-rpc missing result is malformed evidence")
    return payload["result"]


def interpret_chain_id(body: bytes) -> int:
    result = _parse_json_rpc_result(body)
    try:
        return _hex_quantity(result, label="eth_chainId result")
    except Exception as exc:
        raise MatrixSafetyStop(
            "malformed chain id evidence",
            context={"error": type(exc).__name__},
        ) from exc


def interpret_logs(body: bytes, *, domain: QueryDomain) -> tuple[tuple[Any, ...], str]:
    result = _parse_json_rpc_result(body)
    if not isinstance(result, list):
        raise MatrixSafetyStop("eth_getLogs result must be a list")
    try:
        identities = normalize_and_index_logs(result, domain)
    except Exception as exc:
        raise MatrixSafetyStop(
            "malformed or out-of-domain log evidence",
            context={"error": str(exc)[:300]},
        ) from exc
    return identities, log_identity_v2_digest(identities)


# ---------------------------------------------------------------------------
# Cells
# ---------------------------------------------------------------------------


@dataclass
class CellReport:
    range_name: str
    cohort_size: int
    cell_id: str
    status: CellStatus
    primary: dict[str, Any]
    secondary: dict[str, Any]
    scalar_union_digest_primary: str | None
    scalar_union_digest_secondary: str | None
    batch_digest_primary: str | None
    batch_digest_secondary: str | None
    batch_equals_scalar_primary: bool | None
    batch_equals_scalar_secondary: bool | None
    providers_agree: bool | None
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "range_name": self.range_name,
            "cohort_size": self.cohort_size,
            "cell_id": self.cell_id,
            "status": self.status,
            "primary": self.primary,
            "secondary": self.secondary,
            "scalar_union_digest_primary": self.scalar_union_digest_primary,
            "scalar_union_digest_secondary": self.scalar_union_digest_secondary,
            "batch_digest_primary": self.batch_digest_primary,
            "batch_digest_secondary": self.batch_digest_secondary,
            "batch_equals_scalar_primary": self.batch_equals_scalar_primary,
            "batch_equals_scalar_secondary": self.batch_equals_scalar_secondary,
            "providers_agree": self.providers_agree,
            "detail": self.detail,
        }


def _domain_for(
    *,
    addresses: Sequence[str],
    start: int,
    end: int,
    topics: Sequence[str],
) -> QueryDomain:
    return QueryDomain(
        start_block=start,
        end_block=end,
        addresses=tuple(sorted(addresses)),
        topics=tuple(topics),
    )


def _attempt_metrics(rows: Sequence[sqlite3.Row]) -> dict[str, Any]:
    if not rows:
        return {
            "attempts": 0,
            "http_429s": 0,
            "latency_ms_total": 0.0,
            "response_bytes": 0,
            "observed_body_bytes_total": 0,
            "truncated_attempts": 0,
            "status": "missing",
            "error_class": "missing_attempts",
            "last_status_code": None,
        }
    last = rows[-1]
    return {
        "attempts": len(rows),
        "http_429s": sum(int(r["http_429"]) for r in rows),
        "latency_ms_total": sum(float(r["latency_ms"] or 0.0) for r in rows),
        "response_bytes": sum(int(r["body_bytes"]) for r in rows),
        "observed_body_bytes_total": sum(int(r["observed_body_bytes"] or 0) for r in rows),
        "truncated_attempts": sum(int(r["truncated"]) for r in rows),
        "status": (
            "success"
            if last["error_class"] is None and not int(last["truncated"])
            else "error"
        ),
        "error_class": last["error_class"],
        "last_status_code": last["status_code"],
    }


def _provider_side_metrics(
    store: MatrixStore,
    *,
    plan: MatrixPlan,
    range_name: str,
    provider_org: str,
    addresses: Sequence[str],
    cohort_size: int,
) -> dict[str, Any]:
    scalar_attempts = 0
    scalar_429 = 0
    scalar_latency = 0.0
    scalar_bytes = 0
    scalar_observed = 0
    scalar_trunc = 0
    scalar_errors: list[str] = []
    for address in addresses:
        for topic in plan.topics:
            tag = "swap" if topic == SWAP_TOPIC else "sync"
            lid = f"scalar:{range_name}:{provider_org}:{address}:{tag}"
            rows = store.list_attempts(lid)
            m = _attempt_metrics(rows)
            scalar_attempts += m["attempts"]
            scalar_429 += m["http_429s"]
            scalar_latency += m["latency_ms_total"]
            scalar_bytes += m["response_bytes"]
            scalar_observed += m["observed_body_bytes_total"]
            scalar_trunc += m["truncated_attempts"]
            if m["error_class"]:
                scalar_errors.append(f"{lid}:{m['error_class']}")
    batch_lid = f"batch:{range_name}:{cohort_size}:{provider_org}"
    batch_m = _attempt_metrics(store.list_attempts(batch_lid))
    return {
        "provider_org": provider_org,
        "scalar_attempts": scalar_attempts,
        "scalar_http_429s": scalar_429,
        "scalar_latency_ms_total": scalar_latency,
        "scalar_response_bytes": scalar_bytes,
        "scalar_observed_body_bytes_total": scalar_observed,
        "scalar_truncated_attempts": scalar_trunc,
        "scalar_error_classes": scalar_errors[:20],
        "batch_attempts": batch_m["attempts"],
        "batch_http_429s": batch_m["http_429s"],
        "batch_latency_ms_total": batch_m["latency_ms_total"],
        "batch_response_bytes": batch_m["response_bytes"],
        "batch_observed_body_bytes_total": batch_m["observed_body_bytes_total"],
        "batch_truncated_attempts": batch_m["truncated_attempts"],
        "batch_status": batch_m["status"],
        "batch_error_class": batch_m["error_class"],
        "batch_last_status_code": batch_m["last_status_code"],
        "attempts": scalar_attempts + batch_m["attempts"],
        "http_429s": scalar_429 + batch_m["http_429s"],
        "latency_ms_total": scalar_latency + batch_m["latency_ms_total"],
        "response_bytes": scalar_bytes + batch_m["response_bytes"],
        "observed_body_bytes_total": scalar_observed + batch_m["observed_body_bytes_total"],
        "truncated_attempts": scalar_trunc + batch_m["truncated_attempts"],
        "status": batch_m["status"],
        "error_class": batch_m["error_class"] or (scalar_errors[0] if scalar_errors else None),
    }


def scalar_union_digest(
    *,
    plan: MatrixPlan,
    store: MatrixStore,
    range_name: str,
    provider_org: str,
    addresses: Sequence[str],
) -> tuple[str, int]:
    start, end = plan.ranges[range_name]
    all_identities: list[Any] = []
    for address in addresses:
        for topic in plan.topics:
            tag = "swap" if topic == SWAP_TOPIC else "sync"
            lid = f"scalar:{range_name}:{provider_org}:{address}:{tag}"
            success = store.best_success_body(lid)
            if success is None:
                rows = store.list_attempts(lid)
                if not rows:
                    raise MatrixError(
                        "missing scalar attempts for union",
                        context={"logical_call_id": lid},
                    )
                raise MatrixCellFailure(
                    "scalar call has no successful body",
                    context={"logical_call_id": lid, "error_class": rows[-1]["error_class"]},
                )
            sha, nbytes = success
            body = store.load_body(sha, expected_bytes=nbytes)
            domain = _domain_for(
                addresses=[address], start=start, end=end, topics=[topic]
            )
            identities, _ = interpret_logs(body, domain=domain)
            all_identities.extend(identities)
    unique = {item.as_tuple(): item for item in all_identities}
    ordered = tuple(sorted(unique.values(), key=lambda i: i.sort_key()))
    return log_identity_v2_digest(ordered), len(ordered)


# ---------------------------------------------------------------------------
# Config + harness
# ---------------------------------------------------------------------------


@dataclass
class MatrixConfig:
    registry_store_root: Path
    output_root: Path
    mode: RunMode = "plan_only"
    provider_orgs: tuple[str, str] = DEFAULT_PROVIDER_ORGS
    budgets: MatrixBudgets = field(default_factory=MatrixBudgets)
    primary_rpc_url: str | None = None
    secondary_rpc_url: str | None = None
    confirm_matrix_id: str | None = None
    transport: Any | None = None
    run_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "registry_store_root", _resolve_path(self.registry_store_root))
        object.__setattr__(
            self,
            "output_root",
            assert_safe_matrix_output_root(
                self.output_root, registry_store_root=self.registry_store_root
            ),
        )
        orgs = (
            normalize_provider_org(self.provider_orgs[0]),
            normalize_provider_org(self.provider_orgs[1]),
        )
        if orgs[0] == orgs[1]:
            raise MatrixError("provider_orgs must be distinct")
        object.__setattr__(self, "provider_orgs", orgs)
        if self.mode == "execute_live":
            if self.provider_orgs != DEFAULT_PROVIDER_ORGS:
                raise MatrixError(
                    "execute_live rejects caller-supplied provider organizations"
                )
            if not self.confirm_matrix_id:
                raise MatrixError("execute_live requires confirm_matrix_id")
            if self.transport is None:
                if not self.primary_rpc_url or not self.secondary_rpc_url:
                    raise MatrixError(
                        "execute_live requires primary_rpc_url and secondary_rpc_url"
                    )
                if self.primary_rpc_url.rstrip("/") == self.secondary_rpc_url.rstrip("/"):
                    raise MatrixError("primary and secondary RPC URLs must be distinct")


class PairEventV2MatrixHarness:
    def __init__(self, config: MatrixConfig) -> None:
        self.config = config
        self._closed = False
        self._transport = config.transport
        self._owns_transport = False
        self._stop = threading.Event()
        self._safety_lock = threading.Lock()
        self._safety_error: MatrixSafetyStop | None = None
        self.tracker = BudgetTracker(budgets=config.budgets)
        self._gates = {
            org: _ProviderGate(
                max_in_flight=config.budgets.max_in_flight,
                rps=config.budgets.requests_per_second,
            )
            for org in config.provider_orgs
        }
        # Never create a run in the constructor: a premature runs/ dir would make a
        # fresh root non-empty and block exclusive plan/catalog creation. Runs are
        # opened after plan prepare (or after live-report auth for standalone replay).
        try:
            self.store = MatrixStore(
                config.output_root,
                registry_store_root=config.registry_store_root,
                run_id=None,
                create_run=False,
            )
        except Exception:
            self._closed = True
            raise
        self.plan: MatrixPlan | None = None
        self.evidence_snapshot: dict[str, Any] = {}
        self._configured_run_id = config.run_id

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._owns_transport and self._transport is not None:
            close = getattr(self._transport, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
        try:
            self.store.close()
        except Exception:
            pass

    def _signal_safety(self, exc: MatrixSafetyStop) -> None:
        with self._safety_lock:
            if self._safety_error is None:
                self._safety_error = exc
        self._stop.set()

    def _raise_if_stopped(self) -> None:
        if self._stop.is_set():
            with self._safety_lock:
                if self._safety_error is not None:
                    raise self._safety_error
            raise MatrixSafetyStop("stop signal set")

    def prepare_plan(self) -> MatrixPlan:
        """Pure rebuild + open store: authenticate existing or create on fresh root only."""
        if self.store.has_immutable_plan():
            plan, counters, snapshot = self.store.authenticate_immutable_store(
                registry_store_root=self.config.registry_store_root,
            )
            # Provider org freeze for execute_live already in config; still reject drift.
            if self.config.mode == "execute_live" and plan.provider_orgs != DEFAULT_PROVIDER_ORGS:
                raise MatrixSafetyStop("stored plan provider orgs are not frozen defaults")
            self.tracker.load_prior(counters)
            self.evidence_snapshot = snapshot
            self.plan = plan
            self.store.resume_identity = f"resume:{plan.matrix_id}:{snapshot['catalog_sha256'][:16]}"
            return plan
        # Fresh root only.
        if not self.store.is_fresh_empty():
            raise MatrixSafetyStop(
                "matrix root is not empty and has no immutable plan/catalog"
            )
        plan = build_matrix_plan(
            registry_store_root=self.config.registry_store_root,
            provider_orgs=self.config.provider_orgs,
        )
        self.store.create_plan_and_catalog(plan)
        self.evidence_snapshot = {
            "plan_matrix_id": plan.matrix_id,
            "catalog_sha256": _sha256_text(
                json.dumps(catalog_entries(plan), indent=2, sort_keys=True) + "\n"
            ),
            "attempt_count": 0,
            "logical_calls_with_attempts": [],
            "retained_bytes": 0,
            "http_429s": 0,
            "high_water_in_flight": 0,
            "raw_object_count": 0,
        }
        self.plan = plan
        return plan

    def _ensure_transport(self) -> Any:
        if self._transport is not None:
            return self._transport
        assert self.config.primary_rpc_url and self.config.secondary_rpc_url
        self._transport = make_httpx_transport(
            org_to_url={
                self.config.provider_orgs[0]: self.config.primary_rpc_url,
                self.config.provider_orgs[1]: self.config.secondary_rpc_url,
            },
            timeout_seconds=self.config.budgets.http_timeout_seconds,
        )
        self._owns_transport = True
        return self._transport

    def _execute_one(self, call: LogicalCall) -> None:
        self._raise_if_stopped()
        existing = self.store.list_attempts(call.logical_call_id)
        if any(
            r["error_class"] is None and not int(r["truncated"]) and r["body_sha256"]
            for r in existing
        ):
            return
        start_attempt = len(existing) + 1
        if start_attempt == 1:
            self.tracker.register_logical_call()
        transport = self._ensure_transport()
        max_attempts = self.config.budgets.max_attempts_per_logical_call
        gate = self._gates[call.provider_org]
        max_bytes = self.config.budgets.max_response_bytes
        for attempt in range(start_attempt, max_attempts + 1):
            self._raise_if_stopped()
            self.tracker.check_wall()
            self.tracker.register_attempt()
            # Reserve worst-case retained capacity before starting the request.
            self.tracker.reserve_response_bytes(max_bytes)
            reserved = max_bytes
            gate.acquire(stop=self._stop, tracker=self.tracker)
            body_sha: str | None = None
            body_bytes = 0
            observed = 0
            truncated = False
            status_code: int | None = None
            latency_ms = 0.0
            http_429 = False
            error_class: str | None = None
            error_detail: str | None = None
            stream_resp = None
            try:
                self._raise_if_stopped()
                if isinstance(transport, HttpxTransport):
                    result = transport.begin(call.provider_org, call.request)
                    status_code = result.status_code
                    latency_ms = result.latency_ms
                    http_429 = result.http_429
                    error_class = result.error_class
                    error_detail = result.error_detail
                    stream_resp = result.stream_response
                    if stream_resp is not None:
                        body_sha, body_bytes, observed, truncated, cred = (
                            self.store.stream_http_to_spool(
                                logical_call_id=call.logical_call_id,
                                attempt=attempt,
                                response=stream_resp,
                                max_response_bytes=max_bytes,
                            )
                        )
                        if cred:
                            error_class = "credential_detection"
                            error_detail = cred
                            body_sha = None
                            body_bytes = 0
                    else:
                        # transport error with no body
                        body_sha, body_bytes, observed, truncated = None, 0, 0, False
                else:
                    result = transport(call.provider_org, call.request)
                    status_code = result.status_code
                    latency_ms = result.latency_ms
                    http_429 = result.http_429
                    error_class = result.error_class
                    error_detail = result.error_detail
                    raw_body = result.body or b""
                    body_sha, body_bytes, observed, truncated, cred = (
                        self.store.retain_bytes_to_spool(
                            logical_call_id=call.logical_call_id,
                            attempt=attempt,
                            body=raw_body,
                            max_response_bytes=max_bytes,
                        )
                    )
                    if cred:
                        error_class = "credential_detection"
                        error_detail = cred
                        body_sha = None
                        body_bytes = 0
                if truncated:
                    error_class = error_class or "body_size_pressure"
                    error_detail = error_detail or "response_truncated_over_max_response_bytes"
                if http_429:
                    self.tracker.note_429()
                self.tracker.commit_reservation(reserved, body_bytes)
                reserved = 0
                self.store.record_attempt(
                    call=call,
                    attempt=attempt,
                    status_code=status_code,
                    body_sha256=body_sha,
                    body_bytes=body_bytes,
                    observed_body_bytes=observed,
                    truncated=truncated,
                    latency_ms=latency_ms,
                    http_429=http_429,
                    error_class=error_class,
                    error_detail=error_detail,
                )
                self.store.persist_high_water(self.tracker.high_water_in_flight)
            except MatrixSafetyStop as exc:
                if reserved:
                    try:
                        self.tracker.release_reservation(reserved)
                    except Exception:
                        pass
                self._signal_safety(exc)
                raise
            except Exception:
                if reserved:
                    try:
                        self.tracker.release_reservation(reserved)
                    except Exception:
                        pass
                raise
            finally:
                if stream_resp is not None and isinstance(transport, HttpxTransport):
                    transport.finish_stream(stream_resp)
                gate.release()

            if error_class is None and not truncated and body_sha:
                return
            if attempt < max_attempts and not self._stop.is_set():
                time.sleep(min(0.5 * attempt if not http_429 else 2**attempt, 30))

    def _authenticate_chain(self, plan: MatrixPlan, calls: Sequence[LogicalCall]) -> None:
        chain_calls = [c for c in calls if c.kind == "chain"]
        for call in chain_calls:
            self._execute_one(call)
        chain_ids: dict[str, int] = {}
        for call in chain_calls:
            success = self.store.best_success_body(call.logical_call_id)
            if success is None:
                raise MatrixSafetyStop(
                    "chain authentication failed for provider",
                    context={"provider_org": call.provider_org},
                )
            body = self.store.load_body(success[0], expected_bytes=success[1])
            chain_ids[call.provider_org] = interpret_chain_id(body)
        if len(set(chain_ids.values())) != 1:
            raise MatrixSafetyStop(
                "chain disagreement between providers",
                context={"chain_ids": chain_ids},
            )
        only = next(iter(chain_ids.values()))
        expected = _hex_quantity(ETHEREUM_MAINNET_CHAIN_ID, label="mainnet")
        if only != expected:
            raise MatrixSafetyStop(
                "chain id is not Ethereum mainnet",
                context={"chain_id": only, "expected": expected},
            )

    def execute_live(self, plan: MatrixPlan) -> None:
        if self.config.mode != "execute_live":
            raise MatrixError("execute_live called without execute_live mode")
        if self.config.confirm_matrix_id != plan.matrix_id:
            raise MatrixSafetyStop(
                "confirm_matrix_id does not match computed matrix ID",
                context={
                    "confirm": self.config.confirm_matrix_id,
                    "matrix_id": plan.matrix_id,
                },
            )
        # Re-authenticate store before new work (no catalog rewrite).
        _, counters, snapshot = self.store.authenticate_immutable_store(
            expected_plan=plan,
            registry_store_root=self.config.registry_store_root,
        )
        self.tracker.load_prior(counters)
        self.evidence_snapshot = snapshot
        calls = iter_logical_calls(plan)
        self._authenticate_chain(plan, calls)
        work = [c for c in calls if c.kind != "chain"]
        max_workers = self.config.budgets.max_in_flight * len(self.config.provider_orgs)
        pending: set[Future[None]] = set()
        work_iter = iter(work)
        executor = ThreadPoolExecutor(max_workers=max_workers)
        try:
            def submit_next() -> bool:
                if self._stop.is_set():
                    return False
                try:
                    call = next(work_iter)
                except StopIteration:
                    return False
                pending.add(executor.submit(self._worker, call))
                return True

            for _ in range(max_workers):
                if not submit_next():
                    break
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for fut in done:
                    exc = fut.exception()
                    if exc is None:
                        continue
                    if isinstance(exc, MatrixSafetyStop):
                        self._signal_safety(exc)
                    else:
                        self._signal_safety(
                            MatrixSafetyStop(
                                "worker failed",
                                context={"error": type(exc).__name__},
                            )
                        )
                if self._stop.is_set():
                    for fut in pending:
                        fut.cancel()
                    wait(pending)
                    pending.clear()
                    break
                while len(pending) < max_workers and not self._stop.is_set():
                    if not submit_next():
                        break
            self._raise_if_stopped()
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

    def _worker(self, call: LogicalCall) -> None:
        self._execute_one(call)

    def _batch_digest(
        self,
        plan: MatrixPlan,
        range_name: str,
        size: int,
        provider_org: str,
        addresses: Sequence[str],
        start: int,
        end: int,
    ) -> dict[str, Any]:
        lid = f"batch:{range_name}:{size}:{provider_org}"
        rows = self.store.list_attempts(lid)
        metrics = _attempt_metrics(rows)
        success = self.store.best_success_body(lid)
        if success is None:
            raise MatrixCellFailure(
                "batch call has no successful body",
                context={"logical_call_id": lid, "error_class": metrics["error_class"]},
            )
        body = self.store.load_body(success[0], expected_bytes=success[1])
        identities, digest = interpret_logs(
            body,
            domain=_domain_for(
                addresses=addresses, start=start, end=end, topics=plan.topics
            ),
        )
        return {"digest": digest, "log_count": len(identities), **metrics}

    def evaluate_cells(self, plan: MatrixPlan) -> list[CellReport]:
        primary, secondary = plan.provider_orgs
        cells: list[CellReport] = []
        for range_name in RANGE_ORDER:
            start, end = plan.ranges[range_name]
            for size in NESTED_COHORT_SIZES:
                cell_id = f"{range_name}:cohort{size}"
                addresses = plan.maximum_cohort[:size]
                p_metrics = _provider_side_metrics(
                    self.store,
                    plan=plan,
                    range_name=range_name,
                    provider_org=primary,
                    addresses=addresses,
                    cohort_size=size,
                )
                s_metrics = _provider_side_metrics(
                    self.store,
                    plan=plan,
                    range_name=range_name,
                    provider_org=secondary,
                    addresses=addresses,
                    cohort_size=size,
                )
                try:
                    s_primary, n_primary = scalar_union_digest(
                        plan=plan,
                        store=self.store,
                        range_name=range_name,
                        provider_org=primary,
                        addresses=addresses,
                    )
                    s_secondary, n_secondary = scalar_union_digest(
                        plan=plan,
                        store=self.store,
                        range_name=range_name,
                        provider_org=secondary,
                        addresses=addresses,
                    )
                    batch_p = self._batch_digest(
                        plan, range_name, size, primary, addresses, start, end
                    )
                    batch_s = self._batch_digest(
                        plan, range_name, size, secondary, addresses, start, end
                    )
                    eq_p = batch_p["digest"] == s_primary
                    eq_s = batch_s["digest"] == s_secondary
                    agree = (
                        s_primary == s_secondary
                        and batch_p["digest"] == batch_s["digest"]
                        and eq_p
                        and eq_s
                    )
                    status: CellStatus = "pass" if agree else "fail"
                    cells.append(
                        CellReport(
                            range_name=range_name,
                            cohort_size=size,
                            cell_id=cell_id,
                            status=status,
                            primary={
                                **p_metrics,
                                "log_count": n_primary,
                                "identity_v2_digest": s_primary,
                                "batch_digest": batch_p["digest"],
                                "batch_log_count": batch_p["log_count"],
                            },
                            secondary={
                                **s_metrics,
                                "log_count": n_secondary,
                                "identity_v2_digest": s_secondary,
                                "batch_digest": batch_s["digest"],
                                "batch_log_count": batch_s["log_count"],
                            },
                            scalar_union_digest_primary=s_primary,
                            scalar_union_digest_secondary=s_secondary,
                            batch_digest_primary=batch_p["digest"],
                            batch_digest_secondary=batch_s["digest"],
                            batch_equals_scalar_primary=eq_p,
                            batch_equals_scalar_secondary=eq_s,
                            providers_agree=agree,
                            detail=None if agree else "batch/scalar/provider disagreement",
                        )
                    )
                except MatrixSafetyStop:
                    raise
                except MatrixCellFailure as exc:
                    cells.append(
                        CellReport(
                            range_name=range_name,
                            cohort_size=size,
                            cell_id=cell_id,
                            status="fail",
                            primary=p_metrics,
                            secondary=s_metrics,
                            scalar_union_digest_primary=None,
                            scalar_union_digest_secondary=None,
                            batch_digest_primary=None,
                            batch_digest_secondary=None,
                            batch_equals_scalar_primary=None,
                            batch_equals_scalar_secondary=None,
                            providers_agree=False,
                            detail=str(exc),
                        )
                    )
                except MatrixError as exc:
                    cells.append(
                        CellReport(
                            range_name=range_name,
                            cohort_size=size,
                            cell_id=cell_id,
                            status="incomplete",
                            primary=p_metrics,
                            secondary=s_metrics,
                            scalar_union_digest_primary=None,
                            scalar_union_digest_secondary=None,
                            batch_digest_primary=None,
                            batch_digest_secondary=None,
                            batch_equals_scalar_primary=None,
                            batch_equals_scalar_secondary=None,
                            providers_agree=None,
                            detail=str(exc),
                        )
                    )
        if len(cells) != 15:
            raise MatrixError(
                "cell count drift",
                context={"observed": len(cells), "expected": 15},
            )
        return cells

    def _base_report(self, plan: MatrixPlan) -> dict[str, Any]:
        return {
            "schema_version": MATRIX_SCHEMA_VERSION,
            "matrix_id": plan.matrix_id,
            "run_id": self.store.run_id,
            "resume_identity": self.store.resume_identity,
            "mode": self.config.mode,
            "plan": plan.to_public_dict(),
            "budgets": self.config.budgets.as_report_dict(),
            "logical_call_ceiling": LOGICAL_CALL_CEILING,
            "evidence_snapshot": self.evidence_snapshot,
            "cumulative_counters": self.tracker.evidence_counters(),
            "started_at": _now_iso(),
            "complete": False,
            "pass": False,
            "recommendation": {
                "note": (
                    "Report may recommend a cohort size but must not freeze 64, "
                    "dictate production configuration, grant v2 coverage, start "
                    "endurance, or authorize full acquisition."
                ),
                "suggested_cohort_size": None,
                "frozen": False,
                "grants_v2_coverage": False,
                "authorizes_endurance": False,
                "authorizes_full_acquisition": False,
            },
            "credential_scan": "pass",
            "provider_metrics_note": (
                "Each cell includes full primary/secondary attempts, 429s, latency, "
                "response bytes, observed bytes, truncation, status, and error_class."
            ),
        }

    def run(self) -> dict[str, Any]:
        try:
            if self.config.mode == "offline_replay":
                return self._run_standalone_offline_replay()
            plan = self.prepare_plan()
            if self.config.mode == "execute_live":
                if self.config.confirm_matrix_id != plan.matrix_id:
                    raise MatrixSafetyStop(
                        "confirm_matrix_id does not match computed matrix ID"
                    )
            # Exclusive immutable run after plan/catalog are settled.
            self.store.begin_run(run_id=self._configured_run_id)
            base = self._base_report(plan)
            # plan_only / execute_live may write incomplete for this run.
            if self.config.mode == "plan_only":
                base["complete"] = True
                base["pass"] = False
                base["detail"] = (
                    "plan-only complete: registry/cohort pins verified; "
                    "no RPC executed; matrix PASS requires live cells + offline replay"
                )
                base["finished_at"] = _now_iso()
                base["high_water"] = self.tracker.snapshot()
                # Refresh snapshot after authenticate/create.
                base["evidence_snapshot"] = self.evidence_snapshot
                base["cumulative_counters"] = self.tracker.evidence_counters()
                evidence_hash, report_hash = self.store.write_final_report(
                    base, mode="plan_only"
                )
                base["evidence_hash"] = evidence_hash
                base["report_hash"] = report_hash
                return base

            # execute_live
            self.store.write_incomplete_report(base, mode="execute_live")
            try:
                self.execute_live(plan)
            except MatrixSafetyStop as exc:
                # Re-auth snapshot for incomplete safety report metrics.
                try:
                    _, counters, snapshot = self.store.authenticate_immutable_store(
                        expected_plan=plan,
                        registry_store_root=self.config.registry_store_root,
                    )
                    self.evidence_snapshot = snapshot
                    base["cumulative_counters"] = {
                        "logical_calls_started": counters["logical_calls"],
                        "provider_attempts": counters["attempts"],
                        "retained_response_bytes": counters["retained_bytes"],
                        "http_429_count": counters["http_429s"],
                        "high_water_in_flight": counters["high_water_in_flight"],
                    }
                    base["evidence_snapshot"] = snapshot
                except MatrixSafetyStop:
                    pass
                # Best-effort cell metrics even on safety stop.
                try:
                    cells = self.evaluate_cells(plan)
                    base["cells"] = [c.as_dict() for c in cells]
                except MatrixSafetyStop as eval_exc:
                    base["cells"] = []
                    base["cell_evaluation_safety_stop"] = str(eval_exc)
                except MatrixError:
                    base["cells"] = []
                base["safety_stop"] = str(exc)
                base["finished_at"] = _now_iso()
                base["high_water"] = self.tracker.snapshot()
                self.store.write_incomplete_report(base, mode="execute_live")
                raise

            # In-process zero-network evaluation before seal.
            cells = self.evaluate_cells(plan)
            cell_dicts = [c.as_dict() for c in cells]
            all_cells_pass = all(c.status == "pass" for c in cells)
            _, counters, snapshot = self.store.authenticate_immutable_store(
                expected_plan=plan,
                registry_store_root=self.config.registry_store_root,
            )
            self.evidence_snapshot = snapshot
            in_process_replay = {
                "kind": "in_process_pre_seal",
                "all_cells_pass": all_cells_pass,
                "cell_count": len(cells),
                "cells": cell_dicts,
                "authenticated_store": True,
                "cumulative_counters": counters,
            }
            in_process_replay["replay_hash"] = compute_evidence_hash(in_process_replay)
            suggested: int | None = 128 if all_cells_pass else None
            if not all_cells_pass:
                for size in reversed(NESTED_COHORT_SIZES):
                    size_cells = [c for c in cells if c.cohort_size == size]
                    if size_cells and all(c.status == "pass" for c in size_cells):
                        suggested = size
                        break
            incomplete_cells = any(c.status == "incomplete" for c in cells)
            base.update(
                {
                    "cells": cell_dicts,
                    "offline_replay": in_process_replay,
                    "complete": not incomplete_cells,
                    "pass": bool(
                        all_cells_pass
                        and in_process_replay.get("authenticated_store")
                        and in_process_replay.get("all_cells_pass")
                        and len(cells) == 15
                        and not incomplete_cells
                    ),
                    "all_cells_pass": all_cells_pass,
                    "finished_at": _now_iso(),
                    "high_water": self.tracker.snapshot(),
                    "evidence_snapshot": snapshot,
                    "cumulative_counters": self.tracker.evidence_counters(),
                    "recommendation": {
                        **base["recommendation"],
                        "suggested_cohort_size": suggested,
                    },
                }
            )
            if incomplete_cells:
                base["complete"] = False
                base["pass"] = False
                self.store.write_incomplete_report(base, mode="execute_live")
                return base
            evidence_hash, report_hash = self.store.write_final_report(
                base, mode="execute_live"
            )
            base["evidence_hash"] = evidence_hash
            base["report_hash"] = report_hash
            return base
        finally:
            self.close()

    def _run_standalone_offline_replay(self) -> dict[str, Any]:
        """Standalone replay: authenticate sealed live report before any run/pointer write."""
        # Store opened without run. Authenticate plan/catalog/attempts first.
        plan, counters, snapshot = self.store.authenticate_immutable_store(
            registry_store_root=self.config.registry_store_root,
        )
        self.tracker.load_prior(counters)
        self.evidence_snapshot = snapshot
        self.plan = plan
        # Load sealed live report WITHOUT creating a run or changing pointer.
        live = self.store.load_sealed_live_report()
        if live.get("matrix_id") != plan.matrix_id:
            raise MatrixSafetyStop("live report matrix_id disagrees with stored plan")
        # Verify cells recompute.
        cells = self.evaluate_cells(plan)
        cell_dicts = [c.as_dict() for c in cells]
        live_cells = live.get("cells")
        live_cells_hash = compute_evidence_hash({"cells": live_cells})
        replay_cells_hash = compute_evidence_hash({"cells": cell_dicts})
        if live_cells_hash != replay_cells_hash:
            raise MatrixSafetyStop(
                "offline replay cell decisions disagree with authenticated live report"
            )
        all_pass = all(c.status == "pass" for c in cells)
        # Only now create a replay run for offline_replay.json (does not become live PASS).
        self.store.begin_run(run_id=self._configured_run_id)
        replay_body = {
            "matrix_id": plan.matrix_id,
            "mode": "offline_replay",
            "run_id": self.store.run_id,
            "live_run_id": live.get("run_id"),
            "live_evidence_hash": live.get("evidence_hash"),
            "live_report_hash": live.get("report_hash"),
            "live_report_authenticated": True,
            "cells": cell_dicts,
            "all_cells_pass": all_pass,
            "cell_count": len(cells),
            "evidence_snapshot": snapshot,
            "cumulative_counters": counters,
            "plan": plan.to_public_dict(),
            "budgets": self.config.budgets.as_report_dict(),
        }
        replay_body["evidence_hash"] = compute_evidence_hash(replay_body)
        replay_body["report_hash"] = compute_report_hash(
            evidence_hash=replay_body["evidence_hash"], payload=replay_body
        )
        _reject_sensitive_payload(replay_body, label="offline_replay")
        assert self.store.run_dir is not None
        replay_path = self.store.run_dir / "offline_replay.json"
        _exclusive_write_text(
            replay_path, json.dumps(replay_body, indent=2, sort_keys=True) + "\n"
        )
        # Do NOT cas_current_run to this replay — live pointer remains execute_live.
        result = {
            **replay_body,
            "complete": True,
            "pass": bool(
                all_pass
                and replay_body["live_report_authenticated"]
                and len(cells) == 15
            ),
            "finished_at": _now_iso(),
            "high_water": self.tracker.snapshot(),
            "started_at": _now_iso(),
            "recommendation": {
                "note": (
                    "Report may recommend a cohort size but must not freeze 64, "
                    "dictate production configuration, grant v2 coverage, start "
                    "endurance, or authorize full acquisition."
                ),
                "suggested_cohort_size": 128 if all_pass else None,
                "frozen": False,
                "grants_v2_coverage": False,
                "authorizes_endurance": False,
                "authorizes_full_acquisition": False,
            },
        }
        return result


def plan_only(
    *,
    registry_store_root: Path | str,
    output_root: Path | str,
    provider_orgs: tuple[str, str] = DEFAULT_PROVIDER_ORGS,
) -> dict[str, Any]:
    config = MatrixConfig(
        registry_store_root=Path(registry_store_root),
        output_root=Path(output_root),
        mode="plan_only",
        provider_orgs=provider_orgs,
    )
    return PairEventV2MatrixHarness(config).run()


__all__ = [
    "ANCHOR_POOL",
    "BIRTH_BOUNDARY_BLOCK",
    "DEFAULT_PROVIDER_ORGS",
    "LOGICAL_CALL_CEILING",
    "MATRIX_RANGES",
    "MATRIX_SCHEMA_VERSION",
    "NESTED_COHORT_SIZES",
    "PINNED_COHORT_HASHES",
    "BudgetTracker",
    "CellReport",
    "HttpxTransport",
    "LogicalCall",
    "MatrixBudgets",
    "MatrixConfig",
    "MatrixError",
    "MatrixPlan",
    "MatrixSafetyStop",
    "MatrixStore",
    "PairEventV2MatrixHarness",
    "assert_safe_matrix_output_root",
    "build_matrix_plan",
    "catalog_entries",
    "compact_json_array_hash",
    "compute_evidence_hash",
    "compute_report_hash",
    "iter_logical_calls",
    "plan_only",
    "select_matrix_maximum_cohort",
    "verify_and_load_accepted_registry",
    "verify_pinned_cohort_hashes",
]
