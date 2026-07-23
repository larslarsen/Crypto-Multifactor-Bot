"""EXEC-001 — Paper Execution Runtime broker and position manager.

Simulates stateful forward-walking paper trading with costed order fills,
position tracking, and strict promotion gate enforcement.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Final

from cryptofactors.execution.errors import (
    PaperExecutionError,
    UnapprovedArtifactError,
)
from cryptofactors.execution.models import (
    PaperAccountState,
    PaperTrade,
)
from cryptofactors.promotion import (
    PromotionError,
    PromotionRegistry,
    PromotionTarget,
)

_US_PER_SECOND: Final[int] = 1_000_000


def _require_utc(dt: datetime, *, field_name: str) -> datetime:
    if not isinstance(dt, datetime):
        raise PaperExecutionError(
            f"{field_name} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise PaperExecutionError(
            f"{field_name} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


class PaperBroker:
    """Stateful paper execution broker with strict promotion gate enforcement."""

    def __init__(
        self,
        model_artifact_id: str,
        promotion_registry: PromotionRegistry,
        *,
        initial_cash: float = 100_000.0,
        fee_rate: float = 0.0005,
        slippage_rate: float = 0.0005,
        strict_promotion_gate: bool = True,
    ) -> None:
        if not model_artifact_id or not isinstance(model_artifact_id, str):
            raise PaperExecutionError("model_artifact_id must be a non-empty string")
        if initial_cash <= 0:
            raise PaperExecutionError("initial_cash must be positive")
        if fee_rate < 0 or slippage_rate < 0:
            raise PaperExecutionError("fee_rate and slippage_rate must be non-negative")

        self.model_artifact_id: str = model_artifact_id.strip()
        self._promotion_registry: PromotionRegistry = promotion_registry
        self._cash: float = float(initial_cash)
        self._fee_rate: float = float(fee_rate)
        self._slippage_rate: float = float(slippage_rate)
        self._strict_promotion_gate: bool = strict_promotion_gate
        self._positions: dict[str, float] = {}
        self._trades: list[PaperTrade] = []

        if self._strict_promotion_gate:
            self.verify_promotion_gate()

    def verify_promotion_gate(self) -> None:
        """Verify that the model_artifact_id is in PAPER_APPROVED state in PromotionRegistry."""
        try:
            event = self._promotion_registry.get_active_promoted_artifact(
                self.model_artifact_id, PromotionTarget.PAPER
            )
            if not event or event.promotion_state.value != "PAPER_APPROVED":
                raise UnapprovedArtifactError(
                    f"Model artifact '{self.model_artifact_id}' is not in PAPER_APPROVED state",
                    context={
                        "model_artifact_id": self.model_artifact_id,
                        "current_state": event.promotion_state.value if event else "None",
                    },
                )
        except PromotionError as exc:
            raise UnapprovedArtifactError(
                f"Model artifact '{self.model_artifact_id}' failed paper promotion gate: {exc}",
                context={"model_artifact_id": self.model_artifact_id, "error": str(exc)},
            ) from exc

    def restore_from_state(self, state: PaperAccountState) -> None:
        """Restore broker cash balance and open positions from a PaperAccountState snapshot."""
        self._cash = float(state.cash)
        self._positions = {k: float(v) for k, v in state.positions.items()}

    def restore_from_store(self, store: Any, model_artifact_id: str | None = None) -> bool:
        """Load latest snapshot and trades from a PaperSessionStore and restore broker state.

        Returns True if a prior snapshot was loaded and applied, False if no snapshot was found.
        """
        art_id = model_artifact_id or self.model_artifact_id
        snapshot = store.load_latest_snapshot(art_id)
        if snapshot is None:
            return False

        self.restore_from_state(snapshot)
        trades = store.load_trade_history(art_id)
        if trades:
            self._trades = list(trades)
        return True

    def get_cash(self) -> float:
        """Return current unallocated cash balance."""
        return self._cash

    def get_positions(self) -> dict[str, float]:
        """Return current open position quantities by symbol."""
        return {k: v for k, v in self._positions.items() if abs(v) > 1e-12}

    def get_trade_history(self) -> list[PaperTrade]:
        """Return full list of executed paper trades."""
        return list(self._trades)

    def get_equity(self, current_prices: Mapping[str, float]) -> float:
        """Calculate total paper account portfolio equity (cash + mark-to-market positions)."""
        equity = self._cash
        for symbol, qty in self._positions.items():
            if abs(qty) < 1e-12:
                continue
            if symbol not in current_prices:
                raise PaperExecutionError(
                    f"Missing current price for position asset '{symbol}'",
                    context={"symbol": symbol, "available_prices": list(current_prices.keys())},
                )
            price = float(current_prices[symbol])
            if price <= 0:
                raise PaperExecutionError(f"Invalid non-positive price for '{symbol}': {price}")
            equity += qty * price
        return equity

    def rebalance(
        self,
        target_weights: Mapping[str, float],
        current_prices: Mapping[str, float],
        timestamp: datetime,
    ) -> list[PaperTrade]:
        """Rebalance portfolio to target weights at given prices and timestamp."""
        if self._strict_promotion_gate:
            self.verify_promotion_gate()

        dt = _require_utc(timestamp, field_name="timestamp")
        equity = self.get_equity(current_prices)

        tot_weight = sum(abs(float(w)) for w in target_weights.values())
        if tot_weight > 1.0001:
            raise PaperExecutionError(
                f"Total target leverage {tot_weight:.4f} exceeds 1.0 limit",
                context={"target_weights": dict(target_weights)},
            )

        executed_trades: list[PaperTrade] = []
        all_symbols = sorted(set(target_weights.keys()) | set(self._positions.keys()))

        for symbol in all_symbols:
            target_weight = float(target_weights.get(symbol, 0.0))
            if symbol not in current_prices:
                if abs(target_weight) > 1e-12 or abs(self._positions.get(symbol, 0.0)) > 1e-12:
                    raise PaperExecutionError(
                        f"Missing price for symbol '{symbol}'",
                        context={"symbol": symbol},
                    )
                continue

            price = float(current_prices[symbol])
            if price <= 0:
                raise PaperExecutionError(f"Invalid non-positive price for '{symbol}': {price}")

            current_qty = self._positions.get(symbol, 0.0)
            target_value = equity * target_weight
            target_qty = target_value / price

            delta_qty = target_qty - current_qty

            if abs(delta_qty) < 1e-9:
                continue

            side = "BUY" if delta_qty > 0 else "SELL"
            trade_qty = abs(delta_qty)

            trade = self._execute_fill(
                symbol=symbol,
                side=side,
                quantity=trade_qty,
                base_price=price,
                timestamp=dt,
            )
            executed_trades.append(trade)

        return executed_trades

    def _execute_fill(
        self,
        symbol: str,
        side: str,
        quantity: float,
        base_price: float,
        timestamp: datetime,
    ) -> PaperTrade:
        """Execute simulated order fill with fee and slippage costs."""
        if side == "BUY":
            effective_price = base_price * (1.0 + self._slippage_rate)
            notional = quantity * effective_price
            fee = notional * self._fee_rate
            total_cost = notional + fee

            if total_cost > self._cash + 1e-6:
                max_notional = self._cash / (1.0 + self._fee_rate)
                if max_notional <= 0:
                    raise PaperExecutionError(
                        "Insufficient cash balance for BUY fill",
                        context={"cash": self._cash, "required": total_cost, "symbol": symbol},
                    )
                quantity = max_notional / effective_price
                notional = quantity * effective_price
                fee = notional * self._fee_rate
                total_cost = notional + fee

            self._cash -= total_cost
            self._positions[symbol] = self._positions.get(symbol, 0.0) + quantity

        elif side == "SELL":
            effective_price = base_price * (1.0 - self._slippage_rate)
            notional = quantity * effective_price
            fee = notional * self._fee_rate
            net_proceeds = notional - fee

            self._cash += net_proceeds
            curr_pos = self._positions.get(symbol, 0.0)
            new_pos = curr_pos - quantity
            if abs(new_pos) < 1e-12:
                self._positions.pop(symbol, None)
            else:
                self._positions[symbol] = new_pos
        else:
            raise PaperExecutionError(f"Invalid side: {side}")

        trade_id = f"trade_{uuid.uuid4().hex[:12]}"
        trade = PaperTrade(
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            base_price=base_price,
            effective_price=effective_price,
            fee=fee,
            notional=notional,
            timestamp=timestamp,
        )
        self._trades.append(trade)
        return trade

    def get_account_state(
        self,
        current_prices: Mapping[str, float],
        timestamp: datetime,
    ) -> PaperAccountState:
        """Return a snapshot of current paper account state."""
        dt = _require_utc(timestamp, field_name="timestamp")
        equity = self.get_equity(current_prices)
        return PaperAccountState(
            cash=self._cash,
            positions=self.get_positions(),
            equity=equity,
            timestamp=dt,
        )
