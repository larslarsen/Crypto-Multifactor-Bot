#!/usr/bin/env python3
"""Normalize accepted generation-0 hourly klines into two hidden products."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryptofactors.ingest.binance_usdm_klines import normalize_from_generation0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation0-state", required=True, type=Path)
    parser.add_argument("--generation0-content-root", required=True, type=Path)
    parser.add_argument("--bar-output-root", required=True, type=Path)
    parser.add_argument("--trade-flow-output-root", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = normalize_from_generation0(
        generation0_state=args.generation0_state,
        generation0_content_root=args.generation0_content_root,
        bar_output_root=args.bar_output_root,
        trade_flow_output_root=args.trade_flow_output_root,
    )
    print(
        json.dumps(
            {
                "bar_completion_sha256": result.bar.completion_sha256,
                "bar_partitions": len(result.bar.partitions),
                "bar_rows": sum(part.row_count for part in result.bar.partitions),
                "quality_gap_rows": result.bar.gap_artifact.row_count,
                "trade_flow_completion_sha256": result.trade_flow.completion_sha256,
                "trade_flow_partitions": len(result.trade_flow.partitions),
                "trade_flow_rows": sum(part.row_count for part in result.trade_flow.partitions),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
