"""UNIVERSE-002 — Birdeye DEX new-token listing event feed ingestion provider.

Ingests forward-only DEX token listing events from Birdeye Data Services API.

Key constraints & semantics:
- Ingests listing events ONLY via /defi/v2/tokens/new_listing.
- NO price bar or candle endpoints are ever requested or supported.
- NON-survivorship-free: Listing events carry no token death / delisting records.
  `survivorship_free` is explicitly set to False on all rows.
- Source is explicitly labeled "birdeye_new_listing".
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.as_of import AsOfStore

BIRDEYE_LISTINGS_DATASET_ID: Final[str] = "birdeye_dex_listings"
PROVENANCE_SOURCE: Final[str] = "birdeye_new_listing"
DEFAULT_BASE_URL: Final[str] = "https://public-api.birdeye.so"
NEW_LISTING_ENDPOINT: Final[str] = "/defi/v2/tokens/new_listing"
_US_PER_SECOND: Final[int] = 1_000_000

BIRDEYE_LISTINGS_SCHEMA: Final[pa.Schema] = pa.schema(
    [
        ("event_id", pa.string()),
        ("chain", pa.string()),
        ("address", pa.string()),
        ("symbol", pa.string()),
        ("name", pa.string()),
        ("decimals", pa.int32()),
        ("liquidity_added_at", pa.string()),
        ("liquidity_added_at_us", pa.int64()),
        ("liquidity", pa.float64()),
        ("survivorship_free", pa.bool_()),
        ("source", pa.string()),
        ("retrieved_at", pa.string()),
        ("availability_time", pa.int64()),
    ]
)


class BirdeyeListingsError(RuntimeError):
    """Base error for Birdeye DEX listings operations."""

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.context: dict[str, object] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


def _require_utc(dt: datetime, *, field: str) -> datetime:
    if not isinstance(dt, datetime):
        raise BirdeyeListingsError(
            f"{field} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise BirdeyeListingsError(
            f"{field} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


def _dt_to_us(dt: datetime) -> int:
    return int(_require_utc(dt, field="timestamp").timestamp() * _US_PER_SECOND)


def parse_iso_datetime(value: Any) -> datetime | None:
    """Parse ISO datetime string or timestamp into UTC datetime."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e11:
            ts = ts / 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if not isinstance(value, str):
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


def normalize_listing_event(
    item: Mapping[str, Any],
    *,
    chain: str = "solana",
    retrieved_at: str | None = None,
    availability_time: datetime | None = None,
) -> dict[str, Any]:
    """Normalize a raw Birdeye new_listing event into a typed listing record."""
    if not isinstance(item, Mapping):
        raise BirdeyeListingsError(
            "item must be a mapping",
            context={"type": type(item).__name__},
        )

    address = str(item.get("address") or item.get("v3Address") or "").strip()
    if not address:
        raise BirdeyeListingsError(
            "listing event missing required 'address'",
            context={"item": dict(item)},
        )

    symbol = str(item.get("symbol") or "").strip() or "UNKNOWN"
    name = str(item.get("name") or symbol).strip()

    try:
        decimals = int(item.get("decimals") or 0)
    except (ValueError, TypeError):
        decimals = 0

    try:
        liquidity = float(item.get("liquidity") or 0.0)
    except (ValueError, TypeError):
        liquidity = 0.0

    raw_liq_time = (
        item.get("liquidityAddedAt")
        or item.get("liquidity_added_at")
        or item.get("createdAt")
    )
    dt_liq = parse_iso_datetime(raw_liq_time)
    if dt_liq is None:
        dt_liq = datetime.now(timezone.utc)

    liq_added_iso = dt_liq.strftime("%Y-%m-%dT%H:%M:%SZ")
    liq_added_us = _dt_to_us(dt_liq)

    chain_str = str(chain).strip().lower() or "solana"
    event_id = f"birdeye_{chain_str}_{address}"

    if retrieved_at is None:
        retrieved_at_raw = item.get("retrieved_at")
        if retrieved_at_raw:
            retrieved_at_str = str(retrieved_at_raw).strip()
        else:
            retrieved_at_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        retrieved_at_str = str(retrieved_at)

    avail_dt = availability_time or datetime.now(timezone.utc)
    avail_us = _dt_to_us(avail_dt)

    return {
        "event_id": event_id,
        "chain": chain_str,
        "address": address,
        "symbol": symbol,
        "name": name,
        "decimals": decimals,
        "liquidity_added_at": liq_added_iso,
        "liquidity_added_at_us": liq_added_us,
        "liquidity": liquidity,
        "survivorship_free": False,  # Explicitly False per UNIVERSE-002
        "source": PROVENANCE_SOURCE,
        "retrieved_at": retrieved_at_str,
        "availability_time": avail_us,
    }


