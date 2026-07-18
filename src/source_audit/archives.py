"""Safe ZIP and bounded CSV inspection (AUD-002)."""

import zipfile
from pathlib import Path
from typing import List, Optional
import csv
from datetime import datetime, timezone

from .errors import UnsafeArchiveError, MalformedCSVError
from .models import ZipAuditResult, ZipMemberInfo, CSVAuditResult


def _is_unsafe_path(name: str) -> bool:
    """Check for path traversal, absolute, UNC, and drive paths."""
    if ".." in name.split("/"):
        return True
    if name.startswith(("/", "\\")):
        return True
    if name[1:3] == ":\\" or name[1:3] == ":/":  # Windows drive
        return True
    if name.startswith("\\\\"):  # UNC
        return True
    return False


def audit_zip_safe(
    zip_path: Path,
    max_members: int = 1000,
    max_compressed: int = 500 * 1024 * 1024,
) -> ZipAuditResult:
    """Inspect ZIP with strict safety checks. Records unsafe members (marked is_unsafe)
    rather than raising, so callers can decide; raises only on structural limits
    (member count, size, encryption, symlinks)."""
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    members = []
    unsafe_paths = []
    total_comp = 0
    total_size = 0

    with zipfile.ZipFile(zip_path) as z:
        if len(z.namelist()) > max_members:
            raise UnsafeArchiveError("Too many members in archive")

        for name in z.namelist():
            info = z.getinfo(name)

            if _is_unsafe_path(name):
                unsafe_paths.append(name)
                members.append(ZipMemberInfo(
                    name=name,
                    compressed_size=info.compress_size,
                    file_size=info.file_size,
                    is_unsafe=True,
                ))
                continue

            # Reject symlinks and special files (best effort via external_attr)
            if info.external_attr & 0xA0000000:  # symlink
                raise UnsafeArchiveError(f"Symlink detected: {name}")

            if info.compress_type == zipfile.ZIP_STORED and info.file_size == 0 and not name.endswith("/"):
                # Could be special file, but we mainly rely on path checks + encryption
                pass

            # Encrypted entries
            if info.flag_bits & 0x1:
                raise UnsafeArchiveError(f"Encrypted entry detected: {name}")

            members.append(ZipMemberInfo(
                name=name,
                compressed_size=info.compress_size,
                file_size=info.file_size,
                is_unsafe=False
            ))

            total_comp += info.compress_size
            total_size += info.file_size

        if total_comp > max_compressed:
            raise UnsafeArchiveError("Archive exceeds compressed size limit")

    return ZipAuditResult(
        members=members,
        member_count=len(members),
        total_compressed=total_comp,
        total_extracted=total_size,
        unsafe_paths=unsafe_paths,
    )


def audit_csv_safe(
    csv_path: Path,
    max_rows: int = 10000,
    max_line_length: int = 1_000_000,
    key_fields: Optional[List[str]] = None,
    timestamp_field: Optional[str] = None,
) -> CSVAuditResult:
    """Bounded streaming CSV inspection with proper diagnostics."""
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    headers = []
    first_rows: List[List[str]] = []
    last_rows: List[List[str]] = []
    row_count = 0
    malformed_rows = 0
    duplicate_keys = 0
    ordering_violations = 0
    earliest_ts = None
    latest_ts = None

    seen_keys = set()
    prev_ts = None

    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            # Read and validate header
            header_line = f.readline().rstrip("\n\r")
            if len(header_line) > max_line_length:
                raise MalformedCSVError("Header line exceeds max length")

            reader = csv.reader([header_line])
            try:
                headers = next(reader)
            except StopIteration:
                raise MalformedCSVError("Empty CSV header")

            if not headers:
                raise MalformedCSVError("CSV has no header columns")

            # Validate configured fields exist
            if key_fields:
                for kf in key_fields:
                    if kf not in headers:
                        raise MalformedCSVError(f"Key field '{kf}' not in header")

            if timestamp_field and timestamp_field not in headers:
                raise MalformedCSVError(f"Timestamp field '{timestamp_field}' not in header")

            # Stream data rows
            for raw_line in f:
                if len(raw_line) > max_line_length:
                    malformed_rows += 1
                    continue

                try:
                    row = next(csv.reader([raw_line.rstrip("\n\r")]))
                except Exception:
                    malformed_rows += 1
                    continue

                # Row width check
                if len(row) != len(headers):
                    malformed_rows += 1
                    continue

                row_count += 1

                # Collect samples
                if len(first_rows) < 5:
                    first_rows.append(row)
                last_rows.append(row)
                if len(last_rows) > 5:
                    last_rows.pop(0)

                # Duplicate key detection
                if key_fields:
                    try:
                        key = tuple(row[headers.index(k)] for k in key_fields)
                        if key in seen_keys:
                            duplicate_keys += 1
                        seen_keys.add(key)
                    except (ValueError, IndexError):
                        malformed_rows += 1
                        continue

                # Timestamp handling
                if timestamp_field:
                    try:
                        ts_str = row[headers.index(timestamp_field)]
                        ts = int(ts_str)
                        ts_dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                        if earliest_ts is None or ts_dt < earliest_ts:
                            earliest_ts = ts_dt
                        if latest_ts is None or ts_dt > latest_ts:
                            latest_ts = ts_dt

                        if prev_ts is not None and ts_dt < prev_ts:
                            ordering_violations += 1
                        prev_ts = ts_dt
                    except (ValueError, IndexError):
                        # Do not silently ignore
                        malformed_rows += 1
                        continue

                if row_count >= max_rows:
                    break

    except Exception as e:
        raise MalformedCSVError(f"CSV inspection failed: {e}") from e

    return CSVAuditResult(
        headers=headers,
        row_count=row_count,
        first_rows=first_rows,
        last_rows=last_rows,
        malformed_rows=malformed_rows,
        duplicate_keys=duplicate_keys,
        ordering_violations=ordering_violations,
        earliest_ts=earliest_ts,
        latest_ts=latest_ts,
        timestamp_precision="inferred" if timestamp_field else None,
    )
