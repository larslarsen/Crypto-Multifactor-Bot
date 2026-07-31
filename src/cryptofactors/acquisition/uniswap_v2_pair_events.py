"""DEX-003 / ADR-0015 Uniswap V2 Pair Swap and Sync raw-event acquisition.

Extends the DATA-012 JSON-RPC pattern from factory ``PairCreated`` to per-pair
``Swap`` and ``Sync`` events. Completeness requires two independent RPC providers
to agree on every field that reaches a published row. One successful
``eth_getLogs`` is never sufficient authority.

Dual-provider scope for a completed chunk:

* log identity — address, topics, data, block number/hash, tx hash, log index,
  transaction index, and removed flag (``LogIdentity`` digest)
* end-block header hash from both providers
* every event-block header hash **and** timestamp from both providers (so
  ``event_time`` / ``source_available_at`` cannot rest on a single source)
* token ``decimals()`` eth_call results (orientation / OHLC / volume inputs)

Temporal fields follow ADR-0015:

* ``event_time`` — dual-agreed block timestamp of the event
* ``source_available_at`` — ``event_time + 24h`` (conservative finality lag)
* ``retrieved_at`` — when this repository acquired the logs responses

Replay is offline and request-bound: receipts name both providers' preserved
logs and end-block headers, plus every dual-validated event-block header
dependency. Resume with ``emit_rows=True`` is intentionally refused for already-
complete chunks — operators acquire with ``emit_rows=False`` and decode via
``replay_receipts()``.
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
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import httpx

from cryptofactors.acquisition.uniswap_v2 import (
    ETHEREUM_CHAIN,
    ETHEREUM_MAINNET_CHAIN_ID,
    UNISWAP_V2_DEPLOYMENT_BLOCK,
    UniswapV2IngestionError,
    _abi_address,
    _authenticate_acquisition,
    _canonical_json,
    _hex_bytes,
    _hex_quantity,
    _load_acquisitions,
    _parse_timestamp,
    _require,
    _same_address,
    AcquisitionRecord,
    HeaderDependency,
    RpcCall,
    block_header_batch_request,
    block_header_request,
    chain_id_request,
    header_request_core,
)
from cryptofactors.ingest.raw.models import AcquisitionMetadata
from cryptofactors.ingest.raw.paths import content_addressed_absolute_path
from cryptofactors.ingest.raw.writer import RawObjectWriter

# Uniswap V2 Pair event topics (keccak of the canonical signatures).
SWAP_TOPIC = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
SYNC_TOPIC = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"

# ERC-20 decimals() selector = first four bytes of keccak("decimals()").
DECIMALS_SELECTOR = "0x313ce567"

SOURCE_ID = "ethereum_json_rpc_uniswap_v2_pair_events"
RECEIPT_TABLE = "uniswap_v2_pair_event_chunk_receipt"
DECIMALS_RECEIPT_TABLE = "uniswap_v2_token_decimals_receipt"
FAILURE_TABLE = "uniswap_v2_pair_event_transport_failure"
DISAGREEMENT_TABLE = "uniswap_v2_pair_event_provider_disagreement"

_DECIMALS_RECEIPT_COLUMNS = (
    "chain", "chain_id", "token", "block_number", "decimals",
    "primary_provider_id", "secondary_provider_id",
    "primary_request_json", "primary_raw_object_id",
    "primary_acquisition_id", "primary_acquired_at",
    "secondary_request_json", "secondary_raw_object_id",
    "secondary_acquisition_id", "secondary_acquired_at",
    "completed_at",
)

EventKind = Literal["swap", "sync"]
SOURCE_AVAILABILITY_LAG = timedelta(hours=24)

# Default batching / concurrency knobs for eth_getBlockByNumber acquisition.
DEFAULT_HEADER_BATCH_SIZE = 64
DEFAULT_HEADER_MAX_IN_FLIGHT = 4
DEFAULT_HEADER_REQUESTS_PER_SECOND = 20.0

_RECEIPT_COLUMNS = (
    "chain", "chain_id", "pair", "topic", "start_block", "end_block",
    "primary_provider_id",
    "primary_logs_request_json", "primary_logs_raw_object_id",
    "primary_logs_acquisition_id", "primary_logs_acquired_at",
    "secondary_provider_id",
    "secondary_logs_request_json", "secondary_logs_raw_object_id",
    "secondary_logs_acquisition_id", "secondary_logs_acquired_at",
    "log_count", "log_identity_sha256", "reconciliation_status",
    "end_block_number", "end_block_hash",
    "primary_end_header_request_json", "primary_end_header_raw_object_id",
    "primary_end_header_acquisition_id", "primary_end_header_acquired_at",
    "secondary_end_block_hash",
    "secondary_end_header_request_json", "secondary_end_header_raw_object_id",
    "secondary_end_header_acquisition_id", "secondary_end_header_acquired_at",
    "header_dependencies_json", "completed_at",
    "chain_id_request_json", "chain_id_raw_object_id",
    "chain_id_acquisition_id", "chain_id_acquired_at",
    "secondary_header_dependencies_json",
)


# ---------------------------------------------------------------------------
# Canonical requests
# ---------------------------------------------------------------------------

def pair_logs_request(
    *,
    pair: str,
    topic: str,
    start_block: int,
    end_block: int,
) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getLogs",
        "params": [{
            "address": pair,
            "fromBlock": hex(start_block),
            "toBlock": hex(end_block),
            "topics": [topic],
        }],
    }


def token_decimals_request(*, token: str, block_number: int | str = "latest") -> dict[str, Any]:
    block = block_number if isinstance(block_number, str) else hex(block_number)
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [
            {"to": token, "data": DECIMALS_SELECTOR},
            block,
        ],
    }


def topic_for_kind(kind: EventKind) -> str:
    if kind == "swap":
        return SWAP_TOPIC
    if kind == "sync":
        return SYNC_TOPIC
    raise UniswapV2IngestionError(f"unknown event kind: {kind!r}")


def kind_for_topic(topic: str) -> EventKind:
    normalized = _hex_bytes(topic, 32, label="topic")
    if normalized == SWAP_TOPIC:
        return "swap"
    if normalized == SYNC_TOPIC:
        return "sync"
    raise UniswapV2IngestionError(f"unsupported pair event topic: {topic!r}")


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SwapRow:
    chain: str
    pair: str
    sender: str
    to: str
    amount0_in: int
    amount1_in: int
    amount0_out: int
    amount1_out: int
    block_number: int
    block_hash: str
    block_timestamp: int
    tx_hash: str
    tx_index: int
    log_index: int
    event_time: datetime
    source_available_at: datetime
    retrieved_at: datetime
    raw_object_id: str
    block_raw_object_id: str
    primary_provider_id: str
    secondary_provider_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_kind": "swap",
            "chain": self.chain,
            "pair": self.pair,
            "sender": self.sender,
            "to": self.to,
            "amount0_in": self.amount0_in,
            "amount1_in": self.amount1_in,
            "amount0_out": self.amount0_out,
            "amount1_out": self.amount1_out,
            "block_number": self.block_number,
            "block_hash": self.block_hash,
            "block_timestamp": self.block_timestamp,
            "tx_hash": self.tx_hash,
            "tx_index": self.tx_index,
            "log_index": self.log_index,
            "event_time": self.event_time.isoformat(),
            "source_available_at": self.source_available_at.isoformat(),
            "retrieved_at": self.retrieved_at.isoformat(),
            "raw_object_id": self.raw_object_id,
            "block_raw_object_id": self.block_raw_object_id,
            "primary_provider_id": self.primary_provider_id,
            "secondary_provider_id": self.secondary_provider_id,
        }


@dataclass(frozen=True, slots=True)
class SyncRow:
    chain: str
    pair: str
    reserve0: int
    reserve1: int
    block_number: int
    block_hash: str
    block_timestamp: int
    tx_hash: str
    tx_index: int
    log_index: int
    event_time: datetime
    source_available_at: datetime
    retrieved_at: datetime
    raw_object_id: str
    block_raw_object_id: str
    primary_provider_id: str
    secondary_provider_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_kind": "sync",
            "chain": self.chain,
            "pair": self.pair,
            "reserve0": self.reserve0,
            "reserve1": self.reserve1,
            "block_number": self.block_number,
            "block_hash": self.block_hash,
            "block_timestamp": self.block_timestamp,
            "tx_hash": self.tx_hash,
            "tx_index": self.tx_index,
            "log_index": self.log_index,
            "event_time": self.event_time.isoformat(),
            "source_available_at": self.source_available_at.isoformat(),
            "retrieved_at": self.retrieved_at.isoformat(),
            "raw_object_id": self.raw_object_id,
            "block_raw_object_id": self.block_raw_object_id,
            "primary_provider_id": self.primary_provider_id,
            "secondary_provider_id": self.secondary_provider_id,
        }


PairEventRow = SwapRow | SyncRow


@dataclass(frozen=True, slots=True)
class TokenDecimalsRow:
    chain: str
    token: str
    decimals: int
    block_number: int | None
    retrieved_at: datetime
    primary_raw_object_id: str
    secondary_raw_object_id: str
    primary_provider_id: str
    secondary_provider_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "token": self.token,
            "decimals": self.decimals,
            "block_number": self.block_number,
            "retrieved_at": self.retrieved_at.isoformat(),
            "primary_raw_object_id": self.primary_raw_object_id,
            "secondary_raw_object_id": self.secondary_raw_object_id,
            "primary_provider_id": self.primary_provider_id,
            "secondary_provider_id": self.secondary_provider_id,
        }


@dataclass(frozen=True, slots=True)
class TokenDecimalsReceipt:
    """Durable dual-provider decimals evidence for offline resume."""

    chain: str
    chain_id: str
    token: str
    block_number: int
    decimals: int
    primary_provider_id: str
    secondary_provider_id: str
    primary_request_json: str
    primary_raw_object_id: str
    primary_acquisition_id: str
    primary_acquired_at: str
    secondary_request_json: str
    secondary_raw_object_id: str
    secondary_acquisition_id: str
    secondary_acquired_at: str
    completed_at: str

    @property
    def raw_object_ids(self) -> frozenset[str]:
        return frozenset({self.primary_raw_object_id, self.secondary_raw_object_id})

    @property
    def acquisition_ids(self) -> frozenset[str]:
        return frozenset({self.primary_acquisition_id, self.secondary_acquisition_id})


def _decimals_receipt_from_row(row: Sequence[Any]) -> TokenDecimalsReceipt:
    return TokenDecimalsReceipt(
        chain=str(row[0]),
        chain_id=str(row[1]),
        token=str(row[2]),
        block_number=int(row[3]),
        decimals=int(row[4]),
        primary_provider_id=str(row[5]),
        secondary_provider_id=str(row[6]),
        primary_request_json=str(row[7]),
        primary_raw_object_id=str(row[8]),
        primary_acquisition_id=str(row[9]),
        primary_acquired_at=str(row[10]),
        secondary_request_json=str(row[11]),
        secondary_raw_object_id=str(row[12]),
        secondary_acquisition_id=str(row[13]),
        secondary_acquired_at=str(row[14]),
        completed_at=str(row[15]),
    )


@dataclass(frozen=True, slots=True)
class PairEventChunkReceipt:
    chain: str
    chain_id: str
    pair: str
    topic: str
    start_block: int
    end_block: int
    primary_provider_id: str
    primary_logs_request_json: str
    primary_logs_raw_object_id: str
    primary_logs_acquisition_id: str
    primary_logs_acquired_at: str
    secondary_provider_id: str
    secondary_logs_request_json: str
    secondary_logs_raw_object_id: str
    secondary_logs_acquisition_id: str
    secondary_logs_acquired_at: str
    log_count: int
    log_identity_sha256: str
    reconciliation_status: str
    end_block_number: int
    end_block_hash: str
    primary_end_header_request_json: str
    primary_end_header_raw_object_id: str
    primary_end_header_acquisition_id: str
    primary_end_header_acquired_at: str
    secondary_end_block_hash: str
    secondary_end_header_request_json: str
    secondary_end_header_raw_object_id: str
    secondary_end_header_acquisition_id: str
    secondary_end_header_acquired_at: str
    header_dependencies: tuple[HeaderDependency, ...]
    completed_at: str
    chain_id_request_json: str
    chain_id_raw_object_id: str
    chain_id_acquisition_id: str
    chain_id_acquired_at: str
    secondary_header_dependencies: tuple[HeaderDependency, ...]

    @property
    def raw_object_ids(self) -> frozenset[str]:
        return frozenset({
            self.primary_logs_raw_object_id,
            self.secondary_logs_raw_object_id,
            self.primary_end_header_raw_object_id,
            self.secondary_end_header_raw_object_id,
            self.chain_id_raw_object_id,
            *(dep.raw_object_id for dep in self.header_dependencies),
            *(dep.raw_object_id for dep in self.secondary_header_dependencies),
        })

    @property
    def acquisition_ids(self) -> frozenset[str]:
        return frozenset({
            self.primary_logs_acquisition_id,
            self.secondary_logs_acquisition_id,
            self.primary_end_header_acquisition_id,
            self.secondary_end_header_acquisition_id,
            self.chain_id_acquisition_id,
            *(dep.acquisition_id for dep in self.header_dependencies),
            *(dep.acquisition_id for dep in self.secondary_header_dependencies),
        })


@dataclass(frozen=True, slots=True)
class PairEventReplayResult:
    rows: tuple[PairEventRow, ...]
    raw_object_ids: frozenset[str]
    completed_ranges: tuple[tuple[int, int], ...]
    acquisition_ids: frozenset[str]
    log_identity_sha256s: tuple[str, ...]


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
    """Finalized block header retained for cross-chunk / cross-pair reuse."""

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
class LogIdentity:
    """Canonical identity of one log for dual-provider reconciliation.

    Digest fields are fixed for receipt compatibility. Adding published-only
    fields (for example ``transactionIndex``) requires a versioned digest and
    a receipt migration — do not change ``as_tuple`` without one.
    """

    tx_hash: str
    log_index: int
    address: str
    topics: tuple[str, ...]
    data: str
    block_number: int
    block_hash: str
    removed: bool

    def as_tuple(self) -> tuple[Any, ...]:
        return (
            self.tx_hash,
            self.log_index,
            self.address,
            self.topics,
            self.data,
            self.block_number,
            self.block_hash,
            self.removed,
        )


# ---------------------------------------------------------------------------
# Log identity + decoding
# ---------------------------------------------------------------------------

def extract_log_identity(log: Mapping[str, Any]) -> LogIdentity:
    if not isinstance(log, Mapping):
        raise UniswapV2IngestionError("log entry must be an object")
    topics_raw = log.get("topics")
    if not isinstance(topics_raw, list) or not topics_raw:
        raise UniswapV2IngestionError("log topics must be a non-empty list")
    topics = tuple(
        _hex_bytes(topic, 32, label=f"topic[{index}]")
        for index, topic in enumerate(topics_raw)
    )
    data_raw = _require(log, "data", label="log")
    if not isinstance(data_raw, str) or not data_raw.startswith("0x"):
        raise UniswapV2IngestionError(f"log data must be 0x-prefixed hex, got {data_raw!r}")
    data_body = data_raw[2:]
    if len(data_body) % 2 != 0 or any(c not in "0123456789abcdefABCDEF" for c in data_body):
        raise UniswapV2IngestionError(f"log data is not valid hex: {data_raw!r}")
    removed = _require(log, "removed", label="log")
    if not isinstance(removed, bool):
        raise UniswapV2IngestionError("log removed flag must be a boolean")
    return LogIdentity(
        tx_hash=_hex_bytes(
            _require(log, "transactionHash", label="log"), 32, label="transactionHash"
        ),
        log_index=_hex_quantity(_require(log, "logIndex", label="log"), label="logIndex"),
        address=_hex_bytes(_require(log, "address", label="log"), 20, label="log address"),
        topics=topics,
        data="0x" + data_body.lower(),
        block_number=_hex_quantity(
            _require(log, "blockNumber", label="log"), label="blockNumber"
        ),
        block_hash=_hex_bytes(_require(log, "blockHash", label="log"), 32, label="log blockHash"),
        removed=removed,
    )


def log_identity_digest(identities: Sequence[LogIdentity]) -> str:
    """SHA-256 of the canonical sorted identity set for a chunk."""
    ordered = sorted(identities, key=lambda item: (item.block_number, item.tx_hash, item.log_index))
    payload = json.dumps([item.as_tuple() for item in ordered], separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def reconcile_log_sets(
    primary_logs: Sequence[Any],
    secondary_logs: Sequence[Any],
) -> tuple[list[LogIdentity], str]:
    """Require exact identity agreement between two providers. Fail closed otherwise."""
    if not isinstance(primary_logs, list) or not isinstance(secondary_logs, list):
        raise UniswapV2IngestionError("eth_getLogs result must be a list")
    primary = [extract_log_identity(log) for log in primary_logs]
    secondary = [extract_log_identity(log) for log in secondary_logs]
    primary_digest = log_identity_digest(primary)
    secondary_digest = log_identity_digest(secondary)
    if len(primary) != len(secondary):
        raise UniswapV2IngestionError(
            f"provider log count disagreement: primary={len(primary)} "
            f"secondary={len(secondary)}"
        )
    if primary_digest != secondary_digest:
        raise UniswapV2IngestionError(
            f"provider log identity disagreement: primary={primary_digest} "
            f"secondary={secondary_digest}"
        )
    # Duplicate (tx_hash, log_index) within one provider is also refused.
    seen: set[tuple[str, int]] = set()
    for identity in primary:
        key = (identity.tx_hash, identity.log_index)
        if key in seen:
            raise UniswapV2IngestionError("duplicate (tx_hash, log_index) within provider logs")
        seen.add(key)
    return primary, primary_digest


def _uint256_words(data: str, *, expected_words: int, label: str) -> list[int]:
    body = data[2:] if data.startswith("0x") else data
    if len(body) != expected_words * 64:
        raise UniswapV2IngestionError(
            f"{label} data must be exactly {expected_words} uint256 words, "
            f"got {len(body) // 64}"
        )
    return [int(body[index * 64:(index + 1) * 64], 16) for index in range(expected_words)]


def decode_swap_logs(
    logs_response: Mapping[str, Any],
    block_headers: Mapping[int, tuple[Mapping[str, Any], str]],
    *,
    pair: str,
    log_raw_object_id: str,
    retrieved_at: datetime,
    primary_provider_id: str,
    secondary_provider_id: str,
) -> list[SwapRow]:
    logs = logs_response.get("result") if isinstance(logs_response, Mapping) else None
    if not isinstance(logs, list):
        raise UniswapV2IngestionError("eth_getLogs result must be a list")

    rows: list[SwapRow] = []
    seen: set[tuple[str, int]] = set()
    for log in logs:
        if not isinstance(log, Mapping):
            raise UniswapV2IngestionError("log entry must be an object")
        identity = extract_log_identity(log)
        if not _same_address(identity.address, pair):
            raise UniswapV2IngestionError(
                f"log emitted by {identity.address!r}, expected pair {pair}"
            )
        if identity.removed is not False:
            raise UniswapV2IngestionError("reorg-removed log cannot be published")
        if len(identity.topics) != 3 or identity.topics[0] != SWAP_TOPIC:
            raise UniswapV2IngestionError("invalid Swap topics")
        if identity.block_number not in block_headers:
            raise UniswapV2IngestionError(
                f"no preserved block header for block {identity.block_number}"
            )
        header, header_raw_object_id = block_headers[identity.block_number]
        header_number = _hex_quantity(
            _require(header, "number", label="block header"), label="header number"
        )
        if header_number != identity.block_number:
            raise UniswapV2IngestionError(
                f"preserved header is for block {header_number}, not {identity.block_number}"
            )
        header_hash = _hex_bytes(
            _require(header, "hash", label="block header"), 32, label="header hash"
        )
        if identity.block_hash != header_hash:
            raise UniswapV2IngestionError("log block hash does not match block header")
        key = (identity.tx_hash, identity.log_index)
        if key in seen:
            raise UniswapV2IngestionError("duplicate (tx_hash, log_index)")
        seen.add(key)

        # Swap(address indexed sender, uint amount0In, uint amount1In,
        #      uint amount0Out, uint amount1Out, address indexed to)
        amounts = _uint256_words(identity.data, expected_words=4, label="Swap")
        timestamp = _hex_quantity(
            _require(header, "timestamp", label="block header"), label="block timestamp"
        )
        event_time = datetime.fromtimestamp(timestamp, UTC)
        rows.append(SwapRow(
            chain=ETHEREUM_CHAIN,
            pair=pair.lower(),
            sender=_abi_address(identity.topics[1], label="sender"),
            to=_abi_address(identity.topics[2], label="to"),
            amount0_in=amounts[0],
            amount1_in=amounts[1],
            amount0_out=amounts[2],
            amount1_out=amounts[3],
            block_number=identity.block_number,
            block_hash=identity.block_hash,
            block_timestamp=timestamp,
            tx_hash=identity.tx_hash,
            tx_index=_hex_quantity(
                _require(log, "transactionIndex", label="log"), label="transactionIndex"
            ),
            log_index=identity.log_index,
            event_time=event_time,
            source_available_at=event_time + SOURCE_AVAILABILITY_LAG,
            retrieved_at=retrieved_at,
            raw_object_id=log_raw_object_id,
            block_raw_object_id=header_raw_object_id,
            primary_provider_id=primary_provider_id,
            secondary_provider_id=secondary_provider_id,
        ))
    return sorted(rows, key=lambda row: (row.block_number, row.tx_index, row.log_index))


def decode_sync_logs(
    logs_response: Mapping[str, Any],
    block_headers: Mapping[int, tuple[Mapping[str, Any], str]],
    *,
    pair: str,
    log_raw_object_id: str,
    retrieved_at: datetime,
    primary_provider_id: str,
    secondary_provider_id: str,
) -> list[SyncRow]:
    logs = logs_response.get("result") if isinstance(logs_response, Mapping) else None
    if not isinstance(logs, list):
        raise UniswapV2IngestionError("eth_getLogs result must be a list")

    rows: list[SyncRow] = []
    seen: set[tuple[str, int]] = set()
    for log in logs:
        if not isinstance(log, Mapping):
            raise UniswapV2IngestionError("log entry must be an object")
        identity = extract_log_identity(log)
        if not _same_address(identity.address, pair):
            raise UniswapV2IngestionError(
                f"log emitted by {identity.address!r}, expected pair {pair}"
            )
        if identity.removed is not False:
            raise UniswapV2IngestionError("reorg-removed log cannot be published")
        if len(identity.topics) != 1 or identity.topics[0] != SYNC_TOPIC:
            raise UniswapV2IngestionError("invalid Sync topics")
        if identity.block_number not in block_headers:
            raise UniswapV2IngestionError(
                f"no preserved block header for block {identity.block_number}"
            )
        header, header_raw_object_id = block_headers[identity.block_number]
        header_number = _hex_quantity(
            _require(header, "number", label="block header"), label="header number"
        )
        if header_number != identity.block_number:
            raise UniswapV2IngestionError(
                f"preserved header is for block {header_number}, not {identity.block_number}"
            )
        header_hash = _hex_bytes(
            _require(header, "hash", label="block header"), 32, label="header hash"
        )
        if identity.block_hash != header_hash:
            raise UniswapV2IngestionError("log block hash does not match block header")
        key = (identity.tx_hash, identity.log_index)
        if key in seen:
            raise UniswapV2IngestionError("duplicate (tx_hash, log_index)")
        seen.add(key)

        # Sync(uint112 reserve0, uint112 reserve1) — ABI-encoded as two 32-byte words.
        reserves = _uint256_words(identity.data, expected_words=2, label="Sync")
        for value, name in ((reserves[0], "reserve0"), (reserves[1], "reserve1")):
            if value >= 1 << 112:
                raise UniswapV2IngestionError(f"{name} exceeds uint112 range")
        timestamp = _hex_quantity(
            _require(header, "timestamp", label="block header"), label="block timestamp"
        )
        event_time = datetime.fromtimestamp(timestamp, UTC)
        rows.append(SyncRow(
            chain=ETHEREUM_CHAIN,
            pair=pair.lower(),
            reserve0=reserves[0],
            reserve1=reserves[1],
            block_number=identity.block_number,
            block_hash=identity.block_hash,
            block_timestamp=timestamp,
            tx_hash=identity.tx_hash,
            tx_index=_hex_quantity(
                _require(log, "transactionIndex", label="log"), label="transactionIndex"
            ),
            log_index=identity.log_index,
            event_time=event_time,
            source_available_at=event_time + SOURCE_AVAILABILITY_LAG,
            retrieved_at=retrieved_at,
            raw_object_id=log_raw_object_id,
            block_raw_object_id=header_raw_object_id,
            primary_provider_id=primary_provider_id,
            secondary_provider_id=secondary_provider_id,
        ))
    return sorted(rows, key=lambda row: (row.block_number, row.tx_index, row.log_index))


def decode_pair_event_logs(
    logs_response: Mapping[str, Any],
    block_headers: Mapping[int, tuple[Mapping[str, Any], str]],
    *,
    pair: str,
    topic: str,
    log_raw_object_id: str,
    retrieved_at: datetime,
    primary_provider_id: str,
    secondary_provider_id: str,
) -> list[PairEventRow]:
    kind = kind_for_topic(topic)
    if kind == "swap":
        return list(decode_swap_logs(
            logs_response,
            block_headers,
            pair=pair,
            log_raw_object_id=log_raw_object_id,
            retrieved_at=retrieved_at,
            primary_provider_id=primary_provider_id,
            secondary_provider_id=secondary_provider_id,
        ))
    return list(decode_sync_logs(
        logs_response,
        block_headers,
        pair=pair,
        log_raw_object_id=log_raw_object_id,
        retrieved_at=retrieved_at,
        primary_provider_id=primary_provider_id,
        secondary_provider_id=secondary_provider_id,
    ))


def decode_token_decimals(response: Mapping[str, Any]) -> int:
    result = response.get("result") if isinstance(response, Mapping) else None
    if not isinstance(result, str) or not result.startswith("0x"):
        raise UniswapV2IngestionError("eth_call decimals result must be 0x-prefixed hex")
    body = result[2:]
    if not body or any(c not in "0123456789abcdefABCDEF" for c in body):
        raise UniswapV2IngestionError(f"invalid decimals result: {result!r}")
    value = int(body, 16)
    if value > 255:
        raise UniswapV2IngestionError(f"decimals out of uint8 range: {value}")
    return value


# ---------------------------------------------------------------------------
# Receipt persistence
# ---------------------------------------------------------------------------

def _parse_header_dependencies(
    raw_json: str, *, label: str
) -> tuple[HeaderDependency, ...]:
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise UniswapV2IngestionError(
            f"{label} dependency list is not valid JSON"
        ) from exc
    if not isinstance(parsed, list):
        raise UniswapV2IngestionError(f"{label} dependency list must be a JSON array")
    dependencies = tuple(HeaderDependency.from_dict(item) for item in parsed)
    by_block: dict[int, HeaderDependency] = {}
    for dependency in dependencies:
        previous = by_block.get(dependency.block_number)
        if previous is not None:
            if previous.block_hash != dependency.block_hash:
                raise UniswapV2IngestionError(
                    f"conflicting {label} dependencies for block "
                    f"{dependency.block_number}: {previous.block_hash} and "
                    f"{dependency.block_hash}"
                )
            raise UniswapV2IngestionError(
                f"duplicate {label} dependency for block {dependency.block_number}"
            )
        by_block[dependency.block_number] = dependency
    return dependencies


def _receipt_from_row(row: Sequence[Any]) -> PairEventChunkReceipt:
    # Columns 0..35 match migration 0014; column 36 is secondary_header_dependencies
    # from migration 0015 (defaults to '[]' when absent on very old rows).
    dependencies = _parse_header_dependencies(
        str(row[30]), label="primary header"
    )
    secondary_raw = str(row[36]) if len(row) > 36 else "[]"
    secondary_dependencies = _parse_header_dependencies(
        secondary_raw, label="secondary header"
    )
    return PairEventChunkReceipt(
        chain=str(row[0]),
        chain_id=str(row[1]),
        pair=str(row[2]),
        topic=str(row[3]),
        start_block=int(row[4]),
        end_block=int(row[5]),
        primary_provider_id=str(row[6]),
        primary_logs_request_json=str(row[7]),
        primary_logs_raw_object_id=str(row[8]),
        primary_logs_acquisition_id=str(row[9]),
        primary_logs_acquired_at=str(row[10]),
        secondary_provider_id=str(row[11]),
        secondary_logs_request_json=str(row[12]),
        secondary_logs_raw_object_id=str(row[13]),
        secondary_logs_acquisition_id=str(row[14]),
        secondary_logs_acquired_at=str(row[15]),
        log_count=int(row[16]),
        log_identity_sha256=str(row[17]),
        reconciliation_status=str(row[18]),
        end_block_number=int(row[19]),
        end_block_hash=str(row[20]),
        primary_end_header_request_json=str(row[21]),
        primary_end_header_raw_object_id=str(row[22]),
        primary_end_header_acquisition_id=str(row[23]),
        primary_end_header_acquired_at=str(row[24]),
        secondary_end_block_hash=str(row[25]),
        secondary_end_header_request_json=str(row[26]),
        secondary_end_header_raw_object_id=str(row[27]),
        secondary_end_header_acquisition_id=str(row[28]),
        secondary_end_header_acquired_at=str(row[29]),
        header_dependencies=dependencies,
        completed_at=str(row[31]),
        chain_id_request_json=str(row[32]),
        chain_id_raw_object_id=str(row[33]),
        chain_id_acquisition_id=str(row[34]),
        chain_id_acquired_at=str(row[35]),
        secondary_header_dependencies=secondary_dependencies,
    )


# ---------------------------------------------------------------------------
# Ingestor
# ---------------------------------------------------------------------------

class UniswapV2PairEventIngestor:
    """Dual-RPC, resumable Swap/Sync acquisition with offline replay."""

    def __init__(
        self,
        *,
        primary_rpc_url: str,
        secondary_rpc_url: str,
        raw_writer: RawObjectWriter,
        primary_provider_id: str = "rpc_primary",
        secondary_provider_id: str = "rpc_secondary",
        primary_client: httpx.Client | None = None,
        secondary_client: httpx.Client | None = None,
        raw_root: Path | None = None,
        finality_cutoff_block: int | None = None,
        header_batch_size: int = DEFAULT_HEADER_BATCH_SIZE,
        header_max_in_flight: int = DEFAULT_HEADER_MAX_IN_FLIGHT,
        header_requests_per_second: float = DEFAULT_HEADER_REQUESTS_PER_SECOND,
        use_header_batches: bool = True,
    ) -> None:
        if not primary_rpc_url or not secondary_rpc_url:
            raise ValueError("primary_rpc_url and secondary_rpc_url are required")
        if primary_rpc_url.rstrip("/") == secondary_rpc_url.rstrip("/"):
            raise ValueError(
                "primary and secondary RPC URLs must be distinct independent providers"
            )
        if not primary_provider_id or not secondary_provider_id:
            raise ValueError("provider ids are required")
        if primary_provider_id == secondary_provider_id:
            raise ValueError("primary and secondary provider ids must differ")
        if header_batch_size <= 0:
            raise ValueError("header_batch_size must be positive")
        if header_max_in_flight <= 0:
            raise ValueError("header_max_in_flight must be positive")
        if header_requests_per_second <= 0:
            raise ValueError("header_requests_per_second must be positive")
        if finality_cutoff_block is not None and finality_cutoff_block < UNISWAP_V2_DEPLOYMENT_BLOCK:
            raise ValueError(
                "finality_cutoff_block must be >= Uniswap V2 deployment block when set"
            )
        self._primary_url = primary_rpc_url
        self._secondary_url = secondary_rpc_url
        self._primary_provider_id = primary_provider_id
        self._secondary_provider_id = secondary_provider_id
        self._raw_writer = raw_writer
        self._primary_client = primary_client or httpx.Client(timeout=30.0)
        self._secondary_client = secondary_client or httpx.Client(timeout=30.0)
        self._owns_primary = primary_client is None
        self._owns_secondary = secondary_client is None
        self._raw_root = raw_root
        self._chain_call: RpcCall | None = None
        self._finality_cutoff_block = finality_cutoff_block
        self._header_batch_size = header_batch_size
        self._header_max_in_flight = header_max_in_flight
        self._use_header_batches = use_header_batches
        # Per-provider rate limit; capacity = max_in_flight so a full worker pool can start.
        self._primary_bucket = _TokenBucket(
            rate=header_requests_per_second, capacity=float(header_max_in_flight)
        )
        self._secondary_bucket = _TokenBucket(
            rate=header_requests_per_second, capacity=float(header_max_in_flight)
        )
        # (provider_id, block_number) -> finalized header only.
        self._header_cache: dict[tuple[str, int], CachedHeader] = {}
        self._header_cache_lock = threading.Lock()
        # Serializes raw-writer / receipt-db mutations under concurrent batch workers.
        self._io_lock = threading.Lock()

    def close(self) -> None:
        if self._owns_primary:
            self._primary_client.close()
        if self._owns_secondary:
            self._secondary_client.close()

    def clear_header_cache(self) -> None:
        with self._header_cache_lock:
            self._header_cache.clear()

    # -- transport ---------------------------------------------------------

    def _record_failure(
        self,
        receipts: sqlite3.Connection | None,
        *,
        pair: str,
        topic: str,
        provider_id: str,
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
        """Persist transport/protocol failure evidence. Fail closed on write error.

        Gate reports are proven from these tables. Swallowing an insert would let a
        failed run look clean, so sqlite errors re-raise as ``UniswapV2IngestionError``.
        """
        if receipts is None:
            return
        try:
            receipts.execute(
                f"INSERT INTO {FAILURE_TABLE} "
                "(chain, pair, topic, provider_id, method, request_json, start_block, "
                "end_block, failure_kind, status_code, raw_object_id, acquisition_id, "
                "detail, occurred_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ETHEREUM_CHAIN, pair, topic, provider_id, method, request_json,
                    start_block, end_block, kind, status_code, raw_object_id,
                    acquisition_id, detail, datetime.now(UTC).isoformat(),
                ),
            )
            receipts.commit()
        except sqlite3.Error as exc:
            raise UniswapV2IngestionError(
                f"failed to persist transport failure evidence for {provider_id} "
                f"{method} [{start_block}, {end_block}]: {exc}"
            ) from exc

    def _record_disagreement(
        self,
        receipts: sqlite3.Connection | None,
        *,
        pair: str,
        topic: str,
        start_block: int,
        end_block: int,
        detail: str,
        primary_logs_raw_object_id: str | None = None,
        secondary_logs_raw_object_id: str | None = None,
        primary_end_block_hash: str | None = None,
        secondary_end_block_hash: str | None = None,
        primary_log_count: int | None = None,
        secondary_log_count: int | None = None,
        primary_identity_sha256: str | None = None,
        secondary_identity_sha256: str | None = None,
    ) -> None:
        """Persist provider disagreement evidence. Fail closed on write error."""
        if receipts is None:
            return
        try:
            receipts.execute(
                f"INSERT INTO {DISAGREEMENT_TABLE} "
                "(chain, pair, topic, start_block, end_block, primary_provider_id, "
                "secondary_provider_id, primary_logs_raw_object_id, "
                "secondary_logs_raw_object_id, primary_end_block_hash, "
                "secondary_end_block_hash, primary_log_count, secondary_log_count, "
                "primary_identity_sha256, secondary_identity_sha256, detail, occurred_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ETHEREUM_CHAIN, pair, topic, start_block, end_block,
                    self._primary_provider_id, self._secondary_provider_id,
                    primary_logs_raw_object_id, secondary_logs_raw_object_id,
                    primary_end_block_hash, secondary_end_block_hash,
                    primary_log_count, secondary_log_count,
                    primary_identity_sha256, secondary_identity_sha256,
                    detail, datetime.now(UTC).isoformat(),
                ),
            )
            receipts.commit()
        except sqlite3.Error as exc:
            raise UniswapV2IngestionError(
                f"failed to persist provider disagreement evidence for "
                f"[{start_block}, {end_block}]: {exc}"
            ) from exc

    def _rpc(
        self,
        client: httpx.Client,
        rpc_url: str,
        provider_id: str,
        request: Mapping[str, Any],
        *,
        pair: str,
        topic: str,
        event_start: int,
        event_end: int,
        receipts: sqlite3.Connection | None,
    ) -> RpcCall:
        method = str(_require(request, "method", label="rpc request"))
        request_json = _canonical_json(request)
        acquired_at = datetime.now(UTC)
        try:
            response = client.post(rpc_url, json=dict(request))
        except httpx.HTTPError as exc:
            detail = f"transport failure ({provider_id}): {exc}"
            self._raw_writer.record_failed_acquisition(
                AcquisitionMetadata(
                    source_id=SOURCE_ID, request=dict(request), acquired_at=acquired_at
                ),
                detail,
            )
            self._record_failure(
                receipts, pair=pair, topic=topic, provider_id=provider_id, method=method,
                request_json=request_json, start_block=event_start, end_block=event_end,
                kind="transport", detail=detail,
            )
            raise UniswapV2IngestionError(
                f"JSON-RPC {method} transport failure on {provider_id}"
            ) from exc

        body = response.content
        acquired_at = datetime.now(UTC)
        raw = self._raw_writer.write_stream(
            [body],
            AcquisitionMetadata(
                source_id=SOURCE_ID,
                request=dict(request),
                response_metadata={
                    "status_code": response.status_code,
                    "method": method,
                    "provider_id": provider_id,
                },
                original_name=f"{provider_id}_{method}_{event_start}_{event_end}.json",
                acquired_at=acquired_at,
            ),
        )

        if response.is_error:
            detail = f"JSON-RPC HTTP {response.status_code} on {provider_id}"
            self._record_failure(
                receipts, pair=pair, topic=topic, provider_id=provider_id, method=method,
                request_json=request_json, start_block=event_start, end_block=event_end,
                kind="http_status", detail=detail, status_code=response.status_code,
                raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            detail = f"JSON-RPC {method} returned invalid JSON on {provider_id}"
            self._record_failure(
                receipts, pair=pair, topic=topic, provider_id=provider_id, method=method,
                request_json=request_json, start_block=event_start, end_block=event_end,
                kind="invalid_json", detail=detail, status_code=response.status_code,
                raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail) from exc

        if not isinstance(payload, dict):
            detail = f"JSON-RPC {method} response must be an object on {provider_id}"
            self._record_failure(
                receipts, pair=pair, topic=topic, provider_id=provider_id, method=method,
                request_json=request_json, start_block=event_start, end_block=event_end,
                kind="invalid_json", detail=detail, status_code=response.status_code,
                raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail)

        if payload.get("error") is not None:
            detail = f"JSON-RPC {method} failed on {provider_id}: {payload['error']!r}"
            self._record_failure(
                receipts, pair=pair, topic=topic, provider_id=provider_id, method=method,
                request_json=request_json, start_block=event_start, end_block=event_end,
                kind="rpc_error", detail=detail, status_code=response.status_code,
                raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail)

        return RpcCall(
            request=dict(request),
            payload=payload,
            raw_object_id=raw.raw_object_id,
            acquisition_id=raw.acquisition_id,
            acquired_at=acquired_at,
        )

    def _rpc_primary(
        self,
        request: Mapping[str, Any],
        *,
        pair: str,
        topic: str,
        event_start: int,
        event_end: int,
        receipts: sqlite3.Connection | None,
    ) -> RpcCall:
        return self._rpc(
            self._primary_client, self._primary_url, self._primary_provider_id, request,
            pair=pair, topic=topic, event_start=event_start, event_end=event_end,
            receipts=receipts,
        )

    def _rpc_secondary(
        self,
        request: Mapping[str, Any],
        *,
        pair: str,
        topic: str,
        event_start: int,
        event_end: int,
        receipts: sqlite3.Connection | None,
    ) -> RpcCall:
        return self._rpc(
            self._secondary_client, self._secondary_url, self._secondary_provider_id, request,
            pair=pair, topic=topic, event_start=event_start, event_end=event_end,
            receipts=receipts,
        )

    def _http_batch(
        self,
        client: httpx.Client,
        rpc_url: str,
        batch: list[dict[str, Any]],
        *,
        bucket: _TokenBucket,
    ) -> tuple[int, bytes, datetime]:
        """POST a JSON-RPC batch under the provider token bucket (thread-safe HTTP only)."""
        bucket.acquire()
        try:
            response = client.post(rpc_url, json=batch)
        except httpx.HTTPError as exc:
            raise UniswapV2IngestionError(
                f"JSON-RPC batch transport failure: {exc}"
            ) from exc
        return response.status_code, response.content, datetime.now(UTC)

    def _preserve_batch_response(
        self,
        *,
        provider_id: str,
        batch: list[dict[str, Any]],
        status_code: int,
        body: bytes,
        acquired_at: datetime,
        pair: str,
        topic: str,
        event_start: int,
        event_end: int,
        receipts: sqlite3.Connection | None,
        transport_error: str | None = None,
    ) -> RpcBatchCall:
        """Preserve batch bytes and validate payload on the caller thread (SQLite-safe)."""
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
                receipts, pair=pair, topic=topic, provider_id=provider_id, method=method,
                request_json=request_json, start_block=event_start, end_block=event_end,
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
                    "provider_id": provider_id,
                    "batch_size": len(batch),
                },
                original_name=f"{provider_id}_{method}_{event_start}_{event_end}.json",
                acquired_at=acquired_at,
            ),
        )

        if status_code >= 400:
            detail = f"JSON-RPC HTTP {status_code} on {provider_id} (batch)"
            self._record_failure(
                receipts, pair=pair, topic=topic, provider_id=provider_id, method=method,
                request_json=request_json, start_block=event_start, end_block=event_end,
                kind="http_status", detail=detail, status_code=status_code,
                raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            detail = f"JSON-RPC batch returned invalid JSON on {provider_id}"
            self._record_failure(
                receipts, pair=pair, topic=topic, provider_id=provider_id, method=method,
                request_json=request_json, start_block=event_start, end_block=event_end,
                kind="invalid_json", detail=detail, status_code=status_code,
                raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail) from exc

        if not isinstance(payload, list):
            detail = f"JSON-RPC batch response must be an array on {provider_id}"
            self._record_failure(
                receipts, pair=pair, topic=topic, provider_id=provider_id, method=method,
                request_json=request_json, start_block=event_start, end_block=event_end,
                kind="invalid_json", detail=detail, status_code=status_code,
                raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail)

        if len(payload) != len(batch):
            detail = (
                f"JSON-RPC batch size mismatch on {provider_id}: "
                f"sent {len(batch)}, received {len(payload)}"
            )
            self._record_failure(
                receipts, pair=pair, topic=topic, provider_id=provider_id, method=method,
                request_json=request_json, start_block=event_start, end_block=event_end,
                kind="rpc_error", detail=detail, status_code=status_code,
                raw_object_id=raw.raw_object_id, acquisition_id=raw.acquisition_id,
            )
            raise UniswapV2IngestionError(detail)

        for item in payload:
            if not isinstance(item, dict):
                raise UniswapV2IngestionError(
                    f"JSON-RPC batch element must be an object on {provider_id}"
                )
            if item.get("error") is not None:
                detail = f"JSON-RPC batch element failed on {provider_id}: {item['error']!r}"
                self._record_failure(
                    receipts, pair=pair, topic=topic, provider_id=provider_id,
                    method=method, request_json=request_json,
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

    @staticmethod
    def _assert_mainnet_payload(payload: Mapping[str, Any]) -> str:
        raw_chain_id = payload.get("result")
        if _hex_quantity(raw_chain_id, label="eth_chainId result") != 1:
            raise UniswapV2IngestionError(
                f"expected Ethereum mainnet chain id {ETHEREUM_MAINNET_CHAIN_ID}, "
                f"got {raw_chain_id!r}"
            )
        return ETHEREUM_MAINNET_CHAIN_ID

    def _assert_mainnet(
        self,
        *,
        pair: str,
        topic: str,
        receipts: sqlite3.Connection | None,
    ) -> RpcCall:
        if self._chain_call is not None:
            return self._chain_call
        # Chain identity is proven on the primary endpoint; both providers must still
        # agree on block hashes for every completed chunk.
        call = self._rpc_primary(
            chain_id_request(),
            pair=pair, topic=topic, event_start=0, event_end=0, receipts=receipts,
        )
        self._assert_mainnet_payload(call.payload)
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
                raise UniswapV2IngestionError(f"{label} batch request element must be an object")
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
        receipt: PairEventChunkReceipt,
        raw_root: Path,
        acquisitions: Mapping[str, AcquisitionRecord],
    ) -> None:
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
        self,
        receipt: PairEventChunkReceipt,
        acquisitions: Mapping[str, AcquisitionRecord],
    ) -> None:
        _authenticate_acquisition(
            acquisitions,
            acquisition_id=receipt.primary_logs_acquisition_id,
            raw_object_id=receipt.primary_logs_raw_object_id,
            request_json=receipt.primary_logs_request_json,
            acquired_at=receipt.primary_logs_acquired_at,
            label="primary logs response",
        )
        _authenticate_acquisition(
            acquisitions,
            acquisition_id=receipt.secondary_logs_acquisition_id,
            raw_object_id=receipt.secondary_logs_raw_object_id,
            request_json=receipt.secondary_logs_request_json,
            acquired_at=receipt.secondary_logs_acquired_at,
            label="secondary logs response",
        )
        _authenticate_acquisition(
            acquisitions,
            acquisition_id=receipt.primary_end_header_acquisition_id,
            raw_object_id=receipt.primary_end_header_raw_object_id,
            request_json=receipt.primary_end_header_request_json,
            acquired_at=receipt.primary_end_header_acquired_at,
            label="primary end-block header",
        )
        _authenticate_acquisition(
            acquisitions,
            acquisition_id=receipt.secondary_end_header_acquisition_id,
            raw_object_id=receipt.secondary_end_header_raw_object_id,
            request_json=receipt.secondary_end_header_request_json,
            acquired_at=receipt.secondary_end_header_acquired_at,
            label="secondary end-block header",
        )
        for dependency in receipt.header_dependencies:
            _authenticate_acquisition(
                acquisitions,
                acquisition_id=dependency.acquisition_id,
                raw_object_id=dependency.raw_object_id,
                request_json=dependency.request_json,
                acquired_at=dependency.acquired_at,
                label=f"primary header for block {dependency.block_number}",
            )
        for dependency in receipt.secondary_header_dependencies:
            _authenticate_acquisition(
                acquisitions,
                acquisition_id=dependency.acquisition_id,
                raw_object_id=dependency.raw_object_id,
                request_json=dependency.request_json,
                acquired_at=dependency.acquired_at,
                label=f"secondary header for block {dependency.block_number}",
            )

    def _verify_receipt_dependencies(
        self, receipt: PairEventChunkReceipt, raw_root: Path
    ) -> None:
        expected_logs_request = _canonical_json(
            pair_logs_request(
                pair=receipt.pair,
                topic=receipt.topic,
                start_block=receipt.start_block,
                end_block=receipt.end_block,
            )
        )
        if receipt.primary_logs_request_json != expected_logs_request:
            raise UniswapV2IngestionError(
                "primary logs request does not match the requested chunk"
            )
        if receipt.secondary_logs_request_json != expected_logs_request:
            raise UniswapV2IngestionError(
                "secondary logs request does not match the requested chunk"
            )
        if receipt.primary_provider_id == receipt.secondary_provider_id:
            raise UniswapV2IngestionError("receipt records identical provider ids")
        if receipt.reconciliation_status != "AGREED":
            raise UniswapV2IngestionError(
                f"receipt reconciliation status is {receipt.reconciliation_status!r}"
            )
        if receipt.end_block_hash != receipt.secondary_end_block_hash:
            raise UniswapV2IngestionError("receipt end-block hashes disagree")

        primary_logs = self._read_raw_json(raw_root, receipt.primary_logs_raw_object_id)
        secondary_logs = self._read_raw_json(raw_root, receipt.secondary_logs_raw_object_id)
        identities, digest = reconcile_log_sets(
            primary_logs.get("result"), secondary_logs.get("result")
        )
        if digest != receipt.log_identity_sha256:
            raise UniswapV2IngestionError(
                "preserved dual-provider logs no longer match the receipt identity digest"
            )
        if len(identities) != receipt.log_count:
            raise UniswapV2IngestionError(
                "preserved log count does not match the receipt"
            )

        self._authenticate_header(
            raw_root,
            raw_object_id=receipt.primary_end_header_raw_object_id,
            request_json=receipt.primary_end_header_request_json,
            expected_block_number=receipt.end_block,
            expected_block_hash=receipt.end_block_hash,
            label="primary end-block header",
        )
        self._authenticate_header(
            raw_root,
            raw_object_id=receipt.secondary_end_header_raw_object_id,
            request_json=receipt.secondary_end_header_request_json,
            expected_block_number=receipt.end_block,
            expected_block_hash=receipt.secondary_end_block_hash,
            label="secondary end-block header",
        )
        primary_by_block: dict[int, tuple[HeaderDependency, dict[str, Any]]] = {}
        for dependency in receipt.header_dependencies:
            header = self._authenticate_header(
                raw_root,
                raw_object_id=dependency.raw_object_id,
                request_json=dependency.request_json,
                expected_block_number=dependency.block_number,
                expected_block_hash=dependency.block_hash,
                label=f"primary header for block {dependency.block_number}",
                batch_index=dependency.batch_index,
            )
            primary_by_block[dependency.block_number] = (dependency, header)

        secondary_by_block: dict[int, tuple[HeaderDependency, dict[str, Any]]] = {}
        for dependency in receipt.secondary_header_dependencies:
            header = self._authenticate_header(
                raw_root,
                raw_object_id=dependency.raw_object_id,
                request_json=dependency.request_json,
                expected_block_number=dependency.block_number,
                expected_block_hash=dependency.block_hash,
                label=f"secondary header for block {dependency.block_number}",
                batch_index=dependency.batch_index,
            )
            secondary_by_block[dependency.block_number] = (dependency, header)

        # Dual event-block lineage is mandatory offline: every primary event block must
        # have a secondary peer with matching hash and timestamp evidence.
        primary_blocks = set(primary_by_block)
        secondary_blocks = set(secondary_by_block)
        if primary_blocks != secondary_blocks:
            missing_secondary = sorted(primary_blocks - secondary_blocks)
            missing_primary = sorted(secondary_blocks - primary_blocks)
            raise UniswapV2IngestionError(
                "secondary event-block header lineage incomplete: "
                f"missing_secondary={missing_secondary} missing_primary={missing_primary}"
            )
        for block_number in sorted(primary_blocks):
            primary_dep, primary_header = primary_by_block[block_number]
            secondary_dep, secondary_header = secondary_by_block[block_number]
            if primary_dep.block_hash != secondary_dep.block_hash:
                raise UniswapV2IngestionError(
                    f"offline event-block hash disagreement at {block_number}: "
                    f"primary={primary_dep.block_hash} secondary={secondary_dep.block_hash}"
                )
            primary_ts = _hex_quantity(
                _require(primary_header, "timestamp", label="primary block header"),
                label="primary header timestamp",
            )
            secondary_ts = _hex_quantity(
                _require(secondary_header, "timestamp", label="secondary block header"),
                label="secondary header timestamp",
            )
            if primary_ts != secondary_ts:
                raise UniswapV2IngestionError(
                    f"offline event-block timestamp disagreement at {block_number}: "
                    f"primary={primary_ts} secondary={secondary_ts}"
                )
        # Event blocks present in dual-agreed logs must all appear in header lineage.
        event_blocks = {identity.block_number for identity in identities}
        if event_blocks != primary_blocks:
            raise UniswapV2IngestionError(
                "event-block header lineage does not match dual-agreed log blocks: "
                f"logs={sorted(event_blocks)} headers={sorted(primary_blocks)}"
            )

        _parse_timestamp(receipt.primary_logs_acquired_at, label="primary logs_acquired_at")
        _parse_timestamp(receipt.secondary_logs_acquired_at, label="secondary logs_acquired_at")
        _parse_timestamp(receipt.completed_at, label="receipt completed_at")

    # -- header cache / batched acquisition --------------------------------

    def _cacheable_block(self, block_number: int) -> bool:
        cutoff = self._finality_cutoff_block
        return cutoff is not None and block_number < cutoff

    def _get_cached_header(self, provider_id: str, block_number: int) -> CachedHeader | None:
        if not self._cacheable_block(block_number):
            return None
        with self._header_cache_lock:
            return self._header_cache.get((provider_id, block_number))

    def _put_cached_header(self, entry: CachedHeader) -> None:
        if not self._cacheable_block(entry.block_number):
            return
        with self._header_cache_lock:
            self._header_cache[(entry.provider_id, entry.block_number)] = entry

    def _header_from_single_call(
        self,
        call: RpcCall,
        *,
        provider_id: str,
        expected_block_number: int,
    ) -> CachedHeader:
        header = call.payload.get("result")
        if not isinstance(header, dict):
            raise UniswapV2IngestionError(
                f"missing block header for block {expected_block_number} on {provider_id}"
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
            provider_id=provider_id,
        )
        self._put_cached_header(entry)
        return entry

    def _fetch_headers_for_blocks(
        self,
        block_numbers: Sequence[int],
        *,
        is_primary: bool,
        pair: str,
        topic: str,
        receipts: sqlite3.Connection | None,
    ) -> dict[int, CachedHeader]:
        """Acquire headers for distinct blocks via cache, sequential, or JSON-RPC batch.

        Does not serve resume-path reorg checks — callers must use live single RPCs
        for those. Only blocks strictly below ``finality_cutoff_block`` enter the cache.
        """
        provider_id = (
            self._primary_provider_id if is_primary else self._secondary_provider_id
        )
        client = self._primary_client if is_primary else self._secondary_client
        rpc_url = self._primary_url if is_primary else self._secondary_url
        bucket = self._primary_bucket if is_primary else self._secondary_bucket
        rpc_single = self._rpc_primary if is_primary else self._rpc_secondary

        ordered = sorted({int(number) for number in block_numbers})
        results: dict[int, CachedHeader] = {}
        to_fetch: list[int] = []
        for number in ordered:
            cached = self._get_cached_header(provider_id, number)
            if cached is not None:
                results[number] = cached
            else:
                to_fetch.append(number)
        if not to_fetch:
            return results

        if not self._use_header_batches:
            for number in to_fetch:
                call = rpc_single(
                    block_header_request(number),
                    pair=pair, topic=topic,
                    event_start=number, event_end=number, receipts=receipts,
                )
                results[number] = self._header_from_single_call(
                    call, provider_id=provider_id, expected_block_number=number
                )
            return results

        batches = [
            to_fetch[index:index + self._header_batch_size]
            for index in range(0, len(to_fetch), self._header_batch_size)
        ]

        def run_http(
            blocks: list[int],
        ) -> tuple[list[int], list[dict[str, Any]], int | None, bytes | None, datetime, str | None]:
            request = block_header_batch_request(blocks)
            try:
                status_code, body, acquired_at = self._http_batch(
                    client, rpc_url, request, bucket=bucket
                )
                return blocks, request, status_code, body, acquired_at, None
            except UniswapV2IngestionError as exc:
                return blocks, request, None, None, datetime.now(UTC), str(exc)

        # Bounded concurrency on HTTP only. Raw-store / SQLite preservation stays
        # on this thread so catalog connections remain single-threaded.
        with ThreadPoolExecutor(max_workers=self._header_max_in_flight) as executor:
            futures = [executor.submit(run_http, batch) for batch in batches]
            for future in as_completed(futures):
                blocks, request, status_code, body, acquired_at, transport_error = (
                    future.result()
                )
                if transport_error is not None or status_code is None or body is None:
                    self._preserve_batch_response(
                        provider_id=provider_id,
                        batch=request,
                        status_code=0,
                        body=b"",
                        acquired_at=acquired_at,
                        pair=pair, topic=topic,
                        event_start=blocks[0], event_end=blocks[-1],
                        receipts=receipts,
                        transport_error=transport_error or "JSON-RPC batch transport failure",
                    )
                    raise AssertionError("transport failure must raise")  # pragma: no cover
                batch_call = self._preserve_batch_response(
                    provider_id=provider_id,
                    batch=request,
                    status_code=status_code,
                    body=body,
                    acquired_at=acquired_at,
                    pair=pair, topic=topic,
                    event_start=blocks[0], event_end=blocks[-1],
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
                            f"missing batch header for block {number} on {provider_id}"
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
                        provider_id=provider_id,
                    )
                    self._put_cached_header(entry)
                    results[number] = entry
        return results

    # -- token decimals ----------------------------------------------------

    def _replay_token_decimals_receipt(
        self,
        receipt: TokenDecimalsReceipt,
        *,
        raw_root: Path,
        receipts: sqlite3.Connection,
    ) -> TokenDecimalsRow:
        """Re-authenticate a completed decimals receipt from preserved bytes only."""
        expected_request = _canonical_json(
            token_decimals_request(token=receipt.token, block_number=receipt.block_number)
        )
        if receipt.primary_request_json != expected_request:
            raise UniswapV2IngestionError(
                "decimals receipt primary request does not match token/block identity"
            )
        if receipt.secondary_request_json != expected_request:
            raise UniswapV2IngestionError(
                "decimals receipt secondary request does not match token/block identity"
            )
        if receipt.primary_provider_id == receipt.secondary_provider_id:
            raise UniswapV2IngestionError(
                "decimals receipt primary and secondary provider ids must differ"
            )
        acquisitions = _load_acquisitions(
            receipts, sorted(receipt.acquisition_ids)
        )
        _authenticate_acquisition(
            acquisitions,
            acquisition_id=receipt.primary_acquisition_id,
            raw_object_id=receipt.primary_raw_object_id,
            request_json=receipt.primary_request_json,
            acquired_at=receipt.primary_acquired_at,
            label="decimals primary acquisition",
        )
        _authenticate_acquisition(
            acquisitions,
            acquisition_id=receipt.secondary_acquisition_id,
            raw_object_id=receipt.secondary_raw_object_id,
            request_json=receipt.secondary_request_json,
            acquired_at=receipt.secondary_acquired_at,
            label="decimals secondary acquisition",
        )
        primary_payload = self._read_raw_json(raw_root, receipt.primary_raw_object_id)
        secondary_payload = self._read_raw_json(raw_root, receipt.secondary_raw_object_id)
        primary_decimals = decode_token_decimals(primary_payload)
        secondary_decimals = decode_token_decimals(secondary_payload)
        if primary_decimals != secondary_decimals:
            raise UniswapV2IngestionError(
                f"preserved decimals disagree for {receipt.token}: "
                f"primary={primary_decimals} secondary={secondary_decimals}"
            )
        if primary_decimals != receipt.decimals:
            raise UniswapV2IngestionError(
                f"decimals receipt value {receipt.decimals} does not match "
                f"preserved dual-agreed value {primary_decimals}"
            )
        retrieved_at = max(
            _parse_timestamp(receipt.primary_acquired_at, label="primary acquired_at"),
            _parse_timestamp(receipt.secondary_acquired_at, label="secondary acquired_at"),
        )
        return TokenDecimalsRow(
            chain=ETHEREUM_CHAIN,
            token=receipt.token,
            decimals=primary_decimals,
            block_number=receipt.block_number,
            retrieved_at=retrieved_at,
            primary_raw_object_id=receipt.primary_raw_object_id,
            secondary_raw_object_id=receipt.secondary_raw_object_id,
            primary_provider_id=receipt.primary_provider_id,
            secondary_provider_id=receipt.secondary_provider_id,
        )

    def fetch_token_decimals(
        self,
        *,
        token: str,
        block_number: int | str = "latest",
        receipt_db_path: str | None = None,
        raw_root: Path | None = None,
    ) -> TokenDecimalsRow:
        """Acquire ERC-20 decimals() via both RPCs; require exact agreement.

        Decimals drive orientation, OHLC, and volume (blocking gate 3). A single
        provider's answer is not authority.

        When ``receipt_db_path`` is set, ``block_number`` must be an integer block
        (not ``\"latest\"``). Successful dual-provider results are written to
        ``uniswap_v2_token_decimals_receipt`` and subsequent calls resume by
        re-authenticating preserved raw bytes — no silent reacquisition.
        """
        if not isinstance(token, str) or not token.startswith("0x") or len(token) != 42:
            raise ValueError(f"token must be a 20-byte 0x address, got {token!r}")
        token_n = token.lower()
        receipts = sqlite3.connect(receipt_db_path) if receipt_db_path else None
        try:
            if receipts is not None:
                receipts.execute("PRAGMA foreign_keys = ON")
                if isinstance(block_number, str):
                    raise UniswapV2IngestionError(
                        "block_number must be an integer when durable decimals "
                        "receipts are enabled (receipt_db_path is set); "
                        f"got {block_number!r}"
                    )
                event_block = int(block_number)
                if event_block < 0:
                    raise UniswapV2IngestionError(
                        f"block_number must be >= 0, got {event_block}"
                    )
                prior = receipts.execute(
                    f"SELECT {', '.join(_DECIMALS_RECEIPT_COLUMNS)} "
                    f"FROM {DECIMALS_RECEIPT_TABLE} "
                    "WHERE chain = ? AND token = ? AND block_number = ?",
                    (ETHEREUM_CHAIN, token_n, event_block),
                ).fetchone()
                if prior is not None:
                    verify_root = self._resolve_raw_root(raw_root)
                    return self._replay_token_decimals_receipt(
                        _decimals_receipt_from_row(prior),
                        raw_root=verify_root,
                        receipts=receipts,
                    )

            request = token_decimals_request(token=token_n, block_number=block_number)
            event_block = 0 if isinstance(block_number, str) else int(block_number)
            primary_call = self._rpc_primary(
                request,
                pair=token_n,
                topic=DECIMALS_SELECTOR,
                event_start=event_block,
                event_end=event_block,
                receipts=receipts,
            )
            secondary_call = self._rpc_secondary(
                request,
                pair=token_n,
                topic=DECIMALS_SELECTOR,
                event_start=event_block,
                event_end=event_block,
                receipts=receipts,
            )
            primary_decimals = decode_token_decimals(primary_call.payload)
            secondary_decimals = decode_token_decimals(secondary_call.payload)
            if primary_decimals != secondary_decimals:
                self._record_disagreement(
                    receipts,
                    pair=token_n,
                    topic=DECIMALS_SELECTOR,
                    start_block=event_block,
                    end_block=event_block,
                    detail=(
                        f"token decimals disagreement for {token_n}: "
                        f"primary={primary_decimals} secondary={secondary_decimals}"
                    ),
                    primary_logs_raw_object_id=primary_call.raw_object_id,
                    secondary_logs_raw_object_id=secondary_call.raw_object_id,
                )
                raise UniswapV2IngestionError(
                    f"token decimals disagreement for {token_n}: "
                    f"primary={primary_decimals} secondary={secondary_decimals}"
                )
            resolved_block = None if isinstance(block_number, str) else int(block_number)
            if receipts is not None:
                if resolved_block is None:
                    raise UniswapV2IngestionError(
                        "internal error: durable decimals path requires integer block"
                    )
                completed_at = max(primary_call.acquired_at, secondary_call.acquired_at)
                receipts.execute(
                    f"INSERT INTO {DECIMALS_RECEIPT_TABLE} "
                    f"({', '.join(_DECIMALS_RECEIPT_COLUMNS)}) "
                    "VALUES (" + ", ".join("?" * len(_DECIMALS_RECEIPT_COLUMNS)) + ")",
                    (
                        ETHEREUM_CHAIN,
                        ETHEREUM_MAINNET_CHAIN_ID,
                        token_n,
                        resolved_block,
                        primary_decimals,
                        self._primary_provider_id,
                        self._secondary_provider_id,
                        primary_call.request_json,
                        primary_call.raw_object_id,
                        primary_call.acquisition_id,
                        primary_call.acquired_at.isoformat(),
                        secondary_call.request_json,
                        secondary_call.raw_object_id,
                        secondary_call.acquisition_id,
                        secondary_call.acquired_at.isoformat(),
                        completed_at.isoformat(),
                    ),
                )
                receipts.commit()
            return TokenDecimalsRow(
                chain=ETHEREUM_CHAIN,
                token=token_n,
                decimals=primary_decimals,
                block_number=resolved_block,
                retrieved_at=max(primary_call.acquired_at, secondary_call.acquired_at),
                primary_raw_object_id=primary_call.raw_object_id,
                secondary_raw_object_id=secondary_call.raw_object_id,
                primary_provider_id=self._primary_provider_id,
                secondary_provider_id=self._secondary_provider_id,
            )
        finally:
            if receipts is not None:
                receipts.close()

    # -- acquisition -------------------------------------------------------

    def fetch(
        self,
        *,
        pair: str,
        kind: EventKind,
        start_block: int,
        end_block: int,
        chunk_size: int,
        receipt_db_path: str | None = None,
        emit_rows: bool = True,
        raw_root: Path | None = None,
    ) -> list[PairEventRow]:
        if not isinstance(pair, str) or not pair.startswith("0x") or len(pair) != 42:
            raise ValueError(f"pair must be a 20-byte 0x address, got {pair!r}")
        pair = pair.lower()
        if start_block < UNISWAP_V2_DEPLOYMENT_BLOCK:
            raise UniswapV2IngestionError(
                f"start_block must be >= Uniswap V2 deployment block "
                f"{UNISWAP_V2_DEPLOYMENT_BLOCK}, got {start_block}"
            )
        if end_block < start_block or chunk_size <= 0:
            raise ValueError("invalid block range or chunk_size")
        topic = topic_for_kind(kind)

        rows: list[PairEventRow] = []
        receipts = sqlite3.connect(receipt_db_path) if receipt_db_path else None
        try:
            if receipts is not None:
                receipts.execute("PRAGMA foreign_keys = ON")
            chain_call = self._assert_mainnet(pair=pair, topic=topic, receipts=receipts)
            verify_root = self._raw_root if raw_root is None else raw_root

            for chunk_start in range(start_block, end_block + 1, chunk_size):
                chunk_end = min(chunk_start + chunk_size - 1, end_block)

                if receipts is not None:
                    prior = receipts.execute(
                        f"SELECT {', '.join(_RECEIPT_COLUMNS)} FROM {RECEIPT_TABLE} "
                        "WHERE chain = ? AND pair = ? AND topic = ? "
                        "AND start_block = ? AND end_block = ?",
                        (ETHEREUM_CHAIN, pair, topic, chunk_start, chunk_end),
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
                        self._verify_chain_lineage(receipt, verify_root, prior_acquisitions)
                        self._authenticate_receipt_acquisitions(receipt, prior_acquisitions)
                        # Live reorg check against both providers.
                        primary_end = self._rpc_primary(
                            block_header_request(chunk_end),
                            pair=pair, topic=topic,
                            event_start=chunk_end, event_end=chunk_end, receipts=receipts,
                        )
                        secondary_end = self._rpc_secondary(
                            block_header_request(chunk_end),
                            pair=pair, topic=topic,
                            event_start=chunk_end, event_end=chunk_end, receipts=receipts,
                        )
                        for end_call, label in (
                            (primary_end, "primary"),
                            (secondary_end, "secondary"),
                        ):
                            live_header = end_call.payload.get("result")
                            if not isinstance(live_header, dict):
                                raise UniswapV2IngestionError(
                                    f"missing {label} end-block header on resume"
                                )
                            live_hash = _hex_bytes(
                                _require(live_header, "hash", label=f"{label} end-block header"),
                                32, label=f"{label} end-block header hash",
                            )
                            if live_hash != _hex_bytes(
                                receipt.end_block_hash, 32, label="receipt end_block_hash"
                            ):
                                raise UniswapV2IngestionError(
                                    f"completed chunk receipt failed {label} end-block "
                                    "validation"
                                )
                        if emit_rows:
                            raise UniswapV2IngestionError(
                                f"chunk [{chunk_start}, {chunk_end}] is already complete; "
                                "fetch(emit_rows=True) cannot return its rows -- acquire "
                                "with emit_rows=False and decode via replay_receipts()"
                            )
                        continue

                request = pair_logs_request(
                    pair=pair, topic=topic, start_block=chunk_start, end_block=chunk_end
                )
                primary_logs_call = self._rpc_primary(
                    request,
                    pair=pair, topic=topic,
                    event_start=chunk_start, event_end=chunk_end, receipts=receipts,
                )
                secondary_logs_call = self._rpc_secondary(
                    request,
                    pair=pair, topic=topic,
                    event_start=chunk_start, event_end=chunk_end, receipts=receipts,
                )

                primary_result = primary_logs_call.payload.get("result")
                secondary_result = secondary_logs_call.payload.get("result")
                try:
                    identities, digest = reconcile_log_sets(primary_result, secondary_result)
                except UniswapV2IngestionError as exc:
                    primary_count: int | None = (
                        len(primary_result) if isinstance(primary_result, list) else None
                    )
                    secondary_count: int | None = (
                        len(secondary_result) if isinstance(secondary_result, list) else None
                    )
                    primary_digest: str | None = None
                    secondary_digest: str | None = None
                    try:
                        if isinstance(primary_result, list):
                            primary_digest = log_identity_digest(
                                [extract_log_identity(log) for log in primary_result]
                            )
                    except UniswapV2IngestionError:
                        primary_digest = None
                    try:
                        if isinstance(secondary_result, list):
                            secondary_digest = log_identity_digest(
                                [extract_log_identity(log) for log in secondary_result]
                            )
                    except UniswapV2IngestionError:
                        secondary_digest = None
                    self._record_disagreement(
                        receipts,
                        pair=pair, topic=topic,
                        start_block=chunk_start, end_block=chunk_end,
                        detail=str(exc),
                        primary_logs_raw_object_id=primary_logs_call.raw_object_id,
                        secondary_logs_raw_object_id=secondary_logs_call.raw_object_id,
                        primary_log_count=primary_count,
                        secondary_log_count=secondary_count,
                        primary_identity_sha256=primary_digest,
                        secondary_identity_sha256=secondary_digest,
                    )
                    raise

                for identity in identities:
                    if identity.block_number < chunk_start or identity.block_number > chunk_end:
                        raise UniswapV2IngestionError(
                            "RPC returned log outside requested chunk"
                        )

                # Dual end-block identity: both providers must report the same hash.
                primary_end_call = self._rpc_primary(
                    block_header_request(chunk_end),
                    pair=pair, topic=topic,
                    event_start=chunk_end, event_end=chunk_end, receipts=receipts,
                )
                secondary_end_call = self._rpc_secondary(
                    block_header_request(chunk_end),
                    pair=pair, topic=topic,
                    event_start=chunk_end, event_end=chunk_end, receipts=receipts,
                )
                primary_end_header = primary_end_call.payload.get("result")
                secondary_end_header = secondary_end_call.payload.get("result")
                if not isinstance(primary_end_header, dict):
                    raise UniswapV2IngestionError("missing primary end-block header")
                if not isinstance(secondary_end_header, dict):
                    raise UniswapV2IngestionError("missing secondary end-block header")
                primary_end_number = _hex_quantity(
                    _require(primary_end_header, "number", label="primary end-block header"),
                    label="primary end-block header number",
                )
                secondary_end_number = _hex_quantity(
                    _require(secondary_end_header, "number", label="secondary end-block header"),
                    label="secondary end-block header number",
                )
                if primary_end_number != chunk_end or secondary_end_number != chunk_end:
                    raise UniswapV2IngestionError(
                        f"end-block header number mismatch: primary={primary_end_number} "
                        f"secondary={secondary_end_number} expected={chunk_end}"
                    )
                primary_end_hash = _hex_bytes(
                    _require(primary_end_header, "hash", label="primary end-block header"),
                    32, label="primary end-block header hash",
                )
                secondary_end_hash = _hex_bytes(
                    _require(secondary_end_header, "hash", label="secondary end-block header"),
                    32, label="secondary end-block header hash",
                )
                if primary_end_hash != secondary_end_hash:
                    self._record_disagreement(
                        receipts,
                        pair=pair, topic=topic,
                        start_block=chunk_start, end_block=chunk_end,
                        detail=(
                            f"end-block hash disagreement: primary={primary_end_hash} "
                            f"secondary={secondary_end_hash}"
                        ),
                        primary_logs_raw_object_id=primary_logs_call.raw_object_id,
                        secondary_logs_raw_object_id=secondary_logs_call.raw_object_id,
                        primary_end_block_hash=primary_end_hash,
                        secondary_end_block_hash=secondary_end_hash,
                        primary_log_count=len(identities),
                        secondary_log_count=len(identities),
                        primary_identity_sha256=digest,
                        secondary_identity_sha256=digest,
                    )
                    raise UniswapV2IngestionError(
                        f"end-block hash disagreement at {chunk_end}: "
                        f"primary={primary_end_hash} secondary={secondary_end_hash}"
                    )

                # Event-block headers from both providers. Hash must match the dual-
                # agreed log block hash; timestamps must also agree so event_time and
                # source_available_at never rest on a single provider's header body.
                # End-block headers already dual-fetched above are reused for events on
                # chunk_end; remaining distinct event blocks are batch-fetched with
                # bounded concurrency (or sequential when use_header_batches=False).
                block_hash_by_number: dict[int, str] = {}
                for identity in identities:
                    previous_hash = block_hash_by_number.get(identity.block_number)
                    if previous_hash is not None and previous_hash != identity.block_hash:
                        raise UniswapV2IngestionError(
                            f"conflicting log block hashes for block "
                            f"{identity.block_number}"
                        )
                    block_hash_by_number[identity.block_number] = identity.block_hash
                event_blocks = sorted(block_hash_by_number)

                # Seed cache-eligible end-block headers; always available as singles.
                primary_end_entry = self._header_from_single_call(
                    primary_end_call,
                    provider_id=self._primary_provider_id,
                    expected_block_number=chunk_end,
                )
                secondary_end_entry = self._header_from_single_call(
                    secondary_end_call,
                    provider_id=self._secondary_provider_id,
                    expected_block_number=chunk_end,
                )

                blocks_to_fetch = [number for number in event_blocks if number != chunk_end]
                primary_headers = self._fetch_headers_for_blocks(
                    blocks_to_fetch,
                    is_primary=True,
                    pair=pair, topic=topic, receipts=receipts,
                )
                secondary_headers = self._fetch_headers_for_blocks(
                    blocks_to_fetch,
                    is_primary=False,
                    pair=pair, topic=topic, receipts=receipts,
                )
                primary_headers[chunk_end] = primary_end_entry
                secondary_headers[chunk_end] = secondary_end_entry

                headers: dict[int, tuple[dict[str, Any], str]] = {}
                dependencies: list[HeaderDependency] = []
                secondary_dependencies: list[HeaderDependency] = []
                for number in event_blocks:
                    primary_entry = primary_headers[number]
                    secondary_entry = secondary_headers[number]
                    agreed_log_hash = block_hash_by_number[number]
                    if (
                        primary_entry.block_hash != agreed_log_hash
                        or secondary_entry.block_hash != agreed_log_hash
                    ):
                        self._record_disagreement(
                            receipts,
                            pair=pair, topic=topic,
                            start_block=chunk_start, end_block=chunk_end,
                            detail=(
                                f"event-block hash disagreement at {number}: "
                                f"primary={primary_entry.block_hash} "
                                f"secondary={secondary_entry.block_hash} "
                                f"agreed_log={agreed_log_hash}"
                            ),
                            primary_logs_raw_object_id=primary_logs_call.raw_object_id,
                            secondary_logs_raw_object_id=secondary_logs_call.raw_object_id,
                            primary_end_block_hash=primary_entry.block_hash,
                            secondary_end_block_hash=secondary_entry.block_hash,
                            primary_log_count=len(identities),
                            secondary_log_count=len(identities),
                            primary_identity_sha256=digest,
                            secondary_identity_sha256=digest,
                        )
                        raise UniswapV2IngestionError(
                            f"event-block hash disagreement at {number}: "
                            f"primary={primary_entry.block_hash} "
                            f"secondary={secondary_entry.block_hash} "
                            f"agreed_log={agreed_log_hash}"
                        )
                    primary_timestamp = _hex_quantity(
                        _require(primary_entry.header, "timestamp", label="primary block header"),
                        label="primary header timestamp",
                    )
                    secondary_timestamp = _hex_quantity(
                        _require(
                            secondary_entry.header, "timestamp", label="secondary block header"
                        ),
                        label="secondary header timestamp",
                    )
                    if primary_timestamp != secondary_timestamp:
                        self._record_disagreement(
                            receipts,
                            pair=pair, topic=topic,
                            start_block=chunk_start, end_block=chunk_end,
                            detail=(
                                f"event-block timestamp disagreement at {number}: "
                                f"primary={primary_timestamp} secondary={secondary_timestamp}"
                            ),
                            primary_logs_raw_object_id=primary_logs_call.raw_object_id,
                            secondary_logs_raw_object_id=secondary_logs_call.raw_object_id,
                            primary_end_block_hash=primary_entry.block_hash,
                            secondary_end_block_hash=secondary_entry.block_hash,
                            primary_log_count=len(identities),
                            secondary_log_count=len(identities),
                            primary_identity_sha256=digest,
                            secondary_identity_sha256=digest,
                        )
                        raise UniswapV2IngestionError(
                            f"event-block timestamp disagreement at {number}: "
                            f"primary={primary_timestamp} secondary={secondary_timestamp}"
                        )

                    # Primary headers decode rows; secondary headers are retained so
                    # offline replay can re-prove dual hash/timestamp authority.
                    headers[number] = (primary_entry.header, primary_entry.raw_object_id)
                    dependencies.append(HeaderDependency(
                        block_number=number,
                        block_hash=primary_entry.block_hash,
                        request_json=primary_entry.request_json,
                        raw_object_id=primary_entry.raw_object_id,
                        acquisition_id=primary_entry.acquisition_id,
                        acquired_at=primary_entry.acquired_at,
                        batch_index=primary_entry.batch_index,
                    ))
                    secondary_dependencies.append(HeaderDependency(
                        block_number=number,
                        block_hash=secondary_entry.block_hash,
                        request_json=secondary_entry.request_json,
                        raw_object_id=secondary_entry.raw_object_id,
                        acquisition_id=secondary_entry.acquisition_id,
                        acquired_at=secondary_entry.acquired_at,
                        batch_index=secondary_entry.batch_index,
                    ))

                # Deterministic receipt bytes independent of concurrent fetch order.
                dependencies.sort(key=lambda dep: dep.block_number)
                secondary_dependencies.sort(key=lambda dep: dep.block_number)

                if emit_rows:
                    # retrieved_at is the later of the two logs acquisitions — both
                    # must have succeeded for the row to be authority.
                    retrieved_at = max(
                        primary_logs_call.acquired_at, secondary_logs_call.acquired_at
                    )
                    rows.extend(decode_pair_event_logs(
                        primary_logs_call.payload,
                        headers,
                        pair=pair,
                        topic=topic,
                        log_raw_object_id=primary_logs_call.raw_object_id,
                        retrieved_at=retrieved_at,
                        primary_provider_id=self._primary_provider_id,
                        secondary_provider_id=self._secondary_provider_id,
                    ))

                if receipts is not None:
                    completed_at = max(
                        [
                            primary_logs_call.acquired_at,
                            secondary_logs_call.acquired_at,
                            primary_end_call.acquired_at,
                            secondary_end_call.acquired_at,
                            *(
                                _parse_timestamp(dep.acquired_at, label="header acquired_at")
                                for dep in dependencies
                            ),
                            *(
                                _parse_timestamp(
                                    dep.acquired_at, label="secondary header acquired_at"
                                )
                                for dep in secondary_dependencies
                            ),
                        ]
                    )
                    receipts.execute(
                        f"INSERT INTO {RECEIPT_TABLE} "
                        f"({', '.join(_RECEIPT_COLUMNS)}) "
                        "VALUES (" + ", ".join("?" * len(_RECEIPT_COLUMNS)) + ")",
                        (
                            ETHEREUM_CHAIN, ETHEREUM_MAINNET_CHAIN_ID, pair, topic,
                            chunk_start, chunk_end,
                            self._primary_provider_id,
                            primary_logs_call.request_json,
                            primary_logs_call.raw_object_id,
                            primary_logs_call.acquisition_id,
                            primary_logs_call.acquired_at.isoformat(),
                            self._secondary_provider_id,
                            secondary_logs_call.request_json,
                            secondary_logs_call.raw_object_id,
                            secondary_logs_call.acquisition_id,
                            secondary_logs_call.acquired_at.isoformat(),
                            len(identities), digest, "AGREED",
                            chunk_end, primary_end_hash,
                            primary_end_call.request_json,
                            primary_end_call.raw_object_id,
                            primary_end_call.acquisition_id,
                            primary_end_call.acquired_at.isoformat(),
                            secondary_end_hash,
                            secondary_end_call.request_json,
                            secondary_end_call.raw_object_id,
                            secondary_end_call.acquisition_id,
                            secondary_end_call.acquired_at.isoformat(),
                            json.dumps(
                                [dep.as_dict() for dep in dependencies],
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                            completed_at.isoformat(),
                            chain_call.request_json,
                            chain_call.raw_object_id,
                            chain_call.acquisition_id,
                            chain_call.acquired_at.isoformat(),
                            json.dumps(
                                [dep.as_dict() for dep in secondary_dependencies],
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                        ),
                    )
                    receipts.commit()

            identities = [(row.tx_hash, row.log_index) for row in rows]
            if len(identities) != len(set(identities)):
                raise UniswapV2IngestionError(
                    "fetched rows contain duplicate (tx_hash, log_index)"
                )
            return sorted(
                rows, key=lambda row: (row.block_number, row.tx_index, row.log_index)
            )
        finally:
            if receipts is not None:
                receipts.close()

    # -- replay ------------------------------------------------------------

    def replay_receipts(
        self,
        *,
        pair: str,
        kind: EventKind,
        start_block: int,
        end_block: int,
        receipt_db_path: str,
        raw_root: Path | None = None,
    ) -> PairEventReplayResult:
        """Decode only preserved dual-provider receipt bytes; never contacts the network."""
        if not isinstance(pair, str) or not pair.startswith("0x") or len(pair) != 42:
            raise ValueError(f"pair must be a 20-byte 0x address, got {pair!r}")
        pair = pair.lower()
        topic = topic_for_kind(kind)
        root = self._resolve_raw_root(raw_root)
        conn = sqlite3.connect(receipt_db_path)
        try:
            rows_raw = conn.execute(
                f"SELECT {', '.join(_RECEIPT_COLUMNS)} FROM {RECEIPT_TABLE} "
                "WHERE chain = ? AND pair = ? AND topic = ? "
                "AND start_block >= ? AND end_block <= ? ORDER BY start_block",
                (ETHEREUM_CHAIN, pair, topic, start_block, end_block),
            ).fetchall()
            receipts = [_receipt_from_row(row) for row in rows_raw]
            acquisitions = _load_acquisitions(
                conn, [aid for receipt in receipts for aid in sorted(receipt.acquisition_ids)]
            )
        finally:
            conn.close()

        expected = start_block
        rows: list[PairEventRow] = []
        raw_ids: set[str] = set()
        acquisition_ids: set[str] = set()
        digests: list[str] = []

        for receipt in receipts:
            if receipt.start_block != expected or receipt.end_block < receipt.start_block:
                raise UniswapV2IngestionError("receipt coverage is not contiguous")
            if receipt.pair != pair or receipt.topic != topic:
                raise UniswapV2IngestionError("receipt pair/topic does not match replay request")

            self._verify_chain_lineage(receipt, root, acquisitions)
            self._authenticate_receipt_acquisitions(receipt, acquisitions)
            self._verify_receipt_dependencies(receipt, root)

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

            retrieved_at = max(
                _parse_timestamp(
                    receipt.primary_logs_acquired_at, label="primary logs_acquired_at"
                ),
                _parse_timestamp(
                    receipt.secondary_logs_acquired_at, label="secondary logs_acquired_at"
                ),
            )
            chunk_rows = decode_pair_event_logs(
                self._read_raw_json(root, receipt.primary_logs_raw_object_id),
                headers,
                pair=pair,
                topic=topic,
                log_raw_object_id=receipt.primary_logs_raw_object_id,
                retrieved_at=retrieved_at,
                primary_provider_id=receipt.primary_provider_id,
                secondary_provider_id=receipt.secondary_provider_id,
            )
            for row in chunk_rows:
                if not receipt.start_block <= row.block_number <= receipt.end_block:
                    raise UniswapV2IngestionError(
                        f"preserved log for block {row.block_number} is outside receipt "
                        f"range [{receipt.start_block}, {receipt.end_block}]"
                    )
            rows.extend(chunk_rows)
            raw_ids |= receipt.raw_object_ids
            acquisition_ids |= receipt.acquisition_ids
            digests.append(receipt.log_identity_sha256)
            expected = receipt.end_block + 1

        if expected != end_block + 1:
            raise UniswapV2IngestionError("receipt coverage has a block gap")

        identities = [(row.tx_hash, row.log_index) for row in rows]
        if len(identities) != len(set(identities)):
            raise UniswapV2IngestionError("replayed rows contain duplicate (tx_hash, log_index)")

        ordered = tuple(
            sorted(rows, key=lambda row: (row.block_number, row.tx_index, row.log_index))
        )
        return PairEventReplayResult(
            rows=ordered,
            raw_object_ids=frozenset(raw_ids),
            completed_ranges=tuple((r.start_block, r.end_block) for r in receipts),
            acquisition_ids=frozenset(acquisition_ids),
            log_identity_sha256s=tuple(digests),
        )
