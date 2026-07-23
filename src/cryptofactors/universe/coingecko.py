"""UNIVERSE-001 — CoinGecko survivorship-free universe provider.

Fetches active and inactive coin membership from the CoinGecko free tier,
stores point-in-time Arrow snapshots (logical dataset_id ``coingecko_universe``),
and answers ``universe_at(decision_time)`` from eligible snapshots only.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.as_of import AsOfStore
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetStatistics,
    OutputFileSpec,
    PublishPlan,
    QualityStatus,
    RowCountPolicy,
    RowCountReceipt,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.catalog.dataset.publisher import DatasetPublisher

COINGECKO_UNIVERSE_DATASET_ID: Final[str] = "coingecko_universe"
_DEFAULT_BASE_URL: Final[str] = "https://api.coingecko.com/api/v3"
_COINS_LIST_PATH: Final[str] = "/coins/list"
_MAX_REQUESTS_PER_MINUTE: Final[int] = 10
_SCHEMA_NAME: Final[str] = "coingecko_universe"
_SCHEMA_VERSION: Final[str] = "1"
_TRANSFORM_NAME: Final[str] = "coingecko_universe_snapshot"
_TRANSFORM_VERSION: Final[str] = "1"
_CODE_COMMIT: Final[str] = "UNIVERSE-001"
_US_PER_SECOND: Final[int] = 1_000_000

_UNIVERSE_SCHEMA: Final[pa.Schema] = pa.schema(
    [
        ("instrument_id", pa.string()),
        ("symbol", pa.string()),
        ("name", pa.string()),
        ("active", pa.bool_()),
        ("availability_time", pa.int64()),
    ]
)


class CoinGeckoUniverseError(RuntimeError):
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
        raise CoinGeckoUniverseError(
            f"{field} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise CoinGeckoUniverseError(
            f"{field} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


def _dt_to_us(dt: datetime) -> int:
    return int(_require_utc(dt, field="timestamp").timestamp() * _US_PER_SECOND)


@dataclass(frozen=True, slots=True)
class _UniverseSnapshot:
    availability_time: datetime
    table: pa.Table
    instrument_ids: tuple[str, ...]
    rows: tuple[dict[str, str | bool], ...]


class CoinGeckoUniverseProvider:
    def __init__(
        self,
        as_of_store: AsOfStore,
        publisher: DatasetPublisher | None = None,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_s: float = 60.0,
        max_requests_per_minute: int = _MAX_REQUESTS_PER_MINUTE,
        client: httpx.Client | None = None,
    ) -> None:
        if as_of_store is None:
            raise CoinGeckoUniverseError("as_of_store must not be None")
        if max_requests_per_minute < 1:
            raise CoinGeckoUniverseError(
                "max_requests_per_minute must be >= 1",
                context={"max_requests_per_minute": max_requests_per_minute},
            )
        base = base_url.strip().rstrip("/")
        if not base:
            raise CoinGeckoUniverseError("base_url must be non-empty")
        self._as_of_store: AsOfStore = as_of_store
        self._publisher: DatasetPublisher | None = publisher
        self._base_url: str = base
        self._timeout_s: float = float(timeout_s)
        self._max_requests_per_minute: int = int(max_requests_per_minute)
        self._client: httpx.Client | None = client
        self._owns_client: bool = client is None
        self._request_times: list[float] = []
        self._snapshots: list[_UniverseSnapshot] = []
        self._last_published_dataset_id: str | None = None

    def fetch_universe(self) -> list[dict[str, str | bool]]:
        availability_time = datetime.now(tz=timezone.utc)
        active_raw = self._fetch_status("active")
        inactive_raw = self._fetch_status("inactive")
        by_id: dict[str, dict[str, str | bool]] = {}
        for item in inactive_raw:
            row = self._normalize_coin(item, active=False)
            by_id[str(row["id"])] = row
        for item in active_raw:
            row = self._normalize_coin(item, active=True)
            by_id[str(row["id"])] = row
        if not by_id:
            raise CoinGeckoUniverseError(
                "CoinGecko returned empty universe",
                context={"active": len(active_raw), "inactive": len(inactive_raw)},
            )
        ordered = tuple(by_id[k] for k in sorted(by_id.keys()))
        table = self._rows_to_table(ordered, availability_time=availability_time)
        instrument_ids = tuple(str(r["id"]) for r in ordered)
        snapshot = _UniverseSnapshot(
            availability_time=availability_time,
            table=table,
            instrument_ids=instrument_ids,
            rows=ordered,
        )
        self._snapshots.append(snapshot)
        self._snapshots.sort(key=lambda s: s.availability_time)
        if self._publisher is not None:
            self._last_published_dataset_id = self._publish_snapshot(snapshot)
        return [dict(r) for r in ordered]

    def universe_at(self, decision_time: datetime) -> list[str]:
        t = _require_utc(decision_time, field="decision_time")
        if self._snapshots:
            local = self._universe_from_snapshots(t)
            if local is None:
                raise CoinGeckoUniverseError(
                    "no universe snapshot available at decision_time",
                    context={
                        "decision_time": t.isoformat(),
                        "dataset_id": COINGECKO_UNIVERSE_DATASET_ID,
                        "local_snapshots": len(self._snapshots),
                    },
                )
            return local
        store_ids = self._universe_from_as_of(t)
        if store_ids is not None:
            return store_ids
        raise CoinGeckoUniverseError(
            "no universe snapshot available at decision_time",
            context={
                "decision_time": t.isoformat(),
                "dataset_id": COINGECKO_UNIVERSE_DATASET_ID,
                "local_snapshots": 0,
            },
        )

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def _universe_from_snapshots(self, decision_time: datetime) -> list[str] | None:
        eligible = [
            s for s in self._snapshots if s.availability_time <= decision_time
        ]
        if not eligible:
            return None
        latest = max(eligible, key=lambda s: (s.availability_time, s.instrument_ids))
        return list(latest.instrument_ids)

    def _universe_from_as_of(self, decision_time: datetime) -> list[str] | None:
        try:
            table = self._as_of_store.latest_available(
                COINGECKO_UNIVERSE_DATASET_ID,
                [],
                ["instrument_id", "active", "availability_time"],
                decision_time,
                None,
            )
        except Exception as exc:
            raise CoinGeckoUniverseError(
                "as-of universe access failed",
                context={
                    "dataset_id": COINGECKO_UNIVERSE_DATASET_ID,
                    "decision_time": decision_time.isoformat(),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            ) from exc
        if not isinstance(table, pa.Table):
            raise CoinGeckoUniverseError(
                "as-of universe returned non-table",
                context={"type": type(table).__name__},
            )
        if "instrument_id" not in table.column_names:
            raise CoinGeckoUniverseError(
                "as-of universe table missing instrument_id",
                context={"columns": list(table.column_names)},
            )
        if table.num_rows == 0:
            return None
        ids: set[str] = set()
        for value in table.column("instrument_id").to_pylist():
            if value is None or str(value) == "":
                raise CoinGeckoUniverseError(
                    "as-of universe row missing instrument_id",
                )
            ids.add(str(value))
        return sorted(ids)

    def _normalize_coin(
        self,
        item: Mapping[str, Any],
        *,
        active: bool,
    ) -> dict[str, str | bool]:
        if not isinstance(item, Mapping):
            raise CoinGeckoUniverseError(
                "CoinGecko coin entry must be an object",
                context={"type": type(item).__name__},
            )
        coin_id = item.get("id")
        symbol = item.get("symbol")
        name = item.get("name")
        if not isinstance(coin_id, str) or not coin_id.strip():
            raise CoinGeckoUniverseError(
                "CoinGecko coin missing id",
                context={"item": dict(item)},
            )
        if not isinstance(symbol, str) or not symbol.strip():
            raise CoinGeckoUniverseError(
                "CoinGecko coin missing symbol",
                context={"id": coin_id},
            )
        if not isinstance(name, str) or not name.strip():
            raise CoinGeckoUniverseError(
                "CoinGecko coin missing name",
                context={"id": coin_id},
            )
        return {
            "id": coin_id.strip(),
            "symbol": symbol.strip(),
            "name": name.strip(),
            "active": bool(active),
        }

    def _rows_to_table(
        self,
        rows: Sequence[Mapping[str, str | bool]],
        *,
        availability_time: datetime,
    ) -> pa.Table:
        avail_us = _dt_to_us(availability_time)
        return pa.table(
            {
                "instrument_id": [str(r["id"]) for r in rows],
                "symbol": [str(r["symbol"]) for r in rows],
                "name": [str(r["name"]) for r in rows],
                "active": [bool(r["active"]) for r in rows],
                "availability_time": [avail_us] * len(rows),
            },
            schema=_UNIVERSE_SCHEMA,
        )

    def _fetch_status(self, status: str) -> list[Any]:
        if status not in {"active", "inactive"}:
            raise CoinGeckoUniverseError(
                "status must be active or inactive",
                context={"status": status},
            )
        self._throttle()
        url = f"{self._base_url}{_COINS_LIST_PATH}"
        params = {
            "include_platform": "false",
            "status": status,
        }
        client = self._get_client()
        try:
            response = client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise CoinGeckoUniverseError(
                "CoinGecko request failed",
                context={"status": status, "url": url, "error": str(exc)},
            ) from exc
        if response.status_code != 200:
            raise CoinGeckoUniverseError(
                "CoinGecko API error",
                context={
                    "status": status,
                    "http_status": response.status_code,
                    "body": response.text[:500],
                },
            )
        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise CoinGeckoUniverseError(
                "CoinGecko response is not JSON",
                context={"status": status},
            ) from exc
        if not isinstance(payload, list):
            raise CoinGeckoUniverseError(
                "CoinGecko coins/list must return a list",
                context={"status": status, "type": type(payload).__name__},
            )
        return payload

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self._timeout_s),
                follow_redirects=True,
            )
        return self._client

    def _throttle(self) -> None:
        now = time.monotonic()
        window = 60.0
        self._request_times = [t for t in self._request_times if now - t < window]
        if len(self._request_times) >= self._max_requests_per_minute:
            sleep_for = window - (now - self._request_times[0])
            if sleep_for > 0:
                time.sleep(sleep_for)
            now = time.monotonic()
            self._request_times = [t for t in self._request_times if now - t < window]
        self._request_times.append(time.monotonic())

    def _publish_snapshot(self, snapshot: _UniverseSnapshot) -> str:
        if self._publisher is None:
            raise CoinGeckoUniverseError("publisher is not configured")
        body = json.dumps(
            [dict(r) for r in snapshot.rows],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        content_sha = hashlib.sha256(body).hexdigest()
        avail_us = _dt_to_us(snapshot.availability_time)
        relative_path = "universe/coingecko_universe.parquet"
        with tempfile.TemporaryDirectory(prefix="coingecko-universe-") as tmp:
            src = Path(tmp) / "coingecko_universe.parquet"
            pq.write_table(snapshot.table, str(src), compression="zstd")
            sha, byte_size = stream_sha256_and_size(src)
            row_count = snapshot.table.num_rows
            plan = PublishPlan(
                dataset_type=COINGECKO_UNIVERSE_DATASET_ID,
                schema=SchemaIdentity(
                    name=_SCHEMA_NAME,
                    version=_SCHEMA_VERSION,
                    fingerprint=hashlib.sha256(
                        str(_UNIVERSE_SCHEMA).encode("utf-8")
                    ).hexdigest(),
                ),
                transform=TransformSpec(
                    name=_TRANSFORM_NAME,
                    version=_TRANSFORM_VERSION,
                ),
                code=CodeIdentity(commit=_CODE_COMMIT),
                config=ConfigIdentity(
                    config_sha256=hashlib.sha256(
                        json.dumps(
                            {
                                "content_sha256": content_sha,
                                "availability_time_us": avail_us,
                                "dataset_id": COINGECKO_UNIVERSE_DATASET_ID,
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ).hexdigest()
                ),
                dependencies=(),
                output_sources={relative_path: src},
                output_specs=[
                    OutputFileSpec(
                        relative_path=relative_path,
                        sha256=sha,
                        rows=row_count,
                        bytes=byte_size,
                        partition={
                            "availability_time_us": avail_us,
                            "logical_dataset_id": COINGECKO_UNIVERSE_DATASET_ID,
                        },
                        rows_verified=True,
                    )
                ],
                statistics=DatasetStatistics(
                    row_count=row_count,
                    byte_size=byte_size,
                ),
                coverage=CoverageWindow(
                    event_start=snapshot.availability_time,
                    event_end=snapshot.availability_time,
                    availability_start=snapshot.availability_time,
                    availability_end=snapshot.availability_time,
                ),
                quality_status=QualityStatus.PASS,
                quality_summary={
                    "source": "coingecko",
                    "endpoint": _COINS_LIST_PATH,
                    "instrument_count": row_count,
                    "logical_dataset_id": COINGECKO_UNIVERSE_DATASET_ID,
                },
                created_at=snapshot.availability_time,
                row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
                row_receipts={
                    relative_path: RowCountReceipt(
                        relative_path=relative_path,
                        row_count=row_count,
                        verifier_name="coingecko_universe_row_count",
                    )
                },
            )
            try:
                result = self._publisher.publish(plan, register_catalog=True)
            except Exception as exc:
                raise CoinGeckoUniverseError(
                    "universe snapshot publication failed",
                    context={
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "logical_dataset_id": COINGECKO_UNIVERSE_DATASET_ID,
                    },
                ) from exc
        return result.dataset_id
