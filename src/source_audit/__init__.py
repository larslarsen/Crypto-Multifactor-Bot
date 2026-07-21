"""Source-audit toolkit for Research Sprint 003 / AUD-002.

Public API is explicit. No wildcard re-exports.
"""

from __future__ import annotations

from .archives import (
    audit_csv_safe,
    audit_zip_safe,
    is_unsafe_zip_member_name,
    iter_csv_rows_from_text,
    read_zip_member_text,
    read_zip_member_text_prefix,
)
from .bars import compare_bars, normalize_trade, reconstruct_bars
from .binance_precision import compare_binance_archive_precision
from .download import (
    HttpxTransport,
    SyntheticTransport,
    TimeoutConfig,
    atomic_download,
    content_addressed_path,
)
from .errors import (
    AmbiguousTimestampError,
    AuditError,
    BarReconstructionError,
    ChecksumMismatchError,
    DownloadError,
    InvalidNumericError,
    MalformedCSVError,
    OrderingViolationError,
    OutOfRangeTimestampError,
    PaginationError,
    PrecisionComparisonError,
    SerializationError,
    SizeLimitError,
    UnsafeArchiveError,
)
from .hashing import compute_sha256, verify_checksum
from .models import (
    AuditReport,
    BarComparisonResult,
    BarFieldMismatch,
    BarReconstructionResult,
    BinancePrecisionComparison,
    BoundaryPolicy,
    CSVAuditResult,
    DownloadResult,
    DuplicateTradeReport,
    GapReport,
    IntervalClosure,
    MalformedRowReport,
    OHLCVBar,
    OverlapReport,
    PaginationDiagnostics,
    PaginationMode,
    PaginationResult,
    ProjectionAssumptions,
    RecordDisposition,
    SchemaFieldDiff,
    StorageSample,
    StorageStats,
    TimestampInference,
    TimestampUnit,
    Trade,
    ZipAuditResult,
    ZipMemberInfo,
)
from .pagination import PaginationCallbacks, paginate
from .serialization import dump_csv, dump_json, dumps_csv, dumps_json
from .storage import compute_storage_stats
from .timestamps import infer_timestamp_unit

__version__ = "0.2.0"

__all__ = [
    # version
    "__version__",
    # download
    "TimeoutConfig",
    "HttpxTransport",
    "SyntheticTransport",
    "atomic_download",
    "content_addressed_path",
    "compute_sha256",
    "verify_checksum",
    # archives
    "audit_zip_safe",
    "audit_csv_safe",
    "is_unsafe_zip_member_name",
    "read_zip_member_text",
    "read_zip_member_text_prefix",
    "iter_csv_rows_from_text",
    # timestamps
    "infer_timestamp_unit",
    # binance precision
    "compare_binance_archive_precision",
    # pagination
    "PaginationCallbacks",
    "paginate",
    # bars
    "normalize_trade",
    "reconstruct_bars",
    "compare_bars",
    # storage
    "compute_storage_stats",
    # serialization
    "dumps_json",
    "dump_json",
    "dumps_csv",
    "dump_csv",
    # errors
    "AuditError",
    "DownloadError",
    "ChecksumMismatchError",
    "SizeLimitError",
    "UnsafeArchiveError",
    "MalformedCSVError",
    "AmbiguousTimestampError",
    "OutOfRangeTimestampError",
    "PaginationError",
    "OrderingViolationError",
    "InvalidNumericError",
    "SerializationError",
    "BarReconstructionError",
    "PrecisionComparisonError",
    # models
    "TimestampUnit",
    "PaginationMode",
    "BoundaryPolicy",
    "IntervalClosure",
    "RecordDisposition",
    "DownloadResult",
    "ZipMemberInfo",
    "ZipAuditResult",
    "MalformedRowReport",
    "CSVAuditResult",
    "TimestampInference",
    "SchemaFieldDiff",
    "BinancePrecisionComparison",
    "PaginationDiagnostics",
    "GapReport",
    "OverlapReport",
    "PaginationResult",
    "Trade",
    "OHLCVBar",
    "DuplicateTradeReport",
    "BarReconstructionResult",
    "BarFieldMismatch",
    "BarComparisonResult",
    "StorageSample",
    "ProjectionAssumptions",
    "StorageStats",
    "AuditReport",
]
