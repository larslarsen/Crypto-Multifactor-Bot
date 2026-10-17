"""Offline bounded comparison of one-minute klines with accepted hourly products.

The acquisition module owns HTTP. This module only re-authenticates retained
sample bytes and the accepted bar and trade-flow partitions for the selected
symbol-months. It does not normalize, fill, or amend those products.
"""

from __future__ import annotations

import hashlib
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.acquisition import binance_usdm_kline_comparison_sample as sample
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    DECIMAL_PRECISION,
    DECIMAL_SCALE,
    PRODUCT_BAR_1H,
    PRODUCT_TRADE_FLOW_1H,
    QUALITY_GAP_COLUMNS,
    convert_decimal,
    convert_integer,
    final_product_schema,
    product_schema_identity,
)

REPORT_DOCUMENT = "cex002_bounded_kline_reconciliation_report"
COMPLETION_DOCUMENT = "cex002_bounded_kline_reconciliation_completion"
SCHEMA_VERSION = 1
SCOPE = "bounded_one_minute_hourly_sample_not_full_history"
MINUTE_MS = 60_000
MINUTE_CLOSE = 59_999
HOUR_MS = 3_600_000
HOUR_CLOSE = 3_599_999
DAY_MS = 86_400_000
SLOTS_PER_HOUR = 60
HOURS_PER_DAY = 24
PARTITION_ROW_CAP = 1024
QUALITY_ROW_CAP = 1024
PARTITION_BYTES = 8 * 2**20
QUALITY_BYTES = 8 * 2**20
MISSING_KIND = "missing_hour_run"
PROVIDER_KIND = "provider_invalid_required_fields"
BAR_GAP_REASON = "provider_inconsistent_total_volume_pair"
FLOW_GAP_REASON = "provider_inconsistent_trade_flow_required_volume"
MISSING_REASONS = ("within_object_missing_hour", "between_object_missing_hour")
PRODUCTS = (PRODUCT_BAR_1H, PRODUCT_TRADE_FLOW_1H)
PRODUCT_REASONS = {
    PRODUCT_BAR_1H: BAR_GAP_REASON,
    PRODUCT_TRADE_FLOW_1H: FLOW_GAP_REASON,
}
BAR_FIELDS = ("open", "high", "low", "close", "volume", "quote_volume", "trade_count")
FLOW_FIELDS = (
    "volume",
    "quote_volume",
    "taker_buy_volume",
    "taker_buy_quote_volume",
    "trade_count",
    "taker_sell_volume",
    "taker_sell_quote_volume",
    "volume_imbalance",
    "quote_volume_imbalance",
)
FIELDS = {PRODUCT_BAR_1H: BAR_FIELDS, PRODUCT_TRADE_FLOW_1H: FLOW_FIELDS}
DERIVED_FIELDS = {
    "taker_sell_volume": ("volume", "taker_buy_volume"),
    "taker_sell_quote_volume": ("quote_volume", "taker_buy_quote_volume"),
    "volume_imbalance": ("volume", "taker_buy_volume"),
    "quote_volume_imbalance": ("quote_volume", "taker_buy_quote_volume"),
}
TOKEN_INDEX = {
    "open": 1,
    "high": 2,
    "low": 3,
    "close": 4,
    "volume": 5,
    "quote_volume": 7,
    "trade_count": 8,
    "taker_buy_volume": 9,
    "taker_buy_quote_volume": 10,
}
DECIMAL_INDEXES = (
    ("open", 1),
    ("high", 2),
    ("low", 3),
    ("close", 4),
    ("volume", 5),
    ("quote_volume", 7),
    ("taker_buy_volume", 9),
    ("taker_buy_quote_volume", 10),
)
ARITHMETIC_POLICY = {
    "ambient_context": "ignored",
    "binary_float": "forbidden",
    "close": "last",
    "decimal_precision": DECIMAL_PRECISION,
    "decimal_scale": DECIMAL_SCALE,
    "high": "maximum",
    "imbalance_ratio": "not_used",
    "low": "minimum",
    "missing_slot": "explicit_uncomparable_never_filled",
    "open": "first",
    "quote_volume": "sum",
    "quote_volume_imbalance": "buy_minus_sell",
    "representation": "exact_unscaled_integer",
    "taker_buy_quote_volume": "sum",
    "taker_buy_volume": "sum",
    "taker_sell_quote_volume": "total_minus_buy",
    "taker_sell_volume": "total_minus_buy",
    "trade_count": "integer_sum",
    "volume": "sum",
    "volume_imbalance": "buy_minus_sell",
}
_SCALE_BOUND = 10**DECIMAL_PRECISION
_REPO = Path(__file__).resolve().parents[3]
_CLI = _REPO / "scripts" / "research" / "reconcile_binance_usdm_klines.py"
_GAP_SCHEMA = pa.schema([column.field() for column in QUALITY_GAP_COLUMNS])
_PRODUCT_SCHEMA = {product: final_product_schema(product) for product in PRODUCTS}
_SCHEMA_SHA = {product: product_schema_identity(product) for product in PRODUCTS}


class ReconciliationError(RuntimeError):
    """Fail-closed comparison input or publication error."""


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    status: str
    report_sha256: str
    report_path: Path
    completion_sha256: str | None
    completion_path: Path | None
    report_reused: bool
    completion_reused: bool


@dataclass(frozen=True, slots=True)
class _Minute:
    ordinal: int
    open_time: int
    tokens: tuple[str, ...]
    numbers: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class _DayParts:
    parsed_rows: int
    identical_duplicates: int
    compared_primary_rows: int
    uncomparable_rows: int
    comparable: tuple[tuple[int, tuple[_Minute, ...]], ...]
    hours: tuple[tuple[int, int, str], ...]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconciliationError(message)


