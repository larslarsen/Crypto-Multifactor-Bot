#!/usr/bin/env python3
"""CEX-002 Gate 1 — qualify free Binance USD-M and Coinalyze sources.

The Coinalyze key is read only from COINALYZE_API_KEY. Incomplete required
source coverage exits non-zero by default.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    FapiCurrentContractSource,
    HttpxCoinalyzeTransport,
    SourceQualificationError,
    TransportObjectIndex,
    accept_qualification,
    qualification_exit_code,
    run_source_qualification,
    write_qualification_report,
)
from source_audit.download import HttpxTransport, TimeoutConfig

DEFAULT_REPORT = Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CEX-002 Binance USD-M free-source qualification"
    )
    parser.add_argument("--store-root", type=str, default="data/cex002_qualify")
    parser.add_argument("--progress-path", type=str, default=None)
    parser.add_argument("--report-path", type=str, default=str(DEFAULT_REPORT))
    args = parser.parse_args(argv)

    store_root = Path(args.store_root)
    store_root.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("COINALYZE_API_KEY")
    if api_key is not None and not str(api_key).strip():
        api_key = None

    transport = HttpxTransport()
    timeout = TimeoutConfig()
    index = TransportObjectIndex(
        transport,
        timeout=timeout,
        list_cache_dir=store_root / "list_cache",
    )
    current = FapiCurrentContractSource(
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
            coinalyze_transport=coinalyze,
            coinalyze_api_key=api_key,
        )
    except SourceQualificationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    report_path = Path(args.report_path)
    write_qualification_report(report, report_path)
    print(f"Qualification report written to {report_path}", file=sys.stderr)
    print(
        f"gate_status={report.gate_status} accepted={report.accepted} "
        f"symbols={len(report.discovered_symbols)} "
        f"blocked={list(report.blocked_products)}",
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
