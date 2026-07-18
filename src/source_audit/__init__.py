"""Source Audit Toolkit - Research Sprint 003"""

from .errors import (
    AuditError,
    DownloadError,
    ChecksumMismatchError,
    UnsafeArchiveError,
    MalformedCSVError,
    AmbiguousTimestampError,
    PaginationError,
    OrderingViolationError,
    InvalidNumericError,
)
from .models import (
    DownloadResult,
    ZipMemberInfo,
    ZipAuditResult,
    CSVAuditResult,
    TimestampInference,
    BinancePrecisionComparison,
    PaginationResult,
    OHLCVBar,
    BarReconstructionResult,
    StorageStats,
    AuditReport,
)
from .timestamps import infer_timestamp_unit
from .archives import audit_zip_safe, audit_csv_safe
from .pagination import paginate
from .bars import reconstruct_bars, compare_bars

__version__ = "0.1.0"
