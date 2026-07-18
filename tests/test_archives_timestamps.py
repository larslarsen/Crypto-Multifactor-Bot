"""Focused synthetic tests for archives and timestamps (AUD-002)."""

import zipfile
import pytest
from source_audit.archives import audit_zip_safe
from source_audit.timestamps import infer_timestamp_unit, AmbiguousTimestampError, OutOfRangeTimestampError
from source_audit.errors import UnsafeArchiveError


def test_unsafe_zip_detection(tmp_path):
    zpath = tmp_path / "evil.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("../evil.txt", "bad")
    with pytest.raises(UnsafeArchiveError):
        audit_zip_safe(zpath)  # Strict raise on unsafe path


def test_timestamp_inference():
    assert infer_timestamp_unit(1735689600)["unit"] == "s"
    assert infer_timestamp_unit(1735689600000)["unit"] == "ms"
    with pytest.raises((AmbiguousTimestampError, OutOfRangeTimestampError)):
        infer_timestamp_unit(1234567890)
