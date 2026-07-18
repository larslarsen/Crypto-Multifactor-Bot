"""Safe ZIP inspection and bounded streaming CSV inspection.

ZIP members are never extracted to disk. Path safety uses normalized path-component
validation (not substring matching), so names such as ``prices..backup.csv`` are
allowed while ``../evil`` is rejected.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections import deque
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from .errors import (
    AmbiguousTimestampError,
    MalformedCSVError,
    OutOfRangeTimestampError,
    UnsafeArchiveError,
)
from .models import (
    CSVAuditResult,
    MalformedRowReport,
    TimestampUnit,
    ZipAuditResult,
    ZipMemberInfo,
)
from .timestamps import infer_timestamp_unit

# ZIP external_attr Unix mode bits (upper 16 bits).
_S_IFMT = 0o170000
_S_IFREG = 0o100000
_S_IFDIR = 0o040000
_S_IFLNK = 0o120000


def _normalized_components(name: str) -> list[str]:
    """Split a ZIP member name into normalized path components."""
    # ZIP uses forward slashes; tolerate backslashes from non-POSIX producers.
    normalized = name.replace("\\", "/")
    return [part for part in normalized.split("/") if part != ""]


def is_unsafe_zip_member_name(name: str) -> bool:
    """Return True when a ZIP member name is unsafe by component rules.

    Rejects:
    - absolute POSIX paths (leading ``/``)
    - UNC paths (leading ``//`` or ``\\\\``)
    - Windows drive paths (``C:...``)
    - traversal components (``.`` or ``..`` as a whole component)

    Allows harmless names containing ``..`` inside a component, e.g.
    ``prices..backup.csv``.
    """
    if name is None:
        return True
    raw = name.replace("\\", "/")

    # Absolute POSIX.
    if raw.startswith("/"):
        return True
    # UNC (//server/share or after backslash normalization).
    if raw.startswith("//"):
        return True
    # Windows drive path: "C:foo" or "C:/foo"
    if len(raw) >= 2 and raw[1] == ":" and raw[0].isalpha():
        return True

    components = _normalized_components(name)
    for part in components:
        if part in (".", ".."):
            return True
    return False


def audit_zip_safe(
    zip_path: Path,
    *,
    max_members: int = 1000,
    max_compressed_per_member: int = 100 * 1024 * 1024,
    max_total_compressed: int = 500 * 1024 * 1024,
    max_extracted_per_member: int = 500 * 1024 * 1024,
    max_total_extracted: int = 2 * 1024 * 1024 * 1024,
    max_ratio: float = 100.0,
) -> ZipAuditResult:
    """Inspect a ZIP archive without extracting contents to disk.

    Raises :class:`UnsafeArchiveError` immediately on any safety violation.
    """
    if max_members <= 0:
        raise ValueError("max_members must be positive")
    if max_ratio <= 0:
        raise ValueError("max_ratio must be positive")

    path = Path(zip_path)
    if not path.exists():
        raise FileNotFoundError(path)

    members: list[ZipMemberInfo] = []
    seen_names: set[str] = set()
    total_comp = 0
    total_ex = 0
    max_ratio_observed = 0.0

    try:
        zf = zipfile.ZipFile(path, "r")
    except zipfile.BadZipFile as exc:
        raise UnsafeArchiveError(
            f"Not a valid ZIP archive: {path}",
            context={"path": str(path)},
        ) from exc

    with zf:
        names = zf.namelist()
        if len(names) > max_members:
            raise UnsafeArchiveError(
                f"Member count {len(names)} exceeds max_members={max_members}",
                context={"member_count": len(names), "max_members": max_members},
            )

        for name in names:
            if name in seen_names:
                raise UnsafeArchiveError(
                    f"Duplicate member name: {name}",
                    context={"name": name},
                )
            seen_names.add(name)

            if is_unsafe_zip_member_name(name):
                raise UnsafeArchiveError(
                    f"Unsafe path: {name}",
                    context={"name": name},
                )

            info = zf.getinfo(name)

            # Encrypted members.
            if info.flag_bits & 0x1:
                raise UnsafeArchiveError(
                    f"Encrypted member: {name}",
                    context={"name": name},
                )

            mode = (info.external_attr >> 16) & 0xFFFF
            file_type = mode & _S_IFMT if mode else 0
            is_dir = name.endswith("/") or file_type == _S_IFDIR

            if file_type == _S_IFLNK:
                raise UnsafeArchiveError(
                    f"Symlink member: {name}",
                    context={"name": name},
                )
            if mode and file_type not in (0, _S_IFREG, _S_IFDIR):
                # Non-zero special type that is not regular or directory.
                raise UnsafeArchiveError(
                    f"Special file member: {name}",
                    context={"name": name, "mode": oct(mode)},
                )

            if info.compress_size > max_compressed_per_member:
                raise UnsafeArchiveError(
                    f"Compressed size exceeds per-member limit: {name}",
                    context={
                        "name": name,
                        "compress_size": info.compress_size,
                        "max": max_compressed_per_member,
                    },
                )
            if info.file_size > max_extracted_per_member:
                raise UnsafeArchiveError(
                    f"Extracted size exceeds per-member limit: {name}",
                    context={
                        "name": name,
                        "file_size": info.file_size,
                        "max": max_extracted_per_member,
                    },
                )

            # Compression ratio. Zero-byte compressed with positive file size is
            # treated conservatively as an infinite ratio → reject when file_size > 0.
            if info.compress_size == 0:
                if info.file_size > 0 and not is_dir:
                    raise UnsafeArchiveError(
                        f"Zero-byte compressed member with positive size: {name}",
                        context={
                            "name": name,
                            "compress_size": info.compress_size,
                            "file_size": info.file_size,
                        },
                    )
                ratio = 1.0
            else:
                ratio = info.file_size / info.compress_size
            if ratio > max_ratio:
                raise UnsafeArchiveError(
                    f"Compression ratio {ratio:.2f} exceeds max_ratio={max_ratio}: {name}",
                    context={
                        "name": name,
                        "ratio": ratio,
                        "max_ratio": max_ratio,
                    },
                )
            if ratio > max_ratio_observed:
                max_ratio_observed = ratio

            total_comp += info.compress_size
            total_ex += info.file_size
            if total_comp > max_total_compressed:
                raise UnsafeArchiveError(
                    "Total compressed size limit exceeded",
                    context={
                        "total_compressed": total_comp,
                        "max_total_compressed": max_total_compressed,
                    },
                )
            if total_ex > max_total_extracted:
                raise UnsafeArchiveError(
                    "Total extracted size limit exceeded",
                    context={
                        "total_extracted": total_ex,
                        "max_total_extracted": max_total_extracted,
                    },
                )

            members.append(
                ZipMemberInfo(
                    name=name,
                    compressed_size=info.compress_size,
                    file_size=info.file_size,
                    is_directory=is_dir,
                    compress_type=info.compress_type,
                    flag_bits=info.flag_bits,
                )
            )

    return ZipAuditResult(
        members=tuple(members),
        member_count=len(members),
        total_compressed=total_comp,
        total_extracted=total_ex,
        max_ratio_observed=max_ratio_observed,
    )


def _logical_record_length(fields: Sequence[str]) -> int:
    """Exact logical-record character length without ``len(str(row))``.

    Counts field characters plus one separator between fields (delimiter placeholder).
    """
    if not fields:
        return 0
    return sum(len(f) for f in fields) + (len(fields) - 1)


def _validate_headers(headers: list[str]) -> tuple[str, ...]:
    if not headers:
        raise MalformedCSVError("Missing header row")
    cleaned = [h.strip() for h in headers]
    if any(h == "" for h in cleaned):
        raise MalformedCSVError(
            "Empty header field",
            context={"headers": cleaned},
        )
    if len(set(cleaned)) != len(cleaned):
        raise MalformedCSVError(
            "Duplicate header fields",
            context={"headers": cleaned},
        )
    return tuple(cleaned)


class _PhysicalLineLimitedReader(io.TextIOBase):
    """Text stream wrapper that rejects physical lines longer than a limit.

    A physical line is terminated by ``\\n`` (or EOF). Quoted multiline CSV fields
    span multiple physical lines; each physical line is bounded independently.
    """

    def __init__(self, base: io.TextIOBase, max_physical_line: int) -> None:
        super().__init__()
        self._base = base
        self._max_physical_line = max_physical_line
        self._buffer = ""

    def readable(self) -> bool:
        return True

    def read(self, size: int | None = -1) -> str:
        if size is None or size < 0:
            chunks: list[str] = []
            while True:
                line = self.readline()
                if not line:
                    break
                chunks.append(line)
            return "".join(chunks)
        # Read up to size characters, still enforcing per-line limits via readline.
        out: list[str] = []
        remaining = size
        while remaining > 0:
            line = self.readline()
            if not line:
                break
            if len(line) <= remaining:
                out.append(line)
                remaining -= len(line)
            else:
                # Put back overflow into buffer — csv rarely uses bounded read.
                out.append(line[:remaining])
                self._buffer = line[remaining:] + self._buffer
                remaining = 0
        return "".join(out)

    def readline(self, size: int | None = -1) -> str:  # type: ignore[override]
        del size
        if self._buffer:
            # Prefer buffered content first.
            nl = self._buffer.find("\n")
            if nl >= 0:
                line = self._buffer[: nl + 1]
                self._buffer = self._buffer[nl + 1 :]
                if len(line.rstrip("\r\n")) > self._max_physical_line:
                    raise MalformedCSVError(
                        "Physical line exceeds max_physical_line",
                        context={
                            "length": len(line.rstrip("\r\n")),
                            "max_physical_line": self._max_physical_line,
                        },
                    )
                return line
            # No newline in buffer — append more.
            more = self._base.readline()
            combined = self._buffer + more
            self._buffer = ""
            if not combined:
                return ""
            if "\n" not in combined and len(combined.rstrip("\r\n")) > self._max_physical_line:
                raise MalformedCSVError(
                    "Physical line exceeds max_physical_line",
                    context={
                        "length": len(combined.rstrip("\r\n")),
                        "max_physical_line": self._max_physical_line,
                    },
                )
            if "\n" not in combined:
                if len(combined.rstrip("\r\n")) > self._max_physical_line:
                    raise MalformedCSVError(
                        "Physical line exceeds max_physical_line",
                        context={
                            "length": len(combined.rstrip("\r\n")),
                            "max_physical_line": self._max_physical_line,
                        },
                    )
                return combined
            nl = combined.find("\n")
            line = combined[: nl + 1]
            self._buffer = combined[nl + 1 :]
            if len(line.rstrip("\r\n")) > self._max_physical_line:
                raise MalformedCSVError(
                    "Physical line exceeds max_physical_line",
                    context={
                        "length": len(line.rstrip("\r\n")),
                        "max_physical_line": self._max_physical_line,
                    },
                )
            return line

        line = self._base.readline()
        if not line:
            return ""
        if len(line.rstrip("\r\n")) > self._max_physical_line:
            raise MalformedCSVError(
                "Physical line exceeds max_physical_line",
                context={
                    "length": len(line.rstrip("\r\n")),
                    "max_physical_line": self._max_physical_line,
                },
            )
        return line


def audit_csv_safe(
    csv_path: Path,
    *,
    encoding: str,
    delimiter: str = ",",
    max_rows: int = 10_000,
    max_physical_line: int = 1_000_000,
    max_logical_record: int = 10_000_000,
    sample_size: int = 5,
    key_fields: Sequence[str] | None = None,
    order_fields: Sequence[str] | None = None,
    timestamp_field: str | None = None,
    timestamp_min_utc: datetime | None = None,
    timestamp_max_utc: datetime | None = None,
    has_header: bool = True,
) -> CSVAuditResult:
    """Bounded streaming CSV inspection with explicit encoding and structured diagnostics.

    Does not assume millisecond timestamps. Timestamp parsing uses
    :func:`source_audit.timestamps.infer_timestamp_unit` when bounds are provided.
    """
    if not encoding:
        raise ValueError("encoding must be explicitly selected by the caller")
    if max_rows <= 0:
        raise ValueError("max_rows must be positive")
    if max_physical_line <= 0 or max_logical_record <= 0:
        raise ValueError("length limits must be positive")
    if sample_size < 0:
        raise ValueError("sample_size must be non-negative")
    if not has_header:
        raise MalformedCSVError(
            "Headerless CSV is not supported by audit_csv_safe; provide has_header=True"
        )

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(path)

    first_samples: list[tuple[str, ...]] = []
    last_samples: deque[tuple[str, ...]] = deque(maxlen=sample_size if sample_size > 0 else 1)
    malformed_reports: list[MalformedRowReport] = []

    logical_data_records = 0
    valid_records = 0
    malformed_records = 0
    skipped_records = 0
    truncated = False
    duplicate_key_count = 0
    ordering_violation_count = 0
    timestamp_parse_failures = 0
    observed_units: set[str] = set()
    earliest_ts: datetime | None = None
    latest_ts: datetime | None = None

    seen_keys: set[tuple[str, ...]] = set()
    prev_order_key: tuple[str, ...] | None = None

    with path.open("r", encoding=encoding, newline="") as raw:
        limited = _PhysicalLineLimitedReader(raw, max_physical_line)
        reader = csv.reader(limited, delimiter=delimiter, quotechar='"')

        try:
            header_row = next(reader)
        except StopIteration as exc:
            raise MalformedCSVError("CSV is empty; missing header") from exc
        except MalformedCSVError:
            raise
        except UnicodeError as exc:
            raise MalformedCSVError(
                f"Encoding failure with encoding={encoding!r}",
                context={"encoding": encoding},
            ) from exc

        headers = _validate_headers(header_row)
        header_index = {name: idx for idx, name in enumerate(headers)}
        expected_width = len(headers)

        def _require_fields(label: str, fields: Sequence[str] | None) -> tuple[str, ...]:
            if not fields:
                return ()
            missing = [f for f in fields if f not in header_index]
            if missing:
                raise MalformedCSVError(
                    f"Configured {label} not present in headers",
                    context={"missing": missing, "headers": list(headers)},
                )
            return tuple(fields)

        keys = _require_fields("key_fields", key_fields)
        orders = _require_fields("order_fields", order_fields)
        if timestamp_field is not None:
            if timestamp_field not in header_index:
                raise MalformedCSVError(
                    "Configured timestamp_field not present in headers",
                    context={
                        "timestamp_field": timestamp_field,
                        "headers": list(headers),
                    },
                )
            if timestamp_min_utc is None or timestamp_max_utc is None:
                raise MalformedCSVError(
                    "timestamp_min_utc and timestamp_max_utc are required when "
                    "timestamp_field is set"
                )

        for row in reader:
            # row is one logical record (csv module handles quoted multiline).
            logical_data_records += 1
            if logical_data_records > max_rows:
                truncated = True
                logical_data_records -= 1
                skipped_records += 1
                break

            rec_len = _logical_record_length(row)
            if rec_len > max_logical_record:
                malformed_records += 1
                malformed_reports.append(
                    MalformedRowReport(
                        logical_row_number=logical_data_records,
                        reason="logical_record_too_long",
                        field_count=len(row),
                        expected_field_count=expected_width,
                    )
                )
                continue

            if len(row) != expected_width:
                malformed_records += 1
                malformed_reports.append(
                    MalformedRowReport(
                        logical_row_number=logical_data_records,
                        reason="width_mismatch",
                        field_count=len(row),
                        expected_field_count=expected_width,
                    )
                )
                continue

            sample = tuple(row)
            if sample_size > 0 and len(first_samples) < sample_size:
                first_samples.append(sample)
            if sample_size > 0:
                last_samples.append(sample)

            row_valid = True

            if keys:
                try:
                    key = tuple(row[header_index[k]] for k in keys)
                except IndexError:
                    malformed_records += 1
                    malformed_reports.append(
                        MalformedRowReport(
                            logical_row_number=logical_data_records,
                            reason="key_field_index_error",
                            field_count=len(row),
                            expected_field_count=expected_width,
                        )
                    )
                    continue
                if key in seen_keys:
                    duplicate_key_count += 1
                else:
                    seen_keys.add(key)

            if orders:
                order_key = tuple(row[header_index[k]] for k in orders)
                if prev_order_key is not None and order_key < prev_order_key:
                    ordering_violation_count += 1
                prev_order_key = order_key

            if timestamp_field is not None:
                raw_ts = row[header_index[timestamp_field]]
                try:
                    assert timestamp_min_utc is not None
                    assert timestamp_max_utc is not None
                    inference = infer_timestamp_unit(
                        raw_ts,
                        min_utc=timestamp_min_utc,
                        max_utc=timestamp_max_utc,
                    )
                    unit_value = (
                        inference.unit.value
                        if isinstance(inference.unit, TimestampUnit)
                        else str(inference.unit)
                    )
                    observed_units.add(unit_value)
                    ts = inference.datetime_utc
                    if earliest_ts is None or ts < earliest_ts:
                        earliest_ts = ts
                    if latest_ts is None or ts > latest_ts:
                        latest_ts = ts
                except (
                    AmbiguousTimestampError,
                    OutOfRangeTimestampError,
                    MalformedCSVError,
                ):
                    timestamp_parse_failures += 1
                    row_valid = False
                    malformed_records += 1
                    malformed_reports.append(
                        MalformedRowReport(
                            logical_row_number=logical_data_records,
                            reason="timestamp_parse_failure",
                            field_count=len(row),
                            expected_field_count=expected_width,
                        )
                    )
                except Exception:
                    timestamp_parse_failures += 1
                    row_valid = False
                    malformed_records += 1
                    malformed_reports.append(
                        MalformedRowReport(
                            logical_row_number=logical_data_records,
                            reason="timestamp_parse_failure",
                            field_count=len(row),
                            expected_field_count=expected_width,
                        )
                    )

            if row_valid and len(row) == expected_width:
                # Count as valid when width is correct and timestamp (if any) parsed.
                # Width failures already continued above.
                if timestamp_field is None or row_valid:
                    valid_records += 1

    # Fix valid_records: rows that were width-ok but timestamp failed were counted
    # as malformed; ensure valid_records only counts fully valid rows.
    # The loop above increments valid_records only when row_valid is still True
    # after timestamp handling and width matched — good.

    return CSVAuditResult(
        headers=headers,
        encoding=encoding,
        delimiter=delimiter,
        logical_data_records=logical_data_records,
        valid_records=valid_records,
        malformed_records=malformed_records,
        skipped_records=skipped_records,
        truncated=truncated,
        first_samples=tuple(first_samples),
        last_samples=tuple(last_samples) if sample_size > 0 else tuple(),
        malformed_reports=tuple(malformed_reports[:100]),  # bound report retention
        duplicate_key_count=duplicate_key_count,
        ordering_violation_count=ordering_violation_count,
        timestamp_parse_failures=timestamp_parse_failures,
        observed_timestamp_units=tuple(sorted(observed_units)),
        earliest_timestamp=earliest_ts,
        latest_timestamp=latest_ts,
        max_rows_limit=max_rows,
        max_physical_line=max_physical_line,
        max_logical_record=max_logical_record,
    )


def read_zip_member_text(
    zip_path: Path,
    member_name: str,
    *,
    encoding: str,
    max_extracted_bytes: int,
) -> str:
    """Read a single ZIP member into memory with a hard extracted-byte bound.

    Used by precision comparison. Does not write extracted content to disk.
    """
    path = Path(zip_path)
    with zipfile.ZipFile(path, "r") as zf:
        if member_name not in zf.namelist():
            raise UnsafeArchiveError(
                f"Member not found: {member_name}",
                context={"member": member_name, "path": str(path)},
            )
        info = zf.getinfo(member_name)
        if info.file_size > max_extracted_bytes:
            raise UnsafeArchiveError(
                f"Member extracted size exceeds bound: {member_name}",
                context={
                    "member": member_name,
                    "file_size": info.file_size,
                    "max": max_extracted_bytes,
                },
            )
        raw = zf.read(member_name)
        if len(raw) > max_extracted_bytes:
            raise UnsafeArchiveError(
                f"Member extracted size exceeds bound after read: {member_name}",
                context={"member": member_name, "size": len(raw)},
            )
        return raw.decode(encoding)


def iter_csv_rows_from_text(
    text: str,
    *,
    delimiter: str = ",",
    has_header: bool = True,
) -> tuple[tuple[str, ...], list[tuple[str, ...]]]:
    """Parse CSV text into headers and data rows (in-memory helper for comparisons)."""
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        raise MalformedCSVError("CSV text is empty")
    if has_header:
        headers = _validate_headers(rows[0])
        data = [tuple(r) for r in rows[1:]]
        return headers, data
    raise MalformedCSVError("Headerless mode not supported")


__all__ = [
    "audit_zip_safe",
    "audit_csv_safe",
    "is_unsafe_zip_member_name",
    "read_zip_member_text",
    "iter_csv_rows_from_text",
]
