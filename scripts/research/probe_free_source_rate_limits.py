#!/usr/bin/env python3
"""DATA-007 — Generate free DEX/CEX source rate-limit matrix.

Usage:
    python scripts/research/probe_free_source_rate_limits.py --dry-run
    python scripts/research/probe_free_source_rate_limits.py --no-dry-run

Default is dry-run (mocked / no network). Live mode probes public endpoints
politely and may require BIRDEYE_API_KEY for the Birdeye listings row.

No LIVE. No Birdeye OHLCV.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cryptofactors.acquisition.free_source_probes import build_matrix_report


def main() -> int:
    parser = argparse.ArgumentParser(description="DATA-007 free source rate-limit matrix")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.add_argument(
        "--output",
        type=str,
        default="research/sprint_004/35_FREE_SOURCE_RATE_LIMIT_MATRIX.json",
    )
    args = parser.parse_args()

    report = build_matrix_report(live=not args.dry_run)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"DATA-007 matrix written to {out_path}", file=sys.stderr)

    # Sanity check: Birdeye row must have birdeye_ohlcv_forbidden true.
    for row in report["sources"]:
        if row["source_id"] == "birdeye_listings":
            assert row["birdeye_ohlcv_forbidden"] is True, "Birdeye row must forbid OHLCV"
            break
    else:
        raise RuntimeError("Birdeye row missing from matrix")

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
