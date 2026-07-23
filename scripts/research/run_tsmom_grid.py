#!/usr/bin/env python3
"""EXP-004 — TSMOM lookback/skip grid under ALLOC-001 neutrality-preserving risk.

Reuses the EXP-003/ALLOC-001 real backfill (exp003.db + data/exp003_store) and
runs risk-enforced paper sessions for each (lookback, skip) cell. Produces
18_TSMOM_GRID_RESULTS.json with per-cell metrics, ranking, and recommendation.
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


def _require_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(UTC)


def _dt_to_us(dt: datetime) -> int:
    return int(_require_utc(dt).timestamp() * _US_PER_SECOND)


class _InMemoryMarketBarStore:
    """Fast in-memory market-bars as-of store.

    Loads the intraday Parquet files of a canonical market_bars dataset once and
    answers ``latest_available`` queries by filtering the DataFrame in memory.
    """

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
            if "intraday" not in uri:
                continue
            if not uri:
                continue
            paths.append(lexical_join(dataset_base, uri))
        return paths

    def _load_intraday_bars(self) -> pd.DataFrame:
        paths = self._dataset_file_paths()
        tables: list[pa.Table] = []
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"Missing parquet: {path}")
            tables.append(pq.read_table(path))
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
        t_us = _dt_to_us(decision_time)
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

        # Keep the row with max (period_start, availability_time) per instrument_id.
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
        # Not used by TSMOM factor; implement trivially.
        return self.latest_available(dataset_id, keys, fields, decision_time)

    def _project(self, df: pd.DataFrame, fields: Any) -> pa.Table:
        cols = list(fields) if fields else list(df.columns)
        cols = [c for c in cols if c in df.columns]
        if not cols:
            cols = ["instrument_id"]
        return pa.Table.from_pandas(df[cols])

    def _empty_table(self, fields: Any) -> pa.Table:
        cols = list(fields) if fields else ["instrument_id"]
        arrays = [pa.array([], type=pa.null()) for _ in cols]
        return pa.Table.from_arrays(arrays, names=cols)


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
        registry.register_candidate(cand, reason="EXP-004 candidate")
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
            reason="EXP-004 accepted",
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
            reason="EXP-004 PAPER_APPROVED",
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
    store_root: Path,
    dataset_id: str,
    universe: list[str],
    decision_times: list[datetime],
    in_memory_store: _InMemoryMarketBarStore,
) -> dict[str, Any]:
    """Run one grid cell."""
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
    parser = argparse.ArgumentParser(description="EXP-004 TSMOM lookback/skip grid")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--dataset-id", type=str, default="")
    parser.add_argument("--session-start", type=str, default="2025-08-08")
    parser.add_argument("--session-end", type=str, default="2026-07-23")
    parser.add_argument("--lookbacks", type=str, default="7,14,30,60,90")
    parser.add_argument("--skips", type=str, default="0,3,7")
    parser.add_argument("--output-dir", type=str, default="research/sprint_004")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    store_root = Path(args.store_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    session_start = datetime.strptime(args.session_start, "%Y-%m-%d").replace(tzinfo=UTC)
    session_end = datetime.strptime(args.session_end, "%Y-%m-%d").replace(tzinfo=UTC)
    decision_times = _decision_times(session_start, session_end)

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

    print(f"EXP-004: using dataset {dataset_id}, {len(decision_times)} decisions", file=sys.stderr)
    in_memory_store = _InMemoryMarketBarStore(db_path, store_root, dataset_id)
    print("In-memory bar store loaded", file=sys.stderr)

    universe = list(PAPER_TO_INSTRUMENT_ID.keys())
    lookbacks = [int(x) for x in args.lookbacks.split(",") if x.strip()]
    skips = [int(x) for x in args.skips.split(",") if x.strip()]

    cells: list[dict[str, Any]] = []
    for lookback in lookbacks:
        for skip in skips:
            if lookback <= skip:
                print(f"Skipping invalid config lookback={lookback} skip={skip}", file=sys.stderr)
                continue
            print(f"Running tsmom_{lookback}_{skip}...", file=sys.stderr)
            cell = _run_config(
                lookback,
                skip,
                db_path,
                store_root,
                dataset_id,
                universe,
                decision_times,
                in_memory_store,
            )
            cells.append(cell)

    # Ranking by total_net_return, with risk-compliant configs first.
    ranked = sorted(cells, key=lambda c: (not c["meets_risk_limits"], -c["total_net_return"]))
    best = ranked[0]
    recommend_live = best["live_gate_satisfied"]

    artifact: dict[str, Any] = {
        "experiment_id": "EXP-004",
        "data_mode": "real_asof",
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "control_database": str(db_path),
        "dataset_store_root": str(store_root),
        "canonical_dataset_id": dataset_id,
        "universe": universe,
        "venue_symbols": sorted(set(PAPER_TO_BINANCE_MAP.values())),
        "session_start": session_start.isoformat(),
        "session_end": session_end.isoformat(),
        "decision_count": len(decision_times),
        "risk_policy": {
            "max_single_weight": MAX_SINGLE_ASSET_WEIGHT,
            "max_gross_leverage": MAX_GROSS_LEVERAGE,
            "enforcement": "neutrality_preserving_leg_rescale",
        },
        "grid_results": cells,
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
        "best_config": {
            "lookback_days": best["lookback_days"],
            "skip_days": best["skip_days"],
            "factor_id": best["factor_id"],
            "total_net_return": best["total_net_return"],
            "max_abs_single_weight": best["max_abs_single_weight"],
            "max_gross_leverage": best["max_gross_leverage"],
            "max_abs_net_exposure": best["max_abs_net_exposure"],
            "meets_risk_limits": best["meets_risk_limits"],
            "live_gate_satisfied": best["live_gate_satisfied"],
        },
        "recommend_live_path": recommend_live,
        "recommendation_note": (
            "No TSMOM lookback/skip configuration on this real window is both risk-compliant and profitable, "
            "so the family should be redesigned before any LIVE promotion is considered."
            if not recommend_live
            else "At least one configuration is risk-compliant and profitable, but LIVE promotion still requires a separate ticket and owner policy."
        ),
        "live_eligible": False,
        "prior_sessions": [
            "research/sprint_004/13_REAL_PAPER_SESSION.json",
            "research/sprint_004/14_RISK_COMPLIANT_PAPER_SESSION.json",
            "research/sprint_004/15_MOMTS_RISK_DIAGNOSIS.json",
            "research/sprint_004/16_MOMTS_LONG_SESSION.json",
            "research/sprint_004/17_NEUTRAL_RISK_SESSION.json",
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }

    out_path = output_dir / "18_TSMOM_GRID_RESULTS.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Grid results written to {out_path}", file=sys.stderr)
    print(json.dumps(artifact, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
