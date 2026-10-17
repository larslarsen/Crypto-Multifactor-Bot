"""FUND-005 — BitMEX Perpetual Funding Rate Ingestion & Cashflow Provider.

Ingests historical funding rates from BitMEX GET /funding, normalizes them into
a PyArrow table, and computes point-in-time funding cashflows.

Source boundary:
- Raw API rows must use BitMEX camelCase rate, daily-rate, and interval fields.
- Normalized rows are an explicit eight-field contract.
- Unknown availability stays null. Event time is not availability.
- Identical (symbol, timestamp_us) observations collapse. Conflicts fail closed.
"""

from __future__ import annotations

import math
import re
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

DEFAULT_BASE_URL: Final[str] = "https://www.bitmex.com/api/v1"
FUNDING_ENDPOINT: Final[str] = "/funding"
INSTRUMENT_ENDPOINT: Final[str] = "/instrument/active"
INSTRUMENT_ALL_ENDPOINT: Final[str] = "/instrument"
PROVENANCE_SOURCE: Final[str] = "bitmex_funding"
PERP_INSTRUMENT_TYP: Final[str] = "FFWCSX"
_US_PER_SECOND: Final[int] = 1_000_000
_MAX_COUNT_PER_REQ: Final[int] = 500
_DEFAULT_REQUESTS_PER_MINUTE: Final[int] = 120
_DEFAULT_429_RETRIES: Final[int] = 5
_DEFAULT_429_SLEEP_S: Final[float] = 5.0
_MAX_429_SLEEP_S: Final[float] = 60.0
_ALL_ZERO_NONEMPTY_MIN_ROWS: Final[int] = 2
_RAW_VALUE_FIELDS: Final[tuple[str, ...]] = (
    "fundingRate",
    "fundingRateDaily",
    "fundingInterval",
)
_NORMALIZED_ALIASES: Final[tuple[str, ...]] = (
    "funding_rate",
    "funding_rate_daily",
    "funding_interval",
    "timestamp_us",
    "availability_time",
)
_NORMALIZED_FIELDS: Final[tuple[str, ...]] = (
    "timestamp",
    "timestamp_us",
    "symbol",
    "funding_rate",
    "funding_rate_daily",
    "funding_interval",
    "source",
    "availability_time",
)
_OBSERVATION_FIELDS: Final[tuple[str, ...]] = _NORMALIZED_FIELDS

BITMEX_FUNDING_SCHEMA: Final[pa.Schema] = pa.schema(
    [
        ("timestamp", pa.string()),
        ("timestamp_us", pa.int64()),
        ("symbol", pa.string()),
        ("funding_rate", pa.float64()),
        ("funding_rate_daily", pa.float64()),
        ("funding_interval", pa.string()),
        ("source", pa.string()),
        ("availability_time", pa.int64()),
    ]
)


class BitMEXFundingError(RuntimeError):
    """Base error for BitMEX funding ingestion and provider operations."""

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


def _require_utc(dt: datetime, *, field: str) -> datetime:
    if not isinstance(dt, datetime):
        raise BitMEXFundingError(
            f"{field} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise BitMEXFundingError(
            f"{field} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


def event_datetime_to_us(dt: datetime) -> int:
    """Convert an aware datetime to Unix microseconds without a float round trip."""
    utc = _require_utc(dt, field="timestamp")
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = utc - epoch
    return (
        delta.days * 86_400 * _US_PER_SECOND
        + delta.seconds * _US_PER_SECOND
        + delta.microseconds
    )


def us_to_event_datetime(timestamp_us: int) -> datetime:
    """Inverse of event_datetime_to_us for a nonnegative integer microsecond count."""
    if isinstance(timestamp_us, bool) or not isinstance(timestamp_us, int):
        raise BitMEXFundingError(
            "timestamp_us must be an integer microsecond value",
            context={"type": type(timestamp_us).__name__},
        )
    if timestamp_us < 0:
        raise BitMEXFundingError(
            "timestamp_us must be a nonnegative integer microsecond value",
            context={"timestamp_us": timestamp_us},
        )
    seconds, micros = divmod(timestamp_us, _US_PER_SECOND)
    try:
        instant = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OSError, OverflowError, ValueError) as exc:
        raise BitMEXFundingError(
            "timestamp_us is outside the representable range",
            context={"timestamp_us": timestamp_us},
        ) from exc
    return instant.replace(microsecond=micros)


def _dt_to_us(dt: datetime) -> int:
    return event_datetime_to_us(dt)


def _format_event_timestamp(dt: datetime) -> str:
    utc = dt.astimezone(timezone.utc)
    base = utc.strftime("%Y-%m-%dT%H:%M:%S")
    if utc.microsecond:
        return f"{base}.{utc.microsecond:06d}Z"
    return f"{base}Z"


