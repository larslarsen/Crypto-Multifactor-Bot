"""Typed models for AUD-001 schema and coverage profiling."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence


class ProfileMode(str, Enum):
    SAMPLE = "sample"
    FULL = "full"


class MetricCompleteness(str, Enum):
    """Whether a metric is exact, partial (sample-only), or unavailable."""

    EXACT = "exact"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class InferenceBasis(str, Enum):
    DECLARED = "declared"
    SAMPLED_VALUES = "sampled_values"
    FULL_SCAN = "full_scan"
    CALLER_MAPPED = "caller_mapped"
    UNRESOLVED = "unresolved"


class PhysicalType(str, Enum):
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    TIMESTAMP = "timestamp"
    BYTES = "bytes"
    NULL = "null"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ColumnRole(str, Enum):
    TIMESTAMP = "timestamp"
    KEY = "key"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"
    OTHER = "other"


class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class InputIdentity:
    """Immutable identity of the candidate file — caller-supplied, never inferred."""

    content_sha256: str
    byte_size: int
    source_uri: str
    media_type: str | None = None
    acquired_at: datetime | None = None

    def __post_init__(self) -> None:
        digest = self.content_sha256.lower().strip()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("content_sha256 must be 64-char lowercase hex")
        if self.byte_size < 0:
            raise ValueError("byte_size must be >= 0")
        if not self.source_uri:
            raise ValueError("source_uri must be non-empty")
        object.__setattr__(self, "content_sha256", digest)


@dataclass(frozen=True, slots=True)
class ColumnMapping:
    """Explicit role mapping. Ambiguity without a mapping is a quality issue."""

    timestamp: str | None = None
    keys: tuple[str, ...] = ()
    open: str | None = None
    high: str | None = None
    low: str | None = None
    close: str | None = None
    volume: str | None = None

    def role_for(self, column: str) -> ColumnRole | None:
        if self.timestamp is not None and column == self.timestamp:
            return ColumnRole.TIMESTAMP
        if column in self.keys:
            return ColumnRole.KEY
        if self.open is not None and column == self.open:
            return ColumnRole.OPEN
        if self.high is not None and column == self.high:
            return ColumnRole.HIGH
        if self.low is not None and column == self.low:
            return ColumnRole.LOW
        if self.close is not None and column == self.close:
            return ColumnRole.CLOSE
        if self.volume is not None and column == self.volume:
            return ColumnRole.VOLUME
        return None


@dataclass(frozen=True, slots=True)
class ColumnProfile:
    name: str
    physical_type: PhysicalType
    inference_basis: InferenceBasis
    type_uncertainty: bool
    null_count: int | None
    null_count_completeness: MetricCompleteness
    distinct_count: int | None
    distinct_count_completeness: MetricCompleteness
    min_value: str | None = None
    max_value: str | None = None
    range_completeness: MetricCompleteness = MetricCompleteness.UNAVAILABLE
    mapped_role: ColumnRole | None = None
    declared_type_label: str | None = None


@dataclass(frozen=True, slots=True)
class QualityIssue:
    code: str
    severity: IssueSeverity
    message: str
    column: str | None = None
    context: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "column": self.column,
            "context": dict(self.context),
        }


@dataclass(frozen=True, slots=True)
class TimestampCoverage:
    column: str | None
    min_ts: str | None
    max_ts: str | None
    completeness: MetricCompleteness
    monotonic_increasing: bool | None
    monotonic_completeness: MetricCompleteness
    gap_count: int | None
    median_cadence_seconds: float | None
    cadence_completeness: MetricCompleteness
    parse_failure_count: int = 0


@dataclass(frozen=True, slots=True)
class DuplicateKeyMetrics:
    key_columns: tuple[str, ...]
    duplicate_row_count: int | None
    duplicate_key_count: int | None
    completeness: MetricCompleteness


@dataclass(frozen=True, slots=True)
class OhlcMetrics:
    columns: Mapping[str, str]
    violation_count: int | None
    completeness: MetricCompleteness


@dataclass(frozen=True, slots=True)
class ProfileSummary:
    profiler_version: str
    mode: ProfileMode
    input: Mapping[str, Any]
    row_count: int | None
    row_count_completeness: MetricCompleteness
    columns: Sequence[ColumnProfile]
    timestamp: TimestampCoverage
    duplicate_keys: DuplicateKeyMetrics
    ohlc: OhlcMetrics
    issue_count: int
    issues_uri: str
    detail_uri: str
    quality_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "profiler_version": self.profiler_version,
            "mode": self.mode.value,
            "input": dict(self.input),
            "row_count": self.row_count,
            "row_count_completeness": self.row_count_completeness.value,
            "columns": [
                {
                    "name": c.name,
                    "physical_type": c.physical_type.value,
                    "inference_basis": c.inference_basis.value,
                    "type_uncertainty": c.type_uncertainty,
                    "null_count": c.null_count,
                    "null_count_completeness": c.null_count_completeness.value,
                    "distinct_count": c.distinct_count,
                    "distinct_count_completeness": c.distinct_count_completeness.value,
                    "min_value": c.min_value,
                    "max_value": c.max_value,
                    "range_completeness": c.range_completeness.value,
                    "mapped_role": c.mapped_role.value if c.mapped_role else None,
                    "declared_type_label": c.declared_type_label,
                }
                for c in self.columns
            ],
            "timestamp": {
                "column": self.timestamp.column,
                "min_ts": self.timestamp.min_ts,
                "max_ts": self.timestamp.max_ts,
                "completeness": self.timestamp.completeness.value,
                "monotonic_increasing": self.timestamp.monotonic_increasing,
                "monotonic_completeness": self.timestamp.monotonic_completeness.value,
                "gap_count": self.timestamp.gap_count,
                "median_cadence_seconds": self.timestamp.median_cadence_seconds,
                "cadence_completeness": self.timestamp.cadence_completeness.value,
                "parse_failure_count": self.timestamp.parse_failure_count,
            },
            "duplicate_keys": {
                "key_columns": list(self.duplicate_keys.key_columns),
                "duplicate_row_count": self.duplicate_keys.duplicate_row_count,
                "duplicate_key_count": self.duplicate_keys.duplicate_key_count,
                "completeness": self.duplicate_keys.completeness.value,
            },
            "ohlc": {
                "columns": dict(self.ohlc.columns),
                "violation_count": self.ohlc.violation_count,
                "completeness": self.ohlc.completeness.value,
            },
            "issue_count": self.issue_count,
            "issues_uri": self.issues_uri,
            "detail_uri": self.detail_uri,
            "quality_status": self.quality_status,
        }


@dataclass(frozen=True, slots=True)
class ProfileResult:
    """Profiler result: staged artifacts + MAN-001 PublishPlan (not published)."""

    summary: ProfileSummary
    issues: tuple[QualityIssue, ...]
    summary_path: Path
    detail_path: Path
    issues_path: Path
    publish_plan: Any  # cryptofactors.catalog.dataset.models.PublishPlan
