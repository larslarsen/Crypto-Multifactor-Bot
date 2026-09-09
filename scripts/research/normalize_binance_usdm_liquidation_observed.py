#!/usr/bin/env python3
"""Publish authenticated observed daily USD-M liquidations and comparison evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryptofactors.ingest.binance_usdm_liquidation_observed import normalize_from_authorities


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation0-state", required=True, type=Path)
    parser.add_argument("--generation0-content-root", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--sizing", required=True, type=Path)
    parser.add_argument("--bar-product-root", required=True, type=Path)
    parser.add_argument("--open-interest-product-root", required=True, type=Path)
    parser.add_argument("--funding-product-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = normalize_from_authorities(
        generation0_state=args.generation0_state,
        generation0_content_root=args.generation0_content_root,
        report=args.report,
        sizing=args.sizing,
        bar_product_root=args.bar_product_root,
        open_interest_product_root=args.open_interest_product_root,
        funding_product_root=args.funding_product_root,
        output_root=args.output_root,
    )
    print(json.dumps({
        "authority_gap_rows": result.authority_gap_rows,
        "collapsed_identical_rows": result.collapsed_identical_rows,
        "comparison_count": result.comparison_count,
        "completion_sha256": result.completion_sha256,
        "gap_artifact_count": len(result.gaps),
        "missing_daily_slots": result.missing_daily_slots,
        "partition_count": len(result.partitions),
        "physical_source_rows": result.physical_source_rows,
        "product_rows": result.product_rows,
        "schema_sha256": result.schema_sha256,
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
