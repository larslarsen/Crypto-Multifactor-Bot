"""DATA-012 — tests for Uniswap V2 Factory PairCreated raw-event ingestion.

Every test exercises the finished implementation:
``src/cryptofactors/acquisition/uniswap_v2.py`` and its runner
``scripts/research/ingest_uniswap_v2_pair_created.py``. Nothing here re-implements
production logic; the publication test drives the runner itself.

Coverage maps to the DATA-012 acceptance criteria and the REVIEW-0230 corrections:

* no block gaps across resumable chunks              -> `TestFetch`, `TestReplayCoverage`
* exact JSON-RPC response bytes preserved            -> `TestRawPreservation`
* all required source fields present                 -> `TestDecoder`
* deterministic replay                               -> `TestReplayDeterminism`
* no duplicate ``(tx_hash, log_index)``              -> `TestDecoder`, `TestReplayCoverage`
* RPC URL from environment, never Git                -> `TestConfiguration`
* REVIEW-0230 (1) complete ``raw_object_ids``        -> `TestReplayCoverage`
* REVIEW-0230 (2) receipt DB closed in ``finally``   -> `TestFetch`
* REVIEW-0230 (3) invalid raw JSON is a typed error  -> `TestRawPreservation`
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
    PAIR_CREATED_TOPIC,
    UNISWAP_V2_FACTORY,
    PairCreatedRow,
    UniswapV2IngestionError,
    UniswapV2PairCreatedIngestor,
    _address,
    _hex_int,
    decode_pair_created,
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

TIMESTAMP_BASE = 1_700_000_000


# ---------------------------------------------------------------------------
# ABI / JSON-RPC fixtures
# ---------------------------------------------------------------------------

def _addr(n: int) -> str:
    """A 20-byte address as lowercase hex."""
    return "0x" + f"{n:040x}"


def _hash32(n: int) -> str:
    """A 32-byte hash as lowercase hex."""
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
) -> dict[str, Any]:
    """A `PairCreated(address,address,address,uint256)` log as eth_getLogs returns it.

    `token0`/`token1` are indexed (topics); `pair` and the pair count are ABI-encoded
    into `data`, so `data`'s first word is the left-padded pair address.
    """
    return {
        "address": UNISWAP_V2_FACTORY,
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
    """Deterministic JSON-RPC node serving `eth_getLogs` and `eth_getBlockByNumber`.

    Records the exact bytes of every response so tests can assert byte-for-byte
    preservation in the raw store, and records every call so tests can assert which
    requests the ingestor did (and did not) make.
    """

    def __init__(
        self,
        *,
        block_hashes: dict[int, str],
        logs: list[dict[str, Any]] | None = None,
        fail_status_for: set[str] | None = None,
        rpc_error_for: set[str] | None = None,
        honour_block_range: bool = True,
        invalid_json_for: set[str] | None = None,
        omit_header_fields: set[str] | None = None,
    ) -> None:
        self.block_hashes = block_hashes
        self.logs = logs or []
        self.fail_status_for = fail_status_for or set()
        self.rpc_error_for = rpc_error_for or set()
        self.honour_block_range = honour_block_range
        self.invalid_json_for = invalid_json_for or set()
        self.omit_header_fields = omit_header_fields or set()
        self.calls: list[tuple[str, Any]] = []
        self.served: list[bytes] = []

    @staticmethod
    def timestamp(block_number: int) -> int:
        return TIMESTAMP_BASE + block_number

    def _respond(self, status: int, payload: dict[str, Any]) -> httpx.Response:
        body = json.dumps(payload).encode()
        self.served.append(body)
        return httpx.Response(status, content=body, headers={"content-type": "application/json"})

    def _error(self, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": message}}

    def handler(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.read())
        method = payload["method"]
        params = payload["params"]
        self.calls.append((method, params))

        if method in self.fail_status_for:
            return self._respond(500, self._error("upstream failure"))
        if method in self.rpc_error_for:
            return self._respond(200, self._error("rejected by node"))
        if method in self.invalid_json_for:
            body = b"<html><body>502 Bad Gateway</body></html>"
            self.served.append(body)
            return httpx.Response(200, content=body, headers={"content-type": "text/html"})

        if method == "eth_getBlockByNumber":
            number = int(params[0], 16)
            if number not in self.block_hashes:
                return self._respond(200, self._error(f"unknown block {number}"))
            header = {
                "number": hex(number),
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
                or from_block <= int(log["blockNumber"], 16) <= to_block
            ]
            return self._respond(200, {"jsonrpc": "2.0", "id": 1, "result": selected})

        return self._respond(200, self._error(f"unsupported method {method}"))

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Make `httpx.Client()` constructed inside the ingestor talk to this node.

        Needed for the runner script, which owns its client.
        """
        real_client = httpx.Client
        monkeypatch.setattr(
            uniswap_v2.httpx,
            "Client",
            lambda **_kwargs: real_client(transport=httpx.MockTransport(self.handler)),
        )


# ---------------------------------------------------------------------------
# Store / receipt helpers
# ---------------------------------------------------------------------------

