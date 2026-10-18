"""Prepare the CEX-002 harmonic bundle and hand it to the reference catalog.

Accepted product trees stay where they are. This module authenticates their
completions, writes one new bundle Parquet, and asks the catalog adapter to
reference every other file in place. Receipt 258 records 1,133,590 measured
current bytes and 150,331 projected rows. The 24,352,003-byte figure is the
future-only harmonic_bundle charge and remains the actual file cap. It is not
the 5,556,368,003-byte metadata pool. Coverage's unused reservation is not
added back. Catalog commit is the visibility gate. A prepared descriptor is
not a release.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset.cex002_reference_release import (
    CURRENT_PLUS_FUTURE_PROVISION_BYTES,
    FUTURE_BUNDLE_DICTIONARY_BYTES,
    FUTURE_PARTITION_FIELD_BYTES,
    FUTURE_REFERENCE_INDEX_BYTES_PER_ROW,
    HARMONIC_BUNDLE_ALLOCATION_BYTES,
    MEASURED_CURRENT_BUNDLE_BYTES,
    OPERATING_RESERVE_BYTES,
    PROOF_MAX_BYTES,
    RELEASE_METADATA_BYTES,
    RELEASE_METADATA_REMAINDER_BYTES,
    SIZING_PROJECTED_BUNDLE_ROWS,
    ReleaseError,
    ReleaseHooks,
    ReleasePolicy,
    PreparedRelease,
    PublishedRelease,
    ReferenceDatasetPlan,
    ReferenceFile,
    identify_products,
    prepare_release,
    production_release_policy,
    publish_release,
    read_release,
    seal_code_identity,
    write_new_bundle_object,
)
from cryptofactors.catalog.dataset.errors import DatasetError
from cryptofactors.catalog.dataset.paths import (
    assert_no_symlink_components,
    assert_regular_file,
    assert_relative_safe,
    lexical_join,
)
from cryptofactors.ingest.binance_usdm_coverage import (
    COMPLETION_SHA256,
    MAX_JSON_BYTES,
    METADATA_BUDGET_BYTES,
    QUALITY_GAP_SCHEMA,
    SOURCE_GAP_SCHEMA,
    TYPED_GAP_SCHEMA,
)

PRODUCT_BUNDLE = "binance_usdm_harmonic_bundle"
PRODUCT_COVERAGE = "binance_usdm_coverage_gap"
PRODUCT_COST = "binance_usdm_cost_calibration"
PRODUCT_MEMBERSHIP = "binance_usdm_perpetual_membership"
HASH_CHUNK_BYTES = 1024 * 1024
SIZING_RECEIPT_BYTES = 39_727_059
SIZING_READ_LIMIT = 48 * 1024 * 1024
BUNDLE_ROW_INDEX_BOUND = 300_662
SIZING_ROW_BATCH = 65_536
PARQUET_COMPRESSION = "zstd"
PARQUET_COMPRESSION_LEVEL = 3
PARQUET_VERSION = "2.6"
REF_IDENTITY_STATE = "reference_identity_not_yet_created"
UNIT_CONVENTION = "base_and_quote_units_as_published_by_the_venue"
CENSORSHIP_SEMANTICS = "observed_and_censored_aggregate_never_complete"
FEE_AUTHORITY_CLASS = "ASSUMED_CONSERVATIVE"
FEE_GAP_KIND = "historical_fee_schedule_unavailable"
FEE_POLICY_KNOWN_AT = "2026-08-23T03:00:00Z"
ABSENT_MONTH = "absent"
AUTHORITY_MONTH = "authority"
REPORT_SHA256 = "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
MANIFEST_DETAIL_SHA256 = "64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113"
QUALIFICATION_CODE_SHA256 = "2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74"
QUALIFICATION_CLI_SHA256 = "473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f"
SIZING_SHA256 = "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589"
HOLDOUT_SHA256 = "2030e20aa5bd73df8fdbb7467e928508103b2e23659b85527101ec8b8546cb85"
HOLDOUT_ID = "c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2"
HOLDOUT_UTC = "2026-08-21T16:19:08.994166+00:00"
RECON_COMPLETION_SHA256 = "e3c8f9f5ade1b92069b97e6b83931c345886d40901b85b1c4106604edd9b5e5c"
RECON_REPORT_SHA256 = "96ae8db169666598643ac4e2f9aa2136b77c0dbeeaa90d2a3e4e4de9e983c89c"
FAILED_REPORT_SHA256 = "809d7d5338985fb0625a823ff8908eeab2c77e9406e5979d2fb8702cd17dfe10"
COVERAGE_COMPLETION_SHA256 = "9e6e191b9ac1de05de4302e9e6dad64315f7e75d28ade638b977e28e68da1151"
OBSERVED_DAY_COUNT = 428_090
OBSERVED_DAY_SHA256 = "f0c0d7c21fc68d2d454b07ec969b6d794f380e22e751c643dee09184e3896665"
FULL_CADENCE_DAY_COUNT = 424_431
FULL_CADENCE_DAY_SHA256 = "22219a5a243fcf1fda3ab5deacd99fbe72869375021d9d2f2a98868580e48fab"
ALIGNED_DAY_ROWS = 1_971_447
SOURCE_GAP_ROW_PIN = 8_317
TYPED_GAP_ROW_PIN = 3_742
QUALITY_GAP_ROW_PIN = 68_220
FEE_AUTHORITY_GAP_ROWS = 771
COST_SOURCE_GAP_ROWS = 494
COST_SOURCE_GAP_SHA256 = "aace941a43e38c2f790fed4c383e08cbbd27d3f5f7215bc95b50bb134ae3519e"
COST_SOURCE_GAP_BYTES = 178_783
UNUSED_COVERAGE_RESERVATION_BYTES = 114_144_134
TICKER_PROJECTED_ROWS = 745_543_507
TICKER_ACTUAL_ROWS = 882_076_090
TICKER_EXCESS_ROWS = 136_532_583
TICKER_STATUS = "EXCEEDED_REVIEWED_EXACT_ARTIFACT_VARIANCE"
MEMBERSHIP_ACCEPTED_PIN = 771
MEMBERSHIP_EXCLUDED_PIN = 237
MEMBERSHIP_FUNDING_ONLY_PIN = 73
QUALITY_ROWS_BY_PRODUCT = {
    "binance_usdm_bar_1h": 154,
    "binance_usdm_trade_flow_1h": 181,
    "binance_usdm_open_interest_5m": 57_441,
    "binance_usdm_funding_indicative_1h": 1_215,
    "binance_usdm_mark_index_basis_1h": 4_603,
    "binance_usdm_liquidation_observed_daily": 4_626,
}
RECON_MATCHED_FIELDS = 2_672
RECON_FIELD_DENOMINATOR = 2_672
RECON_COMPARED_HOURS = 167
RECON_DISTINCT_DAYS = 9
RECON_LOGICAL_ROLES = 10
RECON_ROLES_WITH_HOUR = 10
COST_COMPONENTS = (
    "retained_book_ticker",
    "retained_book_depth",
    "official_fee_schedule",
    "fee_authority_gap",
    "scenario_policy",
)
COVERAGE_PAGES = (
    "daily",
    "summary",
    "source_gap",
    "typed_gap",
    "quality_gap",
    "excluded_membership",
)
QUALIFICATION_RELATIVE = "research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json"
SIZING_RELATIVE = "research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json"
HOLDOUT_RELATIVE = "data/cex002_qualify/cex002_holdout_boundary.json"
RECON_ROOT = "data/.cex002_kline_reconciliation"
REPORT_DOCUMENT = "cex002_bounded_kline_reconciliation_report"
COMPLETION_DOCUMENT = "cex002_bounded_kline_reconciliation_completion"
_DICTIONARY = str(pa.dictionary(pa.int32(), pa.string()))
_STRING = str(pa.string())
_INT64 = str(pa.int64())

BUNDLE_FIELDS: tuple[tuple[str, str, bool], ...] = (
    ("required_product", _DICTIONARY, False),
    ("component", _DICTIONARY, False),
    ("dataset_id", _DICTIONARY, False),
    ("native_symbol", _DICTIONARY, False),
    ("canonical_instrument_id", _DICTIONARY, True),
    ("canonical_instrument_version_id", _DICTIONARY, True),
    ("reference_identity_state", _DICTIONARY, False),
    ("utc_month", _DICTIONARY, False),
    ("partition_sha256", _STRING, True),
    ("partition_bytes", _INT64, True),
    ("row_count", _INT64, True),
    ("schema_sha256", _STRING, False),
    ("lineage_manifest_sha256", _STRING, True),
    ("lineage_mapping_count", _INT64, False),
    ("source_report_sha256", _STRING, False),
    ("source_manifest_detail_sha256", _STRING, False),
    ("qualification_code_sha256", _STRING, False),
    ("qualification_cli_sha256", _STRING, False),
    ("sizing_code_sha256", _STRING, False),
    ("sizing_cli_sha256", _STRING, False),
    ("configuration_sha256", _STRING, False),
    ("scenario_policy_sha256", _STRING, False),
    ("unit_convention", _DICTIONARY, False),
    ("censorship_semantics", _DICTIONARY, False),
    ("coverage_gap_rows", _INT64, False),
    ("typed_gap_membership_rows", _INT64, False),
    ("fee_authority_gap_rows", _INT64, False),
    ("cross_product_intersection_count", _INT64, False),
    ("cross_product_intersection_sha256", _STRING, False),
)


@dataclass(frozen=True, slots=True)
class ProductSpec:
    dataset_type: str
    root: str
    family: str
    completion_sha256: str


@dataclass(frozen=True, slots=True)
class AssemblyPolicy:
    """Private test injection lives on this object. The CLI cannot override pins."""

    repo: Path
    catalog_path: Path
    code_commit: str
    bind_runtime: bool = False
    executing: Mapping[str, Path] | None = None
    file_bytes: Mapping[str, bytes] | None = None
    authenticate_production_receipt: bool = False
    observed_free_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class _File:
    relative_path: str
    sha256: str
    byte_size: int
    rows: int
    is_table: bool
    schema_fields: tuple[tuple[str, str, bool], ...]
    partition: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _BundleSource:
    owner: str
    required_product: str
    component: str
    native_symbol: str
    utc_month: str
    partition_sha256: str
    partition_bytes: int
    row_count: int
    schema_sha256: str
    lineage_sha256: str | None
    lineage_mapping_count: int


@dataclass(frozen=True, slots=True)
class _ProductAccount:
    spec: ProductSpec
    completion_sha256: str
    files: tuple[_File, ...]
    bundle_sources: tuple[_BundleSource, ...]
    schema_fingerprint: str
    quality: dict[str, Any]
    retained_audit: dict[str, Any] | None = None


PRODUCTS: tuple[ProductSpec, ...] = (
    ProductSpec(PRODUCT_MEMBERSHIP, "data/.cex002_perpetual_membership", "membership", "01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3"),
    ProductSpec("binance_usdm_bar_1h", "data/.cex002_bar_1h", "partition", "3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7"),
    ProductSpec("binance_usdm_trade_flow_1h", "data/.cex002_trade_flow_1h", "partition", "a165f9e57065514cadc95620c280a82dbad5032d17c19e1caf012c9d12a84d0a"),
    ProductSpec("binance_usdm_open_interest_5m", "data/.cex002_open_interest_5m", "partition", "bb089fc992326c66ddb65cea03dda92e8cd9fcf7cb7f373821f04a16db9168e4"),
    ProductSpec("binance_usdm_funding_realized", "data/.cex002_funding_realized", "partition", "57628164f19d182164b6058d9e51f794430cc918706c088f430e1c01d2898522"),
    ProductSpec("binance_usdm_funding_indicative_1h", "data/.cex002_price_state/binance_usdm_funding_indicative_1h", "partition", "360eb662ab89c47ca1f6db754b74f486a42de4aa116970221f0739268a51fba0"),
    ProductSpec("binance_usdm_mark_index_basis_1h", "data/.cex002_price_state/binance_usdm_mark_index_basis_1h", "partition", "b698c0543c281e3244e0c3358ea7ce1f347bc591b06a076058fed749d05584f0"),
    ProductSpec("binance_usdm_liquidation_observed_daily", "data/.cex002_liquidation_observed_daily", "liquidation", "dc4127dccad31477cb72ec6fdf076dbdbdef34a1212d4f090d5f421b96dc267f"),
    ProductSpec(PRODUCT_COST, "data/.cex002_cost_calibration", "cost", "fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e"),
    ProductSpec(PRODUCT_COVERAGE, "data/.cex002_coverage", "coverage", COVERAGE_COMPLETION_SHA256),
)

_RETAINED_KLINE_COUNTS: Mapping[str, tuple[int, int]] = {
    "binance_usdm_bar_1h": (31, 20_335),
    "binance_usdm_trade_flow_1h": (47, 20_335),
}


def _fail(blocker: str, message: str, **context: Any) -> Any:
    raise ReleaseError(message, blocker=blocker, context=context)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _compact(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def _hex64(value: object, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        _fail("identity_pin", f"{label} is not lowercase sha256", label=label)
    return value


def _whole(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail("row_mismatch", f"{label} is not a non-negative integer", label=label)
    return value


def _safe(relative: str, label: str) -> str:
    try:
        return assert_relative_safe(relative, label=label)
    except DatasetError as exc:
        _fail("unsafe_path", f"{label} is not a safe relative path", label=label, error=str(exc))


def _component(value: object, label: str) -> str:
    if type(value) is not str or not value or "/" in value or "\\" in value or value in {".", ".."}:
        _fail("unsafe_path", f"{label} is unsafe", label=label)
    return value


def release_configuration() -> dict[str, str]:
    """Pin map whose pretty digest is the shared catalog configuration."""

    return {
        "failed_reconciliation_report_sha256": FAILED_REPORT_SHA256,
        "holdout_boundary_id": HOLDOUT_ID,
        "holdout_sha256": HOLDOUT_SHA256,
        "holdout_utc": HOLDOUT_UTC,
        "qualification_cli_sha256": QUALIFICATION_CLI_SHA256,
        "qualification_code_sha256": QUALIFICATION_CODE_SHA256,
        "qualification_manifest_detail_sha256": MANIFEST_DETAIL_SHA256,
        "qualification_report_sha256": REPORT_SHA256,
        "reconciliation_completion_sha256": RECON_COMPLETION_SHA256,
        "reconciliation_report_sha256": RECON_REPORT_SHA256,
        "sizing_sha256": SIZING_SHA256,
    }


def scenario_policy_document() -> dict[str, Any]:
    """Fee scenarios are assumptions. Missing history is not a zero fee."""

    return {
        "authority_class": FEE_AUTHORITY_CLASS,
        "charges_each_side": True,
        "gap_kind": FEE_GAP_KIND,
        "historical_observation": False,
        "historical_upper_bound": False,
        "missing_fee_is_zero": False,
        "policy_known_at": FEE_POLICY_KNOWN_AT,
        "scenarios": [
            {
                "maker": "0.0005",
                "name": "assumed_conservative_5bps_per_side_v1",
                "role": "primary_assumption",
                "taker": "0.0005",
            },
            {
                "maker": "0.0010",
                "name": "assumed_severe_10bps_per_side_v1",
                "role": "required_sensitivity",
                "taker": "0.0010",
            },
        ],
    }


def release_metadata_budget(unused_coverage_reservation_bytes: int) -> int:
    """Return the post-coverage remainder. The unused reservation stays unused."""

    if type(unused_coverage_reservation_bytes) is not int or unused_coverage_reservation_bytes < 0:
        _fail("metadata_remainder_exceeded", "unused coverage reservation is not a byte count")
    return RELEASE_METADATA_REMAINDER_BYTES


def _contract(fields: Sequence[tuple[str, str, bool]]) -> list[dict[str, Any]]:
    return [{"name": name, "arrow_type": arrow, "nullable": nullable} for name, arrow, nullable in fields]


def _normalize_arrow(arrow_type: str) -> str:
    if arrow_type in {
        "dictionary<values=string, indices=int32, ordered=0>",
        "dictionary<values=string, indices=int32, ordered=false>",
    }:
        return "dictionary<values=string, indices=int32>"
    if arrow_type in {"list<item: string>", "list<element: string>"}:
        return "list<string>"
    return arrow_type


def _normalize_contract(rows: Sequence[Mapping[str, Any]]) -> list[tuple[str, str, bool]]:
    normalized = []
    for row in rows:
        if type(row) is not dict or type(row.get("nullable")) is not bool:
            _fail("schema_mismatch", "schema contract field is malformed")
        name = row.get("name")
        arrow = row.get("arrow_type")
        if type(name) is not str or type(arrow) is not str:
            _fail("schema_mismatch", "schema contract field is malformed")
        normalized.append((name, _normalize_arrow(arrow), row["nullable"]))
    return normalized


def _schema_sha_pretty(body: Mapping[str, Any]) -> str:
    return _sha256(_pretty(dict(body)))


def _schema_sha_compact(fields: Sequence[Mapping[str, Any]]) -> str:
    return _sha256(_compact(list(fields)))


def _open_reference(root: Path, relative: str) -> tuple[str, int]:
    safe = _safe(relative, "reference path")
    path = lexical_join(root, safe)
    try:
        assert_no_symlink_components(path, stop_at=root)
        assert_regular_file(path, label=safe)
    except DatasetError as exc:
        _fail("unsafe_path", "reference path is unsafe", path=safe, error=str(exc))
    return safe, os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)


def _hash_reference(root: Path, relative: str, maximum: int | None) -> tuple[str, int]:
    """Stream a digest. The payload is not retained."""

    safe, descriptor = _open_reference(root, relative)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail("unsafe_path", "reference is not a regular file", path=safe)
        if maximum is not None and before.st_size > maximum:
            _fail("metadata_bound", "metadata document exceeds its read bound", path=safe, byte_size=before.st_size)
        digest = hashlib.sha256()
        size = 0
        while block := os.read(descriptor, HASH_CHUNK_BYTES):
            digest.update(block)
            size += len(block)
            if maximum is not None and size > maximum:
                _fail("metadata_bound", "metadata document exceeds its read bound", path=safe)
        after = os.fstat(descriptor)
        if before.st_ino != after.st_ino or before.st_dev != after.st_dev or before.st_size != after.st_size or size != before.st_size:
            _fail("reference_mismatch", "reference changed while hashing", path=safe)
        return digest.hexdigest(), size
    finally:
        os.close(descriptor)


def _read_bounded(root: Path, relative: str, maximum: int) -> tuple[str, int, bytes]:
    """Read metadata only after its size is known to fit the cap."""

    safe, descriptor = _open_reference(root, relative)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail("unsafe_path", "reference is not a regular file", path=safe)
        if before.st_size > maximum:
            _fail("metadata_bound", "metadata document exceeds its read bound", path=safe, byte_size=before.st_size)
        digest = hashlib.sha256()
        payload = bytearray()
        while block := os.read(descriptor, HASH_CHUNK_BYTES):
            if len(payload) + len(block) > maximum:
                _fail("metadata_bound", "metadata document exceeds its read bound", path=safe)
            digest.update(block)
            payload.extend(block)
        after = os.fstat(descriptor)
        if before.st_ino != after.st_ino or before.st_size != after.st_size or len(payload) != before.st_size:
            _fail("reference_mismatch", "reference changed while reading", path=safe)
        return digest.hexdigest(), len(payload), bytes(payload)
    finally:
        os.close(descriptor)


def _load_json(root: Path, relative: str, maximum: int, expected: str | None = None) -> tuple[dict[str, Any], str, int]:
    digest, size, payload = _read_bounded(root, relative, maximum)
    if expected is not None and digest != expected:
        _fail("reference_mismatch", "metadata digest mismatch", path=relative)
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ReleaseError(
            "metadata is not JSON",
            blocker="malformed_metadata",
            context={"path": relative},
        ) from exc
    if type(document) is not dict:
        _fail("malformed_metadata", "metadata root is not an object", path=relative)
    return document, digest, size


def _footer(root: Path, relative: str, declared_rows: int) -> tuple[tuple[str, str, bool], ...]:
    path = lexical_join(root, _safe(relative, "parquet path"))
    parquet = pq.ParquetFile(path)
    observed = int(parquet.metadata.num_rows)
    if observed != declared_rows:
        _fail(
            "row_mismatch",
            "Parquet footer row count mismatch",
            path=relative,
            footer_rows=observed,
            declared_rows=declared_rows,
        )
    return tuple((field.name, str(field.type), bool(field.nullable)) for field in parquet.schema_arrow)


def _require_equal_contract(actual: Sequence[tuple[str, str, bool]], expected: pa.Schema, label: str) -> None:
    wanted = tuple((field.name, str(field.type), bool(field.nullable)) for field in expected)
    if tuple((name, _normalize_arrow(arrow), nullable) for name, arrow, nullable in actual) != tuple(
        (name, _normalize_arrow(arrow), nullable) for name, arrow, nullable in wanted
    ):
        _fail("schema_mismatch", "Parquet footer schema mismatch", label=label)


def _bases(spec: ProductSpec) -> tuple[str, ...]:
    if spec.root.startswith("data/.cex002_price_state/"):
        parent = str(Path(spec.root).parent).replace("\\", "/")
        return (spec.root, parent)
    return (spec.root,)


def _resolve(root: Path, spec: ProductSpec, relative: str) -> tuple[str, str, int]:
    safe = _safe(str(relative), "descriptor path")
    found: list[tuple[str, str, int]] = []
    for base in _bases(spec):
        repo_relative = _safe(f"{base}/{safe}", "reference path")
        path = lexical_join(root, repo_relative)
        if path.is_symlink() or path.exists():
            digest, size = _hash_reference(root, repo_relative, None)
            found.append((repo_relative, digest, size))
    if not found:
        _fail("reference_mismatch", "referenced artifact is absent", path=safe)
    if len(found) == 2 and (found[0][1], found[0][2]) != (found[1][1], found[1][2]):
        _fail("mixed_authority", "descriptor resolves to two different artifacts", path=safe)
    return found[0]


def _walk(root: Path, spec: ProductSpec) -> set[str]:
    base = lexical_join(root, _safe(spec.root, "product root"))
    if not base.is_dir() or base.is_symlink():
        _fail("unsafe_path", "product root is not a real directory", path=spec.root)
    found: set[str] = set()
    for directory, dirnames, filenames in os.walk(base, followlinks=False):
        current = Path(directory)
        for name in list(dirnames):
            child = current / name
            if child.is_symlink():
                _fail("unsafe_path", "product tree contains a symlink", path=str(child))
        for name in filenames:
            child = current / name
            if child.is_symlink() or not stat.S_ISREG(child.lstat().st_mode):
                _fail("unsafe_path", "product tree contains a non-regular file", path=str(child))
            found.add(child.relative_to(base).as_posix())
            if spec.dataset_type in _RETAINED_KLINE_COUNTS and len(found) > 65_650:
                _fail("metadata_bound", "kline physical inventory exceeds the accepted bound", product=spec.dataset_type)
    return found


_PATH_ROOTS = frozenset(
    {
        ".partitions",
        ".quality-gaps",
        ".lineage",
        ".quality-gap-lineage",
        ".source-gaps",
        ".typed-gaps",
        ".source-gaps-lineage",
        ".typed-gaps-lineage",
        ".quality-gaps-lineage",
        ".authority-gaps",
        ".authority-gap-lineage",
        ".daily",
        ".summary",
    }
)
_GLOBAL_ROOTS = frozenset({".quality-gaps", ".authority-gaps", ".quality-gap-lineage", ".authority-gap-lineage"})


def _retained_kline_inventory(
    root: Path, spec: ProductSpec, extras: set[str], *, production: bool
) -> dict[str, Any]:
    """Authenticate excluded Review-459 files without making them dataset inputs."""

    parquet_limit, lineage_limit = _RETAINED_KLINE_COUNTS[spec.dataset_type]
    counts = {"parquet": 0, "lineage": 0}
    byte_counts = {"parquet": 0, "lineage": 0}
    inventory = hashlib.sha256()
    if len(extras) > parquet_limit + lineage_limit:
        _fail("metadata_bound", "retained kline inventory exceeds the accepted bound", product=spec.dataset_type)
    for relative in sorted(extras):
        safe = _safe(relative, "retained kline path")
        parts = safe.split("/")
        if len(parts) != 4:
            _fail("reference_mismatch", "retained kline path has an unknown shape", product=spec.dataset_type, path=relative)
        folder, symbol, month, filename = parts
        if folder == ".partitions":
            kind, suffix, limit = "parquet", ".parquet", parquet_limit
        elif folder == ".lineage":
            kind, suffix, limit = "lineage", ".json", lineage_limit
        else:
            _fail("reference_mismatch", "retained kline file has an unknown class", product=spec.dataset_type, path=relative)
        if (
            re.fullmatch(r"[A-Z0-9]{1,40}", symbol) is None
            or re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month) is None
            or not filename.endswith(suffix)
            or re.fullmatch(r"[0-9a-f]{64}", filename[: -len(suffix)]) is None
        ):
            _fail("reference_mismatch", "retained kline filename is not canonical", product=spec.dataset_type, path=relative)
        counts[kind] += 1
        if counts[kind] > limit:
            _fail("metadata_bound", "retained kline kind exceeds the accepted bound", product=spec.dataset_type, path=relative)
        repo_relative = f"{spec.root}/{safe}"
        digest, size = _hash_reference(root, repo_relative, None)
        if digest != filename[: -len(suffix)]:
            _fail("reference_mismatch", "retained kline content differs from its filename", product=spec.dataset_type, path=repo_relative)
        byte_counts[kind] += size
        inventory.update(_compact({"kind": kind, "path": repo_relative, "sha256": digest, "bytes": size}))
    if production and (counts["parquet"], counts["lineage"]) != (parquet_limit, lineage_limit):
        _fail(
            "reference_mismatch", "retained kline inventory differs from Review 459",
            product=spec.dataset_type, parquet_count=counts["parquet"], lineage_count=counts["lineage"],
            expected_parquet_count=parquet_limit, expected_lineage_count=lineage_limit,
        )
    return {
        "parquet_count": counts["parquet"], "parquet_bytes": byte_counts["parquet"],
        "lineage_count": counts["lineage"], "lineage_bytes": byte_counts["lineage"],
        "inventory_sha256": inventory.hexdigest(),
    }


def _declared_text(document: Mapping[str, Any], key: str) -> str | None:
    if key not in document:
        return None
    value = document.get(key)
    if type(value) is not str or not value:
        _fail("identity_pin", f"{key} is present but empty", key=key)
    return value


def _path_identity(relative_under_product: str) -> tuple[str | None, str | None, bool]:
    parts = tuple(part for part in relative_under_product.split("/") if part)
    if len(parts) >= 4 and parts[0] in _PATH_ROOTS:
        return parts[1], parts[2], False
    if len(parts) == 2 and parts[0] in _GLOBAL_ROOTS:
        return None, None, True
    return None, None, False


def _resolve_symbol(
    descriptor: Mapping[str, Any],
    lineage: Mapping[str, Any] | None,
    relative_under_product: str,
) -> str:
    declared = _declared_text(descriptor, "native_symbol")
    if declared is not None:
        return declared
    if lineage is not None:
        declared = _declared_text(lineage, "native_symbol")
        if declared is not None:
            return declared
    symbol, _month, global_artifact = _path_identity(relative_under_product)
    if symbol is not None:
        return symbol
    if global_artifact:
        return ABSENT_MONTH
    _fail("identity_pin", "native_symbol is not declared by the artifact, its lineage, or its path")


def _resolve_month(
    descriptor: Mapping[str, Any],
    lineage: Mapping[str, Any] | None,
    relative_under_product: str,
    writer_month: str | None,
) -> str:
    declared = _declared_text(descriptor, "utc_month")
    if declared is not None:
        return declared
    if lineage is not None:
        declared = _declared_text(lineage, "utc_month")
        if declared is not None:
            return declared
    _symbol, month, _global_artifact = _path_identity(relative_under_product)
    if month is not None:
        return month
    if writer_month is not None:
        return writer_month
    return ABSENT_MONTH


def _mapping_count(document: Mapping[str, Any]) -> int:
    signals: list[int] = []
    for key in ("mappings", "upstream", "raw_objects"):
        value = document.get(key)
        if type(value) is list:
            if key == "raw_objects" and any(type(item) is not dict for item in value):
                _fail("malformed_metadata", "raw_objects entries must be objects")
            signals.append(len(value))
    for key in ("mapping_count", "evidence_records"):
        value = document.get(key)
        if type(value) is int and not isinstance(value, bool):
            if value < 0:
                _fail("row_mismatch", f"{key} is negative", key=key)
            signals.append(value)
    if not signals:
        return 0
    if len(set(signals)) != 1:
        _fail("identity_pin", "lineage count signals disagree", signals=signals)
    return signals[0]


def _validate_lineage(
    document: Mapping[str, Any],
    *,
    owner: str,
    subject: str,
    component: str,
    symbol: str,
    month: str,
    digest: str,
    rows: int,
    schema_sha: str,
) -> None:
    if "required_product" in document and document.get("required_product") not in {owner, subject}:
        _fail("identity_pin", "lineage required_product does not match the artifact", owner=owner, subject=subject)
    lineage_component = {
        "source_gap": "source-gaps",
        "typed_gap_membership": "typed-gaps",
        "quality_gap": "quality-gaps",
    }.get(component, component) if owner == PRODUCT_COVERAGE else component
    if "component" in document and document.get("component") != lineage_component:
        _fail("identity_pin", "lineage component does not match the artifact", component=component)
    if "gap_kind" in document and document.get("gap_kind") != component:
        _fail("identity_pin", "lineage gap kind does not match the artifact", component=component)
    if "native_symbol" in document and document.get("native_symbol") != symbol:
        _fail("identity_pin", "lineage native_symbol does not match the artifact", native_symbol=symbol)
    if "utc_month" in document and document.get("utc_month") != month:
        _fail("identity_pin", "lineage utc_month does not match the artifact", utc_month=month)
    if "parquet_sha256" in document and document.get("parquet_sha256") != digest:
        _fail("reference_mismatch", "lineage parquet digest does not match the artifact")
    if "row_count" in document and _whole(document.get("row_count"), "lineage rows") != rows:
        _fail("row_mismatch", "lineage row count does not match the artifact")
    if "schema_sha256" in document and document.get("schema_sha256") != schema_sha:
        _fail("schema_mismatch", "lineage schema digest does not match the artifact")


def _under_product(spec: ProductSpec, repo_relative: str) -> str:
    prefix = spec.root + "/"
    if not repo_relative.startswith(prefix):
        _fail("unsafe_path", "artifact escaped its product root", path=repo_relative)
    return repo_relative[len(prefix) :]


def _lineage(root: Path, spec: ProductSpec, descriptor: Mapping[str, Any]) -> tuple[_File, str, dict[str, Any]]:
    relative, digest, size = _resolve(root, spec, str(descriptor.get("lineage_path") or ""))
    expected = _hex64(descriptor.get("lineage_sha256"), "lineage")
    if digest != expected:
        _fail("reference_mismatch", "lineage digest mismatch", path=relative)
    if "lineage_bytes" in descriptor and _whole(descriptor.get("lineage_bytes"), "lineage bytes") != size:
        _fail("reference_mismatch", "lineage byte count mismatch", path=relative)
    document, _digest, _size = _load_json(root, relative, MAX_JSON_BYTES, digest)
    under = _under_product(spec, relative)
    symbol = _resolve_symbol(descriptor, document, under)
    month = _resolve_month(descriptor, document, under, None)
    recorded = _File(
        relative,
        digest,
        size,
        0,
        False,
        (),
        {
            "component": str(descriptor.get("component") or descriptor.get("kind") or ""),
            "native_symbol": symbol,
            "utc_month": month,
            "role": "lineage",
        },
    )
    return recorded, digest, document


def _table_file(
    root: Path,
    spec: ProductSpec,
    descriptor: Mapping[str, Any],
    *,
    component: str,
    writer_month: str | None,
    schema_sha: str,
    expected_schema: pa.Schema | None,
    subject: str | None = None,
) -> _Paired:
    relative, digest, size = _resolve(root, spec, str(descriptor.get("parquet_path") or ""))
    if digest != _hex64(descriptor.get("parquet_sha256"), "partition"):
        _fail("reference_mismatch", "partition digest mismatch", path=relative)
    rows = _whole(descriptor.get("row_count"), "partition rows")
    if "parquet_bytes" in descriptor and _whole(descriptor.get("parquet_bytes"), "partition bytes") != size:
        _fail("reference_mismatch", "partition byte count mismatch", path=relative)
    fields = _footer(root, relative, rows)
    if expected_schema is not None:
        _require_equal_contract(fields, expected_schema, relative)
    lineage_sha = None
    lineage_count = 0
    lineage_file: _File | None = None
    lineage_document: dict[str, Any] | None = None
    if descriptor.get("lineage_path"):
        lineage_file, lineage_sha, lineage_document = _lineage(root, spec, descriptor)
        lineage_count = _mapping_count(lineage_document)
    under = _under_product(spec, relative)
    symbol = _resolve_symbol(descriptor, lineage_document, under)
    month = _resolve_month(descriptor, lineage_document, under, writer_month)
    if lineage_document is not None:
        _validate_lineage(
            lineage_document,
            owner=spec.dataset_type,
            subject=subject or spec.dataset_type,
            component=component,
            symbol=symbol,
            month=month,
            digest=digest,
            rows=rows,
            schema_sha=schema_sha,
        )
    recorded = _File(
        relative,
        digest,
        size,
        rows,
        True,
        fields,
        {"component": component, "native_symbol": symbol, "utc_month": month, "role": "partition"},
    )
    source = _BundleSource(
        owner=spec.dataset_type,
        required_product=subject or spec.dataset_type,
        component=component,
        native_symbol=symbol,
        utc_month=month,
        partition_sha256=digest,
        partition_bytes=size,
        row_count=rows,
        schema_sha256=schema_sha,
        lineage_sha256=lineage_sha,
        lineage_mapping_count=lineage_count,
    )
    source_files = (recorded, lineage_file) if lineage_file is not None else (recorded,)
    return _Paired(source_files, source)


class _Paired:
    def __init__(self, files: tuple[_File, ...], source: _BundleSource) -> None:
        self.files = files
        self.source = source


def _append_pair(
    files: list[_File],
    sources: list[_BundleSource],
    root: Path,
    spec: ProductSpec,
    descriptor: Mapping[str, Any],
    *,
    component: str,
    writer_month: str | None,
    schema_sha: str,
    expected_schema: pa.Schema | None,
    subject: str | None = None,
) -> None:
    paired = _table_file(
        root,
        spec,
        descriptor,
        component=component,
        writer_month=writer_month,
        schema_sha=schema_sha,
        expected_schema=expected_schema,
        subject=subject,
    )
    assert isinstance(paired, _Paired)
    files.extend(paired.files)
    sources.append(paired.source)


def _metadata_file(root: Path, spec: ProductSpec, relative_under_root: str, role: str) -> _File:
    repo_relative = _safe(f"{spec.root}/{relative_under_root}", "metadata path")
    digest, size = _hash_reference(root, repo_relative, None)
    return _File(repo_relative, digest, size, 0, False, (), {"role": role})


def _completion_file(root: Path, spec: ProductSpec, production: bool) -> tuple[dict[str, Any], str, _File]:
    directory = lexical_join(root, _safe(f"{spec.root}/.complete", "completion directory"))
    if not directory.is_dir() or directory.is_symlink():
        _fail("reference_mismatch", "completion directory is absent", path=spec.root)
    names = sorted(name for name in os.listdir(directory) if (directory / name).is_file())
    if len(names) != 1 or not names[0].endswith(".json"):
        _fail("mixed_authority", "a product must have one completion marker", path=spec.root)
    relative = f"{spec.root}/.complete/{names[0]}"
    document, digest, size = _load_json(root, relative, MAX_JSON_BYTES)
    if names[0] != f"{digest}.json":
        _fail("identity_pin", "completion filename is not its digest", path=relative)
    pinned = COMPLETION_SHA256.get(spec.dataset_type, spec.completion_sha256)
    if pinned != spec.completion_sha256:
        _fail("identity_pin", "product completion pin drifted from coverage", product=spec.dataset_type)
    if production and digest != spec.completion_sha256:
        _fail("identity_pin", "completion digest is not the accepted pin", path=relative, product=spec.dataset_type)
    if spec.family != "coverage":
        expected_type = f"{spec.dataset_type}_product_completion"
        if document.get("document_type") != expected_type or document.get("required_product") != spec.dataset_type:
            _fail("identity_pin", "completion document type mismatch", path=relative)
    recorded = _File(relative, digest, size, 0, False, (), {"role": "completion"})
    return document, digest, recorded


def _pin_if_present(document: Mapping[str, Any], key: str, expected: Any) -> None:
    if key in document and document.get(key) != expected:
        _fail("identity_pin", "authenticated document contradicts a release pin", key=key)


def _require_pin(document: Mapping[str, Any], key: str, expected: Any) -> None:
    if document.get(key) != expected:
        _fail("identity_pin", "release pin is absent or changed", key=key)


def _ordinary_schema(
    root: Path,
    spec: ProductSpec,
    completion: Mapping[str, Any],
    partitions: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any],
) -> tuple[str, tuple[str, str, bool]]:
    first = partitions[0]
    relative, _digest, _size = _resolve(root, spec, str(first.get("parquet_path")))
    fields = _footer(root, relative, _whole(first.get("row_count"), "partition rows"))
    contract = _contract(fields)
    fingerprint = _schema_sha_pretty({"required_product": spec.dataset_type, "schema": contract})
    if completion.get("schema_sha256") != fingerprint:
        _fail("schema_mismatch", "completion schema hash is not the footer contract", product=spec.dataset_type)
    recorded = receipt.get("projections", {}).get("final_product_schemas", {}).get(spec.dataset_type)
    if type(recorded) is list and _normalize_contract(recorded) != _normalize_contract(contract):
        _fail("schema_mismatch", "receipt schema is not the footer contract", product=spec.dataset_type)
    for part in partitions[1:]:
        other_relative, _d, _s = _resolve(root, spec, str(part.get("parquet_path")))
        other = _footer(root, other_relative, _whole(part.get("row_count"), "partition rows"))
        if other != fields:
            _fail("schema_mismatch", "partitions of one product disagree", product=spec.dataset_type)
    return fingerprint, fields


def _reconcile_ordinary(
    spec: ProductSpec,
    completion: Mapping[str, Any],
    partitions: Sequence[Mapping[str, Any]],
    quality_rows: int,
) -> None:
    """Reconcile declared completion totals. Absent equations are not invented."""

    product_rows = sum(_whole(part.get("row_count"), "partition rows") for part in partitions)
    equation = completion.get("row_equation")
    totals = completion.get("totals")
    if spec.dataset_type == "binance_usdm_open_interest_5m" and type(totals) is dict:
        physical = _whole(totals.get("physical_source_rows"), "physical source rows")
        declared = _whole(totals.get("product_rows"), "product rows")
        excluded = _whole(totals.get("excluded_source_rows"), "excluded source rows")
        collapsed = _whole(totals.get("collapsed_identical_source_rows"), "collapsed source rows")
        gaps = _whole(totals.get("quality_gap_rows"), "quality gap rows")
        if physical != declared + excluded + collapsed or declared != product_rows or gaps != quality_rows:
            _fail("row_mismatch", "open-interest totals do not reconcile", product=spec.dataset_type)
        return
    if type(equation) is not dict:
        return
    if spec.family == "membership":
        classifications = _whole(equation.get("classifications"), "classifications")
        accepted = _whole(equation.get("accepted_membership_rows"), "accepted membership rows")
        excluded = _whole(equation.get("excluded_classifications"), "excluded classifications")
        if classifications != accepted + excluded or accepted != product_rows:
            _fail("row_mismatch", "membership row equation failed", product=spec.dataset_type)
        if "membership_rows" in completion and _whole(completion.get("membership_rows"), "membership rows") != accepted:
            _fail("row_mismatch", "membership rows differ from the accepted side of the equation")
        return
    if spec.family == "liquidation":
        physical = _whole(equation.get("physical_source_rows"), "physical source rows")
        collapsed = _whole(equation.get("collapsed_identical_rows"), "collapsed rows")
        declared = _whole(equation.get("product_rows"), "product rows")
        missing = _whole(equation.get("missing_daily_slots"), "missing slots")
        requested = _whole(equation.get("inclusive_requested_slots"), "requested slots")
        if physical - collapsed != declared or declared + missing != requested or declared != product_rows:
            _fail("row_mismatch", "liquidation row equation failed", product=spec.dataset_type)
        return
    if spec.family == "partition" and spec.dataset_type == "binance_usdm_funding_realized":
        physical = _whole(equation.get("physical_source_rows"), "physical source rows")
        excluded = _whole(equation.get("excluded_source_rows"), "excluded source rows")
        collapsed = _whole(equation.get("collapsed_identical_rows"), "collapsed rows")
        declared = _whole(equation.get("product_rows"), "product rows")
        if physical != declared + excluded + collapsed or declared != product_rows:
            _fail("row_mismatch", "funding row equation failed", product=spec.dataset_type)
        if _whole(equation.get("inferred_events"), "inferred events") or _whole(equation.get("conflicting_events"), "conflicting events"):
            _fail("row_mismatch", "funding observed-event semantics changed")
        return
    if spec.family == "partition" and spec.dataset_type in {
        "binance_usdm_funding_indicative_1h", "binance_usdm_mark_index_basis_1h"
    }:
        physical = _whole(equation.get("physical_source_rows"), "physical source rows")
        joined = _whole(equation.get("joined_input_rows"), "joined input rows")
        unjoinable = _whole(equation.get("unjoinable_source_rows"), "unjoinable source rows")
        excluded = _whole(equation.get("excluded_source_rows"), "excluded source rows")
        collapsed = _whole(equation.get("collapsed_identical_rows"), "collapsed rows")
        declared = _whole(equation.get("product_rows"), "product rows")
        legs = 3 if spec.dataset_type == "binance_usdm_mark_index_basis_1h" else 1
        if physical != joined + unjoinable + excluded + collapsed or joined != legs * declared or declared != product_rows:
            _fail("row_mismatch", "price-state row equation failed", product=spec.dataset_type)
        if _whole(equation.get("fabricated_rows"), "fabricated rows"):
            _fail("row_mismatch", "price-state fabricated rows changed")
        return
    if spec.family == "partition":
        physical = _whole(equation.get("physical_rows"), "physical rows")
        excluded = _whole(equation.get("excluded_rows"), "excluded rows")
        declared = _whole(equation.get("product_rows"), "product rows")
        if physical != declared + excluded or declared != product_rows:
            _fail("row_mismatch", "kline row equation failed", product=spec.dataset_type)


def _account_ordinary(
    root: Path,
    spec: ProductSpec,
    completion: Mapping[str, Any],
    completion_file: _File,
    receipt: Mapping[str, Any],
    production: bool,
) -> _ProductAccount:
    partitions = completion.get("partitions")
    if type(partitions) is not list or not partitions:
        _fail("empty_required", "a required product has no partitions", product=spec.dataset_type)
    typed_parts = [part for part in partitions if type(part) is dict]
    if len(typed_parts) != len(partitions):
        _fail("malformed_metadata", "partition descriptor is malformed", product=spec.dataset_type)
    fingerprint, _fields = _ordinary_schema(root, spec, completion, typed_parts, receipt)
    files = [completion_file]
    sources: list[_BundleSource] = []
    for part in typed_parts:
        _append_pair(
            files,
            sources,
            root,
            spec,
            part,
            component=str(part.get("component") or ""),
            writer_month=None,
            schema_sha=fingerprint,
            expected_schema=None,
        )
    quality_rows = 0
    artifacts: list[Mapping[str, Any]] = []
    single = completion.get("quality_gap_artifact")
    if type(single) is dict:
        artifacts.append(single)
    many = completion.get("quality_gap_artifacts")
    if type(many) is list:
        artifacts.extend(item for item in many if type(item) is dict)
    if spec.family == "liquidation":
        gaps = completion.get("gaps")
        if type(gaps) is not list:
            _fail("malformed_metadata", "liquidation gap descriptors are absent")
        for gap in gaps:
            if type(gap) is not dict:
                _fail("malformed_metadata", "liquidation gap descriptor is malformed")
            if "parquet_path" not in gap:
                _fail("empty_required", "a liquidation gap has no parquet artifact", kind=str(gap.get("kind")))
            artifacts.append(gap)
    for artifact in artifacts:
        before = len(sources)
        component_name = str(artifact.get("kind") or artifact.get("component") or "quality_gap")
        expected_schema = QUALITY_GAP_SCHEMA if spec.family == "partition" else None
        _append_pair(
            files,
            sources,
            root,
            spec,
            artifact,
            component=component_name,
            writer_month=None,
            schema_sha=_schema_sha_compact(_contract(_footer(
                root,
                _resolve(root, spec, str(artifact.get("parquet_path")))[0],
                _whole(artifact.get("row_count"), "quality rows"),
            ))),
            expected_schema=expected_schema,
        )
        quality_rows += sources[-1].row_count
        if len(sources) == before:
            _fail("empty_required", "quality artifact produced no row")
    authority = completion.get("authority_gap_lineage")
    if type(authority) is dict and authority.get("lineage_path"):
        lineage, _sha, _document = _lineage(root, spec, authority)
        files.append(lineage)
    elif type(authority) is list:
        for item in authority:
            if type(item) is dict and item.get("lineage_path"):
                lineage, _sha, _document = _lineage(root, spec, item)
                files.append(lineage)
    _reconcile_ordinary(spec, completion, typed_parts, quality_rows)
    if production and spec.dataset_type in QUALITY_ROWS_BY_PRODUCT:
        if quality_rows != QUALITY_ROWS_BY_PRODUCT[spec.dataset_type]:
            _fail("row_mismatch", "quality-gap rows are not the accepted pin", product=spec.dataset_type)
    if production and spec.family == "membership":
        _require_pin(completion, "membership_rows", MEMBERSHIP_ACCEPTED_PIN)
        _require_pin(completion, "excluded_classifications", MEMBERSHIP_EXCLUDED_PIN)
        _require_pin(completion, "funding_only_rows", MEMBERSHIP_FUNDING_ONLY_PIN)
    quality = {
        "completion_sha256": completion_file.sha256,
        "quality_gap_rows": quality_rows,
        "partition_count": len(typed_parts),
        "utc_month_absent_token": ABSENT_MONTH,
        "native_symbol_absent_token": ABSENT_MONTH,
    }
    return _ProductAccount(spec, completion_file.sha256, tuple(files), tuple(sources), fingerprint, quality)


def _account_cost(
    root: Path,
    spec: ProductSpec,
    completion: Mapping[str, Any],
    completion_file: _File,
    receipt: Mapping[str, Any],
    production: bool,
) -> _ProductAccount:
    partitions = completion.get("partitions")
    if type(partitions) is not list or not partitions:
        _fail("empty_required", "cost calibration has no partitions")
    by_component: dict[str, list[dict[str, Any]]] = {name: [] for name in COST_COMPONENTS}
    for part in partitions:
        if type(part) is not dict:
            _fail("malformed_metadata", "cost partition is malformed")
        component = part.get("component")
        if component not in by_component:
            _fail("mixed_authority", "cost partition component is unknown", component=str(component))
        by_component[str(component)].append(part)
    if any(not rows for rows in by_component.values()):
        _fail("empty_required", "a cost component has no partition")
    component_schemas = completion.get("component_schemas")
    if type(component_schemas) is not dict:
        _fail("schema_mismatch", "cost component schemas are absent")
    files = [completion_file]
    sources: list[_BundleSource] = []
    contracts: dict[str, list[dict[str, Any]]] = {}
    footer_rows: dict[str, int] = {}
    for component, rows in by_component.items():
        total = 0
        component_contract: list[dict[str, Any]] | None = None
        for part in rows:
            relative = _resolve(root, spec, str(part.get("parquet_path")))[0]
            fields = _footer(root, relative, _whole(part.get("row_count"), component))
            contract = _contract(fields)
            if component_contract is None:
                component_contract = contract
            elif contract != component_contract:
                _fail("schema_mismatch", "cost component schemas disagree", component=component)
            total += _whole(part.get("row_count"), component)
        assert component_contract is not None
        contracts[component] = component_contract
        identity = _schema_sha_pretty(
            {"required_product": PRODUCT_COST, "component": component, "schema": component_contract}
        )
        if component_schemas.get(component) != identity:
            _fail("schema_mismatch", "cost component schema hash mismatch", component=component)
        receipt_schemas = receipt.get("typed_schema_contract", {}).get("cost_component_schemas", {})
        if type(receipt_schemas) is dict and type(receipt_schemas.get(component)) is list:
            if _normalize_contract(receipt_schemas[component]) != _normalize_contract(component_contract):
                _fail("schema_mismatch", "receipt cost schema mismatch", component=component)
        for part in rows:
            _append_pair(
                files,
                sources,
                root,
                spec,
                part,
                component=component,
                writer_month=None,
                schema_sha=identity,
                expected_schema=None,
            )
        footer_rows[component] = total
    fingerprint = _schema_sha_pretty({"required_product": PRODUCT_COST, "schema": contracts})
    if completion.get("schema_sha256") != fingerprint:
        _fail("schema_mismatch", "cost product schema hash mismatch")
    disposition = completion.get("ticker_row_projection_disposition")
    if type(disposition) is not dict:
        _fail("row_mismatch", "ticker projection disposition is absent")
    projected = _whole(disposition.get("projected_rows"), "ticker projected rows")
    actual = _whole(disposition.get("actual_rows"), "ticker actual rows")
    excess = _whole(disposition.get("excess_rows"), "ticker excess rows")
    if excess != actual - projected or disposition.get("ordinary_sizing_check_passed") is not False:
        _fail("row_mismatch", "ticker excess is not the reviewed exact variance")
    if disposition.get("status") != TICKER_STATUS:
        _fail("identity_pin", "ticker excess status is not the reviewed marker")
    if footer_rows["retained_book_ticker"] != actual:
        _fail("row_mismatch", "ticker footer rows differ from the disposition")
    if production and (projected, actual, excess) != (TICKER_PROJECTED_ROWS, TICKER_ACTUAL_ROWS, TICKER_EXCESS_ROWS):
        _fail("identity_pin", "ticker disposition is not the accepted excess")
    scope = completion.get("encoded_validation_scope")
    if type(scope) is dict and scope.get("independent_complete_csv_to_parquet_value_equality_claimed") is not False:
        _fail("identity_pin", "cost validation scope claims unchecked CSV equality")
    fee = completion.get("fee_authority")
    if type(fee) is not dict or fee.get("missing_fee_is_zero") is not False:
        _fail("identity_pin", "missing historical fees are not zero")
    scenario = completion.get("scenario_policy")
    if type(scenario) is not dict or scenario.get("historical_observation") is not False:
        _fail("identity_pin", "fee scenarios are not historical observations")
    frozen = completion.get("frozen_source_gaps")
    if type(frozen) is not dict:
        _fail("reference_mismatch", "frozen cost source gaps are absent")
    frozen_relative, frozen_sha, frozen_size = _resolve(root, spec, str(frozen.get("path")))
    if frozen_sha != _hex64(frozen.get("sha256"), "frozen source gaps") or frozen_size != _whole(frozen.get("bytes"), "frozen bytes"):
        _fail("reference_mismatch", "frozen source-gap artifact mismatch")
    if _whole(frozen.get("row_count"), "frozen rows") != COST_SOURCE_GAP_ROWS and production:
        _fail("identity_pin", "frozen source-gap rows are not the accepted pin")
    if production and (frozen_sha, frozen_size) != (COST_SOURCE_GAP_SHA256, COST_SOURCE_GAP_BYTES):
        _fail("identity_pin", "frozen source-gap identity is not the accepted pin")
    files.append(
        _File(frozen_relative, frozen_sha, frozen_size, 0, False, (), {"role": "frozen_source_gaps"})
    )
    quality = {
        "completion_sha256": completion_file.sha256,
        "ticker_row_projection_disposition": {
            "projected_rows": projected,
            "actual_rows": actual,
            "excess_rows": excess,
            "status": TICKER_STATUS,
            "ordinary_sizing_check_passed": False,
        },
        "frozen_source_gaps": {
            "path": frozen_relative,
            "sha256": frozen_sha,
            "bytes": frozen_size,
            "row_count": _whole(frozen.get("row_count"), "frozen rows"),
            "copied": False,
        },
        "fee_authority_gap_reference": {"rows": FEE_AUTHORITY_GAP_ROWS, "copied": False},
        "missing_fee_is_zero": False,
        "scenario_historical_observation": False,
    }
    return _ProductAccount(spec, completion_file.sha256, tuple(files), tuple(sources), fingerprint, quality)


def _coverage_schema_sha(component: str, fields: Sequence[tuple[str, str, bool]]) -> str:
    frozen = {
        "source_gap": SOURCE_GAP_SCHEMA,
        "typed_gap_membership": TYPED_GAP_SCHEMA,
        "quality_gap": QUALITY_GAP_SCHEMA,
    }[component]
    _require_equal_contract(fields, frozen, f"coverage {component}")
    contract = _contract(tuple((field.name, str(field.type), bool(field.nullable)) for field in frozen))
    if component == "source_gap":
        return _schema_sha_pretty({"required_product": PRODUCT_COVERAGE, "schema": contract})
    return _schema_sha_compact(contract)


def _account_coverage(
    root: Path,
    spec: ProductSpec,
    completion: Mapping[str, Any],
    completion_file: _File,
    production: bool,
) -> _ProductAccount:
    if completion.get("document_type") != "binance_usdm_coverage_gap_product_completion":
        _fail("identity_pin", "coverage completion document type mismatch")
    if completion.get("required_product") != PRODUCT_COVERAGE:
        _fail("identity_pin", "coverage required product mismatch")
    manifests = completion.get("manifests")
    if type(manifests) is not dict or set(manifests) != set(COVERAGE_PAGES):
        _fail("partial_release", "coverage completion does not name the six manifest pages")
    publication = completion.get("publication")
    if type(publication) is dict and publication.get("visible_harmonic_bundle") is not False:
        _fail("identity_pin", "coverage publication must not claim a visible harmonic bundle")
    alignment = completion.get("alignment")
    if type(alignment) is not dict:
        _fail("identity_pin", "coverage alignment is absent")
    _require_pin(alignment, "five_product_observed_day_count", OBSERVED_DAY_COUNT)
    _require_pin(alignment, "five_product_observed_day_sha256", OBSERVED_DAY_SHA256)
    _require_pin(alignment, "full_cadence_day_count", FULL_CADENCE_DAY_COUNT)
    _require_pin(alignment, "full_cadence_day_sha256", FULL_CADENCE_DAY_SHA256)
    _require_pin(alignment, "aligned_day_rows", ALIGNED_DAY_ROWS)
    if alignment.get("funding_expected_count") is not None or alignment.get("liquidation_complete") is not False:
        _fail("identity_pin", "funding expectation or liquidation completeness was fabricated")
    ledger = completion.get("metadata_ledger")
    if type(ledger) is dict:
        _pin_if_present(ledger, "release_wide_allocation_bytes", RELEASE_METADATA_BYTES)
        _pin_if_present(ledger, "reserved_debit_bytes", METADATA_BUDGET_BYTES)
        _pin_if_present(ledger, "reserved_release_remainder_bytes", RELEASE_METADATA_REMAINDER_BYTES)
        _pin_if_present(ledger, "unused_coverage_reservation_reallocatable", False)
        _pin_if_present(ledger, "measured_coverage_reservation_remaining_bytes", UNUSED_COVERAGE_RESERVATION_BYTES)
        if production:
            _require_pin(ledger, "release_wide_allocation_bytes", RELEASE_METADATA_BYTES)
            _require_pin(ledger, "reserved_release_remainder_bytes", RELEASE_METADATA_REMAINDER_BYTES)
            _require_pin(ledger, "unused_coverage_reservation_reallocatable", False)
    files = [completion_file]
    sources: list[_BundleSource] = []
    components = completion.get("components")
    if type(components) is not dict:
        _fail("malformed_metadata", "coverage components are absent")
    schemas = {
        "source_gap": SOURCE_GAP_SCHEMA,
        "typed_gap_membership": TYPED_GAP_SCHEMA,
        "quality_gap": QUALITY_GAP_SCHEMA,
    }
    observed_rows = {"source_gap": 0, "typed_gap_membership": 0, "quality_gap": 0}
    for name in COVERAGE_PAGES:
        page = manifests.get(name)
        if type(page) is not dict:
            _fail("malformed_metadata", "coverage manifest page is malformed", page=name)
        page_path = str(page.get("path") or "")
        document, digest, size = _load_json(root, _safe(f"{spec.root}/{_safe(page_path, name)}", name), METADATA_BUDGET_BYTES)
        if digest != _hex64(page.get("sha256"), name) or size != _whole(page.get("bytes"), name):
            _fail("reference_mismatch", "coverage manifest page mismatch", page=name)
        if document.get("document_type") != f"binance_usdm_coverage_{name}_manifest":
            _fail("identity_pin", "coverage manifest document type mismatch", page=name)
        rows = document.get("rows")
        if type(rows) is not list or document.get("row_count") != len(rows):
            _fail("row_mismatch", "coverage manifest row count mismatch", page=name)
        files.append(_File(f"{spec.root}/{_safe(page_path, name)}", digest, size, 0, False, (), {"role": "coverage_manifest", "page": name}))
        if name == "excluded_membership":
            continue
        if name in {"daily", "summary"}:
            if not rows:
                _fail("empty_required", "coverage reporting page is empty", page=name)
            for row in rows:
                if type(row) is not dict:
                    _fail("malformed_metadata", "coverage report row is malformed", page=name)
                symbol = _component(row.get("native_symbol"), "coverage symbol")
                digest_name = _hex64(row.get("sha256"), page)
                if name == "daily":
                    month = _component(row.get("utc_month"), "coverage month")
                    under = f".daily/{symbol}/{month}/{digest_name}.json"
                else:
                    under = f".summary/{symbol}/{digest_name}.json"
                meta = _metadata_file(root, spec, under, name)
                if meta.sha256 != digest_name or meta.byte_size != _whole(row.get("bytes"), name):
                    _fail("reference_mismatch", "coverage report artifact mismatch", path=under)
                files.append(meta)
            continue
        if not rows:
            _fail("empty_required", "coverage gap page is empty", page=name)
        gap_name = {"source_gap": "source_gap", "typed_gap": "typed_gap_membership", "quality_gap": "quality_gap"}[name]
        folder = {"source_gap": "source-gaps", "typed_gap": "typed-gaps", "quality_gap": "quality-gaps"}[name]
        for row in rows:
            if type(row) is not dict:
                _fail("malformed_metadata", "coverage gap row is malformed", page=name)
            product = _component(row.get("required_product"), "gap product")
            symbol = _component(row.get("native_symbol"), "gap symbol")
            parquet_sha = _hex64(row.get("parquet_sha256"), "gap parquet")
            lineage_sha = _hex64(row.get("lineage_sha256"), "gap lineage")
            month = AUTHORITY_MONTH if name in {"source_gap", "typed_gap"} else _component(row.get("utc_month"), "gap month")
            descriptor = {
                "native_symbol": symbol,
                "utc_month": month,
                "row_count": row.get("row_count"),
                "parquet_path": f".{folder}/{product}/{symbol}/{month}/{parquet_sha}.parquet",
                "parquet_sha256": parquet_sha,
                "parquet_bytes": row.get("parquet_bytes"),
                "lineage_path": f".{folder}-lineage/{product}/{symbol}/{month}/{lineage_sha}.json",
                "lineage_sha256": lineage_sha,
                "lineage_bytes": row.get("lineage_bytes"),
                "component": gap_name,
            }
            before = len(sources)
            declared_fields = tuple(
                (field.name, str(field.type), bool(field.nullable)) for field in schemas[gap_name]
            )
            _append_pair(
                files,
                sources,
                root,
                spec,
                descriptor,
                component=gap_name,
                writer_month=month,
                schema_sha=_coverage_schema_sha(gap_name, declared_fields),
                expected_schema=schemas[gap_name],
                subject=product,
            )
            observed_rows[gap_name] += sources[-1].row_count
            if len(sources) == before:
                _fail("empty_required", "coverage gap row was not reconstructed")
    source_component = components.get("source_gap")
    typed_component = components.get("typed_gap_membership")
    quality_component = components.get("quality_gap")
    fee_component = components.get("fee_authority_gap_reference")
    cost_component = components.get("cost_normalization_source_gap_reference")
    for label, component, observed in (
        ("source_gap", source_component, observed_rows["source_gap"]),
        ("typed_gap_membership", typed_component, observed_rows["typed_gap_membership"]),
        ("quality_gap", quality_component, observed_rows["quality_gap"]),
    ):
        if type(component) is not dict or _whole(component.get("rows"), label) != observed:
            _fail("row_mismatch", "coverage component rows differ from the reconstructed files", component=label)
    if type(fee_component) is not dict or fee_component.get("copied") is not False:
        _fail("identity_pin", "fee authority reference must stay uncopied")
    if _whole(fee_component.get("rows"), "fee authority rows") != FEE_AUTHORITY_GAP_ROWS:
        _fail("identity_pin", "fee authority gap rows are not the accepted pin")
    if type(cost_component) is not dict or cost_component.get("copied") is not False:
        _fail("identity_pin", "cost source-gap reference must stay uncopied")
    if production:
        _require_pin(source_component, "rows", SOURCE_GAP_ROW_PIN)
        _require_pin(typed_component, "rows", TYPED_GAP_ROW_PIN)
        _require_pin(quality_component, "rows", QUALITY_GAP_ROW_PIN)
        _require_pin(source_component, "schema_sha256", _coverage_schema_sha("source_gap", next(item.schema_fields for item in files if item.is_table and item.partition.get("component") == "source_gap")))
    fingerprint = _coverage_schema_sha(
        "source_gap",
        next(item.schema_fields for item in files if item.is_table and item.partition.get("component") == "source_gap"),
    )
    if source_component.get("schema_sha256") != fingerprint:
        _fail("schema_mismatch", "coverage source-gap schema hash mismatch")
    quality = {
        "completion_sha256": completion_file.sha256,
        "coverage_gap_rows": observed_rows["source_gap"],
        "typed_gap_membership_rows": observed_rows["typed_gap_membership"],
        "quality_gap_rows": observed_rows["quality_gap"],
        "fee_authority_gap_rows": FEE_AUTHORITY_GAP_ROWS,
        "fee_authority_gap_reference": {"rows": FEE_AUTHORITY_GAP_ROWS, "copied": False},
        "cost_normalization_source_gap_reference": {
            "rows": _whole(cost_component.get("rows"), "cost reference rows"),
            "sha256": _hex64(cost_component.get("sha256"), "cost reference"),
            "bytes": _whole(cost_component.get("bytes"), "cost reference bytes"),
            "copied": False,
        },
        "intersections": {
            "bundle_column_intersection": "five_product_observed_days",
            "five_product_observed_day_count": OBSERVED_DAY_COUNT,
            "five_product_observed_day_sha256": OBSERVED_DAY_SHA256,
            "full_cadence_day_count": FULL_CADENCE_DAY_COUNT,
            "full_cadence_day_sha256": FULL_CADENCE_DAY_SHA256,
            "aligned_day_rows": ALIGNED_DAY_ROWS,
        },
        "funding_expected_count": None,
        "liquidation_complete": False,
        "utc_month_absent_token": ABSENT_MONTH,
        "native_symbol_absent_token": ABSENT_MONTH,
        "visible_harmonic_bundle": False,
    }
    return _ProductAccount(spec, completion_file.sha256, tuple(files), tuple(sources), fingerprint, quality)


def _account_product(root: Path, spec: ProductSpec, receipt: Mapping[str, Any], production: bool) -> _ProductAccount:
    completion, _digest, completion_file = _completion_file(root, spec, production)
    if spec.family == "coverage":
        account = _account_coverage(root, spec, completion, completion_file, production)
    elif spec.family == "cost":
        account = _account_cost(root, spec, completion, completion_file, receipt, production)
    else:
        account = _account_ordinary(root, spec, completion, completion_file, receipt, production)
    disk = _walk(root, spec)
    declared = set()
    for item in account.files:
        prefix = spec.root + "/"
        if not item.relative_path.startswith(prefix):
            _fail("unsafe_path", "accounted file escaped its product root", path=item.relative_path)
        declared.add(item.relative_path[len(prefix):])
    missing = declared - disk
    if missing:
        _fail(
            "reference_mismatch",
            "accepted descriptor file is absent from the product tree",
            product=spec.dataset_type,
            path=f"{spec.root}/{min(missing)}",
        )
    extras = disk - declared
    if spec.dataset_type in _RETAINED_KLINE_COUNTS:
        audit = _retained_kline_inventory(root, spec, extras, production=production)
        return replace(account, retained_audit=audit)
    if extras:
        _fail(
            "reference_mismatch", "product tree has an unexpected file",
            product=spec.dataset_type, path=f"{spec.root}/{min(extras)}",
        )
    return account


def _authenticate_reconciliation(root: Path, accounts: Mapping[str, _ProductAccount], qualification_sha: str, production: bool) -> dict[str, str]:
    completion_relative = f"{RECON_ROOT}/.complete/{RECON_COMPLETION_SHA256}.json" if production else None
    if completion_relative is None:
        directory = lexical_join(root, _safe(f"{RECON_ROOT}/.complete", "reconciliation completion"))
        names = sorted(name for name in os.listdir(directory) if (directory / name).is_file() and not (directory / name).is_symlink())
        if len(names) != 1:
            _fail("mixed_authority", "reconciliation must have one completion marker")
        completion_relative = f"{RECON_ROOT}/.complete/{names[0]}"
    completion, completion_sha, _size = _load_json(root, completion_relative, MAX_JSON_BYTES)
    if production and completion_sha != RECON_COMPLETION_SHA256:
        _fail("identity_pin", "reconciliation completion is not the accepted pin")
    if completion.get("document_type") != COMPLETION_DOCUMENT or completion.get("status") != "PASS":
        _fail("identity_pin", "reconciliation completion is not a passing marker")
    report_sha = _hex64(completion.get("report_sha256"), "reconciliation report")
    if report_sha == FAILED_REPORT_SHA256:
        _fail("mixed_authority", "the preserved failed reconciliation report was selected")
    report_relative = f"{RECON_ROOT}/.reports/{report_sha}.json"
    report, observed_report_sha, _size = _load_json(root, report_relative, MAX_JSON_BYTES, report_sha)
    if report.get("document_type") != REPORT_DOCUMENT or report.get("status") != "PASS":
        _fail("identity_pin", "selected reconciliation report is not passing")
    coverage = report.get("coverage")
    if type(coverage) is not dict:
        _fail("identity_pin", "reconciliation coverage block is absent")
    _require_pin(coverage, "matched_field_count", RECON_MATCHED_FIELDS)
    _require_pin(coverage, "field_denominator", RECON_FIELD_DENOMINATOR)
    _require_pin(coverage, "successfully_compared_hour_count", RECON_COMPARED_HOURS)
    _require_pin(coverage, "distinct_day_count", RECON_DISTINCT_DAYS)
    _require_pin(coverage, "logical_role_count", RECON_LOGICAL_ROLES)
    _require_pin(coverage, "roles_with_compared_hour", RECON_ROLES_WITH_HOUR)
    for key in ("discrepancies", "coverage_failures", "unexplained_absences"):
        if report.get(key) != []:
            _fail("identity_pin", "reconciliation report is not clean", key=key)
    if completion.get("bar_completion_sha256") != accounts["binance_usdm_bar_1h"].completion_sha256:
        _fail("identity_pin", "reconciliation is not bound to the bar completion")
    if completion.get("flow_completion_sha256") != accounts["binance_usdm_trade_flow_1h"].completion_sha256:
        _fail("identity_pin", "reconciliation is not bound to the trade-flow completion")
    if completion.get("qualification_report_sha256") != qualification_sha:
        _fail("identity_pin", "reconciliation qualification binding changed")
    failed_relative = f"{RECON_ROOT}/.reports/{FAILED_REPORT_SHA256}.json"
    failed_path = lexical_join(root, failed_relative)
    if production or failed_path.exists() or failed_path.is_symlink():
        failed_sha, _size = _hash_reference(root, failed_relative, MAX_JSON_BYTES)
        if failed_sha != FAILED_REPORT_SHA256:
            _fail("identity_pin", "preserved failed reconciliation report hash changed")
        if failed_sha == observed_report_sha:
            _fail("mixed_authority", "failed reconciliation report was selected")
    if production and observed_report_sha != RECON_REPORT_SHA256:
        _fail("identity_pin", "reconciliation report is not the accepted pin")
    return {"completion_sha256": completion_sha, "report_sha256": observed_report_sha}


def _authenticate_authorities(root: Path, production: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    qualification_sha, _size = _hash_reference(root, QUALIFICATION_RELATIVE, MAX_JSON_BYTES)
    _hex64(qualification_sha, "qualification report")
    if production and qualification_sha != REPORT_SHA256:
        _fail("identity_pin", "qualification report is not the accepted pin")
    sizing, sizing_sha, sizing_size = _load_json(root, SIZING_RELATIVE, SIZING_READ_LIMIT)
    if production and sizing_size != SIZING_RECEIPT_BYTES:
        _fail("identity_pin", "sizing receipt byte count is not the accepted file", byte_size=sizing_size)
    if production and sizing_sha != SIZING_SHA256:
        _fail("identity_pin", "sizing receipt is not the accepted pin")
    holdout, holdout_sha, _size = _load_json(root, HOLDOUT_RELATIVE, MAX_JSON_BYTES)
    if holdout.get("boundary_id") != HOLDOUT_ID or holdout.get("boundary_utc") != HOLDOUT_UTC:
        _fail("identity_pin", "holdout boundary identity changed")
    if production and holdout_sha != HOLDOUT_SHA256:
        _fail("identity_pin", "holdout boundary file is not the accepted pin")
    capacity = sizing.get("capacity")
    if type(capacity) is not dict:
        _fail("identity_pin", "sizing capacity block is absent")
    _require_pin(capacity, "operating_reserve_bytes", OPERATING_RESERVE_BYTES)
    _require_pin(capacity, "catalog_manifest_bundle_bytes", RELEASE_METADATA_BYTES)
    projections = sizing.get("projections", {})
    fixed = projections.get("fixed_schema_products", {}).get(PRODUCT_BUNDLE) if type(projections) is dict else None
    if type(fixed) is not dict:
        _fail("identity_pin", "harmonic bundle projection is absent")
    if _whole(fixed.get("projected_bytes"), "measured bundle bytes") != MEASURED_CURRENT_BUNDLE_BYTES:
        _fail(
            "bundle_allocation_pin",
            "measured current bundle bytes are not the receipt projection",
            measured_current_bundle_bytes=MEASURED_CURRENT_BUNDLE_BYTES,
        )
    if _whole(fixed.get("projected_rows"), "projected bundle rows") != SIZING_PROJECTED_BUNDLE_ROWS:
        _fail("identity_pin", "projected bundle rows are not the receipt projection")
    partitioning = sizing.get("partitioning")
    if type(partitioning) is not dict:
        _fail("identity_pin", "sizing partitioning block is absent")
    candidates = partitioning.get("largest_future_width_charge_candidates")
    if type(candidates) is not dict:
        _fail("identity_pin", "future width charge candidates are absent")
    if _whole(candidates.get("harmonic_bundle"), "future bundle charge") != HARMONIC_BUNDLE_ALLOCATION_BYTES:
        _fail("bundle_allocation_pin", "future harmonic bundle charge is not the file cap")
    charge_inputs = partitioning.get("largest_future_width_charge_inputs")
    if charge_inputs is None:
        charge_inputs = candidates.get("largest_future_width_charge_inputs")
    if type(charge_inputs) is not dict:
        _fail("identity_pin", "future width charge inputs are absent")
    if _whole(charge_inputs.get("bundle_rows"), "future bundle rows") != SIZING_PROJECTED_BUNDLE_ROWS:
        _fail("identity_pin", "future charge bundle rows are not the receipt projection")
    if _whole(charge_inputs.get("reference_index_bytes_per_row"), "reference index width") != FUTURE_REFERENCE_INDEX_BYTES_PER_ROW:
        _fail("identity_pin", "reference index width is not 8 bytes")
    if _whole(charge_inputs.get("bundle_reference_dictionary_bytes"), "bundle dictionaries") != FUTURE_BUNDLE_DICTIONARY_BYTES:
        _fail("identity_pin", "bundle reference dictionary bytes changed")
    index_bytes = SIZING_PROJECTED_BUNDLE_ROWS * FUTURE_REFERENCE_INDEX_BYTES_PER_ROW
    if index_bytes + FUTURE_PARTITION_FIELD_BYTES + FUTURE_BUNDLE_DICTIONARY_BYTES != HARMONIC_BUNDLE_ALLOCATION_BYTES:
        _fail("bundle_allocation_pin", "future charge arithmetic drifted")
    if MEASURED_CURRENT_BUNDLE_BYTES + HARMONIC_BUNDLE_ALLOCATION_BYTES != CURRENT_PLUS_FUTURE_PROVISION_BYTES:
        _fail("bundle_allocation_pin", "current plus future provision drifted")
    bundle_schema = sizing.get("typed_schema_contract", {}).get("non_archive_product_schemas", {}).get(PRODUCT_BUNDLE)
    if type(bundle_schema) is not list:
        _fail("schema_mismatch", "receipt bundle schema is absent")
    if _normalize_contract(bundle_schema) != _normalize_contract(_contract(BUNDLE_FIELDS)):
        _fail("bundle_schema_mismatch", "receipt bundle schema is not the frozen column contract")
    code = sizing.get("code_identity")
    if type(code) is not dict:
        _fail("identity_pin", "sizing code identity is absent")
    sizing_code = _hex64(code.get("sizing_source_sha256"), "sizing source")
    sizing_cli = _hex64(code.get("sizing_cli_sha256"), "sizing cli")
    bindings = sizing.get("authority", {}).get("bindings") if type(sizing.get("authority")) is dict else None
    if type(bindings) is dict:
        expected = release_configuration()
        for key, pin in expected.items():
            if key in bindings and bindings.get(key) != pin:
                _fail("identity_pin", "sizing authority binding changed", key=key)
    configuration_sha = _sha256(_pretty(release_configuration()))
    scenario_sha = _sha256(_pretty(scenario_policy_document()))
    authorities = {
        "release_pins": release_configuration(),
        "authenticated_files": {
            "qualification_report_sha256": qualification_sha,
            "sizing_receipt_sha256": sizing_sha,
            "holdout_sha256": holdout_sha,
        },
        "holdout_boundary_id": HOLDOUT_ID,
        "holdout_utc": HOLDOUT_UTC,
        "holdout_is_coverage_boundary": True,
        "qualification_code_sha256": QUALIFICATION_CODE_SHA256,
        "qualification_cli_sha256": QUALIFICATION_CLI_SHA256,
        "source_manifest_detail_sha256": MANIFEST_DETAIL_SHA256,
        "sizing_code_sha256": sizing_code,
        "sizing_cli_sha256": sizing_cli,
        "configuration_sha256": configuration_sha,
        "scenario_policy_sha256": scenario_sha,
        "intersections": {
            "bundle_column_intersection": "five_product_observed_days",
            "five_product_observed_day_count": OBSERVED_DAY_COUNT,
            "five_product_observed_day_sha256": OBSERVED_DAY_SHA256,
            "full_cadence_day_count": FULL_CADENCE_DAY_COUNT,
            "full_cadence_day_sha256": FULL_CADENCE_DAY_SHA256,
            "aligned_day_rows": ALIGNED_DAY_ROWS,
        },
        "resources": {
            "harmonic_bundle_allocation_bytes": HARMONIC_BUNDLE_ALLOCATION_BYTES,
            "measured_current_bundle_bytes": MEASURED_CURRENT_BUNDLE_BYTES,
            "sizing_projected_bundle_rows": SIZING_PROJECTED_BUNDLE_ROWS,
            "current_plus_future_provision_bytes": CURRENT_PLUS_FUTURE_PROVISION_BYTES,
            "release_metadata_pool_bytes": RELEASE_METADATA_BYTES,
            "metadata_remainder_bytes": release_metadata_budget(UNUSED_COVERAGE_RESERVATION_BYTES),
            "operating_reserve_bytes": OPERATING_RESERVE_BYTES,
            "operating_reserve_spent": False,
            "unused_coverage_reservation_bytes": UNUSED_COVERAGE_RESERVATION_BYTES,
            "unused_coverage_reservation_reallocatable": False,
            "catalog_commit_required": True,
        },
        "canonical_instrument_ids": None,
        "source_available_at": None,
        "availability_semantics": "unknown_not_imputed",
        "fee_missing_is_zero": False,
        "liquidation_complete": False,
        "funding_expected_count": None,
    }
    return sizing, authorities


def _shared_columns(authorities: Mapping[str, Any], coverage_rows: Mapping[str, int]) -> dict[str, Any]:
    return {
        "canonical_instrument_id": None,
        "canonical_instrument_version_id": None,
        "reference_identity_state": REF_IDENTITY_STATE,
        "source_report_sha256": REPORT_SHA256,
        "source_manifest_detail_sha256": MANIFEST_DETAIL_SHA256,
        "qualification_code_sha256": QUALIFICATION_CODE_SHA256,
        "qualification_cli_sha256": QUALIFICATION_CLI_SHA256,
        "sizing_code_sha256": authorities["sizing_code_sha256"],
        "sizing_cli_sha256": authorities["sizing_cli_sha256"],
        "configuration_sha256": authorities["configuration_sha256"],
        "scenario_policy_sha256": authorities["scenario_policy_sha256"],
        "unit_convention": UNIT_CONVENTION,
        "censorship_semantics": CENSORSHIP_SEMANTICS,
        "coverage_gap_rows": coverage_rows["source_gap"],
        "typed_gap_membership_rows": coverage_rows["typed_gap_membership"],
        "fee_authority_gap_rows": FEE_AUTHORITY_GAP_ROWS,
        "cross_product_intersection_count": OBSERVED_DAY_COUNT,
        "cross_product_intersection_sha256": OBSERVED_DAY_SHA256,
    }


def _write_bundle(rows: Sequence[Mapping[str, Any]]) -> bytes:
    if len(rows) > BUNDLE_ROW_INDEX_BOUND:
        _fail("row_mismatch", "bundle row index exceeds its explicit bound", rows=len(rows))
    schema = pa.schema(
        [pa.field(name, _bundle_type(arrow), nullable=nullable) for name, arrow, nullable in BUNDLE_FIELDS]
    )
    sink = pa.BufferOutputStream()
    writer = pq.ParquetWriter(
        sink,
        schema,
        compression=PARQUET_COMPRESSION,
        compression_level=PARQUET_COMPRESSION_LEVEL,
        version=PARQUET_VERSION,
        use_dictionary=True,
        write_statistics=False,
        store_schema=True,
    )
    try:
        for start in range(0, len(rows), SIZING_ROW_BATCH):
            batch_rows = rows[start : start + SIZING_ROW_BATCH]
            arrays = [pa.array([row[field.name] for row in batch_rows], type=field.type) for field in schema]
            writer.write_table(pa.Table.from_arrays(arrays, schema=schema), row_group_size=SIZING_ROW_BATCH)
    finally:
        writer.close()
    return sink.getvalue().to_pybytes()


def _bundle_type(arrow: str) -> pa.DataType:
    if arrow == _DICTIONARY:
        return pa.dictionary(pa.int32(), pa.string())
    if arrow == _STRING:
        return pa.string()
    if arrow == _INT64:
        return pa.int64()
    _fail("unsupported_arrow_type", "bundle column type is not the frozen contract", arrow_type=arrow)


def _plan(account: _ProductAccount, shared_quality: Mapping[str, Any]) -> ReferenceDatasetPlan:
    quality = {**shared_quality, **account.quality}
    files = tuple(
        ReferenceFile(
            item.relative_path,
            item.sha256,
            item.rows,
            item.byte_size,
            item.partition,
            item.is_table,
            item.schema_fields,
        )
        for item in sorted(account.files, key=lambda value: value.relative_path)
    )
    return ReferenceDatasetPlan(account.spec.dataset_type, account.schema_fingerprint, files, quality)


def _policy(assembly: AssemblyPolicy) -> ReleasePolicy:
    code = seal_code_identity(
        assembly.repo,
        assembly.code_commit,
        bind_runtime=assembly.bind_runtime,
        executing=assembly.executing,
        file_bytes=assembly.file_bytes,
    )
    return replace(
        production_release_policy(assembly.repo, assembly.catalog_path, code),
        observed_free_bytes=assembly.observed_free_bytes,
    )


def prepare_harmonic_bundle(assembly: AssemblyPolicy) -> PreparedRelease:
    """Authenticate accepted inputs and write a non-consumable prepared release."""

    root_policy = _policy(assembly)
    root = root_policy.repo if root_policy.repo.is_absolute() else Path.cwd() / root_policy.repo
    production = assembly.authenticate_production_receipt
    sizing, authorities = _authenticate_authorities(root, production)
    accounts = {spec.dataset_type: _account_product(root, spec, sizing, production) for spec in PRODUCTS}
    authorities["retained_unreferenced_kline_inventory"] = {
        product: accounts[product].retained_audit for product in _RETAINED_KLINE_COUNTS
    }
    reconciliation = _authenticate_reconciliation(
        root,
        accounts,
        authorities["authenticated_files"]["qualification_report_sha256"],
        production,
    )
    authorities["authenticated_files"]["reconciliation_completion_sha256"] = reconciliation["completion_sha256"]
    authorities["authenticated_files"]["reconciliation_report_sha256"] = reconciliation["report_sha256"]
    coverage = accounts[PRODUCT_COVERAGE]
    coverage_rows = {
        "source_gap": int(coverage.quality["coverage_gap_rows"]),
        "typed_gap_membership": int(coverage.quality["typed_gap_membership_rows"]),
    }
    shared = {
        "bundle_column_intersection": "five_product_observed_days",
        "intersections": authorities["intersections"],
        "utc_month_absent_token": ABSENT_MONTH,
        "canonical_instrument_ids": None,
        "source_available_at": None,
        "availability_semantics": "unknown_not_imputed",
        "liquidation_complete": False,
        "funding_expected_count": None,
        "fee_missing_is_zero": False,
        "release_pins": authorities["release_pins"],
    }
    product_plans = [_plan(accounts[spec.dataset_type], shared) for spec in PRODUCTS]
    config_sha = str(authorities["configuration_sha256"])
    identified = identify_products(product_plans, root_policy, config_sha)
    dataset_ids = {item.dataset_type: item.dataset_id for item in identified}
    columns = _shared_columns(authorities, coverage_rows)
    bundle_rows = []
    for spec in PRODUCTS:
        for source in accounts[spec.dataset_type].bundle_sources:
            bundle_rows.append(
                {
                    "required_product": source.required_product,
                    "component": source.component,
                    "dataset_id": dataset_ids[source.owner],
                    "native_symbol": source.native_symbol,
                    "utc_month": source.utc_month,
                    "partition_sha256": source.partition_sha256,
                    "partition_bytes": source.partition_bytes,
                    "row_count": source.row_count,
                    "schema_sha256": source.schema_sha256,
                    "lineage_manifest_sha256": source.lineage_sha256,
                    "lineage_mapping_count": source.lineage_mapping_count,
                    **columns,
                }
            )
    bundle_rows.sort(
        key=lambda row: (
            row["required_product"],
            row["component"],
            row["native_symbol"],
            row["utc_month"],
            row["partition_sha256"] or "",
        )
    )
    projected = sizing["projections"]["fixed_schema_products"][PRODUCT_BUNDLE]
    projected_rows = _whole(projected.get("projected_rows"), "bundle rows")
    if projected_rows != SIZING_PROJECTED_BUNDLE_ROWS:
        _fail("identity_pin", "projected bundle rows changed after authentication")
    if len(bundle_rows) > BUNDLE_ROW_INDEX_BOUND:
        _fail("row_mismatch", "reconstructed bundle rows exceed the explicit index bound", rows=len(bundle_rows))
    if any(row["required_product"] == PRODUCT_BUNDLE for row in bundle_rows):
        _fail("bundle_dependencies", "bundle catalog includes itself")
    payload = _write_bundle(bundle_rows)
    relative, digest, size = write_new_bundle_object(root, payload, root_policy)
    fields = _footer(root, relative, len(bundle_rows))
    if _normalize_contract(_contract(fields)) != _normalize_contract(_contract(BUNDLE_FIELDS)):
        _fail("bundle_schema_mismatch", "written bundle footer is not the frozen contract")
    fingerprint = _schema_sha_pretty({"required_product": PRODUCT_BUNDLE, "schema": _contract(fields)})
    bundle_quality = {
        **shared,
        "bundle_file_sha256": digest,
        "bundle_file_bytes": size,
        "quality_summary_carries_descriptor_hash": False,
    }
    bundle_plan = ReferenceDatasetPlan(
        PRODUCT_BUNDLE,
        fingerprint,
        (
            ReferenceFile(
                relative,
                digest,
                len(bundle_rows),
                size,
                {"role": "harmonic_bundle"},
                True,
                fields,
            ),
        ),
        bundle_quality,
        tuple(spec.dataset_type for spec in PRODUCTS),
    )
    authorities["resources"] = {
        **authorities["resources"],
        "bundle_file_bytes": size,
        "bundle_rows": len(bundle_rows),
        "reconstructed_bundle_rows": len(bundle_rows),
        "sizing_projected_bundle_rows": projected_rows,
    }
    return prepare_release((*product_plans, bundle_plan), root_policy, config_sha256=config_sha, authorities=authorities)


def _proof_bytes(path: Path) -> bytes:
    if path.is_symlink():
        _fail("unsafe_path", "consumer proof path is a symlink", path=str(path))
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        facts = os.fstat(descriptor)
        if not stat.S_ISREG(facts.st_mode) or facts.st_size > PROOF_MAX_BYTES:
            _fail("metadata_bound", "consumer proof exceeds its read bound", path=str(path))
        return os.read(descriptor, facts.st_size)
    finally:
        os.close(descriptor)


def publish_harmonic_bundle(
    assembly: AssemblyPolicy,
    prepared_sha256: str,
    proof_path: Path,
    *,
    proof_sha256: str,
    checker_sha256: str,
    nautilus_version: str,
    hooks: ReleaseHooks | None = None,
    connection: Any = None,
) -> PublishedRelease:
    """Admit the prepared candidate only after its caller-pinned consumer proof."""

    return publish_release(
        _policy(assembly),
        prepared_sha256,
        _proof_bytes(proof_path),
        proof_sha256=proof_sha256,
        checker_sha256=checker_sha256,
        nautilus_version=nautilus_version,
        hooks=hooks,
        connection=connection,
    )


def verify_harmonic_bundle(
    assembly: AssemblyPolicy,
    publication_sha256: str,
    proof_path: Path,
    *,
    proof_sha256: str,
    checker_sha256: str,
    nautilus_version: str,
    connection: Any = None,
) -> PublishedRelease:
    """Reauthenticate the publication, including the caller proof pin."""

    return read_release(
        _policy(assembly),
        publication_sha256,
        _proof_bytes(proof_path),
        proof_sha256=proof_sha256,
        checker_sha256=checker_sha256,
        nautilus_version=nautilus_version,
        connection=connection,
    )


def production_assembly_policy(repo: Path, catalog_path: Path, code_commit: str, cli_file: Path) -> AssemblyPolicy:
    from cryptofactors.catalog.dataset import cex002_reference_release as catalog_module

    return AssemblyPolicy(
        repo=repo,
        catalog_path=catalog_path,
        code_commit=code_commit,
        bind_runtime=True,
        executing={
            "src/cryptofactors/catalog/dataset/cex002_reference_release.py": Path(catalog_module.__file__),
            "src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py": Path(__file__),
            "scripts/research/publish_binance_usdm_harmonic_bundle.py": cli_file,
        },
        authenticate_production_receipt=True,
    )
