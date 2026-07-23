"""DATA-001 — Live Market Data Acquisition: Binance Spot Klines Fetcher.

Downloads historical/recent daily or hourly OHLCV klines from Binance REST API
GET /api/v3/klines (or GET /api/v3/uiKlines), packages them as standard 12-column
Binance CSV inside a zip archive buffer, and writes them through RawObjectWriter
to produce content-addressed RawObjects registered in SqliteRawObjectCatalog.
"""

from __future__ import annotations

import csv
import io
import time
import zipfile
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import httpx

from cryptofactors.contracts import RawObject, SourceObjectRef
from cryptofactors.ingest.raw.models import AcquisitionMetadata
from cryptofactors.ingest.raw.writer import RawObjectWriter

DEFAULT_BINANCE_BASE_URL: Final[str] = "https://api.binance.com"
KLINES_ENDPOINT: Final[str] = "/api/v3/klines"
SOURCE_ID: Final[str] = "binance_spot"


class BinanceFetcherError(RuntimeError):
    """Base error for Binance data acquisition."""

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


def _require_utc(dt: datetime, *, field: str) -> datetime:
    if not isinstance(dt, datetime):
        raise BinanceFetcherError(
            f"{field} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise BinanceFetcherError(
            f"{field} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


def _dt_to_ms(dt: datetime) -> int:
    return int(_require_utc(dt, field="datetime").timestamp() * 1000)


def _ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def klines_to_csv_zip_bytes(
    symbol: str,
    interval: str,
    kline_rows: Sequence[Sequence[Any]],
) -> bytes:
    """Format raw Binance GET /api/v3/klines JSON arrays into 12-column CSV inside a zip buffer."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=",", lineterminator="\n")
    for row in kline_rows:
        if len(row) >= 12:
            writer.writerow([str(x) for x in row[:12]])
        elif len(row) == 11:
            writer.writerow([str(x) for x in row[:11]] + ["0"])

    csv_text = buf.getvalue()
    csv_bytes = csv_text.encode("utf-8")

    zip_buf = io.BytesIO()
    zip_name = f"{symbol.upper()}-{interval}.csv"
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(zip_name, csv_bytes)

    return zip_buf.getvalue()


class BinanceKlineFetcher:
    """Binance REST kline fetcher implementing SourceAdapter protocol and RAW-001 publication."""

    source_id: str = SOURCE_ID

    def __init__(
        self,
        raw_writer: RawObjectWriter,
        *,
        base_url: str = DEFAULT_BINANCE_BASE_URL,
        timeout_s: float = 30.0,
        requests_per_minute: int = 600,
        client: httpx.Client | None = None,
    ) -> None:
        self.raw_writer: RawObjectWriter = raw_writer
        self._base_url: str = base_url.strip().rstrip("/")
        self._timeout_s: float = float(timeout_s)
        self._min_interval_s: float = 60.0 / max(1, requests_per_minute)
        self._last_req_time: float = 0.0
        self._client: httpx.Client | None = client

    def discover(self, request: Mapping[str, Any]) -> list[SourceObjectRef]:
        """Discover source object references for a symbol, interval, and time range."""
        symbol = str(request.get("symbol") or "").strip().upper()
        if not symbol:
            raise BinanceFetcherError("request missing required 'symbol'")

        interval = str(request.get("interval") or "1d").strip()
        start_time = request.get("start_time")
        end_time = request.get("end_time")

        obj_key = f"binance_spot_{symbol}_{interval}"
        req_meta: dict[str, Any] = {
            "symbol": symbol,
            "interval": interval,
            "market_type": "spot",
        }
        if start_time is not None:
            req_meta["start_time"] = _require_utc(start_time, field="start_time").isoformat()
        if end_time is not None:
            req_meta["end_time"] = _require_utc(end_time, field="end_time").isoformat()

        ref = SourceObjectRef(
            source_id=self.source_id,
            object_key=obj_key,
            request=req_meta,
        )
        return [ref]

    def fetch_klines_raw(
        self,
        symbol: str,
        interval: str = "1d",
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[list[Any]]:
        """Fetch raw kline arrays from GET /api/v3/klines with pagination."""
        symbol_clean = symbol.strip().upper()
        url = f"{self._base_url}{KLINES_ENDPOINT}"

        start_ms = _dt_to_ms(start_time) if start_time else None
        end_ms = _dt_to_ms(end_time) if end_time else None

        all_rows: list[list[Any]] = []

        while True:
            params: dict[str, Any] = {
                "symbol": symbol_clean,
                "interval": interval,
                "limit": min(limit, 1000),
            }
            if start_ms is not None:
                params["startTime"] = start_ms
            if end_ms is not None:
                params["endTime"] = end_ms

            data = self._get(url, params)
            if not isinstance(data, list):
                raise BinanceFetcherError(
                    "Binance API returned non-list kline response",
                    context={"response": data},
                )

            if not data:
                break

            all_rows.extend(data)

            if len(data) < limit:
                break

            last_open_ms = int(data[-1][0])
            start_ms = last_open_ms + 1

            if end_ms is not None and start_ms >= end_ms:
                break

        return all_rows

    def fetch_and_write_raw(
        self,
        symbol: str,
        interval: str = "1d",
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> RawObject:
        """Fetch klines from Binance and write through RawObjectWriter to RAW-001 store."""
        st = (
            _require_utc(start_time, field="start_time")
            if start_time
            else datetime(2020, 1, 1, tzinfo=timezone.utc)
        )
        et = _require_utc(end_time, field="end_time") if end_time else datetime.now(timezone.utc)

        raw_rows = self.fetch_klines_raw(symbol, interval, start_time=st, end_time=et)
        if not raw_rows:
            raise BinanceFetcherError(
                f"No klines returned for {symbol} {interval}",
                context={"symbol": symbol},
            )

        zip_bytes = klines_to_csv_zip_bytes(symbol, interval, raw_rows)

        acq_time = datetime.now(timezone.utc)
        acq_meta = AcquisitionMetadata(
            source_id=self.source_id,
            acquisition_id=f"acq_binance_{symbol}_{interval}_{int(acq_time.timestamp())}",
            request={
                "symbol": symbol,
                "interval": interval,
                "market_type": "spot",
                "start_time": st.isoformat(),
                "end_time": et.isoformat(),
            },
            acquired_at=acq_time,
            event_start=_ms_to_dt(int(raw_rows[0][0])),
            event_end=_ms_to_dt(int(raw_rows[-1][6])),
            original_name=f"{symbol.upper()}-{interval}.zip",
        )

        pub_res = self.raw_writer.write_stream(
            source=[zip_bytes],
            metadata=acq_meta,
            register_catalog=True,
        )

        return RawObject(
            raw_object_id=pub_res.raw_object_id,
            source_id=self.source_id,
            sha256=pub_res.sha256,
            bytes=pub_res.byte_size,
            storage_path=pub_res.storage_path,
            acquired_at=acq_time,
        )

    def fetch(self, ref: SourceObjectRef, destination: Path | None = None) -> RawObject:
        """Satisfy SourceAdapter protocol fetch method."""
        symbol = str(ref.request.get("symbol", "BTCUSDT"))
        interval = str(ref.request.get("interval", "1d"))

        st_raw = ref.request.get("start_time")
        et_raw = ref.request.get("end_time")

        st = datetime.fromisoformat(str(st_raw)) if st_raw else None
        et = datetime.fromisoformat(str(et_raw)) if et_raw else None

        return self.fetch_and_write_raw(symbol, interval, start_time=st, end_time=et)

    def _get(self, url: str, params: dict[str, Any]) -> Any:
        self._throttle()
        if self._client:
            res = self._client.get(url, params=params)
        else:
            with httpx.Client(timeout=self._timeout_s) as c:
                res = c.get(url, params=params)

        if res.status_code != 200:
            raise BinanceFetcherError(
                f"Binance GET {url} failed with HTTP {res.status_code}",
                context={"status_code": res.status_code, "body": res.text[:500]},
            )
        return res.json()

    def _throttle(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_req_time
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_req_time = time.monotonic()
