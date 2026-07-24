"""DEX-001 — Decentralised exchange stablecoin pool OHLCV ingestion.

Ingests daily OHLCV for Uniswap V3 USDC/USDT stablecoin pools from the
GeckoTerminal public API. Used for independent FX/stablecoin peg validation.

Key semantics:
- Source: GeckoTerminal REST v2 /networks/{network}/pools/{pool}/ohlcv/day.
- Currency: token (price and volume expressed in the chosen token).
- Token: base token (USDC) so the close is the USDC/USDT exchange rate.
- Daily OHLCV only; pagination via before_timestamp.
- Rate limiting: conservative 6 req/min with automatic exponential backoff on 429.
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

DEFAULT_BASE_URL: Final[str] = "https://api.geckoterminal.com/api/v2"
DEFAULT_NETWORK: Final[str] = "arbitrum"
DEFAULT_TIMEFRAME: Final[str] = "day"
DEFAULT_CURRENCY: Final[str] = "token"
DEFAULT_TOKEN: Final[str] = "base"
PROVENANCE_SOURCE: Final[str] = "geckoterminal"
_US_PER_SECOND: Final[int] = 1_000_000
_DEFAULT_LIMIT: Final[int] = 1000
_DEFAULT_REQUESTS_PER_MIN: Final[int] = 6

DEX_OHLCV_SCHEMA: Final[pa.Schema] = pa.schema(
    [
        ("timestamp", pa.string()),
        ("timestamp_us", pa.int64()),
        ("pool_address", pa.string()),
        ("fee_tier", pa.string()),
        ("network", pa.string()),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.float64()),
        ("source", pa.string()),
        ("availability_time", pa.int64()),
    ]
)


class DEXOHLCVError(RuntimeError):
    """Base error for DEX OHLCV ingestion."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


def _require_utc(dt: datetime, *, field: str) -> datetime:
    if not isinstance(dt, datetime):
        raise DEXOHLCVError(f"{field} must be a datetime", context={"type": type(dt).__name__})
    if dt.tzinfo is None:
        raise DEXOHLCVError(f"{field} must be timezone-aware UTC", context={"value": str(dt)})
    return dt.astimezone(timezone.utc)


def _dt_to_us(dt: datetime) -> int:
    return int(_require_utc(dt, field="timestamp").timestamp() * _US_PER_SECOND)


def _parse_iso(value: str) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    val = value.strip().upper().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _ts_to_iso(unix_seconds: int) -> str:
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_ohlcv_item(
    item: Sequence[Any],
    *,
    pool_address: str,
    fee_tier: str,
    network: str,
    availability_time: datetime | None = None,
) -> dict[str, Any]:
    if len(item) < 6:
        raise DEXOHLCVError("OHLCV item must have at least 6 fields", context={"item": list(item)})

    raw_ts, open_p, high_p, low_p, close_p, volume = item[:6]
    try:
        ts_s = int(raw_ts)
    except (ValueError, TypeError) as exc:
        raise DEXOHLCVError(f"invalid timestamp: {raw_ts}", context={"item": list(item)}) from exc

    dt = datetime.fromtimestamp(ts_s, tz=timezone.utc)
    ts_iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    ts_us = _dt_to_us(dt)

    avail_dt = availability_time or dt
    avail_us = _dt_to_us(avail_dt)

    def _float(v: Any) -> float:
        try:
            return float(v)
        except (ValueError, TypeError) as exc:
            raise DEXOHLCVError(f"invalid numeric field: {v}", context={"item": list(item)}) from exc

    return {
        "timestamp": ts_iso,
        "timestamp_us": ts_us,
        "pool_address": pool_address.lower(),
        "fee_tier": fee_tier,
        "network": network,
        "open": _float(open_p),
        "high": _float(high_p),
        "low": _float(low_p),
        "close": _float(close_p),
        "volume": _float(volume),
        "source": PROVENANCE_SOURCE,
        "availability_time": avail_us,
    }


