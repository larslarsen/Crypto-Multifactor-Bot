#!/usr/bin/env python3
"""Publish an immutable ARCH-003 listing-universe snapshot from the reference catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq

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
from cryptofactors.reference.ref_identity import ReferenceIdentityResolver
from cryptofactors.universe.listing_universe import (
    LISTING_UNIVERSE_DATASET_TYPE,
    LISTING_UNIVERSE_SCHEMA,
    build_listing_universe_table,
)


def _parse_time(value: str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(value.strip())
    if parsed.tzinfo is None:
        raise ValueError("--known-at must be timezone-aware")
    return parsed.astimezone(UTC)


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish ARCH-003 listing universe")
    parser.add_argument("--db-path", type=Path, default=Path("exp003.db"))
    parser.add_argument("--store-root", type=Path, default=Path("data/exp003_store"))
    parser.add_argument("--venue", default="BINANCE")
    parser.add_argument("--known-at", default=None)
    args = parser.parse_args()
    known_at = _parse_time(args.known_at)
    resolver = ReferenceIdentityResolver(args.db_path)
    events = resolver.listing_events_known_at(args.venue, known_at)
    table = build_listing_universe_table(events, venue=args.venue)
    relative_path = "universe/reference_listing_universe.parquet"

    with tempfile.TemporaryDirectory(prefix="reference-listing-universe-") as tmp:
        output = Path(tmp) / "reference_listing_universe.parquet"
        pq.write_table(table, output, compression="zstd")
        sha256, byte_size = stream_sha256_and_size(output)
        config_payload = {
            "known_at": known_at.isoformat(),
            "venue": args.venue.upper(),
            "schema": str(LISTING_UNIVERSE_SCHEMA),
        }
        plan = PublishPlan(
            dataset_type=LISTING_UNIVERSE_DATASET_TYPE,
            schema=SchemaIdentity(
                name="reference_listing_universe",
                version="1",
                fingerprint=hashlib.sha256(str(LISTING_UNIVERSE_SCHEMA).encode()).hexdigest(),
            ),
            transform=TransformSpec(name="publish_reference_listing_universe", version="1"),
            code=CodeIdentity(commit="ARCH-003"),
            config=ConfigIdentity(
                config_sha256=hashlib.sha256(
                    json.dumps(config_payload, sort_keys=True).encode()
                ).hexdigest()
            ),
            dependencies=(),
            output_sources={relative_path: output},
            output_specs=[
                OutputFileSpec(
                    relative_path=relative_path,
                    sha256=sha256,
                    rows=table.num_rows,
                    bytes=byte_size,
                    partition={"venue": args.venue.upper(), "known_at": known_at.isoformat()},
                    rows_verified=True,
                )
            ],
            statistics=DatasetStatistics(row_count=table.num_rows, byte_size=byte_size),
            coverage=CoverageWindow(availability_start=known_at, availability_end=known_at),
            quality_status=QualityStatus.PASS,
            quality_summary={
                "knowledge_cutoff": known_at.isoformat(),
                "venue": args.venue.upper(),
                "record_count": table.num_rows,
            },
            created_at=known_at,
            row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
            row_receipts={
                relative_path: RowCountReceipt(
                    relative_path=relative_path,
                    row_count=table.num_rows,
                    verifier_name="reference_listing_universe_row_count",
                )
            },
        )
        catalog = SqliteDatasetCatalog(args.db_path)
        try:
            DatasetPublisher(DatasetStoreConfig(root=args.store_root), catalog).publish(
                plan, register_catalog=True
            )
        finally:
            catalog.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
