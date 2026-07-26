"""DATA-012 — tests for Uniswap V2 Factory PairCreated raw-event ingestion.

Every test exercises the shipped implementation:
``src/cryptofactors/acquisition/uniswap_v2.py``, migration 0012, and the runner
``scripts/research/ingest_uniswap_v2_pair_created.py``. Nothing here re-implements
production logic; publication is proven by driving the runner itself.

Coverage maps to the ticket acceptance criteria and the review corrections:

* mainnet only (``eth_chainId == 0x1``)        -> `TestChainSafety`
* deployment block 10_000_835 enforced         -> `TestDeploymentBlock`
* strict emitter/removed/topics/ABI/hash/
  quantity/block-identity/duplicate validation -> `TestLogValidation`
* receipts bound to acquisitions, raw ids,
  exact requests, ranges and timestamps        -> `TestReceiptBinding`
* end-header number/hash authenticated         -> `TestReceiptBinding`, `TestResume`
* every dependency verified before a skip      -> `TestResume`
* replay offline, request-bound, SHA-verified,
  contiguous, deterministic                    -> `TestReplay`
* logs acquisition time is row availability    -> `TestAvailabilityTime`
* error bytes preserved, failures recorded     -> `TestFailureRecording`
* no gaps, no duplicate (tx_hash, log_index)   -> `TestFetch`, `TestReplay`
* RPC URL from environment, never Git          -> `TestConfiguration`
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import httpx
import pyarrow.parquet as pq
import pytest

from cryptofactors.acquisition import uniswap_v2
from cryptofactors.acquisition.uniswap_v2 import (
    ETHEREUM_CHAIN,
    ETHEREUM_MAINNET_CHAIN_ID,
    FAILURE_TABLE,
    PAIR_CREATED_TOPIC,
    RECEIPT_TABLE,
    UNISWAP_V2_DEPLOYMENT_BLOCK,
    UNISWAP_V2_FACTORY,
    PairCreatedRow,
    ReplayResult,
    UniswapV2IngestionError,
    UniswapV2PairCreatedIngestor,
    _canonical_json,
    block_header_request,
    chain_id_request,
    decode_pair_created,
    logs_request,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations, get_status
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.paths import content_addressed_absolute_path
from cryptofactors.ingest.raw.writer import RawObjectWriter

# Fields the ticket requires on every published source row.
REQUIRED_ROW_FIELDS = frozenset({
    "chain", "factory", "pair", "token0", "token1",
    "block_number", "block_hash", "block_timestamp",
    "tx_hash", "tx_index", "log_index",
    "event_time", "availability_time", "raw_object_id",
})

TIMESTAMP_BASE = 1_588_000_000


# ---------------------------------------------------------------------------
# ABI / JSON-RPC fixtures
# ---------------------------------------------------------------------------

def _addr(n: int) -> str:
    return "0x" + f"{n:040x}"


def _hash32(n: int) -> str:
    return "0x" + f"{n:064x}"


def _abi_word(address: str) -> str:
    """Left-pad an address into a 32-byte ABI word, as a node returns it."""
    return "0x" + address[2:].lower().rjust(64, "0")


def pair_created_log(
    *,
    block_number: int,
    block_hash: str,
    tx_hash: str,
    tx_index: int,
    log_index: int,
    token0: str,
    token1: str,
    pair: str,
    all_pairs_length: int = 1,
    emitter: str = UNISWAP_V2_FACTORY,
) -> dict[str, Any]:
    """A `PairCreated(address,address,address,uint)` log as eth_getLogs returns it."""
    return {
        "address": emitter,
        "blockHash": block_hash,
        "blockNumber": hex(block_number),
        "data": _abi_word(pair) + f"{all_pairs_length:064x}",
        "logIndex": hex(log_index),
        "removed": False,
        "topics": [PAIR_CREATED_TOPIC, _abi_word(token0), _abi_word(token1)],
        "transactionHash": tx_hash,
        "transactionIndex": hex(tx_index),
    }


class MockEthereumNode:
    """Deterministic JSON-RPC node for eth_chainId, eth_getLogs and eth_getBlockByNumber.

    Records the exact bytes of every response so tests can assert byte-for-byte
    preservation, and every call so tests can assert which requests were and were not
    made (resume must not re-fetch; replay must not call at all).
    """

    def __init__(
        self,
        *,
        block_hashes: dict[int, str],
        logs: list[Any] | None = None,
        chain_id: str = ETHEREUM_MAINNET_CHAIN_ID,
        fail_status_for: set[str] | None = None,
        rpc_error_for: set[str] | None = None,
        invalid_json_for: set[str] | None = None,
        transport_error_for: set[str] | None = None,
        honour_block_range: bool = True,
        omit_header_fields: set[str] | None = None,
        header_number_override: dict[int, int] | None = None,
    ) -> None:
        self.block_hashes = block_hashes
        self.logs = logs if logs is not None else []
        self.chain_id = chain_id
        self.fail_status_for = fail_status_for or set()
        self.rpc_error_for = rpc_error_for or set()
        self.invalid_json_for = invalid_json_for or set()
        self.transport_error_for = transport_error_for or set()
        self.honour_block_range = honour_block_range
        self.omit_header_fields = omit_header_fields or set()
        self.header_number_override = header_number_override or {}
        self.calls: list[tuple[str, Any]] = []
        self.served: list[bytes] = []

    @staticmethod
    def timestamp(block_number: int) -> int:
        return TIMESTAMP_BASE + block_number

    def methods(self) -> list[str]:
        return [method for method, _ in self.calls]

    def _respond(self, status: int, payload: dict[str, Any]) -> httpx.Response:
        body = json.dumps(payload).encode()
        self.served.append(body)
        return httpx.Response(status, content=body, headers={"content-type": "application/json"})

    @staticmethod
    def _error(message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": message}}

    def handler(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.read())
        method = payload["method"]
        params = payload["params"]
        self.calls.append((method, params))

        if method in self.transport_error_for:
            raise httpx.ConnectError("connection refused", request=request)
        if method in self.fail_status_for:
            return self._respond(500, self._error("upstream failure"))
        if method in self.rpc_error_for:
            return self._respond(200, self._error("rejected by node"))
        if method in self.invalid_json_for:
            body = b"<html><body>502 Bad Gateway</body></html>"
            self.served.append(body)
            return httpx.Response(200, content=body, headers={"content-type": "text/html"})

        if method == "eth_chainId":
            return self._respond(200, {"jsonrpc": "2.0", "id": 1, "result": self.chain_id})

        if method == "eth_getBlockByNumber":
            number = int(params[0], 16)
            if number not in self.block_hashes:
                return self._respond(200, self._error(f"unknown block {number}"))
            reported = self.header_number_override.get(number, number)
            header: dict[str, Any] = {
                "number": hex(reported),
                "hash": self.block_hashes[number],
                "parentHash": _hash32(number - 1),
                "timestamp": hex(self.timestamp(number)),
            }
            for field in self.omit_header_fields:
                header.pop(field, None)
            return self._respond(200, {"jsonrpc": "2.0", "id": 1, "result": header})

        if method == "eth_getLogs":
            from_block = int(params[0]["fromBlock"], 16)
            to_block = int(params[0]["toBlock"], 16)
            selected = [
                log for log in self.logs
                if not self.honour_block_range
                or (isinstance(log, dict)
                    and from_block <= int(log["blockNumber"], 16) <= to_block)
            ]
            return self._respond(200, {"jsonrpc": "2.0", "id": 1, "result": selected})

        return self._respond(200, self._error(f"unsupported method {method}"))

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Point `httpx.Client()` built inside the ingestor at this node (runner path)."""
        real_client = httpx.Client
        monkeypatch.setattr(
            uniswap_v2.httpx,
            "Client",
            lambda **_kwargs: real_client(transport=httpx.MockTransport(self.handler)),
        )


