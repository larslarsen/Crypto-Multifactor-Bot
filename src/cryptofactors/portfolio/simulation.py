from __future__ import annotations

import collections
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from cryptofactors.factors.contract import FactorFrame, FactorValue
from cryptofactors.portfolio.cost import CostConfig
from cryptofactors.validation.labels import DecisionEvent


class PortfolioError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SimulationResult:
    portfolio_version: str
    cost_version: str
    periods: tuple[SimulationPeriod, ...]

    @property
    def net_return(self) -> Decimal:
        """Total cumulative net return."""
        r = Decimal("1.0")
        for p in self.periods:
            r *= (Decimal("1.0") + p.net_return)
        return r - Decimal("1.0")


@dataclass(frozen=True, slots=True)
class SimulationPeriod:
    decision_time: datetime
    gross_return: Decimal
    net_return: Decimal
    turnover: Decimal
    cost: Decimal


@runtime_checkable
class Allocator(Protocol):
    """Generates target weights from factor scores."""
    
    allocator_version: str

    def allocate(self, values: Sequence[FactorValue]) -> dict[str, Decimal]: ...


class RankWeightAllocator:
    """Allocates based on rank. Simplest allocator."""
    
    allocator_version = "rank_weight_v1"
    
    def __init__(self, long_only: bool = False):
        self.long_only = long_only
        
    def allocate(self, values: Sequence[FactorValue]) -> dict[str, Decimal]:
        if not values:
            return {}
            
        sorted_vals = sorted(values, key=lambda v: v.score)
        n = len(sorted_vals)
        if n == 1:
            return {sorted_vals[0].instrument_id: Decimal("1.0")}
            
        weights = {}
        for i, val in enumerate(sorted_vals):
            # Rank from -0.5 to 0.5 (or 0 to 1 for long only)
            rank = (i / (n - 1)) if n > 1 else Decimal("0.5")
            weight = Decimal(str(rank))
            if not self.long_only:
                weight = weight - Decimal("0.5")
            weights[val.instrument_id] = weight
            
        # Normalize sum of absolute weights to 1.0 (so leverage is 1.0)
        total_abs_weight = sum(abs(w) for w in weights.values())
        if total_abs_weight > 0:
            weights = {k: w / total_abs_weight for k, w in weights.items()}
            
        return weights


class PortfolioSimulator:
    def __init__(
        self,
        allocator: Allocator,
        cost_config: CostConfig,
        portfolio_version: str = "sim_v1",
    ):
        self.allocator = allocator
        self.cost_config = cost_config
        self.portfolio_version = portfolio_version

    def simulate(
        self,
        frames: Sequence[FactorFrame],
        events: Sequence[DecisionEvent],
    ) -> SimulationResult:
        
        # Group events by decision_time and instrument_id
        event_map: dict[datetime, dict[str, Decimal]] = collections.defaultdict(dict)
        for ev in events:
            inst = str(ev.instrument_id)
            event_map[ev.decision_time][inst] = ev.label_value

        sorted_frames = sorted(frames, key=lambda f: f.decision_time)
        
        periods = []
        current_weights: dict[str, Decimal] = collections.defaultdict(Decimal)
        
        cost_bps = self.cost_config.fee_bps + self.cost_config.slippage_bps
        cost_rate = cost_bps / Decimal("10000")

        for frame in sorted_frames:
            t = frame.decision_time
            # 1. Allocate based on factor scores
            target_weights = self.allocator.allocate(frame.values)
            
            # 2. Compute turnover to transition from current_weights to target_weights
            all_assets = set(current_weights.keys()) | set(target_weights.keys())
            turnover = Decimal("0")
            for asset in all_assets:
                diff = target_weights.get(asset, Decimal("0")) - current_weights.get(asset, Decimal("0"))
                turnover += abs(diff)
                
            # 3. Apply transaction costs
            cost = turnover * cost_rate
            
            # 4. Simulate holding period
            period_events = event_map.get(t, {})
            gross_return = Decimal("0")
            for asset, w in target_weights.items():
                asset_return = period_events.get(asset, Decimal("0"))
                gross_return += w * asset_return
                
            net_return = gross_return - cost
            
            # 5. Drift weights for next period (assuming no compounding of short side for simplicity, just proportional to target and return)
            # A full drift simulation requires position accounting. For a flat rebalance approach, we approximate:
            drifted_weights = {}
            total_drifted_value = Decimal("1.0") + gross_return
            if total_drifted_value > Decimal("0"):
                for asset, w in target_weights.items():
                    asset_return = period_events.get(asset, Decimal("0"))
                    drifted_weights[asset] = (w * (Decimal("1.0") + asset_return)) / total_drifted_value
            else:
                drifted_weights = {} # wipeout
                
            current_weights = collections.defaultdict(Decimal, drifted_weights)
            
            periods.append(
                SimulationPeriod(
                    decision_time=t,
                    gross_return=gross_return,
                    net_return=net_return,
                    turnover=turnover,
                    cost=cost,
                )
            )
            
        return SimulationResult(
            portfolio_version=self.portfolio_version,
            cost_version=self.cost_config.cost_version,
            periods=tuple(periods),
        )
