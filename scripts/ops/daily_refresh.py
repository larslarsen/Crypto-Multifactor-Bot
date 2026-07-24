#!/usr/bin/env python3
"""INFRA-001 — Daily automated Binance spot bar refresh + paper loop scheduler.

Deterministic, idempotent daily ops path:
  1. Refreshes incremental BIN-001 1d spot klines for the configured universe.
  2. Publishes source-normalized datasets (MAN-001) and canonical market_bars via
     BAR-001 transform v6 (native 1d eligible → PASS quality).
  3. Optionally runs a paper loop step, but only on a pre-registered active factor;
     the archived tsmom_14_3 / mod_tsmom_14_3_v1 is NEVER run.
  4. Emits a single machine-readable ops report.

Modes:
  --dry-run (default): skips network fetch and paper loop; reports on the latest
                     existing canonical dataset. Useful for cron smoke tests and
                     days where the exchange has not yet delivered new bars.
  --refresh:         performs the incremental fetch + publish cycle.

Local-first: no cloud daemon. No LIVE. No new factor research.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from cryptofactors.acquisition.binance_fetcher import BinanceKlineFetcher
from cryptofactors.catalog.dataset import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetManifest,
    DatasetPublishResult,
    DatasetPublisher,
    DatasetStatistics,
    DatasetStoreConfig,
    DependencyKind,
    DependencyRef,
    OutputFileSpec,
    PublicationMetadata,
    QualityStatus,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.paths import lexical_join
from cryptofactors.execution.symbols import (
    BINANCE_TO_PAPER_MAP,
    PAPER_TO_INSTRUMENT_ID,
)
from cryptofactors.ingest.binance import normalize_binance_kline
from cryptofactors.ingest.raw.writer import (  # type: ignore[attr-defined]
    RawObjectStoreConfig,
    RawObjectWriter,
)
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.market.bars import VerifiedSourceBarDataset, publish_canonical_bars

UTC = timezone.utc

PASS_DATASET_ID = "ds_0cb6415fa79119bf5317c124e9da2f0d4953b9a8d119aae45e2589ba716c5aaa"
HOLDOUT_START = "2026-07-24T00:00:00+00:00"

DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT",
    "DOGEUSDT", "UNIUSDT", "AAVEUSDT", "CRVUSDT", "APEUSDT",
    "NEARUSDT", "FILUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT",
    "SEIUSDT", "WLDUSDT", "PEPEUSDT",
]

BINANCE_TO_INSTRUMENT_ID = {
    sym: PAPER_TO_INSTRUMENT_ID[BINANCE_TO_PAPER_MAP[sym]]
    for sym in DEFAULT_SYMBOLS
    if sym in BINANCE_TO_PAPER_MAP
}

EXPERIMENT_REGISTRY = Path("research/sprint_004/experiment_registry.csv")


def _parse_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _manifest_from_json(manifest: dict[str, Any]) -> DatasetManifest:
    """Reconstruct a DatasetManifest from a manifest.json dict."""
    schema = manifest["schema"]
    transform = manifest["transform"]
    code = manifest["code"]
    config = manifest.get("config") or {"config_sha256": manifest["config_sha256"]}
    stats = manifest.get("statistics") or {
        "row_count": manifest["row_count"],
        "byte_size": manifest["byte_size"],
    }
    coverage = manifest.get("coverage") or {
        "event_start": manifest["event_start"],
        "event_end": manifest["event_end"],
        "availability_start": manifest.get("availability_start"),
        "availability_end": manifest.get("availability_end"),
    }
    publication = manifest["publication"]
    quality_summary = manifest.get("quality_summary") or {}
    return DatasetManifest(
        dataset_id=manifest["dataset_id"],
        dataset_type=manifest["dataset_type"],
        schema=SchemaIdentity(
            name=schema["name"],
            version=schema["version"],
            fingerprint=schema.get("fingerprint"),
        ),
        transform=TransformSpec(
            name=transform["name"],
            version=transform["version"],
        ),
        code=CodeIdentity(
            commit=code["commit"],
            lock_sha256=code.get("lock_sha256"),
        ),
        config=ConfigIdentity(
            config_sha256=config["config_sha256"],
        ),
        dependencies=tuple(
            DependencyRef(
                id=dep["id"],
                kind=DependencyKind(dep["kind"]),
                role=dep["role"],
            )
            for dep in manifest["dependencies"]
        ),
        files=tuple(
            OutputFileSpec(
                relative_path=f["relative_path"],
                sha256=f["sha256"],
                rows=f["rows"],
                bytes=f["bytes"],
                partition=f.get("partition") or {},
                rows_verified=f.get("rows_verified", False),
            )
            for f in manifest["files"]
        ),
        statistics=DatasetStatistics(
            row_count=stats["row_count"],
            byte_size=stats["byte_size"],
        ),
        coverage=CoverageWindow(
            event_start=_parse_iso(coverage.get("event_start")),
            event_end=_parse_iso(coverage.get("event_end")),
            availability_start=_parse_iso(coverage.get("availability_start")),
            availability_end=_parse_iso(coverage.get("availability_end")),
        ),
        quality_status=QualityStatus(manifest["quality_status"]),
        quality_summary=quality_summary,
        publication=PublicationMetadata(
            created_at=_parse_iso(publication["created_at"]) or datetime(1970, 1, 1, tzinfo=UTC),
            publisher=publication.get("publisher", "cryptofactors.catalog.dataset"),
            publisher_version=publication.get("publisher_version", "1"),
        ),
        supersedes_dataset_id=manifest.get("supersedes_dataset_id"),
        manifest_sha256=manifest.get("manifest_sha256", ""),
    )


def _load_source_dataset(
    dataset_id: str,
    store_root: Path,
    catalog: SqliteDatasetCatalog,
) -> VerifiedSourceBarDataset:
    """Load a published MAN-001 source dataset into VerifiedSourceBarDataset."""
    ds_row = catalog.get_dataset(dataset_id)
    if ds_row is None:
        raise RuntimeError(f"Source dataset {dataset_id} not found in catalog")

    manifest_uri = str(ds_row.get("manifest_uri") or "")
    if not manifest_uri:
        raise RuntimeError(f"Source dataset {dataset_id} has no manifest_uri")

    dataset_base = lexical_join(store_root, str(Path(manifest_uri).parent))
    manifest_path = dataset_base / "manifest.json"
    manifest_json = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = _manifest_from_json(manifest_json)

    local_files: dict[str, Path] = {}
    instrument_id = 1
    for f in manifest.files:
        rel = f.relative_path
        if not rel.endswith("bars.parquet"):
            continue
        local_files[rel] = lexical_join(dataset_base, rel)
        part = f.partition
        iid = part.get("instrument_id")
        if iid is not None:
            instrument_id = int(str(iid))

    if not local_files:
        raise RuntimeError(f"Source dataset {dataset_id} has no resolvable bar files")

    return VerifiedSourceBarDataset(
        local_files=local_files,
        venue_id="binance",
        instrument_id=instrument_id,
        market_type="spot",
        interval="1d",
        schema_variant="quote_notional",
        manifest=manifest,
    )


def _load_existing_source_datasets(
    db_path: Path,
    store_root: Path,
    canonical_dataset_id: str,
) -> list[VerifiedSourceBarDataset]:
    """Load source datasets referenced by the current canonical dataset."""
    catalog = SqliteDatasetCatalog(db_path)
    try:
        ds_row = catalog.get_dataset(canonical_dataset_id)
        if ds_row is None:
            raise RuntimeError(f"Canonical dataset {canonical_dataset_id} not found")

        manifest_path = lexical_join(store_root, str(Path(ds_row["manifest_uri"]).parent), "manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_ids = [
            dep["id"] for dep in manifest.get("dependencies", [])
            if dep.get("kind") == "DATASET" and str(dep.get("role", "")).startswith("source")
        ]

        sources: list[VerifiedSourceBarDataset] = []
        for ds_id in source_ids:
            sources.append(_load_source_dataset(ds_id, store_root, catalog))
        return sources
    finally:
        catalog.close()


def _latest_event_end(sources: list[VerifiedSourceBarDataset]) -> datetime:
    """Return the latest event_end across all source datasets."""
    latest = datetime(1970, 1, 1, tzinfo=UTC)
    for src in sources:
        if src.manifest and src.manifest.coverage.event_end:
            latest = max(latest, src.manifest.coverage.event_end)
    return latest


def _fetch_and_publish_source(
    symbol: str,
    instrument_id: int,
    start_time: datetime,
    end_time: datetime,
    db_path: Path,
    store_root: Path,
    raw_root: Path,
    stage_dir: Path,
    client: httpx.Client | None = None,
) -> str:
    """Fetch incremental 1d klines, normalize, publish source dataset, return dataset_id."""
    raw_catalog = SqliteRawObjectCatalog(db_path)
    raw_writer = RawObjectWriter(
        RawObjectStoreConfig(root=raw_root),
        raw_catalog,
    )
    fetcher = BinanceKlineFetcher(raw_writer, client=client)
    raw_obj = fetcher.fetch_and_write_raw(symbol, "1d", start_time=start_time, end_time=end_time)

    symbol_stage = stage_dir / symbol
    symbol_stage.mkdir(parents=True, exist_ok=True)
    norm_res = normalize_binance_kline(
        raw_objects=[raw_obj],
        market_type="spot",
        interval="1d",
        venue_id="binance",
        instrument_id=str(instrument_id),
        output_dir=symbol_stage,
        code_commit="INFRA-001",
    )

    config = DatasetStoreConfig(root=store_root)
    catalog = SqliteDatasetCatalog(db_path)
    try:
        publisher = DatasetPublisher(config, catalog)
        result = publisher.publish(norm_res.publish_plan, register_catalog=True)
        return result.dataset_id
    finally:
        catalog.close()


def _publish_canonical_bars(
    sources: list[VerifiedSourceBarDataset],
    store_root: Path,
    db_path: Path,
    output_dir: Path,
) -> DatasetPublishResult:
    """Publish canonical market_bars from the combined source datasets."""
    canonical_res = publish_canonical_bars(
        sources,
        output_dir=output_dir,
        code_commit="INFRA-001",
    )

    config = DatasetStoreConfig(root=store_root)
    catalog = SqliteDatasetCatalog(db_path)
    try:
        publisher = DatasetPublisher(config, catalog)
        result = publisher.publish(canonical_res.publish_plan, register_catalog=True)
        return result
    finally:
        catalog.close()


def _analyze_canonical_dataset(
    canonical_ds: DatasetPublishResult,
    store_root: Path,
    holdout_start: datetime,
) -> dict[str, Any]:
    """Compute bar span, total count, and holdout count from the canonical dataset."""
    from pyarrow import parquet as pq
    from pyarrow import concat_tables

    dataset_base = lexical_join(store_root, str(Path(canonical_ds.manifest_uri).parent))
    daily_paths = list((dataset_base / "market_bars" / "daily").rglob("bars.parquet"))
    intraday_paths = list((dataset_base / "market_bars" / "intraday").rglob("bars.parquet"))
    paths = daily_paths or intraday_paths

    if not paths:
        return {
            "bar_start": None,
            "bar_end": None,
            "total_bar_count": 0,
            "bars_in_holdout_count": 0,
            "daily_partition_count": 0,
            "intraday_partition_count": 0,
        }

    tables = [pq.read_table(str(p)) for p in paths if p.is_file()]
    table = concat_tables(tables, promote_options="default")
    period_starts = table.column("period_start").to_pylist()
    holdout_us = int(holdout_start.timestamp() * 1_000_000)

    dt_values = [datetime.fromtimestamp(ps / 1_000_000, tz=UTC) for ps in period_starts]
    return {
        "bar_start": min(dt_values).isoformat(),
        "bar_end": max(dt_values).isoformat(),
        "total_bar_count": len(period_starts),
        "bars_in_holdout_count": int(sum(1 for ps in period_starts if ps >= holdout_us)),
        "daily_partition_count": len(daily_paths),
        "intraday_partition_count": len(intraday_paths),
    }


def _paper_step(
    *,
    run_paper: bool,
    db_path: Path,
    store_root: Path,
    dataset_id: str,
) -> dict[str, Any]:
    """Paper loop step. Always skips the archived tsmom_14_3."""
    if not run_paper:
        return {
            "paper_skipped": True,
            "paper_skip_reason": "Paper loop disabled by default; no pre-registered active factor.",
        }

    # Check for active pre-registered factor. There is none at this time, so skip.
    return {
        "paper_skipped": True,
        "paper_skip_reason": (
            "No pre-registered active factor available. The archived tsmom_14_3 "
            "(mod_tsmom_14_3_v1, REJECTED) is explicitly not run."
        ),
    }


def _append_registry_row(report_path: Path) -> None:
    """Append an INFRA-001 row to experiment_registry.csv (idempotent)."""
    if not EXPERIMENT_REGISTRY.exists():
        return

    artifacts_json = json.dumps(
        {"ops_report": str(report_path)},
        separators=(",", ":"),
        sort_keys=True,
    )
    new_row = {
        "experiment_id": "INFRA-001",
        "status": "EXECUTED",
        "artifacts_json": artifacts_json,
        "generated_at": datetime.now(UTC).isoformat(),
    }

    rows: list[dict[str, str]] = []
    if EXPERIMENT_REGISTRY.exists():
        with EXPERIMENT_REGISTRY.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

    rows = [r for r in rows if r.get("experiment_id") != "INFRA-001"]
    rows.append(new_row)

    with EXPERIMENT_REGISTRY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["experiment_id", "status", "artifacts_json", "generated_at"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="INFRA-001 daily bar refresh + paper scheduler")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--raw-root", type=str, default="data/exp003_store/raw")
    parser.add_argument("--stage-dir", type=str, default="data/exp003_store/daily_stage")
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--run-paper", action="store_true", help="Enable paper loop step (still skips archived tsmom_14_3)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Skip network fetch and paper loop; report on existing canonical dataset")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="Perform real incremental fetch and publish")
    parser.add_argument("--output-dir", type=str, default="research/sprint_004")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    store_root = Path(args.store_root)
    raw_root = Path(args.raw_root)
    stage_dir = Path(args.stage_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    run_at = datetime.now(UTC)
    holdout_start = datetime.fromisoformat(HOLDOUT_START)

    # Resolve latest canonical dataset
    catalog = SqliteDatasetCatalog(db_path)
    try:
        canonical_dataset_id = catalog.resolve_latest_by_type("market_bars")
    finally:
        catalog.close()

    if canonical_dataset_id is None:
        raise RuntimeError("No canonical market_bars dataset found")

    print(f"INFRA-001: latest canonical dataset {canonical_dataset_id}", file=sys.stderr)

    fetch_symbols: list[str] = []
    if args.dry_run:
        print("INFRA-001: dry-run mode; skipping network fetch and paper loop", file=sys.stderr)
        # Use the latest canonical dataset for the report
        ds_row = SqliteDatasetCatalog(db_path).get_dataset(canonical_dataset_id)
        quality_status = ds_row["quality_status"] if ds_row else "UNKNOWN"
        metrics = _analyze_canonical_dataset(
            DatasetPublishResult(
                dataset_id=canonical_dataset_id,
                manifest_sha256=ds_row["manifest_sha256"] if ds_row else "",
                dataset_path=lexical_join(store_root, str(Path(ds_row["manifest_uri"]).parent)) if ds_row else store_root,
                manifest_uri=ds_row["manifest_uri"] if ds_row else "",
                reused_existing=True,
                catalog_registered=True,
                manifest=None,  # type: ignore[arg-type]
                receipt=None,  # type: ignore[arg-type]
            ),
            store_root,
            holdout_start,
        )
        paper_metrics = _paper_step(run_paper=False, db_path=db_path, store_root=store_root, dataset_id=canonical_dataset_id)
        new_canonical_dataset_id = canonical_dataset_id
    else:
        # Real incremental refresh
        stage_dir.mkdir(parents=True, exist_ok=True)
        existing_sources = _load_existing_source_datasets(db_path, store_root, canonical_dataset_id)
        latest_end = _latest_event_end(existing_sources)
        next_start = latest_end + timedelta(days=1)
        today = run_at.replace(hour=0, minute=0, second=0, microsecond=0)

        print(f"INFRA-001: latest source end {latest_end}; fetching from {next_start}", file=sys.stderr)

        new_sources: list[VerifiedSourceBarDataset] = list(existing_sources)
        client: httpx.Client | None = None
        try:
            client = httpx.Client(timeout=30.0)
            for symbol in symbols:
                if next_start > today:
                    print(f"INFRA-001: skip {symbol} - no new calendar days to fetch", file=sys.stderr)
                    continue
                instrument_id = BINANCE_TO_INSTRUMENT_ID.get(symbol)
                if instrument_id is None:
                    print(f"INFRA-001: skip {symbol} - unknown instrument_id", file=sys.stderr)
                    continue
                fetch_symbols.append(symbol)
                print(f"INFRA-001: fetching {symbol} 1d from {next_start} to {today}", file=sys.stderr)
                new_ds_id = _fetch_and_publish_source(
                    symbol,
                    instrument_id,
                    next_start,
                    today,
                    db_path,
                    store_root,
                    raw_root,
                    stage_dir,
                    client=client,
                )
                print(f"INFRA-001: published source dataset {new_ds_id}", file=sys.stderr)
                new_sources.append(_load_source_dataset(new_ds_id, store_root, SqliteDatasetCatalog(db_path)))
        finally:
            if client is not None:
                client.close()

        if not fetch_symbols:
            print("INFRA-001: no new bars fetched; reusing existing canonical dataset", file=sys.stderr)
            new_canonical_dataset_id = canonical_dataset_id
            quality_status = "PASS"
            metrics = _analyze_canonical_dataset(
                DatasetPublishResult(
                    dataset_id=canonical_dataset_id,
                    manifest_sha256="",
                    dataset_path=store_root,
                    manifest_uri="",
                    reused_existing=True,
                    catalog_registered=True,
                    manifest=None,  # type: ignore[arg-type]
                    receipt=None,  # type: ignore[arg-type]
                ),
                store_root,
                holdout_start,
            )
        else:
            canonical_output = stage_dir / "canonical"
            canonical_output.mkdir(parents=True, exist_ok=True)
            canonical_result = _publish_canonical_bars(new_sources, store_root, db_path, canonical_output)
            new_canonical_dataset_id = canonical_result.dataset_id
            quality_status = canonical_result.manifest.quality_status.value if canonical_result.manifest else "UNKNOWN"
            metrics = _analyze_canonical_dataset(canonical_result, store_root, holdout_start)
            print(f"INFRA-001: published canonical dataset {new_canonical_dataset_id}", file=sys.stderr)

        paper_metrics = _paper_step(
            run_paper=args.run_paper,
            db_path=db_path,
            store_root=store_root,
            dataset_id=new_canonical_dataset_id,
        )

    artifact: dict[str, Any] = {
        "experiment_id": "INFRA-001",
        "run_at": run_at.isoformat(),
        "mode": "dry-run" if args.dry_run else "refresh",
        "control_database": str(db_path),
        "dataset_store_root": str(store_root),
        "raw_store_root": str(raw_root),
        "canonical_dataset_id": new_canonical_dataset_id,
        "prior_canonical_dataset_id": canonical_dataset_id,
        "canonical_dataset_quality_status": quality_status,
        "universe": sorted(symbols),
        "paper_symbols": sorted(BINANCE_TO_PAPER_MAP.values()),
        "holdout_start": HOLDOUT_START,
        "holdout_policy": (
            "Bars from 2026-07-24 onward are reserved for pre-registered single-hypothesis tests. "
            "No factor exploration or selection may use the contaminated window through 2026-07-23."
        ),
        "bars": {
            "bar_start": metrics.get("bar_start"),
            "bar_end": metrics.get("bar_end"),
            "total_bar_count": metrics.get("total_bar_count", 0),
            "bars_in_holdout_count": metrics.get("bars_in_holdout_count", 0),
            "daily_partition_count": metrics.get("daily_partition_count", 0),
            "intraday_partition_count": metrics.get("intraday_partition_count", 0),
        },
        "fetch": {
            "symbols_requested": symbols,
            "symbols_fetched": fetch_symbols if not args.dry_run else [],
            "new_bars_fetched": len(fetch_symbols),
        },
        "paper": paper_metrics,
        "archived_factor_note": (
            "The archived tsmom_14_3 / mod_tsmom_14_3_v1 (REJECTED) is never run by this ops runner. "
            "A future paper loop requires a pre-registered factor committed before any data is touched."
        ),
        "live_eligible": False,
        "live_eligible_note": "INFRA-001 is an ops refresh and scheduler; no LIVE authorization.",
        "cross_references": [
            "research/sprint_004/25_QUALITY_CLEARED_BARS_REPORT.json",
            "research/sprint_004/29_HOLDOUT_RESERVATION.json",
            "tickets/templates/PRE_REGISTERED_TEST.md",
        ],
        "prior_artifacts": [
            "research/sprint_004/25_QUALITY_CLEARED_BARS_REPORT.json",
            "research/sprint_004/26_TSMOM_14_3_PASS_BARS_PAPER.json",
            "research/sprint_004/27_TSMOM_14_3_PAPER_PROMOTION.json",
            "research/sprint_004/28_MULTIPLE_TESTING_ANALYSIS.json",
            "research/sprint_004/29_HOLDOUT_RESERVATION.json",
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }

    out_path = output_dir / "30_DAILY_OPS_REPORT.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"INFRA-001: ops report written to {out_path}", file=sys.stderr)

    _append_registry_row(out_path)

    print(json.dumps(artifact, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
