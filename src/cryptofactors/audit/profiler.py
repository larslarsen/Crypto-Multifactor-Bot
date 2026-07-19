"""AUD-001 schema and coverage profiler.

Profiles an explicitly supplied candidate file with immutable input identity.
Does not discover directories, infer instruments, or mutate source observations.
Stages deterministic JSON/Parquet artifacts and builds a MAN-001 PublishPlan.

FULL mode is bounded and out-of-core: fixed-size Parquet batches, SQLite spill
for exact duplicate-key counts, and SQLite spill for exact cadence median.
Never collect()s an entire Parquet dataset; SAMPLE mode uses a bounded reservoir.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sqlite3
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from cryptofactors.audit.errors import (
    AuditFormatError,
    AuditInputError,
    AuditOutputError,
    AuditProfileError,
)
from cryptofactors.audit.models import (
    ColumnMapping,
    ColumnProfile,
    DuplicateKeyMetrics,
    InferenceBasis,
    InputIdentity,
    IssueSeverity,
    MetricCompleteness,
    OhlcMetrics,
    PhysicalType,
    ProfileMode,
    ProfileResult,
    ProfileSummary,
    QualityIssue,
    TimestampCoverage,
)
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetStatistics,
    DependencyKind,
    DependencyRef,
    OutputFileSpec,
    PublishPlan,
    QualityStatus,
    RowCountPolicy,
    SchemaIdentity,
    TransformSpec,
)

PROFILER_VERSION = "1.2.1"
_TRANSFORM_NAME = "audit.schema_coverage_profile"
_TRANSFORM_VERSION = "1"
_DATASET_TYPE = "audit_profile"
_SCHEMA_NAME = "audit_profile_summary"
_SCHEMA_VERSION = "1.1.0"
_SCHEMA_FINGERPRINT = (
    "aud001-profile-summary-v1.1.0"  # stable identity — not content-derived
)

_SUMMARY_NAME = "profile_summary.json"
_DETAIL_NAME = "profile_detail.parquet"
_ISSUES_NAME = "profile_issues.parquet"

_PARQUET_BATCH = 8_192
_CADENCE_RESERVOIR = 4_096
_DETAIL_CAP = 1_000

_TIMESTAMP_NAME_HINTS = frozenset(
    {
        "timestamp",
        "ts",
        "time",
        "datetime",
        "date",
        "open_time",
        "close_time",
        "event_time",
    }
)
_OHLC_NAME_HINTS = {
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "o": "open",
    "h": "high",
    "l": "low",
    "c": "close",
}


# ---- accumulators ---------------------------------------------------------


@dataclass
class _ColumnAccum:
    name: str
    nulls: int = 0
    seen: int = 0
    types_seen: set[str] = field(default_factory=set)
    min_num: float | None = None
    max_num: float | None = None
    min_str: str | None = None
    max_str: str | None = None
    sample_values: set[str] = field(default_factory=set)
    declared_type: str | None = None  # parquet physical/logical label


@dataclass
class _KeySpill:
    """SQLite-backed exact duplicate-key counter (bounded process memory)."""

    path: Path
    conn: sqlite3.Connection

    @classmethod
    def create(cls, work_dir: Path) -> _KeySpill:
        path = work_dir / "key_spill.sqlite"
        conn = sqlite3.connect(str(path))
        conn.execute(
            "CREATE TABLE keys ("
            "  key_blob BLOB NOT NULL PRIMARY KEY,"
            "  cnt INTEGER NOT NULL"
            ")"
        )
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute("PRAGMA journal_mode = MEMORY")
        return cls(path=path, conn=conn)

    def add(self, key_blob: bytes) -> None:
        self.conn.execute(
            "INSERT INTO keys(key_blob, cnt) VALUES (?, 1) "
            "ON CONFLICT(key_blob) DO UPDATE SET cnt = cnt + 1",
            (key_blob,),
        )

    def flush(self) -> None:
        self.conn.commit()

    def metrics(self) -> tuple[int, int]:
        """Return (duplicate_key_count, duplicate_row_count)."""
        self.conn.commit()
        dup_keys = 0
        dup_rows = 0
        for (cnt,) in self.conn.execute("SELECT cnt FROM keys WHERE cnt > 1"):
            dup_keys += 1
            dup_rows += int(cnt) - 1
        return dup_keys, dup_rows

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass


@dataclass
class _DeltaSpill:
    """SQLite-backed exact cadence storage (bounded process memory).

    Deltas are spilled only. Final median is computed once after the scan;
    gap count is a second bounded SQL pass against that final threshold.
    No evolving probe is used for reported exact metrics.
    """
    path: Path
    conn: sqlite3.Connection
    count: int = 0

    @classmethod
    def create(cls, work_dir: Path) -> _DeltaSpill:
        path = work_dir / "delta_spill.sqlite"
        conn = sqlite3.connect(str(path))
        conn.execute(
            "CREATE TABLE deltas ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  delta REAL NOT NULL"
            ")"
        )
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute("PRAGMA journal_mode = MEMORY")
        return cls(path=path, conn=conn)

    def add(self, delta: float) -> None:
        if delta < 0:
            return
        self.conn.execute("INSERT INTO deltas(delta) VALUES (?)", (float(delta),))
        self.count += 1

    def flush(self) -> None:
        self.conn.commit()

    def median(self) -> float | None:
        """Exact median of spilled non-negative deltas."""
        self.conn.commit()
        n = self.conn.execute("SELECT COUNT(*) FROM deltas").fetchone()[0]
        if not n:
            return None
        off = (n - 1) // 2
        row = self.conn.execute(
            "SELECT delta FROM deltas ORDER BY delta LIMIT 1 OFFSET ?",
            (off,),
        ).fetchone()
        return float(row[0]) if row else None

    def gap_count_against(self, median: float | None, *, factor: float = 3.0) -> int | None:
        """Count deltas strictly greater than factor * final median (exact)."""
        if median is None or median <= 0 or self.count == 0:
            return None if self.count == 0 else 0
        self.conn.commit()
        threshold = factor * median
        row = self.conn.execute(
            "SELECT COUNT(*) FROM deltas WHERE delta > ?",
            (threshold,),
        ).fetchone()
        return int(row[0]) if row else 0

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

@dataclass
class _CadenceReservoir:
    """Bounded reservoir for SAMPLE mode only (partial metrics)."""

    capacity: int = _CADENCE_RESERVOIR
    values: list[float] = field(default_factory=list)
    seen: int = 0
    gap_count: int = 0

    def add(self, delta: float) -> None:
        if delta < 0:
            return
        med = self.median()
        self.seen += 1
        if med is not None and med > 0 and delta > 3 * med:
            self.gap_count += 1
        if len(self.values) < self.capacity:
            self.values.append(delta)
            return
        idx = self.seen % self.capacity
        self.values[idx] = delta

    def median(self) -> float | None:
        if not self.values:
            return None
        ordered = sorted(self.values)
        return ordered[len(ordered) // 2]


# ---- helpers --------------------------------------------------------------


def _fsync_file(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _canonical_json(obj: Any) -> str:
    return (
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    )


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def _verify_identity(path: Path, identity: InputIdentity) -> None:
    """Verify both SHA-256 and byte size before any staging or lineage."""
    actual_sha, actual_size = _sha256_file(path)
    if actual_size != identity.byte_size:
        raise AuditInputError(
            "input_identity.byte_size does not match file size",
            context={"expected": identity.byte_size, "actual": actual_size},
        )
    if actual_sha != identity.content_sha256:
        raise AuditInputError(
            "input_identity.content_sha256 does not match file content",
            context={
                "expected": identity.content_sha256,
                "actual": actual_sha,
            },
        )


def _detect_format(path: Path, media_type: str | None) -> str:
    if media_type:
        mt = media_type.lower()
        if "csv" in mt or mt.endswith("/csv"):
            return "csv"
        if "parquet" in mt:
            return "parquet"
        if "json" in mt:
            return "jsonl"
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return "csv"
    if suffix in {".parquet", ".pq"}:
        return "parquet"
    if suffix in {".jsonl", ".ndjson"}:
        return "jsonl"
    raise AuditFormatError(
        "unsupported or unknown candidate format",
        context={"suffix": suffix, "media_type": media_type},
    )


def _classify_value(raw: str | None) -> tuple[str, float | None]:
    """Classify a CSV/text cell. None = null; '' = empty string (distinct)."""
    if raw is None:
        return "null", None
    if raw == "":
        return "empty_string", None
    text = raw.strip()
    if text.lower() in {"true", "false"}:
        return "boolean", None
    try:
        ival = int(text)
        return "integer", float(ival)
    except ValueError:
        pass
    try:
        fval = float(text)
        return "float", fval
    except ValueError:
        pass
    return "string", None


def _physical_from_types(types: set[str]) -> tuple[PhysicalType, bool]:
    cleaned = {t for t in types if t not in {"null"}}
    if not cleaned:
        return PhysicalType.NULL, False
    if cleaned == {"boolean"}:
        return PhysicalType.BOOLEAN, False
    if cleaned == {"integer"}:
        return PhysicalType.INTEGER, False
    if cleaned <= {"integer", "float"} and "float" in cleaned:
        return PhysicalType.FLOAT, False
    if cleaned == {"float"}:
        return PhysicalType.FLOAT, False
    if cleaned == {"string"} or cleaned == {"empty_string"} or cleaned <= {
        "string",
        "empty_string",
    }:
        return PhysicalType.STRING, False
    if len(cleaned) > 1:
        return PhysicalType.MIXED, True
    return PhysicalType.UNKNOWN, True


def _parquet_type_label(dtype: Any) -> tuple[PhysicalType, str, bool]:
    """Map polars/Arrow dtype to PhysicalType + declared label."""
    name = str(dtype)
    lower = name.lower()
    if "bool" in lower:
        return PhysicalType.BOOLEAN, name, False
    if any(x in lower for x in ("int", "uint")):
        return PhysicalType.INTEGER, name, False
    if any(x in lower for x in ("float", "double", "decimal")):
        return PhysicalType.FLOAT, name, False
    if "datetime" in lower or "timestamp" in lower or lower == "date":
        return PhysicalType.TIMESTAMP, name, False
    if "binary" in lower or "bytes" in lower:
        return PhysicalType.BYTES, name, False
    if "str" in lower or "utf" in lower or "categor" in lower:
        return PhysicalType.STRING, name, False
    return PhysicalType.UNKNOWN, name, True


def _encode_key(parts: Sequence[str | None]) -> bytes:
    """Length-prefixed key encoding; None and '' are distinct."""
    out = bytearray()
    for p in parts:
        if p is None:
            out.append(0x00)  # null marker
        else:
            raw = p.encode("utf-8", errors="surrogatepass")
            out.append(0x01)  # present (including empty string)
            out.extend(len(raw).to_bytes(4, "big"))
            out.extend(raw)
    return bytes(out)


def _parse_ts(value: Any) -> tuple[datetime | None, bool]:
    """Return (parsed, parse_failed). Empty/null is not a failure."""
    if value is None:
        return None, False
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc), False
        return value.astimezone(timezone.utc), False
    if isinstance(value, (int, float)):
        try:
            iv = int(value)
            if abs(iv) > 10_000_000_000:
                return datetime.fromtimestamp(iv / 1000.0, tz=timezone.utc), False
            return datetime.fromtimestamp(iv, tz=timezone.utc), False
        except (ValueError, OverflowError, OSError):
            return None, True
    text = str(value).strip()
    if text == "":
        return None, False
    try:
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            iv = int(text)
            if abs(iv) > 10_000_000_000:
                return datetime.fromtimestamp(iv / 1000.0, tz=timezone.utc), False
            return datetime.fromtimestamp(iv, tz=timezone.utc), False
    except (ValueError, OverflowError, OSError):
        return None, True
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc), False
    except ValueError:
        return None, True


def _resolve_timestamp_column(
    columns: Sequence[str],
    mapping: ColumnMapping | None,
    issues: list[QualityIssue],
) -> str | None:
    if mapping is not None and mapping.timestamp is not None:
        if mapping.timestamp not in columns:
            issues.append(
                QualityIssue(
                    code="timestamp_mapping_missing_column",
                    severity=IssueSeverity.ERROR,
                    message="mapped timestamp column not present in file",
                    column=mapping.timestamp,
                )
            )
            return None
        return mapping.timestamp
    hints = [c for c in columns if c.lower() in _TIMESTAMP_NAME_HINTS]
    if len(hints) == 1:
        issues.append(
            QualityIssue(
                code="timestamp_inferred_by_name",
                severity=IssueSeverity.WARNING,
                message="timestamp column inferred by name hint; not caller-mapped",
                column=hints[0],
                context={"basis": "name_hint"},
            )
        )
        return hints[0]
    if len(hints) > 1:
        issues.append(
            QualityIssue(
                code="timestamp_mapping_ambiguous",
                severity=IssueSeverity.ERROR,
                message="multiple timestamp-like columns; provide ColumnMapping.timestamp",
                context={"candidates": hints},
            )
        )
        return None
    issues.append(
        QualityIssue(
            code="timestamp_mapping_absent",
            severity=IssueSeverity.WARNING,
            message="no timestamp column mapped or uniquely inferred",
        )
    )
    return None


def _resolve_ohlc(
    columns: Sequence[str],
    mapping: ColumnMapping | None,
    issues: list[QualityIssue],
) -> dict[str, str]:
    colset = set(columns)
    if mapping is not None:
        resolved: dict[str, str] = {}
        for role, name in (
            ("open", mapping.open),
            ("high", mapping.high),
            ("low", mapping.low),
            ("close", mapping.close),
        ):
            if name is None:
                continue
            if name not in colset:
                issues.append(
                    QualityIssue(
                        code="ohlc_mapping_missing_column",
                        severity=IssueSeverity.ERROR,
                        message=f"mapped OHLC column {role!r} not present",
                        column=name,
                    )
                )
            else:
                resolved[role] = name
        if resolved and len(resolved) < 4:
            issues.append(
                QualityIssue(
                    code="ohlc_mapping_incomplete",
                    severity=IssueSeverity.WARNING,
                    message="partial OHLC mapping; violations require all four columns",
                    context={"mapped": resolved},
                )
            )
        return resolved if len(resolved) == 4 else {}

    found: dict[str, str] = {}
    lower_map = {c.lower(): c for c in columns}
    for hint, role in _OHLC_NAME_HINTS.items():
        if hint in lower_map and role not in found:
            found[role] = lower_map[hint]
    if len(found) == 4:
        issues.append(
            QualityIssue(
                code="ohlc_inferred_by_name",
                severity=IssueSeverity.WARNING,
                message="OHLC columns inferred by name; not caller-mapped",
                context={"columns": found},
            )
        )
        return found
    if found:
        issues.append(
            QualityIssue(
                code="ohlc_mapping_ambiguous",
                severity=IssueSeverity.WARNING,
                message="incomplete OHLC name hints; provide ColumnMapping for OHLC checks",
                context={"partial": found},
            )
        )
    return {}


def _open_csv(path: Path) -> tuple[TextIO, csv.DictReader[str]]:
    handle = path.open("r", encoding="utf-8", newline="", errors="replace")
    reader = csv.DictReader(handle)
    if reader.fieldnames is None:
        handle.close()
        raise AuditFormatError("CSV has no header row", context={"suffix": path.suffix})
    return handle, reader


# ---- core profiling -------------------------------------------------------


def _profile_stream(
    columns: Sequence[str],
    row_batches: Iterator[list[dict[str, Any]]],
    *,
    mode: ProfileMode,
    mapping: ColumnMapping | None,
    work_dir: Path,
    declared_types: Mapping[str, tuple[PhysicalType, str, bool]] | None,
) -> tuple[
    int,
    list[ColumnProfile],
    TimestampCoverage,
    DuplicateKeyMetrics,
    OhlcMetrics,
    list[QualityIssue],
    list[dict[str, Any]],
]:
    issues: list[QualityIssue] = []
    accums = {c: _ColumnAccum(name=c) for c in columns}
    if declared_types:
        for c, (ptype, label, _unc) in declared_types.items():
            if c in accums:
                accums[c].declared_type = label
                accums[c].types_seen.add(ptype.value)

    ts_col = _resolve_timestamp_column(columns, mapping, issues)
    ohlc_cols = _resolve_ohlc(columns, mapping, issues)
    key_cols: tuple[str, ...] = ()
    if mapping is not None and mapping.keys:
        missing = [k for k in mapping.keys if k not in columns]
        if missing:
            issues.append(
                QualityIssue(
                    code="key_mapping_missing_column",
                    severity=IssueSeverity.ERROR,
                    message="mapped key column(s) not present",
                    context={"missing": missing},
                )
            )
        else:
            key_cols = tuple(mapping.keys)
    else:
        issues.append(
            QualityIssue(
                code="key_mapping_absent",
                severity=IssueSeverity.WARNING,
                message="no key columns mapped; duplicate-key metrics unavailable",
            )
        )

    key_spill: _KeySpill | None = None
    if key_cols:
        key_spill = _KeySpill.create(work_dir)

    row_count = 0
    prev_ts: datetime | None = None
    mono_ok = True
    mono_seen = False
    cadence_exact: _DeltaSpill | None = None
    cadence_sample: _CadenceReservoir | None = None
    if mode is ProfileMode.FULL:
        cadence_exact = _DeltaSpill.create(work_dir)
    else:
        cadence_sample = _CadenceReservoir()
    _gap_count = 0
    ohlc_violations = 0
    ts_parse_failures = 0
    ts_min: datetime | None = None
    ts_max: datetime | None = None
    detail_rows: list[dict[str, Any]] = []

    try:
        for batch in row_batches:
            for row in batch:
                row_count += 1
                for c in columns:
                    acc = accums[c]
                    raw = row.get(c)
                    acc.seen += 1
                    # Preserve native types for parquet; CSV arrives as str|None
                    if declared_types and c in declared_types:
                        if raw is None:
                            acc.types_seen.add("null")
                            acc.nulls += 1
                        else:
                            ptype, _label, _u = declared_types[c]
                            acc.types_seen.add(ptype.value)
                            if isinstance(raw, (int, float)) and not isinstance(
                                raw, bool
                            ):
                                num_val = float(raw)
                                acc.min_num = (
                                    num_val if acc.min_num is None else min(acc.min_num, num_val)
                                )
                                acc.max_num = (
                                    num_val if acc.max_num is None else max(acc.max_num, num_val)
                                )
                            elif isinstance(raw, datetime):
                                s = raw.isoformat()
                                acc.min_str = (
                                    s if acc.min_str is None else min(acc.min_str, s)
                                )
                                acc.max_str = (
                                    s if acc.max_str is None else max(acc.max_str, s)
                                )
                            else:
                                s = str(raw)
                                if len(acc.sample_values) < 32:
                                    acc.sample_values.add(s[:128])
                                acc.min_str = (
                                    s if acc.min_str is None else min(acc.min_str, s)
                                )
                                acc.max_str = (
                                    s if acc.max_str is None else max(acc.max_str, s)
                                )
                    else:
                        # CSV path: str | None; '' is empty_string not null
                        if not isinstance(raw, str) and raw is not None:
                            raw = str(raw)
                        kind, num = _classify_value(raw if isinstance(raw, str) or raw is None else str(raw))
                        acc.types_seen.add(kind)
                        if kind == "null":
                            acc.nulls += 1
                        elif kind == "empty_string":
                            if len(acc.sample_values) < 32:
                                acc.sample_values.add("")
                        else:
                            if len(acc.sample_values) < 32 and raw is not None:
                                acc.sample_values.add(str(raw)[:128])
                            if num is not None:
                                acc.min_num = (
                                    num if acc.min_num is None else min(acc.min_num, num)
                                )
                                acc.max_num = (
                                    num if acc.max_num is None else max(acc.max_num, num)
                                )
                            else:
                                s = str(raw) if raw is not None else ""
                                acc.min_str = (
                                    s if acc.min_str is None else min(acc.min_str, s)
                                )
                                acc.max_str = (
                                    s if acc.max_str is None else max(acc.max_str, s)
                                )

                if ts_col is not None:
                    ts, failed = _parse_ts(row.get(ts_col))
                    if failed:
                        ts_parse_failures += 1
                    elif ts is not None:
                        ts_min = ts if ts_min is None else min(ts_min, ts)
                        ts_max = ts if ts_max is None else max(ts_max, ts)
                        if prev_ts is not None:
                            mono_seen = True
                            delta = (ts - prev_ts).total_seconds()
                            if delta < 0:
                                mono_ok = False
                            else:
                                if cadence_exact is not None:
                                    cadence_exact.add(delta)
                                elif cadence_sample is not None:
                                    cadence_sample.add(delta)
                        prev_ts = ts

                if key_spill is not None and key_cols:
                    parts: list[str | None] = []
                    for k in key_cols:
                        v = row.get(k)
                        if v is None:
                            parts.append(None)
                        else:
                            parts.append(str(v))
                    key_spill.add(_encode_key(parts))

                if ohlc_cols:
                    try:
                        o = float(row.get(ohlc_cols["open"]))  # type: ignore[arg-type]
                        h = float(row.get(ohlc_cols["high"]))  # type: ignore[arg-type]
                        low_v = float(row.get(ohlc_cols["low"]))  # type: ignore[arg-type]
                        close_ = float(row.get(ohlc_cols["close"]))  # type: ignore[arg-type]
                        if not (low_v <= o <= h and low_v <= close_ <= h and low_v <= h):
                            ohlc_violations += 1
                    except (TypeError, ValueError):
                        ohlc_violations += 1

                if len(detail_rows) < _DETAIL_CAP:
                    # Deterministic detail: no path fields; stringify for parquet stability
                    detail_rows.append(
                        {
                            k: (
                                None
                                if row.get(k) is None
                                else (
                                    v.isoformat()
                                    if isinstance((v := row.get(k)), datetime)
                                    else v
                                )
                            )
                            for k in columns
                        }
                    )

            if key_spill is not None:
                key_spill.flush()
    finally:
        pass

    if ts_parse_failures:
        issues.append(
            QualityIssue(
                code="timestamp_parse_failures",
                severity=IssueSeverity.WARNING,
                message="timestamp values failed to parse",
                column=ts_col,
                context={"failure_count": ts_parse_failures},
            )
        )

    completeness = (
        MetricCompleteness.EXACT
        if mode is ProfileMode.FULL
        else MetricCompleteness.PARTIAL
    )

    col_profiles: list[ColumnProfile] = []
    for c in columns:
        acc = accums[c]
        if declared_types and c in declared_types:
            ptype, _label, uncertain = declared_types[c]
            basis = InferenceBasis.DECLARED
            # nulls still from scan
        else:
            ptype, uncertain = _physical_from_types(acc.types_seen)
            basis = (
                InferenceBasis.FULL_SCAN
                if mode is ProfileMode.FULL
                else InferenceBasis.SAMPLED_VALUES
            )
        role = mapping.role_for(c) if mapping is not None else None
        min_v = str(acc.min_num) if acc.min_num is not None else acc.min_str
        max_v = str(acc.max_num) if acc.max_num is not None else acc.max_str
        col_profiles.append(
            ColumnProfile(
                name=c,
                physical_type=ptype,
                inference_basis=basis,
                type_uncertainty=uncertain,
                null_count=acc.nulls,
                null_count_completeness=completeness,
                distinct_count=len(acc.sample_values),
                distinct_count_completeness=MetricCompleteness.PARTIAL,
                min_value=min_v,
                max_value=max_v,
                range_completeness=(
                    completeness if min_v is not None else MetricCompleteness.UNAVAILABLE
                ),
                mapped_role=role,
                declared_type_label=(
                    declared_types[c][1] if declared_types and c in declared_types else None
                ),
            )
        )

    if cadence_exact is not None:
        cadence_exact.flush()
        med_cadence = cadence_exact.median()
        # Gaps classified only against the final median (exact, out-of-core).
        gap_out = cadence_exact.gap_count_against(med_cadence)
        cad_comp = completeness if cadence_exact.count else MetricCompleteness.UNAVAILABLE
        cadence_exact.close()
    elif cadence_sample is not None:
        med_cadence = cadence_sample.median()
        gap_out = cadence_sample.gap_count if cadence_sample.values else None
        cad_comp = (
            MetricCompleteness.PARTIAL if cadence_sample.values else MetricCompleteness.UNAVAILABLE
        )
    else:
        med_cadence = None
        gap_out = None
        cad_comp = MetricCompleteness.UNAVAILABLE

    ts_coverage = TimestampCoverage(
        column=ts_col,
        min_ts=ts_min.isoformat() if ts_min else None,
        max_ts=ts_max.isoformat() if ts_max else None,
        completeness=completeness if ts_col else MetricCompleteness.UNAVAILABLE,
        monotonic_increasing=mono_ok if mono_seen else None,
        monotonic_completeness=(
            completeness if mono_seen else MetricCompleteness.UNAVAILABLE
        ),
        gap_count=gap_out,
        median_cadence_seconds=med_cadence,
        cadence_completeness=cad_comp,
        parse_failure_count=ts_parse_failures,
    )

    dup_rows = None
    dup_keys = None
    dup_comp = MetricCompleteness.UNAVAILABLE
    if key_spill is not None:
        dup_keys, dup_rows = key_spill.metrics()
        dup_comp = completeness
        key_spill.close()

    dup_metrics = DuplicateKeyMetrics(
        key_columns=key_cols,
        duplicate_row_count=dup_rows,
        duplicate_key_count=dup_keys,
        completeness=dup_comp,
    )
    ohlc_metrics = OhlcMetrics(
        columns=ohlc_cols,
        violation_count=ohlc_violations if ohlc_cols else None,
        completeness=completeness if ohlc_cols else MetricCompleteness.UNAVAILABLE,
    )
    return (
        row_count,
        col_profiles,
        ts_coverage,
        dup_metrics,
        ohlc_metrics,
        issues,
        detail_rows,
    )


def _csv_batches(
    path: Path, *, limit: int | None, batch_size: int = _PARQUET_BATCH
) -> tuple[list[str], Iterator[list[dict[str, Any]]]]:
    handle, reader = _open_csv(path)
    columns = list(reader.fieldnames or [])

    def _gen() -> Iterator[list[dict[str, Any]]]:
        batch: list[dict[str, Any]] = []
        n = 0
        try:
            for row in reader:
                # Preserve None vs missing; DictReader gives '' for empty fields
                # Map empty missing differently: use row.get which returns None if absent
                rec: dict[str, Any] = {}
                for k in columns:
                    if k not in row:
                        rec[k] = None
                    else:
                        rec[k] = row[k]  # may be ''
                batch.append(rec)
                n += 1
                if limit is not None and n >= limit:
                    if batch:
                        yield batch
                    return
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            if batch:
                yield batch
        finally:
            handle.close()

    return columns, _gen()


def _parquet_batches(
    path: Path, *, limit: int | None, batch_size: int = _PARQUET_BATCH
) -> tuple[
    list[str],
    dict[str, tuple[PhysicalType, str, bool]],
    Iterator[list[dict[str, Any]]],
]:
    try:
        import pyarrow.parquet as pq  # type: ignore[import-untyped]
    except ImportError as exc:
        raise AuditFormatError("pyarrow required for parquet profiling") from exc

    pf = pq.ParquetFile(str(path))
    schema = pf.schema_arrow
    columns = list(schema.names)
    declared: dict[str, tuple[PhysicalType, str, bool]] = {}
    for i, name in enumerate(columns):
        field = schema.field(i)
        declared[name] = _parquet_type_label(field.type)

    def _gen() -> Iterator[list[dict[str, Any]]]:
        n = 0
        for batch in pf.iter_batches(batch_size=batch_size):
            # to_pylist preserves None; native types kept
            rows = batch.to_pylist()
            if limit is not None:
                remain = limit - n
                if remain <= 0:
                    return
                if len(rows) > remain:
                    rows = rows[:remain]
            n += len(rows)
            yield rows
            if limit is not None and n >= limit:
                return

    return columns, declared, _gen()


def _write_parquet(path: Path, rows: Sequence[Mapping[str, Any]]) -> int:
    try:
        import polars as pl
    except ImportError as exc:
        raise AuditOutputError(
            "polars is required to write Parquet profile artifacts",
        ) from exc
    if not rows:
        df = pl.DataFrame({"_empty": []})
    else:

        def _pad(row: Mapping[str, Any]) -> dict[str, Any]:
            # Empty dicts -> field-less struct, which polars cannot write to Parquet.
            # Pad with a dummy key so the struct column stays valid (content preserved
            # for any non-empty dict).
            out = {}
            for k, v in row.items():
                out[k] = v if v != {} else {"_empty": None}
            return out

        df = pl.DataFrame(
            [_pad(r) for r in rows], infer_schema_length=min(len(rows), 1000)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    df.write_parquet(str(tmp))
    _fsync_file(tmp)
    os.replace(str(tmp), str(path))
    _fsync_file(path)
    return int(df.height)


def _stage_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".aud-", suffix=".partial", dir=str(path.parent))
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp_path), str(path))
        _fsync_file(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _quality_status(issues: Sequence[QualityIssue]) -> QualityStatus:
    if any(i.severity is IssueSeverity.ERROR for i in issues):
        return QualityStatus.QUARANTINED
    if any(i.severity is IssueSeverity.WARNING for i in issues):
        return QualityStatus.PASS_WITH_WARNINGS
    return QualityStatus.PASS


def profile_candidate(
    path: Path | str,
    input_identity: InputIdentity,
    *,
    mode: ProfileMode = ProfileMode.SAMPLE,
    column_mapping: ColumnMapping | None = None,
    sample_size: int = 10_000,
    output_dir: Path | str,
    code_commit: str = "unknown",
    config_sha256: str | None = None,
    dependency: DependencyRef | None = None,
) -> ProfileResult:
    """Profile one candidate file; stage artifacts; return MAN-001 PublishPlan."""
    candidate = Path(path)
    out = Path(output_dir)
    if not candidate.is_file():
        raise AuditInputError(
            "candidate path is not a regular file",
            context={"path": str(candidate)},
        )
    if sample_size <= 0:
        raise AuditInputError("sample_size must be positive")

    # Verify identity before any staging or lineage construction.
    _verify_identity(candidate, input_identity)

    fmt = _detect_format(candidate, input_identity.media_type)
    limit = sample_size if mode is ProfileMode.SAMPLE else None

    work_dir = Path(tempfile.mkdtemp(prefix=".aud001-work-", dir=str(out.parent)))
    try:
        declared: dict[str, tuple[PhysicalType, str, bool]] | None = None
        if fmt == "csv":
            columns, batches = _csv_batches(candidate, limit=limit)
        elif fmt == "parquet":
            columns, declared, batches = _parquet_batches(candidate, limit=limit)
        else:
            raise AuditFormatError(
                "format not implemented for profiling",
                context={"format": fmt},
            )

        (
            row_count,
            col_profiles,
            ts_coverage,
            dup_metrics,
            ohlc_metrics,
            issues,
            detail_rows,
        ) = _profile_stream(
            columns,
            batches,
            mode=mode,
            mapping=column_mapping,
            work_dir=work_dir,
            declared_types=declared,
        )
    finally:
        # bounded iterative cleanup
        if work_dir.exists():
            for child in sorted(work_dir.rglob("*"), reverse=True):
                try:
                    if child.is_file() or child.is_symlink():
                        child.unlink(missing_ok=True)
                    elif child.is_dir():
                        child.rmdir()
                except OSError:
                    pass
            try:
                work_dir.rmdir()
            except OSError:
                pass

    row_completeness = (
        MetricCompleteness.EXACT
        if mode is ProfileMode.FULL
        else MetricCompleteness.PARTIAL
    )
    if mode is ProfileMode.SAMPLE:
        issues.append(
            QualityIssue(
                code="sample_mode_partial_metrics",
                severity=IssueSeverity.INFO,
                message="profile ran in SAMPLE mode; metrics marked partial are not exact",
                context={"sample_size": sample_size, "rows_seen": row_count},
            )
        )

    q_status = _quality_status(issues)
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / _SUMMARY_NAME
    detail_path = out / _DETAIL_NAME
    issues_path = out / _ISSUES_NAME

    try:
        detail_rows_out: list[dict[str, Any]] = (
            detail_rows if detail_rows else [{"_empty": None}]
        )
        detail_count = _write_parquet(detail_path, detail_rows_out)
        issues_rows = [i.to_dict() for i in issues] or [
            {
                "code": "none",
                "severity": "info",
                "message": "no issues",
                "column": None,
                "context": {},
            }
        ]
        issues_count = _write_parquet(issues_path, issues_rows)
    except AuditProfileError:
        raise
    except Exception as exc:
        raise AuditOutputError(
            f"failed to write parquet artifacts: {exc}",
            context={"output_dir": str(out)},
        ) from exc

    # Deterministic summary: no local candidate path.
    summary = ProfileSummary(
        profiler_version=PROFILER_VERSION,
        mode=mode,
        input={
            "content_sha256": input_identity.content_sha256,
            "byte_size": input_identity.byte_size,
            "source_uri": input_identity.source_uri,
            "media_type": input_identity.media_type,
        },
        row_count=row_count,
        row_count_completeness=row_completeness,
        columns=tuple(col_profiles),
        timestamp=ts_coverage,
        duplicate_keys=dup_metrics,
        ohlc=ohlc_metrics,
        issue_count=len(issues),
        issues_uri=_ISSUES_NAME,
        detail_uri=_DETAIL_NAME,
        quality_status=q_status.value,
    )
    summary_bytes = _canonical_json(summary.to_dict()).encode("utf-8")
    _stage_bytes(summary_path, summary_bytes)

    sum_sha, sum_sz = _sha256_file(summary_path)
    det_sha, det_sz = _sha256_file(detail_path)
    iss_sha, iss_sz = _sha256_file(issues_path)

    cfg_hash = config_sha256 or hashlib.sha256(
        _canonical_json(
            {
                "mode": mode.value,
                "sample_size": sample_size,
                "mapping": {
                    "timestamp": column_mapping.timestamp if column_mapping else None,
                    "keys": list(column_mapping.keys) if column_mapping else [],
                    "open": column_mapping.open if column_mapping else None,
                    "high": column_mapping.high if column_mapping else None,
                    "low": column_mapping.low if column_mapping else None,
                    "close": column_mapping.close if column_mapping else None,
                },
                "profiler_version": PROFILER_VERSION,
            }
        ).encode("utf-8")
    ).hexdigest()

    deps: list[DependencyRef] = []
    if dependency is not None:
        deps.append(dependency)
    else:
        deps.append(
            DependencyRef(
                id=f"raw_{input_identity.content_sha256}",
                kind=DependencyKind.RAW_OBJECT,
                role="profile_candidate",
            )
        )

    coverage = CoverageWindow(
        event_start=(
            datetime.fromisoformat(ts_coverage.min_ts) if ts_coverage.min_ts else None
        ),
        event_end=(
            datetime.fromisoformat(ts_coverage.max_ts) if ts_coverage.max_ts else None
        ),
    )

    output_specs = (
        OutputFileSpec(
            relative_path=_SUMMARY_NAME,
            sha256=sum_sha,
            rows=1,
            bytes=sum_sz,
            rows_verified=True,
        ),
        OutputFileSpec(
            relative_path=_DETAIL_NAME,
            sha256=det_sha,
            rows=detail_count,
            bytes=det_sz,
            rows_verified=True,
        ),
        OutputFileSpec(
            relative_path=_ISSUES_NAME,
            sha256=iss_sha,
            rows=issues_count,
            bytes=iss_sz,
            rows_verified=True,
        ),
    )
    # Statistics agree with output specs (sum of output bytes/rows).
    total_out_rows = sum(s.rows for s in output_specs)
    total_out_bytes = sum(s.bytes for s in output_specs)

    plan = PublishPlan(
        dataset_type=_DATASET_TYPE,
        schema=SchemaIdentity(
            name=_SCHEMA_NAME,
            version=_SCHEMA_VERSION,
            fingerprint=_SCHEMA_FINGERPRINT,
        ),
        transform=TransformSpec(name=_TRANSFORM_NAME, version=_TRANSFORM_VERSION),
        code=CodeIdentity(commit=code_commit),
        config=ConfigIdentity(config_sha256=cfg_hash),
        dependencies=tuple(deps),
        output_sources={
            _SUMMARY_NAME: summary_path,
            _DETAIL_NAME: detail_path,
            _ISSUES_NAME: issues_path,
        },
        output_specs=output_specs,
        statistics=DatasetStatistics(
            row_count=total_out_rows,
            byte_size=total_out_bytes,
        ),
        coverage=coverage,
        quality_status=q_status,
        quality_summary={
            "issue_count": len(issues),
            "mode": mode.value,
            "profiler_version": PROFILER_VERSION,
            "candidate_row_count": row_count,
        },
        row_count_policy=RowCountPolicy.ALLOW_UNVERIFIED_DECLARED,
    )

    return ProfileResult(
        summary=summary,
        issues=tuple(issues),
        summary_path=summary_path,
        detail_path=detail_path,
        issues_path=issues_path,
        publish_plan=plan,
    )
