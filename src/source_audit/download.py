"""Bounded streaming HTTP download with atomic publication and full audit trail."""

import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import tempfile
import hashlib

from .errors import DownloadError, ChecksumMismatchError
from .hashing import compute_sha256
from .models import DownloadResult


def atomic_download(
    url: str,
    dest_dir: Path,
    params: Optional[Dict[str, Any]] = None,
    max_bytes: int = 100 * 1024 * 1024,
    timeout: int = 300,
    checksum: Optional[str] = None,
    chunk_size: int = 8192,
    headers: Optional[Dict[str, str]] = None,
) -> DownloadResult:
    """
    Perform bounded streaming download using stdlib urllib.
    Atomic rename only on success. Full audit metadata recorded.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    retrieval_utc = datetime.now(timezone.utc)

    # Build request
    req = urllib.request.Request(url, headers=headers or {})
    if params:
        # Simple query string append for GET
        from urllib.parse import urlencode
        query = urlencode(params)
        if "?" in url:
            req.full_url = f"{url}&{query}"
        else:
            req.full_url = f"{url}?{query}"

    tmp_path: Optional[Path] = None
    bytes_written = 0
    sha256_hash = hashlib.sha256()

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.getcode()
            resp_headers = dict(response.getheaders())

            # Create temp file in destination dir
            with tempfile.NamedTemporaryFile(
                dir=dest_dir, delete=False, suffix=".partial"
            ) as tmp:
                tmp_path = Path(tmp.name)

                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise DownloadError(f"Max bytes exceeded: {max_bytes}")
                    tmp.write(chunk)
                    sha256_hash.update(chunk)

                tmp.flush()
                os.fsync(tmp.fileno())

            # Atomic rename
            content_hash = sha256_hash.hexdigest()
            final_name = dest_dir / f"{content_hash[:16]}_{retrieval_utc.strftime('%Y%m%d%H%M%S')}.bin"

            # Do not overwrite if different content exists
            if final_name.exists():
                existing_hash = compute_sha256(final_name)
                if existing_hash != content_hash:
                    raise DownloadError("Existing object with different content")

            os.replace(str(tmp_path), str(final_name))
            tmp_path = None  # Prevent cleanup

            # Checksum verification
            checksum_match = None
            if checksum:
                checksum_match = (content_hash.lower() == checksum.lower())
                if not checksum_match:
                    final_name.unlink(missing_ok=True)
                    raise ChecksumMismatchError(f"Checksum mismatch for {url}")

            return DownloadResult(
                url=url,
                params=params or {},
                retrieval_utc=retrieval_utc,
                status=status,
                headers=resp_headers,
                compressed_bytes=bytes_written,
                sha256=content_hash,
                dest_path=final_name,
                checksum_verified=bool(checksum),
                checksum_match=checksum_match,
            )

    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        raise DownloadError(f"HTTP error for {url}: {e}") from e
    except Exception as e:
        raise DownloadError(f"Download failed for {url}: {e}") from e
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