class Store:
    """Raw object store plus the control database holding the chunk receipts."""

    def __init__(self, tmp_path: Path) -> None:
        self.raw_root = tmp_path / "store" / "raw"
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.store_root = tmp_path / "store"
        self.db = tmp_path / "control.db"
        apply_migrations(self.db, migrations_dir=MIGRATIONS_DIR)
        self.catalog = SqliteRawObjectCatalog(self.db)
        self.writer = RawObjectWriter(RawObjectStoreConfig(root=self.raw_root), self.catalog)

    def close(self) -> None:
        self.catalog.close()

    def receipts(self) -> list[dict[str, Any]]:
        conn = sqlite3.connect(self.db)
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM uniswap_v2_pair_created_chunk_receipt_v2 ORDER BY start_block"
            ).fetchall()
        finally:
            conn.close()
        return [dict(row) for row in rows]

    def insert_receipt(
        self,
        *,
        start_block: int,
        end_block: int,
        end_block_hash: str,
        logs_raw_object_id: str,
        header_raw_object_ids: list[str],
        completed_at: str = "2026-07-25T00:00:00+00:00",
        chain: str = ETHEREUM_CHAIN,
        factory: str = UNISWAP_V2_FACTORY,
        topic: str = PAIR_CREATED_TOPIC,
        header_raw_object_ids_json: str | None = None,
    ) -> None:
        payload = (
            json.dumps(header_raw_object_ids)
            if header_raw_object_ids_json is None
            else header_raw_object_ids_json
        )
        conn = sqlite3.connect(self.db)
        try:
            conn.execute(
                "INSERT INTO uniswap_v2_pair_created_chunk_receipt_v2 "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (chain, factory, topic, start_block, end_block, end_block_hash,
                 logs_raw_object_id, payload, completed_at),
            )
            conn.commit()
        finally:
            conn.close()

    def raw_path(self, raw_object_id: str) -> Path:
        return content_addressed_absolute_path(self.raw_root, raw_object_id.removeprefix("raw_"))

    def write_raw(self, payload: dict[str, Any]) -> str:
        """Place exact bytes at their content address, returning the raw object id."""
        body = json.dumps(payload).encode()
        digest = hashlib.sha256(body).hexdigest()
        path = content_addressed_absolute_path(self.raw_root, digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return f"raw_{digest}"

    def overwrite_raw(self, raw_object_id: str, body: bytes) -> None:
        """Corrupt a preserved object in place, keeping its (now wrong) id."""
        path = self.raw_path(raw_object_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[Store]:
    created = Store(tmp_path)
    yield created
    created.close()


def declared_raw_object_ids(receipts: list[dict[str, Any]]) -> set[str]:
    """Every raw object a receipt says it depends on: the logs response and all headers."""
    declared: set[str] = set()
    for receipt in receipts:
        declared.add(str(receipt["logs_raw_object_id"]))
        declared.update(str(rid) for rid in json.loads(receipt["header_raw_object_ids_json"]))
    return declared


# ---------------------------------------------------------------------------
# A two-chunk scenario: logs in the first chunk, an empty second chunk.
# The empty chunk is what makes the end-block header a mandatory dependency.
# ---------------------------------------------------------------------------

TOKEN_A, TOKEN_B, TOKEN_C = _addr(0xA1), _addr(0xB2), _addr(0xC3)
PAIR_1, PAIR_2, PAIR_3 = _addr(0x11), _addr(0x22), _addr(0x33)
BLOCK_150_HASH, BLOCK_199_HASH, BLOCK_299_HASH = _hash32(150), _hash32(199), _hash32(299)

SCENARIO_BLOCK_HASHES = {150: BLOCK_150_HASH, 199: BLOCK_199_HASH, 299: BLOCK_299_HASH}

# Deliberately served out of order so ordering is proven, not inherited from the node.
SCENARIO_LOGS = [
    pair_created_log(
        block_number=199, block_hash=BLOCK_199_HASH, tx_hash=_hash32(0xF3),
        tx_index=1, log_index=4, token0=TOKEN_A, token1=TOKEN_C, pair=PAIR_3,
    ),
    pair_created_log(
        block_number=150, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF2),
        tx_index=3, log_index=7, token0=TOKEN_B, token1=TOKEN_C, pair=PAIR_2,
    ),
    pair_created_log(
        block_number=150, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF1),
        tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
    ),
]

SCENARIO_START, SCENARIO_END, SCENARIO_CHUNK = 100, 299, 100
SCENARIO_EXPECTED_ORDER = [(150, 0, 0), (150, 3, 7), (199, 1, 4)]


def scenario_node(**overrides: Any) -> MockEthereumNode:
    kwargs: dict[str, Any] = {
        "block_hashes": dict(SCENARIO_BLOCK_HASHES),
        "logs": list(SCENARIO_LOGS),
    }
    kwargs.update(overrides)
    return MockEthereumNode(**kwargs)


def run_scenario_fetch(store: Store, node: MockEthereumNode, **kwargs: Any) -> list[PairCreatedRow]:
    ingestor = UniswapV2PairCreatedIngestor(
        rpc_url="http://node.invalid", raw_writer=store.writer, client=node.client()
    )
    try:
        return ingestor.fetch(
            start_block=SCENARIO_START,
            end_block=SCENARIO_END,
            chunk_size=SCENARIO_CHUNK,
            receipt_db_path=str(store.db),
            **kwargs,
        )
    finally:
        ingestor.close()


