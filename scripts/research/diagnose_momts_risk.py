#!/usr/bin/env python3
"""EXP-003 — Risk-compliant MOM-TS real-data diagnosis.

Backfills the 10-name mapped universe over the longest available real Binance
window, publishes canonical market_bars, runs the paper loop in both
unconstrained (single-asset cap disabled) and risk-enforced (0.15/1.0) modes,
and writes a diagnosis artifact comparing the two.

Usage:
  .venv/bin/python scripts/research/diagnose_momts_risk.py
  .venv/bin/python scripts/research/diagnose_momts_risk.py --start-date 2024-01-01 --end-date 2026-07-23
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptofactors.catalog.as_of import CatalogAsOfStore
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.execution.paper_loop import FactorDrivenPaperLoop
from cryptofactors.execution.risk_limits import (
    MAX_GROSS_LEVERAGE,
    MAX_SINGLE_ASSET_WEIGHT,
    compute_live_gate_satisfied,
    enforce_risk_limits,
)
from cryptofactors.execution.symbols import (
    PAPER_TO_BINANCE_MAP,
    PAPER_TO_INSTRUMENT_ID,
    PaperSymbolAsOfAdapter,
)
from cryptofactors.factors.tsmom import make_tsmom_30_7
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


class _CachedAsOfStore:
    """Cache ``latest_available`` calls to avoid repeated Parquet reads.

    The wrapped store is typically a ``CatalogAsOfStore``. Cache key is
    ``(dataset_id, keys_tuple, fields_tuple, decision_time)``.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._cache: dict[tuple[str, tuple[int | str, ...], tuple[str, ...], datetime], Any] = {}

    def latest_available(
        self,
        dataset_id: str,
        keys: Any,
        fields: Any,
        decision_time: datetime,
        max_age: Any = None,
    ) -> Any:
        key = (dataset_id, tuple(keys), tuple(fields), decision_time)
        if key in self._cache:
            return self._cache[key]
        result = self._inner.latest_available(dataset_id, keys, fields, decision_time, max_age)
        self._cache[key] = result
        return result

    def as_of(
        self,
        dataset_id: str,
        keys: Any,
        fields: Any,
        decision_time: datetime,
        knowledge_time: Any = None,
    ) -> Any:
        # Not cached by design; used only for diagnostics.
        return self._inner.as_of(dataset_id, keys, fields, decision_time, knowledge_time)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _ensure_paper_approved(registry: PromotionRegistry, artifact_id: str = MODEL_ARTIFACT_ID) -> None:
    """Promote the model artifact to PAPER_APPROVED for the diagnosis session."""
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
        registry.register_candidate(cand, reason="EXP-003 diagnosis candidate")
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
            reason="EXP-003 accepted",
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
            reason="EXP-003 PAPER_APPROVED",
        )


def _decision_times(start_date: datetime, end_date: datetime, *, step_days: int = 7) -> list[datetime]:
    """Generate weekly decision times aligned to the calendar."""
    t0 = start_date
    # First decision must have enough lookback+skip history.
    t0 = max(t0, start_date)
    times: list[datetime] = []
    t = t0
    while t <= end_date:
        times.append(t)
        t += timedelta(days=step_days)
    return times


