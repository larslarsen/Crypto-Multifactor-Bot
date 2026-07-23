"""Data models for paper execution runtime (EXEC-001)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


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
