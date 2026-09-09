"""Normalize authenticated Coinalyze daily liquidation observations.

The product preserves the provider's base-asset aggregates and point ordinals.  Its
calendar is the inclusive authenticated request calendar: absent days become typed
gaps, never zero-valued observations.  The bounded Gate-4 comparison is evidence for
review and does not accept either source.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import stat
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlencode

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.acquisition.binance_usdm_harmonic_acquisition import (
    KIND_COINALYZE_INVENTORY,
    KIND_COINALYZE_LIQUIDATION,
    OUTCOME_CHECKSUM_VERIFIED,
    OUTCOME_RETAINED_INVENTORY,
    PROVIDER_COINALYZE,
    STATE_APPLICATION_ID,
    STATE_USER_VERSION,
    AcquisitionState,
    compact_json,
    register_domain_functions,
)
from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    coinalyze_perp_symbol,
)
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    DECIMAL_SCALE,
    PARQUET_COMPRESSION,
    PARQUET_COMPRESSION_LEVEL,
    PARQUET_VERSION,
    PRODUCT_BAR_1H,
    PRODUCT_FUNDING_REALIZED,
    PRODUCT_LIQUIDATION_OBSERVED_DAILY,
    PRODUCT_OPEN_INTEREST_5M,
    QUALITY_GAP_COLUMNS,
    SIZING_ROW_BATCH,
    convert_decimal,
    final_product_schema,
    native_identity,
    product_schema_identity,
    writer_identity,
)

PRODUCT = PRODUCT_LIQUIDATION_OBSERVED_DAILY
SCHEMA = final_product_schema(PRODUCT)
SCHEMA_SHA256 = product_schema_identity(PRODUCT)
GAP_SCHEMA = pa.schema(
    [
        pa.field(c.name, final_product_schema(PRODUCT).field(c.name).type, nullable=c.nullable)
        if c.name in SCHEMA.names
        else pa.field(c.name, {
            "required_product": pa.dictionary(pa.int32(), pa.string()),
            "utc_month": pa.dictionary(pa.int32(), pa.string()),
            "missing_run_start_ms": pa.int64(),
            "missing_run_end_ms": pa.int64(),
            "expected_grid_count": pa.int64(),
            "gap_kind": pa.dictionary(pa.int32(), pa.string()),
            "reason": pa.dictionary(pa.int32(), pa.string()),
        }[c.name], nullable=c.nullable)
        for c in QUALITY_GAP_COLUMNS
    ]
)

REPORT_SHA256 = "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
SIZING_SHA256 = "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589"
GENERATION0_SEAL = "8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab"
INVENTORY_SHA256 = "a5f361ecc91ddfe2a7564f7495adbf7a8cbf75d8f7d0c180c13652592c7b1c97"
INVENTORY_BYTES = 1_449_633
INVENTORY_MAPPING_SHA256 = "915b643adb226699d9b8fd4607e727470114ccf44b9bb9665a9035acdfc1565c"
ACCEPTED_BINANCE_COMPLETIONS = 685_072
ACCEPTED_INVENTORY_MARKETS = 4_958
ACCEPTED_BINANCE_PERPETUAL_MAPPINGS = 759
ACCEPTED_SELECTED_MAPPINGS = 569
ACCEPTED_UNMAPPED = 202
ACCEPTED_RESPONSES = 569
ACCEPTED_RESPONSE_BYTES = 20_126_995
PROJECTED_POINTS = 486_056
PROJECTED_PARTITIONS = 16_419
PROJECTED_NORMALIZED_BYTES = 187_270_569
LARGEST_PARTITION_BYTES = 11_544

COINALYZE_BASE = "https://api.coinalyze.net/v1"
LIQUIDATION_PATH = "/liquidation-history"
INVENTORY_PATH = "/future-markets"
DAY_SECONDS = 86_400
DAY_MS = 86_400_000
MAX_RESPONSE_BYTES = 1 * 2**20
MAX_INVENTORY_BYTES = 2 * 2**20
MAX_REPORT_BYTES = 16 * 2**20
MAX_SIZING_BYTES = 48 * 2**20
MAX_POINTS_PER_RESPONSE = 4_096
MAX_REQUEST_DAYS = 4_096
RENAME_NOREPLACE = 1
REFERENCE_STATE = "canonical_reference_unavailable"
SEMANTICS = "censored_observed_daily_aggregate"
UNKNOWN_AVAILABILITY = "unknown_not_imputed"
CENSORSHIP_START = "2021-04-27"
_HEX = re.compile(r"[0-9a-f]{64}")

OVERLAP = {
    "/ohlcv-history": ("c86e86e868400d6147ea4b41f23afe0d3a381ed1b23673e94335234f895538e6", 97_061, "2026-08-22T22:54:52.930114+00:00"),
    "/open-interest-history": ("019d0028d675e5a5daf746492ca737f86e4a14df08ce8874c747dc1ea2f83b7b", 51_792, "2026-08-22T22:54:51.239980+00:00"),
    "/funding-rate-history": ("149c9fcb443ac008f9f7b54ccec57f58a9e1d397063d6c9771c847369187da09", 45_263, "2026-08-22T22:54:52.090277+00:00"),
}
OFFICIAL_COMPLETIONS = {
    PRODUCT_BAR_1H: "3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7",
    PRODUCT_OPEN_INTEREST_5M: "bb089fc992326c66ddb65cea03dda92e8cd9fcf7cb7f373821f04a16db9168e4",
    PRODUCT_FUNDING_REALIZED: "57628164f19d182164b6058d9e51f794430cc918706c088f430e1c01d2898522",
}
COMPARE_DAYS = ("2020-10-01", "2020-11-15", "2020-12-31")
COMPARE_SYMBOLS = ("BTCUSDT", "ETHUSDT")


class LiquidationNormalizationError(RuntimeError):
    """Fail-closed authority, exactness, lineage, or publication error."""


@dataclass(frozen=True, slots=True)
class LiquidationMapping:
    native_symbol: str
    provider_symbol: str
    base_asset: str
    quote_asset: str


@dataclass(frozen=True, slots=True)
class RawLiquidationObject:
    identity: str
    native_symbol: str
    provider_symbol: str
    base_asset: str
    quote_asset: str
    path: Path
    source_sha256: str
    byte_size: int
    retrieved_at: str
    request_from_s: int
    request_to_s: int
    point_count: int
    status: int = 200
    validation_state: str = OUTCOME_CHECKSUM_VERIFIED


@dataclass(frozen=True, slots=True)
class InventoryProof:
    path: Path
    source_sha256: str
    byte_size: int
    identity: str
    retrieved_at: str
    mapping_count: int
    mapping_digest: str
    market_count: int


@dataclass(frozen=True, slots=True)
class OverlapReceipt:
    endpoint: str
    path: Path
    source_sha256: str
    byte_size: int
    retrieved_at: str
    request_from_s: int = 1_577_836_800
    request_to_s: int = 1_609_459_200
    interval: str = "daily"
    symbols: str = "BTCUSDT_PERP.A,ETHUSDT_PERP.A"
    status: int = 200


@dataclass(frozen=True, slots=True)
class OfficialProductAuthority:
    product: str
    root: Path
    completion_sha256: str
    enforce_pinned_identity: bool = True


@dataclass(frozen=True, slots=True)
class PublishedPartition:
    native_symbol: str
    utc_month: str
    row_count: int
    parquet_path: Path
    parquet_sha256: str
    lineage_path: Path
    lineage_sha256: str
    reused: bool


@dataclass(frozen=True, slots=True)
class PublishedGap:
    kind: str
    row_count: int
    parquet_path: Path
    parquet_sha256: str
    lineage_path: Path
    lineage_sha256: str
    reused: bool


@dataclass(frozen=True, slots=True)
class LiquidationNormalizationResult:
    schema_sha256: str
    partitions: tuple[PublishedPartition, ...]
    gaps: tuple[PublishedGap, ...]
    comparison_path: Path
    comparison_sha256: str
    comparison_count: int
    completion_path: Path
    completion_sha256: str
    completion_reused: bool
    physical_source_rows: int
    collapsed_identical_rows: int
    product_rows: int
    missing_daily_slots: int
    authority_gap_rows: int


@dataclass(frozen=True, slots=True)
class PublicationHooks:
    before_publish: Callable[[str, Path, Path], None] | None = None
    observe_month_buffer: Callable[[str, str, int], None] | None = None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LiquidationNormalizationError(message)


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, "JSON object repeats a key")
        result[key] = value
    return result


def _constant(_value: str) -> Any:
    raise LiquidationNormalizationError("JSON contains a non-finite numeric constant")


def _strict_json(body: bytes, *, maximum: int) -> Any:
    _require(0 < len(body) <= maximum, "JSON authority exceeds its finite bound")
    try:
        return json.loads(
            body.decode("utf-8"), parse_float=Decimal, parse_int=int,
            parse_constant=_constant, object_pairs_hook=_pairs,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise LiquidationNormalizationError("authority is not strict UTF-8 JSON") from exc


def _is_digest(value: object) -> bool:
    return type(value) is str and _HEX.fullmatch(value) is not None


def _safe_component(value: str) -> str:
    _require(type(value) is str and bool(value) and value not in {".", ".."}, "unsafe output component")
    _require("/" not in value and "\\" not in value and "\x00" not in value, "unsafe output component")
    return value


def _no_symlinks(path: Path, label: str) -> None:
    absolute = path.absolute()
    for item in reversed((absolute, *absolute.parents)):
        if not item.exists() and not item.is_symlink():
            continue
        try:
            facts = item.lstat()
        except OSError as exc:
            raise LiquidationNormalizationError(f"{label} cannot be inspected") from exc
        _require(not stat.S_ISLNK(facts.st_mode), f"{label} contains a symlink")


def _read_regular(path: Path, maximum: int, *, digest: str | None = None, size: int | None = None) -> bytes:
    _no_symlinks(path, "authority path")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        raise LiquidationNormalizationError("authority cannot be opened no-follow") from exc
    try:
        facts = os.fstat(fd)
        _require(stat.S_ISREG(facts.st_mode), "authority is not a regular file")
        _require(0 < facts.st_size <= maximum, "authority size exceeds its finite bound")
        chunks: list[bytes] = []
        total = 0
        while block := os.read(fd, 1024 * 1024):
            total += len(block)
            _require(total <= maximum, "authority changed beyond its finite bound")
            chunks.append(block)
        body = b"".join(chunks)
    finally:
        os.close(fd)
    if size is not None:
        _require(len(body) == size, "authority byte size changed")
    if digest is not None:
        _require(_is_digest(digest) and hashlib.sha256(body).hexdigest() == digest, "authority digest changed")
    return body


def _open_authenticated(
    path: Path, maximum: int, *, digest: str, size: int | None = None
) -> int:
    _no_symlinks(path, "authority path")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        raise LiquidationNormalizationError(
            "authority cannot be opened no-follow"
        ) from exc
    try:
        facts = os.fstat(fd)
        _require(stat.S_ISREG(facts.st_mode), "authority is not a regular file")
        _require(0 < facts.st_size <= maximum, "authority size exceeds its finite bound")
        observed_digest, observed_size = _digest_fd(fd)
        _require(observed_digest == digest, "authority digest changed")
        if size is not None:
            _require(observed_size == size, "authority byte size changed")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except Exception:
        os.close(fd)
        raise


def _open_regular_child(directory_fd: int, name: str, label: str) -> int | None:
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise LiquidationNormalizationError(f"{label} cannot be opened no-follow") from exc
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise LiquidationNormalizationError(f"{label} is not a regular file")
    return fd


def _decimal(value: object, *, key: str, column: str, row: int) -> Decimal:
    _require(type(value) in (int, Decimal), f"{column} is not an exact JSON number")
    return convert_decimal(str(value), key=key, output=PRODUCT, column=column, row=row)


def _unscaled(value: Decimal) -> int:
    sign, digits, exponent = value.as_tuple()
    _require(exponent >= -DECIMAL_SCALE, "decimal exceeds pinned scale")
    coefficient = int("".join(str(d) for d in digits) or "0")
    if exponent >= 0:
        coefficient *= 10**exponent
        exponent = 0
    coefficient *= 10 ** (DECIMAL_SCALE + exponent)
    return -coefficient if sign else coefficient


def _scaled(value: int) -> Decimal:
    digits = tuple(int(character) for character in str(abs(value))) if value else (0,)
    _require(len(digits) <= 38, "derived liquidation decimal overflows pinned precision")
    return Decimal((1 if value < 0 else 0, digits, -DECIMAL_SCALE))


def _month(ms: int) -> str:
    return datetime.fromtimestamp(ms // 1000, UTC).strftime("%Y-%m")


def _day_bounds(day: str) -> tuple[int, int]:
    start = int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC).timestamp() * 1000)
    return start, start + DAY_MS


def _iso_time(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise LiquidationNormalizationError("retrieval time is not ISO-8601") from exc
    _require(parsed.tzinfo is not None, "retrieval time is not timezone-aware")


def _validate_raw_descriptor(source: RawLiquidationObject) -> None:
    _safe_component(source.native_symbol)
    _require(
        source.provider_symbol == coinalyze_perp_symbol(source.native_symbol),
        "provider/native mapping changed",
    )
    _require(
        source.identity.startswith(f"{LIQUIDATION_PATH}?"),
        "liquidation identity changed",
    )
    params = {
        "symbols": source.provider_symbol, "interval": "daily",
        "from": str(source.request_from_s), "to": str(source.request_to_s), "convert_to_usd": "false",
    }
    expected = f"{LIQUIDATION_PATH}?{urlencode(params)}"
    _require(source.identity == expected, "liquidation query identity changed")
    _require(source.request_from_s % DAY_SECONDS == 0 and source.request_to_s % DAY_SECONDS == 0, "request bounds are off daily grid")
    _require(source.request_from_s <= source.request_to_s, "request bounds are reversed")
    _require((source.request_to_s - source.request_from_s) // DAY_SECONDS + 1 <= MAX_REQUEST_DAYS, "request range exceeds bound")
    _require(source.status == 200 and source.validation_state == OUTCOME_CHECKSUM_VERIFIED, "liquidation completion state changed")
    _require(type(source.point_count) is int and 0 < source.point_count <= MAX_POINTS_PER_RESPONSE, "revision point count is invalid")
    _require(_is_digest(source.source_sha256), "liquidation digest is invalid")
    _require(type(source.byte_size) is int and 0 < source.byte_size <= MAX_RESPONSE_BYTES, "liquidation size is invalid")
    _iso_time(source.retrieved_at)


def _parse_liquidation(source: RawLiquidationObject) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]]]:
    body = _read_regular(source.path, MAX_RESPONSE_BYTES, digest=source.source_sha256, size=source.byte_size)
    root = _strict_json(body, maximum=MAX_RESPONSE_BYTES)
    _require(type(root) is list and len(root) == 1 and type(root[0]) is dict, "liquidation response envelope is invalid")
    item = root[0]
    _require(set(item) == {"symbol", "history"}, "liquidation response fields changed")
    _require(item["symbol"] == source.provider_symbol, "returned provider symbol changed")
    history = item["history"]
    _require(type(history) is list and len(history) == source.point_count, "revision point count disagrees with response")
    physical = len(history)
    kept: list[dict[str, Any]] = []
    collapsed: list[dict[str, Any]] = []
    previous_t: int | None = None
    by_time: dict[int, dict[str, Any]] = {}
    for ordinal, raw in enumerate(history):
        _require(type(raw) is dict and set(raw) == {"t", "l", "s"}, "liquidation point fields changed")
        t = raw["t"]
        _require(type(t) is int and t % DAY_SECONDS == 0, "liquidation time is not an integer daily-grid second")
        _require(source.request_from_s <= t <= source.request_to_s, "liquidation point is outside inclusive request")
        _require(previous_t is None or t >= previous_t, "liquidation source order decreased")
        long_value = _decimal(raw["l"], key=source.identity, column="long_liquidation", row=ordinal)
        short_value = _decimal(raw["s"], key=source.identity, column="short_liquidation", row=ordinal)
        _require(_unscaled(long_value) >= 0 and _unscaled(short_value) >= 0, "liquidation amount is negative")
        row = {"point_ordinal": ordinal, "event_time_ms": t * 1000, "long_liquidation": long_value, "short_liquidation": short_value}
        prior = by_time.get(t)
        if prior is not None:
            _require(long_value == prior["long_liquidation"] and short_value == prior["short_liquidation"], "repeated liquidation time conflicts")
            collapsed.append({"kept_point_ordinal": prior["point_ordinal"], "collapsed_point_ordinal": ordinal, "event_time_ms": t * 1000, "reason": "identical_source_repeat"})
        else:
            by_time[t] = row
            kept.append(row)
        previous_t = t
    _require(physical > 0 and physical - len(collapsed) == len(kept), "liquidation row equation failed")
    return kept, physical, collapsed


def _product_row(source: RawLiquidationObject, record: Mapping[str, Any]) -> dict[str, Any]:
    imbalance = _scaled(_unscaled(record["long_liquidation"]) - _unscaled(record["short_liquidation"]))
    return {
        **native_identity(source.native_symbol), "raw_object_ref": 0,
        "point_ordinal": record["point_ordinal"], "provider_symbol": source.provider_symbol,
        "event_time_ms": record["event_time_ms"], "long_liquidation": record["long_liquidation"],
        "short_liquidation": record["short_liquidation"], "liquidation_imbalance": imbalance,
        "source_interval_seconds": DAY_SECONDS, "observation_semantics": SEMANTICS, "event_complete": False,
    }


def _missing_runs(start_s: int, end_s: int, observed: set[int]) -> list[tuple[int, int, int]]:
    result: list[tuple[int, int, int]] = []
    run: int | None = None
    cursor = start_s
    while cursor <= end_s:
        if cursor not in observed and run is None:
            run = cursor
        if cursor in observed and run is not None:
            result.append((run * 1000, (cursor - DAY_SECONDS) * 1000, (cursor - run) // DAY_SECONDS))
            run = None
        cursor += DAY_SECONDS
    if run is not None:
        result.append((run * 1000, end_s * 1000, (end_s - run) // DAY_SECONDS + 1))
    return result


def _split_run_months(start_ms: int, end_ms: int) -> list[tuple[str, int, int, int]]:
    result: list[tuple[str, int, int, int]] = []
    cursor = start_ms
    while cursor <= end_ms:
        month = _month(cursor)
        d = datetime.fromtimestamp(cursor // 1000, UTC)
        next_month = (d.replace(day=28) + timedelta(days=4)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        piece_end = min(end_ms, int(next_month.timestamp() * 1000) - DAY_MS)
        result.append((month, cursor, piece_end, (piece_end - cursor) // DAY_MS + 1))
        cursor = piece_end + DAY_MS
    return result


def _gap_row(symbol: str, month: str, start: int | None, end: int | None, count: int, kind: str, reason: str) -> dict[str, Any]:
    return {**native_identity(symbol), "required_product": PRODUCT, "utc_month": month,
            "missing_run_start_ms": start, "missing_run_end_ms": end,
            "expected_grid_count": count, "gap_kind": kind, "reason": reason}


def _lineage_source(source: RawLiquidationObject) -> dict[str, Any]:
    return {"raw_object_ref": 0, "identity": source.identity, "source_sha256": source.source_sha256,
            "byte_size": source.byte_size, "retrieved_at": source.retrieved_at,
            "provider": PROVIDER_COINALYZE, "provider_symbol": source.provider_symbol,
            "native_symbol": source.native_symbol, "base_asset": source.base_asset,
            "quote_asset": source.quote_asset, "amount_unit": "base_asset",
            "request_from_s": source.request_from_s, "request_to_s": source.request_to_s,
            "request_interval": "daily", "convert_to_usd": False,
            "validation_state": source.validation_state, "source_available_at": None,
            "source_availability_state": UNKNOWN_AVAILABILITY}


def _digest_fd(fd: int) -> tuple[str, int]:
    position = os.lseek(fd, 0, os.SEEK_CUR)
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    size = 0
    try:
        while block := os.read(fd, 1024 * 1024):
            digest.update(block)
            size += len(block)
    finally:
        os.lseek(fd, position, os.SEEK_SET)
    return digest.hexdigest(), size


def _same_fd(a: int, b: int) -> bool:
    if os.fstat(a).st_size != os.fstat(b).st_size:
        return False
    left_position = os.lseek(a, 0, os.SEEK_CUR)
    right_position = os.lseek(b, 0, os.SEEK_CUR)
    os.lseek(a, 0, os.SEEK_SET)
    os.lseek(b, 0, os.SEEK_SET)
    try:
        while block := os.read(a, 1024 * 1024):
            if block != os.read(b, len(block)):
                return False
        return os.read(b, 1) == b""
    finally:
        os.lseek(a, left_position, os.SEEK_SET)
        os.lseek(b, right_position, os.SEEK_SET)


def _rename(old_dir: int, old: str, new_dir: int, new: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        fn = libc.renameat2
    except AttributeError as exc:
        raise LiquidationNormalizationError(
            "atomic no-replace rename unavailable"
        ) from exc
    fn.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    fn.restype = ctypes.c_int
    if fn(old_dir, os.fsencode(old), new_dir, os.fsencode(new), RENAME_NOREPLACE):
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), new)


class _OutputTree:
    def __init__(self, root: Path) -> None:
        _require(root.name.startswith("."), "liquidation output root must be hidden")
        _no_symlinks(root, "output root")
        if not root.exists():
            root.mkdir(mode=0o700)
            parent_fd = os.open(root.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        self.root = root.resolve(strict=True)
        self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self.fd)
            raise LiquidationNormalizationError(
                "another normalizer holds output root"
            ) from exc
        facts = os.fstat(self.fd)
        self.identity = (facts.st_dev, facts.st_ino)
        os.close(self.directory((".staging",), True))

    def close(self) -> None:
        os.close(self.fd)

    def verify_root(self) -> None:
        try:
            current = os.open(
                self.root,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
        except OSError as exc:
            raise LiquidationNormalizationError("held output root was replaced") from exc
        try:
            facts = os.fstat(current)
            _require(
                (facts.st_dev, facts.st_ino) == self.identity,
                "held output root was replaced",
            )
        finally:
            os.close(current)

    def directory(self, parts: Sequence[str], create: bool) -> int:
        current = os.dup(self.fd)
        try:
            for value in parts:
                name = _safe_component(value)
                if create:
                    try:
                        os.mkdir(name, 0o700, dir_fd=current)
                        os.fsync(current)
                    except FileExistsError:
                        pass
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
                os.close(current)
                current = child
            return current
        except Exception:
            os.close(current)
            raise

    def publish(self, body_writer: Callable[[int], None], parts: Sequence[str], name: str, kind: str, hooks: PublicationHooks) -> tuple[Path, str, bool]:
        staging = self.directory((".staging",), False)
        stage = f"{kind}-{uuid.uuid4().hex}.tmp"
        fd = os.open(stage, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=staging)
        final: int | None = None
        try:
            body_writer(fd)
            os.fsync(fd)
            digest, _ = _digest_fd(fd)
            _require(name == f"{digest}.{name.rsplit('.', 1)[-1]}", "publication content address changed")
            destination = self.directory(parts, True)
            path = self.root.joinpath(*parts, name)
            try:
                if hooks.before_publish:
                    hooks.before_publish(
                        kind, self.root / ".staging" / stage, path
                    )
                self.verify_root()
                try:
                    _rename(staging, stage, destination, name)
                    os.fsync(destination)
                    os.fsync(staging)
                    reused = False
                except OSError as exc:
                    if exc.errno != errno.EEXIST:
                        raise
                    os.unlink(stage, dir_fd=staging)
                    os.fsync(staging)
                    reused = True
                final = os.open(
                    name,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=destination,
                )
                _require(
                    stat.S_ISREG(os.fstat(final).st_mode),
                    "published object is not regular",
                )
                _require(_same_fd(fd, final), "published or replayed bytes differ")
                self.verify_root()
            finally:
                os.close(destination)
            return path, digest, reused
        finally:
            if final is not None:
                os.close(final)
            os.close(fd)
            os.close(staging)

    def only_completion(self, name: str) -> None:
        fd = self.directory((".complete",), True)
        try:
            _require(
                not [x for x in os.listdir(fd) if x != name],
                "another completion already exists",
            )
        finally:
            os.close(fd)

    def open_published(self, path: Path) -> int:
        self.verify_root()
        _require(path.is_relative_to(self.root), "published path escapes held root")
        relative = path.relative_to(self.root)
        directory = self.directory(relative.parts[:-1], False)
        try:
            fd = os.open(
                relative.name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=directory,
            )
        finally:
            os.close(directory)
        _require(stat.S_ISREG(os.fstat(fd).st_mode), "published path is not regular")
        self.verify_root()
        return fd

    def verify_json(self, path: Path, digest: str, body: bytes) -> None:
        fd = self.open_published(path)
        try:
            _require(_digest_fd(fd)[0] == digest, "published JSON digest changed")
            os.lseek(fd, 0, os.SEEK_SET)
            observed = bytearray()
            while block := os.read(fd, 1024 * 1024):
                observed.extend(block)
            _require(bytes(observed) == body, "published JSON bytes changed")
        finally:
            os.close(fd)

    def verify_parquet(
        self, path: Path, digest: str, schema: pa.Schema, rows: int
    ) -> None:
        fd = self.open_published(path)
        try:
            _require(_digest_fd(fd)[0] == digest, "published Parquet digest changed")
            parquet = pq.ParquetFile(f"/proc/self/fd/{fd}")
            _require(parquet.schema_arrow == schema, "published Parquet schema changed")
            _require(parquet.metadata.num_rows == rows, "published Parquet rows changed")
        except (OSError, pa.ArrowInvalid) as exc:
            raise LiquidationNormalizationError(
                "published Parquet is unreadable"
            ) from exc
        finally:
            os.close(fd)


def _publish_json(tree: _OutputTree, document: Mapping[str, Any], parts: Sequence[str], kind: str, hooks: PublicationHooks) -> tuple[Path, str, bool]:
    body = _canonical_json(document)
    digest = hashlib.sha256(body).hexdigest()
    def write(fd: int) -> None:
        view = memoryview(body)
        while view:
            written = os.write(fd, view)
            _require(written > 0, "staged JSON write failed")
            view = view[written:]
    path, observed, reused = tree.publish(
        write, parts, f"{digest}.json", kind, hooks
    )
    tree.verify_json(path, observed, body)
    return path, observed, reused


def _publish_table(tree: _OutputTree, table: pa.Table, schema: pa.Schema, parts: Sequence[str], kind: str, hooks: PublicationHooks) -> tuple[Path, str, bool]:
    _require(table.schema == schema and table.num_rows > 0, "empty or mistyped Parquet publication")
    holder: dict[str, str] = {}
    def write(fd: int) -> None:
        pq.write_table(table, f"/proc/self/fd/{fd}", compression=PARQUET_COMPRESSION,
                       compression_level=PARQUET_COMPRESSION_LEVEL, version=PARQUET_VERSION,
                       write_statistics=False, store_schema=True, row_group_size=SIZING_ROW_BATCH)
        os.fsync(fd)
        holder["digest"] = _digest_fd(fd)[0]
    # Deterministic bytes are needed to know the destination name; write once to a bounded temporary.
    staging = tree.directory((".staging",), False)
    probe = f"probe-{uuid.uuid4().hex}.tmp"
    fd = os.open(probe, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=staging)
    try:
        write(fd)
        digest = holder["digest"]
        os.lseek(fd, 0, os.SEEK_SET)
        body = bytearray()
        while block := os.read(fd, 1024 * 1024):
            body.extend(block)
    finally:
        os.close(fd)
        os.unlink(probe, dir_fd=staging)
        os.close(staging)
    def copy(target: int) -> None:
        view = memoryview(body)
        while view:
            written = os.write(target, view)
            _require(written > 0, "staged Parquet write failed")
            view = view[written:]
    path, observed, reused = tree.publish(
        copy, parts, f"{digest}.parquet", kind, hooks
    )
    tree.verify_parquet(path, observed, schema, table.num_rows)
    return path, observed, reused


def _exact_fraction(value: object) -> tuple[int, int]:
    _require(type(value) in (int, Decimal), "comparison value is not exact")
    dec = Decimal(value)
    sign, digits, exponent = dec.as_tuple()
    num = int("".join(str(x) for x in digits) or "0") * (-1 if sign else 1)
    _require(len(digits) <= 64 and -30 <= exponent <= 38, "comparison numeric lexeme exceeds finite exact bounds")
    if exponent >= 0:
        return num * 10**exponent, 1
    return num, 10 ** (-exponent)


def _fraction_doc(num: int, den: int) -> dict[str, str]:
    _require(den > 0, "comparison denominator is invalid")
    a, b = abs(num), den
    while b:
        a, b = b, a % b
    gcd = a or 1
    num //= gcd
    den //= gcd
    return {"numerator": str(num), "denominator": str(den)}


def _sub(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    return a[0] * b[1] - b[0] * a[1], a[1] * b[1]


def _equal(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] * b[1] == b[0] * a[1]


def _parse_overlap(receipt: OverlapReceipt) -> dict[str, dict[int, tuple[int, Mapping[str, Any]]]]:
    expected = OVERLAP.get(receipt.endpoint)
    _require(expected is not None, "unknown overlap endpoint")
    _require((receipt.source_sha256, receipt.byte_size, receipt.retrieved_at) == expected, "overlap receipt identity changed")
    _require((receipt.request_from_s, receipt.request_to_s, receipt.interval, receipt.symbols, receipt.status) == (1_577_836_800, 1_609_459_200, "daily", "BTCUSDT_PERP.A,ETHUSDT_PERP.A", 200), "overlap request envelope changed")
    body = _read_regular(receipt.path, MAX_RESPONSE_BYTES, digest=receipt.source_sha256, size=receipt.byte_size)
    root = _strict_json(body, maximum=MAX_RESPONSE_BYTES)
    _require(type(root) is list and len(root) == 2, "overlap response must contain two markets")
    result: dict[str, dict[int, tuple[int, Mapping[str, Any]]]] = {}
    for market in root:
        _require(type(market) is dict and set(market) == {"symbol", "history"}, "overlap envelope fields changed")
        provider = market["symbol"]
        _require(
            provider in {"BTCUSDT_PERP.A", "ETHUSDT_PERP.A"},
            "overlap provider symbol changed",
        )
        _require(provider.removesuffix("_PERP.A") not in result, "overlap response repeats a provider symbol")
        history = market["history"]
        _require(type(history) is list, "overlap history is not a list")
        points: dict[int, tuple[int, Mapping[str, Any]]] = {}
        previous: int | None = None
        for ordinal, row in enumerate(history):
            _require(type(row) is dict and "t" in row and "c" in row, "overlap point lacks t or c")
            t = row["t"]
            _require(
                type(t) is int
                and t % DAY_SECONDS == 0
                and receipt.request_from_s <= t <= receipt.request_to_s,
                "overlap time is invalid",
            )
            _require(previous is None or t > previous, "overlap source order is not strictly increasing")
            _require(type(row["c"]) in (int, Decimal), "overlap close is not exact")
            _exact_fraction(row["c"])
            if receipt.endpoint != "/funding-rate-history":
                _require(
                    _exact_fraction(row["c"])[0] >= 0,
                    "overlap price/OI close is negative",
                )
            _require(t not in points, "overlap response repeats a time")
            points[t] = (ordinal, row)
            previous = t
        result[provider.removesuffix("_PERP.A")] = points
    _require(set(result) == set(COMPARE_SYMBOLS), "overlap symbols changed")
    return result


def _official_completion(authority: OfficialProductAuthority) -> tuple[Mapping[str, Any], Mapping[tuple[str, str], Mapping[str, Any]]]:
    _require(authority.product in OFFICIAL_COMPLETIONS, "unexpected official product")
    if authority.enforce_pinned_identity:
        _require(authority.completion_sha256 == OFFICIAL_COMPLETIONS[authority.product], "official completion identity changed")
    name = authority.completion_sha256
    path = authority.root / ".complete" / f"{name}.json"
    _require((authority.root / ".complete").is_dir(), "official completion directory is missing")
    _require(sorted(x.name for x in (authority.root / ".complete").iterdir()) == [f"{name}.json"], "official completion is not sole")
    body = _read_regular(path, MAX_REPORT_BYTES, digest=name)
    document = _strict_json(body, maximum=MAX_REPORT_BYTES)
    _require(type(document) is dict and document.get("required_product") == authority.product, "official completion product changed")
    _require(document.get("schema_sha256") == product_schema_identity(authority.product), "official schema identity changed")
    index: dict[tuple[str, str], Mapping[str, Any]] = {}
    for raw in document.get("partitions", []):
        _require(type(raw) is dict, "official partition descriptor is invalid")
        key = (raw.get("native_symbol"), raw.get("utc_month"))
        _require(key not in index, "official completion repeats a partition")
        index[key] = raw
    return document, index


def _official_rows(authority: OfficialProductAuthority, descriptor: Mapping[str, Any], columns: Sequence[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rel = PurePosixPath(str(descriptor.get("parquet_path", "")))
    _require(
        not rel.is_absolute() and ".." not in rel.parts,
        "official Parquet path escapes root",
    )
    path = authority.root.joinpath(*rel.parts)
    digest = descriptor.get("parquet_sha256")
    _require(_is_digest(digest), "official Parquet digest invalid")
    fd = _open_authenticated(path, 64 * 2**20, digest=str(digest))
    try:
        parquet = pq.ParquetFile(f"/proc/self/fd/{fd}")
        _require(parquet.schema_arrow == final_product_schema(authority.product), "official Parquet schema changed")
        table = parquet.read(columns=list(columns))
    except (OSError, pa.ArrowInvalid, KeyError) as exc:
        raise LiquidationNormalizationError("official Parquet is unreadable") from exc
    finally:
        os.close(fd)
    _require(table.num_rows == descriptor.get("row_count"), "official row count changed")
    lrel = PurePosixPath(str(descriptor.get("lineage_path", "")))
    _require(
        not lrel.is_absolute() and ".." not in lrel.parts,
        "official lineage path escapes root",
    )
    lsha = descriptor.get("lineage_sha256")
    _require(_is_digest(lsha), "official lineage digest invalid")
    lineage_body = _read_regular(authority.root.joinpath(*lrel.parts), MAX_REPORT_BYTES, digest=str(lsha))
    lineage = _strict_json(lineage_body, maximum=MAX_REPORT_BYTES)
    _require(type(lineage) is dict and lineage.get("parquet_sha256") == digest, "official lineage does not bind Parquet")
    raw_objects = lineage.get("raw_objects")
    _require(type(raw_objects) is list, "official lineage lacks raw objects")
    return table.to_pylist(), {"completion_sha256": authority.completion_sha256, "parquet_path": str(rel), "parquet_sha256": digest,
                               "lineage_path": str(lrel), "lineage_sha256": lsha, "raw_objects": raw_objects}


def build_comparison(receipts: Sequence[OverlapReceipt], officials: Sequence[OfficialProductAuthority]) -> dict[str, Any]:
    _require({x.endpoint for x in receipts} == set(OVERLAP) and len(receipts) == 3, "overlap receipt inventory changed")
    secondary = {r.endpoint: _parse_overlap(r) for r in receipts}
    official_map = {a.product: (a, *_official_completion(a)) for a in officials}
    _require(set(official_map) == set(OFFICIAL_COMPLETIONS), "official product inventory changed")
    entries: list[dict[str, Any]] = []
    for symbol in COMPARE_SYMBOLS:
        for day in COMPARE_DAYS:
            start, end = _day_bounds(day)
            sec_t = start // 1000
            for endpoint, product, metric in (
                ("/ohlcv-history", PRODUCT_BAR_1H, "price_close"),
                ("/funding-rate-history", PRODUCT_FUNDING_REALIZED, "funding_rate"),
                ("/open-interest-history", PRODUCT_OPEN_INTEREST_5M, "open_interest"),
            ):
                sec = secondary[endpoint][symbol].get(sec_t)
                _require(sec is not None, "frozen secondary comparison day is absent")
                sec_ordinal, sec_row = sec
                sec_value = _exact_fraction(sec_row["c"])
                authority, _completion, index = official_map[product]
                descriptor = index.get((symbol, day[:7]))
                base = {"symbol": symbol, "utc_day": day, "metric": metric,
                        "secondary": {"endpoint": endpoint, "source_sha256": next(r.source_sha256 for r in receipts if r.endpoint == endpoint),
                                      "timestamp_s": sec_t, "point_ordinal": sec_ordinal, "value": _fraction_doc(*sec_value)},
                        "review_disposition": "pending_reviewer"}
                if descriptor is None:
                    entries.append({**base, "status": "official_overlap_unavailable", "official": None, "difference": None})
                    continue
                time_col = {PRODUCT_BAR_1H: "open_time", PRODUCT_FUNDING_REALIZED: "calc_time", PRODUCT_OPEN_INTEREST_5M: "create_time"}[product]
                value_col = {PRODUCT_BAR_1H: "close", PRODUCT_FUNDING_REALIZED: "last_funding_rate", PRODUCT_OPEN_INTEREST_5M: "sum_open_interest"}[product]
                cols = [time_col, value_col, "raw_object_ref", "source_row_ordinal"]
                if product == PRODUCT_BAR_1H:
                    cols.append("close_time")
                if product == PRODUCT_FUNDING_REALIZED:
                    cols.append("funding_interval_hours")
                rows, proof = _official_rows(authority, descriptor, cols)
                same = [r for r in rows if start <= int(r[time_col]) < end]
                if not same:
                    entries.append({**base, "status": "official_overlap_unavailable", "official": {**proof, "reason": "no_exact_day_observation"}, "difference": None})
                    continue
                chosen = max(same, key=lambda r: int(r[time_col]))
                official_value = _exact_fraction(chosen[value_col])
                if metric == "funding_rate":
                    sec_value = (sec_value[0], sec_value[1] * 100)
                raw_ref = int(chosen["raw_object_ref"])
                raw_hits = [x for x in proof.pop("raw_objects") if type(x) is dict and x.get("raw_object_ref") == raw_ref]
                _require(len(raw_hits) == 1 and _is_digest(raw_hits[0].get("source_sha256")), "official raw lineage reference is invalid")
                official = {**proof, "timestamp_ms": int(chosen[time_col]), "source_row_ordinal": int(chosen["source_row_ordinal"]),
                            "raw_object_ref": int(chosen["raw_object_ref"]), "value": _fraction_doc(*official_value)}
                official["raw_source"] = raw_hits[0]
                if metric == "price_close":
                    official["close_time_ms"] = int(chosen["close_time"])
                    _require(int(chosen["open_time"]) == end - 3_600_000 and int(chosen["close_time"]) == end - 1,
                             "comparison did not select the final complete official hourly bar")
                if metric == "funding_rate":
                    official["funding_interval_hours"] = int(chosen["funding_interval_hours"])
                    _require(official["funding_interval_hours"] == 8, "comparison settlement interval changed")
                    base["convention"] = "Coinalyze daily close percentage divided by 100; compare with last actual same-day settlement without summing"
                if metric == "open_interest":
                    _require(int(chosen["create_time"]) == end - 300_000, "comparison official OI is not the 23:55 stock")
                    official["same_day_min"] = _fraction_doc(*min((_exact_fraction(r[value_col]) for r in same), key=lambda x: Fraction(*x)))
                    official["same_day_max"] = _fraction_doc(*max((_exact_fraction(r[value_col]) for r in same), key=lambda x: Fraction(*x)))
                    base["convention"] = "daily close base units minus final same-day five-minute base-unit stock"
                difference = _sub(sec_value, official_value)
                status = "measured_difference" if metric == "open_interest" else ("exact_value_match" if _equal(sec_value, official_value) else "measured_difference")
                entries.append({**base, "status": status, "secondary_fractional_value": _fraction_doc(*sec_value), "official": official, "difference": _fraction_doc(*difference)})
    _require(len(entries) == 18, "comparison inventory is not 18 entries")
    return {"document_type": "cex002_liquidation_bounded_secondary_comparison", "schema_version": 1,
            "requested_entries": 18,
            "overlap_receipts": [{"endpoint": r.endpoint, "path": str(r.path), "source_sha256": r.source_sha256,
                                   "byte_size": r.byte_size, "retrieved_at": r.retrieved_at,
                                   "params": {"from": str(r.request_from_s), "to": str(r.request_to_s),
                                              "interval": r.interval, "symbols": r.symbols}, "status": r.status}
                                  for r in sorted(receipts, key=lambda x: x.endpoint)],
            "entries": entries,
            "interpretation": "Evidence only; comparison and product acceptance remain reviewer-owned."}


def _preflight(sources: Iterable[RawLiquidationObject], mappings: Mapping[str, LiquidationMapping]) -> tuple[RawLiquidationObject, ...]:
    ordered = tuple(sorted(sources, key=lambda x: x.native_symbol))
    _require(len({x.native_symbol for x in ordered}) == len(ordered), "multiple responses claim one native symbol")
    for source in ordered:
        _validate_raw_descriptor(source)
        mapping = mappings.get(source.native_symbol)
        _require(mapping is not None, "response has no selected inventory mapping")
        _require((mapping.provider_symbol, mapping.base_asset, mapping.quote_asset) == (source.provider_symbol, source.base_asset, source.quote_asset), "response descriptor conflicts with inventory")
    return ordered


def _month_records(
    records: Sequence[Mapping[str, Any]],
) -> Iterable[tuple[str, Sequence[Mapping[str, Any]]]]:
    start = 0
    while start < len(records):
        month = _month(int(records[start]["event_time_ms"]))
        end = start + 1
        while (
            end < len(records)
            and _month(int(records[end]["event_time_ms"])) == month
        ):
            end += 1
        yield month, records[start:end]
        start = end


def _monthly_gap_rows(
    source: RawLiquidationObject,
    runs: Sequence[tuple[int, int, int]],
) -> Iterable[tuple[str, list[dict[str, Any]]]]:
    current_month: str | None = None
    current_rows: list[dict[str, Any]] = []
    for run_start, run_end, _count in runs:
        for month, start, end, count in _split_run_months(run_start, run_end):
            if current_month is not None and month != current_month:
                yield current_month, current_rows
                current_rows = []
            current_month = month
            current_rows.append(
                _gap_row(
                    source.native_symbol,
                    month,
                    start,
                    end,
                    count,
                    "all_input_missing",
                    "authenticated daily request returned no observation",
                )
            )
    if current_month is not None:
        yield current_month, current_rows


def normalize_liquidation_sources(
    sources: Iterable[RawLiquidationObject], mappings: Mapping[str, LiquidationMapping], unmapped_symbols: Sequence[str],
    overlap_receipts: Sequence[OverlapReceipt], official_products: Sequence[OfficialProductAuthority], output_root: Path,
    *, inventory: InventoryProof | None = None, report_sha256: str = REPORT_SHA256, sizing_sha256: str = SIZING_SHA256,
    enforce_full_corpus: bool = False, hooks: PublicationHooks = PublicationHooks(),
) -> LiquidationNormalizationResult:
    ordered = _preflight(sources, mappings)
    _require(not (set(mappings) & set(unmapped_symbols)), "mapped and unmapped identities overlap")
    _require(len(set(unmapped_symbols)) == len(unmapped_symbols), "unmapped authority repeats an identity")
    comparison = build_comparison(overlap_receipts, official_products)
    tree = _OutputTree(output_root)
    try:
        comparison_path, comparison_sha, _ = _publish_json(tree, comparison, (".comparison",), "comparison", hooks)
        partitions: list[PublishedPartition] = []
        gaps: list[PublishedGap] = []
        physical_total = collapsed_total = row_total = missing_total = request_total = 0
        all_months: set[tuple[str, str]] = set()
        for source in ordered:
            records, physical, collapsed = _parse_liquidation(source)
            physical_total += physical
            collapsed_total += len(collapsed)
            row_total += len(records)
            observed = {int(x["event_time_ms"]) // 1000 for x in records}
            expected = (
                (source.request_to_s - source.request_from_s) // DAY_SECONDS + 1
            )
            request_total += expected
            runs = _missing_runs(source.request_from_s, source.request_to_s, observed)
            missing_total += sum(x[2] for x in runs)
            cursor = source.request_from_s
            while cursor <= source.request_to_s:
                all_months.add((source.native_symbol, _month(cursor * 1000)))
                cursor += DAY_SECONDS
            for month, month_records in _month_records(records):
                rows = [_product_row(source, record) for record in month_records]
                if hooks.observe_month_buffer is not None:
                    hooks.observe_month_buffer(source.native_symbol, month, len(rows))
                table = pa.Table.from_pylist(rows, schema=SCHEMA)
                ppath, psha, preused = _publish_table(tree, table, SCHEMA, (".partitions", source.native_symbol, month), "partition", hooks)
                month_collapsed = [x for x in collapsed if _month(int(x["event_time_ms"])) == month]
                lineage = {"document_type": f"{PRODUCT}_partition_lineage", "schema_version": 1, "required_product": PRODUCT,
                           "native_symbol": source.native_symbol, "utc_month": month, "row_count": len(rows),
                           "physical_row_count": len(rows) + len(month_collapsed), "collapsed_identical_row_count": len(month_collapsed),
                           "schema_sha256": SCHEMA_SHA256, "writer_identity": writer_identity(), "parquet_path": str(ppath.relative_to(tree.root)),
                           "parquet_sha256": psha, "raw_objects": [_lineage_source(source)], "collapsed_identical_source_rows": month_collapsed,
                           "point_ordinals": [int(r["point_ordinal"]) for r in rows]}
                lpath, lsha, lreused = _publish_json(tree, lineage, (".lineage", source.native_symbol, month), "lineage", hooks)
                partitions.append(PublishedPartition(source.native_symbol, month, len(rows), ppath, psha, lpath, lsha, preused and lreused))
                del table
                del rows
                del month_records
                del month_collapsed
                del lineage
            for month, gap_rows in _monthly_gap_rows(source, runs):
                table = pa.Table.from_pylist(gap_rows, schema=GAP_SCHEMA)
                gpath, gsha, greused = _publish_table(tree, table, GAP_SCHEMA, (".quality-gaps", source.native_symbol, month), "quality-gap", hooks)
                lineage = {"document_type": f"{PRODUCT}_quality_gap_lineage", "schema_version": 1, "required_product": PRODUCT,
                           "native_symbol": source.native_symbol, "utc_month": month, "row_count": len(gap_rows),
                           "parquet_path": str(gpath.relative_to(tree.root)), "parquet_sha256": gsha,
                           "raw_objects": [_lineage_source(source)],
                           "runs": [{"start_ms": r["missing_run_start_ms"], "end_ms": r["missing_run_end_ms"],
                                     "expected_grid_count": r["expected_grid_count"]} for r in gap_rows]}
                lpath, lsha, lreused = _publish_json(tree, lineage, (".quality-gap-lineage", source.native_symbol, month), "quality-gap-lineage", hooks)
                gaps.append(PublishedGap("all_input_missing", len(gap_rows), gpath, gsha, lpath, lsha, greused and lreused))
                del table
                del gap_rows
                del lineage
            del records
            del collapsed
            del observed
            del runs
        authority_rows = [_gap_row(symbol, "authority", None, None, 0, "coinalyze_symbol_unmapped", "accepted native identity has no retained Coinalyze provider mapping") for symbol in sorted(unmapped_symbols)]
        if authority_rows:
            table = pa.Table.from_pylist(authority_rows, schema=GAP_SCHEMA)
            gpath, gsha, greused = _publish_table(tree, table, GAP_SCHEMA, (".authority-gaps",), "authority-gap", hooks)
            lineage = {"document_type": f"{PRODUCT}_authority_gap_lineage", "schema_version": 1, "required_product": PRODUCT,
                       "row_count": len(authority_rows), "gap_kind": "coinalyze_symbol_unmapped", "report_sha256": report_sha256,
                       "parquet_path": str(gpath.relative_to(tree.root)), "parquet_sha256": gsha}
            lpath, lsha, lreused = _publish_json(tree, lineage, (".authority-gap-lineage",), "authority-gap-lineage", hooks)
            gaps.append(PublishedGap("coinalyze_symbol_unmapped", len(authority_rows), gpath, gsha, lpath, lsha, greused and lreused))
        _require(physical_total - collapsed_total == row_total, "global physical/collapsed/product equation failed")
        _require(row_total + missing_total == request_total, "observed/missing/request equation failed")
        _require(row_total <= PROJECTED_POINTS and len(all_months) <= PROJECTED_PARTITIONS, "accepted sizing ceiling exceeded")
        if enforce_full_corpus:
            _require(len(ordered) == ACCEPTED_RESPONSES and sum(x.byte_size for x in ordered) == ACCEPTED_RESPONSE_BYTES, "full response inventory changed")
            _require(len(mappings) == ACCEPTED_SELECTED_MAPPINGS and len(unmapped_symbols) == ACCEPTED_UNMAPPED, "accepted identity inventory changed")
            _require(request_total == PROJECTED_POINTS and len(all_months) == PROJECTED_PARTITIONS, "full request calendar changed")
            _require(inventory is not None and inventory.source_sha256 == INVENTORY_SHA256 and inventory.byte_size == INVENTORY_BYTES, "inventory proof changed")
            _require(inventory.mapping_count == ACCEPTED_BINANCE_PERPETUAL_MAPPINGS and inventory.market_count == ACCEPTED_INVENTORY_MARKETS, "inventory counts changed")
        completion = {"document_type": f"{PRODUCT}_product_completion", "schema_version": 1, "required_product": PRODUCT,
                      "schema_sha256": SCHEMA_SHA256, "writer_identity": writer_identity(),
                      "normalizer_source_sha256": hashlib.sha256(_read_regular(Path(__file__).resolve(strict=True), 2 * 2**20)).hexdigest(),
                      "authority_sha256": {"generation0_seal_head": GENERATION0_SEAL, "report": report_sha256, "sizing": sizing_sha256, "schema": SCHEMA_SHA256},
                      "source_semantics": {"provider": "Coinalyze", "amount_unit": "base_asset", "aggregation": "daily_close_derived",
                                           "censorship": {"known_from_utc_day": CENSORSHIP_START, "before_state": "not_asserted_complete"},
                                           "event_available_at": None, "availability_state": UNKNOWN_AVAILABILITY},
                      "inventory": None if inventory is None else {"source_sha256": inventory.source_sha256, "byte_size": inventory.byte_size,
                          "market_count": inventory.market_count, "binance_perpetual_mapping_count": inventory.mapping_count, "selected_mapping_count": len(mappings)},
                      "row_equation": {"responses": len(ordered), "physical_source_rows": physical_total, "collapsed_identical_rows": collapsed_total,
                          "product_rows": row_total, "inclusive_requested_slots": request_total, "missing_daily_slots": missing_total,
                          "excluded_source_rows": 0, "imputed_rows": 0, "converted_to_usd_rows": 0},
                      "partition_calendar": {"requested_symbol_months": len(all_months), "nonempty_data_partitions": len(partitions),
                                             "gap_only_months": len(all_months - {(p.native_symbol, p.utc_month) for p in partitions})},
                      "authority_gap_rows": len(unmapped_symbols), "comparison": {"path": str(comparison_path.relative_to(tree.root)),
                          "sha256": comparison_sha, "entry_count": len(comparison["entries"]), "disposition": "pending_reviewer"},
                      "partitions": [{"native_symbol": p.native_symbol, "utc_month": p.utc_month, "row_count": p.row_count,
                                      "parquet_path": str(p.parquet_path.relative_to(tree.root)), "parquet_sha256": p.parquet_sha256,
                                      "lineage_path": str(p.lineage_path.relative_to(tree.root)), "lineage_sha256": p.lineage_sha256} for p in partitions],
                      "gaps": [{"kind": g.kind, "row_count": g.row_count, "parquet_path": str(g.parquet_path.relative_to(tree.root)),
                                "parquet_sha256": g.parquet_sha256, "lineage_path": str(g.lineage_path.relative_to(tree.root)),
                                "lineage_sha256": g.lineage_sha256} for g in gaps],
                      "sizing_ceiling": {"projected_points": PROJECTED_POINTS, "partition_count": PROJECTED_PARTITIONS,
                                         "projected_normalized_bytes": PROJECTED_NORMALIZED_BYTES, "largest_partition_bytes": LARGEST_PARTITION_BYTES}}
        digest = hashlib.sha256(_canonical_json(completion)).hexdigest()
        tree.only_completion(f"{digest}.json")
        cpath, csha, creused = _publish_json(tree, completion, (".complete",), "completion", hooks)
        _require(csha == digest, "completion identity changed")
        tree.only_completion(f"{digest}.json")
        return LiquidationNormalizationResult(SCHEMA_SHA256, tuple(partitions), tuple(gaps), comparison_path, comparison_sha,
                                               len(comparison["entries"]), cpath, csha, creused, physical_total,
                                               collapsed_total, row_total, missing_total, len(unmapped_symbols))
    finally:
        tree.close()


def _read_pinned(path: Path, digest: str, maximum: int) -> Mapping[str, Any]:
    value = _strict_json(_read_regular(path, maximum, digest=digest), maximum=maximum)
    _require(type(value) is dict, "pinned authority is not an object")
    return value


def _report_authority(report: Mapping[str, Any]) -> tuple[set[str], tuple[str, ...], list[OverlapReceipt]]:
    block = report.get("coinalyze")
    _require(type(block) is dict, "report lacks Coinalyze authority")
    support = block.get("universe_support")
    _require(type(support) is dict, "report lacks universe support")
    mapped = tuple(support.get("supported_symbols", []))
    unmapped = tuple(support.get("unmapped_symbols", []))
    _require(support.get("supported_count") == len(mapped) and support.get("unmapped_count") == len(unmapped), "report universe counts changed")
    _require(
        len(mapped) == ACCEPTED_SELECTED_MAPPINGS
        and len(unmapped) == ACCEPTED_UNMAPPED
        and support.get("universe_size") == len(mapped) + len(unmapped),
        "report accepted universe changed",
    )
    _require(len(set(mapped)) == len(mapped) and len(set(unmapped)) == len(unmapped) and not (set(mapped) & set(unmapped)), "report identity sets are not disjoint and unique")
    products = report.get("product_matrix")
    _require(type(products) is list, "report lacks product matrix")
    product_rows = [x for x in products if type(x) is dict and x.get("product") == PRODUCT]
    _require(len(product_rows) == 1, "report liquidation product authority is not unique")
    product = product_rows[0]
    _require(product.get("accepted_universe_object_count") == 0 and product.get("listed_bytes") == 0 and product.get("listed_object_count") == 0,
             "report liquidation archive inventory changed")
    _require(product.get("typed_gap_symbols") == list(unmapped) and product.get("coverage_gap_kinds") == ["coinalyze_symbol_unmapped"],
             "report liquidation authority gaps changed")
    provenance = block.get("provenance")
    _require(type(provenance) is list, "report lacks Coinalyze provenance")
    receipts: list[OverlapReceipt] = []
    for endpoint, (sha, size, retrieved) in OVERLAP.items():
        hits = [x for x in provenance if type(x) is dict and x.get("path") == endpoint]
        _require(len(hits) == 1, "report overlap provenance is not unique")
        row = hits[0]
        _require(
            row.get("sha256") == sha and row.get("byte_size") == size,
            "report overlap provenance changed",
        )
        _require(row.get("params") == {"from": "1577836800", "interval": "daily", "symbols": "BTCUSDT_PERP.A,ETHUSDT_PERP.A", "to": "1609459200"}, "report overlap parameters changed")
        _require(row.get("retrieved_at") == retrieved and row.get("status_code") == 200, "report overlap retrieval changed")
        raw_path = row.get("content_path")
        _require(type(raw_path) is str, "report overlap path missing")
        receipts.append(OverlapReceipt(endpoint, Path(raw_path), sha, size, retrieved))
    return set(mapped), unmapped, receipts


def _inventory_report_receipt(report: Mapping[str, Any]) -> Mapping[str, Any]:
    block = report.get("coinalyze")
    _require(type(block) is dict, "report lacks Coinalyze authority")
    provenance = block.get("provenance")
    _require(type(provenance) is list, "report lacks Coinalyze provenance")
    rows = [
        row
        for row in provenance
        if type(row) is dict and row.get("path") == INVENTORY_PATH
    ]
    _require(len(rows) == 1, "report inventory receipt is not unique")
    receipt = rows[0]
    _require(
        receipt.get("sha256") == INVENTORY_SHA256
        and receipt.get("byte_size") == INVENTORY_BYTES
        and receipt.get("params") == {}
        and receipt.get("status_code") == 200,
        "report inventory receipt changed",
    )
    _iso_time(str(receipt.get("retrieved_at")))
    _require(
        type(receipt.get("content_path")) is str,
        "report inventory content path is missing",
    )
    return receipt


def _inventory_mappings(body: bytes, accepted: set[str]) -> tuple[dict[str, LiquidationMapping], int, int, str]:
    root = _strict_json(body, maximum=MAX_INVENTORY_BYTES)
    _require(type(root) is list, "inventory is not a list")
    all_mappings: dict[str, LiquidationMapping] = {}
    for row in root:
        if type(row) is not dict or row.get("exchange") != "A":
            continue
        _require(type(row.get("is_perpetual")) is bool, "inventory perpetual flag is not boolean")
        if not row["is_perpetual"]:
            continue
        native_value = row.get("symbol_on_exchange")
        provider = row.get("symbol")
        _require(
            type(native_value) is str,
            "inventory native mapping is not a string",
        )
        native = native_value.strip().upper()
        _require(
            bool(native)
            and type(provider) is str
            and provider == coinalyze_perp_symbol(native),
            "inventory mapping identity changed",
        )
        base_value = row.get("base_asset")
        quote_value = row.get("quote_asset")
        base = base_value if type(base_value) is str else ""
        quote = quote_value if type(quote_value) is str else ""
        if native in accepted:
            _require(
                row.get("oi_lq_vol_denominated_in") == "BASE_ASSET",
                "selected liquidation unit is not base asset",
            )
            _require(bool(base) and bool(quote), "selected inventory asset mapping missing")
        _require(native not in all_mappings, "inventory repeats a native mapping")
        all_mappings[native] = LiquidationMapping(native, provider, base, quote)
    digest = hashlib.sha256(compact_json([{"native_symbol": k, "provider_symbol": v.provider_symbol} for k, v in sorted(all_mappings.items())])).hexdigest()
    _require(accepted <= set(all_mappings), "selected mapping is absent from inventory")
    return {k: all_mappings[k] for k in sorted(accepted)}, len(root), len(all_mappings), digest


def load_generation0_authority(state_path: Path, content_root: Path, report: Mapping[str, Any]) -> tuple[tuple[RawLiquidationObject, ...], dict[str, LiquidationMapping], tuple[str, ...], InventoryProof]:
    mapped, unmapped, _receipts = _report_authority(report)
    retained_receipt = _inventory_report_receipt(report)
    _no_symlinks(state_path, "generation-0 state")
    _no_symlinks(content_root, "generation-0 content")
    parent = state_path.absolute().parent
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    state_fd = _open_regular_child(parent_fd, state_path.name, "generation-0 SQLite state")
    _require(state_fd is not None, "generation-0 SQLite state is missing")
    sidecars = {name: _open_regular_child(parent_fd, name, f"SQLite sidecar {name}")
                for name in (f"{state_path.name}-wal", f"{state_path.name}-shm", f"{state_path.name}-journal")}
    connection: sqlite3.Connection | None = None
    borrowed: AcquisitionState | None = None
    try:
        connection = sqlite3.connect(f"file:/proc/self/fd/{parent_fd}/{state_path.name}?mode=ro", uri=True, isolation_level=None)
        reopened = _open_regular_child(parent_fd, state_path.name, "generation-0 SQLite state")
        _require(reopened is not None, "generation-0 SQLite state disappeared")
        assert state_fd is not None and reopened is not None
        before = os.fstat(state_fd)
        after = os.fstat(reopened)
        os.close(reopened)
        _require((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino), "generation-0 SQLite state was replaced")
        for name, held in sidecars.items():
            observed = _open_regular_child(parent_fd, name, f"SQLite sidecar {name}")
            if held is None:
                _require(observed is None, "a SQLite sidecar appeared during read-only open")
            else:
                _require(observed is not None, "a SQLite sidecar disappeared during read-only open")
                assert observed is not None
                old = os.fstat(held)
                new = os.fstat(observed)
                _require((old.st_dev, old.st_ino) == (new.st_dev, new.st_ino), "a SQLite sidecar was replaced")
            if observed is not None:
                os.close(observed)
        register_domain_functions(connection)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        _require(connection.execute("PRAGMA application_id").fetchone()[0] == STATE_APPLICATION_ID and connection.execute("PRAGMA user_version").fetchone()[0] == STATE_USER_VERSION, "generation-0 SQLite identity changed")
        _require(connection.execute("PRAGMA integrity_check").fetchone() == ("ok",) and not connection.execute("PRAGMA foreign_key_check").fetchall(), "generation-0 SQLite is inconsistent")
        borrowed = AcquisitionState(state_path, state_path.with_name("acquisition.lock"))
        borrowed.conn = connection
        borrowed.authenticate_schema()
        borrowed.authenticate_domains()
        borrowed.authenticate_singletons()
        borrowed.authenticate_prefix()
        borrowed._require_runnable_head()
        head = borrowed.seal_head_row()
        _require(
            head is not None and head["receipt_sha256"] == GENERATION0_SEAL,
            "generation-0 terminal seal changed",
        )
        _require(connection.execute("SELECT COUNT(*) FROM completion WHERE provider='binance_vision'").fetchone()[0] == ACCEPTED_BINANCE_COMPLETIONS, "Binance completion inventory changed")
        _require(connection.execute("SELECT COUNT(*) FROM sidecar_fact WHERE provider=?", (PROVIDER_COINALYZE,)).fetchone()[0] == 0, "Coinalyze completion carries a Binance sidecar fact")
        rows = connection.execute("SELECT p.identity,p.kind,p.payload_json,c.content_sha256,c.content_path,c.listed_bytes,c.retrieved_at,c.validation_state,c.revision_json,c.sidecar_sha256,c.sidecar_path FROM plan_entry p JOIN completion c ON c.provider=p.provider AND c.identity=p.identity WHERE p.provider=? ORDER BY p.identity", (PROVIDER_COINALYZE,)).fetchall()
        inventory_rows = [r for r in rows if r[1] == KIND_COINALYZE_INVENTORY]
        liquidation_rows = [r for r in rows if r[1] == KIND_COINALYZE_LIQUIDATION]
        _require(len(inventory_rows) == 1 and len(liquidation_rows) == ACCEPTED_RESPONSES, "Coinalyze completion inventory changed")
        inv = inventory_rows[0]
        envelope = _strict_json(str(inv[2]).encode(), maximum=MAX_REPORT_BYTES)
        _require(type(envelope) is dict and envelope.get("provider") == PROVIDER_COINALYZE and envelope.get("identity") == inv[0] and envelope.get("kind") == KIND_COINALYZE_INVENTORY, "inventory plan envelope changed")
        payload = envelope.get("payload")
        _require(
            type(payload) is dict
            and payload.get("path") == INVENTORY_PATH
            and payload.get("params") == {},
            "inventory plan payload changed",
        )
        inventory_revision = _strict_json(
            str(inv[8]).encode(), maximum=MAX_REPORT_BYTES
        )
        _require(
            inv[7] == OUTCOME_RETAINED_INVENTORY
            and inventory_revision == {"retained": True}
            and inv[9] is None
            and inv[10] is None,
            "inventory completion state changed",
        )
        isha = str(inv[3])
        _require(
            isha == INVENTORY_SHA256 and int(inv[5]) == INVENTORY_BYTES,
            "inventory raw identity changed",
        )
        _require(inv[0] == f"{PROVIDER_COINALYZE}:{INVENTORY_PATH}" and payload.get("url") == f"{COINALYZE_BASE}{INVENTORY_PATH}", "inventory request identity changed")
        _require(payload.get("accepted_digest") == isha and payload.get("accepted_bytes") == INVENTORY_BYTES,
                 "inventory retained-content binding changed")
        _require(
            payload.get("accepted_path") == retained_receipt.get("content_path")
            and str(inv[6]) == retained_receipt.get("retrieved_at"),
            "inventory retained receipt binding changed",
        )
        ipath = content_root / isha[:2] / isha
        _require(
            Path(str(inv[4])) == ipath,
            "inventory content-address path changed",
        )
        ibody = _read_regular(ipath, MAX_INVENTORY_BYTES, digest=isha, size=INVENTORY_BYTES)
        retained_body = _read_regular(
            Path(str(retained_receipt["content_path"])),
            MAX_INVENTORY_BYTES,
            digest=isha,
            size=INVENTORY_BYTES,
        )
        _require(retained_body == ibody, "retained and generation-0 inventory bytes differ")
        mappings, market_count, mapping_count, mapping_digest = _inventory_mappings(ibody, mapped)
        _require(
            mapping_digest == INVENTORY_MAPPING_SHA256,
            "pinned inventory mapping digest changed",
        )
        _require(payload.get("inventory_mapping_count") == mapping_count and payload.get("inventory_mapping_digest") == mapping_digest, "inventory mapping proof changed")
        declared = sorted((x.get("native_symbol"), x.get("provider_symbol")) for x in payload.get("accepted_mappings", []) if type(x) is dict)
        _require(declared == sorted((k, v.provider_symbol) for k, v in mappings.items()), "selected inventory mappings changed")
        inventory = InventoryProof(ipath, isha, INVENTORY_BYTES, str(inv[0]), str(inv[6]), mapping_count, mapping_digest, market_count)
        sources: list[RawLiquidationObject] = []
        for row in liquidation_rows:
            identity, kind, payload_json, sha, cpath, size, retrieved, state, revision_json, side_sha, side_path = row
            env = _strict_json(str(payload_json).encode(), maximum=MAX_REPORT_BYTES)
            revision = _strict_json(
                str(revision_json).encode(), maximum=MAX_REPORT_BYTES
            )
            _require(type(env) is dict and env.get("provider") == PROVIDER_COINALYZE and env.get("identity") == identity and env.get("kind") == kind, "liquidation plan envelope changed")
            p = env.get("payload")
            _require(type(p) is dict, "liquidation plan payload missing")
            native = p.get("native_symbol")
            provider = p.get("provider_symbol")
            mapping = mappings.get(native)
            _require(mapping is not None and provider == mapping.provider_symbol, "liquidation plan mapping changed")
            params = p.get("params")
            _require(type(params) is dict, "liquidation params missing")
            expected_params = {"symbols": provider, "interval": "daily", "from": str(params.get("from")), "to": str(params.get("to")), "convert_to_usd": "false"}
            _require(params == expected_params, "liquidation request parameters changed")
            _require(set(p) == {"path", "url", "query", "params", "native_symbol", "provider_symbol"}, "liquidation plan payload fields changed")
            query = urlencode(expected_params)
            _require(
                p.get("path") == LIQUIDATION_PATH
                and p.get("query") == query
                and p.get("url") == f"{COINALYZE_BASE}{LIQUIDATION_PATH}",
                "liquidation request identity changed",
            )
            _require(
                identity == f"{LIQUIDATION_PATH}?{query}",
                "liquidation plan identity changed",
            )
            _require(state == OUTCOME_CHECKSUM_VERIFIED and type(revision) is dict and set(revision) == {"points", "status"}
                     and type(revision.get("status")) is int and revision.get("status") == 200
                     and type(revision.get("points")) is int, "liquidation completion status changed")
            _require(side_sha is None and side_path is None, "Coinalyze completion has Binance sidecar fields")
            raw_sha = str(sha)
            expected_path = content_root / raw_sha[:2] / raw_sha
            _require(
                Path(str(cpath)) == expected_path,
                "liquidation content-address path changed",
            )
            sources.append(RawLiquidationObject(str(identity), native, provider, mapping.base_asset, mapping.quote_asset, expected_path, raw_sha, int(size), str(retrieved), int(params["from"]), int(params["to"]), int(revision.get("points")), int(revision.get("status")), str(state)))
        connection.execute("ROLLBACK")
        borrowed.conn = None
        return tuple(sources), mappings, unmapped, inventory
    except sqlite3.Error as exc:
        raise LiquidationNormalizationError(
            "generation-0 authority cannot be read safely"
        ) from exc
    finally:
        if borrowed is not None:
            borrowed.conn = None
        if connection is not None:
            connection.close()
        for fd in sidecars.values():
            if fd is not None:
                os.close(fd)
        if state_fd is not None:
            os.close(state_fd)
        os.close(parent_fd)


def normalize_from_authorities(*, generation0_state: Path, generation0_content_root: Path, report: Path, sizing: Path,
                               bar_product_root: Path, open_interest_product_root: Path, funding_product_root: Path,
                               output_root: Path, hooks: PublicationHooks = PublicationHooks()) -> LiquidationNormalizationResult:
    report_doc = _read_pinned(report, REPORT_SHA256, MAX_REPORT_BYTES)
    sizing_doc = _read_pinned(sizing, SIZING_SHA256, MAX_SIZING_BYTES)
    coinalyze = sizing_doc.get("coinalyze")
    _require(type(coinalyze) is dict, "sizing lacks Coinalyze bounds")
    _require(coinalyze.get("liquidation_receipts") == ACCEPTED_RESPONSES and coinalyze.get("inventory_receipts") == 1, "sizing receipt bounds changed")
    _require(coinalyze.get("projected_points") == PROJECTED_POINTS and coinalyze.get("partition_count") == PROJECTED_PARTITIONS, "sizing row/partition bounds changed")
    _require(coinalyze.get("projected_normalized_bytes") == PROJECTED_NORMALIZED_BYTES and coinalyze.get("largest_partition_bytes") == LARGEST_PARTITION_BYTES, "sizing byte bounds changed")
    sources, mappings, unmapped, inventory = load_generation0_authority(generation0_state, generation0_content_root, report_doc)
    _mapped, _unmapped, overlap = _report_authority(report_doc)
    officials = (OfficialProductAuthority(PRODUCT_BAR_1H, bar_product_root, OFFICIAL_COMPLETIONS[PRODUCT_BAR_1H]),
                 OfficialProductAuthority(PRODUCT_OPEN_INTEREST_5M, open_interest_product_root, OFFICIAL_COMPLETIONS[PRODUCT_OPEN_INTEREST_5M]),
                 OfficialProductAuthority(PRODUCT_FUNDING_REALIZED, funding_product_root, OFFICIAL_COMPLETIONS[PRODUCT_FUNDING_REALIZED]))
    return normalize_liquidation_sources(sources, mappings, unmapped, overlap, officials, output_root,
                                         inventory=inventory, enforce_full_corpus=True, hooks=hooks)