def build_dex_ohlcv_table(
    records: Sequence[Mapping[str, Any]],
    *,
    availability_time: datetime | None = None,
) -> pa.Table:
    """Build a PyArrow table adhering to DEX_OHLCV_SCHEMA from normalized records."""
    normalized: dict[tuple[str, int], dict[str, Any]] = {}
    for r in records:
        if not isinstance(r, Mapping):
            raise DEXOHLCVError("record must be a mapping", context={"type": type(r).__name__})
        key = (r["pool_address"], r["timestamp_us"])
        if key in normalized:
            # Prefer non-missing values; later records overwrite earlier.
            existing = normalized[key]
            for k in ("open", "high", "low", "close", "volume"):
                if r.get(k) is not None:
                    existing[k] = r[k]
            existing["availability_time"] = max(existing["availability_time"], r.get("availability_time", 0))
        else:
            norm = {
                "timestamp": r["timestamp"],
                "timestamp_us": r["timestamp_us"],
                "pool_address": r["pool_address"],
                "fee_tier": r["fee_tier"],
                "network": r["network"],
                "open": r["open"],
                "high": r["high"],
                "low": r["low"],
                "close": r["close"],
                "volume": r["volume"],
                "source": r["source"],
                "availability_time": r.get("availability_time", 0),
            }
            normalized[key] = norm

    if not normalized:
        raise DEXOHLCVError("cannot build DEX OHLCV table from empty records")

    ordered = [normalized[k] for k in sorted(normalized.keys())]
    avail_dt = availability_time or datetime.now(timezone.utc)
    avail_us = _dt_to_us(avail_dt)
    for r in ordered:
        if r["availability_time"] == 0:
            r["availability_time"] = avail_us

    return pa.table(
        {
            "timestamp": [r["timestamp"] for r in ordered],
            "timestamp_us": [r["timestamp_us"] for r in ordered],
            "pool_address": [r["pool_address"] for r in ordered],
            "fee_tier": [r["fee_tier"] for r in ordered],
            "network": [r["network"] for r in ordered],
            "open": [r["open"] for r in ordered],
            "high": [r["high"] for r in ordered],
            "low": [r["low"] for r in ordered],
            "close": [r["close"] for r in ordered],
            "volume": [r["volume"] for r in ordered],
            "source": [r["source"] for r in ordered],
            "availability_time": [r["availability_time"] for r in ordered],
        },
        schema=DEX_OHLCV_SCHEMA,
    )


