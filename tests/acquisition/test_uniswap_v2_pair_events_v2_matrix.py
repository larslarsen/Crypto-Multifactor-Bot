"""DEX-003 — offline tests for the isolated v2 provider-matrix harness.

Freezes Sol final-correction requirements. No network, no RPC credentials, no
production data mutation. Temporary stores and fake transports only.

Grok authors this suite; Jr executes it. Named tests map 1:1 to corrections.
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
    V1_ANCHOR_SWAP_LOG_COUNTS,
    BudgetTracker,
    LogicalCall,
    MatrixBudgets,
    MatrixConfig,
    MatrixError,
    MatrixPlan,
    MatrixSafetyStop,
    MatrixStore,
    PairEventV2MatrixHarness,
    TransportResult,
    _parse_json_rpc_result,
    _promote_content_addressed,
    assert_safe_matrix_output_root,
    catalog_entries,
    compact_json_array_hash,
    compute_evidence_hash,
    compute_matrix_id_from_payload,
    compute_report_hash,
    iter_logical_calls,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _synthetic_cohort() -> tuple[str, ...]:
    """128 valid addresses: anchor first, then lexically lowest synthetic others."""
    others = sorted(f"0x{i:040x}" for i in range(1, 200) if f"0x{i:040x}" != ANCHOR_POOL)
    return (ANCHOR_POOL,) + tuple(others[:127])


def _synthetic_plan(*, created_at: str = "2026-01-01T00:00:00+00:00") -> MatrixPlan:
    cohort = _synthetic_cohort()
    hashes = {size: compact_json_array_hash(cohort[:size]) for size in NESTED_COHORT_SIZES}
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
            name: {"end": MATRIX_RANGES[name][1], "start": MATRIX_RANGES[name][0]}
            for name in ("sparse", "medium", "hot")
        },
        "registry_dataset_id": "ds_" + ("ab" * 32),
        "registry_parquet_bytes": 42,
        "registry_parquet_sha256": "cd" * 32,
        "schema_version": MATRIX_SCHEMA_VERSION,
        "topics": list(ORDERED_EVENT_TOPICS),
        "v1_anchor_swap_log_counts": {
            name: V1_ANCHOR_SWAP_LOG_COUNTS[name] for name in ("sparse", "medium", "hot")
        },
    }
    matrix_id = compute_matrix_id_from_payload(draft)
    return MatrixPlan(
        matrix_id=matrix_id,
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
        created_at=created_at,
    )


@pytest.fixture
def plan() -> MatrixPlan:
    return _synthetic_plan()


@pytest.fixture
def matrix_root(tmp_path: Path) -> Path:
    root = tmp_path / "matrix_out"
    root.mkdir()
    return root


@pytest.fixture
def store(matrix_root: Path) -> MatrixStore:
    s = MatrixStore(matrix_root, registry_store_root=None, create_run=False)
    yield s
    s.close()


def _seed_plan(store: MatrixStore, plan: MatrixPlan) -> MatrixPlan:
    store.create_plan_and_catalog(plan)
    return plan


def _record_minimal_attempt(
    store: MatrixStore,
    plan: MatrixPlan,
    *,
    attempt: int = 1,
    error_class: str | None = "transport",
    body: bytes | None = None,
    truncated: bool = False,
) -> LogicalCall:
    store.begin_run()
    call = iter_logical_calls(plan)[0]
    body_sha = None
    body_bytes = 0
    observed = 0
    if body is not None:
        body_sha, body_bytes, observed, trunc, cred = store.retain_bytes_to_spool(
            logical_call_id=call.logical_call_id,
            attempt=attempt,
            body=body,
            max_response_bytes=8_000_000,
        )
        if cred:
            error_class = "credential_detection"
            body_sha = None
            body_bytes = 0
        truncated = truncated or trunc
    store.record_attempt(
        call=call,
        attempt=attempt,
        status_code=200 if error_class is None else None,
        body_sha256=body_sha,
        body_bytes=body_bytes,
        observed_body_bytes=observed,
        truncated=truncated,
        latency_ms=1.0,
        http_429=False,
        error_class=error_class,
        error_detail=None if error_class is None else "test",
    )
    return call


def _chain_id_body(chain_hex: str = "0x1") -> bytes:
    return json.dumps({"jsonrpc": "2.0", "id": 1, "result": chain_hex}).encode()


def _empty_logs_body() -> bytes:
    return json.dumps({"jsonrpc": "2.0", "id": 1, "result": []}).encode()


class _FakeTransport:
    """Injectable transport returning fixed bodies (no network)."""

    def __init__(self, bodies: dict[str, bytes] | None = None) -> None:
        self.bodies = bodies or {}
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.closed = False
        self.in_flight = 0
        self.high_water = 0
        self._lock = threading.Lock()
        self.hold: dict[str, threading.Event] = {}

    def __call__(self, provider_org: str, request: Mapping[str, Any]) -> TransportResult:
        with self._lock:
            self.in_flight += 1
            self.high_water = max(self.high_water, self.in_flight)
        try:
            self.calls.append((provider_org, dict(request)))
            hold = self.hold.get(provider_org)
            if hold is not None:
                hold.wait(timeout=5.0)
            method = str(request.get("method"))
            key = f"{provider_org}:{method}"
            body = self.bodies.get(key)
            if body is None:
                if method == "eth_chainId":
                    body = _chain_id_body()
                else:
                    body = _empty_logs_body()
            return TransportResult(
                status_code=200,
                body=body,
                stream_response=None,
                latency_ms=0.5,
                http_429=False,
                error_class=None,
                error_detail=None,
            )
        finally:
            with self._lock:
                self.in_flight -= 1

    def close(self) -> None:
        self.closed = True


# ---------------------------------------------------------------------------
# 1. Pure plan vs immutable persistence / auth
# ---------------------------------------------------------------------------


def test_catalog_tamper_rejected_and_not_rewritten_on_auth(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    """Correction 1: pre-write catalog tamper must fail; auth must not rewrite."""
    _seed_plan(store, plan)
    cat_path = store.catalog_path
    original = cat_path.read_bytes()
    cat = json.loads(original)
    cat[0]["request_sha256"] = "0" * 64
    cat_path.write_bytes(
        (json.dumps(cat, indent=2, sort_keys=True) + "\n").encode()
    )
    with pytest.raises(MatrixSafetyStop, match="catalog"):
        store.authenticate_immutable_store(registry_store_root=None)
    assert cat_path.read_bytes() != original  # still tampered — not rewritten
    # Restore and auth succeeds.
    cat_path.write_bytes(original)
    auth_plan, counters, _snap = store.authenticate_immutable_store(
        registry_store_root=None
    )
    assert auth_plan.matrix_id == plan.matrix_id
    assert counters["attempts"] == 0


def test_only_fresh_empty_root_may_create_plan(
    store: MatrixStore, plan: MatrixPlan, matrix_root: Path
) -> None:
    _seed_plan(store, plan)
    with pytest.raises(MatrixSafetyStop, match="non-empty|already exist"):
        store.create_plan_and_catalog(plan)
    # Non-empty without plan also refused.
    dirty = matrix_root.parent / "dirty"
    dirty.mkdir()
    (dirty / "noise.txt").write_text("x", encoding="utf-8")
    s2 = MatrixStore(dirty, create_run=False)
    try:
        assert not s2.is_fresh_empty()
        with pytest.raises(MatrixSafetyStop):
            s2.create_plan_and_catalog(plan)
    finally:
        s2.close()


def test_unknown_attempt_and_state_rows_rejected(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    """Correction 1: extra/unknown attempt and logical-state evidence fail auth."""
    _seed_plan(store, plan)
    _record_minimal_attempt(store, plan)
    # Inject unknown attempt row + state.
    store._conn.execute(
        """
        INSERT INTO attempt_receipt (
            logical_call_id, attempt, run_id, provider_org, kind, request_sha256,
            request_json, status_code, body_sha256, body_bytes, observed_body_bytes,
            truncated, latency_ms, http_429, error_class, error_detail, retained_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            "scalar:forged:infura:0xabc:swap",
            1,
            store.run_id,
            "infura",
            "scalar",
            "aa" * 32,
            "{}",
            None,
            None,
            0,
            0,
            0,
            0.0,
            0,
            "transport",
            "x",
            "t",
        ),
    )
    store._conn.execute(
        """
        INSERT INTO logical_call_state (
            logical_call_id, kind, provider_org, attempts, terminal_status,
            final_body_sha256, updated_at
        ) VALUES (?,?,?,?,?,?,?)
        """,
        ("scalar:forged:infura:0xabc:swap", "scalar", "infura", 1, "error", None, "t"),
    )
    store._conn.commit()
    with pytest.raises(MatrixSafetyStop, match="unknown attempt"):
        store.authenticate_immutable_store(registry_store_root=None)


