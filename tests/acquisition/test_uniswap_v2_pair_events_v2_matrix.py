"""DEX-003 — offline tests for the fresh-run v2 provider-matrix harness.

Public production paths via fake transports and temporary directories.
No network, no RPC credentials, no production data mutation.

Grok authors this suite; Jr executes it unchanged.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from cryptofactors.acquisition.uniswap_v2 import ETHEREUM_CHAIN, UNISWAP_V2_FACTORY
from cryptofactors.acquisition.uniswap_v2_pair_events import SYNC_TOPIC
from cryptofactors.acquisition.uniswap_v2_pair_events_v2 import (
    LOG_IDENTITY_VERSION,
    ORDERED_EVENT_TOPICS,
)
from cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix import (
    ANCHOR_POOL,
    BIRTH_BOUNDARY_BLOCK,
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_PROVIDER_ORGS,
    LOGICAL_CALL_CEILING,
    MATRIX_RANGES,
    MATRIX_SCHEMA_VERSION,
    NESTED_COHORT_SIZES,
    STREAM_CHUNK_BYTES,
    V1_ANCHOR_SWAP_LOG_COUNTS,
    BudgetTracker,
    CredentialScanner,
    LiveOutputLock,
    MatrixBudgets,
    MatrixConfig,
    MatrixError,
    MatrixPlan,
    MatrixRun,
    MatrixSafetyStop,
    PairEventV2MatrixHarness,
    TransportResult,
    _inventory_snapshot,
    _promote_raw,
    assert_safe_matrix_output_root,
    authenticate_completed_run,
    catalog_entries,
    compact_json_array_hash,
    compute_evidence_hash,
    compute_matrix_id_from_payload,
    compute_report_hash,
    evaluate_cells,
    fair_schedule_calls,
    iter_logical_calls,
    parse_json_rpc_result,
    select_capacity_from_cells,
)

_TEST_PRIMARY_RPC = "https://mainnet.infura.io/v3/SECRETprojectkey001"
_TEST_SECONDARY_RPC = "https://ethereum.blockpi.network/v1/rpc/SECRETblockpikey02"




def _synthetic_cohort() -> tuple[str, ...]:
    others = sorted(f"0x{i:040x}" for i in range(1, 200) if f"0x{i:040x}" != ANCHOR_POOL)
    return (ANCHOR_POOL,) + tuple(others[:127])


def _synthetic_plan() -> MatrixPlan:
    cohort = _synthetic_cohort()
    hashes = {s: compact_json_array_hash(cohort[:s]) for s in NESTED_COHORT_SIZES}
    draft = {
        "anchor_pool": ANCHOR_POOL,
        "birth_boundary_block": BIRTH_BOUNDARY_BLOCK,
        "chain": ETHEREUM_CHAIN,
        "factory": UNISWAP_V2_FACTORY.lower(),
        "log_identity_version": LOG_IDENTITY_VERSION,
        "logical_call_ceiling": LOGICAL_CALL_CEILING,
        "maximum_cohort": list(cohort),
        "nested_cohort_hashes": {str(k): hashes[k] for k in NESTED_COHORT_SIZES},
        "provider_orgs": list(DEFAULT_PROVIDER_ORGS),
        "ranges": {
            n: {"end": MATRIX_RANGES[n][1], "start": MATRIX_RANGES[n][0]}
            for n in ("sparse", "medium", "hot")
        },
        "registry_dataset_id": "ds_" + ("ab" * 32),
        "registry_parquet_bytes": 42,
        "registry_parquet_sha256": "cd" * 32,
        "schema_version": MATRIX_SCHEMA_VERSION,
        "topics": list(ORDERED_EVENT_TOPICS),
        "v1_anchor_swap_log_counts": {
            n: V1_ANCHOR_SWAP_LOG_COUNTS[n] for n in ("sparse", "medium", "hot")
        },
    }
    mid = compute_matrix_id_from_payload(draft)
    return MatrixPlan(
        matrix_id=mid,
        schema_version=MATRIX_SCHEMA_VERSION,
        registry_dataset_id=str(draft["registry_dataset_id"]),
        registry_parquet_sha256=str(draft["registry_parquet_sha256"]),
        registry_parquet_bytes=42,
        anchor_pool=ANCHOR_POOL,
        birth_boundary_block=BIRTH_BOUNDARY_BLOCK,
        maximum_cohort=cohort,
        nested_cohort_hashes=hashes,
        ranges=dict(MATRIX_RANGES),
        v1_anchor_swap_log_counts=dict(V1_ANCHOR_SWAP_LOG_COUNTS),
        provider_orgs=DEFAULT_PROVIDER_ORGS,
        topics=ORDERED_EVENT_TOPICS,
        log_identity_version=LOG_IDENTITY_VERSION,
        chain=ETHEREUM_CHAIN,
        factory=UNISWAP_V2_FACTORY.lower(),
        logical_call_ceiling=LOGICAL_CALL_CEILING,
        created_at="2026-01-01T00:00:00+00:00",
    )


def _chain_body() -> bytes:
    return b'{"jsonrpc":"2.0","id":1,"result":"0x1"}'


def _empty_logs() -> bytes:
    return b'{"jsonrpc":"2.0","id":1,"result":[]}'


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.call_log: list[tuple[str, str, int | None]] = []
        self.closed = False
        self.in_flight = 0
        self.high_water = 0
        self._lock = threading.Lock()
        self.hold: dict[str, threading.Event] = {}
        self.body_override: dict[str, bytes] = {}
        # If set, batched eth_getLogs with address list length >= N return capacity error.
        self.capacity_min_batch_addresses: int | None = None
        self.block_until: threading.Event | None = None
        self.entered: threading.Event | None = None

    def __call__(self, provider_org: str, request: Mapping[str, Any]) -> TransportResult:
        with self._lock:
            self.in_flight += 1
            self.high_water = max(self.high_water, self.in_flight)
        try:
            method = str(request.get("method"))
            addr_count: int | None = None
            if method == "eth_getLogs":
                params = request.get("params") or [{}]
                if isinstance(params, list) and params:
                    addr = params[0].get("address") if isinstance(params[0], Mapping) else None
                    if isinstance(addr, list):
                        addr_count = len(addr)
                    elif isinstance(addr, str):
                        addr_count = 1
            self.calls.append((provider_org, method))
            self.call_log.append((provider_org, method, addr_count))
            if self.entered is not None:
                self.entered.set()
            if self.block_until is not None:
                self.block_until.wait(timeout=60.0)
            hold = self.hold.get(provider_org)
            if hold is not None:
                hold.wait(timeout=5.0)
            key = f"{provider_org}:{method}"
            body = self.body_override.get(key)
            http_429 = False
            error_class = None
            if (
                body is None
                and method == "eth_getLogs"
                and self.capacity_min_batch_addresses is not None
                and addr_count is not None
                and addr_count >= self.capacity_min_batch_addresses
            ):
                body = (
                    b'{"jsonrpc":"2.0","id":1,"error":{"code":-32005,'
                    b'"message":"query returned more than 10000 results"}}'
                )
            if body is None:
                body = _chain_body() if method == "eth_chainId" else _empty_logs()
            return TransportResult(
                status_code=200,
                body=body,
                stream_response=None,
                latency_ms=0.05,
                http_429=http_429,
                error_class=error_class,
                error_detail=None,
            )
        finally:
            with self._lock:
                self.in_flight -= 1

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def plan() -> MatrixPlan:
    return _synthetic_plan()


@pytest.fixture
def out_root(tmp_path: Path) -> Path:
    root = tmp_path / "matrix_out"
    root.mkdir()
    return root


@pytest.fixture
def reg_root(tmp_path: Path) -> Path:
    r = tmp_path / "registry_store"
    r.mkdir()
    return r


def _patch_plan(monkeypatch: pytest.MonkeyPatch, plan: MatrixPlan) -> None:
    monkeypatch.setattr(
        "cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix.build_matrix_plan",
        lambda **_k: plan,
    )


def _seal_plan_only(out_root: Path, plan: MatrixPlan) -> dict[str, Any]:
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    report = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "matrix_id": plan.matrix_id,
        "mode": "plan_only",
        "complete": True,
        "pass": False,
        "plan": plan.to_public_dict(),
        "cells": [],
        "budgets": MatrixBudgets().as_dict(),
        "cumulative_counters": {
            "logical_calls_started": 0,
            "provider_attempts": 0,
            "retained_response_bytes": 0,
            "http_429_count": 0,
            "high_water_in_flight": 0,
        },
        "offline_replay": {"authenticated": False, "all_cells_pass": False},
        "credential_scan": "pass",
    }
    return run.seal(kind="COMPLETE", report=report)


# ---------------------------------------------------------------------------
# Catalog / pins
# ---------------------------------------------------------------------------


def test_logical_call_catalog_is_1568(plan: MatrixPlan) -> None:
    calls = iter_logical_calls(plan)
    assert len(calls) == LOGICAL_CALL_CEILING == 1568
    assert len(catalog_entries(plan)) == 1568
    assert sum(1 for c in calls if c.kind == "chain") == 2
    assert sum(1 for c in calls if c.kind == "scalar") == 1536
    assert sum(1 for c in calls if c.kind == "batch") == 30


def test_cohort_and_range_pins_on_plan(plan: MatrixPlan) -> None:
    assert plan.anchor_pool == ANCHOR_POOL
    assert plan.birth_boundary_block == BIRTH_BOUNDARY_BLOCK
    assert len(plan.maximum_cohort) == 128
    assert plan.maximum_cohort[0] == ANCHOR_POOL
    for size in NESTED_COHORT_SIZES:
        assert plan.nested_cohort_hashes[size] == compact_json_array_hash(
            plan.maximum_cohort[:size]
        )
    assert plan.ranges == MATRIX_RANGES
    assert plan.provider_orgs == DEFAULT_PROVIDER_ORGS


def test_catalog_request_json_exact_match(plan: MatrixPlan) -> None:
    for entry, call in zip(catalog_entries(plan), iter_logical_calls(plan), strict=True):
        assert entry["request_json"] == call.request_json()
        assert entry["logical_call_id"] == call.logical_call_id


# ---------------------------------------------------------------------------
# Full 1568-call fake live + standalone replay (single expensive production path)
# ---------------------------------------------------------------------------


def test_complete_fake_live_run_and_standalone_replay(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_plan(monkeypatch, plan)
    transport = FakeTransport()
    live_report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            provider_orgs=DEFAULT_PROVIDER_ORGS,
            # Ceilings may only lower from production defaults; max rps/in-flight
            # keeps fake-transport full-matrix runs offline-bounded.
            budgets=MatrixBudgets(
                max_in_flight=4,
                requests_per_second=8.0,
            ),
            primary_rpc_url=_TEST_PRIMARY_RPC,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                    confirm_matrix_id=plan.matrix_id,
            transport=transport,
        )
    ).run()
    assert live_report["status"] == "COMPLETE"
    assert live_report["complete"] is True
    assert live_report["pass"] is True
    assert live_report["all_cells_pass"] is True
    assert len(live_report["cells"]) == 15
    assert all(c["status"] == "pass" for c in live_report["cells"])
    assert live_report["capacity_selection"]["selection_valid"] is True
    assert live_report["capacity_selection"]["selected_cohort_size"] == 128
    assert len(transport.calls) == LOGICAL_CALL_CEILING
    assert transport.closed is True
    assert live_report["evidence_hash"] != live_report["report_hash"]
    run_dir = Path(live_report["run_dir"])
    assert (run_dir / "COMPLETE.json").is_file()
    assert not (run_dir / "FAILED.json").exists()
    cell0 = live_report["cells"][0]
    for side in ("primary", "secondary"):
        for key in (
            "attempts",
            "http_429s",
            "latency_ms_total",
            "response_bytes",
            "observed_body_bytes_total",
            "truncated_attempts",
            "status",
        ):
            assert key in cell0[side]
    # Exact range/cohort coverage in cells.
    assert {(c["range_name"], c["cohort_size"]) for c in live_report["cells"]} == {
        (r, s) for r in ("sparse", "medium", "hot") for s in NESTED_COHORT_SIZES
    }

    # Exact terminal metrics completeness.
    metrics = live_report["call_metrics"]
    assert metrics["per_call_count"] == LOGICAL_CALL_CEILING
    assert len(metrics["per_call"]) == LOGICAL_CALL_CEILING
    for entry in metrics["per_call"]:
        for key in (
            "logical_call_id",
            "kind",
            "provider_org",
            "attempts",
            "http_429s",
            "latency_ms_total",
            "response_bytes",
            "observed_body_bytes_total",
            "truncated_attempts",
            "status",
            "error_class",
            "last_status_code",
        ):
            assert key in entry
    for org in DEFAULT_PROVIDER_ORGS:
        prov = metrics["per_provider"][org]
        for key in (
            "attempts",
            "http_429s",
            "successes",
            "failures",
            "response_bytes",
            "observed_body_bytes",
            "truncated_attempts",
            "latency_ms_total",
        ):
            assert key in prov
        assert prov["attempts"] > 0
        assert prov["successes"] > 0

    before_inventory = _inventory_snapshot(run_dir)
    replay_out = out_root.parent / "replay_out"
    replay_out.mkdir()
    replay_report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=replay_out,
            mode="offline_replay",
            live_run_dir=run_dir,
        )
    ).run()
    assert replay_report["mode"] == "offline_replay"
    assert replay_report["live_report_authenticated"] is True
    assert replay_report["pass"] is True
    assert replay_report["run_id"] != live_report["run_id"]
    sealed = authenticate_completed_run(run_dir, require_live_pass=True)
    assert sealed["evidence_hash"] == live_report["evidence_hash"]
    # Full source inventory unchanged after standalone replay.
    assert _inventory_snapshot(run_dir) == before_inventory


# ---------------------------------------------------------------------------
# Terminal auth / immutability (plan-only sealed runs — public seal/auth paths)
# ---------------------------------------------------------------------------


def test_missing_extra_tampered_files_fail_auth(out_root: Path, plan: MatrixPlan) -> None:
    sealed = _seal_plan_only(out_root, plan)
    run_dir = Path(sealed["run_dir"])
    authenticate_completed_run(run_dir)  # baseline OK

    # Tamper plan bytes.
    plan_path = run_dir / "plan.json"
    obj = json.loads(plan_path.read_text())
    obj["registry_parquet_sha256"] = "ff" * 32
    plan_path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(MatrixSafetyStop, match="hash/bytes|evidence_hash|catalog"):
        authenticate_completed_run(run_dir)

    sealed2 = _seal_plan_only(out_root, plan)
    run2 = Path(sealed2["run_dir"])
    (run2 / "extra.txt").write_text("x", encoding="utf-8")
    with pytest.raises(MatrixSafetyStop, match="extra file"):
        authenticate_completed_run(run2)

    sealed3 = _seal_plan_only(out_root, plan)
    run3 = Path(sealed3["run_dir"])
    # Drop catalog file listed in terminal map.
    (run3 / "catalog.json").unlink()
    with pytest.raises(MatrixSafetyStop, match="missing"):
        authenticate_completed_run(run3)

    sealed4 = _seal_plan_only(out_root, plan)
    run4 = Path(sealed4["run_dir"])
    complete = json.loads((run4 / "COMPLETE.json").read_text())
    complete["files"]["../escape.txt"] = {"sha256": "00" * 32, "bytes": 0}
    (run4 / "COMPLETE.json").write_text(
        json.dumps(complete, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(MatrixSafetyStop, match="path escape|missing|hash"):
        authenticate_completed_run(run4)


def test_immutable_terminal_collision(out_root: Path, plan: MatrixPlan) -> None:
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    report = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "matrix_id": plan.matrix_id,
        "mode": "plan_only",
        "complete": True,
        "pass": False,
        "plan": plan.to_public_dict(),
        "cells": [],
        "budgets": MatrixBudgets().as_dict(),
        "cumulative_counters": {
            "logical_calls_started": 0,
            "provider_attempts": 0,
            "retained_response_bytes": 0,
            "http_429_count": 0,
            "high_water_in_flight": 0,
        },
        "offline_replay": {"authenticated": False},
    }
    run.seal(kind="COMPLETE", report=report)
    with pytest.raises(MatrixSafetyStop, match="already sealed|already exists"):
        run.seal(kind="COMPLETE", report=report)


def test_exclusive_run_directory(out_root: Path) -> None:
    MatrixRun(out_root, run_id="run_" + "a" * 32)
    with pytest.raises(MatrixSafetyStop, match="already exists"):
        MatrixRun(out_root, run_id="run_" + "a" * 32)


def test_duplicate_attempt_receipt_rejected(out_root: Path, plan: MatrixPlan) -> None:
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    call = iter_logical_calls(plan)[0]
    run.retain_bytes(
        call=call,
        attempt=1,
        body=_chain_body(),
        max_response_bytes=8_000_000,
        status_code=200,
        latency_ms=1.0,
        http_429=False,
        error_class=None,
        error_detail=None,
    )
    with pytest.raises(MatrixSafetyStop, match="contiguous|duplicate"):
        run.retain_bytes(
            call=call,
            attempt=1,
            body=_chain_body(),
            max_response_bytes=8_000_000,
            status_code=200,
            latency_ms=1.0,
            http_429=False,
            error_class=None,
            error_detail=None,
        )


# ---------------------------------------------------------------------------
# Credentials / malformed / truncation / reservation
# ---------------------------------------------------------------------------


def test_credential_before_across_and_after_cap(out_root: Path, plan: MatrixPlan) -> None:
    # Exact runtime endpoint/secret + form checks (ADR-0015 §9.8).
    secret = "SECRETprojectkey001"
    endpoint = f"https://mainnet.infura.io/v3/{secret}"
    scanner = CredentialScanner.from_rpc_urls(endpoint)
    run = MatrixRun(out_root, credential_scanner=scanner)
    run.write_plan_and_catalog(plan)
    call = iter_logical_calls(plan)[0]
    max_b = 64
    r1 = run.retain_bytes(
        call=call,
        attempt=1,
        body=f'{{"x":"{endpoint}"}}'.encode(),
        max_response_bytes=max_b,
        status_code=200,
        latency_ms=1.0,
        http_429=False,
        error_class=None,
        error_detail=None,
    )
    assert r1["error_class"] == "credential_detection"
    assert r1["body_sha256"] is None
    assert not any(run.raw_dir.glob("*.bin"))

    prefix = b"{" + b"a" * 60
    body = prefix + secret.encode()
    assert len(prefix) < max_b < len(body)
    r2 = run.retain_bytes(
        call=call,
        attempt=2,
        body=body,
        max_response_bytes=max_b,
        status_code=200,
        latency_ms=1.0,
        http_429=False,
        error_class=None,
        error_detail=None,
    )
    assert r2["error_class"] == "credential_detection"
    assert r2["truncated"] is True

    r3 = run.retain_bytes(
        call=call,
        attempt=3,
        body=(b"n" * max_b) + f"?api_key={secret}".encode(),
        max_response_bytes=max_b,
        status_code=200,
        latency_ms=1.0,
        http_429=False,
        error_class=None,
        error_detail=None,
    )
    assert r3["error_class"] == "credential_detection"
    # Generic help URL is ordinary 429 evidence (not credential_detection).
    r4 = run.retain_bytes(
        call=call,
        attempt=4,
        body=b'{"jsonrpc":"2.0","id":1,"error":{"message":"see https://docs.infura.io/help"}}',
        max_response_bytes=10_000,
        status_code=429,
        latency_ms=1.0,
        http_429=True,
        error_class=None,
        error_detail=None,
    )
    assert r4["error_class"] != "credential_detection"
    assert r4["http_429"] is True


def test_malformed_empty_missing_result_safety_stops() -> None:
    with pytest.raises(MatrixSafetyStop, match="empty"):
        parse_json_rpc_result(b"")
    with pytest.raises(MatrixSafetyStop, match="missing result"):
        parse_json_rpc_result(b'{"jsonrpc":"2.0","id":1}')
    with pytest.raises(MatrixSafetyStop, match="malformed_json"):
        parse_json_rpc_result(b"not-json")


def test_truncation_never_success_authority(out_root: Path, plan: MatrixPlan) -> None:
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    call = iter_logical_calls(plan)[0]
    body = b'{"jsonrpc":"2.0","id":1,"result":[]}' + b"x" * 100
    rec = run.retain_bytes(
        call=call,
        attempt=1,
        body=body,
        max_response_bytes=40,
        status_code=200,
        latency_ms=1.0,
        http_429=False,
        error_class=None,
        error_detail=None,
    )
    assert rec["truncated"] is True
    assert rec["success"] is False
    assert run.best_success_body(call.logical_call_id) is None


def test_reservation_exhaustion() -> None:
    tracker = BudgetTracker(
        budgets=MatrixBudgets(max_retained_response_bytes=1000, max_response_bytes=500)
    )
    tracker.reserve(500)
    tracker.commit(500, 120)
    tracker.reserve(800)
    with pytest.raises(MatrixSafetyStop, match="budget"):
        tracker.reserve(100)


def test_provider_disagreement_seals_failed(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_plan(monkeypatch, plan)
    transport = FakeTransport()
    transport.body_override["blockpi:eth_chainId"] = b'{"jsonrpc":"2.0","id":1,"result":"0x2"}'
    report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            primary_rpc_url=_TEST_PRIMARY_RPC,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                    confirm_matrix_id=plan.matrix_id,
            transport=transport,
        )
    ).run()
    assert report["status"] == "FAILED"
    assert report["pass"] is False
    assert report.get("safety_stop")


# ---------------------------------------------------------------------------
# Concurrency / stop / in-flight
# ---------------------------------------------------------------------------


def test_equal_body_promotion_races(out_root: Path) -> None:
    raw = out_root / "raw"
    spool = out_root / "spool"
    raw.mkdir()
    spool.mkdir()
    body = b'{"jsonrpc":"2.0","result":"0x1"}'
    digest = __import__("hashlib").sha256(body).hexdigest()

    def one(i: int) -> None:
        p = spool / f"s{i}.part"
        p.write_bytes(body)
        _promote_raw(p, raw, digest)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(one, range(20)))
    assert (raw / f"{digest}.bin").read_bytes() == body


def test_per_provider_in_flight_high_water(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_plan(monkeypatch, plan)
    transport = FakeTransport()
    hold = threading.Event()
    transport.hold["infura"] = hold
    cfg = MatrixConfig(
        registry_store_root=reg_root,
        output_root=out_root,
        mode="execute_live",
        primary_rpc_url=_TEST_PRIMARY_RPC,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                    confirm_matrix_id=plan.matrix_id,
        budgets=MatrixBudgets(max_in_flight=2, max_logical_calls=30, max_provider_attempts=90),
        transport=transport,
    )
    harness = PairEventV2MatrixHarness(cfg)
    harness.active_run = MatrixRun(out_root)
    assert harness.active_run is not None
    harness.active_run.write_plan_and_catalog(plan)
    calls = [c for c in iter_logical_calls(plan) if c.provider_org == "infura"][:6]
    threads = [
        threading.Thread(target=harness._execute_one, args=(harness.active_run, c))
        for c in calls
    ]
    for t in threads:
        t.start()
    time.sleep(0.3)
    assert harness._gates["infura"].in_flight <= 2
    hold.set()
    for t in threads:
        t.join(timeout=15)
    harness.close()
    assert transport.high_water <= 2


def test_stop_drain_behavior_public_scheduler(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public execute-live: safety stop cancels queued work; started work drains."""
    _patch_plan(monkeypatch, plan)

    class StopDrainTransport:
        def __init__(self) -> None:
            self.starts = 0
            self.finishes = 0
            self.lock = threading.Lock()
            self.closed = False
            self._release = threading.Event()
            self._stop: threading.Event | None = None

        def attach_stop(self, stop: threading.Event) -> None:
            self._stop = stop

        def __call__(self, provider_org: str, request: Mapping[str, Any]) -> TransportResult:
            method = str(request.get("method"))
            with self.lock:
                self.starts += 1
                n = self.starts
            if method == "eth_chainId":
                with self.lock:
                    self.finishes += 1
                return TransportResult(
                    status_code=200,
                    body=_chain_body(),
                    stream_response=None,
                    latency_ms=0.1,
                    http_429=False,
                    error_class=None,
                    error_detail=None,
                )
            # Block a wave of log calls, then inject a public safety stop.
            if n <= 8:
                while not self._release.is_set():
                    if self._stop is not None and self._stop.is_set():
                        break
                    self._release.wait(timeout=0.05)
            else:
                raise MatrixSafetyStop("public scheduler stop")
            with self.lock:
                self.finishes += 1
            return TransportResult(
                status_code=200,
                body=_empty_logs(),
                stream_response=None,
                latency_ms=0.1,
                http_429=False,
                error_class=None,
                error_detail=None,
            )

        def close(self) -> None:
            self.closed = True
            self._release.set()

    transport = StopDrainTransport()
    # Release blocked workers shortly after scheduler starts flooding logs.
    def _release_later() -> None:
        time.sleep(0.4)
        transport._release.set()

    threading.Thread(target=_release_later, daemon=True).start()
    report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            primary_rpc_url=_TEST_PRIMARY_RPC,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                    confirm_matrix_id=plan.matrix_id,
            transport=transport,
            budgets=MatrixBudgets(max_in_flight=2, max_logical_calls=40, max_provider_attempts=120),
        )
    ).run()
    assert report["status"] == "FAILED"
    assert (Path(report["run_dir"]) / "FAILED.json").is_file()
    # Did not attempt the full 1,568-call catalog after stop.
    assert transport.starts < 200
    assert transport.finishes <= transport.starts
    assert transport.closed is True
    # No abandoned provider work at terminal return.
    assert report.get("active_provider_ops_at_return", 0) == 0


