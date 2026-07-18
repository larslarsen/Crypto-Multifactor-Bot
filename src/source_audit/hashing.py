"""Deterministic streaming hashing utilities."""

from __future__ import annotations

import hashlib
from pathlib import Path


def compute_sha256(path: Path, *, chunk_size: int = 8192) -> str:
    """Compute the SHA-256 hex digest of a file in streaming fashion."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(path: Path, expected: str, *, chunk_size: int = 8192) -> bool:
    """Return True when the file's SHA-256 matches ``expected`` (case-insensitive)."""
    actual = compute_sha256(path, chunk_size=chunk_size)
    return actual.lower() == expected.lower().strip()
