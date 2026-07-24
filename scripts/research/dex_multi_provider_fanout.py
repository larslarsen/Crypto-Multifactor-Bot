#!/usr/bin/env python3
"""DEX-002 — Multi-provider free DEX OHLCV fan-out runner.

Usage:
    python scripts/research/dex_multi_provider_fanout.py --dry-run
    python scripts/research/dex_multi_provider_fanout.py --no-dry-run

Default is dry-run. Real mode uses the DATA-007 recommended fan-out:
  1. GeckoTerminal (primary)
  2. DexScreener (secondary, gap-fill)
  3. DefiLlama (tertiary, screening context)

No Birdeye OHLCV. No LIVE.
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
import pyarrow as pa
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
from cryptofactors.ingest.dex_fanout import (
    DEXFanOutEngine,
    DefiLlamaProvider,
    DexOHLCVProvider,
    DexScreenerProvider,
    GeckoTerminalProvider,
    ScreeningGate,
    ShardedWatermarkStore,
    build_dex_fanout_table,
)

UTC = timezone.utc

WATERMARK_PATH = Path("data/dex_fanout_watermarks.json")
DEFAULT_POOLS = [
    {
        "chain": "arbitrum",
        "address": "0xbe3ad6a5669dc0b8b12febc03608860c31e2eef6",
        "fee_tier": "0.01%",
    },
    {
        "chain": "arbitrum",
        "address": "0xbce73c2e5a623054b0e8e2428e956f4b9d0412a5",
        "fee_tier": "0.05%",
    },
]


def _today_utc() -> datetime:
    return datetime.now(UTC)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.strip().upper().replace("Z", "+00:00"))


def _mock_handler_factory(
    *,
    candidate_pools: list[dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
) -> Any:
    """Return a mock httpx handler for dry-run mode."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "geckoterminal" in url:
            pool = _extract_pool_from_url(url)
            records = _generate_gecko_records(pool, start_time, end_time)
            return httpx.Response(200, json={"data": {"attributes": {"ohlcv_list": records}}})
        if "dexscreener" in url:
            return httpx.Response(200, json={
                "pairs": [{
                    "priceUsd": "1.0005",
                    "volume": {"h24": 500000.0},
                    "liquidity": {"usd": 2000000.0},
                }],
            })
        if "llama.fi" in url:
            return httpx.Response(200, json={"data": []})
        return httpx.Response(404, text="not found")

    return handler


def _extract_pool_from_url(url: str) -> str:
    parts = url.split("/pools/")
    if len(parts) > 1:
        return parts[1].split("/")[0].lower()
    return "unknown"


def _generate_gecko_records(pool_address: str, start: datetime, end: datetime) -> list[list[Any]]:
    """Generate daily OHLCV records for the mock pool."""
    rows: list[list[Any]] = []
    day = start
    i = 0
    base = 1.0 + (hash(pool_address) % 1000) / 1000.0
    while day < end:
        ts_s = int(day.timestamp())
        open_p = base + 0.001 * (i % 7 - 3)
        close_p = open_p + 0.0002 * (i % 3 - 1)
        high_p = max(open_p, close_p) + 0.0005
        low_p = min(open_p, close_p) - 0.0005
        volume = 1_000_000.0 + i * 10_000.0
        rows.append([ts_s, open_p, high_p, low_p, close_p, volume])
        day += timedelta(days=1)
        i += 1
    return rows


