"""UNIVERSE-003 — CoinMarketCap CEX dead-coin survivorship registry provider.

Ingests CoinMarketCap inactive (dead coin) map and detail records, normalizes birth/death dates
and provenance labels, and provides point-in-time membership queries (as-of access).

Key semantics:
- birth_date: dateAdded / dateLaunched proxy for listing start.
- death_proxy_date: latestUpdateTime proxy for when CMC stopped updating the coin.
- death_date_is_proxy is ALWAYS set to True on rows with a death date proxy (and True for all dead coins).
- source is ALWAYS set to "cmc_data_api_unofficial".
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.as_of import AsOfStore

CMC_SURVIVORSHIP_DATASET_ID: Final[str] = "cmc_survivorship_universe"
PROVENANCE_SOURCE: Final[str] = "cmc_data_api_unofficial"
_US_PER_SECOND: Final[int] = 1_000_000

CMC_SURVIVORSHIP_SCHEMA: Final[pa.Schema] = pa.schema(
    [
        ("instrument_id", pa.string()),
        ("cmc_id", pa.int64()),
        ("symbol", pa.string()),
        ("slug", pa.string()),
        ("name", pa.string()),
        ("is_active", pa.bool_()),
        ("birth_date", pa.string()),
        ("death_proxy_date", pa.string()),
        ("status", pa.string()),
        ("death_date_is_proxy", pa.bool_()),
        ("source", pa.string()),
        ("retrieved_at", pa.string()),
        ("availability_time", pa.int64()),
    ]
)


class CMCSurvivorshipError(RuntimeError):
    """Base error for CMC survivorship operations."""

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
        raise CMCSurvivorshipError(
            f"{field} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise CMCSurvivorshipError(
            f"{field} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


def _dt_to_us(dt: datetime) -> int:
    return int(_require_utc(dt, field="timestamp").timestamp() * _US_PER_SECOND)


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string into UTC datetime, returning None on failure."""
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


def normalize_coin_record(
    map_item: Mapping[str, Any],
    detail_item: Mapping[str, Any] | None = None,
    *,
    retrieved_at: str | None = None,
    availability_time: datetime | None = None,
) -> dict[str, Any]:
    """Normalize a raw CMC map and detail record pair into a typed registry dictionary."""
    if not isinstance(map_item, Mapping):
        raise CMCSurvivorshipError(
            "map_item must be a mapping",
            context={"type": type(map_item).__name__},
        )
    raw_id = map_item.get("id")
    if raw_id is None:
        raw_id = map_item.get("cmc_id")
    if raw_id is None and detail_item:
        raw_id = detail_item.get("id") or detail_item.get("cmc_id")
    if raw_id is None:
        raise CMCSurvivorshipError(
            "coin missing required 'id' or 'cmc_id'",
            context={"map_item": dict(map_item)},
        )
    try:
        cmc_id = int(raw_id)
    except (ValueError, TypeError) as exc:
        raise CMCSurvivorshipError(
            f"invalid cmc_id: {raw_id}",
            context={"id": raw_id},
        ) from exc

    det = detail_item or {}
    symbol = str(
        map_item.get("symbol")
        or det.get("symbol")
        or ""
    ).strip()
    if not symbol:
        raise CMCSurvivorshipError(
            "coin missing required symbol",
            context={"id": cmc_id},
        )

    name = str(
        map_item.get("name")
        or det.get("name")
        or ""
    ).strip()
    if not name:
        raise CMCSurvivorshipError(
            "coin missing required name",
            context={"id": cmc_id},
        )

    slug = str(
        map_item.get("slug")
        or det.get("slug")
        or ""
    ).strip()

    date_launched = det.get("dateLaunched") or map_item.get("dateLaunched")
    date_added = det.get("dateAdded") or map_item.get("dateAdded")
    birth_date_raw = map_item.get("birth_date") or date_added or date_launched
    birth_date_str = str(birth_date_raw).strip() if birth_date_raw else ""

    latest_update = (
        det.get("latestUpdateTime")
        or map_item.get("latestUpdateTime")
        or map_item.get("death_proxy_date")
    )
    death_proxy_str = str(latest_update).strip() if latest_update else ""

    is_active_raw = map_item.get("is_active")
    if is_active_raw is None:
        is_active_raw = det.get("is_active")
    if is_active_raw is None:
        is_active = False
    elif isinstance(is_active_raw, str):
        is_active = is_active_raw.lower() in ("true", "1", "yes")
    else:
        is_active = bool(is_active_raw)

    status = str(
        det.get("status")
        or map_item.get("status")
        or ("inactive" if not is_active else "active")
    ).strip()

    if retrieved_at is None:
        retrieved_at_raw = map_item.get("retrieved_at") or det.get("retrieved_at")
        if retrieved_at_raw:
            retrieved_at_str = str(retrieved_at_raw).strip()
        else:
            retrieved_at_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        retrieved_at_str = str(retrieved_at)

    avail_dt = availability_time or datetime.now(timezone.utc)
    avail_us = _dt_to_us(avail_dt)

    return {
        "instrument_id": f"cmc_{cmc_id}",
        "cmc_id": cmc_id,
        "symbol": symbol,
        "slug": slug,
        "name": name,
        "is_active": is_active,
        "birth_date": birth_date_str or None,
        "death_proxy_date": death_proxy_str or None,
        "status": status,
        "death_date_is_proxy": True,
        "source": PROVENANCE_SOURCE,
        "retrieved_at": retrieved_at_str,
        "availability_time": avail_us,
    }