def _as_int(value: Any, message: str) -> int:
    _require(type(value) is int, message)
    return value


def _unscaled(value: Decimal) -> int:
    _require(isinstance(value, Decimal), "product decimal is invalid")
    sign, digits, exponent = value.as_tuple()
    _require(exponent == -DECIMAL_SCALE, "product decimal is not at the pinned scale")
    magnitude = 0
    for digit in digits:
        magnitude = magnitude * 10 + int(digit)
    _require(magnitude < _SCALE_BOUND, "product decimal overflows pinned precision")
    return -magnitude if sign else magnitude


def _checked_sum(values: Sequence[int]) -> int:
    total = 0
    for value in values:
        total += value
    _require(abs(total) < _SCALE_BOUND, "aggregated decimal overflows pinned precision")
    return total


def _minute_int(token: str, key: str, column: str, row: int) -> int:
    try:
        return convert_integer(token, key=key, output=REPORT_DOCUMENT, column=column, row=row)
    except Exception as exc:
        raise ReconciliationError(f"minute {column} is not an exact integer") from exc


def _minute_decimal(token: str, key: str, column: str, row: int) -> int:
    try:
        value = convert_decimal(token, key=key, output=REPORT_DOCUMENT, column=column, row=row)
    except Exception as exc:
        raise ReconciliationError(f"minute {column} is not an exact decimal") from exc
    return _unscaled(value)


def _parse_minute(
    tokens: tuple[str, ...],
    ordinal: int,
    key: str,
    day_start: int,
    day_end: int,
) -> _Minute:
    _require(len(tokens) == len(sample.MINUTE_FIELDS), "minute CSV row width is invalid")
    open_time = _minute_int(tokens[0], key, "open_time", ordinal)
    close_time = _minute_int(tokens[6], key, "close_time", ordinal)
    count = _minute_int(tokens[8], key, "count", ordinal)
    ignore = _minute_int(tokens[11], key, "ignore", ordinal)
    if min(open_time, close_time, count, ignore) < 0:
        raise ReconciliationError("minute value is negative")
    if open_time % MINUTE_MS != 0:
        raise ReconciliationError("minute open_time is not a UTC minute")
    if close_time != open_time + MINUTE_CLOSE:
        raise ReconciliationError("minute close_time is not aligned")
    if open_time < day_start or open_time >= day_end:
        raise ReconciliationError("minute row is outside its UTC day")
    numbers: dict[str, int] = {}
    for name, index in DECIMAL_INDEXES:
        numbers[name] = _minute_decimal(tokens[index], key, name, ordinal)
        if numbers[name] < 0:
            raise ReconciliationError("minute value is negative")
    high = numbers["high"]
    low = numbers["low"]
    if high < max(numbers["open"], numbers["close"], low):
        raise ReconciliationError("minute OHLC ordering is invalid")
    if low > min(numbers["open"], numbers["close"], high):
        raise ReconciliationError("minute OHLC ordering is invalid")
    if numbers["taker_buy_volume"] > numbers["volume"]:
        raise ReconciliationError("taker volume exceeds its total")
    if numbers["taker_buy_quote_volume"] > numbers["quote_volume"]:
        raise ReconciliationError("taker volume exceeds its total")
    numbers["count"] = count
    numbers["ignore"] = ignore
    return _Minute(ordinal, open_time, tokens, numbers)


def _aggregate_day(rows: Sequence[tuple[str, ...]], utc_date: str, key: str) -> _DayParts:
    day_start = sample.utc_day_start_ms(utc_date)
    parsed = [
        _parse_minute(tuple(row), ordinal, key, day_start, day_start + DAY_MS)
        for ordinal, row in enumerate(rows)
    ]
    grouped: dict[int, list[_Minute]] = {}
    for minute in parsed:
        grouped.setdefault(minute.open_time, []).append(minute)
    identical = 0
    primaries: list[_Minute] = []
    for open_time in sorted(grouped):
        group = sorted(grouped[open_time], key=lambda item: item.ordinal)
        if len({item.tokens for item in group}) != 1:
            raise ReconciliationError("conflicting minute tokens")
        primaries.append(group[0])
        identical += len(group) - 1
    by_hour: dict[int, list[_Minute]] = {}
    for minute in primaries:
        hour = minute.open_time - (minute.open_time % HOUR_MS)
        by_hour.setdefault(hour, []).append(minute)
    expected_hours = tuple(day_start + index * HOUR_MS for index in range(HOURS_PER_DAY))
    allowed = set(expected_hours)
    for hour in by_hour:
        _require(hour in allowed, "minute hour is outside its UTC day")
    comparable: list[tuple[int, tuple[_Minute, ...]]] = []
    uncomparable_rows = 0
    compared_primary = 0
    hours: list[tuple[int, int, str]] = []
    for hour in expected_hours:
        slots = tuple(sorted(by_hour.get(hour, ()), key=lambda item: item.open_time))
        expected_slots = tuple(hour + index * MINUTE_MS for index in range(SLOTS_PER_HOUR))
        observed = len(slots)
        if observed == 0:
            hours.append((hour, 0, "zero_observation"))
            continue
        if tuple(slot.open_time for slot in slots) != expected_slots:
            uncomparable_rows += observed
            hours.append((hour, observed, "partial"))
            continue
        comparable.append((hour, slots))
        compared_primary += observed
        hours.append((hour, observed, "complete"))
    return _DayParts(
        len(parsed),
        identical,
        compared_primary,
        uncomparable_rows,
        tuple(comparable),
        tuple(hours),
    )


