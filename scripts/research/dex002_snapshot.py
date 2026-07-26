#!/usr/bin/env python3
"""DEX-002 screened DEX OHLCV canonical snapshot runner.

Screens a candidate pool set, acquires genuine interval bars for the pools that
passed, merges them with the prior canonical snapshot, and republishes the full
union as the new latest dataset.

Watermarks are written only after publication succeeds. A run that acquires nothing
publishable exits nonzero, publishes no PASS dataset, and leaves both the prior
canonical dataset and the prior watermarks exactly as they were.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetStatistics,
    DatasetStoreConfig,
    DependencyKind,
    DependencyRef,
    OutputFileSpec,
    PublishPlan,
    QualityStatus,
    RowCountPolicy,
    RowCountReceipt,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.ingest.dex_providers import (
    AcquisitionLog,
    DefiLlamaContextProvider,
    DexScreenerScreeningProvider,
    RawHttpAcquirer,
    ScreeningStatus,
    ScreeningThresholds,
)
from cryptofactors.ingest.dex_snapshot import (
    DexSnapshotEngine,
    OhlcvBar,
    PoolAcquisition,
    PoolIdentity,
    WatermarkStore,
    bars_from_records,
    config_fingerprint,
    merge_canonical_bars,
    watermark_key,
)
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.writer import RawObjectWriter

DATASET_TYPE = "dex_pool_ohlcv_daily"
RELATIVE_PATH = "dex/dex_pool_ohlcv_daily/bars.parquet"
REPORT_PATH = Path("research/sprint_004/44_DEX002_REWORK_REPORT.json")

SNAPSHOT_SCHEMA = pa.schema([
    ("chain", pa.string()),
    ("pool_address", pa.string()),
    ("timestamp", pa.string()),
    ("timestamp_us", pa.int64()),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("close", pa.float64()),
    ("volume", pa.float64()),
    ("provider", pa.string()),
    ("raw_object_id", pa.string()),
])


def resolve_code_commit(explicit: str | None) -> str:
    """The real commit; never a placeholder."""
    if explicit:
        return explicit
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("cannot resolve code commit; pass --code-commit") from exc
    commit = result.stdout.strip()
    if len(commit) != 40:
        raise RuntimeError(f"unexpected git commit {commit!r}")
    return commit


def load_candidate_pools(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    pools = document.get("pools") if isinstance(document, dict) else document
    if not isinstance(pools, list) or not pools:
        raise RuntimeError(f"{path} contains no candidate pools")
    return [dict(pool) for pool in pools]


def load_prior_snapshot(
    catalog: SqliteDatasetCatalog, store_root: Path
) -> tuple[str | None, list[OhlcvBar]]:
    """Return the prior canonical dataset id and its rows, if any."""
    dataset_id = catalog.resolve_latest_by_type(DATASET_TYPE)
    if dataset_id is None:
        return None, []
    directory = dataset_absolute_dir(store_root, dataset_id)
    parquet = directory / RELATIVE_PATH
    if not parquet.exists():
        return dataset_id, []
    return dataset_id, bars_from_records(pq.read_table(parquet).to_pylist())


def build_report(
    *,
    end_time: datetime,
    thresholds: ScreeningThresholds,
    config: Mapping[str, Any],
    acquisitions: Sequence[PoolAcquisition],
    log: AcquisitionLog,
    prior_dataset_id: str | None,
    watermarks_before: Mapping[str, str],
    watermarks_after: Mapping[str, str],
    snapshot_rows: int,
    dataset_id: str | None,
) -> dict[str, Any]:
    by_status: dict[str, list[dict[str, Any]]] = {
        "passed": [], "rejected": [], "unavailable": [],
    }
    for acquisition in acquisitions:
        entry = {
            "chain": acquisition.identity.chain,
            "pool_address": acquisition.identity.pool_address,
            "screening": acquisition.decision.as_dict(),
            "row_count": len(acquisition.bars),
            "gaps": [
                {"after": start.isoformat(), "before": end.isoformat()}
                for start, end in acquisition.gaps
            ],
            "error": acquisition.error,
        }
        status = acquisition.decision.status
        if status is ScreeningStatus.PASS:
            by_status["passed"].append(entry)
        elif status is ScreeningStatus.REJECT:
            by_status["rejected"].append(entry)
        else:
            by_status["unavailable"].append(entry)

    return {
        "experiment_id": "DEX-002-SCREENED-DEX-OHLCV-SNAPSHOT",
        "generated_at": datetime.now(UTC).isoformat(),
        "pinned_end_time": end_time.isoformat(),
        "effective_config": dict(config),
        "thresholds": thresholds.as_dict(),
        "thresholds_fingerprint": thresholds.fingerprint(),
        "candidate_pools": [
            {"chain": a.identity.chain, "pool_address": a.identity.pool_address}
            for a in acquisitions
        ],
        "passed_pools": by_status["passed"],
        "rejected_pools": by_status["rejected"],
        "unavailable_pools": by_status["unavailable"],
        "acquisition_attempts": log.as_dicts(),
        "raw_dependency_count": len(log.raw_object_ids),
        "failed_acquisition_count": len(log.failures),
        "prior_dataset_id": prior_dataset_id,
        "watermarks_before": dict(watermarks_before),
        "watermarks_after": dict(watermarks_after),
        "snapshot_row_count": snapshot_rows,
        "published_dataset_id": dataset_id,
        "catalog_reconciled": dataset_id is not None,
        "live_eligible": False,
        "supersedes": {
            "artifact": "research/sprint_004/37_DEX_MULTI_PROVIDER_FANOUT.json",
            "status": "SUPERSEDED_PROTOTYPE",
            "reason": (
                "contains fail-open screening evidence and synthetic DexScreener "
                "candles; no research or canonical-data authority"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DEX-002 screened DEX OHLCV snapshot")
    parser.add_argument("--pools", required=True, type=Path)
    parser.add_argument("--end-time", required=True, help="pinned UTC end time, ISO-8601")
    parser.add_argument("--default-start", required=True, help="first interval, ISO-8601")
    parser.add_argument("--db-path", type=Path, default=Path("exp003.db"))
    parser.add_argument("--raw-root", type=Path, default=Path("data/exp003_store/raw"))
    parser.add_argument("--store-root", type=Path, default=Path("data/exp003_store"))
    parser.add_argument("--watermark-path", type=Path, default=Path("data/dex002_watermarks.json"))
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH)
    parser.add_argument("--min-liquidity-usd", type=float, default=None)
    parser.add_argument("--min-volume-24h-usd", type=float, default=None)
    parser.add_argument("--code-commit", default=None)
    args = parser.parse_args()

    end_time = datetime.fromisoformat(args.end_time)
    default_start = datetime.fromisoformat(args.default_start)
    if end_time.tzinfo is None or default_start.tzinfo is None:
        raise RuntimeError("--end-time and --default-start must be timezone-aware")

    threshold_kwargs: dict[str, float] = {}
    if args.min_liquidity_usd is not None:
        threshold_kwargs["min_liquidity_usd"] = args.min_liquidity_usd
    if args.min_volume_24h_usd is not None:
        threshold_kwargs["min_volume_24h_usd"] = args.min_volume_24h_usd
    thresholds = ScreeningThresholds(**threshold_kwargs)

    code_commit = resolve_code_commit(args.code_commit)
    candidates = load_candidate_pools(args.pools)
    config = {
        "dataset_type": DATASET_TYPE,
        "pinned_end_time": end_time.isoformat(),
        "default_start": default_start.isoformat(),
        "ohlcv_provider": "geckoterminal",
        "screening_provider": "dexscreener",
        "context_providers": ["defillama"],
        "thresholds": thresholds.as_dict(),
        "candidate_pool_count": len(candidates),
    }

    apply_migrations(args.db_path)
    watermark_store = WatermarkStore(args.watermark_path)
    watermarks_before = watermark_store.load()

    import httpx

    raw_catalog = SqliteRawObjectCatalog(args.db_path)
    client = httpx.Client(timeout=30.0)
    acquisitions: list[PoolAcquisition] = []
    try:
        acquirer = RawHttpAcquirer(
            raw_writer=RawObjectWriter(RawObjectStoreConfig(root=args.raw_root), raw_catalog),
            client=client,
        )
        engine = DexSnapshotEngine(
            acquirer=acquirer,
            screening_providers=[DexScreenerScreeningProvider(), DefiLlamaContextProvider()],
            thresholds=thresholds,
        )
        for pool in candidates:
            identity = PoolIdentity.create(str(pool["chain"]), str(pool["pool_address"]))
            acquisitions.append(engine.acquire_pool(
                identity=identity,
                watermarks=watermarks_before,
                default_start=default_start,
                end_time=end_time,
            ))
        log = engine.log
    finally:
        client.close()
        raw_catalog.close()

    acquired = [bar for acquisition in acquisitions for bar in acquisition.bars]
    dataset_catalog = SqliteDatasetCatalog(args.db_path)
    dataset_id: str | None = None
    snapshot: list[OhlcvBar] = []
    watermarks_after = dict(watermarks_before)
    try:
        prior_dataset_id, prior_bars = load_prior_snapshot(dataset_catalog, args.store_root)

        if not acquired:
            # Nothing publishable: the prior canonical dataset and every watermark
            # stay exactly as they were.
            report = build_report(
                end_time=end_time, thresholds=thresholds, config=config,
                acquisitions=acquisitions, log=log, prior_dataset_id=prior_dataset_id,
                watermarks_before=watermarks_before, watermarks_after=watermarks_before,
                snapshot_rows=0, dataset_id=None,
            )
            _write_report(args.report_path, report)
            print("DEX-002: no publishable rows; prior snapshot and watermarks retained")
            return 1

        snapshot = merge_canonical_bars(prior_bars, acquired)
        records = [bar.as_dict() for bar in snapshot]
        table = pa.Table.from_pylist(records, schema=SNAPSHOT_SCHEMA)

        with tempfile.TemporaryDirectory(prefix="dex002-") as tmp:
            output = Path(tmp) / "bars.parquet"
            pq.write_table(table, output, compression="zstd")
            sha256, byte_size = stream_sha256_and_size(output)

            dependencies = [
                DependencyRef(id=raw_id, kind=DependencyKind.RAW_OBJECT, role="controlling_response")
                for raw_id in sorted(log.raw_object_ids)
            ]
            if prior_dataset_id is not None and prior_bars:
                dependencies.append(DependencyRef(
                    id=prior_dataset_id, kind=DependencyKind.DATASET, role="prior_canonical_snapshot"
                ))

            timestamps = [bar.timestamp for bar in snapshot]
            acquired_times = [
                outcome.acquired_at for outcome in log.outcomes if outcome.raw_object_id
            ] or [datetime.now(UTC)]
            plan = PublishPlan(
                dataset_type=DATASET_TYPE,
                schema=SchemaIdentity(name=DATASET_TYPE, version="1"),
                transform=TransformSpec(name="dex002_screened_snapshot", version="1"),
                code=CodeIdentity(commit=code_commit),
                config=ConfigIdentity(config_sha256=config_fingerprint(config)),
                dependencies=dependencies,
                output_sources={RELATIVE_PATH: output},
                output_specs=[OutputFileSpec(
                    relative_path=RELATIVE_PATH, sha256=sha256, rows=table.num_rows,
                    bytes=byte_size, rows_verified=True,
                )],
                statistics=DatasetStatistics(row_count=table.num_rows, byte_size=byte_size),
                coverage=CoverageWindow(
                    event_start=min(timestamps), event_end=max(timestamps),
                    availability_start=min(acquired_times), availability_end=max(acquired_times),
                ),
                quality_status=QualityStatus.PASS,
                quality_summary={
                    "passed_pools": sum(1 for a in acquisitions if a.decision.passed),
                    "row_count": table.num_rows,
                    "unresolved_gaps": sum(len(a.gaps) for a in acquisitions),
                },
                created_at=datetime.now(UTC),
                row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
                row_receipts={RELATIVE_PATH: RowCountReceipt(
                    relative_path=RELATIVE_PATH, row_count=table.num_rows,
                    verifier_name="dex002_snapshot_row_count",
                )},
            )
            DatasetPublisher(
                DatasetStoreConfig(root=args.store_root), dataset_catalog
            ).publish(plan, register_catalog=True)

        dataset_id = dataset_catalog.resolve_latest_by_type(DATASET_TYPE)
        if dataset_id is None:
            raise RuntimeError("publication did not register a resolvable dataset")

        # Publication succeeded: only now may watermarks advance, and only to the
        # last contiguous validated row.
        for acquisition in acquisitions:
            if acquisition.watermark_candidate is None:
                continue
            key = watermark_key(provider="geckoterminal", identity=acquisition.identity)
            watermarks_after[key] = acquisition.watermark_candidate.isoformat()
        watermark_store.save(watermarks_after)
    finally:
        dataset_catalog.close()

    report = build_report(
        end_time=end_time, thresholds=thresholds, config=config, acquisitions=acquisitions,
        log=log, prior_dataset_id=prior_dataset_id, watermarks_before=watermarks_before,
        watermarks_after=watermarks_after, snapshot_rows=len(snapshot), dataset_id=dataset_id,
    )
    _write_report(args.report_path, report)
    print(f"DEX-002: published {len(snapshot)} rows as {dataset_id}")
    return 0


def _write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
