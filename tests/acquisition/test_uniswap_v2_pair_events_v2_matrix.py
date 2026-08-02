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
from cryptofactors.acquisition.uniswap_v2_pair_events_v2 import (
    LOG_IDENTITY_VERSION,
    ORDERED_EVENT_TOPICS,
)
from cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix import (
    ANCHOR_POOL,
    BIRTH_BOUNDARY_BLOCK,
    DEFAULT_PROVIDER_ORGS,
    LOGICAL_CALL_CEILING,
    MATRIX_RANGES,
    MATRIX_SCHEMA_VERSION,
    NESTED_COHORT_SIZES,
    STREAM_CHUNK_BYTES,
    V1_ANCHOR_SWAP_LOG_COUNTS,
    BudgetTracker,
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
    iter_logical_calls,
    parse_json_rpc_result,
)


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
        self.closed = False
        self.in_flight = 0
        self.high_water = 0
        self._lock = threading.Lock()
        self.hold: dict[str, threading.Event] = {}
        self.body_override: dict[str, bytes] = {}

    def __call__(self, provider_org: str, request: Mapping[str, Any]) -> TransportResult:
        with self._lock:
            self.in_flight += 1
            self.high_water = max(self.high_water, self.in_flight)
        try:
            method = str(request.get("method"))
            self.calls.append((provider_org, method))
            hold = self.hold.get(provider_org)
            if hold is not None:
                hold.wait(timeout=5.0)
            key = f"{provider_org}:{method}"
            body = self.body_override.get(key)
            if body is None:
                body = _chain_body() if method == "eth_chainId" else _empty_logs()
            return TransportResult(
                status_code=200,
                body=body,
                stream_response=None,
                latency_ms=0.05,
                http_429=False,
                error_class=None,
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
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    call = iter_logical_calls(plan)[0]
    max_b = 64
    r1 = run.retain_bytes(
        call=call,
        attempt=1,
        body=b'{"x":"https://evil.example/v3/KEY"}',
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
    body = prefix + b"https://leak.example/token"
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
        body=(b"n" * max_b) + b"?api_key=supersecret",
        max_response_bytes=max_b,
        status_code=200,
        latency_ms=1.0,
        http_429=False,
        error_class=None,
        error_detail=None,
    )
    assert r3["error_class"] == "credential_detection"


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
    """Secret straddles STREAM_CHUNK_BYTES (65,536) boundary — detected pre-write."""
    run = MatrixRun(out_root)
    run.write_plan_and_catalog(plan)
    call = iter_logical_calls(plan)[0]
    secret = b"https://evil.example/key"
    # Cross the production streaming chunk boundary used by retain_bytes/stream.
    body = (b"n" * (STREAM_CHUNK_BYTES - 10)) + secret
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