def format_funding_request_bound(dt: datetime) -> str:
    """Serialize an inclusive request bound without dropping microseconds."""
    utc = _require_utc(dt, field="timestamp")
    return f"{utc.strftime('%Y-%m-%dT%H:%M:%S')}.{utc.microsecond:06d}Z"


# Calendar date, T or space, HH:MM:SS, optional dot fraction, optional Z or
# whole-second numeric offset. Comma fractions and fractional offsets are
# outside this shape; fromisoformat would accept them and can truncate.
_SUPPORTED_TIMESTAMP = re.compile(
    r"^(?P<prefix>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"
    r"(?:\.(?P<fraction>\d+))?"
    r"(?P<suffix>Z|[+-]\d{2}:\d{2}(?::\d{2})?)?$"
)


def require_exact_microsecond_timestamp(value: str) -> str:
    """Return a timestamp whose only fraction is an exact microsecond value.

    The supported source shape is a calendar date, ``T`` or space, ``HH:MM:SS``,
    an optional ``.`` fraction, and an optional ``Z`` or numeric offset with no
    fraction. Comma fractions and fractional timezone offsets are rejected.
    More than six fractional digits are kept only when every extra digit is
    zero, and those zeros are removed explicitly.
    """
    if not isinstance(value, str):
        raise BitMEXFundingError(
            "timestamp precision is not representable in microseconds",
            context={"type": type(value).__name__},
        )
    matched = _SUPPORTED_TIMESTAMP.fullmatch(value)
    if matched is None:
        if "," in value or "." in value:
            raise BitMEXFundingError(
                "unsupported timestamp syntax",
                context={"timestamp": value},
            )
        return value
    digits = matched.group("fraction")
    if digits is None or len(digits) <= 6:
        return value
    if any(digit != "0" for digit in digits[6:]):
        raise BitMEXFundingError(
            "timestamp precision is not representable in microseconds",
            context={"timestamp": value},
        )
    suffix = matched.group("suffix") or ""
    return f"{matched.group('prefix')}.{digits[:6]}{suffix}"


def _parse_aware_event_time(
    value: Any,
    *,
    field: str,
    item: Mapping[str, Any],
) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise BitMEXFundingError(
            "funding record missing valid ISO timestamp",
            context={"item": dict(item), "field": field},
        )
    text = require_exact_microsecond_timestamp(value.strip())
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise BitMEXFundingError(
            "funding record missing valid ISO timestamp",
            context={"item": dict(item), "field": field},
        ) from exc
    if parsed.tzinfo is None:
        raise BitMEXFundingError(
            "funding event timestamp must be timezone-aware",
            context={"item": dict(item), "field": field},
        )
    return parsed.astimezone(timezone.utc)


def _require_symbol(raw: Any, *, item: Mapping[str, Any]) -> str:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise BitMEXFundingError(
            "funding record missing symbol",
            context={"item": dict(item)},
        )
    if not isinstance(raw, str):
        raise BitMEXFundingError(
            "funding record symbol must be a nonempty string",
            context={"item": dict(item), "type": type(raw).__name__},
        )
    return raw.strip().upper()


def _require_finite_number(raw: Any, *, field: str, item: Mapping[str, Any]) -> float:
    """Accept JSON numbers only. Numeric strings are not raw funding rates."""
    if raw is None:
        raise BitMEXFundingError(
            f"funding record missing {field}",
            context={"item": dict(item), "field": field},
        )
    if isinstance(raw, bool):
        raise BitMEXFundingError(
            f"boolean {field} is not a numeric funding rate",
            context={"item": dict(item), "field": field},
        )
    if not isinstance(raw, (int, float)):
        raise BitMEXFundingError(
            f"{field} must be a numeric JSON value",
            context={"item": dict(item), "field": field, "type": type(raw).__name__},
        )
    value = float(raw)
    if not math.isfinite(value):
        raise BitMEXFundingError(
            f"non-finite {field}: {raw}",
            context={"item": dict(item), "field": field},
        )
    return value


def _require_funding_interval(raw: Any, *, item: Mapping[str, Any]) -> str:
    if not isinstance(raw, str):
        raise BitMEXFundingError(
            "funding interval must be a nonempty string",
            context={"item": dict(item), "type": type(raw).__name__},
        )
    interval = raw.strip()
    if not interval:
        raise BitMEXFundingError(
            "funding record has empty required funding interval",
            context={"item": dict(item)},
        )
    return interval