# ---------------------------------------------------------------------------
# Isolation / closure / hashes / incomplete / plan-only
# ---------------------------------------------------------------------------


def test_output_tree_isolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "proj"
    bad = project / "data" / "dex003_full" / "store"
    bad.mkdir(parents=True)
    monkeypatch.chdir(project)
    with pytest.raises(MatrixSafetyStop, match="dex003_full"):
        assert_safe_matrix_output_root(bad)
    assert_safe_matrix_output_root(project / "data" / "dex003_v2_matrix")


def test_resource_closure_on_plan_only(
    out_root: Path, reg_root: Path, plan: MatrixPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_plan(monkeypatch, plan)
    transport = FakeTransport()
    h = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="plan_only",
            transport=transport,
        )
    )
    report = h.run()
    assert report["status"] == "COMPLETE"
    assert report["pass"] is False
    assert transport.closed is True
    h.close()
    h.close()


def test_evidence_and_report_hashes_distinct_and_complete() -> None:
    payload = {
        "matrix_id": "mtx_x",
        "run_id": "run_" + "c" * 32,
        "cells": [{"status": "pass"}],
        "cumulative_counters": {
            "logical_calls_started": 5,
            "provider_attempts": 5,
            "retained_response_bytes": 100,
            "http_429_count": 1,
            "high_water_in_flight": 2,
        },
        "started_at": "t1",
        "high_water": {"elapsed_seconds": 1.0, "high_water_in_flight": 2},
    }
    eh = compute_evidence_hash(payload)
    payload2 = dict(payload)
    payload2["started_at"] = "t2"
    payload2["high_water"] = {"elapsed_seconds": 99.0, "high_water_in_flight": 2}
    assert compute_evidence_hash(payload2) == eh
    payload3 = dict(payload)
    payload3["cumulative_counters"] = dict(payload["cumulative_counters"])
    payload3["cumulative_counters"]["high_water_in_flight"] = 9
    assert compute_evidence_hash(payload3) != eh
    rh = compute_report_hash(evidence_hash=eh, payload=payload)
    assert rh != eh


