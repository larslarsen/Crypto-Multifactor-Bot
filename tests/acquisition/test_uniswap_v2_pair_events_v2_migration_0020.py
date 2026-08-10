"""DEX-003 — forward-only migration 0020 production foundation (additive).

No network. Proves 0020 adds root manifest + log candidate tables/indexes without
weakening 0017-0019. Populated upgrade preserves every 0017-0019 table class.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from cryptofactors.acquisition.uniswap_v2_pair_events_v2 import (
    PlanConfig,
    QueryDomain,
    QueryNode,
    plan_record_from_config,
    query_node_record_from_node,
)
from cryptofactors.acquisition.uniswap_v2_pair_events_v2_engine import SOURCE_ID
from cryptofactors.catalog.runner import apply_migrations

REPO_MIGRATIONS = Path(__file__).resolve().parent.parent.parent / "sql" / "migrations"

PLAN_TABLE = "uniswap_v2_pair_event_v2_plan"
NODE_TABLE = "uniswap_v2_pair_event_v2_query_node"
MANIFEST = "uniswap_v2_pair_event_v2_root_manifest"
CANDIDATE = "uniswap_v2_pair_event_v2_log_candidate"
CAND_BLOCK = "uniswap_v2_pair_event_v2_log_candidate_block"
POOL = "0x" + "11" * 20


def _copy_through(dst: Path, through: int) -> Path:
    dst.mkdir(parents=True, exist_ok=True)
    for v in range(1, through + 1):
        src = next(REPO_MIGRATIONS.glob(f"{v:04d}_*.sql"))
        shutil.copy(src, dst / src.name)
    return dst


def _apply(tmp_path: Path, through: int) -> tuple[Path, sqlite3.Connection]:
    migrations_dir = _copy_through(tmp_path / "migrations", through)
    db_path = tmp_path / f"v2_{through}.db"
    apply_migrations(db_path, migrations_dir=migrations_dir)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return db_path, conn


def _insert_plan(conn: sqlite3.Connection, config: PlanConfig | None = None) -> str:
    cfg = config or PlanConfig(initial_cohort_size=8)
    record = plan_record_from_config(cfg, created_at="2026-01-01T00:00:00Z")
    fields = tuple(record.__dataclass_fields__)
    conn.execute(
        f"INSERT INTO {PLAN_TABLE} ({', '.join(fields)}) "
        f"VALUES ({', '.join('?' for _ in fields)})",
        tuple(getattr(record, field) for field in fields),
    )
    return record.plan_id


def _insert_node(conn: sqlite3.Connection, plan_id: str) -> tuple[str, QueryDomain]:
    domain = QueryDomain(
        start_block=10_008_355,
        end_block=10_013_354,
        addresses=(POOL,),
    )
    node = QueryNode(plan_id=plan_id, domain=domain)
    record = query_node_record_from_node(node, updated_at="2026-01-01T00:00:00Z")
    fields = tuple(record.__dataclass_fields__)
    conn.execute(
        f"INSERT INTO {NODE_TABLE} ({', '.join(fields)}) "
        f"VALUES ({', '.join('?' for _ in fields)})",
        tuple(getattr(record, field) for field in fields),
    )
    return node.domain_id, domain


def _insert_raw_pair(conn: sqlite3.Connection, *, tag: str) -> tuple[str, str]:
    """Insert source + raw_object + SUCCEEDED raw_acquisition pair."""
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        "INSERT OR IGNORE INTO source ("
        "source_id, source_type, official_url, terms_class, config_json, created_at"
        ") VALUES (?,?,?,?,?,?)",
        (SOURCE_ID, "rpc", None, None, "{}", now),
    )
    digest = (tag.encode().hex() * 32)[:64]
    raw_id = "raw_" + digest
    acq_id = "acq_" + (tag.encode().hex() * 16)[:32]
    uri = f"raw/sha256/{digest[0:2]}/{digest[2:4]}/{digest}"
    conn.execute(
        "INSERT OR IGNORE INTO raw_object ("
        "raw_object_id, source_id, sha256, byte_size, storage_uri, original_name, "
        "request_json, response_metadata_json, source_checksum, acquired_at, "
        "event_start, event_end, status"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            raw_id,
            SOURCE_ID,
            digest,
            2,
            uri,
            "x.json",
            "{}",
            "{}",
            None,
            now,
            None,
            None,
            "ACTIVE",
        ),
    )
    conn.execute(
        "INSERT INTO raw_acquisition ("
        "acquisition_id, source_id, raw_object_id, request_json, response_metadata_json, "
        "original_name, checksum_algorithm, checksum_value, checksum_verification, "
        "acquired_at, event_start, event_end, status, failure_json, created_at, updated_at"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            acq_id,
            SOURCE_ID,
            raw_id,
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}),
            json.dumps(
                {
                    "provider_org": "infura",
                    "status_code": 200,
                    "response_bytes": 2,
                    "retained_bytes": 2,
                    "truncated": False,
                    "error_kind": None,
                    "error_detail": None,
                }
            ),
            "x.json",
            None,
            None,
            "absent",
            now,
            None,
            None,
            "SUCCEEDED",
            None,
            now,
            now,
        ),
    )
    return acq_id, raw_id


def _populate_all_v2_tables(conn: sqlite3.Connection) -> dict[str, int]:
    """Insert at least one row into every 0017-0019 v2 table class."""
    now = "2026-01-01T00:00:00Z"
    plan_id = _insert_plan(conn)
    domain_id, domain = _insert_node(conn, plan_id)
    acq_p, raw_p = _insert_raw_pair(conn, tag="1")
    acq_s, raw_s = _insert_raw_pair(conn, tag="2")
    conn.execute(
        "INSERT INTO uniswap_v2_pair_event_v2_execution_policy ("
        "policy_id, plan_id, identity_payload_json, schema_version, created_at"
        ") VALUES (?,?,?,?,?)",
        ("pol_" + "a" * 64, plan_id, json.dumps({"plan_id": plan_id}), "1", now),
    )
    conn.execute(
        "INSERT INTO uniswap_v2_pair_event_v2_query_lease ("
        "plan_id, domain_id, worker_id, lease_token, leased_at, expires_at"
        ") VALUES (?,?,?,?,?,?)",
        (plan_id, domain_id, "w1", "tok", now, now),
    )
    conn.execute(
        "INSERT INTO uniswap_v2_pair_event_v2_chain_identity_receipt ("
        "chain_identity_receipt_id, plan_id, chain_id, primary_provider_org, "
        "secondary_provider_org, primary_raw_object_id, secondary_raw_object_id, "
        "primary_acquisition_id, secondary_acquisition_id, schema_version, completed_at"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            "chain_" + "b" * 64,
            plan_id,
            1,
            "infura",
            "blockpi",
            raw_p,
            raw_s,
            acq_p,
            acq_s,
            "1",
            now,
        ),
    )
    conn.execute(
        "INSERT INTO uniswap_v2_pair_event_v2_engine_event ("
        "event_id, schema_version, plan_id, domain_id, attempt, event_kind, "
        "failure_class, decision, provider_org, request_json, "
        "primary_raw_object_id, secondary_raw_object_id, "
        "primary_acquisition_id, secondary_acquisition_id, detail_json, created_at"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "evt_" + "c" * 64,
            "1",
            plan_id,
            domain_id,
            0,
            "retry_decision",
            "transport",
            "retry",
            None,
            None,
            None,
            None,
            None,
            None,
            "{}",
            now,
        ),
    )
    conn.execute(
        "INSERT INTO uniswap_v2_pair_event_v2_terminal_receipt ("
        "terminal_receipt_id, plan_id, domain_id, terminal_mode, attempt, "
        "schema_version, completed_at"
        ") VALUES (?,?,?,?,?,?,?)",
        ("term_" + "d" * 64, plan_id, domain_id, "lease_expired", 3, "1", now),
    )
    # Header + leaf + dependency (composite raw FKs)
    from cryptofactors.acquisition.uniswap_v2_pair_events_v2 import (
        compute_canonical_header_receipt_id,
        compute_leaf_receipt_id,
    )

    header_id = compute_canonical_header_receipt_id(
        plan_id=plan_id,
        block_number=domain.end_block,
        block_hash="0x" + "ab" * 32,
        block_timestamp=1,
        primary_provider_org="infura",
        secondary_provider_org="blockpi",
        primary_raw_object_id=raw_p,
        secondary_raw_object_id=raw_s,
        primary_acquisition_id=acq_p,
        secondary_acquisition_id=acq_s,
    )
    conn.execute(
        "INSERT INTO uniswap_v2_pair_event_v2_canonical_header_receipt ("
        "header_receipt_id, plan_id, block_number, block_hash, block_timestamp, "
        "primary_provider_org, secondary_provider_org, "
        "primary_raw_object_id, secondary_raw_object_id, "
        "primary_acquisition_id, secondary_acquisition_id, "
        "receipt_schema_version, completed_at"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            header_id,
            plan_id,
            domain.end_block,
            "0x" + "ab" * 32,
            1,
            "infura",
            "blockpi",
            raw_p,
            raw_s,
            acq_p,
            acq_s,
            "1",
            now,
        ),
    )
    leaf_id = compute_leaf_receipt_id(
        plan_id=plan_id,
        domain_id=domain_id,
        start_block=domain.start_block,
        end_block=domain.end_block,
        addresses=domain.addresses,
        topics=domain.topics,
        log_identity_sha256="e" * 64,
        primary_provider_org="infura",
        secondary_provider_org="blockpi",
        primary_logs_raw_object_id=raw_p,
        secondary_logs_raw_object_id=raw_s,
        primary_logs_acquisition_id=acq_p,
        secondary_logs_acquisition_id=acq_s,
        log_count=0,
        canonical_header_receipt_ids=(header_id,),
    )
    conn.execute(
        "INSERT INTO uniswap_v2_pair_event_v2_leaf_receipt ("
        "leaf_receipt_id, plan_id, domain_id, start_block, end_block, "
        "addresses_json, topics_json, primary_provider_org, secondary_provider_org, "
        "primary_logs_raw_object_id, secondary_logs_raw_object_id, "
        "primary_logs_acquisition_id, secondary_logs_acquisition_id, "
        "log_count, log_identity_sha256, canonical_header_receipt_ids_json, "
        "log_identity_version, receipt_schema_version, reconciliation_status, completed_at"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            leaf_id,
            plan_id,
            domain_id,
            domain.start_block,
            domain.end_block,
            json.dumps(list(domain.addresses)),
            json.dumps(list(domain.topics)),
            "infura",
            "blockpi",
            raw_p,
            raw_s,
            acq_p,
            acq_s,
            0,
            "e" * 64,
            json.dumps([header_id]),
            "2",
            "1",
            "AGREED",
            now,
        ),
    )
    conn.execute(
        "INSERT INTO uniswap_v2_pair_event_v2_leaf_header_dependency ("
        "plan_id, leaf_receipt_id, header_receipt_id"
        ") VALUES (?,?,?)",
        (plan_id, leaf_id, header_id),
    )
    conn.execute(
        "INSERT INTO uniswap_v2_pair_event_v2_coverage_product ("
        "plan_id, pool_address, topic, expected_start, expected_end, "
        "expected_block_count, covered_block_count, first_covered_block, "
        "last_covered_block, leaf_count, has_gap, has_overlap, "
        "supporting_receipts_root, coverage_hash, is_complete, schema_version"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            plan_id,
            POOL,
            domain.topics[0],
            domain.start_block,
            domain.end_block,
            domain.end_block - domain.start_block + 1,
            0,
            None,
            None,
            0,
            1,
            0,
            "f" * 64,
            "0" * 64,
            0,
            "1",
        ),
    )
    conn.commit()
    counts = {}
    for table in (
        PLAN_TABLE,
        NODE_TABLE,
        "uniswap_v2_pair_event_v2_query_lease",
        "uniswap_v2_pair_event_v2_execution_policy",
        "uniswap_v2_pair_event_v2_chain_identity_receipt",
        "uniswap_v2_pair_event_v2_engine_event",
        "uniswap_v2_pair_event_v2_terminal_receipt",
        "uniswap_v2_pair_event_v2_canonical_header_receipt",
        "uniswap_v2_pair_event_v2_leaf_receipt",
        "uniswap_v2_pair_event_v2_leaf_header_dependency",
        "uniswap_v2_pair_event_v2_coverage_product",
        "raw_object",
        "raw_acquisition",
    ):
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert counts[table] >= 1, table
    return counts


def test_0020_fresh_apply_creates_tables_and_indexes(tmp_path: Path) -> None:
    _db, conn = _apply(tmp_path, 20)
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert MANIFEST in tables
    assert CANDIDATE in tables
    assert CAND_BLOCK in tables
    assert PLAN_TABLE in tables
    assert NODE_TABLE in tables
    assert "uniswap_v2_pair_event_v2_header_backlog" in tables
    assert "uniswap_v2_pair_event_v2_header_backlog_metric" in tables
    assert "uniswap_v2_pair_event_v2_plan_resume_session" in tables
    indexes = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    assert "idx_uniswap_v2_pair_event_v2_query_node_claim_domain" in indexes
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


def test_0020_populated_upgrade_preserves_all_0017_0019_tables(tmp_path: Path) -> None:
    migrations_dir = _copy_through(tmp_path / "migrations", 19)
    db_path = tmp_path / "populated.db"
    apply_migrations(db_path, migrations_dir=migrations_dir)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    before = _populate_all_v2_tables(conn)
    identity = conn.execute(
        f"SELECT identity_payload_json FROM {PLAN_TABLE}"
    ).fetchone()[0]
    conn.close()

    shutil.copy(
        next(REPO_MIGRATIONS.glob("0020_*.sql")),
        migrations_dir / next(REPO_MIGRATIONS.glob("0020_*.sql")).name,
    )
    apply_migrations(db_path, migrations_dir=migrations_dir)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    for table, count in before.items():
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == count
    after_identity = conn.execute(
        f"SELECT identity_payload_json FROM {PLAN_TABLE}"
    ).fetchone()[0]
    assert after_identity == identity
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert MANIFEST in {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()


def test_0020_candidate_fk_rejects_orphan(tmp_path: Path) -> None:
    _db, conn = _apply(tmp_path, 20)
    plan_id = _insert_plan(conn)
    _insert_node(conn, plan_id)
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            f"INSERT INTO {CANDIDATE} ("
            "candidate_id, plan_id, domain_id, attempt, log_identity_sha256, log_count, "
            "primary_provider_org, secondary_provider_org, "
            "primary_logs_raw_object_id, secondary_logs_raw_object_id, "
            "primary_logs_acquisition_id, secondary_logs_acquisition_id, "
            "request_json, created_at"
            ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "lcand_" + "1" * 64,
                plan_id,
                "qd_" + "f" * 64,
                0,
                "c" * 64,
                0,
                "infura",
                "blockpi",
                "raw_" + "1" * 64,
                "raw_" + "2" * 64,
                "acq_" + "3" * 32,
                "acq_" + "4" * 32,
                "{}",
                "t0",
            ),
        )
    conn.close()


def test_0020_atomic_rollback_on_bad_migration(tmp_path: Path) -> None:
    migrations_dir = _copy_through(tmp_path / "migrations", 19)
    db_path = tmp_path / "rollback.db"
    apply_migrations(db_path, migrations_dir=migrations_dir)
    conn = sqlite3.connect(str(db_path))
    _populate_all_v2_tables(conn)
    conn.close()

    real = next(REPO_MIGRATIONS.glob("0020_*.sql")).read_text(encoding="utf-8")
    bad_name = "0020_uniswap_v2_pair_event_v2_production_foundation.sql"
    (migrations_dir / bad_name).write_text(
        real + "\nSELECT RAISE(ABORT, 'forced_0020_failure');\n",
        encoding="utf-8",
    )
    with pytest.raises(Exception):
        apply_migrations(db_path, migrations_dir=migrations_dir)
    conn = sqlite3.connect(str(db_path))
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert MANIFEST not in tables
    assert CANDIDATE not in tables
    assert conn.execute(f"SELECT COUNT(*) FROM {PLAN_TABLE}").fetchone()[0] >= 1
    history = [
        r[0]
        for r in conn.execute(
            "SELECT filename FROM migration_history ORDER BY filename"
        ).fetchall()
    ]
    assert not any("0020_" in h for h in history)
    conn.close()


def test_0020_claim_index_no_temp_btree_for_domain_order(tmp_path: Path) -> None:
    _db, conn = _apply(tmp_path, 20)
    plan_id = _insert_plan(conn)
    _insert_node(conn, plan_id)
    conn.commit()
    plan_rows = conn.execute(
        "EXPLAIN QUERY PLAN "
        f"SELECT * FROM {NODE_TABLE} n "
        "WHERE n.plan_id = ? AND n.status = 'PENDING' AND n.attempt < 3 "
        "ORDER BY n.domain_id LIMIT 1",
        (plan_id,),
    ).fetchall()
    # sqlite3.Row str() is only the object repr; use EXPLAIN detail column values.
    plan_parts: list[str] = []
    for row in plan_rows:
        if hasattr(row, "keys") and "detail" in row.keys():
            plan_parts.append(str(row["detail"]))
        else:
            plan_parts.append(" ".join(str(v) for v in tuple(row)))
    plan_text = " ".join(plan_parts).upper()
    assert "TEMP B-TREE" not in plan_text
    assert "CLAIM_DOMAIN" in plan_text or "USING INDEX" in plan_text
    info = conn.execute(
        "PRAGMA index_info(idx_uniswap_v2_pair_event_v2_query_node_claim_domain)"
    ).fetchall()
    cols = [r[2] for r in info]
    assert cols == ["plan_id", "status", "domain_id"]
    conn.close()
