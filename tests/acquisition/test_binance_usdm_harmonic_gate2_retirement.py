"""Synthetic proof of the ADR-0030 Gate-2 retirement tool.

Every test is temporary-rooted, offline, and free of the live Gate-2 store and the
acquisition engine.
"""

from __future__ import annotations

import errno
import fcntl
import hashlib
import importlib.util
import io
import json
import os
import sqlite3
import stat
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

from cryptofactors.acquisition import binance_usdm_harmonic_gate2_retirement as retire

REPOSITORY = Path(__file__).resolve().parents[2]
SECRET = "SECRET_TEST_KEY_DO_NOT_LEAK_retirement"
PLAN_POLICY = "adr0029_content_addressed_gate2_acquisition_and_resume_v1"
PLAN_SCHEMA = "cex002_gate2_plan_receipt_v1"
APP_ID = 1127368498

SQLITE_SCHEMA = """
CREATE TABLE authority (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    plan_identity TEXT NOT NULL,
    plan_receipt_sha256 TEXT NOT NULL,
    pins_json TEXT NOT NULL,
    code_json TEXT NOT NULL,
    destination TEXT NOT NULL,
    device TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE plan_entry (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE(provider, identity)
);
CREATE TABLE attempt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    class TEXT NOT NULL,
    status_code INTEGER,
    redacted_fact_json TEXT NOT NULL,
    FOREIGN KEY (provider, identity) REFERENCES plan_entry(provider, identity)
);
CREATE TABLE sidecar_fact (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    sidecar_sha256 TEXT NOT NULL,
    sidecar_path TEXT NOT NULL,
    sidecar_bytes INTEGER NOT NULL,
    provider_checksum TEXT NOT NULL,
    UNIQUE(provider, identity),
    FOREIGN KEY (provider, identity) REFERENCES plan_entry(provider, identity)
);
CREATE TABLE completion (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    content_path TEXT NOT NULL,
    sidecar_sha256 TEXT,
    sidecar_path TEXT,
    listed_bytes INTEGER NOT NULL,
    retrieved_at TEXT NOT NULL,
    revision_json TEXT NOT NULL,
    validation_state TEXT NOT NULL,
    UNIQUE(provider, identity),
    FOREIGN KEY (provider, identity) REFERENCES plan_entry(provider, identity)
);
CREATE TABLE terminal_gap (
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    kind TEXT NOT NULL,
    fact_json TEXT NOT NULL,
    PRIMARY KEY (provider, identity),
    FOREIGN KEY (provider, identity) REFERENCES plan_entry(provider, identity)
);
CREATE TABLE coinalyze_ledger (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    charged INTEGER NOT NULL CHECK (charged >= 0)
);
CREATE TABLE coinalyze_charge (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    generation INTEGER NOT NULL,
    content_sha256 TEXT NOT NULL,
    charged_bytes INTEGER NOT NULL,
    http_status INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    points INTEGER NOT NULL,
    request_proof TEXT NOT NULL,
    retrieval_json TEXT NOT NULL,
    revision_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(provider, identity, generation),
    FOREIGN KEY (provider, identity) REFERENCES plan_entry(provider, identity)
);
CREATE TABLE charge_transition (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    identity TEXT NOT NULL,
    generation INTEGER NOT NULL,
    status TEXT NOT NULL,
    at TEXT NOT NULL,
    FOREIGN KEY (provider, identity) REFERENCES plan_entry(provider, identity)
);
CREATE TABLE run_metadata (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    stop_reason TEXT,
    attempt_hi INTEGER NOT NULL,
    network_calls INTEGER NOT NULL,
    start_snapshot_json TEXT NOT NULL,
    error_count INTEGER NOT NULL,
    network_sample_json TEXT NOT NULL,
    pre_capacity_json TEXT NOT NULL,
    post_capacity_json TEXT NOT NULL,
    capacity_blocked INTEGER NOT NULL,
    attempt_delta INTEGER NOT NULL,
    completion_delta INTEGER NOT NULL,
    gap_delta INTEGER NOT NULL,
    byte_delta INTEGER NOT NULL,
    open_coinalyze_charges INTEGER NOT NULL,
    counts_json TEXT NOT NULL
);
CREATE TABLE run_publication (
    run_id TEXT PRIMARY KEY,
    receipt_sha256 TEXT NOT NULL,
    receipt_directory TEXT NOT NULL,
    receipt_body TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_metadata(run_id)
);
CREATE TABLE run_seal (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    receipt_sha256 TEXT NOT NULL,
    predecessor_sha256 TEXT NOT NULL,
    prefix_digest TEXT NOT NULL,
    marks_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_metadata(run_id)
);
CREATE TABLE seal_head (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    receipt_sha256 TEXT NOT NULL,
    receipt_path TEXT NOT NULL,
    prefix_digest TEXT NOT NULL,
    attempt_hi INTEGER NOT NULL,
    completion_hi INTEGER NOT NULL,
    sidecar_hi INTEGER NOT NULL,
    charge_hi INTEGER NOT NULL,
    transition_hi INTEGER NOT NULL,
    run_hi INTEGER NOT NULL,
    seal_hi INTEGER NOT NULL,
    predecessor_sha256 TEXT
);
"""


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(payload: Any) -> bytes:
    return retire.canonical_json(payload)


def _write(path: Path, payload: bytes, mode: int = 0o600) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    os.chmod(path, mode)
    return _sha(payload)