def test_incomplete_run_non_pass(out_root: Path, plan: MatrixPlan) -> None:
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    assert not run.complete_path.exists()
    with pytest.raises(MatrixError, match="incomplete|COMPLETE"):
        authenticate_completed_run(run.run_dir)


def test_plan_only_not_live_pass(
    out_root: Path, reg_root: Path, plan: MatrixPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_plan(monkeypatch, plan)
    report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="plan_only",
        )
    ).run()
    assert report["mode"] == "plan_only"
    assert report["pass"] is False
    assert report["complete"] is True
    # Plan-only COMPLETE cannot be a live PASS replay source.
    with pytest.raises(MatrixError, match="execute_live"):
        authenticate_completed_run(Path(report["run_dir"]), require_live_pass=True)


def test_confirm_matrix_id_mismatch_fails(
    out_root: Path, reg_root: Path, plan: MatrixPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_plan(monkeypatch, plan)
    with pytest.raises(MatrixSafetyStop, match="confirm_matrix_id"):
        PairEventV2MatrixHarness(
            MatrixConfig(
                registry_store_root=reg_root,
                output_root=out_root,
                mode="execute_live",
                primary_rpc_url=_TEST_PRIMARY_RPC,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                    confirm_matrix_id="mtx_wrong",
                transport=FakeTransport(),
            )
        ).run()


def test_standalone_replay_requires_live_run_dir(
    out_root: Path, reg_root: Path
) -> None:
    with pytest.raises(MatrixError, match="live_run_dir"):
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="offline_replay",
        )


# ---------------------------------------------------------------------------
# Sol terminal-auth probes (public APIs)
# ---------------------------------------------------------------------------


def test_http200_jsonrpc_error_is_not_success_and_seals_failed(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Probe: HTTP-200 JSON-RPC error is not success; bounded retries then FAILED."""
    _patch_plan(monkeypatch, plan)
    transport = FakeTransport()
    # Both providers return JSON-RPC error on chainId (HTTP 200).
    err = b'{"jsonrpc":"2.0","id":1,"error":{"code":-32000,"message":"server error"}}'
    transport.body_override["infura:eth_chainId"] = err
    transport.body_override["blockpi:eth_chainId"] = err
    report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            primary_rpc_url=_TEST_PRIMARY_RPC,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                    confirm_matrix_id=plan.matrix_id,
            transport=transport,
            # Default max_attempts_per_logical_call=3 — freeze bounded retry policy.
            budgets=MatrixBudgets(),
        )
    ).run()
    assert report["status"] == "FAILED"
    run_dir = Path(report["run_dir"])
    assert (run_dir / "FAILED.json").is_file()
    assert not (run_dir / "COMPLETE.json").exists()
    # Dual providers × default 3 attempts each for chainId.
    chain_calls = [c for c in transport.calls if c[1] == "eth_chainId"]
    assert len(chain_calls) == 6
    for path in (run_dir / "receipts").glob("chain__*"):
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec.get("success") is False
        assert rec.get("error_class")


def test_disk_raw_tamper_before_pass_detected(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Probe: pre-seal disk evaluation rehashes raw; tamper fails closed with FAILED seal."""
    _patch_plan(monkeypatch, plan)
    transport = FakeTransport()
    # Hook evaluate path by tampering after execute via monkeypatch of validate.
    real_validate = __import__(
        "cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix",
        fromlist=["validate_run_call_inventory"],
    ).validate_run_call_inventory

    def _tamper_then_validate(run_dir: Path, p: MatrixPlan) -> Any:
        raw_dir = Path(run_dir) / "raw"
        for f in raw_dir.glob("*.bin"):
            f.write_bytes(f.read_bytes() + b"X")
            break
        return real_validate(run_dir, p)

    monkeypatch.setattr(
        "cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix.validate_run_call_inventory",
        _tamper_then_validate,
    )
    report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            primary_rpc_url=_TEST_PRIMARY_RPC,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                    confirm_matrix_id=plan.matrix_id,
            transport=transport,
        )
    ).run()
    assert report["status"] == "FAILED"
    assert (Path(report["run_dir"]) / "FAILED.json").is_file()


