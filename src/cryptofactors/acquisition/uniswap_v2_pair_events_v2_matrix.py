"""DEX-003 / ADR-0015 §9.8 — isolated v2 provider-matrix harness (fresh-run).

Replacement design (Sol c9819c2 rejection): no SQLite, no resume, no current_run.
Every live attempt uses a new exclusive run directory. Incomplete runs never PASS
and are not continued; rerun from the beginning in a fresh directory.

Frozen contract retained: accepted registry, cohort pins, ranges, providers,
topics, 15 cells, 1,568 logical calls, ceilings, log identity v2, credential-free
reporting. PASS requires dual mainnet chain auth, all 15 cells PASS, and
in-process zero-network replay of the just-sealed evidence. No coverage credit.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
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
# Pinned frozen contract
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
# Streaming / retain chunk size — scanner must detect secrets across this boundary.
STREAM_CHUNK_BYTES: Final[int] = 65_536

_UNHASHED_METADATA: Final[frozenset[str]] = frozenset(
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

_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_URL_CREDS_RE = re.compile(r"://[^/\s]*:[^/\s]*@")
_QUERY_SECRET_RE = re.compile(
    r"([?&](api[_-]?key|apikey|key|token|password|secret|access_token)=)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"bearer\s+[a-z0-9._\-+/=]+", re.IGNORECASE)
_SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|authorization|password|secret|token|private[_-]?key|bearer)",
    re.IGNORECASE,
)
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_RUN_ID_RE = re.compile(r"^run_[a-f0-9]{32}$")

CallKind = Literal["chain", "scalar", "batch"]
CellStatus = Literal["pass", "fail", "incomplete"]
RunMode = Literal["plan_only", "offline_replay", "execute_live"]
TerminalKind = Literal["COMPLETE", "FAILED"]


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
    """Immediate safety stop — seal FAILED, no PASS."""


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


def _scan_text(text: str, *, label: str) -> None:
    if _URL_CREDS_RE.search(text) or _URL_RE.search(text):
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


def _scan_bytes(data: bytes, *, label: str) -> None:
    if not data:
        return
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    _scan_text(text, label=label)


def _reject_sensitive(payload: object, *, label: str) -> None:
    try:
        text = json.dumps(payload, default=str)
    except TypeError as exc:
        raise MatrixSafetyStop(
            f"credential scan could not serialize {label}",
            context={"error": type(exc).__name__},
        ) from exc
    _scan_text(text, label=label)

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
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")
        elif isinstance(node, str):
            _scan_text(node, label=f"{label}:{path}")

    walk(payload, "$")


def _resolve(path: Path | str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def _related(a: Path, b: Path) -> bool:
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


def assert_safe_matrix_output_root(
    output_root: Path | str,
    *,
    registry_store_root: Path | str | None = None,
) -> Path:
    root = _resolve(output_root)
    if root.is_file():
        raise MatrixSafetyStop("matrix output root must be a directory")
    if root.name.startswith("dex003_full.db"):
        raise MatrixSafetyStop("matrix output root must not be dex003_full.db")
    dex_full = (Path.cwd() / "data" / "dex003_full").resolve()
    if _related(root, dex_full):
        raise MatrixSafetyStop(
            "matrix output root must not equal, contain, or sit inside data/dex003_full",
            context={"output_root": str(root)},
        )
    parts = list(root.parts)
    for i in range(len(parts) - 1):
        if parts[i] == "data" and parts[i + 1] == "dex003_full":
            raise MatrixSafetyStop(
                "matrix output root collides with data/dex003_full path segment",
                context={"output_root": str(root)},
            )
    if ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID in root.parts:
        raise MatrixSafetyStop("matrix output root collides with accepted registry id")
    text = str(root).replace("\\", "/")
    if "/dex/dex_pool_registry" in text:
        raise MatrixSafetyStop("matrix output root collides with staged registry path")
    if registry_store_root is not None:
        reg = _resolve(registry_store_root)
        if _related(root, reg):
            raise MatrixSafetyStop(
                "matrix output root must not equal, contain, or sit inside registry store",
                context={"output_root": str(root), "registry_store_root": str(reg)},
            )
    return root


def _strip_meta(node: Any) -> Any:
    if isinstance(node, Mapping):
        return {
            k: _strip_meta(v)
            for k, v in node.items()
            if k not in _UNHASHED_METADATA and k not in {"evidence_hash", "report_hash"}
        }
    if isinstance(node, list):
        return [_strip_meta(x) for x in node]
    return node


def compute_evidence_hash(payload: Mapping[str, Any]) -> str:
    return _sha256_text(_canonical_json(_strip_meta(dict(payload))))


def compute_report_hash(*, evidence_hash: str, payload: Mapping[str, Any]) -> str:
    return _sha256_text(
        _canonical_json({"evidence_hash": evidence_hash, "report": _strip_meta(dict(payload))})
    )


def _exclusive_write_bytes(path: Path, data: bytes, *, fsync: bool = False) -> None:
    """O_EXCL create. fsync reserved for terminal/plan durability points."""
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(str(path), flags, 0o644)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            if fsync:
                os.fsync(fh.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _exclusive_write_text(path: Path, text: str, *, fsync: bool = False) -> None:
    _scan_text(text, label=path.name)
    _exclusive_write_bytes(path, text.encode("utf-8"), fsync=fsync)


def _file_meta(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"sha256": _sha256_bytes(data), "bytes": len(data)}


def _promote_raw(spool: Path, raw_dir: Path, digest: str) -> Path:
    dest = raw_dir / f"{digest}.bin"
    if dest.exists():
        existing = dest.read_bytes()
        if _sha256_bytes(existing) != digest or existing != spool.read_bytes():
            raise MatrixSafetyStop(
                "content-addressed raw mismatch",
                context={"body_sha256": digest},
            )
        try:
            spool.unlink()
        except OSError:
            pass
        return dest
    tmp = raw_dir / f".promote_{digest}_{uuid.uuid4().hex}.tmp"
    try:
        os.replace(spool, tmp)
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


# ---------------------------------------------------------------------------
# Budgets / limiters
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

    def as_dict(self) -> dict[str, Any]:
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
        if time.monotonic() - self.started_at > self.budgets.max_wall_seconds:
            raise MatrixSafetyStop("global wall-time budget breached")

    def remaining_wall_seconds(self) -> float:
        return max(0.0, self.budgets.max_wall_seconds - (time.monotonic() - self.started_at))

    def http_timeout_seconds(self) -> float:
        """Cap HTTP timeout by remaining wall budget (hard wall across waits/HTTP)."""
        rem = self.remaining_wall_seconds()
        if rem <= 0:
            raise MatrixSafetyStop("global wall-time budget breached")
        return min(self.budgets.http_timeout_seconds, rem)

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

    def reserve(self, nbytes: int) -> None:
        with self._lock:
            self.check_wall()
            projected = (
                self.retained_response_bytes + self.reserved_response_bytes + nbytes
            )
            if projected > self.budgets.max_retained_response_bytes:
                raise MatrixSafetyStop("retained-byte reservation would breach budget")
            self.reserved_response_bytes += nbytes

    def commit(self, reserved: int, actual: int) -> None:
        with self._lock:
            if actual < 0 or reserved < actual or self.reserved_response_bytes < reserved:
                raise MatrixSafetyStop("invalid reservation commit")
            self.reserved_response_bytes -= reserved
            self.retained_response_bytes += actual
            if self.retained_response_bytes > self.budgets.max_retained_response_bytes:
                raise MatrixSafetyStop("retained bytes exceed budget")

    def release(self, reserved: int) -> None:
        with self._lock:
            if self.reserved_response_bytes < reserved:
                raise MatrixSafetyStop("reservation release underflow")
            self.reserved_response_bytes -= reserved

    def note_429(self) -> None:
        with self._lock:
            self.http_429_count += 1

    def note_in_flight(self, n: int) -> None:
        with self._lock:
            if n > self.high_water_in_flight:
                self.high_water_in_flight = n

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
        raise MatrixSafetyStop("stop signal while waiting for RPS token")


class _ProviderGate:
    def __init__(self, *, max_in_flight: int, rps: float) -> None:
        self.sem = threading.Semaphore(max_in_flight)
        self.rps = _RpsLimiter(rate=rps)
        self.in_flight = 0
        self._lock = threading.Lock()

    def acquire(self, *, stop: threading.Event, tracker: BudgetTracker) -> None:
        while not stop.is_set():
            tracker.check_wall()
            if self.sem.acquire(timeout=0.1):
                break
        else:
            raise MatrixSafetyStop("stop signal while waiting for in-flight slot")
        try:
            self.rps.acquire(stop=stop)
            tracker.check_wall()  # hard wall after semaphore/RPS waits
        except Exception:
            self.sem.release()
            raise
        with self._lock:
            self.in_flight += 1
            tracker.note_in_flight(self.in_flight)

    def release(self) -> None:
        with self._lock:
            self.in_flight = max(0, self.in_flight - 1)
        self.sem.release()


# ---------------------------------------------------------------------------
# Registry + plan (pure)
# ---------------------------------------------------------------------------


def verify_and_load_accepted_registry(
    registry_store_root: Path | str,
    *,
    expected_dataset_id: str = ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID,
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    store = _resolve(registry_store_root)
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
        s for s in manifest.files if s.relative_path == DEX_POOL_REGISTRY_RELATIVE_PATH
    )
    if observed_sha != declared.sha256 or observed_bytes != declared.bytes:
        raise MatrixSafetyStop("registry parquet does not match manifest")
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
        {
            "dataset_id": expected_dataset_id,
            "parquet_sha256": observed_sha,
            "parquet_bytes": observed_bytes,
            "pool_count": len(pools),
        },
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


def verify_pinned_cohort_hashes(cohort: Sequence[str]) -> dict[int, str]:
    observed: dict[int, str] = {}
    for size in NESTED_COHORT_SIZES:
        digest = compact_json_array_hash(cohort[:size])
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
        _reject_sensitive(payload, label="matrix_plan")
        return payload

    @staticmethod
    def from_public_dict(payload: Mapping[str, Any]) -> MatrixPlan:
        ranges = {
            name: (
                int(payload["ranges"][name]["start"]),
                int(payload["ranges"][name]["end"]),
            )
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
    primary = normalize_provider_org(provider_orgs[0], label="primary_org")
    secondary = normalize_provider_org(provider_orgs[1], label="secondary_org")
    if primary == secondary:
        raise MatrixError("provider organizations must be distinct")
    verification, pools = verify_and_load_accepted_registry(registry_store_root)
    maximum = select_matrix_maximum_cohort(pools)
    hashes = verify_pinned_cohort_hashes(maximum)
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
        "registry_dataset_id": verification["dataset_id"],
        "registry_parquet_bytes": verification["parquet_bytes"],
        "registry_parquet_sha256": verification["parquet_sha256"],
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
        registry_dataset_id=str(verification["dataset_id"]),
        registry_parquet_sha256=str(verification["parquet_sha256"]),
        registry_parquet_bytes=int(verification["parquet_bytes"]),
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
    _reject_sensitive(plan.to_public_dict(), label="matrix_plan")
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
                    tag = "swap" if topic == SWAP_TOPIC else "sync"
                    lid = f"scalar:{range_name}:{org}:{address}:{tag}"
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


def _receipt_name(logical_call_id: str, attempt: int) -> str:
    return f"{logical_call_id.replace(':', '__')}__a{attempt}.json"


# ---------------------------------------------------------------------------
# Fresh exclusive run directory
# ---------------------------------------------------------------------------


class MatrixRun:
    """One exclusive immutable run directory (no resume)."""

    def __init__(self, output_root: Path, *, run_id: str | None = None) -> None:
        self.output_root = assert_safe_matrix_output_root(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.runs_root = self.output_root / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)
        rid = run_id or _new_run_id()
        if not _RUN_ID_RE.fullmatch(rid):
            raise MatrixError("invalid run_id")
        self.run_id = rid
        self.run_dir = self.runs_root / rid
        try:
            os.mkdir(self.run_dir)
        except FileExistsError as exc:
            raise MatrixSafetyStop(
                "run directory already exists; fresh runs are exclusive",
                context={"run_id": rid},
            ) from exc
        self.plan_path = self.run_dir / "plan.json"
        self.catalog_path = self.run_dir / "catalog.json"
        self.receipts_dir = self.run_dir / "receipts"
        self.raw_dir = self.run_dir / "raw"
        self.spool_dir = self.run_dir / "spool"
        for d in (self.receipts_dir, self.raw_dir, self.spool_dir):
            d.mkdir()
        self.complete_path = self.run_dir / "COMPLETE.json"
        self.failed_path = self.run_dir / "FAILED.json"
        self._sealed = False
        self._open_spools: list[Path] = []
        self._lock = threading.Lock()
        self._attempt_index: dict[str, int] = {}
    def write_plan_and_catalog(self, plan: MatrixPlan) -> None:
        if self.plan_path.exists() or self.catalog_path.exists():
            raise MatrixSafetyStop("plan/catalog already written for this run")
        plan_text = json.dumps(plan.to_public_dict(), indent=2, sort_keys=True) + "\n"
        cat = catalog_entries(plan)
        cat_text = json.dumps(cat, indent=2, sort_keys=True) + "\n"
        _reject_sensitive(plan.to_public_dict(), label="plan.json")
        _reject_sensitive(cat, label="catalog.json")
        _exclusive_write_text(self.plan_path, plan_text, fsync=True)
        _exclusive_write_text(self.catalog_path, cat_text, fsync=True)

    def stream_to_receipt(
        self,
        *,
        call: LogicalCall,
        attempt: int,
        chunks_iter: Any,
        max_response_bytes: int,
        status_code: int | None,
        latency_ms: float,
        http_429: bool,
        error_class: str | None,
        error_detail: str | None,
        wall_check: Callable[[], None] | None = None,
        stream_abort: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        """Stream once: scan before write; enforce absolute wall while consuming chunks.

        On wall expiry the response is cooperatively aborted and the chunk-reader
        thread is joined before this method returns (no abandoned stream work).
        """
        with self._lock:
            prev = self._attempt_index.get(call.logical_call_id, 0)
            if attempt != prev + 1:
                raise MatrixSafetyStop(
                    "attempt numbers must be contiguous from 1",
                    context={"logical_call_id": call.logical_call_id, "attempt": attempt},
                )
            self._attempt_index[call.logical_call_id] = attempt

        receipt_path = self.receipts_dir / _receipt_name(call.logical_call_id, attempt)
        if receipt_path.exists():
            raise MatrixSafetyStop("duplicate attempt receipt")

        spool = self.spool_dir / (
            f"{_receipt_name(call.logical_call_id, attempt)}.{uuid.uuid4().hex}.part"
        )
        self._open_spools.append(spool)
        retained_hasher = hashlib.sha256()
        observed_hasher = hashlib.sha256()
        retained = 0
        observed = 0
        truncated = False
        # Rolling window so secrets split across chunk boundaries are still found
        # *before* the completing bytes are written.
        scan_tail = bytearray()
        keep = 512
        credential_hit = False
        label = f"response:{call.logical_call_id}"
        # Non-daemon chunk reader; must be joined before return on every path.
        active_reader: list[threading.Thread | None] = [None]

        def _scan_window(window: bytes) -> None:
            _scan_bytes(window, label=label)

        def _deadline() -> None:
            if wall_check is not None:
                wall_check()

        def _close_iterator(it: Any) -> None:
            close = getattr(it, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

        def _abort_stream(it: Any) -> None:
            """Cooperatively stop response work so a blocked reader can finish."""
            if stream_abort is not None:
                try:
                    stream_abort()
                except Exception:
                    pass
            _close_iterator(it)

        def _join_reader(*, timeout: float = 120.0) -> None:
            t = active_reader[0]
            if t is not None and t.is_alive():
                t.join(timeout=timeout)
            active_reader[0] = None

        def _next_chunk(it: Any) -> bytes:
            """Pull next chunk while enforcing absolute wall; join reader on expiry."""
            if wall_check is None:
                return next(it)
            box: dict[str, Any] = {}
            done = threading.Event()

            def _worker() -> None:
                try:
                    box["v"] = next(it)
                except StopIteration:
                    box["stop"] = True
                except BaseException as exc:  # noqa: BLE001
                    box["exc"] = exc
                finally:
                    done.set()

            thread = threading.Thread(
                target=_worker, name="matrix-stream-chunk", daemon=False
            )
            active_reader[0] = thread
            thread.start()
            try:
                while not done.wait(timeout=0.02):
                    try:
                        _deadline()
                    except MatrixSafetyStop:
                        # Stop/close response then join started reader before raise.
                        _abort_stream(it)
                        _join_reader()
                        raise
                _join_reader()
            except MatrixSafetyStop:
                raise
            except Exception:
                _abort_stream(it)
                _join_reader()
                raise
            if "exc" in box:
                raise box["exc"]
            if box.get("stop"):
                raise StopIteration
            return box["v"]  # type: ignore[no-any-return]

        try:
            with open(spool, "wb") as fh:
                chunk_it = iter(chunks_iter)
                while True:
                    try:
                        chunk = _next_chunk(chunk_it)
                    except StopIteration:
                        break
                    if not chunk:
                        continue
                    # Scan before any write of these bytes.
                    window = bytes(scan_tail) + chunk
                    try:
                        _scan_window(window)
                    except MatrixSafetyStop:
                        credential_hit = True
                        # Still hash observed drained bytes without writing secrets.
                        observed_hasher.update(chunk)
                        observed += len(chunk)
                        while True:
                            try:
                                rest = _next_chunk(chunk_it)
                            except StopIteration:
                                break
                            if not rest:
                                continue
                            observed_hasher.update(rest)
                            observed += len(rest)
                            # Keep scanning drained over-cap/credential tail.
                            try:
                                _scan_window(rest)
                            except MatrixSafetyStop:
                                pass
                        break
                    scan_tail = bytearray(window[-keep:])
                    observed_hasher.update(chunk)
                    observed += len(chunk)
                    if retained < max_response_bytes:
                        take = min(len(chunk), max_response_bytes - retained)
                        piece = chunk[:take]
                        fh.write(piece)
                        retained_hasher.update(piece)
                        retained += take
                        if take < len(chunk):
                            truncated = True
                    else:
                        truncated = True
                # Final tail already scanned with last chunk.
            truncated = observed > max_response_bytes
            observed_sha = observed_hasher.hexdigest()

            body_sha: str | None = None
            body_bytes = 0
            final_error = error_class
            final_detail = error_detail
            data = b""
            if credential_hit:
                try:
                    spool.unlink()
                except OSError:
                    pass
                final_error = "credential_detection"
                final_detail = "credential_or_endpoint_detected"
                body_sha = None
                body_bytes = 0
            else:
                data = spool.read_bytes() if spool.exists() else b""
                body_bytes = len(data)
                body_sha = retained_hasher.hexdigest() if data else _sha256_bytes(b"")
                if not data:
                    spool.write_bytes(b"")
                    body_sha = _sha256_bytes(b"")
                # Classify JSON-RPC before success authority (not for truncated prefixes).
                if (
                    final_error is None
                    and not truncated
                    and status_code is not None
                    and status_code < 400
                ):
                    try:
                        parse_json_rpc_result(data if data else b"")
                    except MatrixSafetyStop:
                        raise
                    except MatrixCellFailure as exc:
                        final_error = str(exc.message)
                        final_detail = str(exc)[:200]
                _promote_raw(spool, self.raw_dir, body_sha)
            if spool in self._open_spools:
                self._open_spools.remove(spool)

            if truncated and final_error is None:
                final_error = "body_size_pressure"
                final_detail = final_detail or "response_truncated_over_max_response_bytes"
            if body_sha is None and final_error is None:
                final_error = "unauthenticated_body"
            if http_429 and final_error is None:
                final_error = "http_429"
                final_detail = final_detail or "HTTP_429"

            success = (
                final_error is None
                and not truncated
                and body_sha is not None
                and (status_code is None or status_code < 400)
            )
            receipt = {
                "logical_call_id": call.logical_call_id,
                "attempt": attempt,
                "run_id": self.run_id,
                "provider_org": call.provider_org,
                "kind": call.kind,
                "request_sha256": _sha256_text(call.request_json()),
                "request_json": call.request_json(),
                "status_code": status_code,
                "body_sha256": body_sha,
                "body_bytes": body_bytes,
                "observed_body_bytes": observed,
                "observed_sha256": observed_sha,
                "truncated": truncated,
                "latency_ms": latency_ms,
                "http_429": bool(http_429),
                "error_class": final_error,
                "error_detail": (
                    "redacted_credential_or_endpoint"
                    if final_detail
                    and (
                        "http" in str(final_detail).lower()
                        or "bearer" in str(final_detail).lower()
                    )
                    else final_detail
                ),
                "retained_at": _now_iso(),
                "success": success,
            }
            if receipt["error_detail"]:
                try:
                    _scan_text(str(receipt["error_detail"]), label="error_detail")
                except MatrixSafetyStop:
                    receipt["error_detail"] = "redacted_credential_or_endpoint"
            _reject_sensitive(receipt, label="attempt_receipt")
            _exclusive_write_text(
                receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n"
            )
            # Do not cache for authority — replay/auth always re-read disk.
            return receipt
        except MatrixSafetyStop:
            # Reader already joined on wall path inside _next_chunk; join any remnant.
            _join_reader()
            raise
        except OSError as exc:
            _join_reader()
            raise MatrixSafetyStop(
                "raw-persistence failure",
                context={"logical_call_id": call.logical_call_id},
            ) from exc
        finally:
            _join_reader()
            if spool.exists() and spool in self._open_spools:
                try:
                    spool.unlink()
                except OSError:
                    pass
                if spool in self._open_spools:
                    self._open_spools.remove(spool)

    def retain_bytes(
        self,
        *,
        call: LogicalCall,
        attempt: int,
        body: bytes,
        max_response_bytes: int,
        status_code: int | None,
        latency_ms: float,
        http_429: bool,
        error_class: str | None,
        error_detail: str | None,
    ) -> dict[str, Any]:
        """Injectable path: stream body in STREAM_CHUNK_BYTES slices (same as live HTTP)."""

        def gen() -> Any:
            view = memoryview(body)
            step = STREAM_CHUNK_BYTES
            for i in range(0, len(view), step):
                yield bytes(view[i : i + step])

        return self.stream_to_receipt(
            call=call,
            attempt=attempt,
            chunks_iter=gen(),
            max_response_bytes=max_response_bytes,
            status_code=status_code,
            latency_ms=latency_ms,
            http_429=http_429,
            error_class=error_class,
            error_detail=error_detail,
            wall_check=None,
        )

    def best_success_body(self, logical_call_id: str) -> tuple[str, int] | None:
        best: tuple[str, int] | None = None
        for rec in self.list_receipts(logical_call_id):
            if rec.get("success") and rec.get("body_sha256"):
                best = (str(rec["body_sha256"]), int(rec["body_bytes"]))
        return best

    def list_receipts(self, logical_call_id: str) -> list[dict[str, Any]]:
        """Always re-read receipts from disk (no authority cache)."""
        rows: list[dict[str, Any]] = []
        for path in sorted(
            self.receipts_dir.glob(f"{logical_call_id.replace(':', '__')}__a*.json")
        ):
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        return rows

    def load_body(self, body_sha256: str, *, expected_bytes: int | None = None) -> bytes:
        """Always re-read and rehash raw from disk (no authority cache)."""
        if not _SHA256_RE.fullmatch(body_sha256):
            raise MatrixSafetyStop("invalid body sha256")
        path = self.raw_dir / f"{body_sha256}.bin"
        if not path.is_file():
            raise MatrixSafetyStop("retained body missing")
        data = path.read_bytes()
        if _sha256_bytes(data) != body_sha256:
            raise MatrixSafetyStop("retained body SHA-256 mismatch")
        if expected_bytes is not None and len(data) != expected_bytes:
            raise MatrixSafetyStop("retained body byte count mismatch")
        return data

    def _enumerate_allowed_files(self) -> dict[str, dict[str, Any]]:
        files: dict[str, dict[str, Any]] = {}
        for name in ("plan.json", "catalog.json"):
            path = self.run_dir / name
            if path.is_file():
                files[name] = _file_meta(path)
        for path in sorted(self.receipts_dir.glob("*.json")):
            rel = f"receipts/{path.name}"
            files[rel] = _file_meta(path)
        for path in sorted(self.raw_dir.glob("*.bin")):
            rel = f"raw/{path.name}"
            files[rel] = _file_meta(path)
        return files

    def _assert_no_stray_files(self, allowed: set[str]) -> None:
        # Spool must be empty at seal time.
        if any(self.spool_dir.iterdir()):
            raise MatrixSafetyStop("spool not empty at seal")
        for path in self.run_dir.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(self.run_dir)).replace("\\", "/")
            if rel.startswith("spool/"):
                raise MatrixSafetyStop("spool file present at seal")
            if rel in allowed:
                continue
            if rel in {"COMPLETE.json", "FAILED.json"}:
                continue
            raise MatrixSafetyStop(
                "extra file in run directory",
                context={"path": rel},
            )

    def seal(
        self,
        *,
        kind: TerminalKind,
        report: Mapping[str, Any],
    ) -> dict[str, Any]:
        if self._sealed:
            raise MatrixSafetyStop("run already sealed")
        if self.complete_path.exists() or self.failed_path.exists():
            raise MatrixSafetyStop("terminal manifest already exists")
        payload = dict(report)
        payload["status"] = kind
        payload["run_id"] = self.run_id
        payload["run_dir"] = str(self.run_dir)
        files = self._enumerate_allowed_files()
        payload["files"] = files
        self._assert_no_stray_files(set(files))
        # Evidence hash over complete sealed body except wall timestamps and hash fields.
        evidence_hash = compute_evidence_hash(payload)
        payload["evidence_hash"] = evidence_hash
        report_hash = compute_report_hash(evidence_hash=evidence_hash, payload=payload)
        payload["report_hash"] = report_hash
        _reject_sensitive(payload, label=f"{kind}.json")
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        terminal = self.complete_path if kind == "COMPLETE" else self.failed_path
        _exclusive_write_text(terminal, text, fsync=True)
        # Terminal file itself is authenticated by exclusive create + content.
        self._sealed = True
        self._cleanup_spool()
        return payload

    def _cleanup_spool(self) -> None:
        for spool in list(self._open_spools):
            try:
                if spool.exists():
                    spool.unlink()
            except OSError:
                pass
        self._open_spools.clear()
        if self.spool_dir.exists():
            for p in self.spool_dir.iterdir():
                try:
                    p.unlink()
                except OSError:
                    pass

    def close(self) -> None:
        self._cleanup_spool()


def _inventory_snapshot(run_dir: Path) -> dict[str, str]:
    """Relative path -> sha256 for every file under run_dir (sorted)."""
    root = run_dir.resolve()
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        out[rel] = _sha256_bytes(path.read_bytes())
    return out


def validate_run_call_inventory(root: Path, plan: MatrixPlan) -> dict[str, Any]:
    """Authenticate plan/catalog/receipts/raw relationships; reject orphans/unknowns."""
    plan_path = root / "plan.json"
    cat_path = root / "catalog.json"
    if not plan_path.is_file() or not cat_path.is_file():
        raise MatrixSafetyStop("plan/catalog missing for inventory validation")
    plan_text = plan_path.read_text(encoding="utf-8")
    cat_text = cat_path.read_text(encoding="utf-8")
    stored_plan = MatrixPlan.from_public_dict(json.loads(plan_text))
    if stored_plan.matrix_id != plan.matrix_id:
        raise MatrixSafetyStop("plan matrix_id mismatch during inventory validation")
    # Canonical catalog bytes must match plan-derived catalog exactly.
    expected_cat = catalog_entries(plan)
    expected_cat_text = json.dumps(expected_cat, indent=2, sort_keys=True) + "\n"
    if cat_text != expected_cat_text:
        raise MatrixSafetyStop("catalog is not byte-exact plan-derived catalog")
    expected_calls = {c.logical_call_id: c for c in iter_logical_calls(plan)}
    receipts_dir = root / "receipts"
    raw_dir = root / "raw"
    seen_receipts: set[str] = set()
    referenced_raw: set[str] = set()
    per_call_attempts: dict[str, list[dict[str, Any]]] = {cid: [] for cid in expected_calls}

    if receipts_dir.is_dir():
        for path in sorted(receipts_dir.glob("*.json")):
            rec = json.loads(path.read_text(encoding="utf-8"))
            cid = str(rec.get("logical_call_id") or "")
            attempt = int(rec.get("attempt") or 0)
            expected_name = _receipt_name(cid, attempt)
            if path.name != expected_name:
                raise MatrixSafetyStop(
                    "receipt filename does not match call/attempt binding",
                    context={"name": path.name, "expected": expected_name},
                )
            if cid not in expected_calls:
                raise MatrixSafetyStop(
                    "unknown logical-call receipt",
                    context={"logical_call_id": cid},
                )
            call = expected_calls[cid]
            if str(rec.get("run_id") or "") != root.name:
                raise MatrixSafetyStop(
                    "receipt run_id does not match run directory",
                    context={"receipt_run_id": rec.get("run_id"), "dir": root.name},
                )
            if str(rec.get("provider_org")) != call.provider_org:
                raise MatrixSafetyStop("receipt provider_org mismatch")
            if str(rec.get("kind")) != call.kind:
                raise MatrixSafetyStop("receipt kind mismatch")
            if str(rec.get("request_json")) != call.request_json():
                raise MatrixSafetyStop("receipt request_json mismatch")
            if str(rec.get("request_sha256")) != _sha256_text(call.request_json()):
                raise MatrixSafetyStop("receipt request_sha256 mismatch")
            per_call_attempts[cid].append(rec)
            seen_receipts.add(path.name)
            body_sha = rec.get("body_sha256")
            if body_sha:
                referenced_raw.add(str(body_sha))
                raw_path = raw_dir / f"{body_sha}.bin"
                if not raw_path.is_file():
                    raise MatrixSafetyStop(
                        "receipt references missing raw",
                        context={"body_sha256": body_sha},
                    )
                data = raw_path.read_bytes()
                if _sha256_bytes(data) != body_sha:
                    raise MatrixSafetyStop("raw SHA-256 mismatch on rehash")
                if int(rec.get("body_bytes") or -1) != len(data):
                    raise MatrixSafetyStop("receipt body_bytes disagrees with raw")
            # Success semantics.
            if rec.get("success"):
                if rec.get("error_class") or rec.get("truncated") or not body_sha:
                    raise MatrixSafetyStop("success receipt has error/truncated/no body")
                # Re-parse envelope.
                parse_json_rpc_result(raw_dir.joinpath(f"{body_sha}.bin").read_bytes())
            else:
                if not rec.get("error_class") and not rec.get("truncated"):
                    raise MatrixSafetyStop("non-success receipt lacks error/truncated")

    # Contiguous attempts from 1; live execute inventory requires all calls present.
    for cid, rows in per_call_attempts.items():
        rows_sorted = sorted(rows, key=lambda r: int(r["attempt"]))
        for i, row in enumerate(rows_sorted, start=1):
            if int(row["attempt"]) != i:
                raise MatrixSafetyStop(
                    "non-contiguous attempts",
                    context={"logical_call_id": cid, "attempt": row["attempt"]},
                )

    # Orphan raw objects.
    if raw_dir.is_dir():
        for path in raw_dir.glob("*.bin"):
            digest = path.name[: -len(".bin")]
            if digest not in referenced_raw:
                raise MatrixSafetyStop(
                    "orphan raw object not referenced by any receipt",
                    context={"name": path.name},
                )

    return {
        "expected_call_count": len(expected_calls),
        "receipt_file_count": len(seen_receipts),
        "calls_with_attempts": sum(1 for rows in per_call_attempts.values() if rows),
        "referenced_raw_count": len(referenced_raw),
    }


def authenticate_completed_run(
    run_dir: Path | str,
    *,
    require_live_pass: bool = False,
) -> dict[str, Any]:
    """Read-only authentication of a sealed COMPLETE run directory.

    When ``require_live_pass`` is True (standalone replay source), require
    mode=execute_live, complete/pass true, dual chain evidence, all 15 cells, and
    the full 1,568-call inventory.
    """
    root = _resolve(run_dir)
    if not root.is_dir():
        raise MatrixError("run directory missing")
    complete = root / "COMPLETE.json"
    failed = root / "FAILED.json"
    if failed.exists() and not complete.exists():
        raise MatrixError("run sealed as FAILED; not eligible for PASS replay")
    if not complete.is_file():
        raise MatrixError("COMPLETE.json missing; run incomplete")
    if failed.exists():
        raise MatrixSafetyStop("both COMPLETE and FAILED present")
    report = json.loads(complete.read_text(encoding="utf-8"))
    _reject_sensitive(report, label="COMPLETE.json")
    if report.get("status") != "COMPLETE":
        raise MatrixError("terminal status is not COMPLETE")
    files = report.get("files")
    if not isinstance(files, Mapping):
        raise MatrixSafetyStop("terminal files map missing")
    for rel, meta in files.items():
        rel_s = str(rel).replace("\\", "/")
        if ".." in rel_s.split("/") or rel_s.startswith("/"):
            raise MatrixSafetyStop("path escape in terminal files map")
        path = (root / rel_s).resolve()
        if not str(path).startswith(str(root.resolve())):
            raise MatrixSafetyStop("path escapes run directory")
        if not path.is_file():
            raise MatrixSafetyStop(
                "enumerated file missing",
                context={"path": rel_s},
            )
        actual = _file_meta(path)
        if actual["sha256"] != meta.get("sha256") or actual["bytes"] != meta.get("bytes"):
            raise MatrixSafetyStop(
                "enumerated file hash/bytes mismatch",
                context={"path": rel_s},
            )
    allowed = set(str(k).replace("\\", "/") for k in files) | {"COMPLETE.json"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if rel.startswith("spool/"):
            raise MatrixSafetyStop("spool residue in completed run")
        if rel not in allowed:
            raise MatrixSafetyStop(
                "extra file in completed run",
                context={"path": rel},
            )
    evidence = str(report.get("evidence_hash") or "")
    recomputed_e = compute_evidence_hash(report)
    if evidence != recomputed_e:
        raise MatrixSafetyStop(
            "evidence_hash authentication failed",
            context={"expected": evidence, "recomputed": recomputed_e},
        )
    report_hash = str(report.get("report_hash") or "")
    recomputed_r = compute_report_hash(evidence_hash=evidence, payload=report)
    if report_hash != recomputed_r:
        raise MatrixSafetyStop(
            "report_hash authentication failed",
            context={"expected": report_hash, "recomputed": recomputed_r},
        )
    plan = MatrixPlan.from_public_dict(
        json.loads((root / "plan.json").read_text(encoding="utf-8"))
    )
    inventory = validate_run_call_inventory(root, plan)
    if report.get("matrix_id") != plan.matrix_id:
        raise MatrixSafetyStop("terminal matrix_id disagrees with plan")

    if require_live_pass:
        if report.get("mode") != "execute_live":
            raise MatrixError(
                "live PASS replay source must have mode=execute_live",
                context={"mode": report.get("mode")},
            )
        if report.get("complete") is not True or report.get("pass") is not True:
            raise MatrixError("live PASS replay source must be complete with pass=true")
        cells = report.get("cells") or []
        if len(cells) != 15 or not all(c.get("status") == "pass" for c in cells):
            raise MatrixError("live PASS replay source must have 15 passing cells")
        if inventory["calls_with_attempts"] != LOGICAL_CALL_CEILING:
            raise MatrixSafetyStop(
                "live PASS run must contain attempts for all 1,568 logical calls",
                context={"calls_with_attempts": inventory["calls_with_attempts"]},
            )
        # Dual mainnet chain evidence required.
        for org in plan.provider_orgs:
            rows = []
            receipts_dir = root / "receipts"
            for path in sorted(receipts_dir.glob(f"chain__{org}__a*.json")):
                rows.append(json.loads(path.read_text(encoding="utf-8")))
            success = [r for r in rows if r.get("success")]
            if not success:
                raise MatrixSafetyStop(
                    "missing dual mainnet chain success evidence",
                    context={"provider_org": org},
                )
            body = (root / "raw" / f"{success[-1]['body_sha256']}.bin").read_bytes()
            if interpret_chain_id(body) != _hex_quantity(
                ETHEREUM_MAINNET_CHAIN_ID, label="mainnet"
            ):
                raise MatrixSafetyStop("chain evidence is not Ethereum mainnet")
    return report


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TransportResult:
    status_code: int | None
    body: bytes | None
    stream_response: Any | None
    latency_ms: float
    http_429: bool
    error_class: str | None
    error_detail: str | None


TransportFn = Callable[[str, Mapping[str, Any]], TransportResult]


class HttpxTransport:
    def __init__(self, *, org_to_url: Mapping[str, str], timeout_seconds: float) -> None:
        # Constructor timeout is only a default; each request must pass remaining wall.
        self._default_timeout = timeout_seconds
        self._urls = dict(org_to_url)
        self._clients = {
            org: httpx.Client(timeout=timeout_seconds) for org in org_to_url
        }
        self._closed = False
        self._open: list[Any] = []
        self._open_lock = threading.Lock()

    def begin(
        self,
        provider_org: str,
        request: Mapping[str, Any],
        *,
        timeout_seconds: float | None = None,
    ) -> TransportResult:
        if self._closed:
            raise MatrixError("transport closed")
        if provider_org not in self._urls:
            raise MatrixError("unknown provider org")
        client = self._clients[provider_org]
        url = self._urls[provider_org]
        # Hard wall: every HTTP operation uses remaining-wall-capped timeout.
        timeout = float(
            timeout_seconds if timeout_seconds is not None else self._default_timeout
        )
        if timeout <= 0:
            raise MatrixSafetyStop("global wall-time budget breached before HTTP")
        started = time.monotonic()
        try:
            cm = client.stream(
                "POST",
                url,
                json=dict(request),
                timeout=httpx.Timeout(timeout),
            )
            response = cm.__enter__()
            with self._open_lock:
                self._open.append((cm, response))
            latency = (time.monotonic() - started) * 1000.0
            err = None
            detail = None
            if response.status_code >= 400:
                err = "http_status"
                detail = f"HTTP_{response.status_code}"
            return TransportResult(
                status_code=response.status_code,
                body=None,
                stream_response=response,
                latency_ms=latency,
                http_429=response.status_code == 429,
                error_class=err,
                error_detail=detail,
            )
        except httpx.TimeoutException:
            raise MatrixSafetyStop(
                "global wall-time budget breached during HTTP",
                context={"timeout_seconds": timeout},
            )
        except httpx.HTTPError as exc:
            return TransportResult(
                status_code=None,
                body=None,
                stream_response=None,
                latency_ms=(time.monotonic() - started) * 1000.0,
                http_429=False,
                error_class="transport",
                error_detail=type(exc).__name__,
            )

    def finish(self, response: Any) -> None:
        with self._open_lock:
            remaining = []
            for cm, resp in self._open:
                if resp is response:
                    try:
                        cm.__exit__(None, None, None)
                    except Exception:
                        pass
                else:
                    remaining.append((cm, resp))
            self._open = remaining

    def close(self) -> None:
        self._closed = True
        with self._open_lock:
            open_items = list(self._open)
            self._open.clear()
        for cm, _ in open_items:
            try:
                cm.__exit__(None, None, None)
            except Exception:
                pass
        for client in self._clients.values():
            try:
                client.close()
            except Exception:
                pass
        self._clients.clear()


# ---------------------------------------------------------------------------
# Response interpretation
# ---------------------------------------------------------------------------


def parse_json_rpc_result(body: bytes) -> Any:
    if not body:
        raise MatrixSafetyStop("empty response body is malformed evidence")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MatrixSafetyStop("malformed_json response body") from exc
    if not isinstance(payload, Mapping):
        raise MatrixSafetyStop("json-rpc envelope must be an object")
    if payload.get("error") is not None:
        err = payload["error"]
        detail = str(err.get("message", err) if isinstance(err, Mapping) else err)
        try:
            _scan_text(detail, label="rpc_error")
        except MatrixSafetyStop:
            detail = "redacted_credential_or_endpoint"
        lower = detail.lower()
        if any(
            t in lower
            for t in ("limit", "too many", "query returned more", "response size", "timeout")
        ):
            raise MatrixCellFailure("provider_limit_or_size", context={"rpc_error": detail[:200]})
        raise MatrixCellFailure("rpc_error", context={"rpc_error": detail[:200]})
    if "result" not in payload:
        raise MatrixSafetyStop("json-rpc missing result is malformed evidence")
    return payload["result"]


def interpret_chain_id(body: bytes) -> int:
    result = parse_json_rpc_result(body)
    try:
        return _hex_quantity(result, label="eth_chainId result")
    except Exception as exc:
        raise MatrixSafetyStop(
            "malformed chain id evidence",
            context={"error": type(exc).__name__},
        ) from exc


def interpret_logs(body: bytes, *, domain: QueryDomain) -> tuple[tuple[Any, ...], str]:
    result = parse_json_rpc_result(body)
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


# ---------------------------------------------------------------------------
# Cells
# ---------------------------------------------------------------------------


def _receipt_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
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
        "http_429s": sum(1 for r in rows if r.get("http_429")),
        "latency_ms_total": sum(float(r.get("latency_ms") or 0.0) for r in rows),
        "response_bytes": sum(int(r.get("body_bytes") or 0) for r in rows),
        "observed_body_bytes_total": sum(int(r.get("observed_body_bytes") or 0) for r in rows),
        "truncated_attempts": sum(1 for r in rows if r.get("truncated")),
        "status": "success" if last.get("success") else "error",
        "error_class": last.get("error_class"),
        "last_status_code": last.get("status_code"),
    }


def provider_side_metrics(
    run: MatrixRun,
    *,
    plan: MatrixPlan,
    range_name: str,
    provider_org: str,
    addresses: Sequence[str],
    cohort_size: int,
) -> dict[str, Any]:
    scalar_rows: list[dict[str, Any]] = []
    for address in addresses:
        for topic in plan.topics:
            tag = "swap" if topic == SWAP_TOPIC else "sync"
            lid = f"scalar:{range_name}:{provider_org}:{address}:{tag}"
            scalar_rows.extend(run.list_receipts(lid))
    batch_lid = f"batch:{range_name}:{cohort_size}:{provider_org}"
    batch_rows = run.list_receipts(batch_lid)
    sm = _receipt_metrics(scalar_rows)
    bm = _receipt_metrics(batch_rows)
    return {
        "provider_org": provider_org,
        "scalar_attempts": sm["attempts"],
        "scalar_http_429s": sm["http_429s"],
        "scalar_latency_ms_total": sm["latency_ms_total"],
        "scalar_response_bytes": sm["response_bytes"],
        "scalar_observed_body_bytes_total": sm["observed_body_bytes_total"],
        "scalar_truncated_attempts": sm["truncated_attempts"],
        "scalar_status": sm["status"],
        "scalar_error_class": sm["error_class"],
        "batch_attempts": bm["attempts"],
        "batch_http_429s": bm["http_429s"],
        "batch_latency_ms_total": bm["latency_ms_total"],
        "batch_response_bytes": bm["response_bytes"],
        "batch_observed_body_bytes_total": bm["observed_body_bytes_total"],
        "batch_truncated_attempts": bm["truncated_attempts"],
        "batch_status": bm["status"],
        "batch_error_class": bm["error_class"],
        "batch_last_status_code": bm["last_status_code"],
        "attempts": sm["attempts"] + bm["attempts"],
        "http_429s": sm["http_429s"] + bm["http_429s"],
        "latency_ms_total": sm["latency_ms_total"] + bm["latency_ms_total"],
        "response_bytes": sm["response_bytes"] + bm["response_bytes"],
        "observed_body_bytes_total": (
            sm["observed_body_bytes_total"] + bm["observed_body_bytes_total"]
        ),
        "truncated_attempts": sm["truncated_attempts"] + bm["truncated_attempts"],
        "status": bm["status"] if batch_rows else sm["status"],
        "error_class": bm["error_class"] or sm["error_class"],
    }


def scalar_union_digest(
    run: MatrixRun,
    *,
    plan: MatrixPlan,
    range_name: str,
    provider_org: str,
    addresses: Sequence[str],
) -> tuple[str, int]:
    start, end = plan.ranges[range_name]
    all_ids: list[Any] = []
    for address in addresses:
        for topic in plan.topics:
            tag = "swap" if topic == SWAP_TOPIC else "sync"
            lid = f"scalar:{range_name}:{provider_org}:{address}:{tag}"
            success = run.best_success_body(lid)
            if success is None:
                rows = run.list_receipts(lid)
                if not rows:
                    raise MatrixError(
                        "missing scalar attempts",
                        context={"logical_call_id": lid},
                    )
                raise MatrixCellFailure(
                    "scalar call has no successful body",
                    context={"logical_call_id": lid, "error_class": rows[-1].get("error_class")},
                )
            body = run.load_body(success[0], expected_bytes=success[1])
            domain = _domain_for(
                addresses=[address], start=start, end=end, topics=[topic]
            )
            identities, _ = interpret_logs(body, domain=domain)
            all_ids.extend(identities)
    unique = {i.as_tuple(): i for i in all_ids}
    ordered = tuple(sorted(unique.values(), key=lambda i: i.sort_key()))
    return log_identity_v2_digest(ordered), len(ordered)


def _collect_call_metrics(run: Any, plan: MatrixPlan) -> dict[str, Any]:
    """Exact per-call and per-provider metrics from disk receipts."""
    by_provider: dict[str, dict[str, Any]] = {
        org: {
            "attempts": 0,
            "http_429s": 0,
            "successes": 0,
            "failures": 0,
            "response_bytes": 0,
            "observed_body_bytes": 0,
            "truncated_attempts": 0,
            "latency_ms_total": 0.0,
        }
        for org in plan.provider_orgs
    }
    per_call: list[dict[str, Any]] = []
    for call in iter_logical_calls(plan):
        rows = run.list_receipts(call.logical_call_id)
        m = _receipt_metrics(rows)
        entry = {
            "logical_call_id": call.logical_call_id,
            "kind": call.kind,
            "provider_org": call.provider_org,
            **m,
        }
        per_call.append(entry)
        p = by_provider[call.provider_org]
        p["attempts"] += m["attempts"]
        p["http_429s"] += m["http_429s"]
        p["response_bytes"] += m["response_bytes"]
        p["observed_body_bytes"] += m["observed_body_bytes_total"]
        p["truncated_attempts"] += m["truncated_attempts"]
        p["latency_ms_total"] += m["latency_ms_total"]
        if m["status"] == "success":
            p["successes"] += 1
        elif m["attempts"]:
            p["failures"] += 1
    return {
        "per_provider": by_provider,
        "per_call_count": len(per_call),
        "per_call": per_call,
    }


def evaluate_cells(run: MatrixRun, plan: MatrixPlan) -> list[dict[str, Any]]:
    primary, secondary = plan.provider_orgs
    cells: list[dict[str, Any]] = []
    for range_name in RANGE_ORDER:
        start, end = plan.ranges[range_name]
        for size in NESTED_COHORT_SIZES:
            addresses = plan.maximum_cohort[:size]
            cell_id = f"{range_name}:cohort{size}"
            p_m = provider_side_metrics(
                run,
                plan=plan,
                range_name=range_name,
                provider_org=primary,
                addresses=addresses,
                cohort_size=size,
            )
            s_m = provider_side_metrics(
                run,
                plan=plan,
                range_name=range_name,
                provider_org=secondary,
                addresses=addresses,
                cohort_size=size,
            )
            try:
                s_p, n_p = scalar_union_digest(
                    run,
                    plan=plan,
                    range_name=range_name,
                    provider_org=primary,
                    addresses=addresses,
                )
                s_s, n_s = scalar_union_digest(
                    run,
                    plan=plan,
                    range_name=range_name,
                    provider_org=secondary,
                    addresses=addresses,
                )
                batch_p = _batch_digest(run, plan, range_name, size, primary, addresses, start, end)
                batch_s = _batch_digest(run, plan, range_name, size, secondary, addresses, start, end)
                eq_p = batch_p["digest"] == s_p
                eq_s = batch_s["digest"] == s_s
                agree = s_p == s_s and batch_p["digest"] == batch_s["digest"] and eq_p and eq_s
                cells.append(
                    {
                        "range_name": range_name,
                        "cohort_size": size,
                        "cell_id": cell_id,
                        "status": "pass" if agree else "fail",
                        "primary": {
                            **p_m,
                            "log_count": n_p,
                            "identity_v2_digest": s_p,
                            "batch_digest": batch_p["digest"],
                            "batch_log_count": batch_p["log_count"],
                        },
                        "secondary": {
                            **s_m,
                            "log_count": n_s,
                            "identity_v2_digest": s_s,
                            "batch_digest": batch_s["digest"],
                            "batch_log_count": batch_s["log_count"],
                        },
                        "scalar_union_digest_primary": s_p,
                        "scalar_union_digest_secondary": s_s,
                        "batch_digest_primary": batch_p["digest"],
                        "batch_digest_secondary": batch_s["digest"],
                        "batch_equals_scalar_primary": eq_p,
                        "batch_equals_scalar_secondary": eq_s,
                        "providers_agree": agree,
                        "detail": None if agree else "batch/scalar/provider disagreement",
                    }
                )
            except MatrixSafetyStop:
                raise
            except MatrixCellFailure as exc:
                cells.append(
                    {
                        "range_name": range_name,
                        "cohort_size": size,
                        "cell_id": cell_id,
                        "status": "fail",
                        "primary": p_m,
                        "secondary": s_m,
                        "scalar_union_digest_primary": None,
                        "scalar_union_digest_secondary": None,
                        "batch_digest_primary": None,
                        "batch_digest_secondary": None,
                        "batch_equals_scalar_primary": None,
                        "batch_equals_scalar_secondary": None,
                        "providers_agree": False,
                        "detail": str(exc),
                    }
                )
            except MatrixError as exc:
                cells.append(
                    {
                        "range_name": range_name,
                        "cohort_size": size,
                        "cell_id": cell_id,
                        "status": "incomplete",
                        "primary": p_m,
                        "secondary": s_m,
                        "scalar_union_digest_primary": None,
                        "scalar_union_digest_secondary": None,
                        "batch_digest_primary": None,
                        "batch_digest_secondary": None,
                        "batch_equals_scalar_primary": None,
                        "batch_equals_scalar_secondary": None,
                        "providers_agree": None,
                        "detail": str(exc),
                    }
                )
    if len(cells) != 15:
        raise MatrixError("cell count drift", context={"observed": len(cells)})
    return cells


def _batch_digest(
    run: MatrixRun,
    plan: MatrixPlan,
    range_name: str,
    size: int,
    provider_org: str,
    addresses: Sequence[str],
    start: int,
    end: int,
) -> dict[str, Any]:
    lid = f"batch:{range_name}:{size}:{provider_org}"
    rows = run.list_receipts(lid)
    metrics = _receipt_metrics(rows)
    success = run.best_success_body(lid)
    if success is None:
        raise MatrixCellFailure(
            "batch call has no successful body",
            context={"logical_call_id": lid, "error_class": metrics["error_class"]},
        )
    body = run.load_body(success[0], expected_bytes=success[1])
    identities, digest = interpret_logs(
        body,
        domain=_domain_for(addresses=addresses, start=start, end=end, topics=plan.topics),
    )
    return {"digest": digest, "log_count": len(identities), **metrics}


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
    # Standalone replay only:
    live_run_dir: Path | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "registry_store_root", _resolve(self.registry_store_root))
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
                raise MatrixError("execute_live rejects caller-supplied provider organizations")
            if not self.confirm_matrix_id:
                raise MatrixError("execute_live requires confirm_matrix_id")
            if self.transport is None:
                if not self.primary_rpc_url or not self.secondary_rpc_url:
                    raise MatrixError("execute_live requires RPC URLs or injectable transport")
                if self.primary_rpc_url.rstrip("/") == self.secondary_rpc_url.rstrip("/"):
                    raise MatrixError("RPC URLs must be distinct")
        if self.mode == "offline_replay" and self.live_run_dir is None:
            raise MatrixError("offline_replay requires live_run_dir")


class PairEventV2MatrixHarness:
    def __init__(self, config: MatrixConfig) -> None:
        self.config = config
        self.tracker = BudgetTracker(budgets=config.budgets)
        self._gates = {
            org: _ProviderGate(
                max_in_flight=config.budgets.max_in_flight,
                rps=config.budgets.requests_per_second,
            )
            for org in config.provider_orgs
        }
        self._stop = threading.Event()
        self._safety: MatrixSafetyStop | None = None
        self._safety_lock = threading.Lock()
        self._transport = config.transport
        self._owns_transport = False
        self._closed = False
        self.active_run: MatrixRun | None = None
        # Count of started provider operations not yet finished (for drain assertions).
        self._active_provider_ops = 0
        self._provider_ops_lock = threading.Lock()
        self._provider_done = threading.Condition(self._provider_ops_lock)

    def active_provider_ops(self) -> int:
        """Number of started provider operations still in flight."""
        with self._provider_ops_lock:
            return self._active_provider_ops

    def wait_provider_idle(self, *, timeout: float | None = None) -> None:
        """Block until every started provider operation has finished (drain)."""
        deadline = None if timeout is None else (time.monotonic() + timeout)
        with self._provider_done:
            while self._active_provider_ops > 0:
                remaining = None
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise MatrixSafetyStop(
                            "provider work still active after drain timeout",
                            context={"active": self._active_provider_ops},
                        )
                self._provider_done.wait(timeout=remaining)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        # Cooperative stop then drain any started provider work before closing.
        self._stop.set()
        try:
            self.wait_provider_idle(timeout=120.0)
        except MatrixSafetyStop:
            pass
        if self._transport is not None:
            close = getattr(self._transport, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
        if self.active_run is not None:
            try:
                self.active_run.close()
            except Exception:
                pass

    def _signal(self, exc: MatrixSafetyStop) -> None:
        with self._safety_lock:
            if self._safety is None:
                self._safety = exc
        self._stop.set()
        # Wake cooperative injectables that poll attach_stop.
        transport = self._transport
        if transport is not None:
            attach = getattr(transport, "attach_stop", None)
            if callable(attach):
                try:
                    attach(self._stop)
                except Exception:
                    pass

    def _raise_if_stopped(self) -> None:
        if self._stop.is_set():
            with self._safety_lock:
                if self._safety is not None:
                    raise self._safety
            raise MatrixSafetyStop("stop signal set")

    def _ensure_transport(self) -> Any:
        if self._transport is not None:
            # Prefer cooperative stop attachment for injectables.
            attach = getattr(self._transport, "attach_stop", None)
            if callable(attach):
                try:
                    attach(self._stop)
                except Exception:
                    pass
            return self._transport
        assert self.config.primary_rpc_url and self.config.secondary_rpc_url
        self._transport = HttpxTransport(
            org_to_url={
                self.config.provider_orgs[0]: self.config.primary_rpc_url,
                self.config.provider_orgs[1]: self.config.secondary_rpc_url,
            },
            timeout_seconds=self.config.budgets.http_timeout_seconds,
        )
        self._owns_transport = True
        return self._transport

    def _begin_provider_op(self) -> None:
        with self._provider_ops_lock:
            self._active_provider_ops += 1

    def _end_provider_op(self) -> None:
        with self._provider_done:
            self._active_provider_ops = max(0, self._active_provider_ops - 1)
            self._provider_done.notify_all()

    def _invoke_provider(
        self, transport: Any, provider_org: str, request: Mapping[str, Any]
    ) -> TransportResult:
        """Invoke transport with remaining-wall timeout; drain started work on expiry."""
        timeout = self.tracker.http_timeout_seconds()
        attach = getattr(transport, "attach_stop", None)
        if callable(attach):
            try:
                attach(self._stop)
            except Exception:
                pass
        self._begin_provider_op()
        try:
            if isinstance(transport, HttpxTransport):
                return transport.begin(
                    provider_org, request, timeout_seconds=timeout
                )
            # Injectable: run on a worker thread so wall can expire, but always
            # wait for the started call to finish (cooperative stop + drain).
            box: dict[str, Any] = {}
            done = threading.Event()

            def _worker() -> None:
                try:
                    box["result"] = transport(provider_org, request)
                except BaseException as exc:  # noqa: BLE001 — propagate via box
                    box["exc"] = exc
                finally:
                    done.set()

            thread = threading.Thread(target=_worker, name="matrix-provider-call")
            thread.start()
            finished = done.wait(timeout=timeout)
            if not finished:
                # Cooperative stop so blocked injectables can exit, then drain.
                self._stop.set()
                if callable(attach):
                    try:
                        attach(self._stop)
                    except Exception:
                        pass
                done.wait()  # drain: seal only after started work finishes
                raise MatrixSafetyStop(
                    "global wall-time budget breached during provider call",
                    context={"timeout_seconds": timeout},
                )
            if "exc" in box:
                raise box["exc"]
            result = box.get("result")
            if not isinstance(result, TransportResult):
                raise MatrixError("transport must return TransportResult")
            return result
        finally:
            self._end_provider_op()

    def _execute_one(self, run: MatrixRun, call: LogicalCall) -> None:
        self._raise_if_stopped()
        existing = run.list_receipts(call.logical_call_id)
        if any(r.get("success") for r in existing):
            return
        start_attempt = len(existing) + 1
        if start_attempt == 1:
            self.tracker.register_logical_call()
        transport = self._ensure_transport()
        max_attempts = self.config.budgets.max_attempts_per_logical_call
        max_bytes = self.config.budgets.max_response_bytes
        gate = self._gates[call.provider_org]
        for attempt in range(start_attempt, max_attempts + 1):
            self._raise_if_stopped()
            self.tracker.check_wall()
            self.tracker.register_attempt()
            self.tracker.reserve(max_bytes)
            reserved = max_bytes
            gate.acquire(stop=self._stop, tracker=self.tracker)
            stream_resp = None
            transport_is_httpx = isinstance(transport, HttpxTransport)
            try:
                self._raise_if_stopped()
                self.tracker.check_wall()
                if transport_is_httpx:
                    # Provider op spans headers + full body stream (wall checked per chunk).
                    timeout = self.tracker.http_timeout_seconds()
                    self._begin_provider_op()
                    try:
                        result = transport.begin(
                            call.provider_org,
                            call.request,
                            timeout_seconds=timeout,
                        )
                        stream_resp = result.stream_response
                        if stream_resp is not None:
                            chunks = stream_resp.iter_bytes(
                                chunk_size=STREAM_CHUNK_BYTES
                            )

                            def _http_stream_abort(
                                resp: Any = stream_resp,
                                chunk_it: Any = chunks,
                                tr: Any = transport,
                            ) -> None:
                                close = getattr(resp, "close", None)
                                if callable(close):
                                    try:
                                        close()
                                    except Exception:
                                        pass
                                close_it = getattr(chunk_it, "close", None)
                                if callable(close_it):
                                    try:
                                        close_it()
                                    except Exception:
                                        pass
                                try:
                                    tr.finish(resp)
                                except Exception:
                                    pass

                            receipt = run.stream_to_receipt(
                                call=call,
                                attempt=attempt,
                                chunks_iter=chunks,
                                max_response_bytes=max_bytes,
                                status_code=result.status_code,
                                latency_ms=result.latency_ms,
                                http_429=result.http_429,
                                error_class=result.error_class,
                                error_detail=result.error_detail,
                                wall_check=self.tracker.check_wall,
                                stream_abort=_http_stream_abort,
                            )
                        else:
                            receipt = run.retain_bytes(
                                call=call,
                                attempt=attempt,
                                body=b"",
                                max_response_bytes=max_bytes,
                                status_code=result.status_code,
                                latency_ms=result.latency_ms,
                                http_429=result.http_429,
                                error_class=result.error_class or "transport",
                                error_detail=result.error_detail,
                            )
                    finally:
                        if stream_resp is not None:
                            transport.finish(stream_resp)
                            stream_resp = None
                        # End op only after stream_to_receipt joined any chunk reader.
                        self._end_provider_op()
                else:
                    result = self._invoke_provider(
                        transport, call.provider_org, call.request
                    )
                    if result.stream_response is not None:
                        # Injectable streamed body: wall checked per chunk (absolute).
                        stream_obj = result.stream_response
                        chunks = stream_obj.iter_bytes(chunk_size=STREAM_CHUNK_BYTES)

                        def _inj_stream_abort(
                            obj: Any = stream_obj, chunk_it: Any = chunks
                        ) -> None:
                            close = getattr(obj, "close", None)
                            if callable(close):
                                try:
                                    close()
                                except Exception:
                                    pass
                            close_it = getattr(chunk_it, "close", None)
                            if callable(close_it):
                                try:
                                    close_it()
                                except Exception:
                                    pass

                        self._begin_provider_op()
                        try:
                            receipt = run.stream_to_receipt(
                                call=call,
                                attempt=attempt,
                                chunks_iter=chunks,
                                max_response_bytes=max_bytes,
                                status_code=result.status_code,
                                latency_ms=result.latency_ms,
                                http_429=result.http_429,
                                error_class=result.error_class,
                                error_detail=result.error_detail,
                                wall_check=self.tracker.check_wall,
                                stream_abort=_inj_stream_abort,
                            )
                        finally:
                            # End op only after stream reader join (inside stream_to_receipt).
                            self._end_provider_op()
                    else:
                        receipt = run.retain_bytes(
                            call=call,
                            attempt=attempt,
                            body=result.body or b"",
                            max_response_bytes=max_bytes,
                            status_code=result.status_code,
                            latency_ms=result.latency_ms,
                            http_429=result.http_429,
                            error_class=result.error_class,
                            error_detail=result.error_detail,
                        )
                if receipt.get("http_429"):
                    self.tracker.note_429()
                self.tracker.commit(reserved, int(receipt.get("body_bytes") or 0))
                reserved = 0
                if receipt.get("success"):
                    return
            except MatrixSafetyStop as exc:
                if reserved:
                    try:
                        self.tracker.release(reserved)
                    except Exception:
                        pass
                self._signal(exc)
                raise
            except Exception:
                if reserved:
                    try:
                        self.tracker.release(reserved)
                    except Exception:
                        pass
                raise
            finally:
                if stream_resp is not None and transport_is_httpx:
                    try:
                        transport.finish(stream_resp)
                    except Exception:
                        pass
                gate.release()
            if attempt < max_attempts and not self._stop.is_set():
                # Backoff respects remaining wall budget.
                wait_s = min(0.5 * attempt, 30.0, self.tracker.remaining_wall_seconds())
                if wait_s <= 0:
                    raise MatrixSafetyStop("global wall-time budget breached during backoff")
                self._stop.wait(wait_s)
                self.tracker.check_wall()

    def _auth_chain(self, run: MatrixRun, plan: MatrixPlan) -> None:
        calls = [c for c in iter_logical_calls(plan) if c.kind == "chain"]
        for call in calls:
            self._execute_one(run, call)
        chain_ids: dict[str, int] = {}
        for call in calls:
            success = run.best_success_body(call.logical_call_id)
            if success is None:
                raise MatrixSafetyStop(
                    "chain authentication failed",
                    context={"provider_org": call.provider_org},
                )
            body = run.load_body(success[0], expected_bytes=success[1])
            chain_ids[call.provider_org] = interpret_chain_id(body)
        if len(set(chain_ids.values())) != 1:
            raise MatrixSafetyStop(
                "chain disagreement between providers",
                context={"chain_ids": chain_ids},
            )
        expected = _hex_quantity(ETHEREUM_MAINNET_CHAIN_ID, label="mainnet")
        if next(iter(chain_ids.values())) != expected:
            raise MatrixSafetyStop(
                "chain id is not Ethereum mainnet",
                context={"chain_ids": chain_ids},
            )

    def _execute_live_calls(self, run: MatrixRun, plan: MatrixPlan) -> None:
        self._auth_chain(run, plan)
        work = [c for c in iter_logical_calls(plan) if c.kind != "chain"]
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
                pending.add(executor.submit(self._execute_one, run, call))
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
                        self._signal(exc)
                    else:
                        self._signal(
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

    def _base_report(self, plan: MatrixPlan, *, mode: str) -> dict[str, Any]:
        return {
            "schema_version": MATRIX_SCHEMA_VERSION,
            "matrix_id": plan.matrix_id,
            "run_id": self.active_run.run_id if self.active_run else None,
            "mode": mode,
            "plan": plan.to_public_dict(),
            "budgets": self.config.budgets.as_dict(),
            "logical_call_ceiling": LOGICAL_CALL_CEILING,
            "started_at": _now_iso(),
            "pass": False,
            "complete": False,
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
        }

    def run(self) -> dict[str, Any]:
        try:
            if self.config.mode == "offline_replay":
                return self._run_standalone_replay()
            plan = build_matrix_plan(
                registry_store_root=self.config.registry_store_root,
                provider_orgs=self.config.provider_orgs,
            )
            if self.config.mode == "execute_live":
                if self.config.confirm_matrix_id != plan.matrix_id:
                    raise MatrixSafetyStop(
                        "confirm_matrix_id does not match computed matrix ID",
                        context={
                            "confirm": self.config.confirm_matrix_id,
                            "matrix_id": plan.matrix_id,
                        },
                    )
            self.active_run = MatrixRun(self.config.output_root, run_id=self.config.run_id)
            self.active_run.write_plan_and_catalog(plan)
            base = self._base_report(plan, mode=self.config.mode)

            if self.config.mode == "plan_only":
                base.update(
                    {
                        "complete": True,
                        "pass": False,
                        "detail": (
                            "plan-only complete: registry/cohort pins verified; "
                            "no RPC; matrix PASS requires live cells + offline replay"
                        ),
                        "cells": [],
                        "finished_at": _now_iso(),
                        "high_water": self.tracker.snapshot(),
                        "cumulative_counters": self.tracker.evidence_counters(),
                        "offline_replay": {
                            "kind": "not_applicable_plan_only",
                            "authenticated": False,
                            "all_cells_pass": False,
                        },
                    }
                )
                return self.active_run.seal(kind="COMPLETE", report=base)

            # execute_live — every exit path after run creation seals exactly one terminal.
            try:
                self._execute_live_calls(self.active_run, plan)
                # Drain any started provider work before seal/return.
                self.wait_provider_idle(timeout=120.0)
                if self.active_provider_ops() != 0:
                    raise MatrixSafetyStop("provider work still active before seal")
                # Pre-seal: disk-only inventory + evaluation (no caches).
                validate_run_call_inventory(self.active_run.run_dir, plan)
                disk = _ReadOnlyRun(self.active_run.run_dir)
                cells = evaluate_cells(disk, plan)  # type: ignore[arg-type]
                all_pass = all(c["status"] == "pass" for c in cells)
                incomplete = any(c["status"] == "incomplete" for c in cells)
                # In-process zero-network replay re-reads disk again.
                replay_cells = evaluate_cells(disk, plan)  # type: ignore[arg-type]
                if compute_evidence_hash({"cells": cells}) != compute_evidence_hash(
                    {"cells": replay_cells}
                ):
                    raise MatrixSafetyStop(
                        "in-process disk replay cell decisions disagree"
                    )
                in_process = {
                    "kind": "in_process_disk_replay",
                    "authenticated": True,
                    "all_cells_pass": all(c["status"] == "pass" for c in replay_cells),
                    "cell_count": len(replay_cells),
                    "cells": replay_cells,
                }
                in_process["replay_hash"] = compute_evidence_hash(in_process)
                call_metrics = _collect_call_metrics(disk, plan)
                suggested = 128 if all_pass else None
                if not all_pass:
                    for size in reversed(NESTED_COHORT_SIZES):
                        size_cells = [c for c in cells if c["cohort_size"] == size]
                        if size_cells and all(c["status"] == "pass" for c in size_cells):
                            suggested = size
                            break
                matrix_pass = bool(
                    all_pass
                    and in_process["authenticated"]
                    and in_process["all_cells_pass"]
                    and len(cells) == 15
                    and not incomplete
                )
                base.update(
                    {
                        "cells": cells,
                        "offline_replay": in_process,
                        "call_metrics": call_metrics,
                        "complete": not incomplete,
                        "pass": matrix_pass,
                        "all_cells_pass": all_pass,
                        "finished_at": _now_iso(),
                        "high_water": self.tracker.snapshot(),
                        "cumulative_counters": self.tracker.evidence_counters(),
                        "recommendation": {
                            **base["recommendation"],
                            "suggested_cohort_size": suggested,
                        },
                    }
                )
                if incomplete:
                    base["complete"] = False
                    base["pass"] = False
                    return self.active_run.seal(kind="FAILED", report=base)
                base["complete"] = True
                base["pass"] = bool(matrix_pass)
                return self.active_run.seal(kind="COMPLETE", report=base)
            except Exception as exc:
                # MatrixCellFailure, MatrixSafetyStop, and unexpected errors all seal FAILED.
                if isinstance(exc, MatrixSafetyStop):
                    self._signal(exc)
                else:
                    self._stop.set()
                # Drain started provider work before sealing (no abandonment).
                try:
                    self.wait_provider_idle(timeout=120.0)
                except MatrixSafetyStop:
                    pass
                base.update(
                    {
                        "complete": False,
                        "pass": False,
                        "safety_stop": str(exc),
                        "error_type": type(exc).__name__,
                        "finished_at": _now_iso(),
                        "high_water": self.tracker.snapshot(),
                        "cumulative_counters": self.tracker.evidence_counters(),
                        "active_provider_ops_at_seal": self.active_provider_ops(),
                    }
                )
                try:
                    disk = _ReadOnlyRun(self.active_run.run_dir)
                    base["call_metrics"] = _collect_call_metrics(disk, plan)
                    base["cells"] = evaluate_cells(disk, plan)  # type: ignore[arg-type]
                except Exception as eval_exc:
                    base["cells"] = []
                    base["cell_evaluation_error"] = type(eval_exc).__name__
                if not self.active_run.complete_path.exists() and not self.active_run.failed_path.exists():
                    sealed = self.active_run.seal(kind="FAILED", report=base)
                    sealed["active_provider_ops_at_return"] = self.active_provider_ops()
                    return sealed
                raise
        finally:
            self.close()

    def _run_standalone_replay(self) -> dict[str, Any]:
        assert self.config.live_run_dir is not None
        live_root = _resolve(self.config.live_run_dir)
        out_root = _resolve(self.config.output_root)
        if _related(out_root, live_root):
            raise MatrixSafetyStop(
                "replay output root must not equal, contain, or sit inside the live source run",
                context={"live": str(live_root), "output": str(out_root)},
            )
        before = _inventory_snapshot(live_root)
        live = authenticate_completed_run(live_root, require_live_pass=True)
        plan = MatrixPlan.from_public_dict(live["plan"])
        live_run = _ReadOnlyRun(live_root)
        cells = evaluate_cells(live_run, plan)  # type: ignore[arg-type]
        live_cells = live.get("cells")
        if compute_evidence_hash({"cells": live_cells}) != compute_evidence_hash(
            {"cells": cells}
        ):
            raise MatrixSafetyStop(
                "standalone replay cells disagree with sealed live report"
            )
        all_pass = all(c["status"] == "pass" for c in cells)
        after = _inventory_snapshot(live_root)
        if before != after:
            raise MatrixSafetyStop("live source tree changed during standalone replay")
        # Write replay result only to a new exclusive directory under output_root.
        self.active_run = MatrixRun(self.config.output_root, run_id=self.config.run_id)
        # Copy authenticated references (not rewrite live). Write minimal plan/catalog
        # for this replay run so it is self-describing, exclusive.
        self.active_run.write_plan_and_catalog(plan)
        report = {
            "schema_version": MATRIX_SCHEMA_VERSION,
            "matrix_id": plan.matrix_id,
            "run_id": self.active_run.run_id,
            "mode": "offline_replay",
            "live_run_id": live.get("run_id"),
            "live_evidence_hash": live.get("evidence_hash"),
            "live_report_hash": live.get("report_hash"),
            "live_report_authenticated": True,
            "plan": plan.to_public_dict(),
            "budgets": self.config.budgets.as_dict(),
            "cells": cells,
            "all_cells_pass": all_pass,
            "cell_count": len(cells),
            "complete": True,
            "pass": bool(all_pass and len(cells) == 15),
            "started_at": _now_iso(),
            "finished_at": _now_iso(),
            "high_water": self.tracker.snapshot(),
            "cumulative_counters": self.tracker.evidence_counters(),
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
            "credential_scan": "pass",
            "call_metrics": _collect_call_metrics(live_run, plan),
            "offline_replay": {
                "kind": "standalone_read_only",
                "authenticated": True,
                "all_cells_pass": all_pass,
                "live_run_dir": str(live_root),
                "source_inventory_sha256": _sha256_text(_canonical_json(before)),
            },
        }
        sealed = self.active_run.seal(kind="COMPLETE", report=report)
        # Live source must remain immutable after replay seal as well.
        if _inventory_snapshot(live_root) != before:
            raise MatrixSafetyStop("live source tree changed after standalone replay seal")
        return sealed


class _ReadOnlyRun:
    """Minimal adapter so evaluate_cells can read a sealed live run directory."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.receipts_dir = run_dir / "receipts"
        self.raw_dir = run_dir / "raw"
        self.run_id = run_dir.name

    def list_receipts(self, logical_call_id: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in sorted(
            self.receipts_dir.glob(f"{logical_call_id.replace(':', '__')}__a*.json")
        ):
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        return rows

    def best_success_body(self, logical_call_id: str) -> tuple[str, int] | None:
        best: tuple[str, int] | None = None
        for rec in self.list_receipts(logical_call_id):
            if rec.get("success") and rec.get("body_sha256"):
                best = (str(rec["body_sha256"]), int(rec["body_bytes"]))
        return best

    def load_body(self, body_sha256: str, *, expected_bytes: int | None = None) -> bytes:
        if not _SHA256_RE.fullmatch(body_sha256):
            raise MatrixSafetyStop("invalid body sha256")
        path = self.raw_dir / f"{body_sha256}.bin"
        if not path.is_file():
            raise MatrixSafetyStop("retained body missing")
        data = path.read_bytes()
        if _sha256_bytes(data) != body_sha256:
            raise MatrixSafetyStop("retained body SHA-256 mismatch")
        if expected_bytes is not None and len(data) != expected_bytes:
            raise MatrixSafetyStop("retained body byte count mismatch")
        return data


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
    "STREAM_CHUNK_BYTES",
    "BudgetTracker",
    "HttpxTransport",
    "LogicalCall",
    "MatrixBudgets",
    "MatrixConfig",
    "MatrixError",
    "MatrixPlan",
    "MatrixRun",
    "MatrixSafetyStop",
    "PairEventV2MatrixHarness",
    "TransportResult",
    "assert_safe_matrix_output_root",
    "authenticate_completed_run",
    "build_matrix_plan",
    "catalog_entries",
    "compact_json_array_hash",
    "compute_evidence_hash",
    "compute_report_hash",
    "evaluate_cells",
    "iter_logical_calls",
    "parse_json_rpc_result",
    "plan_only",
    "select_matrix_maximum_cohort",
    "validate_run_call_inventory",
    "verify_and_load_accepted_registry",
    "verify_pinned_cohort_hashes",
]
