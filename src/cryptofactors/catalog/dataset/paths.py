"""Dataset store path safety — lexical construction + lstat (MAN-001)."""

from __future__ import annotations

import os
import stat as statmod
from pathlib import Path

from cryptofactors.catalog.dataset.errors import (
    DatasetDurabilityError,
    UnsafePathError,
)


def validate_dataset_store_config(config: object) -> None:
    root = Path(getattr(config, "root"))
    temp_dirname = str(getattr(config, "temp_dirname"))
    object_prefix = str(getattr(config, "object_prefix"))
    for label, rel in (("temp_dirname", temp_dirname), ("object_prefix", object_prefix)):
        p = Path(rel)
        if p.is_absolute():
            raise UnsafePathError(f"{label} must be relative", context={label: rel})
        segs = [s for s in str(rel).replace("\\", "/").split("/") if s]
        if any(s in (".", "..") for s in segs):
            raise UnsafePathError(
                f"{label} must not contain '.' or '..'",
                context={label: rel},
            )
        if not rel.strip():
            raise UnsafePathError(f"{label} must be non-empty")
    # Lexical join under root; check escape without resolving away symlinks first.
    root_abs = root.expanduser()
    if not root_abs.is_absolute():
        root_abs = (Path.cwd() / root_abs)
    root_lex = root_abs
    for label, rel in (("temp", temp_dirname), ("datasets", object_prefix)):
        cand = lexical_join(root_lex, rel)
        if not is_lexical_under(cand, root_lex):
            raise UnsafePathError(
                f"{label} escapes root",
                context={"root": str(root_lex), "path": str(cand)},
            )


def lexical_join(root: Path, *parts: str) -> Path:
    """Join without resolving symlinks."""
    p = root
    for part in parts:
        for seg in str(part).replace("\\", "/").split("/"):
            if seg in ("", "."):
                continue
            if seg == "..":
                raise UnsafePathError("path traversal rejected", context={"seg": seg})
            p = p / seg
    return p


def is_lexical_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def assert_relative_safe(rel: str, *, label: str = "path") -> str:
    text = rel.replace("\\", "/").strip()
    if not text or text.startswith("/"):
        raise UnsafePathError(f"{label} must be relative", context={label: rel})
    parts = [p for p in text.split("/") if p != ""]
    if any(p in (".", "..") for p in parts):
        raise UnsafePathError(
            f"{label} must not contain '.' or '..'",
            context={label: rel},
        )
    return "/".join(parts)


def dataset_relative_dir(dataset_id: str, *, prefix: str = "datasets/sha256") -> Path:
    if not dataset_id.startswith("ds_") or len(dataset_id) != 3 + 64:
        raise UnsafePathError(
            "dataset_id must be ds_<64 hex>",
            context={"dataset_id": dataset_id},
        )
    hexpart = dataset_id[3:]
    return Path(prefix) / hexpart[:2] / hexpart[2:4] / dataset_id


def dataset_absolute_dir(root: Path, dataset_id: str, *, prefix: str = "datasets/sha256") -> Path:
    """Canonical absolute path constructed lexically (no symlink resolution)."""
    root_abs = root.expanduser()
    if not root_abs.is_absolute():
        root_abs = Path.cwd() / root_abs
    rel = dataset_relative_dir(dataset_id, prefix=prefix)
    return lexical_join(root_abs, rel.as_posix())


def lstat_path(path: Path) -> os.stat_result | None:
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise UnsafePathError(
            f"lstat failed: {path}",
            context={"path": str(path), "error": str(exc)},
        ) from exc


def assert_no_symlink_components(path: Path, *, stop_at: Path) -> None:
    """Reject symlink components from stop_at down to path using lstat."""
    stop = stop_at if stop_at.is_absolute() else Path.cwd() / stop_at
    target = path if path.is_absolute() else Path.cwd() / path
    # Walk from stop toward target
    try:
        rel = target.relative_to(stop)
    except ValueError as exc:
        raise UnsafePathError(
            "path not under stop_at",
            context={"path": str(target), "stop": str(stop)},
        ) from exc
    built = stop
    st_stop = lstat_path(built)
    if st_stop is not None and statmod.S_ISLNK(st_stop.st_mode):
        raise UnsafePathError(
            "stop_at must not be a symlink",
            context={"path": str(built)},
        )
    for part in rel.parts:
        built = built / part
        st = lstat_path(built)
        if st is None:
            continue  # not created yet
        if statmod.S_ISLNK(st.st_mode):
            raise UnsafePathError(
                "symlinked path component rejected",
                context={"path": str(built)},
            )


def assert_parents_are_directories(path: Path, *, stop_at: Path) -> None:
    stop = stop_at if stop_at.is_absolute() else Path.cwd() / stop_at
    current = path.parent
    while True:
        st = lstat_path(current)
        if st is not None:
            if statmod.S_ISLNK(st.st_mode):
                raise UnsafePathError(
                    "parent is a symlink",
                    context={"path": str(current)},
                )
            if not statmod.S_ISDIR(st.st_mode):
                raise UnsafePathError(
                    "parent is not a directory",
                    context={"path": str(current)},
                )
        if current == stop or current.parent == current:
            break
        try:
            current.relative_to(stop)
        except ValueError:
            break
        current = current.parent


def assert_regular_file(path: Path, *, label: str) -> None:
    st = lstat_path(path)
    if st is None:
        raise UnsafePathError(f"{label} missing", context={"path": str(path)})
    if statmod.S_ISLNK(st.st_mode):
        raise UnsafePathError(f"{label} must not be a symlink", context={"path": str(path)})
    if not statmod.S_ISREG(st.st_mode):
        raise UnsafePathError(f"{label} is not a regular file", context={"path": str(path)})


def fsync_file(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError as exc:
        raise DatasetDurabilityError(
            f"cannot open file for fsync: {path}",
            context={"path": str(path), "error": str(exc)},
        ) from exc
    try:
        try:
            os.fsync(fd)
        except OSError as exc:
            raise DatasetDurabilityError(
                f"file fsync failed: {path}",
                context={"path": str(path), "error": str(exc)},
            ) from exc
    finally:
        os.close(fd)


def fsync_dir(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError as exc:
        raise DatasetDurabilityError(
            f"cannot open directory for fsync: {path}",
            context={"path": str(path), "error": str(exc)},
        ) from exc
    try:
        try:
            os.fsync(fd)
        except OSError as exc:
            raise DatasetDurabilityError(
                f"directory fsync failed: {path}",
                context={"path": str(path), "error": str(exc)},
            ) from exc
    finally:
        os.close(fd)


def fsync_parents(path: Path, *, stop_at: Path) -> None:
    stop = stop_at if stop_at.is_absolute() else Path.cwd() / stop_at
    current = path if path.is_dir() else path.parent
    seen: set[Path] = set()
    while True:
        if current in seen:
            break
        seen.add(current)
        fsync_dir(current)
        if current == stop or current.parent == current:
            break
        try:
            current.relative_to(stop)
        except ValueError:
            break
        current = current.parent
