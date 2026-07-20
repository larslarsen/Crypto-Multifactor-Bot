"""Bybit public trade-archive normalizer (BYB-001).

Normalizes explicitly registered local Bybit perpetual-trade ``.csv.gz``
archives into a source-specific typed trade dataset with RAW/MAN lineage.

No network, no filename identity, no trade-to-bar aggregation, no invented
inverse base/quote volumes. Streaming bounded gzip/CSV only.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
import zlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, BinaryIO, TextIO

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
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.contracts import RawObject
from cryptofactors.ingest.raw.paths import assert_regular_nonsymlink_file

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

BYBIT_TRADE_DATASET_TYPE = "bybit_trade_source"
BYBIT_TRADE_SCHEMA_NAME = "bybit_trade_source"
BYBIT_TRADE_SCHEMA_VERSION = "1"
BYBIT_TRADE_TRANSFORM_NAME = "bybit_trade_normalizer"
BYBIT_TRADE_TRANSFORM_VERSION = "1"

_SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")
_SAFE_PATH_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
# Audited source timestamps: unsigned decimal seconds (no sign, no exponent).
_UNSIGNED_DECIMAL_SECONDS = re.compile(r"^[0-9]+(\.[0-9]+)?$")

_AUDITED_HEADER: tuple[str, ...] = (
    "timestamp",
    "symbol",
    "side",
    "size",
    "price",
    "tickDirection",
    "trdMatchID",
    "grossValue",
    "homeNotional",
    "foreignNotional",
)
_FIELD_COUNT = 10

_VALID_SIDES_RAW = frozenset({"Buy", "Sell"})
_VALID_TICK_DIRECTIONS = frozenset(
    {"PlusTick", "MinusTick", "ZeroPlusTick", "ZeroMinusTick"}
)

_CONTRACT_STYLES: dict[str, dict[str, str]] = {
    "linear": {
        "market_type": "usdm",
        "size_unit": "base_asset",
        "schema_variant": "linear_base_size",
    },
    "inverse": {
        "market_type": "coinm",
        "size_unit": "contracts",
        "schema_variant": "inverse_contract_size",
    },
}

_DEFAULT_MAX_DECOMPRESSED_BYTES = 209_715_200  # 200 MiB
_DEFAULT_MAX_ROWS = 5_000_000

_DECIMAL_PRECISION = 38
_DECIMAL_SCALE = 18
# event_time UTC range used during parse (not only coverage)
_MIN_EVENT_SEC = 0
_MAX_EVENT_SEC = 4_102_444_800  # 2100-01-01


# ---------------------------------------------------------------------------
# Public result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BybitTradeNormalizeResult:
    """Staged artifacts + MAN-001 PublishPlan (not yet published)."""

    publish_plan: PublishPlan
    trade_paths: tuple[Path, ...]
    quality_paths: tuple[Path, ...]
    issues: tuple[QualityIssue, ...]


@dataclass
class _TradeRow:
    venue_id: str
    instrument_id: str
    market_type: str
    contract_style: str
    schema_variant: str
    size_unit: str
    event_time: int  # UTC us
    source_timestamp: str  # exact source token
    source_timestamp_unit: str
    source_symbol: str
    side: str  # buy | sell
    size: Decimal
    price: Decimal
    tick_direction: str
    trade_match_id: str
    gross_value: Decimal
    home_notional: Decimal
    foreign_notional: Decimal
    raw_object_id: str
    source_row_number: int  # 1-based data rows

    def economic_fingerprint(self) -> str:
        """Content identity for duplicate classification (excludes lineage row #)."""
        payload = {
            "event_time": self.event_time,
            "source_timestamp": self.source_timestamp,
            "source_symbol": self.source_symbol,
            "side": self.side,
            "size": str(self.size),
            "price": str(self.price),
            "tick_direction": self.tick_direction,
            "trade_match_id": self.trade_match_id,
            "gross_value": str(self.gross_value),
            "home_notional": str(self.home_notional),
            "foreign_notional": str(self.foreign_notional),
            "contract_style": self.contract_style,
            "size_unit": self.size_unit,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@dataclass
class _ObjectWork:
    raw_object_id: str
    trade_path: Path
    quality_path: Path
    rows: list[_TradeRow] = field(default_factory=list)
    issues: list[QualityIssue] = field(default_factory=list)
    ordering: str = "empty"  # empty | ascending | descending | mixed | single


class _LimitExceeded(Exception):
    pass


class _RowError(Exception):
    def __init__(self, code: str, message: str, *, column: str | None) -> None:
        super().__init__(message)
        self.code = code
        self.column = column


# ---------------------------------------------------------------------------
# Bounded decompressed stream (RawIOBase + BufferedReader)
# ---------------------------------------------------------------------------


class _BoundedRawReader(io.RawIOBase):
    """Binary raw stream that fails closed when read bytes exceed a hard max.

    Never issues an underlying read larger than ``remaining + 1``, so a single
    unbounded ``read(-1)`` cannot allocate past the limit before checking.
    """

    def __init__(self, raw: BinaryIO, *, max_bytes: int, label: str) -> None:
        super().__init__()
        self._raw = raw
        self._max = max_bytes
        self._n = 0
        self._label = label

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def readinto(self, b: Any) -> int:
        if self.closed:
            raise ValueError("I/O operation on closed file")
        dest = memoryview(b).cast("B")
        if len(dest) == 0:
            return 0
        remaining = self._max - self._n
        # Exact limit is allowed; only content beyond the limit fails.
        # When remaining is 0, probe one byte for true EOF vs overflow.
        if remaining <= 0:
            probe = self._raw.read(1)
            if not probe:
                return 0
            raise _LimitExceeded(
                f"{self._label} exceeded max_decompressed_bytes={self._max}"
            )
        # Cap request to remaining+1 so overflow is detected without huge alloc.
        want = min(len(dest), remaining + 1)
        chunk = self._raw.read(want)
        if not chunk:
            return 0
        if self._n + len(chunk) > self._max:
            raise _LimitExceeded(
                f"{self._label} exceeded max_decompressed_bytes={self._max}"
            )
        self._n += len(chunk)
        dest[: len(chunk)] = chunk
        return len(chunk)

    def read(self, size: int = -1) -> bytes:
        if self.closed:
            raise ValueError("I/O operation on closed file")
        # Preserve zero-length read semantics: never probe/consume underlying.
        if size == 0:
            return b""
        remaining = self._max - self._n
        # Exact limit is allowed; only content beyond the limit fails.
        if remaining <= 0:
            probe = self._raw.read(1)
            if not probe:
                return b""
            raise _LimitExceeded(
                f"{self._label} exceeded max_decompressed_bytes={self._max}"
            )
        if size is None or size < 0:
            to_read = remaining + 1
        else:
            to_read = min(size, remaining + 1)
        chunk = self._raw.read(to_read)
        if not chunk:
            return b""
        if self._n + len(chunk) > self._max:
            raise _LimitExceeded(
                f"{self._label} exceeded max_decompressed_bytes={self._max}"
            )
        self._n += len(chunk)
        return chunk

    def close(self) -> None:
        # Do not close underlying gzip here — owner closes in order.
        if not self.closed:
            super().close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_code_commit(code_commit: str) -> str:
    commit = code_commit.strip()
    if not commit or commit == "unknown":
        raise ValueError(
            "code_commit is required and must be a non-empty immutable code "
            "identity supplied by the caller (not 'unknown')"
        )
    return commit


def _resolve_config_sha256(
    config_sha256: str | None,
    *,
    payload: Mapping[str, Any],
) -> str:
    if config_sha256 is not None and str(config_sha256).strip() != "":
        digest = str(config_sha256).strip().lower()
        if not _SHA256_HEX_RE.fullmatch(digest):
            raise ValueError(
                "config_sha256 must be a 64-character lowercase hex SHA-256 digest"
            )
        return digest
    body = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _require_canonical_path_token(label: str, value: str) -> str:
    """Require value already be the canonical path token (no silent strip rewrite)."""
    if value != value.strip():
        raise ValueError(
            f"{label} must not have leading/trailing whitespace: {value!r}"
        )
    if not value or not _SAFE_PATH_TOKEN.fullmatch(value):
        raise ValueError(
            f"invalid {label} for partition path: {value!r} "
            "(must be a single alphanumeric token with ._- only)"
        )
    return value


def _resolve_contract_style(contract_style: str) -> dict[str, str]:
    key = contract_style.strip().lower()
    if key not in _CONTRACT_STYLES:
        raise ValueError(
            f"contract_style must be 'linear' or 'inverse'; got {contract_style!r}"
        )
    return {"contract_style": key, **_CONTRACT_STYLES[key]}


# Timestamp unscaled-µs digit budget: 4102444800e6 fits in 16 digits.
_TS_MAX_UNSCALED_DIGITS = 16


def _unscaled_int_from_decimal(
    d: Decimal,
    *,
    scale: int,
    max_digits: int,
) -> int | None:
    """Return integer coefficient for d * 10^scale, or None if not exact / overflow.

    Uses only ``Decimal.as_tuple()`` integer digit arithmetic — independent of the
    ambient Decimal context precision.

    Digit-length / magnitude bounds are applied **before** constructing ``coeff``
    so large CSV tokens cannot burn CPU on arbitrary-precision integers
    (REVIEW-0047 remaining #1). ``max_digits`` is 38 for decimal128 fields and
    16 for timestamp microseconds.
    """
    if not d.is_finite():
        return None
    sign, digits, exp = d.as_tuple()
    digs = list(digits)
    # All-zero coefficient is exact zero regardless of exponent (REVIEW-0047 #2).
    if not digs or all(x == 0 for x in digs):
        return 0
    # value = ± coeff * 10^exp; unscaled = ± coeff * 10^(exp+scale)
    power = int(exp) + scale
    if power < 0:
        cut = -power
        if cut > len(digs):
            # All significant digits lie beyond the target scale (e.g. 1e-13 us).
            if any(x != 0 for x in digs):
                return None
            return 0
        if any(x != 0 for x in digs[len(digs) - cut :]):
            return None
        digs = digs[: len(digs) - cut]
        power = 0
        if not digs or all(x == 0 for x in digs):
            return 0
    # Bound unscaled digit count BEFORE building coeff / 10**power.
    # Resulting digit length is len(digs) + power (power >= 0 here).
    result_digits = len(digs) + power
    if result_digits > max_digits:
        return None
    # Safe to construct: at most max_digits digits.
    coeff = 0
    for dig in digs:
        coeff = coeff * 10 + dig
    unscaled = coeff * (10**power) if power > 0 else coeff
    if unscaled >= 10**max_digits:
        return None
    return -unscaled if sign else unscaled


def _is_sub_scale_nonzero(d: Decimal, *, scale: int) -> bool:
    """True if d is nonzero only in fractional digits beyond ``scale`` places."""
    if not d.is_finite() or d.is_zero():
        return False
    _sign, digits, exp = d.as_tuple()
    digs = list(digits)
    if not digs or all(x == 0 for x in digs):
        return False
    frac = max(0, -int(exp))
    if frac <= scale:
        return False
    cut = frac - scale
    # Nonzero mass entirely (or partially) past the scale boundary.
    if cut >= len(digs):
        return any(x != 0 for x in digs)
    return any(x != 0 for x in digs[len(digs) - cut :])


def _canonical_decimal128_38_18(d: Decimal, *, field: str) -> Decimal:
    """Exact Arrow-safe Decimal for decimal128(38, 18), or raise ValueError."""
    unscaled = _unscaled_int_from_decimal(
        d, scale=_DECIMAL_SCALE, max_digits=_DECIMAL_PRECISION
    )
    if unscaled is None:
        raise ValueError(
            f"{field} exceeds decimal128({_DECIMAL_PRECISION},{_DECIMAL_SCALE}) "
            f"without rounding: {d}"
        )
    # Canonical representation: integer unscaled * 10^-scale via as_tuple path
    # Positive and negative zero share the same representation.
    if unscaled == 0:
        return Decimal((0, (0,), 0))
    neg = unscaled < 0
    abs_u = -unscaled if neg else unscaled
    digs = tuple(int(ch) for ch in str(abs_u))
    return Decimal((1 if neg else 0, digs, -_DECIMAL_SCALE))


def _timestamp_token_to_utc_us(token: str) -> int:
    """Parse exact source timestamp token to UTC microseconds.

    Token must match unsigned decimal-seconds grammar (no sign, no exponent).
    Microsecond conversion uses digit arithmetic only (no ambient context).
    Integrality is separate from decimal128 precision (REVIEW-0047 #4).
    """
    if not _UNSIGNED_DECIMAL_SECONDS.fullmatch(token):
        raise ValueError(
            f"timestamp must be unsigned decimal seconds without exponent: {token!r}"
        )
    # String->Decimal is exact for this grammar; multiplication is not used.
    try:
        d = Decimal(token)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"non-decimal timestamp token: {token!r}") from exc
    if not d.is_finite() or d < 0:
        raise ValueError(f"invalid timestamp token: {token!r}")
    # Exact * 1_000_000 via as_tuple integer math (no decimal128 ceiling).
    event_us = _unscaled_int_from_decimal(
        d, scale=6, max_digits=_TS_MAX_UNSCALED_DIGITS
    )
    if event_us is None:
        # Tiny nonzero past microsecond scale -> sub-microsecond, not range
        # (e.g. 0.0000000000001) — REVIEW-0047 remaining #2.
        if _is_sub_scale_nonzero(d, scale=6):
            raise ValueError(f"timestamp has sub-microsecond precision: {token!r}")
        raise ValueError(f"timestamp out of supported UTC range: {token!r}")
    if event_us < 0:
        raise ValueError(f"invalid timestamp token: {token!r}")
    sec = event_us // 1_000_000
    if sec < _MIN_EVENT_SEC or sec > _MAX_EVENT_SEC:
        raise ValueError(f"timestamp out of supported UTC range: {token!r}")
    return event_us


def _parse_positive_decimal(token: str, *, field: str) -> Decimal:
    try:
        d = Decimal(token)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid {field}: {token!r}") from exc
    if not d.is_finite():
        raise ValueError(f"non-finite {field}: {token!r}")
    if d <= 0:
        raise ValueError(f"{field} must be strictly positive: {token!r}")
    return _canonical_decimal128_38_18(d, field=field)


def _parse_nonnegative_decimal(token: str, *, field: str) -> Decimal:
    try:
        d = Decimal(token)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid {field}: {token!r}") from exc
    if not d.is_finite():
        raise ValueError(f"non-finite {field}: {token!r}")
    if d < 0:
        raise ValueError(f"{field} must be nonnegative: {token!r}")
    return _canonical_decimal128_38_18(d, field=field)


def _us_to_datetime(us: int) -> datetime:
    sec, micro = divmod(int(us), 1_000_000)
    return datetime.fromtimestamp(sec, tz=timezone.utc).replace(microsecond=micro)


def _parquet_row_counter(path: Path) -> int:
    return int(pq.ParquetFile(str(path)).metadata.num_rows)


def _trade_schema() -> pa.Schema:
    return pa.schema(
        [
            ("venue_id", pa.string()),
            ("instrument_id", pa.string()),
            ("market_type", pa.string()),
            ("contract_style", pa.string()),
            ("schema_variant", pa.string()),
            ("size_unit", pa.string()),
            ("event_time", pa.int64()),
            ("source_timestamp", pa.string()),
            ("source_timestamp_unit", pa.string()),
            ("source_symbol", pa.string()),
            ("side", pa.string()),
            ("size", pa.decimal128(_DECIMAL_PRECISION, _DECIMAL_SCALE)),
            ("price", pa.decimal128(_DECIMAL_PRECISION, _DECIMAL_SCALE)),
            ("tick_direction", pa.string()),
            ("trade_match_id", pa.string()),
            ("gross_value", pa.decimal128(_DECIMAL_PRECISION, _DECIMAL_SCALE)),
            ("home_notional", pa.decimal128(_DECIMAL_PRECISION, _DECIMAL_SCALE)),
            ("foreign_notional", pa.decimal128(_DECIMAL_PRECISION, _DECIMAL_SCALE)),
            ("raw_object_id", pa.string()),
            ("source_row_number", pa.int64()),
        ]
    )


def _schema_fingerprint() -> str:
    material = "|".join(
        [
            BYBIT_TRADE_SCHEMA_NAME,
            BYBIT_TRADE_SCHEMA_VERSION,
            *[f"{f.name}:{f.type}" for f in _trade_schema()],
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _write_trades_parquet(path: Path, rows: Sequence[_TradeRow]) -> tuple[str, int, int]:
    schema = _trade_schema()
    if not rows:
        table = pa.table([[] for _ in range(len(schema))], schema=schema)
    else:
        arrays = {
            "venue_id": pa.array([r.venue_id for r in rows], type=pa.string()),
            "instrument_id": pa.array([r.instrument_id for r in rows], type=pa.string()),
            "market_type": pa.array([r.market_type for r in rows], type=pa.string()),
            "contract_style": pa.array(
                [r.contract_style for r in rows], type=pa.string()
            ),
            "schema_variant": pa.array(
                [r.schema_variant for r in rows], type=pa.string()
            ),
            "size_unit": pa.array([r.size_unit for r in rows], type=pa.string()),
            "event_time": pa.array([r.event_time for r in rows], type=pa.int64()),
            "source_timestamp": pa.array(
                [r.source_timestamp for r in rows], type=pa.string()
            ),
            "source_timestamp_unit": pa.array(
                [r.source_timestamp_unit for r in rows], type=pa.string()
            ),
            "source_symbol": pa.array(
                [r.source_symbol for r in rows], type=pa.string()
            ),
            "side": pa.array([r.side for r in rows], type=pa.string()),
            "size": pa.array(
                [r.size for r in rows],
                type=pa.decimal128(_DECIMAL_PRECISION, _DECIMAL_SCALE),
            ),
            "price": pa.array(
                [r.price for r in rows],
                type=pa.decimal128(_DECIMAL_PRECISION, _DECIMAL_SCALE),
            ),
            "tick_direction": pa.array(
                [r.tick_direction for r in rows], type=pa.string()
            ),
            "trade_match_id": pa.array(
                [r.trade_match_id for r in rows], type=pa.string()
            ),
            "gross_value": pa.array(
                [r.gross_value for r in rows],
                type=pa.decimal128(_DECIMAL_PRECISION, _DECIMAL_SCALE),
            ),
            "home_notional": pa.array(
                [r.home_notional for r in rows],
                type=pa.decimal128(_DECIMAL_PRECISION, _DECIMAL_SCALE),
            ),
            "foreign_notional": pa.array(
                [r.foreign_notional for r in rows],
                type=pa.decimal128(_DECIMAL_PRECISION, _DECIMAL_SCALE),
            ),
            "raw_object_id": pa.array(
                [r.raw_object_id for r in rows], type=pa.string()
            ),
            "source_row_number": pa.array(
                [r.source_row_number for r in rows], type=pa.int64()
            ),
        }
        table = pa.table(arrays, schema=schema)
    pq.write_table(table, str(path), compression="zstd")
    sha, byte_size = stream_sha256_and_size(path)
    return sha, byte_size, len(rows)


def _write_quality_parquet(
    path: Path, issues: Sequence[QualityIssue]
) -> tuple[str, int, int]:
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
    sha, byte_size = stream_sha256_and_size(path)
    return sha, byte_size, len(issues)


def _parse_trade_row(
    cells: list[str],
    *,
    source_symbol: str,
    style: Mapping[str, str],
    venue_id: str,
    instrument_id: str,
    raw_object_id: str,
    source_row_number: int,
) -> _TradeRow:
    if len(cells) != _FIELD_COUNT:
        raise ValueError(f"expected {_FIELD_COUNT} columns, got {len(cells)}")

    # Exact source tokens (no strip for stored identity fields).
    ts_tok = cells[0]
    symbol = cells[1]
    side_raw = cells[2]
    size_tok = cells[3]
    price_tok = cells[4]
    tick_dir = cells[5]
    trade_id = cells[6]
    gross_tok = cells[7]
    home_tok = cells[8]
    foreign_tok = cells[9]

    # Symbol: exact match only (whitespace-altered symbols rejected).
    if symbol != source_symbol:
        raise _RowError(
            "bybit_trade_symbol_mismatch",
            f"symbol {symbol!r} does not match source_symbol {source_symbol!r}",
            column="symbol",
        )
    if side_raw not in _VALID_SIDES_RAW:
        raise _RowError(
            "bybit_trade_parse_failure",
            f"side must be Buy or Sell; got {side_raw!r}",
            column="side",
        )
    if tick_dir not in _VALID_TICK_DIRECTIONS:
        raise _RowError(
            "bybit_trade_parse_failure",
            f"invalid tickDirection: {tick_dir!r}",
            column="tickDirection",
        )
    if not trade_id:
        raise _RowError(
            "bybit_trade_parse_failure",
            "trdMatchID must be nonempty",
            column="trdMatchID",
        )

    try:
        event_time = _timestamp_token_to_utc_us(ts_tok)
    except ValueError as exc:
        raise _RowError(
            "bybit_trade_invalid_timestamp",
            str(exc),
            column="timestamp",
        ) from exc

    # Numeric fields: parse exact cell text (audited schema has no padding spaces).
    try:
        size = _parse_positive_decimal(size_tok, field="size")
        price = _parse_positive_decimal(price_tok, field="price")
        gross = _parse_nonnegative_decimal(gross_tok, field="grossValue")
        home = _parse_nonnegative_decimal(home_tok, field="homeNotional")
        foreign = _parse_nonnegative_decimal(foreign_tok, field="foreignNotional")
    except ValueError as exc:
        raise _RowError(
            "bybit_trade_parse_failure",
            str(exc),
            column=None,
        ) from exc

    side = "buy" if side_raw == "Buy" else "sell"
    return _TradeRow(
        venue_id=venue_id,
        instrument_id=instrument_id,
        market_type=style["market_type"],
        contract_style=style["contract_style"],
        schema_variant=style["schema_variant"],
        size_unit=style["size_unit"],
        event_time=event_time,
        source_timestamp=ts_tok,
        source_timestamp_unit="decimal_seconds",
        source_symbol=source_symbol,
        side=side,
        size=size,
        price=price,
        tick_direction=tick_dir,
        trade_match_id=trade_id,
        gross_value=gross,
        home_notional=home,
        foreign_notional=foreign,
        raw_object_id=raw_object_id,
        source_row_number=source_row_number,
    )


def _open_csv_stream(
    path: Path,
    *,
    max_decompressed_bytes: int,
) -> tuple[TextIO, gzip.GzipFile, BinaryIO]:
    """Open gzip CSV with decompressed-byte bound. Returns (text, gz, raw_f)."""
    raw_f: BinaryIO = path.open("rb")
    try:
        gz = gzip.GzipFile(fileobj=raw_f, mode="rb")
    except Exception:
        raw_f.close()
        raise
    # Label is identity-stable (not a storage path).
    bounded = _BoundedRawReader(
        gz,  # type: ignore[arg-type]
        max_bytes=max_decompressed_bytes,
        label="decompressed_stream",
    )
    buffered = io.BufferedReader(bounded)
    text = io.TextIOWrapper(buffered, encoding="utf-8", newline="")
    return text, gz, raw_f


def _close_stream(text: TextIO | None, gz: gzip.GzipFile | None, raw_f: BinaryIO | None) -> None:
    """Close in reverse open order; do not suppress gzip CRC/truncation errors.

    Catches ``Exception`` only so KeyboardInterrupt/SystemExit propagate.
    """
    errors: list[Exception] = []
    if text is not None:
        try:
            text.close()
        except Exception as exc:
            errors.append(exc)
    if gz is not None:
        try:
            gz.close()
        except Exception as exc:
            errors.append(exc)
    if raw_f is not None:
        try:
            raw_f.close()
        except Exception as exc:
            errors.append(exc)
    if errors:
        raise errors[0]


def _finalize_ordering(work: _ObjectWork, *, saw_asc: bool, saw_desc: bool) -> None:
    """Derive ordering diagnostic from accepted rows on every exit path."""
    if not work.rows:
        work.ordering = "empty"
    elif len(work.rows) == 1:
        work.ordering = "single"
    elif saw_asc and saw_desc:
        work.ordering = "mixed"
    elif saw_desc and not saw_asc:
        work.ordering = "descending"
    else:
        work.ordering = "ascending"


def _process_raw_object(
    ro: RawObject,
    *,
    style: Mapping[str, str],
    source_symbol: str,
    venue_id: str,
    instrument_id: str,
    max_decompressed_bytes: int,
    max_rows: int,
    out_dir: Path,
) -> _ObjectWork:
    work = _ObjectWork(
        raw_object_id=ro.raw_object_id,
        trade_path=out_dir / f"trades_{ro.raw_object_id}.parquet",
        quality_path=out_dir / f"quality_{ro.raw_object_id}.parquet",
    )
    saw_asc = False
    saw_desc = False

    if ro.source_id != "bybit":
        work.issues.append(
            QualityIssue(
                code="bybit_trade_parse_failure",
                severity=IssueSeverity.ERROR,
                message=f"raw object source_id must be 'bybit'; got {ro.source_id!r}",
                context={"raw_object_id": ro.raw_object_id},
            )
        )
        _finalize_ordering(work, saw_asc=saw_asc, saw_desc=saw_desc)
        return work

    try:
        assert_regular_nonsymlink_file(
            ro.storage_path, label=f"raw_object {ro.raw_object_id}"
        )
    except Exception:
        # Do not serialize storage paths into quality identity (REVIEW-0046 #6).
        work.issues.append(
            QualityIssue(
                code="bybit_trade_parse_failure",
                severity=IssueSeverity.ERROR,
                message="registered storage path is not a regular non-symlink file",
                context={"raw_object_id": ro.raw_object_id},
            )
        )
        _finalize_ordering(work, saw_asc=saw_asc, saw_desc=saw_desc)
        return work

    text: TextIO | None = None
    gz: gzip.GzipFile | None = None
    raw_f: BinaryIO | None = None
    try:
        text, gz, raw_f = _open_csv_stream(
            Path(ro.storage_path),
            max_decompressed_bytes=max_decompressed_bytes,
        )
        reader = csv.reader(text, strict=True)
        try:
            header = next(reader)
        except StopIteration:
            work.issues.append(
                QualityIssue(
                    code="bybit_trade_empty_observations",
                    severity=IssueSeverity.ERROR,
                    message="archive produced no typed trade observations (empty file)",
                    context={"raw_object_id": ro.raw_object_id},
                )
            )
            return work
        except UnicodeDecodeError as exc:
            work.issues.append(
                QualityIssue(
                    code="bybit_trade_parse_failure",
                    severity=IssueSeverity.ERROR,
                    message=f"malformed UTF-8: {exc}",
                    context={"raw_object_id": ro.raw_object_id},
                )
            )
            return work
        except csv.Error as exc:
            work.issues.append(
                QualityIssue(
                    code="bybit_trade_parse_failure",
                    severity=IssueSeverity.ERROR,
                    message=f"malformed CSV: {exc}",
                    context={"raw_object_id": ro.raw_object_id},
                )
            )
            return work

        # Exact header match — do not strip (whitespace-altered headers rejected).
        header_t = tuple(header)
        if header_t != _AUDITED_HEADER:
            work.issues.append(
                QualityIssue(
                    code="bybit_archive_header_mismatch",
                    severity=IssueSeverity.ERROR,
                    message="CSV header does not match audited Bybit trade schema",
                    context={
                        "raw_object_id": ro.raw_object_id,
                        "expected": list(_AUDITED_HEADER),
                        "observed": list(header_t),
                    },
                )
            )
            return work

        prev_event: int | None = None
        established_dir: int | None = None  # +1 asc, -1 desc
        data_rows = 0
        direction_warning_emitted = False
        clean_eof = True  # False if first/later data record fails CSV/UTF-8 parse

        while True:
            try:
                cells = next(reader)
            except StopIteration:
                break
            except csv.Error as exc:
                clean_eof = False
                work.issues.append(
                    QualityIssue(
                        code="bybit_trade_parse_failure",
                        severity=IssueSeverity.ERROR,
                        message=f"malformed CSV: {exc}",
                        context={
                            "raw_object_id": ro.raw_object_id,
                            "source_row_number": data_rows + 1,
                        },
                    )
                )
                break
            except UnicodeDecodeError as exc:
                clean_eof = False
                work.issues.append(
                    QualityIssue(
                        code="bybit_trade_parse_failure",
                        severity=IssueSeverity.ERROR,
                        message=f"malformed UTF-8: {exc}",
                        context={
                            "raw_object_id": ro.raw_object_id,
                            "source_row_number": data_rows + 1,
                        },
                    )
                )
                break

            data_rows += 1
            if data_rows > max_rows:
                work.issues.append(
                    QualityIssue(
                        code="bybit_archive_limit_exceeded",
                        severity=IssueSeverity.ERROR,
                        message=f"row count exceeded max_rows={max_rows}",
                        context={
                            "raw_object_id": ro.raw_object_id,
                            "max_rows": max_rows,
                        },
                    )
                )
                break

            if len(cells) != _FIELD_COUNT:
                work.issues.append(
                    QualityIssue(
                        code="bybit_trade_row_width",
                        severity=IssueSeverity.ERROR,
                        message=(
                            f"expected {_FIELD_COUNT} columns, got {len(cells)}"
                        ),
                        context={
                            "raw_object_id": ro.raw_object_id,
                            "source_row_number": data_rows,
                        },
                    )
                )
                continue

            try:
                row = _parse_trade_row(
                    cells,
                    source_symbol=source_symbol,
                    style=style,
                    venue_id=venue_id,
                    instrument_id=instrument_id,
                    raw_object_id=ro.raw_object_id,
                    source_row_number=data_rows,
                )
            except _RowError as exc:
                work.issues.append(
                    QualityIssue(
                        code=exc.code,
                        severity=IssueSeverity.ERROR,
                        message=str(exc),
                        column=exc.column,
                        context={
                            "raw_object_id": ro.raw_object_id,
                            "source_row_number": data_rows,
                        },
                    )
                )
                continue
            except Exception as exc:
                work.issues.append(
                    QualityIssue(
                        code="bybit_trade_parse_failure",
                        severity=IssueSeverity.ERROR,
                        message=str(exc),
                        context={
                            "raw_object_id": ro.raw_object_id,
                            "source_row_number": data_rows,
                        },
                    )
                )
                continue

            # Direction: first non-equal pair establishes; reverse => one warning.
            if prev_event is not None and row.event_time != prev_event:
                step = 1 if row.event_time > prev_event else -1
                if step > 0:
                    saw_asc = True
                else:
                    saw_desc = True
                if established_dir is None:
                    established_dir = step
                elif step != established_dir and not direction_warning_emitted:
                    direction_warning_emitted = True
                    work.issues.append(
                        QualityIssue(
                            code="bybit_trade_nonmonotonic_timestamp",
                            severity=IssueSeverity.WARNING,
                            message=(
                                "timestamp direction reversed after initial "
                                "ascending/descending trend"
                            ),
                            context={
                                "raw_object_id": ro.raw_object_id,
                                "source_row_number": data_rows,
                                "prev_event_time": prev_event,
                                "event_time": row.event_time,
                                "established_direction": (
                                    "ascending" if established_dir > 0 else "descending"
                                ),
                            },
                        )
                    )
            prev_event = row.event_time
            work.rows.append(row)

        # Header-only only on clean EOF with zero data records (REVIEW-0047 #5).
        if (
            clean_eof
            and data_rows == 0
            and not any(i.code == "bybit_trade_empty_observations" for i in work.issues)
        ):
            work.issues.append(
                QualityIssue(
                    code="bybit_trade_empty_observations",
                    severity=IssueSeverity.ERROR,
                    message="archive produced no typed trade observations (header-only)",
                    context={"raw_object_id": ro.raw_object_id},
                )
            )

        if not work.rows:
            if not any(
                i.code == "bybit_trade_empty_observations" for i in work.issues
            ) and not any(i.severity is IssueSeverity.ERROR for i in work.issues):
                work.issues.append(
                    QualityIssue(
                        code="bybit_trade_empty_observations",
                        severity=IssueSeverity.ERROR,
                        message="archive produced no accepted trade rows",
                        context={"raw_object_id": ro.raw_object_id},
                    )
                )

    except _LimitExceeded:
        work.issues.append(
            QualityIssue(
                code="bybit_archive_limit_exceeded",
                severity=IssueSeverity.ERROR,
                message=(
                    f"decompressed stream exceeded max_decompressed_bytes="
                    f"{max_decompressed_bytes}"
                ),
                context={
                    "raw_object_id": ro.raw_object_id,
                    "max_decompressed_bytes": max_decompressed_bytes,
                },
            )
        )
    except (gzip.BadGzipFile, EOFError, zlib.error) as exc:
        # Structural gzip classification only — no path/message heuristics.
        work.issues.append(
            QualityIssue(
                code="bybit_archive_bad_gzip",
                severity=IssueSeverity.ERROR,
                message=f"invalid or truncated gzip stream: {type(exc).__name__}",
                context={"raw_object_id": ro.raw_object_id},
            )
        )
    except OSError:
        # Location-independent I/O failure (REVIEW-0047 #3).
        work.issues.append(
            QualityIssue(
                code="bybit_trade_parse_failure",
                severity=IssueSeverity.ERROR,
                message="I/O error while reading registered archive",
                context={"raw_object_id": ro.raw_object_id},
            )
        )
    except UnicodeDecodeError:
        work.issues.append(
            QualityIssue(
                code="bybit_trade_parse_failure",
                severity=IssueSeverity.ERROR,
                message="malformed UTF-8 in archive stream",
                context={"raw_object_id": ro.raw_object_id},
            )
        )
    finally:
        try:
            _close_stream(text, gz, raw_f)
        except (gzip.BadGzipFile, EOFError, zlib.error):
            work.issues.append(
                QualityIssue(
                    code="bybit_archive_bad_gzip",
                    severity=IssueSeverity.ERROR,
                    message="gzip finalization failed (CRC/truncation)",
                    context={"raw_object_id": ro.raw_object_id},
                )
            )
        except OSError:
            work.issues.append(
                QualityIssue(
                    code="bybit_trade_parse_failure",
                    severity=IssueSeverity.ERROR,
                    message="stream close failed",
                    context={"raw_object_id": ro.raw_object_id},
                )
            )
        except Exception:
            # Ordinary close failures must not escape untyped (REVIEW-0047 #1).
            work.issues.append(
                QualityIssue(
                    code="bybit_trade_parse_failure",
                    severity=IssueSeverity.ERROR,
                    message="stream close failed",
                    context={"raw_object_id": ro.raw_object_id},
                )
            )
        # Ordering from accepted rows on every exit path (REVIEW-0046 #5).
        _finalize_ordering(work, saw_asc=saw_asc, saw_desc=saw_desc)

    return work


def _detect_duplicates(works: Mapping[str, _ObjectWork]) -> None:
    """Order-independent trdMatchID duplicate detection; preserve all rows.

    Issues are attached to every involved object with full participant context.
    Processing order of raw_objects does not change quality identity.
    """
    # tid -> list of (raw_object_id, source_row_number, fingerprint)
    by_tid: dict[str, list[tuple[str, int, str]]] = {}
    for rid in sorted(works.keys()):
        work = works[rid]
        for row in work.rows:
            by_tid.setdefault(row.trade_match_id, []).append(
                (rid, row.source_row_number, row.economic_fingerprint())
            )

    for tid in sorted(by_tid.keys()):
        occs = by_tid[tid]
        if len(occs) < 2:
            continue
        occs_sorted = sorted(occs, key=lambda o: (o[0], o[1]))
        fps = {o[2] for o in occs_sorted}
        code = (
            "bybit_trade_duplicate_id"
            if len(fps) == 1
            else "bybit_trade_conflicting_duplicate_id"
        )
        message = (
            "exact duplicate trdMatchID (same economic content)"
            if len(fps) == 1
            else "conflicting trdMatchID (different economic content)"
        )
        participants = [
            {"raw_object_id": o[0], "source_row_number": o[1]} for o in occs_sorted
        ]
        raw_ids = sorted({o[0] for o in occs_sorted})
        for rid in raw_ids:
            works[rid].issues.append(
                QualityIssue(
                    code=code,
                    severity=IssueSeverity.ERROR,
                    message=message,
                    context={
                        "trade_match_id": tid,
                        "participants": participants,
                        "raw_object_ids": raw_ids,
                        "cross_object": len(raw_ids) > 1,
                    },
                )
            )


def normalize_bybit_trades(
    raw_objects: Sequence[RawObject],
    *,
    contract_style: str,
    source_symbol: str,
    venue_id: str,
    instrument_id: str,
    output_dir: Path | str,
    code_commit: str,
    config_sha256: str | None = None,
    max_decompressed_bytes: int = _DEFAULT_MAX_DECOMPRESSED_BYTES,
    max_rows: int = _DEFAULT_MAX_ROWS,
) -> BybitTradeNormalizeResult:
    """Normalize registered local Bybit perpetual-trade ``.csv.gz`` archives.

    One invocation covers one resolved instrument and exact ``source_symbol``.
    No network. No filename identity authority.
    """
    if not raw_objects:
        raise ValueError("at least one raw_object required")
    if max_decompressed_bytes <= 0:
        raise ValueError("max_decompressed_bytes must be positive")
    if max_rows <= 0:
        raise ValueError("max_rows must be positive")

    code_id = _require_code_commit(code_commit)
    style = _resolve_contract_style(contract_style)
    venue = _require_canonical_path_token("venue_id", venue_id)
    instrument = _require_canonical_path_token("instrument_id", str(instrument_id))
    # source_symbol is exact identity — no strip/normalization.
    if not source_symbol:
        raise ValueError("source_symbol is required and non-empty")
    symbol = source_symbol

    # Canonicalize object processing order by registered raw_object_id.
    # IDs must already be path-safe without silent rewrite.
    id_to_ro: dict[str, RawObject] = {}
    for ro in raw_objects:
        rid = ro.raw_object_id
        _require_canonical_path_token("raw_object_id", rid)
        if rid in id_to_ro:
            raise ValueError(f"duplicate raw_object_id: {rid!r}")
        id_to_ro[rid] = ro
    ordered_ids = sorted(id_to_ro.keys())

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    works: dict[str, _ObjectWork] = {}
    deps: list[DependencyRef] = []
    for rid in ordered_ids:
        ro = id_to_ro[rid]
        deps.append(
            DependencyRef(
                id=ro.raw_object_id,  # immutable registered ID
                kind=DependencyKind.RAW_OBJECT,
                role="bybit_trade_archive",
            )
        )
        works[rid] = _process_raw_object(
            ro,
            style=style,
            source_symbol=symbol,
            venue_id=venue,
            instrument_id=instrument,
            max_decompressed_bytes=max_decompressed_bytes,
            max_rows=max_rows,
            out_dir=out_dir,
        )

    _detect_duplicates(works)

    # Deterministic issue ordering within each object (stable quality parquet).
    for rid in ordered_ids:
        work = works[rid]
        work.issues.sort(
            key=lambda i: (
                i.code,
                i.severity.value,
                i.message,
                str(dict(i.context)),
            )
        )

    output_sources: dict[str, Path] = {}
    output_specs: list[OutputFileSpec] = []
    row_counters: dict[str, Callable[[Path], int]] = {}
    all_trade_paths: list[Path] = []
    all_quality_paths: list[Path] = []
    all_issues: list[QualityIssue] = []
    total_rows = 0
    total_bytes = 0
    min_event: datetime | None = None
    max_event: datetime | None = None
    ordering_summary: dict[str, str] = {}

    market_type = style["market_type"]
    schema_fp = _schema_fingerprint()

    for rid in ordered_ids:
        work = works[rid]
        ordering_summary[rid] = work.ordering
        all_issues.extend(work.issues)

        for row in work.rows:
            # event_time already range-validated at parse; coverage uses accepted rows only
            ts = _us_to_datetime(row.event_time)
            if min_event is None or ts < min_event:
                min_event = ts
            if max_event is None or ts > max_event:
                max_event = ts

        rel_trades = f"bybit/{market_type}/trades/raw_{rid}/trades.parquet"
        rel_quality = f"bybit/{market_type}/trades/raw_{rid}/quality.parquet"
        trade_nested = out_dir / rel_trades
        quality_nested = out_dir / rel_quality
        trade_nested.parent.mkdir(parents=True, exist_ok=True)

        t_sha, t_bytes, t_n = _write_trades_parquet(trade_nested, work.rows)
        q_sha, q_bytes, q_n = _write_quality_parquet(quality_nested, work.issues)

        all_trade_paths.append(trade_nested)
        all_quality_paths.append(quality_nested)
        output_sources[rel_trades] = trade_nested
        output_sources[rel_quality] = quality_nested
        row_counters[rel_trades] = _parquet_row_counter
        row_counters[rel_quality] = _parquet_row_counter

        partition_common = {
            "raw_object_id": rid,
            "venue_id": venue,
            "instrument_id": instrument,
            "source_symbol": symbol,
            "market_type": market_type,
            "contract_style": style["contract_style"],
            "schema_variant": style["schema_variant"],
            "size_unit": style["size_unit"],
            "source_timestamp_unit": "decimal_seconds",
            "timestamp_storage": "utc_microseconds",
        }
        output_specs.append(
            OutputFileSpec(
                relative_path=rel_trades,
                sha256=t_sha,
                rows=t_n,
                bytes=t_bytes,
                partition=dict(partition_common),
                rows_verified=True,
            )
        )
        output_specs.append(
            OutputFileSpec(
                relative_path=rel_quality,
                sha256=q_sha,
                rows=q_n,
                bytes=q_bytes,
                partition={
                    "raw_object_id": rid,
                    "market_type": market_type,
                    "kind": "quality",
                },
                rows_verified=True,
            )
        )
        total_rows += t_n + q_n
        total_bytes += t_bytes + q_bytes

    has_error = any(i.severity is IssueSeverity.ERROR for i in all_issues)
    has_warn = any(i.severity is IssueSeverity.WARNING for i in all_issues)
    if has_error:
        q_status = QualityStatus.REJECTED
    elif has_warn:
        q_status = QualityStatus.PASS_WITH_WARNINGS
    else:
        q_status = QualityStatus.PASS

    cfg_payload = {
        "contract_style": style["contract_style"],
        "dataset_type": BYBIT_TRADE_DATASET_TYPE,
        "instrument_id": instrument,
        "market_type": market_type,
        "max_decompressed_bytes": max_decompressed_bytes,
        "max_rows": max_rows,
        "schema_fingerprint": schema_fp,
        "schema_name": BYBIT_TRADE_SCHEMA_NAME,
        "schema_variant": style["schema_variant"],
        "schema_version": BYBIT_TRADE_SCHEMA_VERSION,
        "size_unit": style["size_unit"],
        "source_symbol": symbol,
        "source_timestamp_unit": "decimal_seconds",
        "timestamp_storage": "utc_microseconds",
        "transform_name": BYBIT_TRADE_TRANSFORM_NAME,
        "transform_version": BYBIT_TRADE_TRANSFORM_VERSION,
        "venue_id": venue,
    }
    cfg_hash = _resolve_config_sha256(config_sha256, payload=cfg_payload)

    plan = PublishPlan(
        dataset_type=BYBIT_TRADE_DATASET_TYPE,
        schema=SchemaIdentity(
            name=BYBIT_TRADE_SCHEMA_NAME,
            version=BYBIT_TRADE_SCHEMA_VERSION,
            fingerprint=schema_fp,
        ),
        transform=TransformSpec(
            name=BYBIT_TRADE_TRANSFORM_NAME,
            version=BYBIT_TRADE_TRANSFORM_VERSION,
        ),
        code=CodeIdentity(commit=code_id),
        config=ConfigIdentity(config_sha256=cfg_hash),
        dependencies=tuple(deps),
        output_sources=output_sources,
        output_specs=output_specs,
        statistics=DatasetStatistics(row_count=total_rows, byte_size=total_bytes),
        coverage=CoverageWindow(event_start=min_event, event_end=max_event),
        quality_status=q_status,
        quality_summary={
            "issue_count": len(all_issues),
            "contract_style": style["contract_style"],
            "market_type": market_type,
            "schema_variant": style["schema_variant"],
            "size_unit": style["size_unit"],
            "source_symbol": symbol,
            "venue_id": venue,
            "instrument_id": instrument,
            "source_timestamp_unit": "decimal_seconds",
            "timestamp_storage": "utc_microseconds",
            "max_decompressed_bytes": max_decompressed_bytes,
            "max_rows": max_rows,
            "ordering_per_object": ordering_summary,
            "provider_role": "CONDITIONAL - CROSSCHECK",
            "normalizer_version": BYBIT_TRADE_TRANSFORM_VERSION,
            "schema_fingerprint": schema_fp,
            "no_invented_inverse_base_quote": True,
            "preserve_source_row_order": True,
            "duplicate_evidence_order_independent": True,
        },
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters=row_counters,
    )

    return BybitTradeNormalizeResult(
        publish_plan=plan,
        trade_paths=tuple(all_trade_paths),
        quality_paths=tuple(all_quality_paths),
        issues=tuple(all_issues),
    )
