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
- Rate limiting: polite budget defaults to 120 req/min (ticket DATA-009).
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
INSTRUMENT_ALL_ENDPOINT: Final[str] = "/instrument"
PROVENANCE_SOURCE: Final[str] = "bitmex_funding"
PERP_INSTRUMENT_TYP: Final[str] = "FFWCSX"
_US_PER_SECOND: Final[int] = 1_000_000
_MAX_COUNT_PER_REQ: Final[int] = 500
_DEFAULT_REQUESTS_PER_MINUTE: Final[int] = 120
_DEFAULT_429_RETRIES: Final[int] = 5
_DEFAULT_429_SLEEP_S: Final[float] = 5.0
_MAX_429_SLEEP_S: Final[float] = 60.0

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
        # Already-normalized records may only carry timestamp_us.
        raw_us = item.get("timestamp_us")
        if raw_us is not None:
            try:
                dt_ts = datetime.fromtimestamp(int(raw_us) / _US_PER_SECOND, tz=timezone.utc)
            except (TypeError, ValueError, OSError, OverflowError):
                dt_ts = None
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

    # Accept raw BitMEX keys (fundingRate) or already-normalized (funding_rate).
    raw_rate = item.get("fundingRate", item.get("funding_rate"))
    try:
        funding_rate = float(raw_rate if raw_rate is not None else 0.0)
    except (ValueError, TypeError) as exc:
        raise BitMEXFundingError(
            f"invalid fundingRate: {raw_rate}",
            context={"item": dict(item)},
        ) from exc

    raw_daily = item.get("fundingRateDaily", item.get("funding_rate_daily"))
    try:
        if raw_daily is None:
            funding_rate_daily = funding_rate * 3.0
        else:
            funding_rate_daily = float(raw_daily)
    except (ValueError, TypeError):
        funding_rate_daily = funding_rate * 3.0

    funding_interval = str(
        item.get("fundingInterval", item.get("funding_interval")) or ""
    ).strip()

    ts_iso = dt_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    ts_us = _dt_to_us(dt_ts)

    avail_raw = item.get("availability_time")
    if availability_time is not None:
        avail_us = _dt_to_us(availability_time)
    elif avail_raw is not None:
        try:
            avail_us = int(avail_raw)
        except (TypeError, ValueError):
            avail_us = ts_us
    else:
        avail_us = ts_us

    return {
        "timestamp": ts_iso,
        "timestamp_us": ts_us,
        "symbol": symbol,
        "funding_rate": funding_rate,
        "funding_rate_daily": funding_rate_daily,
        "funding_interval": funding_interval,
        "source": str(item.get("source") or PROVENANCE_SOURCE),
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
        # One entry per rate-limit bout (not per retry attempt).
        self.rate_limit_incidents: list[dict[str, Any]] = []

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

            new_on_page = 0
            for item in res:
                norm = normalize_funding_record(item)
                key = (norm["symbol"], norm["timestamp_us"])
                if key not in all_records:
                    new_on_page += 1
                all_records[key] = norm

            # Stop when a full page contributes no new keys (pagination stall /
            # ignored start offset). Without this, a stuck API loops forever.
            if new_on_page == 0:
                break

            if len(res) < fetch_count:
                break

            start_idx += len(res)

        ordered = [all_records[k] for k in sorted(all_records.keys())]
        return ordered

    def fetch_perp_symbols(
        self,
        *,
        state: str | None = "Open",
        active_only: bool = True,
    ) -> list[str]:
        """Discover perpetual contract symbols from BitMEX.

        Filters instruments by type ``FFWCSX`` (perpetual contract) and optionally
        by ``state``. Returns sorted uppercase symbols.

        Parameters
        ----------
        state:
            If set, keep only instruments whose ``state`` matches (e.g. ``Open``).
            Pass ``None`` to include every state (Open, Settled, Unlisted, …).
        active_only:
            If True (default), query ``/instrument/active`` (open book only).
            If False, paginate ``/instrument`` with ``typ=FFWCSX`` so settled and
            other historical perps that still expose funding history are included
            (DATA-009 full universe).
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
            if not isinstance(item, dict):
                continue
            typ = str(item.get("typ") or "").strip()
            if typ != PERP_INSTRUMENT_TYP:
                continue
            if state is not None and str(item.get("state") or "").strip() != state:
                continue
            sym = str(item.get("symbol") or "").strip().upper()
            if sym:
                symbols.add(sym)
        return sorted(symbols)

    def _fetch_all_perp_instruments(self) -> list[dict[str, Any]]:
        """Paginate GET /instrument filtered to perpetual contracts (all states)."""
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

            # Same stall guard as fetch_funding: if /instrument ignores start and
            # repeats a full page, stop rather than growing all_items forever.
            new_on_page = 0
            for item in page:
                sym = str(item.get("symbol") or "").strip().upper()
                if sym and sym not in seen:
                    seen.add(sym)
                    new_on_page += 1
            all_items.extend(page)
            if new_on_page == 0:
                break

            if len(page) < _MAX_COUNT_PER_REQ:
                break
            start_idx += len(page)
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
        return [item for item in res if isinstance(item, dict)]

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
                # Floor at default polite delay; ceiling so a huge Retry-After
                # cannot stall the whole backfill for hours.
                sleep_s = min(
                    max(sleep_s, _DEFAULT_429_SLEEP_S),
                    _MAX_429_SLEEP_S,
                )
                if incident is None:
                    # One rate-limit incident per bout, not per retry attempt.
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