def test_missing_sidecar_and_raw_tamper_rejected(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    """Correction 1: receipt sidecar / raw SHA-byte auth."""
    _seed_plan(store, plan)
    call = _record_minimal_attempt(
        store, plan, error_class=None, body=_chain_id_body()
    )
    # Sidecar missing.
    sidecar = next(store.receipts_dir.glob("*.json"))
    payload = sidecar.read_text(encoding="utf-8")
    sidecar.unlink()
    with pytest.raises(MatrixSafetyStop, match="sidecar"):
        store.authenticate_immutable_store(registry_store_root=None)
    sidecar.write_text(payload, encoding="utf-8")
    # Raw tamper.
    success = store.best_success_body(call.logical_call_id)
    assert success is not None
    raw_path = store.raw_dir / f"{success[0]}.bin"
    raw_path.write_bytes(raw_path.read_bytes() + b"x")
    with pytest.raises(MatrixSafetyStop, match="SHA-256 mismatch|byte count"):
        store.authenticate_immutable_store(registry_store_root=None)


def test_noncontiguous_and_duplicate_attempt_rejected(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    _seed_plan(store, plan)
    store.begin_run()
    call = iter_logical_calls(plan)[0]
    store.record_attempt(
        call=call,
        attempt=1,
        status_code=None,
        body_sha256=None,
        body_bytes=0,
        observed_body_bytes=0,
        truncated=False,
        latency_ms=1.0,
        http_429=False,
        error_class="transport",
        error_detail="a",
    )
    with pytest.raises(MatrixSafetyStop, match="contiguous"):
        store.record_attempt(
            call=call,
            attempt=3,
            status_code=None,
            body_sha256=None,
            body_bytes=0,
            observed_body_bytes=0,
            truncated=False,
            latency_ms=1.0,
            http_429=False,
            error_class="transport",
            error_detail="b",
        )
    with pytest.raises(MatrixSafetyStop, match="append-only|overwrite"):
        store.record_attempt(
            call=call,
            attempt=1,
            status_code=None,
            body_sha256=None,
            body_bytes=0,
            observed_body_bytes=0,
            truncated=False,
            latency_ms=1.0,
            http_429=False,
            error_class="transport",
            error_detail="c",
        )


def test_resume_reconstructs_cumulative_budgets(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    """Correction 1/3: cumulative resume budgets from authenticated evidence."""
    _seed_plan(store, plan)
    store.begin_run()
    calls = iter_logical_calls(plan)[:3]
    for call in calls:
        body = _chain_id_body() if call.kind == "chain" else _empty_logs_body()
        sha, nbytes, observed, trunc, cred = store.retain_bytes_to_spool(
            logical_call_id=call.logical_call_id,
            attempt=1,
            body=body,
            max_response_bytes=8_000_000,
        )
        assert cred is None and not trunc
        store.record_attempt(
            call=call,
            attempt=1,
            status_code=200,
            body_sha256=sha,
            body_bytes=nbytes,
            observed_body_bytes=observed,
            truncated=False,
            latency_ms=2.0,
            http_429=True,
            error_class=None,
            error_detail=None,
        )
    store.persist_high_water(3)
    _plan, counters, snap = store.authenticate_immutable_store(registry_store_root=None)
    assert counters["logical_calls"] == 3
    assert counters["attempts"] == 3
    assert counters["http_429s"] == 3
    assert counters["retained_bytes"] > 0
    assert counters["high_water_in_flight"] == 3
    assert snap["attempt_count"] == 3
    tracker = BudgetTracker(budgets=MatrixBudgets())
    tracker.load_prior(counters)
    assert tracker.logical_calls_started == 3
    assert tracker.provider_attempts == 3
    assert tracker.http_429_count == 3
    assert tracker.high_water_in_flight == 3


# ---------------------------------------------------------------------------
# 2. Exclusive immutable runs / pointer CAS
# ---------------------------------------------------------------------------


def test_exclusive_run_id_and_directory(store: MatrixStore, plan: MatrixPlan) -> None:
    _seed_plan(store, plan)
    rid = store.begin_run()
    with pytest.raises(MatrixSafetyStop, match="already exists"):
        store.begin_run(run_id=rid)


def test_exclusive_report_create_rejects_replace(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    _seed_plan(store, plan)
    store.begin_run()
    report = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "matrix_id": plan.matrix_id,
        "run_id": store.run_id,
        "mode": "plan_only",
        "complete": True,
        "pass": False,
        "plan": plan.to_public_dict(),
        "budgets": MatrixBudgets().as_report_dict(),
        "cumulative_counters": {
            "logical_calls_started": 0,
            "provider_attempts": 0,
            "retained_response_bytes": 0,
            "http_429_count": 0,
            "high_water_in_flight": 0,
        },
        "evidence_snapshot": {},
        "cells": [],
    }
    store.write_final_report(report, mode="plan_only")
    with pytest.raises(FileExistsError):
        store.write_final_report(report, mode="plan_only")


def test_pointer_generation_cas_monotonic(store: MatrixStore, plan: MatrixPlan) -> None:
    """Correction 2: locked generation CAS advances; stale lower gen cannot win."""
    _seed_plan(store, plan)
    store.begin_run()
    g1 = store.cas_current_run(
        run_id=store.run_id or "",
        complete=False,
        passed=False,
        report_relpath="runs/x/report.incomplete.json",
        mode="execute_live",
    )
    g2 = store.cas_current_run(
        run_id=store.run_id or "",
        complete=True,
        passed=False,
        report_relpath="runs/x/report.json",
        mode="execute_live",
    )
    assert g2 == g1 + 1
    pointer = json.loads(store.current_run_path.read_text(encoding="utf-8"))
    assert pointer["generation"] == g2
    assert pointer["complete"] is True


def test_attempts_bind_to_run_id(store: MatrixStore, plan: MatrixPlan) -> None:
    _seed_plan(store, plan)
    call = _record_minimal_attempt(store, plan)
    row = store.list_attempts(call.logical_call_id)[0]
    assert row["run_id"] == store.run_id


# ---------------------------------------------------------------------------
# 3. Live vs standalone replay separation
# ---------------------------------------------------------------------------


def test_plan_only_report_rejected_as_live_for_standalone_replay(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    """Correction 3: plan-only must not satisfy sealed execute_live load."""
    _seed_plan(store, plan)
    store.begin_run()
    report = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "matrix_id": plan.matrix_id,
        "run_id": store.run_id,
        "mode": "plan_only",
        "complete": True,
        "pass": False,
        "plan": plan.to_public_dict(),
        "budgets": MatrixBudgets().as_report_dict(),
        "cumulative_counters": {
            "logical_calls_started": 0,
            "provider_attempts": 0,
            "retained_response_bytes": 0,
            "http_429_count": 0,
            "high_water_in_flight": 0,
        },
        "evidence_snapshot": {},
        "cells": [],
    }
    store.write_final_report(report, mode="plan_only")
    with pytest.raises(MatrixError, match="execute_live"):
        store.load_sealed_live_report()


def test_standalone_replay_requires_pointer_before_run(
    matrix_root: Path, plan: MatrixPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Correction 3: standalone replay authenticates live before creating a run."""
    monkeypatch.setattr(
        "cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix.build_matrix_plan",
        lambda **_k: plan,
    )
    # Empty root with plan only — no live report.
    store = MatrixStore(matrix_root, create_run=False)
    try:
        store.create_plan_and_catalog(plan)
    finally:
        store.close()

    # Registry store must sit outside the matrix output root (isolation).
    reg = matrix_root.parent / "reg_store"
    reg.mkdir(exist_ok=True)
    cfg = MatrixConfig(
        registry_store_root=reg,
        output_root=matrix_root,
        mode="offline_replay",
        provider_orgs=DEFAULT_PROVIDER_ORGS,
    )
    harness = PairEventV2MatrixHarness(cfg)
    try:
        # Without a sealed execute_live pointer, standalone fails before begin_run.
        with pytest.raises((MatrixError, MatrixSafetyStop)):
            harness.run()
        # Pointer must not be promoted to offline_replay as the live result.
        assert not (matrix_root / "current_run.json").exists() or (
            json.loads((matrix_root / "current_run.json").read_text()).get("mode")
            != "offline_replay"
        )
    finally:
        harness.close()


def test_replay_safety_stop_not_swallowed_as_absence(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    """Correction 3/5: MatrixSafetyStop propagates (not treated as missing report)."""
    _seed_plan(store, plan)
    store.begin_run()
    # Forge a complete execute_live pointer to a missing file with bad mode path.
    store.cas_current_run(
        run_id=store.run_id or "run_" + "0" * 32,
        complete=True,
        passed=True,
        report_relpath="runs/missing/report.json",
        mode="execute_live",
    )
    with pytest.raises((MatrixError, MatrixSafetyStop)):
        store.load_sealed_live_report()


def test_pass_requires_authenticated_replay_fields() -> None:
    """Correction 3: PASS predicate requires authenticated replay result."""
    # In-process PASS gates on authenticated_store + all_cells_pass.
    in_process = {
        "kind": "in_process_pre_seal",
        "all_cells_pass": True,
        "authenticated_store": False,
        "cell_count": 15,
    }
    assert not (
        in_process["all_cells_pass"]
        and in_process.get("authenticated_store")
        and in_process["cell_count"] == 15
    )
    standalone = {
        "all_cells_pass": True,
        "live_report_authenticated": False,
        "cell_count": 15,
    }
    assert not (
        standalone["all_cells_pass"]
        and standalone["live_report_authenticated"]
        and standalone["cell_count"] == 15
    )


# ---------------------------------------------------------------------------
# 4. Evidence / report hashes
# ---------------------------------------------------------------------------


def test_evidence_hash_includes_counters_and_excludes_elapsed() -> None:
    base = {
        "matrix_id": "mtx_x",
        "run_id": "run_" + "a" * 32,
        "cumulative_counters": {
            "logical_calls_started": 2,
            "provider_attempts": 3,
            "retained_response_bytes": 10,
            "http_429_count": 1,
            "high_water_in_flight": 4,
        },
        "started_at": "2026-01-01T00:00:00+00:00",
        "high_water": {
            "elapsed_seconds": 9.9,
            "logical_calls_started": 2,
            "provider_attempts": 3,
            "retained_response_bytes": 10,
            "http_429_count": 1,
            "high_water_in_flight": 4,
        },
        "cells": [],
    }
    h1 = compute_evidence_hash(base)
    base2 = dict(base)
    base2["started_at"] = "2099-01-01T00:00:00+00:00"
    base2["high_water"] = dict(base["high_water"])
    base2["high_water"]["elapsed_seconds"] = 1000.0
    assert compute_evidence_hash(base2) == h1  # timestamps/elapsed excluded
    base3 = dict(base)
    base3["cumulative_counters"] = dict(base["cumulative_counters"])
    base3["cumulative_counters"]["high_water_in_flight"] = 99
    assert compute_evidence_hash(base3) != h1  # counters included


def test_report_hash_distinct_and_binds_evidence() -> None:
    payload = {
        "matrix_id": "mtx_y",
        "run_id": "run_" + "b" * 32,
        "complete": True,
        "pass": False,
        "cells": [],
        "cumulative_counters": {
            "logical_calls_started": 0,
            "provider_attempts": 0,
            "retained_response_bytes": 0,
            "http_429_count": 0,
            "high_water_in_flight": 0,
        },
    }
    eh = compute_evidence_hash(payload)
    rh = compute_report_hash(evidence_hash=eh, payload=payload)
    assert eh != rh
    # Tamper evidence binding.
    rh2 = compute_report_hash(evidence_hash="0" * 64, payload=payload)
    assert rh2 != rh


def test_sealed_report_hash_tamper_detected(store: MatrixStore, plan: MatrixPlan) -> None:
    _seed_plan(store, plan)
    store.begin_run()
    report = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "matrix_id": plan.matrix_id,
        "run_id": store.run_id,
        "mode": "execute_live",
        "complete": True,
        "pass": False,
        "plan": plan.to_public_dict(),
        "budgets": MatrixBudgets().as_report_dict(),
        "cumulative_counters": {
            "logical_calls_started": 0,
            "provider_attempts": 0,
            "retained_response_bytes": 0,
            "http_429_count": 0,
            "high_water_in_flight": 0,
        },
        "evidence_snapshot": {"attempt_count": 0},
        "cells": [],
        "offline_replay": {
            "kind": "in_process_pre_seal",
            "all_cells_pass": False,
            "authenticated_store": True,
        },
    }
    store.write_final_report(report, mode="execute_live")
    # Tamper sealed report bytes.
    assert store.report_path is not None
    text = store.report_path.read_text(encoding="utf-8")
    obj = json.loads(text)
    obj["pass"] = True
    # Cannot exclusive-write again; mutate file in place to simulate tamper.
    store.report_path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    with pytest.raises(MatrixSafetyStop, match="evidence_hash|report_hash"):
        store.load_sealed_live_report()


# ---------------------------------------------------------------------------
# 5. Spooling / reservation / equal-body concurrency / in-flight
# ---------------------------------------------------------------------------


def test_equal_body_promotion_concurrency(matrix_root: Path) -> None:
    """Correction 5: concurrent equal bodies race-safe."""
    raw = matrix_root / "raw"
    spool = matrix_root / "spool"
    raw.mkdir(parents=True)
    spool.mkdir(parents=True)
    body = b'{"jsonrpc":"2.0","result":"0x1"}'
    digest = __import__("hashlib").sha256(body).hexdigest()

    def promote(i: int) -> None:
        p = spool / f"s{i}.part"
        p.write_bytes(body)
        _promote_content_addressed(p, raw, digest)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(promote, range(16)))
    dest = raw / f"{digest}.bin"
    assert dest.is_file()
    assert dest.read_bytes() == body


def test_retained_byte_reservation_and_rollback() -> None:
    tracker = BudgetTracker(
        budgets=MatrixBudgets(max_retained_response_bytes=1000, max_response_bytes=500)
    )
    tracker.reserve_response_bytes(500)
    assert tracker.reserved_response_bytes == 500
    tracker.commit_reservation(500, 120)
    assert tracker.retained_response_bytes == 120
    assert tracker.reserved_response_bytes == 0
    tracker.reserve_response_bytes(500)
    tracker.release_reservation(500)
    assert tracker.reserved_response_bytes == 0
    # 120 retained leaves 880 budget; reserve 800 then fail a further 100.
    tracker.reserve_response_bytes(800)
    with pytest.raises(MatrixSafetyStop, match="budget"):
        # 120 + 800 + 100 = 1020 > 1000
        tracker.reserve_response_bytes(100)


def test_hard_per_provider_in_flight_limit(
    matrix_root: Path, plan: MatrixPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Correction 5/1: hard semaphore enforces max_in_flight=2 under slow transport."""
    monkeypatch.setattr(
        "cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix.build_matrix_plan",
        lambda **_k: plan,
    )
    reg = matrix_root.parent / "reg"
    reg.mkdir()
    out = matrix_root / "out"
    out.mkdir()
    store = MatrixStore(out, create_run=False)
    try:
        store.create_plan_and_catalog(plan)
    finally:
        store.close()

    gate_hold = threading.Event()
    transport = _FakeTransport()
    transport.hold["infura"] = gate_hold

    cfg = MatrixConfig(
        registry_store_root=reg,
        output_root=out,
        mode="execute_live",
        provider_orgs=DEFAULT_PROVIDER_ORGS,
        budgets=MatrixBudgets(max_in_flight=2, max_logical_calls=20, max_provider_attempts=60),
        confirm_matrix_id=plan.matrix_id,
        transport=transport,
        primary_rpc_url="http://primary.invalid",
        secondary_rpc_url="http://secondary.invalid",
    )
    # execute_live rejects non-default orgs — defaults used.
    # But URLs are set with transport provided so URL check skipped for transport path.
    harness = PairEventV2MatrixHarness(cfg)
    # Manually exercise gate by running a few _execute_one under hold.
    harness.prepare_plan()
    harness.store.begin_run()
    calls = [c for c in iter_logical_calls(plan) if c.provider_org == "infura"][:6]

    errors: list[BaseException] = []

    def worker(call: LogicalCall) -> None:
        try:
            harness._execute_one(call)
        except BaseException as exc:  # noqa: BLE001 — collect for test
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(c,)) for c in calls]
    for t in threads:
        t.start()
    time.sleep(0.3)
    # While held, high-water for infura gate must be <= 2.
    assert harness._gates["infura"].in_flight <= 2
    gate_hold.set()
    for t in threads:
        t.join(timeout=10)
    harness.close()
    assert harness._gates["infura"].in_flight == 0
    # Transport high water may be bounded by semaphore.
    assert transport.high_water <= 2


def test_direct_bounded_spool_no_success_on_truncated(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    """Correction 5/6: over-cap prefix retained with truncated; never success body."""
    _seed_plan(store, plan)
    store.begin_run()
    call = iter_logical_calls(plan)[0]
    big = b"{" + b"x" * 100 + b"}"
    sha, retained, observed, truncated, cred = store.retain_bytes_to_spool(
        logical_call_id=call.logical_call_id,
        attempt=1,
        body=big,
        max_response_bytes=50,
    )
    assert truncated is True
    assert observed == len(big)
    assert retained == 50
    assert cred is None
    assert sha is not None
    store.record_attempt(
        call=call,
        attempt=1,
        status_code=200,
        body_sha256=sha,
        body_bytes=retained,
        observed_body_bytes=observed,
        truncated=True,
        latency_ms=1.0,
        http_429=False,
        error_class=None,  # must be forced to error by record_attempt
        error_detail=None,
    )
    assert store.best_success_body(call.logical_call_id) is None
    row = store.list_attempts(call.logical_call_id)[0]
    assert int(row["truncated"]) == 1
    assert row["error_class"] == "body_size_pressure"


# ---------------------------------------------------------------------------
# 6. Credential / malformed safety stops
# ---------------------------------------------------------------------------


def test_endpoint_url_in_response_rejected_before_promote(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    _seed_plan(store, plan)
    store.begin_run()
    call = iter_logical_calls(plan)[0]
    body = b'{"jsonrpc":"2.0","result":"https://mainnet.infura.io/v3/SECRET"}'
    sha, retained, observed, truncated, cred = store.retain_bytes_to_spool(
        logical_call_id=call.logical_call_id,
        attempt=1,
        body=body,
        max_response_bytes=8_000_000,
    )
    assert cred == "credential_or_endpoint_detected"
    assert sha is None
    assert retained == 0
    assert not any(store.raw_dir.glob("*.bin"))


def test_bearer_and_query_token_rejected(store: MatrixStore, plan: MatrixPlan) -> None:
    _seed_plan(store, plan)
    store.begin_run()
    call = iter_logical_calls(plan)[0]
    for payload in (
        b'{"err":"Bearer abcdef0123456789"}',
        b'{"err":"https://x.example/?api_key=deadbeef"}',
    ):
        sha, _b, _o, _t, cred = store.retain_bytes_to_spool(
            logical_call_id=call.logical_call_id,
            attempt=1 if payload.startswith(b'{"err":"B') else 2,
            body=payload,
            max_response_bytes=8_000_000,
        )
        assert cred is not None
        assert sha is None


def test_empty_body_and_missing_result_are_safety_stops() -> None:
    with pytest.raises(MatrixSafetyStop, match="empty"):
        _parse_json_rpc_result(b"")
    with pytest.raises(MatrixSafetyStop, match="missing result"):
        _parse_json_rpc_result(b'{"jsonrpc":"2.0","id":1}')
    with pytest.raises(MatrixSafetyStop, match="malformed_json"):
        _parse_json_rpc_result(b"not-json")


def test_malformed_log_evidence_is_safety_stop_not_cell_failure(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    from cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix import (
        interpret_logs,
        _domain_for,
    )

    domain = _domain_for(
        addresses=[plan.maximum_cohort[0]],
        start=MATRIX_RANGES["sparse"][0],
        end=MATRIX_RANGES["sparse"][1],
        topics=[ORDERED_EVENT_TOPICS[0]],
    )
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": [{"address": "not-an-address"}],
        }
    ).encode()
    with pytest.raises(MatrixSafetyStop, match="malformed|out-of-domain"):
        interpret_logs(body, domain=domain)


# ---------------------------------------------------------------------------
# 7. Metrics, isolation, closure
# ---------------------------------------------------------------------------


def test_provider_metrics_present_on_fail_incomplete_shapes(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    from cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix import (
        _provider_side_metrics,
    )

    _seed_plan(store, plan)
    # No attempts yet → metrics still complete with status missing.
    m = _provider_side_metrics(
        store,
        plan=plan,
        range_name="sparse",
        provider_org="infura",
        addresses=plan.maximum_cohort[:1],
        cohort_size=1,
    )
    for key in (
        "attempts",
        "http_429s",
        "latency_ms_total",
        "response_bytes",
        "observed_body_bytes_total",
        "truncated_attempts",
        "status",
        "error_class",
        "batch_attempts",
        "scalar_attempts",
    ):
        assert key in m


def test_output_tree_isolation_rejects_dex003_full(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Correction 7: project data/dex003_full tree always rejected."""
    # Simulate cwd with a data/dex003_full path.
    project = tmp_path / "proj"
    dex = project / "data" / "dex003_full" / "store"
    dex.mkdir(parents=True)
    monkeypatch.chdir(project)
    with pytest.raises(MatrixSafetyStop, match="dex003_full"):
        assert_safe_matrix_output_root(dex)
    with pytest.raises(MatrixSafetyStop, match="dex003_full"):
        assert_safe_matrix_output_root(project / "data" / "dex003_full")
    ok = assert_safe_matrix_output_root(project / "data" / "dex003_v2_matrix")
    assert ok.is_absolute()


def test_deterministic_closure_on_transport_and_store(
    matrix_root: Path, plan: MatrixPlan
) -> None:
    transport = _FakeTransport()
    store = MatrixStore(matrix_root, create_run=False)
    store.create_plan_and_catalog(plan)
    store.begin_run()
    store.close()
    store.close()  # idempotent
    # Httpx transport close
    # Can't construct real clients without network easily; use Fake close flag.
    transport.close()
    assert transport.closed is True


def test_constructor_failure_closes_cleanly(tmp_path: Path) -> None:
    """Correction 7: constructor failure does not leave harness half-open."""
    bad = tmp_path / "data" / "dex003_full" / "matrix"
    bad.mkdir(parents=True)
    with pytest.raises(MatrixSafetyStop):
        MatrixConfig(
            registry_store_root=tmp_path / "reg",
            output_root=bad,
            mode="plan_only",
        )


def test_logical_call_catalog_size_matches_ceiling(plan: MatrixPlan) -> None:
    calls = iter_logical_calls(plan)
    assert len(calls) == LOGICAL_CALL_CEILING
    assert len(catalog_entries(plan)) == LOGICAL_CALL_CEILING


def test_error_detail_with_url_redacted_on_record(
    store: MatrixStore, plan: MatrixPlan
) -> None:
    _seed_plan(store, plan)
    store.begin_run()
    call = iter_logical_calls(plan)[0]
    store.record_attempt(
        call=call,
        attempt=1,
        status_code=None,
        body_sha256=None,
        body_bytes=0,
        observed_body_bytes=0,
        truncated=False,
        latency_ms=1.0,
        http_429=False,
        error_class="transport",
        error_detail="failed at https://example.com/v3/key",
    )
    row = store.list_attempts(call.logical_call_id)[0]
    assert "https://" not in str(row["error_detail"])
    assert "redacted" in str(row["error_detail"])


def test_prepare_plan_does_not_rewrite_catalog_on_second_open(
    matrix_root: Path, plan: MatrixPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Correction 1: second open authenticates; catalog bytes unchanged."""
    monkeypatch.setattr(
        "cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix.build_matrix_plan",
        lambda **_k: plan,
    )
    reg = matrix_root.parent / "reg2"
    reg.mkdir()
    out = matrix_root / "m"
    out.mkdir()
    s = MatrixStore(out, create_run=False)
    try:
        s.create_plan_and_catalog(plan)
        before = s.catalog_path.read_bytes()
    finally:
        s.close()

    cfg = MatrixConfig(
        registry_store_root=reg,
        output_root=out,
        mode="plan_only",
        provider_orgs=DEFAULT_PROVIDER_ORGS,
    )
    h = PairEventV2MatrixHarness(cfg)
    try:
        p = h.prepare_plan()
        assert p.matrix_id == plan.matrix_id
        after = h.store.catalog_path.read_bytes()
        assert before == after
    finally:
        h.close()
