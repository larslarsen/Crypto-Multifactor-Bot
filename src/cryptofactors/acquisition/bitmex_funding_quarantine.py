"""CEX-002 Gate 0: authenticate and atomically reject exactly five false authorities.

Catalog quality alone changes. Every invocation, including replay, proves the
immutable manifests, Parquet bytes, economics and complete catalog identities.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import stat
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.errors import (
    DatasetError,
    DatasetQuarantineError,
    QuarantineReportError,
)
from cryptofactors.catalog.dataset.models import QualityStatus
from cryptofactors.catalog.dataset.parse import load_manifest_bytes
from cryptofactors.catalog.dataset.paths import (
    assert_no_symlink_components,
    assert_regular_file,
    assert_relative_safe,
    dataset_absolute_dir,
    dataset_relative_dir,
)

TICKET_ID = "CEX-002"
QUARANTINE_MARKER = "cex002_bitmex_false_authority"
QUARANTINE_REASON = "all-zero funding_rate and empty funding_interval; false PASS authority"


@dataclass(frozen=True, slots=True)
class BitmexFalseAuthorityTarget:
    dataset_id: str
    dataset_type: str
    expected_rows: int
    expected_symbols: int
    relative_path: str
    file_sha256: str
    expected_byte_size: int
    manifest_sha256: str
    manifest_file_sha256: str
    catalog_created_at: str


# Research 54 Parquet identities and Review 485's two distinct manifest hashes.
BITMEX_FALSE_AUTHORITY_TARGETS: tuple[BitmexFalseAuthorityTarget, ...] = (
    BitmexFalseAuthorityTarget(
        dataset_id="ds_4f82fede83f446e3ca29522e6e5f5a0ad7fb6d03d8931f1300addfe413364933",
        dataset_type="bitmex_funding",
        expected_rows=14_376,
        expected_symbols=2,
        relative_path="bitmex/funding/funding.parquet",
        file_sha256="0213d0b070b02c3a4db02f7028a21938b48237a806731ed4ba03166833b055e2",
        expected_byte_size=205_097,
        manifest_sha256="7d43319236fc73f87bcbbcac19c2ec5028a70e5faed252ae9397ec83d1ca39f4",
        manifest_file_sha256="c26ec01f0fccae79da1b130d75803070bc1efe585b0a4bfe1e73be96aa1f24cc",
        catalog_created_at="1970-01-01T00:00:00+00:00",
    ),
    BitmexFalseAuthorityTarget(
        dataset_id="ds_f61c69342932c78c370b7950faf46d3e78be3695dbde8e6077acf8ccfa115deb",
        dataset_type="bitmex_funding",
        expected_rows=32_768,
        expected_symbols=5,
        relative_path="bitmex/funding/funding.parquet",
        file_sha256="8246d1eb5c77f242bc01178c29aa2fa4e9b2a62ea6d4f15192b82735e42a9c3f",
        expected_byte_size=295_554,
        manifest_sha256="6083d41c906f6bf4278b48a0cc6cd376a0c3c3bdc334fa94f42385eec8083ebb",
        manifest_file_sha256="9020c0faa95199d31d71c523f0fd86451088ce83dcb13a200cd86e74df6c1d1a",
        catalog_created_at="1970-01-01T00:00:00+00:00",
    ),
    BitmexFalseAuthorityTarget(
        dataset_id="ds_11b6665e7dcd37cb85c0098f60681a252801bbc4f80cb053eccc0fa0ce3679ea",
        dataset_type="bitmex_funding",
        expected_rows=32_768,
        expected_symbols=5,
        relative_path="bitmex/funding/funding.parquet",
        file_sha256="8246d1eb5c77f242bc01178c29aa2fa4e9b2a62ea6d4f15192b82735e42a9c3f",
        expected_byte_size=295_554,
        manifest_sha256="0e340f3e18f48bd93ccb3d8b00e17fe7883c677350a95c7dec677a08c1f274e6",
        manifest_file_sha256="0bd3c6d4bfc52642a05764b0b2b32b932bfe9b5e46379f5d9e4f0fdbdc32bc91",
        catalog_created_at="2026-07-24T01:32:06.704813+00:00",
    ),
    BitmexFalseAuthorityTarget(
        dataset_id="ds_ab70ebd21268fe47cbde63b266c0b6f41d0e2ca529d319e3f6f0aa5a5646f512",
        dataset_type="bitmex_funding",
        expected_rows=38_256,
        expected_symbols=5,
        relative_path="bitmex/funding/funding.parquet",
        file_sha256="658ef0f1b5409aaf075ce40f385195712967bb0d369dfdf6a02785525436771e",
        expected_byte_size=409_230,
        manifest_sha256="e7b64fc0312f6e2dea118bb3699734e85ce590ab519390cf5d1867edea7947e1",
        manifest_file_sha256="d434c8219ae382bb9f35164ebe3a05c76db845e5d0777a1ac8d1d02e7bf4fd92",
        catalog_created_at="2026-07-24T01:51:15.156657+00:00",
    ),
    BitmexFalseAuthorityTarget(
        dataset_id="ds_ee8e9cd9ddd4de87a0c68ef0ff9b4a0da6c6bd7692c96b9f29f8cca13daf46c8",
        dataset_type="bitmex_funding_full",
        expected_rows=189_570,
        expected_symbols=45,
        relative_path="bitmex/funding_full/funding.parquet",
        file_sha256="2ef8257c9724ca1949344175276c11b8f7764fd37eedfa866d5a47cf012fd215",
        expected_byte_size=1_187_191,
        manifest_sha256="a6427c8277f951a120984a654254e91d6e704b129aedf2bda8ee080a6cb4a39e",
        manifest_file_sha256="389a192f0d0c64d8403801946506c8f5841c37985cd9bef2c2e9e99b5f558bda",
        catalog_created_at="2026-07-24T04:00:41.830213+00:00",
    ),
)


@dataclass(frozen=True, slots=True)
class ParquetInspection:
    path: str
    sha256: str
    byte_size: int
    row_count: int
    symbol_count: int
    nonzero_rate_count: int
    null_rate_count: int
    empty_interval_count: int


@dataclass(frozen=True, slots=True)
class TargetInspection:
    dataset_id: str
    catalog_row: dict[str, Any]
    catalog_files: tuple[dict[str, Any], ...]
    manifest_sha256: str
    manifest_file_sha256: str
    manifest_quality_status: str
    manifest_created_at: str
    parquet: ParquetInspection
    artifacts: tuple[dict[str, Any], ...]
    already_quarantined: bool


@dataclass(frozen=True, slots=True)
class ResolverSnapshot:
    latest: dict[str, str | None]
    eligible_targets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QuarantineReport:
    ticket: str
    reason: str
    dry_run: bool
    applied: bool
    idempotent_replay: bool
    disposition: str
    generated_at: str
    targets: tuple[BitmexFalseAuthorityTarget, ...]
    pre_resolver: ResolverSnapshot
    post_resolver: ResolverSnapshot
    inspections_pre: tuple[TargetInspection, ...]
    inspections_post: tuple[TargetInspection, ...]
    artifacts_unchanged: bool
    database_path: str
    store_root: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def exact_false_authority_ids() -> tuple[str, ...]:
    return tuple(t.dataset_id for t in BITMEX_FALSE_AUTHORITY_TARGETS)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DatasetQuarantineError(message)


def _safe_absolute(path: Path) -> Path:
    path = path.expanduser()
    _require(".." not in path.parts, "path traversal rejected")
    path = path if path.is_absolute() else Path.cwd() / path
    assert_no_symlink_components(path, stop_at=Path(path.anchor))
    return path


def _read_artifact(path: Path) -> tuple[bytes, dict[str, Any]]:
    path = _safe_absolute(path)
    assert_regular_file(path, label="quarantine artifact")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        _require(stat.S_ISREG(before.st_mode), "artifact is not a regular file")
        raw = handle.read()
        after = os.fstat(handle.fileno())

    def identity(st: os.stat_result) -> tuple[int, ...]:
        return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_mode)

    _require(identity(before) == identity(after), "artifact changed while reading")
    _safe_absolute(path)
    _require(identity(path.stat()) == identity(after), "artifact path changed while reading")
    return raw, {
        "path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_size": len(raw), "device": after.st_dev, "inode": after.st_ino,
        "mtime_ns": after.st_mtime_ns, "ctime_ns": after.st_ctime_ns,
        "mode": after.st_mode,
    }


def _inspect_parquet(raw: bytes, path: Path) -> ParquetInspection:
    table = pq.read_table(pa.BufferReader(raw))
    required = {"funding_rate": pa.float64(), "funding_interval": pa.string(),
                "symbol": pa.string()}
    _require(len(table.column_names) == len(set(table.column_names)), "duplicate Parquet columns")
    for name, dtype in required.items():
        _require(name in table.column_names, f"required economic column missing: {name}")
        _require(table.schema.field(name).type == dtype, f"economic column type mismatch: {name}")
    rates = table.column("funding_rate").to_pylist()
    symbols = table.column("symbol").to_pylist()
    _require(all(isinstance(s, str) and bool(s.strip()) for s in symbols), "invalid symbol")
    return ParquetInspection(
        path=str(path), sha256=hashlib.sha256(raw).hexdigest(), byte_size=len(raw),
        row_count=table.num_rows, symbol_count=len(set(symbols)),
        nonzero_rate_count=sum(r is not None and (not math.isfinite(r) or r != 0) for r in rates),
        null_rate_count=sum(r is None for r in rates),
        empty_interval_count=sum(v is None or not v.strip()
                                 for v in table.column("funding_interval").to_pylist()),
    )


def inspect_funding_parquet(path: Path) -> ParquetInspection:
    raw, _ = _read_artifact(path)
    return _inspect_parquet(raw, path)


def _check_tree(directory: Path, relative_path: str) -> None:
    expected_files = {"manifest.json", relative_path}
    expected_dirs = {p.as_posix() for p in Path(relative_path).parents if p != Path(".")}
    found_files: set[str] = set()
    found_dirs: set[str] = set()
    for root, dirs, files in os.walk(directory, followlinks=False):
        for name in dirs + files:
            child = Path(root) / name
            _safe_absolute(child)
            rel = child.relative_to(directory).as_posix()
            if name in dirs:
                found_dirs.add(rel)
            else:
                assert_regular_file(child, label="dataset file")
                found_files.add(rel)
    _require(found_files == expected_files and found_dirs == expected_dirs,
             "unexpected or missing dataset tree artifacts")


def _quarantine_summary(original: Mapping[str, Any], at: str) -> dict[str, Any]:
    return {
        "quarantine_marker": QUARANTINE_MARKER, "quarantine_ticket": TICKET_ID,
        "quarantine_reason": QUARANTINE_REASON, "quarantined_at": at,
        "pre_quality_status": "PASS", "pre_quality_summary_json": _json(dict(original)),
        "pre_quality_summary": dict(original), "catalog_authority": "REJECTED",
        "preserved_manifest": True, "preserved_parquet": True,
    }


def _authenticate(catalog: SqliteDatasetCatalog, store: Path,
                  target: BitmexFalseAuthorityTarget) -> TargetInspection:
    _require(assert_relative_safe(target.relative_path) == target.relative_path,
             "noncanonical target path")
    directory = _safe_absolute(dataset_absolute_dir(store, target.dataset_id))
    _require(directory.is_dir(), "dataset directory missing")
    _check_tree(directory, target.relative_path)
    manifest_raw, manifest_artifact = _read_artifact(directory / "manifest.json")
    _require(manifest_artifact["sha256"] == target.manifest_file_sha256,
             "physical manifest hash mismatch")
    manifest = load_manifest_bytes(manifest_raw)
    _require(manifest.dataset_id == target.dataset_id, "manifest dataset identity mismatch")
    _require(manifest.manifest_sha256 == target.manifest_sha256, "canonical manifest hash mismatch")
    _require(manifest.quality_status is QualityStatus.PASS, "historical manifest is not PASS")
    _require(manifest.dataset_type == target.dataset_type, "manifest type mismatch")
    _require(len(manifest.files) == 1, "manifest must declare exactly one file")
    spec = manifest.files[0]
    _require((spec.relative_path, spec.sha256, spec.rows, spec.bytes) ==
             (target.relative_path, target.file_sha256, target.expected_rows,
              target.expected_byte_size), "manifest file identity mismatch")
    parquet_path = directory / target.relative_path
    parquet_raw, parquet_artifact = _read_artifact(parquet_path)
    _require(parquet_artifact["sha256"] == target.file_sha256, "Parquet hash mismatch")
    _require(len(parquet_raw) == target.expected_byte_size, "Parquet byte size mismatch")
    parquet = _inspect_parquet(parquet_raw, parquet_path)
    _require(parquet.row_count == target.expected_rows, "economic row count mismatch")
    _require(parquet.symbol_count == target.expected_symbols, "economic symbol count mismatch")
    _require(parquet.nonzero_rate_count == 0, "nonzero funding rates")
    _require(parquet.null_rate_count == 0, "null funding rates")
    _require(parquet.empty_interval_count == target.expected_rows, "nonempty funding intervals")

    row_value = catalog.get_dataset(target.dataset_id)
    _require(row_value is not None, "dataset is not registered")
    row = dict(row_value)
    relative_dir = dataset_relative_dir(target.dataset_id).as_posix()

    def iso(dt: datetime | None) -> str | None:
        return dt.astimezone(UTC).isoformat() if dt is not None else None

    expected = {
        "dataset_id": target.dataset_id, "dataset_type": manifest.dataset_type,
        "schema_version": manifest.schema.version,
        "schema_fingerprint": manifest.schema.fingerprint,
        "manifest_sha256": manifest.manifest_sha256,
        "manifest_uri": relative_dir + "/manifest.json", "publication_uri": relative_dir,
        "transform_name": manifest.transform.name, "transform_version": manifest.transform.version,
        "code_commit": manifest.code.commit, "config_sha256": manifest.config.config_sha256,
        "row_count": manifest.statistics.row_count, "byte_size": manifest.statistics.byte_size,
        "event_start": iso(manifest.coverage.event_start),
        "event_end": iso(manifest.coverage.event_end),
        "availability_start": iso(manifest.coverage.availability_start),
        "availability_end": iso(manifest.coverage.availability_end),
        "quality_status": row["quality_status"], "quality_summary_json": row["quality_summary_json"],
        "supersedes_dataset_id": manifest.supersedes_dataset_id,
        "publication_status": "REGISTERED", "created_at": target.catalog_created_at,
    }
    _require(row == expected, "catalog complete dataset identity mismatch")
    _require(manifest.statistics.row_count == target.expected_rows and
             manifest.statistics.byte_size == target.expected_byte_size,
             "manifest statistics mismatch")
    already = row["quality_status"] == "REJECTED"
    if already:
        summary = json.loads(row["quality_summary_json"])
        _require(isinstance(summary, dict), "invalid quarantine summary")
        _require(row["quality_summary_json"] == _json(summary),
                 "noncanonical quarantine summary")
        at = summary.get("quarantined_at")
        _require(isinstance(at, str), "missing quarantine timestamp")
        dt = datetime.fromisoformat(at)
        _require(dt.tzinfo is not None and dt.utcoffset().total_seconds() == 0,
                 "invalid quarantine timestamp")
        _require(summary == _quarantine_summary(manifest.quality_summary, at),
                 "invalid quarantine marker or preserved prior evidence")
    else:
        _require(row["quality_status"] == "PASS", "unexpected catalog quality status")
        _require(row["quality_summary_json"] == _json(dict(manifest.quality_summary)),
                 "catalog prior quality evidence mismatch")
    expected_files = ({
        "dataset_id": target.dataset_id, "storage_uri": target.relative_path,
        "file_sha256": target.file_sha256, "row_count": target.expected_rows,
        "byte_size": target.expected_byte_size, "partition_json": _json(dict(spec.partition)),
    },)
    files = tuple(dict(f) for f in catalog.list_files(target.dataset_id))
    _require(files == expected_files, "catalog complete file identity mismatch")
    _require(not catalog.list_raw_inputs(target.dataset_id) and
             not catalog.list_dataset_inputs(target.dataset_id) and not manifest.dependencies,
             "unexpected dependency identity")
    return TargetInspection(
        dataset_id=target.dataset_id, catalog_row=row, catalog_files=files,
        manifest_sha256=manifest.manifest_sha256,
        manifest_file_sha256=manifest_artifact["sha256"],
        manifest_quality_status=manifest.quality_status.value,
        manifest_created_at=iso(manifest.publication.created_at), parquet=parquet,
        artifacts=(manifest_artifact, parquet_artifact), already_quarantined=already,
    )


def _resolver_snapshot(catalog: SqliteDatasetCatalog,
                       targets: Sequence[BitmexFalseAuthorityTarget]) -> ResolverSnapshot:
    return ResolverSnapshot(
        latest={dtype: catalog.resolve_latest_by_type(dtype)
                for dtype in sorted({t.dataset_type for t in targets})},
        eligible_targets=tuple(t.dataset_id for t in targets if catalog.is_consumable(t.dataset_id)),
    )


def _execute(catalog: SqliteDatasetCatalog, store_root: Path,
             targets: tuple[BitmexFalseAuthorityTarget, ...], *,
             dry_run: bool, now: datetime | None) -> QuarantineReport:
    _require(len(targets) == 5 and len({t.dataset_id for t in targets}) == 5,
             "quarantine requires exactly five distinct targets")
    at = now or datetime.now(UTC)
    _require(at.tzinfo is not None, "quarantine timestamp must be timezone-aware")
    generated_at = at.astimezone(UTC).isoformat()
    # All authentication, snapshots, writes, and postconditions are under the
    # owned transaction, including no-op replay. No outside preflight authority.
    try:
        store = _safe_absolute(Path(store_root))
        _require(store.is_dir(), "existing store directory required")
        with catalog.quarantine_transaction(inspection_only=dry_run):
            database = _safe_absolute(catalog.database_path())
            assert_regular_file(database, label="existing catalog")
            before_resolver = _resolver_snapshot(catalog, targets)
            before = tuple(_authenticate(catalog, store, t) for t in targets)
            flags = {i.already_quarantined for i in before}
            _require(len(flags) == 1, "partial or mixed quarantine state")
            replay = before[0].already_quarantined
            if replay:
                timestamps = {json.loads(i.catalog_row["quality_summary_json"])["quarantined_at"]
                              for i in before}
                _require(len(timestamps) == 1, "conflicting prior quarantine timestamps")
            expected_rows = []
            for inspection in before:
                expected_row = dict(inspection.catalog_row)
                if not dry_run and not replay:
                    summary = _quarantine_summary(
                        json.loads(expected_row["quality_summary_json"]), generated_at)
                    catalog.compare_and_swap_quality_status(
                        inspection.catalog_row, inspection.catalog_files,
                        quality_status=QualityStatus.REJECTED, quality_summary=summary)
                    expected_row.update(quality_status="REJECTED", quality_summary_json=_json(summary))
                expected_rows.append(expected_row)
            after = tuple(_authenticate(catalog, store, t) for t in targets)
            for pre, post, expected_row in zip(before, after, expected_rows, strict=True):
                _require(post.catalog_row == expected_row, "postcondition complete row mismatch")
                _require(post.catalog_files == pre.catalog_files, "postcondition file rows changed")
                _require(post.artifacts == pre.artifacts, "postcondition artifact identity changed")
            after_resolver = _resolver_snapshot(catalog, targets)
            if not dry_run or replay:
                _require(not after_resolver.eligible_targets,
                         "postcondition: target remains eligible in default resolver")
            database_path = str(database)
            report = QuarantineReport(
                ticket=TICKET_ID, reason=QUARANTINE_REASON, dry_run=dry_run,
                applied=not dry_run and not replay, idempotent_replay=not dry_run and replay,
                disposition="inspected" if dry_run else "replayed" if replay else "applied",
                generated_at=generated_at, targets=targets, pre_resolver=before_resolver,
                post_resolver=after_resolver, inspections_pre=before, inspections_post=after,
                artifacts_unchanged=True, database_path=database_path, store_root=str(store),
            )
        return report
    except DatasetQuarantineError:
        raise
    except (DatasetError, OSError, ValueError, TypeError, KeyError, sqlite3.Error, pa.ArrowException) as exc:
        raise DatasetQuarantineError("quarantine authentication/transaction failed",
                                     context={"detail": str(exc)}) from exc


def execute_bitmex_funding_quarantine(catalog: SqliteDatasetCatalog, store_root: Path, *,
                                      dry_run: bool = False,
                                      now: datetime | None = None) -> QuarantineReport:
    """Production API: the five pinned authorities cannot be overridden."""
    return _execute(catalog, store_root, BITMEX_FALSE_AUTHORITY_TARGETS, dry_run=dry_run, now=now)


def execute_fixture_quarantine(catalog: SqliteDatasetCatalog, store_root: Path, *,
                               targets: Sequence[BitmexFalseAuthorityTarget],
                               dry_run: bool = False,
                               now: datetime | None = None) -> QuarantineReport:
    """Test-only equivalent plan; reject production IDs and require five fixtures.

    Not exposed by the CLI. Callers own an isolated temporary catalog and store;
    no production identity can pass through this API.
    """
    selected = tuple(targets)
    _require(not set(exact_false_authority_ids()) & {t.dataset_id for t in selected},
             "fixture API rejects production identities")
    return _execute(catalog, store_root, selected, dry_run=dry_run, now=now)


def validate_report_destination(path: Path, *, database_path: Path, store_root: Path) -> Path:
    destination = _safe_absolute(path)
    database = _safe_absolute(database_path)
    store = _safe_absolute(store_root)
    _require(not destination.is_relative_to(store), "report destination is inside the store")
    protected = {database, *(Path(str(database) + suffix) for suffix in ("-wal", "-shm", "-journal"))}
    _require(destination not in protected, "report destination is a catalog artifact")
    _require(destination.parent.is_dir(), "report parent directory must already exist")
    if destination.exists():
        assert_regular_file(destination, label="existing report")
        _require(not any(p.exists() and destination.samefile(p) for p in protected),
                 "report destination aliases a catalog artifact")
    return destination


def write_quarantine_report(report: QuarantineReport, path: Path) -> None:
    """Atomically publish JSON; errors explicitly preserve catalog disposition.

    The catalog transaction is already complete. A reporting failure cannot undo
    it. Replay reauthenticates and can recover the report without changing metadata.
    """
    temporary_name: str | None = None
    directory_fd: int | None = None
    published = False
    try:
        destination = validate_report_destination(
            path, database_path=Path(report.database_path), store_root=Path(report.store_root))
        payload = (json.dumps(report.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
        directory_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        directory_stat = os.fstat(directory_fd)
        current_stat = destination.parent.stat()
        _require((directory_stat.st_dev, directory_stat.st_ino) ==
                 (current_stat.st_dev, current_stat.st_ino), "report parent changed")
        temporary_name = ".quarantine-report-" + uuid.uuid4().hex
        fd = os.open(temporary_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory_fd)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        validate_report_destination(destination, database_path=Path(report.database_path),
                                    store_root=Path(report.store_root))
        current_stat = destination.parent.stat()
        _require((directory_stat.st_dev, directory_stat.st_ino) ==
                 (current_stat.st_dev, current_stat.st_ino), "report parent changed")
        # Directory-relative rename stays anchored to the inspected directory
        # even if a parent path is renamed concurrently. It cannot follow a
        # replacement ancestor into a catalog/store destination.
        os.replace(temporary_name, destination.name, src_dir_fd=directory_fd,
                   dst_dir_fd=directory_fd)
        temporary_name = None
        published = True
        os.fsync(directory_fd)
    except (DatasetError, OSError, ValueError, TypeError) as exc:
        raise QuarantineReportError(
            "report publication failed; catalog disposition is unchanged",
            context={"catalog_disposition": report.disposition, "applied": report.applied,
                     "idempotent_replay": report.idempotent_replay,
                     "report_renamed": published, "detail": str(exc)},
        ) from exc
    finally:
        if directory_fd is not None:
            if temporary_name is not None:
                try:
                    os.unlink(temporary_name, dir_fd=directory_fd)
                except OSError:
                    pass
            os.close(directory_fd)