def scenario_replay(store: Store) -> Any:
    ingestor = UniswapV2PairCreatedIngestor(rpc_url="http://node.invalid", raw_writer=store.writer)
    try:
        return ingestor.replay_receipts(
            start_block=SCENARIO_START,
            end_block=SCENARIO_END,
            receipt_db_path=str(store.db),
            raw_root=store.raw_root,
        )
    finally:
        ingestor.close()


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------

class TestMigrations:
    def test_uniswap_migrations_apply_on_a_fresh_database(self, tmp_path: Path) -> None:
        db = tmp_path / "control.db"
        apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
        applied = get_status(db, migrations_dir=MIGRATIONS_DIR)["applied"]
        for version in ("0009", "0010", "0011"):
            assert any(version in name for name in applied), f"migration {version} not applied"

    def test_receipt_table_is_keyed_by_full_ingestion_identity(self, tmp_path: Path) -> None:
        """Chunk identity must include chain/factory/topic, not just the block range."""
        db = tmp_path / "control.db"
        apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
        conn = sqlite3.connect(db)
        try:
            columns = conn.execute(
                "PRAGMA table_info(uniswap_v2_pair_created_chunk_receipt_v2)"
            ).fetchall()
        finally:
            conn.close()

        assert columns, "uniswap_v2_pair_created_chunk_receipt_v2 is missing"
        names = {row[1] for row in columns}
        assert {
            "chain", "factory", "topic", "start_block", "end_block", "end_block_hash",
            "logs_raw_object_id", "header_raw_object_ids_json", "completed_at",
        } <= names
        primary_key = [row[1] for row in sorted(columns, key=lambda row: row[5]) if row[5]]
        assert primary_key == ["chain", "factory", "topic", "start_block", "end_block"]

    def test_receipt_identity_allows_the_same_range_for_a_different_factory(
        self, store: Store
    ) -> None:
        other_factory = _addr(0xDEAD)
        store.insert_receipt(
            start_block=100, end_block=199, end_block_hash=BLOCK_199_HASH,
            logs_raw_object_id="raw_" + "0" * 64, header_raw_object_ids=[],
        )
        store.insert_receipt(
            start_block=100, end_block=199, end_block_hash=BLOCK_199_HASH,
            logs_raw_object_id="raw_" + "1" * 64, header_raw_object_ids=[],
            factory=other_factory,
        )
        factories = {receipt["factory"] for receipt in store.receipts()}
        assert factories == {UNISWAP_V2_FACTORY, other_factory}


# ---------------------------------------------------------------------------
# Acquisition
# ---------------------------------------------------------------------------

