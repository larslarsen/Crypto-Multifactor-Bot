"""Typed dataclasses for audit results and configuration."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class DownloadResult:
    url: str
    params: Dict[str, Any]
    retrieval_utc: datetime
    status: int
    headers: Dict[str, str]
    compressed_bytes: int
    sha256: str
    dest_path: Path
    checksum_verified: bool
    checksum_match: Optional[bool] = None


@dataclass
class ZipMemberInfo:
    name: str
    compressed_size: int
    file_size: int
    is_unsafe: bool = False


@dataclass
class ZipAuditResult:
    members: List[ZipMemberInfo]
    member_count: int
    total_compressed: int
    total_extracted: int
    unsafe_paths: List[str] = field(default_factory=list)


@dataclass
class CSVAuditResult:
    headers: List[str]
    row_count: int
    first_rows: List[List[str]]
    last_rows: List[List[str]]
    malformed_rows: int
    duplicate_keys: int
    ordering_violations: int
    earliest_ts: Optional[datetime] = None
    latest_ts: Optional[datetime] = None
    timestamp_precision: Optional[str] = None  # 's', 'ms', 'us', 'ns' or 'ambiguous'


@dataclass
class TimestampInference:
    unit: str  # 's', 'ms', 'us', 'ns'
    value: int
    inferred_from: str
    is_ambiguous: bool = False


@dataclass
class BinancePrecisionComparison:
    file1_unit: str
    file2_unit: str
    file1_sample: int
    file2_sample: int
    schema_diff: List[str]
    supports_transition: bool
    ambiguity: Optional[str] = None


@dataclass
class PaginationResult:
    records: List[Dict]
    pages_fetched: int
    duplicates: int
    gaps: List[Tuple]
    overlaps: List[Tuple]
    ordering_violations: int
    raw_pages: List[Dict] = field(default_factory=list)


@dataclass
class OHLCVBar:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume_base: Decimal
    volume_quote: Optional[Decimal] = None
    trade_count: int = 0
    is_no_trade_interval: bool = False


@dataclass
class BarReconstructionResult:
    bars: List[OHLCVBar]
    missing_provider: List[datetime]
    missing_reconstructed: List[datetime]
    discrepancies: List[Dict]
    tolerances_used: Dict[str, float]


@dataclass
class StorageStats:
    compressed_bytes: int
    extracted_bytes: int
    row_count: int
    bytes_per_row: float
    median: float
    upper_quantile: float
    max_observed: float
    coverage_duration: Optional[str] = None
    stress_case: Optional[float] = None
    projections: Optional[Dict[str, float]] = None  # U25, U50, U100
    assumptions: Optional[List[str]] = None


@dataclass
class AuditReport:
    schema_version: str = "1.0"
    toolkit_version: str = "0.1.0"
    run_id: str = ""
    input_hashes: Dict[str, str] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    observations: Dict[str, Any] = field(default_factory=dict)
