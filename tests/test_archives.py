"""Focused tests for archive inspection."""

from source_audit.archives import audit_zip_safe
from source_audit.errors import UnsafeArchiveError
import zipfile
import pytest


def test_unsafe_path_detection(tmp_path):
    zpath = tmp_path / "test.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("../evil.txt", "bad")

    with pytest.raises(UnsafeArchiveError):
        audit_zip_safe(zpath)  # Should raise on unsafe path