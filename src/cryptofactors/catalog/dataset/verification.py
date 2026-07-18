"""Read-only dataset verification API (MAN-001)."""

from __future__ import annotations


from cryptofactors.catalog.dataset.canonicalize import (
    dumps_canonical,
    full_manifest_dict,
    sha256_hex,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import (
    DatasetManifest,
    DatasetStoreConfig,
    DatasetVerificationReport,
    VerificationFinding,
    VerificationSeverity,
)
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir


def verify_dataset(
    *,
    config: DatasetStoreConfig,
    catalog: SqliteDatasetCatalog,
    dataset_id: str,
    expected_manifest: DatasetManifest | None = None,
) -> DatasetVerificationReport:
    """Verify filesystem publication against catalog and optional expected manifest."""
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
        add(
            "catalog_present",
            VerificationSeverity.SUCCESS,
            "dataset row present",
            dataset_id=dataset_id,
        )

    final_dir = dataset_absolute_dir(
        config.root, dataset_id, prefix=config.object_prefix
    )
    if not final_dir.exists():
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

    man_path = final_dir / "manifest.json"
    if not man_path.is_file() or man_path.is_symlink():
        add(
            "manifest_missing",
            VerificationSeverity.FAILURE,
            "manifest.json missing or unsafe",
            path=str(man_path),
        )
    else:
        on_disk = man_path.read_text(encoding="utf-8")
        disk_sha = sha256_hex(on_disk.strip().encode("utf-8"))
        # Prefer hashing canonical re-dump of expected when provided.
        if expected_manifest is not None:
            expected_text = dumps_canonical(full_manifest_dict(expected_manifest)) + "\n"
            if on_disk != expected_text and on_disk.strip() != expected_text.strip():
                add(
                    "manifest_mismatch",
                    VerificationSeverity.FAILURE,
                    "on-disk manifest disagrees with expected",
                )
            else:
                add(
                    "manifest_match",
                    VerificationSeverity.SUCCESS,
                    "on-disk manifest matches expected",
                )
            if expected_manifest.manifest_sha256 and catalog_sha:
                if expected_manifest.manifest_sha256 != catalog_sha:
                    add(
                        "catalog_manifest_disagreement",
                        VerificationSeverity.FAILURE,
                        "catalog manifest_sha256 disagrees with expected",
                        catalog=catalog_sha,
                        expected=expected_manifest.manifest_sha256,
                    )
            for fspec in expected_manifest.files:
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
                            "output verified",
                            path=fspec.relative_path,
                        )
                except Exception as exc:
                    add(
                        "output_error",
                        VerificationSeverity.FAILURE,
                        f"output verification error: {exc}",
                        path=fspec.relative_path,
                    )
        else:
            add(
                "manifest_present",
                VerificationSeverity.SUCCESS,
                "manifest.json present",
                approx_sha256=disk_sha,
            )
            if row is not None:
                files = catalog.list_files(dataset_id)
                for frow in files:
                    fpath = final_dir / str(frow["storage_uri"])
                    try:
                        h, sz = stream_sha256_and_size(fpath)
                        if h != frow["file_sha256"] or sz != int(frow["byte_size"]):
                            add(
                                "output_mismatch",
                                VerificationSeverity.FAILURE,
                                "catalog file disagrees with disk",
                                path=str(frow["storage_uri"]),
                            )
                        else:
                            add(
                                "output_ok",
                                VerificationSeverity.SUCCESS,
                                "catalog file matches disk",
                                path=str(frow["storage_uri"]),
                            )
                    except Exception as exc:
                        add(
                            "output_error",
                            VerificationSeverity.FAILURE,
                            str(exc),
                            path=str(frow["storage_uri"]),
                        )

        # Lineage presence
        if row is not None:
            raws = catalog.list_raw_inputs(dataset_id)
            ups = catalog.list_dataset_inputs(dataset_id)
            add(
                "lineage_edges",
                VerificationSeverity.SUCCESS,
                "lineage edges loaded",
                raw_inputs=len(raws),
                dataset_inputs=len(ups),
            )

    ok = not any(f.severity is VerificationSeverity.FAILURE for f in findings)
    manifest_sha = (
        expected_manifest.manifest_sha256 if expected_manifest is not None else None
    )
    return DatasetVerificationReport(
        dataset_id=dataset_id,
        ok=ok,
        findings=tuple(findings),
        manifest_sha256=manifest_sha,
        catalog_manifest_sha256=catalog_sha,
    )
