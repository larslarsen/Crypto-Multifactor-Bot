"""Focused synthetic tests for archives and timestamps (AUD-002)."""

import tempfile
import zipfile
from pathlib import Path
import pytest
from source_audit.archives import audit_zip_safe, audit_csv_safe
from source_audit.timestamps import infer_timestamp_unit, AmbiguousTimestampError, OutOfRangeTimestampError
from source_audit.errors import UnsafeArchiveError, MalformedCSVError


def test_unsafe_zip_detection(tmp_path):
    zpath = tmp_path / "evil.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("../evil.txt", "bad")
    result = audit_zip_safe(zpath)
    assert any(m.is_unsafe for m in result.members)


def test_timestamp_inference():
    assert infer_timestamp_unit(1735689600)["unit"] == "s"
    assert infer_timestamp_unit(1735689600000)["unit"] == "ms"
    with pytest.raises((AmbiguousTimestampError, OutOfRangeTimestampError)):
        infer_timestamp_unit(1234567890)
