"""Streaming verification of dataset output files (MAN-001)."""

from __future__ import annotations

import hashlib
import os
import stat as statmod
from pathlib import Path

from cryptofactors.catalog.dataset.errors import OutputVerificationError, UnsafePathError
from cryptofactors.catalog.dataset.models import OutputFileSpec
from cryptofactors.catalog.dataset.paths import assert_no_symlink_components, assert_relative_safe


def stream_sha256_and_size(path: Path, *, chunk_size: int = 1024 * 1024) -> tuple[str, int]:
    if path.is_symlink():
        raise OutputVerificationError(
            "output must not be a symlink",
            context={"path": str(path)},
        )
    if not path.exists():
        raise OutputVerificationError("output missing", context={"path": str(path)})
    st = os.lstat(path)
    if not statmod.S_ISREG(st.st_mode):
        raise OutputVerificationError(
            "output is not a regular file",
            context={"path": str(path)},
        )
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def verify_outputs(
    *,
    sources: dict[str, Path],
    specs: list[OutputFileSpec] | tuple[OutputFileSpec, ...],
    root_for_symlink_stop: Path | None = None,
    chunk_size: int = 1024 * 1024,
) -> tuple[OutputFileSpec, ...]:
    """Verify declared outputs against local files without loading full content into RAM.

    ``sources`` maps relative_path → local source path.
    Every key in sources must appear in specs and vice versa.
    """
    spec_map = {s.relative_path: s for s in specs}
    if len(spec_map) != len(specs):
        raise OutputVerificationError("duplicate relative_path in output specs")

    source_keys = set(sources)
    spec_keys = set(spec_map)
    missing = spec_keys - source_keys
    unexpected = source_keys - spec_keys
    if missing:
        raise OutputVerificationError(
            "missing output sources for declared specs",
            context={"missing": sorted(missing)},
        )
    if unexpected:
        raise OutputVerificationError(
            "unexpected output sources not declared in specs",
            context={"unexpected": sorted(unexpected)},
        )

    verified: list[OutputFileSpec] = []
    for rel, spec in sorted(spec_map.items(), key=lambda kv: kv[0]):
        assert_relative_safe(rel, label="output relative_path")
        if not (spec.sha256 and len(spec.sha256) == 64):
            raise OutputVerificationError(
                "output sha256 must be 64 hex chars",
                context={"relative_path": rel},
            )
        if spec.rows < 0 or spec.bytes < 0:
            raise OutputVerificationError(
                "rows and bytes must be >= 0",
                context={"relative_path": rel},
            )
        src = sources[rel]
        if root_for_symlink_stop is not None:
            try:
                assert_no_symlink_components(src.resolve(), stop_at=root_for_symlink_stop)
            except UnsafePathError as exc:
                raise OutputVerificationError(str(exc), context=exc.context) from exc
        actual_hash, actual_size = stream_sha256_and_size(src, chunk_size=chunk_size)
        if actual_hash != spec.sha256.lower():
            raise OutputVerificationError(
                "output SHA-256 mismatch",
                context={
                    "relative_path": rel,
                    "expected": spec.sha256.lower(),
                    "actual": actual_hash,
                },
            )
        if actual_size != spec.bytes:
            raise OutputVerificationError(
                "output byte size mismatch",
                context={
                    "relative_path": rel,
                    "expected": spec.bytes,
                    "actual": actual_size,
                },
            )
        # Row count is an explicit declared boundary (not re-derived from binary format).
        verified.append(
            OutputFileSpec(
                relative_path=rel,
                sha256=actual_hash,
                rows=spec.rows,
                bytes=actual_size,
                partition=dict(spec.partition),
            )
        )
    return tuple(verified)
