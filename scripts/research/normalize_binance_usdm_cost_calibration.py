#!/usr/bin/env python3
"""Normalize the accepted Binance USD-M cost-calibration authorities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryptofactors.ingest.binance_usdm_cost_calibration import normalize_from_authorities


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--report", type=Path, required=True)
    value.add_argument("--sizing", type=Path, required=True)
    value.add_argument("--generation0-state", type=Path, required=True)
    value.add_argument("--generation0-content-root", type=Path, required=True)
    value.add_argument("--v3-manifest", type=Path, required=True)
    value.add_argument("--recovery-root", type=Path, required=True)
    value.add_argument("--membership-root", type=Path, required=True)
    value.add_argument("--output-root", type=Path, required=True)
    return value


def main() -> int:
    args = parser().parse_args()
    result = normalize_from_authorities(
        report_path=args.report,
        sizing_path=args.sizing,
        generation0_state=args.generation0_state,
        generation0_content_root=args.generation0_content_root,
        v3_manifest=args.v3_manifest,
        recovery_root=args.recovery_root,
        membership_root=args.membership_root,
        output_root=args.output_root,
    )
    print(
        json.dumps(
            {
                "product": result.product,
                "schema_sha256": result.schema_sha256,
                "partition_count": len(result.components),
                "source_objects": result.source_objects,
                "source_rows": result.source_rows,
                "completion_path": str(result.completion_path),
                "completion_sha256": result.completion_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
