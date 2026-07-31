"""DEX-003 — forward-only migration 0017 + v2 persistence record contract.

No network. Proves the persistence schema matches the v2 record contract
(plan/node/lease/leaf/header/coverage) and rejects forged or divergent rows
the same way the frozen records do. All databases are temporary; the
repository migration file is only copied, never modified.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from cryptofactors.acquisition.uniswap_v2_pair_events import SWAP_TOPIC
from cryptofactors.acquisition.uniswap_v2_pair_events_v2 import (
    CanonicalHeaderReceiptRecord,
    PlanConfig,
    QueryDomain,
    QueryNode,
    RegistryPoolBirth,
    compute_canonical_header_receipt_id,
    coverage_product_record,
    make_leaf_receipt_record,
    plan_record_from_config,
    prove_pool_topic_coverage,
    query_node_record_from_node,
)
from cryptofactors.catalog.runner import apply_migrations

REPO_MIGRATIONS = Path(__file__).resolve().parent.parent.parent / "sql" / "migrations"

PLAN_TABLE = "uniswap_v2_pair_event_v2_plan"
NODE_TABLE = "uniswap_v2_pair_event_v2_query_node"
LEASE_TABLE = "uniswap_v2_pair_event_v2_query_lease"
LEAF_TABLE = "uniswap_v2_pair_event_v2_leaf_receipt"
HEADER_TABLE = "uniswap_v2_pair_event_v2_canonical_header_receipt"
COVERAGE_TABLE = "uniswap_v2_pair_event_v2_coverage_product"
DEPENDENCY_TABLE = "uniswap_v2_pair_event_v2_leaf_header_dependency"

POOL_A = "0x" + "11" * 20
POOL_B = "0x" + "22" * 20
BLOCK = 10_008_355


def _copy_migrations(dst: Path, version: int) -> Path:
    dst.mkdir(parents=True, exist_ok=True)
    src = next(REPO_MIGRATIONS.glob(f"{version:04d}_*.sql"))
    target = dst / src.name
    shutil.copy(src, target)
    return target


def _applied_db(tmp_path: Path) -> tuple[Path, Path, sqlite3.Connection]:
    """Fresh DB with every migration through 0017 applied."""
    migrations_dir = tmp_path / "migrations"
    for v in range(17):
        _copy_migrations(migrations_dir, v + 1)
    db_path = tmp_path / "v2.db"
    apply_migrations(db_path, migrations_dir=migrations_dir)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return db_path, migrations_dir, conn


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _insert_plan(conn: sqlite3.Connection, config: PlanConfig) -> None:
    record = plan_record_from_config(config, created_at="2026-01-01T00:00:00Z")
    fields = tuple(record.__dataclass_fields__)
    conn.execute(
        f"INSERT INTO {PLAN_TABLE} ({', '.join(fields)}) "
        f"VALUES ({', '.join('?' for _ in fields)})",
        tuple(getattr(record, field) for field in fields),
    )


def _insert_node(conn: sqlite3.Connection, node: QueryNode) -> None:
    record = query_node_record_from_node(node, updated_at="2026-01-01T00:00:00Z")
    fields = tuple(record.__dataclass_fields__)
    conn.execute(
        f"INSERT INTO {NODE_TABLE} ({', '.join(fields)}) "
        f"VALUES ({', '.join('?' for _ in fields)})",
        tuple(getattr(record, field) for field in fields),
    )


def _header_record(plan_id: str, block_number: int) -> CanonicalHeaderReceiptRecord:
    args = {
        "plan_id": plan_id,
        "block_number": block_number,
        "block_hash": "0x" + "ab" * 32,
        "block_timestamp": 1_600_000_000,
        "primary_provider_org": "infura",
        "secondary_provider_org": "blockpi",
        "primary_raw_object_id": "raw_" + "1" * 64,
        "secondary_raw_object_id": "raw_" + "2" * 64,
        "primary_acquisition_id": "acq_" + "3" * 32,
        "secondary_acquisition_id": "acq_" + "4" * 32,
    }
    return CanonicalHeaderReceiptRecord(
        header_receipt_id=compute_canonical_header_receipt_id(**args), **args
    )


def _insert_header(conn: sqlite3.Connection, record: CanonicalHeaderReceiptRecord) -> None:
    fields = tuple(record.__dataclass_fields__)
    conn.execute(
        f"INSERT INTO {HEADER_TABLE} ({', '.join(fields)}) "
        f"VALUES ({', '.join('?' for _ in fields)})",
        tuple(getattr(record, field) for field in fields),
    )


def _insert_leaf(conn: sqlite3.Connection, record: object) -> None:
    fields = tuple(record.__dataclass_fields__)
    json_fields = {
        "addresses": "addresses_json",
        "topics": "topics_json",
        "canonical_header_receipt_ids": "canonical_header_receipt_ids_json",
    }
    columns = tuple(json_fields.get(field, field) for field in fields)
    values = []
    for field in fields:
        if field == "addresses":
            values.append(record.addresses_json)
        elif field == "topics":
            values.append(record.topics_json)
        elif field == "canonical_header_receipt_ids":
            values.append(record.canonical_header_receipt_ids_json)
        else:
            values.append(getattr(record, field))
    conn.execute(
        f"INSERT INTO {LEAF_TABLE} ({', '.join(columns)}) "
        f"VALUES ({', '.join('?' for _ in columns)})",
        tuple(values),
    )


class TestMigration0017Applies:
    def test_applies_forward_only(self, tmp_path: Path) -> None:
        db_path, migrations_dir, conn = _applied_db(tmp_path)
        applied = {
            row[0]
            for row in conn.execute("SELECT filename FROM migration_history")
        }
        assert any(f.startswith("0017_") for f in applied)
        assert not any(f.startswith("0018_") for f in applied)
        conn.close()

    def test_v2_tables_and_normalized_dependencies_present(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in (
            PLAN_TABLE,
            NODE_TABLE,
            LEASE_TABLE,
            LEAF_TABLE,
            HEADER_TABLE,
            COVERAGE_TABLE,
            DEPENDENCY_TABLE,
        ):
            assert table in tables
        conn.close()

    def test_plan_columns_match_record(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        record = plan_record_from_config(PlanConfig())
        expected = {f for f in record.__dataclass_fields__}
        assert _columns(conn, PLAN_TABLE) == expected
        conn.close()

    def test_query_node_columns_match_record(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id = PlanConfig().plan_id()
        domain = QueryDomain(
            start_block=BLOCK,
            end_block=BLOCK + 4999,
            addresses=(POOL_A, POOL_B),
        )
        node = QueryNode(plan_id=plan_id, domain=domain)
        record = query_node_record_from_node(node)
        expected = {f for f in record.__dataclass_fields__}
        assert _columns(conn, NODE_TABLE) == expected
        conn.close()

    def test_leaf_and_header_columns_match_records(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id = PlanConfig().plan_id()
        domain = QueryDomain(start_block=BLOCK, end_block=BLOCK + 9, addresses=(POOL_A,))
        header = compute_canonical_header_receipt_id(
            plan_id=plan_id,
            block_number=domain.end_block,
            block_hash="0x" + "ab" * 32,
            block_timestamp=1_600_000_000,
            primary_provider_org="infura",
            secondary_provider_org="blockpi",
            primary_raw_object_id="raw_" + "1" * 64,
            secondary_raw_object_id="raw_" + "2" * 64,
            primary_acquisition_id="acq_" + "3" * 32,
            secondary_acquisition_id="acq_" + "4" * 32,
        )
        receipt = make_leaf_receipt_record(
            plan_id=plan_id,
            domain=domain,
            log_identity_sha256="a" * 64,
            primary_provider_org="infura",
            secondary_provider_org="blockpi",
            primary_logs_raw_object_id="raw_" + "1" * 64,
            secondary_logs_raw_object_id="raw_" + "2" * 64,
            primary_logs_acquisition_id="acq_" + "3" * 32,
            secondary_logs_acquisition_id="acq_" + "4" * 32,
            log_count=0,
            canonical_header_receipt_ids=[header],
        )
        json_fields = {
            "addresses": "addresses_json",
            "topics": "topics_json",
            "canonical_header_receipt_ids": "canonical_header_receipt_ids_json",
        }
        expected = {
            json_fields.get(f, f) for f in receipt.__dataclass_fields__
        }
        assert _columns(conn, LEAF_TABLE) == expected
        conn.close()

    def test_coverage_columns_match_record(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id = PlanConfig().plan_id()
        cov = prove_pool_topic_coverage(
            RegistryPoolBirth(pool_address=POOL_A, creation_block=BLOCK),
            plan_id=plan_id,
            topic=SWAP_TOPIC,
            validated_receipts=[],
            validated_headers={},
        )
        record = coverage_product_record(cov)
        expected = {f for f in record.__dataclass_fields__}
        assert _columns(conn, COVERAGE_TABLE) == expected
        conn.close()

    def test_check_constraints_enforced(self, tmp_path: Path) -> None:
        """Database rejects the same forged/divergent rows the records reject."""
        _, _, conn = _applied_db(tmp_path)
        record = plan_record_from_config(PlanConfig())
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {PLAN_TABLE} (plan_id, registry_dataset_id, "
                "identity_payload_json, event_provider_orgs_json, "
                "metadata_provider_orgs_json, root_block_size, initial_cohort_size, "
                "deployment_block, cutoff_block, plan_schema_version, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "plan_" + "0" * 64,
                    record.registry_dataset_id,
                    record.identity_payload_json,
                    record.event_provider_orgs_json,
                    record.metadata_provider_orgs_json,
                    record.root_block_size,
                    16,  # not a candidate cohort -> CHECK violation
                    record.deployment_block,
                    record.cutoff_block,
                    record.plan_schema_version,
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {NODE_TABLE} (plan_id, domain_id, start_block, "
                "end_block, addresses_json, topics_json, status, parent_domain_id, "
                "split_reason, attempt, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    PlanConfig().plan_id(),
                    "qd_" + "0" * 64,
                    BLOCK,
                    BLOCK + 9,
                    '["' + POOL_A + '"]',
                    '["' + SWAP_TOPIC + '"]',
                    "BOGUS",
                    None,
                    None,
                    0,
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()

    def test_inline_foreign_keys_are_active_and_reject_orphans(
        self, tmp_path: Path
    ) -> None:
        _, _, conn = _applied_db(tmp_path)
        foreign_keys = {
            table: {
                (row[3], row[2], row[4])
                for row in conn.execute(f"PRAGMA foreign_key_list({table})")
            }
            for table in (NODE_TABLE, LEASE_TABLE, LEAF_TABLE, HEADER_TABLE, COVERAGE_TABLE)
        }
        assert ("plan_id", PLAN_TABLE, "plan_id") in foreign_keys[NODE_TABLE]
        assert ("domain_id", NODE_TABLE, "domain_id") in foreign_keys[LEASE_TABLE]
        assert ("domain_id", NODE_TABLE, "domain_id") in foreign_keys[LEAF_TABLE]
        assert ("plan_id", PLAN_TABLE, "plan_id") in foreign_keys[HEADER_TABLE]
        assert ("plan_id", PLAN_TABLE, "plan_id") in foreign_keys[COVERAGE_TABLE]

        unknown_plan = PlanConfig().plan_id()
        orphan_node = QueryNode(
            plan_id=unknown_plan,
            domain=QueryDomain(
                start_block=BLOCK, end_block=BLOCK + 1, addresses=(POOL_A,)
            ),
        )
        with pytest.raises(sqlite3.IntegrityError):
            _insert_node(conn, orphan_node)

        config = PlanConfig()
        _insert_plan(conn, config)
        parent = QueryNode(
            plan_id=config.plan_id(),
            domain=QueryDomain(
                start_block=BLOCK, end_block=BLOCK + 9, addresses=(POOL_A,)
            ),
        )
        missing_parent = QueryNode(
            plan_id=config.plan_id(),
            domain=QueryDomain(
                start_block=BLOCK + 10, end_block=BLOCK + 19, addresses=(POOL_A,)
            ),
            parent_domain_id="qd_" + "0" * 64,
            split_reason="manual",
        )
        with pytest.raises(sqlite3.IntegrityError):
            _insert_node(conn, missing_parent)
        _insert_node(conn, parent)

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {LEASE_TABLE} "
                "(plan_id, domain_id, worker_id, lease_token, leased_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    config.plan_id(),
                    "qd_" + "f" * 64,
                    "worker",
                    "lease",
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:01:00Z",
                ),
            )

        header = _header_record(config.plan_id(), parent.domain.end_block)
        _insert_header(conn, header)
        leaf = make_leaf_receipt_record(
            plan_id=config.plan_id(),
            domain=parent.domain,
            log_identity_sha256="a" * 64,
            primary_provider_org="infura",
            secondary_provider_org="blockpi",
            primary_logs_raw_object_id="raw_" + "1" * 64,
            secondary_logs_raw_object_id="raw_" + "2" * 64,
            primary_logs_acquisition_id="acq_" + "3" * 32,
            secondary_logs_acquisition_id="acq_" + "4" * 32,
            log_count=0,
            canonical_header_receipt_ids=[header.header_receipt_id],
        )
        _insert_leaf(conn, leaf)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {DEPENDENCY_TABLE} "
                "(plan_id, leaf_receipt_id, header_receipt_id) VALUES (?, ?, ?)",
                (config.plan_id(), leaf.leaf_receipt_id, "chdr_" + "0" * 64),
            )
        conn.close()

    def test_idempotent_reapply(self, tmp_path: Path) -> None:
        db_path, migrations_dir, conn = _applied_db(tmp_path)
        conn.close()
        apply_migrations(db_path, migrations_dir=migrations_dir)
        conn = sqlite3.connect(str(db_path))
        count = conn.execute(
            "SELECT COUNT(*) FROM migration_history WHERE filename LIKE '0017_%'"
        ).fetchone()[0]
        assert count == 1
        conn.close()
