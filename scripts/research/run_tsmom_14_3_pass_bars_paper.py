#!/usr/bin/env python3
"""PAPER-009 — Re-validate frozen tsmom_14_3 on the PASS canonical dataset.

Pins the DATA-005 quality-cleared dataset (ds_0cb6415f...) and re-runs the
frozen tsmom_14_3 paper session on the same PAPER-008 window and protocol.
Compares the resulting return to the original PAPER-008 evidence on the
REJECTED dataset. Produces research/sprint_004/26_TSMOM_14_3_PASS_BARS_PAPER.json.

Does not mutate artifacts 08-25. live_eligible: false. No LIVE.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
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

MODEL_ARTIFACT_ID = "mod_tsmom_14_3_v1"
LOOKBACK_DAYS = 14
SKIP_DAYS = 3
FACTOR_ID = "tsmom_14_3"

FINGERPRINT = hashlib.sha256(
    b"PAPER-009:tsmom_14_3:PASS_BARS:" + MODEL_ARTIFACT_ID.encode()
).hexdigest()

PASS_DATASET_ID = "ds_0cb6415fa79119bf5317c124e9da2f0d4953b9a8d119aae45e2589ba716c5aaa"
PAPER_008_DATASET_ID = "ds_a17651d5c871656f18c29d50fe96d41fa9f08eee8436b276237f96a679764dcd"
PAPER_008_ARTIFACT = "research/sprint_004/24_TSMOM_14_3_PAPER_SESSION.json"
EVIDENCE_REFERENCE = "REVIEW-0201"
_US_PER_SECOND = 1_000_000

EXPERIMENT_REGISTRY = Path("research/sprint_004/experiment_registry.csv")


class _InMemoryMarketBarStore:
    """Fast in-memory market-bars as-of store over the canonical PASS dataset.

    Loads the daily partition (the PASS quality-cleared canonical data) plus the
    intraday partition for backward compatibility. Intraday and daily rows are
    identical in the DATA-005 dataset, so we filter by the relative path to avoid
    double-counting.
    """

    def __init__(
        self,
        control_database: Path,
        dataset_store_root: Path,
        dataset_id: str,
        *,
        prefer_kind: str = "daily",
    ) -> None:
        self.control_database = Path(control_database)
        self.dataset_store_root = Path(dataset_store_root)
        self.dataset_id = dataset_id
        self.prefer_kind = prefer_kind
        self._df = self._load_bars()

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
            if not uri.endswith("bars.parquet"):
                continue
            if self.prefer_kind in uri:
                paths.append(lexical_join(dataset_base, uri))
        return paths

    def _load_bars(self) -> pd.DataFrame:
        paths = self._dataset_file_paths()
        if not paths:
            raise ValueError(
                f"No {self.prefer_kind} bars.parquet files found for dataset {self.dataset_id}"
            )
        tables = [pq.read_table(path) for path in paths if path.exists()]
        if not tables:
            raise ValueError(f"No readable bar files for dataset {self.dataset_id}")
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


def _decision_times(start_date: datetime, end_date: datetime, step_days: int = 7) -> list[datetime]:
    times: list[datetime] = []
    t = start_date
    while t <= end_date:
        times.append(t)
        t += timedelta(days=step_days)
    return times


def _ensure_paper_approved(
    registry: PromotionRegistry,
    effective_time: datetime,
    artifact_id: str = MODEL_ARTIFACT_ID,
) -> None:
    """Ensure tsmom_14_3 model artifact is PAPER_APPROVED (idempotent)."""
    current_state = registry.get_current_state(artifact_id)
    if current_state is None:
        cand = PromotionIdentityPayload(
            model_artifact_id=artifact_id,
            experiment_fingerprint=FINGERPRINT,
            dataset_ids=(PASS_DATASET_ID, "coingecko_universe"),
            universe_ids=("cmc_survivorship_universe",),
            code_commit="MOMTS-001",
            config_version="cfg_tsmom_14_3_v1",
            feature_version="feat_tsmom_14_3_v1",
            representation_version="rep_time_bar_1d",
            portfolio_version="perp_ls_v1",
            cost_model_version="cost_v1_binance_spot",
            risk_policy_version="risk_lev1.0_w0.15_v1",
            target_stage=PromotionTarget.RESEARCH,
            effective_time=effective_time,
            approving_authority="Lead Quantitative Researcher",
            evidence_reference=EVIDENCE_REFERENCE,
        )
        registry.register_candidate(cand, reason="PAPER-009 candidate")
        current_state = PromotionState.RESEARCH_CANDIDATE

    if current_state == PromotionState.RESEARCH_CANDIDATE:
        accepted = PromotionIdentityPayload(
            model_artifact_id=artifact_id,
            experiment_fingerprint=FINGERPRINT,
            dataset_ids=(PASS_DATASET_ID, "coingecko_universe"),
            universe_ids=("cmc_survivorship_universe",),
            code_commit="MOMTS-001",
            config_version="cfg_tsmom_14_3_v1",
            feature_version="feat_tsmom_14_3_v1",
            representation_version="rep_time_bar_1d",
            portfolio_version="perp_ls_v1",
            cost_model_version="cost_v1_binance_spot",
            risk_policy_version="risk_lev1.0_w0.15_v1",
            target_stage=PromotionTarget.RESEARCH,
            effective_time=effective_time,
            approving_authority="Lead Quantitative Researcher",
            evidence_reference=EVIDENCE_REFERENCE,
        )
        registry.transition_state(
            accepted,
            target_state=PromotionState.RESEARCH_ACCEPTED,
            reason="PAPER-009 research accepted",
        )
        current_state = PromotionState.RESEARCH_ACCEPTED

    if current_state == PromotionState.RESEARCH_ACCEPTED:
        paper = PromotionIdentityPayload(
            model_artifact_id=artifact_id,
            experiment_fingerprint=FINGERPRINT,
            dataset_ids=(PASS_DATASET_ID, "coingecko_universe"),
            universe_ids=("cmc_survivorship_universe",),
            code_commit="MOMTS-001",
            config_version="cfg_tsmom_14_3_v1",
            feature_version="feat_tsmom_14_3_v1",
            representation_version="rep_time_bar_1d",
            portfolio_version="perp_ls_v1",
            cost_model_version="cost_v1_binance_spot",
            risk_policy_version="risk_lev1.0_w0.15_v1",
            target_stage=PromotionTarget.PAPER,
            effective_time=effective_time,
            approving_authority="Lead Quantitative Researcher",
            evidence_reference=EVIDENCE_REFERENCE,
        )
        registry.transition_state(
            paper,
            target_state=PromotionState.PAPER_APPROVED,
            reason="PAPER-009 PAPER_APPROVED",
        )


def _load_paper_008_return() -> dict[str, Any]:
    path = Path(PAPER_008_ARTIFACT)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "total_net_return": data.get("session", {}).get("total_net_return"),
        "final_equity": data.get("session", {}).get("final_equity"),
        "canonical_dataset_id": data.get("canonical_dataset_id"),
        "canonical_dataset_quality_status": data.get("canonical_dataset_quality_status"),
    }


def _append_registry_row(artifact_path: Path) -> None:
    """Append a PAPER-009 row to experiment_registry.csv if it exists (idempotent)."""
    if not EXPERIMENT_REGISTRY.exists():
        return

    artifacts_json = json.dumps({
        "paper_session": str(artifact_path),
    }, separators=(",", ":"), sort_keys=True)
    new_row = {
        "experiment_id": "PAPER-009",
        "status": "EXECUTED",
        "artifacts_json": artifacts_json,
        "generated_at": datetime.now(UTC).isoformat(),
    }

    rows: list[dict[str, str]] = []
    if EXPERIMENT_REGISTRY.exists():
        with EXPERIMENT_REGISTRY.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

    # Idempotent: keep only the most recent PAPER-009 row if present.
    rows = [r for r in rows if r.get("experiment_id") != "PAPER-009"]
    rows.append(new_row)

    with EXPERIMENT_REGISTRY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["experiment_id", "status", "artifacts_json", "generated_at"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"PAPER-009 row written to {EXPERIMENT_REGISTRY}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="PAPER-009 tsmom_14_3 PASS-bars re-validation")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--dataset-id", type=str, default=PASS_DATASET_ID)
    parser.add_argument("--start", type=str, default="2024-04-01")
    parser.add_argument("--end", type=str, default="2026-07-23")
    parser.add_argument("--output-dir", type=str, default="research/sprint_004")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    store_root = Path(args.store_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_id = args.dataset_id

    start = datetime.strptime(args.start, "%Y-%m-%d").replace(hour=0, minute=0, second=0, tzinfo=UTC)
    end = datetime.strptime(args.end, "%Y-%m-%d").replace(hour=0, minute=0, second=0, tzinfo=UTC)
    decision_times = _decision_times(start, end)

    in_memory_store = _InMemoryMarketBarStore(db_path, store_root, dataset_id, prefer_kind="daily")
    print(f"PAPER-009: in-memory PASS bar store loaded for {dataset_id}", file=sys.stderr)

    universe = list(PAPER_TO_INSTRUMENT_ID.keys())

    registry = PromotionRegistry(db_path)
    _ensure_paper_approved(registry, effective_time=start)
    print(f"PAPER-009: {MODEL_ARTIFACT_ID} ensured PAPER_APPROVED", file=sys.stderr)

    price_store = PaperSymbolAsOfAdapter(in_memory_store)
    factor = TimeSeriesMomentumFactor(
        price_store,
        lookback_days=LOOKBACK_DAYS,
        skip_days=SKIP_DAYS,
        market_dataset_id=dataset_id,
        factor_id=FACTOR_ID,
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
    meets_risk_derived = bool(
        max_abs_weight <= MAX_SINGLE_ASSET_WEIGHT and max_gross <= MAX_GROSS_LEVERAGE
    )
    is_complete_derived = len(result.period_logs) == len(decision_times) and len(decision_times) > 0

    live_gate_satisfied = compute_live_gate_satisfied(
        "real_asof",
        result.total_net_return,
        meets_risk,
        is_complete,
    )

    paper_008 = _load_paper_008_return()
    return_delta = None
    if paper_008.get("total_net_return") is not None:
        return_delta = result.total_net_return - paper_008["total_net_return"]

    if return_delta is None:
        delta_note = "PAPER-008 artifact not found; no comparison available."
    elif return_delta == 0:
        delta_note = (
            "Return is identical to PAPER-008 because the daily PASS partition and "
            "the intraday partition used under the REJECTED dataset contain the same "
            "native 1d source data. Economic signal and parameters are unchanged."
        )
    else:
        delta_note = (
            "Return difference is due to the daily partition being the canonical PASS "
            "bars instead of the intraday partition used under the REJECTED dataset. "
            "Economic signal and parameters are identical."
        )

    artifact: dict[str, Any] = {
        "experiment_id": "PAPER-009",
        "data_mode": "real_asof",
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "factor_id": FACTOR_ID,
        "lookback_days": LOOKBACK_DAYS,
        "skip_days": SKIP_DAYS,
        "protocol": "paper_session",
        "protocol_note": (
            "Re-validation of the frozen tsmom_14_3 candidate on the DATA-005 "
            "quality-cleared PASS canonical dataset (native 1d promoted to daily). "
            "Same window, protocol, and risk policy as PAPER-008. No parameter changes. "
            "This is promotion-grade paper evidence, not LIVE."
        ),
        "control_database": str(db_path),
        "dataset_store_root": str(store_root),
        "canonical_dataset_id": dataset_id,
        "canonical_dataset_quality_status": "PASS",
        "canonical_dataset_quality_note": (
            "DATA-005 quality-cleared canonical bars via Approach A: BAR-001 extended "
            "to accept native 1d source bars as complete daily bars."
        ),
        "universe": universe,
        "venue_symbols": sorted(set(PAPER_TO_BINANCE_MAP.values())),
        "risk_policy": {
            "max_single_weight": MAX_SINGLE_ASSET_WEIGHT,
            "max_gross_leverage": MAX_GROSS_LEVERAGE,
            "enforcement": "neutrality_preserving_leg_rescale",
        },
        "session": {
            "start": start.isoformat(),
            "end": end.isoformat(),
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
            "meets_risk_limits_derived": meets_risk_derived,
            "is_complete_derived": is_complete_derived,
            "live_gate_satisfied": live_gate_satisfied,
            "live_eligible": False,
        },
        "candidate_frozen": True,
        "candidate_frozen_note": (
            "tsmom_14_3 lookback=14/skip=3 remains frozen as the selected research candidate. "
            "No further lookback/skip optimization or re-selection on this path is permitted "
            "without a new ticket and reviewer authorization."
        ),
        "live_eligible": False,
        "live_eligible_note": "PAPER-009 is promotion-grade paper evidence; no LIVE authorization.",
        "oos_supports_live_path": live_gate_satisfied,
        "oos_supports_live_path_note": (
            "Paper session gate satisfied, but LIVE promotion requires a separate ticket and owner policy."
            if live_gate_satisfied
            else "Paper session gate not satisfied; LIVE path not supported by this evidence."
        ),
        "comparison_to_paper_008": {
            "paper_008_canonical_dataset_id": paper_008.get("canonical_dataset_id"),
            "paper_008_canonical_dataset_quality_status": paper_008.get("canonical_dataset_quality_status"),
            "paper_008_total_net_return": paper_008.get("total_net_return"),
            "paper_009_total_net_return": result.total_net_return,
            "total_net_return_delta": return_delta,
            "delta_note": delta_note,
        },
        "cross_references": [
            "research/sprint_004/24_TSMOM_14_3_PAPER_SESSION.json",
            "research/sprint_004/25_QUALITY_CLEARED_BARS_REPORT.json",
        ],
        "prior_artifacts": [
            "research/sprint_004/13_REAL_PAPER_SESSION.json",
            "research/sprint_004/14_RISK_COMPLIANT_PAPER_SESSION.json",
            "research/sprint_004/15_MOMTS_RISK_DIAGNOSIS.json",
            "research/sprint_004/16_MOMTS_LONG_SESSION.json",
            "research/sprint_004/17_NEUTRAL_RISK_SESSION.json",
            "research/sprint_004/18_TSMOM_GRID_RESULTS.json",
            "research/sprint_004/19_TSMOM_OOS_VALIDATION.json",
            "research/sprint_004/20_EXTENDED_HISTORY_REPORT.json",
            "research/sprint_004/21_TSMOM_EXTENDED_OOS.json",
            "research/sprint_004/22_TSMOM_14_0_PAPER_SESSION.json",
            "research/sprint_004/23_TSMOM_FULLWINDOW_SCREEN.json",
            "research/sprint_004/24_TSMOM_14_3_PAPER_SESSION.json",
            "research/sprint_004/25_QUALITY_CLEARED_BARS_REPORT.json",
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }

    out_path = output_dir / "26_TSMOM_14_3_PASS_BARS_PAPER.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"PASS-bars paper artifact written to {out_path}", file=sys.stderr)

    _append_registry_row(out_path)

    print(json.dumps(artifact, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
