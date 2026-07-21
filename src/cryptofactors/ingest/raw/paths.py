"""Deterministic content-addressed path helpers and store path safety."""

from __future__ import annotations

import os
import stat as statmod
from pathlib import Path

from cryptofactors.ingest.raw.errors import DurabilityError, PathSafetyError, RawStoreError


def validate_sha256_hex(sha256_hex: str) -> str:
    digest = sha256_hex.lower().strip()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise RawStoreError(
            "sha256 must be a 64-character lowercase hex digest",
            context={"sha256": sha256_hex},
        )
    return digest


def content_addressed_relative_path(sha256_hex: str, *, prefix: str = "raw/sha256") -> Path:
    """Return ``<prefix>/ab/cd/<full_sha256>`` as a relative path."""
    digest = validate_sha256_hex(sha256_hex)
    return Path(prefix) / digest[:2] / digest[2:4] / digest


def content_addressed_absolute_path(
    root: Path, sha256_hex: str, *, prefix: str = "raw/sha256"
) -> Path:
    return (root / content_addressed_relative_path(sha256_hex, prefix=prefix)).resolve()


def raw_object_id_for_sha256(sha256_hex: str) -> str:
    digest = validate_sha256_hex(sha256_hex)
    return f"raw_{digest}"


def canonical_identity(
    *,
    root: Path,
    object_prefix: str,
    sha256_hex: str,
) -> tuple[str, str, Path, str]:
    """Return ``(sha256, raw_object_id, absolute_path, storage_uri)`` for content H.

    Absolute path is fully resolved (follows symlinks). Writers and layout helpers
    that need a resolved destination keep using this function.
    """
    digest = validate_sha256_hex(sha256_hex)
    oid = raw_object_id_for_sha256(digest)
    rel = content_addressed_relative_path(digest, prefix=object_prefix)
    uri = rel.as_posix()
    abs_path = (Path(root).resolve() / rel).resolve()
    return digest, oid, abs_path, uri


def lexical_absolute_under_root(root: Path, relative: Path) -> Path:
    """Join ``root`` and ``relative`` without resolving the result.

    ``root`` is resolved once. ``relative`` must be relative and must not contain
    ``.`` or ``..`` components. The returned path is absolute and remains lexical
    (no symlink follow). Used by publication-receipt verification (RAW-002).
    """
    root_r = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute():
        raise PathSafetyError(
            "relative content path must not be absolute",
            context={"path": str(rel)},
        )
    _reject_traversal("content path", rel)
    return root_r.joinpath(*rel.parts)


def lexical_content_addressed_absolute_path(
    root: Path, sha256_hex: str, *, prefix: str = "raw/sha256"
) -> Path:
    """Content-addressed absolute path joined lexically under resolved root.

    Does **not** resolve or follow the final path (RAW-002). Distinct from
    :func:`content_addressed_absolute_path` / :func:`canonical_identity`, which
    fully resolve.
    """
    rel = content_addressed_relative_path(sha256_hex, prefix=prefix)
    return lexical_absolute_under_root(root, rel)


