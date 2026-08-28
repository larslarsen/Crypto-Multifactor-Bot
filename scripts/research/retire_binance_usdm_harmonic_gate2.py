#!/usr/bin/env python3
"""Inspect or retire the rejected CEX-002 Gate-2 store under ADR-0030.

Production paths are derived from this script's repository location and the
pinned review-330 authority. The command does not accept an arbitrary store or
destination. Retirement requires the exact rejected plan-receipt digest.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, TextIO

from cryptofactors.acquisition.binance_usdm_harmonic_gate2_retirement import (
    EXIT_COMPLETE,
    EXIT_INDETERMINATE,
    EXIT_SAFE,
    IndeterminateRetirementError,
    RetirementError,
    SafeRetirementError,
    canonical_json,
    inspect_gate2,
    retire_gate2,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect", help="read-only proof of the rejected active tree")
    retire = sub.add_parser("retire", help="atomic no-replace preservation rename")
    retire.add_argument(
        "--confirm",
        required=True,
        help="exact rejected plan-receipt SHA-256",
    )
    return parser


def _emit(
    document: dict[str, Any],
    *,
    command: str,
    stdout: Any,
    stderr: Any,
) -> int:
    body = canonical_json(document)
    try:
        buf = stdout.buffer if hasattr(stdout, "buffer") else stdout
        written = buf.write(body)
        if written is not None and written < len(body):
            raise OSError("short write")
        buf.flush()
    except (BrokenPipeError, OSError, ValueError):
        message = (
            "ERROR: retirement receipt could not be delivered\n"
            if command == "retire"
            else "ERROR: inspection output could not be delivered\n"
        )
        try:
            stderr.write(message)
            stderr.flush()
        except (BrokenPipeError, OSError, ValueError):
            pass
        return EXIT_INDETERMINATE if command == "retire" else EXIT_SAFE
    return EXIT_COMPLETE


def main(
    argv: list[str] | None = None,
    *,
    repository: Path | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    authority_path: Path | None = None,
    authority_digest: str | None = None,
    inspect_fn: Callable[..., dict[str, Any]] = inspect_gate2,
    retire_fn: Callable[..., dict[str, Any]] = retire_gate2,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo = repository if repository is not None else Path(__file__).resolve().parents[2]
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    extra: dict[str, Any] = {}
    if authority_path is not None:
        extra["authority_path"] = authority_path
        extra["authority_digest"] = authority_digest
    try:
        if args.command == "inspect":
            document = inspect_fn(repository=repo, **extra)
        elif args.command == "retire":
            document = retire_fn(
                repository=repo, confirm=str(args.confirm), **extra
            )
        else:
            parser.error("unknown command")
    except IndeterminateRetirementError as exc:
        print(f"ERROR: {exc.message}", file=err)
        print(
            f"source_exists={exc.source_exists} destination_exists={exc.destination_exists}",
            file=err,
        )
        return EXIT_INDETERMINATE
    except SafeRetirementError as exc:
        print(f"ERROR: {exc.message}", file=err)
        return EXIT_SAFE
    except RetirementError as exc:
        print(f"ERROR: {exc.message}", file=err)
        return EXIT_SAFE
    return _emit(document, command=str(args.command), stdout=out, stderr=err)


if __name__ == "__main__":
    raise SystemExit(main())