def _require_microseconds(raw: Any, *, field: str, item: Mapping[str, Any]) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise BitMEXFundingError(
            f"{field} must be an integer microsecond value",
            context={"item": dict(item), "field": field, "type": type(raw).__name__},
        )
    return raw


def _availability_us(
    item: Mapping[str, Any],
    *,
    availability_time: datetime | None,
    read_item: bool,
) -> int | None:
    # Unknown source publication time stays unknown. Do not copy event time.
    if availability_time is not None:
        return event_datetime_to_us(availability_time)
    if not read_item:
        return None
    if "availability_time" not in item:
        raise BitMEXFundingError(
            "source-field drift: normalized funding record is incomplete",
            context={"item": dict(item), "missing_fields": ["availability_time"]},
        )
    raw = item.get("availability_time")
    if raw is None:
        return None
    return _require_microseconds(raw, field="availability_time", item=item)


def _funding_record_kind(item: Mapping[str, Any]) -> str:
    camel = [name for name in _RAW_VALUE_FIELDS if name in item]
    aliases = [name for name in _NORMALIZED_ALIASES if name in item]
    if camel and aliases:
        raise BitMEXFundingError(
            "mixed contradictory funding field aliases",
            context={"item": dict(item), "raw_fields": camel, "normalized_fields": aliases},
        )
    if aliases:
        missing = [name for name in _NORMALIZED_FIELDS if name not in item]
        if missing:
            raise BitMEXFundingError(
                "source-field drift: normalized funding record is incomplete",
                context={"item": dict(item), "missing_fields": missing},
            )
        return "normalized"
    return "raw"


def _observation(record: Mapping[str, Any]) -> dict[str, Any]:
    missing = [name for name in _OBSERVATION_FIELDS if name not in record]
    if missing:
        raise BitMEXFundingError(
            "funding observation missing normalized fields",
            context={"missing_fields": missing},
        )
    symbol = record["symbol"]
    timestamp_us = record["timestamp_us"]
    if not isinstance(symbol, str) or isinstance(timestamp_us, bool) or not isinstance(timestamp_us, int):
        raise BitMEXFundingError(
            "funding observation key is invalid",
            context={"symbol_type": type(symbol).__name__, "timestamp_type": type(timestamp_us).__name__},
        )
    return {name: record[name] for name in _OBSERVATION_FIELDS}


