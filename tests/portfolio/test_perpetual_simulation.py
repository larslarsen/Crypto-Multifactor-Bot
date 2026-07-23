"""Tests for PORT-002 Perpetual Long/Short Portfolio Simulator and Allocator."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from cryptofactors.factors.contract import FactorFrame, FactorValue
from cryptofactors.portfolio import (
    CostConfig,
    LongShortRankAllocator,
    PerpetualSimulator,
)
from cryptofactors.validation.labels import DecisionEvent, LabelType

UTC = timezone.utc


def sample_factor_frame(scores: dict[str, float], dt: datetime) -> FactorFrame:
    vals = [
        FactorValue(
            instrument_id=sym,
            decision_time=dt,
            raw_value=score,
            score=score,
            availability_time=dt,
            factor_id="tsmom_30_7",
            factor_version="1",
        )
        for sym, score in sorted(scores.items())
    ]
    return FactorFrame(
        values=tuple(vals),
        factor_id="tsmom_30_7",
        factor_version="1",
        decision_time=dt,
    )


class FakeFundingProvider:
    """Mock BitMEX funding provider returning deterministic cashflows."""

    def __init__(self, rate: float = 0.001) -> None:
        self.rate = rate

    def compute_funding_cashflow(
        self,
        symbol: str,
        position_qty: float,
        start_time: datetime,
        end_time: datetime,
    ) -> float:
        # Long pays rate when >0 (-pos * rate)
        return -1.0 * position_qty * self.rate


def test_long_short_rank_allocator() -> None:
    allocator = LongShortRankAllocator(target_leverage=1.0)

    # 4 assets: 2 positive (long), 2 negative (short)
    scores = {"BTC": 0.05, "ETH": 0.02, "SOL": -0.01, "XRP": -0.03}
    frame = sample_factor_frame(scores, datetime(2026, 7, 23, tzinfo=UTC))

    weights = allocator.allocate(frame.values)

    # Long leg sum = +0.5, Short leg sum = -0.5
    assert weights["BTC"] == Decimal("0.25")
    assert weights["ETH"] == Decimal("0.25")
    assert weights["SOL"] == Decimal("-0.25")
    assert weights["XRP"] == Decimal("-0.25")

    total_gross = sum(abs(w) for w in weights.values())
    assert total_gross == Decimal("1.0")


def test_perpetual_simulator_with_funding_cashflows() -> None:
    allocator = LongShortRankAllocator(target_leverage=1.0)
    cost = CostConfig(fee_bps=Decimal("5"), slippage_bps=Decimal("5"), cost_version="cost_v1")
    funding_provider = FakeFundingProvider(rate=0.001)  # 10 bps funding fee

    simulator = PerpetualSimulator(
        allocator=allocator,
        cost_config=cost,
        funding_provider=funding_provider,
    )

    t0 = datetime(2026, 7, 23, 0, 0, tzinfo=UTC)
    scores = {"BTC": 0.1, "ETH": -0.1}
    frame = sample_factor_frame(scores, t0)

    # Events: BTC +5% return, ETH -2% return (so shorting ETH gains +2%)
    events = [
        DecisionEvent(
            instrument_id="BTC",
            decision_time=t0,
            event_start=t0,
            event_end=datetime(2026, 7, 30, 0, 0, tzinfo=UTC),
            label_type=LabelType.FORWARD_RETURN,
            label_value=Decimal("0.05"),
            label_direction=1,
            entry_price=Decimal("50000"),
            exit_price=Decimal("52500"),
        ),
        DecisionEvent(
            instrument_id="ETH",
            decision_time=t0,
            event_start=t0,
            event_end=datetime(2026, 7, 30, 0, 0, tzinfo=UTC),
            label_type=LabelType.FORWARD_RETURN,
            label_value=Decimal("-0.02"),
            label_direction=-1,
            entry_price=Decimal("3000"),
            exit_price=Decimal("2940"),
        ),
    ]

    res = simulator.simulate([frame], events)

    assert len(res.periods) == 1
    period = res.periods[0]

    # Gross return = (0.5 * 0.05) + (-0.5 * -0.02) = 0.025 + 0.01 = 0.035 (+3.5%)
    assert pytest.approx(float(period.gross_return), abs=1e-5) == 0.035
    assert pytest.approx(float(period.long_return), abs=1e-5) == 0.025
    assert pytest.approx(float(period.short_return), abs=1e-5) == 0.01

    # Trading cost: turnover 1.0 * (10 bps) = 0.001
    assert pytest.approx(float(period.trading_cost), abs=1e-5) == 0.001

    # Funding cost: long pays 0.5 * 0.001 = 0.0005, short pays -0.5 * 0.001 = -0.0005
    # Total funding cost = 0.0
    assert period.is_liquidated is False


def test_liquidation_on_margin_breach() -> None:
    allocator = LongShortRankAllocator(target_leverage=1.0)
    cost = CostConfig(fee_bps=Decimal("5"), slippage_bps=Decimal("5"), cost_version="cost_v1")

    simulator = PerpetualSimulator(
        allocator=allocator,
        cost_config=cost,
        maintenance_margin_rate=Decimal("0.05"),
    )

    t0 = datetime(2026, 7, 23, 0, 0, tzinfo=UTC)
    scores = {"BTC": 0.1}
    frame = sample_factor_frame(scores, t0)

    # Catastrophic loss event: BTC crashes -98%
    events = [
        DecisionEvent(
            instrument_id="BTC",
            decision_time=t0,
            event_start=t0,
            event_end=datetime(2026, 7, 30, 0, 0, tzinfo=UTC),
            label_type=LabelType.FORWARD_RETURN,
            label_value=Decimal("-0.98"),
            label_direction=-1,
            entry_price=Decimal("50000"),
            exit_price=Decimal("1000"),
        ),
    ]

    res = simulator.simulate([frame], events)

    assert len(res.periods) == 1
    period = res.periods[0]
    assert period.is_liquidated is True
    assert period.net_return == Decimal("-1.0")
    assert res.liquidation_count == 1
