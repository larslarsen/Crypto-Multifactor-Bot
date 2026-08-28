"""CEX-002 Gate-2 retirement tool - ADR-0030 preservation, not acquisition.

Standalone inspect/retire of the rejected pre-network Gate-2 tree. This module uses
only the Python standard library and must not import the acquisition engine.
"""

from __future__ import annotations

import ctypes
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import stat
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TICKET_ID = "CEX-002"
AUTHORITY_SCHEMA = "cex002_rejected_gate2_retirement_authority_v1"
INSPECT_SCHEMA = "cex002_gate2_retirement_inspection_v1"
RECEIPT_SCHEMA = "cex002_gate2_retirement_receipt_v1"
AUTHORITY_RELATIVE = Path(
    "research/sprint_004/330_CEX002_REJECTED_GATE2_RETIREMENT_AUTHORITY.json"
)
AUTHORITY_SHA256 = "8c658629a8adcb4eecd46b84509221f83bb053dc916a83f546e4de8e14a4ebc1"
ACCEPTED_ACQUISITION_SOURCE_SHA256 = (
    "af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d"
)
ACCEPTED_ACQUISITION_TEST_SHA256 = (
    "40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624"
)
ACCEPTED_ACQUISITION_CLI_SHA256 = (
    "6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043"
)
INTEGRATION_COMMIT = "6e7ed863a6478a4a5a2967a23d44c5199b225a17"
ACQUISITION_SOURCE_RELATIVE = Path(
    "src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py"
)
ACQUISITION_TEST_RELATIVE = Path(
    "tests/acquisition/test_binance_usdm_harmonic_acquisition.py"
)
ACQUISITION_CLI_RELATIVE = Path(
    "scripts/research/acquire_binance_usdm_harmonic_release.py"
)
FIXED_STORE_ROOT = "data/cex002_qualify"
FIXED_ACTIVE_NAME = "gate2"
FIXED_RETIREMENT_PARENT = "gate2_retired"
RENAME_NOREPLACE = 1
CHUNK_SIZE = 64 * 1024
LOCK_NAME = "acquisition.lock"
SQLITE_NAME = "state.sqlite"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_OUTPUT_BYTES = 8192
EXIT_COMPLETE = 0
EXIT_USAGE = 1
EXIT_SAFE = 2
EXIT_INDETERMINATE = 3

AUTHORITY_KEYS = frozenset(
    {
        "adr",
        "database",
        "execution_context",
        "filesystem",
        "observed_at",
        "plan_receipt",
        "schema_version",
        "ticket",
    }
)
DATABASE_KEYS = frozenset(
    {
        "application_id",
        "authority",
        "coinalyze_ledger_charged",
        "foreign_key_violation_count",
        "integrity_check",
        "plan_entry_counts",
        "plan_entry_retained_counts",
        "run",
        "seal_head",
        "table_counts",
        "terminal_gap_counts",
        "user_version",
    }
)
DB_AUTHORITY_KEYS = frozenset(
    {
        "acquisition_cli_sha256",
        "acquisition_source_sha256",
        "created_at",
        "destination",
        "device",
        "plan_identity",
        "plan_receipt_sha256",
        "policy_identity",
    }
)
RUN_KEYS = frozenset(
    {
        "attempt_delta",
        "attempt_hi",
        "byte_delta",
        "capacity_blocked",
        "completion_delta",
        "ended_at",
        "error_count",
        "gap_delta",
        "network_calls",
        "open_coinalyze_charges",
        "run_id",
        "seq",
        "started_at",
        "stop_reason",
    }
)
SEAL_HEAD_KEYS = frozenset(
    {
        "attempt_hi",
        "charge_hi",
        "completion_hi",
        "plan_receipt_sha256",
        "predecessor_sha256",
        "prefix_digest",
        "run_hi",
        "seal_hi",
        "sidecar_hi",
        "transition_hi",
    }
)
FILESYSTEM_KEYS = frozenset(
    {
        "active_name",
        "destination_name",
        "device",
        "entries",
        "entry_count",
        "regular_file_bytes",
        "retirement_parent",
        "store_root",
    }
)
ENTRY_KEYS = frozenset({"device", "inode", "mode", "path", "sha256", "size", "type"})
PLAN_RECEIPT_AUTH_KEYS = frozenset(
    {
        "coinalyze_logical_receipts",
        "declared_retained_credit_objects",
        "plan_identity",
        "plan_objects",
        "policy_identity",
        "schema_version",
        "sha256",
        "typed_gaps",
    }
)
EXECUTION_CONTEXT_KEYS = frozenset(
    {
        "accepted_acquisition_cli_sha256",
        "accepted_acquisition_source_sha256",
        "accepted_acquisition_test_sha256",
        "integration_commit",
    }
)
RETAINED_COUNT_KEYS = frozenset({"false", "not_applicable", "true"})
TABLE_COUNT_KEYS = frozenset(
    {
        "attempt",
        "authority",
        "charge_transition",
        "coinalyze_charge",
        "coinalyze_ledger",
        "completion",
        "plan_entry",
        "run_metadata",
        "run_publication",
        "run_seal",
        "seal_head",
        "sidecar_fact",
        "terminal_gap",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "ticket",
        "authority_sha256",
        "plan_identity",
        "plan_receipt_sha256",
        "source",
        "destination",
        "before_inventory_digest",
        "after_inventory_digest",
        "entry_count",
        "regular_file_bytes",
        "lock_held",
        "rename_noreplace",
        "parent_fsync",
        "syncfs",
        "started_at",
        "ended_at",
    }
)
INSPECT_KEYS = frozenset(
    {
        "schema_version",
        "ticket",
        "authority_sha256",
        "command",
        "store_root",
        "active_path",
        "lock_held",
        "sqlite_immutable",
        "entry_count",
        "regular_file_bytes",
        "inventory_digest",
        "plan_identity",
        "plan_receipt_sha256",
        "plan_rows",
        "retained_true",
        "typed_gaps",
        "unfinished_run_id",
        "zero_acquisition_facts",
        "started_at",
        "ended_at",
    }
)


class RetirementError(RuntimeError):
    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = dict(context or {})


class SafeRetirementError(RetirementError):
    """Pre-rename failure; the active tree is left untouched."""


class IndeterminateRetirementError(RetirementError):
    """Post-rename failure; no cleanup, reverse rename, retry, or second transition."""

    def __init__(
        self,
        message: str,
        *,
        source_exists: bool,
        destination_exists: bool,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context=context)
        self.source_exists = source_exists
        self.destination_exists = destination_exists


@dataclass
class RetirementHooks:
    """Narrow injectable primitives. Production leaves every field unset."""

    stream_hash: Callable[[int], str] | None = None
    mkdir: Callable[[int, str, int], None] | None = None
    renameat2: Callable[[int, str, int, str], None] | None = None
    fsync: Callable[[int], None] | None = None
    syncfs: Callable[[int], None] | None = None
    clock: Callable[[], datetime] | None = None
    after_rename: Callable[[], None] | None = None
    before_post_proof: Callable[[], None] | None = None
    after_inventory: Callable[[], None] | None = None
    before_rename: Callable[[], None] | None = None
    on_sqlite: Callable[[str, sqlite3.Connection], None] | None = None


