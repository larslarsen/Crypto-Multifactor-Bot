#!/usr/bin/env python3
"""DEX-003 — fresh-run v2 provider-matrix harness CLI.

Default: plan-only (no RPC). Live: --execute-live + --confirm-matrix-id.
Standalone replay: --offline-replay --live-run-dir <completed run path>.

Every live attempt uses a new exclusive run directory under --output-root/runs/.
No resume. Endpoints/credentials are runtime-only and never recorded.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from cryptofactors.acquisition.uniswap_v2_pair_events_v2_matrix import (
    DEFAULT_MAX_ATTEMPTS_PER_LOGICAL_CALL,
    DEFAULT_MAX_IN_FLIGHT,
    DEFAULT_MAX_PROVIDER_ATTEMPTS,
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_MAX_RETAINED_RESPONSE_BYTES,
    DEFAULT_MAX_WALL_SECONDS,
    DEFAULT_PROVIDER_ORGS,
    DEFAULT_REQUESTS_PER_SECOND,
    LOGICAL_CALL_CEILING,
    MatrixBudgets,
    MatrixConfig,
    MatrixError,
    MatrixSafetyStop,
    PairEventV2MatrixHarness,
    build_matrix_plan,
)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Uniswap V2 v2 provider-matrix harness (fresh-run)")
    p.add_argument(
        "--registry-store-root",
        type=Path,
        default=Path("data/dex003_full/store"),
    )
    p.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/dex003_v2_matrix"),
        help="Dedicated matrix output root (not data/dex003_full or registry store)",
    )
    p.add_argument("--primary-org", default=DEFAULT_PROVIDER_ORGS[0])
    p.add_argument("--secondary-org", default=DEFAULT_PROVIDER_ORGS[1])
    p.add_argument("--execute-live", action="store_true")
    p.add_argument("--confirm-matrix-id", default=None)
    p.add_argument("--offline-replay", action="store_true")
    p.add_argument(
        "--live-run-dir",
        type=Path,
        default=None,
        help="Completed live run directory for standalone read-only replay",
    )
    p.add_argument("--print-matrix-id", action="store_true")
    p.add_argument("--max-logical-calls", type=int, default=LOGICAL_CALL_CEILING)
    p.add_argument(
        "--max-attempts-per-call", type=int, default=DEFAULT_MAX_ATTEMPTS_PER_LOGICAL_CALL
    )
    p.add_argument("--max-provider-attempts", type=int, default=DEFAULT_MAX_PROVIDER_ATTEMPTS)
    p.add_argument("--max-wall-seconds", type=float, default=DEFAULT_MAX_WALL_SECONDS)
    p.add_argument(
        "--max-retained-response-bytes",
        type=int,
        default=DEFAULT_MAX_RETAINED_RESPONSE_BYTES,
    )
    p.add_argument("--max-response-bytes", type=int, default=DEFAULT_MAX_RESPONSE_BYTES)
    p.add_argument("--requests-per-second", type=float, default=DEFAULT_REQUESTS_PER_SECOND)
    p.add_argument("--max-in-flight", type=int, default=DEFAULT_MAX_IN_FLIGHT)
    p.add_argument("--http-timeout-seconds", type=float, default=60.0)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.execute_live and args.offline_replay:
        print("choose at most one of --execute-live and --offline-replay", file=sys.stderr)
        return 2

    try:
        budgets = MatrixBudgets(
            max_logical_calls=args.max_logical_calls,
            max_attempts_per_logical_call=args.max_attempts_per_call,
            max_provider_attempts=args.max_provider_attempts,
            max_wall_seconds=args.max_wall_seconds,
            max_retained_response_bytes=args.max_retained_response_bytes,
            max_response_bytes=args.max_response_bytes,
            requests_per_second=args.requests_per_second,
            max_in_flight=args.max_in_flight,
            http_timeout_seconds=args.http_timeout_seconds,
        )
    except MatrixError as exc:
        print(f"budget error: {exc}", file=sys.stderr)
        return 2

    provider_orgs = (str(args.primary_org), str(args.secondary_org))

    if args.print_matrix_id:
        try:
            plan = build_matrix_plan(
                registry_store_root=args.registry_store_root,
                provider_orgs=provider_orgs,
            )
        except (MatrixError, MatrixSafetyStop) as exc:
            print(f"plan failed: {exc}", file=sys.stderr)
            return 1
        print(plan.matrix_id)
        return 0

    if args.execute_live:
        mode = "execute_live"
        primary_url = os.environ.get("ETHEREUM_RPC_URL")
        secondary_url = os.environ.get("ETHEREUM_RPC_URL_SECONDARY")
        if not primary_url or not secondary_url:
            print(
                "execute-live requires ETHEREUM_RPC_URL and ETHEREUM_RPC_URL_SECONDARY",
                file=sys.stderr,
            )
            return 2
        if not args.confirm_matrix_id:
            print("execute-live requires --confirm-matrix-id", file=sys.stderr)
            return 2
        if provider_orgs != DEFAULT_PROVIDER_ORGS:
            print(
                f"execute-live rejects caller provider orgs; use {DEFAULT_PROVIDER_ORGS}",
                file=sys.stderr,
            )
            return 2
        live_run_dir = None
    elif args.offline_replay:
        mode = "offline_replay"
        primary_url = None
        secondary_url = None
        if not args.live_run_dir:
            print("offline-replay requires --live-run-dir", file=sys.stderr)
            return 2
        live_run_dir = args.live_run_dir
    else:
        mode = "plan_only"
        primary_url = None
        secondary_url = None
        live_run_dir = None

    try:
        config = MatrixConfig(
            registry_store_root=args.registry_store_root,
            output_root=args.output_root,
            mode=mode,  # type: ignore[arg-type]
            provider_orgs=provider_orgs,
            budgets=budgets,
            primary_rpc_url=primary_url,
            secondary_rpc_url=secondary_url,
            confirm_matrix_id=args.confirm_matrix_id,
            live_run_dir=live_run_dir,
        )
    except (MatrixError, MatrixSafetyStop) as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    harness = PairEventV2MatrixHarness(config)
    try:
        report = harness.run()
    except MatrixSafetyStop as exc:
        print(f"SAFETY STOP: {exc}", file=sys.stderr)
        return 1
    except MatrixError as exc:
        print(f"matrix error: {exc}", file=sys.stderr)
        return 1
    finally:
        harness.close()

    summary = {
        "matrix_id": report.get("matrix_id"),
        "run_id": report.get("run_id"),
        "mode": report.get("mode"),
        "status": report.get("status"),
        "complete": report.get("complete"),
        "pass": report.get("pass"),
        "detail": report.get("detail"),
        "evidence_hash": report.get("evidence_hash"),
        "report_hash": report.get("report_hash"),
        "cell_count": len(report.get("cells") or []),
        "all_cells_pass": report.get("all_cells_pass"),
        "recommendation": report.get("recommendation"),
        "high_water": report.get("high_water"),
        "output_root": str(Path(args.output_root).resolve()),
        "run_dir": report.get("run_dir"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if mode == "plan_only":
        return 0
    if report.get("pass") is True and report.get("complete") is True:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
