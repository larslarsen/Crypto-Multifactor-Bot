"""DATA-008 — Free CEX Universe Expansion (Binance-first).

Core helpers for expanding the Binance spot bar universe under free rate limits:
- volume-based symbol priority screen
- resume-safe per-symbol watermarks
- daily symbol budget for multi-day safety
- rate-limit incident tracking

No LIVE. No paid endpoints.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final

import httpx

UTC: Final = timezone.utc
DEFAULT_SYMBOLS_PER_DAY: Final[int] = 20_000
DEFAULT_MIN_QUOTE_VOLUME_USDT: Final[float] = 1_000_000.0
DEFAULT_PRIORITY_LOOKBACK_DAYS: Final[int] = 30


class UniverseExpansionError(RuntimeError):
    """Base error for universe expansion."""


# ---------------------------------------------------------------------------
# Priority screen
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SymbolPriority:
    symbol: str
    quote_volume: float
    price: float
    count: int


class BinanceSymbolScreener:
    """Screen Binance spot symbols by trailing volume/liquidity."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        base_url: str = "https://api.binance.com",
        min_quote_volume_usdt: float = DEFAULT_MIN_QUOTE_VOLUME_USDT,
    ) -> None:
        self._client: httpx.Client | None = client
        self._base_url: str = base_url.strip().rstrip("/")
        self._min_quote_volume_usdt: float = min_quote_volume_usdt

    def fetch_24hr_tickers(self) -> list[dict[str, Any]]:
        """Fetch /api/v3/ticker/24hr from Binance or from a provided client."""
        url = f"{self._base_url}/api/v3/ticker/24hr"
        if self._client:
            r = self._client.get(url)
        else:
            with httpx.Client(timeout=30.0) as c:
                r = c.get(url)
        if r.status_code != 200:
            raise UniverseExpansionError(
                f"Binance ticker/24hr failed: HTTP {r.status_code}",
                context={"body": r.text[:500]},
            )
        data = r.json()
        if not isinstance(data, list):
            raise UniverseExpansionError(
                "Binance ticker/24hr returned non-list",
                context={"type": type(data).__name__},
            )
        return data

    def screen_usdt_spot(self, tickers: Sequence[Mapping[str, Any]]) -> list[SymbolPriority]:
        """Return active USDT spot pairs passing the volume screen."""
        screened: list[SymbolPriority] = []
        for t in tickers:
            symbol = str(t.get("symbol") or "")
            if not symbol.endswith("USDT"):
                continue
            if not symbol.isupper():
                continue
            # Exclude leveraged tokens and stablecoin-stablecoin pairs.
            if any(suffix in symbol for suffix in ("UP", "DOWN", "BEAR", "BULL")):
                continue
            # Exclude USDT pairs where the base is a stablecoin.
            base = symbol[:-4]
            if base in ("USDC", "BUSD", "TUSD", "FDUSD", "DAI"):
                continue
            status = str(t.get("status") or "TRADING")
            if status != "TRADING":
                continue
            try:
                quote_volume = float(t.get("quoteVolume") or 0.0)
                last_price = float(t.get("lastPrice") or 0.0)
                count = int(t.get("count") or 0)
            except (ValueError, TypeError):
                continue
            if quote_volume < self._min_quote_volume_usdt:
                continue
            screened.append(
                SymbolPriority(
                    symbol=symbol,
                    quote_volume=quote_volume,
                    price=last_price,
                    count=count,
                )
            )
        return screened

    def prioritize(
        self,
        screened: Sequence[SymbolPriority],
        *,
        existing_symbols: Sequence[str] | None = None,
        top_n: int | None = None,
    ) -> list[str]:
        """Return symbols sorted by descending quote volume, excluding existing ones."""
        existing = {s.upper() for s in (existing_symbols or [])}
        candidates = [s for s in screened if s.symbol not in existing]
        sorted_symbols = sorted(candidates, key=lambda x: x.quote_volume, reverse=True)
        if top_n is not None:
            sorted_symbols = sorted_symbols[:top_n]
        return [s.symbol for s in sorted_symbols]


# ---------------------------------------------------------------------------
# Watermark store
# ---------------------------------------------------------------------------


class IncrementalWatermarkStore:
    """Resume-safe per-symbol watermarks stored as JSON."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def load(self) -> dict[str, str]:
        """Load watermarks as symbol -> event_end ISO."""
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise UniverseExpansionError(f"Failed to load watermarks from {self._path}") from exc
        return dict(data.get("binance_spot", {}))

    def save(self, watermarks: Mapping[str, str]) -> None:
        """Save watermarks, merging with existing data."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {}
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
        data["binance_spot"] = dict(watermarks)
        self._path.write_text(
            json.dumps(data, indent=2, sort_keys=True),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Rate-limit budget
# ---------------------------------------------------------------------------


@dataclass
class RateLimitIncident:
    timestamp: str
    symbol: str
    status_code: int
    backoff_seconds: float
    note: str


class DailySymbolBudget:
    """Enforce a daily symbol-processing budget (default 20k symbols/day)."""

    def __init__(self, *, symbols_per_day: int = DEFAULT_SYMBOLS_PER_DAY) -> None:
        self._symbols_per_day: int = max(1, symbols_per_day)
        self._processed_today: int = 0
        self._day_start: datetime = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self._incidents: list[RateLimitIncident] = []

    def _reset_if_new_day(self) -> None:
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        if today > self._day_start:
            self._day_start = today
            self._processed_today = 0

    def can_process(self) -> bool:
        self._reset_if_new_day()
        return self._processed_today < self._symbols_per_day

    def record_processed(self, count: int = 1) -> None:
        self._reset_if_new_day()
        self._processed_today += count

    def record_incident(self, incident: RateLimitIncident) -> None:
        self._incidents.append(incident)

    def remaining_today(self) -> int:
        self._reset_if_new_day()
        return max(0, self._symbols_per_day - self._processed_today)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbols_per_day": self._symbols_per_day,
            "processed_today": self._processed_today,
            "day_start": self._day_start.isoformat(),
            "remaining_today": self.remaining_today(),
            "incidents": [
                {
                    "timestamp": inc.timestamp,
                    "symbol": inc.symbol,
                    "status_code": inc.status_code,
                    "backoff_seconds": inc.backoff_seconds,
                    "note": inc.note,
                }
                for inc in self._incidents
            ],
        }