@dataclass
class _Runtime:
    hooks: RetirementHooks = field(default_factory=RetirementHooks)

    def now(self) -> datetime:
        if self.hooks.clock is not None:
            return self.hooks.clock()
        return datetime.now(UTC)

    def stream_hash(self, fd: int) -> str:
        if self.hooks.stream_hash is not None:
            return self.hooks.stream_hash(fd)
        return hash_fd(fd)

    def mkdir(self, dir_fd: int, name: str, mode: int) -> None:
        if self.hooks.mkdir is not None:
            self.hooks.mkdir(dir_fd, name, mode)
            return
        os.mkdir(name, mode, dir_fd=dir_fd)

    def renameat2(self, old_dir: int, old_name: str, new_dir: int, new_name: str) -> None:
        if self.hooks.renameat2 is not None:
            self.hooks.renameat2(old_dir, old_name, new_dir, new_name)
            return
        renameat2_noreplace(old_dir, old_name, new_dir, new_name)

    def fsync(self, fd: int) -> None:
        if self.hooks.fsync is not None:
            self.hooks.fsync(fd)
            return
        os.fsync(fd)

    def syncfs(self, fd: int) -> None:
        if self.hooks.syncfs is not None:
            self.hooks.syncfs(fd)
            return
        syncfs(fd)


class _Descriptors:
    def __init__(self) -> None:
        self._fds: list[int] = []

    def add(self, fd: int) -> int:
        self._fds.append(fd)
        return fd

    def close_all(self) -> list[BaseException]:
        errors: list[BaseException] = []
        while self._fds:
            fd = self._fds.pop()
            try:
                os.close(fd)
            except BaseException as exc:  # noqa: BLE001 - nested cleanup
                errors.append(exc)
        return errors


def canonical_json(payload: Any) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def hash_fd(fd: int) -> str:
    digest = hashlib.sha256()
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, CHUNK_SIZE)
        if not chunk:
            break
        digest.update(chunk)
    os.lseek(fd, 0, os.SEEK_SET)
    return digest.hexdigest()


def _hex_digest(value: Any, *, label: str) -> str:
    if type(value) is not str or HEX64.fullmatch(value) is None:
        raise SafeRetirementError(f"{label} is not sha256")
    return value


def _exact_int(value: Any, *, label: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise SafeRetirementError(f"{label} is not an exact integer")
    if minimum is not None and value < minimum:
        raise SafeRetirementError(f"{label} is below its bound")
    return value


def _exact_str(value: Any, *, label: str) -> str:
    if type(value) is not str or value == "":
        raise SafeRetirementError(f"{label} is not a non-empty string")
    return value


def _exact_null_or_str(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise SafeRetirementError(f"{label} is not a string or null")
    return value


def _exact_object(value: Any, *, label: str, keys: frozenset[str]) -> dict[str, Any]:
    if type(value) is not dict:
        raise SafeRetirementError(f"{label} is not an exact object")
    observed = frozenset(value)
    extra = sorted(observed - keys)
    missing = sorted(keys - observed)
    if extra or missing:
        raise SafeRetirementError(
            f"{label} has extra or missing fields",
            context={"extra": extra, "missing": missing},
        )
    return value


def _exact_str_map(value: Any, *, label: str, keys: frozenset[str] | None = None) -> dict[str, int]:
    if type(value) is not dict:
        raise SafeRetirementError(f"{label} is not an exact object")
    if keys is not None:
        _exact_object(value, label=label, keys=keys)
    out: dict[str, int] = {}
    for key, item in value.items():
        if type(key) is not str or key == "":
            raise SafeRetirementError(f"{label} has a non-string key")
        out[key] = _exact_int(item, label=f"{label}.{key}", minimum=0)
    return out


def _require(condition: bool, message: str, context: Mapping[str, Any] | None = None) -> None:
    if not condition:
        raise SafeRetirementError(message, context=dict(context or {}))


def _unsafe_part(part: str) -> bool:
    return part in {"", ".", ".."} or os.sep in part or part == ".."


def open_directory_nofollow(path: Path) -> int:
    absolute = Path(path).absolute()
    parts = absolute.parts
    if not parts or parts[0] != os.sep:
        raise SafeRetirementError(
            "path is not an absolute directory", context={"path": str(path)}
        )
    current = os.open(os.sep, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[1:]:
            if _unsafe_part(part):
                raise SafeRetirementError("unsafe path component", context={"part": part})
            try:
                nxt = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=current,
                )
            except OSError as exc:
                raise SafeRetirementError(
                    "a path component is a symlink or is not a directory",
                    context={"part": part, "path": str(path)},
                ) from exc
            os.close(current)
            current = nxt
        return current
    except Exception:
        os.close(current)
        raise


def open_child_dir(parent_fd: int, name: str) -> int:
    if _unsafe_part(name):
        raise SafeRetirementError("unsafe path component", context={"part": name})
    try:
        return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
    except OSError as exc:
        raise SafeRetirementError(
            "a directory cannot be opened no-follow", context={"name": name}
        ) from exc


def open_child_file(parent_fd: int, name: str, *, flags: int = os.O_RDONLY) -> int:
    if _unsafe_part(name):
        raise SafeRetirementError("unsafe path component", context={"part": name})
    try:
        fd = os.open(name, flags | os.O_NOFOLLOW, dir_fd=parent_fd)
    except OSError as exc:
        raise SafeRetirementError(
            "a file cannot be opened no-follow", context={"name": name}
        ) from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise SafeRetirementError("a leaf is not a regular file", context={"name": name})
    except Exception:
        os.close(fd)
        raise
    return fd


def _open_relative_regular_file(root_fd: int, relative: str) -> int:
    parts = [part for part in Path(relative).parts if part not in {".", ""}]
    if not parts:
        raise SafeRetirementError(
            "unsafe path component", context={"part": relative}
        )
    current = os.dup(root_fd)
    try:
        for index, part in enumerate(parts):
            last = index == len(parts) - 1
            nxt = (
                open_child_file(current, part)
                if last
                else open_child_dir(current, part)
            )
            os.close(current)
            current = nxt
        return current
    except Exception:
        os.close(current)
        raise


def _lookup_entry(
    entries: Sequence[Mapping[str, Any]], path: str
) -> dict[str, Any]:
    for item in entries:
        if str(item.get("path")) == path:
            return dict(item)
    raise SafeRetirementError(
        "an inventory entry is missing", context={"path": path}
    )


def _require_entry_identity(
    st: os.stat_result, expected: Mapping[str, Any], *, path: str
) -> None:
    if stat.S_ISDIR(st.st_mode):
        kind = "directory"
    elif stat.S_ISREG(st.st_mode):
        kind = "regular_file"
    else:
        kind = "special"
    observed = {
        "type": kind,
        "device": int(st.st_dev),
        "inode": int(st.st_ino),
        "mode": int(stat.S_IMODE(st.st_mode)),
        "size": int(st.st_size),
    }
    for key, actual in observed.items():
        if actual != expected.get(key):
            raise SafeRetirementError(
                "a proved name no longer matches its inventory identity",
                context={
                    "path": path,
                    "field": key,
                    "expected": expected.get(key),
                    "actual": actual,
                },
            )


def prove_held_name(
    parent_fd: int,
    name: str,
    held_fd: int,
    *,
    directory: bool,
    expected: Mapping[str, Any] | None = None,
) -> None:
    """Reopen ``name`` no-follow and require it is still the held descriptor."""

    opened = (
        open_child_dir(parent_fd, name)
        if directory
        else _open_relative_regular_file(parent_fd, name)
    )
    try:
        opened_st = os.fstat(opened)
        held_st = os.fstat(held_fd)
        _require(
            int(opened_st.st_dev) == int(held_st.st_dev)
            and int(opened_st.st_ino) == int(held_st.st_ino),
            "a proved name no longer names its held descriptor",
            {"name": name},
        )
        if expected is not None:
            path = str(expected.get("path") or name)
            _require_entry_identity(held_st, expected, path=path)
    finally:
        os.close(opened)


def _walk_relative(root_fd: int, relative: str, *, flags: int, directory: bool) -> int:
    parts = [part for part in Path(relative).parts if part not in {".", ""}]
    current = os.dup(root_fd)
    try:
        for index, part in enumerate(parts):
            if _unsafe_part(part):
                raise SafeRetirementError("unsafe path component", context={"part": part})
            last = index == len(parts) - 1
            if last and not directory:
                nxt = os.open(part, flags | os.O_NOFOLLOW, dir_fd=current)
            else:
                nxt = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=current,
                )
            os.close(current)
            current = nxt
        return current
    except Exception:
        os.close(current)
        raise


def renameat2_noreplace(old_dir: int, old_name: str, new_dir: int, new_name: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        renameat2 = libc.renameat2
    except AttributeError as exc:
        raise SafeRetirementError("renameat2 is unavailable") from exc
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        old_dir,
        os.fsencode(old_name),
        new_dir,
        os.fsencode(new_name),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), new_name)


