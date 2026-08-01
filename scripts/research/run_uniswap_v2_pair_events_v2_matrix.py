#!/usr/bin/env python3
"""DEX-003 — isolated v2 provider-matrix harness CLI (final source correction).

Default mode is plan-only (no RPC). Live execution requires both
``--execute-live`` and ``--confirm-matrix-id <computed-id>``.

Endpoints/credentials are runtime-only environment variables and are never
written into plan identity, receipts, raw metadata, logs, or reports.

Output root must be dedicated: not data/dex003_full, not the registry store,
not accepted dataset/staged trees, and not a DB with production v2 tables.
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
    MatrixStore,
    PairEventV2MatrixHarness,
    build_matrix_plan,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Uniswap V2 pair-event v2 provider-matrix harness "
            "(plan-only by default; live requires --execute-live)"
        )
    )
    p.add_argument(
        "--registry-store-root",
        type=Path,
        default=Path("data/dex003_full/store"),
        help="Content-addressed dataset store root containing the accepted registry",
    )
    p.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/dex003_v2_matrix"),
        help=(
            "Dedicated matrix output root (must not be data/dex003_full, "
            "registry store, accepted dataset, or staged production trees)"
        ),
    )
    p.add_argument(
        "--primary-org",
        default=os.environ.get("MATRIX_PRIMARY_ORG", DEFAULT_PROVIDER_ORGS[0]),
        help="Credential-free primary provider organization id",
    )
    p.add_argument(
        "--secondary-org",
        default=os.environ.get("MATRIX_SECONDARY_ORG", DEFAULT_PROVIDER_ORGS[1]),
        help="Credential-free secondary provider organization id",
    )
    p.add_argument(
        "--execute-live",
        action="store_true",
        help="Enable live RPC execution (requires --confirm-matrix-id)",
    )
    p.add_argument(
        "--confirm-matrix-id",
        default=None,
        help="Must equal the computed matrix ID before any live call",
    )
    p.add_argument(
        "--offline-replay",
        action="store_true",
        help=(
            "Standalone offline replay: authenticate sealed execute_live report "
            "before creating a replay run (no RPC; does not repoint live current_run)"
        ),
    )
    p.add_argument(
        "--print-matrix-id",
        action="store_true",
        help=(
            "Build pure plan and print matrix_id. Creates plan/catalog only on a "
            "fresh empty output root; otherwise authenticates immutable stored plan."
        ),
    )
    p.add_argument("--max-logical-calls", type=int, default=LOGICAL_CALL_CEILING)
    p.add_argument(
        "--max-attempts-per-call",
        type=int,
        default=DEFAULT_MAX_ATTEMPTS_PER_LOGICAL_CALL,
    )
    p.add_argument(
        "--max-provider-attempts",
        type=int,
        default=DEFAULT_MAX_PROVIDER_ATTEMPTS,
    )
    p.add_argument("--max-wall-seconds", type=float, default=DEFAULT_MAX_WALL_SECONDS)
    p.add_argument(
        "--max-retained-response-bytes",
        type=int,
        default=DEFAULT_MAX_RETAINED_RESPONSE_BYTES,
    )
    p.add_argument(
        "--max-response-bytes",
        type=int,
        default=DEFAULT_MAX_RESPONSE_BYTES,
    )
    p.add_argument(
        "--requests-per-second",
        type=float,
        default=DEFAULT_REQUESTS_PER_SECOND,
    )
    p.add_argument("--max-in-flight", type=int, default=DEFAULT_MAX_IN_FLIGHT)
    p.add_argument("--http-timeout-seconds", type=float, default=60.0)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

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
        store: MatrixStore | None = None
        try:
            # Pure rebuild for display identity.
            rebuilt = build_matrix_plan(
                registry_store_root=args.registry_store_root,
                provider_orgs=provider_orgs,
            )
            store = MatrixStore(
                args.output_root,
                registry_store_root=args.registry_store_root,
                create_run=False,
            )
            if store.has_immutable_plan():
                plan, _counters, _snap = store.authenticate_immutable_store(
                    expected_plan=rebuilt,
                    registry_store_root=args.registry_store_root,
                )
            else:
                if not store.is_fresh_empty():
                    raise MatrixSafetyStop(
                        "output root is not empty and has no immutable plan/catalog"
                    )
                store.create_plan_and_catalog(rebuilt)
                plan = rebuilt
        except (MatrixError, MatrixSafetyStop) as exc:
            print(f"plan failed: {exc}", file=sys.stderr)
            return 1
        finally:
            if store is not None:
                store.close()
        print(plan.matrix_id)
        return 0

    if args.execute_live:
        mode = "execute_live"
        primary_url = os.environ.get("ETHEREUM_RPC_URL")
        secondary_url = os.environ.get("ETHEREUM_RPC_URL_SECONDARY")
        if not primary_url or not secondary_url:
            print(
                "execute-live requires ETHEREUM_RPC_URL and "
                "ETHEREUM_RPC_URL_SECONDARY in the environment",
                file=sys.stderr,
            )
            return 2
        if not args.confirm_matrix_id:
            print(
                "execute-live requires --confirm-matrix-id <matrix_id>; "
                "run with --print-matrix-id first",
                file=sys.stderr,
            )
            return 2
        if provider_orgs != DEFAULT_PROVIDER_ORGS:
            print(
                "execute-live rejects caller-supplied provider organizations; "
                f"use {DEFAULT_PROVIDER_ORGS}",
                file=sys.stderr,
            )
            return 2
    elif args.offline_replay:
        mode = "offline_replay"
        primary_url = None
        secondary_url = None
    else:
        mode = "plan_only"
        primary_url = None
        secondary_url = None

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
        "complete": report.get("complete"),
        "pass": report.get("pass"),
        "detail": report.get("detail"),
        "evidence_hash": report.get("evidence_hash"),
        "report_hash": report.get("report_hash"),
        "cell_count": len(report.get("cells") or []),
        "all_cells_pass": report.get("all_cells_pass"),
        "live_report_authenticated": (report.get("offline_replay") or {}).get(
            "live_report_authenticated"
        )
        if isinstance(report.get("offline_replay"), dict)
        else report.get("live_report_authenticated"),
        "recommendation": report.get("recommendation"),
        "high_water": report.get("high_water"),
        "output_root": str(Path(args.output_root).resolve()),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if mode == "plan_only":
        return 0
    if report.get("pass") is True and report.get("complete") is True:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