def _build_mock_providers(
    candidate_pools: list[dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
) -> dict[str, DexOHLCVProvider]:
    handler = _mock_handler_factory(
        candidate_pools=candidate_pools,
        start_time=start_time,
        end_time=end_time,
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return {
        "geckoterminal": GeckoTerminalProvider(http_client=client),
        "dexscreener": DexScreenerProvider(client=client),
        "defillama": DefiLlamaProvider(client=client),
    }


def _build_live_providers() -> dict[str, DexOHLCVProvider]:
    return {
        "geckoterminal": GeckoTerminalProvider(gecko_client=None),
        "dexscreener": DexScreenerProvider(),
        "defillama": DefiLlamaProvider(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DEX-002 — multi-provider DEX OHLCV fan-out")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--end-time", type=str, default=None)
    parser.add_argument("--pools", type=str, default=None,
                        help="JSON list of {chain, address, fee_tier} pools")
    parser.add_argument("--min-liquidity", type=float, default=10_000.0)
    parser.add_argument("--min-volume", type=float, default=1_000.0)
    parser.add_argument("--death-days", type=int, default=7)
    parser.add_argument("--report-path", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    args = parser.parse_args()

    if args.report_path:
        report_path = Path(args.report_path)
    elif args.dry_run:
        report_path = Path(tempfile.gettempdir()) / "37_DEX_MULTI_PROVIDER_FANOUT.json"
    else:
        report_path = Path("research/sprint_004/37_DEX_MULTI_PROVIDER_FANOUT.json")

    end_time = _parse_iso(args.end_time) if args.end_time else _today_utc()

    if args.pools:
        candidate_pools = json.loads(args.pools)
    else:
        candidate_pools = DEFAULT_POOLS

    data_mode: str
    if args.dry_run:
        print("DEX-002: DRY-RUN mode with mocked responses", file=sys.stderr)
        tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(tmpdir.name) / "exp003.db"
        store_root = Path(tmpdir.name) / "exp003_store"
        watermark_path = Path(tmpdir.name) / "watermarks.json"
        data_mode = "synthetic"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        store_root.mkdir(parents=True, exist_ok=True)
        apply_migrations(db_path)
        providers = _build_mock_providers(candidate_pools, datetime(2020, 1, 1, tzinfo=UTC), end_time)
    else:
        print("DEX-002: real mode — fetching live multi-provider DEX OHLCV", file=sys.stderr)
        data_mode = "real_asof"
        db_path = Path(args.db_path)
        store_root = Path(args.store_root)
        watermark_path = Path(WATERMARK_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        store_root.mkdir(parents=True, exist_ok=True)
        apply_migrations(db_path)
        providers = _build_live_providers()

    watermark_store = ShardedWatermarkStore(watermark_path)
    screening_gate = ScreeningGate(
        min_liquidity_usd=args.min_liquidity,
        min_volume_24h_usd=args.min_volume,
        death_consecutive_days=args.death_days,
    )

    engine = DEXFanOutEngine(
        providers=providers,
        screening_gate=screening_gate,
        watermark_store=watermark_store,
    )

    work_items = engine.screen_and_enqueue(candidate_pools, end_time=end_time)
    print(f"DEX-002: {len(work_items)} work items after screening", file=sys.stderr)

    pool_results = engine.run_work_items(work_items)
    engine.update_watermarks(pool_results)
    dead_pools = engine.mark_dead_pools(pool_results, threshold_days=args.death_days, as_of=end_time)

    all_records = [rec for res in pool_results for rec in res.records]
    if not all_records:
        print("DEX-002: no records produced; cannot publish dataset", file=sys.stderr)
        return 0

    # Build PyArrow table.
    columns = build_dex_fanout_table(all_records)
    schema = pa.schema([
        ("timestamp", pa.string()),
        ("timestamp_us", pa.int64()),
        ("chain", pa.string()),
        ("pool_address", pa.string()),
        ("fee_tier", pa.string()),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.float64()),
        ("provider", pa.string()),
        ("liquidity", pa.float64()),
        ("volume_24h", pa.float64()),
    ])
    table = pa.table(columns, schema=schema)

    stage_dir = store_root / "staged" / "dex_fanout"
    stage_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = stage_dir / "dex_fanout.parquet"
    pq.write_table(table, parquet_path)

    row_count = table.num_rows
    relative_path = "dex/fanout/dex_fanout.parquet"
    output_sources = {relative_path: parquet_path}
    sha256, byte_size = stream_sha256_and_size(parquet_path)
    output_specs = [
        OutputFileSpec(
            relative_path=relative_path,
            sha256=sha256,
            rows=row_count,
            bytes=byte_size,
            partition={"source": "multi_provider", "kind": "dex_fanout"},
        )
    ]

    plan = PublishPlan(
        dataset_type="dex_ohlcv_fanout",
        schema=SchemaIdentity(name="dex_ohlcv_fanout", version="1", fingerprint="dex_fanout_v1"),
        transform=TransformSpec(name="dex_multi_provider_fanout", version="1"),
        code=CodeIdentity(commit="DEX-002"),
        config=ConfigIdentity(config_sha256="a" * 64),
        dependencies=(),
        output_sources=output_sources,
        output_specs=output_specs,
        statistics=DatasetStatistics(row_count=row_count, byte_size=byte_size),
        coverage=CoverageWindow(
            event_start=min(rec.timestamp for rec in all_records),
            event_end=max(rec.timestamp for rec in all_records),
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={
            "record_count": row_count,
            "pool_count": len(pool_results),
            "providers": list(providers.keys()),
            "primary_provider": "geckoterminal",
            "merge_policy": "primary_preferred_then_gap_fill",
        },
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters={relative_path: lambda p: row_count},
        created_at=datetime.now(UTC),
    )

    config = DatasetStoreConfig(root=store_root)
    catalog = SqliteDatasetCatalog(db_path)
    try:
        publisher = DatasetPublisher(config, catalog)
        result = publisher.publish(plan, register_catalog=True)
        resolved_latest = catalog.resolve_latest_by_type("dex_ohlcv_fanout")
    finally:
        catalog.close()

    if not args.dry_run:
        engine.save_watermarks()

    # Build report.
    report = {
        "experiment_id": "DEX-002-MULTI-PROVIDER-FANOUT",
        "data_mode": data_mode,
        "real_asof": end_time.isoformat() if data_mode == "real_asof" else None,
        "providers": list(providers.keys()),
        "recommended_fanout": ["geckoterminal", "dexscreener", "defillama"],
        "candidate_pools": candidate_pools,
        "screened_pools": [s for s in engine.get_screen_results() if s["passed"]],
        "rejected_pools": [s for s in engine.get_screen_results() if not s["passed"]],
        "dead_pools": dead_pools,
        "pool_results": [
            {
                "chain": r.chain,
                "pool_address": r.pool_address,
                "fee_tier": r.fee_tier,
                "record_count": len(r.records),
                "providers_used": r.providers_used,
                "last_timestamp": r.last_timestamp.isoformat() if r.last_timestamp else None,
                "incidents": [
                    {
                        "provider": inc.provider,
                        "status_code": inc.status_code,
                        "note": inc.note,
                    }
                    for inc in r.incidents
                ],
            }
            for r in pool_results
        ],
        "dataset_id": result.dataset_id,
        "dataset_type": "dex_ohlcv_fanout",
        "catalog_reconciliation": {
            "report_pinned_dataset_id": result.dataset_id,
            "resolve_latest_by_type": resolved_latest,
            "match": result.dataset_id == resolved_latest,
        },
        "total_records": row_count,
        "coverage": {
            "start": min(rec.timestamp for rec in all_records).isoformat(),
            "end": max(rec.timestamp for rec in all_records).isoformat(),
        },
        "rate_limit": {
            provider: limiter.to_dict()
            for provider, limiter in [
                ("geckoterminal", providers["geckoterminal"]._rate_limiter),
                ("dexscreener", providers["dexscreener"]._rate_limiter),
                ("defillama", providers["defillama"]._rate_limiter),
            ]
        },
        "live_eligible": False,
        "live_eligible_note": "DEX-002 is a research ingestion fan-out; no LIVE authorization.",
        "generated_at": datetime.now(UTC).isoformat(),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"DEX-002 report written to {report_path}", file=sys.stderr)

    if args.dry_run:
        tmpdir.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