def syncfs(fd: int) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        func = libc.syncfs
    except AttributeError as exc:
        raise SafeRetirementError("syncfs is unavailable") from exc
    func.argtypes = [ctypes.c_int]
    func.restype = ctypes.c_int
    if func(fd) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _dir_names(dir_fd: int) -> list[str]:
    return sorted(
        name
        for name in os.listdir(f"/proc/self/fd/{dir_fd}")
        if name not in {".", ".."}
    )


def _entry_from_stat(
    relative: str, st: os.stat_result, *, digest: str | None
) -> dict[str, Any]:
    if stat.S_ISLNK(st.st_mode):
        raise SafeRetirementError("a tree entry is a symlink", context={"path": relative})
    if stat.S_ISREG(st.st_mode):
        kind = "regular_file"
    elif stat.S_ISDIR(st.st_mode):
        kind = "directory"
    else:
        raise SafeRetirementError("a tree entry is a special file", context={"path": relative})
    return {
        "device": int(st.st_dev),
        "inode": int(st.st_ino),
        "mode": int(stat.S_IMODE(st.st_mode)),
        "path": relative,
        "sha256": digest,
        "size": int(st.st_size),
        "type": kind,
    }


def _stable_meta(st: os.stat_result) -> tuple[int, int, int, int, int]:
    return (int(st.st_dev), int(st.st_ino), int(st.st_mode), int(st.st_size), int(st.st_mtime_ns))


