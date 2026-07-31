"""DATA-012 Uniswap V2 Factory PairCreated raw-event ingestion.

Acquisition preserves exact JSON-RPC response bytes through ``RawObjectWriter`` and
records a chunk receipt that binds every dependency to the request that produced it.
Decoding never touches the network: ``replay_receipts`` reads only preserved bytes,
re-derives the request each receipt claims to answer, verifies SHA-256, and proves
contiguous coverage before returning rows.

Chain safety is explicit. The ingestor refuses to run against anything but Ethereum
mainnet (``eth_chainId == 0x1``) and refuses block ranges that begin before the
Uniswap V2 Factory deployment block, because logs from before deployment cannot
exist and a range that claims them indicates a misconfigured run.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from cryptofactors.ingest.raw.models import AcquisitionMetadata
from cryptofactors.ingest.raw.paths import content_addressed_absolute_path
from cryptofactors.ingest.raw.writer import RawObjectWriter

ETHEREUM_CHAIN = "ethereum"
ETHEREUM_MAINNET_CHAIN_ID = "0x1"
UNISWAP_V2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
UNISWAP_V2_DEPLOYMENT_BLOCK = 10_000_835
PAIR_CREATED_TOPIC = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"
SOURCE_ID = "ethereum_json_rpc_uniswap_v2"
DEFAULT_PROVIDER_ID = "rpc_primary"

RECEIPT_TABLE = "uniswap_v2_pair_created_chunk_receipt_v3"
FAILURE_TABLE = "uniswap_v2_pair_created_transport_failure"

# Default batching / concurrency for eth_getBlockByNumber (event-block headers).
DEFAULT_HEADER_BATCH_SIZE = 64
DEFAULT_HEADER_MAX_IN_FLIGHT = 4
DEFAULT_HEADER_REQUESTS_PER_SECOND = 20.0

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
_ADDRESS_PAD = "0" * 24


class UniswapV2IngestionError(RuntimeError):
    """Raised for malformed RPC responses or invalid event continuity."""


# ---------------------------------------------------------------------------
# Validation primitives
#
# Every accessor below converts a malformed node response into a typed failure.
# A bare KeyError or ValueError escaping this module is indistinguishable from a
# programming fault at the call site.
# ---------------------------------------------------------------------------

def _require(source: Mapping[str, Any], key: str, *, label: str) -> Any:
    if not isinstance(source, Mapping) or key not in source:
        raise UniswapV2IngestionError(f"{label} is missing {key!r}")
    return source[key]


def _hex_quantity(value: Any, *, label: str) -> int:
    """Decode a JSON-RPC QUANTITY.

    Non-canonical zero padding is tolerated (some providers emit it) but the value
    must be a ``0x``-prefixed, non-empty, purely hexadecimal string. A JSON number
    is rejected: silently accepting it would let a provider change the wire type
    without detection.
    """
    if not isinstance(value, str):
        raise UniswapV2IngestionError(f"{label} must be a hex quantity string, got {value!r}")
    if not value.startswith("0x") or len(value) == 2:
        raise UniswapV2IngestionError(f"expected hex quantity, got {value!r}")
    body = value[2:]
    if any(char not in _HEX_DIGITS for char in body):
        raise UniswapV2IngestionError(f"expected hex quantity, got {value!r}")
    return int(body, 16)


def _hex_bytes(value: Any, size: int, *, label: str) -> str:
    """Decode a fixed-width DATA value, returning it lowercase-normalised."""
    if not isinstance(value, str) or not value.startswith("0x"):
        raise UniswapV2IngestionError(f"{label} must be 0x-prefixed hex, got {value!r}")
    body = value[2:]
    if len(body) != size * 2:
        raise UniswapV2IngestionError(
            f"{label} must be exactly {size} bytes, got {len(body) // 2}"
        )
    if any(char not in _HEX_DIGITS for char in body):
        raise UniswapV2IngestionError(f"{label} is not valid hex: {value!r}")
    return "0x" + body.lower()


def _abi_address(word: Any, *, label: str) -> str:
    """Extract a 20-byte address from a 32-byte ABI word, rejecting dirty padding."""
    normalized = _hex_bytes(word, 32, label=label)
    if normalized[2:26] != _ADDRESS_PAD:
        raise UniswapV2IngestionError(f"{label} is not a left-padded 20-byte address")
    return "0x" + normalized[26:]


def _same_address(left: str, right: str) -> bool:
    return left.lower() == right.lower()


# Retained so existing callers keep working; both delegate to the strict helpers.
def _hex_int(value: str) -> int:
    return _hex_quantity(value, label="quantity")


def _address(topic_or_word: str) -> str:
    return _abi_address(topic_or_word, label="ABI word")


def _canonical_json(payload: Any) -> str:
    """Stable request encoding, so a recorded request compares byte-for-byte."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Canonical JSON-RPC requests
#
# Replay re-derives these from the receipt's own identity columns and compares
# them to what was recorded, which is what makes replay request-bound.
# ---------------------------------------------------------------------------

def chain_id_request() -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}


def logs_request(*, factory: str, start_block: int, end_block: int) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getLogs",
        "params": [{
            "address": factory,
            "fromBlock": hex(start_block),
            "toBlock": hex(end_block),
            "topics": [PAIR_CREATED_TOPIC],
        }],
    }


def block_header_request(block_number: int) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getBlockByNumber",
        "params": [hex(block_number), False],
    }


def block_header_batch_request(block_numbers: Sequence[int]) -> list[dict[str, Any]]:
    """Build a JSON-RPC batch of eth_getBlockByNumber calls with distinct ids.

    ``id`` equals the index in the request array so a dependency's ``batch_index``
    can locate the matching request element. Responses must be correlated by
    ``id``, never by position — servers may reorder batch replies.
    """
    return [{**block_header_request(number), "id": index} for index, number in enumerate(block_numbers)]


def header_request_core(request: Mapping[str, Any]) -> dict[str, Any]:
    """JSON-RPC header request identity ignoring the correlation ``id`` field."""
    if not isinstance(request, Mapping):
        raise UniswapV2IngestionError("header request element must be an object")
    return {
        "jsonrpc": request.get("jsonrpc"),
        "method": request.get("method"),
        "params": request.get("params"),
    }


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PairCreatedRow:
    chain: str
    factory: str
    pair: str
    token0: str
    token1: str
    block_number: int
    block_hash: str
    block_timestamp: int
    tx_hash: str
    tx_index: int
    log_index: int
    event_time: datetime
    availability_time: datetime
    raw_object_id: str
    block_raw_object_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "factory": self.factory,
            "pair": self.pair,
            "token0": self.token0,
            "token1": self.token1,
            "block_number": self.block_number,
            "block_hash": self.block_hash,
            "block_timestamp": self.block_timestamp,
            "tx_hash": self.tx_hash,
            "tx_index": self.tx_index,
            "log_index": self.log_index,
            "event_time": self.event_time.isoformat(),
            "availability_time": self.availability_time.isoformat(),
            "raw_object_id": self.raw_object_id,
            "block_raw_object_id": self.block_raw_object_id,
        }


@dataclass(frozen=True, slots=True)
class RpcCall:
    """One acquisition attempt that produced preserved bytes."""

    request: dict[str, Any]
    payload: dict[str, Any]
    raw_object_id: str
    acquisition_id: str
    acquired_at: datetime

    @property
    def request_json(self) -> str:
        return _canonical_json(self.request)


@dataclass(frozen=True, slots=True)
class RpcBatchCall:
    """One JSON-RPC batch acquisition that produced preserved array bytes."""

    request: list[dict[str, Any]]
    payload: list[Any]
    raw_object_id: str
    acquisition_id: str
    acquired_at: datetime

    @property
    def request_json(self) -> str:
        return _canonical_json(self.request)


@dataclass(frozen=True, slots=True)
class CachedHeader:
    """Finalized block header retained for cross-chunk reuse."""

    block_number: int
    header: dict[str, Any]
    block_hash: str
    request_json: str
    raw_object_id: str
    acquisition_id: str
    acquired_at: str
    batch_index: int | None
    provider_id: str