class TestFetch:
    def test_chunks_cover_the_requested_range_without_gaps_or_overlap(
        self, store: Store
    ) -> None:
        run_scenario_fetch(store, scenario_node())
        ranges = [(r["start_block"], r["end_block"]) for r in store.receipts()]

        assert ranges == [(100, 199), (200, 299)]
        assert ranges[0][0] == SCENARIO_START
        assert ranges[-1][1] == SCENARIO_END
        for previous, following in pairwise(ranges):
            assert following[0] == previous[1] + 1, "receipt ranges must be contiguous"

    def test_rows_are_ordered_by_block_transaction_and_log_index(self, store: Store) -> None:
        rows = run_scenario_fetch(store, scenario_node())
        assert [(r.block_number, r.tx_index, r.log_index) for r in rows] == SCENARIO_EXPECTED_ORDER

    def test_an_empty_chunk_still_produces_a_receipt(self, store: Store) -> None:
        run_scenario_fetch(store, scenario_node())
        empty = [r for r in store.receipts() if r["start_block"] == 200]

        assert len(empty) == 1
        assert empty[0]["end_block_hash"] == BLOCK_299_HASH
        header_ids = json.loads(empty[0]["header_raw_object_ids_json"])
        assert len(header_ids) == 1, "an empty chunk still depends on its end-block header"

    def test_emit_rows_false_still_writes_receipts(self, store: Store) -> None:
        """The runner acquires with emit_rows=False and decodes from receipts only."""
        rows = run_scenario_fetch(store, scenario_node(), emit_rows=False)

        assert rows == []
        assert len(store.receipts()) == 2

    def test_rejects_a_log_outside_the_requested_chunk(self, store: Store) -> None:
        """A node that ignores fromBlock/toBlock must not silently widen coverage."""
        stray = pair_created_log(
            block_number=1_000_000, block_hash=_hash32(1_000_000), tx_hash=_hash32(0xEE),
            tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
        )
        node = scenario_node(logs=[stray], honour_block_range=False)

        with pytest.raises(UniswapV2IngestionError, match="outside requested chunk"):
            run_scenario_fetch(store, node)

    @pytest.mark.parametrize(
        ("start_block", "end_block", "chunk_size"),
        [(-1, 100, 10), (200, 100, 10), (100, 200, 0), (100, 200, -5)],
    )
    def test_rejects_an_invalid_range_or_chunk_size(
        self, store: Store, start_block: int, end_block: int, chunk_size: int
    ) -> None:
        ingestor = UniswapV2PairCreatedIngestor(
            rpc_url="http://node.invalid", raw_writer=store.writer, client=scenario_node().client()
        )
        try:
            with pytest.raises(ValueError):
                ingestor.fetch(
                    start_block=start_block, end_block=end_block, chunk_size=chunk_size,
                    receipt_db_path=str(store.db),
                )
        finally:
            ingestor.close()

    def test_http_failure_raises_a_typed_error(self, store: Store) -> None:
        node = scenario_node(fail_status_for={"eth_getLogs"})
        with pytest.raises(UniswapV2IngestionError, match="HTTP 500"):
            run_scenario_fetch(store, node)

    def test_json_rpc_error_body_raises_a_typed_error(self, store: Store) -> None:
        node = scenario_node(rpc_error_for={"eth_getLogs"})
        with pytest.raises(UniswapV2IngestionError, match="failed"):
            run_scenario_fetch(store, node)

    def test_receipt_database_is_closed_when_acquisition_fails(
        self, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """REVIEW-0230 (2): the receipt connection is released even on the error path."""
        opened: list[sqlite3.Connection] = []
        real_connect = sqlite3.connect

        def tracking_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
            conn = real_connect(*args, **kwargs)
            opened.append(conn)
            return conn

        monkeypatch.setattr(uniswap_v2.sqlite3, "connect", tracking_connect)

        with pytest.raises(UniswapV2IngestionError):
            run_scenario_fetch(store, scenario_node(fail_status_for={"eth_getLogs"}))

        assert opened, "fetch did not open the receipt database"
        for conn in opened:
            with pytest.raises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")


class TestResume:
    def test_a_completed_chunk_is_skipped_after_its_end_block_hash_is_reverified(
        self, store: Store
    ) -> None:
        store.insert_receipt(
            start_block=SCENARIO_START, end_block=SCENARIO_END, end_block_hash=BLOCK_299_HASH,
            logs_raw_object_id="raw_" + "0" * 64, header_raw_object_ids=[],
        )
        node = scenario_node()

        ingestor = UniswapV2PairCreatedIngestor(
            rpc_url="http://node.invalid", raw_writer=store.writer, client=node.client()
        )
        try:
            rows = ingestor.fetch(
                start_block=SCENARIO_START, end_block=SCENARIO_END, chunk_size=1_000,
                receipt_db_path=str(store.db),
            )
        finally:
            ingestor.close()

        assert rows == []
        assert [method for method, _ in node.calls] == ["eth_getBlockByNumber"], (
            "a completed chunk must cost exactly one end-block verification"
        )
        assert len(store.receipts()) == 1, "resume must not duplicate the receipt"

    def test_a_receipt_whose_end_block_hash_changed_is_rejected(self, store: Store) -> None:
        """A reorged chunk must fail loudly rather than be silently trusted."""
        store.insert_receipt(
            start_block=SCENARIO_START, end_block=SCENARIO_END, end_block_hash=_hash32(0xBAD),
            logs_raw_object_id="raw_" + "0" * 64, header_raw_object_ids=[],
        )
        ingestor = UniswapV2PairCreatedIngestor(
            rpc_url="http://node.invalid", raw_writer=store.writer, client=scenario_node().client()
        )
        try:
            with pytest.raises(UniswapV2IngestionError, match="end-block validation"):
                ingestor.fetch(
                    start_block=SCENARIO_START, end_block=SCENARIO_END, chunk_size=1_000,
                    receipt_db_path=str(store.db),
                )
        finally:
            ingestor.close()

    def test_a_receipt_for_a_different_factory_does_not_satisfy_this_chunk(
        self, store: Store
    ) -> None:
        store.insert_receipt(
            start_block=SCENARIO_START, end_block=SCENARIO_END, end_block_hash=BLOCK_299_HASH,
            logs_raw_object_id="raw_" + "0" * 64, header_raw_object_ids=[],
            factory=_addr(0xDEAD),
        )
        node = scenario_node()
        ingestor = UniswapV2PairCreatedIngestor(
            rpc_url="http://node.invalid", raw_writer=store.writer, client=node.client()
        )
        try:
            rows = ingestor.fetch(
                start_block=SCENARIO_START, end_block=SCENARIO_END, chunk_size=1_000,
                receipt_db_path=str(store.db),
            )
        finally:
            ingestor.close()

        assert len(rows) == len(SCENARIO_LOGS), "the foreign receipt must not be reused"
        assert "eth_getLogs" in [method for method, _ in node.calls]

    def test_resuming_a_partially_completed_range_fills_only_the_missing_chunk(
        self, store: Store
    ) -> None:
        first = scenario_node()
        ingestor = UniswapV2PairCreatedIngestor(
            rpc_url="http://node.invalid", raw_writer=store.writer, client=first.client()
        )
        try:
            ingestor.fetch(
                start_block=SCENARIO_START, end_block=199, chunk_size=SCENARIO_CHUNK,
                receipt_db_path=str(store.db),
            )
        finally:
            ingestor.close()
        assert [(r["start_block"], r["end_block"]) for r in store.receipts()] == [(100, 199)]

        second = scenario_node()
        run_scenario_fetch(store, second)

        assert [(r["start_block"], r["end_block"]) for r in store.receipts()] == [
            (100, 199), (200, 299),
        ]
        logs_calls = [params for method, params in second.calls if method == "eth_getLogs"]
        assert len(logs_calls) == 1, "the completed chunk must not be re-fetched"
        assert int(logs_calls[0][0]["fromBlock"], 16) == 200


# ---------------------------------------------------------------------------
# Raw preservation
# ---------------------------------------------------------------------------

class TestRawPreservation:
    def test_every_preserved_object_is_the_exact_response_body(self, store: Store) -> None:
        node = scenario_node()
        run_scenario_fetch(store, node)

        served = set(node.served)
        declared = declared_raw_object_ids(store.receipts())
        assert declared, "fetch recorded no raw objects"

        for raw_object_id in declared:
            body = store.raw_path(raw_object_id).read_bytes()
            assert body in served, f"{raw_object_id} is not a byte-for-byte response"
            assert f"raw_{hashlib.sha256(body).hexdigest()}" == raw_object_id

    def test_the_logs_and_header_responses_are_preserved_before_decoding(
        self, store: Store
    ) -> None:
        node = scenario_node()
        run_scenario_fetch(store, node)

        declared = declared_raw_object_ids(store.receipts())
        decoded = [json.loads(store.raw_path(rid).read_bytes()) for rid in declared]

        assert all("error" not in payload for payload in decoded)
        assert any(isinstance(payload["result"], list) for payload in decoded), "logs response"
        assert any(isinstance(payload["result"], dict) for payload in decoded), "header response"

    def test_a_failed_response_is_preserved_before_the_error_is_raised(
        self, store: Store
    ) -> None:
        node = scenario_node(fail_status_for={"eth_getLogs"})
        with pytest.raises(UniswapV2IngestionError):
            run_scenario_fetch(store, node)

        failure_body = node.served[0]
        digest = hashlib.sha256(failure_body).hexdigest()
        path = content_addressed_absolute_path(store.raw_root, digest)
        assert path.read_bytes() == failure_body, "the failing response must still be preserved"

    def test_replay_rejects_a_raw_object_that_is_no_longer_valid_json(
        self, store: Store
    ) -> None:
        """REVIEW-0230 (3): unreadable raw bytes surface as UniswapV2IngestionError."""
        run_scenario_fetch(store, scenario_node())
        logs_id = str(store.receipts()[0]["logs_raw_object_id"])
        store.overwrite_raw(logs_id, b"<html>gateway timeout</html>")

        with pytest.raises(UniswapV2IngestionError, match="cannot replay raw object"):
            scenario_replay(store)

    def test_replay_rejects_a_missing_raw_object(self, store: Store) -> None:
        run_scenario_fetch(store, scenario_node())
        logs_id = str(store.receipts()[0]["logs_raw_object_id"])
        store.raw_path(logs_id).unlink()

        with pytest.raises(UniswapV2IngestionError, match="cannot replay raw object"):
            scenario_replay(store)

    def test_replay_rejects_a_tampered_raw_object_that_is_still_valid_json(
        self, store: Store
    ) -> None:
        run_scenario_fetch(store, scenario_node())
        logs_id = str(store.receipts()[0]["logs_raw_object_id"])
        store.overwrite_raw(logs_id, json.dumps({"jsonrpc": "2.0", "result": []}).encode())

        with pytest.raises(UniswapV2IngestionError, match="SHA-256 mismatch"):
            scenario_replay(store)

    def test_replay_rejects_a_malformed_raw_object_id(self, store: Store) -> None:
        store.insert_receipt(
            start_block=SCENARIO_START, end_block=SCENARIO_END, end_block_hash=BLOCK_299_HASH,
            logs_raw_object_id="not_a_raw_object_id", header_raw_object_ids=[],
        )
        with pytest.raises(UniswapV2IngestionError, match="invalid raw object id"):
            scenario_replay(store)


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------

class TestReplayDeterminism:
    def test_replay_reproduces_the_fetched_rows_exactly(self, store: Store) -> None:
        fetched = run_scenario_fetch(store, scenario_node())
        replayed = scenario_replay(store).rows

        assert [row.as_dict() for row in replayed] == [row.as_dict() for row in fetched]

    def test_replay_is_stable_across_repeated_invocations(self, store: Store) -> None:
        run_scenario_fetch(store, scenario_node())
        first, second = scenario_replay(store), scenario_replay(store)

        assert [row.as_dict() for row in first.rows] == [row.as_dict() for row in second.rows]
        assert first.raw_object_ids == second.raw_object_ids
        assert first.completed_ranges == second.completed_ranges

    def test_replay_does_not_contact_the_node(self, store: Store) -> None:
        """Replay must decode preserved bytes only — no RPC URL is reachable here."""
        node = scenario_node()
        run_scenario_fetch(store, node)
        calls_after_fetch = len(node.calls)

        scenario_replay(store)

        assert len(node.calls) == calls_after_fetch


class TestReplayCoverage:
    def test_raw_object_ids_cover_every_logs_and_header_response(self, store: Store) -> None:
        """REVIEW-0230 (1): including empty chunks and end-block headers."""
        run_scenario_fetch(store, scenario_node())
        receipts = store.receipts()
        replay = scenario_replay(store)

        assert replay.raw_object_ids == frozenset(declared_raw_object_ids(receipts))

        empty_chunk = next(r for r in receipts if r["start_block"] == 200)
        empty_headers = json.loads(empty_chunk["header_raw_object_ids_json"])
        assert set(empty_headers) <= replay.raw_object_ids, "empty-chunk header dropped"
        assert str(empty_chunk["logs_raw_object_id"]) in replay.raw_object_ids

        non_empty = next(r for r in receipts if r["start_block"] == 100)
        headers = json.loads(non_empty["header_raw_object_ids_json"])
        assert len(headers) == 2, "block 150, block 199 (also the end block)"
        assert set(headers) <= replay.raw_object_ids

    def test_completed_ranges_report_the_full_covered_span(self, store: Store) -> None:
        run_scenario_fetch(store, scenario_node())
        replay = scenario_replay(store)

        assert replay.completed_ranges == ((100, 199), (200, 299))

    def test_replayed_rows_have_no_duplicate_transaction_and_log_index(
        self, store: Store
    ) -> None:
        run_scenario_fetch(store, scenario_node())
        rows = scenario_replay(store).rows
        identities = [(row.tx_hash, row.log_index) for row in rows]

        assert len(identities) == len(set(identities))
        assert len(identities) == len(SCENARIO_LOGS)

    def test_a_hole_between_receipts_is_rejected(self, store: Store) -> None:
        payload = {"jsonrpc": "2.0", "id": 1, "result": []}
        header = {
            "jsonrpc": "2.0", "id": 1,
            "result": {"number": hex(199), "hash": BLOCK_199_HASH, "timestamp": hex(1)},
        }
        logs_id, header_id = store.write_raw(payload), store.write_raw(header)
        store.insert_receipt(
            start_block=100, end_block=199, end_block_hash=BLOCK_199_HASH,
            logs_raw_object_id=logs_id, header_raw_object_ids=[header_id],
        )
        store.insert_receipt(
            start_block=250, end_block=299, end_block_hash=BLOCK_299_HASH,
            logs_raw_object_id=logs_id, header_raw_object_ids=[header_id],
        )

        with pytest.raises(UniswapV2IngestionError, match="not contiguous"):
            scenario_replay(store)

    def test_a_range_that_stops_short_of_the_end_block_is_rejected(self, store: Store) -> None:
        first = scenario_node()
        ingestor = UniswapV2PairCreatedIngestor(
            rpc_url="http://node.invalid", raw_writer=store.writer, client=first.client()
        )
        try:
            ingestor.fetch(
                start_block=SCENARIO_START, end_block=199, chunk_size=SCENARIO_CHUNK,
                receipt_db_path=str(store.db),
            )
        finally:
            ingestor.close()

        with pytest.raises(UniswapV2IngestionError, match="block gap"):
            scenario_replay(store)


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------

def _decode(logs: list[dict[str, Any]], headers: dict[int, tuple[dict[str, Any], str]]) -> Any:
    return decode_pair_created(
        {"jsonrpc": "2.0", "id": 1, "result": logs},
        headers,
        factory=UNISWAP_V2_FACTORY,
        log_raw_object_id="raw_" + "a" * 64,
        availability_time=datetime(2026, 7, 25, 12, 0, tzinfo=UTC),
    )


def _header(block_number: int, block_hash: str, timestamp: int) -> dict[str, Any]:
    return {"number": hex(block_number), "hash": block_hash, "timestamp": hex(timestamp)}


class TestDecoder:
    def test_every_required_source_field_is_populated(self) -> None:
        timestamp = 1_700_000_150
        log = pair_created_log(
            block_number=150, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF1),
            tx_index=3, log_index=7, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
        )
        headers = {150: (_header(150, BLOCK_150_HASH, timestamp), "raw_" + "b" * 64)}

        (row,) = _decode([log], headers)
        record = row.as_dict()

        assert REQUIRED_ROW_FIELDS <= set(record)
        assert record["chain"] == ETHEREUM_CHAIN
        assert record["factory"] == UNISWAP_V2_FACTORY
        assert record["pair"] == PAIR_1
        assert record["token0"] == TOKEN_A
        assert record["token1"] == TOKEN_B
        assert record["block_number"] == 150
        assert record["block_hash"] == BLOCK_150_HASH
        assert record["block_timestamp"] == timestamp
        assert record["tx_hash"] == _hash32(0xF1)
        assert record["tx_index"] == 3
        assert record["log_index"] == 7
        assert record["raw_object_id"] == "raw_" + "a" * 64
        assert record["block_raw_object_id"] == "raw_" + "b" * 64

    def test_event_time_is_the_block_timestamp_in_utc(self) -> None:
        timestamp = 1_700_000_150
        log = pair_created_log(
            block_number=150, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF1),
            tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
        )
        headers = {150: (_header(150, BLOCK_150_HASH, timestamp), "raw_" + "b" * 64)}

        (row,) = _decode([log], headers)

        assert row.event_time == datetime.fromtimestamp(timestamp, UTC)
        assert row.event_time.tzinfo is not None
        assert row.availability_time == datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
        assert row.availability_time >= row.event_time

    def test_rows_are_sorted_by_block_transaction_and_log_index(self) -> None:
        logs = [
            pair_created_log(
                block_number=151, block_hash=_hash32(151), tx_hash=_hash32(0xF9),
                tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
            ),
            pair_created_log(
                block_number=150, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF8),
                tx_index=2, log_index=9, token0=TOKEN_A, token1=TOKEN_C, pair=PAIR_2,
            ),
            pair_created_log(
                block_number=150, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF7),
                tx_index=2, log_index=1, token0=TOKEN_B, token1=TOKEN_C, pair=PAIR_3,
            ),
        ]
        headers = {
            150: (_header(150, BLOCK_150_HASH, 1), "raw_" + "b" * 64),
            151: (_header(151, _hash32(151), 2), "raw_" + "c" * 64),
        }

        rows = _decode(logs, headers)

        assert [(r.block_number, r.tx_index, r.log_index) for r in rows] == [
            (150, 2, 1), (150, 2, 9), (151, 0, 0),
        ]

    def test_duplicate_transaction_and_log_index_is_rejected(self) -> None:
        log = pair_created_log(
            block_number=150, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF1),
            tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
        )
        headers = {150: (_header(150, BLOCK_150_HASH, 1), "raw_" + "b" * 64)}

        with pytest.raises(UniswapV2IngestionError, match="duplicate"):
            _decode([log, dict(log)], headers)

    def test_a_log_whose_block_hash_contradicts_the_header_is_rejected(self) -> None:
        log = pair_created_log(
            block_number=150, block_hash=_hash32(0xBAD), tx_hash=_hash32(0xF1),
            tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
        )
        headers = {150: (_header(150, BLOCK_150_HASH, 1), "raw_" + "b" * 64)}

        with pytest.raises(UniswapV2IngestionError, match="block hash"):
            _decode([log], headers)

    def test_a_foreign_event_topic_is_rejected(self) -> None:
        log = pair_created_log(
            block_number=150, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF1),
            tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
        )
        log["topics"] = [_hash32(0x5117), *log["topics"][1:]]
        headers = {150: (_header(150, BLOCK_150_HASH, 1), "raw_" + "b" * 64)}

        with pytest.raises(UniswapV2IngestionError, match="topics"):
            _decode([log], headers)

    def test_a_truncated_topic_list_is_rejected(self) -> None:
        log = pair_created_log(
            block_number=150, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF1),
            tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
        )
        log["topics"] = log["topics"][:2]
        headers = {150: (_header(150, BLOCK_150_HASH, 1), "raw_" + "b" * 64)}

        with pytest.raises(UniswapV2IngestionError, match="topics"):
            _decode([log], headers)

    def test_a_non_list_result_is_rejected(self) -> None:
        with pytest.raises(UniswapV2IngestionError, match="must be a list"):
            decode_pair_created(
                {"jsonrpc": "2.0", "id": 1, "result": {"unexpected": True}},
                {},
                factory=UNISWAP_V2_FACTORY,
                log_raw_object_id="raw_" + "a" * 64,
                availability_time=datetime(2026, 7, 25, tzinfo=UTC),
            )

    def test_an_empty_result_decodes_to_no_rows(self) -> None:
        assert _decode([], {}) == []