def test_forged_unknown_receipt_rejected_on_auth(out_root: Path, plan: MatrixPlan) -> None:
    """Probe: forged logical-call receipt + unreferenced raw fail authentication."""
    sealed = _seal_plan_only(out_root, plan)
    # Build a live-like COMPLETE with one real chain attempt then forge extras.
    # Use a fresh exclusive run with plan + fake execute receipts is heavy;
    # instead seal plan-only then create a second run with catalog and forge.
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    call = iter_logical_calls(plan)[0]
    run.retain_bytes(
        call=call,
        attempt=1,
        body=_chain_body(),
        max_response_bytes=8_000_000,
        status_code=200,
        latency_ms=1.0,
        http_429=False,
        error_class=None,
        error_detail=None,
    )
    # Forged unknown receipt file + orphan raw.
    forged = run.receipts_dir / "scalar__forged__infura__0xabc__swap__a1.json"
    forged.write_text(
        json.dumps(
            {
                "logical_call_id": "scalar:forged:infura:0xabc:swap",
                "attempt": 1,
                "run_id": run.run_id,
                "provider_org": "infura",
                "kind": "scalar",
                "request_sha256": "00" * 32,
                "request_json": "{}",
                "status_code": 200,
                "body_sha256": None,
                "body_bytes": 0,
                "observed_body_bytes": 0,
                "truncated": False,
                "latency_ms": 1.0,
                "http_429": False,
                "error_class": "transport",
                "error_detail": "x",
                "success": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    orphan = run.raw_dir / ("ee" * 32 + ".bin")
    orphan.write_bytes(b"orphan")
    with pytest.raises(MatrixSafetyStop, match="unknown|orphan"):
        from cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix import (
            validate_run_call_inventory,
        )

        validate_run_call_inventory(run.run_dir, plan)
    del sealed


def test_replay_output_overlap_with_live_rejected(
    out_root: Path, reg_root: Path
) -> None:
    """Probe: offline replay cannot target output that contains the live source."""
    live_dir = out_root / "runs" / ("run_" + "b" * 32)
    live_dir.mkdir(parents=True)
    (live_dir / "COMPLETE.json").write_text("{}", encoding="utf-8")
    # Same output root contains the live run directory — rejected before auth.
    with pytest.raises(MatrixSafetyStop, match="equal, contain, or sit inside"):
        PairEventV2MatrixHarness(
            MatrixConfig(
                registry_store_root=reg_root,
                output_root=out_root,
                mode="offline_replay",
                live_run_dir=live_dir,
            )
        ).run()


def test_credentials_split_across_scanner_chunks(out_root: Path, plan: MatrixPlan) -> None:
    """Exact secret straddles STREAM_CHUNK_BYTES (65,536) boundary — detected pre-write."""
    secret = "SECRETspanacrossboundaryXX"
    scanner = CredentialScanner(forbidden_substrings=(secret,))
    run = MatrixRun(out_root, credential_scanner=scanner)
    run.write_plan_and_catalog(plan)
    call = iter_logical_calls(plan)[0]
    body = (b"n" * (STREAM_CHUNK_BYTES - 10)) + secret.encode()
    assert len(body) > STREAM_CHUNK_BYTES
    rec = run.retain_bytes(
        call=call,
        attempt=1,
        body=body,
        max_response_bytes=8_000_000,
        status_code=200,
        latency_ms=1.0,
        http_429=False,
        error_class=None,
        error_detail=None,
    )
    assert rec["error_class"] == "credential_detection"
    assert rec["body_sha256"] is None
    assert not any(run.raw_dir.glob("*.bin"))


def test_hard_wall_timeout_during_blocking_provider_call(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public execute-live: blocking transport is cut by remaining-wall timeout."""
    _patch_plan(monkeypatch, plan)

    class BlockingTransport:
        def __init__(self) -> None:
            self.closed = False
            self.entered = threading.Event()
            self.finished = threading.Event()
            self._stop: threading.Event | None = None

        def attach_stop(self, stop: threading.Event) -> None:
            self._stop = stop

        def __call__(self, provider_org: str, request: Mapping[str, Any]) -> TransportResult:
            self.entered.set()
            # Cooperative: poll stop so drain can complete after wall expiry.
            end = time.monotonic() + 5.0
            while time.monotonic() < end:
                if self._stop is not None and self._stop.is_set():
                    break
                time.sleep(0.01)
            self.finished.set()
            return TransportResult(
                status_code=200,
                body=_chain_body(),
                stream_response=None,
                latency_ms=50.0,
                http_429=False,
                error_class=None,
                error_detail=None,
            )

        def close(self) -> None:
            self.closed = True
            if self._stop is not None:
                self._stop.set()

    transport = BlockingTransport()
    harness = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            primary_rpc_url=_TEST_PRIMARY_RPC,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                    confirm_matrix_id=plan.matrix_id,
            transport=transport,
            # Enough wall to enter the provider call; remaining wall caps the call timeout.
            budgets=MatrixBudgets(max_wall_seconds=0.3, http_timeout_seconds=60.0),
        )
    )
    t0 = time.monotonic()
    report = harness.run()
    elapsed = time.monotonic() - t0
    assert report["status"] == "FAILED"
    assert (Path(report["run_dir"]) / "FAILED.json").is_file()
    # Must not abandon: started work finishes before return.
    assert transport.finished.is_set()
    assert harness.active_provider_ops() == 0
    assert report.get("active_provider_ops_at_return", 0) == 0
    # Wall path is hard: return well before the full 5s sleep.
    assert elapsed < 2.5
    assert transport.entered.is_set()
    assert transport.closed is True


def test_streamed_response_wall_expiry(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stream wall: abort+join reader before terminal; stream finished at return."""
    _patch_plan(monkeypatch, plan)

    class SlowStream:
        def __init__(self) -> None:
            self.chunks_yielded = 0
            self.finished = threading.Event()
            self._stop = threading.Event()
            self.reader_thread: threading.Thread | None = None

        def close(self) -> None:
            # Cooperative stop so a blocked chunk reader can exit and be joined.
            self._stop.set()

        def iter_bytes(self, chunk_size: int = STREAM_CHUNK_BYTES) -> Any:
            self.reader_thread = threading.current_thread()
            try:
                self.chunks_yielded += 1
                yield b'{"jsonrpc":"2.0","id":1,"result":'
                # Slow second chunk; poll stop so abort can finish the reader.
                end = time.monotonic() + 5.0
                while time.monotonic() < end:
                    if self._stop.is_set():
                        return
                    time.sleep(0.01)
                self.chunks_yielded += 1
                yield b"[]}"
            finally:
                self.finished.set()

    class StreamTransport:
        def __init__(self) -> None:
            self.closed = False
            self.stream = SlowStream()

        def __call__(self, provider_org: str, request: Mapping[str, Any]) -> TransportResult:
            return TransportResult(
                status_code=200,
                body=None,
                stream_response=self.stream,
                latency_ms=1.0,
                http_429=False,
                error_class=None,
                error_detail=None,
            )

        def close(self) -> None:
            self.closed = True
            self.stream.close()

    transport = StreamTransport()
    harness = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            primary_rpc_url=_TEST_PRIMARY_RPC,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                    confirm_matrix_id=plan.matrix_id,
            transport=transport,
            budgets=MatrixBudgets(max_wall_seconds=0.15, http_timeout_seconds=60.0),
        )
    )
    t0 = time.monotonic()
    report = harness.run()
    elapsed = time.monotonic() - t0
    assert report["status"] == "FAILED"
    assert (Path(report["run_dir"]) / "FAILED.json").is_file()
    assert elapsed < 1.5
    # Drain, not abandon: stream reader finished before terminal return.
    assert transport.stream.finished.is_set()
    stream_finished_at_return = transport.stream.finished.is_set()
    assert stream_finished_at_return is True
    assert report.get("stream_finished_at_return", stream_finished_at_return) is True
    assert harness.active_provider_ops() == 0
    assert report.get("active_provider_ops_at_return", 0) == 0
    assert transport.closed is True


def test_symlink_replay_output_overlap_rejected(
    out_root: Path, reg_root: Path, tmp_path: Path
) -> None:
    live_dir = out_root / "runs" / ("run_" + "c" * 32)
    live_dir.mkdir(parents=True)
    (live_dir / "COMPLETE.json").write_text("{}", encoding="utf-8")
    link_root = tmp_path / "link_out"
    # Symlink output root resolving into a tree that contains the live source.
    link_root.symlink_to(out_root, target_is_directory=True)
    with pytest.raises(MatrixSafetyStop, match="equal, contain, or sit inside"):
        PairEventV2MatrixHarness(
            MatrixConfig(
                registry_store_root=reg_root,
                output_root=link_root,
                mode="offline_replay",
                live_run_dir=live_dir,
            )
        ).run()


def test_cli_plan_live_replay_failure_paths(
    out_root: Path, reg_root: Path, plan: MatrixPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Public CLI failure paths (no network) via file-path import (scripts is not a package)."""
    import importlib.util

    cli_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "research"
        / "run_uniswap_v2_pair_events_v2_matrix.py"
    )
    assert cli_path.is_file()
    spec = importlib.util.spec_from_file_location("run_v2_matrix_cli", cli_path)
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    # plan-only with missing registry fails closed.
    code = cli.main(
        [
            "--registry-store-root",
            str(reg_root),
            "--output-root",
            str(out_root / "cli_plan"),
        ]
    )
    assert code != 0

    # execute-live without confirm-matrix-id / env URLs.
    code = cli.main(
        [
            "--execute-live",
            "--registry-store-root",
            str(reg_root),
            "--output-root",
            str(out_root / "cli_live"),
        ]
    )
    assert code != 0

    # offline-replay without live-run-dir.
    code = cli.main(
        [
            "--offline-replay",
            "--registry-store-root",
            str(reg_root),
            "--output-root",
            str(out_root / "cli_replay"),
        ]
    )
    assert code != 0


def test_terminal_metrics_present_on_failed_live(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_plan(monkeypatch, plan)
    transport = FakeTransport()
    transport.body_override["infura:eth_chainId"] = (
        b'{"jsonrpc":"2.0","id":1,"error":{"code":-1,"message":"nope"}}'
    )
    transport.body_override["blockpi:eth_chainId"] = transport.body_override[
        "infura:eth_chainId"
    ]
    report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            primary_rpc_url=_TEST_PRIMARY_RPC,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                    confirm_matrix_id=plan.matrix_id,
            transport=transport,
        )
    ).run()
    assert report["status"] == "FAILED"
    assert "call_metrics" in report
    metrics = report["call_metrics"]
    assert "per_provider" in metrics
    assert "per_call" in metrics
    assert metrics["per_call_count"] == LOGICAL_CALL_CEILING
    assert len(metrics["per_call"]) == LOGICAL_CALL_CEILING
    for org in DEFAULT_PROVIDER_ORGS:
        assert org in metrics["per_provider"]
        assert metrics["per_provider"][org]["attempts"] >= 1
        assert metrics["per_provider"][org]["failures"] >= 1
    attempted = [e for e in metrics["per_call"] if e["attempts"] >= 1]
    assert len(attempted) >= 2  # dual chain providers
    for entry in attempted:
        assert entry["status"] == "error"
        assert entry["error_class"]
        assert "latency_ms_total" in entry
        assert "response_bytes" in entry
    # Cells still carry complete provider-side metric keys when present.
    if report.get("cells"):
        for cell in report["cells"]:
            for side in ("primary", "secondary"):
                assert "attempts" in cell[side]
                assert "http_429s" in cell[side]
                assert "response_bytes" in cell[side]
    assert "high_water" in report
    assert "cumulative_counters" in report


# ---------------------------------------------------------------------------
# ADR-0015 §9.8 recovery suite (lock, scanner, fair schedule, capacity selection)
# Fresh regeneration after artifact-loss incident; expands senior suite to 46 tests.
# ---------------------------------------------------------------------------


def _empty_logs_body() -> bytes:
    return b'{"jsonrpc":"2.0","id":1,"result":[]}'


def _sync_log_body(*, address: str, block: int) -> bytes:
    log = {
        "address": address,
        "blockNumber": hex(block),
        "blockHash": "0x" + ("11" * 32),
        "transactionHash": "0x" + ("22" * 32),
        "transactionIndex": "0x0",
        "logIndex": "0x0",
        "topics": [SYNC_TOPIC],
        "data": "0x" + ("00" * 64),
        "removed": False,
    }
    return json.dumps(
        {"jsonrpc": "2.0", "id": 1, "result": [log]}, separators=(",", ":")
    ).encode("utf-8")


def _seed_receipt(
    run: MatrixRun,
    call: Any,
    *,
    body: bytes | None,
    error_class: str | None = None,
    error_detail: str | None = None,
    http_429: bool = False,
) -> None:
    if body is None:
        body = b""
        error_class = error_class or "provider_limit_or_size"
        error_detail = error_detail or "provider_limit_or_size"
    run.retain_bytes(
        call=call,
        attempt=1,
        body=body,
        max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
        status_code=200 if not http_429 else 429,
        latency_ms=0.01,
        http_429=http_429,
        error_class=error_class,
        error_detail=error_detail,
    )


_CAPACITY_RPC_BODY = (
    b'{"jsonrpc":"2.0","id":1,"error":{"code":-32005,'
    b'"message":"query returned more than 10000 results"}}'
)
_HTTP_429_BODY = (
    b'{"jsonrpc":"2.0","id":1,"error":{"code":-32005,'
    b'"message":"Too Many Requests rate limit exceeded"}}'
)


def _seed_full_success(run: MatrixRun, plan: MatrixPlan) -> None:
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        body = _chain_body() if call.kind == "chain" else empty
        _seed_receipt(run, call, body=body)


def _seed_cohort8_capacity_boundary(run: MatrixRun, plan: MatrixPlan) -> None:
    """Scalars agree; batches pass for size<=8; size>=32 are capacity failures both providers."""
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
            continue
        if call.kind == "scalar":
            _seed_receipt(run, call, body=empty)
            continue
        size = int(call.cohort_size or 0)
        if size <= 8:
            _seed_receipt(run, call, body=empty)
        else:
            _seed_receipt(run, call, body=_CAPACITY_RPC_BODY)


def test_live_output_lock_contention_before_run(out_root: Path) -> None:
    """Second exclusive live lock must fail closed before run creation."""
    first = LiveOutputLock(out_root)
    first.acquire()
    try:
        second = LiveOutputLock(out_root)
        with pytest.raises(MatrixSafetyStop, match="live matrix lock"):
            second.acquire()
    finally:
        first.release()


def test_safe_generic_url_429_not_credential_detection() -> None:
    """Credential-free provider help URLs are ordinary evidence; forms still block."""
    scanner = CredentialScanner.from_rpc_urls(
        "https://mainnet.infura.io/v3/SECRETprojectkey001",
        "https://ethereum.blockpi.network/v1/rpc/SECRETblockpikey02",
    )
    scanner.scan_text(
        "https://docs.infura.io/api/network/ethereum/json-rpc-methods",
        label="429_help",
    )
    scanner.scan_text(
        "Too Many Requests. See https://help.example.com/rate-limits for details.",
        label="429_body",
    )
    with pytest.raises(MatrixSafetyStop, match="credential"):
        scanner.scan_text(
            "error: invalid project SECRETprojectkey001",
            label="echo",
        )
    scanner.scan_text("host mainnet.infura.io is reachable", label="plain_netloc")
    empty = CredentialScanner()
    with pytest.raises(MatrixSafetyStop, match="credential"):
        empty.scan_text("https://user:pass@example.com/path", label="userinfo")
    with pytest.raises(MatrixSafetyStop, match="credential"):
        empty.scan_text(
            "Authorization: Bearer DIFFERENTSECRET999",
            label="bearer_form",
        )
    with pytest.raises(MatrixSafetyStop, match="credential"):
        empty.scan_text(
            "https://help.example/?api_key=DIFFERENTSECRET999",
            label="secret_query_form",
        )
    with pytest.raises(MatrixSafetyStop, match="credential"):
        empty.scan_text("https://help.example/?key=DIFFERENTSECRET999", label="key_form")


def test_credential_form_and_exact_runtime_across_cap() -> None:
    """Bearer/secret-query forms and exact endpoint echo reject beyond retained cap."""
    endpoint = "https://mainnet.infura.io/v3/SECRETprojectkey001"
    scanner = CredentialScanner.from_rpc_urls(endpoint)
    with pytest.raises(MatrixSafetyStop, match="credential"):
        scanner.scan_text("Authorization: Bearer DIFFERENTSECRET999", label="bearer")
    with pytest.raises(MatrixSafetyStop, match="credential"):
        scanner.scan_text(
            "https://help.example/?api_key=DIFFERENTSECRET999", label="query"
        )
    pad = "z" * (STREAM_CHUNK_BYTES + 100)
    with pytest.raises(MatrixSafetyStop, match="credential"):
        scanner.scan_text(pad + "SECRETprojectkey001", label="over_cap_echo")


def test_credential_detection_across_chunks_and_beyond_cap() -> None:
    """Exact secret spanning STREAM_CHUNK_BYTES and over-cap tail is detected."""
    secret = "SECRETspanacrossboundaryXX"
    scanner = CredentialScanner(forbidden_substrings=(secret,))
    left = b"x" * (STREAM_CHUNK_BYTES - 10)
    mid = secret.encode("utf-8")
    part1 = left + mid[:10]
    part2 = mid[10:] + b"y" * 100
    with pytest.raises(MatrixSafetyStop, match="credential"):
        window = part1 + part2
        scanner.scan_bytes(window, label="cross_chunk")


def test_fair_schedule_interleaves_providers(plan: MatrixPlan) -> None:
    """Execution order must not submit one org's entire scalar segment first."""
    work = [c for c in iter_logical_calls(plan) if c.kind == "scalar"]
    scheduled = fair_schedule_calls(work)
    assert len(scheduled) == len(work)
    first_orgs = [c.provider_org for c in scheduled[:4]]
    assert len(set(first_orgs)) == 2, first_orgs
    assert {c.logical_call_id for c in scheduled} == {c.logical_call_id for c in work}


def test_capacity_selection_cohort8_with_larger_capacity_failures() -> None:
    """Viable nested prefix 1/8 may PASS while 32+ are authenticated capacity failures."""
    cells: list[dict[str, object]] = []
    for range_name in ("sparse", "medium", "hot"):
        for size in NESTED_COHORT_SIZES:
            if size <= 8:
                cells.append(
                    {
                        "range_name": range_name,
                        "cohort_size": size,
                        "cell_id": f"{range_name}:cohort{size}",
                        "status": "pass",
                        "failure_class": None,
                        "detail": None,
                    }
                )
            else:
                cells.append(
                    {
                        "range_name": range_name,
                        "cohort_size": size,
                        "cell_id": f"{range_name}:cohort{size}",
                        "status": "fail",
                        "failure_class": "capacity",
                        "detail": "provider_limit_or_size: response size",
                    }
                )
    selection = select_capacity_from_cells(cells)
    assert selection["selection_valid"] is True
    assert selection["selected_cohort_size"] == 8
    assert selection["all_cells_pass"] is False
    assert selection["viable_sizes"] == [1, 8]
    assert len(selection["capacity_failure_cells"]) == 9


def test_capacity_selection_rejects_scalar_disagreement_and_nonmonotonic() -> None:
    cells: list[dict[str, object]] = []
    for range_name in ("sparse", "medium", "hot"):
        for size in NESTED_COHORT_SIZES:
            status = "pass" if size in (1, 32) else "fail"
            if size == 8:
                status = "fail"
            cells.append(
                {
                    "range_name": range_name,
                    "cohort_size": size,
                    "cell_id": f"{range_name}:cohort{size}",
                    "status": status,
                    "failure_class": None if status == "pass" else "capacity",
                    "detail": None if status == "pass" else "provider_limit_or_size",
                }
            )
    selection = select_capacity_from_cells(cells)
    assert selection["nonmonotonic"] is True
    assert selection["selection_valid"] is False
    assert selection["selected_cohort_size"] is None

    disagree = []
    for range_name in ("sparse", "medium", "hot"):
        for size in (1, 8, 32, 64, 128):
            disagree.append(
                {
                    "range_name": range_name,
                    "cohort_size": size,
                    "cell_id": f"{range_name}:cohort{size}",
                    "status": "fail" if size == 1 else "pass",
                    "failure_class": "provider_disagreement" if size == 1 else None,
                    "detail": "scalar provider disagreement" if size == 1 else None,
                }
            )
    sel2 = select_capacity_from_cells(disagree)
    assert sel2["selection_valid"] is False
    assert any("provider_disagreement" in b for b in sel2["blocking_reasons"])


def test_evaluate_cells_scalar_disagreement_before_batch_public(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Public evaluate_cells: scalar disagreement preserved; batch not consulted for 32+."""
    diverge_addr = plan.maximum_cohort[8]
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
            continue
        if call.kind == "scalar":
            use_log = (
                call.provider_org == "blockpi"
                and call.address == diverge_addr
                and call.topic == SYNC_TOPIC
            )
            if use_log:
                start, _end = plan.ranges[str(call.range_name)]
                body = _sync_log_body(address=diverge_addr, block=start)
            else:
                body = empty
            _seed_receipt(run, call, body=body)
            continue
        size = int(call.cohort_size or 0)
        if size <= 8:
            _seed_receipt(run, call, body=empty)

    cells = evaluate_cells(run, plan)
    assert len(cells) == 15
    by_id = {c["cell_id"]: c for c in cells}
    for range_name in ("sparse", "medium", "hot"):
        for size in (1, 8):
            cell = by_id[f"{range_name}:cohort{size}"]
            assert cell["status"] == "pass", cell
        for size in (32, 64, 128):
            cell = by_id[f"{range_name}:cohort{size}"]
            assert cell["status"] == "fail", cell
            assert cell["failure_class"] == "provider_disagreement", cell
            assert cell["detail"] == "scalar provider disagreement"
            assert cell["scalar_union_digest_primary"]
            assert cell["scalar_union_digest_secondary"]
            assert (
                cell["scalar_union_digest_primary"]
                != cell["scalar_union_digest_secondary"]
            )
            assert cell["batch_digest_primary"] is None
            assert cell["batch_digest_secondary"] is None
    selection = select_capacity_from_cells(cells)
    assert selection["selection_valid"] is False
    assert any("provider_disagreement" in b for b in selection["blocking_reasons"])


def test_evaluate_cells_batch_scalar_digest_mismatch_hard_blocks(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Successful batch/scalar digest inequality is provider_disagreement, never capacity."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
            continue
        if call.kind == "scalar":
            _seed_receipt(run, call, body=empty)
            continue
        if (
            call.kind == "batch"
            and call.range_name == "hot"
            and int(call.cohort_size or 0) == 1
            and call.provider_org == "infura"
        ):
            start, _end = plan.ranges["hot"]
            body = _sync_log_body(address=plan.maximum_cohort[0], block=start)
            _seed_receipt(run, call, body=body)
        else:
            _seed_receipt(run, call, body=empty)

    cells = evaluate_cells(run, plan)
    target = next(c for c in cells if c["cell_id"] == "hot:cohort1")
    assert target["status"] == "fail"
    assert target["failure_class"] == "provider_disagreement"
    assert "digest inequality" in str(target["detail"])
    assert target["failure_class"] != "capacity"
    selection = select_capacity_from_cells(cells)
    assert selection["selection_valid"] is False
    assert any("provider_disagreement" in b for b in selection["blocking_reasons"])
    assert "hot:cohort1" not in selection["capacity_failure_cells"]


def test_authenticate_rejects_mismatched_capacity_selection(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Generic auth rejects forged selection when disk recomputation disagrees."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    _seed_cohort8_capacity_boundary(run, plan)
    cells = evaluate_cells(run, plan)
    true_selection = select_capacity_from_cells(cells)
    assert true_selection["selected_cohort_size"] == 8
    forged_selection = dict(true_selection)
    forged_selection["selected_cohort_size"] = 32
    forged_selection["nested_prefix"] = [1, 8, 32]
    forged_selection["viable_sizes"] = [1, 8, 32]
    forged_selection["selection_valid"] = True

    report = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "matrix_id": plan.matrix_id,
        "mode": "execute_live",
        "complete": True,
        "pass": False,
        "plan": plan.to_public_dict(),
        "cells": cells,
        "capacity_selection": forged_selection,
        "budgets": MatrixBudgets().as_dict(),
        "cumulative_counters": {
            "logical_calls_started": LOGICAL_CALL_CEILING,
            "provider_attempts": LOGICAL_CALL_CEILING,
            "retained_response_bytes": 0,
            "http_429_count": 0,
            "high_water_in_flight": 1,
        },
        "offline_replay": {"authenticated": True, "selected_cohort_size": 32},
        "credential_scan": "pass",
        "all_cells_pass": False,
    }
    sealed = run.seal(kind="COMPLETE", report=report)
    run_dir = Path(sealed["run_dir"])
    with pytest.raises(MatrixSafetyStop, match="capacity_selection"):
        authenticate_completed_run(run_dir)
    with pytest.raises(MatrixSafetyStop, match="capacity_selection"):
        authenticate_completed_run(run_dir, require_live_pass=True)


def test_authenticate_complete_execute_live_non_pass_with_matching_selection(
    out_root: Path, plan: MatrixPlan
) -> None:
    """COMPLETE execute-live pass=false authenticates disk-consistent cohort-8 selection."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    _seed_cohort8_capacity_boundary(run, plan)
    cells = evaluate_cells(run, plan)
    selection = select_capacity_from_cells(cells)
    assert selection["selection_valid"] is True
    assert selection["selected_cohort_size"] == 8
    assert selection["all_cells_pass"] is False
    assert any(c.get("failure_class") == "capacity" for c in cells if c["status"] == "fail")

    report = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "matrix_id": plan.matrix_id,
        "mode": "execute_live",
        "complete": True,
        "pass": False,
        "plan": plan.to_public_dict(),
        "cells": cells,
        "capacity_selection": selection,
        "budgets": MatrixBudgets().as_dict(),
        "cumulative_counters": {
            "logical_calls_started": LOGICAL_CALL_CEILING,
            "provider_attempts": LOGICAL_CALL_CEILING,
            "retained_response_bytes": 0,
            "http_429_count": 0,
            "high_water_in_flight": 1,
        },
        "offline_replay": {
            "kind": "in_process_disk_replay",
            "authenticated": True,
            "selection_valid": True,
            "selected_cohort_size": 8,
        },
        "credential_scan": "pass",
        "all_cells_pass": False,
        "detail": "matrix non-PASS diagnostic seal for review authentication",
    }
    sealed = run.seal(kind="COMPLETE", report=report)
    run_dir = Path(sealed["run_dir"])
    auth = authenticate_completed_run(run_dir)
    assert auth["mode"] == "execute_live"
    assert auth["pass"] is False
    assert auth["capacity_selection"]["selected_cohort_size"] == 8
    with pytest.raises(MatrixError, match="pass=true"):
        authenticate_completed_run(run_dir, require_live_pass=True)


def test_authenticate_rejects_sealed_cells_disagreeing_with_raw(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Generic auth rejects forged sealed cells that contradict retained receipts/raw."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    _seed_full_success(run, plan)
    disk_cells = evaluate_cells(run, plan)
    assert all(c["status"] == "pass" for c in disk_cells)
    forged_cells: list[dict[str, Any]] = []
    for range_name in ("sparse", "medium", "hot"):
        for size in NESTED_COHORT_SIZES:
            if size <= 8:
                forged_cells.append(
                    {
                        "range_name": range_name,
                        "cohort_size": size,
                        "cell_id": f"{range_name}:cohort{size}",
                        "status": "pass",
                        "failure_class": None,
                        "detail": None,
                    }
                )
            else:
                forged_cells.append(
                    {
                        "range_name": range_name,
                        "cohort_size": size,
                        "cell_id": f"{range_name}:cohort{size}",
                        "status": "fail",
                        "failure_class": "capacity",
                        "detail": "provider_limit_or_size",
                    }
                )
    forged_selection = select_capacity_from_cells(forged_cells)
    report = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "matrix_id": plan.matrix_id,
        "mode": "execute_live",
        "complete": True,
        "pass": False,
        "plan": plan.to_public_dict(),
        "cells": forged_cells,
        "capacity_selection": forged_selection,
        "budgets": MatrixBudgets().as_dict(),
        "cumulative_counters": {
            "logical_calls_started": LOGICAL_CALL_CEILING,
            "provider_attempts": LOGICAL_CALL_CEILING,
            "retained_response_bytes": 0,
            "http_429_count": 0,
            "high_water_in_flight": 1,
        },
        "offline_replay": {"authenticated": True},
        "credential_scan": "pass",
        "all_cells_pass": False,
    }
    sealed = run.seal(kind="COMPLETE", report=report)
    with pytest.raises(MatrixSafetyStop, match="sealed cells disagree"):
        authenticate_completed_run(Path(sealed["run_dir"]))


def test_batch_http_429_is_quota_hard_blocker_not_capacity(
    out_root: Path, plan: MatrixPlan
) -> None:
    """HTTP 429 on batch is quota hard-block; not treated as capacity boundary."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
        elif call.kind == "scalar":
            _seed_receipt(run, call, body=empty)
        else:
            # All batches 429 both providers.
            _seed_receipt(
                run,
                call,
                body=_HTTP_429_BODY,
                http_429=True,
                error_class="http_429",
                error_detail="rate limit",
            )
    cells = evaluate_cells(run, plan)
    assert all(c["status"] == "fail" for c in cells)
    assert all(c["failure_class"] == "quota_or_429" for c in cells)
    selection = select_capacity_from_cells(cells)
    assert selection["selection_valid"] is False
    assert any("quota_or_429" in b for b in selection["blocking_reasons"])
    assert selection["capacity_failure_cells"] == []


def test_validate_cell_topology_rejects_duplicates_and_omissions() -> None:
    cells = []
    for range_name in ("sparse", "medium", "hot"):
        for size in NESTED_COHORT_SIZES:
            cells.append(
                {
                    "range_name": range_name,
                    "cohort_size": size,
                    "cell_id": f"{range_name}:cohort{size}",
                    "status": "pass",
                    "failure_class": None,
                }
            )
    # Drop one and duplicate another.
    bad = cells[:-1] + [dict(cells[0])]
    from cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix import (
        validate_cell_topology,
    )

    with pytest.raises(MatrixSafetyStop, match="duplicate|missing"):
        validate_cell_topology(bad)


def test_live_cohort8_selection_via_public_evaluate(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Public evaluate_cells path yields selected cohort 8 from capacity-bounded disk."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    _seed_cohort8_capacity_boundary(run, plan)
    cells = evaluate_cells(run, plan)
    selection = select_capacity_from_cells(cells)
    assert selection["selected_cohort_size"] == 8
    assert selection["selection_valid"] is True
    assert selection["viable_sizes"] == [1, 8]
    assert len(selection["capacity_failure_cells"]) == 9


def test_public_execute_live_cohort8_capacity_selection(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public execute_live harness selects cohort 8 when larger batches are capacity-only."""
    _patch_plan(monkeypatch, plan)
    transport = FakeTransport()
    transport.capacity_min_batch_addresses = 32
    report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            confirm_matrix_id=plan.matrix_id,
            transport=transport,
            budgets=MatrixBudgets(max_in_flight=4, requests_per_second=8.0),
            primary_rpc_url="https://mainnet.infura.io/v3/SECRETprojectkey001",
            secondary_rpc_url="https://ethereum.blockpi.network/v1/rpc/SECRETblockpikey02",
        )
    ).run()
    assert report["status"] == "COMPLETE"
    assert report["complete"] is True
    # Capacity selection may PASS matrix with selected 8 even when not all cells pass.
    assert report["capacity_selection"]["selected_cohort_size"] == 8
    assert report["capacity_selection"]["selection_valid"] is True
    assert report["all_cells_pass"] is False
    assert report["pass"] is True  # valid selection + in-process replay
    assert len(report["capacity_selection"]["capacity_failure_cells"]) == 9
    # Runtime scanner wired on live run: sealed report remains credential-free.
    assert "SECRETprojectkey001" not in json.dumps(report)
    assert report.get("credential_scan") == "pass"


def test_public_scheduler_submission_fairness(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public execute_live submission order is round-robin (prefix imbalance <= 1)."""
    _patch_plan(monkeypatch, plan)
    transport = FakeTransport()
    harness = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            primary_rpc_url=_TEST_PRIMARY_RPC,
            secondary_rpc_url=_TEST_SECONDARY_RPC,
            confirm_matrix_id=plan.matrix_id,
            transport=transport,
            budgets=MatrixBudgets(max_in_flight=2, requests_per_second=8.0),
        )
    )
    report = harness.run()
    assert report["status"] == "COMPLETE"
    # Deterministic executor submission order (not concurrent transport entry).
    submitted = list(harness.submission_order)
    assert submitted
    orgs = set(submitted)
    assert len(orgs) == 2, submitted[:12]
    for k in range(1, len(submitted) + 1):
        prefix = submitted[:k]
        counts = [prefix.count(o) for o in orgs]
        assert max(counts) - min(counts) <= 1, (k, counts, prefix[:20])
    assert len(transport.calls) == LOGICAL_CALL_CEILING


def test_live_lock_subprocess_contention_before_run_creation(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """First live harness owns OS lock through terminal; subprocess fails before run creation."""
    import subprocess
    import sys
    import textwrap

    _patch_plan(monkeypatch, plan)
    transport = FakeTransport()
    transport.entered = threading.Event()
    transport.block_until = threading.Event()
    result: dict[str, Any] = {}

    def _run_live() -> None:
        result["report"] = PairEventV2MatrixHarness(
            MatrixConfig(
                registry_store_root=reg_root,
                output_root=out_root,
                mode="execute_live",
                primary_rpc_url=_TEST_PRIMARY_RPC,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                    confirm_matrix_id=plan.matrix_id,
                transport=transport,
                budgets=MatrixBudgets(
                    max_in_flight=1,
                    requests_per_second=8.0,
                    max_wall_seconds=120.0,
                ),
            )
        ).run()

    thr = threading.Thread(target=_run_live, name="live-lock-owner")
    thr.start()
    assert transport.entered.wait(timeout=30.0)
    # While live harness holds lock and is mid-execution, child process fails acquire.
    child = textwrap.dedent(
        f"""
        from pathlib import Path
        from cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix import (
            LiveOutputLock, MatrixSafetyStop,
        )
        try:
            LiveOutputLock(Path({str(out_root.resolve())!r})).acquire()
        except MatrixSafetyStop as exc:
            if "live matrix lock" in str(exc):
                raise SystemExit(0)
            raise SystemExit(2)
        raise SystemExit(3)
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", child],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path.cwd()),
    )
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert (out_root / ".matrix_live.lock").exists()
    # No second run directory from child; owner still in flight.
    transport.block_until.set()
    thr.join(timeout=600.0)
    assert thr.is_alive() is False
    report = result["report"]
    assert report["status"] in {"COMPLETE", "FAILED"}
    # After terminal, lock released: reacquire succeeds.
    again = LiveOutputLock(out_root)
    again.acquire()
    again.release()


def test_runtime_scanner_bound_to_live_run_not_plan(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live run scanner rejects exact runtime endpoint; plan-only run does not share it."""
    _patch_plan(monkeypatch, plan)
    secret = "SECRETprojectkey001"
    endpoint = f"https://mainnet.infura.io/v3/{secret}"
    # Plan-only with form-only scanner may still write plan without endpoint secrets.
    plan_report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root / "plan_root",
            mode="plan_only",
        )
    ).run()
    assert plan_report["status"] == "COMPLETE"
    assert plan_report["pass"] is False
    # Live injects runtime scanner on its MatrixRun only.
    transport = FakeTransport()
    # Force one scalar body to echo the secret endpoint.
    transport.body_override["infura:eth_getLogs"] = (
        f'{{"jsonrpc":"2.0","id":1,"result":[],"note":"{endpoint}"}}'.encode()
    )
    live_report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root / "live_root",
            mode="execute_live",
            confirm_matrix_id=plan.matrix_id,
            transport=transport,
            budgets=MatrixBudgets(max_in_flight=4, requests_per_second=8.0),
            primary_rpc_url=endpoint,
            secondary_rpc_url="https://ethereum.blockpi.network/v1/rpc/SECRETblockpikey02",
        )
    ).run()
    # Credential hit becomes safety stop or failed cells; secrets never sealed.
    blob = json.dumps(live_report)
    assert secret not in blob
    assert endpoint not in blob


def test_hard_blockers_credential_and_malformed_not_capacity(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Credential and malformed batch failures hard-block; never capacity selection."""
    # Credential on large batches.
    run = MatrixRun(
        out_root / "cred",
        credential_scanner=CredentialScanner.from_rpc_urls(
            "https://mainnet.infura.io/v3/SECRETprojectkey001"
        ),
    )
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
        elif call.kind == "scalar":
            _seed_receipt(run, call, body=empty)
        else:
            size = int(call.cohort_size or 0)
            if size <= 8:
                _seed_receipt(run, call, body=empty)
            else:
                # Echo runtime secret → credential_detection, no success body.
                body = b'{"jsonrpc":"2.0","id":1,"result":[],"x":"SECRETprojectkey001"}'
                _seed_receipt(run, call, body=body)
    cells = evaluate_cells(run, plan)
    large = [c for c in cells if int(c["cohort_size"]) >= 32]
    assert large
    assert all(c["failure_class"] == "credential_or_endpoint" for c in large)
    sel = select_capacity_from_cells(cells)
    assert sel["selection_valid"] is False
    assert any("credential_or_endpoint" in b for b in sel["blocking_reasons"])

    # Malformed eth_getLogs result type → safety stop on evaluate, not capacity.
    run2 = MatrixRun(out_root / "mal")
    run2.write_plan_and_catalog(plan)
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run2, call, body=_chain_body())
        elif call.kind == "scalar":
            _seed_receipt(run2, call, body=empty)
        else:
            _seed_receipt(
                run2,
                call,
                body=b'{"jsonrpc":"2.0","id":1,"result":"not-a-list"}',
            )
    with pytest.raises(MatrixSafetyStop, match="list|malformed"):
        evaluate_cells(run2, plan)


def test_standalone_replay_requires_live_capacity_selection_equality(
    out_root: Path, reg_root: Path, plan: MatrixPlan
) -> None:
    """Standalone replay requires sealed live capacity_selection equality; forged fails auth."""
    run = MatrixRun(out_root / "live_ok")
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        body = _chain_body() if call.kind == "chain" else empty
        _seed_receipt(run, call, body=body)
    cells = evaluate_cells(run, plan)
    assert all(c["status"] == "pass" for c in cells)
    selection = select_capacity_from_cells(cells)
    assert selection["selection_valid"] is True
    assert selection["selected_cohort_size"] == 128
    report = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "matrix_id": plan.matrix_id,
        "mode": "execute_live",
        "complete": True,
        "pass": True,
        "plan": plan.to_public_dict(),
        "cells": cells,
        "capacity_selection": selection,
        "budgets": MatrixBudgets().as_dict(),
        "cumulative_counters": {
            "logical_calls_started": LOGICAL_CALL_CEILING,
            "provider_attempts": LOGICAL_CALL_CEILING,
            "retained_response_bytes": 0,
            "http_429_count": 0,
            "high_water_in_flight": 1,
        },
        "offline_replay": {
            "kind": "in_process_disk_replay",
            "authenticated": True,
            "all_cells_pass": True,
            "selection_valid": True,
            "selected_cohort_size": selection["selected_cohort_size"],
        },
        "credential_scan": "pass",
        "all_cells_pass": True,
    }
    sealed = run.seal(kind="COMPLETE", report=report)
    live_dir = Path(sealed["run_dir"])
    auth = authenticate_completed_run(live_dir, require_live_pass=True)
    assert auth["capacity_selection"]["selected_cohort_size"] == 128

    replay_out = out_root / "replay_ok"
    replay_out.mkdir()
    replay = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=replay_out,
            mode="offline_replay",
            live_run_dir=live_dir,
        )
    ).run()
    assert replay["pass"] is True
    assert replay["capacity_selection"]["selected_cohort_size"] == 128

    bad_run = MatrixRun(out_root / "live_bad")
    bad_run.write_plan_and_catalog(plan)
    for call in iter_logical_calls(plan):
        body = _chain_body() if call.kind == "chain" else empty
        _seed_receipt(bad_run, call, body=body)
    cells_bad = evaluate_cells(bad_run, plan)
    true_sel = select_capacity_from_cells(cells_bad)
    forged = dict(true_sel)
    forged["selected_cohort_size"] = 8
    forged["nested_prefix"] = [1, 8]
    forged["viable_sizes"] = [1, 8]
    forged["selection_valid"] = True
    forged["all_cells_pass"] = False
    bad_report = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "matrix_id": plan.matrix_id,
        "mode": "execute_live",
        "complete": True,
        "pass": True,
        "plan": plan.to_public_dict(),
        "cells": cells_bad,
        "capacity_selection": forged,
        "budgets": MatrixBudgets().as_dict(),
        "cumulative_counters": {
            "logical_calls_started": LOGICAL_CALL_CEILING,
            "provider_attempts": LOGICAL_CALL_CEILING,
            "retained_response_bytes": 0,
            "http_429_count": 0,
            "high_water_in_flight": 1,
        },
        "offline_replay": {
            "kind": "in_process_disk_replay",
            "authenticated": True,
            "selection_valid": True,
            "selected_cohort_size": 8,
        },
        "credential_scan": "pass",
        "all_cells_pass": False,
    }
    bad_sealed = bad_run.seal(kind="COMPLETE", report=bad_report)
    bad_dir = Path(bad_sealed["run_dir"])
    with pytest.raises(MatrixSafetyStop, match="capacity_selection"):
        authenticate_completed_run(bad_dir)
    with pytest.raises(MatrixSafetyStop, match="capacity_selection"):
        authenticate_completed_run(bad_dir, require_live_pass=True)
    bad_replay_out = out_root / "replay_bad"
    bad_replay_out.mkdir()
    with pytest.raises(MatrixSafetyStop, match="capacity_selection"):
        PairEventV2MatrixHarness(
            MatrixConfig(
                registry_store_root=reg_root,
                output_root=bad_replay_out,
                mode="offline_replay",
                live_run_dir=bad_dir,
            )
        ).run()


