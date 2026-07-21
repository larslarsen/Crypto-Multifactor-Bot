"""Typed, immutable result models for the source-audit toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence


class TimestampUnit(str, Enum):
    """Supported Unix epoch timestamp units."""

    SECONDS = "s"
    MILLISECONDS = "ms"
    MICROSECONDS = "us"
    NANOSECONDS = "ns"


class PaginationMode(str, Enum):
    """Pagination strategy mode."""

    CURSOR = "cursor"
    FORWARD_TIME = "forward_time"
    BACKWARD_TIME = "backward_time"


class BoundaryPolicy(str, Enum):
    """Whether page time/cursor boundaries are inclusive or exclusive."""

    INCLUSIVE = "inclusive"
    EXCLUSIVE = "exclusive"


class IntervalClosure(str, Enum):
    """Bar interval closure semantics."""

    LEFT_CLOSED_RIGHT_OPEN = "left_closed_right_open"
    LEFT_OPEN_RIGHT_CLOSED = "left_open_right_closed"


class RecordDisposition(str, Enum):
    """Disposition of a CSV logical record during inspection."""

    VALID = "valid"
    MALFORMED = "malformed"
    SKIPPED = "skipped"
    TRUNCATED = "truncated"


@dataclass(frozen=True, slots=True)
class DownloadResult:
    """Structured metadata for a successfully published content-addressed object."""

    url: str
    params: Mapping[str, str]
    retrieval_utc: datetime
    status_code: int
    response_headers: Mapping[str, str]
    bytes_written: int
    sha256: str
    dest_path: Path
    reused_existing: bool
    checksum_verified: bool
    checksum_match: bool | None
    connect_timeout_s: float
    read_timeout_s: float
    chunk_size: int
    max_bytes: int


@dataclass(frozen=True, slots=True)
class ZipMemberInfo:
    """Metadata for one ZIP member after safety inspection (no extraction)."""

    name: str
    compressed_size: int
    file_size: int
    is_directory: bool
    compress_type: int
    flag_bits: int


@dataclass(frozen=True, slots=True)
class ZipAuditResult:
    """Structured result of a safe ZIP inspection."""

    members: tuple[ZipMemberInfo, ...]
    member_count: int
    total_compressed: int
    total_extracted: int
    max_ratio_observed: float


@dataclass(frozen=True, slots=True)
class MalformedRowReport:
    """Reasoned report for a malformed CSV logical record."""

    logical_row_number: int
    reason: str
    field_count: int | None = None
    expected_field_count: int | None = None


@dataclass(frozen=True, slots=True)
class CSVAuditResult:
    """Structured result of a bounded streaming CSV inspection."""

    headers: tuple[str, ...]
    encoding: str
    delimiter: str
    logical_data_records: int
    valid_records: int
    malformed_records: int
    skipped_records: int
    truncated: bool
    first_samples: tuple[tuple[str, ...], ...]
    last_samples: tuple[tuple[str, ...], ...]
    malformed_reports: tuple[MalformedRowReport, ...]
    duplicate_key_count: int
    ordering_violation_count: int
    timestamp_parse_failures: int
    observed_timestamp_units: tuple[str, ...]
    earliest_timestamp: datetime | None
    latest_timestamp: datetime | None
    max_rows_limit: int
    max_physical_line: int
    max_logical_record: int


@dataclass(frozen=True, slots=True)
class TimestampInference:
    """Exact inference result for a single timestamp value."""

    original_value: int | float | str | Decimal
    unit: TimestampUnit
    datetime_utc: datetime


@dataclass(frozen=True, slots=True)
class SchemaFieldDiff:
    """Difference between two observed schemas."""

    field_name: str
    side: str  # "only_left" | "only_right" | "both"
    detail: str


@dataclass(frozen=True, slots=True)
class BinancePrecisionComparison:
    """Comparison of two already-downloaded Binance archive objects."""

    archive_a_path: Path
    archive_b_path: Path
    member_a: str
    member_b: str
    representative_raw_a: tuple[str, ...]
    representative_raw_b: tuple[str, ...]
    inferred_unit_a: str | None
    inferred_unit_b: str | None
    unit_distribution_a: Mapping[str, int]
    unit_distribution_b: Mapping[str, int]
    sampled_rows_a: int
    sampled_rows_b: int
    valid_inferences_a: int
    valid_inferences_b: int
    schema_a: tuple[str, ...]
    schema_b: tuple[str, ...]
    schema_differences: tuple[SchemaFieldDiff, ...]
    malformed_a: int
    malformed_b: int
    ambiguous_a: int
    ambiguous_b: int
    supports_timestamp_precision_transition: bool
    transition_rationale: str
    min_valid_inferences: int
    max_malformed_rate: float
    max_ambiguous_rate: float


@dataclass(frozen=True, slots=True)
class PaginationDiagnostics:
    """Deterministic diagnostics collected during pagination."""

    mode: PaginationMode
    pages_fetched: int
    records_yielded: int
    max_pages: int
    max_records: int
    repeated_cursor_events: int
    non_progress_events: int
    repeated_page_events: int
    within_page_order_violations: int
    across_page_order_violations: int
    boundary_duplicate_count: int
    gap_count: int
    overlap_count: int
    stopped_reason: str


@dataclass(frozen=True, slots=True)
class GapReport:
    """Reported gap between consecutive records across pages."""

    previous_key: tuple[Any, ...]
    next_key: tuple[Any, ...]
    page_index: int


@dataclass(frozen=True, slots=True)
class OverlapReport:
    """Reported overlap or boundary duplicate between pages."""

    key: tuple[Any, ...]
    previous_page_index: int
    page_index: int
    kind: str  # "boundary_duplicate" | "overlap"


@dataclass(frozen=True, slots=True)
class PaginationResult:
    """Result of a bounded pagination run. No silent deduplication."""

    records: tuple[Mapping[str, Any], ...]
    diagnostics: PaginationDiagnostics
    gaps: tuple[GapReport, ...]
    overlaps: tuple[OverlapReport, ...]
    raw_pages: tuple[Any, ...]


@dataclass(frozen=True, slots=True)
class Trade:
    """Normalized trade observation for bar reconstruction."""

    timestamp_utc: datetime
    price: Decimal
    quantity: Decimal
    trade_id: str
    quote_quantity: Decimal | None = None


@dataclass(frozen=True, slots=True)
class OHLCVBar:
    """One reconstructed OHLCV bar. Absent intervals are omitted, not zero-filled."""

    interval_start_utc: datetime
    interval_end_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume_base: Decimal
    volume_quote: Decimal
    trade_count: int


@dataclass(frozen=True, slots=True)
class DuplicateTradeReport:
    """Report of duplicate trade identities observed during reconstruction."""

    trade_id: str
    occurrences: int


@dataclass(frozen=True, slots=True)
class BarReconstructionResult:
    """Result of deterministic trade-to-bar reconstruction."""

    bars: tuple[OHLCVBar, ...]
    input_trade_count: int
    unique_trade_count: int
    duplicate_trades: tuple[DuplicateTradeReport, ...]
    interval_duration_s: int
    alignment_origin_utc: datetime
    closure: IntervalClosure


@dataclass(frozen=True, slots=True)
class BarFieldMismatch:
    """Single field mismatch between reconstructed and provider bars."""

    interval_start_utc: datetime
    field_name: str
    expected: str
    observed: str
    absolute_delta: str | None
    signed_delta: str | None


@dataclass(frozen=True, slots=True)
class BarComparisonResult:
    """Structured comparison of reconstructed bars vs provider candles."""

    missing_from_provider: tuple[datetime, ...]
    missing_from_reconstructed: tuple[datetime, ...]
    ohlc_mismatches: tuple[BarFieldMismatch, ...]
    base_volume_mismatches: tuple[BarFieldMismatch, ...]
    quote_volume_mismatches: tuple[BarFieldMismatch, ...]
    trade_count_mismatches: tuple[BarFieldMismatch, ...]
    timestamp_alignment_mismatches: tuple[BarFieldMismatch, ...]
    duplicate_provider_intervals: tuple[datetime, ...]
    duplicate_reconstructed_intervals: tuple[datetime, ...]
    price_tolerance: Decimal
    volume_tolerance: Decimal
    trade_count_tolerance: int
    # Deterministic dimension sets (AUD-005 / REVIEW-0066).
    compared_dimensions: tuple[str, ...]
    not_comparable_dimensions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StorageSample:
    """One labelled observed storage sample."""

    label: str
    source_identity: str
    row_count: int
    compressed_bytes: int
    extracted_bytes: int
    coverage_note: str = ""


@dataclass(frozen=True, slots=True)
class ProjectionAssumptions:
    """Caller-supplied assumptions for U25/U50/U100 projections. No hidden defaults.

    ``u25_universe_size``, ``u50_universe_size``, and ``u100_universe_size`` are
    explicit asset counts for each named scenario — not percentages of a base
    universe.
    """

    u25_universe_size: int
    u50_universe_size: int
    u100_universe_size: int
    rows_per_asset_per_period: int
    retention_periods: int
    replication_factor: Decimal
    basis: str  # "compressed" | "extracted"
    overhead_multiplier: Decimal
    safety_multiplier: Decimal


@dataclass(frozen=True, slots=True)
class StorageStats:
    """Storage statistics and explicit-assumption projections."""

    samples_used: tuple[str, ...]
    bytes_per_row_by_sample: Mapping[str, Decimal]
    median_bytes_per_row: Decimal
    upper_quantile_bytes_per_row: Decimal
    max_observed_bytes_per_row: Decimal
    stress_case_bytes_per_row: Decimal
    upper_quantile: Decimal
    projections: Mapping[str, Decimal]
    projection_assumptions: ProjectionAssumptions
    basis: str


@dataclass(frozen=True, slots=True)
class AuditReport:
    """Generic audit envelope for deterministic serialization tests and tooling."""

    schema_version: str
    toolkit_version: str
    run_id: str
    input_hashes: Mapping[str, str] = field(default_factory=dict)
    config: Mapping[str, Any] = field(default_factory=dict)
    warnings: Sequence[str] = field(default_factory=tuple)
    errors: Sequence[str] = field(default_factory=tuple)
    observations: Mapping[str, Any] = field(default_factory=dict)
