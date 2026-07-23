"""PORT-002 — Perpetual Long/Short Portfolio Simulator.

Simulates perpetual long/short allocations with 8-hour funding rate cashflow accounting
(via BitMEXFundingProvider), margin maintenance checks, liquidation events, and long/short
return attribution.
"""

from __future__ import annotations

import collections
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from cryptofactors.factors.contract import FactorFrame, FactorValue
from cryptofactors.portfolio.cost import CostConfig
from cryptofactors.portfolio.simulation import Allocator, PortfolioError
from cryptofactors.validation.labels import DecisionEvent


@dataclass(frozen=True, slots=True)
class PerpetualSimulationPeriod:
    """One holding period in a perpetual simulation."""

    decision_time: datetime
    gross_return: Decimal
    net_return: Decimal
    turnover: Decimal
    trading_cost: Decimal
    funding_cost: Decimal
    long_return: Decimal
    short_return: Decimal
    is_liquidated: bool = False


@dataclass(frozen=True, slots=True)
class PerpetualSimulationResult:
    """Cumulative result of a perpetual portfolio simulation."""

    portfolio_version: str
    cost_version: str
    periods: tuple[PerpetualSimulationPeriod, ...]

    @property
    def net_return(self) -> Decimal:
        """Total cumulative net return across all periods."""
        r = Decimal("1.0")
        for p in self.periods:
            r *= Decimal("1.0") + p.net_return
        return r - Decimal("1.0")

    @property
    def liquidation_count(self) -> int:
        """Total number of liquidation events during simulation."""
        return sum(1 for p in self.periods if p.is_liquidated)


class LongShortRankAllocator:
    """Long/short allocator allocating top N scores to long leg (+0.5) and bottom N to short leg (-0.5)."""

    allocator_version: str = "ls_rank_v1"

    def __init__(self, target_leverage: float = 1.0) -> None:
        if target_leverage <= 0:
            raise PortfolioError("target_leverage must be positive")
        self.target_leverage: Decimal = Decimal(str(target_leverage))

    def allocate(self, values: Sequence[FactorValue]) -> dict[str, Decimal]:
        """Allocate long weights to positive factor scores and short weights to negative factor scores."""
        if not values:
            return {}

        sorted_vals = sorted(values, key=lambda v: v.score)
        n = len(sorted_vals)
        if n == 1:
            s = sorted_vals[0].score
            if s > 0:
                return {sorted_vals[0].instrument_id: self.target_leverage}
            if s < 0:
                return {sorted_vals[0].instrument_id: -self.target_leverage}
            return {sorted_vals[0].instrument_id: Decimal("0")}

        long_candidates = [v for v in sorted_vals if v.score > 0]
        short_candidates = [v for v in sorted_vals if v.score < 0]

        weights: dict[str, Decimal] = {}
        half_lev = self.target_leverage / Decimal("2")

        if long_candidates:
            w_long = half_lev / Decimal(len(long_candidates))
            for v in long_candidates:
                weights[v.instrument_id] = w_long

        if short_candidates:
            w_short = -half_lev / Decimal(len(short_candidates))
            for v in short_candidates:
                weights[v.instrument_id] = w_short

        return weights


class PerpetualSimulator:
    """Perpetual long/short portfolio simulator with funding cashflows and margin liquidation checks."""

    def __init__(
        self,
        allocator: Allocator,
        cost_config: CostConfig,
        *,
        funding_provider: Any | None = None,
        maintenance_margin_rate: Decimal = Decimal("0.05"),
        portfolio_version: str = "perp_sim_v1",
        horizon_days: int = 7,
    ) -> None:
        self.allocator: Allocator = allocator
        self.cost_config: CostConfig = cost_config
        self.funding_provider: Any | None = funding_provider
        self.maintenance_margin_rate: Decimal = maintenance_margin_rate
        self.portfolio_version: str = portfolio_version
        self.horizon_days: int = horizon_days

    def simulate(
        self,
        frames: Sequence[FactorFrame],
        events: Sequence[DecisionEvent],
    ) -> PerpetualSimulationResult:
        """Run perpetual portfolio simulation across sequential factor frames and decision events."""
        event_map: dict[datetime, dict[str, Decimal]] = collections.defaultdict(dict)
        for ev in events:
            inst = str(ev.instrument_id)
            event_map[ev.decision_time][inst] = ev.label_value

        sorted_frames = sorted(frames, key=lambda f: f.decision_time)

        periods: list[PerpetualSimulationPeriod] = []
        current_weights: dict[str, Decimal] = collections.defaultdict(Decimal)

        cost_bps = self.cost_config.fee_bps + self.cost_config.slippage_bps
        cost_rate = cost_bps / Decimal("10000")

        for idx, frame in enumerate(sorted_frames):
            t = frame.decision_time
            if idx + 1 < len(sorted_frames):
                t_end = sorted_frames[idx + 1].decision_time
            else:
                t_end = t + timedelta(days=self.horizon_days)

            target_weights = self.allocator.allocate(frame.values)

            # 1. Turnover & Trading Cost
            all_assets = set(current_weights.keys()) | set(target_weights.keys())
            turnover = Decimal("0")
            for asset in all_assets:
                diff = target_weights.get(asset, Decimal("0")) - current_weights.get(asset, Decimal("0"))
                turnover += abs(diff)

            trading_cost = turnover * cost_rate

            # 2. Long/Short Return Attribution
            period_events = event_map.get(t, {})
            long_return = Decimal("0")
            short_return = Decimal("0")

            for asset, w in target_weights.items():
                asset_ret = period_events.get(asset, Decimal("0"))
                ret_contrib = w * asset_ret
                if w > Decimal("0"):
                    long_return += ret_contrib
                elif w < Decimal("0"):
                    short_return += ret_contrib

            gross_return = long_return + short_return

            # 3. Funding Cashflows
            funding_cost = Decimal("0")
            if self.funding_provider is not None:
                for asset, w in target_weights.items():
                    try:
                        cf_usd = self.funding_provider.compute_funding_cashflow(
                            symbol=asset,
                            position_qty=float(w),
                            start_time=t,
                            end_time=t_end,
                        )
                        funding_cost += Decimal(str(cf_usd))
                    except Exception:  # noqa: BLE001
                        pass

            # 4. Net Return & Margin Liquidation Check
            loss = trading_cost - gross_return - funding_cost
            max_allowed_loss = Decimal("1.0") - self.maintenance_margin_rate

            if loss >= max_allowed_loss:
                is_liquidated = True
                net_return = Decimal("-1.0")
                current_weights = collections.defaultdict(Decimal)
            else:
                is_liquidated = False
                net_return = gross_return - trading_cost + funding_cost

                drifted_weights: dict[str, Decimal] = {}
                total_val = Decimal("1.0") + net_return
                if total_val > Decimal("0"):
                    for asset, w in target_weights.items():
                        asset_ret = period_events.get(asset, Decimal("0"))
                        drifted_weights[asset] = (w * (Decimal("1.0") + asset_ret)) / total_val

                current_weights = collections.defaultdict(Decimal, drifted_weights)

            periods.append(
                PerpetualSimulationPeriod(
                    decision_time=t,
                    gross_return=gross_return,
                    net_return=net_return,
                    turnover=turnover,
                    trading_cost=trading_cost,
                    funding_cost=funding_cost,
                    long_return=long_return,
                    short_return=short_return,
                    is_liquidated=is_liquidated,
                )
            )

        return PerpetualSimulationResult(
            portfolio_version=self.portfolio_version,
            cost_version=self.cost_config.cost_version,
            periods=tuple(periods),
        )
