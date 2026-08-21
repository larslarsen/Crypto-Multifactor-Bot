"""Focused synthetic tests for atomic content-addressed download (no network)."""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

import pytest

from source_audit.download import (
    PooledHttpxTransport,
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


# --- ADR-0018 bounded connection reuse (no network) -----------------------------------


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.status_code = 200
        self.headers = {"content-length": str(len(body))}
        self._body = body
        self.closed = 0

    def iter_bytes(self):  # noqa: ANN201 - mirrors the httpx streaming surface
        yield self._body

    def close(self) -> None:
        self.closed += 1


class _FakeClient:
    """Minimal httpx.Client stand-in that records construction, sends, and closure."""

    instances: list["_FakeClient"] = []

    def __init__(self, *, timeout=None, follow_redirects=False, limits=None) -> None:
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.limits = limits
        self.requests: list[tuple[str, dict, object]] = []
        self.responses: list[_FakeResponse] = []
        self.closes = 0
        _FakeClient.instances.append(self)

    def build_request(self, method: str, url: str, *, headers=None, timeout=None):  # noqa: ANN201
        request = {"method": method, "url": url, "headers": dict(headers or {}), "timeout": timeout}
        self.requests.append((url, dict(headers or {}), timeout))
        return request

    def send(self, request, *, stream: bool = False) -> _FakeResponse:
        response = _FakeResponse(b"pooled-body")
        self.responses.append(response)
        return response

    def close(self) -> None:
        self.closes += 1


def _pooled(**kwargs) -> PooledHttpxTransport:  # noqa: ANN003
    _FakeClient.instances.clear()
    return PooledHttpxTransport(client_factory=_FakeClient, **kwargs)


def test_pooled_transport_constructs_one_client_and_reuses_it() -> None:
    transport = _pooled(max_connections=4)
    timeout = TimeoutConfig(connect_s=1.0, read_s=2.0)
    for index in range(3):
        response = transport.stream_get(
            f"https://example.test/{index}", headers={"api_key": "secret"}, timeout=timeout
        )
        assert b"".join(response.iter_bytes) == b"pooled-body"
        response.close_response()
    # One client for the whole invocation, reused across every request.
    assert transport.clients_constructed == 1
    assert len(_FakeClient.instances) == 1
    client = _FakeClient.instances[0]
    assert transport.requests_sent == 3
    assert len(client.requests) == 3
    # Streaming a response never closes the shared client.
    assert client.closes == 0
    assert transport.clients_closed == 0
    # Per-call timeouts are still applied per request, and the pool ceiling is explicit.
    assert all(item[2] is not None for item in client.requests)
    assert client.limits.max_connections == 4
    # Credentials stay per request and are never held on the transport.
    assert all(item[1] == {"api_key": "secret"} for item in client.requests)
    assert "secret" not in repr(transport)


def test_pooled_transport_closes_the_client_exactly_once() -> None:
    transport = _pooled(max_connections=2)
    transport.stream_get(
        "https://example.test/a", headers=None, timeout=TimeoutConfig()
    ).close_response()
    transport.close()
    transport.close()
    client = _FakeClient.instances[0]
    assert client.closes == 1
    assert transport.clients_closed == 1
    # A closed transport refuses new work instead of silently reopening a pool.
    with pytest.raises(DownloadError, match="pooled transport is closed"):
        transport.stream_get("https://example.test/b", headers=None, timeout=TimeoutConfig())


def test_pooled_transport_context_manager_closes_on_error() -> None:
    transport = _pooled(max_connections=2)
    with pytest.raises(RuntimeError, match="boom"), transport:
        transport.stream_get(
            "https://example.test/a", headers=None, timeout=TimeoutConfig()
        ).close_response()
        raise RuntimeError("boom")
    assert transport.clients_closed == 1
    assert _FakeClient.instances[0].closes == 1


def test_pooled_transport_publishes_through_unchanged_atomic_download(tmp_path: Path) -> None:
    transport = _pooled(max_connections=2)
    result = atomic_download(
        "https://example.test/obj",
        tmp_path,
        transport=transport,
        max_bytes=1024,
        timeout=TimeoutConfig(connect_s=1.0, read_s=1.0),
    )
    expected = hashlib.sha256(b"pooled-body").hexdigest()
    # Publication semantics are untouched for every consumer.
    assert result.sha256 == expected
    assert result.dest_path == content_addressed_path(tmp_path, expected)
    assert result.dest_path.read_bytes() == b"pooled-body"
    assert compute_sha256(result.dest_path) == expected
    transport.close()
    assert transport.clients_closed == 1


def test_pooled_transport_rejects_a_zero_connection_ceiling() -> None:
    with pytest.raises(ValueError, match="max_connections"):
        PooledHttpxTransport(max_connections=0)


def test_pooled_transport_first_use_is_thread_safe() -> None:
    """Concurrent first use constructs exactly one client and leaks no loser."""
    transport = _pooled(max_connections=8)
    barrier = threading.Barrier(8)
    errors: list[BaseException] = []

    def _first_use() -> None:
        try:
            barrier.wait(timeout=5)
            response = transport.stream_get(
                "https://example.test/race", headers=None, timeout=TimeoutConfig()
            )
            response.close_response()
        except BaseException as exc:  # noqa: BLE001 - re-raised by the assertions below
            errors.append(exc)

    threads = [threading.Thread(target=_first_use) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert errors == []
    assert transport.clients_constructed == 1
    assert len(_FakeClient.instances) == 1
    # Every request went through the one retained client; nothing was overwritten.
    assert transport.requests_sent == 8
    assert len(_FakeClient.instances[0].requests) == 8
    transport.close()
    assert transport.clients_closed == 1
    assert _FakeClient.instances[0].closes == 1


def test_pooled_transport_close_failure_reports_no_successful_close() -> None:
    transport = _pooled(max_connections=2)
    transport.stream_get(
        "https://example.test/a", headers=None, timeout=TimeoutConfig()
    ).close_response()
    client = _FakeClient.instances[0]

    def _explode() -> None:
        client.closes += 1
        raise RuntimeError("client close failed")

    client.close = _explode  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="client close failed"):
        transport.close()

    # A failed close is never reported as a clean shutdown.
    assert transport.clients_closed == 0
    assert client.closes == 1
    # The transport still refuses new work and holds no alternate client.
    with pytest.raises(DownloadError, match="pooled transport is closed"):
        transport.stream_get("https://example.test/b", headers=None, timeout=TimeoutConfig())
    assert transport.clients_constructed == 1
    assert len(_FakeClient.instances) == 1
    # A second close finds nothing left to close and stays quiet.
    transport.close()
    assert client.closes == 1
    assert transport.clients_closed == 0