def _aggregate_numbers(slots: Sequence[_Minute]) -> dict[str, int]:
    # Sell is total minus buy. Imbalance is buy minus sell, not a ratio.
    numbers = {
        "open": slots[0].numbers["open"],
        "high": max(slot.numbers["high"] for slot in slots),
        "low": min(slot.numbers["low"] for slot in slots),
        "close": slots[-1].numbers["close"],
        "volume": _checked_sum([slot.numbers["volume"] for slot in slots]),
        "quote_volume": _checked_sum([slot.numbers["quote_volume"] for slot in slots]),
        "trade_count": _checked_sum([slot.numbers["count"] for slot in slots]),
        "taker_buy_volume": _checked_sum([slot.numbers["taker_buy_volume"] for slot in slots]),
        "taker_buy_quote_volume": _checked_sum(
            [slot.numbers["taker_buy_quote_volume"] for slot in slots]
        ),
    }
    numbers["taker_sell_volume"] = numbers["volume"] - numbers["taker_buy_volume"]
    numbers["taker_sell_quote_volume"] = (
        numbers["quote_volume"] - numbers["taker_buy_quote_volume"]
    )
    numbers["volume_imbalance"] = numbers["taker_buy_volume"] - numbers["taker_sell_volume"]
    numbers["quote_volume_imbalance"] = (
        numbers["taker_buy_quote_volume"] - numbers["taker_sell_quote_volume"]
    )
    for value in numbers.values():
        _require(abs(value) < _SCALE_BOUND, "aggregated decimal overflows pinned precision")
    return numbers


