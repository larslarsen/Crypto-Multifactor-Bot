"""Safe ZIP and bounded CSV inspection (AUD-002 strict)."""

import zipfile
from pathlib import Path
from typing import List, Optional, Set, Tuple, Any
import csv
from datetime import datetime, timezone
from decimal import Decimal

from .errors import UnsafeArchiveError, MalformedCSVError
from .models import ZipAuditResult, ZipMemberInfo, CSVAuditResult


def _is_unsafe_path(name: str) -> bool:
    """Component-based validation (prices..backup.csv is valid)."""
    normalized = name.replace("\\", "/").strip()
    parts = [p for p in normalized.split("/") if p]
    if any(p in ("..", ".", "") for p in parts):
        return True
    if normalized.startswith(("/", "\\", "//")):
        return True
    if len(normalized) > 1 and normalized[1] == ":":
        return True
    return False


def audit_zip_safe(
    zip_path: Path,
    max_members: int = 1000,
    max_compressed_per_member: int = 100 * 1024 * 1024,
    max_total_compressed: int = 500 * 1024 * 1024,
    max_extracted_per_member: int = 500 * 1024 * 1024,
    max_total_extracted: int = 2 * 1024 * 1024 * 1024,
    max_ratio: float = 100.0,
) -> ZipAuditResult:
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    members: List[ZipMemberInfo] = []
    seen: Set[str] = set()
    total_comp = 0
    total_ex = 0

    with zipfile.ZipFile(zip_path) as z:
        namelist = z.namelist()
        if len(namelist) > max_members:
            raise UnsafeArchiveError(f"Too many members: {len(namelist)} > {max_members}")

        for name in namelist:
            if name in seen:
                raise UnsafeArchiveError(f"Duplicate member: {name}")
            seen.add(name)

            info = z.getinfo(name)

            if _is_unsafe_path(name):
                raise UnsafeArchiveError(f"Unsafe path: {name}")

            mode = info.external_attr >> 16
            if mode and (mode & 0o170000) == 0o120000:
                raise UnsafeArchiveError(f"Symlink: {name}")
            if mode and (mode & 0o170000) not in (0o100000, 0o040000):
                raise UnsafeArchiveError(f"Special file: {name}")

            if info.flag_bits & 0x1:
                raise UnsafeArchiveError(f"Encrypted member: {name}")

            if info.compress_size > max_compressed_per_member:
                raise UnsafeArchiveError(f"Compressed size exceed per member: {name}")
            if info.file_size > max_extracted_per_member:
                raise UnsafeArchiveError(f"Extracted size exceed per member: {name}")

            ratio = info.file_size / info.compress_size if info.compress_size > 0 else 1.0
            if ratio > max_ratio:
                raise UnsafeArchiveError(f"Compression ratio violation: {name} ({ratio:.1f})")

            members.append(ZipMemberInfo(name, info.compress_size, info.file_size))
            total_comp += info.compress_size
            total_ex += info.file_size

        if total_comp > max_total_compressed:
            raise UnsafeArchiveError("Total compressed size limit exceeded")
        if total_ex > max_total_extracted:
            raise UnsafeArchiveError("Total extracted size limit exceeded")

    return ZipAuditResult(members, len(members), total_comp, total_ex, [])


def audit_csv_safe(
    csv_path: Path,
    max_rows: int = 10000,
    max_physical_line: int = 1_000_000,
    max_logical_record: int = 10_000_000,
    key_fields: Optional[List[str]] = None,
    timestamp_field: Optional[str] = None,
) -> CSVAuditResult:
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    headers: List[str] = []
    first_rows: List[List[str]] = []
    last_rows: List[List[str]] = []
    row_count = 0
    malformed_rows = 0
    duplicate_keys = 0
    ordering_violations = 0
    earliest_ts = None
    latest_ts = None

    seen_keys: Set[Tuple[Any, ...]] = set()
    prev_ts = None

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        header_line = f.readline()
        if len(header_line) > max_physical_line:
            raise MalformedCSVError("Header too long")

        headers = next(csv.reader([header_line]), [])
        if not headers:
            raise MalformedCSVError("No header")

        if key_fields:
            for k in key_fields:
                if k not in headers:
                    raise MalformedCSVError(f"Missing key field: {k}")
        if timestamp_field and timestamp_field not in headers:
            raise MalformedCSVError(f"Missing timestamp field: {timestamp_field}")

        for row in csv.reader(f):
            if len(str(row)) > max_logical_record:
                malformed_rows += 1
                continue

            row_count += 1
            if len(first_rows) < 5:
                first_rows.append(row)
            last_rows.append(row)
            if len(last_rows) > 5:
                last_rows.pop(0)

            if key_fields:
                try:
                    key = tuple(row[headers.index(k)] for k in key_fields)
                    if key in seen_keys:
                        duplicate_keys += 1
                    seen_keys.add(key)
                except Exception:
                    malformed_rows += 1
                    continue

            if timestamp_field:
                try:
                    ts_str = row[headers.index(timestamp_field)]
                    if '.' in ts_str:
                        ts = int(Decimal(ts_str))
                    else:
                        ts = int(ts_str)
                    ts_dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)

                    if earliest_ts is None or ts_dt < earliest_ts:
                        earliest_ts = ts_dt
                    if latest_ts is None or ts_dt > latest_ts:
                        latest_ts = ts_dt
                    if prev_ts is not None and ts_dt < prev_ts:
                        ordering_violations += 1
                    prev_ts = ts_dt
                except Exception:
                    malformed_rows += 1
                    continue

            if row_count >= max_rows:
                break

    return CSVAuditResult(
        headers, row_count, first_rows, last_rows,
        malformed_rows, duplicate_keys, ordering_violations,
        earliest_ts, latest_ts, "mixed" if timestamp_field else None
    )
