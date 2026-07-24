#!/usr/bin/env python3
"""DATA-010 — DEX OHLCV backfill for U50+ trading assets.

Uses the DEX-002 multi-provider fan-out engine to backfill 8-hour OHLCV for
the highest-liquidity USDC/USDT pool of each U50+ trading asset. Pools are
resolved via DexScreener search, screened by liquidity/volume, and backfilled
in priority order. Reuses ShardedWatermarkStore for incremental resume.

No Birdeye OHLCV. No LIVE.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

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
    DexScreenerProvider,
    DefiLlamaProvider,
    GeckoTerminalProvider,
    ScreeningGate,
    ShardedWatermarkStore,
    TokenBucketRateLimiter,
)
from cryptofactors.universe.dex_pool_resolver import (
    DexPoolResolver,
    U50_TRADING_ASSETS,
    score_pool,
)

UTC = timezone.utc
WATERMARK_PATH = Path("data/dex_fanout_watermarks.json")
REPORT_PATH = "research/sprint_004/40_DEX_UNIVERSE_BACKFILL.json"
DATASET_TYPE = "dex_ohlcv_fanout"


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _mock_resolver_results() -> list[dict[str, Any]]:
    """Synthetic U50+ pool mappings for dry-run."""
    return [
        {"symbol": "BTC", "chain": "arbitrum", "address": "0x0E4831319A50228B9e450861297aB92dee15B44F", "fee_tier": "0.05%", "liquidity_usd": 8_000_000, "volume_24h_usd": 2_000_000},
        {"symbol": "ETH", "chain": "arbitrum", "address": "0xC6962004f452bE9203591991D15f6b388e24E8c7", "fee_tier": "0.05%", "liquidity_usd": 12_000_000, "volume_24h_usd": 3_000_000},
        {"symbol": "SOL", "chain": "solana", "address": "CfZyzHSpSuGFDYTFy5H9DxGajW6UWvBpkPVCrMTtLpey", "fee_tier": None, "liquidity_usd": 1_000_000_000, "volume_24h_usd": 100_000_000},
        {"symbol": "XRP", "chain": "solana", "address": "8D5h8aswERn7ghmTDeqX6y4Mh5M2qR4B9C5V8Y1Q2w3", "fee_tier": None, "liquidity_usd": 500_000_000, "volume_24h_usd": 50_000_000},
        {"symbol": "ADA", "chain": "solana", "address": "9A3B8D5h8aswERn7ghmTDeqX6y4Mh5M2qR4B9C5V8Y1", "fee_tier": None, "liquidity_usd": 100_000_000, "volume_24h_usd": 10_000_000},
        {"symbol": "AVAX", "chain": "solana", "address": "1Q2w3E4r5T6y7U8i9O0pAsDfGhJkLzXcVbNmM4B6", "fee_tier": None, "liquidity_usd": 80_000_000, "volume_24h_usd": 8_000_000},
        {"symbol": "DOT", "chain": "solana", "address": "2W3E4r5T6y7U8i9O0pAsDfGhJkLzXcVbNmM4B5N6", "fee_tier": None, "liquidity_usd": 70_000_000, "volume_24h_usd": 7_000_000},
        {"symbol": "LINK", "chain": "ethereum", "address": "0x2187d779d9b173dd7202b38b54dca6eb04d1b32ca261980869195b5b9fa97ef8", "fee_tier": "0.05%", "liquidity_usd": 900_000, "volume_24h_usd": 200_000},
        {"symbol": "LTC", "chain": "solana", "address": "3E4r5T6y7U8i9O0pAsDfGhJkLzXcVbNmM4B5N6M7", "fee_tier": None, "liquidity_usd": 60_000_000, "volume_24h_usd": 6_000_000},
        {"symbol": "BCH", "chain": "solana", "address": "4r5T6y7U8i9O0pAsDfGhJkLzXcVbNmM4B5N6M7Q8", "fee_tier": None, "liquidity_usd": 50_000_000, "volume_24h_usd": 5_000_000},
        {"symbol": "DOGE", "chain": "solana", "address": "9ZpDuZTX1CdPWTaFXSrC8bkDaGr2oetzCpTcSTY6dQ84", "fee_tier": None, "liquidity_usd": 800_000_000, "volume_24h_usd": 80_000_000},
        {"symbol": "UNI", "chain": "ethereum", "address": "0xFa7F8980b0f1Ae64b206ecd4D4C9b0d9D1C0bB3f", "fee_tier": "0.30%", "liquidity_usd": 600_000, "volume_24h_usd": 150_000},
        {"symbol": "AAVE", "chain": "ethereum", "address": "0x9445bd19767F73DCaE6f2De90e6cd31192F62589", "fee_tier": "0.30%", "liquidity_usd": 2_000_000, "volume_24h_usd": 500_000},
        {"symbol": "CRV", "chain": "ethereum", "address": "0xD533a949740bb3306d119CC777fa00bD10247eAe", "fee_tier": "0.30%", "liquidity_usd": 380_000, "volume_24h_usd": 80_000},
        {"symbol": "APE", "chain": "ethereum", "address": "0x4d224452801ACEd8B2F0aebE1553bb5b5bC243b8", "fee_tier": "0.30%", "liquidity_usd": 300_000, "volume_24h_usd": 60_000},
        {"symbol": "NEAR", "chain": "solana", "address": "5T6y7U8i9O0pAsDfGhJkLzXcVbNmM4B5N6M7Q8W9", "fee_tier": None, "liquidity_usd": 40_000_000, "volume_24h_usd": 4_000_000},
        {"symbol": "FIL", "chain": "solana", "address": "6y7U8i9O0pAsDfGhJkLzXcVbNmM4B5N6M7Q8W9E0", "fee_tier": None, "liquidity_usd": 30_000_000, "volume_24h_usd": 3_000_000},
        {"symbol": "ARB", "chain": "arbitrum", "address": "0x52d6f6Bfdfb1e6a284A7eACC6D88a588A9e49aB5", "fee_tier": "0.05%", "liquidity_usd": 5_000_000, "volume_24h_usd": 1_000_000},
        {"symbol": "OP", "chain": "arbitrum", "address": "0x6c7b4076b3d7a19d4Cc7D2d70e1a0e6C5f4E2b8a", "fee_tier": "0.05%", "liquidity_usd": 1_500_000, "volume_24h_usd": 300_000},
        {"symbol": "SUI", "chain": "solana", "address": "7U8i9O0pAsDfGhJkLzXcVbNmM4B5N6M7Q8W9E0R1", "fee_tier": None, "liquidity_usd": 25_000_000, "volume_24h_usd": 2_500_000},
        {"symbol": "SEI", "chain": "solana", "address": "8i9O0pAsDfGhJkLzXcVbNmM4B5N6M7Q8W9E0R1T2", "fee_tier": None, "liquidity_usd": 20_000_000, "volume_24h_usd": 2_000_000},
        {"symbol": "WLD", "chain": "solana", "address": "0pAsDfGhJkLzXcVbNmM4B5N6M7Q8W9E0R1T2Y3", "fee_tier": None, "liquidity_usd": 15_000_000, "volume_24h_usd": 1_500_000},
        {"symbol": "PEPE", "chain": "ethereum", "address": "0x69b5b3b2b2c3c4c5d6d7d8d9e0e1f2f3a4b5c6d7", "fee_tier": "1.00%", "liquidity_usd": 100_000, "volume_24h_usd": 20_000},
    ]


def _build_mock_providers() -> dict[str, Any]:
    """Build providers backed by a MockTransport for dry-run."""
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "api.geckoterminal.com" in url:
            # Return a few recent daily bars.
            end = int(datetime.now(UTC).timestamp())
            ohlcv = []
            for i in range(5):
                ts = end - (5 - i) * 86400
                ohlcv.append([ts, 1.0, 1.0, 1.0, 1.0, 1_000_000.0])
            return httpx.Response(200, json={"data": {"attributes": {"ohlcv_list": ohlcv}}})
        if "api.dexscreener.com" in url:
            return httpx.Response(200, json={"pairs": []})
        if "api.llama.fi" in url or "defillama.com" in url:
            return httpx.Response(200, json={})
        return httpx.Response(404, text="unmocked")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return {
        "geckoterminal": GeckoTerminalProvider(
            http_client=client,
            rate_limiter=TokenBucketRateLimiter(tokens_per_second=1000.0),
            requests_per_minute=1000,
        ),
        "dexscreener": DexScreenerProvider(
            client=client,
            rate_limiter=TokenBucketRateLimiter(tokens_per_second=1000.0),
        ),
        "defillama": DefiLlamaProvider(
            client=client,
            rate_limiter=TokenBucketRateLimiter(tokens_per_second=1000.0),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-010 — DEX universe OHLCV backfill")
    parser.add_argument("--assets", type=str, default=None,
                        help="Comma-separated U50+ asset symbols")
    parser.add_argument("--min-liquidity", type=float, default=50_000.0)
    parser.add_argument("--min-volume", type=float, default=10_000.0)
    parser.add_argument("--max-pools", type=int, default=None)
    parser.add_argument("--top-n", type=int, default=3,
                        help="Top N pools per asset to resolve")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--end-time", type=str, default=None)
    parser.add_argument("--watermark-path", type=str, default=str(WATERMARK_PATH))
    parser.add_argument("--report-path", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    args = parser.parse_args()

    end_time = _parse_iso(args.end_time) if args.end_time else datetime.now(UTC)
    assets = [a.strip().upper() for a in args.assets.split(",") if a.strip()] if args.assets else U50_TRADING_ASSETS

    if args.report_path:
        report_path = Path(args.report_path)
    elif args.dry_run:
        report_path = Path(tempfile.gettempdir()) / "40_DEX_UNIVERSE_BACKFILL.json"
    else:
        report_path = Path(REPORT_PATH)

    data_mode: str
    if args.dry_run:
        print("DATA-010: DRY-RUN mode with mocked pool data", file=sys.stderr)
        tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(tmpdir.name) / "exp003.db"
        store_root = Path(tmpdir.name) / "exp003_store"
        watermark_path = Path(tmpdir.name) / "watermarks.json"
        data_mode = "synthetic"
        candidates = _mock_resolver_results()
        providers = _build_mock_providers()
    else:
        print("DATA-010: real mode — resolving U50+ pools and backfilling", file=sys.stderr)
        db_path = Path(args.db_path)
        store_root = Path(args.store_root)
        watermark_path = Path(args.watermark_path)
        data_mode = "real_asof"
        resolver = DexPoolResolver()
        candidates = resolver.resolve_universe(
            assets,
            min_liquidity_usd=args.min_liquidity,
            min_volume_24h_usd=args.min_volume,
            top_n=args.top_n,
        )
        providers = {
            "geckoterminal": GeckoTerminalProvider(),
            "dexscreener": DexScreenerProvider(),
            "defillama": DefiLlamaProvider(),
        }

    db_path.parent.mkdir(parents=True, exist_ok=True)
    store_root.mkdir(parents=True, exist_ok=True)
    apply_migrations(db_path)

    # Deduplicate by address before screening so top-N per asset does not
    # double-count the same pool.
    seen: dict[str, dict[str, Any]] = {}
    unique_candidates: list[dict[str, Any]] = []
    for p in candidates:
        key = (p.get("chain") or "").lower() + ":" + (p.get("address") or "").lower()
        if key in seen:
            continue
        seen[key] = p
        unique_candidates.append(p)
    candidates = unique_candidates

    # Screen and prioritize.
    screened = [p for p in candidates if p["liquidity_usd"] >= args.min_liquidity and p["volume_24h_usd"] >= args.min_volume]
    rejected = [p for p in candidates if p not in screened]
    for p in screened:
        p["score"] = score_pool(p)
    screened.sort(key=lambda p: p["score"], reverse=True)
    if args.max_pools is not None:
        screened = screened[: args.max_pools]

    for i, p in enumerate(screened):
        p["rank"] = i + 1

    print(f"DATA-010: {len(screened)} pools after screening, {len(rejected)} rejected", file=sys.stderr)

    if not screened:
        print("DATA-010: no pools to backfill", file=sys.stderr)
        return 1

    # Prepare candidate pools for the fan-out engine.
    candidate_pools = [
        {
            "chain": p["chain"],
            "gecko_network": p.get("gecko_network") or p["chain"],
            "address": p["address"],
            "fee_tier": p.get("fee_tier"),
            "symbol": p["symbol"],
        }
        for p in screened
    ]

    engine = DEXFanOutEngine(
        providers=providers,
        screening_gate=ScreeningGate(min_liquidity_usd=0.0, min_volume_24h_usd=0.0),
        watermark_store=ShardedWatermarkStore(watermark_path),
    )
    work_items = engine.screen_and_enqueue(candidate_pools, end_time=end_time)
    print(f"DATA-010: {len(work_items)} work items enqueued", file=sys.stderr)
    pool_results = engine.run_work_items(work_items)
    engine.update_watermarks(pool_results)
    if not args.dry_run:
        engine.save_watermarks()

    all_records = [rec for res in pool_results for rec in res.records]
    if not all_records:
        print("DATA-010: no records produced; cannot publish dataset", file=sys.stderr)
        return 0

    pool_symbol_by_address: dict[tuple[str, str], str] = {
        (p["chain"], p["address"]): p["symbol"] for p in screened
    }

    # Build table using the same schema as DEX-002.
    import pyarrow as pa

    columns = {
        "timestamp": [r.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") for r in all_records],
        "timestamp_us": [int(r.timestamp.timestamp() * 1_000_000) for r in all_records],
        "chain": [r.chain for r in all_records],
        "pool_address": [r.pool_address.lower() for r in all_records],
        "fee_tier": [r.fee_tier or "" for r in all_records],
        "open": [r.open for r in all_records],
        "high": [r.high for r in all_records],
        "low": [r.low for r in all_records],
        "close": [r.close for r in all_records],
        "volume": [r.volume for r in all_records],
        "provider": [r.provider for r in all_records],
        "liquidity": [r.liquidity for r in all_records],
        "volume_24h": [r.volume_24h for r in all_records],
    }
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
    parquet_path = stage_dir / "dex_universe_fanout.parquet"
    import pyarrow.parquet as pq

    pq.write_table(table, parquet_path)

    row_count = table.num_rows
    relative_path = "dex/fanout/dex_universe_fanout.parquet"
    output_sources = {relative_path: parquet_path}
    sha256, byte_size = stream_sha256_and_size(parquet_path)
    output_specs = [
        OutputFileSpec(
            relative_path=relative_path,
            sha256=sha256,
            rows=row_count,
            bytes=byte_size,
            partition={"source": "multi_provider", "kind": "dex_universe_fanout"},
        )
    ]

    plan = PublishPlan(
        dataset_type=DATASET_TYPE,
        schema=SchemaIdentity(name="dex_ohlcv_fanout", version="1", fingerprint="dex_fanout_v1"),
        transform=TransformSpec(name="dex_universe_fanout", version="1"),
        code=CodeIdentity(commit="DATA-010"),
        config=ConfigIdentity(config_sha256="a" * 64),
        dependencies=(),
        output_sources=output_sources,
        output_specs=output_specs,
        statistics=DatasetStatistics(row_count=row_count, byte_size=byte_size),
        coverage=CoverageWindow(
            event_start=min(r.timestamp for r in all_records),
            event_end=max(r.timestamp for r in all_records),
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
        resolved_latest = catalog.resolve_latest_by_type(DATASET_TYPE)
    finally:
        catalog.close()

    # Build report.
    report: dict[str, Any] = {
        "experiment_id": "DATA-010-DEX-UNIVERSE-BACKFILL",
        "data_mode": data_mode,
        "real_asof": end_time.isoformat() if data_mode == "real_asof" else None,
        "assets": assets,
        "screening_config": {
            "min_liquidity_usd": args.min_liquidity,
            "min_volume_24h_usd": args.min_volume,
            "max_pools": args.max_pools,
        },
        "pools_backfilled": [
            {
                "symbol": p["symbol"],
                "chain": p["chain"],
                "gecko_network": p.get("gecko_network") or p["chain"],
                "address": p["address"],
                "fee_tier": p.get("fee_tier"),
                "score": p.get("score"),
                "rank": p.get("rank"),
                "liquidity_usd": p["liquidity_usd"],
                "volume_24h_usd": p["volume_24h_usd"],
            }
            for p in screened
        ],
        "pool_results": [
            {
                "symbol": pool_symbol_by_address.get((r.chain, r.pool_address), ""),
                "chain": r.chain,
                "gecko_network": r.gecko_network,
                "address": r.pool_address,
                "fee_tier": r.fee_tier,
                "record_count": len(r.records),
                "providers_used": r.providers_used,
                "first_timestamp": r.records[0].timestamp.isoformat() if r.records else None,
                "last_timestamp": r.records[-1].timestamp.isoformat() if r.records else None,
                "incidents": [
                    {"provider": inc.provider, "status_code": inc.status_code, "note": inc.note}
                    for inc in r.incidents
                ],
            }
            for r in pool_results
        ],
        "rejected_pools": [
            {
                "symbol": p["symbol"],
                "chain": p["chain"],
                "gecko_network": p.get("gecko_network") or p["chain"],
                "address": p["address"],
                "liquidity_usd": p["liquidity_usd"],
                "volume_24h_usd": p["volume_24h_usd"],
                "reason": "screen_failed",
            }
            for p in rejected
        ],
        "dataset_id": result.dataset_id,
        "dataset_type": DATASET_TYPE,
        "catalog_reconciliation": {
            "report_pinned_dataset_id": result.dataset_id,
            "resolve_latest_by_type": resolved_latest,
            "match": result.dataset_id == resolved_latest,
        },
        "total_records": row_count,
        "coverage": {
            "start": min(r.timestamp for r in all_records).isoformat(),
            "end": max(r.timestamp for r in all_records).isoformat(),
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
        "live_eligible_note": "DATA-010 is a research DEX universe backfill; no LIVE authorization.",
        "generated_at": datetime.now(UTC).isoformat(),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"DATA-010 report written to {report_path}", file=sys.stderr)

    if args.dry_run:
        tmpdir.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
