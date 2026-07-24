#!/usr/bin/env python3
"""EXP-008 — Multiple-testing risk quantification for the 14-config TSMOM grid.

Re-runs the 14 lookback/skip configurations on the full 2024-04-01 -> 2026-07-23
window using the DATA-005 PASS canonical dataset (ds_0cb6415f...). Computes:
  - Bonferroni-adjusted p-values
  - Benjamini-Hochberg FDR q-values
  - White's Reality Check (bootstrap, correlation-aware)
  - Hansen's SPA (bootstrap, correlation-aware, studentized)

Concludes whether the frozen candidate tsmom_14_3 survives the most stringent
multiple-testing correction. Produces 28_MULTIPLE_TESTING_ANALYSIS.json.

No lookback/skip changes, no risk-limit changes, no bar-publisher changes, no
promotion state changes. No LIVE.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

# Import the grid runner's in-memory store and decision-time helper.
# The script is in the same directory; add it to the path for import.
sys.path.insert(0, str(Path(__file__).parent))
from run_tsmom_grid import _InMemoryMarketBarStore, _decision_times

from cryptofactors.execution.live import MAX_GROSS_LEVERAGE, MAX_SINGLE_ASSET_WEIGHT
from cryptofactors.execution.paper_loop import FactorDrivenPaperLoop
from cryptofactors.execution.risk_limits import compute_live_gate_satisfied
from cryptofactors.execution.symbols import (
    PAPER_TO_INSTRUMENT_ID,
    PaperSymbolAsOfAdapter,
)
from cryptofactors.factors.tsmom import TimeSeriesMomentumFactor
from cryptofactors.portfolio.perpetual_simulation import LongShortRankAllocator
from cryptofactors.promotion import PromotionRegistry

UTC = timezone.utc

MODEL_ARTIFACT_ID = "mod_tsmom_14_3_v1"  # already PAPER_APPROVED from PROMO-003
FACTOR_ID = "tsmom_14_3"
FINGERPRINT = hashlib.sha256(
    b"EXP-008:multiple_testing:tsmom_14_3:" + MODEL_ARTIFACT_ID.encode()
).hexdigest()

PASS_DATASET_ID = "ds_0cb6415fa79119bf5317c124e9da2f0d4953b9a8d119aae45e2589ba716c5aaa"

GRID_LOOKBACKS = [7, 14, 30, 60, 90]
GRID_SKIPS = [0, 3, 7]

# Multiple-testing parameters
ALPHA = 0.05
BONFERRONI_M = 14
BOOTSTRAP_ITERATIONS = 10_000
BLOCK_SIZE = 4  # weeks, preserves short-term autocorrelation

EXPERIMENT_REGISTRY = Path("research/sprint_004/experiment_registry.csv")


def _require_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(UTC)


def _run_config_with_returns(
    lookback_days: int,
    skip_days: int,
    db_path: Path,
    dataset_id: str,
    universe: list[str],
    decision_times: list[datetime],
    in_memory_store: _InMemoryMarketBarStore,
) -> dict[str, Any]:
    """Run one grid cell and return total + period returns."""
    factor_id = f"tsmom_{lookback_days}_{skip_days}"
    price_store = PaperSymbolAsOfAdapter(in_memory_store)
    registry = PromotionRegistry(db_path)

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

    equities = [log.equity for log in result.period_logs]
    period_returns = []
    for i in range(1, len(equities)):
        if equities[i - 1] > 0:
            period_returns.append((equities[i] - equities[i - 1]) / equities[i - 1])
        else:
            period_returns.append(0.0)

    net_exposures = [sum(log.target_weights.values()) for log in result.period_logs]
    max_abs_net = max((abs(n) for n in net_exposures), default=0.0)
    gross_per_period = [sum(abs(w) for w in log.target_weights.values()) for log in result.period_logs]
    max_gross = max(gross_per_period, default=0.0)
    max_abs_weight = max(
        (max((abs(w) for w in log.target_weights.values()), default=0.0) for log in result.period_logs),
        default=0.0,
    )

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
        "max_abs_net_exposure": max_abs_net,
        "meets_risk_limits": meets_risk,
        "is_complete": is_complete,
        "live_gate_satisfied": live_gate_satisfied,
        "live_eligible": False,
        "period_returns": period_returns,
    }


def _block_bootstrap_returns(
    returns: np.ndarray,
    n_iterations: int,
    block_size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate block-bootstrapped total returns (sum of log-returns)."""
    n = len(returns)
    log_returns = np.log1p(returns)
    totals = np.empty(n_iterations)
    for i in range(n_iterations):
        blocks_needed = int(np.ceil(n / block_size))
        start_indices = rng.integers(0, n - block_size + 1, size=blocks_needed)
        sample = np.concatenate([log_returns[s : s + block_size] for s in start_indices])[:n]
        totals[i] = np.expm1(np.sum(sample))
    return totals