class _TokenBucket:
    """Thread-safe token bucket limiting request starts per provider."""

    def __init__(self, *, rate: float, capacity: float) -> None:
        if rate <= 0 or capacity <= 0:
            raise ValueError("token bucket rate and capacity must be positive")
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._updated
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
                self._updated = now
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                wait = (tokens - self._tokens) / self._rate
            time.sleep(wait)


def find_batch_response_by_id(payload: Sequence[Any], request_id: Any) -> Mapping[str, Any]:
    """Locate one batch response element by JSON-RPC id (never by position)."""
    matches = [
        item for item in payload
        if isinstance(item, Mapping) and item.get("id") == request_id
    ]
    if len(matches) != 1:
        raise UniswapV2IngestionError(
            f"expected exactly one batch response for id={request_id!r}, got {len(matches)}"
        )
    return matches[0]


@dataclass(frozen=True, slots=True)
class HeaderDependency:
    """A preserved block header bound to the request that produced it.

    ``batch_index`` is ``None`` when ``raw_object_id`` holds a single JSON-RPC
    response object (legacy / sequential path). When set, the raw object is a
    JSON-RPC batch response array and ``batch_index`` indexes the request
    element in ``request_json`` (also a batch array). Responses are matched by
    request ``id``, never by array position.
    """

    block_number: int
    block_hash: str
    request_json: str
    raw_object_id: str
    acquisition_id: str
    acquired_at: str
    batch_index: int | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "block_number": self.block_number,
            "block_hash": self.block_hash,
            "request_json": self.request_json,
            "raw_object_id": self.raw_object_id,
            "acquisition_id": self.acquisition_id,
            "acquired_at": self.acquired_at,
        }
        # Omit when None so pilot / pre-batch receipts stay byte-stable on rewrite.
        if self.batch_index is not None:
            payload["batch_index"] = self.batch_index
        return payload

    @classmethod
    def from_dict(cls, payload: Any) -> HeaderDependency:
        if not isinstance(payload, Mapping):
            raise UniswapV2IngestionError("header dependency must be an object")
        batch_index_raw = payload.get("batch_index")
        batch_index = None if batch_index_raw is None else int(batch_index_raw)
        return cls(
            block_number=int(_require(payload, "block_number", label="header dependency")),
            block_hash=str(_require(payload, "block_hash", label="header dependency")),
            request_json=str(_require(payload, "request_json", label="header dependency")),
            raw_object_id=str(_require(payload, "raw_object_id", label="header dependency")),
            acquisition_id=str(_require(payload, "acquisition_id", label="header dependency")),
            acquired_at=str(_require(payload, "acquired_at", label="header dependency")),
            batch_index=batch_index,
        )


@dataclass(frozen=True, slots=True)
class AcquisitionRecord:
    """A `raw_acquisition` row, used to authenticate what a receipt claims."""

    acquisition_id: str
    raw_object_id: str | None
    request_json: str
    acquired_at: str
    status: str


@dataclass(frozen=True, slots=True)
class ChunkReceipt:
    """A completed chunk, bound to every acquisition that produced it."""

    chain: str
    chain_id: str
    factory: str
    topic: str
    start_block: int
    end_block: int
    logs_request_json: str
    logs_raw_object_id: str
    logs_acquisition_id: str
    logs_acquired_at: str
    end_block_number: int
    end_block_hash: str
    end_header_request_json: str
    end_header_raw_object_id: str
    end_header_acquisition_id: str
    end_header_acquired_at: str
    header_dependencies: tuple[HeaderDependency, ...]
    completed_at: str
    chain_id_request_json: str
    chain_id_raw_object_id: str
    chain_id_acquisition_id: str
    chain_id_acquired_at: str

    @property
    def raw_object_ids(self) -> frozenset[str]:
        return frozenset({
            self.logs_raw_object_id,
            self.end_header_raw_object_id,
            self.chain_id_raw_object_id,
            *(dep.raw_object_id for dep in self.header_dependencies),
        })

    @property
    def acquisition_ids(self) -> frozenset[str]:
        return frozenset({
            self.logs_acquisition_id,
            self.end_header_acquisition_id,
            self.chain_id_acquisition_id,
            *(dep.acquisition_id for dep in self.header_dependencies),
        })


@dataclass(frozen=True, slots=True)
class ReplayResult:
    rows: tuple[PairCreatedRow, ...]
    raw_object_ids: frozenset[str]
    completed_ranges: tuple[tuple[int, int], ...]
    acquisition_ids: frozenset[str] = frozenset()


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------

def decode_pair_created(
    logs_response: Mapping[str, Any],
    block_headers: Mapping[int, tuple[Mapping[str, Any], str]],
    *,
    factory: str,
    log_raw_object_id: str,
    availability_time: datetime,
) -> list[PairCreatedRow]:
    """Pure deterministic decoder for replaying preserved RPC response bytes.

    Strict by construction: a log is accepted only if it was emitted by the expected
    factory, is not a reorg tombstone, carries exactly the PairCreated topic set, and
    agrees with the preserved header on both block number and block hash. Duplicate
    detection is case-normalised, because hash casing is not stable across providers.
    """
    logs = logs_response.get("result") if isinstance(logs_response, Mapping) else None
    if not isinstance(logs, list):
        raise UniswapV2IngestionError("eth_getLogs result must be a list")

    seen: set[tuple[str, int]] = set()
    rows: list[PairCreatedRow] = []
    for log in logs:
        if not isinstance(log, Mapping):
            raise UniswapV2IngestionError("log entry must be an object")

        emitter = _require(log, "address", label="log")
        if not isinstance(emitter, str) or not _same_address(emitter, factory):
            raise UniswapV2IngestionError(
                f"log emitted by {emitter!r}, expected factory {factory}"
            )

        removed = _require(log, "removed", label="log")
        if removed is not False:
            raise UniswapV2IngestionError("reorg-removed log cannot be published")

        topics = log.get("topics")
        if not isinstance(topics, list) or len(topics) != 3:
            raise UniswapV2IngestionError("invalid PairCreated topics")
        event_topic = _hex_bytes(topics[0], 32, label="event topic")
        if event_topic != PAIR_CREATED_TOPIC:
            raise UniswapV2IngestionError("invalid PairCreated topics")

        block_number = _hex_quantity(_require(log, "blockNumber", label="log"), label="blockNumber")
        if block_number not in block_headers:
            raise UniswapV2IngestionError(f"no preserved block header for block {block_number}")
        header, header_raw_object_id = block_headers[block_number]

        header_number = _hex_quantity(
            _require(header, "number", label="block header"), label="header number"
        )
        if header_number != block_number:
            raise UniswapV2IngestionError(
                f"preserved header is for block {header_number}, not {block_number}"
            )

        block_hash = _hex_bytes(_require(log, "blockHash", label="log"), 32, label="log blockHash")
        header_hash = _hex_bytes(
            _require(header, "hash", label="block header"), 32, label="header hash"
        )
        if block_hash != header_hash:
            raise UniswapV2IngestionError("log block hash does not match block header")

        tx_hash = _hex_bytes(
            _require(log, "transactionHash", label="log"), 32, label="transactionHash"
        )
        log_index = _hex_quantity(_require(log, "logIndex", label="log"), label="logIndex")
        identity = (tx_hash, log_index)
        if identity in seen:
            raise UniswapV2IngestionError("duplicate (tx_hash, log_index)")
        seen.add(identity)

        # PairCreated(address indexed token0, address indexed token1, address pair, uint)
        data = _hex_bytes(_require(log, "data", label="log"), 64, label="log data")
        timestamp = _hex_quantity(
            _require(header, "timestamp", label="block header"), label="block timestamp"
        )
        rows.append(PairCreatedRow(
            chain=ETHEREUM_CHAIN,
            factory=factory,
            pair=_abi_address(data[:66], label="pair"),
            token0=_abi_address(topics[1], label="token0"),
            token1=_abi_address(topics[2], label="token1"),
            block_number=block_number,
            block_hash=block_hash,
            block_timestamp=timestamp,
            tx_hash=tx_hash,
            tx_index=_hex_quantity(
                _require(log, "transactionIndex", label="log"), label="transactionIndex"
            ),
            log_index=log_index,
            event_time=datetime.fromtimestamp(timestamp, UTC),
            availability_time=availability_time,
            raw_object_id=log_raw_object_id,
            block_raw_object_id=header_raw_object_id,
        ))
    return sorted(rows, key=lambda row: (row.block_number, row.tx_index, row.log_index))


