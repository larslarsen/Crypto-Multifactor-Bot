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


class _BoundedCSVTextReader(io.TextIOBase):
    """Text stream enforcing physical-line and logical-record character limits.

    A physical line is terminated by ``\\n`` (or EOF). Quoted multiline CSV fields
    span multiple physical lines. Logical-record character count accumulates across
    those physical lines and is enforced *before* unbounded growth; it resets on an
    unquoted newline (end of logical CSV record). Quote state tracks ``"`` with
    standard doubled-quote escapes.
    """

    def __init__(
        self,
        base: io.TextIOBase,
        *,
        max_physical_line: int,
        max_logical_record: int,
    ) -> None:
        super().__init__()
        self._base = base
        self._max_physical_line = max_physical_line
        self._max_logical_record = max_logical_record
        self._buffer = ""
        self._in_quotes = False
        self._logical_chars = 0

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
                out.append(line[:remaining])
                self._buffer = line[remaining:] + self._buffer
                remaining = 0
        return "".join(out)

    def _track_and_check(self, line: str) -> None:
        body = line.rstrip("\r\n")
        if len(body) > self._max_physical_line:
            raise MalformedCSVError(
                "Physical line exceeds max_physical_line",
                context={
                    "length": len(body),
                    "max_physical_line": self._max_physical_line,
                },
            )
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"':
                if self._in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                    self._logical_chars += 2
                    i += 2
                    continue
                self._in_quotes = not self._in_quotes
                self._logical_chars += 1
                i += 1
                continue
            if ch == "\n" and not self._in_quotes:
                # End of logical record (excluding the terminator from the budget).
                self._logical_chars = 0
                i += 1
                continue
            if ch != "\r":
                self._logical_chars += 1
                if self._logical_chars > self._max_logical_record:
                    raise MalformedCSVError(
                        "Logical record exceeds max_logical_record during accumulation",
                        context={
                            "length": self._logical_chars,
                            "max_logical_record": self._max_logical_record,
                        },
                    )
            i += 1

    def readline(self, size: int | None = -1) -> str:  # type: ignore[override]
        del size
        if self._buffer:
            nl = self._buffer.find("\n")
            if nl >= 0:
                line = self._buffer[: nl + 1]
                self._buffer = self._buffer[nl + 1 :]
                self._track_and_check(line)
                return line
            more = self._base.readline()
            combined = self._buffer + more
            self._buffer = ""
            if not combined:
                return ""
            if "\n" not in combined:
                self._track_and_check(combined)
                return combined
            nl = combined.find("\n")
            line = combined[: nl + 1]
            self._buffer = combined[nl + 1 :]
            self._track_and_check(line)
            return line

        line = self._base.readline()
        if not line:
            return ""
        self._track_and_check(line)
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

    # Align the stdlib CSV field limit with caller configuration so fields larger
    # than the default 131_072 characters are allowed when configured, and fields
    # exceeding the configured logical-record bound are rejected by the parser.
    previous_field_limit = csv.field_size_limit()
    configured_field_limit = max(max_physical_line, max_logical_record, 128)
    try:
        csv.field_size_limit(configured_field_limit)
    except OverflowError:
        csv.field_size_limit(min(configured_field_limit, 2**31 - 1))

    try:
        try:
            raw = path.open("r", encoding=encoding, newline="")
        except (LookupError, UnicodeError, ValueError) as exc:
            raise MalformedCSVError(
                f"Encoding failure opening file with encoding={encoding!r}",
                context={"encoding": encoding},
            ) from exc

        with raw:
            limited = _BoundedCSVTextReader(
                raw,
                max_physical_line=max_physical_line,
                max_logical_record=max_logical_record,
            )
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
            except csv.Error as exc:
                raise MalformedCSVError(
                    f"CSV parse error in header: {exc}",
                    context={"encoding": encoding},
                ) from exc

            headers = _validate_headers(header_row)
            header_index = {name: idx for idx, name in enumerate(headers)}
            expected_width = len(headers)

            def _require_fields(
                label: str, fields: Sequence[str] | None
            ) -> tuple[str, ...]:
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

            while True:
                try:
                    row = next(reader)
                except StopIteration:
                    break
                except MalformedCSVError:
                    raise
                except UnicodeError as exc:
                    raise MalformedCSVError(
                        f"Encoding failure with encoding={encoding!r}",
                        context={"encoding": encoding},
                    ) from exc
                except csv.Error as exc:
                    # Unrecoverable parser failure → typed audit error (same as header).
                    raise MalformedCSVError(
                        f"CSV parse error: {exc}",
                        context={
                            "logical_row_number": logical_data_records + 1,
                            "encoding": encoding,
                        },
                    ) from exc

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
                    valid_records += 1
    finally:
        csv.field_size_limit(previous_field_limit)

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
    chunk_size: int = 65536,
) -> str:
    """Stream-decompress a single ZIP member with a hard extracted-byte bound.

    Does not call ``ZipFile.read`` (which allocates the full decompressed member
    before the limit can be enforced). Decompression is streamed in chunks and
    aborted as soon as ``max_extracted_bytes`` would be exceeded. Does not write
    extracted content to disk.
    """
    if max_extracted_bytes <= 0:
        raise ValueError("max_extracted_bytes must be positive")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not encoding:
        raise ValueError("encoding must be explicitly selected")

    path = Path(zip_path)
    with zipfile.ZipFile(path, "r") as zf:
        if member_name not in zf.namelist():
            raise UnsafeArchiveError(
                f"Member not found: {member_name}",
                context={"member": member_name, "path": str(path)},
            )
        info = zf.getinfo(member_name)
        # Advisory early reject when the declared size already exceeds the bound.
        # Declared size is not trusted alone; streaming still enforces the limit.
        if info.file_size > max_extracted_bytes:
            raise UnsafeArchiveError(
                f"Member extracted size exceeds bound: {member_name}",
                context={
                    "member": member_name,
                    "file_size": info.file_size,
                    "max": max_extracted_bytes,
                },
            )
        chunks: list[bytes] = []
        total = 0
        with zf.open(member_name, "r") as src:
            while True:
                piece = src.read(chunk_size)
                if not piece:
                    break
                total += len(piece)
                if total > max_extracted_bytes:
                    raise UnsafeArchiveError(
                        f"Member extracted size exceeds bound during stream: {member_name}",
                        context={
                            "member": member_name,
                            "bytes_read": total,
                            "max": max_extracted_bytes,
                        },
                    )
                chunks.append(piece)
        raw = b"".join(chunks)
        try:
            return raw.decode(encoding)
        except UnicodeError as exc:
            raise MalformedCSVError(
                f"Encoding failure decoding ZIP member with encoding={encoding!r}",
                context={"member": member_name, "encoding": encoding},
            ) from exc


