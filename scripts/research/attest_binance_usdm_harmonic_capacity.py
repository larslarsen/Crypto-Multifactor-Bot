#!/usr/bin/env python3
"""Publish one ADR-0028 capacity observation over immutable CEX-002 receipt 258."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cryptofactors.acquisition.binance_usdm_capacity_attestation import (
    ATTESTATION_SCHEMA,
    AttestationError,
    run_capacity_attestation,
)

DEFAULT_STORE = Path("data/cex002_qualify")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store-root", default=str(DEFAULT_STORE))
    parser.add_argument("--attestation-path", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repository = Path(__file__).resolve().parents[2]
    try:
        result = run_capacity_attestation(
            repository=repository,
            store_root=Path(args.store_root),
            attestation_path=Path(args.attestation_path),
        )
    except AttestationError as exc:
        print(f"ERROR: {exc.message}", file=sys.stderr)
        return 1

    attestation = result["attestation"]
    identity = result["attestation_file"]
    print(
        f"{ATTESTATION_SCHEMA} written at {identity['path']}", file=sys.stderr
    )
    print(
        f"attestation_sha256={identity['sha256']} "
        f"attestation_bytes={identity['bytes']}",
        file=sys.stderr,
    )
    print(
        "storage_preflight_state="
        f"{attestation['storage_preflight_state']} "
        "total_future_storage_bytes="
        f"{attestation['capacity']['total_future_storage_bytes']} "
        "post_publication_available_bytes="
        f"{attestation['filesystem']['post_publication_available_bytes']}",
        file=sys.stderr,
    )
    if attestation["blockers"]:
        print("blockers: " + ",".join(attestation["blockers"]), file=sys.stderr)
    print(
        "note: this attestation authorizes no acquisition and accepts no gate",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
