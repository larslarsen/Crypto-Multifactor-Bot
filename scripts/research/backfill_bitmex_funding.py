#!/usr/bin/env python3
"""DATA-009 — BitMEX historical funding rate backfill.

Discovers BitMEX perpetual symbols and publishes ``bitmex_funding_full``.
Resume starts at the last retained event, inclusive, and deduplicates overlap.
A saved watermark is not coverage. Retained stage and watermark files are
replaced only after catalog publication succeeds.

Default invocation is a real backfill. ``--dry-run`` is synthetic and isolated
from production paths.

No LIVE. No price or trade data. No other CEXes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    BitMEXFundingClient,
    BitMEXFundingError,
    build_funding_table,
    collapse_funding_observations,
    event_datetime_to_us,
    require_exact_microsecond_timestamp,
    us_to_event_datetime,
    validate_funding_history,
)

DATASET_TYPE = "bitmex_funding_full"
FUNDING_SCHEMA_NAME = "bitmex_funding"
FUNDING_SCHEMA_VERSION = "1"
FUNDING_SCHEMA_FINGERPRINT = "fund_v1"
FUNDING_TRANSFORM_NAME = "bitmex_funding_full_backfill"
FUNDING_TRANSFORM_VERSION = "1"
DEFAULT_START = datetime(2016, 5, 13, tzinfo=UTC)
STAGE_REL = Path("staged") / "bitmex_funding_full"
PARQUET_NAME = "funding.parquet"
REL_PATH = "bitmex/funding_full/funding.parquet"
WATERMARK_PATH = Path("data/bitmex_funding_full_watermarks.json")
DB_PATH = Path("exp003.db")
STORE_ROOT = Path("data/exp003_store")
REPORT_PATH = Path("research/sprint_004/39_BITMEX_FULL_BACKFILL.json")
PRODUCTION_REPORT = (
    Path(__file__).resolve().parents[2] / "research" / "sprint_004" / "39_BITMEX_FULL_BACKFILL.json"
)
_US_PER_SECOND = 1_000_000


class CatalogFollowupError(Exception):
    """Catalog registration succeeded and a later catalog read or close failed."""

    def __init__(self, dataset_id: str, original: BaseException) -> None:
        super().__init__(f"{type(original).__name__}: {original}")
        self.dataset_id = dataset_id
        self.original = original


def config_sha256_for_run(payload: dict[str, Any]) -> str:
    """Deterministic SHA-256 of the run configuration, not of the code commit."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def run_config_payload(
    args: argparse.Namespace,
    *,
    symbol_count: int,
    data_mode: str,
) -> dict[str, Any]:
    return {
        "ticket": "DATA-009",
        "dataset_type": DATASET_TYPE,
        "transform": FUNDING_TRANSFORM_NAME,
        "transform_version": FUNDING_TRANSFORM_VERSION,
        "start_time": args.start_time.isoformat(),
        "end_time": args.end_time.isoformat(),
        "rate_per_minute": args.rate_per_minute,
        "open_only": bool(args.open_only),
        "symbols_arg": args.symbols,
        "discovered_symbol_count": symbol_count,
        "data_mode": data_mode,
    }


def publication_blockers(
    *,
    fetch_errors: list[dict[str, Any]],
    symbols_empty: list[str],
    missing_requested: list[str],
    missing_in_window: list[str] | None = None,
) -> list[str]:
    """Reasons that must prevent catalog publication."""
    blockers: list[str] = []
    if fetch_errors:
        blockers.append("fetch_errors")
    if symbols_empty:
        blockers.append("empty_requested_symbols")
    if missing_requested:
        blockers.append("incomplete_requested_coverage")
    if missing_in_window:
        blockers.append("missing_in_window_coverage")
    return blockers


def unique_symbols(symbols: list[str]) -> list[str]:
    """Keep the first occurrence of each symbol. Distinct symbols stay."""
    seen: set[str] = set()
    ordered: list[str] = []
    for symbol in symbols:
        if symbol in seen:
            continue
        seen.add(symbol)
        ordered.append(symbol)
    return ordered


def missing_requested_symbols(
    requested: list[str],
    records: list[dict[str, Any]],
) -> list[str]:
    """Requested symbols absent from retained rows. A watermark is not a row."""
    present = {str(record["symbol"]) for record in records}
    return [symbol for symbol in requested if symbol not in present]


