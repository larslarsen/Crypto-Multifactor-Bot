#!/usr/bin/env python3
"""CEX-002 ADR-0021 as amended by ADR-0024 — measure version-2 Gate-2 storage.

This executable is a thin fixed-policy adapter. It accepts only the locations of already
accepted bytes: there is no cohort, family, schema, coefficient, multiplicity,
compression, batch-size, overhead, credit, reserve, lifecycle, Coinalyze evidence, or
capacity option, because none of those may be chosen by an operator. The receipt
destination is the fixed version-2 repository target from review 230, and the accepted
version-1 receipt and its envelopes are immutable evidence this command never touches.
It performs no network call and needs no credential.

Exit status is measurement status, never gate status: non-zero when the accepted authority
or a measurement fails, zero when the receipt is honestly complete, whether its storage
preflight state is `sufficient` or `blocked`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    SIZING_RECEIPT_RELATIVE_PATH,
    SIZING_SCHEMA_VERSION,
    STATE_SUFFICIENT,
    AuthorityPaths,
    SizingError,
    run_storage_sizing,
)

DEFAULT_STORE = Path("data/cex002_qualify")
DEFAULT_REPORT = Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store-root", type=str, default=str(DEFAULT_STORE))
    parser.add_argument("--report-path", type=str, default=str(DEFAULT_REPORT))
    parser.add_argument("--manifest-detail-path", type=str, required=True)
    parser.add_argument("--lock-path", type=str, default="")
    parser.add_argument("--amendment-ledger-path", type=str, default="")
    parser.add_argument("--progress-checkpoint-path", type=str, default="")
    parser.add_argument("--listing-checkpoint-path", type=str, default="")
    parser.add_argument("--contract-metadata-path", type=str, default="")
    return parser


def resolve_paths(args: argparse.Namespace, *, repository: Path) -> AuthorityPaths:
    """Every location defaults inside the accepted store; identities stay pinned."""
    store = Path(args.store_root)
    return AuthorityPaths(
        store_root=store,
        report_path=Path(args.report_path),
        manifest_detail_path=Path(args.manifest_detail_path),
        qualification_source_path=repository
        / "src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py",
        qualification_cli_path=repository
        / "scripts/research/qualify_binance_usdm_harmonic_sources.py",
        lock_path=Path(args.lock_path)
        if args.lock_path
        else store / "cex002_sample_plan_lock.json",
        amendment_ledger_path=Path(args.amendment_ledger_path)
        if args.amendment_ledger_path
        else store / "cex002_amendment_ledger.json",
        progress_checkpoint_path=Path(args.progress_checkpoint_path)
        if args.progress_checkpoint_path
        else store / "cex002_qualification_progress.json",
        listing_checkpoint_path=Path(args.listing_checkpoint_path)
        if args.listing_checkpoint_path
        else store / "cex002_listing_checkpoint.json",
        contract_metadata_path=Path(args.contract_metadata_path)
        if args.contract_metadata_path
        else store / "cex002_official_contract_metadata.json",
        listing_cache_dir=store / "list_cache",
        coinalyze_cache_dir=store / "coinalyze_cache",
        sample_dir=store / "raw" / "sha256",
        sidecar_dir=store / "list_cache",
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repository = Path(__file__).resolve().parents[2]
    try:
        result = run_storage_sizing(
            resolve_paths(args, repository=repository),
            # The destination is the fixed reviewed target, never an operator choice.
            receipt_path=repository / SIZING_RECEIPT_RELATIVE_PATH,
            sizing_source_path=repository
            / "src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py",
            sizing_cli_path=Path(__file__).resolve(),
        )
    except SizingError as exc:
        # Only the message reaches the transcript: never authority content.
        print(f"ERROR: {exc.message}", file=sys.stderr)
        return 1

    receipt = result["receipt"]
    identity = result["receipt_file"]
    publication = result["publication"]
    action = "re-proved" if publication["rerun"] else "written"
    print(
        f"{SIZING_SCHEMA_VERSION} receipt {action} at {SIZING_RECEIPT_RELATIVE_PATH}",
        file=sys.stderr,
    )
    print(
        f"envelopes_published={publication['envelopes_published']} "
        f"envelopes_reused={publication['envelopes_reused']}",
        file=sys.stderr,
    )
    print(
        f"receipt_sha256={identity['receipt_sha256']} "
        f"receipt_bytes={identity['receipt_bytes']}",
        file=sys.stderr,
    )
    print(
        "storage_preflight_state="
        f"{receipt['storage_preflight_state']} "
        f"total_future_storage_bytes={receipt['capacity']['total_future_storage_bytes']} "
        f"post_publication_available_bytes="
        f"{receipt['filesystem']['post_publication_available_bytes']}",
        file=sys.stderr,
    )
    capacity = receipt["capacity"]
    print(
        "typed_normalized_partition_bytes="
        f"{capacity['typed_normalized_partition_bytes']} "
        f"catalog_manifest_bundle_bytes={capacity['catalog_manifest_bundle_bytes']} "
        f"bounded_temporary_work_bytes={capacity['bounded_temporary_work_bytes']}",
        file=sys.stderr,
    )
    if receipt["blockers"]:
        print("blockers: " + ",".join(receipt["blockers"]), file=sys.stderr)
    if receipt["storage_preflight_state"] == STATE_SUFFICIENT:
        print(
            "note: a sufficient storage preflight authorizes no acquisition and accepts "
            "no gate",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