class TestHexHelpers:
    def test_hex_quantities_decode(self) -> None:
        assert _hex_int("0x0") == 0
        assert _hex_int("0xff") == 255
        assert _hex_int(hex(20_000_000)) == 20_000_000

    def test_a_non_hex_quantity_is_rejected(self) -> None:
        with pytest.raises(UniswapV2IngestionError, match="expected hex quantity"):
            _hex_int("20000000")

    def test_a_numeric_json_quantity_is_rejected(self) -> None:
        """A node returning a JSON number instead of a hex string must not decode."""
        with pytest.raises(UniswapV2IngestionError, match="expected hex quantity"):
            _hex_int(20_000_000)  # type: ignore[arg-type]

    def test_an_abi_word_yields_its_low_20_bytes(self) -> None:
        address = _addr(0xABCDEF)
        assert _address(_abi_word(address)) == address

    def test_a_short_abi_word_is_rejected(self) -> None:
        with pytest.raises(UniswapV2IngestionError, match="32-byte ABI word"):
            _address("0x" + "ab" * 19)


# ---------------------------------------------------------------------------
# Typed failures
#
# Every malformed node response or corrupt receipt must surface as
# UniswapV2IngestionError. A bare KeyError / JSONDecodeError / ValueError escaping
# the ingestor is indistinguishable from a programming fault at the call site.
# ---------------------------------------------------------------------------

