"""DEX-003 — focused offline migration tests for 0019.

No network. Proves that 0019 adds the composite acquisition↔raw foreign keys
to the engine_event, canonical_header_receipt, and leaf_receipt tables, and
that mismatched acquisition/raw pairings are rejected by the new FKs.
Also proves the leaf_header_dependency table is rebuilt with its own FKs.
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
    ENGINE_EVENT_RECORD_COLUMNS,
    TERMINAL_MODES,
    TERMINAL_RECEIPT_RECORD_COLUMNS,
    TERMINAL_RECEIPT_TABLE,
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
ENGINE_EVENT_TABLE_NAME = "uniswap_v2_pair_event_v2_engine_event"

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
    """Fresh DB with every migration through 0019 applied."""
    migrations_dir = tmp_path / "migrations"
    for v in range(19):
        _copy_migrations(migrations_dir, v + 1)
    db_path = tmp_path / "v2_0019.db"
    apply_migrations(db_path, migrations_dir=migrations_dir)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return db_path, migrations_dir, conn


def _upgrade_db(tmp_path: Path) -> tuple[Path, Path, sqlite3.Connection]:
    """DB with migrations through 0018 applied, then 0019 applied separately."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    for v in range(18):
        _copy_migrations(migrations_dir, v + 1)
    db_path = tmp_path / "v2_upgrade_0019.db"
    apply_migrations(db_path, migrations_dir=migrations_dir)

    # Apply 0019 by copying it into the migrations dir and re-running.
    _copy_migrations(migrations_dir, 19)
    apply_migrations(db_path, migrations_dir=migrations_dir)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return db_path, migrations_dir, conn


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


def _next_raw_id() -> str:
    global _raw_counter
    _raw_counter += 1
    return f"raw_{_raw_counter:064d}"


def _next_acq_id() -> str:
    global _raw_counter
    _raw_counter += 1
    return f"acq_{_raw_counter:064d}"


def _insert_raw_acquisition(
    conn: sqlite3.Connection,
    acquisition_id: str,
    raw_object_id: str,
    *,
    status: str = "SUCCEEDED",
) -> None:
    _insert_source(conn, "ethereum_json_rpc")
    sha = _next_raw_id()
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


def _insert_node(conn: sqlite3.Connection, plan_id: str, *, status: str = "PENDING") -> str:
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
            status,
            None,
            None,
            0,
            "2026-01-01T00:00:00Z",
        ),
    )
    return domain_id


def _insert_header(
    conn: sqlite3.Connection,
    plan_id: str,
    *,
    header_id: str,
    acq_p: str,
    raw_p: str,
    acq_s: str,
    raw_s: str,
) -> None:
    conn.execute(
        f"INSERT INTO {HEADER_TABLE} "
        "(header_receipt_id, plan_id, block_number, block_hash, block_timestamp, "
        "primary_provider_org, secondary_provider_org, primary_raw_object_id, "
        "secondary_raw_object_id, primary_acquisition_id, secondary_acquisition_id, "
        "receipt_schema_version, completed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            header_id,
            plan_id,
            BLOCK + 9,
            "0x" + "ab" * 32,
            1_700_000_000,
            "infura",
            "blockpi",
            raw_p,
            raw_s,
            acq_p,
            acq_s,
            "1",
            "2026-01-01T00:00:00Z",
        ),
    )


def _insert_leaf(
    conn: sqlite3.Connection,
    plan_id: str,
    *,
    leaf_id: str,
    domain_id: str,
    acq_p: str,
    raw_p: str,
    acq_s: str,
    raw_s: str,
    header_ids: list[str],
) -> None:
    conn.execute(
        f"INSERT INTO {LEAF_TABLE} "
        "(leaf_receipt_id, plan_id, domain_id, start_block, end_block, "
        "addresses_json, topics_json, primary_provider_org, secondary_provider_org, "
        "primary_logs_raw_object_id, secondary_logs_raw_object_id, "
        "primary_logs_acquisition_id, secondary_logs_acquisition_id, "
        "log_count, log_identity_sha256, canonical_header_receipt_ids_json, "
        "log_identity_version, receipt_schema_version, reconciliation_status, completed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            leaf_id,
            plan_id,
            domain_id,
            BLOCK,
            BLOCK + 9,
            json.dumps(["0x" + "11" * 20]),
            json.dumps(["0x" + "00" * 32]),
            "infura",
            "blockpi",
            raw_p,
            raw_s,
            acq_p,
            acq_s,
            1,
            _next_raw_id(),
            json.dumps(header_ids),
            "2",
            "1",
            "AGREED",
            "2026-01-01T00:00:00Z",
        ),
    )