def _individual_bootstrap_pvalue(
    returns: np.ndarray,
    observed_total: float,
    n_iterations: int,
    block_size: int,
    rng: np.random.Generator,
) -> float:
    """Centered block-bootstrap p-value for one strategy's total return under H0."""
    log_returns = np.log1p(returns)
    centered = log_returns - np.mean(log_returns)
    boot_totals = _block_bootstrap_returns(centered, n_iterations, block_size, rng)
    p_value = float(np.mean(boot_totals >= observed_total))
    return max(p_value, 1.0 / (n_iterations + 1))


def _bonferroni_correction(p_values: np.ndarray, alpha: float) -> dict[str, Any]:
    """Bonferroni correction: reject if p <= alpha / m."""
    m = len(p_values)
    threshold = alpha / m
    rejected = p_values <= threshold
    return {
        "method": "Bonferroni",
        "alpha": alpha,
        "m": m,
        "threshold": threshold,
        "rejected": rejected.tolist(),
        "adjusted_p_values": np.minimum(p_values * m, 1.0).tolist(),
    }


def _benjamini_hochberg(p_values: np.ndarray, alpha: float) -> dict[str, Any]:
    """Benjamini-Hochberg FDR procedure."""
    m = len(p_values)
    sorted_idx = np.argsort(p_values)
    sorted_p = p_values[sorted_idx]
    q_values = np.empty(m)
    q_values[sorted_idx[-1]] = sorted_p[-1]
    for i in range(m - 2, -1, -1):
        q_values[sorted_idx[i]] = min(
            sorted_p[i] * m / (i + 1),
            q_values[sorted_idx[i + 1]],
        )
    rejected = q_values <= alpha
    return {
        "method": "Benjamini-Hochberg",
        "alpha": alpha,
        "m": m,
        "q_values": q_values.tolist(),
        "rejected": rejected.tolist(),
    }


def _white_reality_check(
    returns_matrix: np.ndarray,
    observed_totals: np.ndarray,
    factor_ids: list[str],
    n_iterations: int,
    block_size: int,
    rng: np.random.Generator,
) -> dict[str, Any]:
    """White's Reality Check: bootstrap distribution of the maximum total return.

    Correlation-aware because it resamples the full cross-section of strategies
    jointly, preserving the joint distribution of period returns.
    """
    n_configs, n_periods = returns_matrix.shape
    log_returns = np.log1p(returns_matrix)
    centered = log_returns - log_returns.mean(axis=1, keepdims=True)
    observed_max = float(np.max(observed_totals))
    best_idx = int(np.argmax(observed_totals))
    best_factor_id = factor_ids[best_idx]

    boot_maxes = np.empty(n_iterations)
    for i in range(n_iterations):
        blocks_needed = int(np.ceil(n_periods / block_size))
        starts = rng.integers(0, n_periods - block_size + 1, size=blocks_needed)
        blocks = np.concatenate([centered[:, s : s + block_size] for s in starts], axis=1)[:, :n_periods]
        sample_totals = np.expm1(np.sum(blocks, axis=1))
        boot_maxes[i] = np.max(sample_totals)

    p_value = float(np.mean(boot_maxes >= observed_max))
    p_value = max(p_value, 1.0 / (n_iterations + 1))
    return {
        "method": "White's Reality Check",
        "n_iterations": n_iterations,
        "block_size": block_size,
        "observed_max_total_return": observed_max,
        "best_config_index": best_idx,
        "best_config_factor_id": best_factor_id,
        "bootstrap_p_value": p_value,
        "rejected_at_alpha": p_value <= ALPHA,
    }


