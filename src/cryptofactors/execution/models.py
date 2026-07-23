"""Data models for execution runtime (EXEC-001, EXEC-002)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _require_utc(dt: datetime, *, field_name: str) -> datetime:
    if not isinstance(dt, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if dt.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class PaperOrder:
    """An execution order submitted to the paper broker."""

    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: float
    target_weight: float | None = None

    def __post_init__(self) -> None:
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValueError("symbol must be a non-empty string")
        side_upper = self.side.upper().strip()
        if side_upper not in ("BUY", "SELL"):
            raise ValueError(f"side must be 'BUY' or 'SELL', got {self.side!r}")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got {self.quantity}")


@dataclass(frozen=True, slots=True)
class PaperTrade:
    """An executed simulated trade record with applied costs."""

    trade_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: float
    base_price: float
    effective_price: float
    fee: float
    notional: float
    timestamp: datetime

    def __post_init__(self) -> None:
        _require_utc(self.timestamp, field_name="timestamp")


@dataclass(frozen=True, slots=True)
class PaperAccountState:
    """Snapshotted paper account state."""

    cash: float
    positions: dict[str, float] = field(default_factory=dict)
    equity: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _require_utc(self.timestamp, field_name="timestamp")


class LiveOrderState(str, Enum):
    """State of a live order tracked by the LiveBroker."""

    NEW = "NEW"
    SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class LiveOrder:
    """An order submitted to the live broker for venue routing."""

    order_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: float
    target_weight: float | None = None

    def __post_init__(self) -> None:
        if not self.order_id or not isinstance(self.order_id, str):
            raise ValueError("order_id must be a non-empty string")
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValueError("symbol must be a non-empty string")
        side_upper = self.side.upper().strip()
        if side_upper not in ("BUY", "SELL"):
            raise ValueError(f"side must be 'BUY' or 'SELL', got {self.side!r}")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got {self.quantity}")


@dataclass(frozen=True, slots=True)
class LiveOrderStatus:
    """Snapshot of a live order's state at the venue."""

    order_id: str
    venue_order_id: str | None
    state: LiveOrderState
    filled_quantity: float
    avg_fill_price: float | None
    timestamp: datetime

    def __post_init__(self) -> None:
        _require_utc(self.timestamp, field_name="timestamp")


@dataclass(frozen=True, slots=True)
class FlattenSignal:
    """Kill-switch signal instructing clients to flatten all open orders / positions."""

    reason: str
    timestamp: datetime
    open_orders: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_utc(self.timestamp, field_name="timestamp")


@dataclass(frozen=True, slots=True)
class PaperOpsStatus:
    """Health/status report artifact for a PAPER_APPROVED model session (PAPER-003)."""

    model_artifact_id: str
    promotion_state: str
    gate_status: str  # "OK" or "FAIL"
    last_rebalance_time: datetime | None
    last_equity: float
    initial_cash: float
    total_net_return: float
    peak_equity: float
    current_drawdown: float
    open_positions_count: int
    total_trades_count: int
    paper_observation_reference: str | None
    drawdown_alert_triggered: bool
    report_generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _require_utc(self.report_generated_at, field_name="report_generated_at")
        if self.last_rebalance_time is not None:
            _require_utc(self.last_rebalance_time, field_name="last_rebalance_time")
