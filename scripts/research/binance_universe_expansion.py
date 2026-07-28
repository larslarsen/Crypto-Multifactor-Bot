#!/usr/bin/env python3
"""DATA-008 Binance spot universe expansion runner.

Discovers spot symbols from exchangeInfo, ranks them on measured trailing 30-day
quote volume (24-hour ticker data is recorded as non-truncating observation only),
checks history eligibility, backfills daily bars for what qualifies, and republishes
the complete canonical snapshot.

Nothing is admitted silently: every excluded symbol carries a taxonomy reason, every
short-history symbol is deferred with a reason, and a symbol that was selected but
failed acquisition blocks the whole publication rather than disappearing from the
panel. Watermarks are written only after publication succeeds.
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

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.acquisition.binance_snapshot import (
    DAY_SECONDS,
    BinanceBarAcquirer,
    KlineBar,
    SymbolAcquisition,
    SymbolState,
    WatermarkStore,
    bars_from_records,
    merge_canonical_bars,
    resume_start,
    symbol_covers_range,
)
from cryptofactors.acquisition.binance_universe import (
    BASE_PANEL_DATASET_ID,
    BINANCE_BASE_URL,
    EXCLUSION_TAXONOMY_VERSION,
    VOLUME_WINDOW,
    BinanceUniverseAcquirer,
    Exclusion,
    ExclusionReason,
    HistoryEligibility,
    MeasurementStatus,
    SelectionConfig,
    SpotSymbol,
    VolumeEvidence,
    VolumeMeasurement,
    filter_non_volume_taxonomy,
    load_base_panel_symbols,
)
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
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.writer import RawObjectWriter
from cryptofactors.ingest.raw_http import RawHttpAcquirer

DATASET_TYPE = "binance_spot_daily_bars"
BASE_PANEL_TYPE = "market_bars"
RELATIVE_PATH = "cex/binance_spot_daily_bars/bars.parquet"
REPORT_PATH = Path("research/sprint_004/36_BINANCE_UNIVERSE_EXPANSION.json")

#: Source whose state the declared commit must describe.
IDENTITY_PATHS = (
    "src/cryptofactors/acquisition/binance_universe.py",
    "src/cryptofactors/acquisition/binance_snapshot.py",
    "src/cryptofactors/ingest/raw_http.py",
    "scripts/research/binance_universe_expansion.py",
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_identity_paths() -> tuple[str, ...]:
    """Every first-party source file actually loaded, as repo-relative paths.

    The hand-maintained tuple above silently under-covers. This runner also imports
    the dataset catalog, publisher, output hashing, migration runner and raw-object
    store, and each of those determines the bytes of the published artifact. A change
    to any of them alters the dataset while a four-file identity check still reports
    clean, which is the same false-identity class cited in REVIEW-0243, 0245 and 0247.

    Deriving the set from sys.modules cannot drift as imports change: a new dependency
    is covered the moment it is imported, with no tuple to remember to update. The
    static tuple is retained and unioned in so the core four are covered even if a
    module is somehow not resolvable at call time.
    """
    paths: set[str] = set(IDENTITY_PATHS)
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        try:
            relative = Path(filename).resolve().relative_to(REPO_ROOT)
        except (OSError, ValueError):
            # Outside the repository (stdlib, site-packages) or unresolvable.
            continue
        if relative.suffix != ".py" or relative.parts[0] not in ("src", "scripts"):
            continue
        paths.add(relative.as_posix())
    return tuple(sorted(paths))

SNAPSHOT_SCHEMA = pa.schema([
    ("symbol", pa.string()),
    ("open_time", pa.string()),
    ("open_time_us", pa.int64()),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("close", pa.float64()),
    ("volume", pa.float64()),
    ("quote_volume", pa.float64()),
    ("trades", pa.int64()),
    ("provider", pa.string()),
    ("raw_object_id", pa.string()),
])


def verify_source_identity(declared: str, *, paths: Sequence[str]) -> None:
    """Refuse to publish unless the declared commit is the source actually running.

    The runner previously accepted --code-commit verbatim, so a manifest could name a
    commit that never produced the artifact. Both halves matter: the checked-out
    commit must match, and the relevant source must be clean, or the declared commit
    does not describe what executed.
    """
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", *paths],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("cannot verify source identity against git") from exc
    if head != declared:
        raise RuntimeError(
            f"declared code commit {declared} is not the checked-out commit {head}; "
            "commit the source first, then publish under that commit"
        )
    if dirty:
        raise RuntimeError(
            "refusing to publish from a dirty source tree:\n" + dirty
        )


def resolve_code_commit(explicit: str | None) -> str:
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


def load_prior_snapshot(
    catalog: SqliteDatasetCatalog, store_root: Path
) -> tuple[str | None, list[KlineBar], dict[str, Any]]:
    """Prior canonical dataset, its revalidated rows, and the reconciliation."""
    dataset_id = catalog.resolve_latest_by_type(DATASET_TYPE)
    if dataset_id is None:
        return None, [], {"prior_dataset_id": None, "state": "none"}

    files = [
        f for f in catalog.list_files(dataset_id)
        if str(f["storage_uri"]).endswith(RELATIVE_PATH)
    ]
    if len(files) != 1:
        raise RuntimeError(f"prior dataset {dataset_id} does not declare one {RELATIVE_PATH}")
    declared = files[0]

    parquet = dataset_absolute_dir(store_root, dataset_id) / RELATIVE_PATH
    if not parquet.exists():
        raise RuntimeError(
            f"prior canonical dataset {dataset_id} is registered but its output "
            f"{parquet} is missing; refusing to publish a delta as a full snapshot"
        )
    actual_sha256, byte_size = stream_sha256_and_size(parquet)
    if actual_sha256 != str(declared["file_sha256"]):
        raise RuntimeError(
            f"prior output hash {actual_sha256} does not match catalog "
            f"{declared['file_sha256']}"
        )
    table = pq.read_table(parquet)
    if table.num_rows != int(declared["row_count"]):
        raise RuntimeError(
            f"prior output has {table.num_rows} rows, catalog says {declared['row_count']}"
        )
    if set(SNAPSHOT_SCHEMA.names) != set(table.column_names):
        raise RuntimeError("prior output schema does not match the snapshot schema")

    declared_raw = {str(r["raw_object_id"]) for r in catalog.list_raw_inputs(dataset_id)}
    bars = bars_from_records(table.to_pylist(), allowed_raw_object_ids=declared_raw)
    return dataset_id, bars, {
        "prior_dataset_id": dataset_id,
        "state": "reconciled",
        "file_sha256": actual_sha256,
        "byte_size": byte_size,
        "row_count": table.num_rows,
        "declared_raw_object_ids": len(declared_raw),
        "rows_revalidated": len(bars),
    }


def build_report(
    *,
    config: SelectionConfig,
    code_commit: str,
    end_time: datetime,
    default_start: datetime,
    selection: Any,
    eligibility: Sequence[HistoryEligibility],
    acquisitions: Sequence[SymbolAcquisition],
    blocked: Sequence[SymbolAcquisition],
    failed_measurements: Sequence[tuple[SpotSymbol, VolumeMeasurement]] = (),
    log: Any,
    prior_reconciliation: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
    watermarks_before: Mapping[str, str],
    watermarks_after: Mapping[str, str],
    snapshot: Sequence[KlineBar],
    dataset_id: str | None,
    net_rows_added: int = 0,
    covered_symbols: set[str] | None = None,
    base_panel_dataset_id: str | None = None,
    newly_published: set[str] | None = None,
    budget: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    # A failed observation is reported as a failure, never also as a deferral.
    deferred = [
        item for item in eligibility if not item.eligible and not item.observation_failed
    ]
    failed_observations = [item for item in eligibility if item.observation_failed]
    snapshot_symbols = {bar.symbol for bar in snapshot}
    per_symbol_spans = {
        sym: {
            "start": min(b.open_time for b in snapshot if b.symbol == sym).isoformat(),
            "end": max(b.open_time for b in snapshot if b.symbol == sym).isoformat(),
            "rows": sum(1 for b in snapshot if b.symbol == sym),
        }
        for sym in sorted(snapshot_symbols)
    }
    by_state: dict[str, list[dict[str, Any]]] = {}
    for acquisition in acquisitions:
        by_state.setdefault(acquisition.state.value, []).append(acquisition.as_dict())

    return {
        "experiment_id": "DATA-008-BINANCE-UNIVERSE-EXPANSION",
        "generated_at": datetime.now(UTC).isoformat(),
        "pinned_end_time": end_time.isoformat(),
        "default_start": default_start.isoformat(),
        "effective_config": config.as_dict(),
        "config_fingerprint": config.fingerprint(),
        # Stated so the report can be checked against the catalog manifest without
        # re-deriving it; a dataset must be reproducible from its own lineage.
        "code_commit": code_commit,
        "volume_window": VOLUME_WINDOW,
        "exclusion_taxonomy_version": EXCLUSION_TAXONOMY_VERSION,
        "base_panel_dataset_id": base_panel_dataset_id,
        "additive_dataset_id": dataset_id,
        "base_addition_symbols_disjoint": not (set(covered_symbols or ()) & snapshot_symbols),
        "logical_union_symbol_count": len(set(covered_symbols or ()) | snapshot_symbols),
        "budget": dict(budget or {}),
        "base_panel_symbols": sorted(covered_symbols or ()),
        "base_panel_symbol_count": len(covered_symbols or ()),
        "selected_symbols_this_run": [item.symbol for item in selection.ranked],
        # Derived from what is actually published, including carried-forward symbols,
        # not from the current selection list.
        "additive_symbols": sorted(snapshot_symbols),
        "additive_symbol_count": len(snapshot_symbols),
        "newly_published_symbols": sorted(newly_published or ()),
        "deferred_symbols_this_run": sorted(
            a.symbol for a in acquisitions if a.state in
            (SymbolState.DEFERRED, SymbolState.BUDGET_DEFERRED)
        ),
        "per_symbol_spans": per_symbol_spans,
        "total_panel_symbol_count": len(set(covered_symbols or ()) | snapshot_symbols),
        "selected_symbols": [item.as_dict() for item in selection.ranked],
        "excluded_symbols": [item.as_dict() for item in selection.excluded],
        "deferred_symbols": [item.as_dict() for item in deferred],
        "eligible_symbols": [item.as_dict() for item in eligibility if item.eligible],
        "symbols_by_state": by_state,
        "failed_history_observations": [item.as_dict() for item in failed_observations],
        "failed_measurements": [
            {"symbol": s.symbol, "reason": m.reason} for s, m in (failed_measurements or [])
        ],
        "failed_symbols": [
            item.as_dict() for item in acquisitions if item.state is SymbolState.FAILED
        ],
        "blocking_symbols": [
            {"symbol": item.symbol, "state": item.state.value, "error": item.error}
            for item in blocked
        ],
        "acquisition_attempts": log.as_dicts(),
        "raw_dependency_count": len(log.raw_object_ids),
        "snapshot_raw_object_count": len({bar.raw_object_id for bar in snapshot}),
        "failed_acquisition_count": len(log.failures),
        "retry_count": len(log.retries),
        "rate_limit_incidents": [item.as_dict() for item in log.rate_limit_incidents],
        "watermarks_before": dict(watermarks_before),
        "watermarks_after": dict(watermarks_after),
        "rows_fetched": sum(len(a.bars) for a in acquisitions if a.usable),
        "total_rows_added": net_rows_added,
        "snapshot_row_count": len(snapshot),
        "snapshot_span": {
            # Global min/max: the snapshot is symbol-major, so first/last rows are not
            # the earliest and latest bars.
            "start": min((b.open_time for b in snapshot), default=None) and
                     min(b.open_time for b in snapshot).isoformat(),
            "end": max((b.open_time for b in snapshot), default=None) and
                   max(b.open_time for b in snapshot).isoformat(),
        },
        "prior_dataset_reconciliation": dict(prior_reconciliation),
        "catalog_reconciliation": dict(reconciliation),
        "canonical_dataset_id": dataset_id,
        "live_eligible": False,
    }


def _write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-008 Binance universe expansion")
    parser.add_argument("--end-time", required=True, help="pinned UTC end day, ISO-8601")
    parser.add_argument("--default-start", required=True, help="first day, ISO-8601")
    parser.add_argument("--db-path", type=Path, default=Path("exp003.db"))
    parser.add_argument("--raw-root", type=Path, default=Path("data/exp003_store/raw"))
    parser.add_argument("--store-root", type=Path, default=Path("data/exp003_store"))
    parser.add_argument("--watermark-path", type=Path, default=Path("data/data008_watermarks.json"))
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--symbols-per-day", type=int, default=20_000)
    parser.add_argument(
        "--processing-day", default=None,
        help="override the UTC processing day (capacity reset key); testing/ops use",
    )
    parser.add_argument("--base-panel-dataset-id", default=BASE_PANEL_DATASET_ID)
    parser.add_argument("--min-quote-volume", type=float, default=None)
    parser.add_argument("--min-history-days", type=int, default=None)
    parser.add_argument("--base-url", default=BINANCE_BASE_URL)
    parser.add_argument("--code-commit", default=None)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--backoff-seconds", type=float, default=15.0)
    args = parser.parse_args()

    end_time = datetime.fromisoformat(args.end_time)
    default_start = datetime.fromisoformat(args.default_start)
    if end_time.tzinfo is None or default_start.tzinfo is None:
        raise RuntimeError("--end-time and --default-start must be timezone-aware")
    # Checked here rather than deep inside coverage helpers, where it would surface
    # as a per-symbol failure long after the run began.
    for label, moment in (("--default-start", default_start), ("--end-time", end_time)):
        if int(moment.timestamp()) % DAY_SECONDS:
            raise RuntimeError(f"{label} must be UTC midnight, got {moment.isoformat()}")
    if default_start > end_time:
        raise RuntimeError("--default-start must not be after --end-time")

    overrides: dict[str, Any] = {"top_n": args.top_n}
    if args.min_quote_volume is not None:
        overrides["min_quote_volume"] = args.min_quote_volume
    if args.min_history_days is not None:
        overrides["min_history_days"] = args.min_history_days
    overrides["base_panel_dataset_id"] = args.base_panel_dataset_id
    overrides["symbols_per_day"] = args.symbols_per_day
    overrides["default_start"] = default_start.isoformat()
    overrides["pinned_end"] = end_time.isoformat()
    # The endpoint actually in effect, not the module default: two runs against
    # different providers must not share a queue identity.
    overrides["evidence_source"] = args.base_url
    config = SelectionConfig(**overrides)
    code_commit = resolve_code_commit(args.code_commit)
    # Unconditional in production: there is no operator flag that can waive it. Tests
    # substitute the module attribute instead, which is not reachable from the CLI.
    # Paths are derived from what is actually loaded, not a fixed list that can rot.
    verify_source_identity(code_commit, paths=resolve_identity_paths())

    apply_migrations(args.db_path)
    # Pinned, never resolved: resolve_latest_by_type("market_bars") returns whichever
    # dataset published most recently, not the reviewer-authorized DATA-006 artifact.
    base_panel_dataset_id = args.base_panel_dataset_id
    covered_symbols = load_base_panel_symbols(
        args.db_path, base_panel_dataset_id, store_root=args.store_root
    )
    watermark_store = WatermarkStore(args.watermark_path)
    watermarks_before = watermark_store.load()

    raw_catalog = SqliteRawObjectCatalog(args.db_path)
    client = httpx.Client(timeout=30.0)
    acquisitions: list[SymbolAcquisition] = []
    eligibility: list[HistoryEligibility] = []
    # A symbol cannot have bars before it listed, so coverage is judged from its
    # effective start rather than the requested one.
    effective_starts: dict[str, datetime] = {}
    try:
        raw_acquirer = RawHttpAcquirer(
            raw_writer=RawObjectWriter(RawObjectStoreConfig(root=args.raw_root), raw_catalog),
            client=client,
            max_attempts=args.max_attempts,
            backoff_seconds=args.backoff_seconds,
        )
        universe = BinanceUniverseAcquirer(acquirer=raw_acquirer, base_url=args.base_url)
        discovered, _ = universe.fetch_exchange_info()
        evidence, _ = universe.fetch_volume_evidence()

        from cryptofactors.acquisition.binance_universe import select_symbols

        # Non-volume taxonomy first, then measure every survivor. A missing 24-hour
        # ticker entry must not remove a tradable target symbol from measurement.
        survivors, taxonomy_excluded = filter_non_volume_taxonomy(
            discovered=discovered, config=config, already_covered=covered_symbols,
        )
        # Typed so the optional evidence must be narrowed explicitly; a dict[str, Any]
        # let `VolumeEvidence | None` through unchecked.
        measured: dict[str, VolumeEvidence] = {}
        short_window: list[tuple[SpotSymbol, VolumeMeasurement]] = []
        failed_measurements: list[tuple[SpotSymbol, VolumeMeasurement]] = []
        for spot in survivors:
            measurement = universe.fetch_trailing_volume(spot.symbol, end_time=end_time)
            if measurement.evidence is not None and measurement.usable:
                measured[spot.symbol] = measurement.evidence
            elif measurement.status is MeasurementStatus.INCOMPLETE_WINDOW:
                short_window.append((spot, measurement))
            else:
                failed_measurements.append((spot, measurement))

        by_symbol = {s.symbol: s for s in survivors}
        selection = select_symbols(
            discovered=[by_symbol[s] for s in measured],
            evidence=measured, config=config, already_covered=covered_symbols,
        )
        selection.excluded.extend(taxonomy_excluded)
        selection.excluded.extend(
            Exclusion(
                symbol=spot.symbol, base_asset=spot.base_asset,
                quote_asset=spot.quote_asset,
                reason=ExclusionReason.INSUFFICIENT_VOLUME_WINDOW, detail=m.reason,
            )
            for spot, m in short_window
        )

        bars_acquirer = BinanceBarAcquirer(acquirer=raw_acquirer, base_url=args.base_url)
        processing_day = args.processing_day or datetime.now(UTC).date().isoformat()
        # Queue position is keyed by the pinned selection and survives day rollover;
        # capacity is keyed by the processing day and resets with it.
        # Capacity and processing day must not reset position, but a material change
        # to what is being selected must identify a new queue.
        selection_key = config.selection_fingerprint()
        attempted, used = watermark_store.load_cursor(
            selection_key=selection_key, processing_day=processing_day
        )
        budget_start = len(attempted)
        for ranked in selection.ranked:
            if ranked.symbol in attempted:
                continue
            if used >= args.symbols_per_day:
                # Capacity reached: recorded, not dropped, so the next run continues
                # from here rather than silently shrinking the requested panel.
                acquisitions.append(SymbolAcquisition(
                    symbol=ranked.symbol, state=SymbolState.BUDGET_DEFERRED,
                    error=f"daily symbol budget {args.symbols_per_day} reached",
                ))
                continue
            used += 1
            verdict = universe.fetch_history_eligibility(
                ranked.symbol, as_of=end_time, min_history_days=config.min_history_days
            )
            eligibility.append(verdict)
            if verdict.observation_failed:
                # Unknown, not deferred: it blocks publication and stays pending.
                acquisitions.append(SymbolAcquisition(
                    symbol=ranked.symbol, state=SymbolState.FAILED,
                    error="history request failed",
                ))
                continue
            if not verdict.eligible:
                # Documented, not admitted: a short-history symbol is not research
                # history and must not silently join the panel. This is a proven
                # terminal fact, so it advances the queue.
                acquisitions.append(SymbolAcquisition(
                    symbol=ranked.symbol, state=SymbolState.DEFERRED,
                    error=None if verdict.reason is None else verdict.reason.value,
                ))
                attempted.add(ranked.symbol)
                continue
            # A symbol cannot have bars before it listed, so the effective start is
            # the later of the requested start and its first observed bar. Demanding
            # pre-listing days would otherwise register as a leading coverage gap.
            listed_at = verdict.first_bar_open_time or default_start
            effective_starts[ranked.symbol] = max(default_start, listed_at)
            acquired_symbol = bars_acquirer.acquire(
                symbol=ranked.symbol,
                start_time=max(
                    resume_start(
                        watermarks_before, symbol=ranked.symbol, default_start=default_start
                    ),
                    listed_at,
                ),
                end_time=end_time,
            )
            acquisitions.append(acquired_symbol)
            # ALREADY_CURRENT is deliberately not persisted here. Its safety depends
            # on prior canonical coverage, which is only reconciled below; persisting
            # it now let a coverage-invalid identity be skipped by every later run.
        log = raw_acquirer.log
    finally:
        client.close()
        raw_catalog.close()

    # A measurement we could not obtain is not evidence of low volume; publishing a
    # lower-ranked survivor in its place would bias the canonical universe.
    for spot, measurement in failed_measurements:
        acquisitions.append(SymbolAcquisition(
            symbol=spot.symbol, state=SymbolState.FAILED,
            error=f"30d measurement failed: {measurement.reason}",
        ))

    acquired = [bar for a in acquisitions if a.usable for bar in a.bars]
    dataset_catalog = SqliteDatasetCatalog(args.db_path)
    dataset_id: str | None = None
    snapshot: list[KlineBar] = []
    watermarks_after = dict(watermarks_before)
    reconciliation: dict[str, Any] = {}
    try:
        prior_dataset_id, prior_bars, prior_reconciliation = load_prior_snapshot(
            dataset_catalog, args.store_root
        )
        blocked = [a for a in acquisitions if a.blocks_publication]
        already_current_gaps: dict[str, list[str]] = {}
        for acquisition in acquisitions:
            if acquisition.state is not SymbolState.ALREADY_CURRENT:
                continue
            covered, missing = symbol_covers_range(
                prior_bars, symbol=acquisition.symbol,
                start_time=effective_starts.get(acquisition.symbol, default_start),
                end_time=end_time,
            )
            if covered:
                # Safe only now that prior coverage reconciles.
                attempted.add(acquisition.symbol)
            else:
                already_current_gaps[acquisition.symbol] = [
                    moment.isoformat() for moment in missing
                ]
                blocked.append(acquisition)

        if blocked or not acquired:
            state = "blocked_by_incomplete_symbols" if blocked else "no_publishable_rows"
            report = build_report(
                config=config, code_commit=code_commit, end_time=end_time,
                default_start=default_start, selection=selection, eligibility=eligibility, acquisitions=acquisitions,
                blocked=blocked, failed_measurements=failed_measurements, log=log, prior_reconciliation=prior_reconciliation,
                reconciliation={
                    "state": state,
                    "already_current_missing_intervals": already_current_gaps,
                }, covered_symbols=covered_symbols,
                base_panel_dataset_id=base_panel_dataset_id,
                budget={"processing_day": processing_day, "queue_position": budget_start,
                        "queue_position_after": len(attempted), "used_today": used,
                        "limit": args.symbols_per_day},
                watermarks_before=watermarks_before,
                watermarks_after=watermarks_before, snapshot=[], dataset_id=None,
            )
            _write_report(args.report_path, report)
            # Safe terminal outcomes are progress even with nothing to publish; losing
            # them would make a constant daily limit retry the same head forever.
            # Safe terminal outcomes are progress even in a mixed batch. Identities
            # that blocked, or whose rows were not published, stay off the queue so a
            # constant daily limit does not repeat them while later ranks starve.
            # Rows that were acquired but not published are not progress; their
            # identities stay on the queue for retry.
            watermark_store.save_cursor(
                selection_key=selection_key, processing_day=processing_day,
                attempted=attempted, used=used,
            )
            print(f"DATA-008: {state}; prior snapshot and watermarks retained")
            return 1

        prior_symbols = {bar.symbol for bar in prior_bars}
        prior_keys = {bar.dedupe_key for bar in prior_bars}
        snapshot = merge_canonical_bars(prior_bars, acquired)
        net_rows_added = sum(1 for bar in snapshot if bar.dedupe_key not in prior_keys)
        newly_published = {b.symbol for b in snapshot} - prior_symbols
        table = pa.Table.from_pylist([b.as_dict() for b in snapshot], schema=SNAPSHOT_SCHEMA)

        with tempfile.TemporaryDirectory(prefix="data008-") as tmp:
            output = Path(tmp) / "bars.parquet"
            pq.write_table(table, output, compression="zstd")
            sha256, byte_size = stream_sha256_and_size(output)

            # Self-auditing: the snapshot directly declares every raw object its own
            # rows cite, so lineage does not depend on walking the prior-dataset chain.
            carried = {bar.raw_object_id for bar in snapshot}
            missing_raw = sorted(
                r for r in carried if not dataset_catalog.raw_object_exists(r)
            )
            if missing_raw:
                raise RuntimeError(f"snapshot cites raw objects that no longer exist: {missing_raw}")

            current = set(log.raw_object_ids)
            dependencies = [
                DependencyRef(
                    id=raw_id, kind=DependencyKind.RAW_OBJECT,
                    role=("controlling_response" if raw_id in current
                          else "carried_forward_row_source"),
                )
                for raw_id in sorted(current | carried)
            ]
            if prior_dataset_id is not None and prior_bars:
                dependencies.append(DependencyRef(
                    id=prior_dataset_id, kind=DependencyKind.DATASET,
                    role="prior_canonical_snapshot",
                ))
            # This dataset is additive to the accepted DATA-006 panel; consumers need
            # the pinned base id to reconcile the logical union.
            if base_panel_dataset_id is not None:
                dependencies.append(DependencyRef(
                    id=base_panel_dataset_id, kind=DependencyKind.DATASET,
                    role="base_panel",
                ))

            times = [bar.open_time for bar in snapshot]
            acquired_at = [o.acquired_at for o in log.outcomes if o.raw_object_id] or [
                datetime.now(UTC)
            ]
            plan = PublishPlan(
                dataset_type=DATASET_TYPE,
                schema=SchemaIdentity(name=DATASET_TYPE, version="1"),
                transform=TransformSpec(name="data008_binance_universe_expansion", version="1"),
                code=CodeIdentity(commit=code_commit),
                config=ConfigIdentity(config_sha256=config.fingerprint()),
                dependencies=dependencies,
                output_sources={RELATIVE_PATH: output},
                output_specs=[OutputFileSpec(
                    relative_path=RELATIVE_PATH, sha256=sha256, rows=table.num_rows,
                    bytes=byte_size, rows_verified=True,
                )],
                statistics=DatasetStatistics(row_count=table.num_rows, byte_size=byte_size),
                coverage=CoverageWindow(
                    event_start=min(times), event_end=max(times),
                    availability_start=min(acquired_at), availability_end=max(acquired_at),
                ),
                quality_status=QualityStatus.PASS,
                quality_summary={
                    "symbols": len({bar.symbol for bar in snapshot}),
                    "row_count": table.num_rows,
                    "blocking_symbols": 0,
                },
                created_at=datetime.now(UTC),
                row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
                row_receipts={RELATIVE_PATH: RowCountReceipt(
                    relative_path=RELATIVE_PATH, row_count=table.num_rows,
                    verifier_name="data008_snapshot_row_count",
                )},
            )
            result = DatasetPublisher(
                DatasetStoreConfig(root=args.store_root), dataset_catalog
            ).publish(plan, register_catalog=True)

        resolved = dataset_catalog.resolve_latest_by_type(DATASET_TYPE)
        reconciliation = {
            "state": "reconciled" if resolved == result.dataset_id else "mismatch",
            "published_dataset_id": result.dataset_id,
            "resolved_dataset_id": resolved,
            "manifest_sha256": result.manifest_sha256,
            "catalog_registered": result.catalog_registered,
            "output_sha256": sha256,
            "row_count": table.num_rows,
        }
        if resolved != result.dataset_id:
            raise RuntimeError(
                f"catalog reconciliation failed: published {result.dataset_id} but "
                f"resolve_latest_by_type returned {resolved}"
            )
        dataset_id = result.dataset_id

        # Publication succeeded, so published identities are now safe progress too.
        attempted |= {a.symbol for a in acquisitions if a.usable}
        for acquisition in acquisitions:
            if acquisition.watermark_candidate is None:
                continue
            watermarks_after[acquisition.symbol] = (
                acquisition.watermark_candidate.isoformat()
            )
        watermark_store.save(watermarks_after)
        watermark_store.save_cursor(
            selection_key=selection_key, processing_day=processing_day,
            attempted=attempted, used=used,
        )
    finally:
        dataset_catalog.close()

    report = build_report(
        config=config, code_commit=code_commit, end_time=end_time,
        default_start=default_start, selection=selection,
        eligibility=eligibility, acquisitions=acquisitions, blocked=[], log=log,
        prior_reconciliation=prior_reconciliation, reconciliation=reconciliation,
        watermarks_before=watermarks_before, watermarks_after=watermarks_after,
        snapshot=snapshot, dataset_id=dataset_id, net_rows_added=net_rows_added,
        covered_symbols=covered_symbols, base_panel_dataset_id=base_panel_dataset_id,
        newly_published=newly_published,
        budget={"processing_day": processing_day, "queue_position": budget_start,
                "queue_position_after": len(attempted), "used_today": used,
                "limit": args.symbols_per_day},
    )
    _write_report(args.report_path, report)
    print(f"DATA-008: published {len(snapshot)} rows as {dataset_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
