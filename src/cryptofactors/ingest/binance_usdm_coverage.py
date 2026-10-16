"""Build the immutable CEX-002 coverage ledger and UTC-day alignment reports.

The producer consumes accepted normalized products only.  It authenticates every
completion, partition and lineage descriptor, streams only timestamp columns, and never
turns source absence into an economic value or an availability vintage.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import hashlib
import json
import os
import stat
import uuid
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    ACCEPTED_MEMBERSHIP_IDENTITIES,
    ACCEPTED_REJECTED_MEMBERSHIP_ROWS,
    ACCEPTED_SOURCE_COVERAGE_GAPS,
    ACCEPTED_TYPED_GAP_MEMBERSHIPS,
    PARQUET_COMPRESSION,
    PARQUET_COMPRESSION_LEVEL,
    PARQUET_VERSION,
    PRODUCT_BAR_1H,
    PRODUCT_COVERAGE_GAP,
    PRODUCT_FUNDING_INDICATIVE_1H,
    PRODUCT_FUNDING_REALIZED,
    PRODUCT_LIQUIDATION_OBSERVED_DAILY,
    PRODUCT_MARK_INDEX_BASIS_1H,
    PRODUCT_MEMBERSHIP,
    PRODUCT_OPEN_INTEREST_5M,
    PRODUCT_TRADE_FLOW_1H,
    QUALITY_GAP_COLUMNS,
    SIZING_ROW_BATCH,
    TYPED_GAP_MEMBERSHIP_COLUMNS,
    final_product_schema,
    native_identity,
    product_schema_identity,
    prove_coverage_authority,
    writer_identity,
)

REPORT_SHA256 = "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
SIZING_SHA256 = "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589"
HOLDOUT_SHA256 = "2030e20aa5bd73df8fdbb7467e928508103b2e23659b85527101ec8b8546cb85"
HOLDOUT_ID = "c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2"
HOLDOUT_UTC = "2026-08-21T16:19:08.994166+00:00"

COMPLETION_SHA256: Mapping[str, str] = {
    PRODUCT_MEMBERSHIP: "01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3",
    PRODUCT_BAR_1H: "3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7",
    PRODUCT_TRADE_FLOW_1H: "a165f9e57065514cadc95620c280a82dbad5032d17c19e1caf012c9d12a84d0a",
    PRODUCT_OPEN_INTEREST_5M: "bb089fc992326c66ddb65cea03dda92e8cd9fcf7cb7f373821f04a16db9168e4",
    PRODUCT_FUNDING_REALIZED: "57628164f19d182164b6058d9e51f794430cc918706c088f430e1c01d2898522",
    PRODUCT_FUNDING_INDICATIVE_1H: "360eb662ab89c47ca1f6db754b74f486a42de4aa116970221f0739268a51fba0",
    PRODUCT_MARK_INDEX_BASIS_1H: "b698c0543c281e3244e0c3358ea7ce1f347bc591b06a076058fed749d05584f0",
    PRODUCT_LIQUIDATION_OBSERVED_DAILY: "dc4127dccad31477cb72ec6fdf076dbdbdef34a1212d4f090d5f421b96dc267f",
    "binance_usdm_cost_calibration": "fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e",
}

ALIGNMENT_PRODUCTS = (
    PRODUCT_BAR_1H,
    PRODUCT_OPEN_INTEREST_5M,
    PRODUCT_FUNDING_REALIZED,
    PRODUCT_MARK_INDEX_BASIS_1H,
    PRODUCT_LIQUIDATION_OBSERVED_DAILY,
)
SUMMARY_PRODUCTS = (
    PRODUCT_BAR_1H,
    PRODUCT_TRADE_FLOW_1H,
    PRODUCT_OPEN_INTEREST_5M,
    PRODUCT_FUNDING_REALIZED,
    PRODUCT_FUNDING_INDICATIVE_1H,
    PRODUCT_MARK_INDEX_BASIS_1H,
    PRODUCT_LIQUIDATION_OBSERVED_DAILY,
    "binance_usdm_cost_calibration",
)

TIMESTAMP_COLUMNS: Mapping[str, str] = {
    PRODUCT_BAR_1H: "open_time",
    PRODUCT_TRADE_FLOW_1H: "open_time",
    PRODUCT_OPEN_INTEREST_5M: "create_time",
    PRODUCT_FUNDING_REALIZED: "calc_time",
    PRODUCT_FUNDING_INDICATIVE_1H: "open_time",
    PRODUCT_MARK_INDEX_BASIS_1H: "open_time",
    PRODUCT_LIQUIDATION_OBSERVED_DAILY: "event_time_ms",
}
FIXED_DAILY_COUNTS: Mapping[str, int] = {
    PRODUCT_BAR_1H: 24,
    PRODUCT_TRADE_FLOW_1H: 24,
    PRODUCT_OPEN_INTEREST_5M: 288,
    PRODUCT_FUNDING_INDICATIVE_1H: 24,
    PRODUCT_MARK_INDEX_BASIS_1H: 24,
}
TIME_PRECISION: Mapping[str, str] = {
    PRODUCT_BAR_1H: "millisecond_hour_open",
    PRODUCT_TRADE_FLOW_1H: "millisecond_hour_open",
    PRODUCT_OPEN_INTEREST_5M: "millisecond_native_five_minute_phase",
    PRODUCT_FUNDING_REALIZED: "millisecond_observed_event",
    PRODUCT_FUNDING_INDICATIVE_1H: "millisecond_hour_open",
    PRODUCT_MARK_INDEX_BASIS_1H: "millisecond_hour_open",
    PRODUCT_LIQUIDATION_OBSERVED_DAILY: "millisecond_observed_daily_point",
    "binance_usdm_cost_calibration": "source_day_only_event_extrema_unavailable",
}

SOURCE_GAP_SCHEMA = final_product_schema(PRODUCT_COVERAGE_GAP)
TYPED_GAP_SCHEMA = pa.schema([column.field() for column in TYPED_GAP_MEMBERSHIP_COLUMNS])
QUALITY_GAP_SCHEMA = pa.schema([column.field() for column in QUALITY_GAP_COLUMNS])
SOURCE_GAP_SCHEMA_SHA256 = product_schema_identity(PRODUCT_COVERAGE_GAP)

SOURCE_GAP_ROWS = 8_317
SOURCE_GAP_PARTITIONS = 4_817
SOURCE_GAP_BYTES = 36_831_146
SOURCE_GAP_LARGEST_FILE = 9_458
TYPED_GAP_ROWS = 3_742
TYPED_GAP_PARTITIONS = 3_742
TYPED_GAP_BYTES = 7_757_166
TYPED_GAP_LARGEST_FILE = 2_073
QUALITY_GAP_ROWS = 216_934_972
QUALITY_GAP_PARTITIONS = 130_820
QUALITY_GAP_BYTES = 9_154_761_060
QUALITY_GAP_LARGEST_FILE = 418_609
METADATA_PAGE_COUNTS = {"source_gap": 4_817, "typed_gap": 3_742, "quality_gap": 130_820}
METADATA_PAGE_BYTES = 4_096
METADATA_BUDGET_BYTES = 570_896_384
RELEASE_METADATA_BYTES = 5_556_368_003
RELEASE_METADATA_REMAINDER_BYTES = 4_985_471_619
DETAILED_MEMBERSHIP_IDENTITIES = 698
FUNDING_ONLY_MEMBERSHIP_IDENTITIES = 73
COST_SOURCE_GAP_ROWS = 494
MAX_JSON_BYTES = 64 * 2**20
DAY_MS = 86_400_000
RENAME_NOREPLACE = 1


class CoverageNormalizationError(RuntimeError):
    """Fail-closed coverage authority, accounting, or publication error."""


@dataclass(frozen=True, slots=True)
class PublicationHooks:
    """Test interruption points; ordinary callers leave every hook unset."""

    before_publish: Callable[[str, Path, Path], None] | None = None


@dataclass(frozen=True, slots=True)
class ProductInput:
    product: str
    root: Path
    descriptor_root: Path
    completion: Mapping[str, Any]
    completion_path: Path
    completion_sha256: str
    schema: pa.Schema


@dataclass(frozen=True, slots=True)
class PartitionInput:
    product: str
    native_symbol: str
    utc_month: str
    row_count: int
    parquet_path: Path
    parquet_sha256: str
    lineage_path: Path
    lineage_sha256: str
    descriptor_sha256: str


@dataclass(frozen=True, slots=True)
class Artifact:
    path: Path
    sha256: str
    byte_size: int
    row_count: int | None
    reused: bool
    schema: pa.Schema | None = None


@dataclass(frozen=True, slots=True)
class PartitionScan:
    observed_by_day: Counter[str]
    distinct_by_day: Mapping[str, int]
    duplicate_by_day: Mapping[str, int]
    cadence_complete_by_day: Mapping[str, bool]
    cadence_failure_by_day: Mapping[str, str]
    first_observed_ms: int | None
    last_observed_ms: int | None
    duplicate_timestamps: int


@dataclass(frozen=True, slots=True)
class CoverageResult:
    completion_path: Path
    completion_sha256: str
    completion_reused: bool
    source_gap_rows: int
    typed_gap_rows: int
    quality_gap_rows: int
    daily_report_count: int
    aligned_day_count: int
    five_product_observed_day_count: int
    full_cadence_day_count: int
    metadata_bytes: int


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CoverageNormalizationError(message)


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _schema_contract(schema: pa.Schema) -> list[dict[str, Any]]:
    return [{"name": field.name, "arrow_type": str(field.type), "nullable": field.nullable} for field in schema]


def _schema_sha(schema: pa.Schema) -> str:
    return _sha(_canonical_json(_schema_contract(schema)))


def _safe_component(value: object, label: str) -> str:
    _require(type(value) is str and bool(value), f"{label} is empty")
    assert isinstance(value, str)
    _require(value not in {".", ".."} and "/" not in value and "\\" not in value and "\x00" not in value, f"{label} is unsafe")
    return value


def _safe_relative(value: object, label: str) -> PurePosixPath:
    _require(type(value) is str and bool(value), f"{label} is empty")
    assert isinstance(value, str)
    _require("\\" not in value and "\x00" not in value and not value.startswith("/"), f"{label} is unsafe")
    original_parts = value.split("/")
    _require(all(part not in {"", ".", ".."} for part in original_parts), f"{label} is unsafe")
    path = PurePosixPath(*original_parts)
    return path


def _require_safe_path(path: Path, *, regular: bool, label: str) -> None:
    absolute = path.absolute()
    for component in reversed((absolute, *absolute.parents)):
        if not component.exists() and not component.is_symlink():
            continue
        facts = component.lstat()
        _require(not stat.S_ISLNK(facts.st_mode), f"{label} contains a symlink")
    if regular:
        _require(path.exists() and stat.S_ISREG(path.lstat().st_mode), f"{label} is not a regular file")


def _read_regular(path: Path, maximum: int | None = None) -> bytes:
    descriptor = _open_regular_path(path, "input path")
    try:
        facts = os.fstat(descriptor)
        if maximum is not None:
            _require(0 < facts.st_size <= maximum, "input exceeds its read bound")
        chunks: list[bytes] = []
        total = 0
        while block := os.read(descriptor, 1024 * 1024):
            total += len(block)
            if maximum is not None:
                _require(total <= maximum, "input exceeds its read bound")
            chunks.append(block)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _read_json(path: Path, expected_sha: str, maximum: int = MAX_JSON_BYTES) -> Mapping[str, Any]:
    body = _read_regular(path, maximum)
    _require(_sha(body) == expected_sha, "JSON authority digest changed")
    try:
        value = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CoverageNormalizationError("JSON authority is malformed") from exc
    _require(type(value) is dict, "JSON authority is not an object")
    return value


def _read_json_artifact(
    path: Path, expected_sha: str, maximum: int = MAX_JSON_BYTES
) -> tuple[Mapping[str, Any], int]:
    body = _read_regular(path, maximum)
    _require(_sha(body) == expected_sha, "JSON authority digest changed")
    try:
        value = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CoverageNormalizationError("JSON authority is malformed") from exc
    _require(type(value) is dict, "JSON authority is not an object")
    return value, len(body)


def _file_sha(path: Path) -> tuple[str, int]:
    descriptor = _open_regular_path(path, "input path")
    try:
        return _hash_fd(descriptor)
    finally:
        os.close(descriptor)


def _hash_fd(descriptor: int) -> tuple[str, int]:
    position = os.lseek(descriptor, 0, os.SEEK_CUR)
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    size = 0
    try:
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
            size += len(block)
    finally:
        os.lseek(descriptor, position, os.SEEK_SET)
    return digest.hexdigest(), size


def _open_regular_path(path: Path, label: str) -> int:
    """Open an absolute pathname one no-follow component at a time."""
    absolute = path.absolute()
    parts = absolute.parts
    _require(bool(parts) and parts[0] == "/" and len(parts) > 1, f"{label} path is invalid")
    directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for component in parts[1:-1]:
            _safe_component(component, label)
            child = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=directory,
            )
            os.close(directory)
            directory = child
        name = _safe_component(parts[-1], label)
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=directory,
        )
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise CoverageNormalizationError(f"{label} is not a regular file")
        return descriptor
    except OSError as exc:
        raise CoverageNormalizationError(
            f"{label} contains a symlink, missing, or unsafe component"
        ) from exc
    finally:
        os.close(directory)


def _parse_month(value: str) -> tuple[int, int]:
    _require(len(value) == 7 and value[4] == "-" and value[:4].isdigit() and value[5:].isdigit(), "UTC month is malformed")
    year, month = int(value[:4]), int(value[5:])
    _require(1970 <= year <= 2100 and 1 <= month <= 12, "UTC month is out of range")
    return year, month


def _month_days(month: str) -> Iterator[date]:
    year, number = _parse_month(month)
    cursor = date(year, number, 1)
    end = date(year + (number == 12), 1 if number == 12 else number + 1, 1)
    while cursor < end:
        yield cursor
        cursor += timedelta(days=1)


def _month_range(first: str, last: str) -> Iterator[str]:
    year, month = _parse_month(first)
    end = _parse_month(last)
    while (year, month) <= end:
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year, month = year + 1, 1


def _day_text(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms // 1000, tz=UTC).date().isoformat()


def _month_text(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms // 1000, tz=UTC).strftime("%Y-%m")


def _descriptor_sha(row: Mapping[str, Any]) -> str:
    return _sha(_canonical_json(dict(row)))


def _completion_path(root: Path, digest: str) -> Path:
    return root / ".complete" / f"{digest}.json"


def _load_product(product: str, root: Path, descriptor_root: Path | None = None) -> ProductInput:
    digest = COMPLETION_SHA256[product]
    completion_path = _completion_path(root, digest)
    _require_safe_path(root / ".complete", regular=False, label="completion directory")
    _require(
        sorted(path.name for path in (root / ".complete").iterdir()) == [f"{digest}.json"],
        "accepted product completion is not sole",
    )
    completion = _read_json(completion_path, digest)
    _require(completion.get("required_product") == product, "completion product changed")
    _require(type(completion.get("partitions")) is list, "completion partition descriptors are absent")
    schema = final_product_schema(product) if product != "binance_usdm_cost_calibration" else pa.schema([])
    if product != "binance_usdm_cost_calibration":
        _require(completion.get("schema_sha256") == product_schema_identity(product), "completion schema identity changed")
        if completion.get("schema") is not None:
            _require(completion["schema"] == _schema_contract(schema), "completion schema contract changed")
    return ProductInput(product, root, descriptor_root or root, completion, completion_path, digest, schema)


def load_inputs(
    *, report_path: Path, sizing_path: Path, holdout_path: Path, product_roots: Mapping[str, Path]
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, ProductInput]]:
    """Authenticate the three authorities and every sole accepted product completion."""
    _require(set(product_roots) == set(COMPLETION_SHA256), "product root arguments are incomplete or foreign")
    report = _read_json(report_path, REPORT_SHA256)
    sizing = _read_json(sizing_path, SIZING_SHA256)
    holdout = _read_json(holdout_path, HOLDOUT_SHA256)
    _require(holdout.get("boundary_id") == HOLDOUT_ID and holdout.get("boundary_utc") == HOLDOUT_UTC, "holdout boundary changed")
    _require(dict(sizing.get("coverage_authority") or {}).get("accepted_source_coverage_gaps") == SOURCE_GAP_ROWS, "sizing source-gap count changed")
    coverage_sizing = dict(sizing.get("coverage_authority") or {})
    for key, schema, expected in (
        (
            "source_gap_component",
            SOURCE_GAP_SCHEMA,
            (SOURCE_GAP_ROWS, SOURCE_GAP_PARTITIONS, SOURCE_GAP_BYTES, SOURCE_GAP_LARGEST_FILE),
        ),
        (
            "typed_gap_membership_component",
            TYPED_GAP_SCHEMA,
            (TYPED_GAP_ROWS, TYPED_GAP_PARTITIONS, TYPED_GAP_BYTES, TYPED_GAP_LARGEST_FILE),
        ),
        (
            "quality_gap_component",
            QUALITY_GAP_SCHEMA,
            (QUALITY_GAP_ROWS, QUALITY_GAP_PARTITIONS, QUALITY_GAP_BYTES, QUALITY_GAP_LARGEST_FILE),
        ),
    ):
        component = dict(coverage_sizing.get(key) or {})
        _require(component.get("schema") == _schema_contract(schema), f"{key} frozen schema changed")
        actual = (
            component.get("projected_rows"),
            component.get("partition_count"),
            component.get("projected_bytes"),
            component.get("largest_partition_bytes"),
        )
        _require(actual == expected, f"{key} frozen allocation changed")
    _require(dict(sizing.get("capacity") or {}).get("catalog_manifest_bundle_bytes") == RELEASE_METADATA_BYTES, "release metadata allocation changed")
    page_size = dict(sizing.get("partitioning") or {}).get("catalog_page_bytes")
    _require(
        page_size == METADATA_PAGE_BYTES
        and sum(METADATA_PAGE_COUNTS.values()) * page_size == METADATA_BUDGET_BYTES
        and RELEASE_METADATA_BYTES - METADATA_BUDGET_BYTES == RELEASE_METADATA_REMAINDER_BYTES,
        "coverage metadata ledger changed",
    )
    price_parent = product_roots[PRODUCT_FUNDING_INDICATIVE_1H].parent
    _require(product_roots[PRODUCT_MARK_INDEX_BASIS_1H].parent == price_parent, "price-state roots do not share their descriptor root")
    products = {
        product: _load_product(product, root, price_parent if product in {PRODUCT_FUNDING_INDICATIVE_1H, PRODUCT_MARK_INDEX_BASIS_1H} else root)
        for product, root in product_roots.items()
    }
    membership = products[PRODUCT_MEMBERSHIP]
    _require(
        membership.completion.get("membership_rows") == ACCEPTED_MEMBERSHIP_IDENTITIES
        and membership.completion.get("detailed_metadata_rows") == DETAILED_MEMBERSHIP_IDENTITIES
        and membership.completion.get("funding_only_rows") == FUNDING_ONLY_MEMBERSHIP_IDENTITIES
        and membership.completion.get("excluded_classifications") == ACCEPTED_REJECTED_MEMBERSHIP_ROWS,
        "membership class allocation changed",
    )
    accepted = prove_coverage_authority(report)["membership"]["accepted"]
    member_symbols = {str(row["symbol"]) for row in accepted}
    seen: set[str] = set()
    for raw in membership.completion["partitions"]:
        _require(type(raw) is dict, "membership partition descriptor is invalid")
        symbol = _safe_component(raw.get("native_symbol"), "membership native symbol")
        _require(symbol in member_symbols and symbol not in seen, "membership completion identity changed")
        seen.add(symbol)
        parquet_path = _resolve_descriptor_path(membership, raw.get("parquet_path"), "membership Parquet path")
        lineage_path = _resolve_descriptor_path(membership, raw.get("lineage_path"), "membership lineage path")
        parquet_fd = _open_regular_path(parquet_path, "membership Parquet path")
        try:
            parquet_sha, parquet_bytes = _hash_fd(parquet_fd)
            lineage_sha, _ = _file_sha(lineage_path)
            _require(parquet_sha == raw.get("parquet_sha256") and lineage_sha == raw.get("lineage_sha256"), "membership descriptor digest changed")
            with os.fdopen(os.dup(parquet_fd), "rb") as source:
                parquet = pq.ParquetFile(source)
                _require(parquet.schema_arrow == membership.schema and parquet.metadata.num_rows == 1 == raw.get("row_count"), "membership partition contract changed")
            _require(_hash_fd(parquet_fd) == (parquet_sha, parquet_bytes), "membership Parquet changed during authentication")
        finally:
            os.close(parquet_fd)
        lineage = _read_json(lineage_path, lineage_sha)
        _require(lineage.get("native_symbol", symbol) == symbol and lineage.get("row_count", 1) == 1, "membership lineage changed")
        if lineage.get("parquet_sha256") is not None:
            _require(lineage["parquet_sha256"] == parquet_sha, "membership lineage Parquet binding changed")
    _require(seen == member_symbols, "membership completion is not the accepted 771-identity set")
    cost = products["binance_usdm_cost_calibration"]
    frozen = cost.completion.get("frozen_source_gaps")
    _require(type(frozen) is dict and frozen.get("row_count") == COST_SOURCE_GAP_ROWS, "cost source-gap descriptor changed")
    cost_gap_path = _resolve_descriptor_path(cost, frozen.get("path"), "cost source-gap path")
    cost_gap_sha, cost_gap_bytes = _file_sha(cost_gap_path)
    _require(cost_gap_sha == frozen.get("sha256") and cost_gap_bytes == frozen.get("bytes"), "cost source-gap artifact changed")
    return report, sizing, holdout, products


def _resolve_descriptor_path(product: ProductInput, value: object, label: str) -> Path:
    relative = _safe_relative(value, label)
    path = product.descriptor_root.joinpath(*relative.parts)
    _require(path.absolute().is_relative_to(product.descriptor_root.absolute()), f"{label} escapes its product root")
    _require_safe_path(path, regular=True, label=label)
    return path


def validate_partition(product: ProductInput, descriptor: Mapping[str, Any]) -> PartitionInput:
    """Authenticate one physical partition and its component-specific lineage."""
    symbol = _safe_component(descriptor.get("native_symbol"), "native symbol")
    month = _safe_component(descriptor.get("utc_month"), "UTC month")
    _parse_month(month)
    rows = descriptor.get("row_count")
    _require(type(rows) is int and rows >= 0, "partition row count is invalid")
    parquet_path = _resolve_descriptor_path(product, descriptor.get("parquet_path"), "Parquet path")
    lineage_path = _resolve_descriptor_path(product, descriptor.get("lineage_path"), "lineage path")
    parquet_fd = _open_regular_path(parquet_path, "Parquet path")
    try:
        parquet_sha, parquet_bytes = _hash_fd(parquet_fd)
        lineage_sha, _lineage_bytes = _file_sha(lineage_path)
        _require(parquet_sha == descriptor.get("parquet_sha256"), "partition Parquet digest changed")
        _require(lineage_sha == descriptor.get("lineage_sha256"), "partition lineage digest changed")
        lineage = _read_json(lineage_path, lineage_sha)
        if "required_product" in lineage:
            _require(lineage["required_product"] == product.product, "partition lineage product changed")
        if "native_symbol" in lineage:
            _require(lineage["native_symbol"] == symbol, "partition lineage symbol changed")
        if "utc_month" in lineage:
            _require(lineage["utc_month"] == month, "partition lineage month changed")
        _require(lineage.get("row_count", rows) == rows, "partition lineage row count changed")
        if lineage.get("parquet_sha256") is not None:
            _require(lineage["parquet_sha256"] == parquet_sha, "partition lineage Parquet binding changed")
        with os.fdopen(os.dup(parquet_fd), "rb") as source:
            parquet = pq.ParquetFile(source)
            _require(parquet.schema_arrow == product.schema, "partition Parquet schema changed")
            _require(parquet.metadata.num_rows == rows, "partition Parquet row count changed")
        _require(_hash_fd(parquet_fd) == (parquet_sha, parquet_bytes), "partition Parquet changed during authentication")
        _require(parquet_bytes > 0, "partition Parquet is empty")
    finally:
        os.close(parquet_fd)
    return PartitionInput(product.product, symbol, month, rows, parquet_path, parquet_sha, lineage_path, lineage_sha, _descriptor_sha(descriptor))


def build_partition_index(products: Mapping[str, ProductInput], members: set[str]) -> Mapping[str, Mapping[tuple[str, str], PartitionInput]]:
    """Build the bounded descriptor index; market rows are not retained."""
    result: dict[str, dict[tuple[str, str], PartitionInput]] = {}
    for product_name in TIMESTAMP_COLUMNS:
        product = products[product_name]
        entries: dict[tuple[str, str], PartitionInput] = {}
        for raw in product.completion["partitions"]:
            _require(type(raw) is dict, "partition descriptor is not an object")
            part = validate_partition(product, raw)
            _require(part.native_symbol in members, "partition names a non-member")
            key = (part.native_symbol, part.utc_month)
            _require(key not in entries, "completion repeats a symbol/month partition")
            entries[key] = part
        result[product_name] = entries
    return result


def validate_row_equations(products: Mapping[str, ProductInput]) -> None:
    """Re-prove each accepted completion's own row equation without mixing units."""
    for name in (PRODUCT_BAR_1H, PRODUCT_TRADE_FLOW_1H):
        row = dict(products[name].completion["row_equation"])
        _require(row["physical_rows"] == row["product_rows"] + row["excluded_rows"] + row["collapsed_rows"], f"{name} row equation failed")
        _require(row["duplicate_rows"] == 0 and row["overlap_rows"] == 0, f"{name} duplicate/overlap fact changed")
    oi = dict(products[PRODUCT_OPEN_INTEREST_5M].completion["totals"])
    _require(oi["physical_source_rows"] == oi["product_rows"] + oi["excluded_source_rows"] + oi["collapsed_identical_source_rows"], "open-interest row equation failed")
    funding = dict(products[PRODUCT_FUNDING_REALIZED].completion["row_equation"])
    _require(funding["physical_source_rows"] == funding["product_rows"] + funding["excluded_source_rows"] + funding["collapsed_identical_rows"], "funding row equation failed")
    _require(funding["inferred_events"] == 0 and funding["conflicting_events"] == 0, "funding observed-event semantics changed")
    for name in (PRODUCT_FUNDING_INDICATIVE_1H, PRODUCT_MARK_INDEX_BASIS_1H):
        row = dict(products[name].completion["row_equation"])
        _require(row["physical_source_rows"] == row["joined_input_rows"] + row["unjoinable_source_rows"] + row["excluded_source_rows"] + row["collapsed_identical_rows"], f"{name} physical row equation failed")
        contribution_count = 1 if name == PRODUCT_FUNDING_INDICATIVE_1H else 3
        _require(row["joined_input_rows"] == contribution_count * row["product_rows"] and row["fabricated_rows"] == 0, f"{name} joined row equation failed")
    liquidation = dict(products[PRODUCT_LIQUIDATION_OBSERVED_DAILY].completion["row_equation"])
    _require(liquidation["inclusive_requested_slots"] == liquidation["product_rows"] + liquidation["missing_daily_slots"], "liquidation request-calendar equation failed")
    _require(liquidation["physical_source_rows"] == liquidation["product_rows"] + liquidation["excluded_source_rows"] + liquidation["collapsed_identical_rows"], "liquidation physical row equation failed")
    _require(liquidation["imputed_rows"] == 0, "liquidation imputation fact changed")
    membership = dict(products[PRODUCT_MEMBERSHIP].completion["row_equation"])
    _require(membership["classifications"] == membership["accepted_membership_rows"] + membership["excluded_classifications"], "membership row equation failed")
    cost = products["binance_usdm_cost_calibration"].completion
    source = dict(cost["source_equation"])
    _require(
        source["objects"] == source["generation0_objects"] + source["recovery_objects"],
        "cost source-object equation failed",
    )
    _require(
        source["physical_rows"]
        == source["retained_rows"] + source["deduplicated_rows"] + source["dropped_rows"],
        "cost source-row equation failed",
    )
    fee = dict(cost["fee_authority"])
    scenario = dict(cost["scenario_policy"])
    _require(
        fee["gap_rows"] == ACCEPTED_MEMBERSHIP_IDENTITIES
        and fee["official_historical_rows"] == 0
        and fee["missing_fee_is_zero"] is False
        and scenario["rows"] == 2
        and scenario["historical_observation"] is False,
        "cost fee-authority equation failed",
    )


