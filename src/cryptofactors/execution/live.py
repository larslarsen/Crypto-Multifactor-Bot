"""EXEC-002 — Live Execution Routing (Sequence #26).

Live order-routing broker permitted to contact real exchange venues ONLY for
artifacts in ``LIVE_APPROVED`` state. Strictly separated from ``PaperBroker``:
no shared mutable state, no dual-mode flag, no inheritance of paper fills.

Hard constraints (from AUD-006):
1. Every order path verifies ``LIVE_APPROVED`` via PromotionRegistry and fails closed.
2. Pre-trade risk checks (gross leverage <= 1.0, single-asset abs weight <= 0.15)
   run BEFORE any network call.
3. Credentials read from environment only; never logged, embedded, or committed.
4. Kill-switch: refuses new orders and surfaces a flatten signal on registry
   failure or explicit activation.
5. Never writes promotion events (read-only access to PromotionRegistry).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Final, Protocol, runtime_checkable

from cryptofactors.execution.errors import (
    KillSwitchActiveError,
    LiveExecutionError,
    RiskLimitViolationError,
    UnapprovedArtifactError,
)
from cryptofactors.execution.models import (
    FlattenSignal,
    LiveOrder,
    LiveOrderState,
    LiveOrderStatus,
)
from cryptofactors.promotion import (
    PromotionError,
    PromotionRegistry,
    PromotionTarget,
)

MAX_GROSS_LEVERAGE: Final[float] = 1.0
MAX_SINGLE_ASSET_WEIGHT: Final[float] = 0.15
_LEVERAGE_TOLERANCE: Final[float] = 1e-6
_US_PER_SECOND: Final[int] = 1_000_000


def _require_utc(dt: datetime, *, field_name: str) -> datetime:
    if not isinstance(dt, datetime):
        raise LiveExecutionError(
            f"{field_name} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise LiveExecutionError(
            f"{field_name} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


@runtime_checkable
class VenueAdapter(Protocol):
    """Pluggable venue REST surface for live order routing."""

    def submit_order(self, order: LiveOrder, credentials: Mapping[str, str]) -> str:
        """Submit order to venue; return venue-assigned order id."""
        ...

    def cancel_order(self, venue_order_id: str, credentials: Mapping[str, str]) -> bool:
        """Cancel an order at the venue; return True if cancellation accepted."""
        ...

    def get_order_status(
        self, venue_order_id: str, credentials: Mapping[str, str]
    ) -> LiveOrderStatus:
        """Query current order state at the venue."""
        ...


class PreTradeRiskValidator:
    """Validates target weights against AUD-006 risk limits pre-trade."""

    def __init__(
        self,
        *,
        max_gross_leverage: float = MAX_GROSS_LEVERAGE,
        max_single_asset_weight: float = MAX_SINGLE_ASSET_WEIGHT,
    ) -> None:
        if max_gross_leverage <= 0:
            raise LiveExecutionError("max_gross_leverage must be positive")
        if max_single_asset_weight <= 0:
            raise LiveExecutionError("max_single_asset_weight must be positive")
        self._max_gross_leverage: float = float(max_gross_leverage)
        self._max_single_asset_weight: float = float(max_single_asset_weight)

    def validate(self, target_weights: Mapping[str, float]) -> None:
        if not target_weights:
            raise RiskLimitViolationError("target_weights must be non-empty")

        gross = sum(abs(float(w)) for w in target_weights.values())
        if gross > self._max_gross_leverage + _LEVERAGE_TOLERANCE:
            raise RiskLimitViolationError(
                f"Gross leverage {gross:.4f} exceeds limit {self._max_gross_leverage:.4f}",
                context={"gross_leverage": gross, "limit": self._max_gross_leverage},
            )

        for symbol, weight in target_weights.items():
            abs_w = abs(float(weight))
            if abs_w > self._max_single_asset_weight + _LEVERAGE_TOLERANCE:
                raise RiskLimitViolationError(
                    f"Single-asset weight for '{symbol}' ({abs_w:.4f}) exceeds limit "
                    f"{self._max_single_asset_weight:.4f}",
                    context={
                        "symbol": symbol,
                        "weight": abs_w,
                        "limit": self._max_single_asset_weight,
                    },
                )


def load_credentials_from_env(prefix: str = "BINANCE") -> dict[str, str]:
    """Load API credentials from environment variables (never logged).

    Reads ``<PREFIX>_API_KEY`` and ``<PREFIX>_API_SECRET`` from the process
    environment. Returns a dict suitable for passing to a VenueAdapter. Values
    are never stored on the broker object in a loggable form.
    """
    creds: dict[str, str] = {}
    key = f"{prefix}_API_KEY"
    secret = f"{prefix}_API_SECRET"
    api_key = os.environ.get(key, "")
    api_secret = os.environ.get(secret, "")
    if not api_key or not api_secret:
        raise LiveExecutionError(
            f"Missing live credentials in environment: {key} / {secret}",
            context={"prefix": prefix},
        )
    creds["api_key"] = api_key
    creds["api_secret"] = api_secret
    return creds


class LiveBroker:
    """Live order-routing broker with strict LIVE_APPROVED gating and pre-trade risk checks.

    This broker is fully isolated from ``PaperBroker``: it holds no paper state,
    inherits no paper fills, and accepts no ``paper_or_live`` flag. It may only
    route orders for artifacts verified as ``LIVE_APPROVED`` by the
    PromotionRegistry, and only after pre-trade risk validation.
    """

    def __init__(
        self,
        model_artifact_id: str,
        promotion_registry: PromotionRegistry,
        venue: VenueAdapter,
        *,
        risk_validator: PreTradeRiskValidator | None = None,
        credentials: Mapping[str, str] | None = None,
        credential_prefix: str = "BINANCE",
        load_credentials: bool = True,
    ) -> None:
        if not model_artifact_id or not isinstance(model_artifact_id, str):
            raise LiveExecutionError("model_artifact_id must be a non-empty string")
        if promotion_registry is None:
            raise LiveExecutionError("promotion_registry must not be None")
        if venue is None:
            raise LiveExecutionError("venue adapter must not be None")

        self.model_artifact_id: str = model_artifact_id.strip()
        self._promotion_registry: PromotionRegistry = promotion_registry
        self._venue: VenueAdapter = venue
        self._risk_validator: PreTradeRiskValidator = (
            risk_validator or PreTradeRiskValidator()
        )

        self._credentials: dict[str, str] = {}
        if credentials is not None:
            self._credentials = {str(k): str(v) for k, v in credentials.items()}
        elif load_credentials:
            self._credentials = load_credentials_from_env(credential_prefix)

        self._open_orders: dict[str, str] = {}
        self._killed: bool = False

        self.verify_promotion_gate()

    def verify_promotion_gate(self) -> None:
        """Verify model_artifact_id is LIVE_APPROVED; fail closed on any error."""
        if self._killed:
            raise KillSwitchActiveError(
                "Kill-switch active; promotion gate cannot be verified",
                context={"model_artifact_id": self.model_artifact_id},
            )
        try:
            event = self._promotion_registry.get_active_promoted_artifact(
                self.model_artifact_id, PromotionTarget.LIVE
            )
        except PromotionError as exc:
            raise UnapprovedArtifactError(
                f"Model artifact '{self.model_artifact_id}' failed live promotion gate: {exc}",
                context={"model_artifact_id": self.model_artifact_id, "error": str(exc)},
            ) from exc

        if event.promotion_state.value != "LIVE_APPROVED":
            raise UnapprovedArtifactError(
                f"Model artifact '{self.model_artifact_id}' is not in LIVE_APPROVED state",
                context={
                    "model_artifact_id": self.model_artifact_id,
                    "current_state": event.promotion_state.value,
                },
            )

    def submit_order(
        self,
        order: LiveOrder,
        target_weights: Mapping[str, float],
    ) -> LiveOrderStatus:
        """Submit a single order to the venue after gate + risk checks.

        Order of operations (network call only at the end):
        1. Kill-switch check.
        2. Promotion gate verification (LIVE_APPROVED).
        3. Pre-trade risk validation (leverage + single-asset caps).
        4. Venue submit_order HTTP call.
        """
        if self._killed:
            raise KillSwitchActiveError(
                "Kill-switch active; new orders refused",
                context={"model_artifact_id": self.model_artifact_id},
            )

        self.verify_promotion_gate()
        self._risk_validator.validate(target_weights)

        venue_order_id = self._venue.submit_order(order, self._credentials)
        self._open_orders[order.order_id] = venue_order_id

        return LiveOrderStatus(
            order_id=order.order_id,
            venue_order_id=venue_order_id,
            state=LiveOrderState.SUBMITTED,
            filled_quantity=0.0,
            avg_fill_price=None,
            timestamp=datetime.now(timezone.utc),
        )

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order at the venue."""
        if self._killed:
            raise KillSwitchActiveError(
                "Kill-switch active; cancel refused",
                context={"order_id": order_id},
            )
        venue_order_id = self._open_orders.get(order_id)
        if venue_order_id is None:
            raise LiveExecutionError(
                f"Unknown order_id '{order_id}'; cannot cancel",
                context={"order_id": order_id, "known_orders": list(self._open_orders.keys())},
            )
        return self._venue.cancel_order(venue_order_id, self._credentials)

    def get_order_status(self, order_id: str) -> LiveOrderStatus:
        """Query current status of a previously submitted order at the venue."""
        venue_order_id = self._open_orders.get(order_id)
        if venue_order_id is None:
            raise LiveExecutionError(
                f"Unknown order_id '{order_id}'; cannot query status",
                context={"order_id": order_id, "known_orders": list(self._open_orders.keys())},
            )
        status = self._venue.get_order_status(venue_order_id, self._credentials)
        if status.state in (LiveOrderState.FILLED, LiveOrderState.CANCELED, LiveOrderState.REJECTED):
            self._open_orders.pop(order_id, None)
        return status

    def activate_kill_switch(self, reason: str = "Manual kill-switch activation") -> FlattenSignal:
        """Activate kill-switch: refuse new orders and surface a flatten signal.

        The returned ``FlattenSignal`` carries the reason and any open order ids
        that the caller should attempt to flatten/cancel at the venue.
        """
        self._killed = True
        open_order_ids = dict(self._open_orders)
        return FlattenSignal(
            reason=reason,
            timestamp=datetime.now(timezone.utc),
            open_orders=open_order_ids,
        )

    def is_kill_switch_active(self) -> bool:
        """Return True if the kill-switch is currently active."""
        return self._killed

    def check_registry_and_kill_if_revoked(self) -> bool:
        """Re-query the registry; if LIVE_APPROVED no longer holds, auto-activate kill-switch.

        Returns True if the kill-switch was activated by this call (state revoked),
        False if the artifact remains LIVE_APPROVED. Fail closed: a registry query
        error activates the kill-switch.
        """
        try:
            self._promotion_registry.get_active_promoted_artifact(
                self.model_artifact_id, PromotionTarget.LIVE
            )
            return False
        except PromotionError:
            if not self._killed:
                self.activate_kill_switch(reason="Registry revoked LIVE_APPROVED or query failed")
            return True


def new_live_order(
    symbol: str,
    side: str,
    quantity: float,
    target_weight: float | None = None,
) -> LiveOrder:
    """Construct a new ``LiveOrder`` with a generated order id."""
    order_id = f"lo_{uuid.uuid4().hex[:12]}"
    return LiveOrder(
        order_id=order_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        target_weight=target_weight,
    )