def iter_csv_rows_from_text(
    text: str,
    *,
    delimiter: str = ",",
    has_header: bool = True,
    max_field_size: int | None = None,
) -> tuple[tuple[str, ...], list[tuple[str, ...]]]:
    """Parse CSV text into headers and data rows (in-memory helper for comparisons).

    In headerless mode the first row is treated as data, so the returned header
    tuple is empty.
    """
    previous = csv.field_size_limit()
    if max_field_size is not None and max_field_size > 0:
        try:
            csv.field_size_limit(max_field_size)
        except OverflowError:
            csv.field_size_limit(min(max_field_size, 2**31 - 1))
    try:
        try:
            reader = csv.reader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)
        except csv.Error as exc:
            raise MalformedCSVError(f"CSV parse error: {exc}") from exc
    finally:
        csv.field_size_limit(previous)
    if not rows:
        raise MalformedCSVError("CSV text is empty")
    if has_header:
        headers = _validate_headers(rows[0])
        data_rows = [tuple(r) for r in rows[1:]]
    else:
        headers = ()
        data_rows = [tuple(r) for r in rows]
    if not data_rows:
        raise MalformedCSVError("CSV text contains no data rows")
    return headers, data_rows


__all__ = [
    "audit_zip_safe",
    "audit_csv_safe",
    "is_unsafe_zip_member_name",
    "read_zip_member_text",
    "iter_csv_rows_from_text",
]
