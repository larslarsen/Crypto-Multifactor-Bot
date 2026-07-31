#!/usr/bin/env python3
"""DEX-003 — pilot Swap/Sync acquisition for 1 pool x 1 chunk with two providers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from cryptofactors.acquisition.uniswap_v2_pair_event_orchestrator import (
    ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID,
    PINNED_FINALITY_CUTOFF_BLOCK,
    PairEventAcquisitionOrchestrator,
    PairEventOrchestratorConfig,
)
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.writer import RawObjectWriter
from cryptofactors.catalog.runner import apply_migrations

STORE_ROOT = Path("data/dex003_full/store")
RECEIPT_DB = Path("dex003_full.db")
RAW_ROOT = Path("data/dex003_full/raw")

DEFAULT_PRIMARY_URL = os.environ.get(
    "ETHEREUM_RPC_URL",
    "https://cloudflare-eth.com",
)
DEFAULT_SECONDARY_URL = os.environ.get(
    "ETHEREUM_RPC_URL_SECONDARY",
    "https://ethereum.public.blockpi.network/v1/rpc/public",
)


def main() -> int:
    primary_rpc = os.environ.get("ETHEREUM_RPC_URL") or DEFAULT_PRIMARY_URL
    secondary_rpc = os.environ.get("ETHEREUM_RPC_URL_SECONDARY") or DEFAULT_SECONDARY_URL
    primary_provider_id = os.environ.get("ETHEREUM_RPC_PROVIDER_ID")
    secondary_provider_id = os.environ.get("ETHEREUM_RPC_PROVIDER_ID_SECONDARY")

    if not primary_rpc or not secondary_rpc:
        print("ETHEREUM_RPC_URL and ETHEREUM_RPC_URL_SECONDARY must be set", file=sys.stderr)
        return 1
    if not primary_provider_id or not secondary_provider_id:
        print(
            "ETHEREUM_RPC_PROVIDER_ID and ETHEREUM_RPC_PROVIDER_ID_SECONDARY must be set",
            file=sys.stderr,
        )
        return 1
    if primary_rpc.rstrip("/") == secondary_rpc.rstrip("/"):
        print("primary and secondary RPC URLs must be distinct", file=sys.stderr)
        return 1
    if primary_provider_id == secondary_provider_id:
        print("primary and secondary provider IDs must be distinct", file=sys.stderr)
        return 1

    apply_migrations(RECEIPT_DB)

    config = PairEventOrchestratorConfig(
        registry_store_root=STORE_ROOT,
        receipt_db_path=RECEIPT_DB,
        raw_root=RAW_ROOT,
        primary_rpc_url=primary_rpc,
        secondary_rpc_url=secondary_rpc,
        primary_provider_id=primary_provider_id,
        secondary_provider_id=secondary_provider_id,
        registry_dataset_id=ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID,
        require_accepted_registry=True,
        finality_cutoff_block=PINNED_FINALITY_CUTOFF_BLOCK,
        chunk_size=5000,
        event_kinds=("swap", "sync"),
        acquire_token_decimals=True,
        # Pilot: one pool (recent block so public RPCs have state), one chunk
        max_pools=1,
        pool_offset=7000,
        max_chunks_per_pool=1,
        header_batch_size=1,
        header_max_in_flight=1,
        header_requests_per_second=2.0,
        use_header_batches=False,
    )

    raw_store_config = RawObjectStoreConfig(root=RAW_ROOT)
    catalog_sql = SqliteRawObjectCatalog(str(RECEIPT_DB))
    writer = RawObjectWriter(raw_store_config, catalog_sql)

    orchestrator = PairEventAcquisitionOrchestrator(
        config=config,
        raw_writer=writer,
    )

    try:
        # Step 1: offline dry-run
        print("=== DRY RUN (offline) ===")
        dry_result = orchestrator.run(dry_run=True)
        plan = dry_result.plan
        print(f"Registry: {plan.registry_dataset_id}")
        print(f"Pools in plan: {len(plan.pools)}")
        print(f"Event jobs: {len(plan.event_jobs)}")
        print(f"Decimals jobs: {len(plan.decimals_jobs)}")
        print(f"Coverage: {len(dry_result.coverage_before.jobs)} jobs, "
              f"{sum(1 for j in dry_result.coverage_before.jobs if j.is_complete)} complete")
        for job in plan.event_jobs:
            pool = job.pool_address[:10]
            print(f"  event job: pool={pool}... kind={job.kind} "
                  f"blocks=[{job.start_block}, {job.end_block}]")
        for job in plan.decimals_jobs:
            print(f"  decimals job: token={job.token[:10]}... block={job.block_number}")
        print("Dry-run PASS")

        # Step 2: live pilot (one pool, one chunk, both Swap+Sync, with decimals)
        print()
        print("=== LIVE PILOT ===")
        # Endpoint URLs may embed credentials; never write them to logs.
        print(f"Primary provider:   {primary_provider_id}")
        print(f"Secondary provider: {secondary_provider_id}")
        print(f"Pools: {config.max_pools}, Chunks/pool: {config.max_chunks_per_pool}")
        result = orchestrator.run(
            dry_run=False,
            skip_complete_jobs=True,
            stop_on_error=True,
        )

        event_results = result.event_results
        decimals_results = result.decimals_results

        print(f"Event jobs executed: {sum(1 for r in event_results if r.status == 'completed')}")
        print(f"Event jobs skipped:  {sum(1 for r in event_results if r.status == 'skipped_complete')}")
        print(f"Event jobs failed:   {sum(1 for r in event_results if r.status == 'failed')}")
        print(f"Decimals jobs done:  {sum(1 for r in decimals_results if r.status == 'completed')}")
        print(f"Decimals jobs failed:{sum(1 for r in decimals_results if r.status == 'failed')}")

        for r in event_results:
            status = "OK" if r.status == "completed" else r.status
            detail = "" if r.status == "completed" else f" {r.detail[:120]}"
            print(f"  kind={r.job.kind} pool={r.job.pool_address[:10]}... "
                  f"[{r.job.start_block},{r.job.end_block}] -> {status}{detail}")
        for r in decimals_results:
            status = "OK" if r.status == "completed" else r.status
            token_short = (r.job.token[:14] + "...") if r.status == "completed" else r.job.token[:10]
            detail = f" decimals={r.row.decimals}" if r.status == "completed" else f" {r.detail}"
            print(f"  token={token_short} block={r.job.block_number} -> {status}{detail}")

        any_failed = any(
            r.status == "failed"
            for r in list(event_results) + list(decimals_results)
        )
        if any_failed:
            print("PILOT FAILED — disagreements or transport errors", file=sys.stderr)
            return 1

        print("PILOT PASS — no disagreements, no errors")
        print(f"Total receipts: {sum(1 for r in event_results if r.status == 'completed')} "
              f"event + {sum(1 for r in decimals_results if r.status == 'completed')} decimals")

    finally:
        orchestrator.close()
        catalog_sql.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
