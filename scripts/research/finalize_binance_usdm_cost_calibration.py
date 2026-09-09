#!/usr/bin/env python3
"""Finalize the exact reviewed preserved Binance USD-M cost-calibration tree."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryptofactors.ingest.binance_usdm_cost_finalization import finalize_from_authorities


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
    result = finalize_from_authorities(
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
                "completion_path": str(result.completion_path),
                "completion_sha256": result.completion_sha256,
                "completion_reused": result.completion_reused,
                "partition_count": result.partition_count,
                "source_rows": result.source_rows,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