def assert_lexical_under_root(path: Path, root: Path, *, label: str) -> Path:
    """Prove ``path`` is lexically under resolved ``root`` without following symlinks.

    Traversal components (``.`` / ``..``) are rejected on the candidate **before**
    ``normpath`` so they cannot collapse into a false under-root match (RAW-002 /
    REVIEW-0073).
    """
    root_r = Path(root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        raise PathSafetyError(
            f"{label} must be absolute",
            context={"path": str(candidate)},
        )
    # Reject before normpath: normpath would erase ".." and hide noncanonical receipts.
    if any(part in (".", "..") for part in candidate.parts):
        raise PathSafetyError(
            f"{label} must not contain '.' or '..' components",
            context={"path": str(candidate)},
        )
    # Collapse redundant separators only; no traversal tokens remain.
    normalized = Path(os.path.normpath(candidate))
    try:
        normalized.relative_to(root_r)
    except ValueError as exc:
        raise PathSafetyError(
            f"{label} escapes configured root",
            context={"root": str(root_r), "path": str(normalized)},
        ) from exc
    return normalized


def assert_store_path_components_lstat(path: Path, *, root: Path) -> None:
    """``lstat`` every component of ``path`` at or below ``root``.

    Rejects missing components, symlinks, non-directory parents, and a non-regular
    final component. Does not follow symlinks (RAW-002).
    """
    root_r = Path(root).resolve()
    target = assert_lexical_under_root(path, root_r, label="publication path")
    try:
        rel = target.relative_to(root_r)
    except ValueError as exc:
        raise PathSafetyError(
            "publication path escapes configured root",
            context={"root": str(root_r), "path": str(target)},
        ) from exc

    current = root_r
    parts = rel.parts
    if not parts:
        raise PathSafetyError(
            "publication path must be a file under the store root",
            context={"path": str(target)},
        )
    for index, part in enumerate(parts):
        current = current / part
        try:
            st = os.lstat(current)
        except FileNotFoundError as exc:
            raise PathSafetyError(
                "path component missing",
                context={"path": str(current)},
            ) from exc
        except OSError as exc:
            raise PathSafetyError(
                f"cannot lstat path component: {exc}",
                context={"path": str(current), "error": str(exc)},
            ) from exc
        if statmod.S_ISLNK(st.st_mode):
            raise PathSafetyError(
                "symlinked storage path component rejected",
                context={"path": str(current)},
            )
        is_final = index == len(parts) - 1
        if is_final:
            if not statmod.S_ISREG(st.st_mode):
                raise PathSafetyError(
                    "publication path is not a regular file",
                    context={"path": str(current)},
                )
        elif not statmod.S_ISDIR(st.st_mode):
            raise PathSafetyError(
                "parent path component is not a directory",
                context={"path": str(current)},
            )


def _reject_traversal(label: str, path: str | Path) -> None:
    raw_segments = [seg for seg in str(path).split(os.sep) if seg != ""]
    if any(seg in (".", "..") for seg in raw_segments):
        raise PathSafetyError(
            f"{label} must not contain '.' or '..' components",
            context={label: str(path)},
        )


def validate_store_config(config: object) -> None:
    """Validate RawObjectStoreConfig path safety (called from __post_init__)."""
    root = Path(getattr(config, "root"))
    temp_dirname = str(getattr(config, "temp_dirname"))
    object_prefix = str(getattr(config, "object_prefix"))

    temp_rel = Path(temp_dirname)
    prefix_rel = Path(object_prefix)

    if temp_rel.is_absolute():
        raise PathSafetyError(
            "temp_dirname must be a relative path under root",
            context={"temp_dirname": temp_dirname},
        )
    if prefix_rel.is_absolute():
        raise PathSafetyError(
            "object_prefix must be a relative path under root",
            context={"object_prefix": object_prefix},
        )
    _reject_traversal("temp_dirname", temp_dirname)
    _reject_traversal("object_prefix", object_prefix)
    if not temp_dirname or temp_dirname.strip() == "":
        raise PathSafetyError("temp_dirname must be non-empty")
    if not object_prefix or object_prefix.strip() == "":
        raise PathSafetyError("object_prefix must be non-empty")

    root_abs = root.expanduser()
    try:
        root_resolved = root_abs.resolve()
    except OSError as exc:
        raise PathSafetyError(
            f"cannot resolve store root: {exc}",
            context={"root": str(root)},
        ) from exc

    if root_resolved.exists() and root_resolved.is_symlink():
        raise PathSafetyError(
            "store root must not be a symlink",
            context={"root": str(root_resolved)},
        )

    for label, candidate in (
        ("temp", root_resolved / temp_rel),
        ("objects", root_resolved / prefix_rel),
    ):
        try:
            candidate.resolve().relative_to(root_resolved)
        except ValueError as exc:
            raise PathSafetyError(
                f"{label} path escapes configured root",
                context={"root": str(root_resolved), "path": str(candidate)},
            ) from exc


def assert_path_under_root(path: Path, root: Path, *, label: str) -> Path:
    root_r = root.resolve()
    path_r = path.resolve()
    try:
        path_r.relative_to(root_r)
    except ValueError as exc:
        raise PathSafetyError(
            f"{label} escapes configured root",
            context={"root": str(root_r), "path": str(path_r)},
        ) from exc
    return path_r


def assert_no_symlink_components(path: Path, *, stop_at: Path | None = None) -> None:
    """Reject if any path component is a symlink.

    When ``stop_at`` is set, only components at or below ``stop_at`` are checked
    (so the system root is not required to be non-symlink).
    """
    path = path if path.is_absolute() else path.resolve()
    stop = stop_at.resolve() if stop_at is not None else None
    built = Path(path.anchor) if path.anchor else Path("/")
    # Rebuild from parts
    if path.is_absolute():
        built = Path("/")
        parts = path.parts[1:]
    else:
        built = Path()
        parts = path.parts

    for part in parts:
        built = built / part
        if stop is not None:
            try:
                built.resolve().relative_to(stop)
            except ValueError:
                # Above stop_at — skip check for system parents
                if not str(built.resolve()).startswith(str(stop)):
                    continue
        if built.is_symlink():
            raise PathSafetyError(
                "symlinked storage-directory component rejected",
                context={"path": str(built)},
            )


def assert_parents_are_directories(path: Path, *, stop_at: Path) -> None:
    """Ensure every parent of ``path`` down to ``stop_at`` is a real directory."""
    stop = stop_at.resolve()
    current = path.parent.resolve()
    while True:
        if current.is_symlink():
            raise PathSafetyError(
                "parent path component is a symlink",
                context={"path": str(current)},
            )
        if current.exists() and not current.is_dir():
            raise PathSafetyError(
                "parent path component is not a directory",
                context={"path": str(current)},
            )
        if current == stop or current.parent == current:
            break
        try:
            current.relative_to(stop)
        except ValueError:
            break
        current = current.parent


def assert_regular_nonsymlink_file(path: Path, *, label: str) -> None:
    if path.is_symlink():
        raise PathSafetyError(
            f"{label} must not be a symlink",
            context={"path": str(path)},
        )
    if not path.exists():
        raise PathSafetyError(
            f"{label} does not exist",
            context={"path": str(path)},
        )
    st = os.lstat(path)
    if not statmod.S_ISREG(st.st_mode):
        raise PathSafetyError(
            f"{label} is not a regular file",
            context={"path": str(path)},
        )


def fsync_dir(path: Path) -> None:
    """fsync a directory entry; raise DurabilityError on failure."""
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError as exc:
        raise DurabilityError(
            f"cannot open directory for fsync: {path}",
            context={"path": str(path), "error": str(exc)},
        ) from exc
    try:
        try:
            os.fsync(fd)
        except OSError as exc:
            raise DurabilityError(
                f"directory fsync failed: {path}",
                context={"path": str(path), "error": str(exc)},
            ) from exc
    finally:
        os.close(fd)


def fsync_file(path: Path) -> None:
    """fsync a file; raise DurabilityError on failure."""
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError as exc:
        raise DurabilityError(
            f"cannot open file for fsync: {path}",
            context={"path": str(path), "error": str(exc)},
        ) from exc
    try:
        try:
            os.fsync(fd)
        except OSError as exc:
            raise DurabilityError(
                f"file fsync failed: {path}",
                context={"path": str(path), "error": str(exc)},
            ) from exc
    finally:
        os.close(fd)
