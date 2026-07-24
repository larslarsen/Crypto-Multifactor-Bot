"""Binance archive kline normalizer (BIN-001).

Consumes explicitly registered local RawObjects (ZIP/CSV kline archives).
No network, no filename inference for identity, no arbitrary discovery.
Explicit market_type, interval, venue_id, resolved instrument_id required.
Headerless support; timestamp unit inferred per row from data (ms/us).
Normalizes timestamps to signed UTC microseconds; validates inclusive close
semantics used by real Binance archives; surfaces dups/gaps/malformations
as typed QualityIssue without repairing, deduplicating, or filling.
Empty/header-only archives fail closed. Cross-object duplicate/gap assessment
runs on the complete multi-object sequence with per-object issue lineage.
Market-specific physical volume fields for spot/usdm vs coinm.
Stages per-raw source-specific bars.parquet + quality.parquet with raw lineage;
builds a MAN-001-publishable PublishPlan (REQUIRE_VERIFIER + row counters).
"""

from __future__ import annotations

import calendar
import csv
import decimal
import hashlib
import io
import json
import re
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.audit.models import IssueSeverity, QualityIssue
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetStatistics,
    DependencyKind,
    DependencyRef,
    OutputFileSpec,
    PublishPlan,
    QualityStatus,
    RowCountPolicy,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.contracts import RawObject
from cryptofactors.ingest.raw.paths import assert_regular_nonsymlink_file

# Public constants (small API surface)
BINANCE_KLINE_DATASET_TYPE = "binance_kline_source"
BINANCE_KLINE_SCHEMA_NAME = "binance_kline_source"
# v2: UTC-us fact times + source timestamp columns + market-physical volume fields
BINANCE_KLINE_SCHEMA_VERSION = "2"
BINANCE_KLINE_TRANSFORM_NAME = "binance_kline_normalizer"
BINANCE_KLINE_TRANSFORM_VERSION = "4"

_SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")

# Fixed Binance kline CSV schema (12 fields, headerless or first row data)
BINANCE_KLINE_FIELD_COUNT = 12
BINANCE_KLINE_FIELD_NAMES = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore",
)

# Case-sensitive fixed intervals (Binance uses 1m minute vs 1M month).
_FIXED_INTERVALS: dict[str, timedelta] = {
    "1s": timedelta(seconds=1),
    "1m": timedelta(minutes=1),
    "3m": timedelta(minutes=3),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "2h": timedelta(hours=2),
    "4h": timedelta(hours=4),
    "6h": timedelta(hours=6),
    "8h": timedelta(hours=8),
    "12h": timedelta(hours=12),
    "1d": timedelta(days=1),
    "3d": timedelta(days=3),
    "1w": timedelta(weeks=1),
}

# Calendar-month labels (never fixed 30-day). "1M" is Binance; "1mo" explicit alias.
_CALENDAR_MONTH_LABELS = frozenset({"1M", "1mo"})

# Explicit market types and volume field semantics (source-specific, not repaired).
_MARKET_TYPE_ALIASES: dict[str, str] = {
    "spot": "spot",
    "usdm": "usdm",
    "usd-m": "usdm",
    "usd_m": "usdm",
    "um": "usdm",
    "futures_um": "usdm",
    "futures-um": "usdm",
    "coinm": "coinm",
    "coin-m": "coinm",
    "coin_m": "coinm",
    "cm": "coinm",
    "futures_cm": "coinm",
    "futures-cm": "coinm",
}

# Physical volume semantics. spot/usdm share CSV meaning; coinm differs.
_MARKET_VOLUME_SEMANTICS: dict[str, dict[str, str]] = {
    "spot": {
        "volume_unit": "base_asset",
        "secondary_volume_unit": "quote_asset",
        "taker_buy_volume_unit": "base_asset",
        "taker_buy_secondary_volume_unit": "quote_asset",
        "schema_variant": "quote_notional",
    },
    "usdm": {
        "volume_unit": "base_asset",
        "secondary_volume_unit": "quote_asset",
        "taker_buy_volume_unit": "base_asset",
        "taker_buy_secondary_volume_unit": "quote_asset",
        "schema_variant": "quote_notional",
    },
    "coinm": {
        "volume_unit": "contracts",
        "secondary_volume_unit": "base_asset",
        "taker_buy_volume_unit": "contracts",
        "taker_buy_secondary_volume_unit": "base_asset",
        "schema_variant": "coin_margined",
    },
}


@dataclass(frozen=True, slots=True)
class BinanceKlineNormalizeResult:
    """Staged artifacts + constructed PublishPlan (not yet published)."""

    publish_plan: PublishPlan
    bar_paths: tuple[Path, ...]
    quality_paths: tuple[Path, ...]
    issues: tuple[QualityIssue, ...]


@dataclass(frozen=True, slots=True)
class _IntervalSpec:
    """Parsed interval: fixed UTC delta or calendar month."""

    label: str
    kind: str  # "fixed" | "calendar_month"
    delta: timedelta | None
    months: int = 0


@dataclass(frozen=True, slots=True)
class _MarketTypeSpec:
    canonical: str
    volume_unit: str
    secondary_volume_unit: str
    taker_buy_volume_unit: str
    taker_buy_secondary_volume_unit: str
    schema_variant: str


