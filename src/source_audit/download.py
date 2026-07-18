"""Bounded streaming HTTP acquisition with atomic content-addressed publication."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable
from urllib.parse import urlencode

import httpx

from .errors import ChecksumMismatchError, DownloadError, SizeLimitError
from .hashing import compute_sha256
from .models import DownloadResult


@dataclass(frozen=True, slots=True)
class TimeoutConfig:
    """Separate connection and read timeouts in seconds."""

    connect_s: float = 10.0
    read_s: float = 60.0

    def __post_init__(self) -> None:
        if self.connect_s <= 0 or self.read_s <= 0:
            raise ValueError("timeouts must be positive")


@dataclass(slots=True)
class StreamResponse:
    """Transport-level streaming response with deterministic close."""

    status_code: int
    headers: Mapping[str, str]
    iter_bytes: Iterator[bytes]
    close: Callable[[], None] = field(default=lambda: None)
    _closed: bool = field(default=False, repr=False)

    def close_response(self) -> None:
        """Close the underlying response without draining remaining body bytes."""
        if self._closed:
            return
        self._closed = True
        try:
            self.close()
        except Exception:
            pass


@runtime_checkable
class HttpTransport(Protocol):
    """Injectable transport for tests and production HTTP clients."""

    def stream_get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        timeout: TimeoutConfig,
    ) -> StreamResponse:
        """Open a streaming GET and return status, headers, and a byte iterator."""
        ...


class HttpxTransport:
    """Default production transport using httpx streaming."""

    def stream_get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        timeout: TimeoutConfig,
    ) -> StreamResponse:
        timeout_cfg = httpx.Timeout(
            connect=timeout.connect_s,
            read=timeout.read_s,
            write=timeout.read_s,
            pool=timeout.connect_s,
        )
        client = httpx.Client(timeout=timeout_cfg, follow_redirects=True)
        response: httpx.Response | None = None
        try:
            request = client.build_request("GET", url, headers=dict(headers or {}))
            response = client.send(request, stream=True)
            status = response.status_code
            resp_headers = {k: v for k, v in response.headers.items()}
            resp = response

            def _chunks() -> Iterator[bytes]:
                try:
                    yield from resp.iter_bytes()
                finally:
                    # Iterator exhaustion path also closes.
                    try:
                        resp.close()
                    except Exception:
                        pass
                    try:
                        client.close()
                    except Exception:
                        pass

            def _close() -> None:
                try:
                    resp.close()
                except Exception:
                    pass
                try:
                    client.close()
                except Exception:
                    pass

            return StreamResponse(
                status_code=status,
                headers=resp_headers,
                iter_bytes=_chunks(),
                close=_close,
            )
        except Exception:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
            try:
                client.close()
            except Exception:
                pass
            raise


def content_addressed_path(dest_dir: Path, sha256_hex: str) -> Path:
    """Deterministic destination path: full SHA-256 hex digest as object identity."""
    digest = sha256_hex.lower().strip()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise DownloadError(
            "sha256 must be a 64-character lowercase hex digest",
            context={"sha256": sha256_hex},
        )
    return dest_dir / digest


def _publish_exclusive(tmp_path: Path, final_path: Path) -> bool:
    """Publish ``tmp_path`` to ``final_path`` without overwriting an existing object.

    Returns True when this caller created ``final_path``; False when the path
    already existed (caller must verify content). Uses ``os.link`` so concurrent
    publishers cannot clobber an existing object. Falls back to ``O_CREAT|O_EXCL``
    when hardlinks are unavailable.
    """
    try:
        os.link(str(tmp_path), str(final_path))
        return True
    except FileExistsError:
        return False
    except OSError:
        try:
            fd = os.open(str(final_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
        except FileExistsError:
            return False
        os.replace(str(tmp_path), str(final_path))
        return True


def atomic_download(
    url: str,
    dest_dir: Path,
    *,
    params: Mapping[str, str] | None = None,
    headers: Mapping[str, str] | None = None,
    max_bytes: int = 100 * 1024 * 1024,
    chunk_size: int = 8192,
    timeout: TimeoutConfig | None = None,
    expected_sha256: str | None = None,
    transport: HttpTransport | None = None,
) -> DownloadResult:
    """Stream a resource, hash it, verify optional provider checksum, publish atomically.

    Publication identity is the full SHA-256 content hash. Existing identical content
    is reused; differing content at the same path is never overwritten.
    Temporary partial files live on the destination filesystem and are cleaned up on
    every failure path. On size/checksum/write failure the stream is closed immediately
    without draining remaining body bytes.
    """
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    timeout_cfg = timeout or TimeoutConfig()
    transport_impl: HttpTransport = transport or HttpxTransport()
    dest_dir.mkdir(parents=True, exist_ok=True)

    request_url = url
    params_map = dict(params) if params else {}
    if params_map:
        query = urlencode(params_map)
        request_url = f"{url}&{query}" if "?" in url else f"{url}?{query}"

    retrieval_utc = datetime.now(timezone.utc)
    tmp_path: Path | None = None
    bytes_written = 0
    digest = hashlib.sha256()
    status_code = 0
    resp_headers: dict[str, str] = {}
    stream: StreamResponse | None = None

    try:
        try:
            stream = transport_impl.stream_get(
                request_url,
                headers=headers,
                timeout=timeout_cfg,
            )
        except DownloadError:
            raise
        except Exception as exc:
            raise DownloadError(
                f"Transport failure for {url}: {exc}",
                context={"url": url},
            ) from exc

        status_code = stream.status_code
        resp_headers = dict(stream.headers)
        if status_code < 200 or status_code >= 300:
            raise DownloadError(
                f"HTTP status {status_code} for {url}",
                context={"status_code": status_code, "url": url},
            )

        fd, tmp_name = tempfile.mkstemp(prefix=".partial-", suffix=".part", dir=dest_dir)
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "wb") as handle:
            for chunk in stream.iter_bytes:
                if not chunk:
                    continue
                offset = 0
                while offset < len(chunk):
                    take = min(chunk_size, len(chunk) - offset)
                    piece = chunk[offset : offset + take]
                    offset += take
                    next_total = bytes_written + len(piece)
                    if next_total > max_bytes:
                        # Stop immediately — do not continue reading.
                        raise SizeLimitError(
                            f"Max bytes exceeded: {max_bytes}",
                            context={
                                "max_bytes": max_bytes,
                                "bytes_written": bytes_written,
                                "url": url,
                            },
                        )
                    try:
                        handle.write(piece)
                    except OSError as exc:
                        raise DownloadError(
                            f"Write failure for {url}: {exc}",
                            context={"url": url},
                        ) from exc
                    digest.update(piece)
                    bytes_written = next_total
            handle.flush()
            os.fsync(handle.fileno())

        # Successful full read — close stream deterministically.
        stream.close_response()
        stream = None

        content_hash = digest.hexdigest()

        # Provider checksum verification BEFORE publication.
        checksum_match: bool | None = None
        checksum_verified = expected_sha256 is not None
        if expected_sha256 is not None:
            checksum_match = content_hash.lower() == expected_sha256.lower().strip()
            if not checksum_match:
                raise ChecksumMismatchError(
                    f"Checksum mismatch for {url}",
                    context={
                        "expected": expected_sha256.lower().strip(),
                        "actual": content_hash,
                        "url": url,
                    },
                )

        final_path = content_addressed_path(dest_dir, content_hash)
        reused = False

        if final_path.exists():
            existing_hash = compute_sha256(final_path, chunk_size=chunk_size)
            if existing_hash.lower() != content_hash.lower():
                raise DownloadError(
                    "Content-addressed path exists with different content",
                    context={
                        "path": str(final_path),
                        "existing_sha256": existing_hash,
                        "new_sha256": content_hash,
                    },
                )
            reused = True
            tmp_path.unlink(missing_ok=True)
            tmp_path = None
        else:
            created = _publish_exclusive(tmp_path, final_path)
            if created:
                # Content is at final_path; remove the hardlink source or leftover tmp.
                tmp_path.unlink(missing_ok=True)
                tmp_path = None
            else:
                # Concurrent publisher won — never overwrite; verify identity.
                existing_hash = compute_sha256(final_path, chunk_size=chunk_size)
                if existing_hash.lower() != content_hash.lower():
                    raise DownloadError(
                        "Content-addressed path exists with different content",
                        context={
                            "path": str(final_path),
                            "existing_sha256": existing_hash,
                            "new_sha256": content_hash,
                        },
                    )
                reused = True
                tmp_path.unlink(missing_ok=True)
                tmp_path = None

        return DownloadResult(
            url=url,
            params=params_map,
            retrieval_utc=retrieval_utc,
            status_code=status_code,
            response_headers=resp_headers,
            bytes_written=bytes_written if not reused else final_path.stat().st_size,
            sha256=content_hash,
            dest_path=final_path,
            reused_existing=reused,
            checksum_verified=checksum_verified,
            checksum_match=checksum_match,
            connect_timeout_s=timeout_cfg.connect_s,
            read_timeout_s=timeout_cfg.read_s,
            chunk_size=chunk_size,
            max_bytes=max_bytes,
        )
    except (DownloadError, SizeLimitError, ChecksumMismatchError):
        raise
    except Exception as exc:
        raise DownloadError(
            f"Download failed for {url}: {exc}",
            context={"url": url},
        ) from exc
    finally:
        if stream is not None:
            stream.close_response()
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@dataclass
class SyntheticTransport:
    """In-memory transport for tests (no network)."""

    body: bytes
    status_code: int = 200
    headers: Mapping[str, str] | None = None
    chunk_size: int = 64
    fail_after_bytes: int | None = None
    closed: bool = False
    bytes_yielded: int = 0

    def stream_get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        timeout: TimeoutConfig,
    ) -> StreamResponse:
        del url, headers, timeout
        body = self.body
        fail_at = self.fail_after_bytes
        size = self.chunk_size
        self.bytes_yielded = 0
        self.closed = False
        transport = self

        def _iter() -> Iterator[bytes]:
            sent = 0
            while sent < len(body):
                if transport.closed:
                    return
                if fail_at is not None and sent >= fail_at:
                    raise OSError("synthetic transport failure")
                piece = body[sent : sent + size]
                sent += len(piece)
                transport.bytes_yielded = sent
                yield piece

        def _close() -> None:
            transport.closed = True

        return StreamResponse(
            status_code=self.status_code,
            headers=dict(self.headers or {"content-type": "application/octet-stream"}),
            iter_bytes=_iter(),
            close=_close,
        )
