#!/usr/bin/env python3
"""CEX-002 Gate-2 listing-only revision candidate planner (ADR-0031).

Production paths are derived from this script's repository location:
`data/cex002_qualify/gate2` and sibling `data/cex002_qualify/gate2_revision_candidate`.
The command has no store, family, symbol, key, or date filter, reads no Coinalyze
secret, downloads no raw ZIP, and does not edit the active gate2 tree. A complete
candidate is evidence only: it accepts no revision and authorizes no acquisition.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, TextIO

from cryptofactors.acquisition.binance_usdm_gate2_revision_candidate import (
    EXIT_COMPLETE,
    EXIT_RESUMABLE_PARTIAL,
    PRODUCTION_PINS,
    PlannerHooks,
    PlannerPaths,
    PlannerPins,
    canonical_json,
    plan_revision_candidate,
    production_paths,
)


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=__doc__)


def main(
    argv: list[str] | None = None,
    *,
    pins: PlannerPins | None = None,
    hooks: PlannerHooks | None = None,
    transport: Any = None,
    paths: PlannerPaths | None = None,
    repository: Path | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    resolved = paths or production_paths(
        repository or Path(__file__).resolve().parents[2]
    )
    result = plan_revision_candidate(
        resolved,
        pins or PRODUCTION_PINS,
        hooks=hooks,
        transport=transport,
    )
    exit_code = int(result["exit_code"])
    stop = str(result.get("stop_reason") or "blocked")
    print(
        f"command=plan_revision_candidate exit={exit_code} stop={stop}",
        file=err,
    )
    if exit_code == EXIT_COMPLETE:
        print(AUTHORIZATION_NOTE, file=err)
        body = canonical_json(result["receipt"])
        buf = out.buffer if hasattr(out, "buffer") else out
        buf.write(body)
        if hasattr(buf, "flush"):
            buf.flush()
    elif exit_code == EXIT_RESUMABLE_PARTIAL:
        print(f"ERROR: {result['message']}", file=err)
        print(f"checkpoint={result.get('checkpoint_path') or ''}", file=err)
    else:
        print(f"ERROR: {result['message']}", file=err)
    return exit_code


AUTHORIZATION_NOTE = (
    "note: this candidate is evidence only; it accepts no revision and "
    "authorizes no acquisition"
)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
