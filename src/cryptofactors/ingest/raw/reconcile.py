"""Orphan temporary-file reconciliation for the raw store."""

from __future__ import annotations

import os
import time
from pathlib import Path

from cryptofactors.ingest.raw.models import (
    OrphanReconciliationReport,
    OrphanTempCandidate,
    RawObjectStoreConfig,
)


# Only names created by RawObjectWriter (tempfile.mkstemp prefix/suffix).
_TEMP_PREFIX = ".partial-"
_TEMP_SUFFIX = ".part"


def _is_managed_temp_name(name: str) -> bool:
    return name.startswith(_TEMP_PREFIX) and name.endswith(_TEMP_SUFFIX)


def reconcile_orphan_temps(
    config: RawObjectStoreConfig,
    *,
    min_age_seconds: float = 3600.0,
    dry_run: bool = True,
    now: float | None = None,
) -> OrphanReconciliationReport:
    """Search only the configured temp area; never touch accepted objects.

    A candidate is removable only when:
    - it lives directly under ``config.temp_dir()``;
    - its name matches the managed partial pattern;
    - its age is strictly greater than ``min_age_seconds``;
    - and ``dry_run`` is False (otherwise report-only).

    Recent matching temps are preserved. Non-matching names are never removed.
    Accepted content under ``raw/sha256/...`` is never scanned for deletion.
    """
    if min_age_seconds < 0:
        raise ValueError("min_age_seconds must be >= 0")

    temp_dir = config.temp_dir()
    temp_dir.mkdir(parents=True, exist_ok=True)
    clock = time.time() if now is None else now

    candidates: list[OrphanTempCandidate] = []
    scanned = 0
    stale_count = 0
    removed_count = 0
    preserved_recent = 0
    preserved_non_matching = 0

    try:
        entries = list(os.scandir(temp_dir))
    except FileNotFoundError:
        entries = []

    for entry in entries:
        if not entry.is_file(follow_symlinks=False):
            continue
        scanned += 1
        name = entry.name
        path = Path(entry.path)

        if not _is_managed_temp_name(name):
            preserved_non_matching += 1
            candidates.append(
                OrphanTempCandidate(
                    path=path,
                    size_bytes=entry.stat(follow_symlinks=False).st_size,
                    age_seconds=max(0.0, clock - entry.stat(follow_symlinks=False).st_mtime),
                    stale=False,
                    removed=False,
                    reason="name_does_not_match_partial_pattern",
                )
            )
            continue

        st = entry.stat(follow_symlinks=False)
        age = max(0.0, clock - st.st_mtime)
        is_stale = age > min_age_seconds
        if not is_stale:
            preserved_recent += 1
            candidates.append(
                OrphanTempCandidate(
                    path=path,
                    size_bytes=st.st_size,
                    age_seconds=age,
                    stale=False,
                    removed=False,
                    reason="recent_temp_preserved",
                )
            )
            continue

        stale_count += 1
        removed = False
        reason = "stale_temp_would_remove" if dry_run else "stale_temp_removed"
        if not dry_run:
            try:
                path.unlink()
                removed = True
                removed_count += 1
            except OSError:
                reason = "stale_temp_remove_failed"
                removed = False
        candidates.append(
            OrphanTempCandidate(
                path=path,
                size_bytes=st.st_size,
                age_seconds=age,
                stale=True,
                removed=removed,
                reason=reason,
            )
        )

    # Sort for deterministic reports.
    candidates.sort(key=lambda c: c.path.as_posix())
    return OrphanReconciliationReport(
        temp_dir=temp_dir,
        dry_run=dry_run,
        min_age_seconds=min_age_seconds,
        scanned=scanned,
        stale_candidates=stale_count,
        removed=removed_count,
        preserved_recent=preserved_recent,
        preserved_non_matching=preserved_non_matching,
        candidates=tuple(candidates),
    )
