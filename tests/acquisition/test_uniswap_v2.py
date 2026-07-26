"""Tests for DATA-012 Uniswap V2 PairCreated ingestion."""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.acquisition.uniswap_v2 import (
    ETHEREUM_CHAIN,
    PAIR_CREATED_TOPIC,
    UNISWAP_V2_FACTORY,
    UniswapV2IngestionError,
    UniswapV2PairCreatedIngestor,
    _address,
    _hex_int,
    decode_pair_created,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetStatistics,
    DatasetStoreConfig,
    DependencyKind,
    DependencyRef,
    OutputFileSpec,
    PublishPlan,
    QualityStatus,
    RowCountPolicy,
    RowCountReceipt,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations, get_status
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.paths import content_addressed_absolute_path
from cryptofactors.ingest.raw.writer import RawObjectWriter


def _sample_log(
    block_number: int = 20_000_000,
    tx_index: int = 0,
    log_index: int = 0,
    tx_hash: str = "0xaa",
    pair: str = "0x00000000000000000000000000000000000000Aa",
    block_hash: str = "0xbb",
) -> dict[str, Any]:
    return {
        "address": pair,
        "blockHash": block_hash,
        "blockNumber": hex(block_number),
        "data": pair + "0" * 128,
        "logIndex": hex(log_index),
        "removed": False,
        "topics": [
            PAIR_CREATED_TOPIC,
            "0x0000000000000000000000000000000000000000000000000000000000000000",
            "0x0000000000000000000000000000000000000000000000000000000000000000",
        ],
        "transactionHash": tx_hash,
        "transactionIndex": hex(tx_index),
    }


def _patch_topics(log: dict[str, Any], token0: str, token1: str) -> dict[str, Any]:
    log = dict(log)
    topics = list(log["topics"])
    topics[1] = "0x" + "0" * 24 + token0[2:].lower().zfill(40)
    topics[2] = "0x" + "0" * 24 + token1[2:].lower().zfill(40)
    log["topics"] = topics
    return log


def _sample_block_header(block_number: int, block_hash: str = "0xbb", timestamp: int = 1700000000) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0", "id": 1,
        "result": {
            "number": hex(block_number), "hash": block_hash,
            "timestamp": hex(timestamp), "parentHash": "0x00", "miner": "0x00",
        },
    }


def _sample_logs_response(logs: list[dict[str, Any]]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": 1, "result": logs}


def _write_raw(raw_root: Path, data: dict[str, Any]) -> str:
    body = json.dumps(data).encode()
    digest = hashlib.sha256(body).hexdigest()
    path = content_addressed_absolute_path(raw_root, digest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return f"raw_{digest}"


def _setup_raw_store(tmp_path: Path):
    raw_root = tmp_path / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    config = RawObjectStoreConfig(root=raw_root)
    db = tmp_path / "store.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    catalog = SqliteRawObjectCatalog(db)
    writer = RawObjectWriter(config, catalog)
    return raw_root, db, catalog, writer


# ---------------------------------------------------------------------------
# 1. Migration tests
# ---------------------------------------------------------------------------

def test_migrations_0009_through_0011_apply_fresh(tmp_path: Path) -> None:
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    status = get_status(db, migrations_dir=MIGRATIONS_DIR)
    applied = status["applied"]
    for v in ("0009", "0010", "0011"):
        assert any(v in fname for fname in applied), f"migration {v} not applied"

    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "uniswap_v2_pair_created_chunk_receipt_v2" in tables
    conn.close()


# ---------------------------------------------------------------------------
# 2. Multi-chunk acquisition with an empty chunk
# ---------------------------------------------------------------------------

def test_multi_chunk_acquisition_with_empty_chunk(tmp_path: Path) -> None:
    _raw_root, db, catalog, writer = _setup_raw_store(tmp_path)

    block1_log = _sample_log(block_number=100, block_hash="0xa1")

    def mock_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        method = body["method"]
        params = body["params"]
        if method == "eth_getBlockByNumber":
            num = int(params[0], 16)
            h = {
                99: _sample_block_header(99, "0xa1", 1700000099),
                100: _sample_block_header(100, "0xa1", 1700000100),
                198: _sample_block_header(198, "0xa2", 1700000198),
                199: _sample_block_header(199, "0xa3", 1700000199),
                298: _sample_block_header(298, "0xa4", 1700000298),
                300: _sample_block_header(300, "0xa5", 1700000300),
            }.get(num)
            return httpx.Response(200, json=h) if h else httpx.Response(500)
        if method == "eth_getLogs":
            frm = int(params[0]["fromBlock"], 16)
            to = int(params[0]["toBlock"], 16)
            if frm == 99 and to == 198:
                return httpx.Response(200, json=_sample_logs_response([block1_log]))
            return httpx.Response(200, json=_sample_logs_response([]))
        return httpx.Response(500)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    ingestor = UniswapV2PairCreatedIngestor(rpc_url="http://mock", raw_writer=writer, client=client)
    rows = ingestor.fetch(start_block=99, end_block=300, chunk_size=100, receipt_db_path=str(db))
    assert len(rows) == 1
    assert rows[0].block_number == 100

    conn = sqlite3.connect(db)
    receipts = conn.execute(
        "SELECT start_block, end_block FROM uniswap_v2_pair_created_chunk_receipt_v2 ORDER BY start_block"
    ).fetchall()
    conn.close()
    assert len(receipts) == 3
    assert [(r[0], r[1]) for r in receipts] == [(99, 198), (199, 298), (299, 300)]

    ingestor.close()
    catalog.close()


# ---------------------------------------------------------------------------
# 3. Resume and contiguous-range validation
# ---------------------------------------------------------------------------

def test_resume_skips_verified_chunks(tmp_path: Path) -> None:
    _raw_root, db, catalog, writer = _setup_raw_store(tmp_path)

    receipt_end_hash = "0xbb"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO uniswap_v2_pair_created_chunk_receipt_v2 "
        "(chain, factory, topic, start_block, end_block, end_block_hash, logs_raw_object_id, header_raw_object_ids_json, completed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ETHEREUM_CHAIN, UNISWAP_V2_FACTORY, PAIR_CREATED_TOPIC, 100, 200, receipt_end_hash,
         "raw_dummy", "[]", "2026-07-25T00:00:00"),
    )
    conn.commit()
    conn.close()

    called: list[str] = []
    def mock_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        called.append(body["method"])
        params = body["params"]
        if body["method"] == "eth_getBlockByNumber":
            num = int(params[0], 16)
            h = _sample_block_header(num, receipt_end_hash if num == 200 else "0xdd", 1700000000)
            return httpx.Response(200, json=h)
        return httpx.Response(500)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    ingestor = UniswapV2PairCreatedIngestor(rpc_url="http://mock", raw_writer=writer, client=client)
    rows = ingestor.fetch(start_block=100, end_block=200, chunk_size=500, receipt_db_path=str(db))
    assert len(rows) == 0
    assert called == ["eth_getBlockByNumber"]

    ingestor.close()
    catalog.close()


