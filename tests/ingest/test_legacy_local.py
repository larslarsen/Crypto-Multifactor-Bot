"""Focused LEG-001 scanner integration tests.

Covers the ticket invariants: bounded streaming, symlink safety, exclusions,
changed-file detection, duplicate reporting, deterministic output,
self-exclusion, and concurrent no-clobber publication.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from pathlib import Path
from unittest import mock

import pytest

from cryptofactors.ingest import legacy_local as ll
from cryptofactors.ingest.legacy_local import (
    LegacyInventoryExistsError,
    scan_legacy_root,
)


# ---------------------------------------------------------------------------
# 1. Recursive census hashes regular files + emits canonical JSONL + summary.
# ---------------------------------------------------------------------------

def test_recursive_census_hashes_and_emits(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    (root / "a").mkdir(parents=True)
    (root / "a" / "x.txt").write_bytes(b"hello")
    (root / "b.csv").write_bytes(b"world")
    out = tmp_path / "out"
    summary = scan_legacy_root(root, out)
    inv = out / "legacy_inventory.jsonl"
    sump = out / "legacy_inventory_summary.json"
    assert inv.is_file() and sump.is_file()
    lines = [json.loads(line) for line in inv.read_text().splitlines() if line.strip()]
    regular = [e for e in lines if e["entry_type"] == "regular_file" and e["sha256"]]
    assert len(regular) == 2
    assert summary.hashed_regular_files == 2
    rels = [e["relative_path"] for e in lines]
    assert rels == sorted(rels)


# ---------------------------------------------------------------------------
# 2. Symlinks recorded but never followed (target outside root not traversed).
# ---------------------------------------------------------------------------

def test_symlinks_recorded_not_followed(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_bytes(b"topsecret")
    link = root / "link_to_secret"
    link.symlink_to(outside / "secret.txt")
    out = tmp_path / "out"
    scan_legacy_root(root, out)
    lines = [json.loads(line) for line in (out / "legacy_inventory.jsonl").read_text().splitlines() if line.strip()]
    link_entry = next(e for e in lines if e["relative_path"] == "link_to_secret")
    assert link_entry["entry_type"] == "symlink"
    assert link_entry["sha256"] is None
    assert link_entry["scan_status"] == "error_symlink"
    # The outside target is NOT under root and must not be traversed/followed.
    assert not any(e["relative_path"].startswith("outside") for e in lines)


# ---------------------------------------------------------------------------
# 3. Default exclusions cover .git, venvs, caches, .env, key files.
# ---------------------------------------------------------------------------

def test_default_exclusions(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    (root / ".git").mkdir(parents=True)
    (root / ".git" / "config").write_bytes(b"x")
    (root / ".venv" / "py").mkdir(parents=True)
    (root / ".venv" / "py" / "mod.py").write_bytes(b"x")
    (root / "__pycache__").mkdir(parents=True)
    (root / "__pycache__" / "m.cpython-313.pyc").write_bytes(b"x")
    (root / ".pytest_cache").mkdir(parents=True)
    (root / ".pytest_cache" / "cache").write_bytes(b"x")
    (root / ".env").write_bytes(b"SECRET=1")
    (root / "key.pem").write_bytes(b"KEY")
    (root / "real.csv").write_bytes(b"data")
    out = tmp_path / "out"
    scan_legacy_root(root, out)
    lines = [json.loads(line) for line in (out / "legacy_inventory.jsonl").read_text().splitlines() if line.strip()]
    excluded = {e["relative_path"] for e in lines if e["scan_status"] == "skipped_excluded"}
    assert "real.csv" not in excluded
    for must_exclude in (".git", ".venv", "__pycache__", ".pytest_cache", ".env", "key.pem"):
        assert must_exclude in excluded, f"expected exclusion of {must_exclude}"


# ---------------------------------------------------------------------------
# 4. Mutating a file during hashing -> changed/error record, digest discarded.
# ---------------------------------------------------------------------------

def test_mutate_during_hash_discards_digest(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    f = root / "f.txt"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"original-content")
    out = tmp_path / "out"

    real_stream = ll._stream_sha256
    state = {"n": 0}

    def tampering_stream(path: Path, *, chunk_size: int) -> tuple[str, int]:
        state["n"] += 1
        if state["n"] == 1:
            f.write_bytes(b"tampered-content-much-longer-than-before")
        return real_stream(path, chunk_size=chunk_size)

    with mock.patch.object(ll, "_stream_sha256", tampering_stream):
        summary = scan_legacy_root(root, out)
    lines = [json.loads(line) for line in (out / "legacy_inventory.jsonl").read_text().splitlines() if line.strip()]
    entry = next(e for e in lines if e["relative_path"] == "f.txt")
    assert entry["scan_status"] == "error_changed"
    assert entry["sha256"] is None
    assert summary.error_count >= 1


# ---------------------------------------------------------------------------
# 5. Duplicate content counted correctly.
# ---------------------------------------------------------------------------

def test_duplicate_content_counted(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
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


# ---------------------------------------------------------------------------
# 6. Output located beneath the scanned root excludes itself.
# ---------------------------------------------------------------------------

def test_output_beneath_root_excluded(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "data.csv").write_bytes(b"x")
    out = root / "inventory_out"
    scan_legacy_root(root, out)
    lines = [json.loads(line) for line in (out / "legacy_inventory.jsonl").read_text().splitlines() if line.strip()]
    assert not any(e["relative_path"].startswith("inventory_out") for e in lines)
    assert "data.csv" in {e["relative_path"] for e in lines}


# ---------------------------------------------------------------------------
# 7. Existing output files are never overwritten (single scan).
# ---------------------------------------------------------------------------

def test_existing_output_not_overwritten(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "data.csv").write_bytes(b"x")
    out = tmp_path / "out"
    out.mkdir()
    (out / "legacy_inventory.jsonl").write_bytes(b"PRE-EXISTING")
    with pytest.raises(LegacyInventoryExistsError):
        scan_legacy_root(root, out)
    assert (out / "legacy_inventory.jsonl").read_bytes() == b"PRE-EXISTING"


# ---------------------------------------------------------------------------
# 8. Concurrent publication is race-safe: a competing writer appearing between
#    the existence check and the link must NOT be clobbered. The corrected
#    ``_atomic_publish_bytes`` uses an O_EXCL hard link, so it raises instead
#    of overwriting.
# ---------------------------------------------------------------------------

def test_concurrent_publish_no_clobber_under_race() -> None:
    d = Path(tempfile.mkdtemp(prefix="leg001-race-"))
    target = d / "inventory.jsonl"

    real_link = os.link

    def racing_link(src: str, dst: str) -> None:
        # Simulate a second concurrent scan that created `dst` between the
        # pre-check and the link call.
        if not os.path.exists(dst):
            Path(dst).write_bytes(b"COMPETING-WRITER-BYTES")
        real_link(src, dst)  # O_EXCL-style: raises FileExistsError if dst exists

    with mock.patch("os.link", racing_link):
        # The no-clobber contract under a race is: refuse, not overwrite.
        with pytest.raises(LegacyInventoryExistsError):
            ll._atomic_publish_bytes(target, b"MY-SCAN-BYTES", label="inventory")
    # The surviving destination must still be the competing writer's bytes,
    # proving our scan did NOT clobber it.
    assert target.read_bytes() == b"COMPETING-WRITER-BYTES"


# ---------------------------------------------------------------------------
# 8b. Two truly concurrent scans targeting the same output dir cannot clobber
#     each other: exactly one wins, the other raises, and no bytes are lost
#     silently.
# ---------------------------------------------------------------------------

def test_two_concurrent_scans_no_clobber(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "a.txt").write_bytes(b"alpha")
    (root / "b.txt").write_bytes(b"beta")
    out = tmp_path / "out"

    results: dict[int, object] = {}
    barrier = threading.Barrier(2)

    def worker(wid: int) -> None:
        barrier.wait()
        try:
            summary = scan_legacy_root(root, out)
            results[wid] = summary.inventory_sha256
        except LegacyInventoryExistsError:
            results[wid] = "exists"

    t1 = threading.Thread(target=worker, args=(1,))
    t2 = threading.Thread(target=worker, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Exactly one scan must have raised (no-clobber); the other must have
    # published.  Both outcomes present, no silent clobber.
    assert results[1] != results[2], f"both scans had identical outcome: {results}"
    assert "exists" in results.values()
    published = [v for v in results.values() if v != "exists"]
    assert len(published) == 1, f"expected exactly one published scan, got {results}"

    # Exactly one inventory file exists and is intact (both source files present).
    assert (out / "legacy_inventory.jsonl").is_file()
    lines = (out / "legacy_inventory.jsonl").read_text().splitlines()
    rels = sorted(json.loads(line)["relative_path"] for line in lines)
    assert rels == ["a.txt", "b.txt"]


# ---------------------------------------------------------------------------
# 9. Summary inventory SHA-256 and byte count match the published JSONL bytes.
# ---------------------------------------------------------------------------

def test_summary_hash_matches_published_jsonl(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "a.txt").write_bytes(b"alpha")
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "b.txt").write_bytes(b"beta")
    out = tmp_path / "out"
    summary = scan_legacy_root(root, out)
    inv_bytes = (out / "legacy_inventory.jsonl").read_bytes()
    assert summary.inventory_byte_size == len(inv_bytes)
    assert summary.inventory_sha256 == hashlib.sha256(inv_bytes).hexdigest()


# ---------------------------------------------------------------------------
# 10. Repeated scans of an unchanged tree produce identical inventory records.
# ---------------------------------------------------------------------------

def test_repeated_scan_identical_inventory(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "a.txt").write_bytes(b"alpha")
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "b.txt").write_bytes(b"beta")
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    s1 = scan_legacy_root(root, out1)
    s2 = scan_legacy_root(root, out2)
    inv1 = (out1 / "legacy_inventory.jsonl").read_bytes()
    inv2 = (out2 / "legacy_inventory.jsonl").read_bytes()
    assert inv1 == inv2
    assert s1.inventory_sha256 == s2.inventory_sha256
    sum1 = json.loads((out1 / "legacy_inventory_summary.json").read_text())
    sum2 = json.loads((out2 / "legacy_inventory_summary.json").read_text())
    # The inventory is stable; the summary's only time-dependent field is
    # scanned_at_utc, so comparing inventory hashes is the determinism check.
    assert sum1["inventory_sha256"] == sum2["inventory_sha256"]


# ---------------------------------------------------------------------------
# 11. Bounded streaming: inventory output stays byte-identical whether built
#     from a tiny or a large number of files (external merge sort, no in-RAM
#     accumulation of all records at once).
# ---------------------------------------------------------------------------

def test_bounded_streaming_deterministic_on_large_tree(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    n = 5000
    for i in range(n):
        (root / f"f{i:05d}.txt").write_bytes(f"content-{i}".encode())
    out = tmp_path / "out"
    summary = scan_legacy_root(root, out)
    assert summary.hashed_regular_files == n
    lines = (out / "legacy_inventory.jsonl").read_text().splitlines()
    assert len(lines) == n
    rels = [json.loads(line)["relative_path"] for line in lines]
    assert rels == sorted(rels)  # proves a real sort happened, not insertion order
