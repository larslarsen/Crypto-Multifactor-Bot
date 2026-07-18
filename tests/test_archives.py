"""Focused tests for archive inspection."""

from pathlib import Path
from source_audit.archives import audit_zip_safe
from source_audit.errors import UnsafeArchiveError
import tempfile
import zipfile


def test_unsafe_path_detection(tmp_path):
    zpath = tmp_path / "test.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("../evil.txt", "bad")

    result = audit_zip_safe(zpath)
    assert any(m.is_unsafe for m in result.members)
