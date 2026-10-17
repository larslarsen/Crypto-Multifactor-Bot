"""Compare retained one-minute klines with the accepted hourly bar and flow products.

Network access happens only when ``--fetch`` is present. Identity hashes, symbols,
dates, and schemas are fixed by the production policy or by a private test policy.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cryptofactors.acquisition.binance_usdm_kline_comparison_sample import (
    SampleError,
    fetch_sample,
    production_policy,
)
from cryptofactors.ingest.binance_usdm_kline_reconciliation import (
    ReconciliationError,
    reconcile,
)


def main(
    argv: list[str] | None = None,
    *,
    policy: object | None = None,
    transport: object | None = None,
    clock: object | None = None,
    hooks: object | None = None,
) -> int:
    """Return 0 for PASS, 1 for a comparison failure, and 2 for usage errors."""

    parser = argparse.ArgumentParser(
        description="Bounded Binance USD-M one-minute and hourly reconciliation",
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--fetch", action="store_true")
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        code = exc.code
        return 2 if code is None else int(code)
    active = production_policy(Path(args.repo)) if policy is None else policy
    try:
        fetch_sample(
            active,  # type: ignore[arg-type]
            Path(args.evidence_root),
            fetch=bool(args.fetch),
            transport=None if not args.fetch else transport,  # type: ignore[arg-type]
            hooks=hooks,  # type: ignore[arg-type]
            clock=clock,  # type: ignore[arg-type]
        )
        result = reconcile(active, Path(args.evidence_root), Path(args.output_root))  # type: ignore[arg-type]
    except (SampleError, ReconciliationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(result.status)
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
