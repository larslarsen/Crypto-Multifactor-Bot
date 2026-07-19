"""AUD-001 schema and coverage profiler.

Profiles an explicitly supplied candidate file with immutable input identity.
Does not discover directories, infer instruments, or mutate source observations.
Stages deterministic JSON/Parquet artifacts and builds a MAN-001 PublishPlan.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
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

PROFILER_VERSION = "1.0.0"
_TRANSFORM_NAME = "audit.schema_coverage_profile"
_TRANSFORM_VERSION = "1"
_DATASET_TYPE = "audit_profile"
_SCHEMA_NAME = "audit_profile_summary"
_SCHEMA_VERSION = "1.0.0"

_SUMMARY_NAME = "profile_summary.json"
_DETAIL_NAME = "profile_detail.parquet"
_ISSUES_NAME = "profile_issues.parquet"

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


@dataclass
class _ColumnAccum:
    name: str
    nulls: int = 0
    seen: int = 0
    types_seen: set[str] | None = None
    min_num: float | None = None
    max_num: float | None = None
    min_str: str | None = None
    max_str: str | None = None
    sample_values: set[str] | None = None

    def __post_init__(self) -> None:
        if self.types_seen is None:
            self.types_seen = set()
        if self.sample_values is None:
            self.sample_values = set()


def _fsync_file(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


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
        context={"path": str(path), "media_type": media_type, "suffix": suffix},
    )


def _classify_value(raw: str | None) -> tuple[str, float | None]:
    if raw is None or raw == "":
        return "null", None
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
    cleaned = {t for t in types if t != "null"}
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
    if cleaned == {"string"}:
        return PhysicalType.STRING, False
    if len(cleaned) > 1:
        return PhysicalType.MIXED, True
    return PhysicalType.UNKNOWN, True


def _open_csv(path: Path) -> tuple[TextIO, csv.DictReader[str]]:
    handle = path.open("r", encoding="utf-8", newline="", errors="replace")
    reader = csv.DictReader(handle)
    if reader.fieldnames is None:
        handle.close()
        raise AuditFormatError("CSV has no header row", context={"path": str(path)})
    return handle, reader


def _iter_csv_rows(
    path: Path, *, limit: int | None
) -> tuple[list[str], Iterator[dict[str, str | None]], Any]:
    handle, reader = _open_csv(path)
    columns = list(reader.fieldnames or [])

    def _gen() -> Iterator[dict[str, str | None]]:
        n = 0
        try:
            for row in reader:
                yield {k: row.get(k) for k in columns}
                n += 1
                if limit is not None and n >= limit:
                    return
        finally:
            handle.close()

    return columns, _gen(), handle


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
                    message="partial OHLC mapping; violations computed only where all four present",
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


def _parse_ts(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    text = value.strip()
    try:
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            iv = int(text)
            # heuristic: ms vs s
            if abs(iv) > 10_000_000_000:
                return datetime.fromtimestamp(iv / 1000.0, tz=timezone.utc)
            return datetime.fromtimestamp(iv, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        pass
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _profile_rows(
    columns: Sequence[str],
    rows: Iterator[dict[str, str | None]],
    *,
    mode: ProfileMode,
    mapping: ColumnMapping | None,
    sample_size: int,
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

    row_count = 0
    prev_ts: datetime | None = None
    mono_ok = True
    mono_seen = False
    deltas: list[float] = []
    gap_count = 0
    ohlc_violations = 0
    key_counts: dict[tuple[str, ...], int] = {}
    detail_rows: list[dict[str, Any]] = []
    ts_min: datetime | None = None
    ts_max: datetime | None = None

    for row in rows:
        row_count += 1
        for c in columns:
            acc = accums[c]
            raw = row.get(c)
            acc.seen += 1
            kind, num = _classify_value(raw)
            assert acc.types_seen is not None
            acc.types_seen.add(kind)
            if kind == "null":
                acc.nulls += 1
                continue
            assert acc.sample_values is not None
            if len(acc.sample_values) < 32 and raw is not None:
                acc.sample_values.add(raw[:128])
            if num is not None:
                acc.min_num = num if acc.min_num is None else min(acc.min_num, num)
                acc.max_num = num if acc.max_num is None else max(acc.max_num, num)
            else:
                s = raw or ""
                acc.min_str = s if acc.min_str is None else min(acc.min_str, s)
                acc.max_str = s if acc.max_str is None else max(acc.max_str, s)

        if ts_col is not None:
            ts = _parse_ts(row.get(ts_col))
            if ts is not None:
                ts_min = ts if ts_min is None else min(ts_min, ts)
                ts_max = ts if ts_max is None else max(ts_max, ts)
                if prev_ts is not None:
                    mono_seen = True
                    delta = (ts - prev_ts).total_seconds()
                    if delta < 0:
                        mono_ok = False
                    else:
                        deltas.append(delta)
                        # gap heuristic: > 3x running median of last deltas
                        if len(deltas) >= 5:
                            recent = sorted(deltas[-11:])
                            med = recent[len(recent) // 2]
                            if med > 0 and delta > 3 * med:
                                gap_count += 1
                prev_ts = ts

        if key_cols:
            key = tuple(row.get(k) or "" for k in key_cols)
            key_counts[key] = key_counts.get(key, 0) + 1

        if ohlc_cols:
            try:
                o = float(row.get(ohlc_cols["open"]) or "nan")
                h = float(row.get(ohlc_cols["high"]) or "nan")
                low = float(row.get(ohlc_cols["low"]) or "nan")
                close_ = float(row.get(ohlc_cols["close"]) or "nan")
                if not (low <= o <= h and low <= close_ <= h and low <= h):
                    ohlc_violations += 1
            except ValueError:
                ohlc_violations += 1

        if row_count <= min(sample_size, 1000):
            detail_rows.append(dict(row))

    completeness = (
        MetricCompleteness.EXACT if mode is ProfileMode.FULL else MetricCompleteness.PARTIAL
    )
    basis = InferenceBasis.FULL_SCAN if mode is ProfileMode.FULL else InferenceBasis.SAMPLED_VALUES

    col_profiles: list[ColumnProfile] = []
    for c in columns:
        acc = accums[c]
        assert acc.types_seen is not None
        ptype, uncertain = _physical_from_types(acc.types_seen)
        role = mapping.role_for(c) if mapping is not None else None
        min_v = (
            str(acc.min_num)
            if acc.min_num is not None
            else acc.min_str
        )
        max_v = (
            str(acc.max_num)
            if acc.max_num is not None
            else acc.max_str
        )
        col_profiles.append(
            ColumnProfile(
                name=c,
                physical_type=ptype,
                inference_basis=basis,
                type_uncertainty=uncertain,
                null_count=acc.nulls,
                null_count_completeness=completeness,
                distinct_count=len(acc.sample_values or []),
                distinct_count_completeness=MetricCompleteness.PARTIAL,
                min_value=min_v,
                max_value=max_v,
                range_completeness=completeness
                if min_v is not None
                else MetricCompleteness.UNAVAILABLE,
                mapped_role=role,
            )
        )

    median_cadence: float | None = None
    if deltas:
        ds = sorted(deltas)
        median_cadence = ds[len(ds) // 2]

    ts_coverage = TimestampCoverage(
        column=ts_col,
        min_ts=ts_min.isoformat() if ts_min else None,
        max_ts=ts_max.isoformat() if ts_max else None,
        completeness=completeness if ts_col else MetricCompleteness.UNAVAILABLE,
        monotonic_increasing=mono_ok if mono_seen else None,
        monotonic_completeness=completeness if mono_seen else MetricCompleteness.UNAVAILABLE,
        gap_count=gap_count if deltas else None,
        median_cadence_seconds=median_cadence,
        cadence_completeness=completeness if deltas else MetricCompleteness.UNAVAILABLE,
    )

    dup_rows = None
    dup_keys = None
    dup_comp = MetricCompleteness.UNAVAILABLE
    if key_cols:
        dup_keys = sum(1 for _, n in key_counts.items() if n > 1)
        dup_rows = sum(n - 1 for _, n in key_counts.items() if n > 1)
        dup_comp = completeness
        # Bound memory: if FULL and huge, still exact for keys seen in stream
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


def _write_parquet(path: Path, rows: Sequence[Mapping[str, Any]]) -> int:
    """Write rows to Parquet via polars. Returns row count."""
    try:
        import polars as pl
    except ImportError as exc:
        raise AuditOutputError(
            "polars is required to write Parquet profile artifacts",
        ) from exc

    def _pad(row: Mapping[str, Any]) -> dict[str, Any]:
        # Empty dicts -> field-less struct, which polars cannot write to Parquet.
        # Pad with a dummy key so the struct column stays valid (content preserved
        # for any non-empty dict).
        out = {}
        for k, v in row.items():
            out[k] = v if v != {} else {"_empty": None}
        return out

    if not rows:
        # empty frame with placeholder column for stable schema
        df = pl.DataFrame({"_empty": []})
    else:
        df = pl.DataFrame(
            [_pad(r) for r in rows], infer_schema_length=min(len(rows), 1000)
        )
    df.write_parquet(str(path))
    _fsync_file(path)
    return df.height


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
    """Profile one candidate file; stage artifacts; return MAN-001 PublishPlan.

    Parameters
    ----------
    path:
        Explicit candidate file path. Not searched or discovered.
    input_identity:
        Caller-supplied immutable identity (hash, size, uri).
    mode:
        SAMPLE (bounded rows, partial metrics) or FULL (streaming full pass).
    column_mapping:
        Optional explicit timestamp/key/OHLC roles. Ambiguity without mapping
        becomes quality issues — never a silent guess presented as fact.
    """
    candidate = Path(path)
    out = Path(output_dir)
    if not candidate.is_file():
        raise AuditInputError(
            "candidate path is not a regular file",
            context={"path": str(candidate)},
        )
    if sample_size <= 0:
        raise AuditInputError("sample_size must be positive")

    # Verify identity size matches (hash verification is caller's duty for full trust;
    # we check byte_size when cheap).
    actual_size = candidate.stat().st_size
    if actual_size != input_identity.byte_size:
        raise AuditInputError(
            "input_identity.byte_size does not match file size",
            context={
                "expected": input_identity.byte_size,
                "actual": actual_size,
            },
        )

    fmt = _detect_format(candidate, input_identity.media_type)
    limit = sample_size if mode is ProfileMode.SAMPLE else None

    if fmt == "csv":
        columns, row_iter, _ = _iter_csv_rows(candidate, limit=limit)
        (
            row_count,
            col_profiles,
            ts_coverage,
            dup_metrics,
            ohlc_metrics,
            issues,
            detail_rows,
        ) = _profile_rows(
            columns,
            row_iter,
            mode=mode,
            mapping=column_mapping,
            sample_size=sample_size,
        )
    elif fmt == "parquet":
        try:
            import polars as pl
        except ImportError as exc:
            raise AuditFormatError("polars required for parquet profiling") from exc
        lf = pl.scan_parquet(str(candidate))
        schema_names = list(lf.collect_schema().names())
        if mode is ProfileMode.SAMPLE:
            df = lf.head(sample_size).collect()
        else:
            df = lf.collect()
        columns = schema_names

        def _row_iter() -> Iterator[dict[str, str | None]]:
            for rec in df.iter_rows(named=True):
                yield {
                    k: (None if v is None else str(v))
                    for k, v in rec.items()
                }

        (
            row_count,
            col_profiles,
            ts_coverage,
            dup_metrics,
            ohlc_metrics,
            issues,
            detail_rows,
        ) = _profile_rows(
            columns,
            _row_iter(),
            mode=mode,
            mapping=column_mapping,
            sample_size=sample_size,
        )
    else:
        raise AuditFormatError(
            "format not implemented for profiling",
            context={"format": fmt},
        )

    row_completeness = (
        MetricCompleteness.EXACT if mode is ProfileMode.FULL else MetricCompleteness.PARTIAL
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

    # Stage detail + issues parquet first.
    try:
        detail_rows_out = detail_rows if detail_rows else [{"_empty": None}]
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

    summary = ProfileSummary(
        profiler_version=PROFILER_VERSION,
        mode=mode,
        input={
            "content_sha256": input_identity.content_sha256,
            "byte_size": input_identity.byte_size,
            "source_uri": input_identity.source_uri,
            "media_type": input_identity.media_type,
            "path": str(candidate),
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
            datetime.fromisoformat(ts_coverage.min_ts)
            if ts_coverage.min_ts
            else None
        ),
        event_end=(
            datetime.fromisoformat(ts_coverage.max_ts)
            if ts_coverage.max_ts
            else None
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

    plan = PublishPlan(
        dataset_type=_DATASET_TYPE,
        schema=SchemaIdentity(
            name=_SCHEMA_NAME,
            version=_SCHEMA_VERSION,
            fingerprint=sum_sha,
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
            row_count=row_count,
            byte_size=sum_sz + det_sz + iss_sz,
        ),
        coverage=coverage,
        quality_status=q_status,
        quality_summary={
            "issue_count": len(issues),
            "mode": mode.value,
            "profiler_version": PROFILER_VERSION,
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