def collapse_funding_observations(
    records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Collapse identical keys and fail closed on conflicting values."""
    merged: dict[tuple[str, int], dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise BitMEXFundingError(
                "funding observation must be a mapping",
                context={"type": type(record).__name__},
            )
        current = _observation(record)
        key = (current["symbol"], current["timestamp_us"])
        prior = merged.get(key)
        if prior is None:
            merged[key] = current
            continue
        if any(prior[name] != current[name] for name in _OBSERVATION_FIELDS):
            raise BitMEXFundingError(
                "conflicting funding observations for the same symbol and timestamp",
                context={"symbol": key[0], "timestamp_us": key[1]},
            )
    return [merged[key] for key in sorted(merged)]


def parse_iso_datetime(value: Any) -> datetime | None:
    """Parse ISO datetime string into UTC datetime.

    Lenient helper retained for cashflow lookup. The funding record boundary
    uses a stricter aware parser and does not call this function.
    """
    if not value or not isinstance(value, str):
        return None
    val = value.strip()
    if not val:
        return None
    if val.endswith("Z"):
        val = val[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _normalize_raw_funding_record(
    item: Mapping[str, Any],
    *,
    availability_time: datetime | None,
) -> dict[str, Any]:
    aliases = [name for name in _NORMALIZED_ALIASES if name in item]
    if aliases:
        raise BitMEXFundingError(
            "mixed contradictory funding field aliases",
            context={"item": dict(item), "normalized_fields": aliases},
        )
    event_time = _parse_aware_event_time(item.get("timestamp"), field="timestamp", item=item)
    symbol = _require_symbol(item.get("symbol"), item=item)
    missing_raw = [name for name in _RAW_VALUE_FIELDS if name not in item]
    if missing_raw:
        raise BitMEXFundingError(
            "source-field drift: raw BitMEX funding record missing required fields",
            context={"item": dict(item), "missing_fields": missing_raw},
        )
    if "source" in item and item.get("source") != PROVENANCE_SOURCE:
        raise BitMEXFundingError(
            "raw funding source must be bitmex_funding",
            context={"item": dict(item), "source": item.get("source")},
        )
    funding_rate = _require_finite_number(item.get("fundingRate"), field="fundingRate", item=item)
    funding_rate_daily = _require_finite_number(
        item.get("fundingRateDaily"),
        field="fundingRateDaily",
        item=item,
    )
    funding_interval = _require_funding_interval(item.get("fundingInterval"), item=item)
    timestamp_us = event_datetime_to_us(event_time)
    return {
        "timestamp": _format_event_timestamp(event_time),
        "timestamp_us": timestamp_us,
        "symbol": symbol,
        "funding_rate": funding_rate,
        "funding_rate_daily": funding_rate_daily,
        "funding_interval": funding_interval,
        "source": PROVENANCE_SOURCE,
        "availability_time": _availability_us(
            item,
            availability_time=availability_time,
            read_item=False,
        ),
    }


def _normalize_normalized_funding_record(
    item: Mapping[str, Any],
    *,
    availability_time: datetime | None,
) -> dict[str, Any]:
    camel = [name for name in _RAW_VALUE_FIELDS if name in item]
    if camel:
        raise BitMEXFundingError(
            "mixed contradictory funding field aliases",
            context={"item": dict(item), "raw_fields": camel},
        )
    missing = [name for name in _NORMALIZED_FIELDS if name not in item]
    if missing:
        raise BitMEXFundingError(
            "source-field drift: normalized funding record is incomplete",
            context={"item": dict(item), "missing_fields": missing},
        )
    event_time = _parse_aware_event_time(item.get("timestamp"), field="timestamp", item=item)
    timestamp_us = _require_microseconds(item.get("timestamp_us"), field="timestamp_us", item=item)
    derived_us = event_datetime_to_us(event_time)
    if timestamp_us != derived_us:
        raise BitMEXFundingError(
            "funding event timestamp and timestamp_us disagree",
            context={
                "item": dict(item),
                "timestamp_us": timestamp_us,
                "derived_us": derived_us,
            },
        )
    symbol = _require_symbol(item.get("symbol"), item=item)
    if item.get("source") != PROVENANCE_SOURCE:
        raise BitMEXFundingError(
            "normalized funding provenance must be bitmex_funding",
            context={"item": dict(item), "source": item.get("source")},
        )
    funding_rate = _require_finite_number(item.get("funding_rate"), field="funding_rate", item=item)
    funding_rate_daily = _require_finite_number(
        item.get("funding_rate_daily"),
        field="funding_rate_daily",
        item=item,
    )
    funding_interval = _require_funding_interval(item.get("funding_interval"), item=item)
    if availability_time is None:
        availability = _availability_us(item, availability_time=None, read_item=True)
    else:
        availability = event_datetime_to_us(availability_time)
    return {
        "timestamp": _format_event_timestamp(event_time),
        "timestamp_us": timestamp_us,
        "symbol": symbol,
        "funding_rate": funding_rate,
        "funding_rate_daily": funding_rate_daily,
        "funding_interval": funding_interval,
        "source": PROVENANCE_SOURCE,
        "availability_time": availability,
    }


def normalize_funding_record(
    item: Mapping[str, Any],
    *,
    availability_time: datetime | None = None,
    record_kind: str | None = None,
) -> dict[str, Any]:
    """Normalize one raw API row or one explicit eight-field normalized row.

    ``record_kind="raw"`` is the API response boundary. CamelCase rate fields
    are required there. Normalized aliases do not fill missing raw fields.
    """
    if not isinstance(item, Mapping):
        raise BitMEXFundingError(
            "item must be a mapping",
            context={"type": type(item).__name__},
        )
    if record_kind is not None and record_kind not in {"raw", "normalized"}:
        raise BitMEXFundingError(
            "record_kind must be raw or normalized",
            context={"record_kind": record_kind},
        )
    kind = record_kind if record_kind is not None else _funding_record_kind(item)
    if kind == "raw":
        return _normalize_raw_funding_record(item, availability_time=availability_time)
    return _normalize_normalized_funding_record(item, availability_time=availability_time)


def _require_schema(table: pa.Table) -> None:
    expected = BITMEX_FUNDING_SCHEMA
    if list(table.column_names) != list(expected.names):
        raise BitMEXFundingError(
            "funding table schema does not match the funding contract",
            context={"columns": list(table.column_names)},
        )
    for name in expected.names:
        actual = table.schema.field(name).type
        if actual != expected.field(name).type:
            raise BitMEXFundingError(
                "funding table schema does not match the funding contract",
                context={"column": name, "type": str(actual)},
            )


def validate_funding_history(table: pa.Table) -> None:
    """Fail closed before publication.

    The all-zero gate is per symbol. A nonzero symbol cannot hide another
    symbol whose nontrivial history is entirely zero. One sourced zero event
    remains valid. Interval cadence is not inferred.
    """
    if not isinstance(table, pa.Table):
        raise BitMEXFundingError(
            "table must be a PyArrow Table",
            context={"type": type(table).__name__},
        )
    if table.num_rows == 0:
        raise BitMEXFundingError("cannot accept empty funding history")
    _require_schema(table)

    rates_by_symbol: dict[str, list[float]] = {}
    seen: set[tuple[str, int]] = set()
    for row in table.to_pylist():
        symbol = row.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            raise BitMEXFundingError(
                "funding history contains a missing symbol",
                context={"symbol": symbol},
            )
        symbol = symbol.strip().upper()
        interval = row.get("funding_interval")
        if not isinstance(interval, str) or not interval.strip():
            raise BitMEXFundingError(
                "funding history contains empty required funding intervals",
                context={"symbol": symbol},
            )
        if row.get("source") != PROVENANCE_SOURCE:
            raise BitMEXFundingError(
                "funding provenance must be bitmex_funding",
                context={"symbol": symbol, "source": row.get("source")},
            )
        rate_raw = row.get("funding_rate")
        if rate_raw is None:
            raise BitMEXFundingError(
                "funding history contains missing funding_rate values",
                context={"symbol": symbol},
            )
        try:
            rate = float(rate_raw)
        except (TypeError, ValueError) as exc:
            raise BitMEXFundingError(
                "funding history contains a non-numeric funding_rate",
                context={"symbol": symbol, "value": rate_raw},
            ) from exc
        if isinstance(rate_raw, bool) or not math.isfinite(rate):
            raise BitMEXFundingError(
                "funding history contains a non-finite funding_rate",
                context={"symbol": symbol, "value": rate_raw},
            )
        daily_raw = row.get("funding_rate_daily")
        if daily_raw is None:
            raise BitMEXFundingError(
                "funding history contains missing funding_rate_daily values",
                context={"symbol": symbol},
            )
        try:
            daily = float(daily_raw)
        except (TypeError, ValueError) as exc:
            raise BitMEXFundingError(
                "funding history contains a non-numeric funding_rate_daily",
                context={"symbol": symbol, "value": daily_raw},
            ) from exc
        if isinstance(daily_raw, bool) or not math.isfinite(daily):
            raise BitMEXFundingError(
                "funding history contains a non-finite funding_rate_daily",
                context={"symbol": symbol, "value": daily_raw},
            )
        timestamp_us = row.get("timestamp_us")
        if isinstance(timestamp_us, bool) or not isinstance(timestamp_us, int):
            raise BitMEXFundingError(
                "timestamp_us must be an integer microsecond value",
                context={"symbol": symbol, "type": type(timestamp_us).__name__},
            )
        event_time = _parse_aware_event_time(row.get("timestamp"), field="timestamp", item=row)
        if event_datetime_to_us(event_time) != timestamp_us:
            raise BitMEXFundingError(
                "funding event timestamp and timestamp_us disagree",
                context={"symbol": symbol, "timestamp_us": timestamp_us},
            )
        availability = row.get("availability_time")
        if availability is not None and (
            isinstance(availability, bool) or not isinstance(availability, int)
        ):
            raise BitMEXFundingError(
                "availability_time must be an integer microsecond value or null",
                context={"symbol": symbol, "type": type(availability).__name__},
            )
        key = (symbol, timestamp_us)
        if key in seen:
            raise BitMEXFundingError(
                "duplicate funding key in funding history",
                context={"symbol": symbol, "timestamp_us": timestamp_us},
            )
        seen.add(key)
        rates_by_symbol.setdefault(symbol, []).append(rate)

    for symbol, symbol_rates in sorted(rates_by_symbol.items()):
        nonzero = sum(1 for rate in symbol_rates if rate != 0.0)
        if len(symbol_rates) >= _ALL_ZERO_NONEMPTY_MIN_ROWS and nonzero == 0:
            raise BitMEXFundingError(
                "all-zero nontrivial funding history is not publishable evidence",
                context={
                    "symbol": symbol,
                    "rows": len(symbol_rates),
                    "nonzero_rate_count": nonzero,
                },
            )


def build_funding_table(
    records: Sequence[Mapping[str, Any]],
    *,
    availability_time: datetime | None = None,
) -> pa.Table:
    """Build a BITMEX_FUNDING_SCHEMA table from raw or explicit normalized rows."""
    if not records:
        raise BitMEXFundingError("cannot build funding table from empty records")
    normalized = [
        normalize_funding_record(record, availability_time=availability_time)
        for record in records
    ]
    ordered = collapse_funding_observations(normalized)
    if not ordered:
        raise BitMEXFundingError("cannot build funding table from empty records")
    table = pa.table(
        {
            "timestamp": [row["timestamp"] for row in ordered],
            "timestamp_us": [row["timestamp_us"] for row in ordered],
            "symbol": [row["symbol"] for row in ordered],
            "funding_rate": [row["funding_rate"] for row in ordered],
            "funding_rate_daily": [row["funding_rate_daily"] for row in ordered],
            "funding_interval": [row["funding_interval"] for row in ordered],
            "source": [row["source"] for row in ordered],
            "availability_time": [row["availability_time"] for row in ordered],
        },
        schema=BITMEX_FUNDING_SCHEMA,
    )
    validate_funding_history(table)
    return table


def _require_page_count(count: Any) -> int:
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise BitMEXFundingError(
            "funding page count must be a positive integer",
            context={"count": count},
        )
    return min(count, _MAX_COUNT_PER_REQ)


def _remember_observation(
    store: dict[tuple[str, int], dict[str, Any]],
    observation: Mapping[str, Any],
) -> bool:
    current = _observation(observation)
    key = (current["symbol"], current["timestamp_us"])
    prior = store.get(key)
    if prior is None:
        store[key] = current
        return True
    if any(prior[name] != current[name] for name in _OBSERVATION_FIELDS):
        raise BitMEXFundingError(
            "conflicting funding observations for the same symbol and timestamp",
            context={"symbol": key[0], "timestamp_us": key[1]},
        )
    return False


def _require_instrument_field(item: Mapping[str, Any], field: str) -> str:
    raw = item.get(field)
    if not isinstance(raw, str) or not raw.strip():
        raise BitMEXFundingError(
            "malformed instrument entry: required field must be a nonempty string",
            context={"field": field, "type": type(raw).__name__},
        )
    return raw.strip()


def _validate_instrument_entry(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise BitMEXFundingError(
            "malformed instrument entry",
            context={"type": type(item).__name__},
        )
    _require_instrument_field(item, "symbol")
    _require_instrument_field(item, "typ")
    return item


class BitMEXFundingClient:
    """REST client for BitMEX GET /funding with rate limiting and pagination."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = 30.0,
        requests_per_minute: int = _DEFAULT_REQUESTS_PER_MINUTE,
        client: httpx.Client | None = None,
        max_429_retries: int = _DEFAULT_429_RETRIES,
    ) -> None:
        self._base_url: str = base_url.strip().rstrip("/")
        self._timeout_s: float = float(timeout_s)
        self._min_interval_s: float = 60.0 / max(1, requests_per_minute)
        self._last_request_time: float = 0.0
        self._client: httpx.Client | None = client
        self._max_429_retries: int = max(0, int(max_429_retries))
        self.rate_limit_incidents: list[dict[str, Any]] = []

    def fetch_funding(
        self,
        symbol: str = "XBTUSD",
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        count: int = _MAX_COUNT_PER_REQ,
    ) -> list[dict[str, Any]]:
        """Fetch historical funding rates for one symbol.

        Rows must match the requested symbol and inclusive window. A full page
        that adds no keys is an error. A short terminal page of identical keys
        collapses. Conflicting keys fail closed.
        """
        if not isinstance(symbol, str) or not symbol.strip():
            raise BitMEXFundingError("symbol must be a non-empty string")
        requested = symbol.strip().upper()
        fetch_count = _require_page_count(count)
        start_us = event_datetime_to_us(start_time) if start_time is not None else None
        end_us = event_datetime_to_us(end_time) if end_time is not None else None
        if start_us is not None and end_us is not None and start_us > end_us:
            raise BitMEXFundingError(
                "start_time is after end_time",
                context={"symbol": requested},
            )

        url = f"{self._base_url}{FUNDING_ENDPOINT}"
        all_records: dict[tuple[str, int], dict[str, Any]] = {}
        start_idx = 0

        while True:
            params: dict[str, Any] = {
                "symbol": requested,
                "count": fetch_count,
                "start": start_idx,
                "reverse": "false",
            }
            if start_time is not None:
                params["startTime"] = format_funding_request_bound(start_time)
            if end_time is not None:
                params["endTime"] = format_funding_request_bound(end_time)

            res = self._get(url, params)
            if not isinstance(res, list):
                raise BitMEXFundingError(
                    "BitMEX /funding endpoint returned non-list response",
                    context={"response_type": type(res).__name__},
                )
            if not res:
                break
            if len(res) > fetch_count:
                raise BitMEXFundingError(
                    "funding page exceeded the requested count",
                    context={"symbol": requested, "count": fetch_count, "rows": len(res)},
                )

            new_on_page = 0
            for item in res:
                norm = normalize_funding_record(item, record_kind="raw")
                if norm["symbol"] != requested:
                    raise BitMEXFundingError(
                        "funding row symbol does not match the requested symbol",
                        context={"requested": requested, "symbol": norm["symbol"]},
                    )
                if start_us is not None and norm["timestamp_us"] < start_us:
                    raise BitMEXFundingError(
                        "funding row is outside the requested window",
                        context={"symbol": requested, "timestamp_us": norm["timestamp_us"]},
                    )
                if end_us is not None and norm["timestamp_us"] > end_us:
                    raise BitMEXFundingError(
                        "funding row is outside the requested window",
                        context={"symbol": requested, "timestamp_us": norm["timestamp_us"]},
                    )
                if _remember_observation(all_records, norm):
                    new_on_page += 1

            if new_on_page == 0:
                if len(res) >= fetch_count:
                    raise BitMEXFundingError(
                        "BitMEX funding pagination stalled with no progress",
                        context={"symbol": requested, "start": start_idx, "rows": len(res)},
                    )
                break
            if len(res) < fetch_count:
                break
            next_start = start_idx + len(res)
            if next_start <= start_idx:
                raise BitMEXFundingError(
                    "funding pagination count did not advance",
                    context={"symbol": requested, "start": start_idx},
                )
            start_idx = next_start

        return [all_records[key] for key in sorted(all_records)]

    def fetch_perp_symbols(
        self,
        *,
        state: str | None = "Open",
        active_only: bool = True,
    ) -> list[str]:
        """Discover perpetual contract symbols from BitMEX.

        Filters instruments by type ``FFWCSX`` and optionally by ``state``.
        Returns sorted uppercase symbols.
        """
        if active_only:
            items = self._fetch_instrument_page(
                f"{self._base_url}{INSTRUMENT_ENDPOINT}",
                params={},
            )
        else:
            items = self._fetch_all_perp_instruments()

        symbols: set[str] = set()
        for item in items:
            typ = _require_instrument_field(item, "typ")
            if typ != PERP_INSTRUMENT_TYP:
                continue
            if state is not None:
                instrument_state = _require_instrument_field(item, "state")
                if instrument_state != state:
                    continue
            symbols.add(_require_instrument_field(item, "symbol").upper())
        return sorted(symbols)

    def _fetch_all_perp_instruments(self) -> list[dict[str, Any]]:
        """Paginate GET /instrument filtered to perpetual contracts."""
        import json as _json

        url = f"{self._base_url}{INSTRUMENT_ALL_ENDPOINT}"
        all_items: list[dict[str, Any]] = []
        seen: set[str] = set()
        start_idx = 0
        while True:
            params: dict[str, Any] = {
                "filter": _json.dumps({"typ": PERP_INSTRUMENT_TYP}),
                "count": _MAX_COUNT_PER_REQ,
                "start": start_idx,
                "reverse": "false",
            }
            page = self._fetch_instrument_page(url, params=params)
            if not page:
                break
            if len(page) > _MAX_COUNT_PER_REQ:
                raise BitMEXFundingError(
                    "instrument page exceeded the requested count",
                    context={"count": _MAX_COUNT_PER_REQ, "rows": len(page)},
                )
            new_on_page = 0
            for item in page:
                sym = _require_instrument_field(item, "symbol").upper()
                if sym not in seen:
                    seen.add(sym)
                    new_on_page += 1
            if new_on_page == 0:
                if len(page) >= _MAX_COUNT_PER_REQ:
                    raise BitMEXFundingError(
                        "BitMEX instrument pagination stalled with no progress",
                        context={"start": start_idx, "rows": len(page)},
                    )
                break
            all_items.extend(page)
            if len(page) < _MAX_COUNT_PER_REQ:
                break
            next_start = start_idx + len(page)
            if next_start <= start_idx:
                raise BitMEXFundingError(
                    "instrument pagination count did not advance",
                    context={"start": start_idx},
                )
            start_idx = next_start
        return all_items

    def _fetch_instrument_page(
        self,
        url: str,
        *,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        res = self._get(url, params)
        if not isinstance(res, list):
            raise BitMEXFundingError(
                "BitMEX instrument endpoint returned non-list response",
                context={"url": url, "response_type": type(res).__name__},
            )
        # Validate in place. Dropping malformed entries would shrink a full
        # page into a short terminal page.
        return [_validate_instrument_entry(item) for item in res]

    def _get(self, url: str, params: dict[str, Any]) -> Any:
        attempts = 0
        incident: dict[str, Any] | None = None
        while True:
            self._throttle()
            if self._client:
                r = self._client.get(url, params=params)
            else:
                with httpx.Client(timeout=self._timeout_s) as c:
                    r = c.get(url, params=params)

            if r.status_code == 429:
                attempts += 1
                retry_after_raw = r.headers.get("Retry-After")
                try:
                    sleep_s = (
                        float(retry_after_raw)
                        if retry_after_raw is not None and str(retry_after_raw).strip()
                        else _DEFAULT_429_SLEEP_S
                    )
                except (TypeError, ValueError):
                    sleep_s = _DEFAULT_429_SLEEP_S
                sleep_s = min(max(sleep_s, _DEFAULT_429_SLEEP_S), _MAX_429_SLEEP_S)
                if incident is None:
                    incident = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "url": url,
                        "status_code": 429,
                        "attempts": attempts,
                        "sleep_s": sleep_s,
                        "body": r.text[:300],
                    }
                    self.rate_limit_incidents.append(incident)
                else:
                    incident["attempts"] = attempts
                    incident["sleep_s"] = sleep_s
                if attempts > self._max_429_retries:
                    raise BitMEXFundingError(
                        f"BitMEX GET failed with HTTP 429 after {attempts} attempts",
                        context={"url": url, "status_code": 429, "body": r.text[:500]},
                    )
                time.sleep(sleep_s)
                continue

            if r.status_code != 200:
                raise BitMEXFundingError(
                    f"BitMEX GET failed with HTTP {r.status_code}",
                    context={"url": url, "status_code": r.status_code, "body": r.text[:500]},
                )
            return r.json()

    def _throttle(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_request_time = time.monotonic()


class BitMEXFundingProvider:
    """Point-in-time funding rate provider and cashflow calculation engine."""

    def __init__(self, table: pa.Table) -> None:
        if not isinstance(table, pa.Table):
            raise BitMEXFundingError(
                "table must be a PyArrow Table",
                context={"type": type(table).__name__},
            )
        validate_funding_history(table)
        self._table: pa.Table = table

    @classmethod
    def from_records(
        cls,
        records: Sequence[Mapping[str, Any]],
        *,
        availability_time: datetime | None = None,
    ) -> BitMEXFundingProvider:
        table = build_funding_table(records, availability_time=availability_time)
        return cls(table)

    @classmethod
    def from_parquet(cls, path: str | Path) -> BitMEXFundingProvider:
        p = Path(path)
        if not p.exists():
            raise BitMEXFundingError(f"Parquet file not found: {path}", context={"path": str(path)})
        table = pq.read_table(p)
        return cls(table)

    def get_funding_events(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        """Return all funding events for symbol in [start_time, end_time]."""
        st = _require_utc(start_time, field="start_time")
        et = _require_utc(end_time, field="end_time")
        st_us = _dt_to_us(st)
        et_us = _dt_to_us(et)

        sym = symbol.strip().upper()
        rows = self._table.to_pylist()

        events: list[dict[str, Any]] = []
        for r in rows:
            if str(r["symbol"]).upper() != sym:
                continue
            ts_us = int(r["timestamp_us"])
            if st_us <= ts_us <= et_us:
                events.append(dict(r))

        events.sort(key=lambda x: x["timestamp_us"])
        return events

    def compute_funding_cashflow(
        self,
        symbol: str,
        position_qty: float,
        start_time: datetime,
        end_time: datetime,
        *,
        pit_prices: Mapping[datetime | int, float] | None = None,
        is_inverse: bool = False,
        mark_price: float = 1.0,
    ) -> float:
        """Compute cumulative USD funding cashflow for a position over [start_time, end_time].

        Cashflow convention:
        - Long position (position_qty > 0) pays funding when rate > 0 (negative cashflow).
        - Short position (position_qty < 0) receives funding when rate > 0 (positive cashflow).
        - Linear contracts: cashflow_usd = -1.0 * position_qty * mark_price * funding_rate.
        - Inverse contracts: base payout is converted back to USD with the supplied price.
        """
        events = self.get_funding_events(symbol, start_time, end_time)
        if not events:
            return 0.0

        total_cashflow_usd = 0.0

        for ev in events:
            rate = float(ev["funding_rate"])
            ts_dt = parse_iso_datetime(ev["timestamp"]) or start_time

            price = mark_price
            if pit_prices:
                if ts_dt in pit_prices:
                    price = float(pit_prices[ts_dt])
                elif ev["timestamp_us"] in pit_prices:
                    price = float(pit_prices[ev["timestamp_us"]])

            if is_inverse or symbol.upper() == "XBTUSD":
                base_btc_payout = -1.0 * position_qty * rate / max(price, 1e-8)
                cashflow_usd = base_btc_payout * price
            else:
                cashflow_usd = -1.0 * position_qty * price * rate

            total_cashflow_usd += cashflow_usd

        return total_cashflow_usd
