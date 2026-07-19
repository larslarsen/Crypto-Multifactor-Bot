"""Streaming verification of dataset output files (MAN-001)."""

from __future__ import annotations

import hashlib
import stat as statmod
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TypeVar

from cryptofactors.catalog.dataset.canonicalize import canonical_relative_path
from cryptofactors.catalog.dataset.errors import OutputVerificationError
from cryptofactors.catalog.dataset.models import (
    OutputFileSpec,
    RowCountPolicy,
    RowCountReceipt,
)
from cryptofactors.catalog.dataset.paths import assert_relative_safe, lstat_path

_T = TypeVar("_T")


def stream_sha256_and_size(path: Path, *, chunk_size: int = 1024 * 1024) -> tuple[str, int]:
    st = lstat_path(path)
    if st is None:
        raise OutputVerificationError("output missing", context={"path": str(path)})
    if statmod.S_ISLNK(st.st_mode):
        raise OutputVerificationError(
            "output must not be a symlink",
            context={"path": str(path)},
        )
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


def _normalize_path_keyed_mapping(
    mapping: Mapping[str, _T],
    *,
    label: str,
) -> dict[str, _T]:
    """Re-key a mapping by canonical relative path without collapsing value types.

    Each call site specializes ``_T`` independently (``Path``, row-counter
    callables, ``RowCountReceipt``, etc.), so inference cannot contaminate one
    mapping's value type with another's.
    """
    out: dict[str, _T] = {}
    for key, value in mapping.items():
        path = canonical_relative_path(key)
        if path in out:
            raise OutputVerificationError(
                f"duplicate canonical logical path in {label}",
                context={"path": path},
            )
        out[path] = value
    return out


def verify_outputs(
    *,
    sources: Mapping[str, Path],
    specs: list[OutputFileSpec] | tuple[OutputFileSpec, ...],
    row_count_policy: RowCountPolicy = RowCountPolicy.REQUIRE_VERIFIER,
    row_counters: Mapping[str, Callable[[Path], int]] | None = None,
    row_receipts: Mapping[str, RowCountReceipt] | None = None,
    chunk_size: int = 1024 * 1024,
) -> tuple[OutputFileSpec, ...]:
    """Verify declared outputs against local files without full-file memory loads.

    Row counts: a declared count alone is not verified observation. Under
    ``REQUIRE_VERIFIER``, each output needs a counter or receipt. Under
    ``ALLOW_UNVERIFIED_DECLARED``, declared rows are accepted with
    ``rows_verified=False``.
    """
    spec_map: dict[str, OutputFileSpec] = {}
    for s in specs:
        path = canonical_relative_path(s.relative_path)
        if path in spec_map:
            raise OutputVerificationError(
                "duplicate logical output path in specs",
                context={"path": path},
            )
        spec_map[path] = OutputFileSpec(
            relative_path=path,
            sha256=s.sha256.lower(),
            rows=s.rows,
            bytes=s.bytes,
            partition=dict(s.partition),
            rows_verified=s.rows_verified,
        )

    # Four separate specializations of the TypeVar helper — never share a
    # heterogeneous dict[str, object] across different value types.
    # Empty defaults are explicitly annotated so mypy does not infer
    # dict[Never, Never] and contaminate the TypeVar specialization.
    empty_counters: dict[str, Callable[[Path], int]] = {}
    empty_receipts: dict[str, RowCountReceipt] = {}
    norm_sources: dict[str, Path] = _normalize_path_keyed_mapping(
        sources,
        label="sources",
    )
    norm_counters: dict[str, Callable[[Path], int]] = _normalize_path_keyed_mapping(
        row_counters if row_counters is not None else empty_counters,
        label="row counters",
    )
    norm_receipts: dict[str, RowCountReceipt] = _normalize_path_keyed_mapping(
        row_receipts if row_receipts is not None else empty_receipts,
        label="row receipts",
    )

    missing = set(spec_map) - set(norm_sources)
    unexpected = set(norm_sources) - set(spec_map)
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
        if len(spec.sha256) != 64:
            raise OutputVerificationError(
                "output sha256 must be 64 hex chars",
                context={"relative_path": rel},
            )
        if spec.rows < 0 or spec.bytes < 0:
            raise OutputVerificationError(
                "rows and bytes must be >= 0",
                context={"relative_path": rel},
            )
        src = norm_sources[rel]
        actual_hash, actual_size = stream_sha256_and_size(src, chunk_size=chunk_size)
        if actual_hash != spec.sha256:
            raise OutputVerificationError(
                "output SHA-256 mismatch",
                context={
                    "relative_path": rel,
                    "expected": spec.sha256,
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

        rows_verified = False
        observed_rows = spec.rows
        if rel in norm_receipts:
            rec = norm_receipts[rel]
            if rec.relative_path and canonical_relative_path(rec.relative_path) != rel:
                raise OutputVerificationError(
                    "row receipt path mismatch",
                    context={"relative_path": rel},
                )
            observed_rows = rec.row_count
            rows_verified = True
        elif rel in norm_counters:
            observed_rows = int(norm_counters[rel](src))
            rows_verified = True
        elif row_count_policy is RowCountPolicy.REQUIRE_VERIFIER:
            raise OutputVerificationError(
                "row count verifier or receipt required for output",
                context={
                    "relative_path": rel,
                    "policy": row_count_policy.value,
                },
            )
        # ALLOW_UNVERIFIED_DECLARED: keep declared rows, rows_verified=False

        if rows_verified and observed_rows != spec.rows:
            raise OutputVerificationError(
                "output row count mismatch",
                context={
                    "relative_path": rel,
                    "expected": spec.rows,
                    "observed": observed_rows,
                },
            )

        verified.append(
            OutputFileSpec(
                relative_path=rel,
                sha256=actual_hash,
                rows=spec.rows,
                bytes=actual_size,
                partition=dict(spec.partition),
                rows_verified=rows_verified,
            )
        )
    return tuple(verified)
