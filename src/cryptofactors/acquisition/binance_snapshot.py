"""DATA-008 Binance daily bar acquisition, watermarks, and canonical snapshot.

Bars are validated on every axis before they can be published, watermarks advance
only to the last contiguous validated bar that was actually published, and every
publication is a complete canonical snapshot rather than a delta. A run that cannot
publish leaves the prior dataset and every watermark exactly as it found them.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from cryptofactors.acquisition.binance_universe import (
    KLINES_SOURCE_ID,
    AcquisitionOutcome,
    BinanceUniverseError,
    RawHttpAcquirer,
    canonical_json,
)

DAY_MS = 86_400_000
DAY_SECONDS = 86_400
BINANCE_PROVIDER = "binance"


class BinanceSnapshotError(RuntimeError):
    """Raised for invalid bars, identity violations, or unresolved coverage."""


class SymbolState(str, Enum):
    """Terminal state of one symbol's acquisition."""

    PUBLISHABLE = "PUBLISHABLE"
    ALREADY_CURRENT = "ALREADY_CURRENT"
    DEFERRED = "DEFERRED"
    FAILED = "FAILED"
    EMPTY = "EMPTY"
    INVALID = "INVALID"
    GAPPED = "GAPPED"
    BUDGET_DEFERRED = "BUDGET_DEFERRED"


#: States that block publication for a symbol that was selected and eligible.
BLOCKING_STATES = frozenset({
    SymbolState.FAILED, SymbolState.EMPTY, SymbolState.INVALID, SymbolState.GAPPED,
})


@dataclass(frozen=True, slots=True)
class KlineBar:
    """One validated daily bar."""

    symbol: str
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: int
    provider: str
    raw_object_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "open_time": self.open_time.isoformat(),
            "open_time_us": int(self.open_time.timestamp() * 1_000_000),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "quote_volume": self.quote_volume,
            "trades": self.trades,
            "provider": self.provider,
            "raw_object_id": self.raw_object_id,
        }

    @property
    def dedupe_key(self) -> tuple[str, int]:
        return (self.symbol, int(self.open_time.timestamp()))