def _insert_event(
    conn: sqlite3.Connection,
    plan_id: str,
    *,
    event_id: str,
    domain_id: str | None,
    acq_p: str,
    raw_p: str,
    acq_s: str | None = None,
    raw_s: str | None = None,
) -> None:
    conn.execute(
        f"INSERT INTO {ENGINE_EVENT_TABLE_NAME} "
        "(event_id, schema_version, plan_id, domain_id, attempt, event_kind, "
        "failure_class, decision, provider_org, request_json, "
        "primary_raw_object_id, secondary_raw_object_id, "
        "primary_acquisition_id, secondary_acquisition_id, detail_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            event_id,
            "1",
            plan_id,
            domain_id,
            0,
            "failure",
            "transport",
            "retry",
            "infura",
            _canonical_json({"jsonrpc": "2.0", "id": 1, "method": "eth_getLogs"}),
            raw_p,
            raw_s,
            acq_p,
            acq_s,
            "{}",
            "2026-01-01T00:00:00Z",
        ),
    )


def _populated_upgrade_db(tmp_path: Path) -> Path:
    """0018 schema populated with valid non-empty rows, then 0019 applied."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    for v in range(18):
        _copy_migrations(migrations_dir, v + 1)
    db_path = tmp_path / "populated_upgrade.db"
    apply_migrations(db_path, migrations_dir=migrations_dir)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _insert_plan(conn, PlanConfig())
        conn.commit()
        plan_id = conn.execute(f"SELECT plan_id FROM {PLAN_TABLE}").fetchone()[0]
        domain_id = _insert_node(conn, plan_id, status="AGREED")
        conn.commit()

        acq_p, raw_p = _next_acq_id(), _next_raw_id()
        acq_s, raw_s = _next_acq_id(), _next_raw_id()
        _insert_raw_acquisition(conn, acq_p, raw_p)
        _insert_raw_acquisition(conn, acq_s, raw_s)
        conn.commit()

        header_id = f"chdr_{_next_raw_id()[:64]}"
        _insert_header(
            conn, plan_id, header_id=header_id, acq_p=acq_p, raw_p=raw_p,
            acq_s=acq_s, raw_s=raw_s,
        )
        leaf_id = f"leaf_{_next_raw_id()[:64]}"
        _insert_leaf(
            conn, plan_id, leaf_id=leaf_id, domain_id=domain_id,
            acq_p=acq_p, raw_p=raw_p, acq_s=acq_s, raw_s=raw_s,
            header_ids=[header_id],
        )
        conn.execute(
            f"INSERT INTO {DEP_TABLE} (plan_id, leaf_receipt_id, header_receipt_id) "
            "VALUES (?, ?, ?)",
            (plan_id, leaf_id, header_id),
        )
        _insert_event(
            conn, plan_id, event_id=f"evt_{_next_raw_id()[:64]}",
            domain_id=domain_id, acq_p=acq_p, raw_p=raw_p, acq_s=acq_s, raw_s=raw_s,
        )
        conn.commit()
    finally:
        conn.close()

    _copy_migrations(migrations_dir, 19)
    apply_migrations(db_path, migrations_dir=migrations_dir)
    return db_path


def _group_fks(conn: sqlite3.Connection, table: str) -> dict[int, list[dict[str, object]]]:
    """Group PRAGMA foreign_key_list rows by FK id, ordered by seq."""
    rows = conn.execute(f"PRAGMA foreign_key_list('{table}')").fetchall()
    groups: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault(row["id"], []).append(
            {
                "seq": row["seq"],
                "table": row["table"],
                "from": row["from"],
                "to": row["to"],
                "on_delete": row["on_delete"],
                "on_update": row["on_update"],
            }
        )
    for cols in groups.values():
        cols.sort(key=lambda item: int(item["seq"]))  # type: ignore[arg-type]
    return groups


def _pairing_fk_signatures(groups: dict[int, list[dict[str, object]]]) -> set[tuple[object, ...]]:
    """Reduce composite raw_acquisition FKs to (table, from-pair, to-pair, delete, update)."""
    signatures: set[tuple[object, ...]] = set()
    for cols in groups.values():
        if cols[0]["table"] != "raw_acquisition":
            continue
        if len(cols) != 2:
            continue
        from_pair = tuple(col["from"] for col in cols)
        to_pair = tuple(col["to"] for col in cols)
        signatures.add(
            (
                "raw_acquisition",
                from_pair,
                to_pair,
                cols[0]["on_delete"],
                cols[0]["on_update"],
            )
        )
    return signatures


class TestMigration0019Applies:
    def test_applies_after_0018(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        applied = {row[0] for row in conn.execute("SELECT filename FROM migration_history")}
        assert any(f.startswith("0019_") for f in applied)
        conn.close()

    def test_upgrade_after_0018(self, tmp_path: Path) -> None:
        _, _, conn = _upgrade_db(tmp_path)
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert ENGINE_EVENT_TABLE_NAME in tables
        conn.close()

    def test_foreign_key_check_empty(self, tmp_path: Path) -> None:
        db_path, _, conn = _applied_db(tmp_path)
        conn.close()
        conn2 = sqlite3.connect(str(db_path))
        conn2.execute("PRAGMA foreign_keys = ON")
        violations = conn2.execute("PRAGMA foreign_key_check").fetchall()
        assert len(violations) == 0
        conn2.close()


class TestEngineEventRawFKs:
    """Engine event table must enforce composite acquisition↔raw pairing."""

    def _setup(self, conn: sqlite3.Connection) -> tuple[str, str, str, str]:
        _insert_plan(conn, PlanConfig())
        conn.commit()
        plan_id = conn.execute(
            f"SELECT plan_id FROM {PLAN_TABLE}"
        ).fetchone()[0]
        acq_id = _next_acq_id()
        raw_id = _next_raw_id()
        _insert_raw_acquisition(conn, acq_id, raw_id)
        conn.commit()
        return plan_id, acq_id, raw_id, ""

    def test_valid_event_insert_accepted(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, acq_id, raw_id, _ = self._setup(conn)
        conn.execute(
            f"INSERT INTO {ENGINE_EVENT_TABLE_NAME} ({', '.join(ENGINE_EVENT_RECORD_COLUMNS)}) "
            f"VALUES ({', '.join('?' for _ in ENGINE_EVENT_RECORD_COLUMNS)})",
            (
                f"evt_{_next_raw_id()[:64]}",
                "1",
                plan_id,
                None,
                0,
                "failure",
                "transport",
                "retry",
                "primary",
                '{"jsonrpc": "2.0"}',
                raw_id,
                None,
                acq_id,
                None,
                '{}',
                "2026-01-01T00:00:00Z",
            ),
        )
        conn.close()

    def test_mismatched_raw_object_rejected(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, acq_id, raw_id, _ = self._setup(conn)
        # raw_other is not paired with acq_id in raw_acquisition
        raw_other = _next_raw_id()
        _insert_source(conn, "ethereum_json_rpc")
        conn.execute(
            "INSERT INTO raw_object (raw_object_id, source_id, sha256, byte_size, "
            "storage_uri, status, acquired_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (raw_other, "ethereum_json_rpc", _next_raw_id(), 100, "raw/x", "PRESENT", "2026-01-01T00:00:00Z"),
        )
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.execute(
                f"INSERT INTO {ENGINE_EVENT_TABLE_NAME} "
                "(event_id, schema_version, plan_id, domain_id, attempt, event_kind, "
                "failure_class, decision, provider_org, request_json, "
                "primary_raw_object_id, secondary_raw_object_id, "
                "primary_acquisition_id, secondary_acquisition_id, detail_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"evt_{_next_raw_id()[:64]}",
                    "1", plan_id, None, 0, "failure", "transport", "retry",
                    "primary", '{"jsonrpc": "2.0"}',
                    raw_other, None, acq_id, None, '{}', "2026-01-01T00:00:00Z",
                ),
            )
        conn.close()

    def test_mismatched_acquisition_rejected(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, acq_id, raw_id, _ = self._setup(conn)
        # acq_other is paired with a different raw_object_id
        acq_other = _next_acq_id()
        raw_other = _next_raw_id()
        _insert_raw_acquisition(conn, acq_other, raw_other)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.execute(
                f"INSERT INTO {ENGINE_EVENT_TABLE_NAME} "
                "(event_id, schema_version, plan_id, domain_id, attempt, event_kind, "
                "failure_class, decision, provider_org, request_json, "
                "primary_raw_object_id, secondary_raw_object_id, "
                "primary_acquisition_id, secondary_acquisition_id, detail_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"evt_{_next_raw_id()[:64]}",
                    "1", plan_id, None, 0, "failure", "transport", "retry",
                    "primary", '{"jsonrpc": "2.0"}',
                    raw_id, None, acq_other, None, '{}', "2026-01-01T00:00:00Z",
                ),
            )
        conn.close()

    def test_null_parity_still_enforced(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, _, _, _ = self._setup(conn)
        # primary_raw_object_id present but primary_acquisition_id NULL → CHECK violation
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {ENGINE_EVENT_TABLE_NAME} "
                "(event_id, schema_version, plan_id, domain_id, attempt, event_kind, "
                "failure_class, decision, provider_org, request_json, "
                "primary_raw_object_id, secondary_raw_object_id, "
                "primary_acquisition_id, secondary_acquisition_id, detail_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"evt_{_next_raw_id()[:64]}",
                    "1", plan_id, None, 0, "failure", "transport", "retry",
                    "primary", '{"jsonrpc": "2.0"}',
                    "raw_present", None, None, None, '{}', "2026-01-01T00:00:00Z",
                ),
            )
        conn.close()


class TestHeaderReceiptRawFKs:
    """Canonical header receipt must enforce composite acquisition↔raw pairing."""

    def _setup(self, conn: sqlite3.Connection) -> tuple[str, str, str]:
        _insert_plan(conn, PlanConfig())
        conn.execute("COMMIT")
        plan_id = conn.execute(f"SELECT plan_id FROM {PLAN_TABLE}").fetchone()[0]
        acq_id = _next_acq_id()
        raw_id = _next_raw_id()
        _insert_raw_acquisition(conn, acq_id, raw_id)
        conn.execute("COMMIT")
        return plan_id, acq_id, raw_id

    def test_valid_header_insert_accepted(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, acq_id, raw_id = self._setup(conn)
        conn.execute(
            f"INSERT INTO {HEADER_TABLE} "
            "(header_receipt_id, plan_id, block_number, block_hash, block_timestamp, "
            "primary_provider_org, secondary_provider_org, primary_raw_object_id, "
            "secondary_raw_object_id, primary_acquisition_id, secondary_acquisition_id, "
            "receipt_schema_version, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"chdr_{_next_raw_id()[:64]}",
                plan_id, 100, "0x" + "ab" * 32, 1_700_000_000,
                "primary", "secondary", raw_id, raw_id, acq_id, acq_id,
                "1", "2026-01-01T00:00:00Z",
            ),
        )
        conn.close()

    def test_mismatched_primary_raw_rejected(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, acq_id, raw_id = self._setup(conn)
        raw_other = _next_raw_id()
        _insert_source(conn, "ethereum_json_rpc")
        conn.execute(
            "INSERT INTO raw_object (raw_object_id, source_id, sha256, byte_size, "
            "storage_uri, status, acquired_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (raw_other, "ethereum_json_rpc", _next_raw_id(), 100, "raw/x", "PRESENT", "2026-01-01T00:00:00Z"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {HEADER_TABLE} "
                "(header_receipt_id, plan_id, block_number, block_hash, block_timestamp, "
                "primary_provider_org, secondary_provider_org, primary_raw_object_id, "
                "secondary_raw_object_id, primary_acquisition_id, secondary_acquisition_id, "
                "receipt_schema_version, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"chdr_{_next_raw_id()[:64]}",
                    plan_id, 100, "0x" + "cd" * 32, 1_700_000_000,
                    "primary", "secondary", raw_other, raw_id, acq_id, acq_id,
                    "1", "2026-01-01T00:00:00Z",
                ),
            )
        conn.close()

    def test_mismatched_secondary_acquisition_rejected(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, acq_id, raw_id = self._setup(conn)
        acq_other = _next_acq_id()
        raw_other = _next_raw_id()
        _insert_raw_acquisition(conn, acq_other, raw_other)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {HEADER_TABLE} "
                "(header_receipt_id, plan_id, block_number, block_hash, block_timestamp, "
                "primary_provider_org, secondary_provider_org, primary_raw_object_id, "
                "secondary_raw_object_id, primary_acquisition_id, secondary_acquisition_id, "
                "receipt_schema_version, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"chdr_{_next_raw_id()[:64]}",
                    plan_id, 100, "0x" + "ab" * 32, 1_700_000_000,
                    "primary", "secondary", raw_id, raw_id, acq_id, acq_other,
                    "1", "2026-01-01T00:00:00Z",
                ),
            )
        conn.close()


class TestLeafReceiptRawFKs:
    """Leaf receipt must enforce composite acquisition↔raw pairing on log acquisitions."""

    def _setup(self, conn: sqlite3.Connection) -> tuple[str, str, str, str]:
        _insert_plan(conn, PlanConfig())
        conn.execute("COMMIT")
        plan_id = conn.execute(f"SELECT plan_id FROM {PLAN_TABLE}").fetchone()[0]
        acq_id = _next_acq_id()
        raw_id = _next_raw_id()
        _insert_raw_acquisition(conn, acq_id, raw_id)
        conn.execute("COMMIT")
        domain_id = _insert_node(conn, plan_id)
        conn.execute("COMMIT")
        return plan_id, domain_id, acq_id, raw_id

    def test_valid_leaf_insert_accepted(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, domain_id, acq_id, raw_id = self._setup(conn)
        conn.execute(
            f"INSERT INTO {LEAF_TABLE} "
            "(leaf_receipt_id, plan_id, domain_id, start_block, end_block, "
            "addresses_json, topics_json, primary_provider_org, secondary_provider_org, "
            "primary_logs_raw_object_id, secondary_logs_raw_object_id, "
            "primary_logs_acquisition_id, secondary_logs_acquisition_id, "
            "log_count, log_identity_sha256, canonical_header_receipt_ids_json, "
            "log_identity_version, receipt_schema_version, reconciliation_status, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"leaf_{_next_raw_id()[:64]}",
                plan_id, domain_id, BLOCK, BLOCK + 9,
                json.dumps(["0x" + "11" * 20]), json.dumps(["0x" + "00" * 32]),
                "primary", "secondary", raw_id, raw_id, acq_id, acq_id,
                1, _next_raw_id(), "[]", "2", "1", "AGREED", "2026-01-01T00:00:00Z",
            ),
        )
        conn.close()

    def test_mismatched_primary_raw_rejected(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, domain_id, acq_id, raw_id = self._setup(conn)
        raw_other = _next_raw_id()
        _insert_source(conn, "ethereum_json_rpc")
        conn.execute(
            "INSERT INTO raw_object (raw_object_id, source_id, sha256, byte_size, "
            "storage_uri, status, acquired_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (raw_other, "ethereum_json_rpc", _next_raw_id(), 100, "raw/x", "PRESENT", "2026-01-01T00:00:00Z"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {LEAF_TABLE} "
                "(leaf_receipt_id, plan_id, domain_id, start_block, end_block, "
                "addresses_json, topics_json, primary_provider_org, secondary_provider_org, "
                "primary_logs_raw_object_id, secondary_logs_raw_object_id, "
                "primary_logs_acquisition_id, secondary_logs_acquisition_id, "
                "log_count, log_identity_sha256, canonical_header_receipt_ids_json, "
                "log_identity_version, receipt_schema_version, reconciliation_status, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"leaf_{_next_raw_id()[:64]}",
                    plan_id, domain_id, BLOCK, BLOCK + 9,
                    json.dumps(["0x" + "11" * 20]), json.dumps(["0x" + "00" * 32]),
                    "primary", "secondary", raw_other, raw_id, acq_id, acq_id,
                    1, _next_raw_id(), "[]", "2", "1", "AGREED", "2026-01-01T00:00:00Z",
                ),
            )
        conn.close()

    def test_mismatched_secondary_acquisition_rejected(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, domain_id, acq_id, raw_id = self._setup(conn)
        acq_other = _next_acq_id()
        raw_other = _next_raw_id()
        _insert_raw_acquisition(conn, acq_other, raw_other)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {LEAF_TABLE} "
                "(leaf_receipt_id, plan_id, domain_id, start_block, end_block, "
                "addresses_json, topics_json, primary_provider_org, secondary_provider_org, "
                "primary_logs_raw_object_id, secondary_logs_raw_object_id, "
                "primary_logs_acquisition_id, secondary_logs_acquisition_id, "
                "log_count, log_identity_sha256, canonical_header_receipt_ids_json, "
                "log_identity_version, receipt_schema_version, reconciliation_status, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"leaf_{_next_raw_id()[:64]}",
                    plan_id, domain_id, BLOCK, BLOCK + 9,
                    json.dumps(["0x" + "11" * 20]), json.dumps(["0x" + "00" * 32]),
                    "primary", "secondary", raw_id, raw_id, acq_id, acq_other,
                    1, _next_raw_id(), "[]", "2", "1", "AGREED", "2026-01-01T00:00:00Z",
                ),
            )
        conn.close()


class TestDependencyRebuild:
    """leaf_header_dependency table must be rebuilt with FKs to rebuilt parents."""

    def _setup_dep(self, conn: sqlite3.Connection) -> tuple[str, str, str, str]:
        _insert_plan(conn, PlanConfig())
        conn.execute("COMMIT")
        plan_id = conn.execute(f"SELECT plan_id FROM {PLAN_TABLE}").fetchone()[0]
        domain_id = _insert_node(conn, plan_id)
        conn.execute("COMMIT")

        acq_p = _next_acq_id()
        raw_p = _next_raw_id()
        _insert_raw_acquisition(conn, acq_p, raw_p)

        acq_h = _next_acq_id()
        raw_h = _next_raw_id()
        _insert_raw_acquisition(conn, acq_h, raw_h)
        conn.execute("COMMIT")

        leaf_id = f"leaf_{_next_raw_id()[:64]}"
        header_id = f"chdr_{_next_raw_id()[:64]}"

        conn.execute(
            f"INSERT INTO {LEAF_TABLE} "
            "(leaf_receipt_id, plan_id, domain_id, start_block, end_block, "
            "addresses_json, topics_json, primary_provider_org, secondary_provider_org, "
            "primary_logs_raw_object_id, secondary_logs_raw_object_id, "
            "primary_logs_acquisition_id, secondary_logs_acquisition_id, "
            "log_count, log_identity_sha256, canonical_header_receipt_ids_json, "
            "log_identity_version, receipt_schema_version, reconciliation_status, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                leaf_id,
                plan_id, domain_id, BLOCK, BLOCK + 9,
                json.dumps(["0x" + "11" * 20]), json.dumps(["0x" + "00" * 32]),
                "primary", "secondary", raw_p, raw_p, acq_p, acq_p,
                1, _next_raw_id(), "[]", "2", "1", "AGREED", "2026-01-01T00:00:00Z",
            ),
        )

        conn.execute(
            f"INSERT INTO {HEADER_TABLE} "
            "(header_receipt_id, plan_id, block_number, block_hash, block_timestamp, "
            "primary_provider_org, secondary_provider_org, primary_raw_object_id, "
            "secondary_raw_object_id, primary_acquisition_id, secondary_acquisition_id, "
            "receipt_schema_version, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                header_id,
                plan_id, 100, "0x" + "ab" * 32, 1_700_000_000,
                "primary", "secondary", raw_h, raw_h, acq_h, acq_h,
                "1", "2026-01-01T00:00:00Z",
            ),
        )
        conn.execute("COMMIT")
        return plan_id, leaf_id, header_id, domain_id

    def test_valid_dependency_insert_accepted(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, leaf_id, header_id, _ = self._setup_dep(conn)
        conn.execute(
            f"INSERT INTO {DEP_TABLE} (plan_id, leaf_receipt_id, header_receipt_id) "
            "VALUES (?, ?, ?)",
            (plan_id, leaf_id, header_id),
        )
        conn.close()

    def test_nonexistent_leaf_rejected(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, leaf_id, header_id, _ = self._setup_dep(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {DEP_TABLE} (plan_id, leaf_receipt_id, header_receipt_id) "
                "VALUES (?, ?, ?)",
                (plan_id, "leaf_nonexistent", header_id),
            )
        conn.close()

    def test_nonexistent_header_rejected(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        plan_id, leaf_id, header_id, _ = self._setup_dep(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {DEP_TABLE} (plan_id, leaf_receipt_id, header_receipt_id) "
                "VALUES (?, ?, ?)",
                (plan_id, leaf_id, "chdr_nonexistent"),
            )
        conn.close()


class TestTerminalReceiptUniqueness:
    """Terminal receipt must preserve UNIQUE(plan_id, domain_id) after 0019 rebuild."""

    def test_duplicate_terminal_rejected(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        _insert_plan(conn, PlanConfig())
        conn.execute("COMMIT")
        plan_id = conn.execute(f"SELECT plan_id FROM {PLAN_TABLE}").fetchone()[0]
        domain_id = _insert_node(conn, plan_id)
        conn.execute("COMMIT")

        receipt_id = compute_terminal_receipt_id(
            plan_id=plan_id,
            domain_id=domain_id,
            terminal_mode="transport",
            attempt=3,
        )
        cols = TERMINAL_RECEIPT_RECORD_COLUMNS
        conn.execute(
            f"INSERT INTO {TERMINAL_RECEIPT_TABLE} ({', '.join(cols)}) "
            f"VALUES ({', '.join('?' for _ in cols)})",
            (receipt_id, plan_id, domain_id, "transport", 3, "1", "2026-01-01T00:00:00Z"),
        )

        # Same plan/domain → UNIQUE violation
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {TERMINAL_RECEIPT_TABLE} ({', '.join(cols)}) "
                f"VALUES ({', '.join('?' for _ in cols)})",
                (receipt_id + "_x", plan_id, domain_id, "internal", 3, "1", "2026-01-01T00:00:00Z"),
            )
        conn.close()

    def test_terminal_modes_count_matches_contract(self) -> None:
        assert len(TERMINAL_MODES) == 16


class TestUpgradePreservesRows:
    """0019 as an upgrade from 0018 with valid non-empty rows must keep every row."""

    _V2_TABLES = (
        PLAN_TABLE,
        NODE_TABLE,
        HEADER_TABLE,
        LEAF_TABLE,
        DEP_TABLE,
        ENGINE_EVENT_TABLE_NAME,
    )

    def test_all_rows_survive_upgrade(self, tmp_path: Path) -> None:
        db_path = _populated_upgrade_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            counts = {
                table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in self._V2_TABLES
            }
            assert counts == {table: 1 for table in self._V2_TABLES}
            raw_pairs = conn.execute(
                "SELECT COUNT(*) FROM raw_acquisition JOIN raw_object "
                "ON raw_acquisition.raw_object_id = raw_object.raw_object_id"
            ).fetchone()[0]
            assert raw_pairs == 2
            legacy = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name LIKE 'zz_legacy%'"
            ).fetchall()
            assert legacy == []
        finally:
            conn.close()

    def test_foreign_key_check_empty_after_populated_upgrade(self, tmp_path: Path) -> None:
        db_path = _populated_upgrade_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            assert len(violations) == 0
        finally:
            conn.close()

    def test_0019_recorded_in_history(self, tmp_path: Path) -> None:
        db_path = _populated_upgrade_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            applied = {
                row[0]
                for row in conn.execute("SELECT filename FROM migration_history")
            }
            assert any(f.startswith("0019_") for f in applied)
        finally:
            conn.close()

    def test_header_and_leaf_content_preserved(self, tmp_path: Path) -> None:
        db_path = _populated_upgrade_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            header = conn.execute(
                f"SELECT block_number, block_hash, primary_provider_org, "
                f"secondary_provider_org, primary_raw_object_id, "
                f"secondary_raw_object_id, primary_acquisition_id, "
                f"secondary_acquisition_id FROM {HEADER_TABLE}"
            ).fetchone()
            assert header["block_number"] == BLOCK + 9
            assert header["block_hash"] == "0x" + "ab" * 32
            assert header["primary_provider_org"] == "infura"
            assert header["secondary_provider_org"] == "blockpi"
            assert header["primary_raw_object_id"].startswith("raw_")
            assert header["secondary_raw_object_id"].startswith("raw_")
            leaf = conn.execute(
                f"SELECT log_count, reconciliation_status, log_identity_version, "
                f"primary_provider_org, secondary_provider_org FROM {LEAF_TABLE}"
            ).fetchone()
            assert leaf["log_count"] == 1
            assert leaf["reconciliation_status"] == "AGREED"
            assert leaf["log_identity_version"] == "2"
            dep = conn.execute(
                f"SELECT COUNT(*) FROM {DEP_TABLE}"
            ).fetchone()[0]
            assert dep == 1
        finally:
            conn.close()


class TestInvalidLegacyRowUpgrade:
    """A legacy mismatched row must fail the 0019 copy atomically."""

    def _build_bad_0018(self, tmp_path: Path) -> Path:
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir(parents=True, exist_ok=True)
        for v in range(18):
            _copy_migrations(migrations_dir, v + 1)
        db_path = tmp_path / "bad_upgrade.db"
        apply_migrations(db_path, migrations_dir=migrations_dir)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            _insert_plan(conn, PlanConfig())
            conn.commit()
            plan_id = conn.execute(f"SELECT plan_id FROM {PLAN_TABLE}").fetchone()[0]
            domain_id = _insert_node(conn, plan_id)
            conn.commit()

            acq_p, raw_p = _next_acq_id(), _next_raw_id()
            acq_s, raw_s = _next_acq_id(), _next_raw_id()
            acq_bad, raw_bad = _next_acq_id(), _next_raw_id()
            _insert_raw_acquisition(conn, acq_p, raw_p)
            _insert_raw_acquisition(conn, acq_s, raw_s)
            _insert_raw_acquisition(conn, acq_bad, raw_bad)
            conn.commit()

            # Genuine mismatch: acquisition_id from one pair, raw_object_id from another.
            # 0018 has no composite FK on engine_event, so this row is accepted there.
            _insert_event(
                conn,
                plan_id,
                event_id=f"evt_{_next_raw_id()[:64]}",
                domain_id=domain_id,
                acq_p=acq_p,
                raw_p=raw_bad,
            )
            conn.commit()
        finally:
            conn.close()
        return db_path

    def test_mismatched_legacy_row_rolls_back(self, tmp_path: Path) -> None:
        db_path = self._build_bad_0018(tmp_path)
        migrations_dir = tmp_path / "migrations"
        _copy_migrations(migrations_dir, 19)
        with pytest.raises(RuntimeError, match="0019_uniswap_v2_pair_event_v2_engine_raw_fks"):
            apply_migrations(db_path, migrations_dir=migrations_dir)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            applied = {
                row[0]
                for row in conn.execute("SELECT filename FROM migration_history")
            }
            assert not any(f.startswith("0019_") for f in applied)

            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert DEP_TABLE in tables
            assert not any(t.startswith("zz_legacy") for t in tables)

            events = conn.execute(
                f"SELECT COUNT(*) FROM {ENGINE_EVENT_TABLE_NAME}"
            ).fetchone()[0]
            assert events == 1

            headers = conn.execute(f"SELECT COUNT(*) FROM {HEADER_TABLE}").fetchone()[0]
            leaves = conn.execute(f"SELECT COUNT(*) FROM {LEAF_TABLE}").fetchone()[0]
            deps = conn.execute(f"SELECT COUNT(*) FROM {DEP_TABLE}").fetchone()[0]
            assert (headers, leaves, deps) == (0, 0, 0)

            conn.execute("PRAGMA foreign_keys = ON")
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        finally:
            conn.close()

    def test_valid_rows_survive_failed_upgrade(self, tmp_path: Path) -> None:
        db_path = self._build_bad_0018(tmp_path)
        migrations_dir = tmp_path / "migrations"
        _copy_migrations(migrations_dir, 19)
        with pytest.raises(RuntimeError):
            apply_migrations(db_path, migrations_dir=migrations_dir)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            plan_id = conn.execute(f"SELECT plan_id FROM {PLAN_TABLE}").fetchone()[0]
            assert plan_id.startswith("plan_")
            nodes = conn.execute(
                f"SELECT COUNT(*) FROM {NODE_TABLE}"
            ).fetchone()[0]
            raws = conn.execute(
                "SELECT COUNT(*) FROM raw_acquisition"
            ).fetchone()[0]
            assert nodes == 1
            assert raws == 3
        finally:
            conn.close()


class TestCompositeFkSchema:
    """Direct schema assertions: both pairing FKs plus exact RESTRICT actions."""

    def _signatures(self, tmp_path: Path, table: str) -> set[tuple[object, ...]]:
        _, _, conn = _applied_db(tmp_path)
        try:
            return _pairing_fk_signatures(_group_fks(conn, table))
        finally:
            conn.close()

    def test_engine_event_pairing_fks(self, tmp_path: Path) -> None:
        sigs = self._signatures(tmp_path, ENGINE_EVENT_TABLE_NAME)
        assert (
            "raw_acquisition",
            ("primary_acquisition_id", "primary_raw_object_id"),
            ("acquisition_id", "raw_object_id"),
            "RESTRICT",
            "RESTRICT",
        ) in sigs
        assert (
            "raw_acquisition",
            ("secondary_acquisition_id", "secondary_raw_object_id"),
            ("acquisition_id", "raw_object_id"),
            "RESTRICT",
            "RESTRICT",
        ) in sigs

    def test_header_pairing_fks(self, tmp_path: Path) -> None:
        sigs = self._signatures(tmp_path, HEADER_TABLE)
        assert (
            "raw_acquisition",
            ("primary_acquisition_id", "primary_raw_object_id"),
            ("acquisition_id", "raw_object_id"),
            "RESTRICT",
            "RESTRICT",
        ) in sigs
        assert (
            "raw_acquisition",
            ("secondary_acquisition_id", "secondary_raw_object_id"),
            ("acquisition_id", "raw_object_id"),
            "RESTRICT",
            "RESTRICT",
        ) in sigs

    def test_leaf_pairing_fks(self, tmp_path: Path) -> None:
        sigs = self._signatures(tmp_path, LEAF_TABLE)
        assert (
            "raw_acquisition",
            ("primary_logs_acquisition_id", "primary_logs_raw_object_id"),
            ("acquisition_id", "raw_object_id"),
            "RESTRICT",
            "RESTRICT",
        ) in sigs
        assert (
            "raw_acquisition",
            ("secondary_logs_acquisition_id", "secondary_logs_raw_object_id"),
            ("acquisition_id", "raw_object_id"),
            "RESTRICT",
            "RESTRICT",
        ) in sigs

    def test_no_legacy_tables_remain(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        try:
            legacy = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name LIKE 'zz_legacy%'"
            ).fetchall()
            assert legacy == []
        finally:
            conn.close()


class TestFkRestrictActions:
    """Delete/update RESTRICT on referenced raw_acquisition rows."""

    def _event_setup(self, tmp_path: Path) -> tuple[Path, sqlite3.Connection, str, str, str]:
        db_path, _, conn = _applied_db(tmp_path)
        _insert_plan(conn, PlanConfig())
        conn.commit()
        plan_id = conn.execute(f"SELECT plan_id FROM {PLAN_TABLE}").fetchone()[0]
        acq_id = _next_acq_id()
        raw_id = _next_raw_id()
        _insert_raw_acquisition(conn, acq_id, raw_id)
        conn.commit()
        _insert_event(
            conn,
            plan_id,
            event_id=f"evt_{_next_raw_id()[:64]}",
            domain_id=None,
            acq_p=acq_id,
            raw_p=raw_id,
        )
        conn.commit()
        return db_path, conn, acq_id, raw_id, plan_id

    def test_event_delete_referenced_pair_restricted(self, tmp_path: Path) -> None:
        _, conn, acq_id, _, _ = self._event_setup(tmp_path)
        try:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "DELETE FROM raw_acquisition WHERE acquisition_id = ?", (acq_id,)
                )
        finally:
            conn.close()

    def test_event_update_referenced_pair_restricted(self, tmp_path: Path) -> None:
        _, conn, acq_id, _, _ = self._event_setup(tmp_path)
        try:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "UPDATE raw_acquisition SET acquisition_id = ? "
                    "WHERE acquisition_id = ?",
                    (_next_acq_id(), acq_id),
                )
        finally:
            conn.close()

    def test_header_delete_referenced_pair_restricted(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        _insert_plan(conn, PlanConfig())
        conn.commit()
        plan_id = conn.execute(f"SELECT plan_id FROM {PLAN_TABLE}").fetchone()[0]
        acq_p, raw_p = _next_acq_id(), _next_raw_id()
        acq_s, raw_s = _next_acq_id(), _next_raw_id()
        _insert_raw_acquisition(conn, acq_p, raw_p)
        _insert_raw_acquisition(conn, acq_s, raw_s)
        conn.commit()
        _insert_header(
            conn,
            plan_id,
            header_id=f"chdr_{_next_raw_id()[:64]}",
            acq_p=acq_p, raw_p=raw_p, acq_s=acq_s, raw_s=raw_s,
        )
        conn.commit()
        try:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "DELETE FROM raw_acquisition WHERE acquisition_id = ?", (acq_p,)
                )
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "DELETE FROM raw_acquisition WHERE acquisition_id = ?", (acq_s,)
                )
        finally:
            conn.close()

    def test_leaf_update_referenced_pair_restricted(self, tmp_path: Path) -> None:
        _, _, conn = _applied_db(tmp_path)
        _insert_plan(conn, PlanConfig())
        conn.commit()
        plan_id = conn.execute(f"SELECT plan_id FROM {PLAN_TABLE}").fetchone()[0]
        domain_id = _insert_node(conn, plan_id)
        conn.commit()
        acq_p, raw_p = _next_acq_id(), _next_raw_id()
        acq_s, raw_s = _next_acq_id(), _next_raw_id()
        _insert_raw_acquisition(conn, acq_p, raw_p)
        _insert_raw_acquisition(conn, acq_s, raw_s)
        conn.commit()
        _insert_leaf(
            conn,
            plan_id,
            leaf_id=f"leaf_{_next_raw_id()[:64]}",
            domain_id=domain_id,
            acq_p=acq_p, raw_p=raw_p, acq_s=acq_s, raw_s=raw_s,
            header_ids=[],
        )
        conn.commit()
        try:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "UPDATE raw_acquisition SET acquisition_id = ? "
                    "WHERE acquisition_id = ?",
                    (_next_acq_id(), acq_s),
                )
        finally:
            conn.close()
