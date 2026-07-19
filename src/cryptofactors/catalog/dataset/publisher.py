"""Immutable dataset publication with concurrent-safe reservation protocol (MAN-001).

Publication protocol (corrected per MAN-001 Senior review):

* Build each contender's complete dataset tree in a unique directory beneath
  ``config.temp_dir()`` on the same filesystem as the final store.
* Verify all staged outputs and canonical manifest bytes, then ``fsync`` staged
  files and directories.
* Coordinate identical concurrent publishers with a per-dataset no-clobber
  reservation (the canonical final path itself).
* While holding that reservation, either verify and reuse an already completed
  identical final dataset, or atomically ``rename`` the completed staged
  directory into the previously absent final path.
* Never overwrite or replace any pre-existing final path, including an empty
  directory.
* The canonical final path is absent until the complete tree is ready.
* Losers verify/reuse the winner and remove only their own stage.
* Owner failure leaves no partial final directory.
* Published output bytes are physically independent of caller-owned source
  files (exclusive streaming copy, or a reflink copy-on-write clone with an
  exclusive streaming-copy fallback).  Hard links are never used.
"""

from __future__ import annotations

import os
import errno
import shutil
import stat as statmod
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from cryptofactors.catalog.dataset.canonicalize import (
    canonical_relative_path,
    compute_dataset_id,
    compute_manifest_sha256,
    dumps_canonical,
    full_manifest_dict,
    identity_payload,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.errors import (
    CorruptDatasetError,
    DatasetPublicationError,
    DatasetPublicationInProgressError,
    RecoverableDatasetCatalogError,
    UnsafePathError,
)
from cryptofactors.catalog.dataset.lineage import validate_dependencies
from cryptofactors.catalog.dataset.models import (
    DatasetManifest,
    DatasetPublicationReceipt,
    DatasetPublishResult,
    DatasetStoreConfig,
    PublicationMetadata,
    PublishPlan,
)
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size, verify_outputs
from cryptofactors.catalog.dataset.parse import load_manifest_file
from cryptofactors.catalog.dataset.paths import (
    assert_no_symlink_components,
    assert_parents_are_directories,
    assert_relative_safe,
    dataset_absolute_dir,
    dataset_relative_dir,
    fsync_dir,
    fsync_file,
    fsync_parents,
    lstat_path,
)


# Deterministic bookkeeping timestamp when plan.created_at is omitted.
_DETERMINISTIC_CREATED_AT = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


class _ReservationLost(Exception):
    """Internal: exclusive rename lost to a concurrent publisher."""


def _copy_bytes_cow(out_fd: int, in_fd: int, *, chunk_size: int) -> None:
    """Copy bytes from in_fd to out_fd (integer file descriptors).

    The destination inode is physically independent of the source (a streaming
    copy), so later writes to the source cannot alter the destination.  On
    copy-on-write-capable filesystems a reflink clone is preferred when
    ``os.copy_file_range`` is available, since it also yields an independent
    inode.
    """
    if hasattr(os, "copy_file_range"):
        try:
            while True:
                n = os.copy_file_range(in_fd, out_fd, chunk_size)
                if n == 0:
                    break
            return
        except OSError:
            os.lseek(in_fd, 0, os.SEEK_SET)
            os.lseek(out_fd, 0, os.SEEK_SET)
    # Manual streaming copy over the raw descriptors (no extra wrappers).
    while True:
        chunk = os.read(in_fd, chunk_size)
        if not chunk:
            break
        os.write(out_fd, chunk)


def _copy_to_new_inode(
    src: Path, dest: Path, *, chunk_size: int = 1024 * 1024
) -> None:
    """Create dest exclusively (no overwrite) as an independent copy of src.

    Never shares an inode with ``src``.  Uses a reflink copy-on-write clone when
    the filesystem supports it, else a streaming copy.  Flushes and ``fsync``s
    the destination.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(dest), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise DatasetPublicationError(
            "output child already exists (no-clobber violation)",
            context={"path": str(dest)},
        ) from exc
    try:
        with os.fdopen(fd, "wb") as rout, src.open("rb") as rin:
            _copy_bytes_cow(rout.fileno(), rin.fileno(), chunk_size=chunk_size)
            rout.flush()
            os.fsync(rout.fileno())
    except Exception:
        # Remove our exclusive create if incomplete.
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _write_manifest_atomic(final_dir: Path, manifest_bytes: bytes) -> None:
    """Write canonical manifest last as the final acceptance marker (no overwrite)."""
    final_man = final_dir / "manifest.json"
    st = lstat_path(final_man)
    if st is not None:
        raise DatasetPublicationError(
            "manifest.json already exists during owner publication",
            context={"path": str(final_man)},
        )
    fd, tmp_name = tempfile.mkstemp(
        prefix=".manifest-",
        suffix=".partial",
        dir=str(final_dir),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(manifest_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        if lstat_path(final_man) is not None:
            raise DatasetPublicationError(
                "manifest.json already exists (no-clobber)",
                context={"path": str(final_man)},
            )
        # Same-directory rename is atomic and refuses if dest exists.
        os.rename(str(tmp_path), str(final_man))
        fsync_file(final_man)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


class DatasetPublisher:
    """Publish immutable datasets with concurrent-safe directory reservation."""

    def __init__(
        self,
        config: DatasetStoreConfig,
        catalog: SqliteDatasetCatalog,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> None:
        self._config = config
        self._catalog = catalog
        self._chunk_size = chunk_size
        root = self._config.root.expanduser()
        if not root.is_absolute():
            root = Path.cwd() / root
        root.mkdir(parents=True, exist_ok=True)
        st = lstat_path(root)
        if st is not None and statmod.S_ISLNK(st.st_mode):
            raise UnsafePathError("dataset store root must not be a symlink")
        temp = self._config.temp_dir()
        if not temp.is_absolute():
            temp = root / self._config.temp_dirname
        temp.mkdir(parents=True, exist_ok=True)
        assert_no_symlink_components(temp, stop_at=root)

    def publish(
        self,
        plan: PublishPlan,
        *,
        register_catalog: bool = True,
    ) -> DatasetPublishResult:
        root = self._config.root.expanduser()
        if not root.is_absolute():
            root = Path.cwd() / root

        validate_dependencies(
            list(plan.dependencies),
            raw_exists=self._catalog.raw_object_exists,
            dataset_exists=self._catalog.dataset_exists,
            dataset_upstreams=self._catalog.upstream_dataset_ids,
        )

        verified_files = verify_outputs(
            sources=dict(plan.output_sources),
            specs=list(plan.output_specs),
            row_count_policy=plan.row_count_policy,
            row_counters=dict(plan.row_counters),
            row_receipts=dict(plan.row_receipts),
            chunk_size=self._chunk_size,
        )

        total_rows = sum(f.rows for f in verified_files)
        total_bytes = sum(f.bytes for f in verified_files)
        if plan.statistics.row_count != total_rows:
            raise DatasetPublicationError(
                "statistics.row_count disagrees with sum of output rows",
                context={
                    "declared": plan.statistics.row_count,
                    "sum_files": total_rows,
                },
            )
        if plan.statistics.byte_size != total_bytes:
            raise DatasetPublicationError(
                "statistics.byte_size disagrees with sum of output bytes",
                context={
                    "declared": plan.statistics.byte_size,
                    "sum_files": total_bytes,
                },
            )

        identity = identity_payload(
            dataset_type=plan.dataset_type,
            schema=plan.schema,
            transform=plan.transform,
            code=plan.code,
            config=plan.config,
            dependencies=list(plan.dependencies),
            files=verified_files,
            statistics=plan.statistics,
            coverage=plan.coverage,
            quality_status=plan.quality_status,
            quality_summary=plan.quality_summary,
            supersedes_dataset_id=plan.supersedes_dataset_id,
        )
        dataset_id, _ = compute_dataset_id(identity)
        created_at = plan.created_at or _DETERMINISTIC_CREATED_AT

        for f in verified_files:
            assert_relative_safe(f.relative_path, label="output relative_path")

        provisional = DatasetManifest(
            dataset_id=dataset_id,
            dataset_type=plan.dataset_type,
            schema=plan.schema,
            transform=plan.transform,
            code=plan.code,
            config=plan.config,
            dependencies=tuple(plan.dependencies),
            files=verified_files,
            statistics=plan.statistics,
            coverage=plan.coverage,
            quality_status=plan.quality_status,
            quality_summary=dict(plan.quality_summary),
            publication=PublicationMetadata(created_at=created_at),
            supersedes_dataset_id=plan.supersedes_dataset_id,
            manifest_sha256="",
        )
        manifest_sha = compute_manifest_sha256(provisional)
        manifest = DatasetManifest(
            dataset_id=dataset_id,
            dataset_type=provisional.dataset_type,
            schema=provisional.schema,
            transform=provisional.transform,
            code=provisional.code,
            config=provisional.config,
            dependencies=provisional.dependencies,
            files=provisional.files,
            statistics=provisional.statistics,
            coverage=provisional.coverage,
            quality_status=provisional.quality_status,
            quality_summary=provisional.quality_summary,
            publication=provisional.publication,
            supersedes_dataset_id=provisional.supersedes_dataset_id,
            manifest_sha256=manifest_sha,
        )

        rel_dir = dataset_relative_dir(dataset_id, prefix=self._config.object_prefix)
        final_dir = dataset_absolute_dir(
            self._config.root, dataset_id, prefix=self._config.object_prefix
        )
        manifest_uri = (rel_dir / "manifest.json").as_posix()
        publication_uri = rel_dir.as_posix()

        # Canonicalize source keys so the publish path indexes outputs by the
        # same canonical logical path that verify_outputs canonicalized specs to.
        # verify_outputs already rejected canonical-key collisions in sources,
        # specs, row counters, and row receipts (typed OutputVerificationError),
        # so no KeyError can occur below.
        canon_sources: dict[str, Path] = {
            canonical_relative_path(k): v for k, v in plan.output_sources.items()
        }

        on_disk, reused = self._ensure_published(
            final_dir,
            sources=canon_sources,
            manifest=manifest,
            root=root,
        )
        manifest = on_disk

        receipt = DatasetPublicationReceipt(
            dataset_id=dataset_id,
            manifest_sha256=manifest.manifest_sha256,
            manifest_uri=manifest_uri,
            publication_uri=publication_uri,
            dataset_path=final_dir,
            verified_outputs=manifest.files,
            publication_verified=True,
            object_prefix=self._config.object_prefix,
            dependencies=manifest.dependencies,
            supersedes_dataset_id=manifest.supersedes_dataset_id,
            dataset_type=manifest.dataset_type,
            schema=manifest.schema,
            transform=manifest.transform,
            code=manifest.code,
            config=manifest.config,
            statistics=manifest.statistics,
            coverage=manifest.coverage,
            quality_status=manifest.quality_status,
            quality_summary=dict(manifest.quality_summary),
            catalog_created_at=manifest.publication.created_at,
        )

        catalog_registered = False
        if register_catalog:
            try:
                inserted = self._catalog.register_from_receipt(receipt, manifest=manifest)
                catalog_registered = True
                if not inserted:
                    reused = True
            except RecoverableDatasetCatalogError:
                raise
            except Exception as exc:
                raise RecoverableDatasetCatalogError(
                    f"catalog registration failed after publication: {exc}",
                    dataset_id=dataset_id,
                    manifest_sha256=manifest.manifest_sha256,
                    dataset_path=str(final_dir),
                    context={"error": str(exc)},
                ) from exc

        return DatasetPublishResult(
            dataset_id=dataset_id,
            manifest_sha256=manifest.manifest_sha256,
            dataset_path=final_dir,
            manifest_uri=manifest_uri,
            reused_existing=reused,
            catalog_registered=catalog_registered,
            manifest=manifest,
            receipt=receipt,
        )

    def _ensure_published(
        self,
        final_dir: Path,
        *,
        sources: dict[str, Path],
        manifest: DatasetManifest,
        root: Path,
    ) -> tuple[DatasetManifest, bool]:
        """Own reservation or wait for concurrent owner; return verified manifest."""
        deadline = time.monotonic() + self._config.publication_wait_seconds
        backoff = self._config.publication_initial_backoff_seconds
        max_backoff = self._config.publication_max_backoff_seconds

        while True:
            st = lstat_path(final_dir)
            if st is None:
                # Path free — try to become owner.
                try:
                    loaded = self._publish_as_owner(
                        final_dir, sources=sources, manifest=manifest, root=root
                    )
                    return loaded, False
                except _ReservationLost:
                    # Concurrent owner won the rename; loop and wait/reuse.
                    continue

            if statmod.S_ISLNK(st.st_mode):
                raise CorruptDatasetError(
                    "final dataset path is a symlink",
                    context={"path": str(final_dir)},
                )
            if not statmod.S_ISDIR(st.st_mode):
                raise CorruptDatasetError(
                    "final dataset path is not a directory",
                    context={"path": str(final_dir)},
                )

            man = final_dir / "manifest.json"
            st_m = lstat_path(man)
            if (
                st_m is not None
                and not statmod.S_ISLNK(st_m.st_mode)
                and statmod.S_ISREG(st_m.st_mode)
            ):
                # Accepted immutable dataset — verify and reuse.
                loaded = self._verify_existing_dataset_strict(final_dir, manifest)
                return loaded, True

            # Incomplete reservation (no acceptance marker yet), or a pre-existing
            # empty directory that must never be replaced.  Wait for completion.
            if time.monotonic() >= deadline:
                raise DatasetPublicationInProgressError(
                    "timed out waiting for concurrent publisher to finish",
                    context={
                        "path": str(final_dir),
                        "wait_seconds": self._config.publication_wait_seconds,
                    },
                )
            time.sleep(backoff)
            backoff = min(backoff * 2.0, max_backoff)
            # If the incomplete reservation disappeared, loop to retry ownership.
            continue

    def _publish_as_owner(
        self,
        final_dir: Path,
        *,
        sources: dict[str, Path],
        manifest: DatasetManifest,
        root: Path,
    ) -> DatasetManifest:
        """Build the complete tree in a temp stage, then atomically rename in.

        The canonical final path remains absent until the complete, fsync'd tree
        is ready.  A rename collision means a concurrent owner already published;
        we drop our stage and signal loss.  Owner failure before the rename
        leaves only our own (safe-to-clean) stage, never a partial final path.
        """
        stage = Path(
            tempfile.mkdtemp(dir=str(self._config.temp_dir()), prefix=".stage-")
        )
        # Final-tree parent prefixes must exist for the atomic rename.
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        assert_no_symlink_components(final_dir.parent, stop_at=root)
        assert_parents_are_directories(final_dir, stop_at=root)

        owned_incomplete = True
        try:
            # 1) Populate all declared outputs with no-clobber creation.
            for fspec in manifest.files:
                try:
                    src = sources[fspec.relative_path]
                except KeyError as exc:
                    raise DatasetPublicationError(
                        "missing staged source for declared output",
                        context={"path": fspec.relative_path},
                    ) from exc
                dest = stage / fspec.relative_path
                assert_relative_safe(fspec.relative_path, label="output path")
                _copy_to_new_inode(src, dest, chunk_size=self._chunk_size)
                h, sz = stream_sha256_and_size(dest, chunk_size=self._chunk_size)
                if h != fspec.sha256 or sz != fspec.bytes:
                    raise DatasetPublicationError(
                        "published output content mismatch",
                        context={"path": fspec.relative_path},
                    )
                fsync_file(dest)

            # 2) Manifest is the final acceptance marker (only after all outputs).
            man_bytes = (dumps_canonical(full_manifest_dict(manifest)) + "\n").encode(
                "utf-8"
            )
            _write_manifest_atomic(stage, man_bytes)
            fsync_dir(stage)
            fsync_dir(stage.parent)

            # 3) Atomically expose the complete tree.
            try:
                os.rename(str(stage), str(final_dir))
            except FileExistsError:
                # Concurrent owner won; remove only our own stage.
                shutil.rmtree(stage, ignore_errors=True)
                raise _ReservationLost() from None
            except OSError as exc:  # ENOTEMPTY / EEXIST on dir->dir rename race
                if getattr(exc, "errno", None) in (errno.EEXIST, errno.ENOTEMPTY):
                    shutil.rmtree(stage, ignore_errors=True)
                    raise _ReservationLost() from None
                # Any other rename failure during atomic exposure is a
                # publication failure (never a partial final directory).
                shutil.rmtree(stage, ignore_errors=True)
                raise DatasetPublicationError(
                    f"atomic final rename failed: {exc}", context={"path": str(final_dir)}
                ) from exc
            owned_incomplete = False
            fsync_parents(final_dir, stop_at=root)

            return self._verify_existing_dataset_strict(final_dir, manifest)
        except Exception:
            # Owner failure before acceptance: clean only our incomplete stage;
            # never touch another publisher's completed dataset.
            if owned_incomplete:
                shutil.rmtree(stage, ignore_errors=True)
            raise

    def _verify_existing_dataset_strict(
        self, dataset_dir: Path, expected: DatasetManifest
    ) -> DatasetManifest:
        """Exact tree and byte verification; return on-disk parsed manifest."""
        st = lstat_path(dataset_dir)
        if st is None:
            raise CorruptDatasetError(
                "dataset directory missing",
                context={"path": str(dataset_dir)},
            )
        if statmod.S_ISLNK(st.st_mode):
            raise CorruptDatasetError(
                "dataset directory is a symlink",
                context={"path": str(dataset_dir)},
            )
        if not statmod.S_ISDIR(st.st_mode):
            raise CorruptDatasetError(
                "dataset path is not a directory",
                context={"path": str(dataset_dir)},
            )

        man_path = dataset_dir / "manifest.json"
        assert_no_symlink_components(man_path, stop_at=dataset_dir.parent)
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
                f"cannot parse existing manifest: {exc}",
                context={"path": str(man_path)},
            ) from exc

        if loaded.dataset_id != expected.dataset_id:
            raise CorruptDatasetError(
                "existing dataset_id disagrees",
                context={
                    "expected": expected.dataset_id,
                    "observed": loaded.dataset_id,
                },
            )
        if loaded.manifest_sha256 != expected.manifest_sha256:
            raise CorruptDatasetError(
                "existing manifest_sha256 disagrees with plan identity",
                context={
                    "expected": expected.manifest_sha256,
                    "observed": loaded.manifest_sha256,
                },
            )
        loaded_bytes = (dumps_canonical(full_manifest_dict(loaded)) + "\n").encode(
            "utf-8"
        )
        if on_disk_bytes != loaded_bytes:
            raise CorruptDatasetError(
                "manifest.json is not exactly canonical",
                context={"path": str(man_path)},
            )

        declared = {"manifest.json"} | {f.relative_path for f in loaded.files}
        found: set[str] = set()
        for path in dataset_dir.rglob("*"):
            rel = path.relative_to(dataset_dir).as_posix()
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
            fpath = dataset_dir / fspec.relative_path
            h, sz = stream_sha256_and_size(fpath, chunk_size=self._chunk_size)
            if h != fspec.sha256 or sz != fspec.bytes:
                raise CorruptDatasetError(
                    "existing dataset file content mismatch",
                    context={"path": fspec.relative_path},
                )
        return loaded

    def retry_catalog_registration(
        self,
        *,
        dataset_id: str,
        receipt: DatasetPublicationReceipt,
        manifest: DatasetManifest,
    ) -> bool:
        final_dir = dataset_absolute_dir(
            self._config.root, dataset_id, prefix=self._config.object_prefix
        )
        loaded = self._verify_existing_dataset_strict(final_dir, manifest)
        return self._catalog.register_from_receipt(receipt, manifest=loaded)
