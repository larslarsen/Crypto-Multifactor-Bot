#!/usr/bin/env python3
"""DATA-012 Ethereum Uniswap V2 PairCreated raw-event ingestion runner."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cryptofactors.acquisition.uniswap_v2 import UniswapV2PairCreatedIngestor
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
    parser.add_argument("--output", type=Path, required=True)
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
        rows = ingestor.fetch(
            start_block=args.start_block,
            end_block=args.end_block,
            chunk_size=args.chunk_size,
        )
    finally:
        catalog.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row.as_dict(), sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
