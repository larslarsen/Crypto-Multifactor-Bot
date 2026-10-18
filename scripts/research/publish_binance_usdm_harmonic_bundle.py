"""Prepare, publish, or verify one CEX-002 harmonic reference release.

The command is a thin gate. It cannot override authority hashes, symbols, dates,
schemas, or resource pins. Publication stays invisible until catalog commit.
Verification reads the publication again and reauthenticates the consumer proof.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cryptofactors.catalog.dataset.errors import DatasetError
from cryptofactors.ingest.binance_usdm_harmonic_bundle import (
    AssemblyPolicy,
    prepare_harmonic_bundle,
    production_assembly_policy,
    publish_harmonic_bundle,
    verify_harmonic_bundle,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="publish_binance_usdm_harmonic_bundle")
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--repo", required=True, type=Path)
    shared.add_argument("--catalog", required=True, type=Path)
    shared.add_argument("--code-commit", required=True)
    proof = argparse.ArgumentParser(add_help=False)
    proof.add_argument("--proof", required=True, type=Path)
    proof.add_argument("--proof-sha", required=True)
    proof.add_argument("--checker-sha", required=True)
    proof.add_argument("--nautilus-version", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare", parents=[shared])
    publish = commands.add_parser("publish", parents=[shared, proof])
    publish.add_argument("--prepared-sha", required=True)
    verify = commands.add_parser("verify", parents=[shared, proof])
    verify.add_argument("--publication-sha", required=True)
    return parser


def _policy(args: argparse.Namespace, injected: AssemblyPolicy | None) -> AssemblyPolicy:
    if injected is None:
        return production_assembly_policy(args.repo, args.catalog, args.code_commit, Path(__file__))
    if injected.code_commit != args.code_commit or injected.repo.resolve() != args.repo.resolve():
        raise DatasetError(
            "injected policy does not match the command",
            context={"blocker": "code_commit"},
        )
    if injected.catalog_path.resolve() != args.catalog.resolve():
        raise DatasetError(
            "injected catalog does not match the command",
            context={"blocker": "unsafe_path"},
        )
    return injected


def main(argv: list[str] | None = None, policy: AssemblyPolicy | None = None) -> int:
    """Return 0 on success, 1 on an operational failure, and 2 on usage errors."""

    try:
        args = _parser().parse_args(argv)
        selected = _policy(args, policy)
        if args.command == "prepare":
            prepared = prepare_harmonic_bundle(selected)
            sys.stdout.write(prepared.descriptor_sha256 + "\n")
            return 0
        if args.command == "publish":
            published = publish_harmonic_bundle(
                selected,
                args.prepared_sha,
                args.proof,
                proof_sha256=args.proof_sha,
                checker_sha256=args.checker_sha,
                nautilus_version=args.nautilus_version,
            )
            sys.stdout.write(published.publication_sha256 + "\n")
            return 0
        verified = verify_harmonic_bundle(
            selected,
            args.publication_sha,
            args.proof,
            proof_sha256=args.proof_sha,
            checker_sha256=args.checker_sha,
            nautilus_version=args.nautilus_version,
        )
        sys.stdout.write(verified.publication_sha256 + "\n")
        return 0
    except SystemExit as exc:
        if exc.code in (None, 0):
            return 0
        return int(exc.code) if type(exc.code) is int else 2
    except DatasetError as exc:
        blocker = str(exc.context.get("blocker") or "release_error")
        sys.stderr.write(f"{blocker}: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
