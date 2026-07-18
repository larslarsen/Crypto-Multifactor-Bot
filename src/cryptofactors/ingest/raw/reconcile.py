"""Orphan temporary-file reconciliation with active-writer lease awareness."""

from __future__ import annotations

import os
import stat as statmod
import time
from pathlib import Path

from cryptofactors.ingest.raw.models import (
    OrphanReconciliationReport,
    OrphanTempCandidate,
    RawObjectStoreConfig,
)

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

_TEMP_PREFIX = ".partial-"
_TEMP_SUFFIX = ".part"


def _is_managed_temp_name(name: str) -> bool:
    return name.startswith(_TEMP_PREFIX) and name.endswith(_TEMP_SUFFIX)


def _is_actively_locked(path: Path) -> bool:
    """Return True if another process holds an exclusive flock on the file."""
    if fcntl is None:
        return False
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return True  # locked by another holder
        # We acquired the lock → not active by another writer; release.
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        return False
    finally:
        os.close(fd)


def reconcile_orphan_temps(
    config: RawObjectStoreConfig,
    *,
    min_age_seconds: float = 3600.0,
    dry_run: bool = True,
    now: float | None = None,
) -> OrphanReconciliationReport:
    """Search only the configured temp area; never touch accepted objects.

    Removable only when:
    - directly under ``config.temp_dir()``;
    - managed partial name;
    - not a symlink;
    - not actively locked;
    - age strictly greater than ``min_age_seconds``;
    - and ``dry_run`` is False.
    """
    if min_age_seconds < 0:
        raise ValueError("min_age_seconds must be >= 0")

    temp_dir = config.temp_dir()
    temp_dir.mkdir(parents=True, exist_ok=True)
    clock = time.time() if now is None else now

    candidates: list[OrphanTempCandidate] = []
    scanned = 0
    active_locked = 0
    preserved_recent = 0
    stale_count = 0
    removed_count = 0
    remove_failed = 0
    preserved_non_matching = 0

    try:
        entries = list(os.scandir(temp_dir))
    except FileNotFoundError:
        entries = []

    for entry in entries:
        # Never follow symlinks.
        try:
            st = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        if entry.is_symlink():
            preserved_non_matching += 1
            scanned += 1
            candidates.append(
                OrphanTempCandidate(
                    path=Path(entry.path),
                    size_bytes=0,
                    age_seconds=0.0,
                    active=False,
                    stale=False,
                    removed=False,
                    reason="symlink_skipped",
                )
            )
            continue
        if not statmod.S_ISREG(st.st_mode):
            continue
        scanned += 1
        name = entry.name
        path = Path(entry.path)

        if not _is_managed_temp_name(name):
            preserved_non_matching += 1
            candidates.append(
                OrphanTempCandidate(
                    path=path,
                    size_bytes=st.st_size,
                    age_seconds=max(0.0, clock - st.st_mtime),
                    active=False,
                    stale=False,
                    removed=False,
                    reason="name_does_not_match_partial_pattern",
                )
            )
            continue

        age = max(0.0, clock - st.st_mtime)
        active = _is_actively_locked(path)
        if active:
            active_locked += 1
            candidates.append(
                OrphanTempCandidate(
                    path=path,
                    size_bytes=st.st_size,
                    age_seconds=age,
                    active=True,
                    stale=False,
                    removed=False,
                    reason="active_writer_lease_preserved",
                )
            )
            continue

        if age <= min_age_seconds:
            preserved_recent += 1
            candidates.append(
                OrphanTempCandidate(
                    path=path,
                    size_bytes=st.st_size,
                    age_seconds=age,
                    active=False,
                    stale=False,
                    removed=False,
                    reason="recent_temp_preserved",
                )
            )
            continue

        stale_count += 1
        removed = False
        reason = "stale_unlocked_temp_would_remove" if dry_run else "stale_unlocked_temp_removed"
        if not dry_run:
            # Re-check lock immediately before delete.
            if _is_actively_locked(path):
                active_locked += 1
                stale_count -= 1
                candidates.append(
                    OrphanTempCandidate(
                        path=path,
                        size_bytes=st.st_size,
                        age_seconds=age,
                        active=True,
                        stale=False,
                        removed=False,
                        reason="active_writer_lease_preserved",
                    )
                )
                continue
            try:
                path.unlink()
                removed = True
                removed_count += 1
            except OSError:
                reason = "stale_temp_remove_failed"
                remove_failed += 1
                removed = False
        candidates.append(
            OrphanTempCandidate(
                path=path,
                size_bytes=st.st_size,
                age_seconds=age,
                active=False,
                stale=True,
                removed=removed,
                reason=reason,
            )
        )

    candidates.sort(key=lambda c: c.path.as_posix())
    return OrphanReconciliationReport(
        temp_dir=temp_dir,
        dry_run=dry_run,
        min_age_seconds=min_age_seconds,
        scanned=scanned,
        active_locked=active_locked,
        preserved_recent=preserved_recent,
        stale_candidates=stale_count,
        removed=removed_count,
        remove_failed=remove_failed,
        preserved_non_matching=preserved_non_matching,
        candidates=tuple(candidates),
    )
