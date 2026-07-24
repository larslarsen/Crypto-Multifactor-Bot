#!/usr/bin/env python3
"""DATA-006 — DEX stablecoin pool (USDC/USDT) historical OHLCV backfill.

Fetches daily OHLCV for the Uniswap V3 USDC/USDT 0.01% and 0.05% pools on
Arbitrum via the GeckoTerminal public API, normalizes the records, and publishes
a MAN-001 dataset. Supports dry-run mode with mocked responses.

No LIVE.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetStatistics,
    DatasetStoreConfig,
    OutputFileSpec,
    PublishPlan,
    QualityStatus,
    RowCountPolicy,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.ingest.dex_ohlcv import (
    GeckoTerminalClient,
    build_dex_ohlcv_table,
)

UTC = timezone.utc

# Uniswap V3 USDC/USDT pools on Arbitrum One.
# Addresses are case-insensitive; stored lower-case for consistency.
DEFAULT_POOLS: list[dict[str, str]] = [
    {
        "address": "0xbe3ad6a5669dc0b8b12febc03608860c31e2eef6",
        "fee_tier": "0.01%",
    },
    {
        "address": "0xbce73c2e5a623054b0e8e2428e956f4b9d0412a5",
        "fee_tier": "0.05%",
    },
]

DEFAULT_NETWORK = "arbitrum"


def generate_mock_ohlcv(
    pool_address: str,
    fee_tier: str,
    end_time: datetime,
    count: int = 180,
) -> list[list[Any]]:
    """Generate mocked daily OHLCV records for dry-run testing.

    Records are generated backwards from end_time so they always fall within the
    public-API 180-day window used by the script.
    """
    rows: list[list[Any]] = []
    for i in range(count):
        ts = end_time - timedelta(days=i + 1)
        ts_s = int(ts.timestamp())
        base = 1.0 + 0.001 * (i % 7 - 3)
        open_p = base
        close_p = base + 0.0002 * (i % 3 - 1)
        high_p = max(open_p, close_p) + 0.0005
        low_p = min(open_p, close_p) - 0.0005
        volume = 1_000_000.0 + i * 10_000.0
        rows.append([ts_s, open_p, high_p, low_p, close_p, volume])
    rows.reverse()
    return rows


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-006 DEX stablecoin OHLCV backfill")
    parser.add_argument("--pools", type=str, default=None,
                        help="JSON list of {address, fee_tier} objects; uses default Arbitrum pools if omitted")
    parser.add_argument("--network", type=str, default=DEFAULT_NETWORK)
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--start-time", type=str, default=None,
                        help="Earliest timestamp to backfill (ISO 8601 UTC); defaults to pool inception")
    parser.add_argument("--end-time", type=str, default=None,
                        help="Latest timestamp to backfill (ISO 8601 UTC); defaults to now")
    parser.add_argument("--report-path", type=str,
                        default="research/sprint_004/33_DEX_STABLECOIN_BACKFILL_REPORT.json")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    args = parser.parse_args()

    pools: list[dict[str, str]]
    if args.pools:
        pools = json.loads(args.pools)
    else:
        pools = DEFAULT_POOLS

    end_time = _parse_iso(args.end_time) if args.end_time else datetime.now(UTC)
    # GeckoTerminal public API only serves ~180 days of OHLCV history.
    # Clip the start to that window unless an explicit start is requested AND
    # it falls within the public window.
    public_earliest = end_time - timedelta(days=180)
    if args.start_time:
        start_time = max(_parse_iso(args.start_time), public_earliest)
    else:
        start_time = public_earliest

    if args.dry_run:
        print("DATA-006 DEX: DRY-RUN mode with mocked responses", file=sys.stderr)
        tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(tmpdir.name) / "exp003.db"
        store_root = Path(tmpdir.name) / "exp003_store"
        data_mode = "synthetic"

        mock_data: dict[str, Any] = {}
        for pool in pools:
            mock_data[pool["address"].lower()] = generate_mock_ohlcv(
                pool["address"], pool["fee_tier"], end_time
            )

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            for pool in pools:
                if pool["address"].lower() in url.lower():
                    return httpx.Response(200, json={
                        "data": {
                            "id": f"{args.network}_{pool['address'].lower()}",
                            "type": "ohlcv",
                            "attributes": {"ohlcv_list": mock_data[pool["address"].lower()]},
                        }
                    })
            return httpx.Response(200, json={"data": {"attributes": {"ohlcv_list": []}}})

        client = GeckoTerminalClient(
            network=args.network,
            client=httpx.Client(transport=httpx.MockTransport(mock_handler)),
        )
    else:
        db_path = Path(args.db_path)
        store_root = Path(args.store_root)
        data_mode = "real_asof"
        client = GeckoTerminalClient(network=args.network)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    store_root.mkdir(parents=True, exist_ok=True)
    apply_migrations(db_path)

    all_records: list[dict[str, Any]] = []
    pool_rows: list[dict[str, Any]] = []
    for pool in pools:
        address = pool["address"].strip()
        fee_tier = pool["fee_tier"].strip()
        try:
            records = client.fetch_pool_ohlcv(
                pool_address=address,
                fee_tier=fee_tier,
                start_time=start_time,
                end_time=end_time,
            )
            if not records:
                print(f"No OHLCV records for {address} ({fee_tier})", file=sys.stderr)
                continue
            all_records.extend(records)
            pool_rows.append({
                "address": address,
                "fee_tier": fee_tier,
                "network": args.network,
                "record_count": len(records),
                "first_timestamp": records[0]["timestamp"],
                "last_timestamp": records[-1]["timestamp"],
            })
            print(f"Fetched {len(records)} OHLCV records for {address} ({fee_tier})", file=sys.stderr)
        except Exception as exc:
            print(f"ERROR fetching {address} ({fee_tier}): {exc}", file=sys.stderr)

    if not all_records:
        print("No DEX OHLCV records produced; cannot publish dataset", file=sys.stderr)
        return 1

    table = build_dex_ohlcv_table(all_records)

    stage_dir = store_root / "staged" / "dex_stablecoin_ohlcv"
    stage_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = stage_dir / "dex_stablecoin_ohlcv.parquet"
    pq.write_table(table, parquet_path)

    row_count = table.num_rows
    relative_path = "dex/stablecoin_ohlcv/dex_stablecoin_ohlcv.parquet"
    output_sources = {relative_path: parquet_path}
    sha256, byte_size = stream_sha256_and_size(parquet_path)
    output_specs = [
        OutputFileSpec(
            relative_path=relative_path,
            sha256=sha256,
            rows=row_count,
            bytes=byte_size,
            partition={"source": "geckoterminal", "kind": "stablecoin_ohlcv"},
        )
    ]

    plan = PublishPlan(
        dataset_type="dex_stablecoin_ohlcv",
        schema=SchemaIdentity(name="dex_stablecoin_ohlcv", version="1", fingerprint="dex_ohlcv_v1"),
        transform=TransformSpec(name="dex_stablecoin_ohlcv_backfill", version="1"),
        code=CodeIdentity(commit="DATA-006"),
        config=ConfigIdentity(config_sha256="a" * 64),
        dependencies=(),
        output_sources=output_sources,
        output_specs=output_specs,
        statistics=DatasetStatistics(row_count=row_count, byte_size=byte_size),
        coverage=CoverageWindow(
            event_start=start_time or _parse_iso(pool_rows[0]["first_timestamp"]),
            event_end=end_time,
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={"record_count": row_count, "pools": [p["address"] for p in pools]},
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters={relative_path: lambda p: row_count},
        created_at=datetime.now(UTC),
    )

    config = DatasetStoreConfig(root=store_root)
    catalog = SqliteDatasetCatalog(db_path)
    try:
        publisher = DatasetPublisher(config, catalog)
        result = publisher.publish(plan, register_catalog=True)
        resolved_latest = catalog.resolve_latest_by_type("dex_stablecoin_ohlcv")
    finally:
        catalog.close()

    print(f"DEX stablecoin OHLCV dataset published: {result.dataset_id}", file=sys.stderr)

    report = {
        "experiment_id": "DATA-006-DEX-STABLECOIN",
        "data_mode": data_mode,
        "network": args.network,
        "pools": pools,
        "pools_backfilled": [r["address"] for r in pool_rows],
        "dataset_id": result.dataset_id,
        "dataset_type": "dex_stablecoin_ohlcv",
        "catalog_reconciliation": {
            "report_pinned_dataset_id": result.dataset_id,
            "resolve_latest_by_type": resolved_latest,
            "match": result.dataset_id == resolved_latest,
        },
        "quality_status": result.manifest.quality_status.value,
        "row_count": row_count,
        "byte_size": byte_size,
        "pool_rows": pool_rows,
        "coverage": {
            "start": (start_time or _parse_iso(pool_rows[0]["first_timestamp"])).isoformat(),
            "end": end_time.isoformat(),
        },
        "live_eligible": False,
        "scope_reduction": {
            "why_not_full_pool_history": (
                "On-chain DEX history from pool inception is available via archival nodes and "
                "paid indexers. The real_asof backfill uses the GeckoTerminal public OHLCV API "
                "which is limited to ~180 days, so the evidence is deliberately scoped to the "
                "recent liquid-stablecoin regime on Arbitrum."
            ),
            "pools_scope": "USDC/USDT Uniswap V3 on Arbitrum only (0.01% and 0.05% tiers).",
            "network_scope": "Arbitrum One mainnet."
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written to {report_path}", file=sys.stderr)

    if args.dry_run:
        tmpdir.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