# ---------------------------------------------------------------------------
# Receipt persistence
# ---------------------------------------------------------------------------

_RECEIPT_COLUMNS = (
    "chain", "chain_id", "factory", "topic", "start_block", "end_block",
    "logs_request_json", "logs_raw_object_id", "logs_acquisition_id", "logs_acquired_at",
    "end_block_number", "end_block_hash", "end_header_request_json",
    "end_header_raw_object_id", "end_header_acquisition_id", "end_header_acquired_at",
    "header_dependencies_json", "completed_at",
    "chain_id_request_json", "chain_id_raw_object_id", "chain_id_acquisition_id",
    "chain_id_acquired_at",
)


def _receipt_from_row(row: Sequence[Any]) -> ChunkReceipt:
    try:
        parsed = json.loads(str(row[16]))
    except json.JSONDecodeError as exc:
        raise UniswapV2IngestionError("receipt header dependency list is not valid JSON") from exc
    if not isinstance(parsed, list):
        raise UniswapV2IngestionError("receipt header dependency list must be a JSON array")
    dependencies = tuple(HeaderDependency.from_dict(item) for item in parsed)
    # One block, one header. A repeat is a provider inconsistency; a repeat with a
    # different hash means two different chains answered for the same height.
    by_block: dict[int, HeaderDependency] = {}
    for dependency in dependencies:
        previous = by_block.get(dependency.block_number)
        if previous is not None:
            if previous.block_hash != dependency.block_hash:
                raise UniswapV2IngestionError(
                    f"conflicting header dependencies for block {dependency.block_number}: "
                    f"{previous.block_hash} and {dependency.block_hash}"
                )
            raise UniswapV2IngestionError(
                f"duplicate header dependency for block {dependency.block_number}"
            )
        by_block[dependency.block_number] = dependency
    return ChunkReceipt(
        chain=str(row[0]),
        chain_id=str(row[1]),
        factory=str(row[2]),
        topic=str(row[3]),
        start_block=int(row[4]),
        end_block=int(row[5]),
        logs_request_json=str(row[6]),
        logs_raw_object_id=str(row[7]),
        logs_acquisition_id=str(row[8]),
        logs_acquired_at=str(row[9]),
        end_block_number=int(row[10]),
        end_block_hash=str(row[11]),
        end_header_request_json=str(row[12]),
        end_header_raw_object_id=str(row[13]),
        end_header_acquisition_id=str(row[14]),
        end_header_acquired_at=str(row[15]),
        header_dependencies=dependencies,
        completed_at=str(row[17]),
        chain_id_request_json=str(row[18]),
        chain_id_raw_object_id=str(row[19]),
        chain_id_acquisition_id=str(row[20]),
        chain_id_acquired_at=str(row[21]),
    )


def _load_acquisitions(
    conn: sqlite3.Connection, acquisition_ids: Sequence[str]
) -> dict[str, AcquisitionRecord]:
    """Read the `raw_acquisition` rows a receipt claims to be backed by."""
    records: dict[str, AcquisitionRecord] = {}
    unique = sorted({str(item) for item in acquisition_ids if item})
    for index in range(0, len(unique), 500):
        batch = unique[index:index + 500]
        placeholders = ", ".join("?" for _ in batch)
        for row in conn.execute(
            "SELECT acquisition_id, raw_object_id, request_json, acquired_at, status "
            f"FROM raw_acquisition WHERE acquisition_id IN ({placeholders})",
            tuple(batch),
        ):
            records[str(row[0])] = AcquisitionRecord(
                acquisition_id=str(row[0]),
                raw_object_id=None if row[1] is None else str(row[1]),
                request_json=str(row[2]),
                acquired_at=str(row[3]),
                status=str(row[4]),
            )
    return records


def _authenticate_acquisition(
    records: Mapping[str, AcquisitionRecord],
    *,
    acquisition_id: str,
    raw_object_id: str,
    request_json: str,
    acquired_at: str,
    label: str,
) -> None:
    """Prove a receipt's claim is backed by a real, successful, matching acquisition.

    A receipt is a claim; `raw_acquisition` is the independent record of what was
    actually retrieved. Without this check a receipt could name any acquisition id --
    or one belonging to a different request -- and replay would never notice.
    """
    if not acquisition_id:
        raise UniswapV2IngestionError(f"{label} records no acquisition id")
    record = records.get(acquisition_id)
    if record is None:
        raise UniswapV2IngestionError(
            f"{label} references acquisition {acquisition_id} with no raw_acquisition row"
        )
    if record.status != "SUCCEEDED":
        raise UniswapV2IngestionError(
            f"{label} references acquisition {acquisition_id} with status {record.status}"
        )
    if record.raw_object_id != raw_object_id:
        raise UniswapV2IngestionError(
            f"{label} claims raw object {raw_object_id} but acquisition "
            f"{acquisition_id} produced {record.raw_object_id}"
        )
    try:
        recorded_request = json.loads(record.request_json)
    except json.JSONDecodeError as exc:
        raise UniswapV2IngestionError(
            f"acquisition {acquisition_id} has an unreadable request record"
        ) from exc
    if recorded_request != json.loads(request_json):
        raise UniswapV2IngestionError(
            f"{label} answers a different request than acquisition {acquisition_id} made"
        )
    claimed = _parse_timestamp(acquired_at, label=f"{label} acquired_at")
    actual = _parse_timestamp(record.acquired_at, label=f"acquisition {acquisition_id} acquired_at")
    if claimed != actual:
        raise UniswapV2IngestionError(
            f"{label} claims acquisition time {claimed.isoformat()} but acquisition "
            f"{acquisition_id} was recorded at {actual.isoformat()}"
        )


