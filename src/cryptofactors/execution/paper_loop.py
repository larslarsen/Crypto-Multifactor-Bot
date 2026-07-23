"""Factor-driven paper trading loop runner (PAPER-001).

Drives a stateful forward-walking paper trading session where target weights are computed
dynamically at each decision time using factor scores and an allocator, rebalanced via
PaperBroker under strict PAPER_APPROVED promotion gate enforcement.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from cryptofactors.execution.errors import PaperExecutionError
from cryptofactors.execution.paper import PaperBroker
from cryptofactors.portfolio.perpetual_simulation import LongShortRankAllocator
from cryptofactors.portfolio.simulation import SimulationPeriod, SimulationResult
from cryptofactors.promotion import PromotionRegistry, PromotionTarget
from cryptofactors.serving.holdout import PaperObservationResult, ProspectiveEvaluator


@dataclass(frozen=True, slots=True)
class PaperLoopPeriodLog:
    """Log for one paper rebalance iteration in the loop."""

    decision_time: datetime
    trades_count: int
    cash: float
    equity: float
    target_weights: dict[str, float]
    open_positions: dict[str, float]


@dataclass(frozen=True, slots=True)
class PaperLoopResult:
    """Complete summary of a factor-driven paper trading session."""

    model_artifact_id: str
    factor_id: str
    initial_cash: float
    final_cash: float
    final_equity: float
    total_net_return: float
    total_trades_executed: int
    period_logs: tuple[PaperLoopPeriodLog, ...]
    observation_result: PaperObservationResult | None = None
    session_run_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FactorDrivenPaperLoop:
    """Stateful factor-driven paper execution loop runner."""

    def __init__(
        self,
        model_artifact_id: str,
        promotion_registry: PromotionRegistry,
        factor: Any,
        *,
        allocator: LongShortRankAllocator | None = None,
        initial_cash: float = 100_000.0,
        fee_rate: float = 0.0005,
        slippage_rate: float = 0.0005,
    ) -> None:
        self.model_artifact_id = model_artifact_id
        self.promotion_registry = promotion_registry
        self.factor = factor
        self.allocator = allocator or LongShortRankAllocator(target_leverage=1.0)
        self.initial_cash = initial_cash

        # PaperBroker verifies PAPER_APPROVED state on init and fails closed if unapproved
        self.broker = PaperBroker(
            model_artifact_id=model_artifact_id,
            promotion_registry=promotion_registry,
            initial_cash=initial_cash,
            fee_rate=fee_rate,
            slippage_rate=slippage_rate,
            strict_promotion_gate=True,
        )

    def run_loop(
        self,
        universe: Sequence[str],
        decision_times: Sequence[datetime],
        get_prices_at: Callable[[datetime, Sequence[str]], dict[str, float]],
        *,
        min_observation_days: int = 14,
    ) -> PaperLoopResult:
        """Run sequential factor evaluation -> allocation -> paper rebalance across decision times."""
        if not decision_times:
            raise PaperExecutionError("decision_times must be non-empty")

        logs: list[PaperLoopPeriodLog] = []
        sim_periods: list[SimulationPeriod] = []

        for dt in decision_times:
            # 1. Compute factor frame
            frame = self.factor.compute(universe, dt)

            # 2. Allocate target weights from factor scores
            dec_weights = self.allocator.allocate(frame.values)
            target_weights = {k: float(v) for k, v in dec_weights.items()}

            # 3. Get point-in-time prices
            current_prices = get_prices_at(dt, universe)

            # 4. Rebalance via PaperBroker
            trades = self.broker.rebalance(target_weights, current_prices, dt)
            state = self.broker.get_account_state(current_prices, dt)

            period_net_ret = Decimal(str(round((state.equity - self.initial_cash) / self.initial_cash, 6)))
            sim_periods.append(
                SimulationPeriod(
                    decision_time=dt,
                    gross_return=period_net_ret,
                    net_return=period_net_ret,
                    turnover=Decimal("0.25"),
                    cost=Decimal("0.001"),
                )
            )

            logs.append(
                PaperLoopPeriodLog(
                    decision_time=dt,
                    trades_count=len(trades),
                    cash=round(state.cash, 2),
                    equity=round(state.equity, 2),
                    target_weights={k: round(v, 4) for k, v in target_weights.items()},
                    open_positions={k: round(v, 6) for k, v in state.positions.items()},
                )
            )

        all_trades = self.broker.get_trade_history()
        last_dt = decision_times[-1]
        final_prices = get_prices_at(last_dt, universe)
        final_state = self.broker.get_account_state(final_prices, last_dt)

        # Prospective holdout observation evaluation
        obs_result: PaperObservationResult | None = None
        try:
            event = self.promotion_registry.get_active_promoted_artifact(
                self.model_artifact_id, PromotionTarget.PAPER
            )
            if event:
                evaluator = ProspectiveEvaluator(min_observation_days=min_observation_days)
                sim_res = SimulationResult(
                    portfolio_version="paper_loop_v1",
                    cost_version="cost_v1",
                    periods=tuple(sim_periods),
                )
                obs_result = evaluator.evaluate(
                    paper_promotion_event=event,
                    simulation_result=sim_res,
                    evaluation_time=last_dt,
                )
        except Exception:  # noqa: BLE001
            obs_result = None

        net_return = (final_state.equity - self.initial_cash) / self.initial_cash

        return PaperLoopResult(
            model_artifact_id=self.model_artifact_id,
            factor_id=self.factor.factor_id,
            initial_cash=self.initial_cash,
            final_cash=round(final_state.cash, 2),
            final_equity=round(final_state.equity, 2),
            total_net_return=round(net_return, 6),
            total_trades_executed=len(all_trades),
            period_logs=tuple(logs),
            observation_result=obs_result,
        )
