"""Immutable dataset publication with verified receipts (MAN-001)."""

from __future__ import annotations

import os
import shutil
import stat as statmod
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cryptofactors.catalog.dataset.canonicalize import (
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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Deterministic bookkeeping timestamp when plan.created_at is omitted.
_DETERMINISTIC_CREATED_AT = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _copy_file_streaming(src: Path, dest: Path, *, chunk_size: int = 1024 * 1024) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with src.open("rb") as rin, dest.open("wb") as rout:
        while True:
            chunk = rin.read(chunk_size)
            if not chunk:
                break
            rout.write(chunk)
        rout.flush()
        os.fsync(rout.fileno())


class DatasetPublisher:
    """Publish immutable datasets with verified outputs and catalog registration."""

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
        # Deterministic created_at when not supplied — catalog bookkeeping only.
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

        reused = False
        st_final = lstat_path(final_dir)
        if st_final is not None:
            if statmod.S_ISLNK(st_final.st_mode):
                raise CorruptDatasetError(
                    "final dataset path is a symlink",
                    context={"path": str(final_dir)},
                )
            # Existing entry — verify exact agreement; reuse canonical on-disk manifest.
            on_disk = self._verify_existing_dataset_strict(final_dir, manifest)
            manifest = on_disk
            reused = True
        else:
            self._publish_new_no_clobber(
                final_dir, dict(plan.output_sources), manifest, root
            )
            self._verify_existing_dataset_strict(final_dir, manifest)

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

    def _publish_new_no_clobber(
        self,
        final_dir: Path,
        sources: dict[str, Path],
        manifest: DatasetManifest,
        root: Path,
    ) -> None:
        """Create final dataset only if it does not exist (including empty dirs)."""
        temp_parent = self._config.temp_dir()
        if not temp_parent.is_absolute():
            temp_parent = root / self._config.temp_dirname
        temp_parent.mkdir(parents=True, exist_ok=True)
        assert_no_symlink_components(temp_parent, stop_at=root)

        stage = Path(tempfile.mkdtemp(prefix=".partial-ds-", dir=str(temp_parent)))
        try:
            for fspec in manifest.files:
                src = sources[fspec.relative_path]
                dest = stage / fspec.relative_path
                assert_relative_safe(fspec.relative_path, label="output path")
                _copy_file_streaming(src, dest, chunk_size=self._chunk_size)
                h, sz = stream_sha256_and_size(dest, chunk_size=self._chunk_size)
                if h != fspec.sha256 or sz != fspec.bytes:
                    raise DatasetPublicationError(
                        "staged output content mismatch",
                        context={"path": fspec.relative_path},
                    )
            man_path = stage / "manifest.json"
            text = dumps_canonical(full_manifest_dict(manifest)) + "\n"
            man_path.write_bytes(text.encode("utf-8"))
            fsync_file(man_path)
            fsync_dir(stage)

            final_dir.parent.mkdir(parents=True, exist_ok=True)
            assert_no_symlink_components(final_dir.parent, stop_at=root)
            assert_parents_are_directories(final_dir, stop_at=root)

            # Exclusive create of final directory — fails if any entry exists
            # (including empty directory).
            try:
                os.mkdir(str(final_dir))
            except FileExistsError:
                # Concurrent winner or pre-existing — verify when complete.
                man = final_dir / "manifest.json"
                if not man.is_file():
                    raise DatasetPublicationError(
                        "final dataset path exists but is incomplete (concurrent race)",
                        context={"path": str(final_dir)},
                    )
                self._verify_existing_dataset_strict(final_dir, manifest)
                return
            except OSError as exc:
                raise DatasetPublicationError(
                    f"cannot create final dataset directory: {exc}",
                    context={"path": str(final_dir)},
                ) from exc

            # Populate final from stage via hardlink when possible, else copy.
            try:
                for dirpath, _dirnames, filenames in os.walk(stage):
                    rel_dir = os.path.relpath(dirpath, stage)
                    target_dir = (
                        final_dir if rel_dir == "." else final_dir / rel_dir
                    )
                    if rel_dir != ".":
                        target_dir.mkdir(parents=True, exist_ok=True)
                    for name in filenames:
                        src_f = Path(dirpath) / name
                        dst_f = target_dir / name
                        try:
                            os.link(str(src_f), str(dst_f))
                        except OSError:
                            _copy_file_streaming(
                                src_f, dst_f, chunk_size=self._chunk_size
                            )
                        fsync_file(dst_f)
                fsync_dir(final_dir)
                fsync_parents(final_dir, stop_at=root)
            except Exception:
                # Incomplete final we created — remove only if incomplete (no valid
                # manifest or verification would fail). Never remove pre-existing.
                man = final_dir / "manifest.json"
                if not man.is_file():
                    shutil.rmtree(final_dir, ignore_errors=True)
                raise
        finally:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)

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
        expected_bytes = (dumps_canonical(full_manifest_dict(expected)) + "\n").encode(
            "utf-8"
        )
        # Prefer loading on-disk as authority for retry; identity must still match.
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
        # Exact bytes: must match canonical serialization of the loaded manifest
        # (no strip). This rejects trailing-whitespace tampering.
        loaded_bytes = (dumps_canonical(full_manifest_dict(loaded)) + "\n").encode(
            "utf-8"
        )
        if on_disk_bytes != loaded_bytes:
            raise CorruptDatasetError(
                "manifest.json is not exactly canonical",
                context={"path": str(man_path)},
            )

        # Exact membership: only manifest.json + declared outputs.
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
