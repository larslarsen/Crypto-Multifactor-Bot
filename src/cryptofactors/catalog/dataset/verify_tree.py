"""Read-only verification of a published dataset tree (MAN-001).

Shared by ``SqliteDatasetCatalog.register_from_receipt`` and the independent
``verify_dataset`` path so the same exact tree-and-manifest checks are applied
in both places.  This module must not import from ``publisher`` (circular
import); it only depends on the parse/canonicalize/outputs/paths/errors layers.
"""

from __future__ import annotations

import stat as statmod
from pathlib import Path

from cryptofactors.catalog.dataset.canonicalize import (
    dumps_canonical,
    full_manifest_dict,
)
from cryptofactors.catalog.dataset.errors import CorruptDatasetError
from cryptofactors.catalog.dataset.models import DatasetManifest, DatasetPublicationReceipt
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.catalog.dataset.parse import load_manifest_file
from cryptofactors.catalog.dataset.paths import (
    assert_no_symlink_components,
    fsync_dir,
    lstat_path,
)


def verify_published_tree(
    receipt: DatasetPublicationReceipt,
    manifest: DatasetManifest,
    *,
    chunk_size: int = 1024 * 1024,
) -> DatasetManifest:
    """Independently load and verify the on-disk immutable tree.

    Returns the freshly parsed on-disk manifest.  Raises ``CorruptDatasetError``
    (or ``InvalidManifestError``) before any caller transaction if the tree is
    missing, incomplete, corrupt, or inconsistent with the supplied receipt and
    manifest.  Read-only: performs no catalog writes.
    """
    final_dir = Path(receipt.dataset_path)
    st = lstat_path(final_dir)
    if st is None:
        raise CorruptDatasetError(
            "published dataset tree missing",
            context={"path": str(final_dir), "dataset_id": receipt.dataset_id},
        )
    if statmod.S_ISLNK(st.st_mode):
        raise CorruptDatasetError(
            "published dataset path is a symlink",
            context={"path": str(final_dir)},
        )
    if not statmod.S_ISDIR(st.st_mode):
        raise CorruptDatasetError(
            "published dataset path is not a directory",
            context={"path": str(final_dir)},
        )

    man_path = final_dir / "manifest.json"
    assert_no_symlink_components(man_path, stop_at=final_dir.parent)
    st_m = lstat_path(man_path)
    if st_m is None or statmod.S_ISLNK(st_m.st_mode) or not statmod.S_ISREG(st_m.st_mode):
        raise CorruptDatasetError(
            "manifest.json missing or unsafe",
            context={"path": str(man_path)},
        )

    on_disk_bytes = man_path.read_bytes()
    try:
        loaded = load_manifest_file(man_path)
    except Exception as exc:
        raise CorruptDatasetError(
            f"cannot parse published manifest: {exc}",
            context={"path": str(man_path)},
        ) from exc

    # Independent recomputation: the on-disk file must be exactly canonical and
    # its embedded hashes must match the bytes.
    if loaded.dataset_id != receipt.dataset_id:
        raise CorruptDatasetError(
            "published tree dataset_id disagrees with receipt",
            context={"expected": receipt.dataset_id, "observed": loaded.dataset_id},
        )
    if loaded.manifest_sha256 != receipt.manifest_sha256:
        raise CorruptDatasetError(
            "published tree manifest_sha256 disagrees with receipt",
            context={
                "expected": receipt.manifest_sha256,
                "observed": loaded.manifest_sha256,
            },
        )
    canon_bytes = (dumps_canonical(full_manifest_dict(loaded)) + "\n").encode("utf-8")
    if on_disk_bytes != canon_bytes:
        raise CorruptDatasetError(
            "published manifest.json is not exactly canonical",
            context={"path": str(man_path)},
        )

    # Tree membership + output hashes/sizes.
    declared = {"manifest.json"} | {f.relative_path for f in loaded.files}
    found: set[str] = set()
    for path in final_dir.rglob("*"):
        rel = path.relative_to(final_dir).as_posix()
        st_e = lstat_path(path)
        if st_e is None:
            continue
        if statmod.S_ISDIR(st_e.st_mode) and not statmod.S_ISLNK(st_e.st_mode):
            continue
        if statmod.S_ISLNK(st_e.st_mode):
            raise CorruptDatasetError(
                "unexpected symlink in dataset tree",
                context={"path": rel},
            )
        if not statmod.S_ISREG(st_e.st_mode):
            raise CorruptDatasetError(
                "unexpected special entry in dataset tree",
                context={"path": rel},
            )
        found.add(rel)
        if rel not in declared:
            raise CorruptDatasetError(
                "unexpected regular file in dataset tree",
                context={"path": rel},
            )
    missing = declared - found
    if missing:
        raise CorruptDatasetError(
            "missing declared dataset files",
            context={"missing": sorted(missing)},
        )

    for fspec in loaded.files:
        fpath = final_dir / fspec.relative_path
        h, sz = stream_sha256_and_size(fpath, chunk_size=chunk_size)
        if h != fspec.sha256 or sz != fspec.bytes:
            raise CorruptDatasetError(
                "published dataset file content mismatch",
                context={"path": fspec.relative_path},
            )

    # Compare the independently loaded manifest with the supplied manifest.
    if loaded.manifest_sha256 != manifest.manifest_sha256:
        raise CorruptDatasetError(
            "supplied manifest disagrees with published tree",
            context={
                "supplied": manifest.manifest_sha256,
                "on_disk": loaded.manifest_sha256,
            },
        )
    if loaded.dataset_id != manifest.dataset_id:
        raise CorruptDatasetError(
            "supplied manifest dataset_id disagrees with published tree",
            context={"supplied": manifest.dataset_id, "on_disk": loaded.dataset_id},
        )
    fsync_dir(final_dir)
    return loaded