def _parse_timestamp(value: str, *, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise UniswapV2IngestionError(f"{label} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise UniswapV2IngestionError(f"{label} must be timezone-aware")
    return parsed


class UniswapV2PairCreatedIngestor:
    """Resumable, gap-checked PairCreated JSON-RPC acquisition only."""

    def __init__(
        self,
        *,
        rpc_url: str,
        raw_writer: RawObjectWriter,
        client: httpx.Client | None = None,
        factory: str = UNISWAP_V2_FACTORY,
        raw_root: Path | None = None,
        provider_id: str = DEFAULT_PROVIDER_ID,
        finality_cutoff_block: int | None = None,
        header_batch_size: int = DEFAULT_HEADER_BATCH_SIZE,
        header_max_in_flight: int = DEFAULT_HEADER_MAX_IN_FLIGHT,
        header_requests_per_second: float = DEFAULT_HEADER_REQUESTS_PER_SECOND,
        use_header_batches: bool = True,
    ) -> None:
        if not rpc_url:
            raise ValueError("rpc_url is required")
        if not provider_id:
            raise ValueError("provider_id is required")
        if header_batch_size <= 0:
            raise ValueError("header_batch_size must be positive")
        if header_max_in_flight <= 0:
            raise ValueError("header_max_in_flight must be positive")
        if header_requests_per_second <= 0:
            raise ValueError("header_requests_per_second must be positive")
        if (
            finality_cutoff_block is not None
            and finality_cutoff_block < UNISWAP_V2_DEPLOYMENT_BLOCK
        ):
            raise ValueError(
                "finality_cutoff_block must be >= Uniswap V2 deployment block when set"
            )
        self._rpc_url = rpc_url
        self._raw_writer = raw_writer
        self._client = client or httpx.Client(timeout=30.0)
        self._owns_client = client is None
        self._factory = factory
        self._raw_root = raw_root
        self._provider_id = provider_id
        self._chain_id: str | None = None
        self._chain_call: RpcCall | None = None
        self._finality_cutoff_block = finality_cutoff_block
        self._header_batch_size = header_batch_size
        self._header_max_in_flight = header_max_in_flight
        self._use_header_batches = use_header_batches
        self._header_bucket = _TokenBucket(
            rate=header_requests_per_second, capacity=float(header_max_in_flight)
        )
        self._header_cache: dict[tuple[str, int], CachedHeader] = {}
        self._header_cache_lock = threading.Lock()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def clear_header_cache(self) -> None:
        with self._header_cache_lock:
            self._header_cache.clear()

    # -- transport ---------------------------------------------------------

    def _record_failure(
        self,
        receipts: sqlite3.Connection | None,
        *,
        method: str,
        request_json: str,
        start_block: int,
        end_block: int,
        kind: str,
        detail: str,
        status_code: int | None = None,
        raw_object_id: str | None = None,
        acquisition_id: str | None = None,
    ) -> None:
        """Record a failed acquisition attempt as durable evidence.

        Best effort by design: a failure to write the failure row must not mask the
        original transport error the caller is about to see.
        """
        if receipts is None:
            return
        try:
            receipts.execute(
                f"INSERT INTO {FAILURE_TABLE} "
                "(chain, factory, topic, method, request_json, start_block, end_block, "
                "failure_kind, status_code, raw_object_id, acquisition_id, detail, occurred_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ETHEREUM_CHAIN, self._factory, PAIR_CREATED_TOPIC, method, request_json,
                 start_block, end_block, kind, status_code, raw_object_id, acquisition_id,
                 detail, datetime.now(UTC).isoformat()),
            )
            receipts.commit()
        except sqlite3.Error:
            return

    def _rpc(
        self,
        request: Mapping[str, Any],
        *,
        event_start: int,
        event_end: int,
        receipts: sqlite3.Connection | None,
    ) -> RpcCall:
        method = str(_require(request, "method", label="rpc request"))
        request_json = _canonical_json(request)
        acquired_at = datetime.now(UTC)

        try:
            response = self._client.post(self._rpc_url, json=dict(request))
        except httpx.HTTPError as exc:
            detail = f"transport failure: {exc}"
            # No bytes were received, so there is nothing to preserve; the attempt is
            # still recorded so a gap in coverage is explainable after the fact.
            self._raw_writer.record_failed_acquisition(
                AcquisitionMetadata(
                    source_id=SOURCE_ID, request=dict(request), acquired_at=acquired_at
                ),
                detail,
            )
            self._record_failure(
                receipts, method=method, request_json=request_json, start_block=event_start,
                end_block=event_end, kind="transport", detail=detail,
            )
            raise UniswapV2IngestionError(f"JSON-RPC {method} transport failure") from exc

        body = response.content
        acquired_at = datetime.now(UTC)
        raw = self._raw_writer.write_stream(
            [body],
            AcquisitionMetadata(
                source_id=SOURCE_ID,
                request=dict(request),
                response_metadata={"status_code": response.status_code, "method": method},
                original_name=f"{method}_{event_start}_{event_end}.json",
                acquired_at=acquired_at,
            ),
        )

        if response.is_error:
            detail = f"JSON-RPC HTTP {response.status_code}"
            self._record_failure(
                receipts, method=method, request_json=request_json, start_block=event_start,
                end_block=event_end, kind="http_status", detail=detail,
                status_code=response.status_code, raw_object_id=raw.raw_object_id,
                acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            detail = f"JSON-RPC {method} returned invalid JSON"
            self._record_failure(
                receipts, method=method, request_json=request_json, start_block=event_start,
                end_block=event_end, kind="invalid_json", detail=detail,
                status_code=response.status_code, raw_object_id=raw.raw_object_id,
                acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail) from exc

        if not isinstance(payload, dict):
            detail = f"JSON-RPC {method} response must be an object"
            self._record_failure(
                receipts, method=method, request_json=request_json, start_block=event_start,
                end_block=event_end, kind="invalid_json", detail=detail,
                status_code=response.status_code, raw_object_id=raw.raw_object_id,
                acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail)

        if payload.get("error") is not None:
            detail = f"JSON-RPC {method} failed: {payload['error']!r}"
            self._record_failure(
                receipts, method=method, request_json=request_json, start_block=event_start,
                end_block=event_end, kind="rpc_error", detail=detail,
                status_code=response.status_code, raw_object_id=raw.raw_object_id,
                acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail)

        return RpcCall(
            request=dict(request),
            payload=payload,
            raw_object_id=raw.raw_object_id,
            acquisition_id=raw.acquisition_id,
            acquired_at=acquired_at,
        )

    @staticmethod
    def _assert_mainnet_payload(payload: Mapping[str, Any]) -> str:
        raw_chain_id = payload.get("result")
        if _hex_quantity(raw_chain_id, label="eth_chainId result") != 1:
            raise UniswapV2IngestionError(
                f"expected Ethereum mainnet chain id {ETHEREUM_MAINNET_CHAIN_ID}, "
                f"got {raw_chain_id!r}"
            )
        return ETHEREUM_MAINNET_CHAIN_ID

    def _assert_mainnet(self, receipts: sqlite3.Connection | None) -> RpcCall:
        """Refuse to ingest mainnet addresses from a non-mainnet endpoint.

        The response is a preserved acquisition, not a throwaway preflight: every
        receipt records it so replay can re-prove the chain identity offline.
        """
        if self._chain_call is not None:
            return self._chain_call
        call = self._rpc(chain_id_request(), event_start=0, event_end=0, receipts=receipts)
        self._chain_id = self._assert_mainnet_payload(call.payload)
        self._chain_call = call
        return call

    # -- preserved bytes ---------------------------------------------------

    def _resolve_raw_root(self, raw_root: Path | None) -> Path:
        resolved = raw_root if raw_root is not None else self._raw_root
        if resolved is None:
            raise UniswapV2IngestionError(
                "raw_root is required to verify preserved dependencies; pass it to the "
                "ingestor or to the call"
            )
        return resolved

    @staticmethod
    def _read_raw_bytes(raw_root: Path, raw_object_id: str) -> Any:
        if not raw_object_id.startswith("raw_"):
            raise UniswapV2IngestionError("invalid raw object id")
        digest = raw_object_id.removeprefix("raw_")
        path = content_addressed_absolute_path(raw_root, digest)
        try:
            body = path.read_bytes()
        except OSError as exc:
            raise UniswapV2IngestionError(f"cannot replay raw object {raw_object_id}") from exc
        if hashlib.sha256(body).hexdigest() != digest:
            raise UniswapV2IngestionError(f"raw object SHA-256 mismatch: {raw_object_id}")
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise UniswapV2IngestionError(f"cannot replay raw object {raw_object_id}") from exc

    @classmethod
    def _read_raw_json(cls, raw_root: Path, raw_object_id: str) -> dict[str, Any]:
        """Read a single JSON-RPC response object (strict)."""
        decoded = cls._read_raw_bytes(raw_root, raw_object_id)
        if not isinstance(decoded, dict):
            raise UniswapV2IngestionError("raw RPC response must be an object")
        return decoded

    @classmethod
    def _read_raw_batch(cls, raw_root: Path, raw_object_id: str) -> list[Any]:
        """Read a JSON-RPC batch response array (strict)."""
        decoded = cls._read_raw_bytes(raw_root, raw_object_id)
        if not isinstance(decoded, list):
            raise UniswapV2IngestionError("raw RPC batch response must be an array")
        return decoded

    def _authenticate_header(
        self,
        raw_root: Path,
        *,
        raw_object_id: str,
        request_json: str,
        expected_block_number: int,
        expected_block_hash: str | None,
        label: str,
        batch_index: int | None = None,
    ) -> dict[str, Any]:
        """Prove a preserved header answers the request the receipt claims, for the
        block the receipt claims, with the hash the receipt claims.

        ``batch_index is None``: single JSON-RPC object (pilot / sequential path).
        Otherwise ``request_json`` and the raw object are batch arrays; the element
        is located by request id, never by response array position.
        """
        expected_core = header_request_core(block_header_request(expected_block_number))
        if batch_index is None:
            expected_request = _canonical_json(block_header_request(expected_block_number))
            if request_json != expected_request:
                raise UniswapV2IngestionError(
                    f"{label} was acquired by a different request than the receipt claims"
                )
            response = self._read_raw_json(raw_root, raw_object_id)
            header = response.get("result")
        else:
            try:
                request_batch = json.loads(request_json)
            except json.JSONDecodeError as exc:
                raise UniswapV2IngestionError(
                    f"{label} batch request_json is not valid JSON"
                ) from exc
            if not isinstance(request_batch, list):
                raise UniswapV2IngestionError(
                    f"{label} batch request_json must be a JSON array"
                )
            if batch_index < 0 or batch_index >= len(request_batch):
                raise UniswapV2IngestionError(
                    f"{label} batch_index {batch_index} out of range for request batch "
                    f"of length {len(request_batch)}"
                )
            element = request_batch[batch_index]
            if not isinstance(element, Mapping):
                raise UniswapV2IngestionError(
                    f"{label} batch request element must be an object"
                )
            if header_request_core(element) != expected_core:
                raise UniswapV2IngestionError(
                    f"{label} batch request element does not match "
                    f"block_header_request({expected_block_number}) ignoring id"
                )
            response_batch = self._read_raw_batch(raw_root, raw_object_id)
            response = find_batch_response_by_id(response_batch, element.get("id"))
            header = response.get("result")

        if not isinstance(header, dict):
            raise UniswapV2IngestionError(f"{label} raw object has no block result")
        number = _hex_quantity(_require(header, "number", label=label), label=f"{label} number")
        if number != expected_block_number:
            raise UniswapV2IngestionError(
                f"{label} is for block {number}, expected {expected_block_number}"
            )
        block_hash = _hex_bytes(_require(header, "hash", label=label), 32, label=f"{label} hash")
        if expected_block_hash is not None and block_hash != _hex_bytes(
            expected_block_hash, 32, label=f"{label} recorded hash"
        ):
            raise UniswapV2IngestionError(f"{label} hash does not match the receipt")
        return header

    def _verify_chain_lineage(
        self,
        receipt: ChunkReceipt,
        raw_root: Path,
        acquisitions: Mapping[str, AcquisitionRecord],
    ) -> None:
        """Re-prove mainnet identity offline from the preserved eth_chainId response."""
        if not receipt.chain_id_raw_object_id or not receipt.chain_id_acquisition_id:
            raise UniswapV2IngestionError(
                "receipt carries no eth_chainId lineage and cannot prove which chain "
                "produced it"
            )
        if receipt.chain_id_request_json != _canonical_json(chain_id_request()):
            raise UniswapV2IngestionError(
                "receipt chain identity was acquired by a different request"
            )
        _authenticate_acquisition(
            acquisitions,
            acquisition_id=receipt.chain_id_acquisition_id,
            raw_object_id=receipt.chain_id_raw_object_id,
            request_json=receipt.chain_id_request_json,
            acquired_at=receipt.chain_id_acquired_at,
            label="chain identity",
        )
        payload = self._read_raw_json(raw_root, receipt.chain_id_raw_object_id)
        self._assert_mainnet_payload(payload)

    def _authenticate_receipt_acquisitions(
        self, receipt: ChunkReceipt, acquisitions: Mapping[str, AcquisitionRecord]
    ) -> None:
        _authenticate_acquisition(
            acquisitions,
            acquisition_id=receipt.logs_acquisition_id,
            raw_object_id=receipt.logs_raw_object_id,
            request_json=receipt.logs_request_json,
            acquired_at=receipt.logs_acquired_at,
            label="logs response",
        )
        _authenticate_acquisition(
            acquisitions,
            acquisition_id=receipt.end_header_acquisition_id,
            raw_object_id=receipt.end_header_raw_object_id,
            request_json=receipt.end_header_request_json,
            acquired_at=receipt.end_header_acquired_at,
            label="end-block header",
        )
        for dependency in receipt.header_dependencies:
            _authenticate_acquisition(
                acquisitions,
                acquisition_id=dependency.acquisition_id,
                raw_object_id=dependency.raw_object_id,
                request_json=dependency.request_json,
                acquired_at=dependency.acquired_at,
                label=f"header for block {dependency.block_number}",
            )

    def _verify_receipt_dependencies(self, receipt: ChunkReceipt, raw_root: Path) -> None:
        """Every dependency must still be present, intact and request-bound.

        Called before a resume skips a completed chunk: a receipt is only a licence to
        skip work if the evidence it points at is still verifiable.
        """
        expected_logs_request = _canonical_json(
            logs_request(
                factory=receipt.factory,
                start_block=receipt.start_block,
                end_block=receipt.end_block,
            )
        )
        if receipt.logs_request_json != expected_logs_request:
            raise UniswapV2IngestionError(
                "receipt logs request does not match the requested chunk"
            )
        logs_response = self._read_raw_json(raw_root, receipt.logs_raw_object_id)
        if not isinstance(logs_response.get("result"), list):
            raise UniswapV2IngestionError("preserved eth_getLogs result must be a list")

        self._authenticate_header(
            raw_root,
            raw_object_id=receipt.end_header_raw_object_id,
            request_json=receipt.end_header_request_json,
            expected_block_number=receipt.end_block,
            expected_block_hash=receipt.end_block_hash,
            label="end-block header",
        )
        for dependency in receipt.header_dependencies:
            self._authenticate_header(
                raw_root,
                raw_object_id=dependency.raw_object_id,
                request_json=dependency.request_json,
                expected_block_number=dependency.block_number,
                expected_block_hash=dependency.block_hash,
                label=f"header for block {dependency.block_number}",
                batch_index=dependency.batch_index,
            )
        _parse_timestamp(receipt.logs_acquired_at, label="receipt logs_acquired_at")
        _parse_timestamp(receipt.completed_at, label="receipt completed_at")

    # -- header cache / batched acquisition --------------------------------

    def _cacheable_block(self, block_number: int) -> bool:
        cutoff = self._finality_cutoff_block
        return cutoff is not None and block_number < cutoff

    def _get_cached_header(self, block_number: int) -> CachedHeader | None:
        if not self._cacheable_block(block_number):
            return None
        with self._header_cache_lock:
            return self._header_cache.get((self._provider_id, block_number))

    def _put_cached_header(self, entry: CachedHeader) -> None:
        if not self._cacheable_block(entry.block_number):
            return
        with self._header_cache_lock:
            self._header_cache[(entry.provider_id, entry.block_number)] = entry

    def _header_from_single_call(
        self, call: RpcCall, *, expected_block_number: int
    ) -> CachedHeader:
        header = call.payload.get("result")
        if not isinstance(header, dict):
            raise UniswapV2IngestionError(
                f"missing block header for block {expected_block_number}"
            )
        number = _hex_quantity(
            _require(header, "number", label="block header"), label="header number"
        )
        if number != expected_block_number:
            raise UniswapV2IngestionError(
                f"header for block {expected_block_number} reports block {number}"
            )
        block_hash = _hex_bytes(
            _require(header, "hash", label="block header"), 32, label="header hash"
        )
        entry = CachedHeader(
            block_number=expected_block_number,
            header=header,
            block_hash=block_hash,
            request_json=call.request_json,
            raw_object_id=call.raw_object_id,
            acquisition_id=call.acquisition_id,
            acquired_at=call.acquired_at.isoformat(),
            batch_index=None,
            provider_id=self._provider_id,
        )
        self._put_cached_header(entry)
        return entry

    def _http_batch(
        self, batch: list[dict[str, Any]]
    ) -> tuple[int, bytes, datetime]:
        """POST a JSON-RPC batch under the provider token bucket (HTTP only)."""
        self._header_bucket.acquire()
        try:
            response = self._client.post(self._rpc_url, json=batch)
        except httpx.HTTPError as exc:
            raise UniswapV2IngestionError(
                f"JSON-RPC batch transport failure: {exc}"
            ) from exc
        return response.status_code, response.content, datetime.now(UTC)

    def _preserve_batch_response(
        self,
        *,
        batch: list[dict[str, Any]],
        status_code: int,
        body: bytes,
        acquired_at: datetime,
        event_start: int,
        event_end: int,
        receipts: sqlite3.Connection | None,
        transport_error: str | None = None,
    ) -> RpcBatchCall:
        """Preserve batch bytes and validate payload on the caller thread."""
        method = "batch"
        request_json = _canonical_json(batch)
        if transport_error is not None:
            self._raw_writer.record_failed_acquisition(
                AcquisitionMetadata(
                    source_id=SOURCE_ID, request=batch, acquired_at=acquired_at
                ),
                transport_error,
            )
            self._record_failure(
                receipts, method=method, request_json=request_json,
                start_block=event_start, end_block=event_end,
                kind="transport", detail=transport_error,
            )
            raise UniswapV2IngestionError(transport_error)

        raw = self._raw_writer.write_stream(
            [body],
            AcquisitionMetadata(
                source_id=SOURCE_ID,
                request=batch,
                response_metadata={
                    "status_code": status_code,
                    "method": method,
                    "provider_id": self._provider_id,
                    "batch_size": len(batch),
                },
                original_name=f"{self._provider_id}_{method}_{event_start}_{event_end}.json",
                acquired_at=acquired_at,
            ),
        )

        if status_code >= 400:
            detail = f"JSON-RPC HTTP {status_code} (batch)"
            self._record_failure(
                receipts, method=method, request_json=request_json,
                start_block=event_start, end_block=event_end,
                kind="http_status", detail=detail, status_code=status_code,
                raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            detail = "JSON-RPC batch returned invalid JSON"
            self._record_failure(
                receipts, method=method, request_json=request_json,
                start_block=event_start, end_block=event_end,
                kind="invalid_json", detail=detail, status_code=status_code,
                raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail) from exc

        if not isinstance(payload, list):
            detail = "JSON-RPC batch response must be an array"
            self._record_failure(
                receipts, method=method, request_json=request_json,
                start_block=event_start, end_block=event_end,
                kind="invalid_json", detail=detail, status_code=status_code,
                raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail)

        if len(payload) != len(batch):
            detail = (
                f"JSON-RPC batch size mismatch: sent {len(batch)}, received {len(payload)}"
            )
            self._record_failure(
                receipts, method=method, request_json=request_json,
                start_block=event_start, end_block=event_end,
                kind="rpc_error", detail=detail, status_code=status_code,
                raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail)

        for item in payload:
            if not isinstance(item, dict):
                raise UniswapV2IngestionError("JSON-RPC batch element must be an object")
            if item.get("error") is not None:
                detail = f"JSON-RPC batch element failed: {item['error']!r}"
                self._record_failure(
                    receipts, method=method, request_json=request_json,
                    start_block=event_start, end_block=event_end,
                    kind="rpc_error", detail=detail, status_code=status_code,
                    raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
                )
                raise UniswapV2IngestionError(detail)

        return RpcBatchCall(
            request=batch,
            payload=payload,
            raw_object_id=raw.raw_object_id,
            acquisition_id=raw.acquisition_id,
            acquired_at=acquired_at,
        )

    def _fetch_headers_for_blocks(
        self,
        block_numbers: Sequence[int],
        *,
        receipts: sqlite3.Connection | None,
    ) -> dict[int, CachedHeader]:
        """Acquire headers via cache, sequential singles, or JSON-RPC batch.

        Does not serve resume-path reorg checks — those always hit the network.
        Only blocks strictly below ``finality_cutoff_block`` enter the cache.
        """
        ordered = sorted({int(number) for number in block_numbers})
        results: dict[int, CachedHeader] = {}
        to_fetch: list[int] = []
        for number in ordered:
            cached = self._get_cached_header(number)
            if cached is not None:
                results[number] = cached
            else:
                to_fetch.append(number)
        if not to_fetch:
            return results

        # Single-block "batches" stay as single JSON-RPC objects so receipt
        # dependencies match the pilot shape (batch_index omitted, id:1 request).
        if not self._use_header_batches or len(to_fetch) == 1:
            for number in to_fetch:
                call = self._rpc(
                    block_header_request(number),
                    event_start=number, event_end=number, receipts=receipts,
                )
                results[number] = self._header_from_single_call(
                    call, expected_block_number=number
                )
            return results

        batches = [
            to_fetch[index:index + self._header_batch_size]
            for index in range(0, len(to_fetch), self._header_batch_size)
        ]

        def run_http(
            blocks: list[int],
        ) -> tuple[
            list[int], list[dict[str, Any]], int | None, bytes | None, datetime, str | None
        ]:
            request = block_header_batch_request(blocks)
            try:
                status_code, body, acquired_at = self._http_batch(request)
                return blocks, request, status_code, body, acquired_at, None
            except UniswapV2IngestionError as exc:
                return blocks, request, None, None, datetime.now(UTC), str(exc)

        # Bounded concurrency on HTTP only; raw-store/SQLite stay on this thread.
        with ThreadPoolExecutor(max_workers=self._header_max_in_flight) as executor:
            futures = [executor.submit(run_http, batch) for batch in batches]
            for future in as_completed(futures):
                blocks, request, status_code, body, acquired_at, transport_error = (
                    future.result()
                )
                if transport_error is not None or status_code is None or body is None:
                    self._preserve_batch_response(
                        batch=request,
                        status_code=0,
                        body=b"",
                        acquired_at=acquired_at,
                        event_start=blocks[0],
                        event_end=blocks[-1],
                        receipts=receipts,
                        transport_error=transport_error
                        or "JSON-RPC batch transport failure",
                    )
                    raise AssertionError("transport failure must raise")  # pragma: no cover
                batch_call = self._preserve_batch_response(
                    batch=request,
                    status_code=status_code,
                    body=body,
                    acquired_at=acquired_at,
                    event_start=blocks[0],
                    event_end=blocks[-1],
                    receipts=receipts,
                )
                for batch_index, number in enumerate(blocks):
                    request_element = batch_call.request[batch_index]
                    response = find_batch_response_by_id(
                        batch_call.payload, request_element.get("id")
                    )
                    header = response.get("result")
                    if not isinstance(header, dict):
                        raise UniswapV2IngestionError(
                            f"missing batch header for block {number}"
                        )
                    reported = _hex_quantity(
                        _require(header, "number", label="block header"),
                        label="header number",
                    )
                    if reported != number:
                        raise UniswapV2IngestionError(
                            f"header for block {number} reports block {reported}"
                        )
                    block_hash = _hex_bytes(
                        _require(header, "hash", label="block header"),
                        32, label="header hash",
                    )
                    entry = CachedHeader(
                        block_number=number,
                        header=header,
                        block_hash=block_hash,
                        request_json=batch_call.request_json,
                        raw_object_id=batch_call.raw_object_id,
                        acquisition_id=batch_call.acquisition_id,
                        acquired_at=batch_call.acquired_at.isoformat(),
                        batch_index=batch_index,
                        provider_id=self._provider_id,
                    )
                    self._put_cached_header(entry)
                    results[number] = entry
        return results

    # -- acquisition -------------------------------------------------------

    def fetch(
        self,
        *,
        start_block: int,
        end_block: int,
        chunk_size: int,
        receipt_db_path: str | None = None,
        emit_rows: bool = True,
        raw_root: Path | None = None,
    ) -> list[PairCreatedRow]:
        if start_block < 0 or end_block < start_block or chunk_size <= 0:
            raise ValueError("invalid block range or chunk_size")
        # DATA-012 ingests from deployment. A later start would silently omit pairs and
        # still produce a receipt chain that looks complete, so it is refused outright
        # rather than left as an untested configuration surface.
        if start_block != UNISWAP_V2_DEPLOYMENT_BLOCK:
            raise UniswapV2IngestionError(
                f"start_block must be the Uniswap V2 Factory deployment block "
                f"{UNISWAP_V2_DEPLOYMENT_BLOCK}, got {start_block}"
            )

        rows: list[PairCreatedRow] = []
        receipts = sqlite3.connect(receipt_db_path) if receipt_db_path else None
        try:
            if receipts is not None:
                receipts.execute("PRAGMA foreign_keys = ON")
            chain_call = self._assert_mainnet(receipts)
            chain_id = ETHEREUM_MAINNET_CHAIN_ID
            verify_root = self._raw_root if raw_root is None else raw_root

            for chunk_start in range(start_block, end_block + 1, chunk_size):
                chunk_end = min(chunk_start + chunk_size - 1, end_block)

                if receipts is not None:
                    prior = receipts.execute(
                        f"SELECT {', '.join(_RECEIPT_COLUMNS)} FROM {RECEIPT_TABLE} "
                        "WHERE chain = ? AND factory = ? AND topic = ? "
                        "AND start_block = ? AND end_block = ?",
                        (ETHEREUM_CHAIN, self._factory, PAIR_CREATED_TOPIC,
                         chunk_start, chunk_end),
                    ).fetchone()
                    if prior is not None:
                        receipt = _receipt_from_row(prior)
                        if verify_root is None:
                            raise UniswapV2IngestionError(
                                "raw_root is required to verify a completed chunk before "
                                "resuming; pass raw_root to fetch()"
                            )
                        self._verify_receipt_dependencies(receipt, verify_root)
                        prior_acquisitions = _load_acquisitions(
                            receipts, sorted(receipt.acquisition_ids)
                        )
                        self._verify_chain_lineage(
                            receipt, verify_root, prior_acquisitions
                        )
                        self._authenticate_receipt_acquisitions(receipt, prior_acquisitions)
                        # Only after the preserved evidence checks out do we confirm the
                        # chain still agrees with it.
                        end_call = self._rpc(
                            block_header_request(chunk_end),
                            event_start=chunk_end, event_end=chunk_end, receipts=receipts,
                        )
                        live_header = end_call.payload.get("result")
                        if not isinstance(live_header, dict):
                            raise UniswapV2IngestionError("missing end-block header")
                        live_hash = _hex_bytes(
                            _require(live_header, "hash", label="end-block header"),
                            32, label="end-block header hash",
                        )
                        if live_hash != _hex_bytes(
                            receipt.end_block_hash, 32, label="receipt end_block_hash"
                        ):
                            raise UniswapV2IngestionError(
                                "completed chunk receipt failed end-block validation"
                            )
                        # A skipped chunk contributes no rows. Returning the remainder
                        # would look indistinguishable from "this range has no events",
                        # so a row-emitting caller must go through replay instead.
                        if emit_rows:
                            raise UniswapV2IngestionError(
                                f"chunk [{chunk_start}, {chunk_end}] is already complete; "
                                "fetch(emit_rows=True) cannot return its rows -- acquire "
                                "with emit_rows=False and decode via replay_receipts()"
                            )
                        continue

                logs_call = self._rpc(
                    logs_request(
                        factory=self._factory, start_block=chunk_start, end_block=chunk_end
                    ),
                    event_start=chunk_start, event_end=chunk_end, receipts=receipts,
                )
                logs = logs_call.payload.get("result")
                if not isinstance(logs, list):
                    raise UniswapV2IngestionError("eth_getLogs result must be a list")

                # Collect distinct event-block numbers first, then acquire headers in
                # one batched/pooled pass instead of one sequential RPC per log.
                event_blocks: list[int] = []
                seen_blocks: set[int] = set()
                for log in logs:
                    if not isinstance(log, Mapping):
                        raise UniswapV2IngestionError("log entry must be an object")
                    block_number = _hex_quantity(
                        _require(log, "blockNumber", label="log"), label="blockNumber"
                    )
                    if block_number < chunk_start or block_number > chunk_end:
                        raise UniswapV2IngestionError(
                            "RPC returned log outside requested chunk"
                        )
                    if block_number in seen_blocks:
                        continue
                    seen_blocks.add(block_number)
                    event_blocks.append(block_number)

                # End-block is always a single eth_getBlockByNumber: receipt identity,
                # resume reorg checks, and pilot receipts all bind that shape. Event
                # blocks other than chunk_end are batch/pooled; when the end block also
                # carries events its single response is reused as the dependency.
                end_call = self._rpc(
                    block_header_request(chunk_end),
                    event_start=chunk_end, event_end=chunk_end, receipts=receipts,
                )
                end_entry = self._header_from_single_call(
                    end_call, expected_block_number=chunk_end
                )
                blocks_to_batch = [number for number in event_blocks if number != chunk_end]
                fetched = self._fetch_headers_for_blocks(
                    blocks_to_batch, receipts=receipts
                )
                if chunk_end in seen_blocks:
                    fetched[chunk_end] = end_entry

                headers: dict[int, tuple[dict[str, Any], str]] = {}
                dependencies: list[HeaderDependency] = []
                for number in sorted(event_blocks):
                    entry = fetched[number]
                    headers[number] = (entry.header, entry.raw_object_id)
                    dependencies.append(HeaderDependency(
                        block_number=number,
                        block_hash=entry.block_hash,
                        request_json=entry.request_json,
                        raw_object_id=entry.raw_object_id,
                        acquisition_id=entry.acquisition_id,
                        acquired_at=entry.acquired_at,
                        batch_index=entry.batch_index,
                    ))
                # Deterministic receipt bytes independent of concurrent fetch order.
                dependencies.sort(key=lambda dep: dep.block_number)

                end_hash = end_entry.block_hash
                end_request_json = end_call.request_json
                end_raw_object_id = end_call.raw_object_id
                end_acquisition_id = end_call.acquisition_id
                end_acquired_at = end_call.acquired_at

                if emit_rows:
                    rows.extend(decode_pair_created(
                        logs_call.payload,
                        headers,
                        factory=self._factory,
                        log_raw_object_id=logs_call.raw_object_id,
                        # Availability is when the events became observable, which is the
                        # moment the logs response was acquired -- not the later header
                        # fetches that merely resolve their timestamps.
                        availability_time=logs_call.acquired_at,
                    ))

                if receipts is not None:
                    completed_at = max(
                        [logs_call.acquired_at, end_acquired_at,
                         *(_parse_timestamp(dep.acquired_at, label="header acquired_at")
                           for dep in dependencies)]
                    )
                    receipts.execute(
                        f"INSERT INTO {RECEIPT_TABLE} "
                        f"({', '.join(_RECEIPT_COLUMNS)}) "
                        "VALUES (" + ", ".join("?" * len(_RECEIPT_COLUMNS)) + ")",
                        (ETHEREUM_CHAIN, chain_id, self._factory, PAIR_CREATED_TOPIC,
                         chunk_start, chunk_end,
                         logs_call.request_json, logs_call.raw_object_id,
                         logs_call.acquisition_id, logs_call.acquired_at.isoformat(),
                         chunk_end, end_hash, end_request_json, end_raw_object_id,
                         end_acquisition_id, end_acquired_at.isoformat(),
                         json.dumps(
                             [dep.as_dict() for dep in dependencies],
                             sort_keys=True,
                             separators=(",", ":"),
                         ),
                         completed_at.isoformat(),
                         chain_call.request_json, chain_call.raw_object_id,
                         chain_call.acquisition_id, chain_call.acquired_at.isoformat()),
                    )
                    receipts.commit()

            # Per-chunk decoding cannot see an event repeated across chunk boundaries.
            identities = [(row.tx_hash, row.log_index) for row in rows]
            if len(identities) != len(set(identities)):
                raise UniswapV2IngestionError(
                    "fetched rows contain duplicate (tx_hash, log_index)"
                )
            return sorted(rows, key=lambda row: (row.block_number, row.tx_index, row.log_index))
        finally:
            if receipts is not None:
                receipts.close()

    # -- replay ------------------------------------------------------------

    @staticmethod
    def _select_chunk_partition(
        candidates: Sequence[ChunkReceipt],
        *,
        start_block: int,
        end_block: int,
    ) -> list[ChunkReceipt]:
        """Pick a non-overlapping contiguous tiling of ``[start_block, end_block]``.

        The pilot store (and any resumable re-chunk) may hold nested partitions
        (for example both 5k and 10k receipts covering the same span). Loading every
        receipt with ``start >= S AND end <= E`` then breaks continuity. Production
        replay therefore selects, at each expected start, the longest candidate that
        still ends within the requested range — a greedy exact partition of the range.
        """
        if end_block < start_block:
            raise UniswapV2IngestionError("invalid replay range")
        by_start: dict[int, list[ChunkReceipt]] = {}
        for receipt in candidates:
            if receipt.end_block < receipt.start_block:
                raise UniswapV2IngestionError("receipt end_block precedes start_block")
            if receipt.start_block < start_block or receipt.end_block > end_block:
                continue
            by_start.setdefault(receipt.start_block, []).append(receipt)

        selected: list[ChunkReceipt] = []
        expected = start_block
        while expected <= end_block:
            options = [
                receipt for receipt in by_start.get(expected, [])
                if receipt.end_block <= end_block
            ]
            if not options:
                raise UniswapV2IngestionError(
                    f"receipt coverage has a block gap at {expected} "
                    f"(requested [{start_block}, {end_block}])"
                )
            # Longest chunk at this start prefers the outer partition when 5k and 10k
            # nest; ties break by earliest end (unique under PK).
            chosen = max(options, key=lambda receipt: (receipt.end_block, -receipt.start_block))
            selected.append(chosen)
            expected = chosen.end_block + 1
        if expected != end_block + 1:
            raise UniswapV2IngestionError("receipt coverage has a block gap")
        return selected

    def replay_receipts(
        self,
        *,
        start_block: int,
        end_block: int,
        receipt_db_path: str,
        raw_root: Path | None = None,
        exact_chunk: bool = False,
    ) -> ReplayResult:
        """Decode only preserved receipt bytes; never contacts the network.

        Coverage must be exactly contiguous over the requested range, every preserved
        object must hash to the id that names it, and every response must answer the
        request the receipt records. Anything less is not a replay, it is a guess.

        Range replay selects a non-overlapping chunk partition when the store holds
        nested/mixed chunk sizes (see ``_select_chunk_partition``). When
        ``exact_chunk`` is True, load only the receipt with this exact
        ``(start_block, end_block)`` primary key.
        """
        root = self._resolve_raw_root(raw_root)
        conn = sqlite3.connect(receipt_db_path)
        try:
            if exact_chunk:
                rows_raw = conn.execute(
                    f"SELECT {', '.join(_RECEIPT_COLUMNS)} FROM {RECEIPT_TABLE} "
                    "WHERE chain = ? AND factory = ? AND topic = ? "
                    "AND start_block = ? AND end_block = ?",
                    (
                        ETHEREUM_CHAIN, self._factory, PAIR_CREATED_TOPIC,
                        start_block, end_block,
                    ),
                ).fetchall()
                receipts = [_receipt_from_row(row) for row in rows_raw]
            else:
                rows_raw = conn.execute(
                    f"SELECT {', '.join(_RECEIPT_COLUMNS)} FROM {RECEIPT_TABLE} "
                    "WHERE chain = ? AND factory = ? AND topic = ? "
                    "AND start_block >= ? AND end_block <= ? ORDER BY start_block",
                    (
                        ETHEREUM_CHAIN, self._factory, PAIR_CREATED_TOPIC,
                        start_block, end_block,
                    ),
                ).fetchall()
                candidates = [_receipt_from_row(row) for row in rows_raw]
                receipts = self._select_chunk_partition(
                    candidates, start_block=start_block, end_block=end_block
                )
            acquisitions = _load_acquisitions(
                conn, [aid for receipt in receipts for aid in sorted(receipt.acquisition_ids)]
            )
        finally:
            conn.close()
        if exact_chunk and not receipts:
            raise UniswapV2IngestionError(
                f"no receipt for exact chunk [{start_block}, {end_block}]"
            )
        expected = start_block
        rows: list[PairCreatedRow] = []
        raw_ids: set[str] = set()
        acquisition_ids: set[str] = set()

        for receipt in receipts:
            # chain_id == 0x1, end_block_number == end_block and end_block >= start_block
            # are CHECK constraints in migration 0012, so an inconsistent receipt cannot
            # be written by any writer; re-asserting them here would be unreachable.
            if receipt.start_block != expected or receipt.end_block < receipt.start_block:
                raise UniswapV2IngestionError("receipt coverage is not contiguous")

            expected_logs_request = _canonical_json(
                logs_request(
                    factory=receipt.factory,
                    start_block=receipt.start_block,
                    end_block=receipt.end_block,
                )
            )
            if receipt.logs_request_json != expected_logs_request:
                raise UniswapV2IngestionError(
                    "receipt logs request does not match its own block range"
                )

            self._verify_chain_lineage(receipt, root, acquisitions)
            self._authenticate_receipt_acquisitions(receipt, acquisitions)

            self._authenticate_header(
                root,
                raw_object_id=receipt.end_header_raw_object_id,
                request_json=receipt.end_header_request_json,
                expected_block_number=receipt.end_block,
                expected_block_hash=receipt.end_block_hash,
                label="end-block header",
            )

            headers: dict[int, tuple[Mapping[str, Any], str]] = {}
            for dependency in receipt.header_dependencies:
                header = self._authenticate_header(
                    root,
                    raw_object_id=dependency.raw_object_id,
                    request_json=dependency.request_json,
                    expected_block_number=dependency.block_number,
                    expected_block_hash=dependency.block_hash,
                    label=f"header for block {dependency.block_number}",
                    batch_index=dependency.batch_index,
                )
                headers[dependency.block_number] = (header, dependency.raw_object_id)

            chunk_rows = decode_pair_created(
                self._read_raw_json(root, receipt.logs_raw_object_id),
                headers,
                factory=receipt.factory,
                log_raw_object_id=receipt.logs_raw_object_id,
                availability_time=_parse_timestamp(
                    receipt.logs_acquired_at, label="receipt logs_acquired_at"
                ),
            )
            # Acquisition rejects logs outside the requested chunk. Replay must apply the
            # same bound: preserved bytes that decode cleanly can still belong to another
            # range, and accepting them would silently widen this receipt's coverage.
            for row in chunk_rows:
                if not receipt.start_block <= row.block_number <= receipt.end_block:
                    raise UniswapV2IngestionError(
                        f"preserved log for block {row.block_number} is outside receipt "
                        f"range [{receipt.start_block}, {receipt.end_block}]"
                    )
            rows.extend(chunk_rows)
            raw_ids |= receipt.raw_object_ids
            acquisition_ids |= receipt.acquisition_ids
            expected = receipt.end_block + 1

        if expected != end_block + 1:
            raise UniswapV2IngestionError("receipt coverage has a block gap")

        # decode_pair_created already normalises hashes to lowercase, so identities are
        # directly comparable; this catches an event repeated across two receipts.
        identities = [(row.tx_hash, row.log_index) for row in rows]
        if len(identities) != len(set(identities)):
            raise UniswapV2IngestionError("replayed rows contain duplicate (tx_hash, log_index)")

        ordered = tuple(
            sorted(rows, key=lambda row: (row.block_number, row.tx_index, row.log_index))
        )
        return ReplayResult(
            rows=ordered,
            raw_object_ids=frozenset(raw_ids),
            completed_ranges=tuple((r.start_block, r.end_block) for r in receipts),
            acquisition_ids=frozenset(acquisition_ids),
        )