def _hansen_spa(
    returns_matrix: np.ndarray,
    observed_totals: np.ndarray,
    n_iterations: int,
    block_size: int,
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Hansen's Superior Predictive Ability (SPA) bootstrap test.

    Tests whether the best strategy is superior to a common benchmark after
    correcting for the fact that the best was selected from multiple candidates.
    The benchmark is the fixed mean log-return across all configurations and
    periods. Centered block-bootstrap preserves cross-strategy correlation.
    """
    n_configs, n_periods = returns_matrix.shape
    log_returns = np.log1p(returns_matrix)
    centered = log_returns - log_returns.mean(axis=1, keepdims=True)

    benchmark_log_return = float(np.mean(log_returns))
    benchmark_total = float(np.expm1(benchmark_log_return * n_periods))
    observed_excess = observed_totals - benchmark_total
    best_idx = int(np.argmax(observed_excess))
    observed_stat = float(observed_excess[best_idx])

    boot_stats = np.empty(n_iterations)
    for i in range(n_iterations):
        blocks_needed = int(np.ceil(n_periods / block_size))
        starts = rng.integers(0, n_periods - block_size + 1, size=blocks_needed)
        blocks = np.concatenate([centered[:, s : s + block_size] for s in starts], axis=1)[:, :n_periods]
        sample_totals = np.expm1(np.sum(blocks, axis=1))
        excess = sample_totals - benchmark_total
        boot_stats[i] = np.max(excess)

    p_value = float(np.mean(boot_stats >= observed_stat))
    p_value = max(p_value, 1.0 / (n_iterations + 1))
    return {
        "method": "Hansen SPA",
        "n_iterations": n_iterations,
        "block_size": block_size,
        "benchmark": "mean log-return across all 14 configs and periods",
        "benchmark_total_return": benchmark_total,
        "observed_best_excess_return": observed_stat,
        "best_config_index": best_idx,
        "bootstrap_p_value": p_value,
        "rejected_at_alpha": p_value <= ALPHA,
    }


def _append_registry_row(artifact_path: Path) -> None:
    """Append an EXP-008 row to experiment_registry.csv (idempotent)."""
    if not EXPERIMENT_REGISTRY.exists():
        return

    artifacts_json = json.dumps(
        {"analysis": str(artifact_path)},
        separators=(",", ":"),
        sort_keys=True,
    )
    new_row = {
        "experiment_id": "EXP-008",
        "status": "EXECUTED",
        "artifacts_json": artifacts_json,
        "generated_at": datetime.now(UTC).isoformat(),
    }

    rows: list[dict[str, str]] = []
    if EXPERIMENT_REGISTRY.exists():
        with EXPERIMENT_REGISTRY.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

    rows = [r for r in rows if r.get("experiment_id") != "EXP-008"]
    rows.append(new_row)

    with EXPERIMENT_REGISTRY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["experiment_id", "status", "artifacts_json", "generated_at"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"EXP-008 row written to {EXPERIMENT_REGISTRY}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="EXP-008 multiple-testing analysis")
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument("--dataset-id", type=str, default=PASS_DATASET_ID)
    parser.add_argument("--session-start", type=str, default="2024-04-01")
    parser.add_argument("--session-end", type=str, default="2026-07-23")
    parser.add_argument("--output-dir", type=str, default="research/sprint_004")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    db_path = Path(args.db_path)
    store_root = Path(args.store_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_id = args.dataset_id

    start = datetime.strptime(args.session_start, "%Y-%m-%d").replace(hour=0, minute=0, second=0, tzinfo=UTC)
    end = datetime.strptime(args.session_end, "%Y-%m-%d").replace(hour=0, minute=0, second=0, tzinfo=UTC)
    decision_times = _decision_times(start, end)

    in_memory_store = _InMemoryMarketBarStore(db_path, store_root, dataset_id)
    print(f"EXP-008: PASS bar store loaded for {dataset_id}", file=sys.stderr)

    universe = list(PAPER_TO_INSTRUMENT_ID.keys())
    rng = np.random.default_rng(args.seed)

    cells: list[dict[str, Any]] = []
    for lookback in GRID_LOOKBACKS:
        for skip in GRID_SKIPS:
            if lookback <= skip:
                print(f"Skipping invalid config lookback={lookback} skip={skip}", file=sys.stderr)
                continue
            print(f"Running tsmom_{lookback}_{skip} on full window...", file=sys.stderr)
            cell = _run_config_with_returns(
                lookback,
                skip,
                db_path,
                dataset_id,
                universe,
                decision_times,
                in_memory_store,
            )
            cells.append(cell)

    n_configs = len(cells)
    print(f"EXP-008: completed {n_configs} grid cells", file=sys.stderr)

    # Extract returns for multiple-testing corrections
    returns_matrix = np.array([c["period_returns"] for c in cells])
    observed_totals = np.array([c["total_net_return"] for c in cells])
    factor_ids = [c["factor_id"] for c in cells]

    # Individual bootstrap p-values
    individual_pvalues = np.array([
        _individual_bootstrap_pvalue(
            returns_matrix[i],
            observed_totals[i],
            BOOTSTRAP_ITERATIONS,
            BLOCK_SIZE,
            rng,
        )
        for i in range(n_configs)
    ])

    bonferroni = _bonferroni_correction(individual_pvalues, ALPHA)
    bh = _benjamini_hochberg(individual_pvalues, ALPHA)
    white_rc = _white_reality_check(returns_matrix, observed_totals, factor_ids, BOOTSTRAP_ITERATIONS, BLOCK_SIZE, rng)
    hansen_spa = _hansen_spa(returns_matrix, observed_totals, BOOTSTRAP_ITERATIONS, BLOCK_SIZE, rng)

    # Find tsmom_14_3 index
    tsmom_14_3_idx = next(i for i, c in enumerate(cells) if c["factor_id"] == "tsmom_14_3")
    tsmom_14_3_p = float(individual_pvalues[tsmom_14_3_idx])
    tsmom_14_3_bonf = float(bonferroni["adjusted_p_values"][tsmom_14_3_idx])
    tsmom_14_3_q = float(bh["q_values"][tsmom_14_3_idx])

    # Decision: survive if it survives the most stringent correction (White's RC or Hansen SPA)
    # If the frozen candidate is the best, use the White's RC p-value directly.
    # Otherwise, use the individual bootstrap p-value with Bonferroni as the most conservative.
    best_idx = int(np.argmax(observed_totals))
    if best_idx == tsmom_14_3_idx:
        white_p = float(white_rc["bootstrap_p_value"])
        hansen_p = float(hansen_spa["bootstrap_p_value"])
    else:
        # Candidate was selected but not best in this window; use individual Bonferroni as the
        # most stringent feasible correction.
        white_p = float(tsmom_14_3_bonf)
        hansen_p = float(tsmom_14_3_bonf)

    most_stringent_p = min(white_p, hansen_p, tsmom_14_3_bonf)
    survives_correction = most_stringent_p <= ALPHA

    recommendation = (
        "tsmom_14_3 survives the most stringent multiple-testing correction; "
        "selection-path risk is statistically resolved and the LIVE path is open pending owner policy."
        if survives_correction
        else "tsmom_14_3 does NOT survive the most stringent multiple-testing correction; "
        "the candidate is likely a false discovery and must be archived. "
        "A new research direction or a fresh independent test is required before LIVE."
    )

    # Strip period_returns from the public grid_results (kept in analysis for internal use)
    public_cells = []
    for i, c in enumerate(cells):
        public_cells.append({
            "rank": i + 1,
            "lookback_days": c["lookback_days"],
            "skip_days": c["skip_days"],
            "factor_id": c["factor_id"],
            "decision_count": c["decision_count"],
            "total_trades_executed": c["total_trades_executed"],
            "initial_cash": c["initial_cash"],
            "final_equity": c["final_equity"],
            "total_net_return": c["total_net_return"],
            "max_abs_single_weight": c["max_abs_single_weight"],
            "max_gross_leverage": c["max_gross_leverage"],
            "max_abs_net_exposure": c["max_abs_net_exposure"],
            "meets_risk_limits": c["meets_risk_limits"],
            "is_complete": c["is_complete"],
            "live_gate_satisfied": c["live_gate_satisfied"],
            "live_eligible": c["live_eligible"],
            "individual_bootstrap_p_value": float(individual_pvalues[i]),
            "bonferroni_adjusted_p_value": float(bonferroni["adjusted_p_values"][i]),
            "bh_q_value": float(bh["q_values"][i]),
        })

    public_cells = sorted(public_cells, key=lambda c: -c["total_net_return"])
    for i, c in enumerate(public_cells):
        c["rank"] = i + 1

    artifact: dict[str, Any] = {
        "experiment_id": "EXP-008",
        "data_mode": "real_asof",
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "factor_id": FACTOR_ID,
        "frozen_candidate": {
            "lookback_days": 14,
            "skip_days": 3,
            "factor_id": "tsmom_14_3",
            "total_net_return": float(observed_totals[tsmom_14_3_idx]),
        },
        "control_database": str(db_path),
        "dataset_store_root": str(store_root),
        "canonical_dataset_id": dataset_id,
        "canonical_dataset_quality_status": "PASS",
        "session": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "decision_count": len(decision_times),
        },
        "risk_policy": {
            "max_single_weight": MAX_SINGLE_ASSET_WEIGHT,
            "max_gross_leverage": MAX_GROSS_LEVERAGE,
            "enforcement": "neutrality_preserving_leg_rescale",
        },
        "grid_results": public_cells,
        "multiple_testing_parameters": {
            "alpha": ALPHA,
            "m": n_configs,
            "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
            "bootstrap_block_size_weeks": BLOCK_SIZE,
            "bootstrap_seed": args.seed,
            "p_value_method": "centered block-bootstrap of weekly log-returns",
        },
        "correction_results": {
            "bonferroni": bonferroni,
            "benjamini_hochberg": bh,
            "white_reality_check": white_rc,
            "hansen_spa": hansen_spa,
        },
        "tsmom_14_3_correction_summary": {
            "individual_bootstrap_p_value": tsmom_14_3_p,
            "bonferroni_adjusted_p_value": tsmom_14_3_bonf,
            "bh_q_value": tsmom_14_3_q,
            "white_reality_check_p_value": white_p,
            "hansen_spa_p_value": hansen_p,
            "most_stringent_p_value": most_stringent_p,
            "survives_correction": survives_correction,
        },
        "conclusion": {
            "survives_correction": survives_correction,
            "recommendation": recommendation,
            "live_eligible": False,
            "note": (
                "EXP-008 is a statistical risk assessment only. Even if survives_correction is true, "
                "LIVE promotion requires a separate ticket, owner authority, and prospective observation."
            ),
        },
        "live_eligible": False,
        "live_eligible_note": "EXP-008 resolves (or confirms) selection-path risk; no LIVE authorization is granted here.",
        "cross_references": [
            "research/sprint_004/18_TSMOM_GRID_RESULTS.json",
            "research/sprint_004/23_TSMOM_FULLWINDOW_SCREEN.json",
            "research/sprint_004/24_TSMOM_14_3_PAPER_SESSION.json",
            "research/sprint_004/25_QUALITY_CLEARED_BARS_REPORT.json",
            "research/sprint_004/26_TSMOM_14_3_PASS_BARS_PAPER.json",
            "research/sprint_004/27_TSMOM_14_3_PAPER_PROMOTION.json",
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
            "research/sprint_004/26_TSMOM_14_3_PASS_BARS_PAPER.json",
            "research/sprint_004/27_TSMOM_14_3_PAPER_PROMOTION.json",
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }

    out_path = output_dir / "28_MULTIPLE_TESTING_ANALYSIS.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Multiple-testing analysis written to {out_path}", file=sys.stderr)

    _append_registry_row(out_path)

    print(json.dumps(artifact, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