def _child(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    _require(
        bool(relative) and not path.is_absolute() and ".." not in path.parts and "\\" not in relative,
        "product evidence path escapes its root",
    )
    return sample.lexical_path(root / Path(*path.parts))


def _hex(value: Any, message: str) -> str:
    _require(type(value) is str and len(value) == 64 and value.lower() == value, message)
    _require(all(character in "0123456789abcdef" for character in value), message)
    return value


def _parquet_rows(body: bytes, schema: pa.Schema, cap: int, message: str) -> list[dict[str, Any]]:
    try:
        parquet = pq.ParquetFile(io.BytesIO(body))
        matches = parquet.schema_arrow.equals(schema, check_metadata=False)
    except ReconciliationError:
        raise
    except Exception as exc:
        raise ReconciliationError("parquet evidence is unreadable") from exc
    _require(matches, message)
    rows: list[dict[str, Any]] = []
    total = 0
    for batch in parquet.iter_batches(batch_size=256):
        total += batch.num_rows
        _require(total <= cap, "parquet evidence exceeds its row bound")
        rows.extend(batch.to_pylist())
    _require(len(rows) == total, "parquet evidence is unreadable")
    return rows


def _schema_facts(schema: pa.Schema) -> list[dict[str, Any]]:
    return [
        {"name": field.name, "nullable": field.nullable, "type": str(field.type)}
        for field in schema
    ]


def _load_completion(policy: sample.Policy, product: str, relative: str, pinned: str) -> tuple[Path, dict[str, Any]]:
    root = sample.lexical_path(policy.repo / relative)
    names = sample.list_regular(root, ".complete", limit=8)
    if not names:
        raise ReconciliationError("product completion is missing")
    _require(len(names) == 1, "product completion is not the sole marker")
    body = sample.read_regular(root / ".complete" / names[0], sample.AUTHORITY_JSON_BYTES)
    digest = sample.sha256_hex(body)
    _require(names[0] == f"{digest}.json", "product completion name does not match its bytes")
    _require(digest == pinned, "product completion digest mismatch")
    document = sample.parse_json_object(body, limit=sample.AUTHORITY_JSON_BYTES)
    _require(document.get("document_type") == f"{product}_product_completion", "product completion identity mismatch")
    _require(document.get("schema_version") == 2, "product completion identity mismatch")
    _require(document.get("required_product") == product, "product completion identity mismatch")
    _require(document.get("schema_sha256") == _SCHEMA_SHA[product], "product schema identity mismatch")
    return root, document


def _selected_facts(document: Mapping[str, Any], wanted: set[tuple[str, str]]) -> dict[tuple[str, str], dict[str, Any]]:
    partitions = document.get("partitions")
    _require(type(partitions) is list, "product completion identity mismatch")
    assert type(partitions) is list
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for fact in partitions:
        _require(type(fact) is dict, "product completion identity mismatch")
        assert type(fact) is dict
        key = (fact.get("native_symbol"), fact.get("utc_month"))
        if key not in wanted:
            continue
        _require(key not in found, "duplicate product partition")
        found[key] = fact
    _require(set(found) == wanted, "selected partition is missing")
    return found


def _validate_raw_objects(raw_objects: Any) -> None:
    _require(type(raw_objects) is list and bool(raw_objects), "partition lineage mismatch")
    assert type(raw_objects) is list
    for item in raw_objects:
        _require(type(item) is dict, "partition lineage mismatch")
        assert type(item) is dict
        _require(item.get("source_available_at") is None, "partition lineage mismatch")
        _require(
            item.get("source_availability_state") == sample.UNKNOWN_AVAILABILITY,
            "partition lineage mismatch",
        )


def _day_ranges(retained: Sequence[sample.RetainedObject]) -> dict[str, tuple[tuple[int, int, str], ...]]:
    grouped: dict[str, list[tuple[int, int, str]]] = {}
    for item in retained:
        start = sample.utc_day_start_ms(item.utc_date)
        _require(sample.utc_year_month(start) == item.utc_date[:7], "sample date month disagrees")
        grouped.setdefault(item.symbol, []).append((start, start + DAY_MS, item.utc_date))
    return {symbol: tuple(ranges) for symbol, ranges in grouped.items()}


def _owned_day(ranges: Sequence[tuple[int, int, str]], open_time: int) -> str | None:
    for start, end, utc_date in ranges:
        if start <= open_time < end:
            return utc_date
    return None


def _product_unscaled(field: str, value: Any) -> int:
    if field == "trade_count":
        _require(type(value) is int and value >= 0, "product trade_count is invalid")
        return value
    return _unscaled(value)


def _keep_partition_rows(
    rows: Sequence[Mapping[str, Any]],
    symbol: str,
    ranges: Sequence[tuple[int, int, str]],
) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in rows:
        _require(row.get("venue_symbol") == symbol, "partition row symbol is invalid")
        _require(row.get("native_symbol") == symbol, "partition row symbol is invalid")
        open_time = _as_int(row.get("open_time"), "partition row open_time is invalid")
        close_time = _as_int(row.get("close_time"), "partition row close_time is invalid")
        _require(open_time >= 0 and open_time % HOUR_MS == 0, "partition row open_time is invalid")
        if open_time in seen:
            raise ReconciliationError("duplicate product open_time")
        seen.add(open_time)
        owned = _owned_day(ranges, open_time)
        if owned is None:
            _require(close_time == open_time + HOUR_CLOSE, "partition row close_time is invalid")
            continue
        kept.append(dict(row))
    return kept


def _read_named(root: Path, relative: Any, digest: str, suffix: str, limit: int, message: str) -> bytes:
    _require(type(relative) is str and relative.endswith(f"{digest}{suffix}"), message)
    body = sample.read_regular(_child(root, relative), limit)
    _require(sample.sha256_hex(body) == digest, message)
    return body


def _load_partition(
    root: Path,
    product: str,
    fact: Mapping[str, Any],
    ranges: Sequence[tuple[int, int, str]],
) -> list[dict[str, Any]]:
    symbol = fact.get("native_symbol")
    month = fact.get("utc_month")
    _require(type(symbol) is str and type(month) is str, "selected partition is missing")
    assert type(symbol) is str
    row_count = _as_int(fact.get("row_count"), "partition lineage mismatch")
    _require(0 <= row_count <= PARTITION_ROW_CAP, "partition lineage mismatch")
    parquet_sha = _hex(fact.get("parquet_sha256"), "partition parquet digest mismatch")
    lineage_sha = _hex(fact.get("lineage_sha256"), "partition lineage mismatch")
    body = _read_named(
        root,
        fact.get("parquet_path"),
        parquet_sha,
        ".parquet",
        PARTITION_BYTES,
        "partition parquet digest mismatch",
    )
    rows = _parquet_rows(body, _PRODUCT_SCHEMA[product], PARTITION_ROW_CAP, "partition schema mismatch")
    _require(len(rows) == row_count, "partition lineage mismatch")
    lineage_body = _read_named(
        root,
        fact.get("lineage_path"),
        lineage_sha,
        ".json",
        sample.AUTHORITY_JSON_BYTES,
        "partition lineage mismatch",
    )
    lineage = sample.parse_json_object(lineage_body, limit=sample.AUTHORITY_JSON_BYTES)
    _require(lineage.get("document_type") == f"{product}_partition_lineage", "partition lineage mismatch")
    _require(lineage.get("schema_version") == 2, "partition lineage mismatch")
    _require(lineage.get("required_product") == product, "partition lineage mismatch")
    _require(lineage.get("native_symbol") == symbol, "partition lineage mismatch")
    _require(lineage.get("utc_month") == month, "partition lineage mismatch")
    _require(lineage.get("row_count") == row_count, "partition lineage mismatch")
    _require(lineage.get("schema_sha256") == _SCHEMA_SHA[product], "partition lineage mismatch")
    _require(lineage.get("parquet_sha256") == parquet_sha, "partition lineage mismatch")
    _validate_raw_objects(lineage.get("raw_objects"))
    return _keep_partition_rows(rows, symbol, ranges)


def _validate_gap_row(row: Mapping[str, Any], product: str) -> None:
    _require(row.get("required_product") == product, "quality gap product identity")
    for key in ("native_symbol", "utc_month", "gap_kind", "reason"):
        _require(type(row.get(key)) is str and bool(row.get(key)), "quality gap row is invalid")
    start = _as_int(row.get("missing_run_start_ms"), "quality gap interval is invalid")
    end = _as_int(row.get("missing_run_end_ms"), "quality gap interval is invalid")
    count = _as_int(row.get("expected_grid_count"), "quality gap interval is invalid")
    _require(start >= 0 and end >= start, "quality gap interval is invalid")
    _require(start % HOUR_MS == 0 and end % HOUR_MS == 0, "quality gap interval is invalid")
    start_month = sample.utc_year_month(start)
    _require(sample.utc_year_month(end) == start_month, "quality gap row crosses a UTC month")
    _require(row.get("utc_month") == start_month, "quality gap row crosses a UTC month")
    _require(count == (end - start) // HOUR_MS + 1, "quality gap interval is invalid")


def _exclusion_sha(rows: Sequence[Mapping[str, Any]]) -> str:
    hasher = hashlib.sha256()
    for row in rows:
        hasher.update(sample.canonical_json(row))
    return hasher.hexdigest()


def _load_gaps(
    root: Path,
    product: str,
    artifact: Mapping[str, Any],
) -> tuple[tuple[dict[str, Any], ...], set[tuple[str, str, int, str]], dict[str, str]]:
    row_count = _as_int(artifact.get("row_count"), "quality gap lineage mismatch")
    missing = _as_int(artifact.get("missing_grid_points"), "quality gap lineage mismatch")
    _require(0 <= row_count <= QUALITY_ROW_CAP, "quality gap lineage mismatch")
    parquet_sha = _hex(artifact.get("parquet_sha256"), "quality gap digest mismatch")
    lineage_sha = _hex(artifact.get("lineage_sha256"), "quality gap lineage mismatch")
    body = _read_named(
        root,
        artifact.get("parquet_path"),
        parquet_sha,
        ".parquet",
        QUALITY_BYTES,
        "quality gap digest mismatch",
    )
    rows = _parquet_rows(body, _GAP_SCHEMA, QUALITY_ROW_CAP, "quality gap schema mismatch")
    _require(len(rows) == row_count, "quality gap lineage mismatch")
    for row in rows:
        _validate_gap_row(row, product)
    _require(sum(int(row["expected_grid_count"]) for row in rows) == missing, "quality gap lineage mismatch")
    lineage_body = _read_named(
        root,
        artifact.get("lineage_path"),
        lineage_sha,
        ".json",
        sample.AUTHORITY_JSON_BYTES,
        "quality gap lineage mismatch",
    )
    lineage = sample.parse_json_object(lineage_body, limit=sample.AUTHORITY_JSON_BYTES)
    _require(lineage.get("document_type") == f"{product}_quality_gap_lineage", "quality gap lineage mismatch")
    _require(lineage.get("schema_version") == 2, "quality gap lineage mismatch")
    _require(lineage.get("required_product") == product, "quality gap lineage mismatch")
    _require(lineage.get("row_count") == row_count, "quality gap lineage mismatch")
    _require(lineage.get("missing_grid_points") == missing, "quality gap lineage mismatch")
    _require(lineage.get("quality_gap_parquet_sha256") == parquet_sha, "quality gap lineage mismatch")
    _require(lineage.get("quality_gap_schema") == _schema_facts(_GAP_SCHEMA), "quality gap lineage mismatch")
    exclusions = lineage.get("provider_invalid_exclusions")
    _require(type(exclusions) is list, "quality gap lineage mismatch")
    assert type(exclusions) is list
    _require(len(exclusions) <= QUALITY_ROW_CAP, "quality gap lineage exceeds its bound")
    _require(lineage.get("provider_invalid_exclusion_count") == len(exclusions), "quality gap lineage mismatch")
    keys: set[tuple[str, str, int, str]] = set()
    for item in exclusions:
        _require(type(item) is dict, "quality gap lineage mismatch")
        assert type(item) is dict
        _require(item.get("required_product") == product, "quality exclusion product identity")
        symbol = item.get("native_symbol")
        reason = item.get("reason")
        _require(type(symbol) is str and type(reason) is str, "quality exclusion is invalid")
        assert type(symbol) is str and type(reason) is str
        open_time = _as_int(item.get("open_time"), "quality exclusion is invalid")
        keys.add((product, symbol, open_time, reason))
    digest = _hex(lineage.get("provider_invalid_exclusions_sha256"), "quality gap lineage mismatch")
    _require(digest == _exclusion_sha(exclusions), "quality gap lineage mismatch")
    proof = {
        "provider_invalid_exclusions_sha256": digest,
        "quality_gap_lineage_sha256": lineage_sha,
        "quality_gap_parquet_sha256": parquet_sha,
    }
    return tuple(dict(row) for row in rows), keys, proof


def _covers(gap: Mapping[str, Any], symbol: str, hour: int, month: str) -> bool:
    if gap["native_symbol"] != symbol or gap["utc_month"] != month:
        return False
    return int(gap["missing_run_start_ms"]) <= hour <= int(gap["missing_run_end_ms"])


def _explaining_gap(
    product: str,
    symbol: str,
    hour: int,
    covering: Sequence[Mapping[str, Any]],
    exclusions: set[tuple[str, str, int, str]],
) -> Mapping[str, Any] | None:
    for gap in covering:
        kind = str(gap["gap_kind"])
        reason = str(gap["reason"])
        if kind == MISSING_KIND and reason in MISSING_REASONS:
            return gap
        if kind != PROVIDER_KIND or reason != PRODUCT_REASONS[product]:
            continue
        if (product, symbol, hour, reason) in exclusions:
            return gap
    return None


def _skip_record(
    product: str,
    symbol: str,
    utc_date: str,
    hour: int,
    gap: Mapping[str, Any],
    proof: Mapping[str, str],
) -> dict[str, Any]:
    reason = str(gap["reason"])
    return {
        "close_time": hour + HOUR_CLOSE,
        "gap_proof": {
            "exclusion_matched": str(gap["gap_kind"]) == PROVIDER_KIND,
            "expected_grid_count": int(gap["expected_grid_count"]),
            "gap_kind": str(gap["gap_kind"]),
            "missing_run_end_ms": int(gap["missing_run_end_ms"]),
            "missing_run_start_ms": int(gap["missing_run_start_ms"]),
            "native_symbol": str(gap["native_symbol"]),
            "provider_invalid_exclusions_sha256": proof["provider_invalid_exclusions_sha256"],
            "quality_gap_lineage_sha256": proof["quality_gap_lineage_sha256"],
            "quality_gap_parquet_sha256": proof["quality_gap_parquet_sha256"],
            "reason": reason,
            "required_product": product,
            "utc_month": str(gap["utc_month"]),
        },
        "kind": "skipped_product_hour",
        "open_time": hour,
        "product": product,
        "reason": reason,
        "symbol": symbol,
        "utc_date": utc_date,
    }


def _field_tokens(slots: Sequence[_Minute], field: str) -> list[str]:
    index = TOKEN_INDEX[field]
    return [slot.tokens[index] for slot in slots]


def _derived_inputs(slots: Sequence[_Minute], field: str) -> dict[str, list[str]] | None:
    parts = DERIVED_FIELDS.get(field)
    if parts is None:
        return None
    return {name: _field_tokens(slots, name) for name in parts}


def _compare_hour(
    product: str,
    symbol: str,
    utc_date: str,
    hour: int,
    slots: Sequence[_Minute],
    aggregated: Mapping[str, int],
    row: Mapping[str, Any] | None,
    covering: Sequence[Mapping[str, Any]],
    exclusions: set[tuple[str, str, int, str]],
    proof: Mapping[str, str],
) -> tuple[bool, list[dict[str, Any]], list[dict[str, Any]], dict[str, bool], dict[str, Any] | None]:
    discrepancies: list[dict[str, Any]] = []
    unexplained: list[dict[str, Any]] = []
    if row is None:
        gap = _explaining_gap(product, symbol, hour, covering, exclusions)
        if gap is not None:
            return False, discrepancies, unexplained, {}, _skip_record(
                product, symbol, utc_date, hour, gap, proof
            )
        unexplained.append(
            {
                "close_time": hour + HOUR_CLOSE,
                "kind": "unexplained_absence",
                "open_time": hour,
                "product": product,
                "symbol": symbol,
                "utc_date": utc_date,
            }
        )
        return False, discrepancies, unexplained, {}, None
    matched = True
    close_time = _as_int(row.get("close_time"), "product close_time is invalid")
    if close_time != hour + HOUR_CLOSE:
        matched = False
        discrepancies.append(
            {
                "expected_close_time": hour + HOUR_CLOSE,
                "kind": "close_time_mismatch",
                "open_time": hour,
                "product": product,
                "product_close_time": close_time,
                "symbol": symbol,
                "utc_date": utc_date,
            }
        )
    field_results: dict[str, bool] = {}
    for field in FIELDS[product]:
        actual = _product_unscaled(field, row.get(field))
        expected_value = aggregated[field]
        field_results[field] = actual == expected_value
        if field_results[field]:
            continue
        matched = False
        expected = expected_value
        record = {
            "aggregated_unscaled": str(expected),
            "close_time": hour + HOUR_CLOSE,
            "derived_inputs": _derived_inputs(slots, field),
            "field": field,
            "kind": "field_mismatch",
            "open_time": hour,
            "product": product,
            "product_unscaled": str(actual),
            "source_ordinals": [slot.ordinal for slot in slots],
            "source_tokens": None if field in DERIVED_FIELDS else _field_tokens(slots, field),
            "symbol": symbol,
            "utc_date": utc_date,
        }
        discrepancies.append(record)
    if covering:
        matched = False
        discrepancies.append(
            {
                "close_time": hour + HOUR_CLOSE,
                "kind": "accepted_row_overlaps_quality_gap",
                "open_time": hour,
                "product": product,
                "symbol": symbol,
                "utc_date": utc_date,
            }
        )
    return matched, discrepancies, unexplained, field_results, None


def _code_identity() -> dict[str, str]:
    paths = {
        "acquisition_sha256": Path(sample.__file__).resolve(),
        "cli_sha256": _CLI,
        "reconciliation_sha256": Path(__file__).resolve(),
    }
    identity: dict[str, str] = {}
    for name, path in paths.items():
        _require(path.is_file(), "reconciliation code identity is unavailable")
        identity[name] = sample.sha256_hex(path.read_bytes())
    return identity


def _config_sha(policy: sample.Policy) -> str:
    config = {
        "arithmetic_policy": ARITHMETIC_POLICY,
        "bar_completion_sha256": policy.bar_completion,
        "bar_schema_sha256": _SCHEMA_SHA[PRODUCT_BAR_1H],
        "flow_completion_sha256": policy.flow_completion,
        "flow_schema_sha256": _SCHEMA_SHA[PRODUCT_TRADE_FLOW_1H],
        "qualification_report_sha256": policy.report_sha256,
        "roles": [
            [role.symbol, role.utc_date, role.regime]
            for role in sorted(policy.roles, key=lambda item: (item.symbol, item.utc_date, item.regime))
        ],
    }
    return sample.sha256_hex(sample.canonical_json(config))


def _record_sort(item: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(item.get("kind", "")),
        str(item.get("product", "")),
        str(item.get("symbol", "")),
        str(item.get("utc_date", "")),
        int(item["open_time"]) if "open_time" in item else -1,
        str(item.get("field", "")),
        str(item.get("role", "")),
    )


def _load_products(
    policy: sample.Policy,
    retained: Sequence[sample.RetainedObject],
) -> tuple[dict[tuple[str, str, int], dict[str, Any]], dict[str, tuple[dict[str, Any], ...]], dict[str, set[tuple[str, str, int, str]]], dict[str, dict[str, str]]]:
    ranges = _day_ranges(retained)
    wanted = {(item.symbol, item.utc_date[:7]) for item in retained}
    pinned = {
        PRODUCT_BAR_1H: (policy.bar_root, policy.bar_completion),
        PRODUCT_TRADE_FLOW_1H: (policy.flow_root, policy.flow_completion),
    }
    rows: dict[tuple[str, str, int], dict[str, Any]] = {}
    gaps: dict[str, tuple[dict[str, Any], ...]] = {}
    exclusions: dict[str, set[tuple[str, str, int, str]]] = {}
    proofs: dict[str, dict[str, str]] = {}
    for product in PRODUCTS:
        relative, digest = pinned[product]
        root, document = _load_completion(policy, product, relative, digest)
        facts = _selected_facts(document, wanted)
        artifact = document.get("quality_gap_artifact")
        _require(type(artifact) is dict, "quality gap lineage mismatch")
        assert type(artifact) is dict
        for key in sorted(wanted):
            symbol, _month = key
            kept = _load_partition(root, product, facts[key], ranges.get(symbol, ()))
            for row in kept:
                open_time = int(row["open_time"])
                identity = (product, symbol, open_time)
                _require(identity not in rows, "duplicate product open_time")
                rows[identity] = row
            del kept
        gap_rows, keys, proof = _load_gaps(root, product, artifact)
        gaps[product] = gap_rows
        exclusions[product] = keys
        proofs[product] = proof
        del document
    return rows, gaps, exclusions, proofs


def _compare(
    policy: sample.Policy,
    loaded: sample.LoadedSample,
    evidence: Path,
) -> dict[str, Any]:
    product_rows, gaps, exclusions, proofs = _load_products(policy, loaded.objects)
    days: list[dict[str, Any]] = []
    discrepancies: list[dict[str, Any]] = []
    unexplained: list[dict[str, Any]] = []
    uncomparable: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    coverage_failures: list[dict[str, Any]] = []
    per_product = {
        product: {
            "fields": {
                field: {"denominator": 0, "matched": 0} for field in FIELDS[product]
            },
            "skipped_hour_count": 0,
            "successfully_compared_hour_count": 0,
        }
        for product in PRODUCTS
    }
    totals = {
        "compared_primary_rows": 0,
        "field_denominator": 0,
        "identical_duplicate_rows": 0,
        "matched_field_count": 0,
        "parsed_rows": 0,
        "uncomparable_rows": 0,
    }
    comparable_hours = 0
    success_hours = 0
    uncomparable_hour_count = 0
    covered_roles = 0
    observed_slot_total = 0
    partial_total = 0
    zero_total = 0
    for retained_day in loaded.objects:
        minute_rows = sample.read_retained_rows(policy, evidence, retained_day)
        parts = _aggregate_day(minute_rows, retained_day.utc_date, retained_day.comparison_key)
        del minute_rows
        month = retained_day.utc_date[:7]
        day_matched = 0
        day_denominator = 0
        day_success = 0
        for hour, slots in parts.comparable:
            comparable_hours += 1
            aggregated = _aggregate_numbers(slots)
            hour_matched_products = 0
            hour_ok = True
            for product in PRODUCTS:
                covering = tuple(
                    gap
                    for gap in gaps[product]
                    if _covers(gap, retained_day.symbol, hour, month)
                )
                matched, found, missing, field_results, skip = _compare_hour(
                    product,
                    retained_day.symbol,
                    retained_day.utc_date,
                    hour,
                    slots,
                    aggregated,
                    product_rows.get((product, retained_day.symbol, hour)),
                    covering,
                    exclusions[product],
                    proofs[product],
                )
                discrepancies.extend(found)
                unexplained.extend(missing)
                if skip is not None:
                    skipped.append(skip)
                    per_product[product]["skipped_hour_count"] += 1
                for field_name, field_ok in field_results.items():
                    bucket = per_product[product]["fields"][field_name]
                    bucket["denominator"] += 1
                    if field_ok:
                        bucket["matched"] += 1
                day_matched += sum(1 for field_ok in field_results.values() if field_ok)
                day_denominator += len(field_results)
                if matched:
                    per_product[product]["successfully_compared_hour_count"] += 1
                    hour_matched_products += 1
                elif missing or found:
                    hour_ok = False
            if hour_ok and hour_matched_products >= 1:
                day_success += 1
                success_hours += 1
        observed_slots = 0
        partial_hours = 0
        zero_hours = 0
        for open_time, observed, coverage in parts.hours:
            observed_slots += observed
            if coverage == "partial":
                partial_hours += 1
            elif coverage == "zero_observation":
                zero_hours += 1
            if coverage == "complete":
                continue
            uncomparable.append(
                {
                    "coverage": coverage,
                    "expected_slots": SLOTS_PER_HOUR,
                    "observed_slots": observed,
                    "open_time": open_time,
                    "symbol": retained_day.symbol,
                    "utc_date": retained_day.utc_date,
                }
            )
        uncomparable_hour_count += partial_hours + zero_hours
        observed_slot_total += observed_slots
        partial_total += partial_hours
        zero_total += zero_hours
        if day_success == 0:
            coverage_failures.append(
                {
                    "kind": "day_without_compared_hour",
                    "roles": list(retained_day.roles),
                    "symbol": retained_day.symbol,
                    "utc_date": retained_day.utc_date,
                }
            )
            for role in retained_day.roles:
                coverage_failures.append(
                    {
                        "kind": "role_without_compared_hour",
                        "role": role,
                        "symbol": retained_day.symbol,
                        "utc_date": retained_day.utc_date,
                    }
                )
        else:
            covered_roles += len(retained_day.roles)
        totals["parsed_rows"] += parts.parsed_rows
        totals["compared_primary_rows"] += parts.compared_primary_rows
        totals["identical_duplicate_rows"] += parts.identical_duplicates
        totals["uncomparable_rows"] += parts.uncomparable_rows
        totals["matched_field_count"] += day_matched
        totals["field_denominator"] += day_denominator
        identity = (
            parts.compared_primary_rows + parts.identical_duplicates + parts.uncomparable_rows
        )
        _require(identity == parts.parsed_rows, "minute accounting identity failed")
        days.append(
            {
                "comparable_hour_count": len(parts.comparable),
                "compared_primary_rows": parts.compared_primary_rows,
                "expected_hour_count": HOURS_PER_DAY,
                "expected_slot_count": HOURS_PER_DAY * SLOTS_PER_HOUR,
                "field_denominator": day_denominator,
                "hours": [
                    {
                        "coverage": coverage,
                        "expected_slots": SLOTS_PER_HOUR,
                        "observed_slots": observed,
                        "open_time": open_time,
                    }
                    for open_time, observed, coverage in parts.hours
                ],
                "identical_duplicate_rows": parts.identical_duplicates,
                "matched_field_count": day_matched,
                "observed_slot_count": observed_slots,
                "parsed_rows": parts.parsed_rows,
                "roles": list(retained_day.roles),
                "successfully_compared_hour_count": day_success,
                "symbol": retained_day.symbol,
                "uncomparable_hour_count": partial_hours + zero_hours,
                "uncomparable_rows": parts.uncomparable_rows,
                "utc_date": retained_day.utc_date,
            }
        )
    grand = (
        totals["compared_primary_rows"]
        + totals["identical_duplicate_rows"]
        + totals["uncomparable_rows"]
    )
    _require(grand == totals["parsed_rows"], "minute accounting identity failed")
    logical_roles = sum(len(item.roles) for item in loaded.objects)
    failed = bool(discrepancies or unexplained or coverage_failures or success_hours < 1)
    report = {
        "accounting": {
            "compared_primary_rows": totals["compared_primary_rows"],
            "identical_duplicate_rows": totals["identical_duplicate_rows"],
            "parsed_rows": totals["parsed_rows"],
            "uncomparable_rows": totals["uncomparable_rows"],
        },
        "arithmetic_policy": ARITHMETIC_POLICY,
        "bar_completion_sha256": policy.bar_completion,
        "bar_schema_sha256": _SCHEMA_SHA[PRODUCT_BAR_1H],
        "code_identity": _code_identity(),
        "config_sha256": _config_sha(policy),
        "coverage": {
            "comparable_hour_count": comparable_hours,
            "days_with_compared_hour": sum(1 for day in days if day["successfully_compared_hour_count"]),
            "distinct_day_count": len(days),
            "expected_hour_count": HOURS_PER_DAY * len(days),
            "expected_slot_count": HOURS_PER_DAY * SLOTS_PER_HOUR * len(days),
            "field_denominator": totals["field_denominator"],
            "logical_role_count": logical_roles,
            "matched_field_count": totals["matched_field_count"],
            "observed_slot_count": observed_slot_total,
            "partial_hour_count": partial_total,
            "per_product": per_product,
            "roles_with_compared_hour": covered_roles,
            "successfully_compared_hour_count": success_hours,
            "uncomparable_hour_count": uncomparable_hour_count,
            "zero_observation_hour_count": zero_total,
        },
        "coverage_failures": sorted(coverage_failures, key=_record_sort),
        "days": days,
        "discrepancies": sorted(discrepancies, key=_record_sort),
        "document_type": REPORT_DOCUMENT,
        "flow_completion_sha256": policy.flow_completion,
        "flow_schema_sha256": _SCHEMA_SHA[PRODUCT_TRADE_FLOW_1H],
        "full_history": False,
        "qualification_report_sha256": policy.report_sha256,
        "sample_manifest_sha256": loaded.manifest_sha256,
        "sample_objects": [
            {
                "comparison_key": item.comparison_key,
                "hourly_sample_sha256": item.hourly_sample_sha256,
                "roles": list(item.roles),
                "symbol": item.symbol,
                "utc_date": item.utc_date,
                "zip_sha256": item.zip_sha256,
            }
            for item in loaded.objects
        ],
        "schema_version": SCHEMA_VERSION,
        "scope": SCOPE,
        "skipped_product_hours": sorted(skipped, key=_record_sort),
        "status": "FAILED" if failed else "PASS",
        "uncomparable_hours": sorted(uncomparable, key=_record_sort),
        "unexplained_absences": sorted(unexplained, key=_record_sort),
    }
    return report


def _publish(output: Path, report: Mapping[str, Any], policy: sample.Policy, manifest: str) -> ReconciliationResult:
    body = sample.canonical_json(report)
    digest = sample.sha256_hex(body)
    relative = f".reports/{digest}.json"
    reused = sample.publish_immutable(
        output,
        relative,
        body,
        read_limit=sample.AUTHORITY_JSON_BYTES,
    )
    report_path = output / ".reports" / f"{digest}.json"
    existing = sample.list_regular(output, ".complete", limit=8)
    if report["status"] != "PASS":
        _require(not existing, "conflicting reconciliation completion")
        return ReconciliationResult("FAILED", digest, report_path, None, None, reused, False)
    completion = {
        "bar_completion_sha256": policy.bar_completion,
        "document_type": COMPLETION_DOCUMENT,
        "flow_completion_sha256": policy.flow_completion,
        "full_history": False,
        "qualification_report_sha256": policy.report_sha256,
        "report_sha256": digest,
        "sample_manifest_sha256": manifest,
        "schema_version": SCHEMA_VERSION,
        "scope": SCOPE,
        "status": "PASS",
    }
    completion_body = sample.canonical_json(completion)
    completion_sha = sample.sha256_hex(completion_body)
    name = f"{completion_sha}.json"
    _require(not existing or existing == [name], "conflicting reconciliation completion")
    completion_reused = sample.publish_immutable(
        output,
        f".complete/{name}",
        completion_body,
        read_limit=sample.AUTHORITY_JSON_BYTES,
    )
    return ReconciliationResult(
        "PASS",
        digest,
        report_path,
        completion_sha,
        output / ".complete" / name,
        reused,
        completion_reused,
    )


def reconcile(policy: sample.Policy, evidence_root: Path, output_root: Path) -> ReconciliationResult:
    """Re-authenticate retained minutes and publish a deterministic comparison."""

    evidence, output = sample.assert_isolated(policy, evidence_root, output_root)
    loaded = sample.load_sample(policy, evidence)
    output = sample._ensure_directory(output)
    locked = sample._LockedDirectory(output)
    try:
        report = _compare(policy, loaded, evidence)
        return _publish(output, report, policy, loaded.manifest_sha256)
    finally:
        locked.close()
