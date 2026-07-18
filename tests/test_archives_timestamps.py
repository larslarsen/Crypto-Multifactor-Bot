"""Cross-module archive + timestamp smoke tests (AUD-002)."""

from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from source_audit.archives import audit_zip_safe
from source_audit.errors import UnsafeArchiveError
from source_audit.timestamps import infer_timestamp_unit


def test_unsafe_zip_detection(tmp_path: Path) -> None:
    zpath = tmp_path / "evil.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("../evil.txt", "bad")
    with pytest.raises(UnsafeArchiveError):
        audit_zip_safe(zpath)


def test_timestamp_inference_smoke() -> None:
    min_utc = datetime(2010, 1, 1, tzinfo=timezone.utc)
    max_utc = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assert infer_timestamp_unit(1735689600, min_utc=min_utc, max_utc=max_utc).unit.value == "s"
    assert (
        infer_timestamp_unit(1735689600000, min_utc=min_utc, max_utc=max_utc).unit.value == "ms"
    )
