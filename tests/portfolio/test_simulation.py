from datetime import datetime, timezone
from decimal import Decimal

from cryptofactors.factors.contract import FactorFrame, FactorValue
from cryptofactors.portfolio.cost import CostConfig
from cryptofactors.portfolio.simulation import (
    RankWeightAllocator,
    PortfolioSimulator,
)
from cryptofactors.validation.labels import DecisionEvent, LabelType


def test_rank_weight_allocator() -> None:
    allocator = RankWeightAllocator(long_only=False)
    
    t = datetime(2024, 1, 1, tzinfo=timezone.utc)
    values = [
        FactorValue("A", t, 0.0, 1.0, t, "f1", "v1"),
        FactorValue("B", t, 0.0, 2.0, t, "f1", "v1"),
        FactorValue("C", t, 0.0, 3.0, t, "f1", "v1"),
    ]
    
    weights = allocator.allocate(values)
    # Ranks: A=0, B=0.5, C=1.0. Centered: A=-0.5, B=0, C=0.5
    # Absolute sum = 1.0. Weights: A=-0.5, B=0, C=0.5
    assert weights["A"] == Decimal("-0.5")
    assert weights["B"] == Decimal("0")
    assert weights["C"] == Decimal("0.5")


def test_portfolio_simulator() -> None:
    allocator = RankWeightAllocator(long_only=True)
    cost = CostConfig(fee_bps=Decimal("10"), slippage_bps=Decimal("10"), cost_version="test")
    sim = PortfolioSimulator(allocator, cost)
    
    t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    
    frame1 = FactorFrame(
        values=(
            FactorValue("A", t1, 0.0, 1.0, t1, "f1", "v1"),
            FactorValue("B", t1, 0.0, 3.0, t1, "f1", "v1"), # Highest score, long_only gets rank 1.0
        ),
        factor_id="f1", factor_version="v1", decision_time=t1
    )
    
    # B gets weight 1.0, A gets weight 0.0
    # Turnover from empty to this is 1.0 + 0.0 = 1.0
    # Cost = 1.0 * 20bps = 0.002
    
    events = [
        DecisionEvent(
            instrument_id="B",
            decision_time=t1,
            event_start=t1,
            event_end=datetime(2024, 1, 2, tzinfo=timezone.utc),
            label_type=LabelType.FORWARD_RETURN,
            label_value=Decimal("0.10"),
            label_direction=1,
            entry_price=Decimal("100"),
            exit_price=Decimal("110"),
        )
    ]
    
    res = sim.simulate([frame1], events)
    assert len(res.periods) == 1
    p1 = res.periods[0]
    
    assert p1.turnover == Decimal("1.0")
    assert p1.cost == Decimal("0.002")
    assert p1.gross_return == Decimal("0.10")
    assert p1.net_return == Decimal("0.098")