def symbols_missing_in_window(
    requested: list[str],
    records: list[dict[str, Any]],
    *,
    requested_start: datetime,
    requested_end: datetime,
) -> list[str]:
    """Requested symbols with no observation inside the inclusive window.

    One in-window observation is enough. This does not infer an 8-hour cadence.
    """
    start_us = event_datetime_to_us(requested_start)
    end_us = event_datetime_to_us(requested_end)
    covered: set[str] = set()
    for record in records:
        timestamp_us = int(record["timestamp_us"])
        if start_us <= timestamp_us <= end_us:
            covered.add(str(record["symbol"]).upper())
    return [symbol for symbol in requested if symbol.upper() not in covered]


def inclusive_resume_start(
    *,
    requested_start: datetime,
    requested_end: datetime,
    watermark: datetime | None,
) -> datetime | None:
    """Inclusive fetch start. None means the watermark already reaches the end.

    The next request begins at the last known event, not one funding interval
    after it. Explicit requested bounds still apply.
    """
    if event_datetime_to_us(requested_start) > event_datetime_to_us(requested_end):
        raise BitMEXFundingError(
            "requested start is after requested end",
            context={"start": requested_start.isoformat(), "end": requested_end.isoformat()},
        )
    if watermark is None:
        return requested_start
    watermark_us = event_datetime_to_us(watermark)
    if watermark_us >= event_datetime_to_us(requested_end):
        return None
    if watermark_us < event_datetime_to_us(requested_start):
        return requested_start
    return watermark


