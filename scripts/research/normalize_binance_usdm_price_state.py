#!/usr/bin/env python3
"""Normalize pinned Binance USD-M price-state authority into two hidden products."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryptofactors.ingest.binance_usdm_price_state import normalize_from_authorities


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
                "basis_completion_sha256": result.basis.completion_sha256,
                "basis_gap_artifacts": len(result.basis.gap_artifacts),
                "basis_partitions": len(result.basis.partitions),
                "basis_rows": result.basis.product_rows,
                "basis_unjoinable_source_rows": result.basis.unjoinable_source_rows,
                "indicative_completion_sha256": result.indicative.completion_sha256,
                "indicative_gap_artifacts": len(result.indicative.gap_artifacts),
                "indicative_partitions": len(result.indicative.partitions),
                "indicative_rows": result.indicative.product_rows,
                "premium_zip_reads": result.premium_zip_reads,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
