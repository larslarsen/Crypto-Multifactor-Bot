#!/usr/bin/env python3
"""EXP-005 — Holdout OOS / walk-forward validation of top TSMOM configs.

Protocol:
- Train fold: 2025-08-08 → 2026-01-10 (weekly decisions) on the real backfill.
- Select top-3 in-sample risk-compliant profitable configs.
- Test fold: 2026-01-17 → 2026-07-23 (weekly decisions) on the same backfill.
- Evaluate frozen top-3 + baseline `tsmom_30_7` on the test fold.
- ALLOC-001 risk enforcement (0.15 / 1.0) throughout.

Do not mutate artifacts 08–17. Produces only 19_TSMOM_OOS_VALIDATION.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.paths import lexical_join
from cryptofactors.execution.live import MAX_GROSS_LEVERAGE, MAX_SINGLE_ASSET_WEIGHT
from cryptofactors.execution.paper_loop import FactorDrivenPaperLoop
from cryptofactors.execution.risk_limits import compute_live_gate_satisfied
from cryptofactors.execution.symbols import (
    PAPER_TO_BINANCE_MAP,
    PAPER_TO_INSTRUMENT_ID,
    PaperSymbolAsOfAdapter,
)
from cryptofactors.factors.tsmom import TimeSeriesMomentumFactor
from cryptofactors.portfolio.perpetual_simulation import LongShortRankAllocator
from cryptofactors.promotion import (
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)

UTC = timezone.utc
MODEL_ARTIFACT_ID = "mod_tsmom_30_7_v1"
FINGERPRINT = "87469a44a18449bee23de76b1312413fd3e5a649a6677e3509a8c270caea3318"
_US_PER_SECOND = 1_000_000

DEFAULT_LOOKBACKS = [7, 14, 30, 60, 90]
DEFAULT_SKIPS = [0, 3, 7]


class _InMemoryMarketBarStore:
    """Fast in-memory market-bars as-of store over the canonical dataset."""

    def __init__(self, control_database: Path, dataset_store_root: Path, dataset_id: str) -> None:
        self.control_database = Path(control_database)
        self.dataset_store_root = Path(dataset_store_root)
        self.dataset_id = dataset_id
        self._df = self._load_intraday_bars()

    def _dataset_file_paths(self) -> list[Path]:
        cat = SqliteDatasetCatalog(self.control_database)
        try:
            files = list(cat.list_files(self.dataset_id))
            ds_row = cat.get_dataset(self.dataset_id)
        finally:
            cat.close()

        root = self.dataset_store_root.expanduser()
        if not root.is_absolute():
            root = Path.cwd() / root

        dataset_base = root
        if ds_row is not None:
            manifest_uri = str(ds_row.get("manifest_uri") or "")
            if manifest_uri:
                dataset_dir = str(Path(manifest_uri).parent)
                dataset_base = lexical_join(root, dataset_dir)

        paths: list[Path] = []
        for f in files:
            uri = str(f.get("storage_uri") or "")
            if "intraday" not in uri or not uri:
                continue
            paths.append(lexical_join(dataset_base, uri))
        return paths

    def _load_intraday_bars(self) -> pd.DataFrame:
        paths = self._dataset_file_paths()
        tables = [pq.read_table(path) for path in paths if path.exists()]
        table = pa.concat_tables(tables, promote_options="default")
        df = table.to_pandas()
        required = {"instrument_id", "period_start", "availability_time", "close"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Dataset missing columns: {missing}")
        return df

    def latest_available(
        self,
        dataset_id: str,
        keys: Any,
        fields: Any,
        decision_time: datetime,
        max_age: Any = None,
    ) -> Any:
        if dataset_id != self.dataset_id:
            raise ValueError(f"This store only supports dataset {self.dataset_id}")
        t_us = int(_require_utc(decision_time).timestamp() * _US_PER_SECOND)
        key_set = {int(k) for k in keys}
        min_availability_us: int | None = None
        if max_age is not None:
            min_availability_us = t_us - int(max_age.total_seconds() * _US_PER_SECOND)

        df = self._df
        mask = (
            df["instrument_id"].isin(key_set)
            & (df["availability_time"] <= t_us)
            & (df["period_start"] <= t_us)
        )
        if min_availability_us is not None:
            mask &= df["availability_time"] >= min_availability_us
        eligible = df.loc[mask]
        if eligible.empty:
            return self._empty_table(fields)

        eligible = eligible.sort_values(["instrument_id", "period_start", "availability_time"])
        latest = eligible.groupby("instrument_id").tail(1)
        return self._project(latest, fields)

    def as_of(
        self,
        dataset_id: str,
        keys: Any,
        fields: Any,
        decision_time: datetime,
        knowledge_time: Any = None,
    ) -> Any:
        return self.latest_available(dataset_id, keys, fields, decision_time)

    def _project(self, df: pd.DataFrame, fields: Any) -> pa.Table:
        cols = [c for c in list(fields) if c in df.columns]
        if not cols:
            cols = ["instrument_id"]
        return pa.Table.from_pandas(df[cols])

    def _empty_table(self, fields: Any) -> pa.Table:
        cols = list(fields) if fields else ["instrument_id"]
        return pa.Table.from_arrays([pa.array([], type=pa.null()) for _ in cols], names=cols)


def _require_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(UTC)


def _ensure_paper_approved(registry: PromotionRegistry, artifact_id: str = MODEL_ARTIFACT_ID) -> None:
    current_state = registry.get_current_state(artifact_id)
    if current_state is None:
        cand = PromotionIdentityPayload(
            model_artifact_id=artifact_id,
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
            effective_time=datetime(2026, 4, 1, tzinfo=UTC),
            approving_authority="Lead Quantitative Researcher",
            evidence_reference="REVIEW-0174",
        )
        registry.register_candidate(cand, reason="EXP-005 candidate")
        current_state = PromotionState.RESEARCH_CANDIDATE

    if current_state == PromotionState.RESEARCH_CANDIDATE:
        accepted = PromotionIdentityPayload(
            model_artifact_id=artifact_id,
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
            effective_time=datetime(2026, 4, 1, tzinfo=UTC),
            approving_authority="Lead Quantitative Researcher",
            evidence_reference="REVIEW-0174",
        )
        registry.transition_state(
            accepted,
            target_state=PromotionState.RESEARCH_ACCEPTED,
            reason="EXP-005 accepted",
        )
        current_state = PromotionState.RESEARCH_ACCEPTED

    if current_state == PromotionState.RESEARCH_ACCEPTED:
        paper = PromotionIdentityPayload(
            model_artifact_id=artifact_id,
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
            effective_time=datetime(2026, 4, 1, tzinfo=UTC),
            approving_authority="Lead Quantitative Researcher",
            evidence_reference="REVIEW-0177",
        )
        registry.transition_state(
            paper,
            target_state=PromotionState.PAPER_APPROVED,
            reason="EXP-005 PAPER_APPROVED",
        )


def _decision_times(start_date: datetime, end_date: datetime, step_days: int = 7) -> list[datetime]:
    times: list[datetime] = []
    t = start_date
    while t <= end_date:
        times.append(t)
        t += timedelta(days=step_days)
    return times


def _run_config(
    lookback_days: int,
    skip_days: int,
    db_path: Path,
    dataset_id: str,
    universe: list[str],
    decision_times: list[datetime],
    in_memory_store: _InMemoryMarketBarStore,
) -> dict[str, Any]:
    factor_id = f"tsmom_{lookback_days}_{skip_days}"
    price_store = PaperSymbolAsOfAdapter(in_memory_store)
    registry = PromotionRegistry(db_path)
    _ensure_paper_approved(registry)

    factor = TimeSeriesMomentumFactor(
        price_store,
        lookback_days=lookback_days,
        skip_days=skip_days,
        market_dataset_id=dataset_id,
        factor_id=factor_id,
    )
    allocator = LongShortRankAllocator(target_leverage=1.0)
    loop = FactorDrivenPaperLoop(
        model_artifact_id=MODEL_ARTIFACT_ID,
        promotion_registry=registry,
        factor=factor,
        allocator=allocator,
        initial_cash=100_000.0,
        fee_rate=0.0005,
        slippage_rate=0.0005,
        max_single_weight=MAX_SINGLE_ASSET_WEIGHT,
        max_gross_leverage=MAX_GROSS_LEVERAGE,
    )

    def get_prices(dt: datetime, univ: Any) -> dict[str, float]:
        res: dict[str, float] = {}
        for sym in universe:
            int_key = PAPER_TO_INSTRUMENT_ID[sym]
            tbl = in_memory_store.latest_available(dataset_id, [int_key], ["close"], dt)
            if tbl is not None and tbl.num_rows > 0:
                res[sym] = float(tbl.column("close")[0].as_py())
        return res

    result = loop.run_loop(
        universe=universe,
        decision_times=decision_times,
        get_prices_at=get_prices,
        min_observation_days=14,
    )

    net_exposures = [sum(log.target_weights.values()) for log in result.period_logs]
    max_abs_net = max((abs(n) for n in net_exposures), default=0.0)
    avg_abs_net = sum(abs(n) for n in net_exposures) / max(len(net_exposures), 1)
    max_abs_weight = max(
        (max((abs(w) for w in log.target_weights.values()), default=0.0) for log in result.period_logs),
        default=0.0,
    )
    gross_per_period = [sum(abs(w) for w in log.target_weights.values()) for log in result.period_logs]
    max_gross = max(gross_per_period, default=0.0)
    avg_gross = sum(gross_per_period) / max(len(gross_per_period), 1)

    obs = result.observation_result
    meets_risk = bool(obs.meets_risk_limits) if obs else False
    is_complete = bool(obs.is_complete) if obs else False
    live_gate_satisfied = compute_live_gate_satisfied(
        "real_asof",
        result.total_net_return,
        meets_risk,
        is_complete,
    )

    return {
        "lookback_days": lookback_days,
        "skip_days": skip_days,
        "factor_id": factor_id,
        "decision_count": len(result.period_logs),
        "total_trades_executed": result.total_trades_executed,
        "initial_cash": result.initial_cash,
        "final_equity": result.final_equity,
        "total_net_return": result.total_net_return,
        "max_abs_single_weight": max_abs_weight,
        "max_gross_leverage": max_gross,
        "avg_gross_leverage": avg_gross,
        "max_abs_net_exposure": max_abs_net,
        "avg_abs_net_exposure": avg_abs_net,
        "meets_risk_limits": meets_risk,
        "is_complete": is_complete,
        "live_gate_satisfied": live_gate_satisfied,
        "live_eligible": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="EXP-005 TSMOM OOS validation")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--dataset-id", type=str, default="")
    parser.add_argument("--train-start", type=str, default="2026-04-08")
    parser.add_argument("--train-end", type=str, default="2026-05-31")
    parser.add_argument("--test-start", type=str, default="2026-06-07")
    parser.add_argument("--test-end", type=str, default="2026-07-23")
    parser.add_argument("--output-dir", type=str, default="research/sprint_004")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    store_root = Path(args.store_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_start = datetime.strptime(args.train_start, "%Y-%m-%d").replace(tzinfo=UTC)
    train_end = datetime.strptime(args.train_end, "%Y-%m-%d").replace(tzinfo=UTC)
    test_start = datetime.strptime(args.test_start, "%Y-%m-%d").replace(tzinfo=UTC)
    test_end = datetime.strptime(args.test_end, "%Y-%m-%d").replace(tzinfo=UTC)

    train_decisions = _decision_times(train_start, train_end)
    test_decisions = _decision_times(test_start, test_end)

    if not args.dataset_id:
        cat = SqliteDatasetCatalog(db_path)
        try:
            dataset_id = cat.resolve_latest_by_type("market_bars")
        finally:
            cat.close()
        if dataset_id is None:
            raise RuntimeError("No canonical market_bars dataset found")
    else:
        dataset_id = args.dataset_id

    print(
        f"EXP-005: train={len(train_decisions)} decisions, test={len(test_decisions)} decisions, dataset={dataset_id}",
        file=sys.stderr,
    )
    in_memory_store = _InMemoryMarketBarStore(db_path, store_root, dataset_id)
    print("In-memory bar store loaded", file=sys.stderr)

    universe = list(PAPER_TO_INSTRUMENT_ID.keys())

    # In-sample train-fold grid to select top-K.
    print("Running train-fold grid for selection...", file=sys.stderr)
    train_results: list[dict[str, Any]] = []
    for lookback in DEFAULT_LOOKBACKS:
        for skip in DEFAULT_SKIPS:
            if lookback <= skip:
                continue
            cell = _run_config(
                lookback,
                skip,
                db_path,
                dataset_id,
                universe,
                train_decisions,
                in_memory_store,
            )
            train_results.append(cell)

    # Select top-3 risk-compliant profitable configs.
    eligible = [c for c in train_results if c["live_gate_satisfied"]]
    eligible.sort(key=lambda c: c["total_net_return"], reverse=True)
    top3 = eligible[:3]
    top3_configs = [(c["lookback_days"], c["skip_days"]) for c in top3]
    print(f"Selected top-3 configs: {top3_configs}", file=sys.stderr)

    # Always include baseline tsmom_30_7.
    baseline = (30, 7)
    test_configs = list(top3_configs)
    if baseline not in test_configs:
        test_configs.append(baseline)

    # Test-fold evaluation.
    print("Running test-fold evaluation...", file=sys.stderr)
    test_results: list[dict[str, Any]] = []
    for lookback, skip in test_configs:
        cell = _run_config(
            lookback,
            skip,
            db_path,
            dataset_id,
            universe,
            test_decisions,
            in_memory_store,
        )
        test_results.append(cell)

    # Ranking on test fold.
    ranked = sorted(test_results, key=lambda c: (not c["live_gate_satisfied"], -c["total_net_return"]))
    any_test_gate = any(c["live_gate_satisfied"] for c in test_results)

    artifact: dict[str, Any] = {
        "experiment_id": "EXP-005",
        "data_mode": "real_asof",
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "protocol": "holdout_split",
        "protocol_note": "Top-3 configs selected in-sample on train fold; frozen configs evaluated out-of-sample on test fold. No lookback/skip optimization on test fold. Split dates are chosen to fit the available real backfill window (2026-01-01 -> 2026-07-23) and the longest lookback (90 days + skip).", 
        "control_database": str(db_path),
        "dataset_store_root": str(store_root),
        "canonical_dataset_id": dataset_id,
        "universe": universe,
        "venue_symbols": sorted(set(PAPER_TO_BINANCE_MAP.values())),
        "risk_policy": {
            "max_single_weight": MAX_SINGLE_ASSET_WEIGHT,
            "max_gross_leverage": MAX_GROSS_LEVERAGE,
            "enforcement": "neutrality_preserving_leg_rescale",
        },
        "train_fold": {
            "start": train_start.isoformat(),
            "end": train_end.isoformat(),
            "decision_count": len(train_decisions),
            "grid_results": train_results,
        },
        "test_fold": {
            "start": test_start.isoformat(),
            "end": test_end.isoformat(),
            "decision_count": len(test_decisions),
            "evaluation_results": test_results,
            "ranking": [
                {
                    "rank": i + 1,
                    "lookback_days": c["lookback_days"],
                    "skip_days": c["skip_days"],
                    "factor_id": c["factor_id"],
                    "total_net_return": c["total_net_return"],
                    "meets_risk_limits": c["meets_risk_limits"],
                    "live_gate_satisfied": c["live_gate_satisfied"],
                }
                for i, c in enumerate(ranked)
            ],
            "best_config": ranked[0],
        },
        "oos_supports_live_path": any_test_gate,
        "oos_supports_live_path_note": (
            "At least one frozen config passed the test-fold gate, but LIVE promotion requires a separate ticket and owner policy."
            if any_test_gate
            else "No frozen config passed the test-fold gate; LIVE path not supported by this evidence."
        ),
        "live_eligible": False,
        "prior_artifacts": [
            "research/sprint_004/13_REAL_PAPER_SESSION.json",
            "research/sprint_004/14_RISK_COMPLIANT_PAPER_SESSION.json",
            "research/sprint_004/15_MOMTS_RISK_DIAGNOSIS.json",
            "research/sprint_004/16_MOMTS_LONG_SESSION.json",
            "research/sprint_004/17_NEUTRAL_RISK_SESSION.json",
            "research/sprint_004/18_TSMOM_GRID_RESULTS.json",
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }

    out_path = output_dir / "19_TSMOM_OOS_VALIDATION.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"OOS validation artifact written to {out_path}", file=sys.stderr)
    print(json.dumps(artifact, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
