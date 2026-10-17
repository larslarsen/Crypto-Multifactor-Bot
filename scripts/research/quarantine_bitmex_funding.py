#!/usr/bin/env python3
"""CEX-002 Gate 0: exact-five catalog quarantine with read-only dry-run."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Sequence

from cryptofactors.acquisition.bitmex_funding_quarantine import (
    execute_bitmex_funding_quarantine,
    validate_report_destination,
    write_quarantine_report,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.errors import DatasetError, QuarantineReportError
from cryptofactors.catalog.dataset.paths import assert_no_symlink_components, assert_regular_file

DEFAULT_REPORT = Path("research/sprint_004/CEX002_BITMEX_QUARANTINE.json")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CEX-002 exact-five BitMEX quarantine")
    parser.add_argument("--db-path", type=Path, default=Path("exp003.db"))
    parser.add_argument("--store-root", type=Path, default=Path("data/exp003_store"))
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--dry-run", action="store_true", help="Read-only inspection; no migrations")
    args = parser.parse_args(argv)
    connection = None
    try:
        database = args.db_path.absolute()
        assert_no_symlink_components(database, stop_at=Path(database.anchor))
        assert_regular_file(database, label="existing catalog")
        # Validate before acquiring a write transaction so obvious output mistakes
        # cannot produce an avoidable post-commit reporting failure.
        validate_report_destination(args.report_path, database_path=database,
                                    store_root=args.store_root)
        mode = "ro" if args.dry_run else "rw"
        connection = sqlite3.connect(database.as_uri() + "?mode=" + mode, uri=True)
        if args.dry_run:
            connection.execute("PRAGMA query_only = ON")
        catalog = SqliteDatasetCatalog(database, connection=connection)
        report = execute_bitmex_funding_quarantine(catalog, args.store_root, dry_run=args.dry_run)
    except (DatasetError, OSError, ValueError, sqlite3.Error) as exc:
        print(f"ERROR: quarantine did not complete: {exc}", file=sys.stderr)
        return 1
    finally:
        if connection is not None:
            connection.close()
    try:
        write_quarantine_report(report, args.report_path)
    except QuarantineReportError as exc:
        print(f"ERROR: catalog disposition={report.disposition}; applied={report.applied}; "
              f"idempotent_replay={report.idempotent_replay}. {exc}. "
              "Reporting failure does not roll back a completed catalog transaction; "
              "a genuine replay can recover the report.", file=sys.stderr)
        return 2
    print(f"disposition={report.disposition} applied={report.applied} dry_run={report.dry_run} "
          f"idempotent_replay={report.idempotent_replay}; report={args.report_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
