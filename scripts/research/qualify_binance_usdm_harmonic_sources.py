#!/usr/bin/env python3
"""CEX-002 Gate 1 — qualify free Binance USD-M and Coinalyze sources.

The Coinalyze key is read only from COINALYZE_API_KEY. Incomplete required
source coverage exits non-zero by default.

Listing pages and verified samples are checkpointed durably, retained evidence is
bootstrapped and reused instead of redownloaded, and transient transport failures are
retried under a bounded policy.

`--apply-reviewed-v4-migration-only` applies the single reviewed ADR-0020 transition. It is
fixed to the accepted report, candidate plan/envelope, prior version-2 lock, legacy ledger,
and complete-cost identities, accepts no operator authority, writes the prepared amendment
ledger before the version-4 lock, keeps the legacy ledger byte-identical, treats the
accepted report and its manifest artifacts as read-only, and downloads no sample.

`--candidate-plan-only` proves the durable version-2 lock and legacy ledger before this
process creates or touches anything, then constructs the version-4 candidate plan from that
read-only prior authority. It migrates no plan or ledger, downloads no sample, and proves
the durable version-2 lock and legacy budget bytes are unchanged.

The sample plan is locked once and replayed immutably; a resume changes execution state
only and any genuine change to the locked inputs fails closed before download. There is no
in-band switch to re-select: a new plan version requires a fresh reviewer authorization.
New sample downloads are reserved before acquisition and settled after verification
against a single cumulative Gate 1 allowance that a new invocation never restores.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    BUDGET_LEDGER_FILENAME,
    GATE1_NEW_DOWNLOAD_BUDGET_BYTES,
    LISTING_DEFAULT_WORKERS,
    LISTING_MAX_WORKERS,
    SAMPLE_PLAN_LOCK_FILENAME,
    VISION_S3_ENDPOINT,
    FapiCurrentContractSource,
    FapiDeliveryPriceSource,
    HttpxCoinalyzeTransport,
    ListingCheckpointStore,
    ResumeIntegrityError,
    RetryJournal,
    RetryPolicy,
    RetryRunner,
    SourceQualificationError,
    TransportObjectIndex,
    accept_qualification,
    candidate_preflight,
    qualification_exit_code,
    reviewed_migration_preflight,
    run_source_qualification,
    write_qualification_report,
)
from source_audit.download import PooledHttpxTransport, TimeoutConfig

DEFAULT_REPORT = Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json")


def cleanup_execution_resources(
    transport: PooledHttpxTransport, checkpoint: ListingCheckpointStore
) -> BaseException | None:
    """Attempt both cleanup actions and return the first failure, if any.

    Both actions always run: closing the connection pool never skips the checkpoint
    boundary flush, and a later failure never replaces the first one.
    """
    first: BaseException | None = None
    for action in (transport.close, checkpoint.flush):
        try:
            action()
        except BaseException as exc:  # noqa: BLE001 - returned to the caller below
            if first is None:
                first = exc
    return first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CEX-002 Binance USD-M free-source qualification"
    )
    parser.add_argument("--store-root", type=str, default="data/cex002_qualify")
    parser.add_argument("--progress-path", type=str, default=None)
    parser.add_argument("--report-path", type=str, default=str(DEFAULT_REPORT))
    parser.add_argument(
        "--listing-checkpoint-path",
        type=str,
        default=None,
        help="request-keyed listing checkpoint (default: <store-root>/cex002_listing_checkpoint.json)",
    )
    parser.add_argument(
        "--sample-budget-bytes",
        type=int,
        default=GATE1_NEW_DOWNLOAD_BUDGET_BYTES,
        help="total NEW sample download budget; may only lower the Gate 1 default",
    )
    parser.add_argument("--retry-max-attempts", type=int, default=5)
    parser.add_argument(
        "--listing-workers",
        type=int,
        default=LISTING_DEFAULT_WORKERS,
        help=(
            "finite ceiling on simultaneous independent listing requests; clamped to "
            f"{LISTING_MAX_WORKERS}. Retry budgets stay per request"
        ),
    )
    parser.add_argument(
        "--candidate-plan-only",
        action="store_true",
        help=(
            "construct the version-4 candidate plan from read-only prior authority: no "
            "plan or ledger migration, no sample download, and no relock"
        ),
    )
    parser.add_argument(
        "--apply-reviewed-v4-migration-only",
        action="store_true",
        help=(
            "apply the one reviewed ADR-0020 version-4 transition: it is fixed to the "
            "accepted report, candidate, prior lock, legacy ledger, and complete-cost "
            "identities, takes no plan, digest, version, allowance, ledger, relock, or "
            "download authority, and stops before every sample acquisition"
        ),
    )
    args = parser.parse_args(argv)

    # The Gate 1 execution budget may be tightened but never raised. There is no
    # independent per-object cap: an object that cannot fit remaining allowance blocks.
    sample_budget = min(int(args.sample_budget_bytes), GATE1_NEW_DOWNLOAD_BUDGET_BYTES)

    store_root = Path(args.store_root)
    report_path = Path(args.report_path)
    apply_migration = bool(args.apply_reviewed_v4_migration_only)

    if apply_migration and args.candidate_plan_only:
        print(
            "ERROR: candidate construction and reviewed migration are separate transitions",
            file=sys.stderr,
        )
        return 1

    if apply_migration:
        # The reviewed transition proves its whole authority before this process creates
        # the store, a transport, a listing cache, a checkpoint, a journal, or reads a
        # credential. An invalid transition must change nothing at all.
        try:
            reviewed_migration_preflight(store_root=store_root, report_path=report_path)
        except (SourceQualificationError, ResumeIntegrityError) as exc:
            print(f"ERROR: {exc.message}", file=sys.stderr)
            return 1

    if args.candidate_plan_only:
        # Prove the exact prior authority before this process creates the store,
        # constructs a transport, loads a listing cache, checkpoint, or retry journal, or
        # reads a credential. An invalid transition must change nothing at all.
        try:
            candidate_preflight(
                plan_lock_path=store_root / SAMPLE_PLAN_LOCK_FILENAME,
                budget_ledger_path=store_root / BUDGET_LEDGER_FILENAME,
                budget_bytes=sample_budget,
            )
        except (SourceQualificationError, ResumeIntegrityError) as exc:
            # ``ResumeIntegrityError`` is a ``SourceQualificationError`` subclass; both are
            # named for clarity. Only the message is printed, never authority content or a
            # credential.
            print(f"ERROR: {exc.message}", file=sys.stderr)
            return 1

    store_root.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("COINALYZE_API_KEY")
    if api_key is not None and not str(api_key).strip():
        api_key = None

    timeout = TimeoutConfig()
    listing_workers = max(1, min(int(args.listing_workers), LISTING_MAX_WORKERS))
    # One bounded connection pool per invocation, closed deterministically below on
    # success, error, or cancellation.
    transport = PooledHttpxTransport(max_connections=listing_workers, timeout=timeout)
    list_cache_dir = store_root / "list_cache"
    checkpoint_path = (
        Path(args.listing_checkpoint_path)
        if args.listing_checkpoint_path
        else store_root / "cex002_listing_checkpoint.json"
    )
    listing_checkpoint = ListingCheckpointStore.load(checkpoint_path, list_cache_dir)
    bootstrapped = listing_checkpoint.bootstrap(endpoint=VISION_S3_ENDPOINT)
    print(
        "listing checkpoint bootstrap: "
        f"claimed={bootstrapped['claimed']} "
        f"checksum_blobs={bootstrapped['checksum_blobs']} "
        f"skipped_already_bound={bootstrapped['skipped_already_bound']} "
        f"unclaimed={bootstrapped['unclaimed']}",
        file=sys.stderr,
    )
    retry = RetryRunner(
        policy=RetryPolicy(max_attempts=int(args.retry_max_attempts)),
        journal=RetryJournal.load(store_root / "cex002_retry_journal.json"),
    )
    index = TransportObjectIndex(
        transport,
        timeout=timeout,
        list_cache_dir=list_cache_dir,
        checkpoint=listing_checkpoint,
        retry=retry,
    )
    current = FapiCurrentContractSource(
        transport,
        cache_dir=store_root / "fapi_cache",
        timeout=timeout,
    )
    # ADR-0020: read-only official settlement-price evidence for exactly the frozen
    # delivery pairs, retained content-addressably beside the other official responses.
    delivery_prices = FapiDeliveryPriceSource(
        transport,
        cache_dir=store_root / "fapi_cache",
        timeout=timeout,
    )
    coinalyze = None
    if api_key is not None:
        coinalyze = HttpxCoinalyzeTransport(
            transport,
            cache_dir=store_root / "coinalyze_cache",
            timeout=timeout,
        )
    try:
        report = run_source_qualification(
            store_root=store_root,
            index=index,
            transport=transport,
            progress_path=Path(args.progress_path) if args.progress_path else None,
            current_contracts=current,
            delivery_prices=delivery_prices,
            coinalyze_transport=coinalyze,
            coinalyze_api_key=api_key,
            retry=retry,
            listing_checkpoint=listing_checkpoint,
            candidate_plan_only=bool(args.candidate_plan_only),
            apply_reviewed_v4_migration=apply_migration,
            migration_report_path=report_path if apply_migration else None,
            listing_workers=listing_workers,
            sample_budget_bytes=sample_budget,
        )
    except SourceQualificationError as exc:
        # Documented precedence: an already active body failure stays primary. Cleanup
        # still runs in full, and any cleanup failure is reported after it, never
        # substituted for it.
        print(f"ERROR: {exc}", file=sys.stderr)
        cleanup_error = cleanup_execution_resources(transport, listing_checkpoint)
        if cleanup_error is not None:
            print(f"ERROR: cleanup failed: {cleanup_error}", file=sys.stderr)
        return 1
    except BaseException:
        cleanup_error = cleanup_execution_resources(transport, listing_checkpoint)
        if cleanup_error is not None:
            print(f"ERROR: cleanup failed: {cleanup_error}", file=sys.stderr)
        raise

    # The body succeeded, so the first cleanup failure is the primary error.
    cleanup_error = cleanup_execution_resources(transport, listing_checkpoint)
    if cleanup_error is not None:
        raise cleanup_error

    if apply_migration:
        # The accepted report is immutable authority. Migration emits its receipt to this
        # transcript and never replaces that path or republishes a manifest detail.
        receipt = report.candidate_plan.get("migration") or {}
        print(
            "reviewed_v4_migration: "
            + json.dumps(receipt, sort_keys=True, default=str),
            file=sys.stderr,
        )
    else:
        # ADR-0019: the complete manifest detail is published content-addressably beneath
        # the store's evidence root, and the tracked receipt carries only its descriptor.
        detail = write_qualification_report(report, report_path, store_root=store_root)
        print(f"Qualification report written to {report_path}", file=sys.stderr)
        print(
            f"manifest_detail: path={detail['relative_path']} "
            f"uncompressed_sha256={detail['uncompressed_sha256']} "
            f"uncompressed_bytes={detail['uncompressed_bytes']} "
            f"compressed_sha256={detail['compressed_sha256']} "
            f"compressed_bytes={detail['compressed_bytes']} "
            f"records={detail['record_counts']} "
            f"reused_existing={detail['reused_existing']}",
            file=sys.stderr,
        )
    print(
        f"gate_status={report.gate_status} accepted={report.accepted} "
        f"symbols={len(report.discovered_symbols)} "
        f"blocked={list(report.blocked_products)}",
        file=sys.stderr,
    )
    plan = report.sample_plan
    print(
        f"sample_plan: planned_new_bytes={plan['new_download_bytes']} "
        f"budget={plan['budget_bytes']} retained_bytes={plan['retained_bytes']} "
        f"budget_blocked={len(plan['blocked'])}",
        file=sys.stderr,
    )
    print(
        f"plan_lock: version={report.plan_lock.get('plan_version')} "
        f"state={report.plan_lock.get('state')} "
        f"plan_digest={report.plan_lock.get('plan_digest')} "
        f"superseded={report.plan_lock.get('superseded_plan_versions')}",
        file=sys.stderr,
    )
    print(
        f"budget: charged={report.budget.get('charged_bytes')} "
        f"spent_range=[{report.budget.get('cumulative_spent_min_bytes')},"
        f"{report.budget.get('cumulative_spent_max_bytes')}] "
        f"remaining={report.budget.get('cumulative_remaining_bytes')} "
        f"reserved={report.budget.get('reserved_bytes')} "
        f"legacy_state={report.budget.get('legacy_state')} "
        f"breach_state={report.budget.get('breach_state')}",
        file=sys.stderr,
    )
    print(
        f"membership: basis={report.membership.get('universe_basis')} "
        f"confirmed={report.membership.get('confirmed_count')} "
        f"unresolved={report.membership.get('unresolved_count')} "
        f"classes={report.membership.get('class_counts')}",
        file=sys.stderr,
    )
    feasibility = report.storage.get("gate2_feasibility", {})
    print(
        f"gate2_storage: state={feasibility.get('gate2_storage_state')} "
        f"selected_raw_bytes={feasibility.get('selected_compressed_raw_bytes')} "
        f"cost_sample_bytes={feasibility.get('cost_sample_compressed_raw_bytes')} "
        f"projected_new_bytes={feasibility.get('projected_new_compressed_raw_bytes')} "
        f"available_bytes={feasibility.get('local_available_bytes')} "
        f"total_required_bytes={feasibility.get('total_required_bytes')} "
        f"unknown_components={feasibility.get('unknown_total_components')}",
        file=sys.stderr,
    )
    candidate = report.candidate_plan
    print(
        f"candidate_plan: state={candidate.get('state')} "
        f"version={candidate.get('plan_version')} "
        f"prior_version={candidate.get('prior_plan_version')} "
        f"plan_digest={candidate.get('plan_digest')} "
        f"envelope_digest={candidate.get('candidate_envelope_digest')} "
        f"migration_authorized={candidate.get('migration_authorized')} "
        f"download_authorized={candidate.get('download_authorized')}",
        file=sys.stderr,
    )
    print(
        f"holdout: id={report.prospective_holdout.get('boundary_id')} "
        f"boundary_utc={report.prospective_holdout.get('boundary_utc')} "
        f"stream_collector={report.prospective_holdout.get('stream_collector_authorized')}",
        file=sys.stderr,
    )
    print(
        f"listing_checkpoint: reused={report.listing_checkpoint.get('reused_requests')} "
        f"fetched={report.listing_checkpoint.get('fetched_requests')} "
        f"unclaimed={report.listing_checkpoint.get('unclaimed_evidence')} "
        f"serializations={report.listing_checkpoint.get('serializations')} | "
        f"workers={listing_workers} "
        f"clients={transport.clients_constructed}/{transport.clients_closed} "
        f"retries={report.retry.get('retries')}",
        file=sys.stderr,
    )
    code = qualification_exit_code(report)
    if code != 0:
        try:
            accept_qualification(report)
        except SourceQualificationError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
        return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
