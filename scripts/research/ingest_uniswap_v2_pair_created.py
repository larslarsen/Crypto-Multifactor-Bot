#!/usr/bin/env python3
"""DATA-012 Ethereum Uniswap V2 PairCreated raw-event ingestion runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.acquisition.uniswap_v2 import UniswapV2PairCreatedIngestor
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetStatistics,
    DatasetStoreConfig,
    OutputFileSpec,
    PublishPlan,
    QualityStatus,
    RowCountPolicy,
    RowCountReceipt,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.writer import RawObjectWriter


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Uniswap V2 PairCreated events")
    parser.add_argument("--start-block", required=True, type=int)
    parser.add_argument("--end-block", required=True, type=int)
    parser.add_argument("--chunk-size", type=int, default=10_000)
    parser.add_argument("--db-path", type=Path, default=Path("exp003.db"))
    parser.add_argument("--raw-root", type=Path, default=Path("data/exp003_store/raw"))
    parser.add_argument("--store-root", type=Path, default=Path("data/exp003_store"))
    parser.add_argument("--code-commit", required=True)
    args = parser.parse_args()
    rpc_url = os.environ.get("ETHEREUM_RPC_URL")
    if not rpc_url:
        raise RuntimeError("ETHEREUM_RPC_URL must be set")
    apply_migrations(args.db_path)
    catalog = SqliteRawObjectCatalog(args.db_path)
    try:
        ingestor = UniswapV2PairCreatedIngestor(
            rpc_url=rpc_url,
            raw_writer=RawObjectWriter(RawObjectStoreConfig(root=args.raw_root), catalog),
        )
        try:
            rows = ingestor.fetch(
                start_block=args.start_block,
                end_block=args.end_block,
                chunk_size=args.chunk_size,
                receipt_db_path=str(args.db_path),
            )
        finally:
            ingestor.close()
    finally:
        catalog.close()
    records = [row.as_dict() for row in rows]
    table = pa.Table.from_pylist(records) if records else pa.table({
        "chain": pa.array([], type=pa.string()),
        "factory": pa.array([], type=pa.string()),
        "pair": pa.array([], type=pa.string()),
        "token0": pa.array([], type=pa.string()),
        "token1": pa.array([], type=pa.string()),
        "block_number": pa.array([], type=pa.int64()),
        "block_hash": pa.array([], type=pa.string()),
        "block_timestamp": pa.array([], type=pa.int64()),
        "tx_hash": pa.array([], type=pa.string()),
        "tx_index": pa.array([], type=pa.int64()),
        "log_index": pa.array([], type=pa.int64()),
        "event_time": pa.array([], type=pa.string()),
        "availability_time": pa.array([], type=pa.string()),
        "raw_object_id": pa.array([], type=pa.string()),
        "block_raw_object_id": pa.array([], type=pa.string()),
    })
    relative_path = "dex/uniswap_v2_pair_created/events.parquet"
    now = datetime.now(UTC)
    with tempfile.TemporaryDirectory(prefix="uniswap-v2-pair-created-") as tmp:
        output = Path(tmp) / "events.parquet"
        pq.write_table(table, output, compression="zstd")
        sha256, byte_size = stream_sha256_and_size(output)
        config = {
            "factory": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
            "start_block": args.start_block,
            "end_block": args.end_block,
            "chunk_size": args.chunk_size,
        }
        plan = PublishPlan(
            dataset_type="uniswap_v2_pair_created",
            schema=SchemaIdentity(name="uniswap_v2_pair_created", version="1"),
            transform=TransformSpec(name="uniswap_v2_pair_created_ingest", version="1"),
            code=CodeIdentity(commit=args.code_commit),
            config=ConfigIdentity(config_sha256=hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()),
            dependencies=(),
            output_sources={relative_path: output},
            output_specs=[OutputFileSpec(relative_path=relative_path, sha256=sha256, rows=table.num_rows, bytes=byte_size, rows_verified=True)],
            statistics=DatasetStatistics(row_count=table.num_rows, byte_size=byte_size),
            coverage=CoverageWindow(availability_start=now, availability_end=now),
            quality_status=QualityStatus.PASS,
            quality_summary={"chain": "ethereum", "event": "PairCreated", "row_count": table.num_rows},
            created_at=now,
            row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
            row_receipts={relative_path: RowCountReceipt(relative_path=relative_path, row_count=table.num_rows, verifier_name="uniswap_v2_pair_created_row_count")},
        )
        dataset_catalog = SqliteDatasetCatalog(args.db_path)
        try:
            DatasetPublisher(DatasetStoreConfig(root=args.store_root), dataset_catalog).publish(plan, register_catalog=True)
        finally:
            dataset_catalog.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
