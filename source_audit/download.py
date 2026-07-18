"""Bounded streaming download with atomic write and audit trail."""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import tempfile
import shutil

from .errors import DownloadError, ChecksumMismatchError
from .hashing import compute_sha256, verify_checksum
from .models import DownloadResult


def atomic_download(
    url: str,
    dest_dir: Path,
    params: Optional[Dict[str, Any]] = None,
    max_bytes: int = 100 * 1024 * 1024,  # 100 MB default
    timeout: int = 300,
    checksum: Optional[str] = None,
    chunk_size: int = 8192,
) -> DownloadResult:
    """
    Stream download to temporary file, then atomically rename.
    Records full audit metadata.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    retrieval_utc = datetime.now(timezone.utc)

    # Use a temp file in the same directory for atomic rename
    with tempfile.NamedTemporaryFile(dir=dest_dir, delete=False, suffix=".partial") as tmp:
        tmp_path = Path(tmp.name)
        bytes_written = 0
        start_time = time.time()

        # NOTE: In real use, replace this stub with actual requests streaming
        # For now, this is a placeholder that simulates failure for safety
        # The integrating developer must implement the actual HTTP client here.
        raise NotImplementedError(
            "Replace this stub with real streaming HTTP client (e.g. requests or httpx). "
            "Example: use response.iter_content(chunk_size=chunk_size)"
        )

        # After successful streaming:
        # tmp.flush()
        # os.fsync(tmp.fileno())

    # Atomic rename only on success
    final_name = dest_dir / f"{hash(url) % 10**8}_{retrieval_utc.strftime('%Y%m%d%H%M%S')}.bin"
    shutil.move(str(tmp_path), str(final_name))

    sha256 = compute_sha256(final_name)

    checksum_match = None
    if checksum:
        checksum_match = verify_checksum(final_name, checksum)
        if not checksum_match:
            final_name.unlink(missing_ok=True)
            raise ChecksumMismatchError(f"Checksum mismatch for {url}")

    return DownloadResult(
        url=url,
        params=params or {},
        retrieval_utc=retrieval_utc,
        status=200,  # placeholder
        headers={},
        compressed_bytes=bytes_written,
        sha256=sha256,
        dest_path=final_name,
        checksum_verified=bool(checksum),
        checksum_match=checksum_match,
    )