def _payload(provider: str, identity: str, kind: str, retained: bool | None) -> str:
    body: dict[str, Any] = {}
    if retained is not None:
        body["retained"] = retained
    return json.dumps(
        {
            "identity": identity,
            "kind": kind,
            "payload": body,
            "provider": provider,
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def _entry(path: Path, relative: str) -> dict[str, Any]:
    target = path if relative == "." else path / relative
    st = os.lstat(target)
    if stat.S_ISLNK(st.st_mode):
        kind = "symlink"
        digest: str | None = None
    elif stat.S_ISREG(st.st_mode):
        kind = "regular_file"
        digest = _sha(target.read_bytes())
    elif stat.S_ISDIR(st.st_mode):
        kind = "directory"
        digest = None
    else:
        kind = "special"
        digest = None
    return {
        "device": int(st.st_dev),
        "inode": int(st.st_ino),
        "mode": int(stat.S_IMODE(st.st_mode)),
        "path": relative,
        "sha256": digest,
        "size": int(st.st_size),
        "type": kind,
    }


def _create_sqlite(
    path: Path,
    *,
    plan_identity: str,
    receipt_sha: str,
    source_sha: str,
    cli_sha: str,
    device_label: str,
    extra_table: bool = False,
    omit_seal_head: bool = False,
    orphan_gap: bool = False,
    application_id: int = APP_ID,
    user_version: int = 7,
    retained_true: int = 2,
    finished_run: bool = False,
    ledger_charged: int = 0,
    completion_row: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SQLITE_SCHEMA)
        if extra_table:
            conn.execute("CREATE TABLE extra_table(id INTEGER)")
        conn.execute(f"PRAGMA application_id={int(application_id)}")
        conn.execute(f"PRAGMA user_version={int(user_version)}")
        code = {
            "acquisition_cli_sha256": cli_sha,
            "acquisition_source_sha256": source_sha,
            "policy_identity": PLAN_POLICY,
        }
        conn.execute(
            "INSERT INTO authority(id, plan_identity, plan_receipt_sha256, pins_json, "
            "code_json, destination, device, created_at) VALUES (1, ?, ?, ?, ?, ?, ?, ?)",
            (
                plan_identity,
                receipt_sha,
                "{}",
                json.dumps(code, sort_keys=True),
                "data/cex002_qualify",
                device_label,
                "2026-08-27T18:11:33.135154+00:00",
            ),
        )
        rows = [
            ("binance_vision", "k1", "binance_object", True),
            ("binance_vision", "k2", "binance_object", True),
            ("binance_vision", "k3", "binance_object", False),
            ("coinalyze", "inv", "coinalyze_inventory", None),
            ("coinalyze", "liq", "coinalyze_liquidation", None),
            ("coinalyze", "unsupported:GAP", "coinalyze_unsupported_gap", None),
        ]
        if retained_true == 1:
            rows[1] = ("binance_vision", "k2", "binance_object", False)
        for provider, identity, kind, flag in rows:
            conn.execute(
                "INSERT INTO plan_entry(provider, identity, kind, payload_json) "
                "VALUES (?, ?, ?, ?)",
                (provider, identity, kind, _payload(provider, identity, kind, flag)),
            )
        conn.commit()
        if orphan_gap:
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute(
                "INSERT INTO terminal_gap(provider, identity, kind, fact_json) "
                "VALUES (?, ?, ?, ?)",
                ("coinalyze", "missing", "unsupported_mapping", "{}"),
            )
            conn.commit()
            conn.execute("PRAGMA foreign_keys=ON")
            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            if not violations:
                raise AssertionError(
                    "orphan gap did not produce a foreign key violation"
                )
        else:
            conn.execute(
                "INSERT INTO terminal_gap(provider, identity, kind, fact_json) "
                "VALUES (?, ?, ?, ?)",
                ("coinalyze", "unsupported:GAP", "unsupported_mapping", "{}"),
            )
        conn.execute(
            "INSERT INTO coinalyze_ledger(id, charged) VALUES (1, ?)",
            (ledger_charged,),
        )
        ended = "2026-08-27T21:00:00+00:00" if finished_run else None
        stop = "interrupted" if finished_run else None
        conn.execute(
            "INSERT INTO run_metadata(run_id, started_at, ended_at, stop_reason, attempt_hi, "
            "network_calls, start_snapshot_json, error_count, network_sample_json, "
            "pre_capacity_json, post_capacity_json, capacity_blocked, attempt_delta, "
            "completion_delta, gap_delta, byte_delta, open_coinalyze_charges, counts_json) "
            "VALUES (?, ?, ?, ?, 0, 0, '{}', 0, '[]', '{}', '{}', 0, 0, 0, 0, 0, 0, '{}')",
            ("a" * 64, "2026-08-27T20:24:52.741721+00:00", ended, stop),
        )
        if completion_row:
            conn.execute(
                "INSERT INTO completion(provider, identity, content_sha256, content_path, "
                "listed_bytes, retrieved_at, revision_json, validation_state) "
                "VALUES (?, ?, ?, ?, 1, ?, '{}', 'checksum_verified')",
                ("binance_vision", "k1", "b" * 64, "/tmp/x", "2026-08-27T20:24:52+00:00"),
            )
        if not omit_seal_head:
            conn.execute(
                "INSERT INTO seal_head(id, receipt_sha256, receipt_path, prefix_digest, "
                "attempt_hi, completion_hi, sidecar_hi, charge_hi, transition_hi, run_hi, "
                "seal_hi, predecessor_sha256) VALUES (1, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, NULL)",
                (receipt_sha, f"plan_receipts/{receipt_sha}.json", "c" * 64),
            )
        if omit_seal_head:
            conn.execute("DROP TABLE seal_head")
        conn.commit()
    finally:
        conn.close()


def build_store(
    tmp_path: Path,
    *,
    extra_child: str | None = None,
    skip: str | None = None,
    corrupt_sqlite: bool = False,
    **sqlite_kwargs: Any,
) -> dict[str, Any]:
    repo = tmp_path / "repo"
    store = repo / "data" / "cex002_qualify"
    tree = store / "gate2"
    for relative, payload in (
        (retire.ACQUISITION_SOURCE_RELATIVE, b"source\n"),
        (retire.ACQUISITION_TEST_RELATIVE, b"test\n"),
        (retire.ACQUISITION_CLI_RELATIVE, b"cli\n"),
    ):
        _write(repo / relative, payload)
    source_sha = _sha(b"source\n")
    test_sha = _sha(b"test\n")
    cli_sha = _sha(b"cli\n")
    for name in ("plan_receipts", "run_receipts", "terminal", "tmp"):
        (tree / name).mkdir(parents=True)
        os.chmod(tree / name, 0o700)
    os.chmod(tree, 0o700)
    plan_identity = "b" * 64
    counts = {
        "plan_objects": 6,
        "coinalyze_logical_receipts": 2,
        "retained_credit_objects": 2,
        "coinalyze_unsupported": 1,
    }
    if sqlite_kwargs.get("retained_true") == 1:
        counts["retained_credit_objects"] = 1
    receipt_doc = {
        "schema_version": PLAN_SCHEMA,
        "ticket": "CEX-002",
        "policy_identity": PLAN_POLICY,
        "plan_identity": plan_identity,
        "counts": counts,
    }
    receipt_body = _canonical(receipt_doc)
    receipt_sha = _sha(receipt_body)
    _write(tree / "plan_receipts" / f"{receipt_sha}.json", receipt_body)
    sqlite_path = tree / "state.sqlite"
    device_label = f"dev:{tree.stat().st_dev}"
    if corrupt_sqlite:
        _write(sqlite_path, b"not a sqlite database")
    else:
        _create_sqlite(
            sqlite_path,
            plan_identity=plan_identity,
            receipt_sha=receipt_sha,
            source_sha=source_sha,
            cli_sha=cli_sha,
            device_label=device_label,
            **sqlite_kwargs,
        )
        os.chmod(sqlite_path, 0o600)
    _write(tree / "state.sqlite-wal", b"")
    _write(tree / "state.sqlite-shm", b"")
    _write(tree / "acquisition.lock", b"")
    if extra_child:
        if extra_child.endswith("/"):
            (tree / extra_child.rstrip("/")).mkdir()
        else:
            _write(tree / extra_child, b"extra")
    if skip == "tmp":
        os.rmdir(tree / "tmp")
    relatives = [
        ".",
        "acquisition.lock",
        "plan_receipts",
        f"plan_receipts/{receipt_sha}.json",
        "run_receipts",
        "state.sqlite",
        "state.sqlite-shm",
        "state.sqlite-wal",
        "terminal",
        "tmp",
    ]
    if extra_child:
        relatives.append(extra_child.rstrip("/"))
    if skip is not None:
        relatives = [item for item in relatives if item != skip and not item.startswith(f"{skip}/")]
    entries = [_entry(tree, item) for item in relatives]
    file_bytes = sum(int(item["size"]) for item in entries if item["type"] == "regular_file")
    true_count = 1 if sqlite_kwargs.get("retained_true") == 1 else 2
    false_count = 2 if sqlite_kwargs.get("retained_true") == 1 else 1
    table_counts = {
        "attempt": 0,
        "authority": 1,
        "charge_transition": 0,
        "coinalyze_charge": 0,
        "coinalyze_ledger": 1,
        "completion": 1 if sqlite_kwargs.get("completion_row") else 0,
        "plan_entry": 6,
        "run_metadata": 1,
        "run_publication": 0,
        "run_seal": 0,
        "seal_head": 0 if sqlite_kwargs.get("omit_seal_head") else 1,
        "sidecar_fact": 0,
        "terminal_gap": 1,
    }
    authority = {
        "adr": "ADR-0030",
        "database": {
            "application_id": sqlite_kwargs.get("application_id", APP_ID),
            "authority": {
                "acquisition_cli_sha256": cli_sha,
                "acquisition_source_sha256": source_sha,
                "created_at": "2026-08-27T18:11:33.135154+00:00",
                "destination": "data/cex002_qualify",
                "device": device_label,
                "plan_identity": plan_identity,
                "plan_receipt_sha256": receipt_sha,
                "policy_identity": PLAN_POLICY,
            },
            "coinalyze_ledger_charged": sqlite_kwargs.get("ledger_charged", 0),
            "foreign_key_violation_count": 1 if sqlite_kwargs.get("orphan_gap") else 0,
            "integrity_check": "ok",
            "plan_entry_counts": {
                "binance_vision/binance_object": 3,
                "coinalyze/coinalyze_inventory": 1,
                "coinalyze/coinalyze_liquidation": 1,
                "coinalyze/coinalyze_unsupported_gap": 1,
            },
            "plan_entry_retained_counts": {
                "false": false_count,
                "not_applicable": 3,
                "true": true_count,
            },
            "run": {
                "attempt_delta": 0,
                "attempt_hi": 0,
                "byte_delta": 0,
                "capacity_blocked": 0,
                "completion_delta": 0,
                "ended_at": "2026-08-27T21:00:00+00:00"
                if sqlite_kwargs.get("finished_run")
                else None,
                "error_count": 0,
                "gap_delta": 0,
                "network_calls": 0,
                "open_coinalyze_charges": 0,
                "run_id": "a" * 64,
                "seq": 1,
                "started_at": "2026-08-27T20:24:52.741721+00:00",
                "stop_reason": "interrupted" if sqlite_kwargs.get("finished_run") else None,
            },
            "seal_head": {
                "attempt_hi": 0,
                "charge_hi": 0,
                "completion_hi": 0,
                "plan_receipt_sha256": receipt_sha,
                "predecessor_sha256": None,
                "prefix_digest": "c" * 64,
                "run_hi": 0,
                "seal_hi": 0,
                "sidecar_hi": 0,
                "transition_hi": 0,
            },
            "table_counts": table_counts,
            "terminal_gap_counts": {"unsupported_mapping": 1},
            "user_version": sqlite_kwargs.get("user_version", 7),
        },
        "execution_context": {
            "accepted_acquisition_cli_sha256": cli_sha,
            "accepted_acquisition_source_sha256": source_sha,
            "accepted_acquisition_test_sha256": test_sha,
            "integration_commit": "test-commit",
        },
        "filesystem": {
            "active_name": "gate2",
            "destination_name": receipt_sha,
            "device": int(tree.stat().st_dev),
            "entries": entries,
            "entry_count": len(entries),
            "regular_file_bytes": file_bytes,
            "retirement_parent": "gate2_retired",
            "store_root": "data/cex002_qualify",
        },
        "observed_at": "2026-08-28T00:00:00Z",
        "plan_receipt": {
            "coinalyze_logical_receipts": 2,
            "declared_retained_credit_objects": counts["retained_credit_objects"],
            "plan_identity": plan_identity,
            "plan_objects": 6,
            "policy_identity": PLAN_POLICY,
            "schema_version": PLAN_SCHEMA,
            "sha256": receipt_sha,
            "typed_gaps": 1,
        },
        "schema_version": retire.AUTHORITY_SCHEMA,
        "ticket": "CEX-002",
    }
    authority_path = repo / retire.AUTHORITY_RELATIVE
    body = _canonical(authority)
    digest = _write(authority_path, body)
    return {
        "repo": repo,
        "store": store,
        "tree": tree,
        "authority": authority,
        "authority_path": authority_path,
        "authority_digest": digest,
        "receipt_sha": receipt_sha,
        "source_sha": source_sha,
        "test_sha": test_sha,
        "cli_sha": cli_sha,
    }


def _run_inspect(built: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return retire.inspect_gate2(
        repository=built["repo"],
        authority_path=built["authority_path"],
        authority_digest=built["authority_digest"],
        **kwargs,
    )


def _run_retire(built: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    confirm = kwargs.pop("confirm", built["receipt_sha"])
    return retire.retire_gate2(
        repository=built["repo"],
        confirm=confirm,
        authority_path=built["authority_path"],
        authority_digest=built["authority_digest"],
        **kwargs,
    )


def _load_cli() -> Any:
    path = REPOSITORY / "scripts/research/retire_binance_usdm_harmonic_gate2.py"
    spec = importlib.util.spec_from_file_location("gate2_retirement_cli", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _snapshot(path: Path) -> dict[str, tuple[int, int, str | None]]:
    out: dict[str, tuple[int, int, str | None]] = {}
    for current, dirs, files in os.walk(path):
        rel_dir = os.path.relpath(current, path)
        for name in dirs + files:
            full = Path(current) / name
            rel = name if rel_dir == "." else str(Path(rel_dir) / name)
            st = os.lstat(full)
            digest = _sha(full.read_bytes()) if stat.S_ISREG(st.st_mode) else None
            out[rel] = (st.st_ino, st.st_size, digest)
    st = os.lstat(path)
    out["."] = (st.st_ino, st.st_size, None)
    return out


def test_inspect_succeeds_without_mutation(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    before = _snapshot(built["tree"])
    parent = built["store"] / "gate2_retired"
    result = _run_inspect(built)
    after = _snapshot(built["tree"])
    assert after == before
    assert not parent.exists()
    assert result["schema_version"] == retire.INSPECT_SCHEMA
    assert result["lock_held"] is True
    assert result["sqlite_immutable"] is True
    assert result["plan_rows"] == 6
    assert result["retained_true"] == 2
    assert result["typed_gaps"] == 1
    assert result["zero_acquisition_facts"] is True
    assert SECRET.encode() not in retire.canonical_json(result)


def test_retire_succeeds_preserving_inode_mode_size_and_hashes(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    before = _snapshot(built["tree"])
    origin_stat = built["tree"].stat()
    result = _run_retire(built)
    dest = (
        built["store"]
        / "gate2_retired"
        / built["receipt_sha"]
    )
    assert not built["tree"].exists()
    assert dest.is_dir()
    after = _snapshot(dest)
    assert after == before
    dest_stat = dest.stat()
    assert dest_stat.st_ino == origin_stat.st_ino
    assert dest_stat.st_dev == origin_stat.st_dev
    assert stat.S_IMODE(dest_stat.st_mode) == 0o700
    assert result["schema_version"] == retire.RECEIPT_SCHEMA
    assert frozenset(result) == retire.RECEIPT_KEYS
    assert result["rename_noreplace"] is True
    assert result["parent_fsync"] is True
    assert result["syncfs"] is True
    assert result["lock_held"] is True
    assert result["plan_receipt_sha256"] == built["receipt_sha"]
    assert result["before_inventory_digest"] == result["after_inventory_digest"]
    assert len(retire.canonical_json(result)) <= retire.MAX_OUTPUT_BYTES


def test_authority_byte_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    with pytest.raises(retire.SafeRetirementError, match="authority hash changed"):
        retire.inspect_gate2(
            repository=built["repo"],
            authority_path=built["authority_path"],
            authority_digest="a" * 64,
        )


def test_authority_schema_mismatch_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    document = json.loads(built["authority_path"].read_text(encoding="utf-8"))
    document["schema_version"] = "other"
    body = _canonical(document)
    built["authority_path"].write_bytes(body)
    with pytest.raises(retire.SafeRetirementError, match="schema version changed"):
        retire.inspect_gate2(
            repository=built["repo"],
            authority_path=built["authority_path"],
            authority_digest=_sha(body),
        )


def test_authority_type_mismatch_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    document = json.loads(built["authority_path"].read_text(encoding="utf-8"))
    document["filesystem"]["entry_count"] = True
    body = _canonical(document)
    built["authority_path"].write_bytes(body)
    with pytest.raises(retire.SafeRetirementError, match="exact integer"):
        retire.inspect_gate2(
            repository=built["repo"],
            authority_path=built["authority_path"],
            authority_digest=_sha(body),
        )


def test_authority_path_mismatch_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    document = json.loads(built["authority_path"].read_text(encoding="utf-8"))
    document["filesystem"]["store_root"] = "data/other"
    body = _canonical(document)
    built["authority_path"].write_bytes(body)
    with pytest.raises(retire.SafeRetirementError, match="store root path changed"):
        retire.inspect_gate2(
            repository=built["repo"],
            authority_path=built["authority_path"],
            authority_digest=_sha(body),
        )


def test_execution_context_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    (built["repo"] / retire.ACQUISITION_SOURCE_RELATIVE).write_bytes(b"tampered\n")
    with pytest.raises(retire.SafeRetirementError, match="execution-context source hash"):
        _run_inspect(built)


def test_cli_rejects_arbitrary_store_target() -> None:
    cli = _load_cli()
    with pytest.raises(SystemExit):
        cli.main(["inspect", "--store-root", "/tmp/data"])
    with pytest.raises(SystemExit):
        cli.main(["inspect", "/tmp/data"])
    with pytest.raises(SystemExit):
        cli.main(["retire", "--confirm", "a" * 64, "--destination", "/tmp"])


def test_cli_rejects_wrong_confirm_before_store_access() -> None:
    cli = _load_cli()
    assert cli.main(["retire", "--confirm", "0" * 64]) == retire.EXIT_SAFE


def test_missing_entry_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    os.rmdir(built["tree"] / "tmp")
    with pytest.raises(retire.SafeRetirementError, match="missing"):
        _run_inspect(built)


def test_extra_entry_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    (built["tree"] / "stray.bin").write_bytes(b"extra")
    with pytest.raises(retire.SafeRetirementError, match="extra"):
        _run_inspect(built)


def test_symlink_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    os.unlink(built["tree"] / "acquisition.lock")
    os.symlink("state.sqlite", built["tree"] / "acquisition.lock")
    with pytest.raises(retire.SafeRetirementError, match="symlink"):
        _run_inspect(built)


def test_special_file_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    os.unlink(built["tree"] / "acquisition.lock")
    os.mkfifo(built["tree"] / "acquisition.lock")
    with pytest.raises(retire.SafeRetirementError, match="special"):
        _run_inspect(built)


def test_replaced_inode_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    lock = built["tree"] / "acquisition.lock"
    os.unlink(lock)
    lock.write_bytes(b"")
    os.chmod(lock, 0o600)
    with pytest.raises(retire.SafeRetirementError, match="inventory entry changed"):
        _run_inspect(built)


def test_tree_device_mismatch_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    document = json.loads(built["authority_path"].read_text(encoding="utf-8"))
    document["filesystem"]["device"] = int(document["filesystem"]["device"]) + 1
    for entry in document["filesystem"]["entries"]:
        entry["device"] = document["filesystem"]["device"]
    document["database"]["authority"]["device"] = f"dev:{document['filesystem']['device']}"
    body = _canonical(document)
    built["authority_path"].write_bytes(body)
    with pytest.raises(retire.SafeRetirementError, match="device"):
        retire.inspect_gate2(
            repository=built["repo"],
            authority_path=built["authority_path"],
            authority_digest=_sha(body),
        )


def test_inventory_size_mismatch_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    (built["tree"] / "acquisition.lock").write_bytes(b"x")
    with pytest.raises(retire.SafeRetirementError, match="inventory entry changed"):
        _run_inspect(built)


def test_file_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    receipt = next((built["tree"] / "plan_receipts").iterdir())
    receipt.write_bytes(receipt.read_bytes() + b"\n")
    with pytest.raises(retire.SafeRetirementError, match="inventory entry changed|hash"):
        _run_inspect(built)


def test_wal_size_mismatch_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    (built["tree"] / "state.sqlite-wal").write_bytes(b"dirty")
    with pytest.raises(retire.SafeRetirementError, match="inventory entry changed"):
        _run_inspect(built)


def test_lock_contention_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    fd = os.open(built["tree"] / "acquisition.lock", os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(retire.SafeRetirementError, match="another writer"):
            _run_inspect(built)
    finally:
        os.close(fd)


def test_preexisting_retirement_parent_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    (built["store"] / "gate2_retired").mkdir()
    with pytest.raises(retire.SafeRetirementError, match="retirement parent already exists"):
        _run_retire(built)
    assert built["tree"].is_dir()


def test_preexisting_destination_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def _mkdir(dir_fd: int, name: str, mode: int) -> None:
        os.mkdir(name, mode, dir_fd=dir_fd)
        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)
        try:
            os.mkdir(built["receipt_sha"], 0o700, dir_fd=child)
        finally:
            os.close(child)

    with pytest.raises(retire.SafeRetirementError, match="destination already exists"):
        _run_retire(built, hooks=retire.RetirementHooks(mkdir=_mkdir))
    assert built["tree"].is_dir()


def test_noreplace_collision_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def _race(old_dir: int, old_name: str, new_dir: int, new_name: str) -> None:
        os.mkdir(new_name, 0o700, dir_fd=new_dir)
        retire.renameat2_noreplace(old_dir, old_name, new_dir, new_name)

    with pytest.raises(retire.SafeRetirementError):
        _run_retire(built, hooks=retire.RetirementHooks(renameat2=_race))
    assert built["tree"].is_dir()
    assert (built["store"] / "gate2_retired").is_dir()


def test_wrong_application_id_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path, application_id=1)
    _rewrite_authority(
        built, lambda document: document["database"].__setitem__("application_id", APP_ID)
    )
    with pytest.raises(retire.SafeRetirementError, match="application_id"):
        _run_inspect(built)


def test_wrong_user_version_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path, user_version=6)
    _rewrite_authority(
        built, lambda document: document["database"].__setitem__("user_version", 7)
    )
    with pytest.raises(retire.SafeRetirementError, match="user_version"):
        _run_inspect(built)


def test_integrity_check_failure_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path, corrupt_sqlite=True)
    with pytest.raises(
        retire.SafeRetirementError,
        match="SQLite",
    ) as raised:
        _run_inspect(built)
    assert not isinstance(raised.value, retire.IndeterminateRetirementError)


def test_foreign_key_failure_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path, orphan_gap=True)
    _rewrite_authority(
        built,
        lambda document: document["database"].__setitem__(
            "foreign_key_violation_count", 0
        ),
    )
    with pytest.raises(retire.SafeRetirementError, match="foreign key"):
        _run_inspect(built)


def test_wrong_tables_are_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path, omit_seal_head=True)
    with pytest.raises(retire.SafeRetirementError, match="table set changed"):
        _run_inspect(built)


def test_extra_table_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path, extra_table=True)
    with pytest.raises(retire.SafeRetirementError, match="table set changed"):
        _run_inspect(built)


def test_wrong_plan_receipt_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    _rewrite_authority(
        built,
        lambda document: document["plan_receipt"].__setitem__("plan_objects", 99),
    )
    with pytest.raises(retire.SafeRetirementError, match="plan object count"):
        _run_inspect(built)


def test_wrong_authority_row_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    _mutate_sqlite(
        built,
        lambda conn: conn.execute("UPDATE authority SET plan_identity=?", ("e" * 64,)),
    )
    with pytest.raises(retire.SafeRetirementError, match="plan identity"):
        _run_inspect(built)


def test_wrong_plan_counts_are_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def _insert(conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO plan_entry(provider, identity, kind, payload_json) "
            "VALUES (?, ?, ?, ?)",
            (
                "binance_vision",
                "k4",
                "binance_object",
                _payload("binance_vision", "k4", "binance_object", False),
            ),
        )

    _mutate_sqlite(built, _insert)
    with pytest.raises(retire.SafeRetirementError, match="plan entry distribution|table count"):
        _run_inspect(built)


def test_wrong_retained_counts_are_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def _mutate(document: dict[str, Any]) -> None:
        document["database"]["plan_entry_retained_counts"]["true"] = 90
        document["database"]["plan_entry_retained_counts"]["false"] = 0

    _rewrite_authority(built, _mutate)
    with pytest.raises(retire.SafeRetirementError, match="retained label counts"):
        _run_inspect(built)


def test_wrong_gap_counts_are_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def _insert(conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO plan_entry(provider, identity, kind, payload_json) "
            "VALUES (?, ?, ?, ?)",
            (
                "coinalyze",
                "unsupported:OTHER",
                "coinalyze_unsupported_gap",
                _payload(
                    "coinalyze",
                    "unsupported:OTHER",
                    "coinalyze_unsupported_gap",
                    None,
                ),
            ),
        )
        conn.execute(
            "INSERT INTO terminal_gap(provider, identity, kind, fact_json) "
            "VALUES (?, ?, ?, ?)",
            ("coinalyze", "unsupported:OTHER", "unsupported_mapping", "{}"),
        )

    _mutate_sqlite(built, _insert)
    with pytest.raises(retire.SafeRetirementError, match="terminal gap counts|table count"):
        _run_inspect(built)


def test_wrong_run_semantics_are_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path, finished_run=True)
    with pytest.raises(retire.SafeRetirementError, match="end time|stop reason"):
        _run_inspect(built)


