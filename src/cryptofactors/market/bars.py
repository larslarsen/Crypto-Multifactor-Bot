"""BAR-001 — Canonical bar publisher and daily reconciliation.

Publishes schema-conformant canonical bars only from **verified** MAN-001
source-normalized datasets (e.g. accepted BIN-001). Caller-asserted quality
and bare paths are rejected: identity, quality, and file hashes are checked
against manifest evidence.

Fail-closed: incomplete UTC days are not promoted to daily bars; missing values
are null (never zero-filled); PASS_WITH_WARNINGS propagates; market-physical
schemas and inclusive close semantics are strict; duplicate conflicts are
order-independent and fail closed; lineage uses valid dataset IDs + dependency
edges only.

No network.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.audit.models import IssueSeverity, QualityIssue
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetManifest,
    DatasetPublicationReceipt,
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
from cryptofactors.catalog.dataset.canonicalize import (
    compute_dataset_id,
    compute_manifest_sha256,
    identity_payload,
)
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size

# ---------------------------------------------------------------------------
# Public identity constants
# ---------------------------------------------------------------------------

MARKET_BARS_DATASET_TYPE = "market_bars"
CANONICAL_BAR_SCHEMA_NAME = "market_bar"
CANONICAL_BAR_SCHEMA_VERSION = "2"
CANONICAL_BAR_TRANSFORM_NAME = "canonical_bar_publisher"
CANONICAL_BAR_TRANSFORM_VERSION = "6"

# Accepted BIN-001 source identity (BAR-001 currently depends on this contract only).
_SUPPORTED_SOURCE_DATASET_TYPE = "binance_kline_source"
_SUPPORTED_SOURCE_SCHEMA_NAME = "binance_kline_source"
_SUPPORTED_SOURCE_SCHEMA_VERSION = "2"
_REQUIRED_PARTITION_KEYS = (
    "venue_id",
    "market_type",
    "interval",
    "instrument_id",
    "schema_variant",
)

_SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")
# Safe single path segment for hive partitions (no separators / traversal).
_SAFE_PATH_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_ALLOWED_MARKET_TYPES = frozenset({"spot", "usdm", "coinm"})

_ACCEPTED_SOURCE_QUALITY = frozenset(
    {QualityStatus.PASS, QualityStatus.PASS_WITH_WARNINGS}
)

_FIXED_INTERVALS: dict[str, timedelta] = {
    "1s": timedelta(seconds=1),
    "1m": timedelta(minutes=1),
    "3m": timedelta(minutes=3),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "2h": timedelta(hours=2),
    "4h": timedelta(hours=4),
    "6h": timedelta(hours=6),
    "8h": timedelta(hours=8),
    "12h": timedelta(hours=12),
    "1d": timedelta(days=1),
    "3d": timedelta(days=3),
    "1w": timedelta(weeks=1),
}

# Intervals that may feed daily resampling: sub-day intervals that exactly divide
# 24h, plus native 1d bars (promoted directly without resampling).
_DAILY_RESAMPLE_INTERVALS = frozenset(
    {
        "1s",
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
    }
)

# ---------------------------------------------------------------------------
# Public input / result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VerifiedSourceBarDataset:
    """Source bars backed by verified MAN-001 publication evidence.

    Either ``manifest`` (with non-empty ``manifest_sha256``) or ``receipt``
    (with ``publication_verified``) must be provided. Local files are mapped by
    manifest relative_path and re-hashed; mismatch fails closed.
    """

    local_files: Mapping[str, Path]
    venue_id: str
    instrument_id: int
    market_type: str
    interval: str
    schema_variant: str = "quote_notional"  # quote_notional | coin_margined
    manifest: DatasetManifest | None = None
    receipt: DatasetPublicationReceipt | None = None


@dataclass(frozen=True, slots=True)
class VerifiedDailySource:
    """Optional verified native daily bars for reconciliation."""

    local_files: Mapping[str, Path]
    venue_id: str
    instrument_id: int
    market_type: str
    schema_variant: str = "quote_notional"
    manifest: DatasetManifest | None = None
    receipt: DatasetPublicationReceipt | None = None


@dataclass(frozen=True, slots=True)
class PartitionSizeMeasurement:
    relative_path: str
    rows: int
    bytes: int
    venue_id: str
    market_type: str
    timeframe: str
    year: int
    month: int
    kind: str


@dataclass(frozen=True, slots=True)
class CanonicalBarPublishResult:
    publish_plan: PublishPlan
    intraday_paths: tuple[Path, ...]
    daily_paths: tuple[Path, ...]
    reconcile_paths: tuple[Path, ...]
    quarantine_paths: tuple[Path, ...]
    partition_sizes: tuple[PartitionSizeMeasurement, ...]
    issues: tuple[QualityIssue, ...]


# Back-compat name intentionally removed: caller-asserted SourceBarDatasetRef
# is no longer accepted (REVIEW-0027 #1).


@dataclass
class _BarRow:
    instrument_id: int
    venue_id: str
    market_type: str
    timeframe: str
    period_start_us: int
    period_end_us: int
    availability_time_us: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    base_volume: Decimal
    quote_volume: Decimal | None
    trade_count: int | None
    taker_buy_base_volume: Decimal | None
    taker_buy_quote_volume: Decimal | None
    source_dataset_id: str
    quality_flags: list[str] = field(default_factory=list)

    def content_fingerprint(self) -> str:
        """Economic bar content only — lineage is NOT part of identity.

        ``source_dataset_id`` is excluded so identical economics from different
        verified datasets collapse as identical (REVIEW-0028 #3). Lineage is
        used only for deterministic tie-break and dependency edges.
        """
        payload = {
            "instrument_id": self.instrument_id,
            "venue_id": self.venue_id,
            "timeframe": self.timeframe,
            "period_start_us": self.period_start_us,
            "period_end_us": self.period_end_us,
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
            "base_volume": str(self.base_volume),
            "quote_volume": None if self.quote_volume is None else str(self.quote_volume),
            "trade_count": self.trade_count,
            "taker_buy_base_volume": (
                None
                if self.taker_buy_base_volume is None
                else str(self.taker_buy_base_volume)
            ),
            "taker_buy_quote_volume": (
                None
                if self.taker_buy_quote_volume is None
                else str(self.taker_buy_quote_volume)
            ),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_code_commit(code_commit: str) -> str:
    commit = code_commit.strip()
    if not commit or commit == "unknown":
        raise ValueError(
            "code_commit is required and must be a non-empty immutable code "
            "identity supplied by the caller (not 'unknown')"
        )
    return commit


def _resolve_config_sha256(
    config_sha256: str | None,
    *,
    payload: Mapping[str, Any],
) -> str:
    if config_sha256 is not None and str(config_sha256).strip() != "":
        digest = str(config_sha256).strip().lower()
        if not _SHA256_HEX_RE.fullmatch(digest):
            raise ValueError(
                "config_sha256 must be a 64-character lowercase hex SHA-256 digest"
            )
        return digest
    body = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _interval_delta(interval: str) -> timedelta:
    raw = interval.strip()
    if raw in ("1M", "1mo"):
        raise ValueError(
            "calendar-month interval is not a supported intraday source interval "
            f"for canonical promotion: {interval!r}"
        )
    if raw not in _FIXED_INTERVALS:
        raise ValueError(f"unsupported interval: {interval!r}")
    return _FIXED_INTERVALS[raw]


def _interval_us(interval: str) -> int:
    return int(_interval_delta(interval).total_seconds() * 1_000_000)


def _us_to_datetime(us: int) -> datetime:
    sec, micro = divmod(int(us), 1_000_000)
    if sec < 0 or sec > 4102444800:
        raise ValueError(f"timestamp out of supported UTC range: {us}")
    return datetime.fromtimestamp(sec, tz=timezone.utc).replace(microsecond=micro)


def _datetime_to_us(dt: datetime) -> int:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware UTC")
    utc = dt.astimezone(timezone.utc)
    return calendar.timegm(utc.timetuple()) * 1_000_000 + utc.microsecond


def _day_start_us(us: int) -> int:
    dt = _us_to_datetime(us)
    day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return _datetime_to_us(day)


def _parquet_row_counter(path: Path) -> int:
    return int(pq.ParquetFile(str(path)).metadata.num_rows)


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        raise ValueError("missing numeric value")
    return Decimal(str(value))


def _recompute_manifest_identity(manifest: DatasetManifest) -> tuple[str, str]:
    """Return (dataset_id, manifest_sha256) recomputed via MAN-001 helpers."""
    computed_sha = compute_manifest_sha256(manifest).lower()
    identity = identity_payload(
        dataset_type=manifest.dataset_type,
        schema=manifest.schema,
        transform=manifest.transform,
        code=manifest.code,
        config=manifest.config,
        dependencies=manifest.dependencies,
        files=manifest.files,
        statistics=manifest.statistics,
        coverage=manifest.coverage,
        quality_status=manifest.quality_status,
        quality_summary=manifest.quality_summary,
        supersedes_dataset_id=manifest.supersedes_dataset_id,
    )
    expected_id, _ = compute_dataset_id(identity)
    return expected_id, computed_sha


def _file_spec_identity(spec: OutputFileSpec) -> tuple[Any, ...]:
    """Order-stable identity of one verified output for dual-evidence compare."""
    part = tuple(
        sorted((str(k), str(v)) for k, v in dict(spec.partition or {}).items())
    )
    return (
        str(spec.relative_path),
        str(spec.sha256).lower(),
        int(spec.rows),
        int(spec.bytes),
        part,
        bool(spec.rows_verified),
    )


def _coverage_identity(cov: CoverageWindow) -> tuple[Any, ...]:
    """Canonical coverage fields for dual-evidence agreement."""
    def _ts(v: datetime | None) -> str | None:
        if v is None:
            return None
        if v.tzinfo is None:
            return v.isoformat()
        return v.astimezone(timezone.utc).isoformat()

    return (
        _ts(cov.event_start),
        _ts(cov.event_end),
        _ts(cov.availability_start),
        _ts(cov.availability_end),
    )


def _quality_summary_identity(summary: Mapping[str, Any]) -> str:
    """Canonical JSON for quality_summary equality (sorted keys)."""
    return json.dumps(dict(summary), sort_keys=True, separators=(",", ":"), default=str)


def _files_identity(files: Sequence[OutputFileSpec]) -> tuple[tuple[Any, ...], ...]:
    return tuple(sorted(_file_spec_identity(f) for f in files))


def _dep_identity(deps: Sequence[DependencyRef]) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        sorted((d.id, d.kind.value if hasattr(d.kind, "value") else str(d.kind), d.role) for d in deps)
    )


def _assert_supported_source_identity(
    *,
    dataset_type: str,
    schema_name: str,
    schema_version: str,
) -> None:
    """Reject non-BIN-001 source identities (current BAR-001 contract)."""
    if dataset_type != _SUPPORTED_SOURCE_DATASET_TYPE:
        raise ValueError(
            f"unsupported source dataset_type={dataset_type!r}; "
            f"BAR-001 accepts only {_SUPPORTED_SOURCE_DATASET_TYPE!r}"
        )
    if (
        schema_name != _SUPPORTED_SOURCE_SCHEMA_NAME
        or schema_version != _SUPPORTED_SOURCE_SCHEMA_VERSION
    ):
        raise ValueError(
            f"unsupported source schema {schema_name!r} v{schema_version!r}; "
            f"BAR-001 accepts only {_SUPPORTED_SOURCE_SCHEMA_NAME!r} "
            f"v{_SUPPORTED_SOURCE_SCHEMA_VERSION!r}"
        )


def _assert_full_dual_evidence_agreement(
    *,
    manifest: DatasetManifest,
    receipt: DatasetPublicationReceipt,
) -> None:
    """Require full immutable agreement between manifest and receipt.

    Includes coverage, quality_summary, and complete output specs including
    rows_verified (REVIEW-0030 #1).
    """
    checks: list[tuple[str, Any, Any]] = [
        ("dataset_type", receipt.dataset_type, manifest.dataset_type),
        ("schema.name", receipt.schema.name, manifest.schema.name),
        ("schema.version", receipt.schema.version, manifest.schema.version),
        ("schema.fingerprint", receipt.schema.fingerprint, manifest.schema.fingerprint),
        ("transform.name", receipt.transform.name, manifest.transform.name),
        ("transform.version", receipt.transform.version, manifest.transform.version),
        ("code.commit", receipt.code.commit, manifest.code.commit),
        ("code.lock_sha256", receipt.code.lock_sha256, manifest.code.lock_sha256),
        (
            "config.config_sha256",
            receipt.config.config_sha256,
            manifest.config.config_sha256,
        ),
        (
            "statistics.row_count",
            receipt.statistics.row_count,
            manifest.statistics.row_count,
        ),
        (
            "statistics.byte_size",
            receipt.statistics.byte_size,
            manifest.statistics.byte_size,
        ),
        (
            "supersedes_dataset_id",
            receipt.supersedes_dataset_id,
            manifest.supersedes_dataset_id,
        ),
        ("quality_status", receipt.quality_status, manifest.quality_status),
    ]
    for label, a, b in checks:
        if a != b:
            raise ValueError(
                f"receipt/manifest disagree on {label}: receipt={a!r} manifest={b!r}"
            )
    if _coverage_identity(receipt.coverage) != _coverage_identity(manifest.coverage):
        raise ValueError(
            "receipt/manifest disagree on coverage "
            f"(receipt={_coverage_identity(receipt.coverage)!r} "
            f"manifest={_coverage_identity(manifest.coverage)!r})"
        )
    if _quality_summary_identity(receipt.quality_summary) != _quality_summary_identity(
        manifest.quality_summary
    ):
        raise ValueError("receipt/manifest disagree on quality_summary")
    if _dep_identity(receipt.dependencies) != _dep_identity(manifest.dependencies):
        raise ValueError("receipt/manifest disagree on dependencies")
    if _files_identity(receipt.verified_outputs) != _files_identity(manifest.files):
        raise ValueError(
            "receipt.verified_outputs disagree with manifest.files "
            "(relative_path/sha256/rows/bytes/partition/rows_verified)"
        )


def _extract_verified_identity(
    *,
    manifest: DatasetManifest | None,
    receipt: DatasetPublicationReceipt | None,
) -> tuple[str, QualityStatus, tuple[OutputFileSpec, ...], str]:
    """Return (dataset_id, quality_status, verified_files, manifest_sha256).

    Manifest identity is recomputed (hash + dataset_id). Receipts must be
    complete. Dual evidence requires full immutable agreement (REVIEW-0029 #3).
    """
    if receipt is None and manifest is None:
        raise ValueError(
            "VerifiedSourceBarDataset requires manifest or receipt with MAN-001 evidence"
        )

    if receipt is not None and manifest is not None:
        if not receipt.is_complete():
            raise ValueError(
                "DatasetPublicationReceipt must be complete "
                "(publication_verified, ds_ id, 64-hex manifest_sha256, URIs)"
            )
        expected_id, computed_sha = _recompute_manifest_identity(manifest)
        declared_sha = (manifest.manifest_sha256 or "").lower()
        if declared_sha != computed_sha:
            raise ValueError(
                f"manifest_sha256 disagrees with recomputed body: "
                f"declared={declared_sha} computed={computed_sha}"
            )
        if manifest.dataset_id != expected_id:
            raise ValueError(
                f"manifest.dataset_id disagrees with recomputed identity: "
                f"declared={manifest.dataset_id!r} expected={expected_id!r}"
            )
        r_sha = receipt.manifest_sha256.lower()
        if r_sha != computed_sha or receipt.dataset_id != expected_id:
            raise ValueError(
                "receipt and manifest disagree on dataset_id/manifest_sha256 "
                f"(receipt id={receipt.dataset_id!r} sha={r_sha}; "
                f"manifest id={expected_id!r} sha={computed_sha})"
            )
        if receipt.quality_status is not manifest.quality_status:
            raise ValueError(
                "receipt and manifest disagree on quality_status: "
                f"receipt={receipt.quality_status.value} "
                f"manifest={manifest.quality_status.value}"
            )
        _assert_full_dual_evidence_agreement(manifest=manifest, receipt=receipt)
        _assert_supported_source_identity(
            dataset_type=manifest.dataset_type,
            schema_name=manifest.schema.name,
            schema_version=manifest.schema.version,
        )
        # Prefer manifest.files (recomputed identity); already proven equal to receipt.
        return (
            expected_id,
            manifest.quality_status,
            tuple(manifest.files),
            computed_sha,
        )

    if receipt is not None:
        if not receipt.is_complete():
            raise ValueError(
                "DatasetPublicationReceipt must be complete "
                "(publication_verified, ds_ id, 64-hex manifest_sha256, URIs)"
            )
        _assert_supported_source_identity(
            dataset_type=receipt.dataset_type,
            schema_name=receipt.schema.name,
            schema_version=receipt.schema.version,
        )
        return (
            receipt.dataset_id,
            receipt.quality_status,
            tuple(receipt.verified_outputs),
            receipt.manifest_sha256.lower(),
        )

    assert manifest is not None
    expected_id, computed_sha = _recompute_manifest_identity(manifest)
    declared_sha = (manifest.manifest_sha256 or "").lower()
    if not _SHA256_HEX_RE.fullmatch(declared_sha):
        raise ValueError(
            "manifest.manifest_sha256 must be a non-empty 64-hex digest"
        )
    if declared_sha != computed_sha:
        raise ValueError(
            f"manifest_sha256 disagrees with recomputed body: "
            f"declared={declared_sha} computed={computed_sha}"
        )
    if manifest.dataset_id != expected_id:
        raise ValueError(
            f"manifest.dataset_id disagrees with recomputed identity: "
            f"declared={manifest.dataset_id!r} expected={expected_id!r}"
        )
    _assert_supported_source_identity(
        dataset_type=manifest.dataset_type,
        schema_name=manifest.schema.name,
        schema_version=manifest.schema.version,
    )
    return expected_id, manifest.quality_status, tuple(manifest.files), computed_sha


def _is_source_bar_spec(spec: OutputFileSpec) -> bool:
    """True only for verified source-observation bar partitions (not quality/etc.)."""
    rel = spec.relative_path.replace("\\", "/").strip("/")
    parts = rel.split("/")
    blocked = {"quality", "reconcile", "quarantine"}
    if any(p in blocked or p.startswith("quality") for p in parts):
        return False
    kind = str((spec.partition or {}).get("kind") or "").lower()
    if kind in blocked:
        return False
    # Require explicit bars.parquet naming (BIN-001 / BAR source convention).
    if not rel.endswith("bars.parquet"):
        return False
    return True


def _validate_path_token(label: str, value: str) -> str:
    """Reject separators/traversal and empty tokens before filesystem writes."""
    v = value.strip()
    if not v or not _SAFE_PATH_TOKEN.fullmatch(v):
        raise ValueError(
            f"invalid {label} for partition path: {value!r} "
            "(must be a single alphanumeric token with ._- only)"
        )
    if ".." in v or "/" in v or "\\" in v:
        raise ValueError(f"invalid {label} for partition path: {value!r}")
    return v


def _validate_market_type(market_type: str) -> str:
    m = market_type.strip().lower()
    if m not in _ALLOWED_MARKET_TYPES:
        raise ValueError(
            f"market_type must be one of {sorted(_ALLOWED_MARKET_TYPES)}; got {market_type!r}"
        )
    return m


def _is_daily_resample_interval(interval: str) -> bool:
    """Fixed sub-day intervals that exactly tile a UTC day."""
    if interval not in _DAILY_RESAMPLE_INTERVALS:
        return False
    secs = int(_FIXED_INTERVALS[interval].total_seconds())
    return secs > 0 and (86_400 % secs) == 0


def _agree_partition_meta(
    *,
    dataset_id: str,
    specs: Sequence[OutputFileSpec],
    venue_id: str,
    instrument_id: int,
    market_type: str,
    interval: str,
    schema_variant: str,
) -> None:
    """Require complete BIN-001 economic partition metadata on every bar spec.

    Every selected output must carry all required keys; values must agree across
    specs and match the caller (REVIEW-0029 #1). No missing-key fallback.
    """
    if not specs:
        raise ValueError(
            f"no selected bar outputs to bind economic metadata for dataset_id={dataset_id!r}"
        )
    expected = {
        "venue_id": venue_id,
        "market_type": market_type,
        "interval": interval,
        "instrument_id": str(instrument_id),
        "schema_variant": schema_variant,
    }
    for key in _REQUIRED_PARTITION_KEYS:
        seen: set[str] = set()
        for spec in specs:
            part = dict(spec.partition or {})
            if key not in part:
                raise ValueError(
                    f"selected bar output {spec.relative_path!r} missing required "
                    f"partition key {key!r} for dataset_id={dataset_id!r}"
                )
            seen.add(str(part[key]))
        if len(seen) != 1:
            raise ValueError(
                f"partition key {key!r} inconsistent across bar outputs for "
                f"dataset_id={dataset_id!r}: {sorted(seen)}"
            )
        got = next(iter(seen))
        if got != expected[key]:
            raise ValueError(
                f"caller {key}={expected[key]!r} disagrees with verified "
                f"partition {key}={got!r} for dataset_id={dataset_id!r}"
            )


def _verify_local_files(
    *,
    dataset_id: str,
    verified_files: Sequence[OutputFileSpec],
    local_files: Mapping[str, Path],
    issues: list[QualityIssue],
) -> list[tuple[OutputFileSpec, Path]]:
    """Match local paths to verified **source bar** outputs and re-hash."""
    bar_specs = [f for f in verified_files if _is_source_bar_spec(f)]
    if not bar_specs:
        raise ValueError(
            f"verified dataset {dataset_id!r} has no source bar outputs "
            "(expected relative_path ending in bars.parquet, excluding "
            "quality/reconcile/quarantine)"
        )

    resolved: list[tuple[OutputFileSpec, Path]] = []
    for spec in sorted(bar_specs, key=lambda s: s.relative_path):
        rel = spec.relative_path
        if rel not in local_files:
            raise ValueError(
                f"local_files missing verified relative_path {rel!r} "
                f"for dataset_id={dataset_id!r}"
            )
        path = Path(local_files[rel])
        if not path.is_file():
            raise ValueError(
                f"local file for {rel!r} is not a regular file: {path} "
                f"(dataset_id={dataset_id!r})"
            )
        sha, size = stream_sha256_and_size(path)
        if sha.lower() != spec.sha256.lower():
            raise ValueError(
                f"hash mismatch for {rel!r} dataset_id={dataset_id!r}: "
                f"manifest={spec.sha256} observed={sha}"
            )
        if size != spec.bytes:
            raise ValueError(
                f"byte size mismatch for {rel!r} dataset_id={dataset_id!r}: "
                f"manifest={spec.bytes} observed={size}"
            )
        resolved.append((spec, path))
    if not resolved:
        issues.append(
            QualityIssue(
                code="bar001_no_verified_bar_files",
                severity=IssueSeverity.ERROR,
                message="no verified bar files resolved for source dataset",
                context={"dataset_id": dataset_id},
            )
        )
    return resolved


def _required_volume_columns(schema_variant: str) -> tuple[str, str | None, str | None, str | None]:
    """Strict physical columns: (base, quote|None, taker_base|None, taker_quote|None)."""
    if schema_variant == "coin_margined":
        return (
            "base_asset_volume",
            None,  # quote notional not present; must remain null
            "taker_buy_base_asset_volume",
            None,
        )
    if schema_variant == "quote_notional":
        return (
            "volume",
            "quote_volume",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
        )
    raise ValueError(
        f"unsupported schema_variant: {schema_variant!r} "
        "(expected quote_notional or coin_margined)"
    )


def _unit_factor_src(unit: str) -> int:
    if unit == "us":
        return 1_000_000
    if unit == "ms":
        return 1_000
    if unit == "s":
        return 1
    raise ValueError(f"unsupported unit: {unit!r}")


def _expected_source_close(open_src: int, interval: str, unit: str) -> int:
    """BIN-001 inclusive close: open + interval − 1 source unit."""
    steps_src = int(_interval_delta(interval).total_seconds() * _unit_factor_src(unit))
    return open_src + steps_src - 1


def _source_to_utc_us(src_ts: int, unit: str) -> int:
    """Convert preserved source timestamp to UTC microseconds."""
    if unit == "us":
        return int(src_ts)
    if unit == "ms":
        return int(src_ts) * 1_000
    if unit == "s":
        return int(src_ts) * 1_000_000
    raise ValueError(f"unsupported source_timestamp_unit: {unit!r}")


def _canonical_bar_schema() -> pa.Schema:
    """Nullable trade/taker/quote fields — never coerced to zero."""
    return pa.schema(
        [
            ("instrument_id", pa.int64()),
            ("venue_id", pa.string()),
            ("market_type", pa.string()),
            ("timeframe", pa.string()),
            ("period_start", pa.int64()),
            ("period_end", pa.int64()),
            ("availability_time", pa.int64()),
            ("open", pa.decimal128(38, 18)),
            ("high", pa.decimal128(38, 18)),
            ("low", pa.decimal128(38, 18)),
            ("close", pa.decimal128(38, 18)),
            ("base_volume", pa.decimal128(38, 18)),
            ("quote_volume", pa.decimal128(38, 18)),  # null allowed
            ("trade_count", pa.int64()),  # null allowed
            ("taker_buy_base_volume", pa.decimal128(38, 18)),
            ("taker_buy_quote_volume", pa.decimal128(38, 18)),
            ("source_dataset_id", pa.string()),
            ("quality_flags", pa.string()),
        ]
    )


def _reconcile_schema() -> pa.Schema:
    return pa.schema(
        [
            ("instrument_id", pa.int64()),
            ("venue_id", pa.string()),
            ("period_start", pa.int64()),
            ("field_name", pa.string()),
            ("expected", pa.string()),
            ("observed", pa.string()),
            ("abs_diff", pa.string()),
            ("within_tolerance", pa.bool_()),
            ("status", pa.string()),
            ("source_dataset_id", pa.string()),
            ("native_dataset_id", pa.string()),
        ]
    )


def _dec_array(values: Sequence[Decimal | None]) -> pa.Array:
    return pa.array(
        [None if v is None else v for v in values],
        type=pa.decimal128(38, 18),
    )


def _write_bars_parquet(path: Path, rows: Sequence[_BarRow]) -> tuple[str, int, int]:
    schema = _canonical_bar_schema()
    if not rows:
        table = pa.table([[] for _ in range(len(schema))], schema=schema)
    else:
        arrays = {
            "instrument_id": pa.array([r.instrument_id for r in rows], type=pa.int64()),
            "venue_id": pa.array([r.venue_id for r in rows], type=pa.string()),
            "market_type": pa.array([r.market_type for r in rows], type=pa.string()),
            "timeframe": pa.array([r.timeframe for r in rows], type=pa.string()),
            "period_start": pa.array([r.period_start_us for r in rows], type=pa.int64()),
            "period_end": pa.array([r.period_end_us for r in rows], type=pa.int64()),
            "availability_time": pa.array(
                [r.availability_time_us for r in rows], type=pa.int64()
            ),
            "open": pa.array([r.open for r in rows], type=pa.decimal128(38, 18)),
            "high": pa.array([r.high for r in rows], type=pa.decimal128(38, 18)),
            "low": pa.array([r.low for r in rows], type=pa.decimal128(38, 18)),
            "close": pa.array([r.close for r in rows], type=pa.decimal128(38, 18)),
            "base_volume": pa.array(
                [r.base_volume for r in rows], type=pa.decimal128(38, 18)
            ),
            "quote_volume": _dec_array([r.quote_volume for r in rows]),
            "trade_count": pa.array(
                [r.trade_count for r in rows], type=pa.int64()
            ),
            "taker_buy_base_volume": _dec_array(
                [r.taker_buy_base_volume for r in rows]
            ),
            "taker_buy_quote_volume": _dec_array(
                [r.taker_buy_quote_volume for r in rows]
            ),
            "source_dataset_id": pa.array(
                [r.source_dataset_id for r in rows], type=pa.string()
            ),
            "quality_flags": pa.array(
                [json.dumps(list(r.quality_flags), separators=(",", ":")) for r in rows],
                type=pa.string(),
            ),
        }
        table = pa.table(arrays, schema=schema)
    pq.write_table(table, str(path), compression="zstd")
    sha, byte_size = stream_sha256_and_size(path)
    return sha, byte_size, len(rows)


def _write_reconcile_parquet(
    path: Path, rows: Sequence[Mapping[str, Any]]
) -> tuple[str, int, int]:
    schema = _reconcile_schema()
    if not rows:
        table = pa.table([[] for _ in range(len(schema))], schema=schema)
    else:
        arrays = {
            "instrument_id": pa.array(
                [int(r["instrument_id"]) for r in rows], type=pa.int64()
            ),
            "venue_id": pa.array([str(r["venue_id"]) for r in rows], type=pa.string()),
            "period_start": pa.array(
                [int(r["period_start"]) for r in rows], type=pa.int64()
            ),
            "field_name": pa.array(
                [str(r["field_name"]) for r in rows], type=pa.string()
            ),
            "expected": pa.array([str(r["expected"]) for r in rows], type=pa.string()),
            "observed": pa.array([str(r["observed"]) for r in rows], type=pa.string()),
            "abs_diff": pa.array([str(r["abs_diff"]) for r in rows], type=pa.string()),
            "within_tolerance": pa.array(
                [bool(r["within_tolerance"]) for r in rows], type=pa.bool_()
            ),
            "status": pa.array([str(r["status"]) for r in rows], type=pa.string()),
            "source_dataset_id": pa.array(
                [str(r["source_dataset_id"]) for r in rows], type=pa.string()
            ),
            "native_dataset_id": pa.array(
                [str(r.get("native_dataset_id") or "") for r in rows], type=pa.string()
            ),
        }
        table = pa.table(arrays, schema=schema)
    pq.write_table(table, str(path), compression="zstd")
    sha, byte_size = stream_sha256_and_size(path)
    return sha, byte_size, len(rows)


def _write_quality_parquet(path: Path, issues: Sequence[QualityIssue]) -> tuple[str, int, int]:
    if not issues:
        schema = pa.schema(
            [
                ("code", pa.string()),
                ("severity", pa.string()),
                ("message", pa.string()),
                ("column", pa.string()),
                ("context", pa.string()),
            ]
        )
        table = pa.table([[] for _ in range(len(schema))], schema=schema)
    else:
        data = {
            "code": [i.code for i in issues],
            "severity": [i.severity.value for i in issues],
            "message": [i.message for i in issues],
            "column": [i.column or "" for i in issues],
            "context": [str(dict(i.context)) for i in issues],
        }
        table = pa.table(data)
    pq.write_table(table, str(path), compression="zstd")
    sha, byte_size = stream_sha256_and_size(path)
    return sha, byte_size, len(issues)


def _load_verified_bars(
    src: VerifiedSourceBarDataset,
    *,
    interval_override: str | None,
    issues: list[QualityIssue],
) -> tuple[str, QualityStatus, list[_BarRow]]:
    dataset_id, quality, verified_files, _msha = _extract_verified_identity(
        manifest=src.manifest, receipt=src.receipt
    )
    if quality not in _ACCEPTED_SOURCE_QUALITY:
        raise ValueError(
            "source dataset quality_status must be PASS or PASS_WITH_WARNINGS "
            f"(from verified MAN-001 evidence); got {quality.value!r} "
            f"for dataset_id={dataset_id!r}"
        )
    venue_id = _validate_path_token("venue_id", src.venue_id)
    market_type = _validate_market_type(src.market_type)
    if src.instrument_id <= 0:
        raise ValueError("instrument_id must be a positive integer surrogate")

    interval = interval_override or src.interval
    interval = interval.strip()
    _interval_us(interval)  # validate known interval
    schema_variant = src.schema_variant.strip()
    if schema_variant not in {"quote_notional", "coin_margined"}:
        raise ValueError(f"unsupported schema_variant: {schema_variant!r}")

    interval_us = _interval_us(interval)
    base_col, quote_col, tb_base_col, tb_quote_col = _required_volume_columns(
        schema_variant
    )

    if quality is QualityStatus.PASS_WITH_WARNINGS:
        issues.append(
            QualityIssue(
                code="bar001_source_pass_with_warnings",
                severity=IssueSeverity.WARNING,
                message="source dataset quality is PASS_WITH_WARNINGS; preserved on canonical plan",
                context={"dataset_id": dataset_id},
            )
        )

    pairs = _verify_local_files(
        dataset_id=dataset_id,
        verified_files=verified_files,
        local_files=src.local_files,
        issues=issues,
    )
    _agree_partition_meta(
        dataset_id=dataset_id,
        specs=[s for s, _ in pairs],
        venue_id=venue_id,
        instrument_id=src.instrument_id,
        market_type=market_type,
        interval=interval,
        schema_variant=schema_variant,
    )

    out: list[_BarRow] = []
    for _spec, path in pairs:
        table = pq.read_table(str(path))
        names = set(table.column_names)
        required = {"open_time", "open", "high", "low", "close", base_col}
        missing = sorted(required - names)
        if missing:
            raise ValueError(
                f"source parquet missing required columns {missing} for "
                f"schema_variant={schema_variant!r} dataset_id={dataset_id!r} "
                f"path={path}"
            )
        if quote_col is not None and quote_col not in names:
            raise ValueError(
                f"source parquet missing required quote column {quote_col!r} for "
                f"schema_variant={schema_variant!r} dataset_id={dataset_id!r}"
            )
        # Strict: no fallback from base_asset_volume → volume for COIN-M.
        if schema_variant == "coin_margined" and base_col not in names:
            raise ValueError(
                "coin_margined source missing base_asset_volume; refusing to "
                "treat contract volume as base-asset volume"
            )
        # REVIEW-0028/0029: require source timestamp fields + normalized close_time.
        for col in (
            "source_open_time",
            "source_close_time",
            "source_timestamp_unit",
            "close_time",
        ):
            if col not in names:
                raise ValueError(
                    f"source parquet missing required {col!r} for timestamp "
                    f"cross-validation (dataset_id={dataset_id!r} path={path})"
                )

        n = table.num_rows
        for i in range(n):
            try:
                open_us = int(table.column("open_time")[i].as_py())
                close_us = int(table.column("close_time")[i].as_py())
                o = _to_decimal(table.column("open")[i].as_py())
                h = _to_decimal(table.column("high")[i].as_py())
                low = _to_decimal(table.column("low")[i].as_py())
                c = _to_decimal(table.column("close")[i].as_py())
                base_v = _to_decimal(table.column(base_col)[i].as_py())

                quote_v: Decimal | None
                if quote_col is not None:
                    quote_v = _to_decimal(table.column(quote_col)[i].as_py())
                else:
                    quote_v = None  # COIN-M: unavailable, not zero

                trades: int | None = None
                if "trades" in names:
                    tv = table.column("trades")[i].as_py()
                    trades = int(tv) if tv is not None else None

                tb_base: Decimal | None = None
                tb_quote: Decimal | None = None
                if tb_base_col is not None and tb_base_col in names:
                    raw_tb = table.column(tb_base_col)[i].as_py()
                    tb_base = None if raw_tb is None else _to_decimal(raw_tb)
                if tb_quote_col is not None and tb_quote_col in names:
                    raw_tq = table.column(tb_quote_col)[i].as_py()
                    tb_quote = None if raw_tq is None else _to_decimal(raw_tq)

                flags: list[str] = []
                if quality is QualityStatus.PASS_WITH_WARNINGS:
                    flags.append("source_pass_with_warnings")
                if quote_v is None:
                    flags.append("quote_volume_unavailable")
                if schema_variant == "coin_margined":
                    flags.append("coinm_volume_semantics")

                # Inclusive close: exact open+interval-1 in source unit only.
                sot = int(table.column("source_open_time")[i].as_py())
                sct = int(table.column("source_close_time")[i].as_py())
                unit = str(table.column("source_timestamp_unit")[i].as_py())
                expected = _expected_source_close(sot, interval, unit)
                if sct != expected:
                    issues.append(
                        QualityIssue(
                            code="bar001_interval_close_mismatch",
                            severity=IssueSeverity.ERROR,
                            message=(
                                "source close_time does not match inclusive "
                                "open+interval-1 convention"
                            ),
                            context={
                                "dataset_id": dataset_id,
                                "source_open_time": sot,
                                "source_close_time": sct,
                                "expected_close": expected,
                                "unit": unit,
                                "interval": interval,
                                "path": str(path),
                                "row": i,
                            },
                        )
                    )
                    continue  # reject row

                # REVIEW-0029 #4: normalized columns must match source unit conversion.
                expected_open_us = _source_to_utc_us(sot, unit)
                expected_close_us = _source_to_utc_us(sct, unit)
                if open_us != expected_open_us or close_us != expected_close_us:
                    issues.append(
                        QualityIssue(
                            code="bar001_normalized_source_timestamp_mismatch",
                            severity=IssueSeverity.ERROR,
                            message=(
                                "normalized open_time/close_time disagree with "
                                "source_* timestamps and unit"
                            ),
                            context={
                                "dataset_id": dataset_id,
                                "open_time": open_us,
                                "close_time": close_us,
                                "expected_open_us": expected_open_us,
                                "expected_close_us": expected_close_us,
                                "source_open_time": sot,
                                "source_close_time": sct,
                                "unit": unit,
                                "path": str(path),
                                "row": i,
                            },
                        )
                    )
                    continue

                period_end = open_us + interval_us

                out.append(
                    _BarRow(
                        instrument_id=src.instrument_id,
                        venue_id=venue_id,
                        market_type=market_type,
                        timeframe=interval,
                        period_start_us=open_us,
                        period_end_us=period_end,
                        availability_time_us=period_end,
                        open=o,
                        high=h,
                        low=low,
                        close=c,
                        base_volume=base_v,
                        quote_volume=quote_v,
                        trade_count=trades,
                        taker_buy_base_volume=tb_base,
                        taker_buy_quote_volume=tb_quote,
                        source_dataset_id=dataset_id,
                        quality_flags=flags,
                    )
                )
            except Exception as exc:
                issues.append(
                    QualityIssue(
                        code="bar001_source_row_parse_failure",
                        severity=IssueSeverity.ERROR,
                        message=str(exc),
                        context={
                            "dataset_id": dataset_id,
                            "path": str(path),
                            "row": i,
                        },
                    )
                )
    return dataset_id, quality, out


def _sort_key(row: _BarRow) -> tuple[int, str, str, int, str]:
    # Include source_dataset_id for deterministic ordering (order-independent).
    return (
        row.instrument_id,
        row.venue_id,
        row.timeframe,
        row.period_start_us,
        row.source_dataset_id,
    )


def _unique_key(row: _BarRow) -> tuple[int, str, str, int]:
    return (row.instrument_id, row.venue_id, row.timeframe, row.period_start_us)


def _enforce_uniqueness(
    rows: Sequence[_BarRow],
    issues: list[QualityIssue],
) -> tuple[list[_BarRow], list[_BarRow]]:
    """Order-independent uniqueness.

    - Identical content duplicates → keep one (min source_dataset_id).
    - Conflicting content → quarantine **all** copies; none promoted.
    """
    ordered = sorted(rows, key=_sort_key)
    groups: dict[tuple[int, str, str, int], list[_BarRow]] = defaultdict(list)
    for row in ordered:
        groups[_unique_key(row)].append(row)

    unique: list[_BarRow] = []
    quarantined: list[_BarRow] = []
    for key in sorted(groups.keys()):
        members = groups[key]
        if len(members) == 1:
            unique.append(members[0])
            continue
        fps = {m.content_fingerprint() for m in members}
        if len(fps) == 1:
            # Identical: keep lexicographically smallest source_dataset_id
            keep = sorted(members, key=lambda r: r.source_dataset_id)[0]
            unique.append(keep)
            issues.append(
                QualityIssue(
                    code="bar001_duplicate_identical",
                    severity=IssueSeverity.WARNING,
                    message="identical duplicate period_start collapsed deterministically",
                    context={
                        "instrument_id": key[0],
                        "venue_id": key[1],
                        "timeframe": key[2],
                        "period_start": key[3],
                        "kept_source_dataset_id": keep.source_dataset_id,
                        "count": len(members),
                    },
                )
            )
        else:
            for m in members:
                q = _BarRow(
                    instrument_id=m.instrument_id,
                    venue_id=m.venue_id,
                    market_type=m.market_type,
                    timeframe=m.timeframe,
                    period_start_us=m.period_start_us,
                    period_end_us=m.period_end_us,
                    availability_time_us=m.availability_time_us,
                    open=m.open,
                    high=m.high,
                    low=m.low,
                    close=m.close,
                    base_volume=m.base_volume,
                    quote_volume=m.quote_volume,
                    trade_count=m.trade_count,
                    taker_buy_base_volume=m.taker_buy_base_volume,
                    taker_buy_quote_volume=m.taker_buy_quote_volume,
                    source_dataset_id=m.source_dataset_id,
                    quality_flags=list(m.quality_flags) + ["duplicate_conflict"],
                )
                quarantined.append(q)
            issues.append(
                QualityIssue(
                    code="bar001_duplicate_conflict",
                    severity=IssueSeverity.ERROR,
                    message=(
                        "conflicting bars share (instrument, venue, timeframe, "
                        "period_start); all copies quarantined (order-independent)"
                    ),
                    context={
                        "instrument_id": key[0],
                        "venue_id": key[1],
                        "timeframe": key[2],
                        "period_start": key[3],
                        "source_dataset_ids": sorted(
                            {m.source_dataset_id for m in members}
                        ),
                        "count": len(members),
                    },
                )
            )
    unique.sort(key=_sort_key)
    return unique, quarantined


def _expected_day_opens(day_start_us: int, interval_us: int) -> list[int]:
    day_end = day_start_us + 86_400_000_000
    opens: list[int] = []
    t = day_start_us
    while t < day_end:
        opens.append(t)
        t += interval_us
    return opens


def _complete_days(
    intraday: Sequence[_BarRow],
    issues: list[QualityIssue],
) -> tuple[list[_BarRow], list[_BarRow]]:
    """Split intraday into complete-UTC-day rows vs incomplete-day quarantine.

    Incomplete days are excluded from daily resampling (not zero-filled).
    Grouping includes timeframe so mixed intervals never share a cadence check
    (REVIEW-0028 #4). Only sub-day intervals that tile 24h are eligible for
    daily promotion (#5).
    """
    by_day: dict[tuple[int, str, str, str, int], list[_BarRow]] = defaultdict(list)
    for row in intraday:
        day = _day_start_us(row.period_start_us)
        key = (
            row.instrument_id,
            row.venue_id,
            row.market_type,
            row.timeframe,
            day,
        )
        by_day[key].append(row)

    complete: list[_BarRow] = []
    incomplete_q: list[_BarRow] = []
    for key, members in sorted(by_day.items()):
        instrument_id, venue_id, market_type, timeframe, day_us = key

        def _quarantine_members(flag: str) -> None:
            for m in members:
                incomplete_q.append(
                    _BarRow(
                        instrument_id=m.instrument_id,
                        venue_id=m.venue_id,
                        market_type=m.market_type,
                        timeframe=m.timeframe,
                        period_start_us=m.period_start_us,
                        period_end_us=m.period_end_us,
                        availability_time_us=m.availability_time_us,
                        open=m.open,
                        high=m.high,
                        low=m.low,
                        close=m.close,
                        base_volume=m.base_volume,
                        quote_volume=m.quote_volume,
                        trade_count=m.trade_count,
                        taker_buy_base_volume=m.taker_buy_base_volume,
                        taker_buy_quote_volume=m.taker_buy_quote_volume,
                        source_dataset_id=m.source_dataset_id,
                        quality_flags=list(m.quality_flags) + [flag],
                    )
                )

        if not _is_daily_resample_interval(timeframe):
            issues.append(
                QualityIssue(
                    code="bar001_daily_unsupported_interval",
                    severity=IssueSeverity.ERROR,
                    message=(
                        f"timeframe={timeframe!r} is not a fixed sub-day interval "
                        "that tiles 24h; excluded from daily resampling"
                    ),
                    context={
                        "instrument_id": instrument_id,
                        "venue_id": venue_id,
                        "day_start": day_us,
                        "timeframe": timeframe,
                    },
                )
            )
            _quarantine_members("unsupported_daily_interval")
            continue

        try:
            interval_us = _interval_us(timeframe)
        except ValueError:
            issues.append(
                QualityIssue(
                    code="bar001_daily_unsupported_interval",
                    severity=IssueSeverity.ERROR,
                    message=f"cannot validate day completeness for timeframe={timeframe!r}",
                    context={
                        "instrument_id": instrument_id,
                        "venue_id": venue_id,
                        "day_start": day_us,
                        "timeframe": timeframe,
                    },
                )
            )
            _quarantine_members("incomplete_utc_day")
            continue

        expected = _expected_day_opens(day_us, interval_us)
        observed = sorted(m.period_start_us for m in members)
        if observed == expected:
            complete.extend(members)
        else:
            issues.append(
                QualityIssue(
                    code="bar001_incomplete_utc_day",
                    severity=IssueSeverity.ERROR,
                    message="UTC day lacks full interval cadence; excluded from daily promotion",
                    context={
                        "instrument_id": instrument_id,
                        "venue_id": venue_id,
                        "market_type": market_type,
                        "day_start": day_us,
                        "timeframe": timeframe,
                        "expected_bars": len(expected),
                        "observed_bars": len(observed),
                    },
                )
            )
            for m in members:
                incomplete_q.append(
                    _BarRow(
                        instrument_id=m.instrument_id,
                        venue_id=m.venue_id,
                        market_type=m.market_type,
                        timeframe=m.timeframe,
                        period_start_us=m.period_start_us,
                        period_end_us=m.period_end_us,
                        availability_time_us=m.availability_time_us,
                        open=m.open,
                        high=m.high,
                        low=m.low,
                        close=m.close,
                        base_volume=m.base_volume,
                        quote_volume=m.quote_volume,
                        trade_count=m.trade_count,
                        taker_buy_base_volume=m.taker_buy_base_volume,
                        taker_buy_quote_volume=m.taker_buy_quote_volume,
                        source_dataset_id=m.source_dataset_id,
                        quality_flags=list(m.quality_flags) + ["incomplete_utc_day"],
                    )
                )
    return complete, incomplete_q


def _canonicalize_daily_source_timeframe(value: str | None) -> str | None:
    """Strip/validate configured timeframe once for behavior + config identity.

    ``"1m"`` and ``" 1m "`` must hash identically (REVIEW-0030 #2).
    """
    if value is None:
        return None
    tf = value.strip()
    if not tf:
        return None
    if not _is_daily_resample_interval(tf):
        raise ValueError(
            f"daily_source_timeframe={tf!r} is not a valid sub-day "
            "resampling interval that tiles 24h"
        )
    return tf


def _select_rows_for_daily_resample(
    complete_rows: Sequence[_BarRow],
    *,
    daily_source_timeframe: str | None,
) -> tuple[list[_BarRow], str | None]:
    """Pick exactly one identity-bearing source timeframe for daily bars.

    ``daily_source_timeframe`` must already be canonical (stripped/validated) or
    None. Returns (rows, effective_timeframe) for config identity hashing.
    Never merges multiple complete timeframes (REVIEW-0029 #2 / REVIEW-0030 #2).
    """
    if not complete_rows:
        return [], None
    present = sorted({r.timeframe for r in complete_rows})
    if daily_source_timeframe is not None:
        tf = daily_source_timeframe  # already canonical
        if not _is_daily_resample_interval(tf):
            raise ValueError(
                f"daily_source_timeframe={tf!r} is not a valid sub-day "
                "resampling interval that tiles 24h"
            )
        selected = [r for r in complete_rows if r.timeframe == tf]
        if not selected:
            raise ValueError(
                f"daily_source_timeframe={tf!r} has no complete-day rows; "
                f"present complete timeframes={present}"
            )
        return selected, tf
    if len(present) > 1:
        raise ValueError(
            "ambiguous multiple complete source timeframes for daily resampling: "
            f"{present}; pass daily_source_timeframe= to select exactly one"
        )
    return list(complete_rows), present[0]


def _resample_daily(intraday_complete: Sequence[_BarRow]) -> list[_BarRow]:
    """Deterministic UTC-day OHLCV from **complete** days of one timeframe only."""
    # Defense in depth: group by timeframe so mixed inputs cannot silently merge.
    groups: dict[tuple[int, str, str, str, int], list[_BarRow]] = defaultdict(list)
    for row in intraday_complete:
        day = _day_start_us(row.period_start_us)
        key = (row.instrument_id, row.venue_id, row.market_type, row.timeframe, day)
        groups[key].append(row)

    daily: list[_BarRow] = []
    for (instrument_id, venue_id, market_type, _src_tf, day_us), members in sorted(
        groups.items(), key=lambda kv: kv[0]
    ):
        members_sorted = sorted(members, key=lambda r: (r.period_start_us, r.source_dataset_id))
        first = members_sorted[0]
        last = members_sorted[-1]
        high = max(m.high for m in members_sorted)
        low = min(m.low for m in members_sorted)
        base_v = sum((m.base_volume for m in members_sorted), Decimal("0"))
        # Quote: sum only if all present; else null (missing semantics preserved).
        quote_vals = [m.quote_volume for m in members_sorted]
        if any(v is None for v in quote_vals):
            quote_v: Decimal | None = None
        else:
            quote_v = sum((v for v in quote_vals if v is not None), Decimal("0"))
        trade_vals = [m.trade_count for m in members_sorted]
        if any(v is None for v in trade_vals):
            trade_count: int | None = None
        else:
            trade_count = sum(int(v) for v in trade_vals if v is not None)

        tb_base_vals = [
            m.taker_buy_base_volume
            for m in members_sorted
            if m.taker_buy_base_volume is not None
        ]
        tb_quote_vals = [
            m.taker_buy_quote_volume
            for m in members_sorted
            if m.taker_buy_quote_volume is not None
        ]
        # Only sum taker when every bar has the field.
        tb_base = (
            sum(tb_base_vals, Decimal("0"))
            if len(tb_base_vals) == len(members_sorted)
            else None
        )
        tb_quote = (
            sum(tb_quote_vals, Decimal("0"))
            if len(tb_quote_vals) == len(members_sorted)
            else None
        )
        period_end = day_us + 86_400_000_000
        # Lineage: single valid dataset_id only (never compound pseudo-IDs).
        source_ids = sorted({m.source_dataset_id for m in members_sorted})
        primary = source_ids[0]
        flags = ["resampled_from_intraday", "complete_utc_day"]
        if len(source_ids) > 1:
            flags.append("multi_source_day_primary_only")
        daily.append(
            _BarRow(
                instrument_id=instrument_id,
                venue_id=venue_id,
                market_type=market_type,
                timeframe="1d",
                period_start_us=day_us,
                period_end_us=period_end,
                availability_time_us=period_end,
                open=first.open,
                high=high,
                low=low,
                close=last.close,
                base_volume=base_v,
                quote_volume=quote_v,
                trade_count=trade_count,
                taker_buy_base_volume=tb_base,
                taker_buy_quote_volume=tb_quote,
                source_dataset_id=primary,
                quality_flags=flags,
            )
        )
    return daily


def _load_native_daily(
    inputs: Sequence[VerifiedDailySource],
    issues: list[QualityIssue],
) -> list[_BarRow]:
    rows: list[_BarRow] = []
    for inp in inputs:
        # Reuse verified loader with interval 1d.
        synthetic = VerifiedSourceBarDataset(
            local_files=inp.local_files,
            venue_id=inp.venue_id,
            instrument_id=inp.instrument_id,
            market_type=inp.market_type,
            interval="1d",
            schema_variant=inp.schema_variant,
            manifest=inp.manifest,
            receipt=inp.receipt,
        )
        _did, _q, loaded = _load_verified_bars(
            synthetic, interval_override="1d", issues=issues
        )
        for r in loaded:
            day = _day_start_us(r.period_start_us)
            rows.append(
                _BarRow(
                    instrument_id=r.instrument_id,
                    venue_id=r.venue_id,
                    market_type=r.market_type,
                    timeframe="1d",
                    period_start_us=day,
                    period_end_us=day + 86_400_000_000,
                    availability_time_us=day + 86_400_000_000,
                    open=r.open,
                    high=r.high,
                    low=r.low,
                    close=r.close,
                    base_volume=r.base_volume,
                    quote_volume=r.quote_volume,
                    trade_count=r.trade_count,
                    taker_buy_base_volume=r.taker_buy_base_volume,
                    taker_buy_quote_volume=r.taker_buy_quote_volume,
                    source_dataset_id=r.source_dataset_id,
                    quality_flags=list(r.quality_flags) + ["source_native_daily"],
                )
            )
    return rows


def _reconcile_daily(
    resampled: Sequence[_BarRow],
    native: Sequence[_BarRow],
    *,
    price_tolerance: Decimal,
    volume_tolerance: Decimal,
    issues: list[QualityIssue],
) -> tuple[list[dict[str, Any]], list[_BarRow]]:
    native_by_key: dict[tuple[int, str, int], _BarRow] = {}
    for n in native:
        key = (n.instrument_id, n.venue_id, n.period_start_us)
        if key in native_by_key:
            issues.append(
                QualityIssue(
                    code="bar001_native_daily_duplicate",
                    severity=IssueSeverity.ERROR,
                    message="duplicate native daily bar key",
                    context={
                        "instrument_id": n.instrument_id,
                        "venue_id": n.venue_id,
                        "period_start": n.period_start_us,
                    },
                )
            )
            continue
        native_by_key[key] = n

    report: list[dict[str, Any]] = []
    quarantine: list[_BarRow] = []
    matched: set[tuple[int, str, int]] = set()

    def _cmp(
        field_name: str,
        expected: Decimal | None,
        observed: Decimal | None,
        tol: Decimal,
        row: _BarRow,
        native_row: _BarRow,
    ) -> bool:
        if expected is None and observed is None:
            report.append(
                {
                    "instrument_id": row.instrument_id,
                    "venue_id": row.venue_id,
                    "period_start": row.period_start_us,
                    "field_name": field_name,
                    "expected": "null",
                    "observed": "null",
                    "abs_diff": "0",
                    "within_tolerance": True,
                    "status": "ok",
                    "source_dataset_id": row.source_dataset_id,
                    "native_dataset_id": native_row.source_dataset_id,
                }
            )
            return True
        if expected is None or observed is None:
            report.append(
                {
                    "instrument_id": row.instrument_id,
                    "venue_id": row.venue_id,
                    "period_start": row.period_start_us,
                    "field_name": field_name,
                    "expected": "null" if expected is None else str(expected),
                    "observed": "null" if observed is None else str(observed),
                    "abs_diff": "",
                    "within_tolerance": False,
                    "status": "null_mismatch",
                    "source_dataset_id": row.source_dataset_id,
                    "native_dataset_id": native_row.source_dataset_id,
                }
            )
            return False
        diff = abs(expected - observed)
        ok = diff <= tol
        report.append(
            {
                "instrument_id": row.instrument_id,
                "venue_id": row.venue_id,
                "period_start": row.period_start_us,
                "field_name": field_name,
                "expected": str(expected),
                "observed": str(observed),
                "abs_diff": str(diff),
                "within_tolerance": ok,
                "status": "ok" if ok else "mismatch",
                "source_dataset_id": row.source_dataset_id,
                "native_dataset_id": native_row.source_dataset_id,
            }
        )
        return ok

    for row in resampled:
        key = (row.instrument_id, row.venue_id, row.period_start_us)
        native_row = native_by_key.get(key)
        if native_row is None:
            report.append(
                {
                    "instrument_id": row.instrument_id,
                    "venue_id": row.venue_id,
                    "period_start": row.period_start_us,
                    "field_name": "*",
                    "expected": "",
                    "observed": "resampled_only",
                    "abs_diff": "",
                    "within_tolerance": False,
                    "status": "missing_native",
                    "source_dataset_id": row.source_dataset_id,
                    "native_dataset_id": "",
                }
            )
            issues.append(
                QualityIssue(
                    code="bar001_daily_missing_native",
                    severity=IssueSeverity.WARNING,
                    message="resampled daily bar has no native counterpart",
                    context={
                        "instrument_id": row.instrument_id,
                        "venue_id": row.venue_id,
                        "period_start": row.period_start_us,
                    },
                )
            )
            continue
        matched.add(key)
        ok = True
        ok = _cmp("open", native_row.open, row.open, price_tolerance, row, native_row) and ok
        ok = _cmp("high", native_row.high, row.high, price_tolerance, row, native_row) and ok
        ok = _cmp("low", native_row.low, row.low, price_tolerance, row, native_row) and ok
        ok = (
            _cmp("close", native_row.close, row.close, price_tolerance, row, native_row)
            and ok
        )
        ok = (
            _cmp(
                "base_volume",
                native_row.base_volume,
                row.base_volume,
                volume_tolerance,
                row,
                native_row,
            )
            and ok
        )
        ok = (
            _cmp(
                "quote_volume",
                native_row.quote_volume,
                row.quote_volume,
                volume_tolerance,
                row,
                native_row,
            )
            and ok
        )
        if not ok:
            quarantine.append(
                _BarRow(
                    instrument_id=row.instrument_id,
                    venue_id=row.venue_id,
                    market_type=row.market_type,
                    timeframe=row.timeframe,
                    period_start_us=row.period_start_us,
                    period_end_us=row.period_end_us,
                    availability_time_us=row.availability_time_us,
                    open=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    base_volume=row.base_volume,
                    quote_volume=row.quote_volume,
                    trade_count=row.trade_count,
                    taker_buy_base_volume=row.taker_buy_base_volume,
                    taker_buy_quote_volume=row.taker_buy_quote_volume,
                    source_dataset_id=row.source_dataset_id,
                    quality_flags=list(row.quality_flags) + ["daily_reconcile_mismatch"],
                )
            )
            issues.append(
                QualityIssue(
                    code="bar001_daily_reconcile_mismatch",
                    severity=IssueSeverity.ERROR,
                    message="resampled daily bar exceeds reconciliation tolerances",
                    context={
                        "instrument_id": row.instrument_id,
                        "venue_id": row.venue_id,
                        "period_start": row.period_start_us,
                        "price_tolerance": str(price_tolerance),
                        "volume_tolerance": str(volume_tolerance),
                    },
                )
            )

    for key, native_row in native_by_key.items():
        if key in matched:
            continue
        report.append(
            {
                "instrument_id": native_row.instrument_id,
                "venue_id": native_row.venue_id,
                "period_start": native_row.period_start_us,
                "field_name": "*",
                "expected": "native_only",
                "observed": "",
                "abs_diff": "",
                "within_tolerance": False,
                "status": "missing_resampled",
                "source_dataset_id": "",
                "native_dataset_id": native_row.source_dataset_id,
            }
        )
        issues.append(
            QualityIssue(
                code="bar001_daily_missing_resampled",
                severity=IssueSeverity.WARNING,
                message="native daily bar has no resampled counterpart",
                context={
                    "instrument_id": native_row.instrument_id,
                    "venue_id": native_row.venue_id,
                    "period_start": native_row.period_start_us,
                },
            )
        )
    return report, quarantine


def _partition_key(row: _BarRow) -> tuple[str, str, str, int, int]:
    dt = _us_to_datetime(row.period_start_us)
    return (row.venue_id, row.market_type, row.timeframe, dt.year, dt.month)


def _group_by_partition(
    rows: Sequence[_BarRow],
) -> dict[tuple[str, str, str, int, int], list[_BarRow]]:
    groups: dict[tuple[str, str, str, int, int], list[_BarRow]] = defaultdict(list)
    for row in rows:
        groups[_partition_key(row)].append(row)
    for key in groups:
        groups[key] = sorted(groups[key], key=_sort_key)
    return groups


def publish_canonical_bars(
    source_datasets: Sequence[VerifiedSourceBarDataset],
    *,
    output_dir: Path | str,
    code_commit: str,
    config_sha256: str | None = None,
    native_daily: Sequence[VerifiedDailySource] | None = None,
    price_tolerance: Decimal | str = Decimal("0"),
    volume_tolerance: Decimal | str = Decimal("0"),
    daily_source_timeframe: str | None = None,
    created_at: datetime | None = None,
) -> CanonicalBarPublishResult:
    """Publish canonical intraday + daily bars from verified MAN-001 sources.

    ``daily_source_timeframe`` selects the single intraday cadence used for
    daily resampling when multiple complete timeframes are present. If omitted
    and more than one complete timeframe exists, publication fails closed.

    ``created_at`` is an optional catalog bookkeeping timestamp; when omitted the
    publication uses a deterministic epoch timestamp and may not win
    resolve_latest_by_type against a dataset with a newer timestamp.
    """
    if not source_datasets:
        raise ValueError("at least one verified source_dataset is required")

    code_id = _require_code_commit(code_commit)
    price_tol = _to_decimal(price_tolerance)
    volume_tol = _to_decimal(volume_tolerance)
    if price_tol < 0 or volume_tol < 0:
        raise ValueError("tolerances must be >= 0")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    issues: list[QualityIssue] = []
    all_intraday: list[_BarRow] = []
    deps: list[DependencyRef] = []
    source_qualities: list[QualityStatus] = []
    source_ids: list[str] = []

    for src in source_datasets:
        did, q, rows = _load_verified_bars(src, interval_override=None, issues=issues)
        source_qualities.append(q)
        source_ids.append(did)
        deps.append(
            DependencyRef(
                id=did,
                kind=DependencyKind.DATASET,
                role="source_normalized_bars",
            )
        )
        all_intraday.extend(rows)

    unique_intraday, q_dups = _enforce_uniqueness(all_intraday, issues)
    # Intraday promotion keeps unique rows; incomplete days still appear as
    # intraday observations but cannot form daily bars.
    complete_for_daily, incomplete_q = _complete_days(unique_intraday, issues)
    # Canonicalize once for both selection behavior and config hash identity.
    resolved_daily_tf = _canonicalize_daily_source_timeframe(daily_source_timeframe)
    daily_input, effective_daily_tf = _select_rows_for_daily_resample(
        complete_for_daily,
        daily_source_timeframe=resolved_daily_tf,
    )
    daily = _resample_daily(daily_input)

    reconcile_rows: list[dict[str, Any]] = []
    q_daily: list[_BarRow] = []
    accepted_daily = list(daily)
    if native_daily:
        for nd in native_daily:
            nd_id, _nq, _files, _msha = _extract_verified_identity(
                manifest=nd.manifest, receipt=nd.receipt
            )
            deps.append(
                DependencyRef(
                    id=nd_id,
                    kind=DependencyKind.DATASET,
                    role="source_native_daily_bars",
                )
            )
        native_rows = _load_native_daily(native_daily, issues)
        reconcile_rows, q_daily = _reconcile_daily(
            daily,
            native_rows,
            price_tolerance=price_tol,
            volume_tolerance=volume_tol,
            issues=issues,
        )
        q_keys = {(r.instrument_id, r.venue_id, r.period_start_us) for r in q_daily}
        accepted_daily = [
            r
            for r in daily
            if (r.instrument_id, r.venue_id, r.period_start_us) not in q_keys
        ]

    quarantine_rows = q_dups + incomplete_q + q_daily

    output_sources: dict[str, Path] = {}
    output_specs: list[OutputFileSpec] = []
    row_counters: dict[str, Callable[[Path], int]] = {}
    partition_sizes: list[PartitionSizeMeasurement] = []
    intraday_paths: list[Path] = []
    daily_paths: list[Path] = []
    quarantine_paths: list[Path] = []
    reconcile_paths: list[Path] = []
    total_rows = 0
    total_bytes = 0
    min_event: datetime | None = None
    max_event: datetime | None = None

    def _track_coverage(rows: Sequence[_BarRow]) -> None:
        nonlocal min_event, max_event
        for r in rows:
            try:
                ts = _us_to_datetime(r.period_start_us)
            except (ValueError, OverflowError, OSError):
                issues.append(
                    QualityIssue(
                        code="bar001_invalid_period_start",
                        severity=IssueSeverity.ERROR,
                        message="period_start out of range for coverage",
                        context={"period_start": r.period_start_us},
                    )
                )
                continue
            if min_event is None or ts < min_event:
                min_event = ts
            if max_event is None or ts > max_event:
                max_event = ts

    def _emit_bar_partitions(
        rows: Sequence[_BarRow],
        *,
        kind: str,
        path_prefix: str,
        path_acc: list[Path],
    ) -> None:
        nonlocal total_rows, total_bytes
        groups = _group_by_partition(rows)
        for (venue, mkt, tf, year, month), part_rows in sorted(groups.items()):
            venue_t = _validate_path_token("venue_id", venue)
            mkt_t = _validate_market_type(mkt)
            tf_t = _validate_path_token("timeframe", tf)
            if year < 1970 or year > 2100 or month < 1 or month > 12:
                raise ValueError(
                    f"invalid year/month partition year={year} month={month}"
                )
            rel = (
                f"{path_prefix}/venue_id={venue_t}/market_type={mkt_t}/"
                f"timeframe={tf_t}/year={year:04d}/month={month:02d}/bars.parquet"
            )
            nested = out_dir / rel
            nested.parent.mkdir(parents=True, exist_ok=True)
            sha, nbytes, nrows = _write_bars_parquet(nested, part_rows)
            path_acc.append(nested)
            output_sources[rel] = nested
            row_counters[rel] = _parquet_row_counter
            output_specs.append(
                OutputFileSpec(
                    relative_path=rel,
                    sha256=sha,
                    rows=nrows,
                    bytes=nbytes,
                    partition={
                        "venue_id": venue_t,
                        "market_type": mkt_t,
                        "timeframe": tf_t,
                        "year": year,
                        "month": month,
                        "kind": kind,
                        "timestamp_storage": "utc_microseconds",
                    },
                    rows_verified=True,
                )
            )
            partition_sizes.append(
                PartitionSizeMeasurement(
                    relative_path=rel,
                    rows=nrows,
                    bytes=nbytes,
                    venue_id=venue_t,
                    market_type=mkt_t,
                    timeframe=tf_t,
                    year=year,
                    month=month,
                    kind=kind,
                )
            )
            total_rows += nrows
            total_bytes += nbytes
            _track_coverage(part_rows)

    _emit_bar_partitions(
        unique_intraday,
        kind="intraday",
        path_prefix="market_bars/intraday",
        path_acc=intraday_paths,
    )
    _emit_bar_partitions(
        accepted_daily,
        kind="daily",
        path_prefix="market_bars/daily",
        path_acc=daily_paths,
    )
    if quarantine_rows:
        _emit_bar_partitions(
            quarantine_rows,
            kind="quarantine",
            path_prefix="market_bars/quarantine",
            path_acc=quarantine_paths,
        )

    rel_rec = "market_bars/reconcile/daily_tolerance_report.parquet"
    rec_path = out_dir / rel_rec
    rec_path.parent.mkdir(parents=True, exist_ok=True)
    rec_sha, rec_bytes, rec_n = _write_reconcile_parquet(rec_path, reconcile_rows)
    reconcile_paths.append(rec_path)
    output_sources[rel_rec] = rec_path
    row_counters[rel_rec] = _parquet_row_counter
    output_specs.append(
        OutputFileSpec(
            relative_path=rel_rec,
            sha256=rec_sha,
            rows=rec_n,
            bytes=rec_bytes,
            partition={"kind": "reconcile"},
            rows_verified=True,
        )
    )
    total_rows += rec_n
    total_bytes += rec_bytes
    partition_sizes.append(
        PartitionSizeMeasurement(
            relative_path=rel_rec,
            rows=rec_n,
            bytes=rec_bytes,
            venue_id="",
            market_type="",
            timeframe="1d",
            year=0,
            month=0,
            kind="reconcile",
        )
    )

    if not unique_intraday and not any(i.code == "bar001_empty_canonical" for i in issues):
        issues.append(
            QualityIssue(
                code="bar001_empty_canonical",
                severity=IssueSeverity.ERROR,
                message="no canonical intraday bars produced from verified sources",
                context={},
            )
        )

    rel_q = "market_bars/quality/issues.parquet"
    q_path = out_dir / rel_q
    q_path.parent.mkdir(parents=True, exist_ok=True)
    q_sha, q_bytes, q_n = _write_quality_parquet(q_path, issues)
    output_sources[rel_q] = q_path
    row_counters[rel_q] = _parquet_row_counter
    output_specs.append(
        OutputFileSpec(
            relative_path=rel_q,
            sha256=q_sha,
            rows=q_n,
            bytes=q_bytes,
            partition={"kind": "quality"},
            rows_verified=True,
        )
    )
    total_rows += q_n
    total_bytes += q_bytes

    has_error = any(i.severity is IssueSeverity.ERROR for i in issues)
    has_warn = any(i.severity is IssueSeverity.WARNING for i in issues)
    source_has_warn = any(q is QualityStatus.PASS_WITH_WARNINGS for q in source_qualities)

    if has_error or not unique_intraday:
        q_status = QualityStatus.REJECTED
    elif has_warn or source_has_warn:
        # Canonical quality is never better than accepted source quality.
        q_status = QualityStatus.PASS_WITH_WARNINGS
    else:
        q_status = QualityStatus.PASS

    cfg_payload = {
        "dataset_type": MARKET_BARS_DATASET_TYPE,
        "schema_name": CANONICAL_BAR_SCHEMA_NAME,
        "schema_version": CANONICAL_BAR_SCHEMA_VERSION,
        "transform_name": CANONICAL_BAR_TRANSFORM_NAME,
        "transform_version": CANONICAL_BAR_TRANSFORM_VERSION,
        "price_tolerance": str(price_tol),
        "volume_tolerance": str(volume_tol),
        "source_dataset_ids": sorted(set(source_ids)),
        "availability_policy": "period_end_exclusive",
        "complete_day_required_for_daily": True,
        # Canonical selected TF only (stripped/validated); never raw caller string.
        "daily_source_timeframe": effective_daily_tf,
        "partitioning": ["venue_id", "market_type", "timeframe", "year", "month"],
        "timestamp_storage": "utc_microseconds",
        "verified_man001_inputs": True,
        "supported_source_dataset_type": _SUPPORTED_SOURCE_DATASET_TYPE,
        "supported_source_schema": (
            f"{_SUPPORTED_SOURCE_SCHEMA_NAME}:{_SUPPORTED_SOURCE_SCHEMA_VERSION}"
        ),
    }
    cfg_hash = _resolve_config_sha256(config_sha256, payload=cfg_payload)

    size_summary = [
        {
            "relative_path": m.relative_path,
            "rows": m.rows,
            "bytes": m.bytes,
            "kind": m.kind,
            "year": m.year,
            "month": m.month,
        }
        for m in partition_sizes
    ]

    plan = PublishPlan(
        dataset_type=MARKET_BARS_DATASET_TYPE,
        schema=SchemaIdentity(
            name=CANONICAL_BAR_SCHEMA_NAME,
            version=CANONICAL_BAR_SCHEMA_VERSION,
            fingerprint=hashlib.sha256(
                json.dumps(
                    {
                        "name": CANONICAL_BAR_SCHEMA_NAME,
                        "version": CANONICAL_BAR_SCHEMA_VERSION,
                        "fields": [f.name for f in _canonical_bar_schema()],
                        "nullable": [
                            "quote_volume",
                            "trade_count",
                            "taker_buy_base_volume",
                            "taker_buy_quote_volume",
                        ],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()[:16],
        ),
        transform=TransformSpec(
            name=CANONICAL_BAR_TRANSFORM_NAME,
            version=CANONICAL_BAR_TRANSFORM_VERSION,
        ),
        code=CodeIdentity(commit=code_id),
        config=ConfigIdentity(config_sha256=cfg_hash),
        dependencies=tuple(deps),
        output_sources=output_sources,
        output_specs=output_specs,
        statistics=DatasetStatistics(row_count=total_rows, byte_size=total_bytes),
        coverage=CoverageWindow(event_start=min_event, event_end=max_event),
        quality_status=q_status,
        quality_summary={
            "issue_count": len(issues),
            "intraday_rows": len(unique_intraday),
            "daily_rows": len(accepted_daily),
            "quarantine_rows": len(quarantine_rows),
            "reconcile_rows": len(reconcile_rows),
            "price_tolerance": str(price_tol),
            "volume_tolerance": str(volume_tol),
            "partition_sizes": size_summary,
            "normalizer_version": CANONICAL_BAR_TRANSFORM_VERSION,
            "timestamp_storage": "utc_microseconds",
            "availability_policy": "period_end_exclusive",
            "source_quality_gate": "verified MAN-001 PASS|PASS_WITH_WARNINGS only",
            "source_qualities": [q.value for q in source_qualities],
            "complete_day_required_for_daily": True,
            "daily_source_timeframe": effective_daily_tf,
            "manifest_identity_recomputed": True,
            "economic_fingerprint_excludes_lineage": True,
        },
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters=row_counters,
        created_at=created_at,
    )

    return CanonicalBarPublishResult(
        publish_plan=plan,
        intraday_paths=tuple(intraday_paths),
        daily_paths=tuple(daily_paths),
        reconcile_paths=tuple(reconcile_paths),
        quarantine_paths=tuple(quarantine_paths),
        partition_sizes=tuple(partition_sizes),
        issues=tuple(issues),
    )