def test_execute_live_acquires_lock_before_run(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public execute-live fails closed on lock before run creation; no second full live run."""
    _patch_plan(monkeypatch, plan)
    held = LiveOutputLock(out_root)
    held.acquire()
    try:
        transport = FakeTransport()
        with pytest.raises(MatrixSafetyStop, match="live matrix lock"):
            PairEventV2MatrixHarness(
                MatrixConfig(
                    registry_store_root=reg_root,
                    output_root=out_root,
                    mode="execute_live",
                    primary_rpc_url=_TEST_PRIMARY_RPC,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                    confirm_matrix_id=plan.matrix_id,
                    transport=transport,
                )
            ).run()
        runs_dir = out_root / "runs"
        if runs_dir.exists():
            assert list(runs_dir.glob("run_*")) == []
        assert transport.calls == []
    finally:
        held.release()
    again = LiveOutputLock(out_root)
    again.acquire()
    try:
        contender = LiveOutputLock(out_root)
        with pytest.raises(MatrixSafetyStop, match="live matrix lock"):
            contender.acquire()
    finally:
        again.release()



def test_mixed_attempt_hard_blocker_dominates_later_capacity(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Earlier 429 attempt hard-blocks even when a later attempt is capacity-classified."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
            continue
        if call.kind == "scalar":
            _seed_receipt(run, call, body=empty)
            continue
        # Attempt 1: 429; attempt 2: explicit capacity error only.
        run.retain_bytes(
            call=call,
            attempt=1,
            body=_HTTP_429_BODY,
            max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
            status_code=429,
            latency_ms=0.01,
            http_429=True,
            error_class="http_429",
            error_detail="rate limit",
        )
        run.retain_bytes(
            call=call,
            attempt=2,
            body=_CAPACITY_RPC_BODY,
            max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
            status_code=200,
            latency_ms=0.01,
            http_429=False,
            error_class=None,
            error_detail=None,
        )
    cells = evaluate_cells(run, plan)
    assert all(c["failure_class"] == "quota_or_429" for c in cells)
    sel = select_capacity_from_cells(cells)
    assert sel["selection_valid"] is False
    assert any("quota_or_429" in b for b in sel["blocking_reasons"])
    assert sel["capacity_failure_cells"] == []


def test_mixed_attempt_429_then_success_still_hard_blocks(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Hard blocker on any attempt dominates a later successful body."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
            continue
        if call.kind == "scalar":
            # One scalar call: 429 then success — must hard-block the cell path.
            if (
                call.provider_org == "infura"
                and call.range_name == "sparse"
                and call.address == plan.maximum_cohort[0]
                and call.topic == plan.topics[0]
            ):
                run.retain_bytes(
                    call=call,
                    attempt=1,
                    body=_HTTP_429_BODY,
                    max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
                    status_code=429,
                    latency_ms=0.01,
                    http_429=True,
                    error_class="http_429",
                    error_detail="rate limit",
                )
                run.retain_bytes(
                    call=call,
                    attempt=2,
                    body=empty,
                    max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
                    status_code=200,
                    latency_ms=0.01,
                    http_429=False,
                    error_class=None,
                    error_detail=None,
                )
            else:
                _seed_receipt(run, call, body=empty)
            continue
        _seed_receipt(run, call, body=empty)
    cells = evaluate_cells(run, plan)
    # At least sparse:cohort1 fails quota due to the poisoned scalar.
    bad = [c for c in cells if c["status"] != "pass"]
    assert bad
    assert any(c["failure_class"] == "quota_or_429" for c in bad)
    sel = select_capacity_from_cells(cells)
    assert sel["selection_valid"] is False


def test_http_401_is_hard_blocker(out_root: Path, plan: MatrixPlan) -> None:
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
        elif call.kind == "scalar":
            _seed_receipt(run, call, body=empty)
        else:
            run.retain_bytes(
                call=call,
                attempt=1,
                body=b'{"jsonrpc":"2.0","id":1,"error":{"message":"Unauthorized"}}',
                max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
                status_code=401,
                latency_ms=0.01,
                http_429=False,
                error_class=None,
                error_detail=None,
            )
    cells = evaluate_cells(run, plan)
    assert all(c["failure_class"] == "blocking_failure" for c in cells)
    assert select_capacity_from_cells(cells)["selection_valid"] is False


def test_http_403_is_hard_blocker(out_root: Path, plan: MatrixPlan) -> None:
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
        elif call.kind == "scalar":
            _seed_receipt(run, call, body=empty)
        else:
            run.retain_bytes(
                call=call,
                attempt=1,
                body=b'{"jsonrpc":"2.0","id":1,"error":{"message":"Forbidden"}}',
                max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
                status_code=403,
                latency_ms=0.01,
                http_429=False,
                error_class=None,
                error_detail=None,
            )
    cells = evaluate_cells(run, plan)
    assert all(c["failure_class"] == "blocking_failure" for c in cells)
    assert select_capacity_from_cells(cells)["selection_valid"] is False
    # Ordinary HTTP status detail must remain non-credential and unredacted.
    batch_rows = run.list_receipts(
        f"batch:sparse:1:{plan.provider_orgs[0]}"
    )
    assert batch_rows
    assert batch_rows[-1].get("error_class") == "http_403"
    assert "redacted_credential" not in str(batch_rows[-1].get("error_detail") or "")


def test_authorization_detail_with_credential_material_classifies_credential(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Real endpoint/secret in error detail → credential_or_endpoint; detail not persisted."""
    secret = "SECRETprojectkey001"
    endpoint = f"https://mainnet.infura.io/v3/{secret}"
    run = MatrixRun(
        out_root,
        credential_scanner=CredentialScanner.from_rpc_urls(endpoint),
    )
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
        elif call.kind == "scalar":
            _seed_receipt(run, call, body=empty)
        else:
            # 401 body/detail carries the exact runtime endpoint secret.
            run.retain_bytes(
                call=call,
                attempt=1,
                body=(
                    b'{"jsonrpc":"2.0","id":1,"error":{"message":"Unauthorized at '
                    + endpoint.encode()
                    + b'"}}'
                ),
                max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
                status_code=401,
                latency_ms=0.01,
                http_429=False,
                error_class=None,
                error_detail=f"Unauthorized endpoint {endpoint}",
            )
    cells = evaluate_cells(run, plan)
    assert all(c["failure_class"] == "credential_or_endpoint" for c in cells)
    sel = select_capacity_from_cells(cells)
    assert sel["selection_valid"] is False
    assert any("credential_or_endpoint" in b for b in sel["blocking_reasons"])
    # Credential material is not retained in receipts or raw objects.
    for path in run.receipts_dir.glob("batch__*.json"):
        text = path.read_text(encoding="utf-8")
        assert secret not in text
        assert endpoint not in text
        rec = json.loads(text)
        if rec.get("error_class"):
            assert rec["error_class"] == "credential_detection"
            assert rec.get("error_detail") == "redacted_credential_or_endpoint"
    for raw in run.raw_dir.glob("*.bin"):
        data = raw.read_bytes()
        assert secret.encode() not in data
        assert endpoint.encode() not in data


def test_credential_detection_precedes_http_429_classification(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Scanner-detected secret with HTTP 429 → credential_or_endpoint, not quota_or_429."""
    secret = "SECRETprojectkey001"
    endpoint = f"https://mainnet.infura.io/v3/{secret}"
    run = MatrixRun(
        out_root,
        credential_scanner=CredentialScanner.from_rpc_urls(endpoint),
    )
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
        elif call.kind == "scalar":
            _seed_receipt(run, call, body=empty)
        else:
            # Mixed signals: HTTP 429 status plus scanner-detected endpoint in detail.
            run.retain_bytes(
                call=call,
                attempt=1,
                body=b'{"jsonrpc":"2.0","id":1,"error":{"message":"rate limited"}}',
                max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
                status_code=429,
                latency_ms=0.01,
                http_429=True,
                error_class=None,
                error_detail=f"Too Many Requests see {endpoint}",
            )
    cells = evaluate_cells(run, plan)
    assert all(c["failure_class"] == "credential_or_endpoint" for c in cells), cells[0]
    sel = select_capacity_from_cells(cells)
    assert sel["selection_valid"] is False
    assert any("credential_or_endpoint" in b for b in sel["blocking_reasons"])
    assert not any("quota_or_429" in b for b in sel["blocking_reasons"])
    for path in run.receipts_dir.glob("batch__*.json"):
        rec = json.loads(path.read_text(encoding="utf-8"))
        if not rec.get("error_class"):
            continue
        assert rec["error_class"] == "credential_detection"
        assert rec.get("error_detail") == "redacted_credential_or_endpoint"
        assert secret not in path.read_text(encoding="utf-8")
        assert endpoint not in path.read_text(encoding="utf-8")
    for raw in run.raw_dir.glob("*.bin"):
        data = raw.read_bytes()
        assert secret.encode() not in data
        assert endpoint.encode() not in data


def test_mixed_provider_scalar_hard_block_dominance(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Scalar: capacity-only no-success on one provider does not hide the other's quota."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
            continue
        if call.kind == "scalar":
            if call.provider_org == "infura":
                # Primary: capacity-classified failures only, no success body.
                _seed_receipt(run, call, body=_CAPACITY_RPC_BODY)
            else:
                # Secondary: 429 hard blocker.
                run.retain_bytes(
                    call=call,
                    attempt=1,
                    body=_HTTP_429_BODY,
                    max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
                    status_code=429,
                    latency_ms=0.01,
                    http_429=True,
                    error_class="http_429",
                    error_detail="rate limit",
                )
            continue
        # Valid empty batches so evaluation reaches scalar decision only.
        _seed_receipt(run, call, body=empty)
    cells = evaluate_cells(run, plan)
    assert all(c["status"] == "fail" for c in cells)
    # Quota from secondary must dominate primary scalar_failure fallback.
    assert all(c["failure_class"] == "quota_or_429" for c in cells)
    sel = select_capacity_from_cells(cells)
    assert sel["selection_valid"] is False
    assert any("quota_or_429" in b for b in sel["blocking_reasons"])
    assert sel["capacity_failure_cells"] == []


def test_mixed_provider_batch_hard_block_dominance(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Batch: all scalars valid; one provider capacity, other 429 — hard block, not capacity."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
            continue
        if call.kind == "scalar":
            _seed_receipt(run, call, body=empty)
            continue
        # Batches: primary explicit capacity, secondary hard 429.
        if call.provider_org == "infura":
            _seed_receipt(run, call, body=_CAPACITY_RPC_BODY)
        else:
            run.retain_bytes(
                call=call,
                attempt=1,
                body=_HTTP_429_BODY,
                max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
                status_code=429,
                latency_ms=0.01,
                http_429=True,
                error_class="http_429",
                error_detail="rate limit",
            )
    cells = evaluate_cells(run, plan)
    assert all(c["status"] == "fail" for c in cells)
    assert all(c["failure_class"] == "quota_or_429" for c in cells)
    sel = select_capacity_from_cells(cells)
    assert sel["selection_valid"] is False
    assert any("quota_or_429" in b for b in sel["blocking_reasons"])
    assert sel["capacity_failure_cells"] == []


def test_ambiguous_timeout_hard_blocks_explicit_size_is_capacity() -> None:
    from cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix import (
        parse_json_rpc_result,
        MatrixCellFailure,
    )

    try:
        parse_json_rpc_result(
            b'{"jsonrpc":"2.0","id":1,"error":{"message":"request timeout after 30s"}}'
        )
        raise AssertionError("expected failure")
    except MatrixCellFailure as exc:
        assert exc.message == "ambiguous_timeout"
    try:
        parse_json_rpc_result(
            b'{"jsonrpc":"2.0","id":1,"error":{"message":"query returned more than 10000 results"}}'
        )
        raise AssertionError("expected failure")
    except MatrixCellFailure as exc:
        assert exc.message == "provider_limit_or_size"


def test_execute_live_injected_transport_requires_scanner_urls(
    out_root: Path, reg_root: Path, plan: MatrixPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_plan(monkeypatch, plan)
    with pytest.raises(MatrixError, match="scanner|primary_rpc_url"):
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            confirm_matrix_id=plan.matrix_id,
            transport=FakeTransport(),
        )


def test_generic_v3_path_slug_not_secret() -> None:
    """Reject exact configured generic endpoint; allow identical non-secret slug on other host."""
    # Configure a non-Infura/non-BlockPI endpoint with a long /v3/ slug (not extracted).
    slug = "notarealsecretpathslugXX"
    configured = f"https://docs.example.com/v3/{slug}"
    other_host = f"https://help.other.example/v3/{slug}"
    scanner = CredentialScanner.from_rpc_urls(configured)
    # Full configured endpoint is an exact forbidden needle.
    with pytest.raises(MatrixSafetyStop, match="credential"):
        scanner.scan_text(configured, label="exact_endpoint")
    # Path slug itself is NOT extracted for generic hosts.
    assert slug not in scanner.forbidden_substrings
    # Same non-secret slug on a different host/URL is allowed.
    scanner.scan_text(other_host, label="other_host_same_slug")
    scanner.scan_text(f"see docs at {other_host}", label="docs_mention")
    # Frozen Infura form still extracts project key as a secret.
    inf = CredentialScanner.from_rpc_urls(
        "https://mainnet.infura.io/v3/SECRETprojectkey001"
    )
    assert "SECRETprojectkey001" in inf.forbidden_substrings


def test_public_live_credential_detection_no_secret_raw_authority(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_plan(monkeypatch, plan)
    secret = "SECRETprojectkey001"
    endpoint = f"https://mainnet.infura.io/v3/{secret}"
    transport = FakeTransport()
    transport.body_override["infura:eth_getLogs"] = (
        f'{{"jsonrpc":"2.0","id":1,"result":[],"echo":"{endpoint}"}}'.encode()
    )
    report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            confirm_matrix_id=plan.matrix_id,
            transport=transport,
            budgets=MatrixBudgets(max_in_flight=4, requests_per_second=8.0),
            primary_rpc_url=endpoint,
            secondary_rpc_url=_TEST_SECONDARY_RPC,
        )
    ).run()
    blob = json.dumps(report)
    assert secret not in blob
    assert endpoint not in blob
    run_dir = Path(report["run_dir"])
    # No raw object may contain the secret.
    for raw in (run_dir / "raw").glob("*.bin"):
        data = raw.read_bytes()
        assert secret.encode() not in data
        assert endpoint.encode() not in data
    # At least one receipt classified credential_detection.
    receipts = list((run_dir / "receipts").glob("*.json"))
    assert any(
        json.loads(path.read_text()).get("error_class") == "credential_detection"
        for path in receipts
    )


def test_generated_complete_non_pass_auth_and_replay_reject(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Single production-generated COMPLETE non-PASS authenticates; PASS-replay rejects."""
    _patch_plan(monkeypatch, plan)

    class _T(FakeTransport):
        def __call__(self, provider_org, request):  # type: ignore[no-untyped-def]
            method = str(request.get("method"))
            if method == "eth_getLogs":
                return TransportResult(
                    status_code=429,
                    body=_HTTP_429_BODY,
                    stream_response=None,
                    latency_ms=0.05,
                    http_429=True,
                    error_class="http_429",
                    error_detail="rate limit",
                )
            return super().__call__(provider_org, request)

    report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root,
            mode="execute_live",
            confirm_matrix_id=plan.matrix_id,
            transport=_T(),
            budgets=MatrixBudgets(max_in_flight=4, requests_per_second=8.0),
            primary_rpc_url=_TEST_PRIMARY_RPC,
            secondary_rpc_url=_TEST_SECONDARY_RPC,
        )
    ).run()
    assert report["status"] == "COMPLETE"
    assert report["pass"] is False
    run_dir = Path(report["run_dir"])
    auth = authenticate_completed_run(run_dir)
    assert auth["pass"] is False
    with pytest.raises(MatrixError, match="pass=true"):
        authenticate_completed_run(run_dir, require_live_pass=True)