@dataclass
class _ObjectWork:
    """Per-raw-object staging before global gap/dup and quality write."""

    raw_object_id: str
    bar_path: Path
    quality_path: Path
    bar_rows: list[dict[str, Any]] = field(default_factory=list)
    issues: list[QualityIssue] = field(default_factory=list)
    obj_unit: str | None = None
    units_seen: set[str] = field(default_factory=set)


def _parse_interval(interval: str) -> _IntervalSpec:
    """Map Binance interval string. Case-sensitive: 1m != 1M.

    Calendar month (1M / 1mo) is never a fixed 30-day timedelta.
    """
    raw = interval.strip()
    if not raw:
        raise ValueError("unsupported interval: empty")
    if raw in _CALENDAR_MONTH_LABELS:
        return _IntervalSpec(label="1M", kind="calendar_month", delta=None, months=1)
    if raw in _FIXED_INTERVALS:
        return _IntervalSpec(label=raw, kind="fixed", delta=_FIXED_INTERVALS[raw], months=0)
    raise ValueError(f"unsupported interval: {interval!r}")


def _resolve_market_type(market_type: str) -> _MarketTypeSpec:
    """Validate and resolve spot / usdm / coinm volume semantics."""
    key = market_type.strip().lower()
    if not key or key not in _MARKET_TYPE_ALIASES:
        raise ValueError(
            "market_type must be one of spot, usdm, coinm "
            f"(aliases: usd-m, coin-m, um, cm); got {market_type!r}"
        )
    canonical = _MARKET_TYPE_ALIASES[key]
    sem = _MARKET_VOLUME_SEMANTICS[canonical]
    return _MarketTypeSpec(
        canonical=canonical,
        volume_unit=sem["volume_unit"],
        secondary_volume_unit=sem["secondary_volume_unit"],
        taker_buy_volume_unit=sem["taker_buy_volume_unit"],
        taker_buy_secondary_volume_unit=sem["taker_buy_secondary_volume_unit"],
        schema_variant=sem["schema_variant"],
    )


def _unit_factor(unit: str) -> int:
    if unit == "us":
        return 1_000_000
    if unit == "ms":
        return 1_000
    if unit == "s":
        return 1
    raise ValueError(f"unsupported timestamp unit: {unit!r}")


def _to_utc_us(ts: int, unit: str) -> int:
    """Normalize provider timestamp to signed UTC microseconds."""
    if unit == "us":
        return ts
    if unit == "ms":
        return ts * 1_000
    if unit == "s":
        return ts * 1_000_000
    raise ValueError(f"unsupported timestamp unit: {unit!r}")


def _from_utc_us(us: int, unit: str) -> int:
    """Convert UTC microseconds back to source unit (integer division)."""
    if unit == "us":
        return us
    if unit == "ms":
        return us // 1_000
    if unit == "s":
        return us // 1_000_000
    raise ValueError(f"unsupported timestamp unit: {unit!r}")


def _us_to_datetime(us: int) -> datetime:
    """Convert UTC microseconds to aware datetime; raises on out-of-range."""
    sec, micro = divmod(int(us), 1_000_000)
    # Explicit range guard so failures surface as quality issues, not OS noise.
    if sec < 0 or sec > 4102444800:  # 1970-01-01 .. 2100-01-01
        raise ValueError(f"timestamp out of supported UTC range: {us}")
    return datetime.fromtimestamp(sec, tz=timezone.utc).replace(microsecond=micro)


def _datetime_to_us(dt: datetime) -> int:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware UTC")
    utc = dt.astimezone(timezone.utc)
    return calendar.timegm(utc.timetuple()) * 1_000_000 + utc.microsecond


def _add_calendar_months(dt: datetime, months: int) -> datetime:
    month0 = dt.month - 1 + months
    year = dt.year + month0 // 12
    month = month0 % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _interval_steps_source(spec: _IntervalSpec, unit: str) -> int | None:
    """Fixed-interval length in source timestamp units; None for calendar month."""
    if spec.kind != "fixed" or spec.delta is None:
        return None
    return int(spec.delta.total_seconds() * _unit_factor(unit))


def _expected_close_inclusive(open_ts: int, spec: _IntervalSpec, unit: str) -> int:
    """Binance inclusive close: open + interval - 1 source unit."""
    if spec.kind == "fixed":
        steps = _interval_steps_source(spec, unit)
        assert steps is not None
        return open_ts + steps - 1
    open_dt = _us_to_datetime(_to_utc_us(open_ts, unit))
    next_open_dt = _add_calendar_months(open_dt, spec.months)
    next_open_src = _from_utc_us(_datetime_to_us(next_open_dt), unit)
    return next_open_src - 1


def _expected_next_open_us(open_us: int, spec: _IntervalSpec) -> int:
    """Expected next bar open_time in UTC microseconds (unit-independent)."""
    if spec.kind == "fixed":
        assert spec.delta is not None
        return open_us + int(spec.delta.total_seconds() * 1_000_000)
    open_dt = _us_to_datetime(open_us)
    next_open_dt = _add_calendar_months(open_dt, spec.months)
    return _datetime_to_us(next_open_dt)


