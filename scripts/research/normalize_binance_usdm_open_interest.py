#!/usr/bin/env python3
"""Normalize the accepted Binance USD-M five-minute open-interest authorities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryptofactors.ingest.binance_usdm_open_interest import normalize_from_authorities


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--generation0-state", type=Path, required=True)
    value.add_argument("--generation0-content-root", type=Path, required=True)
    value.add_argument("--v3-manifest", type=Path, required=True)
    value.add_argument("--recovery-root", type=Path, required=True)
    value.add_argument("--output-root", type=Path, required=True)
    return value


def main() -> int:
    args = parser().parse_args()
    result = normalize_from_authorities(
        generation0_state=args.generation0_state,
        generation0_content_root=args.generation0_content_root,
        v3_manifest=args.v3_manifest,
        recovery_root=args.recovery_root,
        output_root=args.output_root,
    )
    print(
        json.dumps(
            {
                "product": result.product,
                "schema_sha256": result.schema_sha256,
                "writer_identity": result.writer_identity,
                "partition_count": len(result.partitions),
                "row_count": sum(partition.row_count for partition in result.partitions),
                "typed_gap_count": len(result.gaps),
                "quality_gap_rows": result.gap_artifact.row_count,
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