def exploding_client() -> httpx.Client:
    """A client that fails the test if anything touches the network."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"unexpected network call to {request.url}")

    return httpx.Client(transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# Store / receipt helpers
# ---------------------------------------------------------------------------

class Store:
    """Raw object store plus the control database holding chunk receipts."""

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

    def receipt(self, start_block: int) -> dict[str, Any]:
        rows = [r for r in self.receipts() if r["start_block"] == start_block]
        assert len(rows) == 1, f"expected exactly one receipt at {start_block}"
        return rows[0]

    def failures(self) -> list[dict[str, Any]]:
        return self._query(f"SELECT * FROM {FAILURE_TABLE} ORDER BY failure_id")

    def update_receipt(self, _where_start_block: int, /, **columns: Any) -> None:
        assignments = ", ".join(f"{name} = ?" for name in columns)
        conn = sqlite3.connect(self.db)
        try:
            conn.execute(
                f"UPDATE {RECEIPT_TABLE} SET {assignments} WHERE start_block = ?",
                (*columns.values(), _where_start_block),
            )
            conn.commit()
        finally:
            conn.close()

    def acquisitions(self) -> list[dict[str, Any]]:
        return self._query("SELECT * FROM raw_acquisition ORDER BY acquired_at")

    def acquisition(self, acquisition_id: str) -> dict[str, Any]:
        rows = self._query(
            "SELECT * FROM raw_acquisition WHERE acquisition_id = ?", (acquisition_id,)
        )
        assert len(rows) == 1, f"expected exactly one acquisition {acquisition_id}"
        return rows[0]

    def update_acquisition(self, acquisition_id: str, **columns: Any) -> None:
        assignments = ", ".join(f"{name} = ?" for name in columns)
        conn = sqlite3.connect(self.db)
        try:
            conn.execute(
                f"UPDATE raw_acquisition SET {assignments} WHERE acquisition_id = ?",
                (*columns.values(), acquisition_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_acquisition(self, acquisition_id: str) -> None:
        conn = sqlite3.connect(self.db)
        try:
            conn.execute(
                "DELETE FROM raw_acquisition WHERE acquisition_id = ?", (acquisition_id,)
            )
            conn.commit()
        finally:
            conn.close()

    def clone_receipt_for_factory(self, start_block: int, factory: str) -> None:
        """Copy a receipt under a different factory, leaving the original in place."""
        row = self.receipt(start_block)
        row["factory"] = factory
        conn = sqlite3.connect(self.db)
        try:
            conn.execute(
                f"INSERT INTO {RECEIPT_TABLE} ({', '.join(row)}) "
                f"VALUES ({', '.join('?' for _ in row)})",
                tuple(row.values()),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_receipts_for_factory(self, factory: str) -> None:
        conn = sqlite3.connect(self.db)
        try:
            conn.execute(f"DELETE FROM {RECEIPT_TABLE} WHERE factory = ?", (factory,))
            conn.commit()
        finally:
            conn.close()

    def raw_path(self, raw_object_id: str) -> Path:
        return content_addressed_absolute_path(self.raw_root, raw_object_id.removeprefix("raw_"))

    def overwrite_raw(self, raw_object_id: str, body: bytes) -> None:
        path = self.raw_path(raw_object_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[Store]:
    created = Store(tmp_path)
    yield created
    created.close()


# ---------------------------------------------------------------------------
# A two-chunk scenario starting exactly at the deployment block: events in the
# first chunk, an empty second chunk. The empty chunk is what makes the
# end-block header a mandatory, independently-authenticated dependency.
# ---------------------------------------------------------------------------

SCENARIO_START = UNISWAP_V2_DEPLOYMENT_BLOCK
SCENARIO_CHUNK = 100
SCENARIO_END = SCENARIO_START + 199

BLOCK_EVENT = SCENARIO_START + 15       # carries two events
BLOCK_CHUNK1_END = SCENARIO_START + 99  # carries one event and ends chunk 1
BLOCK_CHUNK2_END = SCENARIO_END         # empty chunk's end block

TOKEN_A, TOKEN_B, TOKEN_C = _addr(0xA1), _addr(0xB2), _addr(0xC3)
PAIR_1, PAIR_2, PAIR_3 = _addr(0x11), _addr(0x22), _addr(0x33)

SCENARIO_BLOCK_HASHES = {
    BLOCK_EVENT: _hash32(BLOCK_EVENT),
    BLOCK_CHUNK1_END: _hash32(BLOCK_CHUNK1_END),
    BLOCK_CHUNK2_END: _hash32(BLOCK_CHUNK2_END),
}

TX_1, TX_2, TX_3 = _hash32(0xF1), _hash32(0xF2), _hash32(0xF3)

# Served out of order so ordering is proven, not inherited from the node.
SCENARIO_LOGS: list[Any] = [
    pair_created_log(
        block_number=BLOCK_CHUNK1_END, block_hash=_hash32(BLOCK_CHUNK1_END), tx_hash=TX_3,
        tx_index=1, log_index=4, token0=TOKEN_A, token1=TOKEN_C, pair=PAIR_3,
    ),
    pair_created_log(
        block_number=BLOCK_EVENT, block_hash=_hash32(BLOCK_EVENT), tx_hash=TX_2,
        tx_index=3, log_index=7, token0=TOKEN_B, token1=TOKEN_C, pair=PAIR_2,
    ),
    pair_created_log(
        block_number=BLOCK_EVENT, block_hash=_hash32(BLOCK_EVENT), tx_hash=TX_1,
        tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
    ),
]

SCENARIO_EXPECTED_ORDER = [
    (BLOCK_EVENT, 0, 0),
    (BLOCK_EVENT, 3, 7),
    (BLOCK_CHUNK1_END, 1, 4),
]
SCENARIO_RANGES = [
    (SCENARIO_START, BLOCK_CHUNK1_END),
    (BLOCK_CHUNK1_END + 1, SCENARIO_END),
]


def scenario_node(**overrides: Any) -> MockEthereumNode:
    kwargs: dict[str, Any] = {
        "block_hashes": dict(SCENARIO_BLOCK_HASHES),
        "logs": list(SCENARIO_LOGS),
    }
    kwargs.update(overrides)
    return MockEthereumNode(**kwargs)


def make_ingestor(
    store: Store, node: MockEthereumNode | None = None, **overrides: Any
) -> UniswapV2PairCreatedIngestor:
    kwargs: dict[str, Any] = {
        "rpc_url": "http://node.invalid",
        "raw_writer": store.writer,
        "raw_root": store.raw_root,
        "client": exploding_client() if node is None else node.client(),
    }
    kwargs.update(overrides)
    return UniswapV2PairCreatedIngestor(**kwargs)


def run_fetch(
    store: Store, node: MockEthereumNode, **kwargs: Any
) -> list[PairCreatedRow]:
    params: dict[str, Any] = {
        "start_block": SCENARIO_START,
        "end_block": SCENARIO_END,
        "chunk_size": SCENARIO_CHUNK,
        "receipt_db_path": str(store.db),
    }
    params.update(kwargs)
    ingestor = make_ingestor(store, node)
    try:
        return ingestor.fetch(**params)
    finally:
        ingestor.close()


def run_replay(store: Store, **kwargs: Any) -> ReplayResult:
    """Replay with a client that raises if the network is touched."""
    params: dict[str, Any] = {
        "start_block": SCENARIO_START,
        "end_block": SCENARIO_END,
        "receipt_db_path": str(store.db),
    }
    params.update(kwargs)
    ingestor = make_ingestor(store)
    try:
        return ingestor.replay_receipts(**params)
    finally:
        ingestor.close()


def declared_raw_object_ids(receipts: list[dict[str, Any]]) -> set[str]:
    declared: set[str] = set()
    for receipt in receipts:
        declared.add(str(receipt["logs_raw_object_id"]))
        declared.add(str(receipt["end_header_raw_object_id"]))
        declared.add(str(receipt["chain_id_raw_object_id"]))
        for dep in json.loads(receipt["header_dependencies_json"]):
            declared.add(str(dep["raw_object_id"]))
    return declared


def declared_acquisition_ids(receipts: list[dict[str, Any]]) -> set[str]:
    declared: set[str] = set()
    for receipt in receipts:
        declared.add(str(receipt["logs_acquisition_id"]))
        declared.add(str(receipt["end_header_acquisition_id"]))
        declared.add(str(receipt["chain_id_acquisition_id"]))
        for dep in json.loads(receipt["header_dependencies_json"]):
            declared.add(str(dep["acquisition_id"]))
    return declared


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------

class TestMigrations:
    def test_uniswap_migrations_apply_on_a_fresh_database(self, tmp_path: Path) -> None:
        db = tmp_path / "control.db"
        apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
        applied = get_status(db, migrations_dir=MIGRATIONS_DIR)["applied"]
        for version in ("0009", "0010", "0011", "0012"):
            assert any(version in name for name in applied), f"migration {version} not applied"

    def test_completed_migrations_are_not_replaced(self, store: Store) -> None:
        """0012 is forward-only: the v2 table it supersedes still exists untouched."""
        conn = sqlite3.connect(store.db)
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()
        assert "uniswap_v2_pair_created_chunk_receipt_v2" in tables
        assert RECEIPT_TABLE in tables
        assert FAILURE_TABLE in tables

    def test_receipt_table_binds_identity_requests_acquisitions_and_timestamps(
        self, store: Store
    ) -> None:
        conn = sqlite3.connect(store.db)
        try:
            columns = conn.execute(f"PRAGMA table_info({RECEIPT_TABLE})").fetchall()
        finally:
            conn.close()

        names = {row[1] for row in columns}
        assert {
            "chain", "chain_id", "factory", "topic", "start_block", "end_block",
            "logs_request_json", "logs_raw_object_id", "logs_acquisition_id",
            "logs_acquired_at", "end_block_number", "end_block_hash",
            "end_header_request_json", "end_header_raw_object_id",
            "end_header_acquisition_id", "end_header_acquired_at",
            "header_dependencies_json", "completed_at",
        } <= names
        primary_key = [row[1] for row in sorted(columns, key=lambda row: row[5]) if row[5]]
        assert primary_key == ["chain", "factory", "topic", "start_block", "end_block"]

    def test_receipt_identity_allows_the_same_range_for_a_different_factory(
        self, store: Store
    ) -> None:
        """Why the identity check lives in the query, not in a per-row assertion."""
        run_fetch(store, scenario_node())
        store.clone_receipt_for_factory(SCENARIO_START, _addr(0xDEAD))

        factories = {receipt["factory"] for receipt in store.receipts()}
        assert factories == {UNISWAP_V2_FACTORY, _addr(0xDEAD)}


# ---------------------------------------------------------------------------
# Chain safety and range guards
# ---------------------------------------------------------------------------

class TestChainSafety:
    def test_the_chain_id_is_verified_before_any_logs_are_requested(
        self, store: Store
    ) -> None:
        node = scenario_node()
        run_fetch(store, node)

        assert node.methods()[0] == "eth_chainId"

    def test_the_chain_id_is_verified_once_per_ingestor(self, store: Store) -> None:
        node = scenario_node()
        run_fetch(store, node)

        assert node.methods().count("eth_chainId") == 1

    @pytest.mark.parametrize("chain_id", ["0x5", "0x89", "0xa"])
    def test_a_non_mainnet_endpoint_is_refused(self, store: Store, chain_id: str) -> None:
        node = scenario_node(chain_id=chain_id)
        with pytest.raises(UniswapV2IngestionError, match="mainnet chain id"):
            run_fetch(store, node)

    def test_a_non_mainnet_endpoint_is_refused_before_any_receipt_is_written(
        self, store: Store
    ) -> None:
        node = scenario_node(chain_id="0x5")
        with pytest.raises(UniswapV2IngestionError):
            run_fetch(store, node)

        assert store.receipts() == []
        assert node.methods() == ["eth_chainId"]

    @pytest.mark.parametrize("chain_id", [None, "", "not-hex", "1"])
    def test_a_malformed_chain_id_is_refused(self, store: Store, chain_id: Any) -> None:
        node = scenario_node(chain_id=chain_id)
        with pytest.raises(UniswapV2IngestionError):
            run_fetch(store, node)


class TestDeploymentBlock:
    def test_a_range_starting_before_deployment_is_refused(self, store: Store) -> None:
        node = scenario_node()
        with pytest.raises(UniswapV2IngestionError, match="must be the Uniswap V2 Factory"):
            run_fetch(
                store, node,
                start_block=UNISWAP_V2_DEPLOYMENT_BLOCK - 1,
                end_block=UNISWAP_V2_DEPLOYMENT_BLOCK + 99,
            )

    def test_a_range_starting_after_deployment_is_refused(self, store: Store) -> None:
        """A later start silently omits pairs while still producing a receipt chain
        that looks complete, so the ticket's deployment start is exact, not a floor."""
        node = scenario_node()
        with pytest.raises(UniswapV2IngestionError, match="must be the Uniswap V2 Factory"):
            run_fetch(
                store, node,
                start_block=UNISWAP_V2_DEPLOYMENT_BLOCK + 1,
                end_block=SCENARIO_END,
            )

        assert node.calls == [], "refused before contacting the node"

    def test_a_range_starting_before_deployment_is_refused_without_touching_the_node(
        self, store: Store
    ) -> None:
        node = scenario_node()
        with pytest.raises(UniswapV2IngestionError):
            run_fetch(store, node, start_block=0, end_block=100)

        assert node.calls == []

    def test_a_range_starting_exactly_at_deployment_is_accepted(self, store: Store) -> None:
        rows = run_fetch(store, scenario_node())

        assert [(r.block_number, r.tx_index, r.log_index) for r in rows] == SCENARIO_EXPECTED_ORDER

    @pytest.mark.parametrize(
        ("start_block", "end_block", "chunk_size"),
        [
            (-1, SCENARIO_END, 10),
            (SCENARIO_END, SCENARIO_START, 10),
            (SCENARIO_START, SCENARIO_END, 0),
            (SCENARIO_START, SCENARIO_END, -5),
        ],
    )
    def test_an_invalid_range_or_chunk_size_is_refused(
        self, store: Store, start_block: int, end_block: int, chunk_size: int
    ) -> None:
        with pytest.raises(ValueError):
            run_fetch(
                store, scenario_node(),
                start_block=start_block, end_block=end_block, chunk_size=chunk_size,
            )