def _infer_ts_unit(ts_values: Sequence[str]) -> str:
    """Infer from observed digit lengths only (never filename/date)."""
    digits = [v.strip() for v in ts_values if v.strip().isdigit()]
    if not digits:
        return "ms"
    lens = {len(d) for d in digits}
    if any(length >= 16 for length in lens):
        return "us"
    if any(length >= 13 for length in lens):
        return "ms"
    return "s"


def _to_decimal(s: str) -> decimal.Decimal:
    s = s.strip()
    if not s:
        raise ValueError("empty numeric field")
    return decimal.Decimal(s)


def _ohlc_violation(
    o: decimal.Decimal,
    h: decimal.Decimal,
    low: decimal.Decimal,
    c: decimal.Decimal,
) -> bool:
    """Standard OHLC invariants."""
    if h < low:
        return True
    if o > h or o < low:
        return True
    if c > h or c < low:
        return True
    return False


def _is_header_row(row: list[str]) -> bool:
    """True only for an explicit open_time header cell — not any non-digit."""
    if not row:
        return False
    cell = row[0].strip().lower()
    return cell in {"open_time", "opentime"}


def _validate_interval(ot: int, ct: int, spec: _IntervalSpec, unit: str) -> bool:
    """Validate provider close_time against inclusive Binance convention."""
    return ct == _expected_close_inclusive(ot, spec, unit)


def _is_open_at_interval_boundary(ot: int, spec: _IntervalSpec, unit: str) -> bool:
    """Return True if open_time is aligned to the interval boundary in UTC.

    Used to identify the first partial bar on a symbol's listing day, where the
    open_time is aligned to the boundary but the close_time is not.
    """
    if spec.kind != "fixed" or spec.delta is None:
        return False
    dt = _us_to_datetime(_to_utc_us(ot, unit))
    total_seconds = int(spec.delta.total_seconds())
    if total_seconds >= 86400:  # 1d, 3d, 1w
        return dt.hour == 0 and dt.minute == 0 and dt.second == 0
    if total_seconds >= 3600:  # 1h, 2h, 4h, 6h, 8h, 12h
        return dt.minute == 0 and dt.second == 0
    if total_seconds >= 60:  # 1m, 3m, 5m, 15m, 30m
        return dt.second == 0
    return True  # 1s


def _volume_field_names(market: _MarketTypeSpec) -> tuple[str, str, str, str]:
    """Physical Parquet column names for the four volume fields by market."""
    if market.schema_variant == "coin_margined":
        # COIN-M CSV: volume=contracts, field7=base asset volume,
        # field9=taker buy contracts, field10=taker buy base asset volume.
        return (
            "volume",
            "base_asset_volume",
            "taker_buy_volume",
            "taker_buy_base_asset_volume",
        )
    # spot / USD-M: volume=base, field7=quote, field9/10=taker buy base/quote.
    return (
        "volume",
        "quote_volume",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    )