def test_replay_rejects_gap(tmp_path: Path) -> None:
    raw_root, db, catalog, writer = _setup_raw_store(tmp_path)

    log_content = _sample_logs_response([])
    log_raw_id = _write_raw(raw_root, log_content)
    header_raw_id = _write_raw(raw_root, _sample_block_header(199, "0xbb", 1700000199))

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO uniswap_v2_pair_created_chunk_receipt_v2 "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ETHEREUM_CHAIN, UNISWAP_V2_FACTORY, PAIR_CREATED_TOPIC, 100, 199, "0xbb",
         log_raw_id, json.dumps([header_raw_id]), "2026-07-25T00:00:00"),
    )
    conn.execute(
        "INSERT INTO uniswap_v2_pair_created_chunk_receipt_v2 "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ETHEREUM_CHAIN, UNISWAP_V2_FACTORY, PAIR_CREATED_TOPIC, 300, 399, "0xcc",
         log_raw_id, json.dumps([header_raw_id]), "2026-07-25T00:00:00"),
    )
    conn.commit()
    conn.close()

    ingestor = UniswapV2PairCreatedIngestor(rpc_url="http://mock", raw_writer=writer)
    with pytest.raises(UniswapV2IngestionError, match="not contiguous"):
        ingestor.replay_receipts(start_block=100, end_block=399, receipt_db_path=str(db), raw_root=raw_root)

    ingestor.close()
    catalog.close()


# ---------------------------------------------------------------------------
# 4. Deterministic replay equality
# ---------------------------------------------------------------------------

def test_deterministic_replay_equality(tmp_path: Path) -> None:
    raw_root, db, catalog, writer = _setup_raw_store(tmp_path)

    log1 = _patch_topics(
        _sample_log(block_number=150, tx_hash="0x01", log_index=0, block_hash="0xaa"),
        "0x0000000000000000000000000000000000000Aa1",
        "0x0000000000000000000000000000000000000Bb1",
    )
    block_150 = _sample_block_header(150, "0xaa", 1700000150)
    block_199 = _sample_block_header(199, "0xbb", 1700000199)
    logs = _sample_logs_response([log1])

    def mock_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        params = body["params"]
        if body["method"] == "eth_getBlockByNumber":
            num = int(params[0], 16)
            h = {150: block_150, 199: block_199}.get(num)
            return httpx.Response(200, json=h) if h else httpx.Response(500)
        if body["method"] == "eth_getLogs":
            return httpx.Response(200, json=logs)
        return httpx.Response(500)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    ingestor = UniswapV2PairCreatedIngestor(rpc_url="http://mock", raw_writer=writer, client=client)
    fetched = ingestor.fetch(start_block=150, end_block=199, chunk_size=50, receipt_db_path=str(db))
    replay = ingestor.replay_receipts(start_block=150, end_block=199, receipt_db_path=str(db), raw_root=raw_root)

    assert len(fetched) == len(replay.rows)
    for f, r in zip(fetched, replay.rows):
        assert f.as_dict() == r.as_dict()

    ingestor.close()
    catalog.close()


