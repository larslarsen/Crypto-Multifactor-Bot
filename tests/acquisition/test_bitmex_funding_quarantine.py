"""CEX-002 Gate-0 source contract on canonical, isolated catalog/store fixtures."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.acquisition import bitmex_funding_quarantine as q
from cryptofactors.catalog.dataset.canonicalize import (
    compute_dataset_id,
    compute_manifest_sha256,
    dumps_canonical,
    full_manifest_dict,
    identity_from_manifest_dict,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.errors import DatasetQuarantineError, QuarantineReportError
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetManifest,
    DatasetStatistics,
    OutputFileSpec,
    PublicationMetadata,
    QualityStatus,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.catalog.dataset.parse import load_manifest_bytes
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir, dataset_relative_dir
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations

# The public historical eight-column schema. No dependency on pending edits to
# the BitMEX normalizer, and no change of float rates or unknown availability.
FIXTURE_SCHEMA = pa.schema([
    ("timestamp", pa.string()), ("timestamp_us", pa.int64()), ("symbol", pa.string()),
    ("funding_rate", pa.float64()), ("funding_rate_daily", pa.float64()),
    ("funding_interval", pa.string()), ("source", pa.string()),
    ("availability_time", pa.int64()),
])
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 10, 16, tzinfo=UTC)


def _seed(root: Path, db: Path, number: int, *, rates: list[float | None] | None = None,
          intervals: list[str | None] | None = None, declared_rows: int | None = None,
          expected_symbols: int = 2, missing_column: str | None = None,
          wrong_rate_type: bool = False) -> q.BitmexFalseAuthorityTarget:
    rates = rates if rates is not None else [0.0] * 6
    rows = len(rates)
    table = pa.Table.from_pydict({
        "timestamp": ["2020-01-01T00:00:00Z"] * rows,
        "timestamp_us": list(range(rows)),
        "symbol": ["XBTUSD" if i % 2 else "ETHUSD" for i in range(rows)],
        "funding_rate": rates, "funding_rate_daily": [0.0] * rows,
        "funding_interval": intervals if intervals is not None else [""] * rows,
        "source": ["bitmex_funding"] * rows, "availability_time": [None] * rows,
    }, schema=FIXTURE_SCHEMA)
    if missing_column:
        table = table.drop([missing_column])
    if wrong_rate_type:
        index = table.schema.get_field_index("funding_rate")
        table = table.set_column(index, "funding_rate", pa.array(["0"] * rows))
    staging = root / f"input-{number}.parquet"
    pq.write_table(table, staging)
    raw = staging.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    count = declared_rows if declared_rows is not None else rows
    dtype = "bitmex_funding_full" if number == 4 else "bitmex_funding"
    rel = "bitmex/funding_full/funding.parquet" if number == 4 else "bitmex/funding/funding.parquet"
    manifest = DatasetManifest(
        dataset_id="ds_" + "0" * 64, dataset_type=dtype,
        schema=SchemaIdentity("bitmex_funding", "1", "fund_v1"),
        transform=TransformSpec("fixture_backfill", "1"), code=CodeIdentity(f"fixture-{number}"),
        config=ConfigIdentity("a" * 64), dependencies=(),
        files=(OutputFileSpec(rel, sha, count, len(raw), {"source": "bitmex"}),),
        statistics=DatasetStatistics(count, len(raw)), coverage=CoverageWindow(EPOCH, NOW),
        quality_status=QualityStatus.PASS, quality_summary={"record_count": count},
        publication=PublicationMetadata(EPOCH),
    )
    dataset_id, _ = compute_dataset_id(identity_from_manifest_dict(full_manifest_dict(manifest)))
    manifest = replace(manifest, dataset_id=dataset_id)
    manifest = replace(manifest, manifest_sha256=compute_manifest_sha256(manifest))
    manifest_raw = (dumps_canonical(full_manifest_dict(manifest)) + "\n").encode()
    # This is the real strict parser, not a mocked ID/hash authorization shortcut.
    assert load_manifest_bytes(manifest_raw) == manifest
    store = root / "store"
    directory = dataset_absolute_dir(store, dataset_id)
    (directory / rel).parent.mkdir(parents=True)
    (directory / rel).write_bytes(raw)
    (directory / "manifest.json").write_bytes(manifest_raw)
    relative_dir = dataset_relative_dir(dataset_id).as_posix()
    # Intentionally unlike publication time: preserve catalog registration time.
    registered_at = NOW.isoformat()
    dataset = {
        "dataset_id": dataset_id, "dataset_type": dtype, "schema_version": "1",
        "schema_fingerprint": "fund_v1", "manifest_sha256": manifest.manifest_sha256,
        "manifest_uri": relative_dir + "/manifest.json", "publication_uri": relative_dir,
        "transform_name": "fixture_backfill", "transform_version": "1",
        "code_commit": f"fixture-{number}", "config_sha256": "a" * 64,
        "row_count": count, "byte_size": len(raw), "event_start": EPOCH.isoformat(),
        "event_end": NOW.isoformat(), "availability_start": None, "availability_end": None,
        "quality_status": "PASS", "quality_summary_json": dumps_canonical(manifest.quality_summary),
        "supersedes_dataset_id": None, "publication_status": "REGISTERED", "created_at": registered_at,
    }
    with sqlite3.connect(db) as conn:
        columns = ",".join(dataset)
        marks = ",".join("?" for _ in dataset)
        conn.execute(f"INSERT INTO dataset ({columns}) VALUES ({marks})", tuple(dataset.values()))
        conn.execute("""INSERT INTO dataset_file
                     (dataset_id,storage_uri,file_sha256,row_count,byte_size,partition_json)
                     VALUES (?,?,?,?,?,?)""",
                     (dataset_id, rel, sha, count, len(raw), '{"source":"bitmex"}'))
    return q.BitmexFalseAuthorityTarget(dataset_id, dtype, count, expected_symbols, rel, sha,
                                      len(raw), manifest.manifest_sha256,
                                      hashlib.sha256(manifest_raw).hexdigest(), registered_at)


@pytest.fixture
def environment(tmp_path: Path):
    db = tmp_path / "catalog.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    targets = tuple(_seed(tmp_path, db, i) for i in range(5))
    cat = SqliteDatasetCatalog(db)
    try:
        yield tmp_path, db, cat, targets
    finally:
        cat.close()


def _run(environment, **kwargs):
    root, _, cat, targets = environment
    return q.execute_fixture_quarantine(cat, root / "store", targets=targets, **kwargs)


def _rows(environment) -> list[dict[str, Any]]:
    _, _, cat, targets = environment
    return [dict(cat.get_dataset(t.dataset_id) or {}) for t in targets]


def _files(environment) -> list[list[dict[str, Any]]]:
    _, _, cat, targets = environment
    return [list(cat.list_files(t.dataset_id)) for t in targets]


def _mutate(environment, sql: str, *parameters: Any) -> None:
    _, db, _, _ = environment
    with sqlite3.connect(db) as conn:
        conn.execute(sql, parameters)


def _path(environment, target_number: int = 0, *, manifest: bool = False) -> Path:
    root, _, _, targets = environment
    target = targets[target_number]
    return dataset_absolute_dir(root / "store", target.dataset_id) / (
        "manifest.json" if manifest else target.relative_path)


def _cli():
    script = Path(__file__).parents[2] / "scripts/research/quarantine_bitmex_funding.py"
    spec = importlib.util.spec_from_file_location("quarantine_cli_for_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pinned_production_authorities_and_no_override() -> None:
    targets = q.BITMEX_FALSE_AUTHORITY_TARGETS
    assert q.exact_false_authority_ids() == (
        "ds_4f82fede83f446e3ca29522e6e5f5a0ad7fb6d03d8931f1300addfe413364933",
        "ds_f61c69342932c78c370b7950faf46d3e78be3695dbde8e6077acf8ccfa115deb",
        "ds_11b6665e7dcd37cb85c0098f60681a252801bbc4f80cb053eccc0fa0ce3679ea",
        "ds_ab70ebd21268fe47cbde63b266c0b6f41d0e2ca529d319e3f6f0aa5a5646f512",
        "ds_ee8e9cd9ddd4de87a0c68ef0ff9b4a0da6c6bd7692c96b9f29f8cca13daf46c8",
    )
    assert sum(t.expected_rows for t in targets) == 307_738
    assert [t.expected_symbols for t in targets] == [2, 5, 5, 5, 45]
    assert len({t.manifest_sha256 for t in targets}) == 5
    assert all(t.manifest_sha256 != t.manifest_file_sha256 for t in targets)
    assert targets[2].catalog_created_at == "2026-07-24T01:32:06.704813+00:00"
    import inspect
    assert "targets" not in inspect.signature(q.execute_bitmex_funding_quarantine).parameters


def test_transaction_replay_full_snapshots_original_evidence_and_preserved_bytes(environment) -> None:
    root, db, cat, targets = environment
    rows_before, files_before = _rows(environment), _files(environment)
    bytes_before = {p: p.read_bytes() for p in (root / "store").rglob("*") if p.is_file()}
    report = _run(environment, now=NOW)
    assert report.applied and report.disposition == "applied" and report.artifacts_unchanged
    assert set(report.pre_resolver.eligible_targets) == {t.dataset_id for t in targets}
    assert report.post_resolver.eligible_targets == ()
    assert all(v is None for v in report.post_resolver.latest.values())
    for before, after, item in zip(rows_before, _rows(environment), report.inspections_post, strict=True):
        summary = json.loads(after["quality_summary_json"])
        assert summary["quarantine_ticket"] == "CEX-002"
        assert summary["quarantine_marker"] == q.QUARANTINE_MARKER
        assert summary["pre_quality_summary_json"] == before["quality_summary_json"]
        assert summary["pre_quality_summary"] == json.loads(before["quality_summary_json"])
        assert after == before | {"quality_status": "REJECTED", "quality_summary_json": after["quality_summary_json"]}
        assert item.manifest_quality_status == "PASS"
        assert item.manifest_created_at == EPOCH.isoformat()
        assert after["created_at"] != item.manifest_created_at
        assert not cat.is_consumable(item.dataset_id)
    rows_applied = _rows(environment)
    replay = _run(environment, now=datetime(2027, 1, 1, tzinfo=UTC))
    assert not replay.applied and replay.idempotent_replay and replay.disposition == "replayed"
    assert replay.inspections_pre == replay.inspections_post
    assert _rows(environment) == rows_applied
    assert _files(environment) == files_before
    assert {p: p.read_bytes() for p in bytes_before} == bytes_before
    assert report.database_path == str(db)


@pytest.mark.parametrize("replay", [False, True])
@pytest.mark.parametrize("column,value", [
    ("dataset_type", "wrong_type"), ("schema_version", "9"), ("schema_fingerprint", "wrong"),
    ("manifest_sha256", "0" * 64), ("manifest_uri", "../manifest.json"),
    ("publication_uri", "wrong"), ("transform_name", "other"), ("transform_version", "9"),
    ("code_commit", "other"), ("config_sha256", "0" * 64),
    ("row_count", 7), ("byte_size", 123), ("event_start", None),
    ("event_end", None), ("availability_start", NOW.isoformat()),
    ("availability_end", NOW.isoformat()), ("publication_status", "SUPERSEDED"),
    ("created_at", EPOCH.isoformat()), ("quality_summary_json", "{}"),
    ("quality_status", "PASS_WITH_WARNINGS"), ("quality_status", "QUARANTINED"),
])
def test_changed_catalog_identity_refused_on_first_and_replay(environment, replay, column, value) -> None:
    if replay:
        _run(environment)
    dataset_id = environment[3][0].dataset_id
    _mutate(environment, f"UPDATE dataset SET {column}=? WHERE dataset_id=?", value, dataset_id)
    rows_before = _rows(environment)
    with pytest.raises(DatasetQuarantineError):
        _run(environment)
    assert _rows(environment) == rows_before


@pytest.mark.parametrize("replay", [False, True])
@pytest.mark.parametrize("column,value", [
    ("file_sha256", "0" * 64), ("row_count", 8), ("byte_size", 12),
    ("partition_json", "{}"), ("storage_uri", "../escape.parquet"),
])
def test_changed_catalog_file_identity_refused(environment, replay, column, value) -> None:
    if replay:
        _run(environment)
    _mutate(environment, f"UPDATE dataset_file SET {column}=? WHERE dataset_id=?",
            value, environment[3][0].dataset_id)
    rows_before, files_before = _rows(environment), _files(environment)
    with pytest.raises(DatasetQuarantineError, match="file identity"):
        _run(environment)
    assert _rows(environment) == rows_before
    assert _files(environment) == files_before


@pytest.mark.parametrize("replay", [False, True])
@pytest.mark.parametrize("manifest", [False, True])
@pytest.mark.parametrize("alteration", ["missing", "changed", "symlink"])
def test_authenticate_every_physical_artifact_on_replay(environment, replay, manifest, alteration) -> None:
    if replay:
        _run(environment)
    path = _path(environment, manifest=manifest)
    rows_before = _rows(environment)
    if alteration == "missing":
        path.unlink()
    elif alteration == "changed":
        path.write_bytes(path.read_bytes() + b" ")
    else:
        backup = environment[0] / "artifact-copy"
        backup.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(backup)
    with pytest.raises(DatasetQuarantineError):
        _run(environment)
    assert _rows(environment) == rows_before


@pytest.mark.parametrize("replay", [False, True])
def test_extra_file_rows_and_extra_physical_artifacts_fail(environment, replay) -> None:
    if replay:
        _run(environment)
    target = environment[3][0]
    _mutate(environment, "INSERT INTO dataset_file VALUES (?,?,?,?,?,?)",
            target.dataset_id, "extra.parquet", "1" * 64, 1, 1, "{}")
    rows_before = _rows(environment)
    with pytest.raises(DatasetQuarantineError, match="file identity"):
        _run(environment)
    _mutate(environment, "DELETE FROM dataset_file WHERE storage_uri='extra.parquet'")
    extra = _path(environment, manifest=True).parent / "extra.parquet"
    extra.write_bytes(b"extra")
    with pytest.raises(DatasetQuarantineError, match="tree artifacts"):
        _run(environment)
    assert _rows(environment) == rows_before


def test_missing_catalog_target_and_file_fail(environment) -> None:
    target = environment[3][0]
    _mutate(environment, "DELETE FROM dataset_file WHERE dataset_id=?", target.dataset_id)
    rows_before = _rows(environment)
    with pytest.raises(DatasetQuarantineError, match="file identity"):
        _run(environment)
    _mutate(environment, "DELETE FROM dataset WHERE dataset_id=?", target.dataset_id)
    with pytest.raises(DatasetQuarantineError, match="not registered"):
        _run(environment)
    assert _rows(environment)[1:] == rows_before[1:]


@pytest.mark.parametrize("options,expected", [
    ({"rates": [0.0, None, 0.0, 0.0, 0.0, 0.0]}, "null funding"),
    ({"rates": [0.0, 0.01, 0.0, 0.0, 0.0, 0.0]}, "nonzero funding"),
    ({"rates": [float("nan")] * 6}, "nonzero funding"),
    ({"rates": [float("inf")] * 6}, "nonzero funding"),
    ({"intervals": ["08:00"] * 6}, "nonempty funding"),
    ({"declared_rows": 7}, "economic row count"),
    ({"expected_symbols": 3}, "economic symbol count"),
    ({"missing_column": "funding_rate"}, "column missing"),
    ({"missing_column": "funding_interval"}, "column missing"),
    ({"missing_column": "symbol"}, "column missing"),
    ({"wrong_rate_type": True}, "column type"),
])
@pytest.mark.parametrize("replay", [False, True])
def test_real_authenticated_parquet_economic_failures(tmp_path, options, expected, replay) -> None:
    db = tmp_path / "catalog.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    targets = tuple(_seed(tmp_path, db, i, **(options if i == 0 else {})) for i in range(5))
    cat = SqliteDatasetCatalog(db)
    environment = (tmp_path, db, cat, targets)
    try:
        if replay:
            # Construct a complete, correctly marked prior catalog state over
            # real, authenticated but economically invalid artifacts. Replay
            # must independently inspect those artifacts, not trust the marker.
            for target in targets:
                prior = json.loads(cat.get_dataset(target.dataset_id)["quality_summary_json"])
                summary = q._quarantine_summary(prior, NOW.isoformat())
                _mutate(environment, "UPDATE dataset SET quality_status='REJECTED', "
                        "quality_summary_json=? WHERE dataset_id=?",
                        dumps_canonical(summary), target.dataset_id)
        before = _rows(environment)
        with pytest.raises(DatasetQuarantineError, match=expected):
            _run(environment)
        assert _rows(environment) == before
    finally:
        cat.close()


def test_strict_parser_recomputes_identity_even_if_physical_hash_repinned(environment) -> None:
    path = _path(environment, manifest=True)
    content = json.loads(path.read_bytes())
    content["code_commit"] = "tampered"
    content["code"]["commit"] = "tampered"
    raw = (json.dumps(content, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(raw)
    targets = (replace(environment[3][0], manifest_file_sha256=hashlib.sha256(raw).hexdigest()),
               *environment[3][1:])
    with pytest.raises(DatasetQuarantineError, match="authentication"):
        q.execute_fixture_quarantine(environment[2], environment[0] / "store", targets=targets)


def test_canonical_manifest_pin_is_distinct_from_physical_hash(environment) -> None:
    target = replace(environment[3][0], manifest_sha256=environment[3][0].manifest_file_sha256)
    with pytest.raises(DatasetQuarantineError, match="canonical manifest hash"):
        q.execute_fixture_quarantine(environment[2], environment[0] / "store",
                                     targets=(target, *environment[3][1:]))


@pytest.mark.parametrize("change", ["partial", "marker", "ticket", "reason", "prior", "timestamp"])
def test_partial_or_wrong_prior_quarantine_is_never_completed(environment, change) -> None:
    _run(environment)
    target = environment[3][0]
    if change == "partial":
        _mutate(environment, "UPDATE dataset SET quality_status='PASS',quality_summary_json=? WHERE dataset_id=?",
                '{"record_count":6}', target.dataset_id)
    else:
        summary = json.loads(_rows(environment)[0]["quality_summary_json"])
        key = {"marker": "quarantine_marker", "ticket": "quarantine_ticket",
               "reason": "quarantine_reason", "prior": "pre_quality_summary_json",
               "timestamp": "quarantined_at"}[change]
        summary[key] = "wrong"
        _mutate(environment, "UPDATE dataset SET quality_summary_json=? WHERE dataset_id=?",
                json.dumps(summary), target.dataset_id)
    rows_before = _rows(environment)
    with pytest.raises(DatasetQuarantineError):
        _run(environment)
    assert _rows(environment) == rows_before


def test_valid_but_conflicting_prior_operation_timestamp_rejected(environment) -> None:
    _run(environment, now=NOW)
    row = _rows(environment)[0]
    summary = json.loads(row["quality_summary_json"])
    summary["quarantined_at"] = EPOCH.isoformat()
    _mutate(environment, "UPDATE dataset SET quality_summary_json=? WHERE dataset_id=?",
            dumps_canonical(summary), row["dataset_id"])
    with pytest.raises(DatasetQuarantineError, match="conflicting prior"):
        _run(environment)


def test_parent_symlink_and_plan_traversal_rejected(environment) -> None:
    root, _, cat, targets = environment
    linked_store = root / "linked-store"
    linked_store.symlink_to(root / "store", target_is_directory=True)
    with pytest.raises(DatasetQuarantineError, match="authentication"):
        q.execute_fixture_quarantine(cat, linked_store, targets=targets)
    changed = replace(targets[0], relative_path="../funding.parquet")
    with pytest.raises(DatasetQuarantineError):
        q.execute_fixture_quarantine(cat, root / "store", targets=(changed, *targets[1:]))


def test_fixture_api_cannot_select_production_or_partial_plan(environment) -> None:
    root, _, cat, targets = environment
    with pytest.raises(DatasetQuarantineError, match="exactly five"):
        q.execute_fixture_quarantine(cat, root / "store", targets=targets[:1])
    with pytest.raises(DatasetQuarantineError, match="production identities"):
        q.execute_fixture_quarantine(cat, root / "store", targets=q.BITMEX_FALSE_AUTHORITY_TARGETS)


def test_write_lock_precedes_all_authentication(environment, monkeypatch) -> None:
    _, db, cat, targets = environment
    original = q._authenticate
    attempted = []

    def authenticate(*args):
        with sqlite3.connect(db, timeout=0.01) as other:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                other.execute("UPDATE dataset SET created_at='concurrent' WHERE dataset_id=?",
                              (targets[0].dataset_id,))
        attempted.append(True)
        return original(*args)

    monkeypatch.setattr(q, "_authenticate", authenticate)
    assert _run(environment).applied
    assert len(attempted) == 10
    assert not cat._conn.in_transaction


@pytest.mark.parametrize("file_change", [False, True])
def test_same_connection_cas_change_refused_and_rolled_back(environment, monkeypatch, file_change) -> None:
    cat = environment[2]
    before, files_before = _rows(environment), _files(environment)
    original = cat.compare_and_swap_quality_status

    def change(expected, expected_files, **kwargs):
        if file_change:
            cat._conn.execute("UPDATE dataset_file SET partition_json='{}' WHERE dataset_id=?",
                              (expected["dataset_id"],))
        else:
            cat._conn.execute("UPDATE dataset SET created_at='concurrent' WHERE dataset_id=?",
                              (expected["dataset_id"],))
        return original(expected, expected_files, **kwargs)

    monkeypatch.setattr(cat, "compare_and_swap_quality_status", change)
    with pytest.raises(DatasetQuarantineError, match="CAS|compare-and-swap"):
        _run(environment)
    assert _rows(environment) == before
    assert _files(environment) == files_before


def test_failure_after_first_update_rolls_back_every_target(environment, monkeypatch) -> None:
    cat = environment[2]
    before = _rows(environment)
    original = cat.compare_and_swap_quality_status
    calls = []

    def fail_second(*args, **kwargs):
        calls.append(True)
        if len(calls) == 2:
            assert cat.get_dataset(environment[3][0].dataset_id)["quality_status"] == "REJECTED"
            raise ValueError("injected after early update")
        return original(*args, **kwargs)

    monkeypatch.setattr(cat, "compare_and_swap_quality_status", fail_second)
    with pytest.raises(DatasetQuarantineError, match="injected after early update"):
        _run(environment)
    assert len(calls) == 2 and _rows(environment) == before


@pytest.mark.parametrize("trigger_sql", [
    "UPDATE dataset SET created_at='triggered' WHERE dataset_id=NEW.dataset_id;",
    "UPDATE dataset_file SET partition_json='{}' WHERE dataset_id=NEW.dataset_id;",
    "INSERT INTO dataset_file VALUES(NEW.dataset_id,'extra.parquet','extra',1,1,'{}');",
])
def test_trigger_changes_to_immutable_rows_rollback_all_five(environment, trigger_sql) -> None:
    _mutate(environment, "CREATE TRIGGER quarantine_tamper AFTER UPDATE OF quality_status ON dataset "
            "BEGIN " + trigger_sql + " END")
    rows_before, files_before = _rows(environment), _files(environment)
    with pytest.raises(DatasetQuarantineError):
        _run(environment)
    assert _rows(environment) == rows_before
    assert _files(environment) == files_before


def test_before_commit_resolver_postcondition_failure_rolls_back(environment, monkeypatch) -> None:
    before = _rows(environment)
    original = environment[2].is_consumable

    def eligible(dataset_id):
        if environment[2].get_dataset(dataset_id)["quality_status"] == "REJECTED":
            return True
        return original(dataset_id)

    monkeypatch.setattr(environment[2], "is_consumable", eligible)
    with pytest.raises(DatasetQuarantineError, match="remains eligible"):
        _run(environment)
    assert _rows(environment) == before


def test_nested_external_pending_work_is_never_committed_or_rolled_back(environment) -> None:
    root, db, _, targets = environment
    with sqlite3.connect(db) as external:
        external.execute("UPDATE dataset SET code_commit='pending' WHERE dataset_id=?",
                         (targets[0].dataset_id,))
        catalog = SqliteDatasetCatalog(db, connection=external)
        with pytest.raises(DatasetQuarantineError, match="idle connection"):
            q.execute_fixture_quarantine(catalog, root / "store", targets=targets)
        assert external.in_transaction
        assert catalog.get_dataset(targets[0].dataset_id)["code_commit"] == "pending"
        assert environment[2].get_dataset(targets[0].dataset_id)["code_commit"] == "fixture-0"
        catalog.close()  # Externally owned connection stays usable and pending.
        assert external.in_transaction
        external.rollback()
        with catalog.quarantine_transaction():
            with pytest.raises(DatasetQuarantineError, match="idle connection"):
                _run((root, db, catalog, targets))
        assert not external.in_transaction
        assert q.execute_fixture_quarantine(catalog, root / "store", targets=targets).applied


def test_read_only_dry_run_works_without_schema_or_authority_writes(environment) -> None:
    root, db, _, targets = environment
    rows_before, files_before = _rows(environment), _files(environment)
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as connection:
        cat = SqliteDatasetCatalog(db, connection=connection)
        report = q.execute_fixture_quarantine(cat, root / "store", targets=targets, dry_run=True)
        assert report.dry_run and not report.applied and report.disposition == "inspected"
        assert report.pre_resolver == report.post_resolver
        assert report.inspections_pre == report.inspections_post
        assert not connection.in_transaction
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("UPDATE dataset SET quality_status='REJECTED'")
    assert _rows(environment) == rows_before and _files(environment) == files_before


def test_cli_dry_run_uses_real_read_only_existing_catalog_no_migrations(environment, monkeypatch) -> None:
    root, db, _, targets = environment
    cli = _cli()
    seen = []

    def fixture_execute(cat, store, *, dry_run):
        assert dry_run
        assert cat._conn.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            cat._conn.execute("CREATE TABLE forbidden(x)")
        seen.append(True)
        return q.execute_fixture_quarantine(cat, store, targets=targets, dry_run=dry_run)

    monkeypatch.setattr(cli, "execute_bitmex_funding_quarantine", fixture_execute)
    rows_before = _rows(environment)
    report_path = root / "dry-report.json"
    assert cli.main(["--db-path", str(db), "--store-root", str(root / "store"),
                     "--report-path", str(report_path), "--dry-run"]) == 0
    assert seen == [True] and _rows(environment) == rows_before
    assert json.loads(report_path.read_text())["disposition"] == "inspected"
    # The CLI has no migration import or migration call; missing schema is an
    # error on a pre-existing database, never a reason to create/upgrade it.
    empty = root / "empty.db"
    sqlite3.connect(empty).close()
    monkeypatch.undo()
    assert cli.main(["--db-path", str(empty), "--store-root", str(root / "store"),
                     "--report-path", str(root / "empty-report.json"), "--dry-run"]) == 1
    with sqlite3.connect(empty) as conn:
        assert conn.execute("SELECT name FROM sqlite_master").fetchall() == []


def test_cli_requires_existing_database_store_and_safe_report(environment) -> None:
    root, db, _, _ = environment
    cli = _cli()
    missing = root / "missing.db"
    assert cli.main(["--db-path", str(missing), "--store-root", str(root / "store"),
                     "--report-path", str(root / "report.json")]) == 1
    assert not missing.exists()
    before = _rows(environment)
    assert cli.main(["--db-path", str(db), "--store-root", str(root / "missing-store"),
                     "--report-path", str(root / "report.json")]) == 1
    assert cli.main(["--db-path", str(db), "--store-root", str(root / "store"),
                     "--report-path", str(db)]) == 1
    assert _rows(environment) == before


@pytest.mark.parametrize("destination", ["database", "wal", "shm", "journal", "manifest", "parquet", "store"])
def test_report_refuses_catalog_and_store_destinations(environment, destination) -> None:
    root, db, _, _ = environment
    report = _run(environment)
    paths = {"database": db, "wal": Path(str(db) + "-wal"), "shm": Path(str(db) + "-shm"),
             "journal": Path(str(db) + "-journal"), "manifest": _path(environment, manifest=True),
             "parquet": _path(environment), "store": root / "store" / "report.json"}
    with pytest.raises(QuarantineReportError):
        q.write_quarantine_report(report, paths[destination])
    assert all(r["quality_status"] == "REJECTED" for r in _rows(environment))


def test_report_refuses_symlinks_traversal_and_catalog_alias(environment) -> None:
    root, db, _, _ = environment
    report = _run(environment)
    linked = root / "linked-report.json"
    linked.symlink_to(root / "report.json")
    alias = root / "db-alias.json"
    os.link(db, alias)
    parent = root / "linked-parent"
    parent.symlink_to(root, target_is_directory=True)
    for path in (linked, alias, parent / "report.json", root / ".." / "report.json"):
        with pytest.raises(QuarantineReportError):
            q.write_quarantine_report(report, path)


def test_atomic_report_error_keeps_prior_output_and_genuine_replay_recovers(environment, monkeypatch) -> None:
    root, _, _, _ = environment
    report = _run(environment, now=NOW)
    rows_applied = _rows(environment)
    path = root / "report.json"
    path.write_text("previous complete report\n")
    original_replace = q.os.replace

    def fail(*args, **kwargs):
        raise OSError("injected rename failure")

    monkeypatch.setattr(q.os, "replace", fail)
    with pytest.raises(QuarantineReportError) as failure:
        q.write_quarantine_report(report, path)
    assert failure.value.context["applied"] is True
    assert failure.value.context["report_renamed"] is False
    assert path.read_text() == "previous complete report\n"
    assert not list(root.glob(".quarantine-report-*"))
    assert _rows(environment) == rows_applied
    monkeypatch.setattr(q.os, "replace", original_replace)
    replay = _run(environment)
    q.write_quarantine_report(replay, path)
    payload = json.loads(path.read_text())
    assert payload["idempotent_replay"] and payload["artifacts_unchanged"]
    assert len(payload["targets"]) == len(payload["inspections_pre"]) == 5
    assert payload["inspections_pre"] == payload["inspections_post"]
    assert _rows(environment) == rows_applied


def test_report_directory_fsync_failure_says_output_was_renamed(environment, monkeypatch) -> None:
    root, _, _, _ = environment
    report = _run(environment)
    original = q.os.fsync
    calls = []

    def fail_directory(descriptor):
        calls.append(descriptor)
        if len(calls) == 2:
            raise OSError("directory fsync failure")
        original(descriptor)

    monkeypatch.setattr(q.os, "fsync", fail_directory)
    path = root / "report.json"
    with pytest.raises(QuarantineReportError) as failure:
        q.write_quarantine_report(report, path)
    assert failure.value.context["report_renamed"] is True
    assert json.loads(path.read_text())["applied"] is True
    assert all(r["quality_status"] == "REJECTED" for r in _rows(environment))


def test_cli_post_commit_report_failure_reports_disposition_exit_two(environment, monkeypatch, capsys) -> None:
    root, db, _, targets = environment
    cli = _cli()

    def execute(cat, store, **kwargs):
        return q.execute_fixture_quarantine(cat, store, targets=targets, **kwargs)

    def fail(*args):
        raise QuarantineReportError("injected report failure")

    monkeypatch.setattr(cli, "execute_bitmex_funding_quarantine", execute)
    monkeypatch.setattr(cli, "write_quarantine_report", fail)
    args = ["--db-path", str(db), "--store-root", str(root / "store"),
            "--report-path", str(root / "report.json")]
    assert cli.main(args) == 2
    stderr = capsys.readouterr().err
    assert "disposition=applied" in stderr and "applied=True" in stderr
    assert "does not roll back" in stderr
    rows_applied = _rows(environment)
    monkeypatch.setattr(cli, "write_quarantine_report", q.write_quarantine_report)
    assert cli.main(args) == 0
    assert json.loads((root / "report.json").read_text())["idempotent_replay"]
    assert _rows(environment) == rows_applied


def test_direct_api_rejects_symlink_catalog(environment) -> None:
    root, db, _, targets = environment
    alias = root / "linked-catalog.db"
    alias.symlink_to(db)
    catalog = SqliteDatasetCatalog(alias)
    try:
        with pytest.raises(DatasetQuarantineError, match="authentication"):
            q.execute_fixture_quarantine(catalog, root / "store", targets=targets)
    finally:
        catalog.close()
    assert all(row["quality_status"] == "PASS" for row in _rows(environment))