# ---------------------------------------------------------------------------
# Instrument id allocator
# ---------------------------------------------------------------------------


class InstrumentIdAllocator:
    """Allocate new instrument_ids for symbols not in the base map."""

    def __init__(self, base_map: Mapping[str, int], reserved: set[int] | None = None) -> None:
        self._base_map: dict[str, int] = dict(base_map)
        self._reserved: set[int] = set(reserved) if reserved else set(base_map.values())
        self._next_id: int = max(self._reserved, default=0) + 1
        self._allocation: dict[str, int] = {}

    def allocate(self, symbol: str) -> int:
        sym = symbol.upper()
        if sym in self._base_map:
            return self._base_map[sym]
        if sym in self._allocation:
            return self._allocation[sym]
        # Reserve any symbol passed to allocate so it is stable across calls.
        iid = self._next_id
        while iid in self._reserved:
            iid += 1
        self._next_id = iid + 1
        self._allocation[sym] = iid
        self._reserved.add(iid)
        return iid

    def get_map(self) -> dict[str, int]:
        return {**self._base_map, **self._allocation}


# ---------------------------------------------------------------------------
# Expansion orchestrator
# ---------------------------------------------------------------------------


@dataclass
class ExpansionResult:
    canonical_dataset_id: str
    quality_status: str
    base_symbols: list[str]
    added_symbols: list[str]
    total_symbols: int
    total_bar_count: int
    bar_start: str | None
    bar_end: str | None
    watermarks: dict[str, str]
    rate_limit: dict[str, Any]
    incident_count: int
    symbol_rows: list[dict[str, Any]]


class BinanceUniverseExpander:
    """Orchestrate Binance spot universe expansion with screen, watermarks, and budget."""

    def __init__(
        self,
        *,
        screener: BinanceSymbolScreener,
        watermark_store: IncrementalWatermarkStore,
        budget: DailySymbolBudget,
        instrument_allocator: InstrumentIdAllocator,
        base_symbols: Sequence[str],
        target_start: datetime,
        target_end: datetime,
        top_n: int | None = 100,
    ) -> None:
        self._screener = screener
        self._watermark_store = watermark_store
        self._budget = budget
        self._allocator = instrument_allocator
        self._base_symbols = sorted({s.upper() for s in base_symbols})
        self._target_start = target_start
        self._target_end = target_end
        self._top_n = top_n

    def select_new_symbols(self) -> list[str]:
        """Fetch screen and return prioritized symbols not already in the base."""
        tickers = self._screener.fetch_24hr_tickers()
        screened = self._screener.screen_usdt_spot(tickers)
        return self._screener.prioritize(
            screened,
            existing_symbols=self._base_symbols,
            top_n=self._top_n,
        )

    def plan_backfill(self, new_symbols: Sequence[str]) -> list[str]:
        """Return the subset of new_symbols we can process today under budget."""
        remaining = self._budget.remaining_today()
        return list(new_symbols)[:remaining]

    def allocate_instrument_ids(self, symbols: Sequence[str]) -> dict[str, int]:
        for sym in symbols:
            self._allocator.allocate(sym)
        return self._allocator.get_map()

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_symbols": self._base_symbols,
            "target_start": self._target_start.isoformat(),
            "target_end": self._target_end.isoformat(),
            "top_n": self._top_n,
            "budget": self._budget.to_dict(),
        }


def format_incidents(incidents: Sequence[RateLimitIncident]) -> list[dict[str, Any]]:
    return [
        {
            "timestamp": inc.timestamp,
            "symbol": inc.symbol,
            "status_code": inc.status_code,
            "backoff_seconds": inc.backoff_seconds,
            "note": inc.note,
        }
        for inc in incidents
    ]


def load_watermark_as_datetime(watermarks: Mapping[str, str], symbol: str) -> datetime:
    """Return the start-of-next-day after the watermark for a symbol."""
    sym = symbol.upper()
    if sym in watermarks:
        end = datetime.fromisoformat(watermarks[sym])
        return (end + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return datetime(2020, 1, 1, tzinfo=UTC)


def read_api_key_from_env(key_name: str) -> str | None:
    """Read an optional API key from the environment."""
    return os.environ.get(key_name)