class TestTypedFailures:
    def test_a_non_json_body_on_a_200_response_is_typed(self, store: Store) -> None:
        node = scenario_node(invalid_json_for={"eth_getLogs"})
        with pytest.raises(UniswapV2IngestionError, match="invalid JSON"):
            run_scenario_fetch(store, node)

    def test_an_end_block_header_without_a_hash_is_typed(self, store: Store) -> None:
        node = scenario_node(logs=[], omit_header_fields={"hash"})
        with pytest.raises(UniswapV2IngestionError, match="end-block header is missing"):
            run_scenario_fetch(store, node)

    def test_a_non_object_log_entry_is_typed(self, store: Store) -> None:
        node = scenario_node(logs=["not-an-object"], honour_block_range=False)
        with pytest.raises(UniswapV2IngestionError, match="log entry must be an object"):
            run_scenario_fetch(store, node)

    @pytest.mark.parametrize(
        "field",
        ["blockNumber", "blockHash", "transactionHash", "logIndex", "transactionIndex", "data"],
    )
    def test_a_log_missing_a_required_field_is_typed(self, field: str) -> None:
        log = pair_created_log(
            block_number=150, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF1),
            tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
        )
        del log[field]
        headers = {150: (_header(150, BLOCK_150_HASH, 1), "raw_" + "b" * 64)}

        with pytest.raises(UniswapV2IngestionError, match=f"log is missing '{field}'"):
            _decode([log], headers)

    @pytest.mark.parametrize("field", ["hash", "timestamp"])
    def test_a_block_header_missing_a_required_field_is_typed(self, field: str) -> None:
        log = pair_created_log(
            block_number=150, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF1),
            tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
        )
        header = _header(150, BLOCK_150_HASH, 1)
        del header[field]

        with pytest.raises(UniswapV2IngestionError, match=f"block header is missing '{field}'"):
            _decode([log], {150: (header, "raw_" + "b" * 64)})

    def test_a_log_with_no_preserved_header_is_typed(self) -> None:
        """Previously a bare KeyError out of the block_headers lookup."""
        log = pair_created_log(
            block_number=999, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF1),
            tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
        )
        headers = {150: (_header(150, BLOCK_150_HASH, 1), "raw_" + "b" * 64)}

        with pytest.raises(UniswapV2IngestionError, match="no preserved block header for block 999"):
            _decode([log], headers)

    def test_a_non_string_event_topic_is_typed(self) -> None:
        log = pair_created_log(
            block_number=150, block_hash=BLOCK_150_HASH, tx_hash=_hash32(0xF1),
            tx_index=0, log_index=0, token0=TOKEN_A, token1=TOKEN_B, pair=PAIR_1,
        )
        log["topics"] = [None, *log["topics"][1:]]
        headers = {150: (_header(150, BLOCK_150_HASH, 1), "raw_" + "b" * 64)}

        with pytest.raises(UniswapV2IngestionError, match="topics"):
            _decode([log], headers)

    def test_a_receipt_with_a_corrupt_header_id_list_is_typed(self, store: Store) -> None:
        store.insert_receipt(
            start_block=SCENARIO_START, end_block=SCENARIO_END, end_block_hash=BLOCK_299_HASH,
            logs_raw_object_id="raw_" + "0" * 64, header_raw_object_ids=[],
            header_raw_object_ids_json="{not json",
        )
        with pytest.raises(UniswapV2IngestionError, match="not valid JSON"):
            scenario_replay(store)

    def test_a_receipt_whose_header_id_list_is_not_an_array_is_typed(self, store: Store) -> None:
        store.insert_receipt(
            start_block=SCENARIO_START, end_block=SCENARIO_END, end_block_hash=BLOCK_299_HASH,
            logs_raw_object_id="raw_" + "0" * 64, header_raw_object_ids=[],
            header_raw_object_ids_json='{"raw_a": 1}',
        )
        with pytest.raises(UniswapV2IngestionError, match="must be a JSON array"):
            scenario_replay(store)

    def test_a_receipt_with_an_unparseable_completed_at_is_typed(self, store: Store) -> None:
        logs_id = store.write_raw({"jsonrpc": "2.0", "id": 1, "result": []})
        header_id = store.write_raw({
            "jsonrpc": "2.0", "id": 1,
            "result": {"number": hex(299), "hash": BLOCK_299_HASH, "timestamp": hex(1)},
        })
        store.insert_receipt(
            start_block=SCENARIO_START, end_block=SCENARIO_END, end_block_hash=BLOCK_299_HASH,
            logs_raw_object_id=logs_id, header_raw_object_ids=[header_id],
            completed_at="not-a-timestamp",
        )
        with pytest.raises(UniswapV2IngestionError, match="ISO-8601"):
            scenario_replay(store)

    def test_a_preserved_header_without_a_block_number_is_typed(self, store: Store) -> None:
        logs_id = store.write_raw({"jsonrpc": "2.0", "id": 1, "result": []})
        header_id = store.write_raw({
            "jsonrpc": "2.0", "id": 1,
            "result": {"hash": BLOCK_299_HASH, "timestamp": hex(1)},
        })
        store.insert_receipt(
            start_block=SCENARIO_START, end_block=SCENARIO_END, end_block_hash=BLOCK_299_HASH,
            logs_raw_object_id=logs_id, header_raw_object_ids=[header_id],
        )
        with pytest.raises(UniswapV2IngestionError, match="block header is missing 'number'"):
            scenario_replay(store)


# ---------------------------------------------------------------------------
# Configuration and publication (runner script)
# ---------------------------------------------------------------------------

class TestConfiguration:
    def test_an_empty_rpc_url_is_rejected(self, store: Store) -> None:
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
            "--start-block", "100", "--end-block", "299",
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
        raw_root = tmp_path / "store" / "raw"
        store_root = tmp_path / "store"
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
                "SELECT * FROM uniswap_v2_pair_created_chunk_receipt_v2 ORDER BY start_block"
            )]
        finally:
            conn.close()
        assert [(r["start_block"], r["end_block"]) for r in receipts] == [(100, 199), (200, 299)]

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
        assert [(r["block_number"], r["tx_index"], r["log_index"]) for r in records] == (
            SCENARIO_EXPECTED_ORDER
        )
        assert {r["chain"] for r in records} == {ETHEREUM_CHAIN}
        assert {r["factory"] for r in records} == {UNISWAP_V2_FACTORY}
        assert [r["pair"] for r in records] == [PAIR_1, PAIR_2, PAIR_3]
        assert {r["raw_object_id"] for r in records} <= declared
