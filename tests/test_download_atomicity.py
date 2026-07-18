"""Focused tests for atomic download behavior."""

import pytest
from pathlib import Path
from source_audit.download import atomic_download
from source_audit.errors import ChecksumMismatchError


def test_atomic_download_stub_raises():
    with pytest.raises(NotImplementedError):
        atomic_download("https://example.com", Path("/tmp"))
