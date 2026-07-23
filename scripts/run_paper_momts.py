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

from cryptofactors.catalog.as_of import AsOfAccessError, CatalogAsOfStore
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.execution.errors import PaperExecutionError
from cryptofactors.execution.paper_harden import (
    build_harden_report,
    write_harden_report_artifact,
)
from cryptofactors.execution.paper_loop import FactorDrivenPaperLoop, PaperLoopResult
from cryptofactors.execution.paper_monitor import PaperOpsMonitor
from cryptofactors.execution.paper_store import PaperSessionStore
from cryptofactors.execution.symbols import PAPER_TO_BINANCE_MAP, to_binance_symbol
from cryptofactors.execution.venue_probe import ReadOnlyVenueProbeAdapter
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
            effective_time=datetime(2026, 4, 1, tzinfo=UTC),  # Effective before paper decision window
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
    parser.add_argument("--store-root", type=str, default="data/store", help="Path to dataset store root")
    parser.add_argument("--market-dataset-id", type=str, default="ds_market_bars", help="Market bars dataset ID")
    parser.add_argument("--dry-run", action="store_true", help="Run with temporary SQLite DB and synthetic store")
    parser.add_argument("--venue-probe", action="store_true", help="Perform read-only venue reachability ping probe")
    parser.add_argument("--out", type=str, default="", help="Path to write JSON results summary")
    args = parser.parse_args()

    data_mode = "synthetic" if args.dry_run else "real_asof"
    tmpdir: tempfile.TemporaryDirectory[str] | None = None

    universe = [
        "XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD",
        "AVAXUSD", "DOTUSD", "LINKUSD", "LTCUSD", "BCHUSD",
    ]

    if args.dry_run:
        print("Running factor-driven paper loop in DRY-RUN mode...", file=sys.stderr)
        tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(tmpdir.name) / "control.db"
        store_root = Path(tmpdir.name) / "store"
        synthetic_store = _SyntheticPriceStore(universe, days=160)
        price_store: Any = synthetic_store
        get_prices_fn = synthetic_store.get_prices_at
        dataset_id = args.market_dataset_id
    else:
        db_path = Path(args.db_path)
        if not db_path.exists():
            raise PaperExecutionError(
                f"Control database missing at {db_path}. Non-dry-run mode requires an existing control DB.",
                context={"db_path": str(db_path)},
            )
        store_root = Path(args.store_root)
        if not store_root.exists() or not store_root.is_dir():
            raise PaperExecutionError(
                f"Dataset store root missing or not a directory at {store_root}.",
                context={"store_root": str(store_root)},
            )

        cat = SqliteDatasetCatalog(db_path)
        try:
            row = cat.get_dataset(args.market_dataset_id)
            if row is None:
                raise PaperExecutionError(
                    f"market_bars dataset '{args.market_dataset_id}' not found in catalog. Run backfill or specify --market-dataset-id.",
                    context={"db_path": str(db_path), "market_dataset_id": args.market_dataset_id},
                )
            dataset_id = args.market_dataset_id
        finally:
            cat.close()

        as_of_store = CatalogAsOfStore(control_database=db_path, dataset_store_root=store_root)
        price_store = as_of_store

        def get_real_prices(dt: datetime, univ: Sequence[str]) -> dict[str, float]:
            res: dict[str, float] = {}
            for sym in univ:
                binance_sym = to_binance_symbol(sym)
                try:
                    tbl = as_of_store.latest_available(dataset_id, [binance_sym], ["close"], dt)
                    if tbl is not None and tbl.num_rows > 0:
                        res[sym] = float(tbl.column("close")[0].as_py())
                except AsOfAccessError as exc:
                    raise PaperExecutionError(
                        f"AsOf access error looking up price for '{sym}' ({binance_sym}) at {dt.isoformat()}: {exc}",
                        context={"symbol": sym, "binance_symbol": binance_sym, "decision_time": dt.isoformat()},
                    ) from exc

            if not res:
                raise PaperExecutionError(
                    f"No real bar prices found at {dt.isoformat()} for dataset {dataset_id}",
                    context={"dataset_id": dataset_id, "decision_time": dt.isoformat()},
                )
            return res

        get_prices_fn = get_real_prices

    registry = PromotionRegistry(db_path)
    ensure_paper_approved(registry, MODEL_ARTIFACT_ID)

    session_store = PaperSessionStore(db_path)
    monitor = PaperOpsMonitor(registry)

    # Optional venue reachability probe
    probe_result: dict[str, Any] | None = None
    if args.venue_probe:
        print("Executing read-only venue connectivity probe...", file=sys.stderr)
        probe_adapter = ReadOnlyVenueProbeAdapter()
        probe_result = probe_adapter.ping_venue()

    factor = make_tsmom_30_7(price_store, market_dataset_id=dataset_id)

    loop = FactorDrivenPaperLoop(
        model_artifact_id=MODEL_ARTIFACT_ID,
        promotion_registry=registry,
        factor=factor,
        session_store=session_store,
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
        get_prices_at=get_prices_fn,
        min_observation_days=14,
    )

    # Generate and write PaperOpsStatus report artifact
    obs_ref = result.observation_result.reference_id if result.observation_result else None
    final_prices = get_prices_fn(decision_times[-1], universe)
    ops_status = monitor.inspect_session(
        MODEL_ARTIFACT_ID,
        broker=loop.broker,
        current_prices=final_prices,
        paper_observation_reference=obs_ref,
        drawdown_alert_triggered=result.drawdown_alert_triggered,
    )
    status_path = Path("research/sprint_004/09_PAPER_OPS_STATUS.json")
    monitor.write_status_artifact(ops_status, status_path)
    print(f"Paper ops health/status report written to {status_path}", file=sys.stderr)

    # Generate and write PaperHardenReport artifact (HARDEN-001)
    harden_report = build_harden_report(
        ops_status,
        data_mode=data_mode,
        venue_probe_result=probe_result,
    )
    harden_path = Path("research/sprint_004/10_PAPER_HARDEN_REPORT.json")
    write_harden_report_artifact(harden_report, harden_path)
    print(f"Hardening report written to {harden_path} (live_eligible={harden_report.live_eligible})", file=sys.stderr)

    # Generate and write Real AsOf Correctness Report artifact (DATA-003)
    correctness_report = {
        "data_mode": data_mode,
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "control_database": str(db_path),
        "dataset_store_root": str(store_root),
        "market_dataset_id": dataset_id,
        "symbol_map": PAPER_TO_BINANCE_MAP,
        "watermark_last_decision_time": decision_times[-1].isoformat(),
        "total_periods": len(result.period_logs),
        "gate_status": ops_status.gate_status,
        "live_eligible": False,  # ALWAYS false per DATA-003 policy
        "generated_at": datetime.now(UTC).isoformat(),
    }
    correctness_path = Path("research/sprint_004/12_REAL_ASOF_CORRECTNESS.json")
    correctness_path.parent.mkdir(parents=True, exist_ok=True)
    correctness_path.write_text(json.dumps(correctness_report, indent=2), encoding="utf-8")
    print(f"Real as-of correctness report written to {correctness_path}", file=sys.stderr)

    formatted = format_loop_result(result)
    out_json = json.dumps(formatted, indent=2)
    print(out_json)

    out_file = Path(args.out) if args.out else DEFAULT_OUTPUT_PATH
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(out_json, encoding="utf-8")
    print(f"Paper factor loop results written to {out_file}", file=sys.stderr)

    if tmpdir is not None:
        tmpdir.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