# ---------------------------------------------------------------------------
# Acquisition
# ---------------------------------------------------------------------------

class TestFetch:
    def test_chunks_cover_the_requested_range_without_gaps_or_overlap(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        ranges = [(r["start_block"], r["end_block"]) for r in store.receipts()]

        assert ranges == SCENARIO_RANGES
        assert ranges[0][0] == SCENARIO_START
        assert ranges[-1][1] == SCENARIO_END
        for previous, following in pairwise(ranges):
            assert following[0] == previous[1] + 1, "receipt ranges must be contiguous"

    def test_rows_are_ordered_by_block_transaction_and_log_index(self, store: Store) -> None:
        rows = run_fetch(store, scenario_node())
        assert [(r.block_number, r.tx_index, r.log_index) for r in rows] == SCENARIO_EXPECTED_ORDER

    def test_fetched_rows_have_no_duplicate_transaction_and_log_index(
        self, store: Store
    ) -> None:
        rows = run_fetch(store, scenario_node())
        identities = [(row.tx_hash, row.log_index) for row in rows]

        assert len(identities) == len(set(identities)) == len(SCENARIO_LOGS)

    def test_an_empty_chunk_still_produces_a_receipt_with_its_end_header(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        empty = store.receipt(BLOCK_CHUNK1_END + 1)

        assert empty["end_block_hash"] == _hash32(BLOCK_CHUNK2_END)
        assert json.loads(empty["header_dependencies_json"]) == []
        assert empty["end_header_raw_object_id"].startswith("raw_")

    def test_emit_rows_false_still_writes_receipts(self, store: Store) -> None:
        """The runner acquires with emit_rows=False and decodes from receipts only."""
        rows = run_fetch(store, scenario_node(), emit_rows=False)

        assert rows == []
        assert len(store.receipts()) == 2

    def test_a_log_outside_the_requested_chunk_is_refused(self, store: Store) -> None:
        """A node that ignores fromBlock/toBlock must not silently widen coverage."""
        stray = pair_created_log(
            block_number=SCENARIO_END + 5_000, block_hash=_hash32(1), tx_hash=_hash32(0xEE),
            tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
        )
        node = scenario_node(logs=[stray], honour_block_range=False)

        with pytest.raises(UniswapV2IngestionError, match="outside requested chunk"):
            run_fetch(store, node)

    def test_a_header_reporting_the_wrong_block_number_is_refused(self, store: Store) -> None:
        node = scenario_node(header_number_override={BLOCK_EVENT: BLOCK_EVENT + 1})

        with pytest.raises(UniswapV2IngestionError, match="reports block"):
            run_fetch(store, node)

    def test_an_end_header_reporting_the_wrong_block_number_is_refused(
        self, store: Store
    ) -> None:
        node = scenario_node(
            logs=[], header_number_override={BLOCK_CHUNK1_END: BLOCK_CHUNK1_END + 1}
        )

        with pytest.raises(UniswapV2IngestionError, match="end-block header is for block"):
            run_fetch(store, node)

    def test_each_block_header_is_fetched_exactly_once(self, store: Store) -> None:
        """BLOCK_CHUNK1_END carries an event *and* ends its chunk. Requesting it twice
        would cost one redundant round trip per chunk against a metered endpoint."""
        node = scenario_node()
        run_fetch(store, node)

        header_blocks = [
            int(params[0], 16) for method, params in node.calls
            if method == "eth_getBlockByNumber"
        ]

        assert sorted(header_blocks) == [BLOCK_EVENT, BLOCK_CHUNK1_END, BLOCK_CHUNK2_END]
        assert header_blocks.count(BLOCK_EVENT) == 1, "two events, one header"
        assert header_blocks.count(BLOCK_CHUNK1_END) == 1, "event block reused as end header"

    def test_a_reused_end_header_is_still_bound_as_both_dependencies(
        self, store: Store
    ) -> None:
        """Reusing the acquisition must not weaken the receipt: the block appears as an
        event-header dependency and as the end header, naming the same evidence."""
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)
        dependencies = {
            dep["block_number"]: dep
            for dep in json.loads(receipt["header_dependencies_json"])
        }

        assert BLOCK_CHUNK1_END in dependencies
        reused = dependencies[BLOCK_CHUNK1_END]
        assert receipt["end_header_raw_object_id"] == reused["raw_object_id"]
        assert receipt["end_header_acquisition_id"] == reused["acquisition_id"]
        assert receipt["end_header_request_json"] == reused["request_json"]
        assert receipt["end_block_hash"] == reused["block_hash"]

    def test_an_event_repeated_across_chunks_is_refused(self, store: Store) -> None:
        """Per-chunk decoding cannot see a duplicate that straddles a chunk boundary.

        Both copies sit inside their own chunk, so the in-chunk range guard passes and
        only a range-wide identity check can catch the repeat.
        """
        second_block = BLOCK_CHUNK1_END + 10
        common = {
            "tx_hash": TX_1, "tx_index": 0, "log_index": 0,
            "token0": TOKEN_A, "token1": TOKEN_B, "pair": PAIR_1,
        }
        node = scenario_node(
            block_hashes={
                BLOCK_EVENT: _hash32(BLOCK_EVENT),
                BLOCK_CHUNK1_END: _hash32(BLOCK_CHUNK1_END),
                second_block: _hash32(second_block),
                BLOCK_CHUNK2_END: _hash32(BLOCK_CHUNK2_END),
            },
            logs=[
                pair_created_log(
                    block_number=BLOCK_EVENT, block_hash=_hash32(BLOCK_EVENT), **common
                ),
                pair_created_log(
                    block_number=second_block, block_hash=_hash32(second_block), **common
                ),
            ],
        )

        with pytest.raises(UniswapV2IngestionError, match="duplicate"):
            run_fetch(store, node)

    def test_the_receipt_database_is_closed_when_acquisition_fails(
        self, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        opened: list[sqlite3.Connection] = []
        real_connect = sqlite3.connect

        def tracking_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
            conn = real_connect(*args, **kwargs)
            opened.append(conn)
            return conn

        monkeypatch.setattr(uniswap_v2.sqlite3, "connect", tracking_connect)

        with pytest.raises(UniswapV2IngestionError):
            run_fetch(store, scenario_node(fail_status_for={"eth_getLogs"}))

        assert opened, "fetch did not open the receipt database"
        for conn in opened:
            with pytest.raises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")


# ---------------------------------------------------------------------------
# Receipt binding
# ---------------------------------------------------------------------------

class TestReceiptBinding:
    def test_the_receipt_records_the_exact_logs_request_it_answers(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)

        assert receipt["logs_request_json"] == _canonical_json(
            logs_request(
                factory=UNISWAP_V2_FACTORY,
                start_block=SCENARIO_START,
                end_block=BLOCK_CHUNK1_END,
            )
        )

    def test_the_receipt_records_the_exact_end_header_request_it_answers(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)

        assert receipt["end_header_request_json"] == _canonical_json(
            block_header_request(BLOCK_CHUNK1_END)
        )

    def test_the_receipt_binds_raw_objects_and_acquisition_ids(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)

        assert receipt["logs_raw_object_id"].startswith("raw_")
        assert receipt["end_header_raw_object_id"].startswith("raw_")
        assert receipt["logs_acquisition_id"]
        assert receipt["end_header_acquisition_id"]
        assert receipt["logs_acquisition_id"] != receipt["end_header_acquisition_id"]

    def test_the_receipt_records_chain_identity_and_range(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)

        assert receipt["chain"] == ETHEREUM_CHAIN
        assert receipt["chain_id"] == ETHEREUM_MAINNET_CHAIN_ID
        assert receipt["factory"] == UNISWAP_V2_FACTORY
        assert receipt["topic"] == PAIR_CREATED_TOPIC
        assert receipt["start_block"] == SCENARIO_START
        assert receipt["end_block"] == BLOCK_CHUNK1_END

    def test_the_receipt_authenticates_the_end_block_identity(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)

        assert receipt["end_block_number"] == receipt["end_block"] == BLOCK_CHUNK1_END
        assert receipt["end_block_hash"] == _hash32(BLOCK_CHUNK1_END)

    def test_every_event_block_header_is_bound_individually(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        dependencies = json.loads(store.receipt(SCENARIO_START)["header_dependencies_json"])

        by_block = {dep["block_number"]: dep for dep in dependencies}
        assert set(by_block) == {BLOCK_EVENT, BLOCK_CHUNK1_END}
        for block_number, dep in by_block.items():
            assert dep["block_hash"] == _hash32(block_number)
            assert dep["request_json"] == _canonical_json(block_header_request(block_number))
            assert dep["raw_object_id"].startswith("raw_")
            assert dep["acquisition_id"]
            assert datetime.fromisoformat(dep["acquired_at"]).tzinfo is not None

    def test_receipt_timestamps_are_timezone_aware_and_ordered(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)

        logs_at = datetime.fromisoformat(receipt["logs_acquired_at"])
        end_at = datetime.fromisoformat(receipt["end_header_acquired_at"])
        completed_at = datetime.fromisoformat(receipt["completed_at"])

        for moment in (logs_at, end_at, completed_at):
            assert moment.tzinfo is not None
        assert logs_at <= completed_at
        assert end_at <= completed_at
        assert completed_at == max(logs_at, end_at, *(
            datetime.fromisoformat(dep["acquired_at"])
            for dep in json.loads(receipt["header_dependencies_json"])
        ))

    def test_preserved_objects_are_the_exact_response_bytes(self, store: Store) -> None:
        node = scenario_node()
        run_fetch(store, node)

        served = set(node.served)
        declared = declared_raw_object_ids(store.receipts())
        assert declared

        for raw_object_id in declared:
            body = store.raw_path(raw_object_id).read_bytes()
            assert body in served, f"{raw_object_id} is not a byte-for-byte response"
            assert f"raw_{hashlib.sha256(body).hexdigest()}" == raw_object_id


class TestReceiptConstraints:
    """Schema-level invariants.

    These are enforced by migration 0012's CHECK constraints rather than by a
    read-time assertion, so an inconsistent receipt cannot be written by any writer
    — including one outside this module.
    """

    def test_a_receipt_cannot_record_a_non_mainnet_chain(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        with pytest.raises(sqlite3.IntegrityError, match="chain_id"):
            store.update_receipt(SCENARIO_START, chain_id="0x5")

    def test_a_receipt_cannot_disagree_with_itself_about_the_end_block(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        with pytest.raises(sqlite3.IntegrityError, match="end_block_number"):
            store.update_receipt(SCENARIO_START, end_block_number=BLOCK_CHUNK1_END + 1)

    def test_a_receipt_cannot_invert_its_block_range(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        with pytest.raises(sqlite3.IntegrityError, match="end_block"):
            store.update_receipt(SCENARIO_START, start_block=SCENARIO_END + 1_000)

    def test_a_receipt_cannot_record_a_negative_start_block(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        with pytest.raises(sqlite3.IntegrityError, match="start_block"):
            store.update_receipt(SCENARIO_START, start_block=-1)

    def test_a_failure_row_must_carry_a_known_failure_kind(self, store: Store) -> None:
        conn = sqlite3.connect(store.db)
        try:
            with pytest.raises(sqlite3.IntegrityError, match="failure_kind"):
                conn.execute(
                    f"INSERT INTO {FAILURE_TABLE} "
                    "(chain, factory, topic, method, request_json, start_block, end_block, "
                    "failure_kind, detail, occurred_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (ETHEREUM_CHAIN, UNISWAP_V2_FACTORY, PAIR_CREATED_TOPIC, "eth_getLogs",
                     "{}", 1, 2, "not_a_kind", "detail", "2026-07-25T00:00:00+00:00"),
                )
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Strict log validation
# ---------------------------------------------------------------------------

def _header(block_number: int, block_hash: str, timestamp: int = 1_700_000_000) -> dict[str, Any]:
    return {"number": hex(block_number), "hash": block_hash, "timestamp": hex(timestamp)}


def _decode(
    logs: list[Any], headers: dict[int, tuple[dict[str, Any], str]] | None = None
) -> list[PairCreatedRow]:
    if headers is None:
        headers = {BLOCK_EVENT: (_header(BLOCK_EVENT, _hash32(BLOCK_EVENT)), "raw_" + "b" * 64)}
    return decode_pair_created(
        {"jsonrpc": "2.0", "id": 1, "result": logs},
        headers,
        factory=UNISWAP_V2_FACTORY,
        log_raw_object_id="raw_" + "a" * 64,
        availability_time=datetime(2026, 7, 25, 12, 0, tzinfo=UTC),
    )


def _valid_log(**overrides: Any) -> dict[str, Any]:
    log = pair_created_log(
        block_number=BLOCK_EVENT, block_hash=_hash32(BLOCK_EVENT), tx_hash=TX_1,
        tx_index=3, log_index=7, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
    )
    log.update(overrides)
    return log


class TestLogValidation:
    def test_every_required_source_field_is_populated(self) -> None:
        timestamp = 1_700_000_150
        headers = {BLOCK_EVENT: (
            _header(BLOCK_EVENT, _hash32(BLOCK_EVENT), timestamp), "raw_" + "b" * 64
        )}

        (row,) = _decode([_valid_log()], headers)
        record = row.as_dict()

        assert REQUIRED_ROW_FIELDS <= set(record)
        assert record["chain"] == ETHEREUM_CHAIN
        assert record["factory"] == UNISWAP_V2_FACTORY
        assert record["pair"] == PAIR_1
        assert record["token0"] == TOKEN_A
        assert record["token1"] == TOKEN_B
        assert record["block_number"] == BLOCK_EVENT
        assert record["block_hash"] == _hash32(BLOCK_EVENT)
        assert record["block_timestamp"] == timestamp
        assert record["tx_hash"] == TX_1
        assert record["tx_index"] == 3
        assert record["log_index"] == 7
        assert record["raw_object_id"] == "raw_" + "a" * 64
        assert record["block_raw_object_id"] == "raw_" + "b" * 64

    def test_a_log_from_another_emitter_is_refused(self) -> None:
        """A topic filter alone does not prove the factory emitted the event."""
        with pytest.raises(UniswapV2IngestionError, match="expected factory"):
            _decode([_valid_log(address=_addr(0xDEAD))])

    def test_an_emitter_differing_only_by_case_is_accepted(self) -> None:
        (row,) = _decode([_valid_log(address=UNISWAP_V2_FACTORY.lower())])
        assert row.factory == UNISWAP_V2_FACTORY

    def test_a_reorg_removed_log_is_refused(self) -> None:
        with pytest.raises(UniswapV2IngestionError, match="reorg-removed"):
            _decode([_valid_log(removed=True)])

    def test_a_log_without_a_removed_flag_is_refused(self) -> None:
        log = _valid_log()
        del log["removed"]
        with pytest.raises(UniswapV2IngestionError, match="missing 'removed'"):
            _decode([log])

    @pytest.mark.parametrize("count", [0, 1, 2, 4])
    def test_a_topic_list_of_the_wrong_length_is_refused(self, count: int) -> None:
        log = _valid_log()
        topics = list(log["topics"])
        log["topics"] = (topics + [_hash32(9)] * 4)[:count]
        with pytest.raises(UniswapV2IngestionError, match="topics"):
            _decode([log])

    def test_a_foreign_event_topic_is_refused(self) -> None:
        with pytest.raises(UniswapV2IngestionError, match="topics"):
            _decode([_valid_log(topics=[_hash32(0x5117), _abi_word(TOKEN_A), _abi_word(TOKEN_B)])])

    def test_a_topic_of_the_wrong_byte_length_is_refused(self) -> None:
        with pytest.raises(UniswapV2IngestionError, match="32 bytes"):
            _decode([_valid_log(topics=["0xabcd", _abi_word(TOKEN_A), _abi_word(TOKEN_B)])])

    def test_an_address_word_with_dirty_padding_is_refused(self) -> None:
        """A non-zero high byte means the word is not an address; truncating would lie."""
        dirty = "0x" + "ff" + "0" * 22 + TOKEN_A[2:]
        with pytest.raises(UniswapV2IngestionError, match="left-padded 20-byte address"):
            _decode([_valid_log(topics=[PAIR_CREATED_TOPIC, dirty, _abi_word(TOKEN_B)])])

    @pytest.mark.parametrize("data", ["0x", "0x00", _abi_word(PAIR_1), _abi_word(PAIR_1) + "00"])
    def test_event_data_of_the_wrong_length_is_refused(self, data: str) -> None:
        with pytest.raises(UniswapV2IngestionError, match="log data"):
            _decode([_valid_log(data=data)])

    def test_a_block_hash_of_the_wrong_length_is_refused(self) -> None:
        with pytest.raises(UniswapV2IngestionError, match="blockHash"):
            _decode([_valid_log(blockHash="0xbb")])

    def test_a_transaction_hash_of_the_wrong_length_is_refused(self) -> None:
        with pytest.raises(UniswapV2IngestionError, match="transactionHash"):
            _decode([_valid_log(transactionHash="0xaa")])

    @pytest.mark.parametrize("field", ["blockNumber", "logIndex", "transactionIndex"])
    def test_a_non_hex_quantity_is_refused(self, field: str) -> None:
        with pytest.raises(UniswapV2IngestionError, match="hex quantity"):
            _decode([_valid_log(**{field: 12345})])

    def test_a_log_whose_block_hash_contradicts_the_header_is_refused(self) -> None:
        headers = {BLOCK_EVENT: (_header(BLOCK_EVENT, _hash32(0xBAD)), "raw_" + "b" * 64)}
        with pytest.raises(UniswapV2IngestionError, match="does not match block header"):
            _decode([_valid_log()], headers)

    def test_a_header_for_a_different_block_is_refused(self) -> None:
        headers = {BLOCK_EVENT: (
            _header(BLOCK_EVENT + 1, _hash32(BLOCK_EVENT)), "raw_" + "b" * 64
        )}
        with pytest.raises(UniswapV2IngestionError, match="preserved header is for block"):
            _decode([_valid_log()], headers)

    def test_a_log_with_no_preserved_header_is_refused(self) -> None:
        with pytest.raises(UniswapV2IngestionError, match="no preserved block header"):
            _decode([_valid_log()], {})

    def test_duplicate_transaction_and_log_index_is_refused(self) -> None:
        with pytest.raises(UniswapV2IngestionError, match="duplicate"):
            _decode([_valid_log(), _valid_log()])

    def test_duplicate_detection_is_case_normalised(self) -> None:
        """Providers differ on hash casing; 0xAB.. and 0xab.. are the same event."""
        upper = _valid_log(transactionHash="0x" + TX_1[2:].upper())
        with pytest.raises(UniswapV2IngestionError, match="duplicate"):
            _decode([_valid_log(), upper])

    def test_hashes_are_normalised_on_output(self) -> None:
        headers = {BLOCK_EVENT: (
            _header(BLOCK_EVENT, "0x" + _hash32(BLOCK_EVENT)[2:].upper()), "raw_" + "b" * 64
        )}
        (row,) = _decode(
            [_valid_log(
                transactionHash="0x" + TX_1[2:].upper(),
                blockHash="0x" + _hash32(BLOCK_EVENT)[2:].upper(),
            )],
            headers,
        )
        assert row.tx_hash == TX_1
        assert row.block_hash == _hash32(BLOCK_EVENT)

    def test_rows_are_sorted_by_block_transaction_and_log_index(self) -> None:
        headers = {
            BLOCK_EVENT: (_header(BLOCK_EVENT, _hash32(BLOCK_EVENT), 1), "raw_" + "b" * 64),
            BLOCK_EVENT + 1: (
                _header(BLOCK_EVENT + 1, _hash32(BLOCK_EVENT + 1), 2), "raw_" + "c" * 64
            ),
        }
        logs = [
            _valid_log(
                blockNumber=hex(BLOCK_EVENT + 1), blockHash=_hash32(BLOCK_EVENT + 1),
                transactionHash=TX_3, transactionIndex=hex(0), logIndex=hex(0),
            ),
            _valid_log(transactionHash=TX_2, transactionIndex=hex(2), logIndex=hex(9)),
            _valid_log(transactionHash=TX_1, transactionIndex=hex(2), logIndex=hex(1)),
        ]

        rows = _decode(logs, headers)

        assert [(r.block_number, r.tx_index, r.log_index) for r in rows] == [
            (BLOCK_EVENT, 2, 1), (BLOCK_EVENT, 2, 9), (BLOCK_EVENT + 1, 0, 0),
        ]

    def test_a_non_list_result_is_refused(self) -> None:
        with pytest.raises(UniswapV2IngestionError, match="must be a list"):
            decode_pair_created(
                {"jsonrpc": "2.0", "id": 1, "result": {"unexpected": True}},
                {},
                factory=UNISWAP_V2_FACTORY,
                log_raw_object_id="raw_" + "a" * 64,
                availability_time=datetime(2026, 7, 25, tzinfo=UTC),
            )

    def test_a_non_object_log_entry_is_refused(self) -> None:
        with pytest.raises(UniswapV2IngestionError, match="log entry must be an object"):
            _decode(["not-an-object"])

    def test_an_empty_result_decodes_to_no_rows(self) -> None:
        assert _decode([]) == []


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------

class TestResume:
    def test_a_completed_chunk_is_skipped_after_its_dependencies_verify(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node(), emit_rows=False)
        resumed = scenario_node()

        rows = run_fetch(store, resumed, emit_rows=False)

        assert rows == []
        assert "eth_getLogs" not in resumed.methods(), "a completed chunk must not re-fetch logs"
        assert len(store.receipts()) == 2, "resume must not duplicate receipts"

    def test_a_row_emitting_resume_refuses_to_return_partial_coverage(
        self, store: Store
    ) -> None:
        """Silently returning [] for a completed range is indistinguishable from
        'this range has no events', which would publish an empty dataset."""
        run_fetch(store, scenario_node(), emit_rows=False)

        with pytest.raises(UniswapV2IngestionError, match="already complete"):
            run_fetch(store, scenario_node(), emit_rows=True)

    def test_the_refusal_names_replay_as_the_supported_path(self, store: Store) -> None:
        run_fetch(store, scenario_node(), emit_rows=False)

        with pytest.raises(UniswapV2IngestionError, match="replay_receipts"):
            run_fetch(store, scenario_node(), emit_rows=True)

    def test_resume_reverifies_the_live_end_block_hash(self, store: Store) -> None:
        run_fetch(store, scenario_node(), emit_rows=False)
        resumed = scenario_node()
        run_fetch(store, resumed, emit_rows=False)

        header_blocks = [
            int(params[0], 16) for method, params in resumed.calls
            if method == "eth_getBlockByNumber"
        ]
        assert sorted(header_blocks) == [BLOCK_CHUNK1_END, BLOCK_CHUNK2_END]

    def test_a_reorged_chunk_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        reorged = scenario_node(
            block_hashes={**SCENARIO_BLOCK_HASHES, BLOCK_CHUNK1_END: _hash32(0xBAD)}
        )

        with pytest.raises(UniswapV2IngestionError, match="end-block validation"):
            run_fetch(store, reorged)

    def test_a_missing_dependency_blocks_the_skip(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.raw_path(store.receipt(SCENARIO_START)["logs_raw_object_id"]).unlink()

        with pytest.raises(UniswapV2IngestionError, match="cannot replay raw object"):
            run_fetch(store, scenario_node())

    def test_a_tampered_dependency_blocks_the_skip(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        logs_id = store.receipt(SCENARIO_START)["logs_raw_object_id"]
        store.overwrite_raw(logs_id, json.dumps({"jsonrpc": "2.0", "result": []}).encode())

        with pytest.raises(UniswapV2IngestionError, match="SHA-256 mismatch"):
            run_fetch(store, scenario_node())

    def test_a_tampered_header_dependency_blocks_the_skip(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        dependencies = json.loads(store.receipt(SCENARIO_START)["header_dependencies_json"])
        store.raw_path(dependencies[0]["raw_object_id"]).unlink()

        with pytest.raises(UniswapV2IngestionError, match="cannot replay raw object"):
            run_fetch(store, scenario_node())

    def test_a_receipt_bound_to_a_different_request_blocks_the_skip(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(
            SCENARIO_START,
            logs_request_json=_canonical_json(
                logs_request(factory=UNISWAP_V2_FACTORY, start_block=0, end_block=1)
            ),
        )

        with pytest.raises(UniswapV2IngestionError, match="does not match the requested chunk"):
            run_fetch(store, scenario_node())

    def test_a_receipt_whose_end_header_answers_another_block_blocks_the_skip(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(
            SCENARIO_START,
            end_header_request_json=_canonical_json(block_header_request(BLOCK_CHUNK2_END)),
        )

        with pytest.raises(UniswapV2IngestionError, match="different request"):
            run_fetch(store, scenario_node())

    def test_a_receipt_for_a_different_factory_is_not_reused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.clone_receipt_for_factory(SCENARIO_START, _addr(0xDEAD))
        store.delete_receipts_for_factory(UNISWAP_V2_FACTORY)

        node = scenario_node()
        rows = run_fetch(store, node)

        assert len(rows) == len(SCENARIO_LOGS), "the foreign receipt must not satisfy this chunk"
        assert "eth_getLogs" in node.methods()

    def test_resuming_a_partial_range_fills_only_the_missing_chunk(self, store: Store) -> None:
        run_fetch(store, scenario_node(), end_block=BLOCK_CHUNK1_END, emit_rows=False)
        assert [(r["start_block"], r["end_block"]) for r in store.receipts()] == [
            SCENARIO_RANGES[0]
        ]

        second = scenario_node()
        run_fetch(store, second, emit_rows=False)

        assert [(r["start_block"], r["end_block"]) for r in store.receipts()] == SCENARIO_RANGES
        logs_calls = [params for method, params in second.calls if method == "eth_getLogs"]
        assert len(logs_calls) == 1, "the completed chunk must not be re-fetched"
        assert int(logs_calls[0][0]["fromBlock"], 16) == BLOCK_CHUNK1_END + 1


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------

class TestReplay:
    def test_replay_never_contacts_the_node(self, store: Store) -> None:
        """run_replay builds an ingestor whose client raises on any request."""
        run_fetch(store, scenario_node())
        replay = run_replay(store)

        assert len(replay.rows) == len(SCENARIO_LOGS)

    def test_replay_reproduces_the_fetched_rows_exactly(self, store: Store) -> None:
        fetched = run_fetch(store, scenario_node())
        replayed = run_replay(store).rows

        assert [row.as_dict() for row in replayed] == [row.as_dict() for row in fetched]

    def test_replay_is_stable_across_repeated_invocations(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        first, second = run_replay(store), run_replay(store)

        assert [row.as_dict() for row in first.rows] == [row.as_dict() for row in second.rows]
        assert first.raw_object_ids == second.raw_object_ids
        assert first.acquisition_ids == second.acquisition_ids
        assert first.completed_ranges == second.completed_ranges

    def test_replay_reports_the_full_covered_span(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        assert run_replay(store).completed_ranges == tuple(SCENARIO_RANGES)

    def test_replay_declares_every_logs_and_header_dependency(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        receipts = store.receipts()
        replay = run_replay(store)

        assert replay.raw_object_ids == frozenset(declared_raw_object_ids(receipts))

        empty = store.receipt(BLOCK_CHUNK1_END + 1)
        assert str(empty["logs_raw_object_id"]) in replay.raw_object_ids
        assert str(empty["end_header_raw_object_id"]) in replay.raw_object_ids, (
            "an empty chunk still depends on its end-block header"
        )

    def test_replay_declares_every_acquisition(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        replay = run_replay(store)

        assert replay.acquisition_ids == frozenset(declared_acquisition_ids(store.receipts()))

    def test_replayed_rows_have_no_duplicate_transaction_and_log_index(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        identities = [(row.tx_hash.lower(), row.log_index) for row in run_replay(store).rows]

        assert len(identities) == len(set(identities)) == len(SCENARIO_LOGS)

    def test_a_hole_between_receipts_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(BLOCK_CHUNK1_END + 1, start_block=BLOCK_CHUNK1_END + 50)

        with pytest.raises(UniswapV2IngestionError, match="not contiguous"):
            run_replay(store)

    def test_a_range_that_stops_short_of_the_end_block_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node(), end_block=BLOCK_CHUNK1_END)

        with pytest.raises(UniswapV2IngestionError, match="block gap"):
            run_replay(store)

    def test_a_receipt_bound_to_another_range_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(
            SCENARIO_START,
            logs_request_json=_canonical_json(
                logs_request(factory=UNISWAP_V2_FACTORY, start_block=0, end_block=5)
            ),
        )

        with pytest.raises(UniswapV2IngestionError, match="does not match its own block range"):
            run_replay(store)

    def test_preserved_logs_from_another_range_are_refused(self, store: Store) -> None:
        """Request binding proves which request a receipt answers, not which bytes it
        points at. Replay must still bound decoded events to the receipt's range, or a
        repointed logs object silently widens coverage and duplicates events."""
        run_fetch(store, scenario_node())
        first = store.receipt(SCENARIO_START)
        second = store.receipt(BLOCK_CHUNK1_END + 1)
        assert second["logs_raw_object_id"] != first["logs_raw_object_id"]

        # Point the empty chunk at the first chunk's logs, and lend it the headers those
        # logs need, so decoding succeeds and the range bound is what rejects them.
        # Point the empty chunk at the first chunk's logs and lend it those headers, then
        # forge the acquisition row to match so the binding checks all pass. Only the
        # range bound can reject this.
        store.update_receipt(
            BLOCK_CHUNK1_END + 1,
            logs_raw_object_id=first["logs_raw_object_id"],
            logs_acquisition_id=second["logs_acquisition_id"],
            header_dependencies_json=first["header_dependencies_json"],
        )
        store.update_acquisition(
            second["logs_acquisition_id"], raw_object_id=first["logs_raw_object_id"]
        )

        with pytest.raises(UniswapV2IngestionError, match="outside receipt range"):
            run_replay(store)

    def test_an_end_header_hash_disagreeing_with_the_receipt_is_refused(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(SCENARIO_START, end_block_hash=_hash32(0xBAD))

        with pytest.raises(UniswapV2IngestionError, match="hash does not match the receipt"):
            run_replay(store)

    def test_a_header_dependency_bound_to_another_block_is_refused(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        dependencies = json.loads(store.receipt(SCENARIO_START)["header_dependencies_json"])
        dependencies[0]["request_json"] = _canonical_json(block_header_request(1))
        store.update_receipt(
            SCENARIO_START, header_dependencies_json=json.dumps(dependencies)
        )

        with pytest.raises(UniswapV2IngestionError, match="different request"):
            run_replay(store)

    def test_a_raw_object_that_is_no_longer_valid_json_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        logs_id = store.receipt(SCENARIO_START)["logs_raw_object_id"]
        body = store.raw_path(logs_id).read_bytes()
        # Keep the digest honest so the JSON decode is what fails.
        store.overwrite_raw(f"raw_{hashlib.sha256(body).hexdigest()}", body)
        store.overwrite_raw(logs_id, b"<html>gateway timeout</html>")

        with pytest.raises(UniswapV2IngestionError, match="SHA-256 mismatch|cannot replay"):
            run_replay(store)

    def test_a_missing_raw_object_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.raw_path(store.receipt(SCENARIO_START)["logs_raw_object_id"]).unlink()

        with pytest.raises(UniswapV2IngestionError, match="cannot replay raw object"):
            run_replay(store)

    def test_a_tampered_raw_object_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        logs_id = store.receipt(SCENARIO_START)["logs_raw_object_id"]
        store.overwrite_raw(logs_id, json.dumps({"jsonrpc": "2.0", "result": []}).encode())

        with pytest.raises(UniswapV2IngestionError, match="SHA-256 mismatch"):
            run_replay(store)

    def test_a_repointed_raw_object_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(SCENARIO_START, logs_raw_object_id="not_a_raw_object_id")

        with pytest.raises(UniswapV2IngestionError, match="but acquisition"):
            run_replay(store)

    def test_a_malformed_raw_object_id_is_refused(self, store: Store) -> None:
        """Direct cover for the id guard, which acquisition authentication now shadows."""
        with pytest.raises(UniswapV2IngestionError, match="invalid raw object id"):
            UniswapV2PairCreatedIngestor._read_raw_json(store.raw_root, "not_a_raw_object_id")

    def test_a_corrupt_dependency_list_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(SCENARIO_START, header_dependencies_json="{not json")

        with pytest.raises(UniswapV2IngestionError, match="not valid JSON"):
            run_replay(store)

    def test_a_dependency_list_that_is_not_an_array_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(SCENARIO_START, header_dependencies_json='{"a": 1}')

        with pytest.raises(UniswapV2IngestionError, match="must be a JSON array"):
            run_replay(store)

    def test_an_unparseable_acquisition_timestamp_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(SCENARIO_START, logs_acquired_at="not-a-timestamp")

        with pytest.raises(UniswapV2IngestionError, match="ISO-8601"):
            run_replay(store)

    def test_a_naive_acquisition_timestamp_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(SCENARIO_START, logs_acquired_at="2026-07-25T00:00:00")

        with pytest.raises(UniswapV2IngestionError, match="timezone-aware"):
            run_replay(store)

    def test_replay_requires_a_raw_root(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        ingestor = make_ingestor(store, raw_root=None)
        try:
            with pytest.raises(UniswapV2IngestionError, match="raw_root is required"):
                ingestor.replay_receipts(
                    start_block=SCENARIO_START, end_block=SCENARIO_END,
                    receipt_db_path=str(store.db),
                )
        finally:
            ingestor.close()


# ---------------------------------------------------------------------------
# Acquisition authentication
#
# A receipt is a claim. `raw_acquisition` is the independent record of what was
# actually retrieved. Replay must reconcile the two, or a receipt could name any
# acquisition id and nothing would notice.
# ---------------------------------------------------------------------------

class TestAcquisitionAuthentication:
    def test_every_receipt_acquisition_exists_and_succeeded(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        recorded = {row["acquisition_id"]: row for row in store.acquisitions()}

        for acquisition_id in declared_acquisition_ids(store.receipts()):
            assert acquisition_id in recorded, f"{acquisition_id} has no raw_acquisition row"
            assert recorded[acquisition_id]["status"] == "SUCCEEDED"

    def test_an_orphaned_acquisition_id_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(SCENARIO_START, logs_acquisition_id="acq_does_not_exist")

        with pytest.raises(UniswapV2IngestionError, match="no raw_acquisition row"):
            run_replay(store)

    def test_an_empty_acquisition_id_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(SCENARIO_START, logs_acquisition_id="")

        with pytest.raises(UniswapV2IngestionError, match="records no acquisition id"):
            run_replay(store)

    def test_a_deleted_acquisition_row_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.delete_acquisition(store.receipt(SCENARIO_START)["logs_acquisition_id"])

        with pytest.raises(UniswapV2IngestionError, match="no raw_acquisition row"):
            run_replay(store)

    @pytest.mark.parametrize(
        ("status", "raw_object_id"),
        [
            # raw_acquisition's own CHECK ties FAILED/REJECTED to a null raw object.
            ("FAILED", None),
            ("REJECTED", None),
            ("REGISTRATION_PENDING", "keep"),
        ],
    )
    def test_an_unsuccessful_acquisition_is_refused(
        self, store: Store, status: str, raw_object_id: str | None
    ) -> None:
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)
        columns: dict[str, Any] = {"status": status}
        if raw_object_id != "keep":
            columns["raw_object_id"] = raw_object_id
        store.update_acquisition(receipt["logs_acquisition_id"], **columns)

        with pytest.raises(UniswapV2IngestionError, match=f"status {status}"):
            run_replay(store)

    def test_an_acquisition_for_a_different_raw_object_is_refused(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)
        store.update_acquisition(
            receipt["logs_acquisition_id"],
            raw_object_id=receipt["end_header_raw_object_id"],
        )

        with pytest.raises(UniswapV2IngestionError, match="but acquisition"):
            run_replay(store)

    def test_an_acquisition_for_a_different_request_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)
        store.update_acquisition(
            receipt["logs_acquisition_id"],
            request_json=_canonical_json(block_header_request(1)),
        )

        with pytest.raises(UniswapV2IngestionError, match="different request than acquisition"):
            run_replay(store)

    def test_an_acquisition_recorded_at_another_time_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)
        store.update_acquisition(
            receipt["logs_acquisition_id"], acquired_at="2020-01-01T00:00:00+00:00"
        )

        with pytest.raises(UniswapV2IngestionError, match="claims acquisition time"):
            run_replay(store)

    def test_header_dependency_acquisitions_are_authenticated(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        dependencies = json.loads(store.receipt(SCENARIO_START)["header_dependencies_json"])
        store.delete_acquisition(dependencies[0]["acquisition_id"])

        with pytest.raises(UniswapV2IngestionError, match="no raw_acquisition row"):
            run_replay(store)

    def test_resume_also_authenticates_acquisitions(self, store: Store) -> None:
        run_fetch(store, scenario_node(), emit_rows=False)
        store.delete_acquisition(store.receipt(SCENARIO_START)["logs_acquisition_id"])

        with pytest.raises(UniswapV2IngestionError, match="no raw_acquisition row"):
            run_fetch(store, scenario_node(), emit_rows=False)


# ---------------------------------------------------------------------------
# Chain lineage
# ---------------------------------------------------------------------------

class TestChainLineage:
    def test_the_chain_identity_acquisition_is_recorded_on_every_receipt(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())

        for receipt in store.receipts():
            assert receipt["chain_id_request_json"] == _canonical_json(chain_id_request())
            assert receipt["chain_id_raw_object_id"].startswith("raw_")
            assert receipt["chain_id_acquisition_id"]
            assert datetime.fromisoformat(receipt["chain_id_acquired_at"]).tzinfo is not None

    def test_the_preserved_chain_response_is_the_exact_bytes(self, store: Store) -> None:
        node = scenario_node()
        run_fetch(store, node)
        raw_id = store.receipt(SCENARIO_START)["chain_id_raw_object_id"]

        body = store.raw_path(raw_id).read_bytes()
        assert body in set(node.served)
        assert json.loads(body)["result"] == ETHEREUM_MAINNET_CHAIN_ID

    def test_replay_surfaces_the_chain_acquisition_as_a_dependency(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)
        replay = run_replay(store)

        assert receipt["chain_id_raw_object_id"] in replay.raw_object_ids
        assert receipt["chain_id_acquisition_id"] in replay.acquisition_ids

    def test_replay_reverifies_the_chain_identity_offline(self, store: Store) -> None:
        """Replay must re-prove mainnet from preserved bytes, not trust that some
        earlier online run checked it."""
        run_fetch(store, scenario_node())
        forged = json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x5"}).encode()
        digest = hashlib.sha256(forged).hexdigest()
        # Republish the forged response at its own content address and point the receipt
        # and its acquisition at it, so only the chain-identity check can reject it.
        store.overwrite_raw(f"raw_{digest}", forged)
        store.update_receipt(SCENARIO_START, chain_id_raw_object_id=f"raw_{digest}")
        store.update_acquisition(
            store.receipt(SCENARIO_START)["chain_id_acquisition_id"],
            raw_object_id=f"raw_{digest}",
        )

        with pytest.raises(UniswapV2IngestionError, match="mainnet chain id"):
            run_replay(store)

    def test_a_receipt_without_chain_lineage_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(
            SCENARIO_START, chain_id_raw_object_id="", chain_id_acquisition_id=""
        )

        with pytest.raises(UniswapV2IngestionError, match="no eth_chainId lineage"):
            run_replay(store)

    def test_chain_lineage_bound_to_another_request_is_refused(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        store.update_receipt(
            SCENARIO_START,
            chain_id_request_json=_canonical_json(block_header_request(1)),
        )

        with pytest.raises(UniswapV2IngestionError, match="chain identity was acquired"):
            run_replay(store)

    def test_resume_also_reverifies_chain_lineage(self, store: Store) -> None:
        run_fetch(store, scenario_node(), emit_rows=False)
        store.update_receipt(SCENARIO_START, chain_id_acquisition_id="")

        with pytest.raises(UniswapV2IngestionError, match="no eth_chainId lineage"):
            run_fetch(store, scenario_node(), emit_rows=False)


# ---------------------------------------------------------------------------
# Header dependency consistency
# ---------------------------------------------------------------------------

class TestHeaderDependencyConsistency:
    def _dependency(self, store: Store) -> dict[str, Any]:
        return json.loads(store.receipt(SCENARIO_START)["header_dependencies_json"])[0]

    def test_a_repeated_block_in_the_dependency_list_is_refused(
        self, store: Store
    ) -> None:
        run_fetch(store, scenario_node())
        dependency = self._dependency(store)
        store.update_receipt(
            SCENARIO_START,
            header_dependencies_json=json.dumps([dependency, dict(dependency)]),
        )

        with pytest.raises(UniswapV2IngestionError, match="duplicate header dependency"):
            run_replay(store)

    def test_conflicting_hashes_for_one_block_are_refused(self, store: Store) -> None:
        """Two different hashes for one height means two chains answered."""
        run_fetch(store, scenario_node())
        dependency = self._dependency(store)
        conflicting = dict(dependency, block_hash=_hash32(0xBAD))
        store.update_receipt(
            SCENARIO_START,
            header_dependencies_json=json.dumps([dependency, conflicting]),
        )

        with pytest.raises(UniswapV2IngestionError, match="conflicting header dependencies"):
            run_replay(store)

    def test_a_conflicting_dependency_also_blocks_a_resume(self, store: Store) -> None:
        run_fetch(store, scenario_node(), emit_rows=False)
        dependency = self._dependency(store)
        store.update_receipt(
            SCENARIO_START,
            header_dependencies_json=json.dumps(
                [dependency, dict(dependency, block_hash=_hash32(0xBAD))]
            ),
        )

        with pytest.raises(UniswapV2IngestionError, match="conflicting header dependencies"):
            run_fetch(store, scenario_node(), emit_rows=False)


# ---------------------------------------------------------------------------
# Availability semantics
# ---------------------------------------------------------------------------

class TestAvailabilityTime:
    def test_availability_is_the_logs_acquisition_time(self, store: Store) -> None:
        """Events became observable when the logs response was acquired, not when the
        later header fetches resolved their timestamps."""
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)
        logs_at = datetime.fromisoformat(receipt["logs_acquired_at"])

        chunk_rows = [r for r in run_replay(store).rows if r.block_number <= BLOCK_CHUNK1_END]

        assert chunk_rows
        for row in chunk_rows:
            assert row.availability_time == logs_at

    def test_availability_is_not_the_chunk_completion_time(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        receipt = store.receipt(SCENARIO_START)
        completed_at = datetime.fromisoformat(receipt["completed_at"])
        logs_at = datetime.fromisoformat(receipt["logs_acquired_at"])

        assert logs_at < completed_at, "headers are acquired after the logs response"
        for row in run_replay(store).rows:
            if row.block_number <= BLOCK_CHUNK1_END:
                assert row.availability_time != completed_at

    def test_fetch_and_replay_agree_on_availability(self, store: Store) -> None:
        fetched = run_fetch(store, scenario_node())
        replayed = run_replay(store).rows

        assert [r.availability_time for r in fetched] == [r.availability_time for r in replayed]

    def test_event_time_is_the_block_timestamp_in_utc(self, store: Store) -> None:
        run_fetch(store, scenario_node())

        for row in run_replay(store).rows:
            assert row.event_time == datetime.fromtimestamp(
                MockEthereumNode.timestamp(row.block_number), UTC
            )
            assert row.event_time.tzinfo is not None
            assert row.availability_time >= row.event_time


# ---------------------------------------------------------------------------
# Failure evidence
# ---------------------------------------------------------------------------

class TestFailureRecording:
    def test_a_transport_failure_is_recorded_and_typed(self, store: Store) -> None:
        node = scenario_node(transport_error_for={"eth_getLogs"})

        with pytest.raises(UniswapV2IngestionError, match="transport failure"):
            run_fetch(store, node)

        failures = store.failures()
        assert len(failures) == 1
        assert failures[0]["failure_kind"] == "transport"
        assert failures[0]["method"] == "eth_getLogs"
        assert failures[0]["raw_object_id"] is None, "no bytes were received"
        assert failures[0]["start_block"] == SCENARIO_START
        assert failures[0]["end_block"] == BLOCK_CHUNK1_END
        assert datetime.fromisoformat(failures[0]["occurred_at"]).tzinfo is not None

    def test_an_http_failure_preserves_the_bytes_and_records_the_attempt(
        self, store: Store
    ) -> None:
        node = scenario_node(fail_status_for={"eth_getLogs"})

        with pytest.raises(UniswapV2IngestionError, match="HTTP 500"):
            run_fetch(store, node)

        failures = store.failures()
        assert len(failures) == 1
        assert failures[0]["failure_kind"] == "http_status"
        assert failures[0]["status_code"] == 500
        raw_object_id = failures[0]["raw_object_id"]
        assert raw_object_id is not None
        assert store.raw_path(raw_object_id).read_bytes() in set(node.served), (
            "the failing response body must still be preserved"
        )

    def test_an_invalid_json_body_is_recorded(self, store: Store) -> None:
        node = scenario_node(invalid_json_for={"eth_getLogs"})

        with pytest.raises(UniswapV2IngestionError, match="invalid JSON"):
            run_fetch(store, node)

        failures = store.failures()
        assert [f["failure_kind"] for f in failures] == ["invalid_json"]
        assert failures[0]["raw_object_id"] is not None

    def test_a_json_rpc_error_body_is_recorded(self, store: Store) -> None:
        node = scenario_node(rpc_error_for={"eth_getLogs"})

        with pytest.raises(UniswapV2IngestionError, match="failed"):
            run_fetch(store, node)

        failures = store.failures()
        assert [f["failure_kind"] for f in failures] == ["rpc_error"]

    def test_the_recorded_request_identifies_what_was_attempted(self, store: Store) -> None:
        node = scenario_node(fail_status_for={"eth_getLogs"})
        with pytest.raises(UniswapV2IngestionError):
            run_fetch(store, node)

        assert store.failures()[0]["request_json"] == _canonical_json(
            logs_request(
                factory=UNISWAP_V2_FACTORY,
                start_block=SCENARIO_START,
                end_block=BLOCK_CHUNK1_END,
            )
        )

    def test_a_successful_run_records_no_failures(self, store: Store) -> None:
        run_fetch(store, scenario_node())
        assert store.failures() == []


# ---------------------------------------------------------------------------
# Configuration and publication (runner script)
# ---------------------------------------------------------------------------

class TestConfiguration:
    def test_an_empty_rpc_url_is_refused(self, store: Store) -> None:
        with pytest.raises(ValueError, match="rpc_url is required"):
            UniswapV2PairCreatedIngestor(rpc_url="", raw_writer=store.writer)

    def test_no_rpc_endpoint_is_committed_to_git(self) -> None:
        source = Path(uniswap_v2.__file__).read_text()
        runner = (
            Path(__file__).resolve().parents[2]
            / "scripts" / "research" / "ingest_uniswap_v2_pair_created.py"
        ).read_text()

        assert "ETHEREUM_RPC_URL" in runner, "the runner must read the endpoint from the env"
        for text in (source, runner):
            assert "http://" not in text
            assert "https://" not in text

    def test_the_runner_requires_the_endpoint_in_the_environment(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from scripts.research import ingest_uniswap_v2_pair_created as runner

        monkeypatch.delenv("ETHEREUM_RPC_URL", raising=False)
        monkeypatch.setattr(sys, "argv", [
            "ingest_uniswap_v2_pair_created.py",
            "--start-block", str(SCENARIO_START), "--end-block", str(SCENARIO_END),
            "--db-path", str(tmp_path / "exp.db"), "--code-commit", "test",
        ])

        with pytest.raises(RuntimeError, match="ETHEREUM_RPC_URL"):
            runner.main()


class TestRunnerPublication:
    def test_the_runner_acquires_replays_and_publishes_a_resolvable_dataset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scripts.research import ingest_uniswap_v2_pair_created as runner

        db = tmp_path / "exp.db"
        store_root = tmp_path / "store"
        raw_root = store_root / "raw"
        node = scenario_node()
        node.install(monkeypatch)
        monkeypatch.setenv("ETHEREUM_RPC_URL", "http://node.invalid")
        monkeypatch.setattr(sys, "argv", [
            "ingest_uniswap_v2_pair_created.py",
            "--start-block", str(SCENARIO_START),
            "--end-block", str(SCENARIO_END),
            "--chunk-size", str(SCENARIO_CHUNK),
            "--db-path", str(db),
            "--raw-root", str(raw_root),
            "--store-root", str(store_root),
            "--code-commit", "0" * 40,
        ])

        assert runner.main() == 0

        conn = sqlite3.connect(db)
        try:
            conn.row_factory = sqlite3.Row
            receipts = [dict(r) for r in conn.execute(
                f"SELECT * FROM {RECEIPT_TABLE} ORDER BY start_block"
            )]
        finally:
            conn.close()
        assert [(r["start_block"], r["end_block"]) for r in receipts] == SCENARIO_RANGES

        catalog = SqliteDatasetCatalog(db)
        try:
            dataset_id = catalog.resolve_latest_by_type("uniswap_v2_pair_created")
            assert dataset_id is not None, "the published dataset must resolve by type"

            declared = {str(row["raw_object_id"]) for row in catalog.list_raw_inputs(dataset_id)}
            assert declared == declared_raw_object_ids(receipts), (
                "every preserved response must be declared as a raw dependency"
            )

            files = catalog.list_files(dataset_id)
            assert len(files) == 1
            assert files[0]["row_count"] == len(SCENARIO_LOGS)
        finally:
            catalog.close()

        published = list(store_root.rglob("events.parquet"))
        assert len(published) == 1, "exactly one published events.parquet"
        table = pq.read_table(published[0])
        assert REQUIRED_ROW_FIELDS <= set(table.column_names)

        records = table.to_pylist()
        assert [
            (r["block_number"], r["tx_index"], r["log_index"]) for r in records
        ] == SCENARIO_EXPECTED_ORDER
        assert {r["chain"] for r in records} == {ETHEREUM_CHAIN}
        assert {r["factory"] for r in records} == {UNISWAP_V2_FACTORY}
        assert [r["pair"] for r in records] == [PAIR_1, PAIR_2, PAIR_3]
        assert {r["raw_object_id"] for r in records} <= declared
