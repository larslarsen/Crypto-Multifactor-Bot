"""ZIP and CSV inspection with safety limits."""

import zipfile
from pathlib import Path
from .errors import UnsafeArchiveError
from .models import ZipAuditResult, ZipMemberInfo, CSVAuditResult


def audit_zip_safe(zip_path: Path, max_members: int = 1000) -> ZipAuditResult:
    """Inspect ZIP with safety checks (no full extraction)."""
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
            if ".." in name or name.startswith("/"):
                unsafe.append(name)
            members.append(ZipMemberInfo(
                name=name,
                compressed_size=info.compress_size,
                file_size=info.file_size,
                is_unsafe=".." in name or name.startswith("/")
            ))
            total_comp += info.compress_size
            total_size += info.file_size

    return ZipAuditResult(
        members=members,
        member_count=len(members),
        total_compressed=total_comp,
        total_extracted=total_size,
        unsafe_paths=unsafe,
    )


def audit_csv_safe(csv_path: Path, max_rows: int = 10000) -> CSVAuditResult:
    """Inspect CSV header and sample rows."""
    # Placeholder - full CSV parsing with limits
    return CSVAuditResult(
        headers=[],
        row_count=0,
        first_rows=[],
        last_rows=[],
        malformed_rows=0,
        duplicate_keys=0,
        ordering_violations=0,
    )