def test_wrong_fact_counts_are_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def _insert(conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO completion(provider, identity, content_sha256, content_path, "
            "listed_bytes, retrieved_at, revision_json, validation_state) "
            "VALUES (?, ?, ?, ?, 1, ?, '{}', 'checksum_verified')",
            (
                "binance_vision",
                "k1",
                "b" * 64,
                "/tmp/x",
                "2026-08-27T20:24:52+00:00",
            ),
        )

    _mutate_sqlite(built, _insert)
    with pytest.raises(retire.SafeRetirementError, match="table count changed"):
        _run_inspect(built)


def test_wrong_ledger_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    _mutate_sqlite(
        built,
        lambda conn: conn.execute("UPDATE coinalyze_ledger SET charged=9"),
    )
    with pytest.raises(retire.SafeRetirementError, match="ledger"):
        _run_inspect(built)


def test_wrong_seal_head_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    _mutate_sqlite(
        built, lambda conn: conn.execute("UPDATE seal_head SET attempt_hi=3")
    )
    with pytest.raises(retire.SafeRetirementError, match="seal head attempt_hi"):
        _run_inspect(built)


def test_sqlite_is_immutable_read_only(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    seen: dict[str, Any] = {}

    def _on_sqlite(uri: str, conn: sqlite3.Connection) -> None:
        seen["uri"] = uri
        seen["query_only"] = int(conn.execute("PRAGMA query_only").fetchone()[0])
        path_part = uri.split("?", 1)[0]
        seen["uses_file_descriptor"] = "/proc/self/fd/" in path_part
        seen["uses_state_name"] = path_part.endswith("/" + retire.SQLITE_NAME)

    _run_inspect(built, hooks=retire.RetirementHooks(on_sqlite=_on_sqlite))
    assert seen["query_only"] == 1
    assert "mode=ro" in seen["uri"]
    assert "immutable=1" in seen["uri"]
    assert seen["uses_file_descriptor"] is True
    assert seen["uses_state_name"] is False


def test_acquisition_module_is_never_imported(tmp_path: Path) -> None:
    source = Path(retire.__file__).read_text(encoding="utf-8")
    cli = (REPOSITORY / "scripts/research/retire_binance_usdm_harmonic_gate2.py").read_text(
        encoding="utf-8"
    )
    assert "from cryptofactors.acquisition.binance_usdm_harmonic_acquisition" not in source
    assert "import cryptofactors.acquisition.binance_usdm_harmonic_acquisition" not in source
    assert "binance_usdm_harmonic_acquisition" not in cli
    before = set(sys.modules)
    _run_inspect(build_store(tmp_path))
    added = set(sys.modules) - before
    assert not any(
        name.endswith("binance_usdm_harmonic_acquisition") and "retirement" not in name
        for name in added
    )


def test_injected_hash_failure_is_safe(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def _boom(_fd: int) -> str:
        raise retire.SafeRetirementError("hash failed")

    with pytest.raises(retire.SafeRetirementError, match="hash failed"):
        _run_inspect(built, hooks=retire.RetirementHooks(stream_hash=_boom))
    assert built["tree"].is_dir()
    assert not (built["store"] / "gate2_retired").exists()


def test_injected_mkdir_failure_is_safe(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def _boom(_dir_fd: int, _name: str, _mode: int) -> None:
        raise OSError("mkdir failed")

    with pytest.raises(retire.SafeRetirementError):
        _run_retire(built, hooks=retire.RetirementHooks(mkdir=_boom))
    assert built["tree"].is_dir()
    assert not (built["store"] / "gate2_retired").exists()


def test_injected_rename_failure_is_safe_no_cleanup(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def _boom(_old: int, _old_name: str, _new: int, _new_name: str) -> None:
        raise OSError(errno.EIO, "rename failed")

    with pytest.raises(retire.SafeRetirementError):
        _run_retire(built, hooks=retire.RetirementHooks(renameat2=_boom))
    assert built["tree"].is_dir()
    assert (built["store"] / "gate2_retired").is_dir()


def test_injected_parent_fsync_failure_after_rename_is_indeterminate(
    tmp_path: Path,
) -> None:
    built = build_store(tmp_path)
    calls = {"n": 0}

    def _fsync(fd: int) -> None:
        calls["n"] += 1
        if calls["n"] >= 2:
            raise OSError("fsync failed")
        os.fsync(fd)

    with pytest.raises(retire.IndeterminateRetirementError) as raised:
        _run_retire(built, hooks=retire.RetirementHooks(fsync=_fsync))
    assert raised.value.source_exists is False
    assert raised.value.destination_exists is True
    assert not built["tree"].exists()
    assert (built["store"] / "gate2_retired" / built["receipt_sha"]).is_dir()


def test_injected_syncfs_failure_after_rename_is_indeterminate(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def _boom(_fd: int) -> None:
        raise OSError("syncfs failed")

    with pytest.raises(retire.IndeterminateRetirementError) as raised:
        _run_retire(built, hooks=retire.RetirementHooks(syncfs=_boom))
    assert raised.value.source_exists is False
    assert raised.value.destination_exists is True
    assert not built["tree"].exists()


def test_injected_post_proof_failure_is_indeterminate_without_cleanup(
    tmp_path: Path,
) -> None:
    built = build_store(tmp_path)

    def _boom() -> None:
        raise RuntimeError("post-proof failed")

    with pytest.raises(retire.IndeterminateRetirementError) as raised:
        _run_retire(built, hooks=retire.RetirementHooks(before_post_proof=_boom))
    assert raised.value.source_exists is False
    assert raised.value.destination_exists is True
    assert not built["tree"].exists()
    assert (built["store"] / "gate2_retired" / built["receipt_sha"]).is_dir()


def test_output_is_bounded_and_has_exact_receipt_fields(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    inspected = _run_inspect(built)
    assert frozenset(inspected) == retire.INSPECT_KEYS
    assert len(retire.canonical_json(inspected)) <= retire.MAX_OUTPUT_BYTES
    retired = _run_retire(built)
    assert frozenset(retired) == retire.RECEIPT_KEYS
    body = retire.canonical_json(retired)
    assert len(body) <= retire.MAX_OUTPUT_BYTES
    assert SECRET.encode() not in body
    assert b"k1" not in body


def test_streaming_hash_is_chunked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    built = build_store(tmp_path)
    blob = os.urandom(retire.CHUNK_SIZE + 16)
    target = built["tree"] / "tmp" / "chunk.bin"
    target.write_bytes(blob)
    os.chmod(target, 0o600)

    def _add(document: dict[str, Any]) -> None:
        document["filesystem"]["entries"].append(_entry(built["tree"], "tmp/chunk.bin"))

    _rewrite_authority(built, _add)
    _refresh_authority_files(built)
    reads: list[int] = []
    real_read = os.read

    def _spy(fd: int, n: int) -> bytes:
        chunk = real_read(fd, n)
        reads.append(len(chunk))
        return chunk

    monkeypatch.setattr(os, "read", _spy)
    _run_inspect(built)
    assert any(size == retire.CHUNK_SIZE for size in reads)


def test_inspect_does_not_create_retirement_parent(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    _run_inspect(built)
    assert not (built["store"] / "gate2_retired").exists()


def test_wrong_confirm_is_rejected_before_lock(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    with pytest.raises(retire.SafeRetirementError, match="confirmation digest"):
        _run_retire(built, confirm="f" * 64)
    assert built["tree"].is_dir()


def test_active_root_replacement_before_rename_is_rejected(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def _replace() -> None:
        hidden = built["store"] / "gate2_hidden"
        os.rename(built["tree"], hidden)
        built["tree"].mkdir()
        os.chmod(built["tree"], 0o700)

    with pytest.raises(
        retire.SafeRetirementError,
        match="no longer names its held descriptor|inventory identity",
    ):
        _run_retire(built, hooks=retire.RetirementHooks(before_rename=_replace))
    assert (built["store"] / "gate2_hidden").is_dir()
    assert not (built["store"] / "gate2_retired" / built["receipt_sha"]).exists()


def test_retirement_parent_replacement_before_rename_is_rejected(
    tmp_path: Path,
) -> None:
    built = build_store(tmp_path)

    def _replace() -> None:
        parent = built["store"] / "gate2_retired"
        os.rename(parent, built["store"] / "gate2_retired_hidden")
        parent.mkdir()
        os.chmod(parent, 0o700)

    with pytest.raises(
        retire.SafeRetirementError,
        match="no longer names its held descriptor|inventory identity",
    ):
        _run_retire(built, hooks=retire.RetirementHooks(before_rename=_replace))
    assert built["tree"].is_dir()


def test_retirement_parent_replacement_after_rename_is_indeterminate(
    tmp_path: Path,
) -> None:
    built = build_store(tmp_path)

    def _replace() -> None:
        parent = built["store"] / "gate2_retired"
        os.rename(parent, built["store"] / "gate2_retired_hidden")
        parent.mkdir()
        os.chmod(parent, 0o700)

    with pytest.raises(retire.IndeterminateRetirementError):
        _run_retire(built, hooks=retire.RetirementHooks(after_rename=_replace))
    assert not built["tree"].exists()
    assert (built["store"] / "gate2_retired_hidden" / built["receipt_sha"]).is_dir()


def test_receipt_inode_replacement_after_inventory_is_rejected(
    tmp_path: Path,
) -> None:
    built = build_store(tmp_path)
    receipt = next((built["tree"] / "plan_receipts").iterdir())

    def _replace() -> None:
        payload = receipt.read_bytes()
        receipt.unlink()
        receipt.write_bytes(payload)
        os.chmod(receipt, 0o600)

    with pytest.raises(
        retire.SafeRetirementError, match="inventory identity|held descriptor"
    ):
        _run_inspect(built, hooks=retire.RetirementHooks(after_inventory=_replace))


def test_sqlite_inode_replacement_after_inventory_is_rejected(
    tmp_path: Path,
) -> None:
    built = build_store(tmp_path)
    state = built["tree"] / "state.sqlite"

    def _replace() -> None:
        payload = state.read_bytes()
        state.unlink()
        state.write_bytes(payload)
        os.chmod(state, 0o600)

    with pytest.raises(
        retire.SafeRetirementError, match="inventory identity|held descriptor"
    ):
        _run_inspect(built, hooks=retire.RetirementHooks(after_inventory=_replace))


def test_pre_rename_store_parent_fsync_failure_is_safe(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def _fsync(_fd: int) -> None:
        raise OSError("fsync failed")

    with pytest.raises(retire.SafeRetirementError):
        _run_retire(built, hooks=retire.RetirementHooks(fsync=_fsync))
    assert built["tree"].is_dir()
    assert not (built["store"] / "gate2_retired" / built["receipt_sha"]).exists()


class _BrokenWriter:
    def __init__(self, *, fail_write: bool = False, fail_flush: bool = False) -> None:
        self.buffer = self
        self.payload = b""
        self._fail_write = fail_write
        self._fail_flush = fail_flush

    def write(self, data: bytes) -> int:
        if self._fail_write:
            raise BrokenPipeError()
        self.payload += data
        return len(data)

    def flush(self) -> None:
        if self._fail_flush:
            raise BrokenPipeError()


def _cli_document() -> dict[str, Any]:
    return {
        "schema_version": retire.INSPECT_SCHEMA,
        "ticket": "CEX-002",
        "command": "inspect",
    }


def test_cli_inspect_write_failure_is_safe() -> None:
    cli = _load_cli()
    err = io.StringIO()
    code = cli.main(
        ["inspect"],
        inspect_fn=lambda **_kwargs: _cli_document(),
        stdout=_BrokenWriter(fail_write=True),
        stderr=err,
    )
    assert code == retire.EXIT_SAFE
    assert "inspection output could not be delivered" in err.getvalue()


def test_cli_inspect_flush_failure_is_safe() -> None:
    cli = _load_cli()
    err = io.StringIO()
    code = cli.main(
        ["inspect"],
        inspect_fn=lambda **_kwargs: _cli_document(),
        stdout=_BrokenWriter(fail_flush=True),
        stderr=err,
    )
    assert code == retire.EXIT_SAFE
    assert "inspection output could not be delivered" in err.getvalue()


def test_cli_retire_write_failure_is_indeterminate(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    cli = _load_cli()
    err = io.StringIO()
    code = cli.main(
        ["retire", "--confirm", built["receipt_sha"]],
        repository=built["repo"],
        authority_path=built["authority_path"],
        authority_digest=built["authority_digest"],
        stdout=_BrokenWriter(fail_write=True),
        stderr=err,
    )
    assert code == retire.EXIT_INDETERMINATE
    assert "retirement receipt could not be delivered" in err.getvalue()
    assert (built["store"] / "gate2_retired" / built["receipt_sha"]).is_dir()
    assert not built["tree"].exists()


def test_cli_retire_flush_failure_is_indeterminate(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    cli = _load_cli()
    err = io.StringIO()
    code = cli.main(
        ["retire", "--confirm", built["receipt_sha"]],
        repository=built["repo"],
        authority_path=built["authority_path"],
        authority_digest=built["authority_digest"],
        stdout=_BrokenWriter(fail_flush=True),
        stderr=err,
    )
    assert code == retire.EXIT_INDETERMINATE
    assert "retirement receipt could not be delivered" in err.getvalue()
    assert (built["store"] / "gate2_retired" / built["receipt_sha"]).is_dir()
    assert not built["tree"].exists()


def test_cli_inspect_writes_canonical_output(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    cli = _load_cli()
    stdout = _BrokenWriter()
    code = cli.main(
        ["inspect"],
        repository=built["repo"],
        authority_path=built["authority_path"],
        authority_digest=built["authority_digest"],
        stdout=stdout,
        stderr=io.StringIO(),
    )
    assert code == retire.EXIT_COMPLETE
    document = json.loads(stdout.payload.decode("utf-8"))
    assert document["schema_version"] == retire.INSPECT_SCHEMA
    assert stdout.payload == retire.canonical_json(document)
    assert frozenset(document) == retire.INSPECT_KEYS


def test_production_authority_bytes_authenticate_offline() -> None:
    path = REPOSITORY / retire.AUTHORITY_RELATIVE
    payload = path.read_bytes()
    assert retire.sha256_bytes(payload) == retire.AUTHORITY_SHA256
    document = retire.load_authority_bytes(
        payload, expected_digest=retire.AUTHORITY_SHA256
    )
    assert document["ticket"] == "CEX-002"
    assert document["schema_version"] == retire.AUTHORITY_SCHEMA
    assert document["filesystem"]["store_root"] == retire.FIXED_STORE_ROOT


def _rewrite_authority(
    built: dict[str, Any],
    mutate: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    document = json.loads(built["authority_path"].read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(document)
    body = _canonical(document)
    digest = _write(built["authority_path"], body)
    built["authority"] = document
    built["authority_digest"] = digest
    return built


def _refresh_authority_files(built: dict[str, Any]) -> dict[str, Any]:
    tree = built["tree"]

    def _mutate(document: dict[str, Any]) -> None:
        entries = [_entry(tree, str(item["path"])) for item in document["filesystem"]["entries"]]
        document["filesystem"]["entries"] = entries
        document["filesystem"]["entry_count"] = len(entries)
        document["filesystem"]["regular_file_bytes"] = sum(
            int(item["size"]) for item in entries if item["type"] == "regular_file"
        )

    return _rewrite_authority(built, _mutate)


def _mutate_sqlite(built: dict[str, Any], mutate: Callable[[sqlite3.Connection], None]) -> None:
    conn = sqlite3.connect(built["tree"] / "state.sqlite")
    try:
        mutate(conn)
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()
    (built["tree"] / "state.sqlite-wal").write_bytes(b"")
    (built["tree"] / "state.sqlite-shm").write_bytes(b"")
    _refresh_authority_files(built)
