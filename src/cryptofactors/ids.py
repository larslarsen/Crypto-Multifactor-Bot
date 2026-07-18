from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON-compatible data deterministically for fingerprints."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(prefix: str, value: Any) -> str:
    if not prefix or not prefix.replace("_", "").isalnum():
        raise ValueError("prefix must be a non-empty alphanumeric/underscore string")
    return f"{prefix}_{sha256_bytes(canonical_json_bytes(value))}"