def _number(value: Any, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise BinanceSnapshotError(f"{label} must be numeric, got {value!r}")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise BinanceSnapshotError(f"{label} must be numeric, got {value!r}") from exc
    if not math.isfinite(result):
        raise BinanceSnapshotError(f"{label} must be finite, got {value!r}")
    return result


def _whole_number(value: Any, *, label: str) -> int:
    """Decode a count field without silent truncation or an untyped crash.

    A prior snapshot is untrusted input: int() on it raises ValueError/TypeError,
    which escapes as an unrelated exception type, and int(7.9) would silently
    record a different value than the one stored.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise BinanceSnapshotError(f"{label} must be an integer, got {value!r}")
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError as exc:
            raise BinanceSnapshotError(f"{label} must be an integer, got {value!r}") from exc
    if isinstance(value, float):
        if not math.isfinite(value) or value != int(value):
            raise BinanceSnapshotError(f"{label} must be a whole number, got {value!r}")
    return int(value)


def validate_bar_values(
    *, open_: Any, high: Any, low: Any, close: Any, volume: Any, quote_volume: Any
) -> tuple[float, float, float, float, float, float]:
    """The OHLC/volume invariants every bar must satisfy, however it was obtained."""
    values = (
        _number(open_, label="open"), _number(high, label="high"),
        _number(low, label="low"), _number(close, label="close"),
        _number(volume, label="volume"), _number(quote_volume, label="quote_volume"),
    )
    open_v, high_v, low_v, close_v, volume_v, quote_v = values
    for name, value in (("volume", volume_v), ("quote_volume", quote_v)):
        if value < 0:
            raise BinanceSnapshotError(f"{name} must be non-negative, got {value}")
    if low_v > high_v:
        raise BinanceSnapshotError(f"low {low_v} exceeds high {high_v}")
    for name, value in (("open", open_v), ("close", close_v)):
        if not low_v <= value <= high_v:
            raise BinanceSnapshotError(f"{name} {value} outside [low {low_v}, high {high_v}]")
    return values


def validate_open_time(moment: datetime) -> datetime:
    """Bar open times must be timezone-aware UTC midnight."""
    if moment.tzinfo is None:
        raise BinanceSnapshotError(f"bar open time {moment!r} must be timezone-aware")
    utc = moment.astimezone(UTC)
    if int(utc.timestamp()) % DAY_SECONDS:
        raise BinanceSnapshotError(f"bar open time {utc.isoformat()} is not UTC midnight")
    return utc


def parse_klines(
    payload: Any,
    *,
    symbol: str,
    start_time: datetime,
    end_time: datetime,
    raw_object_id: str,
) -> list[KlineBar]:
    """Decode and validate Binance daily klines.

    Bars outside the requested window are excluded rather than fatal: the endpoint
    pages by startTime/limit and legitimately returns extra history. Coverage is
    judged separately against the range that was requested.
    """
    if not isinstance(payload, list):
        raise BinanceSnapshotError("klines response must be a list")

    seen: set[int] = set()
    bars: list[KlineBar] = []
    for entry in payload:
        if not isinstance(entry, Sequence) or isinstance(entry, (str, bytes)) or len(entry) < 9:
            raise BinanceSnapshotError("each kline must be a sequence of at least 9 fields")
        raw_open_time = entry[0]
        if isinstance(raw_open_time, bool) or not isinstance(raw_open_time, (int, float)):
            raise BinanceSnapshotError(f"kline open time must be numeric, got {raw_open_time!r}")
        epoch_ms = int(raw_open_time)
        if epoch_ms % DAY_MS:
            raise BinanceSnapshotError(f"kline open time {epoch_ms} is not day-aligned")
        open_time = validate_open_time(datetime.fromtimestamp(epoch_ms / 1000, UTC))
        if not start_time <= open_time <= end_time:
            continue
        if epoch_ms in seen:
            raise BinanceSnapshotError(f"duplicate kline open time {open_time.isoformat()}")
        seen.add(epoch_ms)

        open_, high, low, close, volume, quote_volume = validate_bar_values(
            open_=entry[1], high=entry[2], low=entry[3], close=entry[4],
            volume=entry[5], quote_volume=entry[7],
        )
        trades = _whole_number(entry[8], label="trade count")

        bars.append(KlineBar(
            symbol=symbol, open_time=open_time, open=open_, high=high, low=low,
            close=close, volume=volume, quote_volume=quote_volume, trades=int(trades),
            provider=BINANCE_PROVIDER, raw_object_id=raw_object_id,
        ))
    return sorted(bars, key=lambda bar: bar.open_time)


def expected_days(*, start_time: datetime, end_time: datetime) -> list[datetime]:
    if start_time > end_time:
        return []
    first, last = int(start_time.timestamp()), int(end_time.timestamp())
    if first % DAY_SECONDS or last % DAY_SECONDS:
        raise BinanceSnapshotError("requested range must align to UTC midnight")
    return [datetime.fromtimestamp(e, UTC) for e in range(first, last + 1, DAY_SECONDS)]


def missing_days(
    bars: Sequence[KlineBar], *, start_time: datetime, end_time: datetime
) -> list[datetime]:
    """Requested days with no bar, including leading and trailing ones."""
    present = {int(bar.open_time.timestamp()) for bar in bars}
    return [
        day for day in expected_days(start_time=start_time, end_time=end_time)
        if int(day.timestamp()) not in present
    ]


def contiguous_prefix_end(bars: Sequence[KlineBar]) -> datetime | None:
    """Open time of the last bar before the first hole."""
    ordered = sorted(bars, key=lambda bar: bar.open_time)
    if not ordered:
        return None
    last = ordered[0].open_time
    for previous, following in zip(ordered, ordered[1:], strict=False):
        if int((following.open_time - previous.open_time).total_seconds()) > DAY_SECONDS:
            return last
        last = following.open_time
    return last


def symbol_covers_range(
    bars: Iterable[KlineBar], *, symbol: str, start_time: datetime, end_time: datetime
) -> tuple[bool, list[datetime]]:
    """Whether prior canonical rows cover every day in the requested range."""
    present = {
        int(bar.open_time.timestamp()) for bar in bars if bar.symbol == symbol
    }
    expected = expected_days(start_time=start_time, end_time=end_time)
    missing = [day for day in expected if int(day.timestamp()) not in present]
    return (not missing and bool(expected)), missing


def merge_canonical_bars(
    prior: Iterable[KlineBar], acquired: Iterable[KlineBar]
) -> list[KlineBar]:
    """Full snapshot: prior rows plus new rows, newly acquired winning on collision."""
    merged: dict[tuple[str, int], KlineBar] = {}
    for bar in prior:
        merged[bar.dedupe_key] = bar
    for bar in acquired:
        merged[bar.dedupe_key] = bar
    return [merged[key] for key in sorted(merged)]


def bars_from_records(
    records: Iterable[Mapping[str, Any]],
    *,
    allowed_raw_object_ids: Iterable[str] | None = None,
) -> list[KlineBar]:
    """Rebuild and fully revalidate bars from a previously published snapshot.

    A prior snapshot is untrusted input at merge time: it may reconcile on hash and
    row count and still contain rows that no longer satisfy the invariants.
    """
    permitted = None if allowed_raw_object_ids is None else {
        str(raw_id) for raw_id in allowed_raw_object_ids
    }
    restored: list[KlineBar] = []
    seen: set[tuple[str, int]] = set()

    for record in records:
        if not isinstance(record, Mapping):
            raise BinanceSnapshotError("prior snapshot row must be an object")
        for column in (
            "symbol", "open_time", "open", "high", "low", "close", "volume",
            "quote_volume", "trades", "provider", "raw_object_id",
        ):
            if column not in record:
                raise BinanceSnapshotError(f"prior snapshot row is missing {column!r}")

        provider = str(record["provider"])
        if provider != BINANCE_PROVIDER:
            raise BinanceSnapshotError(
                f"prior snapshot row claims provider {provider!r}, which cannot supply bars"
            )
        raw_object_id = str(record["raw_object_id"])
        if not raw_object_id.startswith("raw_"):
            raise BinanceSnapshotError(f"invalid raw object id {raw_object_id!r}")
        if permitted is not None and raw_object_id not in permitted:
            raise BinanceSnapshotError(
                f"prior snapshot row cites raw object {raw_object_id} which the prior "
                "dataset lineage does not declare"
            )

        try:
            parsed = datetime.fromisoformat(str(record["open_time"]))
        except ValueError as exc:
            raise BinanceSnapshotError(
                f"prior snapshot open_time {record['open_time']!r} is not ISO-8601"
            ) from exc
        open_time = validate_open_time(parsed)
        open_, high, low, close, volume, quote_volume = validate_bar_values(
            open_=record["open"], high=record["high"], low=record["low"],
            close=record["close"], volume=record["volume"],
            quote_volume=record["quote_volume"],
        )
        bar = KlineBar(
            symbol=str(record["symbol"]).strip().upper(), open_time=open_time, open=open_,
            high=high, low=low, close=close, volume=volume, quote_volume=quote_volume,
            trades=_whole_number(record["trades"], label="trades"),
            provider=provider, raw_object_id=raw_object_id,
        )
        if bar.dedupe_key in seen:
            raise BinanceSnapshotError(f"prior snapshot has duplicate identity {bar.dedupe_key}")
        seen.add(bar.dedupe_key)
        restored.append(bar)
    return restored


# ---------------------------------------------------------------------------
# Watermarks
# ---------------------------------------------------------------------------

class WatermarkStore:
    """Per-symbol watermarks persisted atomically, retaining unrelated sections."""

    SECTION = "binance_spot_daily"
    BUDGET_SECTION = "binance_spot_daily_budget"

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def _document(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise BinanceSnapshotError(f"cannot read watermark file {self._path}") from exc
        if not isinstance(document, dict):
            raise BinanceSnapshotError(f"watermark file {self._path} must contain an object")
        return document

    def load(self) -> dict[str, str]:
        section = self._document().get(self.SECTION, {})
        if not isinstance(section, Mapping):
            raise BinanceSnapshotError(f"{self.SECTION} watermark section must be an object")
        return {str(k): str(v) for k, v in section.items()}

    def save(self, watermarks: Mapping[str, str]) -> None:
        document = self._document()
        document[self.SECTION] = dict(sorted(watermarks.items()))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        temporary.write_text(canonical_json(document) + "\n", encoding="utf-8")
        temporary.replace(self._path)


    def load_cursor(self, *, selection_key: str, processing_day: str) -> tuple[set[str], int]:
        """Queue position for a pinned selection, and today's request count.

        Two separate facts. The attempted set is queue *position* and persists across
        days, so a constant daily limit still walks down the ranking instead of
        retrying rank one every morning. The counter is per processing day and resets,
        because it represents request capacity, not progress.
        """
        section = self._document().get(self.BUDGET_SECTION, {})
        if not isinstance(section, Mapping):
            return set(), 0
        queues = section.get("queues", {})
        queue = queues.get(selection_key, {}) if isinstance(queues, Mapping) else {}
        attempted = queue.get("attempted", []) if isinstance(queue, Mapping) else []
        used = 0
        if section.get("day") == processing_day:
            try:
                used = int(section.get("used", 0))
            except (TypeError, ValueError):
                used = 0
        return ({str(s) for s in attempted} if isinstance(attempted, list) else set()), used

    def save_cursor(
        self, *, selection_key: str, processing_day: str, attempted: Iterable[str], used: int
    ) -> None:
        document = self._document()
        section = document.get(self.BUDGET_SECTION)
        if not isinstance(section, dict):
            section = {}
        queues = section.get("queues")
        if not isinstance(queues, dict):
            queues = {}
        queues[selection_key] = {"attempted": sorted({str(s) for s in attempted})}
        section.update({"day": processing_day, "used": int(used), "queues": queues})
        document[self.BUDGET_SECTION] = section
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        temporary.write_text(canonical_json(document) + "\n", encoding="utf-8")
        temporary.replace(self._path)


def resume_start(
    watermarks: Mapping[str, str], *, symbol: str, default_start: datetime
) -> datetime:
    """Next day to request, or the configured default on first sight."""
    recorded = watermarks.get(symbol)
    if not recorded:
        return default_start
    try:
        last = datetime.fromisoformat(recorded)
    except ValueError as exc:
        raise BinanceSnapshotError(f"watermark {recorded!r} is not ISO-8601") from exc
    if last.tzinfo is None:
        raise BinanceSnapshotError(f"watermark {recorded!r} must be timezone-aware")
    return last + timedelta(seconds=DAY_SECONDS)


# ---------------------------------------------------------------------------
# Acquisition
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SymbolAcquisition:
    """Everything one symbol contributed to a run."""

    symbol: str
    state: SymbolState
    bars: tuple[KlineBar, ...] = ()
    missing: tuple[datetime, ...] = ()
    watermark_candidate: datetime | None = None
    requested_start: datetime | None = None
    requested_end: datetime | None = None
    error: str | None = None

    @property
    def usable(self) -> bool:
        return self.state is SymbolState.PUBLISHABLE

    @property
    def blocks_publication(self) -> bool:
        return self.state in BLOCKING_STATES

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "state": self.state.value,
            "row_count": len(self.bars),
            "requested_start": (
                None if self.requested_start is None else self.requested_start.isoformat()
            ),
            "requested_end": (
                None if self.requested_end is None else self.requested_end.isoformat()
            ),
            "span_start": self.bars[0].open_time.isoformat() if self.bars else None,
            "span_end": self.bars[-1].open_time.isoformat() if self.bars else None,
            "missing_days": [day.isoformat() for day in self.missing],
            "error": self.error,
        }


class BinanceBarAcquirer:
    """Fetches daily klines for one symbol, preserving responses before decoding."""

    def __init__(self, *, acquirer: RawHttpAcquirer, base_url: str) -> None:
        self._acquirer = acquirer
        self._base_url = base_url.rstrip("/")

    def acquire(
        self, *, symbol: str, start_time: datetime, end_time: datetime,
        limit: int = 1000, max_pages: int = 64,
    ) -> SymbolAcquisition:
        if start_time > end_time:
            return SymbolAcquisition(
                symbol=symbol, state=SymbolState.ALREADY_CURRENT,
                requested_start=start_time, requested_end=end_time,
            )

        # Binance caps a klines response at `limit` rows, so a multi-year backfill
        # needs pagination. Every page is preserved as raw evidence in its own right.
        collected: list[KlineBar] = []
        cursor = start_time
        pages = 0
        while cursor <= end_time and pages < max_pages:
            pages += 1
            outcome: AcquisitionOutcome = self._acquirer.get_json(
                provider=BINANCE_PROVIDER, url=f"{self._base_url}/api/v3/klines",
                params={
                    "symbol": symbol, "interval": "1d",
                    "startTime": int(cursor.timestamp() * 1000),
                    "endTime": int(end_time.timestamp() * 1000), "limit": limit,
                },
                source_id=KLINES_SOURCE_ID, original_name=f"binance_klines_{symbol}.json",
            )
            if not outcome.ok:
                return SymbolAcquisition(
                    symbol=symbol, state=SymbolState.FAILED,
                    requested_start=start_time, requested_end=end_time,
                    error=f"{outcome.failure_kind}: {outcome.detail}",
                )
            try:
                page = parse_klines(
                    outcome.payload, symbol=symbol, start_time=cursor, end_time=end_time,
                    raw_object_id=str(outcome.raw_object_id),
                )
            except (BinanceSnapshotError, BinanceUniverseError) as exc:
                return SymbolAcquisition(
                    symbol=symbol, state=SymbolState.INVALID,
                    requested_start=start_time, requested_end=end_time,
                    error=f"invalid klines response: {exc}",
                )
            if not page:
                break
            collected.extend(page)
            advanced = page[-1].open_time + timedelta(seconds=DAY_SECONDS)
            if advanced <= cursor:
                break
            cursor = advanced

        bars = sorted({b.dedupe_key: b for b in collected}.values(), key=lambda b: b.open_time)
        if not bars:
            return SymbolAcquisition(
                symbol=symbol, state=SymbolState.EMPTY,
                requested_start=start_time, requested_end=end_time,
                error="no rows returned",
            )

        holes = missing_days(bars, start_time=start_time, end_time=end_time)
        if holes:
            return SymbolAcquisition(
                symbol=symbol, state=SymbolState.GAPPED, bars=tuple(bars),
                missing=tuple(holes), requested_start=start_time, requested_end=end_time,
                error="unresolved coverage",
            )
        return SymbolAcquisition(
            symbol=symbol, state=SymbolState.PUBLISHABLE, bars=tuple(bars),
            watermark_candidate=contiguous_prefix_end(bars),
            requested_start=start_time, requested_end=end_time,
        )


__all__ = [
    "BLOCKING_STATES",
    "DAY_MS",
    "DAY_SECONDS",
    "BinanceBarAcquirer",
    "BinanceSnapshotError",
    "KlineBar",
    "SymbolAcquisition",
    "SymbolState",
    "WatermarkStore",
    "bars_from_records",
    "contiguous_prefix_end",
    "expected_days",
    "merge_canonical_bars",
    "missing_days",
    "parse_klines",
    "resume_start",
    "symbol_covers_range",
    "validate_bar_values",
    "validate_open_time",
]
