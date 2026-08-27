#!/usr/bin/env python3
"""CEX-002 Gate 2 — plan, acquire, or verify the harmonic raw release.

Location arguments select already-accepted bytes. Acquire may expose only
operational stop bounds. Planning and verification perform no network call.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from cryptofactors.acquisition.binance_usdm_harmonic_acquisition import (
    EXIT_AUTHORITY_INVALID,
    AcquisitionError,
    AcquisitionPaths,
    AuthorityError,
    CapacityBlocked,
    HttpxStreamTransport,
    PRODUCTION_PINS,
    UnsafeStateError,
    default_paths,
    map_exception,
    run_acquire,
    run_plan,
    verify_state,
)

DEFAULT_STORE = Path("data/cex002_qualify")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_locations(target: argparse.ArgumentParser) -> None:
        target.add_argument("--store-root", default=str(DEFAULT_STORE))
        target.add_argument("--repository", default="")
        target.add_argument("--report-path", default="")
        target.add_argument("--receipt-258-path", default="")
        target.add_argument("--attestation-path", default="")
        target.add_argument("--lock-path", default="")
        target.add_argument("--amendment-ledger-path", default="")
        target.add_argument("--progress-path", default="")
        target.add_argument("--listing-checkpoint-path", default="")
        target.add_argument("--contract-metadata-path", default="")
        target.add_argument("--listing-cache-dir", default="")
        target.add_argument("--coinalyze-cache-dir", default="")
        target.add_argument("--holdout-path", default="")

    plan = sub.add_parser("plan", help="install the immutable Gate-2 plan")
    add_locations(plan)
    acquire = sub.add_parser("acquire", help="resume bounded raw acquisition")
    add_locations(acquire)
    acquire.add_argument("--max-objects", type=int, default=None)
    acquire.add_argument("--max-wall-seconds", type=float, default=None)
    verify = sub.add_parser("verify", help="offline terminal verification")
    add_locations(verify)
    return parser


def _optional_path(value: str, fallback: Path) -> Path:
    return Path(value) if value else fallback


def resolve_paths(args: argparse.Namespace, *, repository: Path) -> AcquisitionPaths:
    base = default_paths(repository, Path(args.store_root))
    return replace(
        base,
        report_path=_optional_path(args.report_path, base.report_path),
        receipt_258_path=_optional_path(args.receipt_258_path, base.receipt_258_path),
        attestation_path=_optional_path(args.attestation_path, base.attestation_path),
        lock_path=_optional_path(args.lock_path, base.lock_path),
        amendment_ledger_path=_optional_path(
            args.amendment_ledger_path, base.amendment_ledger_path
        ),
        progress_path=_optional_path(args.progress_path, base.progress_path),
        listing_checkpoint_path=_optional_path(
            args.listing_checkpoint_path, base.listing_checkpoint_path
        ),
        contract_metadata_path=_optional_path(
            args.contract_metadata_path, base.contract_metadata_path
        ),
        listing_cache_dir=_optional_path(args.listing_cache_dir, base.listing_cache_dir),
        coinalyze_cache_dir=_optional_path(
            args.coinalyze_cache_dir, base.coinalyze_cache_dir
        ),
        holdout_path=_optional_path(args.holdout_path, base.holdout_path),
    )


def main(
    argv: list[str] | None = None,
    *,
    pins: Any = None,
    transport: Any = None,
    filesystem: Any = None,
    secret: str | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repository = (
        Path(args.repository)
        if args.repository
        else Path(__file__).resolve().parents[2]
    )
    paths = resolve_paths(args, repository=repository)
    resolved_pins = pins or PRODUCTION_PINS
    owned_transport = None
    try:
        if args.command == "plan":
            result = run_plan(paths, resolved_pins, filesystem=filesystem, transport=None)
        elif args.command == "verify":
            result = verify_state(
                paths, resolved_pins, filesystem=filesystem, transport=None
            )
        elif args.command == "acquire":
            if transport is None:
                owned_transport = HttpxStreamTransport()
                transport = owned_transport
            result = run_acquire(
                paths,
                resolved_pins,
                filesystem=filesystem,
                transport=transport,
                max_objects=args.max_objects,
                max_wall_seconds=args.max_wall_seconds,
                secret=secret,
            )
        else:
            return EXIT_AUTHORITY_INVALID
    except (AuthorityError, CapacityBlocked, UnsafeStateError, AcquisitionError) as exc:
        print(f"ERROR: {exc.message}", file=sys.stderr)
        return map_exception(exc)
    finally:
        if owned_transport is not None:
            owned_transport.close()
    print(
        f"command={args.command} exit={result['exit_code']} "
        f"stop={result.get('stop_reason') or result.get('status') or 'ok'}",
        file=sys.stderr,
    )
    return int(result["exit_code"])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
