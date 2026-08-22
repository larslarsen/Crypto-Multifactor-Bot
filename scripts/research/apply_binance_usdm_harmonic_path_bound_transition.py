#!/usr/bin/env python3
"""CEX-002 ADR-0022 — apply the reviewed path-bound source-authority transition.

A thin adapter with no authority of its own. It accepts only the locations of already
pinned bytes: there is no override for identity, receipt count, mutation scope, recovery
policy, or anything else, because none of those may be chosen by an operator. It performs
no network call and reads no credential.

Exit status is transition status: non-zero when the pinned pre-state or a mutation
boundary fails, zero when the store is in the completed reviewed state. Completion
advances only the executing source identity; it authorizes no acquisition and accepts no
gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cryptofactors.acquisition.binance_usdm_harmonic_path_bound_transition import (
    TransitionError,
    TransitionPaths,
    apply_path_bound_transition,
)

DEFAULT_STORE = Path("data/cex002_qualify")
DEFAULT_REPORT = Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store-root", type=str, default=str(DEFAULT_STORE))
    parser.add_argument("--report-path", type=str, default=str(DEFAULT_REPORT))
    parser.add_argument("--manifest-detail-path", type=str, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repository = Path(__file__).resolve().parents[2]
    paths = TransitionPaths(
        store_root=Path(args.store_root),
        report_path=Path(args.report_path),
        manifest_detail_path=Path(args.manifest_detail_path),
        qualification_source_path=repository
        / "src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py",
    )
    try:
        receipt = apply_path_bound_transition(paths)
    except TransitionError as exc:
        # Only the message reaches the transcript: never authority content.
        print(f"ERROR: {exc.message}", file=sys.stderr)
        return 1

    print(
        "path_bound_transition: " + json.dumps(receipt, sort_keys=True, default=str),
        file=sys.stderr,
    )
    action = "applied" if receipt["executed"] else "already complete"
    print(
        f"transition {action}: "
        f"code_config_digest={receipt['final']['code_config_digest']} "
        f"source_receipts={receipt['final']['source_receipts']} "
        f"samples_acquired={receipt['work']['samples_acquired']}",
        file=sys.stderr,
    )
    print(
        "note: this transition authorizes no acquisition and accepts no gate",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
