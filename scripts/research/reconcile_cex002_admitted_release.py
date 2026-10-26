"""Reconcile the one already admitted CEX-002 release against its accepted proof.

This command does not create a proof, decode Parquet rows, or admit a dataset.
The accepted consumer proof supplies the historical value/readback result;
fresh physical hashes, footers, and catalog snapshots establish that its inputs
and the admitted release have not changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import stat
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import pyarrow.parquet as pq

from cryptofactors.catalog.dataset.cex002_reference_release import (
    BUNDLE_ROOT_RELATIVE,
    COMPONENT_KEYS,
    HASH_CHUNK_BYTES,
    OPERATING_RESERVE_BYTES,
    PREPARED_MAX_BYTES,
    PROOF_DOCUMENT,
    PROOF_KEYS,
    PROOF_MAX_BYTES,
    PROOF_SCOPE,
    PUBLICATION_DOCUMENT,
    RELEASE_METADATA_REMAINDER_BYTES,
    RUNTIME_CODE_PATHS,
    FileSnapshot,
    _anchor,
    _bitmex_snapshot,
    _check_policy,
    _classify,
    _descriptor,
    _dumps,
    _enforce_resources,
    _footer_from_partition,
    _load_json,
    _load_prepared,
    _open_catalog,
    _open_readonly,
    _refuse_pending_caller,
    _registry_contracts,
    _relative,
    _release_charge,
    _require_bitmex,
    _require_catalog_file,
    _require_connection_binding,
    _time_plan,
    production_release_policy,
    seal_code_identity,
)
from cryptofactors.catalog.dataset.models import CodeIdentity, DatasetManifest, OutputFileSpec

SOURCE_COMMIT = "1f5629badfa0e8af6338fbeb019a5f7e60b6a324"
CANDIDATE_SHA256 = "8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34"
PUBLICATION_SHA256 = "5ea22270b71064c94c4f6dc60f3f045219742a3130cfdb1293b6cbe47a99a30d"
PROOF_SHA256 = "3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d"
PROOF_BYTES = 264_156_517
CHECKER_SHA256 = "ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117"
NAUTILUS_VERSION = "2.0.0rc3"
EXPECTED_DATASETS = 11
EXPECTED_FILES = 423_446
EXPECTED_TABLES = 178_947
EXPECTED_METADATA = 244_499
EXPECTED_ROWS = 1_165_116_869
PUBLICATION_ALLOWANCE_BYTES = 8_388_608
DEADLINE_SECONDS = 1_800
PROGRESS_SECONDS = 5

_ACCEPTED_ANCHORS = {
    "dataset": (11, "04d27a4fc58f80189889df81e3e78a196c33ee7d0d7a98cb497b72bb15993f5d"),
    "dataset_file": (423_446, "c37bdb87f6925f0c6441ed6bf2b1751904b6b7ddab4dd0f054154b871f9c9855"),
    "dataset_input_dataset": (10, "9f4fbf2eec784f2b801f709b4b27ab24b7f0388ad4ad3d22e6d24640d6e2f322"),
    "dataset_input_raw_object": (0, "6a8d487a15f8d0927d64f2c03491325ce88b37d29ed7402743c05bd67f210de3"),
}
_ACCEPTED_QUARANTINE_SHA256 = "b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103"
_TABLE_SQL = {
    "dataset": "SELECT * FROM dataset WHERE transform_name='cex002_reference_publication' ORDER BY dataset_id",
    "dataset_file": "SELECT * FROM dataset_file WHERE dataset_id IN (SELECT dataset_id FROM dataset WHERE transform_name='cex002_reference_publication') ORDER BY dataset_id, storage_uri",
    "dataset_input_dataset": "SELECT * FROM dataset_input_dataset WHERE dataset_id IN (SELECT dataset_id FROM dataset WHERE transform_name='cex002_reference_publication') ORDER BY dataset_id, input_dataset_id, role",
    "dataset_input_raw_object": "SELECT * FROM dataset_input_raw_object WHERE dataset_id IN (SELECT dataset_id FROM dataset WHERE transform_name='cex002_reference_publication') ORDER BY dataset_id, raw_object_id, role",
}
_COLUMNS = {
    "dataset": (
        "dataset_id", "dataset_type", "schema_version", "manifest_sha256", "manifest_uri",
        "transform_name", "transform_version", "code_commit", "config_sha256", "row_count",
        "byte_size", "event_start", "event_end", "availability_start", "availability_end",
        "quality_status", "supersedes_dataset_id", "created_at", "publication_status",
        "schema_fingerprint", "quality_summary_json", "publication_uri",
    ),
    "dataset_file": ("dataset_id", "storage_uri", "file_sha256", "byte_size", "row_count", "partition_json"),
    "dataset_input_dataset": ("dataset_id", "input_dataset_id", "role"),
    "dataset_input_raw_object": ("dataset_id", "raw_object_id", "role"),
}


class ReconciliationError(ValueError):
    def __init__(self, blocker: str, message: str) -> None:
        super().__init__(message)
        self.blocker = blocker


def _need(condition: bool, blocker: str, message: str) -> None:
    if not condition:
        raise ReconciliationError(blocker, message)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


@dataclass(frozen=True, slots=True)
class _Authority:
    candidate: str = CANDIDATE_SHA256
    publication: str = PUBLICATION_SHA256
    proof: str = PROOF_SHA256
    proof_bytes: int = PROOF_BYTES
    checker: str = CHECKER_SHA256
    nautilus: str = NAUTILUS_VERSION
    source_commit: str = SOURCE_COMMIT
    datasets: int = EXPECTED_DATASETS
    files: int = EXPECTED_FILES
    tables: int = EXPECTED_TABLES
    metadata: int = EXPECTED_METADATA
    rows: int = EXPECTED_ROWS
    anchors: Mapping[str, tuple[int, str]] | None = None
    quarantine_sha256: str = _ACCEPTED_QUARANTINE_SHA256
    code: CodeIdentity | None = None  # Private fixture seam; never exposed by CLI.
    checker_path: Path | None = None
    observed_free_bytes: int | None = None


class _Progress:
    def __init__(self, deadline_seconds: float) -> None:
        self.began = time.monotonic()
        self.last = self.began
        self.deadline_seconds = deadline_seconds
        self.stage = "start"
        self.files = 0
        self.bytes = 0
        self.expected_files = 0
        self.expected_bytes = 0

    def tick(self, stage: str | None = None, *, force: bool = False) -> None:
        now = time.monotonic()
        if stage is not None:
            self.stage = stage
        if now - self.began > self.deadline_seconds:
            raise ReconciliationError("deadline", "30-minute reconciliation deadline exceeded")
        if force or now - self.last >= PROGRESS_SECONDS:
            sys.stderr.write(_json({
                "stage": self.stage, "hash_operations_cumulative": self.files,
                "hashed_bytes_cumulative": self.bytes,
                "expected_unique_files": self.expected_files,
                "expected_unique_bytes": self.expected_bytes,
                "elapsed_seconds": round(now - self.began, 3),
            }) + "\n")
            sys.stderr.flush()
            self.last = now


def _hash_bound(root: Path, relative: str, progress: _Progress) -> FileSnapshot:
    path = _relative(root, relative)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        _need(stat.S_ISREG(before.st_mode), "unsafe_path", "referenced file is not regular")
        digest = hashlib.sha256()
        size = 0
        while block := os.read(descriptor, HASH_CHUNK_BYTES):
            digest.update(block)
            size += len(block)
            progress.bytes += len(block)
            progress.tick()
        after = os.fstat(descriptor)
        _need(
            (before.st_dev, before.st_ino, before.st_size) == (after.st_dev, after.st_ino, after.st_size)
            and size == before.st_size,
            "input_changed", "referenced file changed during hashing",
        )
        # Re-resolve the lexical path after hashing to reject replacement of the
        # pathname while the held descriptor still named the old inode.
        current = _relative(root, relative).stat()
        _need((current.st_dev, current.st_ino) == (before.st_dev, before.st_ino),
              "input_changed", "referenced pathname changed during hashing")
        progress.files += 1
        progress.tick()
        return FileSnapshot(relative, digest.hexdigest(), size, before.st_ino, before.st_dev)
    finally:
        os.close(descriptor)


def _source_identity(root: Path, authority: _Authority, progress: _Progress) -> CodeIdentity:
    if authority.code is not None:
        return authority.code
    executing = {relative: root / relative for relative in RUNTIME_CODE_PATHS}
    for relative in RUNTIME_CODE_PATHS:
        _relative(root, relative)
    progress.tick("source_identity", force=True)
    return seal_code_identity(root, authority.source_commit, bind_runtime=True, executing=executing)


def _source_self(source_sha256: str, progress: _Progress) -> None:
    path = Path(__file__)
    _need(not path.is_symlink(), "source_identity", "executing reconciliation script is a symlink")
    digest = hashlib.sha256()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        _need(stat.S_ISREG(before.st_mode), "source_identity", "executing source is not regular")
        size = 0
        while block := os.read(descriptor, HASH_CHUNK_BYTES):
            digest.update(block)
            size += len(block)
            progress.tick()
        after = os.fstat(descriptor)
        current = path.lstat()
        _need((before.st_dev, before.st_ino, before.st_size)
              == (after.st_dev, after.st_ino, after.st_size)
              == (current.st_dev, current.st_ino, current.st_size)
              and size == before.st_size,
              "source_identity", "executing source changed while hashing")
    finally:
        os.close(descriptor)
    _need(digest.hexdigest() == source_sha256, "source_identity", "own source SHA mismatch")


def _checker_identity(root: Path, authority: _Authority, progress: _Progress) -> FileSnapshot:
    if authority.checker_path is None:
        snapshot = _hash_bound(root, "scripts/research/check_cex002_nautilus_consumer.py", progress)
    else:
        snapshot = _hash_bound(authority.checker_path.parent, authority.checker_path.name, progress)
    _need(snapshot.sha256 == authority.checker, "checker_identity", "consumer checker bytes changed")
    return snapshot


def _capacity(root: Path, policy: Any, manifests: Sequence[DatasetManifest], progress: _Progress) -> dict[str, int]:
    progress.tick("capacity", force=True)
    bundle_bytes, charged, incoming, subtotals = _release_charge(root, manifests, ())
    # The accepted proof is already an owned on-disk metadata file in charged.
    # This command writes no replacement proof. Keep only the publication headroom.
    required = charged + PUBLICATION_ALLOWANCE_BYTES
    _need(required <= RELEASE_METADATA_REMAINDER_BYTES, "metadata_bound", "release metadata cap exceeded")
    _enforce_resources(
        policy, root, bundle_bytes, required, stage="reconciliation",
        incoming_bytes=incoming, charged_subtotals=subtotals,
    )
    free = policy.observed_free_bytes
    if free is None:
        facts = os.statvfs(root)
        free = int(facts.f_bavail) * int(facts.f_frsize)
    return {"bundle_bytes": bundle_bytes, "charged_bytes": charged,
            "reserved_metadata_bytes": required, "sqlite_bytes": subtotals["sqlite_bytes"],
            "operating_reserve_bytes": OPERATING_RESERVE_BYTES, "observed_free_bytes": free}


def _component_shape(component: Mapping[str, Any], spec: OutputFileSpec, manifest: DatasetManifest,
                     schema: Any | None) -> None:
    path = spec.relative_path
    _need(type(component) is dict and set(component) == COMPONENT_KEYS,
          "proof_contract", "component keys differ from strict v1")
    kind = spec.partition.get("kind")
    _need(kind in {"table", "metadata"} and component["kind"] == kind,
          "proof_contract", "component kind differs from manifest")
    _need(component["relative_path"] == path and component["physical_sha256"] == spec.sha256,
          "proof_contract", "component path or physical digest differs from manifest")
    _need(type(component["physical_bytes"]) is int and component["physical_bytes"] == spec.bytes,
          "proof_contract", "component byte count differs from manifest")
    for key in ("source_row_count", "readback_row_count"):
        _need(type(component[key]) is int and component[key] == spec.rows,
              "proof_contract", "component row count differs from manifest")
    for key in ("source_value_sha256", "roundtrip_value_sha256"):
        value = component[key]
        _need(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
              "proof_contract", "component value digest is malformed")
    _need(component["source_value_sha256"] == component["roundtrip_value_sha256"],
          "proof_contract", "accepted source and readback value digests differ")
    if kind == "metadata":
        _need(spec.rows == 0 and component["source_value_sha256"] == spec.sha256
              and component["value_identity"] == "metadata_bytes"
              and component["time_start"] is None and component["time_end"] is None
              and component["time_absence_reason"] == "non_temporal_component",
              "proof_contract", "metadata component does not have byte identity")
        return
    _need(component["value_identity"] == "typed_row_digest", "proof_contract", "table value identity changed")
    assert schema is not None
    time_fields, _time_kind = _time_plan(schema)
    start, end, reason = (component[key] for key in ("time_start", "time_end", "time_absence_reason"))
    if not time_fields:
        _need(start is None and end is None and reason == "non_temporal_component",
              "proof_contract", "non-temporal table has a time claim")
    elif reason is None:
        _need(type(start) is str and type(end) is str and bool(start) and bool(end),
              "proof_contract", "temporal table lacks accepted time bounds")
    else:
        _need(start is None and end is None and reason == "empty_component",
              "proof_contract", "temporal table has incompatible absence reason")
    if manifest.dataset_type == "binance_usdm_bar_1h":
        _need(spec.partition.get("role") == "partition" and "component" in spec.partition
              and type(spec.partition["component"]) is str
              and spec.partition["component"] in {"", "quality_gap"},
              "proof_contract", "bar table has unknown role or component")
        if spec.partition["component"] == "":
            _need({"venue_symbol", "open_time", "close_time", "open", "high", "low", "close", "volume"}
                  <= set(schema.names), "proof_contract", "primary bar lacks native projection")


def _proof_and_files(root: Path, manifests: Sequence[DatasetManifest], proof: Mapping[str, Any],
                     authority: _Authority, progress: _Progress) -> tuple[list[FileSnapshot], dict[str, int]]:
    _need(type(proof) is dict and set(proof) == PROOF_KEYS, "proof_contract", "proof root keys are not strict v1")
    _need(proof.get("document_type") == PROOF_DOCUMENT and proof.get("schema_version") == 1
          and type(proof.get("schema_version")) is int and proof.get("status") == "PASS"
          and proof.get("scope") == PROOF_SCOPE and proof.get("candidate_sha256") == authority.candidate
          and proof.get("checker_source_sha256") == authority.checker
          and proof.get("nautilus_version") == authority.nautilus,
          "proof_contract", "accepted proof root binding changed")
    entries = proof.get("datasets")
    _need(type(entries) is list and len(entries) == len(manifests), "proof_contract", "proof dataset count changed")
    counts = {"datasets": 0, "files": 0, "tables": 0, "metadata": 0, "rows": 0, "edges": 0, "raw_edges": 0}
    snapshots: list[FileSnapshot] = []
    seen_global: set[str] = set()
    for manifest, entry in zip(manifests, entries, strict=True):
        progress.tick("physical_authentication", force=True)
        _need(type(entry) is dict and set(entry) == {"dataset_id", "components"}
              and entry.get("dataset_id") == manifest.dataset_id,
              "proof_contract", "proof dataset identity or order changed")
        components = entry.get("components")
        _need(type(components) is list and len(components) == len(manifest.files),
              "proof_contract", "proof component count changed")
        observed: dict[str, Mapping[str, Any]] = {}
        for component in components:
            _need(type(component) is dict and set(component) == COMPONENT_KEYS,
                  "proof_contract", "malformed strict component")
            path = component.get("relative_path")
            _need(type(path) is str and path not in observed and path not in seen_global,
                  "proof_contract", "duplicate or malformed component path")
            observed[path] = component
            seen_global.add(path)
        _need(set(observed) == {spec.relative_path for spec in manifest.files},
              "proof_contract", "proof file closure differs from manifest")
        contracts = _registry_contracts(manifest)
        for spec in manifest.files:
            path = spec.relative_path
            kind = spec.partition.get("kind")
            schema = None
            snapshot = _hash_bound(root, path, progress)
            _need((snapshot.sha256, snapshot.byte_size) == (spec.sha256, spec.bytes),
                  "physical_mismatch", "referenced bytes differ from accepted manifest")
            if kind == "table":
                _footer_from_partition(_relative(root, path), spec, contracts)
                schema = pq.ParquetFile(_relative(root, path)).schema_arrow
                counts["tables"] += 1
            elif kind == "metadata":
                counts["metadata"] += 1
            else:
                raise ReconciliationError("proof_contract", "unknown file kind")
            _component_shape(observed[path], spec, manifest, schema)
            snapshots.append(snapshot)
            counts["files"] += 1
            counts["rows"] += spec.rows
        counts["datasets"] += 1
        counts["edges"] += len(manifest.dependencies)
    _need(counts == {"datasets": authority.datasets, "files": authority.files,
                     "tables": authority.tables, "metadata": authority.metadata,
                     "rows": authority.rows, "edges": authority.datasets - 1, "raw_edges": 0},
          "closure", "release physical count basis changed")
    return snapshots, counts


def _catalog_snapshot(connection: sqlite3.Connection, manifests: Sequence[DatasetManifest],
                      anchors: Mapping[str, tuple[int, str]], quarantine_sha256: str,
                      progress: _Progress) -> dict[str, dict[str, Any]]:
    """Exactly the Review519 all-column SELECT/order/serialization, streamed."""
    _need(set(anchors) == set(_TABLE_SQL), "catalog_anchor", "four accepted snapshot anchors are required")
    observed: dict[str, dict[str, Any]] = {}
    quarantine_rows = connection.execute(
        "SELECT dataset_id, quality_status, publication_status, quality_summary_json "
        "FROM dataset WHERE quality_summary_json LIKE '%cex002_bitmex_false_authority%' "
        "ORDER BY dataset_id"
    ).fetchall()
    quarantine_body = json.dumps([tuple(row) for row in quarantine_rows],
                                 default=str, separators=(",", ":"), ensure_ascii=False)
    _need(len(quarantine_rows) == 5 and hashlib.sha256(quarantine_body.encode()).hexdigest() == quarantine_sha256,
          "quarantine_anchor", "accepted BitMEX quarantine snapshot changed")
    observed["quarantine"] = {"count": 5, "sha256": quarantine_sha256}
    for name, sql in _TABLE_SQL.items():
        cursor = connection.execute(sql)
        columns = [description[0] for description in cursor.description]
        _need(set(columns) == set(_COLUMNS[name]) and len(columns) == len(_COLUMNS[name]),
              "catalog_schema", "catalog columns differ from accepted schema")
        digest = hashlib.sha256()
        digest.update((json.dumps(columns, separators=(",", ":")) + "\n").encode())
        count = 0
        for row in cursor:
            digest.update((json.dumps(tuple(row), default=str, separators=(",", ":"), ensure_ascii=False) + "\n").encode())
            count += 1
            if count % 4096 == 0:
                progress.tick()
        item = {"count": count, "sha256": digest.hexdigest()}
        _need((count, item["sha256"]) == anchors[name], "catalog_anchor", f"{name} differs from accepted admission snapshot")
        observed[name] = item
        progress.tick(f"catalog_{name}", force=True)
    ids = [row[0] for row in connection.execute(
        "SELECT dataset_id FROM dataset WHERE transform_name='cex002_reference_publication' ORDER BY dataset_id")]
    _need(ids == sorted(item.dataset_id for item in manifests), "catalog_closure", "catalog dataset IDs differ from manifests")
    return observed


def _catalog_semantics(catalog: Any, manifests: Sequence[DatasetManifest], publication_relative: str,
                       progress: _Progress) -> None:
    _require_bitmex(_bitmex_snapshot(catalog))
    _need(_classify(catalog, manifests, publication_relative) == "identical", "catalog_classification",
          "already admitted release is not identical")
    for manifest in manifests:
        progress.tick()
        _need(catalog.is_consumable(manifest.dataset_id),
              "catalog_classification", "dataset is not the accepted consumable release")
        _need("publication_sha256" not in _dumps(manifest.quality_summary)
              and "prepared_sha256" not in _dumps(manifest.quality_summary),
              "catalog_classification", "circular publication quality summary")


def _recheck(root: Path, snapshots: Sequence[FileSnapshot], progress: _Progress) -> None:
    progress.tick("complete_recheck", force=True)
    for previous in snapshots:
        current = _hash_bound(root, previous.relative_path, progress)
        _need(current == previous, "input_changed", "referenced file changed before replay")


def _metadata_recheck(root: Path, names: Sequence[FileSnapshot], progress: _Progress) -> None:
    for previous in names:
        _need(_hash_bound(root, previous.relative_path, progress) == previous,
              "input_changed", "release metadata changed before replay")


def reconcile(
    repo: Path, catalog_path: Path, source_sha256: str,
    *,
    connection: sqlite3.Connection | None = None,
    _fixture: _Authority | None = None,
    _deadline_seconds: float = DEADLINE_SECONDS,
) -> dict[str, Any]:
    """Inspect one fixed admitted release; private arguments support tiny fixtures."""
    authority = _fixture if _fixture is not None else _Authority()
    anchors = authority.anchors if authority.anchors is not None else _ACCEPTED_ANCHORS
    progress = _Progress(_deadline_seconds)
    progress.tick("preflight", force=True)
    _refuse_pending_caller(connection)
    _source_self(source_sha256, progress)
    root = _anchor(repo)
    _need(catalog_path.is_absolute(), "unsafe_path", "catalog path must be absolute")
    code = _source_identity(root, authority, progress)
    policy = production_release_policy(root, catalog_path, code)
    if authority.observed_free_bytes is not None:
        policy = replace(policy, observed_free_bytes=authority.observed_free_bytes)
    _check_policy(policy)
    _require_catalog_file(policy)
    if connection is not None:
        _require_connection_binding(connection, catalog_path)
    # A known reserve shortage stops before manifest decoding or file traversal.
    _enforce_resources(policy, root, 0, 0, stage="early_reserve", incoming_bytes=0)
    checker_snapshot = _checker_identity(root, authority, progress)
    prepared, manifests = _load_prepared(root, authority.candidate)
    _need(prepared.get("consumable") is False and len(manifests) == authority.datasets,
          "prepared_identity", "prepared release identity changed")
    _need(all(item.code == code for item in manifests), "source_identity", "manifest runtime source identity changed")
    prepared_relative = f"{BUNDLE_ROOT_RELATIVE}/.prepared/{authority.candidate}.json"
    publication_relative = f"{BUNDLE_ROOT_RELATIVE}/.publication/{authority.publication}.json"
    proof_relative = f"{BUNDLE_ROOT_RELATIVE}/.proofs/{authority.proof}.json"
    metadata_names = [prepared_relative]
    metadata_names.extend(str(entry["manifest_relative_path"]) for entry in prepared["datasets"])
    metadata_names.extend((publication_relative, proof_relative))
    metadata_snapshots = [_hash_bound(root, name, progress) for name in metadata_names[:-2]]
    _need(metadata_snapshots[0].sha256 == authority.candidate, "prepared_identity", "candidate bytes changed")
    for entry, snapshot in zip(prepared["datasets"], metadata_snapshots[1:], strict=True):
        _need((snapshot.sha256, snapshot.byte_size) == (entry["manifest_file_sha256"], entry["manifest_bytes"]),
              "manifest_identity", "manifest bytes changed")
    # Capacity precedes the expensive proof parse and accepted-file traversal.
    resource = _capacity(root, policy, manifests, progress)
    document, publication_payload = _load_json(root, publication_relative, authority.publication, PREPARED_MAX_BYTES)
    _need(document.get("document_type") == PUBLICATION_DOCUMENT and document.get("consumable") is True,
          "publication_identity", "publication is not final and consumable")
    expected_publication = _descriptor(manifests, document_type=PUBLICATION_DOCUMENT, extra={
        "prepared_sha256": authority.candidate, "proof_sha256": authority.proof,
        "proof_relative_path": proof_relative, "proof_bytes": authority.proof_bytes,
        "checker_source_sha256": authority.checker, "nautilus_version": authority.nautilus,
    })
    _need(document == expected_publication, "publication_identity", "publication does not bind accepted authorities")
    _need(len(publication_payload) <= PREPARED_MAX_BYTES, "metadata_bound", "publication exceeds cap")
    proof_document, proof_payload = _load_json(root, proof_relative, authority.proof, PROOF_MAX_BYTES)
    _need(len(proof_payload) == authority.proof_bytes, "proof_identity", "accepted proof byte count changed")
    publication_snapshot = _hash_bound(root, publication_relative, progress)
    proof_snapshot = _hash_bound(root, proof_relative, progress)
    _need((publication_snapshot.sha256, publication_snapshot.byte_size)
          == (authority.publication, len(publication_payload)),
          "publication_identity", "publication changed after authenticated read")
    _need((proof_snapshot.sha256, proof_snapshot.byte_size)
          == (authority.proof, authority.proof_bytes),
          "proof_identity", "proof changed after authenticated read")
    metadata_snapshots.extend((publication_snapshot, proof_snapshot))
    progress.expected_files = authority.files
    progress.expected_bytes = sum(spec.bytes for item in manifests for spec in item.files)
    progress.tick("accepted_proof", force=True)
    snapshots, counts = _proof_and_files(root, manifests, proof_document, authority, progress)
    del proof_payload, proof_document
    _need(progress.files >= authority.files, "closure", "physical traversal did not finish")
    _capacity(root, policy, manifests, progress)
    _metadata_recheck(root, metadata_snapshots, progress)
    _need(_source_identity(root, authority, progress) == code, "source_identity", "runtime code changed")
    _source_self(source_sha256, progress)
    _need(_checker_identity(root, authority, progress) == checker_snapshot,
          "checker_identity", "checker changed before replay")
    catalog = _open_catalog(policy, connection)
    owned = catalog._owned
    try:
        _need(not catalog._conn.in_transaction, "pending_catalog_transaction", "catalog connection is busy")
        catalog._conn.execute("BEGIN IMMEDIATE")
        try:
            progress.tick("replay_transaction", force=True)
            _metadata_recheck(root, metadata_snapshots, progress)
            _need(_source_identity(root, authority, progress) == code, "source_identity", "runtime code changed inside replay")
            _source_self(source_sha256, progress)
            _need(_checker_identity(root, authority, progress) == checker_snapshot,
                  "checker_identity", "checker changed inside replay")
            _recheck(root, snapshots, progress)
            _catalog_semantics(catalog, manifests, publication_relative, progress)
            replay_snapshot = _catalog_snapshot(catalog._conn, manifests, anchors,
                                                authority.quarantine_sha256, progress)
        finally:
            catalog._conn.rollback()  # Identical replay is deliberately a no-op.
        progress.tick("replay_rolled_back", force=True)
        reader = _open_readonly(policy)
        try:
            reader._conn.execute("BEGIN")
            try:
                progress.tick("read_only_snapshot", force=True)
                _catalog_semantics(reader, manifests, publication_relative, progress)
                read_snapshot = _catalog_snapshot(reader._conn, manifests, anchors,
                                                  authority.quarantine_sha256, progress)
            finally:
                reader._conn.rollback()
        finally:
            reader._conn.close()
        _need(read_snapshot == replay_snapshot, "catalog_changed", "read-only snapshot differs from replay")
        _metadata_recheck(root, metadata_snapshots, progress)
        _need(_source_identity(root, authority, progress) == code, "source_identity", "runtime source changed")
        _source_self(source_sha256, progress)
        _need(_checker_identity(root, authority, progress) == checker_snapshot,
              "checker_identity", "checker changed after read-only snapshot")
        progress.tick("PASS", force=True)
        return {
            "scope": "accepted_proof_unchanged_bytes_and_catalog", "status": "PASS",
            "candidate_sha256": authority.candidate, "publication_sha256": authority.publication,
            "proof_sha256": authority.proof, "checker_source_sha256": authority.checker,
            "source_sha256": source_sha256, "source_commit": authority.source_commit,
            "nautilus_version_from_accepted_proof": authority.nautilus,
            "counts": counts, "resources": resource, "catalog_snapshot": read_snapshot,
            "reused_accepted_row_value_evidence": True,
            "fresh_physical_hash_and_footer_authentication": True,
            "new_logical_row_or_nautilus_run": False,
            "elapsed_seconds": round(time.monotonic() - progress.began, 3),
        }
    finally:
        if owned:
            catalog.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reconcile_cex002_admitted_release")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args(argv)
    try:
        result = reconcile(args.repo, args.catalog, args.source_sha)
        print(_json(result), flush=True)
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(_json({"stage": "FAILED", "error_type": type(exc).__name__,
                     "blocker": getattr(exc, "blocker", "unexpected_error"),
                     "error": str(exc)}), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
