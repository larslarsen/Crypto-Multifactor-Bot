#!/usr/bin/env python3
"""EXP-002 — Execution script for MOM-TS-01 confirmatory experiments (EXP-2026-019 / EXP-2026-020).

Executes perpetual long/short factor backtests using CatalogAsOfStore, BitMEX funding cashflows,
and PORT-002 PerpetualSimulator, emitting structured preregistered metrics.

Usage:
  python3 scripts/run_momts_experiments.py --dry-run
  python3 scripts/run_momts_experiments.py --db-path control.db --market-dataset-id ds_market_bars
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptofactors.catalog.as_of import CatalogAsOfStore
from cryptofactors.experiments.momts_runner import MOMTSRunner, MOMTSRunnerResult
from cryptofactors.ingest.bitmex_funding import BitMEXFundingProvider, build_funding_table

UTC = timezone.utc


def generate_synthetic_data(
    universe: list[str],
    days: int = 120,
) -> tuple[dict[str, list[tuple[datetime, float]]], list[dict[str, Any]]]:
    """Generate synthetic price and funding rate history for dry-run execution."""
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    prices: dict[str, list[tuple[datetime, float]]] = {}
    funding_records: list[dict[str, Any]] = []

    for i, inst in enumerate(universe):
        start_p = 100.0 * (1.0 + i * 0.2)
        growth = 0.001 * (1 if i % 2 == 0 else -1)
        inst_prices: list[tuple[datetime, float]] = []

        for d in range(days):
            dt = t0 + timedelta(days=d)
            p = start_p * ((1.0 + growth) ** d)
            inst_prices.append((dt, p))

            if d % 1 == 0:  # funding events every 8h / daily
                funding_records.append(
                    {
                        "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "symbol": inst,
                        "fundingRate": 0.0001 if i % 2 == 0 else -0.0001,
                        "fundingRateDaily": 0.0003,
                    }
                )
        prices[inst] = inst_prices

    return prices, funding_records


class _SyntheticAsOfStore:
    """As-of store wrapper over synthetic price dict for dry-run mode."""

    def __init__(self, prices: dict[str, list[tuple[datetime, float]]]) -> None:
        self._prices = prices

    def latest_available(
        self,
        dataset_id: str,
        keys: list[Any],
        fields: list[str],
        decision_time: datetime,
        max_age: Any = None,
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
        series = self._prices.get(inst, [])
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

    def as_of(
        self,
        dataset_id: str,
        keys: list[Any],
        fields: list[str],
        decision_time: datetime,
        knowledge_time: datetime | None = None,
    ) -> Any:
        return self.latest_available(dataset_id, keys, fields, decision_time)


def format_result(res: MOMTSRunnerResult) -> dict[str, Any]:
    """Format runner result into clean dict structure for reporting."""
    return {
        "experiment_id": res.experiment_id,
        "factor_id": res.factor_id,
        "fingerprint": res.fingerprint,
        "n_periods": res.n_periods,
        "net_return": float(res.net_return),
        "long_return": float(res.long_return),
        "short_return": float(res.short_return),
        "mean_turnover": float(res.mean_turnover),
        "total_cost": float(res.total_cost),
        "total_funding_cost": float(res.total_funding_cost),
        "liquidation_count": res.liquidation_count,
        "run_at": res.run_at.isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MOM-TS-01 confirmatory experiments.")
    parser.add_argument("--db-path", type=str, default="control.db", help="Path to control SQLite DB")
    parser.add_argument("--market-dataset-id", type=str, default="ds_market_bars", help="Market bars dataset ID")
    parser.add_argument("--dry-run", action="store_true", help="Run with synthetic as-of store fixtures")
    parser.add_argument("--out", type=str, default="", help="Path to write JSON results summary")
    args = parser.parse_args()

    universe = ["XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD"]
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    decision_times = [t0 + timedelta(days=d) for d in range(100, 150, 7)]

    if args.dry_run:
        print("Running MOM-TS-01 experiments in DRY-RUN synthetic mode...", file=sys.stderr)
        prices, funding_records = generate_synthetic_data(universe, days=160)
        as_of_store: Any = _SyntheticAsOfStore(prices)
        funding_table = build_funding_table(funding_records)
        funding_provider = BitMEXFundingProvider(funding_table)
    else:
        db_path = Path(args.db_path)
        if not db_path.exists():
            print(f"Error: Control DB not found at {db_path}. Use --dry-run for synthetic testing.", file=sys.stderr)
            return 1
        as_of_store = CatalogAsOfStore(control_database=db_path)
        funding_provider = None

    runner = MOMTSRunner(
        as_of_store=as_of_store,
        market_dataset_id=args.market_dataset_id,
        funding_provider=funding_provider,
    )

    print("Executing EXP-2026-019 (tsmom_30_7)...", file=sys.stderr)
    res_019 = runner.run_30_7(universe, decision_times)

    print("Executing EXP-2026-020 (tsmom_90_7)...", file=sys.stderr)
    res_020 = runner.run_90_7(universe, decision_times)

    results = {
        "EXP-2026-019": format_result(res_019),
        "EXP-2026-020": format_result(res_020),
    }

    out_json = json.dumps(results, indent=2)
    print(out_json)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_json, encoding="utf-8")
        print(f"Results saved to {out_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
