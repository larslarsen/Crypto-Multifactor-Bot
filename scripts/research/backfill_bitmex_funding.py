#!/usr/bin/env python3
"""DATA-009 — BitMEX full historical funding rate backfill.

Extends DATA-006 to:
- Discover all BitMEX perpetual symbols (Open + Settled/historical) from /instrument.
- Backfill 8-hour funding rates from 2016-05-13 (or symbol inception) to present.
- Resume incrementally via per-symbol watermarks without losing prior state.
- Merge prior staged full table with new rows so published dataset stays complete.
- Stay within the 120 req/min polite budget; record HTTP 429 incidents.
- Publish a new canonical dataset type (bitmex_funding_full), separate from DATA-006.

Default invocation is a **real** backfill. Synthetic mode requires ``--dry-run``
and never writes the acceptance report path.

No LIVE. No price/trade data. No other CEXes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
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
from cryptofactors.ingest.bitmex_funding import (
    BITMEX_FUNDING_SCHEMA,
    BitMEXFundingClient,
    build_funding_table,
)

DEFAULT_START_TIME = "2016-05-13T00:00:00+00:00"
WATERMARK_PATH = Path("data/bitmex_funding_full_watermarks.json")
REPORT_PATH = Path("research/sprint_004/39_BITMEX_FULL_BACKFILL.json")
DATASET_TYPE = "bitmex_funding_full"
STAGE_REL = Path("staged") / "bitmex_funding_full"
PARQUET_NAME = "funding.parquet"
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_US_PER_SECOND = 1_000_000


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def resolve_code_commit(explicit: str | None = None) -> str:
    """Resolve a real 40-char git SHA for CodeIdentity (no ticket-id placeholders)."""
    if explicit:
        commit = explicit.strip().lower()
        if not _COMMIT_RE.fullmatch(commit):
            raise RuntimeError(
                f"code commit must be a 40-char lowercase hex SHA, got {explicit!r}"
            )
        return commit
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "cannot resolve code commit from git HEAD; pass --code-commit"
        ) from exc
    commit = result.stdout.strip().lower()
    if not _COMMIT_RE.fullmatch(commit):
        raise RuntimeError(f"unexpected git commit {commit!r}")
    return commit


def config_sha256_for_run(payload: dict[str, Any]) -> str:
    """Deterministic SHA-256 of the run configuration (not a placeholder digest)."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def count_parquet_rows(path: Path | str) -> int:
    """Independently re-count rows from a written parquet file."""
    p = Path(path)
    pf = pq.ParquetFile(p)
    meta = pf.metadata
    if meta is not None:
        return int(meta.num_rows)
    return int(pq.read_table(p).num_rows)


def load_watermarks(path: Path) -> dict[str, str]:
    """Load per-symbol watermarks as ISO timestamps."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    raw = data.get("watermarks", {})
    if not isinstance(raw, dict):
        return {}
    return {str(k).upper(): str(v) for k, v in raw.items()}


def save_watermarks(path: Path, watermarks: dict[str, datetime]) -> None:
    """Save per-symbol watermarks as ISO timestamps (full map, sorted)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "watermarks": {
            sym: dt.isoformat()
            for sym, dt in sorted(watermarks.items(), key=lambda kv: kv[0])
        }
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _records_from_table(table: pa.Table) -> list[dict[str, Any]]:
    """Convert a BITMEX_FUNDING_SCHEMA table into normalized record dicts."""
    rows = table.to_pylist()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "timestamp": r["timestamp"],
                "timestamp_us": int(r["timestamp_us"]),
                "symbol": str(r["symbol"]).upper(),
                "funding_rate": float(r["funding_rate"]),
                "funding_rate_daily": float(r["funding_rate_daily"]),
                "funding_interval": str(r.get("funding_interval") or ""),
                "source": str(r.get("source") or "bitmex_funding"),
                "availability_time": int(r["availability_time"]),
            }
        )
    return out


