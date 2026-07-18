"""Immutable dataset publication (MAN-001)."""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

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
    DatasetPublishResult,
    DatasetStoreConfig,
    OutputFileSpec,
    PublicationMetadata,
    PublishPlan,
)
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size, verify_outputs
from cryptofactors.catalog.dataset.paths import (
    assert_no_symlink_components,
    assert_relative_safe,
    dataset_absolute_dir,
    dataset_relative_dir,
    fsync_dir,
    fsync_file,
    fsync_parents,
)

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


def _tree_manifest_hash(dataset_dir: Path) -> dict[str, str]:
    """Map relative path → sha256 for all regular files under dataset_dir."""
    out: dict[str, str] = {}
    for path in sorted(dataset_dir.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(dataset_dir).as_posix()
        h, _ = stream_sha256_and_size(path)
        out[rel] = h
    return out


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
        self._config.root.mkdir(parents=True, exist_ok=True)
        self._config.temp_dir().mkdir(parents=True, exist_ok=True)
        root = self._config.root.resolve()
        if root.is_symlink():
            raise UnsafePathError("dataset store root must not be a symlink")
        assert_no_symlink_components(self._config.temp_dir(), stop_at=root)

    def publish(
        self,
        plan: PublishPlan,
        *,
        register_catalog: bool = True,
    ) -> DatasetPublishResult:
        """Verify inputs/outputs, publish immutable tree, register catalog."""
        # 1. Verify accepted inputs + lineage
        validate_dependencies(
            list(plan.dependencies),
            raw_exists=self._catalog.raw_object_exists,
            dataset_exists=self._catalog.dataset_exists,
            dataset_upstreams=self._catalog.upstream_dataset_ids,
        )

        # 2. Verify outputs (streaming)
        root = self._config.root.resolve()
        verified_files = verify_outputs(
            sources=dict(plan.output_sources),
            specs=list(plan.output_specs),
            root_for_symlink_stop=root,
            chunk_size=self._chunk_size,
        )

        # Statistics must agree with declared outputs.
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

        # 3. Construct identity + manifest
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
        created_at = plan.created_at or _utc_now()

        # Assign stable relative uris (locators) under the dataset directory.
        files_with_uri = tuple(
            OutputFileSpec(
                relative_path=f.relative_path,
                sha256=f.sha256,
                rows=f.rows,
                bytes=f.bytes,
                partition=dict(f.partition),
            )
            for f in verified_files
        )
        for f in files_with_uri:
            assert_relative_safe(f.relative_path, label="output relative_path")

        provisional = DatasetManifest(
            dataset_id=dataset_id,
            dataset_type=plan.dataset_type,
            schema=plan.schema,
            transform=plan.transform,
            code=plan.code,
            config=plan.config,
            dependencies=tuple(plan.dependencies),
            files=files_with_uri,
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

        # 4. Publish immutable dataset (stage then atomic rename)
        reused = False
        if final_dir.exists():
            self._verify_existing_dataset(final_dir, manifest)
            reused = True
        else:
            self._publish_new(final_dir, plan.output_sources, manifest)

        # 5. Verify final publication
        self._verify_existing_dataset(final_dir, manifest)

        # 6. Catalog registration
        catalog_registered = False
        if register_catalog:
            try:
                inserted = self._catalog.register_dataset(
                    manifest=manifest,
                    manifest_uri=manifest_uri,
                    publication_uri=publication_uri,
                )
                catalog_registered = True
                if not inserted:
                    reused = True
            except RecoverableDatasetCatalogError:
                raise
            except Exception as exc:
                raise RecoverableDatasetCatalogError(
                    f"catalog registration failed after publication: {exc}",
                    dataset_id=dataset_id,
                    manifest_sha256=manifest_sha,
                    dataset_path=str(final_dir),
                    context={"error": str(exc)},
                ) from exc

        return DatasetPublishResult(
            dataset_id=dataset_id,
            manifest_sha256=manifest_sha,
            dataset_path=final_dir,
            manifest_uri=manifest_uri,
            reused_existing=reused,
            catalog_registered=catalog_registered,
            manifest=manifest,
        )

    def _publish_new(
        self,
        final_dir: Path,
        sources: Mapping[str, Path],
        manifest: DatasetManifest,
    ) -> None:
        root = self._config.root.resolve()
        temp_parent = self._config.temp_dir()
        temp_parent.mkdir(parents=True, exist_ok=True)
        stage = Path(
            tempfile.mkdtemp(prefix=".partial-ds-", dir=str(temp_parent))
        )
        try:
            assert_no_symlink_components(stage, stop_at=root)
            # Copy outputs
            for fspec in manifest.files:
                src = sources[fspec.relative_path]
                dest = stage / fspec.relative_path
                assert_relative_safe(fspec.relative_path, label="output path")
                _copy_file_streaming(src, dest, chunk_size=self._chunk_size)
                # Re-hash staged copy
                h, sz = stream_sha256_and_size(dest, chunk_size=self._chunk_size)
                if h != fspec.sha256 or sz != fspec.bytes:
                    raise DatasetPublicationError(
                        "staged output content mismatch",
                        context={
                            "path": fspec.relative_path,
                            "expected_sha": fspec.sha256,
                            "actual_sha": h,
                        },
                    )
            # Write manifest
            man_path = stage / "manifest.json"
            text = dumps_canonical(full_manifest_dict(manifest)) + "\n"
            man_path.write_text(text, encoding="utf-8")
            fsync_file(man_path)
            fsync_dir(stage)

            final_dir.parent.mkdir(parents=True, exist_ok=True)
            assert_no_symlink_components(final_dir.parent, stop_at=root)

            # Atomic no-clobber directory publish via rename.
            published = False
            try:
                os.rename(str(stage), str(final_dir))
                published = True
            except OSError as exc:
                if final_dir.exists():
                    # Concurrent winner — verify identity; drop our stage.
                    self._verify_existing_dataset(final_dir, manifest)
                    published = True  # destination is the accepted tree
                else:
                    raise DatasetPublicationError(
                        f"atomic dataset rename failed: {exc}",
                        context={"final": str(final_dir), "error": str(exc)},
                    ) from exc

            if published and final_dir.exists():
                fsync_parents(final_dir, stop_at=root)
        finally:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)

    def _verify_existing_dataset(self, dataset_dir: Path, manifest: DatasetManifest) -> None:
        if dataset_dir.is_symlink():
            raise CorruptDatasetError(
                "dataset directory must not be a symlink",
                context={"path": str(dataset_dir)},
            )
        if not dataset_dir.is_dir():
            raise CorruptDatasetError(
                "dataset path is not a directory",
                context={"path": str(dataset_dir)},
            )
        man_path = dataset_dir / "manifest.json"
        if not man_path.is_file() or man_path.is_symlink():
            raise CorruptDatasetError(
                "manifest.json missing or unsafe",
                context={"path": str(man_path)},
            )
        on_disk = man_path.read_text(encoding="utf-8")
        expected = dumps_canonical(full_manifest_dict(manifest)) + "\n"
        if on_disk != expected:
            # Allow equivalent parse if only trailing whitespace differs after strip
            if on_disk.strip() != expected.strip():
                raise CorruptDatasetError(
                    "existing manifest.json disagrees with expected canonical bytes",
                    context={"path": str(man_path)},
                )
        for fspec in manifest.files:
            fpath = dataset_dir / fspec.relative_path
            if fpath.is_symlink():
                raise CorruptDatasetError(
                    "dataset file must not be a symlink",
                    context={"path": str(fpath)},
                )
            h, sz = stream_sha256_and_size(fpath, chunk_size=self._chunk_size)
            if h != fspec.sha256 or sz != fspec.bytes:
                raise CorruptDatasetError(
                    "existing dataset file content mismatch",
                    context={
                        "path": fspec.relative_path,
                        "expected_sha": fspec.sha256,
                        "actual_sha": h,
                    },
                )

    def retry_catalog_registration(
        self,
        *,
        dataset_id: str,
        manifest: DatasetManifest,
    ) -> bool:
        """Idempotent catalog registration after recoverable failure."""
        final_dir = dataset_absolute_dir(
            self._config.root, dataset_id, prefix=self._config.object_prefix
        )
        self._verify_existing_dataset(final_dir, manifest)
        rel_dir = dataset_relative_dir(dataset_id, prefix=self._config.object_prefix)
        return self._catalog.register_dataset(
            manifest=manifest,
            manifest_uri=(rel_dir / "manifest.json").as_posix(),
            publication_uri=rel_dir.as_posix(),
        )
