#!/usr/bin/env python3
"""DATA-005 — Quality-cleared canonical market_bars for frozen TSMOM path.

Approach A: extend BAR-001 to accept native 1d source bars as valid daily
promotion input (no resampling needed). Re-publish the same DATA-004 source
datasets through the updated canonical path, producing a new market_bars
dataset with quality PASS (or PASS_WITH_WARNINGS). Writes the report artifact
25_QUALITY_CLEARED_BARS_REPORT.json.

No TSMOM re-tune. No LIVE. Does not mutate artifacts 08-24.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetManifest,
    DatasetPublishResult,
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
from cryptofactors.catalog.dataset.paths import lexical_join
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.execution.symbols import PAPER_TO_INSTRUMENT_ID
from cryptofactors.market.bars import VerifiedSourceBarDataset, publish_canonical_bars

UTC = timezone.utc

OLD_DATASET_ID = "ds_a17651d5c871656f18c29d50fe96d41fa9f08eee8436b276237f96a679764dcd"


def _us_to_datetime(us: int) -> datetime:
    return datetime.fromtimestamp(us / 1_000_000, tz=UTC)


def _parse_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    # Replace 'Z' with '+00:00' and parse ISO 8601.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _manifest_from_json(manifest: dict[str, Any]) -> DatasetManifest:
    """Reconstruct a DatasetManifest from a manifest.json dict."""
    schema = manifest["schema"]
    transform = manifest["transform"]
    code = manifest["code"]
    config = manifest.get("config") or {"config_sha256": manifest["config_sha256"]}
    dependencies = manifest["dependencies"]
    files = manifest["files"]
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
    quality_status = manifest["quality_status"]
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
            for dep in dependencies
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
            for f in files
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
        quality_status=QualityStatus(quality_status),
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
    db_path: Path,
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

    files = manifest.files
    if not files:
        raise RuntimeError(f"Source dataset {dataset_id} manifest has no files")

    local_files: dict[str, Path] = {}
    instrument_id = 1
    for f in files:
        rel = f.relative_path
        if not rel.endswith("bars.parquet"):
            continue
        # Published source manifests use the same URI as relative_path.
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


def _analyze_canonical_dataset(
    canonical_ds: DatasetPublishResult,
    store_root: Path,
) -> dict[str, Any]:
    """Compute bar span and per-symbol counts from the published canonical dataset."""
    dataset_base = store_root
    if canonical_ds.manifest_uri:
        dataset_base = lexical_join(store_root, str(Path(canonical_ds.manifest_uri).parent))

    bar_paths = list((dataset_base / "market_bars").rglob("bars.parquet"))
    if not bar_paths:
        return {
            "total_bar_count": 0,
            "bar_start": None,
            "bar_end": None,
            "symbols": [],
        }

    tables = [pq.read_table(str(p)) for p in bar_paths if p.is_file()]
    table = pa.concat_tables(tables, promote_options="default")

    instrument_ids = table.column("instrument_id").to_pylist()
    period_starts = table.column("period_start").to_pylist()

    by_instrument: dict[int, list[datetime]] = defaultdict(list)
    for iid, ps in zip(instrument_ids, period_starts):
        if iid is None or ps is None:
            continue
        by_instrument[int(iid)].append(_us_to_datetime(int(ps)))

    symbol_stats: list[dict[str, Any]] = []
    for paper_symbol, instrument_id in sorted(PAPER_TO_INSTRUMENT_ID.items(), key=lambda kv: kv[1]):
        dates = sorted(by_instrument.get(instrument_id, []))
        symbol_stats.append({
            "paper_symbol": paper_symbol,
            "instrument_id": instrument_id,
            "row_count": len(dates),
            "bar_start": dates[0].isoformat() if dates else None,
            "bar_end": dates[-1].isoformat() if dates else None,
        })

    all_dates = [d for dates in by_instrument.values() for d in dates]
    return {
        "total_bar_count": int(table.num_rows),
        "bar_start": min(all_dates).isoformat() if all_dates else None,
        "bar_end": max(all_dates).isoformat() if all_dates else None,
        "symbols": symbol_stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-005 — quality-cleared canonical bars")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--old-dataset-id", type=str, default=OLD_DATASET_ID)
    parser.add_argument("--output-dir", type=str, default="research/sprint_004")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    store_root = Path(args.store_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog = SqliteDatasetCatalog(db_path)
    try:
        old_ds = catalog.get_dataset(args.old_dataset_id)
        if old_ds is None:
            raise RuntimeError(f"Old dataset {args.old_dataset_id} not found")

        # Resolve source dataset IDs from the old canonical dataset's manifest.
        old_manifest_path = lexical_join(store_root, str(Path(old_ds["manifest_uri"]).parent), "manifest.json")
        old_manifest = json.loads(old_manifest_path.read_text())
        source_dataset_ids = [
            dep["id"] for dep in old_manifest.get("dependencies", [])
            if dep.get("kind") == "DATASET" and str(dep.get("role", "")).startswith("source")
        ]

        print(f"DATA-005: republishing {len(source_dataset_ids)} source datasets", file=sys.stderr)

        sources: list[VerifiedSourceBarDataset] = []
        for ds_id in source_dataset_ids:
            src = _load_source_dataset(ds_id, db_path, store_root, catalog)
            sources.append(src)
            print(f"  loaded {ds_id} instrument_id={src.instrument_id}", file=sys.stderr)
    finally:
        catalog.close()

    canonical_stage_dir = store_root / "staged" / "canonical_bars_cleared"
    canonical_stage_dir.mkdir(parents=True, exist_ok=True)

    canonical_plan_res = publish_canonical_bars(
        source_datasets=sources,
        output_dir=canonical_stage_dir,
        code_commit="DATA-005",
    )

    config = DatasetStoreConfig(root=store_root)
    catalog = SqliteDatasetCatalog(db_path)
    publisher = DatasetPublisher(config, catalog)
    canonical_ds = publisher.publish(canonical_plan_res.publish_plan, register_catalog=True)
    print(
        f"BAR-001 quality-cleared canonical market_bars published: {canonical_ds.dataset_id}",
        file=sys.stderr,
    )

    # Verify catalog state.
    catalog2 = SqliteDatasetCatalog(db_path)
    try:
        ds_row = catalog2.get_dataset(canonical_ds.dataset_id)
        quality_status = str(ds_row["quality_status"]) if ds_row else "UNKNOWN"
    finally:
        catalog2.close()

    analysis = _analyze_canonical_dataset(canonical_ds, store_root)

    if analysis["bar_start"] and analysis["bar_end"]:
        start_dt = datetime.fromisoformat(analysis["bar_start"])
        end_dt = datetime.fromisoformat(analysis["bar_end"])
        span_days = (end_dt - start_dt).days
        span_months = round(span_days / 30.4375, 2)
    else:
        span_days = 0
        span_months = 0.0

    report_data = {
        "experiment_id": "DATA-005",
        "data_mode": "real_asof",
        "approach": "A",
        "approach_note": (
            "Extended BAR-001 daily eligibility to include native 1d source bars. "
            "1d source rows are now treated as complete daily bars and promoted directly "
            "to the daily partition without sub-day resampling."
        ),
        "old_canonical_dataset_id": args.old_dataset_id,
        "old_canonical_quality_status": "REJECTED",
        "new_canonical_dataset_id": canonical_ds.dataset_id,
        "new_canonical_quality_status": quality_status,
        "source_dataset_ids": source_dataset_ids,
        "store_root": str(store_root),
        "db_path": str(db_path),
        "bar_start": analysis["bar_start"],
        "bar_end": analysis["bar_end"],
        "span_days": span_days,
        "span_months": span_months,
        "total_bar_count": analysis["total_bar_count"],
        "symbols_covered": sorted(PAPER_TO_INSTRUMENT_ID.keys()),
        "per_symbol": analysis["symbols"],
        "frozen_config_note": "tsmom_14_3 parameters remain unchanged; this is a dataset-quality fix only.",
        "live_eligible": False,
        "live_eligible_note": "DATA-005 is a quality-clearing dataset ticket; no LIVE authorization.",
        "cross_references": [
            "research/sprint_004/20_EXTENDED_HISTORY_REPORT.json",
            "research/sprint_004/24_TSMOM_14_3_PAPER_SESSION.json",
        ],
        "prior_artifacts": [
            "research/sprint_004/13_REAL_PAPER_SESSION.json",
            "research/sprint_004/14_RISK_COMPLIANT_PAPER_SESSION.json",
            "research/sprint_004/15_MOMTS_RISK_DIAGNOSIS.json",
            "research/sprint_004/16_MOMTS_LONG_SESSION.json",
            "research/sprint_004/17_NEUTRAL_RISK_SESSION.json",
            "research/sprint_004/18_TSMOM_GRID_RESULTS.json",
            "research/sprint_004/19_TSMOM_OOS_VALIDATION.json",
            "research/sprint_004/20_EXTENDED_HISTORY_REPORT.json",
            "research/sprint_004/21_TSMOM_EXTENDED_OOS.json",
            "research/sprint_004/22_TSMOM_14_0_PAPER_SESSION.json",
            "research/sprint_004/23_TSMOM_FULLWINDOW_SCREEN.json",
            "research/sprint_004/24_TSMOM_14_3_PAPER_SESSION.json",
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }

    report_path = output_dir / "25_QUALITY_CLEARED_BARS_REPORT.json"
    report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"Quality-cleared bars report written to {report_path}", file=sys.stderr)
    print(json.dumps(report_data, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
