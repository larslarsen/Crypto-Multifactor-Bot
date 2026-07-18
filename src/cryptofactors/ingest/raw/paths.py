"""Deterministic content-addressed path helpers."""

from __future__ import annotations

from pathlib import Path

from cryptofactors.ingest.raw.errors import RawStoreError


def validate_sha256_hex(sha256_hex: str) -> str:
    digest = sha256_hex.lower().strip()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise RawStoreError(
            "sha256 must be a 64-character lowercase hex digest",
            context={"sha256": sha256_hex},
        )
    return digest


def content_addressed_relative_path(sha256_hex: str, *, prefix: str = "raw/sha256") -> Path:
    """Return ``raw/sha256/ab/cd/<full_sha256>`` as a relative path."""
    digest = validate_sha256_hex(sha256_hex)
    return Path(prefix) / digest[:2] / digest[2:4] / digest


def content_addressed_absolute_path(root: Path, sha256_hex: str, *, prefix: str = "raw/sha256") -> Path:
    return root / content_addressed_relative_path(sha256_hex, prefix=prefix)


def raw_object_id_for_sha256(sha256_hex: str) -> str:
    digest = validate_sha256_hex(sha256_hex)
    return f"raw_{digest}"
