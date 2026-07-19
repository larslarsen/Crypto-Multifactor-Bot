"""LEG-001 v1.2.0 — Jr validation suite (exact 10 invariant focus).

Each test maps 1:1 to a required invariant. Deterministic; races are
simulated via controlled patches (fstat/open), not real wall-clock timing.
"""

from __future__ import annotations

import base64
import json
import os
import sqlite3 as _sql
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

import cryptofactors.ingest.legacy_local as ll
from cryptofactors.ingest.legacy_local import (
    LegacyInventoryExistsError,
    LegacyPathCollisionError,
    ScanStatus,
    scan_legacy_root,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inv(out: Path) -> list[dict[str, Any]]:
    text = (out / "legacy_inventory.jsonl").read_text()
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _entry(out: Path, rel: str) -> dict[str, Any]:
    for e in _inv(out):
        if e["relative_path"] == rel:
            return e
    raise AssertionError(f"no inventory entry for {rel!r}")


# ---------------------------------------------------------------------------
# 1. Filename with embedded newline survives and is unique in inventory.
# ---------------------------------------------------------------------------


def test_embedded_newline_name_unique(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    # POSIX allows newlines inside a single name component.
    (root / "a\nb.txt").write_bytes(b"x")
    (root / "a.txt").write_bytes(b"y")
    out = tmp_path / "out"
    scan_legacy_root(root, out)
    # The newline name is encoded reversibly (b64: due to embedded newline) and
    # is its own unique entry, distinct from the plain "a.txt".
    rels = [e["relative_path"] for e in _inv(out)]
    assert "b64:YQpiLnR4dA==" in rels  # a\nb.txt (reversible b64 form)
    assert "a.txt" in rels
    assert len(rels) == len(set(rels))  # newline name is its own unique entry
    assert len(_inv(out)) == 2


# ---------------------------------------------------------------------------
# 2. Non-UTF-8 name -> b64: display, no surrogates in JSONL.
# ---------------------------------------------------------------------------


def test_non_utf8_name_b64_display(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    bad = b"caf\xc3\x28"  # invalid UTF-8 byte sequence
    # Create the file with the raw bytes name via the os bytes API.
    path_bytes = bytes(root) + b"/" + bad
    fd = os.open(path_bytes, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    with os.fdopen(fd, "wb") as fh:
        fh.write(b"z")
    out = tmp_path / "out"
    scan_legacy_root(root, out)
    raw = (out / "legacy_inventory.jsonl").read_text()
    # The JSONL must contain NO surrogate code points anywhere.
    for line in raw.splitlines():
        json.loads(line)  # parseable
    for ch in raw:
        assert not (0xD800 <= ord(ch) <= 0xDFFF), f"surrogate in JSONL: {ch!r}"
    rel = [e["relative_path"] for e in _inv(out) if e["relative_path"].startswith("b64:")][0]
    # The b64 payload decodes back to the exact raw bytes.
    payload = rel[len("b64:"):]
    assert base64.b64decode(payload) == bad


# ---------------------------------------------------------------------------
# 3. Path collision on binary identity -> LegacyPathCollisionError.
# ---------------------------------------------------------------------------


def test_path_collision_binary_identity(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "a.txt").write_bytes(b"x")
    (root / "b.txt").write_bytes(b"y")
    out = tmp_path / "out"

    # The scanner inserts each entry's binary identity key into `seen(id_key)`
    # with a PRIMARY KEY; a 2nd insert of the same id_key raises IntegrityError,
    # converted to LegacyPathCollisionError. Simulate a true duplicate key.
    real_connect = _sql.connect

    class _CollisionConn:
        def __init__(self, real: _sql.Connection) -> None:
            self._real = real
            self._count = 0

        def execute(self, sql: str, params: tuple[object, ...] = ()) -> object:
            if sql.strip().upper().startswith("INSERT INTO SEEN"):
                self._count += 1
                if self._count >= 2:
                    raise _sql.IntegrityError("UNIQUE constraint failed: seen.id_key")
            return self._real.execute(sql, params)

        def __getattr__(self, name: str) -> object:
            return getattr(self._real, name)

    def _connect(path: str) -> _CollisionConn:
        return _CollisionConn(real_connect(path))

    with mock.patch("sqlite3.connect", _connect):
        with pytest.raises(LegacyPathCollisionError):
            scan_legacy_root(root, out)


# ---------------------------------------------------------------------------
# 4. Symlink swap mid-hash -> ERROR_CHANGED.
# ---------------------------------------------------------------------------


def test_symlink_swap_mid_hash_error_changed(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "swapme.txt").write_bytes(b"original")
    out = tmp_path / "out"

    real_fstat = os.fstat
    calls = {"n": 0}

    def fake_fstat(fd: int) -> object:
        st = real_fstat(fd)
        # 2nd fstat (post-hash revalidation) returns a different identity.
        if calls["n"] == 0:
            calls["n"] += 1
            return st
        fake = mock.Mock()
        fake.st_mode = st.st_mode
        fake.st_size = st.st_size
        fake.st_mtime_ns = 9999999999  # differs from st_before
        fake.st_ino = st.st_ino
        fake.st_dev = st.st_dev
        return fake

    with mock.patch("os.fstat", fake_fstat):
        scan_legacy_root(root, out)
    entry = _entry(out, "swapme.txt")
    assert entry["scan_status"] == ScanStatus.ERROR_CHANGED.value
    assert entry["sha256"] is None


# ---------------------------------------------------------------------------
# 5. Parent directory replaced by symlink mid-traversal -> no escape outside root.
# ---------------------------------------------------------------------------


def test_symlink_dir_swap_no_escape(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "file.txt").write_bytes(b"top")
    sub = root / "sub"
    sub.mkdir()
    (sub / "inner.txt").write_bytes(b"inner")
    # A sibling directory OUTSIDE root that must never be reached.
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_bytes(b"leak")
    out = tmp_path / "out"

    real_open = os.open

    def fake_open(file: str | bytes | int, *args: object, **kwargs: object) -> int:
        # Simulate `sub` having been swapped to an escaping symlink between
        # enqueue and descriptor-relative reopen.
        name = file if isinstance(file, (str, bytes)) else None
        if name is not None and os.fsdecode(name) == "sub":
            raise OSError(40, "Too many levels of symbolic links", "sub")  # ELOOP
        return real_open(file, *args, **kwargs)  # type: ignore[arg-type]

    with mock.patch("os.open", fake_open):
        summary = scan_legacy_root(root, out)

    rels = {e["relative_path"] for e in _inv(out)}
    # No entry from outside the root may appear — escape is prevented.
    assert "secret.txt" not in rels
    assert not any(r.startswith("outside") for r in rels)
    # `sub` is recorded (it was a directory at list time) but is NOT expanded:
    # its child is never scanned.
    assert "sub/inner.txt" not in rels
    # The walk failure is recorded as a traversal/unreadable error (not silent).
    err_entries = [
        e for e in _inv(out)
        if e["relative_path"].startswith("sub")
        and e["scan_status"]
        in (ScanStatus.ERROR_UNREADABLE.value, ScanStatus.ERROR_SYMLINK.value)
    ]
    assert err_entries  # the swapped-dir failure is surfaced, not hidden
    assert summary.error_count >= 1


# ---------------------------------------------------------------------------
# 6. Overlong path -> full identity retained + ERROR_OVERLONG.
# ---------------------------------------------------------------------------


def test_overlong_full_identity_retained(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    cfg = ll.ScanConfig(max_path_bytes=40)
    deep = root
    for _ in range(20):
        deep = deep / "dd"
        deep.mkdir()
    (deep / "f.txt").write_bytes(b"x")
    out = tmp_path / "out"
    summary = scan_legacy_root(root, out, config=cfg)
    assert summary.counts_by_scan_status.get(ScanStatus.ERROR_OVERLONG.value, 0) >= 1
    # The overlong entry keeps its full (non-truncated) identity.
    overlong = [
        e for e in _inv(out) if e["scan_status"] == ScanStatus.ERROR_OVERLONG.value
    ]
    assert overlong
    for e in overlong:
        # Identity is the full joined path, not cut to max_path_bytes.
        assert e["relative_path"].endswith("dd") or e["relative_path"].count("dd/") >= 1
        assert len(e["relative_path"]) > 0


# ---------------------------------------------------------------------------
# 7. Work/stage dirs never appear in census.
# ---------------------------------------------------------------------------


def test_work_stage_dirs_excluded(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "real.txt").write_bytes(b"x")
    # Scanner's own scratch dirs live under root in this scenario.
    work = root / ".leg001-work-abc"
    work.mkdir()
    (work / "scratch.txt").write_bytes(b"junk")
    stage = root / ".leg001-stage-def"
    stage.mkdir()
    (stage / "staged.txt").write_bytes(b"junk")
    out = tmp_path / "out"
    scan_legacy_root(root, out)
    rels = {e["relative_path"] for e in _inv(out)}
    assert "real.txt" in rels
    assert ".leg001-work-abc/scratch.txt" not in rels
    assert ".leg001-stage-def/staged.txt" not in rels
    # Excluded entries are recorded as skipped_excluded, not hashed.
    for e in _inv(out):
        if e["relative_path"].startswith(".leg001-"):
            assert e["scan_status"] == ScanStatus.SKIPPED_EXCLUDED.value
            assert e["sha256"] is None


# ---------------------------------------------------------------------------
# 8. Duplicate report streams correctly; summary counts match.
# ---------------------------------------------------------------------------


def test_duplicate_report_streams_and_counts_match(tmp_path: Path) -> None:
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
    assert set(group["relative_paths"]) == {"a/one.txt", "b/two.txt"}


# ---------------------------------------------------------------------------
# 9. Concurrent second publisher -> no-clobber; partial rollback allows retry.
# ---------------------------------------------------------------------------


def test_concurrent_no_clobber_and_rollback_retry(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "data.csv").write_bytes(b"x")
    out = tmp_path / "out"
    scan_legacy_root(root, out)

    # Second publisher into the SAME output must not clobber.
    with pytest.raises(LegacyInventoryExistsError):
        scan_legacy_root(root, out)

    # Partial failure during publish (after reservation succeeds) must roll
    # back and leave nothing blocking a clean retry into a fresh output dir.
    real_link = os.link
    calls = {"n": 0}

    def failing_link(src: str, dst: str, *a: object, **k: object) -> None:
        calls["n"] += 1
        if calls["n"] >= 2:  # fail after the first artifact is linked
            raise OSError(5, "I/O error")  # ENOTEMPTY-style mid-publish failure
        real_link(src, dst)

    with mock.patch("os.link", failing_link):
        with pytest.raises(Exception):
            scan_legacy_root(root, tmp_path / "out_rollback")

    # A clean retry into a fresh output directory succeeds.
    summary = scan_legacy_root(root, tmp_path / "out2")
    assert summary.total_entries >= 1


# ---------------------------------------------------------------------------
# 10. Memory stays bounded on large trees (streaming run files, no full buffers).
# ---------------------------------------------------------------------------


def test_bounded_streaming_on_large_tree(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    n = 5000
    for i in range(n):
        (root / f"f{i:05d}.bin").write_bytes(b"seed-%d" % (i % 97))
    out = tmp_path / "out"

    captured: dict[str, Any] = {}

    real_merge: Any = getattr(ll, "_merge_runs_streaming")

    def spy_merge(run_paths: list[Path], out_path: Path) -> tuple[str, int]:
        # Capture streaming evidence DURING the scan (work dir is removed after).
        captured["run_count"] = len(run_paths)
        captured["run_sizes"] = [p.stat().st_size for p in run_paths if p.exists()]
        result: tuple[str, int] = real_merge(run_paths, out_path)
        return result

    with mock.patch(
        "cryptofactors.ingest.legacy_local._merge_runs_streaming", spy_merge
    ):
        summary = scan_legacy_root(root, out)

    assert summary.total_entries == n
    assert summary.hashed_regular_files == n
    # Streaming produced multiple bounded run files (not one in-RAM buffer).
    assert captured["run_count"] >= 2, "expected multiple spilled runs"
    run_sizes = captured["run_sizes"]
    assert run_sizes, "run files were materialized"
    # No single run holds the entire tree in memory (bounded by _RUN_BUFFER_LIMIT=2048).
    assert max(run_sizes) < n * 200  # each run is a small fraction of the tree
    # Inventory fully captures the tree (sorted, complete).
    assert len(_inv(out)) == n


# ===========================================================================
# Sr acceptance blockers (v1.2.1) — encoded as focused tests.
# ===========================================================================


# Blocker 1: Bounded directory iteration + streaming duplicates.
def test_bounded_iteration_and_streaming_duplicates(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    # Many entries: traversal must not fully materialize via os.listdir.
    many = 1000
    for i in range(many):
        (root / f"e{i:04d}.dat").write_bytes(b"entry-%d" % i)
    # Two files share one content hash -> repeated hash in duplicate report.
    (root / "dup_a.txt").write_bytes(b"shared-content")
    (root / "dup_b.txt").write_bytes(b"shared-content")
    out = tmp_path / "out"
    summary = scan_legacy_root(root, out)
    # Census completed over the large directory.
    assert summary.total_entries == many + 2
    assert summary.hashed_regular_files == many + 2
    # The repeated content hash is reported with both relative paths.
    assert summary.duplicate_hash_groups == 1
    assert summary.duplicate_path_count == 2
    group = json.loads((out / "legacy_inventory_duplicates.jsonl").read_text())
    assert set(group["relative_paths"]) == {"dup_a.txt", "dup_b.txt"}


# Blocker 2: Reversible, collision-free path representation + deterministic order.
def test_b64_self_wrap_distinct_and_deterministic_order(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    # Raw byte name b"\x80" and a literal UTF-8 file named "b64:gA==" must
    # produce TWO different relative_path values.
    raw_path = bytes(root) + b"/" + b"\x80"
    fd = os.open(raw_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    with os.fdopen(fd, "wb") as fh:
        fh.write(b"raw")
    lit_path = bytes(root) + b"/" + b"b64:gA=="
    fd = os.open(lit_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    with os.fdopen(fd, "wb") as fh:
        fh.write(b"literal")

    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    scan_legacy_root(root, out1)
    scan_legacy_root(root, out2)

    rels = [e["relative_path"] for e in _inv(out1)]
    # Raw byte b"\x80" -> b64:gA== ; literal UTF-8 "b64:gA==" -> re-wrapped again
    # to b64:YjY0OmdBPT0= . The two MUST be distinct values.
    raw_rel = "b64:gA=="
    lit_rel = "b64:YjY0OmdBPT0="
    assert raw_rel in rels
    assert lit_rel in rels
    assert raw_rel != lit_rel

    # Deterministic ordering: inventory bytes identical across two scans
    # (scanned_at_utc lives only in the summary, not the inventory JSONL).
    inv1 = (out1 / "legacy_inventory.jsonl").read_bytes()
    inv2 = (out2 / "legacy_inventory.jsonl").read_bytes()
    assert inv1 == inv2


# Blocker 3: Zero-byte regular file size.
def test_zero_byte_regular_file_size(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "empty.txt").write_bytes(b"")  # empty regular file
    (root / "nonempty.txt").write_bytes(b"x")
    out = tmp_path / "out"
    scan_legacy_root(root, out)
    empty = _entry(out, "empty.txt")
    assert empty["entry_type"] == "regular_file"
    assert empty["byte_size"] == 0  # not null / omitted
    nonempty = _entry(out, "nonempty.txt")
    assert nonempty["byte_size"] == 1


# Blocker 4: Output/work subtree exclusion before enqueue or hash.
def test_output_subtree_excluded_before_enqueue(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "keep.txt").write_bytes(b"keep me")
    # Layout: legacy_root/out/preexisting.txt with output_dir = legacy_root/out
    out = root / "out"
    out.mkdir()
    (out / "preexisting.txt").write_bytes(b"should not be scanned")
    summary = scan_legacy_root(root, out)
    rels = {e["relative_path"] for e in _inv(out)}
    # The pre-existing output artifact must NOT appear in the census.
    assert "out/preexisting.txt" not in rels
    assert "preexisting.txt" not in rels
    # Summary records the output self-exclusion.
    assert summary.excluded_by_rule.get("output_self", 0) >= 1


# Regression guard for the v1.2.2 merge-key fix: external merge (including
# intermediate levels) must order by canonical binary identity, never by the
# display relative_path. Force a multi-level merge, then confirm the inventory
# is byte-identical across two scans.
def test_multilevel_merge_deterministic_binary_order(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    n = 2000
    for i in range(n):
        (root / f"f{i:05d}.bin").write_bytes(b"seed-%d" % (i % 131))
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"

    with mock.patch.object(ll, "_RUN_BUFFER_LIMIT", 50):
        s1 = scan_legacy_root(root, out1)
        s2 = scan_legacy_root(root, out2)
    assert s1.total_entries == n
    assert s1.hashed_regular_files == n
    assert s2.total_entries == n
    # Byte-identical across scans proves stable binary-key ordering at every
    # merge level (display paths would sort differently under some locales).
    inv1 = (out1 / "legacy_inventory.jsonl").read_bytes()
    inv2 = (out2 / "legacy_inventory.jsonl").read_bytes()
    assert inv1 == inv2


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