def _parse_iso(value: str) -> datetime:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def parse_strict_watermark(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise BitMEXFundingError(
            "unsupported funding watermark",
            context={"value": value},
        )
    raw = require_exact_microsecond_timestamp(value.strip())
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise BitMEXFundingError(
            "unsupported funding watermark",
            context={"value": value},
        ) from exc
    if parsed.tzinfo is None:
        raise BitMEXFundingError(
            "unsupported funding watermark",
            context={"value": value},
        )
    return parsed.astimezone(UTC)


def resolve_code_commit(explicit: str | None) -> str:
    if explicit:
        if not re.fullmatch(r"[0-9a-f]{40}", explicit):
            raise ValueError("code commit must be a 40-char hex sha")
        return explicit
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError(f"unexpected git sha: {sha}")
    return sha


def count_parquet_rows(path: Path | str) -> int:
    metadata = pq.read_metadata(Path(path))
    return int(metadata.num_rows)


def per_symbol_stats(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Record count and date span per symbol from the merged table."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(record["symbol"]).upper(), []).append(record)
    rows: list[dict[str, Any]] = []
    for symbol in sorted(grouped):
        items = sorted(grouped[symbol], key=lambda rec: int(rec["timestamp_us"]))
        rows.append(
            {
                "symbol": symbol,
                "record_count": len(items),
                "first_timestamp": items[0]["timestamp"],
                "last_timestamp": items[-1]["timestamp"],
            }
        )
    return rows


def load_watermarks(path: Path) -> dict[str, str]:
    """Load watermarks. A missing file is empty. A damaged file fails closed."""
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise BitMEXFundingError(
            "unreadable funding watermark file",
            context={"path": str(path)},
        ) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BitMEXFundingError(
            "malformed funding watermark file",
            context={"path": str(path)},
        ) from exc
    if not isinstance(data, dict) or "watermarks" not in data or not isinstance(data["watermarks"], dict):
        raise BitMEXFundingError(
            "malformed funding watermark file",
            context={"path": str(path)},
        )
    loaded: dict[str, str] = {}
    for key, value in data["watermarks"].items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise BitMEXFundingError(
                "malformed funding watermark file",
                context={"path": str(path), "key": key},
            )
        symbol = key.strip().upper()
        stamp = value.strip()
        if not symbol or not stamp:
            raise BitMEXFundingError(
                "malformed funding watermark file",
                context={"path": str(path), "key": key},
            )
        if symbol in loaded and loaded[symbol] != stamp:
            raise BitMEXFundingError(
                "conflicting funding watermarks",
                context={"symbol": symbol},
            )
        loaded[symbol] = stamp
    return loaded


def _records_from_table(table: pa.Table) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in table.to_pylist():
        records.append(
            {
                "timestamp": row["timestamp"],
                "timestamp_us": row["timestamp_us"],
                "symbol": row["symbol"],
                "funding_rate": row["funding_rate"],
                "funding_rate_daily": row["funding_rate_daily"],
                "funding_interval": row["funding_interval"],
                "source": row["source"],
                "availability_time": row["availability_time"],
            }
        )
    return records


def load_prior_staged_records(stage_parquet: Path) -> list[dict[str, Any]]:
    """Load a validated retained stage. Damaged bytes are not an empty history."""
    if not stage_parquet.exists():
        return []
    try:
        table = pq.read_table(stage_parquet)
    except (OSError, pa.ArrowInvalid) as exc:
        raise BitMEXFundingError(
            "retained funding stage is unreadable",
            context={"path": str(stage_parquet)},
        ) from exc
    validate_funding_history(table)
    return _records_from_table(table)


def validate_retained_resume_state(
    watermarks: dict[str, datetime],
    records: list[dict[str, Any]],
) -> None:
    """A watermark needs retained history and cannot be ahead of its last event."""
    max_us: dict[str, int] = {}
    for record in records:
        symbol = str(record["symbol"])
        timestamp_us = record["timestamp_us"]
        if isinstance(timestamp_us, bool) or not isinstance(timestamp_us, int):
            raise BitMEXFundingError(
                "retained funding history has a non-integer timestamp_us",
                context={"symbol": symbol},
            )
        prior = max_us.get(symbol)
        max_us[symbol] = timestamp_us if prior is None else max(prior, timestamp_us)
    if watermarks and not records:
        raise BitMEXFundingError(
            "saved watermark requires retained funding history; missing stage is not coverage"
        )
    for symbol, watermark in watermarks.items():
        if symbol not in max_us:
            raise BitMEXFundingError(
                "saved watermark is not coverage and has no retained history for symbol",
                context={"symbol": symbol},
            )
        watermark_us = event_datetime_to_us(watermark)
        if watermark_us > max_us[symbol]:
            raise BitMEXFundingError(
                "saved watermark is ahead of retained funding history",
                context={
                    "symbol": symbol,
                    "watermark_us": watermark_us,
                    "max_event_us": max_us[symbol],
                },
            )


def load_retained_funding_state(
    watermark_path: Path,
    stage_parquet: Path,
) -> tuple[dict[str, datetime], list[dict[str, Any]]]:
    parsed: dict[str, datetime] = {}
    for symbol, text in load_watermarks(watermark_path).items():
        parsed[symbol] = parse_strict_watermark(text)
    records = load_prior_staged_records(stage_parquet)
    validate_retained_resume_state(parsed, records)
    return parsed, records


def merge_funding_records(
    prior: list[dict[str, Any]],
    new: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Identical keys collapse. Conflicting overlap stops the publish."""
    return collapse_funding_observations([*prior, *new])


def save_watermarks(path: Path, watermarks: dict[str, datetime]) -> None:
    """Atomically replace the watermark file in its own directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "watermarks": {
            symbol: watermarks[symbol].isoformat()
            for symbol in sorted(watermarks)
        }
    }
    encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(
        prefix=".watermarks-",
        suffix=".partial",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def fsync_path(path: Path) -> None:
    """Fsync a file or directory before the next publication barrier."""
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def validate_candidate_parquet(path: Path, *, expected_rows: int) -> pa.Table:
    try:
        table = pq.read_table(path)
    except (OSError, pa.ArrowInvalid) as exc:
        raise BitMEXFundingError(
            "candidate parquet is unreadable",
            context={"path": str(path)},
        ) from exc
    validate_funding_history(table)
    if table.num_rows != expected_rows:
        raise BitMEXFundingError(
            "candidate parquet row count mismatch",
            context={"path": str(path), "rows": table.num_rows, "expected_rows": expected_rows},
        )
    return table


def write_candidate_parquet(stage_dir: Path, table: pa.Table) -> Path:
    """Write a same-directory sibling. Do not replace the retained stage."""
    stage_dir.mkdir(parents=True, exist_ok=True)
    candidate = stage_dir / f".{PARQUET_NAME}.partial"
    candidate.unlink(missing_ok=True)
    try:
        pq.write_table(table, candidate)
        validate_candidate_parquet(candidate, expected_rows=table.num_rows)
        fsync_path(candidate)
    except Exception:
        candidate.unlink(missing_ok=True)
        raise
    return candidate


def promote_candidate(candidate: Path, retained: Path) -> None:
    """Promote the candidate only after catalog registration."""
    if candidate.parent.resolve() != retained.parent.resolve():
        raise BitMEXFundingError(
            "funding candidate must be a same-directory sibling of the retained stage",
            context={"candidate": str(candidate), "retained": str(retained)},
        )
    os.replace(candidate, retained)


def write_json_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2).encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(
        prefix=".report-",
        suffix=".partial",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _is_production_report(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return True
    protected = {REPORT_PATH.resolve(), PRODUCTION_REPORT.resolve()}
    return resolved in protected


def _refuse(reasons: list[str], details: dict[str, Any]) -> int:
    print(
        "ERROR: refusing to publish BitMEX funding: "
        + ",".join(reasons)
        + f" details={details}",
        file=sys.stderr,
    )
    return 1


def _max_event_us(records: list[dict[str, Any]]) -> dict[str, int]:
    max_us: dict[str, int] = {}
    for record in records:
        symbol = str(record["symbol"])
        timestamp_us = int(record["timestamp_us"])
        prior = max_us.get(symbol)
        max_us[symbol] = timestamp_us if prior is None else max(prior, timestamp_us)
    return max_us


def publish_funding_plan(
    *,
    db_path: Path,
    store_root: Path,
    plan: PublishPlan,
) -> tuple[Any, str | None]:
    """Register the dataset. Resolver and close failures keep the published id."""
    config = DatasetStoreConfig(root=store_root)
    catalog = SqliteDatasetCatalog(db_path)
    try:
        publisher = DatasetPublisher(config, catalog)
        result = publisher.publish(plan, register_catalog=True)
    except Exception:
        try:
            catalog.close()
        except Exception:
            pass
        raise
    followup: Exception | None = None
    resolved_id: str | None = None
    try:
        resolved = catalog.resolve_latest_by_type(DATASET_TYPE)
        if resolved is not None and not isinstance(resolved, str):
            raise TypeError("resolve_latest_by_type must return a dataset id or None")
        resolved_id = resolved
    except Exception as exc:
        followup = exc
    try:
        catalog.close()
    except Exception as exc:
        followup = exc if followup is None else RuntimeError(f"{followup}; catalog close failed: {exc}")
    if followup is not None:
        raise CatalogFollowupError(result.dataset_id, followup)
    return result, resolved_id


def build_publish_plan(
    *,
    table: pa.Table,
    candidate: Path,
    merged_records: list[dict[str, Any]],
    code_commit: str,
    config_sha256: str,
    symbol_rows: list[dict[str, Any]],
    rate_limit_incidents: list[dict[str, Any]],
    symbols_added: list[str],
    new_record_count: int,
) -> PublishPlan:
    digest, byte_size = stream_sha256_and_size(candidate)
    min_us = min(int(record["timestamp_us"]) for record in merged_records)
    max_us = max(int(record["timestamp_us"]) for record in merged_records)
    backfilled = [row["symbol"] for row in symbol_rows]
    return PublishPlan(
        dataset_type=DATASET_TYPE,
        schema=SchemaIdentity(
            name=FUNDING_SCHEMA_NAME,
            version=FUNDING_SCHEMA_VERSION,
            fingerprint=FUNDING_SCHEMA_FINGERPRINT,
        ),
        transform=TransformSpec(
            name=FUNDING_TRANSFORM_NAME,
            version=FUNDING_TRANSFORM_VERSION,
        ),
        code=CodeIdentity(commit=code_commit),
        config=ConfigIdentity(config_sha256=config_sha256),
        dependencies=(),
        output_sources={REL_PATH: candidate},
        output_specs=(
            OutputFileSpec(
                relative_path=REL_PATH,
                sha256=digest,
                rows=table.num_rows,
                bytes=byte_size,
                partition={"source": "bitmex", "kind": "funding_full"},
            ),
        ),
        statistics=DatasetStatistics(row_count=table.num_rows, byte_size=byte_size),
        coverage=CoverageWindow(
            event_start=us_to_event_datetime(min_us),
            event_end=us_to_event_datetime(max_us),
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={
            "record_count": table.num_rows,
            "symbol_count": len(backfilled),
            "symbols_backfilled": backfilled,
            "symbols_added": symbols_added,
            "new_record_count": new_record_count,
            "rate_limit_incidents": len(rate_limit_incidents),
            "fetch_errors": 0,
        },
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters={REL_PATH: count_parquet_rows},
        created_at=datetime.now(UTC),
    )


def _run_backfill(
    args: argparse.Namespace,
    *,
    db_path: Path,
    store_root: Path,
    watermark_path: Path,
    report_path: Path,
    stage_parquet: Path,
) -> int:
    code_commit = resolve_code_commit(args.code_commit)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store_root.mkdir(parents=True, exist_ok=True)
    apply_migrations(db_path)

    data_mode = "synthetic" if args.dry_run else "real_asof"
    client = BitMEXFundingClient(requests_per_minute=args.rate_per_minute)
    if args.dry_run:
        client = BitMEXFundingClient(
            client=httpx.Client(transport=httpx.MockTransport(mock_handler)),
            requests_per_minute=args.rate_per_minute,
        )

    try:
        prior_watermarks, prior_records = load_retained_funding_state(
            watermark_path,
            stage_parquet,
        )
    except BitMEXFundingError as exc:
        print(f"ERROR: retained BitMEX funding state is not usable: {exc}", file=sys.stderr)
        return 1

    prior_symbols = sorted({str(record["symbol"]) for record in prior_records})
    if args.symbols:
        symbols = unique_symbols(
            [part.strip().upper() for part in args.symbols.split(",") if part.strip()]
        )
    else:
        try:
            if args.open_only:
                discovered = client.fetch_perp_symbols()
            else:
                discovered = client.fetch_perp_symbols(state=None, active_only=False)
            symbols = unique_symbols(discovered)
        except Exception as exc:
            print(f"ERROR: symbol discovery failed: {exc}", file=sys.stderr)
            return 1
    if not symbols:
        print("ERROR: no BitMEX perpetual symbols discovered", file=sys.stderr)
        return 1

    new_records: list[dict[str, Any]] = []
    fetch_errors: list[dict[str, Any]] = []
    symbols_empty: list[str] = []
    symbols_skipped_current: list[str] = []
    fetch_rows: list[dict[str, Any]] = []
    fetched_symbols: list[str] = []
    symbols_added: list[str] = []
    prior_symbol_set = set(prior_symbols)

    for symbol in symbols:
        fetch_start = inclusive_resume_start(
            requested_start=args.start_time,
            requested_end=args.end_time,
            watermark=prior_watermarks.get(symbol),
        )
        if fetch_start is None:
            symbols_skipped_current.append(symbol)
            continue
        try:
            records = client.fetch_funding(
                symbol,
                start_time=fetch_start,
                end_time=args.end_time,
                count=args.page_count,
            )
        except Exception as exc:
            fetch_errors.append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "symbol": symbol,
                    "note": str(exc),
                }
            )
            continue
        if not records:
            symbols_empty.append(symbol)
            continue
        new_records.extend(records)
        fetched_symbols.append(symbol)
        if symbol not in prior_symbol_set:
            symbols_added.append(symbol)
        ordered = sorted(records, key=lambda rec: int(rec["timestamp_us"]))
        resumed = prior_watermarks.get(symbol)
        last_event = us_to_event_datetime(int(ordered[-1]["timestamp_us"]))
        fetch_rows.append(
            {
                "symbol": symbol,
                "record_count": len(ordered),
                "first_timestamp": ordered[0]["timestamp"],
                "last_timestamp": ordered[-1]["timestamp"],
                "watermark": last_event.isoformat(),
                "resumed_from": None if resumed is None else resumed.isoformat(),
            }
        )

    early = publication_blockers(
        fetch_errors=fetch_errors,
        symbols_empty=symbols_empty,
        missing_requested=[],
    )
    if early:
        return _refuse(
            early,
            {
                "fetch_errors": fetch_errors,
                "symbols_empty": symbols_empty,
                "symbols_skipped_current": symbols_skipped_current,
            },
        )

    try:
        merged_records = merge_funding_records(prior_records, new_records)
        if not merged_records:
            raise BitMEXFundingError("cannot accept empty funding history")
        table = build_funding_table(merged_records)
    except BitMEXFundingError as exc:
        print(f"ERROR: refusing to publish invalid funding evidence: {exc}", file=sys.stderr)
        return 1

    symbol_rows = per_symbol_stats(merged_records)
    missing = missing_requested_symbols(symbols, merged_records)
    missing_window = symbols_missing_in_window(
        symbols,
        merged_records,
        requested_start=args.start_time,
        requested_end=args.end_time,
    )
    coverage_blockers = publication_blockers(
        fetch_errors=[],
        symbols_empty=[],
        missing_requested=missing,
        missing_in_window=missing_window,
    )
    if coverage_blockers:
        return _refuse(
            coverage_blockers,
            {
                "missing_requested": missing,
                "missing_in_window": missing_window,
                "symbols_skipped_current": symbols_skipped_current,
            },
        )

    try:
        candidate = write_candidate_parquet(stage_parquet.parent, table)
    except BitMEXFundingError as exc:
        print(f"ERROR: refusing to publish invalid funding candidate: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(
            "ERROR: funding candidate durability failed before catalog registration: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    max_us = _max_event_us(merged_records)
    proposed_watermarks = dict(prior_watermarks)
    for symbol in fetched_symbols:
        if symbol not in max_us:
            candidate.unlink(missing_ok=True)
            print(
                f"ERROR: fetched symbol {symbol} is missing from validated funding history",
                file=sys.stderr,
            )
            return 1
        proposed_watermarks[symbol] = us_to_event_datetime(max_us[symbol])

    config_sha256 = config_sha256_for_run(
        run_config_payload(args, symbol_count=len(symbols), data_mode=data_mode)
    )
    plan = build_publish_plan(
        table=table,
        candidate=candidate,
        merged_records=merged_records,
        code_commit=code_commit,
        config_sha256=config_sha256,
        symbol_rows=symbol_rows,
        rate_limit_incidents=client.rate_limit_incidents,
        symbols_added=symbols_added,
        new_record_count=len(new_records),
    )
    try:
        result, resolved_id = publish_funding_plan(
            db_path=db_path,
            store_root=store_root,
            plan=plan,
        )
    except CatalogFollowupError as exc:
        print(
            "ERROR: catalog publication succeeded "
            f"dataset_id={exc.dataset_id} but retained persistence failed: {exc}. "
            "no rollback was performed",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        candidate.unlink(missing_ok=True)
        print(
            "ERROR: funding publication failed before catalog registration: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    row_count = table.num_rows
    coverage_start = us_to_event_datetime(min(int(record["timestamp_us"]) for record in merged_records))
    coverage_end = us_to_event_datetime(max(int(record["timestamp_us"]) for record in merged_records))
    try:
        promote_candidate(candidate, stage_parquet)
        fsync_path(stage_parquet.parent)
        save_watermarks(watermark_path, proposed_watermarks)
        fsync_path(watermark_path.parent)
        backfilled_symbols = [row["symbol"] for row in symbol_rows]
        report = {
            "experiment_id": "DATA-009-BITMEX-FULL-BACKFILL",
            "data_mode": data_mode,
            "real_asof": None if data_mode == "synthetic" else datetime.now(UTC).isoformat(),
            "code_commit": code_commit,
            "config_sha256": config_sha256,
            "symbols": symbols,
            "symbols_added": symbols_added,
            "symbols_backfilled": backfilled_symbols,
            "symbols_skipped": [symbol for symbol in symbols if symbol not in set(backfilled_symbols)],
            "symbols_skipped_current": symbols_skipped_current,
            "symbols_empty": symbols_empty,
            "dataset_id": result.dataset_id,
            "dataset_type": DATASET_TYPE,
            "catalog_reconciliation": {
                "report_pinned_dataset_id": result.dataset_id,
                "resolve_latest_by_type": resolved_id,
                "match": result.dataset_id == resolved_id,
            },
            "quality_status": result.manifest.quality_status.value,
            "row_count": row_count,
            "byte_size": plan.statistics.byte_size,
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
            "rate_limit_incidents": client.rate_limit_incidents,
            "fetch_errors": fetch_errors,
            "watermarks": {
                symbol: moment.isoformat()
                for symbol, moment in sorted(proposed_watermarks.items())
            },
            "live_eligible": False,
            "scope": (
                "BitMEX perpetuals with source-supplied funding intervals; "
                "resume is inclusive at the last retained event"
            ),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        write_json_report(report_path, report)
    except Exception as exc:
        print(
            "ERROR: catalog publication succeeded "
            f"dataset_id={result.dataset_id} but retained persistence failed: {exc}. "
            "no rollback was performed",
            file=sys.stderr,
        )
        return 1

    print(
        f"BitMEX full funding dataset published: {result.dataset_id} "
        f"rows={row_count} symbols={len(symbol_rows)} "
        f"prior={len(prior_records)} new={len(new_records)} mode={data_mode}",
        file=sys.stderr,
    )
    print(f"Report written to {report_path}", file=sys.stderr)
    return 0


def generate_mock_instruments() -> list[dict[str, Any]]:
    return [
        {"symbol": "XBTUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "ETHUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "XRPUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "LTCUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "SOLUSDT", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "LEGACYUSD", "typ": "FFWCSX", "state": "Settled"},
        {"symbol": "SPYUSD", "typ": "FFCCSX", "state": "Open"},
    ]


def generate_mock_funding(symbol: str, count: int = 100) -> list[dict[str, Any]]:
    """Synthetic rows. The 8-hour clock is sample spacing, not a resume rule.

    ``fundingRateDaily`` is a supplied value and is not derived from the rate.
    """
    t0 = datetime(2016, 5, 13, tzinfo=UTC)
    records: list[dict[str, Any]] = []
    for i in range(count):
        ts = t0 + timedelta(hours=8 * i)
        rate = 0.0001 * ((i % 5) - 2)
        records.append(
            {
                "timestamp": ts.isoformat().replace("+00:00", "Z"),
                "symbol": symbol,
                "fundingRate": rate,
                "fundingRateDaily": 0.0005,
                "fundingInterval": "2000-01-01T08:00:00.000Z",
            }
        )
    return records


def mock_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "/instrument" in url:
        return httpx.Response(200, json=generate_mock_instruments())
    for symbol in (item["symbol"] for item in generate_mock_instruments()):
        if f"symbol={symbol}" in url:
            return httpx.Response(200, json=generate_mock_funding(symbol, 100))
    return httpx.Response(404, json={"error": "not found"})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    parser.add_argument("--store-root", type=Path, default=STORE_ROOT)
    parser.add_argument("--watermark-path", type=Path, default=WATERMARK_PATH)
    parser.add_argument("--report-path", type=Path, default=None)
    parser.add_argument("--start-time", type=_parse_iso, default=DEFAULT_START.isoformat())
    parser.add_argument("--end-time", type=_parse_iso, default=None)
    parser.add_argument("--symbols", default=None, help="Comma-separated override; default discovers all")
    parser.add_argument("--instrument-state", default=None, help="Exact instrument state filter; default all")
    parser.add_argument(
        "--open-only",
        action="store_true",
        help="Use /instrument/active and the Open state instead of full history",
    )
    parser.add_argument("--page-count", type=int, default=500)
    parser.add_argument("--rate-per-minute", type=int, default=120)
    parser.add_argument("--code-commit", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Synthetic isolated backfill. Does not call BitMEX or overwrite production paths.",
    )
    args = parser.parse_args(argv)
    if args.end_time is None:
        args.end_time = datetime.now(UTC)

    tmpdir: tempfile.TemporaryDirectory[str] | None = None
    try:
        if args.dry_run:
            tmpdir = tempfile.TemporaryDirectory(prefix="bitmex-funding-dry-run-")
            root = Path(tmpdir.name)
            db_path = root / "exp003.db"
            store_root = root / "store"
            watermark_path = root / "watermarks.json"
            stage_parquet = store_root / STAGE_REL / PARQUET_NAME
            if args.report_path is None or _is_production_report(Path(args.report_path)):
                report_path = root / REPORT_PATH.name
            else:
                report_path = Path(args.report_path)
            print(
                "DRY RUN: synthetic BitMEX funding backfill in an isolated temp store",
                file=sys.stderr,
            )
        else:
            db_path = Path(args.db_path)
            store_root = Path(args.store_root)
            watermark_path = Path(args.watermark_path)
            stage_parquet = store_root / STAGE_REL / PARQUET_NAME
            report_path = Path(args.report_path) if args.report_path is not None else REPORT_PATH

        return _run_backfill(
            args,
            db_path=db_path,
            store_root=store_root,
            watermark_path=watermark_path,
            report_path=report_path,
            stage_parquet=stage_parquet,
        )
    finally:
        if tmpdir is not None:
            tmpdir.cleanup()


if __name__ == "__main__":
    sys.exit(main())
