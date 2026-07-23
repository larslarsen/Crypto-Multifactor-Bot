"""HARDEN-001 — Read-Only Venue Probe Adapter.

Provides a read-only venue connectivity probe (ping / status check) satisfying the
VenueAdapter protocol while strictly forbidding order placement or cancellation.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Final

import httpx

from cryptofactors.execution.errors import LiveExecutionError
from cryptofactors.execution.models import LiveOrder, LiveOrderStatus

DEFAULT_PING_URL: Final[str] = "https://api.binance.com/api/v3/ping"
UTC: Final[timezone] = timezone.utc


class ReadOnlyVenueProbeAdapter:
    """Read-only venue connectivity probe that satisfies VenueAdapter protocol for health checks."""

    def __init__(
        self,
        *,
        venue_name: str = "binance_spot_public",
        ping_url: str = DEFAULT_PING_URL,
        timeout_s: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.venue_name: str = venue_name
        self.ping_url: str = ping_url
        self.timeout_s: float = float(timeout_s)
        self._client: httpx.Client | None = client

    def ping_venue(self) -> dict[str, Any]:
        """Perform a read-only HTTP ping to test venue reachability and measure round-trip latency."""
        t_start = time.monotonic()
        try:
            if self._client is not None:
                resp = self._client.get(self.ping_url, timeout=self.timeout_s)
            else:
                with httpx.Client(timeout=self.timeout_s) as c:
                    resp = c.get(self.ping_url)

            latency_ms = round((time.monotonic() - t_start) * 1000.0, 2)
            if resp.status_code == 200:
                return {
                    "status": "PING_OK",
                    "venue": self.venue_name,
                    "endpoint": self.ping_url,
                    "latency_ms": latency_ms,
                    "http_status": 200,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            return {
                "status": "PING_FAILED",
                "venue": self.venue_name,
                "endpoint": self.ping_url,
                "latency_ms": latency_ms,
                "http_status": resp.status_code,
                "error": f"HTTP {resp.status_code}",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.monotonic() - t_start) * 1000.0, 2)
            return {
                "status": "PING_ERROR",
                "venue": self.venue_name,
                "endpoint": self.ping_url,
                "latency_ms": latency_ms,
                "error": str(exc),
                "timestamp": datetime.now(UTC).isoformat(),
            }

    def submit_order(self, order: LiveOrder, credentials: Mapping[str, str]) -> str:
        """Fail closed: read-only probe adapter forbids submitting orders."""
        raise LiveExecutionError(
            "Order submission is disabled in ReadOnlyVenueProbeAdapter (HARDEN-001)",
            context={"order_id": order.order_id, "symbol": order.symbol},
        )

    def cancel_order(self, venue_order_id: str, credentials: Mapping[str, str]) -> bool:
        """Fail closed: read-only probe adapter forbids canceling orders."""
        raise LiveExecutionError(
            "Order cancellation is disabled in ReadOnlyVenueProbeAdapter (HARDEN-001)",
            context={"venue_order_id": venue_order_id},
        )

    def get_order_status(
        self, venue_order_id: str, credentials: Mapping[str, str]
    ) -> LiveOrderStatus:
        """Fail closed: read-only probe adapter does not track live venue orders."""
        raise LiveExecutionError(
            "Order status queries are disabled in ReadOnlyVenueProbeAdapter (HARDEN-001)",
            context={"venue_order_id": venue_order_id},
        )
