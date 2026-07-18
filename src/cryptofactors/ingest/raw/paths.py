"""Deterministic content-addressed path helpers and store path safety."""

from __future__ import annotations

import os
from pathlib import Path

from cryptofactors.ingest.raw.errors import PathSafetyError, RawStoreError


def validate_sha256_hex(sha256_hex: str) -> str:
    digest = sha256_hex.lower().strip()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise RawStoreError(
            "sha256 must be a 64-character lowercase hex digest",
            context={"sha256": sha256_hex},
        )
    return digest


def content_addressed_relative_path(sha256_hex: str, *, prefix: str = "raw/sha256") -> Path:
    """Return ``raw/sha256/ab/cd/<full_sha256>`` as a relative path."""
    digest = validate_sha256_hex(sha256_hex)
    return Path(prefix) / digest[:2] / digest[2:4] / digest


def content_addressed_absolute_path(
    root: Path, sha256_hex: str, *, prefix: str = "raw/sha256"
) -> Path:
    return (root / content_addressed_relative_path(sha256_hex, prefix=prefix)).resolve()


def raw_object_id_for_sha256(sha256_hex: str) -> str:
    digest = validate_sha256_hex(sha256_hex)
    return f"raw_{digest}"


def _reject_traversal(label: str, path: str | Path) -> None:
    # Inspect raw text segments: pathlib normalizes "." away from Path.parts,
    # so "tmp/./x" would otherwise bypass the check. Split on the OS separator.
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

    # Ensure resolved paths stay under root once root exists or is created.
    root_abs = root.expanduser()
    # Do not resolve if missing — still check pure path joining.
    try:
        root_resolved = root_abs.resolve()
    except OSError as exc:
        raise PathSafetyError(
            f"cannot resolve store root: {exc}",
            context={"root": str(root)},
        ) from exc

    temp_candidate = (root_resolved / temp_rel)
    obj_candidate = (root_resolved / prefix_rel)
    for label, candidate in (("temp", temp_candidate), ("objects", obj_candidate)):
        try:
            # relative_to raises if not under root
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


def assert_no_symlink_components(path: Path, *, must_exist: bool = False) -> None:
    """Reject if any path component is a symlink (absolute paths only)."""
    if not path.is_absolute():
        path = path.resolve()
    built = Path("/")
    for part in path.parts[1:]:
        built = built / part
        if built.is_symlink():
            raise PathSafetyError(
                "symlinked storage-directory component rejected",
                context={"path": str(built)},
            )
        if must_exist and not built.exists():
            raise PathSafetyError(
                "required path component missing",
                context={"path": str(built)},
            )


def assert_regular_nonsymlink_file(path: Path, *, label: str) -> None:
    if path.is_symlink():
        raise PathSafetyError(
            f"{label} must not be a symlink",
            context={"path": str(path)},
        )
    if not path.is_file():
        raise PathSafetyError(
            f"{label} must be a regular file",
            context={"path": str(path), "exists": path.exists()},
        )
    # Extra: reject non-regular via stat
    st = os.lstat(path)
    import stat as statmod

    if not statmod.S_ISREG(st.st_mode):
        raise PathSafetyError(
            f"{label} is not a regular file",
            context={"path": str(path)},
        )


def fsync_dir(path: Path) -> None:
    """fsync a directory entry (best-effort on platforms that support it)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
