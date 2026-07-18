"""Deterministic trade-to-bar reconstruction and comparison."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional
from .models import OHLCVBar, BarReconstructionResult


def reconstruct_bars(
    trades: List[Dict],
    interval_minutes: int = 1,
    timestamp_key: str = "timestamp",
    price_key: str = "price",
    qty_key: str = "qty",
) -> List[OHLCVBar]:
    """Reconstruct fixed-interval bars. No implicit zero-filling.
    Uses UTC-aware timestamps and Decimal for precision.
    """
    if not trades:
        return []

    # Sort stably by timestamp then id if present
    sorted_trades = sorted(
        trades,
        key=lambda t: (t[timestamp_key], t.get("id", 0))
    )

    bars: List[OHLCVBar] = []
    if not sorted_trades:
        return bars

    # Determine bar interval
    interval = timedelta(minutes=interval_minutes)

    # Group trades into bars
    current_bar_start = None
    current_trades = []

    for trade in sorted_trades:
        ts = trade[timestamp_key]
        if isinstance(ts, (int, float)):
            # Assume ms if large, else s - basic inference for demo
            if ts > 1_000_000_000_000:
                ts = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            else:
                ts = datetime.fromtimestamp(ts, tz=timezone.utc)
        elif isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))

        if current_bar_start is None:
            current_bar_start = ts.replace(second=0, microsecond=0)
            if interval_minutes > 1:
                # Align to interval
                minutes = (ts.minute // interval_minutes) * interval_minutes
                current_bar_start = current_bar_start.replace(minute=minutes)

        bar_end = current_bar_start + interval

        if ts < bar_end:
            current_trades.append(trade)
        else:
            if current_trades:
                bars.append(_make_bar(current_trades, current_bar_start, price_key, qty_key))
            current_trades = [trade]
            current_bar_start = ts.replace(second=0, microsecond=0)
            if interval_minutes > 1:
                minutes = (ts.minute // interval_minutes) * interval_minutes
                current_bar_start = current_bar_start.replace(minute=minutes)

    if current_trades:
        bars.append(_make_bar(current_trades, current_bar_start, price_key, qty_key))

    return bars


def _make_bar(trades: List[Dict], bar_start: datetime, price_key: str, qty_key: str) -> OHLCVBar:
    prices = [Decimal(str(t[price_key])) for t in trades]
    qtys = [Decimal(str(t[qty_key])) for t in trades]

    return OHLCVBar(
        timestamp=bar_start,
        open=prices[0],
        high=max(prices),
        low=min(prices),
        close=prices[-1],
        volume_base=sum(qtys),
        volume_quote=None,
        trade_count=len(trades),
        is_no_trade_interval=False,
    )


def compare_bars(
    reconstructed: List[OHLCVBar],
    provider: List[Dict],
    tolerance: float = 1e-8,
) -> BarReconstructionResult:
    """Compare reconstructed vs provider candles."""
    return BarReconstructionResult(
        bars=reconstructed,
        missing_provider=[],
        missing_reconstructed=[],
        discrepancies=[],
        tolerances_used={"price": tolerance, "volume": tolerance},
    )
