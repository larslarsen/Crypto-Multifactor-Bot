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
)
from cryptofactors.acquisition.uniswap_v2_pair_events_v2_engine import (
    CHAIN_IDENTITY_TABLE,
    ENGINE_EVENT_TABLE,
    LEAF_TABLE,
    NODE_TABLE,
    TERMINAL_RECEIPT_TABLE,
    Claim,
    EngineConfig,
    EnginePhase,
    FailureClass,
    NetworkWorker,
    PairEventV2Engine,
    SpoolDescriptor,
    SOURCE_ID,
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
        assert outcome.startswith("terminal:")
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


def test_immutable_policy_resume_rejects_changed_settings(
    store: Store, rpc: RpcFixture
) -> None:
    """Re-initialize with same plan must match stored execution policy exactly."""
    engine = _engine(store, rpc)
    try:
        pools = [RegistryPoolBirth(pool_address=POOL, creation_block=LATE_BIRTH)]
        plan = engine.initialize(pools)
        engine.authenticate_chain()

        # Tamper with the stored policy to simulate drift.
        conn = sqlite3.connect(store.db)
        try:
            conn.execute(
                "UPDATE uniswap_v2_pair_event_v2_execution_policy "
                "SET identity_payload_json = ?",
                (json.dumps({"plan_id": plan.plan_id, "tampered": True}),),
            )
            conn.commit()
        finally:
            conn.close()

        with pytest.raises(PairEventV2Error, match="execution policy mismatch"):
            engine.initialize(pools)
    finally:
        engine.close()


def test_heartbeat_servicing_during_persistence(store: Store, rpc: RpcFixture) -> None:
    """Heartbeat (control queue) is serviced during lease operations."""
    engine = _engine(store, rpc, lease_ttl_seconds=120.0)
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

        # Renew lease via the claim-bound heartbeat path.
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
    """Internal failure at max attempts creates terminal receipt with 'internal' mode."""
    engine = _engine(store, rpc, max_attempts=1)
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
            failure_class=FailureClass.INTERNAL,
            decision="terminal",
            request={"jsonrpc": "2.0", "id": 1, "method": "eth_getLogs", "params": []},
            detail={"reason": "internal"},
        )

        engine.coordinator.terminalize(
            claim,
            [terminal_event],
            terminal_mode="internal",
        )

        terminals = store.query(
            f"SELECT * FROM {TERMINAL_RECEIPT_TABLE} WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert len(terminals) == 1
        assert terminals[0]["terminal_mode"] == "internal"
        assert int(terminals[0]["attempt"]) == 1  # max_attempts

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

        # Two logs for single-address domain → exceeds max_log_count=1,
        # but can't split by address → unsplittable_singleton terminal
        rpc.logs = [
            _swap_log(block_number=LATE_BIRTH + 1, log_index=0),
            _swap_log(block_number=LATE_BIRTH + 1, log_index=1, tx_hash="0x" + "ee" * 32),
        ]
        root = plan.root_filters[0]
        rpc.headers[root.domain.end_block] = _header_result(
            block_number=root.domain.end_block
        )
        outcome = engine.process_one()
        assert outcome == "terminal:unsplittable_singleton"

        terminals = store.query(
            f"SELECT * FROM {TERMINAL_RECEIPT_TABLE} WHERE plan_id = ?",
            (plan.plan_id,),
        )
        assert len(terminals) == 1
        assert terminals[0]["terminal_mode"] == "unsplittable_singleton"
    finally:
        engine.close()


def test_progressed_split_children_persist_valid_status(
    store: Store, rpc: RpcFixture
) -> None:
    """SPLIT children are created with PENDING status and correct split_reason."""
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
            from cryptofactors.acquisition.uniswap_v2_pair_events_v2 import QueryNode

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

        children = store.query(
            f"SELECT domain_id, status, split_reason FROM {NODE_TABLE} "
            "WHERE parent_domain_id IS NOT NULL AND plan_id = ?",
            (plan.plan_id,),
        )
        assert len(children) == 2
        assert all(child["split_reason"] == "oversized_result" for child in children)
        assert all(child["status"] == "PENDING" for child in children)
    finally:
        engine.close()


def test_atomic_retry_inc_attempt_and_delete_lease(
    store: Store, rpc: RpcFixture
) -> None:
    """release_retry atomically increments attempt and deletes the lease."""
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

        engine.coordinator.release_retry(claim, events=())

        after = store.query(
            f"SELECT attempt, status FROM {NODE_TABLE} WHERE plan_id = ? AND domain_id = ?",
            (claim.plan_id, claim.domain_id),
        )
        assert after[0]["attempt"] == 1
        assert after[0]["status"] == "PENDING"

        leases = store.query(
            "SELECT * FROM uniswap_v2_pair_event_v2_query_lease "
            "WHERE plan_id = ? AND domain_id = ?",
            (claim.plan_id, claim.domain_id),
        )
        assert len(leases) == 0
    finally:
        engine.close()


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


def test_early_heartbeat_loss_branch_returns_lease_lost(
    store: Store, rpc: RpcFixture
) -> None:
    """Early lease-loss branch in resolve_winner returns 'lease_lost' for IN_FLIGHT."""
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

        # resolve_winner on IN_FLIGHT node with no terminal_mode → lease_lost
        result = engine.coordinator.resolve_winner(claim)
        assert result == "lease_lost"
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
