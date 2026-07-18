"""Deterministic hashing utilities."""

import hashlib
from pathlib import Path
from typing import Optional


def compute_sha256(path: Path, chunk_size: int = 8192) -> str:
    """Compute SHA-256 of a file in streaming fashion."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def verify_checksum(path: Path, expected: str) -> bool:
    """Verify file against expected hex checksum."""
    actual = compute_sha256(path)
    return actual.lower() == expected.lower()
