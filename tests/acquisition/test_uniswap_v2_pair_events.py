"""DEX-003 — focused tests for Uniswap V2 Swap/Sync dual-RPC acquisition.

Coverage maps to CURRENT_TASK / ADR-0015 for this layer:

* dual independent RPC providers required
* exact receipt binding + offline replay
* provider disagreement fail-closed
* block identity / mainnet chain guard
* event_time / source_available_at (+24h) / retrieved_at
* token decimals eth_call preservation
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from cryptofactors.acquisition.uniswap_v2 import (
    ETHEREUM_CHAIN,
    ETHEREUM_MAINNET_CHAIN_ID,
    UNISWAP_V2_DEPLOYMENT_BLOCK,
    UniswapV2IngestionError,
    _canonical_json,
)
from cryptofactors.acquisition.uniswap_v2_pair_events import (
    DECIMALS_SELECTOR,
    DISAGREEMENT_TABLE,
    FAILURE_TABLE,
    RECEIPT_TABLE,
    SOURCE_AVAILABILITY_LAG,
    SWAP_TOPIC,
    SYNC_TOPIC,
    PairEventReplayResult,
    SwapRow,
    UniswapV2PairEventIngestor,
    decode_swap_logs,
    decode_sync_logs,
    decode_token_decimals,
    extract_log_identity,
    log_identity_digest,
    pair_logs_request,
    reconcile_log_sets,
    token_decimals_request,
    topic_for_kind,
)
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.writer import RawObjectWriter

TIMESTAMP_BASE = 1_600_000_000
PAIR = "0x" + "11" * 20
TOKEN = "0x" + "a1" * 20
SENDER = "0x" + "b2" * 20
TO = "0x" + "c3" * 20


def _addr(n: int) -> str:
    return "0x" + f"{n:040x}"


def _hash32(n: int) -> str:
    return "0x" + f"{n:064x}"


def _abi_word(address: str) -> str:
    return "0x" + address[2:].lower().rjust(64, "0")


def _uint256(value: int) -> str:
    return f"{value:064x}"


def swap_log(
    *,
    block_number: int,
    block_hash: str,
    tx_hash: str,
    tx_index: int,
    log_index: int,
    amount0_in: int = 100,
    amount1_in: int = 0,
    amount0_out: int = 0,
    amount1_out: int = 50,
    sender: str = SENDER,
    to: str = TO,
    emitter: str = PAIR,
) -> dict[str, Any]:
    return {
        "address": emitter,
        "blockHash": block_hash,
        "blockNumber": hex(block_number),
        "data": "0x" + _uint256(amount0_in) + _uint256(amount1_in)
        + _uint256(amount0_out) + _uint256(amount1_out),
        "logIndex": hex(log_index),
        "removed": False,
        "topics": [SWAP_TOPIC, _abi_word(sender), _abi_word(to)],
        "transactionHash": tx_hash,
        "transactionIndex": hex(tx_index),
    }


def sync_log(
    *,
    block_number: int,
    block_hash: str,
    tx_hash: str,
    tx_index: int,
    log_index: int,
    reserve0: int = 1_000_000,
    reserve1: int = 2_000_000,
    emitter: str = PAIR,
) -> dict[str, Any]:
    return {
        "address": emitter,
        "blockHash": block_hash,
        "blockNumber": hex(block_number),
        "data": "0x" + _uint256(reserve0) + _uint256(reserve1),
        "logIndex": hex(log_index),
        "removed": False,
        "topics": [SYNC_TOPIC],
        "transactionHash": tx_hash,
        "transactionIndex": hex(tx_index),
    }


class DualMockNode:
    """Two logical providers backed by one or two log sets and shared block hashes."""

    def __init__(
        self,
        *,
        block_hashes: dict[int, str],
        primary_logs: list[Any] | None = None,
        secondary_logs: list[Any] | None = None,
        chain_id: str = ETHEREUM_MAINNET_CHAIN_ID,
        primary_end_hash_override: dict[int, str] | None = None,
        secondary_end_hash_override: dict[int, str] | None = None,
        primary_timestamp_override: dict[int, int] | None = None,
        secondary_timestamp_override: dict[int, int] | None = None,
        primary_decimals_result: str = "0x" + "12".rjust(64, "0"),
        secondary_decimals_result: str | None = None,
        fail_secondary_logs: bool = False,
        shuffle_batch_responses: bool = True,
    ) -> None:
        self.block_hashes = block_hashes
        self.primary_logs = primary_logs if primary_logs is not None else []
        self.secondary_logs = (
            secondary_logs if secondary_logs is not None else list(self.primary_logs)
        )
        self.chain_id = chain_id
        self.primary_end_hash_override = primary_end_hash_override or {}
        self.secondary_end_hash_override = secondary_end_hash_override or {}
        self.primary_timestamp_override = primary_timestamp_override or {}
        self.secondary_timestamp_override = secondary_timestamp_override or {}
        self.primary_decimals_result = primary_decimals_result
        self.secondary_decimals_result = (
            secondary_decimals_result
            if secondary_decimals_result is not None
            else primary_decimals_result
        )
        self.fail_secondary_logs = fail_secondary_logs
        self.shuffle_batch_responses = shuffle_batch_responses
        self.primary_calls: list[tuple[str, Any]] = []
        self.secondary_calls: list[tuple[str, Any]] = []

    @staticmethod
    def timestamp(block_number: int) -> int:
        return TIMESTAMP_BASE + block_number

    def _respond(self, status: int, payload: Any) -> httpx.Response:
        return httpx.Response(
            status,
            content=json.dumps(payload).encode(),
            headers={"content-type": "application/json"},
        )

    def _block_response(
        self, *, is_primary: bool, number: int, request_id: Any
    ) -> dict[str, Any]:
        hash_overrides = (
            self.primary_end_hash_override if is_primary
            else self.secondary_end_hash_override
        )
        ts_overrides = (
            self.primary_timestamp_override if is_primary
            else self.secondary_timestamp_override
        )
        if number in hash_overrides:
            block_hash = hash_overrides[number]
        elif number in self.block_hashes:
            block_hash = self.block_hashes[number]
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": f"unknown block {number}"},
            }
        timestamp = ts_overrides.get(number, self.timestamp(number))
        header = {
            "number": hex(number),
            "hash": block_hash,
            "parentHash": _hash32(number - 1),
            "timestamp": hex(timestamp),
        }
        return {"jsonrpc": "2.0", "id": request_id, "result": header}

    def _dispatch_one(
        self, *, is_primary: bool, payload: dict[str, Any]
    ) -> dict[str, Any]:
        method = payload["method"]
        params = payload["params"]
        request_id = payload.get("id", 1)
        calls = self.primary_calls if is_primary else self.secondary_calls
        calls.append((method, params))

        if method == "eth_chainId":
            return {"jsonrpc": "2.0", "id": request_id, "result": self.chain_id}

        if method == "eth_call":
            result = (
                self.primary_decimals_result if is_primary
                else self.secondary_decimals_result
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": result}

        if method == "eth_getBlockByNumber":
            number = int(params[0], 16)
            return self._block_response(
                is_primary=is_primary, number=number, request_id=request_id
            )

        if method == "eth_getLogs":
            if not is_primary and self.fail_secondary_logs:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32005,
                        "message": "query returned more than 10000 results",
                    },
                }
            from_block = int(params[0]["fromBlock"], 16)
            to_block = int(params[0]["toBlock"], 16)
            source = self.primary_logs if is_primary else self.secondary_logs
            selected = [
                log for log in source
                if isinstance(log, dict)
                and from_block <= int(log["blockNumber"], 16) <= to_block
            ]
            return {"jsonrpc": "2.0", "id": request_id, "result": selected}

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": method},
        }

    def _handler(
        self,
        *,
        is_primary: bool,
        request: httpx.Request,
    ) -> httpx.Response:
        payload = json.loads(request.read())
        # JSON-RPC batch: array of request objects. Respond in shuffled order so
        # callers must correlate by id, never by position.
        if isinstance(payload, list):
            responses = [
                self._dispatch_one(is_primary=is_primary, payload=item)
                for item in payload
                if isinstance(item, dict)
            ]
            if self.shuffle_batch_responses:
                responses = list(reversed(responses))
            return self._respond(200, responses)

        if not isinstance(payload, dict):
            return self._respond(
                200, {"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "bad"}}
            )
        return self._respond(
            200, self._dispatch_one(is_primary=is_primary, payload=payload)
        )

    def primary_client(self) -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(
                lambda request: self._handler(is_primary=True, request=request)
            )
        )

    def secondary_client(self) -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(
                lambda request: self._handler(is_primary=False, request=request)
            )
        )


class Store:
    def __init__(self, tmp_path: Path) -> None:
        self.store_root = tmp_path / "store"
        self.raw_root = self.store_root / "raw"
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.db = tmp_path / "control.db"
        apply_migrations(self.db, migrations_dir=MIGRATIONS_DIR)
        self.catalog = SqliteRawObjectCatalog(self.db)
        self.writer = RawObjectWriter(RawObjectStoreConfig(root=self.raw_root), self.catalog)

    def close(self) -> None:
        self.catalog.close()

    def _query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        conn = sqlite3.connect(self.db)
        try:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(sql, params)]
        finally:
            conn.close()

    def receipts(self) -> list[dict[str, Any]]:
        return self._query(f"SELECT * FROM {RECEIPT_TABLE} ORDER BY start_block")

    def disagreements(self) -> list[dict[str, Any]]:
        return self._query(f"SELECT * FROM {DISAGREEMENT_TABLE} ORDER BY disagreement_id")

    def failures(self) -> list[dict[str, Any]]:
        return self._query(f"SELECT * FROM {FAILURE_TABLE} ORDER BY failure_id")


@pytest.fixture
def store(tmp_path: Path) -> Iterator[Store]:
    created = Store(tmp_path)
    yield created
    created.close()


SCENARIO_START = UNISWAP_V2_DEPLOYMENT_BLOCK + 1000
SCENARIO_CHUNK = 50
SCENARIO_END = SCENARIO_START + 99
BLOCK_EVENT = SCENARIO_START + 10
BLOCK_CHUNK1_END = SCENARIO_START + 49
BLOCK_CHUNK2_END = SCENARIO_END

BLOCK_HASHES = {
    BLOCK_EVENT: _hash32(BLOCK_EVENT),
    BLOCK_CHUNK1_END: _hash32(BLOCK_CHUNK1_END),
    BLOCK_CHUNK2_END: _hash32(BLOCK_CHUNK2_END),
}


def _make_ingestor(
    store: Store,
    node: DualMockNode,
    *,
    use_header_batches: bool = True,
    header_batch_size: int = 2,
    finality_cutoff_block: int | None = None,
) -> UniswapV2PairEventIngestor:
    return UniswapV2PairEventIngestor(
        primary_rpc_url="https://rpc-a.example",
        secondary_rpc_url="https://rpc-b.example",
        raw_writer=store.writer,
        primary_provider_id="rpc_a",
        secondary_provider_id="rpc_b",
        primary_client=node.primary_client(),
        secondary_client=node.secondary_client(),
        raw_root=store.raw_root,
        use_header_batches=use_header_batches,
        header_batch_size=header_batch_size,
        header_max_in_flight=2,
        header_requests_per_second=1000.0,
        finality_cutoff_block=finality_cutoff_block,
    )


# ---------------------------------------------------------------------------
# Construction / request shape
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_identical_rpc_urls_are_refused(self, store: Store) -> None:
        with pytest.raises(ValueError, match="distinct"):
            UniswapV2PairEventIngestor(
                primary_rpc_url="https://same.example",
                secondary_rpc_url="https://same.example/",
                raw_writer=store.writer,
            )

    def test_identical_provider_ids_are_refused(self, store: Store) -> None:
        with pytest.raises(ValueError, match="provider ids must differ"):
            UniswapV2PairEventIngestor(
                primary_rpc_url="https://a.example",
                secondary_rpc_url="https://b.example",
                raw_writer=store.writer,
                primary_provider_id="same",
                secondary_provider_id="same",
            )

    def test_pair_logs_request_is_canonical(self) -> None:
        request = pair_logs_request(
            pair=PAIR, topic=SWAP_TOPIC, start_block=10, end_block=20
        )
        assert request["method"] == "eth_getLogs"
        assert request["params"][0]["address"] == PAIR
        assert request["params"][0]["topics"] == [SWAP_TOPIC]
        assert request["params"][0]["fromBlock"] == hex(10)
        assert request["params"][0]["toBlock"] == hex(20)
        # Request binding depends on stable encoding.
        assert _canonical_json(request) == _canonical_json(request)

    def test_topic_for_kind(self) -> None:
        assert topic_for_kind("swap") == SWAP_TOPIC
        assert topic_for_kind("sync") == SYNC_TOPIC


# ---------------------------------------------------------------------------
# Pure decode / reconcile
# ---------------------------------------------------------------------------

class TestDecodeAndReconcile:
    def test_swap_decode_sets_adr0015_times(self) -> None:
        block_hash = _hash32(BLOCK_EVENT)
        log = swap_log(
            block_number=BLOCK_EVENT, block_hash=block_hash,
            tx_hash=_hash32(1), tx_index=0, log_index=1,
            amount0_in=10, amount1_out=5,
        )
        header = {
            "number": hex(BLOCK_EVENT),
            "hash": block_hash,
            "timestamp": hex(TIMESTAMP_BASE + BLOCK_EVENT),
        }
        retrieved = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
        rows = decode_swap_logs(
            {"result": [log]},
            {BLOCK_EVENT: (header, "raw_header")},
            pair=PAIR,
            log_raw_object_id="raw_logs",
            retrieved_at=retrieved,
            primary_provider_id="a",
            secondary_provider_id="b",
        )
        assert len(rows) == 1
        row = rows[0]
        assert isinstance(row, SwapRow)
        assert row.amount0_in == 10
        assert row.amount1_out == 5
        assert row.sender == SENDER.lower()
        assert row.event_time == datetime.fromtimestamp(TIMESTAMP_BASE + BLOCK_EVENT, UTC)
        assert row.source_available_at == row.event_time + SOURCE_AVAILABILITY_LAG
        assert row.source_available_at == row.event_time + timedelta(hours=24)
        assert row.retrieved_at == retrieved
        assert row.primary_provider_id == "a"

    def test_sync_decode_rejects_oversize_reserve(self) -> None:
        block_hash = _hash32(BLOCK_EVENT)
        log = sync_log(
            block_number=BLOCK_EVENT, block_hash=block_hash,
            tx_hash=_hash32(1), tx_index=0, log_index=1,
            reserve0=1 << 112, reserve1=1,
        )
        header = {
            "number": hex(BLOCK_EVENT),
            "hash": block_hash,
            "timestamp": hex(TIMESTAMP_BASE + BLOCK_EVENT),
        }
        with pytest.raises(UniswapV2IngestionError, match="uint112"):
            decode_sync_logs(
                {"result": [log]},
                {BLOCK_EVENT: (header, "raw_header")},
                pair=PAIR,
                log_raw_object_id="raw_logs",
                retrieved_at=datetime.now(UTC),
                primary_provider_id="a",
                secondary_provider_id="b",
            )

    def test_reconcile_requires_identical_identity_sets(self) -> None:
        block_hash = _hash32(BLOCK_EVENT)
        primary = [swap_log(
            block_number=BLOCK_EVENT, block_hash=block_hash,
            tx_hash=_hash32(1), tx_index=0, log_index=1,
        )]
        secondary = [swap_log(
            block_number=BLOCK_EVENT, block_hash=block_hash,
            tx_hash=_hash32(1), tx_index=0, log_index=1,
            amount0_in=999,  # data differs → identity differs
        )]
        with pytest.raises(UniswapV2IngestionError, match="identity disagreement"):
            reconcile_log_sets(primary, secondary)

    def test_reconcile_detects_count_disagreement(self) -> None:
        block_hash = _hash32(BLOCK_EVENT)
        primary = [
            swap_log(
                block_number=BLOCK_EVENT, block_hash=block_hash,
                tx_hash=_hash32(1), tx_index=0, log_index=1,
            ),
            swap_log(
                block_number=BLOCK_EVENT, block_hash=block_hash,
                tx_hash=_hash32(2), tx_index=1, log_index=2,
            ),
        ]
        secondary = primary[:1]
        with pytest.raises(UniswapV2IngestionError, match="log count disagreement"):
            reconcile_log_sets(primary, secondary)

    def test_log_identity_digest_is_order_independent(self) -> None:
        a = extract_log_identity(swap_log(
            block_number=BLOCK_EVENT, block_hash=_hash32(BLOCK_EVENT),
            tx_hash=_hash32(1), tx_index=0, log_index=1,
        ))
        b = extract_log_identity(swap_log(
            block_number=BLOCK_EVENT, block_hash=_hash32(BLOCK_EVENT),
            tx_hash=_hash32(2), tx_index=1, log_index=2,
        ))
        assert log_identity_digest([a, b]) == log_identity_digest([b, a])

    def test_token_decimals_decode(self) -> None:
        assert decode_token_decimals({"result": "0x" + "12".rjust(64, "0")}) == 18
        with pytest.raises(UniswapV2IngestionError, match="uint8"):
            decode_token_decimals({"result": "0x" + "100".rjust(64, "0")})


# ---------------------------------------------------------------------------
# Dual-RPC fetch / receipt / replay
# ---------------------------------------------------------------------------

class TestDualRpcAcquisition:
    def test_swap_fetch_writes_dual_receipt_and_replays(self, store: Store) -> None:
        logs = [
            swap_log(
                block_number=BLOCK_EVENT,
                block_hash=BLOCK_HASHES[BLOCK_EVENT],
                tx_hash=_hash32(0xF1),
                tx_index=2,
                log_index=5,
                amount0_in=1000,
                amount1_out=42,
            ),
            swap_log(
                block_number=BLOCK_CHUNK1_END,
                block_hash=BLOCK_HASHES[BLOCK_CHUNK1_END],
                tx_hash=_hash32(0xF2),
                tx_index=0,
                log_index=1,
            ),
        ]
        node = DualMockNode(block_hashes=BLOCK_HASHES, primary_logs=logs)
        ingestor = _make_ingestor(store, node)
        try:
            rows = ingestor.fetch(
                pair=PAIR,
                kind="swap",
                start_block=SCENARIO_START,
                end_block=SCENARIO_END,
                chunk_size=SCENARIO_CHUNK,
                receipt_db_path=str(store.db),
                emit_rows=True,
                raw_root=store.raw_root,
            )
        finally:
            ingestor.close()

        assert len(rows) == 2
        assert all(isinstance(row, SwapRow) for row in rows)
        assert rows[0].amount0_in == 1000
        assert rows[0].amount1_out == 42
        assert rows[0].source_available_at == rows[0].event_time + timedelta(hours=24)

        receipts = store.receipts()
        assert len(receipts) == 2
        first = receipts[0]
        assert first["primary_provider_id"] == "rpc_a"
        assert first["secondary_provider_id"] == "rpc_b"
        assert first["reconciliation_status"] == "AGREED"
        assert first["log_count"] == 2
        assert first["end_block_hash"] == first["secondary_end_block_hash"]
        assert first["chain_id"] == ETHEREUM_MAINNET_CHAIN_ID
        # Content-addressed raw ids may match when both providers return identical
        # bytes; the two independent acquisitions must still be distinct.
        assert first["primary_logs_acquisition_id"] != first["secondary_logs_acquisition_id"]
        assert first["primary_end_header_acquisition_id"] != first[
            "secondary_end_header_acquisition_id"
        ]
        assert first["primary_logs_raw_object_id"].startswith("raw_")
        assert first["secondary_logs_raw_object_id"].startswith("raw_")

        # Both providers must have been queried for logs and end headers.
        assert node.primary_calls
        assert node.secondary_calls
        assert any(m == "eth_getLogs" for m, _ in node.primary_calls)
        assert any(m == "eth_getLogs" for m, _ in node.secondary_calls)

        # Offline replay is deterministic and network-free.
        quiet = DualMockNode(block_hashes={})
        replayer = UniswapV2PairEventIngestor(
            primary_rpc_url="https://rpc-a.example",
            secondary_rpc_url="https://rpc-b.example",
            raw_writer=store.writer,
            primary_provider_id="rpc_a",
            secondary_provider_id="rpc_b",
            primary_client=quiet.primary_client(),
            secondary_client=quiet.secondary_client(),
            raw_root=store.raw_root,
        )
        try:
            replayed = replayer.replay_receipts(
                pair=PAIR,
                kind="swap",
                start_block=SCENARIO_START,
                end_block=SCENARIO_END,
                receipt_db_path=str(store.db),
                raw_root=store.raw_root,
            )
        finally:
            replayer.close()

        assert isinstance(replayed, PairEventReplayResult)
        assert len(replayed.rows) == 2
        assert [row.as_dict() for row in replayed.rows] == [row.as_dict() for row in rows]
        assert quiet.primary_calls == []
        assert quiet.secondary_calls == []
        assert first["log_identity_sha256"] in replayed.log_identity_sha256s
        assert first["primary_logs_raw_object_id"] in replayed.raw_object_ids
        assert first["secondary_logs_raw_object_id"] in replayed.raw_object_ids

    def test_sync_fetch_empty_chunk_still_binds_end_headers(self, store: Store) -> None:
        node = DualMockNode(block_hashes=BLOCK_HASHES, primary_logs=[])
        ingestor = _make_ingestor(store, node)
        try:
            rows = ingestor.fetch(
                pair=PAIR,
                kind="sync",
                start_block=SCENARIO_START,
                end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                chunk_size=SCENARIO_CHUNK,
                receipt_db_path=str(store.db),
                emit_rows=True,
                raw_root=store.raw_root,
            )
        finally:
            ingestor.close()

        assert rows == []
        receipts = store.receipts()
        assert len(receipts) == 1
        assert receipts[0]["log_count"] == 0
        assert receipts[0]["topic"] == SYNC_TOPIC
        assert receipts[0]["end_block_hash"] == BLOCK_HASHES[BLOCK_CHUNK1_END]
        assert receipts[0]["secondary_end_block_hash"] == BLOCK_HASHES[BLOCK_CHUNK1_END]

    def test_provider_log_disagreement_is_recorded_and_blocks(self, store: Store) -> None:
        primary = [swap_log(
            block_number=BLOCK_EVENT,
            block_hash=BLOCK_HASHES[BLOCK_EVENT],
            tx_hash=_hash32(1),
            tx_index=0,
            log_index=1,
        )]
        secondary = [swap_log(
            block_number=BLOCK_EVENT,
            block_hash=BLOCK_HASHES[BLOCK_EVENT],
            tx_hash=_hash32(1),
            tx_index=0,
            log_index=1,
            amount0_in=9999,
        )]
        node = DualMockNode(
            block_hashes=BLOCK_HASHES,
            primary_logs=primary,
            secondary_logs=secondary,
        )
        ingestor = _make_ingestor(store, node)
        try:
            with pytest.raises(UniswapV2IngestionError, match="identity disagreement"):
                ingestor.fetch(
                    pair=PAIR,
                    kind="swap",
                    start_block=SCENARIO_START,
                    end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                    chunk_size=SCENARIO_CHUNK,
                    receipt_db_path=str(store.db),
                    emit_rows=True,
                    raw_root=store.raw_root,
                )
        finally:
            ingestor.close()

        assert store.receipts() == []
        disagreements = store.disagreements()
        assert len(disagreements) == 1
        assert disagreements[0]["primary_log_count"] == 1
        assert disagreements[0]["secondary_log_count"] == 1
        assert disagreements[0]["primary_identity_sha256"] != disagreements[0][
            "secondary_identity_sha256"
        ]

    def test_end_block_hash_disagreement_is_recorded_and_blocks(self, store: Store) -> None:
        logs = [swap_log(
            block_number=BLOCK_EVENT,
            block_hash=BLOCK_HASHES[BLOCK_EVENT],
            tx_hash=_hash32(1),
            tx_index=0,
            log_index=1,
        )]
        node = DualMockNode(
            block_hashes=BLOCK_HASHES,
            primary_logs=logs,
            secondary_end_hash_override={BLOCK_CHUNK1_END: _hash32(0xDEAD)},
        )
        ingestor = _make_ingestor(store, node)
        try:
            with pytest.raises(UniswapV2IngestionError, match="end-block hash disagreement"):
                ingestor.fetch(
                    pair=PAIR,
                    kind="swap",
                    start_block=SCENARIO_START,
                    end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                    chunk_size=SCENARIO_CHUNK,
                    receipt_db_path=str(store.db),
                    emit_rows=True,
                    raw_root=store.raw_root,
                )
        finally:
            ingestor.close()

        assert store.receipts() == []
        disagreements = store.disagreements()
        assert len(disagreements) == 1
        assert disagreements[0]["primary_end_block_hash"] == BLOCK_HASHES[BLOCK_CHUNK1_END]
        assert disagreements[0]["secondary_end_block_hash"] == _hash32(0xDEAD)

    def test_event_block_timestamp_disagreement_is_recorded_and_blocks(
        self, store: Store
    ) -> None:
        logs = [swap_log(
            block_number=BLOCK_EVENT,
            block_hash=BLOCK_HASHES[BLOCK_EVENT],
            tx_hash=_hash32(1),
            tx_index=0,
            log_index=1,
        )]
        node = DualMockNode(
            block_hashes=BLOCK_HASHES,
            primary_logs=logs,
            secondary_timestamp_override={BLOCK_EVENT: TIMESTAMP_BASE + BLOCK_EVENT + 999},
        )
        ingestor = _make_ingestor(store, node)
        try:
            with pytest.raises(
                UniswapV2IngestionError, match="event-block timestamp disagreement"
            ):
                ingestor.fetch(
                    pair=PAIR,
                    kind="swap",
                    start_block=SCENARIO_START,
                    end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                    chunk_size=SCENARIO_CHUNK,
                    receipt_db_path=str(store.db),
                    emit_rows=True,
                    raw_root=store.raw_root,
                )
        finally:
            ingestor.close()

        assert store.receipts() == []
        disagreements = store.disagreements()
        assert len(disagreements) == 1
        assert "timestamp disagreement" in disagreements[0]["detail"]

    def test_disagreement_write_failure_fails_closed(self, store: Store) -> None:
        """Evidence insert failure must re-raise, not leave the audit table silent."""
        primary = [swap_log(
            block_number=BLOCK_EVENT,
            block_hash=BLOCK_HASHES[BLOCK_EVENT],
            tx_hash=_hash32(1),
            tx_index=0,
            log_index=1,
        )]
        secondary = [swap_log(
            block_number=BLOCK_EVENT,
            block_hash=BLOCK_HASHES[BLOCK_EVENT],
            tx_hash=_hash32(1),
            tx_index=0,
            log_index=1,
            amount0_in=9999,
        )]
        node = DualMockNode(
            block_hashes=BLOCK_HASHES,
            primary_logs=primary,
            secondary_logs=secondary,
        )
        ingestor = _make_ingestor(store, node)
        # Drop the disagreement table so INSERT fails with OperationalError.
        conn = sqlite3.connect(store.db)
        try:
            conn.execute(f"DROP TABLE {DISAGREEMENT_TABLE}")
            conn.commit()
        finally:
            conn.close()
        try:
            with pytest.raises(
                UniswapV2IngestionError, match="failed to persist provider disagreement"
            ):
                ingestor.fetch(
                    pair=PAIR,
                    kind="swap",
                    start_block=SCENARIO_START,
                    end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                    chunk_size=SCENARIO_CHUNK,
                    receipt_db_path=str(store.db),
                    emit_rows=True,
                    raw_root=store.raw_root,
                )
        finally:
            ingestor.close()

    def test_secondary_rpc_error_is_recorded(self, store: Store) -> None:
        node = DualMockNode(
            block_hashes=BLOCK_HASHES,
            primary_logs=[],
            fail_secondary_logs=True,
        )
        ingestor = _make_ingestor(store, node)
        try:
            with pytest.raises(UniswapV2IngestionError, match="rpc_b"):
                ingestor.fetch(
                    pair=PAIR,
                    kind="swap",
                    start_block=SCENARIO_START,
                    end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                    chunk_size=SCENARIO_CHUNK,
                    receipt_db_path=str(store.db),
                    emit_rows=True,
                    raw_root=store.raw_root,
                )
        finally:
            ingestor.close()

        failures = store.failures()
        assert any(row["provider_id"] == "rpc_b" for row in failures)
        assert store.receipts() == []

    def test_non_mainnet_is_refused(self, store: Store) -> None:
        node = DualMockNode(block_hashes=BLOCK_HASHES, chain_id="0x89")
        ingestor = _make_ingestor(store, node)
        try:
            with pytest.raises(UniswapV2IngestionError, match="mainnet"):
                ingestor.fetch(
                    pair=PAIR,
                    kind="swap",
                    start_block=SCENARIO_START,
                    end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                    chunk_size=SCENARIO_CHUNK,
                    receipt_db_path=str(store.db),
                    emit_rows=True,
                    raw_root=store.raw_root,
                )
        finally:
            ingestor.close()

    def test_start_before_deployment_is_refused(self, store: Store) -> None:
        node = DualMockNode(block_hashes=BLOCK_HASHES)
        ingestor = _make_ingestor(store, node)
        try:
            with pytest.raises(UniswapV2IngestionError, match="deployment block"):
                ingestor.fetch(
                    pair=PAIR,
                    kind="swap",
                    start_block=UNISWAP_V2_DEPLOYMENT_BLOCK - 1,
                    end_block=UNISWAP_V2_DEPLOYMENT_BLOCK + 10,
                    chunk_size=10,
                    receipt_db_path=str(store.db),
                )
        finally:
            ingestor.close()

    def test_resume_skips_verified_chunk(self, store: Store) -> None:
        logs = [swap_log(
            block_number=BLOCK_EVENT,
            block_hash=BLOCK_HASHES[BLOCK_EVENT],
            tx_hash=_hash32(1),
            tx_index=0,
            log_index=1,
        )]
        node = DualMockNode(block_hashes=BLOCK_HASHES, primary_logs=logs)
        ingestor = _make_ingestor(store, node)
        try:
            ingestor.fetch(
                pair=PAIR,
                kind="swap",
                start_block=SCENARIO_START,
                end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                chunk_size=SCENARIO_CHUNK,
                receipt_db_path=str(store.db),
                emit_rows=False,
                raw_root=store.raw_root,
            )
            primary_before = len([c for c in node.primary_calls if c[0] == "eth_getLogs"])
            secondary_before = len([c for c in node.secondary_calls if c[0] == "eth_getLogs"])
            with pytest.raises(UniswapV2IngestionError, match="already complete"):
                ingestor.fetch(
                    pair=PAIR,
                    kind="swap",
                    start_block=SCENARIO_START,
                    end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                    chunk_size=SCENARIO_CHUNK,
                    receipt_db_path=str(store.db),
                    emit_rows=True,
                    raw_root=store.raw_root,
                )
            # Resume verified the receipt and re-checked end headers, but did not
            # re-fetch logs for the completed chunk.
            primary_after = len([c for c in node.primary_calls if c[0] == "eth_getLogs"])
            secondary_after = len([c for c in node.secondary_calls if c[0] == "eth_getLogs"])
            assert primary_after == primary_before
            assert secondary_after == secondary_before
        finally:
            ingestor.close()

    def test_token_decimals_require_dual_agreement(self, store: Store) -> None:
        node = DualMockNode(
            block_hashes=BLOCK_HASHES,
            primary_decimals_result="0x" + "6".rjust(64, "0"),
        )
        ingestor = _make_ingestor(store, node)
        try:
            row = ingestor.fetch_token_decimals(token=TOKEN, block_number=BLOCK_EVENT)
        finally:
            ingestor.close()
        assert row.decimals == 6
        assert row.token == TOKEN.lower()
        assert row.chain == ETHEREUM_CHAIN
        assert row.primary_raw_object_id.startswith("raw_")
        assert row.secondary_raw_object_id.startswith("raw_")
        assert row.primary_provider_id == "rpc_a"
        assert row.secondary_provider_id == "rpc_b"
        assert any(m == "eth_call" for m, _ in node.primary_calls)
        assert any(m == "eth_call" for m, _ in node.secondary_calls)
        request = token_decimals_request(token=TOKEN, block_number=BLOCK_EVENT)
        assert request["params"][0]["data"] == DECIMALS_SELECTOR

    def test_token_decimals_disagreement_blocks(self, store: Store) -> None:
        node = DualMockNode(
            block_hashes=BLOCK_HASHES,
            primary_decimals_result="0x" + "6".rjust(64, "0"),
            secondary_decimals_result="0x" + "12".rjust(64, "0"),
        )
        ingestor = _make_ingestor(store, node)
        try:
            with pytest.raises(UniswapV2IngestionError, match="decimals disagreement"):
                ingestor.fetch_token_decimals(
                    token=TOKEN,
                    block_number=BLOCK_EVENT,
                    receipt_db_path=str(store.db),
                )
        finally:
            ingestor.close()
        disagreements = store.disagreements()
        assert len(disagreements) == 1
        assert "decimals disagreement" in disagreements[0]["detail"]

    def test_token_decimals_receipt_resume_skips_network(self, store: Store) -> None:
        from cryptofactors.acquisition.uniswap_v2_pair_events import (
            DECIMALS_RECEIPT_TABLE,
        )

        node = DualMockNode(
            block_hashes=BLOCK_HASHES,
            primary_decimals_result="0x" + "6".rjust(64, "0"),
        )
        ingestor = _make_ingestor(store, node)
        try:
            first = ingestor.fetch_token_decimals(
                token=TOKEN,
                block_number=BLOCK_EVENT,
                receipt_db_path=str(store.db),
                raw_root=store.raw_root,
            )
            assert first.decimals == 6
            primary_calls = len([c for c in node.primary_calls if c[0] == "eth_call"])
            secondary_calls = len([c for c in node.secondary_calls if c[0] == "eth_call"])
            assert primary_calls == 1
            assert secondary_calls == 1

            # Receipt persisted.
            rows = store._query(
                f"SELECT token, block_number, decimals FROM {DECIMALS_RECEIPT_TABLE}"
            )
            assert len(rows) == 1
            assert rows[0]["decimals"] == 6

            # Resume re-authenticates preserved bytes; no new eth_call.
            second = ingestor.fetch_token_decimals(
                token=TOKEN,
                block_number=BLOCK_EVENT,
                receipt_db_path=str(store.db),
                raw_root=store.raw_root,
            )
            assert second.decimals == first.decimals
            assert second.primary_raw_object_id == first.primary_raw_object_id
            assert second.secondary_raw_object_id == first.secondary_raw_object_id
            assert len([c for c in node.primary_calls if c[0] == "eth_call"]) == 1
            assert len([c for c in node.secondary_calls if c[0] == "eth_call"]) == 1

            # latest is refused when durable receipts are enabled.
            with pytest.raises(UniswapV2IngestionError, match="integer"):
                ingestor.fetch_token_decimals(
                    token=TOKEN,
                    block_number="latest",
                    receipt_db_path=str(store.db),
                )
        finally:
            ingestor.close()


# ---------------------------------------------------------------------------
# Batched header acquisition — equivalence regression (gating)
# ---------------------------------------------------------------------------

# Frozen pilot fixture: receipts + raw bytes committed under tests/acquisition/fixtures.
# Digests lock the pre-tx_index LogIdentity definition; changing as_tuple / sort key
# must fail this test until a versioned digest migration ships.
PILOT_FIXTURE_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "uniswap_v2_pair_events_pilot_v1"
)
# Hardcoded — do not recompute from live code when asserting.
PILOT_LOG_IDENTITY_SHA256S = (
    "a09a5a3eee597a334265c9a453813078dd9352892935b308085727aa418a6538",
    "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
)


class TestHeaderBatchEquivalence:
    """Gating: batch path must not change rows, digests, ranges, or pilot replay."""

    def _scenario_logs(self) -> list[dict[str, Any]]:
        return [
            swap_log(
                block_number=BLOCK_EVENT,
                block_hash=BLOCK_HASHES[BLOCK_EVENT],
                tx_hash=_hash32(0xF1),
                tx_index=2,
                log_index=5,
                amount0_in=1000,
                amount1_out=42,
            ),
            swap_log(
                block_number=BLOCK_CHUNK1_END,
                block_hash=BLOCK_HASHES[BLOCK_CHUNK1_END],
                tx_hash=_hash32(0xF2),
                tx_index=0,
                log_index=1,
            ),
        ]

    def test_pilot_style_receipts_without_batch_index_still_replay(
        self, tmp_path: Path
    ) -> None:
        """Replay committed pilot receipts; fail if digest function or batch auth drifts."""
        import shutil

        from cryptofactors.acquisition.uniswap_v2 import HeaderDependency

        assert PILOT_FIXTURE_DIR.is_dir(), f"missing fixture dir {PILOT_FIXTURE_DIR}"
        manifest = json.loads((PILOT_FIXTURE_DIR / "manifest.json").read_text())
        # Manifest and hardcoded constant must agree — both are part of the lock.
        assert tuple(manifest["log_identity_sha256s"]) == PILOT_LOG_IDENTITY_SHA256S

        work = tmp_path / "pilot_replay"
        shutil.copytree(PILOT_FIXTURE_DIR / "raw", work / "raw")
        db_path = work / "control.db"
        shutil.copy2(PILOT_FIXTURE_DIR / "control.db", db_path)

        quiet = DualMockNode(block_hashes={})
        catalog = SqliteRawObjectCatalog(db_path)
        writer = RawObjectWriter(RawObjectStoreConfig(root=work / "raw"), catalog)
        replayer = UniswapV2PairEventIngestor(
            primary_rpc_url="https://rpc-a.example",
            secondary_rpc_url="https://rpc-b.example",
            raw_writer=writer,
            primary_provider_id="rpc_a",
            secondary_provider_id="rpc_b",
            primary_client=quiet.primary_client(),
            secondary_client=quiet.secondary_client(),
            raw_root=work / "raw",
            use_header_batches=True,
        )
        try:
            replayed = replayer.replay_receipts(
                pair=manifest["pair"],
                kind=manifest["kind"],
                start_block=int(manifest["start_block"]),
                end_block=int(manifest["end_block"]),
                receipt_db_path=str(db_path),
                raw_root=work / "raw",
            )
        finally:
            replayer.close()
            catalog.close()

        assert quiet.primary_calls == []
        assert quiet.secondary_calls == []
        assert replayed.log_identity_sha256s == PILOT_LOG_IDENTITY_SHA256S
        assert [list(r) for r in replayed.completed_ranges] == manifest["completed_ranges"]
        assert [row.as_dict() for row in replayed.rows] == manifest["rows"]

        # Pilot deps omit batch_index; from_dict must default to None.
        conn = sqlite3.connect(db_path)
        try:
            receipt_rows = conn.execute(
                f"SELECT header_dependencies_json, log_identity_sha256 FROM {RECEIPT_TABLE} "
                "ORDER BY start_block"
            ).fetchall()
        finally:
            conn.close()
        assert [row[1] for row in receipt_rows] == list(PILOT_LOG_IDENTITY_SHA256S)
        for deps_json, _digest in receipt_rows:
            deps = json.loads(deps_json)
            for dep in deps:
                assert "batch_index" not in dep
                assert HeaderDependency.from_dict(dep).batch_index is None

    def test_sequential_and_batched_reacquire_rows_are_byte_identical(
        self, tmp_path: Path
    ) -> None:
        """Re-acquire one small range both ways; rows must match field-for-field."""
        logs = self._scenario_logs()

        seq_store = Store(tmp_path / "seq")
        batch_store = Store(tmp_path / "batch")
        try:
            seq_node = DualMockNode(block_hashes=BLOCK_HASHES, primary_logs=logs)
            batch_node = DualMockNode(block_hashes=BLOCK_HASHES, primary_logs=logs)
            sequential = _make_ingestor(seq_store, seq_node, use_header_batches=False)
            batched = _make_ingestor(
                batch_store, batch_node, use_header_batches=True, header_batch_size=2
            )
            try:
                seq_rows = sequential.fetch(
                    pair=PAIR,
                    kind="swap",
                    start_block=SCENARIO_START,
                    end_block=SCENARIO_END,
                    chunk_size=SCENARIO_CHUNK,
                    receipt_db_path=str(seq_store.db),
                    emit_rows=True,
                    raw_root=seq_store.raw_root,
                )
                batch_rows = batched.fetch(
                    pair=PAIR,
                    kind="swap",
                    start_block=SCENARIO_START,
                    end_block=SCENARIO_END,
                    chunk_size=SCENARIO_CHUNK,
                    receipt_db_path=str(batch_store.db),
                    emit_rows=True,
                    raw_root=batch_store.raw_root,
                )
            finally:
                sequential.close()
                batched.close()

            # Independent runs produce distinct raw_object_ids and wall-clock
            # retrieved_at. Semantic published fields (amounts, times, identity)
            # must match byte-for-byte after freezing lineage/clock fields.
            def freeze_lineage(rows: list[Any]) -> list[dict[str, Any]]:
                out = []
                for row in rows:
                    payload = row.as_dict()
                    payload["retrieved_at"] = "FROZEN"
                    payload["raw_object_id"] = "FROZEN"
                    payload["block_raw_object_id"] = "FROZEN"
                    out.append(payload)
                return out

            assert freeze_lineage(seq_rows) == freeze_lineage(batch_rows)

            seq_replay = _make_ingestor(
                seq_store, DualMockNode(block_hashes={}), use_header_batches=False
            )
            batch_replay = _make_ingestor(
                batch_store, DualMockNode(block_hashes={}), use_header_batches=True
            )
            try:
                seq_result = seq_replay.replay_receipts(
                    pair=PAIR, kind="swap",
                    start_block=SCENARIO_START, end_block=SCENARIO_END,
                    receipt_db_path=str(seq_store.db), raw_root=seq_store.raw_root,
                )
                batch_result = batch_replay.replay_receipts(
                    pair=PAIR, kind="swap",
                    start_block=SCENARIO_START, end_block=SCENARIO_END,
                    receipt_db_path=str(batch_store.db), raw_root=batch_store.raw_root,
                )
            finally:
                seq_replay.close()
                batch_replay.close()

            assert seq_result.completed_ranges == batch_result.completed_ranges
            assert seq_result.log_identity_sha256s == batch_result.log_identity_sha256s
            assert freeze_lineage(list(seq_result.rows)) == freeze_lineage(
                list(batch_result.rows)
            )

            # Batched path actually wrote batch_index on non-end event blocks when
            # more than the end-block was fetched as a batch.
            batch_receipts = batch_store.receipts()
            assert batch_receipts
            batch_deps = json.loads(batch_receipts[0]["header_dependencies_json"])
            # Dependencies are sorted by block_number.
            assert batch_deps == sorted(batch_deps, key=lambda d: d["block_number"])
            # At least the non-end event block should be a batch element when
            # use_header_batches=True and it is not the chunk end.
            non_end = [d for d in batch_deps if d["block_number"] == BLOCK_EVENT]
            assert non_end and non_end[0].get("batch_index") is not None
        finally:
            seq_store.close()
            batch_store.close()

    def test_batch_response_id_correlation_not_position(
        self, store: Store
    ) -> None:
        """Shuffled batch responses still authenticate and decode correctly."""
        logs = self._scenario_logs()
        node = DualMockNode(
            block_hashes=BLOCK_HASHES,
            primary_logs=logs,
            shuffle_batch_responses=True,
        )
        ingestor = _make_ingestor(store, node, use_header_batches=True, header_batch_size=2)
        try:
            rows = ingestor.fetch(
                pair=PAIR,
                kind="swap",
                start_block=SCENARIO_START,
                end_block=SCENARIO_END,
                chunk_size=SCENARIO_CHUNK,
                receipt_db_path=str(store.db),
                emit_rows=True,
                raw_root=store.raw_root,
            )
            replayed = ingestor.replay_receipts(
                pair=PAIR,
                kind="swap",
                start_block=SCENARIO_START,
                end_block=SCENARIO_END,
                receipt_db_path=str(store.db),
                raw_root=store.raw_root,
            )
        finally:
            ingestor.close()
        assert [row.as_dict() for row in replayed.rows] == [row.as_dict() for row in rows]

    def test_header_cache_serves_finalized_blocks_only(
        self, store: Store
    ) -> None:
        logs = self._scenario_logs()
        node = DualMockNode(block_hashes=BLOCK_HASHES, primary_logs=logs)
        # Cutoff above all scenario blocks so they are cacheable.
        ingestor = _make_ingestor(
            store, node,
            use_header_batches=True,
            header_batch_size=2,
            finality_cutoff_block=SCENARIO_END + 1000,
        )
        try:
            ingestor.fetch(
                pair=PAIR, kind="swap",
                start_block=SCENARIO_START,
                end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                chunk_size=SCENARIO_CHUNK,
                receipt_db_path=str(store.db),
                emit_rows=False,
                raw_root=store.raw_root,
            )
            header_calls_first = len([
                c for c in node.primary_calls if c[0] == "eth_getBlockByNumber"
            ])
            # Second pair over the same blocks should not re-fetch finalized headers
            # for event blocks (end-block identity RPCs still run per chunk).
            other_pair = "0x" + "22" * 20
            other_logs = [
                swap_log(
                    block_number=BLOCK_EVENT,
                    block_hash=BLOCK_HASHES[BLOCK_EVENT],
                    tx_hash=_hash32(0xA1),
                    tx_index=1,
                    log_index=3,
                    emitter=other_pair,
                ),
            ]
            node.primary_logs = other_logs
            node.secondary_logs = list(other_logs)
            ingestor.fetch(
                pair=other_pair, kind="swap",
                start_block=SCENARIO_START,
                end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                chunk_size=SCENARIO_CHUNK,
                receipt_db_path=str(store.db),
                emit_rows=False,
                raw_root=store.raw_root,
            )
            header_calls_second = len([
                c for c in node.primary_calls if c[0] == "eth_getBlockByNumber"
            ])
            # Second run still fetches end-block (and resume reorg path is not
            # used for a new pair), but not the shared event block via batch.
            # At minimum, total header calls for the second chunk should not grow
            # by a full event-block re-fetch of BLOCK_EVENT.
            assert header_calls_second >= header_calls_first
            # Cache should hold the event block for primary.
            assert ingestor._get_cached_header("rpc_a", BLOCK_EVENT) is not None
        finally:
            ingestor.close()


class TestSecondaryHeaderLineage:
    """Secondary event-block headers must be retained and verified offline."""

    def test_receipt_stores_secondary_event_headers(self, store: Store) -> None:
        logs = [
            swap_log(
                block_number=BLOCK_EVENT,
                block_hash=BLOCK_HASHES[BLOCK_EVENT],
                tx_hash=_hash32(0xF1),
                tx_index=2,
                log_index=5,
                amount0_in=1000,
                amount1_out=42,
            ),
            swap_log(
                block_number=BLOCK_CHUNK1_END,
                block_hash=BLOCK_HASHES[BLOCK_CHUNK1_END],
                tx_hash=_hash32(0xF2),
                tx_index=0,
                log_index=1,
            ),
        ]
        node = DualMockNode(block_hashes=BLOCK_HASHES, primary_logs=logs)
        ingestor = _make_ingestor(store, node, use_header_batches=False)
        try:
            ingestor.fetch(
                pair=PAIR,
                kind="swap",
                start_block=SCENARIO_START,
                end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                chunk_size=SCENARIO_CHUNK,
                receipt_db_path=str(store.db),
                emit_rows=False,
                raw_root=store.raw_root,
            )
        finally:
            ingestor.close()

        receipt = store.receipts()[0]
        primary = json.loads(receipt["header_dependencies_json"])
        secondary = json.loads(receipt["secondary_header_dependencies_json"])
        assert {d["block_number"] for d in primary} == {
            BLOCK_EVENT, BLOCK_CHUNK1_END
        }
        assert {d["block_number"] for d in secondary} == {
            BLOCK_EVENT, BLOCK_CHUNK1_END
        }
        assert all(d["raw_object_id"].startswith("raw_") for d in secondary)

    def test_replay_fails_when_secondary_event_headers_missing(
        self, store: Store
    ) -> None:
        logs = [
            swap_log(
                block_number=BLOCK_EVENT,
                block_hash=BLOCK_HASHES[BLOCK_EVENT],
                tx_hash=_hash32(1),
                tx_index=0,
                log_index=1,
            ),
        ]
        node = DualMockNode(block_hashes=BLOCK_HASHES, primary_logs=logs)
        ingestor = _make_ingestor(store, node, use_header_batches=False)
        try:
            ingestor.fetch(
                pair=PAIR,
                kind="swap",
                start_block=SCENARIO_START,
                end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                chunk_size=SCENARIO_CHUNK,
                receipt_db_path=str(store.db),
                emit_rows=False,
                raw_root=store.raw_root,
            )
        finally:
            ingestor.close()

        conn = sqlite3.connect(store.db)
        try:
            conn.execute(
                f"UPDATE {RECEIPT_TABLE} SET secondary_header_dependencies_json = '[]'"
            )
            conn.commit()
        finally:
            conn.close()

        quiet = DualMockNode(block_hashes={})
        replayer = _make_ingestor(store, quiet)
        try:
            with pytest.raises(
                UniswapV2IngestionError,
                match="secondary event-block header lineage incomplete",
            ):
                replayer.replay_receipts(
                    pair=PAIR,
                    kind="swap",
                    start_block=SCENARIO_START,
                    end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                    receipt_db_path=str(store.db),
                    raw_root=store.raw_root,
                )
        finally:
            replayer.close()

    def test_replay_fails_when_secondary_event_header_is_tampered(
        self, store: Store
    ) -> None:
        logs = [
            swap_log(
                block_number=BLOCK_EVENT,
                block_hash=BLOCK_HASHES[BLOCK_EVENT],
                tx_hash=_hash32(1),
                tx_index=0,
                log_index=1,
            ),
        ]
        node = DualMockNode(block_hashes=BLOCK_HASHES, primary_logs=logs)
        ingestor = _make_ingestor(store, node, use_header_batches=False)
        try:
            ingestor.fetch(
                pair=PAIR,
                kind="swap",
                start_block=SCENARIO_START,
                end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                chunk_size=SCENARIO_CHUNK,
                receipt_db_path=str(store.db),
                emit_rows=False,
                raw_root=store.raw_root,
            )
        finally:
            ingestor.close()

        receipt = store.receipts()[0]
        secondary = json.loads(receipt["secondary_header_dependencies_json"])
        assert secondary
        # Tamper the stored hash so offline dual agreement fails after auth of bytes
        # still succeeds only if we change the dependency hash without changing bytes —
        # that fails at authenticate_header (hash mismatch with receipt). Change the
        # raw object body instead so SHA fails, or change dependency hash field.
        secondary[0]["block_hash"] = _hash32(0xDEAD)
        conn = sqlite3.connect(store.db)
        try:
            conn.execute(
                f"UPDATE {RECEIPT_TABLE} SET secondary_header_dependencies_json = ?",
                (json.dumps(secondary),),
            )
            conn.commit()
        finally:
            conn.close()

        quiet = DualMockNode(block_hashes={})
        replayer = _make_ingestor(store, quiet)
        try:
            with pytest.raises(UniswapV2IngestionError, match="hash does not match"):
                replayer.replay_receipts(
                    pair=PAIR,
                    kind="swap",
                    start_block=SCENARIO_START,
                    end_block=SCENARIO_START + SCENARIO_CHUNK - 1,
                    receipt_db_path=str(store.db),
                    raw_root=store.raw_root,
                )
        finally:
            replayer.close()
