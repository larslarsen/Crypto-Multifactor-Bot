#!/usr/bin/env python3
"""Normalize the three accepted authorities into hidden USD-M membership."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryptofactors.ingest.binance_usdm_membership import normalize_from_authorities


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--contract-metadata", required=True, type=Path)
    parser.add_argument("--sizing", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = normalize_from_authorities(
        report_path=args.report,
        contract_metadata_path=args.contract_metadata,
        sizing_path=args.sizing,
        output_root=args.output_root,
    )
    print(
        json.dumps(
            {
                "completion_sha256": result.completion_sha256,
                "membership_rows": len(result.partitions),
                "partitions": len(result.partitions),
                "schema_sha256": result.schema_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
