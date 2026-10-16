#!/usr/bin/env python3
"""Publish the accepted Binance USD-M coverage ledger and UTC-day reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryptofactors.ingest.binance_usdm_coverage import COMPLETION_SHA256, normalize_coverage
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    PRODUCT_BAR_1H,
    PRODUCT_FUNDING_INDICATIVE_1H,
    PRODUCT_FUNDING_REALIZED,
    PRODUCT_LIQUIDATION_OBSERVED_DAILY,
    PRODUCT_MARK_INDEX_BASIS_1H,
    PRODUCT_MEMBERSHIP,
    PRODUCT_OPEN_INTEREST_5M,
    PRODUCT_TRADE_FLOW_1H,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--sizing", required=True, type=Path)
    parser.add_argument("--holdout", required=True, type=Path)
    parser.add_argument("--membership-root", required=True, type=Path)
    parser.add_argument("--bar-root", required=True, type=Path)
    parser.add_argument("--trade-flow-root", required=True, type=Path)
    parser.add_argument("--open-interest-root", required=True, type=Path)
    parser.add_argument("--funding-realized-root", required=True, type=Path)
    parser.add_argument("--price-state-root", required=True, type=Path)
    parser.add_argument("--liquidation-root", required=True, type=Path)
    parser.add_argument("--cost-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    roots = {
        PRODUCT_MEMBERSHIP: args.membership_root,
        PRODUCT_BAR_1H: args.bar_root,
        PRODUCT_TRADE_FLOW_1H: args.trade_flow_root,
        PRODUCT_OPEN_INTEREST_5M: args.open_interest_root,
        PRODUCT_FUNDING_REALIZED: args.funding_realized_root,
        PRODUCT_FUNDING_INDICATIVE_1H: args.price_state_root / PRODUCT_FUNDING_INDICATIVE_1H,
        PRODUCT_MARK_INDEX_BASIS_1H: args.price_state_root / PRODUCT_MARK_INDEX_BASIS_1H,
        PRODUCT_LIQUIDATION_OBSERVED_DAILY: args.liquidation_root,
        "binance_usdm_cost_calibration": args.cost_root,
    }
    if set(roots) != set(COMPLETION_SHA256):
        raise RuntimeError("coverage CLI product inventory changed")
    result = normalize_coverage(
        report_path=args.report,
        sizing_path=args.sizing,
        holdout_path=args.holdout,
        product_roots=roots,
        output_root=args.output_root,
    )
    print(
        json.dumps(
            {
                "aligned_day_count": result.aligned_day_count,
                "completion_path": str(result.completion_path),
                "completion_reused": result.completion_reused,
                "completion_sha256": result.completion_sha256,
                "daily_report_count": result.daily_report_count,
                "five_product_observed_day_count": result.five_product_observed_day_count,
                "full_cadence_day_count": result.full_cadence_day_count,
                "metadata_bytes": result.metadata_bytes,
                "quality_gap_rows": result.quality_gap_rows,
                "source_gap_rows": result.source_gap_rows,
                "typed_gap_rows": result.typed_gap_rows,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
