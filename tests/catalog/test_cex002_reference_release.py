"""Focused adapter tests. Fixtures are temporary and expected values are local."""

from __future__ import annotations

import decimal
import hashlib
import json
import sqlite3
import subprocess
import threading
from dataclasses import replace
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.catalog.dataset.cex002_reference_release import (
    BITMEX_FALSE_AUTHORITY_TARGETS,
    BUNDLE_ROOT_RELATIVE,
    CODE_PATHS,
    HARMONIC_BUNDLE_ALLOCATION_BYTES,
    MEASURED_CURRENT_BUNDLE_BYTES,
    OPERATING_RESERVE_BYTES,
    QUARANTINE_MARKER,
    RELEASE_METADATA_BYTES,
    RELEASE_METADATA_REMAINDER_BYTES,
    SEALED_CREATED_AT,
    SIZING_PROJECTED_BUNDLE_ROWS,
    ReleaseError,
    ReleaseHooks,
    ReferenceDatasetPlan,
    ReferenceFile,
    identify_products,
    prepare_release,
    production_release_policy,
    publish_release as _publish_release,
    read_release as _read_release,
    reference_proof_component,
    seal_code_identity,
    write_new_bundle_object,
    _sqlite_reservation,
)
from cryptofactors.catalog.runner import apply_migrations

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS = REPO / "sql/migrations"
COMMIT = "a" * 40
CONFIG = "e" * 64
CHECKER = "b" * 64
NAUTILUS = "nautilus-test"
PRODUCTS = (
    "binance_usdm_perpetual_membership",
    "binance_usdm_bar_1h",
    "binance_usdm_trade_flow_1h",
    "binance_usdm_open_interest_5m",
    "binance_usdm_funding_realized",
    "binance_usdm_funding_indicative_1h",
    "binance_usdm_mark_index_basis_1h",
    "binance_usdm_liquidation_observed_daily",
    "binance_usdm_cost_calibration",
    "binance_usdm_coverage_gap",
)
BITMEX_IDS = (
    "ds_4f82fede83f446e3ca29522e6e5f5a0ad7fb6d03d8931f1300addfe413364933",
    "ds_f61c69342932c78c370b7950faf46d3e78be3695dbde8e6077acf8ccfa115deb",
    "ds_11b6665e7dcd37cb85c0098f60681a252801bbc4f80cb053eccc0fa0ce3679ea",
    "ds_ab70ebd21268fe47cbde63b266c0b6f41d0e2ca529d319e3f6f0aa5a5646f512",
    "ds_ee8e9cd9ddd4de87a0c68ef0ff9b4a0da6c6bd7692c96b9f29f8cca13daf46c8",
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write(repo: Path, relative: str, payload: bytes) -> tuple[str, int]:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return _sha(payload), len(payload)


def _parquet(rows: int = 1) -> bytes:
    arrow = pa.dictionary(pa.int32(), pa.string())
    table = pa.table({"native_symbol": pa.array(["BTCUSDT"] * rows, type=arrow)})
    sink = pa.BufferOutputStream()
    pq.write_table(
        table,
        sink,
        compression="zstd",
        compression_level=3,
        version="2.6",
        row_group_size=65_536,
        use_dictionary=True,
        write_statistics=False,
        store_schema=True,
    )
    return sink.getvalue().to_pybytes()


def _named_parquet(symbol: str) -> bytes:
    arrow = pa.dictionary(pa.int32(), pa.string())
    table = pa.table({"native_symbol": pa.array([symbol], type=arrow)})
    sink = pa.BufferOutputStream()
    pq.write_table(
        table,
        sink,
        compression="zstd",
        compression_level=3,
        version="2.6",
        row_group_size=65_536,
        use_dictionary=True,
        write_statistics=False,
        store_schema=True,
    )
    return sink.getvalue().to_pybytes()


def _fields() -> tuple[tuple[str, str, bool], ...]:
    schema = pq.ParquetFile(pa.BufferReader(_parquet())).schema_arrow
    return tuple((field.name, str(field.type), bool(field.nullable)) for field in schema)


def _policy(repo: Path, catalog: Path):
    code = seal_code_identity(
        repo,
        COMMIT,
        bind_runtime=False,
        file_bytes={relative: f"code-{index}".encode() for index, relative in enumerate(CODE_PATHS)},
    )
    return replace(
        production_release_policy(repo, catalog, code),
        observed_free_bytes=OPERATING_RESERVE_BYTES + 8_000_000_000,
    )


def _plans(repo: Path, payload: bytes | None = None) -> tuple[ReferenceDatasetPlan, ...]:
    body = payload if payload is not None else _parquet()
    fields = _fields()
    digest, size = _write(repo, f"{BUNDLE_ROOT_RELATIVE}/.objects/aa/{_sha(body)}", body)
    # The path above used the digest after the write name was chosen from the same hash.
    relative = f"{BUNDLE_ROOT_RELATIVE}/.objects/aa/{digest}"
    if not (repo / relative).is_file():
        _write(repo, relative, body)
    plans = []
    for product in PRODUCTS:
        file_digest, file_size = _write(repo, f"data/fixture/{product}.json", f'{{"product":"{product}"}}\n'.encode())
        plans.append(
            ReferenceDatasetPlan(
                product,
                CONFIG,
                (
                    ReferenceFile(
                        f"data/fixture/{product}.json",
                        file_digest,
                        0,
                        file_size,
                        {"role": "metadata"},
                        False,
                    ),
                ),
                {"product": product, "fixture": True},
            )
        )
    plans.append(
        ReferenceDatasetPlan(
            "binance_usdm_harmonic_bundle",
            CONFIG,
            (
                ReferenceFile(
                    relative,
                    digest,
                    1,
                    size,
                    {"role": "harmonic_bundle"},
                    True,
                    fields,
                ),
            ),
            {"product": "binance_usdm_harmonic_bundle", "fixture": True},
            PRODUCTS,
        )
    )
    return tuple(plans)


def _migrate(catalog: Path) -> None:
    apply_migrations(catalog, MIGRATIONS)


def _seed_bitmex(catalog: Path) -> None:
    assert tuple(item.dataset_id for item in BITMEX_FALSE_AUTHORITY_TARGETS) == BITMEX_IDS
    connection = sqlite3.connect(catalog)
    try:
        for target in BITMEX_FALSE_AUTHORITY_TARGETS:
            connection.execute(
                """
                INSERT INTO dataset (
                    dataset_id, dataset_type, schema_version, schema_fingerprint, manifest_sha256,
                    manifest_uri, publication_uri, transform_name, transform_version, code_commit,
                    config_sha256, row_count, byte_size, quality_status, quality_summary_json,
                    publication_status, created_at
                ) VALUES (?, ?, '1', ?, ?, ?, NULL, 'cex002_reference_publication', '1', ?, ?, ?, ?,
                          'REJECTED', ?, 'REGISTERED', ?)
                """,
                (
                    target.dataset_id,
                    target.dataset_type,
                    "f" * 64,
                    target.manifest_sha256,
                    f"bitmex/manifests/{target.dataset_id}.json",
                    COMMIT,
                    CONFIG,
                    target.rows,
                    target.byte_size,
                    json.dumps({"quarantine_marker": QUARANTINE_MARKER}, sort_keys=True, separators=(",", ":")),
                    target.created_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO dataset_file (
                    dataset_id, storage_uri, file_sha256, byte_size, row_count, partition_json
                ) VALUES (?, ?, ?, ?, ?, '{}')
                """,
                (target.dataset_id, target.relative_path, target.file_sha256, target.byte_size, target.rows),
            )
        connection.commit()
    finally:
        connection.close()


def publish_release(policy, prepared_sha: str, proof: bytes, **kwargs):
    kwargs.setdefault("proof_sha256", _sha(proof))
    kwargs.setdefault("checker_sha256", CHECKER)
    kwargs.setdefault("nautilus_version", NAUTILUS)
    return _publish_release(policy, prepared_sha, proof, **kwargs)


def read_release(policy, publication_sha: str, proof: bytes, **kwargs):
    kwargs.setdefault("proof_sha256", _sha(proof))
    kwargs.setdefault("checker_sha256", CHECKER)
    kwargs.setdefault("nautilus_version", NAUTILUS)
    return _read_release(policy, publication_sha, proof, **kwargs)


def _proof(repo: Path, prepared, *, scope: str = "complete_release", bad_integer: bool = False) -> bytes:
    datasets = []
    for manifest in prepared.manifests:
        components = []
        for spec in manifest.files:
            component = reference_proof_component(
                repo / spec.relative_path,
                spec.relative_path,
                spec.partition["kind"],
            )
            if bad_integer:
                component["source_row_count"] = True
            components.append(component)
        datasets.append({"dataset_id": manifest.dataset_id, "components": components})
    document = {
        "candidate_sha256": prepared.descriptor_sha256,
        "checker_source_sha256": CHECKER,
        "datasets": datasets,
        "document_type": "cex002_harmonic_bundle_consumer_proof",
        "nautilus_version": NAUTILUS,
        "schema_version": 1,
        "scope": scope,
        "status": "PASS",
    }
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _ready(tmp_path: Path, payload: bytes | None = None):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    catalog = tmp_path / "catalog.sqlite"
    _migrate(catalog)
    _seed_bitmex(catalog)
    policy = _policy(repo, catalog)
    prepared = prepare_release(_plans(repo, payload), policy, config_sha256=CONFIG, authorities={"fixture": True})
    return repo, policy, prepared


def test_resource_pins_are_the_measured_projection() -> None:
    assert MEASURED_CURRENT_BUNDLE_BYTES == 1_133_590
    assert SIZING_PROJECTED_BUNDLE_ROWS == 150_331
    assert HARMONIC_BUNDLE_ALLOCATION_BYTES == 24_352_003
    assert MEASURED_CURRENT_BUNDLE_BYTES + HARMONIC_BUNDLE_ALLOCATION_BYTES == 25_485_593
    assert SIZING_PROJECTED_BUNDLE_ROWS * 8 + 22_850_312 + 299_043 == HARMONIC_BUNDLE_ALLOCATION_BYTES
    assert RELEASE_METADATA_BYTES == 5_556_368_003
    assert RELEASE_METADATA_REMAINDER_BYTES == 4_985_471_619
    assert OPERATING_RESERVE_BYTES == 29_690_701_415
    assert SEALED_CREATED_AT.isoformat() == "1970-01-01T00:00:00+00:00"


def test_sqlite_record_reservation_admits_accepted_reference_scale(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    catalog = tmp_path / "catalog.sqlite"
    _migrate(catalog)
    manifests = prepare_release(
        _plans(repo), _policy(repo, catalog), config_sha256=CONFIG, authorities={"fixture": True}
    ).manifests
    sample = manifests[0].files[0]
    prefix = "data/.cex002_coverage/.source-gaps/binance_usdm_bar_1h/BTCUSDT/authority/"
    partition = {"kind": "table", "native_symbol": "BTCUSDT", "utc_month": "authority", "component": "source_gap"}
    scaled = replace(manifests[0], files=tuple(
        replace(sample, relative_path=f"{prefix}{index:064x}.parquet", partition=partition)
        for index in range(147_081)
    ))
    assert _sqlite_reservation((scaled, *manifests[1:])) < RELEASE_METADATA_REMAINDER_BYTES


def test_prepare_is_not_a_consumable_release(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    catalog = tmp_path / "catalog.sqlite"
    _migrate(catalog)
    policy = _policy(repo, catalog)
    plans = _plans(repo)
    identified = identify_products(plans[:10], policy, CONFIG)
    assert len(identified) == 10
    prepared = prepare_release(plans, policy, config_sha256=CONFIG, authorities={"fixture": True})
    assert prepared.consumable is False
    document = json.loads((repo / prepared.descriptor_relative_path).read_text())
    assert document["document_type"] == "cex002_harmonic_bundle_prepared_release"
    assert document["consumable"] is False
    assert document["catalog_commit_required"] is True
    assert document["authorities"] == {"fixture": True}
    connection = sqlite3.connect(catalog)
    try:
        assert connection.execute("SELECT COUNT(*) FROM dataset").fetchone()[0] == 0
    finally:
        connection.close()


def test_bundle_allocation_and_metadata_bounds_fail_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    policy = replace(
        _policy(repo, tmp_path / "catalog.sqlite"),
        enforce_published_allocation=False,
        bundle_allocation_bytes=1,
    )
    with pytest.raises(ReleaseError) as allocation:
        prepare_release(_plans(repo), policy, config_sha256=CONFIG, authorities={"fixture": True})
    assert allocation.value.blocker == "bundle_allocation_exceeded"
    blocked = list((repo / BUNDLE_ROOT_RELATIVE / ".prepared").glob("*.json"))
    assert len(blocked) == 1
    assert json.loads(blocked[0].read_text())["consumable"] is False
    huge = tmp_path / "huge"
    huge.mkdir()
    metadata = replace(
        _policy(huge, tmp_path / "other.sqlite"),
        enforce_metadata_pin=False,
        metadata_remainder_bytes=0,
    )
    with pytest.raises(ReleaseError) as remainder:
        prepare_release(_plans(huge), metadata, config_sha256=CONFIG, authorities={"fixture": True})
    assert remainder.value.blocker == "metadata_remainder_exceeded"


def test_operating_reserve_cannot_be_spent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    policy = replace(_policy(repo, tmp_path / "catalog.sqlite"), operating_reserve_bytes=1)
    with pytest.raises(ReleaseError) as exc:
        prepare_release((), policy, config_sha256=CONFIG, authorities={})
    assert exc.value.blocker == "operating_reserve_not_preserved"


def test_consumer_proof_gates(tmp_path: Path) -> None:
    repo, policy, prepared = _ready(tmp_path)
    bare_bytes = b'{"status":"PASS"}'
    with pytest.raises(ReleaseError) as bare:
        publish_release(policy, prepared.descriptor_sha256, bare_bytes)
    assert bare.value.blocker == "consumer_proof_bare_pass"
    with pytest.raises(ReleaseError) as sample:
        publish_release(policy, prepared.descriptor_sha256, _proof(repo, prepared, scope="sample_only"))
    assert sample.value.blocker == "consumer_proof_sample_only"
    with pytest.raises(ReleaseError) as boolean:
        publish_release(policy, prepared.descriptor_sha256, _proof(repo, prepared, bad_integer=True))
    assert boolean.value.blocker == "consumer_proof_unsupported"
    missing = json.loads(_proof(repo, prepared))
    missing["datasets"][0]["components"] = []
    missing_bytes = json.dumps(missing).encode()
    with pytest.raises(ReleaseError) as incomplete:
        publish_release(policy, prepared.descriptor_sha256, missing_bytes)
    assert incomplete.value.blocker == "consumer_proof_incomplete"
    proof = _proof(repo, prepared)
    with pytest.raises(ReleaseError) as pinned:
        publish_release(policy, prepared.descriptor_sha256, proof, proof_sha256="c" * 64)
    assert pinned.value.blocker == "consumer_proof_pin"
    connection = sqlite3.connect(policy.catalog_path)
    try:
        admitted = connection.execute(
            "SELECT COUNT(*) FROM dataset WHERE quality_status = 'PASS'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert admitted == 0


def test_schema_and_row_mismatch(tmp_path: Path) -> None:
    repo = tmp_path / "schema"
    repo.mkdir()
    policy = _policy(repo, tmp_path / "schema.sqlite")
    plans = list(_plans(repo))
    bundle = plans[-1]
    spec = bundle.files[0]
    plans[-1] = replace(
        bundle,
        files=(replace(spec, schema_fields=(("native_symbol", "string", False),)),),
    )
    with pytest.raises(ReleaseError) as schema:
        prepare_release(tuple(plans), policy, config_sha256=CONFIG, authorities={"fixture": True})
    assert schema.value.blocker == "schema_mismatch"
    row_repo = tmp_path / "rows"
    row_repo.mkdir()
    row_policy = _policy(row_repo, tmp_path / "rows.sqlite")
    row_plans = list(_plans(row_repo))
    row_bundle = row_plans[-1]
    row_plans[-1] = replace(row_bundle, files=(replace(row_bundle.files[0], rows=2),))
    with pytest.raises(ReleaseError) as rows:
        prepare_release(tuple(row_plans), row_policy, config_sha256=CONFIG, authorities={"fixture": True})
    assert rows.value.blocker == "row_mismatch"


def test_publish_replay_and_reader(tmp_path: Path) -> None:
    repo, policy, prepared = _ready(tmp_path)
    proof = _proof(repo, prepared)
    connection = sqlite3.connect(policy.catalog_path, isolation_level=None)
    try:
        # The caller's ordinary tuple-row connection has no row factory.
        first = publish_release(policy, prepared.descriptor_sha256, proof, connection=connection)
    finally:
        connection.close()
    assert first.reused is False and first.consumable is True
    second = publish_release(policy, prepared.descriptor_sha256, proof)
    assert second.reused is True and second.publication_sha256 == first.publication_sha256
    visible = read_release(policy, first.publication_sha256, proof)
    assert visible.consumable is True
    connection = sqlite3.connect(policy.catalog_path)
    try:
        rows = connection.execute(
            "SELECT COUNT(*) FROM dataset WHERE dataset_type NOT IN ('bitmex_funding', 'bitmex_funding_full')"
        ).fetchone()
        assert rows[0] == 11
        consumable = connection.execute(
            "SELECT dataset_id FROM dataset WHERE dataset_type = 'bitmex_funding' AND quality_status = 'PASS'"
        ).fetchall()
        assert consumable == []
    finally:
        connection.close()


def test_interruption_before_and_after_commit(tmp_path: Path) -> None:
    repo, policy, prepared = _ready(tmp_path)
    proof = _proof(repo, prepared)
    target = repo / prepared.manifests[0].files[0].relative_path

    def corrupt(_path: Path) -> None:
        target.write_bytes(target.read_bytes() + b"x")

    with pytest.raises(ReleaseError) as changed:
        publish_release(
            policy,
            prepared.descriptor_sha256,
            proof,
            hooks=ReleaseHooks(before_commit=corrupt),
        )
    assert changed.value.blocker == "input_changed_during_admission"
    connection = sqlite3.connect(policy.catalog_path)
    try:
        count = connection.execute(
            "SELECT COUNT(*) FROM dataset WHERE quality_status = 'PASS'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert count == 0
    target.write_bytes(target.read_bytes()[:-1])

    def boom(_published) -> None:
        raise ReleaseError("after commit", blocker="after_commit")

    with pytest.raises(ReleaseError) as raised:
        publish_release(
            policy,
            prepared.descriptor_sha256,
            proof,
            hooks=ReleaseHooks(after_commit=boom),
        )
    assert raised.value.blocker == "after_commit"
    visible = read_release(policy, _publication_sha(repo), proof)
    assert visible.consumable is True


def _publication_sha(repo: Path) -> str:
    files = list((repo / BUNDLE_ROOT_RELATIVE / ".publication").glob("*.json"))
    assert len(files) == 1
    return files[0].stem


def test_pending_transaction_and_conflict_roll_back(tmp_path: Path) -> None:
    repo, policy, prepared = _ready(tmp_path)
    proof = _proof(repo, prepared)
    held = sqlite3.connect(policy.catalog_path)
    try:
        held.execute("BEGIN")
        held.execute("CREATE TABLE sentinel (value TEXT)")
        held.execute("INSERT INTO sentinel (value) VALUES ('uncommitted')")
        with pytest.raises(ReleaseError) as pending:
            publish_release(policy, prepared.descriptor_sha256, proof, connection=held)
        assert pending.value.blocker == "pending_catalog_transaction"
        assert held.execute("SELECT value FROM sentinel").fetchone()[0] == "uncommitted"
        other = sqlite3.connect(policy.catalog_path)
        try:
            names = {row[0] for row in other.execute("SELECT name FROM sqlite_master")}
        finally:
            other.close()
        assert "sentinel" not in names
        held.rollback()
    finally:
        held.close()
    connection = sqlite3.connect(policy.catalog_path)
    try:
        connection.execute(
            """
            INSERT INTO dataset (
                dataset_id, dataset_type, schema_version, manifest_sha256, manifest_uri,
                transform_name, transform_version, code_commit, config_sha256, row_count,
                byte_size, quality_status, publication_status, created_at
            ) VALUES (?, 'binance_usdm_bar_1h', '1', ?, ?, 'cex002_reference_publication', '1',
                      ?, ?, 1, 1, 'PASS', 'REGISTERED', '1970-01-01T00:00:00+00:00')
            """,
            ("ds_" + "ab" * 32, "1" * 64, "fixture/conflict.json", COMMIT, CONFIG),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ReleaseError) as conflict:
        publish_release(policy, prepared.descriptor_sha256, proof, checker_sha256=CHECKER, nautilus_version=NAUTILUS)
    assert conflict.value.blocker == "conflicting_release"
    connection = sqlite3.connect(policy.catalog_path)
    try:
        count = connection.execute(
            "SELECT COUNT(*) FROM dataset WHERE dataset_id = ?",
            (prepared.dataset_ids["binance_usdm_bar_1h"],),
        ).fetchone()[0]
    finally:
        connection.close()
    assert count == 0


def test_reader_rejects_partial_and_mixed_releases(tmp_path: Path) -> None:
    repo, policy, prepared = _ready(tmp_path)
    proof = _proof(repo, prepared)
    published = publish_release(policy, prepared.descriptor_sha256, proof)
    dataset_id = prepared.dataset_ids["binance_usdm_harmonic_bundle"]
    connection = sqlite3.connect(policy.catalog_path)
    try:
        connection.execute("DELETE FROM dataset_file WHERE dataset_id = ?", (dataset_id,))
        connection.execute("DELETE FROM dataset_input_dataset WHERE dataset_id = ? OR input_dataset_id = ?", (dataset_id, dataset_id))
        connection.execute("DELETE FROM dataset WHERE dataset_id = ?", (dataset_id,))
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ReleaseError) as partial:
        read_release(policy, published.publication_sha256, proof)
    assert partial.value.blocker == "partial_release"
    _ready_again = tmp_path / "mixed"
    mixed_repo, mixed_policy, mixed_prepared = _ready(_ready_again)
    mixed_proof = _proof(mixed_repo, mixed_prepared)
    mixed = publish_release(mixed_policy, mixed_prepared.descriptor_sha256, mixed_proof)
    connection = sqlite3.connect(mixed_policy.catalog_path)
    try:
        connection.execute(
            "UPDATE dataset SET quality_summary_json = '{\"changed\":true}' WHERE dataset_id = ?",
            (mixed_prepared.dataset_ids["binance_usdm_cost_calibration"],),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ReleaseError) as mixed_error:
        read_release(mixed_policy, mixed.publication_sha256, mixed_proof)
    assert mixed_error.value.blocker == "mixed_release"


def test_missing_bitmex_rows_and_ineligible_resolution(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    catalog = tmp_path / "catalog.sqlite"
    _migrate(catalog)
    policy = _policy(repo, catalog)
    prepared = prepare_release(_plans(repo), policy, config_sha256=CONFIG, authorities={"fixture": True})
    with pytest.raises(ReleaseError) as missing:
        publish_release(policy, prepared.descriptor_sha256, _proof(repo, prepared))
    assert missing.value.blocker == "bitmex_false_authority_missing"
    _seed_bitmex(catalog)
    from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog

    store = SqliteDatasetCatalog(catalog)
    try:
        assert store.resolve_latest_by_type("bitmex_funding", consumable_only=True) is None
        assert store.resolve_latest_by_type("bitmex_funding_full", consumable_only=True) is None
        assert store.is_consumable(BITMEX_IDS[0]) is False
    finally:
        store.close()


def test_concurrent_identical_and_conflicting_writers(tmp_path: Path) -> None:
    repo, policy, prepared = _ready(tmp_path)
    proof = _proof(repo, prepared)
    results: list = []
    errors: list = []
    barrier = threading.Barrier(2)

    def publish() -> None:
        barrier.wait(5)
        try:
            results.append(publish_release(policy, prepared.descriptor_sha256, proof))
        except Exception as exc:  # noqa: BLE001 - the test records either writer's failure
            errors.append(exc)

    threads = [threading.Thread(target=publish), threading.Thread(target=publish)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert errors == []
    assert sorted(item.reused for item in results) == [False, True]
    moved_repo, moved_policy, moved = _ready(tmp_path / "moved")
    assert moved.dataset_ids == prepared.dataset_ids
    home = identify_products(_plans(repo)[:10], policy, CONFIG)
    away = identify_products(_plans(moved_repo)[:10], moved_policy, CONFIG)
    assert [item.dataset_id for item in home] == [item.dataset_id for item in away]
    race = tmp_path / "race"
    left = race / "left"
    right = race / "right"
    left.mkdir(parents=True)
    right.mkdir(parents=True)
    catalog = race / "catalog.sqlite"
    _migrate(catalog)
    _seed_bitmex(catalog)
    left_policy = _policy(left, catalog)
    right_policy = _policy(right, catalog)
    left_prepared = prepare_release(
        _plans(left, _named_parquet("BTCUSDT")),
        left_policy,
        config_sha256=CONFIG,
        authorities={"fixture": True},
    )
    right_prepared = prepare_release(
        _plans(right, _named_parquet("ETHUSDT")),
        right_policy,
        config_sha256=CONFIG,
        authorities={"fixture": True},
    )
    left_id = left_prepared.dataset_ids["binance_usdm_harmonic_bundle"]
    right_id = right_prepared.dataset_ids["binance_usdm_harmonic_bundle"]
    assert left_id != right_id
    left_proof = _proof(left, left_prepared)
    right_proof = _proof(right, right_prepared)
    race_results: list = []
    race_errors: list = []
    race_barrier = threading.Barrier(2)

    def publish_left() -> None:
        race_barrier.wait(5)
        try:
            race_results.append(publish_release(left_policy, left_prepared.descriptor_sha256, left_proof))
        except ReleaseError as exc:
            race_errors.append(exc.blocker)

    def publish_right() -> None:
        race_barrier.wait(5)
        try:
            race_results.append(publish_release(right_policy, right_prepared.descriptor_sha256, right_proof))
        except ReleaseError as exc:
            race_errors.append(exc.blocker)

    pair = [threading.Thread(target=publish_left), threading.Thread(target=publish_right)]
    for thread in pair:
        thread.start()
    for thread in pair:
        thread.join(30)
    assert race_errors == ["conflicting_release"]
    assert len(race_results) == 1 and race_results[0].reused is False
    connection = sqlite3.connect(catalog)
    try:
        present = {
            row[0]
            for row in connection.execute(
                "SELECT dataset_id FROM dataset WHERE dataset_id IN (?, ?)",
                (left_id, right_id),
            )
        }
    finally:
        connection.close()
    assert present == {race_results[0].dataset_ids["binance_usdm_harmonic_bundle"]}


def test_empty_plan_and_false_authority_type_are_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    policy = _policy(repo, tmp_path / "catalog.sqlite")
    plans = list(_plans(repo))
    plans[0] = replace(plans[0], files=())
    with pytest.raises(ReleaseError) as empty:
        prepare_release(tuple(plans), policy, config_sha256=CONFIG, authorities={"fixture": True})
    assert empty.value.blocker == "empty_required"
    forbidden_root = tmp_path / "forbidden"
    forbidden = list(_plans(forbidden_root))
    forbidden[0] = replace(forbidden[0], dataset_type="bitmex_funding")
    with pytest.raises(ReleaseError) as mixed:
        prepare_release(
            tuple(forbidden),
            _policy(forbidden_root, tmp_path / "f.sqlite"),
            config_sha256=CONFIG,
            authorities={"fixture": True},
        )
    assert mixed.value.blocker == "mixed_authority"


def _write_table(path: Path, table: pa.Table) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        table,
        path,
        compression="zstd",
        compression_level=3,
        version="2.6",
        row_group_size=65_536,
        use_dictionary=True,
        write_statistics=False,
        store_schema=True,
    )


def _symbols(kind: str) -> pa.Array:
    values = ["BTCUSDT", "ETHUSDT"]
    if kind == "dictionary":
        return pa.array(values, type=pa.dictionary(pa.int32(), pa.string()))
    return pa.array(values, type=pa.string())


def _fee(first: str) -> pa.Array:
    values = [decimal.Decimal(first), decimal.Decimal("0.0010")]
    return pa.array(values, type=pa.decimal128(10, 4))


def _times(first: int) -> pa.Array:
    return pa.array([first, 1_700_003_600_000], type=pa.timestamp("ms"))


def test_logical_digest_tracks_values_not_parquet_encoding(tmp_path: Path) -> None:
    moment = _times(1_700_000_000_000)
    fee = _fee("0.0005")
    dictionary = pa.table(
        {"native_symbol": _symbols("dictionary"), "fee": fee, "open_time": moment}
    )
    plain = pa.table({"native_symbol": _symbols("plain"), "fee": fee, "open_time": moment})
    dictionary_path = tmp_path / "dictionary.parquet"
    plain_path = tmp_path / "plain.parquet"
    _write_table(dictionary_path, dictionary)
    _write_table(plain_path, plain)
    encoded = reference_proof_component(dictionary_path, "dictionary.parquet", "table")
    literal = reference_proof_component(plain_path, "plain.parquet", "table")
    assert encoded["value_identity"] == "typed_row_digest"
    assert encoded["source_value_sha256"] == literal["source_value_sha256"]
    assert encoded["physical_sha256"] != literal["physical_sha256"]
    assert encoded["time_absence_reason"] is None
    assert encoded["time_start"] != encoded["time_end"]
    changed_fee = pa.table(
        {"native_symbol": _symbols("plain"), "fee": _fee("0.0006"), "open_time": moment}
    )
    fee_path = tmp_path / "fee.parquet"
    _write_table(fee_path, changed_fee)
    fee_proof = reference_proof_component(fee_path, "fee.parquet", "table")
    assert fee_proof["source_value_sha256"] != literal["source_value_sha256"]
    changed_time = pa.table(
        {"native_symbol": _symbols("plain"), "fee": fee, "open_time": _times(1_700_000_000_001)}
    )
    time_path = tmp_path / "time.parquet"
    _write_table(time_path, changed_time)
    time_proof = reference_proof_component(time_path, "time.parquet", "table")
    assert time_proof["source_value_sha256"] != literal["source_value_sha256"]
    assert time_proof["time_start"] != literal["time_start"]
    note = tmp_path / "note.json"
    note.write_bytes(b'{"kind":"metadata"}\n')
    metadata = reference_proof_component(note, "note.json", "metadata")
    assert metadata["value_identity"] == "metadata_bytes"
    assert metadata["time_absence_reason"] == "non_temporal_component"
    assert metadata["source_row_count"] == 0
    assert metadata["source_value_sha256"] == metadata["physical_sha256"]


def test_logical_digest_preserves_precision_38_and_nanoseconds(tmp_path: Path) -> None:
    schema = pa.schema([
        pa.field("fee", pa.decimal128(38, 8), nullable=False),
        pa.field("event_time", pa.timestamp("ns"), nullable=False),
    ])
    def proof(name: str, fee: str, instant: int) -> dict:
        path = tmp_path / f"{name}.parquet"
        _write_table(path, pa.Table.from_arrays([
            pa.array([decimal.Decimal(fee)], type=schema.field("fee").type),
            pa.array([instant], type=schema.field("event_time").type),
        ], schema=schema))
        return reference_proof_component(path, path.name, "table")

    base = proof("base", "123456789012345678901234567890.12345678", 1_700_000_000_000_000_001)
    decimal_change = proof("decimal", "123456789012345678901234567890.12345679", 1_700_000_000_000_000_001)
    time_change = proof("time", "123456789012345678901234567890.12345678", 1_700_000_000_000_000_002)
    assert base["source_value_sha256"] != decimal_change["source_value_sha256"]
    assert base["source_value_sha256"] != time_change["source_value_sha256"]
    assert base["time_start"] == "2023-11-14T22:13:20.000000001+00:00"
    assert time_change["time_start"] == "2023-11-14T22:13:20.000000002+00:00"


def test_repeated_descriptor_is_not_a_complete_chain(tmp_path: Path) -> None:
    repo, policy, prepared = _ready(tmp_path)
    document = json.loads((repo / prepared.descriptor_relative_path).read_text())
    document["datasets"] = [document["datasets"][0]] * 11
    payload = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()
    digest = _sha(payload)
    relative = f"{BUNDLE_ROOT_RELATIVE}/.prepared/{digest}.json"
    (repo / relative).parent.mkdir(parents=True, exist_ok=True)
    (repo / relative).write_bytes(payload)
    with pytest.raises(ReleaseError) as exc:
        publish_release(policy, digest, _proof(repo, prepared))
    assert exc.value.blocker == "mixed_release"


def test_code_identity_binds_the_committed_blobs(tmp_path: Path) -> None:
    repo = tmp_path / "code"
    payloads = {}
    for index, relative in enumerate(CODE_PATHS):
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        body = f"blob-{index}\n".encode()
        path.write_bytes(body)
        payloads[relative] = body
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "--", *CODE_PATHS], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.email=cex002@example.invalid",
            "-c",
            "user.name=CEX002",
            "commit",
            "-m",
            "fixture",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    executing = {relative: repo / relative for relative in CODE_PATHS[:3]}
    sealed = seal_code_identity(repo, commit, bind_runtime=True, executing=executing)
    again = seal_code_identity(repo, commit, bind_runtime=False)
    assert sealed.lock_sha256 == again.lock_sha256
    injected = seal_code_identity(repo, commit, bind_runtime=False, file_bytes=payloads)
    assert injected.lock_sha256 == sealed.lock_sha256
    with pytest.raises(ReleaseError) as runtime:
        seal_code_identity(repo, commit, bind_runtime=True, file_bytes=payloads)
    assert runtime.value.blocker == "dirty_code"
    (repo / CODE_PATHS[0]).write_bytes(b"dirty\n")
    with pytest.raises(ReleaseError) as dirty:
        seal_code_identity(repo, commit, bind_runtime=False)
    assert dirty.value.blocker == "dirty_code"
    with pytest.raises(ReleaseError) as missing:
        seal_code_identity(repo, "ab" * 20, bind_runtime=False)
    assert missing.value.blocker == "dirty_code"


def test_symlinked_catalog_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    real = tmp_path / "real.sqlite"
    _migrate(real)
    link = tmp_path / "catalog.sqlite"
    link.symlink_to(real)
    with pytest.raises(ReleaseError) as exc:
        prepare_release(
            _plans(repo),
            _policy(repo, link),
            config_sha256=CONFIG,
            authorities={"fixture": True},
        )
    assert exc.value.blocker == "unsafe_path"


def test_stale_stage_does_not_block_a_later_prepare(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    catalog = tmp_path / "catalog.sqlite"
    _migrate(catalog)
    stale = repo / BUNDLE_ROOT_RELATIVE / ".prepared" / ".fixed.json.tmp"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale-attempt")
    prepared = prepare_release(
        _plans(repo),
        _policy(repo, catalog),
        config_sha256=CONFIG,
        authorities={"fixture": True},
    )
    assert prepared.consumable is False
    assert stale.read_bytes() == b"stale-attempt"
    assert (repo / prepared.descriptor_relative_path).is_file()


def test_free_space_preserves_the_operating_reserve(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    catalog = tmp_path / "catalog.sqlite"
    _migrate(catalog)
    policy = replace(_policy(repo, catalog), observed_free_bytes=OPERATING_RESERVE_BYTES)
    with pytest.raises(ReleaseError) as exc:
        prepare_release(_plans(repo), policy, config_sha256=CONFIG, authorities={"fixture": True})
    assert exc.value.blocker == "operating_reserve_not_preserved"
    assert list((repo / BUNDLE_ROOT_RELATIVE).rglob("*.json")) == []
    connection = sqlite3.connect(catalog)
    try:
        admitted = connection.execute(
            "SELECT COUNT(*) FROM dataset WHERE quality_status = 'PASS'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert admitted == 0


def test_bundle_object_preflight_counts_existing_owned_candidates(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    catalog = tmp_path / "catalog.sqlite"
    _migrate(catalog)
    low = replace(_policy(repo, catalog), observed_free_bytes=OPERATING_RESERVE_BYTES)
    with pytest.raises(ReleaseError) as capacity:
        write_new_bundle_object(repo, b"new candidate", low)
    assert capacity.value.blocker == "operating_reserve_not_preserved"
    assert not list((repo / BUNDLE_ROOT_RELATIVE).rglob("*.tmp"))
    assert not list((repo / BUNDLE_ROOT_RELATIVE / ".objects").rglob("*"))
    existing = repo / BUNDLE_ROOT_RELATIVE / ".objects" / "aa" / "candidate"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"old")
    cap = replace(
        _policy(repo, catalog), enforce_published_allocation=False,
        bundle_allocation_bytes=len(b"old") + len(b"new candidate") - 1,
    )
    with pytest.raises(ReleaseError) as allocation:
        write_new_bundle_object(repo, b"new candidate", cap)
    assert allocation.value.blocker == "bundle_allocation_exceeded"
    assert existing.read_bytes() == b"old"


def test_mid_insert_failure_rolls_the_release_back(tmp_path: Path) -> None:
    repo, policy, prepared = _ready(tmp_path)
    proof = _proof(repo, prepared)

    def fail(count: int) -> None:
        if count >= 1:
            raise ReleaseError("insert failed", blocker="after_insert")

    with pytest.raises(ReleaseError) as exc:
        publish_release(
            policy,
            prepared.descriptor_sha256,
            proof,
            hooks=ReleaseHooks(after_insert=fail),
        )
    assert exc.value.blocker == "after_insert"
    connection = sqlite3.connect(policy.catalog_path)
    try:
        rejected = connection.execute(
            "SELECT COUNT(*) FROM dataset WHERE quality_status = 'REJECTED'"
        ).fetchone()[0]
        passed = connection.execute(
            "SELECT COUNT(*) FROM dataset WHERE quality_status = 'PASS'"
        ).fetchone()[0]
        identifiers = {row[0] for row in connection.execute("SELECT dataset_id FROM dataset")}
    finally:
        connection.close()
    assert rejected == 5
    assert passed == 0
    assert identifiers == set(BITMEX_IDS)


def test_metadata_mutation_after_insert_rolls_back(tmp_path: Path) -> None:
    repo, policy, prepared = _ready(tmp_path)
    proof = _proof(repo, prepared)
    manifest_path = repo / BUNDLE_ROOT_RELATIVE / ".manifests" / f"{prepared.manifests[0].manifest_sha256}.json"

    def mutate(count: int) -> None:
        if count == 11:
            manifest_path.write_bytes(manifest_path.read_bytes() + b" ")

    with pytest.raises(ReleaseError) as exc:
        publish_release(
            policy, prepared.descriptor_sha256, proof,
            hooks=ReleaseHooks(after_insert=mutate),
        )
    assert exc.value.blocker == "input_changed_during_admission"
    connection = sqlite3.connect(policy.catalog_path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM dataset WHERE quality_status = 'PASS'").fetchone()[0] == 0
    finally:
        connection.close()
