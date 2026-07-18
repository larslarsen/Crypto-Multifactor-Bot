"""Focused tests for trade-to-bar reconstruction and provider comparison."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from source_audit.bars import compare_bars, normalize_trade, reconstruct_bars
from source_audit.errors import BarReconstructionError, InvalidNumericError
from source_audit.models import IntervalClosure, OHLCVBar, Trade

UTC = timezone.utc
ORIGIN = datetime(2025, 1, 1, tzinfo=UTC)


def _t(
    minute: int,
    second: int,
    price: str,
    qty: str,
    trade_id: str,
    *,
    hour: int = 0,
) -> Trade:
    return Trade(
        timestamp_utc=datetime(2025, 1, 1, hour, minute, second, tzinfo=UTC),
        price=Decimal(price),
        quantity=Decimal(qty),
        trade_id=trade_id,
    )


def test_empty_trades() -> None:
    result = reconstruct_bars(
        [],
        interval_duration=timedelta(minutes=1),
        alignment_origin_utc=ORIGIN,
    )
    assert result.bars == ()
    assert result.input_trade_count == 0


def test_deterministic_ohlcv_and_order_independence() -> None:
    trades = [
        _t(0, 10, "100", "1", "a"),
        _t(0, 20, "110", "2", "b"),
        _t(0, 30, "90", "1.5", "c"),
        _t(1, 5, "95", "3", "d"),
    ]
    interval = timedelta(minutes=1)
    r1 = reconstruct_bars(trades, interval_duration=interval, alignment_origin_utc=ORIGIN)
    r2 = reconstruct_bars(
        list(reversed(trades)),
        interval_duration=interval,
        alignment_origin_utc=ORIGIN,
    )
    assert r1.bars == r2.bars
    assert len(r1.bars) == 2
    b0 = r1.bars[0]
    assert b0.open == Decimal("100")
    assert b0.high == Decimal("110")
    assert b0.low == Decimal("90")
    assert b0.close == Decimal("90")
    assert b0.volume_base == Decimal("4.5")
    assert b0.trade_count == 3
    # No zero-filled gap bars between minute 0 and 1 — only intervals with trades.
    assert r1.bars[1].trade_count == 1


def test_identical_timestamp_tiebreak_by_trade_id() -> None:
    ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    trades = [
        Trade(timestamp_utc=ts, price=Decimal("2"), quantity=Decimal("1"), trade_id="b"),
        Trade(timestamp_utc=ts, price=Decimal("1"), quantity=Decimal("1"), trade_id="a"),
    ]
    result = reconstruct_bars(
        trades,
        interval_duration=timedelta(minutes=1),
        alignment_origin_utc=ORIGIN,
    )
    assert result.bars[0].open == Decimal("1")  # trade_id "a" first
    assert result.bars[0].close == Decimal("2")


def test_duplicate_trade_id_reported_and_excluded() -> None:
    trades = [
        _t(0, 1, "10", "1", "same"),
        _t(0, 2, "12", "1", "same"),
        _t(0, 3, "11", "1", "other"),
    ]
    result = reconstruct_bars(
        trades,
        interval_duration=timedelta(minutes=1),
        alignment_origin_utc=ORIGIN,
    )
    assert result.input_trade_count == 3
    assert result.unique_trade_count == 2
    assert result.duplicate_trades[0].trade_id == "same"
    assert result.duplicate_trades[0].occurrences == 2
    assert result.bars[0].trade_count == 2


def test_reject_naive_timestamp() -> None:
    with pytest.raises(BarReconstructionError, match="timezone-aware"):
        reconstruct_bars(
            [
                Trade(
                    timestamp_utc=datetime(2025, 1, 1, 0, 0, 0),  # type: ignore[arg-type]
                    price=Decimal("1"),
                    quantity=Decimal("1"),
                    trade_id="x",
                )
            ],
            interval_duration=timedelta(minutes=1),
            alignment_origin_utc=ORIGIN,
        )


def test_reject_float_price() -> None:
    with pytest.raises(InvalidNumericError):
        normalize_trade(
            {
                "timestamp_utc": datetime(2025, 1, 1, tzinfo=UTC),
                "price": 1.5,
                "quantity": "1",
                "trade_id": "x",
            }
        )


def test_no_implicit_zero_bars() -> None:
    trades = [_t(0, 1, "1", "1", "a"), _t(5, 1, "2", "1", "b")]
    result = reconstruct_bars(
        trades,
        interval_duration=timedelta(minutes=1),
        alignment_origin_utc=ORIGIN,
    )
    assert len(result.bars) == 2
    starts = [b.interval_start_utc.minute for b in result.bars]
    assert starts == [0, 5]


def test_compare_bars_mismatches_and_missing() -> None:
    interval = timedelta(minutes=1)
    recon = reconstruct_bars(
        [_t(0, 1, "100", "1", "a"), _t(0, 2, "110", "1", "b")],
        interval_duration=interval,
        alignment_origin_utc=ORIGIN,
    )
    provider = [
        OHLCVBar(
            interval_start_utc=ORIGIN,
            interval_end_utc=ORIGIN + interval,
            open=Decimal("100"),
            high=Decimal("110"),
            low=Decimal("100"),
            close=Decimal("110"),
            volume_base=Decimal("2"),
            volume_quote=Decimal("210"),
            trade_count=2,
        ),
        OHLCVBar(
            interval_start_utc=ORIGIN + interval,
            interval_end_utc=ORIGIN + 2 * interval,
            open=Decimal("1"),
            high=Decimal("1"),
            low=Decimal("1"),
            close=Decimal("1"),
            volume_base=Decimal("1"),
            volume_quote=Decimal("1"),
            trade_count=1,
        ),
    ]
    # Mutate provider open to force mismatch.
    provider[0] = OHLCVBar(
        interval_start_utc=ORIGIN,
        interval_end_utc=ORIGIN + interval,
        open=Decimal("99"),
        high=Decimal("110"),
        low=Decimal("100"),
        close=Decimal("110"),
        volume_base=Decimal("2"),
        volume_quote=Decimal("210"),
        trade_count=2,
    )
    cmp = compare_bars(
        recon.bars,
        provider,
        price_tolerance=Decimal("0"),
        volume_tolerance=Decimal("0"),
    )
    assert cmp.missing_from_provider == ()
    assert len(cmp.missing_from_reconstructed) == 1
    assert any(m.field_name == "open" for m in cmp.ohlc_mismatches)
    assert cmp.ohlc_mismatches[0].expected == "99"
    assert cmp.ohlc_mismatches[0].observed == "100"


def test_compare_duplicate_provider_intervals() -> None:
    interval = timedelta(minutes=1)
    bar = OHLCVBar(
        interval_start_utc=ORIGIN,
        interval_end_utc=ORIGIN + interval,
        open=Decimal("1"),
        high=Decimal("1"),
        low=Decimal("1"),
        close=Decimal("1"),
        volume_base=Decimal("1"),
        volume_quote=Decimal("1"),
        trade_count=1,
    )
    cmp = compare_bars(
        [bar],
        [bar, bar],
        price_tolerance=Decimal("0"),
        volume_tolerance=Decimal("0"),
    )
    assert cmp.duplicate_provider_intervals == (ORIGIN,)


def test_left_open_right_closed_closure() -> None:
    # Trade exactly on boundary belongs to previous interval under left-open/right-closed.
    boundary = ORIGIN + timedelta(minutes=1)
    trades = [
        Trade(
            timestamp_utc=boundary,
            price=Decimal("5"),
            quantity=Decimal("1"),
            trade_id="edge",
        )
    ]
    result = reconstruct_bars(
        trades,
        interval_duration=timedelta(minutes=1),
        alignment_origin_utc=ORIGIN,
        closure=IntervalClosure.LEFT_OPEN_RIGHT_CLOSED,
    )
    assert len(result.bars) == 1
    assert result.bars[0].interval_start_utc == ORIGIN


def test_direct_trade_rejects_non_positive_price() -> None:
    with pytest.raises(InvalidNumericError, match="price"):
        reconstruct_bars(
            [
                Trade(
                    timestamp_utc=ORIGIN,
                    price=Decimal("0"),
                    quantity=Decimal("1"),
                    trade_id="z",
                )
            ],
            interval_duration=timedelta(minutes=1),
            alignment_origin_utc=ORIGIN,
        )


def test_direct_trade_rejects_non_positive_quantity() -> None:
    with pytest.raises(InvalidNumericError, match="quantity"):
        reconstruct_bars(
            [
                Trade(
                    timestamp_utc=ORIGIN,
                    price=Decimal("1"),
                    quantity=Decimal("0"),
                    trade_id="z",
                )
            ],
            interval_duration=timedelta(minutes=1),
            alignment_origin_utc=ORIGIN,
        )


def test_duplicate_reconstructed_intervals_reported_not_overwritten() -> None:
    interval = timedelta(minutes=1)
    bar = OHLCVBar(
        interval_start_utc=ORIGIN,
        interval_end_utc=ORIGIN + interval,
        open=Decimal("1"),
        high=Decimal("1"),
        low=Decimal("1"),
        close=Decimal("1"),
        volume_base=Decimal("1"),
        volume_quote=Decimal("1"),
        trade_count=1,
    )
    other = OHLCVBar(
        interval_start_utc=ORIGIN,
        interval_end_utc=ORIGIN + interval,
        open=Decimal("9"),
        high=Decimal("9"),
        low=Decimal("9"),
        close=Decimal("9"),
        volume_base=Decimal("9"),
        volume_quote=Decimal("9"),
        trade_count=9,
    )
    cmp = compare_bars(
        [bar, other],
        [bar],
        price_tolerance=Decimal("0"),
        volume_tolerance=Decimal("0"),
    )
    assert cmp.duplicate_reconstructed_intervals == (ORIGIN,)
    # First reconstructed bar is used for comparison (not silently last-wins).
    assert not any(m.field_name == "open" for m in cmp.ohlc_mismatches)