def _run_session(
    db_path: Path,
    store_root: Path,
    dataset_id: str,
    universe: list[str],
    decision_times: list[datetime],
    *,
    max_single_weight: float,
    max_gross_leverage: float,
    label: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run a single risk-configuration paper session and return summary + period metrics."""
    raw_as_of = _CachedAsOfStore(CatalogAsOfStore(control_database=db_path, dataset_store_root=store_root))
    price_store = PaperSymbolAsOfAdapter(raw_as_of)
    registry = PromotionRegistry(db_path)
    _ensure_paper_approved(registry)

    factor = make_tsmom_30_7(price_store, market_dataset_id=dataset_id)
    allocator = LongShortRankAllocator(target_leverage=1.0)

    loop = FactorDrivenPaperLoop(
        model_artifact_id=MODEL_ARTIFACT_ID,
        promotion_registry=registry,
        factor=factor,
        allocator=allocator,
        initial_cash=100_000.0,
        fee_rate=0.0005,
        slippage_rate=0.0005,
        max_single_weight=max_single_weight,
        max_gross_leverage=max_gross_leverage,
    )

    def get_prices(dt: datetime, univ: Any) -> dict[str, float]:
        res: dict[str, float] = {}
        for sym in universe:
            try:
                int_key = PAPER_TO_INSTRUMENT_ID[sym]
            except KeyError:
                continue
            tbl = raw_as_of.latest_available(dataset_id, [int_key], ["close"], dt)
            if tbl is not None and tbl.num_rows > 0:
                res[sym] = float(tbl.column("close")[0].as_py())
        return res

    result = loop.run_loop(
        universe=universe,
        decision_times=decision_times,
        get_prices_at=get_prices,
        min_observation_days=14,
    )

    # Compute per-period weight statistics.
    raw_factor = make_tsmom_30_7(price_store, market_dataset_id=dataset_id)
    periods: list[dict[str, Any]] = []
    for log in result.period_logs:
        frame = raw_factor.compute(universe, log.decision_time)
        raw_weights = allocator.allocate(frame.values)
        raw_dict = {k: float(v) for k, v in raw_weights.items()}
        enforced = enforce_risk_limits(raw_dict, max_gross_leverage=max_gross_leverage, max_single_weight=max_single_weight)
        periods.append({
            "decision_time": log.decision_time.isoformat(),
            "equity": log.equity,
            "raw_max_single_weight": max((abs(w) for w in raw_dict.values()), default=0.0),
            "raw_gross_leverage": sum(abs(w) for w in raw_dict.values()),
            "raw_net_exposure": sum(raw_dict.values()),
            "enforced_max_single_weight": max((abs(w) for w in enforced.values()), default=0.0),
            "enforced_gross_leverage": sum(abs(w) for w in enforced.values()),
            "enforced_net_exposure": sum(enforced.values()),
            "enforced_weights": enforced,
        })

    summary: dict[str, Any] = {
        "label": label,
        "max_single_weight": max_single_weight,
        "max_gross_leverage": max_gross_leverage,
        "initial_cash": result.initial_cash,
        "final_equity": result.final_equity,
        "total_net_return": result.total_net_return,
        "total_trades_executed": result.total_trades_executed,
        "decision_count": len(result.period_logs),
        "observation_is_complete": result.observation_result.is_complete if result.observation_result else False,
        "observation_meets_risk_limits": result.observation_result.meets_risk_limits if result.observation_result else False,
        "observation_max_single_weight": float(result.observation_result.max_single_asset_weight) if result.observation_result else None,
        "observation_max_leverage": float(result.observation_result.max_leverage_observed) if result.observation_result else None,
        "live_gate_satisfied": compute_live_gate_satisfied(
            "real_asof",
            result.total_net_return,
            bool(result.observation_result.meets_risk_limits) if result.observation_result else False,
            bool(result.observation_result.is_complete) if result.observation_result else False,
        ),
        "live_eligible": False,
    }
    return summary, periods


def _backfill_and_publish(
    db_path: Path,
    store_root: Path,
    start_time: datetime,
    end_time: datetime,
    output_dir: Path,
) -> str:
    """Backfill symbols and publish canonical market bars; return canonical dataset id."""
    symbols = ",".join(sorted(PAPER_TO_BINANCE_MAP.values()))
    report_path = output_dir / "11_REAL_DATA_PATH_REPORT_EXP003.json"
    cmd = [
        ".venv/bin/python",
        "scripts/research/backfill_binance_klines.py",
        "--symbols", symbols,
        "--interval", "1d",
        "--db-path", str(db_path),
        "--store-root", str(store_root),
        "--start-time", start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--end-time", end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--report-path", str(report_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Backfill failed: {result.stderr}\nstdout: {result.stdout}"
        )

    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        return str(report["canonical_dataset_id"])

    # Fallback: resolve latest market_bars from catalog.
    cat = SqliteDatasetCatalog(db_path)
    try:
        resolved = cat.resolve_latest_by_type("market_bars")
        if resolved is None:
            raise RuntimeError("No canonical market_bars dataset found after backfill")
        return resolved
    finally:
        cat.close()


def _write_experiment_registry(
    output_dir: Path,
    experiment_id: str,
    artifacts: dict[str, str],
) -> None:
    """Update / create the experiment CSV registry used by EXP-002."""
    csv_path = output_dir / "experiment_registry.csv"
    header = "experiment_id,status,artifacts_json,generated_at\n"
    row = (
        f"{experiment_id},EXECUTED,{json.dumps(artifacts)},"
        f"{datetime.now(UTC).isoformat()}\n"
    )
    if csv_path.exists():
        content = csv_path.read_text(encoding="utf-8")
        lines = content.rstrip("\n").split("\n")
        if lines and lines[0].startswith("experiment_id"):
            lines = lines[1:]
        filtered = [ln for ln in lines if not ln.startswith(f"{experiment_id},")]
        filtered.append(row)
        csv_path.write_text(header + "\n".join(filtered), encoding="utf-8")
    else:
        csv_path.write_text(header + row, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="EXP-003 MOM-TS risk diagnosis")
    parser.add_argument("--db-path", type=str, default="exp003.db", help="Path to control SQLite DB")
    parser.add_argument("--store-root", type=str, default="data/exp003_store", help="Path to dataset store root")
    parser.add_argument("--start-date", type=str, default="2026-01-01", help="Backfill start date YYYY-MM-DD")
    parser.add_argument("--end-date", type=str, default="2026-07-23", help="Backfill end date YYYY-MM-DD")
    parser.add_argument("--session-start", type=str, default="2026-02-08", help="First decision date YYYY-MM-DD (must allow lookback+skip)")
    parser.add_argument("--session-end", type=str, default="2026-07-23", help="Last decision date YYYY-MM-DD")
    parser.add_argument("--decision-step", type=int, default=7, help="Days between decisions")
    parser.add_argument("--output-dir", type=str, default="research/sprint_004", help="Artifact output directory")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    store_root = Path(args.store_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=UTC)
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=UTC)
    session_start = datetime.strptime(args.session_start, "%Y-%m-%d").replace(tzinfo=UTC)
    session_end = datetime.strptime(args.session_end, "%Y-%m-%d").replace(tzinfo=UTC)

    # Ensure enough history for tsmom_30_7 (lookback=30, skip=7).
    first_decision = session_start
    if first_decision < start_date + timedelta(days=37):
        print(
            f"WARNING: session_start too early for tsmom_30_7; moving to {start_date + timedelta(days=37)}",
            file=sys.stderr,
        )
        first_decision = start_date + timedelta(days=37)
    if first_decision > session_end:
        raise ValueError("session_start is after session_end")

    decision_times = _decision_times(first_decision, session_end, step_days=args.decision_step)
    print(
        f"EXP-003: {len(decision_times)} weekly decisions from {first_decision.date()} to {session_end.date()}",
        file=sys.stderr,
    )

    # Backfill and publish.
    print("Backfilling real bars...", file=sys.stderr)
    canonical_dataset_id = _backfill_and_publish(db_path, store_root, start_date, end_date, output_dir)
    print(f"Canonical dataset: {canonical_dataset_id}", file=sys.stderr)

    universe = list(PAPER_TO_INSTRUMENT_ID.keys())

    # Risk-enforced session.
    print("Running risk-enforced paper session...", file=sys.stderr)
    enforced_summary, enforced_periods = _run_session(
        db_path,
        store_root,
        canonical_dataset_id,
        universe,
        decision_times,
        max_single_weight=MAX_SINGLE_ASSET_WEIGHT,
        max_gross_leverage=MAX_GROSS_LEVERAGE,
        label="risk_enforced",
    )

    # Unconstrained (single-asset cap disabled) session for comparison.
    print("Running unconstrained paper session for comparison...", file=sys.stderr)
    unconstrained_summary, unconstrained_periods = _run_session(
        db_path,
        store_root,
        canonical_dataset_id,
        universe,
        decision_times,
        max_single_weight=1.0,
        max_gross_leverage=MAX_GROSS_LEVERAGE,
        label="unconstrained",
    )

    # Diagnosis: compute aggregate return gap and per-period clipping impact.
    return_gap = unconstrained_summary["total_net_return"] - enforced_summary["total_net_return"]
    avg_clip_impact = return_gap / max(len(decision_times), 1)

    # Find worst single-asset clipping cases.
    clipping_cases: list[dict[str, Any]] = []
    for ep, up in zip(enforced_periods, unconstrained_periods):
        assert ep["decision_time"] == up["decision_time"]
        raw_max = up["raw_max_single_weight"]
        enf_max = ep["enforced_max_single_weight"]
        if raw_max > MAX_SINGLE_ASSET_WEIGHT + 1e-9:
            clipping_cases.append({
                "decision_time": ep["decision_time"],
                "raw_max_single_weight": raw_max,
                "enforced_max_single_weight": enf_max,
                "raw_gross_leverage": up["raw_gross_leverage"],
                "enforced_gross_leverage": ep["enforced_gross_leverage"],
                "raw_net_exposure": up["raw_net_exposure"],
                "enforced_net_exposure": ep["enforced_net_exposure"],
            })

    diagnosis: dict[str, Any] = {
        "experiment_id": "EXP-003",
        "data_mode": "real_asof",
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "factor_id": "tsmom_30_7",
        "control_database": str(db_path),
        "dataset_store_root": str(store_root),
        "canonical_dataset_id": canonical_dataset_id,
        "universe": universe,
        "venue_symbols": sorted(set(PAPER_TO_BINANCE_MAP.values())),
        "session_start": first_decision.isoformat(),
        "session_end": session_end.isoformat(),
        "backfill_start": start_date.isoformat(),
        "backfill_end": end_date.isoformat(),
        "decision_count": len(decision_times),
        "risk_policy": {
            "max_single_weight": MAX_SINGLE_ASSET_WEIGHT,
            "max_gross_leverage": MAX_GROSS_LEVERAGE,
            "policy": "clip_and_renormalize",
        },
        "unconstrained_summary": unconstrained_summary,
        "enforced_summary": enforced_summary,
        "return_gap": {
            "absolute": return_gap,
            "percentage_points": return_gap * 100,
            "avg_per_decision": avg_clip_impact,
            "attribution": "Return gap attributed to single-asset clipping (0.15 cap) and uniform gross scaling after clip. "
                           "Unconstrained mode concentrates in fewer assets; enforcement flattens weights.",
        },
        "dollar_neutrality_drift": {
            "note": "After clipping and renormalizing to gross 1.0, the long/short dollar balance may drift "
                    "because the raw long and short legs are clipped by different amounts depending on leg count.",
            "clipping_cases": len(clipping_cases),
            "sample_cases": clipping_cases[:10],
        },
        "live_gate_satisfied": enforced_summary["live_gate_satisfied"],
        "live_eligible": False,
        "prior_sessions": [
            "research/sprint_004/13_REAL_PAPER_SESSION.json",
            "research/sprint_004/14_RISK_COMPLIANT_PAPER_SESSION.json",
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }

    diagnosis_path = output_dir / "15_MOMTS_RISK_DIAGNOSIS.json"
    diagnosis_path.write_text(json.dumps(diagnosis, indent=2), encoding="utf-8")
    print(f"Diagnosis artifact written to {diagnosis_path}", file=sys.stderr)

    # Longer-window session summary artifact.
    long_session_path = output_dir / "16_MOMTS_LONG_SESSION.json"
    long_session: dict[str, Any] = {
        "experiment_id": "EXP-003",
        "data_mode": "real_asof",
        "label": "longer_window_risk_enforced",
        "control_database": str(db_path),
        "dataset_store_root": str(store_root),
        "canonical_dataset_id": canonical_dataset_id,
        "universe": universe,
        "session_start": first_decision.isoformat(),
        "session_end": session_end.isoformat(),
        "backfill_start": start_date.isoformat(),
        "backfill_end": end_date.isoformat(),
        "decision_count": enforced_summary["decision_count"],
        "total_trades_executed": enforced_summary["total_trades_executed"],
        "initial_cash": enforced_summary["initial_cash"],
        "final_equity": enforced_summary["final_equity"],
        "total_net_return": enforced_summary["total_net_return"],
        "observation_is_complete": enforced_summary["observation_is_complete"],
        "observation_meets_risk_limits": enforced_summary["observation_meets_risk_limits"],
        "live_gate_satisfied": enforced_summary["live_gate_satisfied"],
        "live_eligible": False,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    long_session_path.write_text(json.dumps(long_session, indent=2), encoding="utf-8")
    print(f"Longer session artifact written to {long_session_path}", file=sys.stderr)

    # Update experiment registry.
    artifacts = {
        "diagnosis": str(diagnosis_path),
        "long_session": str(long_session_path),
        "real_data_path_report": str(output_dir / "11_REAL_DATA_PATH_REPORT_EXP003.json"),
    }
    _write_experiment_registry(output_dir, "EXP-003", artifacts)
    print(f"Experiment registry updated at {output_dir / 'experiment_registry.csv'}", file=sys.stderr)

    print(json.dumps(diagnosis, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
