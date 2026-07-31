#!/usr/bin/env python3
"""DEX-003 — publish dex_pool_registry from the pinned PairCreated census."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path

from cryptofactors.catalog.dataset.parse import load_manifest_file
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import DatasetStoreConfig
from cryptofactors.market.dex_pool_registry import (
    PINNED_PAIR_CREATED_DATASET_ID,
    build_dex_pool_registry,
)

STORE_ROOT = Path("data/dex003_full/store")
CATALOG_DB = Path("dex003_full.db")
DATASET_DIR = STORE_ROOT / "datasets/sha256/0e/ab" / PINNED_PAIR_CREATED_DATASET_ID
MANIFEST_PATH = DATASET_DIR / "manifest.json"
EVENTS_PATH = DATASET_DIR / "dex/uniswap_v2_pair_created/events.parquet"
OUTPUT_DIR = STORE_ROOT / "staged"
CODE_COMMIT = "a1aba05a7e8c6d6fcdd67bda8bc2aa0a8d747cde"
SUPERSEDES_DS_ID = "ds_1db3071508f50557a0f2bf57190ce43141a4c273ce8068bdb320e6cebbf8da6c"


def main() -> int:
    if not MANIFEST_PATH.exists():
        raise RuntimeError(f"manifest not found: {MANIFEST_PATH}")
    if not EVENTS_PATH.exists():
        raise RuntimeError(f"events not found: {EVENTS_PATH}")

    manifest = load_manifest_file(MANIFEST_PATH)

    result = build_dex_pool_registry(
        source_manifest=manifest,
        source_events_path=EVENTS_PATH,
        output_dir=OUTPUT_DIR,
        code_commit=CODE_COMMIT,
        require_pinned_source=True,
        created_at=datetime.now(UTC),
    )

    print(f"Source rows: {result.source_row_count}")
    print(f"Selected pools: {result.selected_count}")
    print(f"  USDC: {result.usdc_count}")
    print(f"  USDT: {result.usdt_count}")
    print(f"Output: {result.output_path}")
    print(f"Plan dataset_type: {result.publish_plan.dataset_type}")

    # Supersede the provenance-bad first publication
    result = dataclasses.replace(
        result,
        publish_plan=dataclasses.replace(
            result.publish_plan,
            supersedes_dataset_id=SUPERSEDES_DS_ID,
        ),
    )

    catalog = SqliteDatasetCatalog(CATALOG_DB)
    try:
        publisher = DatasetPublisher(
            DatasetStoreConfig(root=STORE_ROOT),
            catalog,
        )
        published_id = publisher.publish(
            result.publish_plan,
            register_catalog=True,
        )
        print(f"Published dataset_id: {published_id}")
    finally:
        catalog.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
