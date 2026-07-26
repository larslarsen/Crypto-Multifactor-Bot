"""DATA-012 Uniswap V2 Factory PairCreated raw-event ingestion."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from cryptofactors.ingest.raw.models import AcquisitionMetadata
from cryptofactors.ingest.raw.writer import RawObjectWriter

ETHEREUM_CHAIN = "ethereum"
UNISWAP_V2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
PAIR_CREATED_TOPIC = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"


class UniswapV2IngestionError(RuntimeError):
    """Raised for malformed RPC responses or invalid event continuity."""


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


def _hex_int(value: str) -> int:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise UniswapV2IngestionError(f"expected hex quantity, got {value!r}")
    return int(value, 16)


def _address(topic_or_word: str) -> str:
    if not isinstance(topic_or_word, str) or not topic_or_word.startswith("0x"):
        raise UniswapV2IngestionError("expected ABI hex word")
    payload = topic_or_word[2:]
    if len(payload) != 64:
        raise UniswapV2IngestionError("expected 32-byte ABI word")
    return "0x" + payload[-40:]


def decode_pair_created(
    logs_response: dict[str, Any],
    block_headers: dict[int, tuple[dict[str, Any], str]],
    *,
    factory: str,
    log_raw_object_id: str,
    availability_time: datetime,
) -> list[PairCreatedRow]:
    """Pure deterministic decoder for replaying preserved RPC response bytes."""
    logs = logs_response.get("result")
    if not isinstance(logs, list):
        raise UniswapV2IngestionError("eth_getLogs result must be a list")
    seen: set[tuple[str, int]] = set()
    rows: list[PairCreatedRow] = []
    for log in logs:
        if not isinstance(log, dict):
            raise UniswapV2IngestionError("log entry must be an object")
        topics = log.get("topics")
        if not isinstance(topics, list) or len(topics) < 3 or topics[0].lower() != PAIR_CREATED_TOPIC:
            raise UniswapV2IngestionError("invalid PairCreated topics")
        block_number = _hex_int(log["blockNumber"])
        header, header_raw_object_id = block_headers[block_number]
        if str(log["blockHash"]).lower() != str(header["hash"]).lower():
            raise UniswapV2IngestionError("log block hash does not match block header")
        identity = (str(log["transactionHash"]), _hex_int(log["logIndex"]))
        if identity in seen:
            raise UniswapV2IngestionError("duplicate (tx_hash, log_index)")
        seen.add(identity)
        timestamp = _hex_int(header["timestamp"])
        rows.append(PairCreatedRow(
            chain=ETHEREUM_CHAIN, factory=factory, pair=_address(str(log["data"])[:66]),
            token0=_address(str(topics[1])), token1=_address(str(topics[2])),
            block_number=block_number, block_hash=str(log["blockHash"]), block_timestamp=timestamp,
            tx_hash=identity[0], tx_index=_hex_int(log["transactionIndex"]), log_index=identity[1],
            event_time=datetime.fromtimestamp(timestamp, UTC), availability_time=availability_time,
            raw_object_id=log_raw_object_id, block_raw_object_id=header_raw_object_id,
        ))
    return sorted(rows, key=lambda row: (row.block_number, row.tx_index, row.log_index))


class UniswapV2PairCreatedIngestor:
    """Resumable, gap-checked PairCreated JSON-RPC acquisition only."""

    def __init__(
        self,
        *,
        rpc_url: str,
        raw_writer: RawObjectWriter,
        client: httpx.Client | None = None,
        factory: str = UNISWAP_V2_FACTORY,
    ) -> None:
        if not rpc_url:
            raise ValueError("rpc_url is required")
        self._rpc_url = rpc_url
        self._raw_writer = raw_writer
        self._client = client or httpx.Client(timeout=30.0)
        self._owns_client = client is None
        self._factory = factory

    def _rpc(self, method: str, params: list[Any], *, event_start: int, event_end: int) -> tuple[dict[str, Any], str, datetime]:
        request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        response = self._client.post(self._rpc_url, json=request)
        body = response.content
        fetched_at = datetime.now(UTC)
        raw = self._raw_writer.write_stream(
            [body],
            AcquisitionMetadata(
                source_id="ethereum_json_rpc_uniswap_v2",
                request=request,
                response_metadata={"status_code": response.status_code, "method": method},
                original_name=f"{method}_{event_start}_{event_end}.json",
                acquired_at=fetched_at,
            ),
        )
        if response.is_error:
            raise UniswapV2IngestionError(f"JSON-RPC HTTP {response.status_code}")
        decoded = json.loads(body)
        if not isinstance(decoded, dict) or decoded.get("error") is not None:
            raise UniswapV2IngestionError(f"JSON-RPC {method} failed: {decoded!r}")
        return decoded, raw.raw_object_id, fetched_at

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def fetch(
        self,
        *,
        start_block: int,
        end_block: int,
        chunk_size: int,
        receipt_db_path: str | None = None,
    ) -> list[PairCreatedRow]:
        if start_block < 0 or end_block < start_block or chunk_size <= 0:
            raise ValueError("invalid block range or chunk_size")
        rows: list[PairCreatedRow] = []
        seen: set[tuple[str, int]] = set()
        receipts = sqlite3.connect(receipt_db_path) if receipt_db_path else None
        if receipts is not None:
            receipts.execute("PRAGMA foreign_keys = ON")
        for chunk_start in range(start_block, end_block + 1, chunk_size):
            chunk_end = min(chunk_start + chunk_size - 1, end_block)
            if receipts is not None:
                prior = receipts.execute(
                    "SELECT end_block_hash FROM uniswap_v2_pair_created_chunk_receipt WHERE start_block = ? AND end_block = ?",
                    (chunk_start, chunk_end),
                ).fetchone()
                if prior is not None:
                    header_response, _, _ = self._rpc(
                        "eth_getBlockByNumber",
                        [hex(chunk_end), False],
                        event_start=chunk_end,
                        event_end=chunk_end,
                    )
                    header = header_response.get("result")
                    if not isinstance(header, dict) or str(header.get("hash", "")).lower() != str(prior[0]).lower():
                        raise UniswapV2IngestionError("completed chunk receipt failed end-block validation")
                    continue
            logs_response, raw_object_id, availability_time = self._rpc(
                "eth_getLogs",
                [{"address": self._factory, "fromBlock": hex(chunk_start), "toBlock": hex(chunk_end), "topics": [PAIR_CREATED_TOPIC]}],
                event_start=chunk_start,
                event_end=chunk_end,
            )
            logs = logs_response.get("result")
            if not isinstance(logs, list):
                raise UniswapV2IngestionError("eth_getLogs result must be a list")
            blocks: dict[int, tuple[dict[str, Any], str, datetime]] = {}
            for log in logs:
                if not isinstance(log, dict):
                    raise UniswapV2IngestionError("log entry must be an object")
                block_number = _hex_int(log["blockNumber"])
                if block_number < chunk_start or block_number > chunk_end:
                    raise UniswapV2IngestionError("RPC returned log outside requested chunk")
                if block_number not in blocks:
                    block, block_raw_id, block_availability_time = self._rpc(
                        "eth_getBlockByNumber", [hex(block_number), False], event_start=block_number, event_end=block_number
                    )
                    result = block.get("result")
                    if not isinstance(result, dict):
                        raise UniswapV2IngestionError("missing block result")
                    blocks[block_number] = (result, block_raw_id, block_availability_time)
                topics = log.get("topics")
                if not isinstance(topics, list) or len(topics) < 3 or topics[0].lower() != PAIR_CREATED_TOPIC:
                    raise UniswapV2IngestionError("invalid PairCreated topics")
                identity = (str(log["transactionHash"]), _hex_int(log["logIndex"]))
                if identity in seen:
                    raise UniswapV2IngestionError("duplicate (tx_hash, log_index)")
                seen.add(identity)
                block, block_raw_object_id, block_availability_time = blocks[block_number]
                if str(log["blockHash"]).lower() != str(block["hash"]).lower():
                    raise UniswapV2IngestionError("log block hash does not match block header")
                rows.append(PairCreatedRow(
                    chain=ETHEREUM_CHAIN,
                    factory=self._factory,
                    pair=_address(str(log["data"])[:66]),
                    token0=_address(str(topics[1])), token1=_address(str(topics[2])),
                    block_number=block_number, block_hash=str(log["blockHash"]),
                    block_timestamp=_hex_int(block["timestamp"]), tx_hash=identity[0],
                    tx_index=_hex_int(log["transactionIndex"]), log_index=identity[1],
                    event_time=datetime.fromtimestamp(_hex_int(block["timestamp"]), UTC),
                    availability_time=max(availability_time, block_availability_time), raw_object_id=raw_object_id,
                    block_raw_object_id=block_raw_object_id,
                ))
            if receipts is not None:
                end_header, _, _ = self._rpc(
                    "eth_getBlockByNumber", [hex(chunk_end), False], event_start=chunk_end, event_end=chunk_end
                )
                header = end_header.get("result")
                if not isinstance(header, dict):
                    raise UniswapV2IngestionError("missing end-block header")
                receipts.execute(
                    "INSERT INTO uniswap_v2_pair_created_chunk_receipt VALUES (?, ?, ?, ?, ?)",
                    (chunk_start, chunk_end, str(header["hash"]), raw_object_id, availability_time.isoformat()),
                )
                receipts.commit()
        if receipts is not None:
            receipts.close()
        return sorted(rows, key=lambda row: (row.block_number, row.tx_index, row.log_index))
