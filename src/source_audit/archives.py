"""Safe ZIP and bounded CSV inspection (AUD-002)."""

import zipfile
from pathlib import Path
from typing import List, Optional
import csv
import io

from .errors import UnsafeArchiveError, MalformedCSVError
from .models import ZipAuditResult, ZipMemberInfo, CSVAuditResult


def audit_zip_safe(zip_path: Path, max_members: int = 1000, max_compressed: int = 500 * 1024 * 1024) -> ZipAuditResult:
    """Inspect ZIP with strict safety checks. No extraction."""
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    members = []
    unsafe = []
    total_comp = 0
    total_size = 0

    with zipfile.ZipFile(zip_path) as z:
        if len(z.namelist()) > max_members:
            raise UnsafeArchiveError("Too many members in archive")

        for name in z.namelist():
            info = z.getinfo(name)

            is_unsafe = False
            reasons = []

            if ".." in name or name.startswith(("/", "\\")):
                is_unsafe = True
                reasons.append("traversal/absolute")

            if name.endswith(("/", "\\")) and not info.is_dir():
                is_unsafe = True
                reasons.append("special file")

            # Check for encrypted entries
            if info.flag_bits & 0x1:
                is_unsafe = True
                reasons.append("encrypted")

            members.append(ZipMemberInfo(
                name=name,
                compressed_size=info.compress_size,
                file_size=info.file_size,
                is_unsafe=is_unsafe
            ))

            total_comp += info.compress_size
            total_size += info.file_size

            if is_unsafe:
                unsafe.append(name)

        if total_comp > max_compressed:
            raise UnsafeArchiveError("Archive exceeds compressed size limit")

    return ZipAuditResult(
        members=members,
        member_count=len(members),
        total_compressed=total_comp,
        total_extracted=total_size,
        unsafe_paths=unsafe,
    )


def audit_csv_safe(
    csv_path: Path,
    max_rows: int = 10000,
    max_line_length: int = 1_000_000,
    key_fields: Optional[List[str]] = None,
    timestamp_field: Optional[str] = None,
) -> CSVAuditResult:
    """Bounded CSV inspection with schema and quality diagnostics."""
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    headers = []
    first_rows = []
    last_rows = []
    row_count = 0
    malformed = 0
    duplicates = 0
    ordering_violations = 0

    seen_keys = set()
    prev_ts = None

    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            # Read header
            header_line = f.readline()
            if len(header_line) > max_line_length:
                raise MalformedCSVError("Header line too long")

            reader = csv.reader(io.StringIO(header_line))
            headers = next(reader, [])

            if not headers:
                raise MalformedCSVError("Empty header")

            for line_num, row in enumerate(reader, start=2):
                if len(str(row)) > max_line_length:
                    malformed += 1
                    continue

                row_count += 1
                if row_count <= 5:
                    first_rows.append(row)
                if row_count > max_rows - 5:
                    last_rows.append(row)

                # Duplicate key check
                if key_fields:
                    key = tuple(row[headers.index(k)] for k in key_fields if k in headers)
                    if key in seen_keys:
                        duplicates += 1
                    seen_keys.add(key)

                # Timestamp ordering check
                if timestamp_field and timestamp_field in headers:
                    try:
                        idx = headers.index(timestamp_field)
                        ts = int(row[idx])
                        if prev_ts is not None and ts < prev_ts:
                            ordering_violations += 1
                        prev_ts = ts
                    except (ValueError, IndexError):
                        pass

                if row_count >= max_rows:
                    break

    except Exception as e:
        raise MalformedCSVError(f"CSV parsing failed: {e}") from e

    return CSVAuditResult(
        headers=headers,
        row_count=row_count,
        first_rows=first_rows,
        last_rows=last_rows[-5:] if last_rows else [],
        malformed_rows=malformed,
        duplicate_keys=duplicates,
        ordering_violations=ordering_violations,
    )
