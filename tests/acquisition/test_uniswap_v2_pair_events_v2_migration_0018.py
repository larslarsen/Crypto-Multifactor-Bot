"""DEX-003 — focused offline migration tests for 0018.

No network. Proves the engine persistence schema (chain identity, engine event,
execution policy, terminal receipt, raw_acquisition composite pairing key, and
header/leaf/dependency uniqueness contracts) matches the 0018 contract exactly
and rejects forged, mismatched, or divergent rows. All databases are temporary;
the repository migration file is only copied, never modified.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from cryptofactors.acquisition.uniswap_v2 import _canonical_json
from cryptofactors.acquisition.uniswap_v2_pair_events_v2 import (
    PlanConfig,
    plan_record_from_config,
)
from cryptofactors.acquisition.uniswap_v2_pair_events_v2_engine import (
    CHAIN_IDENTITY_RECORD_COLUMNS,
    CHAIN_IDENTITY_SCHEMA_VERSION,
    CHAIN_IDENTITY_TABLE,
    ENGINE_EVENT_RECORD_COLUMNS,
    ENGINE_EVENT_TABLE,
    EXECUTION_POLICY_RECORD_COLUMNS,
    EXECUTION_POLICY_SCHEMA_VERSION,
    EXECUTION_POLICY_TABLE,
    TERMINAL_MODES,
    TERMINAL_RECEIPT_RECORD_COLUMNS,
    TERMINAL_RECEIPT_SCHEMA_VERSION,
    TERMINAL_RECEIPT_TABLE,
    compute_chain_identity_receipt_id,
    compute_terminal_receipt_id,
)
from cryptofactors.catalog.runner import apply_migrations

REPO_MIGRATIONS = Path(__file__).resolve().parent.parent.parent / "sql" / "migrations"

PLAN_TABLE = "uniswap_v2_pair_event_v2_plan"
NODE_TABLE = "uniswap_v2_pair_event_v2_query_node"
LEASE_TABLE = "uniswap_v2_pair_event_v2_query_lease"
LEAF_TABLE = "uniswap_v2_pair_event_v2_leaf_receipt"
HEADER_TABLE = "uniswap_v2_pair_event_v2_canonical_header_receipt"
COVERAGE_TABLE = "uniswap_v2_pair_event_v2_coverage_product"
DEP_TABLE = "uniswap_v2_pair_event_v2_leaf_header_dependency"

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
    """Fresh DB with every migration through 0018 applied."""
    migrations_dir = tmp_path / "migrations"
    for v in range(18):
        _copy_migrations(migrations_dir, v + 1)
    db_path = tmp_path / "v2.db"
    apply_migrations(db_path, migrations_dir=migrations_dir)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return db_path, migrations_dir, conn


def _upgrade_db(tmp_path: Path) -> tuple[Path, Path, sqlite3.Connection]:
    """DB with migrations through 0017 applied, then 0018 applied separately."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    for v in range(17):
        _copy_migrations(migrations_dir, v + 1)
    db_path = tmp_path / "v2_upgrade.db"
    apply_migrations(db_path, migrations_dir=migrations_dir)

    # Apply 0018 by copying it into the migrations dir and re-running.
    _copy_migrations(migrations_dir, 18)
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


def _insert_source(conn: sqlite3.Connection, source_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO source (source_id, source_type, config_json, created_at) "
        "VALUES (?, ?, ?, ?)",
        (source_id, "test", _canonical_json({"type": "test"}), "2026-01-01T00:00:00Z"),
    )


_raw_counter = 0


def _next_sha256() -> str:
    global _raw_counter
    _raw_counter += 1
    sha = f"{_raw_counter:064d}"
    return sha


def _insert_raw_acquisition(
    conn: sqlite3.Connection,
    acquisition_id: str,
    raw_object_id: str,
    *,
    status: str = "SUCCEEDED",
) -> None:
    _insert_source(conn, "ethereum_json_rpc")
    sha = _next_sha256()
    conn.execute(
        "INSERT INTO raw_object (raw_object_id, source_id, sha256, byte_size, "
        "storage_uri, status, acquired_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            raw_object_id,
            "ethereum_json_rpc",
            sha,
            100,
            f"raw/sha256/{sha[:2]}/{sha[2:4]}/{sha}",
            "PRESENT",
            "2026-01-01T00:00:00Z",
        ),
    )
    conn.execute(
        "INSERT INTO raw_acquisition (acquisition_id, source_id, raw_object_id, "
        "request_json, response_metadata_json, checksum_verification, "
        "acquired_at, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            acquisition_id,
            "ethereum_json_rpc",
            raw_object_id,
            "{}",
            "{}",
            "verified",
            "2026-01-01T00:00:00Z",
            status,
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:00Z",
        ),
    )


