"""Tiny admitted-release fixtures for accepted-proof reconciliation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.catalog.dataset.cex002_reference_release import (
    BITMEX_FALSE_AUTHORITY_TARGETS,
    BUNDLE_ROOT_RELATIVE,
    CODE_PATHS,
    OPERATING_RESERVE_BYTES,
    QUARANTINE_MARKER,
    ReferenceDatasetPlan,
    ReferenceFile,
    ReleaseError,
    prepare_release,
    production_release_policy,
    publish_release,
    read_release,
    reference_proof_component,
    seal_code_identity,
)
from cryptofactors.catalog.dataset.errors import UnsafePathError
from cryptofactors.catalog.runner import apply_migrations
from scripts.research import reconcile_cex002_admitted_release as audit

COMMIT = "a" * 40
CHECKER = "b" * 64
NAUTILUS = "test-nautilus"
CONFIG = "e" * 64
PRODUCTS = (
    "binance_usdm_perpetual_membership", "binance_usdm_bar_1h",
    "binance_usdm_trade_flow_1h", "binance_usdm_open_interest_5m",
    "binance_usdm_funding_realized", "binance_usdm_funding_indicative_1h",
    "binance_usdm_mark_index_basis_1h", "binance_usdm_liquidation_observed_daily",
    "binance_usdm_cost_calibration", "binance_usdm_coverage_gap",
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _put(root: Path, relative: str, payload: bytes) -> tuple[str, int]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return _sha(payload), len(payload)


def _parquet(symbol: str = "BTCUSDT") -> bytes:
    table = pa.table({"native_symbol": pa.array([symbol], type=pa.dictionary(pa.int32(), pa.string()))})
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, compression="zstd", version="2.6", store_schema=True)
    return sink.getvalue().to_pybytes()


def _seed_bitmex(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        for target in BITMEX_FALSE_AUTHORITY_TARGETS:
            connection.execute(
                """INSERT INTO dataset (
                    dataset_id,dataset_type,schema_version,schema_fingerprint,manifest_sha256,
                    manifest_uri,publication_uri,transform_name,transform_version,code_commit,
                    config_sha256,row_count,byte_size,quality_status,quality_summary_json,
                    publication_status,created_at
                ) VALUES (?,?,'1',?,?,?,NULL,'bitmex_quarantine','1',?,?,?,?,'REJECTED',?,'REGISTERED',?)""",
                (target.dataset_id, target.dataset_type, "f" * 64, target.manifest_sha256,
                 f"bitmex/manifests/{target.dataset_id}.json", COMMIT, CONFIG, target.rows,
                 target.byte_size, json.dumps({"quarantine_marker": QUARANTINE_MARKER},
                                              sort_keys=True, separators=(",", ":")), target.created_at),
            )
            connection.execute(
                "INSERT INTO dataset_file (dataset_id,storage_uri,file_sha256,byte_size,row_count,partition_json) VALUES (?,?,?,?,?,'{}')",
                (target.dataset_id, target.relative_path, target.file_sha256, target.byte_size, target.rows),
            )
        connection.commit()
    finally:
        connection.close()


def _anchors(catalog_path: Path) -> dict[str, tuple[int, str]]:
    """Independently reproduce Review519's column-header and row serialization."""
    connection = sqlite3.connect(catalog_path)
    try:
        selected = "SELECT dataset_id FROM dataset WHERE transform_name='cex002_reference_publication'"
        queries = {
            "dataset": "SELECT * FROM dataset WHERE transform_name='cex002_reference_publication' ORDER BY dataset_id",
            "dataset_file": f"SELECT * FROM dataset_file WHERE dataset_id IN ({selected}) ORDER BY dataset_id, storage_uri",
            "dataset_input_dataset": f"SELECT * FROM dataset_input_dataset WHERE dataset_id IN ({selected}) ORDER BY dataset_id, input_dataset_id, role",
            "dataset_input_raw_object": f"SELECT * FROM dataset_input_raw_object WHERE dataset_id IN ({selected}) ORDER BY dataset_id, raw_object_id, role",
        }
        result = {}
        review519_separator = bytes((10,))  # accepted Record521 oracle binds a newline byte
        for name, sql in queries.items():
            cursor = connection.execute(sql)
            digest = hashlib.sha256()
            digest.update(json.dumps([d[0] for d in cursor.description],
                                     separators=(",", ":")).encode() + review519_separator)
            count = 0
            for row in cursor:
                digest.update(json.dumps(row, default=str, separators=(",", ":"),
                                         ensure_ascii=False).encode() + review519_separator)
                count += 1
            result[name] = (count, digest.hexdigest())
        return result
    finally:
        connection.close()


