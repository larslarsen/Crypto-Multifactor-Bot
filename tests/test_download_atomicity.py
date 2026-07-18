"""Focused synthetic tests for atomic content-addressed download (no network)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from source_audit.download import (
    SyntheticTransport,
    TimeoutConfig,
    atomic_download,
    content_addressed_path,
)
from source_audit.errors import ChecksumMismatchError, DownloadError, SizeLimitError
from source_audit.hashing import compute_sha256


def test_atomic_download_success_and_content_address(tmp_path: Path) -> None:
    body = b"hello-source-audit-payload"
    expected = hashlib.sha256(body).hexdigest()
    transport = SyntheticTransport(body=body, chunk_size=8)
    result = atomic_download(
        "https://example.test/obj",
        tmp_path,
        transport=transport,
        max_bytes=1024,
        chunk_size=8,
        timeout=TimeoutConfig(connect_s=1.0, read_s=1.0),
        expected_sha256=expected,
    )
    assert result.sha256 == expected
    assert result.dest_path == content_addressed_path(tmp_path, expected)
    assert result.dest_path.exists()
    assert result.dest_path.read_bytes() == body
    assert result.reused_existing is False
    assert result.checksum_verified is True
    assert result.checksum_match is True
    assert result.bytes_written == len(body)
    # No partial files left behind.
    assert list(tmp_path.glob(".partial-*")) == []
    assert list(tmp_path.glob("*.part")) == []


def test_reuse_identical_content(tmp_path: Path) -> None:
    body = b"identical-bytes"
    transport = SyntheticTransport(body=body)
    first = atomic_download("https://example.test/a", tmp_path, transport=transport)
    second = atomic_download("https://example.test/b", tmp_path, transport=transport)
    assert first.dest_path == second.dest_path
    assert second.reused_existing is True
    assert first.sha256 == second.sha256


def test_checksum_mismatch_before_publication(tmp_path: Path) -> None:
    body = b"payload"
    transport = SyntheticTransport(body=body)
    with pytest.raises(ChecksumMismatchError):
        atomic_download(
            "https://example.test/x",
            tmp_path,
            transport=transport,
            expected_sha256="0" * 64,
        )
    # Nothing published under content address; no partials.
    assert list(tmp_path.iterdir()) == []


def test_size_limit_cleans_partial(tmp_path: Path) -> None:
    body = b"0123456789abcdef"
    transport = SyntheticTransport(body=body, chunk_size=4)
    with pytest.raises(SizeLimitError):
        atomic_download(
            "https://example.test/big",
            tmp_path,
            transport=transport,
            max_bytes=8,
            chunk_size=4,
        )
    assert list(tmp_path.iterdir()) == []


def test_http_error_status(tmp_path: Path) -> None:
    transport = SyntheticTransport(body=b"nope", status_code=404)
    with pytest.raises(DownloadError):
        atomic_download("https://example.test/missing", tmp_path, transport=transport)


def test_transport_failure_cleans_up(tmp_path: Path) -> None:
    body = b"abcdefghijklmnopqrstuvwxyz"
    transport = SyntheticTransport(body=body, fail_after_bytes=5, chunk_size=4)
    with pytest.raises(DownloadError):
        atomic_download("https://example.test/fail", tmp_path, transport=transport)
    assert list(tmp_path.iterdir()) == []


def test_no_overwrite_different_content(tmp_path: Path) -> None:
    body = b"original-content-xx"
    digest = hashlib.sha256(body).hexdigest()
    target = content_addressed_path(tmp_path, digest)
    target.write_bytes(b"DIFFERENT-CONTENT!!!!!")
    # Force path collision by pre-seeding wrong bytes at the hash path of `body`.
    # Download of `body` will compute the same path and detect mismatch.
    transport = SyntheticTransport(body=body)
    with pytest.raises(DownloadError, match="different content"):
        atomic_download("https://example.test/collide", tmp_path, transport=transport)


def test_compute_sha256_matches(tmp_path: Path) -> None:
    p = tmp_path / "f.bin"
    data = b"hash-me"
    p.write_bytes(data)
    assert compute_sha256(p) == hashlib.sha256(data).hexdigest()


def test_size_limit_stops_reading_immediately(tmp_path: Path) -> None:
    """On size failure the transport is closed without draining the body."""
    body = b"x" * 1000
    transport = SyntheticTransport(body=body, chunk_size=10)
    with pytest.raises(SizeLimitError):
        atomic_download(
            "https://example.test/big",
            tmp_path,
            transport=transport,
            max_bytes=25,
            chunk_size=10,
        )
    assert transport.closed is True
    # Must not have consumed the entire body after the limit.
    assert transport.bytes_yielded < len(body)
    assert list(tmp_path.iterdir()) == []


def test_exclusive_publish_does_not_overwrite(tmp_path: Path) -> None:
    """If destination exists with different content, never overwrite."""
    body = b"payload-aaa"
    digest = hashlib.sha256(body).hexdigest()
    target = content_addressed_path(tmp_path, digest)
    target.write_bytes(b"OTHER-CONTENT-XXXX")
    transport = SyntheticTransport(body=body)
    with pytest.raises(DownloadError, match="different content"):
        atomic_download("https://example.test/x", tmp_path, transport=transport)
    assert target.read_bytes() == b"OTHER-CONTENT-XXXX"


def test_checksum_mismatch_closes_without_publish(tmp_path: Path) -> None:
    body = b"checksum-me"
    transport = SyntheticTransport(body=body)
    with pytest.raises(ChecksumMismatchError):
        atomic_download(
            "https://example.test/x",
            tmp_path,
            transport=transport,
            expected_sha256="ab" * 32,
        )
    assert transport.closed is True
    assert list(tmp_path.iterdir()) == []