def test_concurrent_plan_replay_scanner_isolation(
    out_root: Path, reg_root: Path, plan: MatrixPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plan-only and offline replay run while live scanner is active (deterministic overlap)."""
    _patch_plan(monkeypatch, plan)
    secret = "SECRETprojectkey001"
    endpoint = f"https://mainnet.infura.io/v3/{secret}"
    # Pre-build a valid PASS live seal for offline replay under a separate root.
    seed_root = out_root / "seed_live"
    seed_run = MatrixRun(seed_root)
    seed_run.write_plan_and_catalog(plan)
    _seed_full_success(seed_run, plan)
    cells = evaluate_cells(seed_run, plan)
    selection = select_capacity_from_cells(cells)
    sealed = seed_run.seal(
        kind="COMPLETE",
        report={
            "schema_version": MATRIX_SCHEMA_VERSION,
            "matrix_id": plan.matrix_id,
            "mode": "execute_live",
            "complete": True,
            "pass": True,
            "plan": plan.to_public_dict(),
            "cells": cells,
            "capacity_selection": selection,
            "budgets": MatrixBudgets().as_dict(),
            "cumulative_counters": {
                "logical_calls_started": LOGICAL_CALL_CEILING,
                "provider_attempts": LOGICAL_CALL_CEILING,
                "retained_response_bytes": 0,
                "http_429_count": 0,
                "high_water_in_flight": 1,
            },
            "offline_replay": {
                "kind": "in_process_disk_replay",
                "authenticated": True,
                "selection_valid": True,
                "selected_cohort_size": selection["selected_cohort_size"],
            },
            "credential_scan": "pass",
            "all_cells_pass": True,
        },
    )
    live_src = Path(sealed["run_dir"])

    live_active = threading.Event()
    release_live = threading.Event()
    plan_done = threading.Event()
    replay_done = threading.Event()
    results: dict[str, Any] = {}
    errors: list[BaseException] = []

    class BlockingLiveTransport(FakeTransport):
        def __call__(self, provider_org: str, request: Mapping[str, Any]) -> TransportResult:
            # First provider call: scanner is already bound on the live MatrixRun.
            if not live_active.is_set():
                live_active.set()
                # Hold until plan-only and offline replay finish during live activity.
                if not release_live.wait(timeout=600.0):
                    raise RuntimeError("release_live timeout")
            return super().__call__(provider_org, request)

    def _live() -> None:
        try:
            results["live"] = PairEventV2MatrixHarness(
                MatrixConfig(
                    registry_store_root=reg_root,
                    output_root=out_root / "live_iso",
                    mode="execute_live",
                    confirm_matrix_id=plan.matrix_id,
                    transport=BlockingLiveTransport(),
                    budgets=MatrixBudgets(max_in_flight=4, requests_per_second=8.0),
                    primary_rpc_url=endpoint,
                    secondary_rpc_url=_TEST_SECONDARY_RPC,
                )
            ).run()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    thr_live = threading.Thread(target=_live, name="iso-live")
    thr_live.start()
    assert live_active.wait(timeout=120.0)

    def _plan() -> None:
        try:
            results["plan"] = PairEventV2MatrixHarness(
                MatrixConfig(
                    registry_store_root=reg_root,
                    output_root=out_root / "plan_iso",
                    mode="plan_only",
                )
            ).run()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            plan_done.set()

    def _replay() -> None:
        try:
            results["replay"] = PairEventV2MatrixHarness(
                MatrixConfig(
                    registry_store_root=reg_root,
                    output_root=out_root / "replay_iso",
                    mode="offline_replay",
                    live_run_dir=live_src,
                )
            ).run()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            replay_done.set()

    thr_plan = threading.Thread(target=_plan, name="iso-plan")
    thr_replay = threading.Thread(target=_replay, name="iso-replay")
    thr_plan.start()
    thr_replay.start()
    assert plan_done.wait(timeout=120.0)
    assert replay_done.wait(timeout=120.0)
    thr_plan.join(timeout=30.0)
    thr_replay.join(timeout=30.0)
    # Release live after plan and replay completed while its scanner was active.
    release_live.set()
    thr_live.join(timeout=900.0)
    assert not errors, errors
    assert results["plan"]["status"] == "COMPLETE"
    assert results["replay"]["pass"] is True
    assert secret not in json.dumps(results["plan"])
    assert secret not in json.dumps(results["replay"])
    assert secret not in json.dumps(results["live"])


def test_missing_scalar_evidence_incomplete_and_failed_terminal(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public harness: chain-only execution leaves scalars absent → incomplete + FAILED."""
    _patch_plan(monkeypatch, plan)

    # Inject only the execution phase through chain auth; leave scalar/batch receipts absent.
    def _chain_only(self, run, plan_arg):  # type: ignore[no-untyped-def]
        self._auth_chain(run, plan_arg)

    monkeypatch.setattr(
        PairEventV2MatrixHarness,
        "_execute_live_calls",
        _chain_only,
    )
    report = PairEventV2MatrixHarness(
        MatrixConfig(
            registry_store_root=reg_root,
            output_root=out_root / "failed_term",
            mode="execute_live",
            confirm_matrix_id=plan.matrix_id,
            transport=FakeTransport(),
            budgets=MatrixBudgets(max_in_flight=4, requests_per_second=8.0),
            primary_rpc_url=_TEST_PRIMARY_RPC,
            secondary_rpc_url=_TEST_SECONDARY_RPC,
        )
    ).run()
    assert report["status"] == "FAILED"
    assert report["complete"] is False
    assert report["pass"] is False
    cells = report.get("cells") or []
    assert cells
    assert all(c.get("status") == "incomplete" for c in cells)
    # Unmodified disk evaluate_cells on the sealed run also reports incomplete.
    from cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix import (
        _ReadOnlyRun,
    )

    disk = evaluate_cells(_ReadOnlyRun(Path(report["run_dir"])), plan)
    assert all(c["status"] == "incomplete" for c in disk)


def test_missing_scalar_plus_stronger_blocker_keeps_incomplete_status(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Missing required scalar keeps status incomplete while failure_class is stronger."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
            continue
        if call.kind == "scalar":
            if call.provider_org == "infura":
                # Leave all primary scalar receipts absent → incomplete.
                continue
            # Secondary: quota hard blocker with no success.
            run.retain_bytes(
                call=call,
                attempt=1,
                body=_HTTP_429_BODY,
                max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
                status_code=429,
                latency_ms=0.01,
                http_429=True,
                error_class="http_429",
                error_detail="rate limit",
            )
            continue
        _seed_receipt(run, call, body=empty)
    cells = evaluate_cells(run, plan)
    assert all(c["status"] == "incomplete" for c in cells)
    # Stronger quota class retained; not erased by incomplete completeness bit.
    assert all(c["failure_class"] == "quota_or_429" for c in cells)


def test_scalar_raw_integrity_safety_stop_propagates(
    out_root: Path, plan: MatrixPlan
) -> None:
    """Missing/mismatched raw body is evidence-integrity safety stop, not cell failure."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    empty = _empty_logs_body()
    for call in iter_logical_calls(plan):
        if call.kind == "chain":
            _seed_receipt(run, call, body=_chain_body())
        else:
            _seed_receipt(run, call, body=empty)
    # Tamper one scalar success receipt to reference a missing raw object.
    lid = None
    for call in iter_logical_calls(plan):
        if call.kind == "scalar" and call.provider_org == "infura":
            lid = call.logical_call_id
            break
    assert lid is not None
    rec_path = next((run.receipts_dir).glob(f"{lid.replace(':', '__')}__a1.json"))
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    rec["body_sha256"] = "ab" * 32
    rec["body_bytes"] = 0
    rec["success"] = True
    rec_path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(MatrixSafetyStop, match="retained body|missing|SHA-256|byte count"):
        evaluate_cells(run, plan)


def test_subprocess_competing_public_harness_during_blocked_seal(
    out_root: Path,
    reg_root: Path,
    plan: MatrixPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Competing public harness fails lock while owner is blocked inside MatrixRun.seal."""
    import subprocess
    import sys
    import textwrap

    _patch_plan(monkeypatch, plan)
    entered = threading.Event()
    cont = threading.Event()
    orig = MatrixRun.seal

    def _blocked_seal(self, **kwargs):  # type: ignore[no-untyped-def]
        entered.set()
        cont.wait(timeout=120.0)
        return orig(self, **kwargs)

    monkeypatch.setattr(MatrixRun, "seal", _blocked_seal)
    result: dict[str, Any] = {}

    def _owner() -> None:
        result["report"] = PairEventV2MatrixHarness(
            MatrixConfig(
                registry_store_root=reg_root,
                output_root=out_root,
                mode="execute_live",
                confirm_matrix_id=plan.matrix_id,
                transport=FakeTransport(),
                budgets=MatrixBudgets(max_in_flight=4, requests_per_second=8.0),
                primary_rpc_url=_TEST_PRIMARY_RPC,
                secondary_rpc_url=_TEST_SECONDARY_RPC,
            )
        ).run()

    thr = threading.Thread(target=_owner, name="seal-owner")
    thr.start()
    assert entered.wait(timeout=600.0)
    # Child-local plan fixture so contender reaches lock acquisition (not registry miss).
    plan_path = out_root / "_child_plan.json"
    plan_path.write_text(json.dumps(plan.to_public_dict()), encoding="utf-8")
    child = textwrap.dedent(
        f"""
        import json
        from pathlib import Path
        import cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix as m
        from cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix import (
            MatrixConfig, MatrixPlan, PairEventV2MatrixHarness, MatrixSafetyStop, MatrixError,
            TransportResult,
        )
        plan = MatrixPlan.from_public_dict(json.loads(Path({str(plan_path.resolve())!r}).read_text()))
        m.build_matrix_plan = lambda **_k: plan
        class T:
            def __call__(self, org, request):
                method = str(request.get("method"))
                body = b'{{"jsonrpc":"2.0","id":1,"result":"0x1"}}' if method == "eth_chainId" else b'{{"jsonrpc":"2.0","id":1,"result":[]}}'
                return TransportResult(200, body, None, 0.01, False, None, None)
            def close(self):
                pass
        try:
            PairEventV2MatrixHarness(MatrixConfig(
                registry_store_root=Path({str(reg_root.resolve())!r}),
                output_root=Path({str(out_root.resolve())!r}),
                mode="execute_live",
                confirm_matrix_id=plan.matrix_id,
                transport=T(),
                primary_rpc_url="https://mainnet.infura.io/v3/SECRETprojectkey001",
                secondary_rpc_url="https://ethereum.blockpi.network/v1/rpc/SECRETblockpikey02",
            )).run()
        except (MatrixSafetyStop, MatrixError) as exc:
            if "live matrix lock" in str(exc):
                raise SystemExit(0)
            raise SystemExit(2)
        raise SystemExit(3)
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", child],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(Path.cwd()),
    )
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    cont.set()
    thr.join(timeout=600.0)
    assert thr.is_alive() is False


def test_topology_omission_unknown_mismatched_cell_id_branches() -> None:
    from cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix import (
        validate_cell_topology,
    )

    base = []
    for range_name in ("sparse", "medium", "hot"):
        for size in NESTED_COHORT_SIZES:
            base.append(
                {
                    "range_name": range_name,
                    "cohort_size": size,
                    "cell_id": f"{range_name}:cohort{size}",
                    "status": "pass",
                    "failure_class": None,
                }
            )
    # Omission
    with pytest.raises(MatrixSafetyStop, match="missing|exactly 15"):
        validate_cell_topology(base[:-1])
    # Unknown range
    unknown = list(base)
    unknown[0] = {
        **unknown[0],
        "range_name": "cold",
        "cell_id": "cold:cohort1",
    }
    with pytest.raises(MatrixSafetyStop, match="unknown"):
        validate_cell_topology(unknown)
    # Unknown size
    bad_size = list(base)
    bad_size[0] = {
        "range_name": "sparse",
        "cohort_size": 2,
        "cell_id": "sparse:cohort2",
        "status": "pass",
        "failure_class": None,
    }
    with pytest.raises(MatrixSafetyStop, match="unknown"):
        validate_cell_topology(bad_size)
    # Mismatched cell_id
    mismatch = list(base)
    mismatch[0] = {**mismatch[0], "cell_id": "sparse:cohort8"}
    with pytest.raises(MatrixSafetyStop, match="cell_id"):
        validate_cell_topology(mismatch)