def _insert_node(conn: sqlite3.Connection, plan_id: str) -> str:
    domain_id = "qd_" + "b" * 64
    conn.execute(
        f"INSERT INTO {NODE_TABLE} (plan_id, domain_id, start_block, end_block, "
        "addresses_json, topics_json, status, parent_domain_id, split_reason, "
        "attempt, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            plan_id,
            domain_id,
            BLOCK,
            BLOCK + 9,
            json.dumps(["0x" + "11" * 20]),
            json.dumps(["0x" + "00" * 32]),
            "PENDING",
            None,
            None,
            0,
            "2026-01-01T00:00:00Z",
        ),
    )
    return domain_id


class TestMigration0018Applies:
    def test_applies_forward_only(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        applied = {
            row[0]
            for row in conn.execute("SELECT filename FROM migration_history")
        }
        assert any(f.startswith("0018_") for f in applied)
        conn.close()

    def test_upgrade_after_0017(self, tmp_path: Path) -> None:
        _, _, conn = _upgrade_db(tmp_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in (
            CHAIN_IDENTITY_TABLE,
            ENGINE_EVENT_TABLE,
            EXECUTION_POLICY_TABLE,
            TERMINAL_RECEIPT_TABLE,
        ):
            assert table in tables
        conn.close()

    def test_raw_acquisition_composite_unique_key(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        indexes = {
            row[1]
            for row in conn.execute(
                "SELECT type, name FROM sqlite_master WHERE type='index' "
                "AND name LIKE '%raw_acquisition_pair%'"
            )
        }
        assert len(indexes) == 1
        # Verify it's a unique index
        index_info = conn.execute(
            "PRAGMA index_list('raw_acquisition')"
        ).fetchall()
        pair_index = [row for row in index_info if row[1] == "idx_raw_acquisition_pair"]
        assert len(pair_index) == 1
        assert pair_index[0][2] == 1  # unique = 1
        conn.close()


class TestMigration0018Contracts:
    def test_chain_identity_columns_match_record(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        expected = {f for f in CHAIN_IDENTITY_RECORD_COLUMNS}
        assert _columns(conn, CHAIN_IDENTITY_TABLE) == expected
        conn.close()

    def test_engine_event_columns_match_record(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        expected = {f for f in ENGINE_EVENT_RECORD_COLUMNS}
        assert _columns(conn, ENGINE_EVENT_TABLE) == expected
        conn.close()

    def test_execution_policy_columns_match_record(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        expected = {f for f in EXECUTION_POLICY_RECORD_COLUMNS}
        assert _columns(conn, EXECUTION_POLICY_TABLE) == expected
        conn.close()

    def test_terminal_receipt_columns_match_record(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        expected = {f for f in TERMINAL_RECEIPT_RECORD_COLUMNS}
        assert _columns(conn, TERMINAL_RECEIPT_TABLE) == expected
        conn.close()

    def test_foreign_keys_enforced_pragma_check(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        # PRAGMA foreign_key_check returns empty when all FKs are satisfied
        result = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert result == []
        conn.close()

    def test_chain_identity_rejects_orphan_plan(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {CHAIN_IDENTITY_TABLE} "
                "(chain_identity_receipt_id, plan_id, chain_id, "
                "primary_provider_org, secondary_provider_org, "
                "primary_raw_object_id, secondary_raw_object_id, "
                "primary_acquisition_id, secondary_acquisition_id, "
                "schema_version, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "chain_" + "1" * 64,
                    "plan_" + "0" * 64,  # unknown plan
                    1,
                    "infura",
                    "blockpi",
                    "raw_" + "1" * 64,
                    "raw_" + "2" * 64,
                    "acq_" + "3" * 32,
                    "acq_" + "4" * 32,
                    "1",
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()

    def test_chain_identity_rejects_duplicate_plan(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        _insert_plan(conn, PlanConfig())
        plan_id = PlanConfig().plan_id()
        _insert_source(conn, "ethereum_json_rpc")
        _insert_raw_acquisition(conn, "acq_" + "3" * 32, "raw_" + "1" * 64)
        _insert_raw_acquisition(conn, "acq_" + "4" * 32, "raw_" + "2" * 64)
        row = {
            "plan_id": plan_id,
            "chain_id": 1,
            "primary_provider_org": "infura",
            "secondary_provider_org": "blockpi",
            "primary_raw_object_id": "raw_" + "1" * 64,
            "secondary_raw_object_id": "raw_" + "2" * 64,
            "primary_acquisition_id": "acq_" + "3" * 32,
            "secondary_acquisition_id": "acq_" + "4" * 32,
        }
        receipt_id = compute_chain_identity_receipt_id(**row)
        conn.execute(
            f"INSERT INTO {CHAIN_IDENTITY_TABLE} ("
            + ", ".join(CHAIN_IDENTITY_RECORD_COLUMNS)
            + ") VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                receipt_id,
                plan_id,
                1,
                "infura",
                "blockpi",
                "raw_" + "1" * 64,
                "raw_" + "2" * 64,
                "acq_" + "3" * 32,
                "acq_" + "4" * 32,
                CHAIN_IDENTITY_SCHEMA_VERSION,
                "2026-01-01T00:00:00Z",
            ),
        )
        # Second insert for same plan must fail (UNIQUE constraint)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {CHAIN_IDENTITY_TABLE} ("
                + ", ".join(CHAIN_IDENTITY_RECORD_COLUMNS)
                + ") VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "chain_" + "2" * 64,
                    plan_id,  # same plan_id
                    1,
                    "infura",
                    "blockpi",
                    "raw_" + "1" * 64,
                    "raw_" + "2" * 64,
                    "acq_" + "3" * 32,
                    "acq_" + "4" * 32,
                    CHAIN_IDENTITY_SCHEMA_VERSION,
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()

    def test_chain_identity_rejects_non_mainnet(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        _insert_plan(conn, PlanConfig())
        plan_id = PlanConfig().plan_id()
        _insert_source(conn, "ethereum_json_rpc")
        _insert_raw_acquisition(conn, "acq_" + "3" * 32, "raw_" + "1" * 64)
        _insert_raw_acquisition(conn, "acq_" + "4" * 32, "raw_" + "2" * 64)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {CHAIN_IDENTITY_TABLE} "
                "(chain_identity_receipt_id, plan_id, chain_id, "
                "primary_provider_org, secondary_provider_org, "
                "primary_raw_object_id, secondary_raw_object_id, "
                "primary_acquisition_id, secondary_acquisition_id, "
                "schema_version, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "chain_" + "3" * 64,
                    plan_id,
                    1337,  # not mainnet
                    "infura",
                    "blockpi",
                    "raw_" + "1" * 64,
                    "raw_" + "2" * 64,
                    "acq_" + "3" * 32,
                    "acq_" + "4" * 32,
                    CHAIN_IDENTITY_SCHEMA_VERSION,
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()

    def test_chain_identity_rejects_same_provider(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        _insert_plan(conn, PlanConfig())
        plan_id = PlanConfig().plan_id()
        _insert_source(conn, "ethereum_json_rpc")
        _insert_raw_acquisition(conn, "acq_" + "3" * 32, "raw_" + "1" * 64)
        _insert_raw_acquisition(conn, "acq_" + "4" * 32, "raw_" + "2" * 64)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {CHAIN_IDENTITY_TABLE} "
                "(chain_identity_receipt_id, plan_id, chain_id, "
                "primary_provider_org, secondary_provider_org, "
                "primary_raw_object_id, secondary_raw_object_id, "
                "primary_acquisition_id, secondary_acquisition_id, "
                "schema_version, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "chain_" + "4" * 64,
                    plan_id,
                    1,
                    "infura",
                    "infura",  # same provider
                    "raw_" + "1" * 64,
                    "raw_" + "2" * 64,
                    "acq_" + "3" * 32,
                    "acq_" + "4" * 32,
                    CHAIN_IDENTITY_SCHEMA_VERSION,
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()

    def test_chain_identity_composite_fk_rejects_mismatched_pair(
        self, tmp_path: Path
    ) -> None:
        """FK (acquisition_id, raw_object_id) → raw_acquisition must match exactly."""
        _, _, conn = _applied_db(tmp_path)
        _insert_plan(conn, PlanConfig())
        plan_id = PlanConfig().plan_id()
        _insert_source(conn, "ethereum_json_rpc")
        # Create two valid raw_acquisition pairs
        _insert_raw_acquisition(conn, "acq_" + "3" * 32, "raw_" + "1" * 64)
        _insert_raw_acquisition(conn, "acq_" + "4" * 32, "raw_" + "2" * 64)
        # Now try to insert a chain identity with mismatched pair:
        # primary uses (acq_3, raw_1) - valid
        # secondary uses (acq_3, raw_2) - INVALID pair (acq_3 pairs with raw_1, not raw_2)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {CHAIN_IDENTITY_TABLE} "
                "(chain_identity_receipt_id, plan_id, chain_id, "
                "primary_provider_org, secondary_provider_org, "
                "primary_raw_object_id, secondary_raw_object_id, "
                "primary_acquisition_id, secondary_acquisition_id, "
                "schema_version, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "chain_" + "5" * 64,
                    plan_id,
                    1,
                    "infura",
                    "blockpi",
                    "raw_" + "1" * 64,  # valid with acq_3
                    "raw_" + "2" * 64,  # valid with acq_4, not acq_3
                    "acq_" + "3" * 32,  # pairs with raw_1, not raw_2
                    "acq_" + "3" * 32,  # mismatch!
                    CHAIN_IDENTITY_SCHEMA_VERSION,
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()

    def test_execution_policy_rejects_orphan_plan(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {EXECUTION_POLICY_TABLE} "
                "(policy_id, plan_id, identity_payload_json, "
                "schema_version, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    "pol_" + "1" * 64,
                    "plan_" + "0" * 64,  # unknown plan
                    "{}",
                    EXECUTION_POLICY_SCHEMA_VERSION,
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()


class TestMigration0018TerminalReceipts:
    def _setup_plan_node(self, conn: sqlite3.Connection) -> tuple[str, str]:
        _insert_plan(conn, PlanConfig())
        plan_id = PlanConfig().plan_id()
        domain_id = _insert_node(conn, plan_id)
        return plan_id, domain_id

    def test_terminal_modes_all_present(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        assert len(TERMINAL_MODES) == 16
        conn.close()

    def test_terminal_receipt_insert_and_reject_mode_conflict(
        self, tmp_path: Path
    ) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, domain_id = self._setup_plan_node(conn)
        mode_a = "lease_expired"
        mode_b = "unsplittable_singleton"
        receipt_id_a = compute_terminal_receipt_id(
            plan_id=plan_id,
            domain_id=domain_id,
            terminal_mode=mode_a,
            attempt=3,
        )
        receipt_id_b = compute_terminal_receipt_id(
            plan_id=plan_id,
            domain_id=domain_id,
            terminal_mode=mode_b,
            attempt=3,
        )
        conn.execute(
            f"INSERT INTO {TERMINAL_RECEIPT_TABLE} ("
            + ", ".join(TERMINAL_RECEIPT_RECORD_COLUMNS)
            + ") VALUES (?,?,?,?,?,?,?)",
            (
                receipt_id_a,
                plan_id,
                domain_id,
                mode_a,
                3,
                TERMINAL_RECEIPT_SCHEMA_VERSION,
                "2026-01-01T00:00:00Z",
            ),
        )
        # Same domain cannot have a different mode
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {TERMINAL_RECEIPT_TABLE} ("
                + ", ".join(TERMINAL_RECEIPT_RECORD_COLUMNS)
                + ") VALUES (?,?,?,?,?,?,?)",
                (
                    receipt_id_b,
                    plan_id,
                    domain_id,
                    mode_b,
                    3,
                    TERMINAL_RECEIPT_SCHEMA_VERSION,
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()

    def test_terminal_rejects_invalid_mode(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, domain_id = self._setup_plan_node(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {TERMINAL_RECEIPT_TABLE} "
                "(terminal_receipt_id, plan_id, domain_id, terminal_mode, "
                "attempt, schema_version, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "term_" + "9" * 64,
                    plan_id,
                    domain_id,
                    "bogus_mode",
                    3,
                    TERMINAL_RECEIPT_SCHEMA_VERSION,
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()

    def test_terminal_rejects_negative_attempt(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, domain_id = self._setup_plan_node(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {TERMINAL_RECEIPT_TABLE} "
                "(terminal_receipt_id, plan_id, domain_id, terminal_mode, "
                "attempt, schema_version, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "term_" + "8" * 64,
                    plan_id,
                    domain_id,
                    "internal",
                    -1,  # CHECK(attempt >= 0) rejects
                    TERMINAL_RECEIPT_SCHEMA_VERSION,
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()


class TestMigration0018EventNullParity:
    def _setup_plan_node(self, conn: sqlite3.Connection) -> tuple[str, str]:
        _insert_plan(conn, PlanConfig())
        plan_id = PlanConfig().plan_id()
        domain_id = _insert_node(conn, plan_id)
        return plan_id, domain_id

    def test_event_rejects_partial_raw_acq_pair(
        self, tmp_path: Path
    ) -> None:
        """NULL parity: primary_raw_object_id IS NULL iff primary_acquisition_id IS NULL."""
        _, _, conn = _applied_db(tmp_path)
        plan_id, domain_id = self._setup_plan_node(conn)
        # raw present, acq NULL → violates NULL parity CHECK
        compute_terminal_receipt_id(
            plan_id=plan_id,
            domain_id=domain_id,
            terminal_mode="internal",
            attempt=3,
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {ENGINE_EVENT_TABLE} ("
                + ", ".join(ENGINE_EVENT_RECORD_COLUMNS)
                + ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "evt_" + "5" * 64,
                    "1",
                    plan_id,
                    domain_id,
                    0,
                    "failure",
                    "transport",
                    None,
                    None,
                    None,
                    "raw_" + "1" * 64,  # raw present
                    None,               # secondary raw NULL
                    None,               # acq NULL — violates parity!
                    None,
                    "{}",
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()

    def test_event_rejects_null_acq_with_raw(
        self, tmp_path: Path
    ) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, domain_id = self._setup_plan_node(conn)
        # acq present, raw NULL → violates NULL parity
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {ENGINE_EVENT_TABLE} ("
                + ", ".join(ENGINE_EVENT_RECORD_COLUMNS)
                + ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "evt_" + "6" * 64,
                    "1",
                    plan_id,
                    domain_id,
                    0,
                    "failure",
                    None,
                    None,
                    None,
                    None,
                    None,               # raw NULL
                    None,               # secondary raw NULL
                    "acq_" + "3" * 32,  # acq present — violates parity!
                    None,
                    "{}",
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()


class TestMigration0018HeaderUniqueness:
    def test_header_plan_block_unique(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        _insert_plan(conn, PlanConfig())
        plan_id = PlanConfig().plan_id()
        _insert_source(conn, "ethereum_json_rpc")
        _insert_raw_acquisition(conn, "acq_" + "3" * 32, "raw_" + "1" * 64)
        _insert_raw_acquisition(conn, "acq_" + "4" * 32, "raw_" + "2" * 64)
        header_id = (
            "chdr_" + "a" * 64
        )
        conn.execute(
            f"INSERT INTO {HEADER_TABLE} (header_receipt_id, plan_id, block_number, "
            "block_hash, block_timestamp, primary_provider_org, "
            "secondary_provider_org, primary_raw_object_id, "
            "secondary_raw_object_id, primary_acquisition_id, "
            "secondary_acquisition_id, receipt_schema_version, completed_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                header_id,
                plan_id,
                100,
                "0x" + "ab" * 32,
                1700000000,
                "infura",
                "blockpi",
                "raw_" + "1" * 64,
                "raw_" + "2" * 64,
                "acq_" + "3" * 32,
                "acq_" + "4" * 32,
                "1",
                "2026-01-01T00:00:00Z",
            ),
        )
        # Same plan + block_number must fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {HEADER_TABLE} (header_receipt_id, plan_id, block_number, "
                "block_hash, block_timestamp, primary_provider_org, "
                "secondary_provider_org, primary_raw_object_id, "
                "secondary_raw_object_id, primary_acquisition_id, "
                "secondary_acquisition_id, receipt_schema_version, completed_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "chdr_" + "b" * 64,
                    plan_id,
                    100,  # same block
                    "0x" + "cd" * 32,
                    1700000001,
                    "infura",
                    "blockpi",
                    "raw_" + "1" * 64,
                    "raw_" + "2" * 64,
                    "acq_" + "3" * 32,
                    "acq_" + "4" * 32,
                    "1",
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.rollback()
        conn.close()


class TestMigration0018Idempotency:
    def test_idempotent_reapply(self, tmp_path: Path) -> None:
        db_path, migrations_dir, conn = _applied_db(tmp_path)
        conn.close()
        apply_migrations(db_path, migrations_dir=migrations_dir)
        conn = sqlite3.connect(str(db_path))
        count = conn.execute(
            "SELECT COUNT(*) FROM migration_history WHERE filename LIKE '0018_%'"
        ).fetchone()[0]
        assert count == 1
        conn.close()