def _scan_partition(part: PartitionInput, schema: pa.Schema) -> PartitionScan:
    """Read one authenticated timestamp column and prove native daily cadence."""
    column = TIMESTAMP_COLUMNS[part.product]
    _require(column in schema.names, "product timestamp field is absent")
    counts: Counter[str] = Counter()
    slots: dict[str, set[int]] = defaultdict(set)
    first: int | None = None
    last: int | None = None
    seen = 0
    descriptor = _open_regular_path(part.parquet_path, "partition scan path")
    try:
        authenticated = _hash_fd(descriptor)
        _require(authenticated[0] == part.parquet_sha256, "partition changed before timestamp scan")
        with os.fdopen(os.dup(descriptor), "rb") as source:
            parquet = pq.ParquetFile(source)
            _require(parquet.schema_arrow == schema, "partition scan schema changed")
            _require(parquet.metadata.num_rows == part.row_count, "partition scan row count changed")
            for batch in parquet.iter_batches(batch_size=SIZING_ROW_BATCH, columns=[column], use_threads=False):
                for value in batch.column(0).to_pylist():
                    _require(type(value) is int and value >= 0, "observed timestamp is invalid")
                    _require(_month_text(value) == part.utc_month, "observed timestamp escapes its descriptor month")
                    day = _day_text(value)
                    counts[day] += 1
                    slots[day].add(value)
                    first = value if first is None else min(first, value)
                    last = value if last is None else max(last, value)
                    seen += 1
        _require(_hash_fd(descriptor) == authenticated, "partition changed during timestamp scan")
    finally:
        os.close(descriptor)
    _require(seen == part.row_count, "timestamp scan row count changed")
    distinct = {day: len(values) for day, values in slots.items()}
    duplicates = {day: counts[day] - len(values) for day, values in slots.items()}
    complete: dict[str, bool] = {}
    failures: dict[str, str] = {}
    if part.product in FIXED_DAILY_COUNTS:
        expected = FIXED_DAILY_COUNTS[part.product]
        spacing = 300_000 if part.product == PRODUCT_OPEN_INTEREST_5M else 3_600_000
        for day, values in slots.items():
            ordered = sorted(values)
            has_native_spacing = all(right - left == spacing for left, right in zip(ordered, ordered[1:]))
            complete[day] = len(ordered) == expected and has_native_spacing
            if not complete[day]:
                count_failure = (
                    "duplicate_and_missing_native_slots"
                    if duplicates[day] and len(ordered) < expected
                    else "distinct_native_slot_count_incomplete"
                    if len(ordered) != expected
                    else None
                )
                failures[day] = (
                    f"{count_failure}_and_irregular_native_interval"
                    if count_failure is not None and not has_native_spacing
                    else count_failure or "irregular_native_interval"
                )
    return PartitionScan(
        counts,
        distinct,
        duplicates,
        complete,
        failures,
        first,
        last,
        sum(duplicates.values()),
    )


