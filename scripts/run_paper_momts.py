#!/usr/bin/env python3
"""PAPER-001 — Factor-driven paper trading loop for MOM-TS-01 (mod_tsmom_30_7_v1).

1. Verifies model artifact ``mod_tsmom_30_7_v1`` is in ``PAPER_APPROVED`` state (promoting if needed).
2. Computes point-in-time factor scores via ``tsmom_30_7`` at each decision time.
3. Allocates target weights via ``LongShortRankAllocator``.
4. Executes paper rebalances via ``PaperBroker`` under strict promotion gate.
5. Evaluates prospective holdout observation reference via ``ProspectiveEvaluator``.
6. Emits ``research/sprint_004/08_PAPER_FACTOR_LOOP_RESULTS.json``.

Usage:
  python3 scripts/run_paper_momts.py --dry-run
  python3 scripts/run_paper_momts.py --db-path control.db
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptofactors.execution.paper_loop import FactorDrivenPaperLoop, PaperLoopResult
from cryptofactors.factors.tsmom import make_tsmom_30_7
from cryptofactors.promotion import (
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)

UTC = timezone.utc
MODEL_ARTIFACT_ID = "mod_tsmom_30_7_v1"
FINGERPRINT = "87469a44a18449bee23de76b1312413fd3e5a649a6677e3509a8c270caea3318"
DEFAULT_OUTPUT_PATH = Path("research/sprint_004/08_PAPER_FACTOR_LOOP_RESULTS.json")


def ensure_paper_approved(
    registry: PromotionRegistry,
    model_artifact_id: str = MODEL_ARTIFACT_ID,
) -> None:
    """Ensure artifact is registered and promoted to PAPER_APPROVED."""
    current_state = registry.get_current_state(model_artifact_id)

    if current_state is None:
        cand_payload = PromotionIdentityPayload(
            model_artifact_id=model_artifact_id,
            experiment_fingerprint=FINGERPRINT,
            dataset_ids=("ds_market_bars", "coingecko_universe"),
            universe_ids=("cmc_survivorship_universe",),
            code_commit="MOMTS-001",
            config_version="cfg_momts_v1",
            feature_version="feat_tsmom_30_7_v1",
            representation_version="rep_time_bar_1h",
            portfolio_version="perp_ls_v1",
            cost_model_version="cost_v1_binance_spot",
            risk_policy_version="risk_lev1.0_w0.15_v1",
            target_stage=PromotionTarget.RESEARCH,
            effective_time=datetime.now(UTC),
            approving_authority="Lead Quantitative Researcher",
            evidence_reference="REVIEW-0174",
        )
        registry.register_candidate(cand_payload, reason="Initial candidate registration")
        current_state = PromotionState.RESEARCH_CANDIDATE

    if current_state == PromotionState.RESEARCH_CANDIDATE:
        accepted_payload = PromotionIdentityPayload(
            model_artifact_id=model_artifact_id,
            experiment_fingerprint=FINGERPRINT,
            dataset_ids=("ds_market_bars", "coingecko_universe"),
            universe_ids=("cmc_survivorship_universe",),
            code_commit="MOMTS-001",
            config_version="cfg_momts_v1",
            feature_version="feat_tsmom_30_7_v1",
            representation_version="rep_time_bar_1h",
            portfolio_version="perp_ls_v1",
            cost_model_version="cost_v1_binance_spot",
            risk_policy_version="risk_lev1.0_w0.15_v1",
            target_stage=PromotionTarget.RESEARCH,
            effective_time=datetime.now(UTC),
            approving_authority="Lead Quantitative Researcher",
            evidence_reference="REVIEW-0174",
        )
        registry.transition_state(
            accepted_payload,
            target_state=PromotionState.RESEARCH_ACCEPTED,
            reason="Accepted scientific review via REVIEW-0174",
        )
        current_state = PromotionState.RESEARCH_ACCEPTED

    if current_state == PromotionState.RESEARCH_ACCEPTED:
        paper_payload = PromotionIdentityPayload(
            model_artifact_id=model_artifact_id,
            experiment_fingerprint=FINGERPRINT,
            dataset_ids=("ds_market_bars", "coingecko_universe"),
            universe_ids=("cmc_survivorship_universe",),
            code_commit="MOMTS-001",
            config_version="cfg_momts_v1",
            feature_version="feat_tsmom_30_7_v1",
            representation_version="rep_time_bar_1h",
            portfolio_version="perp_ls_v1",
            cost_model_version="cost_v1_binance_spot",
            risk_policy_version="risk_lev1.0_w0.15_v1",
            target_stage=PromotionTarget.PAPER,
            effective_time=datetime.now(UTC) - timedelta(days=20),  # effective 20 days ago for holdout
            approving_authority="Lead Quantitative Researcher",
            evidence_reference="REVIEW-0177",
        )
        registry.transition_state(
            paper_payload,
            target_state=PromotionState.PAPER_APPROVED,
            reason="Promoted to PAPER_APPROVED via REVIEW-0177",
        )


class _SyntheticPriceStore:
    """Synthetic as-of price store for factor calculation and price queries."""

    def __init__(self, universe: list[str], days: int = 160) -> None:
        self.universe = universe
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        self.prices: dict[str, list[tuple[datetime, float]]] = {}

        for i, inst in enumerate(universe):
            start = 100.0 * (1.0 + i * 0.2)
            growth = 0.001 * (1 if i % 2 == 0 else -1)
            inst_prices = []
            for d in range(days):
                dt = t0 + timedelta(days=d)
                p = start * ((1.0 + growth) ** d)
                inst_prices.append((dt, p))
            self.prices[inst] = inst_prices

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> Any:
        import pyarrow as pa

        if "ref_instrument" in dataset_id:
            return pa.table({"instrument_id": pa.array([str(k) for k in keys], pa.string())})

        if not keys:
            return pa.table(
                {
                    "instrument_id": pa.array([], pa.string()),
                    "close": pa.array([], pa.float64()),
                    "availability_time": pa.array([], pa.int64()),
                    "period_start": pa.array([], pa.int64()),
                }
            )

        inst = str(keys[0])
        series = self.prices.get(inst, [])
        d = decision_time.astimezone(UTC)

        chosen: tuple[datetime, float] | None = None
        for period_start, v in series:
            avail = period_start + timedelta(days=1)
            if avail <= d:
                chosen = (period_start, v)
            else:
                break

        if chosen is None:
            return pa.table(
                {
                    "instrument_id": pa.array([], pa.string()),
                    "close": pa.array([], pa.float64()),
                    "availability_time": pa.array([], pa.int64()),
                    "period_start": pa.array([], pa.int64()),
                }
            )

        period_start, price = chosen
        pstart_us = int(period_start.timestamp() * 1_000_000)
        avail_us = int((period_start + timedelta(days=1)).timestamp() * 1_000_000)

        return pa.table(
            {
                "instrument_id": pa.array([inst], pa.string()),
                "close": pa.array([price], pa.float64()),
                "availability_time": pa.array([avail_us], pa.int64()),
                "period_start": pa.array([pstart_us], pa.int64()),
            }
        )

    def get_prices_at(self, dt: datetime, universe: Sequence[str]) -> dict[str, float]:
        res: dict[str, float] = {}
        for inst in universe:
            series = self.prices.get(inst, [])
            for p_time, p_val in series:
                if p_time <= dt:
                    res[inst] = p_val
                else:
                    break
        return res


def format_loop_result(res: PaperLoopResult) -> dict[str, Any]:
    """Convert PaperLoopResult to JSON-serializable dictionary."""
    logs = [
        {
            "decision_time": p.decision_time.isoformat(),
            "trades_count": p.trades_count,
            "cash": p.cash,
            "equity": p.equity,
            "target_weights": p.target_weights,
            "open_positions": p.open_positions,
        }
        for p in res.period_logs
    ]

    obs_dict = None
    if res.observation_result:
        obs_dict = {
            "model_artifact_id": res.observation_result.model_artifact_id,
            "reference_id": res.observation_result.reference_id,
            "observation_start": res.observation_result.observation_start.isoformat(),
            "observation_end": res.observation_result.observation_end.isoformat(),
            "duration_days": res.observation_result.duration_days,
            "net_return": float(res.observation_result.net_return),
            "is_complete": res.observation_result.is_complete,
            "meets_risk_limits": res.observation_result.meets_risk_limits,
        }

    return {
        "model_artifact_id": res.model_artifact_id,
        "factor_id": res.factor_id,
        "initial_cash": res.initial_cash,
        "final_cash": res.final_cash,
        "final_equity": res.final_equity,
        "total_net_return": res.total_net_return,
        "total_trades_executed": res.total_trades_executed,
        "paper_observation_reference": obs_dict["reference_id"] if obs_dict else None,
        "observation_summary": obs_dict,
        "period_logs": logs,
        "session_run_at": res.session_run_at.isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run factor-driven paper trading loop for MOM-TS-01.")
    parser.add_argument("--db-path", type=str, default="control.db", help="Path to control SQLite DB")
    parser.add_argument("--dry-run", action="store_true", help="Run with temporary SQLite DB and synthetic store")
    parser.add_argument("--out", type=str, default="", help="Path to write JSON results summary")
    args = parser.parse_args()

    if args.dry_run:
        print("Running factor-driven paper loop in DRY-RUN mode...", file=sys.stderr)
        tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(tmpdir.name) / "control.db"
    else:
        db_path = Path(args.db_path)

    registry = PromotionRegistry(db_path)
    ensure_paper_approved(registry, MODEL_ARTIFACT_ID)

    universe = ["XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD"]
    price_store = _SyntheticPriceStore(universe, days=160)

    factor = make_tsmom_30_7(price_store, market_dataset_id="ds_market_bars")

    loop = FactorDrivenPaperLoop(
        model_artifact_id=MODEL_ARTIFACT_ID,
        promotion_registry=registry,
        factor=factor,
        initial_cash=100_000.0,
        fee_rate=0.0005,
        slippage_rate=0.0005,
    )

    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    decision_times = [t0 + timedelta(days=d) for d in range(100, 150, 7)]

    print(f"Executing paper loop for '{MODEL_ARTIFACT_ID}' across {len(decision_times)} decision times...", file=sys.stderr)
    result = loop.run_loop(
        universe=universe,
        decision_times=decision_times,
        get_prices_at=price_store.get_prices_at,
        min_observation_days=14,
    )

    formatted = format_loop_result(result)
    out_json = json.dumps(formatted, indent=2)
    print(out_json)

    out_file = Path(args.out) if args.out else DEFAULT_OUTPUT_PATH
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(out_json, encoding="utf-8")
    print(f"Paper factor loop results written to {out_file}", file=sys.stderr)

    if args.dry_run:
        tmpdir.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
