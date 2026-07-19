"""AUD-001 schema and coverage profiler (quality layer)."""

from __future__ import annotations

from cryptofactors.audit.errors import (
    AuditFormatError,
    AuditInputError,
    AuditMappingError,
    AuditOutputError,
    AuditProfileError,
)
from cryptofactors.audit.models import (
    ColumnMapping,
    ColumnProfile,
    ColumnRole,
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
from cryptofactors.audit.profiler import PROFILER_VERSION, profile_candidate

__all__ = [
    "PROFILER_VERSION",
    "AuditFormatError",
    "AuditInputError",
    "AuditMappingError",
    "AuditOutputError",
    "AuditProfileError",
    "ColumnMapping",
    "ColumnProfile",
    "ColumnRole",
    "DuplicateKeyMetrics",
    "InferenceBasis",
    "InputIdentity",
    "IssueSeverity",
    "MetricCompleteness",
    "OhlcMetrics",
    "PhysicalType",
    "ProfileMode",
    "ProfileResult",
    "ProfileSummary",
    "QualityIssue",
    "TimestampCoverage",
    "profile_candidate",
]