def _schema_fingerprint(market: _MarketTypeSpec) -> str:
    """Stable fingerprint for the material Parquet schema identity."""
    vol_names = _volume_field_names(market)
    material = "|".join(
        [
            BINANCE_KLINE_SCHEMA_NAME,
            BINANCE_KLINE_SCHEMA_VERSION,
            market.schema_variant,
            "open_time:int64_utc_us",
            "close_time:int64_utc_us",
            "source_open_time:int64",
            "source_close_time:int64",
            "source_timestamp_unit:string",
            f"vol:{','.join(vol_names)}",
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _parse_kline_row(
    row: list[str],
    interval_spec: _IntervalSpec,
    market: _MarketTypeSpec,
    *,
    raw_object_id: str,
    is_first: bool = False,
) -> tuple[dict[str, Any], str | None, list[QualityIssue]]:
    """Parse one row. Normalize with the row's own detected unit."""
    issues: list[QualityIssue] = []
    if len(row) != BINANCE_KLINE_FIELD_COUNT:
        issues.append(
            QualityIssue(
                code="binance_kline_malformed_row",
                severity=IssueSeverity.ERROR,
                message=f"expected {BINANCE_KLINE_FIELD_COUNT} fields, got {len(row)}",
                context={"row_preview": row[:3], "raw_object_id": raw_object_id},
            )
        )
        return {}, None, issues

    try:
        ot_s, o_s, h_s, l_s, c_s, v_s, ct_s, qv_s, tr_s, tb_s, tq_s, ign = (
            x.strip() for x in row
        )

        ot = int(ot_s)
        ct = int(ct_s)

        # Always convert with this row's observed unit (never the object's first unit).
        detected = _infer_ts_unit([ot_s, ct_s])
        eff_unit = detected

        if not _validate_interval(ot, ct, interval_spec, eff_unit):
            # The first bar on a symbol's listing day may start at the interval
            # boundary but close early because trading began intra-interval. Treat
            # this specific case as a warning; malformed bars (off-boundary open)
            # remain errors.
            is_listing_day_partial = (
                is_first
                and _is_open_at_interval_boundary(ot, interval_spec, eff_unit)
            )
            severity = (
                IssueSeverity.WARNING
                if is_listing_day_partial
                else IssueSeverity.ERROR
            )
            issues.append(
                QualityIssue(
                    code="binance_kline_interval_mismatch",
                    severity=severity,
                    message=(
                        "provider close_time does not match inclusive interval "
                        "(expected open_time + interval - 1 source unit)"
                    ),
                    context={
                        "open_time": ot,
                        "close_time": ct,
                        "expected_close_time": _expected_close_inclusive(
                            ot, interval_spec, eff_unit
                        ),
                        "interval": interval_spec.label,
                        "unit": eff_unit,
                        "raw_object_id": raw_object_id,
                        "is_first": is_first,
                        "is_listing_day_partial": is_listing_day_partial,
                    },
                )
            )

        o = _to_decimal(o_s)
        h = _to_decimal(h_s)
        low = _to_decimal(l_s)
        c = _to_decimal(c_s)
        v = _to_decimal(v_s)
        secondary = _to_decimal(qv_s)
        tbv = _to_decimal(tb_s)
        tqv = _to_decimal(tq_s)
        trades = int(tr_s)

        if _ohlc_violation(o, h, low, c):
            issues.append(
                QualityIssue(
                    code="binance_kline_ohlc_violation",
                    severity=IssueSeverity.ERROR,
                    message="OHLC invariants violated",
                    context={
                        "open": str(o),
                        "high": str(h),
                        "low": str(low),
                        "close": str(c),
                        "raw_object_id": raw_object_id,
                    },
                )
            )

        open_us = _to_utc_us(ot, eff_unit)
        close_us = _to_utc_us(ct, eff_unit)

        # Surface invalid/out-of-range times; do not swallow.
        try:
            _us_to_datetime(open_us)
            _us_to_datetime(close_us)
        except (ValueError, OverflowError, OSError) as exc:
            issues.append(
                QualityIssue(
                    code="binance_kline_invalid_timestamp",
                    severity=IssueSeverity.ERROR,
                    message=f"invalid or out-of-range timestamp: {exc}",
                    context={
                        "source_open_time": ot,
                        "source_close_time": ct,
                        "unit": eff_unit,
                        "open_time_utc_us": open_us,
                        "close_time_utc_us": close_us,
                        "raw_object_id": raw_object_id,
                    },
                )
            )

        vol_a, vol_b, vol_c, vol_d = _volume_field_names(market)
        parsed: dict[str, Any] = {
            "open_time": open_us,
            "close_time": close_us,
            "source_open_time": ot,
            "source_close_time": ct,
            "source_timestamp_unit": eff_unit,
            "open": o,
            "high": h,
            "low": low,
            "close": c,
            vol_a: v,
            vol_b: secondary,
            "trades": trades,
            vol_c: tbv,
            vol_d: tqv,
            "ignore": ign,
            "raw_object_id": raw_object_id,
        }
        return parsed, eff_unit, issues

    except Exception as exc:
        issues.append(
            QualityIssue(
                code="binance_kline_parse_failure",
                severity=IssueSeverity.ERROR,
                message=str(exc),
                context={"row_preview": row[:4], "raw_object_id": raw_object_id},
            )
        )
        return {}, None, issues


def _detect_duplicates_and_gaps(
    bar_rows: Sequence[dict[str, Any]],
    interval_spec: _IntervalSpec,
    issues: list[QualityIssue],
    *,
    scope: str,
) -> None:
    """Surface duplicate open_time and interval gaps on a bar sequence.

    ``scope`` is ``within_object`` or ``cross_object`` (complete multi-object
    sequence). Issues carry per-object lineage via ``raw_object_id`` fields.
    All observations are preserved.
    """
    if not bar_rows:
        return

    # Duplicates on normalized UTC open_time.
    seen: dict[int, tuple[int, str]] = {}
    for idx, row in enumerate(bar_rows):
        ot = int(row["open_time"])
        rid = str(row.get("raw_object_id", ""))
        if ot in seen:
            first_idx, first_rid = seen[ot]
            issues.append(
                QualityIssue(
                    code="binance_kline_duplicate_open_time",
                    severity=IssueSeverity.ERROR,
                    message=f"duplicate open_time ({scope})",
                    context={
                        "scope": scope,
                        "open_time_utc_us": ot,
                        "source_open_time": row.get("source_open_time"),
                        "first_index": first_idx,
                        "duplicate_index": idx,
                        "first_raw_object_id": first_rid,
                        "raw_object_id": rid,
                        "other_raw_object_id": first_rid if first_rid != rid else None,
                    },
                )
            )
        else:
            seen[ot] = (idx, rid)

    # Gaps on time-ordered sequence using unit-independent UTC microseconds.
    ordered = sorted(range(len(bar_rows)), key=lambda i: int(bar_rows[i]["open_time"]))
    for prev_i, next_i in zip(ordered, ordered[1:]):
        prev = bar_rows[prev_i]
        nxt = bar_rows[next_i]
        prev_us = int(prev["open_time"])
        next_us = int(nxt["open_time"])
        if prev_us == next_us:
            continue
        expected_us = _expected_next_open_us(prev_us, interval_spec)
        if next_us != expected_us:
            prev_rid = str(prev.get("raw_object_id", ""))
            next_rid = str(nxt.get("raw_object_id", ""))
            # For cross_object scope, only emit when the adjacent pair spans objects
            # or always emit for global continuity. Always emit for full sequence.
            issues.append(
                QualityIssue(
                    code="binance_kline_gap",
                    severity=IssueSeverity.ERROR,
                    message=f"gap or non-contiguous open_time ({scope})",
                    context={
                        "scope": scope,
                        "prev_open_time_utc_us": prev_us,
                        "next_open_time_utc_us": next_us,
                        "expected_open_time_utc_us": expected_us,
                        "prev_source_open_time": prev.get("source_open_time"),
                        "next_source_open_time": nxt.get("source_open_time"),
                        "prev_raw_object_id": prev_rid,
                        "next_raw_object_id": next_rid,
                        "raw_object_id": next_rid,
                        "interval": interval_spec.label,
                        "cross_object": prev_rid != next_rid,
                    },
                )
            )


def _bar_schema(market: _MarketTypeSpec) -> pa.Schema:
    vol_a, vol_b, vol_c, vol_d = _volume_field_names(market)
    return pa.schema(
        [
            ("open_time", pa.int64()),  # UTC microseconds
            ("open", pa.decimal128(38, 18)),
            ("high", pa.decimal128(38, 18)),
            ("low", pa.decimal128(38, 18)),
            ("close", pa.decimal128(38, 18)),
            (vol_a, pa.decimal128(38, 18)),
            ("close_time", pa.int64()),  # UTC microseconds
            (vol_b, pa.decimal128(38, 18)),
            ("trades", pa.int64()),
            (vol_c, pa.decimal128(38, 18)),
            (vol_d, pa.decimal128(38, 18)),
            ("ignore", pa.string()),
            ("source_open_time", pa.int64()),
            ("source_close_time", pa.int64()),
            ("source_timestamp_unit", pa.string()),
        ]
    )


def _write_parquet_bars(
    path: Path,
    rows: list[dict[str, Any]],
    market: _MarketTypeSpec,
) -> tuple[str, int, int]:
    """Write deterministic source-specific bar parquet. Return (sha, bytes, row_count)."""
    schema = _bar_schema(market)
    vol_a, vol_b, vol_c, vol_d = _volume_field_names(market)
    if not rows:
        table = pa.table([[] for _ in range(len(schema))], schema=schema)
    else:
        arrays = {
            "open_time": pa.array([r["open_time"] for r in rows], type=pa.int64()),
            "open": pa.array([r["open"] for r in rows], type=pa.decimal128(38, 18)),
            "high": pa.array([r["high"] for r in rows], type=pa.decimal128(38, 18)),
            "low": pa.array([r["low"] for r in rows], type=pa.decimal128(38, 18)),
            "close": pa.array([r["close"] for r in rows], type=pa.decimal128(38, 18)),
            vol_a: pa.array([r[vol_a] for r in rows], type=pa.decimal128(38, 18)),
            "close_time": pa.array([r["close_time"] for r in rows], type=pa.int64()),
            vol_b: pa.array([r[vol_b] for r in rows], type=pa.decimal128(38, 18)),
            "trades": pa.array([r["trades"] for r in rows], type=pa.int64()),
            vol_c: pa.array([r[vol_c] for r in rows], type=pa.decimal128(38, 18)),
            vol_d: pa.array([r[vol_d] for r in rows], type=pa.decimal128(38, 18)),
            "ignore": pa.array([r["ignore"] for r in rows], type=pa.string()),
            "source_open_time": pa.array(
                [r["source_open_time"] for r in rows], type=pa.int64()
            ),
            "source_close_time": pa.array(
                [r["source_close_time"] for r in rows], type=pa.int64()
            ),
            "source_timestamp_unit": pa.array(
                [r["source_timestamp_unit"] for r in rows], type=pa.string()
            ),
        }
        table = pa.table(arrays, schema=schema)

    pq.write_table(table, str(path), compression="zstd")
    from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size

    sha, byte_size = stream_sha256_and_size(path)
    return sha, byte_size, len(rows)


def _write_quality_parquet(path: Path, issues: list[QualityIssue]) -> tuple[str, int, int]:
    """Write deterministic quality issues parquet."""
    if not issues:
        schema = pa.schema(
            [
                ("code", pa.string()),
                ("severity", pa.string()),
                ("message", pa.string()),
                ("column", pa.string()),
                ("context", pa.string()),
            ]
        )
        table = pa.table([[] for _ in range(len(schema))], schema=schema)
    else:
        data = {
            "code": [i.code for i in issues],
            "severity": [i.severity.value for i in issues],
            "message": [i.message for i in issues],
            "column": [i.column or "" for i in issues],
            "context": [str(dict(i.context)) for i in issues],
        }
        table = pa.table(data)
    pq.write_table(table, str(path), compression="zstd")
    from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size

    sha, byte_size = stream_sha256_and_size(path)
    return sha, byte_size, len(issues)


def _parquet_row_counter(path: Path) -> int:
    """MAN-001 row verifier: observe parquet row count without full load."""
    return int(pq.ParquetFile(str(path)).metadata.num_rows)


def _require_code_commit(code_commit: str) -> str:
    """Require a non-empty immutable code identity from the caller.

    Does not invoke Git or infer repository state. Rejects empty and the
    placeholder ``unknown``.
    """
    commit = code_commit.strip()
    if not commit or commit == "unknown":
        raise ValueError(
            "code_commit is required and must be a non-empty immutable code "
            "identity supplied by the caller (not 'unknown'); the normalizer "
            "does not invoke Git or infer repository state"
        )
    return commit


def _canonical_config_bytes(
    *,
    market: _MarketTypeSpec,
    interval_spec: _IntervalSpec,
    venue_id: str,
    instrument_id: str,
    schema_fingerprint: str,
) -> bytes:
    """Deterministic encoding of identity-bearing normalization configuration."""
    payload = {
        "close_time_convention": "inclusive_open_plus_interval_minus_one",
        "dataset_type": BINANCE_KLINE_DATASET_TYPE,
        "instrument_id": instrument_id,
        "interval": interval_spec.label,
        "interval_kind": interval_spec.kind,
        "market_type": market.canonical,
        "schema_fingerprint": schema_fingerprint,
        "schema_name": BINANCE_KLINE_SCHEMA_NAME,
        "schema_variant": market.schema_variant,
        "schema_version": BINANCE_KLINE_SCHEMA_VERSION,
        "secondary_volume_unit": market.secondary_volume_unit,
        "taker_buy_secondary_volume_unit": market.taker_buy_secondary_volume_unit,
        "taker_buy_volume_unit": market.taker_buy_volume_unit,
        "timestamp_storage": "utc_microseconds",
        "transform_name": BINANCE_KLINE_TRANSFORM_NAME,
        "transform_version": BINANCE_KLINE_TRANSFORM_VERSION,
        "venue_id": venue_id,
        "volume_unit": market.volume_unit,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def _resolve_config_sha256(
    config_sha256: str | None,
    *,
    market: _MarketTypeSpec,
    interval_spec: _IntervalSpec,
    venue_id: str,
    instrument_id: str,
    schema_fingerprint: str,
) -> str:
    """Return a MAN-001-valid 64-hex config hash.

    When the caller supplies a hash, validate it. When omitted or empty, derive a
    deterministic hash from identity-bearing normalization configuration. Never
    emit an empty string.
    """
    if config_sha256 is not None and str(config_sha256).strip() != "":
        digest = str(config_sha256).strip().lower()
        if not _SHA256_HEX_RE.fullmatch(digest):
            raise ValueError(
                "config_sha256 must be a 64-character lowercase hex SHA-256 digest"
            )
        return digest
    return hashlib.sha256(
        _canonical_config_bytes(
            market=market,
            interval_spec=interval_spec,
            venue_id=venue_id,
            instrument_id=instrument_id,
            schema_fingerprint=schema_fingerprint,
        )
    ).hexdigest()


def _assign_issue_to_objects(
    issue: QualityIssue,
    works: dict[str, _ObjectWork],
) -> None:
    """Route a global issue to the relevant per-object quality partition(s)."""
    ctx = dict(issue.context)
    targets: list[str] = []
    for key in ("raw_object_id", "next_raw_object_id", "prev_raw_object_id"):
        rid = ctx.get(key)
        if isinstance(rid, str) and rid and rid in works and rid not in targets:
            targets.append(rid)
    if not targets:
        # Fallback: attach to every object so the issue is not lost.
        targets = list(works.keys())
    for rid in targets:
        works[rid].issues.append(issue)


def normalize_binance_kline(
    raw_objects: Sequence[RawObject],
    *,
    market_type: str,
    interval: str,
    venue_id: str,
    instrument_id: str,
    output_dir: Path | str,
    code_commit: str,
    config_sha256: str | None = None,
) -> BinanceKlineNormalizeResult:
    """Normalize registered Binance kline archive raw objects.

    Explicit params required, including a non-empty immutable ``code_commit``
    supplied by the caller (never inferred via Git). When ``config_sha256`` is
    omitted, a deterministic 64-hex digest is derived from identity-bearing
    normalization configuration so the returned plan is MAN-001-valid.
    Per-row unit inference from data. Stages source-specific bars + quality
    with raw-object lineage. Returns MAN-001-publishable PublishPlan
    (source-normalized only).
    """
    if not raw_objects:
        raise ValueError("at least one raw_object required")
    if not venue_id or not instrument_id:
        raise ValueError("venue_id and instrument_id are required and non-empty")
    if not interval or not str(interval).strip():
        raise ValueError(
            "market_type, interval, venue_id, instrument_id are required and non-empty"
        )
    if not market_type or not str(market_type).strip():
        raise ValueError(
            "market_type, interval, venue_id, instrument_id are required and non-empty"
        )

    code_id = _require_code_commit(code_commit)
    market = _resolve_market_type(market_type)
    interval_spec = _parse_interval(interval)
    schema_fp_early = _schema_fingerprint(market)
    cfg_hash = _resolve_config_sha256(
        config_sha256,
        market=market,
        interval_spec=interval_spec,
        venue_id=venue_id,
        instrument_id=instrument_id,
        schema_fingerprint=schema_fp_early,
    )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    works: dict[str, _ObjectWork] = {}
    deps: list[DependencyRef] = []
    min_event: datetime | None = None
    max_event: datetime | None = None

    # ---- Pass 1: parse every object, collect bars + within-object issues ----
    for ro in raw_objects:
        assert_regular_nonsymlink_file(
            ro.storage_path, label=f"raw_object {ro.raw_object_id}"
        )

        deps.append(
            DependencyRef(
                id=ro.raw_object_id,
                kind=DependencyKind.RAW_OBJECT,
                role="binance_kline_archive",
            )
        )

        work = _ObjectWork(
            raw_object_id=ro.raw_object_id,
            bar_path=out_dir / f"bars_{ro.raw_object_id}.parquet",
            quality_path=out_dir / f"quality_{ro.raw_object_id}.parquet",
        )
        works[ro.raw_object_id] = work

        def _consume_row(
            row: list[str], *, _work: _ObjectWork = work, _row_idx: int = 0
        ) -> None:
            nonlocal min_event, max_event
            parsed, detected, row_issues = _parse_kline_row(
                row,
                interval_spec,
                market,
                raw_object_id=_work.raw_object_id,
                is_first=(_row_idx == 0),
            )
            for issue in row_issues:
                _work.issues.append(issue)
            if detected is not None:
                _work.units_seen.add(detected)
                if _work.obj_unit is None:
                    _work.obj_unit = detected
            if parsed:
                _work.bar_rows.append(parsed)
                open_us = int(parsed["open_time"])
                try:
                    ts = _us_to_datetime(open_us)
                except (ValueError, OverflowError, OSError) as exc:
                    _work.issues.append(
                        QualityIssue(
                            code="binance_kline_invalid_timestamp",
                            severity=IssueSeverity.ERROR,
                            message=f"coverage conversion failed: {exc}",
                            context={
                                "open_time_utc_us": open_us,
                                "source_open_time": parsed.get("source_open_time"),
                                "source_timestamp_unit": parsed.get(
                                    "source_timestamp_unit"
                                ),
                                "raw_object_id": _work.raw_object_id,
                            },
                        )
                    )
                else:
                    if min_event is None or ts < min_event:
                        min_event = ts
                    if max_event is None or ts > max_event:
                        max_event = ts

        try:
            with zipfile.ZipFile(ro.storage_path, "r") as zf:
                csv_members = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                if len(csv_members) != 1:
                    work.issues.append(
                        QualityIssue(
                            code="binance_archive_csv_count",
                            severity=IssueSeverity.ERROR,
                            message=(
                                f"expected exactly 1 CSV in archive, got {len(csv_members)}"
                            ),
                            context={
                                "members": csv_members[:3],
                                "raw_object_id": ro.raw_object_id,
                            },
                        )
                    )
                else:
                    csv_name = csv_members[0]
                    with zf.open(csv_name) as raw_f:
                        text_f = io.TextIOWrapper(raw_f, encoding="utf-8", newline="")
                        reader = csv.reader(text_f, delimiter=",")
                        try:
                            first = next(reader)
                        except StopIteration:
                            first = None
                        if first is not None:
                            if _is_header_row(first):
                                pass  # skip explicit header only
                            else:
                                _consume_row(first, _row_idx=0)
                            for row_idx, data_row in enumerate(reader, start=1):
                                _consume_row(data_row, _row_idx=row_idx)
        except zipfile.BadZipFile as exc:
            work.issues.append(
                QualityIssue(
                    code="binance_archive_bad_zip",
                    severity=IssueSeverity.ERROR,
                    message=str(exc),
                    context={"raw_object_id": ro.raw_object_id},
                )
            )

        # Mixed units: reject object; each row already normalized with its own unit.
        if len(work.units_seen) > 1:
            work.issues.append(
                QualityIssue(
                    code="binance_kline_mixed_timestamp_unit",
                    severity=IssueSeverity.ERROR,
                    message="mixed timestamp units within archive object",
                    context={
                        "units_seen": sorted(work.units_seen),
                        "raw_object_id": ro.raw_object_id,
                    },
                )
            )

        if work.obj_unit is None:
            work.obj_unit = "ms"

        # Empty / header-only: fail closed (no silent PASS with zero bars).
        if not work.bar_rows:
            work.issues.append(
                QualityIssue(
                    code="binance_kline_empty_observations",
                    severity=IssueSeverity.ERROR,
                    message="archive produced no typed bar observations",
                    context={"raw_object_id": ro.raw_object_id},
                )
            )

        # Within-object duplicate / gap detection.
        _detect_duplicates_and_gaps(
            work.bar_rows,
            interval_spec,
            work.issues,
            scope="within_object",
        )

    # ---- Pass 2: complete multi-object sequence (cross-object dups/gaps) ----
    global_bars: list[dict[str, Any]] = []
    for work in works.values():
        global_bars.extend(work.bar_rows)

    if len(works) > 1 and global_bars:
        global_issues: list[QualityIssue] = []
        _detect_duplicates_and_gaps(
            global_bars,
            interval_spec,
            global_issues,
            scope="cross_object",
        )
        # Only attach issues that are truly cross-object (span objects) or
        # cross_object-scoped duplicates; drop pure within-object duplicates of
        # gaps already reported, to avoid double-counting identical pairs.
        for issue in global_issues:
            ctx = dict(issue.context)
            if issue.code == "binance_kline_gap":
                if ctx.get("cross_object"):
                    _assign_issue_to_objects(issue, works)
            elif issue.code == "binance_kline_duplicate_open_time":
                first_rid = ctx.get("first_raw_object_id")
                rid = ctx.get("raw_object_id")
                if first_rid and rid and first_rid != rid:
                    _assign_issue_to_objects(issue, works)

    # ---- Pass 3: write partitions + PublishPlan ----
    all_issues: list[QualityIssue] = []
    all_bar_paths: list[Path] = []
    all_quality_paths: list[Path] = []
    output_sources: dict[str, Path] = {}
    output_specs: list[OutputFileSpec] = []
    row_counters: dict[str, Callable[[Path], int]] = {}
    total_rows = 0
    total_bytes = 0

    for ro in raw_objects:
        work = works[ro.raw_object_id]
        obj_unit = work.obj_unit or "ms"

        bar_sha, bar_bytes, bar_n = _write_parquet_bars(
            work.bar_path, work.bar_rows, market
        )
        all_bar_paths.append(work.bar_path)
        rel_bar = (
            f"binance/{market.canonical}/{interval_spec.label}/"
            f"raw_{ro.raw_object_id}/bars.parquet"
        )
        output_sources[rel_bar] = work.bar_path
        row_counters[rel_bar] = _parquet_row_counter
        output_specs.append(
            OutputFileSpec(
                relative_path=rel_bar,
                sha256=bar_sha,
                rows=bar_n,
                bytes=bar_bytes,
                partition={
                    "raw_object_id": ro.raw_object_id,
                    "market_type": market.canonical,
                    "interval": interval_spec.label,
                    "venue_id": venue_id,
                    "instrument_id": instrument_id,
                    "timestamp_unit": obj_unit,
                    "timestamp_storage": "utc_microseconds",
                    "volume_unit": market.volume_unit,
                    "secondary_volume_unit": market.secondary_volume_unit,
                    "taker_buy_volume_unit": market.taker_buy_volume_unit,
                    "taker_buy_secondary_volume_unit": (
                        market.taker_buy_secondary_volume_unit
                    ),
                    "schema_variant": market.schema_variant,
                },
                rows_verified=True,
            )
        )
        total_rows += bar_n
        total_bytes += bar_bytes

        q_sha, q_bytes, q_n = _write_quality_parquet(work.quality_path, work.issues)
        all_quality_paths.append(work.quality_path)
        rel_q = (
            f"binance/{market.canonical}/{interval_spec.label}/"
            f"raw_{ro.raw_object_id}/quality.parquet"
        )
        output_sources[rel_q] = work.quality_path
        row_counters[rel_q] = _parquet_row_counter
        output_specs.append(
            OutputFileSpec(
                relative_path=rel_q,
                sha256=q_sha,
                rows=q_n,
                bytes=q_bytes,
                partition={
                    "raw_object_id": ro.raw_object_id,
                    "market_type": market.canonical,
                    "interval": interval_spec.label,
                    "venue_id": venue_id,
                    "instrument_id": instrument_id,
                },
                rows_verified=True,
            )
        )
        total_bytes += q_bytes
        total_rows += q_n
        all_issues.extend(work.issues)

    has_error = any(i.severity is IssueSeverity.ERROR for i in all_issues)
    has_warn = any(i.severity is IssueSeverity.WARNING for i in all_issues)
    if has_error:
        q_status = QualityStatus.REJECTED
    elif has_warn:
        q_status = QualityStatus.PASS_WITH_WARNINGS
    else:
        q_status = QualityStatus.PASS

    vol_names = _volume_field_names(market)
    schema_fp = schema_fp_early

    plan = PublishPlan(
        dataset_type=BINANCE_KLINE_DATASET_TYPE,
        schema=SchemaIdentity(
            name=BINANCE_KLINE_SCHEMA_NAME,
            version=BINANCE_KLINE_SCHEMA_VERSION,
            fingerprint=schema_fp,
        ),
        transform=TransformSpec(
            name=BINANCE_KLINE_TRANSFORM_NAME,
            version=BINANCE_KLINE_TRANSFORM_VERSION,
        ),
        code=CodeIdentity(commit=code_id),
        config=ConfigIdentity(config_sha256=cfg_hash),
        dependencies=tuple(deps),
        output_sources=output_sources,
        output_specs=output_specs,
        statistics=DatasetStatistics(
            row_count=total_rows,
            byte_size=total_bytes,
        ),
        coverage=CoverageWindow(
            event_start=min_event,
            event_end=max_event,
        ),
        quality_status=q_status,
        quality_summary={
            "issue_count": len(all_issues),
            "market_type": market.canonical,
            "volume_unit": market.volume_unit,
            "secondary_volume_unit": market.secondary_volume_unit,
            "taker_buy_volume_unit": market.taker_buy_volume_unit,
            "taker_buy_secondary_volume_unit": market.taker_buy_secondary_volume_unit,
            "schema_variant": market.schema_variant,
            "volume_field_names": list(vol_names),
            "interval": interval_spec.label,
            "interval_kind": interval_spec.kind,
            "venue_id": venue_id,
            "instrument_id": instrument_id,
            "normalizer_version": BINANCE_KLINE_TRANSFORM_VERSION,
            "schema_version": BINANCE_KLINE_SCHEMA_VERSION,
            "schema_fingerprint": schema_fp,
            "config_sha256": cfg_hash,
            "code_commit": code_id,
            "timestamp_unit_inferred_per_row": True,
            "timestamp_storage": "utc_microseconds",
            "close_time_convention": "inclusive_open_plus_interval_minus_one",
        },
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters=row_counters,
    )

    return BinanceKlineNormalizeResult(
        publish_plan=plan,
        bar_paths=tuple(all_bar_paths),
        quality_paths=tuple(all_quality_paths),
        issues=tuple(all_issues),
    )