def build_birdeye_listings_table(
    records: Sequence[Mapping[str, Any]],
    *,
    availability_time: datetime | None = None,
) -> pa.Table:
    """Build PyArrow table adhering to BIRDEYE_LISTINGS_SCHEMA from records."""
    normalized: dict[tuple[str, str], dict[str, Any]] = {}
    for r in records:
        norm = normalize_listing_event(r, availability_time=availability_time)
        key = (norm["chain"], norm["address"])
        normalized[key] = norm

    if not normalized:
        raise BirdeyeListingsError("cannot build listings table from empty records")

    ordered = [normalized[k] for k in sorted(normalized.keys())]
    return pa.table(
        {
            "event_id": [r["event_id"] for r in ordered],
            "chain": [r["chain"] for r in ordered],
            "address": [r["address"] for r in ordered],
            "symbol": [r["symbol"] for r in ordered],
            "name": [r["name"] for r in ordered],
            "decimals": [r["decimals"] for r in ordered],
            "liquidity_added_at": [r["liquidity_added_at"] for r in ordered],
            "liquidity_added_at_us": [r["liquidity_added_at_us"] for r in ordered],
            "liquidity": [r["liquidity"] for r in ordered],
            "survivorship_free": [r["survivorship_free"] for r in ordered],
            "source": [r["source"] for r in ordered],
            "retrieved_at": [r["retrieved_at"] for r in ordered],
            "availability_time": [r["availability_time"] for r in ordered],
        },
        schema=BIRDEYE_LISTINGS_SCHEMA,
    )


class BirdeyeListingsProvider:
    """Ingestion client and point-in-time event accessor for Birdeye DEX new listings."""

    def __init__(
        self,
        table: pa.Table | None = None,
        *,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        client: httpx.Client | None = None,
        as_of_store: AsOfStore | None = None,
    ) -> None:
        self._table: pa.Table | None = table
        self._api_key: str | None = api_key
        self._base_url: str = base_url.strip().rstrip("/")
        self._client: httpx.Client | None = client
        self._as_of_store: AsOfStore | None = as_of_store

    @classmethod
    def from_records(
        cls,
        records: Sequence[Mapping[str, Any]],
        *,
        availability_time: datetime | None = None,
        as_of_store: AsOfStore | None = None,
    ) -> BirdeyeListingsProvider:
        table = build_birdeye_listings_table(records, availability_time=availability_time)
        return cls(table=table, as_of_store=as_of_store)

    @classmethod
    def from_parquet(
        cls,
        path: str | Path,
        as_of_store: AsOfStore | None = None,
    ) -> BirdeyeListingsProvider:
        p = Path(path)
        if not p.exists():
            raise BirdeyeListingsError(f"Parquet file not found: {path}", context={"path": str(path)})
        table = pq.read_table(p)
        return cls(table=table, as_of_store=as_of_store)

    def fetch_new_listings(
        self,
        chain: str = "solana",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch latest new token listings from Birdeye /defi/v2/tokens/new_listing endpoint ONLY."""
        url = f"{self._base_url}{NEW_LISTING_ENDPOINT}"
        headers = {
            "Accept": "application/json",
            "X-Chain": chain,
        }
        if self._api_key:
            headers["X-API-KEY"] = self._api_key

        params = {"limit": min(limit, 50)}

        if self._client:
            res = self._client.get(url, headers=headers, params=params)
        else:
            with httpx.Client(timeout=30.0) as c:
                res = c.get(url, headers=headers, params=params)

        if res.status_code != 200:
            raise BirdeyeListingsError(
                f"Birdeye request failed with HTTP {res.status_code}",
                context={"status_code": res.status_code, "body": res.text[:500]},
            )

        data = res.json()
        if not isinstance(data, dict) or not data.get("success", False):
            raise BirdeyeListingsError(
                "Birdeye response indicates unsuccessful query",
                context={"response": data},
            )

        items = (data.get("data") or {}).get("items") or []
        records = [normalize_listing_event(i, chain=chain) for i in items]
        return records

    def universe_events_since(
        self,
        since_time: datetime,
        chain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return listing events at or after since_time."""
        if self._table is None:
            raise BirdeyeListingsError("No underlying table loaded in provider")

        s = _require_utc(since_time, field="since_time")
        s_us = _dt_to_us(s)

        rows: list[dict[str, Any]] = [dict(r) for r in self._table.to_pylist()]
        out: list[dict[str, Any]] = []
        for r in rows:
            if chain and str(r["chain"]).lower() != chain.lower():
                continue
            if r["liquidity_added_at_us"] >= s_us:
                out.append(r)
        return out

    def universe_at(
        self,
        decision_time: datetime,
        chain: str | None = None,
    ) -> list[str]:
        """Return list of DEX token addresses listed on or before decision_time."""
        if self._table is None:
            raise BirdeyeListingsError("No underlying table loaded in provider")

        d = _require_utc(decision_time, field="decision_time")
        d_us = _dt_to_us(d)

        rows = self._table.to_pylist()
        addrs: set[str] = set()
        for r in rows:
            if chain and str(r["chain"]).lower() != chain.lower():
                continue
            if r["liquidity_added_at_us"] <= d_us:
                addrs.add(str(r["address"]))
        return sorted(addrs)

    def records(self) -> list[dict[str, Any]]:
        """Return all listing records as dict rows."""
        if self._table is None:
            return []
        return [dict(r) for r in self._table.to_pylist()]
