"""DEX-003 — focused tests for pair-event production orchestration.

Covers deterministic scheduling from the registry, pilot bounds, receipt-store
resume accounting, accepted-registry gating, and run()/dry_run delegation to a
fake ingestor. No network.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.acquisition.uniswap_v2 import (
    ETHEREUM_CHAIN,
    UNISWAP_V2_DEPLOYMENT_BLOCK,
    UniswapV2IngestionError,
)
from cryptofactors.acquisition.uniswap_v2_pair_event_orchestrator import (
    ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID,
    DEFAULT_EVENT_CHUNK_SIZE,
    PINNED_FINALITY_CUTOFF_BLOCK,
    PairEventAcquisitionOrchestrator,
    PairEventOrchestrationError,
    PairEventOrchestratorConfig,
    RegistryPoolRef,
    build_acquisition_plan,
    build_coverage_report,
    build_decimals_jobs,
    build_event_jobs,
    iter_chunk_ranges,
    job_coverage,
    load_plan_from_registry_store,
    load_registry_pool_refs,
    production_aligned_end_block,
    production_chunk_ranges,
    select_pools_for_run,
    verify_registry_manifest,
)
from cryptofactors.acquisition.uniswap_v2_pair_events import (
    RECEIPT_TABLE,
    SWAP_TOPIC,
    TokenDecimalsRow,
)
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetManifest,
    DatasetStatistics,
    OutputFileSpec,
    PublicationMetadata,
    QualityStatus,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir
from cryptofactors.catalog.runner import apply_migrations

USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDT = "0xdac17f958d2ee523a2206206994597c13d831ec7"
WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
WBTC = "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"

POOL_A = "0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc"
POOL_B = "0x0d4a11d5eeaac28ec3f61d100daf4d40471f1852"
POOL_C = "0x3041cbd36888becc7bbcbc0045e3b1f144466f5f"


def _pool(
    address: str,
    *,
    token0: str,
    token1: str,
    base: str,
    quote: str,
    symbol: str,
    creation_block: int,
) -> RegistryPoolRef:
    return RegistryPoolRef(
        pool_address=address,
        token0=token0,
        token1=token1,
        base_token=base,
        quote_token=quote,
        quote_symbol=symbol,
        creation_block=creation_block,
    )


FIXTURE_POOLS = (
    _pool(
        POOL_A,
        token0=USDC,
        token1=WETH,
        base=WETH,
        quote=USDC,
        symbol="USDC",
        creation_block=10_008_355,
    ),
    _pool(
        POOL_B,
        token0=WETH,
        token1=USDT,
        base=WETH,
        quote=USDT,
        symbol="USDT",
        creation_block=10_083_018,
    ),
    _pool(
        POOL_C,
        token0=WBTC,
        token1=USDC,
        base=WBTC,
        quote=USDC,
        symbol="USDC",
        creation_block=10_100_000,
    ),
)


def _config(tmp_path: Path, **overrides: Any) -> PairEventOrchestratorConfig:
    base = dict(
        registry_store_root=tmp_path / "store",
        receipt_db_path=tmp_path / "receipts.db",
        raw_root=tmp_path / "raw",
        primary_rpc_url="https://rpc.primary.example",
        secondary_rpc_url="https://rpc.secondary.example",
        require_accepted_registry=False,
        registry_dataset_id=ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID,
    )
    base.update(overrides)
    return PairEventOrchestratorConfig(**base)


def _write_registry_parquet(path: Path, pools: tuple[RegistryPoolRef, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "pool_address": p.pool_address,
            "token0": p.token0,
            "token1": p.token1,
            "base_token": p.base_token,
            "quote_token": p.quote_token,
            "quote_symbol": p.quote_symbol,
            "creation_block": p.creation_block,
            "chain": "ethereum",
            "protocol": "uniswap_v2",
            "factory": "0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f",
        }
        for p in pools
    ]
    table = pa.Table.from_pylist(records)
    pq.write_table(table, path, compression="zstd")


def _install_registry(
    tmp_path: Path,
    pools: tuple[RegistryPoolRef, ...] = FIXTURE_POOLS,
    *,
    dataset_id: str = ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID,
) -> tuple[Path, DatasetManifest]:
    store = tmp_path / "store"
    dataset_dir = dataset_absolute_dir(store, dataset_id)
    pools_path = dataset_dir / "dex/dex_pool_registry/pools.parquet"
    _write_registry_parquet(pools_path, pools)
    sha, nbytes = stream_sha256_and_size(pools_path)
    manifest = DatasetManifest(
        dataset_id=dataset_id,
        dataset_type="dex_pool_registry",
        schema=SchemaIdentity(name="dex_pool_registry", version="1"),
        transform=TransformSpec(name="dex_pool_registry_from_pair_created", version="1"),
        code=CodeIdentity(commit="a" * 40),
        config=ConfigIdentity(config_sha256="b" * 64),
        dependencies=(),
        files=(
            OutputFileSpec(
                relative_path="dex/dex_pool_registry/pools.parquet",
                sha256=sha,
                rows=len(pools),
                bytes=nbytes,
                rows_verified=True,
            ),
        ),
        statistics=DatasetStatistics(row_count=len(pools), byte_size=nbytes),
        coverage=CoverageWindow(
            event_start=datetime(2020, 5, 5, tzinfo=UTC),
            event_end=datetime(2020, 6, 1, tzinfo=UTC),
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={"selected_pool_count": len(pools)},
        publication=PublicationMetadata(created_at=datetime(2026, 7, 30, tzinfo=UTC)),
        supersedes_dataset_id=None,
        manifest_sha256="c" * 64,
    )
    return pools_path, manifest


def _seed_receipt(
    db_path: Path,
    *,
    pair: str,
    topic: str,
    start_block: int,
    end_block: int,
) -> None:
    apply_migrations(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            f"INSERT INTO {RECEIPT_TABLE} ("
            "chain, chain_id, pair, topic, start_block, end_block, "
            "primary_provider_id, primary_logs_request_json, primary_logs_raw_object_id, "
            "primary_logs_acquisition_id, primary_logs_acquired_at, "
            "secondary_provider_id, secondary_logs_request_json, secondary_logs_raw_object_id, "
            "secondary_logs_acquisition_id, secondary_logs_acquired_at, "
            "log_count, log_identity_sha256, reconciliation_status, "
            "end_block_number, end_block_hash, "
            "primary_end_header_request_json, primary_end_header_raw_object_id, "
            "primary_end_header_acquisition_id, primary_end_header_acquired_at, "
            "secondary_end_block_hash, "
            "secondary_end_header_request_json, secondary_end_header_raw_object_id, "
            "secondary_end_header_acquisition_id, secondary_end_header_acquired_at, "
            "header_dependencies_json, completed_at, "
            "chain_id_request_json, chain_id_raw_object_id, "
            "chain_id_acquisition_id, chain_id_acquired_at, "
            "secondary_header_dependencies_json"
            ") VALUES ("
            "?, '0x1', ?, ?, ?, ?, "
            "'rpc_primary', '{}', 'raw_" + "11" * 32 + "', 'acq_1', '2026-01-01T00:00:00+00:00', "
            "'rpc_secondary', '{}', 'raw_" + "22" * 32 + "', 'acq_2', '2026-01-01T00:00:00+00:00', "
            "0, '" + "ab" * 32 + "', 'AGREED', "
            "?, '" + "cd" * 32 + "', "
            "'{}', 'raw_" + "33" * 32 + "', 'acq_3', '2026-01-01T00:00:00+00:00', "
            "'" + "cd" * 32 + "', "
            "'{}', 'raw_" + "44" * 32 + "', 'acq_4', '2026-01-01T00:00:00+00:00', "
            "'[]', '2026-01-01T00:00:00+00:00', "
            "'{}', 'raw_" + "55" * 32 + "', 'acq_5', '2026-01-01T00:00:00+00:00', "
            "'[]')"
            ,
            (
                ETHEREUM_CHAIN,
                pair,
                topic,
                start_block,
                end_block,
                end_block,
            ),
        )
        conn.commit()
    finally:
        conn.close()


class FakeIngestor:
    """Records fetch/decimals calls; no network."""

    def __init__(self) -> None:
        self.fetch_calls: list[dict[str, Any]] = []
        self.decimals_calls: list[dict[str, Any]] = []
        self.fail_pairs: set[str] = set()
        self.closed = False

    def fetch(self, **kwargs: Any) -> list[Any]:
        self.fetch_calls.append(kwargs)
        if kwargs["pair"] in self.fail_pairs:
            raise UniswapV2IngestionError("injected failure")
        return []

    def fetch_token_decimals(self, **kwargs: Any) -> TokenDecimalsRow:
        self.decimals_calls.append(kwargs)
        return TokenDecimalsRow(
            chain=ETHEREUM_CHAIN,
            token=str(kwargs["token"]).lower(),
            decimals=18,
            block_number=int(kwargs["block_number"]),
            retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            primary_raw_object_id="raw_" + "aa" * 32,
            secondary_raw_object_id="raw_" + "bb" * 32,
            primary_provider_id="rpc_primary",
            secondary_provider_id="rpc_secondary",
        )

    def close(self) -> None:
        self.closed = True


# ---------------------------------------------------------------------------
# Pure scheduling
# ---------------------------------------------------------------------------


def test_iter_chunk_ranges_matches_fetch_tiling() -> None:
    ranges = iter_chunk_ranges(100, 250, 100)
    assert ranges == [(100, 199), (200, 250)]


def test_build_event_jobs_from_birth_to_cutoff() -> None:
    jobs = build_event_jobs(
        FIXTURE_POOLS[:1],
        finality_cutoff_block=PINNED_FINALITY_CUTOFF_BLOCK,
        chunk_size=DEFAULT_EVENT_CHUNK_SIZE,
        event_kinds=("swap", "sync"),
    )
    assert len(jobs) == 2
    assert {j.kind for j in jobs} == {"swap", "sync"}
    for job in jobs:
        assert job.pool_address == POOL_A
        assert job.start_block == 10_008_355
        assert job.end_block == PINNED_FINALITY_CUTOFF_BLOCK
        assert job.chunk_size == DEFAULT_EVENT_CHUNK_SIZE
        assert job.planned_chunk_count == len(
            iter_chunk_ranges(job.start_block, job.end_block, job.chunk_size)
        )


def test_pilot_bounds_use_exact_production_chunk_prefix() -> None:
    creation = 10_008_355
    chunk_size = 1_000
    production = production_chunk_ranges(
        creation_block=creation,
        finality_cutoff_block=PINNED_FINALITY_CUTOFF_BLOCK,
        chunk_size=chunk_size,
    )
    # Mid-chunk bound must drop the incomplete chunk, not shorten it.
    mid_chunk_bound = production[0][0] + 500
    assert production_aligned_end_block(
        creation_block=creation,
        finality_cutoff_block=PINNED_FINALITY_CUTOFF_BLOCK,
        chunk_size=chunk_size,
        max_end_block=mid_chunk_bound,
    ) is None

    # Bound at the end of the second production chunk keeps exactly those two.
    end_two = production[1][1]
    aligned = production_aligned_end_block(
        creation_block=creation,
        finality_cutoff_block=PINNED_FINALITY_CUTOFF_BLOCK,
        chunk_size=chunk_size,
        max_end_block=end_two + 50,  # still before chunk 3 ends
        max_chunks=10,
    )
    assert aligned == end_two
    planned = iter_chunk_ranges(creation, aligned, chunk_size)
    assert planned == production[:2]

    jobs = build_event_jobs(
        FIXTURE_POOLS[:1],
        finality_cutoff_block=PINNED_FINALITY_CUTOFF_BLOCK,
        chunk_size=chunk_size,
        event_kinds=("swap",),
        max_chunks_per_pool=3,
    )
    assert len(jobs) == 1
    assert jobs[0].end_block == production[2][1]
    assert iter_chunk_ranges(
        jobs[0].start_block, jobs[0].end_block, chunk_size
    ) == production[:3]


def test_select_pools_pilot_bounds_are_deterministic() -> None:
    selected = select_pools_for_run(
        FIXTURE_POOLS, pool_offset=1, max_pools=1
    )
    assert len(selected) == 1
    assert selected[0].pool_address == POOL_B

    allow = select_pools_for_run(
        FIXTURE_POOLS, pool_allowlist=frozenset({POOL_C.upper()})
    )
    assert [p.pool_address for p in allow] == [POOL_C]


def test_decimals_jobs_unique_tokens_earliest_birth() -> None:
    jobs = build_decimals_jobs(FIXTURE_POOLS)
    tokens = [j.token for j in jobs]
    assert tokens == sorted(set(tokens))
    by_token = {j.token: j.block_number for j in jobs}
    # USDC appears in pool A (earliest) and pool C.
    assert by_token[USDC] == 10_008_355
    assert by_token[WETH] == 10_008_355
    assert by_token[USDT] == 10_083_018
    assert by_token[WBTC] == 10_100_000


def test_build_acquisition_plan_orders_jobs_by_pool_then_kind(tmp_path: Path) -> None:
    config = _config(tmp_path, event_kinds=("swap", "sync"), max_pools=2)
    plan = build_acquisition_plan(FIXTURE_POOLS, config)
    assert plan.pool_count == 2
    assert [p.pool_address for p in plan.pools] == [POOL_A, POOL_B]
    # Per pool: swap then sync.
    assert [(j.pool_address, j.kind) for j in plan.event_jobs] == [
        (POOL_A, "swap"),
        (POOL_A, "sync"),
        (POOL_B, "swap"),
        (POOL_B, "sync"),
    ]
    assert plan.registry_dataset_id == ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID
    assert plan.finality_cutoff_block == PINNED_FINALITY_CUTOFF_BLOCK


def test_config_rejects_identical_rpc_urls(tmp_path: Path) -> None:
    with pytest.raises(PairEventOrchestrationError, match="distinct"):
        _config(
            tmp_path,
            primary_rpc_url="https://same.example",
            secondary_rpc_url="https://same.example",
        )


def test_config_rejects_bad_pilot_bounds(tmp_path: Path) -> None:
    with pytest.raises(PairEventOrchestrationError, match="max_pools"):
        _config(tmp_path, max_pools=0)
    with pytest.raises(PairEventOrchestrationError, match="pool_offset"):
        _config(tmp_path, pool_offset=-1)


# ---------------------------------------------------------------------------
# Registry load + gating
# ---------------------------------------------------------------------------


def test_load_registry_pool_refs_from_parquet(tmp_path: Path) -> None:
    path = tmp_path / "pools.parquet"
    _write_registry_parquet(path, FIXTURE_POOLS)
    loaded = load_registry_pool_refs(path)
    assert len(loaded) == 3
    assert loaded[0].pool_address == POOL_A
    assert loaded[0].creation_block >= UNISWAP_V2_DEPLOYMENT_BLOCK


def test_load_plan_from_registry_store_with_manifest(tmp_path: Path) -> None:
    _pools_path, manifest = _install_registry(tmp_path)
    config = _config(tmp_path, max_pools=2, acquire_token_decimals=True)
    orch = PairEventAcquisitionOrchestrator(config=config)
    plan = orch.build_plan(manifest=manifest)
    assert plan.pool_count == 2
    assert plan.event_job_count == 4
    assert plan.decimals_jobs  # unique tokens from first two pools


def test_load_plan_requires_manifest_and_pools_hash(tmp_path: Path) -> None:
    pools_path, manifest = _install_registry(tmp_path)
    config = _config(tmp_path, max_pools=1, require_accepted_registry=True)
    # No manifest.json on disk and no in-memory manifest → refuse bare parquet.
    with pytest.raises(PairEventOrchestrationError, match="manifest.json is required"):
        load_plan_from_registry_store(config, manifest=None)

    # Hash mismatch fails closed.
    bad = DatasetManifest(
        dataset_id=manifest.dataset_id,
        dataset_type=manifest.dataset_type,
        schema=manifest.schema,
        transform=manifest.transform,
        code=manifest.code,
        config=manifest.config,
        dependencies=(),
        files=(
            OutputFileSpec(
                relative_path="dex/dex_pool_registry/pools.parquet",
                sha256="0" * 64,
                rows=manifest.statistics.row_count,
                bytes=manifest.statistics.byte_size,
                rows_verified=True,
            ),
        ),
        statistics=manifest.statistics,
        coverage=manifest.coverage,
        quality_status=QualityStatus.PASS,
        quality_summary=manifest.quality_summary,
        publication=manifest.publication,
        supersedes_dataset_id=None,
        manifest_sha256="c" * 64,
    )
    with pytest.raises(PairEventOrchestrationError, match="does not match manifest"):
        load_plan_from_registry_store(config, manifest=bad)

    # Verified path succeeds.
    plan = load_plan_from_registry_store(config, manifest=manifest)
    assert plan.pool_count == 1
    assert pools_path.is_file()


def test_require_accepted_registry_blocks_injected_pools_and_plan(tmp_path: Path) -> None:
    """Production gate: no bypass via build_plan(pools=...) or run(plan=...)."""
    _pools_path, manifest = _install_registry(tmp_path)
    config = _config(tmp_path, max_pools=1, require_accepted_registry=True)
    orch = PairEventAcquisitionOrchestrator(config=config)

    with pytest.raises(PairEventOrchestrationError, match="caller-supplied pools"):
        orch.build_plan(pools=FIXTURE_POOLS)

    injected = build_acquisition_plan(FIXTURE_POOLS, config)
    with pytest.raises(PairEventOrchestrationError, match="caller-supplied prebuilt plan"):
        orch.run(plan=injected, dry_run=True)

    # Verified store path still works.
    plan = orch.build_plan(manifest=manifest)
    assert plan.pool_count == 1
    result = orch.run(manifest=manifest, dry_run=True)
    assert result.dry_run is True
    assert result.plan.pool_count == 1


def test_injected_pools_and_plan_allowed_when_registry_gate_disabled(tmp_path: Path) -> None:
    config = _config(tmp_path, max_pools=1, require_accepted_registry=False)
    orch = PairEventAcquisitionOrchestrator(config=config)
    plan = orch.build_plan(pools=FIXTURE_POOLS)
    assert plan.pool_count == 1
    result = orch.run(plan=plan, dry_run=True)
    assert result.dry_run is True


def test_verify_registry_requires_accepted_id() -> None:
    manifest = DatasetManifest(
        dataset_id="ds_" + "00" * 32,
        dataset_type="dex_pool_registry",
        schema=SchemaIdentity(name="dex_pool_registry", version="1"),
        transform=TransformSpec(name="t", version="1"),
        code=CodeIdentity(commit="a" * 40),
        config=ConfigIdentity(config_sha256="b" * 64),
        dependencies=(),
        files=(
            OutputFileSpec(
                relative_path="dex/dex_pool_registry/pools.parquet",
                sha256="d" * 64,
                rows=1,
                bytes=1,
            ),
        ),
        statistics=DatasetStatistics(row_count=1, byte_size=1),
        coverage=CoverageWindow(),
        quality_status=QualityStatus.PASS,
        quality_summary={},
        publication=PublicationMetadata(created_at=datetime(2026, 1, 1, tzinfo=UTC)),
        supersedes_dataset_id=None,
        manifest_sha256="e" * 64,
    )
    with pytest.raises(PairEventOrchestrationError, match="accepted production registry"):
        verify_registry_manifest(manifest, require_accepted=True)


# ---------------------------------------------------------------------------
# Resume / coverage from receipts
# ---------------------------------------------------------------------------


def test_coverage_marks_completed_and_pending_chunks(tmp_path: Path) -> None:
    config = _config(
        tmp_path,
        chunk_size=1_000,
        max_chunks_per_pool=2,
        event_kinds=("swap",),
        max_pools=1,
    )
    plan = build_acquisition_plan(FIXTURE_POOLS, config)
    assert plan.event_job_count == 1
    job = plan.event_jobs[0]
    planned = iter_chunk_ranges(job.start_block, job.end_block, job.chunk_size)
    assert len(planned) == 2

    # Complete only the first chunk.
    _seed_receipt(
        config.receipt_db_path,
        pair=job.pool_address,
        topic=SWAP_TOPIC,
        start_block=planned[0][0],
        end_block=planned[0][1],
    )
    cov = job_coverage(job, receipt_db_path=config.receipt_db_path)
    assert cov.completed_chunks == (planned[0],)
    assert cov.pending_chunks == (planned[1],)
    assert not cov.is_complete

    report = build_coverage_report(plan, receipt_db_path=config.receipt_db_path)
    assert report.completed_chunk_count == 1
    assert report.pending_chunk_count == 1


def test_coverage_fails_closed_on_chunk_size_mismatch(tmp_path: Path) -> None:
    config = _config(
        tmp_path,
        chunk_size=1_000,
        max_chunks_per_pool=2,
        event_kinds=("swap",),
        max_pools=1,
    )
    plan = build_acquisition_plan(FIXTURE_POOLS, config)
    job = plan.event_jobs[0]
    # Receipt uses a different tiling (500-block chunk).
    _seed_receipt(
        config.receipt_db_path,
        pair=job.pool_address,
        topic=SWAP_TOPIC,
        start_block=job.start_block,
        end_block=job.start_block + 499,
    )
    with pytest.raises(PairEventOrchestrationError, match="planned tiling"):
        job_coverage(job, receipt_db_path=config.receipt_db_path)


# ---------------------------------------------------------------------------
# run() / dry_run with fake ingestor
# ---------------------------------------------------------------------------


def test_dry_run_does_not_call_ingestor(tmp_path: Path) -> None:
    fake = FakeIngestor()
    config = _config(tmp_path, max_pools=1, event_kinds=("swap", "sync"))
    orch = PairEventAcquisitionOrchestrator(config=config, ingestor=fake)
    plan = build_acquisition_plan(FIXTURE_POOLS, config)
    result = orch.run(plan=plan, dry_run=True)
    assert result.dry_run is True
    assert fake.fetch_calls == []
    assert fake.decimals_calls == []
    assert len(result.event_results) == 2


def test_run_skips_complete_jobs_and_fetches_pending(tmp_path: Path) -> None:
    fake = FakeIngestor()
    config = _config(
        tmp_path,
        max_pools=1,
        event_kinds=("swap", "sync"),
        max_chunks_per_pool=1,  # first production 10k chunk only
        chunk_size=10_000,
        acquire_token_decimals=True,
    )
    plan = build_acquisition_plan(FIXTURE_POOLS, config)
    assert plan.event_job_count == 2
    swap_job = plan.event_jobs[0]
    assert swap_job.kind == "swap"
    planned = iter_chunk_ranges(swap_job.start_block, swap_job.end_block, swap_job.chunk_size)
    assert len(planned) == 1
    _seed_receipt(
        config.receipt_db_path,
        pair=swap_job.pool_address,
        topic=SWAP_TOPIC,
        start_block=planned[0][0],
        end_block=planned[0][1],
    )

    orch = PairEventAcquisitionOrchestrator(config=config, ingestor=fake)
    result = orch.run(plan=plan, dry_run=False, skip_complete_jobs=True)
    assert result.failed is False
    # Swap skipped; sync fetched once as full range.
    assert [r.status for r in result.event_results] == ["skipped_complete", "completed"]
    assert len(fake.fetch_calls) == 1
    call = fake.fetch_calls[0]
    assert call["pair"] == POOL_A
    assert call["kind"] == "sync"
    assert call["start_block"] == swap_job.start_block
    assert call["end_block"] == swap_job.end_block
    assert call["emit_rows"] is False
    assert call["chunk_size"] == 10_000
    # Decimals for unique tokens in selected pools (USDC, WETH).
    assert {c["token"] for c in fake.decimals_calls} == {USDC, WETH}


def test_run_stop_on_error(tmp_path: Path) -> None:
    fake = FakeIngestor()
    fake.fail_pairs.add(POOL_A)
    config = _config(
        tmp_path,
        max_pools=2,
        event_kinds=("swap",),
        max_chunks_per_pool=1,
        acquire_token_decimals=False,
    )
    plan = build_acquisition_plan(FIXTURE_POOLS, config)
    orch = PairEventAcquisitionOrchestrator(config=config, ingestor=fake)
    result = orch.run(plan=plan, stop_on_error=True)
    assert result.failed is True
    assert result.event_results[0].status == "failed"
    # Second pool not attempted.
    assert len(fake.fetch_calls) == 1


def test_run_without_skip_still_submits_complete_job(tmp_path: Path) -> None:
    """Ingestor remains authoritative for reorg checks when skip is disabled."""
    fake = FakeIngestor()
    config = _config(
        tmp_path,
        max_pools=1,
        event_kinds=("swap",),
        max_chunks_per_pool=1,
        chunk_size=10_000,
        acquire_token_decimals=False,
    )
    plan = build_acquisition_plan(FIXTURE_POOLS, config)
    job = plan.event_jobs[0]
    planned = iter_chunk_ranges(job.start_block, job.end_block, job.chunk_size)
    _seed_receipt(
        config.receipt_db_path,
        pair=job.pool_address,
        topic=SWAP_TOPIC,
        start_block=planned[0][0],
        end_block=planned[0][1],
    )
    orch = PairEventAcquisitionOrchestrator(config=config, ingestor=fake)
    result = orch.run(plan=plan, skip_complete_jobs=False)
    assert result.event_results[0].status == "completed"
    assert len(fake.fetch_calls) == 1


# ---------------------------------------------------------------------------
# Optional: accepted registry on local disk
# ---------------------------------------------------------------------------


def test_accepted_registry_plan_when_present(tmp_path: Path) -> None:
    root = (
        Path("data/dex003_full/store/datasets/sha256/42/ce")
        / ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID
        / "dex/dex_pool_registry/pools.parquet"
    )
    if not root.is_file():
        pytest.skip("accepted registry parquet not present locally")
    pools = load_registry_pool_refs(root)
    assert len(pools) == 7_659
    config = _config(
        tmp_path,
        max_pools=3,
        event_kinds=("swap", "sync"),
        max_chunks_per_pool=1,
    )
    plan = build_acquisition_plan(pools, config)
    assert plan.pool_count == 3
    assert plan.event_job_count == 6
    # First registry pool is the canonical USDC/WETH pair.
    assert plan.pools[0].pool_address == POOL_A
    assert plan.pools[0].quote_symbol == "USDC"
    # Pilot chunks are the first production chunk for each pool.
    for job in plan.event_jobs:
        production = production_chunk_ranges(
            creation_block=job.creation_block,
            finality_cutoff_block=PINNED_FINALITY_CUTOFF_BLOCK,
            chunk_size=DEFAULT_EVENT_CHUNK_SIZE,
        )
        planned = iter_chunk_ranges(job.start_block, job.end_block, job.chunk_size)
        assert planned == production[:1]