def build_cmc_survivorship_table(
    records: Sequence[Mapping[str, Any]],
    *,
    availability_time: datetime | None = None,
) -> pa.Table:
    """Build PyArrow table adhering to CMC_SURVIVORSHIP_SCHEMA from records."""
    normalized: dict[int, dict[str, Any]] = {}
    for r in records:
        norm = normalize_coin_record(r, availability_time=availability_time)
        normalized[norm["cmc_id"]] = norm

    if not normalized:
        raise CMCSurvivorshipError("cannot build registry table from empty records")

    ordered = [normalized[k] for k in sorted(normalized.keys())]
    return pa.table(
        {
            "instrument_id": [r["instrument_id"] for r in ordered],
            "cmc_id": [r["cmc_id"] for r in ordered],
            "symbol": [r["symbol"] for r in ordered],
            "slug": [r["slug"] for r in ordered],
            "name": [r["name"] for r in ordered],
            "is_active": [r["is_active"] for r in ordered],
            "birth_date": [r["birth_date"] for r in ordered],
            "death_proxy_date": [r["death_proxy_date"] for r in ordered],
            "status": [r["status"] for r in ordered],
            "death_date_is_proxy": [r["death_date_is_proxy"] for r in ordered],
            "source": [r["source"] for r in ordered],
            "retrieved_at": [r["retrieved_at"] for r in ordered],
            "availability_time": [r["availability_time"] for r in ordered],
        },
        schema=CMC_SURVIVORSHIP_SCHEMA,
    )


class CMCSurvivorshipProvider:
    """Registry provider and point-in-time as-of membership accessor for CMC dead coins."""

    def __init__(
        self,
        table: pa.Table,
        as_of_store: AsOfStore | None = None,
    ) -> None:
        if not isinstance(table, pa.Table):
            raise CMCSurvivorshipError(
                "table must be a PyArrow Table",
                context={"type": type(table).__name__},
            )
        for field in ("instrument_id", "symbol", "death_date_is_proxy", "source"):
            if field not in table.column_names:
                raise CMCSurvivorshipError(
                    f"table missing required column '{field}'",
                    context={"columns": list(table.column_names)},
                )
        self._table: pa.Table = table
        self._as_of_store: AsOfStore | None = as_of_store

    @classmethod
    def from_records(
        cls,
        records: Sequence[Mapping[str, Any]],
        *,
        availability_time: datetime | None = None,
        as_of_store: AsOfStore | None = None,
    ) -> CMCSurvivorshipProvider:
        table = build_cmc_survivorship_table(records, availability_time=availability_time)
        return cls(table, as_of_store=as_of_store)

    @classmethod
    def from_csv(
        cls,
        path: str | Path,
        *,
        availability_time: datetime | None = None,
        as_of_store: AsOfStore | None = None,
    ) -> CMCSurvivorshipProvider:
        p = Path(path)
        if not p.exists():
            raise CMCSurvivorshipError(
                f"CSV file not found: {path}",
                context={"path": str(path)},
            )
        records: list[dict[str, Any]] = []
        with open(p, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        return cls.from_records(records, availability_time=availability_time, as_of_store=as_of_store)

    @classmethod
    def from_parquet(
        cls,
        path: str | Path,
        as_of_store: AsOfStore | None = None,
    ) -> CMCSurvivorshipProvider:
        p = Path(path)
        if not p.exists():
            raise CMCSurvivorshipError(
                f"Parquet file not found: {path}",
                context={"path": str(path)},
            )
        table = pq.read_table(p)
        return cls(table, as_of_store=as_of_store)

    def get_table(self) -> pa.Table:
        """Return underlying PyArrow Table."""
        return self._table

    def universe_at(
        self,
        decision_time: datetime,
        *,
        ignore_availability: bool = True,
    ) -> list[str]:
        """Return list of instrument_ids eligible in the CMC universe at decision_time.

        A coin is eligible if:
        1. availability_time <= decision_time_us (unless ignore_availability=True for historical backfills).
        2. birth_date <= decision_time (if birth_date is set).
        3. Either is_active is True OR (death_proxy_date is set and decision_time <= death_proxy_date).
        """
        t = _require_utc(decision_time, field="decision_time")
        t_us = _dt_to_us(t)

        inst_col = self._table.column("instrument_id").to_pylist()
        is_active_col = self._table.column("is_active").to_pylist()
        birth_col = self._table.column("birth_date").to_pylist()
        death_col = self._table.column("death_proxy_date").to_pylist()
        avail_col = self._table.column("availability_time").to_pylist()

        eligible: set[str] = set()

        for i in range(self._table.num_rows):
            if not ignore_availability:
                avail_us = avail_col[i]
                if avail_us is not None and avail_us > t_us:
                    continue

            birth_str = birth_col[i]
            if birth_str:
                birth_dt = parse_iso_datetime(birth_str)
                if birth_dt and birth_dt > t:
                    continue

            is_active = bool(is_active_col[i])
            death_str = death_col[i]

            if not is_active and death_str:
                death_dt = parse_iso_datetime(death_str)
                if death_dt and t > death_dt:
                    continue

            eligible.add(str(inst_col[i]))

        return sorted(eligible)

    def records(self) -> list[dict[str, Any]]:
        """Return all registry records as dictionary rows with explicit provenance labels."""
        rows: list[dict[str, Any]] = [dict(r) for r in self._table.to_pylist()]
        return rows