def _component_rows(rows: Sequence[Mapping[str, Any]], schema: pa.Schema) -> pa.Table:
    try:
        return pa.Table.from_pylist(list(rows), schema=schema)
    except (pa.ArrowInvalid, pa.ArrowTypeError, TypeError, ValueError) as exc:
        raise CoverageNormalizationError("typed coverage row does not satisfy its frozen schema") from exc


class _OutputTree:
    def __init__(self, root: Path, hooks: PublicationHooks) -> None:
        _require(root.name.startswith("."), "coverage output root must be hidden")
        _require_safe_path(root, regular=False, label="output root")
        root_existed = root.exists()
        root.mkdir(parents=True, exist_ok=True)
        if not root_existed:
            _fsync_dir(root.parent)
        self.root = root.resolve(strict=True)
        self.hooks = hooks
        self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        facts = os.fstat(self.fd)
        self.identity = (facts.st_dev, facts.st_ino)
        self.expected: dict[Path, Artifact] = {}
        self.expected_directories: set[Path] = {Path(".staging")}
        self.metadata_bytes = 0
        self.metadata_by_kind: Counter[str] = Counter()
        self._owned_stages: dict[str, tuple[int, int]] = {}
        staging = self._directory((".staging",), create=True, track=True)
        os.close(staging)

    def close(self) -> None:
        for stage in tuple(self._owned_stages):
            self._cleanup_stage(stage)
        os.close(self.fd)

    def _verify_root(self) -> None:
        current = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            facts = os.fstat(current)
            _require((facts.st_dev, facts.st_ino) == self.identity, "held output root was replaced")
        finally:
            os.close(current)

    def _directory(self, parts: Sequence[str], *, create: bool, track: bool) -> int:
        current = os.dup(self.fd)
        traversed: list[str] = []
        try:
            for raw in parts:
                name = _safe_component(raw, "output component")
                if create:
                    try:
                        os.mkdir(name, 0o700, dir_fd=current)
                        os.fsync(current)
                    except FileExistsError:
                        pass
                child = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=current,
                )
                os.close(current)
                current = child
                traversed.append(name)
                if track:
                    self.expected_directories.add(Path(*traversed))
            return current
        except BaseException:
            os.close(current)
            raise

    def _stage_matches(self, staging: int, name: str) -> bool:
        expected = self._owned_stages.get(name)
        if expected is None:
            return False
        try:
            facts = os.stat(name, dir_fd=staging, follow_symlinks=False)
        except FileNotFoundError:
            return False
        return stat.S_ISREG(facts.st_mode) and (facts.st_dev, facts.st_ino) == expected

    def _cleanup_stage(self, name: str) -> None:
        staging = self._directory((".staging",), create=False, track=True)
        try:
            if self._stage_matches(staging, name):
                os.unlink(name, dir_fd=staging)
                os.fsync(staging)
            self._owned_stages.pop(name, None)
        finally:
            os.close(staging)

    def _verify_artifact_fd(self, descriptor: int, artifact: Artifact) -> None:
        _require(stat.S_ISREG(os.fstat(descriptor).st_mode), "published object is not regular")
        _require(_hash_fd(descriptor) == (artifact.sha256, artifact.byte_size), "published object bytes changed")
        if artifact.schema is not None:
            with os.fdopen(os.dup(descriptor), "rb") as source:
                parquet = pq.ParquetFile(source)
                _require(parquet.schema_arrow == artifact.schema, "published Parquet schema changed")
                _require(parquet.metadata.num_rows == artifact.row_count, "published Parquet row count changed")

    def publish(
        self,
        body: bytes,
        *,
        directory: str,
        suffix: str,
        kind: str,
        row_count: int | None,
        metadata: bool,
        schema: pa.Schema | None = None,
        precommit: Callable[[], None] | None = None,
    ) -> Artifact:
        if metadata:
            _require(self.metadata_bytes + len(body) <= METADATA_BUDGET_BYTES, "coverage metadata budget exceeded")
        digest = _sha(body)
        directory_parts = _safe_relative(directory, "output directory").parts
        destination = self._directory(directory_parts, create=True, track=True)
        staging = self._directory((".staging",), create=False, track=True)
        name = f"{digest}.{_safe_component(suffix, 'output suffix')}"
        stage = f"{_safe_component(kind, 'output kind')}-{uuid.uuid4().hex}.tmp"
        descriptor = os.open(
            stage,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=staging,
        )
        stage_facts = os.fstat(descriptor)
        self._owned_stages[stage] = (stage_facts.st_dev, stage_facts.st_ino)
        temporary = self.root / ".staging" / stage
        final = self.root.joinpath(*directory_parts, name)
        artifact = Artifact(final, digest, len(body), row_count, False, schema)
        try:
            view = memoryview(body)
            while view:
                written = os.write(descriptor, view)
                _require(written > 0, "temporary output write made no progress")
                view = view[written:]
            os.fsync(descriptor)
            if self.hooks.before_publish is not None:
                self.hooks.before_publish(kind, temporary, final)
            # Completion's dependency/inventory proof must follow the last caller
            # hook, while the verified completion is still an owned staging file.
            if precommit is not None:
                precommit()
            self._verify_root()
            _require(self._stage_matches(staging, stage), "held staged object was replaced")
            _require(_hash_fd(descriptor) == (digest, len(body)), "held staged bytes changed")
            try:
                _rename_noreplace_at(staging, stage, destination, name)
                self._owned_stages.pop(stage, None)
                os.fsync(destination)
                os.fsync(staging)
                reused = False
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                reused = True
            artifact = Artifact(final, digest, len(body), row_count, reused, schema)
            winner = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=destination)
            try:
                self._verify_artifact_fd(winner, artifact)
                _require(_hash_fd(descriptor) == _hash_fd(winner), "published or replayed bytes differ")
            finally:
                os.close(winner)
            if reused:
                self._cleanup_stage(stage)
            self._verify_root()
        except BaseException:
            self._cleanup_stage(stage)
            raise
        finally:
            os.close(descriptor)
            os.close(staging)
            os.close(destination)
        self.expected[final.relative_to(self.root)] = artifact
        if metadata:
            self.metadata_bytes += len(body)
            self.metadata_by_kind[kind] += len(body)
        return artifact

    def publish_json(self, value: Mapping[str, Any], *, directory: str, kind: str) -> Artifact:
        return self.publish(_canonical_json(value), directory=directory, suffix="json", kind=kind, row_count=None, metadata=True)

    def publish_table(self, table: pa.Table, *, directory: str, kind: str) -> Artifact:
        sink = pa.BufferOutputStream()
        pq.write_table(table, sink, compression=PARQUET_COMPRESSION, compression_level=PARQUET_COMPRESSION_LEVEL, version=PARQUET_VERSION, row_group_size=SIZING_ROW_BATCH, use_dictionary=True, write_statistics=False, store_schema=True)
        return self.publish(sink.getvalue().to_pybytes(), directory=directory, suffix="parquet", kind=kind, row_count=table.num_rows, metadata=False, schema=table.schema)

    def _inventory(self) -> tuple[set[Path], set[Path]]:
        files: set[Path] = set()
        directories: set[Path] = set()

        def walk(directory: int, prefix: tuple[str, ...]) -> None:
            for name in sorted(os.listdir(directory)):
                _safe_component(name, "output inventory component")
                facts = os.stat(name, dir_fd=directory, follow_symlinks=False)
                relative = Path(*prefix, name)
                if stat.S_ISDIR(facts.st_mode):
                    child = os.open(
                        name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                        dir_fd=directory,
                    )
                    directories.add(relative)
                    try:
                        walk(child, (*prefix, name))
                    finally:
                        os.close(child)
                elif stat.S_ISREG(facts.st_mode):
                    files.add(relative)
                else:
                    raise CoverageNormalizationError("output contains a non-regular object")

        walk(self.fd, ())
        self._verify_root()
        return files, directories

    def audit(self, prospective_completion: tuple[Path, bytes] | None = None) -> None:
        actual_files, actual_directories = self._inventory()
        expected_files = set(self.expected)
        staging = self._directory((".staging",), create=False, track=False)
        try:
            for stage in self._owned_stages:
                _require(self._stage_matches(staging, stage), "held staged object was replaced")
                expected_files.add(Path(".staging") / stage)
        finally:
            os.close(staging)
        allowed_directories = set(self.expected_directories)
        prospective_relative: Path | None = None
        if prospective_completion is not None:
            prospective_relative, body = prospective_completion
            allowed_directories.add(prospective_relative.parent)
            if prospective_relative in actual_files:
                expected_files.add(prospective_relative)
                descriptor = _open_regular_path(self.root / prospective_relative, "existing completion")
                try:
                    _require(_hash_fd(descriptor) == (_sha(body), len(body)), "existing completion bytes differ")
                finally:
                    os.close(descriptor)
        _require(actual_files == expected_files, "output contains a foreign, stale, or incomplete artifact")
        _require(
            frozenset(actual_directories)
            in {
                frozenset(allowed_directories),
                frozenset(allowed_directories - {Path(".complete")}),
            },
            "output contains an unexpected directory",
        )
        for relative, artifact in self.expected.items():
            _require(relative.stem == artifact.sha256, "output address does not match its digest")
            descriptor = _open_regular_path(self.root / relative, "published inventory object")
            try:
                self._verify_artifact_fd(descriptor, artifact)
            finally:
                os.close(descriptor)


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rename_noreplace_at(source_dir: int, source: str, target_dir: int, target: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    function = getattr(libc, "renameat2", None)
    _require(function is not None, "renameat2 is unavailable")
    function.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    function.restype = ctypes.c_int
    if function(source_dir, os.fsencode(source), target_dir, os.fsencode(target), RENAME_NOREPLACE):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), target)


