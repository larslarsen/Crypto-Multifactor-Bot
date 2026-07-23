"""MOMTS-001 — Confirmatory experiment runner for MOM-TS-01 time-series momentum.

Builds distinct EXP-001 ``ExperimentBundle`` fingerprints for EXP-2026-019
(``tsmom_30_7``) and EXP-2026-020 (``tsmom_90_7``), runs costed spot long/cash
portfolio simulation via PORT-001, and emits structured run artifacts. No
promotion events are produced by this runner.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from cryptofactors.factors.contract import FactorFrame
from cryptofactors.factors.tsmom import (
    TSMOM_30_7_FACTOR_ID,
    TSMOM_90_7_FACTOR_ID,
    TimeSeriesMomentumFactor,
)
from cryptofactors.portfolio.cost import CostConfig
from cryptofactors.portfolio.simulation import (
    PortfolioSimulator,
    RankWeightAllocator,
    SimulationResult,
)
from cryptofactors.validation.experiment import (
    ExperimentBundle,
    InMemoryExperimentRegistry,
)
from cryptofactors.validation.labels import (
    AsOfLabelEngine,
    DecisionEvent,
    LabelConfig,
    LabelType,
)
from cryptofactors.validation.split import (
    PurgedChronologicalSplitter,
    SplitConfig,
    SplitMode,
)

EXP_2026_019_ID: str = "EXP-2026-019"
EXP_2026_020_ID: str = "EXP-2026-020"

DEFAULT_HORIZON: timedelta = timedelta(days=7)
DEFAULT_EMBARGO: timedelta = timedelta(days=1)
DEFAULT_MIN_GAP: timedelta = timedelta(0)
DEFAULT_COST_VERSION: str = "cost_v1_binance_spot"


def _default_label_config(market_dataset_id: str) -> LabelConfig:
    return LabelConfig(
        horizon=DEFAULT_HORIZON,
        label_type=LabelType.FORWARD_RETURN,
        min_gap=DEFAULT_MIN_GAP,
        price_field="close",
        market_dataset_id=market_dataset_id,
    )


def _default_split_config() -> SplitConfig:
    return SplitConfig(
        mode=SplitMode.PURGED_KFOLD,
        n_folds=3,
        embargo=DEFAULT_EMBARGO,
        instrument_dataset_id="ref_instrument_version",
    )


def _default_cost_config() -> CostConfig:
    return CostConfig(
        fee_bps=Decimal("10"),
        slippage_bps=Decimal("5"),
        cost_version=DEFAULT_COST_VERSION,
    )


def build_momts_30_7_bundle(
    market_dataset_id: str,
    *,
    universe_source: str = "audited_u50_best_available_pit",
    portfolio_version: str = "spot_long_cash_v1",
    cost_version: str = DEFAULT_COST_VERSION,
) -> ExperimentBundle:
    """Build the EXP-001 ExperimentBundle for EXP-2026-019 (tsmom_30_7)."""
    metadata: dict[str, str | int | float | bool] = {
        "experiment_id": EXP_2026_019_ID,
        "signal": "tsmom_30_7",
        "formula": "log(P[t-7d] / P[t-30d])",
        "lookback_days": 30,
        "skip_days": 7,
        "horizon_days": 7,
        "universe_source": universe_source,
        "portfolio_cell": "spot_long_cash",
        "portfolio_version": portfolio_version,
        "cost_version": cost_version,
        "survivorship_source": "cmc_data_api_unofficial_proxy",
    }
    return ExperimentBundle(
        label_config=_default_label_config(market_dataset_id),
        split_config=_default_split_config(),
        factor_defs=(TSMOM_30_7_FACTOR_ID,),
        metadata=metadata,
    )


def build_momts_90_7_bundle(
    market_dataset_id: str,
    *,
    universe_source: str = "audited_u50_best_available_pit",
    portfolio_version: str = "spot_long_cash_v1",
    cost_version: str = DEFAULT_COST_VERSION,
) -> ExperimentBundle:
    """Build the EXP-001 ExperimentBundle for EXP-2026-020 (tsmom_90_7)."""
    metadata: dict[str, str | int | float | bool] = {
        "experiment_id": EXP_2026_020_ID,
        "signal": "tsmom_90_7",
        "formula": "log(P[t-7d] / P[t-90d])",
        "lookback_days": 90,
        "skip_days": 7,
        "horizon_days": 7,
        "universe_source": universe_source,
        "portfolio_cell": "spot_long_cash",
        "portfolio_version": portfolio_version,
        "cost_version": cost_version,
        "survivorship_source": "cmc_data_api_unofficial_proxy",
    }
    return ExperimentBundle(
        label_config=_default_label_config(market_dataset_id),
        split_config=_default_split_config(),
        factor_defs=(TSMOM_90_7_FACTOR_ID,),
        metadata=metadata,
    )


@dataclass(frozen=True, slots=True)
class MOMTSRunnerResult:
    """Structured run artifact for one confirmatory experiment."""

    experiment_id: str
    factor_id: str
    factor_version: str
    bundle: ExperimentBundle
    fingerprint: str
    simulation: SimulationResult
    n_periods: int
    net_return: Decimal
    mean_turnover: Decimal
    total_cost: Decimal
    run_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MOMTSRunner:
    """Confirmatory runner for MOM-TS-01 (EXP-2026-019 / EXP-2026-020).

    Parameters
    ----------
    as_of_store:
        Reviewed AsOfStore (e.g. ``CatalogAsOfStore``) used for both factor
        computation and label/split engines.
    market_dataset_id:
        Published market_bars dataset id for price access.
    registry:
        Optional experiment registry for bundle registration. When provided,
        bundles are registered and the fingerprint is validated against the
        registry. Defaults to an ``InMemoryExperimentRegistry``.
    """

    def __init__(
        self,
        as_of_store: Any,
        *,
        market_dataset_id: str,
        registry: InMemoryExperimentRegistry | None = None,
        cost_config: CostConfig | None = None,
    ) -> None:
        if as_of_store is None:
            raise ValueError("as_of_store must not be None")
        if not market_dataset_id or not isinstance(market_dataset_id, str):
            raise ValueError("market_dataset_id must be a non-empty string")
        self._as_of_store = as_of_store
        self._market_dataset_id: str = market_dataset_id
        self._registry: InMemoryExperimentRegistry = registry or InMemoryExperimentRegistry()
        self._cost_config: CostConfig = cost_config or _default_cost_config()
        self._label_engine: AsOfLabelEngine = AsOfLabelEngine(as_of_store)
        self._splitter: PurgedChronologicalSplitter = PurgedChronologicalSplitter(as_of_store)

    def run_experiment(
        self,
        *,
        experiment_id: str,
        factor: TimeSeriesMomentumFactor,
        bundle: ExperimentBundle,
        universe: Sequence[str],
        decision_times: Sequence[datetime],
    ) -> MOMTSRunnerResult:
        """Execute one confirmatory experiment end-to-end (no promotion events).

        Steps:
        1. Register the bundle and obtain its fingerprint.
        2. Compute factor frames at each decision time.
        3. Build 7d forward-return labels via LABEL-001.
        4. Build purged chronological splits via SPLIT-001.
        5. Run costed spot long/cash portfolio simulation via PORT-001.
        6. Emit structured run artifact.
        """
        if experiment_id not in (EXP_2026_019_ID, EXP_2026_020_ID):
            raise ValueError(
                f"experiment_id must be {EXP_2026_019_ID} or {EXP_2026_020_ID}, got {experiment_id!r}"
            )

        fingerprint = self._registry.register(bundle)

        frames: list[FactorFrame] = []
        for dt in decision_times:
            frame = factor.compute(universe, dt)
            if frame.values:
                frames.append(frame)

        if not frames:
            raise ValueError(
                f"No factor frames produced for {experiment_id}; check universe/decision_times"
            )

        events: list[DecisionEvent] = self._label_engine.compute(
            instruments=list(universe),
            decision_times=list(decision_times),
            config=bundle.label_config,
        )
        if not events:
            raise ValueError(
                f"No labels produced for {experiment_id}; check market data coverage"
            )
        self._splitter.split(
            events=[e.to_event_interval() for e in events],
            config=bundle.split_config,
        )

        allocator = RankWeightAllocator(long_only=True)
        simulator = PortfolioSimulator(
            allocator=allocator,
            cost_config=self._cost_config,
            portfolio_version="spot_long_cash_v1",
        )
        simulation = simulator.simulate(frames, events)

        periods = simulation.periods
        n_periods = len(periods)
        net_return = simulation.net_return
        mean_turnover: Decimal = (
            sum((p.turnover for p in periods), Decimal("0")) / Decimal(n_periods)
            if n_periods > 0
            else Decimal("0")
        )
        total_cost = sum((p.cost for p in periods), Decimal("0"))

        return MOMTSRunnerResult(
            experiment_id=experiment_id,
            factor_id=factor.factor_id,
            factor_version=factor.factor_version,
            bundle=bundle,
            fingerprint=fingerprint,
            simulation=simulation,
            n_periods=n_periods,
            net_return=net_return,
            mean_turnover=mean_turnover,
            total_cost=total_cost,
        )

    def run_30_7(
        self,
        universe: Sequence[str],
        decision_times: Sequence[datetime],
    ) -> MOMTSRunnerResult:
        """Run EXP-2026-019 (tsmom_30_7)."""
        factor = TimeSeriesMomentumFactor(
            self._as_of_store,
            lookback_days=30,
            skip_days=7,
            market_dataset_id=self._market_dataset_id,
            factor_id=TSMOM_30_7_FACTOR_ID,
        )
        bundle = build_momts_30_7_bundle(self._market_dataset_id)
        return self.run_experiment(
            experiment_id=EXP_2026_019_ID,
            factor=factor,
            bundle=bundle,
            universe=universe,
            decision_times=decision_times,
        )

    def run_90_7(
        self,
        universe: Sequence[str],
        decision_times: Sequence[datetime],
    ) -> MOMTSRunnerResult:
        """Run EXP-2026-020 (tsmom_90_7)."""
        factor = TimeSeriesMomentumFactor(
            self._as_of_store,
            lookback_days=90,
            skip_days=7,
            market_dataset_id=self._market_dataset_id,
            factor_id=TSMOM_90_7_FACTOR_ID,
        )
        bundle = build_momts_90_7_bundle(self._market_dataset_id)
        return self.run_experiment(
            experiment_id=EXP_2026_020_ID,
            factor=factor,
            bundle=bundle,
            universe=universe,
            decision_times=decision_times,
        )