def _quarantine_sha(catalog_path: Path) -> str:
    connection = sqlite3.connect(catalog_path)
    try:
        rows = connection.execute(
            "SELECT dataset_id, quality_status, publication_status, quality_summary_json "
            "FROM dataset WHERE quality_summary_json LIKE '%cex002_bitmex_false_authority%' "
            "ORDER BY dataset_id"
        ).fetchall()
        assert len(rows) == 5
        return _sha(json.dumps(rows, default=str, separators=(",", ":"), ensure_ascii=False).encode())
    finally:
        connection.close()


def _ready(tmp_path: Path) -> tuple[Path, Path, audit._Authority, str, object]:
    root = tmp_path / "repo"
    root.mkdir()
    catalog_path = tmp_path / "catalog.sqlite"
    apply_migrations(catalog_path, Path(__file__).resolve().parents[1] / "sql/migrations")
    _seed_bitmex(catalog_path)
    code = seal_code_identity(
        root, COMMIT, bind_runtime=False,
        file_bytes={name: f"source-{index}".encode() for index, name in enumerate(CODE_PATHS)},
    )
    policy = replace(production_release_policy(root, catalog_path, code),
                     observed_free_bytes=OPERATING_RESERVE_BYTES + 10_000_000_000)
    plans: list[ReferenceDatasetPlan] = []
    for product in PRODUCTS:
        relative = f"data/fixture/{product}.json"
        digest, size = _put(root, relative, (product + "\n").encode())
        plans.append(ReferenceDatasetPlan(product, CONFIG,
                                          (ReferenceFile(relative, digest, 0, size,
                                                         {"role": "metadata"}, False),),
                                          {"fixture": True, "product": product}))
    table_bytes = _parquet()
    digest = _sha(table_bytes)
    relative = f"{BUNDLE_ROOT_RELATIVE}/.objects/aa/{digest}"
    _put(root, relative, table_bytes)
    fields = tuple((field.name, str(field.type), bool(field.nullable))
                   for field in pq.ParquetFile(pa.BufferReader(table_bytes)).schema_arrow)
    plans.append(ReferenceDatasetPlan(
        "binance_usdm_harmonic_bundle", CONFIG,
        (ReferenceFile(relative, digest, 1, len(table_bytes), {"role": "harmonic_bundle"}, True, fields),),
        {"fixture": True, "product": "binance_usdm_harmonic_bundle"}, PRODUCTS,
    ))
    prepared = prepare_release(tuple(plans), policy, config_sha256=CONFIG, authorities={"fixture": True})
    checker = tmp_path / "checker.py"
    checker.write_bytes(b"accepted-checker\n")
    checker_sha = _sha(checker.read_bytes())
    entries = []
    for manifest in prepared.manifests:
        components = [reference_proof_component(root / spec.relative_path, spec.relative_path,
                                                spec.partition["kind"]) for spec in manifest.files]
        entries.append({"dataset_id": manifest.dataset_id, "components": components})
    proof = (json.dumps({
        "document_type": "cex002_harmonic_bundle_consumer_proof", "schema_version": 1,
        "status": "PASS", "scope": "complete_release",
        "candidate_sha256": prepared.descriptor_sha256,
        "checker_source_sha256": checker_sha, "nautilus_version": NAUTILUS,
        "datasets": entries,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()
    published = publish_release(policy, prepared.descriptor_sha256, proof,
                                proof_sha256=_sha(proof), checker_sha256=checker_sha,
                                nautilus_version=NAUTILUS)
    authority = audit._Authority(
        candidate=prepared.descriptor_sha256, publication=published.publication_sha256,
        proof=_sha(proof), proof_bytes=len(proof), checker=checker_sha, nautilus=NAUTILUS,
        source_commit=COMMIT, datasets=11, files=11, tables=1, metadata=10, rows=1,
        anchors=_anchors(catalog_path), quarantine_sha256=_quarantine_sha(catalog_path),
        code=code, checker_path=checker,
        observed_free_bytes=OPERATING_RESERVE_BYTES + 10_000_000_000,
    )
    source_sha = _sha(Path(audit.__file__).read_bytes())
    return root, catalog_path, authority, source_sha, prepared


def _counts(path: Path) -> tuple[int, int]:
    connection = sqlite3.connect(path)
    try:
        return (connection.execute("SELECT count(*) FROM dataset").fetchone()[0],
                connection.execute("SELECT count(*) FROM dataset_file").fetchone()[0])
    finally:
        connection.close()


def test_admitted_identical_replay_and_independent_reader_do_not_decode_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, catalog, authority, source_sha, prepared = _ready(tmp_path)
    initial = _anchors(catalog)
    counts = _counts(catalog)
    import cryptofactors.catalog.dataset.cex002_reference_release as original

    monkeypatch.setattr(original, "reference_proof_component",
                        lambda *_args, **_kwargs: pytest.fail("new reconciliation decoded rows"))
    monkeypatch.setattr(pq, "read_table",
                        lambda *_args, **_kwargs: pytest.fail("new reconciliation read a logical table"))
    monkeypatch.setattr(pq.ParquetFile, "iter_batches",
                        lambda *_args, **_kwargs: pytest.fail("new reconciliation iterated logical rows"))
    result = audit.reconcile(root, catalog, source_sha, _fixture=authority)
    assert result["status"] == "PASS"
    assert result["scope"] == "accepted_proof_unchanged_bytes_and_catalog"
    assert result["new_logical_row_or_nautilus_run"] is False
    assert result["catalog_snapshot"]["dataset_file"]["sha256"] == initial["dataset_file"][1]
    assert _anchors(catalog) == initial and _counts(catalog) == counts
    # Generic reader remains unchanged and its ordinary proof verifier still works.
    monkeypatch.undo()
    proof = (root / BUNDLE_ROOT_RELATIVE / ".proofs" / f"{authority.proof}.json").read_bytes()
    visible = read_release(
        replace(production_release_policy(root, catalog, authority.code),
                observed_free_bytes=OPERATING_RESERVE_BYTES + 10_000_000_000),
        authority.publication, proof, proof_sha256=authority.proof,
        checker_sha256=authority.checker, nautilus_version=authority.nautilus,
    )
    assert visible.consumable and visible.dataset_ids["binance_usdm_harmonic_bundle"] == prepared.dataset_ids["binance_usdm_harmonic_bundle"]


@pytest.mark.parametrize("change", ["source_bytes", "proof_bytes", "checker_bytes", "publication_bytes",
                                         "source_symlink", "unsafe_parent", "catalog_bookkeeping", "catalog_file",
                                         "catalog_extra", "quarantine", "anchor", "candidate_pin"])
def test_changed_authority_or_catalog_refuses_without_rows(tmp_path: Path, change: str) -> None:
    root, catalog, authority, source_sha, prepared = _ready(tmp_path)
    target = root / prepared.manifests[-1].files[0].relative_path
    proof_path = root / BUNDLE_ROOT_RELATIVE / ".proofs" / f"{authority.proof}.json"
    publication_path = root / BUNDLE_ROOT_RELATIVE / ".publication" / f"{authority.publication}.json"
    if change == "source_bytes":
        altered = _parquet("ETHUSDT")  # same footer schema and row count, different values
        target.write_bytes(altered)
    elif change == "proof_bytes":
        proof_path.write_bytes(proof_path.read_bytes() + b" ")
    elif change == "checker_bytes":
        assert authority.checker_path is not None
        authority.checker_path.write_bytes(b"changed\n")
    elif change == "publication_bytes":
        publication_path.write_bytes(publication_path.read_bytes() + b" ")
    elif change == "source_symlink":
        other = tmp_path / "replacement"
        target.replace(other)
        target.symlink_to(other)
    elif change == "unsafe_parent":
        parent = target.parent
        other = tmp_path / "objects"
        parent.replace(other)
        parent.symlink_to(other, target_is_directory=True)
    elif change.startswith("catalog_") or change == "quarantine":
        connection = sqlite3.connect(catalog)
        try:
            if change == "catalog_bookkeeping":
                connection.execute("UPDATE dataset SET created_at='2020-01-01' WHERE dataset_id=?",
                                   (prepared.manifests[0].dataset_id,))
            elif change == "catalog_file":
                connection.execute("DELETE FROM dataset_file WHERE dataset_id=?",
                                   (prepared.manifests[0].dataset_id,))
            elif change == "catalog_extra":
                connection.execute("UPDATE dataset SET transform_name='other' WHERE dataset_id=?",
                                   (prepared.manifests[0].dataset_id,))
            elif change == "quarantine":
                connection.execute("UPDATE dataset SET quality_status='PASS' WHERE dataset_id=?",
                                   (BITMEX_FALSE_AUTHORITY_TARGETS[0].dataset_id,))
            connection.commit()
        finally:
            connection.close()
    elif change == "anchor":
        authority = replace(authority, anchors={**authority.anchors, "dataset": (11, "0" * 64)})
    elif change == "candidate_pin":
        authority = replace(authority, candidate="0" * 64)
    before = _counts(catalog)
    expected_error = (UnsafePathError,) if change == "candidate_pin" else (
        audit.ReconciliationError, ReleaseError, OSError, ValueError
    )
    with pytest.raises(expected_error):
        audit.reconcile(root, catalog, source_sha, _fixture=authority)
    assert _counts(catalog) == before


def test_pending_and_foreign_connections_are_rejected_without_touching_caller_work(tmp_path: Path) -> None:
    root, catalog, authority, source_sha, _prepared = _ready(tmp_path)
    held = sqlite3.connect(catalog)
    try:
        held.execute("BEGIN")
        held.execute("CREATE TABLE sentinel (value TEXT)")
        held.execute("INSERT INTO sentinel VALUES ('pending')")
        with pytest.raises(ReleaseError) as pending:
            audit.reconcile(root, catalog, source_sha, connection=held, _fixture=authority)
        assert pending.value.blocker == "pending_catalog_transaction"
        assert held.execute("SELECT value FROM sentinel").fetchone() == ("pending",)
        held.rollback()
    finally:
        held.close()
    foreign = tmp_path / "foreign.sqlite"
    sqlite3.connect(foreign).close()
    other = sqlite3.connect(foreign, isolation_level=None)
    try:
        with pytest.raises(ReleaseError) as refused:
            audit.reconcile(root, catalog, source_sha, connection=other, _fixture=authority)
        assert refused.value.blocker == "unsafe_path"
    finally:
        other.close()


def test_reserve_fails_before_source_traversal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, catalog, authority, source_sha, _prepared = _ready(tmp_path)
    authority = replace(authority, observed_free_bytes=OPERATING_RESERVE_BYTES - 1)
    monkeypatch.setattr(audit, "_proof_and_files", lambda *_args: pytest.fail("source traversal began"))
    with pytest.raises(ReleaseError) as refused:
        audit.reconcile(root, catalog, source_sha, _fixture=authority)
    assert refused.value.blocker == "operating_reserve_not_preserved"


@pytest.mark.parametrize("bound", ["proof", "publication"])
def test_metadata_read_caps_fail_before_physical_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bound: str,
) -> None:
    root, catalog, authority, source_sha, _prepared = _ready(tmp_path)
    if bound == "proof":
        monkeypatch.setattr(audit, "PROOF_MAX_BYTES", 1)
    else:
        monkeypatch.setattr(audit, "PREPARED_MAX_BYTES", 1)
    monkeypatch.setattr(audit, "_proof_and_files", lambda *_args: pytest.fail("physical traversal began"))
    with pytest.raises(ReleaseError) as refused:
        audit.reconcile(root, catalog, source_sha, _fixture=authority)
    assert refused.value.blocker == "metadata_bound"


def test_late_source_replacement_and_deadline_refuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, catalog, authority, source_sha, prepared = _ready(tmp_path)
    prior = audit._recheck
    target = root / prepared.manifests[-1].files[0].relative_path

    def changed(root_arg: Path, snapshots: object, progress: object) -> None:
        target.write_bytes(target.read_bytes() + b"x")
        prior(root_arg, snapshots, progress)

    monkeypatch.setattr(audit, "_recheck", changed)
    before = _anchors(catalog)
    with pytest.raises(audit.ReconciliationError) as refused:
        audit.reconcile(root, catalog, source_sha, _fixture=authority)
    assert refused.value.blocker == "input_changed" and _anchors(catalog) == before
    monkeypatch.undo()
    with pytest.raises(audit.ReconciliationError) as deadline:
        audit.reconcile(root, catalog, source_sha, _fixture=authority, _deadline_seconds=-1)
    assert deadline.value.blocker == "deadline"


@pytest.mark.parametrize("which", ["publication", "proof"])
def test_metadata_replacement_between_parse_and_snapshot_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: str,
) -> None:
    root, catalog, authority, source_sha, _prepared = _ready(tmp_path)
    relative = (f"{BUNDLE_ROOT_RELATIVE}/.publication/{authority.publication}.json" if which == "publication"
                else f"{BUNDLE_ROOT_RELATIVE}/.proofs/{authority.proof}.json")
    original = audit._hash_bound
    changed = False

    def switch(root_arg: Path, name: str, progress: object) -> object:
        nonlocal changed
        if name == relative and not changed:
            changed = True
            path = root_arg / name
            path.write_bytes(path.read_bytes() + b" ")
        return original(root_arg, name, progress)

    monkeypatch.setattr(audit, "_hash_bound", switch)
    baseline = _anchors(catalog)
    with pytest.raises(audit.ReconciliationError) as refused:
        audit.reconcile(root, catalog, source_sha, _fixture=authority)
    assert refused.value.blocker == ("publication_identity" if which == "publication" else "proof_identity")
    assert _anchors(catalog) == baseline


def test_proof_component_paths_and_bar_routing_are_strict(tmp_path: Path) -> None:
    root, catalog, authority, _source_sha, prepared = _ready(tmp_path)
    proof_path = root / BUNDLE_ROOT_RELATIVE / ".proofs" / f"{authority.proof}.json"
    proof = json.loads(proof_path.read_bytes())
    proof["datasets"][0]["components"].append(proof["datasets"][0]["components"][0])
    progress = audit._Progress(60)
    with pytest.raises(audit.ReconciliationError) as duplicate:
        audit._proof_and_files(root, prepared.manifests, proof, authority, progress)
    assert duplicate.value.blocker == "proof_contract"
    spec = prepared.manifests[-1].files[0]
    component = reference_proof_component(root / spec.relative_path, spec.relative_path, "table")
    schema = pq.ParquetFile(root / spec.relative_path).schema_arrow
    bar = replace(prepared.manifests[1], dataset_type="binance_usdm_bar_1h")
    with pytest.raises(audit.ReconciliationError):
        audit._component_shape(component, spec, bar, schema)
    assert _counts(catalog) == (16, 16)


@pytest.mark.parametrize("forbidden", ["--proof-sha", "--candidate-sha", "--fixture"])
def test_cli_has_no_pin_or_fixture_overrides(
    monkeypatch: pytest.MonkeyPatch, forbidden: str,
) -> None:
    monkeypatch.setattr(audit, "reconcile", lambda *_args, **_kwargs: pytest.fail("CLI reached audit"))
    with pytest.raises(SystemExit) as refused:
        audit.main(["--repo", "/unused", "--catalog", "/unused/catalog.sqlite",
                    "--source-sha", "0" * 64, forbidden, "arbitrary"])
    assert refused.value.code == 2


def test_review519_serialization_oracle_for_empty_raw_edges(tmp_path: Path) -> None:
    _root, catalog, _authority, _source_sha, _prepared = _ready(tmp_path)
    assert _anchors(catalog)["dataset_input_raw_object"] == (
        0, "6a8d487a15f8d0927d64f2c03491325ce88b37d29ed7402743c05bd67f210de3"
    )