# ---------------------------------------------------------------------------
# 5. Complete raw dependencies
# ---------------------------------------------------------------------------

def test_raw_dependencies_include_logs_and_all_headers(tmp_path: Path) -> None:
    raw_root, db, catalog, writer = _setup_raw_store(tmp_path)

    log1 = _patch_topics(
        _sample_log(block_number=400, tx_hash="0x01", log_index=0, block_hash="0xcc"),
        "0x0000000000000000000000000000000000000Dd1",
        "0x0000000000000000000000000000000000000Ee1",
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        params = body["params"]
        if body["method"] == "eth_getBlockByNumber":
            num = int(params[0], 16)
            h = _sample_block_header(num, "0xcc" if num == 400 else "0xff", 1700000000)
            return httpx.Response(200, json=h)
        if body["method"] == "eth_getLogs":
            return httpx.Response(200, json=_sample_logs_response([log1]))
        return httpx.Response(500)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    ingestor = UniswapV2PairCreatedIngestor(rpc_url="http://mock", raw_writer=writer, client=client)
    ingestor.fetch(start_block=400, end_block=500, chunk_size=200, receipt_db_path=str(db))
    replay = ingestor.replay_receipts(start_block=400, end_block=500, receipt_db_path=str(db), raw_root=raw_root)

    assert len(replay.raw_object_ids) >= 3
    assert len(replay.completed_ranges) == 1
    assert replay.completed_ranges[0] == (400, 500)
    for rid in replay.raw_object_ids:
        assert isinstance(rid, str) and rid.startswith("raw_")

    ingestor.close()
    catalog.close()


# ---------------------------------------------------------------------------
# 6. Duplicate event and block-hash mismatch rejection
# ---------------------------------------------------------------------------

def test_decode_rejects_duplicate_tx_hash_log_index() -> None:
    log1 = _sample_log(block_number=200, tx_hash="0xaa", log_index=0, block_hash="0xbb")
    log2 = _sample_log(block_number=200, tx_hash="0xaa", log_index=0, block_hash="0xbb")
    headers = {200: ({"number": hex(200), "hash": "0xbb", "timestamp": hex(1700000000)}, "raw_1")}
    with pytest.raises(UniswapV2IngestionError, match="duplicate"):
        decode_pair_created(
            {"result": [log1, log2]}, headers,
            factory=UNISWAP_V2_FACTORY, log_raw_object_id="raw_logs",
            availability_time=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_decode_rejects_block_hash_mismatch() -> None:
    log1 = _sample_log(block_number=200, tx_hash="0xaa", log_index=0, block_hash="0xwrong")
    headers = {200: ({"number": hex(200), "hash": "0xcorrect", "timestamp": hex(1700000000)}, "raw_1")}
    with pytest.raises(UniswapV2IngestionError, match="block hash"):
        decode_pair_created(
            {"result": [log1]}, headers,
            factory=UNISWAP_V2_FACTORY, log_raw_object_id="raw_logs",
            availability_time=datetime(2026, 1, 1, tzinfo=UTC),
        )


# ---------------------------------------------------------------------------
# 7. Invalid JSON and SHA-256 mismatch rejection
# ---------------------------------------------------------------------------

def test_read_raw_json_rejects_invalid_json(tmp_path: Path) -> None:
    raw_root, _, _, writer = _setup_raw_store(tmp_path)
    body = b"not json"
    digest = hashlib.sha256(body).hexdigest()
    raw_id = f"raw_{digest}"
    content_addressed_absolute_path(raw_root, digest).parent.mkdir(parents=True, exist_ok=True)
    content_addressed_absolute_path(raw_root, digest).write_bytes(body)

    ingestor = UniswapV2PairCreatedIngestor(rpc_url="http://mock", raw_writer=writer)
    with pytest.raises(UniswapV2IngestionError, match="cannot replay raw object"):
        ingestor._read_raw_json(raw_root, raw_id)

    ingestor.close()


def test_read_raw_json_rejects_sha256_mismatch(tmp_path: Path) -> None:
    raw_root, _, _, writer = _setup_raw_store(tmp_path)
    body = b'{"jsonrpc":"2.0","result":[]}'
    wrong_digest = hashlib.sha256(b"different content").hexdigest()
    raw_id = f"raw_{wrong_digest}"
    content_addressed_absolute_path(raw_root, wrong_digest).parent.mkdir(parents=True, exist_ok=True)
    content_addressed_absolute_path(raw_root, wrong_digest).write_bytes(body)

    ingestor = UniswapV2PairCreatedIngestor(rpc_url="http://mock", raw_writer=writer)
    with pytest.raises(UniswapV2IngestionError, match="SHA-256 mismatch"):
        ingestor._read_raw_json(raw_root, raw_id)

    ingestor.close()


# ---------------------------------------------------------------------------
# 8. Dataset publication and catalog reconciliation
# ---------------------------------------------------------------------------

def test_full_man001_publish_and_catalog_reconciliation(tmp_path: Path) -> None:
    raw_root, db, catalog, writer = _setup_raw_store(tmp_path)
    store_root = tmp_path / "store"
    store_root.mkdir(parents=True, exist_ok=True)

    log1 = _patch_topics(
        _sample_log(block_number=500, tx_hash="0x01", log_index=0, block_hash="0xdd"),
        "0x0000000000000000000000000000000000000Ff1",
        "0x0000000000000000000000000000000000000Gg1",
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        params = body["params"]
        if body["method"] == "eth_getBlockByNumber":
            num = int(params[0], 16)
            h = _sample_block_header(num, "0xdd" if num == 500 else "0xee", 1700000000)
            return httpx.Response(200, json=h)
        if body["method"] == "eth_getLogs":
            return httpx.Response(200, json=_sample_logs_response([log1]))
        return httpx.Response(500)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    ingestor = UniswapV2PairCreatedIngestor(rpc_url="http://mock", raw_writer=writer, client=client)
    ingestor.fetch(start_block=500, end_block=600, chunk_size=200, receipt_db_path=str(db))
    replay = ingestor.replay_receipts(start_block=500, end_block=600, receipt_db_path=str(db), raw_root=raw_root)
    ingestor.close()

    rows = replay.rows
    assert len(rows) == 1

    records = [row.as_dict() for row in rows]
    table = pa.Table.from_pylist(records)
    relative_path = "dex/uniswap_v2_pair_created/events.parquet"

    output = tmp_path / "events.parquet"
    pq.write_table(table, output, compression="zstd")
    sha256 = hashlib.sha256(output.read_bytes()).hexdigest()
    byte_size = output.stat().st_size

    now = datetime.now(UTC)
    raw_deps = sorted(replay.raw_object_ids)
    plan = PublishPlan(
        dataset_type="uniswap_v2_pair_created",
        schema=SchemaIdentity(name="uniswap_v2_pair_created", version="1"),
        transform=TransformSpec(name="uniswap_v2_pair_created_ingest", version="1"),
        code=CodeIdentity(commit="test_commit"),
        config=ConfigIdentity(config_sha256="0" * 64),
        dependencies=[
            DependencyRef(id=raw_id, kind=DependencyKind.RAW_OBJECT, role="rpc_response")
            for raw_id in raw_deps
        ],
        output_sources={relative_path: output},
        output_specs=[OutputFileSpec(relative_path=relative_path, sha256=sha256, rows=table.num_rows, bytes=byte_size, rows_verified=True)],
        statistics=DatasetStatistics(row_count=table.num_rows, byte_size=byte_size),
        coverage=CoverageWindow(
            event_start=rows[0].event_time,
            event_end=rows[0].event_time,
            availability_start=rows[0].availability_time,
            availability_end=rows[0].availability_time,
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={"chain": "ethereum", "event": "PairCreated", "row_count": table.num_rows},
        created_at=now,
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_receipts={relative_path: RowCountReceipt(relative_path=relative_path, row_count=table.num_rows, verifier_name="test_row_count")},
    )

    dataset_catalog = SqliteDatasetCatalog(db)
    DatasetPublisher(DatasetStoreConfig(root=store_root), dataset_catalog).publish(plan, register_catalog=True)

    resolved = dataset_catalog.resolve_latest_by_type("uniswap_v2_pair_created")
    assert resolved is not None, "dataset should be registered and resolvable"
    dataset_catalog.close()
    catalog.close()


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------

def test_hex_int() -> None:
    assert _hex_int("0x1") == 1
    assert _hex_int("0xff") == 255
    with pytest.raises(UniswapV2IngestionError):
        _hex_int("not_hex")
    with pytest.raises(UniswapV2IngestionError):
        _hex_int(42)


def test_address_extracts_last_20_bytes() -> None:
    word = "0x" + "00" * 12 + "aa" * 20
    assert _address(word) == "0x" + "aa" * 20
    with pytest.raises(UniswapV2IngestionError):
        _address(42)
    with pytest.raises(UniswapV2IngestionError):
        _address("0xshort")
