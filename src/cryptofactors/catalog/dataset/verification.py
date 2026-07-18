"""Independent read-only dataset verification (MAN-001)."""

from __future__ import annotations

from typing import Any

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.errors import InvalidManifestError
from cryptofactors.catalog.dataset.models import (
    DatasetManifest,
    DatasetStoreConfig,
    DatasetVerificationReport,
    DependencyKind,
    VerificationFinding,
    VerificationSeverity,
)
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.catalog.dataset.parse import load_manifest_file
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir, lstat_path
import stat as statmod


def verify_dataset(
    *,
    config: DatasetStoreConfig,
    catalog: SqliteDatasetCatalog,
    dataset_id: str,
    expected_manifest: DatasetManifest | None = None,
    row_counters: dict[Any, Any] | None = None,
) -> DatasetVerificationReport:
    """Verify filesystem + catalog independently (expected_manifest optional)."""
    findings: list[VerificationFinding] = []

    def add(
        code: str,
        severity: VerificationSeverity,
        message: str,
        **ctx: object,
    ) -> None:
        findings.append(
            VerificationFinding(
                code=code,
                severity=severity,
                message=message,
                context=dict(ctx),
            )
        )

    row = catalog.get_dataset(dataset_id)
    catalog_sha = str(row["manifest_sha256"]) if row else None
    if row is None:
        add("catalog_missing", VerificationSeverity.FAILURE, "dataset not in catalog")
    else:
        add("catalog_present", VerificationSeverity.SUCCESS, "dataset row present")

    final_dir = dataset_absolute_dir(
        config.root, dataset_id, prefix=config.object_prefix
    )
    st = lstat_path(final_dir)
    if st is None:
        add(
            "location_missing",
            VerificationSeverity.FAILURE,
            "canonical dataset directory missing",
            path=str(final_dir),
        )
        return DatasetVerificationReport(
            dataset_id=dataset_id,
            ok=False,
            findings=tuple(findings),
            catalog_manifest_sha256=catalog_sha,
        )
    if statmod.S_ISLNK(st.st_mode):
        add(
            "location_symlink",
            VerificationSeverity.FAILURE,
            "canonical dataset directory is a symlink",
            path=str(final_dir),
        )

    man_path = final_dir / "manifest.json"
    loaded: DatasetManifest | None = None
    try:
        loaded = load_manifest_file(man_path)
        add(
            "manifest_parsed",
            VerificationSeverity.SUCCESS,
            "manifest.json parsed and identity verified",
            manifest_sha256=loaded.manifest_sha256,
            dataset_id=loaded.dataset_id,
        )
        if loaded.dataset_id != dataset_id:
            add(
                "dataset_id_mismatch",
                VerificationSeverity.FAILURE,
                "path dataset_id disagrees with manifest",
                path_id=dataset_id,
                manifest_id=loaded.dataset_id,
            )
    except InvalidManifestError as exc:
        add(
            "manifest_invalid",
            VerificationSeverity.FAILURE,
            f"manifest validation failed: {exc}",
        )
    except Exception as exc:
        add(
            "manifest_load_error",
            VerificationSeverity.FAILURE,
            f"cannot load manifest: {exc}",
        )

    if loaded is not None:
        # Exact tree membership
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
                add(
                    "unexpected_symlink",
                    VerificationSeverity.FAILURE,
                    "unexpected symlink in dataset tree",
                    path=rel,
                )
                continue
            if not statmod.S_ISREG(st_e.st_mode):
                add(
                    "unexpected_special",
                    VerificationSeverity.FAILURE,
                    "unexpected special entry",
                    path=rel,
                )
                continue
            found.add(rel)
            if rel not in declared:
                add(
                    "unexpected_file",
                    VerificationSeverity.FAILURE,
                    "unexpected regular file",
                    path=rel,
                )
        for missing in sorted(declared - found):
            add(
                "missing_file",
                VerificationSeverity.FAILURE,
                "declared file missing",
                path=missing,
            )

        for fspec in loaded.files:
            fpath = final_dir / fspec.relative_path
            try:
                h, sz = stream_sha256_and_size(fpath)
                if h != fspec.sha256 or sz != fspec.bytes:
                    add(
                        "output_mismatch",
                        VerificationSeverity.FAILURE,
                        "output hash/size mismatch",
                        path=fspec.relative_path,
                        expected_sha=fspec.sha256,
                        actual_sha=h,
                    )
                else:
                    add(
                        "output_ok",
                        VerificationSeverity.SUCCESS,
                        "output hash/size verified",
                        path=fspec.relative_path,
                    )
                if row_counters and fspec.relative_path in row_counters:
                    observed = int(row_counters[fspec.relative_path](fpath))
                    if observed != fspec.rows:
                        add(
                            "row_count_mismatch",
                            VerificationSeverity.FAILURE,
                            "observed row count mismatch",
                            path=fspec.relative_path,
                            expected=fspec.rows,
                            observed=observed,
                        )
            except Exception as exc:
                add(
                    "output_error",
                    VerificationSeverity.FAILURE,
                    str(exc),
                    path=fspec.relative_path,
                )

        # Catalog agreement
        if row is not None:
            if str(row["manifest_sha256"]) != loaded.manifest_sha256:
                add(
                    "catalog_manifest_disagreement",
                    VerificationSeverity.FAILURE,
                    "catalog manifest_sha256 disagrees with on-disk manifest",
                    catalog=str(row["manifest_sha256"]),
                    disk=loaded.manifest_sha256,
                )
            if str(row["dataset_type"]) != loaded.dataset_type:
                add(
                    "catalog_field_mismatch",
                    VerificationSeverity.FAILURE,
                    "catalog dataset_type mismatch",
                )
            if int(row["row_count"]) != loaded.statistics.row_count:
                add(
                    "catalog_field_mismatch",
                    VerificationSeverity.FAILURE,
                    "catalog row_count mismatch",
                )
            if int(row["byte_size"]) != loaded.statistics.byte_size:
                add(
                    "catalog_field_mismatch",
                    VerificationSeverity.FAILURE,
                    "catalog byte_size mismatch",
                )

            files = catalog.list_files(dataset_id)
            file_map = {str(f["storage_uri"]): f for f in files}
            for fspec in loaded.files:
                crow = file_map.get(fspec.relative_path)
                if crow is None:
                    add(
                        "catalog_output_missing",
                        VerificationSeverity.FAILURE,
                        "catalog missing output row",
                        path=fspec.relative_path,
                    )
                elif (
                    str(crow["file_sha256"]) != fspec.sha256
                    or int(crow["row_count"]) != fspec.rows
                    or int(crow["byte_size"]) != fspec.bytes
                ):
                    add(
                        "catalog_output_mismatch",
                        VerificationSeverity.FAILURE,
                        "catalog output row disagrees with manifest",
                        path=fspec.relative_path,
                    )
            for uri in file_map:
                if uri not in {f.relative_path for f in loaded.files}:
                    add(
                        "catalog_output_extra",
                        VerificationSeverity.FAILURE,
                        "catalog has extra output row",
                        path=uri,
                    )

            # Lineage exact agreement
            expected_raw = {
                (d.id, d.role)
                for d in loaded.dependencies
                if d.kind is DependencyKind.RAW_OBJECT
            }
            expected_ds = {
                (d.id, d.role)
                for d in loaded.dependencies
                if d.kind is DependencyKind.DATASET
            }
            got_raw = {
                (str(r["raw_object_id"]), str(r["role"]))
                for r in catalog.list_raw_inputs(dataset_id)
            }
            got_ds = {
                (str(r["input_dataset_id"]), str(r["role"]))
                for r in catalog.list_dataset_inputs(dataset_id)
            }
            if got_raw != expected_raw:
                add(
                    "lineage_raw_mismatch",
                    VerificationSeverity.FAILURE,
                    "raw-object lineage disagrees with manifest",
                    expected=sorted(expected_raw),
                    observed=sorted(got_raw),
                )
            else:
                add(
                    "lineage_raw_ok",
                    VerificationSeverity.SUCCESS,
                    "raw-object lineage agrees",
                )
            if got_ds != expected_ds:
                add(
                    "lineage_dataset_mismatch",
                    VerificationSeverity.FAILURE,
                    "upstream dataset lineage disagrees with manifest",
                    expected=sorted(expected_ds),
                    observed=sorted(got_ds),
                )
            else:
                add(
                    "lineage_dataset_ok",
                    VerificationSeverity.SUCCESS,
                    "upstream dataset lineage agrees",
                )

        if expected_manifest is not None:
            if expected_manifest.manifest_sha256 != loaded.manifest_sha256:
                add(
                    "expected_manifest_mismatch",
                    VerificationSeverity.FAILURE,
                    "optional expected manifest disagrees",
                )

    ok = not any(f.severity is VerificationSeverity.FAILURE for f in findings)
    return DatasetVerificationReport(
        dataset_id=dataset_id,
        ok=ok,
        findings=tuple(findings),
        manifest_sha256=loaded.manifest_sha256 if loaded else None,
        catalog_manifest_sha256=catalog_sha,
        recomputed_dataset_id=loaded.dataset_id if loaded else None,
    )