def load_prior_staged_records(stage_parquet: Path) -> list[dict[str, Any]]:
    """Load previously staged full funding table, if present."""
    if not stage_parquet.exists():
        return []
    try:
        table = pq.read_table(stage_parquet)
    except (OSError, pa.ArrowInvalid):
        return []
    for col in ("timestamp_us", "symbol", "funding_rate"):
        if col not in table.column_names:
            return []
    return _records_from_table(table)


def merge_funding_records(
    prior: list[dict[str, Any]],
    new: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate by (symbol, timestamp_us); prefer newer fetch on collision."""
    merged: dict[tuple[str, int], dict[str, Any]] = {}
    for r in prior:
        key = (str(r["symbol"]).upper(), int(r["timestamp_us"]))
        merged[key] = r
    for r in new:
        key = (str(r["symbol"]).upper(), int(r["timestamp_us"]))
        merged[key] = r
    return [merged[k] for k in sorted(merged.keys())]


def per_symbol_stats(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build record count and date span per symbol from the full merged table."""
    by_sym: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_sym.setdefault(str(r["symbol"]).upper(), []).append(r)
    rows: list[dict[str, Any]] = []
    for sym in sorted(by_sym.keys()):
        ordered = sorted(by_sym[sym], key=lambda x: int(x["timestamp_us"]))
        rows.append(
            {
                "symbol": sym,
                "record_count": len(ordered),
                "first_timestamp": ordered[0]["timestamp"],
                "last_timestamp": ordered[-1]["timestamp"],
            }
        )
    return rows


def coverage_from_timestamp_us(
    records: list[dict[str, Any]],
    *,
    default_start: datetime,
    default_end: datetime,
) -> tuple[datetime, datetime]:
    """Coverage bounds from integer timestamp_us (no ISO re-parse)."""
    if not records:
        return default_start, default_end
    min_us = min(int(r["timestamp_us"]) for r in records)
    max_us = max(int(r["timestamp_us"]) for r in records)
    return (
        datetime.fromtimestamp(min_us / _US_PER_SECOND, tz=UTC),
        datetime.fromtimestamp(max_us / _US_PER_SECOND, tz=UTC),
    )


def generate_mock_funding(symbol: str, count: int = 100) -> list[dict[str, Any]]:
    """Generate mocked BitMEX funding records for dry-run testing."""
    t0 = datetime(2016, 5, 13, tzinfo=UTC)
    records: list[dict[str, Any]] = []
    for i in range(count):
        ts = t0 + timedelta(hours=8 * i)
        records.append(
            {
                "timestamp": ts.isoformat().replace("+00:00", "Z"),
                "symbol": symbol,
                "fundingRate": 0.0001 * (i % 5 - 2),
                "fundingRateDaily": 0.0003 * (i % 5 - 2),
                "fundingInterval": "2000-01-01T08:00:00.000Z",
            }
        )
    return records


def generate_mock_instruments() -> list[dict[str, Any]]:
    """Generate mocked instruments for dry-run (Open + Settled perps)."""
    return [
        {"symbol": "XBTUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "ETHUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "XRPUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "LTCUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "SOLUSDT", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "LEGACYUSD", "typ": "FFWCSX", "state": "Settled"},
        {"symbol": "SPYUSD", "typ": "FFCCSX", "state": "Open"},  # not a perp
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-009 BitMEX full funding backfill")
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbols; if omitted, discover full perp universe",
    )
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--start-time", type=str, default=DEFAULT_START_TIME)
    parser.add_argument("--end-time", type=str, default=None)
    parser.add_argument("--watermark-path", type=str, default=str(WATERMARK_PATH))
    parser.add_argument(
        "--report-path",
        type=str,
        default=None,
        help=(
            f"Report JSON path (default: {REPORT_PATH} for real runs; "
            "tmpdir under dry-run so acceptance artifact is never clobbered)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Synthetic mocked BitMEX responses; does not write acceptance report",
    )
    parser.add_argument("--rate-per-minute", type=int, default=120)
    parser.add_argument(
        "--open-only",
        action="store_true",
        default=False,
        help="Discover only Open perps via /instrument/active (legacy DATA-006 style)",
    )
    parser.add_argument(
        "--code-commit",
        type=str,
        default=None,
        help="40-char git SHA for CodeIdentity (default: git rev-parse HEAD)",
    )
    args = parser.parse_args()

    start_time = _parse_iso(args.start_time)
    end_time = _parse_iso(args.end_time) if args.end_time else datetime.now(UTC)

    tmpdir: tempfile.TemporaryDirectory[str] | None = None
    try:
        if args.dry_run:
            print(
                "DATA-009 BitMEX: DRY-RUN mode with mocked responses",
                file=sys.stderr,
            )
            tmpdir = tempfile.TemporaryDirectory()
            db_path = Path(tmpdir.name) / "exp003.db"
            store_root = Path(tmpdir.name) / "exp003_store"
            watermark_path = Path(tmpdir.name) / "watermarks.json"
            # Never write synthetic output to the real acceptance report path.
            if args.report_path is None:
                report_path = Path(tmpdir.name) / REPORT_PATH.name
            else:
                report_path = Path(args.report_path)
                try:
                    if report_path.resolve() == REPORT_PATH.resolve():
                        print(
                            "WARNING: dry-run refuses to overwrite acceptance report "
                            f"{REPORT_PATH}; redirecting to tmpdir",
                            file=sys.stderr,
                        )
                        report_path = Path(tmpdir.name) / REPORT_PATH.name
                except OSError:
                    report_path = Path(tmpdir.name) / REPORT_PATH.name
            data_mode = "synthetic"

            def mock_handler(request: httpx.Request) -> httpx.Response:
                url = str(request.url)
                if "/instrument/active" in url or "/instrument" in url:
                    return httpx.Response(200, json=generate_mock_instruments())
                for sym in [
                    "XBTUSD",
                    "ETHUSD",
                    "XRPUSD",
                    "LTCUSD",
                    "SOLUSDT",
                    "LEGACYUSD",
                ]:
                    if f"symbol={sym}" in url or f"symbol={sym}&" in url or sym in url:
                        return httpx.Response(200, json=generate_mock_funding(sym))
                return httpx.Response(200, json=[])

            client = BitMEXFundingClient(
                client=httpx.Client(transport=httpx.MockTransport(mock_handler)),
                requests_per_minute=args.rate_per_minute,
            )
        else:
            db_path = Path(args.db_path)
            store_root = Path(args.store_root)
            watermark_path = Path(args.watermark_path)
            report_path = Path(args.report_path) if args.report_path else REPORT_PATH
            data_mode = "real_asof"
            client = BitMEXFundingClient(requests_per_minute=args.rate_per_minute)

        try:
            code_commit = resolve_code_commit(args.code_commit)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

        db_path.parent.mkdir(parents=True, exist_ok=True)
        store_root.mkdir(parents=True, exist_ok=True)
        apply_migrations(db_path)

        # Discover or use provided symbol universe.
        if args.symbols:
            symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        else:
            try:
                if args.open_only:
                    symbols = client.fetch_perp_symbols(state="Open", active_only=True)
                else:
                    # DATA-009: all FFWCSX states (Open + Settled/historical).
                    symbols = client.fetch_perp_symbols(state=None, active_only=False)
                print(
                    f"DATA-009: discovered {len(symbols)} perpetual symbols "
                    f"(open_only={args.open_only})",
                    file=sys.stderr,
                )
            except Exception as exc:
                print(f"ERROR discovering symbols: {exc}", file=sys.stderr)
                return 1

        if not symbols:
            print("No symbols to backfill", file=sys.stderr)
            return 1

        prior_watermarks = load_watermarks(watermark_path)
        # Full watermark map: start from prior, update only successful fetches.
        watermark_dt_map: dict[str, datetime] = {}
        for sym, iso in prior_watermarks.items():
            try:
                watermark_dt_map[sym.upper()] = _parse_iso(iso)
            except (TypeError, ValueError):
                continue

        new_records: list[dict[str, Any]] = []
        fetch_rows: list[dict[str, Any]] = []
        symbols_added: list[str] = []
        symbols_skipped_current: list[str] = []
        symbols_empty: list[str] = []
        fetch_errors: list[dict[str, Any]] = []

        for symbol in symbols:
            symbol_start = start_time
            prior_wm = watermark_dt_map.get(symbol)
            watermark_str = prior_wm.isoformat() if prior_wm is not None else None
            if prior_wm is not None:
                symbol_start = prior_wm + timedelta(hours=8)
                if symbol_start >= end_time:
                    print(f"Skipping {symbol}: up to watermark", file=sys.stderr)
                    symbols_skipped_current.append(symbol)
                    continue

            try:
                records = client.fetch_funding(
                    symbol, start_time=symbol_start, end_time=end_time
                )
                if not records:
                    print(f"No funding records for {symbol}", file=sys.stderr)
                    symbols_empty.append(symbol)
                    continue
                new_records.extend(records)
                last_ts = _parse_iso(records[-1]["timestamp"])
                watermark_dt_map[symbol] = last_ts
                if prior_wm is None:
                    symbols_added.append(symbol)
                fetch_rows.append(
                    {
                        "symbol": symbol,
                        "record_count": len(records),
                        "first_timestamp": records[0]["timestamp"],
                        "last_timestamp": records[-1]["timestamp"],
                        "watermark": last_ts.isoformat(),
                        "resumed_from": watermark_str,
                    }
                )
                print(
                    f"Fetched {len(records)} funding records for {symbol}",
                    file=sys.stderr,
                )
            except Exception as exc:
                note = str(exc)
                print(f"ERROR fetching {symbol}: {note}", file=sys.stderr)
                fetch_errors.append(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "symbol": symbol,
                        "note": note,
                    }
                )
                # Preserve prior watermark for failed symbols (do not drop).

        # Keep rate-limit incidents pure (HTTP 429 only); fetch errors separate.
        rate_limit_incidents = list(client.rate_limit_incidents)

        stage_dir = store_root / STAGE_REL
        stage_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = stage_dir / PARQUET_NAME

        prior_records = load_prior_staged_records(parquet_path)
        merged_records = merge_funding_records(prior_records, new_records)

        if not merged_records:
            print(
                "No funding records available (neither prior staged nor new fetch); "
                "cannot publish dataset",
                file=sys.stderr,
            )
            # Still persist watermarks so partial progress is not lost.
            if watermark_dt_map:
                save_watermarks(watermark_path, watermark_dt_map)
            return 1

        save_watermarks(watermark_path, watermark_dt_map)

        table = build_funding_table(merged_records)
        if table.schema != BITMEX_FUNDING_SCHEMA:
            table = table.cast(BITMEX_FUNDING_SCHEMA)
        pq.write_table(table, parquet_path)

        row_count = table.num_rows
        relative_path = "bitmex/funding_full/funding.parquet"
        output_sources = {relative_path: parquet_path}
        sha256, byte_size = stream_sha256_and_size(parquet_path)
        output_specs = [
            OutputFileSpec(
                relative_path=relative_path,
                sha256=sha256,
                rows=row_count,
                bytes=byte_size,
                partition={"source": "bitmex", "kind": "funding_full"},
            )
        ]

        coverage_start, coverage_end = coverage_from_timestamp_us(
            merged_records,
            default_start=start_time,
            default_end=end_time,
        )

        symbol_rows = per_symbol_stats(merged_records)
        backfilled_symbols = [r["symbol"] for r in symbol_rows]

        cfg_payload = {
            "ticket": "DATA-009",
            "dataset_type": DATASET_TYPE,
            "transform": "bitmex_funding_full_backfill",
            "transform_version": "1",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "rate_per_minute": args.rate_per_minute,
            "open_only": bool(args.open_only),
            "symbols_arg": args.symbols,
            "discovered_symbol_count": len(symbols),
            "data_mode": data_mode,
        }
        config_digest = config_sha256_for_run(cfg_payload)

        plan = PublishPlan(
            dataset_type=DATASET_TYPE,
            schema=SchemaIdentity(
                name="bitmex_funding", version="1", fingerprint="fund_v1"
            ),
            transform=TransformSpec(name="bitmex_funding_full_backfill", version="1"),
            code=CodeIdentity(commit=code_commit),
            config=ConfigIdentity(config_sha256=config_digest),
            dependencies=(),
            output_sources=output_sources,
            output_specs=output_specs,
            statistics=DatasetStatistics(row_count=row_count, byte_size=byte_size),
            coverage=CoverageWindow(
                event_start=coverage_start,
                event_end=coverage_end,
            ),
            quality_status=QualityStatus.PASS,
            quality_summary={
                "record_count": row_count,
                "symbol_count": len(backfilled_symbols),
                "symbols_backfilled": backfilled_symbols,
                "symbols_added": symbols_added,
                "new_record_count": len(new_records),
                "rate_limit_incidents": len(rate_limit_incidents),
                "fetch_errors": len(fetch_errors),
            },
            row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
            # Independent re-count of the written parquet (must read path).
            row_counters={relative_path: count_parquet_rows},
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

        print(
            f"BitMEX full funding dataset published: {result.dataset_id}",
            file=sys.stderr,
        )

        report = {
            "experiment_id": "DATA-009-BITMEX-FULL-BACKFILL",
            "data_mode": data_mode,
            "real_asof": (
                datetime.now(UTC).isoformat() if data_mode == "real_asof" else None
            ),
            "code_commit": code_commit,
            "config_sha256": config_digest,
            "symbols": symbols,
            "symbols_added": symbols_added,
            "symbols_backfilled": backfilled_symbols,
            "symbols_skipped": [
                s for s in symbols if s not in set(backfilled_symbols)
            ],
            "symbols_skipped_current": symbols_skipped_current,
            "symbols_empty": symbols_empty,
            "dataset_id": result.dataset_id,
            "dataset_type": DATASET_TYPE,
            "catalog_reconciliation": {
                "report_pinned_dataset_id": result.dataset_id,
                "resolve_latest_by_type": resolved_latest,
                "match": result.dataset_id == resolved_latest,
            },
            "quality_status": result.manifest.quality_status.value,
            "row_count": row_count,
            "byte_size": byte_size,
            "new_record_count": len(new_records),
            "prior_record_count": len(prior_records),
            "symbol_rows": symbol_rows,
            "fetch_rows": fetch_rows,
            "date_span": {
                "start": coverage_start.isoformat(),
                "end": coverage_end.isoformat(),
            },
            "coverage": {
                "start": coverage_start.isoformat(),
                "end": coverage_end.isoformat(),
            },
            "rate_limit_incidents": rate_limit_incidents,
            "fetch_errors": fetch_errors,
            "watermarks": {
                sym: dt.isoformat() for sym, dt in sorted(watermark_dt_map.items())
            },
            "live_eligible": False,
            "scope": (
                "all BitMEX perpetuals (Open + Settled/historical FFWCSX) from "
                "2016-05-13 (or symbol inception) to present; 8-hour funding; "
                "separate dataset type from DATA-006 bitmex_funding"
            ),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report written to {report_path}", file=sys.stderr)

        return 0
    finally:
        if tmpdir is not None:
            tmpdir.cleanup()


if __name__ == "__main__":
    sys.exit(main())