def _rename_noreplace(source: Path, target: Path) -> bool:
    source_dir = os.open(source.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    target_dir = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        try:
            _rename_noreplace_at(source_dir, source.name, target_dir, target.name)
            return True
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                return False
            raise
    finally:
        os.close(source_dir)
        os.close(target_dir)


def _publish_gap_group(tree: _OutputTree, *, component: str, product: str, symbol: str, month: str, rows: Sequence[Mapping[str, Any]], schema: pa.Schema, upstream: Sequence[Mapping[str, Any]]) -> tuple[Artifact, Artifact]:
    table = _component_rows(rows, schema)
    part = tree.publish_table(table, directory=f".{component}/{product}/{symbol}/{month}", kind=component)
    lineage = tree.publish_json(
        {
            "document_type": f"binance_usdm_coverage_{component}_lineage",
            "schema_version": 1,
            "component": component,
            "required_product": product,
            "native_symbol": symbol,
            "utc_month": month,
            "row_count": len(rows),
            "parquet_sha256": part.sha256,
            "schema": _schema_contract(schema),
            "upstream": list(upstream),
        },
        directory=f".{component}-lineage/{product}/{symbol}/{month}",
        kind=f"{component}-lineage",
    )
    return part, lineage


def publish_source_and_typed_gaps(tree: _OutputTree, authority: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    source_rows = list(authority["source_gaps"])
    typed_rows = list(authority["typed_gap_memberships"])
    _require(len(source_rows) == SOURCE_GAP_ROWS == ACCEPTED_SOURCE_COVERAGE_GAPS, "source-gap row count changed")
    _require(len(typed_rows) == TYPED_GAP_ROWS == ACCEPTED_TYPED_GAP_MEMBERSHIPS, "typed-gap row count changed")
    manifests: dict[str, list[dict[str, Any]]] = {"source_gap": [], "typed_gap": []}
    sizes = {"source_gap": 0, "typed_gap": 0}
    largest = {"source_gap": 0, "typed_gap": 0}
    grouped_source: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for raw in source_rows:
        row = {**native_identity(str(raw["native_symbol"])), **dict(raw)}
        grouped_source[(str(row["required_product"]), str(row["native_symbol"]))].append(row)
    _require(len(grouped_source) == SOURCE_GAP_PARTITIONS, "source-gap partition count changed")
    for (product, symbol), rows in sorted(grouped_source.items()):
        part, lineage = _publish_gap_group(tree, component="source-gaps", product=_safe_component(product, "source-gap product"), symbol=_safe_component(symbol, "source-gap symbol"), month="authority", rows=rows, schema=SOURCE_GAP_SCHEMA, upstream=[{"report_sha256": REPORT_SHA256, "rows_sha256": _sha(_canonical_json(rows))}])
        sizes["source_gap"] += part.byte_size
        largest["source_gap"] = max(largest["source_gap"], part.byte_size)
        manifests["source_gap"].append({"required_product": product, "native_symbol": symbol, "row_count": len(rows), "parquet_sha256": part.sha256, "parquet_bytes": part.byte_size, "lineage_sha256": lineage.sha256, "lineage_bytes": lineage.byte_size})
    for raw in sorted(typed_rows, key=lambda item: (str(item["required_product"]), str(item["native_symbol"]))):
        product, symbol = str(raw["required_product"]), str(raw["native_symbol"])
        row = {**native_identity(symbol), **dict(raw)}
        part, lineage = _publish_gap_group(tree, component="typed-gaps", product=_safe_component(product, "typed-gap product"), symbol=_safe_component(symbol, "typed-gap symbol"), month="authority", rows=[row], schema=TYPED_GAP_SCHEMA, upstream=[{"report_sha256": REPORT_SHA256, "row_sha256": _sha(_canonical_json(raw))}])
        sizes["typed_gap"] += part.byte_size
        largest["typed_gap"] = max(largest["typed_gap"], part.byte_size)
        manifests["typed_gap"].append({"required_product": product, "native_symbol": symbol, "row_count": 1, "parquet_sha256": part.sha256, "parquet_bytes": part.byte_size, "lineage_sha256": lineage.sha256, "lineage_bytes": lineage.byte_size})
    _require(len(manifests["typed_gap"]) == TYPED_GAP_PARTITIONS, "typed-gap partition count changed")
    _require(sizes["source_gap"] <= SOURCE_GAP_BYTES and largest["source_gap"] <= SOURCE_GAP_LARGEST_FILE, "source-gap byte bound exceeded")
    _require(sizes["typed_gap"] <= TYPED_GAP_BYTES and largest["typed_gap"] <= TYPED_GAP_LARGEST_FILE, "typed-gap byte bound exceeded")
    return manifests["source_gap"], manifests["typed_gap"], {**sizes, "source_gap_largest": largest["source_gap"], "typed_gap_largest": largest["typed_gap"]}


def _quality_descriptors(product: ProductInput) -> Iterator[Mapping[str, Any]]:
    single = product.completion.get("quality_gap_artifact")
    if isinstance(single, dict):
        yield single
    many = product.completion.get("quality_gap_artifacts")
    if isinstance(many, list):
        yield from (row for row in many if isinstance(row, dict))
    if product.product == PRODUCT_LIQUIDATION_OBSERVED_DAILY:
        gaps = product.completion.get("gaps")
        _require(type(gaps) is list, "liquidation gap descriptors are absent")
        # The 202 unmapped-symbol authority rows are already represented by the frozen
        # typed-gap-membership component.  They are not normalized observed quality gaps.
        yield from (
            row
            for row in gaps
            if isinstance(row, dict) and row.get("kind") != "coinalyze_symbol_unmapped"
        )


def publish_quality_gaps(tree: _OutputTree, products: Mapping[str, ProductInput], members: set[str]) -> tuple[list[dict[str, Any]], dict[str, int], Mapping[tuple[str, str], int]]:
    manifest: list[dict[str, Any]] = []
    missing_counts: dict[tuple[str, str], int] = defaultdict(int)
    total_bytes = total_rows = largest = 0
    published_keys: set[tuple[str, str, str]] = set()

    def publish_group(
        key: tuple[str, str, str],
        rows: Sequence[Mapping[str, Any]],
        parquet_sha: str,
        lineage_sha: str,
        descriptor_sha: str,
        first_source_row_ordinal: int,
        last_source_row_ordinal: int,
    ) -> None:
        nonlocal total_bytes, total_rows, largest
        product, symbol, month = key
        _require(key not in published_keys, "two upstream quality artifacts repeat a product/symbol/month")
        published_keys.add(key)
        part, lineage = _publish_gap_group(
            tree,
            component="quality-gaps",
            product=_safe_component(product, "quality-gap product"),
            symbol=_safe_component(symbol, "quality-gap symbol"),
            month=month,
            rows=rows,
            schema=QUALITY_GAP_SCHEMA,
            upstream=[
                {
                    "descriptor_sha256": descriptor_sha,
                    "parquet_sha256": parquet_sha,
                    "lineage_sha256": lineage_sha,
                    "first_source_row_ordinal": first_source_row_ordinal,
                    "last_source_row_ordinal": last_source_row_ordinal,
                    "source_row_count": last_source_row_ordinal - first_source_row_ordinal + 1,
                }
            ],
        )
        total_rows += len(rows)
        total_bytes += part.byte_size
        largest = max(largest, part.byte_size)
        missing_counts[(product, symbol)] += sum(int(row["expected_grid_count"]) for row in rows)
        manifest.append({"required_product": product, "native_symbol": symbol, "utc_month": month, "row_count": len(rows), "parquet_sha256": part.sha256, "parquet_bytes": part.byte_size, "lineage_sha256": lineage.sha256, "lineage_bytes": lineage.byte_size})

    for product_name in TIMESTAMP_COLUMNS:
        product = products[product_name]
        for descriptor in _quality_descriptors(product):
            parquet_path = _resolve_descriptor_path(product, descriptor.get("parquet_path"), "quality-gap Parquet path")
            lineage_path = _resolve_descriptor_path(product, descriptor.get("lineage_path"), "quality-gap lineage path")
            parquet_sha, parquet_bytes = _file_sha(parquet_path)
            lineage_sha, _ = _file_sha(lineage_path)
            _require(parquet_sha == descriptor.get("parquet_sha256") and lineage_sha == descriptor.get("lineage_sha256"), "quality-gap descriptor digest changed")
            lineage = _read_json(lineage_path, lineage_sha)
            _require(lineage.get("row_count") == descriptor.get("row_count"), "quality-gap lineage row count changed")
            lineage_parquet_sha = lineage.get("parquet_sha256", lineage.get("quality_gap_parquet_sha256"))
            if lineage_parquet_sha is not None:
                _require(lineage_parquet_sha == parquet_sha, "quality-gap lineage Parquet binding changed")
            descriptor_sha = _descriptor_sha(descriptor)
            seen = 0
            current_key: tuple[str, str, str] | None = None
            current_rows: list[dict[str, Any]] = []
            current_first_ordinal = 0
            parquet_fd = _open_regular_path(parquet_path, "quality-gap Parquet path")
            try:
                _require(_hash_fd(parquet_fd) == (parquet_sha, parquet_bytes), "quality-gap Parquet changed before scan")
                with os.fdopen(os.dup(parquet_fd), "rb") as source:
                    parquet = pq.ParquetFile(source)
                    _require(parquet.schema_arrow == QUALITY_GAP_SCHEMA, "quality-gap schema changed")
                    _require(parquet.metadata.num_rows == descriptor.get("row_count"), "quality-gap Parquet row count changed")
                    for batch in parquet.iter_batches(batch_size=SIZING_ROW_BATCH, use_threads=False):
                        for row in batch.to_pylist():
                            key = (str(row["required_product"]), str(row["native_symbol"]), str(row["utc_month"]))
                            _require(key[0] == product_name and key[1] in members, "quality-gap identity conflicts with its completion")
                            _parse_month(key[2])
                            start_ms, end_ms = row["missing_run_start_ms"], row["missing_run_end_ms"]
                            _require(
                                type(row["expected_grid_count"]) is int and row["expected_grid_count"] >= 0,
                                "quality-gap expected count is invalid",
                            )
                            _require(
                                (start_ms is None and end_ms is None)
                                or (
                                    type(start_ms) is int
                                    and type(end_ms) is int
                                    and start_ms <= end_ms
                                ),
                                "quality-gap inclusive endpoints are invalid",
                            )
                            if current_key is not None and key != current_key:
                                _require(key > current_key, "upstream quality-gap rows are not in deterministic partition order")
                                publish_group(
                                    current_key,
                                    current_rows,
                                    parquet_sha,
                                    lineage_sha,
                                    descriptor_sha,
                                    current_first_ordinal,
                                    seen - 1,
                                )
                                current_rows = []
                                current_first_ordinal = seen
                            current_key = key
                            current_rows.append(row)
                            seen += 1
                _require(_hash_fd(parquet_fd) == (parquet_sha, parquet_bytes), "quality-gap Parquet changed during scan")
            finally:
                os.close(parquet_fd)
            if current_key is not None:
                publish_group(
                    current_key,
                    current_rows,
                    parquet_sha,
                    lineage_sha,
                    descriptor_sha,
                    current_first_ordinal,
                    seen - 1,
                )
            _require(seen == descriptor.get("row_count"), "quality-gap scan row count changed")
            del current_rows
    _require(total_rows <= QUALITY_GAP_ROWS and len(manifest) <= QUALITY_GAP_PARTITIONS, "quality-gap allocation count exceeded")
    _require(total_bytes <= QUALITY_GAP_BYTES and largest <= QUALITY_GAP_LARGEST_FILE, "quality-gap byte bound exceeded")
    return manifest, {"quality_gap": total_bytes, "quality_gap_largest": largest, "quality_gap_rows": total_rows}, missing_counts


EXCLUSION_REASON_DICTIONARY: Mapping[int, str] = {
    0: "no_observed_row_in_accepted_partition;source_availability_not_inferred",
    1: "no_observed_settlement;expected_count_unknown",
    2: "no_observed_liquidation_row;not_zero;source_censorship_retained",
    3: "typed_source_unavailable",
    4: "no_accepted_partition_observation;source_availability_unknown",
    5: "partial_fixed_cadence_day;distinct_native_slot_count_incomplete",
    6: "partial_fixed_cadence_day;duplicate_and_missing_native_slots",
    7: "partial_fixed_cadence_day;irregular_native_interval",
    8: "partial_fixed_cadence_day;distinct_native_slot_count_incomplete;irregular_native_interval",
    9: "partial_fixed_cadence_day;duplicate_and_missing_native_slots;irregular_native_interval",
}

CADENCE_FAILURE_CODES = {
    "distinct_native_slot_count_incomplete": 5,
    "duplicate_and_missing_native_slots": 6,
    "irregular_native_interval": 7,
    "distinct_native_slot_count_incomplete_and_irregular_native_interval": 8,
    "duplicate_and_missing_native_slots_and_irregular_native_interval": 9,
}


def _availability_reason(product: str, symbol: str, month: str, index: Mapping[str, Mapping[tuple[str, str], PartitionInput]], typed: set[tuple[str, str]]) -> int:
    if (symbol, month) in index.get(product, {}):
        if product == PRODUCT_FUNDING_REALIZED:
            return 1
        if product == PRODUCT_LIQUIDATION_OBSERVED_DAILY:
            return 2
        return 0
    if (product, symbol) in typed:
        return 3
    return 4


def publish_reports(
    tree: _OutputTree,
    *,
    products: Mapping[str, ProductInput],
    index: Mapping[str, Mapping[tuple[str, str], PartitionInput]],
    membership: Sequence[Mapping[str, Any]],
    typed_rows: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    quality_missing_counts: Mapping[tuple[str, str], int],
    quality_gap_references: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    members = sorted(str(row["symbol"]) for row in membership)
    quality_references = quality_gap_references or {}
    typed = {(str(row["required_product"]), str(row["native_symbol"])) for row in typed_rows}
    months = {month for entries in index.values() for _symbol, month in entries}
    for row in source_rows:
        for field in ("first_observed_period", "last_observed_period", "family_first_observed_period", "family_last_observed_period", "onboard_period", "close_period"):
            value = str(row.get(field) or "")
            if len(value) == 7:
                _parse_month(value)
                months.add(value)
    for row in membership:
        evidence = row.get("evidence")
        _require(type(evidence) is list and bool(evidence), "accepted membership evidence is absent")
        for record in evidence:
            _require(type(record) is dict, "accepted membership evidence is malformed")
            for field in ("onboard_ms", "closed_observed_ms"):
                value = record.get(field)
                if value is not None:
                    _require(type(value) is int and value >= 0, "membership temporal bound is invalid")
                    months.add(_month_text(value))
    _require(bool(months), "historical reporting domain is empty")
    first_month, last_month = min(months), max(months)
    domain = tuple(_month_range(first_month, last_month))
    report_manifest: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {
        symbol: {product: {"observed_count": 0, "first_observed_ms": None, "last_observed_ms": None, "duplicate_timestamps": 0, "descriptors": []} for product in SUMMARY_PRODUCTS}
        for symbol in members
    }
    for symbol in members:
        summaries[symbol]["binance_usdm_cost_calibration"].update(
            {"component_counts": Counter(), "source_days": defaultdict(set)}
        )
    for raw in products["binance_usdm_cost_calibration"].completion["partitions"]:
        _require(type(raw) is dict, "cost partition descriptor is malformed")
        symbol = str(raw.get("native_symbol") or "")
        component = _safe_component(raw.get("component"), "cost component")
        rows = raw.get("row_count")
        _require(type(rows) is int and rows >= 0, "cost descriptor row count is invalid")
        lineage_path = _resolve_descriptor_path(
            products["binance_usdm_cost_calibration"],
            raw.get("lineage_path"),
            "cost lineage path",
        )
        lineage, lineage_bytes = _read_json_artifact(lineage_path, str(raw.get("lineage_sha256") or ""))
        _require(lineage_bytes == raw.get("lineage_bytes"), "cost lineage size changed")
        _require(
            lineage.get("component", component) == component
            and lineage.get("native_symbol", symbol) == symbol
            and lineage.get("row_count", rows) == rows,
            "cost lineage identity changed",
        )
        lineage_parquet_sha = lineage.get("parquet_sha256")
        if lineage_parquet_sha is not None:
            _require(lineage_parquet_sha == raw.get("parquet_sha256"), "cost lineage Parquet binding changed")
        if symbol in summaries:
            cost_summary = summaries[symbol]["binance_usdm_cost_calibration"]
            cost_summary["component_counts"][component] += rows
            for source in lineage.get("raw_objects") or ():
                _require(type(source) is dict, "cost lineage source object is malformed")
                source_day = source.get("economic_day")
                if source_day is not None:
                    _require(type(source_day) is str and len(source_day) == 10, "cost source day is malformed")
                    try:
                        canonical_day = date.fromisoformat(source_day).isoformat()
                    except ValueError as exc:
                        raise CoverageNormalizationError("cost source day is malformed") from exc
                    _require(canonical_day == source_day, "cost source day is not canonical")
                    cost_summary["source_days"][component].add(source_day)
            cost_summary["descriptors"].append(
                {
                    "component": component,
                    "utc_month": str(raw.get("utc_month") or ""),
                    "row_count": rows,
                    "parquet_bytes": raw.get("parquet_bytes"),
                    "lineage_bytes": lineage_bytes,
                    "descriptor_sha256": _descriptor_sha(raw),
                    "parquet_sha256": raw.get("parquet_sha256"),
                    "lineage_sha256": raw.get("lineage_sha256"),
                    "authority": "pinned_cost_completion_descriptor;market_values_not_rescanned",
                }
            )
    alignment_hash = hashlib.sha256()
    predicate_hashes = {"observed": hashlib.sha256(), "full": hashlib.sha256()}
    totals = {"reports": 0, "days": 0, "observed": 0, "full": 0, "maximum_loaded_observations": 0}
    for symbol in members:
        for month in domain:
            day_counts: dict[str, Counter[str]] = {}
            day_cadence: dict[str, Mapping[str, bool]] = {}
            day_cadence_failures: dict[str, Mapping[str, str]] = {}
            for product_name in ALIGNMENT_PRODUCTS:
                part = index[product_name].get((symbol, month))
                if part is None:
                    day_counts[product_name] = Counter()
                    day_cadence[product_name] = {}
                    day_cadence_failures[product_name] = {}
                    continue
                scan = _scan_partition(part, products[product_name].schema)
                totals["maximum_loaded_observations"] = max(totals["maximum_loaded_observations"], part.row_count)
                day_counts[product_name] = scan.observed_by_day
                day_cadence[product_name] = scan.cadence_complete_by_day
                day_cadence_failures[product_name] = scan.cadence_failure_by_day
                summary = summaries[symbol][product_name]
                summary["observed_count"] += part.row_count
                if scan.first_observed_ms is not None:
                    summary["first_observed_ms"] = scan.first_observed_ms if summary["first_observed_ms"] is None else min(summary["first_observed_ms"], scan.first_observed_ms)
                    summary["last_observed_ms"] = scan.last_observed_ms if summary["last_observed_ms"] is None else max(summary["last_observed_ms"], scan.last_observed_ms)
                summary["duplicate_timestamps"] += scan.duplicate_timestamps
                summary["descriptors"].append({"utc_month": month, "descriptor_sha256": part.descriptor_sha256, "parquet_sha256": part.parquet_sha256, "lineage_sha256": part.lineage_sha256})
            days: list[list[Any]] = []
            month_observed = month_full = 0
            for day in _month_days(month):
                day_name = day.isoformat()
                counts = [day_counts[product].get(day_name, 0) for product in ALIGNMENT_PRODUCTS]
                present = [count > 0 for count in counts]
                complete = [
                    day_cadence[PRODUCT_BAR_1H].get(day_name, False),
                    day_cadence[PRODUCT_OPEN_INTEREST_5M].get(day_name, False),
                    None,
                    day_cadence[PRODUCT_MARK_INDEX_BASIS_1H].get(day_name, False),
                    None,
                ]
                exclusions: list[int | None] = []
                for product, presence in zip(ALIGNMENT_PRODUCTS, present, strict=True):
                    if not presence:
                        exclusions.append(_availability_reason(product, symbol, month, index, typed))
                    elif product in FIXED_DAILY_COUNTS and not day_cadence[product].get(day_name, False):
                        exclusions.append(CADENCE_FAILURE_CODES[day_cadence_failures[product][day_name]])
                    else:
                        exclusions.append(None)
                observed = all(present)
                full = complete[0] is True and complete[1] is True and complete[3] is True and present[2] and present[4]
                row = [day_name, counts, present, complete, exclusions, observed, full]
                days.append(row)
                encoded = _canonical_json([symbol, row])
                alignment_hash.update(encoded)
                totals["days"] += 1
                if observed:
                    predicate_hashes["observed"].update(encoded)
                    totals["observed"] += 1
                    month_observed += 1
                if full:
                    predicate_hashes["full"].update(encoded)
                    totals["full"] += 1
                    month_full += 1
            document = {
                "document_type": "binance_usdm_coverage_daily_alignment",
                "schema_version": 1,
                "native_symbol": symbol,
                "utc_month": month,
                "field_order": ["utc_date", "observed_counts", "observed_presence", "fixed_cadence_complete", "exclusion_reasons", "five_product_observed_intersection", "full_cadence_with_event_presence"],
                "product_order": list(ALIGNMENT_PRODUCTS),
                "exclusion_reason_dictionary": {str(key): value for key, value in EXCLUSION_REASON_DICTIONARY.items()},
                "semantics": {"funding_expected_count": None, "funding_absence": "no_observed_settlement;expected_count_unknown", "liquidation": "observed_and_censored_never_complete", "availability": "unknown_not_a_causal_vintage", "fixed_daily_counts": dict(FIXED_DAILY_COUNTS)},
                "days": days,
                "counts": {"days": len(days), "five_product_observed_intersection": month_observed, "full_cadence_with_event_presence": month_full},
            }
            artifact = tree.publish_json(document, directory=f".daily/{symbol}/{month}", kind="daily-alignment")
            report_manifest.append({"native_symbol": symbol, "utc_month": month, "sha256": artifact.sha256, "bytes": artifact.byte_size, **document["counts"]})
            totals["reports"] += 1
        # Scan non-alignment products for their per-instrument summaries.
        for product_name in (PRODUCT_TRADE_FLOW_1H, PRODUCT_FUNDING_INDICATIVE_1H):
            for month in domain:
                part = index[product_name].get((symbol, month))
                if part is None:
                    continue
                scan = _scan_partition(part, products[product_name].schema)
                totals["maximum_loaded_observations"] = max(totals["maximum_loaded_observations"], part.row_count)
                summary = summaries[symbol][product_name]
                summary["observed_count"] += part.row_count
                if scan.first_observed_ms is not None:
                    summary["first_observed_ms"] = scan.first_observed_ms if summary["first_observed_ms"] is None else min(summary["first_observed_ms"], scan.first_observed_ms)
                    summary["last_observed_ms"] = scan.last_observed_ms if summary["last_observed_ms"] is None else max(summary["last_observed_ms"], scan.last_observed_ms)
                summary["duplicate_timestamps"] += scan.duplicate_timestamps
                summary["descriptors"].append({"utc_month": part.utc_month, "descriptor_sha256": part.descriptor_sha256, "parquet_sha256": part.parquet_sha256, "lineage_sha256": part.lineage_sha256})
    summary_manifest: list[dict[str, Any]] = []
    source_by_identity: dict[tuple[str, str], list[str]] = defaultdict(list)
    source_context: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        symbol = str(row["native_symbol"])
        identity = (str(row["required_product"]), symbol)
        row_sha = _sha(_canonical_json({**native_identity(symbol), **dict(row)}))
        source_by_identity[identity].append(row_sha)
        source_context[identity].append(
            {
                "row_sha256": row_sha,
                "gap_kind": row.get("gap_kind"),
                "gap_status": row.get("gap_status"),
                "first_observed_period": row.get("first_observed_period"),
                "last_observed_period": row.get("last_observed_period"),
                "family_first_observed_period": row.get("family_first_observed_period"),
                "family_last_observed_period": row.get("family_last_observed_period"),
                "onboard_period": row.get("onboard_period"),
                "close_period": row.get("close_period"),
                "missing_months": row.get("missing_months"),
                "semantics": "qualification_gap_context;not_a_current_missing_observation",
            }
        )
    for symbol in members:
        entries: list[dict[str, Any]] = []
        for product_name in SUMMARY_PRODUCTS:
            value = summaries[symbol][product_name]
            if product_name == "binance_usdm_cost_calibration":
                value.update({"observed_count": None, "first_observed_ms": None, "last_observed_ms": None, "duplicate_timestamps": None})
                value["descriptors"].append({"completion_sha256": COMPLETION_SHA256[product_name], "frozen_source_gap_sha256": products[product_name].completion["frozen_source_gaps"]["sha256"]})
            missing = quality_missing_counts.get((product_name, symbol), 0)
            fixed = product_name in FIXED_DAILY_COUNTS
            request_calendar = product_name == PRODUCT_LIQUIDATION_OBSERVED_DAILY
            established = value["observed_count"] not in (None, 0) or missing > 0
            expected = value["observed_count"] + missing if established and (fixed or request_calendar) else None
            entries.append({
                "required_product": product_name,
                "time_precision": TIME_PRECISION[product_name],
                "observed_count": value["observed_count"],
                "observed_count_unit": "normalized_rows" if product_name != "binance_usdm_cost_calibration" else "unavailable_per_instrument;component_counts_only",
                "expected_count": expected,
                "missing_count": missing if established and (fixed or request_calendar) else None,
                "expected_count_basis": ("accepted_observed_rows_plus_normalized_quality_gap_expected_grid_count" if established and fixed else "authenticated_inclusive_request_calendar;never_a_completeness_claim" if established and request_calendar else None),
                "first_observed_ms": value["first_observed_ms"],
                "last_observed_ms": value["last_observed_ms"],
                "duplicate_timestamps": value["duplicate_timestamps"],
                "component_counts": (
                    [
                        {
                            "component": component,
                            "row_count": count,
                            "unit": {
                                "retained_book_depth": "normalized_book_depth_rows",
                                "retained_book_ticker": "normalized_book_ticker_rows",
                                "fee_authority_gap": "authority_gap_rows",
                            }.get(component, "component_native_rows"),
                        }
                        for component, count in sorted(value.get("component_counts", {}).items())
                    ]
                    if product_name == "binance_usdm_cost_calibration"
                    else None
                ),
                "source_day_extrema": (
                    [
                        {"component": component, "first_source_day": min(days), "last_source_day": max(days)}
                        for component, days in sorted(value.get("source_days", {}).items())
                        if days
                    ]
                    if product_name == "binance_usdm_cost_calibration"
                    else None
                ),
                "non_instrument_cost_counts": (
                    {"official_historical_fee_rows": 0, "scenario_policy_rows": 2}
                    if product_name == "binance_usdm_cost_calibration"
                    else None
                ),
                "source_gap_row_sha256": sorted(source_by_identity[(product_name, symbol)]),
                "qualification_source_gap_context": sorted(
                    source_context[(product_name, symbol)],
                    key=lambda row: str(row["row_sha256"]),
                ),
                "quality_gap_partitions": list(quality_references.get((product_name, symbol), ())),
                "fee_authority_gap_reference": (
                    {"present": True, "authority": "accepted_cost_completion", "historical_fee_observation": False}
                    if product_name == "binance_usdm_cost_calibration"
                    else None
                ),
                "input_descriptors": value["descriptors"],
                "source_revisions": "retained_in_referenced_partition_lineages;no_availability_vintage_inferred",
            })
        document = {"document_type": "binance_usdm_instrument_coverage_summary", "schema_version": 1, **native_identity(symbol), "reporting_domain": {"first_utc_month": first_month, "last_utc_month": last_month}, "products": entries}
        artifact = tree.publish_json(document, directory=f".summary/{symbol}", kind="coverage-summary")
        summary_manifest.append({"native_symbol": symbol, "sha256": artifact.sha256, "bytes": artifact.byte_size})
    expected_reports = len(members) * len(domain)
    _require(totals["reports"] == expected_reports, "daily report matrix is incomplete")
    return report_manifest, summary_manifest, {
        "historical_domain": {
            "first_utc_month": first_month,
            "last_utc_month": last_month,
            "month_count": len(domain),
            "basis": "accepted_source_membership_bounds_and_actual_product_ranges",
        },
        "daily_report_equation": {
            "accepted_membership_identities": len(members),
            "historical_utc_months": len(domain),
            "expected_partitions": expected_reports,
            "published_partitions": totals["reports"],
        },
        "aligned_day_rows": totals["days"],
        "daily_report_partitions": totals["reports"],
        "five_product_observed_day_count": totals["observed"],
        "five_product_observed_day_sha256": predicate_hashes["observed"].hexdigest(),
        "full_cadence_day_count": totals["full"],
        "full_cadence_day_sha256": predicate_hashes["full"].hexdigest(),
        "aligned_days_sha256": alignment_hash.hexdigest(),
        "maximum_loaded_symbol_month_observations": totals["maximum_loaded_observations"],
        "memory_rule": "one product/symbol/month timestamp column at a time; descriptor indexes and incremental summaries only",
    }


def _publish_manifest(tree: _OutputTree, name: str, rows: Sequence[Mapping[str, Any]]) -> Artifact:
    return tree.publish_json({"document_type": f"binance_usdm_coverage_{name}_manifest", "schema_version": 1, "row_count": len(rows), "rows": list(rows)}, directory=".manifests", kind=name)


def _completion_body(document: dict[str, Any], prior_metadata_bytes: int) -> bytes:
    completion_bytes = 0
    for _ in range(32):
        document["metadata_ledger"]["measured_category_bytes"]["completion"] = completion_bytes
        document["metadata_ledger"]["measured_metadata_bytes"] = prior_metadata_bytes + completion_bytes
        document["metadata_ledger"]["measured_coverage_reservation_remaining_bytes"] = (
            METADATA_BUDGET_BYTES - prior_metadata_bytes - completion_bytes
        )
        body = _canonical_json(document)
        if len(body) == completion_bytes:
            return body
        completion_bytes = len(body)
    raise CoverageNormalizationError("completion byte-size fixed point did not converge")


def _reprove_consumed_dependencies(
    *,
    report_path: Path,
    sizing_path: Path,
    holdout_path: Path,
    product_roots: Mapping[str, Path],
    original_index: Mapping[str, Mapping[tuple[str, str], PartitionInput]],
) -> None:
    """Reopen every consumed authority through no-follow traversal before completion."""
    report, _sizing, _holdout, products = load_inputs(
        report_path=report_path,
        sizing_path=sizing_path,
        holdout_path=holdout_path,
        product_roots=product_roots,
    )
    authority = prove_coverage_authority(report)
    members = {str(row["symbol"]) for row in authority["membership"]["accepted"]}
    rebuilt = build_partition_index(products, members)
    validate_row_equations(products)
    for product, entries in original_index.items():
        _require(
            {
                key: (part.descriptor_sha256, part.parquet_sha256, part.lineage_sha256)
                for key, part in entries.items()
            }
            == {
                key: (part.descriptor_sha256, part.parquet_sha256, part.lineage_sha256)
                for key, part in rebuilt[product].items()
            },
            "consumed partition inventory changed before completion",
        )
    for product_name in TIMESTAMP_COLUMNS:
        product = products[product_name]
        for descriptor in _quality_descriptors(product):
            parquet_path = _resolve_descriptor_path(product, descriptor.get("parquet_path"), "quality-gap Parquet path")
            lineage_path = _resolve_descriptor_path(product, descriptor.get("lineage_path"), "quality-gap lineage path")
            _require(_file_sha(parquet_path)[0] == descriptor.get("parquet_sha256"), "quality-gap Parquet changed before completion")
            _require(_file_sha(lineage_path)[0] == descriptor.get("lineage_sha256"), "quality-gap lineage changed before completion")
    cost = products["binance_usdm_cost_calibration"]
    for descriptor in cost.completion["partitions"]:
        _require(type(descriptor) is dict, "cost partition descriptor is malformed")
        lineage_path = _resolve_descriptor_path(cost, descriptor.get("lineage_path"), "cost lineage path")
        lineage_sha, lineage_bytes = _file_sha(lineage_path)
        _require(
            lineage_sha == descriptor.get("lineage_sha256")
            and lineage_bytes == descriptor.get("lineage_bytes"),
            "cost lineage changed before completion",
        )


def normalize_coverage(
    *,
    report_path: Path,
    sizing_path: Path,
    holdout_path: Path,
    product_roots: Mapping[str, Path],
    output_root: Path,
    hooks: PublicationHooks = PublicationHooks(),
) -> CoverageResult:
    """Create the complete immutable coverage product under ``output_root``."""
    output = output_root.absolute()
    for input_root in product_roots.values():
        protected = input_root.absolute()
        _require(
            output != protected
            and not output.is_relative_to(protected)
            and not protected.is_relative_to(output),
            "coverage output overlaps an immutable input tree",
        )
    _require(output not in {report_path.absolute(), sizing_path.absolute(), holdout_path.absolute()}, "coverage output aliases an authority file")
    report, _sizing, _holdout, products = load_inputs(report_path=report_path, sizing_path=sizing_path, holdout_path=holdout_path, product_roots=product_roots)
    coverage = prove_coverage_authority(report)
    members = {str(row["symbol"]) for row in coverage["membership"]["accepted"]}
    _require(len(members) == ACCEPTED_MEMBERSHIP_IDENTITIES, "accepted membership identity count changed")
    _require(len(coverage["membership"]["rejected"]) == ACCEPTED_REJECTED_MEMBERSHIP_ROWS, "excluded membership count changed")
    index = build_partition_index(products, members)
    validate_row_equations(products)
    tree = _OutputTree(output, hooks)
    try:
        source_manifest, typed_manifest, gap_bytes = publish_source_and_typed_gaps(tree, coverage)
        quality_manifest, quality_bytes, quality_missing_counts = publish_quality_gaps(tree, products, members)
        quality_references: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
        for descriptor in quality_manifest:
            quality_references[(str(descriptor["required_product"]), str(descriptor["native_symbol"]))].append(
                {
                    "utc_month": descriptor["utc_month"],
                    "row_count": descriptor["row_count"],
                    "parquet_sha256": descriptor["parquet_sha256"],
                    "parquet_bytes": descriptor["parquet_bytes"],
                    "lineage_sha256": descriptor["lineage_sha256"],
                    "lineage_bytes": descriptor["lineage_bytes"],
                }
            )
        for references in quality_references.values():
            references.sort(key=lambda item: (str(item["utc_month"]), str(item["parquet_sha256"])))
        daily_manifest, summary_manifest, alignment = publish_reports(
            tree,
            products=products,
            index=index,
            membership=coverage["membership"]["accepted"],
            typed_rows=coverage["typed_gap_memberships"],
            source_rows=coverage["source_gaps"],
            quality_missing_counts=quality_missing_counts,
            quality_gap_references=quality_references,
        )
        manifest_artifacts = {
            "source_gap": _publish_manifest(tree, "source_gap", source_manifest),
            "typed_gap": _publish_manifest(tree, "typed_gap", typed_manifest),
            "quality_gap": _publish_manifest(tree, "quality_gap", quality_manifest),
            "daily": _publish_manifest(tree, "daily", daily_manifest),
            "summary": _publish_manifest(tree, "summary", summary_manifest),
            "excluded_membership": _publish_manifest(tree, "excluded_membership", [dict(row) for row in coverage["membership"]["rejected"]]),
        }
        _require(len(source_manifest) == SOURCE_GAP_PARTITIONS and len(typed_manifest) == TYPED_GAP_PARTITIONS, "gap manifest count changed")
        input_bindings = {name: {"completion_sha256": item.completion_sha256} for name, item in sorted(products.items())}
        metadata_categories = dict(sorted(tree.metadata_by_kind.items()))
        _require(sum(metadata_categories.values()) == tree.metadata_bytes, "metadata category accounting diverged")
        metadata_categories["completion"] = 0
        completion: dict[str, Any] = {
            "document_type": "binance_usdm_coverage_gap_product_completion",
            "schema_version": 1,
            "required_product": PRODUCT_COVERAGE_GAP,
            "writer_identity": writer_identity(),
            "normalizer_source_sha256": _file_sha(Path(__file__))[0],
            "authorities": {"report_sha256": REPORT_SHA256, "sizing_sha256": SIZING_SHA256, "holdout_sha256": HOLDOUT_SHA256, "holdout_boundary_id": HOLDOUT_ID, "holdout_utc": HOLDOUT_UTC},
            "input_completions": input_bindings,
            "membership": {"accepted_identities": len(members), "funding_only_identities": FUNDING_ONLY_MEMBERSHIP_IDENTITIES, "excluded_classifications": len(coverage["membership"]["rejected"]), "product_absence_removes_membership": False},
            "components": {
                "source_gap": {"schema_sha256": SOURCE_GAP_SCHEMA_SHA256, "rows": SOURCE_GAP_ROWS, "partitions": len(source_manifest), "parquet_bytes": gap_bytes["source_gap"], "largest_file_bytes": gap_bytes["source_gap_largest"], "partition_bound": SOURCE_GAP_PARTITIONS, "bound_bytes": SOURCE_GAP_BYTES, "largest_file_bound_bytes": SOURCE_GAP_LARGEST_FILE, "manifest_sha256": manifest_artifacts["source_gap"].sha256},
                "typed_gap_membership": {"schema_sha256": _schema_sha(TYPED_GAP_SCHEMA), "rows": TYPED_GAP_ROWS, "partitions": len(typed_manifest), "parquet_bytes": gap_bytes["typed_gap"], "largest_file_bytes": gap_bytes["typed_gap_largest"], "partition_bound": TYPED_GAP_PARTITIONS, "bound_bytes": TYPED_GAP_BYTES, "largest_file_bound_bytes": TYPED_GAP_LARGEST_FILE, "manifest_sha256": manifest_artifacts["typed_gap"].sha256},
                "quality_gap": {"schema_sha256": _schema_sha(QUALITY_GAP_SCHEMA), "rows": quality_bytes["quality_gap_rows"], "partitions": len(quality_manifest), "parquet_bytes": quality_bytes["quality_gap"], "largest_file_bytes": quality_bytes["quality_gap_largest"], "row_ceiling": QUALITY_GAP_ROWS, "partition_ceiling": QUALITY_GAP_PARTITIONS, "bound_bytes": QUALITY_GAP_BYTES, "largest_file_bound_bytes": QUALITY_GAP_LARGEST_FILE, "manifest_sha256": manifest_artifacts["quality_gap"].sha256},
                "cost_normalization_source_gap_reference": {"rows": products["binance_usdm_cost_calibration"].completion["frozen_source_gaps"]["row_count"], "sha256": products["binance_usdm_cost_calibration"].completion["frozen_source_gaps"]["sha256"], "bytes": products["binance_usdm_cost_calibration"].completion["frozen_source_gaps"]["bytes"], "copied": False, "semantics": "accepted_normalization_source_gaps_distinct_from_qualification_source_gaps"},
                "fee_authority_gap_reference": {"rows": ACCEPTED_MEMBERSHIP_IDENTITIES, "copied": False, "completion_sha256": COMPLETION_SHA256["binance_usdm_cost_calibration"], "semantics": "historical_fee_schedule_unavailable;not_zero_cost"},
            },
            "row_equations": {name: item.completion.get("row_equation", item.completion.get("totals", item.completion.get("source_equation"))) for name, item in sorted(products.items())},
            "alignment": {**alignment, "daily_manifest_sha256": manifest_artifacts["daily"].sha256, "summary_manifest_sha256": manifest_artifacts["summary"].sha256, "funding_expected_count": None, "liquidation_complete": False},
            "metadata_ledger": {
                "source_page_counts": METADATA_PAGE_COUNTS,
                "page_bytes": METADATA_PAGE_BYTES,
                "reserved_debit_bytes": METADATA_BUDGET_BYTES,
                "release_wide_allocation_bytes": RELEASE_METADATA_BYTES,
                "reserved_release_remainder_bytes": RELEASE_METADATA_REMAINDER_BYTES,
                "measured_category_bytes": metadata_categories,
                "measured_metadata_bytes": 0,
                "measured_coverage_reservation_remaining_bytes": 0,
                "unused_coverage_reservation_reallocatable": False,
                "gap_parquet_charged_as_metadata": False,
            },
            "manifests": {name: {"sha256": artifact.sha256, "bytes": artifact.byte_size, "path": str(artifact.path.relative_to(tree.root))} for name, artifact in sorted(manifest_artifacts.items())},
            "publication": {"content_addressed": True, "completion_last": True, "no_clobber": True, "input_mutation": False, "visible_harmonic_bundle": False, "catalog_transaction": False},
        }
        body = _completion_body(completion, tree.metadata_bytes)
        _require(tree.metadata_bytes + len(body) <= METADATA_BUDGET_BYTES, "coverage completion exceeds metadata budget")
        expected_completion_sha = _sha(body)
        prospective = Path(".complete") / f"{expected_completion_sha}.json"

        def prove_completion_precommit() -> None:
            _reprove_consumed_dependencies(
                report_path=report_path,
                sizing_path=sizing_path,
                holdout_path=holdout_path,
                product_roots=product_roots,
                original_index=index,
            )
            tree.audit((prospective, body))

        completion_artifact = tree.publish(body, directory=".complete", suffix="json", kind="completion", row_count=None, metadata=True, precommit=prove_completion_precommit)
        _require(completion_artifact.sha256 == expected_completion_sha, "coverage completion identity changed")
        tree.audit()
        return CoverageResult(completion_artifact.path, completion_artifact.sha256, completion_artifact.reused, SOURCE_GAP_ROWS, TYPED_GAP_ROWS, quality_bytes["quality_gap_rows"], alignment["daily_report_partitions"], alignment["aligned_day_rows"], alignment["five_product_observed_day_count"], alignment["full_cadence_day_count"], tree.metadata_bytes)
    finally:
        tree.close()


__all__ = [
    "ALIGNMENT_PRODUCTS",
    "COMPLETION_SHA256",
    "CoverageNormalizationError",
    "CoverageResult",
    "METADATA_BUDGET_BYTES",
    "PublicationHooks",
    "QUALITY_GAP_SCHEMA",
    "SOURCE_GAP_SCHEMA",
    "TYPED_GAP_SCHEMA",
    "normalize_coverage",
]
