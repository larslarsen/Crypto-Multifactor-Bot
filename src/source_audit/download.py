"""Bounded streaming HTTP acquisition with atomic content-addressed publication."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class StreamResponse:
    """Transport-level streaming response."""

    status_code: int
    headers: Mapping[str, str]
    iter_bytes: Iterator[bytes]


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
        # Materialize the response body stream under a held client context by
        # reading chunks into a generator that owns the client lifecycle.
        client = httpx.Client(timeout=timeout_cfg, follow_redirects=True)
        try:
            request = client.build_request("GET", url, headers=dict(headers or {}))
            response = client.send(request, stream=True)
            status = response.status_code
            resp_headers = {k: v for k, v in response.headers.items()}

            def _chunks() -> Iterator[bytes]:
                try:
                    yield from response.iter_bytes()
                finally:
                    response.close()
                    client.close()

            return StreamResponse(
                status_code=status,
                headers=resp_headers,
                iter_bytes=_chunks(),
            )
        except Exception:
            client.close()
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
    every failure path.
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
        try:
            with os.fdopen(fd, "wb") as handle:
                for chunk in stream.iter_bytes:
                    if not chunk:
                        continue
                    # Stream in transport chunks; enforce max_bytes.
                    offset = 0
                    while offset < len(chunk):
                        take = min(chunk_size, len(chunk) - offset)
                        piece = chunk[offset : offset + take]
                        offset += take
                        bytes_written += len(piece)
                        if bytes_written > max_bytes:
                            raise SizeLimitError(
                                f"Max bytes exceeded: {max_bytes}",
                                context={
                                    "max_bytes": max_bytes,
                                    "bytes_written": bytes_written,
                                    "url": url,
                                },
                            )
                        handle.write(piece)
                        digest.update(piece)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            # Ensure iterator resources are exhausted/closed if possible.
            try:
                for _ in stream.iter_bytes:
                    pass
            except Exception:
                pass
            raise

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
            # Identical content: reuse, drop partial.
            reused = True
            tmp_path.unlink(missing_ok=True)
            tmp_path = None
        else:
            # Atomic publish via os.replace on the same filesystem.
            os.replace(str(tmp_path), str(final_path))
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

    def stream_get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        timeout: TimeoutConfig,
    ) -> StreamResponse:
        del url, headers, timeout  # unused; synthetic

        body = self.body
        fail_at = self.fail_after_bytes
        size = self.chunk_size

        def _iter() -> Iterator[bytes]:
            sent = 0
            while sent < len(body):
                if fail_at is not None and sent >= fail_at:
                    raise OSError("synthetic transport failure")
                piece = body[sent : sent + size]
                sent += len(piece)
                yield piece

        return StreamResponse(
            status_code=self.status_code,
            headers=dict(self.headers or {"content-type": "application/octet-stream"}),
            iter_bytes=_iter(),
        )
