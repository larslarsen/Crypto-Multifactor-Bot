"""FUND-005 — BitMEX Perpetual Funding Rate Ingestion & Cashflow Provider.

Ingests historical funding rates from BitMEX GET /funding endpoint, normalizes
them into a PyArrow table, and provides an interface for computing point-in-time
funding cashflows on perpetual positions.

Key semantics:
- Source: BitMEX REST /funding (GET /api/v1/funding).
- 8-hour funding settlement intervals (handles 2016 daily-interval transition).
- Quote FX assumption: USDT = USD 1:1.
- Inverse contracts (XBTUSD): base currency payout = -1 * position_qty * funding_rate,
  converted to USD equivalent using point-in-time BTC/USD price.
- Rate limiting: respects 180 req/min limit.
"""

from __future__ import annotations

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
PROVENANCE_SOURCE: Final[str] = "bitmex_funding"
_US_PER_SECOND: Final[int] = 1_000_000
_MAX_COUNT_PER_REQ: Final[int] = 500

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


def _dt_to_us(dt: datetime) -> int:
    return int(_require_utc(dt, field="timestamp").timestamp() * _US_PER_SECOND)


def parse_iso_datetime(value: Any) -> datetime | None:
    """Parse ISO datetime string into UTC datetime."""
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


def normalize_funding_record(
    item: Mapping[str, Any],
    *,
    availability_time: datetime | None = None,
) -> dict[str, Any]:
    """Normalize raw BitMEX /funding JSON item into typed record dictionary."""
    if not isinstance(item, Mapping):
        raise BitMEXFundingError(
            "item must be a mapping",
            context={"type": type(item).__name__},
        )

    raw_ts = item.get("timestamp")
    dt_ts = parse_iso_datetime(raw_ts)
    if dt_ts is None:
        raise BitMEXFundingError(
            "funding record missing valid ISO timestamp",
            context={"item": dict(item)},
        )

    symbol = str(item.get("symbol") or "").strip().upper()
    if not symbol:
        raise BitMEXFundingError(
            "funding record missing symbol",
            context={"item": dict(item)},
        )

    try:
        funding_rate = float(item.get("fundingRate") or 0.0)
    except (ValueError, TypeError) as exc:
        raise BitMEXFundingError(
            f"invalid fundingRate: {item.get('fundingRate')}",
            context={"item": dict(item)},
        ) from exc

    try:
        funding_rate_daily = float(item.get("fundingRateDaily") or (funding_rate * 3.0))
    except (ValueError, TypeError):
        funding_rate_daily = funding_rate * 3.0

    funding_interval = str(item.get("fundingInterval") or "").strip()

    ts_iso = dt_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    ts_us = _dt_to_us(dt_ts)

    avail_dt = availability_time or dt_ts
    avail_us = _dt_to_us(avail_dt)

    return {
        "timestamp": ts_iso,
        "timestamp_us": ts_us,
        "symbol": symbol,
        "funding_rate": funding_rate,
        "funding_rate_daily": funding_rate_daily,
        "funding_interval": funding_interval,
        "source": PROVENANCE_SOURCE,
        "availability_time": avail_us,
    }


def build_funding_table(
    records: Sequence[Mapping[str, Any]],
    *,
    availability_time: datetime | None = None,
) -> pa.Table:
    """Build PyArrow table adhering to BITMEX_FUNDING_SCHEMA from raw or normalized records."""
    normalized: dict[tuple[str, int], dict[str, Any]] = {}
    for r in records:
        norm = normalize_funding_record(r, availability_time=availability_time)
        key = (norm["symbol"], norm["timestamp_us"])
        normalized[key] = norm

    if not normalized:
        raise BitMEXFundingError("cannot build funding table from empty records")

    ordered = [normalized[k] for k in sorted(normalized.keys())]
    return pa.table(
        {
            "timestamp": [r["timestamp"] for r in ordered],
            "timestamp_us": [r["timestamp_us"] for r in ordered],
            "symbol": [r["symbol"] for r in ordered],
            "funding_rate": [r["funding_rate"] for r in ordered],
            "funding_rate_daily": [r["funding_rate_daily"] for r in ordered],
            "funding_interval": [r["funding_interval"] for r in ordered],
            "source": [r["source"] for r in ordered],
            "availability_time": [r["availability_time"] for r in ordered],
        },
        schema=BITMEX_FUNDING_SCHEMA,
    )


