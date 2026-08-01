"""DEX-003 — focused offline tests for the corrected bounded v2 engine.

No live RPC. MockTransport only. Covers the authorization corrections:

1. HTTP bodies stream to durable spool descriptors (no unbounded materialize)
2. Persistent workers + multi-node flight + dedicated persistence thread
3. Preserve-before-interpret dual drain/offer
4. Lease heartbeat/renewal, expiry attempt bump, claim max-attempt filter
5. Reinit verifies complete plan/root set
6. Dual chain identity once per plan
7. Dual header fields, log↔header hash bind, re-auth cache
8. Exact error classes (429 backoff no-split; size split; transport ≠ size)
9. Versioned engine event records (forward 0018 tables in test fixture only)
10. Credential-free requests in spools/events

Jr owns integration, crash/concurrency stress, and migration 0018.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from cryptofactors.acquisition.uniswap_v2 import _canonical_json
from cryptofactors.acquisition.uniswap_v2_pair_events import SWAP_TOPIC
from cryptofactors.acquisition.uniswap_v2_pair_events_v2 import (
    ORDERED_EVENT_TOPICS,
    PINNED_FINALITY_CUTOFF_BLOCK,
    PairEventV2Error,
    PlanConfig,
    QueryDomain,
    QueryNode,
    RegistryPoolBirth,
    build_acquisition_plan_v2,
    request_for_domain,
    split_node,
)
from cryptofactors.acquisition.uniswap_v2_pair_events_v2_engine import (
    CHAIN_IDENTITY_TABLE,
    ENGINE_EVENT_RECORD_COLUMNS,
    ENGINE_EVENT_TABLE,
    EXECUTION_POLICY_TABLE,
    FAILURE_ROUTE_PRECEDENCE,
    HEADER_TABLE,
    LEAF_TABLE,
    NODE_TABLE,
    SPOOL_DESCRIPTOR_SCHEMA_VERSION,
    TERMINAL_RECEIPT_TABLE,
    Claim,
    EngineConfig,
    EnginePhase,
    FailureClass,
    NetworkWorker,
    PairEventV2Engine,
    PersistedEnvelope,
    SpoolDescriptor,
    SOURCE_ID,
    _ActiveWork,
    _FailureFact,
    _PairFailure,
    _TokenBucket,
    compute_terminal_receipt_id,
    make_engine_event_record,
)
from cryptofactors.catalog.runner import apply_migrations

REPO_MIGRATIONS = Path(__file__).resolve().parent.parent.parent / "sql" / "migrations"

POOL = "0x" + "ab" * 20
POOL_B = "0x" + "cd" * 20
LATE_BIRTH = PINNED_FINALITY_CUTOFF_BLOCK - 100
WORD = "00" * 32


def _addr_topic(byte: int) -> str:
    return "0x" + "00" * 12 + f"{byte:02x}" * 20


def _swap_log(
    *,
    address: str = POOL,
    block_number: int = LATE_BIRTH + 1,
    block_hash: str = "0x" + "ab" * 32,
    tx_hash: str = "0x" + "cd" * 32,
    tx_index: int = 1,
    log_index: int = 0,
) -> dict[str, Any]:
    return {
        "address": address,
        "blockNumber": hex(block_number),
        "blockHash": block_hash,
        "transactionHash": tx_hash,
        "transactionIndex": hex(tx_index),
        "logIndex": hex(log_index),
        "topics": [SWAP_TOPIC, _addr_topic(0x22), _addr_topic(0x33)],
        "data": "0x" + WORD * 4,
        "removed": False,
    }


def _header_result(
    *,
    block_number: int,
    block_hash: str = "0x" + "ab" * 32,
    timestamp: int = 1_700_000_000,
) -> dict[str, Any]:
    return {
        "number": hex(block_number),
        "hash": block_hash,
        "timestamp": hex(timestamp),
        "parentHash": "0x" + "11" * 32,
    }


def _rpc_ok(result: Any, *, req_id: Any = 1) -> bytes:
    return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}).encode()


def _apply_forward_tables(db_path: Path) -> None:
    """Migration 0018 now provides all engine persistence tables via apply_migrations.
    This helper is retained for backward compatibility but is a no-op.
    """
    # Nothing to do — migration 0018 creates CHAIN_IDENTITY_TABLE,
    # ENGINE_EVENT_TABLE, EXECUTION_POLICY_TABLE, TERMINAL_RECEIPT_TABLE,
    # plus all header/leaf/dependency/terminal uniqueness indexes.
    pass


class RpcFixture:
    def __init__(self) -> None:
        self.logs: list[dict[str, Any]] = []
        self.headers: dict[int, dict[str, Any]] = {}
        self.method_status: dict[str, int] = {}
        self.primary_logs: list[dict[str, Any]] | None = None
        self.secondary_logs: list[dict[str, Any]] | None = None
        self.rpc_error: dict[str, Any] | None = None
        self.call_counts: dict[str, int] = {}
        self.lock = threading.Lock()

    def set_empty_logs(self) -> None:
        self.logs = []
        self.primary_logs = None
        self.secondary_logs = None

    def set_agreed_swap(self, block_number: int) -> None:
        log = _swap_log(block_number=block_number)
        self.logs = [log]
        self.headers[block_number] = _header_result(
            block_number=block_number, block_hash=str(log["blockHash"])
        )

    def _handle(self, request: httpx.Request, *, org: str) -> httpx.Response:
        body = json.loads(request.content)
        method = str(body.get("method", ""))
        req_id = body.get("id", 1)
        with self.lock:
            self.call_counts[method] = self.call_counts.get(method, 0) + 1
        status = self.method_status.get(method, 200)
        if status == 429:
            return httpx.Response(429, content=b"rate limited")
        if status >= 400:
            return httpx.Response(status, content=b"error")
        if method == "eth_chainId":
            return httpx.Response(200, content=_rpc_ok("0x1", req_id=req_id))
        if method == "eth_getLogs":
            if self.rpc_error is not None:
                return httpx.Response(
                    200,
                    content=json.dumps(
                        {"jsonrpc": "2.0", "id": req_id, "error": self.rpc_error}
                    ).encode(),
                )
            if org == "primary" and self.primary_logs is not None:
                logs = self.primary_logs
            elif org == "secondary" and self.secondary_logs is not None:
                logs = self.secondary_logs
            else:
                logs = self.logs
            return httpx.Response(200, content=_rpc_ok(logs, req_id=req_id))
        if method == "eth_getBlockByNumber":
            params = body.get("params") or []
            block_number = int(params[0], 16) if params else 0
            header = self.headers.get(block_number) or _header_result(
                block_number=block_number
            )
            self.headers.setdefault(block_number, header)
            return httpx.Response(200, content=_rpc_ok(header, req_id=req_id))
        return httpx.Response(
            200,
            content=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"unknown {method}"},
                }
            ).encode(),
        )

    def primary_client(self) -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(
                lambda request: self._handle(request, org="primary")
            )
        )

    def secondary_client(self) -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(
                lambda request: self._handle(request, org="secondary")
            )
        )


class Store:
    def __init__(self, tmp_path: Path) -> None:
        self.raw_root = tmp_path / "raw"
        self.spool_dir = tmp_path / "spool"
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.spool_dir.mkdir(parents=True, exist_ok=True)
        self.db = tmp_path / "engine.db"
        apply_migrations(self.db, migrations_dir=REPO_MIGRATIONS)
        _apply_forward_tables(self.db)

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        conn = sqlite3.connect(self.db)
        try:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(sql, params)]
        finally:
            conn.close()


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path)


@pytest.fixture
def rpc() -> RpcFixture:
    return RpcFixture()


def _engine(
    store: Store,
    rpc: RpcFixture,
    *,
    worker_id: str = "worker-a",
    max_attempts: int = 3,
    max_log_count: int = 8_000,
    lease_ttl_seconds: float = 120.0,
    max_nodes_in_flight: int = 1,
    backoff_base_seconds: float = 0.01,
    backoff_max_seconds: float = 0.02,
    http_timeout_seconds: float = 60.0,
    command_offer_timeout_seconds: float = 60.0,
) -> PairEventV2Engine:
    config = EngineConfig(
        receipt_db_path=store.db,
        raw_root=store.raw_root,
        spool_dir=store.spool_dir,
        primary_rpc_url="https://primary.example/v3/KEY",
        secondary_rpc_url="https://secondary.example/v1/KEY",
        worker_id=worker_id,
        plan_config=PlanConfig(),
        max_attempts=max_attempts,
        max_log_count=max_log_count,
        lease_ttl_seconds=lease_ttl_seconds,
        max_nodes_in_flight=max_nodes_in_flight,
        max_spool_files=max(8, max_nodes_in_flight * 2),
        requests_per_second=1000.0,
        max_in_flight_per_provider=4,
        backoff_base_seconds=backoff_base_seconds,
        backoff_max_seconds=backoff_max_seconds,
        http_timeout_seconds=http_timeout_seconds,
        command_offer_timeout_seconds=command_offer_timeout_seconds,
    )
    return PairEventV2Engine(
        config,
        primary_client=rpc.primary_client(),
        secondary_client=rpc.secondary_client(),
    )


# ---------------------------------------------------------------------------
# Config / spool transport
# ---------------------------------------------------------------------------


def test_engine_config_rejects_same_urls(tmp_path: Path) -> None:
    with pytest.raises(PairEventV2Error, match="distinct"):
        EngineConfig(
            receipt_db_path=tmp_path / "x.db",
            raw_root=tmp_path / "raw",
            spool_dir=tmp_path / "spool",
            primary_rpc_url="https://same.example/rpc",
            secondary_rpc_url="https://same.example/rpc",
            worker_id="w1",
        )


def test_engine_config_rejects_same_orgs(tmp_path: Path) -> None:
    with pytest.raises(PairEventV2Error, match="distinct"):
        EngineConfig(
            receipt_db_path=tmp_path / "x.db",
            raw_root=tmp_path / "raw",
            spool_dir=tmp_path / "spool",
            primary_rpc_url="https://a.example/rpc",
            secondary_rpc_url="https://b.example/rpc",
            worker_id="w1",
            primary_org="infura",
            secondary_org="infura",
        )


def test_network_worker_streams_to_spool_not_memory(tmp_path: Path) -> None:
    payload = _rpc_ok("0x1")
    spool = tmp_path / "spool"
    spool.mkdir()
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=payload))
    )
    worker = NetworkWorker(
        client=client,
        rpc_url="https://example/rpc",
        provider_org="infura",
        bucket=_TokenBucket(rate=1000.0, capacity=2.0),
        limiter=__import__(
            "cryptofactors.acquisition.uniswap_v2_pair_events_v2_engine",
            fromlist=["_AdaptiveLimiter"],
        )._AdaptiveLimiter(2),
        spool_dir=spool,
        spool_capacity=threading.BoundedSemaphore(4),
        max_body_bytes=1_000_000,
        chunk_bytes=16,
        response_drain_deadline_seconds=30.0,
    )
    request = {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}
    descriptor = worker.fetch(request)
    assert isinstance(descriptor, SpoolDescriptor)
    assert descriptor.error_kind is None
    assert descriptor.spool_path is not None
    assert descriptor.spool_path.exists()
    assert descriptor.spool_path.read_bytes() == payload
    assert descriptor.retained_bytes == len(payload)
    assert descriptor.response_bytes == len(payload)
    assert "KEY" not in descriptor.request_json
    assert json.loads(descriptor.request_json)["method"] == "eth_chainId"
    client.close()


def test_network_worker_transport_failure_still_returns_descriptor(
    tmp_path: Path,
) -> None:
    spool = tmp_path / "spool"
    spool.mkdir()

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    client = httpx.Client(transport=httpx.MockTransport(boom))
    worker = NetworkWorker(
        client=client,
        rpc_url="https://example/rpc",
        provider_org="blockpi",
        bucket=_TokenBucket(rate=1000.0, capacity=2.0),
        limiter=__import__(
            "cryptofactors.acquisition.uniswap_v2_pair_events_v2_engine",
            fromlist=["_AdaptiveLimiter"],
        )._AdaptiveLimiter(2),
        spool_dir=spool,
        spool_capacity=threading.BoundedSemaphore(4),
        max_body_bytes=1_000_000,
        chunk_bytes=64,
        response_drain_deadline_seconds=30.0,
    )
    descriptor = worker.fetch(
        {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}
    )
    assert descriptor.error_kind == "transport"
    assert descriptor.acquisition_id is not None
    client.close()


def test_engine_event_record_rejects_sensitive_detail() -> None:
    with pytest.raises(PairEventV2Error):
        make_engine_event_record(
            plan_id="plan_" + "a" * 64,
            domain_id=None,
            attempt=0,
            event_kind="failure",
            failure_class=FailureClass.TRANSPORT,
            detail={"api_key": "secret"},
        )


def test_spool_journal_and_persisted_artifacts_are_credential_free(
    store: Store, rpc: RpcFixture
) -> None:
    """Live spool journals, engine events, and raw acquisitions never leak the endpoint or key.

    The engine runs against credential-bearing URLs (https://primary.example/v3/KEY
    and https://secondary.example/v1/KEY). The spool journal is read live from disk,
    and the persisted engine-event and raw-acquisition JSON are read back from the
    receipt database; neither the endpoint host, the key path segment, nor the key
    material may appear in any of them.
    """
    # 1. Live NetworkWorker fetch writes a journal beside the retained spool.
    payload = _rpc_ok("0x1")
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=payload))
    )
    worker = NetworkWorker(
        client=client,
        rpc_url="https://primary.example/v3/KEY",
        provider_org="infura",
        bucket=_TokenBucket(rate=1000.0, capacity=2.0),
        limiter=__import__(
            "cryptofactors.acquisition.uniswap_v2_pair_events_v2_engine",
            fromlist=["_AdaptiveLimiter"],
        )._AdaptiveLimiter(2),
        spool_dir=store.spool_dir,
        spool_capacity=threading.BoundedSemaphore(4),
        max_body_bytes=1_000_000,
        chunk_bytes=16,
        response_drain_deadline_seconds=30.0,
    )
    descriptor = None
    try:
        descriptor = worker.fetch(
            {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}
        )
        assert descriptor.journal_path is not None
        assert descriptor.journal_path.exists()
        journal_text = descriptor.journal_path.read_text()
        assert "primary.example" not in journal_text
        assert "/v3/" not in journal_text
        assert "KEY" not in journal_text
        assert json.loads(journal_text)["request"]["method"] == "eth_chainId"
    finally:
        client.close()
        if descriptor is not None:
            if descriptor.journal_path is not None:
                descriptor.journal_path.unlink(missing_ok=True)
            if descriptor.spool_path is not None:
                descriptor.spool_path.unlink(missing_ok=True)

    # 2. End-to-end transport failure persists engine events and raw acquisitions.
    class TransportFail(RpcFixture):
        def _handle(self, request: httpx.Request, *, org: str) -> httpx.Response:
            body = json.loads(request.content)
            method = str(body.get("method", ""))
            if method == "eth_chainId":
                return httpx.Response(
                    200, content=_rpc_ok("0x1", req_id=body.get("id", 1))
                )
            if method == "eth_getLogs":
                raise httpx.ConnectError("transport down")
            return super()._handle(request, org=org)

    broken = TransportFail()
    engine = _engine(store, broken, max_attempts=1)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()
        assert engine.process_one() == "terminal:transport"

        event_rows = store.query(
            f"SELECT request_json FROM {ENGINE_EVENT_TABLE} WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert event_rows, "engine events must be persisted"
        for row in event_rows:
            assert "primary.example" not in (row["request_json"] or "")
            assert "secondary.example" not in (row["request_json"] or "")
            assert "KEY" not in (row["request_json"] or "")

        raw_rows = store.query(
            "SELECT request_json, response_metadata_json FROM raw_acquisition"
        )
        assert raw_rows, "raw acquisitions must be persisted"
        for row in raw_rows:
            for field in ("request_json", "response_metadata_json"):
                assert "primary.example" not in (row[field] or "")
                assert "secondary.example" not in (row[field] or "")
                assert "KEY" not in (row[field] or "")
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Plan / lease contracts
# ---------------------------------------------------------------------------


def test_initialize_plan_claim_and_idempotent_reinit(
    store: Store, rpc: RpcFixture
) -> None:
    engine = _engine(store, rpc)
    try:
        pools = [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        plan = engine.initialize(pools)
        assert plan.root_filter_count == 1
        counts = engine.coordinator.count_by_status(plan.plan_id)
        assert counts.get("PENDING") == 1
        assert counts.get("IN_FLIGHT", 0) == 0

        # Dual chain identity cached once.
        engine.authenticate_chain()
        chains = store.query(f"SELECT * FROM {CHAIN_IDENTITY_TABLE}")
        assert len(chains) == 1
        assert chains[0]["chain_id"] == 1
        assert chains[0]["primary_provider_org"] == "infura"
        assert chains[0]["secondary_provider_org"] == "blockpi"

        # Reinit verifies exact root set (no duplicate roots).
        plan2 = engine.initialize(pools)
        assert plan2.plan_id == plan.plan_id
        assert engine.coordinator.count_by_status(plan.plan_id).get("PENDING") == 1

        claim = engine.coordinator.claim_pending(
            plan_id=plan.plan_id,
            worker_id="worker-a",
            lease_ttl_seconds=60.0,
        )
        assert claim is not None
        assert claim.node.status == "IN_FLIGHT"
        assert len(claim.lease_token) == 32
        assert (
            engine.coordinator.claim_pending(
                plan_id=plan.plan_id,
                worker_id="worker-b",
                lease_ttl_seconds=60.0,
            )
            is None
        )
        renewed = engine.coordinator.renew_lease(
            claim=Claim(
                plan_id=plan.plan_id,
                domain_id=claim.node.domain_id,
                worker_id="worker-a",
                lease_token=claim.lease_token,
                attempt=claim.attempt,
                node=claim.node,
            ),
            lease_ttl_seconds=60.0,
        )
        assert renewed is True
    finally:
        engine.close()


def _tamper_raw_evidence(store: Store, acquisition_id: str, tamper: str) -> None:
    """Apply one tamper to a persisted complete-success raw acquisition."""
    conn = sqlite3.connect(str(store.db))
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT a.acquisition_id, a.raw_object_id, a.response_metadata_json, "
            "o.storage_uri FROM raw_acquisition a JOIN raw_object o "
            "ON o.raw_object_id = a.raw_object_id WHERE a.acquisition_id = ?",
            (acquisition_id,),
        ).fetchone()
        assert row is not None, f"raw evidence for {acquisition_id} is missing"
        if tamper == "metadata_truncated":
            meta = json.loads(row["response_metadata_json"])
            meta["truncated"] = True
            conn.execute(
                "UPDATE raw_acquisition SET response_metadata_json = ? "
                "WHERE acquisition_id = ?",
                (json.dumps(meta), acquisition_id),
            )
        elif tamper == "metadata_status":
            conn.execute(
                "UPDATE raw_acquisition SET status = 'REGISTRATION_PENDING' "
                "WHERE acquisition_id = ?",
                (acquisition_id,),
            )
        elif tamper == "raw_bytes":
            path = store.raw_root / row["storage_uri"]
            original = path.read_bytes()
            flipped = bytearray(original)
            flipped[-1] ^= 0xFF
            path.write_bytes(bytes(flipped))
        elif tamper == "storage_uri":
            # Same content at a non-canonical path defeats the digest-derived URI.
            original = (store.raw_root / row["storage_uri"]).read_bytes()
            wrong = store.raw_root / "raw/sha256/zz/zz/wrong-location"
            wrong.parent.mkdir(parents=True, exist_ok=True)
            wrong.write_bytes(original)
            conn.execute(
                "UPDATE raw_object SET storage_uri = ? WHERE raw_object_id = ?",
                ("raw/sha256/zz/zz/wrong-location", row["raw_object_id"]),
            )
        else:
            raise AssertionError(f"unknown tamper kind: {tamper}")
        conn.commit()
    finally:
        conn.close()


@pytest.mark.parametrize(
    "tamper",
    ["metadata_truncated", "metadata_status", "raw_bytes", "storage_uri"],
)
def test_cached_chain_replay_rejects_tampered_evidence(
    store: Store, rpc: RpcFixture, tamper: str
) -> None:
    """Cached chain identity replay re-authenticates raw evidence; any tamper fails closed."""
    engine = _engine(store, rpc)
    try:
        engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()
    finally:
        engine.close()

    chain = store.query(f"SELECT * FROM {CHAIN_IDENTITY_TABLE}")[0]
    _tamper_raw_evidence(store, chain["primary_acquisition_id"], tamper)

    # A fresh engine on the same store re-runs the cached load path and must fail.
    engine = _engine(store, rpc)
    try:
        engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        with pytest.raises(PairEventV2Error, match="cached chain identity load failed"):
            engine.authenticate_chain()
    finally:
        engine.close()


@pytest.mark.parametrize(
    "tamper",
    ["metadata_truncated", "metadata_status", "raw_bytes", "storage_uri"],
)
def test_cached_header_replay_rejects_tampered_evidence(
    store: Store, rpc: RpcFixture, tamper: str
) -> None:
    """Cached header replay re-authenticates raw evidence; any tamper routes AUTHENTICATION."""
    rpc.set_agreed_swap(LATE_BIRTH)
    engine = _engine(store, rpc)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()
        assert engine.process_one() == "agreed"
    finally:
        engine.close()

    # End-block header (block_number = PINNED_FINALITY_CUTOFF_BLOCK) is cached.
    header = store.query(
        f"SELECT primary_acquisition_id FROM {HEADER_TABLE} "
        "WHERE plan_id = ? ORDER BY block_number DESC LIMIT 1",
        (plan.plan_id,),
    )
    assert len(header) == 1
    _tamper_raw_evidence(store, header[0]["primary_acquisition_id"], tamper)

    engine = _engine(store, rpc)
    try:
        plan2 = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        assert plan2.plan_id == plan.plan_id
        engine.authenticate_chain()

        # Fresh node ending at the cached block with no logs must re-load it.
        rpc.set_empty_logs()
        domain = QueryDomain(
            start_block=LATE_BIRTH + 5,
            end_block=PINNED_FINALITY_CUTOFF_BLOCK,
            addresses=(POOL,),
            topics=ORDERED_EVENT_TOPICS,
        )
        conn = sqlite3.connect(str(store.db))
        try:
            conn.execute("PRAGMA busy_timeout = 5000")
            node = QueryNode(plan_id=plan.plan_id, domain=domain, status="PENDING")
            conn.execute(
                f"INSERT INTO {NODE_TABLE} (plan_id, domain_id, start_block, end_block, "
                "addresses_json, topics_json, status, parent_domain_id, split_reason, "
                "attempt, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    node.plan_id,
                    node.domain_id,
                    domain.start_block,
                    domain.end_block,
                    _canonical_json(list(domain.addresses)),
                    _canonical_json(list(domain.topics)),
                    "PENDING",
                    None,
                    None,
                    0,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        outcome = engine.process_one()
        assert outcome == "retry:authentication"
        events = store.query(
            f"SELECT failure_class, event_kind FROM {ENGINE_EVENT_TABLE} "
            "WHERE plan_id = ? AND domain_id = ?",
            (plan.plan_id, node.domain_id),
        )
        assert any(
            e["failure_class"] == FailureClass.AUTHENTICATION.value
            and e["event_kind"] == "failure"
            for e in events
        )
    finally:
        engine.close()


def test_lease_expiry_increments_attempt_and_records_event(
    store: Store, rpc: RpcFixture
) -> None:
    engine = _engine(store, rpc, lease_ttl_seconds=0.05)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        claim = engine.coordinator.claim_pending(
            plan_id=plan.plan_id,
            worker_id="worker-a",
            lease_ttl_seconds=0.05,
        )
        assert claim is not None
        # Force past expiry while satisfying CHECK(expires_at >= leased_at).
        leased = (datetime.now(UTC) - timedelta(seconds=60)).isoformat()
        expired_at = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()
        conn = sqlite3.connect(store.db)
        try:
            conn.execute(
                "UPDATE uniswap_v2_pair_event_v2_query_lease "
                "SET leased_at = ?, expires_at = ?",
                (leased, expired_at),
            )
            conn.commit()
        finally:
            conn.close()
        # Claim path expires leases first.
        reclaimed = engine.coordinator.claim_pending(
            plan_id=plan.plan_id,
            worker_id="worker-b",
            lease_ttl_seconds=60.0,
        )
        assert reclaimed is not None
        assert reclaimed.attempt == 1
        events = store.query(
            f"SELECT event_kind FROM {ENGINE_EVENT_TABLE} ORDER BY created_at"
        )
        kinds = {row["event_kind"] for row in events}
        assert "lease_expiry" in kinds
        assert "retry_decision" in kinds
    finally:
        engine.close()


def test_claim_filters_nodes_at_retry_limit(store: Store, rpc: RpcFixture) -> None:
    engine = _engine(store, rpc, max_attempts=2)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        conn = sqlite3.connect(store.db)
        try:
            conn.execute(
                f"UPDATE {NODE_TABLE} SET attempt = 2 WHERE plan_id = ?",
                (plan.plan_id,),
            )
            conn.commit()
        finally:
            conn.close()
        assert (
            engine.coordinator.claim_pending(
                plan_id=plan.plan_id,
                worker_id="worker-a",
                lease_ttl_seconds=60.0,
            )
            is None
        )
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Process paths
# ---------------------------------------------------------------------------


def test_process_one_agreed_empty_logs(store: Store, rpc: RpcFixture) -> None:
    rpc.set_empty_logs()
    engine = _engine(store, rpc)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()
        root = plan.root_filters[0]
        rpc.headers[root.domain.end_block] = _header_result(
            block_number=root.domain.end_block
        )
        outcome = engine.process_one()
        assert outcome == "agreed"
        metrics = engine.metrics
        assert metrics.claims == 1
        assert metrics.agreed == 1
        assert metrics.headers_fetched >= 1
        assert engine.coordinator.count_by_status(plan.plan_id).get("AGREED") == 1
        leaves = store.query(f"SELECT * FROM {LEAF_TABLE}")
        assert len(leaves) == 1
        assert leaves[0]["log_count"] == 0
        assert leaves[0]["reconciliation_status"] == "AGREED"
        deps = store.query(
            "SELECT * FROM uniswap_v2_pair_event_v2_leaf_header_dependency"
        )
        assert len(deps) >= 1
    finally:
        engine.close()


def test_process_one_agreed_binds_log_block_hash_to_header(
    store: Store, rpc: RpcFixture
) -> None:
    event_block = LATE_BIRTH + 1
    rpc.set_agreed_swap(event_block)
    engine = _engine(store, rpc)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()
        root = plan.root_filters[0]
        rpc.headers[root.domain.end_block] = _header_result(
            block_number=root.domain.end_block
        )
        assert engine.process_one() == "agreed"
        leaves = store.query(f"SELECT * FROM {LEAF_TABLE}")
        assert leaves[0]["log_count"] == 1
        headers = store.query(
            "SELECT block_number, block_hash FROM "
            "uniswap_v2_pair_event_v2_canonical_header_receipt "
            "ORDER BY block_number"
        )
        by_block = {int(h["block_number"]): h["block_hash"] for h in headers}
        assert event_block in by_block
        assert by_block[event_block] == "0x" + "ab" * 32
        assert root.domain.end_block in by_block
    finally:
        engine.close()


def test_process_one_429_retries_without_split(store: Store, rpc: RpcFixture) -> None:
    # Chain succeeds; logs hit 429 → backoff retry, never split.
    rpc.method_status["eth_getLogs"] = 429
    engine = _engine(store, rpc, backoff_base_seconds=0.01, backoff_max_seconds=0.02)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()
        outcome = engine.process_one()
        assert outcome == f"retry:{FailureClass.HTTP_429}"
        assert engine.metrics.http_429 == 1
        assert engine.metrics.retries == 1
        assert engine.metrics.splits == 0
        assert engine.coordinator.count_by_status(plan.plan_id).get("PENDING") == 1
        rows = store.query(
            f"SELECT attempt, status FROM {NODE_TABLE} WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert rows[0]["status"] == "PENDING"
        assert int(rows[0]["attempt"]) == 1
        events = store.query(
            f"SELECT event_kind, failure_class, decision FROM {ENGINE_EVENT_TABLE}"
        )
        assert any(e["event_kind"] == "retry_decision" for e in events)
        assert any(e["failure_class"] == FailureClass.HTTP_429.value for e in events)
    finally:
        engine.close()


def test_process_one_transport_does_not_masquerade_as_size(
    store: Store, rpc: RpcFixture
) -> None:
    class TransportFail(RpcFixture):
        def _handle(self, request: httpx.Request, *, org: str) -> httpx.Response:
            body = json.loads(request.content)
            method = str(body.get("method", ""))
            if method == "eth_chainId":
                return httpx.Response(
                    200, content=_rpc_ok("0x1", req_id=body.get("id", 1))
                )
            if method == "eth_getLogs":
                raise httpx.ConnectError("transport down")
            return super()._handle(request, org=org)

    broken = TransportFail()
    engine = _engine(store, broken, max_attempts=1)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()
        outcome = engine.process_one()
        # Transport is not a size class → terminal after max attempts, no split.
        assert outcome == "terminal:transport"
        assert "oversized" not in outcome
        assert engine.metrics.splits == 0
        assert engine.metrics.terminal_blockers == 1
        events = store.query(
            f"SELECT failure_class, event_kind FROM {ENGINE_EVENT_TABLE}"
        )
        assert any(e["failure_class"] == FailureClass.TRANSPORT.value for e in events)
        assert any(e["event_kind"] == "terminal_blocker" for e in events)
        # Node not claimable at limit.
        assert engine.coordinator.count_by_status(plan.plan_id)["PENDING"] == 1

        # One durable terminal receipt with exact mode, attempt, domain, and
        # recomputed content-addressed ID.
        claim = store.query(
            f"SELECT domain_id FROM {NODE_TABLE} WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert len(claim) == 1
        domain_id = claim[0]["domain_id"]
        terminals = store.query(
            f"SELECT * FROM {TERMINAL_RECEIPT_TABLE} WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert len(terminals) == 1
        assert terminals[0]["terminal_mode"] == "transport"
        assert int(terminals[0]["attempt"]) == 1  # max_attempts
        assert terminals[0]["domain_id"] == domain_id
        expected_id = compute_terminal_receipt_id(
            plan_id=plan.plan_id,
            domain_id=domain_id,
            terminal_mode="transport",
            attempt=1,
        )
        assert terminals[0]["terminal_receipt_id"] == expected_id
    finally:
        engine.close()


def test_process_one_oversized_splits_by_address(store: Store, rpc: RpcFixture) -> None:
    engine = _engine(store, rpc, max_log_count=1)
    try:
        plan = build_acquisition_plan_v2(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)],
            PlanConfig(),
        )
        # Initialize plan (and chain) then replace root with 2-address domain.
        engine.coordinator.initialize_plan(
            plan, execution_policy=engine.execution_policy_identity(plan.plan_id)
        )
        engine._plan_id = plan.plan_id
        engine._phase = EnginePhase.PLAN_INITIALIZED
        engine.authenticate_chain()

        domain = QueryDomain(
            start_block=LATE_BIRTH,
            end_block=LATE_BIRTH + 10,
            addresses=tuple(sorted([POOL, POOL_B])),
            topics=ORDERED_EVENT_TOPICS,
        )
        # Direct DB surgery on the single owner would race the persistence thread —
        # use a short-lived connection after stop is not set; coordinator owns the DB.
        # Replace via commit path: delete roots using a one-shot SQL through status.
        # Claim and force size pressure on the custom domain by rewriting nodes via
        # sqlite on a separate connection with busy timeout while coordinator is idle.
        time.sleep(0.05)
        conn = sqlite3.connect(store.db, timeout=10)
        try:
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute(f"DELETE FROM {NODE_TABLE} WHERE plan_id = ?", (plan.plan_id,))
            node = QueryNode(plan_id=plan.plan_id, domain=domain, status="PENDING")
            conn.execute(
                f"INSERT INTO {NODE_TABLE} (plan_id, domain_id, start_block, end_block, "
                "addresses_json, topics_json, status, parent_domain_id, split_reason, "
                "attempt, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    node.plan_id,
                    node.domain_id,
                    domain.start_block,
                    domain.end_block,
                    _canonical_json(list(domain.addresses)),
                    _canonical_json(list(domain.topics)),
                    "PENDING",
                    None,
                    None,
                    0,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        rpc.logs = [
            _swap_log(block_number=LATE_BIRTH + 1, log_index=0),
            _swap_log(
                block_number=LATE_BIRTH + 1,
                log_index=1,
                tx_hash="0x" + "ee" * 32,
            ),
        ]
        outcome = engine.process_one()
        assert outcome == "split:oversized_result"
        counts = engine.coordinator.count_by_status(plan.plan_id)
        assert counts.get("SPLIT") == 1
        assert counts.get("PENDING") == 2
        assert engine.metrics.splits == 1
    finally:
        engine.close()


def test_process_one_disagreement_retries_then_splits(
    store: Store, rpc: RpcFixture
) -> None:
    disagree = RpcFixture()
    disagree.primary_logs = [_swap_log(block_number=LATE_BIRTH + 1, log_index=0)]
    disagree.secondary_logs = [
        _swap_log(
            block_number=LATE_BIRTH + 1,
            log_index=1,
            tx_hash="0x" + "ff" * 32,
        )
    ]
    engine = _engine(store, disagree, max_attempts=1)
    try:
        plan = build_acquisition_plan_v2(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)],
            PlanConfig(),
        )
        engine.coordinator.initialize_plan(
            plan, execution_policy=engine.execution_policy_identity(plan.plan_id)
        )
        engine._plan_id = plan.plan_id
        engine._phase = EnginePhase.PLAN_INITIALIZED
        engine.authenticate_chain()
        domain = QueryDomain(
            start_block=LATE_BIRTH,
            end_block=LATE_BIRTH + 10,
            addresses=tuple(sorted([POOL, POOL_B])),
            topics=ORDERED_EVENT_TOPICS,
        )
        time.sleep(0.05)
        conn = sqlite3.connect(store.db, timeout=10)
        try:
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute(f"DELETE FROM {NODE_TABLE} WHERE plan_id = ?", (plan.plan_id,))
            node = QueryNode(plan_id=plan.plan_id, domain=domain, status="PENDING")
            conn.execute(
                f"INSERT INTO {NODE_TABLE} (plan_id, domain_id, start_block, end_block, "
                "addresses_json, topics_json, status, parent_domain_id, split_reason, "
                "attempt, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    node.plan_id,
                    node.domain_id,
                    domain.start_block,
                    domain.end_block,
                    _canonical_json(list(domain.addresses)),
                    _canonical_json(list(domain.topics)),
                    "PENDING",
                    None,
                    None,
                    0,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        outcome = engine.process_one()
        assert outcome == "split:provider_disagreement"
        assert engine.metrics.disagreements == 1
        assert engine.metrics.splits == 1
        events = store.query(
            f"SELECT event_kind FROM {ENGINE_EVENT_TABLE} WHERE event_kind = "
            "'provider_disagreement' OR event_kind = 'split_decision'"
        )
        assert len(events) >= 2
    finally:
        engine.close()


def test_explicit_range_limit_splits_blocks(store: Store, rpc: RpcFixture) -> None:
    rpc.rpc_error = {
        "code": -32005,
        "message": "query exceeds maximum block range of 2000 blocks",
    }
    engine = _engine(store, rpc)
    try:
        plan = build_acquisition_plan_v2(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)],
            PlanConfig(),
        )
        engine.coordinator.initialize_plan(
            plan, execution_policy=engine.execution_policy_identity(plan.plan_id)
        )
        engine._plan_id = plan.plan_id
        engine._phase = EnginePhase.PLAN_INITIALIZED
        engine.authenticate_chain()

        domain = QueryDomain(
            start_block=LATE_BIRTH,
            end_block=LATE_BIRTH + 50,
            addresses=(POOL,),
            topics=ORDERED_EVENT_TOPICS,
        )
        time.sleep(0.05)
        conn = sqlite3.connect(store.db, timeout=10)
        try:
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute(f"DELETE FROM {NODE_TABLE} WHERE plan_id = ?", (plan.plan_id,))
            node = QueryNode(plan_id=plan.plan_id, domain=domain, status="PENDING")
            conn.execute(
                f"INSERT INTO {NODE_TABLE} (plan_id, domain_id, start_block, end_block, "
                "addresses_json, topics_json, status, parent_domain_id, split_reason, "
                "attempt, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    node.plan_id,
                    node.domain_id,
                    domain.start_block,
                    domain.end_block,
                    _canonical_json(list(domain.addresses)),
                    _canonical_json(list(domain.topics)),
                    "PENDING",
                    None,
                    None,
                    0,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        outcome = engine.process_one()
        assert outcome == "split:block_range_limit"
        counts = engine.coordinator.count_by_status(plan.plan_id)
        assert counts.get("SPLIT") == 1
        assert counts.get("PENDING", 0) >= 2
    finally:
        engine.close()


def test_run_until_idle_and_stop(store: Store, rpc: RpcFixture) -> None:
    rpc.set_empty_logs()
    engine = _engine(store, rpc, max_nodes_in_flight=1)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()
        root = plan.root_filters[0]
        rpc.headers[root.domain.end_block] = _header_result(
            block_number=root.domain.end_block
        )
        metrics = engine.run_until_idle()
        assert metrics.agreed == 1
        assert engine.process_one() is None
        engine.request_stop()
        assert engine.process_one() is None
        assert metrics.persistence_queue_high_water >= 0
    finally:
        engine.close()


def test_source_id_is_v2() -> None:
    assert SOURCE_ID.endswith("_v2")
    assert "pair_events" in SOURCE_ID


# ---------------------------------------------------------------------------
# Focused engine tests for 0018 authorization corrections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "setting, value",
    [
        ("http_timeout_seconds", 30.0),
        ("command_offer_timeout_seconds", 30.0),
    ],
)
def test_immutable_policy_resume_rejects_changed_settings(
    store: Store, rpc: RpcFixture, setting: str, value: float
) -> None:
    """Same-plan resume must match the stored execution policy exactly.

    The second engine uses the same plan but a changed runtime setting; the
    stored policy row is never mutated. Initialization must reject the drift.
    """
    engine = _engine(store, rpc)
    resumed: PairEventV2Engine | None = None
    try:
        pools = [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        plan = engine.initialize(pools)
        engine.authenticate_chain()
        stored = store.query(
            f"SELECT identity_payload_json FROM {EXECUTION_POLICY_TABLE} "
            "WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert len(stored) == 1
        engine.close()

        resumed = _engine(store, rpc, **{setting: value})
        with pytest.raises(PairEventV2Error, match="execution policy mismatch"):
            resumed.initialize(pools)

        # The stored policy row is byte-identical to the original identity.
        after = store.query(
            f"SELECT identity_payload_json FROM {EXECUTION_POLICY_TABLE} "
            "WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert after[0]["identity_payload_json"] == stored[0]["identity_payload_json"]
    finally:
        engine.close()
        if resumed is not None:
            resumed.close()


def test_heartbeat_servicing_during_streaming_persistence(
    store: Store, rpc: RpcFixture
) -> None:
    """Heartbeat (control queue) is serviced during streamed raw writes via pulse.

    A real claim owns the lease. A multi-chunk spool stream is held behind
    thread events: the persistence thread consumes the first chunk and then
    blocks. renew_lease is enqueued while the stream is blocked, one chunk is
    released, and the renewal must complete and advance ``expires_at`` before
    the persistence future finishes.
    """
    engine = _engine(store, rpc, lease_ttl_seconds=3600.0)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()

        claim = engine.coordinator.claim_pending(
            plan_id=plan.plan_id,
            worker_id="worker-a",
            lease_ttl_seconds=3600.0,
        )
        assert claim is not None

        lease_before = store.query(
            "SELECT leased_at, expires_at FROM uniswap_v2_pair_event_v2_query_lease "
            "WHERE plan_id = ? AND domain_id = ?",
            (claim.plan_id, claim.domain_id),
        )
        assert len(lease_before) == 1

        big_payload = b"x" * (64 * 1024 * 3)  # 3 chunks
        spool_path = store.spool_dir / "heartbeat_stream.bin"
        spool_path.write_bytes(big_payload)

        descriptor = SpoolDescriptor(
            provider_org="primary",
            request_json=_canonical_json(
                {"jsonrpc": "2.0", "id": 1, "method": "eth_getLogs", "params": []}
            ),
            acquired_at=datetime.now(UTC),
            status_code=200,
            spool_path=spool_path,
            response_started=True,
            response_bytes=len(big_payload),
            retained_bytes=len(big_payload),
            truncated=False,
            error_kind=None,
            error_detail=None,
        )

        reached_gate = threading.Event()
        allow_next_chunk = threading.Event()
        allow_eof = threading.Event()

        def _gated_spool_chunks(path: Path, *, pulse=None):
            """Replay the real chunk loop but hold the stream on thread events."""
            body = Path(path).read_bytes()
            chunks = [body[i : i + 64 * 1024] for i in range(0, len(body), 64 * 1024)]
            for index, chunk in enumerate(chunks):
                if index == 1:
                    reached_gate.set()
                    if not allow_next_chunk.wait(timeout=30.0):
                        raise RuntimeError("heartbeat chunk gate timed out")
                if pulse is not None:
                    pulse()
                yield chunk
            if not allow_eof.wait(timeout=30.0):
                raise RuntimeError("heartbeat EOF gate timed out")

        engine.coordinator._spool_chunks = _gated_spool_chunks
        envelope = engine.coordinator.persist_async(descriptor)

        assert reached_gate.wait(timeout=30.0)
        assert not envelope.done()

        renew_result: dict[str, bool] = {}
        renew_error: list[BaseException] = []

        def _renew() -> None:
            try:
                renew_result["value"] = engine.coordinator.renew_lease(
                    claim, lease_ttl_seconds=3600.0
                )
            except BaseException as exc:  # pragma: no cover - failure path
                renew_error.append(exc)

        renew_thread = threading.Thread(target=_renew)
        renew_thread.start()
        allow_next_chunk.set()
        renew_thread.join(timeout=30.0)
        assert not renew_thread.is_alive()
        assert not renew_error
        assert renew_result == {"value": True}

        lease_after = store.query(
            "SELECT expires_at FROM uniswap_v2_pair_event_v2_query_lease "
            "WHERE plan_id = ? AND domain_id = ?",
            (claim.plan_id, claim.domain_id),
        )
        assert lease_after[0]["expires_at"] > lease_before[0]["expires_at"]

        assert not envelope.done()
        allow_eof.set()
        envelope.result(timeout=30.0)

        assert not spool_path.exists()
        raw_records = store.query(
            "SELECT raw_object_id FROM raw_object WHERE byte_size > 0"
        )
        assert len(raw_records) >= 1
    finally:
        engine.close()


def test_lease_expired_terminal_receipt_persisted(
    store: Store, rpc: RpcFixture
) -> None:
    """Lease expiry at max attempts creates a terminal receipt with correct mode."""
    engine = _engine(store, rpc, max_attempts=2, lease_ttl_seconds=0.05)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()

        # Claim and let lease expire at max attempts
        claim = engine.coordinator.claim_pending(
            plan_id=plan.plan_id,
            worker_id="worker-a",
            lease_ttl_seconds=0.05,
        )
        assert claim is not None
        assert claim.attempt == 0

        # Force lease expiry + set attempt to max - 1 (so next expiry hits max)
        leased = (datetime.now(UTC) - timedelta(seconds=60)).isoformat()
        expired_at = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()
        conn = sqlite3.connect(store.db)
        try:
            conn.execute(
                "UPDATE uniswap_v2_pair_event_v2_query_lease "
                "SET leased_at = ?, expires_at = ?",
                (leased, expired_at),
            )
            conn.execute(
                f"UPDATE {NODE_TABLE} SET attempt = 1 WHERE plan_id = ?",
                (plan.plan_id,),
            )
            conn.commit()
        finally:
            conn.close()

        # Claim path expires leases → at max attempts → terminal receipt persisted,
        # no new claim returned (node is now terminal).
        reclaimed = engine.coordinator.claim_pending(
            plan_id=plan.plan_id,
            worker_id="worker-b",
            lease_ttl_seconds=60.0,
        )
        assert reclaimed is None

        # Verify terminal receipt exists with correct mode and attempt
        terminals = store.query(
            f"SELECT * FROM {TERMINAL_RECEIPT_TABLE} WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert len(terminals) == 1
        assert terminals[0]["terminal_mode"] == "lease_expired"
        assert int(terminals[0]["attempt"]) == 2

        # Verify terminal_receipt_id is content-addressed
        expected_id = compute_terminal_receipt_id(
            plan_id=plan.plan_id,
            domain_id=terminals[0]["domain_id"],
            terminal_mode="lease_expired",
            attempt=2,
        )
        assert terminals[0]["terminal_receipt_id"] == expected_id
    finally:
        engine.close()


def test_ordinary_terminal_receipt_on_internal_failure(
    store: Store, rpc: RpcFixture
) -> None:
    """Internal failure at max attempts creates a terminal receipt via process_one.

    An unexpected exception inside the claimed processing path routes INTERNAL
    through process_one (never a direct terminalize call) and persists one
    durable terminal receipt with exact mode, attempt, domain, and recomputed ID.
    """
    engine = _engine(store, rpc, max_attempts=1)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()

        def _boom(claim: Claim, block_number: int):
            raise RuntimeError("unexpected header failure")

        engine._get_header = _boom  # type: ignore[assignment]
        outcome = engine.process_one()
        assert outcome == "terminal:internal"
        assert engine.metrics.terminal_blockers == 1

        claim = store.query(
            f"SELECT domain_id FROM {NODE_TABLE} WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert len(claim) == 1
        domain_id = claim[0]["domain_id"]
        terminals = store.query(
            f"SELECT * FROM {TERMINAL_RECEIPT_TABLE} WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert len(terminals) == 1
        assert terminals[0]["terminal_mode"] == "internal"
        assert int(terminals[0]["attempt"]) == 1  # max_attempts
        assert terminals[0]["domain_id"] == domain_id
        expected_id = compute_terminal_receipt_id(
            plan_id=plan.plan_id,
            domain_id=domain_id,
            terminal_mode="internal",
            attempt=1,
        )
        assert terminals[0]["terminal_receipt_id"] == expected_id

        assert engine.coordinator.count_by_status(plan.plan_id)["TERMINAL_BLOCKER"] == 1
    finally:
        engine.close()


def test_unsplittable_terminal_receipt_persisted(
    store: Store, rpc: RpcFixture
) -> None:
    """Unsplittable failure (single-address domain that exceeds log limit) creates terminal receipt."""
    engine = _engine(store, rpc, max_log_count=1)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()

        # Replace root with a 1-address singleton domain (cannot split by address)
        conn = sqlite3.connect(store.db, timeout=10)
        try:
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute(f"DELETE FROM {NODE_TABLE} WHERE plan_id = ?", (plan.plan_id,))

            # Single-block, single-address domain → cannot split any way
            domain = QueryDomain(
                start_block=LATE_BIRTH,
                end_block=LATE_BIRTH,
                addresses=(POOL,),
                topics=ORDERED_EVENT_TOPICS,
            )
            node = QueryNode(plan_id=plan.plan_id, domain=domain, status="PENDING")
            conn.execute(
                f"INSERT INTO {NODE_TABLE} (plan_id, domain_id, start_block, end_block, "
                "addresses_json, topics_json, status, parent_domain_id, split_reason, "
                "attempt, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    node.plan_id,
                    node.domain_id,
                    domain.start_block,
                    domain.end_block,
                    _canonical_json(list(domain.addresses)),
                    _canonical_json(list(domain.topics)),
                    "PENDING",
                    None,
                    None,
                    0,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        # Both unique logs AND the required header are at the singleton's exact block.
        rpc.logs = [
            _swap_log(block_number=LATE_BIRTH, log_index=0),
            _swap_log(
                block_number=LATE_BIRTH,
                log_index=1,
                tx_hash="0x" + "ee" * 32,
                block_hash="0x" + "ab" * 32,
            ),
        ]
        rpc.headers[LATE_BIRTH] = _header_result(block_number=LATE_BIRTH)
        outcome = engine.process_one()
        assert outcome == "terminal:unsplittable_singleton"

        claim = store.query(
            f"SELECT domain_id FROM {NODE_TABLE} WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert len(claim) == 1
        domain_id = claim[0]["domain_id"]
        terminals = store.query(
            f"SELECT * FROM {TERMINAL_RECEIPT_TABLE} WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert len(terminals) == 1
        assert terminals[0]["terminal_mode"] == "unsplittable_singleton"
        assert int(terminals[0]["attempt"]) == engine.config.max_attempts
        assert terminals[0]["domain_id"] == domain_id
        expected_id = compute_terminal_receipt_id(
            plan_id=plan.plan_id,
            domain_id=domain_id,
            terminal_mode="unsplittable_singleton",
            attempt=engine.config.max_attempts,
        )
        assert terminals[0]["terminal_receipt_id"] == expected_id
    finally:
        engine.close()


def test_progressed_split_children_resolve_winner_matches_split_node(
    store: Store, rpc: RpcFixture
) -> None:
    """SPLIT winner resolution authenticates a progressed child against split_node.

    Commit a parent SPLIT through process_one, progress one exact child to
    IN_FLIGHT, call the parent's resolve_winner(split_reason=...), and compare
    every child ID, parent, bounds, addresses, topics, and reason to the
    versioned split_node partition.
    """
    engine = _engine(store, rpc, max_log_count=1)
    try:
        plan = build_acquisition_plan_v2(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)],
            PlanConfig(),
        )
        engine.coordinator.initialize_plan(
            plan, execution_policy=engine.execution_policy_identity(plan.plan_id)
        )
        engine._plan_id = plan.plan_id
        engine._phase = EnginePhase.PLAN_INITIALIZED
        engine.authenticate_chain()

        domain = QueryDomain(
            start_block=LATE_BIRTH,
            end_block=LATE_BIRTH + 10,
            addresses=tuple(sorted([POOL, POOL_B])),
            topics=ORDERED_EVENT_TOPICS,
        )
        time.sleep(0.05)
        conn = sqlite3.connect(store.db, timeout=10)
        try:
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute(f"DELETE FROM {NODE_TABLE} WHERE plan_id = ?", (plan.plan_id,))
            node = QueryNode(plan_id=plan.plan_id, domain=domain, status="PENDING")
            conn.execute(
                f"INSERT INTO {NODE_TABLE} (plan_id, domain_id, start_block, end_block, "
                "addresses_json, topics_json, status, parent_domain_id, split_reason, "
                "attempt, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    node.plan_id,
                    node.domain_id,
                    domain.start_block,
                    domain.end_block,
                    _canonical_json(list(domain.addresses)),
                    _canonical_json(list(domain.topics)),
                    "PENDING",
                    None,
                    None,
                    0,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        rpc.logs = [
            _swap_log(block_number=LATE_BIRTH + 1, log_index=0),
            _swap_log(block_number=LATE_BIRTH + 1, log_index=1, tx_hash="0x" + "ee" * 32),
        ]
        outcome = engine.process_one()
        assert outcome == "split:oversized_result"

        # Parent is durably SPLIT with the exact reason.
        parent_rows = store.query(
            f"SELECT status, split_reason FROM {NODE_TABLE} "
            "WHERE plan_id = ? AND domain_id = ?",
            (plan.plan_id, node.domain_id),
        )
        assert len(parent_rows) == 1
        assert parent_rows[0]["status"] == "SPLIT"
        assert parent_rows[0]["split_reason"] == "oversized_result"

        # Progress one exact child to IN_FLIGHT (real claim + lease).
        child_claim = engine.coordinator.claim_pending(
            plan_id=plan.plan_id,
            worker_id="worker-a",
            lease_ttl_seconds=60.0,
        )
        assert child_claim is not None
        assert child_claim.attempt == 0
        child_row = store.query(
            f"SELECT status FROM {NODE_TABLE} WHERE plan_id = ? AND domain_id = ?",
            (plan.plan_id, child_claim.domain_id),
        )
        assert child_row[0]["status"] == "IN_FLIGHT"

        # Winner resolution on the parent with the exact split reason.
        parent_node = QueryNode(
            plan_id=plan.plan_id,
            domain=domain,
            status="SPLIT",
        )
        parent_claim = Claim(
            plan_id=plan.plan_id,
            domain_id=node.domain_id,
            worker_id="worker-a",
            lease_token="winner-token",
            attempt=0,
            node=parent_node,
        )
        assert (
            engine.coordinator.resolve_winner(parent_claim, split_reason="oversized_result")
            == "split_winner"
        )

        # Compare every child to the versioned split_node partition.
        expected = split_node(parent_node, reason="oversized_result")
        rows = store.query(
            f"SELECT * FROM {NODE_TABLE} WHERE plan_id = ? AND parent_domain_id = ?",
            (plan.plan_id, node.domain_id),
        )
        assert {row["domain_id"] for row in rows} == {
            child.domain_id for child in expected
        }
        by_id = {row["domain_id"]: row for row in rows}
        for child in expected:
            row = by_id[child.domain_id]
            assert row["parent_domain_id"] == node.domain_id
            assert row["split_reason"] == "oversized_result"
            assert int(row["start_block"]) == child.domain.start_block
            assert int(row["end_block"]) == child.domain.end_block
            assert row["addresses_json"] == _canonical_json(
                list(child.domain.addresses)
            )
            assert row["topics_json"] == _canonical_json(list(child.domain.topics))
        inflight = [row for row in rows if row["status"] == "IN_FLIGHT"]
        assert len(inflight) == 1
        assert inflight[0]["domain_id"] == child_claim.domain_id
        assert int(inflight[0]["attempt"]) == 0
    finally:
        engine.close()


def test_atomic_retry_rolls_back_on_event_conflict(
    store: Store, rpc: RpcFixture
) -> None:
    """release_retry is atomic: on event insertion conflict, attempt and lease are unchanged.

    _insert_event handles PK conflicts as deduplication: if the existing record
    matches (except created_at), it is silenced. If it diverges (different
    decision, failure_class, etc.), it raises PairEventV2Error. We verify that
    when this error fires mid-transaction, the entire release_retry transaction
    rolls back — attempt must NOT increment and lease must NOT be deleted.
    """
    engine = _engine(store, rpc)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()

        claim = engine.coordinator.claim_pending(
            plan_id=plan.plan_id,
            worker_id="worker-a",
            lease_ttl_seconds=60.0,
        )
        assert claim is not None
        assert claim.attempt == 0

        # Pre-insert an event with the SAME event_id but DIFFERENT decision.
        # release_retry will try to insert an event with the same event_id but
        # matching decision → the pre-inserted divergent record triggers the
        # "divergent identity payload" error during deduplication.
        existing_event = make_engine_event_record(
            plan_id=plan.plan_id,
            domain_id=claim.domain_id,
            attempt=0,
            event_kind="retry_decision",
            failure_class=FailureClass.TRANSPORT,
            decision="retry",
            request={"jsonrpc": "2.0", "id": 1, "method": "eth_getLogs", "params": []},
            detail={"reason": "conflict_test"},
        )

        # Pre-insert the event with a different decision to trigger divergence
        conn = sqlite3.connect(str(store.db))
        conn.row_factory = sqlite3.Row
        try:
            conn.execute(
                f"INSERT INTO {ENGINE_EVENT_TABLE} ({','.join(ENGINE_EVENT_RECORD_COLUMNS)}) "
                f"VALUES ({','.join('?' for _ in ENGINE_EVENT_RECORD_COLUMNS)})",
                (
                    existing_event.event_id,
                    existing_event.schema_version,
                    existing_event.plan_id,
                    existing_event.domain_id,
                    existing_event.attempt,
                    existing_event.event_kind,
                    existing_event.failure_class,
                    "terminal",  # DIFFERENT decision from the event below
                    existing_event.provider_org,
                    existing_event.request_json,
                    existing_event.primary_raw_object_id,
                    existing_event.secondary_raw_object_id,
                    existing_event.primary_acquisition_id,
                    existing_event.secondary_acquisition_id,
                    existing_event.detail_json,
                    existing_event.created_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        # release_retry tries to insert the same event_id. _insert_event catches
        # the PK conflict, fetches the existing row, compares payloads, and raises
        # PairEventV2Error ("divergent identity payload") because the pre-inserted
        # decision was "terminal" while the event's decision is "retry".
        # The surrounding BEGIN IMMEDIATE / ROLLBACK in _op_release_retry ensures
        # the attempt increment and lease deletion are rolled back.
        with pytest.raises(PairEventV2Error, match="divergent identity|does not match"):
            engine.coordinator.release_retry(claim, events=[existing_event])

        # Verify the entire transaction rolled back: node stays IN_FLIGHT with
        # attempt unchanged, and the exact lease remains.
        after = store.query(
            f"SELECT attempt, status FROM {NODE_TABLE} WHERE plan_id = ? AND domain_id = ?",
            (claim.plan_id, claim.domain_id),
        )
        assert len(after) == 1
        assert after[0]["attempt"] == 0  # unchanged — rolled back
        assert after[0]["status"] == "IN_FLIGHT"  # unchanged — rolled back

        leases = store.query(
            "SELECT lease_token, worker_id, expires_at "
            "FROM uniswap_v2_pair_event_v2_query_lease "
            "WHERE plan_id = ? AND domain_id = ?",
            (claim.plan_id, claim.domain_id),
        )
        assert len(leases) == 1  # lease still present — rolled back
        assert leases[0]["lease_token"] == claim.lease_token  # exact lease
        assert leases[0]["worker_id"] == claim.worker_id
        assert datetime.fromisoformat(leases[0]["expires_at"]) > datetime.now(UTC)  # live lease

        # The pre-existing conflicting event is byte-identical after the
        # rollback: every stored column matches the original record.
        stored = store.query(
            f"SELECT {','.join(ENGINE_EVENT_RECORD_COLUMNS)} FROM {ENGINE_EVENT_TABLE} "
            "WHERE plan_id = ? AND domain_id = ?",
            (claim.plan_id, claim.domain_id),
        )
        assert len(stored) == 1
        row = stored[0]
        assert row["event_id"] == existing_event.event_id
        assert row["schema_version"] == existing_event.schema_version
        assert row["decision"] == "terminal"  # divergent decision preserved
        assert row["detail_json"] == existing_event.detail_json
        assert row["request_json"] == existing_event.request_json
    finally:
        engine.close()


def test_failure_route_precedence_exact_tuple() -> None:
    """FAILURE_ROUTE_PRECEDENCE equals the exact accepted precedence tuple.

    Routing order is acceptance-critical: transport must outrank size classes
    and provider disagreement must come after header conflicts. The tuple must
    match exactly, not merely share the same element set.
    """
    assert FAILURE_ROUTE_PRECEDENCE == (
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


def test_post_lease_winner_mode_mismatch_rejected(
    store: Store, rpc: RpcFixture
) -> None:
    """Post-lease winner resolution rejects mode mismatch."""
    engine = _engine(store, rpc, max_attempts=2)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()

        claim = engine.coordinator.claim_pending(
            plan_id=plan.plan_id,
            worker_id="worker-a",
            lease_ttl_seconds=60.0,
        )
        assert claim is not None

        terminal_event = make_engine_event_record(
            plan_id=plan.plan_id,
            domain_id=claim.domain_id,
            attempt=1,
            event_kind="terminal_blocker",
            failure_class=FailureClass.TRANSPORT,
            decision="terminal",
            request={"jsonrpc": "2.0", "id": 1, "method": "eth_getLogs", "params": []},
            detail={"reason": "transport"},
        )
        engine.coordinator.terminalize(
            claim,
            [terminal_event],
            terminal_mode="transport",
        )

        # Resolve winner with different mode → must reject
        fake_claim = Claim(
            plan_id=plan.plan_id,
            domain_id=claim.domain_id,
            worker_id="worker-a",
            lease_token=claim.lease_token,
            attempt=1,
            node=claim.node,
        )
        with pytest.raises(PairEventV2Error, match="mode mismatch"):
            engine.coordinator.resolve_winner(fake_claim, terminal_mode="internal")
    finally:
        engine.close()


def test_post_lease_winner_attempt_mismatch_rejected(
    store: Store, rpc: RpcFixture
) -> None:
    """Post-lease winner resolution authenticates terminal receipt attempt == max."""
    engine = _engine(store, rpc, max_attempts=3)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()

        claim = engine.coordinator.claim_pending(
            plan_id=plan.plan_id,
            worker_id="worker-a",
            lease_ttl_seconds=60.0,
        )
        assert claim is not None

        terminal_event = make_engine_event_record(
            plan_id=plan.plan_id,
            domain_id=claim.domain_id,
            attempt=0,
            event_kind="terminal_blocker",
            failure_class=FailureClass.TRANSPORT,
            decision="terminal",
            request={"jsonrpc": "2.0", "id": 1, "method": "eth_getLogs", "params": []},
            detail={"reason": "transport"},
        )
        engine.coordinator.terminalize(
            claim,
            [terminal_event],
            terminal_mode="transport",
        )

        # Tamper with terminal receipt attempt to simulate mismatch
        conn = sqlite3.connect(store.db)
        try:
            conn.execute(
                f"UPDATE {TERMINAL_RECEIPT_TABLE} SET attempt = 2 WHERE plan_id = ?",
                (plan.plan_id,),
            )
            conn.commit()
        finally:
            conn.close()

        with pytest.raises(PairEventV2Error, match="attempt must equal"):
            engine.coordinator.resolve_winner(claim, terminal_mode="transport")
    finally:
        engine.close()


def test_early_loss_route_failure_mode_mismatch(
    store: Store, rpc: RpcFixture
) -> None:
    """_route_failure on a lost lease detects terminal winner mode mismatch.

    Seed a durable terminal winner with mode 'transport' (via claim-bound
    terminalize). Force ``_lease_lost`` true, then call ``_route_failure`` with
    a different max-attempt candidate (mode 'persistence'). The candidate's
    failure and terminal_blocker events are durably inserted before resolve_winner
    rejects the winner-mode mismatch. This executes ``_route_failure``, never a
    direct resolve_winner call.
    """
    engine = _engine(store, rpc, max_attempts=3)
    try:
        plan = engine.initialize(
            [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        )
        engine.authenticate_chain()

        live = engine.coordinator.claim_pending(
            plan_id=plan.plan_id,
            worker_id="worker-a",
            lease_ttl_seconds=60.0,
        )
        assert live is not None

        # Durable terminal winner: mode 'transport' at max attempts.
        transport_event = make_engine_event_record(
            plan_id=plan.plan_id,
            domain_id=live.domain_id,
            attempt=0,
            event_kind="terminal_blocker",
            failure_class=FailureClass.TRANSPORT,
            decision="terminal",
            request={"jsonrpc": "2.0", "id": 1, "method": "eth_getLogs", "params": []},
            detail={"reason": "transport"},
        )
        engine.coordinator.terminalize(
            live, [transport_event], terminal_mode="transport"
        )

        # Lost-lease candidate at max attempts with a different terminal mode.
        candidate = Claim(
            plan_id=plan.plan_id,
            domain_id=live.domain_id,
            worker_id="worker-b",
            lease_token="never-active-token",
            attempt=engine.config.max_attempts,
            node=QueryNode(
                plan_id=plan.plan_id,
                domain=live.node.domain,
                status="PENDING",
            ),
        )
        work = _ActiveWork(candidate)
        work.lost.set()
        with engine._active_lock:
            engine._active_by_token[candidate.lease_token] = work
        assert engine._lease_lost(candidate)

        failure = _PairFailure(
            [_FailureFact(FailureClass.PERSISTENCE, None, {"stage": "leaf"})]
        )
        with pytest.raises(PairEventV2Error, match="mode mismatch"):
            engine._route_failure(
                candidate,
                failure,
                request_for_domain(candidate.node.domain),
                allow_split=False,
            )

        # Failure observations and the candidate terminal_blocker event are
        # durably inserted even though winner resolution rejects the mismatch.
        events = store.query(
            f"SELECT failure_class, event_kind, decision FROM {ENGINE_EVENT_TABLE} "
            "WHERE plan_id = ? AND domain_id = ?",
            (plan.plan_id, live.domain_id),
        )
        assert any(
            e["event_kind"] == "failure"
            and e["failure_class"] == FailureClass.PERSISTENCE.value
            for e in events
        )
        assert any(
            e["event_kind"] == "terminal_blocker"
            and e["failure_class"] == FailureClass.PERSISTENCE.value
            and e["decision"] == "terminal"
            for e in events
        )

        # Seeded transport winner receipt is untouched.
        receipts = store.query(
            f"SELECT terminal_mode FROM {TERMINAL_RECEIPT_TABLE} "
            "WHERE plan_id = ? AND domain_id = ?",
            (plan.plan_id, live.domain_id),
        )
        assert len(receipts) == 1
        assert receipts[0]["terminal_mode"] == "transport"
    finally:
        engine.close()


def test_terminal_receipt_content_addressed_identity(store: Store, rpc: RpcFixture) -> None:
    """Terminal receipt ID is deterministically content-addressed."""
    mode = "explicit_range_limit"
    attempt = 3
    plan_id = "plan_" + "a" * 64
    domain_id = "qd_" + "b" * 64
    receipt_id = compute_terminal_receipt_id(
        plan_id=plan_id,
        domain_id=domain_id,
        terminal_mode=mode,
        attempt=attempt,
    )
    assert receipt_id.startswith("term_")
    assert len(receipt_id) == 5 + 64  # "term_" + 64-char sha256

    # Same inputs produce same ID
    receipt_id_2 = compute_terminal_receipt_id(
        plan_id=plan_id,
        domain_id=domain_id,
        terminal_mode=mode,
        attempt=attempt,
    )
    assert receipt_id_2 == receipt_id

    # Different mode produces different ID
    receipt_id_diff = compute_terminal_receipt_id(
        plan_id=plan_id,
        domain_id=domain_id,
        terminal_mode="internal",
        attempt=attempt,
    )
    assert receipt_id_diff != receipt_id


# ---------------------------------------------------------------------------
# Crash recovery (spool journaling) — 0019 authorization corrections
# ---------------------------------------------------------------------------


def _crash_request() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getLogs",
        "params": [
            {
                "address": POOL,
                "fromBlock": hex(LATE_BIRTH),
                "toBlock": hex(LATE_BIRTH + 10),
            }
        ],
    }


def _write_crash_artifacts(
    store: Store,
    *,
    name: str,
    content: bytes | None = None,
    complete: bool = False,
    response_started: bool = True,
    response_bytes: int = 0,
    retained_bytes: int = 0,
    truncated: bool = False,
    status_code: int | None = None,
    error_kind: str | None = None,
    error_detail: str | None = None,
    provider_org: str = "infura",
    acquisition_id: str | None = None,
    request: dict[str, Any] | None = None,
) -> None:
    """Simulate a crashed worker's durable journal + spool on disk."""
    store.spool_dir.mkdir(parents=True, exist_ok=True)
    spool_path = store.spool_dir / f"{name}.spool"
    journal_path = store.spool_dir / f"{name}.spool.journal.json"
    if content is not None:
        spool_path.write_bytes(content)
    payload = {
        "acquired_at": datetime.now(UTC).isoformat(),
        "acquisition_id": acquisition_id,
        "complete": complete,
        "error_detail": error_detail,
        "error_kind": error_kind,
        "provider_org": provider_org,
        "request": request or _crash_request(),
        "reservation_id": "resv_" + name,
        "response_bytes": response_bytes,
        "response_started": response_started,
        "retained_bytes": retained_bytes,
        "schema_version": SPOOL_DESCRIPTOR_SCHEMA_VERSION,
        "spool_name": f"{name}.spool",
        "status_code": status_code,
        "truncated": truncated,
    }
    journal_path.write_text(json.dumps(payload))


def test_crash_recovery_complete_spool_persisted(store: Store, rpc: RpcFixture) -> None:
    """Crash after the full response was drained: journal + spool recover as evidence."""
    body = _rpc_ok({"logs": []})
    _write_crash_artifacts(
        store,
        name="crashed_complete",
        content=body,
        complete=True,
        response_started=True,
        response_bytes=len(body),
        retained_bytes=len(body),
        status_code=200,
        acquisition_id="acq_" + "a" * 64,
    )
    engine = _engine(store, rpc)
    try:
        raws = store.query(
            "SELECT acquisition_id, status FROM raw_acquisition "
            "WHERE acquisition_id = ?",
            ("acq_" + "a" * 64,),
        )
        assert len(raws) == 1
        assert raws[0]["status"] == "SUCCEEDED"
        objects = store.query("SELECT byte_size, sha256 FROM raw_object")
        assert len(objects) == 1
        assert objects[0]["byte_size"] == len(body)
        assert objects[0]["sha256"] == __import__("hashlib").sha256(body).hexdigest()
        assert list(store.spool_dir.glob("*.journal.json")) == []
        assert list(store.spool_dir.glob("*.spool")) == []
    finally:
        engine.close()


def test_crash_recovery_complete_truncated_uses_journaled_bytes(
    store: Store, rpc: RpcFixture
) -> None:
    """Complete+truncated crash: journaled response_bytes may exceed retained file bytes."""
    retained = b"partial-json"
    journaled_response = 5_000_000
    _write_crash_artifacts(
        store,
        name="crashed_truncated",
        content=retained,
        complete=True,
        response_started=True,
        response_bytes=journaled_response,
        retained_bytes=len(retained),
        truncated=True,
        status_code=200,
        acquisition_id="acq_" + "b" * 64,
    )
    engine = _engine(store, rpc)
    try:
        raws = store.query(
            "SELECT status, response_metadata_json FROM raw_acquisition "
            "WHERE acquisition_id = ?",
            ("acq_" + "b" * 64,),
        )
        assert len(raws) == 1
        assert raws[0]["status"] == "SUCCEEDED"
        metadata = json.loads(raws[0]["response_metadata_json"])
        assert metadata["response_bytes"] == journaled_response
        assert metadata["retained_bytes"] == len(retained)
        objects = store.query("SELECT byte_size, sha256 FROM raw_object")
        assert objects[0]["byte_size"] == len(retained)
        assert objects[0]["sha256"] == __import__("hashlib").sha256(retained).hexdigest()
        # Both the journal and the retained spool file are removed after recovery.
        assert list(store.spool_dir.glob("*.journal.json")) == []
        assert list(store.spool_dir.glob("*.spool")) == []
    finally:
        engine.close()


def test_crash_recovery_incomplete_spool_recorded_as_spool_incomplete(
    store: Store, rpc: RpcFixture
) -> None:
    """Crash mid-drain: incomplete spool is recovered as a non-authoritative failure."""
    body = b'{"jsonrpc":"2.0","id":1,"result":'  # cut off mid-write
    _write_crash_artifacts(
        store,
        name="crashed_mid_drain",
        content=body,
        complete=False,
        response_started=True,
        response_bytes=len(body),
        retained_bytes=len(body),
        status_code=200,
        acquisition_id="acq_" + "c" * 64,
    )
    engine = _engine(store, rpc)
    try:
        raws = store.query(
            "SELECT status, response_metadata_json FROM raw_acquisition "
            "WHERE acquisition_id = ?",
            ("acq_" + "c" * 64,),
        )
        assert len(raws) == 1
        assert raws[0]["status"] == "SUCCEEDED"
        metadata = json.loads(raws[0]["response_metadata_json"])
        assert metadata["error_kind"] == "spool_incomplete"
        assert list(store.spool_dir.glob("*.journal.json")) == []
        assert list(store.spool_dir.glob("*.spool")) == []
    finally:
        engine.close()


def test_crash_recovery_missing_spool_after_start_recorded_as_failed(
    store: Store, rpc: RpcFixture
) -> None:
    """Journal says a response started but the spool file is gone → failed acquisition."""
    _write_crash_artifacts(
        store,
        name="crashed_missing_spool",
        content=None,  # no spool file on disk
        complete=False,
        response_started=True,
        response_bytes=0,
        retained_bytes=0,
        status_code=None,
        acquisition_id="acq_" + "d" * 64,
    )
    engine = _engine(store, rpc)
    try:
        raws = store.query(
            "SELECT status, raw_object_id, response_metadata_json FROM raw_acquisition "
            "WHERE acquisition_id = ?",
            ("acq_" + "d" * 64,),
        )
        assert len(raws) == 1
        assert raws[0]["status"] == "FAILED"
        assert raws[0]["raw_object_id"] is None
        metadata = json.loads(raws[0]["response_metadata_json"])
        assert metadata["error_kind"] == "spool_missing_after_start"
        assert list(store.spool_dir.glob("*.journal.json")) == []
    finally:
        engine.close()


def test_crash_recovery_pre_start_reservation_freed(store: Store, rpc: RpcFixture) -> None:
    """A reservation with no response started is freed (journal + spool removed)."""
    _write_crash_artifacts(
        store,
        name="never_started",
        content=b"",
        complete=False,
        response_started=False,
        response_bytes=0,
        retained_bytes=0,
        status_code=None,
        acquisition_id="acq_" + "e" * 64,
    )
    engine = _engine(store, rpc)
    try:
        assert list(store.spool_dir.glob("*.journal.json")) == []
        assert list(store.spool_dir.glob("*.spool")) == []
        raws = store.query(
            "SELECT COUNT(*) AS n FROM raw_acquisition WHERE acquisition_id = ?",
            ("acq_" + "e" * 64,),
        )
        assert raws[0]["n"] == 0
    finally:
        engine.close()


def test_crash_recovery_malformed_journal_kept_for_capacity(
    store: Store, rpc: RpcFixture
) -> None:
    """An unreadable journal is never deleted while its spool is untracked."""
    store.spool_dir.mkdir(parents=True, exist_ok=True)
    (store.spool_dir / "response-corrupt.spool").write_bytes(b"x" * 16)
    (store.spool_dir / "response-corrupt.spool.journal.json").write_text(
        "{ not valid json !!"
    )
    engine = _engine(store, rpc)
    try:
        assert (store.spool_dir / "response-corrupt.spool").exists()
        assert (store.spool_dir / "response-corrupt.spool.journal.json").exists()
        raws = store.query("SELECT COUNT(*) AS n FROM raw_acquisition")
        assert raws[0]["n"] == 0
    finally:
        engine.close()


def test_crash_recovery_occupancy_overflow_fails_startup(store: Store) -> None:
    """Surviving occupancy beyond max_spool_files must fail startup loudly."""
    store.spool_dir.mkdir(parents=True, exist_ok=True)
    for i in range(9):
        name = f"response-survivor-{i}"
        (store.spool_dir / f"{name}.spool").write_bytes(b"x" * 4)
        (store.spool_dir / f"{name}.spool.journal.json").write_text("{ not json")
    coordinator = None
    try:
        with pytest.raises(PairEventV2Error, match="occupancy exceeds max_spool_files"):
            coordinator = __import__(
                "cryptofactors.acquisition.uniswap_v2_pair_events_v2_engine",
                fromlist=["PersistenceCoordinator"],
            ).PersistenceCoordinator(
                db_path=store.db,
                raw_root=store.raw_root,
                spool_dir=store.spool_dir,
                spool_capacity=threading.BoundedSemaphore(8),
                queue_size=64,
                offer_timeout_seconds=30.0,
                max_body_bytes=1_000_000,
                max_attempts=3,
                max_spool_files=8,
            )
    finally:
        if coordinator is not None:
            coordinator.close()


# ---------------------------------------------------------------------------
# Mixed-failure precedence — 0019 authorization corrections
# ---------------------------------------------------------------------------


def test_failure_route_precedence_is_full_deterministic_ordering() -> None:
    """FAILURE_ROUTE_PRECEDENCE must name every FailureClass exactly once."""
    assert len(FAILURE_ROUTE_PRECEDENCE) == len({c.value for c in FailureClass})
    assert set(FAILURE_ROUTE_PRECEDENCE) == {c.value for c in FailureClass}
    assert len(set(FAILURE_ROUTE_PRECEDENCE)) == len(FAILURE_ROUTE_PRECEDENCE)


def test_failure_route_precedence_429_beats_transport_and_size() -> None:
    failure = _PairFailure(
        [
            _FailureFact(FailureClass.BODY_SIZE_PRESSURE, "infura", {}),
            _FailureFact(FailureClass.TRANSPORT, "blockpi", {}),
            _FailureFact(FailureClass.HTTP_429, "infura", {}),
        ]
    )
    assert failure.route == FailureClass.HTTP_429


def test_failure_route_precedence_transport_before_size() -> None:
    failure = _PairFailure(
        [
            _FailureFact(FailureClass.RESULT_SIZE_PRESSURE, "infura", {}),
            _FailureFact(FailureClass.TRANSPORT, "blockpi", {}),
        ]
    )
    assert failure.route == FailureClass.TRANSPORT


def test_failure_route_precedence_auth_before_status_and_size() -> None:
    failure = _PairFailure(
        [
            _FailureFact(FailureClass.HTTP_STATUS, "infura", {}),
            _FailureFact(FailureClass.BODY_SIZE_PRESSURE, "infura", {}),
            _FailureFact(FailureClass.AUTHENTICATION, "blockpi", {}),
        ]
    )
    assert failure.route == FailureClass.AUTHENTICATION


def test_failure_route_precedence_range_limit_before_size() -> None:
    failure = _PairFailure(
        [
            _FailureFact(FailureClass.BODY_SIZE_PRESSURE, "infura", {}),
            _FailureFact(FailureClass.RESULT_SIZE_PRESSURE, "infura", {}),
            _FailureFact(FailureClass.EXPLICIT_RANGE_LIMIT, "blockpi", {}),
        ]
    )
    assert failure.route == FailureClass.EXPLICIT_RANGE_LIMIT


def test_failure_route_precedence_persistence_before_malformed_json() -> None:
    failure = _PairFailure(
        [
            _FailureFact(FailureClass.MALFORMED_JSON, "infura", {}),
            _FailureFact(FailureClass.PERSISTENCE, "blockpi", {}),
        ]
    )
    assert failure.route == FailureClass.PERSISTENCE


def test_failure_route_precedence_internal_is_last() -> None:
    failure = _PairFailure(
        [
            _FailureFact(FailureClass.INTERNAL, None, {"stage": "x"}),
            _FailureFact(FailureClass.RPC_ERROR, "infura", {}),
            _FailureFact(FailureClass.HEADER_CONFLICT, "infura", {}),
        ]
    )
    assert failure.route == FailureClass.RPC_ERROR


def _descriptor_envelope(
    *,
    org: str,
    status_code: int | None,
    error_kind: str | None = None,
    truncated: bool = False,
    response_bytes: int = 0,
) -> PersistedEnvelope:
    descriptor = SpoolDescriptor(
        provider_org=org,
        request_json=_canonical_json(_crash_request()),
        acquired_at=datetime.now(UTC),
        status_code=status_code,
        spool_path=None,
        response_started=True,
        response_bytes=response_bytes,
        retained_bytes=0,
        truncated=truncated,
        error_kind=error_kind,
        error_detail=None,
    )
    return PersistedEnvelope(descriptor, None, None, 0.0)


def test_inspect_pair_429_plus_oversized_routes_retry(store: Store, rpc: RpcFixture) -> None:
    """429 (retry) dominates body-size pressure (split) inside one response."""
    engine = _engine(store, rpc)
    try:
        pair = (
            _descriptor_envelope(org="infura", status_code=429, truncated=True),
            _descriptor_envelope(org="blockpi", status_code=200, error_kind="transport"),
        )
        with pytest.raises(_PairFailure) as exc:
            engine._inspect_pair(pair, _crash_request())
        assert exc.value.route == FailureClass.HTTP_429
    finally:
        engine.close()


def test_inspect_pair_auth_plus_oversized_routes_auth(store: Store, rpc: RpcFixture) -> None:
    """401/403 dominate both http_status and size pressure."""
    engine = _engine(store, rpc)
    try:
        pair = (
            _descriptor_envelope(org="infura", status_code=403, truncated=True),
            _descriptor_envelope(org="blockpi", status_code=500),
        )
        with pytest.raises(_PairFailure) as exc:
            engine._inspect_pair(pair, _crash_request())
        assert exc.value.route == FailureClass.AUTHENTICATION
    finally:
        engine.close()


def test_inspect_pair_transport_plus_persistence_routes_transport(
    store: Store, rpc: RpcFixture
) -> None:
    """Transport precedes persistence and size pressure."""
    engine = _engine(store, rpc)
    try:
        pair = (
            _descriptor_envelope(
                org="infura", status_code=200, error_kind="transport", truncated=True
            ),
            _descriptor_envelope(org="blockpi", status_code=200, error_kind="spool_io"),
        )
        with pytest.raises(_PairFailure) as exc:
            engine._inspect_pair(pair, _crash_request())
        assert exc.value.route == FailureClass.TRANSPORT
    finally:
        engine.close()


def test_inspect_pair_persistence_plus_malformed_routes_persistence(
    store: Store, rpc: RpcFixture
) -> None:
    """spool_incomplete (persistence) dominates a malformed/unparseable sibling."""
    engine = _engine(store, rpc)
    try:
        pair = (
            _descriptor_envelope(
                org="infura", status_code=200, error_kind="spool_incomplete"
            ),
            _descriptor_envelope(org="blockpi", status_code=200),
        )
        with pytest.raises(_PairFailure) as exc:
            engine._inspect_pair(pair, _crash_request())
        assert exc.value.route == FailureClass.PERSISTENCE
    finally:
        engine.close()


def test_inspect_pair_malformed_json_routes_before_status(
    store: Store, rpc: RpcFixture
) -> None:
    """A truly unparseable sibling outranks a plain non-2xx status."""
    engine = _engine(store, rpc)
    try:
        pair = (
            _descriptor_envelope(org="infura", status_code=502),
            _descriptor_envelope(org="blockpi", status_code=200),
        )
        with pytest.raises(_PairFailure) as exc:
            engine._inspect_pair(pair, _crash_request())
        assert exc.value.route == FailureClass.MALFORMED_JSON
    finally:
        engine.close()