def collect_inventory(
    root_fd: int, *, runtime: _Runtime, expected_device: int
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    root_stat = os.fstat(root_fd)
    _require(
        stat.S_ISDIR(root_stat.st_mode),
        "the active tree root is not a directory",
    )
    _require(
        int(root_stat.st_dev) == expected_device,
        "tree device changed",
        {"expected": expected_device, "actual": int(root_stat.st_dev)},
    )
    entries.append(_entry_from_stat(".", root_stat, digest=None))

    def _walk(dir_fd: int, prefix: str) -> None:
        for name in _dir_names(dir_fd):
            if _unsafe_part(name):
                raise SafeRetirementError("unsafe tree name", context={"name": name})
            relative = name if prefix == "." else f"{prefix}/{name}"
            st = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
            if stat.S_ISLNK(st.st_mode):
                raise SafeRetirementError(
                    "a tree entry is a symlink", context={"path": relative}
                )
            if stat.S_ISREG(st.st_mode):
                fd = open_child_file(dir_fd, name)
                try:
                    before = os.fstat(fd)
                    _require(
                        _stable_meta(before) == _stable_meta(st),
                        "a regular file was replaced",
                        {"path": relative},
                    )
                    digest = runtime.stream_hash(fd)
                    after = os.fstat(fd)
                    _require(
                        _stable_meta(after) == _stable_meta(before),
                        "a regular file changed during hashing",
                        {"path": relative},
                    )
                    _require(
                        int(after.st_dev) == expected_device,
                        "tree device changed",
                        {"path": relative},
                    )
                    entries.append(_entry_from_stat(relative, after, digest=digest))
                finally:
                    os.close(fd)
            elif stat.S_ISDIR(st.st_mode):
                child = open_child_dir(dir_fd, name)
                try:
                    child_stat = os.fstat(child)
                    _require(
                        _stable_meta(child_stat)[:4] == (
                            int(st.st_dev),
                            int(st.st_ino),
                            int(st.st_mode),
                            int(st.st_size),
                        ),
                        "a directory was replaced",
                        {"path": relative},
                    )
                    _require(
                        int(child_stat.st_dev) == expected_device,
                        "tree device changed",
                        {"path": relative},
                    )
                    entries.append(_entry_from_stat(relative, child_stat, digest=None))
                    _walk(child, relative)
                finally:
                    os.close(child)
            else:
                raise SafeRetirementError(
                    "a tree entry is a special file", context={"path": relative}
                )

    _walk(root_fd, ".")
    entries.sort(key=lambda item: str(item["path"]))
    return entries


def inventory_digest(entries: Sequence[Mapping[str, Any]]) -> str:
    return sha256_bytes(canonical_json({"entries": [dict(item) for item in entries]}))


def _authenticate_authority_document(document: Mapping[str, Any]) -> dict[str, Any]:
    body = _exact_object(document, label="authority", keys=AUTHORITY_KEYS)
    _require(
        body.get("schema_version") == AUTHORITY_SCHEMA,
        "retirement authority schema version changed",
        {"actual": body.get("schema_version")},
    )
    _require(body.get("ticket") == TICKET_ID, "retirement authority ticket changed")
    _exact_str(body.get("adr"), label="adr")
    _exact_str(body.get("observed_at"), label="observed_at")
    database = _exact_object(body.get("database"), label="database", keys=DATABASE_KEYS)
    db_auth = _exact_object(
        database.get("authority"), label="database.authority", keys=DB_AUTHORITY_KEYS
    )
    _hex_digest(db_auth.get("acquisition_cli_sha256"), label="database authority cli")
    _hex_digest(db_auth.get("acquisition_source_sha256"), label="database authority source")
    _exact_str(db_auth.get("created_at"), label="created_at")
    _exact_str(db_auth.get("destination"), label="database destination")
    _exact_str(db_auth.get("device"), label="database device")
    _hex_digest(db_auth.get("plan_identity"), label="plan identity")
    _hex_digest(db_auth.get("plan_receipt_sha256"), label="plan receipt sha256")
    _exact_str(db_auth.get("policy_identity"), label="policy identity")
    _exact_int(database.get("application_id"), label="application_id", minimum=0)
    _exact_int(database.get("user_version"), label="user_version", minimum=0)
    _exact_int(
        database.get("coinalyze_ledger_charged"),
        label="coinalyze_ledger_charged",
        minimum=0,
    )
    _exact_int(
        database.get("foreign_key_violation_count"),
        label="foreign_key_violation_count",
        minimum=0,
    )
    _exact_str(database.get("integrity_check"), label="integrity_check")
    _exact_str_map(
        database.get("table_counts"), label="table_counts", keys=TABLE_COUNT_KEYS
    )
    _exact_str_map(database.get("plan_entry_counts"), label="plan_entry_counts")
    _exact_str_map(
        database.get("plan_entry_retained_counts"),
        label="plan_entry_retained_counts",
        keys=RETAINED_COUNT_KEYS,
    )
    _exact_str_map(database.get("terminal_gap_counts"), label="terminal_gap_counts")
    run = _exact_object(database.get("run"), label="run", keys=RUN_KEYS)
    _hex_digest(run.get("run_id"), label="run_id")
    _exact_str(run.get("started_at"), label="run started_at")
    _exact_null_or_str(run.get("ended_at"), label="run ended_at")
    _exact_null_or_str(run.get("stop_reason"), label="run stop_reason")
    for field_name in (
        "attempt_delta",
        "attempt_hi",
        "byte_delta",
        "capacity_blocked",
        "completion_delta",
        "error_count",
        "gap_delta",
        "network_calls",
        "open_coinalyze_charges",
        "seq",
    ):
        _exact_int(run.get(field_name), label=f"run.{field_name}", minimum=0)
    seal = _exact_object(database.get("seal_head"), label="seal_head", keys=SEAL_HEAD_KEYS)
    _hex_digest(seal.get("plan_receipt_sha256"), label="seal plan receipt")
    _hex_digest(seal.get("prefix_digest"), label="seal prefix digest")
    _exact_null_or_str(seal.get("predecessor_sha256"), label="seal predecessor")
    for field_name in (
        "attempt_hi",
        "charge_hi",
        "completion_hi",
        "run_hi",
        "seal_hi",
        "sidecar_hi",
        "transition_hi",
    ):
        _exact_int(seal.get(field_name), label=f"seal_head.{field_name}", minimum=0)
    filesystem = _exact_object(
        body.get("filesystem"), label="filesystem", keys=FILESYSTEM_KEYS
    )
    _require(
        filesystem.get("store_root") == FIXED_STORE_ROOT,
        "store root path changed",
        {"actual": filesystem.get("store_root")},
    )
    _require(
        filesystem.get("active_name") == FIXED_ACTIVE_NAME,
        "active name changed",
        {"actual": filesystem.get("active_name")},
    )
    _require(
        filesystem.get("retirement_parent") == FIXED_RETIREMENT_PARENT,
        "retirement parent changed",
        {"actual": filesystem.get("retirement_parent")},
    )
    dest = _hex_digest(filesystem.get("destination_name"), label="destination_name")
    device = _exact_int(filesystem.get("device"), label="filesystem.device", minimum=0)
    _require(
        db_auth["device"] == f"dev:{device}",
        "database device disagrees with filesystem device",
        {"database": db_auth["device"], "filesystem": device},
    )
    _require(
        db_auth["destination"] == FIXED_STORE_ROOT,
        "database destination changed",
    )
    entries = filesystem.get("entries")
    if type(entries) is not list:
        raise SafeRetirementError("filesystem entries are not a list")
    parsed: list[dict[str, Any]] = []
    paths: set[str] = set()
    file_bytes = 0
    for item in entries:
        entry = _exact_object(item, label="inventory entry", keys=ENTRY_KEYS)
        path = _exact_str(entry.get("path"), label="entry.path")
        _require(path not in paths, "inventory path is duplicated", {"path": path})
        paths.add(path)
        kind = _exact_str(entry.get("type"), label="entry.type")
        _require(
            kind in {"directory", "regular_file"},
            "inventory entry type is unknown",
            {"type": kind, "path": path},
        )
        _exact_int(entry.get("device"), label="entry.device", minimum=0)
        _exact_int(entry.get("inode"), label="entry.inode", minimum=0)
        _exact_int(entry.get("mode"), label="entry.mode", minimum=0)
        size = _exact_int(entry.get("size"), label="entry.size", minimum=0)
        _require(
            int(entry["device"]) == device,
            "inventory entry device changed",
            {"path": path},
        )
        if kind == "directory":
            _require(entry.get("sha256") is None, "a directory carries a digest", {"path": path})
        else:
            _hex_digest(entry.get("sha256"), label=f"entry.sha256:{path}")
            file_bytes += size
        parsed.append(entry)
    _require(
        _exact_int(filesystem.get("entry_count"), label="entry_count") == len(parsed),
        "entry count changed",
        {"expected": len(parsed), "actual": filesystem.get("entry_count")},
    )
    _require(
        _exact_int(filesystem.get("regular_file_bytes"), label="regular_file_bytes")
        == file_bytes,
        "regular file byte total changed",
        {"expected": file_bytes, "actual": filesystem.get("regular_file_bytes")},
    )
    receipt = _exact_object(
        body.get("plan_receipt"), label="plan_receipt", keys=PLAN_RECEIPT_AUTH_KEYS
    )
    _hex_digest(receipt.get("sha256"), label="plan_receipt.sha256")
    _require(
        receipt["sha256"] == dest,
        "destination name disagrees with the plan receipt digest",
    )
    _require(
        receipt["sha256"] == db_auth["plan_receipt_sha256"],
        "plan receipt digest disagrees with database authority",
    )
    _require(
        receipt["plan_identity"] == db_auth["plan_identity"],
        "plan identity disagrees across authority blocks",
    )
    for field_name in (
        "coinalyze_logical_receipts",
        "declared_retained_credit_objects",
        "plan_objects",
        "typed_gaps",
    ):
        _exact_int(receipt.get(field_name), label=f"plan_receipt.{field_name}", minimum=0)
    _exact_str(receipt.get("schema_version"), label="plan_receipt.schema_version")
    _exact_str(receipt.get("policy_identity"), label="plan_receipt.policy_identity")
    context = _exact_object(
        body.get("execution_context"),
        label="execution_context",
        keys=EXECUTION_CONTEXT_KEYS,
    )
    _hex_digest(context.get("accepted_acquisition_cli_sha256"), label="context cli")
    _hex_digest(context.get("accepted_acquisition_source_sha256"), label="context source")
    _hex_digest(context.get("accepted_acquisition_test_sha256"), label="context test")
    _exact_str(context.get("integration_commit"), label="integration_commit")
    return body


def load_authority_bytes(payload: bytes, *, expected_digest: str) -> dict[str, Any]:
    actual = sha256_bytes(payload)
    _require(
        actual == expected_digest,
        "retirement authority hash changed",
        {"expected": expected_digest, "actual": actual},
    )
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SafeRetirementError("retirement authority is not JSON") from exc
    if type(document) is not dict:
        raise SafeRetirementError("retirement authority is not an object")
    return _authenticate_authority_document(document)


def _read_regular_file(dir_fd: int, relative: str) -> bytes:
    fd = _walk_relative(dir_fd, relative, flags=os.O_RDONLY, directory=False)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise SafeRetirementError("authority path is not a regular file")
        chunks: list[bytes] = []
        os.lseek(fd, 0, os.SEEK_SET)
        while True:
            chunk = os.read(fd, CHUNK_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def load_authority_from_repository(
    repository: Path,
    *,
    authority_path: Path | None = None,
    authority_digest: str | None = None,
) -> tuple[dict[str, Any], str, int]:
    repo_fd = open_directory_nofollow(repository)
    try:
        if authority_path is None and authority_digest is None:
            relative = str(AUTHORITY_RELATIVE)
            digest = AUTHORITY_SHA256
        elif authority_path is not None and authority_digest is not None:
            try:
                relative = str(authority_path.resolve().relative_to(repository.resolve()))
            except ValueError as exc:
                raise SafeRetirementError(
                    "authority path is outside the repository",
                    context={"path": str(authority_path)},
                ) from exc
            digest = authority_digest
        else:
            raise SafeRetirementError("authority path and digest must be supplied together")
        payload = _read_regular_file(repo_fd, relative)
        document = load_authority_bytes(payload, expected_digest=digest)
        return document, digest, repo_fd
    except Exception:
        os.close(repo_fd)
        raise


def _hash_relative_file(repo_fd: int, relative: Path) -> str:
    fd = _walk_relative(repo_fd, str(relative), flags=os.O_RDONLY, directory=False)
    try:
        return hash_fd(fd)
    finally:
        os.close(fd)


def prove_execution_context(repo_fd: int, authority: Mapping[str, Any]) -> None:
    context = authority["execution_context"]
    actual_source = _hash_relative_file(repo_fd, ACQUISITION_SOURCE_RELATIVE)
    actual_test = _hash_relative_file(repo_fd, ACQUISITION_TEST_RELATIVE)
    actual_cli = _hash_relative_file(repo_fd, ACQUISITION_CLI_RELATIVE)
    _require(
        actual_source == context["accepted_acquisition_source_sha256"],
        "execution-context source hash changed",
        {"expected": context["accepted_acquisition_source_sha256"], "actual": actual_source},
    )
    _require(
        actual_test == context["accepted_acquisition_test_sha256"],
        "execution-context test hash changed",
        {"expected": context["accepted_acquisition_test_sha256"], "actual": actual_test},
    )
    _require(
        actual_cli == context["accepted_acquisition_cli_sha256"],
        "execution-context CLI hash changed",
        {"expected": context["accepted_acquisition_cli_sha256"], "actual": actual_cli},
    )
    if authority_digest_is_production(authority):
        _require(
            actual_source == ACCEPTED_ACQUISITION_SOURCE_SHA256
            and actual_test == ACCEPTED_ACQUISITION_TEST_SHA256
            and actual_cli == ACCEPTED_ACQUISITION_CLI_SHA256
            and context["integration_commit"] == INTEGRATION_COMMIT,
            "production execution context changed",
        )


def authority_digest_is_production(authority: Mapping[str, Any]) -> bool:
    context = authority.get("execution_context") or {}
    return (
        context.get("accepted_acquisition_source_sha256")
        == ACCEPTED_ACQUISITION_SOURCE_SHA256
        and context.get("integration_commit") == INTEGRATION_COMMIT
    )


def _compare_inventory(
    actual: Sequence[Mapping[str, Any]], expected: Sequence[Mapping[str, Any]]
) -> None:
    actual = sorted((dict(item) for item in actual), key=lambda item: str(item["path"]))
    expected = sorted((dict(item) for item in expected), key=lambda item: str(item["path"]))
    actual_paths = [str(item["path"]) for item in actual]
    expected_paths = [str(item["path"]) for item in expected]
    missing = sorted(set(expected_paths) - set(actual_paths))
    extra = sorted(set(actual_paths) - set(expected_paths))
    if missing:
        raise SafeRetirementError(
            "an inventory entry is missing",
            context={"missing": missing[:8], "missing_count": len(missing)},
        )
    if extra:
        raise SafeRetirementError(
            "an extra inventory entry is present",
            context={"extra": extra[:8], "extra_count": len(extra)},
        )
    for observed, wanted in zip(actual, expected, strict=True):
        path = wanted["path"]
        for key in ("type", "device", "inode", "mode", "size", "sha256"):
            if observed.get(key) != wanted.get(key):
                raise SafeRetirementError(
                    "inventory entry changed",
                    context={
                        "path": path,
                        "field": key,
                        "expected": wanted.get(key),
                        "actual": observed.get(key),
                    },
                )


def _plan_receipt_path(authority: Mapping[str, Any]) -> str:
    digest = str(authority["plan_receipt"]["sha256"])
    return f"plan_receipts/{digest}.json"


def prove_plan_receipt(fd: int, authority: Mapping[str, Any], runtime: _Runtime) -> None:
    before = os.fstat(fd)
    digest = runtime.stream_hash(fd)
    after = os.fstat(fd)
    _require(
        _stable_meta(before) == _stable_meta(after),
        "plan receipt changed during hashing",
    )
    expected = str(authority["plan_receipt"]["sha256"])
    _require(digest == expected, "plan receipt hash changed", {"actual": digest})
    os.lseek(fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, CHUNK_SIZE)
        if not chunk:
            break
        chunks.append(chunk)
    payload = b"".join(chunks)
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SafeRetirementError("plan receipt is not JSON") from exc
    if type(document) is not dict:
        raise SafeRetirementError("plan receipt is not an object")
    wanted = authority["plan_receipt"]
    _require(
        document.get("schema_version") == wanted["schema_version"],
        "plan receipt schema version changed",
    )
    _require(
        document.get("policy_identity") == wanted["policy_identity"],
        "plan receipt policy identity changed",
    )
    _require(
        document.get("plan_identity") == wanted["plan_identity"],
        "plan receipt plan identity changed",
    )
    counts = document.get("counts")
    if type(counts) is not dict:
        raise SafeRetirementError("plan receipt counts are missing")
    _require(
        counts.get("plan_objects") == wanted["plan_objects"],
        "plan receipt plan object count changed",
    )
    _require(
        counts.get("coinalyze_logical_receipts") == wanted["coinalyze_logical_receipts"],
        "plan receipt Coinalyze logical receipt count changed",
    )
    _require(
        counts.get("retained_credit_objects") == wanted["declared_retained_credit_objects"],
        "plan receipt retained object declaration changed",
    )
    _require(
        counts.get("coinalyze_unsupported") == wanted["typed_gaps"],
        "plan receipt typed gap count changed",
    )


def _open_sqlite_immutable(
    file_fd: int, runtime: _Runtime
) -> sqlite3.Connection:
    uri = f"file:/proc/self/fd/{file_fd}?mode=ro&immutable=1"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise SafeRetirementError(
            "SQLite state cannot be opened immutable"
        ) from exc
    try:
        conn.execute("PRAGMA query_only=ON")
        flag = conn.execute("PRAGMA query_only").fetchone()
        if flag is None or int(flag[0]) != 1:
            raise SafeRetirementError("SQLite query_only is not enabled")
        try:
            conn.execute("CREATE TABLE retirement_write_probe(x INTEGER)")
        except sqlite3.Error as exc:
            message = str(exc).lower()
            if not (
                "readonly" in message
                or "read-only" in message
                or "query_only" in message
            ):
                raise SafeRetirementError(
                    "SQLite write probe failed unexpectedly"
                ) from exc
        else:
            raise SafeRetirementError("SQLite opened writable")
        if runtime.hooks.on_sqlite is not None:
            runtime.hooks.on_sqlite(uri, conn)
    except Exception:
        conn.close()
        raise
    return conn


def prove_sqlite(
    file_fd: int, authority: Mapping[str, Any], runtime: _Runtime
) -> None:
    database = authority["database"]
    conn: sqlite3.Connection | None = None
    try:
        conn = _open_sqlite_immutable(file_fd, runtime)
        _prove_sqlite_connection(conn, database)
    except SafeRetirementError:
        raise
    except sqlite3.Error as exc:
        raise SafeRetirementError(
            "SQLite state is not safely readable"
        ) from exc
    except (TypeError, ValueError, IndexError, KeyError) as exc:
        raise SafeRetirementError("SQLite row shape is invalid") from exc
    finally:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error as exc:
                raise SafeRetirementError("SQLite close failed") from exc


def _prove_sqlite_connection(
    conn: sqlite3.Connection, database: Mapping[str, Any]
) -> None:
    app = conn.execute("PRAGMA application_id").fetchone()
    user = conn.execute("PRAGMA user_version").fetchone()
    integrity = conn.execute("PRAGMA integrity_check").fetchone()
    fk_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
    _require(
        int(app[0]) == database["application_id"],
        "SQLite application_id changed",
        {"expected": database["application_id"], "actual": int(app[0])},
    )
    _require(
        int(user[0]) == database["user_version"],
        "SQLite user_version changed",
        {"expected": database["user_version"], "actual": int(user[0])},
    )
    _require(
        str(integrity[0]) == database["integrity_check"],
        "SQLite integrity_check changed",
        {"actual": str(integrity[0])},
    )
    _require(
        len(fk_rows) == database["foreign_key_violation_count"],
        "SQLite foreign key violations changed",
        {"actual": len(fk_rows)},
    )
    names = {
        str(row[0])
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    }
    expected_tables = set(database["table_counts"])
    extra = sorted(names - expected_tables)
    missing = sorted(expected_tables - names)
    if extra or missing:
        raise SafeRetirementError(
            "SQLite table set changed",
            context={"extra": extra, "missing": missing},
        )
    for table, expected in database["table_counts"].items():
        if table not in TABLE_COUNT_KEYS:
            raise SafeRetirementError(
                "unknown SQLite table in authority",
                context={"table": table},
            )
        actual = int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        _require(
            actual == expected,
            "SQLite table count changed",
            {"table": table, "expected": expected, "actual": actual},
        )
    row = conn.execute(
        "SELECT plan_identity, plan_receipt_sha256, code_json, destination, device, "
        "created_at FROM authority WHERE id=1"
    ).fetchone()
    if row is None:
        raise SafeRetirementError("SQLite authority row is missing")
    db_auth = database["authority"]
    _require(str(row[0]) == db_auth["plan_identity"], "SQLite plan identity changed")
    _require(
        str(row[1]) == db_auth["plan_receipt_sha256"],
        "SQLite plan receipt identity changed",
    )
    try:
        code = json.loads(str(row[2]))
    except json.JSONDecodeError as exc:
        raise SafeRetirementError("SQLite code_json is not JSON") from exc
    if type(code) is not dict:
        raise SafeRetirementError("SQLite code_json is not an object")
    _require(
        code.get("policy_identity") == db_auth["policy_identity"],
        "SQLite policy identity changed",
    )
    _require(
        code.get("acquisition_cli_sha256") == db_auth["acquisition_cli_sha256"],
        "SQLite acquisition CLI identity changed",
    )
    _require(
        code.get("acquisition_source_sha256") == db_auth["acquisition_source_sha256"],
        "SQLite acquisition source identity changed",
    )
    _require(str(row[3]) == db_auth["destination"], "SQLite destination changed")
    _require(str(row[4]) == db_auth["device"], "SQLite device changed")
    _require(str(row[5]) == db_auth["created_at"], "SQLite created_at changed")
    plan_counts: dict[str, int] = {}
    for provider, kind, count in conn.execute(
        "SELECT provider, kind, COUNT(*) FROM plan_entry GROUP BY provider, kind"
    ):
        plan_counts[f"{provider}/{kind}"] = int(count)
    _require(
        plan_counts == dict(database["plan_entry_counts"]),
        "SQLite plan entry distribution changed",
        {"expected": database["plan_entry_counts"], "actual": plan_counts},
    )
    retained_counts = {"true": 0, "false": 0, "not_applicable": 0}
    for flag, count in conn.execute(
        "SELECT CASE json_extract(payload_json, '$.payload.retained') "
        "WHEN 1 THEN 'true' WHEN 0 THEN 'false' ELSE 'not_applicable' END, "
        "COUNT(*) FROM plan_entry GROUP BY 1"
    ):
        retained_counts[str(flag)] = int(count)
    _require(
        retained_counts == dict(database["plan_entry_retained_counts"]),
        "SQLite retained label counts changed",
        {"expected": database["plan_entry_retained_counts"], "actual": retained_counts},
    )
    gap_counts: dict[str, int] = {}
    for kind, count in conn.execute(
        "SELECT kind, COUNT(*) FROM terminal_gap GROUP BY kind"
    ):
        gap_counts[str(kind)] = int(count)
    _require(
        gap_counts == dict(database["terminal_gap_counts"]),
        "SQLite terminal gap counts changed",
        {"expected": database["terminal_gap_counts"], "actual": gap_counts},
    )
    run = conn.execute(
        "SELECT seq, run_id, started_at, ended_at, stop_reason, attempt_hi, "
        "network_calls, error_count, capacity_blocked, attempt_delta, "
        "completion_delta, gap_delta, byte_delta, open_coinalyze_charges "
        "FROM run_metadata"
    ).fetchall()
    _require(len(run) == 1, "SQLite unfinished run count changed", {"actual": len(run)})
    expected_run = database["run"]
    observed_run = run[0]
    _require(int(observed_run[0]) == expected_run["seq"], "run seq changed")
    _require(str(observed_run[1]) == expected_run["run_id"], "run id changed")
    _require(str(observed_run[2]) == expected_run["started_at"], "run started_at changed")
    _require(observed_run[3] == expected_run["ended_at"], "run ended_at changed")
    _require(observed_run[4] == expected_run["stop_reason"], "run stop_reason changed")
    mapping = {
        5: "attempt_hi",
        6: "network_calls",
        7: "error_count",
        8: "capacity_blocked",
        9: "attempt_delta",
        10: "completion_delta",
        11: "gap_delta",
        12: "byte_delta",
        13: "open_coinalyze_charges",
    }
    for index, key in mapping.items():
        _require(
            int(observed_run[index]) == expected_run[key],
            f"run {key} changed",
            {"expected": expected_run[key], "actual": int(observed_run[index])},
        )
    _require(observed_run[3] is None, "the unfinished run has an end time")
    _require(observed_run[4] is None, "the unfinished run has a stop reason")
    ledger = conn.execute("SELECT charged FROM coinalyze_ledger WHERE id=1").fetchone()
    if ledger is None:
        raise SafeRetirementError("SQLite Coinalyze ledger is missing")
    _require(
        int(ledger[0]) == database["coinalyze_ledger_charged"],
        "SQLite Coinalyze ledger changed",
    )
    seal = conn.execute(
        "SELECT receipt_sha256, prefix_digest, attempt_hi, completion_hi, sidecar_hi, "
        "charge_hi, transition_hi, run_hi, seal_hi, predecessor_sha256 "
        "FROM seal_head WHERE id=1"
    ).fetchone()
    if seal is None:
        raise SafeRetirementError("SQLite seal head is missing")
    expected_seal = database["seal_head"]
    _require(
        str(seal[0]) == expected_seal["plan_receipt_sha256"],
        "seal head receipt changed",
    )
    _require(str(seal[1]) == expected_seal["prefix_digest"], "seal head prefix changed")
    for index, key in enumerate(
        (
            "attempt_hi",
            "completion_hi",
            "sidecar_hi",
            "charge_hi",
            "transition_hi",
            "run_hi",
            "seal_hi",
        ),
        start=2,
    ):
        _require(
            int(seal[index]) == expected_seal[key],
            f"seal head {key} changed",
        )
    _require(
        seal[9] == expected_seal["predecessor_sha256"],
        "seal head predecessor changed",
    )
    zero_tables = (
        "attempt",
        "completion",
        "sidecar_fact",
        "coinalyze_charge",
        "charge_transition",
        "run_publication",
        "run_seal",
    )
    for table in zero_tables:
        _require(
            database["table_counts"][table] == 0,
            "zero-fact table is not zero in authority",
            {"table": table},
        )


def _acquire_lock(tree_fd: int, descriptors: _Descriptors) -> int:
    try:
        st = os.stat(LOCK_NAME, dir_fd=tree_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise SafeRetirementError("acquisition lock is missing") from exc
    except OSError as exc:
        raise SafeRetirementError(
            "acquisition lock cannot be inspected safely"
        ) from exc
    if stat.S_ISLNK(st.st_mode):
        raise SafeRetirementError("acquisition lock is a symlink")
    if not stat.S_ISREG(st.st_mode):
        raise SafeRetirementError("acquisition lock is a special file")
    try:
        lock_fd = os.open(
            LOCK_NAME,
            os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=tree_fd,
        )
    except FileNotFoundError as exc:
        raise SafeRetirementError("acquisition lock is missing") from exc
    except OSError as exc:
        raise SafeRetirementError(
            "acquisition lock cannot be opened no-follow"
        ) from exc
    descriptors.add(lock_fd)
    if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
        raise SafeRetirementError("acquisition lock is a special file")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise SafeRetirementError("another writer holds the acquisition lock") from exc
    return lock_fd


def _name_exists(dir_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise SafeRetirementError(
            "a path cannot be inspected safely", context={"name": name}
        ) from exc
    return True


def _prove_tree(
    *,
    repository: Path,
    authority: Mapping[str, Any],
    authority_digest: str,
    runtime: _Runtime,
    descriptors: _Descriptors,
    repo_fd: int,
) -> dict[str, Any]:
    prove_execution_context(repo_fd, authority)
    store_rel = str(authority["filesystem"]["store_root"])
    store_fd = descriptors.add(
        _walk_relative(repo_fd, store_rel, flags=os.O_RDONLY, directory=True)
    )
    active = str(authority["filesystem"]["active_name"])
    if not _name_exists(store_fd, active):
        raise SafeRetirementError("the active Gate-2 tree is missing")
    tree_fd = descriptors.add(open_child_dir(store_fd, active))
    lock_fd = _acquire_lock(tree_fd, descriptors)
    device = int(authority["filesystem"]["device"])
    tree_stat = os.fstat(tree_fd)
    _require(int(tree_stat.st_dev) == device, "active tree device changed")
    receipt_rel = _plan_receipt_path(authority)
    receipt_fd = descriptors.add(_open_relative_regular_file(tree_fd, receipt_rel))
    sqlite_fd = descriptors.add(open_child_file(tree_fd, SQLITE_NAME))
    entries = collect_inventory(tree_fd, runtime=runtime, expected_device=device)
    _compare_inventory(entries, authority["filesystem"]["entries"])
    root_entry = _lookup_entry(entries, ".")
    lock_entry = _lookup_entry(entries, LOCK_NAME)
    sqlite_entry = _lookup_entry(entries, SQLITE_NAME)
    receipt_entry = _lookup_entry(entries, receipt_rel)
    if runtime.hooks.after_inventory is not None:
        runtime.hooks.after_inventory()
    prove_held_name(
        tree_fd,
        receipt_rel,
        receipt_fd,
        directory=False,
        expected=receipt_entry,
    )
    prove_held_name(
        tree_fd,
        SQLITE_NAME,
        sqlite_fd,
        directory=False,
        expected=sqlite_entry,
    )
    prove_plan_receipt(receipt_fd, authority, runtime)
    prove_sqlite(sqlite_fd, authority, runtime)
    parent = str(authority["filesystem"]["retirement_parent"])
    destination = str(authority["filesystem"]["destination_name"])
    return {
        "store_fd": store_fd,
        "tree_fd": tree_fd,
        "lock_fd": lock_fd,
        "entries": entries,
        "tree_stat": tree_stat,
        "root_entry": root_entry,
        "lock_entry": lock_entry,
        "parent": parent,
        "destination": destination,
        "device": device,
        "authority_digest": authority_digest,
    }


def _inspect_document(
    *,
    authority: Mapping[str, Any],
    authority_digest: str,
    repository: Path,
    started: datetime,
    ended: datetime,
) -> dict[str, Any]:
    database = authority["database"]
    document = {
        "schema_version": INSPECT_SCHEMA,
        "ticket": TICKET_ID,
        "authority_sha256": authority_digest,
        "command": "inspect",
        "store_root": str(repository / authority["filesystem"]["store_root"]),
        "active_path": str(
            repository
            / authority["filesystem"]["store_root"]
            / authority["filesystem"]["active_name"]
        ),
        "lock_held": True,
        "sqlite_immutable": True,
        "entry_count": authority["filesystem"]["entry_count"],
        "regular_file_bytes": authority["filesystem"]["regular_file_bytes"],
        "inventory_digest": inventory_digest(authority["filesystem"]["entries"]),
        "plan_identity": authority["plan_receipt"]["plan_identity"],
        "plan_receipt_sha256": authority["plan_receipt"]["sha256"],
        "plan_rows": database["table_counts"]["plan_entry"],
        "retained_true": database["plan_entry_retained_counts"]["true"],
        "typed_gaps": database["table_counts"]["terminal_gap"],
        "unfinished_run_id": database["run"]["run_id"],
        "zero_acquisition_facts": True,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
    }
    _exact_object(document, label="inspection", keys=INSPECT_KEYS)
    body = canonical_json(document)
    _require(
        len(body) <= MAX_OUTPUT_BYTES,
        "inspection output exceeds the bounded receipt ceiling",
        {"bytes": len(body)},
    )
    return document


def _receipt_document(
    *,
    authority: Mapping[str, Any],
    authority_digest: str,
    repository: Path,
    before: str,
    after: str,
    started: datetime,
    ended: datetime,
) -> dict[str, Any]:
    filesystem = authority["filesystem"]
    source = str(repository / filesystem["store_root"] / filesystem["active_name"])
    destination = str(
        repository
        / filesystem["store_root"]
        / filesystem["retirement_parent"]
        / filesystem["destination_name"]
    )
    document = {
        "schema_version": RECEIPT_SCHEMA,
        "ticket": TICKET_ID,
        "authority_sha256": authority_digest,
        "plan_identity": authority["plan_receipt"]["plan_identity"],
        "plan_receipt_sha256": authority["plan_receipt"]["sha256"],
        "source": source,
        "destination": destination,
        "before_inventory_digest": before,
        "after_inventory_digest": after,
        "entry_count": filesystem["entry_count"],
        "regular_file_bytes": filesystem["regular_file_bytes"],
        "lock_held": True,
        "rename_noreplace": True,
        "parent_fsync": True,
        "syncfs": True,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
    }
    _exact_object(document, label="retirement receipt", keys=RECEIPT_KEYS)
    body = canonical_json(document)
    _require(
        len(body) <= MAX_OUTPUT_BYTES,
        "retirement receipt exceeds the bounded receipt ceiling",
        {"bytes": len(body)},
    )
    return document


def inspect_gate2(
    *,
    repository: Path,
    authority_path: Path | None = None,
    authority_digest: str | None = None,
    hooks: RetirementHooks | None = None,
) -> dict[str, Any]:
    runtime = _Runtime(hooks or RetirementHooks())
    started = runtime.now()
    descriptors = _Descriptors()
    repo_fd: int | None = None
    try:
        authority, digest, repo_fd = load_authority_from_repository(
            repository,
            authority_path=authority_path,
            authority_digest=authority_digest,
        )
        descriptors.add(repo_fd)
        _prove_tree(
            repository=repository,
            authority=authority,
            authority_digest=digest,
            runtime=runtime,
            descriptors=descriptors,
            repo_fd=repo_fd,
        )
        ended = runtime.now()
        return _inspect_document(
            authority=authority,
            authority_digest=digest,
            repository=repository,
            started=started,
            ended=ended,
        )
    except IndeterminateRetirementError:
        raise
    except RetirementError:
        raise
    except OSError as exc:
        raise SafeRetirementError(str(exc)) from exc
    finally:
        descriptors.close_all()


def retire_gate2(
    *,
    repository: Path,
    confirm: str,
    authority_path: Path | None = None,
    authority_digest: str | None = None,
    hooks: RetirementHooks | None = None,
) -> dict[str, Any]:
    runtime = _Runtime(hooks or RetirementHooks())
    started = runtime.now()
    descriptors = _Descriptors()
    repo_fd: int | None = None
    renamed = False
    store_fd: int | None = None
    parent_fd: int | None = None
    destination_name = ""
    active_name = FIXED_ACTIVE_NAME
    try:
        authority, digest, repo_fd = load_authority_from_repository(
            repository,
            authority_path=authority_path,
            authority_digest=authority_digest,
        )
        descriptors.add(repo_fd)
        expected_confirm = str(authority["plan_receipt"]["sha256"])
        _require(
            confirm == expected_confirm,
            "retirement confirmation digest changed",
            {"expected": expected_confirm},
        )
        proof = _prove_tree(
            repository=repository,
            authority=authority,
            authority_digest=digest,
            runtime=runtime,
            descriptors=descriptors,
            repo_fd=repo_fd,
        )
        store_fd = proof["store_fd"]
        parent_name = proof["parent"]
        destination_name = proof["destination"]
        active_name = str(authority["filesystem"]["active_name"])
        _require(
            not _name_exists(store_fd, parent_name),
            "retirement parent already exists",
            {"parent": parent_name},
        )
        runtime.mkdir(store_fd, parent_name, 0o700)
        runtime.fsync(store_fd)
        parent_fd = descriptors.add(open_child_dir(store_fd, parent_name))
        os.fchmod(parent_fd, 0o700)
        parent_stat = os.fstat(parent_fd)
        _require(
            int(parent_stat.st_dev) == proof["device"],
            "retirement parent device changed",
        )
        _require(
            int(stat.S_IMODE(parent_stat.st_mode)) == 0o700,
            "retirement parent mode changed",
        )
        parent_entry = _entry_from_stat(parent_name, parent_stat, digest=None)
        _require(
            not _name_exists(parent_fd, destination_name),
            "retirement destination already exists",
            {"destination": destination_name},
        )
        before = inventory_digest(proof["entries"])
        try:
            if runtime.hooks.before_rename is not None:
                runtime.hooks.before_rename()
            prove_held_name(
                store_fd,
                active_name,
                proof["tree_fd"],
                directory=True,
                expected=proof["root_entry"],
            )
            prove_held_name(
                proof["tree_fd"],
                LOCK_NAME,
                proof["lock_fd"],
                directory=False,
                expected=proof["lock_entry"],
            )
            prove_held_name(
                store_fd,
                parent_name,
                parent_fd,
                directory=True,
                expected=parent_entry,
            )
            runtime.renameat2(store_fd, active_name, parent_fd, destination_name)
            renamed = True
            if runtime.hooks.after_rename is not None:
                runtime.hooks.after_rename()
            runtime.fsync(store_fd)
            runtime.fsync(parent_fd)
            runtime.syncfs(store_fd)
            if runtime.hooks.before_post_proof is not None:
                runtime.hooks.before_post_proof()
            prove_held_name(
                store_fd,
                parent_name,
                parent_fd,
                directory=True,
            )
            _require(
                not _name_exists(store_fd, active_name),
                "active Gate-2 name still exists after rename",
            )
            children = _dir_names(parent_fd)
            _require(
                children == [destination_name],
                "retirement parent does not contain exactly the destination",
                {"actual": children},
            )
            dest_fd = descriptors.add(open_child_dir(parent_fd, destination_name))
            dest_stat = os.fstat(dest_fd)
            origin = proof["tree_stat"]
            _require(
                int(dest_stat.st_ino) == int(origin.st_ino)
                and int(dest_stat.st_dev) == int(origin.st_dev),
                "retired root inode or device changed",
                {
                    "expected_inode": int(origin.st_ino),
                    "actual_inode": int(dest_stat.st_ino),
                },
            )
            dest_entry = dict(proof["root_entry"])
            dest_entry["path"] = destination_name
            dest_entry["inode"] = int(dest_stat.st_ino)
            dest_entry["device"] = int(dest_stat.st_dev)
            dest_entry["mode"] = int(stat.S_IMODE(dest_stat.st_mode))
            dest_entry["size"] = int(dest_stat.st_size)
            prove_held_name(
                parent_fd,
                destination_name,
                dest_fd,
                directory=True,
                expected=dest_entry,
            )
            after_entries = collect_inventory(
                dest_fd, runtime=runtime, expected_device=proof["device"]
            )
            _compare_inventory(after_entries, authority["filesystem"]["entries"])
            after = inventory_digest(after_entries)
            _require(after == before, "post-rename inventory digest changed")
        except IndeterminateRetirementError:
            raise
        except Exception as exc:
            if renamed:
                raise IndeterminateRetirementError(
                    str(exc) or "retirement failed after rename",
                    source_exists=_name_exists(store_fd, active_name),
                    destination_exists=_name_exists(parent_fd, destination_name)
                    if parent_fd is not None
                    else False,
                ) from exc
            if isinstance(exc, RetirementError):
                raise
            raise SafeRetirementError(str(exc)) from exc
        ended = runtime.now()
        return _receipt_document(
            authority=authority,
            authority_digest=digest,
            repository=repository,
            before=before,
            after=after,
            started=started,
            ended=ended,
        )
    except IndeterminateRetirementError:
        raise
    except RetirementError:
        raise
    except OSError as exc:
        if renamed and store_fd is not None:
            raise IndeterminateRetirementError(
                str(exc),
                source_exists=_name_exists(store_fd, active_name),
                destination_exists=_name_exists(parent_fd, destination_name)
                if parent_fd is not None
                else False,
            ) from exc
        raise SafeRetirementError(str(exc)) from exc
    finally:
        descriptors.close_all()


def map_exception(error: BaseException) -> int:
    if isinstance(error, IndeterminateRetirementError):
        return EXIT_INDETERMINATE
    if isinstance(error, RetirementError):
        return EXIT_SAFE
    return EXIT_USAGE
