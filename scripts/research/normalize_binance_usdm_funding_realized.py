#!/usr/bin/env python3
"""Normalize accepted generation-0 monthly funding into hidden realized events."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryptofactors.ingest.binance_usdm_funding_realized import normalize_from_authorities


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation0-state", required=True, type=Path)
    parser.add_argument("--generation0-content-root", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--sizing", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = normalize_from_authorities(
        generation0_state=args.generation0_state,
        generation0_content_root=args.generation0_content_root,
        report=args.report,
        sizing=args.sizing,
        output_root=args.output_root,
    )
    print(
        json.dumps(
            {
                "collapsed_identical_rows": result.collapsed_identical_rows,
                "completion_sha256": result.completion_sha256,
                "partition_count": len(result.partitions),
                "physical_source_rows": result.physical_source_rows,
                "product_rows": result.product_rows,
                "schema_sha256": result.schema_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
