"""Dataset store path safety and layout (MAN-001)."""

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
        segs = [s for s in str(rel).split(os.sep) if s]
        if any(s in (".", "..") for s in segs):
            raise UnsafePathError(
                f"{label} must not contain '.' or '..'",
                context={label: rel},
            )
        if not rel.strip():
            raise UnsafePathError(f"{label} must be non-empty")
    root_r = root.expanduser().resolve()
    for label, rel in (("temp", temp_dirname), ("datasets", object_prefix)):
        cand = (root_r / rel).resolve()
        try:
            cand.relative_to(root_r)
        except ValueError as exc:
            raise UnsafePathError(
                f"{label} escapes root",
                context={"root": str(root_r), "path": str(cand)},
            ) from exc


def assert_relative_safe(rel: str, *, label: str = "path") -> Path:
    p = Path(rel)
    if p.is_absolute() or rel.startswith("/") or rel.startswith("\\"):
        raise UnsafePathError(f"{label} must be relative", context={label: rel})
    parts = p.parts
    if any(part in (".", "..") for part in parts):
        raise UnsafePathError(
            f"{label} must not contain '.' or '..'",
            context={label: rel},
        )
    if not rel or rel.strip() == "":
        raise UnsafePathError(f"{label} must be non-empty")
    return p


def dataset_relative_dir(dataset_id: str, *, prefix: str = "datasets/sha256") -> Path:
    if not dataset_id.startswith("ds_") or len(dataset_id) != 3 + 64:
        raise UnsafePathError(
            "dataset_id must be ds_<64 hex>",
            context={"dataset_id": dataset_id},
        )
    hexpart = dataset_id[3:]
    return Path(prefix) / hexpart[:2] / hexpart[2:4] / dataset_id


def dataset_absolute_dir(root: Path, dataset_id: str, *, prefix: str = "datasets/sha256") -> Path:
    return (root / dataset_relative_dir(dataset_id, prefix=prefix)).resolve()


def assert_no_symlink_components(path: Path, *, stop_at: Path) -> None:
    path = path if path.is_absolute() else path.resolve()
    stop = stop_at.resolve()
    built = Path("/")
    for part in path.parts[1:]:
        built = built / part
        try:
            built.resolve().relative_to(stop)
        except ValueError:
            continue
        if built.is_symlink():
            raise UnsafePathError(
                "symlinked path component rejected",
                context={"path": str(built)},
            )


def assert_regular_file(path: Path, *, label: str) -> None:
    if path.is_symlink():
        raise UnsafePathError(f"{label} must not be a symlink", context={"path": str(path)})
    if not path.exists():
        raise UnsafePathError(f"{label} missing", context={"path": str(path)})
    st = os.lstat(path)
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
    stop = stop_at.resolve()
    current = path if path.is_dir() else path.parent
    current = current.resolve()
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