class GeckoTerminalClient:
    """REST client for GeckoTerminal pool OHLCV with pagination and rate limiting."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        network: str = DEFAULT_NETWORK,
        timeframe: str = DEFAULT_TIMEFRAME,
        currency: str = DEFAULT_CURRENCY,
        token: str = DEFAULT_TOKEN,
        timeout_s: float = 30.0,
        requests_per_minute: int = _DEFAULT_REQUESTS_PER_MIN,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url: str = base_url.strip().rstrip("/")
        self._network: str = network.strip()
        self._timeframe: str = timeframe.strip()
        self._currency: str = currency.strip()
        self._token: str = token.strip()
        self._timeout_s: float = float(timeout_s)
        self._min_interval_s: float = 60.0 / max(1, requests_per_minute)
        self._last_request_time: float = 0.0
        self._client: httpx.Client | None = client

    def fetch_pool_ohlcv(
        self,
        pool_address: str,
        *,
        fee_tier: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[dict[str, Any]]:
        """Fetch all daily OHLCV records for a pool from start_time to end_time.

        Pagination walks backwards using ``before_timestamp``. The records are
        returned chronological order (oldest first) after de-duplication.
        """
        if not pool_address or not isinstance(pool_address, str):
            raise DEXOHLCVError("pool_address must be a non-empty string")
        if not fee_tier:
            raise DEXOHLCVError("fee_tier must be a non-empty string")

        pool = pool_address.strip()
        eff_end = _require_utc(end_time, field="end_time") if end_time else datetime.now(timezone.utc)
        before_ts = int(eff_end.timestamp())

        records: dict[tuple[str, int], dict[str, Any]] = {}
        max_iterations = 1000
        for _ in range(max_iterations):
            params: dict[str, Any] = {
                "currency": self._currency,
                "token": self._token,
                "limit": min(max(1, limit), _DEFAULT_LIMIT),
                "before_timestamp": before_ts,
            }
            data = self._get_pool_ohlcv(pool, params)
            ohlcv_list = data.get("attributes", {}).get("ohlcv_list", [])
            if not ohlcv_list:
                break

            for item in ohlcv_list:
                norm = _normalize_ohlcv_item(
                    item,
                    pool_address=pool,
                    fee_tier=fee_tier,
                    network=self._network,
                )
                key = (norm["pool_address"], norm["timestamp_us"])
                records[key] = norm

            # The API returns oldest first within the page; the next page should
            # start before the oldest timestamp in this page.
            oldest_ts = min(int(r[0]) for r in ohlcv_list)
            if oldest_ts >= before_ts:
                break
            before_ts = oldest_ts

            # Stop once we have passed the requested start_time.
            if start_time is not None:
                st = _require_utc(start_time, field="start_time")
                oldest_dt = datetime.fromtimestamp(oldest_ts, tz=timezone.utc)
                if oldest_dt <= st:
                    break

        ordered = [records[k] for k in sorted(records.keys())]
        if start_time is not None:
            st_us = _dt_to_us(start_time)
            ordered = [r for r in ordered if r["timestamp_us"] >= st_us]
        eff_end_us = _dt_to_us(eff_end)
        ordered = [r for r in ordered if r["timestamp_us"] <= eff_end_us]
        return ordered

    def _get_pool_ohlcv(self, pool_address: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/networks/{self._network}/pools/{pool_address}/ohlcv/{self._timeframe}"
        self._throttle()

        for attempt in range(3):
            if self._client:
                r = self._client.get(url, params=params)
            else:
                with httpx.Client(timeout=self._timeout_s) as c:
                    r = c.get(url, params=params)

            if r.status_code == 429:
                # Exponential backoff: 10s, 20s, 40s
                backoff = 10.0 * (2 ** attempt)
                time.sleep(backoff)
                self._last_request_time = time.monotonic()
                continue

            if r.status_code == 200:
                break

            raise DEXOHLCVError(
                f"GeckoTerminal OHLCV request failed with HTTP {r.status_code}",
                context={"url": url, "params": params, "body": r.text[:500]},
            )
        else:
            raise DEXOHLCVError(
                "GeckoTerminal OHLCV request rate limited after retries",
                context={"url": url, "params": params, "body": r.text[:500]},
            )

        payload = r.json()
        if "data" not in payload:
            raise DEXOHLCVError(
                "GeckoTerminal OHLCV response missing data field",
                context={"payload": payload},
            )
        data = payload["data"]
        if isinstance(data, list):
            if not data:
                raise DEXOHLCVError("GeckoTerminal OHLCV response data is empty list")
            data = data[0]
        if not isinstance(data, dict):
            raise DEXOHLCVError(
                "GeckoTerminal OHLCV response data is not a dict",
                context={"type": type(data).__name__},
            )
        return data

    def _throttle(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_request_time = time.monotonic()


class DEXOHLCVProvider:
    """In-memory provider of DEX OHLCV records."""

    def __init__(self, table: pa.Table) -> None:
        if not isinstance(table, pa.Table):
            raise DEXOHLCVError("table must be a PyArrow Table", context={"type": type(table).__name__})
        for col in ("timestamp_us", "pool_address", "close"):
            if col not in table.column_names:
                raise DEXOHLCVError(
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
    ) -> DEXOHLCVProvider:
        table = build_dex_ohlcv_table(records, availability_time=availability_time)
        return cls(table)

    @classmethod
    def from_parquet(cls, path: str | Path) -> DEXOHLCVProvider:
        p = Path(path)
        if not p.exists():
            raise DEXOHLCVError(f"Parquet file not found: {path}", context={"path": str(path)})
        table = pq.read_table(p)
        return cls(table)

    def get_pool_history(
        self,
        pool_address: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        """Return OHLCV records for a pool in [start_time, end_time]."""
        st = _require_utc(start_time, field="start_time")
        et = _require_utc(end_time, field="end_time")
        st_us = _dt_to_us(st)
        et_us = _dt_to_us(et)
        pool = pool_address.strip().lower()

        rows = self._table.to_pylist()
        result = [
            dict(r)
            for r in rows
            if str(r["pool_address"]).lower() == pool and st_us <= int(r["timestamp_us"]) <= et_us
        ]
        result.sort(key=lambda x: x["timestamp_us"])
        return result