class BitMEXFundingClient:
    """REST client for BitMEX GET /funding endpoint with rate limiting and pagination."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = 30.0,
        requests_per_minute: int = 180,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url: str = base_url.strip().rstrip("/")
        self._timeout_s: float = float(timeout_s)
        self._min_interval_s: float = 60.0 / max(1, requests_per_minute)
        self._last_request_time: float = 0.0
        self._client: httpx.Client | None = client

    def fetch_funding(
        self,
        symbol: str = "XBTUSD",
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        count: int = _MAX_COUNT_PER_REQ,
    ) -> list[dict[str, Any]]:
        """Fetch historical funding rates for a symbol with pagination."""
        if not symbol or not isinstance(symbol, str):
            raise BitMEXFundingError("symbol must be a non-empty string")

        sym = symbol.strip().upper()
        url = f"{self._base_url}{FUNDING_ENDPOINT}"

        all_records: dict[tuple[str, int], dict[str, Any]] = {}
        start_idx = 0
        fetch_count = min(count, _MAX_COUNT_PER_REQ)

        while True:
            params: dict[str, Any] = {
                "symbol": sym,
                "count": fetch_count,
                "start": start_idx,
                "reverse": "false",
            }
            if start_time is not None:
                st = _require_utc(start_time, field="start_time")
                params["startTime"] = st.strftime("%Y-%m-%d %H:%M:%S")
            if end_time is not None:
                et = _require_utc(end_time, field="end_time")
                params["endTime"] = et.strftime("%Y-%m-%d %H:%M:%S")

            res = self._get(url, params)
            if not isinstance(res, list):
                raise BitMEXFundingError(
                    "BitMEX /funding endpoint returned non-list response",
                    context={"response": res},
                )

            if not res:
                break

            for item in res:
                norm = normalize_funding_record(item)
                all_records[(norm["symbol"], norm["timestamp_us"])] = norm

            if len(res) < fetch_count:
                break

            start_idx += len(res)

        ordered = [all_records[k] for k in sorted(all_records.keys())]
        return ordered

    def fetch_perp_symbols(self, *, state: str | None = "Open") -> list[str]:
        """Discover all active perpetual contract symbols from BitMEX.

        Filters instruments by type ``FFWCSX`` (perpetual contract) and optionally
        by ``state``. Returns sorted uppercase symbols.
        """
        url = f"{self._base_url}{INSTRUMENT_ENDPOINT}"
        res = self._get(url, {})
        if not isinstance(res, list):
            raise BitMEXFundingError(
                "BitMEX /instrument/active endpoint returned non-list response",
                context={"response": res},
            )

        symbols: set[str] = set()
        for item in res:
            if not isinstance(item, dict):
                continue
            typ = str(item.get("typ") or "").strip()
            if typ != "FFWCSX":
                continue
            if state is not None and str(item.get("state") or "").strip() != state:
                continue
            sym = str(item.get("symbol") or "").strip().upper()
            if sym:
                symbols.add(sym)
        return sorted(symbols)

    def _get(self, url: str, params: dict[str, Any]) -> Any:
        self._throttle()
        if self._client:
            r = self._client.get(url, params=params)
        else:
            with httpx.Client(timeout=self._timeout_s) as c:
                r = c.get(url, params=params)

        if r.status_code != 200:
            raise BitMEXFundingError(
                f"BitMEX GET /funding failed with HTTP {r.status_code}",
                context={"status_code": r.status_code, "body": r.text[:500]},
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
        for col in ("timestamp_us", "symbol", "funding_rate"):
            if col not in table.column_names:
                raise BitMEXFundingError(
                    f"Table missing required column '{col}'",
                    context={"columns": list(table.column_names)},
                )
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
        """Compute cumulative USD funding cashflow for position held over [start_time, end_time].

        Cashflow convention:
        - Long position (position_qty > 0) pays funding when rate > 0 (negative cashflow).
        - Short position (position_qty < 0) receives funding when rate > 0 (positive cashflow).
        - For linear contracts (e.g. USDT perps):
          cashflow_usd = -1.0 * position_qty * mark_price * funding_rate
        - For inverse contracts (e.g. XBTUSD):
          base_payout = -1.0 * position_qty_usd * funding_rate  (in BTC)
          cashflow_usd = base_payout * btc_usd_price
        """
        events = self.get_funding_events(symbol, start_time, end_time)
        if not events:
            return 0.0

        total_cashflow_usd = 0.0

        for ev in events:
            rate = float(ev["funding_rate"])
            ts_dt = parse_iso_datetime(ev["timestamp"]) or start_time

            # Resolve price for inverse conversion or mark price
            price = mark_price
            if pit_prices:
                if ts_dt in pit_prices:
                    price = float(pit_prices[ts_dt])
                elif ev["timestamp_us"] in pit_prices:
                    price = float(pit_prices[ev["timestamp_us"]])

            if is_inverse or symbol.upper() == "XBTUSD":
                # Inverse contract: position_qty is USD notional.
                # Base payout (e.g. BTC) = -1.0 * (position_qty / price) * rate if position is contracts
                # Or for XBTUSD, 1 contract = $1 USD.
                # Funding payment in BTC = -1.0 * position_qty_usd * funding_rate / price (or rate * contracts / price)
                # Converting BTC payout back to USD: BTC_payout * price = -1.0 * position_qty_usd * funding_rate
                # Note: in BitMEX XBTUSD, funding = position_usd * funding_rate in USD terms!
                base_btc_payout = -1.0 * position_qty * rate / max(price, 1e-8)
                cashflow_usd = base_btc_payout * price
            else:
                # Linear contract
                cashflow_usd = -1.0 * position_qty * price * rate

            total_cashflow_usd += cashflow_usd

        return total_cashflow_usd
