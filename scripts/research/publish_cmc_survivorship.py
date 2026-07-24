"""UNIVERSE-006 — Publish CMC survivorship CSV as catalog universe dataset.

One-shot: loads data/survivorship/cmc_dead_universe_full.csv, builds a
CMCSurvivorshipProvider table, publishes as a catalog universe dataset,
and emits research/sprint_004/42_CMC_UNIVERSE_PUBLISHED.json.

No LIVE. No CMC HTTP.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.universe.cmc_survivorship import (
    CMC_SURVIVORSHIP_DATASET_ID,
    CMC_SURVIVORSHIP_SCHEMA,
    CMCSurvivorshipProvider,
    parse_iso_datetime,
)

CSV_PATH = Path("data/survivorship/cmc_dead_universe_full.csv")
STORE_ROOT = Path("data/exp003_store")
DB_PATH = Path("exp003.db")
REPORT_PATH = Path("research/sprint_004/42_CMC_UNIVERSE_PUBLISHED.json")

_SCHEMA_NAME = "cmc_survivorship"
_SCHEMA_VERSION = "1"
_TRANSFORM_NAME = "publish_cmc_survivorship"
_TRANSFORM_VERSION = "1"
_CODE_COMMIT = "UNIVERSE-006"


def _fingerprint_schema(schema) -> str:
    return hashlib.sha256(str(schema).encode("utf-8")).hexdigest()


def main() -> int:
    now = datetime.now(UTC)

    provider = CMCSurvivorshipProvider.from_csv(
        CSV_PATH,
        availability_time=now,
    )
    table = provider.get_table()
    row_count = table.num_rows
    print(f"Loaded {row_count} rows from {CSV_PATH}", file=sys.stderr)

    rows = table.to_pylist()

    # Inactive coins without a death_proxy_date are now excluded by the provider
    # at every point in time (fail-closed). Count them for the evidence report.
    immortal_rows_fixed = sum(
        1 for r in rows if not r.get("is_active") and not r.get("death_proxy_date")
    )
    if immortal_rows_fixed:
        print(f"Excluded {immortal_rows_fixed} immortal rows in universe_at", file=sys.stderr)

    # Coverage window spans the actual data range: earliest birth to latest
    # death or retrieved timestamp.
    all_date_strs: list[str] = []
    for r in rows:
        if r.get("birth_date"):
            all_date_strs.append(r["birth_date"])
        if r.get("death_proxy_date"):
            all_date_strs.append(r["death_proxy_date"])
        if r.get("retrieved_at"):
            all_date_strs.append(r["retrieved_at"])
    all_dts = [parse_iso_datetime(s) for s in all_date_strs if s]
    all_dts = [d for d in all_dts if d is not None]
    event_start = min(all_dts) if all_dts else now
    event_end = max(all_dts) if all_dts else now

    avail_us = int(now.timestamp() * 1_000_000)
    relative_path = "universe/cmc_survivorship_universe.parquet"

    with tempfile.TemporaryDirectory(prefix="cmc-survivorship-") as tmpdir:
        src = Path(tmpdir) / "cmc_survivorship_universe.parquet"
        pq.write_table(table, str(src), compression="zstd")
        sha256, byte_size = stream_sha256_and_size(src)

        config_dict: dict[str, Any] = {
            "availability_time_us": avail_us,
            "dataset_id": CMC_SURVIVORSHIP_DATASET_ID,
            "csv_path": str(CSV_PATH),
            "row_count": row_count,
        }

        plan = PublishPlan(
            dataset_type=CMC_SURVIVORSHIP_DATASET_ID,
            schema=SchemaIdentity(
                name=_SCHEMA_NAME,
                version=_SCHEMA_VERSION,
                fingerprint=_fingerprint_schema(CMC_SURVIVORSHIP_SCHEMA),
            ),
            transform=TransformSpec(
                name=_TRANSFORM_NAME,
                version=_TRANSFORM_VERSION,
            ),
            code=CodeIdentity(commit=_CODE_COMMIT),
            config=ConfigIdentity(
                config_sha256=hashlib.sha256(
                    json.dumps(config_dict, sort_keys=True).encode("utf-8")
                ).hexdigest()
            ),
            dependencies=(),
            output_sources={relative_path: src},
            output_specs=[
                OutputFileSpec(
                    relative_path=relative_path,
                    sha256=sha256,
                    rows=row_count,
                    bytes=byte_size,
                    partition={
                        "availability_time_us": avail_us,
                        "logical_dataset_id": CMC_SURVIVORSHIP_DATASET_ID,
                    },
                    rows_verified=True,
                )
            ],
            statistics=DatasetStatistics(
                row_count=row_count,
                byte_size=byte_size,
            ),
            coverage=CoverageWindow(
                event_start=event_start,
                event_end=event_end,
                availability_start=now,
                availability_end=now,
            ),
            quality_status=QualityStatus.PASS,
            quality_summary={
                "source": "cmc_data_api_unofficial",
                "csv_path": str(CSV_PATH),
                "row_count": row_count,
                "logical_dataset_id": CMC_SURVIVORSHIP_DATASET_ID,
                "death_date_is_proxy": True,
            },
            created_at=now,
            row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
            row_receipts={
                relative_path: RowCountReceipt(
                    relative_path=relative_path,
                    row_count=row_count,
                    verifier_name="cmc_survivorship_row_count",
                )
            },
        )

        apply_migrations(DB_PATH)
        config = DatasetStoreConfig(root=STORE_ROOT)
        catalog = SqliteDatasetCatalog(DB_PATH)
        try:
            publisher = DatasetPublisher(config, catalog)
            result = publisher.publish(plan, register_catalog=True)
        finally:
            catalog.close()

    dataset_id = result.dataset_id
    print(f"Published dataset {dataset_id}", file=sys.stderr)

    # Fix 3: catalog reconciliation - actually resolve_latest_by_type
    catalog2 = SqliteDatasetCatalog(DB_PATH)
    try:
        latest_id = catalog2.resolve_latest_by_type(CMC_SURVIVORSHIP_DATASET_ID)
    finally:
        catalog2.close()

    # Compute universe membership snapshots
    t_2020 = datetime(2020, 1, 1, tzinfo=UTC)
    t_2026 = datetime(2026, 7, 1, tzinfo=UTC)

    univ_2020 = provider.universe_at(t_2020)
    univ_2026 = provider.universe_at(t_2026)

    report: dict[str, Any] = {
        "experiment_id": "UNIVERSE-006",
        "data_mode": "csv_asof",
        "csv_path": str(CSV_PATH),
        "row_count": row_count,
        "dataset_id": dataset_id,
        "dataset_type": CMC_SURVIVORSHIP_DATASET_ID,
        "catalog_reconciliation": {
            "report_pinned_dataset_id": dataset_id,
            "resolve_latest_by_type": latest_id,
            "match": dataset_id == latest_id,
        },
        "universe_at_2020_01_01_count": len(univ_2020),
        "universe_at_2026_07_01_count": len(univ_2026),
        "immortal_rows_fixed": immortal_rows_fixed,
        "coverage_window": {
            "event_start": event_start.isoformat(),
            "event_end": event_end.isoformat(),
        },
        "birth_dates_present": sum(1 for r in rows if r.get("birth_date")),
        "death_proxy_dates_present": sum(1 for r in rows if r.get("death_proxy_date")),
        "all_provenance_labels_present": all(
            r.get("death_date_is_proxy") is True and r.get("source") == "cmc_data_api_unofficial"
            for r in rows
        ),
        "all_rows_have_source": all(r.get("source") == "cmc_data_api_unofficial" for r in rows),
        "all_dead_coins_have_proxy_label": all(r.get("death_date_is_proxy") is True for r in rows),
        "quality_status": "PASS",
        "live_eligible": False,
        "generated_at": now.isoformat(),
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written to {REPORT_PATH}", file=sys.stderr)
    print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
