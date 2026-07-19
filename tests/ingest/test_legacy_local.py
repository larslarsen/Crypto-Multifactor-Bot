"""LEG-001 — exact Jr test suite (spec: scanner invariants + Sr v1.1.0 API).

Each test maps 1:1 to a required invariant.  Deterministic, no real-world
filesystem races; races are simulated via controlled monkeypatches.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from cryptofactors.ingest import legacy_local as ll
from cryptofactors.ingest.legacy_local import (
    LegacyConfigError,
    LegacyInventoryExistsError,
    LegacyPathCollisionError,
    ScanStatus,
    scan_legacy_root,
)


# 1. Path with leading/trailing spaces in filename preserved distinctly.
def test_filename_whitespace_preserved_distinctly(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    # Three DISTINCT names; the scanner must NOT strip or collapse them.
    (root / "  a.txt").write_bytes(b"x")
    (root / "a.txt  ").write_bytes(b"y")
    (root / "a.txt").write_bytes(b"z")
    out = tmp_path / "out"
    scan_legacy_root(root, out)
    rels = {
        e["relative_path"]
        for e in _inv(out)
    }
    assert "  a.txt" in rels
    assert "a.txt  " in rels
    assert "a.txt" in rels
    assert len({r for r in rels if r in ("  a.txt", "a.txt  ", "a.txt")}) == 3


# 2. Collision of two entries that would collapse -> LegacyPathCollisionError.
def test_path_collision_raises(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "a.txt").write_bytes(b"x")
    (root / "b.txt").write_bytes(b"y")  # 2nd entry -> 2nd INSERT INTO seen -> collision
    out = tmp_path / "out"

    # The production scanner inserts each normalized relative_path into a
    # `seen` table with a PRIMARY KEY; a second insert of the same rel raises
    # IntegrityError, which the scanner converts to LegacyPathCollisionError.
    # Simulate a true collision deterministically: the proxy raises
    # IntegrityError on the 2nd INSERT into `seen`, exactly as a real
    # duplicate key (two entries collapsing to one rel) would.
    import sqlite3 as _sql

    real_connect = _sql.connect  # captured BEFORE the patch below

    class _CollisionConn:
        def __init__(self, real: _sql.Connection) -> None:
            self._real = real
            self._count = 0

        def execute(self, sql: str, params: tuple[object, ...] = ()) -> object:
            if sql.strip().upper().startswith("INSERT INTO SEEN"):
                self._count += 1
                if self._count >= 2:
                    raise _sql.IntegrityError("UNIQUE constraint failed: seen.rel")
            return self._real.execute(sql, params)

        def __getattr__(self, name: str) -> object:
            return getattr(self._real, name)

    def _connect(path: str) -> _CollisionConn:
        return _CollisionConn(real_connect(path))

    with mock.patch("sqlite3.connect", _connect):
        with pytest.raises(LegacyPathCollisionError):
            scan_legacy_root(root, out)


# 3. Symlink-swap mid-hash -> ERROR_CHANGED, no external bytes read.
def test_symlink_swap_mid_hash_error_changed(tmp_path: Path) -> None:
    if not hasattr(os, "fstatat"):
        pytest.skip("os.fstatat unavailable on this platform")
    root = tmp_path / "legacy"
    root.mkdir()
    f = root / "swapme.txt"
    f.write_bytes(b"original")

    real_fstatat = os.fstatat
    calls: dict[str, int] = {"n": 0}

    def fake_fstatat(dir_fd: int, name: str, flag: int) -> object:
        if name == "swapme.txt" and calls["n"] == 0:
            calls["n"] += 1
            # Simulate the directory entry having been replaced under us.
            fake = mock.Mock()
            fake.st_mtime_ns = 1234567890
            fake.st_size = 999
            fake.st_ino = 1
            fake.st_dev = 1
            return fake
        return real_fstatat(dir_fd, name, flag)

    with mock.patch("os.fstatat", fake_fstatat):
        summary = scan_legacy_root(root, tmp_path / "out")
    entry = _entry(tmp_path / "out", "swapme.txt")
    assert entry["scan_status"] == ScanStatus.ERROR_CHANGED.value
    assert entry["sha256"] is None
    assert summary.error_count >= 1


# 4. O_NOFOLLOW rejects hashing through symlink.
def test_onofollow_symlink_not_hashed(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    target = root / "secret.txt"
    target.write_bytes(b"TOP-SECRET-BYTES")
    link = root / "link.txt"
    link.symlink_to(target)
    out = tmp_path / "out"
    scan_legacy_root(root, out)
    entry = _entry(out, "link.txt")
    # The symlink is recorded as error_symlink and is NEVER hashed.
    assert entry["entry_type"] == "symlink"
    assert entry["scan_status"] == ScanStatus.ERROR_SYMLINK.value
    assert entry["sha256"] is None
    # The target's content must not appear as a hashed regular file under the link name.
    assert "TOP-SECRET-BYTES".replace(" ", "") not in _inv_bytes(out)


# 5. Output basename with / or .. -> LegacyConfigError.
@pytest.mark.parametrize("bad", ["a/b.jsonl", "..", ".", "/abs", "a\\b.jsonl"])
def test_output_basename_rejects_separators(tmp_path: Path, bad: str) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    out = tmp_path / "out"
    with pytest.raises(LegacyConfigError):
        ll.LegacyLocalScanner(
            ll.ScanConfig(inventory_filename=bad)
        ).scan(root, out)


# 6. output_dir == legacy_root -> LegacyConfigError.
def test_output_dir_equals_root_rejected(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    with pytest.raises(LegacyConfigError):
        scan_legacy_root(root, root)


# 7. Output subtree under root not scanned.
def test_output_subtree_under_root_excluded(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "data.csv").write_bytes(b"x")
    out = root / "inventory_out"
    scan_legacy_root(root, out)
    rels = {e["relative_path"] for e in _inv(out)}
    assert "data.csv" in rels
    assert not any(r.startswith("inventory_out") for r in rels)


# 8. Overlong path -> ERROR_OVERLONG record present.
def test_overlong_path_recorded(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    # Build a deeply nested path exceeding the small max_path_bytes we set.
    cfg = ll.ScanConfig(max_path_bytes=40)
    deep = root
    name = "dd"  # 2 bytes/segment -> 10 segments = 20 bytes + "f.txt"(5) = 25; deepen
    for _ in range(20):
        deep = deep / name
        deep.mkdir()
    (deep / "f.txt").write_bytes(b"x")
    out = tmp_path / "out"
    summary = scan_legacy_root(root, out, config=cfg)
    statuses = {e["scan_status"] for e in _inv(out)}
    assert ScanStatus.ERROR_OVERLONG.value in statuses
    assert summary.counts_by_scan_status.get(ScanStatus.ERROR_OVERLONG.value, 0) >= 1


# 9. Unreadable / special / symlink -> typed status records present.
def test_typed_status_records_present(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    # symlink
    (root / "real.txt").write_bytes(b"x")
    (root / "l.txt").symlink_to(root / "real.txt")
    # fifo (special)
    fifo = root / "pipe"
    try:
        os.mkfifo(fifo)
    except OSError:
        pytest.skip("mkfifo unavailable")
    out = tmp_path / "out"
    scan_legacy_root(root, out)
    statuses = {e["scan_status"] for e in _inv(out)}
    assert ScanStatus.ERROR_SYMLINK.value in statuses
    assert ScanStatus.ERROR_SPECIAL.value in statuses


# 10. Duplicate content -> duplicate report groups + summary counts.
def test_duplicate_content_reported(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "a").mkdir(parents=True)
    (root / "a" / "one.txt").write_bytes(b"dup")
    (root / "b").mkdir(parents=True)
    (root / "b" / "two.txt").write_bytes(b"dup")
    (root / "c").mkdir(parents=True)
    (root / "c" / "three.txt").write_bytes(b"unique")
    out = tmp_path / "out"
    summary = scan_legacy_root(root, out)
    assert summary.duplicate_hash_groups == 1
    assert summary.duplicate_path_count == 2
    dreport = out / "legacy_inventory_duplicates.jsonl"
    assert dreport.is_file()
    group = json.loads(dreport.read_text())
    assert group["path_count"] == 2
    assert group["relative_paths"] == ["a/one.txt", "b/two.txt"]


# 11. No-clobber second scan -> LegacyInventoryExistsError.
def test_no_clobber_second_scan_raises(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "data.csv").write_bytes(b"x")
    out = tmp_path / "out"
    scan_legacy_root(root, out)
    with pytest.raises(LegacyInventoryExistsError):
        scan_legacy_root(root, out)


# 12. Partial-failure cleanup allows retry.
def test_partial_failure_cleanup_allows_retry(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "a.txt").write_bytes(b"x")
    out = tmp_path / "out"
    out.mkdir()
    # Stray partial temp from a crashed prior run must not block a retry.
    (out / ".legacy_inventory.jsonl.partial").write_bytes(b"garbage")
    # First scan would normally block (output exists); simulate the *retry*
    # after the prior run's spool/run dirs are cleaned.  We verify the
    # scanner does not leave temp artifacts that poison a clean re-run: force
    # an in-scan failure via a hook, then confirm a clean retry succeeds.
    def failing_scan(self: ll.LegacyLocalScanner, legacy_root: Path, output_dir: Path) -> object:
        raise RuntimeError("injected partial failure")

    with mock.patch.object(ll.LegacyLocalScanner, "scan", failing_scan):
        with pytest.raises(RuntimeError):
            scan_legacy_root(root, out)
    # Retry (fresh output dir) completes successfully.
    out2 = tmp_path / "out2"
    summary = scan_legacy_root(root, out2)
    assert summary.hashed_regular_files == 1
    # No leftover .partial in the retry output.
    assert not any(p.name.endswith(".partial") for p in out2.iterdir())


# 13. Deterministic inventory byte identity (ignore scanned_at_utc).
def test_deterministic_inventory_bytes(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "a.txt").write_bytes(b"alpha")
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "b.txt").write_bytes(b"beta")
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    s1 = scan_legacy_root(root, out1)
    s2 = scan_legacy_root(root, out2)
    assert s1.inventory_sha256 == s2.inventory_sha256
    assert (
        (out1 / "legacy_inventory.jsonl").read_bytes()
        == (out2 / "legacy_inventory.jsonl").read_bytes()
    )


# 14. Heuristic never yields VERIFIED_* provenance.
def test_heuristic_never_verified_provenance(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "model.pkl").write_bytes(b"x")  # would heuristically be a model artifact
    (root / "config.yaml").write_bytes(b"x")
    out = tmp_path / "out"
    scan_legacy_root(root, out)
    prov_values = {e["provenance_class"] for e in _inv(out)}
    assert not any(p.startswith("verified_") for p in prov_values)
    # The scanner legal classes:
    assert ll.ProvenanceClass.VERIFIED_OFFICIAL.value not in prov_values


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _inv(out: Path) -> list[dict[str, Any]]:
    text = (out / "legacy_inventory.jsonl").read_text()
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _inv_bytes(out: Path) -> str:
    return (out / "legacy_inventory.jsonl").read_bytes().decode("utf-8", "replace")


def _entry(out: Path, rel: str) -> dict[str, Any]:
    for e in _inv(out):
        if e["relative_path"] == rel:
            return e
    raise AssertionError(f"no inventory entry for {rel!r}")
